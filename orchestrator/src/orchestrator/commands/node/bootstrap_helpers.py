"""
Helper functions for the bootstrap command.

Extracted from bootstrap.py to keep the main command manageable.
"""

import json
from pathlib import Path
from typing import Any

import click
import pulumi.automation as auto

from orchestrator.ansible.inventory import generate_inventory
from orchestrator.ansible.runner import run_ansible_role, AnsibleError
from orchestrator.commands.config.sync import get_repo_root, get_sops_key_from_esc, run_pulumi_sync
from orchestrator.config import get_config_value
from orchestrator.context import OrchestratorContext
from orchestrator.utils.sops import update_sops_file, SopsError
from orchestrator.utils.ssh import setup_ssh_agent, get_ssh_agent_status, SSHError


def load_and_validate_ssh_key(
    ctx: OrchestratorContext,
    proxmox_config: dict[str, Any],
    node_name: str,
) -> None:
    """
    Load and validate SSH key for bootstrap access.

    Args:
        ctx: Orchestrator context
        proxmox_config: Proxmox configuration from ESC
        node_name: Name of the node being bootstrapped

    Raises:
        click.Abort: If SSH setup fails
    """
    try:
        # Check ssh-agent status
        agent_status = get_ssh_agent_status()
        if not agent_status["running"]:
            click.secho("✗ ssh-agent is not running", fg="red", err=True)
            click.echo("Please start ssh-agent with: eval $(ssh-agent -s)", err=True)
            raise click.Abort()

        if ctx.verbose:
            click.echo(f"  ssh-agent PID: {agent_status['pid']}")
            click.echo(f"  Current keys loaded: {agent_status['num_keys']}")

        # Get SSH key from Proxmox config
        ssh_key = get_config_value(proxmox_config, "ssh.admin.private_key")
        if not ssh_key or ssh_key == {}:
            click.secho("✗ Bootstrap SSH key not found in Proxmox configuration", fg="red", err=True)
            click.echo("Expected key at: ssh.admin.private_key", err=True)
            raise click.Abort()

        # Add SSH key to agent
        setup_ssh_agent(ssh_key, key_name=f"bootstrap_{node_name}")
        click.secho("✓ SSH key added to agent", fg="green")

    except SSHError as e:
        click.secho(f"✗ SSH setup failed: {e}", fg="red", err=True)
        raise click.Abort()


def run_ansible_bootstrap_role(
    ctx: OrchestratorContext,
    proxmox_config: dict[str, Any],
    tailscale_config: dict[str, Any],
    node_name: str,
) -> str:
    """
    Run the Ansible bootstrap role on the target node.

    Args:
        ctx: Orchestrator context
        proxmox_config: Proxmox configuration from ESC
        tailscale_config: Tailscale configuration from ESC
        node_name: Name of the node being bootstrapped

    Returns:
        Path to the local token file (if token was created)

    Raises:
        click.Abort: If Ansible execution fails
    """
    try:
        # Generate Ansible inventory
        click.echo("  Generating Ansible inventory...")
        inventory = generate_inventory(proxmox_config, target_node=node_name)

        if ctx.verbose:
            click.echo()
            click.echo("Generated inventory:")
            click.echo(json.dumps(inventory, indent=2))
            click.echo()

        # Define local path for fetched API token
        token_local_file = f"/tmp/proxmox-api-token-{node_name}.json"

        # Prepare extravars for Ansible
        tailscale_authkey = get_config_value(tailscale_config, "client_secret")

        extravars = {
            "tailscale_authkey": tailscale_authkey,
            "tailscale_tags": get_config_value(tailscale_config, "tags"),
            "tailscale_oauth_ephemeral": get_config_value(tailscale_config, "oauth_ephemeral", False),
            "tailscale_oauth_preauthorized": get_config_value(tailscale_config, "oauth_preauthorized", True),
            "tailscale_verbose": ctx.verbose,
            "proxmox_api_token_local_file": token_local_file,
        }

        # Validate required extravars
        missing_vars = []
        if not extravars.get("tailscale_authkey"):
            missing_vars.append("tailscale_authkey (client_secret required)")
        if not extravars.get("tailscale_tags"):
            missing_vars.append("tailscale_tags")

        if missing_vars:
            click.secho("✗ Missing required variables for Ansible role:", fg="red", err=True)
            for var in missing_vars:
                click.echo(f"  - {var}", err=True)
            raise click.Abort()

        if ctx.verbose:
            click.echo("Ansible extravars:")
            masked_vars = extravars.copy()
            masked_vars["tailscale_authkey"] = "***REDACTED***"
            click.echo(json.dumps(masked_vars, indent=2))
            click.echo()

        # Run the proxmox-bootstrap role
        click.echo("  Executing proxmox-bootstrap role...")
        click.echo("  (This may take several minutes)")
        click.echo()

        success = run_ansible_role(
            role_name="proxmox-bootstrap",
            inventory=inventory,
            extra_vars=extravars,
            verbose=ctx.verbose,
        )

        if not success:
            click.secho("✗ Ansible bootstrap role did not complete successfully", fg="red", err=True)
            raise click.Abort()

        click.echo()
        click.secho("✓ Ansible bootstrap role completed successfully", fg="green", bold=True)

        return token_local_file

    except AnsibleError as e:
        click.secho(f"✗ Ansible execution failed: {e}", fg="red", err=True)
        raise click.Abort()


def process_api_token(
    ctx: OrchestratorContext,
    token_local_file: str,
    proxmox_config: dict[str, Any],
    node_name: str,
) -> None:
    """
    Process the API token created by Ansible, update secrets, and sync to ESC.

    Args:
        ctx: Orchestrator context
        token_local_file: Path to the local token file fetched by Ansible
        proxmox_config: Proxmox configuration from ESC
        node_name: Name of the node

    Raises:
        click.Abort: If token processing fails
    """
    try:
        token_file_path = Path(token_local_file)

        if not token_file_path.exists():
            click.secho("⚠ No token file found - token already existed", fg="yellow")
            click.echo("  Ansible skipped token creation (already exists in Proxmox)")
            click.echo("  If you need to recreate the token, delete it in Proxmox and re-run bootstrap")
            return

        # Read token file
        click.echo(f"  Token file found: {token_file_path}")
        click.echo("  Reading token credentials...")

        with open(token_file_path, 'r') as f:
            token_data = json.load(f)

        token_id = token_data.get("full-tokenid")
        token_secret = token_data.get("value")

        if not token_id or not token_secret:
            click.secho("✗ Token file is missing required fields", fg="red", err=True)
            raise click.Abort()

        click.secho(f"✓ Token retrieved: {token_id}", fg="green")

        # Mask the token secret for display
        masked_secret = f"{token_secret[:8]}...{token_secret[-8:]}" if len(token_secret) > 16 else "***"
        click.echo(f"  Token secret: {masked_secret}")

        # Update secrets file
        _update_secrets_file(ctx, token_id, token_secret, proxmox_config, node_name)

        # Sync to ESC
        _sync_to_esc(ctx)

        # Clean up
        click.echo()
        click.echo("🧹 Cleaning up temporary token file...")
        token_file_path.unlink()
        click.secho("✓ Token file removed", fg="green")

    except SopsError as e:
        click.secho(f"✗ Failed to update secrets: {e}", fg="red", err=True)
        raise click.Abort()
    except Exception as e:
        click.secho(f"✗ Unexpected error processing API token: {e}", fg="red", err=True)
        if ctx.verbose:
            import traceback
            click.echo(traceback.format_exc(), err=True)
        raise click.Abort()


def _update_secrets_file(
    ctx: OrchestratorContext,
    token_id: str,
    token_secret: str,
    proxmox_config: dict[str, Any],
    node_name: str,
) -> None:
    """Update the SOPS-encrypted secrets file with new token."""
    click.echo()
    click.echo("💾 Updating secrets file...")

    repo_root = get_repo_root()
    secrets_file = repo_root / "secrets" / "proxmox" / "api.enc.yaml"

    if ctx.verbose:
        click.echo(f"  Secrets file: {secrets_file}")

    # Get node configuration
    from orchestrator.commands.node.bootstrap import find_node_in_config
    node_config = find_node_in_config(proxmox_config, node_name)
    if not node_config:
        click.secho(f"✗ Node configuration not found for {node_name}", fg="red", err=True)
        raise click.Abort()

    # Determine API endpoint
    api_endpoint = node_config.get("endpoint")
    if not api_endpoint:
        node_host = node_config.get("ssh_host") or node_config.get("tailscale_hostname")
        if node_host:
            api_endpoint = f"https://{node_host}:8006/api2/json"
        else:
            api_endpoint = "https://10.0.0.1:8006/api2/json"

    # Update secrets file
    click.echo("  Encrypting and updating secrets with SOPS...")
    update_sops_file(
        secrets_file,
        {
            f"api.nodes.{node_name}.endpoint": api_endpoint,
            f"api.nodes.{node_name}.token_id": token_id,
            f"api.nodes.{node_name}.token_secret": token_secret,
            f"api.nodes.{node_name}.insecure": True,
        },
    )
    click.secho(f"✓ Secrets file updated: {secrets_file}", fg="green")


def _sync_to_esc(ctx: OrchestratorContext) -> None:
    """Sync updated configuration to Pulumi ESC."""
    click.echo()
    click.echo("☁️  Syncing configuration to Pulumi ESC...")

    try:
        # Get SOPS key
        click.echo("  Retrieving SOPS key from ESC...")
        sops_key = get_sops_key_from_esc()

        # Run sync
        repo_root = get_repo_root()
        esc_sync_dir = repo_root / "pulumi" / "esc-sync"
        click.echo("  Running Pulumi sync...")

        result = run_pulumi_sync(
            work_dir=esc_sync_dir,
            sops_key=sops_key,
            dry_run=False,
            verbose=ctx.verbose,
        )

        click.echo()
        click.secho("✓ Configuration synced to ESC", fg="green")

        if ctx.verbose and isinstance(result, auto.UpResult):
            click.echo()
            click.echo("Sync summary:")
            if result.summary.resource_changes:
                for change_type, count in result.summary.resource_changes.items():
                    if count > 0:
                        click.echo(f"  {change_type}: {count}")

    except Exception as e:
        click.secho(f"⚠ Failed to sync to ESC: {e}", fg="yellow", err=True)
        click.echo("  You can manually sync later with: orchestrator config sync", fg="yellow")
        if ctx.verbose:
            import traceback
            click.echo(traceback.format_exc(), err=True)

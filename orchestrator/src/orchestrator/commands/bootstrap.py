"""
Bootstrap command for initializing Proxmox nodes.

Installs Tailscale, configures security lockdown, and prepares the node
for orchestration.
"""

import json

import click

from orchestrator.context import pass_orchestrator_context, OrchestratorContext
from orchestrator.config import load_esc_config, get_config_value, ConfigError
from orchestrator.utils.ssh import setup_ssh_agent, get_ssh_agent_status, verify_ssh_connectivity, SSHError


def find_node_in_config(config: dict, node_name: str) -> dict | None:
    """
    Find a node configuration by name, handling both list and dict formats.

    Args:
        config: ESC configuration dictionary
        node_name: Name of the node to find

    Returns:
        Node configuration dict, or None if not found
    """
    nodes = config.get("nodes", [])

    # Handle list format
    if isinstance(nodes, list):
        for node in nodes:
            if node.get("name") == node_name:
                return node
        return None

    # Handle dict format
    elif isinstance(nodes, dict):
        return nodes.get(node_name)

    return None


@click.command()
@click.argument("node_name")
@click.option(
    "--skip-tailscale",
    is_flag=True,
    help="Skip Tailscale installation (for testing)",
)
@pass_orchestrator_context
def bootstrap(
    ctx: OrchestratorContext,
    node_name: str,
    skip_tailscale: bool,
) -> None:
    """
    Bootstrap a Proxmox node with Tailscale and security lockdown.

    This is a one-time operation performed on each new physical server.
    It must be run before any other orchestrator commands.

    Steps performed:
    1. Load node configuration from ESC
    2. Setup SSH agent with bootstrap keys
    3. Run Ansible bootstrap role (proxmox-bootstrap)
    4. Verify Tailscale connectivity
    5. Lock down public access

    \b
    Example:
        orchestrator bootstrap rk1
    """
    click.secho(f"🚀 Bootstrapping node: {node_name}", fg="cyan", bold=True)
    click.echo()

    # Phase 1: Load configuration from ESC
    click.echo("📋 Loading configuration from Pulumi ESC...")
    try:
        # Load Proxmox environment configuration
        proxmox_config = load_esc_config("proxmox")
        click.secho("✓ Loaded Proxmox configuration", fg="green")

        # Load Tailscale environment configuration
        # This is required - bootstrap cannot proceed without Tailscale OAuth credentials
        tailscale_config = load_esc_config("tailscale")
        click.secho("✓ Loaded Tailscale configuration", fg="green")

        # Validate OAuth credentials are present
        # The client_secret should be the complete OAuth secret (tskey-client-XXXXX)
        if not get_config_value(tailscale_config, "client_secret"):
            click.secho("✗ Tailscale OAuth credentials missing", fg="red", err=True)
            click.echo("Expected: client_secret (complete OAuth token) in Tailscale configuration", err=True)
            raise click.Abort()

        # Validate tags are present (required for OAuth)
        tags = get_config_value(tailscale_config, "tags")
        if not tags or (isinstance(tags, list) and len(tags) == 0):
            click.secho("✗ Tailscale tags are required when using OAuth", fg="red", err=True)
            click.echo("Expected: tags list in Tailscale configuration (e.g., ['subnet-router', 'proxmox'])", err=True)
            raise click.Abort()

        if ctx.verbose:
            click.echo()
            click.echo("Proxmox Configuration:")
            click.echo(json.dumps(proxmox_config, indent=2))

            if tailscale_config:
                click.echo()
                click.echo("Tailscale Configuration:")
                # Mask OAuth credentials for security
                masked_tailscale = tailscale_config.copy()
                if "client_secret" in masked_tailscale:
                    masked_tailscale["client_secret"] = "***REDACTED***"
                # Show client_id but mask the secret
                click.echo(json.dumps(masked_tailscale, indent=2))

    except ConfigError as e:
        click.secho(f"✗ Failed to load configuration: {e}", fg="red", err=True)
        raise click.Abort()

    click.echo()
    click.secho("✓ Configuration loaded successfully", fg="green", bold=True)

    # Phase 2: Setup SSH agent with bootstrap keys
    click.echo()
    click.echo("🔑 Setting up SSH authentication...")

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
        # The SSH key should be in the proxmox config under 'ssh.admin.private_key'
        ssh_key = get_config_value(proxmox_config, "ssh.admin.private_key")
        if not ssh_key or ssh_key == {}:
            click.secho("✗ Bootstrap SSH key not found in Proxmox configuration", fg="red", err=True)
            click.echo("Expected key at: ssh.admin.private_key", err=True)
            click.echo("Note: The key appears to be an encrypted secret that wasn't decrypted", err=True)
            raise click.Abort()

        # Add SSH key to agent
        setup_ssh_agent(ssh_key, key_name=f"bootstrap_{node_name}")
        click.secho("✓ SSH key added to agent", fg="green")

        # Get node endpoint for SSH connectivity check
        node_config = find_node_in_config(proxmox_config, node_name)
        node_endpoint = node_config.get("ssh_host") if node_config else None
        if node_endpoint:
            click.echo(f"  Verifying SSH connectivity to {node_endpoint}...")
            if verify_ssh_connectivity(node_endpoint, user="root"):
                click.secho(f"✓ SSH connection to {node_endpoint} successful", fg="green")
            else:
                click.secho(f"⚠ SSH connection to {node_endpoint} failed", fg="yellow")
                click.echo("  This may be expected if the node is not yet accessible", fg="yellow")
        else:
            if ctx.verbose:
                click.echo(f"  No SSH endpoint configured for node {node_name}, skipping connectivity check")

    except SSHError as e:
        click.secho(f"✗ SSH setup failed: {e}", fg="red", err=True)
        raise click.Abort()

    click.echo()
    click.secho("✓ SSH authentication configured", fg="green", bold=True)

    # Phase 3: Run Ansible bootstrap role
    click.echo()
    click.echo("⚙️  Running Ansible bootstrap role...")

    try:
        from orchestrator.ansible.inventory import generate_inventory
        from orchestrator.ansible.runner import run_ansible_role, AnsibleError

        # Generate Ansible inventory for the target node
        click.echo("  Generating Ansible inventory...")
        inventory = generate_inventory(proxmox_config, target_node=node_name)

        if ctx.verbose:
            click.echo()
            click.echo("Generated inventory:")
            click.echo(json.dumps(inventory, indent=2))
            click.echo()

        # Prepare extravars for the Ansible role
        # These are the required variables for the proxmox-bootstrap role

        # Get the complete Tailscale OAuth client secret
        # This is the full OAuth secret token (format: tskey-client-XXXXX)
        # provided directly from Tailscale when creating an OAuth client
        tailscale_authkey = get_config_value(tailscale_config, "client_secret")

        extravars = {
            # Tailscale OAuth credentials
            "tailscale_authkey": tailscale_authkey,
            "tailscale_tags": get_config_value(tailscale_config, "tags"),

            # Optional: OAuth settings (have defaults in role)
            "tailscale_oauth_ephemeral": get_config_value(
                tailscale_config, "oauth_ephemeral", False
            ),
            "tailscale_oauth_preauthorized": get_config_value(
                tailscale_config, "oauth_preauthorized", True
            ),

            # Verbose output
            "tailscale_verbose": ctx.verbose,
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

        if success:
            click.echo()
            click.secho("✓ Ansible bootstrap role completed successfully", fg="green", bold=True)
        else:
            click.secho("✗ Ansible bootstrap role did not complete successfully", fg="red", err=True)
            raise click.Abort()

    except AnsibleError as e:
        click.secho(f"✗ Ansible execution failed: {e}", fg="red", err=True)
        raise click.Abort()
    except Exception as e:
        click.secho(f"✗ Unexpected error during Ansible execution: {e}", fg="red", err=True)
        if ctx.verbose:
            import traceback
            click.echo(traceback.format_exc(), err=True)
        raise click.Abort()

    # Phase 4: Bootstrap complete
    click.echo()
    click.secho("✓ Bootstrap completed successfully!", fg="green", bold=True)

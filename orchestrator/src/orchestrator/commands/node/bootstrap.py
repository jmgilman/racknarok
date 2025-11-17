"""
Bootstrap command for initializing Proxmox nodes.

Installs Tailscale, configures security lockdown, and prepares the node
for orchestration.
"""

import json

import click

from orchestrator.context import pass_orchestrator_context, OrchestratorContext
from orchestrator.config import load_esc_config, get_config_value, ConfigError
from orchestrator.commands.node.bootstrap_helpers import (
    load_and_validate_ssh_key,
    run_ansible_bootstrap_role,
    process_api_token,
)


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
    4. Process API token (if created)
    5. Sync configuration to ESC

    \b
    Example:
        orchestrator node bootstrap rk1
    """
    click.secho(f"🚀 Bootstrapping node: {node_name}", fg="cyan", bold=True)
    click.echo()

    # Phase 1: Load configuration from ESC
    proxmox_config, tailscale_config = _load_configurations(ctx)

    # Phase 2: Setup SSH authentication
    click.echo()
    click.echo("🔑 Setting up SSH authentication...")
    load_and_validate_ssh_key(ctx, proxmox_config, node_name)
    click.echo()
    click.secho("✓ SSH authentication configured", fg="green", bold=True)

    # Phase 3: Run Ansible bootstrap role
    click.echo()
    click.echo("⚙️  Running Ansible bootstrap role...")
    token_local_file = run_ansible_bootstrap_role(
        ctx, proxmox_config, tailscale_config, node_name
    )

    # Phase 4: Process API token (if created by Ansible)
    click.echo()
    click.echo("🔑 Processing Proxmox API token...")
    process_api_token(ctx, token_local_file, proxmox_config, node_name)

    # Phase 5: Bootstrap complete
    click.echo()
    click.secho("✓ Bootstrap completed successfully!", fg="green", bold=True)
    click.echo()
    click.echo("Next steps:")
    click.echo("  1. The Proxmox node is now secured and accessible via Tailscale")
    click.echo("  2. API credentials have been created and synced to ESC")
    click.echo("  3. You can now provision VMs with: orchestrator provision")


def _load_configurations(ctx: OrchestratorContext) -> tuple[dict, dict]:
    """
    Load Proxmox and Tailscale configurations from ESC.

    Args:
        ctx: Orchestrator context

    Returns:
        Tuple of (proxmox_config, tailscale_config)

    Raises:
        click.Abort: If configuration loading fails
    """
    click.echo("📋 Loading configuration from Pulumi ESC...")

    try:
        # Load Proxmox environment configuration
        proxmox_config = load_esc_config("proxmox")
        click.secho("✓ Loaded Proxmox configuration", fg="green")

        # Load Tailscale environment configuration
        tailscale_config = load_esc_config("tailscale")
        click.secho("✓ Loaded Tailscale configuration", fg="green")

        # Validate OAuth credentials
        if not get_config_value(tailscale_config, "client_secret"):
            click.secho("✗ Tailscale OAuth credentials missing", fg="red", err=True)
            click.echo("Expected: client_secret (complete OAuth token) in Tailscale configuration", err=True)
            raise click.Abort()

        # Validate tags
        tags = get_config_value(tailscale_config, "tags")
        if not tags or (isinstance(tags, list) and len(tags) == 0):
            click.secho("✗ Tailscale tags are required when using OAuth", fg="red", err=True)
            click.echo("Expected: tags list in Tailscale configuration (e.g., ['subnet-router', 'proxmox'])", err=True)
            raise click.Abort()

        if ctx.verbose:
            click.echo()
            click.echo("Proxmox Configuration:")
            click.echo(json.dumps(proxmox_config, indent=2))

            click.echo()
            click.echo("Tailscale Configuration:")
            masked_tailscale = tailscale_config.copy()
            if "client_secret" in masked_tailscale:
                masked_tailscale["client_secret"] = "***REDACTED***"
            click.echo(json.dumps(masked_tailscale, indent=2))

    except ConfigError as e:
        click.secho(f"✗ Failed to load configuration: {e}", fg="red", err=True)
        raise click.Abort()

    click.echo()
    click.secho("✓ Configuration loaded successfully", fg="green", bold=True)

    return proxmox_config, tailscale_config

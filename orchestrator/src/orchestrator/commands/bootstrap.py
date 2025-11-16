"""
Bootstrap command for initializing Proxmox nodes.

Installs Tailscale, configures security lockdown, and prepares the node
for orchestration.
"""

import click

from orchestrator.context import pass_orchestrator_context, OrchestratorContext


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
    # TODO: Implement bootstrap workflow
    # - Load ESC config for 'proxmox' environment
    # - Extract node configuration
    # - Setup SSH agent with bootstrap key
    # - Generate Ansible inventory
    # - Run 'proxmox-bootstrap' role
    # - Verify Tailscale is working
    # - Report success/failure

    click.echo(f"Bootstrapping node: {node_name}")

    if skip_tailscale:
        click.echo("Skipping Tailscale installation")

    if ctx.verbose:
        click.echo(f"Verbose mode enabled")

    # Placeholder for actual implementation
    click.secho("✗ Not yet implemented", fg="red", err=True)
    raise click.Abort()

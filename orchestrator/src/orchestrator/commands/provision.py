"""
Provision command for creating VMs via Pulumi.

Creates and configures VMs on Proxmox using Pulumi Automation API.
"""

import click

from orchestrator.context import pass_orchestrator_context, OrchestratorContext


@click.command()
@click.option(
    "--stack",
    default="dev",
    help="Pulumi stack to use",
)
@click.option(
    "--preview",
    is_flag=True,
    help="Preview changes without applying",
)
@pass_orchestrator_context
def provision(
    ctx: OrchestratorContext,
    stack: str,
    preview: bool,
) -> None:
    """
    Provision VMs via Pulumi.

    Creates VMs on Proxmox using the Pulumi Automation API. This includes:
    - Talos Linux nodes for Kubernetes clusters
    - NixOS utility VMs (Tailscale router, DNS server)
    - Network configuration

    \b
    Example:
        orchestrator provision
        orchestrator provision --preview
        orchestrator provision --stack prod
    """
    # TODO: Implement Pulumi provisioning workflow
    # - Load ESC config for stack
    # - Initialize Pulumi Automation API
    # - Select or create stack
    # - Run preview or up
    # - Display results
    # - Handle errors gracefully

    click.echo(f"Provisioning infrastructure (stack: {stack})")

    if preview:
        click.echo("Preview mode - no changes will be made")

    if ctx.verbose:
        click.echo("Verbose output enabled")

    # Placeholder for actual implementation
    click.secho("✗ Not yet implemented", fg="red", err=True)
    raise click.Abort()

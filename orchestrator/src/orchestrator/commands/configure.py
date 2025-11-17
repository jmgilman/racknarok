"""
Configure command for deploying NixOS configurations.

Uses deploy-rs to configure NixOS-based utility VMs.
"""

import click

from orchestrator.context import pass_orchestrator_context, OrchestratorContext


@click.command()
@click.option(
    "--target",
    multiple=True,
    help="Specific target(s) to configure (can be specified multiple times)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Build but don't activate configurations",
)
@pass_orchestrator_context
def configure(
    ctx: OrchestratorContext,
    target: tuple[str, ...],
    dry_run: bool,
) -> None:
    """
    Configure NixOS VMs using deploy-rs.

    Deploys NixOS configurations to utility VMs:
    - Tailscale subnet router
    - Internal DNS server
    - Future utility VMs

    \b
    Example:
        orchestrator configure
        orchestrator configure --target tailscale-router
        orchestrator configure --target dns-server --dry-run
    """
    # TODO: Implement NixOS configuration workflow
    # - Load list of NixOS targets from config
    # - If specific targets specified, filter to those
    # - For each target:
    #   - Run deploy-rs build
    #   - Run deploy-rs activate (unless dry-run)
    # - Report results for each target

    click.echo("Configuring NixOS VMs")

    if target:
        click.echo(f"Targets: {', '.join(target)}")
    else:
        click.echo("Configuring all NixOS VMs")

    if dry_run:
        click.echo("Dry run mode - building but not activating")

    if ctx.verbose:
        click.echo("Verbose output enabled")

    # Placeholder for actual implementation
    click.secho("✗ Not yet implemented", fg="red", err=True)
    raise click.Abort()

"""
Main CLI entry point and command group setup.

This module defines the root CLI group and registers all subcommands.
"""

import click

from orchestrator.context import OrchestratorContext
from orchestrator.commands.bootstrap import bootstrap
from orchestrator.commands.provision import provision
from orchestrator.commands.configure import configure
from orchestrator.commands.deploy import deploy
from orchestrator.commands.sync import sync_config


@click.group()
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output",
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug mode",
)
@click.pass_context
def cli(ctx: click.Context, verbose: bool, debug: bool) -> None:
    """
    Racknarok Infrastructure Orchestrator.

    Coordinate deployment workflows across Ansible, Pulumi, and deploy-rs.
    """
    # Initialize shared context object
    ctx.obj = OrchestratorContext(verbose=verbose, debug=debug)

    if debug:
        click.echo("Debug mode enabled", err=True)


# Register commands
cli.add_command(bootstrap)
cli.add_command(provision)
cli.add_command(configure)
cli.add_command(deploy)
cli.add_command(sync_config)


def main() -> None:
    """Entry point for console script."""
    cli()


if __name__ == "__main__":
    main()

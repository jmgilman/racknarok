"""
Main CLI entry point and command group setup.

This module defines the root CLI group and registers all subcommands.
"""

import click

from orchestrator.context import OrchestratorContext
from orchestrator.commands.node import node
from orchestrator.commands.config import config
from orchestrator.commands.provision import provision
from orchestrator.commands.configure import configure
from orchestrator.commands.deploy import deploy


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


# Register command groups
cli.add_command(node)
cli.add_command(config)

# Register remaining standalone commands
# TODO: These will be organized into groups in future iterations
cli.add_command(provision)
cli.add_command(configure)
cli.add_command(deploy)


def main() -> None:
    """Entry point for console script."""
    cli()


if __name__ == "__main__":
    main()

"""
Configuration management commands.

Commands for managing configuration and secrets synchronization.
"""

import click

from orchestrator.context import pass_orchestrator_context


@click.group()
@pass_orchestrator_context
def config(ctx):
    """Manage configuration."""
    pass


# Import and register subcommands
from orchestrator.commands.config.sync import sync

config.add_command(sync)

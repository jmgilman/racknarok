"""
Node management commands.

Commands for managing Proxmox nodes: bootstrap, setup, and configuration.
"""

import click

from orchestrator.context import pass_orchestrator_context


@click.group()
@pass_orchestrator_context
def node(ctx):
    """Manage Proxmox nodes."""
    pass


# Import and register subcommands
from orchestrator.commands.node.bootstrap import bootstrap
from orchestrator.commands.node.setup import setup

node.add_command(bootstrap)
node.add_command(setup)

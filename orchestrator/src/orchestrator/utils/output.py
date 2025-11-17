"""
Pretty output formatting utilities.

Provides consistent, colorful output formatting for the CLI.
"""

import click
from typing import Any


def print_header(text: str) -> None:
    """
    Print a styled header.

    Args:
        text: Header text to display
    """
    click.secho(f"\n{'=' * 60}", fg="blue", bold=True)
    click.secho(f"  {text}", fg="blue", bold=True)
    click.secho(f"{'=' * 60}\n", fg="blue", bold=True)


def print_step(step_num: int, text: str) -> None:
    """
    Print a numbered step.

    Args:
        step_num: Step number
        text: Step description
    """
    click.secho(f"[{step_num}] ", fg="cyan", bold=True, nl=False)
    click.echo(text)


def print_success(text: str) -> None:
    """
    Print a success message.

    Args:
        text: Success message
    """
    click.secho("✓ ", fg="green", bold=True, nl=False)
    click.echo(text)


def print_error(text: str) -> None:
    """
    Print an error message.

    Args:
        text: Error message
    """
    click.secho("✗ ", fg="red", bold=True, nl=False)
    click.echo(text, err=True)


def print_warning(text: str) -> None:
    """
    Print a warning message.

    Args:
        text: Warning message
    """
    click.secho("⚠ ", fg="yellow", bold=True, nl=False)
    click.echo(text)


def print_info(text: str) -> None:
    """
    Print an info message.

    Args:
        text: Info message
    """
    click.secho("ℹ ", fg="blue", nl=False)
    click.echo(text)


def print_table(headers: list[str], rows: list[list[Any]]) -> None:
    """
    Print a simple table.

    Args:
        headers: Column headers
        rows: Table rows (list of lists)
    """
    # TODO: Implement simple table formatting
    # - Calculate column widths
    # - Print header row
    # - Print separator
    # - Print data rows
    # - Consider using rich library for better tables in the future
    raise NotImplementedError("Table formatting not yet implemented")


def confirm_action(message: str, default: bool = False) -> bool:
    """
    Prompt user for confirmation.

    Args:
        message: Confirmation prompt message
        default: Default value if user just presses enter

    Returns:
        True if user confirmed, False otherwise
    """
    return click.confirm(message, default=default)

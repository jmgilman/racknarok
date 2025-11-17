"""
Pulumi Automation API wrapper.

Provides a clean interface for running Pulumi projects programmatically.
"""

import subprocess
from pathlib import Path
from typing import Any

import click


def run_pulumi_project(
    project_path: Path,
    stack_name: str,
    operation: str = "up",
    preview_only: bool = False,
    config: dict[str, Any] | None = None,
) -> bool:
    """
    Execute a Pulumi project using the Automation API.

    Args:
        project_path: Path to the Pulumi project directory
        stack_name: Name of the stack to operate on
        operation: Operation to perform ('up', 'preview', 'destroy')
        preview_only: If True, only preview changes without applying
        config: Optional configuration to set on the stack

    Returns:
        True if operation succeeded, False otherwise

    Raises:
        PulumiError: If operation fails critically
    """
    if not validate_project_exists(project_path):
        raise PulumiError(f"Pulumi project not found at: {project_path}")

    # Ensure stack exists
    _ensure_stack_exists(project_path, stack_name)

    # Build command
    if preview_only or operation == "preview":
        cmd = ["pulumi", "preview", "--stack", stack_name]
    elif operation == "up":
        cmd = ["pulumi", "up", "--stack", stack_name, "--yes"]
    elif operation == "destroy":
        cmd = ["pulumi", "destroy", "--stack", stack_name, "--yes"]
    else:
        raise ValueError(f"Unknown operation: {operation}")

    # Run command
    result = subprocess.run(
        cmd,
        cwd=project_path,
        capture_output=False,  # Stream to console
        text=True,
    )

    return result.returncode == 0


def get_stack_outputs(project_path: Path, stack_name: str) -> dict[str, Any]:
    """
    Get outputs from a Pulumi stack.

    Args:
        project_path: Path to the Pulumi project directory
        stack_name: Name of the stack

    Returns:
        Dictionary of stack outputs

    Raises:
        PulumiError: If stack outputs cannot be retrieved
    """
    import json

    result = subprocess.run(
        ["pulumi", "stack", "output", "--json", "--stack", stack_name],
        cwd=project_path,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise PulumiError(f"Failed to get stack outputs: {result.stderr}")

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise PulumiError(f"Failed to parse stack outputs: {e}")


def validate_project_exists(project_path: Path) -> bool:
    """
    Check if a Pulumi project exists at the given path.

    Args:
        project_path: Path to check for Pulumi project

    Returns:
        True if Pulumi.yaml exists at path, False otherwise
    """
    return (project_path / "Pulumi.yaml").exists()


def _ensure_stack_exists(project_path: Path, stack_name: str) -> None:
    """
    Ensure a Pulumi stack exists, creating it if necessary.

    Args:
        project_path: Path to the Pulumi project directory
        stack_name: Name of the stack
    """
    # Check if stack exists
    result = subprocess.run(
        ["pulumi", "stack", "ls", "--json"],
        cwd=project_path,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        # If listing fails, try to create the stack anyway
        click.echo(f"Creating stack: {stack_name}")
        result = subprocess.run(
            ["pulumi", "stack", "init", stack_name],
            cwd=project_path,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise PulumiError(f"Failed to create stack: {result.stderr}")
        return

    import json

    try:
        stacks = json.loads(result.stdout)
        stack_names = [s["name"] for s in stacks]

        if stack_name not in stack_names:
            click.echo(f"Creating stack: {stack_name}")
            result = subprocess.run(
                ["pulumi", "stack", "init", stack_name],
                cwd=project_path,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                raise PulumiError(f"Failed to create stack: {result.stderr}")
    except json.JSONDecodeError:
        # If JSON parsing fails, assume stack doesn't exist and try to create
        click.echo(f"Creating stack: {stack_name}")
        result = subprocess.run(
            ["pulumi", "stack", "init", stack_name],
            cwd=project_path,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0 and "already exists" not in result.stderr:
            raise PulumiError(f"Failed to create stack: {result.stderr}")


class PulumiError(Exception):
    """Raised when Pulumi operations fail."""

    pass

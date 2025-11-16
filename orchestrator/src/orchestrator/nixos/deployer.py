"""
NixOS deployment wrapper for deploy-rs.

Provides a clean interface for deploying NixOS configurations.
"""

from pathlib import Path
from typing import Any


def deploy_nixos_config(
    config_path: Path,
    target: str | None = None,
    dry_run: bool = False,
    verbose: bool = False,
) -> bool:
    """
    Deploy NixOS configuration using deploy-rs.

    Args:
        config_path: Path to the NixOS flake directory
        target: Optional specific target to deploy (e.g., 'tailscale-router')
        dry_run: If True, build but don't activate
        verbose: Enable verbose output

    Returns:
        True if deployment succeeded, False otherwise

    Raises:
        NixOSDeployError: If deployment fails critically
    """
    # TODO: Implement deploy-rs execution
    # - Validate flake.nix exists at config_path
    # - Build deploy-rs command
    # - Add target if specified (.#target)
    # - Add --dry-activate if dry_run
    # - Execute deploy-rs
    # - Stream output to console
    # - Return success/failure
    raise NotImplementedError("NixOS deployment not yet implemented")


def list_deploy_targets(config_path: Path) -> list[str]:
    """
    List available deploy-rs targets from a flake.

    Args:
        config_path: Path to the NixOS flake directory

    Returns:
        List of available target names

    Raises:
        NixOSDeployError: If targets cannot be listed
    """
    # TODO: Parse flake.nix or use nix flake show
    # - Run: nix flake show --json
    # - Extract deploy-rs nodes
    # - Return list of target names
    raise NotImplementedError("Target listing not yet implemented")


def validate_flake_exists(config_path: Path) -> bool:
    """
    Check if a NixOS flake exists at the given path.

    Args:
        config_path: Path to check for NixOS flake

    Returns:
        True if flake.nix exists, False otherwise
    """
    # TODO: Check if flake.nix exists
    return (config_path / "flake.nix").exists()


class NixOSDeployError(Exception):
    """Raised when NixOS deployment fails."""

    pass

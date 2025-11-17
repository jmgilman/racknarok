"""
NixOS deployment wrapper for nixos-anywhere and deploy-rs.

Provides a clean interface for installing and deploying NixOS configurations.
"""

import subprocess
import time
from pathlib import Path

import click


def check_nixos_installed(host: str, user: str = "root", timeout: int = 5) -> bool:
    """
    Check if NixOS is already installed on a target host.

    Args:
        host: IP address or hostname of target
        user: SSH user (default: root)
        timeout: SSH connection timeout in seconds

    Returns:
        True if NixOS is installed, False otherwise
    """
    result = subprocess.run(
        [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", f"ConnectTimeout={timeout}",
            f"{user}@{host}",
            "test", "-f", "/etc/NIXOS",
        ],
        capture_output=True,
        timeout=timeout + 5,
    )

    return result.returncode == 0


def wait_for_ssh(
    host: str,
    user: str = "root",
    max_attempts: int = 30,
    delay: int = 10,
) -> bool:
    """
    Wait for SSH to become available on a host.

    Args:
        host: IP address or hostname of target
        user: SSH user (default: root)
        max_attempts: Maximum number of connection attempts
        delay: Delay between attempts in seconds

    Returns:
        True if SSH became available, False if timeout
    """
    click.echo(f"Waiting for SSH on {host}...")

    for attempt in range(1, max_attempts + 1):
        result = subprocess.run(
            [
                "ssh",
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", "ConnectTimeout=5",
                f"{user}@{host}",
                "echo", "ready",
            ],
            capture_output=True,
            timeout=10,
        )

        if result.returncode == 0:
            click.secho(f"✓ SSH available on {host}", fg="green")
            return True

        if attempt < max_attempts:
            click.echo(f"  Attempt {attempt}/{max_attempts} failed, retrying in {delay}s...")
            time.sleep(delay)

    click.secho(f"✗ SSH timeout on {host}", fg="red")
    return False


def install_nixos_anywhere(
    flake_path: Path,
    target_host: str,
    hostname: str,
    verbose: bool = False,
) -> bool:
    """
    Install NixOS on a target host using nixos-anywhere.

    WARNING: This is a DESTRUCTIVE operation. The target system will be
    completely reformatted and NixOS will be installed.

    Args:
        flake_path: Path to NixOS flake directory
        target_host: IP address or hostname of target
        hostname: NixOS hostname (must match flake config)
        verbose: Enable verbose output

    Returns:
        True if installation succeeded

    Raises:
        NixOSDeployError: If installation fails
    """
    # Check if NixOS already installed
    if check_nixos_installed(target_host):
        click.secho(f"NixOS already installed on {target_host}, skipping installation", fg="yellow")
        return True

    # Build nixos-anywhere command
    cmd = [
        "nix", "run", "github:nix-community/nixos-anywhere", "--",
        "--flake", f"{flake_path}#{hostname}",
        f"root@{target_host}",
    ]

    if verbose:
        cmd.append("--debug")

    click.echo(f"Installing NixOS on {target_host}...")
    click.echo("This may take 10-20 minutes...")

    # Run nixos-anywhere
    result = subprocess.run(
        cmd,
        cwd=flake_path,
        env={"SHELL": "/bin/sh"},
        capture_output=not verbose,
        text=True,
    )

    if result.returncode != 0:
        error_msg = result.stderr if not verbose else "Check output above"
        raise NixOSDeployError(f"nixos-anywhere failed: {error_msg}")

    click.secho(f"✓ NixOS installed on {target_host}", fg="green")
    return True


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
    if not validate_flake_exists(config_path):
        raise NixOSDeployError(f"NixOS flake not found at: {config_path}")

    # Build deploy-rs command
    cmd = ["nix", "run", "github:serokell/deploy-rs", "--"]

    if target:
        cmd.extend(["--targets", f".#{target}"])

    if dry_run:
        cmd.append("--dry-activate")

    click.echo(f"Deploying NixOS configuration{f' to {target}' if target else ''}...")

    # Run deploy-rs
    result = subprocess.run(
        cmd,
        cwd=config_path,
        capture_output=not verbose,
        text=True,
    )

    if result.returncode != 0:
        error_msg = result.stderr if not verbose else "Check output above"
        raise NixOSDeployError(f"deploy-rs failed: {error_msg}")

    click.secho(f"✓ Configuration deployed{f' to {target}' if target else ''}", fg="green")
    return True


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
    import json

    result = subprocess.run(
        ["nix", "flake", "show", "--json"],
        cwd=config_path,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise NixOSDeployError(f"Failed to list targets: {result.stderr}")

    try:
        flake_info = json.loads(result.stdout)
        # Extract deploy.nodes from flake output
        deploy_nodes = flake_info.get("deploy", {}).get("nodes", {})
        return list(deploy_nodes.keys())
    except (json.JSONDecodeError, KeyError) as e:
        raise NixOSDeployError(f"Failed to parse flake output: {e}")


def validate_flake_exists(config_path: Path) -> bool:
    """
    Check if a NixOS flake exists at the given path.

    Args:
        config_path: Path to check for NixOS flake

    Returns:
        True if flake.nix exists, False otherwise
    """
    return (config_path / "flake.nix").exists()


class NixOSDeployError(Exception):
    """Raised when NixOS deployment fails."""

    pass

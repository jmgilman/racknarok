"""
SSH key management utilities.

Handles loading SSH keys from ESC and adding them to ssh-agent.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def setup_ssh_agent(ssh_key: str, key_name: str = "orchestrator") -> bool:
    """
    Add an SSH key to ssh-agent.

    Args:
        ssh_key: SSH private key content (PEM format)
        key_name: Name for the key (used in temp file naming)

    Returns:
        True if key was added successfully, False otherwise

    Raises:
        SSHError: If ssh-agent is not running or key cannot be added
    """
    # Check if ssh-agent is running
    agent_status = get_ssh_agent_status()
    if not agent_status["running"]:
        raise SSHError(
            "ssh-agent is not running. Please start ssh-agent first.\n"
            "Run: eval $(ssh-agent -s)"
        )

    # Create a temporary file for the SSH key with secure permissions
    # We use NamedTemporaryFile with delete=False so we can control when it's deleted
    try:
        with tempfile.NamedTemporaryFile(
            mode='w',
            prefix=f'orchestrator_{key_name}_',
            suffix='.key',
            delete=False
        ) as key_file:
            key_path = Path(key_file.name)
            # Write the key content
            key_file.write(ssh_key)
            # Ensure newline at end if not present
            if not ssh_key.endswith('\n'):
                key_file.write('\n')

        # Set secure permissions (0600 = rw-------)
        key_path.chmod(0o600)

        # Add key to ssh-agent
        try:
            result = subprocess.run(
                ['ssh-add', str(key_path)],
                capture_output=True,
                text=True,
                check=True
            )
            return True
        except subprocess.CalledProcessError as e:
            raise SSHError(
                f"Failed to add SSH key to agent: {e.stderr}"
            ) from e
    finally:
        # Clean up temporary key file
        if key_path.exists():
            key_path.unlink()

    return False


def verify_ssh_connectivity(host: str, user: str = "root", port: int = 22) -> bool:
    """
    Verify SSH connectivity to a host.

    Args:
        host: Hostname or IP address
        user: SSH user
        port: SSH port

    Returns:
        True if SSH connection successful, False otherwise
    """
    try:
        # Use BatchMode to prevent interactive prompts
        # Use ConnectTimeout to fail quickly if host is unreachable
        # StrictHostKeyChecking=no for initial bootstrap (can be tightened later)
        result = subprocess.run(
            [
                'ssh',
                '-o', 'BatchMode=yes',
                '-o', 'ConnectTimeout=5',
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'UserKnownHostsFile=/dev/null',
                '-p', str(port),
                f'{user}@{host}',
                'exit'
            ],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        return False


def get_ssh_agent_status() -> dict[str, Any]:
    """
    Get the status of ssh-agent.

    Returns:
        Dictionary with agent status information:
        - running: bool
        - pid: int or None
        - num_keys: int
    """
    # Check if SSH_AUTH_SOCK is set (indicates ssh-agent is configured)
    auth_sock = os.getenv('SSH_AUTH_SOCK')
    if not auth_sock:
        return {
            'running': False,
            'pid': None,
            'num_keys': 0
        }

    # Try to list keys to verify agent is actually responsive
    try:
        result = subprocess.run(
            ['ssh-add', '-l'],
            capture_output=True,
            text=True,
            timeout=5
        )

        # ssh-add -l returns:
        # - 0: agent has keys
        # - 1: agent has no keys
        # - 2: agent not running or error
        if result.returncode == 2:
            return {
                'running': False,
                'pid': None,
                'num_keys': 0
            }

        # Count number of keys (each line is one key)
        num_keys = 0
        if result.returncode == 0:
            # Only count non-empty lines
            num_keys = len([line for line in result.stdout.split('\n') if line.strip()])

        # Try to get agent PID from environment
        agent_pid = os.getenv('SSH_AGENT_PID')
        pid = int(agent_pid) if agent_pid else None

        return {
            'running': True,
            'pid': pid,
            'num_keys': num_keys
        }
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, ValueError):
        return {
            'running': False,
            'pid': None,
            'num_keys': 0
        }


class SSHError(Exception):
    """Raised when SSH operations fail."""

    pass

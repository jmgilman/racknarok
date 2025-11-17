"""
Ansible execution wrapper using ansible-runner.

Provides a clean interface for running Ansible roles with dynamic inventory.
"""

import os
import tempfile
from pathlib import Path
from typing import Any

import ansible_runner


def run_ansible_role(
    role_name: str,
    inventory: dict[str, Any],
    extra_vars: dict[str, Any] | None = None,
    verbose: bool = False,
) -> bool:
    """
    Execute an Ansible role using ansible-runner.

    Args:
        role_name: Name of the role to execute (e.g., 'proxmox-bootstrap')
        inventory: Ansible inventory dictionary
        extra_vars: Optional additional variables to pass to the role
        verbose: Enable verbose output

    Returns:
        True if role execution succeeded, False otherwise

    Raises:
        AnsibleError: If role execution fails critically
    """
    # Validate role exists
    if not validate_role_exists(role_name):
        raise AnsibleError(f"Role '{role_name}' not found in ansible/roles/")

    # Prepare extra_vars
    extravars = extra_vars or {}

    # Set verbosity level (0-4, maps to -v, -vv, -vvv, -vvvv)
    verbosity = 2 if verbose else 0

    # Get project root (assuming orchestrator is in PROJECT_ROOT/orchestrator/)
    project_root = Path(__file__).parent.parent.parent.parent.parent
    ansible_dir = project_root / "ansible"

    # Create temporary directory for ansible-runner artifacts
    with tempfile.TemporaryDirectory(prefix="ansible-runner-") as tmpdir:
        # Execute role using ansible-runner
        # ansible-runner can execute roles directly without a playbook
        result = ansible_runner.run(
            private_data_dir=str(tmpdir),
            roles_path=str(ansible_dir / "roles"),
            role=role_name,
            inventory=inventory,
            extravars=extravars,
            verbosity=verbosity,
            quiet=False,
            # Stream output to console
            event_handler=_event_handler if verbose else None,
        )

        # Check result
        if result.rc != 0:
            raise AnsibleError(
                f"Ansible role '{role_name}' failed with return code {result.rc}\n"
                f"Status: {result.status}\n"
                f"See output above for details"
            )

        return result.status == "successful"


def _event_handler(event: dict[str, Any]) -> None:
    """
    Handle Ansible events for real-time output.

    Args:
        event: Ansible event dictionary
    """
    # Only print task events
    if event.get("event") in ["runner_on_ok", "runner_on_failed", "runner_on_unreachable"]:
        if stdout := event.get("stdout"):
            print(stdout)


def validate_role_exists(role_name: str) -> bool:
    """
    Check if an Ansible role exists in the ansible/roles directory.

    Args:
        role_name: Name of the role to check

    Returns:
        True if role exists, False otherwise
    """
    # Get project root
    project_root = Path(__file__).parent.parent.parent.parent.parent
    ansible_dir = project_root / "ansible"
    role_path = ansible_dir / "roles" / role_name

    # Check if role directory exists and has at least a tasks/main.yml
    return role_path.is_dir() and (role_path / "tasks" / "main.yml").exists()


class AnsibleError(Exception):
    """Raised when Ansible execution fails."""

    pass

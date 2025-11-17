"""
SOPS utilities for managing encrypted secrets.

Handles reading and updating SOPS-encrypted YAML files.
"""

import subprocess
import tempfile
from pathlib import Path
from typing import Any

import yaml


class SopsError(Exception):
    """Raised when SOPS operations fail."""

    pass


def update_sops_file(
    file_path: Path,
    updates: dict[str, Any],
    create_if_missing: bool = False,
) -> None:
    """
    Update values in a SOPS-encrypted YAML file.

    This function uses SOPS to decrypt, update, and re-encrypt a file.
    It supports nested key updates using dot notation.

    Args:
        file_path: Path to the SOPS-encrypted YAML file
        updates: Dictionary of key-value pairs to update
                Keys can use dot notation for nested values (e.g., 'api.nodes.rk1.token_id')
        create_if_missing: Create the file if it doesn't exist

    Raises:
        SopsError: If SOPS operations fail

    Example:
        >>> update_sops_file(
        ...     Path("secrets/proxmox/api.enc.yaml"),
        ...     {
        ...         "api.nodes.rk1.token_id": "automation@pve!infra",
        ...         "api.nodes.rk1.token_secret": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        ...     }
        ... )
    """
    if not file_path.exists():
        if create_if_missing:
            # Create an empty encrypted file
            _create_empty_sops_file(file_path)
        else:
            raise SopsError(f"File not found: {file_path}")

    # Get the directory containing the file (for running sops from correct location)
    file_dir = file_path.parent
    file_name = file_path.name

    # Create a temporary file in the same directory as the original
    # This ensures SOPS can find .sops.yaml in the parent directories
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, dir=file_dir
    ) as temp_file:
        temp_path = Path(temp_file.name)

    try:
        # Step 1: Decrypt the file
        result = subprocess.run(
            ["sops", "--decrypt", str(file_path)],
            capture_output=True,
            text=True,
            check=True,
            cwd=file_dir,  # Run from file directory
        )

        # Step 2: Parse the decrypted YAML
        data = yaml.safe_load(result.stdout) or {}

        # Step 3: Apply updates
        for key, value in updates.items():
            _set_nested_value(data, key, value)

        # Step 4: Write updated data to temporary file
        with open(temp_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        # Step 5: Encrypt the temporary file in place
        # Running from file_dir ensures .sops.yaml is found
        subprocess.run(
            [
                "sops",
                "--encrypt",
                "--in-place",
                temp_path.name,  # Use relative path
            ],
            capture_output=True,
            text=True,
            check=True,
            cwd=file_dir,  # Run from file directory so .sops.yaml is found
        )

        # Step 6: Replace original file with encrypted temp file
        temp_path.replace(file_path)

    except subprocess.CalledProcessError as e:
        raise SopsError(f"SOPS command failed: {e.stderr}") from e
    except yaml.YAMLError as e:
        raise SopsError(f"YAML parsing error: {e}") from e
    except Exception as e:
        raise SopsError(f"Unexpected error: {e}") from e
    finally:
        # Clean up temp file if it still exists
        if temp_path.exists():
            temp_path.unlink()


def read_sops_file(file_path: Path) -> dict[str, Any]:
    """
    Read and decrypt a SOPS-encrypted YAML file.

    Args:
        file_path: Path to the SOPS-encrypted YAML file

    Returns:
        Decrypted data as a dictionary

    Raises:
        SopsError: If decryption fails
    """
    try:
        result = subprocess.run(
            ["sops", "--decrypt", str(file_path)],
            capture_output=True,
            text=True,
            check=True,
        )

        data = yaml.safe_load(result.stdout) or {}
        return data

    except subprocess.CalledProcessError as e:
        raise SopsError(f"SOPS decryption failed: {e.stderr}") from e
    except yaml.YAMLError as e:
        raise SopsError(f"YAML parsing error: {e}") from e


def _set_nested_value(data: dict, key: str, value: Any) -> None:
    """
    Set a nested value in a dictionary using dot notation.

    Args:
        data: Dictionary to update
        key: Key path using dot notation (e.g., 'api.nodes.rk1.token_id')
        value: Value to set

    Example:
        >>> data = {}
        >>> _set_nested_value(data, 'api.nodes.rk1.token_id', 'test')
        >>> print(data)
        {'api': {'nodes': {'rk1': {'token_id': 'test'}}}}
    """
    keys = key.split(".")
    current = data

    # Navigate/create nested structure
    for k in keys[:-1]:
        if k not in current:
            current[k] = {}
        elif not isinstance(current[k], dict):
            # If the key exists but isn't a dict, we can't navigate further
            raise SopsError(
                f"Cannot set nested value: '{k}' in path '{key}' is not a dictionary"
            )
        current = current[k]

    # Set the final value
    current[keys[-1]] = value


def _create_empty_sops_file(file_path: Path) -> None:
    """
    Create an empty SOPS-encrypted YAML file.

    Args:
        file_path: Path where the file should be created

    Raises:
        SopsError: If file creation fails
    """
    # Ensure parent directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Create empty YAML
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False
    ) as temp_file:
        temp_path = Path(temp_file.name)
        yaml.dump({}, temp_file, default_flow_style=False)

    try:
        # Encrypt the empty file
        subprocess.run(
            ["sops", "--encrypt", str(temp_path)],
            capture_output=True,
            text=True,
            check=True,
        )

        # Move encrypted file to final location
        temp_path.replace(file_path)

    except subprocess.CalledProcessError as e:
        raise SopsError(f"Failed to create encrypted file: {e.stderr}") from e
    finally:
        if temp_path.exists():
            temp_path.unlink()

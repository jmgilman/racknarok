"""
Pulumi ESC configuration loading and management.

This module handles loading configuration and secrets from Pulumi ESC
environments.
"""

import json
import os
from pathlib import Path
from typing import Any

import pulumi_esc_sdk as esc


def _extract_esc_values(data: Any) -> Any:
    """
    Extract actual values from ESC format, removing metadata like ranges, schemas, etc.

    ESC returns values in a structured format with metadata. This function recursively
    extracts just the actual configuration values.

    Args:
        data: ESC format data (dict, list, or literal value)

    Returns:
        Extracted values as plain Python objects (dict, list, str, int, etc.)
    """
    if isinstance(data, dict):
        # If it has 'literal' key, return that value
        if 'literal' in data:
            return data['literal']

        # If it has 'object' key, recursively extract from that
        if 'object' in data:
            return _extract_esc_values(data['object'])

        # If it has 'list' key, recursively extract from that
        if 'list' in data:
            return _extract_esc_values(data['list'])

        # If it has 'exprs' key (top-level ESC format), extract from that
        if 'exprs' in data:
            return _extract_esc_values(data['exprs'])

        # Otherwise, recursively process all keys
        result = {}
        for key, value in data.items():
            # Skip metadata keys
            if key in ('range', 'schema', 'keyRanges', 'builtin', 'nameRange', 'argSchema', 'arg'):
                continue
            result[key] = _extract_esc_values(value)
        return result

    elif isinstance(data, list):
        # Recursively extract from list items
        return [_extract_esc_values(item) for item in data]

    else:
        # Return literals as-is
        return data


def _get_pulumi_access_token() -> str:
    """
    Get Pulumi access token from environment or credentials file.

    Returns:
        Access token string

    Raises:
        ConfigError: If no token can be found
    """
    # Check environment variable first
    token = os.getenv("PULUMI_ACCESS_TOKEN")
    if token:
        return token

    # Try to read from Pulumi credentials file
    creds_path = Path.home() / ".pulumi" / "credentials.json"
    if creds_path.exists():
        try:
            with open(creds_path) as f:
                creds = json.load(f)
                # Get token for api.pulumi.com
                tokens = creds.get("accessTokens", {})
                token = tokens.get("https://api.pulumi.com")
                if token:
                    return token
        except (json.JSONDecodeError, IOError) as e:
            raise ConfigError(f"Failed to read Pulumi credentials: {e}") from e

    raise ConfigError(
        "No Pulumi access token found. Run 'pulumi login' or set PULUMI_ACCESS_TOKEN"
    )


def load_esc_config(
    environment: str,
    project: str = "racknarok",
    org: str = "jmgilman"
) -> dict[str, Any]:
    """
    Load configuration from a Pulumi ESC environment.

    Args:
        environment: Name of the ESC environment (e.g., 'proxmox', 'tailscale')
        project: Pulumi project name (defaults to 'racknarok')
        org: Pulumi organization name (defaults to 'jmgilman')

    Returns:
        Dictionary containing the environment configuration

    Raises:
        ConfigError: If the environment cannot be loaded

    Example:
        >>> config = load_esc_config("proxmox")
        >>> print(config)
    """
    try:
        # Get access token from environment or credentials file
        access_token = _get_pulumi_access_token()

        # Create ESC client with authentication
        configuration = esc.Configuration(access_token=access_token)
        client = esc.EscClient(configuration)

        # Open and read the environment
        # ESC environments are organized as: org/project/environment
        # Returns tuple: (Environment, values_dict, raw_yaml_str)
        # We want the second element - the evaluated/decrypted values
        env_obj, values, raw_yaml = client.open_and_read_environment(org, project, environment)

        # The values should already be a dictionary with evaluated/decrypted values
        if isinstance(values, dict):
            return values["pulumiConfig"]
        # If it's a Mapping but not a dict, convert it
        elif hasattr(values, 'items'):
            return dict(values)["pulumiConfig"]
        else:
            raise ConfigError(
                f"Unexpected values type from ESC: {type(values)}"
            )
    except Exception as e:
        raise ConfigError(
            f"Failed to load ESC environment '{org}/{project}/{environment}': {e}"
        ) from e


def get_config_value(config: dict[str, Any], key: str, default: Any = None) -> Any:
    """
    Get a configuration value from loaded ESC config.

    Supports nested key access using dot notation (e.g., 'proxmox.api.token').

    Args:
        config: Configuration dictionary from load_esc_config
        key: Configuration key (supports dot notation for nested values)
        default: Default value if key not found

    Returns:
        Configuration value or default

    Example:
        >>> config = {"proxmox": {"api": {"token": "secret"}}}
        >>> get_config_value(config, "proxmox.api.token")
        'secret'
        >>> get_config_value(config, "missing.key", "default_value")
        'default_value'
    """
    keys = key.split(".")
    value = config

    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return default

    return value


def sync_config_to_esc(
    environment: str,
    config_data: dict[str, Any],
    org: str = "jmgilman",
) -> None:
    """
    Sync configuration data to a Pulumi ESC environment.

    Used by the sync-config command to update ESC environments from Git.

    Args:
        environment: Name of the ESC environment to update
        config_data: Configuration data to sync
        org: Pulumi organization name

    Raises:
        ConfigError: If sync fails
    """
    # TODO: Implement ESC sync logic
    # - Authenticate to Pulumi Cloud
    # - Update ESC environment with provided data
    # - Handle errors and validation
    raise NotImplementedError("ESC sync not yet implemented")


class ConfigError(Exception):
    """Raised when configuration loading or access fails."""

    pass

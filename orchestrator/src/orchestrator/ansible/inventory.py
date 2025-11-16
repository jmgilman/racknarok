"""
Dynamic Ansible inventory generation from ESC configuration.

Generates Ansible inventory data structures from Pulumi ESC config.
"""

from typing import Any


def generate_inventory(config: dict[str, Any], target_node: str | None = None) -> dict[str, Any]:
    """
    Generate Ansible inventory from ESC configuration.

    Args:
        config: ESC configuration dictionary (from config.load_esc_config)
        target_node: Optional specific node to target (filters inventory)

    Returns:
        Ansible inventory dictionary in the format expected by ansible-runner

    Example inventory structure:
        {
            "all": {
                "hosts": {
                    "proxmox-01": {
                        "ansible_host": "10.0.0.10",
                        "ansible_user": "root",
                        ...
                    }
                },
                "vars": {
                    "ansible_python_interpreter": "/usr/bin/python3"
                }
            }
        }
    """
    inventory = {
        "all": {
            "hosts": {},
            "vars": {
                "ansible_python_interpreter": "/usr/bin/python3",
            }
        }
    }

    # Extract nodes from config
    # Config structure: config['nodes'][node_name] = {...} (primary)
    # Or fallback to: config['api']['nodes'][node_name] = {...} (API endpoints only)
    # Nodes can be either a dict or a list
    # Note: Prefer top-level 'nodes' as it has full node config including ssh_host
    nodes_raw = config.get("nodes", {}) or config.get("api", {}).get("nodes", {})

    if not nodes_raw:
        raise ValueError("No nodes found in configuration (expected under 'api.nodes' or 'nodes')")

    # Normalize nodes to a dictionary format
    # If it's a list, convert to dict keyed by node name
    if isinstance(nodes_raw, list):
        nodes = {node["name"]: node for node in nodes_raw if "name" in node}
    elif isinstance(nodes_raw, dict):
        nodes = nodes_raw
    else:
        raise ValueError(f"'nodes' configuration must be a dictionary or list, got {type(nodes_raw).__name__}")

    for node_name, node_config in nodes.items():
        # Skip if filtering to a specific node and this isn't it
        if target_node and node_name != target_node:
            continue

        # Build host configuration
        host_vars = get_host_vars(config, node_name, node_config)

        # Add to inventory
        inventory["all"]["hosts"][node_name] = host_vars

    # If target_node specified and not found, raise error
    if target_node and target_node not in inventory["all"]["hosts"]:
        raise ValueError(f"Node '{target_node}' not found in configuration")

    return inventory


def get_host_vars(config: dict[str, Any], hostname: str, node_config: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Get host-specific variables for an Ansible target.

    Args:
        config: ESC configuration dictionary
        hostname: Hostname to get variables for
        node_config: Optional node configuration dict (if already retrieved)

    Returns:
        Dictionary of host variables
    """
    # If node_config not provided, look it up
    if node_config is None:
        nodes_raw = config.get("nodes", {})
        # Handle both list and dict formats
        if isinstance(nodes_raw, list):
            nodes = {node["name"]: node for node in nodes_raw if "name" in node}
        else:
            nodes = nodes_raw

        node_config = nodes.get(hostname)
        if not node_config:
            raise ValueError(f"No configuration found for node '{hostname}'")

    # Determine SSH host
    # Priority: ssh_host > ssh.public_ip > fqdn > hostname
    ssh_host = (
        node_config.get("ssh_host")
        or node_config.get("ssh", {}).get("public_ip")
        or node_config.get("fqdn")
        or hostname
    )

    # Build Ansible host variables
    host_vars = {
        "ansible_host": ssh_host,
        "ansible_user": node_config.get("ssh_user", "root"),
        "ansible_port": node_config.get("ssh_port", 22),
    }

    # Add SSH key path if specified (will be in ssh-agent, but some modules need the path)
    if ssh_key_path := node_config.get("ssh_key_path"):
        host_vars["ansible_ssh_private_key_file"] = ssh_key_path

    # Add any additional node-specific variables
    # These can be used by roles
    if node_vars := node_config.get("vars"):
        host_vars.update(node_vars)

    return host_vars

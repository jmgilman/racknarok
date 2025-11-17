"""
Setup command for configuring Proxmox nodes.

Configures networking and storage on a bootstrapped Proxmox node.
"""

import json

import click

from orchestrator.context import pass_orchestrator_context, OrchestratorContext
from orchestrator.config import load_esc_config, get_config_value, ConfigError
from orchestrator.utils.ssh import setup_ssh_agent, get_ssh_agent_status, SSHError


def find_node_in_config(config: dict, node_name: str) -> dict | None:
    """
    Find a node configuration by name, handling both list and dict formats.

    Args:
        config: ESC configuration dictionary
        node_name: Name of the node to find

    Returns:
        Node configuration dict, or None if not found
    """
    nodes = config.get("nodes", [])

    # Handle list format
    if isinstance(nodes, list):
        for node in nodes:
            if node.get("name") == node_name:
                return node
        return None

    # Handle dict format
    elif isinstance(nodes, dict):
        return nodes.get(node_name)

    return None


def setup_ssh_authentication(ctx: OrchestratorContext, proxmox_config: dict, node_name: str) -> None:
    """
    Setup SSH agent with authentication for the node.

    Args:
        ctx: Orchestrator context
        proxmox_config: Proxmox configuration from ESC
        node_name: Name of the node

    Raises:
        click.Abort: If SSH setup fails
    """
    click.echo("🔑 Setting up SSH authentication...")

    try:
        agent_status = get_ssh_agent_status()
        if not agent_status["running"]:
            click.secho("✗ ssh-agent is not running", fg="red", err=True)
            click.echo("Please start ssh-agent with: eval $(ssh-agent -s)", err=True)
            raise click.Abort()

        if ctx.verbose:
            click.echo(f"  ssh-agent PID: {agent_status['pid']}")
            click.echo(f"  Current keys loaded: {agent_status['num_keys']}")

        ssh_key = get_config_value(proxmox_config, "ssh.admin.private_key")
        if not ssh_key or ssh_key == {}:
            click.secho("✗ SSH key not found in Proxmox configuration", fg="red", err=True)
            raise click.Abort()

        setup_ssh_agent(ssh_key, key_name=f"setup_{node_name}")
        click.secho("✓ SSH key added to agent", fg="green")

    except SSHError as e:
        click.secho(f"✗ SSH setup failed: {e}", fg="red", err=True)
        raise click.Abort()

    click.echo()
    click.secho("✓ SSH authentication configured", fg="green", bold=True)


def configure_networking(
    ctx: OrchestratorContext,
    proxmox_config: dict,
    node_name: str,
    node_config: dict,
) -> None:
    """
    Configure networking on the node.

    Args:
        ctx: Orchestrator context
        proxmox_config: Proxmox configuration from ESC
        node_name: Name of the node
        node_config: Node-specific configuration

    Raises:
        click.Abort: If networking configuration fails
    """
    click.echo()
    click.echo("🌐 Configuring networking...")

    # Extract network configuration
    network_config = node_config.get("network", {})
    vrack_config = network_config.get("vrack", {})

    if not vrack_config:
        click.secho(f"✗ No vRack configuration found for node '{node_name}'", fg="red", err=True)
        raise click.Abort()

    try:
        from orchestrator.ansible.inventory import generate_inventory
        from orchestrator.ansible.runner import run_ansible_role, AnsibleError

        # Generate inventory
        click.echo("  Generating Ansible inventory...")
        inventory = generate_inventory(proxmox_config, target_node=node_name)

        if ctx.verbose:
            click.echo()
            click.echo("Generated inventory:")
            click.echo(json.dumps(inventory, indent=2))
            click.echo()

        # Prepare extravars
        extravars = {
            "vrack_interface": vrack_config.get("interface"),
            "vrack_bridge": vrack_config.get("bridge"),
            "vrack_ip": vrack_config.get("ip"),
            "vrack_vlan_aware": vrack_config.get("vlan_aware", True),
            "vrack_mtu": network_config.get("mtu", 1500),
            "networking_verbose": ctx.verbose,
        }

        # Validate required variables
        missing_vars = []
        if not extravars.get("vrack_interface"):
            missing_vars.append("network.vrack.interface")
        if not extravars.get("vrack_bridge"):
            missing_vars.append("network.vrack.bridge")
        if not extravars.get("vrack_ip"):
            missing_vars.append("network.vrack.ip")

        if missing_vars:
            click.secho("✗ Missing required network configuration:", fg="red", err=True)
            for var in missing_vars:
                click.echo(f"  - {var}", err=True)
            raise click.Abort()

        if ctx.verbose:
            click.echo("Ansible extravars:")
            click.echo(json.dumps(extravars, indent=2))
            click.echo()

        # Run the proxmox-networking role
        click.echo("  Executing proxmox-networking role...")
        click.echo("  (This may take a few minutes)")
        click.echo()

        success = run_ansible_role(
            role_name="proxmox-networking",
            inventory=inventory,
            extra_vars=extravars,
            verbose=ctx.verbose,
        )

        if success:
            click.echo()
            click.secho("✓ Networking configuration completed successfully", fg="green", bold=True)
        else:
            click.secho("✗ Networking configuration failed", fg="red", err=True)
            raise click.Abort()

    except Exception as e:
        if isinstance(e, click.Abort):
            raise
        click.secho(f"✗ Unexpected error: {e}", fg="red", err=True)
        if ctx.verbose:
            import traceback
            click.echo(traceback.format_exc(), err=True)
        raise click.Abort()


def configure_storage(
    ctx: OrchestratorContext,
    proxmox_config: dict,
    node_name: str,
    node_config: dict,
    force: bool,
) -> None:
    """
    Configure storage on the node.

    Args:
        ctx: Orchestrator context
        proxmox_config: Proxmox configuration from ESC
        node_name: Name of the node
        node_config: Node-specific configuration
        force: Force creation even if disks contain data

    Raises:
        click.Abort: If storage configuration fails
    """
    click.echo()
    click.echo("💾 Configuring storage...")

    if force:
        click.secho("⚠️  WARNING: Force mode enabled - will overwrite existing data!", fg="yellow", bold=True)
        click.echo()

    # Extract storage configuration
    storage_pools = node_config.get("storage", [])

    if not storage_pools:
        click.secho(f"✗ No storage configuration found for node '{node_name}'", fg="red", err=True)
        raise click.Abort()

    click.echo(f"  Found {len(storage_pools)} storage pool(s) to configure:")
    for pool in storage_pools:
        click.echo(f"    - {pool.get('name')} ({pool.get('type')})")
    click.echo()

    try:
        from orchestrator.ansible.inventory import generate_inventory
        from orchestrator.ansible.runner import run_ansible_role, AnsibleError

        # Generate inventory
        click.echo("  Generating Ansible inventory...")
        inventory = generate_inventory(proxmox_config, target_node=node_name)

        if ctx.verbose:
            click.echo()
            click.echo("Generated inventory:")
            click.echo(json.dumps(inventory, indent=2))
            click.echo()

        # Prepare extravars
        extravars = {
            "storage_pools": storage_pools,
            "storage_force_create": force,
            "storage_verbose": ctx.verbose,
        }

        if ctx.verbose:
            click.echo("Ansible extravars:")
            click.echo(json.dumps(extravars, indent=2))
            click.echo()

        # Run the proxmox-storage role
        click.echo("  Executing proxmox-storage role...")
        click.echo("  (This may take several minutes)")
        click.echo()

        success = run_ansible_role(
            role_name="proxmox-storage",
            inventory=inventory,
            extra_vars=extravars,
            verbose=ctx.verbose,
        )

        if success:
            click.echo()
            click.secho("✓ Storage configuration completed successfully", fg="green", bold=True)
        else:
            click.secho("✗ Storage configuration failed", fg="red", err=True)
            raise click.Abort()

    except Exception as e:
        if isinstance(e, click.Abort):
            raise
        click.secho(f"✗ Unexpected error: {e}", fg="red", err=True)
        if ctx.verbose:
            import traceback
            click.echo(traceback.format_exc(), err=True)
        raise click.Abort()


@click.command(name="setup")
@click.argument("node_name")
@click.option(
    "--skip-networking",
    is_flag=True,
    help="Skip networking configuration",
)
@click.option(
    "--skip-storage",
    is_flag=True,
    help="Skip storage configuration",
)
@click.option(
    "--force-storage",
    is_flag=True,
    help="Force storage creation even if disks contain data (DANGEROUS!)",
)
@pass_orchestrator_context
def setup(
    ctx: OrchestratorContext,
    node_name: str,
    skip_networking: bool,
    skip_storage: bool,
    force_storage: bool,
) -> None:
    """
    Complete setup of a Proxmox node.

    Configures networking and storage on a bootstrapped node.
    This should be run after 'orchestrator node bootstrap' is complete.

    By default, both networking and storage are configured.
    Use --skip-networking or --skip-storage to configure only one.

    \b
    Examples:
        # Full setup (networking + storage)
        orchestrator node setup rk1

        # Only networking
        orchestrator node setup rk1 --skip-storage

        # Only storage
        orchestrator node setup rk1 --skip-networking

        # Force storage creation (overwrites existing)
        orchestrator node setup rk1 --force-storage
    """
    click.secho(f"⚙️  Setting up node: {node_name}", fg="cyan", bold=True)
    click.echo()

    # Check that at least one configuration is enabled
    if skip_networking and skip_storage:
        click.secho("✗ Cannot skip both networking and storage", fg="red", err=True)
        click.echo("Use --skip-networking OR --skip-storage, not both", err=True)
        raise click.Abort()

    # Phase 1: Load configuration from ESC
    click.echo("📋 Loading configuration from Pulumi ESC...")
    try:
        proxmox_config = load_esc_config("proxmox")
        click.secho("✓ Loaded Proxmox configuration", fg="green")

        if ctx.verbose:
            click.echo()
            click.echo("Proxmox Configuration:")
            click.echo(json.dumps(proxmox_config, indent=2))

    except ConfigError as e:
        click.secho(f"✗ Failed to load configuration: {e}", fg="red", err=True)
        raise click.Abort()

    # Find node configuration
    node_config = find_node_in_config(proxmox_config, node_name)
    if not node_config:
        click.secho(f"✗ Node '{node_name}' not found in configuration", fg="red", err=True)
        raise click.Abort()

    click.echo()
    click.secho("✓ Configuration loaded successfully", fg="green", bold=True)

    # Phase 2: Setup SSH agent
    click.echo()
    setup_ssh_authentication(ctx, proxmox_config, node_name)

    # Phase 3: Configure networking (if not skipped)
    if not skip_networking:
        configure_networking(ctx, proxmox_config, node_name, node_config)
    else:
        click.echo()
        click.secho("⏭️  Skipping networking configuration", fg="yellow")

    # Phase 4: Configure storage (if not skipped)
    if not skip_storage:
        configure_storage(ctx, proxmox_config, node_name, node_config, force_storage)
    else:
        click.echo()
        click.secho("⏭️  Skipping storage configuration", fg="yellow")

    # Phase 5: Complete
    click.echo()
    click.secho("✓ Node setup completed!", fg="green", bold=True)

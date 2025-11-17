# ADR 002: Ansible for Proxmox Administration

## Status

Accepted

## Context

Project Racknarok uses Pulumi to manage Proxmox VMs, but the Proxmox Pulumi provider has significant gaps in functionality. Specifically, it lacks support for:
- Storage pool management (ZFS, LVM, directory storage)
- Advanced networking configuration beyond basic bridges
- System-level configuration (kernel parameters, firewall rules, etc.)
- Initial host bootstrapping (Tailscale installation, security lockdown)

We need a solution to manage Proxmox host-level configuration and administration tasks that Pulumi cannot handle.

### Requirements

1. **Storage management**: Create and manage ZFS pools, LVM volumes
2. **Advanced networking**: Configure vRack bridges with specific options
3. **System hardening**: Apply security configurations, firewall rules
4. **Bootstrap automation**: Install Tailscale, lock down public access
5. **Idempotent**: Safe to run multiple times
6. **Git-managed**: Configuration as code
7. **Integrates with orchestrator**: Can be called programmatically

### Alternatives Considered

**Option 1: Extend Pulumi Provider**
- **Pros**: Single tool for all infrastructure management
- **Cons**:
  - Requires maintaining custom provider fork
  - Pulumi not designed for OS-level configuration
  - High development effort for playground project
  - Abstracts away learning opportunities

**Option 2: Bash Scripts**
- **Pros**: Simple, no additional dependencies, full control
- **Cons**:
  - Not idempotent by default
  - Harder to maintain as complexity grows
  - No built-in inventory management
  - Limited error handling
  - Reinventing configuration management

**Option 3: Salt/Chef/Puppet**
- **Pros**: Full-featured configuration management
- **Cons**:
  - Requires agent installation (Salt, Puppet) or complex setup
  - Overkill for managing 1-2 Proxmox hosts
  - Steeper learning curve
  - Not commonly used in modern infrastructure

**Option 4: Ansible (Selected)**
- **Pros**:
  - Agentless (SSH-based)
  - Idempotent modules for storage, networking, system config
  - Industry standard, good community support
  - Role-based organization aligns with our needs
  - Integrates well with Python orchestrator (ansible-runner)
  - Good documentation for Proxmox management
- **Cons**:
  - Another tool in the stack
  - YAML-based (some prefer code)
  - Slower than compiled tools

## Decision

We will use **Ansible** for Proxmox host configuration and administration tasks that fall outside Pulumi's scope.

### Scope

**Ansible manages**:
- Proxmox host configuration (system-level)
- Storage pools (ZFS, LVM)
- Advanced network configuration
- Initial bootstrapping (Tailscale + lockdown)
- System hardening and optimization

**Pulumi manages**:
- VM provisioning
- VM hardware configuration
- Basic VM networking (vmbr assignments)
- OVH resources (future: load balancers, additional servers)

### Architecture

**Role-based execution** (no playbooks):
```
ansible/
└── roles/
    ├── proxmox-bootstrap/    # Initial setup, Tailscale, lockdown
    ├── proxmox-networking/   # vRack bridges, routing
    └── proxmox-storage/      # ZFS pools, LVM config
```

**Execution via orchestrator**:
```python
# orchestrator.py
from ansible_runner import run

# Generate inventory from ESC
inventory = generate_inventory_from_esc()

# Run role directly
run(
    private_data_dir='.',
    role='proxmox-bootstrap',
    inventory=inventory,
    ssh_key=get_ssh_key_from_esc()
)
```

**Inventory source**: Dynamically generated from ESC by orchestrator
- No static inventory files
- Node definitions in `config/proxmox/nodes.yaml`
- Synced to ESC `racknarok/proxmox`
- Orchestrator generates Ansible inventory at runtime

## Consequences

### Positive

1. **Fill Pulumi gaps**: Storage and advanced networking now manageable
2. **Idempotent**: Safe to re-run configurations
3. **Role-based**: Clean separation of concerns (bootstrap vs networking vs storage)
4. **Industry standard**: Well-documented, community modules
5. **Learning value**: Understanding Ansible is valuable for bare-metal management
6. **Integrates well**: ansible-runner provides Python API
7. **Agentless**: No agents on Proxmox hosts, just SSH

### Negative

1. **Another tool**: Adds Ansible to technology stack
2. **YAML management**: More YAML files to maintain
3. **Version complexity**: Need to pin Ansible version (via Nix)
4. **Overlap potential**: Must be careful not to conflict with Pulumi-managed resources

### Mitigation

- **Clear scope boundaries**: Document what Ansible manages vs Pulumi
- **Nix devshell**: Pin Ansible version for reproducibility
- **Role-only execution**: ansible-runner runs roles directly (simpler than playbooks)
- **ESC integration**: Configuration comes from same source as Pulumi

## Implementation Notes

### Role Structure

**proxmox-bootstrap**:
- Install Tailscale from Proxmox package repositories
- Join Proxmox host to Tailscale network (no route advertisement)
- Set up Tailscale SSH for secure access
- Configure firewall to block public access (except Tailscale)
- Disable Proxmox web UI on public interface
- Note: vRack subnet routing handled by dedicated router VM, not Proxmox hosts

**proxmox-networking**:
- Create vRack bridge (vmbr1)
- Configure VLAN awareness
- Set up routing if needed
- Configure MTU, bonding (future multi-NIC)

**proxmox-storage**:
- Create ZFS pools on NVMe drives
- Configure LVM thin provisioning
- Set up storage for VM images vs data
- Configure Longhorn storage backend

### Execution Flow

```bash
# Orchestrator workflow
orchestrator.py bootstrap rk1

# Under the hood:
1. Pull config from ESC (racknarok/proxmox)
2. Generate Ansible inventory dynamically
3. Retrieve SSH key from ESC
4. Add SSH key to ssh-agent
5. Run ansible-runner with proxmox-bootstrap role
6. Execute tasks on target host
```

### Bootstrap Safety

**Critical**: Bootstrap role must be run **manually** on new Proxmox hosts:
- Not automated via CI (requires initial SSH access)
- One-time operation per physical server
- Locks down public access immediately after Tailscale setup

### Configuration Source

```yaml
# config/proxmox/nodes.yaml
nodes:
  - name: rk1
    hostname: rk1.example.com
    vrack_interface: enp2s0
    vrack_ip: 10.0.0.1/24
    storage:
      - type: zfs
        name: nvme-pool
        device: /dev/nvme0n1
```

Synced to ESC → orchestrator generates inventory:
```yaml
# Generated Ansible inventory
all:
  hosts:
    rk1:
      ansible_host: rk1.example.com
      vrack_interface: enp2s0
      vrack_ip: 10.0.0.1/24
```

## Tool Versioning

**Via Nix devshell**:
```nix
# flake.nix
packages = with pkgs; [
  ansible_2_16  # Pin specific version
  # ... other tools
];
```

**Rationale**:
- Ansible version changes can break roles
- Nix ensures reproducible environment
- Same version for all developers and CI

## Future Considerations

### Multi-server support

When adding more Proxmox servers:
- Extend roles for Proxmox clustering
- Manage corosync configuration
- Handle distributed storage (Ceph consideration)

### Advanced use cases

- **Proxmox API management**: Use Ansible's proxmox modules
- **Backup automation**: Ansible cron jobs for vzdump
- **Monitoring**: Deploy Prometheus node exporters

### If complexity grows

- **Consider switching to playbooks** if roles become too interdependent
- **Split into collections** if role library grows large
- **CI testing**: Molecule for Ansible role testing

## References

- [Ansible Documentation](https://docs.ansible.com/)
- [ansible-runner](https://ansible-runner.readthedocs.io/)
- [Proxmox Ansible Modules](https://docs.ansible.com/ansible/latest/collections/community/general/proxmox_module.html)
- [Tailscale Ansible Role](https://github.com/artis3n/ansible-role-tailscale)

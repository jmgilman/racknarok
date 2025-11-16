# Configuration

This directory contains non-secret configuration for Project Racknarok infrastructure.

## Structure

```
config/
├── esc-mapping.yaml          # Defines Git → ESC environment mappings
└── proxmox/                  # Proxmox-specific configuration
    ├── cluster.yaml          # Cluster-wide settings
    ├── nodes.yaml            # Per-node configuration
    └── firewall.yaml         # Firewall rules
```

## Configuration Files

### Proxmox

- **`cluster.yaml`**: Cluster-wide settings that apply to all Proxmox nodes
  - Cluster name and configuration
  - Default settings (timezone, DNS, NTP)
  - Storage templates
  - Network defaults
  - Repository configuration

- **`nodes.yaml`**: Per-node configuration for each physical server
  - Node identity (name, FQDN, datacenter)
  - Network configuration (public, vRack)
  - Hardware specifications (for reference)
  - Storage configuration (ZFS, LVM)

- **`firewall.yaml`**: Host-level firewall rules
  - Default policies
  - Access rules (Tailscale, SSH, Proxmox UI)
  - vRack network rules
  - Future cluster communication rules

## ESC Mapping

The `esc-mapping.yaml` file defines how configuration and secrets are synchronized to Pulumi ESC environments.

Each environment maps to specific configuration and secret files:

```yaml
environments:
  proxmox:
    config:
      - config/proxmox/*.yaml
    secrets:
      - secrets/proxmox/*.enc.yaml
```

## Adding New Configuration

1. Create configuration files in the appropriate service directory
2. Update `esc-mapping.yaml` to include the new files
3. Commit changes to Git
4. Run `orchestrator.py sync-config` or let GitHub Actions sync automatically

## See Also

- [Secrets](../secrets/README.md) - Secret management with SOPS
- [ADR 005](../docs/decisions/005-config-organization-strategy.md) - Configuration organization strategy

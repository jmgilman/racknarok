# Proxmox Host Configuration Runbook

## Overview

This runbook covers the complete configuration of a Proxmox VE host after initial installation, including networking and storage setup.

## Prerequisites

- Proxmox VE installed via OVH wizard (see [Proxmox Installation](./proxmox-installation.md))
- Bootstrap completed (`orchestrator bootstrap rk1`)
- SSH access via Tailscale
- Development environment active (`devenv shell`)

## Configuration Steps

### Step 1: Verify Bootstrap

Ensure the bootstrap process completed successfully:

```bash
# Verify Tailscale is running
ssh root@rk1 'tailscale status'

# Verify firewall is configured
ssh root@rk1 'ufw status'

# Verify you can access Proxmox web UI via Tailscale
# https://rk1.racknarok.internal:8006
```

### Step 2: Configure Networking

Configure the vRack bridge for private VM networking:

```bash
# Run networking configuration
orchestrator configure-networking rk1
```

**What this does**:
- Creates Linux bridge `vmbr1` on interface `eno2`
- Assigns IP `10.0.0.1/24` to the bridge
- Enables VLAN awareness for future network segmentation
- Sets MTU to 1500
- Configures network for VM attachment

**Verification**:
```bash
# Check bridge status
ssh root@rk1 'ip addr show vmbr1'

# Check bridge members
ssh root@rk1 'brctl show vmbr1'

# Verify configuration in Proxmox UI
# Navigate to: Node (rk1) > System > Network
```

**Expected output**:
```
vmbr1: <BROADCAST,MULTICAST,UP,LOWER_UP>
    inet 10.0.0.1/24
    bridge-ports eno2
```

### Step 3: Configure Storage

Set up ZFS pools and LVM-thin volumes for VM storage:

```bash
# Run storage configuration
orchestrator configure-storage rk1
```

**What this does**:
- Creates ZFS pool `rpool-vms` on `/dev/nvme1n1`
- Enables LZ4 compression
- Sets proper 4K alignment (ashift=12)
- Creates LVM-thin pool on `pve` volume group
- Registers storage in Proxmox

**Verification**:
```bash
# Check ZFS pool
ssh root@rk1 'zpool status'
ssh root@rk1 'zpool list'

# Check LVM
ssh root@rk1 'lvs'
ssh root@rk1 'vgs'

# Check Proxmox storage
ssh root@rk1 'pvesm status'

# Verify in Proxmox UI
# Navigate to: Datacenter > Storage
```

**Expected storage pools**:
- `local` - Built-in directory storage (ISOs, templates, backups)
- `nvme-pool` - ZFS pool for VM images (~920 GB)
- `vm-storage` - LVM-thin for flexible VM storage

### Step 4: Final Verification

Verify the complete configuration:

```bash
# Check all network bridges
ssh root@rk1 'ip -br link'

# Check all storage
ssh root@rk1 'pvesm status'

# Check system status
ssh root@rk1 'pveversion --verbose'
```

## Network Topology After Configuration

```
┌─────────────────────────────────────────────┐
│         Proxmox Host (rk1)                  │
│                                             │
│  eno1 ──────> vmbr0 (public)               │
│               ├─ IP: <public-ip>            │
│               └─ Access: Blocked by UFW     │
│                                             │
│  eno2 ──────> vmbr1 (vRack)                │
│               ├─ IP: 10.0.0.1/24            │
│               ├─ VLAN-aware: yes            │
│               └─ Purpose: VM networking     │
│                                             │
│  tailscale0 ──> Tailscale mesh              │
│               └─ Admin access only          │
└─────────────────────────────────────────────┘
```

## Storage Layout After Configuration

```
/dev/nvme0n1 (960 GB)              /dev/nvme1n1 (960 GB)
├─ /boot (1 GB)                    └─ rpool-vms (ZFS)
├─ / (20 GB)                          ├─ Compression: lz4
├─ swap (1 GB)                        ├─ ashift: 12
└─ data (ZFS, ~872 GB)                └─ nvme-pool → Proxmox
   └─ local → Proxmox                    └─ ~920 GB usable
      └─ ISOs, templates

pve (LVM Volume Group)
└─ vm-storage (LVM-thin)
   └─ Thin provisioning enabled
```

## Troubleshooting

### Networking Issues

**Bridge not created**:
```bash
# Check if interface exists
ssh root@rk1 'ip link show eno2'

# Check Ansible logs for errors
# Review output from orchestrator command
```

**Can't reach VMs on vRack**:
```bash
# Verify bridge has IP
ssh root@rk1 'ip addr show vmbr1'

# Check if interface is attached to bridge
ssh root@rk1 'brctl show vmbr1'

# Verify VMs are attached to vmbr1
# Check in Proxmox UI: VM > Hardware > Network Device
```

### Storage Issues

**ZFS pool creation fails**:
```bash
# Check if disk exists
ssh root@rk1 'ls -l /dev/nvme1n1'

# Check if disk is already in use
ssh root@rk1 'lsblk /dev/nvme1n1'

# Force creation if safe (WARNING: destroys data)
orchestrator configure-storage rk1 --force
```

**Storage not visible in Proxmox**:
```bash
# Check Proxmox storage configuration
ssh root@rk1 'cat /etc/pve/storage.cfg'

# Re-register storage
ssh root@rk1 'pvesm add zfspool nvme-pool --pool rpool-vms'
```

### Lost Connectivity During Configuration

If you lose connectivity during networking changes:

1. **Wait 60 seconds** - Tailscale usually reconnects automatically
2. **Check Tailscale status** - Login to Tailscale admin console
3. **Use OVH KVM console** - Access via OVH control panel
4. **Review backup** - Network config is backed up to `/etc/network/interfaces.d/backups/`

## Revert Configuration

If you need to revert changes:

### Revert Networking

```bash
# SSH to host via Tailscale
ssh root@rk1

# Find backup
ls -la /etc/network/interfaces.d/backups/

# Restore backup
cp /etc/network/interfaces.d/backups/interfaces.backup-YYYYMMDD /etc/network/interfaces

# Restart networking (may lose connection temporarily)
systemctl restart networking

# Verify
ip addr show
```

### Revert Storage

```bash
# SSH to host
ssh root@rk1

# Destroy ZFS pool (WARNING: deletes all data)
zpool destroy rpool-vms

# Remove LVM thin pool
lvremove pve/vm-storage

# Remove from Proxmox
pvesm remove nvme-pool
pvesm remove vm-storage
```

## Next Steps

After completing host configuration:

1. **Provision VMs**: Deploy Talos nodes and utility VMs
2. **Deploy subnet router**: NixOS VM for Tailscale subnet routing
3. **Initialize Kubernetes**: Bootstrap Talos clusters
4. **Deploy platform services**: Argo CD, Vault, etc.

See [VM Provisioning](./vm-provisioning.md) for next steps.

## Reference

- **Bootstrap**: [Proxmox Installation](./proxmox-installation.md)
- **Architecture**: [Solution Strategy](../architecture/04-solution-strategy.md)
- **Networking Role**: [ansible/roles/proxmox-networking/README.md](../../ansible/roles/proxmox-networking/README.md)
- **Storage Role**: [ansible/roles/proxmox-storage/README.md](../../ansible/roles/proxmox-storage/README.md)

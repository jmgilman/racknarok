# 2. Constraints

## Budget Constraints

- **Initial hardware**: 1× OVH RISE-5 dedicated server
  - AMD Epyc 7413 (24c/48t)
  - 128 GB RAM
  - 2× 960 GB NVMe SSD
- **Future expansion**: Additional RISE-3 servers if employer-expensed
- **Cost-conscious**: Cannot replicate full production scale

## Hardware Constraints

- **Single physical server initially**: Limits true hardware-level HA
  - Longhorn can provide logical redundancy but data is on same physical disks
  - True HA requires multiple physical servers
- **Two NVMe drives per server**:
  - Disk 0: Proxmox OS + basic VM storage
  - Disk 1: VM data storage (primarily for Longhorn)
- **No hardware RAID**: Using "Soft RAID" / software-managed storage

## Provider Constraints

- **OVH-specific features**:
  - vRack for private networking
  - OVH Load Balancer integration
  - Limited to OVH's datacenter locations and capabilities
- **Network topology dictated by OVH**:
  - Public WAN interface on host
  - Private vRack network for inter-VM communication

## Security Constraints (by design)

- **Tailscale as sole admin access**: Non-negotiable architectural decision
  - All control planes (Proxmox, Kubernetes API, Talos API) must be private
  - No public exposure of admin/management interfaces
  - Requires Tailscale subnet router setup
- **OVH LB only for app ingress**: Cannot use for control-plane services

## Technology Constraints

- **Talos Linux**: Immutable OS with limited customization options
  - Must work within Talos configuration constraints
  - Cannot install arbitrary packages or run traditional SSH
- **Proxmox on bare-metal**: All Kubernetes nodes run as VMs
  - Adds virtualization overhead
  - Limits direct hardware access from Kubernetes

## Operational Constraints

- **Single operator**: Just me, no team
- **Time-boxed**: Side project, not full-time work
- **Everything-as-code preference**: Avoid manual operations where practical
  - May require workarounds when automation is impractical
  - Accept pragmatic "hacks" when necessary for learning

## Knowledge Constraints

- **Learning context**: Technologies are being learned as implemented
- **Documentation may lag**: Architecture evolves through experimentation
- **Mistakes are expected**: This is a playground, not production

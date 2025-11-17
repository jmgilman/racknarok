# 6. Deployment View

## Overview

This document describes how Project Racknarok infrastructure is deployed, configured, and maintained. The deployment strategy emphasizes automation, GitOps principles, and clear separation of concerns between different infrastructure layers.

## Deployment Principles

1. **Git as Single Source of Truth**: All configuration and secrets (encrypted) live in version control
2. **ESC as Distribution**: Pulumi ESC distributes configuration and secrets to all services
3. **Layered Deployment**: Each infrastructure layer has appropriate tooling
4. **Orchestrated Workflows**: Python CLI coordinates multi-tool deployments
5. **Automated Sync**: GitHub Actions automates configuration synchronization

## Deployment Layers

### Layer 1: Proxmox Host Configuration

**Tools**: Ansible (role-based execution)

**Scope**:
- Initial bootstrap (Tailscale installation, security lockdown)
- Network configuration (vRack bridges, routing)
- Storage management (ZFS pools, LVM)
- System hardening and optimization

**Execution**:
```bash
orchestrator bootstrap <node-name>
```

**Workflow**:
1. Orchestrator pulls ESC configuration for specified node
2. Generates dynamic Ansible inventory from ESC data
3. Retrieves SSH key from ESC, adds to ssh-agent
4. Executes Ansible roles via ansible-runner
5. Roles are executed directly (no playbooks)

**Roles**:
- `proxmox-bootstrap`: Install Tailscale, lock down public access, configure firewall
  - Command: `orchestrator bootstrap <node>`
  - Status: ✅ Implemented
- `proxmox-networking`: Configure vRack bridges, routing, VLANs
  - Command: `orchestrator configure-networking <node>`
  - Status: ✅ Implemented
- `proxmox-storage`: Set up ZFS pools, LVM volumes, storage for VMs
  - Command: `orchestrator configure-storage <node>`
  - Status: ✅ Implemented

**Inventory Source**: ESC environment `racknarok/proxmox`

**Manual Prerequisite**: SSH public key added to Proxmox during OVH installation wizard

### Layer 2: VM Provisioning

**Tools**: Pulumi (Automation SDK)

**Scope**:
- Create VMs on Proxmox (Talos nodes, NixOS utility VMs)
- Configure VM hardware (CPU, RAM, storage, network interfaces)
- Basic VM networking (vRack assignments)

**Execution**:
```bash
orchestrator provision
```

**Workflow**:
1. Orchestrator invokes Pulumi projects via Automation SDK
2. Pulumi projects reference ESC environments for configuration
3. VMs are created on Proxmox via Pulumi provider

**Pulumi Projects**:
- `pulumi/proxmox/`: Main VM provisioning project
  - Talos Linux nodes
  - NixOS Tailscale router
  - NixOS DNS server

**Configuration Source**: ESC environments (`racknarok/talos-mgmt`, `racknarok/services-tailscale`, etc.)

### Layer 3: NixOS VM Configuration

**Tools**: deploy-rs

**Scope**:
- Configure NixOS-based infrastructure VMs
- Deploy system packages and services
- Manage NixOS secrets via sops-nix

**Execution**:
```bash
orchestrator configure
```

**Workflow**:
1. Orchestrator runs `deploy-rs` for each NixOS configuration
2. deploy-rs builds NixOS system closure
3. Pushes closure to target VM and activates
4. Systemd services on VM pull runtime config from ESC

**Configurations**:
- Tailscale subnet router: Bridges Tailscale mesh to vRack
- DNS server: Internal DNS for `*.internal.yourdomain.com`

**Secrets Management**:
- sops-nix for encrypted secrets in NixOS configs
- ESC tokens encrypted with SOPS, decrypted at boot
- Systemd service fetches runtime config from ESC

### Layer 4: Kubernetes Deployment

**Tools**: Argo CD, Crossplane

**Scope**:
- Talos cluster provisioning (Crossplane with Talos provider)
- Kubernetes workload deployment (Argo CD)
- Platform services (Vault, cert-manager, etc.)

**Execution**: GitOps (automated)

**Workflow**:
1. Changes pushed to Git repository
2. Argo CD detects changes and syncs to cluster
3. Crossplane manages Talos cluster lifecycle
4. Applications deployed via Argo CD ApplicationSets

## Configuration Synchronization

### Git → ESC Sync Pipeline

**Purpose**: Keep ESC environments synchronized with Git repository

**Triggers**:
1. **Manual**: Operator runs `orchestrator.py sync-config`
2. **Automated**: GitHub Actions on changes to `config/` or `secrets/`

**Workflow**:

```
Developer modifies files in config/ or secrets/
  ↓
Commits to Git
  ↓
GitHub Actions workflow triggered
  ↓
[CI Environment]
├─ Authenticate to Pulumi Cloud (GitHub OIDC)
├─ Pull SOPS decryption key from ESC
├─ Decrypt secrets in secrets/
├─ Execute pulumi/esc-sync/ project
└─ Update ESC environments per config/esc-mapping.yaml
  ↓
Services consume updated config from ESC
```

**GitHub Actions Workflow**:
- File: `.github/workflows/sync-config.yml`
- Trigger: `on: [push]` for paths `config/**` or `secrets/**`
- Authentication: GitHub OIDC token (pre-configured in Pulumi Cloud)
- SOPS key: Retrieved from ESC environment `racknarok/ci`

**Pulumi Project**: `pulumi/esc-sync/`
- Uses Pulumi ESC service provider
- Reads `config/esc-mapping.yaml` to determine file → environment mappings
- Creates/updates ESC environments with decrypted secrets and config

### ESC Environment Structure

**Service-based organization**:

```
racknarok/
├─ proxmox                  # Proxmox node config, API tokens, SSH keys
├─ talos-mgmt               # Management cluster Talos config
├─ talos-prod               # Production cluster Talos config (future)
├─ services-tailscale       # Tailscale auth keys, config
├─ services-dns             # DNS server config
├─ ci                       # SOPS decryption key for GitHub Actions
└─ [additional services]
```

**Mapping Definition**: `config/esc-mapping.yaml`

```yaml
environments:
  proxmox:
    config:
      - config/proxmox/**
    secrets:
      - secrets/proxmox/**
      - secrets/ssh-keys.enc.yaml

  talos-mgmt:
    config:
      - config/talos/mgmt-cluster.yaml
    secrets:
      - secrets/talos/secrets.enc.yaml

  services-tailscale:
    config:
      - config/services/tailscale.yaml
    secrets:
      - secrets/services/tailscale.enc.yaml
```

## Orchestrator CLI

### Purpose

Coordinate multi-tool deployment workflows that span Ansible, Pulumi, and deploy-rs.

### Implementation

- **Language**: Python
- **Execution**: Using `uv` for dependency management
- **Location**: `orchestrator/src/orchestrator/`
- **Dependencies**: Pulumi Automation SDK, ansible-runner, ESC SDK, Click

### Commands

```bash
# Bootstrap a new Proxmox node (Tailscale + security lockdown)
orchestrator bootstrap <node-name>

# Configure networking (vRack bridges)
orchestrator configure-networking <node-name>

# Configure storage (ZFS pools, LVM-thin)
orchestrator configure-storage <node-name> [--force]

# Provision VMs via Pulumi
orchestrator provision

# Configure NixOS VMs
orchestrator configure

# Full deployment workflow
orchestrator deploy

# Sync config/secrets to ESC
orchestrator sync-config
```

### Example: Full Deployment

```bash
# Step 1: Bootstrap Proxmox host (manual, one-time)
orchestrator bootstrap rk1
# - Installs Tailscale
# - Locks down public access
# - Enables Tailscale-only access

# Step 2: Configure networking
orchestrator configure-networking rk1
# - Creates vRack bridge (vmbr1)
# - Configures VLAN awareness
# - Prepares for VM networking

# Step 3: Configure storage
orchestrator configure-storage rk1
# - Creates ZFS pool on /dev/nvme1n1
# - Sets up LVM-thin volumes
# - Registers storage in Proxmox

# Step 4: Provision VMs (future)
orchestrator provision
# - Creates Tailscale router, DNS, Talos nodes
# - Uses storage pools from Step 3

# Step 5: Configure NixOS VMs (future)
orchestrator configure
# - Runs deploy-rs for each NixOS config
# - VMs pull runtime config from ESC

# Step 6: Manual Kubernetes setup (future)
# (Talos cluster init, Argo CD bootstrap - documented in runbooks)
```

## Secrets Management

### At Rest (Git)

**Tool**: SOPS with age encryption

**Files**:
- `secrets/**/*.enc.yaml`: Encrypted secret files
- `secrets/.sops.yaml`: SOPS configuration

**Key Management**:
- Age key generated via `scripts/bootstrap-sops.sh`
- Public key stored in `.sops.yaml`
- Private key stored in ESC environment `racknarok/ci`

**Example**:
```bash
# Edit encrypted secret
sops secrets/proxmox/api-tokens.enc.yaml

# Encrypt new file
sops -e secrets/new-secret.yaml > secrets/new-secret.enc.yaml
```

### In Transit

**CI Pipeline**:
1. GitHub Actions retrieves SOPS private key from ESC
2. Decrypts secrets in `secrets/` directory
3. Passes decrypted values to `pulumi/esc-sync/` project
4. ESC stores secrets encrypted at rest

**Local Operations**:
1. Operator runs `orchestrator.py sync-config`
2. Orchestrator retrieves SOPS key from ESC (if needed)
3. Decrypts and syncs to ESC

### At Runtime

**Pulumi Projects**:
- Reference ESC environments: `pulumi.Config.requireObject("esc")`
- No secrets in Pulumi stack config
- All secrets pulled from ESC at runtime

**NixOS VMs**:
- ESC token encrypted with sops-nix
- Systemd service decrypts token at boot
- Service fetches runtime config from ESC API
- Config stored in secure location on filesystem

**Ansible**:
- Orchestrator generates inventory from ESC
- SSH keys retrieved from ESC, added to ssh-agent
- No secrets on disk

## Initial Bootstrap Sequence

**Context**: New physical server from OVH

**Steps**:

1. **OVH Installation Wizard**:
   - Select Proxmox VE as OS
   - Add bootstrap SSH public key (from `secrets/ssh-keys.enc.yaml`)
   - Complete installation

2. **Manual Bootstrap** (one-time):
   ```bash
   # From operator laptop (not in CI)
   orchestrator.py bootstrap rk1
   ```
   - Connects via bootstrap SSH key
   - Installs Tailscale on Proxmox host (joins Tailscale network)
   - Enables Tailscale SSH for secure access
   - Configures firewall to block public access (except Tailscale)
   - Post-bootstrap: All access via Tailscale only
   - Note: Subnet routing configured separately via dedicated router VM

3. **Automated Deployment**:
   ```bash
   orchestrator.py deploy
   ```
   - Configures Proxmox (Ansible roles)
   - Provisions VMs (Pulumi)
   - Configures NixOS VMs (deploy-rs)

4. **Manual Kubernetes Bootstrap**:
   - Initialize Talos cluster
   - Bootstrap Argo CD
   - (Detailed in `docs/runbooks/kubernetes-bootstrap.md`)

## Development Environment

### Nix Devshell

**File**: `flake.nix` (root)

**Tools Provided**:
- Ansible
- Pulumi CLI
- SOPS
- age
- Python 3.12
- uv
- just
- deploy-rs (or rely on nixos/flake.nix)

**Activation**:
```bash
# Manual
nix develop

# Automatic (via direnv)
# Add to .envrc:
use flake
```

### Justfile

**File**: `justfile`

**Common Tasks**:
```bash
# Bootstrap new node
just bootstrap <node>

# Full deployment
just deploy

# Sync config to ESC
just sync-config

# Edit encrypted secret
just edit-secret <path>
```

## CI/CD Pipeline

### GitHub Actions Workflow

**File**: `.github/workflows/sync-config.yml`

**Trigger**:
```yaml
on:
  push:
    paths:
      - 'config/**'
      - 'secrets/**'
```

**Jobs**:

1. **Authenticate**:
   - Use GitHub OIDC token to authenticate to Pulumi Cloud
   - No long-lived credentials stored in GitHub

2. **Decrypt Secrets**:
   - Pull SOPS private key from ESC `racknarok/ci` environment
   - Decrypt all files in `secrets/`

3. **Sync to ESC**:
   - Run `pulumi/esc-sync/` project
   - Update ESC environments per `config/esc-mapping.yaml`

4. **Verify**:
   - Optional: Run validation tests
   - Check that ESC environments are accessible

## Deployment Constraints

### Manual Operations

**One-time per physical server**:
- Initial Proxmox bootstrap (Tailscale + lockdown)
- Adding bootstrap SSH key during OVH installation

**Rationale**: These operations require physical server access or occur before automation is available.

### Security Constraints

- **No public Proxmox access**: Enforced by bootstrap process
- **All operations via Tailscale**: Post-bootstrap requirement
- **No secrets in Git**: Enforced by SOPS encryption
- **ESC as secrets gateway**: All runtime secret access via ESC

### Ordering Dependencies

1. **Bootstrap** → Proxmox host configured, Tailscale running
2. **Provision** → VMs created (requires Proxmox accessible via Tailscale)
3. **Configure** → NixOS VMs configured (requires VMs to exist)
4. **Kubernetes** → Clusters deployed (requires Talos VMs configured)

## Disaster Recovery

### Recovery Scenarios

**Complete rebuild**:
1. Restore from OVH rescue mode (or new server)
2. Run bootstrap process
3. Run orchestrator deployment
4. Restore Kubernetes persistent data from backups

**Lost ESC data**:
1. Re-run `orchestrator.py sync-config` (or CI workflow)
2. ESC environments restored from Git

**Lost local development environment**:
1. Clone repository
2. `nix develop` (rebuilds environment)
3. Pull secrets access from ESC

### Backup Strategy

**In Git**:
- All configuration (plaintext)
- All secrets (SOPS-encrypted)
- Infrastructure code (Pulumi, Ansible, NixOS)

**In ESC**:
- Runtime copy of configuration
- Can be fully reconstructed from Git

**Not in Git** (requires separate backup):
- Kubernetes persistent volumes
- Application data
- SOPS private key (stored in ESC, backed up separately)

## Future Enhancements

### Automation Improvements

- **Pulumi Deployments**: Replace manual orchestrator with Pulumi Cloud deployments
- **Self-service provisioning**: API or web UI for common operations
- **Drift detection**: Automated checks for configuration drift

### Multi-Server Support

- **Proxmox clustering**: Ansible roles for cluster formation
- **HA considerations**: Multi-node Kubernetes clusters
- **Storage replication**: Longhorn across physical servers

### Observability

- **Deployment metrics**: Track deployment duration, success rate
- **Configuration auditing**: Track who changed what in ESC
- **Alerting**: Notify on deployment failures

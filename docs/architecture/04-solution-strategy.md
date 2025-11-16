# 4. Solution Strategy

## High-Level Approach

Project Racknarok uses a **layered architecture** built from bare metal up to application workloads:

1. **Physical Layer**: OVH dedicated servers
2. **Virtualization Layer**: Proxmox VE
3. **OS Layer**: Talos Linux (immutable, API-driven)
4. **Container Orchestration**: Kubernetes
5. **Platform Services**: Argo CD, Crossplane, Vault, etc.
6. **Application Layer**: User workloads

## Key Architectural Decisions

### Multi-Cluster Topology

**Decision**: Separate management and production clusters

**Rationale**:
- **Management cluster**: Runs platform control plane (Argo CD, Crossplane, Vault)
- **Production cluster**: Runs application workloads (managed by management cluster)
- Reflects real-world enterprise patterns
- Isolates platform operations from workload churn
- Allows independent scaling and lifecycle management

**Implementation**:
- Start with management cluster on single RISE-5
- Add production cluster when more servers are available
- Use Crossplane with Talos provider for cluster lifecycle management

### Security-First Design

**Decision**: All control planes private, accessed only via Tailscale

**Rationale**:
- Reduces attack surface to near-zero for admin interfaces
- Leverages Tailscale identity and ACLs for access control
- No need to secure/harden public-facing Kubernetes API
- Enables zero-trust networking for operators

**Implementation**:
- Tailscale subnet router on Proxmox host or utility VM
- Advertise vRack subnet (`10.0.0.0/24`) to Tailscale network
- No Proxmox, Kubernetes API, or Talos API ports exposed publicly
- OVH Load Balancer used exclusively for application HTTP/S traffic

**Bootstrapping Security**:
- Initial Proxmox installation exposes port 8006 publicly (OVH default)
- **Critical**: First bootstrap step installs Tailscale and locks down public access
- Bootstrap uses SSH key pre-configured during OVH installation wizard
- Post-bootstrap access exclusively via Tailscale SSH
- This is a **manual** operation (not automated via CI) performed once per physical server

### Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **OS (K8s nodes)** | Talos Linux | Immutable, API-managed, Kubernetes-native, minimal attack surface |
| **OS (Infra VMs)** | NixOS | Declarative configuration, reproducible, GitOps-friendly |
| **VM Deployment** | deploy-rs | GitOps-native NixOS deployment tool |
| **CNI** | Cilium | eBPF-based, high performance, rich observability, kube-proxy replacement |
| **Service Mesh** | Istio Ambient | Sidecar-less architecture, mTLS, modern approach to learn |
| **Storage** | Longhorn | Kubernetes-native, distributed, works well with Talos |
| **GitOps (K8s)** | Argo CD | Industry standard, flexible, good UX |
| **IaC (Infrastructure)** | Pulumi | Type-safe, multi-provider, powerful for Proxmox + OVH |
| **IaC (K8s lifecycle)** | Crossplane | Kubernetes-native infrastructure management, composable |
| **Config Management** | Ansible | Proxmox host configuration, storage/networking management |
| **Secrets (at rest)** | SOPS + age | Encrypted secrets in Git, industry-standard tooling |
| **Secrets (runtime)** | Pulumi ESC + Vault | ESC for infra secrets distribution, Vault for K8s workloads |
| **Orchestration** | Custom Python CLI | Coordinates Ansible, Pulumi, and deploy-rs workflows |
| **Tool Versioning** | Nix devshell | Reproducible development environment, consistent tooling |
| **DNS** | CoreDNS/ExternalDNS | Internal DNS + automated public DNS record management |
| **Certs** | cert-manager | Automated Let's Encrypt via DNS-01 challenge |

### Networking Strategy

**Internal (vRack)**:
- All Talos nodes communicate over OVH vRack private network
- Provides isolated, high-bandwidth inter-VM connectivity
- Used for Kubernetes pod networking, storage replication, node communication

**External (Public)**:
- OVH Load Balancer provides public ingress
- Backends: Worker node NodePorts/hostPorts on vRack IPs
- Frontends: Public IPs on ports 80/443
- Cloudflare DNS points app domains to OVH LB public IPs

**Admin Access**:
- Tailscale subnet router bridges Tailscale mesh to vRack
- Split DNS: `*.internal.yourdomain.com` resolves via internal DNS VM
- All operators must be on Tailscale network to access infrastructure

### Infrastructure as Code

**Decision**: Automate everything practical, avoid clickops

**Configuration Management Strategy**:
- **Git as Single Source of Truth**: All configuration and secrets stored in version control
- **Pulumi ESC as Distribution Mechanism**: Centralized secret/config delivery to all services
- **Separation of Concerns**:
  - `config/`: Non-secret configuration data (YAML)
  - `secrets/`: Encrypted secrets using SOPS + age
  - ESC environments organized by service (e.g., `racknarok/proxmox`, `racknarok/talos-mgmt`)

**Configuration Sync Pipeline**:
1. **Local/Manual Operations**:
   - Operator modifies files in `config/` or `secrets/`
   - Dedicated Pulumi project (`pulumi/esc-sync/`) syncs to ESC environments
   - Uses service provider module for ESC integration

2. **CI/CD Automation** (GitHub Actions):
   - Triggers on changes to `config/` or `secrets/` directories
   - Authenticates to Pulumi Cloud via GitHub OIDC token
   - Pulls SOPS decryption key from dedicated ESC environment
   - Decrypts secrets and syncs everything to appropriate ESC environments
   - `config/esc-mapping.yaml` defines which files map to which ESC environments

**Secrets Management**:
- **At Rest (Git)**: SOPS encryption with age keys
  - SSH keys, API tokens, passwords stored encrypted
  - `.sops.yaml` configuration defines encryption rules
  - No plaintext secrets ever committed
- **In Transit**: SOPS key stored in ESC, retrieved by CI
- **At Runtime**: Services pull from ESC environments
  - Pulumi projects reference ESC environments
  - NixOS VMs use encrypted ESC tokens + systemd services to fetch config
  - Ansible inventory generated from ESC by orchestrator

**Proxmox Management Layer (Ansible)**:
- **Scope**: Proxmox host configuration and administration
  - Storage pool management (not supported by Pulumi provider)
  - Network bridge configuration (supplements Pulumi)
  - System hardening and initial bootstrapping
- **Execution**: Role-based (no playbooks)
  - `ansible/roles/proxmox-bootstrap/`: Tailscale + lockdown
  - `ansible/roles/proxmox-networking/`: vRack bridges, routing
  - `ansible/roles/proxmox-storage/`: ZFS pools, LVM configuration
- **Inventory**: Dynamically generated by orchestrator from ESC data
- **SSH Access**: Keys managed in ESC, injected into ssh-agent by orchestrator

**Infrastructure Layer (Pulumi)**:
- **Scope**: Proxmox VMs, VM networking, OVH resources
- **Projects**:
  - `pulumi/esc-sync/`: Syncs config/secrets to ESC environments
  - `pulumi/proxmox/`: Manages Proxmox VMs and basic networking
- **Management**:
  - Pulumi Cloud (free tier) as control plane
  - All secrets/config pulled from ESC (not hardcoded)
  - Executed via orchestrator using Pulumi Automation SDK

**VM Configuration Layer (NixOS)**:
- **Scope**: Non-Talos infrastructure VMs (Tailscale router, DNS server)
- **Tool**: deploy-rs for GitOps-style NixOS deployments
- **Secrets**: sops-nix for encrypted secrets in NixOS configs
- **Workflow**:
  1. Pulumi creates the VM
  2. Orchestrator runs `deploy-rs` to configure NixOS
  3. NixOS systemd services pull runtime config from ESC

**Kubernetes Layer (Argo CD + Crossplane)**:
- **Argo CD**: GitOps for Kubernetes resources and applications
- **Crossplane**: Kubernetes-native infrastructure lifecycle
  - Talos cluster provisioning and upgrades (via Talos provider)
  - Potential cloud resource management (future)

**Orchestrator (Python CLI)**:
- **Purpose**: Coordinate multi-tool deployment workflows
- **Capabilities**:
  - Execute Ansible roles with dynamic inventory from ESC
  - Run Pulumi projects via Automation SDK
  - Execute `deploy-rs` for NixOS deployments
  - Manage SSH keys and credentials from ESC
- **Execution**: Single Python file using `uv` for dependency management
- **Example Workflow**:
  1. Orchestrator pulls config from ESC
  2. Runs Ansible to configure Proxmox hosts
  3. Executes Pulumi to create VMs
  4. Runs deploy-rs to configure NixOS VMs

**Development Environment (Nix)**:
- **Scope**: Tool versioning and reproducible environments
- **Flake**: Root-level `flake.nix` provides devshell
- **Tools included**: Ansible, Pulumi, SOPS, age, Python, uv, just
- **Activation**: `nix develop` or automatic via direnv

**Repository Structure**:
```
Git Repository (Single Source of Truth)
├─ config/                      # Non-secret configuration (YAML)
│  ├─ proxmox/
│  ├─ talos/
│  ├─ services/
│  └─ esc-mapping.yaml          # Config → ESC environment mapping
├─ secrets/                     # SOPS-encrypted secrets
│  ├─ .sops.yaml
│  ├─ ssh-keys.enc.yaml
│  ├─ proxmox/
│  ├─ talos/
│  └─ services/
├─ ansible/roles/               # Ansible roles for Proxmox management
├─ pulumi/
│  ├─ esc-sync/                 # Syncs config/secrets → ESC
│  └─ proxmox/                  # Proxmox VM provisioning
├─ nixos/                       # NixOS configurations + deploy-rs
├─ orchestrator/                # Python CLI for deployment workflows
├─ scripts/                     # Helper scripts (SOPS bootstrap, etc.)
└─ flake.nix                    # Nix devshell for tooling
```

**Pragmatic exceptions**:
- Initial Proxmox bootstrap is **manual** (one-time per server)
- One-off operations where automation overhead is excessive
- Exploratory work during learning phase
- Document manual operations as ADRs or runbooks

### Evolution Path

**Phase 1 (Current)**: Single-server foundation
- Proxmox on 1× RISE-5
- Configuration management (Git → ESC pipeline)
- Orchestrator for deployment workflows
- Ansible for Proxmox host management
- Management cluster (Talos VMs)
- Tailscale subnet routing + security lockdown
- Internal DNS + split DNS
- Core platform services (Argo, Crossplane, Vault)
- Cilium networking, Longhorn storage

**Phase 2**: Platform maturation
- Istio Ambient service mesh
- Production-like app deployments
- Observability stack (Prometheus, Grafana, Hubble)
- Policy enforcement (OPA/Kyverno)

**Phase 3**: Multi-server expansion
- Add 2+ RISE-3 servers
- Form Proxmox cluster
- Deploy production Kubernetes cluster across multiple physical hosts
- True HA for storage (Longhorn replicas on separate hardware)
- Multi-cluster service mesh experiments

## Design Principles

1. **Learning over Production**: Favor interesting technologies over boring reliability
2. **Security by Default**: Private by design, explicit exposure when needed
3. **Realistic Topology**: Mimic enterprise patterns within budget constraints
4. **Everything as Code**: Automate where practical, document where not
5. **Incremental Complexity**: Start simple, add sophistication as understanding grows
6. **Document Decisions**: Capture the "why" as you go via ADRs and architecture docs

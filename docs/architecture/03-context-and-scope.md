# 3. Context and Scope

## System Boundary

**What Project Racknarok manages:**
- Proxmox virtualization layer
- Talos Linux VMs and Kubernetes clusters
- Platform services (Argo CD, Crossplane, Vault, CloudNativePG)
- Application workloads deployed to Kubernetes
- Internal DNS for `*.internal.yourdomain.com`
- Storage management via Longhorn

**What Project Racknarok does NOT manage:**
- Physical server hardware (managed by OVH)
- Public internet routing (delegated to Cloudflare)
- Tailscale network infrastructure (SaaS service)
- Pulumi Cloud infrastructure (SaaS service)
- Domain registration and public DNS zones (Cloudflare)

## External Dependencies

### OVH
- **Dedicated Servers**: RISE-3/RISE-5 bare-metal hosts
- **vRack**: Private network connecting servers and load balancer
- **Load Balancer**: Public ingress for application traffic (HTTP/S)
- **Responsibilities**:
  - Physical hardware provisioning and maintenance
  - Network infrastructure (public IPs, vRack connectivity)
  - Load balancer service for app ingress

### Tailscale
- **Service**: WireGuard-based mesh VPN
- **Role**: Sole access mechanism for all control planes
- **Configuration**:
  - Subnet router advertising vRack network
  - ACLs restricting admin access
  - Split DNS integration for internal hostnames
- **Responsibilities**:
  - Secure tunneling and identity management
  - DNS integration for `.ts.net` and split DNS

### Cloudflare
- **Services**:
  - DNS hosting for public domains
  - DNS API for automated record management
- **Integration points**:
  - ExternalDNS manages DNS records for app ingress
  - cert-manager uses DNS-01 challenge for Let's Encrypt
- **Responsibilities**:
  - Public DNS resolution
  - DNS API for automation

### Pulumi Cloud
- **Service**: SaaS control plane for Pulumi infrastructure-as-code
- **Tier**: Free tier
- **Role**: Infrastructure state management and configuration distribution
- **Components**:
  - **Pulumi Stacks**: Store infrastructure state for Proxmox resources
  - **Pulumi ESC (Environments, Secrets, and Configuration)**:
    - **Primary role**: Configuration distribution mechanism (not just secrets)
    - Stores both secrets and non-secret configuration
    - Service-based environments: `racknarok/proxmox`, `racknarok/talos-mgmt`, etc.
    - All services consume configuration from ESC
    - **Git is source of truth**, ESC is delivery mechanism
- **Operations**:
  - Orchestrator uses Pulumi Automation SDK
  - Dedicated `pulumi/esc-sync/` project syncs Git → ESC
  - GitHub Actions automates config/secrets sync to ESC
- **Responsibilities**:
  - State locking and concurrency control
  - Configuration and secrets distribution
  - Deployment history and audit trail

## Interfaces

### Admin/Operator Interfaces (Private - Tailscale only)
- **Proxmox Web UI**: `https://proxmox-01.internal.yourdomain.com:8006`
- **Kubernetes API**: `https://k8s-mgmt-api.internal.yourdomain.com:6443`
- **Talos API**: Port 50000 on individual node IPs
- **Argo CD UI**: `https://argocd.internal.yourdomain.com` (planned)
- **Vault UI**: `https://vault.internal.yourdomain.com` (planned)

### Infrastructure Management Interfaces (Public SaaS)
- **Pulumi Cloud Console**: `https://app.pulumi.com` (state, history, ESC config/secrets)
- **Tailscale Admin Console**: `https://login.tailscale.com/admin` (network config, ACLs)
- **Cloudflare Dashboard**: `https://dash.cloudflare.com` (DNS zone management)

### Operational Interfaces (Local/Developer)
- **Orchestrator CLI**: Python-based deployment workflow coordinator
  - Executes Ansible roles for Proxmox configuration
  - Runs Pulumi via Automation SDK
  - Deploys NixOS configurations via deploy-rs
  - Pulls configuration from ESC environments
- **GitHub Actions**: Automated config/secrets sync to ESC
  - Triggers on changes to `config/` or `secrets/` directories
  - Authenticates via GitHub OIDC token
  - Decrypts SOPS-encrypted secrets and syncs to ESC

### Application Interfaces (Public)
- **HTTP/HTTPS**: Port 80/443 via OVH Load Balancer
- **Public endpoints**: `*.yourdomain.com` (app-specific subdomains)
- **Flow**: Internet → Cloudflare DNS → OVH LB → Worker NodePorts → App Pods

### Infrastructure Interfaces (Private - vRack)
- **OVH LB backends**: Worker node IPs on vRack for ingress/gateway traffic
- **Inter-VM communication**: All Talos nodes communicate over vRack
- **Storage traffic**: Longhorn replication over vRack network

## Data Flows

### Configuration Distribution Flow
```
Developer modifies config/secrets in Git
  → Commits to repository
  → GitHub Actions triggered (on config/ or secrets/ changes)
  → Authenticates to Pulumi Cloud (OIDC)
  → Retrieves SOPS key from ESC
  → Decrypts secrets
  → Pulumi esc-sync project updates ESC environments
  → Services consume from ESC:
     - Pulumi projects reference ESC environments
     - Orchestrator pulls config for Ansible inventory
     - NixOS VMs fetch runtime config via systemd
```

### Admin Access Flow
```
Operator Laptop (Tailscale client)
  → Tailscale mesh network
  → Subnet router (dedicated NixOS utility VM)
  → vRack network
  → Proxmox / Kubernetes API / Talos API
```

### Deployment Workflow Flow
```
Operator runs orchestrator CLI
  → Pulls configuration from ESC
  → Executes Ansible roles (Proxmox configuration)
     - Dynamic inventory from ESC
     - SSH keys from ESC → ssh-agent
  → Runs Pulumi projects (VM provisioning)
     - Uses Automation SDK
     - Pulls config from ESC
  → Deploys NixOS configurations
     - Runs deploy-rs
     - VMs fetch secrets from ESC at runtime
```

### Application Traffic Flow
```
Internet User
  → Cloudflare DNS (resolve *.yourdomain.com)
  → OVH Load Balancer (public IP)
  → Worker Nodes (vRack IPs, NodePort/hostPort)
  → Istio Gateway / Ingress Controller
  → Application Pods
```

### Internal Service Communication
```
Pod A → Cilium CNI → (optional: Istio ztunnel mTLS) → Pod B
```

## Scope Boundaries

### In Scope
- Configuration management (Git → ESC pipeline)
- Secrets management (SOPS encryption, ESC distribution)
- Proxmox host configuration (Ansible)
- Proxmox VM provisioning (Pulumi)
- NixOS VM configuration (deploy-rs)
- Kubernetes cluster lifecycle and configuration
- Application deployment and management
- Platform service operation (Argo, Vault, etc.)
- Internal networking and service mesh
- Storage provisioning and management
- Internal DNS and certificate management
- Deployment orchestration workflows

### Out of Scope
- Physical hardware management
- Public DNS zone management (automated via ExternalDNS)
- Tailscale network administration (use Tailscale admin console)
- Public certificate issuance (automated via cert-manager)
- DDoS protection / CDN (delegated to Cloudflare if needed)

### Future Scope (when multi-server)
- Proxmox clustering
- Multi-node Kubernetes clusters with true HA
- Physical server diversity for storage replication
- Production workload cluster (separate from management)

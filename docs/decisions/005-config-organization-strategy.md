# ADR 005: Configuration Organization Strategy

## Status

Accepted

## Context

Project Racknarok requires a consistent approach to organizing configuration and secrets across multiple services (Proxmox, Talos, Tailscale, DNS, etc.). This configuration needs to:
- Be stored in Git (single source of truth)
- Map cleanly to Pulumi ESC environments
- Support both non-secret config and encrypted secrets
- Be consumed by multiple tools (Pulumi, Ansible, NixOS)
- Enable automated sync to ESC via CI/CD

Without a clear organization strategy, we risk:
- Scattered configuration files
- Unclear ESC environment structure
- Difficult mapping between Git and ESC
- Maintenance headaches as project grows

### Requirements

1. **Clear separation**: Non-secret config vs encrypted secrets
2. **Parallel structure**: Easy to find related config and secrets
3. **Service-based grouping**: Organize by service/component
4. **ESC mapping**: Clean mapping to ESC environments
5. **Tool-agnostic**: Multiple tools can consume the config
6. **Scalable**: Structure works from 1 to N services
7. **Auditable**: Easy to track what changed

### Alternatives Considered

**Option 1: Flat Structure**
```
config/
  proxmox-nodes.yaml
  talos-mgmt.yaml
  tailscale.yaml
secrets/
  proxmox-api-tokens.enc.yaml
  ssh-keys.enc.yaml
  talos-secrets.enc.yaml
```
- **Pros**: Simple for small projects
- **Cons**:
  - Doesn't scale beyond ~10 files
  - Hard to find related config/secrets
  - No clear grouping by service

**Option 2: Tool-Based Structure**
```
config/
  ansible/
  pulumi/
  nixos/
secrets/
  ansible/
  pulumi/
  nixos/
```
- **Pros**: Organized by tool
- **Cons**:
  - Service config split across tool boundaries
  - Doesn't map well to ESC (service-based)
  - Makes config less portable between tools

**Option 3: Environment-Based Structure**
```
config/
  dev/
  prod/
secrets/
  dev/
  prod/
```
- **Pros**: Clear environment separation
- **Cons**:
  - Overkill for playground (no dev/prod split initially)
  - Doesn't address service organization within environments
  - Can combine with other approaches later if needed

**Option 4: Service-Based Structure (Selected)**
```
config/
  proxmox/
    nodes.yaml
  talos/
    mgmt-cluster.yaml
    prod-cluster.yaml
  services/
    tailscale.yaml
    dns.yaml
  esc-mapping.yaml

secrets/
  .sops.yaml
  ssh-keys.enc.yaml
  proxmox/
    api-tokens.enc.yaml
  talos/
    secrets.enc.yaml
  services/
    tailscale.enc.yaml
    dns.enc.yaml
```
- **Pros**:
  - Clear service grouping
  - Parallel config/secrets structure
  - Maps naturally to ESC environments
  - Easy to find all config for a service
  - Scales well as services are added
- **Cons**:
  - Slight complexity compared to flat structure
  - Requires `esc-mapping.yaml` to define relationships

## Decision

We will use a **service-based directory structure** with parallel organization for config and secrets.

### Directory Structure

```
config/                          # Non-secret configuration (plaintext YAML)
├── proxmox/                     # Proxmox-specific config
│   └── nodes.yaml               # Node definitions, network config
├── talos/                       # Talos cluster configs
│   ├── mgmt-cluster.yaml
│   └── prod-cluster.yaml        # Future
├── services/                    # Infrastructure services
│   ├── tailscale.yaml
│   ├── dns.yaml
│   └── [more services]
└── esc-mapping.yaml             # Defines config → ESC env mapping

secrets/                         # SOPS-encrypted secrets (Git-safe)
├── .sops.yaml                   # SOPS encryption config
├── ssh-keys.enc.yaml            # Shared SSH keys
├── proxmox/
│   └── api-tokens.enc.yaml
├── talos/
│   └── secrets.enc.yaml
└── services/
    ├── tailscale.enc.yaml
    └── dns.enc.yaml
```

### ESC Environment Mapping

**Service-based ESC environments**:
```
racknarok/
├── proxmox                      # Proxmox config + secrets
├── talos-mgmt                   # Management cluster
├── talos-prod                   # Production cluster (future)
├── services-tailscale           # Tailscale service
├── services-dns                 # DNS service
└── ci                           # CI-specific (SOPS key)
```

**Mapping definition** (`config/esc-mapping.yaml`):
```yaml
environments:
  # Proxmox environment
  proxmox:
    config:
      - config/proxmox/**
    secrets:
      - secrets/proxmox/**
      - secrets/ssh-keys.enc.yaml

  # Management cluster environment
  talos-mgmt:
    config:
      - config/talos/mgmt-cluster.yaml
    secrets:
      - secrets/talos/secrets.enc.yaml

  # Tailscale service environment
  services-tailscale:
    config:
      - config/services/tailscale.yaml
    secrets:
      - secrets/services/tailscale.enc.yaml

  # DNS service environment
  services-dns:
    config:
      - config/services/dns.yaml
    secrets:
      - secrets/services/dns.enc.yaml
```

### File Format

**All files use YAML**:
- Industry standard
- Human-readable
- Well-supported by tools
- SOPS native support

**Naming conventions**:
- Non-secret: `*.yaml`
- Secret: `*.enc.yaml`
- Clear distinction at a glance

## Consequences

### Positive

1. **Clear organization**: Easy to find config for any service
2. **Parallel structure**: Secrets mirror config layout
3. **Service-based ESC**: Natural mapping to ESC environments
4. **Scalable**: Adding services doesn't break structure
5. **Tool-agnostic**: Any tool can consume YAML files
6. **Explicit mapping**: `esc-mapping.yaml` documents relationships
7. **Separation of concerns**: Config vs secrets, service vs shared
8. **Git-friendly**: Logical grouping for commits and PRs

### Negative

1. **More directories**: Slight overhead vs flat structure
2. **Mapping file needed**: Must maintain `esc-mapping.yaml`
3. **Deep nesting potential**: Could get complex with many services

### Mitigation

- **Keep it flat initially**: Only create directories as needed
- **Validate mapping**: `pulumi/esc-sync/` project validates mapping
- **Documentation**: Clear examples and conventions

## Implementation Notes

### Example: Proxmox Configuration

**config/proxmox/nodes.yaml**:
```yaml
nodes:
  - name: rk1
    hostname: rk1.racknarok.internal
    public_ip: 51.91.xxx.xxx
    vrack:
      interface: enp2s0
      ip: 10.0.0.1/24
      gateway: 10.0.0.254
    storage:
      - name: nvme-pool
        type: zfs
        devices:
          - /dev/nvme0n1
      - name: vm-storage
        type: lvm-thin
        vg: pve
```

**secrets/proxmox/api-tokens.enc.yaml** (encrypted):
```yaml
# Encrypted with SOPS
api_tokens:
  terraform: pve-token-id!token-secret-xxxxx
  automation: pve-token-id!token-secret-yyyyy
```

**secrets/ssh-keys.enc.yaml** (encrypted):
```yaml
# Bootstrap SSH keys (shared across nodes)
ssh:
  bootstrap:
    public: ssh-ed25519 AAAA...
    private: |
      -----BEGIN OPENSSH PRIVATE KEY-----
      [encrypted]
      -----END OPENSSH PRIVATE KEY-----
```

### Example: Talos Configuration

**config/talos/mgmt-cluster.yaml**:
```yaml
cluster:
  name: mgmt
  version: v1.8.0
  endpoint: https://mgmt.racknarok.internal:6443

nodes:
  control_plane:
    count: 3
    cpus: 4
    memory: 8192
    disk: 100

  workers:
    count: 2
    cpus: 8
    memory: 16384
    disk: 200

network:
  pod_cidr: 10.244.0.0/16
  service_cidr: 10.96.0.0/12
  cni: cilium
```

**secrets/talos/secrets.enc.yaml** (encrypted):
```yaml
# Talos secrets bundle
secrets:
  cluster:
    id: xxx
    secret: yyy
  ca:
    crt: |
      -----BEGIN CERTIFICATE-----
      [encrypted]
      -----END CERTIFICATE-----
    key: |
      -----BEGIN RSA PRIVATE KEY-----
      [encrypted]
      -----END RSA PRIVATE KEY-----
```

### Sync to ESC

**pulumi/esc-sync/index.ts**:
```typescript
import * as pulumi from "@pulumi/pulumi";
import * as fs from "fs";
import * as yaml from "js-yaml";

const mapping = yaml.load(
  fs.readFileSync("../../config/esc-mapping.yaml", "utf8")
);

// For each ESC environment
for (const [envName, envConfig] of Object.entries(mapping.environments)) {
  // Collect config files
  const configData = collectFiles(envConfig.config);

  // Collect and decrypt secret files (decrypted by SOPS before this runs)
  const secretData = collectFiles(envConfig.secrets);

  // Create/update ESC environment
  const env = new pulumi.esc.Environment(`${envName}`, {
    organization: "racknarok",
    name: envName,
    values: {
      ...configData,
      ...secretData,
    },
  });
}
```

## Naming Conventions

### Directory Names
- Lowercase, hyphen-separated
- Descriptive service names: `proxmox`, `talos`, `services`

### File Names
- Lowercase, hyphen-separated
- Non-secrets: `*.yaml`
- Secrets: `*.enc.yaml` (encrypted)
- Descriptive: `nodes.yaml`, `mgmt-cluster.yaml`, `api-tokens.enc.yaml`

### ESC Environment Names
- Pattern: `{org}/{service}` or `{org}/{service}-{variant}`
- Examples: `racknarok/proxmox`, `racknarok/talos-mgmt`, `racknarok/services-tailscale`

## Service Categories

### Infrastructure Layer
- `proxmox/`: Bare-metal virtualization
- `talos/`: Kubernetes clusters
- `ovh/`: OVH-specific resources (future)

### Services Layer
- `services/tailscale/`: VPN mesh
- `services/dns/`: Internal DNS
- `services/*/`: Additional infrastructure services

### Shared
- Root-level files for shared config (like `ssh-keys.enc.yaml`)

## Future Considerations

### Environment Split (dev/prod)

**If needed later**:
```
config/
  dev/
    proxmox/
    talos/
  prod/
    proxmox/
    talos/
```

**ESC environments**:
- `racknarok/dev-proxmox`
- `racknarok/prod-proxmox`

**For now**: Single environment (playground), don't over-engineer

### Multi-Cluster Support

**Already supported**:
```
config/talos/
  mgmt-cluster.yaml
  prod-cluster.yaml
  edge-cluster.yaml
```

Maps to:
- `racknarok/talos-mgmt`
- `racknarok/talos-prod`
- `racknarok/talos-edge`

### Shared Configuration

**For config used by multiple services**:
- Option 1: Put in root (e.g., `ssh-keys.enc.yaml`)
- Option 2: Create `shared/` directory
- Option 3: Include in multiple ESC environments via mapping

**Current approach**: Root-level for truly shared items

## Validation

### Schema Validation (Future)

Could add JSON Schema or similar:
```
config/
  schemas/
    proxmox-nodes.schema.json
    talos-cluster.schema.json
```

Validate during `esc-sync` execution.

### Sync Validation

`pulumi/esc-sync/` project should:
1. Validate `esc-mapping.yaml` syntax
2. Check that referenced files exist
3. Ensure no orphaned files (files not in mapping)
4. Verify SOPS encryption on secret files

## References

- [YAML Specification](https://yaml.org/spec/)
- [SOPS Configuration](https://github.com/getsops/sops#usage)
- [Pulumi ESC Environments](https://www.pulumi.com/docs/esc/environments/)

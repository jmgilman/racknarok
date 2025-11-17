# NixOS VM Provisioning Implementation Plan

## Overview

Implementation of the complete foundation for provisioning NixOS VMs in Project Racknarok. This creates the infrastructure layer to deploy the Tailscale subnet router and future infrastructure VMs through a single idempotent command: `orchestrator provision`.

## Current Status

### ✅ Completed (Phase 1-3)

#### Phase 1: Configuration Structure
- [x] Created `config/nixos/vms.yaml` with VM definitions
- [x] Created `secrets/nixos/secrets.yaml` template (needs encryption)
- [x] Updated `config/esc-mapping.yaml` to include nixos-vms environment

#### Phase 2: NixOS Flake Structure
- [x] Created `nixos/flake.nix` with deploy-rs, sops-nix, and disko integration
- [x] Created `nixos/hosts/tailscale-router/configuration.nix` (basic NixOS config)
- [x] Created `nixos/hosts/tailscale-router/hardware-configuration.nix` (static Proxmox template)
- [x] Created `nixos/hosts/tailscale-router/disk-config.nix` (disko configuration)
- [x] Created `nixos/.sops.yaml` for sops-nix
- [x] Created `nixos/secrets/secrets.yaml` template
- [x] Created `nixos/.gitignore` to prevent committing unencrypted secrets

#### Phase 3: Pulumi Project
- [x] Created `pulumi/proxmox/` project structure (TypeScript)
- [x] Created `Pulumi.yaml` and `Pulumi.dev.yaml`
- [x] Created `index.ts` (currently exports config, needs VM resources added)
- [x] Created `package.json` and `tsconfig.json`
- [x] Standardized on TypeScript (matches esc-sync project)

#### Phase 4: Orchestrator Integration (Partial)
- [x] Implemented `orchestrator/src/orchestrator/pulumi/automation.py` (Pulumi wrapper)
- [x] Implemented `orchestrator/src/orchestrator/nixos/deployer.py` (nixos-anywhere + deploy-rs)

### 🔄 Remaining Work

#### Phase 4: Orchestrator Integration (Completion)
- [ ] Implement `orchestrator provision` command that orchestrates:
  1. Load ESC configuration
  2. Run Pulumi to create/update VMs
  3. Wait for SSH availability
  4. Run nixos-anywhere (with age key injection)
  5. Run deploy-rs for final configuration

#### Phase 5: Configuration & Testing
- [ ] One-time setup: Generate password hashes
- [ ] One-time setup: Encrypt secrets with SOPS
- [ ] Sync configuration to ESC (`orchestrator config sync`)
- [ ] Add Proxmox provider configuration to Pulumi
- [ ] Test full provision workflow
- [ ] Extract generated hardware-configuration.nix from VM (one-time)
- [ ] Document manual steps in runbook

---

## Critical Configuration Workflows

### Age Key Management (RESOLVED)

**Decision**: Reuse existing age key from main project (age16u38wxvlqphcxz6rvju3z6y9qwz2lue098l3xevzlzvrffvxt58suuhew4)

**Workflow**:
1. **Before first provision**: Encrypt `nixos/secrets/secrets.yaml` with existing age key
2. **During nixos-anywhere**: Orchestrator passes age private key via `--extra-files`
3. **On VM**: Age key placed at `/var/lib/sops-nix/key.txt`
4. **sops-nix**: Reads secrets using that key
5. **Updates**: Never - key is static

**Implementation**:
```python
# In orchestrator provision command:
# 1. Get age key from ESC
age_key = esc_config['sops']['private_key']

# 2. Create temp directory structure
temp_dir/
  └── var/lib/sops-nix/
      └── key.txt  # Contains age private key

# 3. Pass to nixos-anywhere
nixos-anywhere --extra-files ./temp_dir ...
```

### Hardware Configuration (RESOLVED)

**Decision**: Use static Proxmox VM template, optionally update after first install

**Workflow**:
1. **First install**: nixos-anywhere uses static template from Git
2. **Optional**: After first boot, extract generated config and update Git
3. **Subsequent deploys**: Use version in Git

**Static template works because**:
- We control the VM hardware (Proxmox)
- VirtIO drivers are consistent
- Disk device is always `/dev/vda`

**To update** (optional, one-time per VM type):
```bash
ssh root@10.0.0.10 cat /etc/nixos/hardware-configuration.nix \
  > nixos/hosts/tailscale-router/hardware-configuration.nix
git commit -am "chore: update hardware-configuration.nix from live system"
```

### SSH Keys (RESOLVED)

**Decision**: Use existing Proxmox admin SSH key, store in sops-nix secrets

**Workflow**:
1. **Extract existing key**: Already in `secrets/proxmox/ssh.enc.yaml`
2. **Add to NixOS secrets**: Add public key to `nixos/secrets/secrets.yaml`
3. **NixOS config reads from sops-nix**:
   ```nix
   users.users.root.openssh.authorizedKeys.keys = [
     (builtins.readFile config.sops.secrets.root_ssh_public_key.path)
   ];
   ```
4. **Updates**: Manual - update secrets, re-encrypt, re-provision

### Password Hashes (RESOLVED)

**Workflow**:
1. **Generate locally**:
   ```bash
   mkpasswd -m sha-512
   # Enter password when prompted
   ```
2. **Add to secrets**: Put hash in `nixos/secrets/secrets.yaml`
3. **Encrypt**:
   ```bash
   sops -e nixos/secrets/secrets.yaml > nixos/secrets/secrets.enc.yaml
   ```
4. **NixOS reads from sops-nix**:
   ```nix
   users.users.root.hashedPasswordFile =
     config.sops.secrets.root_password_hash.path;
   ```
5. **Updates**: Generate new hash, update secrets, re-provision

---

## One-Time Setup Steps (Before First Provision)

### 1. Generate Password Hashes

```bash
# Generate root password hash
mkpasswd -m sha-512
# Enter your desired root password
# Copy the hash (starts with $6$)
```

### 2. Extract SSH Public Key

```bash
# Get the public key from existing Proxmox secrets
sops -d secrets/proxmox/ssh.enc.yaml | yq '.ssh.admin.public_key'
# Copy the output
```

### 3. Create and Encrypt NixOS Secrets

```bash
# Edit the secrets file
cat > nixos/secrets/secrets.yaml <<EOF
# Root user password hash (from step 1)
root_password_hash: "\$6$rounds=656000$..."

# Root user SSH public key (from step 2)
root_ssh_public_key: "ssh-ed25519 AAAAC3..."
EOF

# Encrypt with SOPS using existing age key
sops -e nixos/secrets/secrets.yaml > nixos/secrets/secrets.enc.yaml

# Remove unencrypted file
rm nixos/secrets/secrets.yaml
```

### 4. Update NixOS Configuration

Edit `nixos/hosts/tailscale-router/configuration.nix`:

```nix
# Add to sops.secrets section:
sops.secrets = {
  root_password_hash = {
    neededForUsers = true;
  };
  root_ssh_public_key = {};
};

# Update users.users.root:
users.users.root = {
  hashedPasswordFile = config.sops.secrets.root_password_hash.path;
  openssh.authorizedKeys.keys = [
    (builtins.readFile config.sops.secrets.root_ssh_public_key.path)
  ];
};
```

### 5. Sync Configuration to ESC

```bash
orchestrator config sync
```

This creates the `nixos-vms` ESC environment with:
- VM definitions from `config/nixos/vms.yaml`
- Encrypted secrets from `secrets/nixos/secrets.enc.yaml`
- Proxmox admin SSH key (reused)

### 6. Install Dependencies and Add Proxmox Provider

```bash
# Install npm dependencies
cd pulumi/proxmox
npm install

# Add Proxmox provider
npm install @pulumiverse/proxmox
```

Edit `pulumi/proxmox/index.ts` to add actual VM provisioning with the Proxmox provider. This requires:
- Proxmox API endpoint from ESC
- Proxmox API token from ESC
- `@pulumiverse/proxmox` provider package

---

## Implementation Details

### Orchestrator Provision Command

**Location**: `orchestrator/src/orchestrator/commands/provision.py`

**Workflow**:
```python
@click.command()
@click.option("--vm", help="Specific VM to provision")
@pass_orchestrator_context
def provision(ctx, vm):
    """Provision NixOS VMs: Create → Install → Configure."""

    # 1. Load configuration from ESC
    nixos_config = load_esc_config("nixos-vms")
    proxmox_config = load_esc_config("proxmox")

    # Filter VMs if specified
    vms = [v for v in nixos_config["vms"] if not vm or v["name"] == vm]

    # 2. Run Pulumi to create/update VMs
    project_path = Path(__file__).parent.parent.parent.parent / "pulumi" / "proxmox"
    run_pulumi_project(project_path, stack_name="dev", operation="up")

    # 3. For each VM:
    for vm_config in vms:
        vm_name = vm_config["name"]
        vm_ip = vm_config["network"]["ip"].split("/")[0]

        # 3a. Wait for SSH
        if not wait_for_ssh(vm_ip):
            raise click.ClickException(f"SSH timeout for {vm_name}")

        # 3b. Check if NixOS already installed (idempotency)
        if check_nixos_installed(vm_ip):
            click.echo(f"NixOS already installed on {vm_name}, skipping installation")
        else:
            # 3c. Prepare age key for sops-nix
            age_key = proxmox_config["sops"]["private_key"]  # From ESC
            temp_dir = prepare_extra_files(age_key)

            # 3d. Run nixos-anywhere
            nixos_dir = Path(__file__).parent.parent.parent.parent / "nixos"
            install_nixos_anywhere(
                flake_path=nixos_dir,
                target_host=vm_ip,
                hostname=vm_name,
                extra_files=temp_dir,
            )

            # Cleanup temp dir
            cleanup_temp_dir(temp_dir)

        # 3e. Deploy configuration with deploy-rs
        deploy_nixos_config(
            config_path=nixos_dir,
            target=vm_name,
        )

    click.secho("✓ Provisioning complete!", fg="green")
```

### Helper Functions Needed

```python
def prepare_extra_files(age_key: str) -> Path:
    """
    Create temporary directory with age key for nixos-anywhere.

    Structure:
    temp_dir/
      └── var/lib/sops-nix/
          └── key.txt
    """
    import tempfile
    temp_dir = Path(tempfile.mkdtemp(prefix="nixos-anywhere-"))
    key_dir = temp_dir / "var" / "lib" / "sops-nix"
    key_dir.mkdir(parents=True)
    (key_dir / "key.txt").write_text(age_key)
    return temp_dir

def cleanup_temp_dir(temp_dir: Path):
    """Remove temporary directory."""
    import shutil
    shutil.rmtree(temp_dir)
```

### nixos-anywhere Integration

Update `orchestrator/src/orchestrator/nixos/deployer.py`:

```python
def install_nixos_anywhere(
    flake_path: Path,
    target_host: str,
    hostname: str,
    extra_files: Path,  # Added parameter
    verbose: bool = False,
) -> bool:
    """Install NixOS with age key injection."""

    cmd = [
        "nix", "run", "github:nix-community/nixos-anywhere", "--",
        "--flake", f"{flake_path}#{hostname}",
        "--extra-files", str(extra_files),  # Pass age key
        f"root@{target_host}",
    ]

    # ... rest of implementation
```

---

## Testing Plan

### 1. Configuration Validation

```bash
# Check NixOS flake builds
cd nixos
nix flake check

# Check Pulumi project is valid
cd pulumi/proxmox
pulumi preview --stack dev
```

### 2. Provision Test VM

```bash
# Full provision workflow
orchestrator provision --vm tailscale-router
```

**Expected flow**:
1. Loads config from ESC
2. Pulumi creates VM in Proxmox (cloud-init injects SSH key)
3. Waits for VM to boot and SSH to be available
4. Runs nixos-anywhere:
   - Boots into kexec
   - Partitions disk with disko
   - Installs NixOS
   - Copies age key to `/var/lib/sops-nix/key.txt`
   - Reboots
5. Runs deploy-rs:
   - Builds final configuration
   - Activates on VM
   - Confirms success

### 3. Idempotency Test

```bash
# Run provision again - should skip nixos-anywhere
orchestrator provision --vm tailscale-router
```

**Expected**:
- Pulumi: No changes (VM already exists)
- nixos-anywhere: Skipped (detects `/etc/NIXOS`)
- deploy-rs: Runs (applies any config changes)

### 4. Configuration Update Test

```bash
# Edit NixOS config
vim nixos/hosts/tailscale-router/configuration.nix
# Add a package to environment.systemPackages

# Commit
git commit -am "feat: add package to tailscale-router"

# Re-provision
orchestrator provision --vm tailscale-router
```

**Expected**:
- Only deploy-rs runs
- New package is installed
- No VM recreation or OS reinstall

---

## File Tree

```
/Users/josh/code/infra/
├── config/
│   ├── esc-mapping.yaml                    [MODIFIED] Added nixos-vms
│   └── nixos/
│       └── vms.yaml                         [CREATED] VM definitions
├── secrets/
│   └── nixos/
│       └── secrets.enc.yaml                 [TODO] Needs encryption
├── pulumi/
│   └── proxmox/                            [CREATED] TypeScript
│       ├── Pulumi.yaml
│       ├── Pulumi.dev.yaml
│       ├── index.ts                         [TODO] Add VM resources
│       ├── package.json
│       ├── tsconfig.json
│       └── .gitignore
├── nixos/                                   [CREATED]
│   ├── flake.nix
│   ├── .sops.yaml
│   ├── .gitignore
│   ├── hosts/
│   │   └── tailscale-router/
│   │       ├── configuration.nix            [TODO] Update to use sops secrets
│   │       ├── hardware-configuration.nix
│   │       └── disk-config.nix
│   └── secrets/
│       └── secrets.enc.yaml                 [TODO] Needs encryption
├── orchestrator/src/orchestrator/
│   ├── commands/
│   │   └── provision.py                    [TODO] Implement
│   ├── pulumi/
│   │   └── automation.py                   [IMPLEMENTED]
│   └── nixos/
│       └── deployer.py                     [IMPLEMENTED]
└── PLAN.md                                  [THIS FILE]
```

---

## Next Steps (In Order)

1. **Encrypt secrets**:
   ```bash
   # Create nixos/secrets/secrets.yaml with password hash and SSH key
   # Then encrypt:
   sops -e nixos/secrets/secrets.yaml > nixos/secrets/secrets.enc.yaml
   ```

2. **Update NixOS config** to read from sops-nix secrets

3. **Sync to ESC**:
   ```bash
   orchestrator config sync
   ```

4. **Install dependencies and add Proxmox provider** to `pulumi/proxmox/index.ts`

5. **Implement `provision` command** in orchestrator

6. **Test provision workflow**

7. **Extract hardware-configuration.nix** from live VM (optional)

8. **Document** in runbook at `docs/runbooks/nixos-vm-provisioning.md`

---

## Known Issues & Considerations

### Cloud-init vs Manual SSH Bootstrap

Current plan uses cloud-init for SSH injection. If cloud-init doesn't work on NixOS ISO:
- **Fallback**: Manual one-time SSH key setup via Proxmox console
- **Alternative**: Use pre-built NixOS image with SSH configured

### Proxmox Provider Configuration

**Installation**:
```bash
cd pulumi/proxmox
npm install
npm install @pulumiverse/proxmox
```

**Configuration needed in ESC**:
- Proxmox API endpoint (e.g., `https://rk1.internal.racknarok.com:8006/api2/json`)
- Proxmox API token with proper permissions
- Provider configuration in Pulumi

**Example implementation** in `index.ts`:
```typescript
import * as proxmox from "@pulumiverse/proxmox";

// Configure provider (credentials come from ESC)
const provider = new proxmox.Provider("proxmox", {
  endpoint: config.require("proxmox_endpoint"),
  apiToken: config.requireSecret("proxmox_api_token"),
  insecure: true, // For internal CA
});

// Create VM
const vm = new proxmox.vm.VirtualMachine(vmName, {
  // ... VM configuration
}, { provider });
```

### First Boot May Be Slow

NixOS installation via nixos-anywhere takes 10-20 minutes:
- Downloading packages
- Building system
- Installing to disk
- Progress indicators needed in orchestrator

### Age Key Security

Age private key is passed via `--extra-files`:
- Creates temporary directory
- nixos-anywhere copies to VM
- Temp directory cleaned up after
- Key lives at `/var/lib/sops-nix/key.txt` on VM
- Protected by VM filesystem permissions

---

## Success Criteria

- [x] Configuration structure created
- [x] NixOS flake builds successfully
- [x] Pulumi project structure created
- [x] Orchestrator integration modules implemented
- [ ] Secrets encrypted and synced to ESC
- [ ] `orchestrator provision` command implemented
- [ ] Can run `orchestrator provision --vm tailscale-router` successfully
- [ ] VM is created in Proxmox
- [ ] NixOS is installed automatically
- [ ] Can SSH to VM with admin key
- [ ] Running provision twice is idempotent
- [ ] Can update NixOS config and re-provision
- [ ] Documentation complete

---

## References

- [nixos-anywhere docs](https://nix-community.github.io/nixos-anywhere/)
- [deploy-rs docs](https://github.com/serokell/deploy-rs)
- [disko docs](https://github.com/nix-community/disko)
- [sops-nix docs](https://github.com/Mic92/sops-nix)
- ADR 003: Python Orchestrator
- ADR 005: Configuration Organization Strategy

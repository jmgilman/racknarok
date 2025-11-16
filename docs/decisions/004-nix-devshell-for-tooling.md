# ADR 004: Nix Devshell for Tool Versioning

## Status

Accepted

## Context

Project Racknarok requires multiple external tools for infrastructure management:
- **Ansible**: Proxmox configuration
- **Pulumi CLI**: Infrastructure deployment
- **SOPS**: Secret encryption/decryption
- **age**: Encryption keys
- **Python**: Orchestrator execution
- **uv**: Python package management
- **just**: Task runner
- **deploy-rs**: NixOS deployment (optional in devshell)

Each tool has specific version requirements. Version mismatches between developers, CI, and different machines can cause:
- Configuration incompatibilities
- Subtle bugs from version-specific behavior
- Failed deployments due to CLI changes
- "Works on my machine" problems

### Requirements

1. **Reproducible environments**: Same tool versions everywhere
2. **Easy onboarding**: New developers/machines get tools automatically
3. **Version pinning**: Lock specific versions of all tools
4. **No global pollution**: Don't interfere with system packages
5. **Cross-platform**: Work on macOS and Linux
6. **Low friction**: Minimal setup, automatic activation
7. **Declarative**: Tool versions defined in code

### Alternatives Considered

**Option 1: Manual Installation**
- **Pros**: Simple, no extra tools
- **Cons**:
  - Version drift between machines
  - Manual dependency tracking
  - Poor onboarding experience
  - No reproducibility guarantees
  - Platform-specific installation steps

**Option 2: Docker/Container**
- **Pros**: Fully isolated, reproducible
- **Cons**:
  - Heavyweight for development environment
  - Complicates file access and networking
  - Slower iteration (rebuilds)
  - Overkill for tool versioning
  - Poor macOS performance (via VM)
  - SSH agent forwarding complexity

**Option 3: asdf Version Manager**
- **Pros**: Multi-language version management, popular
- **Cons**:
  - Requires plugins for each tool
  - Not all tools have asdf plugins (age, sops)
  - Still requires manual installation of asdf
  - No declarative configuration in repo
  - Platform-specific plugin support

**Option 4: Homebrew Bundle**
- **Pros**: Declarative Brewfile, macOS-native
- **Cons**:
  - macOS only (no Linux support)
  - Can't pin exact versions (only latest)
  - No activation/deactivation
  - Installs globally (pollutes system)
  - Homebrew itself requires installation

**Option 5: devenv (Selected)**
- **Pros**:
  - Declarative tool definitions in `devenv.nix`
  - Exact version pinning via devenv.lock
  - Cross-platform (macOS, Linux)
  - Automatic activation via direnv
  - Project-local environment (no global pollution)
  - Reproducible across all machines
  - Rich package repository (nixpkgs)
  - Already using Nix for NixOS VMs
  - Simpler syntax than raw Nix flakes
  - Built-in scripts and tasks support
  - Better developer experience (devenv shell, devenv info, etc.)
- **Cons**:
  - Requires Nix installation (one-time)
  - Learning curve for Nix language (mitigated by devenv's simpler syntax)
  - Larger download/storage footprint
  - macOS requires Determinate Systems installer (recommended)

## Decision

We will use **devenv** (built on Nix) to provide a reproducible development environment with pinned tool versions.

### Architecture

**devenv structure**:
```nix
# devenv.nix (root)
{ pkgs, lib, config, ... }:

{
  env = {
    PULUMI_SKIP_UPDATE_CHECK = "true";
    ANSIBLE_HOST_KEY_CHECKING = "False";
    RACKNAROK_ROOT = config.devenv.root;
  };

  packages = with pkgs; [
    # Infrastructure tools
    ansible_2_16
    pulumi-bin
    sops
    age

    # Python package manager (uv manages Python itself)
    uv

    # Utilities
    jq
    yq-go
    git
    openssh
  ];

  scripts.bootstrap.exec = ''
    uv run orchestrator/orchestrator.py bootstrap "$@"
  '';

  scripts.provision.exec = ''
    uv run orchestrator/orchestrator.py provision "$@"
  '';

  # ... more scripts

  tasks."racknarok:check-tools" = {
    exec = ''
      echo "✓ Ansible: $(ansible --version | head -n1)"
      echo "✓ Pulumi: $(pulumi version)"
      echo "✓ uv: $(uv --version)"
    '';
    before = [ "devenv:enterShell" ];
  };

  enterShell = ''
    cat <<EOF
    🎯 Welcome to Racknarok Development Environment

    Available commands:
      bootstrap <node> - Bootstrap a new Proxmox node
      provision        - Provision VMs via Pulumi
      deploy           - Run full deployment workflow
    EOF
  '';

  dotenv.enable = true;
}
```

```yaml
# devenv.yaml
inputs:
  nixpkgs:
    url: github:NixOS/nixpkgs/nixpkgs-unstable
```

**Activation methods**:

1. **Manual**: `devenv shell`
2. **Automatic (direnv)**: Add `.envrc`:
   ```bash
   #!/usr/bin/env bash
   eval "$(devenv direnvrc)"
   use devenv
   ```

### Tool Versions

**Pinning strategy**:
- devenv inputs pinned in `devenv.lock`
- Specific package versions from nixpkgs
- Lock file committed to Git
- Update via `devenv update`

**Example versions**:
```nix
packages = with pkgs; [
  ansible_2_16      # Ansible 2.16.x (pin specific minor)
  pulumi-bin        # Latest Pulumi (or pin: pulumi-bin_3_113)
  uv                # Latest uv (manages Python itself)
  # ...
];
```

## Consequences

### Positive

1. **Reproducibility**: Same tool versions on all machines and CI
2. **Declarative**: All dependencies defined in `devenv.nix`
3. **Version pinning**: `devenv.lock` ensures exact reproducibility
4. **Easy onboarding**: `devenv shell` or direnv auto-activation
5. **Cross-platform**: Works on macOS and Linux
6. **No conflicts**: Project-local environment, no global pollution
7. **Leverage existing knowledge**: Already using Nix for NixOS VMs
8. **Ecosystem**: Access to 80,000+ packages in nixpkgs
9. **Rollback**: Can pin to older nixpkgs if needed
10. **Better DX**: Scripts, tasks, and simpler syntax than raw Nix flakes
11. **Python via uv**: Let uv manage Python instead of Nix (more reliable)

### Negative

1. **Nix installation required**: One-time setup per machine
2. **devenv installation required**: Additional layer on top of Nix
3. **Learning curve**: Nix language and concepts (reduced by devenv's simpler syntax)
4. **Disk space**: Nix store can grow large (mitigated by gc)
5. **Download size**: Initial setup downloads packages
6. **macOS complexity**: Needs Determinate Systems installer for best experience
7. **Slower first activation**: Downloads and builds packages

### Mitigation

- **Documentation**: Clear setup instructions in README
- **Minimal Nix knowledge needed**: devenv's syntax is simpler than raw flakes
- **Determinate Systems installer**: Handles macOS complexity
- **Garbage collection**: Regular `nix-collect-garbage` or `devenv gc` to clean up
- **Binary cache**: Most packages pre-built, minimal compilation
- **uv handles Python**: No need to understand Nix Python packaging

## Implementation Notes

### Setup Instructions

**For new developers**:

1. **Install Nix** (macOS):
   ```bash
   curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix | sh -s -- install
   ```

2. **Install devenv**:
   ```bash
   nix profile install nixpkgs#devenv
   ```

3. **Clone repository**:
   ```bash
   git clone https://github.com/yourusername/infra.git
   cd infra
   ```

4. **Activate environment**:
   ```bash
   devenv shell
   # Or with direnv:
   direnv allow
   ```

### CI Integration

**GitHub Actions**:
```yaml
- name: Install Nix
  uses: DeterminateSystems/nix-installer-action@main

- name: Install devenv
  run: nix profile install nixpkgs#devenv

- name: Load dev environment
  run: devenv shell pulumi preview
```

### Tool Updates

**Updating all tools**:
```bash
devenv update
git add devenv.lock
git commit -m "chore: update tool versions"
```

**Updating specific input** (via devenv.yaml):
```yaml
inputs:
  nixpkgs:
    url: github:NixOS/nixpkgs/abc123def456  # Pin to specific commit
```

### Devshell vs NixOS VMs

**Separate concerns**:
- **Root `devenv.nix`**: Developer tooling (Ansible, Pulumi, etc.)
- **`nixos/flake.nix`**: NixOS VM configurations

**Why separate**:
- Different purposes (dev tools vs system config)
- Can update independently
- VM configs don't need dev tools
- Dev environment doesn't need VM system packages

### direnv Integration

**.envrc**:
```bash
#!/usr/bin/env bash
eval "$(devenv direnvrc)"
use devenv

# Note: devenv has built-in dotenv support (dotenv.enable = true)
```

**Benefits**:
- Automatic activation when entering directory
- Automatic deactivation when leaving
- Fast subsequent activations (cached)
- No manual `nix develop` needed

## Tool-Specific Considerations

### Ansible

**Version pinning**:
```nix
ansible_2_16  # Pin to 2.16.x branch (stable)
```

**Why**: Ansible modules change between versions, role compatibility

### Pulumi

**Options**:
```nix
pulumi-bin        # Latest version (auto-updates)
# OR
pulumi-bin_3_113  # Pin specific version
```

**Recommendation**: Pin specific version for stability

### Python/uv

**Rationale**:
- Orchestrator uses uv with inline dependencies
- devenv provides only uv (not Python itself)
- uv downloads and manages Python + all dependencies
- More reliable than Nix's Python packaging
- Faster updates for Python packages

### deploy-rs

**Decision**: Keep in `nixos/flake.nix`
- Only needed for NixOS deployments
- Keeps root devenv lighter
- Can add to root if needed for orchestrator integration

## Future Considerations

### If team grows

- **Binary cache**: Set up shared cache for faster setup (Cachix)
- **devenv CI**: Use devenv in CI for consistent environments
- **Pre-commit hooks**: Enable devenv's pre-commit integration

### Advanced features

- **devenv containers**: Export environment as OCI container
- **devenv processes**: Run background services (databases, etc.)
- **Custom tasks**: More sophisticated task dependencies

### If Nix becomes burdensome

- **Alternative**: Could fall back to asdf + Brewfile, or plain Nix flakes
- **Hybrid**: Nix for Linux, Homebrew for macOS
- **Unlikely**: devenv solves real problems and improves on raw Nix

## Onboarding Experience

**Before (manual installation)**:
```
1. Install Python 3.12
2. Install Ansible 2.16
3. Install Pulumi
4. Install SOPS
5. Install age
6. Install uv
7. Install just
... hope versions match
```

**After (with devenv)**:
```
1. Install Nix (one-time)
2. Install devenv (one-time)
3. cd infra && devenv shell
   (or direnv allow)

All tools ready ✓
```

## References

- [devenv Documentation](https://devenv.sh/)
- [devenv GitHub](https://github.com/cachix/devenv)
- [Determinate Systems Nix Installer](https://github.com/DeterminateSystems/nix-installer)
- [direnv](https://direnv.net/)
- [uv - Python Package Manager](https://github.com/astral-sh/uv)

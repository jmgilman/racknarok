# Pulumi ESC Sync Project

Syncs configuration and secrets from Git to Pulumi ESC environments.

## Overview

This Pulumi project reads `config/esc-mapping.yaml` from the repository root and:

1. Loads config files (plain YAML) from `config/` directory
2. Decrypts and loads secret files (SOPS-encrypted) from `secrets/` directory
3. Merges them together (secrets override config)
4. Wraps all secret values with `fn::secret`
5. Creates/updates Pulumi ESC environments

## Prerequisites

- **SOPS**: Must be installed and available in PATH
- **Age key**: SOPS private key must be available for decryption
- **Pulumi access**: Must be authenticated to Pulumi Cloud

## Usage

### First Time Setup

```bash
# Install dependencies
npm install

# Login to Pulumi (if not already)
pulumi login

# Select the prod stack
pulumi stack select prod
```

### Sync Config to ESC

```bash
# Preview changes
pulumi preview

# Apply changes
pulumi up
```

## Project Structure

```
pulumi/esc-sync/
├── index.ts              # Main Pulumi program
├── lib/
│   ├── types.ts         # TypeScript type definitions
│   ├── sops.ts          # SOPS decryption wrapper
│   └── loader.ts        # Config/secrets loader and merger
├── package.json          # Dependencies
├── tsconfig.json        # TypeScript configuration
└── Pulumi.yaml          # Pulumi project definition
```

## How It Works

### 1. ESC Mapping

The `config/esc-mapping.yaml` file defines which files belong to which environments:

```yaml
environments:
  proxmox:
    config:
      - config/proxmox/cluster.yaml
      - config/proxmox/nodes.yaml
    secrets:
      - secrets/proxmox/api.enc.yaml
      - secrets/proxmox/ssh.enc.yaml
```

### 2. Loading and Merging

For each environment:
- All `config` files are loaded and merged
- All `secrets` files are decrypted and merged
- Secrets override config if keys conflict
- Secret values are wrapped with `fn::secret`

### 3. ESC Environment Creation

Creates a `pulumiservice.Environment` resource for each environment with:
- Organization: `jmgilman`
- Project: `racknarok`
- Name: Environment name (e.g., `proxmox`)
- YAML: Merged configuration in ESC format

## Environment Variables

The project uses standard Pulumi and SOPS environment variables:

- `PULUMI_ACCESS_TOKEN`: Pulumi Cloud access token (or use `pulumi login`)
- `SOPS_AGE_KEY` or `SOPS_AGE_KEY_FILE`: Age private key for SOPS decryption

## Outputs

The program exports:

- `organizationName`: Organization name (`jmgilman`)
- `projectName`: Project name (`racknarok`)
- `environmentNames`: List of environment names synced
- `environmentCount`: Number of environments synced
- `environmentRevisions`: Object mapping environment names to their revision numbers

## CI/CD Integration

This project can be run in GitHub Actions:

```yaml
- name: Sync config to ESC
  run: |
    cd pulumi/esc-sync
    pulumi up --yes
  env:
    PULUMI_ACCESS_TOKEN: ${{ secrets.PULUMI_ACCESS_TOKEN }}
    SOPS_AGE_KEY: ${{ secrets.SOPS_AGE_KEY }}
```

## Notes

- Git is the single source of truth
- ESC is a distribution mechanism
- All secrets are automatically encrypted by ESC
- Environments can be reconstructed from Git at any time

# Secrets

This directory contains encrypted secrets for Project Racknarok infrastructure.

All secrets are encrypted using [SOPS](https://github.com/getsops/sops) with [age](https://age-encryption.org/) encryption.

## Structure

```
secrets/
├── .sops.yaml                    # SOPS configuration
├── proxmox/                      # Proxmox secrets
│   ├── api.enc.yaml              # API tokens and credentials
│   ├── network.enc.yaml          # Sensitive network info (public IPs)
│   ├── ssh.enc.yaml              # SSH keys for host access
│   └── certificates.enc.yaml    # SSL certificates (future)
└── README.md                     # This file
```

## Bootstrap Process

Before you can create or edit encrypted secrets, you must initialize SOPS:

```bash
# Generate age key pair and configure SOPS
./scripts/bootstrap-sops.sh
```

This script uses Pulumi ESC as the source of truth for the age key:

**First time (no key exists anywhere):**
1. Generates a new age key pair
2. Uploads the private key to Pulumi ESC (`jmgilman/ci`)
3. Saves the key locally at `secrets/.age-key.txt` (gitignored)
4. Updates `.sops.yaml` with the public key

**On additional machines:**
1. Checks if key exists in ESC (`jmgilman/ci`)
2. Downloads it to `secrets/.age-key.txt`
3. Updates `.sops.yaml` with the public key

**Benefits:**
- No need to manually back up keys - ESC is the backup
- Clone repo on new machine, run script, and you're ready
- Team members can easily get access to secrets
- Key is never in version control

## Working with Secrets

### Creating a New Secret File

1. Create the secret file with plaintext content:
   ```bash
   cat > secrets/proxmox/example.yaml <<EOF
   my_secret: super_secret_value
   EOF
   ```

2. Encrypt it with SOPS:
   ```bash
   sops -e secrets/proxmox/example.yaml > secrets/proxmox/example.enc.yaml
   rm secrets/proxmox/example.yaml
   ```

3. Commit the encrypted file:
   ```bash
   git add secrets/proxmox/example.enc.yaml
   git commit -m "Add example secret"
   ```

### Editing an Encrypted Secret

SOPS provides a convenient editor:

```bash
sops secrets/proxmox/api.enc.yaml
```

This will:
1. Decrypt the file temporarily
2. Open it in your `$EDITOR`
3. Re-encrypt it when you save and exit

### Viewing an Encrypted Secret

To view without editing:

```bash
sops -d secrets/proxmox/api.enc.yaml
```

## Secret Files

### Proxmox Secrets

- **`api.enc.yaml`**: Proxmox API credentials
  - API token ID and secret for each node
  - Alternative user/password authentication

- **`network.enc.yaml`**: Sensitive network configuration
  - Public IP addresses (not in public repo)
  - Gateway addresses
  - Failover IPs

- **`ssh.enc.yaml`**: SSH keys for host access
  - Admin key (used for initial setup and ongoing automation)

- **`certificates.enc.yaml`**: SSL certificates (future)
  - Custom certificates for Proxmox web UI
  - Currently using self-signed certs

## SOPS Configuration

The `.sops.yaml` file defines encryption rules:

```yaml
creation_rules:
  - path_regex: \.enc\.yaml$
    age: age1xxxxxxxxxx...
```

All files matching `*.enc.yaml` will be encrypted with the specified age key.

**Key Location**: The age private key is stored at `secrets/.age-key.txt` (repo-local). SOPS will automatically find it by checking:
1. `SOPS_AGE_KEY_FILE` environment variable
2. `secrets/.age-key.txt` (when running from repo root)
3. `~/.config/sops/age/keys.txt` (fallback)

Since we use a repo-local key, you should set the environment variable:
```bash
export SOPS_AGE_KEY_FILE="$PWD/secrets/.age-key.txt"
```

Or let the devenv shell handle it automatically (recommended).

## Security Notes

1. **Never commit unencrypted secrets** to Git
2. **Always use `.enc.yaml` extension** for encrypted files
3. **Keep age private key secure** - store in password manager
4. **Verify encryption** before committing:
   ```bash
   # Should show encrypted content, not plaintext
   cat secrets/proxmox/api.enc.yaml
   ```

## Integration with Pulumi ESC

Encrypted secrets are automatically synced to Pulumi ESC:

1. Secrets are decrypted (locally or in CI)
2. Synced to ESC environments via `pulumi/esc-sync/`
3. Consumed by infrastructure code at runtime

See `config/esc-mapping.yaml` for the mapping configuration.

## See Also

- [ADR 001](../docs/decisions/001-sops-esc-secrets-management.md) - SOPS + ESC architecture
- [SOPS Documentation](https://github.com/getsops/sops)
- [age Documentation](https://age-encryption.org/)

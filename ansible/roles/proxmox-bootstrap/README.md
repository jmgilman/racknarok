# Proxmox Bootstrap Ansible Role

This role bootstraps a fresh Proxmox VE installation with Tailscale and security lockdown.

## Purpose

This is a **one-time bootstrap operation** performed on each new Proxmox physical server. It:

1. Installs and configures Tailscale with OAuth authentication
2. Joins the Proxmox host to the Tailscale network (no route advertisement)
3. Enables Tailscale SSH for secure remote access
4. Locks down public access to Proxmox web interface
5. Configures UFW firewall to only allow Tailscale access

**Note**: Subnet routing for vRack is handled by a dedicated router VM, not the Proxmox hosts.

## How It Works

### Execution Order

This role uses Ansible's dependency system. The execution order is:

1. **Dependencies execute FIRST** (`meta/main.yml`)
   - `artis3n.tailscale.machine` role installs and configures Tailscale
   - Variables are passed to the dependency from this role's scope
   - Tailscale is fully installed and connected

2. **Role tasks execute AFTER** (`tasks/main.yml`)
   - Verify Tailscale installation and connection
   - Configure UFW firewall rules
   - Lock down public access to Proxmox
   - Display completion message

### Variable Flow

```
Caller (orchestrator) provides extravars
    ↓
defaults/main.yml provides defaults for optional vars
    ↓
meta/main.yml dependency receives all vars
    ↓
artis3n.tailscale.machine installs Tailscale
    ↓
tasks/main.yml performs post-installation tasks
```

**Important**: Variable validation must happen in the **caller** (orchestrator), not in this role, because dependencies execute before role tasks.

## Requirements

- **Ansible**: 2.12 or higher
- **Target OS**: Debian 11 (Bullseye) or Debian 12 (Bookworm) - Proxmox VE
- **Collections**:
  - `artis3n.tailscale` - Install with: `ansible-galaxy collection install artis3n.tailscale`
  - `community.general` - For UFW management

## Role Variables

### Required Variables

These **must** be provided when calling the role:

| Variable | Description | Example |
|----------|-------------|---------|
| `tailscale_authkey` | Tailscale OAuth client secret | `tskey-client-xxxxx` |
| `tailscale_tags` | ACL tags for the node (required for OAuth) | `['proxmox']` |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `skip_tailscale` | `false` | Skip Tailscale installation (testing only) |
| `tailscale_oauth_ephemeral` | `false` | Register as ephemeral node |
| `tailscale_oauth_preauthorized` | `true` | Skip manual device approval |
| `tailscale_state` | `latest` | Tailscale package state (`latest`, `present`) |
| `tailscale_enable_ssh` | `true` | Enable Tailscale SSH |
| `firewall_enable` | `true` | Enable firewall lockdown |
| `proxmox_web_port` | `8006` | Proxmox web interface port |
| `public_interface` | `vmbr0` | Public network interface |
| `tailscale_verbose` | `true` | Enable verbose output |

## Dependencies

This role depends on:
- `artis3n.tailscale.machine` - Handles Tailscale installation and configuration

The dependency is declared in `meta/main.yml` and will be automatically included.

## Example Usage

### Via ansible-runner (Python)

```python
import ansible_runner

result = ansible_runner.run(
    private_data_dir='/tmp/ansible-bootstrap',
    role='proxmox-bootstrap',
    role_vars={
        'tailscale_authkey': 'tskey-client-xxxxx',
        'tailscale_tags': ['proxmox'],
    },
    inventory={
        'all': {
            'hosts': {
                'rk1': {
                    'ansible_host': 'public.ip.address',
                    'ansible_user': 'root',
                }
            }
        }
    }
)
```

### Via Playbook

```yaml
- name: Bootstrap Proxmox node
  hosts: proxmox
  roles:
    - role: proxmox-bootstrap
      vars:
        tailscale_authkey: "{{ lookup('env', 'TAILSCALE_OAUTH_SECRET') }}"
        tailscale_tags:
          - proxmox
```

## Post-Bootstrap Steps

After the role completes successfully:

1. **Verify node appears in Tailscale**:
   - Go to https://login.tailscale.com/admin/machines
   - Verify your Proxmox node is connected
   - Check that it has a Tailscale IP address

2. **Verify Tailscale access**:
   - Connect to your Tailscale network
   - Access Proxmox: `https://<node-name>:8006`
   - Test SSH: `ssh root@<node-name>`

3. **Deploy subnet router VM**:
   - A dedicated NixOS router VM is needed to advertise vRack subnet to Tailscale
   - See architecture documentation for subnet router deployment

4. **Disable public SSH** (optional, recommended):
   ```bash
   ssh root@<node-name>
   sudo ufw delete allow 22/tcp
   sudo ufw reload
   ```

## Security Notes

- The role leaves public SSH (port 22) open initially to prevent lockout during bootstrap
- Proxmox web interface (port 8006) is immediately blocked from public access
- Only Tailscale network can access Proxmox after bootstrap
- A warning file is created at `/root/TAILSCALE_BOOTSTRAP_README.txt` with instructions

## Firewall Rules Applied

- **Allow**: Tailscale UDP port 41641 (from anywhere)
- **Allow**: SSH port 22 (from anywhere, for initial setup)
- **Allow**: Proxmox port 8006 (only from Tailscale interface)
- **Deny**: Proxmox port 8006 (from public internet)
- **Default**: Deny all other incoming, allow outgoing

## Troubleshooting

### Tailscale not connecting

Check Tailscale status:
```bash
tailscale status
journalctl -u tailscaled -f
```

### Cannot access Proxmox after bootstrap

1. Verify you're connected to Tailscale
2. Check firewall rules: `sudo ufw status verbose`
3. Verify Tailscale interface: `ip addr show tailscale0`

### Locked out of SSH

If you accidentally block yourself, you'll need to use OVH's rescue mode or KVM console to fix the firewall rules.

## License

MIT

## Author

Project Racknarok

/**
 * Pulumi Proxmox Project
 *
 * Provisions NixOS VMs on Proxmox infrastructure.
 *
 * Configuration is loaded from Pulumi ESC environments:
 * - nixos-vms: VM definitions and configuration
 * - proxmox: Proxmox API credentials and node configuration
 *
 * This program will:
 * 1. Configure the Proxmox provider from ESC
 * 2. Load VM definitions from ESC
 * 3. Create VMs with cloud-init for SSH key injection
 * 4. Export VM information for orchestrator
 */

import * as pulumi from '@pulumi/pulumi';
import * as proxmox from '@muhlba91/pulumi-proxmoxve';

// ============================================================================
// Configuration Types
// ============================================================================

interface NetworkConfig {
  bridge: string;
  ip: string;
  gateway: string;
  nameservers: string[];
}

interface VMConfig {
  name: string;
  description: string;
  node: string;
  cpus: number;
  memory: number;
  disk: number;
  network: NetworkConfig;
  nixos_config: string;
}

interface ProxmoxNodeApiConfig {
  endpoint: string;
  token_id: string;
  token_secret: string;
  insecure: boolean;
}

interface SSHConfig {
  admin: {
    public_key: string;
    private_key: string;
  };
}

// ============================================================================
// Load Configuration from ESC
// ============================================================================

// ESC environment values are exposed via pulumiConfig (nested under values)
// They are accessible as unprefixed keys (e.g., "vms", "api", "ssh")
const config = new pulumi.Config();

// Get VM definitions from nixos-vms environment
const vms = config.requireObject<VMConfig[]>('vms');

// Get Proxmox API configuration (nested object)
const api = config.requireObject<{ nodes: Record<string, ProxmoxNodeApiConfig> }>('api');
const proxmoxApi = api.nodes;

// Get SSH configuration from proxmox environment
const sshConfig = config.requireObject<SSHConfig>('ssh');
const sshPublicKey = sshConfig.admin.public_key;

// ============================================================================
// Configure Proxmox Provider
// ============================================================================

const nodeConfig = proxmoxApi['rk1'];

if (!nodeConfig) {
  throw new Error('Proxmox node "rk1" configuration not found in ESC');
}

const provider = new proxmox.Provider('proxmox', {
  endpoint: nodeConfig.endpoint,
  insecure: nodeConfig.insecure,
  apiToken: `${nodeConfig.token_id}=${nodeConfig.token_secret}`,
});

// ============================================================================
// NixOS Installer ISO
// ============================================================================

// Reference to NixOS minimal installer ISO on Proxmox storage
// The ISO is automatically downloaded by Ansible during Proxmox bootstrap
// (ansible/roles/proxmox-bootstrap/tasks/download-isos.yml)
// Format: <datastore>:iso/<filename>
const nixosIsoFileId = 'local:iso/nixos-minimal-23.11.iso';

// ============================================================================
// Create VMs
// ============================================================================

const createdVMs: Record<string, proxmox.vm.VirtualMachine> = {};

for (const vmDef of vms) {
  const vmName = vmDef.name;

  pulumi.log.info(`Creating VM: ${vmName}`);

  // Extract IP address without CIDR notation
  const vmIp = vmDef.network.ip.split('/')[0];
  const vmCidr = vmDef.network.ip;

  // Create VM with NixOS installer ISO attached
  // The VM will boot from the ISO, then nixos-anywhere will install NixOS
  const vm = new proxmox.vm.VirtualMachine(vmName, {
    nodeName: vmDef.node,
    name: vmName,
    description: vmDef.description,
    tags: ['nixos', 'pulumi', 'infrastructure'],

    // QEMU Guest Agent (will be enabled after NixOS is installed)
    agent: {
      enabled: true,
      trim: true,
      type: 'virtio',
    },

    // BIOS configuration
    bios: 'seabios',

    // CPU configuration
    cpu: {
      cores: vmDef.cpus,
      sockets: 1,
      type: 'host',  // Use host CPU for best performance
    },

    // Memory configuration (in MB)
    memory: {
      dedicated: vmDef.memory,
    },

    // Disk configuration - empty disk that nixos-anywhere will partition and format
    disks: [{
      interface: 'scsi0',
      datastoreId: 'nvme-pool',  // ZFS pool on NVMe
      size: vmDef.disk,
      fileFormat: 'raw',  // ZFS uses raw format
      iothread: true,
      ssd: true,
      discard: 'on',  // Enable TRIM for SSD
    }],

    // CD-ROM with NixOS installer ISO
    // The VM will boot from this ISO initially
    cdrom: {
      enabled: true,
      fileId: nixosIsoFileId,  // Reference to the manually downloaded ISO
      interface: 'ide2',
    },

    // Network configuration
    networkDevices: [{
      bridge: vmDef.network.bridge,
      model: 'virtio',
      firewall: false,
    }],

    // Operating system type
    operatingSystem: {
      type: 'l26',  // Linux 2.6+ kernel
    },

    // Boot order: CD-ROM first, then disk
    // This allows the VM to boot from ISO initially
    // After nixos-anywhere installs, it will boot from disk
    bootOrders: ['ide2', 'scsi0'],  // CD-ROM (ide2), then disk (scsi0)

    // Boot configuration
    onBoot: true,     // Start VM on Proxmox boot
    started: true,    // Start VM immediately after creation

    // Serial console for debugging
    serialDevices: [{}],
  }, {
    provider,
    // Protect VMs from accidental deletion
    protect: false,  // Set to true in production
    // Ignore IP address changes since guest agent won't be available until NixOS is installed
    ignoreChanges: ['ipv4Addresses', 'ipv6Addresses'],
  });

  createdVMs[vmName] = vm;
}

// ============================================================================
// Exports
// ============================================================================

// Export VM IDs
export const vmIds = Object.entries(createdVMs).reduce((acc, [name, vm]) => {
  acc[name] = vm.vmId;
  return acc;
}, {} as Record<string, pulumi.Output<number>>);

// Export VM names
export const vmNames = Object.keys(createdVMs);

// Note: VM IP addresses not exported until NixOS is installed and guest agent is running
// The VMs boot from ISO initially, so guest agent is not available for IP detection

// Export VM count
export const vmCount = Object.keys(createdVMs).length;

// Export provider endpoint (for debugging)
export const proxmoxEndpoint = nodeConfig.endpoint;

// Export NixOS ISO information
export const nixosIsoId = nixosIsoFileId;

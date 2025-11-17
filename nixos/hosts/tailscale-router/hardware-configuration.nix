# Hardware configuration for Proxmox VM
# This is a template - nixos-anywhere will generate the actual hardware configuration
# based on the VM's hardware during installation

{ config, lib, pkgs, modulesPath, ... }:

{
  imports = [
    (modulesPath + "/profiles/qemu-guest.nix")
  ];

  boot.initrd.availableKernelModules = [
    "ata_piix"
    "uhci_hcd"
    "virtio_pci"
    "virtio_scsi"
    "sd_mod"
    "sr_mod"
  ];

  boot.initrd.kernelModules = [ ];
  boot.kernelModules = [ ];
  boot.extraModulePackages = [ ];

  # Filesystem configuration
  # Note: This is managed by disko during nixos-anywhere installation
  fileSystems."/" = {
    device = "/dev/vda1";
    fsType = "ext4";
  };

  swapDevices = [ ];

  nixpkgs.hostPlatform = lib.mkDefault "x86_64-linux";
}

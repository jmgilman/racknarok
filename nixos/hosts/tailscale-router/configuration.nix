{ config, pkgs, lib, ... }:

{
  imports = [
    ./hardware-configuration.nix
  ];

  # System configuration
  system.stateVersion = "24.05";

  # Boot loader configuration
  boot.loader.grub = {
    enable = true;
    device = "/dev/vda";
  };

  # Networking
  networking = {
    hostName = "tailscale-router";
    useDHCP = false;

    interfaces.ens18 = {
      ipv4.addresses = [{
        address = "10.0.0.10";
        prefixLength = 24;
      }];
    };

    defaultGateway = "10.0.0.1";
    nameservers = [ "1.1.1.1" "8.8.8.8" ];

    # Enable IP forwarding (for subnet routing)
    firewall = {
      enable = true;
      trustedInterfaces = [ "tailscale0" ];
      # Allow forwarding for subnet routing
      checkReversePath = "loose";
    };
  };

  # Enable QEMU guest agent for Proxmox
  services.qemu-guest-agent.enable = true;

  # SSH configuration
  services.openssh = {
    enable = true;
    settings = {
      PermitRootLogin = "prohibit-password";
      PasswordAuthentication = false;
    };
  };

  # SOPS secrets management
  sops = {
    defaultSopsFile = ../../secrets/secrets.yaml;
    age.keyFile = "/var/lib/sops-nix/key.txt";

    secrets = {
      # Root password hash
      root_password_hash = {
        neededForUsers = true;
      };
    };
  };

  # Users
  users.users.root = {
    # Password from SOPS
    hashedPasswordFile = config.sops.secrets.root_password_hash.path;

    # SSH keys for root user (from Proxmox admin SSH key)
    openssh.authorizedKeys.keys = [
      # This will be populated via cloud-init on first boot
      # and then managed by deploy-rs
    ];
  };

  # Essential system packages
  environment.systemPackages = with pkgs; [
    vim
    git
    htop
    tmux
    curl
    wget
  ];

  # Enable nix flakes
  nix.settings.experimental-features = [ "nix-command" "flakes" ];

  # Automatic garbage collection
  nix.gc = {
    automatic = true;
    dates = "weekly";
    options = "--delete-older-than 30d";
  };

  # Note: Tailscale configuration will be added in a future iteration
  # For now, this is just the foundation to get NixOS running
}

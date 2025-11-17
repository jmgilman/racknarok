{
  description = "NixOS configurations for Racknarok infrastructure VMs";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

    deploy-rs = {
      url = "github:serokell/deploy-rs";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    sops-nix = {
      url = "github:Mic92/sops-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    disko = {
      url = "github:nix-community/disko";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, deploy-rs, sops-nix, disko }: {
    # NixOS configurations
    nixosConfigurations = {
      tailscale-router = nixpkgs.lib.nixosSystem {
        system = "x86_64-linux";
        modules = [
          ./hosts/tailscale-router/configuration.nix
          ./hosts/tailscale-router/disk-config.nix
          sops-nix.nixosModules.sops
          disko.nixosModules.disko
        ];
      };
    };

    # deploy-rs configuration
    deploy.nodes = {
      tailscale-router = {
        hostname = "10.0.0.10";
        sshUser = "root";
        profiles.system = {
          user = "root";
          path = deploy-rs.lib.x86_64-linux.activate.nixos
            self.nixosConfigurations.tailscale-router;
        };
      };
    };

    # Check that deploy-rs configurations are valid
    checks = builtins.mapAttrs
      (system: deployLib: deployLib.deployChecks self.deploy)
      deploy-rs.lib;
  };
}

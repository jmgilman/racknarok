# Disko disk configuration for nixos-anywhere
# This defines how the disk should be partitioned and formatted

{ ... }:

{
  disko.devices = {
    disk = {
      main = {
        device = "/dev/vda";
        type = "disk";
        content = {
          type = "gpt";
          partitions = {
            # BIOS boot partition
            boot = {
              size = "1M";
              type = "EF02";
            };
            # Root partition
            root = {
              size = "100%";
              content = {
                type = "filesystem";
                format = "ext4";
                mountpoint = "/";
              };
            };
          };
        };
      };
    };
  };
}

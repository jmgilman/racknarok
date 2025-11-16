{ pkgs, lib, config, ... }:

{
  # https://devenv.sh/basics/
  env = {
    PULUMI_SKIP_UPDATE_CHECK = "true";
    ANSIBLE_HOST_KEY_CHECKING = "False";
    RACKNAROK_ROOT = config.devenv.root;
    SOPS_CONFIG_FILE = "${config.devenv.root}/secrets/.sops.yaml";
    SOPS_AGE_KEY_FILE = "${config.devenv.root}/secrets/.age-key.txt";
    # Pulumi organization
    PULUMI_ORG = "jmgilman";
  };

  # https://devenv.sh/packages/
  packages = with pkgs; [
    # Infrastructure tools
    ansible_2_16
    pulumi-bin
    pulumi-esc  # Pulumi ESC CLI for secrets management
    sops
    age

    # Python package manager (manages Python itself)
    uv

    # Utilities
    jq
    yq-go
    git
    openssh
  ];

  # https://devenv.sh/scripts/
  scripts.bootstrap.exec = ''
    echo "🚀 Bootstrapping Proxmox node..."
    echo "Usage: bootstrap <node-name>"
    uv run --directory orchestrator orchestrator bootstrap "$@"
  '';

  scripts.provision.exec = ''
    echo "🏗️  Provisioning VMs..."
    uv run --directory orchestrator orchestrator provision "$@"
  '';

  scripts.deploy.exec = ''
    echo "🚢 Running full deployment..."
    uv run --directory orchestrator orchestrator deploy "$@"
  '';

  scripts.sync-config.exec = ''
    echo "🔄 Syncing config to ESC..."
    uv run --directory orchestrator orchestrator sync-config "$@"
  '';

  scripts.edit-secret = {
    exec = ''
      if [ -z "$1" ]; then
        echo "Usage: edit-secret <path/to/secret.enc.yaml>"
        exit 1
      fi
      sops "$1"
    '';
    description = "Edit an encrypted secret file with SOPS";
  };

  scripts.encrypt-secret = {
    exec = ''
      if [ -z "$1" ]; then
        echo "Usage: encrypt-secret <path/to/plaintext.yaml>"
        exit 1
      fi
      sops -e "$1" > "''${1%.yaml}.enc.yaml"
      echo "Encrypted: ''${1%.yaml}.enc.yaml"
    '';
    description = "Encrypt a plaintext file with SOPS";
  };

  # https://devenv.sh/tasks/
  tasks."racknarok:check-tools" = {
    exec = ''
      echo "Checking installed tools..."
      echo "✓ Ansible: $(ansible --version | head -n1)"
      echo "✓ Pulumi: $(pulumi version)"
      echo "✓ SOPS: $(sops --version)"
      echo "✓ uv: $(uv --version)"
      echo ""
      echo "Python will be managed by uv when running orchestrator"
    '';
    before = [ "devenv:enterShell" ];
  };

  # https://devenv.sh/reference/options/
  enterShell = ''
    cat <<EOF

    🎯 Welcome to Racknarok Development Environment

    Available commands:
      bootstrap <node>      - Bootstrap a new Proxmox node
      provision             - Provision VMs via Pulumi
      deploy                - Run full deployment workflow
      sync-config           - Sync config/secrets to ESC
      edit-secret <file>    - Edit encrypted secret
      encrypt-secret <file> - Encrypt a plaintext file

    Or use the orchestrator directly:
      uv run orchestrator/orchestrator.py --help

EOF
  '';

  # Load .env file if it exists (for local overrides)
  # https://devenv.sh/basics/#dotenv
  dotenv.enable = true;
}

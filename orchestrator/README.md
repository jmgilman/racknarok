# Racknarok Infrastructure Orchestrator

A CLI tool for coordinating deployment workflows across Ansible, Pulumi, and deploy-rs.

## Overview

The orchestrator provides a unified interface for managing Project Racknarok infrastructure:

- **Bootstrap**: Initialize Proxmox nodes with Tailscale and security lockdown
- **Provision**: Create VMs via Pulumi Automation API
- **Configure**: Deploy NixOS configurations via deploy-rs
- **Deploy**: Execute full deployment workflow
- **Sync**: Synchronize configuration and secrets to Pulumi ESC

## Installation

Using uv (recommended):

```bash
# Install in development mode
uv pip install -e .

# Or run directly with uv
uv run orchestrator --help
```

## Usage

```bash
# Bootstrap a Proxmox node
orchestrator bootstrap rk1

# Provision VMs
orchestrator provision

# Configure NixOS VMs
orchestrator configure

# Full deployment workflow
orchestrator deploy

# Sync config to ESC
orchestrator sync-config
```

## Project Structure

```
orchestrator/
├── src/orchestrator/
│   ├── __init__.py          # Package initialization
│   ├── cli.py               # Main CLI entry point
│   ├── context.py           # Shared context/state
│   ├── config.py            # ESC configuration loading
│   ├── commands/            # CLI commands
│   │   ├── bootstrap.py
│   │   ├── provision.py
│   │   ├── configure.py
│   │   ├── deploy.py
│   │   └── sync.py
│   ├── ansible/             # Ansible integration
│   │   ├── inventory.py     # Dynamic inventory
│   │   └── runner.py        # Ansible runner wrapper
│   ├── pulumi/              # Pulumi integration
│   │   └── automation.py    # Automation API wrapper
│   ├── nixos/               # NixOS integration
│   │   └── deployer.py      # deploy-rs wrapper
│   └── utils/               # Utilities
│       ├── ssh.py           # SSH key management
│       └── output.py        # Pretty output formatting
├── pyproject.toml           # Project configuration
└── README.md
```

## Design Principles

- **Absolute imports**: All imports use full paths (e.g., `from orchestrator.config import load_esc_config`)
- **Separation of concerns**: Each module has a single, focused responsibility
- **Click command groups**: Commands organized using Click's group system
- **Shared context**: State passed between commands via `OrchestratorContext`
- **Type hints**: Full type annotations throughout

## Development

```bash
# Install with dev dependencies
uv pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy src/orchestrator

# Linting
ruff check src/orchestrator
```

## Implementation Status

All modules are currently stubs with TODOs marking implementation points. This provides a solid foundation for incremental development.

# ADR 003: Python Orchestrator for Deployment Workflows

## Status

Accepted

## Context

Project Racknarok uses multiple tools for infrastructure management:
- **Ansible**: Proxmox host configuration
- **Pulumi**: VM provisioning
- **deploy-rs**: NixOS configuration deployment

Each tool has its own CLI, configuration format, and execution model. Deployment workflows require coordinating these tools in sequence with proper error handling, credential management, and configuration sourcing from Pulumi ESC.

### Requirements

1. **Coordination**: Execute multiple tools in correct order
2. **ESC integration**: Pull configuration from Pulumi ESC environments
3. **Credential management**: Handle SSH keys from ESC securely
4. **Dynamic inventory**: Generate Ansible inventory from ESC data
5. **Automation API**: Programmatic access to Pulumi (not just CLI)
6. **Error handling**: Graceful failures, clear error messages
7. **Simplicity**: Lightweight tool for a playground project
8. **Version pinning**: Reproducible execution environment

### Alternatives Considered

**Option 1: Bash Scripts**
- **Pros**: Simple, no dependencies, universally available
- **Cons**:
  - ESC SDK not available for bash
  - Pulumi Automation API requires a real programming language
  - ansible-runner more complex from bash
  - Poor error handling and data structure manipulation
  - Becomes unmaintainable as complexity grows

**Option 2: Make/Justfile Only**
- **Pros**: Simple task runner, familiar to developers
- **Cons**:
  - Not a programming language (limited logic)
  - Can't integrate with ESC SDK or Pulumi Automation API
  - Would just shell out to scripts (defeats purpose)
  - No credential management capabilities

**Option 3: Go**
- **Pros**: Compiled, fast, good for tooling, Pulumi SDK available
- **Cons**:
  - Overkill for coordination scripts
  - More boilerplate than Python
  - Slower development iteration
  - ansible-runner not available for Go
  - Over-engineering for playground

**Option 4: TypeScript/Node.js**
- **Pros**: Pulumi Automation API available, good async support
- **Cons**:
  - ansible-runner not available for Node
  - Another runtime to manage
  - ESC SDK less mature than Python
  - Node ecosystem more complex for CLI tools

**Option 5: Python (Selected)**
- **Pros**:
  - Pulumi Automation API fully supported
  - ansible-runner is Python-native
  - ESC SDK available and mature
  - Excellent for scripting and glue code
  - `uv` enables single-file scripts with inline dependencies
  - Rich ecosystem for SSH, process management, etc.
  - Fast development iteration
- **Cons**:
  - Runtime dependency (mitigated by Nix devshell)
  - Slower than compiled languages (irrelevant for this use case)

## Decision

We will create a **Python-based orchestrator CLI** that coordinates Ansible, Pulumi, and deploy-rs workflows.

### Architecture

**Single-file script** (initially):
```python
#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "pulumi>=3.0.0",
#   "ansible-runner>=2.0.0",
#   "pulumi-esc-sdk>=0.10.0",
# ]
# ///

# Orchestrator implementation
```

**Location**: `orchestrator/orchestrator.py`

**Execution via uv**:
- Inline dependencies using PEP 723 script metadata
- No separate virtual environment needed
- Dependencies downloaded/cached by `uv`
- Can add shebang for direct execution

### Key Capabilities

**1. ESC Configuration Retrieval**:
```python
from pulumi_esc_sdk import EscClient

client = EscClient()
config = client.open_environment("racknarok", "proxmox")
```

**2. Dynamic Ansible Inventory Generation**:
```python
def generate_ansible_inventory(esc_config):
    """Generate Ansible inventory from ESC config."""
    return {
        "all": {
            "hosts": {
                node["name"]: {
                    "ansible_host": node["hostname"],
                    "vrack_interface": node["vrack_interface"],
                    # ... more vars from ESC
                }
                for node in esc_config["nodes"]
            }
        }
    }
```

**3. Ansible Role Execution**:
```python
import ansible_runner

result = ansible_runner.run(
    private_data_dir='.',
    role='proxmox-bootstrap',
    inventory=inventory,
    ssh_key=ssh_key_path
)
```

**4. Pulumi Automation API**:
```python
import pulumi.automation as auto

stack = auto.select_stack(
    stack_name="proxmox",
    work_dir="pulumi/proxmox"
)
result = stack.up()
```

**5. SSH Key Management**:
```python
import subprocess

# Add SSH key from ESC to ssh-agent
subprocess.run([
    "ssh-add", "-t", "3600", "-",
], input=ssh_key_from_esc, text=True)
```

**6. deploy-rs Execution**:
```python
import subprocess

subprocess.run([
    "deploy-rs",
    "--targets", ".#tailscale-router",
], check=True)
```

### Command Structure

```bash
# Bootstrap new Proxmox node
orchestrator.py bootstrap <node-name>

# Provision VMs
orchestrator.py provision [--stack proxmox]

# Configure NixOS VMs
orchestrator.py configure-nixos [--target <name>]

# Sync config/secrets to ESC
orchestrator.py sync-config

# Full deployment workflow
orchestrator.py deploy
```

### Wrapper Options

**Option A: Direct execution** (with shebang):
```bash
./orchestrator/orchestrator.py deploy
```

**Option B: Justfile wrapper**:
```justfile
# justfile
deploy:
    uv run orchestrator/orchestrator.py deploy

bootstrap NODE:
    uv run orchestrator/orchestrator.py bootstrap {{NODE}}
```

**Option C: Nix wrapper** (future):
```nix
# Could package as proper Nix app
apps.orchestrator = {
  type = "app";
  program = "${orchestrator}/bin/orchestrator";
};

# Then: nix run .#orchestrator -- deploy
```

## Consequences

### Positive

1. **Unified interface**: Single entry point for all deployment operations
2. **ESC integration**: Native access to configuration via Python SDK
3. **Pulumi Automation API**: Programmatic Pulumi execution (better than CLI)
4. **ansible-runner**: Clean Python API for Ansible (no shell-out)
5. **Credential management**: Secure handling of SSH keys from ESC
6. **Dynamic configuration**: Generate Ansible inventory on-the-fly from ESC
7. **Error handling**: Proper exception handling, clear error messages
8. **Fast iteration**: Single Python file, no build step
9. **uv benefits**: Inline dependencies, no venv management
10. **Extensible**: Easy to add new commands as needs evolve

### Negative

1. **Another component**: Adds custom code to maintain
2. **Python dependency**: Requires Python runtime (mitigated by Nix)
3. **Single file limitation**: Will need refactoring if it grows large
4. **Testing complexity**: Integration testing requires real infrastructure

### Mitigation

- **Nix devshell**: Pins Python version and uv
- **Keep simple**: Resist urge to over-engineer
- **Refactor when needed**: Can split into package if it grows
- **Document well**: Clear help text, examples, error messages

## Implementation Notes

### Project Structure

```
orchestrator/
├── orchestrator.py          # Main script (single file initially)
└── README.md               # Usage documentation
```

**If it grows**:
```
orchestrator/
├── orchestrator/
│   ├── __init__.py
│   ├── cli.py              # Command parsing
│   ├── ansible.py          # Ansible integration
│   ├── pulumi.py           # Pulumi Automation API
│   └── esc.py              # ESC client wrapper
├── pyproject.toml          # Proper package if needed
└── README.md
```

### Example Implementation

```python
#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "pulumi>=3.113.0",
#   "ansible-runner>=2.4.0",
#   "pulumi-esc-sdk>=0.10.0",
#   "typer>=0.12.0",
# ]
# ///

import typer
from pulumi_esc_sdk import EscClient
import ansible_runner
import pulumi.automation as auto

app = typer.Typer()

@app.command()
def bootstrap(node: str):
    """Bootstrap a new Proxmox node."""
    # Pull config from ESC
    esc = EscClient()
    config = esc.open_environment("racknarok", "proxmox")

    # Generate inventory
    inventory = generate_inventory(config, node)

    # Get SSH key
    ssh_key = config["ssh"]["private_key"]

    # Run bootstrap role
    result = ansible_runner.run(
        role='proxmox-bootstrap',
        inventory=inventory,
        ssh_key=ssh_key
    )

    if result.rc != 0:
        raise typer.Exit(code=1)

@app.command()
def provision():
    """Provision VMs via Pulumi."""
    stack = auto.select_stack(
        stack_name="proxmox",
        work_dir="pulumi/proxmox"
    )

    result = stack.up(on_output=print)
    print(f"Provisioned: {result.summary.resource_changes}")

if __name__ == "__main__":
    app()
```

### Helper Script Integration

**Justfile for convenience**:
```justfile
# Bootstrap new node
bootstrap NODE:
    ./orchestrator/orchestrator.py bootstrap {{NODE}}

# Full deployment
deploy:
    ./orchestrator/orchestrator.py deploy

# Quick provision
provision:
    ./orchestrator/orchestrator.py provision
```

### Error Handling

```python
class OrchestratorError(Exception):
    """Base exception for orchestrator errors."""
    pass

class ESCConfigError(OrchestratorError):
    """Failed to retrieve config from ESC."""
    pass

class AnsibleExecutionError(OrchestratorError):
    """Ansible role execution failed."""
    pass

# Usage
try:
    config = esc_client.open_environment("racknarok", "proxmox")
except Exception as e:
    raise ESCConfigError(f"Failed to get config: {e}")
```

## Tool Versioning

**Via Nix devshell**:
```nix
# flake.nix
packages = with pkgs; [
  python312      # Pin Python version
  uv             # uv for script execution
  # ... other tools
];
```

**Via uv script metadata**:
```python
# /// script
# dependencies = [
#   "pulumi>=3.113.0,<4.0.0",  # Pin major version
#   "ansible-runner>=2.4.0",
# ]
# ///
```

## Future Considerations

### If complexity grows

- **Refactor to package**: Convert to proper Python package with `pyproject.toml`
- **Add tests**: Unit tests for config parsing, integration tests with mocks
- **CLI framework**: Already using Typer, could add more features
- **Logging**: Structured logging instead of print statements
- **Progress bars**: Rich library for better UX

### Advanced features

- **Parallel execution**: Run multiple Pulumi projects concurrently
- **Dry-run mode**: Preview changes without execution
- **State inspection**: Query current infrastructure state
- **Rollback**: Automatic rollback on failure

### Alternatives if Python becomes limiting

- **Go**: If performance becomes critical (unlikely)
- **Pulumi Deployments**: If Pulumi Cloud Deployments becomes viable

## References

- [Pulumi Automation API](https://www.pulumi.com/docs/using-pulumi/automation-api/)
- [ansible-runner](https://ansible-runner.readthedocs.io/)
- [Pulumi ESC SDK](https://github.com/pulumi/esc-sdk)
- [uv](https://github.com/astral-sh/uv)
- [PEP 723 - Inline Script Metadata](https://peps.python.org/pep-0723/)

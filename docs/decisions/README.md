# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records for Project Racknarok. ADRs document significant architectural decisions, including context, alternatives considered, and consequences.

## Format

Each ADR follows this structure:
- **Status**: Accepted, Proposed, Deprecated, or Superseded
- **Context**: Background and problem being solved
- **Decision**: What was decided and why
- **Consequences**: Positive and negative outcomes
- **Alternatives Considered**: Other options evaluated

## Index

### Configuration and Secrets Management

- [ADR 001: SOPS + ESC for Secrets Management](./001-sops-esc-secrets-management.md)
  - **Status**: Accepted
  - **Summary**: Use SOPS with age encryption for secrets at rest in Git, and Pulumi ESC for runtime distribution
  - **Key Decision**: Git as single source of truth (encrypted), ESC as delivery mechanism

- [ADR 005: Configuration Organization Strategy](./005-config-organization-strategy.md)
  - **Status**: Accepted
  - **Summary**: Service-based directory structure with parallel config/ and secrets/ organization
  - **Key Decision**: Organize by service (proxmox, talos, services/*), map to ESC via esc-mapping.yaml

### Infrastructure Management

- [ADR 002: Ansible for Proxmox Administration](./002-ansible-for-proxmox-admin.md)
  - **Status**: Accepted
  - **Summary**: Use Ansible for Proxmox host configuration where Pulumi provider is insufficient
  - **Key Decision**: Ansible for storage, networking, bootstrapping; Pulumi for VM provisioning

- [ADR 003: Python Orchestrator for Deployment Workflows](./003-python-orchestrator.md)
  - **Status**: Accepted
  - **Summary**: Python CLI to coordinate Ansible, Pulumi, and deploy-rs workflows
  - **Key Decision**: Single-file Python script using uv, integrates with ESC SDK and Pulumi Automation API

### Development Environment

- [ADR 004: Nix Devshell for Tool Versioning](./004-nix-devshell-for-tooling.md)
  - **Status**: Accepted
  - **Summary**: Use Nix flakes to provide reproducible development environment with pinned tools
  - **Key Decision**: Nix devshell for Ansible, Pulumi, SOPS, Python, etc.; direnv for auto-activation

## Reading Order

For new contributors, suggested reading order:

1. **ADR 004** (Nix Devshell) - How to set up development environment
2. **ADR 005** (Config Organization) - How configuration is structured
3. **ADR 001** (SOPS + ESC) - How secrets are managed
4. **ADR 002** (Ansible) - How Proxmox is configured
5. **ADR 003** (Orchestrator) - How everything ties together

## Creating New ADRs

When making significant architectural decisions:

1. Copy an existing ADR as template
2. Number sequentially (006, 007, etc.)
3. Use descriptive filename: `NNN-short-description.md`
4. Include all standard sections
5. Update this README index
6. Reference from relevant architecture docs

## Status Lifecycle

- **Proposed**: Under discussion, not yet implemented
- **Accepted**: Decision made and implemented
- **Deprecated**: No longer recommended, but still in use
- **Superseded**: Replaced by another ADR (link to replacement)

## References

- [Architecture Documentation](../architecture/)
- [ADR Process (Michael Nygard)](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)

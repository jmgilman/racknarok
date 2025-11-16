# 10. Quality Requirements

## Overview

Quality requirements for Project Racknarok are calibrated for a **learning lab**, not production. The emphasis is on educational value, architectural realism, and security-conscious design while accepting compromises on availability, performance, and operational maturity.

## Primary Quality Attributes

### Learnability (Highest Priority)

**Goal**: Maximize hands-on learning opportunities

**Criteria**:
- Technologies are interesting and modern (even if more complex)
- Each layer of the stack is observable and debuggable
- Failures provide learning opportunities (not disasters)
- Architecture mimics real-world patterns worth understanding

**Acceptable Trade-offs**:
- Higher operational complexity is fine
- Slower time-to-productivity acceptable
- More moving parts = more to learn

### Security (High Priority)

**Goal**: Build security-conscious habits and patterns

**Criteria**:
- All control planes are private (Tailscale-only access)
- No admin interfaces exposed to public internet
- Secrets managed via Vault (not in Git)
- mTLS between services (via Istio Ambient)
- Least-privilege access patterns

**Acceptable Trade-offs**:
- May not have SOC2/compliance-grade security
- Learning environment assumes trusted operators
- Some "defense in depth" layers may be skipped initially

### Architectural Realism (Medium Priority)

**Goal**: Reflect real-world enterprise Kubernetes patterns

**Criteria**:
- Separate management and production clusters
- GitOps-driven deployment workflows
- Infrastructure-as-code discipline
- Proper networking segmentation (private control plane, public apps)
- Observability and debugging capabilities

**Acceptable Trade-offs**:
- Single-server "HA" isn't truly highly available
- Cost prevents full geographic redundancy
- May use simpler implementations initially (e.g., single-replica Vault)

### Maintainability (Medium Priority)

**Goal**: Keep the lab operational without excessive toil

**Criteria**:
- Configuration is documented and version-controlled
- Infrastructure changes are reproducible via code
- Architecture decisions are captured in writing
- System state is recoverable from Git + backups

**Acceptable Trade-offs**:
- Automation may lag behind manual operations initially
- Some operational shortcuts acceptable for learning
- Documentation evolves as implementation progresses

## Secondary Quality Attributes

### Availability (Low Priority)

**Goal**: Lab should stay running, but downtime is acceptable

**Criteria**:
- Uptime isn't critical (this isn't production)
- Single-server setup means no true HA initially
- Acceptable to take systems offline for experiments

**Acceptable Trade-offs**:
- No SLA requirements
- Maintenance windows can be whenever convenient
- Rebuilding from scratch is a valid recovery strategy

### Performance (Low Priority)

**Goal**: Adequate for learning and demos, not optimized

**Criteria**:
- Workloads should run without constant resource starvation
- Network performance adequate for multi-tier apps
- Storage performance acceptable for stateful workloads

**Acceptable Trade-offs**:
- Virtualization overhead is fine
- Not optimized for high-throughput workloads
- Resource over-subscription acceptable
- Slower than cloud-hosted equivalents is fine

### Cost Efficiency (Medium Priority)

**Goal**: Constrain spending while maintaining learning value

**Criteria**:
- Start with single server, expand only if expensed
- Avoid unnecessary managed services with ongoing costs
- Use self-hosted alternatives where practical (Vault vs cloud KMS)

**Acceptable Trade-offs**:
- May choose expensive but interesting technologies
- Bare metal is cost-effective at scale but has upfront costs
- Learning value justifies some inefficiency

## Quality Scenarios

### Scenario 1: Operator Access
**Context**: Need to access Kubernetes API from laptop
**Requirement**: Must work only when connected to Tailscale
**Priority**: Critical (security requirement)

### Scenario 2: Application Deployment
**Context**: Deploy new app via GitOps
**Requirement**: Changes to Git repo should automatically deploy to cluster within 5 minutes
**Priority**: High (workflow validation)

### Scenario 3: Storage Failure
**Context**: A Longhorn replica becomes unavailable
**Requirement**: Data should remain accessible (if multiple replicas exist)
**Priority**: Medium (degrades to low until multi-server)

### Scenario 4: Certificate Renewal
**Context**: Let's Encrypt certificate expires
**Requirement**: cert-manager should automatically renew via DNS-01
**Priority**: Medium (manual renewal is acceptable fallback)

### Scenario 5: Learning New Technology
**Context**: Want to add Kyverno for policy enforcement
**Requirement**: Should be able to add via Argo CD without breaking existing workloads
**Priority**: High (validates modular architecture)

## Evolution of Quality Requirements

### Current State (Single Server)
- **Security**: ✅ Fully enforced (Tailscale-only access)
- **Learnability**: ✅ Primary focus
- **Availability**: ⚠️ Single point of failure accepted
- **Performance**: ⚠️ Resource-constrained but adequate
- **Maintainability**: 🔄 Building automation incrementally

### Future State (Multi-Server)
- **Availability**: ⬆️ Increase priority, achieve true HA
- **Performance**: ⬆️ Improve with distributed resources
- **Learnability**: ➡️ Remains primary focus
- **Security**: ➡️ Maintain standards, add advanced patterns
- **Maintainability**: ⬆️ Automation becomes more critical

## Anti-Requirements

What we explicitly do NOT care about for this project:

- ❌ **Production SLAs**: Downtime for learning is fine
- ❌ **Enterprise compliance**: No HIPAA, PCI-DSS, SOC2 requirements
- ❌ **Multi-tenancy**: Single operator, no tenant isolation needed
- ❌ **Global distribution**: Single datacenter is sufficient
- ❌ **Backwards compatibility**: Breaking changes acceptable
- ❌ **Support contracts**: No vendor support needed
- ❌ **Disaster recovery**: Rebuild from Git is acceptable

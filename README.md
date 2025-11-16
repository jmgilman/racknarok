# Project Racknarok

## What is this?

This is a learning experiment in building production-class Kubernetes infrastructure on bare metal servers. Not because it's practical or cost-effective, but because it's interesting and educational.

The goal isn't to run production workloads. It's to understand how everything works when you can't hide behind cloud provider abstractions.

## Why bare metal?

Cloud providers are amazing. They've abstracted away decades of operational complexity, letting teams focus on building products instead of managing infrastructure. That abstraction is valuable.

But abstraction comes at a cost: you don't learn what's underneath. You don't understand the decisions that were made for you, or what trade-offs exist in the layer you can't see.

Running Kubernetes on bare metal means:
- Configuring your own networking (no VPC wizard)
- Managing your own storage (no EBS)
- Setting up your own load balancers (no ALB/NLB)
- Understanding the full stack from BIOS to pod

It's harder. It's also where the learning happens.

## Why these technologies?

The technology choices in this project favor **interesting over boring** and **learning over operational simplicity**:

- **Talos Linux** instead of Ubuntu: Immutable, API-managed, forces you to think differently
- **Cilium** instead of simpler CNIs: eBPF is the future, might as well learn it now
- **Istio Ambient** instead of traditional service mesh: New architecture, new mental models
- **Pulumi** instead of Terraform: Type safety, better abstractions, modern tooling
- **NixOS** for utility VMs: Declarative, reproducible, conceptually elegant

Are these choices "necessary"? No. Are they production-proven at scale? Some are, some aren't. But they're all worth understanding.

## The philosophy

### This is a playground

Production systems optimize for reliability, supportability, and known-good patterns. This project optimizes for learning and experimentation.

That means:
- Trying technologies before they're "battle-tested"
- Accepting complexity in exchange for deeper understanding
- Rebuilding things that break instead of avoiding failure
- Documenting the journey, not just the destination

### Everything as code (where practical)

Clickops is easy. Clickops is also ephemeral, unrepeatable, and teaches bad habits.

This project treats infrastructure as code not because it's required, but because it forces discipline. If you can't codify it, you don't understand it well enough yet.

Exceptions exist (one-off operations, initial exploration), but they're acknowledged as technical debt.

### Security-conscious by default

Even in a learning environment, security matters. Not because this runs sensitive workloads, but because security-first design is a habit worth building.

All control planes are private. Admin access requires VPN. Secrets are managed, not committed to Git. These constraints make the project more interesting, not less.

### Architecturally realistic

The multi-cluster topology (management cluster orchestrating workload clusters) mirrors real enterprise patterns. The separation of concerns between Pulumi (infrastructure), NixOS (VM config), and Argo CD (Kubernetes workloads) reflects real operational boundaries.

Cost and scale limitations mean this can't replicate a full production environment, but the **patterns** are real. The **architecture** is sound. The **decisions** are defensible.

## What this isn't

This is explicitly **not**:
- A production system (no SLAs, no on-call, no disaster recovery)
- A cost-optimized solution (interesting beats cheap)
- A reference implementation for enterprises (too many single-server compromises)
- A tutorial (documentation evolves with understanding, not ahead of it)

## Who is this for?

Honestly? Me.

This is a personal learning project. The documentation exists so I don't forget why I made certain decisions. The architecture is sound because I want to build good habits. The code is clean because I might reference it later.

If you've stumbled across this repository and find it useful, great. If the approach resonates with you, even better. But it's not built for an audience - it's built for understanding.

## The path forward

This project started with one server and will grow as budget allows. The architecture is designed to scale from single-server constraints to multi-node HA, but that evolution is organic, not planned.

Technologies will be added when they're interesting to learn. Features will be built when they teach something new. Documentation will capture decisions as they're made, not prescriptively.

There's no timeline, no roadmap, no definition of "done". Just a bare metal server, a pile of interesting technologies, and a desire to understand how it all fits together.

---

For technical details, see the [architecture documentation](./architecture/).

For specific implementation questions, check the code or the ADRs.

For the philosophy? You just read it.

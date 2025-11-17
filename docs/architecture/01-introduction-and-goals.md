# 1. Introduction and Goals

## What is Project Racknarok?

Project Racknarok is a bare-metal Kubernetes lab built on OVH dedicated servers. It's a learning environment designed to explore modern cloud-native technologies in a realistic multi-cluster setup without the constraints and abstractions of managed cloud services.

## Learning Objectives

The primary goal is hands-on experience with:

- **Proxmox VE**: Bare-metal virtualization and VM lifecycle management
- **Talos Linux**: Immutable, API-managed Kubernetes OS
- **Cilium**: eBPF-based CNI with advanced networking capabilities
- **Istio Ambient**: Sidecar-less service mesh architecture
- **Longhorn**: Distributed block storage for Kubernetes
- **Crossplane**: Infrastructure-as-Code using Kubernetes CRDs
- **Argo CD**: GitOps continuous delivery
- **Multi-cluster patterns**: Management cluster orchestrating workload clusters

## Secondary Goals

- Experiment with **security-first design**: All control planes private by default
- Practice **infrastructure-as-code** discipline (avoid clickops)
- Understand **bare-metal networking** (vRack, load balancers, routing)
- Build a **realistic topology** (management vs prod clusters) despite cost constraints
- Create a **reference architecture** for future bare-metal deployments

## Non-Goals

- **Not production-ready**: This is explicitly a learning lab
- **Not cost-optimized**: Choices favor learning over efficiency
- **Not highly available** (initially): Starting with single server, HA comes later
- **Not exhaustively documented**: Documentation grows with the implementation

## Success Criteria

Success means:
- Successfully running multi-cluster Kubernetes on bare-metal
- Understanding each technology layer deeply through hands-on operation
- Maintaining an architecturally sound design despite compromises
- Documenting learnings and decisions for future reference
- Having fun experimenting without production pressure

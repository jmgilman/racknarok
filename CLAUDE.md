# Project Racknarok

This repository contains the IaC code for an experiment I am running to run Kubernetes on bare metal OVH servers.
The exact state of the repository will be in flux.

IMPORTANT: Please read the `README.md` at the root of the repository and review all documents in `docs/` to get full context on what this project is about and how it's designed.
This is a non-negotiable step and must be completed before performing any work on the project.

## Everything as Code

Please note that _all_ operations should prefer to go through some form of code or configuration.
We should avoid clickops or manual operations unless it's completely impractical (i.e. would require an extensive amount of operation to get/set a single value).

## Playground

It's important to note that this whole project is essentially a giant "playground."
While we are attempting to mimic "real" production setups, we are _not_ bound by production rules.
As you work in the project, be mindful of the spirit of the project and avoid being over-bearing with enforcing production standards.
In many cases we will be necessarily limited to using "hacks" to resolve issues.

## Researching

When working in this project, please prefer looking up the latest documentation rather than assuming your knowledge is correct.
This is especially true for tools whose configuration changes quite frequently over time.
You may use web searching, the `context7` MCP tool, or the `exa` MCP tool to assist in this endeavor.


## Using the SSH MCP tool

You can execute commands directly on the server using the SSH MCP tool.
Each server is held under its own MCP tool.
For example, the `rk1` Proxmox node is accessed using the `ssh-rk1` MCP tool.
You will be executing commands over SSH using the `root` account.
You should feel free to use this to get information as needed from the server.
You should not make changes to the server unless I request it _or_ you ask permission first.

## Usig the Pulumi MCP

You will have access to an MCP tool called `pulumi`.
This tool has been preauthenticated to the Pulumi Cloud account managing these projects.
You should use this tool to:

- Get specific details about a stack
- Search and view details about created resources
- Lookup exact configuration details for a provider using the registry tools
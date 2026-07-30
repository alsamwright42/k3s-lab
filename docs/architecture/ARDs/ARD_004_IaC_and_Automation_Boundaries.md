# ARD 004: Infrastructure as Code (IaC) Boundaries and Terraform Adoption

## Context
As the cluster architecture expands to integrate external cloud dependencies—specifically Microsoft Entra ID (App Registrations, Service Principals) and Azure Key Vault—we must provision these resources without resorting to manual "ClickOps" in the Azure Portal. While our internal Kubernetes cluster state is designed to be managed via GitOps (Argo CD), Argo CD is not designed to provision or manage external cloud infrastructure.

## Decision
We will adopt **Terraform** as the standard IaC tool for provisioning all external cloud dependencies. To prevent automation tool collision and configuration drift, we are establishing strict "Separation of Concerns" boundaries across our stack:

1. **Bash (Bare Metal Layer):** Scripts in `scripts/` are strictly responsible for the physical Dell OptiPlex hardware, local Debian OS bindings, and bootstrapping the K3s daemons.
2. **Argo CD (Cluster Layer):** Declarative YAML in `manifests/` is strictly responsible for all internal Kubernetes workloads, routing, and configurations.
3. **Terraform (Cloud Layer):** Declarative HCL in `infrastructure/terraform/` is strictly responsible for external Azure resources (e.g., Entra ID, Azure Key Vault, RBAC role assignments).

## Consequences & Next Steps
* **Enterprise Alignment:** All infrastructure, both local and cloud-based, is now declaratively version-controlled in the repository.
* **Tooling Overhead:** Introduces Terraform to the local workstation toolchain and requires managing a local `terraform.tfstate` file for the homelab.
* **Action Item:** The `04_Architecture_Strategy.md` and `05_Repository_Structure.md` documents must be updated to reflect these boundaries and the new directory structure.

```markdown
# 05 Repository Structure

This document outlines the declarative GitOps repository structure for the `k3s-lab` bare-metal cluster.

## Directory Tree
    
```text
k3s-lab/
├── apps/
├── core/
│   └── k3s-config/
├── docs/
|   └── architecture/
│       └── ards/
|   └── build/
├── infrastructure/
|   ├── nodes/
│   └── terraform/
├── inventory/
├── manifests/
│   ├── apps/
│   └── base/
└── scripts/
|   ├── azure/
|   ├── bare-metal/
│   └── workstation/
```

## Directory Purposes

* **`apps/`**: Reserved for source code or configurations for custom applications. 
* **`core/k3s-config/`**: Baseline K3s system configurations and systemd service files.
* **`docs/`**: reference documentation. This folder is synced to google drive on git commit as live sources for Gemini NotebookLM
  * **`docs/architecture/`**: Architecture Reference Documents (ARDs), deployment logs, and topology documentation (e.g., `01_Hardware_and_Network_Topology.md`, `02_Cluster_Deployment_Log.md`).
    * **`docs/architecture/ards`*: Architecture Reference Documents recording why architectural decisions were made.
  * **`docs/build/`**: Documentation regarding the building of the IAC configuration
* **`infrastructure/`**: Infrastructure as Code definitions.
  * **`infrastructure/nodes/`** : Node-specific configurations, including K3s server/agent configs that define taints and labels for `KC01` and `KC02`.
  *   **infrastructure/terraform/** : Declarative Terraform code for provisioning external cloud dependencies (e.g., Azure Key Vault, Entra ID Service Principals).
* **`inventory/`**: Host mappings and IP inventory (e.g., `hosts.ini`).
* **`manifests/`**: Declarative Kubernetes YAML manifests. **Must use dedicated subfolders per application/workload in the apps and base subfolders** (e.g., `manifests/apps/vaultwarden/`). Flat-filing is prohibited.
  * **`manifests/base/`**: Core deployments like `cert-manager` and test workloads.
  * **`manifests/apps/`**: User workloads. 
* **`scripts/`**: Automation and bootstrapping scripts. Scripts must be idempotent. All scripts must be in subfolders.
  * **`scripts/azure`** Imperative bash scripts for Azure tasks that cannot be handled by Terraform (e.g `sync-azure-secrets.sh`)
  * **`scripts/bare-metal`** Scripts strictly responsible for the physical Dell hardware, OS-level configuration, and local systemd services (e.g., `bootstrap.sh`, `provision-node.sh`).
  * **`scripts/workstation`** Scripts for preparing the management hardware with the required toolchain. In the current scenario this is Ubuntu WSL on a Dell Windows laptop. (e.g. `setup-workstation.sh`).

```

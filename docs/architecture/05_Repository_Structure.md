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
├── infrastructure/
├── inventory/
├── manifests/
│   ├── apps/
│   └── base/
└── scripts/
```

## Directory Purposes

* **`apps/`**: Reserved for source code or configurations for custom applications. 
* **`core/k3s-config/`**: Baseline K3s system configurations and systemd service files.
* **`docs/`**: Architecture Reference Documents (ARDs), deployment logs, and topology documentation (e.g., `01_Hardware_and_Network_Topology.md`, `02_Cluster_Deployment_Log.md`).
* **`infrastructure/`**: Node-specific configurations, including K3s server/agent configs that define taints and labels for `KC01` and `KC02`.
* **`inventory/`**: Host mappings and IP inventory (e.g., `hosts.ini`).
* **`manifests/`**: Declarative Kubernetes YAML manifests. **Must use dedicated subfolders per application/workload in the apps and base subfolders** (e.g., `manifests/apps/vaultwarden/`). Flat-filing is prohibited.
  * **`manifests/base/`**: Core deployments like `cert-manager` and test workloads.
  * **`manifests/apps/`**: User workloads. 
* **`scripts/`**: Automation and bootstrapping scripts for provisioning nodes and clusters (e.g., `bootstrap.sh`, `provision-node.sh`).
```

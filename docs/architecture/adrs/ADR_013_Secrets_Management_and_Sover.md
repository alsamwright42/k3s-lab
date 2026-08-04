# ADR 013: Secrets Management and Sovereignty Boundaries

## Status
Active

## Context
In our cloud-native enterprise-aligned homelab (K3s cluster running on bare-metal `kc01` and `kc02`), we must manage secrets of various scopes. Storing unencrypted credentials in Git is a critical security vulnerability, and base64-encoded Kubernetes Secret manifests offer no native encryption at rest inside `etcd`. 

Furthermore, we must navigate a fundamental tension between two security principles:
1. **The Principle of Least Privilege (Machine-to-Machine Integration):** Automations should only have access to precisely mapped, scoped API keys and token paths.
2. **Break-Glass Sovereignty (Disaster Recovery):** If the K3s control plane or networking fails entirely, the administrator must retain instant, offline, decrypted access to the "Edge" configurations (router settings, Proxmox hypervisor root logins, bare-metal hardware access) required to repair the hardware. 

To solve both constraints, we must establish a clear boundary between **Machine Secrets** and **Human Secrets**.

## Decision
We will establish a strict architectural boundary dividing secrets management into two distinct control planes:

### 1. Machine Secrets (System-to-System Integration)
All secrets used exclusively by running containers, applications, and operators to integrate with other services (e.g., deSEC DNS validation tokens, database connection strings, API integration keys) will be centrally managed in **Azure Key Vault (AKV)**.
* **Synchronization:** We will use the **External Secrets Operator (ESO)** running in-cluster. ESO will authenticate to Azure via an Entra ID Service Principal or Workload Identity, poll Azure Key Vault, and dynamically create native, ephemeral Kubernetes Secrets in cluster memory.
* **Operational Boundary:** These credentials will remain uncommitted to Git. Developers will only commit non-sensitive Metadata manifests (`ExternalSecret`) referencing the cloud vault paths. No human administrator should ever need to copy-paste or manually type these passwords.

### 2. Human Secrets (Operational Edge & Password Manager Layer)
All secrets that must be manually read, shared, or typed by a human (e.g., router credentials, Proxmox host root passwords, developer database admin credentials, standard user logins) will live in **Vaultwarden**.
* **Self-Hosted Passbolt Parity:** Vaultwarden serves as our local, lightweight, self-hosted equivalent to Passbolt, utilizing Bitwarden's secure organizations and collections to partition shared credentials safely.
* **Break-Glass Automation:** To satisfy the disaster recovery requirement, a pinned nightly CronJob will automate a local, encrypted export of the Vaultwarden vault directly to the host storage of node `kc02` at `/mnt/backups/vaultwarden/offline-vault.json` using the password-encrypted JSON format. 
* **Sovereignty Boundary:** If the cluster dies, the administrator can decrypt this JSON file directly on a local workstation using **KeePassXC**, gaining access to the Edge routing and virtualization passwords needed to restore the bare-metal servers.

## Consequences & Next Steps

* **Zero Secret Leakage:** Committing raw secrets to the Git repository is permanently eliminated.
* **Separation of Planes:** The application compute plane no longer houses the keys to its own hypervisor hosts, dramatically reducing the blast radius of a workload-level container compromise.
* **Disaster Recovery Resilience:** We achieve 100% offline survivability for human operations, while maintaining clean, GitOps-ready configuration boundaries for automated deployments.
* **Action Items:**
  * Implement namespace-scoped `SecretStore` configurations to restrict which namespaces can call specific Azure Key Vault paths.
  * Ensure that the backup script on `kc02` remains functional and is regularly monitored for successful execution.

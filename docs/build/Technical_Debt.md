# Technical Debt & Future Refactoring

## 1. Configuration Management / Ansible Adoption
* **Current State:** OS-level dependencies (e.g., `curl`, `apt-transport-https`, Docker Engine) are hardcoded directly inside the imperative `scripts/bare-metal/provision-node.sh` script.
* **Target State:** Decouple data from logic. Transition from hardcoded bash scripts to a manifest-driven approach (like a `dependencies.txt` file), or fully adopt **Ansible** for declarative, idempotent OS-level configuration management.

## 2. Revisit Portainer Deployment Architecture
* **Current State:** Portainer is currently deployed via Helm on `kc01` in `deploy_core.sh`. This does both the helm repo update and the helm install. Once we have arco installed we may want to change this. It may also be preferable to host it on the WSL workstation.
* **Target State:** Refactor the Portainer deployment to align with the final management plane boundaries, ensuring it doesn't consume unnecessary K3s cluster resources if it is better suited for the WSL workstation.

## 3. Automate Standalone Vaultwarden Deployment
* **Current State:** Vaultwarden was successfully migrated to a standalone Docker container on the host OS of `kc02` to satisfy the "Break-Glass Survival" requirement [1, 4]. However, this container was spun up via imperative command-line actions rather than a version-controlled script.
* **Target State:** Draft a `scripts/bare-metal/deploy-vaultwarden.sh` script to formalize the container deployment and automate its KeePass (`.kdbx`) backup CronJob [5] so the entire disaster recovery mechanism is idempotent and tracked in Git.
* **Status:* Completed

## 4. Centralize Global Configuration (Makefile / Inventory Pattern)
* **Current State:** Critical environment values—such as node IP addresses (`192.168.1.50`, `192.168.1.51`), the Keepalived VIP (`192.168.1.53`), and the primary cluster domain (`samjam.dedyn.io`) are hardcoded directly within individual execution scripts.
* **Target State:** Mirror a Makefile or Maven-properties approach by extracting all hardcoded environment variables into a centralized configuration file located in the `inventory/` directory (e.g., a global `.env` or `hosts.ini` file). Refactor all bash scripts to source this single file dynamically, guaranteeing that changing an IP or domain only requires editing a single file. 
* **Status:** Makefile has been created and global configuration file `inventory/global.env` created. Manual deployment is now managed via make (e.g. make deploy-vaultwarden).

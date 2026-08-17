# 🏡 Homelab & Cluster Operations Backlog

This backlog serves as a comprehensive, structured technical task list to bridge our architectural decisions (ADRs) with our execution pipeline [ADR_004, ADR_011]. Since we have formalized our transition from "vibe coding" to structured, branch-led GitOps development on **GitHub**, these items are structured to be directly translated into **Azure Devops Work Items** and tracked on our project board.

Each task contains clear objective statements, implementation notes mapping back to our verified baseline documents, and explicit "Acceptance Criteria" to keep our multi-environment deployment robust, clean, and completely environment-agnostic [ADR_011].

---
## Definition of Done
* **No Configuration Drift:** Desired state configurations are declared as version-controlled code and committed directly to Git, which serves as the single source of truth.
* **Idempotent Pathing:** Manifests use the mandatory subfolder encapsulation pattern (no flat-filing) inside the dedicated apps/base directory structure.
* **Zero committed secrets:** All secret resources must be externalized (using your External Secrets Operator framework) and completely scrubbed from Git history.
* **Green Workstation Audits:** The codebase passes all local static pre-commit linter checks, including shellcheck for bash automation scripts and yamllint for Kubernetes configurations.
* **Automated Validation Passing:** The CI/CD pipelines run and pass successfully.
* **Formal Pull Request Approval:** Code is merged into the default branch only after a peer review or mandatory review approvals.

---

## 🗺️ Backlog Index & Epic Map
1. **Epic: Ephemeral Azure Sandbox & Agnostic Core Deployment** (Active Milestone)
2. **Epic: Developer Experience, Git Hygiene & DevEx Automation**
3. **Epic: Security Hardening & Cluster Governance**
4. **Epic: Observability, Threat Detection & SIEM**
5. **Epic: High Availability & Disaster Recovery**

---

## 🇨🇦 Epic 1: Ephemeral Azure Sandbox & Agnostic Core Deployment (Active Milestone)

### Task 1.1: Agnostic Kustomize Refactoring for Ingress & cert-manager
*   **Jira/GitHub Ref:** `#1`
*   **Issue Type:** `Feature (Infra)`
*   **Target Branch:** `feat/azure-sandbox`
*   **Description:** Refactor the baseline `manifests/base/cert-manager/` configurations to be environment-agnostic. Remove hardcoded domains (e.g. `samjam.dedyn.io`) and substitute them dynamically at deploy-time using Kustomize replacements.
*   **Implementation Details:**
    *   Utilize the Kustomize `replacements` field in `manifests/base/cert-manager/kustomization.yaml`.
    *   Configure it to dynamically extract the `DOMAIN` key from the `homelab-globals` ConfigMap deployed during cluster bootstrapping and inject it into the `Certificate` and `ClusterIssuer` specs.
*   **Acceptance Criteria:**
    *   Running `kustomize build manifests/base/cert-manager/` does not throw syntax or schema errors.
    *   Compiling with `PROFILE=local` generates manifests with `samjam.dedyn.io`.
    *   Compiling with `PROFILE=azure` generates manifests with `sandbox.samjam.dedyn.io`.

### Task 1.2: Standalone Azure Key Vault Isolation & Terraform Provisioning
*   **Jira/GitHub Ref:** `#2`
*   **Issue Type:** `Feature (Infra)`
*   **Target Branch:** `feat/azure-sandbox`
*   **Description:** Provision an isolated, ephemeral Azure Key Vault in Canada Central to host sandbox cluster secrets without polluting the on-premise production secrets.
*   **Implementation Details:**
    *   Deploy `azure-sandbox-security.tf` and `azure-sandbox-outputs.tf` using the active `azure` profile variables [azure-sandbox-outputs.tf, azure-sandbox-security.tf].
    *   Create a dedicated App Registration/Service Principal (`k3s-lab-test-eso-app`) mapped strictly to the Sandbox Key Vault (`k3s-lab-test-kv-sandbox`).
    *   Configure strict RBAC role assignments: grant `Key Vault Secrets User` only to the sandbox Service Principal on the sandbox vault to ensure absolute logical boundaries.
*   **Acceptance Criteria:**
    *   `terraform apply` successfully provisions the Key Vault and Service Principal in the `k3s-lab-test-rg` group without modifying production resource trees [azure-test-vms.tf].
    *   Sandbox Service Principal credentials can successfully authenticate and read a test secret in the sandbox vault, but are completely blocked from reading the production keyvault.

### Task 1.3: External DNS Integration for Sandbox Domain
*   **Jira/GitHub Ref:** `#3`
*   **Issue Type:** `Feature (Infra)`
*   **Target Branch:** `feat/azure-sandbox`
*   **Description:** Deploy and configure `external-dns` to monitor Kubernetes Ingress resources in the sandbox cluster and automatically publish DNS A-records to our deSEC sandbox zone in real-time.
*   **Implementation Details:**
    *   Use the community external-dns deSEC provider (`external-dns-desec-provider`).
    *   Configure the deployment using Kustomize under `manifests/base/external-dns/` 
    *   Inject the deSEC API token from our sandbox vault via the External Secrets Operator.
*   **Acceptance Criteria:**
    *   Creating a new test Ingress in the sandbox default namespace automatically updates deSEC DNS records [ADR_007].
    *   Resolving the dynamic subdomain locally and externally routes correctly over the internet to our Canada Central VM Traefik IP [ADR_007].

---

## ⚓ Epic 2: Developer Experience, Git Hygiene & DevEx Automation

### Task 2.1: pre-commit Git Hook Integration
*   **Jira/GitHub Ref:** `#4`
*   **Issue Type:** `Chore (DevEx)`
*   **Target Branch:** `feat/azure-sandbox`
*   **Description:** Enforce strict cross-platform code styling, line-ending hygiene, and syntax validation locally on workstation machines prior to code commits to eliminate the CRLF line-ending trap [ADR_011].
*   **Implementation Details:**
    *   Create a `.pre-commit-config.yaml` file in the repository root [ADR_011].
    *   Add native Git filters to automatically normalize line endings from CRLF to LF on check-in using `.gitattributes`.
    *   Integrate `shellcheck` for static analysis of bash scripts inside `scripts/` and `yamllint` for Kubernetes manifests in `manifests/`.
*   **Acceptance Criteria:**
    *   Running `pre-commit run --all-files` successfully cleans up any lingering carriage returns (`\r`).
    *   Invalid shell script structures or improperly formatted YAML blocks block commits until resolved.

### Task 2.2: Local CLI Helper (`cb`) for Conventional Branching
*   **Jira/GitHub Ref:** `#5`
*   **Issue Type:** `Chore (DevEx)`
*   **Target Branch:** `main`
*   **Description:** Eliminate the requirement to context-switch to a web browser to format Git branch names. Create a terminal helper function that automates branch generation using the **Conventional Branch Specification (1.1.0)**.
*   **Implementation Details:**
    *   Draft a bash shell utility named `cb()` and add it to our workstation shell profile (`~/.bashrc` / `~/.zshrc`).
    *   The utility must take `<type>`, `<ticket>`, and `<description>` as positional parameters, convert characters to lowercase, replace spaces with hyphens, and execute `git checkout -b`.
*   **Acceptance Criteria:**
    *   Running `cb feat SYSOP-42 "add sandbox vault"` locally translates seamlessly to:
        `git checkout -b feat/SYSOP-42-add-sandbox-vault`.

### Task 2.3: Commit Message Git Hook for Ticket Enforcement
*   **Jira/GitHub Ref:** `#6`
*   **Issue Type:** `Chore (DevEx)`
*   **Target Branch:** `main`
*   **Description:** Enforce strict link-traceability between Git commit history and our issue tracker. Create a local `commit-msg` hook that prevents developers from executing generic, unscoped, or untracked commits.
*   **Implementation Details:**
    *   Draft a `.git/hooks/commit-msg` script inside the repository template.
    *   Enforce a regex pattern requiring commits to start with a valid issue pattern (e.g., `#<issue-number>: <type>(<scope>): <message>`).
*   **Acceptance Criteria:**
    *   Trying to commit with `git commit -m "fixed trailing spaces"` is automatically blocked with a detailed format failure error message.
    *   Committing with `git commit -m "#12: feat(infra): add pre-commit-hooks"` passes validation cleanly.

---

## 🛡️ Epic 3: Security Hardening & Cluster Governance

### Task 3.1: Administrative sudoers Lockdown
*   **Jira/GitHub Ref:** `#7`
*   **Issue Type:** `Feature (Security)`
*   **Target Branch:** `main`
*   **Description:** Transition away from wild NOPASSWD access for our administrative `sysop` account to align with production least-privilege standards.
*   **Implementation Details:**
    *   Configure `/etc/sudoers.d/sysop` on `kc01` and `kc02` nodes.
    *   Restrict passwordless escalation strictly to critical binaries required by our automated orchestration engine (e.g. `systemctl restart k3s`, `/usr/local/bin/apply-k3s-node-config.sh`).
*   **Acceptance Criteria:**
    *   Running `sudo systemctl restart k3s` executes seamlessly without a password prompt.
    *   Running general administrative actions (e.g. `sudo cat /etc/shadow` or spawning a root shell via `sudo -i`) demands password verification.

### Task 3.2: Kyverno Policy Enforcement for Cluster Governance
*   **Jira/GitHub Ref:** `#8`
*   **Issue Type:** `Feature (Security)`
*   **Target Branch:** `main`
*   **Description:** Implement local automated policy enforcement matching Azure Policy capabilities. Protect the cluster from running raw, insecure, or over-privileged pods.
*   **Implementation Details:**
    *   Deploy **Kyverno** inside the cluster using its official Helm chart managed by Argo CD [ADR_002].
    *   Define baseline cluster policies to block containers with known vulnerabilities or insecure contexts (e.g., restricting host namespaces, blocking root privileges, enforcing read-only root filesystems on solver pods).
*   **Acceptance Criteria:**
    *   Insecure pod manifests (e.g. those requesting root context or mounting direct host filesystems outside system paths) are rejected natively by the admission controller.

### Task 3.3: Decouple Dependencies via Ansible Transition
*   **Jira/GitHub Ref:** `#9`
*   **Issue Type:** `Refactor (Technical Debt)`
*   **Target Branch:** `main`
*   **Description:** Eliminate the procedural technical debt in `scripts/bare-metal/provision-node.sh`. Transition all OS-level dependency installations and configuration setups (apt keys, Docker engine, sysctl flags) into declarative Ansible playbooks.
*   **Implementation Details:**
    *   Define dependencies declaratively in a unified Ansible playbook structure inside `infrastructure/ansible/`.
    *   Reference node configurations dynamically from `inventory/hosts.ini`.
*   **Acceptance Criteria:**
    *   Local scripts no longer install packages or configure system files directly.
    *   Provisioning a clean, headless Debian machine is fully completed by executing a single `ansible-playbook` command.

---

## 📊 Epic 4: Observability, Threat Detection & SIEM

### Task 4.1: Deploy Prometheus-Operator & Grafana
*   **Jira/GitHub Ref:** `#10`
*   **Issue Type:** `Feature (Observability)`
*   **Target Branch:** `main`
*   **Description:** Deploy our telemetry foundation to monitor cluster hardware, daemon processes, and container resource consumption.
*   **Implementation Details:**
    *   Deploy `kube-prometheus-stack` via Argo CD.
    *   Include matching tolerations and node selectors so the control plane monitoring utilities schedule correctly on `kc01` while keeping heavy analytics tools on the worker node.
*   **Acceptance Criteria:**
    *   The Prometheus API is scraping metric endpoints natively across both nodes.
    *   Grafana dashboards are live, accessible via our secure Traefik routing, and plotting active cluster statistics.

### Task 4.2: Grafana Loki and Promtail Log Aggregation
*   **Jira/GitHub Ref:** `#11`
*   **Issue Type:** `Feature (Observability)`
*   **Target Branch:** `main`
*   **Description:** Collect, aggregate, and visualize node-level system logs (such as `/var/log/auth.log`) and Kubernetes container stdout logs in a centralized dashboard.
*   **Implementation Details:**
    *   Deploy **Loki** as the backend datastore and **Promtail** as the node agent.
    *   Configure Promtail to parse host-level security logs to track administrative escalations.
*   **Acceptance Criteria:**
    *   Running `sudo` on any cluster node generates an event that is instantly searchable inside the Grafana Explore panel.

### Task 4.3: eBPF-Based Runtime Threat Detection via Falco
*   **Jira/GitHub Ref:** `#12`
*   **Issue Type:** `Feature (Security)`
*   **Target Branch:** `main`
*   **Description:** Deploy kernel-level runtime monitoring to detect system abnormalities, unexpected binary executions, and direct configuration edits.
*   **Implementation Details:**
    *   Deploy **Falco** with the native eBPF driver onto our headless Debian nodes.
    *   Write rules to flag unexpected shell access inside container environments or modifications to key system files.
*   **Acceptance Criteria:**
    *   Opening an interactive terminal inside any running pod fires a real-time warning alert routed directly to our aggregation panel.

---

## 💾 Epic 5: High Availability & Disaster Recovery

### Task 5.1: Implement Velero S3-Compatible Backup Pipeline
*   **Jira/GitHub Ref:** `#13`
*   **Issue Type:** `Feature (DR)`
*   **Target Branch:** `main`
*   **Description:** Secure the cluster's recovery boundaries. Implement automated nightly snapshots of our declarative cluster state, namespace manifests, and persistent volumes to an offsite location [2, 411].
*   **Implementation Details:**
    *   Install **Velero** inside the cluster using Helm [411].
    *   Configure the backup target to write to an offsite S3-compatible bucket (e.g. Cloudflare R2 or a local secure MinIO node) [411].
*   **Acceptance Criteria:**
    *   Velero successfully schedules and uploads nightly snapshots.
    *   Executing a simulated namespace wipe can be fully recovered with a single `velero restore` command.

### Task 5.2: Idempotent Standalone Vaultwarden & Pi-hole Deploy Script
*   **Jira/GitHub Ref:** `#14`
*   **Issue Type:** `Refactor (Technical Debt)`
*   **Target Branch:** `main`
*   **Description:** Automate the bootstrapping of our standalone management containers to enforce true disaster recovery reproducibility [674].
*   **Implementation Details:**
    *   Write a robust, version-controlled `scripts/bare-metal/deploy-vaultwarden.sh` script [674].
    *   Enforce absolute volume bindings, local environment scoping, and bootstrap the associated encrypted `.kdbx` KeePass cron backup job dynamically [20, 674].
*   **Acceptance Criteria:**
    *   Running `make deploy-vaultwarden` on a fresh node completely configures Docker Engine, launches the vault, secures volume structures, and binds the backup loop automatically without manual steps [674, 675].

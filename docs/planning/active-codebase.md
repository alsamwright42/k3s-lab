# 📂 Active Codebase State

Last compiled: 2026-08-13T17:14:10Z

This file provides high-density context of tracked configurations for AI alignment.

---

## 🛠️ Core Automation Files

---

### 📄 File: Makefile
```text
# Homelab Cluster Operations Makefile
# Fulfills Technical Debt #4: Centralize Global Configuration

# =============================================================================
# ⚙️ CONFIGURATION & EXTENSIONS
# =============================================================================

# Define universal binary requirements. Individual repositories can append 
# their own specific tools (e.g., REQUIRED_TOOLS += terraform or REQUIRED_TOOLS += mvnw).
REQUIRED_TOOLS ?= shellcheck git 

REQUIRED_TOOLS += terraform kubectl kustomize envsubst ssh

PROFILE ?= local		## [Optional] Target environment profile. Maps to any 'inventory/<name>.env' file. Default: local
FORCE ?= false			## [Optional] Bypass safety checks and run-once safety locks. Choices: [true, false]. Default: false
CI ?= false 			## [Optional] CI/CD Mode. Bypasses local file-sourcing. Choices: [true, false]. Default: false
USE_PROFILES ?= true	## [Optional] Enable environment variable profile loading. Choices: [true, false]. Default: false

# =============================================================================
# 🧼 WHITESPACE SANITIZER (Sanitizes trailing spaces from comments in advance)
# =============================================================================
# We use eager evaluation (:=) to strip trailing whitespace immediately on startup
PROFILE      := $(strip $(PROFILE))
FORCE        := $(strip $(FORCE))
CI           := $(strip $(CI))
USE_PROFILES := $(strip $(USE_PROFILES))

ENV_FILE := inventory/$(PROFILE).env

# Define the temporary build artifact
CLEAN_ENV := /tmp/clean.env

# =============================================================================
# 🔐 ENVIRONMENT LOADER
# =============================================================================
ifeq ($(CI),true)
  # 🟢 CI/CD Mode: Bypass local file-sourcing entirely.
  $(info === CI/CD Mode: Inheriting environment variables from runner ===)
else ifeq ($(USE_PROFILES),true)
  # 💻 Profile Loading Enabled: Verify file existence before running sanitizer
  ifeq ($(wildcard $(ENV_FILE)),)
    $(warning ⚠️  WARNING: Profile configuration file not found at '$(ENV_FILE)'!)
    $(warning    -> To fix this, create the file or copy from a template.)
  else ifeq ($(wildcard ./scripts/workstation/sanitize-env.sh),)
    # 🟡 Sandbox/Missing Script Mode: Fallback gracefully
    $(info === Sandbox Mode: Profile file found, but sanitize-env.sh is missing. Skipping load ===)
  else
    # 💻 Local Workstation Mode: Clean, include, and export the selected profile file.
    $(info === Local Workstation Mode: Sanitizing and loading $(ENV_FILE) ===)
    $(info $(shell ./scripts/workstation/sanitize-env.sh $(ENV_FILE) $(CLEAN_ENV)))
    -include $(CLEAN_ENV)
    export
  endif
endif

# Sentinel file indicating onboarding compliance
SETUP_SENTINEL := .setup_done

.DEFAULT_GOAL := help

# Centralized staging files in a secure, unprivileged directory
STAGE := /tmp/kustomize-argocd.yaml
STAGE_CORE := /tmp/kustomize-argocd-core.yaml
DAY0_LOCK := /etc/rancher/k3s/.day0_lock

.PHONY: setup setup-githooks check-workstation-tools guard-setup test help \
        day0-bare-metal platform-core gitops-apps \
        check-day0-lock write-day0-lock \ 
		provision-nodes deploy-ha-dns sync-azure-secrets apply-globals \
        kustomize-argocd bootstrap-argocd \
		deploy-portainer deploy-vaultwarden deploy-vw-backup \
		bundle

help: ## Display this help message with target descriptions
	@echo "=========================================================================="
	@echo " Homelab Cluster Operations Toolchain"
	@echo "=========================================================================="
	@echo "Usage: make <target> [VARIABLE=value] [PROFILE=]"
	@echo ""
	@echo "Variables:"
	@grep -h -E '^[a-zA-Z0-9_-]+ \?=.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = " \\?=.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Targets:"
	@grep -h -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ==============================================================================
# 🛠️ WORKSPACE ONBOARDING TARGETS
# ==============================================================================

setup: check-workstation-tools setup-githooks ## Bootstrap local WSL workspace and prepare development plane
	@touch $(SETUP_SENTINEL)
	@echo "=========================================================================="
	@echo "🎉 SUCCESS: Workspace is configured!"
	@echo "=========================================================================="

setup-githooks: ## Activate local Git hooks and map core.hooksPath
	@echo "⚓ Activating local workstation Git hooks..."
	@chmod +x githooks/pre-commit githooks/commit-msg 2>/dev/null || true
	@chmod +x githooks/pre-commit.d/* githooks/commit-msg.d/* 2>/dev/null || true
	@chmod +x scripts/workstation/*.sh 2>/dev/null || true
	@git config core.hooksPath githooks
	@echo "✅ Git hooks successfully mapped to 'githooks/' and marked executable!"

check-workstation-tools: ## Validate if required binaries are present on disk without hard fail
	@echo "🔎 Auditing workstation binary toolchain..."
	@failed=0; \
	for tool in $(REQUIRED_TOOLS); do \
		if command -v $$tool > /dev/null 2>&1; then \
			echo "✅ $$tool is present."; \
		else \
			echo "⚠️  WARNING: '$$tool' is missing on this workstation. Some targets may fail."; \			
		fi; \
	done

# Quietly guard critical targets. Supports FORCE=true to allow pipeline/CI bypasses.
# This must be the first dependency in any target chain that requires a fully initialized workstation.
guard-setup:
ifeq ($(FORCE),true)
	@echo "⚠️ FORCE=true specified. Bypassing workspace setup validation checks!"
else ifeq ($(CI),true)
	@echo "🟢 CI/CD environment detected. Bypassing workstation setup check."
else ifeq ($(wildcard $(SETUP_SENTINEL)),)
	@echo "=========================================================================="
	@echo "🛑 REJECTED: Your workspace has not been initialized yet!"
	@echo "👉 To unblock this target and configure your workstation linter gates,"
	@echo "   you must run the onboarding target first:"
	@echo "   "
	@echo "   make setup"
	@echo "=========================================================================="
	@exit 1
endif

# ==============================================================================
# 🚀 MACRO ENTRY POINTS (The platform lifecycle)
# ==============================================================================

# DAY 0: Bare Metal & Host OS Layer (Locked to run-once; override with FORCE=true)
day0-bare-metal: guard-setup check-day0-lock provision-nodes deploy-ha-dns write-day0-lock ## [Day 0] Provision bare-metal nodes and deploy HA DNS (Keepalived + Pi-hole)
	@echo "✅ [Day 0 Complete] Physical hosts provisioned and routing is stable."

# DAY 1: Platform Core & Control Plane (Gated by TDD Workstation Unit Tests)
platform-core: test sync-azure-secrets apply-globals bootstrap-argocd ## [Day 1] Bootstrap platform core(Secrets, Globals, Argo CD GitOps Controller)
	@echo "🚀 [Platform Core Complete] Secrets injected, global environments active, and GitOps controller live."

# DAY 2: GitOps Applications (Delegates all standard deployments to Argo CD)
gitops-apps: bootstrap-argocd ## [Day 2] Delegate all application deployments to Argo CDGitOps controller
	@echo "=== Day 2: Declarative GitOps Sync ==="
	@echo "Platform control handed off to Argo CD."
	@echo "To apply app updates (Vaultwarden, backup CronJobs, etc.), simply commit changes to Git."
	@echo "Argo CD will automatically heal drift and reconcile state in the cluster."

# ==============================================================================
# 🔒 DAY 0 PROTECTION CONTROLS (Run-Once Safety Guards)
# ==============================================================================

check-day0: ## Verify if the Day 0 bare-metal layer is already provisioned
ifeq ($(FORCE),true)
	@echo "⚠️ FORCE=true specified. Bypassing Day 0 run-once safety guards!"
else
	@echo "🔍 Checking if Day 0 bare-metal layer is already provisioned..."
	@if ssh -n -q -o BatchMode=yes $(CONTROL_PLANE_IP) "[ -f $(DAY0_LOCK) ]"; then \
		echo "❌ ERROR: Day 0 bare-metal setup has already been run on this cluster."; \
		echo "   To prevent accidental host network flushes or K3s control-plane corruption,"; \
		echo "   this target is locked."; \
		echo ""; \
		echo "   To override this lock and force execution, append FORCE=true:"; \
		echo "   make day0-bare-metal FORCE=true"; \
		echo ""; \
		exit 1; \
	fi
	@echo "✅ No prior Day 0 lock detected. Proceeding..."
endif

write-day0-lock:
	@echo "🔒 Writing Day 0 run-once lock to control plane node..." ## Write the Day 0 lock file to the control plane node
	@ssh -n -q -o BatchMode=yes $(CONTROL_PLANE_IP) "sudo mkdir -p /etc/rancher/k3s && sudo touch $(DAY0_LOCK)"

# ==============================================================================
# ⚙️ DETAILED OPERATIONAL TARGETS
# ==============================================================================

test: guard-setup ## Run the complete workstation test suite
	@echo "=== Running Workstation Test Suite ==="
	python3 -m unittest discover -v -s tests -p "test_*.py"
	@echo "✅ All unit tests passed successfully!"

kustomize-argocd: guard-setup ## Compile Kustomize AST and substitute environment variables
	@echo "=== Compiling and Verifying ArgoCD Kustomize build ==="
	kubectl kustomize manifests/base/argocd/ | envsubst > $(STAGE)
	@echo "✅ Kustomize validation succeeded! Rendered manifest cached at $(STAGE)"

bootstrap-argocd: kustomize-argocd ## Deploy Argo CD controller in two-phase sync pass
	@echo "=== Deploying Argo CD (GitOps Controller) ==="
	@echo "=== Phase 1: Filtering & Deploying Argo CD Base (No Custom Kinds) ==="
	# Uses standard library Python to split and filter out custom kinds (Application, AppProject)
	@./scripts/workstation/filter_manifest.py $(STAGE) $(STAGE_CORE)
	kubectl apply --server-side --force-conflicts -f $(STAGE_CORE)

	@echo "=== Waiting for Custom Resource Definitions to stabilize ==="
	# We block here until the API server officially establishes the Argo CD custom schemas.
	kubectl wait --for=condition=Established crd/applications.argoproj.io crd/appprojects.argoproj.io crd/applicationsets.argoproj.io --timeout=60s
	
	@echo "=== Phase 2: Applying Custom Resources ==="
	# Re-applies the complete manifest including the now-valid custom resources
	kubectl apply --server-side --force-conflicts -f $(STAGE)
	@rm -f $(STAGE_CORE)
	@echo "🚀 Argo CD successfully bootstrapped!" 

provision-nodes: guard-setup ## Bootstrap K3s server and agent nodes over SSH
	@echo "=== Bootstrapping K3s Nodes ==="
	./scripts/bare-metal/bootstrap.sh

deploy-ha-dns: guard-setup ## Deploy Keepalived and Pi-hole for high-availability DNS routing
	@echo "=== Deploying High-Availability DNS ==="
	./scripts/bare-metal/deploy-ha-dns.sh

deploy-vaultwarden: guard-setup ## Deploy standalone Vaultwarden Docker container
	@echo "=== Deploying Standalone Vaultwarden ==="
	./scripts/bare-metal/deploy-vaultwarden.sh

sync-azure-secrets: guard-setup ## Sync Azure Key Vault credentials to K3s cluster
	@echo "=== Syncing Azure Key Vault Credentials to K3s ==="
	./scripts/azure/sync-azure-secrets.sh

apply-globals: guard-setup ## Inject homelab global environment ConfigMaps
	@echo "=== Injecting global configuration from environment variables ==="
	envsubst < manifests/base/globals/homelab-globals.yaml | kubectl apply -f -

deploy-vw-backup: guard-setup ## Deploy standalone Vaultwarden backup CronJob manifest
	@echo "=== Deploying Vaultwarden Backup CronJob ==="
	envsubst '$$INGRESS_IP $$DOMAIN $$VW_URL' < manifests/apps/vaultwarden/vaultwarden-backup-cronjob.yaml | kubectl apply -f -

bundle: guard-setup ## Bundle the active codebase into a single markdown for AI agent consumption
	@echo "=== Bundling codebase into a single markdown file ==="
	./scripts/workstation/bundle-codebase.sh
	
```

---

## 🐚 Active Shell Scripts

---

### 📄 File: scripts/azure/sync-azure-secrets.sh
```bash
#!/usr/bin/env bash
set -euo pipefail

# Anchor paths to the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Define clean absolute paths for Terraform and manifest directories
TF_DIR="${REPO_ROOT}/infrastructure/terraform"
MANIFEST_DIR="${REPO_ROOT}/manifests/base/external-secrets"

echo "=== Syncing Azure Key Vault Credentials to K3s ==="

# Extract all dynamic values from Terraform state
echo "Extracting data from Terraform..."
CLIENT_ID=$(terraform -chdir="${TF_DIR}" output -raw client_id)
CLIENT_SECRET=$(terraform -chdir="${TF_DIR}" output -raw client_secret)
TENANT_ID=$(terraform -chdir="${TF_DIR}" output -raw tenant_id)
export TENANT_ID

# Inject into K3s idempotently (creates or updates the secret)
echo "Injecting credentials into the external-secrets namespace..."
kubectl create secret generic azure-kv-credentials \
    -n external-secrets \
    --from-literal=ClientID="${CLIENT_ID}" \
    --from-literal=ClientSecret="${CLIENT_SECRET}" \
    --dry-run=client -o yaml | kubectl apply -f -

# 2. Render and Apply the ClusterSecretStore Template
echo "Applying ClusterSecretStore using Terraform outputs..."
envsubst < "${MANIFEST_DIR}/cluster-secret-store.yaml" | kubectl apply -f -

echo "Success! External Secrets Operator is fully wired to Azure."
```

---

### 📄 File: scripts/bare-metal/apply-k3s-node-config.sh
```bash
#!/usr/bin/env bash
set -euo pipefail

ROLE="${1:-worker}"
TEMP_CONFIG="/tmp/config.yaml"
DEST_CONFIG="/etc/rancher/k3s/config.yaml"

if [ ! -f "$TEMP_CONFIG" ]; then
    echo "Error: $TEMP_CONFIG not found." >&2
    exit 1
fi

mv "$TEMP_CONFIG" "$DEST_CONFIG"
chmod 664 "$DEST_CONFIG"

if [ "$ROLE" = "control-plane" ]; then
    echo "Restarting K3s control plane..."
    # Detached asynchronously to prevent SSH session hangs
    systemctl restart k3s </dev/null >/dev/null 2>&1 &
else
    echo "Restarting K3s worker agent..."
    # Detached asynchronously to prevent SSH session hangs
    systemctl restart k3s-agent </dev/null >/dev/null 2>&1 &
fi```

---

### 📄 File: scripts/bare-metal/bootstrap.sh
```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Generic smart polling function
# Usage: wait_for_condition <retries> <wait_interval_seconds> <"Status Message"> <command...>
wait_for_condition() {
    local retries=$1
    local wait_time=$2
    local message=$3
    shift 3 # Remove the first 3 arguments so only the command remains in "$@"
    local cmd=("$@")

    echo "Waiting: ${message}..."
    for ((i=1; i<=retries; i++)); do
        # Execute the command silently
        if "${cmd[@]}" >/dev/null 2>&1; then
            echo "  -> Success!"
            return 0
        fi
        echo "  -> Not ready yet. Retrying in ${wait_time}s... ($i/$retries)"
        sleep "$wait_time"
    done

    # If the loop finishes without success, throw an error and halt the script
    echo "Error: Timed out waiting for ${message} after $((retries * wait_time)) seconds." >&2
    exit 1
}

echo "=== Validating and Parsing Node Inventory ==="
declare -a CLUSTER_NODES

# Validate and Register Control Plane
if [ -z "${CONTROL_PLANE_NODE:-}" ]; then
    echo "FAILED: CONTROL_PLANE_NODE is missing from the provided environment!"
    exit 1
fi

declare -A WORKER_NODES

# Validate and Parse Worker Nodes
for record in $WORKER_NODES_CONFIG; do
    IFS=':' read -r node ip <<< "$record"
    
    # FAIL EARLY: Check if the string was malformed (missing node or IP)
    if [ -z "${node:-}" ] || [ -z "${ip:-}" ]; then
        echo "FAILED: Malformed worker record '$record'. Expected format 'hostname:IP'."
        exit 1
    fi
    
    # Register the worker and dynamically build its config file name
    WORKER_NODES["$node"]="$ip"
done

# Create cluster node list
CLUSTER_NODES=("CONTROL_PLANE_NODE" "${!WORKER_NODES[@]}")

echo "=== K3s Lab Connectivity Check ==="
# Check Control Plane
echo -n "Testing SSH connection to ${CONTROL_PLANE_NODE}... "
if ssh -n -q -o BatchMode=yes -o ConnectTimeout=5 "${CONTROL_PLANE_NODE}" exit; then 
    echo "Control plane connectivity verified."
else
    echo "FAILED: Cannot reach control plane node."
    exit 1
fi


for node in "${CLUSTER_NODES[@]}"; do
    echo -n "Testing SSH connection to ${node}... "
    if ssh -n -q -o BatchMode=yes -o ConnectTimeout=5 "${node}" exit; then
        echo "OK"
    else
        echo "FAILED"
        exit 1
    fi
done

echo ""
echo "=== Provisioning Remote Host Environments ==="
for node in "${CLUSTER_NODES[@]}"; do
    echo "--> Provisioning ${node}..."
    scp -o BatchMode=yes "${SCRIPT_DIR}/provision-node.sh" "${node}:/tmp/provision-node.sh"
    scp -o BatchMode=yes "${SCRIPT_DIR}/apply-k3s-node-config.sh" "${node}:/tmp/apply-k3s-node-config.sh"
    ssh -n -o BatchMode=yes "${node}" "sudo bash /tmp/provision-node.sh"
done

echo ""
echo "=== Deploying Control Plane ($CONTROL_PLANE_NODE) ==="
scp -o BatchMode=yes "${REPO_ROOT}/infrastructure/nodes/control-plane-config.yaml" "${CONTROL_PLANE_NODE}:/tmp/config.yaml"
ssh -n -o BatchMode=yes "${CONTROL_PLANE_NODE}" "sudo /usr/local/bin/apply-k3s-node-config.sh control-plane"

wait_for_condition 12 5 "K3s control plane to be ready" ssh -n -o BatchMode=yes "${CONTROL_PLANE_NODE}" "sudo k3s kubectl get nodes 2>/dev/null | grep -q 'Ready'"

echo "=== Extracting K3s Token ==="
# Fetch the token dynamically and export it to memory for the template renderer
K3S_TOKEN=$(ssh -n -o BatchMode=yes "${CONTROL_PLANE_NODE}" "sudo cat /var/lib/rancher/k3s/server/node-token")
export K3S_TOKEN
echo "Token extracted successfully."

echo ""
echo "=== Deploying Worker Nodes ==="
for node in "${!WORKER_NODES[@]}"; do
    export WORKER_IP="${WORKER_NODES[$node]}"

    echo "--> Rendering template and updating ${node} (worker node)..."
    # Use envsubst to populate the YAML template with our active memory variables
    envsubst < "${REPO_ROOT}/core/k3s-config/worker-config.yaml.template" > "/tmp/${node}-config.yaml"

    scp -o BatchMode=yes "/tmp/${node}-config.yaml" "${node}:/tmp/config.yaml"
    ssh -n -o BatchMode=yes "${node}" "sudo /usr/local/bin/apply-k3s-node-config.sh worker"

done

echo ""
echo "=== Node Bootstrap Complete ==="
echo "Verifying all registered nodes are Ready..."

# Loop through every node in the associative array
for target_node in "${CLUSTER_NODES[@]}"; do
    wait_for_condition 15 4 "Node ${target_node} to report as Ready" \
        ssh -n -o BatchMode=yes kc01 "sudo k3s kubectl get nodes 2>/dev/null | grep -E '^${target_node}\s+.*Ready'"
done

echo ""
echo "Cluster is fully online. Final status and labels:"
ssh -n -o BatchMode=yes kc01 "sudo k3s kubectl get nodes --show-labels"



```

---

### 📄 File: scripts/bare-metal/deploy-core.sh
```bash
#!/usr/bin/env bash
set -euo pipefail

# Set paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "=== Deploying Core Infrastructure Utilities ==="

# 1. Update local Helm repositories
echo "--> Updating Helm repositories..."
helm repo add portainer https://portainer.github.io/k8s/
# (We will add Traefik and Cert-Manager repos here later)
helm repo update >/dev/null

# 2. Deploy Portainer using your version-controlled values
echo "--> Deploying Portainer to KC01..."
helm upgrade --install portainer portainer/portainer \
  --namespace portainer \
  --create-namespace \
  -f "${REPO_ROOT}/manifests/apps/portainer/values.yaml" \
  --wait

echo ""
echo "=== Core Deployment Complete ==="
echo "Portainer is running. Access it at http://192.168.1.50:30777"kube
```

---

### 📄 File: scripts/bare-metal/deploy-ha-dns.sh
```bash
#!/usr/bin/env bash
set -euo pipefail

echo "=== Validating and Parsing HA Node Inventory ==="
declare -A HA_NODES

# Rebuild the associative array from the flat string in the node config environment variable
for record in $HA_NODES_CONFIG; do
    # Extract the three pieces of data separated by colons
    IFS=':' read -r node state priority <<< "$record"
    
    # Fail early if the string is malformed
    if [ -z "${node:-}" ] || [ -z "${state:-}" ] || [ -z "${priority:-}" ]; then
        echo "FAILED: Malformed HA node record '$record'. Expected format 'hostname:STATE:PRIORITY'."
        exit 1
    fi
    
    # Reconstruct the exact format your script originally used
    HA_NODES["$node"]="${state}:${priority}"
done

echo "=== Deploying High-Availability DNS (Keepalived + Pi-hole) ==="

for node in "${!HA_NODES[@]}"; do
    IFS=':' read -r state priority <<< "${HA_NODES[$node]}"
    echo "--> Provisioning ${node} as ${state} (Priority: ${priority})..."

    # 1. Install Keepalived on the host OS
    ssh -q -o BatchMode=yes "${node}" "sudo apt-get update && sudo apt-get install -y keepalived"

    # 2. Configure Keepalived for the Virtual IP (VIP)
    cat <<EOF | ssh -q -o BatchMode=yes "${node}" "sudo tee /etc/keepalived/keepalived.conf > /dev/null"
vrrp_instance VI_CLUSTER_DNS {
    state ${state}
    interface ${INTERFACE}
    virtual_router_id 53
    priority ${priority}
    advert_int 1
    authentication {
        auth_type PASS
        auth_pass k3s_dns_ha
    }
    virtual_ipaddress {
        ${VIP}/24 dev ${INTERFACE}
    }
}
EOF

    # Restart and enable Keepalived
    ssh -q -o BatchMode=yes "${node}" "sudo systemctl restart keepalived && sudo systemctl enable keepalived"

    # 3. Deploy Standalone Pi-hole via Docker
    echo "    Spinning up Pi-hole container..."
    ssh -q -o BatchMode=yes "${node}" "sudo docker rm -f pihole 2>/dev/null || true"
    
    # We publish DNS (53) normally, but map the Web UI to 8053 so it doesn't conflict with Traefik Ingress
    ssh -q -o BatchMode=yes "${node}" "sudo docker run -d \\
        --name pihole \\
        --restart=unless-stopped \\
        -p 53:53/tcp -p 53:53/udp \\
        -p 8053:80/tcp \\
        -e TZ=\"America/Denver\" \\
        -e WEBPASSWORD=\"${PIHOLE_PW}\" \\
        -v /opt/pihole/etc-pihole:/etc/pihole \\
        -v /opt/pihole/etc-dnsmasq.d:/etc/dnsmasq.d \\
        pihole/pihole:latest >/dev/null"

    # 4. Inject Split-Horizon DNS configuration
    echo "    Applying Split-Horizon DNS rewrite for ${DOMAIN} -> ${VIP}..."
    ssh -q -o BatchMode=yes "${node}" "sudo bash -c 'echo \"address=/${DOMAIN}/${VIP}\" > /opt/pihole/etc-dnsmasq.d/99-k3s-cluster.conf'"
    
    # Restart Pi-hole to load the new dnsmasq config
    ssh -q -o BatchMode=yes "${node}" "sudo docker restart pihole >/dev/null"

    echo "--> ${node} deployment successful."
    echo ""
done

echo "=== HA DNS Deployment Complete ==="
echo "Keepalived VIP: ${VIP} is now active."
echo "Pi-hole Web UIs accessible at: http://192.168.1.50:8053 and http://192.168.1.51:8053"
```

---

### 📄 File: scripts/bare-metal/deploy-vaultwarden.sh
```bash
#!/usr/bin/env bash
set -euo pipefail

echo "=== Deploying Standalone Vaultwarden on ${VW_NODE} ==="

# ADR 011 Rule 1: No Error Swallowing (We allow 'true' only to permit first-time clean deployment)
# ADR 011 Rule 4: Headless SSH Safety
echo "--> Cleaning up existing Vaultwarden container..."
ssh -n -o BatchMode=yes -o ConnectTimeout=5 "${VW_NODE}" "sudo docker rm -f vaultwarden || true"

echo "--> Provisioning data directory and launching container..."
ssh -n -o BatchMode=yes -o ConnectTimeout=5 "${VW_NODE}" "sudo mkdir -p ${VW_DATA_DIR} && sudo docker run -d \
  --name vaultwarden \
  --restart=unless-stopped \
  -p ${VW_PORT}:80 \
  -v ${VW_DATA_DIR}:/data \
  vaultwarden/server:latest"

echo "=== Vaultwarden Deployment Complete ==="
echo "Vaultwarden is now natively listening on http://${VW_IP}:${VW_PORT}"
```

---

### 📄 File: scripts/bare-metal/provision-node.sh
```bash
#!/usr/bin/env bash
set -euo pipefail

echo "=== Installing OS Dependencies and Docker Engine ==="
sudo apt-get update
sudo apt-get install -y curl ca-certificates gnupg

# Install Docker Engine if it is not already installed
if ! command -v docker &> /dev/null; then
    echo "--> Docker not found. Installing native Docker Engine..."
    curl -fsSL https://get.docker.com | sudo sh
    sudo systemctl enable docker
    sudo systemctl start docker
else
    echo "--> Docker is already installed."
fi

# Add the sysop user to the docker group so you don't need sudo for docker commands
sudo usermod -aG docker sysop

echo "=== Provisioning Cluster Node OS Security & Helper Scripts ==="

# 1. Create the administrative group & assign user
sudo groupadd -f k3s-admin
sudo usermod -aG k3s-admin sysop

# 2. Grant k3s-admin group ownership over /etc/rancher/k3s/
sudo mkdir -p /etc/rancher/k3s
sudo chown -R root:k3s-admin /etc/rancher/k3s
sudo chmod 775 /etc/rancher/k3s

# 3. Copy the helper script into place from staging
if [ -f /tmp/apply-k3s-node-config.sh ]; then
    sudo cp /tmp/apply-k3s-node-config.sh /usr/local/bin/apply-k3s-node-config.sh
    sudo chmod 755 /usr/local/bin/apply-k3s-node-config.sh
else
    echo "Error: /tmp/apply-k3s-node-config.sh not found." >&2
    exit 1
fi

# 4. Enforce Least-Privilege Sudoers Rule
echo "sysop ALL=(ALL) NOPASSWD: /usr/local/bin/apply-k3s-node-config.sh" | sudo tee /etc/sudoers.d/k3s-admin-safe
sudo chmod 0440 /etc/sudoers.d/k3s-admin-safe

echo "=== Node Provisioning Complete ==="```

---

### 📄 File: scripts/workstation/audit-repo-secrets.sh
```bash
#!/usr/bin/env bash
# scripts/workstation/audit-repo-secrets.sh
# Audits the local repository for potential secret leaks, untracked files, 
# and ensures that gitignore rules are actively protecting sensitive files.
# Aligned with ADR_011 (Automation Standards) and ADR_013 (Secrets Management).

set -euo pipefail

# Force safe environment fallback locales (suppresses locale warnings)
export LANG=C.UTF-8
export LC_ALL=C.UTF-8

# ANSI color codes for terminal logging
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=====================================================================${NC}"
echo -e "${BLUE}🛡️  HOMELAB REPOSITORY SECURITY & SECRETS AUDIT GATE (v3)${NC}"
echo -e "${BLUE}=====================================================================${NC}"

# Check if inside a git repo
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo -e "${RED}❌ ERROR: Not inside a Git repository! Run this script from your repository root.${NC}"
    exit 1
fi

# Directory Anchoring (ADR 011 Rule 5: Script is 2 levels deep inside scripts/workstation/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$REPO_ROOT"

FAILED=0

# Step 1: Active Tracking Audit
echo -e "\n${BLUE}🔎 Step 1: Checking for actively tracked sensitive files...${NC}"
TRACKED_SECRETS=$(git ls-files | grep -E '(\.tfvars$|\.env$|\.tfstate$|id_rsa|id_ed25519|\.pem$|\.key$|vault-keys\.json|\.kdbx$)' || true)

if [ -n "$TRACKED_SECRETS" ]; then
    echo -e "${RED}❌ CRITICAL WARNING: Git is actively tracking sensitive files!${NC}"
    echo -e "${RED}These files are committed or staged and WILL be pushed to your public repository:${NC}"
    while IFS= read -r file; do
        [ -z "$file" ] && continue
        echo -e "  - $file"
    done <<< "$TRACKED_SECRETS"
    echo -e "${YELLOW}👉 To stop tracking these files while keeping them locally, run:${NC}"
    echo -e "   git rm --cached <filename>"
    FAILED=1
else
    echo -e "${GREEN}✅ Clean! No actively tracked sensitive files detected.${NC}"
fi

# Step 2: Gitignore Enforcement Audit
echo -e "\n${BLUE}🔎 Step 2: Verifying .gitignore coverage for sensitive files...${NC}"
EXISTING_SECRETS=$(find . -type f \( -name "*.env" -o -name "*.tfvars" -o -name "*.tfstate" -o -name "vault-keys.json" -o -name "*.kdbx" \) -not -path '*/.*' -not -path '*/node_modules/*' || true)

if [ -n "$EXISTING_SECRETS" ]; then
    UNIGNORED_SECRETS=""
    while IFS= read -r file; do
        [ -z "$file" ] && continue
        if ! git check-ignore -q "$file"; then
            UNIGNORED_SECRETS="${UNIGNORED_SECRETS}\n  - $file"
        fi
    done <<< "$EXISTING_SECRETS"

    if [ -n "$UNIGNORED_SECRETS" ]; then
        echo -e "${RED}❌ WARNING: Found existing secret files NOT covered by .gitignore:${NC}"
        echo -e "$UNIGNORED_SECRETS"
        echo -e "${YELLOW}👉 Add these patterns to your .gitignore immediately!${NC}"
        FAILED=1
    else
        echo -e "${GREEN}✅ Safe! All existing local secret files (.env, .tfvars, .tfstate, .kdbx) are properly ignored.${NC}"
    fi
else
    echo -e "${GREEN}✅ Safe! No local .env, .tfvars, or backup files found in the directory tree.${NC}"
fi

# Step 3: High-Entropy Plaintext Scan
echo -e "\n${BLUE}🔎 Step 3: Scanning files for high-entropy strings and plaintext patterns...${NC}"
PATTERN="(password|token|pat|client_secret|client-secret|clientid|client-id|access_key|access-key|api-token|api_token)[[:space:]]*=[[:space:]]*[\"'][a-zA-Z0-9_-]{8,128}[\"']"

SUSPICIOUS_LINES=$(git grep -E -n -i "$PATTERN" -- '*.tf' '*.sh' '*.yaml' '*.yml' '*.env' '*.json' 2>/dev/null || true)

if [ -n "$SUSPICIOUS_LINES" ]; then
    echo -e "${YELLOW}⚠️  POTENTIAL PLAIN-TEXT SECRET LEAKS DETECTED:${NC}"
    echo -e "${YELLOW}The following tracked lines seem to assign sensitive strings in plain text:${NC}"
    while IFS= read -r line; do
        [ -z "$line" ] && continue
        echo -e "  - $line"
    done <<< "$SUSPICIOUS_LINES"
    echo -e "${YELLOW}👉 Ensure these values are abstracted into variables/Azure Key Vault references!${NC}"
else
    echo -e "${GREEN}✅ Clean! No obvious plain-text password/token assignments found in tracked files.${NC}"
fi

# Step 4: Line Normalization Check
echo -e "\n${BLUE}🔎 Step 4: Running validation checklist...${NC}"
if [ -f ".gitattributes" ]; then
    echo -e "${GREEN}✅ .gitattributes exists (line normalization is active).${NC}"
else
    echo -e "${YELLOW}⚠️  Missing .gitattributes! Highly recommended for cross-platform WSL setups to prevent CRLF errors.${NC}"
fi

if [ "$FAILED" -eq 1 ]; then
    echo -e "\n${RED}🛑 AUDIT FAILED! Please resolve the security gaps above before pushing code to your public repository.${NC}"
    exit 1
else
    echo -e "\n${GREEN}🎉 SUCCESS! Your repository is 100% clean and ready for public push!${NC}"
    exit 0
fi
```

---

### 📄 File: scripts/workstation/audit-shellcheck.sh
```bash
#!/usr/bin/env bash
# scripts/workstation/audit-shellcheck.sh
# Deterministically audits only the staged bytes of shell scripts in the Git index.
# Prevents checking clean unmodified files while catching active staged/unstaged errors on disk.
# Fulfills ADR_011 (Directory Anchoring) and ADR_013 (Secrets Sovereignty).

set -euo pipefail

# ADR 011 Rule 5: Directory Anchoring (Script is 2 levels deep)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Force C.UTF-8 locale fallback to suppress host-side setlocale warnings
export LANG=C.UTF-8
export LC_ALL=C.UTF-8

if ! command -v shellcheck &> /dev/null; then
    echo "⚠️  [ShellCheck Audit] 'shellcheck' is not installed!"
    echo "   To enable syntax checks, run: sudo apt install shellcheck"
    exit 0
fi

echo "🔍 Auditing changed and staged Shell scripts on disk..."

failed=0
# Loop through files with any changes (staged or unstaged) compared to HEAD
while IFS= read -r file; do
    [ -z "$file" ] && continue
    
    # Check if the file physically exists in the working directory
    if [ -f "${REPO_ROOT}/${file}" ]; then
        first_line=$(head -n 1 "${REPO_ROOT}/${file}" || true)
        if [[ "$file" =~ \.sh$ ]] || [[ "$first_line" =~ ^#\!.*sh ]]; then
            echo "   -> Scanning working tree copy of staged file: $file"
            if ! shellcheck "${REPO_ROOT}/${file}"; then
                echo "❌ ShellCheck failed on working version of: $file"
                failed=1
            fi
        fi
    fi
done < <(git -C "$REPO_ROOT" diff --cached --name-only --diff-filter=ACMR 2>/dev/null || true)

if [ "$failed" -ne 0 ]; then
    echo "❌ [Audit Gate] ShellCheck validation failed! Fix warnings before committing."
    exit 1
fi

echo "✅ ShellCheck audit completed successfully!"
exit 0
```

---

### 📄 File: scripts/workstation/bundle-codebase.sh
```bash
#!/usr/bin/env bash
# scripts/workstation/bundle-codebase.sh
# Generates a single high-density markdown snapshot of tracked files
# to auto-sync with your Google Drive / Gemini Notebook pipeline.

set -euo pipefail
shopt -s globstar nullglob

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OUTPUT_FILE="${OUTPUT_FILE:-${REPO_ROOT}/docs/planning/active-codebase.md}"

prepare_output() {
    mkdir -p "$(dirname "$OUTPUT_FILE")"
}

write_header() {
    prepare_output
    printf '# 📂 Active Codebase State\n\n' > "$OUTPUT_FILE"
    printf 'Last compiled: %s\n\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" >> "$OUTPUT_FILE"
    printf 'This file provides high-density context of tracked configurations for AI alignment.\n' >> "$OUTPUT_FILE"
}

section_title() {
    printf '\n---\n\n%s\n' "$1" >> "$OUTPUT_FILE"
}

append_file() {
    local path="$1"
    local lang="$2"

    section_title "### 📄 File: ${path}"
    {
      printf '```%s\n' "$lang" >> "$OUTPUT_FILE"
      cat "$REPO_ROOT/$path" >> "$OUTPUT_FILE"
      printf '```\n'
    }  >> "$OUTPUT_FILE"
}

append_files() {
    local title="$1"
    local lang="$2"
    shift 2

    local files=()
    local path
    for glob in "$@"; do
        for path in "$REPO_ROOT"/$glob; do
            [ -f "$path" ] || continue
            files+=("${path#"$REPO_ROOT"/}")
        done
    done

    local tracked=()
    declare -A seen=()
    for path in "${files[@]}"; do
        [ -n "${seen[$path]:-}" ] && continue
        if git -C "$REPO_ROOT" ls-files --error-unmatch -- "$path" >/dev/null 2>&1; then
            seen[$path]=1
            tracked+=("$path")
        fi
    done

    if [ "${#tracked[@]}" -eq 0 ]; then
        return
    fi

    mapfile -t sorted < <(printf '%s\n' "${tracked[@]}" | sort)
    section_title "$title"
    for path in "${sorted[@]}"; do
        append_file "$path" "$lang"
    done
}

main() {
    write_header

    append_files '## 🛠️ Core Automation Files' 'text' Makefile local-profile.env azure-profile.env
    append_files '## 🐚 Active Shell Scripts' 'bash' 'scripts/**/*.sh' 'scripts/**/*.py'
    append_files '## ☸️ Declarative Kubernetes Manifests' 'yaml' 'manifests/**/*.yaml' 'manifests/**/*.yml' 'manifests/**/*.txt'
    append_files '## ☸️ Declarative Infrastructure Files' 'yaml' 'infrastructure/**/*.yaml' 'infrastructure/**/*.yml' 'infrastructure/**/*.tf'
    append_files '## 📁 Core Configuration Files' 'yaml' 'core/**/*.service' 'core/**/*.yaml' 'core/**/*.yml' 'core/**/*.template'
    append_files '## 📁 Inventory Files' 'yaml' 'inventory/**/*.env' 'inventory/**/*.ini'

    printf '\nCodebase successfully compiled to %s!\n' "$OUTPUT_FILE"
}

main
```

---

### 📄 File: scripts/workstation/filter_manifest.py
```bash
#!/usr/bin/env python3
"""
Utility script to filter out custom resources from a compiled Kustomize stream.
This facilitates safe multi-phase bootstraps without triggering premature custom API validations.
"""
import sys
import os

def filter_manifest(input_path, output_path):
    """
    Filters out Argo CD Custom Resources (Application, AppProject) from a compiled manifest stream.
    Strictly parses top-level 'kind:' fields to prevent block scalar and comment collisions.
    """
    if not os.path.exists(input_path):
        print(f"Error: Input manifest '{input_path}' not found.", file=sys.stderr)
        sys.exit(1)

    with open(input_path, 'r') as f:
        # Split stream natively on standard YAML document boundaries
        documents = f.read().split('---')

    filtered_docs = []
    for doc in documents:
        doc_strip = doc.strip()
        if not doc_strip:
            continue

        # Inspect lines to verify if this block defines a custom workload kind
        lines = doc_strip.split('\n')
        is_custom_workload = False

        for line in lines:
            # Clean carriage returns
            line_clean = line.rstrip('\r')
            
            # Top-level keys must start with 'kind:' at column 0 (no indentation)
            if line_clean.startswith('kind:'):
                # Separate the value and strip away inline comments
                parts = line_clean.split(':', 1)
                kind_value = parts[1].split('#')[0].strip()
                
                # Exact match against targeted custom kinds
                if kind_value in ('Application', 'AppProject'):
                    is_custom_workload = True
                    break
                
        if not is_custom_workload:
            filtered_docs.append(f"---\n{doc_strip}")

    with open(output_path, 'w') as f:
        f.write('\n'.join(filtered_docs) + '\n')

if __name__ == "__main__":
    if len(sys.argv) < 3:
        # Dynamically extracts the active filename (no hardcoded string mismatches!)
        script_name = os.path.basename(sys.argv[0])
        print(f"Usage: {script_name} <input_file> <output_file>", file=sys.stderr)
        sys.exit(1)
    
    filter_manifest(sys.argv[1], sys.argv[2])
```

---

### 📄 File: scripts/workstation/query-gemini-review.py
```bash
#!/usr/bin/env python3
import os
import sys
import json
import argparse
import urllib.request
import urllib.error

def parse_args():
    parser = argparse.ArgumentParser(
        description="Extract Git diff and consult Gemini for secure homelab code review annotations."
    )
    parser.add_argument(
        "--diff-path",
        default=os.environ.get("GEMINI_DIFF_PATH", "pr_changes.diff"),
        help="Path to the input Git diff file (default: 'pr_changes.diff' or GEMINI_DIFF_PATH env var)"
    )
    parser.add_argument(
        "--output-path",
        default=os.environ.get("GEMINI_OUTPUT_PATH", "review_output.json"),
        help="Path to save the generated JSON review findings (default: 'review_output.json' or GEMINI_OUTPUT_PATH env var)"
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("GEMINI_MODEL", "gemini-3.5-flash"),
        help="Gemini model version (default: 'gemini-3.5-flash' or GEMINI_MODEL env var)"
    )
    parser.add_argument(
        "--api-version",
        default=os.environ.get("GEMINI_API_VERSION", "v1beta"),
        help="Gemini api version used in gemini url (default: 'v1beta' or GEMINI_API_VERSION env var)"
    )    
    return parser.parse_args()

def main():
    args = parse_args()
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    diff_path = args.diff_path
    output_path = args.output_path
    api_version = args.api_version
    model = args.model

    # Initialize default empty comments file to ensure downstream steps don't crash
    default_output = {"comments": []}
    try:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    except Exception:
        pass  # If path is flat/current directory, avoid failing

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(default_output, f, indent=2)

    if not os.path.exists(diff_path):
        print(f"⚠️ Warning: Input diff file '{diff_path}' not found. Skipping analysis.", file=sys.stderr)
        return

    with open(diff_path, "r", encoding="utf-8") as f:
        diff_content = f.read().strip()

    if not diff_content:
        print(f"✅ PR Diff '{diff_path}' is empty. No changes to analyze.")
        return
    # Prompt engineered to guide the model to perform a rigid code quality & security review
    prompt = (
        "You are an expert DevOps and Platform Engineer auditing code quality, syntax, "
        "security (credential leaks), and architectural anti-patterns in a Kubernetes homelab. "
        "Analyze the following Git diff of a Pull Request. Focus on:\n"
        "1. POSIX-safe shell scripting (avoiding bash-isms like '&>' in standard /bin/sh recipes).\n"
        "2. Safe environment sourcing and dynamic configurations in Makefiles.\n"
        "3. Terraform module declarations, ensuring required arguments are populated and secrets are sensitive.\n"
        "4. Kubernetes manifest security (avoiding hardcoded secrets or privileged contexts).\n\n"
        "You must return your output strictly in JSON format. Do not wrap your response in markdown code blocks. "
        "The JSON structure must match this exact schema:\n"
        "{\n"
        "  \"comments\": [\n"
        "    { \"file\": \"filename\", \"line\": line_number_integer, \"message\": \"Markdown warning/error string\" }\n"
        "  ]\n"
        "}\n\n"
        "Analyze only the lines showing additions or changes (+ lines) in the diff. "
        "Identify the file path and line number precisely. If no issues are found, return an empty comments list.\n\n"
        f"Here is the diff to analyze:\n\n{diff_content}"
    )

    url = f"https://generativelanguage.googleapis.com/{api_version}/models/{model}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST"
    )

    try:
        print("🚀 Sending diff to Gemini API for secure analysis...")
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode("utf-8"))
        
        # Extract generated text content
        text_response = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
        
        # Parse model's JSON response to validate schema
        ai_reviews = json.loads(text_response)
        
        # Write verified JSON output back to disk
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(ai_reviews, f, indent=2)
        
        print(f"✅ AI Review completed. Issues found: {len(ai_reviews.get('comments', []))}")

    except urllib.error.HTTPError as e:
        print(f"❌ API HTTP Error: {e.code} - {e.read().decode('utf-8')}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error during AI review processing: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

---

### 📄 File: scripts/workstation/sanitize-env.sh
```bash
#!/usr/bin/env bash
# This script sanitizes a .env file by removing comments and trailing whitespace making it compatible with make
set -euo pipefail

INPUT_FILE="${1:-}"
OUTPUT_FILE="${2:-}"


if [ -z "$INPUT_FILE" ] || [ -z "$OUTPUT_FILE" ]; then
    echo "FAILED: Both Input and Output files must be provided."
    exit 1
fi

if [ ! -f "$INPUT_FILE" ]; then
    echo "FAILED: $INPUT_FILE not found."
    exit 1
fi

# ADR 011 Rule 2: Safe File Staging (No sed -i)
# Treat INPUT_FILE as immutable and compile the result directly to OUTPUT_FILE
sed -e 's/[[:space:]]*#.*//' -e 's/[[:space:]]*$//' "$INPUT_FILE" > "$OUTPUT_FILE"
```

---

### 📄 File: scripts/workstation/setup-workstation.sh
```bash
#!/usr/bin/env bash

# 1. Fetch the Kubeconfig from KC01 and point it to the static IP
mkdir -p ~/.kube
ssh -n -o BatchMode=yes kc01 "sudo cat /etc/rancher/k3s/k3s.yaml" | sed "s/127.0.0.1/192.168.1.50/" > ~/.kube/config
chmod 600 ~/.kube/config

# 2. Download and install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
#    Install into system path with execution permissions
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
#    Clean up the downloaded file
rm kubectl

# 3. Install the Helm CLI
curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# 4. Add the jetpack repository to Helm
echo "Adding jetstack Helm repository..."
helm repo add jetstack https://charts.jetstack.io
helm repo update

# 5. Add the External Secrets repository to Helm
echo "Adding External Secrets Helm repository..."
helm repo add external-secrets https://charts.external-secrets.io
helm repo update

# 6. Install the Terraform CLI (Official HashiCorp Repository)
echo "Installing Terraform CLI..."
# Install prerequisite packages
sudo apt-get update && sudo apt-get install -y gnupg software-properties-common curl
# Add the HashiCorp GPG key
wget -O- https://apt.releases.hashicorp.com/gpg | \
  gpg --dearmor | \
  sudo tee /usr/share/keyrings/hashicorp-archive-keyring.gpg > /dev/null
# Add the official HashiCorp Linux repository
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] \
  https://apt.releases.hashicorp.com $(lsb_release -cs) main" | \
  sudo tee /etc/apt/sources.list.d/hashicorp.list
# Install Terraform
sudo apt-get update && sudo apt-get install -y terraform
echo "Terraform installation complete. Version:"
terraform -version

# 7. Install the Azure CLI
echo "Installing Azure CLI..."
# Download the script to a temporary file first
curl -sL https://aka.ms/InstallAzureCLIDeb -o /tmp/install-az.sh
# Execute it
sudo bash /tmp/install-az.sh
# Clean up the temporary file
rm /tmp/install-az.sh

echo "Azure CLI installation complete. Version:"
az version

# 8. Install make
echo "Installing Make..."
sudo apt-get update && sudo apt-get install -y make
echo "Make installation complete. Version:"
make --version
```

---

## ☸️ Declarative Kubernetes Manifests

---

### 📄 File: manifests/apps/portainer/values.yaml
```yaml
# yaml-language-server: $schema=none
# manifests/apps/portainer/values.yaml

# 1. Pin the workload specifically to the infra/control plane node
nodeSelector:
  workload-type: infra

# 2. Tolerate the NoSchedule taint on KC01
tolerations:
  - key: "node-role.kubernetes.io/control-plane"
    operator: "Exists"
    effect: "NoSchedule"

# 3. Disable Portainer's strict TLS so we can manage SSL via Traefik Ingress later
tls:
  force: false
```

---

### 📄 File: manifests/apps/vaultwarden/vaultwarden-backup-credentials-sync.yaml
```yaml
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: vaultwarden-backup-credentials-sync
  namespace: default
spec:
  refreshInterval: "1h"
  secretStoreRef:
    name: azure-backend
    kind: ClusterSecretStore
  target:
    name: vaultwarden-backup-credentials # The secret name the CronJob expects
    creationPolicy: Owner
  data:
  - secretKey: BW_CLIENTID
    remoteRef:
      key: vw-backup-client-id     # The name in Azure Key Vault
  - secretKey: BW_CLIENTSECRET
    remoteRef:
      key: vw-backup-client-secret # The name in Azure Key Vault
  - secretKey: VAULT_PASSWORD
    remoteRef:
      key: vw-backup-svc-password  # The Vaultwarden backup service user password in Azure Key Vault
  - secretKey: KDBX_PASSWORD
    remoteRef:
      key: vw-kdbx-password        # The KeePass archive encryption password in Azure Key Vault
  - secretKey: VW_REMOTE_API_TOKEN
    remoteRef:
      key: vw-backup-remote-api-token     # The remote API token in Azure Key Vault
```

---

### 📄 File: manifests/apps/vaultwarden/vaultwarden-backup-cronjob.yaml
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: vaultwarden-breakglass-backup
  namespace: default
spec:
  schedule: "0 2 * * *" # Runs daily at 2:00 AM server time
  jobTemplate:
    spec:
      template:
        spec:
          nodeSelector:
            workload-type: compute
          hostAliases:
          - ip: "${INGRESS_IP}" 
            hostnames:
            - "vault.${DOMAIN}"
          containers:
          - name: bw-backup-runner
            image: node:20-alpine # Your original, trusted Node.js Alpine image
            command: ["/bin/sh", "-c"]
            args:
              - |
                set -euo pipefail

                # 1. Install the official Bitwarden CLI, KeePassXC, and Rclone
                echo "--> Installing runtime dependencies..."
                apk add --no-cache keepassxc rclone expect jq > /dev/null
                npm install -g @bitwarden/cli > /dev/null

                echo "--> Configuring Vaultwarden API endpoint..."
                bw config server "${VW_URL}"
              
                echo "--> Authenticating via API Key..."
                bw login --apikey > /dev/null
              
                echo "--> Unlocking Vault..."
                export BW_SESSION=$(bw unlock "${BW_PASSWORD}" --raw)

                CLEAN_PATH="${VW_BACKUP_LOCATION#*:}"

                echo "--> Fetching and Exporting Organization Vaults..."
                # The corrected jq syntax that iterates through all organizations
                bw list organizations --session "${BW_SESSION}" | jq -r '.[] | "\(.id)|\(.name)"' | while IFS="|" read -r ORG_ID ORG_NAME; do
                  
                  SAFE_NAME=$(echo "$ORG_NAME" | tr ' ' '_')
                  echo "--> Exporting Organization: $ORG_NAME"
                  
                  bw export --organizationid "$ORG_ID" --output "/backup/org_${SAFE_NAME}.json" --format encrypted_json --password "$KDBX_PASSWORD" --session "${BW_SESSION}"
                  rclone copy "/backup/org_${SAFE_NAME}.json" remote:"${CLEAN_PATH}"
                done

                echo "--> Cleaning up..."
                rm -f /tmp/vault-export.csv
                bw lock
                unset BW_SESSION
                echo "--> Backup sequence complete."
            env:
            - name: BW_CLIENTID
              valueFrom:
                secretKeyRef:
                  name: vaultwarden-backup-credentials # Synchronized from Azure via ESO
                  key: BW_CLIENTID
            - name: BW_CLIENTSECRET
              valueFrom:
                secretKeyRef:
                  name: vaultwarden-backup-credentials
                  key: BW_CLIENTSECRET
            - name: BW_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: vaultwarden-backup-credentials
                  key: VAULT_PASSWORD
            - name: KDBX_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: vaultwarden-backup-credentials
                  key: KDBX_PASSWORD
            
            # --- PULL NON-SECRETS FROM GLOBAL CONFIGMAP ---
            - name: VW_BACKUP_LOCATION
              valueFrom:
                configMapKeyRef:
                  name: homelab-globals
                  key: VW_BACKUP_LOCATION
            - name: VW_URL
              valueFrom:
                configMapKeyRef:
                  name: homelab-globals
                  key: VW_URL

            # Rclone natively reads these environment variables, bypassing the need for a config file
            - name: RCLONE_CONFIG_REMOTE_TOKEN
              valueFrom:
                secretKeyRef:
                  name: vaultwarden-backup-credentials
                  key: VW_REMOTE_API_TOKEN
            - name: RCLONE_CONFIG_REMOTE_TYPE
              valueFrom:
                configMapKeyRef:
                  name: homelab-globals
                  key: VW_BACKUP_REMOTE_TYPE
            
            volumeMounts:
            - name: backup-storage
              mountPath: /backup
          restartPolicy: OnFailure
          volumes:
          - name: backup-storage
            hostPath:
              path: /mnt/backups/vaultwarden
              type: DirectoryOrCreate
```

---

### 📄 File: manifests/apps/vaultwarden/vaultwarden.yaml
```yaml
apiVersion: v1
kind: Service
metadata:
  name: vaultwarden-external
  namespace: default
spec:
  ports:
    - port: 8080
      targetPort: 8080
      protocol: TCP
---
apiVersion: v1
kind: Endpoints
metadata:
  name: vaultwarden-external
  namespace: default
subsets:
  - addresses:
      # The static IP of KC02 where Docker is running
      - ip: 192.168.1.51
    ports:
      - port: 8080
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: vaultwarden-ingress
  namespace: default
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-production
    traefik.ingress.kubernetes.io/router.middlewares: ""
spec:
  tls:
    - hosts:
        - vault.samjam.dedyn.io
      secretName: samjam-dedyn-io-tls
  rules:
    - host: vault.samjam.dedyn.io
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: vaultwarden-external
                port:
                  number: 8080```

---

### 📄 File: manifests/base/argocd/kustomization.yaml
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: argocd

resources:
  - namespace.yaml
  # Declaratively pulls the official v3.4.6 stable release manifest
  - https://raw.githubusercontent.com/argoproj/argo-cd/v3.4.6/manifests/install.yaml
  - ../globals
  - repo-secret.yaml
  - root-application.yaml


patches:
  - path: patches/control-plane-scheduling.yaml
  - path: patches/resource-limits.yaml

# Dynamically routes non-sensitive ConfigMap values into your manifests
replacements:
  - source:
      kind: ConfigMap
      name: homelab-globals
      fieldPath: data.GIT_REPO_URL
    targets:
      - select:
          kind: ExternalSecret
          name: argocd-private-repo-credentials
        fieldPaths:
          - spec.target.template.data.url
      - select:
          kind: Application
          name: root-application
        fieldPaths:
          - spec.source.repoURL
```

---

### 📄 File: manifests/base/argocd/namespace.yaml
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: argocd
```

---

### 📄 File: manifests/base/argocd/patches/control-plane-scheduling.yaml
```yaml
# yaml-language-server: $schema=none
apiVersion: apps/v1
kind: Deployment
metadata:
  name: argocd-server
spec:
  template:
    spec:
      tolerations:
        - key: "node-role.kubernetes.io/control-plane"
          operator: "Exists"
          effect: "NoSchedule"
        - key: "node-role.kubernetes.io/master"
          operator: "Exists"
          effect: "NoSchedule"
      nodeSelector:
        workload-type: "infra"
---
# yaml-language-server: $schema=none
apiVersion: apps/v1
kind: Deployment
metadata:
  name: argocd-repo-server
spec:
  template:
    spec:
      tolerations:
        - key: "node-role.kubernetes.io/control-plane"
          operator: "Exists"
          effect: "NoSchedule"
        - key: "node-role.kubernetes.io/master"
          operator: "Exists"
          effect: "NoSchedule"
      nodeSelector:
        workload-type: "infra"
---
# yaml-language-server: $schema=none
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: argocd-application-controller
spec:
  template:
    spec:
      tolerations:
        - key: "node-role.kubernetes.io/control-plane"
          operator: "Exists"
          effect: "NoSchedule"
        - key: "node-role.kubernetes.io/master"
          operator: "Exists"
          effect: "NoSchedule"
      nodeSelector:
        workload-type: "infra"
```

---

### 📄 File: manifests/base/argocd/patches/resource-limits.yaml
```yaml
# yaml-language-server: $schema=none
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: argocd-application-controller
spec:
  template:
    spec:
      containers:
        - name: argocd-application-controller
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi
---
# yaml-language-server: $schema=none
apiVersion: apps/v1
kind: Deployment
metadata:
  name: argocd-server
spec:
  template:
    spec:
      containers:
        - name: argocd-server
          resources:
            requests:
              cpu: 50m
              memory: 128Mi
            limits:
              cpu: 200m
              memory: 256Mi
```

---

### 📄 File: manifests/base/argocd/repo-secret.yaml
```yaml
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: argocd-private-repo-credentials
  namespace: argocd
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: azure-backend
    kind: ClusterSecretStore
  target:
    name: github-private-repo-ssh
    creationPolicy: Owner
    template:
      metadata:
        labels:
          # This label tells Argo CD to auto-discover this secret as repository credentials
          argocd.argoproj.io/secret-type: repository
      data:
        type: git
        url: "REPO_URL"
        sshPrivateKey: "{{ .ssh_key | toString }}"
  data:
    - secretKey: ssh_key
      remoteRef:
        key: argocd-repo-ssh-key
```

---

### 📄 File: manifests/base/argocd/root-application.yaml
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: root-application
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default
  source:
    repoURL: "REPO_URL"
    targetRevision: HEAD
    path: manifests
  destination:
    server: 'https://kubernetes.default.svc'
    namespace: argocd
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

---

### 📄 File: manifests/base/cert-manager/cert-manager-values.yaml
```yaml
installCRDs: true

nodeSelector:
  workload-type: infra
tolerations:
  - key: "node-role.kubernetes.io/control-plane"
    operator: "Exists"
    effect: "NoSchedule"
  - key: "node-role.kubernetes.io/master"
    operator: "Exists"
    effect: "NoSchedule"

webhook:
  nodeSelector:
    workload-type: infra
  tolerations:
    - key: "node-role.kubernetes.io/control-plane"
      operator: "Exists"
      effect: "NoSchedule"
    - key: "node-role.kubernetes.io/master"
      operator: "Exists"
      effect: "NoSchedule"

cainjector:
  nodeSelector:
    workload-type: infra
  tolerations:
    - key: "node-role.kubernetes.io/control-plane"
      operator: "Exists"
      effect: "NoSchedule"
    - key: "node-role.kubernetes.io/master"
      operator: "Exists"
      effect: "NoSchedule"

startupapicheck:
  nodeSelector:
    workload-type: infra
  tolerations:
    - key: "node-role.kubernetes.io/control-plane"
      operator: "Exists"
      effect: "NoSchedule"
    - key: "node-role.kubernetes.io/master"
      operator: "Exists"
      effect: "NoSchedule"      ```

---

### 📄 File: manifests/base/cert-manager/cluster-issuer.yaml
```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-production
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: alsamwright@gmail.com
    privateKeySecretRef:
      name: letsencrypt-production-account-key
    solvers:
      - dns01:
          webhook:
            groupName: acme.pr0ton11.github.com
            solverName: desec
            config:
              apiKeySecretRef:
                name: desec-token
                key: token```

---

### 📄 File: manifests/base/cert-manager/desec-external-secret.yaml
```yaml
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: desec-api-token
  namespace: cert-manager
spec:
  refreshInterval: "1h"
  secretStoreRef:
    name: azure-backend
    kind: ClusterSecretStore
  target:
    # This must match the exact secret name cert-manager is looking for
    name: desec-token 
    creationPolicy: Owner
  data:
    - secretKey: token # The key inside the Kubernetes secret
      remoteRef:
        key: desec-api-token # The name of the secret in Azure Key Vault```

---

### 📄 File: manifests/base/cert-manager/desec-secret.yaml
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: desec-api-token
  namespace: cert-manager
type: Opaque
stringData:
  token: "${DESEC_API_TOKEN}"
```

---

### 📄 File: manifests/base/cert-manager/desec-webhook-values.yaml
```yaml
certManager:
  namespace: cert-manager
  serviceAccountName: cert-manager

nodeSelector:
  node-role.kubernetes.io/control-plane: "true"
tolerations:
  - key: "node-role.kubernetes.io/control-plane"
    operator: "Exists"
    effect: "NoSchedule"
  - key: "node-role.kubernetes.io/master"
    operator: "Exists"
    effect: "NoSchedule"```

---

### 📄 File: manifests/base/cert-manager/wildcard-cert.yaml
```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: wildcard-samjam-cert
  namespace: default
spec:
  commonName: samjam.dedyn.io
  dnsNames:
    - samjam.dedyn.io
    - "*.samjam.dedyn.io"
  issuerRef:
    name: letsencrypt-production
    kind: ClusterIssuer
  secretName: samjam-dedyn-io-tls```

---

### 📄 File: manifests/base/external-secrets/cluster-secret-store.yaml
```yaml
apiVersion: external-secrets.io/v1
kind: ClusterSecretStore
metadata:
  name: azure-backend
spec:
  provider:
    azurekv:
      authType: ServicePrincipal
      vaultUrl: "${KEY_VAULT_URI}"
      tenantId: "${TENANT_ID}"
      authSecretRef:
        clientId:
          name: azure-kv-credentials
          key: ClientID
          namespace: external-secrets
        clientSecret:
          name: azure-kv-credentials
          key: ClientSecret
          namespace: external-secrets```

---

### 📄 File: manifests/base/external-secrets/desec-token-sync.yaml
```yaml
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: desec-token-sync
  namespace: cert-manager
spec:
  refreshInterval: "1h"
  secretStoreRef:
    name: azure-backend 
    kind: ClusterSecretStore
  target:
    name: desec-token # The exact secret name the ClusterIssuer already expects
    creationPolicy: Owner
  data:
  - secretKey: desec-token # The exact data key the deSEC webhook requires
    remoteRef:
      key: desec-api-token # The name of the secret inside your Azure Key Vault
```

---

### 📄 File: manifests/base/external-secrets/test-desec-sync.yaml
```yaml
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: desec-token-sync
  namespace: cert-manager
spec:
  refreshInterval: "1h"
  secretStoreRef:
    name: azure-backend # Matches the name from <kubectl get clustersecretstore output>
    kind: ClusterSecretStore
  target:
    name: desec-api-token-secret # The name of the native K8s secret it will create
    creationPolicy: Owner
  data:
  - secretKey: token
    remoteRef:
      key: desec-api-token # The exact name of the secret created in Azure Key Vault
```

---

### 📄 File: manifests/base/forwardauth/forwardauth.yaml
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: traefik-forward-auth
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: traefik-forward-auth
  template:
    metadata:
      labels:
        app: traefik-forward-auth
    spec:
      nodeSelector:
        workload-type: "infra"
      tolerations:
        - key: "node-role.kubernetes.io/control-plane"
          operator: "Equal"
          value: "true"
          effect: "NoSchedule"
      containers:
      - name: traefik-forward-auth
        image: thomseddon/traefik-forward-auth:2
        resources:
          requests:
            cpu: 50m
            memory: 64Mi
          limits:
            cpu: 100m
            memory: 128Mi
        env:
        - name: DEFAULT_PROVIDER
          value: oidc
        - name: PROVIDERS_OIDC_ISSUER_URL
          valueFrom:
            secretKeyRef:
              name: entra-id-credentials
              key: oidc-issuer
        - name: PROVIDERS_OIDC_CLIENT_ID
          valueFrom:
            secretKeyRef:
              name: entra-id-credentials
              key: client-id
        - name: PROVIDERS_OIDC_CLIENT_SECRET
          valueFrom:
            secretKeyRef:
              name: entra-id-credentials
              key: client-secret
        - name: SECRET
          valueFrom:
            secretKeyRef:
              name: entra-id-credentials
              key: cookie-secret
        - name: AUTH_HOST
          value: auth.samjam.dedyn.io
        - name: URL_PATH
          value: /_oauth
        - name: COOKIE_DOMAIN
          value: samjam.dedyn.io
        - name: PROVIDERS_OIDC_USER_ID_CLAIM
          value: preferred_username   
        - name: LOG_LEVEL
          value: trace 
        ports:
        - containerPort: 4181
---
apiVersion: v1
kind: Service
metadata:
  name: traefik-forward-auth
  namespace: default
spec:
  ports:
  - port: 4181
    targetPort: 4181
  selector:
    app: traefik-forward-auth
---
# The Traefik Middleware that we will attach to applications
apiVersion: traefik.io/v1alpha1
kind: Middleware
metadata:
  name: entra-forward-auth
  namespace: default
spec:
  forwardAuth:
    address: http://traefik-forward-auth.default.svc.cluster.local:4181
    trustForwardHeader: true
    authResponseHeaders:
      - X-Forwarded-User
---
# The Ingress routing traffic for the authentication callbacks
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: traefik-forward-auth-ingress
  namespace: default
  annotations:
    traefik.ingress.kubernetes.io/router.entrypoints: websecure
spec:
  tls:
    - hosts:
        - auth.samjam.dedyn.io
      secretName: samjam-dedyn-io-tls
  rules:
    - host: auth.samjam.dedyn.io
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: traefik-forward-auth
                port:
                  number: 4181```

---

### 📄 File: manifests/base/globals/homelab-globals.yaml
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: homelab-globals
  namespace: default
data:
  VW_BACKUP_REMOTE_TYPE: "${VW_BACKUP_REMOTE_TYPE}"
  VW_BACKUP_LOCATION: "${VW_BACKUP_LOCATION}"
  VW_URL: "${VW_URL}"
  GIT_REPO_URL: "${GIT_REPO_URL}"
```

---

### 📄 File: manifests/base/globals/kustomization.yaml
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - homelab-globals.yaml
```

---

### 📄 File: manifests/base/scheduling-test.yaml
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: test-infra-pod
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: test-infra
  template:
    metadata:
      labels:
        app: test-infra
    spec:
      nodeSelector:
        node-role.kubernetes.io/infra: "true"
      tolerations:
      - key: "node-role.kubernetes.io/control-plane"
        operator: "Exists"
        effect: "NoSchedule"
      containers:
      - name: pause
        image: registry.k8s.io/pause:3.9
        resources:
          requests:
            cpu: 10m
            memory: 32Mi
          limits:
            cpu: 50m
            memory: 64Mi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: test-worker-pod
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: test-worker
  template:
    metadata:
      labels:
        app: test-worker
    spec:
      nodeSelector:
        node-role.kubernetes.io/worker: "true"
      containers:
      - name: web
        image: nginx:alpine
        resources:
          requests:
            cpu: 10m
            memory: 32Mi
          limits:
            cpu: 50m
            memory: 64Mi
```

---

## ☸️ Declarative Infrastructure Files

---

### 📄 File: infrastructure/nodes/control-plane-config.yaml
```yaml
# /etc/rancher/k3s/config.yaml on KC01
node-ip: "192.168.1.50"
flannel-iface: "enp0s31f6"
write-kubeconfig-mode: "0644"  #home lab convenience, allows non-root users to read the kubeconfig
node-taint:
  - "node-role.kubernetes.io/control-plane:NoSchedule"
node-label:
  - "node-type=control-plane"
  - "workload-type=infra"

```

---

### 📄 File: infrastructure/terraform/main.tf
```yaml
# 1. Resource Group
resource "azurerm_resource_group" "homelab" {
  name     = "rg-homelab-core"
  location = "canadacentral" # Update if you used a different region
}

# 2. Azure Key Vault (Updated for AzureRM v5.0.0)
resource "azurerm_key_vault" "vault" {
  name                        = var.key_vault_name
  location                    = azurerm_resource_group.homelab.location
  resource_group_name         = azurerm_resource_group.homelab.name
  enabled_for_disk_encryption = false
  tenant_id                   = data.azurerm_client_config.current.tenant_id
  soft_delete_retention_days  = 7
  purge_protection_enabled    = false

  sku_name = "standard"

  # Enterprise Security Standard: Use Entra ID RBAC
  rbac_authorization_enabled = true
}

# 3. Entra ID Application for K3s External Secrets Operator
resource "azuread_application" "k3s_eso" {
  display_name = "app-homelab-k3s-eso"
}

# 4. Service Principal for the Application
resource "azuread_service_principal" "k3s_eso_sp" {
  client_id = azuread_application.k3s_eso.client_id
}

# 5. Password (client secret) for the Service Principal
resource "azuread_service_principal_password" "k3s_eso_sp_password" {
  service_principal_id = azuread_service_principal.k3s_eso_sp.id
}

# 6. Assign "Key Vault Secrets User" role to the Service Principal
resource "azurerm_role_assignment" "eso_kv_secrets_user" {
  scope                = azurerm_key_vault.vault.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azuread_service_principal.k3s_eso_sp.object_id
}
```

---

### 📄 File: infrastructure/terraform/outputs.tf
```yaml
output "key_vault_id" {
  description = "The Azure Resource ID of the Key Vault"
  value       = azurerm_key_vault.vault.id
}

output "key_vault_uri" {
  description = "The URI of the Key Vault used for ESO authentication"
  value       = azurerm_key_vault.vault.vault_uri
}

output "client_id" {
  description = "The Client ID of the ESO Service Principal"
  value       = azuread_service_principal.k3s_eso_sp.client_id
}

output "client_secret" {
  description = "The Client Secret of the ESO Service Principal"
  value       = azuread_service_principal_password.k3s_eso_sp_password.value
  sensitive   = true
}

output "tenant_id" {
  description = "The Azure Tenant ID"
  value       = data.azurerm_client_config.current.tenant_id
}```

---

### 📄 File: infrastructure/terraform/providers.tf
```yaml
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "=5.0.0"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 3.9"
    }
  }
}

provider "azurerm" {
  # Prevent Terraform from attempting to register missing resource providers
  resource_provider_registrations = "none"

  features {
    key_vault {
      purge_soft_delete_on_destroy    = true
      recover_soft_deleted_key_vaults = true
    }
  }
}

# Add the Azure Active Directory (Entra ID) provider
provider "azuread" {}

# Fetch the Azure AD tenant and object ID of the user executing the code
data "azurerm_client_config" "current" {}```

---

### 📄 File: infrastructure/terraform/variables.tf
```yaml
variable "location" {
  description = "The Azure region to deploy resources into"
  type        = string
  default     = "East US"
}

variable "resource_group_name" {
  description = "The name of the homelab resource group"
  type        = string
  default     = "rg-homelab-core"
}

variable "key_vault_name" {
  description = "The globally unique name of the Azure Key Vault"
  type        = string
  default     = "kv-homelab-samjam" # Must be globally unique
}```

---

## 📁 Core Configuration Files

---

### 📄 File: core/k3s-config/k3s.service
```yaml
# /etc/systemd/system/k3s.service
[Unit]
Description=Lightweight Kubernetes
Documentation=https://k3s.io
Wants=network-online.target
After=network-online.target

[Install]
WantedBy=multi-user.target

[Service]
Type=notify
EnvironmentFile=-/etc/default/%N
EnvironmentFile=-/etc/sysconfig/%N
EnvironmentFile=-/etc/systemd/system/k3s.service.env
KillMode=process
Delegate=yes
User=root
# Having non-zero Limit*s causes performance problems due to accounting overhead
# in the kernel. We recommend using cgroups to do container-local accounting.
LimitNOFILE=1048576
LimitNPROC=infinity
LimitCORE=infinity
TasksMax=infinity
TimeoutStartSec=0
Restart=always
RestartSec=5s
ExecStartPre=-/sbin/modprobe br_netfilter
ExecStartPre=-/sbin/modprobe overlay
ExecStart=/usr/local/bin/k3s \
    server \

```

---

### 📄 File: core/k3s-config/worker-config.yaml.template
```yaml
# /etc/rancher/k3s/<node>-config.yaml
server: "https://${CONTROL_PLANE_IP}:6443"
token: "${K3S_TOKEN}"
node-ip: "${WORKER_IP}"
flannel-iface: "enp0s31f6"
node-label:
  - "node-type=worker"
  - "workload-type=compute"
```

---

## 📁 Inventory Files

---

### 📄 File: inventory/hosts.ini
```yaml
[control_plane]
kc01 ansible_host=192.168.1.50

[node]
kc02

[k3s_cluster:children]
control_plane
node
```

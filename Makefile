# Homelab Cluster Operations Makefile
# Fulfills Technical Debt #4: Centralize Global Configuration

# Define the source file and the temporary build artifact
ENV_FILE ?= inventory/global.env
CLEAN_ENV := /tmp/clean.env

# Create the clean environment file BEFORE Make evaluates anything else
$(info $(shell ./scripts/workstation/sanitize-env.sh $(ENV_FILE) $(CLEAN_ENV)))

# Load global variables
include $(CLEAN_ENV)
export

# 2. Centralized staging files in a secure, unprivileged directory
STAGE := /tmp/kustomize-argocd.yaml
STAGE_CORE := /tmp/kustomize-argocd-core.yaml
DAY0_LOCK := /etc/rancher/k3s/.day0_lock

.DEFAULT_GOAL := help

.PHONY: day0-bare-metal platform-core gitops-apps \
        check-day0-lock write-day0-lock \ 
				provision-nodes deploy-ha-dns sync-azure-secrets apply-globals \
        kustomize-argocd bootstrap-argocd test \
				deploy-portainer deploy-vaultwarden deploy-vw-backup 

help: ## Display this help message with target descriptions
	@echo "=========================================================================="
	@echo " Homelab Cluster Operations Toolchain"
	@echo "=========================================================================="
	@echo "Usage: make <target> [FORCE=true]"
	@echo ""
	@echo "Targets:"
	@grep -h -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ==============================================================================
# 🚀 MACRO ENTRY POINTS (The platform lifecycle)
# ==============================================================================

# DAY 0: Bare Metal & Host OS Layer (Locked to run-once; override with FORCE=true)
day0-bare-metal: check-day0-lock provision-nodes deploy-ha-dns write-day0-lock ## [Day 0] Provision bare-metal nodes and deploy HA DNS (Keepalived + Pi-hole)
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

# Test suite: Dynamically discover and execute all unit tests under tests/
test: ## Run the complete workstation test suite
	@echo "=== Running Workstation Test Suite ==="
	python3 -m unittest discover -v -s tests -p "test_*.py"
	@echo "✅ All unit tests passed successfully!"

kustomize-argocd: ## Compile Kustomize AST and substitute environment variables
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

provision-nodes: ## Bootstrap K3s server and agent nodes over SSH
	@echo "=== Bootstrapping K3s Nodes ==="
	./scripts/bare-metal/bootstrap.sh

deploy-ha-dns: ## Deploy Keepalived and Pi-hole for high-availability DNS routing
	@echo "=== Deploying High-Availability DNS ==="
	./scripts/bare-metal/deploy-ha-dns.sh

deploy-vaultwarden: ## Deploy standalone Vaultwarden Docker container
	@echo "=== Deploying Standalone Vaultwarden ==="
	./scripts/bare-metal/deploy-vaultwarden.sh

sync-azure-secrets: ## Sync Azure Key Vault credentials to K3s cluster
	@echo "=== Syncing Azure Key Vault Credentials to K3s ==="
	./scripts/azure/sync-azure-secrets.sh

apply-globals: ## Inject homelab global environment ConfigMaps
	@echo "=== Injecting global configuration from inventory/global.env ==="
	envsubst < manifests/base/globals/homelab-globals.yaml | kubectl apply -f -

deploy-vw-backup: ## Deploy standalone Vaultwarden backup CronJob manifest
	@echo "=== Deploying Vaultwarden Backup CronJob ==="
	envsubst '$$INGRESS_IP $$DOMAIN $$VW_URL' < manifests/apps/vaultwarden/vaultwarden-backup-cronjob.yaml | kubectl apply -f -




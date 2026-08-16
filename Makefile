# Homelab Cluster Operations Makefile
# Fulfills Technical Debt #4: Centralize Global Configuration

# =============================================================================
# ⚙️ CONFIGURATION & EXTENSIONS
# =============================================================================

# Define universal binary requirements. Individual repositories can append 
# their own specific tools (e.g., REQUIRED_TOOLS += terraform or REQUIRED_TOOLS += mvnw).
REQUIRED_TOOLS ?= shellcheck git

# Define tools that are required by specific targets
OPTIONAL_TOOLS ?= python3 terraform kubectl kustomize envsubst ssh

PROFILE ?= local		## [Optional] Target environment profile. Maps to any 'inventory/<name>.env' file. Default: local
FORCE ?= false			## [Optional] Bypass safety checks and run-once safety locks. Choices: [true, false]. Default: false
CI ?= false 			## [Optional] CI/CD Mode. Bypasses local file-sourcing. Choices: [true, false]. Default: false
USE_PROFILES ?= true	## [Optional] Enable environment variable profile loading. Choices: [true, false]. Default: false

# =============================================================================
# 🛠️ LOCAL HELPER FUNCTIONS
# =============================================================================
# Track tool presence status in-memory (TOOL_PRESENT_name = true/false)
# If a tool has not been evaluated yet, its state is undefined.

# 🔎 Private helper that checks command presence and populates the status map
define check_tool
$(if $(filter undefined,$(origin TOOL_PRESENT_$(1))),\
    $(if $(shell command -v $(1) 2>/dev/null),\
        $(eval TOOL_PRESENT_$(1) := true),\
        $(eval TOOL_PRESENT_$(1) := false)\
    )\
)
endef

# 🔎 Private helper to audit tools and populate missing lists dynamically
# Usage: $(call find_missing_tools,<SUFFIX>,<tools_list>)
define find_missing_tools
$(eval MISSING_$(1) := )\
$(foreach tool,$(2),\
    $(call check_tool,$(tool))\
    $(if $(filter false,$(TOOL_PRESENT_$(tool))),$(eval MISSING_$(1) += $(tool)))\
)
endef

# 🛡️ Hard Verification: Audits tools and halts execution with exit code 1 on any failure
define require_tools
$(call find_missing_tools,REQUIRED,$(1))\
$(if $(MISSING_REQUIRED),\
    @echo "❌ ERROR: Required tool(s) missing for target '$@':";\
    $(foreach bin,$(MISSING_REQUIRED),echo "   - $(bin)";)\
    echo "🛑 Please install the missing tool(s) and try again." && exit 1;\
)
endef

# ⚠️ Soft Verification: Audits tools and prints diagnostic warnings
# halts execution with exit code 1 for missing required files only 
define audit_tools
$(call find_missing_tools,REQUIRED,$(1))\
$(call find_missing_tools,OPTIONAL,$(2))\
$(foreach tool,$(1),\
    $(if $(filter true,$(TOOL_PRESENT_$(tool))),\
		@echo "✅ $(tool) is required and present.";,\
		@echo "❌ $(tool) is required and missing.";\
	)
)
$(foreach tool,$(2),\
    $(if $(filter true,$(TOOL_PRESENT_$(tool))),\
		@echo "✅ $(tool) is present.";,\
		@echo "⚠️ $(tool) is missing.";\
	)
)
$(if $(MISSING_REQUIRED),\
    @echo "🛑 Please install the required missing tool(s) and try again." && exit 1;\
)
endef

# 🛡️ Safe Script Runner: Ensures executability, and runs the script safely
# Usage: $(call run_script,<script_path>, [optional arguments])
define run_script
@test -x $(1) || (echo "🛡️ Fixing stripped execution bit on '$(1)'..." && chmod +x $(1)); \
$(1) $(2)
endef

#
# =============================================================================
# 🧼 WHITESPACE SANITIZER (Sanitizes trailing spaces from comments in advance)
# =============================================================================
# We use eager evaluation (:=) to strip trailing whitespace immediately on startup
PROFILE      := $(strip $(PROFILE))
FORCE        := $(strip $(FORCE))
CI           := $(strip $(CI))
USE_PROFILES := $(strip $(USE_PROFILES))

ENV_FILE := inventory/$(PROFILE).env
SANITIZE_SCRIPT := ./scripts/workstation/sanitize-env.sh

# 🛡️ Establish a secure, user-owned temporary directory (CWE-377 Compliance) and a non-secure build directory
UID := $(shell id -u)
SECURE_TMP_DIR := /tmp/k3s-lab-$(UID)
BUILD_DIR := build

# Ensure the secure directory exists with strict permissions (drwx------) before evaluating paths
_prep_secure_tmp := $(shell mkdir -p $(SECURE_TMP_DIR) && chmod 700 $(SECURE_TMP_DIR))

# Dynamic workspace hashing for isolation (macOS and Linux compliant)
# 🛡️ Highly portable, subshell-free workspace hashing
WORKSPACE_HASH := $(shell (printf '%s' "$(CURDIR)" | sha256sum 2>/dev/null || printf '%s' "$(CURDIR)" | shasum -a 256 2>/dev/null || echo "default") | cut -c1-8)
CLEAN_ENV := $(SECURE_TMP_DIR)/clean-$(WORKSPACE_HASH)-$(PROFILE).env

# =============================================================================
# 🔐 ENVIRONMENT LOADER
# =============================================================================
ifeq ($(CI),true)
  # 🟢 CI/CD Mode: Inherit credentials and vars directly from runner environment
  $(info === CI/CD Mode: Inheriting environment variables from runner ===)
else ifeq ($(USE_PROFILES),true)
  # 💻 Profiles Enabled: Enforce loud fail-fast boundary if profile is missing
  ifeq ($(wildcard $(ENV_FILE)),)
    $(error ❌ ERROR: Profile configuration file not found at '$(ENV_FILE)'! Create it or set USE_PROFILES=false)
  else ifeq ($(wildcard $(SANITIZE_SCRIPT)),)
     $(error ❌ ERROR: Environment sanitizer script not found at '$(SANITIZE_SCRIPT)'! Create it or set USE_PROFILES=false)
  else
    # 💻 Local Workstation Mode: Clean, include, and export the selected profile file securely.
    $(info === Local Workstation Mode: Sanitizing and loading $(ENV_FILE) ===)
    $(info $(shell $(SANITIZE_SCRIPT) $(ENV_FILE) $(CLEAN_ENV)))
    include $(CLEAN_ENV)
    export  # ai-ignore: Necessary to propagate loaded configurations to envsubst templates during manifest generation
  endif
endif

# Sentinel file indicating onboarding compliance
SETUP_SENTINEL := .setup_done

# Centralized staging files in a secure, unprivileged directory
STAGE_kustomize-argocd := $(SECURE_TMP_DIR)/kustomize-argocd.yaml
STAGE_kustomize-argocd-core := $(SECURE_TMP_DIR)/kustomize-argocd-core.yaml
DAY0_LOCK := /etc/rancher/k3s/.day0_lock

.PHONY: setup setup-githooks check-workstation-tools guard-setup test help \
        day0-bare-metal platform-core gitops-apps \
        check-day0-lock write-day0-lock \ 
		provision-nodes deploy-ha-dns sync-azure-secrets apply-globals \
        kustomize-argocd bootstrap-argocd \
		deploy-portainer deploy-vaultwarden deploy-vw-backup \
		bundle clean _is_secure_tmp_safe _is_build_dir_safe

.DEFAULT_GOAL := help

help: ## Display this help message with target descriptions
	@echo "=========================================================================="
	@echo " Homelab Cluster Operations Toolchain"
	@echo "=========================================================================="
	@echo "Usage: make <target>"
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
	$(call require_tools,git)
	@chmod +x githooks/pre-commit githooks/commit-msg 2>/dev/null || true
	@chmod +x githooks/pre-commit.d/* githooks/commit-msg.d/* 2>/dev/null || true
	@chmod +x scripts/workstation/*.sh 2>/dev/null || true
	@git config core.hooksPath githooks
	@echo "✅ Git hooks successfully mapped to 'githooks/' and marked executable!"

check-workstation-tools: ## Validate if required binaries are present on disk without hard fail
	@echo "🔎 Auditing workstation binary toolchain..."
	$(call audit_tools,$(REQUIRED_TOOLS),$(OPTIONAL_TOOLS))

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

check-day0-lock: ## Verify if the Day 0 bare-metal layer is already provisioned
ifeq ($(FORCE),true)
	@echo "⚠️ FORCE=true specified. Bypassing Day 0 run-once safety guards!"
else
	@echo "🔍 Checking if Day 0 bare-metal layer is already provisioned..."
	$(call require_tools,ssh)
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
	$(call require_tools,ssh)
	@ssh -n -q -o BatchMode=yes $(CONTROL_PLANE_IP) "sudo mkdir -p /etc/rancher/k3s && sudo touch $(DAY0_LOCK)"

# ==============================================================================
# ⚙️ DETAILED OPERATIONAL TARGETS
# ==============================================================================

test: guard-setup ## Run the complete workstation test suite
	@echo "=== Running Workstation Test Suite ==="
	$(call require_tools,python3)
	python3 -m unittest discover -v -s tests -p "test_*.py"
	@echo "✅ All unit tests passed successfully!"

kustomize-argocd: guard-setup ## Compile Kustomize AST and substitute environment variables
	@echo "=== Compiling and Verifying ArgoCD Kustomize build ==="
	$(call require_tools,envsubst kubectl kustomize)
	kubectl kustomize manifests/base/argocd/ | envsubst > $(STAGE_kustomize-argocd)
	@echo "✅ Kustomize validation succeeded! Rendered manifest cached at $(STAGE_kustomize-argocd)"

bootstrap-argocd: kustomize-argocd ## Deploy Argo CD controller in two-phase sync pass
	@echo "=== Deploying Argo CD (GitOps Controller) ==="
	@echo "=== Phase 1: Filtering & Deploying Argo CD Base (No Custom Kinds) ==="
	# Uses standard library Python to split and filter out custom kinds (Application, AppProject)
	$(call require_tools,python3 kubectl)
	$(call run_script,./scripts/workstation/filter_manifest.py $(STAGE_kustomize-argocd) $(STAGE_kustomize-argocd-core))
	kubectl apply --server-side --force-conflicts -f $(STAGE_kustomize-argocd-core)

	@echo "=== Waiting for Custom Resource Definitions to stabilize ==="
	# We block here until the API server officially establishes the Argo CD custom schemas.
	kubectl wait --for=condition=Established crd/applications.argoproj.io crd/appprojects.argoproj.io crd/applicationsets.argoproj.io --timeout=60s
	
	@echo "=== Phase 2: Applying Custom Resources ==="
	# Re-applies the complete manifest including the now-valid custom resources
	kubectl apply --server-side --force-conflicts -f $(STAGE_kustomize-argocd)
	@rm -f $(STAGE_kustomize-argocd-core)
	@echo "🚀 Argo CD successfully bootstrapped!" 

provision-nodes: guard-setup ## Bootstrap K3s server and agent nodes over SSH
	@echo "=== Bootstrapping K3s Nodes ==="
	$(call require_tools,ssh envsubst)
	$(call run_script,./scripts/bare-metal/bootstrap.sh)

deploy-ha-dns: guard-setup ## Deploy Keepalived and Pi-hole for high-availability DNS routing
	@echo "=== Deploying High-Availability DNS ==="
	$(call require_tools,ssh)
	$(call run_script,./scripts/bare-metal/deploy-ha-dns.sh)

deploy-vaultwarden: guard-setup ## Deploy standalone Vaultwarden Docker container
	@echo "=== Deploying Standalone Vaultwarden ==="
	$(call require_tools,ssh)
	$(call run_script,./scripts/bare-metal/deploy-vaultwarden.sh)
	

sync-azure-secrets: guard-setup ## Sync Azure Key Vault credentials to K3s cluster
	@echo "=== Syncing Azure Key Vault Credentials to K3s ==="
	$(call require_tools,ssh)
	$(call run_script,./scripts/azure/sync-azure-secrets.sh)
	

apply-globals: guard-setup ## Inject homelab global environment ConfigMaps
	@echo "=== Injecting global configuration from environment variables ==="
	$(call require_tools,envsubst kubectl)
	envsubst < manifests/base/globals/homelab-globals.yaml | kubectl apply -f -

deploy-vw-backup: guard-setup ## Deploy standalone Vaultwarden backup CronJob manifest
	@echo "=== Deploying Vaultwarden Backup CronJob ==="
	$(call require_tools,envsubst kubectl)
	envsubst '$$INGRESS_IP $$DOMAIN $$VW_URL' < manifests/apps/vaultwarden/vaultwarden-backup-cronjob.yaml | kubectl apply -f -

bundle: guard-setup ## Bundle the active codebase into a single markdown for AI agent consumption
	@echo "=== Bundling codebase into a single markdown file ==="
	$(call run_script,./scripts/workstation/bundle-codebase.sh)


# ==============================================================================
# 🧹 CLEANUP CONTROLS
# ==============================================================================

# 🛡️ Pure GNU Make-level path safety checkers (No subshell spawn overhead, completely decoupled)
is_secure_tmp_safe = $(and $(1),$(filter /tmp/%,$(1)),$(filter-out /tmp/,$(1)))
is_build_dir_safe = $(and \
	$(1),\
	$(filter-out . ..,$(1)),\
	$(if $(findstring ..,$(1)),,true),\
	$(filter-out ~%,$(1)),\
	$(if $(filter /%,$(1)),$(filter $(CURDIR)/%,$(1)),true),\
	$(filter-out $(CURDIR) $(CURDIR)/,$(1))\
)

clean: ## Remove temporary build files and decrypted environment caches
	@echo "🧹  Wiping workspace build artifacts and secure caches..."

	# 🛡️ Guard 1: Only purge SECURE_TMP_DIR if it is strictly a safe /tmp subdirectory
	$(if $(call is_secure_tmp_safe,$(SECURE_TMP_DIR)),\
		@rm -rf "$(SECURE_TMP_DIR)" && echo "✅ Purged secure temp directory: $(SECURE_TMP_DIR)",\
		@echo "⚠️ Skipped SECURE_TMP_DIR purge: Path is empty, unsafe, or outside /tmp/"\
	)
	
	# 🛡️ Guard 2: Only purge BUILD_DIR if it is a safe relative folder name
	$(if $(call is_build_dir_safe,$(BUILD_DIR)),\
		@rm -rf "$(BUILD_DIR)" && echo "✅ Purged local build directory: $(BUILD_DIR)",\
		@echo "⚠️ Skipped BUILD_DIR purge: Absolute path, home folder, or directory traversal detected"\
	)

	@echo "✅ Cleanup complete."	

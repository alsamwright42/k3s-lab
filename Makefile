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

.PHONY: provision-nodes deploy-ha-dns deploy-vaultwarden sync-azure-secrets bootstrap-gitops apply-globals

provision-nodes:
	@echo "=== Bootstrapping K3s Nodes ==="
	./scripts/bare-metal/bootstrap.sh

deploy-ha-dns:
	@echo "=== Deploying High-Availability DNS ==="
	./scripts/bare-metal/deploy-ha-dns.sh

deploy-vaultwarden:
	@echo "=== Deploying Standalone Vaultwarden ==="
	./scripts/bare-metal/deploy-vaultwarden.sh

sync-azure-secrets:
	@echo "=== Syncing Azure Key Vault Credentials to K3s ==="
	./scripts/azure/sync-azure-secrets.sh

apply-globals:
	@echo "=== Injecting global configuration from inventory/global.env ==="
	envsubst < manifests/base/globals/homelab-globals.yaml | kubectl apply -f -

deploy-vw-backup:
	@echo "=== Deploying Vaultwarden Backup CronJob ==="
	envsubst '$$INGRESS_IP $$DOMAIN $$VW_URL' < manifests/apps/vaultwarden/vaultwarden-backup-cronjob.yaml | kubectl apply -f -

bootstrap-gitops:
	@echo "=== Installing Argo CD (GitOps Controller) ==="
	# To be implemented next!
	@echo "Argo CD deployment pending..."

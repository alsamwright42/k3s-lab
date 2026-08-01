#!/usr/bin/env bash
set -euo pipefail

# Anchor paths to the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Define clean absolute paths for Terraform and manifest directories
TF_DIR="${REPO_ROOT}/infrastructure/terraform"
MANIFEST_DIR="${REPO_ROOT}/manifests/base/external-secrets"

echo "=== Syncing Azure Key Vault Credentials to K3s ==="

# Extract all dynamic values from Terraform state
echo "Extracting data from Terraform..."
CLIENT_ID=$(terraform -chdir="${TF_DIR}" output -raw client_id)
CLIENT_SECRET=$(terraform -chdir="${TF_DIR}" output -raw client_secret)
export KEY_VAULT_URI=$(terraform -chdir="${TF_DIR}" output -raw key_vault_uri)
export TENANT_ID=$(terraform -chdir="${TF_DIR}" output -raw tenant_id)

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
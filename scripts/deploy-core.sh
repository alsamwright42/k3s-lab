#!/usr/bin/env bash
set -euo pipefail

# Set paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

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
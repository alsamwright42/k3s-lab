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

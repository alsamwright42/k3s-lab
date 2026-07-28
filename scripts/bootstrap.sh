#!/usr/bin/env bash
set -euo pipefail

TARGETS=("kc01" "kc02")

echo "=== K3s Lab Connectivity Check ==="
for target in "${TARGETS[@]}"; do
    echo -n "Testing SSH connection to ${target}... "
    if ssh -q -o BatchMode=yes -o ConnectTimeout=5 "${target}" exit; then
        echo "OK"
    else
        echo "FAILED"
        exit 1
    fi
done

echo "All cluster nodes reachable via SSH."

echo ""
echo "=== Deploying K3s Node Configurations ==="

echo "--> Updating KC01 (control plane)..."
scp infrastructure/nodes/kc01-config.yaml kc01:/tmp/config.yaml
ssh kc01 "sudo mv /tmp/config.yaml /etc/rancher/k3s/config.yaml && sudo systemctl restart k3s"

echo "Waiting 12 seconds for KC01 K3s API server to initialize..."
sleep 12

echo "--> Updating KC02 (worker node)..."
scp infrastructure/nodes/kc02-config.yaml kc02:/tmp/config.yaml
ssh kc02 "sudo mv /tmp/config.yaml /etc/rancher/k3s/config.yaml && sudo systemctl restart k3s-agent"

echo "Waiting 5 seconds for KC02 agent handshake..."
sleep 5

echo ""
echo "=== Node Bootstrap Complete ==="
echo "Checking cluster status and labels:"
kubectl get nodes --show-labels

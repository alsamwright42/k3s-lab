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

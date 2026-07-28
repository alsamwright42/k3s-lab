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
fi
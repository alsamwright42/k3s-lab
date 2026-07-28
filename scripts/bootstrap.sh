#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

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
    echo "Error: Timed out waiting for ${message} after $(($retries * $wait_time)) seconds." >&2
    exit 1
}

# Self-Healing Safety Net: Automatically strip Windows CRLF line endings
# Excludes this running script to prevent the self-modifying truncation trap.
for script in "${SCRIPT_DIR}"/*.sh; do
    if [ -f "$script" ] && [ "$script" != "${BASH_SOURCE}" ]; then
        sed -i -e 's/\r$//' "$script" 2>/dev/null || true
    fi
done

# Infrastructure Inventory
CONTROL_PLANE_NODE="kc01"
export CONTROL_PLANE_IP="192.168.1.50"

declare -A WORKER_NODES=(
    ["kc02"]="192.168.1.51"
)

echo "=== K3s Lab Connectivity Check ==="
for node in "$CONTROL_PLANE_NODE" "${!WORKER_NODES[@]}"; do
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
for node in "$CONTROL_PLANE_NODE" "${!WORKER_NODES[@]}"; do
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
echo "Checking cluster status and labels:"
wait_for_condition 15 4 "Cluster nodes to report as Ready" ssh -n -o BatchMode=yes "${CONTROL_PLANE_NODE}" "sudo k3s kubectl get nodes --show-labels"


#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

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
        if "${cmd[@]}" >/dev/null; then
            echo "  -> Success!"
            return 0
        fi
        echo "  -> Not ready yet. Retrying in ${wait_time}s... ($i/$retries)"
        sleep "$wait_time"
    done

    # If the loop finishes without success, throw an error and halt the script
    echo "Error: Timed out waiting for ${message} after $((retries * wait_time)) seconds." >&2
    exit 1
}

echo "=== Validating and Parsing Node Inventory ==="
declare -a CLUSTER_NODES

# Validate and Register Control Plane
if [ -z "${CONTROL_PLANE_NODE:-}" ]; then
    echo "FAILED: CONTROL_PLANE_NODE is missing from the provided environment!"
    exit 1
fi

declare -A WORKER_NODES

# Validate and Parse Worker Nodes
for record in $WORKER_NODES_CONFIG; do
    IFS=':' read -r node ip <<< "$record"

    # FAIL EARLY: Check if the string was malformed (missing node or IP)
    if [ -z "${node:-}" ] || [ -z "${ip:-}" ]; then
        echo "FAILED: Malformed worker record '$record'. Expected format 'hostname:IP'."
        exit 1
    fi

    # Register the worker and dynamically build its config file name
    WORKER_NODES["$node"]="$ip"
done

# Create cluster node list
CLUSTER_NODES=("CONTROL_PLANE_NODE" "${!WORKER_NODES[@]}")

echo "=== K3s Lab Connectivity Check ==="
# Check Control Plane
echo -n "Testing SSH connection to ${CONTROL_PLANE_NODE}... "
if ssh -n -o BatchMode=yes -o ConnectTimeout=5 "${CONTROL_PLANE_NODE}" exit; then
    echo "Control plane connectivity verified."
else
    echo "FAILED: Cannot reach control plane node."
    exit 1
fi


for node in "${CLUSTER_NODES[@]}"; do
    echo -n "Testing SSH connection to ${node}... "
    if ssh -n -o BatchMode=yes -o ConnectTimeout=5 "${node}" exit; then
        echo "OK"
    else
        echo "FAILED"
        exit 1
    fi
done

echo ""
echo "=== Provisioning Remote Host Environments ==="
for node in "${CLUSTER_NODES[@]}"; do
    echo "--> Provisioning ${node}..."
    scp -o BatchMode=yes "${SCRIPT_DIR}/provision-node.sh" "${node}:/tmp/provision-node.sh"
    scp -o BatchMode=yes "${SCRIPT_DIR}/apply-k3s-node-config.sh" "${node}:/tmp/apply-k3s-node-config.sh"
    ssh -n -o BatchMode=yes "${node}" "sudo bash /tmp/provision-node.sh"
done

echo ""
echo "=== Deploying Control Plane ($CONTROL_PLANE_NODE) ==="
scp -o BatchMode=yes "${REPO_ROOT}/infrastructure/nodes/control-plane-config.yaml" "${CONTROL_PLANE_NODE}:/tmp/config.yaml"
ssh -n -o BatchMode=yes "${CONTROL_PLANE_NODE}" "sudo /usr/local/bin/apply-k3s-node-config.sh control-plane"

wait_for_condition 12 5 "K3s control plane to be ready" ssh -n -o BatchMode=yes "${CONTROL_PLANE_NODE}" "sudo k3s kubectl get nodes | grep -q 'Ready'"

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
    # shellcheck disable=SC2016
    # Use envsubst to populate the YAML template with our active memory variables
    envsubst '$CONTROL_PLANE_IP $K3S_TOKEN $WORKER_IP $INTERFACE' \
        < "${REPO_ROOT}/core/k3s-config/worker-config.yaml.template" \
        > "/tmp/${node}-config.yaml"

    scp -o BatchMode=yes "/tmp/${node}-config.yaml" "${node}:/tmp/config.yaml"
    ssh -n -o BatchMode=yes "${node}" "sudo /usr/local/bin/apply-k3s-node-config.sh worker"

done

echo ""
echo "=== Node Bootstrap Complete ==="
echo "Verifying all registered nodes are Ready..."

# Loop through every node in the associative array
for target_node in "${CLUSTER_NODES[@]}"; do
    wait_for_condition 15 4 "Node ${target_node} to report as Ready" \
        ssh -n -o BatchMode=yes kc01 "sudo k3s kubectl get nodes | grep -E '^${target_node}\s+.*Ready'"
done

echo ""
echo "Cluster is fully online. Final status and labels:"
ssh -n -o BatchMode=yes kc01 "sudo k3s kubectl get nodes --show-labels"




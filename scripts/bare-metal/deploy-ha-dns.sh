#!/usr/bin/env bash
set -euo pipefail

echo "=== Validating and Parsing HA Node Inventory ==="
declare -A HA_NODES

# Rebuild the associative array from the flat string in the node config environment variable
for record in $HA_NODES_CONFIG; do
    # Extract the three pieces of data separated by colons
    IFS=':' read -r node state priority <<< "$record"
    
    # Fail early if the string is malformed
    if [ -z "${node:-}" ] || [ -z "${state:-}" ] || [ -z "${priority:-}" ]; then
        echo "FAILED: Malformed HA node record '$record'. Expected format 'hostname:STATE:PRIORITY'."
        exit 1
    fi
    
    # Reconstruct the exact format your script originally used
    HA_NODES["$node"]="${state}:${priority}"
done

echo "=== Deploying High-Availability DNS (Keepalived + Pi-hole) ==="

for node in "${!HA_NODES[@]}"; do
    IFS=':' read -r state priority <<< "${HA_NODES[$node]}"
    echo "--> Provisioning ${node} as ${state} (Priority: ${priority})..."

    # 1. Install Keepalived on the host OS
    ssh -q -o BatchMode=yes "${node}" "sudo apt-get update && sudo apt-get install -y keepalived"

    # 2. Configure Keepalived for the Virtual IP (VIP)
    cat <<EOF | ssh -q -o BatchMode=yes "${node}" "sudo tee /etc/keepalived/keepalived.conf > /dev/null"
vrrp_instance VI_CLUSTER_DNS {
    state ${state}
    interface ${INTERFACE}
    virtual_router_id 53
    priority ${priority}
    advert_int 1
    authentication {
        auth_type PASS
        auth_pass k3s_dns_ha
    }
    virtual_ipaddress {
        ${VIP}/24 dev ${INTERFACE}
    }
}
EOF

    # Restart and enable Keepalived
    ssh -q -o BatchMode=yes "${node}" "sudo systemctl restart keepalived && sudo systemctl enable keepalived"

    # 3. Deploy Standalone Pi-hole via Docker
    echo "    Spinning up Pi-hole container..."
    ssh -q -o BatchMode=yes "${node}" "sudo docker rm -f pihole 2>/dev/null || true"
    
    # We publish DNS (53) normally, but map the Web UI to 8053 so it doesn't conflict with Traefik Ingress
    ssh -q -o BatchMode=yes "${node}" "sudo docker run -d \\
        --name pihole \\
        --restart=unless-stopped \\
        -p 53:53/tcp -p 53:53/udp \\
        -p 8053:80/tcp \\
        -e TZ=\"America/Denver\" \\
        -e WEBPASSWORD=\"${PIHOLE_PW}\" \\
        -v /opt/pihole/etc-pihole:/etc/pihole \\
        -v /opt/pihole/etc-dnsmasq.d:/etc/dnsmasq.d \\
        pihole/pihole:latest >/dev/null"

    # 4. Inject Split-Horizon DNS configuration
    echo "    Applying Split-Horizon DNS rewrite for ${DOMAIN} -> ${VIP}..."
    ssh -q -o BatchMode=yes "${node}" "sudo bash -c 'echo \"address=/${DOMAIN}/${VIP}\" > /opt/pihole/etc-dnsmasq.d/99-k3s-cluster.conf'"
    
    # Restart Pi-hole to load the new dnsmasq config
    ssh -q -o BatchMode=yes "${node}" "sudo docker restart pihole >/dev/null"

    echo "--> ${node} deployment successful."
    echo ""
done

echo "=== HA DNS Deployment Complete ==="
echo "Keepalived VIP: ${VIP} is now active."
echo "Pi-hole Web UIs accessible at: http://192.168.1.50:8053 and http://192.168.1.51:8053"

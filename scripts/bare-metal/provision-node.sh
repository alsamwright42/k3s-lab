#!/usr/bin/env bash
set -euo pipefail

echo "=== Installing OS Dependencies and Docker Engine ==="
sudo apt-get update
sudo apt-get install -y curl apt-transport-https ca-certificates software-properties-common

# Install Docker Engine if it is not already installed
if ! command -v docker &> /dev/null; then
    echo "--> Docker not found. Installing native Docker Engine..."
    curl -fsSL https://get.docker.com | sudo sh
    sudo systemctl enable docker
    sudo systemctl start docker
else
    echo "--> Docker is already installed."
fi

# Add the sysop user to the docker group so you don't need sudo for docker commands
sudo usermod -aG docker sysop

echo "=== Provisioning Cluster Node OS Security & Helper Scripts ==="

# 1. Create the administrative group & assign user
sudo groupadd -f k3s-admin
sudo usermod -aG k3s-admin sysop

# 2. Grant k3s-admin group ownership over /etc/rancher/k3s/
sudo mkdir -p /etc/rancher/k3s
sudo chown -R root:k3s-admin /etc/rancher/k3s
sudo chmod 775 /etc/rancher/k3s

# 3. Copy the helper script into place from staging
if [ -f /tmp/apply-k3s-node-config.sh ]; then
    sudo cp /tmp/apply-k3s-node-config.sh /usr/local/bin/apply-k3s-node-config.sh
    sudo chmod 755 /usr/local/bin/apply-k3s-node-config.sh
else
    echo "Error: /tmp/apply-k3s-node-config.sh not found." >&2
    exit 1
fi

# 4. Enforce Least-Privilege Sudoers Rule
echo "sysop ALL=(ALL) NOPASSWD: /usr/local/bin/apply-k3s-node-config.sh" | sudo tee /etc/sudoers.d/k3s-admin-safe
sudo chmod 0440 /etc/sudoers.d/k3s-admin-safe

echo "=== Node Provisioning Complete ==="
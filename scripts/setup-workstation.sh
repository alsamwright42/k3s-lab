#!/usr/bin/env bash
# Define script and repository root directories dynamically
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# 1. Fetch the Kubeconfig from KC01 and point it to the static IP
mkdir -p ~/.kube
ssh -n -o BatchMode=yes kc01 "sudo cat /etc/rancher/k3s/k3s.yaml" | sed "s/127.0.0.1/192.168.1.50/" > ~/.kube/config
chmod 600 ~/.kube/config

# 2. Download and install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
#    Install into system path with execution permissions
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
#    Clean up the downloaded file
rm kubectl

# 3. Install the Helm CLI
curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# 4. Add the jetpack repository to Helm
echo "Adding jetstack Helm repository..."
helm repo add jetstack https://charts.jetstack.io
helm repo update

# 5. Add the External Secrets repository to Helm
echo "Adding External Secrets Helm repository..."
helm repo add external-secrets https://charts.external-secrets.io
helm repo update

# 6. Verify local environment variables
echo "Verifying local .env file and tokens..."
if [ ! -f "${REPO_ROOT}/.env" ]; then
    echo "WARNING: .env file not found at repository root!"
    echo "Please create it and add DESEC_API_TOKEN=your_token"
else
    if grep -q "DESEC_API_TOKEN" "${REPO_ROOT}/.env"; then
        echo "OK: DESEC_API_TOKEN found in .env"
    else
        echo "WARNING: DESEC_API_TOKEN is missing from .env!"
    fi
fi

# 7. Install the Terraform CLI (Official HashiCorp Repository)
echo "Installing Terraform CLI..."
# Install prerequisite packages
sudo apt-get update && sudo apt-get install -y gnupg software-properties-common curl
# Add the HashiCorp GPG key
wget -O- https://apt.releases.hashicorp.com/gpg | \
  gpg --dearmor | \
  sudo tee /usr/share/keyrings/hashicorp-archive-keyring.gpg > /dev/null
# Add the official HashiCorp Linux repository
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] \
  https://apt.releases.hashicorp.com $(lsb_release -cs) main" | \
  sudo tee /etc/apt/sources.list.d/hashicorp.list
# Install Terraform
sudo apt-get update && sudo apt-get install -y terraform
echo "Terraform installation complete. Version:"
terraform -version

# 8. Install the Azure CLI
echo "Installing Azure CLI..."
# Download the script to a temporary file first
curl -sL https://aka.ms/InstallAzureCLIDeb -o /tmp/install-az.sh
# Execute it
sudo bash /tmp/install-az.sh
# Clean up the temporary file
rm /tmp/install-az.sh

echo "Azure CLI installation complete. Version:"
az version
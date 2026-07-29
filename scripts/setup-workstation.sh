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
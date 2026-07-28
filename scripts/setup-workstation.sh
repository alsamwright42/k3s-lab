# 1. Fetch the Kubeconfig from KC01 and point it to the static IP
mkdir -p ~/.kube
ssh -n -o BatchMode=yes kc01 "sudo cat /etc/rancher/k3s/k3s.yaml" | sed "s/127.0.0.1/192.168.1.50/" > ~/.kube/config
chmod 600 ~/.kube/config

# 2. Install the Helm CLI
curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
| Component | Target Node | Deployment Priority | Operational Status | Notes |
| ------ | ------ | ------ | ------ | ------ |
| K3s Server Engine | kc01 | Tier 1 (Core Runtime) | Active | Stable with proper taints/tolerations |
| K3s Agent Engine | kc02 | Tier 1 (Core Runtime) | Active | Stable with compute/worker labels |
| Flannel CNI & CoreDNS | kc01, kc02 | Tier 1 (Core Runtime) | Active | |
| Traefik Ingress Controller | kc01 | Tier 2 (Edge Routing) | Active | Default K3s Bundle |
| Azure Infrastructure (IaC) | Cloud | Tier 3 (Cloud Dependencies) | Active | Key Vault, App Reg, and SP provisioned via Terraform |
| Cert-Manager & deSEC Webhook | kc01 | Tier 3 (Certificates) | Active | Helm deployed; waiting on ESO for secret injection |
| External Secrets Operator (ESO) | kc01 | Tier 3 (Secret Management) | Planned | Next Step: Syncing Azure Key Vault to cluster |
| Microsoft Entra ID Integration | kc01 | Tier 4 (Identity & Access) | In Progress | App Registration built; ForwardAuth deployment pending |
| Portainer | kc01 | Tier 5 (Management) | Active | Deployed via Helm |
| Vaultwarden | kc02 | Tier 5 (Applications) | Planned | Password vault, backed by KeePass .kdbx |
| Observability Stack | kc01, kc02 | Tier 5 (Observability) | Planned | Prometheus/Grafana Loki |
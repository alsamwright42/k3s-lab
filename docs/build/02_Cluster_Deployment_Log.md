| Component | Target Node | Deployment Priority | Operational Status | Notes |  
| :--- | :--- | :--- | :--- | :--- |  
| K3s Server Engine | kc01 | Tier 1 (Core Runtime) | Active | Stable with proper taints/tolerations |  
| K3s Agent Engine | kc02 | Tier 1 (Core Runtime) | Active | Stable with compute/worker labels |  
| Flannel CNI & CoreDNS | kc01, kc02 | Tier 1 (Core Runtime) | Active | |  
| Traefik Ingress Controller | kc01 | Tier 2 (Edge Routing) | Active | Default K3s Bundle |  
| Cert-Manager & ClusterIssuers | kc01 | Tier 3 (Certificates) | Planned | Helm Deployment (Immediate Next Step) |  
| Microsoft Entra ID Integration | kc01 | Tier 4 (Identity & Access) | Planned | OIDC / App Registration |  
| Portainer | kc01 | Tier 5 (Management) | Active | Deployed via Helm |  
| Vaultwarden | kc02 | Tier 5 (Applications) | Planned | Password vault, backed by KeePass .kdbx |  
| Observability Stack (Prometheus/Grafana) | kc01, kc02 | Tier 5 (Observability) | Planned | |  

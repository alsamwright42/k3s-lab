# **04_Architecture_Strategy**
I am building a 2-node bare-metal homelab (Dell hardware) running a lightweight Kubernetes cluster (k3s) to mimic a cloud-native enterprise/SaaS architecture (inspired by Azure security standards).

Here is our current architecture plan, context, and decisions made so far:

## 1. Cluster Architecture & Node Strategy

- **Distribution:** Using K3s (avoiding `kind` as it is for ephemeral dev/testing, not 24/7 homelabs).

- **Control Plane Node:** Tainted with `node-role.kubernetes.io/control-plane:NoSchedule` for stability, but using tolerations and strict resource limits to run lightweight core infra utilities (Traefik, Portainer, Authentik/IdP) locally. Heavy user workloads are pinned to the worker node via `nodeSelector`.

- **Host OS vs. K8s:** Hardware-dependent apps (e.g., 3D printing/Klipper via USB/serial) run directly on the host OS via `systemd` or Docker to avoid hardware pass-through issues, and are exposed externally via Traefik Ingress.

## 2. Identity Provider (IdP) &amp; Security Stack

- **Identity Strategy:** Moving away from heavy self-hosted Keycloak deployments.

- **Option A (Self-Hosted):** Authentik (lightweight OIDC/SAML/LDAP provider using ~350MB RAM, ideal for custom execution flows and offline reliability).

- **Option B (Cloud Managed):** Microsoft Entra External ID (Azure’s CIAM solution, direct equivalent to AWS Cognito, free for up to 50k MAUs, 0 MB local cluster footprint).

- **Azure Enterprise Mimesis:** Mapping open-source tooling 1:1 to Azure native security services:

- **Policy Enforcement (Azure Policy equivalent):** Kyverno

- **Runtime Threat Detection (Defender equivalent):** Falco (eBPF kernel-level monitoring)

- **SIEM / Telemetry (Sentinel/Log Analytics equivalent):** Grafana Loki + Grafana

- **Zero Trust / Access Control:** Teleport or Traefik ForwardAuth

- **User Access & RBAC (Entra ID):** To maintain strict enterprise non-repudiation and auditing compliance, generic shared administrative accounts (e.g., `admin@`) are strictly prohibited. Access is granted exclusively through named individual "people" identities (e.g., `sam@alsamwrightgmail.onmicrosoft.com`). Application privileges are never assigned directly to the user; instead, access is managed by assigning the Traefik ForwardAuth enterprise application to dedicated Entra ID Security Groups (e.g., `Homelab-Cluster-Admins`), and adding the named identities to those groups.

#### 3. Certificate Management & TLS Strategy
* **Automated TLS Stack:** Utilizing `cert-manager` integrated with the deSEC DNS-01 ACME challenge webhook to automatically generate Let's Encrypt certificates [3]. 
* **Certificate Scope (Wildcard):** We are explicitly deploying a wildcard certificate (`*.samjam.dedyn.io`) to cover the entire cluster ingress.
* **Enterprise Mimesis Deviation (Accepted Risk):** In a strict enterprise environment, utilizing a wildcard certificate violates the Principle of Least Required Scope (Least Privilege), as compromising the private key exposes the blast radius of all subdomains.
* **Trade-off Justification:**
  * **Automation & Velocity:** Allows the Traefik Ingress controller [3] to dynamically secure new subdomains (e.g., `auth.samjam.dedyn.io`, `vault.samjam.dedyn.io`) without triggering a new Let's Encrypt API challenge per service.
  * **Rate Limiting:** Prevents hitting strict Let's Encrypt API throttling limits (e.g., 5 failures per hour) during frequent homelab teardown and rebuild cycles.
  * **Risk Mitigation:** The private key is generated and stored exclusively within the K3s cluster's internal storage as a Kubernetes Secret (`samjam-dedyn-io-tls`). It is managed automatically by `cert-manager` and never manually leaves the cluster environment.


## Your Task:

Acts as my expert Cloud/DevOps Architect. Help me continue designing, deploying, and configuring this K3s homelab, keeping enterprise best practices, resource constraints, and Azure-aligned architectural patterns top of mind  

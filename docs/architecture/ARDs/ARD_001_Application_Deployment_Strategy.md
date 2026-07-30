# ARD 001: Application Deployment Strategy (Vaultwarden)

## Context
During the deployment of Tier 5 (Applications), Vaultwarden was introduced to the cluster to validate the Tier 4 (Identity & Access) Zero-Trust boundary enforced by Microsoft Entra ID and Traefik ForwardAuth. 

In a standard enterprise environment, applications are deployed via parameterized Helm charts to enable dynamic secret injection, version control, and automated rollbacks. However, Vaultwarden was deployed using a static, raw Kubernetes YAML manifest.

## Decision
We accepted the operational trade-off of deploying Vaultwarden via a raw YAML manifest (`manifests/apps/vaultwarden/vaultwarden.yaml`) for the immediate bootstrapping phase. 

This decision allows for rapid validation of the Traefik ForwardAuth proxy loop and OIDC callbacks without the overhead of packaging a custom Helm chart before the automated GitOps pipeline is fully established. Resource quotas (`requests` and `limits`) have been hardcoded directly into the manifest to ensure compliance with our cluster governance policies.

## Consequences & Next Steps
* **Accepted Risk:** Static manifests are susceptible to configuration drift and make secret injection (via External Secrets Operator) more manual.
* **Target State Transition:** Once the GitOps controller (Argo CD / Flux) and External Secrets Operator (ESO) are deployed, this static Vaultwarden manifest must be refactored into a Helm chart or Kustomize overlay. This will align the application with our strict enterprise declarative deployment standards.
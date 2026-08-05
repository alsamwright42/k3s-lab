# ADR 003: Zero-Trust Proxy & TLS Namespace Architecture

## Status
Active

## Context
During the deployment of Tier 4 (Identity & Access) and Tier 5 (Applications), we integrated Microsoft Entra External ID with Traefik ForwardAuth and automated our TLS certificates via `cert-manager` and the deSEC DNS-01 webhook. 

Connecting these independent systems revealed several Kubernetes namespace boundary and OIDC token claim constraints that must be standardized for all future workloads.

## Decisions

### 1. Cross-Namespace Middleware Routing
Traefik runs in the `kube-system` namespace, while the ForwardAuth proxy and user applications (e.g., Vaultwarden) run in workload namespaces (e.g., `default`).
* **Rule:** Any Traefik `Middleware` resource defined in a workload namespace must reference its backend service using the Kubernetes Fully Qualified Domain Name (FQDN). 
* **Example:** `address: http://traefik-forward-auth.default.svc.cluster.local:4181`

### 2. Entra ID Token Claim Mapping
Microsoft Entra ID does not pass the `email` claim for purely cloud-native `.onmicrosoft.com` administrative accounts.
* **Rule:** Traefik ForwardAuth must be configured with `PROVIDERS_OIDC_USER_ID_CLAIM: preferred_username` to ensure authentication loops do not fail when identifying administrative identities.

### 3. TLS Certificate Namespace Scoping
Kubernetes strictly forbids an `Ingress` from mounting a TLS `Secret` that resides in a different namespace. 
* **Rule:** The `Certificate` manifest generating the wildcard TLS secret (`samjam-dedyn-io-tls`) must be deployed directly into the namespace where the applications reside (e.g., `default`), **not** in the `cert-manager` infrastructure namespace. 
* **Future Consideration:** If we expand to multiple workload namespaces (e.g., separating `apps` from `monitoring`), we will need to deploy a tool like *kubed* or *reflector* to automatically sync the wildcard TLS secret across namespace boundaries.

## Consequences
These rules ensure that our Zero-Trust authentication proxy successfully intercepts and validates traffic, and that Traefik successfully serves a trusted Let's Encrypt production certificate without throwing `500 Internal Server Error` or `ERR_CERT_AUTHORITY_INVALID` warnings.

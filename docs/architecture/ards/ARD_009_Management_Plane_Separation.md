### ARD 009: Management Plane Separation (Vaultwarden)

#### Status
Active

#### Context
Vaultwarden was initially deployed inside the K3s cluster behind Traefik ForwardAuth and Microsoft Entra ID. However, this created two critical issues:
1. **Zero-Trust Friction:** Forcing non-technical family members to authenticate against Microsoft Entra ID before accessing the password manager created unacceptable usability friction (double-authentication). 
2. **Break-Glass Survival:** Keeping the master credential vault inside the application compute cluster violates the enterprise principle of Separating the Management Plane from the Compute Plane. If K3s crashes, the credentials required to fix it become inaccessible.

#### Decision
Vaultwarden was removed from the K3s cluster workloads and migrated to run as a standalone Docker container directly on the host OS of the worker node (`kc02`). 
To maintain automated wildcard TLS via cert-manager, we utilized the Kubernetes "External Service" pattern. We created a `Service` and `Endpoints` object in K3s that tells Traefik to terminate the SSL for `vault.samjam.dedyn.io` and route the raw traffic out of the cluster to the standalone Docker port on `kc02`, explicitly omitting the Entra ID ForwardAuth middleware.

#### Consequences
*   **Usability:** Family members can now use native Bitwarden mobile apps and browser extensions frictionlessly.
*   **Resilience:** If K3s crashes, the Vaultwarden Docker container remains online and accessible via the host's direct IP.
*   **Host Management:** This introduces a requirement to manage native Docker Engine on the bare-metal nodes alongside K3s.

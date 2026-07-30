# ARD 007: DNS, Routing & Certificate Strategy

## Status
Active

## Context
Establishing secure internal communications, external ingress routing, and automated TLS certificate management for the homelab services (`*.samjam.dedyn.io`).

## Summary of Findings

### 1. Split-Horizon DNS
* **The Issue:** Pinging internal nodes via their public FQDNs routes traffic out to the ISP and relies on NAT hairpinning to return, which can break node-to-node communication if the external link drops.
* **The Solution:** OpenWrt `dnsmasq` serves a dedicated `.lan` zone internally. This isolates internal cluster traffic (e.g., `kc01.lan`) strictly to the local `192.168.1.0/24` subnet while leaving `samjam.dedyn.io` strictly for external WAN routing.

### 2. Disabling UFW on K3s Nodes
* **The Issue:** Running `ufw` on Kubernetes nodes causes iptables conflicts with the Flannel CNI, dropping pod-to-pod and overlay network traffic.
* **The Solution:** Host-level firewalls (`ufw`) were disabled on KC01 and KC02. External boundary protection is handled exclusively by the OpenWrt edge router.

### 3. Imperative Secret Injection for DNS-01 Challenges
* **The Issue:** Committing the deSEC API token into Git to configure `cert-manager` creates a critical security leak.
* **The Solution:** The token is stored in a `.env` file (added to `.gitignore`) and injected imperatively via `kubectl create secret generic --from-env-file`. This bridges the gap safely until the External Secrets Operator (ESO) and Azure Key Vault are fully integrated.

### 4. Hybrid Password Vault Architecture
* **The Issue:** Depending entirely on a self-hosted cluster for password management risks a complete lockout during a total cluster hardware failure.
* **The Solution:** **Vaultwarden** acts as the live, user-friendly daily driver within the K3s cluster. A CronJob is configured to automate encrypted backups to a standalone `.kdbx` (KeePass) file, ensuring full offline "break-glass" recovery.

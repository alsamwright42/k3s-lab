# 00 Cluster Bootstrap Runbook

## Overview
This runbook documents the imperative bootstrapping steps required to bring the bare-metal hardware up to a "GitOps Ready" state. Once these steps are complete, Argo CD takes over the declarative management of all Kubernetes workloads.

## The Bootstrap Sequence
The sequence is centrally executed via the root `Makefile`, pulling shared configuration from `inventory/global.env`.

1. **`make provision-nodes`**: Executes `scripts/bare-metal/bootstrap.sh` to configure the headless Debian OS, apply strict static IP bindings (avoiding ISP router DHCP dependencies), and bootstrap the K3s daemons.
2. **`make deploy-ha-dns`**: Executes `scripts/bare-metal/deploy-ha-dns.sh` to spin up Keepalived and Pi-hole natively on the hosts for Split-Horizon DNS and VIP management.
3. **`make deploy-vaultwarden`**: Executes `scripts/bare-metal/deploy-vaultwarden.sh` to spin up the break-glass Vaultwarden container on the host OS of `kc02`.
4. **`make sync-azure-secrets`**: Executes `scripts/azure/sync-azure-secrets.sh` to imperatively inject Azure Service Principal credentials so the External Secrets Operator (ESO) can authenticate to Azure Key Vault.
5. **`make bootstrap-gitops`**: The final imperative step to install Argo CD into the cluster.

## Post-Bootstrap
Once `make bootstrap-gitops` completes, manual `kubectl apply` commands are prohibited. All further cluster modifications must be pushed as declarative YAML to the `manifests/` directory.

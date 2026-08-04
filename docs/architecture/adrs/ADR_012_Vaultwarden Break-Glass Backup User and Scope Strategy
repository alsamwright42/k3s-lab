### ARD 012: Vaultwarden Break-Glass Backup User and Scope Strategy

#### Status
Active

#### Context
To ensure the homelab can survive a total K3s cluster failure, Vaultwarden is deployed as a standalone container on the host OS (`kc02`), and a Kubernetes `CronJob` is being configured to automate backups of the vault into an encrypted KeePassXC (`.kdbx`) Break-Glass archive. 

Automating this backup requires the Bitwarden CLI (`bw`) to authenticate to the API and unlock the vault to export the raw JSON data. Using a personal administrator account's Master Password for this automation violates the principle of least privilege and unnecessarily exposes personal credentials. Furthermore, relying entirely on the Kubernetes cluster for password management risks a complete lockout during a hardware failure.

#### Decision
We will employ a "Service Account" pattern by creating a dedicated, limited-scope Backup User within Vaultwarden. This setup will be completed manually as a one-time pre-requisite due to the zero-knowledge encryption requirements of user generation.

1. **Dedicated Backup User**: A new Vaultwarden user will be created explicitly for the backup `CronJob`.
2. **Organization and Collections**: We will create a shared "Homelab" Organization and group shared credentials into specific Collections (e.g., "Infrastructure", "Network").
3. **Strict Scoping (Least Privilege)**: The Backup User will be invited to the Organization and granted **read-only** access exclusively to the shared Collections. It will have no access to personal individual vaults.
4. **Credential Injection**: The Backup User's specific API keys (`client_id` and `client_secret`) will be used to bypass interactive 2FA during session authentication. The Backup User's unique Master Password will be used to execute `bw unlock`. 
5. **Secret Management**: These credentials, alongside the `KDBX_PASSWORD` used to encrypt the resulting KeePass archive, will be stored securely in Azure Key Vault and injected dynamically at runtime via the External Secrets Operator (ESO).

#### Consequences & Next Steps
* **Security & Blast Radius**: The automation script has zero knowledge of your personal Master Password. If the backup `CronJob` or Kubernetes Secrets are ever compromised, the attacker can only read the explicitly shared Infrastructure passwords, leaving your personal vault secure.
* **Break-Glass Survival**: The resulting `.kdbx` file will be stored directly on the `kc02` host filesystem using a `hostPath` volume, ensuring that you can access your infrastructure passwords offline using KeePassXC even if the K3s control plane is destroyed.
* **Action Item**: Manually create the Backup User, Organization, and Collections in the Vaultwarden Web UI.
* **Action Item**: Generate the Backup User's API keys and store them, along with the Backup User's Master Password and the KeePass encryption password, into Azure Key Vault. 
* **Action Item**: Update the `ExternalSecret` manifest to sync these four values from Azure Key Vault into the cluster.

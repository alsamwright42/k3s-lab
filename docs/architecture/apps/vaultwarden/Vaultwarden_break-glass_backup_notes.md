# Vaultwarden Break-Glass Backup Notes

## 1. Overview & Architecture Strategy
As part of our **Hybrid Password Vault Architecture**, Vaultwarden serves as our primary manager for "Human & Infrastructure Secrets" (e.g., Edge routing passwords, Proxmox host logins, database credentials). 

To ensure **Break-Glass Survival** during a total cluster failure, a Kubernetes `CronJob` automates a nightly export of the Vaultwarden database.

**Key Architectural Decisions:**
*   **Format:** We utilize Bitwarden's native **Password-Protected Encrypted JSON** format rather than standard CSVs or `.kdbx` conversion scripts. This preserves TOTP seeds, custom fields, and folder structures, and perfectly imports into KeePassXC via its native Bitwarden JSON import feature.
*   **Execution:** The CronJob is pinned to the worker node (`kc02`) via a `nodeSelector`.
*   **Storage:** The encrypted JSON is written directly to the host OS NVMe drive at `/mnt/backups/vaultwarden/` and seamlessly pushed to Google Drive via statelessly configured `rclone`.

---

## 2. Backup Service User & Permissions

For security and isolation, the backup automation runs as a dedicated service account rather than a personal user account. 

### Creating the User
1. Create a dedicated user in your Vaultwarden instance (e.g., `backup-svc@samjam.dedyn.io`).
2. Log into the web vault as this user at least once to initialize their personal vault.
3. In your **primary** admin account, invite the backup user to your `Homelab` Organization.

### Required Permissions (The "CLI Quirk")
Bitwarden's strict Role-Based Access Control (RBAC) behaves differently in the CLI than in the Web UI. While the Web UI allows standard users with "Manage Collection" permissions to export items, **the `bw` CLI will fail with an authorization error unless the user holds Global Admin privileges.**
*   **Organization Role:** You must assign the backup user the **Admin** role at the Global Organization level.
*   **Collection Permissions:** Because the user is an Admin, you can ignore the specific Collection-level visibility toggles (they inherit full access).
*   **API Keys:** You must use the Backup User's **Personal API Key** (`client_id` and `client_secret`) located in their Account Settings -> Security -> Keys. *Do not use an Organization API Key, as it lacks the cryptographic Master Password required to decrypt the actual password payloads.*

---

## 3. Required Secrets (Azure Key Vault / ESO)
Ensure the following variables are populated in your secret store and synced to the `vaultwarden-backup-credentials` Kubernetes Secret:
*   `BW_CLIENTID`: The backup user's personal API Client ID.
*   `BW_CLIENTSECRET`: The backup user's personal API Client Secret.
*   `VAULT_PASSWORD`: The backup user's actual Master Password (required by the CLI for vault decryption).
*   `KDBX_PASSWORD`: The highly secure passphrase (e.g., 7-word passphrase) used to natively encrypt the output JSON files.
*   `VW_REMOTE_API_TOKEN`: The authentication token/credentials for `rclone` (Google Drive).

---

## 4. The Backup Script Logic
The `args` block in the CronJob uses `jq` to dynamically fetch every Organization the backup user belongs to. It loops through them and exports individual, clearly named files as `org_<OrgName>.json`.

---

## 5. Testing & Operations

Because Kubernetes Jobs are immutable, you cannot simply re-run a failed job. You must force-delete the old test job and spawn a new one from the CronJob template.

**Step 1: Deploy any manifest changes**
```bash
make deploy-vw-backup
```

**Step 2: Clean up previous test runs**
```bash
kubectl delete job manual-vault-backup-test --force
```

**Step 3: Trigger a manual job**
```bash
kubectl create job --from=cronjob/vaultwarden-breakglass-backup manual-vault-backup-test
```

**Step 4: Tail the live logs**
```bash
kubectl logs -l job-name=manual-vault-backup-test -f
```

---

## 6. Disaster Recovery (Break-Glass Restoration)

If the K3s cluster is completely offline and you need infrastructure passwords:

1. **Locate the Backup Files:**
   *   **Cloud:** Download `org_<Name>.json` from your Google Drive `HomeLab Operations/Backups/Vaultwarden/` folder.
   *   **Local:** Access the files directly from the internal drive of `kc02` at `/mnt/backups/vaultwarden/`.
2. **Import to KeePassXC:**
   *   Open the KeePassXC desktop application on your workstation.
   *   Click **Database** -> **Import** -> **Import from Bitwarden...**
   *   Select the `.json` file.
   *   When prompted, enter the `$KDBX_PASSWORD` used during the backup generation.
   *   Save the newly converted `.kdbx` file locally. You now have full, offline access to your entire infrastructure vault.

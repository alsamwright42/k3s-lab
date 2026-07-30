# ARD 006: K3s Node Bootstrap & Automation Strategy

## Status
Active

## Context
Automating the provisioning of bare-metal K3s nodes (KC01 and KC02) via Bash scripts requires handling remote SSH execution, privilege escalation, and dynamic cluster tokens without introducing configuration drift or silent failures.

## Summary of Findings

### 1. Network Bindings & DHCP
* **The Issue:** Assigning static IPs directly in `/etc/network/interfaces` caused the nodes to bypass OpenWrt's DHCP server, preventing `dnsmasq` from automatically registering their `.lan` hostnames across the subnet.
* **The Solution:** The OS was reverted to DHCP (`iface enp0s31f6 inet dhcp`), and static MAC reservations were set on the OpenWrt router to guarantee stable IPs while ensuring proper local DNS resolution.

### 2. Silent SSH/SCP Hangs
* **The Issue:** Non-interactive automation scripts hung indefinitely when transferring files to new nodes because `sudo` or host-key checks awaited unseen interactive prompts.
* **The Solution:** Automating `scp` and `ssh` requires the `-o BatchMode=yes` flag to enforce strict fail-fast behavior instead of hanging silently in the background.

### 3. Least-Privilege Remote Sudo
* **The Issue:** Granting a deployment user `NOPASSWD: ALL` is a severe security violation.
* **The Solution:** Sudo execution was scoped to a single script by creating a strict `/etc/sudoers.d/k3s-admin-safe` rule (with `0440` permissions). Configurations are staged securely in world-writable `/tmp/` before being promoted by the privileged script.

### 4. CRLF Corruption & Sed Truncation
* **The Issue:** Running inline `sed -i` to sanitize Windows line endings (`\r`) in scripts caused files to occasionally truncate to 0 bytes, breaking the deployment.
* **The Solution:** Inline `sed` was removed entirely. Cross-platform line endings are now strictly enforced via a repository `.gitattributes` file (`* text=auto eol=lf`).

### 5. Dynamic K3s Token Extraction
* **The Issue:** Committing the K3s cluster join token to a Git repository is a security risk, and the token does not exist until KC01 is fully deployed.
* **The Solution:** The orchestrator script deploys KC01 first, extracts the token dynamically from `/var/lib/rancher/k3s/server/node-token` via SSH, and injects it imperatively into KC02's config at runtime.
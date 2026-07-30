# ARD 008: Local Management Plane & Rancher Architecture

## Status
Active

## Context
Deploying Rancher as a local Docker container to manage the K3s cluster preserves hardware resources on the physical nodes, but introduces complex network and memory boundaries within Windows Subsystem for Linux (WSL2).

## Summary of Findings

### 1. WSL2 Docker Engine over Docker Desktop
* **The Issue:** Docker Desktop introduces resource bloat and complex virtual NAT adapters.
* **The Solution:** Docker Engine was installed natively inside the WSL2 Ubuntu distribution to ensure a cleaner, lower-overhead Linux environment.

### 2. WSL2 Memory Constraints (OOM Crash Loops)
* **The Issue:** Windows limits WSL2 memory by default. Rancher's embedded K3s cluster spiked memory during startup, triggering the Out-Of-Memory (OOM) killer and causing an infinite crash loop (`[FATAL] k3s exited with: <nil>`).
* **The Solution:** A `%USERPROFILE%\.wslconfig` file was manually created in Windows to explicitly allocate `memory=8GB`, giving Rancher enough overhead to stabilize.

### 3. WSL Mirrored Networking
* **The Issue:** WSL2 operates behind an isolated NAT network, preventing physical LAN nodes (KC01) from reaching the Rancher container running on the laptop [30, 31].
* **The Solution:** The `.wslconfig` file was updated with `networkingMode=mirrored`, bridging the WSL instance to share the laptop's physical LAN IP so remote nodes could connect inbound.

### 4. Rancher Server-URL Binding
* **The Issue:** Accessing Rancher initially via `https://localhost` hardcoded the cluster registration URL to `localhost`, causing the KC01 `cattle-cluster-agent` to loop back to itself and fail.
* **The Solution:** The `server-url` in Rancher Global Settings must be explicitly updated to the laptop's physical LAN IP (e.g., `192.168.1.X`) before generating the cluster import command.

### 5. Browser Extension Interference
* **The Issue:** Aggressive ad-blockers (like uBlock Origin Lite under Chrome's Manifest V3) silently block Rancher's internal WebSockets and dynamic API calls, freezing the UI.
* **The Solution:** `localhost` and internal IPs must have their filtering mode toggled off, or a standard extension like AdBlock Plus with a "Pause on this site" feature must be used for local development environments.

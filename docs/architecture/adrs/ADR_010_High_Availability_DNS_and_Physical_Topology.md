### ARD 010: High-Availability DNS and Physical Topology
#### Status
Active

#### Context
The builder-grade home wiring restricted the office to a single active Ethernet uplink, presenting a bottleneck risk if the K3s cluster and the Wi-Fi router were daisy-chained. Furthermore, the Telus NH20T gateway strictly locks down DNS settings, removing our ability to configure Split-Horizon DNS directly on the router for internal `*.samjam.dedyn.io` routing. 

#### Decisions
##### 1. The Physical Topology
To maximize bandwidth and isolate fault domains, the network physical layer was split at the basement patch panel:
*   The Wi-Fi router was moved to the Living Room and patched directly into the Telus NH20T's 10G/2.5G port (Port 5), ensuring the wireless network gets dedicated multi-gigabit backhaul. Heavy video streaming (TVs) is hardwired directly to the Wi-Fi router or modem to protect wireless airtime.
*   The K3s cluster (`kc01`, `kc02`) and the management laptop share a dedicated 5-port D-Link Gigabit switch in the office, patched into a standard 1 Gbps port on the Telus NH20T (Port 1). This creates a dedicated Layer 2 switching plane so inter-node K3s traffic and management SSH sessions bypass the Wi-Fi router entirely.

##### 2. Keepalived Virtual IP (VIP)
Because the Telus NH20T restricts custom DNS records, we must host our own primary DNS server to handle Split-Horizon routing for the cluster. To prevent a single node failure from taking down home internet resolution, we are deploying **Keepalived**.
*   Keepalived will float a Virtual IP (VIP) of `192.168.1.53` between `kc01` and `kc02`.
*   The Telus NH20T DHCP settings will be updated to hand out `192.168.1.53` as the primary DNS server for all home clients.

##### 3. Pi-hole on Standalone Docker
To provide the Split-Horizon DNS rewriting (pointing `*.samjam.dedyn.io` to the cluster) and network-wide ad-blocking, **Pi-hole** will be deployed on both `kc01` and `kc02`.
*   Applying the "Break-Glass Survival" exception previously established for Vaultwarden, Pi-hole will run as a standalone Docker container directly on the host OS rather than inside K3s. If the K3s control plane crashes, Pi-hole continues resolving DNS independently, ensuring the home network stays online and management tools remain accessible to recover the cluster.

#### Consequences
*   The K3s cluster achieves true High-Availability for its most critical network service (DNS).
*   The physical separation guarantees cluster inter-node bandwidth is completely un-bottlenecked by Wi-Fi traffic.
*   Adds a dependency on Keepalived and requires managing standalone Docker containers on both host nodes.

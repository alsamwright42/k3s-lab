# **01 Hardware and Network Topology 
================================================================================
                         PHYSICAL NETWORK TOPOLOGY
================================================================================

[ Telus NH20T Network Access Hub (Basement Media Panel) ]
  │
  ├─ Port 5 (10G/2.5G) ───(Living Room Wall Run)──> [ Wi-Fi Router ] ── (2.5 Gbps Link)
  │                                                   │
  │                                                   └─ Port 1 ──> Living Room TV
  │
  ├─ Port 1 (1000 Mbps) ──(Office Wall Run)───────> [ D-Link DGS-105 Switch (Office) ]
  │                                                   │  (1 Gbps Dedicated Layer 2)
  │                                                   ├─ Port 1: KC02 (192.168.1.51)
  │                                                   ├─ Port 2: KC01 (192.168.1.50)
  │                                                   ├─ Port 4: Laptop Dock
  │                                                   └─ Port 5: (Uplink to Wall)
  │
  └─ Port 2 (100 Mbps) ───(Bedroom Wall Run)──────> Bedroom TV

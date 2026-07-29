# **03 Service Manifest Ledger V3**

**Status:** Active / Verified Technical Baseline  
**Architecture Pattern:** Headless Minimal Debian Nodes with Local Static OS Interface Bindings

## **1\. Network Infrastructure & Routing Blueprint**

To eliminate dependencies on unstable or locked ISP router administration portals (Telus Network Access Hub), all cluster nodes utilize local client-side static IP bindings configured within /etc/network/interfaces. These static IP assignments are positioned below .64, sitting completely outside the gateway's active dynamic DHCP pool (192.168.1.64 – 192.168.1.253) to prevent address collisions without requiring router-side DHCP reservations.

| Parameter | Value / Specification   |
| :---- | :---- |
| **Subnet Mask** | 192.168.1.0/24 (255.255.255.0) |
| **Default Gateway** | 192.168.1.254 (Telus NAH) |
| **DNS Servers** | 1.1.1.1, 8.8.8.8 |
| **DHCP Safe Zone (Static)** | 192.168.1.2 – 192.168.1.63 |

## **2\. Cluster Node Inventory**

### **Node 01: Control Plane / Master (KC01)**

| Specification | Value   |
| :---- | :---- |
| **Hostname** | KC01 |
| **Assigned Static IP** | 192.168.1.50 |
| **Primary Network Interface** | enp0s31f6 |
| **Physical Hardware** | Dell OptiPlex 7040 Desktop |
| **CPU / RAM** | Intel Core i7-6700 (4C/8T) | 32 GB DDR4 |
| **Storage** | 512 GB NVMe SSD |
| **Operating System** | Debian Linux (Headless Minimal, sudo enabled) |

### **Node 02: Worker / Secondary Node (KC02)**

| Specification | Value   |
| :---- | :---- |
| **Hostname** | KC02 |
| **Assigned Static IP** | 192.168.1.51 |
| **Primary Network Interface** | enp0s31f6 |
| **Physical Hardware** | Dell OptiPlex 7040 Desktop |
| **CPU / RAM** | Intel Core i7-6700 (4C/8T) | 32 GB DDR4 |
| **Storage** | 512 GB NVMe SSD |
| **Operating System** | Debian Linux (Headless Minimal, sudo enabled) |

## **3\. Local OS Network Configuration Pattern**

The standard network configuration template applied to /etc/network/interfaces across cluster nodes:  
`source /etc/network/interfaces.d/*`

`# The loopback network interface`  
`auto lo`  
`iface lo inet loopback`

`# Primary Network Interface - Static OS Allocation`  
`allow-hotplug enp0s31f6`  
`iface enp0s31f6 inet dhcp`

`# Autoconfigured IPv6`  
`iface enp0s31f6 inet6 auto`  

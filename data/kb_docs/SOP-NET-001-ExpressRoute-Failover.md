# SOP-NET-001: GlobalTech ExpressRoute & Hybrid BGP Failover Runbook
**Document Owner:** NetOps Tier-3 | **Effective Date:** 2026-01-15 | **SLA Target:** 4 Minutes

## 1. Scope
Applies to all Mission-Critical (24x7 SLA) tenants hosted in Azure East US 2 and West Europe connected via ExpressRoute circuits `ER-PROD-01` (Primary) and `ER-DR-02` (Secondary).

## 2. Mandatory Failover Sequence
When primary ExpressRoute circuit `ER-PROD-01` experiences BGP session drop or >15% packet loss:
1. **DO NOT** hard-reset the customer edge (CE) router BGP peering immediately, as this flushes ARP tables across spoke VNets.
2. Verify secondary circuit `ER-DR-02` route preference weight is set to `200` in **Azure Route Server (`ars-globaltech-prod`)**.
3. Execute the automated traffic shift utility on the jump host:
   `/opt/netops/failover_er.sh --circuit ER-DR-02 --mode=graceful --verify-bgp`
4. Confirm East US 2 AKS egress traffic routes through Azure Firewall (`afw-hub-eastus2`) without SNAT port exhaustion.
5. Escalation Contact: `netops-oncall@globaltech.internal` (Bridge PIN: `88421`).

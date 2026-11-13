# SOP-SEC-014: Production AKS Break-Glass Access & Pod Isolation Policy
**Document Owner:** InfoSec Governance | **Compliance Standard:** SOC2 / ISO-27001

## 1. Emergency Cluster-Admin Access
Direct `kubectl` access with `cluster-admin` privileges on production AKS clusters (`aks-contoso-prod`, `aks-globaltech-core`) is disabled by default via Entra ID RBAC.
- To request emergency break-glass elevation:
  1. Log a ServiceNow incident tagged **`SEC-BREAKGLASS`**.
  2. Obtain dual-custody approval from CyberArk Vault (`Vault-09`).
  3. Temporary kubeconfig tokens automatically expire after **45 minutes** and trigger a mandatory **P2 Security Audit Alert** in Sentinel.

## 2. Compromised Pod Quarantine Procedure
If Defender for Containers flags suspicious outbound SSH or crypto-mining activity:
- Apply the quarantine NetworkPolicy immediately rather than deleting the pod (to preserve memory forensics):
  `kubectl label pod <POD_NAME> security.globaltech.io/quarantine=true -n production`

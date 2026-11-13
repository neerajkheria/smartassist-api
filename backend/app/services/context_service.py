from typing import Dict, Optional

# Simulated enterprise tenant & inventory database
CUSTOMER_PROFILES: Dict[str, dict] = {
    "CUST-101": {
        "company_name": "Contoso Logistics",
        "tier": "Mission-Critical (24x7 SLA)",
        "cloud_provider": "Azure",
        "primary_region": "East US 2",
        "cluster_type": "AKS v1.29",
        "network_topology": "Hub-Spoke with Azure Firewall"
    },
    "CUST-102": {
        "company_name": "Fabrikam Retail",
        "tier": "Standard Business Hours",
        "cloud_provider": "Hybrid",
        "primary_region": "West Europe",
        "cluster_type": "Docker Compose on Ubuntu 22.04",
        "network_topology": "Site-to-Site IPsec VPN"
    }
}

class ContextService:
    @staticmethod
    def get_customer_context(customer_id: str) -> Optional[dict]:
        return CUSTOMER_PROFILES.get(customer_id)

    @staticmethod
    def inject_context(prompt: str, customer_id: str) -> str:
        profile = ContextService.get_customer_context(customer_id)
        if not profile:
            return prompt

        context_block = (
            f"CUSTOMER CONTEXT:\n"
            f"- Company: {profile['company_name']}\n"
            f"- Support Tier: {profile['tier']}\n"
            f"- Environment: {profile['cloud_provider']} ({profile['primary_region']})\n"
            f"- Stack: {profile['cluster_type']}\n"
            f"- Networking: {profile['network_topology']}\n\n"
        )
        return f"{context_block}CUSTOMER QUESTION:\n{prompt}"

context_service = ContextService()

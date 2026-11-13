import requests
import json

BASE_URL = "http://localhost:8000/api/v1/support"

# 1. Normal query
short_query = "How do I reset an Azure SQL Database admin password?"
res1 = requests.post(f"{BASE_URL}/query", json={"query": short_query, "customer_id": "ORG-001"})
print("[1] Normal Query Response:", res1.status_code)
if res1.status_code == 200:
    print("    Usage:", res1.json().get("tokens"))

# 2. Oversized query
long_query = "Analyze this configuration snippet: " + ("ipsec-policy ikev2-aes256-sha256-group14 " * 120)
res2 = requests.post(f"{BASE_URL}/query", json={"query": long_query, "customer_id": "ORG-002"})
print("\n[2] Oversized Query Response:", res2.status_code)
print("    Rejection Reason:", res2.json().get("detail"))

# 3. Report
res3 = requests.get(f"{BASE_URL}/tokens/metrics")
print("\n[3] Current Metrics Report:")
print(json.dumps(res3.json(), indent=2))
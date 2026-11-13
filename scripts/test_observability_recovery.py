import requests
import json

BASE = "http://localhost:8000"

print("=== [Labs 16-18] Observability, Tracing & Recovery Audit ===\n")

# 1. Verify Correlation ID & Latency Telemetry Headers
res = requests.post(
    f"{BASE}/api/v1/support/query",
    headers={"X-Correlation-ID": "trace-neeraj-001"},
    json={"query": "How do I check AKS pod memory limits?"}
)
print(f"[1] Telemetry Headers Check -> HTTP {res.status_code}")
print(f"    X-Correlation-ID:   {res.headers.get('X-Correlation-ID')}")
print(f"    X-Process-Time-Ms:  {res.headers.get('X-Process-Time-Ms')} ms")
print(f"    Model Latency:      {res.json().get('parameters', {}).get('llm_latency_ms')} ms\n")

# 2. Verify Health & Circuit Breaker State
health = requests.get(f"{BASE}/healthz").json()
print("[2] Circuit Breaker Health Check:")
print(json.dumps(health, indent=2))


import re
import json
import random
from pathlib import Path

DATA_DIR = Path.home() / "smartassist-ai" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Raw enterprise ticket history
raw_tickets = [
    {"text": "John Doe (j.doe@company.com) reported ExpressRoute circuit ER-109 in EastUS down after maintenance.", "cat": "Networking", "prio": "P1-Critical"},
    {"text": "SSH brute force detected from IP 198.51.100.24 targeting bastion host. Admin Alice alerted.", "cat": "Security", "prio": "P2-High"},
    {"text": "AKS cluster worker nodes stuck in NotReady status after image upgrade. Contact bob@tech.com.", "cat": "Cloud Infrastructure", "prio": "P1-Critical"},
    {"text": "Customer wants to know how to install Node.js 20 on App Service deployment slot.", "cat": "Application", "prio": "P4-Low"},
    {"text": "TLS certificate expired for api.globaltech.internal at 10.0.4.15. HTTPS calls failing.", "cat": "Security", "prio": "P2-High"},
    {"text": "Packet loss observed across Site-to-Site VPN gateway vpn-gw-01 to Frankfurt office.", "cat": "Networking", "prio": "P2-High"},
    {"text": "Storage account blob replication delay between Central US and East US.", "cat": "Cloud Infrastructure", "prio": "P3-Medium"},
    {"text": "Database deadlocks reported on order_processing table during flash sale.", "cat": "Application", "prio": "P2-High"},
    {"text": "Can we configure auto-scaling rules for App Service based on CPU threshold 75%?", "cat": "Cloud Infrastructure", "prio": "P4-Low"},
    {"text": "DDoS alert triggered on public IP 203.0.113.88. WAF blocking anomalous rate.", "cat": "Security", "prio": "P1-Critical"},
    {"text": "User cannot mount Azure Files NFS share on Ubuntu 22.04 client VM.", "cat": "Cloud Infrastructure", "prio": "P3-Medium"},
    {"text": "DNS resolution failing for internal domain corp.internal from VNet-Spoke-02.", "cat": "Networking", "prio": "P2-High"}
]

def sanitize_pii(text: str) -> str:
    # Redact email addresses
    text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '<REDACTED_EMAIL>', text)
    # Redact public IPv4 addresses
    text = re.sub(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', '<REDACTED_IP>', text)
    # Redact common names
    for name in ["John Doe", "Alice", "Bob"]:
        text = text.replace(name, "<REDACTED_USER>")
    return text

SYSTEM_PROMPT = "You are an automated IT ticket classifier for GlobalTech Solutions. Return JSON with category, priority, and reasoning."

formatted_records = []

for item in raw_tickets:
    clean_text = sanitize_pii(item["text"])
    expected_output = json.dumps({
        "category": item["cat"],
        "priority": item["prio"],
        "reasoning": f"Classified based on {item['cat'].lower()} impact."
    })
    
    formatted_records.append({
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Ticket:\n{clean_text}"},
            {"role": "assistant", "content": expected_output}
        ]
    })

# Shuffle and split into 80% train, 20% validation
random.seed(42) #make shuffle reproducible, ie same dataset/output for n number of execution
random.shuffle(formatted_records)

split_index = int(len(formatted_records) * 0.8)
train_set = formatted_records[:split_index]
val_set = formatted_records[split_index:]

train_file = DATA_DIR / "tickets_train.jsonl"
val_file = DATA_DIR / "tickets_val.jsonl"

with open(train_file, "w") as f:
    for rec in train_set:
        f.write(json.dumps(rec) + "\n")

with open(val_file, "w") as f:
    for rec in val_set:
        f.write(json.dumps(rec) + "\n")

print(f"Dataset generated successfully:")
print(f"- Training Examples: {len(train_set)} -> {train_file}")
print(f"- Validation Examples: {len(val_set)} -> {val_file}")

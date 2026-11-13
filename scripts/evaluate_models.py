import os
import json
import time
from pathlib import Path
from openai import AzureOpenAI
from tabulate import tabulate
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/smartassist-ai/.env"))

client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION")
)
model = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1-mini)

EVAL_FILE = Path.home() / "smartassist-ai" / "data" / "eval_dataset.json"
with open(EVAL_FILE, "r") as f:
    eval_cases = json.load(f)

# Baseline generic system prompt
BASELINE_SYSTEM = "Classify this IT support ticket. Return the category and priority."

# Customized enterprise system prompt
CUSTOM_SYSTEM = """You are an automated IT service management classifier for GlobalTech Solutions.
Classify incoming tickets into:
- Category: [Networking, Security, Cloud Infrastructure, Application]
- Priority: [P1-Critical, P2-High, P3-Medium, P4-Low]

Return ONLY valid JSON:
{"category": "<Category>", "priority": "<Priority>"}"""

print("=================================================================")
print(f"  SmartAssist AI Model Evaluation Suite (Model: {model})")
print("=================================================================\n")

results = []
baseline_cat_correct = 0
custom_cat_correct = 0
total = len(eval_cases)

for case in eval_cases:
    ticket_id = case["id"]
    text = case["ticket"]
    expected_cat = case["expected_category"]
    expected_prio = case["expected_priority"]

    # 1. Test Baseline Model
    try:
        r_base = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": BASELINE_SYSTEM},
                {"role": "user", "content": text}
            ],
            max_completion_tokens=150
        )
        base_out = r_base.choices[0].message.content.strip().replace("\n", " ")
        base_cat_match = expected_cat.lower() in base_out.lower()
    except Exception as e:
        base_out = f"Error: {e}"
        base_cat_match = False

    # 2. Test Customized Schema Prompt
    try:
        r_cust = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": CUSTOM_SYSTEM},
                {"role": "user", "content": f"Ticket:\n{text}"}
            ],
            max_completion_tokens=150
        )
        cust_out = r_cust.choices[0].message.content.strip()
        
        # Clean backticks
        if cust_out.startswith("```"):
            cust_out = cust_out.split("```")[1].replace("json", "")
        
        parsed = json.loads(cust_out.strip())
        cust_cat = parsed.get("category", "")
        cust_prio = parsed.get("priority", "")
        cust_cat_match = (cust_cat.lower() == expected_cat.lower())
    except Exception:
        cust_cat = "Parse Error"
        cust_prio = "N/A"
        cust_cat_match = False

    if base_cat_match:
        baseline_cat_correct += 1
    if cust_cat_match:
        custom_cat_correct += 1

    results.append([
        ticket_id,
        expected_cat,
        "PASS" if base_cat_match else "FAIL",
        f"{cust_cat} ({cust_prio})",
        "PASS" if cust_cat_match else "FAIL"
    ])

# Print Evaluation Results Table
headers = ["Test ID", "Target Category", "Baseline Cat", "Custom Prediction", "Custom Cat"]
print(tabulate(results, headers=headers, tablefmt="grid"))

print("\n--- Summary Performance Metrics ---")
print(f"Total Test Cases: {total}")
print(f"Baseline Categorization Accuracy: {(baseline_cat_correct / total) * 100:.1f}%")
print(f"Customized Schema Accuracy:      {(custom_cat_correct / total) * 100:.1f}%")

# Save evaluation report artifact for the capstone deliverable
report_path = Path.home() / "smartassist-ai" / "data" / "model_evaluation_report.md"
with open(report_path, "w") as f:
    f.write("# Model Evaluation Report: Baseline vs Customized SmartAssist AI\n\n")
    f.write(f"- **Evaluated Model:** {model}\n")
    f.write(f"- **Total Test Scenarios:** {total}\n")
    f.write(f"- **Baseline Accuracy:** {(baseline_cat_correct / total) * 100:.1f}%\n")
    f.write(f"- **Customized System Accuracy:** {(custom_cat_correct / total) * 100:.1f}%\n")
    f.write("\n## Detailed Case Breakdown\n\n")
    f.write(tabulate(results, headers=headers, tablefmt="pipe"))

print(f"\nArtifact generated: {report_path}")

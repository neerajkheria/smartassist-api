cat << 'EOF' > ~/smartassist-ai/scripts/check_job_status.py
import os
import sys
from pathlib import Path
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/smartassist-ai/.env"))

client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION")
)

job_file = Path.home() / "smartassist-ai" / "data" / "last_job.txt"
if not job_file.exists():
    print("No active job ID found. Run submit_finetuning.py first.")
    sys.exit(1)

with open(job_file, "r") as f:
    job_id = f.read().strip()

print(f"Checking status for Job: {job_id}")
job = client.fine_tuning.jobs.retrieve(job_id)

print(f"Status: {job.status}")
print(f"Model: {job.model}")
if job.fine_tuned_model:
    print(f"Resulting Model: {job.fine_tuned_model}")
if hasattr(job, "trained_tokens"):
    print(f"Trained Tokens: {job.trained_tokens}")
EOF
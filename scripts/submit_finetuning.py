import os
import sys
import time
from pathlib import Path
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/smartassist-ai/.env"))

client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION")
)

TRAIN_FILE_PATH = Path.home() / "smartassist-ai" / "data" / "tickets_train.jsonl"
VAL_FILE_PATH = Path.home() / "smartassist-ai" / "data" / "tickets_val.jsonl"
BASE_MODEL = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1-mini")
LEARNER_ID = os.getenv("LEARNER_ID", "Neeraj")

print(f"=== [SmartAssist AI] Submitting Fine-Tuning Job for {LEARNER_ID} ===")

# 1. Upload Training File
print(f"[1/3] Uploading training dataset: {TRAIN_FILE_PATH.name}...")
with open(TRAIN_FILE_PATH, "rb") as f:
    train_file = client.files.create(file=f, purpose="fine-tune")
print(f" -> Training File ID: {train_file.id}")

# 2. Upload Validation File
print(f"[2/3] Uploading validation dataset: {VAL_FILE_PATH.name}...")
with open(VAL_FILE_PATH, "rb") as f:
    val_file = client.files.create(file=f, purpose="fine-tune")
print(f" -> Validation File ID: {val_file.id}")

# Wait briefly for cloud file processing
print("Waiting for file status to be processed...")
time.sleep(5)

# 3. Create Fine-Tuning Job
custom_suffix = f"smartassist-{LEARNER_ID}"
print(f"[3/3] Initiating fine-tuning job (Base: {BASE_MODEL}, Suffix: {custom_suffix})...")

try:
    job = client.fine_tuning.jobs.create(
        training_file=train_file.id,
        validation_file=val_file.id,
        model=BASE_MODEL,
        suffix=custom_suffix,
        hyperparameters={
            "n_epochs": 2
        }
    )
    print("\n✅ Fine-tuning job successfully submitted!")
    print(f"Job ID: {job.id}")
    print(f"Status: {job.status}")
    print(f"Created At: {job.created_at}")

    # Save Job Metadata locally
    with open(Path.home() / "smartassist-ai" / "data" / "last_job.txt", "w") as f:
        f.write(job.id)

except Exception as e:
    print(f"\n⚠️ Note on submission: {str(e)}")
    print("If your subscription/region has dedicated fine-tuning quota disabled, proceed to Lab 12 using the evaluation benchmark harness.")

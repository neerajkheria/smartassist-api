import os
from pathlib import Path
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import FilePurpose

load_dotenv(os.path.expanduser("~/smartassist-ai/.env"))

project_endpoint = os.environ["FOUNDRY_PROJECT_ENDPOINT"]

agents_client = AgentsClient(
    endpoint=project_endpoint,
    credential=DefaultAzureCredential()
)

KB_DIR = Path.home() / "smartassist-ai" / "data" / "kb_docs"
doc_files = sorted(KB_DIR.glob("*.md"))

print(f"=== [Lab 19] Uploading {len(doc_files)} Knowledge Base Docs to {project_endpoint} ===")

uploaded_file_ids = []
for doc_path in doc_files:
    print(f" -> Uploading {doc_path.name}...")
    uploaded = agents_client.files.upload_and_poll(
        file_path=str(doc_path),
        purpose=FilePurpose.AGENTS
    )
    print(f"    Uploaded File ID: {uploaded.id}")
    uploaded_file_ids.append(uploaded.id)

print("\nCreating Foundry Vector Store & Indexing Chunks...")
vector_store = agents_client.vector_stores.create_and_poll(
    file_ids=uploaded_file_ids,
    name="smartassist-enterprise-kb"
)

print(f"\n✅ Vector Store Ready!")
print(f"   Vector Store ID: {vector_store.id}")
print(f"   Status:          {vector_store.status}")
print(f"   File Counts:     {vector_store.file_counts}")

env_path = Path.home() / "smartassist-ai" / ".env"
with open(env_path, "a") as f:
    f.write(f'\nFOUNDRY_VECTOR_STORE_ID="{vector_store.id}"\n')

print(f"Saved FOUNDRY_VECTOR_STORE_ID to {env_path}")

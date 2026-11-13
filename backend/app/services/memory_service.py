import os
from typing import Dict, List, Optional
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import ResourceNotFoundError
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    MemoryStoreDefaultDefinition,
    MemoryStoreDefaultOptions,
    MemorySearchOptions,
    MemorySearchPreviewTool,
)
from app.core.telemetry import telemetry_logger

load_dotenv(os.path.expanduser("~/smartassist-ai/.env"))

class FoundryMemoryService:
    """
    Native Microsoft Foundry Memory Service (`project_client.beta.memory_stores`):
    - Short-Term Memory (STM): Binds active session_id -> Foundry conversation/thread ID
      and extracts condensed chat summaries (`chat_summary_enabled=True`).
    - Long-Term Memory (LTM): Extracts and persists user/tenant profile facts
      (`user_profile_enabled=True`) scoped by `customer_id` across sessions.
    """
    def __init__(self):
        self.endpoint = os.getenv("FOUNDRY_PROJECT_ENDPOINT") or os.getenv("AZURE_AI_PROJECT_ENDPOINT")
        self.store_name = os.getenv("FOUNDRY_MEMORY_STORE_NAME", "smartassist-memory-store")
        self.chat_model = os.getenv("MEMORY_STORE_CHAT_MODEL", os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1-mini"))
        self.embedding_model = os.getenv("MEMORY_STORE_EMBEDDING_MODEL", "text-embedding-3-small")

        self.session_threads: Dict[str, str] = {}  # STM: session_id -> thread/conversation id
        self.last_update_ids: Dict[str, str] = {}  # Tracks async memory extraction jobs per scope

        self.client: Optional[AIProjectClient] = None
        if self.endpoint:
            self.client = AIProjectClient(
                endpoint=self.endpoint,
                credential=DefaultAzureCredential()
            )
            self._ensure_memory_store()

    def _ensure_memory_store(self):
        """Creates the Foundry Memory Store if it does not already exist."""
        try:
            store = self.client.beta.memory_stores.get(name=self.store_name)
            telemetry_logger.info(f"Connected to existing Foundry Memory Store: {store.name}")
        except ResourceNotFoundError:
            options = MemoryStoreDefaultOptions(
                chat_summary_enabled=True,
                user_profile_enabled=True,
                user_profile_details=(
                    "Extract enterprise IT environment details: AKS cluster names, Azure regions, "
                    "ExpressRoute circuits, SLA tiers, and troubleshooting preferences. "
                    "Do not store passwords, tokens, or personal financial details."
                )
            )
            definition = MemoryStoreDefaultDefinition(
                chat_model=self.chat_model,
                embedding_model=self.embedding_model,
                options=options
            )
            store = self.client.beta.memory_stores.create(
                name=self.store_name,
                description="SmartAssist AI cross-session tenant and incident memory store",
                definition=definition
            )
            telemetry_logger.info(f"Created new Foundry Memory Store: {store.name}")

    # --- Short-Term Memory (Session / Thread Binding) ---
    def get_thread_id(self, session_id: str) -> Optional[str]:
        return self.session_threads.get(session_id)

    def bind_thread_id(self, session_id: str, thread_id: str):
        self.session_threads[session_id] = thread_id
        telemetry_logger.info(f"STM: Bound session '{session_id}' -> thread '{thread_id}'")

    def clear_session(self, session_id: str):
        self.session_threads.pop(session_id, None)

    # --- Foundry Agent Tool Attachment ---
    def get_memory_search_tool(self, scope: str, update_delay: int = 5) -> MemorySearchPreviewTool:
        """Returns a MemorySearchPreviewTool configured for a specific tenant/user scope."""
        return MemorySearchPreviewTool(
            memory_store_name=self.store_name,
            scope=scope,
            update_delay=update_delay
        )

    # --- Direct Memory Store Operations (Update, Search, Scope Reset) ---
    def record_turn_memories(self, scope: str, user_message: str, assistant_message: str):
        """Submits conversation turns to Foundry Memory Store for async fact & summary extraction."""
        if not self.client:
            return
        items = [
            {"role": "user", "content": user_message, "type": "message"},
            {"role": "assistant", "content": assistant_message, "type": "message"}
        ]
        prev_id = self.last_update_ids.get(scope)
        poller = self.client.beta.memory_stores.begin_update_memories(
            name=self.store_name,
            scope=scope,
            items=items,
            previous_update_id=prev_id,
            update_delay=0
        )
        result = poller.result()
        self.last_update_ids[scope] = poller.details.get("update_id", prev_id)
        telemetry_logger.info(f"Foundry LTM updated for scope '{scope}': {len(getattr(result, 'memory_operations', []))} ops")

    def search_memories(self, scope: str, query: str, max_memories: int = 5) -> List[str]:
        """Queries Foundry Memory Store semantically for relevant user profile & chat summary memories."""
        if not self.client:
            return []
        query_item = {"role": "user", "content": query, "type": "message"}
        response = self.client.beta.memory_stores.search_memories(
            name=self.store_name,
            scope=scope,
            items=[query_item],
            options=MemorySearchOptions(max_memories=max_memories)
        )
        return [mem.memory_item.content for mem in getattr(response, "memories", [])]

    def format_ltm_context(self, scope: str, query: str = "What is the tenant infrastructure and SLA profile?") -> str:
        memories = self.search_memories(scope=scope, query=query)
        if not memories:
            return "No prior Foundry long-term memories found for this tenant."
        formatted = "\n".join([f"- {m}" for m in memories])
        return f"FOUNDRY LONG-TERM MEMORY (Scope: {scope}):\n{formatted}"

    def delete_scope_memories(self, scope: str):
        if self.client:
            self.client.beta.memory_stores.delete_scope(name=self.store_name, scope=scope)
            self.last_update_ids.pop(scope, None)

memory_service = FoundryMemoryService()

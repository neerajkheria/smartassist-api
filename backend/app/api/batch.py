import uuid
import time
from typing import List, Dict
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from app.services.llm_service import llm_service
from app.prompts.classifier_prompts import FEW_SHOT_CLASSIFIER_SYSTEM_PROMPT, build_classification_prompt

router = APIRouter(prefix="/api/v1/batch", tags=["Batch Inference"])

# In-memory batch store (suitable for single-node; Azure Redis/Table Storage in scaled enterprise tiers)
BATCH_JOBS: Dict[str, dict] = {}

class BatchTicketRequest(BaseModel):
    tickets: List[str] = Field(..., min_items=1, max_items=20, description="Array of incident descriptions")

def process_batch_tickets(job_id: str, tickets: List[str]):
    BATCH_JOBS[job_id]["status"] = "processing"
    processed_results = []
    
    for idx, text in enumerate(tickets):
        prompt = build_classification_prompt(text)
        result = llm_service.generate_chat_response(
            prompt=prompt,
            system_instruction=FEW_SHOT_CLASSIFIER_SYSTEM_PROMPT,
            max_tokens=250
        )
        processed_results.append({
            "ticket_index": idx,
            "input": text,
            "response": result.get("response") if result.get("success") else result.get("error"),
            "success": result.get("success")
        })
        time.sleep(0.5)  # Throttle to prevent TPM starvation across shared classroom deployment

    BATCH_JOBS[job_id]["status"] = "completed"
    BATCH_JOBS[job_id]["results"] = processed_results
    BATCH_JOBS[job_id]["completed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

@router.post("/process")
async def create_batch_inference_job(payload: BatchTicketRequest, background_tasks: BackgroundTasks):
    job_id = f"batch-{uuid.uuid4().hex[:8]}"
    BATCH_JOBS[job_id] = {
        "job_id": job_id,
        "total_items": len(payload.tickets),
        "status": "queued",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "results": []
    }
    background_tasks.add_task(process_batch_tickets, job_id, payload.tickets)
    return {"job_id": job_id, "status": "queued", "check_status_url": f"/api/v1/batch/{job_id}"}

@router.get("/{job_id}")
async def get_batch_job_status(job_id: str):
    job = BATCH_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Batch Job ID not found.")
    return job

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from app.services.llm_service import llm_service
from app.services.token_tracker import token_tracker
from app.prompts.support_prompts import BASE_SUPPORT_SYSTEM_PROMPT, build_support_prompt
from app.services.context_service import context_service

router = APIRouter(prefix="/api/v1/support", tags=["Support AI"])

class SupportQueryRequest(BaseModel):
    query: str = Field(..., min_length=5, max_length=4000)
    customer_id: Optional[str] = "CUST-DEFAULT"
    max_tokens: Optional[int] = Field(None, ge=50, le=1500)

@router.post("/query")
async def handle_support_query(request: SupportQueryRequest):
    # Pre-execution token size gate
    if not token_tracker.validate_request_size(request.query):
        estimated = token_tracker.count_tokens(request.query)
        raise HTTPException(
            status_code=400,
            detail=f"Prompt rejected: Token count ({estimated}) exceeds maximum allowed input limit ({token_tracker.MAX_INPUT_TOKENS_PER_REQUEST})."
        )

    result = llm_service.generate_chat_response(
        prompt=request.query,
        max_tokens=request.max_tokens
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=result.get("status_code", 500),
            detail=result.get("error")
        )
    
    # Record token telemetry
    tokens = result["tokens"]
    token_tracker.record_usage(
        customer_id=request.customer_id,
        prompt_tokens=tokens["prompt_tokens"],
        completion_tokens=tokens["completion_tokens"]
    )
        
    return result

@router.get("/tokens/metrics")
async def get_token_metrics():
    return token_tracker.generate_report()

@router.post("/query/structured")
async def handle_structured_query(request: SupportQueryRequest):
    # Lab 7: Enforce structured system instructions and templates
    formatted_prompt = build_support_prompt(request.query)
    
    result = llm_service.generate_chat_response(
        prompt=formatted_prompt,
        system_instruction=BASE_SUPPORT_SYSTEM_PROMPT,
        max_tokens=request.max_tokens
    )
    
    if not result["success"]:
        raise HTTPException(status_code=result.get("status_code", 500), detail=result.get("error"))
        
    return result

@router.post("/query/contextual")
async def handle_contextual_query(request: SupportQueryRequest):
    # Lab 8: Inject tenant profile into prompt
    contextual_prompt = context_service.inject_context(
        prompt=request.query, 
        customer_id=request.customer_id
    )

    result = llm_service.generate_chat_response(
        prompt=contextual_prompt,
        system_instruction=BASE_SUPPORT_SYSTEM_PROMPT,
        max_tokens=request.max_tokens
    )

    if not result["success"]:
        raise HTTPException(status_code=result.get("status_code", 500), detail=result.get("error"))

    return {
        "customer_id": request.customer_id,
        "context_applied": context_service.get_customer_context(request.customer_id) is not None,
        "response": result["response"],
        "tokens": result["tokens"]
    }
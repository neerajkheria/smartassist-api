import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.services.llm_service import llm_service
from app.prompts.classifier_prompts import FEW_SHOT_CLASSIFIER_SYSTEM_PROMPT, build_classification_prompt

router = APIRouter(prefix="/api/v1/tickets", tags=["Ticket Operations"])

class TicketClassifyRequest(BaseModel):
    ticket_text: str = Field(..., min_length=10, max_length=2000)

class TicketClassifyResponse(BaseModel):
    category: str
    priority: str
    confidence_score: float
    reasoning: str
    raw_prompt_tokens: int

@router.post("/classify", response_model=TicketClassifyResponse)
async def classify_ticket(request: TicketClassifyRequest):
    prompt = build_classification_prompt(request.ticket_text)
    
    result = llm_service.generate_chat_response(
        prompt=prompt,
        system_instruction=FEW_SHOT_CLASSIFIER_SYSTEM_PROMPT,
        max_tokens=250
    )

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error"))

    try:
        content = result["response"].strip()
        # Clean any accidental markdown backticks
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:] #Removes leading json labels if it is present in response
        data = json.loads(content.strip())
        data["raw_prompt_tokens"] = result["tokens"]["total_tokens"]
        return data
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to parse classification JSON: {str(e)} | Output: {result.get('response')}"
        )

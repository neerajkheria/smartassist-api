import socket
from fastapi import APIRouter
from app.core.config import settings
from app.services.llm_service import llm_service

router = APIRouter(tags=["Health & Diagnostics"])

@router.get("/healthz")
async def liveness_check():
    return {
        "status": "healthy",
        "learner_id": settings.LEARNER_ID,
        "host": socket.gethostname(),
        "circuit_breaker_state": llm_service.circuit_breaker.state,
        "consecutive_failures": llm_service.circuit_breaker.failure_count
    }

@router.get("/readyz")
async def readiness_check():
    return {
        "status": "ready",
        "model_deployment": llm_service.deployment,
        "circuit_breaker_state": llm_service.circuit_breaker.state
    }

from dotenv import load_dotenv; import os; load_dotenv(os.path.expanduser("~/smartassist-ai/.env"))
import os
import time
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.core.config import settings
from app.core.telemetry import telemetry_logger, correlation_id_ctx
from app.api.health import router as health_router
from app.api.chat import router as chat_router
from app.api.classify import router as classify_router
from app.api.batch import router as batch_router

# Initialize Azure Monitor OpenTelemetry exporter if connection string is set
conn_str = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "")
if conn_str and "InstrumentationKey=" in conn_str:
    configure_azure_monitor(connection_string=conn_str)
    telemetry_logger.info("Azure Monitor OpenTelemetry initialized.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    req_id = request.headers.get("X-Correlation-ID", f"req-{uuid.uuid4().hex[:10]}")
    correlation_id_ctx.set(req_id)
    start_time = time.perf_counter()

    response = await call_next(request)

    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
    response.headers["X-Correlation-ID"] = req_id
    response.headers["X-Process-Time-Ms"] = str(latency_ms)

    telemetry_logger.info(
        f"HTTP {request.method} {request.url.path} completed",
        extra={
            "custom_dimensions": {
                "http_method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "latency_ms": latency_ms
            }
        }
    )
    return response

app.include_router(health_router)
app.include_router(chat_router)
app.include_router(classify_router)
app.include_router(batch_router)

# Instrument FastAPI spans automatically
FastAPIInstrumentor.instrument_app(app)

@app.get("/")
async def root():
    return {
        "service": settings.PROJECT_NAME,
        "learner": settings.LEARNER_ID,
        "telemetry": "azure-monitor-enabled"
    }
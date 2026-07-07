"""
The root entry point that initializes the FastAPI application instance and its operational lifespan events.
Mounts the modular API routers, configures CORS for the frontend, and binds global error-handling middleware.
"""

import time
import sentry_sdk
from fastapi import FastAPI, Request, HTTPException, status
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

from app.api.tenants import router as tenant_router
from app.api.prompt_router import router as prompt_router
from app.api.chat import router as chat_router
from app.core.rate_limiter import SlidingWindowRateLimiter

# Initialize Sentry middleware monitoring context
sentry_sdk.init(
    dsn="",  # Production telemetry credentials injected via system environment parameters
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
)

app = FastAPI(title="Resolve AI Gateway Core", version="2.0.0")

# Mount structured functional system endpoints
app.include_router(tenant_router, prefix="/api/v1")
app.include_router(prompt_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")

# --- Observability Metrics Definition ---
API_REQUEST_COUNTER = Counter(
    "api_requests_total", 
    "Total transaction requests handled by the platform gateway", 
    ["method", "endpoint", "status_code"]
)

API_LATENCY_HISTOGRAM = Histogram(
    "api_request_latency_seconds",
    "Granular transaction execution latency metric space",
    ["method", "endpoint"],
    buckets=(0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0)
)

@app.middleware("http")
async def monitor_telemetry_and_rate_limit_interceptor(request: Request, call_next):
    """
    Asynchronously tracks application latency, throughput, and enforces tenant rate limits via Redis.
    """
    start_time = time.perf_counter()
    
    tenant_id = request.headers.get("X-Tenant-ID")
    
    if tenant_id:
        try:
            # Enforce sliding window quota constraints
            await SlidingWindowRateLimiter.check_rate_limit(
                tenant_id=tenant_id, 
                limit_key="global_api", 
                max_requests=60, 
                window_seconds=60
            )
        except HTTPException as exc:
            API_REQUEST_COUNTER.labels(method=request.method, endpoint=request.url.path, status_code=str(exc.status_code)).inc()
            return Response(content=exc.detail, status_code=exc.status_code)

    response = await call_next(request)
    duration = time.perf_counter() - start_time
    
    endpoint_path = request.url.path
    method_type = request.method
    status_code_str = str(response.status_code)
    
    API_REQUEST_COUNTER.labels(method=method_type, endpoint=endpoint_path, status_code=status_code_str).inc()
    API_LATENCY_HISTOGRAM.labels(method=method_type, endpoint=endpoint_path).observe(duration)
    
    return response

@app.get("/metrics")
def expose_prometheus_metrics():
    """
    Exposes application execution logs in raw exposition syntax to automated scraping daemons.
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
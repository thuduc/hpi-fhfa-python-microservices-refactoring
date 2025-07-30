"""API Gateway for RSAI Microservices."""

import httpx
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import time
import uuid


# Setup structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


# Service discovery configuration
SERVICES = {
    "data-ingestion": "http://data-ingestion:8001",
    "data-validation": "http://data-validation:8002", 
    "geography": "http://geography:8003",
    "index-calculation": "http://index-calculation:8004",
    "export": "http://export:8005",
    "orchestration": "http://orchestration:8006",
    "configuration": "http://configuration:8007",
}


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Add correlation ID to all requests."""
    
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        request.state.correlation_id = correlation_id
        
        # Add correlation ID to response headers
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests and responses."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        correlation_id = getattr(request.state, 'correlation_id', 'unknown')
        
        logger.info(
            "Request received",
            method=request.method,
            url=str(request.url),
            correlation_id=correlation_id,
            client_host=request.client.host if request.client else None,
        )
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            logger.info(
                "Request completed",
                status_code=response.status_code,
                process_time=process_time,
                correlation_id=correlation_id,
            )
            
            return response
            
        except Exception as exc:
            process_time = time.time() - start_time
            logger.exception(
                "Request failed",
                error=str(exc),
                process_time=process_time,
                correlation_id=correlation_id,
            )
            
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "Internal server error",
                    "correlation_id": correlation_id,
                }
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting RSAI API Gateway", version="1.0.0")
    
    # Verify service connectivity
    async with httpx.AsyncClient() as client:
        for service_name, service_url in SERVICES.items():
            try:
                response = await client.get(f"{service_url}/health", timeout=5.0)
                if response.status_code == 200:
                    logger.info(f"Service {service_name} is healthy")
                else:
                    logger.warning(f"Service {service_name} health check failed", status_code=response.status_code)
            except Exception as e:
                logger.warning(f"Could not connect to {service_name}", error=str(e))
    
    yield
    
    logger.info("Shutting down RSAI API Gateway")


# Create FastAPI application
app = FastAPI(
    title="RSAI API Gateway",
    description="API Gateway for RSAI Microservices Architecture",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add middleware
app.add_middleware(CorrelationIDMiddleware)
app.add_middleware(LoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def proxy_request(service_name: str, path: str, request: Request):
    """Proxy request to appropriate microservice."""
    if service_name not in SERVICES:
        raise HTTPException(status_code=404, detail=f"Service {service_name} not found")
    
    service_url = SERVICES[service_name]
    target_url = f"{service_url}{path}"
    
    # Prepare headers
    headers = dict(request.headers)
    headers["X-Correlation-ID"] = getattr(request.state, 'correlation_id', str(uuid.uuid4()))
    
    # Remove host header to avoid conflicts
    headers.pop("host", None)
    
    async with httpx.AsyncClient() as client:
        try:
            # Forward request to microservice
            if request.method == "GET":
                response = await client.get(
                    target_url,
                    headers=headers,
                    params=request.query_params,
                    timeout=30.0
                )
            elif request.method == "POST":
                body = await request.body()
                response = await client.post(
                    target_url,
                    headers=headers,
                    params=request.query_params,
                    content=body,
                    timeout=30.0
                )
            elif request.method == "PUT":
                body = await request.body()
                response = await client.put(
                    target_url,
                    headers=headers,
                    params=request.query_params,
                    content=body,
                    timeout=30.0
                )
            elif request.method == "DELETE":
                response = await client.delete(
                    target_url,
                    headers=headers,
                    params=request.query_params,
                    timeout=30.0
                )
            else:
                raise HTTPException(status_code=405, detail=f"Method {request.method} not allowed")
            
            # Return response
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.headers.get("content-type")
            )
            
        except httpx.TimeoutException:
            logger.error(f"Timeout calling {service_name} at {target_url}")
            raise HTTPException(status_code=504, detail="Service timeout")
        except httpx.ConnectError:
            logger.error(f"Connection error calling {service_name} at {target_url}")
            raise HTTPException(status_code=503, detail="Service unavailable")
        except Exception as e:
            logger.exception(f"Error proxying to {service_name}", error=str(e))
            raise HTTPException(status_code=500, detail="Internal server error")


# Route definitions
@app.api_route("/api/v1/ingestion/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def ingestion_proxy(path: str, request: Request):
    """Proxy requests to Data Ingestion Service."""
    return await proxy_request("data-ingestion", f"/api/v1/{path}", request)


@app.api_route("/api/v1/validation/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def validation_proxy(path: str, request: Request):
    """Proxy requests to Data Validation Service."""
    return await proxy_request("data-validation", f"/api/v1/{path}", request)


@app.api_route("/api/v1/geography/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def geography_proxy(path: str, request: Request):
    """Proxy requests to Geography Service."""
    return await proxy_request("geography", f"/api/v1/{path}", request)


@app.api_route("/api/v1/index/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def index_proxy(path: str, request: Request):
    """Proxy requests to Index Calculation Service."""
    return await proxy_request("index-calculation", f"/api/v1/{path}", request)


@app.api_route("/api/v1/export/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def export_proxy(path: str, request: Request):
    """Proxy requests to Export Service."""
    return await proxy_request("export", f"/api/v1/{path}", request)


@app.api_route("/api/v1/orchestration/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def orchestration_proxy(path: str, request: Request):
    """Proxy requests to Orchestration Service."""
    return await proxy_request("orchestration", f"/api/v1/{path}", request)


@app.api_route("/api/v1/config/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def config_proxy(path: str, request: Request):
    """Proxy requests to Configuration Service."""
    return await proxy_request("configuration", f"/api/v1/{path}", request)


@app.get("/health")
async def health_check():
    """Gateway health check."""
    service_status = {}
    
    async with httpx.AsyncClient() as client:
        for service_name, service_url in SERVICES.items():
            try:
                response = await client.get(f"{service_url}/health", timeout=5.0)
                service_status[service_name] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "response_time": response.elapsed.total_seconds()
                }
            except Exception as e:
                service_status[service_name] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
    
    # Overall gateway health
    all_healthy = all(s["status"] == "healthy" for s in service_status.values())
    
    return {
        "service": "api-gateway",
        "status": "healthy" if all_healthy else "degraded",
        "version": "1.0.0",
        "services": service_status,
    }


@app.get("/")
async def root():
    """Gateway information."""
    return {
        "service": "RSAI API Gateway",
        "version": "1.0.0",
        "description": "API Gateway for RSAI Microservices Architecture",
        "docs_url": "/docs",
        "health_url": "/health",
        "available_services": list(SERVICES.keys()),
    }


@app.get("/services")
async def list_services():
    """List all available services."""
    return {
        "services": SERVICES,
        "service_count": len(SERVICES),
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config=None,  # We use structlog
    )
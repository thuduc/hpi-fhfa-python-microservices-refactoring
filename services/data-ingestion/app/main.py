"""Main FastAPI application for Data Ingestion Service."""

import logging
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

from .api.routes import router
from .core.config import settings
from .core.logging import setup_logging
from .db.database import engine, Base


# Setup structured logging
setup_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Data Ingestion Service", version="1.0.0")
    
    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database tables created successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Data Ingestion Service")
    await engine.dispose()


# Create FastAPI application
app = FastAPI(
    title="RSAI Data Ingestion Service",
    description="Microservice for ingesting and preprocessing real estate transaction data",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log all requests with correlation ID."""
    correlation_id = request.headers.get("X-Correlation-ID", "unknown")
    
    # Bind correlation ID to logger
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
    
    logger.info(
        "Request received",
        method=request.method,
        url=str(request.url),
        client_host=request.client.host if request.client else None,
    )
    
    try:
        response = await call_next(request)
        
        logger.info(
            "Request completed",
            status_code=response.status_code,
        )
        
        return response
    
    except Exception as exc:
        logger.exception("Request failed", error=str(exc))
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Internal server error",
                "correlation_id": correlation_id,
            }
        )


# Include API routes
app.include_router(router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "service": "data-ingestion",
        "status": "healthy",
        "version": "1.0.0",
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "RSAI Data Ingestion Service",
        "version": "1.0.0",
        "docs_url": "/docs",
        "health_url": "/health",
        "metrics_url": "/metrics",
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=settings.DEBUG,
        log_config=None,  # We use structlog
    )
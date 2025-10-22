"""
FastAPI Application Entry Point
================================
Main application setup and configuration.
Includes health checks, CORS, documentation.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import datetime
import logging

from app.database import init_db
from app.schemas import HealthCheckResponse, ErrorResponse

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    logger.info("🚀 Starting Austrian Research Metadata Platform API...")
    init_db()
    logger.info("✓ Database initialized")

    yield

    # Shutdown
    logger.info("🛑 Shutting down API...")


# Create FastAPI application
app = FastAPI(
    title="Austrian Research Metadata Platform API",
    description="Aggregating and discovering Austrian research across universities and institutions",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for MVP
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Health Check Endpoints
# ============================================================================


@app.get("/health", response_model=HealthCheckResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    Verify API is running and database is connected.
    """
    return HealthCheckResponse(
        status="healthy",
        version="0.1.0",
        database="connected",
        timestamp=datetime.utcnow(),
    )


@app.get("/", tags=["Info"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Austrian Research Metadata Platform",
        "version": "0.1.0",
        "status": "operational",
        "docs": "/docs",
        "redoc": "/redoc",
        "contact": "research-metadata@example.at",
    }


# ============================================================================
# API Routes
# ============================================================================

from app.api import publications, organizations

app.include_router(publications.router)
app.include_router(organizations.router)


# ============================================================================
# Error Handlers
# ============================================================================


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "message": str(exc.detail),
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "status_code": 500,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


# ============================================================================
# Middleware & Logging
# ============================================================================


@app.middleware("http")
async def log_requests(request, call_next):
    """Log all incoming requests."""
    logger.info(f"{request.method} {request.url.path}")
    response = await call_next(request)
    return response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )

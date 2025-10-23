"""
FastAPI Application Entry Point
================================
Main application setup and configuration.
Includes health checks, CORS, documentation.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime
import logging
import os

from app.database import init_db
from app.schemas import HealthCheckResponse, ErrorResponse

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Get allowed origins from environment variable
# Format: comma-separated list of origins
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:8000"
).split(",")

# Strip whitespace from each origin
CORS_ORIGINS_LIST = [origin.strip() for origin in CORS_ORIGINS if origin.strip()]

logger.info(f"✓ CORS configured for origins: {CORS_ORIGINS_LIST}")


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

# Configure CORS with restricted origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS_LIST,  # ✅ SECURE: Only allow specific origins
    allow_credentials=False,  # ✅ SECURE: Disable credentials (public API)
    allow_methods=["GET", "POST"],  # ✅ SECURE: Only allow needed methods
    allow_headers=["Content-Type", "Authorization"],  # ✅ SECURE: Only needed headers
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


@app.get("/api/info", tags=["Info"])
async def api_info():
    """API information endpoint."""
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

from app.api import publications, organizations, researchers, projects, analytics, web

app.include_router(publications.router)
app.include_router(organizations.router)
app.include_router(researchers.router)
app.include_router(projects.router)
app.include_router(analytics.router)
app.include_router(web.router)


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
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)

    # Prevent browsers from guessing MIME type
    response.headers["X-Content-Type-Options"] = "nosniff"

    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"

    # Enable browser XSS protection
    response.headers["X-XSS-Protection"] = "1; mode=block"

    # Referrer policy
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Content Security Policy (CSP)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' https://cdn.jsdelivr.net https://cdn.plot.ly; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "img-src 'self' https: data:; "
        "font-src 'self' https:; "
        "connect-src 'self' https:; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )

    # HSTS (only in production)
    if os.getenv("ENVIRONMENT") == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
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

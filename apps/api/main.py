"""
MailGuard OSS - API Service
FastAPI REST API for OTP send/verify operations
"""
import asyncio
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from secure import SecureHeaders

from core.config import settings
from core.redis_client import init_redis, close_redis, check_redis_health
from core.db import check_db_health
from apps.api.routes import otp, health
from apps.api.middleware.api_key import APIKeyMiddleware


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup, cleanup on shutdown."""
    # Startup
    await init_redis(settings.REDIS_URL)
    print(f"✓ Redis connected")
    print(f"✓ MailGuard API starting in {settings.ENV} mode")
    
    yield
    
    # Shutdown
    await close_redis()
    print("✓ Redis connection closed")


# Create FastAPI application
app = FastAPI(
    title="MailGuard OSS",
    description="Telegram-Powered OTP & Email Automation Server",
    version="1.0.0",
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    lifespan=lifespan
)


# Security headers middleware
secure_headers = SecureHeaders()


@app.middleware("http")
async def set_secure_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    secure_headers.fastapi(response)
    return response


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.is_development else [],  # Configure in production
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unhandled exceptions gracefully."""
    # Log the error in production
    if settings.is_production:
        print(f"Error: {exc}")
        return JSONResponse(
            status_code=500,
            content={"error": "internal_server_error"}
        )
    # Show error details in development
    return JSONResponse(
        status_code=500,
        content={"error": str(exc)}
    )


# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(otp.router, prefix="/api/v1", tags=["OTP"])


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint - basic service info."""
    return {
        "name": "MailGuard OSS",
        "version": "1.0.0",
        "status": "running"
    }
"""
MailGuard OSS - Health Check Routes
"""
from fastapi import APIRouter, HTTPException
from core.redis_client import check_redis_health
from core.db import check_db_health

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check endpoint.
    Verifies database and Redis connectivity.
    Used by Railway for deployment health checks.
    """
    db_ok = False
    redis_ok = False
    
    # Check database
    try:
        db_ok = await check_db_health()
    except Exception as e:
        print(f"DB health check failed: {e}")
    
    # Check Redis
    try:
        redis_ok = await check_redis_health()
    except Exception as e:
        print(f"Redis health check failed: {e}")
    
    if not db_ok or not redis_ok:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "db": db_ok,
                "redis": redis_ok
            }
        )
    
    return {
        "status": "ok",
        "db": True,
        "redis": True
    }


@router.get("/health/live")
async def liveness_check():
    """Kubernetes-style liveness probe."""
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness_check():
    """Kubernetes-style readiness probe."""
    db_ok = await check_db_health()
    redis_ok = await check_redis_health()
    
    if not db_ok or not redis_ok:
        raise HTTPException(
            status_code=503,
            detail={"status": "not_ready"}
        )
    
    return {"status": "ready"}
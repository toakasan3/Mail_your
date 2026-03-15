"""
MailGuard OSS - API Key Authentication Middleware
"""
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import Optional, Dict, Any

from core.config import settings
from core.crypto import hash_api_key, is_sandbox_key
from core.db import get_api_key_by_hash, update_api_key_last_used
from core.redis_client import check_rate_limit_api_key

security = HTTPBearer()


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Verify API key from Authorization header.
    
    Args:
        credentials: Bearer token from Authorization header
        
    Returns:
        API key record with project information
        
    Raises:
        HTTPException: If key is invalid, revoked, or rate limited
    """
    api_key = credentials.credentials
    
    # Check for sandbox key in production
    if settings.is_production and is_sandbox_key(api_key):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "sandbox_key_in_production",
                "message": "Sandbox keys are not permitted in production"
            }
        )
    
    # Hash the key and look it up
    key_hash = hash_api_key(api_key)
    key_record = await get_api_key_by_hash(key_hash)
    
    if not key_record:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "invalid_api_key",
                "message": "API key not found or revoked"
            }
        )
    
    # Check if key is active
    if not key_record.get('is_active'):
        raise HTTPException(
            status_code=401,
            detail={
                "error": "api_key_revoked",
                "message": "API key has been revoked"
            }
        )
    
    # Check rate limit for API key
    rate_limit = await check_rate_limit_api_key(key_hash)
    if not rate_limit.allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limit_exceeded",
                "retry_after": rate_limit.retry_after
            }
        )
    
    # Update last used timestamp (non-blocking)
    await update_api_key_last_used(key_record['id'])
    
    return key_record


async def verify_api_key_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[Dict[str, Any]]:
    """
    Optionally verify API key - returns None if no key provided.
    """
    if credentials is None:
        return None
    return await verify_api_key(credentials)


def get_project_from_key(key_record: Dict[str, Any] = Depends(verify_api_key)) -> Dict[str, Any]:
    """
    Extract project from verified API key.
    """
    project = key_record.get('projects')
    if not project:
        raise HTTPException(
            status_code=500,
            detail={"error": "project_not_found"}
        )
    return project


class APIKeyMiddleware:
    """
    Middleware for API key validation and rate limiting.
    Can be used for additional request-level checks.
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        # This middleware is for additional processing
        # Main auth is done via Depends in route handlers
        await self.app(scope, receive, send)
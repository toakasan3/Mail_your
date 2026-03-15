"""
MailGuard OSS - OTP Routes
Handles OTP send and verify endpoints
"""
import asyncio
import time
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, validator
from typing import Optional

from core.config import settings
from core.crypto import hash_api_key, hmac_email, mask_email, is_sandbox_key
from core.otp import generate_otp, hash_otp, verify_otp_hash, generate_jwt_token
from core.db import (
    get_project, get_active_otp, create_otp_record,
    increment_otp_attempt, mark_otp_verified, invalidate_otp,
    count_otps_for_email, create_email_log, get_sender_email
)
from core.redis_client import (
    check_rate_limit_email, check_rate_limit_ip, check_rate_limit_project
)
from apps.api.middleware.api_key import verify_api_key, get_project_from_key

router = APIRouter()

# Anti-enumeration delay
SEND_MIN_SECONDS = 0.2


# ============================================================================
# Request/Response Models
# ============================================================================

class OtpSendRequest(BaseModel):
    """Request body for OTP send."""
    email: EmailStr
    purpose: Optional[str] = "verification"
    
    @validator('purpose')
    def validate_purpose(cls, v):
        allowed = ['registration', 'login', 'password_reset', 'verification', 'other']
        if v and v not in allowed:
            raise ValueError(f'purpose must be one of: {allowed}')
        return v


class OtpVerifyRequest(BaseModel):
    """Request body for OTP verify."""
    email: EmailStr
    code: str
    
    @validator('code')
    def validate_code(cls, v):
        if not v.isdigit():
            raise ValueError('code must contain only digits')
        if len(v) < 4 or len(v) > 8:
            raise ValueError('code must be 4-8 digits')
        return v


class OtpSendResponse(BaseModel):
    """Response for OTP send."""
    id: str
    status: str
    expires_in: int
    masked_email: str


class OtpVerifyResponse(BaseModel):
    """Response for OTP verify."""
    verified: bool
    token: Optional[str] = None
    expires_at: Optional[str] = None
    error: Optional[str] = None
    attempts_remaining: Optional[int] = None


# ============================================================================
# OTP Send Endpoint
# ============================================================================

@router.post("/otp/send", response_model=OtpSendResponse)
async def send_otp(
    request: Request,
    body: OtpSendRequest,
    key_record: dict = Depends(verify_api_key)
):
    """
    Send an OTP to the specified email address.
    
    - Generates a new OTP code
    - Hashes and stores it in the database
    - Queues email for delivery via worker
    - Implements rate limiting and anti-enumeration
    """
    start = time.monotonic()
    
    project = key_record.get('projects')
    if not project:
        raise HTTPException(status_code=500, detail={"error": "project_not_found"})
    
    project_id = project['id']
    email = body.email.lower().strip()
    email_hash = hmac_email(email)
    
    # Check for sandbox key
    is_sandbox = key_record.get('is_sandbox', False)
    
    # Check rate limits
    # 1. Per-email rate limit
    email_rate = await check_rate_limit_email(project_id, email_hash, project.get('rate_limit_per_hour', 10))
    if not email_rate.allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limit_exceeded",
                "message": "Too many OTPs sent to this email",
                "retry_after": email_rate.retry_after
            }
        )
    
    # 2. Per-project rate limit
    project_rate = await check_rate_limit_project(project_id)
    if not project_rate.allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limit_exceeded",
                "message": "Project daily limit exceeded",
                "retry_after": project_rate.retry_after
            }
        )
    
    # 3. Per-IP rate limit (if available)
    client_ip = request.client.host if request.client else None
    if client_ip:
        ip_rate = await check_rate_limit_ip(client_ip)
        if not ip_rate.allowed:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests from this IP",
                    "retry_after": ip_rate.retry_after
                }
            )
    
    # Invalidate any existing OTPs for this email
    existing_otp = await get_active_otp(project_id, email_hash)
    if existing_otp:
        await invalidate_otp(existing_otp['id'])
    
    # Generate new OTP
    otp_length = project.get('otp_length', settings.OTP_LENGTH)
    otp_expiry = project.get('otp_expiry_seconds', settings.OTP_EXPIRY_SECONDS)
    
    plaintext_otp = generate_otp(otp_length)
    otp_hash = hash_otp(plaintext_otp)
    expires_at = datetime.utcnow() + timedelta(seconds=otp_expiry)
    
    # Store OTP record
    otp_record = await create_otp_record(
        project_id=project_id,
        email_hash=email_hash,
        otp_hash=otp_hash,
        purpose=body.purpose,
        expires_at=expires_at
    )
    
    # For sandbox keys, use fixed OTP 000000
    if is_sandbox:
        plaintext_otp = "000000"
    
    # Queue email for sending (via ARQ worker)
    # This will be implemented in the worker service
    sender_email_id = project.get('sender_email_id')
    if sender_email_id and not is_sandbox:
        # Import here to avoid circular imports
        from apps.worker.tasks import send_otp_email
        await send_otp_email.kiq(
            email=email,
            otp=plaintext_otp,
            project_id=project_id,
            sender_email_id=sender_email_id,
            purpose=body.purpose,
            otp_record_id=otp_record['id']
        )
    
    # Anti-enumeration delay
    elapsed = time.monotonic() - start
    if elapsed < SEND_MIN_SECONDS:
        await asyncio.sleep(SEND_MIN_SECONDS - elapsed)
    
    return OtpSendResponse(
        id=otp_record['id'],
        status="sent",
        expires_in=otp_expiry,
        masked_email=mask_email(email)
    )


# ============================================================================
# OTP Verify Endpoint
# ============================================================================

@router.post("/otp/verify", response_model=OtpVerifyResponse)
async def verify_otp(
    request: Request,
    body: OtpVerifyRequest,
    key_record: dict = Depends(verify_api_key)
):
    """
    Verify an OTP code.
    
    - Checks the submitted code against stored hash
    - Implements attempt limiting
    - Issues JWT on successful verification
    """
    project = key_record.get('projects')
    if not project:
        raise HTTPException(status_code=500, detail={"error": "project_not_found"})
    
    project_id = project['id']
    email = body.email.lower().strip()
    email_hash = hmac_email(email)
    code = body.code
    
    # Check for sandbox key
    is_sandbox = key_record.get('is_sandbox', False)
    
    # For sandbox keys, accept 000000 as valid
    if is_sandbox:
        if code == "000000":
            token = generate_jwt_token(email, settings.JWT_SECRET, settings.JWT_EXPIRY_MINUTES)
            return OtpVerifyResponse(
                verified=True,
                token=token,
                expires_at=(datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRY_MINUTES)).isoformat()
            )
        else:
            return OtpVerifyResponse(
                verified=False,
                error="invalid_code",
                attempts_remaining=999
            )
    
    # Get active OTP for this email
    otp_record = await get_active_otp(project_id, email_hash)
    
    if not otp_record:
        # No OTP found - return error but don't reveal if email exists
        return OtpVerifyResponse(
            verified=False,
            error="invalid_code"
        )
    
    # Check if OTP is expired
    if datetime.utcnow() > datetime.fromisoformat(otp_record['expires_at'].replace('Z', '+00:00')):
        return OtpVerifyResponse(
            verified=False,
            error="otp_expired"
        )
    
    # Check if account is locked
    max_attempts = project.get('otp_max_attempts', settings.OTP_MAX_ATTEMPTS)
    if otp_record['attempt_count'] >= max_attempts:
        return OtpVerifyResponse(
            verified=False,
            error="account_locked"
        )
    
    # Verify the OTP
    if verify_otp_hash(code, otp_record['otp_hash']):
        # Success - mark as verified and issue JWT
        await mark_otp_verified(otp_record['id'])
        
        token = generate_jwt_token(email, settings.JWT_SECRET, settings.JWT_EXPIRY_MINUTES)
        expires_at = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRY_MINUTES)
        
        return OtpVerifyResponse(
            verified=True,
            token=token,
            expires_at=expires_at.isoformat()
        )
    else:
        # Failed - increment attempt count
        new_count = await increment_otp_attempt(otp_record['id'])
        remaining = max(0, max_attempts - new_count)
        
        if remaining == 0:
            return OtpVerifyResponse(
                verified=False,
                error="account_locked"
            )
        
        return OtpVerifyResponse(
            verified=False,
            error="invalid_code",
            attempts_remaining=remaining
        )
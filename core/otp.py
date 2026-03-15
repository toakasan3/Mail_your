"""
MailGuard OSS - OTP Module
OTP generation, bcrypt hashing, and verification
"""
import secrets
import bcrypt
import hmac
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Tuple


def generate_otp(length: int = 6) -> str:
    """
    Generate a numeric OTP code.
    
    Uses secrets.randbelow for uniform distribution.
    
    Args:
        length: Number of digits (default 6)
        
    Returns:
        Numeric OTP string
    """
    # Use secrets for cryptographically secure random
    # randbelow gives uniform distribution
    max_value = 10 ** length
    otp = secrets.randbelow(max_value)
    return str(otp).zfill(length)


def hash_otp(otp: str, rounds: int = 10) -> str:
    """
    Hash an OTP using bcrypt.
    
    Args:
        otp: The OTP string to hash
        rounds: bcrypt cost factor (default 10)
        
    Returns:
        bcrypt hashed OTP string
    """
    salt = bcrypt.gensalt(rounds=rounds)
    hashed = bcrypt.hashpw(otp.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_otp_hash(otp: str, otp_hash: str) -> bool:
    """
    Verify an OTP against a bcrypt hash.
    Uses constant-time comparison.
    
    Args:
        otp: The plaintext OTP to verify
        otp_hash: The bcrypt hash to verify against
        
    Returns:
        True if OTP matches, False otherwise
    """
    try:
        return bcrypt.checkpw(otp.encode('utf-8'), otp_hash.encode('utf-8'))
    except Exception:
        return False


def generate_jwt_token(
    email: str,
    jwt_secret: str,
    expiry_minutes: int = 10,
    additional_claims: Optional[dict] = None
) -> str:
    """
    Generate a JWT token for verified OTP.
    
    Args:
        email: The verified email address
        jwt_secret: Secret key for signing
        expiry_minutes: Token expiry time in minutes
        additional_claims: Optional additional claims
        
    Returns:
        JWT token string
    """
    import jwt
    
    now = datetime.utcnow()
    exp = now + timedelta(minutes=expiry_minutes)
    jti = secrets.token_hex(16)  # Unique token ID prevents reuse
    
    payload = {
        'sub': email,
        'iat': now,
        'exp': exp,
        'jti': jti,
        'type': 'otp_verified'
    }
    
    if additional_claims:
        payload.update(additional_claims)
    
    return jwt.encode(payload, jwt_secret, algorithm='HS256')


def verify_jwt_token(token: str, jwt_secret: str) -> Optional[dict]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token string
        jwt_secret: Secret key for verification
        
    Returns:
        Decoded payload if valid, None otherwise
    """
    import jwt
    
    try:
        payload = jwt.decode(token, jwt_secret, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def compute_expiry_seconds(custom_expiry: Optional[int] = None, default: int = 600) -> int:
    """
    Compute OTP expiry time in seconds.
    
    Args:
        custom_expiry: Custom expiry time if provided
        default: Default expiry time in seconds
        
    Returns:
        Expiry time in seconds
    """
    if custom_expiry is not None and 60 <= custom_expiry <= 3600:
        return custom_expiry
    return default


def is_otp_expired(expires_at: datetime) -> bool:
    """
    Check if an OTP has expired.
    
    Args:
        expires_at: Expiry datetime
        
    Returns:
        True if expired, False otherwise
    """
    return datetime.utcnow() > expires_at


def is_otp_locked(attempt_count: int, max_attempts: int = 5) -> bool:
    """
    Check if an OTP is locked due to too many attempts.
    
    Args:
        attempt_count: Number of failed attempts
        max_attempts: Maximum allowed attempts
        
    Returns:
        True if locked, False otherwise
    """
    return attempt_count >= max_attempts


class OTPResult:
    """Result of OTP generation."""
    
    def __init__(
        self,
        otp_id: str,
        plaintext_otp: str,
        otp_hash: str,
        email_hash: str,
        expires_at: datetime,
        masked_email: str
    ):
        self.otp_id = otp_id
        self.plaintext_otp = plaintext_otp
        self.otp_hash = otp_hash
        self.email_hash = email_hash
        self.expires_at = expires_at
        self.masked_email = masked_email
    
    @property
    def expires_in(self) -> int:
        """Seconds until expiry."""
        delta = self.expires_at - datetime.utcnow()
        return max(0, int(delta.total_seconds()))


class VerificationResult:
    """Result of OTP verification."""
    
    def __init__(
        self,
        verified: bool,
        error: Optional[str] = None,
        attempts_remaining: Optional[int] = None,
        jwt_token: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ):
        self.verified = verified
        self.error = error
        self.attempts_remaining = attempts_remaining
        self.jwt_token = jwt_token
        self.expires_at = expires_at
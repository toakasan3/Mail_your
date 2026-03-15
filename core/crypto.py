"""
MailGuard OSS - Cryptography Module
AES-256-GCM encryption for SMTP passwords and sensitive data
"""
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from typing import Optional

# Import settings with fallback for initialization
_settings = None


def init_crypto(settings):
    """Initialize crypto module with settings"""
    global _settings
    _settings = settings


def _get_key() -> bytes:
    """Get encryption key from settings"""
    if _settings is None:
        from core.config import settings as s
        return bytes.fromhex(s.ENCRYPTION_KEY)
    return bytes.fromhex(_settings.ENCRYPTION_KEY)


def encrypt(plaintext: str) -> str:
    """
    Encrypt plaintext using AES-256-GCM.
    
    Args:
        plaintext: The string to encrypt
        
    Returns:
        Hex-encoded string containing IV + ciphertext + auth tag
    """
    if not plaintext:
        raise ValueError("Cannot encrypt empty plaintext")
    
    key = _get_key()  # 32 bytes, always
    iv = os.urandom(12)  # 96-bit nonce, fresh per operation
    aesgcm = AESGCM(key)
    
    # Encrypt and prepend IV to ciphertext
    ciphertext = aesgcm.encrypt(iv, plaintext.encode('utf-8'), None)
    
    # Return IV + ciphertext as hex for storage
    return (iv + ciphertext).hex()


def decrypt(ciphertext_hex: str) -> str:
    """
    Decrypt ciphertext that was encrypted with encrypt().
    
    Args:
        ciphertext_hex: Hex-encoded string from encrypt()
        
    Returns:
        Original plaintext string
    """
    if not ciphertext_hex:
        raise ValueError("Cannot decrypt empty ciphertext")
    
    key = _get_key()
    data = bytes.fromhex(ciphertext_hex)
    
    # Extract IV (first 12 bytes) and ciphertext
    iv = data[:12]
    ciphertext = data[12:]
    
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(iv, ciphertext, None)
    
    return plaintext.decode('utf-8')


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key using SHA-256.
    
    Args:
        api_key: The plaintext API key
        
    Returns:
        SHA-256 hash of the key
    """
    import hashlib
    return hashlib.sha256(api_key.encode('utf-8')).hexdigest()


def generate_api_key(is_sandbox: bool = False) -> str:
    """
    Generate a new API key with proper prefix.
    
    Args:
        is_sandbox: If True, generate sandbox key (mg_test_)
        
    Returns:
        New API key string
    """
    import secrets
    prefix = "mg_test_" if is_sandbox else "mg_live_"
    return f"{prefix}{secrets.token_hex(32)}"


def get_key_prefix(api_key: str) -> str:
    """
    Extract the prefix from an API key.
    
    Args:
        api_key: The API key
        
    Returns:
        The prefix (mg_live_ or mg_test_)
    """
    if api_key.startswith("mg_test_"):
        return "mg_test_"
    elif api_key.startswith("mg_live_"):
        return "mg_live_"
    return ""


def is_sandbox_key(api_key: str) -> bool:
    """
    Check if an API key is a sandbox key.
    
    Args:
        api_key: The API key to check
        
    Returns:
        True if sandbox key, False otherwise
    """
    return api_key.startswith("mg_test_")


def hmac_email(email: str, secret: Optional[str] = None) -> str:
    """
    Generate HMAC-SHA256 hash of email address.
    Email addresses are never stored in plaintext.
    
    Args:
        email: Email address to hash
        secret: Optional secret (uses ENCRYPTION_KEY if not provided)
        
    Returns:
        HMAC-SHA256 hash of the email
    """
    import hmac
    import hashlib
    
    if secret is None:
        secret = _get_key().hex()
    
    return hmac.new(
        secret.encode('utf-8'),
        email.lower().strip().encode('utf-8'),
        hashlib.sha256
    ).hexdigest()


def mask_email(email: str) -> str:
    """
    Mask an email address for display purposes.
    
    Args:
        email: Email address to mask
        
    Returns:
        Masked email (e.g., "u***@example.com")
    """
    if '@' not in email:
        return email
    
    local, domain = email.split('@', 1)
    if len(local) <= 1:
        masked_local = local[0] + '***'
    else:
        masked_local = local[0] + '***'
    
    return f"{masked_local}@{domain}"
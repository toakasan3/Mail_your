"""
MailGuard OSS - Core Module
"""
from core.config import settings, Settings
from core.crypto import encrypt, decrypt, hash_api_key, generate_api_key, hmac_email, mask_email
from core.otp import generate_otp, hash_otp, verify_otp_hash, generate_jwt_token, verify_jwt_token

__all__ = [
    'settings',
    'Settings',
    'encrypt',
    'decrypt',
    'hash_api_key',
    'generate_api_key',
    'hmac_email',
    'mask_email',
    'generate_otp',
    'hash_otp',
    'verify_otp_hash',
    'generate_jwt_token',
    'verify_jwt_token',
]
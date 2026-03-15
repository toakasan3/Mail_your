"""
MailGuard OSS - Crypto Module Tests
"""
import pytest
from core.crypto import encrypt, decrypt, hash_api_key, generate_api_key, hmac_email, mask_email


class TestEncryptDecrypt:
    """Test AES-256-GCM encryption and decryption."""
    
    def test_encrypt_produces_different_ciphertext(self):
        """Same plaintext should produce different ciphertext each time."""
        plaintext = "my_secret_password"
        
        cipher1 = encrypt(plaintext)
        cipher2 = encrypt(plaintext)
        
        assert cipher1 != cipher2
        assert len(cipher1) > len(plaintext)
    
    def test_decrypt_reverses_encrypt(self):
        """Decrypt should recover the original plaintext."""
        plaintext = "my_app_password_123"
        
        ciphertext = encrypt(plaintext)
        recovered = decrypt(ciphertext)
        
        assert recovered == plaintext
    
    def test_encrypt_empty_raises(self):
        """Encrypting empty string should raise."""
        with pytest.raises(ValueError):
            encrypt("")
    
    def test_decrypt_empty_raises(self):
        """Decrypting empty string should raise."""
        with pytest.raises(ValueError):
            decrypt("")


class TestAPIKeyFunctions:
    """Test API key generation and hashing."""
    
    def test_generate_live_key(self):
        """Generate a live API key."""
        key = generate_api_key(is_sandbox=False)
        
        assert key.startswith("mg_live_")
        assert len(key) > 20
    
    def test_generate_sandbox_key(self):
        """Generate a sandbox API key."""
        key = generate_api_key(is_sandbox=True)
        
        assert key.startswith("mg_test_")
    
    def test_hash_api_key_consistent(self):
        """Same key should produce same hash."""
        key = "mg_live_test123456789"
        
        hash1 = hash_api_key(key)
        hash2 = hash_api_key(key)
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex
    
    def test_hash_api_key_different_keys(self):
        """Different keys should produce different hashes."""
        key1 = "mg_live_test123456789"
        key2 = "mg_live_test987654321"
        
        hash1 = hash_api_key(key1)
        hash2 = hash_api_key(key2)
        
        assert hash1 != hash2


class TestHMACEmail:
    """Test HMAC email hashing."""
    
    def test_hmac_email_consistent(self):
        """Same email should produce same hash."""
        email = "user@example.com"
        
        hash1 = hmac_email(email)
        hash2 = hmac_email(email)
        
        assert hash1 == hash2
    
    def test_hmac_email_normalizes(self):
        """HMAC should normalize email case and whitespace."""
        email1 = "User@Example.COM"
        email2 = "  user@example.com  "
        
        hash1 = hmac_email(email1)
        hash2 = hmac_email(email2)
        
        assert hash1 == hash2


class TestMaskEmail:
    """Test email masking."""
    
    def test_mask_email_standard(self):
        """Test standard email masking."""
        masked = mask_email("user@example.com")
        
        assert masked == "u***@example.com"
    
    def test_mask_email_short(self):
        """Test masking with short local part."""
        masked = mask_email("a@example.com")
        
        assert masked == "a***@example.com"
    
    def test_mask_email_invalid(self):
        """Test masking invalid email."""
        masked = mask_email("notanemail")
        
        assert masked == "notanemail"
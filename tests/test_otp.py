"""
MailGuard OSS - OTP Module Tests
"""
import pytest
from datetime import datetime, timedelta
from core.otp import (
    generate_otp, hash_otp, verify_otp_hash,
    generate_jwt_token, verify_jwt_token,
    is_otp_expired, is_otp_locked
)


class TestOTPGeneration:
    """Test OTP generation."""
    
    def test_generate_otp_default_length(self):
        """Generate OTP with default length."""
        otp = generate_otp()
        
        assert len(otp) == 6
        assert otp.isdigit()
    
    def test_generate_otp_custom_length(self):
        """Generate OTP with custom length."""
        otp = generate_otp(length=8)
        
        assert len(otp) == 8
        assert otp.isdigit()
    
    def test_generate_otp_uniform_distribution(self):
        """OTP should have uniform distribution (rough test)."""
        # Generate many OTPs and check all digits appear
        otps = [generate_otp() for _ in range(100)]
        all_digits = "".join(otps)
        
        # Each digit should appear roughly 10% of the time
        for digit in "0123456789":
            count = all_digits.count(digit)
            # With 600 digits total, expect ~60 per digit, allow wide margin
            assert count > 20, f"Digit {digit} appears too few times: {count}"
    
    def test_generate_otp_unique(self):
        """Each OTP should be unique (with very high probability)."""
        otps = set(generate_otp() for _ in range(1000))
        
        assert len(otps) > 990  # Almost all should be unique


class TestOTPHashing:
    """Test OTP hashing with bcrypt."""
    
    def test_hash_otp_produces_hash(self):
        """Hash OTP should produce bcrypt hash."""
        otp = "123456"
        hashed = hash_otp(otp)
        
        assert hashed != otp
        assert hashed.startswith("$2b$")
    
    def test_verify_correct_otp(self):
        """Verify correct OTP against hash."""
        otp = "654321"
        hashed = hash_otp(otp)
        
        assert verify_otp_hash(otp, hashed) is True
    
    def test_verify_incorrect_otp(self):
        """Verify incorrect OTP against hash."""
        otp = "654321"
        hashed = hash_otp(otp)
        
        assert verify_otp_hash("111111", hashed) is False
    
    def test_hash_different_each_time(self):
        """Same OTP should produce different hashes (bcrypt salt)."""
        otp = "123456"
        
        hash1 = hash_otp(otp)
        hash2 = hash_otp(otp)
        
        assert hash1 != hash2
        # But both should verify
        assert verify_otp_hash(otp, hash1)
        assert verify_otp_hash(otp, hash2)


class TestJWTToken:
    """Test JWT token generation and verification."""
    
    @pytest.fixture
    def jwt_secret(self):
        return "test_jwt_secret_minimum_64_characters_long_for_security_purposes_12345678"
    
    def test_generate_jwt_token(self, jwt_secret):
        """Generate a JWT token."""
        token = generate_jwt_token("user@example.com", jwt_secret)
        
        assert token is not None
        assert len(token) > 50
    
    def test_verify_valid_jwt_token(self, jwt_secret):
        """Verify a valid JWT token."""
        email = "user@example.com"
        token = generate_jwt_token(email, jwt_secret)
        
        payload = verify_jwt_token(token, jwt_secret)
        
        assert payload is not None
        assert payload["sub"] == email
        assert payload["type"] == "otp_verified"
        assert "jti" in payload
    
    def test_verify_expired_jwt_token(self, jwt_secret):
        """Verify rejects expired token."""
        import jwt
        
        email = "user@example.com"
        # Create expired token
        payload = {
            "sub": email,
            "exp": datetime.utcnow() - timedelta(hours=1),
            "jti": "test_jti"
        }
        token = jwt.encode(payload, jwt_secret, algorithm="HS256")
        
        result = verify_jwt_token(token, jwt_secret)
        
        assert result is None
    
    def test_verify_invalid_jwt_token(self, jwt_secret):
        """Verify rejects invalid token."""
        result = verify_jwt_token("invalid.token.here", jwt_secret)
        
        assert result is None


class TestOTPValidation:
    """Test OTP validation helpers."""
    
    def test_is_otp_expired_future(self):
        """OTP in future is not expired."""
        expires = datetime.utcnow() + timedelta(minutes=5)
        
        assert is_otp_expired(expires) is False
    
    def test_is_otp_expired_past(self):
        """OTP in past is expired."""
        expires = datetime.utcnow() - timedelta(minutes=1)
        
        assert is_otp_expired(expires) is True
    
    def test_is_otp_locked_under_limit(self):
        """OTP under attempt limit is not locked."""
        assert is_otp_locked(0) is False
        assert is_otp_locked(4) is False
    
    def test_is_otp_locked_at_limit(self):
        """OTP at attempt limit is locked."""
        assert is_otp_locked(5) is True
        assert is_otp_locked(10) is True
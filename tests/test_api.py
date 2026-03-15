"""
MailGuard OSS - API Tests
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestHealthEndpoint:
    """Test health check endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi import FastAPI
        from apps.api.routes.health import router
        
        app = FastAPI()
        app.include_router(router)
        
        return TestClient(app)
    
    def test_health_check_healthy(self, client, mock_redis, mock_supabase):
        """Test health check when all services healthy."""
        with patch("apps.api.routes.health.check_db_health", return_value=True), \
             patch("apps.api.routes.health.check_redis_health", return_value=True):
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["db"] is True
            assert data["redis"] is True
    
    def test_health_check_db_unhealthy(self, client):
        """Test health check when database is unhealthy."""
        with patch("apps.api.routes.health.check_db_health", return_value=False), \
             patch("apps.api.routes.health.check_redis_health", return_value=True):
            response = client.get("/health")
            
            assert response.status_code == 503
            data = response.json()
            assert data["detail"]["status"] == "unhealthy"
            assert data["detail"]["db"] is False
    
    def test_liveness_check(self, client):
        """Test liveness probe."""
        response = client.get("/health/live")
        
        assert response.status_code == 200
        assert response.json()["status"] == "alive"
    
    def test_readiness_check_healthy(self, client):
        """Test readiness probe when ready."""
        with patch("apps.api.routes.health.check_db_health", return_value=True), \
             patch("apps.api.routes.health.check_redis_health", return_value=True):
            response = client.get("/health/ready")
            
            assert response.status_code == 200
            assert response.json()["status"] == "ready"


class TestOTPEndpoints:
    """Test OTP send and verify endpoints."""
    
    @pytest.fixture
    def app(self):
        """Create test FastAPI app."""
        from fastapi import FastAPI
        from apps.api.routes.otp import router
        
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        
        return app
    
    @pytest.fixture
    def mock_api_key_record(self):
        """Mock API key record."""
        return {
            "id": "test-key-id",
            "is_active": True,
            "is_sandbox": False,
            "projects": {
                "id": "test-project-id",
                "name": "Test Project",
                "slug": "test-project",
                "otp_length": 6,
                "otp_expiry_seconds": 600,
                "otp_max_attempts": 5,
                "rate_limit_per_hour": 10
            }
        }
    
    def test_send_otp_sandbox(self, app, mock_api_key_record):
        """Test sending OTP with sandbox key."""
        mock_api_key_record["is_sandbox"] = True
        
        client = TestClient(app)
        
        with patch("apps.api.routes.otp.verify_api_key", return_value=mock_api_key_record), \
             patch("apps.api.routes.otp.check_rate_limit_email") as mock_rate, \
             patch("apps.api.routes.otp.check_rate_limit_project") as mock_proj_rate:
            
            mock_rate.return_value = MagicMock(allowed=True)
            mock_proj_rate.return_value = MagicMock(allowed=True)
            
            response = client.post(
                "/api/v1/otp/send",
                json={"email": "user@example.com", "purpose": "registration"},
                headers={"Authorization": "Bearer mg_test_key"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "sent"
            assert "id" in data
            assert "expires_in" in data
    
    def test_send_otp_rate_limited(self, app, mock_api_key_record):
        """Test sending OTP when rate limited."""
        client = TestClient(app)
        
        with patch("apps.api.routes.otp.verify_api_key", return_value=mock_api_key_record), \
             patch("apps.api.routes.otp.check_rate_limit_email") as mock_rate:
            
            mock_rate.return_value = MagicMock(
                allowed=False,
                retry_after=3600
            )
            
            response = client.post(
                "/api/v1/otp/send",
                json={"email": "user@example.com"},
                headers={"Authorization": "Bearer mg_live_key"}
            )
            
            assert response.status_code == 429
    
    def test_verify_otp_sandbox(self, app, mock_api_key_record):
        """Test verifying OTP with sandbox key."""
        mock_api_key_record["is_sandbox"] = True
        
        client = TestClient(app)
        
        with patch("apps.api.routes.otp.verify_api_key", return_value=mock_api_key_record):
            response = client.post(
                "/api/v1/otp/verify",
                json={"email": "user@example.com", "code": "000000"},
                headers={"Authorization": "Bearer mg_test_key"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["verified"] is True
            assert "token" in data
    
    def test_verify_otp_invalid_code(self, app, mock_api_key_record):
        """Test verifying with invalid code."""
        mock_api_key_record["is_sandbox"] = True
        
        client = TestClient(app)
        
        with patch("apps.api.routes.otp.verify_api_key", return_value=mock_api_key_record):
            response = client.post(
                "/api/v1/otp/verify",
                json={"email": "user@example.com", "code": "123456"},
                headers={"Authorization": "Bearer mg_test_key"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["verified"] is False
            assert data["error"] == "invalid_code"
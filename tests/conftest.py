"""
MailGuard OSS - Test Configuration
"""
import pytest
import asyncio
from typing import Generator

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings(monkeypatch):
    """Mock settings for testing."""
    from core.config import Settings
    
    test_settings = Settings(
        SUPABASE_URL="https://test.supabase.co",
        SUPABASE_SERVICE_ROLE_KEY="test_service_role_key",
        REDIS_URL="redis://localhost:6379",
        ENCRYPTION_KEY="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        JWT_SECRET="test_jwt_secret_minimum_64_characters_long_for_security_purposes_12345678",
        ENV="test",
        TELEGRAM_BOT_TOKEN="test_token",
        TELEGRAM_ADMIN_UID=123456789
    )
    
    monkeypatch.setattr("core.config.settings", test_settings)
    return test_settings


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    from unittest.mock import AsyncMock, MagicMock
    
    redis_mock = MagicMock()
    redis_mock.ping = AsyncMock(return_value=True)
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.setex = AsyncMock(return_value=True)
    redis_mock.delete = AsyncMock(return_value=1)
    redis_mock.zadd = AsyncMock(return_value=1)
    redis_mock.zremrangebyscore = AsyncMock(return_value=0)
    redis_mock.zcard = AsyncMock(return_value=0)
    redis_mock.zrange = AsyncMock(return_value=[])
    
    return redis_mock


@pytest.fixture
def mock_supabase():
    """Mock Supabase client for testing."""
    from unittest.mock import MagicMock
    
    client = MagicMock()
    client.table = MagicMock(return_value=client)
    client.select = MagicMock(return_value=client)
    client.insert = MagicMock(return_value=client)
    client.update = MagicMock(return_value=client)
    client.delete = MagicMock(return_value=client)
    client.eq = MagicMock(return_value=client)
    client.limit = MagicMock(return_value=client)
    client.execute = MagicMock(return_value=MagicMock(data=[]))
    
    return client
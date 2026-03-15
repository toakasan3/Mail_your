"""
MailGuard OSS - Redis Module
Redis client and rate limiting with sliding window algorithm
"""
import redis.asyncio as redis
from typing import Optional, Tuple
from datetime import datetime
import time

# Global Redis client
_redis_client: Optional[redis.Redis] = None


async def init_redis(redis_url: str) -> redis.Redis:
    """
    Initialize the Redis client.
    
    Args:
        redis_url: Redis connection URL
        
    Returns:
        Redis client instance
    """
    global _redis_client
    _redis_client = redis.from_url(redis_url, decode_responses=True)
    return _redis_client


async def get_redis() -> redis.Redis:
    """
    Get the Redis client instance.
    
    Returns:
        Redis client
        
    Raises:
        RuntimeError: If client not initialized
    """
    if _redis_client is None:
        raise RuntimeError("Redis client not initialized. Call init_redis() first.")
    return _redis_client


async def close_redis() -> None:
    """Close the Redis connection."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None


async def check_redis_health() -> bool:
    """Check Redis connectivity."""
    try:
        client = await get_redis()
        await client.ping()
        return True
    except Exception:
        return False


# ============================================================================
# Rate Limiting with Sliding Window
# ============================================================================

class RateLimitResult:
    """Result of a rate limit check."""
    
    def __init__(
        self,
        allowed: bool,
        limit: int,
        remaining: int,
        reset_after: float,
        retry_after: Optional[int] = None
    ):
        self.allowed = allowed
        self.limit = limit
        self.remaining = remaining
        self.reset_after = reset_after
        self.retry_after = retry_after
    
    def to_dict(self) -> dict:
        return {
            'allowed': self.allowed,
            'limit': self.limit,
            'remaining': self.remaining,
            'reset_after': self.reset_after,
            'retry_after': self.retry_after
        }


async def check_rate_limit(
    key: str,
    limit: int,
    window_seconds: int
) -> RateLimitResult:
    """
    Check rate limit using sliding window algorithm.
    
    Uses Redis sorted sets for accurate sliding window rate limiting.
    
    Args:
        key: Redis key for this rate limit
        limit: Maximum requests allowed in window
        window_seconds: Window size in seconds
        
    Returns:
        RateLimitResult with allowed status and metadata
    """
    client = await get_redis()
    now = time.time()
    window_start = now - window_seconds
    
    # Use pipeline for atomicity
    pipe = client.pipeline()
    
    # Remove expired entries
    pipe.zremrangebyscore(key, 0, window_start)
    
    # Count current entries
    pipe.zcard(key)
    
    # Add current request (score = timestamp, member = unique ID)
    member = f"{now}:{id(pipe)}"
    pipe.zadd(key, {member: now})
    
    # Set expiry
    pipe.expire(key, window_seconds + 1)
    
    results = await pipe.execute()
    current_count = results[1]  # Count after cleanup, before adding
    
    if current_count >= limit:
        # Rate limit exceeded
        # Calculate when the oldest entry will expire
        oldest = await client.zrange(key, 0, 0, withscores=True)
        if oldest:
            oldest_time = oldest[0][1]
            reset_after = oldest_time + window_seconds - now
        else:
            reset_after = window_seconds
        
        return RateLimitResult(
            allowed=False,
            limit=limit,
            remaining=0,
            reset_after=reset_after,
            retry_after=int(reset_after) + 1
        )
    
    return RateLimitResult(
        allowed=True,
        limit=limit,
        remaining=limit - current_count - 1,
        reset_after=window_seconds
    )


async def increment_rate_limit(key: str, window_seconds: int) -> None:
    """
    Increment rate limit counter.
    Usually called after check_rate_limit passes.
    
    Args:
        key: Redis key
        window_seconds: Window size
    """
    client = await get_redis()
    now = time.time()
    member = f"{now}:{id(client)}"
    
    pipe = client.pipeline()
    pipe.zadd(key, {member: now})
    pipe.expire(key, window_seconds + 1)
    await pipe.execute()


# ============================================================================
# Predefined Rate Limit Tiers
# ============================================================================

async def check_rate_limit_email(project_id: str, email_hash: str, limit: int = 10) -> RateLimitResult:
    """
    Check per-email rate limit (default: 10 OTPs/hour).
    """
    key = f"ratelimit:email:{project_id}:{email_hash}"
    return await check_rate_limit(key, limit, 3600)


async def check_rate_limit_api_key(key_hash: str, limit: int = 1000) -> RateLimitResult:
    """
    Check per-API-key rate limit (default: 1000 requests/hour).
    """
    key = f"ratelimit:apikey:{key_hash}"
    return await check_rate_limit(key, limit, 3600)


async def check_rate_limit_ip(ip_address: str, limit: int = 100) -> RateLimitResult:
    """
    Check per-IP rate limit (default: 100 requests/15 minutes).
    """
    key = f"ratelimit:ip:{ip_address}"
    return await check_rate_limit(key, limit, 900)


async def check_rate_limit_project(project_id: str, limit: int = 10000) -> RateLimitResult:
    """
    Check per-project global rate limit (default: 10000 OTPs/day).
    """
    key = f"ratelimit:project:{project_id}"
    return await check_rate_limit(key, limit, 86400)


async def check_rate_limit_sender(sender_id: str, limit: int = 500) -> RateLimitResult:
    """
    Check per-sender SMTP rate limit (default: 500 emails/day).
    """
    key = f"ratelimit:sender:{sender_id}"
    return await check_rate_limit(key, limit, 86400)


# ============================================================================
# Cache Utilities
# ============================================================================

async def cache_get(key: str) -> Optional[str]:
    """Get a cached value."""
    client = await get_redis()
    return await client.get(key)


async def cache_set(key: str, value: str, ttl: int = 3600) -> None:
    """Set a cached value with TTL."""
    client = await get_redis()
    await client.setex(key, ttl, value)


async def cache_delete(key: str) -> None:
    """Delete a cached value."""
    client = await get_redis()
    await client.delete(key)


async def cache_invalidate_pattern(pattern: str) -> int:
    """Delete all keys matching a pattern."""
    client = await get_redis()
    keys = []
    async for key in client.scan_iter(match=pattern):
        keys.append(key)
    if keys:
        return await client.delete(*keys)
    return 0
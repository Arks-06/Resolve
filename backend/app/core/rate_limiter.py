"""
Implements distributed algorithms via Redis to throttle excessive consumer requests and prevent platform abuse.
Enforces tenant-level quotas to ensure stable infrastructure performance across the multi-tenant architecture.
"""

import os
import time
from fastapi import HTTPException, status
from redis.asyncio import Redis, from_url

# Initialize dynamic environment lookup for distributed Redis cache cluster
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client: Redis = from_url(REDIS_URL, decode_responses=True)

class SlidingWindowRateLimiter:
    """
    Enforces transaction limits per tenant identifier using an atomic Redis sliding window log mechanism.
    """
    
    @staticmethod
    def _generate_key(tenant_id: str, limit_key: str) -> str:
        """
        Builds a structured namespace lookup key for Redis keyspace isolation.
        """
        return f"rate_limit:{tenant_id}:{limit_key}"

    @classmethod
    async def check_rate_limit(
        cls, 
        tenant_id: str, 
        limit_key: str = "global_api", 
        max_requests: int = 60, 
        window_seconds: int = 60
    ) -> None:
        """
        Evaluates execution limits. Raises an HTTP 429 exception if incoming request velocities exceed limits.
        """
        current_timestamp = time.time()
        redis_key = cls._generate_key(tenant_id, limit_key)
        clear_before_timestamp = current_timestamp - window_seconds
        
        try:
            # Execute atomic multi-command execution transaction space over connection pool
            async with redis_client.pipeline(transaction=True) as pipe:
                # Evict stale entry records falling behind the threshold boundary parameter
                pipe.zremrangebyscore(redis_key, 0, clear_before_timestamp)
                # Query population volume currently remaining within active window boundaries
                pipe.zcard(redis_key)
                # Inject current unique transaction entry record execution payload
                pipe.zadd(redis_key, {str(current_timestamp): current_timestamp})
                # Re-verify sliding scale TTL parameters to clear space efficiently
                pipe.expire(redis_key, window_seconds)
                
                # Extract evaluation matrices from sequential pipeline outputs
                _, current_window_count, _, _ = await pipe.execute()
                
            if current_window_count > max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Organization API transactional quota threshold exceeded. Action rejected."
                )
        except HTTPException:
            raise
        except Exception:
            # Fall open in case of unexpected cache system errors to guarantee service availability
            pass
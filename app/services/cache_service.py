"""
Redis Cache Service

Provides caching functionality with TTL support for API responses.
"""

import json
import logging
import hashlib
from typing import Any, Optional, Union
from datetime import timedelta

import redis.asyncio as redis
from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Redis-based cache service with TTL support"""
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self._redis: Optional[redis.Redis] = None
        self.default_ttl = 600  # 10 minutes in seconds
    
    async def connect(self):
        """Initialize Redis connection"""
        if self._redis is None:
            try:
                self._redis = redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                # Test connection
                await self._redis.ping()
                logger.info("Redis cache service connected successfully")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self._redis = None
    
    async def disconnect(self):
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("Redis cache service disconnected")
    
    def _generate_cache_key(self, prefix: str, **params) -> str:
        """
        Generate a consistent cache key from parameters
        
        Args:
            prefix: Key prefix (e.g., "location_search")
            **params: Parameters to include in key
            
        Returns:
            Consistent cache key
        """
        # Sort parameters for consistent key generation
        sorted_params = sorted(params.items())
        params_str = "&".join([f"{k}={v}" for k, v in sorted_params if v is not None])
        
        # Hash for consistent length and special character handling
        params_hash = hashlib.md5(params_str.encode()).hexdigest()
        
        return f"{prefix}:{params_hash}"
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get cached value by key
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        if not self._redis:
            return None
        
        try:
            cached_data = await self._redis.get(key)
            if cached_data:
                logger.debug(f"Cache HIT for key: {key}")
                return json.loads(cached_data)
        except Exception as e:
            logger.warning(f"Cache GET error for key {key}: {e}")
        
        logger.debug(f"Cache MISS for key: {key}")
        return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[Union[int, timedelta]] = None
    ) -> bool:
        """
        Set cached value with TTL
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time to live in seconds or timedelta (default: 10 minutes)
            
        Returns:
            True if cached successfully, False otherwise
        """
        if not self._redis:
            return False
        
        try:
            # Convert value to JSON
            cached_data = json.dumps(value, default=str)
            
            # Handle TTL
            if ttl is None:
                ttl = self.default_ttl
            elif isinstance(ttl, timedelta):
                ttl = int(ttl.total_seconds())
            
            # Set with TTL
            result = await self._redis.setex(key, ttl, cached_data)
            
            if result:
                logger.debug(f"Cache SET for key: {key} (TTL: {ttl}s)")
                return True
                
        except Exception as e:
            logger.warning(f"Cache SET error for key {key}: {e}")
        
        return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete cached value
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted, False otherwise
        """
        if not self._redis:
            return False
        
        try:
            result = await self._redis.delete(key)
            logger.debug(f"Cache DELETE for key: {key}")
            return result > 0
        except Exception as e:
            logger.warning(f"Cache DELETE error for key {key}: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern
        
        Args:
            pattern: Pattern to match (e.g., "location_search:*")
            
        Returns:
            Number of keys deleted
        """
        if not self._redis:
            return 0
        
        try:
            keys = await self._redis.keys(pattern)
            if keys:
                deleted = await self._redis.delete(*keys)
                logger.info(f"Cache CLEAR pattern '{pattern}': {deleted} keys deleted")
                return deleted
        except Exception as e:
            logger.warning(f"Cache CLEAR pattern error for '{pattern}': {e}")
        
        return 0
    
    async def get_cached_search_results(
        self,
        search_keyword: str,
        page: int,
        per_page: int,
        location_type: Optional[str] = None,
        country_id: Optional[int] = None,
        tracking_only: bool = False
    ) -> Optional[Any]:
        """
        Get cached search results with specific parameters
        
        Returns:
            Cached search results or None
        """
        key = self._generate_cache_key(
            "location_search",
            q=search_keyword,
            page=page,
            per_page=per_page,
            type=location_type,
            country_id=country_id,
            tracking_only=tracking_only
        )
        
        return await self.get(key)
    
    async def cache_search_results(
        self,
        search_keyword: str,
        page: int,
        per_page: int,
        results: Any,
        location_type: Optional[str] = None,
        country_id: Optional[int] = None,
        tracking_only: bool = False,
        ttl: int = None
    ) -> bool:
        """
        Cache search results with specific parameters
        
        Args:
            ttl: TTL in seconds (default: 10 minutes)
            
        Returns:
            True if cached successfully
        """
        key = self._generate_cache_key(
            "location_search",
            q=search_keyword,
            page=page,
            per_page=per_page,
            type=location_type,
            country_id=country_id,
            tracking_only=tracking_only
        )
        
        return await self.set(key, results, ttl or 600)  # 10 minutes default
    
    async def invalidate_location_cache(self) -> int:
        """
        Invalidate all location search cache entries
        
        Useful when location data is updated.
        
        Returns:
            Number of cache entries cleared
        """
        return await self.clear_pattern("location_search:*")


# Global cache service instance
_cache_service: Optional[CacheService] = None


async def get_cache_service() -> CacheService:
    """Get or create cache service instance"""
    global _cache_service
    
    if _cache_service is None:
        _cache_service = CacheService()
        await _cache_service.connect()
    
    return _cache_service


async def close_cache_service():
    """Close cache service connection"""
    global _cache_service
    
    if _cache_service:
        await _cache_service.disconnect()
        _cache_service = None
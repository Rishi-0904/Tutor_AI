import os
import json
import threading
from typing import Any, Optional

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

class RedisCache:
    def __init__(self):
        self.redis_client = None
        self.fallback_cache = {}
        self.lock = threading.Lock()
        
        if REDIS_AVAILABLE:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            try:
                # Set a low timeout so we don't block backend startup if Redis is absent
                self.redis_client = redis.Redis.from_url(
                    redis_url, 
                    socket_connect_timeout=2.0,
                    socket_timeout=2.0,
                    decode_responses=True
                )
                # Test connection
                self.redis_client.ping()
                print(f"[Redis] Successfully connected to Redis at {redis_url}")
            except Exception as e:
                print(f"[Redis] Connection failed: {e}. Falling back to In-Memory Cache.")
                self.redis_client = None
        else:
            print("[Redis] Library not available. Falling back to In-Memory Cache.")

    def get(self, key: str) -> Optional[Any]:
        """Retrieve key from Redis or fallback dictionary."""
        if self.redis_client:
            try:
                val = self.redis_client.get(key)
                if val:
                    try:
                        return json.loads(val)
                    except:
                        return val
            except Exception as e:
                print(f"[Redis] Error reading key {key}: {e}")
                
        # In-memory fallback
        with self.lock:
            return self.fallback_cache.get(key)

    def set(self, key: str, value: Any, expire_seconds: Optional[int] = None) -> bool:
        """Store key-value pair in Redis or fallback dictionary."""
        val_str = json.dumps(value) if not isinstance(value, str) else value
        
        if self.redis_client:
            try:
                if expire_seconds:
                    self.redis_client.setex(key, expire_seconds, val_str)
                else:
                    self.redis_client.set(key, val_str)
                return True
            except Exception as e:
                print(f"[Redis] Error setting key {key}: {e}")
                
        # In-memory fallback
        with self.lock:
            self.fallback_cache[key] = value
            # Note: We won't implement complex expiration timers in memory fallback 
            # to keep it simple and lightweight.
            return True

    def delete(self, key: str) -> bool:
        """Delete key from Redis or fallback dictionary."""
        if self.redis_client:
            try:
                self.redis_client.delete(key)
                return True
            except Exception as e:
                print(f"[Redis] Error deleting key {key}: {e}")
                
        with self.lock:
            if key in self.fallback_cache:
                del self.fallback_cache[key]
                return True
        return False

# Global Cache Singleton
cache = RedisCache()

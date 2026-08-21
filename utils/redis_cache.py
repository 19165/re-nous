import json
import hashlib
from typing import Optional, Dict, Any
from config import redis_client, is_redis_available, REDIS_CACHE_TTL
from utils.logger import logger

def make_hash_key(prefix: str, content: str) -> str:
    """
    Generates a deterministic SHA256 cache key based on the prefix and normalized input text.
    """
    normalized = content.strip().lower()
    hash_digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"node_cache:{prefix}:{hash_digest}"

def get_cached_node_result(prefix: str, input_data: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves a cached JSON-serialized node result from Redis by prefix and input hash.
    Returns None if Redis is unavailable or on cache miss.
    """
    if not is_redis_available or redis_client is None:
        return None

    key = make_hash_key(prefix, input_data)
    try:
        cached_value = redis_client.get(key)
        if cached_value:
            logger.info(f"⚡ [bold magenta][Cache Hit][/bold magenta] Returning cached result for [cyan]{prefix}[/cyan] (key: [dim]{key[:25]}...[/dim])")
            return json.loads(cached_value)
    except Exception as e:
        logger.warning(f"⚠️ Failed to read from Redis cache for key '{key}': {e}")
        return None

    return None

def set_cached_node_result(
    prefix: str, input_data: str, result_data: Dict[str, Any], ttl: int = REDIS_CACHE_TTL
) -> bool:
    """
    Stores a JSON-serializable node result in Redis with a specified TTL.
    Returns True if successfully written, False otherwise.
    """
    if not is_redis_available or redis_client is None:
        return False

    key = make_hash_key(prefix, input_data)
    try:
        serialized = json.dumps(result_data, default=str)
        redis_client.set(key, serialized, ex=ttl)
        logger.debug(f"💾 [Cache Saved] Saved result for {prefix} to Redis (TTL: {ttl}s)")
        return True
    except Exception as e:
        logger.warning(f"⚠️ Failed to write to Redis cache for key '{key}': {e}")
        return False

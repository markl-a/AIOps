# AIOps Cache System - Usage Guide

## Table of Contents
1. [Basic Usage](#basic-usage)
2. [Redis Configuration](#redis-configuration)
3. [TTL Strategies](#ttl-strategies)
4. [Cache Stampede Protection](#cache-stampede-protection)
5. [Pattern-Based Invalidation](#pattern-based-invalidation)
6. [Health Monitoring](#health-monitoring)
7. [Best Practices](#best-practices)

---

## Basic Usage

### Using the @cached Decorator

```python
from aiops.core.cache import cached

# Simple caching with default TTL (1 hour)
@cached()
async def fetch_user_data(user_id: int):
    # Expensive database query
    return await db.query("SELECT * FROM users WHERE id = ?", user_id)

# Custom TTL
@cached(ttl=300)  # 5 minutes
async def get_stock_price(symbol: str):
    return await api.get_price(symbol)

# Disable stampede protection if needed
@cached(ttl=3600, enable_stampede_protection=False)
async def low_cost_operation():
    return simple_computation()
```

### Direct Cache Access

```python
from aiops.core.cache import get_cache

cache = get_cache()

# Set a value
cache.set("user:123", {"name": "John", "email": "john@example.com"}, ttl=3600)

# Get a value
user_data = cache.get("user:123")

# Check if exists
if cache.exists("user:123"):
    print("User in cache")

# Delete a key
cache.delete("user:123")

# Clear all cache
cache.clear()
```

---

## Redis Configuration

### Environment-Based Configuration

```bash
# .env file
ENABLE_REDIS=true
REDIS_URL=redis://localhost:6379/0
```

```python
from aiops.core.cache import Cache

# Auto-detects from environment
cache = Cache()
```

### Programmatic Configuration

```python
from aiops.core.cache import Cache, RedisBackend

# Create custom Redis backend
redis_backend = RedisBackend(
    redis_url="redis://localhost:6379/0",
    prefix="myapp",
    max_retries=5,              # Retry 5 times on connection failure
    retry_backoff=1.0,          # Start with 1s, doubles each retry
    socket_timeout=10,          # 10s socket timeout
    socket_connect_timeout=10,  # 10s connection timeout
    max_connections=100,        # Pool of 100 connections
)

# Use custom backend
cache = Cache(enable_redis=True)
cache.backend = redis_backend
```

### Async Redis Cache

```python
from aiops.cache.redis_cache import RedisCache

# Create async Redis cache
cache = RedisCache(
    redis_url="redis://localhost:6379/0",
    default_ttl=3600,
    max_retries=3,
    retry_backoff=0.5,
    max_connections=50,
    enable_stampede_protection=True,
)

# Must connect before use
await cache.connect()

# Use cache
await cache.set("key", "value", ttl=300)
value = await cache.get("key")

# Cleanup
await cache.disconnect()
```

### Connection Resilience Example

```python
# Redis connection failure is handled automatically
cache = RedisCache(
    redis_url="redis://invalid-host:6379/0",
    max_retries=3,
    retry_backoff=0.5,
)

# This will retry 3 times with exponential backoff
# If all retries fail, it logs error and cache operations return None
try:
    await cache.connect()
except Exception as e:
    # Connection failed after retries
    # Cache operations will gracefully fail
    pass

# Operations continue to work, just return None on failure
result = await cache.get("key")  # Returns None if disconnected
```

---

## TTL Strategies

### Using Predefined TTL Tiers

```python
from aiops.core.cache import cached, TTLStrategy

# Very short TTL for rapidly changing data
@cached(ttl=TTLStrategy.VERY_SHORT)  # 1 minute
async def get_live_price(symbol: str):
    return await trading_api.get_current_price(symbol)

# Short TTL for frequently updated data
@cached(ttl=TTLStrategy.SHORT)  # 5 minutes
async def get_trending_topics():
    return await api.get_trending()

# Medium TTL for moderately stable data
@cached(ttl=TTLStrategy.MEDIUM)  # 30 minutes
async def get_user_profile(user_id: int):
    return await db.get_user(user_id)

# Long TTL for stable data (default)
@cached(ttl=TTLStrategy.LONG)  # 1 hour
async def get_product_catalog():
    return await db.get_products()

# Very long TTL for rarely changing data
@cached(ttl=TTLStrategy.VERY_LONG)  # 6 hours
async def get_country_list():
    return await db.get_countries()

# Persistent TTL for static data
@cached(ttl=TTLStrategy.PERSISTENT)  # 24 hours
async def get_system_config():
    return await db.get_config()
```

### Using Tier Names

```python
from aiops.core.cache import TTLStrategy

# Get TTL by tier name
very_short = TTLStrategy.get_tier_ttl("very_short")  # 60
short = TTLStrategy.get_tier_ttl("short")            # 300
medium = TTLStrategy.get_tier_ttl("medium")          # 1800
long = TTLStrategy.get_tier_ttl("long")              # 3600
very_long = TTLStrategy.get_tier_ttl("very_long")    # 21600
persistent = TTLStrategy.get_tier_ttl("persistent")  # 86400

# Use in cache operations
cache.set("key", value, ttl=TTLStrategy.get_tier_ttl("short"))
```

### Adaptive TTL Based on Access Patterns

```python
from aiops.core.cache import TTLStrategy

# Simulate access tracking
class SmartCache:
    def __init__(self):
        self.access_counts = {}
        self.cache = get_cache()

    async def get_with_adaptive_ttl(self, key: str, compute_func):
        """Get value with TTL that adapts to access frequency."""
        # Track access
        self.access_counts[key] = self.access_counts.get(key, 0) + 1

        # Check cache
        value = self.cache.get(key)
        if value is not None:
            return value

        # Compute value
        value = await compute_func()

        # Calculate adaptive TTL
        access_count = self.access_counts[key]
        ttl = TTLStrategy.get_adaptive_ttl(access_count, base_ttl=3600)

        # Cache with adaptive TTL
        self.cache.set(key, value, ttl=ttl)

        return value

# Usage
smart_cache = SmartCache()

# First access: TTL = 3600 (base)
value = await smart_cache.get_with_adaptive_ttl("popular_item", fetch_item)

# After 5 accesses: TTL = 3600 (base)
# After 20 accesses: TTL = 5400 (1.5x)
# After 100 accesses: TTL = 7200 (2x)
# After 200 accesses: TTL = 10800 (3x max)
```

---

## Cache Stampede Protection

### What is Cache Stampede?

When a popular cached item expires, multiple requests simultaneously try to regenerate it:

```python
# WITHOUT stampede protection
@cached(ttl=60, enable_stampede_protection=False)
async def expensive_query(id: int):
    await asyncio.sleep(5)  # Simulate 5s database query
    return f"Result for {id}"

# 100 concurrent requests for expired cache
# All 100 requests will execute the 5s query = 500s total wasted time
```

### With Stampede Protection

```python
# WITH stampede protection (default)
@cached(ttl=60, enable_stampede_protection=True)
async def expensive_query(id: int):
    await asyncio.sleep(5)  # Simulate 5s database query
    return f"Result for {id}"

# 100 concurrent requests for expired cache
# Only 1 request executes the query (5s)
# Other 99 requests wait and reuse the result
# Total time: 5s instead of 500s
```

### Real-World Example: LLM API Calls

```python
from aiops.core.cache import cached, TTLStrategy

@cached(ttl=TTLStrategy.MEDIUM, enable_stampede_protection=True)
async def analyze_code_with_llm(code: str, prompt: str):
    """Expensive LLM API call with stampede protection."""
    # This might take 10-30 seconds and cost money
    response = await llm_client.complete(
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": code}
        ]
    )
    return response

# Multiple users analyze the same code simultaneously
# Only ONE API call is made, others wait and reuse result
# Saves time, money, and API quota
tasks = [
    analyze_code_with_llm(same_code, same_prompt)
    for _ in range(50)  # 50 concurrent requests
]
results = await asyncio.gather(*tasks)
# Only 1 LLM API call made, 49 results served from cache
```

### Monitoring Stampede Protection

```python
from aiops.core.cache import get_cache

cache = get_cache()

# Check if stampede protection is enabled
stats = cache.get_stats()
print(f"Stampede protection: {stats['stampede_protection']}")

# The decorator adds logging
# You'll see in logs:
# - "Computing fresh result for ..." (first request)
# - "Waiting for another thread to compute ..." (concurrent requests)
# - "Returning cached result for ..." (subsequent requests)
```

---

## Pattern-Based Invalidation

### Invalidate User Data

```python
from aiops.core.cache import get_cache

cache = get_cache()

# Cache user data
cache.set("user:123:profile", user_profile)
cache.set("user:123:settings", user_settings)
cache.set("user:123:preferences", user_prefs)

# User logs out - invalidate all their data
deleted = cache.delete_pattern("user:123:*")
print(f"Deleted {deleted} cache entries for user 123")
```

### Invalidate by Resource Type

```python
# Cache various resources
cache.set("product:101:details", product_data)
cache.set("product:102:details", product_data)
cache.set("product:101:reviews", reviews)

# Product catalog updated - invalidate all products
deleted = cache.delete_pattern("product:*:details")
print(f"Invalidated {deleted} product caches")
```

### Session Management

```python
# Store session data
cache.set("session:abc123:user", user_id)
cache.set("session:abc123:data", session_data)
cache.set("session:def456:user", user_id)
cache.set("session:def456:data", session_data)

# Clear all sessions for a user (logout from all devices)
deleted = cache.delete_pattern("session:*")
print(f"Cleared {deleted} sessions")
```

### Time-Based Invalidation

```python
from datetime import datetime

# Cache with timestamp in key
timestamp = datetime.now().strftime("%Y%m%d_%H")
cache.set(f"report:hourly:{timestamp}:sales", report_data)

# Clear old hourly reports
cache.delete_pattern("report:hourly:20240101_*")
```

### Async Pattern Deletion

```python
from aiops.cache.redis_cache import get_cache

cache = get_cache()
await cache.connect()

# Async pattern deletion
deleted = await cache.delete_pattern("temp:*")
print(f"Deleted {deleted} temporary keys")

# Clear everything (use with caution!)
deleted = await cache.clear()  # Deletes all keys
```

---

## Health Monitoring

### Check Cache Health

```python
from aiops.core.cache import get_cache

cache = get_cache()
stats = cache.get_stats()

print(f"""
Cache Statistics:
- Backend: {stats['backend']}
- Hit Rate: {stats['hit_rate']}
- Hits: {stats['hits']}
- Misses: {stats['misses']}
- Total Requests: {stats['total']}
- Stampede Protection: {stats['stampede_protection']}
""")

# Check Redis health if using Redis backend
if 'backend_health' in stats:
    health = stats['backend_health']
    print(f"""
Redis Health:
- Status: {health['status']}
- Latency: {health.get('latency_ms', 'N/A')} ms
- Connected Clients: {health.get('connected_clients', 'N/A')}
- Memory Used: {health.get('used_memory_human', 'N/A')}
- Uptime: {health.get('uptime_days', 'N/A')} days
""")
```

### Async Health Monitoring

```python
from aiops.cache.redis_cache import get_cache

cache = get_cache()
await cache.connect()

stats = await cache.get_stats()
print(f"""
Async Cache Statistics:
- Hit Rate: {stats['hit_rate']}
- Total Requests: {stats['total_requests']}
- Connected: {stats['connected']}
- Redis Health: {stats['redis_health']}
- Latency: {stats.get('latency_ms', 'N/A')} ms
""")
```

### Monitoring in FastAPI

```python
from fastapi import APIRouter
from aiops.cache.redis_cache import get_cache

router = APIRouter()

@router.get("/cache/health")
async def cache_health():
    """Health check endpoint for cache."""
    cache = get_cache()

    try:
        stats = await cache.get_stats()
        return {
            "status": "healthy" if stats['connected'] else "degraded",
            "statistics": stats
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@router.get("/cache/stats")
async def cache_stats():
    """Detailed cache statistics."""
    cache = get_cache()
    return await cache.get_stats()
```

### Prometheus Metrics Integration

```python
from prometheus_client import Counter, Histogram, Gauge
from aiops.cache.redis_cache import get_cache

# Define metrics
cache_hits = Counter('cache_hits_total', 'Total cache hits')
cache_misses = Counter('cache_misses_total', 'Total cache misses')
cache_latency = Histogram('cache_latency_seconds', 'Cache operation latency')
cache_connected = Gauge('cache_connected', 'Cache connection status')

async def update_cache_metrics():
    """Periodically update Prometheus metrics."""
    cache = get_cache()
    stats = await cache.get_stats()

    cache_hits._value.set(stats['hits'])
    cache_misses._value.set(stats['misses'])
    cache_connected.set(1 if stats['connected'] else 0)
```

---

## Best Practices

### 1. Choose Appropriate TTL

```python
# ✅ Good: Match TTL to data update frequency
@cached(ttl=TTLStrategy.VERY_SHORT)  # 1 minute
async def get_real_time_stock_price(symbol: str):
    return await market_api.get_price(symbol)

@cached(ttl=TTLStrategy.PERSISTENT)  # 24 hours
async def get_country_codes():
    return await db.get_countries()

# ❌ Bad: Same TTL for all data
@cached(ttl=3600)  # Too long for prices, too short for static data
async def get_data(type: str):
    return await fetch_data(type)
```

### 2. Use Stampede Protection for Expensive Operations

```python
# ✅ Good: Enable for expensive operations
@cached(ttl=300, enable_stampede_protection=True)
async def generate_complex_report(user_id: int):
    # 30-second computation
    return await complex_analytics(user_id)

# ❌ Acceptable: Disable for cheap operations
@cached(ttl=60, enable_stampede_protection=False)
async def get_user_name(user_id: int):
    # 10ms database lookup
    return await db.get_user_name(user_id)
```

### 3. Namespace Your Cache Keys

```python
# ✅ Good: Clear namespacing
cache.set("user:123:profile", data)
cache.set("product:456:details", data)
cache.set("session:abc:data", data)

# ❌ Bad: Flat namespace
cache.set("123", data)  # What is this?
cache.set("data", data)  # Collision risk
```

### 4. Handle Cache Failures Gracefully

```python
# ✅ Good: Fallback on cache failure
async def get_user_data(user_id: int):
    # Try cache first
    cached_data = cache.get(f"user:{user_id}")
    if cached_data:
        return cached_data

    # Fetch from database
    data = await db.get_user(user_id)

    # Try to cache (don't fail if cache is down)
    try:
        cache.set(f"user:{user_id}", data, ttl=3600)
    except Exception as e:
        logger.warning(f"Failed to cache user data: {e}")

    return data

# ❌ Bad: Fail if cache fails
async def get_user_data(user_id: int):
    return cache.get(f"user:{user_id}")  # What if cache is down?
```

### 5. Clean Up Old Cache Entries

```python
# ✅ Good: Regular cleanup
async def cleanup_old_sessions():
    """Run daily to clean up expired sessions."""
    cache = get_cache()

    # Delete old session keys
    deleted = await cache.delete_pattern("session:expired:*")
    logger.info(f"Cleaned up {deleted} expired sessions")

# ❌ Bad: Never clean up, memory grows indefinitely
```

### 6. Monitor Cache Performance

```python
# ✅ Good: Regular monitoring
async def check_cache_health():
    cache = get_cache()
    stats = await cache.get_stats()

    # Alert if hit rate is too low
    hit_rate = float(stats['hit_rate'].rstrip('%'))
    if hit_rate < 50:
        logger.warning(f"Low cache hit rate: {hit_rate}%")

    # Alert if not connected
    if not stats['connected']:
        logger.error("Cache disconnected!")

    return stats
```

### 7. Use Pattern Deletion for Bulk Invalidation

```python
# ✅ Good: Efficient bulk deletion
async def user_updated(user_id: int):
    # Invalidate all user-related caches
    deleted = cache.delete_pattern(f"user:{user_id}:*")
    logger.info(f"Invalidated {deleted} cache entries for user {user_id}")

# ❌ Bad: Individual deletions
async def user_updated(user_id: int):
    cache.delete(f"user:{user_id}:profile")
    cache.delete(f"user:{user_id}:settings")
    cache.delete(f"user:{user_id}:preferences")
    # What if you forget one?
```

### 8. Set Appropriate Connection Pool Size

```python
# ✅ Good: Size based on expected load
redis_cache = RedisCache(
    max_connections=100,  # For high-traffic application
    socket_timeout=5,      # Don't wait too long
)

# ❌ Bad: Default settings for high-traffic
redis_cache = RedisCache()  # Only 10 connections by default
```

---

## Summary

The improved cache system provides:

1. **Reliability**: Auto-reconnection with exponential backoff
2. **Performance**: Stampede protection and connection pooling
3. **Flexibility**: Multiple TTL strategies and adaptive TTL
4. **Maintainability**: Pattern-based invalidation
5. **Observability**: Comprehensive health monitoring

Use these features to build robust, performant caching into your AIOps applications.

"""Semantic caching for LLM requests to reduce redundant API calls."""

import asyncio
import hashlib
import json
import time
import re
from typing import Any, Optional, Dict, List, Tuple
from dataclasses import dataclass
from difflib import SequenceMatcher
from collections import OrderedDict
import threading

from aiops.core.logger import get_logger
from aiops.core.cache import Cache, get_cache

logger = get_logger(__name__)


class AsyncLockWrapper:
    """
    Wrapper that provides both sync and async lock capabilities.

    For sync usage: Use as a regular context manager
    For async usage: Use with async_lock() method
    """

    def __init__(self):
        self._sync_lock = threading.Lock()
        self._async_lock: Optional[asyncio.Lock] = None
        self._async_lock_creation_lock = threading.Lock()

    def __enter__(self):
        self._sync_lock.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._sync_lock.release()
        return False

    async def async_lock(self):
        """Get async lock - creates one per event loop if needed."""
        if self._async_lock is None:
            with self._async_lock_creation_lock:
                if self._async_lock is None:  # Double-check pattern
                    try:
                        # Create async lock in current event loop
                        self._async_lock = asyncio.Lock()
                    except RuntimeError:
                        # No event loop running, use sync lock
                        return self
        return self._async_lock


@dataclass
class SemanticCacheEntry:
    """A cache entry with semantic matching support."""
    key: str
    prompt_hash: str
    prompt_normalized: str
    value: Any
    created_at: float
    access_count: int = 0
    last_accessed: float = 0
    similarity_threshold: float = 0.85
    metadata: Optional[Dict] = None


class SemanticCache:
    """
    Semantic cache that can match similar prompts.

    Features:
    - Exact match caching (fast)
    - Semantic similarity matching (for similar prompts)
    - Configurable similarity threshold
    - LRU eviction with access tracking
    - Size limits and TTL
    - Thread-safe operations

    Example:
        cache = SemanticCache(similarity_threshold=0.9)

        # First call - cache miss
        result = cache.get("Review this Python code: def foo(): pass")

        # Similar call - cache hit
        result = cache.get("Review this Python code: def bar(): pass")
    """

    def __init__(
        self,
        similarity_threshold: float = 0.85,
        max_entries: int = 1000,
        ttl: int = 3600,
        enable_semantic: bool = True,
        normalize_prompts: bool = True,
    ):
        """
        Initialize semantic cache.

        Args:
            similarity_threshold: Minimum similarity ratio (0-1) for semantic match
            max_entries: Maximum number of cached entries
            ttl: Time-to-live in seconds
            enable_semantic: Enable semantic matching (set False for exact only)
            normalize_prompts: Normalize prompts before comparison
        """
        self.similarity_threshold = similarity_threshold
        self.max_entries = max_entries
        self.ttl = ttl
        self.enable_semantic = enable_semantic
        self.normalize_prompts = normalize_prompts

        # Storage using OrderedDict for LRU
        self._cache: OrderedDict[str, SemanticCacheEntry] = OrderedDict()
        self._prompt_index: Dict[str, str] = {}  # normalized_prompt -> cache_key

        # Statistics
        self._stats = {
            "exact_hits": 0,
            "semantic_hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0,
        }

        # Cleanup tracking - run cleanup every 5 minutes (300 seconds)
        self._last_cleanup: float = time.time()
        self._cleanup_interval: float = 300.0  # 5 minutes

        # Use lock wrapper for both sync and async support
        self._lock = AsyncLockWrapper()

        logger.info(
            f"Semantic cache initialized: threshold={similarity_threshold}, "
            f"max_entries={max_entries}, ttl={ttl}s"
        )

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources."""
        # Clear cache on exit to free memory
        self.clear()
        logger.debug("Semantic cache cleared on context exit")
        return False

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup resources."""
        # Same cleanup as sync version
        self.clear()
        logger.debug("Semantic cache cleared on async context exit")
        return False

    def _normalize_prompt(self, prompt: str) -> str:
        """
        Normalize a prompt for comparison.

        Normalizes by:
        - Converting to lowercase
        - Removing extra whitespace
        - Removing common variations
        """
        if not self.normalize_prompts:
            return prompt

        normalized = prompt.lower().strip()
        # Collapse multiple spaces
        normalized = re.sub(r'\s+', ' ', normalized)
        # Remove punctuation variations
        normalized = re.sub(r'[.,!?;:]+', '', normalized)

        return normalized

    def _generate_key(self, prompt: str, model: str = "", **kwargs) -> str:
        """Generate a unique cache key."""
        key_data = {
            "prompt": prompt,
            "model": model,
            **{k: str(v) for k, v in sorted(kwargs.items())},
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_string.encode()).hexdigest()

    def _calculate_similarity(self, s1: str, s2: str) -> float:
        """Calculate similarity ratio between two strings."""
        return SequenceMatcher(None, s1, s2).ratio()

    def _find_semantic_match(
        self,
        normalized_prompt: str,
    ) -> Optional[SemanticCacheEntry]:
        """
        Find a semantically similar cached entry.

        Uses normalized prompt comparison with similarity threshold.
        """
        if not self.enable_semantic:
            return None

        best_match = None
        best_similarity = 0.0

        for entry in self._cache.values():
            # Skip expired entries
            if time.time() - entry.created_at > self.ttl:
                continue

            similarity = self._calculate_similarity(
                normalized_prompt,
                entry.prompt_normalized,
            )

            if similarity >= self.similarity_threshold and similarity > best_similarity:
                best_match = entry
                best_similarity = similarity

        if best_match:
            logger.debug(
                f"Semantic match found with similarity {best_similarity:.2%}"
            )

        return best_match

    def _evict_if_needed(self):
        """Evict oldest entries if cache is full."""
        while len(self._cache) >= self.max_entries:
            # Remove oldest entry (first in OrderedDict)
            oldest_key = next(iter(self._cache))
            # Clean up prompt index to prevent memory leak
            entry = self._cache[oldest_key]
            normalized = entry.prompt_normalized
            if normalized in self._prompt_index:
                del self._prompt_index[normalized]
            del self._cache[oldest_key]
            self._stats["evictions"] += 1
            logger.debug(f"Evicted cache entry: {oldest_key[:16]}...")

    def _cleanup_expired(self):
        """Remove expired entries and clean up prompt index."""
        now = time.time()
        expired_keys = [
            key for key, entry in self._cache.items()
            if now - entry.created_at > self.ttl
        ]

        for key in expired_keys:
            # Clean up prompt index to prevent memory leak
            entry = self._cache[key]
            normalized = entry.prompt_normalized
            if normalized in self._prompt_index:
                del self._prompt_index[normalized]
            del self._cache[key]
            self._stats["expirations"] += 1

    def get(
        self,
        prompt: str,
        model: str = "",
        use_semantic: bool = True,
        **kwargs,
    ) -> Optional[Any]:
        """
        Get a cached value.

        Args:
            prompt: The prompt to look up
            model: Model name for key generation
            use_semantic: Whether to use semantic matching
            **kwargs: Additional key parameters

        Returns:
            Cached value or None if not found
        """
        with self._lock:
            # Clean up expired entries periodically using proper time tracking
            current_time = time.time()
            if len(self._cache) > 0 and (current_time - self._last_cleanup) >= self._cleanup_interval:
                self._cleanup_expired()
                self._last_cleanup = current_time

            # Try exact match first
            key = self._generate_key(prompt, model, **kwargs)
            entry = self._cache.get(key)

            if entry and time.time() - entry.created_at <= self.ttl:
                # Move to end for LRU
                self._cache.move_to_end(key)
                entry.access_count += 1
                entry.last_accessed = time.time()
                self._stats["exact_hits"] += 1
                logger.debug(f"Exact cache hit for key: {key[:16]}...")
                return entry.value

            # Try semantic match if enabled
            if use_semantic and self.enable_semantic:
                normalized = self._normalize_prompt(prompt)
                match = self._find_semantic_match(normalized)

                if match:
                    match.access_count += 1
                    match.last_accessed = time.time()
                    self._cache.move_to_end(match.key)
                    self._stats["semantic_hits"] += 1
                    return match.value

            self._stats["misses"] += 1
            return None

    def set(
        self,
        prompt: str,
        value: Any,
        model: str = "",
        metadata: Optional[Dict] = None,
        **kwargs,
    ):
        """
        Set a cached value.

        Args:
            prompt: The prompt to cache
            value: The value to cache
            model: Model name for key generation
            metadata: Optional metadata to store
            **kwargs: Additional key parameters
        """
        with self._lock:
            self._evict_if_needed()

            key = self._generate_key(prompt, model, **kwargs)
            normalized = self._normalize_prompt(prompt)

            entry = SemanticCacheEntry(
                key=key,
                prompt_hash=hashlib.sha256(prompt.encode()).hexdigest(),
                prompt_normalized=normalized,
                value=value,
                created_at=time.time(),
                last_accessed=time.time(),
                similarity_threshold=self.similarity_threshold,
                metadata=metadata,
            )

            self._cache[key] = entry
            self._prompt_index[normalized] = key

            logger.debug(f"Cached value for key: {key[:16]}...")

    def delete(self, prompt: str, model: str = "", **kwargs):
        """Delete a cached entry."""
        with self._lock:
            key = self._generate_key(prompt, model, **kwargs)
            if key in self._cache:
                # Also clean up the prompt index to prevent memory leak
                entry = self._cache[key]
                normalized = entry.prompt_normalized
                if normalized in self._prompt_index:
                    del self._prompt_index[normalized]
                del self._cache[key]

    def clear(self):
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()
            self._prompt_index.clear()
            self._stats = {
                "exact_hits": 0,
                "semantic_hits": 0,
                "misses": 0,
                "evictions": 0,
                "expirations": 0,
            }
        logger.info("Semantic cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = (
                self._stats["exact_hits"] +
                self._stats["semantic_hits"] +
                self._stats["misses"]
            )

            hit_rate = 0.0
            if total_requests > 0:
                hits = self._stats["exact_hits"] + self._stats["semantic_hits"]
                hit_rate = hits / total_requests * 100

            return {
                "entries": len(self._cache),
                "max_entries": self.max_entries,
                "exact_hits": self._stats["exact_hits"],
                "semantic_hits": self._stats["semantic_hits"],
                "total_hits": self._stats["exact_hits"] + self._stats["semantic_hits"],
                "misses": self._stats["misses"],
                "hit_rate": f"{hit_rate:.2f}%",
                "evictions": self._stats["evictions"],
                "expirations": self._stats["expirations"],
            }

    async def aget(
        self,
        prompt: str,
        model: str = "",
        use_semantic: bool = True,
        **kwargs,
    ) -> Optional[Any]:
        """
        Async version of get() - preferred for async contexts.

        This method uses an async lock to avoid blocking the event loop.
        """
        lock = await self._lock.async_lock()
        async with lock:
            # Clean up expired entries periodically using proper time tracking
            current_time = time.time()
            if len(self._cache) > 0 and (current_time - self._last_cleanup) >= self._cleanup_interval:
                self._cleanup_expired()
                self._last_cleanup = current_time

            # Try exact match first
            key = self._generate_key(prompt, model, **kwargs)
            entry = self._cache.get(key)

            if entry and time.time() - entry.created_at <= self.ttl:
                # Move to end for LRU
                self._cache.move_to_end(key)
                entry.access_count += 1
                entry.last_accessed = time.time()
                self._stats["exact_hits"] += 1
                logger.debug(f"Exact cache hit for key: {key[:16]}...")
                return entry.value

            # Try semantic match if enabled
            if use_semantic and self.enable_semantic:
                normalized = self._normalize_prompt(prompt)
                match = self._find_semantic_match(normalized)

                if match:
                    match.access_count += 1
                    match.last_accessed = time.time()
                    self._cache.move_to_end(match.key)
                    self._stats["semantic_hits"] += 1
                    return match.value

            self._stats["misses"] += 1
            return None

    def _get_sync(
        self,
        prompt: str,
        model: str = "",
        use_semantic: bool = True,
        **kwargs,
    ) -> Optional[Any]:
        """Internal sync get logic."""
        # Clean up expired entries periodically using proper time tracking
        current_time = time.time()
        if len(self._cache) > 0 and (current_time - self._last_cleanup) >= self._cleanup_interval:
            self._cleanup_expired()
            self._last_cleanup = current_time

        # Try exact match first
        key = self._generate_key(prompt, model, **kwargs)
        entry = self._cache.get(key)

        if entry and time.time() - entry.created_at <= self.ttl:
            # Move to end for LRU
            self._cache.move_to_end(key)
            entry.access_count += 1
            entry.last_accessed = time.time()
            self._stats["exact_hits"] += 1
            logger.debug(f"Exact cache hit for key: {key[:16]}...")
            return entry.value

        # Try semantic match if enabled
        if use_semantic and self.enable_semantic:
            normalized = self._normalize_prompt(prompt)
            match = self._find_semantic_match(normalized)

            if match:
                match.access_count += 1
                match.last_accessed = time.time()
                self._cache.move_to_end(match.key)
                self._stats["semantic_hits"] += 1
                return match.value

        self._stats["misses"] += 1
        return None

    async def aset(
        self,
        prompt: str,
        value: Any,
        model: str = "",
        metadata: Optional[Dict] = None,
        **kwargs,
    ):
        """
        Async version of set() - preferred for async contexts.

        This method uses an async lock to avoid blocking the event loop.
        """
        lock = await self._lock.async_lock()
        async with lock:
            self._evict_if_needed()

            key = self._generate_key(prompt, model, **kwargs)
            normalized = self._normalize_prompt(prompt)

            entry = SemanticCacheEntry(
                key=key,
                prompt_hash=hashlib.sha256(prompt.encode()).hexdigest(),
                prompt_normalized=normalized,
                value=value,
                created_at=time.time(),
                last_accessed=time.time(),
                similarity_threshold=self.similarity_threshold,
                metadata=metadata,
            )

            self._cache[key] = entry
            self._prompt_index[normalized] = key

            logger.debug(f"Cached value for key: {key[:16]}...")

    def _set_sync(
        self,
        prompt: str,
        value: Any,
        model: str = "",
        metadata: Optional[Dict] = None,
        **kwargs,
    ):
        """Internal sync set logic."""
        self._evict_if_needed()

        key = self._generate_key(prompt, model, **kwargs)
        normalized = self._normalize_prompt(prompt)

        entry = SemanticCacheEntry(
            key=key,
            prompt_hash=hashlib.sha256(prompt.encode()).hexdigest(),
            prompt_normalized=normalized,
            value=value,
            created_at=time.time(),
            last_accessed=time.time(),
            similarity_threshold=self.similarity_threshold,
            metadata=metadata,
        )

        self._cache[key] = entry
        self._prompt_index[normalized] = key

        logger.debug(f"Cached value for key: {key[:16]}...")


# Global semantic cache instance
_semantic_cache: Optional[SemanticCache] = None


def get_semantic_cache(
    similarity_threshold: float = 0.85,
    **kwargs,
) -> SemanticCache:
    """Get or create global semantic cache instance."""
    global _semantic_cache
    if _semantic_cache is None:
        _semantic_cache = SemanticCache(
            similarity_threshold=similarity_threshold,
            **kwargs,
        )
    return _semantic_cache


def semantic_cached(
    similarity_threshold: float = 0.85,
    ttl: int = 3600,
    model: str = "",
):
    """
    Decorator for caching function results with semantic matching.

    Args:
        similarity_threshold: Minimum similarity for match
        ttl: Time-to-live in seconds
        model: Model name for cache key

    Example:
        @semantic_cached(similarity_threshold=0.9)
        async def analyze_code(prompt: str) -> str:
            # LLM call here
            pass
    """
    from functools import wraps

    cache = get_semantic_cache(similarity_threshold=similarity_threshold, ttl=ttl)

    def decorator(func):
        @wraps(func)
        async def wrapper(prompt: str, *args, **kwargs):
            # Try to get from cache using async method
            cached_result = await cache.aget(prompt, model=model)
            if cached_result is not None:
                return cached_result

            # Call function
            result = await func(prompt, *args, **kwargs)

            # Cache result using async method
            await cache.aset(prompt, result, model=model)

            return result

        wrapper.cache = cache
        wrapper.clear_cache = cache.clear
        wrapper.get_cache_stats = cache.get_stats

        return wrapper

    return decorator


class PromptCompressor:
    """
    Compress prompts to reduce token usage while preserving meaning.

    Techniques:
    - Remove redundant whitespace
    - Shorten common phrases
    - Remove filler words
    """

    # Common phrases that can be shortened
    PHRASE_SHORTCUTS = {
        "please ": "",
        "can you ": "",
        "i would like you to ": "",
        "i want you to ": "",
        "could you please ": "",
        "please help me ": "",
        "i need help with ": "",
    }

    # Words that can be removed without losing meaning
    FILLER_WORDS = {
        "just", "basically", "actually", "really", "very", "quite",
        "simply", "literally", "definitely", "certainly", "obviously",
    }

    @classmethod
    def compress(cls, prompt: str, aggressive: bool = False) -> str:
        """
        Compress a prompt.

        Args:
            prompt: The prompt to compress
            aggressive: Use aggressive compression (may lose some nuance)

        Returns:
            Compressed prompt
        """
        compressed = prompt.lower() if aggressive else prompt

        # Remove redundant whitespace
        compressed = re.sub(r'\s+', ' ', compressed).strip()

        if aggressive:
            # Apply phrase shortcuts
            for phrase, shortcut in cls.PHRASE_SHORTCUTS.items():
                compressed = compressed.replace(phrase, shortcut)

            # Remove filler words
            words = compressed.split()
            words = [w for w in words if w.lower() not in cls.FILLER_WORDS]
            compressed = " ".join(words)

        return compressed

    @classmethod
    def estimate_savings(cls, original: str, compressed: str) -> Dict[str, Any]:
        """Estimate token savings from compression."""
        # Rough token estimate (1 token ~ 4 chars)
        original_tokens = len(original) / 4
        compressed_tokens = len(compressed) / 4
        saved_tokens = original_tokens - compressed_tokens

        return {
            "original_chars": len(original),
            "compressed_chars": len(compressed),
            "char_reduction": f"{(1 - len(compressed)/len(original)) * 100:.1f}%",
            "estimated_tokens_saved": int(saved_tokens),
        }

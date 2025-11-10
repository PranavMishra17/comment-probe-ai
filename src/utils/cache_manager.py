"""
Cache management for embeddings and API responses.

Provides persistent caching to reduce API costs and improve performance.
"""

import logging
import os
import pickle
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Manages caching of embeddings and API responses.

    Uses pickle for persistence. Cache is keyed by text hash.
    """

    def __init__(self, cache_dir: str):
        """
        Initialize cache manager.

        Args:
            cache_dir: Directory for cache files
        """
        self.cache_dir = cache_dir
        self.cache_file = os.path.join(cache_dir, 'embeddings_cache.pkl')
        self.cache: Dict[str, List[float]] = {}
        self.hits = 0
        self.misses = 0

        # Create cache directory
        try:
            os.makedirs(cache_dir, exist_ok=True)
            logger.info(f"[CacheManager] Initialized with cache dir: {cache_dir}")
        except Exception as e:
            logger.error(f"[CacheManager] Failed to create cache directory: {e}")
            raise

        # Load existing cache
        self.load_cache()

    def get_embedding(self, text_hash: str) -> Optional[List[float]]:
        """
        Retrieves cached embedding for text hash.

        Args:
            text_hash: Hash of the text

        Returns:
            Embedding vector if cached, None otherwise
        """
        if text_hash in self.cache:
            self.hits += 1
            logger.debug(f"[CacheManager] Cache hit for hash: {text_hash[:16]}...")
            return self.cache[text_hash]
        else:
            self.misses += 1
            logger.debug(f"[CacheManager] Cache miss for hash: {text_hash[:16]}...")
            return None

    def set_embedding(self, text_hash: str, embedding: List[float]) -> None:
        """
        Stores embedding in cache.

        Args:
            text_hash: Hash of the text
            embedding: Embedding vector
        """
        try:
            self.cache[text_hash] = embedding
            logger.debug(f"[CacheManager] Cached embedding for hash: {text_hash[:16]}...")
        except Exception as e:
            logger.warning(f"[CacheManager] Failed to cache embedding: {e}")

    def save_cache(self) -> None:
        """
        Writes cache to disk.
        """
        logger.info(f"[CacheManager] Saving cache with {len(self.cache)} entries")
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.cache, f)
            logger.info(f"[CacheManager] Cache saved successfully to {self.cache_file}")
        except Exception as e:
            logger.error(f"[CacheManager] Failed to save cache: {e}", exc_info=True)

    def load_cache(self) -> None:
        """
        Loads cache from disk if it exists.
        """
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'rb') as f:
                    self.cache = pickle.load(f)
                logger.info(f"[CacheManager] Loaded cache with {len(self.cache)} entries")
            except Exception as e:
                logger.warning(f"[CacheManager] Failed to load cache, starting fresh: {e}")
                self.cache = {}
        else:
            logger.info("[CacheManager] No existing cache found, starting fresh")
            self.cache = {}

    def clear_cache(self) -> None:
        """
        Removes all cached data.
        """
        logger.info("[CacheManager] Clearing cache")
        self.cache = {}
        if os.path.exists(self.cache_file):
            try:
                os.remove(self.cache_file)
                logger.info("[CacheManager] Cache file deleted")
            except Exception as e:
                logger.warning(f"[CacheManager] Failed to delete cache file: {e}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Returns cache statistics.

        Returns:
            Dictionary with cache metrics
        """
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0.0

        stats = {
            "total_entries": len(self.cache),
            "cache_hits": self.hits,
            "cache_misses": self.misses,
            "hit_rate": round(hit_rate, 3),
            "cache_file": self.cache_file,
            "cache_exists": os.path.exists(self.cache_file)
        }

        # Get cache file size if exists
        if os.path.exists(self.cache_file):
            try:
                size_bytes = os.path.getsize(self.cache_file)
                stats["cache_size_mb"] = round(size_bytes / (1024 * 1024), 2)
            except Exception as e:
                logger.warning(f"[CacheManager] Failed to get cache file size: {e}")
                stats["cache_size_mb"] = 0

        return stats

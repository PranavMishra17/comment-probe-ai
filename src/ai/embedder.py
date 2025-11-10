"""
Embedding generation with caching.

Handles embedding generation for comments with persistent caching.
"""

import logging
from typing import List

from src.core.models import Comment
from src.ai.openai_client import OpenAIClient
from src.utils.cache_manager import CacheManager
from src.utils.helpers import hash_text, batch_list
from src.core.exceptions import EmbeddingError
from config import Config

logger = logging.getLogger(__name__)


class Embedder:
    """
    Handles embedding generation with caching.
    """

    def __init__(self, openai_client: OpenAIClient, cache_manager: CacheManager):
        """
        Initialize embedder.

        Args:
            openai_client: OpenAI client for API calls
            cache_manager: Cache manager for storing embeddings
        """
        self.openai_client = openai_client
        self.cache_manager = cache_manager
        logger.info("[Embedder] Initialized")

    def embed_comments(
        self,
        comments: List[Comment],
        force_refresh: bool = False
    ) -> List[Comment]:
        """
        Generates embeddings for comments.

        Args:
            comments: List of comments to embed
            force_refresh: If True, ignores cache

        Returns:
            Comments with embeddings populated
        """
        logger.info(f"[Embedder] Embedding {len(comments)} comments")

        # Identify comments needing embeddings
        to_embed = []
        for comment in comments:
            if force_refresh or comment.embedding is None:
                text_hash = hash_text(comment.cleaned_content)
                cached = self.cache_manager.get_embedding(text_hash)

                if cached and not force_refresh:
                    comment.embedding = cached
                    logger.debug(f"[Embedder] Using cached embedding for {comment.id}")
                else:
                    to_embed.append(comment)

        logger.info(f"[Embedder] Need to generate {len(to_embed)} new embeddings")

        if not to_embed:
            return comments

        # Batch embeddings
        batches = batch_list(to_embed, Config.EMBEDDING_BATCH_SIZE)
        embedded_count = 0

        for i, batch in enumerate(batches, 1):
            logger.info(f"[Embedder] Processing batch {i}/{len(batches)}")

            try:
                texts = [c.cleaned_content for c in batch]
                embeddings = self.openai_client.create_embedding(texts)

                # Assign embeddings and cache
                for comment, embedding in zip(batch, embeddings):
                    comment.embedding = embedding
                    text_hash = hash_text(comment.cleaned_content)
                    self.cache_manager.set_embedding(text_hash, embedding)
                    embedded_count += 1

            except Exception as e:
                logger.error(f"[Embedder] Failed to embed batch {i}: {e}")
                continue

        # Save cache
        self.cache_manager.save_cache()

        logger.info(f"[Embedder] Embedded {embedded_count} comments successfully")
        return comments

    def embed_text(self, text: str) -> List[float]:
        """
        Embeds single text string.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        text_hash = hash_text(text)
        cached = self.cache_manager.get_embedding(text_hash)

        if cached:
            return cached

        try:
            embeddings = self.openai_client.create_embedding([text])
            embedding = embeddings[0]
            self.cache_manager.set_embedding(text_hash, embedding)
            return embedding
        except Exception as e:
            logger.error(f"[Embedder] Failed to embed text: {e}")
            raise EmbeddingError(f"Failed to embed text: {e}") from e

    def get_embedding_dimension(self) -> int:
        """
        Returns dimension of embedding model.

        Returns:
            Embedding dimension (1536 for text-embedding-3-small)
        """
        return 1536

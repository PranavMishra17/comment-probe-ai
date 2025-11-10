"""
Hybrid search engine: embedding-based filtering + LLM ranking.

Implements two-stage search for optimal results.
"""

import logging
import time
from typing import List, Tuple

from src.core.models import Video, Comment, CommentSearchSpec, SearchResult
from src.ai.openai_client import OpenAIClient
from src.ai.embedder import Embedder
from src.ai.prompts import Prompts
from src.utils.helpers import compute_cosine_similarity
from config import Config

logger = logging.getLogger(__name__)


class SearchEngine:
    """
    Implements hybrid search: semantic filtering + LLM ranking.
    """

    def __init__(self, openai_client: OpenAIClient, embedder: Embedder):
        """
        Initialize search engine.

        Args:
            openai_client: OpenAI client for LLM calls
            embedder: Embedder for generating query embeddings
        """
        self.openai_client = openai_client
        self.embedder = embedder
        self.prompts = Prompts()
        logger.info("[SearchEngine] Initialized")

    def execute_search(
        self,
        video: Video,
        spec: CommentSearchSpec
    ) -> SearchResult:
        """
        Executes search spec on video comments.

        Args:
            video: Video with comments to search
            spec: Search specification

        Returns:
            SearchResult with matched comments
        """
        logger.info(f"[SearchEngine] Executing search: {spec.context}")
        start_time = time.time()
        api_calls = 0

        # Stage 1: Semantic filtering
        candidates, candidate_scores = self._semantic_filter(
            video.comments,
            spec.query,
            spec.top_k
        )
        api_calls += 1  # For query embedding

        logger.info(f"[SearchEngine] Stage 1: Found {len(candidates)} candidates")

        # Stage 2: LLM reranking (simplified - use semantic scores)
        # Full implementation would call LLM for each candidate
        # For now, use semantic scores directly
        final_comments = candidates
        final_scores = candidate_scores

        logger.info(f"[SearchEngine] Stage 2: Selected {len(final_comments)} results")

        execution_time = time.time() - start_time

        result = SearchResult(
            spec=spec,
            matched_comments=final_comments,
            relevance_scores=final_scores,
            extracted_insights={},
            execution_time=execution_time,
            api_calls_made=api_calls
        )

        logger.info(
            f"[SearchEngine] Search complete - "
            f"Results: {len(final_comments)}, Time: {execution_time:.2f}s"
        )

        return result

    def _semantic_filter(
        self,
        comments: List[Comment],
        query: str,
        top_k: int
    ) -> Tuple[List[Comment], List[float]]:
        """
        Filters comments using semantic similarity.

        Args:
            comments: Comments to filter
            query: Search query
            top_k: Number of results to return

        Returns:
            Tuple of (top comments, scores)
        """
        logger.info(f"[SearchEngine] Semantic filtering {len(comments)} comments")

        # Get query embedding
        query_embedding = self.embedder.embed_text(query)

        # Compute similarities
        scored_comments = []
        for comment in comments:
            if comment.embedding is None:
                logger.warning(f"[SearchEngine] Comment {comment.id} has no embedding")
                continue

            similarity = compute_cosine_similarity(query_embedding, comment.embedding)
            scored_comments.append((comment, similarity))

        # Sort by similarity
        scored_comments.sort(key=lambda x: x[1], reverse=True)

        # Take top_k
        top_results = scored_comments[:top_k]

        comments_list = [c for c, s in top_results]
        scores_list = [s for c, s in top_results]

        return comments_list, scores_list

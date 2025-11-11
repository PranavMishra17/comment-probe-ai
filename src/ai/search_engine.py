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
            spec.top_k * 2  # Get more candidates for LLM filtering
        )
        api_calls += 1  # For query embedding

        logger.info(f"[SearchEngine] Stage 1: Found {len(candidates)} candidates")

        # Apply filters from spec
        filtered_candidates = self._apply_filters(candidates, spec)
        logger.info(f"[SearchEngine] After filtering: {len(filtered_candidates)} comments")

        # Stage 2: LLM reranking
        if len(filtered_candidates) > 0:
            final_comments, final_scores, insights, llm_calls = self._llm_rerank(
                filtered_candidates,
                spec
            )
            api_calls += llm_calls
        else:
            final_comments = []
            final_scores = []
            insights = {}

        # Limit to top_k results
        final_comments = final_comments[:spec.top_k]
        final_scores = final_scores[:spec.top_k]

        logger.info(f"[SearchEngine] Stage 2: Selected {len(final_comments)} results")

        execution_time = time.time() - start_time

        result = SearchResult(
            spec=spec,
            matched_comments=final_comments,
            relevance_scores=final_scores,
            extracted_insights=insights,
            execution_time=execution_time,
            api_calls_made=api_calls
        )

        logger.info(
            f"[SearchEngine] Search complete - "
            f"Results: {len(final_comments)}, Time: {execution_time:.2f}s, API calls: {api_calls}"
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

    def _apply_filters(
        self,
        comments: List[Comment],
        spec: CommentSearchSpec
    ) -> List[Comment]:
        """
        Applies filters from search spec to comments.

        Args:
            comments: Comments to filter
            spec: Search specification with filters

        Returns:
            Filtered comments
        """
        if not spec.filters:
            return comments

        filtered = comments

        # Apply min_length filter
        if 'min_length' in spec.filters:
            min_len = spec.filters['min_length']
            filtered = [c for c in filtered if len(c.content) >= min_len]
            logger.info(f"[SearchEngine] After min_length filter: {len(filtered)} comments")

        # Apply exclude_spam filter
        if spec.filters.get('exclude_spam', False):
            filtered = [c for c in filtered if not self._is_spam(c)]
            logger.info(f"[SearchEngine] After spam filter: {len(filtered)} comments")

        # Apply require_question_mark filter
        if spec.filters.get('require_question_mark', False):
            filtered = [c for c in filtered if '?' in c.content]
            logger.info(f"[SearchEngine] After question mark filter: {len(filtered)} comments")

        return filtered

    def _is_spam(self, comment: Comment) -> bool:
        """
        Checks if comment is spam.

        Args:
            comment: Comment to check

        Returns:
            True if spam, False otherwise
        """
        spam_patterns = [
            'http://',
            'https://',
            'bit.ly',
            'click here',
            'subscribe',
            'check out my',
            'visit my channel'
        ]

        content_lower = comment.content.lower()
        return any(pattern in content_lower for pattern in spam_patterns)

    def _llm_rerank(
        self,
        candidates: List[Comment],
        spec: CommentSearchSpec
    ) -> Tuple[List[Comment], List[float], dict, int]:
        """
        Reranks candidates using LLM for better relevance.

        Args:
            candidates: Candidate comments from semantic search
            spec: Search specification

        Returns:
            Tuple of (reranked comments, scores, insights, api_calls)
        """
        logger.info(f"[SearchEngine] LLM reranking {len(candidates)} candidates")

        if len(candidates) == 0:
            return [], [], {}, 0

        # Batch candidates for efficiency
        batch_size = Config.BATCH_SIZE
        all_scores = []
        api_calls = 0

        for i in range(0, len(candidates), batch_size):
            batch = candidates[i:i + batch_size]

            # Build prompt for LLM ranking
            prompt = self._build_ranking_prompt(batch, spec)

            try:
                # Call LLM for ranking
                result = self.openai_client.create_completion(
                    messages=[
                        {"role": "system", "content": "You are a relevance scoring expert."},
                        {"role": "user", "content": prompt}
                    ],
                    model=Config.FAST_COMPLETION_MODEL,
                    temperature=0.1
                )
                response = result.content
                api_calls += 1

                # Parse scores from response
                scores = self._parse_ranking_response(response, len(batch))
                all_scores.extend(scores)

            except Exception as e:
                logger.error(f"[SearchEngine] LLM ranking failed: {e}", exc_info=True)
                # Fallback to semantic scores
                all_scores.extend([0.5] * len(batch))

        # Combine comments with scores and sort
        scored_comments = list(zip(candidates, all_scores))
        scored_comments.sort(key=lambda x: x[1], reverse=True)

        reranked_comments = [c for c, s in scored_comments]
        reranked_scores = [s for c, s in scored_comments]

        # Extract insights if specified
        insights = {}
        if spec.extract_fields:
            insights = self._extract_insights(reranked_comments[:5], spec.extract_fields)

        return reranked_comments, reranked_scores, insights, api_calls

    def _build_ranking_prompt(
        self,
        comments: List[Comment],
        spec: CommentSearchSpec
    ) -> str:
        """
        Builds prompt for LLM ranking.

        Args:
            comments: Comments to rank
            spec: Search specification

        Returns:
            Prompt string
        """
        prompt = f"""Task: Score the relevance of these comments to the search query.

Search Query: {spec.query}
Context: {spec.context}

Score each comment from 0.0 (not relevant) to 1.0 (highly relevant).

Comments:
"""
        for i, comment in enumerate(comments):
            prompt += f"{i+1}. {comment.content[:200]}...\n"

        prompt += "\nReturn ONLY a JSON array of scores (numbers between 0.0 and 1.0), one per comment. Example: [0.8, 0.6, 0.9, 0.3]"

        return prompt

    def _parse_ranking_response(self, response: str, expected_count: int) -> List[float]:
        """
        Parses LLM ranking response into scores.

        Args:
            response: LLM response text
            expected_count: Number of expected scores

        Returns:
            List of relevance scores
        """
        import json
        import re

        try:
            # Try to find JSON array in response
            json_match = re.search(r'\[[\d\.\,\s]+\]', response)
            if json_match:
                scores = json.loads(json_match.group(0))
                if len(scores) == expected_count:
                    return [float(s) for s in scores]
        except:
            pass

        # Fallback: return neutral scores
        logger.warning(f"[SearchEngine] Failed to parse ranking response, using fallback")
        return [0.5] * expected_count

    def _extract_insights(
        self,
        comments: List[Comment],
        fields: List[str]
    ) -> dict:
        """
        Extracts insights from top comments.

        Args:
            comments: Top comments
            fields: Fields to extract

        Returns:
            Dict of insights
        """
        insights = {}

        if 'sentiment' in fields:
            avg_sentiment = sum(getattr(c, 'sentiment', 0.5) for c in comments) / max(len(comments), 1)
            insights['average_sentiment'] = avg_sentiment

        if 'topics' in fields:
            insights['common_themes'] = self._extract_themes(comments)

        if 'suggestions' in fields:
            suggestions = [c.content for c in comments if any(word in c.content.lower() for word in ['should', 'could', 'would', 'suggest'])]
            insights['suggestions'] = suggestions[:3]

        return insights

    def _extract_themes(self, comments: List[Comment]) -> List[str]:
        """
        Extracts common themes from comments.

        Args:
            comments: Comments to analyze

        Returns:
            List of themes
        """
        # Simple keyword extraction
        from collections import Counter
        import re

        words = []
        for comment in comments:
            words.extend(re.findall(r'\b\w{4,}\b', comment.content.lower()))

        # Get most common words (excluding stop words)
        stop_words = {'this', 'that', 'with', 'from', 'have', 'your', 'been', 'more', 'what', 'were', 'there'}
        filtered_words = [w for w in words if w not in stop_words]

        counter = Counter(filtered_words)
        return [word for word, count in counter.most_common(5)]

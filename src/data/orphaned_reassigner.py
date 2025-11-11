"""
Orphaned comment reassignment for recovering lost data.

Provides intelligent reassignment of orphaned comments to videos using:
1. Parent ID pattern matching
2. Semantic similarity clustering
3. Unassigned grouping for remaining comments
"""

import logging
from typing import List, Dict, Tuple, Optional
from collections import Counter

from src.core.models import Comment, Video
from src.ai.embedder import Embedder
from src.utils.helpers import compute_cosine_similarity

logger = logging.getLogger(__name__)


class OrphanedCommentReassigner:
    """
    Intelligently reassigns orphaned comments to videos.

    Uses a 3-pass approach:
    1. Pattern matching on parent IDs
    2. Semantic similarity with threshold
    3. Group remaining as unassigned
    """

    def __init__(
        self,
        embedder: Optional[Embedder] = None,
        similarity_threshold: float = 0.7,
        create_unassigned_video: bool = True
    ):
        """
        Initialize orphaned comment reassigner.

        Args:
            embedder: Embedder instance for semantic matching (required for pass 2)
            similarity_threshold: Minimum cosine similarity for reassignment
            create_unassigned_video: Whether to create virtual video for unassigned
        """
        self.embedder = embedder
        self.similarity_threshold = similarity_threshold
        self.create_unassigned_video = create_unassigned_video

        self.stats = {
            'total_orphaned': 0,
            'recovered_by_pattern': 0,
            'recovered_by_similarity': 0,
            'unassigned': 0,
            'recovery_rate': 0.0
        }

        logger.info("[OrphanedCommentReassigner] Initialized")

    def analyze_parent_ids(self, orphaned: List[Comment]) -> Dict[str, int]:
        """
        Analyzes parent ID patterns in orphaned comments.

        Args:
            orphaned: List of orphaned comments

        Returns:
            Dictionary mapping parent IDs to count
        """
        logger.info(f"[OrphanedCommentReassigner] Analyzing {len(orphaned)} orphaned comments")

        parent_id_counts = Counter(comment.parent_id for comment in orphaned)

        logger.info(f"[OrphanedCommentReassigner] Found {len(parent_id_counts)} unique parent IDs")

        return dict(parent_id_counts)

    def match_by_pattern(
        self,
        orphaned: List[Comment],
        videos: List[Video]
    ) -> Tuple[List[Comment], Dict[str, int]]:
        """
        First pass: Match orphaned comments by parent ID patterns.

        Checks for:
        - Exact matches (case variations)
        - Substring matches
        - URL variations
        - Reply thread patterns

        Args:
            orphaned: List of orphaned comments
            videos: List of known videos

        Returns:
            Tuple of (remaining orphaned, assignments dict)
        """
        logger.info("[OrphanedCommentReassigner] Pass 1: Pattern matching")

        video_ids = {v.id for v in videos}
        video_lookup = {v.id: v for v in videos}

        remaining = []
        assignments = {v.id: 0 for v in videos}

        for comment in orphaned:
            parent_id = comment.parent_id
            matched = False

            # Try exact match (case insensitive)
            parent_id_lower = parent_id.lower()
            for video_id in video_ids:
                if video_id.lower() == parent_id_lower:
                    video_lookup[video_id].add_comment(comment)
                    comment.metadata['reassigned'] = 'pattern_exact'
                    comment.metadata['original_parent_id'] = parent_id
                    assignments[video_id] += 1
                    matched = True
                    break

            if matched:
                continue

            # Try substring match (parent_id contains video_id or vice versa)
            for video_id in video_ids:
                if video_id in parent_id or parent_id in video_id:
                    video_lookup[video_id].add_comment(comment)
                    comment.metadata['reassigned'] = 'pattern_substring'
                    comment.metadata['original_parent_id'] = parent_id
                    assignments[video_id] += 1
                    matched = True
                    break

            if matched:
                continue

            # Try URL extraction (extract video ID from URL)
            if 'watch?v=' in parent_id or 'youtu.be/' in parent_id:
                extracted_id = self._extract_video_id_from_url(parent_id)
                if extracted_id in video_ids:
                    video_lookup[extracted_id].add_comment(comment)
                    comment.metadata['reassigned'] = 'pattern_url'
                    comment.metadata['original_parent_id'] = parent_id
                    assignments[extracted_id] += 1
                    matched = True
                    continue

            if not matched:
                remaining.append(comment)

        recovered = len(orphaned) - len(remaining)
        self.stats['recovered_by_pattern'] = recovered

        logger.info(
            f"[OrphanedCommentReassigner] Pattern matching: "
            f"Recovered {recovered}/{len(orphaned)} comments"
        )

        for video_id, count in assignments.items():
            if count > 0:
                logger.info(f"  - Video {video_id}: +{count} comments")

        return remaining, assignments

    def match_by_similarity(
        self,
        orphaned: List[Comment],
        videos: List[Video]
    ) -> Tuple[List[Comment], Dict[str, List[Tuple[Comment, float]]]]:
        """
        Second pass: Match by semantic similarity.

        Requires embedder to be set. Computes cosine similarity between
        orphaned comments and all comments in each video.

        Args:
            orphaned: List of remaining orphaned comments
            videos: List of videos with embedded comments

        Returns:
            Tuple of (remaining orphaned, assignments dict with scores)
        """
        logger.info("[OrphanedCommentReassigner] Pass 2: Semantic similarity matching")

        if not self.embedder:
            logger.warning(
                "[OrphanedCommentReassigner] No embedder provided, skipping similarity matching"
            )
            return orphaned, {}

        if not orphaned:
            logger.info("[OrphanedCommentReassigner] No orphaned comments remaining")
            return [], {}

        # Embed orphaned comments
        logger.info(f"[OrphanedCommentReassigner] Embedding {len(orphaned)} orphaned comments")
        self.embedder.embed_comments(orphaned)

        remaining = []
        assignments = {v.id: [] for v in videos}

        # Pre-compute video embeddings for efficiency
        video_embeddings = {}
        for video in videos:
            embedded_comments = [c for c in video.comments if c.embedding]
            if embedded_comments:
                video_embeddings[video.id] = {
                    'video': video,
                    'embeddings': [c.embedding for c in embedded_comments],
                    'count': len(embedded_comments)
                }

        logger.info(
            f"[OrphanedCommentReassigner] Processing {len(orphaned)} orphaned comments "
            f"against {len(video_embeddings)} videos with embeddings"
        )

        # Process each orphaned comment with progress tracking
        for idx, comment in enumerate(orphaned, 1):
            if idx % 100 == 0 or idx == len(orphaned):
                logger.info(
                    f"[OrphanedCommentReassigner] Progress: {idx}/{len(orphaned)} "
                    f"({idx/len(orphaned)*100:.1f}%)"
                )

            if not comment.embedding:
                logger.warning(
                    f"[OrphanedCommentReassigner] Comment {comment.id} has no embedding, skipping"
                )
                remaining.append(comment)
                continue

            best_video = None
            best_score = 0.0

            # Compute similarity to each video
            for video_id, video_data in video_embeddings.items():
                # Compute average similarity to this video's comments
                similarities = [
                    compute_cosine_similarity(comment.embedding, emb)
                    for emb in video_data['embeddings']
                ]
                avg_similarity = sum(similarities) / len(similarities)

                if avg_similarity > best_score:
                    best_score = avg_similarity
                    best_video = video_data['video']

            # Assign if above threshold
            if best_video and best_score >= self.similarity_threshold:
                best_video.add_comment(comment)
                comment.metadata['reassigned'] = 'semantic'
                comment.metadata['similarity_score'] = best_score
                comment.metadata['original_parent_id'] = comment.parent_id
                assignments[best_video.id].append((comment, best_score))
            else:
                remaining.append(comment)

        recovered = len(orphaned) - len(remaining)
        self.stats['recovered_by_similarity'] = recovered

        logger.info(
            f"[OrphanedCommentReassigner] Similarity matching: "
            f"Recovered {recovered}/{len(orphaned)} comments"
        )

        for video_id, assigned in assignments.items():
            if assigned:
                avg_score = sum(score for _, score in assigned) / len(assigned)
                logger.info(
                    f"  - Video {video_id}: +{len(assigned)} comments "
                    f"(avg similarity: {avg_score:.3f})"
                )

        return remaining, assignments

    def create_unassigned_group(
        self,
        orphaned: List[Comment]
    ) -> Optional[Video]:
        """
        Third pass: Create virtual video for unassigned comments.

        Args:
            orphaned: List of remaining orphaned comments

        Returns:
            Video object with unassigned comments, or None if disabled
        """
        logger.info("[OrphanedCommentReassigner] Pass 3: Creating unassigned group")

        if not orphaned:
            logger.info("[OrphanedCommentReassigner] No orphaned comments remaining")
            return None

        if not self.create_unassigned_video:
            logger.info(
                f"[OrphanedCommentReassigner] Unassigned video creation disabled, "
                f"{len(orphaned)} comments remain orphaned"
            )
            self.stats['unassigned'] = len(orphaned)
            return None

        # Mark all as unassigned
        for comment in orphaned:
            comment.metadata['reassigned'] = 'unassigned'
            comment.metadata['original_parent_id'] = comment.parent_id

        # Create virtual video
        unassigned_video = Video(
            id="UNASSIGNED",
            url="unassigned://orphaned-comments",
            content="Unassigned Orphaned Comments (No Parent Video Found)",
            author_id="SYSTEM",
            comments=orphaned,
            video_metadata={
                'is_virtual': True,
                'is_unassigned': True,
                'comment_count': len(orphaned)
            }
        )

        self.stats['unassigned'] = len(orphaned)

        logger.info(
            f"[OrphanedCommentReassigner] Created unassigned video with "
            f"{len(orphaned)} comments"
        )

        return unassigned_video

    def reassign_comments(
        self,
        videos: List[Video],
        orphaned: List[Comment]
    ) -> Tuple[List[Video], Dict[str, any]]:
        """
        Main reassignment orchestrator.

        Runs all 3 passes and returns updated videos list.

        Args:
            videos: List of original videos
            orphaned: List of orphaned comments

        Returns:
            Tuple of (updated videos list, stats dict)
        """
        logger.info(
            f"[OrphanedCommentReassigner] Starting reassignment for "
            f"{len(orphaned)} orphaned comments"
        )

        self.stats['total_orphaned'] = len(orphaned)

        if not orphaned:
            logger.info("[OrphanedCommentReassigner] No orphaned comments to reassign")
            return videos, self.stats

        # Analyze parent IDs first
        parent_id_analysis = self.analyze_parent_ids(orphaned)
        logger.info(f"[OrphanedCommentReassigner] Parent ID distribution:")
        for parent_id, count in sorted(
            parent_id_analysis.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]:
            logger.info(f"  - {parent_id}: {count} comments")

        # Pass 1: Pattern matching
        remaining, pattern_assignments = self.match_by_pattern(orphaned, videos)

        # Pass 2: Semantic similarity (if embedder available)
        if self.embedder and remaining:
            remaining, similarity_assignments = self.match_by_similarity(remaining, videos)

        # Pass 3: Unassigned group
        unassigned_video = None
        if remaining:
            unassigned_video = self.create_unassigned_group(remaining)
            if unassigned_video:
                videos.append(unassigned_video)

        # Calculate recovery rate
        total_recovered = (
            self.stats['recovered_by_pattern'] +
            self.stats['recovered_by_similarity']
        )
        self.stats['recovery_rate'] = (
            total_recovered / self.stats['total_orphaned']
            if self.stats['total_orphaned'] > 0
            else 0.0
        )

        logger.info("[OrphanedCommentReassigner] Reassignment complete")
        logger.info(f"  - Total orphaned: {self.stats['total_orphaned']}")
        logger.info(f"  - Recovered by pattern: {self.stats['recovered_by_pattern']}")
        logger.info(f"  - Recovered by similarity: {self.stats['recovered_by_similarity']}")
        logger.info(f"  - Unassigned: {self.stats['unassigned']}")
        logger.info(f"  - Recovery rate: {self.stats['recovery_rate']:.1%}")

        return videos, self.stats

    def _extract_video_id_from_url(self, url: str) -> Optional[str]:
        """
        Extracts YouTube video ID from URL.

        Args:
            url: YouTube URL

        Returns:
            Video ID or None if not found
        """
        try:
            if 'watch?v=' in url:
                start = url.find('watch?v=') + 8
                video_id = url[start:start+11]
                return video_id
            elif 'youtu.be/' in url:
                start = url.find('youtu.be/') + 9
                video_id = url[start:start+11]
                return video_id
        except Exception as e:
            logger.debug(f"[OrphanedCommentReassigner] Failed to extract video ID from {url}: {e}")

        return None

"""
Video discovery and comment grouping.

Identifies which posts are videos vs comments and groups them.
"""

import logging
import re
from typing import List, Tuple, Dict

from src.core.models import Comment, Video
from src.core.exceptions import DiscoveryException, VideoCountMismatchError

logger = logging.getLogger(__name__)


class VideoDiscoverer:
    """
    Identifies which posts are videos vs comments.
    """

    def __init__(self):
        """Initialize video discoverer."""
        logger.info("[VideoDiscoverer] Initialized")

    def discover_videos(self, comments: List[Comment]) -> Tuple[List[Video], List[Comment]]:
        """
        Analyze comments to identify videos and group comments by video.

        Args:
            comments: List of all comments and video posts

        Returns:
            Tuple of (videos list, orphaned comments list)

        Raises:
            VideoCountMismatchError: If != 5 videos found
        """
        logger.info(f"[VideoDiscoverer] Discovering videos from {len(comments)} items")

        # Group by parent_id
        video_map: Dict[str, List[Comment]] = {}
        video_posts: Dict[str, Comment] = {}

        for comment in comments:
            parent_id = comment.parent_id

            # Check if this is a video post (parent_id == id)
            if comment.id == parent_id or self._looks_like_video(comment):
                video_posts[comment.id] = comment
                comment.is_video = True
                if comment.id not in video_map:
                    video_map[comment.id] = []
            else:
                # This is a comment, add to parent's list
                if parent_id not in video_map:
                    video_map[parent_id] = []
                video_map[parent_id].append(comment)

        # Create Video objects
        videos = []
        for video_id, video_post in video_posts.items():
            video_comments = video_map.get(video_id, [])
            metadata = self.extract_video_metadata(video_post)

            video = Video(
                id=video_post.id,
                url=video_post.url,
                content=video_post.content,
                author_id=video_post.author_id,
                comments=video_comments,
                video_metadata=metadata
            )
            videos.append(video)

        # Find orphaned comments (comments without a known video)
        known_video_ids = set(video_posts.keys())
        orphaned = []
        for parent_id, comments_list in video_map.items():
            if parent_id not in known_video_ids:
                orphaned.extend(comments_list)

        logger.info(
            f"[VideoDiscoverer] Found {len(videos)} videos, "
            f"{sum(len(v.comments) for v in videos)} comments, "
            f"{len(orphaned)} orphaned"
        )

        # Validate exactly 5 videos
        if len(videos) != 5:
            error_msg = f"Expected 5 videos, found {len(videos)}"
            logger.error(f"[VideoDiscoverer] {error_msg}")
            raise VideoCountMismatchError(error_msg)

        # Log per-video stats
        for video in videos:
            logger.info(
                f"[VideoDiscoverer] Video {video.id}: "
                f"{len(video.comments)} comments"
            )

        return videos, orphaned

    def validate_discovery(self, videos: List[Video]) -> bool:
        """
        Validates discovery results.

        Args:
            videos: List of discovered videos

        Returns:
            True if valid

        Raises:
            DiscoveryException: If validation fails
        """
        if len(videos) != 5:
            raise VideoCountMismatchError(f"Expected 5 videos, got {len(videos)}")

        for video in videos:
            if len(video.comments) == 0:
                logger.warning(f"[VideoDiscoverer] Video {video.id} has no comments")

        return True

    def extract_video_metadata(self, video: Comment) -> Dict:
        """
        Extracts metadata from video post.

        Args:
            video: Video post comment

        Returns:
            Dictionary of metadata
        """
        metadata = {}

        # Extract video ID from URL
        video_id_match = re.search(r'v=([a-zA-Z0-9_-]+)', video.url)
        if video_id_match:
            metadata['video_id'] = video_id_match.group(1)

        # Use content as title
        metadata['title'] = video.content[:100] if video.content else "Unknown"

        metadata['channel_id'] = video.author_id

        return metadata

    def _looks_like_video(self, comment: Comment) -> bool:
        """
        Heuristics to identify if a comment is actually a video post.

        Args:
            comment: Comment to check

        Returns:
            True if likely a video post
        """
        # Check if parent_id matches id
        if comment.id == comment.parent_id:
            return True

        # Check if URL doesn't have lc parameter (comment anchor)
        if 'lc=' not in comment.url:
            return True

        return False

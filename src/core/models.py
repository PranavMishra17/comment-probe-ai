"""
Data models for the YouTube Comments Analysis System.

All models are pure data containers with validation and serialization methods.
No business logic should be implemented here.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import random


class Comment:
    """
    Represents a single comment or video post.

    Attributes:
        id: Unique identifier for the comment
        url: YouTube URL with comment anchor
        content: Text content of the comment
        author_id: YouTube channel ID of the author
        parent_id: Video ID (same as id for video posts)
        is_video: Whether this is a video post or comment
        cleaned_content: Cleaned version of content
        metadata: Additional fields (likes, replies, etc.)
        embedding: Vector embedding of the content
    """

    def __init__(
        self,
        id: str,
        url: str,
        content: str,
        author_id: str,
        parent_id: str,
        is_video: bool = False,
        cleaned_content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None
    ):
        """Initialize Comment."""
        self.id = id
        self.url = url
        self.content = content
        self.author_id = author_id
        self.parent_id = parent_id
        self.is_video = is_video
        self.cleaned_content = cleaned_content or content
        self.metadata = metadata or {}
        self.embedding = embedding

    def validate(self) -> bool:
        """
        Validates all required fields are present.

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        if not self.id:
            raise ValueError("Comment id is required")
        if not self.content:
            raise ValueError("Comment content is required")
        if not self.parent_id:
            raise ValueError("Comment parent_id is required")
        return True

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts Comment to dictionary for JSON serialization.

        Returns:
            Dictionary representation
        """
        return {
            "id": self.id,
            "url": self.url,
            "content": self.content,
            "author_id": self.author_id,
            "parent_id": self.parent_id,
            "is_video": self.is_video,
            "cleaned_content": self.cleaned_content,
            "metadata": self.metadata,
            "embedding": self.embedding
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Comment':
        """
        Creates Comment from dictionary.

        Args:
            data: Dictionary with comment data

        Returns:
            Comment instance
        """
        return cls(
            id=data['id'],
            url=data['url'],
            content=data['content'],
            author_id=data['author_id'],
            parent_id=data['parent_id'],
            is_video=data.get('is_video', False),
            cleaned_content=data.get('cleaned_content'),
            metadata=data.get('metadata', {}),
            embedding=data.get('embedding')
        )


class CommentSearchSpec:
    """
    Specification for searching comments.

    Attributes:
        query: Natural language search query
        context: Category name (e.g., technical_feedback, content_ideas)
        filters: Dictionary of filter criteria
        extract_fields: Fields to extract (sentiment, topics, etc.)
        is_static: Whether this is a universal or video-specific spec
        rationale: Explanation of why this search is valuable
        top_k: Number of results to return
    """

    def __init__(
        self,
        query: str,
        context: str,
        filters: Optional[Dict[str, Any]] = None,
        extract_fields: Optional[List[str]] = None,
        is_static: bool = False,
        rationale: str = "",
        top_k: int = 30
    ):
        """Initialize CommentSearchSpec."""
        self.query = query
        self.context = context
        self.filters = filters or {}
        self.extract_fields = extract_fields or []
        self.is_static = is_static
        self.rationale = rationale
        self.top_k = top_k

    def validate(self) -> bool:
        """
        Validates spec is properly formed.

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        if not self.query:
            raise ValueError("Search query is required")
        if not self.context:
            raise ValueError("Search context is required")
        if self.top_k <= 0:
            raise ValueError(f"top_k must be positive, got {self.top_k}")
        return True

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts spec to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "query": self.query,
            "context": self.context,
            "filters": self.filters,
            "extract_fields": self.extract_fields,
            "is_static": self.is_static,
            "rationale": self.rationale,
            "top_k": self.top_k
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CommentSearchSpec':
        """
        Creates spec from dictionary.

        Args:
            data: Dictionary with spec data

        Returns:
            CommentSearchSpec instance
        """
        return cls(
            query=data['query'],
            context=data['context'],
            filters=data.get('filters', {}),
            extract_fields=data.get('extract_fields', []),
            is_static=data.get('is_static', False),
            rationale=data.get('rationale', ''),
            top_k=data.get('top_k', 30)
        )


class SearchResult:
    """
    Result of executing a CommentSearchSpec.

    Attributes:
        spec: The spec that was executed
        matched_comments: Comments matching the search
        relevance_scores: Relevance score for each matched comment
        extracted_insights: Insights extracted per extract_fields
        execution_time: Time taken to execute search
        api_calls_made: Number of API calls during search
    """

    def __init__(
        self,
        spec: CommentSearchSpec,
        matched_comments: List[Comment],
        relevance_scores: List[float],
        extracted_insights: Optional[Dict[str, Any]] = None,
        execution_time: float = 0.0,
        api_calls_made: int = 0
    ):
        """Initialize SearchResult."""
        self.spec = spec
        self.matched_comments = matched_comments
        self.relevance_scores = relevance_scores
        self.extracted_insights = extracted_insights or {}
        self.execution_time = execution_time
        self.api_calls_made = api_calls_made

    def get_top_n(self, n: int) -> List[tuple[Comment, float]]:
        """
        Returns top n results by relevance.

        Args:
            n: Number of results to return

        Returns:
            List of (comment, score) tuples
        """
        combined = list(zip(self.matched_comments, self.relevance_scores))
        sorted_results = sorted(combined, key=lambda x: x[1], reverse=True)
        return sorted_results[:n]

    def filter_by_threshold(self, threshold: float) -> 'SearchResult':
        """
        Filters results by relevance threshold.

        Args:
            threshold: Minimum relevance score

        Returns:
            New SearchResult with filtered results
        """
        filtered_comments = []
        filtered_scores = []
        for comment, score in zip(self.matched_comments, self.relevance_scores):
            if score >= threshold:
                filtered_comments.append(comment)
                filtered_scores.append(score)

        return SearchResult(
            spec=self.spec,
            matched_comments=filtered_comments,
            relevance_scores=filtered_scores,
            extracted_insights=self.extracted_insights,
            execution_time=self.execution_time,
            api_calls_made=self.api_calls_made
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts result to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "spec": self.spec.to_dict(),
            "matched_comments": [
                {
                    **comment.to_dict(),
                    "relevance_score": score
                }
                for comment, score in zip(self.matched_comments, self.relevance_scores)
            ],
            "result_count": len(self.matched_comments),
            "extracted_insights": self.extracted_insights,
            "execution_time": self.execution_time,
            "api_calls_made": self.api_calls_made
        }


class TopicCluster:
    """
    Represents a discovered topic cluster.

    Attributes:
        topic_name: LLM-generated label
        comment_count: Number of comments in this cluster
        percentage: Percentage of total comments
        representative_comments: Sample comments from cluster
        keywords: Key terms extracted
    """

    def __init__(
        self,
        topic_name: str,
        comment_count: int,
        percentage: float,
        representative_comments: List[Comment],
        keywords: List[str]
    ):
        """Initialize TopicCluster."""
        self.topic_name = topic_name
        self.comment_count = comment_count
        self.percentage = percentage
        self.representative_comments = representative_comments
        self.keywords = keywords

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts cluster to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "topic_name": self.topic_name,
            "comment_count": self.comment_count,
            "percentage": round(self.percentage, 2),
            "keywords": self.keywords,
            "representative_comments": [
                {
                    "id": comment.id,
                    "content": comment.content,
                    "relevance_score": 0.9  # Placeholder
                }
                for comment in self.representative_comments[:3]
            ]
        }


class Question:
    """
    Represents an identified question from comments.

    Attributes:
        comment: The comment containing the question
        question_text: Extracted question
        engagement_score: Likes + replies weighted
        is_answered: Whether creator responded
        category: Question category (technical, usage, pricing, etc.)
        relevance_score: LLM-determined relevance
    """

    def __init__(
        self,
        comment: Comment,
        question_text: str,
        engagement_score: float,
        is_answered: bool,
        category: str,
        relevance_score: float
    ):
        """Initialize Question."""
        self.comment = comment
        self.question_text = question_text
        self.engagement_score = engagement_score
        self.is_answered = is_answered
        self.category = category
        self.relevance_score = relevance_score

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts question to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "question_text": self.question_text,
            "engagement_score": round(self.engagement_score, 2),
            "is_answered": self.is_answered,
            "category": self.category,
            "relevance_score": round(self.relevance_score, 2),
            "comment": {
                "id": self.comment.id,
                "content": self.comment.content,
                "author_id": self.comment.author_id
            }
        }


class Video:
    """
    Represents a discovered video with its associated comments.

    Attributes:
        id: Video ID
        url: Video URL
        content: Video title/description
        author_id: Channel ID
        comments: All comments for this video
        video_metadata: Channel name, video title, etc.
        dynamic_search_specs: Video-specific search specs
        static_search_specs: Universal search specs
    """

    def __init__(
        self,
        id: str,
        url: str,
        content: str,
        author_id: str,
        comments: Optional[List[Comment]] = None,
        video_metadata: Optional[Dict[str, Any]] = None,
        dynamic_search_specs: Optional[List[CommentSearchSpec]] = None,
        static_search_specs: Optional[List[CommentSearchSpec]] = None
    ):
        """Initialize Video."""
        self.id = id
        self.url = url
        self.content = content
        self.author_id = author_id
        self.comments = comments or []
        self.video_metadata = video_metadata or {}
        self.dynamic_search_specs = dynamic_search_specs or []
        self.static_search_specs = static_search_specs or []

    def add_comment(self, comment: Comment) -> None:
        """
        Adds comment to this video.

        Args:
            comment: Comment to add
        """
        self.comments.append(comment)

    def get_comment_count(self) -> int:
        """
        Returns total number of comments.

        Returns:
            Comment count
        """
        return len(self.comments)

    def get_sample_comments(self, n: int) -> List[Comment]:
        """
        Returns n random comments for analysis.

        Args:
            n: Number of comments to sample

        Returns:
            List of sampled comments
        """
        if len(self.comments) <= n:
            return self.comments.copy()
        return random.sample(self.comments, n)

    def validate(self) -> bool:
        """
        Ensures video has required data.

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        if not self.id:
            raise ValueError("Video id is required")
        if not self.content:
            raise ValueError("Video content is required")
        return True

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts video to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "video_id": self.id,
            "url": self.url,
            "title": self.content,
            "author_id": self.author_id,
            "comment_count": len(self.comments),
            "video_metadata": self.video_metadata
        }


class AnalyticsResult:
    """
    Container for all analytics results for a video.

    Attributes:
        video_id: Video ID
        sentiment_score: Overall sentiment (0-1 scale)
        sentiment_distribution: Breakdown of positive/neutral/negative
        top_topics: 5 most common topics
        top_questions: 5 most popular questions
        search_results: Results from all CommentSearchSpecs
        metadata: Processing time, comment count, etc.
    """

    def __init__(
        self,
        video_id: str,
        sentiment_score: float,
        sentiment_distribution: Dict[str, int],
        top_topics: List[TopicCluster],
        top_questions: List[Question],
        search_results: List[SearchResult],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Initialize AnalyticsResult."""
        self.video_id = video_id
        self.sentiment_score = sentiment_score
        self.sentiment_distribution = sentiment_distribution
        self.top_topics = top_topics
        self.top_questions = top_questions
        self.search_results = search_results
        self.metadata = metadata or {}

    def validate(self) -> bool:
        """
        Ensures all required analytics are present.

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        if not self.video_id:
            raise ValueError("Video ID is required")
        if self.sentiment_score < 0 or self.sentiment_score > 1:
            raise ValueError(f"Sentiment score must be 0-1, got {self.sentiment_score}")
        return True

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts analytics to dictionary for JSON output.

        Returns:
            Dictionary representation
        """
        # Separate static and dynamic search results
        static_results = [sr for sr in self.search_results if sr.spec.is_static]
        dynamic_results = [sr for sr in self.search_results if not sr.spec.is_static]

        return {
            "sentiment": {
                "overall_score": round(self.sentiment_score, 2),
                "distribution": self.sentiment_distribution,
                "confidence": self.metadata.get('sentiment_confidence', 0.0)
            },
            "topics": [topic.to_dict() for topic in self.top_topics],
            "questions": [question.to_dict() for question in self.top_questions],
            "search_results": {
                "static_searches": [sr.to_dict() for sr in static_results],
                "dynamic_searches": [sr.to_dict() for sr in dynamic_results]
            }
        }


class ProcessingMetadata:
    """
    Metadata about a complete processing run.

    Attributes:
        run_id: Unique identifier (timestamp-based)
        start_time: When processing started
        end_time: When processing ended
        total_duration: Total processing time in seconds
        input_file: Path to input CSV
        videos_processed: Number of videos analyzed
        total_comments: Total number of comments
        api_calls_made: Total API calls
        api_cost_estimate: Estimated cost in USD
        errors_encountered: List of errors
        warnings: List of warnings
    """

    def __init__(
        self,
        run_id: str,
        start_time: datetime,
        input_file: str,
        end_time: Optional[datetime] = None,
        total_duration: float = 0.0,
        videos_processed: int = 0,
        total_comments: int = 0,
        api_calls_made: int = 0,
        api_cost_estimate: float = 0.0,
        errors_encountered: Optional[List[Dict[str, Any]]] = None,
        warnings: Optional[List[Dict[str, Any]]] = None
    ):
        """Initialize ProcessingMetadata."""
        self.run_id = run_id
        self.start_time = start_time
        self.end_time = end_time
        self.total_duration = total_duration
        self.input_file = input_file
        self.videos_processed = videos_processed
        self.total_comments = total_comments
        self.api_calls_made = api_calls_made
        self.api_cost_estimate = api_cost_estimate
        self.errors_encountered = errors_encountered or []
        self.warnings = warnings or []

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts metadata to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "run_id": self.run_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_duration_seconds": round(self.total_duration, 2),
            "input_file": self.input_file,
            "videos_processed": self.videos_processed,
            "total_comments": self.total_comments,
            "api_calls_made": self.api_calls_made,
            "api_cost_estimate": round(self.api_cost_estimate, 2),
            "errors": self.errors_encountered,
            "warnings": self.warnings
        }

    def save(self, path: str) -> None:
        """
        Saves metadata to JSON file.

        Args:
            path: Path to save metadata
        """
        import json
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

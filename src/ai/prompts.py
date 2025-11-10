"""
Centralized prompt templates for all LLM operations.

All prompts are defined as constants with formatting methods.
"""

from typing import List
from src.core.models import Comment, Video, CommentSearchSpec


class Prompts:
    """
    Prompt templates for various AI operations.
    """

    HYPOTHESIS_GENERATION_PROMPT = """You are analyzing a YouTube video to help the creator understand their audience.

Video Information:
Title: {video_title}
Author: {author_id}
Total Comments: {comment_count}

Sample Comments:
{sample_comments}

Generate 5 CommentSearchSpec objects that identify the most valuable comment categories for this creator.

Focus on:
- Actionable feedback and suggestions
- Common user pain points or questions
- Feature requests or improvement ideas
- Technical issues or concerns
- Audience interests and preferences

Output as JSON array with structure:
[
  {{
    "query": "natural language search query",
    "context": "category_name",
    "filters": {{}},
    "extract_fields": ["sentiment", "topics", "suggestions"],
    "rationale": "why this search is valuable for the creator"
  }}
]
"""

    COMMENT_RELEVANCE_PROMPT = """Score the relevance of this comment to the search query on a scale of 0-1.

Search Query: {query}
Context: {context}

Comment: {comment}

Respond with ONLY a number between 0 and 1, where:

Score:"""

        SENTIMENT_ANALYSIS_PROMPT = """Analyze the sentiment of these comments on a scale of 0-1.
    0 = Very negative, 0.5 = Neutral, 1 = Very positive

    Comments:
    {comments}

    Output ONLY a JSON array with one score per comment, nothing else:
    [0.8, 0.3, 0.9]"""

    TOPIC_LABELING_PROMPT = """Given these representative comments from a cluster, generate a concise topic label (2-4 words) and 3-5 keywords.

Comments:
{comments}

Respond with JSON:
{{
  "topic_name": "Concise Topic Label",
  "keywords": ["keyword1", "keyword2", "keyword3"]
}}"""

    QUESTION_VALIDATION_PROMPT = """Determine if this is a substantive question and categorize it.

Text: {question_text}

Is this a real, substantive question? If yes, categorize it.

Categories: technical, usage, pricing, feature_request, comparison, troubleshooting, other

Respond with JSON:
{{
  "is_substantive": true/false,
  "category": "category_name",
  "relevance_score": 0.0-1.0
}}"""

    @staticmethod
    def format_hypothesis_prompt(video: Video, samples: List[Comment]) -> str:
        """Format prompt for hypothesis generation."""
        sample_text = "\n".join([
            f"{i+1}. {comment.cleaned_content[:200]}"
            for i, comment in enumerate(samples[:10])
        ])

        return Prompts.HYPOTHESIS_GENERATION_PROMPT.format(
            video_title=video.content,
            author_id=video.author_id,
            comment_count=len(video.comments),
            sample_comments=sample_text
        )

    @staticmethod
    def format_relevance_prompt(comment: Comment, spec: CommentSearchSpec) -> str:
        """Format prompt for relevance scoring."""
        return Prompts.COMMENT_RELEVANCE_PROMPT.format(
            query=spec.query,
            context=spec.context,
            comment=comment.cleaned_content[:500]
        )

    @staticmethod
    def format_sentiment_prompt(comments: List[Comment]) -> str:
        """Format prompt for sentiment analysis."""
        comment_text = "\n".join([
            f"{i+1}. {comment.cleaned_content[:200]}"
            for i, comment in enumerate(comments)
        ])

        return Prompts.SENTIMENT_ANALYSIS_PROMPT.format(
            comments=comment_text
        )

    @staticmethod
    def format_topic_prompt(cluster_comments: List[Comment]) -> str:
        """Format prompt for topic labeling."""
        comment_text = "\n".join([
            f"- {comment.cleaned_content[:150]}"
            for comment in cluster_comments[:7]
        ])

        return Prompts.TOPIC_LABELING_PROMPT.format(
            comments=comment_text
        )

    @staticmethod
    def format_question_prompt(question_text: str) -> str:
        """Format prompt for question validation."""
        return Prompts.QUESTION_VALIDATION_PROMPT.format(
            question_text=question_text
        )

"""
Miscellaneous utility functions for the YouTube Comments Analysis System.

Provides general-purpose helper functions used across the codebase.
"""

import hashlib
import json
import math
from datetime import datetime
from typing import List, Any


def generate_run_id() -> str:
    """
    Creates timestamp-based unique ID for a processing run.

    Returns:
        Unique run ID in format YYYYMMDD_HHMMSS_microseconds
    """
    now = datetime.utcnow()
    return now.strftime("%Y%m%d_%H%M%S_") + str(now.microsecond)


def compute_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Computes cosine similarity between two vectors.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Cosine similarity score between -1 and 1
    """
    if len(vec1) != len(vec2):
        raise ValueError(f"Vectors must have same length: {len(vec1)} vs {len(vec2)}")

    # Compute dot product
    dot_product = sum(a * b for a, b in zip(vec1, vec2))

    # Compute magnitudes
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(b * b for b in vec2))

    # Avoid division by zero
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0

    return dot_product / (magnitude1 * magnitude2)


def hash_text(text: str) -> str:
    """
    Creates SHA256 hash of text for use as cache key.

    Args:
        text: Text to hash

    Returns:
        Hexadecimal hash string
    """
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def batch_list(items: List[Any], batch_size: int) -> List[List[Any]]:
    """
    Splits list into batches of specified size.

    Args:
        items: List to batch
        batch_size: Size of each batch

    Returns:
        List of batches
    """
    if batch_size <= 0:
        raise ValueError(f"Batch size must be positive, got {batch_size}")

    batches = []
    for i in range(0, len(items), batch_size):
        batches.append(items[i:i + batch_size])
    return batches


def safe_json_dumps(obj: Any, indent: int = 2) -> str:
    """
    Safely serializes objects to JSON, handling non-serializable types.

    Args:
        obj: Object to serialize
        indent: JSON indentation level

    Returns:
        JSON string
    """
    def default_handler(o):
        """Handler for non-serializable types."""
        if isinstance(o, datetime):
            return o.isoformat()
        if hasattr(o, 'to_dict'):
            return o.to_dict()
        if hasattr(o, '__dict__'):
            return o.__dict__
        return str(o)

    try:
        return json.dumps(obj, indent=indent, default=default_handler)
    except Exception as e:
        # Fallback: convert to string
        return json.dumps({"error": f"Serialization failed: {e}", "value": str(obj)})


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncates text to maximum length with ellipsis.

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add when truncated

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def estimate_tokens(text: str) -> int:
    """
    Estimates token count for text (rough approximation).

    Uses simple heuristic: ~4 characters per token on average for English.

    Args:
        text: Text to estimate

    Returns:
        Estimated token count
    """
    # Simple estimation: 1 token ~= 4 characters
    return max(1, len(text) // 4)


def format_duration(seconds: float) -> str:
    """
    Formats duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string like "2m 34s" or "1h 23m"
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def validate_url(url: str) -> bool:
    """
    Validates if string is a valid YouTube URL.

    Args:
        url: URL to validate

    Returns:
        True if valid YouTube URL
    """
    if not url:
        return False
    return 'youtube.com' in url or 'youtu.be' in url

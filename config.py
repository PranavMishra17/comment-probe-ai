"""
Configuration management for YouTube Comments Analysis System.

Loads all configuration values from environment variables with defaults.
No hardcoded values allowed.
"""

import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class ConfigException(Exception):
    """Exception raised for configuration errors."""
    pass


class Config:
    """
    Configuration manager that loads all settings from environment variables.

    All configuration values are loaded from environment variables with sensible
    defaults where appropriate. API keys must be provided via environment.
    """

    # API Configuration
    OPENAI_API_KEY: str = os.getenv('OPENAI_API_KEY', '')
    OPENAI_ORG_ID: Optional[str] = os.getenv('OPENAI_ORG_ID')
    API_TIMEOUT: int = int(os.getenv('API_TIMEOUT', '60'))
    MAX_RETRIES: int = int(os.getenv('MAX_RETRIES', '3'))
    RETRY_DELAY: int = int(os.getenv('RETRY_DELAY', '1'))
    REQUESTS_PER_MINUTE: int = int(os.getenv('REQUESTS_PER_MINUTE', '60'))
    TOKENS_PER_MINUTE: int = int(os.getenv('TOKENS_PER_MINUTE', '150000'))

    # Model Configuration
    COMPLETION_MODEL: str = os.getenv('COMPLETION_MODEL', 'gpt-4-turbo')
    FAST_COMPLETION_MODEL: str = os.getenv('FAST_COMPLETION_MODEL', 'gpt-3.5-turbo')
    EMBEDDING_MODEL: str = os.getenv('EMBEDDING_MODEL', 'text-embedding-3-small')
    COMPLETION_TEMPERATURE: float = float(os.getenv('COMPLETION_TEMPERATURE', '0.7'))
    COMPLETION_MAX_TOKENS: int = int(os.getenv('COMPLETION_MAX_TOKENS', '1000'))

    # Processing Configuration
    BATCH_SIZE: int = int(os.getenv('BATCH_SIZE', '20'))
    EMBEDDING_BATCH_SIZE: int = int(os.getenv('EMBEDDING_BATCH_SIZE', '100'))
    SEMANTIC_SEARCH_TOP_K: int = int(os.getenv('SEMANTIC_SEARCH_TOP_K', '30'))
    NUM_DYNAMIC_SPECS: int = int(os.getenv('NUM_DYNAMIC_SPECS', '5'))
    NUM_TOPICS: int = int(os.getenv('NUM_TOPICS', '5'))
    NUM_QUESTIONS: int = int(os.getenv('NUM_QUESTIONS', '5'))
    SAMPLE_COMMENTS_FOR_HYPOTHESIS: int = int(os.getenv('SAMPLE_COMMENTS_FOR_HYPOTHESIS', '10'))
    MIN_COMMENT_LENGTH: int = int(os.getenv('MIN_COMMENT_LENGTH', '10'))
    ENABLE_CACHING: bool = os.getenv('ENABLE_CACHING', 'true').lower() == 'true'
    CACHE_DIR: str = os.getenv('CACHE_DIR', './cache')

    # Output Configuration
    OUTPUT_BASE_DIR: str = os.getenv('OUTPUT_BASE_DIR', './output')
    RESULTS_FILENAME: str = os.getenv('RESULTS_FILENAME', 'results.json')
    METADATA_FILENAME: str = os.getenv('METADATA_FILENAME', 'metadata.json')
    VISUALIZATION_FILENAME: str = os.getenv('VISUALIZATION_FILENAME', 'index.html')
    ENABLE_VISUALIZATION: bool = os.getenv('ENABLE_VISUALIZATION', 'true').lower() == 'true'

    # Logging Configuration
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_TO_CONSOLE: bool = os.getenv('LOG_TO_CONSOLE', 'true').lower() == 'true'
    LOG_TO_FILE: bool = os.getenv('LOG_TO_FILE', 'true').lower() == 'true'
    LOG_FORMAT: str = os.getenv('LOG_FORMAT', '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s')

    # Static Search Specs - Universal for all videos
    STATIC_SEARCH_SPECS = [
        {
            "query": "Find highly engaged comments in the top 10% by likes and replies that provide constructive feedback, suggestions, or detailed experiences",
            "context": "community_validated_feedback",
            "filters": {
                "min_length": 50,
                "exclude_spam": True
            },
            "extract_fields": ["sentiment", "suggestions"],
            "is_static": True,
            "rationale": "Community engagement signals important feedback that resonates with audience",
            "top_k": 30
        },
        {
            "query": "Identify substantive unanswered questions that could inspire follow-up content or address gaps in the original video",
            "context": "content_gap_questions",
            "filters": {
                "require_question_mark": True,
                "min_length": 20
            },
            "extract_fields": ["topics", "question_category"],
            "is_static": True,
            "rationale": "Unanswered questions reveal audience needs and potential content opportunities",
            "top_k": 30
        }
    ]

    @classmethod
    def validate(cls) -> bool:
        """
        Validates all required configuration fields are present and valid.

        Returns:
            True if configuration is valid

        Raises:
            ConfigException: If required fields are missing or invalid
        """
        # Check required fields
        if not cls.OPENAI_API_KEY:
            raise ConfigException("OPENAI_API_KEY is required but not set")

        if not cls.OPENAI_API_KEY.startswith('sk-'):
            raise ConfigException("OPENAI_API_KEY appears to be invalid (should start with 'sk-')")

        # Validate ranges
        if cls.BATCH_SIZE <= 0:
            raise ConfigException(f"BATCH_SIZE must be positive, got {cls.BATCH_SIZE}")

        if cls.EMBEDDING_BATCH_SIZE <= 0:
            raise ConfigException(f"EMBEDDING_BATCH_SIZE must be positive, got {cls.EMBEDDING_BATCH_SIZE}")

        if cls.SEMANTIC_SEARCH_TOP_K <= 0:
            raise ConfigException(f"SEMANTIC_SEARCH_TOP_K must be positive, got {cls.SEMANTIC_SEARCH_TOP_K}")

        if cls.NUM_DYNAMIC_SPECS <= 0:
            raise ConfigException(f"NUM_DYNAMIC_SPECS must be positive, got {cls.NUM_DYNAMIC_SPECS}")

        if cls.NUM_TOPICS <= 0:
            raise ConfigException(f"NUM_TOPICS must be positive, got {cls.NUM_TOPICS}")

        if cls.NUM_QUESTIONS <= 0:
            raise ConfigException(f"NUM_QUESTIONS must be positive, got {cls.NUM_QUESTIONS}")

        if cls.COMPLETION_TEMPERATURE < 0 or cls.COMPLETION_TEMPERATURE > 2:
            raise ConfigException(f"COMPLETION_TEMPERATURE must be between 0 and 2, got {cls.COMPLETION_TEMPERATURE}")

        if cls.MAX_RETRIES < 0:
            raise ConfigException(f"MAX_RETRIES must be non-negative, got {cls.MAX_RETRIES}")

        if cls.API_TIMEOUT <= 0:
            raise ConfigException(f"API_TIMEOUT must be positive, got {cls.API_TIMEOUT}")

        return True

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """
        Gets configuration value by key.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        return getattr(cls, key, default)

    @classmethod
    def to_dict(cls, sanitize: bool = True) -> Dict[str, Any]:
        """
        Exports configuration as dictionary.

        Args:
            sanitize: If True, masks sensitive values like API keys

        Returns:
            Dictionary of configuration values
        """
        config_dict = {}
        for key in dir(cls):
            if key.isupper() and not key.startswith('_'):
                value = getattr(cls, key)
                if sanitize and 'KEY' in key and isinstance(value, str):
                    # Mask API keys
                    config_dict[key] = value[:7] + '...' if value else None
                else:
                    config_dict[key] = value
        return config_dict

"""
Custom exception classes for the YouTube Comments Analysis System.

Provides a hierarchical exception structure for different types of errors
that can occur during processing.
"""


class AppException(Exception):
    """Base exception for all application errors."""
    pass


# Data-related exceptions
class DataException(AppException):
    """Base exception for data-related errors."""
    pass


class FileNotFoundError(DataException):
    """Exception raised when a required file is not found."""
    pass


class CSVParsingError(DataException):
    """Exception raised when CSV file cannot be parsed."""
    pass


class ValidationError(DataException):
    """Exception raised when data validation fails."""
    pass


class DataCleaningError(DataException):
    """Exception raised when data cleaning operations fail."""
    pass


# Discovery-related exceptions
class DiscoveryException(AppException):
    """Base exception for video discovery errors."""
    pass


class VideoCountMismatchError(DiscoveryException):
    """Exception raised when discovered video count does not match expected."""
    pass


class OrphanedCommentsError(DiscoveryException):
    """Exception raised when comments cannot be assigned to any video."""
    pass


# AI/API-related exceptions
class AIException(AppException):
    """Base exception for AI and API-related errors."""
    pass


class APIKeyError(AIException):
    """Exception raised when API key is invalid or missing."""
    pass


class RateLimitError(AIException):
    """Exception raised when API rate limits are exceeded."""
    pass


class APIConnectionError(AIException):
    """Exception raised when API connection fails."""
    pass


class InvalidResponseError(AIException):
    """Exception raised when API returns invalid response."""
    pass


class EmbeddingError(AIException):
    """Exception raised when embedding generation fails."""
    pass


# Analytics-related exceptions
class AnalyticsException(AppException):
    """Base exception for analytics errors."""
    pass


class SentimentAnalysisError(AnalyticsException):
    """Exception raised when sentiment analysis fails."""
    pass


class TopicExtractionError(AnalyticsException):
    """Exception raised when topic extraction fails."""
    pass


class QuestionFinderError(AnalyticsException):
    """Exception raised when question finding fails."""
    pass


# Output-related exceptions
class OutputException(AppException):
    """Base exception for output generation errors."""
    pass


class DirectoryCreationError(OutputException):
    """Exception raised when output directory cannot be created."""
    pass


class FileWriteError(OutputException):
    """Exception raised when output file cannot be written."""
    pass


class VisualizationError(OutputException):
    """Exception raised when visualization generation fails."""
    pass

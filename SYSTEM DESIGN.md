# System Design Document: YouTube Comments Analysis System

## TABLE OF CONTENTS
1. [Project Context](#1-project-context)
2. [System Architecture](#2-system-architecture)
3. [Core Components Design](#3-core-components-design)
4. [Workflow and Data Flow](#4-workflow-and-data-flow)
5. [Error Handling Strategy](#5-error-handling-strategy)
6. [Logging and Monitoring](#6-logging-and-monitoring)
7. [Configuration Management](#7-configuration-management)
8. [Output Structure](#8-output-structure)
9. [API Integration](#9-api-integration)
10. [Testing Strategy](#10-testing-strategy)

---

## 1. PROJECT CONTEXT

### 1.1 DATA STRUCTURE

**CSV Input Format:**
```
Columns:
- id: string (unique comment/video identifier)
- url: string (YouTube URL with comment anchor)
- content: string (text content)
- author_id: string (YouTube channel ID)
- parent_id: string (video ID for comments, self-reference for videos)
```

**Dataset Characteristics:**
- 5 YouTube videos mixed with their comments
- Flat structure with no hierarchy preserved
- Variable content lengths
- Potential data quality issues: encoding errors, null values, duplicates

**Example Data:**
```
id: UgzcgekGRhEoJI-Anbt4AaABAg
url: https://www.youtube.com/watch?v=FqIMu4C87SM&lc=UgzcgekGRhEoJI-Anbt4AaABAg
content: Thanks for the video. I will be getting a new laptop soon...
author_id: UC_8zGnzW2DBlQ672fMxPJIA
parent_id: FqIMu4C87SM
```

### 1.2 ORIGINAL TASK REQUIREMENTS

**Scored Tasks:**
- [1pt] Task 1: Discover which posts are videos
- [5pt] Task 2: Dynamic hypothesis generation for comment categories
- [2pt] Task 3: Two static CommentSearchSpecs for all videos
- [1pt] Task 4: Data cleaning and preprocessing
- [10pt] Task 5: Search execution algorithm
- [2pt] Task 6.1: Overall sentiment analysis (0-1 scale)
- [5pt] Task 6.2: Top 5 common topics per video
- [5pt] Task 6.3: Top 5 popular questions per video
- [5pt] Task 7: Web visualization

**Total Points:** 36

**Deliverables:**
- `output/run-{unique-run-id}/results.json`
- `output/run-{unique-run-id}/visualization/index.html`
- Comprehensive logging in `logs/` directory
- Easy setup via README with single command

**Technical Constraints:**
- Use OpenAI API for all LLM tasks
- No hardcoded API keys (use environment variables)
- Graceful error handling for all API calls
- Cost-conscious API usage with caching
- Results must be reproducible

---

## 2. SYSTEM ARCHITECTURE

### 2.1 HIGH-LEVEL ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────┐
│                     Flask Application Layer                      │
│  ┌──────────┐  ┌─────────────┐  ┌────────────────────────────┐ │
│  │  Routes  │──│ Orchestrator│──│     Output Manager         │ │
│  │          │  │             │  │                            │ │
│  │ /analyze │  │  Workflow   │  │  Results + Visualization   │ │
│  │ /status  │  │  Control    │  │  Generation                │ │
│  │ /results │  │             │  │                            │ │
│  └──────────┘  └──────┬──────┘  └────────┬───────────────────┘ │
└────────────────────────┼──────────────────┼─────────────────────┘
                         │                  │
         ┌───────────────┴──────────────────┴───────────────┐
         │           Processing Layer                        │
         │                                                    │
┌────────▼───────────┐  ┌──────────────┐  ┌────────────────▼─────┐
│  Data Pipeline     │  │  AI Engine   │  │  Analytics Engine    │
│                    │  │              │  │                      │
│ ┌────────────────┐ │  │ ┌──────────┐│  │ ┌──────────────────┐ │
│ │ CSVLoader      │ │  │ │ OpenAI   ││  │ │ Sentiment        │ │
│ │ DataValidator  │ │  │ │ Client   ││  │ │ Analyzer         │ │
│ │ DataCleaner    │ │  │ │          ││  │ │                  │ │
│ │ VideoDiscoverer│ │  │ │ Embedder ││  │ │ Topic            │ │
│ └────────────────┘ │  │ │          ││  │ │ Extractor        │ │
│                    │  │ │ Hypothesis│  │ │                  │ │
│                    │  │ │ Generator││  │ │ Question         │ │
│                    │  │ │          ││  │ │ Finder           │ │
│                    │  │ │ Search   ││  │ └──────────────────┘ │
│                    │  │ │ Engine   ││  │                      │
│                    │  │ └──────────┘│  │                      │
└────────────────────┘  └──────────────┘  └──────────────────────┘
         │                      │                    │
         └──────────────────────┴────────────────────┘
                                │
                    ┌───────────▼──────────────┐
                    │  Infrastructure Layer    │
                    │                          │
                    │  ┌────────────────────┐  │
                    │  │ CacheManager       │  │
                    │  │ Logger             │  │
                    │  │ RateLimiter        │  │
                    │  │ ErrorHandler       │  │
                    │  └────────────────────┘  │
                    └──────────────────────────┘
```

### 2.2 DIRECTORY STRUCTURE

```
project_root/
├── app.py                          # Flask application entry point
├── config.py                       # Configuration management
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variables template
├── .gitignore                      # Git ignore rules
├── README.md                       # Setup and usage instructions
├── SYSTEM_DESIGN.md               # This document
│
├── src/
│   ├── __init__.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── orchestrator.py         # Main workflow orchestrator
│   │   ├── exceptions.py           # Custom exception classes
│   │   └── models.py               # Data models and types
│   │
│   ├── data/
│   │   ├── __init__.py
│   │   ├── loader.py               # CSV loading with validation
│   │   ├── validator.py            # Data validation rules
│   │   ├── cleaner.py              # Data cleaning operations
│   │   └── video_discoverer.py    # Video identification logic
│   │
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── openai_client.py       # OpenAI API wrapper
│   │   ├── embedder.py            # Embedding generation
│   │   ├── hypothesis_generator.py # Dynamic CommentSearchSpec generation
│   │   ├── search_engine.py       # Hybrid search implementation
│   │   └── prompts.py             # Prompt templates
│   │
│   ├── analytics/
│   │   ├── __init__.py
│   │   ├── sentiment_analyzer.py  # Sentiment analysis
│   │   ├── topic_extractor.py     # Topic clustering and labeling
│   │   └── question_finder.py     # Question identification
│   │
│   ├── output/
│   │   ├── __init__.py
│   │   ├── output_manager.py      # Coordinates all output
│   │   ├── results_writer.py      # JSON results generation
│   │   └── visualization_builder.py # HTML visualization generation
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logger.py              # Logging configuration
│       ├── cache_manager.py       # Caching for embeddings
│       ├── rate_limiter.py        # API rate limiting
│       └── helpers.py             # Utility functions
│
├── templates/
│   └── visualization.html          # Jinja2 template for visualization
│
├── static/
│   ├── css/
│   │   └── styles.css
│   └── js/
│       └── visualization.js
│
├── tests/
│   ├── __init__.py
│   ├── test_data_pipeline.py
│   ├── test_ai_engine.py
│   └── test_analytics.py
│
└── output/                         # Generated outputs (gitignored)
    └── run-{timestamp}/
        ├── results.json
        ├── metadata.json
        ├── embeddings_cache.pkl
        ├── logs/
        │   ├── app.log
        │   ├── openai_calls.log
        │   └── errors.log
        └── visualization/
            └── index.html
```

---

## 3. CORE COMPONENTS DESIGN

### 3.1 DATA MODELS

**Location:** `src/core/models.py`

**Purpose:** Define all data structures used throughout the system. These are pure data containers with validation, no business logic.

#### Comment
```
Represents a single comment or video post.

Attributes:
- id: str
- url: str
- content: str
- author_id: str
- parent_id: str
- is_video: bool (determined during discovery)
- cleaned_content: str (populated after cleaning)
- metadata: dict (additional fields like extracted likes/replies)
- embedding: Optional[List[float]] (populated during embedding phase)

Methods:
- validate(): Validates all required fields are present
- to_dict(): Converts to dictionary for JSON serialization
- from_dict(data: dict): Creates instance from dictionary
```

#### Video
```
Represents a discovered video with its associated comments.

Attributes:
- id: str (video ID extracted from parent_id)
- url: str
- content: str (video title/description)
- author_id: str
- comments: List[Comment] (all comments for this video)
- video_metadata: dict (channel name, video title, etc.)
- dynamic_search_specs: List[CommentSearchSpec] (generated hypotheses)
- static_search_specs: List[CommentSearchSpec] (universal searches)

Methods:
- add_comment(comment: Comment): Adds comment to this video
- get_comment_count(): Returns total number of comments
- get_sample_comments(n: int): Returns n random comments for analysis
- validate(): Ensures video has required data
- to_dict(): Converts to dictionary for JSON serialization
```

#### CommentSearchSpec
```
Specification for searching comments.

Attributes:
- query: str (natural language search query)
- context: str (category: technical_feedback, content_ideas, support_requests, etc.)
- filters: dict
  - min_length: int
  - max_length: int
  - exclude_spam: bool
  - require_question_mark: bool
- extract_fields: List[str] (sentiment, topics, issues, suggestions)
- is_static: bool (True if universal, False if video-specific)
- rationale: str (explanation of why this search is valuable)
- top_k: int (number of results to return, default 30)

Methods:
- validate(): Ensures spec is properly formed
- to_dict(): Converts to dictionary
- from_dict(data: dict): Creates instance from dictionary
```

#### SearchResult
```
Result of executing a CommentSearchSpec.

Attributes:
- spec: CommentSearchSpec (the spec that was executed)
- matched_comments: List[Comment] (comments matching the search)
- relevance_scores: List[float] (relevance score for each matched comment)
- extracted_insights: dict (insights extracted per extract_fields)
- execution_time: float (time taken to execute search)
- api_calls_made: int (number of API calls during search)

Methods:
- get_top_n(n: int): Returns top n results by relevance
- filter_by_threshold(threshold: float): Filters results by relevance
- to_dict(): Converts to dictionary
```

#### AnalyticsResult
```
Container for all analytics results for a video.

Attributes:
- video_id: str
- sentiment_score: float (0-1 scale)
- sentiment_distribution: dict (breakdown of positive/neutral/negative)
- top_topics: List[TopicCluster] (5 most common topics)
- top_questions: List[Question] (5 most popular questions)
- search_results: List[SearchResult] (results from all CommentSearchSpecs)
- metadata: dict (processing time, comment count, etc.)

Methods:
- to_dict(): Converts to dictionary for JSON output
- validate(): Ensures all required analytics are present
```

#### TopicCluster
```
Represents a discovered topic cluster.

Attributes:
- topic_name: str (LLM-generated label)
- comment_count: int (number of comments in this cluster)
- percentage: float (percentage of total comments)
- representative_comments: List[Comment] (sample comments)
- keywords: List[str] (key terms extracted)

Methods:
- to_dict(): Converts to dictionary
```

#### Question
```
Represents an identified question from comments.

Attributes:
- comment: Comment (the comment containing the question)
- question_text: str (extracted question)
- engagement_score: float (likes + replies weighted)
- is_answered: bool (whether creator responded)
- category: str (technical, usage, pricing, etc.)
- relevance_score: float (LLM-determined relevance)

Methods:
- to_dict(): Converts to dictionary
```

#### ProcessingMetadata
```
Metadata about a complete processing run.

Attributes:
- run_id: str (unique identifier: timestamp-based)
- start_time: datetime
- end_time: datetime
- total_duration: float
- input_file: str
- videos_processed: int
- total_comments: int
- api_calls_made: int
- api_cost_estimate: float
- errors_encountered: List[dict]
- warnings: List[dict]

Methods:
- to_dict(): Converts to dictionary
- save(path: str): Saves metadata to JSON file
```

### 3.2 DATA PIPELINE COMPONENTS

**Location:** `src/data/`

#### CSVLoader
```
Responsible for loading CSV data into Comment objects.

Methods:
- load_csv(file_path: str) -> List[Comment]
  - Reads CSV file
  - Handles encoding issues (utf-8, latin-1 fallback)
  - Creates Comment objects
  - Logs loading statistics
  - Raises: FileNotFoundError, CSVParsingError

Dependencies: pandas, logger
Error Handling: Try-catch on file operations, encoding errors
Logging: Row count, encoding used, loading time
```

#### DataValidator
```
Validates loaded data for completeness and correctness.

Methods:
- validate_comments(comments: List[Comment]) -> ValidationResult
  - Check for required fields (id, content, parent_id)
  - Detect duplicates
  - Identify null/empty content
  - Validate URL format
  - Returns ValidationResult with issues found

- fix_recoverable_issues(comments: List[Comment]) -> List[Comment]
  - Remove duplicates (keep first occurrence)
  - Strip whitespace from fields
  - Fix common URL issues
  - Returns cleaned comment list

ValidationResult:
- is_valid: bool
- total_comments: int
- issues_found: List[ValidationIssue]
- recommendations: List[str]

ValidationIssue:
- severity: str (error, warning, info)
- comment_id: str
- field: str
- description: str

Dependencies: logger
Error Handling: Non-critical issues logged as warnings
Logging: Each validation issue with severity
```

#### DataCleaner
```
Cleans and normalizes comment content.

Methods:
- clean_comments(comments: List[Comment]) -> List[Comment]
  - Remove HTML entities
  - Normalize unicode characters
  - Fix encoding artifacts
  - Trim excessive whitespace
  - Remove zero-width characters
  - Populate cleaned_content field
  
- detect_and_remove_spam(comments: List[Comment]) -> List[Comment]
  - Identify spam patterns (repeated characters, all caps)
  - Mark as spam in metadata
  - Returns non-spam comments
  
- normalize_text(text: str) -> str
  - Internal method for text normalization
  - Handles special characters
  - Preserves important punctuation

Dependencies: re, html, unicodedata, logger
Error Handling: Per-comment try-catch, logs failures but continues
Logging: Number of comments cleaned, issues fixed, spam detected
```

#### VideoDiscoverer
```
Identifies which posts are videos vs comments.

Methods:
- discover_videos(comments: List[Comment]) -> tuple[List[Video], List[Comment]]
  - Analyzes parent_id patterns
  - Videos: parent_id == id OR parent_id extracted from URL
  - Comments: parent_id != id
  - Groups comments by video
  - Returns (videos, orphaned_comments)

- validate_discovery(videos: List[Video]) -> bool
  - Ensures exactly 5 videos found
  - Validates each video has comments
  - Checks for orphaned comments
  - Raises DiscoveryError if validation fails

- extract_video_metadata(video: Video) -> dict
  - Extracts video ID from URL
  - Attempts to parse title from content
  - Returns metadata dict

DiscoveryError: Custom exception for discovery failures

Dependencies: re, logger
Error Handling: Raises DiscoveryError if != 5 videos found
Logging: Number of videos found, comments per video, orphaned comments
```

### 3.3 AI ENGINE COMPONENTS

**Location:** `src/ai/`

#### OpenAIClient
```
Wrapper for OpenAI API with error handling and retry logic.

Methods:
- __init__(api_key: str, rate_limiter: RateLimiter)
  - Initializes OpenAI client
  - Sets up retry logic
  - Validates API key

- create_completion(
    messages: List[dict],
    model: str = "gpt-4-turbo",
    temperature: float = 0.7,
    max_tokens: int = 1000,
    response_format: Optional[dict] = None
  ) -> CompletionResult
  - Makes chat completion request
  - Handles rate limiting
  - Retries on transient failures
  - Logs all API calls
  - Returns CompletionResult

- create_batch_completion(
    message_batches: List[List[dict]],
    model: str = "gpt-4-turbo"
  ) -> List[CompletionResult]
  - Processes multiple completions
  - Uses ThreadPoolExecutor for parallelization
  - Respects rate limits
  - Returns list of results

- create_embedding(
    texts: List[str],
    model: str = "text-embedding-3-small"
  ) -> List[List[float]]
  - Generates embeddings
  - Batches requests (up to 100 texts per call)
  - Caches results
  - Returns embedding vectors

CompletionResult:
- content: str
- model: str
- tokens_used: int
- cost_estimate: float
- response_time: float

Retry Strategy:
- Max attempts: 3
- Backoff: exponential (1s, 2s, 4s)
- Retry on: RateLimitError, APIConnectionError
- No retry on: InvalidRequestError, AuthenticationError

Dependencies: openai, tenacity, logger, rate_limiter
Error Handling: Comprehensive try-catch, custom exceptions
Logging: Every API call with tokens, cost, duration
```

#### Embedder
```
Handles embedding generation with caching.

Methods:
- __init__(openai_client: OpenAIClient, cache_manager: CacheManager)

- embed_comments(
    comments: List[Comment],
    force_refresh: bool = False
  ) -> List[Comment]
  - Generates embeddings for comment content
  - Checks cache first
  - Batches uncached comments
  - Stores embeddings in Comment.embedding
  - Saves to cache
  - Returns comments with embeddings populated

- embed_text(text: str) -> List[float]
  - Single text embedding
  - Used for search queries
  - Checks cache
  - Returns embedding vector

- get_embedding_dimension() -> int
  - Returns dimension of embedding model (1536 for text-embedding-3-small)

Dependencies: numpy, openai_client, cache_manager, logger
Error Handling: Per-batch try-catch, logs failures
Logging: Batch sizes, cache hits/misses, embedding time
Caching: Stores embeddings keyed by hash(content)
```

#### HypothesisGenerator
```
Generates dynamic CommentSearchSpecs for each video.

Methods:
- __init__(openai_client: OpenAIClient, prompts: Prompts)

- generate_search_specs(
    video: Video,
    num_specs: int = 5
  ) -> List[CommentSearchSpec]
  - Samples 10 diverse comments from video
  - Analyzes video content and sample comments
  - Uses LLM to generate hypotheses
  - Returns list of CommentSearchSpecs

- validate_and_refine_specs(
    video: Video,
    initial_specs: List[CommentSearchSpec]
  ) -> List[CommentSearchSpec]
  - Tests specs on full comment set
  - Evaluates result quality
  - Refines low-performing specs
  - Returns validated specs

- _create_generation_prompt(
    video: Video,
    sample_comments: List[Comment]
  ) -> str
  - Internal method to create prompt
  - Includes video context
  - Includes sample comments
  - Specifies output format

Prompt Structure:
"""
You are analyzing a YouTube video to help the creator understand their audience.

Video Information:
Title: {video.content}
Author: {video.author_id}
Total Comments: {video.get_comment_count()}

Sample Comments:
{sample_comments}

Generate 5 CommentSearchSpec objects that identify the most valuable comment categories for this creator.

Output as JSON array with structure:
[
  {
    "query": "natural language search query",
    "context": "category name",
    "filters": {},
    "extract_fields": [],
    "rationale": "why this is valuable"
  }
]
"""

Dependencies: openai_client, prompts, logger, random
Error Handling: Try-catch on LLM calls, fallback to generic specs
Logging: Generated specs, validation results, refinements
```

#### SearchEngine
```
Implements hybrid search: embedding-based filtering + LLM ranking.

Methods:
- __init__(
    openai_client: OpenAIClient,
    embedder: Embedder
  )

- execute_search(
    video: Video,
    spec: CommentSearchSpec
  ) -> SearchResult
  - Stage 1: Semantic filtering using embeddings
  - Stage 2: LLM-based ranking and relevance scoring
  - Stage 3: Insight extraction
  - Returns SearchResult

- _semantic_filter(
    comments: List[Comment],
    query_embedding: List[float],
    top_k: int = 30
  ) -> List[tuple[Comment, float]]
  - Computes cosine similarity
  - Returns top_k candidates with scores
  
- _llm_rerank(
    candidates: List[Comment],
    spec: CommentSearchSpec
  ) -> List[tuple[Comment, float]]
  - Batches candidates for LLM analysis
  - Scores relevance (0-1)
  - Returns reranked results

- _extract_insights(
    results: List[Comment],
    extract_fields: List[str]
  ) -> dict
  - Extracts requested insights from results
  - Fields: sentiment, topics, issues, suggestions
  - Returns structured insights dict

Dependencies: numpy, scipy, openai_client, embedder, logger
Error Handling: Graceful degradation if LLM fails (use semantic only)
Logging: Stage timing, candidate counts, final result count
```

#### Prompts
```
Centralized prompt templates for all LLM operations.

Class Attributes (as constants):
- HYPOTHESIS_GENERATION_PROMPT: str
- COMMENT_RELEVANCE_PROMPT: str
- SENTIMENT_ANALYSIS_PROMPT: str
- TOPIC_LABELING_PROMPT: str
- QUESTION_VALIDATION_PROMPT: str

Methods:
- format_hypothesis_prompt(video: Video, samples: List[Comment]) -> str
- format_relevance_prompt(comment: Comment, spec: CommentSearchSpec) -> str
- format_sentiment_prompt(comments: List[Comment]) -> str
- format_topic_prompt(cluster_comments: List[Comment]) -> str
- format_question_prompt(questions: List[str]) -> str

Each method:
- Takes structured inputs
- Fills template with data
- Returns formatted prompt string
- Handles escaping and formatting

Dependencies: None (pure template management)
Error Handling: Validates inputs before formatting
Logging: Not logged (templates are static)
```

### 3.4 ANALYTICS ENGINE COMPONENTS

**Location:** `src/analytics/`

#### SentimentAnalyzer
```
Performs sentiment analysis on comments.

Methods:
- __init__(openai_client: OpenAIClient)

- analyze_sentiment(
    comments: List[Comment],
    batch_size: int = 20
  ) -> SentimentResult
  - Batches comments for analysis
  - Uses GPT-3.5-turbo for cost efficiency
  - Scores each comment 0-1
  - Computes overall statistics
  - Returns SentimentResult

- _analyze_batch(
    comment_batch: List[Comment]
  ) -> List[float]
  - Internal method for batch processing
  - Prompt requests JSON array of scores
  - Returns list of sentiment scores

SentimentResult:
- overall_score: float (mean sentiment)
- distribution: dict
  - positive: int (count of scores > 0.6)
  - neutral: int (count of scores 0.4-0.6)
  - negative: int (count of scores < 0.4)
- comment_scores: dict[comment_id -> float]
- confidence: float (standard deviation-based)

Prompt Design:
- Requests JSON array output
- Emphasizes consistency
- Handles sarcasm and context
- Scale: 0 (very negative) to 1 (very positive)

Dependencies: openai_client, logger, statistics
Error Handling: Per-batch try-catch, logs failures
Logging: Batch processing progress, score distribution
```

#### TopicExtractor
```
Discovers and labels topics using clustering + LLM.

Methods:
- __init__(
    embedder: Embedder,
    openai_client: OpenAIClient
  )

- extract_topics(
    comments: List[Comment],
    num_topics: int = 5
  ) -> List[TopicCluster]
  - Ensures comments have embeddings
  - Clusters embeddings (KMeans)
  - Samples comments per cluster
  - LLM labels each cluster
  - Returns top num_topics clusters by size

- _cluster_embeddings(
    embeddings: np.ndarray,
    n_clusters: int = 10
  ) -> np.ndarray
  - Performs KMeans clustering
  - Returns cluster labels array

- _label_cluster(
    cluster_comments: List[Comment]
  ) -> tuple[str, List[str]]
  - Samples 5-7 representative comments
  - LLM generates topic name and keywords
  - Returns (topic_name, keywords)

- _select_representative_comments(
    cluster_comments: List[Comment],
    centroid: np.ndarray,
    n: int = 3
  ) -> List[Comment]
  - Selects comments closest to cluster centroid
  - Returns representative samples

Clustering Strategy:
- Initial clusters: 10 (oversample)
- Algorithm: KMeans with k-means++ init
- Distance metric: Euclidean (on embeddings)
- Final selection: Top 5 by cluster size

Dependencies: sklearn, numpy, embedder, openai_client, logger
Error Handling: Fallback to generic labels if LLM fails
Logging: Cluster sizes, labeling success, topic names
```

#### QuestionFinder
```
Identifies and ranks popular questions from comments.

Methods:
- __init__(openai_client: OpenAIClient)

- find_top_questions(
    comments: List[Comment],
    top_n: int = 5
  ) -> List[Question]
  - Stage 1: Filter comments with question marks
  - Stage 2: Rank by engagement (likes + replies)
  - Stage 3: LLM validation and categorization
  - Returns top_n Question objects

- _filter_questions(
    comments: List[Comment]
  ) -> List[Comment]
  - Checks for question mark presence
  - Validates minimum length (> 10 chars)
  - Returns potential questions

- _extract_engagement_score(
    comment: Comment
  ) -> float
  - Parses likes/replies from metadata or URL
  - Weighted formula: (likes * 1.0 + replies * 2.0)
  - Returns engagement score

- _validate_and_categorize(
    questions: List[Comment]
  ) -> List[Question]
  - LLM validates each is a substantive question
  - Categorizes: technical, usage, pricing, feature_request, etc.
  - Scores relevance to video topic
  - Returns validated Question objects

- _check_if_answered(
    question: Comment,
    all_comments: List[Comment],
    video: Video
  ) -> bool
  - Checks if video author replied to question
  - Returns True if answered

Dependencies: openai_client, logger, re
Error Handling: Graceful degradation if engagement parsing fails
Logging: Questions found, validation results, categories
```

### 3.5 OUTPUT COMPONENTS

**Location:** `src/output/`

#### OutputManager
```
Orchestrates all output generation.

Methods:
- __init__(
    base_output_dir: str = "output"
  )

- create_run_directory() -> str
  - Creates output/run-{timestamp}/
  - Sets up subdirectories: logs/, visualization/
  - Returns run directory path

- save_results(
    videos: List[Video],
    analytics: dict[str, AnalyticsResult],
    metadata: ProcessingMetadata
  ) -> None
  - Calls ResultsWriter to generate results.json
  - Calls VisualizationBuilder to generate HTML
  - Saves metadata.json
  - Copies logs to run directory

- get_run_id() -> str
  - Returns current run ID

Dependencies: results_writer, visualization_builder, logger, os
Error Handling: Try-catch on file operations
Logging: Output file creation, sizes, locations
```

#### ResultsWriter
```
Generates results.json with all analysis outcomes.

Methods:
- __init__()

- write_results(
    output_path: str,
    videos: List[Video],
    analytics: dict[str, AnalyticsResult],
    metadata: ProcessingMetadata
  ) -> None
  - Constructs complete results structure
  - Converts all objects to dicts
  - Writes formatted JSON
  - Validates JSON structure

- _build_results_structure(
    videos: List[Video],
    analytics: dict[str, AnalyticsResult],
    metadata: ProcessingMetadata
  ) -> dict
  - Creates nested dictionary structure
  - Ensures all data is JSON-serializable
  - Returns complete results dict

Results JSON Structure:
{
  "metadata": {
    "run_id": str,
    "timestamp": str,
    "processing_time": float,
    "videos_analyzed": int,
    "total_comments": int
  },
  "videos": [
    {
      "video_id": str,
      "url": str,
      "title": str,
      "comment_count": int,
      "analytics": {
        "sentiment": {
          "overall_score": float,
          "distribution": {...}
        },
        "topics": [...],
        "questions": [...],
        "search_results": {
          "static_searches": [...],
          "dynamic_searches": [...]
        }
      }
    }
  ]
}

Dependencies: json, logger
Error Handling: Validates JSON serializability
Logging: File size, validation results
```

#### VisualizationBuilder
```
Generates interactive HTML visualization.

Methods:
- __init__(
    template_path: str = "templates/visualization.html"
  )

- build_visualization(
    output_path: str,
    results_json_path: str
  ) -> None
  - Reads results.json
  - Renders Jinja2 template
  - Embeds data as JavaScript
  - Generates charts using Chart.js
  - Writes index.html

- _prepare_chart_data(
    results: dict
  ) -> dict
  - Transforms results for Chart.js
  - Creates data structures for:
    - Sentiment distribution (bar chart)
    - Topics distribution (horizontal bar)
    - Questions list (table)
    - Search results (cards)

Visualization Features:
- Navigation sidebar (video selector)
- Overview cards (metrics)
- Sentiment gauge chart
- Topic distribution chart
- Questions table (sortable)
- Search results expandable cards
- Responsive design
- No external dependencies (all inline)

Template Variables:
- run_id: str
- videos: List[dict]
- chart_data: dict
- timestamp: str

Dependencies: jinja2, json, logger
Error Handling: Template rendering errors caught
Logging: Template rendering, file generation
```

### 3.6 UTILITY COMPONENTS

**Location:** `src/utils/`

#### Logger
```
Centralized logging configuration.

Methods:
- setup_logging(
    log_dir: str,
    level: str = "INFO"
  ) -> logging.Logger
  - Creates log directory
  - Configures file and console handlers
  - Sets up formatters
  - Returns configured logger

- get_logger(name: str) -> logging.Logger
  - Returns logger for specific module

Log Files:
- app.log: General application logs
- openai_calls.log: All API call details
- errors.log: Errors and exceptions only

Format:
[TIMESTAMP] [LEVEL] [MODULE] MESSAGE

Dependencies: logging, os
Error Handling: Creates log directory if missing
```

#### CacheManager
```
Manages caching of embeddings and API responses.

Methods:
- __init__(cache_dir: str)

- get_embedding(text_hash: str) -> Optional[List[float]]
  - Retrieves cached embedding
  - Returns None if not cached

- set_embedding(
    text_hash: str,
    embedding: List[float]
  ) -> None
  - Stores embedding in cache
  - Persists to disk

- save_cache() -> None
  - Writes cache to embeddings_cache.pkl

- load_cache() -> None
  - Loads cache from disk if exists

- clear_cache() -> None
  - Removes all cached data

- get_cache_stats() -> dict
  - Returns cache statistics
  - Size, hit rate, items

Dependencies: pickle, hashlib, logger
Error Handling: Graceful handling of corrupted cache
Logging: Cache hits/misses, save operations
```

#### RateLimiter
```
Prevents API rate limit violations.

Methods:
- __init__(
    requests_per_minute: int = 60,
    tokens_per_minute: int = 150000
  )

- acquire(estimated_tokens: int = 100) -> None
  - Blocks if rate limit would be exceeded
  - Updates request and token counters
  - Sleeps if necessary

- _reset_if_needed() -> None
  - Resets counters after time window

- get_stats() -> dict
  - Returns current usage statistics

Implementation:
- Sliding window algorithm
- Tracks requests and tokens
- Thread-safe (uses threading.Lock)

Dependencies: time, threading, logger
Error Handling: None (blocking behavior)
Logging: Rate limit waits, resets
```

#### Helpers
```
Miscellaneous utility functions.

Functions:
- generate_run_id() -> str
  - Creates timestamp-based unique ID
  - Format: YYYYMMDD_HHMMSS_microseconds

- compute_cosine_similarity(
    vec1: List[float],
    vec2: List[float]
  ) -> float
  - Computes cosine similarity between vectors
  - Returns score -1 to 1

- hash_text(text: str) -> str
  - Creates SHA256 hash of text
  - Used for cache keys

- batch_list(
    items: List,
    batch_size: int
  ) -> List[List]
  - Splits list into batches
  - Returns list of batches

- safe_json_dumps(obj: Any) -> str
  - Safely serializes objects to JSON
  - Handles non-serializable types

- truncate_text(
    text: str,
    max_length: int = 100
  ) -> str
  - Truncates text for display
  - Adds ellipsis

Dependencies: hashlib, json, math, datetime
Error Handling: Type validation
Logging: None (utility functions)
```

### 3.7 CORE ORCHESTRATOR

**Location:** `src/core/orchestrator.py`

#### Orchestrator
```
Main workflow controller that coordinates all components.

Methods:
- __init__(
    config: Config,
    logger: logging.Logger
  )
  - Initializes all components
  - Sets up dependency injection

- run_analysis(csv_path: str) -> str
  - Main entry point for analysis
  - Executes complete workflow
  - Returns run_id

- _load_and_validate_data(csv_path: str) -> List[Comment]
  - Phase 1: Data Loading
  - Loads CSV
  - Validates data
  - Cleans comments
  - Returns validated comments

- _discover_videos(comments: List[Comment]) -> tuple
  - Phase 2: Video Discovery
  - Identifies videos
  - Groups comments by video
  - Returns (videos, orphaned_comments)

- _generate_embeddings(videos: List[Video]) -> None
  - Phase 3: Embedding Generation
  - Embeds all comments
  - Caches embeddings
  - Updates comment objects

- _generate_search_specs(videos: List[Video]) -> None
  - Phase 4: Search Spec Generation
  - Creates static specs
  - Generates dynamic specs per video
  - Validates and refines specs
  - Attaches to video objects

- _execute_searches(videos: List[Video]) -> dict
  - Phase 5: Search Execution
  - Runs all specs for each video
  - Collects search results
  - Returns video_id -> List[SearchResult]

- _perform_analytics(videos: List[Video]) -> dict
  - Phase 6: Analytics
  - Sentiment analysis
  - Topic extraction
  - Question identification
  - Returns video_id -> AnalyticsResult

- _generate_outputs(
    videos: List[Video],
    analytics: dict,
    metadata: ProcessingMetadata
  ) -> str
  - Phase 7: Output Generation
  - Creates run directory
  - Writes results.json
  - Generates visualization
  - Copies logs
  - Returns run directory path

Complete Workflow:
1. Load and Validate Data
2. Discover Videos
3. Generate Embeddings
4. Generate Search Specs
5. Execute Searches
6. Perform Analytics
7. Generate Outputs

Error Recovery:
- Each phase wrapped in try-catch
- Logs errors and continues if possible
- Critical failures abort workflow
- Metadata tracks all errors

Dependencies: All component classes, logger, config
Error Handling: Per-phase error handling with recovery
Logging: Phase start/end, progress, timing
```

---

## 4. WORKFLOW AND DATA FLOW

### 4.1 COMPLETE PROCESSING PIPELINE

```
┌─────────────────────────────────────────────────────────────┐
│                      INPUT: CSV File                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 1: DATA LOADING & VALIDATION                          │
│                                                              │
│ CSVLoader.load_csv()                                        │
│   ├─ Read CSV file                                          │
│   ├─ Handle encoding (utf-8, fallback to latin-1)          │
│   └─ Create Comment objects                                 │
│                                                              │
│ DataValidator.validate_comments()                           │
│   ├─ Check required fields                                  │
│   ├─ Detect duplicates                                      │
│   ├─ Validate URLs                                          │
│   └─ Generate ValidationResult                              │
│                                                              │
│ DataCleaner.clean_comments()                                │
│   ├─ Remove HTML entities                                   │
│   ├─ Normalize unicode                                      │
│   ├─ Fix encoding artifacts                                 │
│   └─ Detect spam                                            │
│                                                              │
│ Output: List[Comment] (validated and cleaned)               │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 2: VIDEO DISCOVERY                                    │
│                                                              │
│ VideoDiscoverer.discover_videos()                           │
│   ├─ Analyze parent_id patterns                             │
│   ├─ Identify video posts (parent_id == id)                │
│   ├─ Group comments by video_id                             │
│   ├─ Extract video metadata                                 │
│   └─ Validate: exactly 5 videos found                       │
│                                                              │
│ Output: List[Video], List[Comment] (orphaned)               │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 3: EMBEDDING GENERATION                               │
│                                                              │
│ Embedder.embed_comments()                                   │
│   ├─ Check cache for existing embeddings                    │
│   ├─ Batch uncached comments (100 per batch)               │
│   ├─ Call OpenAI embedding API                             │
│   ├─ Store embeddings in Comment.embedding                  │
│   └─ Save to cache (embeddings_cache.pkl)                   │
│                                                              │
│ Output: Comments with embeddings populated                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 4: SEARCH SPEC GENERATION                             │
│                                                              │
│ For each video:                                             │
│                                                              │
│ Static Specs (universal for all videos):                    │
│   ├─ Spec 1: High-engagement constructive feedback         │
│   └─ Spec 2: Unanswered content gap questions              │
│                                                              │
│ HypothesisGenerator.generate_search_specs()                 │
│   ├─ Sample 10 diverse comments                             │
│   ├─ Analyze video content + samples                        │
│   ├─ LLM generates 5 video-specific specs                   │
│   ├─ Validate specs on full dataset                         │
│   └─ Refine low-performing specs                            │
│                                                              │
│ Output: Video.dynamic_search_specs + Video.static_search_specs│
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 5: SEARCH EXECUTION                                   │
│                                                              │
│ For each video, for each spec:                             │
│                                                              │
│ SearchEngine.execute_search()                               │
│   │                                                          │
│   ├─ Stage 1: Semantic Filtering                           │
│   │   ├─ Embed spec.query                                   │
│   │   ├─ Compute cosine similarity with all comments       │
│   │   └─ Select top 30 candidates                           │
│   │                                                          │
│   ├─ Stage 2: LLM Ranking                                  │
│   │   ├─ Batch candidates (20 per batch)                   │
│   │   ├─ LLM scores relevance (0-1)                        │
│   │   └─ Rerank by relevance                               │
│   │                                                          │
│   └─ Stage 3: Insight Extraction                           │
│       ├─ Extract sentiment (if requested)                   │
│       ├─ Identify topics (if requested)                     │
│       └─ Extract suggestions/issues (if requested)          │
│                                                              │
│ Output: dict[video_id -> List[SearchResult]]                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 6: ANALYTICS                                          │
│                                                              │
│ For each video:                                             │
│                                                              │
│ 6.1 Sentiment Analysis                                      │
│ SentimentAnalyzer.analyze_sentiment()                       │
│   ├─ Batch comments (20 per batch)                          │
│   ├─ LLM scores each comment 0-1                           │
│   ├─ Compute overall score (mean)                           │
│   └─ Calculate distribution (pos/neu/neg)                   │
│                                                              │
│ 6.2 Topic Extraction                                        │
│ TopicExtractor.extract_topics()                             │
│   ├─ Cluster embeddings (KMeans, n=10)                     │
│   ├─ Sample comments per cluster                            │
│   ├─ LLM labels each cluster                               │
│   ├─ Extract keywords                                       │
│   └─ Select top 5 by cluster size                           │
│                                                              │
│ 6.3 Question Identification                                 │
│ QuestionFinder.find_top_questions()                         │
│   ├─ Filter comments with '?'                               │
│   ├─ Rank by engagement (likes + replies)                  │
│   ├─ LLM validates substantive questions                    │
│   ├─ Categorize questions                                   │
│   └─ Return top 5                                           │
│                                                              │
│ Output: dict[video_id -> AnalyticsResult]                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 7: OUTPUT GENERATION                                  │
│                                                              │
│ OutputManager.create_run_directory()                        │
│   └─ Create output/run-{timestamp}/                         │
│                                                              │
│ ResultsWriter.write_results()                               │
│   ├─ Build complete results structure                       │
│   ├─ Convert all objects to dicts                           │
│   └─ Write results.json                                     │
│                                                              │
│ VisualizationBuilder.build_visualization()                  │
│   ├─ Read results.json                                      │
│   ├─ Prepare chart data                                     │
│   ├─ Render Jinja2 template                                │
│   └─ Write visualization/index.html                         │
│                                                              │
│ OutputManager.save_results()                                │
│   ├─ Save metadata.json                                     │
│   └─ Copy logs to run directory                             │
│                                                              │
│ Output: output/run-{timestamp}/                             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    FINAL OUTPUT                              │
│                                                              │
│ output/run-{timestamp}/                                     │
│   ├─ results.json                                           │
│   ├─ metadata.json                                          │
│   ├─ embeddings_cache.pkl                                   │
│   ├─ logs/                                                  │
│   │   ├─ app.log                                            │
│   │   ├─ openai_calls.log                                   │
│   │   └─ errors.log                                         │
│   └─ visualization/                                         │
│       └─ index.html                                         │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 DATA FLOW DIAGRAM

```
CSV File
   │
   ├──> CSVLoader ──> List[Comment] (raw)
   │
   ├──> DataValidator ──> ValidationResult
   │                        │
   │                        └──> DataCleaner ──> List[Comment] (clean)
   │
   └──> VideoDiscoverer ──> List[Video] + List[Comment] (orphaned)
                             │
                             ├──> Embedder ──> Video (with embeddings)
                             │                  │
                             │                  ├──> HypothesisGenerator
                             │                  │      │
                             │                  │      └──> Video (with search specs)
                             │                  │
                             │                  └──> SearchEngine
                             │                         │
                             │                         └──> List[SearchResult]
                             │
                             ├──> SentimentAnalyzer ──> SentimentResult
                             │
                             ├──> TopicExtractor ──> List[TopicCluster]
                             │
                             └──> QuestionFinder ──> List[Question]
                                    │
                                    ├──> ResultsWriter ──> results.json
                                    │
                                    └──> VisualizationBuilder ──> index.html
```

### 4.3 STATE TRANSITIONS

```
[IDLE]
   │
   └──> [LOADING] ──> [VALIDATING] ──> [CLEANING]
           │              │               │
           ├─ Error ──────┴───────────────┴──> [ERROR]
           │
           └──> [DISCOVERING]
                   │
                   ├─ != 5 videos found ──> [ERROR]
                   │
                   └──> [EMBEDDING]
                           │
                           ├─ API Error ──> [RETRY] ──> [EMBEDDING]
                           │                    │
                           │                    └─ Max retries ──> [ERROR]
                           │
                           └──> [GENERATING_SPECS]
                                   │
                                   └──> [SEARCHING]
                                           │
                                           └──> [ANALYZING]
                                                   │
                                                   └──> [GENERATING_OUTPUT]
                                                           │
                                                           └──> [COMPLETE]
```

---

## 5. ERROR HANDLING STRATEGY

### 5.1 ERROR HIERARCHY

```
AppException (base)
├── DataException
│   ├── FileNotFoundError
│   ├── CSVParsingError
│   ├── ValidationError
│   └── DataCleaningError
│
├── DiscoveryException
│   ├── VideoCountMismatchError
│   └── OrphanedCommentsError
│
├── AIException
│   ├── APIKeyError
│   ├── RateLimitError
│   ├── APIConnectionError
│   ├── InvalidResponseError
│   └── EmbeddingError
│
├── AnalyticsException
│   ├── SentimentAnalysisError
│   ├── TopicExtractionError
│   └── QuestionFinderError
│
└── OutputException
    ├── DirectoryCreationError
    ├── FileWriteError
    └── VisualizationError
```

### 5.2 ERROR HANDLING PATTERNS

#### Pattern 1: Try-Catch with Logging
```
Used in: All API calls, file operations
Strategy:
- Wrap risky operations in try-catch
- Log error with context
- Raise custom exception or return None
- Never fail silently

Example Context:
try:
    result = openai_client.create_completion(messages)
    logger.info(f"API call successful: {result.tokens_used} tokens")
    return result
except RateLimitError as e:
    logger.warning(f"Rate limit hit: {e}")
    raise AIException("Rate limit exceeded") from e
except APIConnectionError as e:
    logger.error(f"Connection failed: {e}")
    raise AIException("API connection failed") from e
except Exception as e:
    logger.error(f"Unexpected error in API call: {e}")
    raise AIException("API call failed") from e
```

#### Pattern 2: Retry with Exponential Backoff
```
Used in: OpenAI API calls
Strategy:
- Max 3 attempts
- Wait: 1s, 2s, 4s
- Only retry on transient errors
- Log each attempt

Retry Conditions:
- RateLimitError: Yes
- APIConnectionError: Yes
- InvalidRequestError: No (bad input)
- AuthenticationError: No (bad API key)
```

#### Pattern 3: Graceful Degradation
```
Used in: Search engine, analytics
Strategy:
- Attempt operation
- If fails, fall back to simpler method
- Log degradation
- Continue execution

Example Context:
Stage 1: Semantic search (always succeeds)
Stage 2: LLM ranking
  - If fails: Use only semantic scores
  - Log: "LLM ranking failed, using semantic scores only"
Stage 3: Insight extraction
  - If fails: Return results without insights
  - Log: "Insight extraction failed, basic results only"
```

#### Pattern 4: Validation with Early Exit
```
Used in: Data validation, video discovery
Strategy:
- Validate inputs before processing
- Raise exception immediately if invalid
- Provide detailed error message
- Never process invalid data

Example Context:
if len(videos) != 5:
    error_msg = f"Expected 5 videos, found {len(videos)}"
    logger.error(error_msg)
    raise VideoCountMismatchError(error_msg)
```

#### Pattern 5: Batch Error Handling
```
Used in: Batch processing (embeddings, sentiment)
Strategy:
- Process items in batches
- Try-catch per batch
- Log failed batches
- Continue with successful batches
- Report failure rate

Example Context:
successful_batches = 0
failed_batches = []

for i, batch in enumerate(batches):
    try:
        results = process_batch(batch)
        successful_batches += 1
    except Exception as e:
        logger.error(f"Batch {i} failed: {e}")
        failed_batches.append(i)
        continue

if failed_batches:
    logger.warning(f"{len(failed_batches)} batches failed")
```

### 5.3 ERROR RECOVERY STRATEGIES

#### Critical Errors (Abort Workflow)
```
Errors:
- API authentication failure
- Input file not found
- != 5 videos discovered
- Output directory write failure

Response:
- Log detailed error
- Save partial results if possible
- Generate error report
- Return error status code
```

#### Non-Critical Errors (Continue with Degradation)
```
Errors:
- Single embedding batch fails
- LLM ranking unavailable
- Insight extraction fails
- Individual topic labeling fails

Response:
- Log warning
- Use fallback method
- Mark result as degraded
- Continue workflow
```

#### Transient Errors (Retry)
```
Errors:
- Rate limit errors
- Network timeouts
- Temporary API unavailability

Response:
- Wait with exponential backoff
- Retry up to 3 times
- Log each attempt
- Fail if retries exhausted
```

### 5.4 ERROR REPORTING

#### Error Log Structure
```
Format:
{
  "timestamp": "2024-11-10T14:32:15.123Z",
  "level": "ERROR",
  "component": "SearchEngine",
  "operation": "execute_search",
  "error_type": "APIConnectionError",
  "error_message": "Connection to OpenAI failed",
  "context": {
    "video_id": "FqIMu4C87SM",
    "spec_context": "technical_feedback",
    "retry_attempt": 2
  },
  "stack_trace": "..."
}
```

#### Metadata Error Tracking
```
ProcessingMetadata includes:
- errors_encountered: List[dict]
  - timestamp
  - component
  - error_type
  - error_message
  - severity (critical, error, warning)
  
- warnings: List[dict]
  - timestamp
  - component
  - warning_message
  - impact
```

---

## 6. LOGGING AND MONITORING

### 6.1 LOG LEVELS

```
DEBUG: Detailed diagnostic information
- Function entry/exit
- Variable values
- Internal state changes

INFO: Normal operation confirmations
- Phase start/end
- Successful operations
- Progress updates
- Statistics

WARNING: Unexpected but handled situations
- Degraded performance
- Fallback methods used
- Validation warnings
- Retry attempts

ERROR: Errors that affect specific operations
- Failed API calls (after retries)
- Processing errors
- Invalid data

CRITICAL: Errors that stop workflow
- Authentication failures
- File system errors
- Unrecoverable exceptions
```

### 6.2 LOG FILES

#### app.log
```
Purpose: General application flow
Content:
- Workflow phase transitions
- High-level progress
- Component initialization
- Summary statistics
- Warnings and errors

Rotation: Daily, keep 7 days
Format: [TIMESTAMP] [LEVEL] [MODULE] MESSAGE
```

#### openai_calls.log
```
Purpose: Track all OpenAI API usage
Content:
- Request timestamp
- Model used
- Prompt summary (first 100 chars)
- Tokens used (prompt + completion)
- Cost estimate
- Response time
- Success/failure status

Rotation: Daily, keep 30 days
Format: JSON lines

Example:
{
  "timestamp": "2024-11-10T14:32:15.123Z",
  "operation": "create_completion",
  "model": "gpt-4-turbo",
  "prompt_preview": "Analyze this video to help...",
  "tokens_prompt": 250,
  "tokens_completion": 180,
  "tokens_total": 430,
  "cost_estimate": 0.00645,
  "response_time_ms": 1234,
  "status": "success"
}
```

#### errors.log
```
Purpose: All errors and exceptions
Content:
- Error timestamp
- Component/module
- Operation being performed
- Error type and message
- Stack trace
- Context data
- Recovery action taken

Rotation: Daily, keep 90 days
Format: JSON lines with full stack traces
```

### 6.3 LOGGING PATTERNS

#### Component Entry/Exit
```
Pattern:
logger.info(f"[{component}] Starting {operation}")
# ... operation code ...
logger.info(f"[{component}] Completed {operation} in {duration}s")

Example:
logger.info("[VideoDiscoverer] Starting video discovery")
videos, orphaned = discover_videos(comments)
logger.info(f"[VideoDiscoverer] Completed discovery in 0.23s - Found {len(videos)} videos")
```

#### Progress Tracking
```
Pattern:
total = len(items)
for i, item in enumerate(items, 1):
    logger.info(f"Processing {i}/{total} ({i/total*100:.1f}%)")
    process(item)

Example:
logger.info(f"Embedding comments: 0/{len(comments)} (0.0%)")
for i, batch in enumerate(batches):
    embed_batch(batch)
    progress = (i + 1) / len(batches) * 100
    logger.info(f"Embedding comments: {(i+1)*batch_size}/{len(comments)} ({progress:.1f}%)")
```

#### API Call Logging
```
Pattern:
logger.info(f"API call: {model}, prompt={prompt[:50]}...")
try:
    result = api_call()
    logger.info(f"API success: {result.tokens_used} tokens, ${result.cost:.4f}")
except Exception as e:
    logger.error(f"API failed: {e}")
    raise
```

#### Error Context
```
Pattern:
try:
    risky_operation()
except Exception as e:
    logger.error(
        f"Operation failed",
        extra={
            "component": component_name,
            "operation": operation_name,
            "error_type": type(e).__name__,
            "context": {...}
        },
        exc_info=True
    )
    raise
```

### 6.4 MONITORING METRICS

#### Tracked Metrics
```
Processing Metrics:
- Total processing time
- Time per phase
- Comments processed per second
- Videos analyzed

API Metrics:
- Total API calls
- API calls per endpoint
- Total tokens used
- Total cost estimate
- Average response time
- Error rate

Quality Metrics:
- Cache hit rate
- Search result counts
- Average relevance scores
- Topics discovered
- Questions identified

Error Metrics:
- Total errors
- Errors by type
- Errors by component
- Recovery success rate
```

#### Metrics Output
```
Location: output/run-{id}/metadata.json

Structure:
{
  "metrics": {
    "processing": {
      "total_duration": 127.4,
      "phase_durations": {...},
      "comments_per_second": 15.7
    },
    "api": {
      "total_calls": 342,
      "total_tokens": 125430,
      "total_cost_estimate": 1.89,
      "avg_response_time": 0.87,
      "error_rate": 0.02
    },
    "quality": {
      "cache_hit_rate": 0.87,
      "avg_search_results": 12.3,
      "topics_discovered": 25,
      "questions_identified": 35
    },
    "errors": {
      "total": 7,
      "by_type": {...},
      "recovered": 5
    }
  }
}
```

---

## 7. CONFIGURATION MANAGEMENT

### 7.1 CONFIGURATION STRUCTURE

**Location:** `config.py`

```
Class: Config

Sections:
1. API Configuration
2. Model Configuration
3. Processing Configuration
4. Output Configuration
5. Logging Configuration

All values loaded from environment variables with defaults
```

### 7.2 CONFIGURATION PARAMETERS

#### API Configuration
```
OPENAI_API_KEY: str (required, no default)
OPENAI_ORG_ID: Optional[str] (default: None)
API_TIMEOUT: int (default: 60 seconds)
MAX_RETRIES: int (default: 3)
RETRY_DELAY: int (default: 1 second)
REQUESTS_PER_MINUTE: int (default: 60)
TOKENS_PER_MINUTE: int (default: 150000)
```

#### Model Configuration
```
COMPLETION_MODEL: str (default: "gpt-4-turbo")
FAST_COMPLETION_MODEL: str (default: "gpt-3.5-turbo")
EMBEDDING_MODEL: str (default: "text-embedding-3-small")
COMPLETION_TEMPERATURE: float (default: 0.7)
COMPLETION_MAX_TOKENS: int (default: 1000)
```

#### Processing Configuration
```
BATCH_SIZE: int (default: 20)
EMBEDDING_BATCH_SIZE: int (default: 100)
SEMANTIC_SEARCH_TOP_K: int (default: 30)
NUM_DYNAMIC_SPECS: int (default: 5)
NUM_TOPICS: int (default: 5)
NUM_QUESTIONS: int (default: 5)
SAMPLE_COMMENTS_FOR_HYPOTHESIS: int (default: 10)
MIN_COMMENT_LENGTH: int (default: 10)
ENABLE_CACHING: bool (default: True)
CACHE_DIR: str (default: "./cache")
```

#### Output Configuration
```
OUTPUT_BASE_DIR: str (default: "./output")
RESULTS_FILENAME: str (default: "results.json")
METADATA_FILENAME: str (default: "metadata.json")
VISUALIZATION_FILENAME: str (default: "index.html")
ENABLE_VISUALIZATION: bool (default: True)
```

#### Logging Configuration
```
LOG_LEVEL: str (default: "INFO")
LOG_TO_CONSOLE: bool (default: True)
LOG_TO_FILE: bool (default: True)
LOG_FORMAT: str (default: "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")
```

### 7.3 ENVIRONMENT VARIABLES

**File:** `.env`

```bash
Required:
OPENAI_API_KEY=sk-...

Optional (with defaults):
OPENAI_ORG_ID=org-...
API_TIMEOUT=60
MAX_RETRIES=3
COMPLETION_MODEL=gpt-4-turbo
FAST_COMPLETION_MODEL=gpt-3.5-turbo
EMBEDDING_MODEL=text-embedding-3-small
BATCH_SIZE=20
LOG_LEVEL=INFO
OUTPUT_BASE_DIR=./output
ENABLE_CACHING=true
CACHE_DIR=./cache
```

### 7.4 STATIC SEARCH SPECS

**Location:** `config.py` or separate constants file

```
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
        "rationale": "Community engagement signals important feedback that resonates with audience"
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
        "rationale": "Unanswered questions reveal audience needs and potential content opportunities"
    }
]
```

### 7.5 CONFIGURATION VALIDATION

```
Config class methods:

validate() -> bool
- Validates all required fields present
- Checks data types
- Validates ranges (e.g., batch_size > 0)
- Validates API key format
- Returns True if valid, raises ConfigError if not

get(key: str, default: Any = None) -> Any
- Gets configuration value
- Returns default if not found
- Logs access for debugging

to_dict() -> dict
- Exports configuration (sanitized)
- Masks sensitive values (API keys)
- Used for metadata

load_from_env() -> Config
- Static method
- Loads from environment variables
- Uses python-dotenv
- Returns Config instance
```

---

## 8. OUTPUT STRUCTURE

### 8.1 DIRECTORY LAYOUT

```
output/
└── run-20241110_143215_892341/
    ├── results.json
    ├── metadata.json
    ├── embeddings_cache.pkl
    ├── logs/
    │   ├── app.log
    │   ├── openai_calls.log
    │   └── errors.log
    └── visualization/
        └── index.html
```

### 8.2 results.json STRUCTURE

```json
{
  "metadata": {
    "run_id": "20241110_143215_892341",
    "timestamp": "2024-11-10T14:32:15.892341Z",
    "processing_time_seconds": 127.4,
    "input_file": "youtube_comments.csv",
    "videos_analyzed": 5,
    "total_comments": 2847,
    "api_calls_made": 342,
    "api_cost_estimate": 1.89
  },
  "videos": [
    {
      "video_id": "FqIMu4C87SM",
      "url": "https://www.youtube.com/watch?v=FqIMu4C87SM",
      "title": "Framework Laptop Review",
      "author_id": "UCxxxxxxxxxxxxxxxx",
      "comment_count": 547,
      "analytics": {
        "sentiment": {
          "overall_score": 0.72,
          "distribution": {
            "positive": 412,
            "neutral": 98,
            "negative": 37
          },
          "confidence": 0.89
        },
        "topics": [
          {
            "topic_name": "Pricing and Value",
            "comment_count": 142,
            "percentage": 25.9,
            "keywords": ["price", "expensive", "cost", "worth", "value"],
            "representative_comments": [
              {
                "id": "Ugw...",
                "content": "I agree Framework laptops are expensive...",
                "relevance_score": 0.94
              }
            ]
          }
        ],
        "questions": [
          {
            "question_text": "Does it support external GPU docks?",
            "engagement_score": 127.0,
            "is_answered": false,
            "category": "technical",
            "relevance_score": 0.91,
            "comment": {
              "id": "Ugz...",
              "content": "Great review! Does it support...",
              "author_id": "UCy..."
            }
          }
        ],
        "search_results": {
          "static_searches": [
            {
              "spec": {
                "query": "Find highly engaged comments...",
                "context": "community_validated_feedback",
                "is_static": true
              },
              "matched_comments": [
                {
                  "id": "Ugx...",
                  "content": "...",
                  "relevance_score": 0.95,
                  "insights": {
                    "sentiment": 0.85,
                    "suggestions": ["Lower price", "More ports"]
                  }
                }
              ],
              "result_count": 12,
              "execution_time": 3.2
            }
          ],
          "dynamic_searches": [
            {
              "spec": {
                "query": "Find comments about build quality and durability concerns",
                "context": "product_quality_feedback",
                "is_static": false,
                "rationale": "Understanding durability concerns helps..."
              },
              "matched_comments": [...],
              "result_count": 8,
              "execution_time": 2.9
            }
          ]
        }
      }
    }
  ],
  "summary": {
    "total_topics_identified": 25,
    "total_questions_identified": 35,
    "total_search_results": 87,
    "average_sentiment": 0.68
  }
}
```

### 8.3 metadata.json STRUCTURE

```json
{
  "run_id": "20241110_143215_892341",
  "start_time": "2024-11-10T14:32:15.892341Z",
  "end_time": "2024-11-10T14:34:23.312456Z",
  "total_duration_seconds": 127.42,
  "config": {
    "completion_model": "gpt-4-turbo",
    "fast_completion_model": "gpt-3.5-turbo",
    "embedding_model": "text-embedding-3-small",
    "batch_size": 20,
    "semantic_search_top_k": 30
  },
  "input": {
    "file": "youtube_comments.csv",
    "total_rows": 2852,
    "valid_comments": 2847,
    "duplicates_removed": 5
  },
  "processing_phases": {
    "data_loading": {
      "duration": 0.45,
      "comments_loaded": 2852
    },
    "video_discovery": {
      "duration": 0.12,
      "videos_found": 5,
      "orphaned_comments": 0
    },
    "embedding": {
      "duration": 34.2,
      "comments_embedded": 2847,
      "cache_hits": 0,
      "api_calls": 29
    },
    "search_spec_generation": {
      "duration": 15.8,
      "static_specs": 2,
      "dynamic_specs_per_video": 5,
      "api_calls": 10
    },
    "search_execution": {
      "duration": 52.3,
      "total_searches": 35,
      "total_results": 87,
      "api_calls": 175
    },
    "analytics": {
      "duration": 22.1,
      "sentiment_analysis": 8.4,
      "topic_extraction": 9.2,
      "question_identification": 4.5,
      "api_calls": 128
    },
    "output_generation": {
      "duration": 2.45,
      "files_created": 5
    }
  },
  "api_usage": {
    "total_calls": 342,
    "by_operation": {
      "create_embedding": 29,
      "create_completion": 313
    },
    "by_model": {
      "text-embedding-3-small": 29,
      "gpt-4-turbo": 198,
      "gpt-3.5-turbo": 115
    },
    "total_tokens": 125430,
    "tokens_by_model": {
      "gpt-4-turbo": 89320,
      "gpt-3.5-turbo": 36110
    },
    "estimated_cost": 1.89,
    "average_response_time": 0.87
  },
  "quality_metrics": {
    "cache_hit_rate": 0.0,
    "average_search_results_per_spec": 2.49,
    "average_relevance_score": 0.78,
    "topics_discovered": 25,
    "questions_identified": 35,
    "average_sentiment": 0.68
  },
  "errors": [
    {
      "timestamp": "2024-11-10T14:33:42.123Z",
      "component": "SearchEngine",
      "operation": "execute_search",
      "error_type": "RateLimitError",
      "severity": "warning",
      "message": "Rate limit hit, retrying...",
      "recovery_action": "exponential_backoff_retry",
      "recovered": true
    }
  ],
  "warnings": [
    {
      "timestamp": "2024-11-10T14:32:48.456Z",
      "component": "DataCleaner",
      "message": "5 comments marked as potential spam",
      "impact": "excluded_from_analysis"
    }
  ]
}
```

### 8.4 VISUALIZATION HTML STRUCTURE

```html
<!DOCTYPE html>
<html>
<head>
    <title>YouTube Comments Analysis - Run {run_id}</title>
    <style>
        /* Inline CSS for portability */
        /* Responsive design */
        /* Clean, professional styling */
    </style>
</head>
<body>
    <!-- Header with run metadata -->
    <header>
        <h1>YouTube Comments Analysis</h1>
        <div class="metadata">
            <span>Run ID: {run_id}</span>
            <span>Timestamp: {timestamp}</span>
            <span>Videos: 5</span>
            <span>Comments: {total_comments}</span>
        </div>
    </header>

    <!-- Navigation sidebar -->
    <nav>
        <ul>
            <li><a href="#overview">Overview</a></li>
            {for video in videos}
            <li><a href="#video-{video.id}">{video.title}</a></li>
            {endfor}
        </ul>
    </nav>

    <!-- Main content -->
    <main>
        <!-- Overview section -->
        <section id="overview">
            <h2>Overview</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>Average Sentiment</h3>
                    <p class="large-number">{avg_sentiment}</p>
                </div>
                <!-- More stat cards -->
            </div>
        </section>

        <!-- Per-video sections -->
        {for video in videos}
        <section id="video-{video.id}">
            <h2>{video.title}</h2>
            
            <!-- Sentiment -->
            <div class="analytics-section">
                <h3>Sentiment Analysis</h3>
                <canvas id="sentiment-chart-{video.id}"></canvas>
            </div>

            <!-- Topics -->
            <div class="analytics-section">
                <h3>Top Topics</h3>
                <canvas id="topics-chart-{video.id}"></canvas>
            </div>

            <!-- Questions -->
            <div class="analytics-section">
                <h3>Popular Questions</h3>
                <table id="questions-table-{video.id}">
                    <!-- Questions data -->
                </table>
            </div>

            <!-- Search Results -->
            <div class="analytics-section">
                <h3>Search Results</h3>
                
                <h4>Static Searches</h4>
                {for result in video.static_search_results}
                <div class="search-result-card">
                    <div class="spec-header">
                        <span class="context">{result.spec.context}</span>
                        <span class="result-count">{result.result_count} results</span>
                    </div>
                    <p class="query">{result.spec.query}</p>
                    <details>
                        <summary>View Comments</summary>
                        <ul class="comment-list">
                            {for comment in result.matched_comments}
                            <li>
                                <span class="score">{comment.relevance_score}</span>
                                <p>{comment.content}</p>
                            </li>
                            {endfor}
                        </ul>
                    </details>
                </div>
                {endfor}

                <h4>Dynamic Searches</h4>
                <!-- Similar structure -->
            </div>
        </section>
        {endfor}
    </main>

    <script>
        // Embedded data
        const resultsData = {/* results.json content */};
        
        // Chart.js initialization
        // Event handlers
        // Interactivity
    </script>
</body>
</html>
```

---

## 9. API INTEGRATION

### 9.1 OPENAI API USAGE PATTERNS

#### Completion Requests
```
Purpose: LLM-based analysis and generation

Used For:
- Hypothesis generation
- Comment relevance scoring
- Sentiment analysis
- Topic labeling
- Question validation

Model Selection:
- Complex tasks: gpt-4-turbo
- Simple classification: gpt-3.5-turbo

Request Structure:
{
  "model": "gpt-4-turbo",
  "messages": [
    {"role": "system", "content": "You are an expert..."},
    {"role": "user", "content": "..."}
  ],
  "temperature": 0.7,
  "max_tokens": 1000,
  "response_format": {"type": "json_object"}  // when needed
}

Response Handling:
- Extract content from response.choices[0].message.content
- Parse JSON if response_format was json_object
- Log tokens used
- Estimate cost
- Handle errors
```

#### Embedding Requests
```
Purpose: Generate vector representations

Used For:
- Comment embeddings (for semantic search)
- Query embeddings (for search specs)

Model: text-embedding-3-small

Request Structure:
{
  "model": "text-embedding-3-small",
  "input": ["text1", "text2", ...],  // batch up to 100
  "encoding_format": "float"
}

Response Handling:
- Extract embeddings array
- Map back to original texts
- Store in cache
- Return vectors
```

### 9.2 COST MANAGEMENT

#### Cost Estimation
```
Pricing (as of Jan 2025):
- gpt-4-turbo: $0.01/1K prompt tokens, $0.03/1K completion tokens
- gpt-3.5-turbo: $0.0005/1K prompt tokens, $0.0015/1K completion tokens
- text-embedding-3-small: $0.00002/1K tokens

Cost Calculator:
estimate_cost(
    model: str,
    prompt_tokens: int,
    completion_tokens: int = 0
) -> float

Cost Tracking:
- Per API call
- Per component
- Per phase
- Total for run
- Stored in metadata
```

#### Cost Optimization Strategies
```
1. Caching
   - Cache all embeddings
   - Never re-embed same text
   - Estimated savings: 90% on repeated runs

2. Batching
   - Batch embeddings: 100 per request
   - Batch sentiment: 20 comments per request
   - Reduces overhead

3. Model Selection
   - Use gpt-3.5-turbo for simple tasks
   - Reserve gpt-4-turbo for complex analysis
   - Estimated savings: 95% on classification tasks

4. Token Management
   - Truncate long comments for classification
   - Use concise prompts
   - Limit completion tokens
   - Estimated savings: 20-30%

5. Staged Execution
   - Semantic search filters 90% of comments
   - LLM only on top candidates
   - Estimated savings: 90% on search
```

### 9.3 RATE LIMITING

#### Rate Limit Configuration
```
OpenAI Limits (typical):
- Requests per minute: 60
- Tokens per minute: 150,000

RateLimiter Implementation:
- Tracks requests and tokens in sliding window
- Blocks if limit would be exceeded
- Auto-sleeps to stay under limits
- Thread-safe with locks

Usage:
rate_limiter = RateLimiter(
    requests_per_minute=60,
    tokens_per_minute=150000
)

# Before each API call
rate_limiter.acquire(estimated_tokens=250)
response = api.create_completion(...)
```

### 9.4 ERROR HANDLING FOR API CALLS

#### OpenAI Error Types
```
1. RateLimitError
   - Cause: Exceeded rate limits
   - Response: Wait and retry
   - Max retries: 3
   - Backoff: exponential (1s, 2s, 4s)

2. APIConnectionError
   - Cause: Network issues
   - Response: Retry
   - Max retries: 3

3. AuthenticationError
   - Cause: Invalid API key
   - Response: Abort immediately
   - User action: Check API key

4. InvalidRequestError
   - Cause: Bad request parameters
   - Response: Log and skip
   - No retry

5. Timeout
   - Cause: Request took too long
   - Response: Retry with longer timeout
   - Max retries: 2
```

---

## 10. TESTING STRATEGY

### 10.1 TEST STRUCTURE

```
tests/
├── __init__.py
├── conftest.py                  # Pytest fixtures
├── test_data/                   # Sample data files
│   ├── sample_comments.csv
│   └── expected_results.json
├── test_data_pipeline.py        # Data loading and processing
├── test_ai_engine.py           # AI component tests
├── test_analytics.py           # Analytics component tests
├── test_output.py              # Output generation tests
└── test_integration.py         # End-to-end tests
```

### 10.2 UNIT TESTS

#### Data Pipeline Tests
```
test_csv_loader.py:
- test_load_valid_csv()
- test_load_missing_file()
- test_load_malformed_csv()
- test_encoding_handling()

test_data_validator.py:
- test_validate_complete_data()
- test_validate_missing_fields()
- test_validate_duplicates()
- test_validate_url_format()

test_data_cleaner.py:
- test_clean_html_entities()
- test_normalize_unicode()
- test_detect_spam()

test_video_discoverer.py:
- test_discover_five_videos()
- test_discover_incorrect_count()
- test_group_comments_by_video()
```

#### AI Engine Tests
```
test_openai_client.py:
- test_create_completion_success()
- test_create_completion_rate_limit()
- test_create_completion_invalid_key()
- test_create_embedding_batch()

test_embedder.py:
- test_embed_comments_uncached()
- test_embed_comments_cached()
- test_cache_persistence()

test_search_engine.py:
- test_semantic_filter()
- test_llm_rerank()
- test_full_search_pipeline()
```

#### Analytics Tests
```
test_sentiment_analyzer.py:
- test_analyze_positive_comments()
- test_analyze_negative_comments()
- test_analyze_mixed_comments()

test_topic_extractor.py:
- test_cluster_embeddings()
- test_label_clusters()
- test_extract_topics()

test_question_finder.py:
- test_filter_questions()
- test_rank_by_engagement()
- test_validate_questions()
```

### 10.3 INTEGRATION TESTS

```
test_integration.py:

test_end_to_end_analysis():
- Load sample CSV
- Run complete pipeline
- Validate output structure
- Check results.json exists
- Verify visualization generated

test_error_recovery():
- Simulate API failures
- Verify graceful degradation
- Check error logging

test_caching_behavior():
- Run analysis twice
- Verify cache usage on second run
- Validate performance improvement
```

### 10.4 MOCK STRATEGIES

```
API Mocking:
- Mock OpenAI API responses
- Use sample responses for tests
- No actual API calls in tests
- Fast test execution

Fixtures:
- Sample comments dataset
- Pre-computed embeddings
- Expected analysis results

pytest-mock usage:
@pytest.fixture
def mock_openai_client(mocker):
    mock = mocker.patch('src.ai.openai_client.OpenAI')
    mock.create_completion.return_value = CompletionResult(...)
    return mock
```

### 10.5 TEST EXECUTION

```
Commands:
- Run all tests: pytest
- Run specific test: pytest tests/test_data_pipeline.py
- Run with coverage: pytest --cov=src
- Run integration only: pytest tests/test_integration.py

CI/CD Integration:
- Run tests on every commit
- Block merge if tests fail
- Generate coverage reports
```

---

## 11. DEPLOYMENT AND EXECUTION

### 11.1 SETUP INSTRUCTIONS

```
Prerequisites:
- Python 3.10+
- pip
- OpenAI API key

Setup Steps:
1. Clone repository
2. Create virtual environment: python -m venv venv
3. Activate: source venv/bin/activate (Linux/Mac) or venv\Scripts\activate (Windows)
4. Install dependencies: pip install -r requirements.txt
5. Copy .env.example to .env
6. Add OpenAI API key to .env
7. Place CSV file in project root
```

### 11.2 EXECUTION

```
Flask Application:
python app.py

API Endpoints:
POST /analyze
  Body: {"csv_path": "path/to/file.csv"}
  Returns: {"run_id": "...", "status": "processing"}

GET /status/<run_id>
  Returns: {"status": "complete|processing|error", "progress": 0.75}

GET /results/<run_id>
  Returns: results.json content

GET /visualization/<run_id>
  Returns: HTML visualization

Command Line (if implemented):
python -m src.cli analyze data/youtube_comments.csv
```

### 11.3 OUTPUT ACCESS

```
After completion:
- Results JSON: output/run-{id}/results.json
- Visualization: output/run-{id}/visualization/index.html
- Logs: output/run-{id}/logs/
- Metadata: output/run-{id}/metadata.json

Access visualization:
1. Via Flask: http://localhost:5000/visualization/{run_id}
2. Direct: Open output/run-{id}/visualization/index.html in browser
```

---

## 12. EXTENSIBILITY AND FUTURE ENHANCEMENTS

### 12.1 PLUGIN ARCHITECTURE

```
Designed for extensibility:
- All components are interfaces
- Easy to swap implementations
- New search strategies can be added
- New analytics can be plugged in

Example Extension Points:
1. New Embedder: Implement Embedder interface
2. New Search Strategy: Extend SearchEngine
3. New Analytics: Implement new analyzer class
4. New Visualization: Extend VisualizationBuilder
```

### 12.2 POTENTIAL ENHANCEMENTS

```
1. Multi-Provider Support
   - Add support for Claude, Gemini
   - Abstract LLM interface
   - Provider selection in config

2. Advanced Caching
   - Redis for distributed caching
   - Cache search results
   - Incremental processing

3. Streaming Output
   - Real-time progress updates
   - WebSocket connections
   - Live visualization updates

4. Advanced Analytics
   - User journey analysis
   - Temporal trends
   - Comparative analysis across videos

5. Export Options
   - PDF reports
   - CSV exports
   - API for programmatic access

6. Interactive Visualization
   - Drill-down capabilities
   - Custom filtering
   - Export specific sections
```

---

This system design document provides a comprehensive blueprint for implementing the YouTube Comments Analysis System. All components are designed to be modular, maintainable, and extensible while following best practices for error handling, logging, and cost management.
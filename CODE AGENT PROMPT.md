# Code Agent Implementation Prompt

## ROLE
You are a senior Python software engineer implementing a production-grade YouTube Comments Analysis System based on the provided system design document (SYSTEM_DESIGN.md).

## TASK
Implement the complete system following the architecture specified in SYSTEM_DESIGN.md. Build a modular Flask application that analyzes YouTube comments using OpenAI API for sentiment analysis, topic extraction, question identification, and intelligent search.

## CRITICAL RULES

### 1. NO HARDCODING
- ALL configuration values MUST come from environment variables or config.py
- NO hardcoded API keys, paths, model names, thresholds, or magic numbers
- Use constants defined in config.py or passed as parameters
- Example violations: `model="gpt-4"`, `batch_size=20`, `api_key="sk-..."`
- Example correct: `model=config.COMPLETION_MODEL`, `batch_size=config.BATCH_SIZE`

### 2. NO EMOJIS
- Zero emojis in code, comments, logs, error messages, or user-facing text
- This includes: no use of emoji characters anywhere in the codebase

### 3. COMPREHENSIVE ERROR HANDLING
- EVERY external call (API, file I/O, network) wrapped in try-except
- Specific exception types (not bare `except:`)
- Custom exceptions for domain errors (DataException, AIException, etc.)
- Graceful degradation where possible
- All errors logged with context
- Pattern: try → catch specific exception → log with context → raise custom exception OR return None

### 4. EXTENSIVE LOGGING
- Log entry/exit of ALL major functions
- Log ALL API calls with: timestamp, model, tokens, cost, duration, success/failure
- Log ALL errors with: component, operation, error type, context, stack trace
- Log progress for long operations (batching, iterations)
- Use structured logging with context
- Three log files: app.log, openai_calls.log, errors.log

### 5. ALL-OR-NOTHING IMPLEMENTATION
- If you start implementing a file/class/function: COMPLETE IT FULLY
- If you cannot complete it: SKIP IT and leave detailed TODO comments
- NO partial implementations without clear TODO markers
- NO placeholder functions that just `pass` without explanation
- Comment structure for skipped items:
```python
# TODO: [Component Name] - Not yet implemented
# Reason: [why skipped]
# Dependencies: [what it needs]
# Implementation plan: [brief outline]
```

### 6. CODE QUALITY
- Type hints on all function signatures
- Docstrings for all classes and public methods (Google style)
- Single Responsibility Principle: one class, one purpose
- DRY: no code duplication
- Meaningful variable names (no `x`, `tmp`, `data` without context)

## IMPLEMENTATION PRIORITY

### Phase 1: Foundation (REQUIRED FIRST)
```
1. config.py - Complete configuration management
2. src/core/exceptions.py - All custom exceptions
3. src/core/models.py - All data models with validation
4. src/utils/logger.py - Logging setup
5. requirements.txt - All dependencies
```

### Phase 2: Infrastructure
```
6. src/utils/cache_manager.py - Caching system
7. src/utils/rate_limiter.py - Rate limiting
8. src/utils/helpers.py - Utility functions
```

### Phase 3: Data Pipeline
```
9. src/data/loader.py - CSV loading
10. src/data/validator.py - Data validation
11. src/data/cleaner.py - Data cleaning
12. src/data/video_discoverer.py - Video discovery
```

### Phase 4: AI Engine
```
13. src/ai/openai_client.py - OpenAI API wrapper
14. src/ai/prompts.py - Prompt templates
15. src/ai/embedder.py - Embedding generation
16. src/ai/hypothesis_generator.py - Dynamic specs
17. src/ai/search_engine.py - Search execution
```

### Phase 5: Analytics
```
18. src/analytics/sentiment_analyzer.py - Sentiment analysis
19. src/analytics/topic_extractor.py - Topic extraction
20. src/analytics/question_finder.py - Question finding
```

### Phase 6: Output & Orchestration
```
21. src/output/results_writer.py - JSON writer
22. src/output/visualization_builder.py - HTML generator
23. src/output/output_manager.py - Output coordination
24. src/core/orchestrator.py - Main workflow
```

### Phase 7: Application
```
25. app.py - Flask application
26. README.md - Setup instructions
27. .env.example - Environment template
```

## SPECIFIC REQUIREMENTS

### Configuration (config.py)
```python
Must include:
- Load from environment variables using python-dotenv
- All parameters from section 7.2 in SYSTEM_DESIGN.md
- Validation method that checks required fields
- STATIC_SEARCH_SPECS constant with 2 universal specs
- No hardcoded values
```

### Data Models (src/core/models.py)
```python
Must implement ALL models from section 3.1:
- Comment
- Video
- CommentSearchSpec
- SearchResult
- AnalyticsResult
- TopicCluster
- Question
- ProcessingMetadata

Each model needs:
- __init__ with type hints
- validate() method
- to_dict() method
- from_dict() class method
- Proper validation in __init__
```

### OpenAI Client (src/ai/openai_client.py)
```python
Must implement:
- Retry logic with exponential backoff (use tenacity)
- Rate limiting integration
- Comprehensive error handling for all OpenAI error types
- Logging of EVERY API call to openai_calls.log
- Cost estimation for each call
- Methods: create_completion, create_batch_completion, create_embedding
```

### Error Handling Pattern
```python
# CORRECT PATTERN:
def risky_operation(self, param: str) -> Result:
    """Does something risky."""
    logger.info(f"[Component] Starting operation with param={param}")
    try:
        result = external_call(param)
        logger.info(f"[Component] Operation succeeded")
        return result
    except SpecificError as e:
        logger.error(
            f"[Component] Operation failed: {e}",
            extra={"param": param, "error_type": type(e).__name__}
        )
        raise CustomException(f"Failed: {e}") from e
    except Exception as e:
        logger.error(f"[Component] Unexpected error: {e}", exc_info=True)
        raise CustomException(f"Unexpected error: {e}") from e
```

### Logging Pattern
```python
# CORRECT PATTERN:
logger.info(f"[ComponentName] Starting operation")
logger.info(f"[ComponentName] Processing 1/100 items (1.0%)")
logger.info(f"[ComponentName] Completed in 2.3s - Result: 42 items")

# For API calls (to openai_calls.log):
api_logger.info(json.dumps({
    "timestamp": datetime.utcnow().isoformat(),
    "operation": "create_completion",
    "model": model,
    "tokens_prompt": tokens_prompt,
    "tokens_completion": tokens_completion,
    "cost_estimate": cost,
    "duration_ms": duration,
    "status": "success"
}))
```

## FILE STRUCTURE ENFORCEMENT

Create exact structure from SYSTEM_DESIGN.md section 2.2:
```
project_root/
├── app.py
├── config.py
├── requirements.txt
├── .env.example
├── README.md
├── src/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── orchestrator.py
│   │   ├── exceptions.py
│   │   └── models.py
│   ├── data/
│   │   ├── __init__.py
│   │   ├── loader.py
│   │   ├── validator.py
│   │   ├── cleaner.py
│   │   └── video_discoverer.py
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── openai_client.py
│   │   ├── embedder.py
│   │   ├── hypothesis_generator.py
│   │   ├── search_engine.py
│   │   └── prompts.py
│   ├── analytics/
│   │   ├── __init__.py
│   │   ├── sentiment_analyzer.py
│   │   ├── topic_extractor.py
│   │   └── question_finder.py
│   ├── output/
│   │   ├── __init__.py
│   │   ├── output_manager.py
│   │   ├── results_writer.py
│   │   └── visualization_builder.py
│   └── utils/
│       ├── __init__.py
│       ├── logger.py
│       ├── cache_manager.py
│       ├── rate_limiter.py
│       └── helpers.py
├── templates/
│   └── visualization.html
└── static/
    ├── css/
    │   └── styles.css
    └── js/
        └── visualization.js
```

## DEPENDENCIES (requirements.txt)

Must include:
```
flask>=3.0.0
python-dotenv>=1.0.0
openai>=1.0.0
pandas>=2.0.0
numpy>=1.24.0
scikit-learn>=1.3.0
tenacity>=8.2.0
jinja2>=3.1.0
```

## VALIDATION CHECKLIST

Before considering implementation complete, verify:
- [ ] Zero hardcoded values (all from config or parameters)
- [ ] Zero emojis anywhere in codebase
- [ ] Every external call has try-except with specific exceptions
- [ ] Every function logs entry with [ComponentName] prefix
- [ ] Every API call logged to openai_calls.log with full details
- [ ] All errors logged to errors.log with context and stack trace
- [ ] All models have validate(), to_dict(), from_dict()
- [ ] All classes have docstrings
- [ ] All functions have type hints
- [ ] No partial implementations (either complete or TODO)
- [ ] config.py loads ALL values from environment
- [ ] Rate limiting integrated in OpenAI client
- [ ] Caching implemented for embeddings
- [ ] All 7 phases of workflow implemented in orchestrator.py
- [ ] Flask app has all 4 endpoints: /analyze, /status, /results, /visualization
- [ ] Output generates: results.json, metadata.json, visualization/index.html, logs/
- [ ] README.md has setup and usage instructions

## EXAMPLE COMPONENT STRUCTURE

```python
"""
Module: src/data/loader.py
Purpose: Load and parse CSV data into Comment objects.
"""

import logging
from pathlib import Path
from typing import List

import pandas as pd

from src.core.models import Comment
from src.core.exceptions import DataException, FileNotFoundError, CSVParsingError
from config import Config

logger = logging.getLogger(__name__)


class CSVLoader:
    """
    Loads YouTube comments data from CSV file.
    
    Handles encoding issues and creates Comment objects from raw CSV data.
    """
    
    def __init__(self, config: Config):
        """
        Initialize CSV loader.
        
        Args:
            config: Configuration object with settings
        """
        self.config = config
        logger.info("[CSVLoader] Initialized")
    
    def load_csv(self, file_path: str) -> List[Comment]:
        """
        Load comments from CSV file.
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            List of Comment objects
            
        Raises:
            FileNotFoundError: If file does not exist
            CSVParsingError: If CSV cannot be parsed
            DataException: For other data loading errors
        """
        logger.info(f"[CSVLoader] Loading CSV from {file_path}")
        
        # Validate file exists
        if not Path(file_path).exists():
            logger.error(f"[CSVLoader] File not found: {file_path}")
            raise FileNotFoundError(f"CSV file not found: {file_path}")
        
        # Try UTF-8 first, fallback to latin-1
        encoding = 'utf-8'
        try:
            df = pd.read_csv(file_path, encoding=encoding)
            logger.info(f"[CSVLoader] Loaded with {encoding} encoding")
        except UnicodeDecodeError:
            logger.warning(f"[CSVLoader] UTF-8 failed, trying latin-1")
            encoding = 'latin-1'
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                logger.info(f"[CSVLoader] Loaded with {encoding} encoding")
            except Exception as e:
                logger.error(f"[CSVLoader] Failed to load CSV: {e}", exc_info=True)
                raise CSVParsingError(f"Could not parse CSV: {e}") from e
        except Exception as e:
            logger.error(f"[CSVLoader] Failed to load CSV: {e}", exc_info=True)
            raise DataException(f"Error loading CSV: {e}") from e
        
        # Validate required columns
        required_columns = ['id', 'url', 'content', 'author_id', 'parent_id']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"[CSVLoader] Missing columns: {missing_columns}")
            raise CSVParsingError(f"Missing required columns: {missing_columns}")
        
        # Convert to Comment objects
        comments = []
        for idx, row in df.iterrows():
            try:
                comment = Comment(
                    id=str(row['id']),
                    url=str(row['url']),
                    content=str(row['content']),
                    author_id=str(row['author_id']),
                    parent_id=str(row['parent_id'])
                )
                comments.append(comment)
            except Exception as e:
                logger.warning(f"[CSVLoader] Skipping row {idx}: {e}")
                continue
        
        logger.info(f"[CSVLoader] Loaded {len(comments)} comments from {len(df)} rows")
        return comments
```

## SUCCESS CRITERIA

Implementation is complete when:
1. All files from priority phases 1-7 are implemented
2. System can run end-to-end: CSV input → JSON + HTML output
3. All validation checklist items pass
4. No errors when running with valid input
5. Comprehensive logs generated in all 3 log files
6. results.json matches structure in SYSTEM_DESIGN.md section 8.2
7. visualization/index.html renders correctly in browser

## CONSTRAINTS

- Python 3.10+
- Only use dependencies listed in requirements specification
- Must work with OpenAI API (no other providers)
- Flask for web framework (no alternatives)
- Follow system design exactly (no architectural changes)
- Code must be production-ready (not prototype quality)

## REFERENCE DOCUMENTS

- SYSTEM_DESIGN.md: Complete architectural specification
- Refer to specific sections for detailed requirements

## OUTPUT EXPECTATIONS

When you implement:
1. Create files in correct directory structure
2. Implement completely or skip with TODO
3. Include all error handling and logging
4. Add docstrings and type hints
5. Follow all critical rules
6. Test that code is syntactically correct
7. Ensure no hardcoded values

Begin implementation starting with Phase 1 (Foundation), then proceed through phases sequentially.
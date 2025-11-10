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
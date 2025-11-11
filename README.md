# YouTube Comments Analysis System - Assesment project

<div align="center">
  <img src="static/home.png" alt="YouTube Comments Analysis System" width="600" />
</div>

Multi-agent comment analysis system featuring semantic search, LLM-based categorization, and automated insight extraction with comprehensive analytics pipeline.

## Features

- Web UI for easy analysis and visualization
- Automated video discovery and comment grouping
- Sentiment analysis with distribution breakdown
- Topic clustering and labeling (top 5 topics per video)
- Question identification and ranking
- Dynamic hypothesis generation for comment categories
- Hybrid search (semantic + LLM ranking)
- Session persistence for reusing embeddings
- Live categorization of new comments
- Comprehensive logging and error handling
- Cost-conscious API usage with caching

## Prerequisites

- Python 3.10+
- OpenAI API key
- Input CSV file with YouTube comments

## Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI API key
   ```

3. **Verify setup**
   ```bash
   python -c "from config import Config; Config.validate(); print('Configuration valid!')"
   ```

## Usage

### Option 1: All-in-One Analysis (Recommended)

The fastest way to analyze your data is using the complete pipeline:

```bash
python analyze.py dataset.csv
```

**What it does:**
- Automatically runs all 7 analysis steps (see below)
- Generates complete results in `output/run-{timestamp}/`
- Typically takes 3-5 minutes for ~4,000 comments
- Creates reusable session for future queries

**Options:**
```bash
# With custom logging
python analyze.py dataset.csv --log-level DEBUG

# Alternative syntax
python analyze.py --csv dataset.csv
```

**Output:**
```
================================================================================
YouTube Comments Analysis System
================================================================================
CSV File: dataset.csv

Configuration validated
Initializing system...

Starting analysis...
This may take several minutes depending on the number of comments.
--------------------------------------------------------------------------------
[Orchestrator] Phase 1: Loading and validating data
[Orchestrator] Phase 1 complete - 4188 comments
[Orchestrator] Phase 2: Discovering videos
[Orchestrator] Phase 2 complete - 5 videos
[Orchestrator] Phase 3: Generating embeddings
[Orchestrator] Phase 3 complete
[Orchestrator] Phase 4: Generating search specs
[Orchestrator] Phase 4 complete
[Orchestrator] Phase 5: Executing searches
[Orchestrator] Phase 5 complete
[Orchestrator] Phase 6: Performing analytics
[Orchestrator] Phase 6 complete
[Orchestrator] Phase 7: Generating outputs
[Orchestrator] Phase 7 complete
--------------------------------------------------------------------------------

Analysis complete!
Run ID: 20251110_143215_892341
Results: output/run-20251110_143215_892341/results.json
Logs: output/run-20251110_143215_892341/logs/
```

### Option 2: Step-by-Step Analysis (For Development/Debugging)

Run individual steps manually for testing or debugging:

#### Step 1: Load & Validate Data
```bash
python step1_load_validate.py dataset.csv
```
**What it does:**
- Loads CSV file with YouTube comments
- Validates required columns and data types
- Cleans text (removes HTML, normalizes whitespace)
- Detects and removes spam
- Saves: `intermediate/step1_comments.pkl`

#### Step 2: Discover Videos
```bash
python step2_discover_videos.py intermediate/
```
**What it does:**
- Groups comments by parent video using URL patterns
- Identifies which entries are videos vs comments
- Handles orphaned comments (comments without parent videos)
- Validates exactly 5 videos discovered
- Saves: `intermediate/step2_videos.pkl`

#### Step 3: Generate Embeddings
```bash
python step3_generate_embeddings.py intermediate/
```
**What it does:**
- Generates 1536-dimensional embedding vectors for each comment
- Uses OpenAI text-embedding-3-small model
- Caches embeddings to avoid redundant API calls
- Required for semantic search
- Saves: `intermediate/step3_videos_embedded.pkl`, `intermediate/embeddings_cache.pkl`

#### Step 4: Generate Search Specifications
```bash
python step4_generate_specs.py intermediate/
```
**What it does:**
- Loads 3 static search specs (universal for all videos)
- Generates 5 dynamic search specs per video using GPT-4o
- Analyzes 10 sample comments to understand video context
- Creates targeted queries for finding valuable comments
- Saves: `intermediate/step4_videos_with_specs.pkl`

#### Step 5: Execute Searches
```bash
python step5_execute_searches.py intermediate/
```
**What it does:**
- Executes all search specs (static + dynamic) on each video
- Uses two-phase hybrid search: semantic filtering + LLM ranking
- Finds top 30 most relevant comments per search
- Extracts insights from matched comments
- Saves: `intermediate/step5_search_results.pkl`

#### Step 6: Perform Analytics
```bash
python step6_analytics.py intermediate/
```
**What it does:**
- Sentiment analysis: Scores each comment 0-1 (negative to positive)
- Topic extraction: Clusters comments and identifies top 5 topics
- Question finding: Extracts and ranks top 5 questions by engagement
- Generates aggregate statistics
- Saves: `intermediate/step6_analytics.pkl`

#### Step 7: Generate Output
```bash
python step7_output.py intermediate/ --csv-file dataset.csv
```
**What it does:**
- Creates timestamped output directory
- Saves `results.json` with complete analysis
- Saves `metadata.json` with run statistics
- Saves `session.pkl` for reuse
- Generates HTML visualization
- Saves: `output/run-{timestamp}/` with all files

### Option 3: Web UI

For interactive visualization and search:

```bash
python app.py
```

Then open your browser to `http://localhost:5000`

**Features:**
- **Home Tab**: Load and view analysis sessions
- **Algorithm Tab**: View system architecture and pipeline
- **Search Tab**: Semantic search across comments with LLM ranking
- **Analysis Tab**: View sentiment, topics, and questions
- **Results Tab**: Browse detailed results per video

### Option 4: CLI Search Tool

For testing semantic search from the command line:

```bash
# Basic search
python search_cli.py 20251110_070350 "technical questions about performance"

# Search specific video
python search_cli.py 20251110_070350 "feature requests" --video-id FqIMu4C87SM

# Get more results
python search_cli.py 20251110_070350 "bugs and issues" --top-k 20
```

**What it does:**
- Loads a previous analysis session (with embeddings)
- Performs semantic search using two-phase hybrid algorithm
- Displays relevance scores and extracted insights
- Useful for testing and debugging search queries

**Output:**
```
Loading session: 20251110_070350...
Searching video: FqIMu4C87SM (977 comments)
Initializing search engine...

================================================================================
SEARCH RESULTS FOR: technical questions about performance
================================================================================
Video: https://youtube.com/watch?v=FqIMu4C87SM
Total comments searched: 977
Results found: 10
Execution time: 12.34s
API calls made: 3
================================================================================

[RESULT 1] Relevance: 0.923
Author: UCxyz123
URL: https://youtube.com/watch?v=FqIMu4C87SM&lc=...
Content: How do I optimize performance for older devices? I'm getting...
--------------------------------------------------------------------------------
```

## Input CSV Format

Required columns:
- `id`: Unique comment/video identifier
- `url`: YouTube URL with comment anchor
- `content`: Text content
- `author_id`: YouTube channel ID
- `parent_id`: Video ID for comments, self-reference for videos

## Output Structure

After analysis, results are saved in `output/run-{timestamp}/`:

```
output/run-{timestamp}/
├── results.json          # Complete analysis results
├── metadata.json         # Processing metadata
├── session.pkl          # Session data for reuse
├── embeddings_cache.pkl  # Cached embeddings
└── logs/
    ├── app.log          # General application logs
    ├── openai_calls.log # API call details
    └── errors.log       # Error logs
```

### Session Persistence

The system automatically saves sessions including:
- All embeddings (reused for categorizing new comments)
- Video groupings and metadata
- Analytics results
- Search specifications

This allows you to:
- Categorize new comments without reprocessing
- Reload and view previous analysis
- Build on existing analysis incrementally

## Features in Detail

### 1. Automated Analysis
- Upload CSV and get complete analysis in minutes
- 5 videos automatically discovered and grouped
- Comments cleaned and validated

### 2. AI-Powered Insights
- Sentiment analysis (0-100% scale)
- Topic clustering (top 5 topics per video)
- Question identification (top 5 questions)
- Dynamic search spec generation

### 3. Session Persistence
- All embeddings saved for reuse
- Fast categorization of new comments
- Browse previous analysis sessions

### 4. Live Categorization
- Add new comments via web UI
- See which topic they match
- Get sentiment and category predictions
- Uses embeddings from existing analysis

### 5. Web Visualization
- Interactive UI with tabs
- Sentiment distribution metrics
- Topic breakdowns with keywords
- Question lists with engagement scores
- Search results organized by category

### 6. Advanced Semantic Search

The system implements a sophisticated two-phase hybrid search algorithm that combines the speed of semantic similarity with the accuracy of LLM ranking.

#### Search Algorithm Architecture

```
Phase 1: Semantic Filtering (Fast)
├─ Convert search query to embedding vector (1536-dim)
├─ Compute cosine similarity with all comment embeddings
├─ Select top 60 candidates (2x requested results)
└─ Apply filters (min_length, exclude_spam, require_question_mark)

Phase 2: LLM Ranking (Accurate)
├─ Batch filtered candidates (20 per batch)
├─ Use GPT-4o-mini to score relevance (0.0-1.0)
├─ Consider query context and search intent
├─ Extract insights (sentiment, topics, suggestions)
└─ Return top-k results sorted by LLM relevance score
```

#### Why This Approach?

1. **Speed**: Semantic filtering reduces search space from thousands to ~60 candidates in milliseconds
2. **Accuracy**: LLM ranking captures semantic nuances that embeddings alone miss
3. **Cost-Effective**: Only calls LLM for pre-filtered candidates, not entire dataset
4. **Flexible**: Supports custom filters and field extraction per search spec
5. **Scalable**: Batching enables efficient processing of large comment sets

#### Using the CLI Search Tool

For testing and debugging, use the standalone CLI search tool:

```bash
# Basic search
python search_cli.py 20251110_070350 "technical questions about performance"

# Search specific video
python search_cli.py 20251110_070350 "feature requests" --video-id FqIMu4C87SM

# Get more results
python search_cli.py 20251110_070350 "bugs and issues" --top-k 20
```

**Output Example:**
```
================================================================================
SEARCH RESULTS FOR: technical questions about performance
================================================================================
Video: https://youtube.com/watch?v=FqIMu4C87SM
Total comments searched: 977
Results found: 10
Execution time: 12.34s
API calls made: 3
================================================================================

[RESULT 1] Relevance: 0.923
Author: UCxyz123
URL: https://youtube.com/watch?v=FqIMu4C87SM&lc=...
Content: How do I optimize performance for older devices? I'm getting...
--------------------------------------------------------------------------------

[RESULT 2] Relevance: 0.887
Author: UCabc456
URL: https://youtube.com/watch?v=FqIMu4C87SM&lc=...
Content: Great video, but I noticed significant lag when running...
--------------------------------------------------------------------------------

EXTRACTED INSIGHTS:
  average_sentiment: 0.65
  common_themes: ['performance', 'optimization', 'device', 'speed', 'memory']
  suggestions: ['optimize for older devices', 'reduce memory usage', 'add performance mode']
```

#### Using Web UI Semantic Search

The web interface now uses the full semantic search engine:

1. Load an analysis session from the home page
2. Enter your search query in natural language
3. Optionally filter by specific videos
4. View results ranked by relevance with LLM scoring

**Features:**
- Natural language queries (not just keyword matching)
- Semantic understanding of intent
- LLM-powered relevance scoring
- Cross-video search with filtering
- Real-time results with progress indicators

**Example Queries:**
- "comments asking about pricing or cost"
- "feedback suggesting new features"
- "technical questions about installation"
- "complaints about bugs or errors"
- "positive reviews and testimonials"

## Configuration

All configuration is managed through environment variables. See `.env.example` for all options.

Required:
- `OPENAI_API_KEY`: Your OpenAI API key

Key optional settings (with defaults):
- `COMPLETION_MODEL`: gpt-4-turbo
- `FAST_COMPLETION_MODEL`: gpt-3.5-turbo
- `EMBEDDING_MODEL`: text-embedding-3-small
- `BATCH_SIZE`: 20
- `NUM_TOPICS`: 5
- `NUM_QUESTIONS`: 5

## Cost Management

- Embeddings cached to avoid redundant API calls
- Batch processing to reduce overhead
- Smart model selection (GPT-3.5 for simple tasks)
- Rate limiting to stay within API limits
- Cost estimation in metadata
- Session reuse eliminates re-embedding

## Development

Project structure:
```
comment-probe-ai/
├── app.py                 # Flask application with web UI
├── analyze.py             # All-in-one CLI analysis script
├── search_cli.py          # Standalone semantic search tool
├── config.py              # Configuration
├── templates/             # Web UI templates
├── static/                # JavaScript, CSS for web UI
├── src/
│   ├── core/             # Models, orchestrator, session manager
│   ├── data/             # Data pipeline (loader, validator, cleaner)
│   ├── ai/               # AI components (OpenAI, embedder, search engine)
│   ├── analytics/        # Analytics (sentiment, topics, questions)
│   ├── output/           # Output generation (results, visualization)
│   └── utils/            # Utilities (logging, caching, rate limiting)
├── step1_load_validate.py        # Modular pipeline steps
├── step2_discover_videos.py      # (for development & debugging)
├── step3_generate_embeddings.py
├── step4_generate_specs.py
├── step5_execute_searches.py
├── step6_analytics.py
├── step7_output.py
├── output/               # Analysis results (by run ID)
└── logs/                 # Application logs
```

## Troubleshooting

### API Key Issues
- Ensure `OPENAI_API_KEY` is set in `.env`
- Verify key starts with `sk-`

### Rate Limiting
- System automatically handles with backoff
- Adjust `REQUESTS_PER_MINUTE` if needed

### Memory Issues
- Reduce `BATCH_SIZE` and `EMBEDDING_BATCH_SIZE`

### Session Not Found
- Ensure session was fully analyzed
- Check `output/` directory for run folders

## License

See LICENSE file.

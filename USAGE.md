# YouTube Comments Analysis System - Usage Guide

Complete guide for using the system in modular steps, with web UI, API, and CLI options.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Modular Step-by-Step Analysis](#modular-step-by-step-analysis)
3. [All-in-One Analysis](#all-in-one-analysis)
4. [Web UI Usage](#web-ui-usage)
5. [REST API Usage](#rest-api-usage)
6. [Vector Database (ChromaDB)](#vector-database-chromadb)
7. [Session Management](#session-management)
8. [Categorizing New Comments](#categorizing-new-comments)
9. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 3. Verify setup
python -c "from config import Config; Config.validate(); print('✓ Configuration valid!')"
```

### Fastest Path to Results

```bash
# Option A: Use Web UI (recommended for beginners)
python app.py
# Open http://localhost:5000

# Option B: Use CLI for quick analysis
python analyze.py dataset.csv
```

---

## Modular Step-by-Step Analysis

For testing, debugging, or understanding each phase individually, use the modular scripts. Each step saves intermediate state and can be run independently.

### Step 1: Load and Validate CSV

```bash
python step1_load_validate.py dataset.csv
```

**What it does:**
- Loads CSV file with YouTube comments
- Validates data structure and content
- Fixes recoverable issues
- Cleans text (removes HTML, normalizes whitespace)
- Detects and removes spam

**Output:**
- `intermediate/step1_comments.pkl` - Cleaned and validated comments

**Validation Report:**
```
STEP 1: LOAD AND VALIDATE DATA
CSV File: dataset.csv

Loading CSV...
Loaded 1234 comments

Validating comments...
✓ All comments valid

Fixing recoverable issues...
✓ Fixed issues, 1234 comments remaining

Cleaning comments...
✓ Cleaned 1234 comments

Detecting spam...
✓ Removed 12 spam comments
✓ Final count: 1222 valid comments

✓ Saved to: intermediate/step1_comments.pkl
```

### Step 2: Discover Videos and Group Comments

```bash
python step2_discover_videos.py intermediate/
```

**What it does:**
- Groups comments by parent video
- Discovers video metadata
- Validates grouping logic
- Identifies orphaned comments

**Output:**
- `intermediate/step2_videos.pkl` - Videos with grouped comments

**Discovery Report:**
```
STEP 2: DISCOVER VIDEOS

Loading comments from: intermediate/step1_comments.pkl
✓ Loaded 1222 comments

Discovering videos...
✓ Discovered 5 videos
✓ Found 0 orphaned comments

Video Summary:
1. Video ID: UCxyz123
   URL: https://youtube.com/watch?v=abc123
   Comments: 245
   Title: How to Build AI Systems...

2. Video ID: UCxyz124
   ...
```

### Step 2.5: Reassign Orphaned Comments (Optional)

```bash
python step2.5_reassign_orphaned.py intermediate/
```

**What it does:**
- Attempts to recover orphaned comments by reassigning them to videos
- Uses 3-pass hybrid approach:
  1. Pattern matching on parent IDs
  2. Semantic similarity with threshold 0.85
  3. Creates "Unassigned" virtual video for remaining
- Analyzes parent ID patterns
- Embeds orphaned comments for similarity matching
- Tracks reassignment statistics

**Output:**
- `intermediate/step2.5_videos_reassigned.pkl` - Videos with reassigned comments

**IMPORTANT WARNINGS:**

**⚠️ Risk of Data Contamination:**
Orphaned comments are comments where the `parent_id` doesn't match any of your 5 video IDs. They could be:
1. **Replies to OTHER comments** (not top-level video comments)
2. **Comments on DIFFERENT videos** not in your dataset
3. **Data extraction errors or ID mismatches**

**Reassigning them based on semantic similarity WILL introduce noise** because they may genuinely belong to completely different contexts or videos outside your dataset!

**⚠️ Use With Extreme Caution:**
- Only use if you're confident orphaned comments are genuinely related to your videos
- High similarity threshold (0.85) reduces false positives but doesn't eliminate them
- Reassigned comments are tagged with `metadata['reassigned']` for filtering
- By default, reassigned comments are EXCLUDED from analytics (see config below)
- Consider analyzing original comments only for accurate insights

**When to Use:**
- ✅ Small, controlled dataset where you know all comments are related
- ✅ Exploratory analysis where some noise is acceptable
- ❌ Production analytics requiring high accuracy
- ❌ When orphaned comments likely belong to external videos

**Performance Note:**
- Can take 5-15 minutes for large datasets (1,954 orphaned × 5 videos × ~700 comments each)
- Makes OpenAI API calls for embedding orphaned comments
- Use `--skip-similarity` flag for pattern-only matching (faster, no API costs)

**Reassignment Report:**
```
STEP 2.5: REASSIGN ORPHANED COMMENTS (OPTIONAL)

Loaded 5 videos
Found 1954 orphaned comments

Initializing AI components for semantic matching...
Components initialized

Starting reassignment process...
======================================================================

[OrphanedCommentReassigner] Analyzing 1954 orphaned comments
[OrphanedCommentReassigner] Found 45 unique parent IDs

Pass 1: Pattern matching
[OrphanedCommentReassigner] Pattern matching: Recovered 234/1954 comments
  - Video FqIMu4C87SM: +89 comments
  - Video ubSE4me-sE8: +67 comments
  - Video rdMyaxhWQ8k: +78 comments

Pass 2: Semantic similarity matching
[OrphanedCommentReassigner] Embedding 1720 orphaned comments
[OrphanedCommentReassigner] Similarity matching: Recovered 1356/1720 comments
  - Video FqIMu4C87SM: +312 comments (avg similarity: 0.782)
  - Video ubSE4me-sE8: +289 comments (avg similarity: 0.754)
  - Video rdMyaxhWQ8k: +445 comments (avg similarity: 0.791)
  - Video YKbDApzT1iw: +298 comments (avg similarity: 0.768)
  - Video 2yyCnKcSrUg: +12 comments (avg similarity: 0.723)

Pass 3: Creating unassigned group
[OrphanedCommentReassigner] Created unassigned video with 364 comments

======================================================================

Reassignment Summary:
----------------------------------------------------------------------
Total orphaned comments: 1954
Recovered by pattern matching: 234
Recovered by semantic similarity: 1356
Remaining unassigned: 364
Recovery rate: 81.4%

Updated Video Summary:
----------------------------------------------------------------------
1. Video ID: FqIMu4C87SM
   Total comments: 977
   Original: 576
   Reassigned: 401

2. Video ID: ubSE4me-sE8
   Total comments: 867
   Original: 511
   Reassigned: 356

3. Video ID: rdMyaxhWQ8k
   Total comments: 1875
   Original: 1352
   Reassigned: 523

4. Video ID: YKbDApzT1iw
   Total comments: 1886
   Original: 1588
   Reassigned: 298

5. Video ID: 2yyCnKcSrUg
   Total comments: 173
   Original: 161
   Reassigned: 12

6. Video ID: UNASSIGNED
   Total comments: 364
   Original: 0
   Reassigned: 364
   [VIRTUAL: Unassigned Comments Group]

Saved to: intermediate/step2.5_videos_reassigned.pkl
```

**Configuration Options:**
```bash
# Enable/disable orphan reassignment
ENABLE_ORPHAN_REASSIGNMENT=true

# Minimum cosine similarity for reassignment (0.85 = high confidence, reduces false positives)
SEMANTIC_SIMILARITY_THRESHOLD=0.85

# Create virtual UNASSIGNED video for remaining orphaned comments
CREATE_UNASSIGNED_VIDEO=true

# Skip reassigned comments in analytics (RECOMMENDED to avoid noise)
SKIP_REASSIGNED_IN_ANALYTICS=true

# Skip UNASSIGNED virtual video in analytics
SKIP_UNASSIGNED_IN_ANALYTICS=true
```

**Metadata Tracking:**
All reassigned comments are tagged with `metadata['reassigned']` field:
- `'pattern_exact'` - Matched by exact parent ID
- `'pattern_substring'` - Matched by substring pattern
- `'pattern_url'` - Matched by extracting video ID from URL
- `'semantic'` - Matched by semantic similarity (includes `similarity_score`)
- `'unassigned'` - No match found, placed in UNASSIGNED group

This allows you to:
- Filter out reassigned comments in custom analysis
- Identify which comments may be noisy
- Compare analytics with/without reassigned comments
- Audit reassignment quality by checking similarity scores

### Step 3: Generate Embeddings

```bash
python step3_generate_embeddings.py intermediate/
```

**What it does:**
- Generates OpenAI embeddings for each comment
- Uses caching to avoid redundant API calls
- Shows progress and cost estimates
- Saves embeddings with comments

**Output:**
- `intermediate/step3_videos_embedded.pkl` - Videos with embeddings
- `intermediate/embeddings_cache.pkl` - Embedding cache

**Important Notes:**
- This step makes OpenAI API calls (costs money)
- Uses `text-embedding-3-small` by default
- Cached embeddings are reused automatically
- Can take several minutes for large datasets

**Progress Report:**
```
STEP 3: GENERATE EMBEDDINGS

Total comments to embed: 1222

Generating embeddings...

Video 1/5: UCxyz123
  Comments: 245
  ✓ Embedded: 245/245

Video 2/5: UCxyz124
  Comments: 312
  ✓ Embedded: 312/312
...

✓ Total embeddings generated: 1222/1222
✓ Cache hits: 89
✓ Cache misses: 1133
```

### Step 4: Generate Search Specifications

```bash
python step4_generate_specs.py intermediate/
```

**What it does:**
- Loads static search specs from config
- Generates dynamic search specs using GPT-4
- Analyzes comment patterns to create hypotheses
- Creates targeted search queries

**Output:**
- `intermediate/step4_videos_with_specs.pkl` - Videos with search specs

**Search Specs:**
- **Static specs**: Predefined in `config.py` (e.g., "highly engaged comments")
- **Dynamic specs**: AI-generated based on actual comment patterns

**Specs Report:**
```
STEP 4: GENERATE SEARCH SPECIFICATIONS

Loading static search specs...
✓ Loaded 3 static specs:
  1. Find highly engaged comments with multiple replies...
  2. Identify comments that suggest improvements...
  3. Find comments asking specific questions...

Generating dynamic search specs...

Video 1/5: UCxyz123
  Generating dynamic specs...
  ✓ Generated 5 dynamic specs:
    1. Find comments discussing integration challenges...
    2. Find comments about pricing concerns...
    ...

✓ Total static specs: 15
✓ Total dynamic specs: 25
✓ Total specs: 40
```

### Step 5: Execute Searches

```bash
python step5_execute_searches.py intermediate/
```

**What it does:**
- Executes all search specs (static + dynamic)
- Uses hybrid search: semantic filtering + LLM ranking
- Finds most relevant comments for each query
- Ranks results by relevance

**Output:**
- `intermediate/step5_search_results.pkl` - Search results for all specs

**Important Notes:**
- This step makes many OpenAI API calls (GPT-4 for ranking)
- Can be expensive for large datasets
- Results are ranked by relevance score

**Search Report:**
```
STEP 5: EXECUTE SEARCHES

Executing searches...

Video 1/5: UCxyz123
  Total search specs: 8
  Executing 3 static specs...
    1. Find highly engaged comments... → 15 results
    2. Identify comments that suggest... → 23 results
    3. Find comments asking specific... → 12 results
  Executing 5 dynamic specs...
    1. Find comments discussing integration... → 8 results
    ...

✓ Total searches executed: 40
✓ Total comments found: 342
```

### Step 6: Perform Analytics

```bash
python step6_analytics.py intermediate/
```

**What it does:**
- Sentiment analysis (positive/neutral/negative)
- Topic clustering using KMeans
- Question identification and ranking
- Generates analytics for each video

**Output:**
- `intermediate/step6_analytics.pkl` - Complete analytics results

**Analytics Report:**
```
STEP 6: PERFORM ANALYTICS

Video 1/5: UCxyz123
  Analyzing 245 comments...
  - Sentiment analysis...
    ✓ Overall sentiment: 0.73
    ✓ Distribution: Positive=156, Neutral=67, Negative=22
  - Topic extraction...
    ✓ Extracted 5 topics:
      1. Integration Challenges (45 comments)
      2. Pricing Feedback (32 comments)
      3. Feature Requests (28 comments)
      ...
  - Question finding...
    ✓ Found 5 top questions

✓ Total topics extracted: 25
✓ Total questions found: 25
✓ Average sentiment score: 0.71
```

### Step 7: Generate Output Files

```bash
python step7_output.py intermediate/ --csv-file dataset.csv
```

**What it does:**
- Creates timestamped output directory
- Saves results.json with all analysis
- Saves metadata.json with processing info
- Saves session.pkl for reuse

**Output:**
- `output/run-{timestamp}/results.json` - Complete results
- `output/run-{timestamp}/metadata.json` - Processing metadata
- `output/run-{timestamp}/session.pkl` - Reusable session

**Output Report:**
```
STEP 7: GENERATE OUTPUT

Run ID: 20241110_152345_892341
Output directory: output/run-20241110_152345_892341

Saving results...
✓ Saved results to: output/run-20241110_152345_892341/results.json
✓ Saved metadata to: output/run-20241110_152345_892341/metadata.json

Saving session for reuse...
✓ Saved session to: output/run-20241110_152345_892341/session.pkl

Output Summary:
  Run ID: 20241110_152345_892341
  Videos: 5
  Comments: 1222

View results:
  python -m json.tool output/run-20241110_152345_892341/results.json

Use this session for categorization:
  Session ID: 20241110_152345_892341
```

---

## All-in-One Analysis

For production use or when you don't need to debug individual steps:

### CLI Script

```bash
python analyze.py dataset.csv
```

This runs all 7 steps automatically and produces the same output as the modular approach.

**Options:**
```bash
# With custom log level
python analyze.py dataset.csv --log-level DEBUG

# Alternative syntax
python analyze.py --csv dataset.csv
```

---

## Web UI Usage

### Starting the Web Server

```bash
python app.py
```

Open `http://localhost:5000` in your browser.

### Web UI Features

#### 1. Analyze Tab

- **Upload CSV**: Select your dataset.csv file
- **Click Analyze**: Runs complete 7-phase analysis
- **View Progress**: Real-time status updates
- **Get Results**: Automatic redirect to results when complete

#### 2. Sessions Tab

- **List All Sessions**: See all previous analysis runs
- **View Results**: Click on any session to see detailed results
- **Visualizations**:
  - Sentiment distribution charts
  - Topic breakdowns with keywords
  - Top questions by engagement
  - Search results by category

#### 3. Categorize Tab

- **Select Session**: Choose a previous analysis session
- **Enter Comment**: Type or paste a new comment
- **Categorize**: See where it fits in the analysis
- **Results**:
  - Sentiment score (0-1)
  - Most similar topic
  - Similarity score
  - Category (question/suggestion/issue/feedback)

---

## REST API Usage

The Flask app provides a REST API for integration with other tools.

### Start the API Server

```bash
python app.py
```

### Endpoints

#### 1. Health Check

```bash
curl http://localhost:5000/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "YouTube Comments Analysis System"
}
```

#### 2. Analyze CSV

```bash
curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{"csv_path": "dataset.csv"}'
```

**Response:**
```json
{
  "status": "complete",
  "run_id": "20241110_152345_892341",
  "message": "Analysis complete. Results available in output/run-20241110_152345_892341/"
}
```

#### 3. Get Results

```bash
curl http://localhost:5000/results/20241110_152345_892341
```

**Response:** JSON file with complete analysis results

#### 4. List All Runs

```bash
curl http://localhost:5000/runs
```

**Response:**
```json
{
  "runs": [
    "20241110_152345_892341",
    "20241110_143215_782134",
    "20241110_135412_671823"
  ],
  "count": 3
}
```

#### 5. Categorize New Comment

```bash
curl -X POST http://localhost:5000/categorize \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "20241110_152345_892341",
    "comment": "This is amazing! How do I integrate it with my app?"
  }'
```

**Response:**
```json
{
  "sentiment": 0.82,
  "similar_topic": "Integration Questions",
  "similarity_score": 0.87,
  "category": "question",
  "comment": "This is amazing! How do I integrate it with my app?"
}
```

---

## Vector Database (ChromaDB)

For large datasets or frequent similarity searches, use ChromaDB instead of pickle files.

### Why ChromaDB?

- **Fast similarity search**: Optimized for vector operations
- **Persistent storage**: Survives process restarts
- **Efficient memory usage**: Doesn't load all embeddings into RAM
- **Scalable**: Handles millions of embeddings

### Migrating to ChromaDB

```bash
# After Step 3 (embeddings generated)
python migrate_to_chromadb.py intermediate/step3_videos_embedded.pkl
```

**Migration Process:**
```
MIGRATE TO CHROMADB

Loading embeddings from: intermediate/step3_videos_embedded.pkl
✓ Loaded 5 videos
✓ Total comments: 1222
✓ Embedded comments: 1222

Initializing ChromaDB in: ./chroma_db
✓ ChromaDB initialized

Creating collection: comments
✓ Collection created

Adding embeddings to ChromaDB...

Video 1/5: UCxyz123
  Adding 245 embeddings...
  ✓ Added 245 embeddings
...

✓ Total embeddings added to ChromaDB: 1222

Collection Statistics:
  Name: comments
  Count: 1222
  Directory: ./chroma_db
```

### Using ChromaDB for Searches

ChromaDB is automatically used by the search engine when available. You can also query it directly:

```python
from src.utils.vector_store import VectorStore

# Initialize
vector_store = VectorStore(persist_directory="./chroma_db")

# Search for similar comments
results = vector_store.search(
    collection_name="comments",
    query_embedding=your_embedding,
    top_k=10
)

# Results: [(comment_id, distance, document), ...]
for comment_id, distance, text in results:
    print(f"{comment_id}: {text[:50]}... (distance: {distance:.3f})")
```

### Managing Collections

```python
from src.utils.vector_store import VectorStore

vector_store = VectorStore()

# List all collections
collections = vector_store.list_collections()
print(collections)

# Get statistics
stats = vector_store.get_statistics("comments")
print(f"Collection has {stats['count']} embeddings")

# Delete collection
vector_store.delete_collection("comments")
```

---

## Session Management

Sessions allow you to reuse expensive computations (embeddings, analytics) across runs.

### What's Saved in a Session?

- All comment embeddings
- Video groupings and metadata
- Analytics results (sentiment, topics, questions)
- Search specifications (static + dynamic)
- Processing metadata

### Loading a Previous Session

```python
from src.core.session_manager import SessionManager

session_manager = SessionManager()

# Load session
session = session_manager.load_session("20241110_152345_892341")

videos = session['videos']
analytics = session['analytics']
metadata = session['metadata']
```

### Session File Structure

```
output/run-20241110_152345_892341/
├── results.json          # Human-readable results
├── metadata.json         # Processing metadata
├── session.pkl          # Complete session data
├── logs/
│   ├── app.log          # General logs
│   ├── openai_calls.log # API call details
│   └── errors.log       # Error logs
└── visualization/       # Future: charts and graphs
```

---

## Categorizing New Comments

Once you have a session, you can categorize new comments without re-running the entire analysis.

### Via Web UI

1. Open http://localhost:5000
2. Go to "Categorize" tab
3. Select a session from dropdown
4. Enter new comment text
5. Click "Categorize"
6. View results: sentiment, topic match, category

### Via REST API

```bash
curl -X POST http://localhost:5000/categorize \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "20241110_152345_892341",
    "comment": "Great tutorial! One question though - how do I handle rate limits?"
  }'
```

### Via Python Script

```python
from src.core.session_manager import SessionManager
from src.ai.openai_client import OpenAIClient
from src.ai.embedder import Embedder
from src.utils.cache_manager import CacheManager
from src.utils.rate_limiter import RateLimiter
from src.utils.helpers import compute_cosine_similarity
from src.core.models import Comment
from config import Config

# Load session
session_manager = SessionManager()
session = session_manager.load_session("20241110_152345_892341")

# Initialize components
cache_mgr = CacheManager(Config.CACHE_DIR)
rate_limiter = RateLimiter(Config.REQUESTS_PER_MINUTE, Config.TOKENS_PER_MINUTE)
openai_client = OpenAIClient(Config.OPENAI_API_KEY, rate_limiter)
embedder = Embedder(openai_client, cache_mgr)

# Create new comment
new_comment_text = "How do I integrate this with Django?"
new_embedding = embedder.embed_text(new_comment_text)

# Find most similar topic
videos = session['videos']
best_similarity = 0
best_topic = "Unknown"

for video in videos:
    for comment in video.comments[:100]:  # Sample for performance
        if comment.embedding:
            similarity = compute_cosine_similarity(new_embedding, comment.embedding)
            if similarity > best_similarity:
                best_similarity = similarity
                best_video = video

# Get topic from analytics
analytics = session['analytics']
if best_video and best_video.id in analytics:
    topics = analytics[best_video.id].top_topics
    if topics:
        best_topic = topics[0].topic_name

print(f"Most similar topic: {best_topic}")
print(f"Similarity score: {best_similarity:.3f}")
```

---

## Troubleshooting

### Common Issues

#### 1. API Key Not Found

**Error:**
```
ConfigException: OPENAI_API_KEY is required
```

**Solution:**
```bash
# Check .env file exists
ls -la .env

# Verify it contains your key
cat .env | grep OPENAI_API_KEY

# Should show:
# OPENAI_API_KEY=sk-...
```

#### 2. Rate Limiting

**Error:**
```
RateLimitError: Rate limit exceeded
```

**Solution:**
```bash
# Edit .env to reduce request rate
REQUESTS_PER_MINUTE=30  # Default is 60
TOKENS_PER_MINUTE=50000  # Default is 90000
```

#### 3. Out of Memory

**Error:**
```
MemoryError: Unable to allocate array
```

**Solution:**
```bash
# Reduce batch sizes in .env
BATCH_SIZE=10            # Default is 20
EMBEDDING_BATCH_SIZE=50  # Default is 100

# Or use ChromaDB instead of loading all embeddings
python migrate_to_chromadb.py intermediate/step3_videos_embedded.pkl
```

#### 4. Session Not Found

**Error:**
```
Session 20241110_152345_892341 not found
```

**Solution:**
```bash
# List available sessions
ls -la output/

# Verify the run directory exists
ls -la output/run-20241110_152345_892341/

# Check for session.pkl
ls -la output/run-20241110_152345_892341/session.pkl
```

#### 5. CSV Format Issues

**Error:**
```
KeyError: 'content' or 'id'
```

**Solution:**

Ensure your CSV has these required columns:
- `id`: Unique identifier
- `url`: YouTube URL
- `content`: Comment text
- `author_id`: Author identifier
- `parent_id`: Parent video/comment ID

Example CSV:
```csv
id,url,content,author_id,parent_id
comment1,https://youtube.com/...,Great video!,user123,video1
comment2,https://youtube.com/...,How do I...,user456,video1
```

#### 6. Import Errors

**Error:**
```
ModuleNotFoundError: No module named 'chromadb'
```

**Solution:**
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Or install specific package
pip install chromadb>=0.4.0
```

### Debug Mode

For detailed logging:

```bash
# Set DEBUG level in .env
LOG_LEVEL=DEBUG

# Or pass to CLI
python analyze.py dataset.csv --log-level DEBUG

# Check logs
tail -f logs/app.log
tail -f logs/errors.log
```

### Performance Optimization

For faster analysis:

1. **Use ChromaDB** instead of pickle for embeddings
2. **Reduce NUM_TOPICS and NUM_QUESTIONS** in .env
3. **Use faster model** for simple tasks:
   ```bash
   FAST_COMPLETION_MODEL=gpt-3.5-turbo
   ```
4. **Increase batch sizes** (if you have enough RAM):
   ```bash
   BATCH_SIZE=50
   EMBEDDING_BATCH_SIZE=200
   ```

### Cost Reduction

To minimize OpenAI API costs:

1. **Cache embeddings**: Always reuse sessions
2. **Reduce dynamic specs**: Set `NUM_DYNAMIC_SPECS=3` in config
3. **Sample comments**: For testing, use a smaller CSV
4. **Use cheaper models**:
   ```bash
   COMPLETION_MODEL=gpt-3.5-turbo
   EMBEDDING_MODEL=text-embedding-3-small
   ```

---

## Next Steps

- Explore the codebase in `src/` directory
- Check `SYSTEM_DESIGN.md` for architecture details
- Review `README.md` for project overview
- Check logs in `logs/` for debugging

For questions or issues, check the logs directory or review error messages carefully.

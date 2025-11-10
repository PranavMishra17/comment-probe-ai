# YouTube Comments Analysis System

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

### Option 1: Web UI (Recommended)

The easiest way to use the system is through the web interface:

```bash
python app.py
```

Then open your browser to `http://localhost:5000`

The web UI provides:
- **Analyze Tab**: Upload and analyze your CSV files
- **Sessions Tab**: View all analysis results and visualizations
- **Categorize Tab**: Add new comments and see where they fit

### Option 2: Command Line

For direct command-line analysis:

```bash
python analyze.py dataset.csv
```

Or with options:

```bash
python analyze.py --csv dataset.csv --log-level DEBUG
```

### Option 3: REST API

For integration with other tools:

#### Analyze CSV
```bash
curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{"csv_path": "dataset.csv"}'
```

#### Get Results
```bash
curl http://localhost:5000/results/20241110_143215_892341
```

#### Categorize New Comment
```bash
curl -X POST http://localhost:5000/categorize \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "20241110_143215_892341",
    "comment": "This is a great video, very helpful!"
  }'
```

Response:
```json
{
  "sentiment": 0.8,
  "similar_topic": "Positive Feedback",
  "similarity_score": 0.87,
  "category": "feedback"
}
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
├── analyze.py             # CLI script
├── config.py              # Configuration
├── templates/             # Web UI templates
├── src/
│   ├── core/             # Models, orchestrator, session manager
│   ├── data/             # Data pipeline
│   ├── ai/               # AI components
│   ├── analytics/        # Analytics
│   ├── output/           # Output generation
│   └── utils/            # Utilities
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

# YouTube Comments Analysis System

Multi-agent comment analysis system featuring semantic search, LLM-based categorization, and automated insight extraction with comprehensive analytics pipeline.

## Features

- Automated video discovery and comment grouping
- Sentiment analysis with distribution breakdown
- Topic clustering and labeling (top 5 topics per video)
- Question identification and ranking
- Dynamic hypothesis generation for comment categories
- Hybrid search (semantic + LLM ranking)
- Comprehensive logging and error handling
- Cost-conscious API usage with caching
- REST API with Flask

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

### Running the Flask API

```bash
python app.py
```

The API will start on `http://localhost:5000`

### API Endpoints

#### Health Check
```bash
curl http://localhost:5000/health
```

#### Analyze CSV
```bash
curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{"csv_path": "path/to/your/comments.csv"}'
```

Response:
```json
{
  "status": "complete",
  "run_id": "20241110_143215_892341",
  "message": "Analysis complete. Results available in output/run-20241110_143215_892341/"
}
```

#### Get Results
```bash
curl http://localhost:5000/results/20241110_143215_892341
```

#### List All Runs
```bash
curl http://localhost:5000/runs
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
├── embeddings_cache.pkl  # Cached embeddings
└── logs/
    ├── app.log          # General application logs
    ├── openai_calls.log # API call details
    └── errors.log       # Error logs
```

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

## System Architecture

7 processing phases:
1. Data Loading & Validation
2. Video Discovery
3. Embedding Generation
4. Search Spec Generation
5. Search Execution
6. Analytics (Sentiment, Topics, Questions)
7. Output Generation

## Cost Management

- Embeddings cached to avoid redundant API calls
- Batch processing to reduce overhead
- Smart model selection (GPT-3.5 for simple tasks)
- Rate limiting
- Cost estimation in metadata

## Development

Project structure:
```
comment-probe-ai/
├── app.py                 # Flask application
├── config.py              # Configuration
├── src/
│   ├── core/             # Models & orchestrator
│   ├── data/             # Data pipeline
│   ├── ai/               # AI components
│   ├── analytics/        # Analytics
│   ├── output/           # Output generation
│   └── utils/            # Utilities
└── logs/                 # Logs
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

## License

See LICENSE file.

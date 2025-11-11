"""
Visualization generator for Comment Probe results.

Generates a clean, formal HTML interface with algorithm documentation.
"""

import logging
import os
import json
from typing import List, Dict
from datetime import datetime

from src.core.models import Video, AnalyticsResult, ProcessingMetadata

logger = logging.getLogger(__name__)


class Visualizer:
    """
    Generates HTML visualization of results.
    """

    def __init__(self):
        """Initialize visualizer."""
        logger.info("[Visualizer] Initialized")

    def generate_html(
        self,
        videos: List[Video],
        analytics: Dict[str, AnalyticsResult],
        metadata: ProcessingMetadata,
        output_path: str
    ) -> None:
        """
        Generates HTML visualization.

        Args:
            videos: List of videos
            analytics: Analytics results
            metadata: Processing metadata
            output_path: Path to write HTML file
        """
        logger.info(f"[Visualizer] Generating HTML visualization: {output_path}")

        html = self._generate_html_content(videos, analytics, metadata)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        logger.info("[Visualizer] HTML generation complete")

    def _generate_html_content(
        self,
        videos: List[Video],
        analytics: Dict[str, AnalyticsResult],
        metadata: ProcessingMetadata
    ) -> str:
        """Generate complete HTML content."""

        # Prepare data for JSON embedding
        results_data = []
        for video in videos:
            video_analytics = analytics.get(video.id)
            if not video_analytics:
                continue

            video_data = {
                'video_id': video.id,
                'url': video.url,
                'title': video.content[:200] + '...' if len(video.content) > 200 else video.content,
                'comment_count': len(video.comments),
                'sentiment': {
                    'overall_score': video_analytics.sentiment_score,
                    'distribution': video_analytics.sentiment_distribution
                },
                'topics': [
                    {
                        'name': topic.topic_name,
                        'count': topic.comment_count,
                        'percentage': topic.percentage,
                        'keywords': topic.keywords,
                        'representative_comments': [
                            {
                                'content': comment.content[:300] + '...' if len(comment.content) > 300 else comment.content,
                                'relevance': comment.metadata.get('relevance_score', 0.0)
                            }
                            for comment in topic.representative_comments[:3]
                        ]
                    }
                    for topic in video_analytics.top_topics
                ],
                'questions': [
                    {
                        'text': q.question_text,
                        'category': q.category,
                        'relevance': q.relevance_score,
                        'engagement': q.engagement_score,
                        'is_answered': q.is_answered
                    }
                    for q in video_analytics.top_questions
                ]
            }
            results_data.append(video_data)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Comment Probe AI - Analysis Results</title>
    {self._get_css()}
</head>
<body>
    <div class="container">
        <header>
            <h1>COMMENT PROBE AI</h1>
            <div class="meta">
                Run ID: {metadata.run_id} | Videos: {len(videos)} | Comments: {metadata.total_comments}
            </div>
        </header>

        <section id="algorithm-section">
            <h2>ALGORITHM OVERVIEW</h2>
            {self._generate_algorithm_steps()}
        </section>

        <section id="results-section">
            <h2>ANALYSIS RESULTS</h2>
            <div id="videos-container"></div>
        </section>
    </div>

    <script>
        const resultsData = {json.dumps(results_data, indent=2)};
        {self._get_javascript()}
    </script>
</body>
</html>"""

    def _get_css(self) -> str:
        """Returns CSS styles with pixelated White/Black/Yellow theme."""
        return """<style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Courier New', monospace;
            background: #fff;
            color: #000;
            line-height: 1.6;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }

        header {
            background: #000;
            color: #ffeb3b;
            padding: 30px;
            text-align: center;
            border: 4px solid #000;
            margin-bottom: 30px;
        }

        header h1 {
            font-size: 48px;
            font-weight: bold;
            letter-spacing: 4px;
            image-rendering: pixelated;
        }

        .meta {
            color: #fff;
            font-size: 14px;
            margin-top: 10px;
            font-weight: bold;
        }

        h2 {
            background: #ffeb3b;
            color: #000;
            padding: 15px 20px;
            font-size: 24px;
            font-weight: bold;
            border: 4px solid #000;
            margin: 30px 0 20px;
        }

        h3 {
            background: #000;
            color: #ffeb3b;
            padding: 10px 15px;
            font-size: 18px;
            font-weight: bold;
            border: 3px solid #000;
            margin: 20px 0 10px;
        }

        .step-box {
            border: 3px solid #000;
            margin: 15px 0;
            background: #fff;
        }

        .step-header {
            background: #ffeb3b;
            color: #000;
            padding: 15px;
            cursor: pointer;
            font-weight: bold;
            font-size: 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 3px solid #000;
        }

        .step-header:hover {
            background: #000;
            color: #ffeb3b;
        }

        .step-toggle {
            font-weight: bold;
            font-size: 20px;
        }

        .step-content {
            padding: 20px;
            display: none;
            background: #fff;
            color: #000;
        }

        .step-content.active {
            display: block;
        }

        .step-content p {
            margin: 10px 0;
        }

        .step-content ul {
            margin: 10px 0 10px 30px;
        }

        .step-content li {
            margin: 5px 0;
        }

        .video-card {
            border: 4px solid #000;
            margin: 20px 0;
            background: #fff;
        }

        .video-header {
            background: #000;
            color: #ffeb3b;
            padding: 15px;
            font-weight: bold;
        }

        .video-title {
            font-size: 16px;
            margin: 5px 0;
        }

        .video-meta {
            font-size: 12px;
            color: #fff;
            margin-top: 5px;
        }

        .video-body {
            padding: 20px;
        }

        .stat-box {
            border: 3px solid #000;
            padding: 15px;
            margin: 15px 0;
            background: #ffeb3b;
        }

        .stat-title {
            font-weight: bold;
            font-size: 14px;
            margin-bottom: 10px;
            color: #000;
        }

        .stat-value {
            font-size: 32px;
            font-weight: bold;
            color: #000;
        }

        .distribution {
            display: flex;
            gap: 10px;
            margin-top: 10px;
        }

        .dist-item {
            flex: 1;
            border: 2px solid #000;
            padding: 10px;
            background: #fff;
            text-align: center;
        }

        .dist-label {
            font-size: 12px;
            font-weight: bold;
        }

        .dist-value {
            font-size: 24px;
            font-weight: bold;
            margin-top: 5px;
        }

        .topic-item, .question-item {
            border: 3px solid #000;
            padding: 15px;
            margin: 10px 0;
            background: #fff;
        }

        .topic-header, .question-header {
            font-weight: bold;
            font-size: 16px;
            margin-bottom: 10px;
        }

        .keywords {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin: 10px 0;
        }

        .keyword {
            background: #ffeb3b;
            color: #000;
            padding: 5px 10px;
            border: 2px solid #000;
            font-size: 12px;
            font-weight: bold;
        }

        .comment-sample {
            background: #f5f5f5;
            border: 2px solid #000;
            padding: 10px;
            margin: 5px 0;
            font-size: 13px;
        }

        .relevance {
            color: #666;
            font-size: 11px;
            margin-top: 5px;
        }

        @media print {
            body {
                background: #fff;
            }
            .step-content {
                display: block !important;
            }
        }
    </style>"""

    def _get_javascript(self) -> str:
        """Returns JavaScript for interactive functionality."""
        return """
        // Toggle algorithm steps
        document.querySelectorAll('.step-header').forEach(header => {
            header.addEventListener('click', () => {
                const content = header.nextElementSibling;
                const toggle = header.querySelector('.step-toggle');

                if (content.classList.contains('active')) {
                    content.classList.remove('active');
                    toggle.textContent = '+';
                } else {
                    content.classList.add('active');
                    toggle.textContent = '-';
                }
            });
        });

        // Render video results
        function renderVideos() {
            const container = document.getElementById('videos-container');

            resultsData.forEach((video, index) => {
                const card = document.createElement('div');
                card.className = 'video-card';

                card.innerHTML = `
                    <div class="video-header">
                        <div>VIDEO ${index + 1}: ${video.video_id}</div>
                        <div class="video-title">${escapeHtml(video.title)}</div>
                        <div class="video-meta">
                            ${video.comment_count} comments |
                            <a href="${video.url}" target="_blank" style="color: #ffeb3b;">Watch on YouTube</a>
                        </div>
                    </div>
                    <div class="video-body">
                        ${renderSentiment(video.sentiment)}
                        ${renderTopics(video.topics)}
                        ${renderQuestions(video.questions)}
                    </div>
                `;

                container.appendChild(card);
            });
        }

        function renderSentiment(sentiment) {
            const score = (sentiment.overall_score * 100).toFixed(1);
            const dist = sentiment.distribution;

            return `
                <div class="stat-box">
                    <div class="stat-title">SENTIMENT ANALYSIS</div>
                    <div class="stat-value">${score}/100</div>
                    <div class="distribution">
                        <div class="dist-item">
                            <div class="dist-label">POSITIVE</div>
                            <div class="dist-value">${dist.positive || 0}</div>
                        </div>
                        <div class="dist-item">
                            <div class="dist-label">NEUTRAL</div>
                            <div class="dist-value">${dist.neutral || 0}</div>
                        </div>
                        <div class="dist-item">
                            <div class="dist-label">NEGATIVE</div>
                            <div class="dist-value">${dist.negative || 0}</div>
                        </div>
                    </div>
                </div>
            `;
        }

        function renderTopics(topics) {
            if (!topics || topics.length === 0) {
                return '<div class="stat-box"><div class="stat-title">NO TOPICS FOUND</div></div>';
            }

            return `
                <h3>TOP ${topics.length} TOPICS</h3>
                ${topics.map(topic => `
                    <div class="topic-item">
                        <div class="topic-header">${escapeHtml(topic.name)} (${topic.count} comments)</div>
                        <div class="keywords">
                            ${topic.keywords.map(kw => `<span class="keyword">${escapeHtml(kw)}</span>`).join('')}
                        </div>
                        ${topic.representative_comments && topic.representative_comments.length > 0 ? `
                            <div style="margin-top: 10px;">
                                ${topic.representative_comments.map(comment => `
                                    <div class="comment-sample">
                                        ${escapeHtml(comment.content)}
                                        <div class="relevance">Relevance: ${(comment.relevance * 100).toFixed(0)}%</div>
                                    </div>
                                `).join('')}
                            </div>
                        ` : ''}
                    </div>
                `).join('')}
            `;
        }

        function renderQuestions(questions) {
            if (!questions || questions.length === 0) {
                return '<div class="stat-box"><div class="stat-title">NO QUESTIONS FOUND</div></div>';
            }

            return `
                <h3>TOP ${questions.length} QUESTIONS</h3>
                ${questions.map((q, i) => `
                    <div class="question-item">
                        <div class="question-header">${i + 1}. ${escapeHtml(q.text)}</div>
                        <div style="margin-top: 5px; font-size: 13px;">
                            Category: ${escapeHtml(q.category)} |
                            Relevance: ${(q.relevance * 100).toFixed(0)}% |
                            Engagement: ${q.engagement.toFixed(1)} |
                            ${q.is_answered ? '<span style="color: #000; background: #ffeb3b; padding: 2px 5px; border: 1px solid #000;">ANSWERED</span>' : '<span style="color: #000;">Unanswered</span>'}
                        </div>
                    </div>
                `).join('')}
            `;
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Initialize
        renderVideos();
        """

    def _generate_algorithm_steps(self) -> str:
        """Generate HTML for the 7 algorithm steps."""
        steps = [
            {
                'number': 1,
                'title': 'LOAD & VALIDATE DATA',
                'description': 'Load the CSV dataset and validate its structure.',
                'details': [
                    'Read CSV file containing YouTube posts and comments',
                    'Validate required columns: id, url, content, author_id, parent_id',
                    'Check for data integrity issues',
                    'Filter out invalid or malformed entries',
                    'Statistics: Total rows, valid comments, orphaned comments'
                ]
            },
            {
                'number': 2,
                'title': 'DISCOVER VIDEOS',
                'description': 'Identify which posts are videos vs comments.',
                'details': [
                    'Parse URLs to extract video IDs',
                    'Group comments by parent video using parent_id relationships',
                    'Handle orphaned comments (comments without identifiable videos)',
                    'Build Video objects with associated Comment objects',
                    'Optional: Step 2.5 attempts to reassign orphaned comments using semantic similarity'
                ]
            },
            {
                'number': 3,
                'title': 'GENERATE EMBEDDINGS',
                'description': 'Convert comments to vector representations using OpenAI embeddings.',
                'details': [
                    'Use OpenAI text-embedding-3-small model',
                    'Generate 1536-dimensional embedding vectors for each comment',
                    'Cache embeddings to avoid duplicate API calls',
                    'Enable semantic search and similarity comparisons',
                    'Required for search execution and orphaned comment reassignment'
                ]
            },
            {
                'number': 4,
                'title': 'GENERATE SEARCH SPECIFICATIONS',
                'description': 'Create search queries to find relevant comments.',
                'details': [
                    '<strong>Static Specs:</strong> Universal searches applied to all videos (e.g., "Find critical feedback", "Find feature requests")',
                    '<strong>Dynamic Specs:</strong> Video-specific searches generated by analyzing comment samples with LLM',
                    'LLM (GPT-4o) analyzes 10 sample comments per video to understand context',
                    'Generates 5 custom search specifications per video',
                    'Each spec includes: query, context, filters, extract_fields, rationale'
                ]
            },
            {
                'number': 5,
                'title': 'EXECUTE SEARCHES',
                'description': 'Run semantic search + LLM ranking to find matching comments.',
                'details': [
                    '<strong>Phase 1:</strong> Semantic Search - Find top 30 candidates using cosine similarity on embeddings',
                    '<strong>Phase 2:</strong> LLM Ranking - Use GPT-4o-mini to re-rank candidates by true relevance',
                    'Apply filters specified in CommentSearchSpec',
                    'Extract insights from matched comments',
                    'Store SearchResult objects with matched comments and relevance scores'
                ]
            },
            {
                'number': 6,
                'title': 'PERFORM ANALYTICS',
                'description': 'Analyze sentiment, extract topics, and identify questions.',
                'details': [
                    '<strong>Sentiment Analysis:</strong> Batch comments and score each 0-1 (negative to positive) using GPT-4o-mini',
                    '<strong>Topic Extraction:</strong> Cluster comments using K-means on embeddings, generate topic labels with LLM',
                    '<strong>Question Finding:</strong> Extract questions from comments, validate and categorize them',
                    'Calculate aggregate statistics (overall sentiment, distribution)',
                    'Generate AnalyticsResult objects for each video'
                ]
            },
            {
                'number': 7,
                'title': 'GENERATE OUTPUT',
                'description': 'Save results and generate visualization.',
                'details': [
                    'Create timestamped output directory',
                    'Save results.json with complete analysis data',
                    'Save metadata.json with run statistics',
                    'Save session.pkl for future reuse/categorization',
                    'Generate HTML visualization (this page)',
                    'Display summary statistics and next steps'
                ]
            }
        ]

        html = '<div class="steps-container">'
        for step in steps:
            html += f'''
            <div class="step-box">
                <div class="step-header">
                    <span>STEP {step['number']}: {step['title']}</span>
                    <span class="step-toggle">+</span>
                </div>
                <div class="step-content">
                    <p><strong>{step['description']}</strong></p>
                    <ul>
                        {''.join(f'<li>{detail}</li>' for detail in step['details'])}
                    </ul>
                </div>
            </div>
            '''
        html += '</div>'
        return html

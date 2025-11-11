// Comment Probe AI - Interactive Web UI
let currentRun = null;
let currentResults = null;
let selectedVideoFilters = [];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadRuns();
    setupEventListeners();
    renderAlgorithmSteps();
});

function setupEventListeners() {
    document.getElementById('run-select').addEventListener('change', (e) => {
        const hasSelection = e.target.value !== '';
        document.getElementById('load-btn').disabled = !hasSelection;
    });

    document.getElementById('load-btn').addEventListener('click', loadAnalysis);
    document.getElementById('search-btn').addEventListener('click', performSearch);
    document.getElementById('clear-search-btn').addEventListener('click', clearSearch);

    document.getElementById('search-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            performSearch();
        }
    });
}

async function loadRuns() {
    try {
        const response = await fetch('/api/runs');
        const data = await response.json();

        const select = document.getElementById('run-select');
        select.innerHTML = '<option value="">-- Select a run --</option>';

        if (data.runs && data.runs.length > 0) {
            data.runs.forEach(run => {
                const option = document.createElement('option');
                option.value = run.run_id;
                option.textContent = run.run_id + ' (' + run.videos + ' videos, ' + run.comments + ' comments)';
                select.appendChild(option);
            });
        } else {
            select.innerHTML = '<option value="">No runs available</option>';
        }
    } catch (error) {
        console.error('Failed to load runs:', error);
        showError('Failed to load available runs');
    }
}

async function loadAnalysis() {
    const runId = document.getElementById('run-select').value;
    if (!runId) return;

    currentRun = runId;
    selectedVideoFilters = [];

    showLoading(true);
    hideError();
    clearSearch();

    try {
        const response = await fetch('/api/results/' + runId);
        if (!response.ok) throw new Error('Failed to load results');

        currentResults = await response.json();

        renderResults(currentResults);
        setupVideoFilters(currentResults);

        // Enable search
        document.getElementById('search-input').disabled = false;
        document.getElementById('search-btn').disabled = false;
        document.getElementById('clear-search-btn').disabled = false;

        showLoading(false);
    } catch (error) {
        console.error('Failed to load analysis:', error);
        showError('Failed to load analysis results');
        showLoading(false);
    }
}

function setupVideoFilters(results) {
    const container = document.getElementById('video-filters');
    container.style.display = 'flex';

    // Clear existing filters (keep label)
    const label = container.querySelector('label');
    container.innerHTML = '';
    container.appendChild(label);

    // Add "All Videos" chip
    const allChip = document.createElement('div');
    allChip.className = 'video-filter-chip active';
    allChip.textContent = 'ALL VIDEOS';
    allChip.dataset.videoId = '';
    allChip.addEventListener('click', () => toggleVideoFilter(''));
    container.appendChild(allChip);

    // Add chip for each video
    results.videos.forEach((video, index) => {
        const chip = document.createElement('div');
        chip.className = 'video-filter-chip';
        chip.textContent = 'VIDEO ' + (index + 1) + ': ' + video.video_id;
        chip.dataset.videoId = video.video_id;
        chip.addEventListener('click', () => toggleVideoFilter(video.video_id));
        container.appendChild(chip);
    });
}

function toggleVideoFilter(videoId) {
    if (videoId === '') {
        // "All Videos" selected
        selectedVideoFilters = [];
        document.querySelectorAll('.video-filter-chip').forEach(chip => {
            chip.classList.toggle('active', chip.dataset.videoId === '');
        });
    } else {
        // Individual video selected
        const index = selectedVideoFilters.indexOf(videoId);
        if (index === -1) {
            selectedVideoFilters.push(videoId);
        } else {
            selectedVideoFilters.splice(index, 1);
        }

        // Update chip states
        document.querySelectorAll('.video-filter-chip').forEach(chip => {
            if (chip.dataset.videoId === '') {
                chip.classList.toggle('active', selectedVideoFilters.length === 0);
            } else {
                chip.classList.toggle('active', selectedVideoFilters.includes(chip.dataset.videoId));
            }
        });
    }

    // If search is active, re-run search with new filters
    const searchInput = document.getElementById('search-input');
    if (searchInput.value.trim()) {
        performSearch();
    }
}

async function performSearch() {
    const query = document.getElementById('search-input').value.trim();
    if (!query || !currentRun) return;

    showLoading(true);
    hideError();

    try {
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                run_id: currentRun,
                query: query,
                video_ids: selectedVideoFilters.length > 0 ? selectedVideoFilters : undefined
            })
        });

        if (!response.ok) throw new Error('Search failed');

        const results = await response.json();
        renderSearchResults(results);

        showLoading(false);
    } catch (error) {
        console.error('Search failed:', error);
        showError('Search failed');
        showLoading(false);
    }
}

function clearSearch() {
    document.getElementById('search-input').value = '';
    document.getElementById('search-results').classList.remove('active');
    document.getElementById('results-section').style.display = 'block';
    document.getElementById('algorithm-section').style.display = 'block';
}

function renderSearchResults(results) {
    const container = document.getElementById('search-results-container');
    const section = document.getElementById('search-results');

    // Hide main results, show search results
    document.getElementById('results-section').style.display = 'none';
    document.getElementById('algorithm-section').style.display = 'none';
    section.classList.add('active');

    if (results.matches.length === 0) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">˜</div><div>NO MATCHES FOUND FOR "' + escapeHtml(results.query) + '"</div></div>';
        return;
    }

    let html = '<div style="margin-bottom: 20px; font-weight: bold;">FOUND ' + results.total_matches + ' MATCHES FOR "' + escapeHtml(results.query) + '"</div>';

    results.matches.forEach((match, index) => {
        html += '<div class="search-result-item">';
        html += '<div class="result-header">RESULT ' + (index + 1) + ' | VIDEO: ' + escapeHtml(match.video_id) + ' | TYPE: ' + escapeHtml(match.match_type).toUpperCase() + '</div>';
        if (match.topic_name) html += '<div style="margin: 5px 0;"><strong>Topic:</strong> ' + escapeHtml(match.topic_name) + '</div>';
        if (match.category) html += '<div style="margin: 5px 0;"><strong>Category:</strong> ' + escapeHtml(match.category) + '</div>';
        html += '<div class="comment-sample">' + escapeHtml(match.comment) + '<div class="relevance">Relevance: ' + (match.relevance * 100).toFixed(0) + '%</div></div>';
        html += '<div style="margin-top: 10px; font-size: 12px;"><a href="' + match.video_url + '" target="_blank" style="color: #000; font-weight: bold;">WATCH ON YOUTUBE ’</a></div>';
        html += '</div>';
    });

    container.innerHTML = html;
}

function renderResults(results) {
    const container = document.getElementById('videos-container');

    if (!results.videos || results.videos.length === 0) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">˜</div><div>NO VIDEOS FOUND</div></div>';
        return;
    }

    let html = '';
    results.videos.forEach((video, index) => {
        const analytics = video.analytics || {};
        const sentiment = analytics.sentiment || {};

        html += '<div class="video-card">';
        html += '<div class="video-header">';
        html += '<div>VIDEO ' + (index + 1) + ': ' + escapeHtml(video.video_id) + '</div>';
        html += '<div class="video-title">' + escapeHtml(video.title || '') + '</div>';
        html += '<div class="video-meta">' + video.comment_count + ' comments | <a href="' + video.url + '" target="_blank" style="color: #ffeb3b;">WATCH ON YOUTUBE</a></div>';
        html += '</div>';
        html += '<div class="video-body">';
        html += renderSentiment(sentiment);
        html += renderTopics(analytics.topics || []);
        html += renderQuestions(analytics.questions || []);
        html += '</div>';
        html += '</div>';
    });

    container.innerHTML = html;
}

function renderSentiment(sentiment) {
    const score = ((sentiment.overall_score || 0.5) * 100).toFixed(1);
    const dist = sentiment.distribution || {};

    let html = '<div class="stat-box">';
    html += '<div class="stat-title">SENTIMENT ANALYSIS</div>';
    html += '<div class="stat-value">' + score + '/100</div>';
    html += '<div class="distribution">';
    html += '<div class="dist-item"><div class="dist-label">POSITIVE</div><div class="dist-value">' + (dist.positive || 0) + '</div></div>';
    html += '<div class="dist-item"><div class="dist-label">NEUTRAL</div><div class="dist-value">' + (dist.neutral || 0) + '</div></div>';
    html += '<div class="dist-item"><div class="dist-label">NEGATIVE</div><div class="dist-value">' + (dist.negative || 0) + '</div></div>';
    html += '</div></div>';
    return html;
}

function renderTopics(topics) {
    if (!topics || topics.length === 0) {
        return '<div class="stat-box"><div class="stat-title">NO TOPICS FOUND</div></div>';
    }

    let html = '<h3>TOP ' + topics.length + ' TOPICS</h3>';
    topics.forEach(topic => {
        html += '<div class="topic-item">';
        html += '<div class="topic-header">' + escapeHtml(topic.topic_name) + ' (' + topic.comment_count + ' comments)</div>';
        html += '<div class="keywords">';
        (topic.keywords || []).forEach(kw => {
            html += '<span class="keyword">' + escapeHtml(kw) + '</span>';
        });
        html += '</div>';
        if (topic.representative_comments && topic.representative_comments.length > 0) {
            html += '<div style="margin-top: 10px;">';
            topic.representative_comments.forEach(comment => {
                html += '<div class="comment-sample">' + escapeHtml(comment.content);
                html += '<div class="relevance">Relevance: ' + (comment.relevance_score * 100).toFixed(0) + '%</div></div>';
            });
            html += '</div>';
        }
        html += '</div>';
    });
    return html;
}

function renderQuestions(questions) {
    if (!questions || questions.length === 0) {
        return '<div class="stat-box"><div class="stat-title">NO QUESTIONS FOUND</div></div>';
    }

    let html = '<h3>TOP ' + questions.length + ' QUESTIONS</h3>';
    questions.forEach((q, i) => {
        html += '<div class="question-item">';
        html += '<div class="question-header">' + (i + 1) + '. ' + escapeHtml(q.question_text) + '</div>';
        html += '<div style="margin-top: 5px; font-size: 13px;">';
        html += 'Category: ' + escapeHtml(q.category) + ' | ';
        html += 'Relevance: ' + (q.relevance_score * 100).toFixed(0) + '% | ';
        html += 'Engagement: ' + q.engagement_score.toFixed(1) + ' | ';
        html += q.is_answered ? '<span style="color: #000; background: #ffeb3b; padding: 2px 5px; border: 1px solid #000;">ANSWERED</span>' : '<span style="color: #000;">Unanswered</span>';
        html += '</div></div>';
    });
    return html;
}

function renderAlgorithmSteps() {
    const steps = [
        {n:1,t:'LOAD & VALIDATE DATA',d:'Load the CSV dataset and validate its structure.',i:['Read CSV file containing YouTube posts and comments','Validate required columns: id, url, content, author_id, parent_id','Check for data integrity issues','Filter out invalid or malformed entries','Statistics: Total rows, valid comments, orphaned comments']},
        {n:2,t:'DISCOVER VIDEOS',d:'Identify which posts are videos vs comments.',i:['Parse URLs to extract video IDs','Group comments by parent video using parent_id relationships','Handle orphaned comments (comments without identifiable videos)','Build Video objects with associated Comment objects','Optional: Step 2.5 attempts to reassign orphaned comments using semantic similarity']},
        {n:3,t:'GENERATE EMBEDDINGS',d:'Convert comments to vector representations using OpenAI embeddings.',i:['Use OpenAI text-embedding-3-small model','Generate 1536-dimensional embedding vectors for each comment','Cache embeddings to avoid duplicate API calls','Enable semantic search and similarity comparisons','Required for search execution and orphaned comment reassignment']},
        {n:4,t:'GENERATE SEARCH SPECIFICATIONS',d:'Create search queries to find relevant comments.',i:['<strong>Static Specs:</strong> Universal searches applied to all videos','<strong>Dynamic Specs:</strong> Video-specific searches generated by analyzing comment samples with LLM','LLM (GPT-4o) analyzes 10 sample comments per video to understand context','Generates 5 custom search specifications per video','Each spec includes: query, context, filters, extract_fields, rationale']},
        {n:5,t:'EXECUTE SEARCHES',d:'Run semantic search + LLM ranking to find matching comments.',i:['<strong>Phase 1:</strong> Semantic Search - Find top 30 candidates using cosine similarity on embeddings','<strong>Phase 2:</strong> LLM Ranking - Use GPT-4o-mini to re-rank candidates by true relevance','Apply filters specified in CommentSearchSpec','Extract insights from matched comments','Store SearchResult objects with matched comments and relevance scores']},
        {n:6,t:'PERFORM ANALYTICS',d:'Analyze sentiment, extract topics, and identify questions.',i:['<strong>Sentiment Analysis:</strong> Batch comments and score each 0-1 (negative to positive) using GPT-4o-mini','<strong>Topic Extraction:</strong> Cluster comments using K-means on embeddings, generate topic labels with LLM','<strong>Question Finding:</strong> Extract questions from comments, validate and categorize them','Calculate aggregate statistics (overall sentiment, distribution)','Generate AnalyticsResult objects for each video']},
        {n:7,t:'GENERATE OUTPUT',d:'Save results and generate visualization.',i:['Create timestamped output directory','Save results.json with complete analysis data','Save metadata.json with run statistics','Save session.pkl for future reuse/categorization','Generate HTML visualization (this page)','Display summary statistics and next steps']}
    ];

    const container = document.getElementById('algorithm-steps');
    let html = '';

    steps.forEach(step => {
        html += '<div class="step-box">';
        html += '<div class="step-header" onclick="toggleStep(this)"><span>STEP ' + step.n + ': ' + step.t + '</span><span class="step-toggle">+</span></div>';
        html += '<div class="step-content"><p><strong>' + step.d + '</strong></p><ul>';
        step.i.forEach(detail => {
            html += '<li>' + detail + '</li>';
        });
        html += '</ul></div></div>';
    });

    container.innerHTML = html;
}

function toggleStep(header) {
    const content = header.nextElementSibling;
    const toggle = header.querySelector('.step-toggle');

    if (content.classList.contains('active')) {
        content.classList.remove('active');
        toggle.textContent = '+';
    } else {
        content.classList.add('active');
        toggle.textContent = '-';
    }
}

function showLoading(show) {
    document.getElementById('loading').style.display = show ? 'block' : 'none';
}

function showError(message) {
    const errorDiv = document.getElementById('error');
    errorDiv.textContent = 'ERROR: ' + message;
    errorDiv.style.display = 'block';
}

function hideError() {
    document.getElementById('error').style.display = 'none';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

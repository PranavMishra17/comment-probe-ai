// Comment Probe AI - Interactive Web UI
let currentRun = null;
let currentResults = null;
let selectedVideoFilters = [];
let videoTitleCache = {}; // Cache for YouTube video titles

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadRuns();
    setupEventListeners();
    renderAlgorithmSteps();
    setupTabs();
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

function setupTabs() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    tabButtons.forEach(button => {
        button.addEventListener('click', (e) => {
            // Don't trigger if clicking the close button
            if (e.target.classList.contains('tab-close')) {
                return;
            }
            const tabName = button.getAttribute('data-tab');
            switchTab(tabName);
        });
    });
}

function switchTab(tabName) {
    // Hide home screen
    document.getElementById('home-screen').style.display = 'none';

    // Hide all tab contents
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.style.display = 'none';
    });

    // Remove active class from all buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    // Show selected tab
    const selectedTab = document.getElementById('tab-' + tabName);
    if (selectedTab) {
        selectedTab.style.display = 'block';
    }

    // Add active class to clicked button
    const selectedButton = document.querySelector(`[data-tab="${tabName}"]`);
    if (selectedButton) {
        selectedButton.classList.add('active');
    }
}

function closeTab(event, tabName) {
    event.stopPropagation(); // Prevent tab click event

    // Hide the tab content
    const tabContent = document.getElementById('tab-' + tabName);
    if (tabContent) {
        tabContent.style.display = 'none';
    }

    // Remove active class from button
    const button = document.querySelector(`[data-tab="${tabName}"]`);
    if (button) {
        button.classList.remove('active');
    }

    // Show home screen if no tabs are active
    const anyActive = document.querySelector('.tab-btn.active');
    if (!anyActive) {
        document.getElementById('home-screen').style.display = 'block';
    }
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

    showLoading(true, 'LOADING ANALYSIS RESULTS...');
    hideError();
    clearSearch();

    try {
        const response = await fetch('/api/results/' + runId);
        if (!response.ok) throw new Error('Failed to load results');

        currentResults = await response.json();

        await renderResults(currentResults);
        await setupVideoFilters(currentResults);

        // Enable search
        document.getElementById('search-input').disabled = false;
        document.getElementById('search-btn').disabled = false;
        document.getElementById('clear-search-btn').disabled = false;

        // Hide search warning
        const searchWarning = document.getElementById('search-warning');
        if (searchWarning) {
            searchWarning.style.display = 'none';
        }

        // Switch to results tab
        switchTab('results');

        showLoading(false);
    } catch (error) {
        console.error('Failed to load analysis:', error);
        showError('Failed to load analysis results');
        showLoading(false);
    }
}

async function setupVideoFilters(results) {
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

    // Fetch titles for all videos
    const videoTitles = await fetchYouTubeTitles(results.videos);

    // Add chip for each video
    results.videos.forEach((video, index) => {
        const chip = document.createElement('div');
        chip.className = 'video-filter-chip';
        const videoTitle = videoTitles[video.video_id] || video.video_id;
        // Truncate title if too long
        const displayTitle = videoTitle.length > 40 ? videoTitle.substring(0, 37) + '...' : videoTitle;
        chip.textContent = 'VIDEO ' + (index + 1) + ': ' + displayTitle;
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

    showLoading(true, 'SEARCHING COMMENTS...');
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
        await renderSearchResults(results);

        showLoading(false);
    } catch (error) {
        console.error('Search failed:', error);
        showError('Search failed');
        showLoading(false);
    }
}

function clearSearch() {
    document.getElementById('search-input').value = '';
    document.getElementById('search-results-container').innerHTML = '';
}

async function renderSearchResults(results) {
    const container = document.getElementById('search-results-container');

    if (results.matches.length === 0) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">SEARCH</div><div>NO MATCHES FOUND FOR "' + escapeHtml(results.query) + '"</div></div>';
        return;
    }

    // Get unique video IDs and fetch their titles
    const uniqueVideoIds = [...new Set(results.matches.map(m => m.video_id))];
    const videoTitlesMap = {};
    const idsToFetch = [];

    // Check cache first
    uniqueVideoIds.forEach(videoId => {
        if (videoTitleCache[videoId]) {
            videoTitlesMap[videoId] = videoTitleCache[videoId];
        } else {
            idsToFetch.push(videoId);
        }
    });

    // Fetch uncached titles
    if (idsToFetch.length > 0) {
        await Promise.all(idsToFetch.map(async (videoId) => {
            try {
                const response = await fetch(`https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=${videoId}&format=json`);
                if (response.ok) {
                    const data = await response.json();
                    videoTitlesMap[videoId] = data.title;
                    videoTitleCache[videoId] = data.title;
                } else {
                    videoTitlesMap[videoId] = videoId;
                    videoTitleCache[videoId] = videoId;
                }
            } catch (error) {
                console.error('Failed to fetch title for', videoId, error);
                videoTitlesMap[videoId] = videoId;
                videoTitleCache[videoId] = videoId;
            }
        }));
    }

    let html = '<div style="margin-bottom: 20px; font-weight: 700;">FOUND ' + results.total_matches + ' MATCHES FOR "' + escapeHtml(results.query) + '"</div>';

    results.matches.forEach((match, index) => {
        const videoTitle = videoTitlesMap[match.video_id] || match.video_id;
        const relevancePercent = (match.relevance * 100).toFixed(0);
        const relevanceScore = match.relevance;

        // Determine relevance badge color
        let badgeColor = '#FF00FF'; // Default magenta
        let badgeText = 'MEDIUM';
        if (relevanceScore >= 0.8) {
            badgeColor = '#00FF00'; // Bright green
            badgeText = 'HIGH';
        } else if (relevanceScore < 0.5) {
            badgeColor = '#FF6B6B'; // Coral red
            badgeText = 'LOW';
        }

        html += '<div class="search-result-item">';
        html += '<div class="result-header" style="display: flex; justify-content: space-between; align-items: center; padding: 12px 15px;">';
        html += '<div style="display: flex; align-items: center; gap: 15px;">';
        html += '<div class="result-number" style="background: #000; color: #FFF59D; width: 35px; height: 35px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 16px;">' + (index + 1) + '</div>';
        html += '<span style="font-size: 14px;">TYPE: ' + escapeHtml(match.match_type).toUpperCase() + '</span>';
        html += '</div>';
        html += '<div style="display: flex; align-items: center; gap: 10px;">';
        html += '<span class="relevance-badge" style="background: ' + badgeColor + '; color: #000; padding: 6px 14px; border: 2px solid #000; font-size: 12px; font-weight: 700; box-shadow: 3px 3px 0 #000;" title="LLM Relevance Score">' + badgeText + ' • ' + relevancePercent + '%</span>';
        html += '</div>';
        html += '</div>';

        html += '<div style="padding: 0 15px 15px 15px;">';
        html += '<div style="margin: 10px 0; font-size: 13px; color: #666;"><strong style="color: #000;">Video:</strong> ' + escapeHtml(videoTitle) + '</div>';
        if (match.topic_name) html += '<div style="margin: 5px 0; font-size: 12px;"><span style="background: #00FFFF; padding: 3px 8px; border: 2px solid #000; font-weight: 700;">TOPIC: ' + escapeHtml(match.topic_name) + '</span></div>';
        if (match.category) html += '<div style="margin: 5px 0; font-size: 12px;"><span style="background: #FFF59D; padding: 3px 8px; border: 2px solid #000; font-weight: 700;">CATEGORY: ' + escapeHtml(match.category) + '</span></div>';
        html += '<div class="comment-sample" style="margin-top: 10px;">' + escapeHtml(match.comment) + '</div>';
        html += '<div style="margin-top: 10px; font-size: 12px;"><a href="' + match.video_url + '" target="_blank" style="color: #FF00FF; font-weight: 700; text-decoration: none; border-bottom: 2px solid #FF00FF;">→ WATCH ON YOUTUBE</a></div>';
        html += '</div>';
        html += '</div>';
    });

    container.innerHTML = html;
}

async function renderResults(results) {
    const container = document.getElementById('videos-container');

    if (!results.videos || results.videos.length === 0) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">NO DATA</div><div>NO VIDEOS FOUND</div></div>';
        return;
    }

    let html = '';

    // Fetch YouTube titles for all videos
    const videoTitles = await fetchYouTubeTitles(results.videos);

    results.videos.forEach((video, index) => {
        const analytics = video.analytics || {};
        const sentiment = analytics.sentiment || {};
        const videoId = 'video-' + index;
        const youtubeTitle = videoTitles[video.video_id] || 'YouTube Video';

        html += '<div class="video-card">';
        html += '<div class="video-header" onclick="toggleVideo(\'' + videoId + '\')" style="cursor: pointer;">';
        html += '<div style="display: flex; justify-content: space-between; align-items: center;">';
        html += '<div>';
        html += '<div class="video-number">VIDEO ' + (index + 1) + '</div>';
        html += '<div class="video-title">' + escapeHtml(youtubeTitle) + '</div>';
        html += '<div class="video-meta">' + video.comment_count + ' comments | <a href="' + video.url + '" target="_blank" onclick="event.stopPropagation();">WATCH ON YOUTUBE</a></div>';
        html += '</div>';
        html += '<div class="step-toggle" id="' + videoId + '-toggle">+</div>';
        html += '</div>';
        html += '</div>';
        html += '<div class="video-body" id="' + videoId + '" style="display: none;">';

        // Child tabs for video sections
        html += '<div class="video-tabs">';
        html += '<button class="video-tab-btn active" onclick="switchVideoTab(\'' + videoId + '\', \'sentiment\')">SENTIMENT</button>';
        html += '<button class="video-tab-btn" onclick="switchVideoTab(\'' + videoId + '\', \'topics\')">TOP 5 TOPICS</button>';
        html += '<button class="video-tab-btn" onclick="switchVideoTab(\'' + videoId + '\', \'questions\')">TOP 5 QUESTIONS</button>';
        html += '</div>';

        // Tab contents
        html += '<div class="video-tab-content active" id="' + videoId + '-sentiment">';
        html += renderSentiment(sentiment, videoId);
        html += '</div>';

        html += '<div class="video-tab-content" id="' + videoId + '-topics">';
        html += renderTopics(analytics.topics || [], videoId);
        html += '</div>';

        html += '<div class="video-tab-content" id="' + videoId + '-questions">';
        html += renderQuestions(analytics.questions || [], analytics.topics || []);
        html += '</div>';

        html += '</div>';
        html += '</div>';
    });

    container.innerHTML = html;

    // Initialize pie charts after HTML is rendered
    setTimeout(() => {
        results.videos.forEach((video, index) => {
            const videoId = 'video-' + index;
            const analytics = video.analytics || {};
            if (analytics.topics && analytics.topics.length > 0) {
                createTopicsPieChart(videoId, analytics.topics);
            }
        });
    }, 100);
}

async function fetchYouTubeTitles(videos) {
    const titles = {};
    const videosToFetch = [];

    // Check cache first
    videos.forEach(video => {
        const videoId = video.video_id;
        if (videoTitleCache[videoId]) {
            titles[videoId] = videoTitleCache[videoId];
        } else {
            videosToFetch.push(video);
        }
    });

    // Fetch titles for uncached videos in parallel
    if (videosToFetch.length > 0) {
        await Promise.all(videosToFetch.map(async (video) => {
            try {
                const videoId = video.video_id;
                const response = await fetch(`https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=${videoId}&format=json`);

                if (response.ok) {
                    const data = await response.json();
                    titles[videoId] = data.title;
                    videoTitleCache[videoId] = data.title; // Cache it
                } else {
                    titles[videoId] = videoId; // Fallback to video ID
                    videoTitleCache[videoId] = videoId;
                }
            } catch (error) {
                console.error('Failed to fetch title for', video.video_id, error);
                titles[video.video_id] = video.video_id; // Fallback to video ID
                videoTitleCache[video.video_id] = video.video_id;
            }
        }));
    }

    return titles;
}

function renderSentiment(sentiment, videoId) {
    const score = ((sentiment.overall_score || 0.5) * 100).toFixed(0);
    const scoreNum = parseInt(score);
    const dist = sentiment.distribution || {};

    const positive = dist.positive || 0;
    const neutral = dist.neutral || 0;
    const negative = dist.negative || 0;
    const total = positive + neutral + negative || 1;

    // Calculate color for sentiment score (light red to light green spectrum)
    const getScoreColor = (score) => {
        const percent = score / 100;
        if (percent <= 0.5) {
            // Red to Yellow (0-50)
            const r = 255;
            const g = Math.round(255 * (percent * 2));
            const b = 100;
            return `rgb(${r}, ${g}, ${b})`;
        } else {
            // Yellow to Green (50-100)
            const r = Math.round(255 * (2 - percent * 2));
            const g = 255;
            const b = 100;
            return `rgb(${r}, ${g}, ${b})`;
        }
    };

    let html = '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 30px; padding: 20px;">';

    // Left: Sentiment score spectrum box
    html += '<div>';
    html += '<h3 style="margin-bottom: 20px;">OVERALL SENTIMENT</h3>';
    html += '<div style="width: 250px; margin: 0 auto;">';

    // Color spectrum bar
    html += '<div style="height: 40px; background: linear-gradient(to right, #FF6464 0%, #FFFF64 50%, #90EE90 100%); border: 3px solid #000; position: relative;">';
    // Score marker
    const markerPosition = scoreNum;
    html += '<div style="position: absolute; left: ' + markerPosition + '%; top: -5px; transform: translateX(-50%); width: 4px; height: 50px; background: #000; border: 2px solid #fff;"></div>';
    html += '</div>';

    // Score display box
    const scoreColor = getScoreColor(scoreNum);
    html += '<div style="margin-top: 20px; padding: 30px; background: ' + scoreColor + '; border: 4px solid #000; text-align: center; box-shadow: 5px 5px 0 #000;">';
    html += '<div style="font-size: 48px; font-weight: 700; color: #000;">' + score + '</div>';
    html += '<div style="font-size: 20px; font-weight: 700; color: #000; margin-top: 5px;">/100</div>';
    html += '</div>';

    html += '</div>';
    html += '</div>';

    // Right: Distribution buckets (water fill style)
    html += '<div>';
    html += '<h3 style="margin-bottom: 20px;">COMMENT DISTRIBUTION</h3>';
    html += '<div style="display: flex; gap: 20px; align-items: flex-start;">';

    const bucketHeight = 193; // Match left side height (40 + 20 + 133)

    // Positive bucket
    const posPercent = ((positive / total) * 100).toFixed(0);
    const posFillHeight = Math.max((positive / total) * bucketHeight, 10); // Min 10px visibility
    html += '<div style="flex: 1; display: flex; flex-direction: column; align-items: center;">';
    html += '<div style="font-weight: 700; margin-bottom: 10px; color: #000;">POSITIVE</div>';
    html += '<div style="position: relative; width: 100%; height: ' + bucketHeight + 'px; border: 4px solid #000; background: #f5f5f5; box-shadow: 5px 5px 0 #000;">';
    html += '<div style="position: absolute; bottom: 0; left: 0; right: 0; height: ' + posFillHeight + 'px; background: #90EE90; transition: height 0.5s;">';
    html += '<div style="position: absolute; top: 5px; left: 0; right: 0; text-align: center; font-weight: 700; font-size: 14px; color: #000;">' + posPercent + '%</div>';
    html += '</div>';
    html += '</div>';
    html += '<div style="margin-top: 8px; font-weight: 700; font-size: 16px; color: #000;">' + positive + '</div>';
    html += '</div>';

    // Neutral bucket
    const neuPercent = ((neutral / total) * 100).toFixed(0);
    const neuFillHeight = Math.max((neutral / total) * bucketHeight, 10); // Min 10px visibility
    html += '<div style="flex: 1; display: flex; flex-direction: column; align-items: center;">';
    html += '<div style="font-weight: 700; margin-bottom: 10px; color: #000;">NEUTRAL</div>';
    html += '<div style="position: relative; width: 100%; height: ' + bucketHeight + 'px; border: 4px solid #000; background: #f5f5f5; box-shadow: 5px 5px 0 #000;">';
    html += '<div style="position: absolute; bottom: 0; left: 0; right: 0; height: ' + neuFillHeight + 'px; background: #FFFF64; transition: height 0.5s;">';
    html += '<div style="position: absolute; top: 5px; left: 0; right: 0; text-align: center; font-weight: 700; font-size: 14px; color: #000;">' + neuPercent + '%</div>';
    html += '</div>';
    html += '</div>';
    html += '<div style="margin-top: 8px; font-weight: 700; font-size: 16px; color: #000;">' + neutral + '</div>';
    html += '</div>';

    // Negative bucket
    const negPercent = ((negative / total) * 100).toFixed(0);
    const negFillHeight = Math.max((negative / total) * bucketHeight, 10); // Min 10px visibility
    html += '<div style="flex: 1; display: flex; flex-direction: column; align-items: center;">';
    html += '<div style="font-weight: 700; margin-bottom: 10px; color: #000;">NEGATIVE</div>';
    html += '<div style="position: relative; width: 100%; height: ' + bucketHeight + 'px; border: 4px solid #000; background: #f5f5f5; box-shadow: 5px 5px 0 #000;">';
    html += '<div style="position: absolute; bottom: 0; left: 0; right: 0; height: ' + negFillHeight + 'px; background: #FF6464; transition: height 0.5s;">';
    html += '<div style="position: absolute; top: 5px; left: 0; right: 0; text-align: center; font-weight: 700; font-size: 14px; color: #000;">' + negPercent + '%</div>';
    html += '</div>';
    html += '</div>';
    html += '<div style="margin-top: 8px; font-weight: 700; font-size: 16px; color: #000;">' + negative + '</div>';
    html += '</div>';

    html += '</div>';
    html += '</div>';
    html += '</div>';

    return html;
}

function renderTopics(topics, videoId) {
    if (!topics || topics.length === 0) {
        return '<div class="stat-box"><div class="stat-title">NO TOPICS FOUND</div></div>';
    }

    let html = '<div style="display: grid; grid-template-columns: 300px 1fr; gap: 30px; padding: 20px;">';

    // Left: Pie chart
    html += '<div>';
    html += '<h3 style="margin-bottom: 20px;">TOPIC DISTRIBUTION</h3>';
    html += '<canvas id="' + videoId + '-pie-chart" width="280" height="280"></canvas>';
    html += '</div>';

    // Right: Topic list
    html += '<div>';
    html += '<h3 style="margin-bottom: 20px;">TOP ' + topics.length + ' TOPICS</h3>';

    const colors = ['#FF00FF', '#00FF00', '#FFF59D', '#90EE90', '#00FFFF'];

    topics.forEach((topic, index) => {
        const color = colors[index % colors.length];
        html += '<div class="topic-item" style="margin-bottom: 15px; border-left: 5px solid ' + color + ';">';
        html += '<div style="display: flex; justify-content: space-between; align-items: center; padding: 10px;">';
        html += '<div style="flex: 1;">';
        html += '<div style="font-weight: 700; font-size: 16px; margin-bottom: 5px;">' + (index + 1) + '. ' + escapeHtml(topic.topic_name) + '</div>';
        html += '<div style="font-size: 12px; color: #666;">' + topic.comment_count + ' comments</div>';
        html += '</div>';
        html += '<div style="background: ' + color + '; color: #000; padding: 8px 15px; border: 2px solid #000; font-weight: 700; font-size: 18px;">' + Math.round((topic.comment_count / topics.reduce((sum, t) => sum + t.comment_count, 0)) * 100) + '%</div>';
        html += '</div>';

        html += '<div style="padding: 0 10px 10px 10px;">';
        html += '<div class="keywords">';
        (topic.keywords || []).forEach(kw => {
            html += '<span class="keyword" style="background: ' + color + '; opacity: 0.7;">' + escapeHtml(kw) + '</span>';
        });
        html += '</div>';

        if (topic.representative_comments && topic.representative_comments.length > 0) {
            html += '<div style="margin-top: 10px;">';
            // Show up to 2 comments
            const commentsToShow = topic.representative_comments.slice(0, 2);
            commentsToShow.forEach((comment, idx) => {
                html += '<div class="comment-sample" style="font-size: 13px; border-left: 3px solid ' + color + '; margin-bottom: 8px;">';
                html += '<div style="font-size: 11px; font-weight: 700; color: #666; margin-bottom: 5px;">EXAMPLE ' + (idx + 1) + ':</div>';
                html += escapeHtml(comment.content.substring(0, 120)) + (comment.content.length > 120 ? '...' : '');
                html += '<div class="relevance">Relevance: ' + (comment.relevance_score * 100).toFixed(0) + '%</div>';
                html += '</div>';
            });
            html += '</div>';
        }
        html += '</div>';
        html += '</div>';
    });

    html += '</div>';
    html += '</div>';

    return html;
}

function renderQuestions(questions, topics) {
    if (!questions || questions.length === 0) {
        return '<div class="stat-box"><div class="stat-title">NO QUESTIONS FOUND</div></div>';
    }

    // Helper function to match question to most relevant topic
    const matchQuestionToTopic = (questionText) => {
        if (!topics || topics.length === 0) return 'GENERAL';

        const questionWords = questionText.toLowerCase().split(/\s+/);
        let bestMatch = null;
        let maxOverlap = 0;

        topics.forEach((topic) => {
            const keywords = (topic.keywords || []).map(kw => kw.toLowerCase());
            const topicWords = topic.topic_name.toLowerCase().split(/\s+/);
            const allTopicWords = [...keywords, ...topicWords];

            let overlap = 0;
            questionWords.forEach(word => {
                if (word.length > 3 && allTopicWords.some(tw => tw.includes(word) || word.includes(tw))) {
                    overlap++;
                }
            });

            if (overlap > maxOverlap) {
                maxOverlap = overlap;
                bestMatch = topic.topic_name;
            }
        });

        return bestMatch || 'GENERAL';
    };

    // Color mapping for topics (same as topics section)
    const topicColors = ['#FF00FF', '#00FF00', '#FFF59D', '#90EE90', '#00FFFF'];
    const getTopicColor = (topicName) => {
        const index = topics.findIndex(t => t.topic_name === topicName);
        return index >= 0 ? topicColors[index % topicColors.length] : '#FFF59D';
    };

    let html = '<div style="padding: 20px;">';
    html += '<h3 style="margin-bottom: 20px;">TOP ' + questions.length + ' QUESTIONS</h3>';

    questions.forEach((q, i) => {
        const matchedTopic = matchQuestionToTopic(q.question_text);
        const categoryColor = getTopicColor(matchedTopic);
        const relevancePercent = (q.relevance_score * 100).toFixed(0);

        html += '<div class="question-item" style="margin-bottom: 15px; border-left: 5px solid ' + categoryColor + ';">';
        html += '<div style="padding: 15px;">';

        html += '<div style="display: flex; align-items: flex-start; gap: 15px; margin-bottom: 10px;">';
        html += '<div style="background: #000; color: #FFF59D; width: 35px; height: 35px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 16px; flex-shrink: 0;">' + (i + 1) + '</div>';
        html += '<div style="flex: 1;">';
        html += '<div style="font-weight: 700; font-size: 15px; line-height: 1.5; margin-bottom: 10px;">' + escapeHtml(q.question_text) + '</div>';

        html += '<div style="display: flex; gap: 10px; flex-wrap: wrap; align-items: center;">';
        html += '<span style="background: ' + categoryColor + '; color: #000; padding: 4px 10px; border: 2px solid #000; font-size: 11px; font-weight: 700;">TOPIC: ' + escapeHtml(matchedTopic.substring(0, 30)) + (matchedTopic.length > 30 ? '...' : '') + '</span>';

        // Relevance badge
        let relevanceBadgeColor = '#FFF59D';
        if (relevancePercent >= 80) relevanceBadgeColor = '#90EE90';
        else if (relevancePercent < 50) relevanceBadgeColor = '#FF6464';

        html += '<span style="background: ' + relevanceBadgeColor + '; color: #000; padding: 4px 10px; border: 2px solid #000; font-size: 11px; font-weight: 700;">RELEVANCE: ' + relevancePercent + '%</span>';
        html += '</div>';

        html += '</div>';
        html += '</div>';

        html += '</div>';
        html += '</div>';
    });

    html += '</div>';
    return html;
}

function renderAlgorithmSteps() {
    const container = document.getElementById('algorithm-steps');

    // System Architecture Diagram
    let html = '<div class="architecture-section">';
    html += '<h3>SYSTEM ARCHITECTURE</h3>';
    html += '<pre class="architecture-diagram">';
    html += '┌─────────────────────────────────────────────────────────────────┐\n';
    html += '│                     Flask Application Layer                      │\n';
    html += '│  ┌──────────┐  ┌─────────────┐  ┌────────────────────────────┐ │\n';
    html += '│  │  Routes  │──│ Orchestrator│──│     Output Manager         │ │\n';
    html += '│  │          │  │             │  │                            │ │\n';
    html += '│  │ /analyze │  │  Workflow   │  │  Results + Visualization   │ │\n';
    html += '│  │ /status  │  │  Control    │  │  Generation                │ │\n';
    html += '│  │ /results │  │             │  │                            │ │\n';
    html += '│  └──────────┘  └──────┬──────┘  └────────┬───────────────────┘ │\n';
    html += '└────────────────────────┼──────────────────┼─────────────────────┘\n';
    html += '                         │                  │\n';
    html += '         ┌───────────────┴──────────────────┴───────────────┐\n';
    html += '         │           Processing Layer                        │\n';
    html += '         │                                                    │\n';
    html += '┌────────▼───────────┐  ┌──────────────┐  ┌────────────────▼─────┐\n';
    html += '│  Data Pipeline     │  │  AI Engine   │  │  Analytics Engine    │\n';
    html += '│                    │  │              │  │                      │\n';
    html += '│ ┌────────────────┐ │  │ ┌──────────┐│  │ ┌──────────────────┐ │\n';
    html += '│ │ CSVLoader      │ │  │ │ OpenAI   ││  │ │ Sentiment        │ │\n';
    html += '│ │ DataValidator  │ │  │ │ Client   ││  │ │ Analyzer         │ │\n';
    html += '│ │ DataCleaner    │ │  │ │          ││  │ │                  │ │\n';
    html += '│ │ VideoDiscoverer│ │  │ │ Embedder ││  │ │ Topic            │ │\n';
    html += '│ └────────────────┘ │  │ │          ││  │ │ Extractor        │ │\n';
    html += '│                    │  │ │ Hypothesis│  │ │                  │ │\n';
    html += '│                    │  │ │ Generator││  │ │ Question         │ │\n';
    html += '│                    │  │ │          ││  │ │ Finder           │ │\n';
    html += '│                    │  │ │ Search   ││  │ └──────────────────┘ │\n';
    html += '│                    │  │ │ Engine   ││  │                      │\n';
    html += '│                    │  │ └──────────┘│  │                      │\n';
    html += '└────────────────────┘  └──────────────┘  └──────────────────────┘\n';
    html += '         │                      │                    │\n';
    html += '         └──────────────────────┴────────────────────┘\n';
    html += '                                │\n';
    html += '                    ┌───────────▼──────────────┐\n';
    html += '                    │  Infrastructure Layer    │\n';
    html += '                    │                          │\n';
    html += '                    │  ┌────────────────────┐  │\n';
    html += '                    │  │ CacheManager       │  │\n';
    html += '                    │  │ Logger             │  │\n';
    html += '                    │  │ RateLimiter        │  │\n';
    html += '                    │  │ ErrorHandler       │  │\n';
    html += '                    │  └────────────────────┘  │\n';
    html += '                    └──────────────────────────┘\n';
    html += '</pre>';
    html += '</div>';

    // Processing Pipeline
    html += '<div class="pipeline-section">';
    html += '<h3>7-STEP PROCESSING PIPELINE</h3>';
    html += '<pre class="pipeline-diagram">';
    html += '┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐\n';
    html += '│   STEP 1     │───▶│   STEP 2     │───▶│   STEP 3     │───▶│   STEP 4     │\n';
    html += '│ Load & Validate  │ Discover Videos│ Gen Embeddings │ Gen Search Specs│\n';
    html += '└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘\n';
    html += '                                                                     │\n';
    html += '                                                                     ▼\n';
    html += '┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐\n';
    html += '│   STEP 7     │◀───│   STEP 6     │◀───│   STEP 5     │◀───│              │\n';
    html += '│ Generate Output│ Perform Analytics Execute Searches│              │\n';
    html += '└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘\n';
    html += '</pre>';
    html += '</div>';

    const steps = [
        {n:1,t:'LOAD & VALIDATE DATA',d:'Load the CSV dataset and validate its structure.',i:['Read CSV file containing YouTube posts and comments','Validate required columns: id, url, content, author_id, parent_id','Check for data integrity issues','Filter out invalid or malformed entries','Statistics: Total rows, valid comments, orphaned comments']},
        {n:2,t:'DISCOVER VIDEOS',d:'Identify which posts are videos vs comments.',i:['Parse URLs to extract video IDs','Group comments by parent video using parent_id relationships','Handle orphaned comments (comments without identifiable videos)','Build Video objects with associated Comment objects','Optional: Step 2.5 attempts to reassign orphaned comments using semantic similarity']},
        {n:3,t:'GENERATE EMBEDDINGS',d:'Convert comments to vector representations using OpenAI embeddings.',i:['Use OpenAI text-embedding-3-small model','Generate 1536-dimensional embedding vectors for each comment','Cache embeddings to avoid duplicate API calls','Enable semantic search and similarity comparisons','Required for search execution and orphaned comment reassignment']},
        {n:4,t:'GENERATE SEARCH SPECIFICATIONS',d:'Create search queries to find relevant comments.',i:['<strong>Static Specs:</strong> Universal searches applied to all videos','<strong>Dynamic Specs:</strong> Video-specific searches generated by analyzing comment samples with LLM','LLM (GPT-4o) analyzes 10 sample comments per video to understand context','Generates 5 custom search specifications per video','Each spec includes: query, context, filters, extract_fields, rationale']},
        {n:5,t:'EXECUTE SEARCHES',d:'Run semantic search + LLM ranking to find matching comments.',i:['<strong>Phase 1:</strong> Semantic Search - Find top 30 candidates using cosine similarity on embeddings','<strong>Phase 2:</strong> LLM Ranking - Use GPT-4o-mini to re-rank candidates by true relevance','Apply filters specified in CommentSearchSpec','Extract insights from matched comments','Store SearchResult objects with matched comments and relevance scores']},
        {n:6,t:'PERFORM ANALYTICS',d:'Analyze sentiment, extract topics, and identify questions.',i:['<strong>Sentiment Analysis:</strong> Batch comments and score each 0-1 (negative to positive) using GPT-4o-mini','<strong>Topic Extraction:</strong> Cluster comments using K-means on embeddings, generate topic labels with LLM','<strong>Question Finding:</strong> Extract questions from comments, validate and categorize them','Calculate aggregate statistics (overall sentiment, distribution)','Generate AnalyticsResult objects for each video']},
        {n:7,t:'GENERATE OUTPUT',d:'Save results and generate visualization.',i:['Create timestamped output directory','Save results.json with complete analysis data','Save metadata.json with run statistics','Save session.pkl for future reuse/categorization','Generate HTML visualization (this page)','Display summary statistics and next steps']}
    ];

    html += '<div class="steps-section">';
    html += '<h3>DETAILED STEPS</h3>';

    steps.forEach(step => {
        html += '<div class="step-box">';
        html += '<div class="step-header" onclick="toggleStep(this)"><span>STEP ' + step.n + ': ' + step.t + '</span><span class="step-toggle">+</span></div>';
        html += '<div class="step-content"><p><strong>' + step.d + '</strong></p><ul>';
        step.i.forEach(detail => {
            html += '<li>' + detail + '</li>';
        });
        html += '</ul></div></div>';
    });

    html += '</div>'; // Close steps-section

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

function toggleVideo(videoId) {
    const content = document.getElementById(videoId);
    const toggle = document.getElementById(videoId + '-toggle');

    if (content.style.display === 'none') {
        content.style.display = 'block';
        toggle.textContent = '-';
    } else {
        content.style.display = 'none';
        toggle.textContent = '+';
    }
}

function showLoading(show, message = 'LOADING...') {
    const loadingElement = document.getElementById('loading');
    loadingElement.textContent = message;
    loadingElement.style.display = show ? 'block' : 'none';
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

function switchVideoTab(videoId, tabName) {
    // Hide all tab contents for this video
    document.querySelectorAll(`[id^="${videoId}-"]`).forEach(tab => {
        if (tab.classList.contains('video-tab-content')) {
            tab.classList.remove('active');
        }
    });

    // Remove active class from all buttons for this video
    const videoCard = document.getElementById(videoId).closest('.video-card');
    videoCard.querySelectorAll('.video-tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    // Show selected tab
    const selectedTab = document.getElementById(videoId + '-' + tabName);
    if (selectedTab) {
        selectedTab.classList.add('active');
    }

    // Add active class to clicked button
    const buttons = videoCard.querySelectorAll('.video-tab-btn');
    buttons.forEach(btn => {
        if (btn.textContent.toLowerCase().includes(tabName)) {
            btn.classList.add('active');
        }
    });
}

function createTopicsPieChart(videoId, topics) {
    const canvas = document.getElementById(videoId + '-pie-chart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const centerX = 140;
    const centerY = 140;
    const radius = 100;

    // Calculate total and percentages
    const total = topics.reduce((sum, topic) => sum + topic.comment_count, 0);
    const colors = ['#FF00FF', '#00FF00', '#FFF59D', '#90EE90', '#00FFFF'];

    let currentAngle = -Math.PI / 2; // Start at top

    topics.forEach((topic, index) => {
        const percentage = topic.comment_count / total;
        const sliceAngle = percentage * 2 * Math.PI;
        const color = colors[index % colors.length];

        // Draw slice
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.moveTo(centerX, centerY);
        ctx.arc(centerX, centerY, radius, currentAngle, currentAngle + sliceAngle);
        ctx.closePath();
        ctx.fill();

        // Draw border
        ctx.strokeStyle = '#000';
        ctx.lineWidth = 2;
        ctx.stroke();

        // Draw percentage label
        const labelAngle = currentAngle + sliceAngle / 2;
        const labelX = centerX + (radius * 0.7) * Math.cos(labelAngle);
        const labelY = centerY + (radius * 0.7) * Math.sin(labelAngle);

        ctx.fillStyle = '#000';
        ctx.font = 'bold 16px "Courier New"';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(Math.round(percentage * 100) + '%', labelX, labelY);

        currentAngle += sliceAngle;
    });

    // Draw center circle for donut effect
    ctx.fillStyle = '#fff';
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius * 0.5, 0, 2 * Math.PI);
    ctx.fill();
    ctx.strokeStyle = '#000';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Draw center text
    ctx.fillStyle = '#000';
    ctx.font = 'bold 14px "Courier New"';
    ctx.textAlign = 'center';
    ctx.fillText('TOP 5', centerX, centerY - 5);
    ctx.font = '12px "Courier New"';
    ctx.fillText('TOPICS', centerX, centerY + 10);
}

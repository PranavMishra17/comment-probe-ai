"""
Topic extraction using clustering + LLM labeling.

Discovers topics using KMeans clustering on embeddings.
"""

import logging
import json
from typing import List, Optional
import numpy as np
from sklearn.cluster import KMeans

from src.core.models import Comment, TopicCluster
from src.ai.openai_client import OpenAIClient
from src.ai.embedder import Embedder
from src.ai.prompts import Prompts
from config import Config

logger = logging.getLogger(__name__)


class TopicExtractor:
    """
    Discovers and labels topics using clustering + LLM.
    """

    def __init__(self, embedder: Embedder, openai_client: OpenAIClient):
        """
        Initialize topic extractor.

        Args:
            embedder: Embedder for getting embeddings
            openai_client: OpenAI client for labeling
        """
        self.embedder = embedder
        self.openai_client = openai_client
        self.prompts = Prompts()
        logger.info("[TopicExtractor] Initialized")

    def extract_topics(
        self,
        comments: List[Comment],
        num_topics: Optional[int] = None
    ) -> List[TopicCluster]:
        """
        Extracts top topics from comments.

        Args:
            comments: List of comments
            num_topics: Number of topics to return

        Returns:
            List of TopicCluster objects
        """
        num_topics = num_topics or Config.NUM_TOPICS
        logger.info(f"[TopicExtractor] Extracting {num_topics} topics from {len(comments)} comments")

        # Collect embeddings
        embeddings = []
        valid_comments = []
        for comment in comments:
            if comment.embedding is not None:
                embeddings.append(comment.embedding)
                valid_comments.append(comment)

        if len(embeddings) < num_topics:
            logger.warning(f"[TopicExtractor] Too few comments for {num_topics} topics")
            return []

        # Cluster
        embeddings_array = np.array(embeddings)
        labels = self._cluster_embeddings(embeddings_array, n_clusters=min(10, len(embeddings)))

        # Group by cluster
        clusters = {}
        for comment, label in zip(valid_comments, labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(comment)

        # Sort clusters by size
        sorted_clusters = sorted(clusters.items(), key=lambda x: len(x[1]), reverse=True)

        # Label top clusters
        topics = []
        for cluster_id, cluster_comments in sorted_clusters[:num_topics]:
            topic = self._label_cluster(cluster_comments)
            topics.append(topic)

        logger.info(f"[TopicExtractor] Extracted {len(topics)} topics")
        return topics

    def _cluster_embeddings(self, embeddings: np.ndarray, n_clusters: int) -> np.ndarray:
        """
        Performs KMeans clustering.

        Args:
            embeddings: Array of embeddings
            n_clusters: Number of clusters

        Returns:
            Array of cluster labels
        """
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(embeddings)
        return labels

    def _label_cluster(self, cluster_comments: List[Comment]) -> TopicCluster:
        """
        Labels a cluster using LLM.

        Args:
            cluster_comments: Comments in the cluster

        Returns:
            TopicCluster object
        """
        # Sample representatives
        representatives = cluster_comments[:5]

        # Generate label
        prompt = self.prompts.format_topic_prompt(representatives)

        try:
            result = self.openai_client.create_completion(
                messages=[
                    {"role": "system", "content": "You are an expert at topic labeling."},
                    {"role": "user", "content": prompt}
                ],
                model=Config.FAST_COMPLETION_MODEL,
                response_format={"type": "json_object"}
            )

            data = json.loads(result.content)
            topic_name = data.get("topic_name", "Unnamed Topic")
            keywords = data.get("keywords", [])

        except Exception as e:
            logger.error(f"[TopicExtractor] Failed to label cluster: {e}")
            topic_name = "General Discussion"
            keywords = []

        total_comments = len(cluster_comments)
        percentage = 0.0  # Would need total comment count to calculate

        return TopicCluster(
            topic_name=topic_name,
            comment_count=total_comments,
            percentage=percentage,
            representative_comments=representatives[:3],
            keywords=keywords
        )

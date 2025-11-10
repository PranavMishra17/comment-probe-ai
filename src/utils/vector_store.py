"""
Vector database management using ChromaDB.

Provides persistent storage and fast retrieval of embeddings.
"""

import logging
import os
from typing import List, Dict, Optional, Tuple
import chromadb
from chromadb.config import Settings

from src.core.models import Comment

logger = logging.getLogger(__name__)


class VectorStore:
    """
    Vector database for storing and retrieving embeddings.

    Uses ChromaDB for efficient similarity search and persistence.
    """

    def __init__(self, persist_directory: str = "./chroma_db"):
        """
        Initialize vector store.

        Args:
            persist_directory: Directory for persisting ChromaDB data
        """
        self.persist_directory = persist_directory
        logger.info(f"[VectorStore] Initializing with directory: {persist_directory}")

        try:
            # Create persist directory
            os.makedirs(persist_directory, exist_ok=True)

            # Initialize ChromaDB client
            self.client = chromadb.Client(Settings(
                persist_directory=persist_directory,
                anonymized_telemetry=False
            ))

            logger.info("[VectorStore] ChromaDB client initialized")

        except Exception as e:
            logger.error(f"[VectorStore] Failed to initialize: {e}", exc_info=True)
            raise

    def create_collection(self, name: str, metadata: Optional[Dict] = None) -> None:
        """
        Creates a new collection for storing embeddings.

        Args:
            name: Collection name
            metadata: Optional metadata
        """
        logger.info(f"[VectorStore] Creating collection: {name}")

        try:
            # Delete if exists
            try:
                self.client.delete_collection(name)
            except:
                pass

            # Create collection
            self.client.create_collection(
                name=name,
                metadata=metadata or {}
            )

            logger.info(f"[VectorStore] Collection created: {name}")

        except Exception as e:
            logger.error(f"[VectorStore] Failed to create collection: {e}", exc_info=True)
            raise

    def add_comments(
        self,
        collection_name: str,
        comments: List[Comment]
    ) -> None:
        """
        Adds comments with embeddings to collection.

        Args:
            collection_name: Name of collection
            comments: List of comments with embeddings
        """
        logger.info(f"[VectorStore] Adding {len(comments)} comments to {collection_name}")

        try:
            collection = self.client.get_collection(collection_name)

            # Prepare data
            ids = []
            embeddings = []
            documents = []
            metadatas = []

            for comment in comments:
                if comment.embedding is None:
                    continue

                ids.append(comment.id)
                embeddings.append(comment.embedding)
                documents.append(comment.cleaned_content or comment.content)
                metadatas.append({
                    'author_id': comment.author_id,
                    'parent_id': comment.parent_id,
                    'url': comment.url
                })

            if not ids:
                logger.warning("[VectorStore] No embeddings to add")
                return

            # Add to collection
            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )

            logger.info(f"[VectorStore] Added {len(ids)} embeddings")

        except Exception as e:
            logger.error(f"[VectorStore] Failed to add comments: {e}", exc_info=True)
            raise

    def search(
        self,
        collection_name: str,
        query_embedding: List[float],
        top_k: int = 10,
        filter_dict: Optional[Dict] = None
    ) -> List[Tuple[str, float, str]]:
        """
        Searches for similar embeddings.

        Args:
            collection_name: Name of collection
            query_embedding: Query embedding vector
            top_k: Number of results to return
            filter_dict: Optional metadata filter

        Returns:
            List of (id, distance, document) tuples
        """
        logger.info(f"[VectorStore] Searching in {collection_name} with top_k={top_k}")

        try:
            collection = self.client.get_collection(collection_name)

            # Search
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filter_dict
            )

            # Format results
            formatted_results = []
            for i in range(len(results['ids'][0])):
                comment_id = results['ids'][0][i]
                distance = results['distances'][0][i]
                document = results['documents'][0][i]
                formatted_results.append((comment_id, distance, document))

            logger.info(f"[VectorStore] Found {len(formatted_results)} results")
            return formatted_results

        except Exception as e:
            logger.error(f"[VectorStore] Search failed: {e}", exc_info=True)
            return []

    def get_comment(self, collection_name: str, comment_id: str) -> Optional[Dict]:
        """
        Retrieves a specific comment by ID.

        Args:
            collection_name: Name of collection
            comment_id: Comment ID

        Returns:
            Comment data or None
        """
        try:
            collection = self.client.get_collection(collection_name)
            result = collection.get(ids=[comment_id])

            if result['ids']:
                return {
                    'id': result['ids'][0],
                    'embedding': result['embeddings'][0] if result['embeddings'] else None,
                    'document': result['documents'][0] if result['documents'] else None,
                    'metadata': result['metadatas'][0] if result['metadatas'] else None
                }

            return None

        except Exception as e:
            logger.error(f"[VectorStore] Failed to get comment: {e}")
            return None

    def get_statistics(self, collection_name: str) -> Dict:
        """
        Gets statistics about a collection.

        Args:
            collection_name: Name of collection

        Returns:
            Statistics dictionary
        """
        try:
            collection = self.client.get_collection(collection_name)
            count = collection.count()

            return {
                'name': collection_name,
                'count': count,
                'persist_directory': self.persist_directory
            }

        except Exception as e:
            logger.error(f"[VectorStore] Failed to get statistics: {e}")
            return {}

    def list_collections(self) -> List[str]:
        """
        Lists all collections.

        Returns:
            List of collection names
        """
        try:
            collections = self.client.list_collections()
            return [c.name for c in collections]
        except Exception as e:
            logger.error(f"[VectorStore] Failed to list collections: {e}")
            return []

    def delete_collection(self, collection_name: str) -> None:
        """
        Deletes a collection.

        Args:
            collection_name: Name of collection to delete
        """
        logger.info(f"[VectorStore] Deleting collection: {collection_name}")

        try:
            self.client.delete_collection(collection_name)
            logger.info(f"[VectorStore] Collection deleted: {collection_name}")
        except Exception as e:
            logger.error(f"[VectorStore] Failed to delete collection: {e}")

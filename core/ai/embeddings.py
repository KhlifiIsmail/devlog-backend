"""
Vector Embeddings and Similarity Search Service for DevLog.
Provides ChromaDB integration for session and commit embeddings.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
import json
from datetime import datetime

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from django.conf import settings

from core.tracking.models import CodingSession, Commit

logger = logging.getLogger(__name__)


class VectorStoreService:
    """
    Service for managing vector embeddings and similarity search.
    Uses ChromaDB for storage and sentence-transformers for embeddings.
    """

    def __init__(self):
        """Initialize the vector store service."""
        # ChromaDB configuration
        chroma_host = getattr(settings, 'CHROMADB_HOST', 'localhost')
        chroma_port = getattr(settings, 'CHROMADB_PORT', 8000)

        # Initialize ChromaDB client
        self.chroma_client = chromadb.HttpClient(
            host=chroma_host,
            port=chroma_port,
            settings=Settings(anonymized_telemetry=False)
        )

        # Initialize embedding model
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

        # Collection names
        self.sessions_collection_name = "coding_sessions"
        self.commits_collection_name = "commits"

        # Initialize collections
        self._initialize_collections()

    def _initialize_collections(self):
        """Initialize or get ChromaDB collections."""
        try:
            # Sessions collection
            self.sessions_collection = self.chroma_client.get_or_create_collection(
                name=self.sessions_collection_name,
                metadata={"description": "Coding session embeddings for similarity search"}
            )

            # Commits collection
            self.commits_collection = self.chroma_client.get_or_create_collection(
                name=self.commits_collection_name,
                metadata={"description": "Individual commit embeddings for pattern detection"}
            )

            logger.info("ChromaDB collections initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB collections: {str(e)}")
            raise RuntimeError(f"ChromaDB initialization failed: {str(e)}")

    def add_session_embedding(self, session_id: int) -> bool:
        """
        Generate and store embedding for a coding session.

        Args:
            session_id: ID of the CodingSession

        Returns:
            True if successful, False otherwise
        """
        try:
            session = CodingSession.objects.get(id=session_id)
            commits = session.commits.all()

            # Create text representation for embedding
            session_text = self._create_session_text(session, commits)

            # Generate embedding
            embedding = self.embedding_model.encode(session_text).tolist()

            # Prepare metadata
            metadata = {
                "session_id": session_id,
                "repository": session.repository.full_name,
                "user_id": session.user.id,
                "username": session.user.username,
                "duration_minutes": session.duration_minutes,
                "total_commits": session.total_commits,
                "total_additions": session.total_additions,
                "total_deletions": session.total_deletions,
                "files_changed": session.files_changed,
                "primary_language": session.primary_language or "unknown",
                "started_at": session.started_at.isoformat(),
                "ended_at": session.ended_at.isoformat(),
                "languages_used": json.dumps(session.languages_used or [])
            }

            # Store in ChromaDB
            self.sessions_collection.add(
                embeddings=[embedding],
                documents=[session_text],
                metadatas=[metadata],
                ids=[f"session_{session_id}"]
            )

            logger.info(f"Added embedding for session {session_id}")
            return True

        except CodingSession.DoesNotExist:
            logger.error(f"Session {session_id} not found")
            return False
        except Exception as e:
            logger.error(f"Failed to add session embedding {session_id}: {str(e)}")
            return False

    def add_commit_embedding(self, commit_id: int) -> bool:
        """
        Generate and store embedding for a single commit.

        Args:
            commit_id: ID of the Commit

        Returns:
            True if successful, False otherwise
        """
        try:
            commit = Commit.objects.get(id=commit_id)

            # Create text representation
            commit_text = self._create_commit_text(commit)

            # Generate embedding
            embedding = self.embedding_model.encode(commit_text).tolist()

            # Prepare metadata
            metadata = {
                "commit_id": commit_id,
                "session_id": commit.session_id if commit.session else None,
                "repository": commit.repository.full_name,
                "sha": commit.sha,
                "author_name": commit.author_name,
                "additions": commit.additions,
                "deletions": commit.deletions,
                "changed_files": commit.changed_files,
                "committed_at": commit.committed_at.isoformat(),
                "branch": commit.branch or "unknown"
            }

            # Store in ChromaDB
            self.commits_collection.add(
                embeddings=[embedding],
                documents=[commit_text],
                metadatas=[metadata],
                ids=[f"commit_{commit_id}"]
            )

            logger.info(f"Added embedding for commit {commit_id}")
            return True

        except Commit.DoesNotExist:
            logger.error(f"Commit {commit_id} not found")
            return False
        except Exception as e:
            logger.error(f"Failed to add commit embedding {commit_id}: {str(e)}")
            return False

    def find_similar_sessions(
        self,
        session_id: int,
        limit: int = 5,
        user_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Find sessions similar to the given session.

        Args:
            session_id: ID of the reference session
            limit: Maximum number of similar sessions to return
            user_only: Whether to limit results to same user

        Returns:
            List of similar sessions with similarity scores
        """
        try:
            session = CodingSession.objects.get(id=session_id)

            # Get session embedding from ChromaDB
            results = self.sessions_collection.get(
                ids=[f"session_{session_id}"],
                include=['embeddings']
            )

            if not results['embeddings']:
                # Generate embedding if not exists
                if not self.add_session_embedding(session_id):
                    return []

                # Retry getting embedding
                results = self.sessions_collection.get(
                    ids=[f"session_{session_id}"],
                    include=['embeddings']
                )

            embedding = results['embeddings'][0]

            # Build where clause for filtering
            where_clause = {}
            if user_only:
                where_clause["user_id"] = session.user.id

            # Query similar sessions
            similar_results = self.sessions_collection.query(
                query_embeddings=[embedding],
                n_results=limit + 1,  # +1 to exclude self
                where=where_clause,
                include=['metadatas', 'distances']
            )

            # Process results
            similar_sessions = []
            for i, metadata in enumerate(similar_results['metadatas'][0]):
                session_id_result = metadata['session_id']

                # Skip self
                if session_id_result == session_id:
                    continue

                similarity_score = 1 - similar_results['distances'][0][i]  # Convert distance to similarity

                similar_sessions.append({
                    'session_id': session_id_result,
                    'similarity_score': similarity_score,
                    'repository': metadata['repository'],
                    'duration_minutes': metadata['duration_minutes'],
                    'total_commits': metadata['total_commits'],
                    'primary_language': metadata['primary_language'],
                    'started_at': metadata['started_at'],
                    'files_changed': metadata['files_changed']
                })

            # Sort by similarity score (highest first)
            similar_sessions.sort(key=lambda x: x['similarity_score'], reverse=True)

            return similar_sessions[:limit]

        except CodingSession.DoesNotExist:
            logger.error(f"Session {session_id} not found")
            return []
        except Exception as e:
            logger.error(f"Failed to find similar sessions for {session_id}: {str(e)}")
            return []

    def find_similar_commits(
        self,
        commit_message: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find commits similar to the given commit message.

        Args:
            commit_message: The commit message to search for
            limit: Maximum number of similar commits to return

        Returns:
            List of similar commits with similarity scores
        """
        try:
            # Generate embedding for the query
            query_embedding = self.embedding_model.encode(commit_message).tolist()

            # Query similar commits
            similar_results = self.commits_collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                include=['metadatas', 'distances', 'documents']
            )

            # Process results
            similar_commits = []
            for i, metadata in enumerate(similar_results['metadatas'][0]):
                similarity_score = 1 - similar_results['distances'][0][i]
                document = similar_results['documents'][0][i]

                similar_commits.append({
                    'commit_id': metadata['commit_id'],
                    'similarity_score': similarity_score,
                    'sha': metadata['sha'],
                    'repository': metadata['repository'],
                    'author_name': metadata['author_name'],
                    'committed_at': metadata['committed_at'],
                    'additions': metadata['additions'],
                    'deletions': metadata['deletions'],
                    'document': document
                })

            return similar_commits

        except Exception as e:
            logger.error(f"Failed to find similar commits: {str(e)}")
            return []

    def _create_session_text(self, session: CodingSession, commits) -> str:
        """Create text representation of a coding session for embedding."""
        # Combine commit messages
        commit_messages = [commit.message for commit in commits if commit.message]

        # Create descriptive text
        session_text = f"""
        Repository: {session.repository.full_name}
        Duration: {session.duration_minutes} minutes
        Primary Language: {session.primary_language or 'unknown'}
        Total Commits: {session.total_commits}
        Files Changed: {session.files_changed}
        Total Changes: +{session.total_additions} -{session.total_deletions}
        Languages Used: {', '.join(session.languages_used or [])}

        Commit Messages:
        {' | '.join(commit_messages)}
        """.strip()

        return session_text

    def _create_commit_text(self, commit: Commit) -> str:
        """Create text representation of a commit for embedding."""
        # Include file information if available
        file_info = ""
        if commit.files_data:
            files = [f.get('filename', '') for f in commit.files_data if f.get('filename')]
            file_info = f" Files: {', '.join(files[:10])}"  # Limit to 10 files

        commit_text = f"""
        Message: {commit.message}
        Author: {commit.author_name}
        Repository: {commit.repository.full_name}
        Branch: {commit.branch or 'unknown'}
        Changes: +{commit.additions} -{commit.deletions} in {commit.changed_files} files
        {file_info}
        """.strip()

        return commit_text

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector collections."""
        try:
            sessions_count = self.sessions_collection.count()
            commits_count = self.commits_collection.count()

            return {
                'sessions_count': sessions_count,
                'commits_count': commits_count,
                'embedding_model': 'all-MiniLM-L6-v2',
                'collections': {
                    'sessions': self.sessions_collection_name,
                    'commits': self.commits_collection_name
                }
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {str(e)}")
            return {}
"""
Celery tasks for AI processing in DevLog backend.
Handles background AI narrative generation and embedding processing.
"""

import logging
from typing import Dict, Any
from celery import shared_task
from django.utils import timezone

from .narrative import NarrativeService
from .embeddings import VectorStoreService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_session_narrative(self, session_id: int) -> Dict[str, Any]:
    """
    Generate AI narrative for a coding session.

    Args:
        session_id: ID of the CodingSession to analyze

    Returns:
        Dict with narrative result and metadata
    """
    try:
        logger.info(f"Starting narrative generation for session {session_id}")

        narrative_service = NarrativeService()
        result = narrative_service.generate_session_narrative(session_id)

        logger.info(f"Successfully generated narrative for session {session_id}")
        return {
            'success': True,
            'session_id': session_id,
            'narrative': result['narrative'],
            'generated_at': result['generated_at'],
            'model_used': result['model_used']
        }

    except Exception as exc:
        logger.error(f"Failed to generate narrative for session {session_id}: {str(exc)}")

        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying narrative generation for session {session_id} (attempt {self.request.retries + 1})")
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

        # Final failure
        return {
            'success': False,
            'session_id': session_id,
            'error': str(exc),
            'failed_at': timezone.now().isoformat()
        }


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def add_session_embedding(self, session_id: int) -> Dict[str, Any]:
    """
    Generate and store vector embedding for a coding session.

    Args:
        session_id: ID of the CodingSession to embed

    Returns:
        Dict with embedding result
    """
    try:
        logger.info(f"Adding embedding for session {session_id}")

        vector_service = VectorStoreService()
        success = vector_service.add_session_embedding(session_id)

        if success:
            logger.info(f"Successfully added embedding for session {session_id}")
            return {
                'success': True,
                'session_id': session_id,
                'processed_at': timezone.now().isoformat()
            }
        else:
            raise Exception("Failed to add session embedding")

    except Exception as exc:
        logger.error(f"Failed to add embedding for session {session_id}: {str(exc)}")

        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying embedding for session {session_id} (attempt {self.request.retries + 1})")
            raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))

        # Final failure
        return {
            'success': False,
            'session_id': session_id,
            'error': str(exc),
            'failed_at': timezone.now().isoformat()
        }


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def add_commit_embedding(self, commit_id: int) -> Dict[str, Any]:
    """
    Generate and store vector embedding for a single commit.

    Args:
        commit_id: ID of the Commit to embed

    Returns:
        Dict with embedding result
    """
    try:
        logger.info(f"Adding embedding for commit {commit_id}")

        vector_service = VectorStoreService()
        success = vector_service.add_commit_embedding(commit_id)

        if success:
            logger.info(f"Successfully added embedding for commit {commit_id}")
            return {
                'success': True,
                'commit_id': commit_id,
                'processed_at': timezone.now().isoformat()
            }
        else:
            raise Exception("Failed to add commit embedding")

    except Exception as exc:
        logger.error(f"Failed to add embedding for commit {commit_id}: {str(exc)}")

        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying embedding for commit {commit_id} (attempt {self.request.retries + 1})")
            raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))

        # Final failure
        return {
            'success': False,
            'commit_id': commit_id,
            'error': str(exc),
            'failed_at': timezone.now().isoformat()
        }


@shared_task(bind=True, max_retries=2)
def process_session_complete_ai(self, session_id: int) -> Dict[str, Any]:
    """
    Complete AI processing for a session (narrative + embeddings).

    This task chains both narrative generation and embedding creation.

    Args:
        session_id: ID of the CodingSession to process

    Returns:
        Dict with complete processing result
    """
    try:
        logger.info(f"Starting complete AI processing for session {session_id}")

        # Generate embedding first (faster, less likely to fail)
        embedding_result = add_session_embedding.delay(session_id)

        # Only generate narrative on-demand, so this task just handles embeddings
        # for automatic processing after session creation

        return {
            'success': True,
            'session_id': session_id,
            'embedding_task_id': embedding_result.id,
            'processed_at': timezone.now().isoformat(),
            'note': 'Embedding queued. Narrative will be generated on-demand.'
        }

    except Exception as exc:
        logger.error(f"Failed AI processing for session {session_id}: {str(exc)}")

        if self.request.retries < self.max_retries:
            logger.info(f"Retrying AI processing for session {session_id}")
            raise self.retry(exc=exc, countdown=120)

        return {
            'success': False,
            'session_id': session_id,
            'error': str(exc),
            'failed_at': timezone.now().isoformat()
        }


@shared_task
def batch_process_embeddings(session_ids: list = None, commit_ids: list = None) -> Dict[str, Any]:
    """
    Batch process embeddings for multiple sessions or commits.

    Args:
        session_ids: List of session IDs to process
        commit_ids: List of commit IDs to process

    Returns:
        Dict with batch processing results
    """
    results = {
        'sessions_processed': 0,
        'commits_processed': 0,
        'sessions_failed': 0,
        'commits_failed': 0,
        'started_at': timezone.now().isoformat()
    }

    # Process sessions
    if session_ids:
        logger.info(f"Batch processing {len(session_ids)} session embeddings")
        for session_id in session_ids:
            try:
                add_session_embedding.delay(session_id)
                results['sessions_processed'] += 1
            except Exception as e:
                logger.error(f"Failed to queue session {session_id}: {str(e)}")
                results['sessions_failed'] += 1

    # Process commits
    if commit_ids:
        logger.info(f"Batch processing {len(commit_ids)} commit embeddings")
        for commit_id in commit_ids:
            try:
                add_commit_embedding.delay(commit_id)
                results['commits_processed'] += 1
            except Exception as e:
                logger.error(f"Failed to queue commit {commit_id}: {str(e)}")
                results['commits_failed'] += 1

    results['completed_at'] = timezone.now().isoformat()
    logger.info(f"Batch processing completed: {results}")

    return results


@shared_task
def cleanup_old_narratives(days_old: int = 30) -> Dict[str, Any]:
    """
    Clean up old cached narratives and regenerate if needed.

    Args:
        days_old: Remove cached narratives older than this many days

    Returns:
        Dict with cleanup results
    """
    from django.core.cache import cache
    from core.tracking.models import CodingSession
    from datetime import timedelta

    try:
        # Find sessions with old AI summaries
        cutoff_date = timezone.now() - timedelta(days=days_old)
        old_sessions = CodingSession.objects.filter(
            ai_generated_at__lt=cutoff_date,
            ai_generated_at__isnull=False
        )

        cleared_count = 0
        for session in old_sessions:
            cache_key = f"narrative_{session.id}"
            if cache.delete(cache_key):
                cleared_count += 1

        logger.info(f"Cleared {cleared_count} old cached narratives")

        return {
            'success': True,
            'cleared_count': cleared_count,
            'cutoff_date': cutoff_date.isoformat(),
            'completed_at': timezone.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to cleanup old narratives: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'failed_at': timezone.now().isoformat()
        }
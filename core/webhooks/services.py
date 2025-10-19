import logging
from typing import Dict, Any, Optional, List
from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime

from core.tracking.models import GitHubRepository, Commit, CodingSession
from core.tracking.services import SessionGrouper
from .models import WebhookEvent

User = get_user_model()
logger = logging.getLogger(__name__)


class WebhookProcessor:
    """
    Service for processing GitHub webhook events.
    Handles push events by creating commits and grouping into sessions.
    """
    
    def __init__(self, webhook_event: WebhookEvent):
        self.webhook_event = webhook_event
        self.payload = webhook_event.payload
    
    @transaction.atomic
    def process_push_event(self) -> Dict[str, Any]:
        """
        Process a GitHub push event.
        
        Returns:
            Dict with processing results
        
        Raises:
            ValueError: If payload is invalid
            Exception: For other processing errors
        """
        logger.info(f"Processing push event {self.webhook_event.id}")
        
        # Mark as processing
        self.webhook_event.mark_processing()
        
        try:
            # Extract data from payload
            repo_full_name = self.payload.get('repository', {}).get('full_name')
            repo_github_id = self.payload.get('repository', {}).get('id')
            commits_data = self.payload.get('commits', [])
            pusher_email = self.payload.get('pusher', {}).get('email')
            
            if not repo_full_name:
                raise ValueError("Missing repository full_name in payload")
            
            if not commits_data:
                logger.info("No commits in push event, skipping")
                self.webhook_event.mark_completed()
                return {'commits_created': 0, 'sessions_created': 0}
            
            # Find user first (required for repository)
            user = self._resolve_user(pusher_email, repo_github_id)
            
            if not user:
                # Can't process without a user
                error_msg = f"Cannot process webhook: no user found for {pusher_email} or repo {repo_github_id}"
                logger.warning(error_msg)
                self.webhook_event.mark_failed(error_msg)
                return {'commits_created': 0, 'sessions_created': 0, 'error': 'User not found'}
            
            # Get or create repository
            repository = self._get_or_create_repository(repo_full_name, repo_github_id, user)
            
            # Update webhook event with user
            self.webhook_event.user = user
            self.webhook_event.save(update_fields=['user'])
            
            # Process commits
            commits_created = self._process_commits(repository, commits_data, user)
            
            # Group commits into sessions
            sessions_created = self._group_sessions(repository, user)
            
            # Mark as completed
            self.webhook_event.mark_completed()
            
            result = {
                'commits_created': commits_created,
                'sessions_created': sessions_created,
                'repository': repo_full_name,
                'user_id': user.id,
            }
            
            logger.info(f"Push event processed: {result}")
            return result
        
        except Exception as e:
            logger.error(f"Error processing push event {self.webhook_event.id}: {str(e)}")
            self.webhook_event.mark_failed(str(e))
            raise
    
    def _get_or_create_repository(
        self,
        full_name: str,
        github_id: int,
        user: User
    ) -> GitHubRepository:
        """Get or create repository from webhook payload."""
        repo_data = self.payload.get('repository', {})
        repo_name = full_name.split('/')[-1] if '/' in full_name else full_name
        
        # Try to find existing repository by github_id and user
        if github_id:
            try:
                repository = GitHubRepository.objects.get(
                    github_id=github_id,
                    user=user
                )
                logger.debug(f"Found existing repository: {full_name}")
                return repository
            except GitHubRepository.DoesNotExist:
                pass
        
        # Try to find by full_name and user
        try:
            repository = GitHubRepository.objects.get(
                full_name=full_name,
                user=user
            )
            logger.debug(f"Found existing repository by full_name: {full_name}")
            return repository
        except GitHubRepository.DoesNotExist:
            pass
        
        # Create new repository
        repository = GitHubRepository.objects.create(
            user=user,
            github_id=github_id or 0,
            name=repo_name,
            full_name=full_name,
            description=repo_data.get('description') or '',
            url=repo_data.get('html_url', ''),
            default_branch=repo_data.get('default_branch', 'main'),
            is_private=repo_data.get('private', False),
            is_fork=repo_data.get('fork', False),
            language=repo_data.get('language') or '',
            stars_count=repo_data.get('stargazers_count', 0),
            forks_count=repo_data.get('forks_count', 0),
            is_tracking_enabled=True,
        )
        
        logger.info(f"Created new repository: {full_name} for user {user.id}")
        return repository
    
    def _resolve_user(
        self,
        pusher_email: Optional[str],
        repo_github_id: Optional[int]
    ) -> Optional[User]:
        """
        Resolve user from pusher email or repository ownership.
        
        Priority:
        1. User by existing repository github_id
        2. User by pusher email
        3. None (cannot process)
        """
        # Try to find user by repository they already own
        if repo_github_id:
            try:
                repo = GitHubRepository.objects.filter(github_id=repo_github_id).first()
                if repo and repo.user:
                    logger.debug(f"Found user {repo.user.id} from existing repository")
                    return repo.user
            except Exception as e:
                logger.debug(f"Could not find repository by github_id: {e}")
        
        # Try to find user by pusher email
        if pusher_email:
            try:
                user = User.objects.get(email=pusher_email)
                logger.debug(f"Found user {user.id} by email {pusher_email}")
                return user
            except User.DoesNotExist:
                logger.warning(f"No user found for email {pusher_email}")
        
        logger.warning(f"Could not resolve user for repo {repo_github_id}")
        return None
    
    def _process_commits(
        self,
        repository: GitHubRepository,
        commits_data: List[Dict[str, Any]],
        user: User
    ) -> int:
        """
        Process commits from webhook payload.
        
        Returns:
            Number of commits created
        """
        commits_created = 0
        
        for commit_data in commits_data:
            sha = commit_data.get('id')
            if not sha:
                logger.warning("Commit missing SHA, skipping")
                continue
            
            # Skip if commit already exists
            if Commit.objects.filter(sha=sha).exists():
                logger.debug(f"Commit {sha} already exists, skipping")
                continue
            
            # Parse timestamp
            timestamp_str = commit_data.get('timestamp')
            timestamp = self._parse_timestamp(timestamp_str)
            
            # Count file changes
            added = commit_data.get('added', [])
            removed = commit_data.get('removed', [])
            modified = commit_data.get('modified', [])
            changed_files = len(added) + len(removed) + len(modified)
            
            # Build files_data
            files_data = []
            for file in added:
                files_data.append({'filename': file, 'status': 'added'})
            for file in removed:
                files_data.append({'filename': file, 'status': 'removed'})
            for file in modified:
                files_data.append({'filename': file, 'status': 'modified'})
            
            # Create commit
            commit = Commit.objects.create(
                repository=repository,
                sha=sha,
                message=commit_data.get('message', ''),
                author_name=commit_data.get('author', {}).get('name', ''),
                author_email=commit_data.get('author', {}).get('email', ''),
                committed_at=timestamp,
                additions=0,  # GitHub webhook doesn't include detailed stats
                deletions=0,
                changed_files=changed_files,
                files_data=files_data,
                branch='main',  # Could extract from ref in payload
            )
            
            logger.debug(f"Created commit {commit.sha}")
            commits_created += 1
        
        logger.info(f"Created {commits_created} commits for {repository.full_name}")
        return commits_created
    
    def _group_sessions(
        self,
        repository: GitHubRepository,
        user: User
    ) -> int:
        """
        Group recent commits into coding sessions.
        
        Returns:
            Number of sessions created
        """
        # Get recent ungrouped commits (last 7 days)
        from datetime import timedelta
        cutoff_date = timezone.now() - timedelta(days=7)
        
        ungrouped_commits = Commit.objects.filter(
            repository=repository,
            session__isnull=True,
            committed_at__gte=cutoff_date
        ).order_by('committed_at')
        
        if not ungrouped_commits.exists():
            logger.info("No ungrouped commits to process")
            return 0
        
        # Use SessionGrouper to create sessions
        grouper = SessionGrouper(threshold_minutes=30)
        sessions = grouper.group_commits(list(ungrouped_commits))
        
        logger.info(f"Grouped {ungrouped_commits.count()} commits into {len(sessions)} sessions")
        return len(sessions)
    
    def _parse_timestamp(self, timestamp_str: Optional[str]) -> datetime:
        """Parse ISO 8601 timestamp from GitHub."""
        if not timestamp_str:
            return timezone.now()
        
        try:
            # GitHub uses ISO 8601 format
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            logger.warning(f"Invalid timestamp format: {timestamp_str}")
            return timezone.now()
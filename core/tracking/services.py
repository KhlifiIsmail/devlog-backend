"""Business logic services for tracking app."""

import logging
import requests
from typing import List, Dict, Optional
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from .models import GitHubRepository, Commit, CodingSession

logger = logging.getLogger(__name__)


class GitHubService:
    """Service for interacting with GitHub API."""
    
    BASE_URL = 'https://api.github.com'
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            'Authorization': f'token {access_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
    
    def get_user_repositories(self) -> List[Dict]:
        """
        Fetch all repositories for the authenticated user.
        
        Returns:
            List of repository data dictionaries
        """
        try:
            response = requests.get(
                f'{self.BASE_URL}/user/repos',
                headers=self.headers,
                params={'per_page': 100, 'sort': 'updated'}
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch repositories: {e}")
            return []
    
    def sync_repositories(self, user) -> int:
        """
        Sync user's repositories from GitHub.
        
        Args:
            user: User instance
            
        Returns:
            Number of repositories synced
        """
        repos_data = self.get_user_repositories()
        synced_count = 0
        
        for repo_data in repos_data:
            try:
                repo, created = GitHubRepository.objects.update_or_create(
                    user=user,
                    github_id=repo_data['id'],
                    defaults={
                        'name': repo_data['name'],
                        'full_name': repo_data['full_name'],
                        'description': repo_data.get('description', ''),
                        'url': repo_data['html_url'],
                        'default_branch': repo_data.get('default_branch', 'main'),
                        'is_private': repo_data['private'],
                        'is_fork': repo_data['fork'],
                        'language': repo_data.get('language'),
                        'stars_count': repo_data['stargazers_count'],
                        'forks_count': repo_data['forks_count'],
                        'last_synced_at': timezone.now(),
                    }
                )
                synced_count += 1
                logger.info(f"Synced repository: {repo.full_name}")
            except Exception as e:
                logger.error(f"Failed to sync repository {repo_data['full_name']}: {e}")
        
        return synced_count


class SessionGrouper:
    """
    Service for grouping commits into coding sessions.
    
    A session is defined as a group of commits with < 30 minutes gap between them.
    """
    
    SESSION_TIMEOUT_MINUTES = 30
    
    def __init__(self, user):
        self.user = user
    
    def group_commits(self) -> int:
        """
        Group user's ungrouped commits into sessions.
        
        Returns:
            Number of sessions created
        """
        # Get commits without sessions
        ungrouped_commits = Commit.objects.filter(
            repository__user=self.user,
            session__isnull=True
        ).order_by('committed_at')
        
        if not ungrouped_commits.exists():
            logger.info(f"No ungrouped commits for user {self.user.username}")
            return 0
        
        sessions_created = 0
        current_session = None
        last_commit_time = None
        
        for commit in ungrouped_commits:
            # Check if this commit starts a new session
            if not current_session or self._is_new_session(last_commit_time, commit.committed_at):
                current_session = self._create_new_session(commit)
                sessions_created += 1
                logger.info(f"Created new session: {current_session.id}")
            
            # Add commit to current session
            commit.session = current_session
            commit.save()
            
            # Update session stats
            self._update_session_stats(current_session)
            
            last_commit_time = commit.committed_at
        
        logger.info(f"Created {sessions_created} sessions for user {self.user.username}")
        return sessions_created
    
    def _is_new_session(self, last_time, current_time) -> bool:
        """Check if enough time has passed to start new session."""
        if not last_time:
            return True
        
        gap_minutes = (current_time - last_time).total_seconds() / 60
        return gap_minutes > self.SESSION_TIMEOUT_MINUTES
    
    def _create_new_session(self, first_commit: Commit) -> CodingSession:
        """Create a new coding session."""
        return CodingSession.objects.create(
            user=self.user,
            repository=first_commit.repository,
            started_at=first_commit.committed_at,
            ended_at=first_commit.committed_at,
            duration_minutes=0,
        )
    
    def _update_session_stats(self, session: CodingSession) -> None:
        """Update session statistics from its commits."""
        session.update_stats()


class CommitProcessor:
    """Service for processing commit data from webhooks."""
    
    @staticmethod
    def process_commit_data(repository: GitHubRepository, commit_data: Dict) -> Optional[Commit]:
        """
        Process a single commit from webhook payload.
        
        Args:
            repository: GitHubRepository instance
            commit_data: Commit data from webhook
            
        Returns:
            Created/updated Commit instance or None if failed
        """
        try:
            commit, created = Commit.objects.update_or_create(
                sha=commit_data['id'],
                defaults={
                    'repository': repository,
                    'message': commit_data['message'],
                    'author_name': commit_data['author']['name'],
                    'author_email': commit_data['author']['email'],
                    'committed_at': commit_data['timestamp'],
                    'additions': len(commit_data.get('added', [])),
                    'deletions': len(commit_data.get('removed', [])),
                    'changed_files': len(commit_data.get('modified', [])),
                    'files_data': commit_data.get('modified', []),
                }
            )
            
            if created:
                logger.info(f"Created new commit: {commit.sha[:7]}")
            else:
                logger.info(f"Updated existing commit: {commit.sha[:7]}")
            
            return commit
        except Exception as e:
            logger.error(f"Failed to process commit {commit_data.get('id')}: {e}")
            return None
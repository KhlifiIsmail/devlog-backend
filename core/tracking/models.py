"""Tracking models - Repository, Commit, CodingSession."""

from django.db import models
from django.conf import settings


class GitHubRepository(models.Model):
    """
    Represents a GitHub repository tracked by the user.
    """
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='repositories',
        help_text='User who owns this repository'
    )
    
    github_id = models.BigIntegerField(
        unique=True,
        db_index=True,
        help_text='GitHub repository ID'
    )
    
    name = models.CharField(
        max_length=255,
        help_text='Repository name'
    )
    
    full_name = models.CharField(
        max_length=255,
        help_text='Full repository name (owner/repo)'
    )
    
    description = models.TextField(
        blank=True,
        null=True,
        help_text='Repository description'
    )
    
    url = models.URLField(
        max_length=500,
        help_text='GitHub repository URL'
    )
    
    default_branch = models.CharField(
        max_length=100,
        default='main',
        help_text='Default branch name'
    )
    
    is_private = models.BooleanField(
        default=False,
        help_text='Is this a private repository?'
    )
    
    is_fork = models.BooleanField(
        default=False,
        help_text='Is this repository a fork?'
    )
    
    language = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='Primary programming language'
    )
    
    stars_count = models.IntegerField(
        default=0,
        help_text='Number of stars'
    )
    
    forks_count = models.IntegerField(
        default=0,
        help_text='Number of forks'
    )
    
    is_tracking_enabled = models.BooleanField(
        default=True,
        help_text='Track commits from this repository?'
    )
    
    webhook_id = models.BigIntegerField(
        null=True,
        blank=True,
        help_text='GitHub webhook ID'
    )
    
    last_synced_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Last time we synced with GitHub'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'repositories'
        ordering = ['-created_at']
        unique_together = [['user', 'github_id']]
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['github_id']),
            models.Index(fields=['is_tracking_enabled']),
        ]
        verbose_name = 'GitHub Repository'
        verbose_name_plural = 'GitHub Repositories'
    
    def __str__(self) -> str:
        return self.full_name
    
    @property
    def total_commits(self) -> int:
        """Get total number of commits in this repository."""
        return self.commits.count()
    
    @property
    def total_sessions(self) -> int:
        """Get total number of coding sessions in this repository."""
        return self.sessions.count()


class Commit(models.Model):
    """
    Represents a single Git commit from GitHub.
    """
    
    repository = models.ForeignKey(
        GitHubRepository,
        on_delete=models.CASCADE,
        related_name='commits',
        help_text='Repository this commit belongs to'
    )
    
    session = models.ForeignKey(
        'CodingSession',
        on_delete=models.SET_NULL,
        related_name='commits',
        null=True,
        blank=True,
        help_text='Coding session this commit belongs to'
    )
    
    sha = models.CharField(
        max_length=40,
        unique=True,
        db_index=True,
        help_text='Git commit SHA'
    )
    
    message = models.TextField(
        help_text='Commit message'
    )
    
    author_name = models.CharField(
        max_length=255,
        help_text='Commit author name'
    )
    
    author_email = models.EmailField(
        help_text='Commit author email'
    )
    
    committed_at = models.DateTimeField(
        db_index=True,
        help_text='When the commit was made'
    )
    
    additions = models.IntegerField(
        default=0,
        help_text='Lines added'
    )
    
    deletions = models.IntegerField(
        default=0,
        help_text='Lines deleted'
    )
    
    changed_files = models.IntegerField(
        default=0,
        help_text='Number of files changed'
    )
    
    files_data = models.JSONField(
        default=list,
        blank=True,
        help_text='List of changed files with details'
    )
    
    branch = models.CharField(
        max_length=255,
        default='main',
        help_text='Branch name'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'commits'
        ordering = ['-committed_at']
        indexes = [
            models.Index(fields=['repository', '-committed_at']),
            models.Index(fields=['session', '-committed_at']),
            models.Index(fields=['sha']),
        ]
        verbose_name = 'Commit'
        verbose_name_plural = 'Commits'
    
    def __str__(self) -> str:
        return f"{self.sha[:7]} - {self.message[:50]}"
    
    @property
    def net_lines(self) -> int:
        """Calculate net lines changed (additions - deletions)."""
        return self.additions - self.deletions
    
    @property
    def total_changes(self) -> int:
        """Calculate total lines changed (additions + deletions)."""
        return self.additions + self.deletions
    
    @property
    def short_message(self) -> str:
        """Get first line of commit message."""
        return self.message.split('\n')[0]


class CodingSession(models.Model):
    """
    Represents a logical coding session - a group of commits within a time window.
    
    Sessions are created by grouping commits with < 30 minutes gap between them.
    """
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sessions',
        help_text='User who created this session'
    )
    
    repository = models.ForeignKey(
        GitHubRepository,
        on_delete=models.CASCADE,
        related_name='sessions',
        null=True,
        blank=True,
        help_text='Repository where session occurred'
    )
    
    started_at = models.DateTimeField(
        db_index=True,
        help_text='Session start time'
    )
    
    ended_at = models.DateTimeField(
        help_text='Session end time'
    )
    
    duration_minutes = models.IntegerField(
        default=0,
        help_text='Session duration in minutes'
    )
    
    total_commits = models.IntegerField(
        default=0,
        help_text='Number of commits in session'
    )
    
    total_additions = models.IntegerField(
        default=0,
        help_text='Total lines added'
    )
    
    total_deletions = models.IntegerField(
        default=0,
        help_text='Total lines deleted'
    )
    
    files_changed = models.IntegerField(
        default=0,
        help_text='Number of unique files changed'
    )
    
    primary_language = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='Most used programming language'
    )
    
    languages_used = models.JSONField(
        default=list,
        blank=True,
        help_text='List of all languages used'
    )
    
    ai_summary = models.TextField(
        blank=True,
        null=True,
        help_text='AI-generated session narrative'
    )
    
    ai_generated_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text='When AI summary was generated'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'coding_sessions'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['user', '-started_at']),
            models.Index(fields=['repository', '-started_at']),
            models.Index(fields=['-started_at']),
        ]
        verbose_name = 'Coding Session'
        verbose_name_plural = 'Coding Sessions'
    
    def __str__(self) -> str:
        repo_name = self.repository.name if self.repository else 'Multiple repos'
        return f"{repo_name} - {self.started_at.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def net_lines(self) -> int:
        """Calculate net lines changed."""
        return self.total_additions - self.total_deletions
    
    @property
    def total_changes(self) -> int:
        """Calculate total lines changed."""
        return self.total_additions + self.total_deletions
    
    def update_stats(self) -> None:
        """
        Recalculate session statistics from commits.
        Should be called after adding/removing commits.
        """
        commits = self.commits.all()
        
        if not commits.exists():
            return
        
        # Update time range
        self.started_at = commits.order_by('committed_at').first().committed_at
        self.ended_at = commits.order_by('-committed_at').first().committed_at
        self.duration_minutes = int(
            (self.ended_at - self.started_at).total_seconds() / 60
        )
        
        # Update stats
        self.total_commits = commits.count()
        self.total_additions = sum(c.additions for c in commits)
        self.total_deletions = sum(c.deletions for c in commits)
        self.files_changed = sum(c.changed_files for c in commits)
        
        # Update languages
        languages = {}
        for commit in commits:
            for file_data in commit.files_data:
                if 'language' in file_data:
                    lang = file_data['language']
                    languages[lang] = languages.get(lang, 0) + 1
        
        if languages:
            self.languages_used = list(languages.keys())
            self.primary_language = max(languages, key=languages.get)
        
        self.save()
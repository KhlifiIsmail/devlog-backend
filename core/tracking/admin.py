"""Admin configuration for tracking app."""

from django.contrib import admin
from .models import GitHubRepository, Commit, CodingSession


@admin.register(GitHubRepository)
class GitHubRepositoryAdmin(admin.ModelAdmin):
    """Admin for GitHub repositories."""
    
    list_display = [
        'full_name',
        'user',
        'language',
        'is_private',
        'is_tracking_enabled',
        'stars_count',
        'created_at',
    ]
    list_filter = [
        'is_private',
        'is_fork',
        'is_tracking_enabled',
        'language',
        'created_at',
    ]
    search_fields = [
        'name',
        'full_name',
        'description',
        'user__username',
    ]
    readonly_fields = [
        'github_id',
        'created_at',
        'updated_at',
        'last_synced_at',
    ]
    fieldsets = (
        ('Basic Info', {
            'fields': (
                'user',
                'github_id',
                'name',
                'full_name',
                'description',
                'url',
            )
        }),
        ('Repository Details', {
            'fields': (
                'default_branch',
                'is_private',
                'is_fork',
                'language',
                'stars_count',
                'forks_count',
            )
        }),
        ('Tracking', {
            'fields': (
                'is_tracking_enabled',
                'webhook_id',
                'last_synced_at',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
            )
        }),
    )


@admin.register(Commit)
class CommitAdmin(admin.ModelAdmin):
    """Admin for commits."""
    
    list_display = [
        'sha_short',
        'repository',
        'author_name',
        'committed_at',
        'additions',
        'deletions',
        'session',
    ]
    list_filter = [
        'repository',
        'branch',
        'committed_at',
    ]
    search_fields = [
        'sha',
        'message',
        'author_name',
        'author_email',
    ]
    readonly_fields = [
        'sha',
        'created_at',
    ]
    date_hierarchy = 'committed_at'
    
    def sha_short(self, obj):
        """Display short SHA."""
        return obj.sha[:7]
    sha_short.short_description = 'SHA'


@admin.register(CodingSession)
class CodingSessionAdmin(admin.ModelAdmin):
    """Admin for coding sessions."""
    
    list_display = [
        'id',
        'user',
        'repository',
        'started_at',
        'duration_minutes',
        'total_commits',
        'primary_language',
        'has_ai_summary',
    ]
    list_filter = [
        'user',
        'repository',
        'primary_language',
        'started_at',
    ]
    search_fields = [
        'user__username',
        'repository__name',
        'ai_summary',
    ]
    readonly_fields = [
        'created_at',
        'updated_at',
    ]
    date_hierarchy = 'started_at'
    
    def has_ai_summary(self, obj):
        """Check if session has AI summary."""
        return bool(obj.ai_summary)
    has_ai_summary.boolean = True
    has_ai_summary.short_description = 'AI Summary'
    
    fieldsets = (
        ('Session Info', {
            'fields': (
                'user',
                'repository',
                'started_at',
                'ended_at',
                'duration_minutes',
            )
        }),
        ('Statistics', {
            'fields': (
                'total_commits',
                'total_additions',
                'total_deletions',
                'files_changed',
            )
        }),
        ('Languages', {
            'fields': (
                'primary_language',
                'languages_used',
            )
        }),
        ('AI Summary', {
            'fields': (
                'ai_summary',
                'ai_generated_at',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
            )
        }),
    )
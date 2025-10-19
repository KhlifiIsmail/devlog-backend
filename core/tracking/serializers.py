"""Serializers for tracking app."""

from rest_framework import serializers
from .models import GitHubRepository, Commit, CodingSession


class GitHubRepositorySerializer(serializers.ModelSerializer):
    """Serializer for GitHub repositories."""
    
    total_commits = serializers.ReadOnlyField()
    total_sessions = serializers.ReadOnlyField()
    
    class Meta:
        model = GitHubRepository
        fields = [
            'id',
            'github_id',
            'name',
            'full_name',
            'description',
            'url',
            'default_branch',
            'is_private',
            'is_fork',
            'language',
            'stars_count',
            'forks_count',
            'is_tracking_enabled',
            'last_synced_at',
            'total_commits',
            'total_sessions',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'github_id',
            'created_at',
            'updated_at',
            'total_commits',
            'total_sessions',
        ]


class CommitSerializer(serializers.ModelSerializer):
    """Serializer for commits."""
    
    repository_name = serializers.CharField(
        source='repository.name',
        read_only=True
    )
    net_lines = serializers.ReadOnlyField()
    total_changes = serializers.ReadOnlyField()
    short_message = serializers.ReadOnlyField()
    
    class Meta:
        model = Commit
        fields = [
            'id',
            'sha',
            'message',
            'short_message',
            'author_name',
            'author_email',
            'committed_at',
            'additions',
            'deletions',
            'changed_files',
            'net_lines',
            'total_changes',
            'branch',
            'repository_name',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'net_lines',
            'total_changes',
            'short_message',
        ]


class CodingSessionListSerializer(serializers.ModelSerializer):
    """Serializer for session list view."""
    
    repository_name = serializers.CharField(
        source='repository.name',
        read_only=True
    )
    net_lines = serializers.ReadOnlyField()
    total_changes = serializers.ReadOnlyField()
    
    class Meta:
        model = CodingSession
        fields = [
            'id',
            'repository_name',
            'started_at',
            'ended_at',
            'duration_minutes',
            'total_commits',
            'total_additions',
            'total_deletions',
            'net_lines',
            'total_changes',
            'files_changed',
            'primary_language',
            'languages_used',
            'ai_summary',
            'ai_generated_at',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'net_lines',
            'total_changes',
            'created_at',
        ]


class CodingSessionDetailSerializer(serializers.ModelSerializer):
    """Serializer for session detail view with commits."""
    
    repository_name = serializers.CharField(
        source='repository.name',
        read_only=True
    )
    commits = CommitSerializer(many=True, read_only=True)
    net_lines = serializers.ReadOnlyField()
    total_changes = serializers.ReadOnlyField()
    
    class Meta:
        model = CodingSession
        fields = [
            'id',
            'repository_name',
            'started_at',
            'ended_at',
            'duration_minutes',
            'total_commits',
            'total_additions',
            'total_deletions',
            'net_lines',
            'total_changes',
            'files_changed',
            'primary_language',
            'languages_used',
            'ai_summary',
            'ai_generated_at',
            'commits',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'net_lines',
            'total_changes',
            'created_at',
            'updated_at',
        ]


class ToggleTrackingSerializer(serializers.Serializer):
    """Serializer for toggling repository tracking."""
    
    is_tracking_enabled = serializers.BooleanField()
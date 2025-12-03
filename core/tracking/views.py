"""Views for tracking app."""

import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.http import StreamingHttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse
import json
import time

from .models import GitHubRepository, Commit, CodingSession
from .serializers import (
    GitHubRepositorySerializer,
    CommitSerializer,
    CodingSessionListSerializer,
    CodingSessionDetailSerializer,
    ToggleTrackingSerializer,
)
from .services import GitHubService, SessionGrouper

logger = logging.getLogger(__name__)


# ==================== REPOSITORY VIEWS ====================

class RepositoryListView(APIView):
    """List all repositories for authenticated user."""
    
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses={200: GitHubRepositorySerializer(many=True)},
        tags=['Repositories']
    )
    def get(self, request):
        """List all user's repositories."""
        repositories = GitHubRepository.objects.filter(user=request.user)
        serializer = GitHubRepositorySerializer(repositories, many=True)
        return Response(serializer.data)


class RepositoryDetailView(APIView):
    """Get detailed view of a specific repository."""
    
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses={
            200: GitHubRepositorySerializer,
            404: OpenApiResponse(description='Repository not found')
        },
        tags=['Repositories']
    )
    def get(self, request, pk):
        """Get repository detail."""
        try:
            repository = GitHubRepository.objects.get(pk=pk, user=request.user)
            serializer = GitHubRepositorySerializer(repository)
            return Response(serializer.data)
        except GitHubRepository.DoesNotExist:
            return Response(
                {'error': 'Repository not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class RepositorySyncView(APIView):
    """Sync repositories from GitHub."""
    
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses={
            200: OpenApiResponse(description='Sync successful'),
            400: OpenApiResponse(description='Sync failed')
        },
        tags=['Repositories']
    )
    def post(self, request):
        """Sync user's repositories from GitHub API."""
        try:
            github_service = GitHubService(request.user.github_access_token)
            synced_count = github_service.sync_repositories(request.user)
            
            return Response({
                'message': f'Successfully synced {synced_count} repositories',
                'count': synced_count
            })
        except Exception as e:
            logger.error(f"Failed to sync repositories: {e}")
            return Response(
                {'error': 'Failed to sync repositories from GitHub'},
                status=status.HTTP_400_BAD_REQUEST
            )


class RepositoryToggleTrackingView(APIView):
    """Toggle tracking on/off for a repository."""
    
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        request=ToggleTrackingSerializer,
        responses={
            200: GitHubRepositorySerializer,
            400: OpenApiResponse(description='Invalid data'),
            404: OpenApiResponse(description='Repository not found')
        },
        tags=['Repositories']
    )
    def post(self, request, pk):
        """Toggle repository tracking."""
        try:
            repository = GitHubRepository.objects.get(pk=pk, user=request.user)
        except GitHubRepository.DoesNotExist:
            return Response(
                {'error': 'Repository not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ToggleTrackingSerializer(data=request.data)
        
        if serializer.is_valid():
            repository.is_tracking_enabled = serializer.validated_data['is_tracking_enabled']
            repository.save()
            
            return Response(GitHubRepositorySerializer(repository).data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ==================== COMMIT VIEWS ====================

class CommitListView(APIView):
    """List all commits for authenticated user."""
    
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses={200: CommitSerializer(many=True)},
        tags=['Commits']
    )
    def get(self, request):
        """List all user's commits."""
        commits = Commit.objects.filter(
            repository__user=request.user
        ).select_related('repository', 'session').order_by('-committed_at')
        
        serializer = CommitSerializer(commits, many=True)
        return Response(serializer.data)


class CommitDetailView(APIView):
    """Get detailed view of a specific commit."""
    
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses={
            200: CommitSerializer,
            404: OpenApiResponse(description='Commit not found')
        },
        tags=['Commits']
    )
    def get(self, request, pk):
        """Get commit detail."""
        try:
            commit = Commit.objects.select_related('repository', 'session').get(
                pk=pk,
                repository__user=request.user
            )
            serializer = CommitSerializer(commit)
            return Response(serializer.data)
        except Commit.DoesNotExist:
            return Response(
                {'error': 'Commit not found'},
                status=status.HTTP_404_NOT_FOUND
            )


# ==================== SESSION VIEWS ====================

class SessionListView(APIView):
    """List all coding sessions for authenticated user."""
    
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses={200: CodingSessionListSerializer(many=True)},
        tags=['Sessions']
    )
    def get(self, request):
        """List all user's coding sessions."""
        sessions = CodingSession.objects.filter(
            user=request.user
        ).select_related('repository').order_by('-started_at')
        
        serializer = CodingSessionListSerializer(sessions, many=True)
        return Response(serializer.data)


class SessionDetailView(APIView):
    """Get detailed view of a specific coding session with commits."""
    
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses={
            200: CodingSessionDetailSerializer,
            404: OpenApiResponse(description='Session not found')
        },
        tags=['Sessions']
    )
    def get(self, request, pk):
        """Get session detail with all commits."""
        try:
            session = CodingSession.objects.select_related('repository').prefetch_related('commits').get(
                pk=pk,
                user=request.user
            )
            serializer = CodingSessionDetailSerializer(session)
            return Response(serializer.data)
        except CodingSession.DoesNotExist:
            return Response(
                {'error': 'Session not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class SessionGroupView(APIView):
    """Group ungrouped commits into coding sessions."""
    
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses={
            200: OpenApiResponse(description='Grouping successful'),
            400: OpenApiResponse(description='Grouping failed')
        },
        tags=['Sessions']
    )
    def post(self, request):
        """Group ungrouped commits into sessions."""
        try:
            grouper = SessionGrouper(request.user)
            sessions_created = grouper.group_commits()
            
            return Response({
                'message': f'Successfully created {sessions_created} sessions',
                'count': sessions_created
            })
        except Exception as e:
            logger.error(f"Failed to group commits: {e}")
            return Response(
                {'error': 'Failed to group commits into sessions'},
                status=status.HTTP_400_BAD_REQUEST
            )


# ==================== AI NARRATIVE VIEWS ====================

class SessionNarrativeView(APIView):
    """Generate AI narrative for a coding session."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="generate_session_narrative",
        summary="Generate AI narrative for session",
        description="Generate a technical analysis narrative for a coding session using AI",
        responses={
            200: OpenApiResponse(
                description="AI narrative generated successfully",
                response={
                    'type': 'object',
                    'properties': {
                        'narrative': {'type': 'string'},
                        'generated_at': {'type': 'string'},
                        'model_used': {'type': 'string'},
                        'session_id': {'type': 'integer'},
                        'cached': {'type': 'boolean'}
                    }
                }
            ),
            404: OpenApiResponse(description="Session not found"),
            400: OpenApiResponse(description="Failed to generate narrative"),
            403: OpenApiResponse(description="Permission denied"),
        }
    )
    def post(self, request, session_id):
        """Generate or retrieve AI narrative for a session."""
        try:
            # Verify session exists and user has access
            session = CodingSession.objects.get(
                id=session_id,
                user=request.user
            )

            # Import AI service
            from core.ai.narrative import NarrativeService

            # Generate narrative
            narrative_service = NarrativeService()
            result = narrative_service.generate_session_narrative(session_id)

            # Check if it was cached
            from django.core.cache import cache
            cache_key = f"narrative_{session_id}"
            was_cached = cache.get(cache_key) is not None

            logger.info(f"Generated narrative for session {session_id} (cached: {was_cached})")

            return Response({
                'narrative': result['narrative'],
                'generated_at': result['generated_at'],
                'model_used': result['model_used'],
                'session_id': session_id,
                'cached': was_cached,
                'commit_count': result.get('commit_count', 0),
                'session_duration': result.get('session_duration', 0)
            })

        except CodingSession.DoesNotExist:
            return Response(
                {'error': 'Session not found or access denied'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError as e:
            logger.error(f"Invalid session data for narrative generation: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except RuntimeError as e:
            logger.error(f"AI service failed for session {session_id}: {e}")
            return Response(
                {'error': 'AI service temporarily unavailable'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            logger.error(f"Unexpected error generating narrative for session {session_id}: {e}")
            return Response(
                {'error': 'Failed to generate narrative'},
                status=status.HTTP_400_BAD_REQUEST
            )


class SessionSimilarityView(APIView):
    """Find similar coding sessions using vector embeddings."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="find_similar_sessions",
        summary="Find similar coding sessions",
        description="Find coding sessions similar to the given session using vector embeddings",
        responses={
            200: OpenApiResponse(
                description="Similar sessions found",
                response={
                    'type': 'object',
                    'properties': {
                        'similar_sessions': {
                            'type': 'array',
                            'items': {
                                'type': 'object',
                                'properties': {
                                    'session_id': {'type': 'integer'},
                                    'similarity_score': {'type': 'number'},
                                    'repository': {'type': 'string'},
                                    'duration_minutes': {'type': 'integer'},
                                    'total_commits': {'type': 'integer'},
                                    'primary_language': {'type': 'string'},
                                    'started_at': {'type': 'string'},
                                    'files_changed': {'type': 'integer'}
                                }
                            }
                        },
                        'session_id': {'type': 'integer'},
                        'count': {'type': 'integer'}
                    }
                }
            ),
            404: OpenApiResponse(description="Session not found"),
            400: OpenApiResponse(description="Failed to find similar sessions"),
        }
    )
    def get(self, request, session_id):
        """Find sessions similar to the given session."""
        try:
            # Verify session exists and user has access
            session = CodingSession.objects.get(
                id=session_id,
                user=request.user
            )

            # Import vector service
            from core.ai.embeddings import VectorStoreService

            # Get limit from query params (default 5, max 20)
            limit = min(int(request.GET.get('limit', 5)), 20)
            user_only = request.GET.get('user_only', 'true').lower() == 'true'

            # Find similar sessions
            vector_service = VectorStoreService()
            similar_sessions = vector_service.find_similar_sessions(
                session_id=session_id,
                limit=limit,
                user_only=user_only
            )

            logger.info(f"Found {len(similar_sessions)} similar sessions for session {session_id}")

            return Response({
                'similar_sessions': similar_sessions,
                'session_id': session_id,
                'count': len(similar_sessions),
                'user_only': user_only
            })

        except CodingSession.DoesNotExist:
            return Response(
                {'error': 'Session not found or access denied'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Failed to find similar sessions for {session_id}: {e}")
            return Response(
                {'error': 'Failed to find similar sessions'},
                status=status.HTTP_400_BAD_REQUEST
            )


# ==================== ACTIVITY FEED VIEWS ====================

class ActivityFeedView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: OpenApiResponse(description='Activity feed data'),
            400: OpenApiResponse(description='Bad request')
        },
        tags=['Activity']
    )
    def get(self, request):
        user = request.user
        now = timezone.now()

        # Get recent commits (last 7 days)
        recent_commits = Commit.objects.filter(
            repository__user=user,
            committed_at__gte=now - timedelta(days=7)
        ).select_related('repository', 'session').order_by('-committed_at')[:20]

        # Get recent sessions (last 7 days)
        recent_sessions = CodingSession.objects.filter(
            user=user,
            started_at__gte=now - timedelta(days=7)
        ).select_related('repository').order_by('-started_at')[:10]

        # Calculate today's activity
        today = now.date()
        today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))

        commits_today = Commit.objects.filter(
            repository__user=user,
            committed_at__gte=today_start
        ).count()

        sessions_today = CodingSession.objects.filter(
            user=user,
            started_at__gte=today_start
        )

        time_today = sum(session.duration_minutes for session in sessions_today)

        # Active repositories (repositories with commits in last 7 days)
        active_repos = GitHubRepository.objects.filter(
            user=user,
            commits__committed_at__gte=now - timedelta(days=7)
        ).distinct().count()

        # Calculate current streak (consecutive days with commits)
        current_streak = self._calculate_commit_streak(user)

        return Response({
            'recent_commits': CommitSerializer(recent_commits, many=True).data,
            'recent_sessions': CodingSessionListSerializer(recent_sessions, many=True).data,
            'activity_summary': {
                'total_commits_today': commits_today,
                'total_time_today': time_today,
                'active_repositories': active_repos,
                'current_streak': current_streak
            }
        })

    def _calculate_commit_streak(self, user):
        """Calculate consecutive days with commits."""
        streak = 0
        current_date = timezone.now().date()

        while True:
            day_start = timezone.make_aware(datetime.combine(current_date, datetime.min.time()))
            day_end = day_start + timedelta(days=1)

            commits_that_day = Commit.objects.filter(
                repository__user=user,
                committed_at__gte=day_start,
                committed_at__lt=day_end
            ).count()

            if commits_that_day > 0:
                streak += 1
                current_date -= timedelta(days=1)
            else:
                break

            # Prevent infinite loops
            if streak > 365:
                break

        return streak


class ActivityStreamView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Just return a simple message for now - fuck SSE
        return Response({
            'message': 'Real-time stream temporarily disabled. Use /api/v1/activity/ for updates.',
            'status': 'disabled'
        })


# ==================== INSIGHTS VIEWS ====================

class InsightListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: OpenApiResponse(description='User insights')},
        tags=['Insights']
    )
    def get(self, request):
        user = request.user
        insights = self._generate_basic_insights(user)
        return Response({'insights': insights})

    def _generate_basic_insights(self, user):
        """Generate basic insights from user data."""
        now = timezone.now()
        last_30_days = now - timedelta(days=30)

        # Get last 30 days data
        recent_sessions = CodingSession.objects.filter(
            user=user,
            started_at__gte=last_30_days
        )

        recent_commits = Commit.objects.filter(
            repository__user=user,
            committed_at__gte=last_30_days
        )

        insights = []

        # Productivity insight
        total_time = sum(session.duration_minutes for session in recent_sessions)
        avg_session_time = total_time / max(recent_sessions.count(), 1)

        insights.append({
            'id': 1,
            'title': 'Productivity Overview',
            'description': f'You\'ve coded for {total_time} minutes across {recent_sessions.count()} sessions in the last 30 days',
            'type': 'productivity',
            'generated_at': now.isoformat(),
            'data': {
                'total_time_minutes': total_time,
                'total_sessions': recent_sessions.count(),
                'average_session_time': round(avg_session_time, 1),
                'total_commits': recent_commits.count()
            }
        })

        # Language insight
        language_stats = {}
        for session in recent_sessions:
            if session.primary_language:
                lang = session.primary_language
                language_stats[lang] = language_stats.get(lang, 0) + session.duration_minutes

        if language_stats:
            top_language = max(language_stats, key=language_stats.get)
            insights.append({
                'id': 2,
                'title': 'Top Programming Language',
                'description': f'You spent the most time coding in {top_language} ({language_stats[top_language]} minutes)',
                'type': 'language',
                'generated_at': now.isoformat(),
                'data': {
                    'top_language': top_language,
                    'time_spent': language_stats[top_language],
                    'all_languages': language_stats
                }
            })

        # Repository activity insight
        repo_activity = {}
        for session in recent_sessions:
            if session.repository:
                repo = session.repository.name
                repo_activity[repo] = repo_activity.get(repo, 0) + 1

        if repo_activity:
            most_active_repo = max(repo_activity, key=repo_activity.get)
            insights.append({
                'id': 3,
                'title': 'Most Active Repository',
                'description': f'You had the most coding sessions in {most_active_repo} ({repo_activity[most_active_repo]} sessions)',
                'type': 'repository',
                'generated_at': now.isoformat(),
                'data': {
                    'most_active_repo': most_active_repo,
                    'session_count': repo_activity[most_active_repo],
                    'all_repos': repo_activity
                }
            })

        return insights


class GenerateWeeklySummaryView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: OpenApiResponse(description='Weekly summary generated')},
        tags=['Insights']
    )
    def post(self, request):
        user = request.user

        # Calculate current week bounds
        now = timezone.now()
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=7)

        # Get week's data
        week_sessions = CodingSession.objects.filter(
            user=user,
            started_at__gte=week_start,
            started_at__lt=week_end
        )

        week_commits = Commit.objects.filter(
            repository__user=user,
            committed_at__gte=week_start,
            committed_at__lt=week_end
        )

        # Calculate stats
        total_time = sum(session.duration_minutes for session in week_sessions)
        total_sessions = week_sessions.count()
        total_commits = week_commits.count()
        repositories = week_sessions.values('repository').distinct().count()

        # Generate simple summary (could be enhanced with AI later)
        summary = f"This week you completed {total_sessions} coding sessions across {repositories} repositories, " \
                 f"making {total_commits} commits in {total_time} minutes of coding time."

        return Response({
            'summary': summary,
            'week_start': week_start.isoformat(),
            'week_end': week_end.isoformat(),
            'stats': {
                'total_sessions': total_sessions,
                'total_commits': total_commits,
                'total_time': total_time,
                'repositories': repositories
            },
            'generated_at': now.isoformat()
        })


class WeeklyInsightsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: OpenApiResponse(description='Weekly insights')},
        tags=['Insights']
    )
    def get(self, request):
        user = request.user
        now = timezone.now()

        # Current week
        current_week_start = now - timedelta(days=now.weekday())
        current_week_start = current_week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        current_week_end = current_week_start + timedelta(days=7)

        # Previous week
        previous_week_start = current_week_start - timedelta(days=7)
        previous_week_end = current_week_start

        # Get data for both weeks
        current_week_data = self._get_week_stats(user, current_week_start, current_week_end)
        previous_week_data = self._get_week_stats(user, previous_week_start, previous_week_end)

        # Calculate trends
        trends = {}
        for key in ['sessions', 'commits', 'time']:
            current = current_week_data.get(key, 0)
            previous = previous_week_data.get(key, 0)
            if previous > 0:
                change = ((current - previous) / previous) * 100
                trends[f'{key}_change_percent'] = round(change, 1)
            else:
                trends[f'{key}_change_percent'] = 0

        return Response({
            'current_week': {
                **current_week_data,
                'week_start': current_week_start.isoformat(),
                'week_end': current_week_end.isoformat()
            },
            'previous_week': {
                **previous_week_data,
                'week_start': previous_week_start.isoformat(),
                'week_end': previous_week_end.isoformat()
            },
            'trends': trends
        })

    def _get_week_stats(self, user, start, end):
        """Get stats for a specific week."""
        sessions = CodingSession.objects.filter(
            user=user,
            started_at__gte=start,
            started_at__lt=end
        )

        commits = Commit.objects.filter(
            repository__user=user,
            committed_at__gte=start,
            committed_at__lt=end
        )

        return {
            'sessions': sessions.count(),
            'commits': commits.count(),
            'time': sum(session.duration_minutes for session in sessions),
            'repositories': sessions.values('repository').distinct().count()
        }


# ==================== PATTERNS VIEWS ====================

class PatternListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: OpenApiResponse(description='Coding patterns')},
        tags=['Patterns']
    )
    def get(self, request):
        user = request.user
        patterns = []

        # Time-based patterns
        time_pattern = self._analyze_time_patterns(user)
        if time_pattern:
            patterns.append(time_pattern)

        # Language patterns
        language_pattern = self._analyze_language_patterns(user)
        if language_pattern:
            patterns.append(language_pattern)

        # Session length patterns
        session_pattern = self._analyze_session_patterns(user)
        if session_pattern:
            patterns.append(session_pattern)

        # Commit frequency patterns
        commit_pattern = self._analyze_commit_patterns(user)
        if commit_pattern:
            patterns.append(commit_pattern)

        return Response({'patterns': patterns})

    def _analyze_time_patterns(self, user):
        """Analyze when user codes most."""
        sessions = CodingSession.objects.filter(user=user)

        if not sessions.exists():
            return None

        # Count sessions by hour of day
        hour_counts = {}
        for session in sessions:
            hour = session.started_at.hour
            hour_counts[hour] = hour_counts.get(hour, 0) + 1

        if not hour_counts:
            return None

        peak_hour = max(hour_counts, key=hour_counts.get)
        peak_count = hour_counts[peak_hour]

        # Determine time of day
        if 5 <= peak_hour < 12:
            time_period = "morning"
        elif 12 <= peak_hour < 17:
            time_period = "afternoon"
        elif 17 <= peak_hour < 21:
            time_period = "evening"
        else:
            time_period = "night"

        return {
            'type': 'time_preference',
            'title': f'Peak Coding Time: {time_period.title()}',
            'description': f'You code most frequently at {peak_hour}:00, with {peak_count} sessions started during this hour',
            'data': {
                'peak_hour': peak_hour,
                'peak_count': peak_count,
                'time_period': time_period,
                'hour_distribution': hour_counts
            }
        }

    def _analyze_language_patterns(self, user):
        """Analyze language usage patterns."""
        sessions = CodingSession.objects.filter(
            user=user,
            primary_language__isnull=False
        )

        if not sessions.exists():
            return None

        language_time = {}
        for session in sessions:
            lang = session.primary_language
            language_time[lang] = language_time.get(lang, 0) + session.duration_minutes

        if not language_time:
            return None

        favorite_language = max(language_time, key=language_time.get)
        favorite_time = language_time[favorite_language]
        total_time = sum(language_time.values())
        percentage = (favorite_time / total_time) * 100

        return {
            'type': 'language_preference',
            'title': f'Favorite Language: {favorite_language}',
            'description': f'You spend {percentage:.1f}% of your coding time using {favorite_language} ({favorite_time} minutes total)',
            'data': {
                'favorite_language': favorite_language,
                'time_spent': favorite_time,
                'percentage': round(percentage, 1),
                'language_distribution': language_time
            }
        }

    def _analyze_session_patterns(self, user):
        """Analyze session length patterns."""
        sessions = CodingSession.objects.filter(user=user)

        if not sessions.exists():
            return None

        durations = [session.duration_minutes for session in sessions]
        avg_duration = sum(durations) / len(durations)

        # Categorize session lengths
        short_sessions = len([d for d in durations if d < 30])
        medium_sessions = len([d for d in durations if 30 <= d <= 120])
        long_sessions = len([d for d in durations if d > 120])

        total_sessions = len(durations)

        if medium_sessions >= short_sessions and medium_sessions >= long_sessions:
            pattern = "balanced"
            description = "You tend to have balanced coding sessions, typically lasting 30-120 minutes"
        elif short_sessions > medium_sessions and short_sessions > long_sessions:
            pattern = "short_bursts"
            description = "You prefer short coding sessions, usually under 30 minutes"
        else:
            pattern = "long_sessions"
            description = "You prefer longer coding sessions, often over 2 hours"

        return {
            'type': 'session_length',
            'title': f'Session Style: {pattern.replace("_", " ").title()}',
            'description': description,
            'data': {
                'pattern': pattern,
                'average_duration': round(avg_duration, 1),
                'short_sessions': short_sessions,
                'medium_sessions': medium_sessions,
                'long_sessions': long_sessions,
                'total_sessions': total_sessions
            }
        }

    def _analyze_commit_patterns(self, user):
        """Analyze commit frequency patterns."""
        commits = Commit.objects.filter(repository__user=user)

        if not commits.exists():
            return None

        # Group commits by day
        daily_commits = {}
        for commit in commits:
            date = commit.committed_at.date()
            daily_commits[date] = daily_commits.get(date, 0) + 1

        if not daily_commits:
            return None

        # Calculate average commits per day
        avg_commits = sum(daily_commits.values()) / len(daily_commits)

        # Find most productive day
        max_commits = max(daily_commits.values())
        most_productive_day = None
        for date, count in daily_commits.items():
            if count == max_commits:
                most_productive_day = date
                break

        return {
            'type': 'commit_frequency',
            'title': f'Average Commits: {avg_commits:.1f} per day',
            'description': f'Your most productive day was {most_productive_day} with {max_commits} commits',
            'data': {
                'average_commits_per_day': round(avg_commits, 1),
                'max_commits_in_day': max_commits,
                'most_productive_day': most_productive_day.isoformat() if most_productive_day else None,
                'total_commit_days': len(daily_commits),
                'total_commits': commits.count()
            }
        }
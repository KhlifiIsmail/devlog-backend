"""Views for tracking app."""

import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse

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
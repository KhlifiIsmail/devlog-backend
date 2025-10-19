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
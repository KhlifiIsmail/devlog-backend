"""URL configuration for tracking app."""

from django.urls import path
from .views import (
    RepositoryListView,
    RepositoryDetailView,
    RepositorySyncView,
    RepositoryToggleTrackingView,
    CommitListView,
    CommitDetailView,
    SessionListView,
    SessionDetailView,
    SessionGroupView,
    SessionNarrativeView,
    SessionSimilarityView,
)

app_name = 'tracking'

urlpatterns = [
    # Repositories
    path('repositories/', RepositoryListView.as_view(), name='repository-list'),
    path('repositories/<int:pk>/', RepositoryDetailView.as_view(), name='repository-detail'),
    path('repositories/sync/', RepositorySyncView.as_view(), name='repository-sync'),
    path('repositories/<int:pk>/toggle-tracking/', RepositoryToggleTrackingView.as_view(), name='repository-toggle-tracking'),
    
    # Commits
    path('commits/', CommitListView.as_view(), name='commit-list'),
    path('commits/<int:pk>/', CommitDetailView.as_view(), name='commit-detail'),
    
    # Sessions
    path('sessions/', SessionListView.as_view(), name='session-list'),
    path('sessions/<int:pk>/', SessionDetailView.as_view(), name='session-detail'),
    path('sessions/group/', SessionGroupView.as_view(), name='session-group'),

    # AI Features
    path('sessions/<int:session_id>/generate-narrative/', SessionNarrativeView.as_view(), name='session-narrative'),
    path('sessions/<int:session_id>/similar/', SessionSimilarityView.as_view(), name='session-similarity'),
]
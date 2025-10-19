"""URL configuration for webhooks app."""

from django.urls import path
from .views import (
    GitHubWebhookView,
    WebhookEventListView,
    WebhookEventDetailView,
)

app_name = 'webhooks'

urlpatterns = [
    path('webhooks/github/', GitHubWebhookView.as_view(), name='github-webhook'),
    path('webhooks/events/', WebhookEventListView.as_view(), name='webhook-event-list'),
    path('webhooks/events/<int:pk>/', WebhookEventDetailView.as_view(), name='webhook-event-detail'),
]
"""Views for webhooks app."""

import logging
import json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import WebhookEvent
from .utils import verify_github_signature, extract_event_type
from .tasks import process_push_event

logger = logging.getLogger(__name__)


@extend_schema(tags=['Webhooks'], exclude=True)
@method_decorator(csrf_exempt, name='dispatch')
class GitHubWebhookView(APIView):
    """
    Receive GitHub webhook events and queue for processing.
    
    Endpoint: POST /api/v1/webhooks/github/
    
    Headers required:
    - X-GitHub-Event: Event type (push, pull_request, etc.)
    - X-Hub-Signature-256: HMAC SHA256 signature
    - X-GitHub-Delivery: Unique delivery ID
    """
    
    authentication_classes = []  # No auth for webhooks
    permission_classes = []
    
    @extend_schema(
        responses={
            202: OpenApiResponse(description='Webhook received'),
            403: OpenApiResponse(description='Invalid signature'),
            400: OpenApiResponse(description='Invalid payload'),
        }
    )
    def post(self, request):
        """Handle incoming GitHub webhook."""
        # Extract headers
        event_type_header = request.headers.get('X-GitHub-Event', '')
        signature = request.headers.get('X-Hub-Signature-256', '')
        delivery_id = request.headers.get('X-GitHub-Delivery', '')
        
        logger.info(f"Received webhook: {event_type_header} - {delivery_id}")
        
        # Verify signature
        if not self._verify_signature(request.body, signature):
            logger.warning(f"Invalid signature for delivery {delivery_id}")
            return Response(
                {'error': 'Invalid signature'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Parse payload
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON payload for delivery {delivery_id}")
            return Response(
                {'error': 'Invalid JSON payload'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Handle ping event
        if event_type_header == 'ping':
            logger.info(f"Ping event received: {delivery_id}")
            return Response({'message': 'pong'}, status=status.HTTP_200_OK)
        
        # Create webhook event record
        event_type = extract_event_type(event_type_header)
        repo_full_name = payload.get('repository', {}).get('full_name', 'unknown')
        
        webhook_event = WebhookEvent.objects.create(
            event_type=event_type,
            repository_full_name=repo_full_name,
            delivery_id=delivery_id,
            payload=payload,
            status='pending',
        )
        
        logger.info(f"Created webhook event {webhook_event.id}")
        
        # Queue for async processing
        if event_type == 'push':
            process_push_event.delay(webhook_event.id)
            logger.info(f"Queued push event {webhook_event.id} for processing")
        else:
            logger.info(f"Event type {event_type} not processed yet")
            webhook_event.mark_completed()
        
        return Response(
            {'status': 'received', 'event_id': webhook_event.id},
            status=status.HTTP_202_ACCEPTED
        )
    
    def _verify_signature(self, payload_body: bytes, signature: str) -> bool:
        """Verify GitHub webhook signature."""
        webhook_secret = settings.GITHUB_WEBHOOK_SECRET
        
        if not webhook_secret:
            logger.error("GITHUB_WEBHOOK_SECRET not configured")
            return False
        
        return verify_github_signature(payload_body, signature, webhook_secret)


@extend_schema(tags=['Webhooks'])
class WebhookEventListView(APIView):
    """
    List webhook events for debugging.
    
    GET /api/v1/webhooks/events/
    """
    
    @extend_schema(
        responses={200: OpenApiResponse(description='List of webhook events')}
    )
    def get(self, request):
        """Get recent webhook events."""
        from .serializers import WebhookEventSerializer
        
        events = WebhookEvent.objects.all()[:50]
        serializer = WebhookEventSerializer(events, many=True)
        
        return Response(serializer.data)


@extend_schema(tags=['Webhooks'])
class WebhookEventDetailView(APIView):
    """
    Get detailed view of a specific webhook event.
    
    GET /api/v1/webhooks/events/<id>/
    """
    
    @extend_schema(
        responses={
            200: OpenApiResponse(description='Webhook event detail'),
            404: OpenApiResponse(description='Webhook event not found')
        }
    )
    def get(self, request, pk):
        """Get webhook event detail."""
        from .serializers import WebhookEventDetailSerializer
        
        try:
            event = WebhookEvent.objects.get(pk=pk)
            serializer = WebhookEventDetailSerializer(event)
            return Response(serializer.data)
        except WebhookEvent.DoesNotExist:
            return Response(
                {'error': 'Webhook event not found'},
                status=status.HTTP_404_NOT_FOUND
            )
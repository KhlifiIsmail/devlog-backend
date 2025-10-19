import logging
from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.db import transaction

from .models import WebhookEvent
from .services import WebhookProcessor

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name='webhooks.process_push_event',
    max_retries=3,
    default_retry_delay=60,  # 1 minute
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,  # 10 minutes
    retry_jitter=True,
)
def process_push_event(self, webhook_event_id: int):
    """
    Process a GitHub push event asynchronously.
    
    Args:
        webhook_event_id: ID of WebhookEvent to process
    
    Raises:
        WebhookEvent.DoesNotExist: If event not found
        Exception: For processing errors (triggers retry)
    """
    logger.info(f"Processing push event {webhook_event_id}")
    
    try:
        # Get webhook event
        webhook_event = WebhookEvent.objects.get(id=webhook_event_id)
        
        # Process event
        processor = WebhookProcessor(webhook_event)
        result = processor.process_push_event()
        
        logger.info(f"Push event {webhook_event_id} processed successfully: {result}")
        return result
    
    except WebhookEvent.DoesNotExist:
        logger.error(f"WebhookEvent {webhook_event_id} not found")
        raise
    
    except SoftTimeLimitExceeded:
        logger.error(f"Push event {webhook_event_id} timed out")
        try:
            webhook_event = WebhookEvent.objects.get(id=webhook_event_id)
            webhook_event.mark_failed("Task timed out")
        except WebhookEvent.DoesNotExist:
            pass
        raise
    
    except Exception as e:
        logger.error(f"Error processing push event {webhook_event_id}: {str(e)}")
        
        # Mark as failed if max retries exceeded
        if self.request.retries >= self.max_retries:
            try:
                webhook_event = WebhookEvent.objects.get(id=webhook_event_id)
                webhook_event.mark_failed(f"Max retries exceeded: {str(e)}")
            except WebhookEvent.DoesNotExist:
                pass
        
        raise
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class WebhookEvent(models.Model):
    """
    Log all incoming webhook events for debugging and replay.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    EVENT_TYPES = [
        ('push', 'Push'),
        ('pull_request', 'Pull Request'),
        ('ping', 'Ping'),
        ('other', 'Other'),
    ]
    
    id = models.AutoField(primary_key=True)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES, db_index=True)
    repository_full_name = models.CharField(max_length=255, db_index=True)
    delivery_id = models.CharField(max_length=255, unique=True, db_index=True)
    
    payload = models.JSONField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    error_message = models.TextField(blank=True, null=True)
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='webhook_events',
        null=True,
        blank=True,
        help_text="User who owns the repository (resolved during processing)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'webhook_events'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at', 'status']),
            models.Index(fields=['repository_full_name', '-created_at']),
        ]
    
    def __str__(self) -> str:
        return f"{self.event_type} - {self.repository_full_name} - {self.status}"
    
    def mark_processing(self) -> None:
        """Mark event as currently being processed."""
        self.status = 'processing'
        self.save(update_fields=['status', 'updated_at'])
    
    def mark_completed(self) -> None:
        """Mark event as successfully completed."""
        from django.utils import timezone
        self.status = 'completed'
        self.processed_at = timezone.now()
        self.save(update_fields=['status', 'processed_at', 'updated_at'])
    
    def mark_failed(self, error: str) -> None:
        """Mark event as failed with error message."""
        from django.utils import timezone
        self.status = 'failed'
        self.error_message = error
        self.processed_at = timezone.now()
        self.save(update_fields=['status', 'error_message', 'processed_at', 'updated_at'])
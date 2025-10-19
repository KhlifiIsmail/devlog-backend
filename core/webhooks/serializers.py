from rest_framework import serializers
from .models import WebhookEvent


class WebhookEventSerializer(serializers.ModelSerializer):
    """Serializer for WebhookEvent model."""
    
    class Meta:
        model = WebhookEvent
        fields = [
            'id',
            'event_type',
            'repository_full_name',
            'delivery_id',
            'status',
            'error_message',
            'created_at',
            'updated_at',
            'processed_at',
        ]
        read_only_fields = fields


class WebhookEventDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer including payload."""
    
    class Meta:
        model = WebhookEvent
        fields = [
            'id',
            'event_type',
            'repository_full_name',
            'delivery_id',
            'payload',
            'status',
            'error_message',
            'user',
            'created_at',
            'updated_at',
            'processed_at',
        ]
        read_only_fields = fields
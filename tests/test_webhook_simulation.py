"""
Test webhook endpoint with simulated GitHub events.
"""
import pytest
import json
import hmac
import hashlib
from django.test import Client
from django.contrib.auth import get_user_model
from core.webhooks.models import WebhookEvent

User = get_user_model()


@pytest.mark.django_db
class TestWebhookEndpoint:
    
    def setup_method(self):
        """Setup test client and user."""
        self.client = Client()
        self.webhook_url = '/api/v1/webhooks/github/'
    
    def _generate_signature(self, payload_bytes, secret):
        """Generate GitHub webhook signature."""
        return 'sha256=' + hmac.new(
            secret.encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
    
    def test_ping_event(self, webhook_secret):
        """Test ping event returns pong."""
        payload = {"zen": "Design for failure.", "hook_id": 12345}
        payload_bytes = json.dumps(payload).encode('utf-8')
        signature = self._generate_signature(payload_bytes, webhook_secret)
        
        response = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type='application/json',
            HTTP_X_GITHUB_EVENT='ping',
            HTTP_X_HUB_SIGNATURE_256=signature,
            HTTP_X_GITHUB_DELIVERY='test-delivery-ping'
        )
        
        assert response.status_code == 200
        assert response.json()['message'] == 'pong'
    
    def test_push_event_creates_webhook_record(self, sample_push_payload, webhook_secret):
        """Test push event creates WebhookEvent record."""
        payload_bytes = json.dumps(sample_push_payload).encode('utf-8')
        signature = self._generate_signature(payload_bytes, webhook_secret)
        
        response = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type='application/json',
            HTTP_X_GITHUB_EVENT='push',
            HTTP_X_HUB_SIGNATURE_256=signature,
            HTTP_X_GITHUB_DELIVERY='test-delivery-push-123'
        )
        
        assert response.status_code == 202
        assert 'event_id' in response.json()
        
        # Check WebhookEvent was created
        event = WebhookEvent.objects.get(delivery_id='test-delivery-push-123')
        assert event.event_type == 'push'
        assert event.repository_full_name == 'testuser/devlog-test'
        assert event.status == 'pending'
    
    def test_invalid_signature_rejected(self, sample_push_payload):
        """Test invalid signature is rejected."""
        payload_bytes = json.dumps(sample_push_payload).encode('utf-8')
        
        response = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type='application/json',
            HTTP_X_GITHUB_EVENT='push',
            HTTP_X_HUB_SIGNATURE_256='sha256=invalid_signature',
            HTTP_X_GITHUB_DELIVERY='test-delivery-invalid'
        )
        
        assert response.status_code == 403
        assert 'Invalid signature' in response.json()['error']
    
    def test_invalid_json_rejected(self, webhook_secret):
        """Test invalid JSON payload is rejected."""
        payload_bytes = b'not valid json {]'
        signature = self._generate_signature(payload_bytes, webhook_secret)
        
        response = self.client.post(
            self.webhook_url,
            data=payload_bytes,
            content_type='application/json',
            HTTP_X_GITHUB_EVENT='push',
            HTTP_X_HUB_SIGNATURE_256=signature,
            HTTP_X_GITHUB_DELIVERY='test-delivery-bad-json'
        )
        
        assert response.status_code == 400
        assert 'Invalid JSON' in response.json()['error']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
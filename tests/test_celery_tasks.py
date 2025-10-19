"""
Test Celery tasks for webhook processing.
"""
import pytest
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from core.webhooks.models import WebhookEvent
from core.webhooks.tasks import process_push_event
from core.tracking.models import GitHubRepository, Commit

User = get_user_model()


@pytest.mark.django_db
class TestCeleryTasks:
    
    def setup_method(self):
        """Setup test data."""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            github_username='testuser'
        )
    
    def test_process_push_event_creates_commits(self, sample_push_payload):
        """Test processing push event creates commits."""
        # Create webhook event
        webhook_event = WebhookEvent.objects.create(
            event_type='push',
            repository_full_name='testuser/devlog-test',
            delivery_id='test-123',
            payload=sample_push_payload,
            status='pending'
        )
        
        # Process event (synchronously for testing)
        result = process_push_event(webhook_event.id)
        
        # Check webhook event status
        webhook_event.refresh_from_db()
        assert webhook_event.status == 'completed'
        
        # Check repository was created
        repo = GitHubRepository.objects.get(full_name='testuser/devlog-test')
        assert repo.name == 'devlog-test'
        assert repo.user == self.user  # FIX: Check user, not owner
        assert repo.full_name == 'testuser/devlog-test'  # This covers the owner info
        
        # Check commits were created
        assert Commit.objects.filter(repository=repo).count() == 2
        
        # Check result
        assert result['commits_created'] == 2
        assert result['repository'] == 'testuser/devlog-test'
    def test_process_push_event_handles_duplicate_commits(self, sample_push_payload):
        """Test that duplicate commits are not created."""
        # Create webhook event
        webhook_event = WebhookEvent.objects.create(
            event_type='push',
            repository_full_name='testuser/devlog-test',
            delivery_id='test-456',
            payload=sample_push_payload,
            status='pending'
        )
        
        # Process event first time
        result1 = process_push_event(webhook_event.id)
        assert result1['commits_created'] == 2
        
        # Create another webhook event with same commits
        webhook_event2 = WebhookEvent.objects.create(
            event_type='push',
            repository_full_name='testuser/devlog-test',
            delivery_id='test-789',
            payload=sample_push_payload,
            status='pending'
        )
        
        # Process event second time
        result2 = process_push_event(webhook_event2.id)
        
        # Should not create duplicate commits
        assert result2['commits_created'] == 0
        
        # Total commits should still be 2
        repo = GitHubRepository.objects.get(full_name='testuser/devlog-test')
        assert Commit.objects.filter(repository=repo).count() == 2
    
    def test_process_push_event_with_no_commits(self):
        """Test processing push event with no commits."""
        payload = {
            "ref": "refs/heads/main",
            "repository": {
                "full_name": "testuser/empty-push"
            },
            "commits": []
        }
        
        webhook_event = WebhookEvent.objects.create(
            event_type='push',
            repository_full_name='testuser/empty-push',
            delivery_id='test-empty',
            payload=payload,
            status='pending'
        )
        
        result = process_push_event(webhook_event.id)
        
        webhook_event.refresh_from_db()
        assert webhook_event.status == 'completed'
        assert result['commits_created'] == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
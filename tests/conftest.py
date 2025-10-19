"""
Pytest configuration and fixtures for webhook tests.
"""
import pytest
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'devlog.settings')

# Setup Django
import django
django.setup()


@pytest.fixture
def sample_push_payload():
    """Sample GitHub push event payload."""
    return {
        "ref": "refs/heads/main",
        "repository": {
            "id": 123456789,
            "name": "devlog-test",
            "full_name": "testuser/devlog-test",
            "owner": {
                "login": "testuser",
                "id": 12345
            },
            "html_url": "https://github.com/testuser/devlog-test",
            "description": "Test repository for DevLog",
            "private": False,
            "language": "Python"
        },
        "pusher": {
            "name": "testuser",
            "email": "test@example.com"
        },
        "sender": {
            "login": "testuser",
            "id": 12345
        },
        "commits": [
            {
                "id": "abc123def456ghi789",
                "message": "Fix bug in authentication",
                "timestamp": "2025-01-15T10:00:00Z",
                "url": "https://github.com/testuser/devlog-test/commit/abc123",
                "author": {
                    "name": "Test User",
                    "email": "test@example.com",
                    "username": "testuser"
                },
                "committer": {
                    "name": "Test User",
                    "email": "test@example.com",
                    "username": "testuser"
                },
                "added": ["new_file.py"],
                "removed": [],
                "modified": ["existing_file.py"]
            },
            {
                "id": "def456ghi789jkl012",
                "message": "Add new feature",
                "timestamp": "2025-01-15T10:15:00Z",
                "url": "https://github.com/testuser/devlog-test/commit/def456",
                "author": {
                    "name": "Test User",
                    "email": "test@example.com",
                    "username": "testuser"
                },
                "committer": {
                    "name": "Test User",
                    "email": "test@example.com",
                    "username": "testuser"
                },
                "added": ["feature.py"],
                "removed": [],
                "modified": ["main.py"]
            }
        ]
    }


@pytest.fixture
def webhook_secret():
    """Get webhook secret from environment."""
    from django.conf import settings
    return settings.GITHUB_WEBHOOK_SECRET or "test_secret_key_123"
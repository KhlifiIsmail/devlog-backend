#!/usr/bin/env python
"""
Simulate a GitHub webhook push to test webhook processing
"""
import os
import sys
import django
import json
from datetime import datetime, timezone

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'devlog.settings')
django.setup()

from core.webhooks.models import WebhookEvent
from core.webhooks.services import WebhookProcessor
from core.accounts.models import User
from core.tracking.models import GitHubRepository

def simulate_push_webhook():
    """Simulate a GitHub push webhook"""
    try:
        # Get user and repository
        user = User.objects.first()
        if not user:
            print("ERROR: No users found")
            return

        repo = GitHubRepository.objects.filter(user=user).first()
        if not repo:
            print("ERROR: No repositories found")
            return

        print(f"Simulating webhook for user: {user.github_username}")
        print(f"Repository: {repo.full_name}")

        # Create a fake webhook payload (similar to GitHub's format)
        webhook_payload = {
            "ref": "refs/heads/main",
            "before": "abc123def456789",
            "after": "def456ghi789abc",
            "created": False,
            "deleted": False,
            "forced": False,
            "base_ref": None,
            "compare": f"https://github.com/{repo.full_name}/compare/abc123def456789...def456ghi789abc",
            "commits": [
                {
                    "id": f"def456ghi789abc{datetime.now().microsecond}",
                    "tree_id": "tree123456789",
                    "distinct": True,
                    "message": "Test commit from webhook simulation",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "url": f"https://github.com/{repo.full_name}/commit/def456ghi789abc",
                    "author": {
                        "name": user.github_username,
                        "email": user.email or f"{user.github_username}@example.com",
                        "username": user.github_username
                    },
                    "committer": {
                        "name": user.github_username,
                        "email": user.email or f"{user.github_username}@example.com",
                        "username": user.github_username
                    },
                    "added": ["new_file.py"],
                    "removed": [],
                    "modified": ["existing_file.py"]
                }
            ],
            "head_commit": {
                "id": f"def456ghi789abc{datetime.now().microsecond}",
                "tree_id": "tree123456789",
                "distinct": True,
                "message": "Test commit from webhook simulation",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "url": f"https://github.com/{repo.full_name}/commit/def456ghi789abc",
                "author": {
                    "name": user.github_username,
                    "email": user.email or f"{user.github_username}@example.com",
                    "username": user.github_username
                },
                "committer": {
                    "name": user.github_username,
                    "email": user.email or f"{user.github_username}@example.com",
                    "username": user.github_username
                },
                "added": ["new_file.py"],
                "removed": [],
                "modified": ["existing_file.py"]
            },
            "repository": {
                "id": repo.github_id,
                "name": repo.name,
                "full_name": repo.full_name,
                "private": repo.is_private,
                "owner": {
                    "name": user.github_username,
                    "email": user.email or f"{user.github_username}@example.com",
                    "login": user.github_username,
                    "id": user.github_id,
                    "avatar_url": user.github_avatar_url or "",
                    "type": "User"
                },
                "html_url": repo.url,
                "clone_url": f"{repo.url}.git",
                "default_branch": repo.default_branch
            },
            "pusher": {
                "name": user.github_username,
                "email": user.email or f"{user.github_username}@example.com"
            },
            "sender": {
                "login": user.github_username,
                "id": user.github_id,
                "avatar_url": user.github_avatar_url or "",
                "type": "User"
            }
        }

        # Create webhook event
        webhook_event = WebhookEvent.objects.create(
            event_type='push',
            repository_full_name=repo.full_name,
            delivery_id=f"sim-{datetime.now().timestamp()}",
            payload=webhook_payload,
            status='pending'
        )

        print(f"Created webhook event: {webhook_event.id}")

        # Process the webhook directly (instead of using Celery)
        print("Processing webhook...")
        processor = WebhookProcessor(webhook_event)
        result = processor.process_push_event()

        print(f"Webhook processed successfully!")
        print(f"Result: {result}")

        # Check if commits were created
        from core.tracking.models import Commit
        new_commits = Commit.objects.filter(repository=repo).order_by('-created_at')[:5]

        print(f"\nRecent commits in {repo.name}:")
        for commit in new_commits:
            print(f"  - {commit.sha[:8]}: {commit.message[:50]}...")

        print(f"\nNow test /api/v1/activity/ - it should show the new commit!")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    simulate_push_webhook()
"""
Simulate a GitHub push webhook event for testing.
"""
import requests
import json
import hmac
import hashlib
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Configuration
WEBHOOK_URL = "http://localhost:8000/api/v1/webhooks/github/"
WEBHOOK_SECRET = os.getenv('GITHUB_WEBHOOK_SECRET', 'test_secret_123')

# Sample push payload
payload = {
    "ref": "refs/heads/main",
    "repository": {
        "id": 123456789,
        "name": "devlog-test",
        "full_name": "yourusername/devlog-test",
        "owner": {
            "login": "yourusername",
            "id": 12345
        },
        "html_url": "https://github.com/yourusername/devlog-test",
        "description": "Test repository for DevLog",
        "private": False,
        "language": "Python"
    },
    "pusher": {
        "name": "yourusername",
        "email": "your@email.com"
    },
    "commits": [
        {
            "id": f"abc{datetime.now().timestamp()}",
            "message": "Test commit - Fix authentication bug",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "url": "https://github.com/yourusername/devlog-test/commit/abc123",
            "author": {
                "name": "Your Name",
                "email": "your@email.com",
                "username": "yourusername"
            },
            "committer": {
                "name": "Your Name",
                "email": "your@email.com",
                "username": "yourusername"
            },
            "added": ["auth/fix.py"],
            "removed": [],
            "modified": ["auth/views.py"]
        },
        {
            "id": f"def{datetime.now().timestamp()}",
            "message": "Test commit - Add new feature",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "url": "https://github.com/yourusername/devlog-test/commit/def456",
            "author": {
                "name": "Your Name",
                "email": "your@email.com",
                "username": "yourusername"
            },
            "committer": {
                "name": "Your Name",
                "email": "your@email.com",
                "username": "yourusername"
            },
            "added": ["features/new_feature.py"],
            "removed": [],
            "modified": ["main.py", "config.py"]
        }
    ]
}


def generate_signature(payload_bytes, secret):
    """Generate GitHub webhook signature."""
    return 'sha256=' + hmac.new(
        secret.encode('utf-8'),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()


def send_webhook():
    """Send simulated webhook to Django."""
    payload_bytes = json.dumps(payload).encode('utf-8')
    signature = generate_signature(payload_bytes, WEBHOOK_SECRET)
    
    headers = {
        'Content-Type': 'application/json',
        'X-GitHub-Event': 'push',
        'X-Hub-Signature-256': signature,
        'X-GitHub-Delivery': f'test-delivery-{datetime.now().timestamp()}'
    }
    
    print("🚀 Sending webhook to:", WEBHOOK_URL)
    print("📦 Payload contains", len(payload['commits']), "commits")
    print("🔐 Signature:", signature[:50] + "...")
    
    try:
        response = requests.post(
            WEBHOOK_URL,
            data=payload_bytes,
            headers=headers,
            timeout=10
        )
        
        print(f"\n✅ Status: {response.status_code}")
        print(f"📄 Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 202:
            print("\n🎉 Webhook accepted! Check your Celery worker terminal for processing logs.")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to Django server.")
        print("   Make sure Django is running: python manage.py runserver")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == '__main__':
    send_webhook()
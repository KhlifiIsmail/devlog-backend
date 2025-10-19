"""
Test Celery worker connection.
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'devlog.settings')

import django
django.setup()

from celery import Celery
from devlog.celery import app

print("🔍 Testing Celery worker...")
print(f"📍 Broker URL: {app.conf.broker_url}")
print(f"📍 Result backend: {app.conf.result_backend}")

try:
    # Test Celery connection
    inspector = app.control.inspect()
    
    # Check active workers
    active = inspector.active()
    if active:
        print(f"✅ Active workers: {list(active.keys())}")
        for worker, tasks in active.items():
            print(f"   - {worker}: {len(tasks)} active tasks")
    else:
        print("⚠️  No active workers found")
        print("   Make sure Celery worker is running:")
        print("   celery -A devlog worker --loglevel=info --pool=solo")
    
    # Check registered tasks
    registered = inspector.registered()
    if registered:
        print(f"\n✅ Registered tasks:")
        for worker, tasks in registered.items():
            print(f"   Worker: {worker}")
            for task in tasks:
                if 'webhooks' in task or 'devlog' in task:
                    print(f"      - {task}")
    
    print("\n🎉 Celery connection successful!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("   Make sure:")
    print("   1. Redis is running")
    print("   2. Celery worker is running")
#!/usr/bin/env python
"""
Create test data for DevLog backend
"""
import os
import sys
import django
from datetime import datetime, timedelta
from django.utils import timezone

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'devlog.settings')
django.setup()

from core.accounts.models import User
from core.tracking.models import GitHubRepository, Commit, CodingSession

def create_test_data():
    # Get the first user (you)
    try:
        user = User.objects.first()
        if not user:
            print("ERROR: No users found. Please login first via GitHub OAuth.")
            return

        print(f"Creating test data for user: {user.github_username}")

        # Get the first repository
        repo = GitHubRepository.objects.filter(user=user).first()
        if not repo:
            print("ERROR: No repositories found. Please sync repositories first.")
            return

        print(f"Using repository: {repo.full_name}")

        # Create test commits
        now = timezone.now()
        commits = []

        for i in range(10):
            commit_time = now - timedelta(hours=i, minutes=i*5)

            commit = Commit.objects.create(
                repository=repo,
                sha=f"abc123def456789{i}",
                message=f"Test commit {i+1}: Add feature {i+1}",
                author_name=user.github_username,
                author_email=user.email or f"{user.github_username}@example.com",
                committed_at=commit_time,
                additions=20 + i*10,
                deletions=5 + i*2,
                changed_files=2 + i,
                files_data=[
                    {
                        "filename": f"src/feature_{i}.py",
                        "additions": 15 + i*5,
                        "deletions": 3 + i,
                        "status": "added" if i < 3 else "modified",
                        "language": "Python"
                    },
                    {
                        "filename": f"tests/test_feature_{i}.py",
                        "additions": 5 + i*3,
                        "deletions": 2,
                        "status": "added",
                        "language": "Python"
                    }
                ],
                branch="main"
            )
            commits.append(commit)

        print(f"SUCCESS: Created {len(commits)} test commits")

        # Create test sessions
        sessions = []
        for i in range(3):
            session_start = now - timedelta(days=i, hours=2)
            session_end = session_start + timedelta(hours=1, minutes=30)

            session = CodingSession.objects.create(
                user=user,
                repository=repo,
                started_at=session_start,
                ended_at=session_end,
                duration_minutes=90,
                total_commits=3 + i,
                total_additions=150 + i*50,
                total_deletions=30 + i*10,
                files_changed=8 + i*2,
                primary_language="Python",
                languages_used=["Python", "JavaScript", "CSS"]
            )
            sessions.append(session)

        print(f"SUCCESS: Created {len(sessions)} test sessions")

        # Update commits to belong to sessions
        for i, session in enumerate(sessions):
            session_commits = commits[i*3:(i+1)*3]
            for commit in session_commits:
                commit.session = session
                commit.save()

        print(f"SUCCESS: Linked commits to sessions")

        # Update session stats
        for session in sessions:
            session.update_stats()

        print("COMPLETE: Test data creation complete!")
        print(f"Created:")
        print(f"   - {len(commits)} commits")
        print(f"   - {len(sessions)} coding sessions")
        print(f"   - Linked commits to sessions")
        print("")
        print("Now test your API endpoints:")
        print("   - GET /api/v1/activity/")
        print("   - GET /api/v1/sessions/")
        print("   - GET /api/v1/commits/")
        print("   - GET /api/v1/insights/")
        print("   - GET /api/v1/patterns/")

    except Exception as e:
        print(f"ERROR: Error creating test data: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_test_data()
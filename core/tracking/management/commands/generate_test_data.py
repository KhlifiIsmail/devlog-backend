"""Management command to generate test data for tracking app."""

import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from core.tracking.models import GitHubRepository, Commit, CodingSession
from core.tracking.services import SessionGrouper

User = get_user_model()


class Command(BaseCommand):
    help = 'Generate test data for tracking app'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            help='Username to generate data for',
            default=None
        )
        parser.add_argument(
            '--repos',
            type=int,
            help='Number of repositories to create',
            default=3
        )
        parser.add_argument(
            '--commits',
            type=int,
            help='Number of commits per repository',
            default=20
        )
    
    def handle(self, *args, **options):
        username = options['user']
        num_repos = options['repos']
        num_commits = options['commits']
        
        # Get or create test user
        if username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'User {username} not found'))
                return
        else:
            user, created = User.objects.get_or_create(
                username='testuser',
                defaults={
                    'email': 'test@example.com',
                    'github_username': 'testuser',
                }
            )
            if created:
                user.set_password('testpass123')
                user.save()
                self.stdout.write(self.style.SUCCESS(f'Created test user: testuser'))
        
        # Generate repositories
        repos = []
        languages = ['Python', 'JavaScript', 'TypeScript', 'Go', 'Rust']
        
        for i in range(num_repos):
            repo = GitHubRepository.objects.create(
                user=user,
                github_id=random.randint(100000, 999999),
                name=f'test-repo-{i+1}',
                full_name=f'{user.github_username}/test-repo-{i+1}',
                description=f'Test repository {i+1}',
                url=f'https://github.com/{user.github_username}/test-repo-{i+1}',
                default_branch='main',
                is_private=random.choice([True, False]),
                is_fork=False,
                language=random.choice(languages),
                stars_count=random.randint(0, 100),
                forks_count=random.randint(0, 20),
                is_tracking_enabled=True,
            )
            repos.append(repo)
            self.stdout.write(self.style.SUCCESS(f'Created repository: {repo.full_name}'))
        
        # Generate commits
        commit_messages = [
            'Add new feature',
            'Fix bug in authentication',
            'Refactor code',
            'Update documentation',
            'Improve performance',
            'Add tests',
            'Update dependencies',
            'Fix typo',
            'Add validation',
            'Optimize query',
        ]
        
        base_time = timezone.now() - timedelta(days=30)
        
        for repo in repos:
            current_time = base_time
            
            for j in range(num_commits):
                # Random time gap (5 mins to 2 hours)
                time_gap = random.randint(5, 120)
                current_time += timedelta(minutes=time_gap)
                
                Commit.objects.create(
                    repository=repo,
                    sha=f'{random.randint(1000000, 9999999):07x}{random.randint(1000000, 9999999):07x}',
                    message=random.choice(commit_messages),
                    author_name=user.username,
                    author_email=user.email,
                    committed_at=current_time,
                    additions=random.randint(10, 200),
                    deletions=random.randint(5, 100),
                    changed_files=random.randint(1, 10),
                    files_data=[],
                    branch='main',
                )
            
            self.stdout.write(self.style.SUCCESS(
                f'Created {num_commits} commits for {repo.name}'
            ))
        
        # Group commits into sessions
        grouper = SessionGrouper(user)
        sessions_created = grouper.group_commits()
        
        self.stdout.write(self.style.SUCCESS(
            f'\nSuccessfully created:'
            f'\n  - {num_repos} repositories'
            f'\n  - {num_repos * num_commits} commits'
            f'\n  - {sessions_created} coding sessions'
        ))
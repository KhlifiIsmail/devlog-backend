"""
AI Narrative Generation Service for DevLog.
Provides technical analysis of coding sessions using A4F with provider-5/gpt-4o-mini.
"""

import logging
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from core.tracking.models import CodingSession, Commit

logger = logging.getLogger(__name__)


class NarrativeService:
    """
    Service for generating technical narratives of coding sessions.
    Uses A4F API with provider-5/gpt-4o-mini for cost-effective, high-quality analysis.
    """

    def __init__(self):
        """Initialize the narrative service with A4F client."""
        self.api_key = getattr(settings, 'A4F_API_KEY', None)
        self.base_url = getattr(settings, 'A4F_BASE_URL', 'https://api.a4f.co/v1')
        self.model = getattr(settings, 'A4F_MODEL', 'provider-5/gpt-4o-mini')

        if not self.api_key:
            raise ValueError("A4F_API_KEY not configured in settings")

        self.cache_timeout = 60 * 60 * 24  # 24 hours

        # Setup headers for A4F API
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

    def generate_session_narrative(self, session_id: int) -> Dict[str, Any]:
        """
        Generate a technical narrative for a coding session.

        Args:
            session_id: ID of the CodingSession to analyze

        Returns:
            Dict containing the narrative and metadata

        Raises:
            ValueError: If session not found
            RuntimeError: If AI generation fails
        """
        # Check cache first
        cache_key = f"narrative_{session_id}"
        cached_result = cache.get(cache_key)
        if cached_result:
            logger.info(f"Retrieved cached narrative for session {session_id}")
            return cached_result

        try:
            # Get session and commits
            session = CodingSession.objects.get(id=session_id)
            commits = session.commits.all().order_by('committed_at')

            if not commits.exists():
                raise ValueError(f"No commits found for session {session_id}")

            # Prepare session data for analysis
            session_data = self._prepare_session_data(session, commits)

            # Generate narrative using OpenAI
            narrative = self._generate_narrative(session_data)

            # Create result with metadata
            result = {
                'narrative': narrative,
                'generated_at': timezone.now().isoformat(),
                'model_used': self.model,
                'session_id': session_id,
                'commit_count': commits.count(),
                'session_duration': session.duration_minutes
            }

            # Cache the result
            cache.set(cache_key, result, self.cache_timeout)

            # Update session model
            session.ai_summary = narrative
            session.ai_generated_at = timezone.now()
            session.save(update_fields=['ai_summary', 'ai_generated_at'])

            logger.info(f"Generated narrative for session {session_id}")
            return result

        except CodingSession.DoesNotExist:
            raise ValueError(f"Session {session_id} not found")
        except Exception as e:
            logger.error(f"Failed to generate narrative for session {session_id}: {str(e)}")
            raise RuntimeError(f"AI narrative generation failed: {str(e)}")

    def _prepare_session_data(self, session: CodingSession, commits: List[Commit]) -> Dict[str, Any]:
        """
        Prepare session data for AI analysis.

        Args:
            session: CodingSession instance
            commits: List of Commit instances

        Returns:
            Structured data for AI prompt
        """
        # Aggregate file changes
        file_changes = {}
        total_additions = 0
        total_deletions = 0
        languages = set()

        for commit in commits:
            total_additions += commit.additions
            total_deletions += commit.deletions

            # Process file data
            if commit.files_data:
                for file_info in commit.files_data:
                    filename = file_info.get('filename', '')
                    if filename:
                        # Extract file extension for language detection
                        ext = filename.split('.')[-1].lower() if '.' in filename else 'unknown'
                        languages.add(ext)

                        # Track file modification counts
                        if filename not in file_changes:
                            file_changes[filename] = {
                                'modifications': 0,
                                'additions': 0,
                                'deletions': 0,
                                'status': file_info.get('status', 'modified')
                            }

                        file_changes[filename]['modifications'] += 1
                        file_changes[filename]['additions'] += file_info.get('additions', 0)
                        file_changes[filename]['deletions'] += file_info.get('deletions', 0)

        # Get most modified files (top 10)
        most_modified = sorted(
            file_changes.items(),
            key=lambda x: x[1]['modifications'],
            reverse=True
        )[:10]

        return {
            'session': {
                'id': session.id,
                'started_at': session.started_at.isoformat(),
                'ended_at': session.ended_at.isoformat(),
                'duration_minutes': session.duration_minutes,
                'repository': session.repository.full_name,
                'primary_language': session.primary_language,
            },
            'commits': [
                {
                    'sha': commit.sha[:8],
                    'message': commit.message,
                    'committed_at': commit.committed_at.isoformat(),
                    'additions': commit.additions,
                    'deletions': commit.deletions,
                    'changed_files': commit.changed_files
                }
                for commit in commits
            ],
            'summary': {
                'total_commits': len(commits),
                'total_additions': total_additions,
                'total_deletions': total_deletions,
                'unique_files_changed': len(file_changes),
                'languages_used': list(languages),
                'most_modified_files': most_modified
            }
        }

    def _generate_narrative(self, session_data: Dict[str, Any]) -> str:
        """
        Generate technical narrative using A4F API.

        Args:
            session_data: Prepared session data

        Returns:
            Generated narrative string
        """
        system_prompt = self._get_system_prompt()
        user_prompt = self._format_user_prompt(session_data)

        # Prepare A4F API request payload
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 1000
        }

        try:
            # Make request to A4F API
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=30  # 30 second timeout
            )

            response.raise_for_status()  # Raise an exception for bad status codes

            # Parse response
            result = response.json()

            if 'choices' not in result or len(result['choices']) == 0:
                raise RuntimeError("Invalid response format from A4F API")

            narrative = result['choices'][0]['message']['content'].strip()

            logger.info(f"Successfully generated narrative using A4F API with {self.model}")
            return narrative

        except requests.exceptions.RequestException as e:
            logger.error(f"A4F API request failed: {str(e)}")
            raise RuntimeError(f"Failed to connect to A4F API: {str(e)}")
        except KeyError as e:
            logger.error(f"Invalid response format from A4F API: {str(e)}")
            raise RuntimeError(f"Invalid API response format: {str(e)}")
        except Exception as e:
            logger.error(f"A4F API call failed: {str(e)}")
            raise RuntimeError(f"Failed to generate narrative: {str(e)}")

    def _get_system_prompt(self) -> str:
        """Get the system prompt for technical analysis."""
        return """You are a technical code review assistant that analyzes coding sessions for developers.

Your task is to provide a concise, technical analysis of a coding session based on commit data. Focus on:

1. **Development Patterns**: What type of work was being done (feature development, bug fixes, refactoring, etc.)
2. **File Organization**: Which files/modules were the focus of changes
3. **Code Scope**: Scale of changes (additions vs deletions, number of files affected)
4. **Technical Decisions**: Infer technical decisions from commit messages and file patterns
5. **Development Flow**: How the work progressed through the session

Keep the analysis:
- **Technical and objective** - focus on code changes, not subjective opinions
- **Concise** - 3-4 sentences maximum
- **Actionable** - highlight patterns that could inform future development
- **Professional** - suitable for developer review or team sharing

Avoid speculation about developer intentions or emotions. Stick to observable technical patterns."""

    def _format_user_prompt(self, session_data: Dict[str, Any]) -> str:
        """Format the user prompt with session data."""
        session = session_data['session']
        commits = session_data['commits']
        summary = session_data['summary']

        # Format commit messages
        commit_details = []
        for commit in commits:
            commit_details.append(
                f"• {commit['sha']}: {commit['message']} "
                f"(+{commit['additions']}, -{commit['deletions']}, {commit['changed_files']} files)"
            )

        # Format top modified files
        file_details = []
        for filename, stats in summary['most_modified_files'][:5]:
            file_details.append(
                f"• {filename}: {stats['modifications']} modifications "
                f"(+{stats['additions']}, -{stats['deletions']})"
            )

        prompt = f"""Analyze this coding session from {session['repository']}:

**Session Overview:**
- Duration: {session['duration_minutes']} minutes
- Time: {session['started_at']} to {session['ended_at']}
- Primary Language: {session['primary_language']}

**Commit Activity ({summary['total_commits']} commits):**
{chr(10).join(commit_details)}

**Change Summary:**
- Total: +{summary['total_additions']}, -{summary['total_deletions']} lines
- Files Changed: {summary['unique_files_changed']}
- Languages: {', '.join(summary['languages_used'])}

**Most Modified Files:**
{chr(10).join(file_details) if file_details else '• No file details available'}

Provide a technical analysis of this coding session focusing on development patterns, technical decisions, and code organization."""

        return prompt

    def invalidate_cache(self, session_id: int) -> bool:
        """
        Invalidate cached narrative for a session.

        Args:
            session_id: ID of the session to invalidate

        Returns:
            True if cache was cleared, False otherwise
        """
        cache_key = f"narrative_{session_id}"
        return cache.delete(cache_key)
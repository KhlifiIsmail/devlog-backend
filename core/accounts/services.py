import requests
from django.conf import settings
from typing import Dict, Optional


class GitHubOAuthService:
    """Service for GitHub OAuth authentication"""
    
    GITHUB_API_URL = 'https://api.github.com'
    GITHUB_OAUTH_URL = 'https://github.com/login/oauth'
    
    def exchange_code_for_token(self, code: str) -> Optional[str]:
        """
        Exchange OAuth code for access token
        
        Args:
            code: OAuth authorization code from GitHub
            
        Returns:
            Access token string or None if failed
        """
        response = requests.post(
            f'{self.GITHUB_OAUTH_URL}/access_token',
            data={
                'client_id': settings.GITHUB_CLIENT_ID,
                'client_secret': settings.GITHUB_CLIENT_SECRET,
                'code': code,
            },
            headers={'Accept': 'application/json'},
            timeout=10,
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get('access_token')
        
        return None
    
    def get_user_info(self, access_token: str) -> Optional[Dict]:
        """
        Get user information from GitHub
        
        Args:
            access_token: GitHub access token
            
        Returns:
            User data dict or None if failed
        """
        response = requests.get(
            f'{self.GITHUB_API_URL}/user',
            headers={
                'Authorization': f'token {access_token}',
                'Accept': 'application/json',
            },
            timeout=10,
        )
        
        if response.status_code == 200:
            return response.json()
        
        return None
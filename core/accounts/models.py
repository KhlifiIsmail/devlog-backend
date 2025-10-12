from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom User model with GitHub OAuth fields"""
    
    github_id = models.BigIntegerField(unique=True, null=True, blank=True)
    github_username = models.CharField(max_length=100, unique=True, null=True, blank=True)
    github_avatar_url = models.URLField(null=True, blank=True)
    github_access_token = models.CharField(max_length=255, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'users'
    
    def __str__(self):
        return self.github_username or self.username
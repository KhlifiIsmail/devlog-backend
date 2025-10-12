from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'github_id',
            'github_username',
            'github_avatar_url',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class AuthResponseSerializer(serializers.Serializer):
    """Serializer for authentication response"""
    
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()


class GitHubCallbackSerializer(serializers.Serializer):
    """Serializer for GitHub OAuth callback"""
    
    code = serializers.CharField(required=True)
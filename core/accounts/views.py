from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import User
from .serializers import (
    GitHubCallbackSerializer,
    AuthResponseSerializer,
    UserSerializer,
)
from .services import GitHubOAuthService


class GitHubCallbackView(APIView):
    permission_classes = [AllowAny]
    
    @extend_schema(
        request=GitHubCallbackSerializer,
        responses={
            200: AuthResponseSerializer,
            400: OpenApiResponse(description='Invalid code'),
        },
        tags=['Authentication']
    )
    def post(self, request):
        serializer = GitHubCallbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        code = serializer.validated_data['code']
        
        github_service = GitHubOAuthService()
        access_token = github_service.exchange_code_for_token(code)
        
        if not access_token:
            return Response(
                {'error': 'Failed to exchange code for access token'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        github_user = github_service.get_user_info(access_token)
        
        if not github_user:
            return Response(
                {'error': 'Failed to fetch user info from GitHub'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user, created = User.objects.update_or_create(
            github_id=github_user['id'],
            defaults={
                'github_username': github_user['login'],
                'github_avatar_url': github_user['avatar_url'],
                'github_access_token': access_token,
                'email': github_user.get('email') or '',
                'username': github_user['login'],
            }
        )
        
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
        })


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses={200: UserSerializer},
        tags=['Authentication']
    )
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
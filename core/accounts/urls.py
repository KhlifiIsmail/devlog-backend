from django.urls import path
from .views import GitHubCallbackView, CurrentUserView

app_name = 'accounts'

urlpatterns = [
    path('github/callback/', GitHubCallbackView.as_view(), name='github-callback'),
    path('user/', CurrentUserView.as_view(), name='current-user'),
]
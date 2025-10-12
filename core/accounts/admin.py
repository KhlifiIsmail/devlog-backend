from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'github_username', 'is_staff', 'created_at']
    list_filter = ['is_staff', 'is_superuser', 'is_active']
    search_fields = ['username', 'email', 'github_username']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('GitHub Info', {
            'fields': ('github_id', 'github_username', 'github_avatar_url', 'github_access_token')
        }),
    )
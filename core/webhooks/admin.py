from django.contrib import admin
from .models import WebhookEvent


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'event_type',
        'repository_full_name',
        'status',
        'user',
        'created_at',
        'processed_at',
    ]
    list_filter = ['event_type', 'status', 'created_at']
    search_fields = ['repository_full_name', 'delivery_id']
    readonly_fields = [
        'id',
        'event_type',
        'repository_full_name',
        'delivery_id',
        'payload',
        'created_at',
        'updated_at',
        'processed_at',
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Event Info', {
            'fields': ('id', 'event_type', 'repository_full_name', 'delivery_id')
        }),
        ('Processing', {
            'fields': ('status', 'error_message', 'user')
        }),
        ('Payload', {
            'fields': ('payload',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'processed_at')
        }),
    )
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
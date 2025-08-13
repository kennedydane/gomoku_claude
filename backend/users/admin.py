"""
Django admin configuration for user models.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin interface for User model."""
    
    list_display = [
        'username', 'email', 'display_name', 'games_played',
        'games_won', 'win_rate', 'is_active', 'date_joined'
    ]
    
    list_filter = ['is_active', 'is_staff', 'is_superuser', 'date_joined']
    
    search_fields = ['username', 'email', 'display_name']
    
    readonly_fields = ['date_joined', 'last_login', 'win_rate']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Game Statistics', {
            'fields': ('games_played', 'games_won', 'win_rate')
        }),
        ('Profile', {
            'fields': ('display_name',)
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Profile', {
            'fields': ('email', 'display_name')
        }),
    )
    
    def win_rate(self, obj):
        """Display win rate in admin."""
        return f"{obj.win_rate:.1f}%"
    win_rate.short_description = 'Win Rate'
    
    actions = ['reset_game_stats']
    
    def reset_game_stats(self, request, queryset):
        """Admin action to reset game statistics."""
        for user in queryset:
            user.reset_stats()
        self.message_user(request, f"Reset game stats for {queryset.count()} users.")
    reset_game_stats.short_description = "Reset game statistics"
"""
Django admin configuration for game models.
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    RuleSet, Game, GameMove, PlayerSession,
    GameEvent, Challenge
)


@admin.register(RuleSet)
class RuleSetAdmin(admin.ModelAdmin):
    """Admin interface for RuleSet model."""
    
    list_display = ['name', 'game_type', 'board_size', 'allow_overlines', 'created_at']
    list_filter = ['game_type', 'board_size', 'allow_overlines', 'scoring_method', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'game_type', 'description')
        }),
        ('Board Configuration', {
            'fields': ('board_size',)
        }),
        ('Gomoku Rules', {
            'fields': ('allow_overlines', 'forbidden_moves'),
            'classes': ('collapse',),
            'description': 'These settings apply only to Gomoku games'
        }),
        ('Go Rules', {
            'fields': ('komi', 'handicap_stones', 'scoring_method'),
            'classes': ('collapse',),
            'description': 'These settings apply only to Go games'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    """Admin interface for Game model."""
    
    list_display = [
        'id_short', 'black_player', 'white_player', 'status',
        'current_player', 'move_count', 'winner', 'created_at'
    ]
    list_filter = ['status', 'created_at', 'ruleset']
    search_fields = [
        'id', 'black_player__username', 'white_player__username',
        'winner__username'
    ]
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'started_at', 'finished_at',
        'board_preview'
    ]
    
    fieldsets = (
        ('Game Info', {
            'fields': ('id', 'ruleset', 'status')
        }),
        ('Players', {
            'fields': ('black_player', 'white_player', 'current_player', 'winner')
        }),
        ('Game State', {
            'fields': ('move_count', 'board_state', 'board_preview')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'started_at', 'finished_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def id_short(self, obj):
        """Display shortened UUID."""
        return str(obj.id)[:8] + '...'
    id_short.short_description = 'Game ID'
    
    def board_preview(self, obj):
        """Display a simple board preview."""
        if not obj.board_state or 'board' not in obj.board_state:
            return 'No board'
        
        board = obj.board_state['board']
        size = obj.board_state.get('size', 15)
        
        # Create a simple HTML representation
        html = '<div style="font-family: monospace; line-height: 1.2;">'
        for row in board[:10]:  # Show only first 10 rows
            for cell in row[:10]:  # Show only first 10 columns
                if cell == 'BLACK':
                    html += '●'
                elif cell == 'WHITE':
                    html += '○'
                else:
                    html += '·'
                html += ' '
            html += '<br>'
        if size > 10:
            html += f'... ({size}x{size} board)'
        html += '</div>'
        
        return format_html(html)
    board_preview.short_description = 'Board Preview'
    
    actions = ['start_games', 'abandon_games']
    
    def start_games(self, request, queryset):
        """Start selected waiting games."""
        count = 0
        for game in queryset.filter(status='WAITING'):
            try:
                game.start_game()
                count += 1
            except ValueError:
                pass
        self.message_user(request, f"Started {count} games.")
    start_games.short_description = "Start selected games"
    
    def abandon_games(self, request, queryset):
        """Abandon selected active games."""
        count = queryset.filter(status='ACTIVE').update(status='ABANDONED')
        self.message_user(request, f"Abandoned {count} games.")
    abandon_games.short_description = "Abandon selected games"


@admin.register(GameMove)
class GameMoveAdmin(admin.ModelAdmin):
    """Admin interface for GameMove model."""
    
    list_display = [
        'game_short', 'move_number', 'player', 'position',
        'player_color', 'is_winning_move', 'created_at'
    ]
    list_filter = ['player_color', 'is_winning_move', 'created_at']
    search_fields = ['game__id', 'player__username']
    readonly_fields = ['created_at']
    
    def game_short(self, obj):
        """Display shortened game UUID."""
        return str(obj.game_id)[:8] + '...'
    game_short.short_description = 'Game'
    
    def position(self, obj):
        """Display position as coordinates."""
        return f"({obj.row}, {obj.col})"
    position.short_description = 'Position'


@admin.register(PlayerSession)
class PlayerSessionAdmin(admin.ModelAdmin):
    """Admin interface for PlayerSession model."""
    
    list_display = [
        'session_short', 'user', 'status', 'is_active_now',
        'last_activity', 'created_at'
    ]
    list_filter = ['status', 'created_at', 'last_activity']
    search_fields = ['session_id', 'user__username']
    readonly_fields = ['session_id', 'created_at']
    
    def session_short(self, obj):
        """Display shortened session UUID."""
        return str(obj.session_id)[:8] + '...'
    session_short.short_description = 'Session'
    
    def is_active_now(self, obj):
        """Show if session is currently active."""
        return obj.is_active
    is_active_now.boolean = True
    is_active_now.short_description = 'Active Now'
    
    actions = ['end_sessions']
    
    def end_sessions(self, request, queryset):
        """End selected sessions."""
        count = queryset.update(status='IDLE', current_game=None)
        self.message_user(request, f"Ended {count} sessions.")
    end_sessions.short_description = "End selected sessions"


@admin.register(GameEvent)
class GameEventAdmin(admin.ModelAdmin):
    """Admin interface for GameEvent model."""
    
    list_display = [
        'id', 'user', 'event_type', 'consumed',
        'created_at'
    ]
    list_filter = ['event_type', 'consumed', 'created_at']
    search_fields = ['user__username', 'event_type']
    readonly_fields = ['created_at']
    
    actions = ['mark_consumed', 'mark_unconsumed']
    
    def mark_consumed(self, request, queryset):
        """Mark events as consumed."""
        count = queryset.update(consumed=True)
        self.message_user(request, f"Marked {count} events as consumed.")
    mark_consumed.short_description = "Mark as consumed"
    
    def mark_unconsumed(self, request, queryset):
        """Mark events as unconsumed."""
        count = queryset.update(consumed=False)
        self.message_user(request, f"Marked {count} events as unconsumed.")
    mark_unconsumed.short_description = "Mark as unconsumed"


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    """Admin interface for Challenge model."""
    
    list_display = [
        'id_short', 'challenger', 'challenged', 'status',
        'is_expired_now', 'created_at', 'expires_at'
    ]
    list_filter = ['status', 'created_at', 'expires_at']
    search_fields = [
        'id', 'challenger__username', 'challenged__username'
    ]
    readonly_fields = ['id', 'created_at', 'responded_at']
    
    fieldsets = (
        ('Challenge Info', {
            'fields': ('id', 'status')
        }),
        ('Players', {
            'fields': ('challenger', 'challenged')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'expires_at', 'responded_at')
        }),
    )
    
    def id_short(self, obj):
        """Display shortened UUID."""
        return str(obj.id)[:8] + '...'
    id_short.short_description = 'Challenge ID'
    
    def is_expired_now(self, obj):
        """Show if challenge is expired."""
        return obj.is_expired
    is_expired_now.boolean = True
    is_expired_now.short_description = 'Expired'
    
    actions = ['expire_challenges', 'cancel_challenges']
    
    def expire_challenges(self, request, queryset):
        """Expire selected pending challenges."""
        count = queryset.filter(status='PENDING').update(status='EXPIRED')
        self.message_user(request, f"Expired {count} challenges.")
    expire_challenges.short_description = "Expire selected challenges"
    
    def cancel_challenges(self, request, queryset):
        """Cancel selected pending challenges."""
        count = queryset.filter(status='PENDING').update(status='CANCELLED')
        self.message_user(request, f"Cancelled {count} challenges.")
    cancel_challenges.short_description = "Cancel selected challenges"
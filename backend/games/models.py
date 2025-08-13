"""
Game models for the Gomoku system.

This module defines all game-related models including RuleSet, Game, GameMove,
PlayerSession, GameEvent, and Challenge models.
"""

import uuid
from datetime import timedelta
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone


class RuleSet(models.Model):
    """
    RuleSet model for different Gomoku game variations.
    
    Supports Standard, Renju, Freestyle, Caro and custom rule configurations.
    """
    
    name = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Unique name of the rule set"
    )
    
    board_size = models.PositiveIntegerField(
        default=15,
        validators=[
            MinValueValidator(9, message="Board size must be at least 9"),
            MaxValueValidator(25, message="Board size cannot exceed 25")
        ],
        help_text="Size of the game board (e.g., 15 for 15x15)"
    )
    
    allow_overlines = models.BooleanField(
        default=False,
        help_text="Whether lines longer than 5 stones count as wins"
    )
    
    forbidden_moves = models.JSONField(
        default=dict,
        blank=True,
        help_text="JSON configuration for forbidden move patterns"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Human-readable description of the rules"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'rulesets'
        verbose_name = 'Rule Set'
        verbose_name_plural = 'Rule Sets'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class GameStatus(models.TextChoices):
    """Enumeration of game statuses."""
    WAITING = 'WAITING', 'Waiting'
    ACTIVE = 'ACTIVE', 'Active'
    FINISHED = 'FINISHED', 'Finished'
    ABANDONED = 'ABANDONED', 'Abandoned'


class Player(models.TextChoices):
    """Enumeration of player colors."""
    BLACK = 'BLACK', 'Black'
    WHITE = 'WHITE', 'White'


class Game(models.Model):
    """
    Game model representing a Gomoku game session.
    
    Tracks game state, players, moves, and results.
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique game identifier"
    )
    
    black_player = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='games_as_black',
        db_index=True,  # Index for player queries
        help_text="Player with black stones"
    )
    
    white_player = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='games_as_white',
        db_index=True,  # Index for player queries
        help_text="Player with white stones"
    )
    
    ruleset = models.ForeignKey(
        RuleSet,
        on_delete=models.RESTRICT,
        related_name='games',
        db_index=True,  # Index for ruleset queries
        help_text="Rule set for this game"
    )
    
    status = models.CharField(
        max_length=10,
        choices=GameStatus.choices,
        default=GameStatus.WAITING,
        db_index=True,
        help_text="Current game status"
    )
    
    current_player = models.CharField(
        max_length=5,
        choices=Player.choices,
        default=Player.BLACK,
        help_text="Player whose turn it is"
    )
    
    board_state = models.JSONField(
        default=dict,
        help_text="Current board state as JSON"
    )
    
    winner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='won_games',
        help_text="Winner of the game"
    )
    
    move_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of moves made"
    )
    
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the game started"
    )
    
    finished_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the game finished"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True  # Index for date-based queries
    )
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'games'
        verbose_name = 'Game'
        verbose_name_plural = 'Games'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['black_player', 'status']),
            models.Index(fields=['white_player', 'status']),
            models.Index(fields=['finished_at']),
        ]
    
    def __str__(self):
        return f"Game {self.id}: {self.black_player} vs {self.white_player}"
    
    def initialize_board(self):
        """Initialize empty board based on ruleset size."""
        size = self.ruleset.board_size
        self.board_state = {
            'size': size,
            'board': [[None for _ in range(size)] for _ in range(size)]
        }
    
    def start_game(self):
        """Start the game."""
        if self.status != GameStatus.WAITING:
            raise ValueError("Can only start a waiting game")
        self.status = GameStatus.ACTIVE
        self.started_at = timezone.now()
        self.initialize_board()
        self.save()
    
    def finish_game(self, winner=None):
        """Finish the game with optional winner."""
        self.status = GameStatus.FINISHED
        self.finished_at = timezone.now()
        self.winner = winner
        self.save()
        
        # Update player statistics
        if winner:
            winner.update_game_stats(won=True)
            loser = self.white_player if winner == self.black_player else self.black_player
            loser.update_game_stats(won=False)


class GameMove(models.Model):
    """
    GameMove model representing individual moves in a game.
    
    Tracks move sequence, position, and player information.
    """
    
    game = models.ForeignKey(
        Game,
        on_delete=models.CASCADE,
        related_name='moves',
        db_index=True,  # Index for game-specific move queries
        help_text="Game this move belongs to"
    )
    
    player = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='moves',
        db_index=True,  # Index for player move history
        help_text="Player who made this move"
    )
    
    move_number = models.PositiveIntegerField(
        help_text="Sequential move number"
    )
    
    row = models.PositiveIntegerField(
        validators=[MaxValueValidator(24)],
        help_text="Row position (0-based)"
    )
    
    col = models.PositiveIntegerField(
        validators=[MaxValueValidator(24)],
        help_text="Column position (0-based)"
    )
    
    player_color = models.CharField(
        max_length=5,
        choices=Player.choices,
        help_text="Color of the player making the move"
    )
    
    is_winning_move = models.BooleanField(
        default=False,
        help_text="Whether this move won the game"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True  # Index for chronological move queries
    )
    
    class Meta:
        db_table = 'game_moves'
        verbose_name = 'Game Move'
        verbose_name_plural = 'Game Moves'
        ordering = ['game', 'move_number']
        unique_together = [
            ['game', 'move_number'],
            ['game', 'row', 'col']
        ]
        indexes = [
            models.Index(fields=['game', 'move_number']),
            models.Index(fields=['player', 'created_at']),
            models.Index(fields=['is_winning_move']),
        ]
    
    def __str__(self):
        return f"Move {self.move_number} in {self.game_id}: ({self.row}, {self.col})"


class SessionStatus(models.TextChoices):
    """Enumeration of session statuses."""
    ONLINE = 'ONLINE', 'Online'
    IDLE = 'IDLE', 'Idle'
    IN_GAME = 'IN_GAME', 'In Game'


class PlayerSession(models.Model):
    """
    PlayerSession model for tracking online players.
    
    Manages player presence and current game associations.
    """
    
    session_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique session identifier"
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sessions',
        help_text="User this session belongs to"
    )
    
    current_game = models.ForeignKey(
        Game,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='active_sessions',
        help_text="Current game if player is in game"
    )
    
    status = models.CharField(
        max_length=20,
        choices=SessionStatus.choices,
        default=SessionStatus.ONLINE,
        help_text="Current session status"
    )
    
    last_activity = models.DateTimeField(
        auto_now=True,
        db_index=True,
        help_text="Last activity timestamp"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'player_sessions'
        verbose_name = 'Player Session'
        verbose_name_plural = 'Player Sessions'
        ordering = ['-last_activity']
    
    def __str__(self):
        return f"Session {self.session_id}: {self.user}"
    
    @property
    def is_active(self):
        """Check if session is still active (not timed out)."""
        time_since = timezone.now() - self.last_activity
        return time_since < timedelta(seconds=60)
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = timezone.now()
        self.save(update_fields=['last_activity'])


class GameEvent(models.Model):
    """
    GameEvent model for SSE event distribution.
    
    Stores events to be pushed to clients via Server-Sent Events.
    """
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='events',
        help_text="User this event is for"
    )
    
    event_type = models.CharField(
        max_length=50,
        help_text="Type of event (e.g., 'move', 'game_start', 'challenge')"
    )
    
    event_data = models.JSONField(
        help_text="Event payload as JSON"
    )
    
    consumed = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether this event has been consumed"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )
    
    class Meta:
        db_table = 'game_events'
        verbose_name = 'Game Event'
        verbose_name_plural = 'Game Events'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['user', 'consumed', 'created_at']),
        ]
    
    def __str__(self):
        return f"Event {self.id}: {self.event_type} for {self.user}"


class ChallengeStatus(models.TextChoices):
    """Enumeration of challenge statuses."""
    PENDING = 'PENDING', 'Pending'
    ACCEPTED = 'ACCEPTED', 'Accepted'
    REJECTED = 'REJECTED', 'Rejected'
    EXPIRED = 'EXPIRED', 'Expired'
    CANCELLED = 'CANCELLED', 'Cancelled'


class Challenge(models.Model):
    """
    Challenge model for player-to-player game invitations.
    
    Manages game challenges between players with expiration.
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique challenge identifier"
    )
    
    challenger = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_challenges',
        help_text="Player who sent the challenge"
    )
    
    challenged = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_challenges',
        help_text="Player who received the challenge"
    )
    
    status = models.CharField(
        max_length=20,
        choices=ChallengeStatus.choices,
        default=ChallengeStatus.PENDING,
        db_index=True,
        help_text="Current challenge status"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    expires_at = models.DateTimeField(
        help_text="When this challenge expires"
    )
    
    responded_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the challenge was responded to"
    )
    
    class Meta:
        db_table = 'challenges'
        verbose_name = 'Challenge'
        verbose_name_plural = 'Challenges'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['challenged', 'status']),
        ]
    
    def __str__(self):
        return f"Challenge {self.id}: {self.challenger} -> {self.challenged}"
    
    def save(self, *args, **kwargs):
        """Set expiration time on creation."""
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=5)
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        """Check if challenge has expired."""
        return timezone.now() > self.expires_at
    
    def accept(self):
        """Accept the challenge."""
        if self.status != ChallengeStatus.PENDING:
            raise ValueError("Can only accept pending challenges")
        if self.is_expired:
            self.status = ChallengeStatus.EXPIRED
        else:
            self.status = ChallengeStatus.ACCEPTED
            self.responded_at = timezone.now()
        self.save()
    
    def reject(self):
        """Reject the challenge."""
        if self.status != ChallengeStatus.PENDING:
            raise ValueError("Can only reject pending challenges")
        self.status = ChallengeStatus.REJECTED
        self.responded_at = timezone.now()
        self.save()
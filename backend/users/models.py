"""
User models for the Gomoku game system.

This module defines the User model which extends Django's AbstractUser
to include game statistics and custom fields.
"""

from django.contrib.auth.models import AbstractUser
from django.core.validators import MinLengthValidator, RegexValidator
from django.db import models


class User(AbstractUser):
    """
    Custom User model for Gomoku players.
    
    Extends Django's AbstractUser to add game statistics and custom fields.
    The username field is case-insensitive and follows specific validation rules.
    """
    
    # Override username to add custom validators
    username = models.CharField(
        max_length=50,
        unique=True,
        validators=[
            MinLengthValidator(3, message="Username must be at least 3 characters long"),
            RegexValidator(
                regex=r'^[\w-]+$',
                message="Username can only contain letters, numbers, underscores, and hyphens"
            )
        ],
        help_text="Required. 3-50 characters. Letters, numbers, underscores and hyphens only."
    )
    
    # Override email to make it optional but unique when provided
    email = models.EmailField(
        max_length=255,
        blank=True,
        null=True,
        unique=True,
        help_text="Optional. Must be unique if provided."
    )
    
    # Additional profile fields
    display_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional display name shown in the UI"
    )
    
    # Game statistics
    games_played = models.PositiveIntegerField(
        default=0,
        db_index=True,
        help_text="Total number of completed games"
    )
    
    games_won = models.PositiveIntegerField(
        default=0,
        db_index=True,
        help_text="Total number of games won"
    )
    
    # Soft deletion is handled by is_active field from AbstractUser
    # created_at is handled by date_joined from AbstractUser
    # updated_at can be added if needed
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']
        constraints = [
            models.CheckConstraint(
                check=models.Q(games_won__lte=models.F('games_played')),
                name='games_won_not_exceed_played'
            ),
        ]
    
    def __str__(self):
        """Return display name if available, otherwise username."""
        return self.display_name or self.username
    
    def save(self, *args, **kwargs):
        """Override save to ensure username is lowercase."""
        if self.username:
            self.username = self.username.lower().strip()
        if self.email:
            self.email = self.email.lower().strip()
        super().save(*args, **kwargs)
    
    @property
    def win_rate(self):
        """Calculate win rate as a percentage."""
        if self.games_played == 0:
            return 0.0
        return (self.games_won / self.games_played) * 100
    
    @property
    def losses(self):
        """Calculate number of games lost."""
        return self.games_played - self.games_won
    
    @property
    def is_experienced(self):
        """Check if user has played 10+ games."""
        return self.games_played >= 10
    
    def update_game_stats(self, won):
        """
        Update game statistics after a game.
        
        Args:
            won: Boolean indicating if the user won
        """
        self.games_played += 1
        if won:
            self.games_won += 1
        self.save(update_fields=['games_played', 'games_won'])
    
    def reset_stats(self):
        """Reset all game statistics."""
        self.games_played = 0
        self.games_won = 0
        self.save(update_fields=['games_played', 'games_won'])
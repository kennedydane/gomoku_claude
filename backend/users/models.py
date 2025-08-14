"""
User models for the Gomoku game system.

This module defines the User model which extends Django's AbstractUser
to include game statistics and custom fields, plus enhanced token authentication.
"""

import binascii
import os
from datetime import timedelta
from django.contrib.auth.models import AbstractUser, UserManager as BaseUserManager
from django.core.validators import MinLengthValidator, RegexValidator
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """Custom user manager to handle email normalization."""
    
    def _normalize_email_for_unique_constraint(self, email):
        """Convert empty string to None for proper unique constraint handling."""
        if email == '':
            return None
        return email
    
    def create_user(self, username, email=None, password=None, **extra_fields):
        """Create and save a regular User with the given username and password."""
        email = self._normalize_email_for_unique_constraint(email)
        return super().create_user(username, email, password, **extra_fields)
    
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        """Create and save a superuser with the given username and password."""
        email = self._normalize_email_for_unique_constraint(email)
        return super().create_superuser(username, email, password, **extra_fields)


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
    
    objects = UserManager()
    
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
        if self.email is not None:
            self.email = self.email.lower().strip()
            # Convert empty string to None for unique constraint
            if self.email == '':
                self.email = None
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


class EnhancedTokenManager(models.Manager):
    """Manager for enhanced token operations."""
    
    def create_for_device(self, user, device_name='', device_info=None):
        """Create a token for a specific device."""
        if device_info is None:
            device_info = {}
        
        return self.create(
            user=user,
            device_name=device_name,
            device_info=device_info
        )
    
    def get_valid_tokens_for_user(self, user):
        """Get all valid (non-expired) tokens for a user."""
        return self.filter(
            user=user,
            expires_at__gt=timezone.now()
        )
    
    def revoke_all_for_user(self, user):
        """Revoke (delete) all tokens for a user."""
        return self.filter(user=user).delete()[0]
    
    def cleanup_expired(self):
        """Remove all expired tokens."""
        return self.filter(expires_at__lte=timezone.now()).delete()[0]


class EnhancedToken(models.Model):
    """
    Enhanced authentication token with expiration, device tracking, and usage tracking.
    
    This model extends the basic DRF token functionality to provide:
    - Token expiration
    - Device-specific tokens
    - Last used tracking
    - Multiple tokens per user
    """
    
    user = models.ForeignKey(
        'User',
        related_name='enhanced_tokens',
        on_delete=models.CASCADE,
        help_text="The user this token belongs to"
    )
    
    key = models.CharField(
        max_length=40,
        unique=True,
        db_index=True,
        help_text="The token key used for authentication"
    )
    
    device_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional device identifier"
    )
    
    device_info = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional device information"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this token was created"
    )
    
    expires_at = models.DateTimeField(
        help_text="When this token expires"
    )
    
    last_used = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this token was last used"
    )
    
    objects = EnhancedTokenManager()
    
    class Meta:
        db_table = 'enhanced_tokens'
        verbose_name = 'Enhanced Token'
        verbose_name_plural = 'Enhanced Tokens'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'expires_at']),
            models.Index(fields=['key']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        """Return string representation."""
        device = f" ({self.device_name})" if self.device_name else ""
        return f"Token for {self.user.username}{device}"
    
    def save(self, *args, **kwargs):
        """Override save to generate key and set expiration."""
        if not self.key:
            self.key = self.generate_key()
        
        if not self.expires_at:
            # Default expiration: 7 days from now
            self.expires_at = timezone.now() + timedelta(days=7)
        
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        """Check if token has expired."""
        return timezone.now() > self.expires_at
    
    def generate_key(self):
        """Generate a random token key."""
        return binascii.hexlify(os.urandom(20)).decode()
    
    def update_last_used(self):
        """Update the last_used timestamp."""
        self.last_used = timezone.now()
        self.save(update_fields=['last_used'])
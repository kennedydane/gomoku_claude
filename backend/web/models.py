"""
Models for the web interface.
"""

from typing import TYPE_CHECKING
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser

User = get_user_model()


class FriendshipStatus(models.TextChoices):
    """Enumeration of friendship statuses."""
    PENDING = 'PENDING', 'Pending'
    ACCEPTED = 'ACCEPTED', 'Accepted'
    REJECTED = 'REJECTED', 'Rejected'


class FriendshipManager(models.Manager):
    """Custom manager for Friendship model."""
    
    def get_friends(self, user: 'AbstractUser'):
        """Get all accepted friends for a user."""
        from django.db.models import Case, When, IntegerField
        
        # Single query to get all friend relationships involving the user
        friendships = self.filter(
            models.Q(requester=user) | models.Q(addressee=user),
            status=FriendshipStatus.ACCEPTED
        ).select_related('requester', 'addressee')
        
        # Extract friend user objects
        friends = []
        for friendship in friendships:
            friend = friendship.addressee if friendship.requester == user else friendship.requester
            friends.append(friend)
        
        return User.objects.filter(id__in=[f.id for f in friends])
    
    def get_pending_requests(self, user: 'AbstractUser'):
        """Get pending friend requests TO a user."""
        return self.filter(
            addressee=user,
            status=FriendshipStatus.PENDING
        )
    
    def are_friends(self, user1: 'AbstractUser', user2: 'AbstractUser') -> bool:
        """Check if two users are friends."""
        return self.filter(
            models.Q(requester=user1, addressee=user2) | 
            models.Q(requester=user2, addressee=user1),
            status=FriendshipStatus.ACCEPTED
        ).exists()


class Friendship(models.Model):
    """
    Model representing friendship relationships between users.
    """
    
    requester = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_friend_requests',
        help_text="User who sent the friend request"
    )
    
    addressee = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_friend_requests',
        help_text="User who received the friend request"
    )
    
    status = models.CharField(
        max_length=10,
        choices=FriendshipStatus.choices,
        default=FriendshipStatus.PENDING,
        help_text="Current status of the friendship"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the friend request was sent"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When the friendship status was last updated"
    )
    
    objects = FriendshipManager()
    
    class Meta:
        # Prevent duplicate friendships and self-friendships
        constraints = [
            models.UniqueConstraint(
                fields=['requester', 'addressee'],
                name='unique_friendship'
            ),
            models.CheckConstraint(
                check=~models.Q(requester=models.F('addressee')),
                name='no_self_friendship'
            ),
        ]
        
        # Add index for common queries
        indexes = [
            models.Index(fields=['requester', 'status']),
            models.Index(fields=['addressee', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]
        
        ordering = ['-created_at']
    
    def clean(self):
        """Validate the friendship."""
        if self.requester == self.addressee:
            raise ValidationError("Users cannot befriend themselves.")
        
        # Check for reverse duplicate (if user2 -> user1 exists, prevent user1 -> user2)
        reverse_exists = Friendship.objects.filter(
            requester=self.addressee,
            addressee=self.requester
        ).exclude(pk=self.pk).exists()
        
        if reverse_exists:
            raise ValidationError("A friendship already exists between these users.")
    
    def save(self, *args, **kwargs):
        """Save with validation."""
        self.clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        """String representation."""
        return f"{self.requester.username} -> {self.addressee.username} ({self.status})"

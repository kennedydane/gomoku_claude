"""
Comprehensive tests for User model.
"""

from django.test import TestCase, TransactionTestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.contrib.auth import get_user_model

from tests.factories import UserFactory

User = get_user_model()


class UserModelConstraintTests(TransactionTestCase):
    """Test cases for database constraints that need transaction rollback."""
    
    def test_username_uniqueness(self):
        """Test that usernames must be unique (case-insensitive)."""
        UserFactory(username='testuser')
        
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                User.objects.create(username='testuser')
        
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                User.objects.create(username='TestUser')
    
    def test_email_uniqueness_when_provided(self):
        """Test that emails must be unique when provided."""
        UserFactory(email='test@example.com')
        
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                User.objects.create(username='user2', email='test@example.com')
    
    def test_games_won_constraint(self):
        """Test that games_won cannot exceed games_played."""
        user = UserFactory(games_played=5, games_won=3)
        user.save()  # Should be valid
        
        # This should be caught by database constraint
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                User.objects.create(
                    username='testuser',
                    games_played=5,
                    games_won=10  # More wins than games played
                )
    
    def test_negative_statistics_not_allowed(self):
        """Test that negative statistics are not allowed."""
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                User.objects.create(
                    username='testuser',
                    games_played=-1
                )
        
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                User.objects.create(
                    username='testuser2',
                    games_won=-1
                )


class UserModelTestCase(TestCase):
    """Test cases for User model validation and behavior."""
    
    def test_user_creation_with_valid_data(self):
        """Test creating a user with valid data."""
        user = UserFactory(
            username='testuser',
            email='test@example.com',
            display_name='Test User'
        )
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.display_name, 'Test User')
        self.assertEqual(user.games_played, 0)
        self.assertEqual(user.games_won, 0)
        self.assertTrue(user.is_active)
        self.assertIsNotNone(user.date_joined)
    
    def test_username_case_insensitive_storage(self):
        """Test that usernames are stored in lowercase."""
        user = User.objects.create(username='TestUser', email='test@example.com')
        self.assertEqual(user.username, 'testuser')
    
    def test_email_case_insensitive_storage(self):
        """Test that emails are stored in lowercase."""
        user = User.objects.create(username='testuser', email='Test@Example.COM')
        self.assertEqual(user.email, 'test@example.com')
    
    
    def test_email_can_be_blank(self):
        """Test that email can be blank."""
        user = User.objects.create(username='testuser')
        self.assertIsNone(user.email)
    
    def test_multiple_users_with_blank_email(self):
        """Test that multiple users can have blank emails."""
        user1 = User.objects.create(username='user1')  # email defaults to None
        user2 = User.objects.create(username='user2')  # email defaults to None
        self.assertIsNone(user1.email)
        self.assertIsNone(user2.email)
    
    def test_username_minimum_length_validation(self):
        """Test that username must be at least 3 characters."""
        with self.assertRaises(ValidationError):
            user = User(username='ab')
            user.full_clean(exclude=['password'])
    
    def test_username_character_validation(self):
        """Test that username only allows valid characters."""
        # Valid characters - create user without full_clean due to password requirement
        user = User.objects.create(username='user_name-123', email='test@example.com')
        self.assertEqual(user.username, 'user_name-123')
        
        # Invalid characters - test at model level
        with self.assertRaises(ValidationError):
            user = User(username='user@name')
            user.full_clean(exclude=['password'])
        
        with self.assertRaises(ValidationError):
            user = User(username='user name')
            user.full_clean(exclude=['password'])
    
    def test_display_name_optional(self):
        """Test that display_name is optional."""
        user = UserFactory(display_name='')
        self.assertEqual(user.display_name, '')
    
    def test_games_statistics_default_values(self):
        """Test that game statistics have correct default values."""
        user = UserFactory()
        self.assertEqual(user.games_played, 0)
        self.assertEqual(user.games_won, 0)
    
    
    def test_win_rate_calculation(self):
        """Test win rate property calculation."""
        user = UserFactory(games_played=0, games_won=0)
        self.assertEqual(user.win_rate, 0.0)
        
        user = UserFactory(games_played=10, games_won=7)
        self.assertEqual(user.win_rate, 70.0)
        
        user = UserFactory(games_played=3, games_won=1)
        self.assertAlmostEqual(user.win_rate, 33.33, places=2)
    
    def test_losses_calculation(self):
        """Test losses property calculation."""
        user = UserFactory(games_played=10, games_won=3)
        self.assertEqual(user.losses, 7)
        
        user = UserFactory(games_played=0, games_won=0)
        self.assertEqual(user.losses, 0)
    
    def test_is_experienced_property(self):
        """Test is_experienced property (10+ games)."""
        user = UserFactory(games_played=5)
        self.assertFalse(user.is_experienced)
        
        user = UserFactory(games_played=10)
        self.assertTrue(user.is_experienced)
        
        user = UserFactory(games_played=15)
        self.assertTrue(user.is_experienced)
    
    def test_update_game_stats_won(self):
        """Test updating statistics when user wins."""
        user = UserFactory(games_played=5, games_won=2)
        user.update_game_stats(won=True)
        
        user.refresh_from_db()
        self.assertEqual(user.games_played, 6)
        self.assertEqual(user.games_won, 3)
    
    def test_update_game_stats_lost(self):
        """Test updating statistics when user loses."""
        user = UserFactory(games_played=5, games_won=2)
        user.update_game_stats(won=False)
        
        user.refresh_from_db()
        self.assertEqual(user.games_played, 6)
        self.assertEqual(user.games_won, 2)
    
    def test_reset_stats(self):
        """Test resetting game statistics."""
        user = UserFactory(games_played=10, games_won=7)
        user.reset_stats()
        
        user.refresh_from_db()
        self.assertEqual(user.games_played, 0)
        self.assertEqual(user.games_won, 0)
    
    def test_str_method_with_display_name(self):
        """Test string representation with display name."""
        user = UserFactory(username='testuser', display_name='Test User')
        self.assertEqual(str(user), 'Test User')
    
    def test_str_method_without_display_name(self):
        """Test string representation without display name."""
        user = UserFactory(username='testuser', display_name='')
        self.assertEqual(str(user), 'testuser')
    
    def test_user_soft_deletion(self):
        """Test user soft deletion via is_active flag."""
        user = UserFactory()
        self.assertTrue(user.is_active)
        
        user.is_active = False
        user.save()
        
        user.refresh_from_db()
        self.assertFalse(user.is_active)
    
    def test_username_stripping_whitespace(self):
        """Test that username whitespace is stripped."""
        user = User.objects.create(username='  testuser  ')
        self.assertEqual(user.username, 'testuser')
    
    def test_email_stripping_whitespace(self):
        """Test that email whitespace is stripped."""
        user = User.objects.create(username='testuser', email='  test@example.com  ')
        self.assertEqual(user.email, 'test@example.com')
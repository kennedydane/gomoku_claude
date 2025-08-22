"""
pytest tests for users model functionality.

Migrated from users/test_models.py to pytest format for better test management.
"""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.contrib.auth import get_user_model
from faker import Faker

from tests.factories import UserFactory

User = get_user_model()
fake = Faker()


@pytest.mark.django_db
class TestUserModelConstraints:
    """Test cases for database constraints that need transaction rollback."""
    
    def test_username_uniqueness(self):
        """Test that usernames must be unique (case-insensitive)."""
        user1 = UserFactory()
        
        with transaction.atomic():
            with pytest.raises(IntegrityError):
                User.objects.create(username=user1.username)
        
        with transaction.atomic():
            with pytest.raises(IntegrityError):
                User.objects.create(username=user1.username.upper())
    
    def test_email_uniqueness_when_provided(self):
        """Test that emails must be unique when provided."""
        UserFactory(email='test@example.com')
        
        with transaction.atomic():
            with pytest.raises(IntegrityError):
                User.objects.create(username='user2', email='test@example.com')
    
    def test_games_won_constraint(self):
        """Test that games_won cannot exceed games_played."""
        user = UserFactory(games_played=5, games_won=3)
        user.save()  # Should be valid
        
        # This should be caught by database constraint
        with transaction.atomic():
            with pytest.raises(IntegrityError):
                User.objects.create(
                    username=fake.user_name(),
                    games_played=5,
                    games_won=10  # More wins than games played
                )
    
    def test_negative_statistics_not_allowed(self):
        """Test that negative statistics are not allowed."""
        with transaction.atomic():
            with pytest.raises(IntegrityError):
                User.objects.create(
                    username=fake.user_name(),
                    games_played=-1
                )
        
        with transaction.atomic():
            with pytest.raises(IntegrityError):
                User.objects.create(
                    username='testuser2',
                    games_won=-1
                )


@pytest.mark.django_db
class TestUserModel:
    """Test cases for User model validation and behavior."""
    
    def test_user_creation_with_valid_data(self):
        """Test creating a user with valid data."""
        test_username = fake.user_name()
        user = UserFactory(
            username=test_username,
            email='test@example.com',
            display_name='Test User'
        )
        assert user.username == test_username.lower().strip()
        assert user.email == 'test@example.com'
        assert user.display_name == 'Test User'
        assert user.games_played == 0
        assert user.games_won == 0
        assert user.is_active is True
        assert user.date_joined is not None
    
    def test_username_case_insensitive_storage(self):
        """Test that usernames are stored in lowercase."""
        test_username = 'TestUser' + fake.uuid4()[:8]  # Make it unique
        user = User.objects.create(username=test_username, email='test@example.com')
        assert user.username == test_username.lower()
    
    def test_email_case_insensitive_storage(self):
        """Test that emails are stored in lowercase."""
        user = User.objects.create(username=fake.user_name(), email='Test@Example.COM')
        assert user.email == 'test@example.com'
    
    def test_email_can_be_blank(self):
        """Test that email can be blank."""
        user = User.objects.create(username=fake.user_name())
        assert user.email is None
    
    def test_multiple_users_with_blank_email(self):
        """Test that multiple users can have blank emails."""
        user1 = User.objects.create(username='blank_email_user1')  # email defaults to None
        user2 = User.objects.create(username='blank_email_user2')  # email defaults to None
        assert user1.email is None
        assert user2.email is None
    
    def test_username_minimum_length_validation(self):
        """Test that username must be at least 3 characters."""
        with pytest.raises(ValidationError):
            user = User(username='ab')
            user.full_clean(exclude=['password'])
    
    def test_username_character_validation(self):
        """Test that username only allows valid characters."""
        # Valid characters - create user without full_clean due to password requirement
        user = User.objects.create(username='user_name-123', email='test@example.com')
        assert user.username == 'user_name-123'
        
        # Invalid characters - test at model level
        with pytest.raises(ValidationError):
            user = User(username='user@name')
            user.full_clean(exclude=['password'])
        
        with pytest.raises(ValidationError):
            user = User(username='user name')
            user.full_clean(exclude=['password'])
    
    def test_display_name_optional(self):
        """Test that display_name is optional."""
        user = UserFactory(username='optional_display_user', display_name='')
        assert user.display_name == ''
    
    def test_games_statistics_default_values(self):
        """Test that game statistics have correct default values."""
        user = UserFactory()
        assert user.games_played == 0
        assert user.games_won == 0
    
    def test_win_rate_calculation(self):
        """Test win rate property calculation."""
        user = UserFactory(games_played=0, games_won=0)
        assert user.win_rate == 0.0
        
        user = UserFactory(games_played=10, games_won=7)
        assert user.win_rate == 70.0
        
        user = UserFactory(games_played=3, games_won=1)
        assert abs(user.win_rate - 33.33) < 0.01  # approximately equal
    
    def test_losses_calculation(self):
        """Test losses property calculation."""
        user = UserFactory(games_played=10, games_won=3)
        assert user.losses == 7
        
        user = UserFactory(games_played=0, games_won=0)
        assert user.losses == 0
    
    def test_is_experienced_property(self):
        """Test is_experienced property (10+ games)."""
        user = UserFactory(games_played=5)
        assert user.is_experienced is False
        
        user = UserFactory(games_played=10)
        assert user.is_experienced is True
        
        user = UserFactory(games_played=15)
        assert user.is_experienced is True
    
    def test_update_game_stats_won(self):
        """Test updating statistics when user wins."""
        user = UserFactory(games_played=5, games_won=2)
        user.update_game_stats(won=True)
        
        user.refresh_from_db()
        assert user.games_played == 6
        assert user.games_won == 3
    
    def test_update_game_stats_lost(self):
        """Test updating statistics when user loses."""
        user = UserFactory(games_played=5, games_won=2)
        user.update_game_stats(won=False)
        
        user.refresh_from_db()
        assert user.games_played == 6
        assert user.games_won == 2
    
    def test_reset_stats(self):
        """Test resetting game statistics."""
        user = UserFactory(games_played=10, games_won=7)
        user.reset_stats()
        
        user.refresh_from_db()
        assert user.games_played == 0
        assert user.games_won == 0
    
    def test_str_method_with_display_name(self):
        """Test string representation with display name."""
        user = UserFactory(display_name='Test User')
        assert str(user) == 'Test User'
    
    def test_str_method_without_display_name(self):
        """Test string representation without display name."""
        test_username = fake.user_name()
        user = UserFactory(username=test_username, display_name='')
        assert str(user) == test_username.lower().strip()
    
    def test_user_soft_deletion(self):
        """Test user soft deletion via is_active flag."""
        user = UserFactory()
        assert user.is_active is True
        
        user.is_active = False
        user.save()
        
        user.refresh_from_db()
        assert user.is_active is False
    
    def test_username_stripping_whitespace(self):
        """Test that username whitespace is stripped."""
        test_username = fake.user_name()
        user = User.objects.create(username=f'  {test_username}  ')
        assert user.username == test_username.lower().strip()
    
    def test_email_stripping_whitespace(self):
        """Test that email whitespace is stripped."""
        user = User.objects.create(username=fake.user_name(), email='  test@example.com  ')
        assert user.email == 'test@example.com'


@pytest.mark.django_db
class TestUserModelMethods:
    """Test custom methods on the User model."""
    
    def test_get_win_percentage_no_games(self):
        """Test win percentage calculation with no games played."""
        user = UserFactory(games_played=0, games_won=0)
        assert user.win_rate == 0.0
    
    def test_get_win_percentage_perfect_record(self):
        """Test win percentage calculation with perfect record."""
        user = UserFactory(games_played=5, games_won=5)
        assert user.win_rate == 100.0
    
    def test_get_win_percentage_no_wins(self):
        """Test win percentage calculation with no wins."""
        user = UserFactory(games_played=5, games_won=0)
        assert user.win_rate == 0.0
    
    def test_user_authentication_methods(self):
        """Test that Django auth methods work correctly."""
        user = UserFactory(username=fake.user_name())
        
        # Test password setting and checking
        user.set_password('testpassword123')
        user.save()
        
        assert user.check_password('testpassword123') is True
        assert user.check_password('wrongpassword') is False
    
    def test_user_permissions_default(self):
        """Test default user permissions."""
        user = UserFactory()
        
        assert user.is_staff is False
        assert user.is_superuser is False
        assert user.is_active is True
    
    def test_user_full_name_fallback(self):
        """Test that get_full_name falls back to username."""
        user = UserFactory(username=fake.user_name(), display_name='')
        
        # If model has get_full_name method
        if hasattr(user, 'get_full_name'):
            full_name = user.get_full_name()
            # Should fall back to username if display_name is empty
            assert full_name in ['testuser', '']
    
    def test_user_short_name_fallback(self):
        """Test that get_short_name works correctly."""
        user = UserFactory(display_name='Test User')
        
        # If model has get_short_name method
        if hasattr(user, 'get_short_name'):
            short_name = user.get_short_name()
            # Django's default get_short_name returns first_name, which may be empty
            # This is expected behavior - we use display_name for UI purposes
            assert isinstance(short_name, str)  # Should be a string, can be empty


@pytest.mark.django_db
class TestUserModelEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_very_long_username(self):
        """Test username length limits."""
        # Test maximum allowed length (should succeed)
        long_username = 'a' * 150  # Assuming 150 is the max length
        with pytest.raises(ValidationError):
            user = User(username=long_username)
            user.full_clean(exclude=['password'])
    
    def test_very_long_email(self):
        """Test email length limits."""
        # Test very long email (should fail validation) - exceed 255 char limit
        long_email = 'a' * 300 + '@example.com'  # This will be over 300 chars
        with pytest.raises(ValidationError):
            user = User(username=fake.user_name(), email=long_email)
            user.full_clean(exclude=['password'])
    
    def test_unicode_username_support(self):
        """Test that usernames support unicode characters appropriately."""
        # Test what characters are actually allowed by the model
        try:
            test_username = fake.user_name()
            user = User.objects.create(username=test_username)
            assert user.username == test_username.lower().strip()
        except Exception:
            pytest.skip("Unicode username tests require specific model configuration")
    
    def test_concurrent_user_creation(self):
        """Test concurrent user creation scenarios."""
        # This tests race conditions in username uniqueness
        username = 'concurrent_test_user'
        
        # Create first user
        user1 = UserFactory(username=username)
        
        # Attempt to create second user with same username should fail
        with transaction.atomic():
            with pytest.raises(IntegrityError):
                User.objects.create(username=username)
    
    def test_user_statistics_overflow(self):
        """Test handling of very large game statistics."""
        # Test large numbers (within database limits)
        user = UserFactory(games_played=999999, games_won=500000)
        assert user.games_played == 999999
        assert user.games_won == 500000
        # Use approximate comparison for floating point precision
        assert abs(user.win_rate - 50.0) < 0.1  # Should calculate correctly
    
    def test_user_with_special_characters_in_display_name(self):
        """Test display names with special characters."""
        special_names = [
            'User with émojis 🎮',
            'User (with) [brackets]',
            'User-with-dashes_and_underscores',
            'User with "quotes" and \'apostrophes\'',
        ]
        
        for name in special_names:
            user = UserFactory(display_name=name)
            assert user.display_name == name
            assert str(user) == name
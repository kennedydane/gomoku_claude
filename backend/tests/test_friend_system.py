"""
Tests for Friend System Backend

Comprehensive pytest-style tests for friendship functionality:
- Friendship model tests
- Friendship manager tests
- Friend API endpoint tests
- Friend web view tests
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from rest_framework import status

from web.models import Friendship, FriendshipStatus
from tests.factories import UserFactory
import factory

User = get_user_model()


@pytest.mark.django_db
class TestFriendshipModel:
    """Tests for the Friendship model."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test data."""
        self.user1 = UserFactory()
        self.user2 = UserFactory()
        self.user3 = UserFactory()
    
    def test_friendship_creation(self):
        """Test creating a friendship with default PENDING status."""
        friendship = Friendship.objects.create(
            requester=self.user1,
            addressee=self.user2
        )
        
        assert friendship.requester == self.user1
        assert friendship.addressee == self.user2
        assert friendship.status == 'PENDING'
        assert friendship.created_at is not None
    
    def test_friendship_unique_constraint(self):
        """Test that duplicate friendships are prevented."""
        # Create first friendship
        Friendship.objects.create(requester=self.user1, addressee=self.user2)
        
        # Attempt duplicate should fail
        with pytest.raises(IntegrityError):
            Friendship.objects.create(requester=self.user1, addressee=self.user2)
    
    def test_friendship_reverse_unique_constraint(self):
        """Test that reverse duplicate friendships are prevented."""
        Friendship.objects.create(requester=self.user1, addressee=self.user2)
        
        # Reverse should also fail (user2 -> user1 when user1 -> user2 exists)
        with pytest.raises(ValidationError):
            Friendship.objects.create(requester=self.user2, addressee=self.user1)
    
    def test_friendship_self_constraint(self):
        """Test that users cannot befriend themselves."""
        with pytest.raises(ValidationError):
            Friendship.objects.create(requester=self.user1, addressee=self.user1)
    
    def test_friendship_status_choices(self):
        """Test valid status transitions."""
        friendship = Friendship.objects.create(
            requester=self.user1,
            addressee=self.user2
        )
        
        # Test PENDING -> ACCEPTED
        friendship.status = FriendshipStatus.ACCEPTED
        friendship.save()
        assert friendship.status == FriendshipStatus.ACCEPTED
        
        # Test PENDING -> REJECTED  
        friendship.status = FriendshipStatus.REJECTED
        friendship.save()
        assert friendship.status == FriendshipStatus.REJECTED
    
    def test_friendship_str_representation(self):
        """Test string representation of friendship."""
        friendship = Friendship.objects.create(
            requester=self.user1,
            addressee=self.user2
        )
        
        expected = f"{self.user1.username} -> {self.user2.username} (PENDING)"
        assert str(friendship) == expected


@pytest.mark.django_db
class TestFriendshipManager:
    """Tests for custom Friendship manager methods."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test data."""
        self.user1 = UserFactory()
        self.user2 = UserFactory()
        self.user3 = UserFactory()
    
    def test_get_friends(self):
        """Test getting all friends for a user."""
        # Create accepted friendship
        Friendship.objects.create(
            requester=self.user1,
            addressee=self.user2,
            status=FriendshipStatus.ACCEPTED
        )
        
        # Create pending friendship (should not appear in friends)
        Friendship.objects.create(
            requester=self.user1,
            addressee=self.user3,
            status=FriendshipStatus.PENDING
        )
        
        friends = Friendship.objects.get_friends(self.user1)
        assert friends.count() == 1
        assert self.user2 in friends
        assert self.user3 not in friends
    
    def test_get_pending_requests(self):
        """Test getting pending friend requests for a user."""
        # Create pending request TO user1
        Friendship.objects.create(
            requester=self.user2,
            addressee=self.user1,
            status=FriendshipStatus.PENDING
        )
        
        # Create pending request FROM user1
        Friendship.objects.create(
            requester=self.user1,
            addressee=self.user3,
            status=FriendshipStatus.PENDING
        )
        
        pending_requests = Friendship.objects.get_pending_requests(self.user1)
        assert pending_requests.count() == 1
        assert pending_requests.first().requester == self.user2
    
    def test_are_friends(self):
        """Test checking if two users are friends."""
        # Not friends initially
        assert not Friendship.objects.are_friends(self.user1, self.user2)
        
        # Create accepted friendship
        Friendship.objects.create(
            requester=self.user1,
            addressee=self.user2,
            status=FriendshipStatus.ACCEPTED
        )
        
        # Should be friends now (both directions)
        assert Friendship.objects.are_friends(self.user1, self.user2)
        assert Friendship.objects.are_friends(self.user2, self.user1)


@pytest.mark.django_db
class TestFriendAPI:
    """Tests for Friend API endpoints."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test data."""
        self.user1 = UserFactory()
        self.user2 = UserFactory()
        self.user3 = UserFactory()
        
        # Set password for login
        self.user1.set_password('testpass123')
        self.user1.save()
    
    def test_send_friend_request_endpoint(self, client):
        """Test sending a friend request via API."""
        client.force_login(self.user1)
        
        url = reverse('web:send_friend_request')
        data = {'username': self.user2.username}
        
        response = client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        
        # Check that friendship was created
        friendship = Friendship.objects.get(requester=self.user1, addressee=self.user2)
        assert friendship.status == FriendshipStatus.PENDING
    
    def test_send_friend_request_to_nonexistent_user(self, client):
        """Test sending friend request to non-existent user."""
        client.force_login(self.user1)
        
        url = reverse('web:send_friend_request')
        data = {'username': 'nonexistent'}
        
        response = client.post(url, data)
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_send_friend_request_to_self(self, client):
        """Test sending friend request to self."""
        client.force_login(self.user1)
        
        url = reverse('web:send_friend_request')
        data = {'username': self.user1.username}
        
        response = client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_data = response.json()
        assert 'yourself' in response_data['error'].lower()
    
    def test_duplicate_friend_request(self, client):
        """Test sending duplicate friend request."""
        # Create existing friendship
        Friendship.objects.create(requester=self.user1, addressee=self.user2)
        
        client.force_login(self.user1)
        url = reverse('web:send_friend_request')
        data = {'username': self.user2.username}
        
        response = client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_data = response.json()
        assert 'already' in response_data['error'].lower()
    
    def test_respond_to_friend_request_accept(self, client):
        """Test accepting a friend request."""
        # Create pending friendship
        friendship = Friendship.objects.create(
            requester=self.user2,
            addressee=self.user1,
            status=FriendshipStatus.PENDING
        )
        
        client.force_login(self.user1)
        url = reverse('web:respond_friend_request', kwargs={'friendship_id': friendship.id})
        data = {'action': 'accept'}
        
        response = client.post(url, data)
        assert response.status_code == status.HTTP_200_OK
        
        friendship.refresh_from_db()
        assert friendship.status == FriendshipStatus.ACCEPTED
    
    def test_respond_to_friend_request_reject(self, client):
        """Test rejecting a friend request."""
        friendship = Friendship.objects.create(
            requester=self.user2,
            addressee=self.user1,
            status=FriendshipStatus.PENDING
        )
        
        client.force_login(self.user1)
        url = reverse('web:respond_friend_request', kwargs={'friendship_id': friendship.id})
        data = {'action': 'reject'}
        
        response = client.post(url, data)
        assert response.status_code == status.HTTP_200_OK
        
        friendship.refresh_from_db()
        assert friendship.status == FriendshipStatus.REJECTED
    
    def test_respond_to_nonexistent_request(self, client):
        """Test responding to non-existent friend request."""
        client.force_login(self.user1)
        url = reverse('web:respond_friend_request', kwargs={'friendship_id': 99999})
        data = {'action': 'accept'}
        
        response = client.post(url, data)
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_respond_to_others_request(self, client):
        """Test responding to someone else's friend request."""
        # Create friendship between user2 and user3
        friendship = Friendship.objects.create(
            requester=self.user2,
            addressee=self.user3
        )
        
        # Try to respond as user1 (should fail)
        client.force_login(self.user1)
        url = reverse('web:respond_friend_request', kwargs={'friendship_id': friendship.id})
        data = {'action': 'accept'}
        
        response = client.post(url, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_get_friends_list(self, client):
        """Test getting user's friends list."""
        # Create accepted friendship
        Friendship.objects.create(
            requester=self.user1,
            addressee=self.user2,
            status=FriendshipStatus.ACCEPTED
        )
        
        client.force_login(self.user1)
        url = reverse('web:friends_list')
        
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert len(response_data) == 1
        assert response_data[0]['username'] == self.user2.username
    
    def test_get_pending_requests_list(self, client):
        """Test getting pending friend requests."""
        # Create pending request TO user1
        Friendship.objects.create(
            requester=self.user2,
            addressee=self.user1,
            status=FriendshipStatus.PENDING
        )
        
        client.force_login(self.user1)
        url = reverse('web:pending_requests')
        
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert len(response_data) == 1
        assert response_data[0]['requester']['username'] == self.user2.username
    
    def test_search_users(self, client):
        """Test searching for users to befriend."""
        # Create more users with unique search patterns
        alice = UserFactory(username='alice_unique')
        bob = UserFactory(username='bob_unique')
        charlie = UserFactory(username='charlie_unique')
        
        client.force_login(self.user1)
        url = reverse('web:search_users')
        
        # Search by partial username
        response = client.get(url, {'q': 'alice_'})
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert len(response_data) == 1
        assert response_data[0]['username'] == 'alice_unique'
    
    def test_authentication_required(self, client):
        """Test that authentication is required for all friend endpoints."""
        endpoints = [
            ('web:send_friend_request', 'post', {}),
            ('web:friends_list', 'get', None),
            ('web:pending_requests', 'get', None),
            ('web:search_users', 'get', None),
        ]
        
        for endpoint_name, method, data in endpoints:
            url = reverse(endpoint_name)
            if method == 'post':
                response = client.post(url, data or {})
            else:
                response = client.get(url)
            
            assert response.status_code in [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
                status.HTTP_302_FOUND  # Redirect to login
            ]


@pytest.mark.django_db
class TestFriendWebViews:
    """Tests for web interface views for friends."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test data."""
        self.user1 = UserFactory()
        self.user2 = UserFactory()
        
        self.user1.set_password('testpass123')
        self.user1.save()
    
    def test_friends_page_renders(self, client):
        """Test friends page renders correctly."""
        client.force_login(self.user1)
        
        url = reverse('web:friends')
        response = client.get(url)
        
        assert response.status_code == 200
        assert 'Friends' in response.content.decode()
        assert 'Send Request' in response.content.decode()
    
    def test_friends_page_shows_friends(self, client):
        """Test friends page displays user's friends."""
        # Create accepted friendship
        Friendship.objects.create(
            requester=self.user1,
            addressee=self.user2,
            status=FriendshipStatus.ACCEPTED
        )
        
        client.force_login(self.user1)
        url = reverse('web:friends')
        response = client.get(url)
        
        assert response.status_code == 200
        assert self.user2.username in response.content.decode()
    
    def test_friends_page_shows_pending_requests(self, client):
        """Test friends page shows pending requests."""
        # Create pending request TO user1
        Friendship.objects.create(
            requester=self.user2,
            addressee=self.user1,
            status=FriendshipStatus.PENDING
        )
        
        client.force_login(self.user1)
        url = reverse('web:friends')
        response = client.get(url)
        
        assert response.status_code == 200
        content = response.content.decode()
        assert self.user2.username in content
        assert 'Accept' in content
        assert 'Reject' in content
    
    def test_friends_page_requires_authentication(self, client):
        """Test friends page requires login."""
        url = reverse('web:friends')
        response = client.get(url)
        
        assert response.status_code == 302
        assert 'login' in response.url
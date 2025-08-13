"""
TDD Tests for Friend System Backend.

Following Red-Green-Refactor methodology:
1. RED: Write failing tests for friendship functionality
2. GREEN: Implement minimal code to pass tests
3. REFACTOR: Improve code quality while keeping tests green
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from tests.factories import UserFactory

User = get_user_model()


class FriendshipModelTests(TestCase):
    """RED: Test the Friendship model."""
    
    def setUp(self):
        """Set up test data."""
        self.user1 = UserFactory(username='user1')
        self.user2 = UserFactory(username='user2')
        self.user3 = UserFactory(username='user3')
    
    def test_friendship_creation(self):
        """RED: Test creating a friendship with default PENDING status."""
        # This will FAIL - Friendship model doesn't exist yet
        from web.models import Friendship
        
        friendship = Friendship.objects.create(
            requester=self.user1,
            addressee=self.user2
        )
        
        self.assertEqual(friendship.requester, self.user1)
        self.assertEqual(friendship.addressee, self.user2)
        self.assertEqual(friendship.status, 'PENDING')
        self.assertIsNotNone(friendship.created_at)
    
    def test_friendship_unique_constraint(self):
        """RED: Test that duplicate friendships are prevented."""
        from web.models import Friendship
        
        # Create first friendship
        Friendship.objects.create(requester=self.user1, addressee=self.user2)
        
        # Attempt duplicate should fail
        with self.assertRaises(IntegrityError):
            Friendship.objects.create(requester=self.user1, addressee=self.user2)
    
    def test_friendship_reverse_unique_constraint(self):
        """RED: Test that reverse duplicate friendships are prevented."""
        from web.models import Friendship
        from django.core.exceptions import ValidationError
        
        Friendship.objects.create(requester=self.user1, addressee=self.user2)
        
        # Reverse should also fail (user2 -> user1 when user1 -> user2 exists)
        with self.assertRaises(ValidationError):
            Friendship.objects.create(requester=self.user2, addressee=self.user1)
    
    def test_friendship_self_constraint(self):
        """RED: Test that users cannot befriend themselves."""
        from web.models import Friendship
        from django.core.exceptions import ValidationError
        
        with self.assertRaises(ValidationError):
            Friendship.objects.create(requester=self.user1, addressee=self.user1)
    
    def test_friendship_status_choices(self):
        """RED: Test valid status transitions."""
        from web.models import Friendship, FriendshipStatus
        
        friendship = Friendship.objects.create(
            requester=self.user1,
            addressee=self.user2
        )
        
        # Test PENDING -> ACCEPTED
        friendship.status = FriendshipStatus.ACCEPTED
        friendship.save()
        self.assertEqual(friendship.status, FriendshipStatus.ACCEPTED)
        
        # Test PENDING -> REJECTED  
        friendship.status = FriendshipStatus.REJECTED
        friendship.save()
        self.assertEqual(friendship.status, FriendshipStatus.REJECTED)
    
    def test_friendship_str_representation(self):
        """RED: Test string representation of friendship."""
        from web.models import Friendship
        
        friendship = Friendship.objects.create(
            requester=self.user1,
            addressee=self.user2
        )
        
        expected = f"{self.user1.username} -> {self.user2.username} (PENDING)"
        self.assertEqual(str(friendship), expected)


class FriendshipManagerTests(TestCase):
    """RED: Test custom Friendship manager methods."""
    
    def setUp(self):
        """Set up test data."""
        self.user1 = UserFactory(username='user1')
        self.user2 = UserFactory(username='user2')
        self.user3 = UserFactory(username='user3')
    
    def test_get_friends(self):
        """RED: Test getting all friends for a user."""
        from web.models import Friendship, FriendshipStatus
        
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
        self.assertEqual(friends.count(), 1)
        self.assertIn(self.user2, friends)
        self.assertNotIn(self.user3, friends)
    
    def test_get_pending_requests(self):
        """RED: Test getting pending friend requests for a user."""
        from web.models import Friendship, FriendshipStatus
        
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
        self.assertEqual(pending_requests.count(), 1)
        self.assertEqual(pending_requests.first().requester, self.user2)
    
    def test_are_friends(self):
        """RED: Test checking if two users are friends."""
        from web.models import Friendship, FriendshipStatus
        
        # Not friends initially
        self.assertFalse(Friendship.objects.are_friends(self.user1, self.user2))
        
        # Create accepted friendship
        Friendship.objects.create(
            requester=self.user1,
            addressee=self.user2,
            status=FriendshipStatus.ACCEPTED
        )
        
        # Should be friends now (both directions)
        self.assertTrue(Friendship.objects.are_friends(self.user1, self.user2))
        self.assertTrue(Friendship.objects.are_friends(self.user2, self.user1))


class FriendAPITests(APITestCase):
    """RED: Test Friend API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user1 = UserFactory(username='user1')
        self.user2 = UserFactory(username='user2')
        self.user3 = UserFactory(username='user3')
        
        # Set password for login
        self.user1.set_password('testpass123')
        self.user1.save()
    
    def test_send_friend_request_endpoint(self):
        """RED: Test sending a friend request via API."""
        self.client.login(username='user1', password='testpass123')
        
        url = reverse('web:send_friend_request')
        data = {'username': 'user2'}
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check that friendship was created
        from web.models import Friendship, FriendshipStatus
        friendship = Friendship.objects.get(requester=self.user1, addressee=self.user2)
        self.assertEqual(friendship.status, FriendshipStatus.PENDING)
    
    def test_send_friend_request_to_nonexistent_user(self):
        """RED: Test sending friend request to non-existent user."""
        self.client.login(username='user1', password='testpass123')
        
        url = reverse('web:send_friend_request')
        data = {'username': 'nonexistent'}
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_send_friend_request_to_self(self):
        """RED: Test sending friend request to self."""
        self.client.login(username='user1', password='testpass123')
        
        url = reverse('web:send_friend_request')
        data = {'username': 'user1'}
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response_data = response.json()
        self.assertIn('yourself', response_data['error'].lower())
    
    def test_duplicate_friend_request(self):
        """RED: Test sending duplicate friend request."""
        from web.models import Friendship
        
        # Create existing friendship
        Friendship.objects.create(requester=self.user1, addressee=self.user2)
        
        self.client.login(username='user1', password='testpass123')
        url = reverse('web:send_friend_request')
        data = {'username': 'user2'}
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response_data = response.json()
        self.assertIn('already', response_data['error'].lower())
    
    def test_respond_to_friend_request_accept(self):
        """RED: Test accepting a friend request."""
        from web.models import Friendship, FriendshipStatus
        
        # Create pending friendship
        friendship = Friendship.objects.create(
            requester=self.user2,
            addressee=self.user1,
            status=FriendshipStatus.PENDING
        )
        
        self.client.login(username='user1', password='testpass123')
        url = reverse('web:respond_friend_request', kwargs={'friendship_id': friendship.id})
        data = {'action': 'accept'}
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        friendship.refresh_from_db()
        self.assertEqual(friendship.status, FriendshipStatus.ACCEPTED)
    
    def test_respond_to_friend_request_reject(self):
        """RED: Test rejecting a friend request."""
        from web.models import Friendship, FriendshipStatus
        
        friendship = Friendship.objects.create(
            requester=self.user2,
            addressee=self.user1,
            status=FriendshipStatus.PENDING
        )
        
        self.client.login(username='user1', password='testpass123')
        url = reverse('web:respond_friend_request', kwargs={'friendship_id': friendship.id})
        data = {'action': 'reject'}
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        friendship.refresh_from_db()
        self.assertEqual(friendship.status, FriendshipStatus.REJECTED)
    
    def test_respond_to_nonexistent_request(self):
        """RED: Test responding to non-existent friend request."""
        self.client.login(username='user1', password='testpass123')
        url = reverse('web:respond_friend_request', kwargs={'friendship_id': 99999})
        data = {'action': 'accept'}
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_respond_to_others_request(self):
        """RED: Test responding to someone else's friend request."""
        from web.models import Friendship
        
        # Create friendship between user2 and user3
        friendship = Friendship.objects.create(
            requester=self.user2,
            addressee=self.user3
        )
        
        # Try to respond as user1 (should fail)
        self.client.login(username='user1', password='testpass123')
        url = reverse('web:respond_friend_request', kwargs={'friendship_id': friendship.id})
        data = {'action': 'accept'}
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_get_friends_list(self):
        """RED: Test getting user's friends list."""
        from web.models import Friendship, FriendshipStatus
        
        # Create accepted friendship
        Friendship.objects.create(
            requester=self.user1,
            addressee=self.user2,
            status=FriendshipStatus.ACCEPTED
        )
        
        self.client.login(username='user1', password='testpass123')
        url = reverse('web:friends_list')
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(len(response_data), 1)
        self.assertEqual(response_data[0]['username'], 'user2')
    
    def test_get_pending_requests_list(self):
        """RED: Test getting pending friend requests."""
        from web.models import Friendship, FriendshipStatus
        
        # Create pending request TO user1
        Friendship.objects.create(
            requester=self.user2,
            addressee=self.user1,
            status=FriendshipStatus.PENDING
        )
        
        self.client.login(username='user1', password='testpass123')
        url = reverse('web:pending_requests')
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(len(response_data), 1)
        self.assertEqual(response_data[0]['requester']['username'], 'user2')
    
    def test_search_users(self):
        """RED: Test searching for users to befriend."""
        # Create more users
        UserFactory(username='alice')
        UserFactory(username='bob')
        UserFactory(username='charlie')
        
        self.client.login(username='user1', password='testpass123')
        url = reverse('web:search_users')
        
        # Search by partial username
        response = self.client.get(url, {'q': 'al'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(len(response_data), 1)
        self.assertEqual(response_data[0]['username'], 'alice')
    
    def test_authentication_required(self):
        """RED: Test that authentication is required for all friend endpoints."""
        endpoints = [
            ('web:send_friend_request', 'post', {}),
            ('web:friends_list', 'get', None),
            ('web:pending_requests', 'get', None),
            ('web:search_users', 'get', None),
        ]
        
        for endpoint_name, method, data in endpoints:
            url = reverse(endpoint_name)
            if method == 'post':
                response = self.client.post(url, data or {})
            else:
                response = self.client.get(url)
            
            self.assertIn(response.status_code, [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
                status.HTTP_302_FOUND  # Redirect to login
            ])


class FriendWebViewTests(TestCase):
    """RED: Test web interface views for friends."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user1 = UserFactory(username='user1')
        self.user2 = UserFactory(username='user2')
        
        self.user1.set_password('testpass123')
        self.user1.save()
    
    def test_friends_page_renders(self):
        """RED: Test friends page renders correctly."""
        self.client.login(username='user1', password='testpass123')
        
        url = reverse('web:friends')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Friends')
        self.assertContains(response, 'Send Request')
    
    def test_friends_page_shows_friends(self):
        """RED: Test friends page displays user's friends."""
        from web.models import Friendship, FriendshipStatus
        
        # Create accepted friendship
        Friendship.objects.create(
            requester=self.user1,
            addressee=self.user2,
            status=FriendshipStatus.ACCEPTED
        )
        
        self.client.login(username='user1', password='testpass123')
        url = reverse('web:friends')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'user2')
    
    def test_friends_page_shows_pending_requests(self):
        """RED: Test friends page shows pending requests."""
        from web.models import Friendship, FriendshipStatus
        
        # Create pending request TO user1
        Friendship.objects.create(
            requester=self.user2,
            addressee=self.user1,
            status=FriendshipStatus.PENDING
        )
        
        self.client.login(username='user1', password='testpass123')
        url = reverse('web:friends')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'user2')
        self.assertContains(response, 'Accept')
        self.assertContains(response, 'Reject')
    
    def test_friends_page_requires_authentication(self):
        """RED: Test friends page requires login."""
        url = reverse('web:friends')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)


# These tests will ALL FAIL initially - that's the RED phase!
# Next step: Implement minimal code to make them pass (GREEN phase)
"""
TDD Tests for Web Challenge System.

Following Red-Green-Refactor methodology:
1. RED: Write failing tests for challenge functionality
2. GREEN: Implement minimal code to pass tests
3. REFACTOR: Improve code quality while keeping tests green
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from games.models import Challenge, ChallengeStatus, RuleSet
from web.models import Friendship, FriendshipStatus
from tests.factories import UserFactory, RuleSetFactory
import json

User = get_user_model()


class ChallengeCreationTests(TestCase):
    """RED: Test challenge creation between friends."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.challenger = UserFactory(username='challenger')
        self.challenged = UserFactory(username='challenged')
        self.challenger.set_password('testpass123')
        self.challenged.set_password('testpass123')
        self.challenger.save()
        self.challenged.save()
        
        # Make them friends
        friendship = Friendship.objects.create(
            requester=self.challenger,
            addressee=self.challenged,
            status=FriendshipStatus.ACCEPTED
        )
        
        self.ruleset = RuleSetFactory(board_size=15)
    
    def test_challenge_friend_ajax_endpoint_exists(self):
        """RED: Test challenge creation endpoint exists."""
        self.client.login(username='challenger', password='testpass123')
        
        url = reverse('web:challenge_friend')
        response = self.client.post(url, {
            'username': 'challenged',
            'ruleset_id': self.ruleset.id
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        # Should return JSON response (not 404)
        self.assertNotEqual(response.status_code, 404)
        self.assertEqual(response['Content-Type'], 'application/json')
    
    def test_challenge_friend_creates_challenge(self):
        """RED: Test successful challenge creation."""
        self.client.login(username='challenger', password='testpass123')
        
        url = reverse('web:challenge_friend')
        response = self.client.post(url, {
            'username': 'challenged',
            'ruleset_id': self.ruleset.id
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('success', data)
        self.assertTrue(data['success'])
        self.assertIn('challenge_id', data)
        
        # Check challenge was created in database
        challenge = Challenge.objects.get(id=data['challenge_id'])
        self.assertEqual(challenge.challenger, self.challenger)
        self.assertEqual(challenge.challenged, self.challenged)
        self.assertEqual(challenge.status, ChallengeStatus.PENDING)
    
    def test_challenge_non_friend_rejected(self):
        """RED: Test challenge to non-friend is rejected."""
        stranger = UserFactory(username='stranger')
        stranger.set_password('testpass123')
        stranger.save()
        
        self.client.login(username='challenger', password='testpass123')
        
        url = reverse('web:challenge_friend')
        response = self.client.post(url, {
            'username': 'stranger',
            'ruleset_id': self.ruleset.id
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('friend', data['error'].lower())
    
    def test_challenge_nonexistent_user_rejected(self):
        """RED: Test challenge to nonexistent user is rejected."""
        self.client.login(username='challenger', password='testpass123')
        
        url = reverse('web:challenge_friend')
        response = self.client.post(url, {
            'username': 'nonexistent',
            'ruleset_id': self.ruleset.id
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('not found', data['error'].lower())
    
    def test_challenge_self_rejected(self):
        """RED: Test self-challenge is rejected."""
        self.client.login(username='challenger', password='testpass123')
        
        url = reverse('web:challenge_friend')
        response = self.client.post(url, {
            'username': 'challenger',
            'ruleset_id': self.ruleset.id
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('yourself', data['error'].lower())


class ChallengeResponseTests(TestCase):
    """RED: Test challenge acceptance and rejection."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.challenger = UserFactory(username='challenger')
        self.challenged = UserFactory(username='challenged')
        self.challenger.set_password('testpass123')
        self.challenged.set_password('testpass123')
        self.challenger.save()
        self.challenged.save()
        
        # Make them friends
        friendship = Friendship.objects.create(
            requester=self.challenger,
            addressee=self.challenged,
            status=FriendshipStatus.ACCEPTED
        )
        
        self.ruleset = RuleSetFactory(board_size=15)
        
        # Create a pending challenge
        self.challenge = Challenge.objects.create(
            challenger=self.challenger,
            challenged=self.challenged,
            status=ChallengeStatus.PENDING,
            expires_at=timezone.now() + timedelta(hours=24),
            ruleset=self.ruleset
        )
    
    def test_accept_challenge_endpoint_exists(self):
        """RED: Test challenge acceptance endpoint exists."""
        self.client.login(username='challenged', password='testpass123')
        
        url = reverse('web:respond_challenge', kwargs={'challenge_id': self.challenge.id})
        response = self.client.post(url, {
            'action': 'accept'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        # Should return JSON response (not 404)
        self.assertNotEqual(response.status_code, 404)
        self.assertEqual(response['Content-Type'], 'application/json')
    
    def test_accept_challenge_creates_game(self):
        """RED: Test accepting challenge creates a game."""
        self.client.login(username='challenged', password='testpass123')
        
        url = reverse('web:respond_challenge', kwargs={'challenge_id': self.challenge.id})
        response = self.client.post(url, {
            'action': 'accept'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('success', data)
        self.assertTrue(data['success'])
        self.assertIn('game_id', data)
        
        # Check challenge status updated
        self.challenge.refresh_from_db()
        self.assertEqual(self.challenge.status, ChallengeStatus.ACCEPTED)
        
        # Check game was created
        from games.models import Game, GameStatus
        game = Game.objects.get(id=data['game_id'])
        self.assertEqual(game.status, GameStatus.ACTIVE)
        self.assertIn(game.black_player, [self.challenger, self.challenged])
        self.assertIn(game.white_player, [self.challenger, self.challenged])
    
    def test_reject_challenge_updates_status(self):
        """RED: Test rejecting challenge updates status."""
        self.client.login(username='challenged', password='testpass123')
        
        url = reverse('web:respond_challenge', kwargs={'challenge_id': self.challenge.id})
        response = self.client.post(url, {
            'action': 'reject'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('success', data)
        self.assertTrue(data['success'])
        
        # Check challenge status updated
        self.challenge.refresh_from_db()
        self.assertEqual(self.challenge.status, ChallengeStatus.REJECTED)
        
        # Check no game was created
        from games.models import Game
        self.assertEqual(Game.objects.count(), 0)
    
    def test_wrong_user_cannot_respond(self):
        """RED: Test only challenged user can respond."""
        self.client.login(username='challenger', password='testpass123')  # Wrong user
        
        url = reverse('web:respond_challenge', kwargs={'challenge_id': self.challenge.id})
        response = self.client.post(url, {
            'action': 'accept'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('access denied', data['error'].lower())


class ChallengeJavaScriptIntegrationTests(TestCase):
    """RED: Test JavaScript integration with challenge system."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user1 = UserFactory(username='user1')
        self.user2 = UserFactory(username='user2')
        self.user1.set_password('testpass123')
        self.user1.save()
        
        # Make them friends
        friendship = Friendship.objects.create(
            requester=self.user1,
            addressee=self.user2,
            status=FriendshipStatus.ACCEPTED
        )
    
    def test_friends_page_has_challenge_javascript(self):
        """RED: Test friends page includes challenge JavaScript functions."""
        self.client.login(username='user1', password='testpass123')
        
        url = reverse('web:friends')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Should have challengeUser function (not placeholder)
        content = response.content.decode()
        self.assertIn('challengeUser', content)
        self.assertNotIn('Challenge feature coming soon', content)  # No more placeholder
    
    def test_challenge_button_triggers_modal(self):
        """RED: Test challenge button shows ruleset selection modal."""
        self.client.login(username='user1', password='testpass123')
        
        url = reverse('web:friends')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Should have modal for challenge options
        self.assertIn('challenge-modal', content)
        self.assertIn('ruleset', content.lower())


# These tests will ALL FAIL initially - that's the RED phase!
# Next step: Implement minimal code to make them pass (GREEN phase)
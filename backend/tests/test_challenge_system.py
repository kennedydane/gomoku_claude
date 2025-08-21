"""
pytest tests for Web Challenge System.

Migrated from web/test_challenge_system.py to pytest format for better test management.
Following TDD methodology with comprehensive challenge system coverage.
"""

import pytest
import json
from datetime import timedelta
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

from games.models import Game, GameStatus, Challenge, ChallengeStatus
from web.models import Friendship, FriendshipStatus
from tests.factories import UserFactory, GomokuRuleSetFactory

User = get_user_model()


@pytest.mark.django_db
class TestChallengeCreation:
    """pytest tests for challenge creation between friends."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test data."""
        self.client = Client()
        self.challenger = UserFactory(username='challenger')
        self.challenged = UserFactory(username='challenged')
        self.challenger.set_password('testpass123')
        self.challenged.set_password('testpass123')
        self.challenger.save()
        self.challenged.save()
        
        # Make them friends
        self.friendship = Friendship.objects.create(
            requester=self.challenger,
            addressee=self.challenged,
            status=FriendshipStatus.ACCEPTED
        )
        
        self.ruleset = GomokuRuleSetFactory(board_size=15)
    
    def test_challenge_friend_ajax_endpoint_exists(self):
        """Test challenge creation endpoint exists."""
        self.client.login(username='challenger', password='testpass123')
        
        url = reverse('web:challenge_friend')
        response = self.client.post(url, {
            'username': 'challenged',
            'ruleset_id': self.ruleset.id
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        # Should return JSON response (not 404)
        assert response.status_code != 404
        assert response['Content-Type'] == 'application/json'
    
    def test_challenge_friend_creates_challenge(self):
        """Test successful challenge creation."""
        self.client.login(username='challenger', password='testpass123')
        
        url = reverse('web:challenge_friend')
        response = self.client.post(url, {
            'username': 'challenged',
            'ruleset_id': self.ruleset.id
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        assert response.status_code == 200
        data = response.json()
        assert 'success' in data
        assert data['success'] is True
        assert 'challenge_id' in data
        
        # Check challenge was created in database
        challenge = Challenge.objects.get(id=data['challenge_id'])
        assert challenge.challenger == self.challenger
        assert challenge.challenged == self.challenged
        assert challenge.status == ChallengeStatus.PENDING
    
    def test_challenge_non_friend_rejected(self):
        """Test challenge to non-friend is rejected."""
        stranger = UserFactory(username='stranger')
        stranger.set_password('testpass123')
        stranger.save()
        
        self.client.login(username='challenger', password='testpass123')
        
        url = reverse('web:challenge_friend')
        response = self.client.post(url, {
            'username': 'stranger',
            'ruleset_id': self.ruleset.id
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        assert response.status_code == 400
        data = response.json()
        assert 'error' in data
        assert 'friend' in data['error'].lower()
    
    def test_challenge_nonexistent_user_rejected(self):
        """Test challenge to nonexistent user is rejected."""
        self.client.login(username='challenger', password='testpass123')
        
        url = reverse('web:challenge_friend')
        response = self.client.post(url, {
            'username': 'nonexistent',
            'ruleset_id': self.ruleset.id
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        assert response.status_code == 404
        data = response.json()
        assert 'error' in data
        assert 'not found' in data['error'].lower()
    
    def test_challenge_self_rejected(self):
        """Test self-challenge is rejected."""
        self.client.login(username='challenger', password='testpass123')
        
        url = reverse('web:challenge_friend')
        response = self.client.post(url, {
            'username': 'challenger',
            'ruleset_id': self.ruleset.id
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        assert response.status_code == 400
        data = response.json()
        assert 'error' in data
        assert 'yourself' in data['error'].lower()


@pytest.mark.django_db
class TestChallengeResponse:
    """pytest tests for challenge acceptance and rejection."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test data."""
        self.client = Client()
        self.challenger = UserFactory(username='challenger')
        self.challenged = UserFactory(username='challenged')
        self.challenger.set_password('testpass123')
        self.challenged.set_password('testpass123')
        self.challenger.save()
        self.challenged.save()
        
        # Make them friends
        self.friendship = Friendship.objects.create(
            requester=self.challenger,
            addressee=self.challenged,
            status=FriendshipStatus.ACCEPTED
        )
        
        self.ruleset = GomokuRuleSetFactory(board_size=15)
        
        # Create a pending challenge
        self.challenge = Challenge.objects.create(
            challenger=self.challenger,
            challenged=self.challenged,
            status=ChallengeStatus.PENDING,
            ruleset=self.ruleset
        )
    
    def test_accept_challenge_endpoint_exists(self):
        """Test challenge acceptance endpoint exists."""
        self.client.login(username='challenged', password='testpass123')
        
        url = reverse('web:respond_challenge', kwargs={'challenge_id': self.challenge.id})
        response = self.client.post(url, {
            'action': 'accept'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        # Should return JSON response (not 404)
        assert response.status_code != 404
        assert response['Content-Type'] == 'application/json'
    
    def test_accept_challenge_creates_game(self):
        """Test accepting challenge creates a game."""
        self.client.login(username='challenged', password='testpass123')
        
        url = reverse('web:respond_challenge', kwargs={'challenge_id': self.challenge.id})
        response = self.client.post(url, {
            'action': 'accept'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        assert response.status_code == 200
        data = response.json()
        assert 'success' in data
        assert data['success'] is True
        assert 'game_id' in data
        
        # Check challenge status updated
        self.challenge.refresh_from_db()
        assert self.challenge.status == ChallengeStatus.ACCEPTED
        
        # Check game was created
        game = Game.objects.get(id=data['game_id'])
        assert game.status == GameStatus.ACTIVE
        assert game.black_player in [self.challenger, self.challenged]
        assert game.white_player in [self.challenger, self.challenged]
    
    def test_reject_challenge_updates_status(self):
        """Test rejecting challenge updates status."""
        self.client.login(username='challenged', password='testpass123')
        
        url = reverse('web:respond_challenge', kwargs={'challenge_id': self.challenge.id})
        response = self.client.post(url, {
            'action': 'reject'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        assert response.status_code == 200
        data = response.json()
        assert 'success' in data
        assert data['success'] is True
        
        # Check challenge status updated
        self.challenge.refresh_from_db()
        assert self.challenge.status == ChallengeStatus.REJECTED
        
        # Check no game was created for this challenge
        # (Filter by the specific players to avoid counting games from other tests)
        assert Game.objects.filter(
            black_player__in=[self.challenger, self.challenged],
            white_player__in=[self.challenger, self.challenged]
        ).count() == 0
    
    def test_wrong_user_cannot_respond(self):
        """Test only challenged user can respond."""
        self.client.login(username='challenger', password='testpass123')  # Wrong user
        
        url = reverse('web:respond_challenge', kwargs={'challenge_id': self.challenge.id})
        response = self.client.post(url, {
            'action': 'accept'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        assert response.status_code == 403
        data = response.json()
        assert 'error' in data
        assert 'access denied' in data['error'].lower()

    def test_htmx_accept_challenge_returns_html(self):
        """Test HTMX challenge acceptance returns HTML response with redirect."""
        self.client.login(username='challenged', password='testpass123')
        
        url = reverse('web:respond_challenge', kwargs={'challenge_id': self.challenge.id})
        response = self.client.post(url, {
            'action': 'accept'
        }, HTTP_HX_REQUEST='true')  # Simulate HTMX request
        
        assert response.status_code == 200
        # Should be HTML content type, not JSON
        assert response['Content-Type'] == 'text/html; charset=utf-8'
        # Should have HX-Redirect header
        assert 'HX-Redirect' in response
        assert '/games/' in response['HX-Redirect']
        
        # Challenge should be accepted
        self.challenge.refresh_from_db()
        assert self.challenge.status == ChallengeStatus.ACCEPTED
        
        # Game should be created for these specific players
        games = Game.objects.filter(
            black_player__in=[self.challenger, self.challenged],
            white_player__in=[self.challenger, self.challenged]
        )
        assert games.count() == 1
        game = games.first()
        assert '/games/' in response['HX-Redirect']
        assert str(game.id) in response['HX-Redirect']

    def test_htmx_reject_challenge_returns_html(self):
        """Test HTMX challenge rejection returns HTML response."""
        self.client.login(username='challenged', password='testpass123')
        
        url = reverse('web:respond_challenge', kwargs={'challenge_id': self.challenge.id})
        response = self.client.post(url, {
            'action': 'reject'
        }, HTTP_HX_REQUEST='true')  # Simulate HTMX request
        
        assert response.status_code == 200
        # Should be HTML content type, not JSON
        assert response['Content-Type'] == 'text/html; charset=utf-8'
        
        # Challenge should be rejected
        self.challenge.refresh_from_db()
        assert self.challenge.status == ChallengeStatus.REJECTED
        
        # No game should be created for this challenge
        assert Game.objects.filter(
            black_player__in=[self.challenger, self.challenged],
            white_player__in=[self.challenger, self.challenged]
        ).count() == 0

    def test_challenge_appears_on_dashboard(self):
        """Test that an existing challenge appears on the challenged user's dashboard."""
        # Use the existing challenge from setUp (which is pending)
        
        # Login as the challenged user
        self.client.login(username='challenged', password='testpass123')
        
        # Check dashboard
        dashboard_url = reverse('web:dashboard')
        response = self.client.get(dashboard_url)
        assert response.status_code == 200
        
        # The challenge should appear on the dashboard
        assert str(self.challenge.id) in response.content.decode()
        assert self.challenger.username in response.content.decode()
    
    def test_dashboard_query_for_pending_challenges(self):
        """Test the dashboard query logic for pending challenges."""
        # Test the same query that DashboardView uses
        pending_challenges = Challenge.objects.prefetch_related('ruleset').select_related(
            'challenger', 'challenged'
        ).filter(
            challenged=self.challenged, 
            status=ChallengeStatus.PENDING
        )
        
        # Should find our test challenge
        assert pending_challenges.count() == 1
        assert pending_challenges.first() == self.challenge
    
    def test_htmx_challenge_acceptance_from_dashboard_works(self):
        """Test the exact HTMX flow from dashboard"""
        # Login as challenged user
        self.client.login(username='challenged', password='testpass123')
        
        # Try to accept the challenge using HTMX (simulating dashboard click)
        accept_url = reverse('web:respond_challenge', kwargs={'challenge_id': self.challenge.id})
        response = self.client.post(
            accept_url,
            {'action': 'accept'},
            HTTP_HX_REQUEST='true'
        )
        
        # Should succeed without CSRF errors
        assert response.status_code == 200
        assert 'HX-Redirect' in response
        
        # Verify challenge was accepted
        self.challenge.refresh_from_db()
        assert self.challenge.status == ChallengeStatus.ACCEPTED
        
        # Verify game was created for these specific players
        games = Game.objects.filter(
            black_player__in=[self.challenger, self.challenged],
            white_player__in=[self.challenger, self.challenged]
        )
        assert games.count() == 1


@pytest.mark.django_db
class TestChallengeGameIntegration:
    """pytest tests for challenge-to-game integration and SSE updates."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test data for game integration tests."""
        self.client = Client()
        self.challenger = UserFactory(username='challenger')
        self.challenged = UserFactory(username='challenged')
        self.challenger.set_password('testpass123')
        self.challenged.set_password('testpass123')
        self.challenger.save()
        self.challenged.save()
        
        # Make them friends
        self.friendship = Friendship.objects.create(
            requester=self.challenger,
            addressee=self.challenged,
            status=FriendshipStatus.ACCEPTED
        )
        
        self.ruleset = GomokuRuleSetFactory(board_size=15)
        
        # Create a pending challenge
        self.challenge = Challenge.objects.create(
            challenger=self.challenger,
            challenged=self.challenged,
            status=ChallengeStatus.PENDING,
            ruleset=self.ruleset
        )

    def test_sse_move_updates_board_correctly(self):
        """Test that SSE move updates render the board correctly with proper turn handling."""
        # Create a game from accepted challenge
        self.challenge.status = ChallengeStatus.ACCEPTED
        self.challenge.save()
        
        # Create game with challenger as black player
        game = Game.objects.create(
            black_player=self.challenger,
            white_player=self.challenged,
            ruleset_content_type_id=self.ruleset.get_content_type().id,
            ruleset_object_id=self.ruleset.id,
            status=GameStatus.ACTIVE
        )
        game.initialize_board()
        game.save()
        
        # Login as black player and make a move
        self.client.login(username=self.challenger.username, password='testpass123')
        
        move_url = reverse('web:game_move', kwargs={'game_id': game.id})
        response = self.client.post(
            move_url,
            {'row': 0, 'col': 0},
            HTTP_HX_REQUEST='true'
        )
        
        # Should succeed
        assert response.status_code == 200
        
        # The response should show the move was made (stone placed)
        response_content = response.content.decode()
        assert 'stone-black' in response_content
        assert 'Intersection 0, 0 - BLACK stone' in response_content
        
        # After black's move, it should be white's turn
        # Login as white player to verify they can see HTMX attributes for their turn
        self.client.login(username=self.challenged.username, password='testpass123')
        game_url = reverse('web:game_detail', kwargs={'game_id': game.id})
        response = self.client.get(game_url, follow=True)  # Follow redirect to dashboard
        
        response_content = response.content.decode()
        # White player should see HTMX attributes since it's their turn
        assert ('hx-include="[name=\'csrfmiddlewaretoken\']"' in response_content or
                'hx-post' in response_content or
                'game-board' in response_content)


@pytest.mark.django_db 
class TestChallengeValidation:
    """pytest tests for challenge validation and edge cases."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test data for validation tests."""
        self.client = Client()
        self.user1 = UserFactory(username='validator1')
        self.user2 = UserFactory(username='validator2')
        self.user1.set_password('testpass123')
        self.user2.set_password('testpass123')
        self.user1.save()
        self.user2.save()
        
        self.ruleset = GomokuRuleSetFactory(board_size=15)
    
    def test_challenge_requires_friendship(self):
        """Test that challenges require an existing friendship."""
        self.client.login(username='validator1', password='testpass123')
        
        url = reverse('web:challenge_friend')
        response = self.client.post(url, {
            'username': 'validator2',
            'ruleset_id': self.ruleset.id
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        # Should fail without friendship
        assert response.status_code == 400
        data = response.json()
        assert 'error' in data
        assert 'friend' in data['error'].lower()
    
    def test_challenge_requires_valid_ruleset(self):
        """Test that challenges require a valid ruleset."""
        # Make them friends first
        Friendship.objects.create(
            requester=self.user1,
            addressee=self.user2,
            status=FriendshipStatus.ACCEPTED
        )
        
        self.client.login(username='validator1', password='testpass123')
        
        url = reverse('web:challenge_friend')
        response = self.client.post(url, {
            'username': 'validator2',
            'ruleset_id': 99999  # Invalid ruleset ID
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        # Should fail with invalid ruleset
        assert response.status_code in [400, 404]
    
    def test_challenge_requires_authentication(self):
        """Test that challenges require user authentication."""
        url = reverse('web:challenge_friend')
        response = self.client.post(url, {
            'username': 'validator2',
            'ruleset_id': self.ruleset.id
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        # Should redirect to login or return 403
        assert response.status_code in [302, 403]
    
    def test_duplicate_challenge_prevention(self):
        """Test that duplicate challenges between same users are prevented."""
        # Make them friends
        Friendship.objects.create(
            requester=self.user1,
            addressee=self.user2,
            status=FriendshipStatus.ACCEPTED
        )
        
        # Create first challenge
        Challenge.objects.create(
            challenger=self.user1,
            challenged=self.user2,
            status=ChallengeStatus.PENDING,
            ruleset=self.ruleset
        )
        
        self.client.login(username='validator1', password='testpass123')
        
        # Try to create duplicate challenge
        url = reverse('web:challenge_friend')
        response = self.client.post(url, {
            'username': 'validator2',
            'ruleset_id': self.ruleset.id
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        # Should prevent duplicate
        assert response.status_code == 400
        data = response.json()
        assert 'error' in data
        assert 'pending' in data['error'].lower() or 'already' in data['error'].lower()


@pytest.mark.django_db
class TestChallengeCleanup:
    """pytest tests for challenge lifecycle and cleanup."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test data for cleanup tests."""
        self.client = Client()
        self.user1 = UserFactory(username='cleanup1')
        self.user2 = UserFactory(username='cleanup2')
        self.user1.set_password('testpass123')
        self.user2.set_password('testpass123')
        self.user1.save()
        self.user2.save()
        
        # Make them friends
        Friendship.objects.create(
            requester=self.user1,
            addressee=self.user2,
            status=FriendshipStatus.ACCEPTED
        )
        
        self.ruleset = GomokuRuleSetFactory(board_size=15)
    
    def test_challenge_cancellation_by_challenger(self):
        """Test that challenger can cancel pending challenges."""
        # Create challenge
        challenge = Challenge.objects.create(
            challenger=self.user1,
            challenged=self.user2,
            status=ChallengeStatus.PENDING,
            ruleset=self.ruleset
        )
        
        self.client.login(username='cleanup1', password='testpass123')
        
        # Cancel challenge
        url = reverse('web:respond_challenge', kwargs={'challenge_id': challenge.id})
        response = self.client.post(url, {
            'action': 'cancel'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        # Should succeed
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        
        # Challenge should be cancelled
        challenge.refresh_from_db()
        assert challenge.status == ChallengeStatus.CANCELLED
    
    def test_challenge_cleanup_after_acceptance(self):
        """Test challenge status updates correctly after acceptance."""
        challenge = Challenge.objects.create(
            challenger=self.user1,
            challenged=self.user2,
            status=ChallengeStatus.PENDING,
            ruleset=self.ruleset
        )
        
        self.client.login(username='cleanup2', password='testpass123')
        
        # Accept challenge
        url = reverse('web:respond_challenge', kwargs={'challenge_id': challenge.id})
        response = self.client.post(url, {
            'action': 'accept'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        assert response.status_code == 200
        
        # Challenge should be accepted and game created
        challenge.refresh_from_db()
        assert challenge.status == ChallengeStatus.ACCEPTED
        assert Game.objects.filter(
            black_player__in=[self.user1, self.user2],
            white_player__in=[self.user1, self.user2]
        ).count() == 1
    
    def test_challenge_status_transitions(self):
        """Test valid challenge status transitions."""
        challenge = Challenge.objects.create(
            challenger=self.user1,
            challenged=self.user2,
            status=ChallengeStatus.PENDING,
            ruleset=self.ruleset
        )
        
        # PENDING -> ACCEPTED
        challenge.status = ChallengeStatus.ACCEPTED
        challenge.save()
        assert challenge.status == ChallengeStatus.ACCEPTED
        
        # Create another for PENDING -> REJECTED
        challenge2 = Challenge.objects.create(
            challenger=self.user1,
            challenged=self.user2,
            status=ChallengeStatus.PENDING,
            ruleset=self.ruleset
        )
        
        challenge2.status = ChallengeStatus.REJECTED
        challenge2.save()
        assert challenge2.status == ChallengeStatus.REJECTED
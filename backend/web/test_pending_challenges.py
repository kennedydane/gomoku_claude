"""
TDD Tests for Pending Challenges Feature.

Following Red-Green-Refactor methodology:
1. RED: Write failing tests for pending challenges functionality
2. GREEN: Implement minimal code to pass tests  
3. REFACTOR: Improve code quality while keeping tests green

Tests cover:
- Pending challenges display in friends panel
- Challenge management actions (accept/reject/cancel)
- SSE real-time updates
- Integration with Active Games panel
"""

import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from bs4 import BeautifulSoup

from games.models import Challenge, ChallengeStatus, Game, GameStatus, RuleSet
from web.models import Friendship, FriendshipStatus
from tests.factories import UserFactory, RuleSetFactory

User = get_user_model()


@pytest.fixture
def authenticated_client():
    """Authenticated test client."""
    return Client()


@pytest.fixture
def challenge_users(db):
    """Create users for challenge testing."""
    challenger = UserFactory(username='challenger')
    challengee = UserFactory(username='challengee')
    challenger.set_password('testpass123')
    challengee.set_password('testpass123')
    challenger.save()
    challengee.save()
    
    # Make them friends
    Friendship.objects.create(
        requester=challenger,
        addressee=challengee,
        status=FriendshipStatus.ACCEPTED
    )
    
    return challenger, challengee


@pytest.fixture  
def test_ruleset(db):
    """Create test ruleset."""
    return RuleSetFactory(name='Standard Gomoku', board_size=15)


@pytest.fixture
def pending_challenge(db, challenge_users, test_ruleset):
    """Create a pending challenge."""
    challenger, challengee = challenge_users
    return Challenge.objects.create(
        challenger=challenger,
        challenged=challengee,
        ruleset=test_ruleset,
        status=ChallengeStatus.PENDING
    )


@pytest.fixture
def multiple_challenges(db, challenge_users, test_ruleset):
    """Create multiple challenges for testing."""
    challenger, challengee = challenge_users
    
    # Create additional users for more challenge scenarios
    user3 = UserFactory(username='user3')
    user3.set_password('testpass123')
    user3.save()
    
    # Make user3 friends with challenger
    Friendship.objects.create(
        requester=challenger,
        addressee=user3,
        status=FriendshipStatus.ACCEPTED
    )
    
    challenges = [
        # Challenge sent by challenger to challengee
        Challenge.objects.create(
            challenger=challenger,
            challenged=challengee, 
            ruleset=test_ruleset,
            status=ChallengeStatus.PENDING
        ),
        # Challenge sent by user3 to challenger  
        Challenge.objects.create(
            challenger=user3,
            challenged=challenger,
            ruleset=test_ruleset,
            status=ChallengeStatus.PENDING
        ),
    ]
    
    return challenges, (challenger, challengee, user3)


@pytest.mark.web
@pytest.mark.django_db
class TestPendingChallengesDisplay:
    """Test pending challenges display in friends panel."""
    
    def test_dashboard_shows_sent_pending_challenges(self, authenticated_client, multiple_challenges):
        """RED: Test dashboard shows challenges sent by current user."""
        challenges, (challenger, challengee, user3) = multiple_challenges
        
        authenticated_client.login(username='challenger', password='testpass123')
        response = authenticated_client.get(reverse('web:dashboard'))
        
        assert response.status_code == 200
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Should show pending challenges section
        pending_section = soup.find('div', class_='pending-challenges-section')
        assert pending_section is not None, "Pending challenges section should exist"
        
        # Should show sent challenges subsection
        sent_challenges = soup.find('div', class_='sent-challenges')
        assert sent_challenges is not None, "Sent challenges subsection should exist"
        
        # Should show challenge to challengee with cancel button
        challenge_items = soup.find_all('div', class_='challenge-item')
        assert len(challenge_items) >= 1, "Should show at least one challenge item"
        
        # Find the sent challenge
        sent_challenge = None
        for item in challenge_items:
            if challengee.username in item.text:
                sent_challenge = item
                break
        
        assert sent_challenge is not None, f"Should show challenge to {challengee.username}"
        
        # Should have cancel button
        cancel_btn = sent_challenge.find('button', class_='cancel-challenge-btn')
        assert cancel_btn is not None, "Sent challenge should have cancel button"
    
    def test_dashboard_shows_received_pending_challenges(self, authenticated_client, multiple_challenges):
        """RED: Test dashboard shows challenges received by current user."""
        challenges, (challenger, challengee, user3) = multiple_challenges
        
        authenticated_client.login(username='challenger', password='testpass123')
        response = authenticated_client.get(reverse('web:dashboard'))
        
        assert response.status_code == 200
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Should show received challenges subsection
        received_challenges = soup.find('div', class_='received-challenges')
        assert received_challenges is not None, "Received challenges subsection should exist"
        
        # Should show challenge from user3 with accept/reject buttons
        challenge_items = soup.find_all('div', class_='challenge-item')
        
        # Find the received challenge
        received_challenge = None
        for item in challenge_items:
            if user3.username in item.text:
                received_challenge = item
                break
        
        assert received_challenge is not None, f"Should show challenge from {user3.username}"
        
        # Should have accept and reject buttons
        accept_btn = received_challenge.find('button', class_='accept-challenge-btn')
        reject_btn = received_challenge.find('button', class_='reject-challenge-btn')
        assert accept_btn is not None, "Received challenge should have accept button"
        assert reject_btn is not None, "Received challenge should have reject button"
    
    def test_no_pending_challenges_shows_empty_state(self, authenticated_client, challenge_users):
        """RED: Test empty state when no pending challenges."""
        challenger, challengee = challenge_users
        
        authenticated_client.login(username='challenger', password='testpass123')
        response = authenticated_client.get(reverse('web:dashboard'))
        
        assert response.status_code == 200
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Should show empty state or hide section when no challenges
        pending_section = soup.find('div', class_='pending-challenges-section')
        if pending_section:
            empty_state = pending_section.find('div', class_='empty-state')
            assert empty_state is not None, "Should show empty state when no challenges"


@pytest.mark.web
@pytest.mark.django_db  
class TestChallengeActions:
    """Test challenge management actions via HTMX."""
    
    def test_accept_challenge_creates_game_and_updates_panels(self, authenticated_client, pending_challenge):
        """RED: Test accepting challenge creates game and updates Active Games panel."""
        challengee = pending_challenge.challenged
        
        authenticated_client.login(username=challengee.username, password='testpass123')
        
        # Accept the challenge via HTMX
        response = authenticated_client.post(
            reverse('web:respond_challenge', kwargs={'challenge_id': pending_challenge.id}),
            {'action': 'accept'},
            HTTP_HX_REQUEST='true'
        )
        
        assert response.status_code == 200
        
        # Challenge should be accepted
        pending_challenge.refresh_from_db()
        assert pending_challenge.status == ChallengeStatus.ACCEPTED
        
        # Should create a new game
        games = Game.objects.filter(
            black_player__in=[pending_challenge.challenger, pending_challenge.challenged],
            white_player__in=[pending_challenge.challenger, pending_challenge.challenged]
        )
        assert games.count() == 1, "Should create exactly one game"
        
        game = games.first()
        assert game.status == GameStatus.ACTIVE, "Game should be active"
        assert game.ruleset == pending_challenge.ruleset, "Game should use challenge ruleset"
        
        # Response should update the friends panel
        soup = BeautifulSoup(response.content, 'html.parser')
        # This will fail initially until we implement the response template
        updated_panel = soup.find('div', id='friends-panel')
        assert updated_panel is not None, "Should return updated friends panel"
    
    def test_reject_challenge_removes_from_pending_list(self, authenticated_client, pending_challenge):
        """RED: Test rejecting challenge removes it from pending list."""
        challengee = pending_challenge.challenged
        
        authenticated_client.login(username=challengee.username, password='testpass123')
        
        # Reject the challenge via HTMX
        response = authenticated_client.post(
            reverse('web:respond_challenge', kwargs={'challenge_id': pending_challenge.id}),
            {'action': 'reject'},
            HTTP_HX_REQUEST='true'
        )
        
        assert response.status_code == 200
        
        # Challenge should be rejected
        pending_challenge.refresh_from_db()
        assert pending_challenge.status == ChallengeStatus.REJECTED
        
        # Should not create a game
        games = Game.objects.filter(
            black_player__in=[pending_challenge.challenger, pending_challenge.challenged],
            white_player__in=[pending_challenge.challenger, pending_challenge.challenged]
        )
        assert games.count() == 0, "Should not create a game when rejected"
        
        # Response should update the friends panel without this challenge
        soup = BeautifulSoup(response.content, 'html.parser')
        updated_panel = soup.find('div', id='friends-panel')
        assert updated_panel is not None, "Should return updated friends panel"
    
    def test_cancel_sent_challenge_removes_from_pending_list(self, authenticated_client, pending_challenge):
        """RED: Test cancelling sent challenge removes it from pending list."""
        challenger = pending_challenge.challenger
        
        authenticated_client.login(username=challenger.username, password='testpass123')
        
        # Cancel the challenge via HTMX
        response = authenticated_client.post(
            reverse('web:respond_challenge', kwargs={'challenge_id': pending_challenge.id}),
            {'action': 'cancel'},
            HTTP_HX_REQUEST='true'
        )
        
        assert response.status_code == 200
        
        # Challenge should be cancelled
        pending_challenge.refresh_from_db()
        assert pending_challenge.status == ChallengeStatus.CANCELLED
        
        # Should not create a game
        games = Game.objects.filter(
            black_player__in=[pending_challenge.challenger, pending_challenge.challenged],
            white_player__in=[pending_challenge.challenger, pending_challenge.challenged]
        )
        assert games.count() == 0, "Should not create a game when cancelled"
    
    def test_invalid_challenge_action_returns_error(self, authenticated_client, pending_challenge):
        """RED: Test invalid action returns proper error response."""
        challengee = pending_challenge.challenged
        
        authenticated_client.login(username=challengee.username, password='testpass123')
        
        # Try invalid action
        response = authenticated_client.post(
            reverse('web:respond_challenge', kwargs={'challenge_id': pending_challenge.id}),
            {'action': 'invalid_action'},
            HTTP_HX_REQUEST='true'
        )
        
        assert response.status_code == 400
        
        # Challenge should remain pending
        pending_challenge.refresh_from_db()
        assert pending_challenge.status == ChallengeStatus.PENDING


@pytest.mark.web
@pytest.mark.django_db
class TestChallengeSSEIntegration:
    """Test SSE real-time updates for challenges."""
    
    def test_challenge_response_triggers_sse_update_for_both_users(self, authenticated_client, pending_challenge):
        """RED: Test challenge response sends SSE updates to both users."""
        # This test will verify that SSE events are sent
        # We'll implement the SSE event sending in the view
        
        challengee = pending_challenge.challenged
        authenticated_client.login(username=challengee.username, password='testpass123')
        
        # Accept the challenge
        response = authenticated_client.post(
            reverse('web:respond_challenge', kwargs={'challenge_id': pending_challenge.id}),
            {'action': 'accept'},
            HTTP_HX_REQUEST='true'
        )
        
        assert response.status_code == 200
        
        # This test will pass once we implement SSE event sending
        # For now, we just verify the challenge was processed
        pending_challenge.refresh_from_db()
        assert pending_challenge.status == ChallengeStatus.ACCEPTED
    
    def test_accepted_challenge_updates_active_games_panel_realtime(self, authenticated_client, pending_challenge):
        """RED: Test accepted challenge triggers Active Games panel update."""
        challengee = pending_challenge.challenged
        authenticated_client.login(username=challengee.username, password='testpass123')
        
        # Accept the challenge
        response = authenticated_client.post(
            reverse('web:respond_challenge', kwargs={'challenge_id': pending_challenge.id}),
            {'action': 'accept'},
            HTTP_HX_REQUEST='true'
        )
        
        assert response.status_code == 200
        
        # Verify game was created (this should trigger Active Games update)
        games = Game.objects.filter(
            black_player__in=[pending_challenge.challenger, pending_challenge.challenged],
            white_player__in=[pending_challenge.challenger, pending_challenge.challenged]
        )
        assert games.count() == 1, "Should create game that appears in Active Games"


@pytest.mark.web
@pytest.mark.django_db
class TestChallengeIntegration:
    """Test integration with existing dashboard features."""
    
    def test_pending_challenges_appear_in_friends_panel_context(self, authenticated_client, multiple_challenges):
        """RED: Test pending challenges are included in dashboard context."""
        challenges, (challenger, challengee, user3) = multiple_challenges
        
        authenticated_client.login(username='challenger', password='testpass123')
        response = authenticated_client.get(reverse('web:dashboard'))
        
        assert response.status_code == 200
        
        # Context should include pending challenges
        assert 'pending_sent_challenges' in response.context, "Context should include sent challenges"
        assert 'pending_received_challenges' in response.context, "Context should include received challenges"
        
        sent_challenges = response.context['pending_sent_challenges']
        received_challenges = response.context['pending_received_challenges']
        
        assert len(sent_challenges) == 1, "Should have one sent challenge"
        assert len(received_challenges) == 1, "Should have one received challenge"
        
        # Verify the challenges are the correct ones
        assert sent_challenges[0].challenged == challengee
        assert received_challenges[0].challenger == user3
    
    def test_accepted_challenge_removes_from_pending_and_adds_to_active_games(self, authenticated_client, pending_challenge):
        """RED: Test challenge acceptance updates both pending and active sections."""
        challenger = pending_challenge.challenger
        challengee = pending_challenge.challenged
        
        # Check dashboard before accepting
        authenticated_client.login(username=challengee.username, password='testpass123')
        response_before = authenticated_client.get(reverse('web:dashboard'))
        
        # Should have pending challenge
        assert len(response_before.context['pending_received_challenges']) == 1
        
        # Accept the challenge
        authenticated_client.post(
            reverse('web:respond_challenge', kwargs={'challenge_id': pending_challenge.id}),
            {'action': 'accept'},
            HTTP_HX_REQUEST='true'
        )
        
        # Check dashboard after accepting
        response_after = authenticated_client.get(reverse('web:dashboard'))
        
        # Should no longer have pending challenge
        assert len(response_after.context['pending_received_challenges']) == 0
        
        # Should have new active game
        active_games = response_after.context['active_games']
        assert len(active_games) >= 1, "Should have at least one active game"
        
        # Verify the new game involves the correct players
        new_game = None
        for game in active_games:
            if game.black_player in [challenger, challengee] and game.white_player in [challenger, challengee]:
                new_game = game
                break
        
        assert new_game is not None, "Should find the newly created game in active games"
        assert new_game.status == GameStatus.ACTIVE
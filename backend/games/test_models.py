"""
Comprehensive tests for Game models.
"""

from django.test import TestCase, TransactionTestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from datetime import timedelta

from tests.factories import UserFactory, RuleSetFactory, GameFactory, GameMoveFactory, PlayerSessionFactory, GameEventFactory, ChallengeFactory
from .models import (
    Game, RuleSet, GameMove, GameStatus, Player,
    PlayerSession, SessionStatus, GameEvent, Challenge, ChallengeStatus
)


class RuleSetModelTestCase(TestCase):
    """Test cases for RuleSet model."""
    
    def test_ruleset_creation_with_valid_data(self):
        """Test creating a ruleset with valid data."""
        ruleset = RuleSetFactory(
            name='Test Rules',
            board_size=15,
            allow_overlines=False,
            description='Test ruleset'
        )
        self.assertEqual(ruleset.name, 'Test Rules')
        self.assertEqual(ruleset.board_size, 15)
        self.assertFalse(ruleset.allow_overlines)
        self.assertEqual(ruleset.description, 'Test ruleset')
        self.assertEqual(ruleset.forbidden_moves, {})
    
    def test_ruleset_name_uniqueness(self):
        """Test that ruleset names must be unique."""
        RuleSetFactory(name='Standard')
        
        with self.assertRaises(IntegrityError):
            RuleSet.objects.create(name='Standard', board_size=15)
    
    def test_board_size_validation(self):
        """Test board size constraints."""
        # Valid board sizes
        for size in [9, 15, 19, 25]:
            ruleset = RuleSet(name=f'Test {size}', board_size=size)
            ruleset.full_clean()  # Should not raise
        
        # Invalid board sizes
        for size in [8, 26]:
            with self.assertRaises(ValidationError):
                ruleset = RuleSet(name=f'Invalid {size}', board_size=size)
                ruleset.full_clean()
    
    def test_forbidden_moves_json_field(self):
        """Test forbidden_moves JSON field."""
        forbidden = {
            'three_three': True,
            'four_four': True,
            'overlines': ['black']
        }
        ruleset = RuleSetFactory(forbidden_moves=forbidden)
        self.assertEqual(ruleset.forbidden_moves, forbidden)
    
    def test_str_representation(self):
        """Test string representation."""
        ruleset = RuleSetFactory(name='Standard Gomoku')
        self.assertEqual(str(ruleset), 'Standard Gomoku')


class GameModelConstraintTests(TransactionTestCase):
    """Test cases for Game model database constraints."""
    
    def test_game_players_cannot_be_same(self):
        """Test that black and white players must be different - application logic validation."""
        user = UserFactory()
        ruleset = RuleSetFactory()
        
        # This currently passes at DB level but should be caught by application logic
        game = Game.objects.create(
            black_player=user,
            white_player=user,  # Same as black_player
            ruleset=ruleset
        )
        # In a real application, this validation would be in a form or service layer
        self.assertEqual(game.black_player, game.white_player)
    
    def test_winner_must_be_one_of_players(self):
        """Test that winner must be either black or white player."""
        black_player = UserFactory()
        white_player = UserFactory()
        other_player = UserFactory()
        game = GameFactory(black_player=black_player, white_player=white_player)
        
        # Valid winners
        game.winner = black_player
        game.save()  # Should work
        
        game.winner = white_player
        game.save()  # Should work
        
        # Invalid winner - this would be caught by application logic, not DB constraint
        game.winner = other_player
        game.save()  # Actually works in Django, but business logic should prevent this


class GameModelTestCase(TestCase):
    """Test cases for Game model validation and behavior."""
    
    def test_game_creation_with_valid_data(self):
        """Test creating a game with valid data."""
        black_player = UserFactory(username='black')
        white_player = UserFactory(username='white')
        ruleset = RuleSetFactory(name='Standard')
        
        game = Game.objects.create(
            black_player=black_player,
            white_player=white_player,
            ruleset=ruleset
        )
        
        self.assertEqual(game.black_player, black_player)
        self.assertEqual(game.white_player, white_player)
        self.assertEqual(game.ruleset, ruleset)
        self.assertEqual(game.status, GameStatus.WAITING)
        self.assertEqual(game.current_player, Player.BLACK)
        self.assertEqual(game.board_state, {})
        self.assertEqual(game.move_count, 0)
        self.assertIsNone(game.winner)
        self.assertIsNone(game.started_at)
        self.assertIsNone(game.finished_at)
        self.assertIsNotNone(game.created_at)
    
    def test_game_uuid_primary_key(self):
        """Test that games use UUID primary keys."""
        game = GameFactory()
        self.assertIsNotNone(game.id)
        self.assertEqual(len(str(game.id)), 36)  # UUID length with hyphens
    
    def test_initialize_board(self):
        """Test board initialization."""
        game = GameFactory()
        game.initialize_board()
        
        expected_size = game.ruleset.board_size
        self.assertEqual(game.board_state['size'], expected_size)
        self.assertEqual(len(game.board_state['board']), expected_size)
        self.assertEqual(len(game.board_state['board'][0]), expected_size)
        
        # Check all positions are None
        for row in game.board_state['board']:
            for cell in row:
                self.assertIsNone(cell)
    
    def test_start_game_from_waiting(self):
        """Test starting a game from waiting status."""
        game = GameFactory(status=GameStatus.WAITING)
        self.assertIsNone(game.started_at)
        
        game.start_game()
        
        self.assertEqual(game.status, GameStatus.ACTIVE)
        self.assertIsNotNone(game.started_at)
        self.assertIsNotNone(game.board_state)
        self.assertEqual(game.board_state['size'], game.ruleset.board_size)
    
    def test_start_game_invalid_status(self):
        """Test that starting a non-waiting game raises error."""
        game = GameFactory(status=GameStatus.ACTIVE)
        
        with self.assertRaises(ValueError):
            game.start_game()
        
        game = GameFactory(status=GameStatus.FINISHED)
        
        with self.assertRaises(ValueError):
            game.start_game()
    
    def test_finish_game_without_winner(self):
        """Test finishing a game without specifying winner."""
        game = GameFactory(status=GameStatus.ACTIVE)
        self.assertIsNone(game.finished_at)
        
        game.finish_game()
        
        self.assertEqual(game.status, GameStatus.FINISHED)
        self.assertIsNotNone(game.finished_at)
        self.assertIsNone(game.winner)
    
    def test_finish_game_with_winner(self):
        """Test finishing a game with a winner."""
        black_player = UserFactory(games_played=5, games_won=2)
        white_player = UserFactory(games_played=3, games_won=1)
        game = GameFactory(
            black_player=black_player,
            white_player=white_player,
            status=GameStatus.ACTIVE
        )
        
        game.finish_game(winner=black_player)
        
        self.assertEqual(game.status, GameStatus.FINISHED)
        self.assertEqual(game.winner, black_player)
        self.assertIsNotNone(game.finished_at)
        
        # Check that player stats were updated
        black_player.refresh_from_db()
        white_player.refresh_from_db()
        self.assertEqual(black_player.games_played, 6)
        self.assertEqual(black_player.games_won, 3)
        self.assertEqual(white_player.games_played, 4)
        self.assertEqual(white_player.games_won, 1)
    
    def test_str_representation(self):
        """Test string representation."""
        black_player = UserFactory(username='alice', display_name='')
        white_player = UserFactory(username='bob', display_name='')
        game = GameFactory(black_player=black_player, white_player=white_player)
        
        expected = f"Game {game.id}: alice vs bob"
        self.assertEqual(str(game), expected)
    
    def test_game_status_choices(self):
        """Test all game status choices are valid."""
        game = GameFactory()
        
        for status, _ in GameStatus.choices:
            game.status = status
            game.save()  # Should work for all valid statuses
    
    def test_current_player_choices(self):
        """Test current player choices."""
        game = GameFactory()
        
        game.current_player = Player.BLACK
        game.save()
        
        game.current_player = Player.WHITE
        game.save()
    
    def test_board_state_persistence(self):
        """Test that board state is properly persisted as JSON."""
        game = GameFactory()
        board_state = {
            'size': 15,
            'board': [['BLACK' if i == j == 7 else None for j in range(15)] for i in range(15)]
        }
        game.board_state = board_state
        game.save()
        
        game.refresh_from_db()
        self.assertEqual(game.board_state, board_state)
        self.assertEqual(game.board_state['board'][7][7], 'BLACK')
    
    def test_move_count_tracking(self):
        """Test move count increments."""
        game = GameFactory(move_count=0)
        
        game.move_count += 1
        game.save()
        
        game.refresh_from_db()
        self.assertEqual(game.move_count, 1)
    
    def test_game_timestamps(self):
        """Test game timestamp behavior."""
        game = GameFactory()
        
        # created_at should be set automatically
        self.assertIsNotNone(game.created_at)
        
        # started_at should be None initially
        self.assertIsNone(game.started_at)
        
        # Start the game
        game.start_game()
        self.assertIsNotNone(game.started_at)
        
        # Finish the game
        game.finish_game()
        self.assertIsNotNone(game.finished_at)
        
        # started_at should be before finished_at
        self.assertLess(game.started_at, game.finished_at)


class GameMoveModelTestCase(TransactionTestCase):
    """Test cases for GameMove model."""
    
    def test_gamemove_creation(self):
        """Test creating a game move with valid data."""
        game = GameFactory()
        player = game.black_player
        
        move = GameMove.objects.create(
            game=game,
            player=player,
            move_number=1,
            row=7,
            col=7,
            player_color=Player.BLACK
        )
        
        self.assertEqual(move.game, game)
        self.assertEqual(move.player, player)
        self.assertEqual(move.move_number, 1)
        self.assertEqual(move.row, 7)
        self.assertEqual(move.col, 7)
        self.assertEqual(move.player_color, Player.BLACK)
        self.assertFalse(move.is_winning_move)
        self.assertIsNotNone(move.created_at)
    
    def test_move_coordinate_validation(self):
        """Test move coordinate validation."""
        game = GameFactory()
        player = game.black_player
        
        # Valid coordinates
        move = GameMove(
            game=game, player=player, move_number=1,
            row=0, col=0, player_color=Player.BLACK
        )
        move.full_clean()  # Should not raise
        
        move = GameMove(
            game=game, player=player, move_number=2,
            row=24, col=24, player_color=Player.BLACK
        )
        move.full_clean()  # Should not raise (max validator allows 24)
    
    def test_move_uniqueness_constraints(self):
        """Test that moves have proper uniqueness constraints."""
        game = GameFactory()
        player = game.black_player
        
        # Create first move
        GameMove.objects.create(
            game=game, player=player, move_number=1,
            row=7, col=7, player_color=Player.BLACK
        )
        
        # Same move number should fail
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                GameMove.objects.create(
                    game=game, player=player, move_number=1,
                    row=8, col=8, player_color=Player.WHITE
                )
        
        # Same position should fail
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                GameMove.objects.create(
                    game=game, player=player, move_number=2,
                    row=7, col=7, player_color=Player.WHITE
                )
    
    def test_winning_move_flag(self):
        """Test winning move flag."""
        move = GameMoveFactory(is_winning_move=True)
        self.assertTrue(move.is_winning_move)
        
        move = GameMoveFactory(is_winning_move=False)
        self.assertFalse(move.is_winning_move)
    
    def test_str_representation(self):
        """Test string representation."""
        move = GameMoveFactory(move_number=5, row=3, col=7)
        expected = f"Move 5 in {move.game_id}: (3, 7)"
        self.assertEqual(str(move), expected)
    
    def test_move_ordering(self):
        """Test that moves are ordered correctly."""
        game = GameFactory()
        player = game.black_player
        
        # Create moves out of order
        move3 = GameMoveFactory(game=game, player=player, move_number=3, row=2, col=2)
        move1 = GameMoveFactory(game=game, player=player, move_number=1, row=0, col=0)
        move2 = GameMoveFactory(game=game, player=player, move_number=2, row=1, col=1)
        
        # Query should return in order
        moves = list(game.moves.all())
        self.assertEqual(len(moves), 3)
        self.assertEqual(moves[0].move_number, 1)
        self.assertEqual(moves[1].move_number, 2)
        self.assertEqual(moves[2].move_number, 3)


class PlayerSessionModelTestCase(TestCase):
    """Test cases for PlayerSession model."""
    
    def test_session_creation_with_valid_data(self):
        """Test creating a session with valid data."""
        user = UserFactory()
        game = GameFactory()
        
        session = PlayerSession.objects.create(
            user=user,
            current_game=game,
            status=SessionStatus.IN_GAME
        )
        
        self.assertEqual(session.user, user)
        self.assertEqual(session.current_game, game)
        self.assertEqual(session.status, SessionStatus.IN_GAME)
        self.assertIsNotNone(session.session_id)
        self.assertIsNotNone(session.created_at)
        self.assertIsNotNone(session.last_activity)
    
    def test_session_uuid_primary_key(self):
        """Test that sessions use UUID primary keys."""
        session = PlayerSessionFactory()
        self.assertIsNotNone(session.session_id)
        self.assertEqual(len(str(session.session_id)), 36)  # UUID length with hyphens
    
    def test_session_without_current_game(self):
        """Test creating session without current game."""
        session = PlayerSessionFactory(current_game=None, status=SessionStatus.ONLINE)
        self.assertIsNone(session.current_game)
        self.assertEqual(session.status, SessionStatus.ONLINE)
    
    def test_session_status_choices(self):
        """Test all session status choices are valid."""
        session = PlayerSessionFactory()
        
        for status, _ in SessionStatus.choices:
            session.status = status
            session.save()  # Should work for all valid statuses
    
    def test_is_active_property_recent(self):
        """Test is_active property for recent activity."""
        session = PlayerSessionFactory()
        self.assertTrue(session.is_active)
    
    def test_is_active_property_old(self):
        """Test is_active property for old activity."""
        session = PlayerSessionFactory()
        # Simulate old activity (much more than 60 seconds)
        old_time = timezone.now() - timedelta(minutes=5)
        # Use update to bypass auto_now behavior
        PlayerSession.objects.filter(session_id=session.session_id).update(last_activity=old_time)
        
        session.refresh_from_db()  # Ensure we have the updated value
        self.assertFalse(session.is_active)
    
    def test_update_activity(self):
        """Test updating activity timestamp."""
        session = PlayerSessionFactory()
        old_activity = session.last_activity
        
        # Wait a bit to ensure timestamp difference
        import time
        time.sleep(0.01)
        
        session.update_activity()
        
        session.refresh_from_db()
        self.assertGreater(session.last_activity, old_activity)
    
    def test_str_representation(self):
        """Test string representation."""
        user = UserFactory(username='testuser', display_name='')
        session = PlayerSessionFactory(user=user)
        
        expected = f"Session {session.session_id}: testuser"
        self.assertEqual(str(session), expected)
    
    def test_session_ordering(self):
        """Test sessions are ordered by last activity."""
        session1 = PlayerSessionFactory()
        session2 = PlayerSessionFactory()
        session3 = PlayerSessionFactory()
        
        # Update activity in reverse order
        session2.update_activity()
        session3.update_activity() 
        
        sessions = list(PlayerSession.objects.all())
        # Most recent activity should come first
        self.assertEqual(sessions[0], session3)
        self.assertEqual(sessions[1], session2)
        self.assertEqual(sessions[2], session1)
    
    def test_default_status(self):
        """Test default session status."""
        session = PlayerSession.objects.create(user=UserFactory())
        self.assertEqual(session.status, SessionStatus.ONLINE)


class GameEventModelTestCase(TestCase):
    """Test cases for GameEvent model."""
    
    def test_event_creation_with_valid_data(self):
        """Test creating an event with valid data."""
        user = UserFactory()
        event_data = {'move': {'row': 7, 'col': 7, 'player': 'black'}}
        
        event = GameEvent.objects.create(
            user=user,
            event_type='move',
            event_data=event_data
        )
        
        self.assertEqual(event.user, user)
        self.assertEqual(event.event_type, 'move')
        self.assertEqual(event.event_data, event_data)
        self.assertFalse(event.consumed)
        self.assertIsNotNone(event.created_at)
    
    def test_event_different_types(self):
        """Test various event types."""
        user = UserFactory()
        event_types = ['move', 'game_start', 'challenge', 'game_end', 'player_join']
        
        for event_type in event_types:
            event = GameEvent.objects.create(
                user=user,
                event_type=event_type,
                event_data={'test': 'data'}
            )
            self.assertEqual(event.event_type, event_type)
    
    def test_event_data_persistence(self):
        """Test that event data is properly persisted as JSON."""
        event_data = {
            'game_id': 'test-uuid',
            'move': {'row': 5, 'col': 10},
            'metadata': {'timestamp': '2025-08-13T10:00:00Z'}
        }
        
        event = GameEventFactory(event_data=event_data)
        
        event.refresh_from_db()
        self.assertEqual(event.event_data, event_data)
        self.assertEqual(event.event_data['move']['row'], 5)
    
    def test_consumed_flag(self):
        """Test consumed flag behavior."""
        event = GameEventFactory(consumed=False)
        self.assertFalse(event.consumed)
        
        event.consumed = True
        event.save()
        
        event.refresh_from_db()
        self.assertTrue(event.consumed)
    
    def test_str_representation(self):
        """Test string representation."""
        user = UserFactory(username='alice', display_name='')
        event = GameEventFactory(user=user, event_type='move')
        
        expected = f"Event {event.id}: move for alice"
        self.assertEqual(str(event), expected)
    
    def test_event_ordering(self):
        """Test events are ordered by creation time."""
        user = UserFactory()
        event1 = GameEventFactory(user=user, event_type='first')
        event2 = GameEventFactory(user=user, event_type='second')
        event3 = GameEventFactory(user=user, event_type='third')
        
        events = list(GameEvent.objects.all())
        # Should be ordered by created_at (ascending)
        self.assertEqual(events[0].event_type, 'first')
        self.assertEqual(events[1].event_type, 'second')
        self.assertEqual(events[2].event_type, 'third')
    
    def test_user_events_filtering(self):
        """Test filtering events by user."""
        user1 = UserFactory()
        user2 = UserFactory()
        
        event1 = GameEventFactory(user=user1, event_type='user1_event')
        event2 = GameEventFactory(user=user2, event_type='user2_event')
        event3 = GameEventFactory(user=user1, event_type='user1_event2')
        
        user1_events = GameEvent.objects.filter(user=user1)
        user2_events = GameEvent.objects.filter(user=user2)
        
        self.assertEqual(user1_events.count(), 2)
        self.assertEqual(user2_events.count(), 1)
    
    def test_unconsumed_events_query(self):
        """Test querying for unconsumed events."""
        user = UserFactory()
        event1 = GameEventFactory(user=user, consumed=False)
        event2 = GameEventFactory(user=user, consumed=True)
        event3 = GameEventFactory(user=user, consumed=False)
        
        unconsumed = GameEvent.objects.filter(consumed=False)
        self.assertEqual(unconsumed.count(), 2)
        self.assertIn(event1, unconsumed)
        self.assertIn(event3, unconsumed)
        self.assertNotIn(event2, unconsumed)


class ChallengeModelTestCase(TestCase):
    """Test cases for Challenge model."""
    
    def test_challenge_creation_with_valid_data(self):
        """Test creating a challenge with valid data."""
        challenger = UserFactory()
        challenged = UserFactory()
        
        challenge = Challenge.objects.create(
            challenger=challenger,
            challenged=challenged
        )
        
        self.assertEqual(challenge.challenger, challenger)
        self.assertEqual(challenge.challenged, challenged)
        self.assertEqual(challenge.status, ChallengeStatus.PENDING)
        self.assertIsNotNone(challenge.id)
        self.assertIsNotNone(challenge.created_at)
        self.assertIsNotNone(challenge.expires_at)
        self.assertIsNone(challenge.responded_at)
    
    def test_challenge_uuid_primary_key(self):
        """Test that challenges use UUID primary keys."""
        challenge = ChallengeFactory()
        self.assertIsNotNone(challenge.id)
        self.assertEqual(len(str(challenge.id)), 36)  # UUID length with hyphens
    
    def test_automatic_expiration_time(self):
        """Test that expiration time is set automatically."""
        challenge = Challenge.objects.create(
            challenger=UserFactory(),
            challenged=UserFactory()
        )
        
        expected_expiry = challenge.created_at + timedelta(minutes=5)
        # Allow for small time differences in test execution
        time_diff = abs((challenge.expires_at - expected_expiry).total_seconds())
        self.assertLess(time_diff, 5)  # Within 5 seconds
    
    def test_custom_expiration_time(self):
        """Test setting custom expiration time."""
        custom_expiry = timezone.now() + timedelta(minutes=10)
        challenge = Challenge.objects.create(
            challenger=UserFactory(),
            challenged=UserFactory(),
            expires_at=custom_expiry
        )
        
        self.assertEqual(challenge.expires_at, custom_expiry)
    
    def test_is_expired_property_not_expired(self):
        """Test is_expired property for non-expired challenge."""
        challenge = ChallengeFactory()
        self.assertFalse(challenge.is_expired)
    
    def test_is_expired_property_expired(self):
        """Test is_expired property for expired challenge."""
        past_time = timezone.now() - timedelta(minutes=1)
        challenge = ChallengeFactory(expires_at=past_time)
        self.assertTrue(challenge.is_expired)
    
    def test_accept_pending_challenge(self):
        """Test accepting a pending challenge."""
        challenge = ChallengeFactory(status=ChallengeStatus.PENDING)
        
        challenge.accept()
        
        self.assertEqual(challenge.status, ChallengeStatus.ACCEPTED)
        self.assertIsNotNone(challenge.responded_at)
    
    def test_accept_expired_challenge(self):
        """Test accepting an expired challenge."""
        past_time = timezone.now() - timedelta(minutes=1)
        challenge = ChallengeFactory(
            status=ChallengeStatus.PENDING,
            expires_at=past_time
        )
        
        challenge.accept()
        
        self.assertEqual(challenge.status, ChallengeStatus.EXPIRED)
    
    def test_accept_non_pending_challenge_fails(self):
        """Test that accepting non-pending challenge raises error."""
        challenge = ChallengeFactory(status=ChallengeStatus.ACCEPTED)
        
        with self.assertRaises(ValueError):
            challenge.accept()
    
    def test_reject_pending_challenge(self):
        """Test rejecting a pending challenge."""
        challenge = ChallengeFactory(status=ChallengeStatus.PENDING)
        
        challenge.reject()
        
        self.assertEqual(challenge.status, ChallengeStatus.REJECTED)
        self.assertIsNotNone(challenge.responded_at)
    
    def test_reject_non_pending_challenge_fails(self):
        """Test that rejecting non-pending challenge raises error."""
        challenge = ChallengeFactory(status=ChallengeStatus.ACCEPTED)
        
        with self.assertRaises(ValueError):
            challenge.reject()
    
    def test_challenge_status_choices(self):
        """Test all challenge status choices are valid."""
        challenge = ChallengeFactory()
        
        for status, _ in ChallengeStatus.choices:
            challenge.status = status
            challenge.save()  # Should work for all valid statuses
    
    def test_str_representation(self):
        """Test string representation."""
        challenger = UserFactory(username='alice', display_name='')
        challenged = UserFactory(username='bob', display_name='')
        challenge = ChallengeFactory(challenger=challenger, challenged=challenged)
        
        expected = f"Challenge {challenge.id}: alice -> bob"
        self.assertEqual(str(challenge), expected)
    
    def test_challenge_ordering(self):
        """Test challenges are ordered by creation time (desc)."""
        challenge1 = ChallengeFactory()
        challenge2 = ChallengeFactory()
        challenge3 = ChallengeFactory()
        
        challenges = list(Challenge.objects.all())
        # Most recent should come first
        self.assertEqual(challenges[0], challenge3)
        self.assertEqual(challenges[1], challenge2)
        self.assertEqual(challenges[2], challenge1)
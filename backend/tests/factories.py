"""
Test factories for creating consistent test data using factory_boy.
"""

import factory
from django.contrib.auth import get_user_model
from games.models import RuleSet, Game, GameMove, PlayerSession, GameEvent, Challenge

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    """Factory for User model."""
    
    class Meta:
        model = User
    
    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.Faker('email')
    display_name = factory.Faker('name')
    games_played = 0
    games_won = 0
    is_active = True


class RuleSetFactory(factory.django.DjangoModelFactory):
    """Factory for RuleSet model."""
    
    class Meta:
        model = RuleSet
    
    name = factory.Sequence(lambda n: f"RuleSet {n}")
    game_type = 'GOMOKU'  # Default to Gomoku for backward compatibility
    board_size = 15
    allow_overlines = False
    forbidden_moves = {}
    description = factory.Faker('text', max_nb_chars=200)


class GameFactory(factory.django.DjangoModelFactory):
    """Factory for Game model."""
    
    class Meta:
        model = Game
    
    black_player = factory.SubFactory(UserFactory)
    white_player = factory.SubFactory(UserFactory)
    ruleset = factory.SubFactory(RuleSetFactory)
    status = 'WAITING'
    current_player = 'BLACK'
    board_state = {}
    move_count = 0


class GameMoveFactory(factory.django.DjangoModelFactory):
    """Factory for GameMove model."""
    
    class Meta:
        model = GameMove
    
    game = factory.SubFactory(GameFactory)
    player = factory.SubFactory(UserFactory)
    move_number = factory.Sequence(lambda n: n + 1)
    row = factory.Faker('random_int', min=0, max=14)
    col = factory.Faker('random_int', min=0, max=14)
    player_color = 'BLACK'
    is_winning_move = False


class PlayerSessionFactory(factory.django.DjangoModelFactory):
    """Factory for PlayerSession model."""
    
    class Meta:
        model = PlayerSession
    
    user = factory.SubFactory(UserFactory)
    status = 'ONLINE'
    current_game = None


class GameEventFactory(factory.django.DjangoModelFactory):
    """Factory for GameEvent model."""
    
    class Meta:
        model = GameEvent
    
    user = factory.SubFactory(UserFactory)
    event_type = 'move'
    event_data = {}
    consumed = False


class ChallengeFactory(factory.django.DjangoModelFactory):
    """Factory for Challenge model."""
    
    class Meta:
        model = Challenge
    
    challenger = factory.SubFactory(UserFactory)
    challenged = factory.SubFactory(UserFactory)
    status = 'PENDING'
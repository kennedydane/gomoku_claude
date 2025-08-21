"""
Test factories for creating consistent test data using factory_boy.
"""

import factory
from django.contrib.auth import get_user_model
from games.models import GomokuRuleSet, GoRuleSet, Game, GameMove, PlayerSession, GameEvent, Challenge

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    """Factory for User model."""
    
    class Meta:
        model = User
    
    username = factory.Faker('user_name')
    email = factory.Faker('email')
    display_name = factory.Faker('name')
    games_played = 0
    games_won = 0
    is_active = True


class GomokuRuleSetFactory(factory.django.DjangoModelFactory):
    """Factory for GomokuRuleSet model."""
    
    class Meta:
        model = GomokuRuleSet
    
    name = factory.Faker('company')
    board_size = 15
    allow_overlines = True
    forbidden_moves = {}
    description = factory.Faker('text', max_nb_chars=200)


class GoRuleSetFactory(factory.django.DjangoModelFactory):
    """Factory for GoRuleSet model."""
    
    class Meta:
        model = GoRuleSet
    
    name = factory.Faker('company')
    board_size = 19
    komi = 6.5
    handicap_stones = 0
    scoring_method = 'TERRITORY'
    description = factory.Faker('text', max_nb_chars=200)


# Backward compatibility - default to Gomoku
RuleSetFactory = GomokuRuleSetFactory


class GameFactory(factory.django.DjangoModelFactory):
    """Factory for Game model."""
    
    class Meta:
        model = Game
    
    black_player = factory.SubFactory(UserFactory)
    white_player = factory.SubFactory(UserFactory)
    # Use generic foreign key for ruleset
    ruleset = factory.SubFactory(GomokuRuleSetFactory)  # Default to Gomoku
    
    @factory.post_generation
    def set_generic_foreign_key(self, create, extracted, **kwargs):
        if create:
            self.ruleset_content_type = self.ruleset.get_content_type()
            self.ruleset_object_id = self.ruleset.id
            self.save()
    status = 'ACTIVE'
    current_player = 'BLACK'
    board_state = {}
    move_count = 0


class GameMoveFactory(factory.django.DjangoModelFactory):
    """Factory for GameMove model."""
    
    class Meta:
        model = GameMove
    
    game = factory.SubFactory(GameFactory)
    player_color = 'BLACK'
    move_number = factory.Sequence(lambda n: n + 1)
    row = factory.Faker('random_int', min=0, max=14)
    col = factory.Faker('random_int', min=0, max=14)
    is_winning_move = False
    
    @factory.lazy_attribute
    def player(self):
        # Return the actual user based on player_color
        if self.player_color == 'BLACK':
            return self.game.black_player
        else:
            return self.game.white_player


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
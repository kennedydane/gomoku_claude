"""
Tests for subclassed RuleSet architecture.

This test file validates that:
1. Abstract base RuleSet provides common functionality
2. GomokuRuleSet contains Gomoku-specific fields and methods
3. GoRuleSet contains Go-specific fields and methods
4. GameServiceFactory works with subclassed models
5. Type safety and separation of concerns
"""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from games.models import GameType, ScoringMethod


class TestAbstractRuleSet:
    """Test abstract base RuleSet functionality."""
    
    @pytest.mark.django_db
    def test_cannot_instantiate_abstract_ruleset(self):
        """Test that abstract RuleSet cannot be instantiated directly."""
        from games.models import RuleSet
        
        # This should fail because RuleSet will be abstract
        with pytest.raises(TypeError):
            RuleSet(
                name="Abstract Test",
                board_size=15,
                description="Should not work"
            )
    
    @pytest.mark.django_db
    def test_common_fields_in_base_class(self):
        """Test that common fields are defined in the base class."""
        from games.models import RuleSet
        
        # These fields should exist in the abstract base class
        expected_fields = {
            'name', 'board_size', 'description', 
            'created_at', 'updated_at'
        }
        
        actual_fields = set(field.name for field in RuleSet._meta.fields)
        assert expected_fields.issubset(actual_fields), (
            f"Missing common fields in base class: {expected_fields - actual_fields}"
        )
    
    @pytest.mark.django_db
    def test_abstract_base_properties(self):
        """Test that abstract base class is properly configured."""
        from games.models import RuleSet
        
        # Should be abstract
        assert RuleSet._meta.abstract, "RuleSet should be abstract"


class TestGomokuRuleSet:
    """Test GomokuRuleSet subclass functionality."""
    
    @pytest.mark.django_db
    def test_gomoku_ruleset_creation(self):
        """Test creating GomokuRuleSet instances."""
        from games.models import GomokuRuleSet
        
        ruleset = GomokuRuleSet.objects.create(
            name="Test Gomoku",
            board_size=15,
            allow_overlines=True,
            description="Test Gomoku ruleset"
        )
        
        assert ruleset.name == "Test Gomoku"
        assert ruleset.board_size == 15
        assert ruleset.allow_overlines is True
        assert ruleset.is_gomoku is True
        assert ruleset.is_go is False
    
    @pytest.mark.django_db
    def test_gomoku_specific_fields(self):
        """Test that GomokuRuleSet has Gomoku-specific fields."""
        from games.models import GomokuRuleSet
        
        # These fields should exist only in GomokuRuleSet
        gomoku_specific_fields = {'allow_overlines', 'forbidden_moves'}
        
        actual_fields = set(field.name for field in GomokuRuleSet._meta.fields)
        assert gomoku_specific_fields.issubset(actual_fields), (
            f"Missing Gomoku-specific fields: {gomoku_specific_fields - actual_fields}"
        )
        
        # Go-specific fields should NOT exist
        go_specific_fields = {'komi', 'handicap_stones', 'scoring_method'}
        assert not go_specific_fields.intersection(actual_fields), (
            f"Found Go-specific fields in GomokuRuleSet: {go_specific_fields.intersection(actual_fields)}"
        )
    
    @pytest.mark.django_db
    def test_gomoku_ruleset_validation(self):
        """Test GomokuRuleSet validation methods."""
        from games.models import GomokuRuleSet
        
        # Valid Gomoku ruleset
        ruleset = GomokuRuleSet(
            name="Valid Gomoku",
            board_size=15,
            allow_overlines=False,
            description="Valid ruleset"
        )
        
        # Should not raise validation errors
        ruleset.full_clean()
        
        # Invalid board size should fail
        invalid_ruleset = GomokuRuleSet(
            name="Invalid Gomoku",
            board_size=8,  # Below minimum
            allow_overlines=True,
            description="Invalid board size"
        )
        
        with pytest.raises(ValidationError):
            invalid_ruleset.full_clean()
    
    @pytest.mark.django_db
    def test_gomoku_game_type_property(self):
        """Test that GomokuRuleSet properly identifies its game type."""
        from games.models import GomokuRuleSet
        
        ruleset = GomokuRuleSet.objects.create(
            name="Gomoku Type Test",
            board_size=15,
            allow_overlines=True,
            description="Game type test"
        )
        
        assert ruleset.game_type == GameType.GOMOKU
        assert ruleset.get_game_type_display() == 'Gomoku'


class TestGoRuleSet:
    """Test GoRuleSet subclass functionality."""
    
    @pytest.mark.django_db
    def test_go_ruleset_creation(self):
        """Test creating GoRuleSet instances."""
        from games.models import GoRuleSet
        
        ruleset = GoRuleSet.objects.create(
            name="Test Go",
            board_size=19,
            komi=6.5,
            handicap_stones=0,
            scoring_method=ScoringMethod.TERRITORY,
            description="Test Go ruleset"
        )
        
        assert ruleset.name == "Test Go"
        assert ruleset.board_size == 19
        assert ruleset.komi == 6.5
        assert ruleset.handicap_stones == 0
        assert ruleset.scoring_method == ScoringMethod.TERRITORY
        assert ruleset.is_go is True
        assert ruleset.is_gomoku is False
    
    @pytest.mark.django_db
    def test_go_specific_fields(self):
        """Test that GoRuleSet has Go-specific fields."""
        from games.models import GoRuleSet
        
        # These fields should exist only in GoRuleSet
        go_specific_fields = {'komi', 'handicap_stones', 'scoring_method'}
        
        actual_fields = set(field.name for field in GoRuleSet._meta.fields)
        assert go_specific_fields.issubset(actual_fields), (
            f"Missing Go-specific fields: {go_specific_fields - actual_fields}"
        )
        
        # Gomoku-specific fields should NOT exist
        gomoku_specific_fields = {'allow_overlines', 'forbidden_moves'}
        assert not gomoku_specific_fields.intersection(actual_fields), (
            f"Found Gomoku-specific fields in GoRuleSet: {gomoku_specific_fields.intersection(actual_fields)}"
        )
    
    @pytest.mark.django_db
    def test_go_ruleset_validation(self):
        """Test GoRuleSet validation methods."""
        from games.models import GoRuleSet
        
        # Valid Go ruleset
        ruleset = GoRuleSet(
            name="Valid Go",
            board_size=19,
            komi=6.5,
            handicap_stones=3,
            scoring_method=ScoringMethod.AREA,
            description="Valid Go ruleset"
        )
        
        # Should not raise validation errors
        ruleset.full_clean()
        
        # Invalid handicap stones (over maximum)
        invalid_ruleset = GoRuleSet(
            name="Invalid Go",
            board_size=19,
            komi=6.5,
            handicap_stones=15,  # Above maximum of 9
            scoring_method=ScoringMethod.TERRITORY,
            description="Invalid handicap"
        )
        
        with pytest.raises(ValidationError):
            invalid_ruleset.full_clean()
    
    @pytest.mark.django_db
    def test_go_game_type_property(self):
        """Test that GoRuleSet properly identifies its game type."""
        from games.models import GoRuleSet
        
        ruleset = GoRuleSet.objects.create(
            name="Go Type Test",
            board_size=19,
            komi=7.5,
            handicap_stones=2,
            scoring_method=ScoringMethod.AREA,
            description="Game type test"
        )
        
        assert ruleset.game_type == GameType.GO
        assert ruleset.get_game_type_display() == 'Go'


class TestRuleSetPolymorphism:
    """Test polymorphic behavior of RuleSet subclasses."""
    
    @pytest.mark.django_db
    def test_polymorphic_queries(self):
        """Test that we can query both subclasses separately."""
        from games.models import GomokuRuleSet, GoRuleSet
        
        # Create instances of both types
        gomoku_ruleset = GomokuRuleSet.objects.create(
            name="Polymorphic Gomoku",
            board_size=15,
            allow_overlines=True,
            description="Polymorphic test"
        )
        
        go_ruleset = GoRuleSet.objects.create(
            name="Polymorphic Go",
            board_size=19,
            komi=6.5,
            handicap_stones=0,
            scoring_method=ScoringMethod.TERRITORY,
            description="Polymorphic test"
        )
        
        # Since we use abstract base class, we query each subclass separately
        total_rulesets = GomokuRuleSet.objects.count() + GoRuleSet.objects.count()
        assert total_rulesets >= 2
        
        # Should be able to filter by specific types
        gomoku_only = GomokuRuleSet.objects.all()
        go_only = GoRuleSet.objects.all()
        
        assert gomoku_ruleset in gomoku_only
        assert go_ruleset in go_only
        assert gomoku_ruleset not in go_only
        assert go_ruleset not in gomoku_only
    
    @pytest.mark.django_db
    def test_game_service_integration(self):
        """Test that GameServiceFactory works with subclassed models."""
        from games.models import GomokuRuleSet, GoRuleSet
        from games.game_services import GameServiceFactory
        
        gomoku_ruleset = GomokuRuleSet.objects.create(
            name="Service Test Gomoku",
            board_size=15,
            allow_overlines=True,
            description="Service integration test"
        )
        
        go_ruleset = GoRuleSet.objects.create(
            name="Service Test Go",
            board_size=19,
            komi=6.5,
            handicap_stones=0,
            scoring_method=ScoringMethod.TERRITORY,
            description="Service integration test"
        )
        
        # GameServiceFactory should work with subclassed models
        gomoku_service = GameServiceFactory.get_service(gomoku_ruleset.game_type)
        go_service = GameServiceFactory.get_service(go_ruleset.game_type)
        
        assert gomoku_service is not None
        assert go_service is not None
        assert gomoku_service != go_service


class TestSeedDataWithSubclasses:
    """Test that seed data command works with subclassed models."""
    
    @pytest.mark.django_db
    def test_seed_data_creates_subclass_instances(self):
        """Test that seed data creates proper subclass instances."""
        from django.core.management import call_command
        from games.models import GomokuRuleSet, GoRuleSet
        
        # Clear existing data
        GomokuRuleSet.objects.all().delete()
        GoRuleSet.objects.all().delete()
        
        # Run seed data command
        call_command('create_initial_rulesets', '--force')
        
        # Should create GomokuRuleSet instances
        gomoku_rulesets = GomokuRuleSet.objects.all()
        assert gomoku_rulesets.count() == 5
        
        for ruleset in gomoku_rulesets:
            assert hasattr(ruleset, 'allow_overlines')
            assert hasattr(ruleset, 'forbidden_moves')
            assert not hasattr(ruleset, 'komi')
        
        # Should create GoRuleSet instances
        go_rulesets = GoRuleSet.objects.all()
        assert go_rulesets.count() == 5
        
        for ruleset in go_rulesets:
            assert hasattr(ruleset, 'komi')
            assert hasattr(ruleset, 'handicap_stones')
            assert hasattr(ruleset, 'scoring_method')
            assert not hasattr(ruleset, 'allow_overlines')
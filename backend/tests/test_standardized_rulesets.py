"""
Tests for standardized rulesets with proper board size validation.

This test file validates that:
1. All rulesets comply with board size constraints (9 ≤ size ≤ 25)
2. Board sizes are standardized to approved values: 9×9, 13×13, 15×15, 19×19, 25×25
3. No 8×8 boards exist (violates validator constraints)
4. Proper game-specific ruleset counts

Updated for subclassed RuleSet architecture.
"""

import pytest
from django.core.management import call_command
from django.core.exceptions import ValidationError
from games.models import GomokuRuleSet, GoRuleSet, GameType


@pytest.mark.django_db
class TestStandardizedRulesets:
    """Test standardized ruleset validation."""
    
    def test_no_8x8_boards_allowed(self):
        """Test that 8×8 boards cannot be created (violates validator)."""
        ruleset = GomokuRuleSet(
            name="Invalid 8x8 Board",
            board_size=8,  # Should fail validation
            description="This should fail"
        )
        
        with pytest.raises(ValidationError):
            ruleset.full_clean()  # This triggers model validation
    
    def test_standardized_board_sizes_only(self):
        """Test that only standardized board sizes are created."""
        # Delete any existing rulesets
        GomokuRuleSet.objects.all().delete()
        GoRuleSet.objects.all().delete()
        
        # Create initial rulesets with force flag
        call_command('create_initial_rulesets', '--force')
        
        # Get all board sizes from both subclasses
        gomoku_sizes = set(GomokuRuleSet.objects.values_list('board_size', flat=True))
        go_sizes = set(GoRuleSet.objects.values_list('board_size', flat=True))
        board_sizes = gomoku_sizes.union(go_sizes)
        
        # Should only contain standardized sizes
        expected_sizes = {9, 13, 15, 19, 25}
        assert board_sizes == expected_sizes, f"Found non-standard board sizes: {board_sizes - expected_sizes}"
        
        # Should NOT contain 8×8 boards
        assert 8 not in board_sizes, "Found prohibited 8×8 board size"
    
    def test_proper_ruleset_counts(self):
        """Test that we have the expected number of rulesets."""
        # Delete any existing rulesets
        GomokuRuleSet.objects.all().delete()
        GoRuleSet.objects.all().delete()
        
        # Create initial rulesets with force flag
        call_command('create_initial_rulesets', '--force')
        
        # Should have 5 Gomoku rulesets
        assert GomokuRuleSet.objects.count() == 5, f"Expected 5 Gomoku rulesets, got {GomokuRuleSet.objects.count()}"
        
        # Should have 5 Go rulesets
        assert GoRuleSet.objects.count() == 5, f"Expected 5 Go rulesets, got {GoRuleSet.objects.count()}"
        
        # Total should be 10
        total = GomokuRuleSet.objects.count() + GoRuleSet.objects.count()
        assert total == 10, f"Expected 10 total rulesets, got {total}"


@pytest.mark.django_db
class TestRulesetValidation:
    """Test ruleset validation constraints."""
    
    def test_board_size_minimum_boundary(self):
        """Test board size minimum boundary (9)."""
        # Valid minimum size (9)
        valid_ruleset = GomokuRuleSet(
            name="Valid Minimum",
            board_size=9,
            description="Valid minimum size"
        )
        valid_ruleset.full_clean()  # Should not raise
        
        # Invalid size below minimum (8)
        invalid_ruleset = GomokuRuleSet(
            name="Invalid Below Minimum",
            board_size=8,
            description="Invalid below minimum"
        )
        
        with pytest.raises(ValidationError):
            invalid_ruleset.full_clean()
    
    def test_board_size_maximum_boundary(self):
        """Test board size maximum boundary (25)."""
        # Valid maximum size (25)
        valid_ruleset = GomokuRuleSet(
            name="Valid Maximum",
            board_size=25,
            description="Valid maximum size"
        )
        valid_ruleset.full_clean()  # Should not raise
        
        # Invalid size above maximum (26)
        invalid_ruleset = GomokuRuleSet(
            name="Invalid Above Maximum",
            board_size=26,
            description="Invalid above maximum"
        )
        
        with pytest.raises(ValidationError):
            invalid_ruleset.full_clean()
    
    def test_unique_ruleset_names(self):
        """Test that ruleset names must be unique."""
        # Create first ruleset
        GomokuRuleSet.objects.create(
            name="Test Ruleset",
            board_size=15,
            description="First test ruleset"
        )
        
        # Try to create another with same name - should fail
        with pytest.raises(Exception):  # Could be IntegrityError or ValidationError
            GomokuRuleSet.objects.create(
                name="Test Ruleset",
                board_size=19,
                description="Second test ruleset"
            )
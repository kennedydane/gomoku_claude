# Gomoku Rulesets Fixtures

This directory contains fixture data for different Gomoku rule variations.

## Available Rulesets

### 🎯 **Standard Variants**
- **Standard Gomoku** (15×15) - Classic rules, exactly 5 in a row wins, no overlines
- **Freestyle Gomoku** (15×15) - Overlines allowed, 5+ stones win  
- **Pro Gomoku** (19×19) - Tournament rules on Go board size

### 🏆 **Tournament Variants**
- **Renju** (15×15) - Traditional with black player restrictions (3-3, 4-4, overlines forbidden)
- **Swap2 Tournament** (15×15) - Modern tournament standard with opening protocol
- **Caro** (15×15) - Vietnamese rules requiring unblocked wins

### ⚡ **Quick Play Variants**
- **Mini Gomoku** (8×8) - Compact freestyle board perfect for fast games
- **Speed Gomoku** (9×9) - Lightning-fast minimal board for rapid matches
- **Beginner Friendly** (11×11) - Simplified rules ideal for learning

### 🚀 **Challenge Variants**
- **Giant Gomoku** (25×25) - Epic games on maximum board size

## Loading Rulesets

### Option 1: Use the Management Command (Recommended)
```bash
# Preview what will be loaded
python manage.py load_rulesets --dry-run

# Load all rulesets
python manage.py load_rulesets

# Force reload (if no games exist using current rulesets)
python manage.py load_rulesets --force
```

### Option 2: Manual Django Fixture Loading
```bash
python manage.py loaddata fixtures/rulesets.json
```

### Option 3: Basic Seed Data
```bash
# Creates Standard, Mini, and Freestyle rulesets only
python manage.py seed_data
```

## Ruleset Details

| Name | Board Size | Overlines | Special Rules | Best For |
|------|------------|-----------|---------------|----------|
| **Mini Gomoku** | 8×8 | ✅ Yes | Freestyle | Quick games, learning |
| **Speed Gomoku** | 9×9 | ✅ Yes | Time pressure | Tournaments, rapid play |
| **Beginner Friendly** | 11×11 | ✅ Yes | Simplified | New players |
| **Standard Gomoku** | 15×15 | ❌ No | Classic rules | Traditional play |
| **Freestyle Gomoku** | 15×15 | ✅ Yes | No restrictions | Casual games |
| **Renju** | 15×15 | ❌ No | Black restrictions | Competitive play |
| **Swap2 Tournament** | 15×15 | ❌ No | Opening protocol | Tournaments |
| **Caro** | 15×15 | ✅ Yes | Unblocked wins | Vietnamese style |
| **Pro Gomoku** | 19×19 | ❌ No | Go board size | International competition |
| **Giant Gomoku** | 25×25 | ❌ No | Maximum size | Epic strategic games |

## Mini Gomoku Highlights

The **Mini Gomoku** variant is perfect for:
- ⚡ **Quick Games**: 8×8 board enables faster completion
- 🎓 **Learning**: Smaller board is less overwhelming for beginners  
- 📱 **Mobile Play**: Compact size works well on small screens
- 🏃 **Freestyle Rules**: Overlines allowed for more dynamic gameplay

### Example Mini Gomoku Game
```python
from games.models import RuleSet, Game, GameStatus
from games.services import GameService

# Get the Mini Gomoku ruleset
mini_ruleset = RuleSet.objects.get(name='Mini Gomoku')

# Create a game
game = Game.objects.create(
    black_player=user1,
    white_player=user2, 
    ruleset=mini_ruleset,
    status=GameStatus.ACTIVE
)
game.initialize_board()

# The board is now 8×8 instead of 15×15
assert len(game.board_state['board']) == 8
assert len(game.board_state['board'][0]) == 8
```

## Testing

The rulesets include comprehensive tests in `tests/test_rulesets.py`:

```bash
# Run all ruleset tests
python manage.py test tests.test_rulesets

# Run just Mini Gomoku tests  
python manage.py test tests.test_rulesets.MiniGomokuGameplayTests
```

## Adding Custom Rulesets

To add your own rulesets:

1. **Via Django Admin**: Visit `/admin/games/ruleset/` and create new rulesets
2. **Via Code**: Create RuleSet objects with your custom configurations
3. **Via Fixtures**: Add to `rulesets.json` and reload

### Custom Ruleset Example
```python
custom_ruleset = RuleSet.objects.create(
    name='Custom Variant',
    board_size=13,  # Any size from 9-25
    allow_overlines=True,
    forbidden_moves={
        'custom_rule': True,
        'description': 'Your custom rules here'
    },
    description='Description of your custom variant'
)
```

## Troubleshooting

**Problem**: `load_rulesets --force` fails with foreign key constraint error
**Solution**: The command protects existing games. Use without `--force` to load alongside existing rulesets.

**Problem**: Fixtures not found during tests
**Solution**: Tests create rulesets directly in `setUpTestData()` for reliability.

**Problem**: Want to reset all rulesets
**Solution**: Delete all games first, then use `load_rulesets --force`.
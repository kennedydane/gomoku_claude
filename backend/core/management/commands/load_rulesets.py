"""
Management command to load ruleset fixtures.
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import transaction
from games.models import RuleSet
from loguru import logger


class Command(BaseCommand):
    """Load predefined rulesets from fixtures."""
    
    help = 'Load predefined rulesets from fixtures'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force reload by clearing existing rulesets first'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be loaded without making changes'
        )
    
    def handle(self, *args, **options):
        """Handle the command execution."""
        dry_run = options['dry_run']
        force = options['force']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )
        
        # Check existing rulesets
        existing_count = RuleSet.objects.count()
        if existing_count > 0 and not force:
            self.stdout.write(
                self.style.WARNING(
                    f'Found {existing_count} existing rulesets. '
                    'Use --force to reload or --dry-run to preview.'
                )
            )
            return
        
        try:
            with transaction.atomic():
                if force and not dry_run:
                    # Check for games using rulesets
                    from games.models import Game
                    games_count = Game.objects.count()
                    if games_count > 0:
                        self.stdout.write(
                            self.style.WARNING(
                                f'Found {games_count} existing games. '
                                'Cannot clear rulesets due to foreign key constraints.'
                            )
                        )
                        self.stdout.write('Loading new rulesets alongside existing ones...')
                    else:
                        self.stdout.write('Clearing existing rulesets...')
                        RuleSet.objects.all().delete()
                        logger.info("Cleared existing rulesets")
                
                if not dry_run:
                    self.stdout.write('Loading ruleset fixtures...')
                    call_command('loaddata', 'fixtures/rulesets.json', verbosity=0)
                    
                    # Verify loaded rulesets
                    loaded_count = RuleSet.objects.count()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Successfully loaded {loaded_count} rulesets'
                        )
                    )
                    logger.success(f"Loaded {loaded_count} rulesets from fixtures")
                    
                    # Display loaded rulesets
                    self.stdout.write('\\nLoaded rulesets:')
                    for ruleset in RuleSet.objects.all().order_by('id'):
                        self.stdout.write(
                            f'  • {ruleset.name} ({ruleset.board_size}×{ruleset.board_size})'
                        )
                else:
                    # Dry run - show what would be loaded
                    self.stdout.write('Would load the following rulesets:')
                    rulesets_info = [
                        ('Standard Gomoku', 15, 'Classic rules, no overlines'),
                        ('Freestyle Gomoku', 15, 'Overlines allowed'),
                        ('Renju', 15, 'Traditional with black restrictions'),
                        ('Pro Gomoku', 19, 'Tournament rules on Go board'),
                        ('Caro', 15, 'Vietnamese rules, unblocked wins'),
                        ('Mini Gomoku', 8, 'Quick-play on compact board'),
                        ('Swap2 Tournament', 15, 'Modern tournament standard'),
                        ('Beginner Friendly', 11, 'Simplified for new players'),
                        ('Giant Gomoku', 25, 'Epic games on maximum board'),
                        ('Speed Gomoku', 9, 'Lightning-fast minimal board')
                    ]
                    
                    for name, size, desc in rulesets_info:
                        self.stdout.write(f'  • {name} ({size}×{size}) - {desc}')
                    
                    self.stdout.write(
                        self.style.WARNING('\\nRun without --dry-run to actually load these rulesets')
                    )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error loading rulesets: {str(e)}')
            )
            logger.error(f"Failed to load rulesets: {e}")
            raise
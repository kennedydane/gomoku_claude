"""
Management command to create initial rulesets for both Gomoku and Go.

This command populates the database with a variety of rulesets to give users
different game options for both Gomoku and Go.
"""

from django.core.management.base import BaseCommand
from games.models import GomokuRuleSet, GoRuleSet, GameType, ScoringMethod


class Command(BaseCommand):
    help = 'Create initial rulesets for Gomoku and Go games'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Delete existing rulesets and recreate them',
        )

    def handle(self, *args, **options):
        if options['force']:
            self.stdout.write('Deleting existing rulesets...')
            GomokuRuleSet.objects.all().delete()
            GoRuleSet.objects.all().delete()

        # Create Gomoku rulesets (standardized board sizes: 9×9, 13×13, 15×15, 19×19, 25×25)
        gomoku_rulesets = [
            {
                'name': 'Mini Gomoku',
                'game_type': GameType.GOMOKU,
                'board_size': 9,
                'allow_overlines': True,
                'description': 'Quick Gomoku games on a 9×9 board. Perfect for beginners and rapid matches.'
            },
            {
                'name': 'Beginner Friendly',
                'game_type': GameType.GOMOKU,
                'board_size': 13,
                'allow_overlines': True,
                'description': 'Medium-sized board for new players. 13×13 board with overlines allowed.'
            },
            {
                'name': 'Standard Gomoku',
                'game_type': GameType.GOMOKU,
                'board_size': 15,
                'allow_overlines': False,
                'description': 'Classic Gomoku rules on a 15×15 board. First player to get exactly 5 stones in a row wins. Overlines (6+ stones) do not count as wins.'
            },
            {
                'name': 'Pro Gomoku',
                'game_type': GameType.GOMOKU,
                'board_size': 19,
                'allow_overlines': False,
                'description': 'Professional tournament rules on a 19×19 board. Exactly 5 stones in a row wins. Used in international competitions.'
            },
            {
                'name': 'Giant Gomoku',
                'game_type': GameType.GOMOKU,
                'board_size': 25,
                'allow_overlines': True,
                'description': 'Epic Gomoku battles on a massive 25×25 board. Long strategic games with plenty of space.'
            }
        ]

        # Create Go rulesets
        go_rulesets = [
            {
                'name': 'Standard Go',
                'game_type': GameType.GO,
                'board_size': 19,
                'komi': 6.5,
                'handicap_stones': 0,
                'scoring_method': ScoringMethod.TERRITORY,
                'description': 'Traditional Go rules on a 19×19 board with 6.5 komi. Territory scoring with Japanese rules.'
            },
            {
                'name': 'Beginner Go',
                'game_type': GameType.GO,
                'board_size': 13,
                'komi': 5.5,
                'handicap_stones': 0,
                'scoring_method': ScoringMethod.TERRITORY,
                'description': 'Smaller board perfect for learning Go. 13×13 board with reduced complexity.'
            },
            {
                'name': 'Quick Go',
                'game_type': GameType.GO,
                'board_size': 9,
                'komi': 5.5,
                'handicap_stones': 0,
                'scoring_method': ScoringMethod.TERRITORY,
                'description': 'Fast Go games on a 9×9 board. Great for quick matches and tactical practice.'
            },
            {
                'name': 'High Handicap Go',
                'game_type': GameType.GO,
                'board_size': 19,
                'komi': 0.5,
                'handicap_stones': 9,
                'scoring_method': ScoringMethod.TERRITORY,
                'description': 'Go with maximum handicap stones for teaching games between players of different skill levels.'
            },
            {
                'name': 'Area Scoring Go',
                'game_type': GameType.GO,
                'board_size': 19,
                'komi': 7.5,
                'handicap_stones': 0,
                'scoring_method': ScoringMethod.AREA,
                'description': 'Standard 19×19 Go with Chinese-style area scoring rules.'
            }
        ]

        # Create Gomoku rulesets
        created_gomoku = 0
        for ruleset_data in gomoku_rulesets:
            # Remove game_type since it's now a property of the subclass
            data = {k: v for k, v in ruleset_data.items() if k != 'game_type'}
            ruleset, created = GomokuRuleSet.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            if created:
                created_gomoku += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created Gomoku ruleset: {ruleset.name}')
                )
            else:
                self.stdout.write(f'Gomoku ruleset already exists: {ruleset.name}')

        # Create Go rulesets
        created_go = 0
        for ruleset_data in go_rulesets:
            # Remove game_type since it's now a property of the subclass
            data = {k: v for k, v in ruleset_data.items() if k != 'game_type'}
            ruleset, created = GoRuleSet.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            if created:
                created_go += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created Go ruleset: {ruleset.name}')
                )
            else:
                self.stdout.write(f'Go ruleset already exists: {ruleset.name}')

        # Summary
        total_rulesets = GomokuRuleSet.objects.count() + GoRuleSet.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Seed data creation complete!\n'
                f'Created {created_gomoku} Gomoku rulesets and {created_go} Go rulesets.\n'
                f'Total rulesets in database: {total_rulesets}'
            )
        )

        # Show what was created
        self.stdout.write('\n📋 Available Rulesets:')
        
        # Show Gomoku rulesets
        gomoku_rulesets = GomokuRuleSet.objects.all().order_by('board_size')
        self.stdout.write(f'\n{GameType.GOMOKU.label} ({gomoku_rulesets.count()} rulesets):')
        for rs in gomoku_rulesets:
            size_info = f"{rs.board_size}×{rs.board_size}"
            extra_info = f"overlines={'yes' if rs.allow_overlines else 'no'}"
            self.stdout.write(f'  • {rs.name} ({size_info}, {extra_info})')
        
        # Show Go rulesets
        go_rulesets = GoRuleSet.objects.all().order_by('board_size')
        self.stdout.write(f'\n{GameType.GO.label} ({go_rulesets.count()} rulesets):')
        for rs in go_rulesets:
            size_info = f"{rs.board_size}×{rs.board_size}"
            extra_info = f"komi={rs.komi}, handicap={rs.handicap_stones}"
            self.stdout.write(f'  • {rs.name} ({size_info}, {extra_info})')
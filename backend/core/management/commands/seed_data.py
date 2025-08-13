"""
Management command to seed the database with initial test data.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from games.models import RuleSet, Game

User = get_user_model()


class Command(BaseCommand):
    help = 'Seeds the database with initial test data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing data...'))
            Game.objects.all().delete()
            RuleSet.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()
            self.stdout.write(self.style.SUCCESS('Data cleared'))

        # Create test users
        self.stdout.write('Creating test users...')
        users = []
        for i in range(1, 4):
            user, created = User.objects.get_or_create(
                username=f'player{i}',
                defaults={
                    'email': f'player{i}@example.com',
                    'display_name': f'Player {i}',
                    'games_played': i * 5,
                    'games_won': i * 2,
                }
            )
            if created:
                user.set_unusable_password()
                user.save()
                self.stdout.write(f'  Created user: {user.username}')
            else:
                self.stdout.write(f'  User already exists: {user.username}')
            users.append(user)

        # Create rulesets (use load_rulesets command for comprehensive set)
        self.stdout.write('Creating basic rulesets...')
        self.stdout.write(self.style.WARNING('  Note: Use "python manage.py load_rulesets" for the complete ruleset collection'))
        rulesets = [
            {
                'name': 'Standard Gomoku',
                'board_size': 15,
                'allow_overlines': False,
                'description': 'Standard Gomoku rules - exactly 5 in a row wins'
            },
            {
                'name': 'Mini Gomoku',
                'board_size': 8,
                'allow_overlines': True,
                'description': 'Quick-play freestyle Gomoku on a compact 8×8 board'
            },
            {
                'name': 'Freestyle Gomoku',
                'board_size': 15,
                'allow_overlines': True,
                'description': 'Freestyle rules - overlines count as wins'
            },
        ]

        created_rulesets = []
        for ruleset_data in rulesets:
            ruleset, created = RuleSet.objects.get_or_create(
                name=ruleset_data['name'],
                defaults=ruleset_data
            )
            if created:
                self.stdout.write(f'  Created ruleset: {ruleset.name}')
            else:
                self.stdout.write(f'  Ruleset already exists: {ruleset.name}')
            created_rulesets.append(ruleset)

        # Create sample games
        self.stdout.write('Creating sample games...')
        if len(users) >= 2 and created_rulesets:
            # Create a finished game
            game = Game.objects.create(
                black_player=users[0],
                white_player=users[1],
                ruleset=created_rulesets[0],
                status='FINISHED',
                winner=users[0],
                move_count=25
            )
            game.initialize_board()
            game.save()
            self.stdout.write(f'  Created finished game: {game.id}')

            # Create an active game
            active_game = Game.objects.create(
                black_player=users[1],
                white_player=users[2],
                ruleset=created_rulesets[0],
                status='ACTIVE',
                move_count=10
            )
            active_game.initialize_board()
            active_game.save()
            self.stdout.write(f'  Created active game: {active_game.id}')

            # Create a waiting game
            waiting_game = Game.objects.create(
                black_player=users[0],
                white_player=users[2],
                ruleset=created_rulesets[1]
            )
            self.stdout.write(f'  Created waiting game: {waiting_game.id}')

        self.stdout.write(
            self.style.SUCCESS('Successfully seeded database with test data!')
        )
"""
Management command to create regular (non-admin) users.
Complements Django's built-in createsuperuser command.
"""

import getpass
import sys
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import DEFAULT_DB_ALIAS


class Command(BaseCommand):
    help = 'Create a regular user account (non-admin)'
    requires_migrations_checks = True
    stealth_options = ('stdin',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.UserModel = get_user_model()
        self.username_field = self.UserModel._meta.get_field(self.UserModel.USERNAME_FIELD)

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            help='Specifies the username for the user.',
        )
        parser.add_argument(
            '--email',
            help='Specifies the email for the user.',
        )
        parser.add_argument(
            '--noinput', '--no-input',
            action='store_true',
            help=(
                'Tells Django to NOT prompt the user for input of any kind. '
                'You must use --username with --noinput, along with an option '
                'for any other required field. Users created with --noinput will '
                'not be able to log in until they\'re given a valid password.'
            ),
        )
        parser.add_argument(
            '--database',
            default=DEFAULT_DB_ALIAS,
            help='Specifies the database to use. Default is "default".',
        )

    def execute(self, *args, **options):
        self.stdin = options.get('stdin', sys.stdin)
        return super().execute(*args, **options)

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        database = options['database']
        
        # Determine the username
        verbose_field_name = self.username_field.verbose_name
        while username is None:
            message = f'{verbose_field_name.title()}'
            if self.username_field.blank:
                message += ' (leave blank to use current username)'
            message += ': '
            if not options['noinput']:
                username = input(message)
            else:
                raise CommandError("You must use --username with --noinput.")
            if username and self.UserModel.objects.filter(**{self.UserModel.USERNAME_FIELD: username}).exists():
                self.stderr.write(f"Error: That {verbose_field_name} is already taken.")
                username = None

        if not username:
            raise CommandError(f'{verbose_field_name} cannot be blank.')

        # Determine the email
        if email is None and not options['noinput']:
            email = input('Email address (optional): ')

        # Create the user
        user_data = {
            self.UserModel.USERNAME_FIELD: username,
        }
        
        if email:
            user_data['email'] = email

        try:
            if options['noinput']:
                # Create user without password when using --noinput
                user = self.UserModel._default_manager.db_manager(database).create_user(**user_data)
                self.stdout.write(
                    self.style.SUCCESS(
                        f'User "{username}" created successfully. '
                        'Note: User cannot log in until a password is set.'
                    )
                )
            else:
                # Prompt for password when interactive
                password = None
                while password is None:
                    password = getpass.getpass('Password: ')
                    if not password:
                        self.stderr.write("Error: Blank passwords aren't allowed.")
                        password = None
                        continue
                    
                    password2 = getpass.getpass('Password (again): ')
                    if password != password2:
                        self.stderr.write("Error: Your passwords didn't match.")
                        password = None
                        continue

                user_data['password'] = password
                user = self.UserModel._default_manager.db_manager(database).create_user(**user_data)
                self.stdout.write(
                    self.style.SUCCESS(f'User "{username}" created successfully.')
                )

        except ValidationError as e:
            raise CommandError('; '.join(e.messages))
        except Exception as e:
            raise CommandError(f'Error creating user: {e}')

        # Don't return the user object as Django expects string output
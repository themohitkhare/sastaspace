from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()

class Command(BaseCommand):
    help = 'Create test users for development'

    def handle(self, *args, **options):
        test_users = [
            {
                'username': 'admin',
                'email': 'admin@sastaspace.com',
                'password': 'admin123',
                'first_name': 'Admin',
                'last_name': 'User',
                'is_staff': True,
                'is_superuser': True,
            },
            {
                'username': 'john_doe',
                'email': 'john@sastaspace.com',
                'password': 'password123',
                'first_name': 'John',
                'last_name': 'Doe',
                'is_staff': False,
                'is_superuser': False,
            },
            {
                'username': 'jane_smith',
                'email': 'jane@sastaspace.com',
                'password': 'password123',
                'first_name': 'Jane',
                'last_name': 'Smith',
                'is_staff': False,
                'is_superuser': False,
            },
            {
                'username': 'bob_wilson',
                'email': 'bob@sastaspace.com',
                'password': 'password123',
                'first_name': 'Bob',
                'last_name': 'Wilson',
                'is_staff': False,
                'is_superuser': False,
            },
            {
                'username': 'alice_johnson',
                'email': 'alice@sastaspace.com',
                'password': 'password123',
                'first_name': 'Alice',
                'last_name': 'Johnson',
                'is_staff': False,
                'is_superuser': False,
            },
        ]

        with transaction.atomic():
            for user_data in test_users:
                username = user_data['username']
                email = user_data['email']
                
                # Check if user already exists
                if User.objects.filter(username=username).exists():
                    self.stdout.write(
                        self.style.WARNING(f'User {username} already exists, skipping...')
                    )
                    continue
                
                # Create user
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=user_data['password'],
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name'],
                    is_staff=user_data['is_staff'],
                    is_superuser=user_data['is_superuser'],
                )
                
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully created user: {username} ({email})')
                )

        self.stdout.write(
            self.style.SUCCESS('Test users creation completed!')
        ) 
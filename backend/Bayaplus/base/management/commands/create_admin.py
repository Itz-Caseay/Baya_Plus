from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Create an admin user'

    def add_arguments(self, parser):
        parser.add_argument('--username', required=True, help='Admin username')
        parser.add_argument('--email', required=True, help='Admin email')
        parser.add_argument('--password', required=True, help='Admin password')

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']
        
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.ERROR(f'User {username} already exists'))
            return
        
        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
            is_staff=True,
            is_superuser=True
        )
        self.stdout.write(self.style.SUCCESS(f'Admin user {username} created successfully!'))
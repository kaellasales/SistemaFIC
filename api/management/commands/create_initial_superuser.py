import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Cria um superusuário se ele não existir.'

    def handle(self, *args, **options):
        email = os.getenv('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
        password = os.getenv('DJANGO_SUPERUSER_PASSWORD', 'admin')

        if not User.objects.filter(email=email).exists():
            self.stdout.write(self.style.SUCCESS(f'Criando superusuário: {email}'))
            User.objects.create_superuser(email, password)
        else:
            self.stdout.write(self.style.WARNING(f'Superusuário "{email}" já existe.'))
"""
Management command: python manage.py setup_google_oauth

Creates (or updates) the Google SocialApp record in the database using
GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET from settings / .env.

Run this once after:
  1. Adding your credentials to backend/.env
  2. Running: python manage.py migrate
"""
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Create or update the Google OAuth SocialApp from .env credentials'

    def handle(self, *args, **options):
        from django.contrib.sites.models import Site
        from allauth.socialaccount.models import SocialApp

        client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '').strip()
        secret    = getattr(settings, 'GOOGLE_CLIENT_SECRET', '').strip()

        if not client_id or not secret:
            self.stderr.write(self.style.ERROR(
                '\n[!] GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET is missing in backend/.env\n'
                '    Add them and re-run this command.\n'
            ))
            return

        # Ensure the default Site exists
        site, _ = Site.objects.get_or_create(
            id=settings.SITE_ID,
            defaults={'domain': '127.0.0.1:8000', 'name': 'MediSkin AI (local)'}
        )
        if site.domain != '127.0.0.1:8000':
            site.domain = '127.0.0.1:8000'
            site.name   = 'MediSkin AI (local)'
            site.save()
            self.stdout.write('  Updated Site domain to 127.0.0.1:8000')

        # Create or update the Google SocialApp
        app, created = SocialApp.objects.update_or_create(
            provider='google',
            defaults={
                'name':      'Google',
                'client_id': client_id,
                'secret':    secret,
                'key':       '',
            }
        )
        app.sites.add(site)

        action = 'Created' if created else 'Updated'
        self.stdout.write(self.style.SUCCESS(
            f'\n[+] {action} Google SocialApp (id={app.pk})\n'
            f'    client_id: {client_id[:20]}...\n'
            f'    Linked to site: {site.domain}\n\n'
            f'    You can now start the server and test Google login at:\n'
            f'    http://127.0.0.1:8000/accounts/google/login/\n'
        ))

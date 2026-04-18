import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mediskin.settings')
django.setup()

from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp

print('=== Sites in DB ===')
for s in Site.objects.all().order_by('id'):
    print(f'  id={s.id}  domain={s.domain}')

print()
print('=== Google SocialApps ===')
for a in SocialApp.objects.filter(provider='google'):
    sites = list(a.sites.values_list('id', 'domain'))
    print(f'  id={a.id}  name={a.name}')
    print(f'  client_id={a.client_id}')
    print(f'  sites linked={sites}')

print()
print('=== SITE_ID in use ===')
from django.conf import settings
print(f'  SITE_ID = {settings.SITE_ID}')

# Fix: ensure SocialApp is ONLY linked to the correct site (id matching SITE_ID)
correct_site = Site.objects.get(id=settings.SITE_ID)
print(f'\n[FIX] Using site id={correct_site.id}, domain={correct_site.domain}')

app = SocialApp.objects.get(provider='google')

# Remove ALL site links first, then add only the correct one
app.sites.clear()
app.sites.add(correct_site)

print(f'[OK] SocialApp now linked ONLY to: {list(app.sites.values_list("domain", flat=True))}')
print('\nDone! Restart the server and try Google login again.')

"""
MediSkin AI — Social Auth Signals
Auto-creates a UserProfile whenever a Google (or any social) account is connected.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='socialaccount.SocialAccount')
def create_profile_on_social_login(sender, instance, created, **kwargs):
    """
    Fired after a SocialAccount row is saved.
    When a new social account is created (first Google login), make sure the
    linked Django User has a UserProfile and send a welcome email.
    """
    if not created:
        return

    from main.models import UserProfile  # local import avoids circular refs

    user = instance.user
    extra = instance.extra_data or {}

    # Build a sensible full name from Google's profile data
    full_name = (
        extra.get('name')
        or f"{extra.get('given_name', '')} {extra.get('family_name', '')}".strip()
        or user.get_full_name()
        or user.username
    )

    UserProfile.objects.get_or_create(
        user=user,
        defaults={
            'full_name': full_name,
            'profile_complete': False,
        }
    )

    # Send personalised welcome email on first Google sign-in
    if user.email:
        first_name = full_name.split()[0] if full_name else user.username
        try:
            from main.views import _send_email_safe
            _send_email_safe(
                subject='Welcome to MediSkin AI!',
                body=(
                    f"Hi {first_name},\n\n"
                    f"Welcome to MediSkin AI! You've signed in with Google successfully.\n\n"
                    f"Account: {user.username}\n"
                    f"Email: {user.email}\n\n"
                    f"You can now upload skin images and get AI-powered diagnoses instantly.\n\n"
                    f"Get started: http://127.0.0.1:8000/diagnostics/\n\n"
                    f"-- MediSkin AI Team"
                ),
                recipient_email=user.email,
            )
        except Exception as e:
            print(f"[EMAIL] Google login welcome email failed: {e}")

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.adapter import DefaultAccountAdapter


class NoSignupFormSocialAdapter(DefaultSocialAccountAdapter):
    """
    Custom social account adapter that completely bypasses the
    /accounts/3rdparty/signup/ confirmation page.

    Key behaviours:
    - Always allows auto-signup (no confirmation form)
    - If an existing user has the same email as the Google account,
      the Google account is automatically connected to that user
      (avoids the "account already exists" blocking error)
    """

    def is_auto_signup_allowed(self, request, sociallogin):
        # Always allow auto-signup → no confirmation form shown
        return True

    def is_open_for_signup(self, request, sociallogin):
        # Allow new social accounts to be created without a signup form
        return True

    def pre_social_login(self, request, sociallogin):
        """
        Called after OAuth but before the login is finalised.
        If the Google email matches an existing Django user,
        connect the social account to that user automatically.
        """
        from django.contrib.auth.models import User

        if sociallogin.is_existing:
            return  # already connected — nothing to do

        # Try to find an existing user with the same email
        email = sociallogin.account.extra_data.get('email', '')
        if not email:
            return

        try:
            existing_user = User.objects.get(email=email)
            # Connect this Google login to the existing account
            sociallogin.connect(request, existing_user)
        except User.DoesNotExist:
            pass  # No existing user — normal new signup flow
        except User.MultipleObjectsReturned:
            pass  # Multiple users with same email — let allauth handle it


class NoSignupFormAccountAdapter(DefaultAccountAdapter):
    """
    Prevents allauth's standard email/password signup page from being
    reached directly (users sign up via Google OAuth only or via our
    custom registration API — not via allauth's built-in pages).
    """

    def is_open_for_signup(self, request):
        # Disable allauth's own signup page (we have a custom one)
        return False

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # Google OAuth 2.0 — allauth handles /accounts/google/login/ and /callback/
    path('accounts/', include('allauth.urls')),

    # Main app routes (includes /auth/google/complete/ bridge)
    path('', include('main.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('create-account/', views.create_account, name='create_account'),
    path('reset-password/', views.reset_password, name='reset_password'),

    # Protected pages — require Django login (login_required decorator)
    path('diagnostics/', views.diagnostics, name='diagnostics'),
    path('profile/', views.profile, name='profile'),

    # Google OAuth bridge — called by allauth after successful Google sign-in
    path('auth/google/complete/', views.google_oauth_complete, name='google_oauth_complete'),

    # ML API endpoint
    path('api/predict/', views.predict_skin_disease, name='predict_skin_disease'),

    # Authentication API endpoints (existing username/password flow)
    path('api/auth/register/', views.register_user, name='register_user'),
    path('api/auth/login/', views.login_user, name='login_user'),
    path('api/auth/logout/', views.logout_user, name='logout_user'),
    path('api/auth/reset-password/', views.reset_password_user, name='reset_password_user'),
    path('api/auth/change-password/', views.change_password, name='change_password'),

    # History API endpoint
    path('api/history/', views.get_prediction_history, name='get_prediction_history'),

    # PDF Report endpoint
    path('api/report/pdf/', views.generate_pdf_report, name='generate_pdf_report'),

    # Profile API endpoints
    path('api/profile/location/', views.update_profile_location, name='update_profile_location'),
    path('api/profile/picture/', views.update_profile_picture, name='update_profile_picture'),
    path('api/profile/data/', views.get_profile_data, name='get_profile_data'),

    # Google Places proxy — returns top-3 dermatology clinics, key stays server-side
    path('api/maps/nearby-clinics/', views.nearby_dermatology_clinics, name='nearby_dermatology_clinics'),
]

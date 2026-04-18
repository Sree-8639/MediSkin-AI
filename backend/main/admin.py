from django.contrib import admin

from .models import UserProfile, SkinPrediction

admin.site.register(UserProfile)
admin.site.register(SkinPrediction)

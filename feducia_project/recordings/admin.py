from django.contrib import admin
from .models import SpeechSession
from .models import Profile



admin.site.register(SpeechSession)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'points')
    search_fields = ('user__username',)

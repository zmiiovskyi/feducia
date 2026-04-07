from django.conf import settings
from django.db import models

# Create your models here


class SpeechSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sessions')

    video = models.FileField(
        upload_to='recordings/%Y/%m/%d/',
        help_text="Repeat recording in format mp4/webm"
    )
    text = models.TextField(
        blank=True,
        null=True,
        help_text="Optional speech text to be displayed on the teleprompter during recording."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    feedback = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"Session {self.id} by {self.user.username}"
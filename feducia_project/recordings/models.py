from django.db import models
from django.contrib.auth.models import User

# Create your models here


class SpeechSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')

    video = models.FileField(
        upload_to='recordings/%Y/%m/%d/',
        help_text="Repeat recording in format mp4/webm"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Session {self.id} by {self.user.username}"
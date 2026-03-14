from django.db import models
from django.contrib.auth.models import User

# Create your models here


class SpeechSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')

    # Використовуємо FileField з динамічним шляхом
    video = models.FileField(
        upload_to='recordings/%Y/%m/%d/',
        help_text="Запис репетиції у форматі mp4/webm"
    )

    # Додамо дату створення, це корисно для сортування
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Session {self.id} by {self.user.username}"
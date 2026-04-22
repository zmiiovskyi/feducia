from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


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

class Profile(models.Model):

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    points = models.IntegerField(default=0)

    def __str__(self):
        return f"Profile of {self.user.username} - Points: {self.points}"


    @receiver(post_save, sender=settings.AUTH_USER_MODEL)
    def create_user_profile(sender, instance, created, **kwargs):
        if created:
            Profile.objects.create(user=instance)

    @receiver(post_save, sender=settings.AUTH_USER_MODEL)
    def save_user_profile(sender, instance, **kwargs):
        if hasattr(instance, 'profile'):
            instance.profile.save()
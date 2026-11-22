from django.db import models, transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.conf import settings

class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='dashboard_profile')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)

    def __str__(self):
        return f"{self.user.email}'s Profile"


@receiver(post_delete, sender=Profile)
def delete_avatar_file(sender, instance, **kwargs):
    name = instance.avatar.name
    if name:
        transaction.on_commit(lambda: instance.avatar.storage.delete(name))

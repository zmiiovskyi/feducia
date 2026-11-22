import io
import shutil
import tempfile
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

PASSWORD = "Zq8-strong-pass-91"
MP4 = b"\x00\x00\x00\x18ftypisom" + b"\x00" * 64
WEBM = b"\x1a\x45\xdf\xa3" + b"\x00" * 64


def image_bytes(image_format="PNG"):
    buffer = io.BytesIO()
    Image.new("RGB", (16, 16), "red").save(buffer, image_format)
    return buffer.getvalue()


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class AppTestCase(TestCase):
    """Тимчасовий media, чистий кеш і готовий залогінений користувач."""

    def setUp(self):
        media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media, ignore_errors=True)

        media_settings = override_settings(MEDIA_ROOT=media)
        media_settings.enable()
        self.addCleanup(media_settings.disable)

        cache.clear()
        self.user = self.create_user("owner")
        self.client.force_login(self.user)

    def create_user(self, username):
        return get_user_model().objects.create_user(username, f"{username}@example.com", PASSWORD)

    def client_for(self, user=None):
        client = self.client_class()
        if user:
            client.force_login(user)
        return client

    def upload_video(self, name="rehearsal.mp4", content=MP4, **data):
        # Сам аналіз тут не запускаємо
        with mock.patch("recordings.views.threading.Thread"):
            return self.client.post(
                "/save-recording/",
                {"video_file": SimpleUploadedFile(name, content), **data},
            )

    def upload_avatar(self, name="me.png", content=None):
        content = image_bytes() if content is None else content
        return self.client.post("/profile/upload-avatar/", {"avatar": SimpleUploadedFile(name, content)})

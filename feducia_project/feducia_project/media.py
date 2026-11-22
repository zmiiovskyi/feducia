from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.views.decorators.cache import cache_control
from django.views.static import serve

from dashboard.forms import AVATAR_EXTENSIONS
from dashboard.models import Profile
from recordings.models import SpeechSession
from recordings.validators import VIDEO_EXTENSIONS


@login_required
@cache_control(private=True, no_cache=True)
def protected_media_view(request, path):
    # Файл віддаємо лише власнику і лише з безпечним розширенням
    extension = path.rsplit(".", 1)[-1].lower()

    if extension in VIDEO_EXTENSIONS:
        is_owner = SpeechSession.objects.filter(user=request.user, video=path).exists()
    elif extension in AVATAR_EXTENSIONS:
        is_owner = Profile.objects.filter(user=request.user, avatar=path).exists()
    else:
        is_owner = False

    if not is_owner:
        raise Http404

    return serve(request, path, document_root=settings.MEDIA_ROOT)

from django.shortcuts import render
from django.http import JsonResponse
from .models import SpeechSession


def recording_view(request):
    return render(request, 'recordings/recording.html')


def save_recording_view(request):
    if request.method == 'POST' and request.FILES.get('video_file'):
        video = request.FILES['video_file']

        session = SpeechSession.objects.create(
            user=request.user,
            video=video
        )

        return JsonResponse({
            'status': 'success',
            'id': session.id
        })
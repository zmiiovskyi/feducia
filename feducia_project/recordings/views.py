import os
import time
from django.shortcuts import render
from django.http import JsonResponse


def recording_view(request):
    return render(request, 'recordings/recording.html')


def save_recording_view(request):
    if request.method == 'POST' and request.FILES.get('video_file'):
        video = request.FILES['video_file']

        save_folder = 'media'
        os.makedirs(save_folder, exist_ok=True)

        filename = f"rehearsal_{int(time.time())}.webm"
        filepath = os.path.join(save_folder, filename)

        with open(filepath, 'wb+') as destination:
            for chunk in video.chunks():
                destination.write(chunk)

        return JsonResponse({'status': 'success', 'message': 'Відео успішно збережено!'})

    return JsonResponse({'status': 'error', 'message': 'Помилка збереження'}, status=400)
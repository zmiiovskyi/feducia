import os
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.core.cache import cache
import threading
from django.db import connection
from .models import SpeechSession, Profile
from .video_analysis import VideoAnalyzer
from .audio_utils import extract_audio_from_video
from .audio_analysis import analyze_audio


@login_required
def recording_view(request):
    return render(request, "recordings/recording.html")


@login_required
def save_recording_view(request):
    if request.method != "POST":
        return JsonResponse(
            {"status": "error", "message": "Only POST method is allowed."},
            status=405
        )

    video_file = request.FILES.get("video_file")

    if not video_file:
        return JsonResponse(
            {"status": "error", "message": "No video file provided."},
            status=400
        )

    session = SpeechSession.objects.create(
        user=request.user,
        video=video_file
    )

    cache.set(f'progress_{session.id}', 5, timeout=300)

    def run_analysis():
        analyzer = None
        try:
            video_path = session.video.path
            cache.set(f'progress_{session.id}', 10, timeout=300)

            audio_path = extract_audio_from_video(video_path)
            cache.set(f'progress_{session.id}', 18, timeout=300)

            cache.set(f'progress_{session.id}', 22, timeout=300)
            audio_result = analyze_audio(audio_path)

            cache.set(f'progress_{session.id}', 30, timeout=300)

            model_path = os.path.join(settings.BASE_DIR, "models", "pose_landmarker_full.task")
            cache.set(f'progress_{session.id}', 32, timeout=300)

            analyzer = VideoAnalyzer(model_path=model_path)

            def update_progress(video_percent):
                total_progress = int(30 + (video_percent * 0.7))
                cache.set(f'progress_{session.id}', total_progress, timeout=300)

            analysis_result = analyzer.analyze(video_path, progress_callback=update_progress)

            cache.set(f'progress_{session.id}', 100, timeout=300)

            video_score = analysis_result.get("score", 0)
            audio_score = audio_result.get("confidence_score", 0)

            final_score = round((video_score * 0.6) + (audio_score * 0.4))

            analysis_result["video_score"] = video_score
            analysis_result["audio_score"] = audio_score
            analysis_result["score"] = final_score

            analysis_result["audio"] = audio_result
            analysis_result["audio_extracted"] = True
            analysis_result["audio_file"] = os.path.basename(audio_path)

            session.feedback = analysis_result
            session.save()

            if not analysis_result.get("success"):
                cache.set(f'progress_{session.id}', -1, timeout=300)
                return

            profile, created = Profile.objects.get_or_create(user=request.user)
            profile.points += 50
            profile.save()

        except Exception as error:
            session.feedback = {
                "success": False,
                "error": str(error)
            }
            session.save()
            cache.set(f'progress_{session.id}', -1, timeout=300)

        finally:
            if analyzer is not None:
                analyzer.close()
            connection.close()

    thread = threading.Thread(target=run_analysis)
    thread.start()

    return JsonResponse(
        {
            "status": "success",
            "id": session.id
        }
    )


@login_required
def loading_view(request, session_id):
    session = get_object_or_404(
        SpeechSession,
        id=session_id,
        user=request.user
    )

    return render(
        request,
        "dashboard/loading_menu.html",
        {"session": session}
    )


@login_required
def analytics_view(request, session_id):
    session = get_object_or_404(
        SpeechSession,
        id=session_id,
        user=request.user
    )

    result = session.feedback or {}

    metrics = result.get("metrics", {})
    timeline = result.get("timeline", {})
    audio = result.get("audio", {})

    def safe(val, default=0):
        return val if val is not None else default

    chart = {
        "posture": round((1 - safe(metrics.get("posture"))) * 100),
        "head": round((1 - safe(metrics.get("head"))) * 100),
        "gesture": round((1 - safe(metrics.get("gesture_frequency"))) * 100),
        "symmetry": round(safe(metrics.get("symmetry")) * 100),
    }

    context = {
        "result": result,
        "metrics": metrics,
        "timeline": timeline,
        "chart": chart,
        "score": result.get("score"),
        "style": result.get("style"),
        "audio": audio,
    }

    return render(request, "recordings/analytics.html", context)


@login_required
def delete_session_view(request, session_id):
    if request.method == "POST":
        session = get_object_or_404(
            SpeechSession,
            id=session_id,
            user=request.user
        )
        session.delete()

    return redirect("Main_Page")


@login_required
def get_progress(request, session_id):
    progress = cache.get(f'progress_{session_id}', 0)
    return JsonResponse({'progress': progress})
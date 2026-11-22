import logging
import os
import uuid

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404

from .models import SpeechSession, Profile
from django.core.cache import cache
import threading
from django.db import connection
from django.db.models import F
from .video_analysis import VideoAnalyzer
from .audio_utils import extract_audio_from_video
from .audio_analysis import analyze_audio
from .validators import validate_video
from feducia_project.ratelimit import rate_limit

logger = logging.getLogger(__name__)

PROGRESS_TIMEOUT = 60 * 60


@login_required
def recording_view(request):
    return render(request, "recordings/recording.html")


@login_required
@rate_limit("upload", limit=20, window=3600, as_json=True)
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

    try:
        extension = validate_video(video_file)
    except ValidationError as error:
        return JsonResponse({"status": "error", "message": error.messages[0]}, status=400)

    video_file.name = f"{uuid.uuid4().hex}.{extension}"

    session = SpeechSession.objects.create(
        user=request.user,
        video=video_file,
        text=request.POST.get("teleprompter_text", "").strip() or None
    )

    cache.set(f'progress_{session.id}', 5, timeout=PROGRESS_TIMEOUT)

    def run_analysis():
        analyzer = None
        audio_path = None
        try:
            video_path = session.video.path
            cache.set(f'progress_{session.id}', 10, timeout=PROGRESS_TIMEOUT)

            audio_path = extract_audio_from_video(video_path)
            cache.set(f'progress_{session.id}', 18, timeout=PROGRESS_TIMEOUT)

            cache.set(f'progress_{session.id}', 22, timeout=PROGRESS_TIMEOUT)
            audio_result = analyze_audio(audio_path)

            cache.set(f'progress_{session.id}', 30, timeout=PROGRESS_TIMEOUT)

            model_path = os.path.join(settings.BASE_DIR, "models", "pose_landmarker_full.task")
            cache.set(f'progress_{session.id}', 32, timeout=PROGRESS_TIMEOUT)

            analyzer = VideoAnalyzer(model_path=model_path)

            def update_progress(video_percent):
                # 100 ставимо лише після збереження результату
                total_progress = min(99, int(30 + (video_percent * 0.7)))
                cache.set(f'progress_{session.id}', total_progress, timeout=PROGRESS_TIMEOUT)

            analysis_result = analyzer.analyze(video_path, progress_callback=update_progress)

            video_score = analysis_result.get("score", 0)
            audio_score = audio_result.get("confidence_score", 0)

            final_score = round((video_score * 0.6) + (audio_score * 0.4))

            analysis_result["video_score"] = video_score
            analysis_result["audio_score"] = audio_score
            analysis_result["score"] = final_score

            analysis_result["audio"] = audio_result
            analysis_result["audio_extracted"] = audio_path is not None
            analysis_result["audio_file"] = os.path.basename(audio_path) if audio_path else None

            # update() замість save(), щоб не відновити видалену під час аналізу сесію
            if not SpeechSession.objects.filter(pk=session.pk).update(feedback=analysis_result):
                return

            if not analysis_result.get("success"):
                cache.set(f'progress_{session.id}', -1, timeout=PROGRESS_TIMEOUT)
                return

            profile, created = Profile.objects.get_or_create(user=request.user)
            Profile.objects.filter(pk=profile.pk).update(points=F("points") + 50)
            cache.set(f'progress_{session.id}', 100, timeout=PROGRESS_TIMEOUT)

        except Exception:
            logger.exception("Analysis of session %s failed", session.pk)
            SpeechSession.objects.filter(pk=session.pk).update(feedback={
                "success": False,
                "error": "Could not analyze the video."
            })
            cache.set(f'progress_{session.id}', -1, timeout=PROGRESS_TIMEOUT)

        finally:
            if analyzer is not None:
                analyzer.close()
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
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

    def score_posture(value):
        if value is None:
            return {"score": 0, "status": "Not detected"}

        if value < 0.02:
            return {"score": 95, "status": "Excellent"}

        if value < 0.05:
            return {"score": 65, "status": "Good"}

        return {"score": 35, "status": "Needs Work"}


    def score_head(value):
        if value is None:
            return {"score": 0, "status": "Not detected"}

        if value < 0.01:
            return {"score": 95, "status": "Excellent"}

        if value < 0.03:
            return {"score": 65, "status": "Moderate"}

        return {"score": 35, "status": "Too Active"}


    def score_gesture(left_hand, right_hand):
        values = []

        if left_hand is not None:
            values.append(left_hand)

        if right_hand is not None:
            values.append(right_hand)

        if not values:
            return {"score": 0, "status": "Not detected"}

        avg_hand = sum(values) / len(values)

        if avg_hand < 0.01:
            return {"score": 45, "status": "Too Low"}

        if avg_hand < 0.03:
            return {"score": 95, "status": "Balanced"}

        return {"score": 35, "status": "Too Active"}


    chart = {
        "Posture": score_posture(metrics.get("posture")),
        "Head": score_head(metrics.get("head")),
        "Gesture": score_gesture(
            metrics.get("left_hand"),
            metrics.get("right_hand")
        ),
    }

    context = {
        "result": result,
        "failed": result.get("success") is False,
        "video_score": result.get("video_score", result.get("score")),
        "metrics": metrics,
        "timeline": timeline,
        "chart": chart,
        "score": result.get("score"),
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
    session = get_object_or_404(
        SpeechSession,
        id=session_id,
        user=request.user
    )

    if session.feedback:
        progress = 100 if session.feedback.get("success") else -1
    else:
        # немає ні результату, ні прогресу: аналіз перервано, наприклад рестартом
        progress = cache.get(f'progress_{session.id}', -1)
    return JsonResponse({'progress': progress})
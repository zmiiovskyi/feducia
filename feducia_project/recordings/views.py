import os
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from .models import SpeechSession
from .video_analysis import VideoAnalyzer


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

    analyzer = None

    try:
        video_path = session.video.path
        model_path = os.path.join(settings.BASE_DIR, "models", "pose_landmarker_full.task")

        analyzer = VideoAnalyzer(model_path=model_path)
        analysis_result = analyzer.analyze(video_path)

        session.feedback = analysis_result
        session.save()

        if not analysis_result.get("success"):
            return JsonResponse(
                {
                    "status": "error",
                    "message": analysis_result.get("error", "Video analysis failed."),
                    "id": session.id
                },
                status=500
            )

        return JsonResponse({
            "status": "success",
            "id": session.id
        })

    except Exception as error:
        session.feedback = {
            "success": False,
            "error": str(error)
        }
        session.save()

        return JsonResponse(
            {
                "status": "error",
                "message": "Server error during video analysis.",
                "details": str(error)
            },
            status=500
        )

    finally:
        if analyzer is not None:
            analyzer.close()


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

    feedback_data = session.feedback or {}
    return render(
        request,
        "recordings/analytics.html",
        {
            "session": session,
            "result": feedback_data,
            "feedback_list": feedback_data.get("feedback", [])
        }
    )


@login_required
def delete_session_view(request, session_id):
    if request.method == 'POST':
        session = get_object_or_404(SpeechSession, id=session_id, user=request.user)
        session.delete()
    return redirect('Main_Page')
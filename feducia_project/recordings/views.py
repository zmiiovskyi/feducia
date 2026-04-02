from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.conf import settings

from .models import SpeechSession
from .video_analysis import VideoAnalyzer


@login_required
def recording_view(request):
    return render(request, "recordings/recording.html")


@login_required
def save_recording_view(request):
    if request.method == "POST" and request.FILES.get("video_file"):
        video = request.FILES["video_file"]

        session = SpeechSession.objects.create(
            user=request.user,
            video=video
        )

        print(f"[SAVE] Session {session.id} saved")

        model_path = settings.BASE_DIR / "models" / "pose_landmarker_lite.task"
        analyzer = VideoAnalyzer(str(model_path))

        try:
            result = analyzer.analyze(session.video.path)

            print(f"[ANALYSIS] Session {session.id} done")
            print("  success:", result.get("success"))
            print("  frames:", result.get("processed_frames"), "/", result.get("total_frames"))
            print("  detection_rate:", result.get("detection_rate"))

            feedback = result.get("feedback", [])
            if feedback:
                print("  feedback:")
                for f in feedback:
                    print("   -", f)

        except Exception as error:
            print(f"[ERROR] Session {session.id}: {error}")

        finally:
            analyzer.close()

        return JsonResponse({
            "status": "success",
            "id": session.id
        })

    return JsonResponse({"status": "error"}, status=400)
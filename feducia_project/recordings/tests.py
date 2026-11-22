import os
import shutil
import subprocess
import tempfile
import threading
import time
from types import SimpleNamespace
from unittest import mock, skipUnless

import cv2
import numpy as np
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from feducia_project.testing import MP4, WEBM, AppTestCase
from users.models import User

from . import audio_analysis
from .audio_utils import extract_audio_from_video
from .models import Profile, SpeechSession
from .video_analysis import VideoAnalyzer

HAS_FFMPEG = shutil.which("ffmpeg") is not None


class UploadTests(AppTestCase):
    def test_supported_videos(self):
        for name, content in (("a.mp4", MP4), ("a.webm", WEBM), ("A.MOV", MP4), ("a.mkv", WEBM)):
            with self.subTest(name=name):
                self.assertEqual(self.upload_video(name, content).status_code, 200)

    def test_bad_files_are_rejected(self):
        cases = [
            ("x.html", b"<script>alert(1)</script>"),
            ("x.mp4", b"<script>alert(1)</script>"),
            ("x.mp4", b"#EXTM3U\nfile:///etc/passwd"),
            ("x.mp4", b"ffconcat version 1.0\n"),
            ("x.mp4", b""),
            ("x.html", MP4),
            ("no-extension", MP4),
        ]
        for name, content in cases:
            with self.subTest(name=name, content=content[:20]):
                self.assertEqual(self.upload_video(name, content).status_code, 400)

    def test_size_limit(self):
        with mock.patch("recordings.validators.MAX_VIDEO_SIZE", 10):
            self.assertEqual(self.upload_video().status_code, 400)

    def test_file_name_is_random(self):
        self.upload_video()
        self.assertNotIn("rehearsal", SpeechSession.objects.get().video.name)

    def test_teleprompter_text_is_saved(self):
        self.upload_video(teleprompter_text="My speech")
        self.assertEqual(SpeechSession.objects.get().text, "My speech")


class AccessTests(AppTestCase):
    def setUp(self):
        super().setUp()
        self.upload_video()
        self.session = SpeechSession.objects.get()
        self.stranger = self.client_for(self.create_user("stranger"))

    def test_owner_can_watch_video(self):
        response = self.client.get(self.session.video.url)
        self.assertEqual(b"".join(response.streaming_content), MP4)

    def test_stranger_gets_404(self):
        paths = [
            self.session.video.url,
            f"/get-progress/{self.session.id}/",
            f"/analytics/{self.session.id}/",
            f"/loading/{self.session.id}/",
        ]
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(self.stranger.get(path).status_code, 404)

    def test_stranger_cannot_delete(self):
        self.assertEqual(self.stranger.post(f"/delete/{self.session.id}/").status_code, 404)
        self.assertTrue(SpeechSession.objects.exists())

    def test_anonymous_is_redirected(self):
        self.assertEqual(self.client_for().get(self.session.video.url).status_code, 302)

    def test_unsafe_extension_is_not_served(self):
        session = SpeechSession.objects.create(
            user=self.user, video=SimpleUploadedFile("old.html", b"<script>")
        )
        self.assertEqual(self.client.get(session.video.url).status_code, 404)

    def test_files_are_removed_with_session_and_account(self):
        for path in (f"/delete/{self.session.id}/", "/delete-account/"):
            with self.subTest(path=path):
                if not SpeechSession.objects.exists():
                    self.upload_video()
                video = SpeechSession.objects.get().video.path
                audio = os.path.splitext(video)[0] + ".wav"
                open(audio, "wb").close()

                with self.captureOnCommitCallbacks(execute=True):
                    self.client.post(path)

                self.assertFalse(os.path.exists(video))
                self.assertFalse(os.path.exists(audio))


class ProgressTests(AppTestCase):
    def progress(self, feedback=None, cached=None):
        session = SpeechSession.objects.create(user=self.user, video="recordings/a.mp4", feedback=feedback)
        if cached is not None:
            cache.set(f"progress_{session.id}", cached)
        return self.client.get(f"/get-progress/{session.id}/").json()["progress"]

    def test_running(self):
        self.assertEqual(self.progress(cached=42), 42)

    def test_finished_after_cache_expired(self):
        self.assertEqual(self.progress(feedback={"success": True}), 100)

    def test_failed(self):
        self.assertEqual(self.progress(feedback={"success": False}), -1)

    def test_lost_after_restart(self):
        self.assertEqual(self.progress(), -1)


class PipelineTests(AppTestCase):
    def run_pipeline(self, video_result=None, audio_error=None, during_analysis=None):
        self.seen_progress = []

        def analyze(path, progress_callback):
            for percent in (50, 100, 130):
                progress_callback(percent)
                self.seen_progress.append(cache.get(f"progress_{SpeechSession.objects.get().id}"))
            if during_analysis:
                during_analysis()
            return video_result or {"success": True, "score": 9}

        with (
            mock.patch("recordings.views.threading.Thread") as thread,
            mock.patch("recordings.views.connection.close"),
            mock.patch("recordings.views.extract_audio_from_video", return_value=None),
            mock.patch("recordings.views.analyze_audio", side_effect=audio_error,
                       return_value={"success": True, "confidence_score": 4}),
            mock.patch("recordings.views.VideoAnalyzer") as analyzer,
        ):
            analyzer.return_value.analyze.side_effect = analyze
            self.client.post("/save-recording/", {"video_file": SimpleUploadedFile("a.mp4", MP4)})
            thread.call_args.kwargs["target"]()

    def test_success(self):
        self.run_pipeline()
        session = SpeechSession.objects.get()
        self.assertEqual(session.feedback["score"], 7)
        self.assertEqual(cache.get(f"progress_{session.id}"), 100)
        self.assertEqual(Profile.objects.get(user=self.user).points, 50)

    def test_progress_is_100_only_after_result_is_saved(self):
        self.run_pipeline()
        self.assertLess(max(self.seen_progress), 100)

    def test_failure(self):
        with self.assertLogs("recordings.views", "ERROR"):
            self.run_pipeline(audio_error=RuntimeError("/private/path"))
        session = SpeechSession.objects.get()
        self.assertEqual(cache.get(f"progress_{session.id}"), -1)
        self.assertNotIn("/private/path", str(session.feedback))
        self.assertEqual(Profile.objects.get(user=self.user).points, 0)

    def test_deleted_session_is_not_restored(self):
        self.run_pipeline(during_analysis=lambda: SpeechSession.objects.all().delete())
        self.assertFalse(SpeechSession.objects.exists())

    def test_saving_user_keeps_new_points(self):
        user = User.objects.get(pk=self.user.pk)
        self.assertEqual(user.recordings_profile.points, 0)
        Profile.objects.filter(user=user).update(points=50)
        user.save()
        self.assertEqual(Profile.objects.get(user=user).points, 50)


class AnalyticsTests(AppTestCase):
    def report(self, feedback):
        session = SpeechSession.objects.create(user=self.user, video="recordings/a.mp4", feedback=feedback)
        return self.client.get(f"/analytics/{session.id}/")

    def test_zero_video_score_is_not_replaced_by_total(self):
        response = self.report({"success": True, "score": 3, "video_score": 0})
        self.assertEqual(response.context["video_score"], 0)

    def test_failed_analysis(self):
        response = self.report({"success": False, "error": "Could not analyze the video."})
        self.assertContains(response, "Could not analyze the video.")
        self.assertNotContains(response, "Overall Score")

    def test_timeline_cannot_break_out_of_script(self):
        payload = "</script><script>alert(1)</script>"
        response = self.report({"success": True, "timeline": {"time": [1.0], "head": [payload]}})
        self.assertNotContains(response, "<script>alert(1)")
        self.assertContains(response, 'integrity="sha384-')


class AudioAnalysisTests(SimpleTestCase):
    def analyze(self, text, duration=60):
        model = mock.Mock()
        model.transcribe.return_value = {"text": text, "segments": []}
        with (
            mock.patch.object(audio_analysis, "get_model", return_value=model),
            mock.patch.object(audio_analysis, "get_audio_duration", return_value=duration),
        ):
            return audio_analysis.analyze_audio("speech.wav")

    def test_fillers(self):
        self.assertEqual(self.analyze("Um, you know, this works")["filler_count"], 2)

    def test_phrases_match_whole_words_only(self):
        self.assertEqual(audio_analysis.count_fillers("hi meaning mankind of", []), [])

    def test_non_english_words_are_counted(self):
        self.assertEqual(self.analyze("Добрий день, пам’ять працює")["words_count"], 4)

    def test_no_audio_track(self):
        self.assertEqual(audio_analysis.analyze_audio(None)["confidence"], "Not detected")

    def test_empty_audio(self):
        self.assertEqual(self.analyze("ghost words", duration=0)["words_count"], 0)

    def test_pauses(self):
        pauses = audio_analysis.analyze_pauses([{"start": 0, "end": 1}, {"start": 3, "end": 4}])
        self.assertEqual((pauses["long_pause_count"], pauses["max_pause"]), (1, 2))

    def test_model_is_never_used_in_parallel(self):
        active = []
        overlaps = []

        def transcribe(*args, **kwargs):
            active.append(1)
            overlaps.append(len(active))
            time.sleep(0.05)
            active.pop()
            return {"text": "hello", "segments": []}

        model = mock.Mock(transcribe=transcribe)
        with (
            mock.patch.object(audio_analysis, "get_model", return_value=model),
            mock.patch.object(audio_analysis, "get_audio_duration", return_value=10),
        ):
            workers = [threading.Thread(target=audio_analysis.analyze_audio, args=("a.wav",)) for _ in range(3)]
            for worker in workers:
                worker.start()
            for worker in workers:
                worker.join()

        self.assertEqual(overlaps, [1, 1, 1])


class VideoAnalysisTests(SimpleTestCase):
    def analyze_frames(self, milliseconds):
        points = [SimpleNamespace(x=0.5, y=0.5) for _ in range(33)]
        analyzer = VideoAnalyzer.__new__(VideoAnalyzer)
        analyzer.landmarker = mock.Mock()
        analyzer.landmarker.detect_for_video.return_value = SimpleNamespace(pose_landmarks=[points])

        capture = mock.Mock()
        frame = np.zeros((32, 32, 3), np.uint8)
        capture.read.side_effect = [(True, frame)] * len(milliseconds) + [(False, None)]
        position = iter(milliseconds)
        capture.get.side_effect = lambda prop: (
            next(position) if prop == cv2.CAP_PROP_POS_MSEC else len(milliseconds)
        )

        with mock.patch("recordings.video_analysis.cv2.VideoCapture", return_value=capture):
            result = analyzer.analyze("video.mp4", frame_step=1)

        sent = [call.args[1] for call in analyzer.landmarker.detect_for_video.call_args_list]
        return result, sent

    def test_timeline_is_aligned(self):
        timeline = self.analyze_frames([0, 100, 200, 300])[0]["timeline"]
        self.assertEqual(timeline["time"], [0.1, 0.2, 0.3])
        self.assertEqual(len(timeline["head"]), 3)

    def test_timestamps_always_increase(self):
        sent = self.analyze_frames([0, 100, 100, 0])[1]
        self.assertEqual(sent, sorted(set(sent)))

    def test_real_model_on_blank_video(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "blank.mp4")
            writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), 10, (160, 120))
            for _ in range(9):
                writer.write(np.zeros((120, 160, 3), np.uint8))
            writer.release()

            analyzer = VideoAnalyzer(str(settings.BASE_DIR / "models" / "pose_landmarker_full.task"))
            self.addCleanup(analyzer.close)
            self.assertEqual(analyzer.analyze(path)["score"], 0)


@skipUnless(HAS_FFMPEG, "ffmpeg is not installed")
class AudioExtractionTests(SimpleTestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder)
        self.video = os.path.join(self.folder, "video.mp4")

    def make_video(self, *options):
        subprocess.run(
            ["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "color=size=64x64:duration=1", *options, self.video],
            check=True,
        )

    def test_video_with_audio(self):
        self.make_video("-f", "lavfi", "-i", "sine=duration=1")
        self.assertTrue(os.path.exists(extract_audio_from_video(self.video)))

    def test_silent_video(self):
        self.make_video()
        self.assertIsNone(extract_audio_from_video(self.video))

    def test_playlist_is_refused(self):
        audio = os.path.join(self.folder, "inner.wav")
        subprocess.run(
            ["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "sine=duration=1", audio], check=True
        )
        with open(self.video, "w") as playlist:
            playlist.write("ffconcat version 1.0\nfile inner.wav\n")
        with self.assertRaises(subprocess.CalledProcessError):
            extract_audio_from_video(self.video)

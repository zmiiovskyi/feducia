import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent / "feducia_project"
sys.path.insert(0, str(PROJECT_DIR))

from recordings.video_analysis import VideoAnalyzer  # noqa: E402

VIDEO_PATH = sys.argv[1] if len(sys.argv) > 1 else "test_video.mp4"
MODEL_PATH = str(PROJECT_DIR / "models" / "pose_landmarker_lite.task")
OUTPUT_JSON_PATH = "analysis_result.json"

analyzer = VideoAnalyzer(MODEL_PATH)

try:
    result = analyzer.analyze(VIDEO_PATH, frame_step=3)

    if not result["success"]:
        print(result["error"])
    else:
        print("\n=== Analysis Result ===")
        print(result)

        analyzer.save_result_to_json(result, OUTPUT_JSON_PATH)
        print(f"\nResult saved to file: {OUTPUT_JSON_PATH}")
finally:
    analyzer.close()

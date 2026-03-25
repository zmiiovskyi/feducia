from video_analysis import SimpleVideoAnalyzer


VIDEO_PATH = "test_video.mp4"
MODEL_PATH = "pose_landmarker_lite.task"
OUTPUT_JSON_PATH = "analysis_result.json"


analyzer = SimpleVideoAnalyzer(MODEL_PATH)

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
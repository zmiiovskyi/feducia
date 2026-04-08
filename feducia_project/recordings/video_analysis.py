import json
import math
import cv2
import mediapipe as mp

from mediapipe.tasks import python
from mediapipe.tasks.python import vision


NOSE_IDX = 0
LEFT_SHOULDER_IDX = 11
RIGHT_SHOULDER_IDX = 12
LEFT_WRIST_IDX = 15
RIGHT_WRIST_IDX = 16


class VideoAnalyzer:
    def __init__(self, model_path):
        with open(model_path, "rb") as f:
            model_data = f.read()

        base_options = python.BaseOptions(
            model_asset_buffer=model_data
        )

        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_poses=1,
        )

        self.landmarker = vision.PoseLandmarker.create_from_options(options)


    def generate_feedback(
        self,
        avg_shoulder_diff,
        avg_head_movement,
        avg_left_hand_movement,
        avg_right_hand_movement
    ):
        strengths = []
        issues = []
        advice = []

        # POSTURE
        if avg_shoulder_diff is None:
            issues.append(
                "The system could not fully evaluate your posture."
            )
            advice.append(
                "Make sure your upper body and shoulders are clearly visible in the frame during the whole recording."
            )
        elif avg_shoulder_diff < 0.02:
            strengths.append(
                "Your posture looks straight and balanced. This creates a confident and stable impression."
            )
        elif avg_shoulder_diff < 0.05:
            issues.append(
                "A slight shoulder imbalance was detected. Your posture is generally acceptable, but it may look a little uneven."
            )
            advice.append(
                "Try to keep both shoulders relaxed and at a similar level while speaking."
            )
        else:
            issues.append(
                "A noticeable shoulder imbalance was detected. This can make your posture look tense or less confident."
            )
            advice.append(
                "Practice standing straighter and check whether you lean more to one side during your speech."
            )

        # HEAD MOVEMENT
        if avg_head_movement is None:
            issues.append(
                "The system could not evaluate your head movement."
            )
            advice.append(
                "Keep your face visible and try not to move out of the frame."
            )
        elif avg_head_movement < 0.01:
            strengths.append(
                "Your head movement is well controlled. This helps you look calm and focused."
            )
        elif avg_head_movement < 0.03:
            issues.append(
                "Your head movement is moderate. Some movement is natural, but too much of it may distract the audience."
            )
            advice.append(
                "Try to keep your head a little more stable and avoid unnecessary movements when speaking."
            )
        else:
            issues.append(
                "A high level of head movement was detected. This may make your presentation look nervous or less controlled."
            )
            advice.append(
                "Practice speaking with slower and more controlled head movements, and keep your attention directed forward."
            )

        # HAND GESTURES
        hand_values = []

        if avg_left_hand_movement is not None:
            hand_values.append(avg_left_hand_movement)

        if avg_right_hand_movement is not None:
            hand_values.append(avg_right_hand_movement)

        if not hand_values:
            issues.append(
                "The system could not evaluate your hand gestures."
            )
            advice.append(
                "Make sure your hands are visible in the frame if you want gesture analysis."
            )
        else:
            avg_hand_movement = sum(hand_values) / len(hand_values)

            if avg_hand_movement < 0.01:
                issues.append(
                    "Very few hand gestures were detected. This may make your speech look too stiff or not expressive enough."
                )
                advice.append(
                    "Try to add a few natural gestures to support your main ideas and make your delivery more lively."
                )
            elif avg_hand_movement < 0.03:
                strengths.append(
                    "Your hand gestures look moderate and natural. This usually helps support your speech without distracting the audience."
                )
            else:
                issues.append(
                    "A high level of hand movement was detected. Too many gestures may distract the audience from your message."
                )
                advice.append(
                    "Try to use fewer but more meaningful gestures, especially when you want to emphasize important points."
                )

        # SUMMARY
        if strengths and not issues:
            summary = (
                "This recording shows a confident and controlled presentation style. "
                "Your body language looks stable and supports your speech well."
            )
        elif strengths and issues:
            summary = (
                "Your presentation already has some strong points, but there are also a few areas that could be improved. "
                "With a bit more control over body language, your delivery can become stronger and more professional."
            )
        else:
            summary = (
                "This recording shows several areas that need improvement. "
                "Working on posture, movement control, and gesture usage can make your presentation clearer and more confident."
            )

        return {
            "summary": summary,
            "strengths": strengths,
            "issues": issues,
            "advice": advice,
        }

    def build_report_text(self, feedback):
        parts = []

        summary = feedback.get("summary")
        strengths = feedback.get("strengths", [])
        issues = feedback.get("issues", [])
        advice = feedback.get("advice", [])

        if summary:
            parts.append(f"Summary: {summary}")

        if strengths:
            parts.append("What you did well: " + " ".join(strengths))

        if issues:
            parts.append("What needs improvement: " + " ".join(issues))

        if advice:
            parts.append("Advice: " + " ".join(advice))

        return "\n\n".join(parts)

    def analyze(self, video_path, frame_step=10):
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            return {
                "success": False,
                "error": "Failed to open video"
            }

        shoulder_diffs = []
        head_movements = []
        left_hand_movements = []
        right_hand_movements = []

        total_frames = 0
        processed_frames = 0
        detected_frames = 0

        prev_nose = None
        prev_left_wrist = None
        prev_right_wrist = None

        while True:
            ret, frame = cap.read()

            if not ret:
                break

            total_frames += 1

            if total_frames % frame_step != 0:
                continue

            processed_frames += 1

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=rgb_frame
            )

            timestamp_ms = int(cap.get(cv2.CAP_PROP_POS_MSEC))
            result = self.landmarker.detect_for_video(mp_image, timestamp_ms)

            if result.pose_landmarks:
                detected_frames += 1

                pose_landmarks = result.pose_landmarks[0]

                nose = pose_landmarks[NOSE_IDX]
                left_shoulder = pose_landmarks[LEFT_SHOULDER_IDX]
                right_shoulder = pose_landmarks[RIGHT_SHOULDER_IDX]
                left_wrist = pose_landmarks[LEFT_WRIST_IDX]
                right_wrist = pose_landmarks[RIGHT_WRIST_IDX]

                nose_point = (nose.x, nose.y)
                left_wrist_point = (left_wrist.x, left_wrist.y)
                right_wrist_point = (right_wrist.x, right_wrist.y)

                shoulder_diff = abs(left_shoulder.y - right_shoulder.y)
                shoulder_diffs.append(shoulder_diff)

                if prev_nose is not None:
                    head_movement = math.sqrt(
                        (nose_point[0] - prev_nose[0]) ** 2 +
                        (nose_point[1] - prev_nose[1]) ** 2
                    )
                    head_movements.append(head_movement)

                if prev_left_wrist is not None:
                    left_hand_movement = math.sqrt(
                        (left_wrist_point[0] - prev_left_wrist[0]) ** 2 +
                        (left_wrist_point[1] - prev_left_wrist[1]) ** 2
                    )
                    left_hand_movements.append(left_hand_movement)

                if prev_right_wrist is not None:
                    right_hand_movement = math.sqrt(
                        (right_wrist_point[0] - prev_right_wrist[0]) ** 2 +
                        (right_wrist_point[1] - prev_right_wrist[1]) ** 2
                    )
                    right_hand_movements.append(right_hand_movement)

                prev_nose = nose_point
                prev_left_wrist = left_wrist_point
                prev_right_wrist = right_wrist_point

        cap.release()

        avg_shoulder_diff = sum(shoulder_diffs) / len(shoulder_diffs) if shoulder_diffs else None
        avg_head_movement = sum(head_movements) / len(head_movements) if head_movements else None
        avg_left_hand_movement = sum(left_hand_movements) / len(left_hand_movements) if left_hand_movements else None
        avg_right_hand_movement = sum(right_hand_movements) / len(right_hand_movements) if right_hand_movements else None

        feedback = self.generate_feedback(
            avg_shoulder_diff,
            avg_head_movement,
            avg_left_hand_movement,
            avg_right_hand_movement
        )

        report_text = self.build_report_text(feedback)

        return {
            "success": True,
            "report": report_text
        }

    def save_result_to_json(self, result, output_path):
        clean_result = {
            "success": result.get("success"),
            "report": result.get("report")
        }

        with open(output_path, "w", encoding="utf-8") as file:
            json.dump(clean_result, file, ensure_ascii=False, indent=4)

    def close(self):
        self.landmarker.close()
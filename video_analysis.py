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


class SimpleVideoAnalyzer:
    def __init__(self, model_path):
        base_options = python.BaseOptions(model_asset_path=model_path)

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
        feedback = []

        if avg_shoulder_diff is None:
            feedback.append("Could not evaluate posture.")
        elif avg_shoulder_diff < 0.02:
            feedback.append("Posture is quite straight.")
        elif avg_shoulder_diff < 0.05:
            feedback.append("Slight shoulder imbalance detected.")
        else:
            feedback.append("Noticeable shoulder imbalance.")

        if avg_head_movement is None:
            feedback.append("Could not evaluate head movement.")
        elif avg_head_movement < 0.01:
            feedback.append("Head is stable.")
        elif avg_head_movement < 0.03:
            feedback.append("Moderate head movement.")
        else:
            feedback.append("High head movement.")

        hand_values = []

        if avg_left_hand_movement is not None:
            hand_values.append(avg_left_hand_movement)

        if avg_right_hand_movement is not None:
            hand_values.append(avg_right_hand_movement)

        if not hand_values:
            feedback.append("Could not evaluate hand gestures.")
        else:
            avg_hand_movement = sum(hand_values) / len(hand_values)

            if avg_hand_movement < 0.01:
                feedback.append("Very few gestures.")
            elif avg_hand_movement < 0.03:
                feedback.append("Moderate gestures.")
            else:
                feedback.append("Active gestures.")

        return feedback

    def analyze(self, video_path, frame_step=10):
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            return {
                "success": False,
                "error": "Не вдалося відкрити відео"
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

        detection_rate = detected_frames / processed_frames if processed_frames > 0 else 0

        feedback = self.generate_feedback(
            avg_shoulder_diff,
            avg_head_movement,
            avg_left_hand_movement,
            avg_right_hand_movement
        )

        return {
            "success": True,
            "video_path": video_path,
            "total_frames": total_frames,
            "processed_frames": processed_frames,
            "detected_frames": detected_frames,
            "detection_rate": round(detection_rate, 4),
            "frame_step": frame_step,
            "avg_shoulder_diff": round(avg_shoulder_diff, 4) if avg_shoulder_diff is not None else None,
            "avg_head_movement": round(avg_head_movement, 4) if avg_head_movement is not None else None,
            "avg_left_hand_movement": round(avg_left_hand_movement, 4) if avg_left_hand_movement is not None else None,
            "avg_right_hand_movement": round(avg_right_hand_movement, 4) if avg_right_hand_movement is not None else None,
            "feedback": feedback
        }

    def save_result_to_json(self, result, output_path):
        with open(output_path, "w", encoding="utf-8") as file:
            json.dump(result, file, ensure_ascii=False, indent=4)

    def close(self):
        self.landmarker.close()
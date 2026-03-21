import cv2

def open_camera():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Неможливо відкрити камеру")
        return
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Помилка отримання кадру")
            break
        cv2.imshow('Camera Feed', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()

open_camera()
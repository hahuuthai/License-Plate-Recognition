import cv2

for i in range(5):
    cap = cv2.VideoCapture(i)
    if cap.isOpened():
        print(f"Camera {i}: OK")
        cap.release()
    else:
        print(f"Camera {i}: FAIL")
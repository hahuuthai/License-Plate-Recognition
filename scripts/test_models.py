import cv2

from ai.pipeline.recognition_pipeline import RecognitionPipeline
from ai.models.vehicle_model import VehicleModel
from ai.models.plate_model import PlateModel
from ai.models.ocr_model import OCRModel

# ===== LOAD MODEL =====
vehicle_model = VehicleModel("yolov8")
plate_model = PlateModel("yolov8")
ocr_model = OCRModel()

pipeline = RecognitionPipeline(
    vehicle_model,
    plate_model,
    ocr_model
)

# ===== LOAD IMAGE =====
frame = cv2.imread("D:/DoAnTN/Dataset/GreenParking/0017_00195_b.jpg")

# ===== RUN PIPELINE =====
result = pipeline.process(frame)

# ===== VẼ KẾT QUẢ =====

if result:
    plate = result["plate"]
    vehicle_type = result["vehicle_type"]
    vehicle_bbox = result["vehicle_bbox"]
    plate_bbox = result["plate_bbox"]

    # =========================
    # VẼ BBOX XE
    # =========================
    x1, y1, x2, y2 = vehicle_bbox
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

    # =========================
    # TEXT XE (dưới bbox xe)
    # =========================
    vehicle_text = f"{vehicle_type}"

    vx = x1
    vy = y2 + 25

    h, w, _ = frame.shape
    if vy > h - 10:
        vy = y2 - 10

    (tw, th), _ = cv2.getTextSize(vehicle_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)

    cv2.rectangle(frame, (vx, vy - th - 5), (vx + tw, vy + 5), (0, 0, 0), -1)

    cv2.putText(
        frame,
        vehicle_text,
        (vx, vy),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 0),
        2
    )

    # =========================
    # VẼ BBOX BIỂN
    # =========================
    px1, py1, px2, py2 = plate_bbox
    cv2.rectangle(frame, (px1, py1), (px2, py2), (0, 0, 255), 2)

    # =========================
    # TEXT BIỂN (dưới bbox biển)
    # =========================
    plate_text = f"{plate}"

    tx = px1
    ty = py2 + 30

    if ty > h - 10:
        ty = py2 - 10

    (tw, th), _ = cv2.getTextSize(plate_text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)

    cv2.rectangle(frame, (tx, ty - th - 5), (tx + tw, ty + 5), (0, 0, 0), -1)

    cv2.putText(
        frame,
        plate_text,
        (tx, ty),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 255),
        2
    )

# ===== HIỂN THỊ =====
cv2.imshow("Result", frame)


cv2.waitKey(0)
cv2.destroyAllWindows()
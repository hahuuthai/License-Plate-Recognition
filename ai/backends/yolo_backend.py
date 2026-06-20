from ultralytics import YOLO
import os
import torch
from ultralytics.nn.tasks import DetectionModel


class YOLOBackend:
    def __init__(self, model_path):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found: {model_path}")

        try:
            print("🔍 LOADING YOLO MODEL:", model_path)

            # =========================
            # FIX PYTORCH 2.6 LOAD
            # =========================
            torch.serialization.add_safe_globals([DetectionModel])
            torch._dynamo.config.suppress_errors = True

            # =========================
            # LOAD MODEL
            # =========================
            self.model = YOLO(model_path)

            # =========================
            # FIX CPU 
            # =========================
            self.model.to("cpu")

            print("YOLO MODEL LOADED")

        except Exception as e:
            print("LOAD YOLO ERROR:", e)
            raise

    def predict(self, image):
        try:
            results = self.model(image, verbose=False)[0]
        except Exception as e:
            print("YOLO inference lỗi:", e)
            return []

        output = []

        if results.boxes is None:
            return output

        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            cls = int(box.cls[0])

            crop = image[y1:y2, x1:x2]

            output.append({
                "bbox": [x1, y1, x2, y2],
                "class": cls,
                "confidence": conf,
                "crop": crop
            })

        return output
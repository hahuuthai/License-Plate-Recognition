from ai.backends.yolo_backend import YOLOBackend
from ai.backends.faster_rcnn_backend import FasterRCNNBackend
import os
import sys


# =========================
# FIX RESOURCE PATH 
# =========================
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


class PlateModel:
    def __init__(self, model_type="yolov8", conf_threshold=0.5):
        self.conf_threshold = conf_threshold

        # =========================
        # 1. LOAD TỪ FILE .PT
        # =========================
        if isinstance(model_type, str) and model_type.endswith(".pt"):
            model_path = os.path.basename(model_type)

            # FIX PATH KHI BUILD EXE
            if not os.path.exists(model_path):
                model_path = resource_path(os.path.join("models_weight", model_path))
                print("MODEL PATH:", model_path)
                print("FILE EXISTS:", os.path.exists(model_path))

            # auto chọn backend
            if "frcnn" in model_path.lower():
                self.model = FasterRCNNBackend(model_path)
                backend = "FasterRCNN"
            else:
                self.model = YOLOBackend(model_path)
                backend = "YOLO"

            print(f"PlateModel loaded: {model_path} ({backend})")

        # =========================
        # 2. LEGACY MODE
        # =========================
        elif model_type == "yolov8":
            self.model = YOLOBackend(resource_path("models_weight/LicensePlateV8s.pt"))

        elif model_type == "yolo26":
            self.model = YOLOBackend(resource_path("models_weight/LicensePlate26s.pt"))

        elif model_type == "fasterrcnn":
            self.model = FasterRCNNBackend(resource_path("models_weight/FRCNN_MobileNet_LicensePlate.pt"))

        else:
            raise ValueError("Invalid plate model type")

    # =========================
    # PREDICT
    # =========================
    def predict(self, image):
        try:
            results = self.model.predict(image)

            if not results:
                return None

            results = [
                r for r in results
                if r.get("confidence", 0) >= self.conf_threshold
            ]

            if not results:
                return None

            results.sort(key=lambda x: x.get("confidence", 0), reverse=True)
            best = results[0]

            if "bbox" not in best or "crop" not in best:
                return None

            return {
                "bbox": best.get("bbox"),
                "confidence": float(best.get("confidence", 0)),
                "crop": best.get("crop")
            }

        except Exception as e:
            print("PlateModel error:", e)
            return None
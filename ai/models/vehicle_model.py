from ai.backends.yolo_backend import YOLOBackend
from ai.backends.faster_rcnn_backend import FasterRCNNBackend
import os
import sys


# =========================
# PATH 
# =========================
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


class VehicleModel:
    CLASS_MAP = {
        0: "motorbike",
        1: "car"
    }

    def __init__(self, model_type="yolov8", conf_threshold=0.5):
        self.conf_threshold = conf_threshold

        # =========================
        # 1. LOAD FILE .PT
        # =========================
        if isinstance(model_type, str) and model_type.endswith(".pt"):
            model_path = os.path.basename(model_type)

            if not os.path.exists(model_path):
                model_path = resource_path(os.path.join("models_weight", model_path))

            if "frcnn" in model_path.lower():
                self.model = FasterRCNNBackend(model_path)
                backend = "FasterRCNN"
            else:
                self.model = YOLOBackend(model_path)
                backend = "YOLO"

            print(f"VehicleModel loaded: {model_path} ({backend})")

        # =========================
        # 2. LEGACY MODE
        # =========================
        elif model_type == "yolov8":
            self.model = YOLOBackend(resource_path("models_weight/VehicleV8s.pt"))

        elif model_type == "yolo26":
            self.model = YOLOBackend(resource_path("models_weight/Vehicle26s.pt"))

        elif model_type == "fasterrcnn":
            self.model = FasterRCNNBackend(resource_path("models_weight/frcnn_mobilenet_vehicle.pt"))

        else:
            raise ValueError("Invalid vehicle model type")

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

            class_id = best.get("class")

            if isinstance(class_id, int):
                class_name = self.CLASS_MAP.get(class_id, "unknown")
            else:
                class_name = class_id

            return {
                "bbox": best.get("bbox"),
                "confidence": float(best.get("confidence", 0)),
                "class": class_name,
                "crop": best.get("crop")
            }

        except Exception as e:
            print("VehicleModel error:", e)
            return None
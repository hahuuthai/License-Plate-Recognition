import torch
import numpy as np
from torchvision.models.detection import fasterrcnn_mobilenet_v3_large_fpn
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor


class FasterRCNNBackend:
    def __init__(self, model_path):
        try:
            print("Loading FRCNN:", model_path)

            # =========================
            # FIX PYTORCH 2.6 LOAD
            # =========================
            state_dict = torch.load(
                model_path,
                map_location="cpu",
                weights_only=False
            )

            # =========================
            # AUTO DETECT NUM_CLASSES
            # =========================
            cls_weight = state_dict["roi_heads.box_predictor.cls_score.weight"]
            num_classes = cls_weight.shape[0]

            print(f"Detected num_classes = {num_classes}")

            # =========================
            # INIT MODEL
            # =========================
            self.model = fasterrcnn_mobilenet_v3_large_fpn(weights=None)

            in_features = self.model.roi_heads.box_predictor.cls_score.in_features

            self.model.roi_heads.box_predictor = FastRCNNPredictor(
                in_features, num_classes
            )

            # =========================
            # LOAD WEIGHT
            # =========================
            self.model.load_state_dict(state_dict)

            # =========================
            # FIX CPU
            # =========================
            self.model.to("cpu")

            self.model.eval()

            print("FRCNN loaded OK")

        except Exception as e:
            print("Load FRCNN lỗi:", e)
            raise

    def predict(self, image):
        if not isinstance(image, np.ndarray):
            raise ValueError("Input must be numpy image")

        img_tensor = torch.from_numpy(image).permute(2, 0, 1).float() / 255

        with torch.no_grad():
            preds = self.model([img_tensor])[0]

        output = []

        for i in range(len(preds["boxes"])):
            conf = float(preds["scores"][i])

            if conf < 0.5:
                continue

            x1, y1, x2, y2 = map(int, preds["boxes"][i])

            h, w = image.shape[:2]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)

            crop = image[y1:y2, x1:x2]

            cls = int(preds["labels"][i])

            output.append({
                "bbox": [x1, y1, x2, y2],
                "class": cls,
                "confidence": conf,
                "crop": crop
            })

        return output
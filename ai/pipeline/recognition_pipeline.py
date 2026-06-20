import cv2


class RecognitionPipeline:
    def __init__(self, vehicle_model, plate_model, ocr_model):
        self.vehicle_model = vehicle_model
        self.plate_model = plate_model
        self.ocr_model = ocr_model

    # =========================
    # MAIN PIPELINE
    # =========================
    def process(self, frame, do_ocr=True):
        # ===== 1. VEHICLE =====
        vehicle = self.vehicle_model.predict(frame)
        if vehicle is None:
            return None

        vehicle_crop = vehicle.get("crop")
        if vehicle_crop is None:
            return None

        # ===== 2. PLATE =====
        plate = self.plate_model.predict(vehicle_crop)
        if plate is None:
            return None

        plate_crop = plate.get("crop")
        if plate_crop is None:
            return None

        # ===== 3. OCR =====
        text, conf = None, 0.0

        if do_ocr:
            text, conf = self.run_ocr_multi(plate_crop)

            if not text or conf < 0.5:
                return None

        # ===== 4. RESULT =====
        return {
            "plate": text,
            "confidence": float(conf),
            "vehicle_type": vehicle.get("class"),

            "vehicle_bbox": vehicle.get("bbox"),
            "plate_bbox": self._map_bbox(
                plate.get("bbox"),
                vehicle.get("bbox")
            ),

            "vehicle_crop": vehicle_crop,
            "plate_crop": plate_crop
        }

    # =========================
    # OCR MULTI METHOD
    # =========================
    def preprocess_methods(self, img):
        methods = []

        # original
        methods.append(("original", img))

        # resize
        resize = cv2.resize(img, None, fx=2, fy=2)
        methods.append(("resize", resize))

        # clahe
        gray = cv2.cvtColor(resize, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        clahe_img = clahe.apply(gray)
        methods.append(("clahe", clahe_img))

        # threshold
        thresh = cv2.adaptiveThreshold(
            clahe_img,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,
            2
        )
        methods.append(("thresh", thresh))

        return methods

    def run_ocr_multi(self, plate_crop):
        candidates = []

        methods = self.preprocess_methods(plate_crop)

        for name, img in methods:
            try:
                text, conf = self.ocr_model.read(img)

                if text:
                    clean_text = self._clean_text(text)

                    candidates.append({
                        "method": name,
                        "text": clean_text,
                        "conf": float(conf)
                    })

            except Exception as e:
                print(f"OCR error ({name}):", e)

        return self.select_best_candidate(candidates)

    # =========================
    # SELECT BEST
    # =========================
    def select_best_candidate(self, candidates):
        if not candidates:
            return None, 0.0

        candidates = [c for c in candidates if len(c["text"]) >= 5]

        if not candidates:
            return None, 0.0

        candidates = sorted(candidates, key=lambda x: x["conf"], reverse=True)

        best = candidates[0]

        print("OCR candidates:")
        for c in candidates:
            print(c)

        print("BEST:", best)

        return best["text"], best["conf"]

    # =========================
    # CLEAN TEXT
    # =========================
    def _clean_text(self, text):
        text = text.upper()
        text = text.replace(" ", "")
        text = text.replace(".", "")
        text = text.replace("-", "")
        text = text.replace(":", "")

        replace_map = {
            "O": "0",
            "I": "1",
            "Z": "2",
            "S": "5",
            "B": "8"
        }

        for k, v in replace_map.items():
            text = text.replace(k, v)

        return text

    # =========================
    # MAP BBOX
    # =========================
    def _map_bbox(self, plate_bbox, vehicle_bbox):
        if plate_bbox is None or vehicle_bbox is None:
            return None

        px1, py1, px2, py2 = plate_bbox
        vx1, vy1, _, _ = vehicle_bbox

        return [
            px1 + vx1,
            py1 + vy1,
            px2 + vx1,
            py2 + vy1
        ]
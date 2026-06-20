import time


class RecognitionService:
    def __init__(self, pipeline, cooldown=3, max_cache=100):
        self.pipeline = pipeline
        self.last_seen = {}
        self.cooldown = cooldown
        self.max_cache = max_cache

        # control FPS
        self.last_time = 0
        self.min_interval = 0.05  # ~20 FPS

    # =========================
    # REALTIME (KHÔNG OCR)
    # =========================
    def recognize(self, frame):
        now = time.time()

        # ===== LIMIT FPS =====
        if now - self.last_time < self.min_interval:
            return None

        self.last_time = now

        try:
            result = self.pipeline.process(frame, do_ocr=False)
        except Exception as e:
            print("Realtime error:", e)
            return None

        return result

    # =========================
    # CAPTURE (CÓ OCR)
    # =========================
    def recognize_with_ocr(self, frame):
        try:
            result = self.pipeline.process(frame, do_ocr=True)
        except Exception as e:
            print("OCR error:", e)
            return None

        if result is None:
            return None

        plate = result.get("plate")
        if not plate:
            return None

        now = time.time()

        # ===== COOLDOWN =====
        if plate in self.last_seen:
            if now - self.last_seen[plate] < self.cooldown:
                print("⏳ Cooldown:", plate)
                return None

        self.last_seen[plate] = now

        # ===== CLEAN CACHE =====
        if len(self.last_seen) > self.max_cache:
            self._cleanup_cache()

        return result

    # =========================
    # CLEAN MEMORY
    # =========================
    def _cleanup_cache(self):
        now = time.time()

        # giữ lại các plate mới
        self.last_seen = {
            k: v for k, v in self.last_seen.items()
            if now - v < self.cooldown
        }
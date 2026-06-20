from paddleocr import PaddleOCR
import re


class OCRModel:
    def __init__(self):
        self.ocr = PaddleOCR(
            use_angle_cls=False,   # nhanh hơn
            lang='en',
            show_log=False
        )

    def read(self, image):
        try:
            result = self.ocr.ocr(image, cls=False)

            if not result or not result[0]:
                return None, 0

            texts = []
            confs = []

            for line in result[0]:
                if len(line) < 2:
                    continue

                text = line[1][0]
                conf = line[1][1]

                if text:
                    texts.append(text)
                    confs.append(conf)

            if not texts:
                return None, 0

            # ghép text
            text = "".join(texts)

            # clean ký tự 
            text = self._clean_plate(text)

            conf = sum(confs) / len(confs)

            return text, conf

        except Exception as e:
            print("OCR error:", e)
            return None, 0

    # =========================
    # CLEAN BIỂN SỐ
    # =========================
    def _clean_plate(self, text):
        text = text.upper()

        # bỏ ký tự rác
        text = re.sub(r"[^A-Z0-9]", "", text)

        return text
from datetime import datetime


class ParkingService:
    def __init__(self, db):
        self.db = db

    # =========================
    # XỬ LÝ XE (IN / OUT)
    # =========================
    def process_vehicle(self, result, mode="in"):
        if result is None:
            return {
                "status": "error",
                "message": "Không nhận diện được"
            }

        plate = result.get("plate")
        vehicle_type = result.get("vehicle_type")

        if not plate:
            return {
                "status": "error",
                "message": "Không có biển số"
            }

        if mode == "in":
            return self._vehicle_in(plate, vehicle_type, result)

        elif mode == "out":
            return self._vehicle_out(plate)

        return {
            "status": "error",
            "message": "Mode không hợp lệ"
        }

    # =========================
    # XE VÀO
    # =========================
    def _vehicle_in(self, plate, vehicle_type, result):
        if self.db.is_vehicle_inside(plate):
            return {
                "status": "error",
                "message": "Xe chưa ra"
            }

        # ===== LẤY IMAGE PATH TỪ UI =====
        image_path = result.get("image_path")
        plate_image_path = result.get("plate_image_path")

        self.db.insert_vehicle(
            plate=plate,
            vehicle_type=vehicle_type,
            image_path=result.get("image_path"),
            plate_image_path=result.get("plate_image_path")
        )

        data = self.db.get_vehicle_in(plate)

        return {
            "status": "success",
            "message": "Xe vào",
            "data": data
        }

    # =========================
    # XE RA
    # =========================
    def _vehicle_out(self, plate):
        if not self.db.is_vehicle_inside(plate):
            return {
                "status": "error",
                "message": "Không tìm thấy xe trong bãi"
            }

        self.db.update_vehicle_out(plate)

        data = self.db.search(plate=plate)

        return {
            "status": "success",
            "message": "Xe ra",
            "data": data[0] if data else None
        }
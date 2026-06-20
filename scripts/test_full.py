import cv2

from ai.pipeline.recognition_pipeline import RecognitionPipeline
from ai.models.vehicle_model import VehicleModel
from ai.models.plate_model import PlateModel
from ai.models.ocr_model import OCRModel

from database.db_manager import DatabaseManager
from services.parking_service import ParkingService


# ===== INIT =====
vehicle_model = VehicleModel("yolov8")
plate_model = PlateModel("yolov8")
ocr_model = OCRModel()

pipeline = RecognitionPipeline(vehicle_model, plate_model, ocr_model)

db = DatabaseManager()
parking_service = ParkingService(db)


# ===== LOAD IMAGE =====
frame = cv2.imread("C:/DoAnTN/Dataset/Car/frame_15.jpg")


# ===== RECOGNIZE =====
result = pipeline.process(frame)
print("Nhận diện:", result)


# ===== XE VÀO =====
res_in = parking_service.process_vehicle(result, mode="in")
print("Xe vào:", res_in)


# ===== XE RA =====
res_out = parking_service.process_vehicle(result, mode="out")
print("Xe ra:", res_out)


# ===== CHECK DB =====
print("\n===== DATABASE =====")
for row in db.get_history():
    print(row)


db.close()
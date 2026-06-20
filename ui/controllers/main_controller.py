import cv2
from PIL import Image, ImageTk

from ai.pipeline.recognition_pipeline import RecognitionPipeline
from ai.models.vehicle_model import VehicleModel
from ai.models.plate_model import PlateModel
from ai.models.ocr_model import OCRModel

from services.recognition_service import RecognitionService
from services.parking_service import ParkingService
from database.db_manager import DatabaseManager


class MainController:
    def __init__(self, camera_view, control_panel, root):
        self.camera_view = camera_view
        self.control_panel = control_panel
        self.root = root

        # ===== INIT SYSTEM =====
        vehicle_model = VehicleModel("yolov8")
        plate_model = PlateModel("yolov8")
        ocr_model = OCRModel()

        pipeline = RecognitionPipeline(
            vehicle_model,
            plate_model,
            ocr_model
        )

        self.recognition_service = RecognitionService(pipeline)
        self.db = DatabaseManager()
        self.parking_service = ParkingService(self.db)

        self.cap = cv2.VideoCapture(0)
        self.current_result = None

        # bind events
        self.control_panel.btn_capture.config(command=self.capture)
        self.control_panel.btn_save.config(command=self.save)
        self.control_panel.btn_delete.config(command=self.clear)

        self.update_frame()

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return

        result = self.recognition_service.recognize(frame)

        if result:
            self.current_result = result
            self.control_panel.plate_var.set(result["plate"])

            x1, y1, x2, y2 = result["vehicle_bbox"]
            px1, py1, px2, py2 = result["plate_bbox"]

            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.rectangle(frame, (px1, py1), (px2, py2), (0, 0, 255), 2)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        imgtk = ImageTk.PhotoImage(image=img)

        self.camera_view.update(imgtk)

        self.root.after(30, self.update_frame)

    def capture(self):
        if self.current_result:
            self.control_panel.plate_var.set(self.current_result["plate"])

    def save(self):
        if not self.current_result:
            return

        mode = self.control_panel.mode_var.get()

        response = self.parking_service.process_vehicle(
            self.current_result,
            mode
        )

        print(response)

    def clear(self):
        self.control_panel.plate_var.set("")
        self.current_result = None
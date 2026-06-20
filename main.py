import sys
import os

import os, subprocess, ctypes

def ensure_vc():
    try:
        ctypes.CDLL("msvcp140.dll")
    except:
        vc = os.path.join(os.getcwd(), "vc_redist.x64.exe")
        if os.path.exists(vc):
            subprocess.run([vc, "/quiet", "/norestart"])

ensure_vc()

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk
import cv2
import os
import threading
import logging
from datetime import datetime
from difflib import SequenceMatcher
import numpy as np

# ===== IMPORT AI =====
from ai.models.vehicle_model import VehicleModel
from ai.models.plate_model import PlateModel
from ai.models.ocr_model import OCRModel
from ai.pipeline.recognition_pipeline import RecognitionPipeline

# ===== SERVICES =====
from services.recognition_service import RecognitionService
from services.parking_service import ParkingService

# ===== DB =====
from database.db_manager import DatabaseManager


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_DIR = resource_path("models_weight")

BASE_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.getcwd()

IMAGE_DIR = os.path.join(BASE_DIR, "data/images")
PLATE_DIR = os.path.join(BASE_DIR, "data/plates")

os.makedirs(IMAGE_DIR, exist_ok=True)
os.makedirs(PLATE_DIR, exist_ok=True)


# =========================
# CAMERA VIEW
# =========================
class CameraView:
    def __init__(self, parent, cam_id, title, vehicle_type, parking_service):
        self.vehicle_type = vehicle_type
        self.parking_service = parking_service
        self.cam_id = cam_id

        self.current_frame = None
        self.captured_image = None
        self._recognition_service = None
        self._service_lock = threading.Lock()
        self.frame_count = 0

        # ===== OCR REALTIME =====
        self.realtime_ocr = tk.BooleanVar(value=False)
        self.last_plate_text = ""

        # ===== UI =====
        self.frame = tk.Frame(parent, bg="#2c2c2c")
        self.frame.pack(side=tk.LEFT, expand=True, fill="both", padx=10, pady=10)

        # Thanh tiêu đề + dropdown + nút đổi camera trên cùng một hàng
        title_row = tk.Frame(self.frame, bg="#2c2c2c")
        title_row.pack(fill="x", pady=5)

        # Đặt Label vào title_row (không phải self.frame)
        tk.Label(title_row, text=title, font=("Arial", 18, "bold"),
                fg="white", bg="#2c2c2c").pack(side=tk.LEFT, padx=5)

        self.cam_id_var = tk.IntVar(value=cam_id)
        self.available_cams = self._scan_cameras()
        self.cam_menu = tk.OptionMenu(title_row, self.cam_id_var, *self.available_cams)
        self.cam_menu.pack(side=tk.LEFT, padx=5)

        self.btn_connect = tk.Button(title_row, text="🔄 Đổi Camera", command=self.change_camera)
        self.btn_connect.pack(side=tk.LEFT, padx=5)

        # Realtime detection state (background thread)
        self._live_result = None          # latest bbox result from bg thread
        self._live_result_lock = threading.Lock()
        self._detecting = False           # throttle flag


        self.video = tk.Label(self.frame, bg="#1a1a1a")
        self.video.pack()

        # Plate entry
        plate_frame = tk.Frame(self.frame, bg="#2c2c2c")
        plate_frame.pack(pady=5)
        tk.Label(plate_frame, text="Biển số:", fg="white",
                 bg="#2c2c2c", font=("Arial", 12)).pack(side=tk.LEFT)
        self.plate_text = tk.StringVar()
        tk.Entry(plate_frame, textvariable=self.plate_text,
                 font=("Arial", 16), width=14).pack(side=tk.LEFT, padx=5)

        # Status label
        self.status_var = tk.StringVar(value="Sẵn sàng")
        tk.Label(self.frame, textvariable=self.status_var,
                 fg="#aaffaa", bg="#2c2c2c", font=("Arial", 10)).pack()

        # ===== MODEL SELECT =====
        mf = tk.Frame(self.frame, bg="#2c2c2c")
        mf.pack(pady=3)

        vehicle_models = self._list_models("vehicle")
        plate_models = self._list_models("plate")

        self.vehicle_model_var = tk.StringVar(
            value=vehicle_models[0] if vehicle_models else "")
        self.plate_model_var = tk.StringVar(
            value=plate_models[0] if plate_models else "")

        if vehicle_models:
            tk.OptionMenu(mf, self.vehicle_model_var,
                          *vehicle_models).pack(side=tk.LEFT)
        if plate_models:
            tk.OptionMenu(mf, self.plate_model_var,
                          *plate_models).pack(side=tk.LEFT)

        tk.Button(mf, text="Load Model",
                  command=self.reload_model).pack(side=tk.LEFT, padx=4)

        # ===== IN / OUT =====
        mode_frame = tk.Frame(self.frame, bg="#2c2c2c")
        mode_frame.pack(pady=3)
        tk.Label(mode_frame, text="Chế độ:", fg="white",
                 bg="#2c2c2c").pack(side=tk.LEFT)
        self.mode_var = tk.StringVar(value="in")
        tk.OptionMenu(mode_frame, self.mode_var, "in", "out").pack(side=tk.LEFT)

        # ===== BUTTONS =====
        bf = tk.Frame(self.frame, bg="#2c2c2c")
        bf.pack(pady=10)

        tk.Button(bf, text="📸 Chụp", width=12, height=2,
                  command=self.capture).pack(side=tk.LEFT, padx=5)
        tk.Button(bf, text="💾 Lưu", width=12, height=2,
                  command=self.save).pack(side=tk.LEFT, padx=5)
        tk.Button(bf, text="❌ Xóa", width=12, height=2,
                  command=self.clear).pack(side=tk.LEFT, padx=5)
        
        # ===== REALTIME OCR TOGGLE =====
        tk.Checkbutton(
            self.frame,
            text="OCR Realtime",
            variable=self.realtime_ocr,
            fg="white",
            bg="#2c2c2c",
            selectcolor="#2c2c2c",
            activebackground="#2c2c2c",
            activeforeground="white"
        ).pack()

        # Preview + plate crop side by side
        preview_row = tk.Frame(self.frame, bg="#2c2c2c")
        preview_row.pack(pady=5)

        preview_col = tk.Frame(preview_row, bg="#2c2c2c")
        preview_col.pack(side=tk.LEFT, padx=5)
        tk.Label(preview_col, text="Ảnh chụp", fg="gray",
                 bg="#2c2c2c", font=("Arial", 9)).pack()
        self.preview = tk.Label(preview_col, bg="#1a1a1a")
        self.preview.pack()

        plate_col = tk.Frame(preview_row, bg="#2c2c2c")
        plate_col.pack(side=tk.LEFT, padx=5)
        tk.Label(plate_col, text="Biển số cắt", fg="gray",
                 bg="#2c2c2c", font=("Arial", 9)).pack()
        self.plate_preview = tk.Label(plate_col, bg="#1a1a1a")
        self.plate_preview.pack()

        # ===== CAMERA =====
        self.cap = None
        self._open_camera(cam_id)

    # --------------------------------------------------
    def _list_models(self, keyword):
        if not os.path.isdir(MODEL_DIR):
            return []
        return [f for f in os.listdir(MODEL_DIR)
                if keyword.lower() in f.lower()]

    def _open_camera(self, cam_id):
        """Giải phóng cam cũ và mở kết nối tới cam_id mới"""
        # 1. Giải phóng camera hiện tại nếu đang mở
        if self.cap is not None:
            self.cap.release()
            
        # 2. Thử mở cổng cam mới
        self.cap = cv2.VideoCapture(cam_id)
        
        if not self.cap.isOpened():
            # Nếu lỗi, hiển thị thông báo và tạo frame đen cảnh báo
            self.status_var.set(f"⚠ Lỗi kết nối Camera {cam_id}")
            self.error_frame = np.zeros((280, 400, 3), dtype=np.uint8)
            cv2.putText(self.error_frame, f"Camera {cam_id} Not Found", (50, 140),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            self.cap = None
        else:
            # Nếu thành công, lưu ID và xóa trạng thái lỗi
            self.cam_id = cam_id
            self.error_frame = None
            self.status_var.set(f"Camera {cam_id} sẵn sàng")

    @property
    def recognition_service(self):
        with self._service_lock:
            return self._recognition_service

    @recognition_service.setter
    def recognition_service(self, value):
        with self._service_lock:
            self._recognition_service = value

    def set_service(self, s):
        self.recognition_service = s

    def _scan_cameras(self):
        """Quét và trả về danh sách các ID camera đang hoạt động (0-4)"""
        available = []
        for i in range(5):  # Kiểm tra 5 cổng đầu tiên
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    available.append(i)
                cap.release()
        return available if available else [0] # Mặc định trả về 0 nếu không thấy gì
    
    def change_camera(self):
        """Lấy ID từ Dropdown và thực hiện chuyển đổi"""
        new_id = self.cam_id_var.get() # Lấy giá trị từ OptionMenu
        
        # Cập nhật trạng thái chờ trên UI
        self.status_var.set(f"⏳ Đang chuyển sang Cam {new_id}...")
        
        # Gọi hàm mở camera để thực thi logic chuyển đổi
        self._open_camera(new_id)

    # =========================
    # LOAD MODEL (THREAD-SAFE)
    # =========================
    def reload_model(self):
        def load():
            self.frame.after(0, lambda: self.status_var.set("⏳ Đang load model..."))
            try:
                v_name = self.vehicle_model_var.get()
                p_name = self.plate_model_var.get()
                if not v_name or not p_name:
                    raise ValueError("Chưa chọn model")

                v_path = os.path.join(MODEL_DIR, v_name)
                p_path = os.path.join(MODEL_DIR, p_name)

                v = VehicleModel(v_path)
                p = PlateModel(p_path)
                o = OCRModel()

                pipe = RecognitionPipeline(v, p, o)
                # Tạo service riêng cho từng camera
                self.recognition_service = RecognitionService(pipe)

                self.frame.after(0, lambda: self.status_var.set("✅ Model đã load"))
                self.frame.after(0, lambda:
                    messagebox.showinfo("Model", "Load thành công"))

            except Exception as e:
                logger.error(f"Load model lỗi: {e}")
                self.frame.after(0, lambda: self.status_var.set("❌ Load model lỗi"))
                self.frame.after(0, lambda:
                    messagebox.showerror("Error", str(e)))

        threading.Thread(target=load, daemon=True).start()

    # =========================
    # UPDATE CAMERA (main thread — render only)
    # =========================
    def update(self):
        if self.cap is None or not self.cap.isOpened():
            # HIỂN THỊ FRAME LỖI
            if hasattr(self, "error_frame") and self.error_frame is not None:
                frame_rgb = cv2.cvtColor(self.error_frame, cv2.COLOR_BGR2RGB)
                img = ImageTk.PhotoImage(Image.fromarray(frame_rgb))
                self.video.imgtk = img
                self.video.configure(image=img)
            return

        ret, frame = self.cap.read()
        if not ret:
            return

        self.current_frame = frame.copy()
        self.frame_count += 1

        # Kick off background detection every 10 frames (non-blocking)
        service = self.recognition_service
        if service and self.frame_count % 10 == 0 and not self._detecting:
            self._detecting = True
            snapshot = frame.copy()
            threading.Thread(
                target=self._detect_live,
                args=(service, snapshot),
                daemon=True
            ).start()

        # Draw latest cached result — zero blocking
        with self._live_result_lock:
            result = self._live_result

        if result:
            vb = result.get("vehicle_bbox")
            pb = result.get("plate_bbox")
            plate_text = result.get("plate", "")

            if self.realtime_ocr.get() and self.last_plate_text:
                plate_text = self.last_plate_text

            if vb:
                x1, y1, x2, y2 = vb
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            if pb:
                px1, py1, px2, py2 = pb
                cv2.rectangle(frame, (px1, py1), (px2, py2), (0, 0, 255), 2)
                if plate_text:
                    cv2.putText(frame, plate_text, (px1, max(py1 - 8, 0)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                                (0, 0, 255), 2)

        h, w = frame.shape[:2]
        scale = min(400 / w, 280 / h)
        new_w, new_h = int(w * scale), int(h * scale)

        resized = cv2.resize(frame, (new_w, new_h))

        canvas = 255 * np.ones((280, 400, 3), dtype="uint8")
        y_offset = (280 - new_h) // 2
        x_offset = (400 - new_w) // 2
        canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized

        frame_rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
        img = ImageTk.PhotoImage(Image.fromarray(frame_rgb))
        self.video.imgtk = img
        self.video.configure(image=img)

    def _detect_live(self, service, frame):
        """Realtime detect background"""

        try:
            # ===== OCR REALTIME =====
            if self.realtime_ocr.get():
                result = service.recognize_with_ocr(frame)
            else:
                result = service.recognize(frame)

            if result and result.get("vehicle_type") == self.vehicle_type:

                # update realtime plate text
                if self.realtime_ocr.get():
                    plate = result.get("plate", "")
                    if plate:
                        self.last_plate_text = plate

                        self.frame.after(
                            0,
                            lambda: self.plate_text.set(plate)
                        )

                with self._live_result_lock:
                    self._live_result = result

            else:
                with self._live_result_lock:
                    self._live_result = None

        except Exception as e:
            logger.warning(f"Live detect lỗi: {e}")

        finally:
            self._detecting = False

    # =========================
    # CAPTURE -> detect ngay từ ảnh chụp
    # =========================
    def capture(self):
        if self.cap is None or not self.cap.isOpened():
            messagebox.showwarning("Lỗi", "Camera chưa sẵn sàng")
            return

        # CHỤP FRAME GỐC TỪ CAMERA 
        ret, frame = self.cap.read()
        if not ret:
            messagebox.showerror("Lỗi", "Không chụp được ảnh")
            return

        self.captured_image = frame.copy()

        # ===== HIỂN THỊ PREVIEW =====
        h, w = frame.shape[:2]
        scale = min(250 / w, 180 / h)
        preview = cv2.resize(frame, (int(w * scale), int(h * scale)))

        preview_rgb = cv2.cvtColor(preview, cv2.COLOR_BGR2RGB)
        img_tk = ImageTk.PhotoImage(Image.fromarray(preview_rgb))
        self.preview.configure(image=img_tk)
        self.preview.imgtk = img_tk

        # reset UI
        self.plate_preview.configure(image="")
        self.plate_preview.imgtk = None
        self.plate_text.set("")
        self.status_var.set("⏳ Đang nhận dạng...")

        # detect trong thread riêng
        threading.Thread(target=self._detect_from_capture, daemon=True).start()

    def _detect_from_capture(self):
        """Chạy trong background thread, cập nhật UI qua frame.after()"""
        service = self.recognition_service

        if service is None:
            self.frame.after(0, lambda: self.status_var.set(
            "⚠ Chưa load model - nhập biển số thủ công"))
            return

        try:
            frame = self.captured_image.copy()

            # detect trên ảnh capture (KHÔNG dùng realtime)
            result = service.recognize_with_ocr(frame)

            if result and result.get("vehicle_type") == self.vehicle_type:

                plate = result.get("plate", "")
                plate_bbox = result.get("plate_bbox")
                vehicle_bbox = result.get("vehicle_bbox")

                # ===== VẼ BBOX =====
                annotated = frame.copy()

                if vehicle_bbox:
                    x1, y1, x2, y2 = map(int, vehicle_bbox)
                    #cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)

                if plate_bbox:
                    px1, py1, px2, py2 = map(int, plate_bbox)
                    #cv2.rectangle(annotated, (px1, py1), (px2, py2), (0, 0, 255), 2)

                    """if plate:
                        cv2.putText(annotated, plate, (px1, max(py1 - 10, 0)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.9,
                                    (0, 0, 255), 2)"""

                # ===== CẮT BIỂN SỐ =====
                plate_crop_tk = None
                self.plate_image_path = None

                if plate_bbox:
                    px1, py1, px2, py2 = map(int, plate_bbox)

                    h, w = frame.shape[:2]

                    # clamp tránh out-of-bound
                    px1, py1 = max(0, px1), max(0, py1)
                    px2, py2 = min(w, px2), min(h, py2)

                    crop = frame[py1:py2, px1:px2]

                    if crop.size > 0:
                        # resize để hiển thị
                        h_c, w_c = crop.shape[:2]
                        scale = min(200 / w_c, 80 / h_c)

                        new_w, new_h = int(w_c * scale), int(h_c * scale)
                        crop_resized = cv2.resize(crop, (new_w, new_h))
                        crop_rgb = cv2.cvtColor(crop_resized, cv2.COLOR_BGR2RGB)
                        plate_crop_tk = ImageTk.PhotoImage(Image.fromarray(crop_rgb))

                        # CHỈ GIỮ crop trong RAM (KHÔNG LƯU FILE)
                        self.plate_crop_image = crop
                        self.plate_image_path = None

                # ===== PREVIEW  =====
                h, w = annotated.shape[:2]
                scale = min(250 / w, 180 / h)
                annotated = cv2.resize(annotated, (int(w * scale), int(h * scale)))

                prev_rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
                prev_tk = ImageTk.PhotoImage(Image.fromarray(prev_rgb))

                # ===== UPDATE UI =====
                def update_ui():
                    self.preview.configure(image=prev_tk)
                    self.preview.imgtk = prev_tk

                    if plate_crop_tk:
                        self.plate_preview.configure(image=plate_crop_tk)
                        self.plate_preview.imgtk = plate_crop_tk

                    if plate:
                        self.plate_text.set(plate)
                        self.status_var.set(f"Nhận dạng: {plate}")
                    else:
                        self.status_var.set("⚠ Không đọc được OCR – nhập thủ công")

                self.frame.after(0, update_ui)

            else:
                self.frame.after(0, lambda: self.status_var.set(
                    "⚠ Không phát hiện xe/biển số phù hợp"))

        except Exception as e:
            logger.error(f"Detect capture lỗi: {e}")
            self.frame.after(0, lambda: self.status_var.set(
                f"Lỗi nhận dạng: {e}"))
    # =========================
    def save(self):
        if self.captured_image is None:
            messagebox.showwarning("Lỗi", "Chưa chụp ảnh")
            return

        plate = self.plate_text.get().strip()
        if not plate:
            messagebox.showwarning("Lỗi", "Không có biển số (nhập thủ công nếu cần)")
            return

        filename = f"{plate}.jpg"
        path = os.path.join(IMAGE_DIR, filename)

        # ===== LƯU ẢNH XE =====
        ok = cv2.imwrite(path, self.captured_image)
        if not ok:
            messagebox.showerror("Lỗi", f"Không ghi được file: {path}")
            return

        # ===== LƯU ẢNH BIỂN SỐ (CHỈ KHI SAVE) =====
        plate_path = None

        if hasattr(self, "plate_crop_image") and self.plate_crop_image is not None:
            plate_filename = f"crop_{plate}.jpg"
            plate_path = os.path.join(PLATE_DIR, plate_filename)

            # GHI ĐÈ nếu đã tồn tại
            cv2.imwrite(plate_path, self.plate_crop_image)

        # ===== DATA =====
        data = {
            "plate": plate,
            "vehicle_type": self.vehicle_type,
            "image_path": path,
            "plate_image_path": plate_path
        }

        try:
            res = self.parking_service.process_vehicle(
                data, mode=self.mode_var.get())
            messagebox.showinfo("Thông báo", res["message"])
            self.clear()
        except Exception as e:
            # DB lỗi → xóa file ảnh đã lưu để tránh rác
            logger.error(f"process_vehicle lỗi: {e}")
            try:
                os.remove(path)
            except OSError:
                pass
            messagebox.showerror("Lỗi", f"Xử lý thất bại: {e}")

    # =========================
    def clear(self):
        self.captured_image = None

        # reset preview ảnh chụp
        self.preview.configure(image="")
        self.preview.imgtk = None

        # reset preview biển số
        self.plate_preview.configure(image="")
        self.plate_preview.imgtk = None

        # reset text
        self.plate_text.set("")
        self.status_var.set("Sẵn sàng")

        
        self.plate_crop_image = None
        self.plate_image_path = None   

    def release(self):
        if self.cap:
            self.cap.release()


# =========================
# MANAGER UI
# =========================
class ManagerUI:
    def __init__(self, root, db):
        self.db = db
        self.selected_items = {}

        self.win = tk.Toplevel(root)
        self.win.title("Quản lý bãi xe")
        self.win.state('zoomed')
        self.win.protocol("WM_DELETE_WINDOW", self.on_close)

        # ===== TOP BAR =====
        top = tk.Frame(self.win)
        top.pack(fill="x", padx=10, pady=6)

        tk.Label(top, text="Tìm biển số:",
                 font=("Arial", 12)).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        tk.Entry(top, textvariable=self.search_var,
                 font=("Arial", 13), width=18).pack(side=tk.LEFT, padx=5)
        tk.Button(top, text="🔍 Tìm",
                  command=self.search).pack(side=tk.LEFT)
        tk.Button(top, text="↩ Tất cả",
                  command=lambda: self.load(None)).pack(side=tk.LEFT, padx=5)

        # ===== SCROLLABLE CANVAS =====
        container = tk.Frame(self.win)
        container.pack(fill="both", expand=True, padx=10, pady=5)

        self.canvas = tk.Canvas(container)
        scrollbar = ttk.Scrollbar(container, orient="vertical",
                                   command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill="y")
        self.canvas.pack(side=tk.LEFT, fill="both", expand=True)

        self.inner_frame = tk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.inner_frame, anchor="nw")

        self.inner_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        
        # ===== SELECTED ITEM =====
        self.selected_id = tk.IntVar(value=-1)

        # ===== DELETE BUTTON =====
        btn_frame = tk.Frame(self.win)
        btn_frame.pack(fill="x", pady=5)

        tk.Button(btn_frame, text="🗑 XÓA", 
                    command=self.delete_selected,
                        bg="#ff4444", fg="white").pack(side=tk.RIGHT, padx=10)
        # ===== BACK BUTTON =====
        tk.Button(btn_frame, text="⬅ Quay lại",
                    command=self.on_close,
                    bg="#4444ff", fg="white").pack(side=tk.LEFT, padx=10)
        
        self.load(None)

    def _on_frame_configure(self, event):
        self.canvas.configure(
            scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def similarity(self, a, b):
        return SequenceMatcher(None, a.upper(), b.upper()).ratio()

    def load(self, data):

        # RESET CHECKBOX STATE
        self.selected_items.clear()
        for w in self.inner_frame.winfo_children():
            w.destroy()

        if data is None:
            data = self.db.get_all()

        if not data:
            tk.Label(self.inner_frame, text="Không có dữ liệu",
                     font=("Arial", 14), pady=20).pack()
            return

        for item in data:
            card = tk.Frame(self.inner_frame, bd=1,
                            relief="ridge", pady=4, padx=4, bg="white")
            card.pack(fill="x", pady=4)

            # ===== CHECK BOX =====
            item_id = item.get("id")

            var = tk.BooleanVar()
            self.selected_items[item_id] = var

            chk = tk.Checkbutton(card, variable=var, bg="white")
            chk.pack(side=tk.LEFT, padx=5)

            info = (
                f"Biển số : {item.get('plate', '')}\n"
                f"Loại xe : {item.get('vehicle_type', '')}\n"
                f"Vào     : {item.get('time_in', '')}\n"
                f"Ra      : {item.get('time_out', '') or '—'}"
            )
            label = tk.Label(card, text=info, font=("Courier", 11),
                     justify=tk.LEFT, bg="white")
            label.pack(side=tk.LEFT, padx=10)
            # ===== CLICK → OPEN DETAIL =====
            label.bind("<Button-1>", lambda e, item=item: self.open_detail(item))

    def search(self):
        keyword = self.search_var.get().strip()
        if not keyword:
            self.load(None)
            return

        data = self.db.get_all()
        scored = sorted(
            data,
            key=lambda item: self.similarity(keyword, item.get("plate", "")),
            reverse=True
        )
        self.load(scored)
    
    def delete_selected(self):
        selected_ids = [
            item_id for item_id, var in self.selected_items.items()
            if var.get()
        ]

        if not selected_ids:
            messagebox.showwarning("Lỗi", "Chưa chọn dòng nào")
            return

        confirm = messagebox.askyesno(
            "Xác nhận",
            f"Xóa {len(selected_ids)} bản ghi?"
        )
        if not confirm:
            return

        try:
            for record_id in selected_ids:
                item = next((x for x in self.db.get_all() if x["id"] == record_id), None)

                if item:
                    # XÓA ẢNH GỐC
                    if item.get("image_path") and os.path.exists(item["image_path"]):
                        os.remove(item["image_path"])

                    # XÓA ẢNH BIỂN SỐ
                    if item.get("plate_image_path") and os.path.exists(item["plate_image_path"]):
                        os.remove(item["plate_image_path"])

                self.db.delete_by_id(record_id)

            messagebox.showinfo("OK", "Đã xóa thành công")

            # reload lại list
            self.selected_items.clear()
            self.load(None)

        except Exception as e:
            messagebox.showerror("Lỗi", str(e))

    def open_detail(self, item):
        # ẨN window hiện tại
        self.win.withdraw()

        DetailWindow(self.win, item)
    
    def on_close(self):
        self.win.destroy()
        self.win.master.deiconify()  
        self.win.master.state('zoomed')

# =========================
# DETAIL WINDOW
# =========================
class DetailWindow:
    def __init__(self, parent, item):
        self.parent = parent

        self.win = tk.Toplevel(parent)
        self.win.title("Chi tiết xe")
        self.win.state('zoomed')
        

        # ===== INFO =====
        info = (
            f"Biển số : {item.get('plate', '')}\n"
            f"Loại xe : {item.get('vehicle_type', '')}\n"
            f"Vào     : {item.get('time_in', '')}\n"
            f"Ra      : {item.get('time_out', '') or '—'}"
        )

        tk.Label(self.win, text=info,
                 font=("Courier", 12),
                 justify=tk.LEFT).pack(pady=10)

        # ===== IMAGE =====
        img_path = item.get("image_path", "")

        if img_path and os.path.exists(img_path):
            try:
                img = cv2.imread(img_path)
                h, w = img.shape[:2]
                scale = min(400 / w, 300 / h)
                img = cv2.resize(img, (int(w * scale), int(h * scale)))
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

                img_tk = ImageTk.PhotoImage(Image.fromarray(img))

                lbl = tk.Label(self.win, image=img_tk)
                lbl.image = img_tk
                lbl.pack()
            except:
                pass

        plate_img_path = item.get("plate_image_path", "")

        if plate_img_path and os.path.exists(plate_img_path):
            try:
                img = cv2.imread(plate_img_path)
                h, w = img.shape[:2]
                scale = min(300 / w, 150 / h)
                img = cv2.resize(img, (int(w * scale), int(h * scale)))
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

                img_tk = ImageTk.PhotoImage(Image.fromarray(img))

                tk.Label(self.win, text="Biển số", font=("Arial", 12, "bold")).pack()
                lbl = tk.Label(self.win, image=img_tk)
                lbl.image = img_tk
                lbl.pack()
            except:
                pass

        # ===== BACK BUTTON =====
        tk.Button(self.win, text="⬅ Quay lại",
                  command=self.go_back).pack(pady=10)

        # Khi đóng window
        self.win.protocol("WM_DELETE_WINDOW", self.go_back)

    def go_back(self):
        self.win.destroy()
        self.parent.deiconify()
        self.parent.state('zoomed')



# =========================
# MAIN UI
# =========================
class MainUI:
    def __init__(self, root):
        root.title("Hệ thống bãi đỗ xe")
        root.configure(bg="#2c2c2c")
        root.state('zoomed')

        self.db = DatabaseManager()
        # AUTO CLEAN 30 NGÀY
        self.db.clean_old_records(30)
        self.parking = ParkingService(self.db)

        # ===== TOP BAR =====
        top = tk.Frame(root, bg="#1e1e1e")
        top.pack(fill="x")

        tk.Label(top, text="🅿 Parking System", font=("Arial", 16, "bold"),
                 fg="white", bg="#1e1e1e", pady=8).pack(side=tk.LEFT, padx=10)

        tk.Button(top, text="📊 Quản lý",
            command=lambda: self.open_manager(root)
        ).pack(side=tk.RIGHT, padx=10, pady=5)

        # ===== CAMERA AREA =====
        main = tk.Frame(root, bg="#2c2c2c")
        main.pack(fill="both", expand=True)

        self.cam1 = CameraView(main, 0, "🛵 Xe máy", "motorbike", self.parking)
        self.cam2 = CameraView(main, 1, "🚗 Ô tô", "car", self.parking)

        # ===== LOAD DEFAULT MODEL (từng camera dùng pipeline riêng) =====
        def load_default():
            for cam, label in [(self.cam1, "cam1"), (self.cam2, "cam2")]:
                try:
                    v = VehicleModel(os.path.join(MODEL_DIR, "VehicleV8s.pt"))
                    p = PlateModel(os.path.join(MODEL_DIR, "LicensePlateV8s.pt"))
                    o = OCRModel()
                    pipe = RecognitionPipeline(v, p, o)
                    service = RecognitionService(pipe)
                    cam.set_service(service)
                    logger.info(f"Default model loaded for {label}")
                except Exception as e:
                    logger.error(f"Load default model lỗi ({label}): {e}")

        threading.Thread(target=load_default, daemon=True).start()

        root.protocol("WM_DELETE_WINDOW", lambda: self._on_close(root))
        self._loop(root)

    def _loop(self, root):
        self.cam1.update()
        self.cam2.update()
        root.after(50, lambda: self._loop(root))

    def _on_close(self, root):
        self.cam1.release()
        self.cam2.release()
        root.destroy()
    
    def open_manager(self, root):
        root.withdraw()  # ẨN màn detect

        ManagerUI(root, self.db)


# =========================
# RUN
# =========================
if __name__ == "__main__":
    root = tk.Tk()
    MainUI(root)
    root.mainloop()
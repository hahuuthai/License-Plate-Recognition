# License-Plate-Recognition
A deep learning-based, real-time License Plate Recognition (LPR) system tailored for Vietnamese traffic and parking management contexts. Built with high performance in mind, this desktop application processes live camera streams with an end-to-end processing time of **~200ms on standard CPUs** without requiring a dedicated GPU, avoiding UI freezing using advanced multi-threading techniques.

## 🌟 Key Features
- **Cascaded AI Pipeline:** Separate, dedicated models for vehicle detection and license plate isolation to drastically reduce spatial noise and optimize small-object detection.
- **Robust OCR Engine:** Integrated PaddleOCR to handle complex lighting variations (overexposure, nighttime, low-light), tilted plates, and motion blur.
- **Custom Post-Processing Algorithms:**
  - **Y-center Clustering:** A mathematical approach to accurately split, sort, and parse dual-line motorbike license plates common in Vietnam.
  - **Replace-Map Regularization:** Contextual character filters to resolve classic OCR ambiguities (e.g., misidentifying `O`/`0`, `I`/`1`, `S`/`5`, `B`/`8`) based on Vietnamese plate formats.
- **Asynchronous Architecture:** Implemented via Python's native multi-threading to cleanly decouple the heavy computer vision inference loop from the Tkinter GUI thread.
- **Lightweight Local Storage:** Local SQLite database configuration storing timestamps, check-in/out statuses, extracted license texts, and compressed image crop references.

---

## 🛠️ System Architecture & AI Pipeline

The application processes raw input frames through a 3-stage cascaded pipeline:
[Camera Stream / Video Input] - Stage 1: Vehicle Detect ──► YOLOv8s Model (Isolates Cars / Motorbikes) - Stage 2: Plate Detection ──► YOLO26s with Attention Mechanism (Crops Plate) - Stage 3: Advanced OCR   ──► CLAHE + Adaptive Thresholding ──► PaddleOCR - [Post-Processing: Y-center Sorting & Regularization Map] ──► Save to SQLite

1. **Vehicle Detection (YOLOv8s):** Localizes and crops vehicles from the main scene to strip away background noise.
2. **License Plate Localization (YOLO26s with Attention):** Pinpoints the precise bounding boxes of the license plates within the vehicle crops.
3. **Character Recognition & Formatting (PaddleOCR + Algorithms):** Normalizes the image via CLAHE and Adaptive Thresholding before extracting the alphanumeric text array.

---

## 📊 Experimental Performance Results

The system was evaluated against a standalone `Faster R-CNN + MobileNetV3` alternative. The dual-stage YOLO architecture exhibited superior speed-to-accuracy trade-offs:

| Metric | Vehicle Detection (YOLOv8s) | Plate Detection (YOLO26s) | Standalone Faster R-CNN Alternative |
| :--- | :---: | :---: | :---: |
| **Input Size** | 640x640 | 416x416 | 640x640 |
| **mAP@50 Accuracy** | **96.4%** | **95.2%** | 89.7% |
| **Inference Time (CPU)** | ~45 ms | ~35 ms | ~180 ms |

- **OCR Accuracy (Single-line Plates):** **94.8%**
- **OCR Accuracy (Dual-line Plates):** **91.3%** *(via Y-center Clustering algorithm)*
- **Total End-to-End Latency:** **~200ms** (~5 FPS on standard office CPUs).

---

## ⚙️ Tech Stack & Dependencies
- **Core Language:** Python 3.10+
- **Deep Learning Frameworks:** PyTorch, Ultralytics (YOLOv8), PaddlePaddle (PaddleOCR)
- **Computer Vision Utilities:** OpenCV (cv2)
- **Database Architecture:** SQLite3
- **User Interface:** Tkinter

---

## 🚀 Getting Started

### 1. Clone the Repository
```bash
git clone [https://github.com/yourusername/license-plate-recognition-lpr.git](https://github.com/yourusername/license-plate-recognition-lpr.git)
cd license-plate-recognition-lpr

2. Install Required Packages
We recommend setting up a virtual environment (e.g., venv or conda) before installing dependencies:
pip install -r requirements.requirements
(Make sure to install the appropriate torch/paddlepaddle versions depending on whether you intend to deploy on CPU or GPU).

3. Running the Application
To launch the desktop parking application interface:
python main.py
Future Enhancements
Color-coded Plate Identification: Expand detection capabilities to categorize public, diplomatic, military, and commercial vehicles based on background plate colors.
Model Quantization: Incorporate OpenVINO or ONNX Runtime INT8 quantization to double CPU frame rates.
Enterprise DB Integration: Migrate the localized database access layer from SQLite to a centralized SQL Server client-server model to support multi-lane synchronization.

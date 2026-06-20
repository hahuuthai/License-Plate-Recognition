import tkinter as tk

class CameraView:
    def __init__(self, root):
        self.label = tk.Label(root)
        self.label.pack()

    def update(self, image):
        self.label.imgtk = image
        self.label.configure(image=image)
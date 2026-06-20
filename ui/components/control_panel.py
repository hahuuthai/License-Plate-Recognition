import tkinter as tk

class ControlPanel:
    def __init__(self, root):
        self.frame = tk.Frame(root)
        self.frame.pack(pady=10)

        self.plate_var = tk.StringVar()

        self.entry = tk.Entry(self.frame, textvariable=self.plate_var, font=("Arial", 16))
        self.entry.grid(row=0, column=0, columnspan=3)

        self.mode_var = tk.StringVar(value="in")
        self.mode_menu = tk.OptionMenu(self.frame, self.mode_var, "in", "out")
        self.mode_menu.grid(row=1, column=0)

        self.btn_capture = tk.Button(self.frame, text="📸 Capture")
        self.btn_capture.grid(row=1, column=1)

        self.btn_save = tk.Button(self.frame, text="💾 Save")
        self.btn_save.grid(row=1, column=2)

        self.btn_delete = tk.Button(self.frame, text="❌ Delete")
        self.btn_delete.grid(row=1, column=3)
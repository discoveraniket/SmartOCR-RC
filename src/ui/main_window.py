import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import logging
import os
from src.core.coordinator import PipelineCoordinator
from src.utils.threading import run_in_background

logger = logging.getLogger(__name__)

class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("RC-PaddleOCR v2")
        self.geometry("800x600")
        self.coordinator = PipelineCoordinator()
        self.setup_ui()

    def setup_ui(self):
        # Header
        header = ttk.Label(self, text="RC-PaddleOCR Processor", font=("Helvetica", 16, "bold"))
        header.pack(pady=20)

        # Controls
        controls_frame = ttk.Frame(self)
        controls_frame.pack(fill=tk.X, padx=20)

        self.select_btn = ttk.Button(controls_frame, text="Select Image", command=self.select_image)
        self.select_btn.pack(side=tk.LEFT, padx=5)

        self.process_btn = ttk.Button(controls_frame, text="Run Pipeline", command=self.start_processing, state=tk.DISABLED)
        self.process_btn.pack(side=tk.LEFT, padx=5)

        # Status
        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Log view
        self.log_text = tk.Text(self, height=20)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        self.selected_path = None

    def select_image(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.tiff")]
        )
        if file_path:
            self.selected_path = file_path
            self.status_var.set(f"Selected: {os.path.basename(file_path)}")
            self.process_btn.config(state=tk.NORMAL)

    def start_processing(self):
        if not self.selected_path:
            return

        self.process_btn.config(state=tk.DISABLED)
        self.status_var.set("Processing...")
        
        # Run in background to keep UI responsive
        run_in_background(self.coordinator.process_image, self.selected_path, callback=self.on_processing_finished)

    def on_processing_finished(self, result):
        self.status_var.set("Processing Complete")
        self.process_btn.config(state=tk.NORMAL)
        if result:
            messagebox.showinfo("Success", f"Processing finished successfully!\nCategory: {result.get('category')}\nID: {result.get('id')}")
        else:
            messagebox.showerror("Error", "Processing failed. Check logs for details.")

if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()

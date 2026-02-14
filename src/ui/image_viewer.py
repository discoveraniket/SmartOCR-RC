import customtkinter as ctk
import os
import logging
from PIL import Image, ImageTk
from tkinter import messagebox, Canvas
from src.core.result_handler import ResultDataHandler

logger = logging.getLogger(__name__)

class ZoomableImageCanvas(Canvas):
    """
    A custom Canvas widget that supports zooming and panning.
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs, highlightthickness=0, bg="#2b2b2b")
        
        self.pil_image = None
        self.image_id = None
        self.base_image = None # The scaled image to fit the window
        
        self.scale = 1.0
        self.orig_width = 0
        self.orig_height = 0
        
        # Bind events
        self.bind("<MouseWheel>", self._on_mousewheel) # Windows
        self.bind("<Button-4>", self._on_mousewheel)   # Linux Scroll Up
        self.bind("<Button-5>", self._on_mousewheel)   # Linux Scroll Down
        
        self.bind("<ButtonPress-1>", self._on_button_press)
        self.bind("<B1-Motion>", self._on_mouse_drag)
        self.bind("<Configure>", self._on_resize)
        
        self.last_x = 0
        self.last_y = 0

    def _on_resize(self, event):
        # When canvas is resized, reset to fit if we were already in "fit" mode
        # or just ensure the current image stays centered. 
        # For "autoscale to fit", we reset scale to 1.0 and redraw.
        self.scale = 1.0
        self.show_image()

    def set_image(self, pil_image):
        self.pil_image = pil_image
        self.orig_width, self.orig_height = pil_image.size
        self.scale = 1.0
        self.show_image()

    def show_image(self):
        if self.pil_image is None:
            return

        self.delete("all")
        
        # Calculate size based on scale
        width = int(self.orig_width * self.scale)
        height = int(self.orig_height * self.scale)
        
        # If scale is 1.0, we fit it to the canvas initially
        if self.scale == 1.0:
            cw = self.winfo_width()
            ch = self.winfo_height()
            if cw > 1 and ch > 1: # Ensure canvas has size
                ratio = min(cw / self.orig_width, ch / self.orig_height)
                self.scale = ratio
                width = int(self.orig_width * self.scale)
                height = int(self.orig_height * self.scale)

        resized_image = self.pil_image.resize((width, height), Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(resized_image)
        
        # Center initially or keep relative position? 
        # For now, center if it's the first load or just created
        # Use actual current dimensions for centering
        canvas_width = self.winfo_width()
        canvas_height = self.winfo_height()
        
        self.image_id = self.create_image(canvas_width // 2, canvas_height // 2, 
                                          image=self.tk_image, anchor="center")

    def _on_mousewheel(self, event):
        # Respond to Windows (event.delta) or Linux (event.num)
        if event.num == 4 or event.delta > 0:
            self.scale *= 1.1
        elif event.num == 5 or event.delta < 0:
            self.scale /= 1.1
        
        # Constrain scale
        self.scale = max(0.1, min(self.scale, 5.0))
        self.show_image()

    def _on_button_press(self, event):
        self.last_x = event.x
        self.last_y = event.y

    def _on_mouse_drag(self, event):
        if self.image_id:
            dx = event.x - self.last_x
            dy = event.y - self.last_y
            self.move(self.image_id, dx, dy)
            self.last_x = event.x
            self.last_y = event.y

class ImageViewerWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)

        self.title("Result Image Viewer & Editor")
        self.geometry("1400x900")
        
        self.transient(parent)
        self.grab_set()

        # Data Layer
        from src.utils.config import OCR_SETTINGS
        base_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(base_dir))
        
        output_dir_name = OCR_SETTINGS.get("default_output_dir", "output")
        output_dir = os.path.join(project_root, output_dir_name)
        results_csv = os.path.join(output_dir, "results.csv")
        
        self.handler = ResultDataHandler(results_csv, output_dir)
        self.current_rotation = 0
        self.entries = {}
        self.pil_image = None

        self.grid_columnconfigure(0, weight=4) # Image area
        self.grid_columnconfigure(1, weight=1) # Data area
        self.grid_rowconfigure(0, weight=1)

        self.setup_ui()
        self.after(200, self.load_current_item) # Delay to allow canvas winfo_width to update

    def setup_ui(self):
        # --- Left Side: Image Area ---
        self.image_container = ctk.CTkFrame(self)
        self.image_container.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.image_container.grid_rowconfigure(0, weight=1)
        self.image_container.grid_columnconfigure(0, weight=1)
        
        # Use our custom Zoomable Canvas
        self.canvas = ZoomableImageCanvas(self.image_container)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        # Image Controls
        self.img_controls = ctk.CTkFrame(self.image_container, fg_color="transparent")
        self.img_controls.grid(row=1, column=0, pady=10)
        
        self.rotate_btn = ctk.CTkButton(self.img_controls, text="Rotate 90°", width=100, command=self.rotate_image)
        self.rotate_btn.pack(side="left", padx=5)
        
        self.reset_zoom_btn = ctk.CTkButton(self.img_controls, text="Reset View", width=100, command=self.reset_view)
        self.reset_zoom_btn.pack(side="left", padx=5)

        # --- Right Side: Data Editor ---
        self.data_frame = ctk.CTkFrame(self)
        self.data_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        ctk.CTkLabel(self.data_frame, text="Extracted Data", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=20)

        self.fields_container = ctk.CTkScrollableFrame(self.data_frame, fg_color="transparent")
        self.fields_container.pack(expand=True, fill="both", padx=10)

        # Bottom Buttons
        self.nav_frame = ctk.CTkFrame(self.data_frame, fg_color="transparent")
        self.nav_frame.pack(fill="x", side="bottom", pady=20)

        self.prev_btn = ctk.CTkButton(self.nav_frame, text="< Prev", width=80, command=self.prev_item)
        self.prev_btn.pack(side="left", padx=10)

        self.save_btn = ctk.CTkButton(self.nav_frame, text="Save Edits", fg_color="green", hover_color="darkgreen", command=self.save_edits)
        self.save_btn.pack(side="left", expand=True, padx=10)

        self.next_btn = ctk.CTkButton(self.nav_frame, text="Next >", width=80, command=self.next_item)
        self.next_btn.pack(side="right", padx=10)

    def load_current_item(self):
        item = self.handler.get_current_item()
        if not item:
            return

        # 1. Update Image
        self.current_rotation = 0
        img_path = self.handler.get_image_path(item)
        
        if img_path and os.path.exists(img_path):
            try:
                self.pil_image = Image.open(img_path)
                self.canvas.set_image(self.pil_image)
            except Exception as e:
                logger.error(f"Failed to load image: {e}")

        # 2. Update Data Fields
        for widget in self.fields_container.winfo_children():
            widget.destroy()
        
        self.entries = {}
        for key, value in item.items():
            if key == "processed_image_name": continue
            
            field_frame = ctk.CTkFrame(self.fields_container, fg_color="transparent")
            field_frame.pack(fill="x", pady=5)
            
            ctk.CTkLabel(field_frame, text=f"{key}:", font=ctk.CTkFont(weight="bold")).pack(side="top", anchor="w")
            entry = ctk.CTkEntry(field_frame)
            entry.insert(0, str(value))
            entry.pack(side="top", fill="x", pady=(0, 5))
            self.entries[key] = entry

    def rotate_image(self):
        if self.pil_image:
            self.pil_image = self.pil_image.rotate(-90, expand=True)
            self.canvas.set_image(self.pil_image)

    def reset_view(self):
        if self.pil_image:
            self.canvas.set_image(self.pil_image)

    def save_edits(self):
        updated_data = {k: v.get() for k, v in self.entries.items()}
        if self.handler.save_edit(self.handler.current_index, updated_data):
            messagebox.showinfo("Saved", "Data updated successfully.")

    def next_item(self):
        if self.handler.next_item():
            self.load_current_item()

    def prev_item(self):
        if self.handler.prev_item():
            self.load_current_item()

import customtkinter as ctk
from PIL import Image, ImageTk
from tkinter import Canvas

class ZoomableImageCanvas(Canvas):
    """
    A custom Tkinter Canvas for displaying images with zoom and pan capabilities.
    """
    def __init__(self, master, **kwargs):
        # Default styling for the OCR application
        defaults = {
            "highlightthickness": 0,
            "bg": "#1d1d1d"
        }
        defaults.update(kwargs)
        super().__init__(master, **defaults)
        
        self.pil_image = None
        self.image_id = None
        self.scale = 1.0
        self.orig_width = 0
        self.orig_height = 0
        
        self.bind("<MouseWheel>", self._on_mousewheel)
        self.bind("<ButtonPress-1>", self._on_button_press)
        self.bind("<B1-Motion>", self._on_mouse_drag)
        self.bind("<Configure>", self._on_resize)
        self.last_x = 0
        self.last_y = 0

    def _on_resize(self, event):
        self.scale = 1.0
        self.show_image()

    def set_image(self, pil_image):
        self.pil_image = pil_image
        if pil_image:
            self.orig_width, self.orig_height = pil_image.size
        self.scale = 1.0
        self.show_image()

    def show_image(self):
        if self.pil_image is None:
            self.delete("all")
            return
            
        self.delete("all")
        width = int(self.orig_width * self.scale)
        height = int(self.orig_height * self.scale)
        
        # Initial fit-to-screen logic
        if self.scale == 1.0:
            cw, ch = self.winfo_width(), self.winfo_height()
            if cw > 1 and ch > 1:
                ratio = min(cw / self.orig_width, ch / self.orig_height)
                self.scale = ratio
                width, height = int(self.orig_width * self.scale), int(self.orig_height * self.scale)

        # Use Lanczos for high-quality downsampling
        resized_image = self.pil_image.resize((width, height), Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(resized_image)
        self.image_id = self.create_image(
            self.winfo_width() // 2, 
            self.winfo_height() // 2, 
            image=self.tk_image, 
            anchor="center"
        )

    def _on_mousewheel(self, event):
        # Zoom in/out relative to current scale
        self.scale *= 1.1 if event.delta > 0 else 0.9
        self.scale = max(0.1, min(self.scale, 10.0))
        self.show_image()

    def _on_button_press(self, event):
        self.last_x, self.last_y = event.x, event.y

    def _on_mouse_drag(self, event):
        if self.image_id:
            self.move(self.image_id, event.x - self.last_x, event.y - self.last_y)
            self.last_x, self.last_y = event.x, event.y
            
    def reset_view(self):
        """Resets scale to fit the window."""
        self.scale = 1.0
        self.show_image()

import customtkinter as ctk
import os
import logging
from PIL import Image, ImageTk
from tkinter import messagebox, Canvas
from src.core.result_handler import ResultDataHandler
from src.utils.image_processing import ImageProcessingService
from src.utils.config import KEY_MAP

logger = logging.getLogger(__name__)

class ZoomableImageCanvas(Canvas):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs, highlightthickness=0, bg="#1d1d1d")
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
        self.orig_width, self.orig_height = pil_image.size
        self.scale = 1.0
        self.show_image()

    def show_image(self):
        if self.pil_image is None: return
        self.delete("all")
        width = int(self.orig_width * self.scale)
        height = int(self.orig_height * self.scale)
        if self.scale == 1.0:
            cw, ch = self.winfo_width(), self.winfo_height()
            if cw > 1 and ch > 1:
                ratio = min(cw / self.orig_width, ch / self.orig_height)
                self.scale = ratio
                width, height = int(self.orig_width * self.scale), int(self.orig_height * self.scale)

        resized_image = self.pil_image.resize((width, height), Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(resized_image)
        self.image_id = self.create_image(self.winfo_width() // 2, self.winfo_height() // 2, image=self.tk_image, anchor="center")

    def _on_mousewheel(self, event):
        self.scale *= 1.1 if event.delta > 0 else 0.9
        self.scale = max(0.1, min(self.scale, 10.0))
        self.show_image()

    def _on_button_press(self, event):
        self.last_x, self.last_y = event.x, event.y

    def _on_mouse_drag(self, event):
        if self.image_id:
            self.move(self.image_id, event.x - self.last_x, event.y - self.last_y)
            self.last_x, self.last_y = event.x, event.y

class ImageViewerWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Result Image Viewer & Editor")
        self.geometry("1400x950")
        # Removed self.transient(parent) to allow minimize/maximize buttons

        from src.utils.config import OCR_SETTINGS, LLM_SETTINGS
        base_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(base_dir))
        self.output_dir = os.path.join(project_root, OCR_SETTINGS.get("default_output_dir", "output"))
        self.handler = ResultDataHandler(os.path.join(self.output_dir, "results.csv"), self.output_dir)
        
        # Temp Overrides
        self.model_overrides = {
            "step1_model": LLM_SETTINGS.get("step1_model"),
            "text_to_JSON_model": LLM_SETTINGS.get("text_to_JSON_model"),
            "think": False
        }

        self.current_rotation = 0
        self.entries = {}
        self.pil_image = None

        self.grid_columnconfigure(0, weight=4)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.setup_ui()
        self.bind_shortcuts()
        self.after(200, self.load_current_item)

    def bind_shortcuts(self):
        self.bind(KEY_MAP["viewer_next"], lambda e: self.next_item())
        self.bind(KEY_MAP["viewer_prev"], lambda e: self.prev_item())
        self.bind(KEY_MAP["viewer_save_data"], lambda e: self.save_edits())
        self.bind(KEY_MAP["viewer_save_img"], lambda e: self.save_current_image())
        self.bind(KEY_MAP["viewer_rotate"], lambda e: self.rotate_image())
        self.bind(KEY_MAP["viewer_crop"], lambda e: self.auto_crop())
        self.bind(KEY_MAP["viewer_reprocess"], lambda e: self.reprocess_image())
        self.bind(KEY_MAP["viewer_settings"], lambda e: self.open_model_settings())
        self.bind(KEY_MAP["viewer_reset"], lambda e: self.reset_view())

    def setup_ui(self):
        self.image_container = ctk.CTkFrame(self)
        self.image_container.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.image_container.grid_rowconfigure(0, weight=1)
        self.image_container.grid_columnconfigure(0, weight=1)
        
        self.canvas = ZoomableImageCanvas(self.image_container)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self.img_controls = ctk.CTkFrame(self.image_container, fg_color="transparent")
        self.img_controls.grid(row=1, column=0, pady=10)
        
        # Helper to format key for display - now much simpler per request
        def fmt(key): 
            clean = key.replace("<Control-", "").replace(">", "").replace("Right", "→").replace("Left", "←").replace("Shift-", "")
            return f"[{clean.upper()}]"

        ctk.CTkButton(self.img_controls, text=f"Rotate\n{fmt(KEY_MAP['viewer_rotate'])}", width=100, command=self.rotate_image).pack(side="left", padx=5)
        ctk.CTkButton(self.img_controls, text=f"Auto Crop\n{fmt(KEY_MAP['viewer_crop'])}", width=100, fg_color="#6c757d", command=self.auto_crop).pack(side="left", padx=5)
        ctk.CTkButton(self.img_controls, text=f"Save Image\n{fmt(KEY_MAP['viewer_save_img'])}", width=100, fg_color="#dc3545", command=self.save_current_image).pack(side="left", padx=5)
        ctk.CTkButton(self.img_controls, text=f"Reset View\n{fmt(KEY_MAP['viewer_reset'])}", width=100, command=self.reset_view).pack(side="left", padx=5)

        self.data_frame = ctk.CTkFrame(self)
        self.data_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        # Directory Control
        dir_frame = ctk.CTkFrame(self.data_frame, fg_color="transparent")
        dir_frame.pack(fill="x", padx=10, pady=(10, 0))
        self.dir_label = ctk.CTkLabel(dir_frame, text=f"Dir: {os.path.basename(self.output_dir)}", font=ctk.CTkFont(size=11))
        self.dir_label.pack(side="left")
        ctk.CTkButton(dir_frame, text="Browse", width=60, height=24, command=self.browse_output_dir).pack(side="right")

        ctk.CTkLabel(self.data_frame, text="Extracted Data", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=20)

        self.fields_container = ctk.CTkScrollableFrame(self.data_frame, fg_color="transparent")
        self.fields_container.pack(expand=True, fill="both", padx=10)

        self.action_frame = ctk.CTkFrame(self.data_frame, fg_color="transparent")
        self.action_frame.pack(fill="x", side="bottom", pady=10, padx=10)

        self.reprocess_btn = ctk.CTkButton(self.action_frame, text=f"Re-process with AI\n{fmt(KEY_MAP['viewer_reprocess'])}", 
                                          fg_color="#1f538d", text_color="white", font=ctk.CTkFont(weight="bold"),
                                          command=self.reprocess_image)
        self.reprocess_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.settings_btn = ctk.CTkButton(self.action_frame, text=f"⚙\n{fmt(KEY_MAP['viewer_settings'])}", width=40, 
                                         fg_color="#4a4a4a", command=self.open_model_settings)
        self.settings_btn.pack(side="right")

        self.nav_frame = ctk.CTkFrame(self.data_frame, fg_color="transparent")
        self.nav_frame.pack(fill="x", side="bottom", pady=10, padx=10)
        
        self.prev_btn = ctk.CTkButton(self.nav_frame, text=f"< Prev\n{fmt(KEY_MAP['viewer_prev'])}", width=80, command=self.prev_item)
        self.prev_btn.pack(side="left")
        
        self.save_btn = ctk.CTkButton(self.nav_frame, text=f"Save Edits\n{fmt(KEY_MAP['viewer_save_data'])}", fg_color="#28a745", command=self.save_edits)
        self.save_btn.pack(side="left", expand=True, padx=10)
        
        self.next_btn = ctk.CTkButton(self.nav_frame, text=f"Next >\n{fmt(KEY_MAP['viewer_next'])}", width=80, command=self.next_item)
        self.next_btn.pack(side="right")

    def browse_output_dir(self):
        from tkinter import filedialog
        new_dir = filedialog.askdirectory(initialdir=self.output_dir)
        if new_dir:
            csv_path = os.path.join(new_dir, "results.csv")
            if not os.path.exists(csv_path):
                messagebox.showerror("Error", f"No results.csv found in selected directory:\n{new_dir}")
                self.focus_set()
                return
            
            self.output_dir = new_dir
            self.dir_label.configure(text=f"Dir: {os.path.basename(self.output_dir)}")
            self.handler = ResultDataHandler(csv_path, self.output_dir)
            self.load_current_item()
        self.focus_set()

    def open_model_settings(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Temp Model Override")
        dialog.geometry("400x350")
        dialog.transient(self)
        dialog.grab_set()
        
        from src.utils.config import LLM_SETTINGS
        available_models = LLM_SETTINGS.get("available_models", ["deepseek-r1:8b"])
        
        ctk.CTkLabel(dialog, text="Temporary Model Overrides", font=ctk.CTkFont(weight="bold")).pack(pady=10)
        
        ctk.CTkLabel(dialog, text="Cleaning Model (Step 1):").pack(pady=(10, 0))
        step1_menu = ctk.CTkOptionMenu(dialog, width=300, values=available_models)
        step1_menu.set(self.model_overrides["step1_model"])
        step1_menu.pack(pady=5)
        
        ctk.CTkLabel(dialog, text="JSON Model (Step 2):").pack(pady=(10, 0))
        json_menu = ctk.CTkOptionMenu(dialog, width=300, values=available_models)
        json_menu.set(self.model_overrides["text_to_JSON_model"])
        json_menu.pack(pady=5)
        
        think_var = ctk.BooleanVar(value=self.model_overrides["think"])
        ctk.CTkCheckBox(dialog, text="Enable Thinking (Step 1)", variable=think_var).pack(pady=10)
        
        def apply():
            self.model_overrides.update({
                "step1_model": step1_menu.get(), 
                "text_to_JSON_model": json_menu.get(), 
                "think": think_var.get()
            })
            dialog.destroy()
            messagebox.showinfo("Applied", "Overrides set.")
            self.focus_set()
            
        ctk.CTkButton(dialog, text="Apply Locally", command=apply).pack(pady=20)

    def load_current_item(self):
        item = self.handler.get_current_item()
        if not item: return
        self.current_rotation = 0
        img_path = self.handler.get_image_path(item)
        if img_path and os.path.exists(img_path):
            try:
                self.pil_image = Image.open(img_path)
                self.canvas.set_image(self.pil_image)
            except: pass
        for widget in self.fields_container.winfo_children(): widget.destroy()
        self.entries = {}
        for key, value in item.items():
            if key == "processed_image_name": continue
            f = ctk.CTkFrame(self.fields_container, fg_color="transparent"); f.pack(fill="x", pady=2)
            ctk.CTkLabel(f, text=f"{key}:", font=ctk.CTkFont(weight="bold")).pack(side="top", anchor="w")
            e = ctk.CTkEntry(f); e.insert(0, str(value)); e.pack(side="top", fill="x"); self.entries[key] = e
            
        # Focus the 'category' entry if it exists
        if "category" in self.entries:
            self.entries["category"].focus_set()

    def reprocess_image(self):
        item = self.handler.get_current_item(); 
        if not item: return
        img_path = self.handler.get_image_path(item)
        self.reprocess_btn.configure(state="disabled", text="Processing...")
        from src.core.coordinator import PipelineCoordinator
        from src.utils.threading import run_in_background
        coord = PipelineCoordinator()
        def on_fin(res):
            def _update():
                self.reprocess_btn.configure(state="normal", text=f"Re-process with AI\n[A]")
                if res and "data" in res:
                    for k, v in self.entries.items():
                        if k in res["data"]: v.delete(0, "end"); v.insert(0, str(res["data"][k]))
                    
                    # Show duration in success message
                    metrics = res.get("metrics", {})
                    duration = metrics.get("ocr", 0) + metrics.get("step1", 0) + metrics.get("json", 0)
                    messagebox.showinfo("Success", f"Extraction complete in {duration:.2f}s.\n(OCR: {metrics.get('ocr', 0)}s, LLM: {metrics.get('step1', 0) + metrics.get('json', 0):.2f}s)")
                else: 
                    messagebox.showerror("Error", "Reprocessing failed.")
                self.focus_set()
            self.after(0, _update)
        run_in_background(coord.extract_data, img_path, model_overrides=self.model_overrides, callback=on_fin)

    def auto_crop(self):
        item = self.handler.get_current_item(); 
        if not item or not self.pil_image: return
        img_path = self.handler.get_image_path(item)
        from src.core.ocr_engine import OcrEngine
        from src.utils.threading import run_in_background
        ocr = OcrEngine()
        def on_ocr_finished(raw):
            def _update():
                if not raw: return
                results = raw[0] if raw else []
                ocr_data = [{"box": line[0], "text": line[1][0]} for line in results]
                from src.utils.config import OCR_SETTINGS
                bounds = ImageProcessingService.calculate_text_bounds(ocr_data, padding=int(OCR_SETTINGS.get("crop_padding", 20)))
                if bounds: 
                    self.pil_image = ImageProcessingService.crop_to_content(self.pil_image, bounds)
                    self.canvas.set_image(self.pil_image)
            self.after(0, _update)
        run_in_background(ocr.run_inference, img_path, callback=on_ocr_finished)

    def save_current_image(self):
        item = self.handler.get_current_item(); 
        if not item or not self.pil_image: return
        img_path = self.handler.get_image_path(item)
        if messagebox.askyesno("Confirm", "Overwrite original?"):
            if ImageProcessingService.save_image(self.pil_image, img_path): 
                messagebox.showinfo("Saved", "Image saved.")
        self.focus_set()

    def rotate_image(self):
        if self.pil_image: self.pil_image = self.pil_image.rotate(-90, expand=True); self.canvas.set_image(self.pil_image)
    def reset_view(self):
        if self.pil_image: self.canvas.set_image(self.pil_image)
    def save_edits(self):
        if self.handler.save_edit(self.handler.current_index, {k: v.get() for k, v in self.entries.items()}):
            messagebox.showinfo("Saved", "Data updated.")
        self.focus_set()
    def next_item(self):
        if self.handler.next_item(): self.load_current_item()
    def prev_item(self):
        if self.handler.prev_item(): self.load_current_item()

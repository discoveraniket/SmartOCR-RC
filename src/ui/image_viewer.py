import customtkinter as ctk
import os
import logging
from pathlib import Path
from PIL import Image
from tkinter import messagebox

from src.core.result_handler import ResultDataHandler
from src.utils.image_processing import ImageProcessingService
from src.utils.config import KEY_MAP, KEY_HINTS, OCR_SETTINGS, LLM_SETTINGS
from src.core.coordinator import PipelineCoordinator
from src.utils.threading import run_in_background
from src.ui.components.zoomable_canvas import ZoomableImageCanvas
from src.ui.ui_utils import ToastNotifier, format_shortcut, browse_directory

logger = logging.getLogger(__name__)

class ImageViewerWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("RC-PaddleOCR - Result Inspector")
        self.geometry("1500x950")
        
        # Configure grid for main window
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Initialize Data and Services
        project_root = Path(__file__).parents[2]
        self.output_dir = project_root / OCR_SETTINGS.get("default_output_dir", "output")
        self.handler = ResultDataHandler(str(self.output_dir / "results.csv"), str(self.output_dir))
        self.coordinator = PipelineCoordinator(output_dir=str(self.output_dir))
        
        self.model_overrides = {
            "step1_model": LLM_SETTINGS.get("step1_model"),
            "text_to_JSON_model": LLM_SETTINGS.get("text_to_JSON_model"),
            "think": False
        }

        self.pil_image = None
        self.entries = {}

        self._create_main_layout()
        self._bind_shortcuts()
        
        self.notifier = ToastNotifier(self.toast_label)
        self.after(200, self.load_current_item)

    def _get_btn_text(self, text: str, key_id: str) -> str:
        """Unifies the formatting of button labels and shortcut hints."""
        hint = KEY_HINTS.get(key_id, "")
        return f"{text} {hint}" if hint else text

    def _create_main_layout(self):
        """Creates the primary structural containers using a modern layout."""
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.main_container.grid_columnconfigure(0, weight=4) # Viewport
        self.main_container.grid_columnconfigure(1, weight=1) # Side Panel
        self.main_container.grid_rowconfigure(0, weight=1)

        # --- LEFT SIDE: Viewport Area ---
        self.viewport_frame = ctk.CTkFrame(self.main_container)
        self.viewport_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.viewport_frame.grid_rowconfigure(1, weight=1) # Canvas expands
        self.viewport_frame.grid_columnconfigure(0, weight=1)

        self._setup_viewport_top_bar()
        
        self.canvas = ZoomableImageCanvas(self.viewport_frame)
        self.canvas.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        self._setup_viewport_bottom_bar()

        # --- RIGHT SIDE: Data & Action Panel ---
        self.side_panel = ctk.CTkFrame(self.main_container, width=350)
        self.side_panel.grid(row=0, column=1, sticky="nsew")
        self._setup_side_panel_content()

    def _setup_viewport_top_bar(self):
        """Top bar for navigation and metadata."""
        self.top_bar = ctk.CTkFrame(self.viewport_frame, height=50, fg_color="transparent")
        self.top_bar.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        
        # Navigation group
        nav_group = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        nav_group.pack(side="left")
        
        ctk.CTkButton(nav_group, text=self._get_btn_text("<", "viewer_prev"), width=60, command=self.prev_item).pack(side="left", padx=2)
        
        self.count_label = ctk.CTkLabel(nav_group, text="0 / 0", font=ctk.CTkFont(size=13, weight="bold"))
        self.count_label.pack(side="left", padx=10)
        
        ctk.CTkButton(nav_group, text=self._get_btn_text(">", "viewer_next"), width=60, command=self.next_item).pack(side="left", padx=2)

        # File Info group
        info_group = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        info_group.pack(side="right")
        
        self.filename_label = ctk.CTkLabel(info_group, text="No File Selected", font=ctk.CTkFont(size=12))
        self.filename_label.pack(side="right", padx=10)
        
        self.dir_btn = ctk.CTkButton(
            info_group, text=f"📂 {self.output_dir.name}", 
            height=28, fg_color="transparent", border_width=1,
            command=self.browse_output_dir
        )
        self.dir_btn.pack(side="right", padx=5)

    def _setup_viewport_bottom_bar(self):
        """Bottom bar for image-specific tools."""
        self.tool_bar = ctk.CTkFrame(self.viewport_frame, height=50, fg_color="transparent")
        self.tool_bar.grid(row=2, column=0, sticky="ew", padx=10, pady=10)

        tools = [
            ("Rotate", "viewer_rotate", self.rotate_image, None),
            ("Auto-Crop", "viewer_crop", self.auto_crop, "#6c757d"),
            ("Reset Zoom", "viewer_reset", self.canvas.reset_view, None),
            ("Save Image", "viewer_save_img", self.save_current_image, "#dc3545")
        ]
        
        for text, key_id, cmd, color in tools:
            btn = ctk.CTkButton(
                self.tool_bar, text=self._get_btn_text(text, key_id), 
                width=110, height=32,
                command=cmd, 
                font=ctk.CTkFont(size=12)
            )
            if color: btn.configure(fg_color=color)
            btn.pack(side="left", padx=5)

    def _setup_side_panel_content(self):
        """Organizes the data entry and primary action buttons."""
        # Header
        header_frame = ctk.CTkFrame(self.side_panel, fg_color="transparent")
        header_frame.pack(fill="x", padx=15, pady=(20, 10))
        
        ctk.CTkLabel(header_frame, text="Extraction Data", font=ctk.CTkFont(size=20, weight="bold")).pack(side="left")
        
        # Font size controls
        font_ctrl_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        font_ctrl_frame.pack(side="right", padx=(10, 0))

        ctk.CTkButton(
            font_ctrl_frame, text="A+", width=30, height=28, 
            fg_color="transparent", border_width=1,
            command=lambda: self.change_font_size(2)
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            font_ctrl_frame, text="A-", width=30, height=28, 
            fg_color="transparent", border_width=1,
            command=lambda: self.change_font_size(-2)
        ).pack(side="left", padx=2)

        self.settings_btn = ctk.CTkButton(
            header_frame, text=self._get_btn_text("⚙", "viewer_settings"), 
            width=32, height=32, 
            fg_color="transparent", hover_color="#3B3B3B",
            command=self.open_model_settings
        )
        self.settings_btn.pack(side="right")

        # Scrollable fields
        self.fields_container = ctk.CTkScrollableFrame(self.side_panel, fg_color="transparent")
        self.fields_container.pack(expand=True, fill="both", padx=5)

        # Footer Actions
        self.footer = ctk.CTkFrame(self.side_panel, fg_color="transparent")
        self.footer.pack(fill="x", side="bottom", padx=15, pady=15)

        # Primary Action: Save
        self.save_btn = ctk.CTkButton(
            self.footer, text=self._get_btn_text("Save Changes", "viewer_save_data"),
            fg_color="#28a745", hover_color="#218838", height=40, font=ctk.CTkFont(weight="bold"),
            command=self.save_edits
        )
        self.save_btn.pack(fill="x", pady=(0, 10))

        # Secondary Actions
        sec_actions = ctk.CTkFrame(self.footer, fg_color="transparent")
        sec_actions.pack(fill="x")
        
        self.reprocess_btn = ctk.CTkButton(
            sec_actions, text=self._get_btn_text("AI Re-process", "viewer_reprocess"), height=32,
            command=self.reprocess_image
        )
        self.reprocess_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.log_btn = ctk.CTkButton(
            sec_actions, text=self._get_btn_text("Log", "viewer_view_log"), width=70, height=32,
            fg_color="#3B3B3B", command=self.view_log
        )
        self.log_btn.pack(side="left", padx=(0, 5))

        self.delete_btn = ctk.CTkButton(
            sec_actions, text="Delete", width=60, height=32, 
            fg_color="#b22222", hover_color="#8b0000",
            command=self.delete_current_item
        )
        self.delete_btn.pack(side="left")

        # Status/Toast
        self.toast_label = ctk.CTkLabel(self.side_panel, text="", font=ctk.CTkFont(size=12, weight="bold"))
        self.toast_label.pack(side="bottom", pady=10)

    def _bind_shortcuts(self):
        bindings = [
            (KEY_MAP["viewer_next"], self.next_item),
            (KEY_MAP["viewer_prev"], self.prev_item),
            (KEY_MAP["viewer_save_data"], self.save_edits),
            (KEY_MAP["viewer_save_img"], self.save_current_image),
            (KEY_MAP["viewer_rotate"], self.rotate_image),
            (KEY_MAP["viewer_crop"], self.auto_crop),
            (KEY_MAP["viewer_reprocess"], self.reprocess_image),
            (KEY_MAP["viewer_view_log"], self.view_log),
            (KEY_MAP["viewer_reset"], self.canvas.reset_view)
        ]
        for key, cmd in bindings:
            self.bind(key, lambda e, c=cmd: c())

    def load_current_item(self):
        item = self.handler.get_current_item()
        if not item: 
            self.count_label.configure(text="0 / 0")
            self.filename_label.configure(text="No results found")
            return
            
        total = len(self.handler.results)
        current = self.handler.current_index + 1
        self.count_label.configure(text=f"{current} / {total}")
        self.handler.save_last_index()

        image_name = item.get('processed_image_name', 'Unknown')
        self.filename_label.configure(text=image_name)

        img_path = self.handler.get_image_path(item)
        if img_path and os.path.exists(img_path):
            try:
                self.pil_image = Image.open(img_path)
                self.canvas.set_image(self.pil_image)
            except Exception as e:
                logger.error(f"Failed to load image: {e}")

        self._refresh_data_fields(item)

    def _refresh_data_fields(self, item):
        for widget in self.fields_container.winfo_children():
            widget.destroy()
        
        self.entries = {}
        font_size = OCR_SETTINGS.get("viewer_font_size", 15)
        
        for key, value in item.items():
            if key == "processed_image_name": continue
            
            field_frame = ctk.CTkFrame(self.fields_container, fg_color="transparent")
            field_frame.pack(fill="x", pady=8, padx=10)
            
            ctk.CTkLabel(
                field_frame, text=key.upper(), 
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="#888888"
            ).pack(side="top", anchor="w")
            
            entry_height = 32
            if font_size > 20:
                entry_height += (font_size - 20)
                
            entry = ctk.CTkEntry(field_frame, font=ctk.CTkFont(size=font_size), height=entry_height)
            entry.insert(0, str(value))
            entry.pack(side="top", fill="x", pady=(2, 0))
            self.entries[key] = entry
            
        if "category" in self.entries:
            self.entries["category"].focus_set()

    def change_font_size(self, delta: int):
        """Adjusts the text size in the entry fields centrally."""
        from src.utils.config import save_config
        
        # Update global setting
        new_size = max(8, min(80, OCR_SETTINGS.get("viewer_font_size", 15) + delta))
        OCR_SETTINGS["viewer_font_size"] = new_size
        
        # Persist to config.json
        save_config(OCR_SETTINGS, LLM_SETTINGS)
        
        # Apply to current UI
        for key, entry in self.entries.items():
            height = 32
            if new_size > 20:
                height += (new_size - 20)
                
            entry.configure(font=ctk.CTkFont(size=new_size), height=height)

    def browse_output_dir(self):
        new_dir = browse_directory(str(self.output_dir))
        if new_dir:
            csv_path = os.path.join(new_dir, "results.csv")
            if os.path.exists(csv_path):
                self.output_dir = Path(new_dir)
                self.dir_btn.configure(text=f"📂 {self.output_dir.name}")
                self.handler = ResultDataHandler(csv_path, str(self.output_dir))
                self.coordinator = PipelineCoordinator(output_dir=str(self.output_dir))
                self.load_current_item()
            else:
                messagebox.showerror("Error", "No results.csv found in selected directory.")
        self.focus_set()

    def save_edits(self):
        idx = self.handler.current_index
        new_data = {k: v.get() for k, v in self.entries.items()}
        
        # Rename files if ID/Category changed
        updated_name = self.handler.rename_item_files(
            idx, 
            new_data.get('category', 'UNKNOWN'), 
            new_data.get('id', 'UNKNOWN')
        )
        
        if self.handler.save_edit(idx, new_data):
            self.notifier.show("Updated ✓")
            if updated_name:
                self.filename_label.configure(text=updated_name)
        self.focus_set()

    def reprocess_image(self):
        item = self.handler.get_current_item()
        if not item: return
        
        img_path = self.handler.get_image_path(item)
        self.reprocess_btn.configure(state="disabled", text="AI Working...")
        
        def on_finished(pipeline_result):
            def _update_ui():
                self.reprocess_btn.configure(
                    state="normal", 
                    text=self._get_btn_text("AI Re-process", "viewer_reprocess")
                )
                if pipeline_result and pipeline_result.data:
                    data = pipeline_result.data
                    for k, v in self.entries.items():
                        if k in data:
                            v.delete(0, "end")
                            v.insert(0, str(data[k]))
                    self.notifier.show("AI Extraction Successful ✓")
                else: 
                    messagebox.showerror("Error", "AI reprocessing failed.")
                self.focus_set()
            self.after(0, _update_ui)
            
        run_in_background(
            self.coordinator.extract_data, 
            img_path, 
            model_overrides=self.model_overrides,
            callback=on_finished
        )

    def auto_crop(self):
        item = self.handler.get_current_item()
        if not item or not self.pil_image: return
        
        img_path = self.handler.get_image_path(item)
        from src.core.ocr_engine import OcrEngine
        ocr = OcrEngine()
        
        def on_ocr_finished(raw):
            def _update():
                if not raw: return
                results = raw[0] if raw else []
                ocr_data = [{"box": line[0], "text": line[1][0]} for line in results]
                bounds = ImageProcessingService.calculate_text_bounds(
                    ocr_data, 
                    padding=int(OCR_SETTINGS.get("crop_padding", 20))
                )
                if bounds: 
                    self.pil_image = ImageProcessingService.crop_to_content(self.pil_image, bounds)
                    self.canvas.set_image(self.pil_image)
            self.after(0, _update)
            
        run_in_background(ocr.run_inference, img_path, callback=on_ocr_finished)

    def rotate_image(self):
        if self.pil_image:
            self.pil_image = self.pil_image.rotate(-90, expand=True)
            self.canvas.set_image(self.pil_image)

    def save_current_image(self):
        item = self.handler.get_current_item()
        if not item or not self.pil_image: return
        
        img_path = self.handler.get_image_path(item)
        if messagebox.askyesno("Confirm", "Overwrite original image with current view?"):
            if ImageProcessingService.save_image(self.pil_image, img_path): 
                self.notifier.show("Image Saved ✓")
        self.focus_set()

    def delete_current_item(self):
        item = self.handler.get_current_item()
        if not item: return
        
        if not messagebox.askyesno("Confirm Delete", "Permanently delete this item?"):
            self.focus_set()
            return
            
        try:
            # Cleanup files
            img_path = self.handler.get_image_path(item)
            if img_path and os.path.exists(img_path):
                os.remove(img_path)
            
            image_name = item.get('processed_image_name', '').strip()
            log_path = self.output_dir / "logs" / f"{Path(image_name).stem}.txt"
            if log_path.exists():
                os.remove(log_path)
            
            if self.handler.delete_item(self.handler.current_index):
                self.notifier.show("Deleted", color="#dc3545")
                self.load_current_item()
        except Exception as e:
            messagebox.showerror("Error", f"Deletion failed: {e}")
        self.focus_set()

    def view_log(self):
        item = self.handler.get_current_item()
        if not item: return
        
        image_name = item.get('processed_image_name', '').strip()
        if not image_name:
            messagebox.showinfo("Error", "No image name found for this item.")
            return

        log_path = self.output_dir / "logs" / f"{Path(image_name).stem}.txt"
        
        if log_path.exists():
            try:
                os.startfile(str(log_path))
            except Exception as e:
                messagebox.showerror("Error", f"Could not open log file: {e}")
        else:
            messagebox.showinfo("Log Not Found", f"No log file exists for this item.\nExpected at: {log_path}")
        self.focus_set()

    def open_model_settings(self):
        settings_win = ctk.CTkToplevel(self)
        settings_win.title("Session Model Overrides")
        settings_win.geometry("500x600")
        settings_win.transient(self)
        settings_win.grab_set()

        ctk.CTkLabel(settings_win, text="Active Model Settings", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        from src.ui.dashboard import HELP_TEXT
        from src.ui.components.settings_pane import SettingsPane
        
        # Prepare session-specific settings dictionary
        current_session_settings = {
            "step1_model": self.model_overrides.get("step1_model", LLM_SETTINGS.get("step1_model")),
            "text_to_JSON_model": self.model_overrides.get("text_to_JSON_model", LLM_SETTINGS.get("text_to_JSON_model")),
            "think": self.model_overrides.get("think", False),
            "available_models": LLM_SETTINGS.get("available_models", [])
        }
        
        pane = SettingsPane(settings_win, "Overrides", current_session_settings, HELP_TEXT)
        pane.pack(expand=True, fill="both", padx=10, pady=10)

        def apply_overrides():
            new_vals = pane.get_values()
            self.model_overrides.update(new_vals)
            settings_win.destroy()
            self.notifier.show("Session Overrides Applied ✓")

        ctk.CTkButton(settings_win, text="Apply for this Session", command=apply_overrides).pack(pady=10)

    def next_item(self):
        if self.handler.next_item(): self.load_current_item()
    def prev_item(self):
        if self.handler.prev_item(): self.load_current_item()

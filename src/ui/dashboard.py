import customtkinter as ctk
import logging
from tkinter import messagebox

from src.utils.config import OCR_SETTINGS, LLM_SETTINGS, KEY_MAP, save_config, FACTORY_DEFAULTS
from src.ui.batch_window import BatchWindow
from src.ui.image_viewer import ImageViewerWindow
from src.ui.components.settings_pane import SettingsPane
from src.ui.ui_utils import browse_directory

logger = logging.getLogger(__name__)

HELP_TEXT = {
    "lang": "Language code for OCR (e.g., 'en', 'ch').",
    "use_angle_cls": "Enable text angle classification for rotated text.",
    "show_log": "Display PaddleOCR internal logs in console.",
    "ocr_version": "Version of the OCR model (e.g., PP-OCRv4).",
    "use_gpu": "Use NVIDIA GPU (requires CUDA) for acceleration.",
    "det_db_thresh": "Threshold for text detection binarization.",
    "det_db_box_thresh": "Threshold for filtering detected text boxes.",
    "det_db_unclip_ratio": "Expands detection boxes to prevent clipping.",
    "det_limit_side_len": "Maximum side length for detection scaling.",
    "drop_score": "Filter out text with confidence lower than this.",
    "enable_mkldnn": "Use Intel MKLDNN for faster CPU processing.",
    "cpu_threads": "Number of CPU threads to use.",
    "rec_image_shape": "Input shape for the recognition model.",
    "crop_padding": "Padding added around text during auto-crop.",
    "auto_crop": "Automatically crop image to text areas.",
    "dump_text_flow": "Save raw/cleaned text to logs for auditing.",
    "standard_prompt": "Main cleaning prompt. Use 'USE_DEFAULT' for built-in.",
    "text_to_json_prompt": "JSON conversion prompt. Use 'USE_DEFAULT' for built-in.",
    "step1_model": "Ollama model for cleaning.",
    "text_to_JSON_model": "Ollama model for JSON extraction.",
    "models_path": "Local path for LLM models.",
    "max_loaded_models": "Max models in memory.",
    "keep_alive": "How long models stay loaded."
}

class Dashboard(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("RC-PaddleOCR - Dashboard")
        self.geometry("1100x850")
        
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self._setup_layout()
        self._setup_sidebar()
        self._setup_main_content()
        self._setup_status_bar()
        
        self.after(500, self.check_dependencies)

    def _setup_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

    def _setup_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        ctk.CTkLabel(self.sidebar, text="RC-PaddleOCR", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=20)

        ctk.CTkButton(self.sidebar, text="Batch Processing", command=self.open_batch_window).pack(padx=20, pady=10)
        ctk.CTkButton(self.sidebar, text="Image Viewer", command=self.open_viewer_window).pack(padx=20, pady=10)

        # Bottom UI controls
        ctk.CTkLabel(self.sidebar, text="Appearance:").pack(side="bottom", padx=20, pady=(0, 5))
        self.appearance_menu = ctk.CTkOptionMenu(self.sidebar, values=["Light", "Dark", "System"], command=ctk.set_appearance_mode)
        self.appearance_menu.pack(side="bottom", padx=20, pady=(0, 20))
        self.appearance_menu.set("Dark")

    def _setup_main_content(self):
        self.main_container = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(self.main_container, text="Configuration Settings", font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, sticky="w", pady=(0, 20))

        # Path Overrides
        self.path_frame = ctk.CTkFrame(self.main_container)
        self.path_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        self.path_frame.grid_columnconfigure(1, weight=1)

        self._create_path_row("Input:", "default_input_dir", 0)
        self._create_path_row("Output:", "default_output_dir", 1)

        # Settings Tabs/Panes
        self.tabview = ctk.CTkTabview(self.main_container)
        self.tabview.grid(row=2, column=0, sticky="nsew")
        
        self.tab_ocr = self.tabview.add("OCR Engine")
        self.tab_llm = self.tabview.add("LLM Service")
        
        self.ocr_pane = SettingsPane(self.tab_ocr, "OCR Parameters", OCR_SETTINGS, HELP_TEXT, fg_color="transparent")
        self.ocr_pane.pack(fill="both", expand=True)
        
        self.llm_pane = SettingsPane(self.tab_llm, "LLM Parameters", LLM_SETTINGS, HELP_TEXT, fg_color="transparent")
        self.llm_pane.pack(fill="both", expand=True)

        # Footer Buttons
        btn_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        btn_frame.grid(row=3, column=0, pady=20)
        
        ctk.CTkButton(btn_frame, text="Save Settings", command=self.save_all).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Revert Defaults", fg_color="transparent", border_width=2, command=self.revert).pack(side="left", padx=10)

    def _setup_status_bar(self):
        self.status_bar = ctk.CTkFrame(self, height=30, corner_radius=0)
        self.status_bar.grid(row=1, column=0, columnspan=2, sticky="ew")
        
        self.ocr_status_label = ctk.CTkLabel(self.status_bar, text="OCR: Checking...", font=ctk.CTkFont(size=11))
        self.ocr_status_label.pack(side="left", padx=20)
        
        self.llm_status_label = ctk.CTkLabel(self.status_bar, text="LLM: Checking...", font=ctk.CTkFont(size=11))
        self.llm_status_label.pack(side="left", padx=20)

    def check_dependencies(self):
        from src.core.ocr_engine import OcrEngine
        from src.core.llm_engine import LlmInferenceEngine, ModelManager
        
        # Check OCR
        try:
            ocr = OcrEngine(show_log=False)
            if ocr.is_ready():
                self.ocr_status_label.configure(text="OCR: Ready ✅", text_color="green")
            else:
                self.ocr_status_label.configure(text="OCR: Library Missing ❌", text_color="red")
        except Exception:
            self.ocr_status_label.configure(text="OCR: Failed ❌", text_color="red")

        # Check LLM Service
        llm_ready = False
        try:
            llm = LlmInferenceEngine()
            if llm.is_ready():
                self.llm_status_label.configure(text="LLM: Service Ready ✅", text_color="green")
                llm_ready = True
            else:
                self.llm_status_label.configure(text="LLM: Service Down/Missing ❌", text_color="red")
        except Exception:
            self.llm_status_label.configure(text="LLM: Service Failed ❌", text_color="red")

        # Check Specific Models if service is ready
        if llm_ready:
            self._check_llm_models()

    def _check_llm_models(self):
        from src.core.llm_engine import ModelManager
        mm = ModelManager()
        
        m1 = LLM_SETTINGS.get("step1_model")
        m2 = LLM_SETTINGS.get("text_to_JSON_model")
        
        missing = []
        if not mm.ensure_model_loaded(m1): missing.append(m1)
        if not mm.ensure_model_loaded(m2): missing.append(m2)
        
        if missing:
            self.llm_status_label.configure(
                text=f"LLM: Models Missing ({', '.join(missing)}) ⚠️", 
                text_color="orange"
            )
            if messagebox.askyesno("Models Missing", f"The following LLM models are not found locally:\n{', '.join(missing)}\n\nWould you like to download them now?"):
                self._download_models(missing)
        else:
            self.llm_status_label.configure(text="LLM: Ready (Service + Models) ✅", text_color="green")

    def _download_models(self, models):
        from src.core.llm_engine import ModelManager
        from src.utils.threading import run_in_background
        
        mm = ModelManager()
        self.llm_status_label.configure(text="LLM: Downloading Models... ⏳", text_color="blue")
        
        def do_download():
            success = True
            for m in models:
                if not mm.pull_model(m):
                    success = False
            
            def finish():
                if success:
                    messagebox.showinfo("Success", "Models downloaded successfully.")
                    self._check_llm_models()
                else:
                    messagebox.showerror("Error", "Failed to download some models. Check internet connection.")
                    self.check_dependencies()
            self.after(0, finish)
            
        run_in_background(do_download)

    def _create_path_row(self, label, config_key, row):
        ctk.CTkLabel(self.path_frame, text=label, font=ctk.CTkFont(weight="bold")).grid(row=row, column=0, padx=10, pady=10, sticky="w")
        entry = ctk.CTkEntry(self.path_frame)
        entry.insert(0, OCR_SETTINGS.get(config_key, ""))
        entry.grid(row=row, column=1, padx=10, pady=10, sticky="ew")
        ctk.CTkButton(self.path_frame, text="Browse", width=80, command=lambda e=entry: self._browse(e)).grid(row=row, column=2, padx=10, pady=10)
        setattr(self, f"{config_key}_entry", entry)

    def _browse(self, entry):
        path = browse_directory()
        if path:
            entry.delete(0, "end")
            entry.insert(0, path)

    def save_all(self):
        ocr_vals = self.ocr_pane.get_values()
        ocr_vals["default_input_dir"] = self.default_input_dir_entry.get()
        ocr_vals["default_output_dir"] = self.default_output_dir_entry.get()
        
        llm_vals = self.llm_pane.get_values()
        
        save_config(ocr_vals, llm_vals)
        messagebox.showinfo("Success", "Configuration saved successfully.")

    def revert(self):
        if messagebox.askyesno("Confirm", "Revert to factory defaults?"):
            self.ocr_pane.set_values(FACTORY_DEFAULTS["OCR_SETTINGS"])
            self.llm_pane.set_values(FACTORY_DEFAULTS["LLM_SETTINGS"])
            
            self.default_input_dir_entry.delete(0, "end")
            self.default_input_dir_entry.insert(0, FACTORY_DEFAULTS["OCR_SETTINGS"]["default_input_dir"])
            self.default_output_dir_entry.delete(0, "end")
            self.default_output_dir_entry.insert(0, FACTORY_DEFAULTS["OCR_SETTINGS"]["default_output_dir"])

    def open_batch_window(self):
        if hasattr(self, "bw") and self.bw.winfo_exists():
            self.bw.focus()
        else:
            self.bw = BatchWindow(self)

    def open_viewer_window(self):
        if hasattr(self, "vw") and self.vw.winfo_exists():
            self.vw.focus()
        else:
            self.vw = ImageViewerWindow(self)

if __name__ == "__main__":
    from src.utils.logging_utils import setup_logging
    setup_logging()
    app = Dashboard()
    app.mainloop()

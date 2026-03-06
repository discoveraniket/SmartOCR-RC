import customtkinter as ctk
from tkinter import messagebox
from src.utils.config import OCR_SETTINGS, LLM_SETTINGS, save_config, FACTORY_DEFAULTS
from src.ui.components.settings_pane import SettingsPane
from src.ui.ui_utils import browse_directory

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

class SettingsView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self._setup_ui()

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=40, pady=(30, 20))
        
        ctk.CTkLabel(header_frame, text="Configuration Settings", font=ctk.CTkFont(size=28, weight="bold")).pack(side="left")

        # Main Content area (scrollable if needed, but here we use tabs)
        self.content_container = ctk.CTkFrame(self, fg_color="transparent")
        self.content_container.grid(row=1, column=0, sticky="nsew", padx=40, pady=0)
        self.content_container.grid_columnconfigure(0, weight=1)
        self.content_container.grid_rowconfigure(1, weight=1)

        # Path Overrides
        self.path_frame = ctk.CTkFrame(self.content_container)
        self.path_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        self.path_frame.grid_columnconfigure(1, weight=1)

        self._create_path_row("Input Directory:", "default_input_dir", 0)
        self._create_path_row("Output Directory:", "default_output_dir", 1)

        # Settings Tabs
        self.tabview = ctk.CTkTabview(self.content_container)
        self.tabview.grid(row=1, column=0, sticky="nsew")
        
        self.tab_ocr = self.tabview.add("OCR Engine")
        self.tab_llm = self.tabview.add("LLM Service")
        
        self.ocr_pane = SettingsPane(self.tab_ocr, "OCR Parameters", OCR_SETTINGS, HELP_TEXT, fg_color="transparent")
        self.ocr_pane.pack(fill="both", expand=True)
        
        self.llm_pane = SettingsPane(self.tab_llm, "LLM Parameters", LLM_SETTINGS, HELP_TEXT, fg_color="transparent")
        self.llm_pane.pack(fill="both", expand=True)

        # Footer Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=2, column=0, sticky="ew", padx=40, pady=30)
        
        ctk.CTkButton(btn_frame, text="Save Settings", width=160, height=40, command=self.save_all).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Revert Defaults", width=160, height=40, fg_color="transparent", border_width=2, command=self.revert).pack(side="left", padx=10)

    def _create_path_row(self, label, config_key, row):
        ctk.CTkLabel(self.path_frame, text=label, font=ctk.CTkFont(weight="bold")).grid(row=row, column=0, padx=20, pady=10, sticky="w")
        entry = ctk.CTkEntry(self.path_frame, height=35)
        entry.insert(0, OCR_SETTINGS.get(config_key, ""))
        entry.grid(row=row, column=1, padx=10, pady=10, sticky="ew")
        ctk.CTkButton(self.path_frame, text="Browse", width=100, height=35, command=lambda e=entry: self._browse(e)).grid(row=row, column=2, padx=20, pady=10)
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

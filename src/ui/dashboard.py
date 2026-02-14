import customtkinter as ctk
import os
import json
import logging
from tkinter import filedialog
from src.utils.threading import run_in_background
from src.ui.batch_window import BatchWindow
from src.ui.image_viewer import ImageViewerWindow

logger = logging.getLogger(__name__)

class Dashboard(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("RC-PaddleOCR - Dashboard")
        self.geometry("950x750")
        
        # Set appearance mode
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar frame
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="RC-PaddleOCR", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.batch_btn = ctk.CTkButton(self.sidebar_frame, text="Batch Processing", command=self.open_batch_window)
        self.batch_btn.grid(row=1, column=0, padx=20, pady=10)

        self.viewer_btn = ctk.CTkButton(self.sidebar_frame, text="Image Viewer", command=self.open_viewer_window)
        self.viewer_btn.grid(row=2, column=0, padx=20, pady=10)

        self.appearance_mode_label = ctk.CTkLabel(self.sidebar_frame, text="Appearance Mode:", anchor="w")
        self.appearance_mode_label.grid(row=5, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = ctk.CTkOptionMenu(self.sidebar_frame, values=["Light", "Dark", "System"],
                                                                       command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=6, column=0, padx=20, pady=(10, 10))
        self.appearance_mode_optionemenu.set("Dark")

        # Main content frame
        self.main_frame = ctk.CTkScrollableFrame(self, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)

        self.setup_settings_ui()

    def setup_settings_ui(self):
        # Settings Label
        self.settings_label = ctk.CTkLabel(self.main_frame, text="Configuration Settings", font=ctk.CTkFont(size=24, weight="bold"))
        self.settings_label.grid(row=0, column=0, padx=20, pady=(20, 20), sticky="w")

        # Paths Section
        self.paths_frame = ctk.CTkFrame(self.main_frame)
        self.paths_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.paths_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.paths_frame, text="Default Input Directory:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.input_dir_entry = ctk.CTkEntry(self.paths_frame)
        self.input_dir_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.input_dir_btn = ctk.CTkButton(self.paths_frame, text="Browse", width=80, command=lambda: self.browse_directory(self.input_dir_entry))
        self.input_dir_btn.grid(row=0, column=2, padx=10, pady=10)

        ctk.CTkLabel(self.paths_frame, text="Default Output Directory:", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.output_dir_entry = ctk.CTkEntry(self.paths_frame)
        self.output_dir_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        self.output_dir_btn = ctk.CTkButton(self.paths_frame, text="Browse", width=80, command=lambda: self.browse_directory(self.output_dir_entry))
        self.output_dir_btn.grid(row=1, column=2, padx=10, pady=10)

        # OCR Settings Section
        self.ocr_frame = ctk.CTkFrame(self.main_frame)
        self.ocr_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.ocr_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self.ocr_frame, text="OCR Settings", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="w")
        
        # LLM Settings Section
        self.llm_frame = ctk.CTkFrame(self.main_frame)
        self.llm_frame.grid(row=3, column=0, padx=20, pady=10, sticky="nsew")
        self.llm_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self.llm_frame, text="LLM Settings", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="w")
        
        self.ocr_entries = {}
        self.llm_entries = {}

        # Buttons Frame
        self.button_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.button_frame.grid(row=4, column=0, padx=20, pady=20)

        # Save Button
        self.save_btn = ctk.CTkButton(self.button_frame, text="Save Settings", command=self.save_settings)
        self.save_btn.pack(side="left", padx=10)

        # Revert Button
        self.revert_btn = ctk.CTkButton(self.button_frame, text="Revert to Default", fg_color="transparent", border_width=2, text_color=("gray10", "#DCE4EE"), command=self.revert_to_default)
        self.revert_btn.pack(side="left", padx=10)

        self.load_initial_settings()

    def revert_to_default(self):
        from src.utils.config import FACTORY_DEFAULTS, save_config
        from tkinter import messagebox
        
        if messagebox.askyesno("Confirm", "Are you sure you want to revert all settings to factory defaults?"):
            # Update the config file
            save_config(FACTORY_DEFAULTS["OCR_SETTINGS"], FACTORY_DEFAULTS["LLM_SETTINGS"])
            
            # Clear current UI entries
            self.input_dir_entry.delete(0, "end")
            self.output_dir_entry.delete(0, "end")
            
            # Since load_initial_settings adds widgets, we need to clear frames first or just re-run with value updates
            # A cleaner way is to just reload the values into existing widgets
            
            ocr_defaults = FACTORY_DEFAULTS["OCR_SETTINGS"]
            llm_defaults = FACTORY_DEFAULTS["LLM_SETTINGS"]
            
            self.input_dir_entry.insert(0, ocr_defaults.get("default_input_dir", "data"))
            self.output_dir_entry.insert(0, ocr_defaults.get("default_output_dir", "output"))
            
            for key, (entry, _) in self.ocr_entries.items():
                if key in ocr_defaults:
                    entry.delete(0, "end")
                    entry.insert(0, str(ocr_defaults[key]))
                    
            for key, (entry, _) in self.llm_entries.items():
                if key in llm_defaults:
                    entry.delete(0, "end")
                    entry.insert(0, str(llm_defaults[key]))
            
            messagebox.showinfo("Success", "Settings reverted to defaults.")

    def browse_directory(self, entry_widget):
        directory = filedialog.askdirectory()
        if directory:
            entry_widget.delete(0, "end")
            entry_widget.insert(0, directory)

    def load_initial_settings(self):
        try:
            from src.utils.config import OCR_SETTINGS, LLM_SETTINGS
            
            # Paths
            self.input_dir_entry.insert(0, OCR_SETTINGS.get("default_input_dir", "data"))
            self.output_dir_entry.insert(0, OCR_SETTINGS.get("default_output_dir", "output"))

            row = 1
            for key, value in OCR_SETTINGS.items():
                if key in ["default_input_dir", "default_output_dir"]:
                    continue
                
                ctk.CTkLabel(self.ocr_frame, text=f"{key}:").grid(row=row, column=0, padx=10, pady=5, sticky="w")
                
                entry = ctk.CTkEntry(self.ocr_frame)
                entry.insert(0, str(value))
                entry.grid(row=row, column=1, padx=10, pady=5, sticky="ew")
                
                # Help Icon to the right
                help_btn = ctk.CTkButton(self.ocr_frame, text="?", width=25, height=25, corner_radius=12, 
                                        fg_color="#3B3B3B", hover_color="#555555",
                                        command=lambda k=key: self.show_help(k))
                help_btn.grid(row=row, column=2, padx=5, pady=5)

                self.ocr_entries[key] = (entry, type(value))
                row += 1
            
            row = 1
            for key, value in LLM_SETTINGS.items():
                ctk.CTkLabel(self.llm_frame, text=f"{key}:").grid(row=row, column=0, padx=10, pady=5, sticky="w")
                
                entry = ctk.CTkEntry(self.llm_frame)
                entry.insert(0, str(value))
                entry.grid(row=row, column=1, padx=10, pady=5, sticky="ew")

                # Help Icon to the right
                help_btn = ctk.CTkButton(self.llm_frame, text="?", width=25, height=25, corner_radius=12, 
                                        fg_color="#3B3B3B", hover_color="#555555",
                                        command=lambda k=key: self.show_help(k))
                help_btn.grid(row=row, column=2, padx=5, pady=5)

                self.llm_entries[key] = (entry, type(value))
                row += 1

        except Exception as e:
            logger.error(f"Error loading settings: {e}")

    def show_help(self, key):
        help_text = {
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
            "crop_padding": "Padding (in pixels) added around the text area during auto-crop.",
            "auto_crop": "Automatically crop the image to text areas for better accuracy.",
            "dump_text_flow": "Save raw and cleaned text to a .txt file in output/logs for auditing.",
            "step1_model": "Ollama model used for initial text cleaning/reasoning.",
            "text_to_JSON_model": "Ollama model used for final data extraction.",
            "models_path": "Local path where LLM models are stored.",
            "max_loaded_models": "Maximum number of models kept in memory.",
            "keep_alive": "How long models stay loaded in Ollama after use."
        }
        from tkinter import messagebox
        messagebox.showinfo("Setting Info", help_text.get(key, "No description available."))

    def save_settings(self):
        from src.utils.config import save_config
        
        def parse_value(val_str, target_type):
            if target_type == bool:
                return val_str.lower() in ("true", "1", "yes")
            try:
                return target_type(val_str)
            except:
                return val_str

        updated_ocr = {k: parse_value(v[0].get(), v[1]) for k, v in self.ocr_entries.items()}
        updated_ocr["default_input_dir"] = self.input_dir_entry.get()
        updated_ocr["default_output_dir"] = self.output_dir_entry.get()
        
        updated_llm = {k: parse_value(v[0].get(), v[1]) for k, v in self.llm_entries.items()}
        
        save_config(updated_ocr, updated_llm)
        from tkinter import messagebox
        messagebox.showinfo("Success", "Settings saved successfully! Restart application for some changes to take effect.")

    def open_batch_window(self):
        if hasattr(self, "batch_window") and self.batch_window.winfo_exists():
            self.batch_window.focus()
            return
        self.batch_window = BatchWindow(self)

    def open_viewer_window(self):
        if hasattr(self, "viewer_window") and self.viewer_window.winfo_exists():
            self.viewer_window.focus()
            return
        self.viewer_window = ImageViewerWindow(self)

    def change_appearance_mode_event(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)

if __name__ == "__main__":
    app = Dashboard()
    app.mainloop()

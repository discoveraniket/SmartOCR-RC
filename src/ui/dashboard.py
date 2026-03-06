import customtkinter as ctk
import logging
from tkinter import messagebox

from src.utils.config import OCR_SETTINGS, LLM_SETTINGS, KEY_MAP, save_config, FACTORY_DEFAULTS
from src.ui.batch_window import BatchWindow
from src.ui.image_viewer import ImageViewerWindow
from src.ui.rc_processor_window import RCProcessorWindow
from src.ui.views.search_view import SearchView
from src.ui.views.settings_view import SettingsView

logger = logging.getLogger(__name__)

class Dashboard(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("SmartOCR-RC")
        self.geometry("1200x850")
        
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # Sidebar state
        self.sidebar_is_expanded = True
        self.sidebar_width_expanded = 220
        self.sidebar_width_collapsed = 60

        self._setup_layout()
        self._setup_sidebar()
        self._setup_main_content()
        self._setup_status_bar()
        
        # Select default frame
        self.select_frame_by_name("search")
        
        self.after(500, self.check_dependencies)

    def _setup_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

    def _setup_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=self.sidebar_width_expanded, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(7, weight=1) # Spacer
        self.sidebar.grid_propagate(False) # Keep width fixed

        # Toggle Button (Hamburger)
        self.btn_toggle = ctk.CTkButton(self.sidebar, text="≡", width=40, height=40, 
                                       corner_radius=8, fg_color="transparent", 
                                       hover_color=("gray70", "gray30"),
                                       font=ctk.CTkFont(size=24), command=self.toggle_sidebar)
        self.btn_toggle.grid(row=0, column=0, padx=(10, 10), pady=20, sticky="w")

        self.logo_label = ctk.CTkLabel(self.sidebar, text="SmartOCR-RC", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=(60, 20), pady=20, sticky="w")

        # Navigation Buttons
        self.nav_buttons = {}
        
        nav_items = [
            ("search", "🔍  Search Ration Card", self.btn_search_event),
            ("db_tools", "📊  RC Database Tools", self.btn_db_tools_event),
            ("batch", "📦  Batch Processing", self.btn_batch_event),
            ("viewer", "🖼️  Image Viewer", self.btn_viewer_event),
            ("settings", "⚙️  Settings", self.btn_settings_event)
        ]

        for i, (name, text, cmd) in enumerate(nav_items, start=1):
            btn = ctk.CTkButton(self.sidebar, text=text, 
                               corner_radius=0, height=50, border_spacing=10,
                               fg_color="transparent", text_color=("gray10", "gray90"), 
                               hover_color=("gray70", "gray30"),
                               anchor="w", command=cmd)
            btn.grid(row=i, column=0, sticky="ew")
            self.nav_buttons[name] = (btn, text)

        # Bottom UI controls
        self.appearance_menu = ctk.CTkOptionMenu(self.sidebar, values=["Light", "Dark", "System"], command=ctk.set_appearance_mode)
        self.appearance_menu.grid(row=8, column=0, padx=10, pady=20, sticky="s")
        self.appearance_menu.set("Dark")

    def toggle_sidebar(self):
        if self.sidebar_is_expanded:
            # Collapse
            self.sidebar.configure(width=self.sidebar_width_collapsed)
            self.logo_label.grid_remove()
            for name, (btn, full_text) in self.nav_buttons.items():
                icon = full_text.split("  ")[0] # Extract icon part
                btn.configure(text=icon, anchor="center")
            self.appearance_menu.grid_remove()
            self.sidebar_is_expanded = False
        else:
            # Expand
            self.sidebar.configure(width=self.sidebar_width_expanded)
            self.logo_label.grid(row=0, column=0, padx=(60, 20), pady=20, sticky="w")
            for name, (btn, full_text) in self.nav_buttons.items():
                btn.configure(text=full_text, anchor="w")
            self.appearance_menu.grid(row=8, column=0, padx=10, pady=20, sticky="s")
            self.sidebar_is_expanded = True

    def _setup_main_content(self):
        self.main_container = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew")
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)

        # Initialize frames
        self.search_frame = SearchView(self.main_container, fg_color="transparent")
        self.settings_frame = SettingsView(self.main_container, fg_color="transparent")

    def _setup_status_bar(self):
        self.status_bar = ctk.CTkFrame(self, height=30, corner_radius=0)
        self.status_bar.grid(row=1, column=0, columnspan=2, sticky="ew")
        
        self.ocr_status_label = ctk.CTkLabel(self.status_bar, text="OCR: Checking...", font=ctk.CTkFont(size=11))
        self.ocr_status_label.pack(side="left", padx=20)
        
        self.llm_status_label = ctk.CTkLabel(self.status_bar, text="LLM: Checking...", font=ctk.CTkFont(size=11))
        self.llm_status_label.pack(side="left", padx=20)

    def select_frame_by_name(self, name):
        # Update button colors
        for btn_name, (btn, _) in self.nav_buttons.items():
            btn.configure(fg_color=("gray75", "gray25") if btn_name == name else "transparent")

        # Show/Hide frames
        if name == "search":
            self.search_frame.grid(row=0, column=0, sticky="nsew")
        else:
            self.search_frame.grid_forget()
            
        if name == "settings":
            self.settings_frame.grid(row=0, column=0, sticky="nsew")
        else:
            self.settings_frame.grid_forget()

    def btn_search_event(self):
        self.select_frame_by_name("search")

    def btn_db_tools_event(self):
        self.open_rc_processor_window() # Temporary for Phase 1

    def btn_batch_event(self):
        self.open_batch_window() # Temporary for Phase 1

    def btn_viewer_event(self):
        self.open_viewer_window() # Temporary for Phase 1

    def btn_settings_event(self):
        self.select_frame_by_name("settings")

    def check_dependencies(self):
        from src.utils.threading import run_in_background
        
        self.ocr_status_label.configure(text="OCR: Checking...", text_color="white")
        self.llm_status_label.configure(text="LLM: Checking...", text_color="white")
        
        def do_check():
            from src.core.ocr_engine import OcrEngine
            from src.core.llm_engine import LlmInferenceEngine
            
            # Check OCR
            ocr_status = ("OCR: Failed ❌", "red")
            try:
                ocr = OcrEngine(show_log=False)
                if ocr.is_ready():
                    ocr_status = ("OCR: Ready ✅", "green")
                else:
                    ocr_status = ("OCR: Library Missing ❌", "red")
            except Exception:
                pass
            
            self.after(0, lambda: self.ocr_status_label.configure(text=ocr_status[0], text_color=ocr_status[1]))

            # Check LLM Service
            llm_status = ("LLM: Service Failed ❌", "red")
            llm_ready = False
            try:
                llm = LlmInferenceEngine()
                if llm.is_ready():
                    llm_status = ("LLM: Service Ready ✅", "green")
                    llm_ready = True
                else:
                    llm_status = ("LLM: Service Down/Missing ❌", "red")
            except Exception:
                pass

            self.after(0, lambda: self.llm_status_label.configure(text=llm_status[0], text_color=llm_status[1]))

            if llm_ready:
                self.after(0, self._check_llm_models)

        run_in_background(do_check)

    def _check_llm_models(self):
        from src.core.llm_engine import ModelManager
        from src.utils.threading import run_in_background
        
        def do_model_check():
            mm = ModelManager()
            m1 = LLM_SETTINGS.get("step1_model")
            m2 = LLM_SETTINGS.get("text_to_JSON_model")
            
            missing = []
            if not mm.ensure_model_loaded(m1): missing.append(m1)
            if not mm.ensure_model_loaded(m2): missing.append(m2)
            
            def update_ui():
                if missing:
                    self.llm_status_label.configure(
                        text=f"LLM: Models Missing ({', '.join(missing)}) ⚠️", 
                        text_color="orange"
                    )
                    if messagebox.askyesno("Models Missing", f"The following LLM models are not found locally:\n{', '.join(missing)}\n\nWould you like to download them now?"):
                        self._download_models(missing)
                else:
                    self.llm_status_label.configure(text="LLM: Ready (Service + Models) ✅", text_color="green")
            
            self.after(0, update_ui)

        run_in_background(do_model_check)

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

    def open_rc_processor_window(self):
        if hasattr(self, "rcw") and self.rcw.winfo_exists():
            self.rcw.focus()
        else:
            self.rcw = RCProcessorWindow(self)

if __name__ == "__main__":
    from src.utils.logging_utils import setup_logging
    setup_logging()
    app = Dashboard()
    app.mainloop()

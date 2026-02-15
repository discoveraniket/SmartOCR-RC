import customtkinter as ctk
from typing import Dict, Any, Tuple, Type
from src.utils.config import FACTORY_DEFAULTS

class SettingsPane(ctk.CTkScrollableFrame):
    """
    A reusable component for managing application settings.
    Dynamically generates UI based on configuration dictionaries.
    """
    def __init__(self, master, title: str, settings_dict: Dict[str, Any], help_text: Dict[str, str] = None, **kwargs):
        super().__init__(master, **kwargs)
        
        self.settings_dict = settings_dict
        self.help_text = help_text or {}
        self.entries: Dict[str, Tuple[ctk.CTkBaseClass, Type]] = {}
        
        self._setup_ui(title)

    def _setup_ui(self, title: str):
        self.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(self, text=title, font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, columnspan=3, padx=10, pady=10, sticky="w")
        
        row = 1
        # Filter out complex types or handle specifically
        available_models = self.settings_dict.get("available_models", [])
        
        for key, value in self.settings_dict.items():
            if key == "available_models" or key.startswith("default_"):
                continue
                
            ctk.CTkLabel(self, text=f"{key}:").grid(row=row, column=0, padx=10, pady=5, sticky="nw")
            
            entry = self._create_field(key, value, available_models)
            entry.grid(row=row, column=1, padx=10, pady=5, sticky="ew")
            
            # Help Icon
            if key in self.help_text:
                help_btn = ctk.CTkButton(
                    self, text="?", width=25, height=25, corner_radius=12, 
                    fg_color="#3B3B3B", hover_color="#555555",
                    command=lambda k=key: self._show_help(k)
                )
                help_btn.grid(row=row, column=2, padx=5, pady=5, sticky="n")

            self.entries[key] = (entry, type(value))
            row += 1

    def _create_field(self, key: str, value: Any, available_models: list) -> ctk.CTkBaseClass:
        if key.endswith("_model") and available_models:
            entry = ctk.CTkOptionMenu(self, values=available_models)
            entry.set(str(value))
            return entry
        elif key.endswith("_prompt"):
            entry = ctk.CTkTextbox(self, height=100)
            entry.insert("1.0", str(value))
            return entry
        else:
            entry = ctk.CTkEntry(self)
            entry.insert(0, str(value))
            return entry

    def _show_help(self, key: str):
        from tkinter import messagebox
        messagebox.showinfo("Setting Info", self.help_text.get(key, "No description available."))

    def get_values(self) -> Dict[str, Any]:
        """Returns the current values from the UI fields."""
        results = {}
        for key, (entry, target_type) in self.entries.items():
            if isinstance(entry, ctk.CTkTextbox):
                val_str = entry.get("1.0", "end-1c")
            else:
                val_str = entry.get()
                
            if target_type == bool:
                results[key] = val_str.lower() in ("true", "1", "yes")
            else:
                try:
                    results[key] = target_type(val_str)
                except:
                    results[key] = val_str
        return results

    def set_values(self, values: Dict[str, Any]):
        """Updates the UI fields with new values."""
        for key, value in values.items():
            if key in self.entries:
                entry, _ = self.entries[key]
                if isinstance(entry, ctk.CTkTextbox):
                    entry.delete("1.0", "end")
                    entry.insert("1.0", str(value))
                else:
                    if hasattr(entry, "set"): # OptionMenu
                        entry.set(str(value))
                    else: # Entry
                        entry.delete(0, "end")
                        entry.insert(0, str(value))

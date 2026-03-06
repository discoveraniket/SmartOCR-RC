import customtkinter as ctk
from tkinter import filedialog
from typing import Optional, Callable

def browse_directory(initial_dir: Optional[str] = None) -> Optional[str]:
    """Standardized directory picker."""
    return filedialog.askdirectory(initialdir=initial_dir)

def browse_file(filetypes: list, initial_dir: Optional[str] = None) -> Optional[str]:
    """Standardized file picker."""
    return filedialog.askopenfilename(filetypes=filetypes, initial_dir=initial_dir)

class ToastNotifier:
    """Provides temporary status messages in the UI."""
    def __init__(self, label_widget: ctk.CTkLabel):
        self.label = label_widget

    def show(self, message: str, color: str = "#28a745", duration_ms: int = 2000):
        self.label.configure(text=message, text_color=color)
        self.label.after(duration_ms, lambda: self.label.configure(text=""))

def format_shortcut(key_map_val: str) -> str:
    """Formats a tkinter shortcut string (e.g. <Control-S>) for button display ([S])."""
    return f"[{key_map_val.replace('<Control-', '').replace('>', '').replace('Shift-', '').upper()}]"

import customtkinter as ctk
import os
import time
from tkinter import filedialog, messagebox
import logging
from src.core.batch_processor import BatchProcessor

logger = logging.getLogger(__name__)

class TextboxHandler(logging.Handler):
    def __init__(self, textbox):
        super().__init__()
        self.textbox = textbox

    def emit(self, record):
        msg = self.format(record)
        def append():
            try:
                self.textbox.configure(state="normal")
                self.textbox.insert("end", msg + "\n")
                self.textbox.see("end")
                self.textbox.configure(state="disabled")
            except:
                pass
        self.textbox.after(0, append)

class BatchWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)

        self.title("Overnight Batch Processing")
        self.geometry("1000x850")
        
        # Ensure it stays on top of the parent and gets focus
        self.transient(parent)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1) # Log area takes expansion

        self.processor = None
        self.log_handler = None

        self.setup_config_ui()
        self.setup_progress_ui()
        self.setup_log_ui()
        self.setup_controls_ui()
        
    def setup_config_ui(self):
        self.config_frame = ctk.CTkFrame(self)
        self.config_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="nsew")
        self.config_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.config_frame, text="Session Configuration", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, columnspan=3, padx=10, pady=10, sticky="w")

        # Input Path
        ctk.CTkLabel(self.config_frame, text="Input Path:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.input_entry = ctk.CTkEntry(self.config_frame)
        self.input_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        self.input_btn = ctk.CTkButton(self.config_frame, text="Browse", width=80, command=lambda: self.browse_dir(self.input_entry))
        self.input_btn.grid(row=1, column=2, padx=10, pady=5)

        # Output Path
        ctk.CTkLabel(self.config_frame, text="Output Path:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.output_entry = ctk.CTkEntry(self.config_frame)
        self.output_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        self.output_btn = ctk.CTkButton(self.config_frame, text="Browse", width=80, command=lambda: self.browse_dir(self.output_entry))
        self.output_btn.grid(row=2, column=2, padx=10, pady=5)

        # Options
        options_frame = ctk.CTkFrame(self.config_frame, fg_color="transparent")
        options_frame.grid(row=3, column=0, columnspan=3, padx=5, pady=5, sticky="w")

        self.recursive_var = ctk.BooleanVar(value=True)
        self.recursive_check = ctk.CTkCheckBox(options_frame, text="Recursive Search", variable=self.recursive_var)
        self.recursive_check.pack(side="left", padx=10)

        self.retry_var = ctk.BooleanVar(value=True)
        self.retry_check = ctk.CTkCheckBox(options_frame, text="Auto-retry errors", variable=self.retry_var)
        self.retry_check.pack(side="left", padx=10)

        ctk.CTkLabel(self.config_frame, text="Post-Process Action:").grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.post_action_var = ctk.StringVar(value="None")
        self.post_action_menu = ctk.CTkOptionMenu(self.config_frame, values=["None", "Shutdown", "Sleep"], variable=self.post_action_var)
        self.post_action_menu.grid(row=4, column=1, padx=10, pady=5, sticky="w")

        from src.utils.config import OCR_SETTINGS
        self.input_entry.insert(0, OCR_SETTINGS.get("default_input_dir", "data"))
        self.output_entry.insert(0, OCR_SETTINGS.get("default_output_dir", "output"))

    def setup_progress_ui(self):
        self.progress_frame = ctk.CTkFrame(self)
        self.progress_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.progress_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.progress_frame, text="Live Progress & Metrics", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_bar.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.progress_bar.set(0)

        self.stats_label = ctk.CTkLabel(self.progress_frame, text="Total: 0 | Processed: 0 | Remaining: 0 | Errors: 0", font=ctk.CTkFont(size=14))
        self.stats_label.grid(row=2, column=0, padx=20, pady=5)

        self.eta_label = ctk.CTkLabel(self.progress_frame, text="ETA: --:--:-- | Elapsed: 00:00:00")
        self.eta_label.grid(row=3, column=0, padx=20, pady=5)

        self.speed_label = ctk.CTkLabel(self.progress_frame, text="OCR1 Speed: --s | Model1: --s | text to JSON: --s", font=ctk.CTkFont(weight="bold"))
        self.speed_label.grid(row=4, column=0, padx=20, pady=5)

        self.current_file_label = ctk.CTkLabel(self.progress_frame, text="Current: Waiting...", font=ctk.CTkFont(slant="italic"))
        self.current_file_label.grid(row=5, column=0, padx=20, pady=5)

    def setup_log_ui(self):
        self.log_frame = ctk.CTkFrame(self)
        self.log_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.log_frame.grid_columnconfigure(0, weight=1)
        self.log_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self.log_frame, text="Session Logs", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.log_textbox = ctk.CTkTextbox(self.log_frame, height=200)
        self.log_textbox.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.log_textbox.configure(state="disabled")

        # Attach logging handler
        self.log_handler = TextboxHandler(self.log_textbox)
        self.log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%H:%M:%S'))
        logging.getLogger().addHandler(self.log_handler)

    def setup_controls_ui(self):
        self.controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.controls_frame.grid(row=3, column=0, padx=20, pady=20)

        self.start_btn = ctk.CTkButton(self.controls_frame, text="Start Batch Session", fg_color="green", hover_color="darkgreen", command=self.start_session)
        self.start_btn.pack(side="left", padx=10)

        self.stop_btn = ctk.CTkButton(self.controls_frame, text="Stop Session", fg_color="red", hover_color="darkred", state="disabled", command=self.stop_session)
        self.stop_btn.pack(side="left", padx=10)

    def browse_dir(self, entry):
        directory = filedialog.askdirectory()
        if directory:
            entry.delete(0, "end")
            entry.insert(0, directory)

    def log(self, message):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", f">>> {message}\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def format_time(self, seconds):
        if seconds < 0: return "--:--:--"
        return time.strftime('%H:%M:%S', time.gmtime(seconds))

    def update_ui(self, stats, current_file=None, last_speeds=None):
        self.progress_bar.set(stats["progress"])
        self.stats_label.configure(text=f"Total: {stats['total']} | Processed: {stats['processed']} | Remaining: {stats['remaining']} | Errors: {stats['errors']}")
        
        eta_str = self.format_time(stats["eta"])
        elapsed_str = self.format_time(stats["elapsed"])
        self.eta_label.configure(text=f"ETA: {eta_str} | Elapsed: {elapsed_str}")
        
        if last_speeds:
            ocr = last_speeds.get('ocr', '--')
            m1 = last_speeds.get('step1', '--')
            json_speed = last_speeds.get('json', '--')
            self.speed_label.configure(text=f"OCR1 Speed: {ocr}s | Model1: {m1}s | text to JSON: {json_speed}s")
            
        if current_file:
            self.current_file_label.configure(text=f"Current: {current_file}")

    def start_session(self):
        input_dir = self.input_entry.get()
        output_dir = self.output_entry.get()
        
        if not os.path.exists(input_dir):
            messagebox.showerror("Error", "Input directory does not exist.")
            return

        self.processor = BatchProcessor(
            input_dir, 
            output_dir, 
            recursive=self.recursive_var.get(),
            auto_retry=self.retry_var.get(),
            post_action=self.post_action_var.get()
        )
        
        # Disable inputs and start button
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.input_entry.configure(state="disabled")
        self.output_entry.configure(state="disabled")
        self.input_btn.configure(state="disabled")
        self.output_btn.configure(state="disabled")
        self.recursive_check.configure(state="disabled")
        self.retry_check.configure(state="disabled")
        self.post_action_menu.configure(state="disabled")
        
        self.log("--- Starting Batch Session ---")
        self.processor.start(progress_callback=self.update_ui, completion_callback=self.on_completion)

    def stop_session(self):
        if self.processor:
            self.processor.stop()
            self.log("!!! Stop Requested - Waiting for current item to finish !!!")
            self.stop_btn.configure(state="disabled")

    def on_completion(self, stats):
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        
        # Re-enable inputs
        self.input_entry.configure(state="normal")
        self.output_entry.configure(state="normal")
        self.input_btn.configure(state="normal")
        self.output_btn.configure(state="normal")
        self.recursive_check.configure(state="normal")
        self.retry_check.configure(state="normal")
        self.post_action_menu.configure(state="normal")

        self.log(f"--- Session Finished ---")
        self.log(f"Total Processed: {stats['processed']}")
        self.log(f"Total Errors: {stats['errors']}")
        messagebox.showinfo("Session Complete", "Batch processing has finished.")

    def destroy(self):
        # Clean up logging handler
        if self.log_handler:
            logging.getLogger().removeHandler(self.log_handler)
        super().destroy()

if __name__ == "__main__":
    root = ctk.CTk()
    bw = BatchWindow(root)
    root.mainloop()

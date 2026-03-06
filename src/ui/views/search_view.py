import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import os
import winsound
from src.rc_processor.search_manager import SearchManager

class SearchView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        db_path = os.path.join("data", "rc_db", "final_rc_data.db")
        if not os.path.exists(db_path):
            db_path = os.path.join("data", "rc_db", "rcdb.db")
        
        self.search_manager = SearchManager(db_path)
        self.search_manager.connect()
        
        self._setup_ui(db_path)
        self.current_search_match = {}

    def _setup_ui(self, db_path):
        self.grid_columnconfigure(0, weight=1)
        
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=40, pady=30)
        
        header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(header_frame, text="Search Ration Card", font=ctk.CTkFont(size=28, weight="bold")).pack(side="left")
        
        search_input_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        search_input_frame.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(search_input_frame, text="Enter 10 Digit Ration Card Number:", font=ctk.CTkFont(size=14)).pack(anchor="w")
        
        self.rc_entry_var = ctk.StringVar()
        self.rc_entry_var.trace_add("write", self.on_rc_search_change)
        
        self.rc_entry = ctk.CTkEntry(search_input_frame, textvariable=self.rc_entry_var, font=ctk.CTkFont(size=18), height=45)
        self.rc_entry.pack(fill="x", pady=(5, 5))
        self.rc_entry.focus_set()
        self.rc_entry.bind("<Return>", self.save_search_data)

        self.match_count_var = ctk.StringVar(value="")
        ctk.CTkLabel(search_input_frame, textvariable=self.match_count_var, font=ctk.CTkFont(size=12), text_color="#1f6aa5").pack(anchor="w")
        
        # Details area
        details_frame = ctk.CTkFrame(main_frame)
        details_frame.pack(fill="x", expand=False, pady=(0, 20))
        
        ctk.CTkLabel(details_frame, text="Record Details", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=20, pady=(15, 10))
        
        self.display_fields = {
            "Category": "Category",
            "Ration Card No.": "Ration Card No.",
            "Name": "Name",
            "Father/Husband Name": "Father/Husband Name",
            "HOF Name": "HOF Name(As Per NFSA Provision)",
            "Dealer Name": "Dealer_Name_Mapped"
        }
        
        self.search_labels = {}
        
        for display_name, db_col in self.display_fields.items():
            row_frame = ctk.CTkFrame(details_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=4, padx=20)
            ctk.CTkLabel(row_frame, text=f"{display_name}:", width=220, anchor="w", font=ctk.CTkFont(weight="bold")).pack(side="left")
            val_label = ctk.CTkLabel(row_frame, text="", anchor="w", font=ctk.CTkFont(size=14))
            val_label.pack(side="left", fill="x", expand=True)
            self.search_labels[db_col] = val_label
            
        ctk.CTkFrame(details_frame, height=10, fg_color="transparent").pack()

        # Editable fields
        edit_frame = ctk.CTkFrame(main_frame)
        edit_frame.pack(fill="x", expand=False, pady=(0, 20))
        
        ctk.CTkLabel(edit_frame, text="Additional Info (Editable)", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, columnspan=2, sticky='w', padx=20, pady=(15, 10))

        ctk.CTkLabel(edit_frame, text="Caste:", width=220, anchor="w", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, sticky='w', padx=20, pady=5)
        self.search_caste_var = ctk.StringVar()
        self.entry_caste = ctk.CTkEntry(edit_frame, textvariable=self.search_caste_var, width=350, height=35)
        self.entry_caste.grid(row=1, column=1, sticky='w', pady=5)
        self.entry_caste.bind("<Return>", self.save_search_data)

        ctk.CTkLabel(edit_frame, text="Mobile No:", width=220, anchor="w", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, sticky='w', padx=20, pady=5)
        self.search_mobile_var = ctk.StringVar()
        self.entry_mobile = ctk.CTkEntry(edit_frame, textvariable=self.search_mobile_var, width=350, height=35)
        self.entry_mobile.grid(row=2, column=1, sticky='w', pady=(5, 15))
        self.entry_mobile.bind("<Return>", self.save_search_data)

        # Tab navigation for accessibility
        self.rc_entry.bind("<Tab>", lambda e: self.entry_caste.focus_set())
        self.entry_caste.bind("<Tab>", lambda e: self.entry_mobile.focus_set())
        self.entry_mobile.bind("<Tab>", lambda e: self.rc_entry.focus_set())

        # File output path
        output_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        output_frame.pack(fill="x", pady=(10, 0))
        ctk.CTkLabel(output_frame, text="Save to File:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(0, 10))
        self.search_output_var = ctk.StringVar(value=os.path.join("data", "rc_db", "Benef_list.csv"))
        ctk.CTkEntry(output_frame, textvariable=self.search_output_var, height=35).pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(output_frame, text="Browse...", width=100, height=35, command=self.browse_search_output).pack(side="left")

        ctk.CTkLabel(main_frame, text="Press Enter to save match to file", font=ctk.CTkFont(size=12, slant="italic"), text_color="gray").pack(pady=(10, 0))

        self.flash_label = ctk.CTkLabel(main_frame, text="", font=ctk.CTkFont(size=14, weight="bold"))
        self.flash_label.pack(pady=(5, 0))
        
        # Database connection status
        status_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        status_frame.pack(side="bottom", fill="x", pady=(20, 0))
        
        self.search_db_status_var = ctk.StringVar(value=f"Connected to: {db_path}" if os.path.exists(db_path) else "Database not found! Run pipeline first.")
        ctk.CTkLabel(status_frame, textvariable=self.search_db_status_var, font=ctk.CTkFont(size=11), text_color="#1f6aa5").pack(side="left")
        
        ctk.CTkButton(status_frame, text="Link Database", width=140, height=30, command=self.browse_search_db).pack(side="right")

    def on_rc_search_change(self, *args):
        search_term = self.rc_entry_var.get().strip()
        if not search_term:
            self.clear_search_fields()
            self.match_count_var.set("")
            return
        
        result, count = self.search_manager.search_ration_card(search_term)
        
        if result:
            self.populate_search_fields(result)
            self.match_count_var.set(f"Matches found: {count}")
            if count == 1:
                threading.Thread(target=winsound.Beep, args=(1000, 200), daemon=True).start()
        else:
            self.clear_search_fields()
            self.match_count_var.set("No matches found")
            threading.Thread(target=winsound.Beep, args=(400, 200), daemon=True).start()

    def populate_search_fields(self, row):
        self.current_search_match = row
        for db_col, label_widget in self.search_labels.items():
            val = row.get(db_col, "")
            if db_col == "Name":
                caste_ref = row.get("Deducted_Caste", "")
                if caste_ref:
                    val = f"{val} ({caste_ref})"
            label_widget.configure(text=str(val))
        self.search_caste_var.set(row.get("Deducted_Caste", ""))
        self.search_mobile_var.set(row.get("Mobile No", ""))

    def clear_search_fields(self):
        self.current_search_match = {}
        for label in self.search_labels.values():
            label.configure(text="")
        self.search_caste_var.set("")
        self.search_mobile_var.set("")

    def show_flash_message(self, message, color="green"):
        self.flash_label.configure(text=message, text_color=color)
        if hasattr(self, '_flash_timer') and self._flash_timer:
            self.after_cancel(self._flash_timer)
        self._flash_timer = self.after(3000, lambda: self.flash_label.configure(text=""))

    def save_search_data(self, event=None):
        if not self.current_search_match:
            messagebox.showwarning("No Data", "No matching record found to save.")
            return
        output_file = self.search_output_var.get()
        if not output_file:
             messagebox.showerror("Error", "Please select an output file.")
             return
        save_data = self.current_search_match.copy()
        save_data["Deducted_Caste"] = self.search_caste_var.get()
        save_data["Mobile No"] = self.search_mobile_var.get()
        
        success, msg = self.search_manager.save_record(save_data, target_file=output_file)
        
        if success:
            self.rc_entry.delete(0, tk.END)
            self.clear_search_fields()
            self.match_count_var.set("")
            self.show_flash_message("Record Saved Successfully!", "green")
            threading.Thread(target=winsound.Beep, args=(1500, 150), daemon=True).start()
            self.rc_entry.focus_set()
        else:
            messagebox.showerror("Error", f"Failed to save: {msg}")

    def browse_search_db(self):
        filename = filedialog.askopenfilename(filetypes=[("SQLite DB", "*.db"), ("All Files", "*.*")])
        if filename:
            self.search_manager = SearchManager(filename)
            success, msg = self.search_manager.connect()
            if success:
                self.search_db_status_var.set(f"Connected to: {filename}")
                self.rc_entry.delete(0, tk.END)
                self.clear_search_fields()
            else:
                self.search_db_status_var.set(f"Connection Failed: {msg}")
                messagebox.showerror("Error", f"Could not connect to database: {msg}")

    def browse_search_output(self):
        filename = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv"), ("Excel Files", "*.xlsx")])
        if filename:
            self.search_output_var.set(filename)

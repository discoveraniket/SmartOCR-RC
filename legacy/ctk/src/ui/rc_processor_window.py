import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import os
import sys
import csv
import re
import pandas as pd
import sqlite3
import winsound

# Add src to path if needed
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.rc_processor.downloader import BeneficiaryDownloader
from src.rc_processor.converter import BeneficiaryConverter
from src.rc_processor.caste_deducer import DataEnricher
from src.rc_processor.db_manager import DatabaseManager
from src.rc_processor.pipeline import PipelineManager
from src.rc_processor.search_manager import SearchManager

class RCProcessorWindow(ctk.CTkToplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("RC Processor - Dashboard")
        self.geometry("1000x850") 
        
        self.lift()
        
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(expand=True, fill='both', padx=10, pady=10)
        
        self.tab_search = self.tabview.add("Search Ration Card")
        self.tab_dash = self.tabview.add("Auto Process (One-Click)")
        self.tab_dl = self.tabview.add("Download")
        self.tab_conv = self.tabview.add("HTML to CSV")
        self.tab_enrich = self.tabview.add("Enrichment")
        self.tab_db = self.tabview.add("CSV to Database")
        
        self.tabview.set("Search Ration Card")

        self.create_search_tab()
        self.create_dashboard_tab()
        self.create_download_tab()
        self.create_convert_tab()
        self.create_enrichment_tab()
        self.create_database_tab()

    def create_search_tab(self):
        tab = self.tab_search
        
        db_path = os.path.join("data", "rc_db", "final_rc_data.db")
        if not os.path.exists(db_path):
            db_path = os.path.join("data", "rc_db", "rcdb.db")
        
        self.search_manager = SearchManager(db_path)
        self.search_manager.connect()
        
        main_frame = ctk.CTkFrame(tab, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(header_frame, text="Search Ration Card", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")
        
        ctk.CTkLabel(main_frame, text="Enter 10 Digit Ration Card Number:", font=ctk.CTkFont(size=14)).pack(anchor="w")
        
        self.rc_entry_var = ctk.StringVar()
        self.rc_entry_var.trace_add("write", self.on_rc_search_change)
        
        self.rc_entry = ctk.CTkEntry(main_frame, textvariable=self.rc_entry_var, font=ctk.CTkFont(size=16), height=35)
        self.rc_entry.pack(fill="x", pady=(5, 5))
        self.rc_entry.focus_set()
        self.rc_entry.bind("<Return>", self.save_search_data)

        self.match_count_var = ctk.StringVar(value="")
        ctk.CTkLabel(main_frame, textvariable=self.match_count_var, font=ctk.CTkFont(size=12), text_color="green").pack(anchor="w", pady=(0, 15))
        
        hint_frame = ctk.CTkFrame(main_frame)
        hint_frame.pack(fill="x", expand=False, pady=(0, 10))
        
        ctk.CTkLabel(hint_frame, text="Record Details", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=15, pady=(10, 5))
        
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
            row_frame = ctk.CTkFrame(hint_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=2, padx=15)
            ctk.CTkLabel(row_frame, text=f"{display_name}:", width=200, anchor="w", font=ctk.CTkFont(weight="bold")).pack(side="left")
            val_label = ctk.CTkLabel(row_frame, text="", anchor="w")
            val_label.pack(side="left", fill="x", expand=True)
            self.search_labels[db_col] = val_label
            
        ctk.CTkFrame(hint_frame, height=5, fg_color="transparent").pack() # bottom padding

        edit_frame = ctk.CTkFrame(main_frame)
        edit_frame.pack(fill="x", expand=False, pady=(0, 10))
        
        ctk.CTkLabel(edit_frame, text="Additional Info (Editable)", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, sticky='w', padx=15, pady=(10, 5))

        ctk.CTkLabel(edit_frame, text="Caste:", width=200, anchor="w", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, sticky='w', padx=15, pady=5)
        self.search_caste_var = ctk.StringVar()
        self.entry_caste = ctk.CTkEntry(edit_frame, textvariable=self.search_caste_var, width=300)
        self.entry_caste.grid(row=1, column=1, sticky='w', pady=5)
        self.entry_caste.bind("<Return>", self.save_search_data)

        ctk.CTkLabel(edit_frame, text="Mobile No:", width=200, anchor="w", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, sticky='w', padx=15, pady=5)
        self.search_mobile_var = ctk.StringVar()
        self.entry_mobile = ctk.CTkEntry(edit_frame, textvariable=self.search_mobile_var, width=300)
        self.entry_mobile.grid(row=2, column=1, sticky='w', pady=(5, 15))
        self.entry_mobile.bind("<Return>", self.save_search_data)

        self.rc_entry.bind("<Tab>", lambda e: self.entry_caste.focus_set())
        self.entry_caste.bind("<Tab>", lambda e: self.entry_mobile.focus_set())
        self.entry_mobile.bind("<Tab>", lambda e: self.rc_entry.focus_set())

        output_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        output_frame.pack(fill="x", pady=(15, 0))
        ctk.CTkLabel(output_frame, text="Save to File:").pack(side="left", padx=(0, 5))
        self.search_output_var = ctk.StringVar(value=os.path.join("data", "rc_db", "Benef_list.csv"))
        ctk.CTkEntry(output_frame, textvariable=self.search_output_var).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(output_frame, text="Browse...", command=self.browse_search_output).pack(side="left")

        ctk.CTkLabel(main_frame, text="Press Enter to save match to file", font=ctk.CTkFont(size=12, slant="italic"), text_color="gray").pack(pady=(5, 0))

        self.flash_label = ctk.CTkLabel(main_frame, text="", font=ctk.CTkFont(size=14, weight="bold"))
        self.flash_label.pack(pady=(5, 0))
        
        status_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        status_frame.pack(side="bottom", fill="x", pady=(10, 0))
        
        self.search_db_status_var = ctk.StringVar(value=f"Connected to: {db_path}" if os.path.exists(db_path) else "Database not found! Run pipeline first.")
        ctk.CTkLabel(status_frame, textvariable=self.search_db_status_var, font=ctk.CTkFont(size=11), text_color="#1f6aa5").pack(side="left")
        
        ctk.CTkButton(status_frame, text="Link Database", width=120, command=self.browse_search_db).pack(side="right")

        self.current_search_match = {}

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

    def create_dashboard_tab(self):
        tab = self.tab_dash
        
        frame_config = ctk.CTkFrame(tab)
        frame_config.pack(fill='x', padx=20, pady=20)
        frame_config.columnconfigure(1, weight=1)
        
        ctk.CTkLabel(frame_config, text="Source URL:").grid(row=0, column=0, sticky='w', padx=10, pady=10)
        self.dash_url_var = ctk.StringVar()
        self.dash_url_var.trace_add("write", self.on_dash_url_change)
        ctk.CTkEntry(frame_config, textvariable=self.dash_url_var).grid(row=0, column=1, sticky='ew', padx=10, pady=10)
        
        ctk.CTkLabel(frame_config, text="Session ID:").grid(row=1, column=0, sticky='w', padx=10, pady=10)
        self.dash_session_var = ctk.StringVar()
        ctk.CTkEntry(frame_config, textvariable=self.dash_session_var).grid(row=1, column=1, sticky='ew', padx=10, pady=10)

        ctk.CTkLabel(frame_config, text="Dealer List CSV:").grid(row=3, column=0, sticky='w', padx=10, pady=10)
        self.dash_dealer_file_var = ctk.StringVar(value=os.path.join("data", "rc_db", "dealers list.csv"))
        ctk.CTkEntry(frame_config, textvariable=self.dash_dealer_file_var).grid(row=3, column=1, sticky='ew', padx=10, pady=10)
        ctk.CTkButton(frame_config, text="Browse...", command=self.browse_dash_dealer).grid(row=3, column=2, padx=10, pady=10)

        ctk.CTkLabel(frame_config, text="Dealer Code Column:").grid(row=4, column=0, sticky='w', padx=10, pady=10)
        self.dash_dealer_code_var = ctk.StringVar()
        self.dash_dealer_code_combo = ctk.CTkOptionMenu(frame_config, variable=self.dash_dealer_code_var, values=[""])
        self.dash_dealer_code_combo.grid(row=4, column=1, sticky='ew', padx=10, pady=10)

        ctk.CTkLabel(frame_config, text="Dealer Name Column:").grid(row=5, column=0, sticky='w', padx=10, pady=10)
        self.dash_dealer_name_var = ctk.StringVar()
        self.dash_dealer_name_combo = ctk.CTkOptionMenu(frame_config, variable=self.dash_dealer_name_var, values=[""])
        self.dash_dealer_name_combo.grid(row=5, column=1, sticky='ew', padx=10, pady=10)

        ctk.CTkLabel(frame_config, text="Caste Database CSV:").grid(row=7, column=0, sticky='w', padx=10, pady=10)
        self.dash_caste_file_var = ctk.StringVar(value=os.path.join("data", "rc_db", "castedb.csv"))
        ctk.CTkEntry(frame_config, textvariable=self.dash_caste_file_var).grid(row=7, column=1, sticky='ew', padx=10, pady=10)
        ctk.CTkButton(frame_config, text="Browse...", command=self.browse_dash_caste).grid(row=7, column=2, padx=10, pady=10)

        ctk.CTkLabel(frame_config, text="Working Directory:").grid(row=9, column=0, sticky='w', padx=10, pady=10)
        self.dash_output_dir_var = ctk.StringVar(value=os.path.join("data", "rc_db"))
        ctk.CTkEntry(frame_config, textvariable=self.dash_output_dir_var).grid(row=9, column=1, sticky='ew', padx=10, pady=10)
        ctk.CTkButton(frame_config, text="Browse...", command=self.browse_dash_output).grid(row=9, column=2, padx=10, pady=10)

        ctk.CTkLabel(frame_config, text="Final DB Filename:").grid(row=10, column=0, sticky='w', padx=10, pady=10)
        self.dash_db_name_var = ctk.StringVar(value="final_rc_data.db")
        ctk.CTkEntry(frame_config, textvariable=self.dash_db_name_var).grid(row=10, column=1, sticky='ew', padx=10, pady=10)

        ctk.CTkButton(tab, text="START AUTO PROCESS", font=ctk.CTkFont(weight="bold"), command=self.start_pipeline).pack(pady=15)

        self.dash_log = ctk.CTkTextbox(tab, height=200, state='disabled')
        self.dash_log.pack(fill='both', expand=True, padx=20, pady=10)

    def create_download_tab(self):
        tab = self.tab_dl
        tab.columnconfigure(1, weight=1)
        
        ctk.CTkLabel(tab, text="Source URL (from browser):").grid(row=0, column=0, sticky='w', padx=10, pady=10)
        self.url_var = ctk.StringVar()
        self.url_var.trace_add("write", self.on_url_change)
        ctk.CTkEntry(tab, textvariable=self.url_var).grid(row=0, column=1, sticky='ew', padx=10, pady=10)
        
        ctk.CTkLabel(tab, text="Extracted Session ID:").grid(row=1, column=0, sticky='w', padx=10, pady=10)
        self.session_id_var = ctk.StringVar()
        ctk.CTkEntry(tab, textvariable=self.session_id_var).grid(row=1, column=1, sticky='ew', padx=10, pady=10)
        
        ctk.CTkLabel(tab, text="Dealer CSV File:").grid(row=2, column=0, sticky='w', padx=10, pady=10)
        self.download_csv_var = ctk.StringVar()
        ctk.CTkEntry(tab, textvariable=self.download_csv_var).grid(row=2, column=1, sticky='ew', padx=10, pady=10)
        ctk.CTkButton(tab, text="Browse...", command=self.browse_download_csv).grid(row=2, column=2, padx=10, pady=10)
        
        ctk.CTkLabel(tab, text="Dealer Code Column:").grid(row=3, column=0, sticky='w', padx=10, pady=10)
        self.column_var = ctk.StringVar()
        self.column_combo = ctk.CTkOptionMenu(tab, variable=self.column_var, values=[""])
        self.column_combo.grid(row=3, column=1, sticky='ew', padx=10, pady=10)
        
        ctk.CTkLabel(tab, text="Output Directory:").grid(row=4, column=0, sticky='w', padx=10, pady=10)
        self.download_output_var = ctk.StringVar()
        ctk.CTkEntry(tab, textvariable=self.download_output_var).grid(row=4, column=1, sticky='ew', padx=10, pady=10)
        ctk.CTkButton(tab, text="Browse...", command=self.browse_download_output).grid(row=4, column=2, padx=10, pady=10)
        
        ctk.CTkButton(tab, text="Start Download", command=self.start_download).grid(row=5, column=1, pady=20)
        
        self.download_log = ctk.CTkTextbox(tab, state='disabled')
        self.download_log.grid(row=6, column=0, columnspan=3, sticky='nsew', padx=10, pady=10)
        tab.rowconfigure(6, weight=1)

    def create_convert_tab(self):
        tab = self.tab_conv
        tab.columnconfigure(1, weight=1)
        
        ctk.CTkLabel(tab, text="Input Directory (HTML files):").grid(row=0, column=0, sticky='w', padx=10, pady=10)
        self.convert_input_var = ctk.StringVar()
        ctk.CTkEntry(tab, textvariable=self.convert_input_var).grid(row=0, column=1, sticky='ew', padx=10, pady=10)
        ctk.CTkButton(tab, text="Browse...", command=self.browse_convert_input).grid(row=0, column=2, padx=10, pady=10)
        
        ctk.CTkLabel(tab, text="Output CSV File:").grid(row=1, column=0, sticky='w', padx=10, pady=10)
        self.convert_output_var = ctk.StringVar()
        ctk.CTkEntry(tab, textvariable=self.convert_output_var).grid(row=1, column=1, sticky='ew', padx=10, pady=10)
        ctk.CTkButton(tab, text="Browse...", command=self.browse_convert_output).grid(row=1, column=2, padx=10, pady=10)
        
        ctk.CTkButton(tab, text="Start Conversion", command=self.start_conversion).grid(row=2, column=1, pady=20)
        
        self.convert_log = ctk.CTkTextbox(tab, state='disabled')
        self.convert_log.grid(row=3, column=0, columnspan=3, sticky='nsew', padx=10, pady=10)
        tab.rowconfigure(3, weight=1)

    def create_enrichment_tab(self):
        tab = self.tab_enrich
        
        frame_input = ctk.CTkFrame(tab)
        frame_input.pack(fill='x', padx=10, pady=10)
        frame_input.columnconfigure(1, weight=1)
        
        ctk.CTkLabel(frame_input, text="Input Data File:").grid(row=0, column=0, sticky='w', padx=10, pady=10)
        self.enrich_input_var = ctk.StringVar()
        ctk.CTkEntry(frame_input, textvariable=self.enrich_input_var).grid(row=0, column=1, sticky='ew', padx=10, pady=10)
        ctk.CTkButton(frame_input, text="Browse...", command=self.browse_enrich_input).grid(row=0, column=2, padx=10, pady=10)

        frame_caste = ctk.CTkFrame(tab)
        frame_caste.pack(fill='x', padx=10, pady=10)
        frame_caste.columnconfigure(1, weight=1)

        self.use_caste_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(frame_caste, text="Enable Caste Mapping", variable=self.use_caste_var).grid(row=0, column=0, columnspan=2, sticky='w', padx=10, pady=10)

        ctk.CTkLabel(frame_caste, text="Name Column (Input):").grid(row=1, column=0, sticky='w', padx=10, pady=10)
        self.caste_name_col_var = ctk.StringVar()
        self.caste_name_combo = ctk.CTkOptionMenu(frame_caste, variable=self.caste_name_col_var, values=[""])
        self.caste_name_combo.grid(row=1, column=1, sticky='ew', padx=10, pady=10)

        ctk.CTkLabel(frame_caste, text="Caste Database File:").grid(row=2, column=0, sticky='w', padx=10, pady=10)
        self.caste_db_var = ctk.StringVar()
        ctk.CTkEntry(frame_caste, textvariable=self.caste_db_var).grid(row=2, column=1, sticky='ew', padx=10, pady=10)
        ctk.CTkButton(frame_caste, text="Browse...", command=self.browse_caste_db).grid(row=2, column=2, padx=10, pady=10)

        frame_dealer = ctk.CTkFrame(tab)
        frame_dealer.pack(fill='x', padx=10, pady=10)
        frame_dealer.columnconfigure(1, weight=1)

        self.use_dealer_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(frame_dealer, text="Enable Dealer Mapping", variable=self.use_dealer_var).grid(row=0, column=0, columnspan=2, sticky='w', padx=10, pady=10)

        ctk.CTkLabel(frame_dealer, text="Dealer Code Column (Input):").grid(row=1, column=0, sticky='w', padx=10, pady=10)
        self.dealer_data_col_var = ctk.StringVar()
        self.dealer_data_combo = ctk.CTkOptionMenu(frame_dealer, variable=self.dealer_data_col_var, values=[""])
        self.dealer_data_combo.grid(row=1, column=1, sticky='ew', padx=10, pady=10)

        ctk.CTkLabel(frame_dealer, text="Dealer List File:").grid(row=2, column=0, sticky='w', padx=10, pady=10)
        self.dealer_db_var = ctk.StringVar()
        ctk.CTkEntry(frame_dealer, textvariable=self.dealer_db_var).grid(row=2, column=1, sticky='ew', padx=10, pady=10)
        ctk.CTkButton(frame_dealer, text="Browse...", command=self.browse_dealer_db).grid(row=2, column=2, padx=10, pady=10)

        ctk.CTkLabel(frame_dealer, text="DB Code Column:").grid(row=3, column=0, sticky='w', padx=10, pady=10)
        self.dealer_db_code_var = ctk.StringVar()
        self.dealer_db_code_combo = ctk.CTkOptionMenu(frame_dealer, variable=self.dealer_db_code_var, values=[""])
        self.dealer_db_code_combo.grid(row=3, column=1, sticky='ew', padx=10, pady=10)
        
        ctk.CTkLabel(frame_dealer, text="DB Name Column:").grid(row=4, column=0, sticky='w', padx=10, pady=10)
        self.dealer_db_name_var = ctk.StringVar()
        self.dealer_db_name_combo = ctk.CTkOptionMenu(frame_dealer, variable=self.dealer_db_name_var, values=[""])
        self.dealer_db_name_combo.grid(row=4, column=1, sticky='ew', padx=10, pady=10)

        frame_output = ctk.CTkFrame(tab)
        frame_output.pack(fill='x', padx=10, pady=10)
        frame_output.columnconfigure(1, weight=1)

        ctk.CTkLabel(frame_output, text="Output File:").grid(row=0, column=0, sticky='w', padx=10, pady=10)
        self.enrich_output_var = ctk.StringVar()
        ctk.CTkEntry(frame_output, textvariable=self.enrich_output_var).grid(row=0, column=1, sticky='ew', padx=10, pady=10)
        ctk.CTkButton(frame_output, text="Browse...", command=self.browse_enrich_output).grid(row=0, column=2, padx=10, pady=10)
        
        ctk.CTkButton(tab, text="Start Enrichment", command=self.start_enrichment).pack(pady=10)
        
        self.enrich_log = ctk.CTkTextbox(tab, state='disabled')
        self.enrich_log.pack(fill='both', expand=True, padx=10, pady=10)

    def create_database_tab(self):
        tab = self.tab_db
        tab.columnconfigure(1, weight=1)
        
        ctk.CTkLabel(tab, text="Input CSV File:").grid(row=0, column=0, sticky='w', padx=10, pady=10)
        self.db_input_var = ctk.StringVar()
        ctk.CTkEntry(tab, textvariable=self.db_input_var).grid(row=0, column=1, sticky='ew', padx=10, pady=10)
        ctk.CTkButton(tab, text="Browse...", command=self.browse_db_input).grid(row=0, column=2, padx=10, pady=10)
        
        ctk.CTkLabel(tab, text="Output DB File:").grid(row=1, column=0, sticky='w', padx=10, pady=10)
        self.db_output_var = ctk.StringVar()
        ctk.CTkEntry(tab, textvariable=self.db_output_var).grid(row=1, column=1, sticky='ew', padx=10, pady=10)
        ctk.CTkButton(tab, text="Browse...", command=self.browse_db_output).grid(row=1, column=2, padx=10, pady=10)
        
        ctk.CTkLabel(tab, text="Table Name:").grid(row=2, column=0, sticky='w', padx=10, pady=10)
        self.db_table_var = ctk.StringVar(value="beneficiaries")
        ctk.CTkEntry(tab, textvariable=self.db_table_var).grid(row=2, column=1, sticky='ew', padx=10, pady=10)
        
        ctk.CTkButton(tab, text="Create Database", command=self.start_db_conversion).grid(row=3, column=1, pady=20)
        
        self.db_log = ctk.CTkTextbox(tab, state='disabled')
        self.db_log.grid(row=4, column=0, columnspan=3, sticky='nsew', padx=10, pady=10)
        tab.rowconfigure(4, weight=1)

    def on_url_change(self, *args):
        url_text = self.url_var.get().strip()
        if not url_text: return
        session_match = re.search(r'\(S\(([a-zA-Z0-9]+)\)\)', url_text)
        if session_match: self.session_id_var.set(session_match.group(1))

    def on_dash_url_change(self, *args):
        url_text = self.dash_url_var.get().strip()
        if not url_text: return
        session_match = re.search(r'\(S\(([a-zA-Z0-9]+)\)\)', url_text)
        if session_match: self.dash_session_var.set(session_match.group(1))

    def browse_download_csv(self):
        filename = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")])
        if filename:
            self.download_csv_var.set(filename)
            try:
                with open(filename, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    headers = reader.fieldnames
                    if headers:
                        self.column_combo.configure(values=headers)
                        self.column_var.set(headers[0])
                    else: messagebox.showwarning("Warning", "No headers found in CSV.")
            except Exception as e: messagebox.showerror("Error", f"Failed to read CSV headers: {e}")

    def browse_download_output(self):
        dirname = filedialog.askdirectory()
        if dirname: self.download_output_var.set(dirname)

    def browse_convert_input(self):
        dirname = filedialog.askdirectory()
        if dirname: self.convert_input_var.set(dirname)

    def browse_convert_output(self):
        filename = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if filename: self.convert_output_var.set(filename)

    def browse_enrich_input(self):
        filename = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv"), ("Excel Files", "*.xlsx;*.xls"), ("All Files", "*.*")])
        if filename:
            self.enrich_input_var.set(filename)
            try:
                if filename.lower().endswith('.csv'): df = pd.read_csv(filename, nrows=0)
                else: df = pd.read_excel(filename, nrows=0)
                headers = list(df.columns)
                if headers:
                    self.caste_name_combo.configure(values=headers)
                    if "Name" in headers: self.caste_name_col_var.set("Name")
                    else: self.caste_name_col_var.set(headers[0])
                    
                    self.dealer_data_combo.configure(values=headers)
                    if "Source File" in headers: self.dealer_data_col_var.set("Source File")
                    elif "Dealer Code" in headers: self.dealer_data_col_var.set("Dealer Code")
                    else: self.dealer_data_col_var.set(headers[0])
                else: messagebox.showwarning("Warning", "No headers found in file.")
            except Exception as e: messagebox.showerror("Error", f"Failed to read file headers: {e}")

    def browse_caste_db(self):
        filename = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv"), ("Excel Files", "*.xlsx;*.xls")])
        if filename: self.caste_db_var.set(filename)

    def browse_dealer_db(self):
        filename = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv"), ("Excel Files", "*.xlsx;*.xls")])
        if filename:
            self.dealer_db_var.set(filename)
            try:
                if filename.lower().endswith('.csv'): df = pd.read_csv(filename, nrows=0)
                else: df = pd.read_excel(filename, nrows=0)
                headers = list(df.columns)
                if headers:
                    self.dealer_db_code_combo.configure(values=headers)
                    if "Code" in headers: self.dealer_db_code_var.set("Code")
                    else: self.dealer_db_code_var.set(headers[0])
                    
                    self.dealer_db_name_combo.configure(values=headers)
                    if "Name" in headers: self.dealer_db_name_var.set("Name")
                    else: self.dealer_db_name_var.set(headers[0])
                else: messagebox.showwarning("Warning", "No headers found in dealer DB file.")
            except Exception as e: messagebox.showerror("Error", f"Failed to read file headers: {e}")

    def browse_enrich_output(self):
        filename = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv"), ("Excel Files", "*.xlsx")])
        if filename: self.enrich_output_var.set(filename)

    def browse_db_input(self):
        filename = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")])
        if filename: self.db_input_var.set(filename)

    def browse_db_output(self):
        filename = filedialog.asksaveasfilename(defaultextension=".db", filetypes=[("SQLite DB", "*.db"), ("All Files", "*.*")])
        if filename: self.db_output_var.set(filename)

    def browse_dash_dealer(self):
        filename = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")])
        if filename:
            self.dash_dealer_file_var.set(filename)
            try:
                with open(filename, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    headers = reader.fieldnames
                    if headers:
                        self.dash_dealer_code_combo.configure(values=headers)
                        if "Code" in headers: self.dash_dealer_code_var.set("Code")
                        else: self.dash_dealer_code_var.set(headers[0])
                        
                        self.dash_dealer_name_combo.configure(values=headers)
                        if "Name" in headers: self.dash_dealer_name_var.set("Name")
                        else: self.dash_dealer_name_var.set(headers[0])
                    else: messagebox.showwarning("Warning", "No headers found in CSV.")
            except Exception as e: messagebox.showerror("Error", f"Failed to read CSV headers: {e}")

    def browse_dash_caste(self):
        filename = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv"), ("Excel Files", "*.xlsx")])
        if filename: self.dash_caste_file_var.set(filename)

    def browse_dash_output(self):
        dirname = filedialog.askdirectory()
        if dirname: self.dash_output_dir_var.set(dirname)

    def _append_log(self, text_widget, message):
        text_widget.configure(state='normal')
        text_widget.insert(tk.END, message + "\n")
        text_widget.see(tk.END)
        text_widget.configure(state='disabled')

    def log_download(self, message):
        self.after(0, self._append_log, self.download_log, message)
    
    def log_convert(self, message):
        self.after(0, self._append_log, self.convert_log, message)
        
    def log_enrich(self, message):
        self.after(0, self._append_log, self.enrich_log, message)
        
    def log_db(self, message):
        self.after(0, self._append_log, self.db_log, message)
        
    def log_dash(self, message):
        self.after(0, self._append_log, self.dash_log, message)

    def start_download(self):
        csv_file = self.download_csv_var.get()
        output_dir = self.download_output_var.get()
        session_id = self.session_id_var.get()
        dealer_column = self.column_var.get()
        if not csv_file or not output_dir:
            messagebox.showerror("Error", "Please select CSV file and Output Directory.")
            return
        if not dealer_column:
             messagebox.showerror("Error", "Please select the Dealer Code Column.")
             return
        if not session_id:
             messagebox.showerror("Error", "Please provide a URL to extract Session ID.")
             return
        self.log_download("Starting download...")
        def run():
            try:
                downloader = BeneficiaryDownloader()
                downloader.download_from_csv(csv_file, output_dir, session_id, dealer_column=dealer_column, progress_callback=self.log_download)
                self.log_download("Download process finished.")
            except Exception as e:
                self.log_download(f"Critical Error: {e}")
        threading.Thread(target=run, daemon=True).start()

    def start_conversion(self):
        input_dir = self.convert_input_var.get()
        output_file = self.convert_output_var.get()
        if not input_dir or not output_file:
            messagebox.showerror("Error", "Please select Input Directory and Output File.")
            return
        self.log_convert("Starting conversion...")
        def run():
            try:
                converter = BeneficiaryConverter()
                converter.convert_directory(input_dir, output_file, progress_callback=self.log_convert)
                self.log_convert("Conversion process finished.")
            except Exception as e:
                self.log_convert(f"Critical Error: {e}")
        threading.Thread(target=run, daemon=True).start()

    def start_enrichment(self):
        input_file = self.enrich_input_var.get()
        output_file = self.enrich_output_var.get()
        if not input_file or not output_file:
            messagebox.showerror("Error", "Please select Input and Output files.")
            return
        caste_config = None
        if self.use_caste_var.get():
            caste_db = self.caste_db_var.get()
            caste_col = self.caste_name_col_var.get()
            if not caste_db or not caste_col:
                messagebox.showerror("Error", "Please fill in Caste Mapping details.")
                return
            caste_config = {'db_path': caste_db, 'name_col': caste_col}
        dealer_config = None
        if self.use_dealer_var.get():
            dealer_db = self.dealer_db_var.get()
            dealer_data_col = self.dealer_data_col_var.get()
            db_code = self.dealer_db_code_var.get()
            db_name = self.dealer_db_name_var.get()
            if not dealer_db or not dealer_data_col or not db_code or not db_name:
                 messagebox.showerror("Error", "Please fill in Dealer Mapping details.")
                 return
            dealer_config = {'db_path': dealer_db, 'data_code_col': dealer_data_col, 'db_code_col': db_code, 'db_name_col': db_name}
        if not caste_config and not dealer_config:
             messagebox.showerror("Error", "Please enable at least one enrichment option.")
             return
        self.log_enrich("Starting enrichment process...")
        def run():
            try:
                enricher = DataEnricher()
                success, msg = enricher.enrich_data(input_file, output_file, caste_config=caste_config, dealer_config=dealer_config, progress_callback=self.log_enrich)
                if not success: self.log_enrich(f"Error: {msg}")
            except Exception as e: self.log_enrich(f"Critical Error: {e}")
        threading.Thread(target=run, daemon=True).start()

    def start_db_conversion(self):
        csv_file = self.db_input_var.get()
        db_file = self.db_output_var.get()
        table_name = self.db_table_var.get()
        if not csv_file or not db_file or not table_name:
            messagebox.showerror("Error", "Please fill in all database fields.")
            return
        self.log_db("Starting database conversion...")
        def run():
            try:
                manager = DatabaseManager()
                success, msg = manager.convert_csv_to_sqlite(csv_file, db_file, table_name, progress_callback=self.log_db)
                if not success: self.log_db(f"Error: {msg}")
            except Exception as e: self.log_db(f"Critical Error: {e}")
        threading.Thread(target=run, daemon=True).start()

    def start_pipeline(self):
        session_id = self.dash_session_var.get()
        dealer_list = self.dash_dealer_file_var.get()
        dealer_code_col = self.dash_dealer_code_var.get()
        dealer_name_col = self.dash_dealer_name_var.get()
        caste_db = self.dash_caste_file_var.get()
        output_dir = self.dash_output_dir_var.get()
        final_db_name = self.dash_db_name_var.get()
        if not all([session_id, dealer_list, dealer_code_col, dealer_name_col, caste_db, output_dir, final_db_name]):
            messagebox.showerror("Error", "Please fill in ALL fields in the configuration.")
            return
        self.log_dash(f"Starting Auto Process...")
        config = {'dealer_list_file': dealer_list, 'dealer_code_col': dealer_code_col, 'dealer_name_col': dealer_name_col, 'caste_db_file': caste_db, 'session_id': session_id, 'output_dir': output_dir, 'final_db_name': final_db_name}
        def run():
            manager = PipelineManager()
            success, msg = manager.run_pipeline(config, progress_callback=self.log_dash)
            if success: self.log_dash("Pipeline completed successfully!")
            else: self.log_dash(f"Pipeline failed: {msg}")
        threading.Thread(target=run, daemon=True).start()

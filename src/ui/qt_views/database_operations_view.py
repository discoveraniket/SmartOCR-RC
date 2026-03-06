import os
import threading
import csv
import re
import pandas as pd
from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QFrame
from qfluentwidgets import (Pivot, SegmentedWidget, SubtitleLabel, setFont, 
                            CardWidget, StrongBodyLabel, BodyLabel, CaptionLabel,
                            LineEdit, PushButton, PrimaryPushButton, 
                            InfoBar, InfoBarPosition, TextEdit, CheckBox, 
                            ComboBox, MessageBox, IconWidget, FluentIcon as FIF)

from src.rc_processor.downloader import BeneficiaryDownloader
from src.rc_processor.converter import BeneficiaryConverter
from src.rc_processor.caste_deducer import DataEnricher
from src.rc_processor.db_manager import DatabaseManager

class LogSignal(QObject):
    log_received = Signal(str, str) # tab_name, message

class StepIndicator(QFrame):
    """A visual indicator of the sequential workflow steps"""
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(15, 10, 15, 10)
        self.layout.setSpacing(15)
        self.setObjectName("step-indicator")
        self.setStyleSheet("QFrame#step-indicator { background: transparent; }")

        self.steps = ["Download", "HTML to CSV", "Enrichment", "CSV to DB"]
        self.labels = []
        
        for i, step in enumerate(self.steps):
            step_container = QHBoxLayout()
            step_container.setSpacing(8)
            
            lbl = BodyLabel(f"{i+1}. {step}", self)
            self.labels.append(lbl)
            
            self.layout.addWidget(lbl)
            
            if i < len(self.steps) - 1:
                # icon = IconWidget(FIF.CHEVRON_RIGHT, self) (for redundancy)
                icon = IconWidget(FIF.RIGHT_ARROW, self)
                icon.setFixedSize(14, 14)
                self.layout.addWidget(icon)
        
        self.layout.addStretch(1)
        self.set_current_step(0)

    def set_current_step(self, index):
        for i, lbl in enumerate(self.labels):
            if i == index:
                lbl.setStyleSheet("color: #0078d4; font-weight: bold;")
                setFont(lbl, 16, weight=QFont.Weight.Bold)
            else:
                lbl.setStyleSheet("color: gray; font-weight: normal;")
                setFont(lbl, 14)

class BaseTab(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 20, 0, 0)
        self.layout.setSpacing(15)

    def _add_log_area(self):
        self.layout.addWidget(StrongBodyLabel("Process Logs", self))
        self.log_area = TextEdit(self)
        self.log_area.setReadOnly(True)
        self.log_area.setPlaceholderText("Logs will appear here...")
        self.layout.addWidget(self.log_area, 1)

    def append_log(self, message):
        self.log_area.append(message)
        # Scroll to bottom
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())

class DownloadTab(BaseTab):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._setup_ui()

    def _setup_ui(self):
        # Configuration Card
        self.config_card = CardWidget(self)
        config_layout = QVBoxLayout(self.config_card)
        
        # URL
        config_layout.addWidget(BodyLabel("Source URL (from browser):", self))
        self.url_input = LineEdit(self)
        self.url_input.setPlaceholderText("Paste URL here to extract Session ID...")
        self.url_input.textChanged.connect(self._on_url_changed)
        config_layout.addWidget(self.url_input)

        # Session ID
        config_layout.addWidget(BodyLabel("Extracted Session ID:", self))
        self.session_id_input = LineEdit(self)
        config_layout.addWidget(self.session_id_input)

        # Dealer CSV
        config_layout.addWidget(BodyLabel("Dealer CSV File:", self))
        dealer_layout = QHBoxLayout()
        self.dealer_csv_input = LineEdit(self)
        self.browse_dealer_btn = PushButton("Browse...", self)
        self.browse_dealer_btn.clicked.connect(self._browse_dealer_csv)
        dealer_layout.addWidget(self.dealer_csv_input, 1)
        dealer_layout.addWidget(self.browse_dealer_btn)
        config_layout.addLayout(dealer_layout)

        # Dealer Code Column
        config_layout.addWidget(BodyLabel("Dealer Code Column:", self))
        self.column_combo = ComboBox(self)
        config_layout.addWidget(self.column_combo)

        # Output Dir
        config_layout.addWidget(BodyLabel("Output Directory:", self))
        out_layout = QHBoxLayout()
        self.output_dir_input = LineEdit(self)
        self.browse_out_btn = PushButton("Browse...", self)
        self.browse_out_btn.clicked.connect(self._browse_output_dir)
        out_layout.addWidget(self.output_dir_input, 1)
        out_layout.addWidget(self.browse_out_btn)
        config_layout.addLayout(out_layout)

        self.layout.addWidget(self.config_card)

        # Actions
        self.start_btn = PrimaryPushButton("Start Download", self)
        self.start_btn.clicked.connect(self._start_download)
        self.layout.addWidget(self.start_btn)

        self._add_log_area()

    def _on_url_changed(self, text):
        session_match = re.search(r'\(S\(([a-zA-Z0-9]+)\)\)', text.strip())
        if session_match:
            self.session_id_input.setText(session_match.group(1))

    def _browse_dealer_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Dealer CSV", "", "CSV Files (*.csv);;All Files (*)")
        if file_path:
            self.dealer_csv_input.setText(file_path)
            try:
                with open(file_path, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    headers = reader.fieldnames
                    if headers:
                        self.column_combo.clear()
                        self.column_combo.addItems(headers)
                        if "Code" in headers: self.column_combo.setCurrentText("Code")
                    else:
                        InfoBar.warning("Warning", "No headers found in CSV.", parent=self.window())
            except Exception as e:
                InfoBar.error("Error", f"Failed to read CSV: {e}", parent=self.window())

    def _browse_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if dir_path:
            self.output_dir_input.setText(dir_path)

    def _start_download(self):
        csv_file = self.dealer_csv_input.text()
        output_dir = self.output_dir_input.text()
        session_id = self.session_id_input.text()
        dealer_col = self.column_combo.currentText()

        if not all([csv_file, output_dir, session_id, dealer_col]):
            InfoBar.error("Error", "Please fill in all fields", parent=self.window())
            return

        self.start_btn.setEnabled(False)
        self.log_area.clear()
        
        def run():
            try:
                downloader = BeneficiaryDownloader()
                downloader.download_from_csv(
                    csv_file, output_dir, session_id, 
                    dealer_column=dealer_col, 
                    progress_callback=self.append_log
                )
            except Exception as e:
                self.append_log(f"CRITICAL ERROR: {e}")
            finally:
                self.start_btn.setEnabled(True)

        threading.Thread(target=run, daemon=True).start()

class ConvertTab(BaseTab):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._setup_ui()

    def _setup_ui(self):
        self.config_card = CardWidget(self)
        config_layout = QVBoxLayout(self.config_card)

        config_layout.addWidget(BodyLabel("Input Directory (HTML files):", self))
        in_layout = QHBoxLayout()
        self.input_dir_input = LineEdit(self)
        self.browse_in_btn = PushButton("Browse...", self)
        self.browse_in_btn.clicked.connect(self._browse_input_dir)
        in_layout.addWidget(self.input_dir_input, 1)
        in_layout.addWidget(self.browse_in_btn)
        config_layout.addLayout(in_layout)

        config_layout.addWidget(BodyLabel("Output CSV File:", self))
        out_layout = QHBoxLayout()
        self.output_file_input = LineEdit(self)
        self.browse_out_btn = PushButton("Browse...", self)
        self.browse_out_btn.clicked.connect(self._browse_output_file)
        out_layout.addWidget(self.output_file_input, 1)
        out_layout.addWidget(self.browse_out_btn)
        config_layout.addLayout(out_layout)

        self.layout.addWidget(self.config_card)

        self.start_btn = PrimaryPushButton("Start Conversion", self)
        self.start_btn.clicked.connect(self._start_conversion)
        self.layout.addWidget(self.start_btn)

        self._add_log_area()

    def _browse_input_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Input Directory")
        if dir_path: self.input_dir_input.setText(dir_path)

    def _browse_output_file(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Output CSV", "", "CSV Files (*.csv)")
        if file_path: self.output_file_input.setText(file_path)

    def _start_conversion(self):
        input_dir = self.input_dir_input.text()
        output_file = self.output_file_input.text()

        if not input_dir or not output_file:
            InfoBar.error("Error", "Please select input and output", parent=self.window())
            return

        self.start_btn.setEnabled(False)
        self.log_area.clear()

        def run():
            try:
                converter = BeneficiaryConverter()
                converter.convert_directory(input_dir, output_file, progress_callback=self.append_log)
            except Exception as e:
                self.append_log(f"CRITICAL ERROR: {e}")
            finally:
                self.start_btn.setEnabled(True)

        threading.Thread(target=run, daemon=True).start()

class EnrichmentTab(BaseTab):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._setup_ui()

    def _setup_ui(self):
        # Input Section
        self.input_card = CardWidget(self)
        input_layout = QVBoxLayout(self.input_card)
        input_layout.addWidget(StrongBodyLabel("1. Input Data", self))
        
        in_row = QHBoxLayout()
        self.input_file_input = LineEdit(self)
        self.browse_in_btn = PushButton("Browse...", self)
        self.browse_in_btn.clicked.connect(self._browse_input_file)
        in_row.addWidget(self.input_file_input, 1)
        in_row.addWidget(self.browse_in_btn)
        input_layout.addLayout(in_row)
        self.layout.addWidget(self.input_card)

        # Caste Mapping Section
        self.caste_card = CardWidget(self)
        caste_layout = QVBoxLayout(self.caste_card)
        self.use_caste_check = CheckBox("Enable Caste Mapping", self)
        self.use_caste_check.setChecked(True)
        caste_layout.addWidget(self.use_caste_check)
        
        caste_layout.addWidget(BodyLabel("Name Column (in Input):", self))
        self.caste_name_combo = ComboBox(self)
        caste_layout.addWidget(self.caste_name_combo)
        
        caste_layout.addWidget(BodyLabel("Caste Database File:", self))
        c_db_row = QHBoxLayout()
        self.caste_db_input = LineEdit(self)
        self.browse_c_db_btn = PushButton("Browse...", self)
        self.browse_c_db_btn.clicked.connect(lambda: self._browse_file(self.caste_db_input, "Select Caste DB"))
        c_db_row.addWidget(self.caste_db_input, 1)
        c_db_row.addWidget(self.browse_c_db_btn)
        caste_layout.addLayout(c_db_row)
        self.layout.addWidget(self.caste_card)

        # Dealer Mapping Section
        self.dealer_card = CardWidget(self)
        dealer_layout = QVBoxLayout(self.dealer_card)
        self.use_dealer_check = CheckBox("Enable Dealer Mapping", self)
        dealer_layout.addWidget(self.use_dealer_check)

        dealer_layout.addWidget(BodyLabel("Dealer Code Column (in Input):", self))
        self.dealer_data_combo = ComboBox(self)
        dealer_layout.addWidget(self.dealer_data_combo)

        dealer_layout.addWidget(BodyLabel("Dealer List File:", self))
        d_db_row = QHBoxLayout()
        self.dealer_db_input = LineEdit(self)
        self.browse_d_db_btn = PushButton("Browse...", self)
        self.browse_d_db_btn.clicked.connect(self._browse_dealer_db)
        d_db_row.addWidget(self.dealer_db_input, 1)
        d_db_row.addWidget(self.browse_d_db_btn)
        dealer_layout.addLayout(d_db_row)

        h_layout = QHBoxLayout()
        v1 = QVBoxLayout(); v1.addWidget(BodyLabel("DB Code Col:", self)); self.d_db_code_combo = ComboBox(self); v1.addWidget(self.d_db_code_combo)
        v2 = QVBoxLayout(); v2.addWidget(BodyLabel("DB Name Col:", self)); self.d_db_name_combo = ComboBox(self); v2.addWidget(self.d_db_name_combo)
        h_layout.addLayout(v1); h_layout.addLayout(v2)
        dealer_layout.addLayout(h_layout)
        self.layout.addWidget(self.dealer_card)

        # Output Section
        self.output_card = CardWidget(self)
        out_layout = QVBoxLayout(self.output_card)
        out_layout.addWidget(StrongBodyLabel("2. Output File", self))
        out_row = QHBoxLayout()
        self.output_file_input = LineEdit(self)
        self.browse_out_btn = PushButton("Browse...", self)
        self.browse_out_btn.clicked.connect(self._browse_output_file)
        out_row.addWidget(self.output_file_input, 1)
        out_row.addWidget(self.browse_out_btn)
        out_layout.addLayout(out_row)
        self.layout.addWidget(self.output_card)

        self.start_btn = PrimaryPushButton("Start Enrichment", self)
        self.start_btn.clicked.connect(self._start_enrichment)
        self.layout.addWidget(self.start_btn)

        self._add_log_area()

    def _browse_file(self, line_edit, title):
        file_path, _ = QFileDialog.getOpenFileName(self, title, "", "CSV/Excel (*.csv *.xlsx *.xls);;All Files (*)")
        if file_path: line_edit.setText(file_path)

    def _browse_input_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Input Data", "", "CSV/Excel (*.csv *.xlsx *.xls);;All Files (*)")
        if file_path:
            self.input_file_input.setText(file_path)
            try:
                if file_path.lower().endswith('.csv'): df = pd.read_csv(file_path, nrows=0)
                else: df = pd.read_excel(file_path, nrows=0)
                headers = list(df.columns)
                self.caste_name_combo.clear(); self.caste_name_combo.addItems(headers)
                if "Name" in headers: self.caste_name_combo.setCurrentText("Name")
                self.dealer_data_combo.clear(); self.dealer_data_combo.addItems(headers)
                if "Source File" in headers: self.dealer_data_combo.setCurrentText("Source File")
            except Exception as e:
                InfoBar.error("Error", f"Failed to read headers: {e}", parent=self.window())

    def _browse_dealer_db(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Dealer DB", "", "CSV/Excel (*.csv *.xlsx *.xls)")
        if file_path:
            self.dealer_db_input.setText(file_path)
            try:
                if file_path.lower().endswith('.csv'): df = pd.read_csv(file_path, nrows=0)
                else: df = pd.read_excel(file_path, nrows=0)
                headers = list(df.columns)
                self.d_db_code_combo.clear(); self.d_db_code_combo.addItems(headers)
                self.d_db_name_combo.clear(); self.d_db_name_combo.addItems(headers)
                if "Code" in headers: self.d_db_code_combo.setCurrentText("Code")
                if "Name" in headers: self.d_db_name_combo.setCurrentText("Name")
            except Exception as e:
                InfoBar.error("Error", f"Failed to read headers: {e}", parent=self.window())

    def _browse_output_file(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Output", "", "CSV Files (*.csv);;Excel Files (*.xlsx)")
        if file_path: self.output_file_input.setText(file_path)

    def _start_enrichment(self):
        input_file = self.input_file_input.text()
        output_file = self.output_file_input.text()
        if not input_file or not output_file:
            InfoBar.error("Error", "Input/Output missing", parent=self.window())
            return

        caste_config = None
        if self.use_caste_check.isChecked():
            db = self.caste_db_input.text()
            col = self.caste_name_combo.currentText()
            if not db or not col:
                InfoBar.error("Error", "Caste Mapping info missing", parent=self.window())
                return
            caste_config = {'db_path': db, 'name_col': col}

        dealer_config = None
        if self.use_dealer_check.isChecked():
            db = self.dealer_db_input.text()
            d_col = self.dealer_data_combo.currentText()
            db_c = self.d_db_code_combo.currentText()
            db_n = self.d_db_name_combo.currentText()
            if not all([db, d_col, db_c, db_n]):
                InfoBar.error("Error", "Dealer Mapping info missing", parent=self.window())
                return
            dealer_config = {'db_path': db, 'data_code_col': d_col, 'db_code_col': db_c, 'db_name_col': db_n}

        if not caste_config and not dealer_config:
            InfoBar.error("Error", "Enable at least one enrichment", parent=self.window())
            return

        self.start_btn.setEnabled(False)
        self.log_area.clear()

        def run():
            try:
                enricher = DataEnricher()
                enricher.enrich_data(input_file, output_file, caste_config=caste_config, dealer_config=dealer_config, progress_callback=self.append_log)
            except Exception as e:
                self.append_log(f"CRITICAL ERROR: {e}")
            finally:
                self.start_btn.setEnabled(True)

        threading.Thread(target=run, daemon=True).start()

class DatabaseTab(BaseTab):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._setup_ui()

    def _setup_ui(self):
        self.config_card = CardWidget(self)
        config_layout = QVBoxLayout(self.config_card)

        config_layout.addWidget(BodyLabel("Input CSV File:", self))
        in_row = QHBoxLayout()
        self.input_file_input = LineEdit(self)
        self.browse_in_btn = PushButton("Browse...", self)
        self.browse_in_btn.clicked.connect(self._browse_input)
        in_row.addWidget(self.input_file_input, 1)
        in_row.addWidget(self.browse_in_btn)
        config_layout.addLayout(in_row)

        config_layout.addWidget(BodyLabel("Output SQLite DB File:", self))
        out_row = QHBoxLayout()
        self.output_file_input = LineEdit(self)
        self.browse_out_btn = PushButton("Browse...", self)
        self.browse_out_btn.clicked.connect(self._browse_output)
        out_row.addWidget(self.output_file_input, 1)
        out_row.addWidget(self.browse_out_btn)
        config_layout.addLayout(out_row)

        config_layout.addWidget(BodyLabel("Table Name:", self))
        self.table_input = LineEdit(self)
        self.table_input.setText("beneficiaries")
        config_layout.addWidget(self.table_input)

        self.layout.addWidget(self.config_card)

        self.start_btn = PrimaryPushButton("Create Database", self)
        self.start_btn.clicked.connect(self._start_db)
        self.layout.addWidget(self.start_btn)

        self._add_log_area()

    def _browse_input(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select CSV", "", "CSV Files (*.csv)")
        if file_path: self.input_file_input.setText(file_path)

    def _browse_output(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save SQLite DB", "", "SQLite DB (*.db)")
        if file_path: self.output_file_input.setText(file_path)

    def _start_db(self):
        csv_file = self.input_file_input.text()
        db_file = self.output_file_input.text()
        table = self.table_input.text()

        if not csv_file or not db_file or not table:
            InfoBar.error("Error", "Missing fields", parent=self.window())
            return

        self.start_btn.setEnabled(False)
        self.log_area.clear()

        def run():
            try:
                manager = DatabaseManager()
                manager.convert_csv_to_sqlite(csv_file, db_file, table_name=table, progress_callback=self.append_log)
            except Exception as e:
                self.append_log(f"CRITICAL ERROR: {e}")
            finally:
                self.start_btn.setEnabled(True)

        threading.Thread(target=run, daemon=True).start()

class DatabaseOperationsView(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("database-operations-view")
        self._setup_ui()

    def _setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(40, 40, 40, 40)
        self.layout.setSpacing(20)

        # Header
        self.title = SubtitleLabel("Database Operations Hub", self)
        setFont(self.title, 28)
        self.layout.addWidget(self.title)

        # Sequential Workflow Indicator
        self.step_indicator = StepIndicator(self)
        self.layout.addWidget(self.step_indicator)

        # Pivot Navigation
        self.pivot = Pivot(self)
        self.layout.addWidget(self.pivot)

        # Content Area
        self.stacked_widget = QWidget(self)
        self.stacked_layout = QVBoxLayout(self.stacked_widget)
        self.stacked_layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.stacked_widget, 1)

        # Tabs
        self.download_tab = DownloadTab(self)
        self.convert_tab = ConvertTab(self)
        self.enrichment_tab = EnrichmentTab(self)
        self.db_tab = DatabaseTab(self)

        self._add_tab(self.download_tab, "download", "1. Download")
        self._add_tab(self.convert_tab, "convert", "2. HTML to CSV")
        self._add_tab(self.enrichment_tab, "enrich", "3. Enrichment")
        self._add_tab(self.db_tab, "db", "4. CSV to DB")

        self.pivot.setCurrentItem("download")
        self._on_pivot_changed("download")
        self.pivot.currentItemChanged.connect(self._on_pivot_changed)

    def _add_tab(self, widget, route, text):
        widget.hide()
        self.stacked_layout.addWidget(widget)
        self.pivot.addItem(route, text, lambda: None)

    def _on_pivot_changed(self, route):
        for i in range(self.stacked_layout.count()):
            self.stacked_layout.itemAt(i).widget().hide()
        
        if route == "download":
            self.download_tab.show()
            self.step_indicator.set_current_step(0)
        elif route == "convert":
            self.convert_tab.show()
            self.step_indicator.set_current_step(1)
        elif route == "enrich":
            self.enrichment_tab.show()
            self.step_indicator.set_current_step(2)
        elif route == "db":
            self.db_tab.show()
            self.step_indicator.set_current_step(3)

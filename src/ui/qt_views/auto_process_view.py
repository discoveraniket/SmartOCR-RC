import os
import threading
import csv
import re
import pandas as pd
from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QFrame, QScrollArea
from qfluentwidgets import (SubtitleLabel, setFont, CardWidget, StrongBodyLabel, 
                            BodyLabel, LineEdit, PushButton, PrimaryPushButton, 
                            InfoBar, InfoBarPosition, TextEdit, ComboBox, 
                            IconWidget, FluentIcon as FIF)

from src.rc_processor.pipeline import PipelineManager

class AutoProcessView(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("auto-process-view")
        self._setup_ui()

    def _setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Use a ScrollArea for long configuration forms
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("background: transparent;")
        
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(40, 40, 40, 40)
        self.scroll_layout.setSpacing(25)

        # Header
        self.title = SubtitleLabel("Auto Process Pipeline", self)
        setFont(self.title, 28)
        self.scroll_layout.addWidget(self.title)

        # Description
        desc = BodyLabel("This one-click pipeline automates downloading, converting, enriching, and database generation.", self)
        desc.setStyleSheet("color: gray;")
        self.scroll_layout.addWidget(desc)

        # Configuration Card
        self.config_card = CardWidget(self)
        config_layout = QVBoxLayout(self.config_card)
        config_layout.setContentsMargins(20, 20, 20, 20)
        config_layout.setSpacing(15)

        # 1. Source & Session
        config_layout.addWidget(StrongBodyLabel("1. Web Session Configuration", self))
        
        config_layout.addWidget(BodyLabel("Source URL:", self))
        self.url_input = LineEdit(self)
        self.url_input.setPlaceholderText("Paste browser URL to extract Session ID...")
        self.url_input.textChanged.connect(self._on_url_changed)
        config_layout.addWidget(self.url_input)

        config_layout.addWidget(BodyLabel("Session ID:", self))
        self.session_id_input = LineEdit(self)
        config_layout.addWidget(self.session_id_input)

        # 2. Dealer List
        config_layout.addWidget(StrongBodyLabel("2. Dealer List Configuration", self))
        
        config_layout.addWidget(BodyLabel("Dealer List CSV File:", self))
        dealer_row = QHBoxLayout()
        self.dealer_file_input = LineEdit(self)
        self.dealer_file_input.setText(os.path.join("data", "rc_db", "dealers list.csv"))
        self.browse_dealer_btn = PushButton("Browse...", self)
        self.browse_dealer_btn.clicked.connect(self._browse_dealer_file)
        dealer_row.addWidget(self.dealer_file_input, 1)
        dealer_row.addWidget(self.browse_dealer_btn)
        config_layout.addLayout(dealer_row)

        col_row = QHBoxLayout()
        v1 = QVBoxLayout(); v1.addWidget(BodyLabel("Dealer Code Column:", self)); self.dealer_code_combo = ComboBox(self); v1.addWidget(self.dealer_code_combo)
        v2 = QVBoxLayout(); v2.addWidget(BodyLabel("Dealer Name Column:", self)); self.dealer_name_combo = ComboBox(self); v2.addWidget(self.dealer_name_combo)
        col_row.addLayout(v1); col_row.addLayout(v2)
        config_layout.addLayout(col_row)

        # 3. Caste DB
        config_layout.addWidget(StrongBodyLabel("3. Caste Database Configuration", self))
        config_layout.addWidget(BodyLabel("Caste Database CSV:", self))
        caste_row = QHBoxLayout()
        self.caste_file_input = LineEdit(self)
        self.caste_file_input.setText(os.path.join("data", "rc_db", "castedb.csv"))
        self.browse_caste_btn = PushButton("Browse...", self)
        self.browse_caste_btn.clicked.connect(lambda: self._browse_file(self.caste_file_input, "Select Caste DB"))
        caste_row.addWidget(self.caste_file_input, 1)
        caste_row.addWidget(self.browse_caste_btn)
        config_layout.addLayout(caste_row)

        # 4. Output
        config_layout.addWidget(StrongBodyLabel("4. Output Configuration", self))
        config_layout.addWidget(BodyLabel("Working Directory:", self))
        out_row = QHBoxLayout()
        self.output_dir_input = LineEdit(self)
        self.output_dir_input.setText(os.path.join("data", "rc_db"))
        self.browse_out_btn = PushButton("Browse...", self)
        self.browse_out_btn.clicked.connect(self._browse_output_dir)
        out_row.addWidget(self.output_dir_input, 1)
        out_row.addWidget(self.browse_out_btn)
        config_layout.addLayout(out_row)

        config_layout.addWidget(BodyLabel("Final DB Filename:", self))
        self.db_name_input = LineEdit(self)
        self.db_name_input.setText("final_rc_data.db")
        config_layout.addWidget(self.db_name_input)

        self.scroll_layout.addWidget(self.config_card)

        # Start Button
        self.start_btn = PrimaryPushButton("START AUTO PROCESS", self)
        self.start_btn.setFixedHeight(50)
        setFont(self.start_btn, 18, weight=QFont.Weight.Bold)
        self.start_btn.clicked.connect(self._start_pipeline)
        self.scroll_layout.addWidget(self.start_btn)

        # Logs
        self.scroll_layout.addWidget(StrongBodyLabel("Pipeline Execution Logs", self))
        self.log_area = TextEdit(self)
        self.log_area.setReadOnly(True)
        self.log_area.setPlaceholderText("Execution logs will appear here...")
        self.log_area.setMinimumHeight(300)
        self.scroll_layout.addWidget(self.log_area)

        self.scroll_area.setWidget(self.scroll_content)
        self.layout.addWidget(self.scroll_area)

        # Attempt to auto-populate headers if default file exists
        self._on_dealer_file_changed(self.dealer_file_input.text())

    def _on_url_changed(self, text):
        session_match = re.search(r'\(S\(([a-zA-Z0-9]+)\)\)', text.strip())
        if session_match:
            self.session_id_input.setText(session_match.group(1))

    def _browse_file(self, line_edit, title):
        file_path, _ = QFileDialog.getOpenFileName(self, title, "", "CSV Files (*.csv);;All Files (*)")
        if file_path: line_edit.setText(file_path)

    def _browse_dealer_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Dealer List", "", "CSV Files (*.csv)")
        if file_path:
            self.dealer_file_input.setText(file_path)
            self._on_dealer_file_changed(file_path)

    def _on_dealer_file_changed(self, file_path):
        if not os.path.exists(file_path): return
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames
                if headers:
                    self.dealer_code_combo.clear(); self.dealer_code_combo.addItems(headers)
                    self.dealer_name_combo.clear(); self.dealer_name_combo.addItems(headers)
                    if "Code" in headers: self.dealer_code_combo.setCurrentText("Code")
                    if "Name" in headers: self.dealer_name_combo.setCurrentText("Name")
        except: pass

    def _browse_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if dir_path: self.output_dir_input.setText(dir_path)

    def append_log(self, message):
        self.log_area.append(message)
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())

    def _start_pipeline(self):
        config = {
            'dealer_list_file': self.dealer_file_input.text(),
            'dealer_code_col': self.dealer_code_combo.currentText(),
            'dealer_name_col': self.dealer_name_combo.currentText(),
            'caste_db_file': self.caste_file_input.text(),
            'session_id': self.session_id_input.text(),
            'output_dir': self.output_dir_input.text(),
            'final_db_name': self.db_name_input.text()
        }

        if not all(config.values()):
            InfoBar.error("Missing Fields", "Please ensure all configuration fields are filled.", 
                          parent=self.window(), position=InfoBarPosition.TOP)
            return

        self.start_btn.setEnabled(False)
        self.log_area.clear()
        self.append_log(f"[*] Pipeline initialized at {pd.Timestamp.now()}")

        def run():
            try:
                manager = PipelineManager()
                success, msg = manager.run_pipeline(config, progress_callback=self.append_log)
                if success:
                    InfoBar.success("Success", "Auto Process completed successfully!", parent=self.window())
                else:
                    InfoBar.error("Pipeline Failed", msg, parent=self.window())
            except Exception as e:
                self.append_log(f"[CRITICAL] {e}")
            finally:
                self.start_btn.setEnabled(True)

        threading.Thread(target=run, daemon=True).start()

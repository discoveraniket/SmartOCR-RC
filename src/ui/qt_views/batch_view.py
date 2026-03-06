import os
import time
import logging
import threading
from pathlib import Path
from PySide6.QtCore import Qt, Signal, QObject, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QFrame, QScrollArea
from qfluentwidgets import (SubtitleLabel, setFont, CardWidget, StrongBodyLabel, 
                            BodyLabel, LineEdit, PushButton, PrimaryPushButton, 
                            InfoBar, InfoBarPosition, TextEdit, ComboBox, 
                            ProgressBar, CheckBox, TransparentPushButton, FluentIcon as FIF)

from src.core.batch_processor import BatchProcessor
from src.utils.config import OCR_SETTINGS

class QPlainTextEditLogger(logging.Handler):
    def __init__(self, parent):
        super().__init__()
        self.widget = parent

    def emit(self, record):
        msg = self.format(record)
        self.widget.append_log_signal.emit(msg)

class LogBridge(QObject):
    append_log_signal = Signal(str)

class BatchView(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("batch-view")
        
        self.processor = None
        self.log_bridge = LogBridge()
        self.log_bridge.append_log_signal.connect(self._append_log)
        
        self._setup_logging()
        self._setup_ui()

    def _setup_logging(self):
        self.log_handler = QPlainTextEditLogger(self.log_bridge)
        self.log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%H:%M:%S'))
        logging.getLogger().addHandler(self.log_handler)
        logging.getLogger().setLevel(logging.INFO)

    def _setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("background: transparent;")
        
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(40, 40, 40, 40)
        self.scroll_layout.setSpacing(25)

        # Header
        self.title = SubtitleLabel("Overnight Batch Processing", self)
        setFont(self.title, 28)
        self.scroll_layout.addWidget(self.title)

        # 1. Configuration Card
        self.config_card = CardWidget(self)
        config_layout = QVBoxLayout(self.config_card)
        config_layout.setContentsMargins(20, 20, 20, 20)
        config_layout.setSpacing(15)

        config_layout.addWidget(StrongBodyLabel("Session Configuration", self))

        # Input
        config_layout.addWidget(BodyLabel("Input Directory:", self))
        in_row = QHBoxLayout()
        self.input_input = LineEdit(self)
        self.input_input.setText(OCR_SETTINGS.get("default_input_dir", "data"))
        self.browse_in_btn = PushButton("Browse...", self)
        self.browse_in_btn.clicked.connect(self._browse_input)
        in_row.addWidget(self.input_input, 1)
        in_row.addWidget(self.browse_in_btn)
        config_layout.addLayout(in_row)

        # Output
        config_layout.addWidget(BodyLabel("Output Directory:", self))
        out_row = QHBoxLayout()
        self.output_input = LineEdit(self)
        self.output_input.setText(OCR_SETTINGS.get("default_output_dir", "output"))
        self.browse_out_btn = PushButton("Browse...", self)
        self.browse_out_btn.clicked.connect(self._browse_output)
        out_row.addWidget(self.output_input, 1)
        out_row.addWidget(self.browse_out_btn)
        config_layout.addLayout(out_row)

        # Options
        opts_row = QHBoxLayout()
        self.recursive_check = CheckBox("Recursive Search", self)
        self.recursive_check.setChecked(True)
        self.retry_check = CheckBox("Auto-retry errors", self)
        self.retry_check.setChecked(True)
        opts_row.addWidget(self.recursive_check)
        opts_row.addWidget(self.retry_check)
        opts_row.addStretch(1)
        config_layout.addLayout(opts_row)

        # Post Action
        config_layout.addWidget(BodyLabel("Post-Process Action:", self))
        self.post_action_combo = ComboBox(self)
        self.post_action_combo.addItems(["None", "Shutdown", "Sleep"])
        self.post_action_combo.setCurrentText("None")
        config_layout.addWidget(self.post_action_combo)

        self.scroll_layout.addWidget(self.config_card)

        # 2. Progress Card
        self.progress_card = CardWidget(self)
        progress_layout = QVBoxLayout(self.progress_card)
        progress_layout.setContentsMargins(20, 20, 20, 20)
        progress_layout.setSpacing(15)

        progress_layout.addWidget(StrongBodyLabel("Live Progress & Metrics", self))

        self.progress_bar = ProgressBar(self)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)

        self.stats_label = BodyLabel("Total: 0 | Processed: 0 | Remaining: 0 | Errors: 0", self)
        progress_layout.addWidget(self.stats_label)

        self.eta_label = BodyLabel("ETA: --:--:-- | Elapsed: 00:00:00", self)
        progress_layout.addWidget(self.eta_label)

        self.speed_label = BodyLabel("OCR (Det: --s | Rec: --s) | Model1: --s | JSON: --s", self)
        self.speed_label.setStyleSheet("font-weight: bold; color: #0078d4;")
        progress_layout.addWidget(self.speed_label)

        self.current_file_label = BodyLabel("Current: Waiting...", self)
        self.current_file_label.setStyleSheet("font-style: italic; color: gray;")
        progress_layout.addWidget(self.current_file_label)

        self.scroll_layout.addWidget(self.progress_card)

        # Controls
        ctrl_row = QHBoxLayout()
        self.start_btn = PrimaryPushButton("Start Batch Session", self)
        self.start_btn.setFixedHeight(40)
        self.start_btn.clicked.connect(self._start_session)
        
        self.stop_btn = PushButton("Stop Session", self)
        self.stop_btn.setFixedHeight(40)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_session)
        
        ctrl_row.addWidget(self.start_btn)
        ctrl_row.addWidget(self.stop_btn)
        self.scroll_layout.addLayout(ctrl_row)

        # Logs
        self.scroll_layout.addWidget(StrongBodyLabel("Session Logs", self))
        self.log_area = TextEdit(self)
        self.log_area.setReadOnly(True)
        self.log_area.setPlaceholderText("Logs will appear here...")
        self.log_area.setMinimumHeight(250)
        self.scroll_layout.addWidget(self.log_area)

        self.scroll_area.setWidget(self.scroll_content)
        self.layout.addWidget(self.scroll_area)

    def _browse_input(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Input Directory", self.input_input.text())
        if dir_path: self.input_input.setText(dir_path)

    def _browse_output(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Output Directory", self.output_input.text())
        if dir_path: self.output_input.setText(dir_path)

    def _append_log(self, message):
        self.log_area.append(message)
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())

    def _format_time(self, seconds):
        if seconds < 0: return "--:--:--"
        return time.strftime('%H:%M:%S', time.gmtime(seconds))

    def _update_ui(self, stats, current_file=None, last_speeds=None):
        self.progress_bar.setValue(int(stats["progress"] * 100))
        self.stats_label.setText(f"Total: {stats['total']} | Processed: {stats['processed']} | Remaining: {stats['remaining']} | Errors: {stats['errors']}")
        
        eta_str = self._format_time(stats["eta"])
        elapsed_str = self._format_time(stats["elapsed"])
        self.eta_label.setText(f"ETA: {eta_str} | Elapsed: {elapsed_str}")
        
        if last_speeds:
            det = last_speeds.get('ocr_det', '--')
            rec = last_speeds.get('ocr_rec', '--')
            m1 = last_speeds.get('step1', '--')
            json_speed = last_speeds.get('json', '--')
            self.speed_label.setText(f"OCR (Det: {det}s | Rec: {rec}s) | Model1: {m1}s | JSON: {json_speed}s")
            
        if current_file:
            self.current_file_label.setText(f"Current: {current_file}")

    def _start_session(self):
        # Basic readiness check
        from src.core.ocr_engine import OcrEngine
        from src.core.llm_engine import LlmInferenceEngine
        
        ocr = OcrEngine(show_log=False)
        if not ocr.is_ready():
            InfoBar.error("Dependency Error", "OCR Engine is not ready.", parent=self.window())
            return
            
        input_dir = self.input_input.text()
        output_dir = self.output_input.text()
        
        if not os.path.exists(input_dir):
            InfoBar.error("Error", "Input directory does not exist.", parent=self.window())
            return

        self.processor = BatchProcessor(
            input_dir, 
            output_dir, 
            recursive=self.recursive_check.isChecked(),
            auto_retry=self.retry_check.isChecked(),
            post_action=self.post_action_combo.currentText()
        )
        
        # UI State
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.input_input.setEnabled(False)
        self.output_input.setEnabled(False)
        self.browse_in_btn.setEnabled(False)
        self.browse_out_btn.setEnabled(False)
        self.recursive_check.setEnabled(False)
        self.retry_check.setEnabled(False)
        self.post_action_combo.setEnabled(False)
        
        self.log_area.clear()
        logging.info("--- Starting Batch Session ---")
        
        def on_complete(stats):
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.input_input.setEnabled(True)
            self.output_input.setEnabled(True)
            self.browse_in_btn.setEnabled(True)
            self.browse_out_btn.setEnabled(True)
            self.recursive_check.setEnabled(True)
            self.retry_check.setEnabled(True)
            self.post_action_combo.setEnabled(True)
            
            logging.info(f"--- Session Finished ---")
            InfoBar.success("Session Complete", "Batch processing has finished.", parent=self.window())

        self.processor.start(progress_callback=self._update_ui, completion_callback=on_complete)

    def _stop_session(self):
        if self.processor:
            self.processor.stop()
            logging.info("!!! Stop Requested - Waiting for current item to finish !!!")
            self.stop_btn.setEnabled(False)

    def __del__(self):
        # Clean up logging handler
        if hasattr(self, 'log_handler'):
            logging.getLogger().removeHandler(self.log_handler)

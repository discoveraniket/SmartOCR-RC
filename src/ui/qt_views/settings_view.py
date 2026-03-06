import os
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QFileDialog, 
                                 QScrollArea, QWidget, QSpacerItem, QSizePolicy)
from qfluentwidgets import (SubtitleLabel, setFont, CardWidget, StrongBodyLabel, 
                            BodyLabel, LineEdit, PushButton, PrimaryPushButton, 
                            InfoBar, InfoBarPosition, SwitchButton, SpinBox, 
                            DoubleSpinBox, ComboBox, PlainTextEdit, FluentIcon as FIF)

from src.utils.config import OCR_SETTINGS, LLM_SETTINGS, save_config, FACTORY_DEFAULTS

class SettingGroup(CardWidget):
    """A card to group related settings"""
    def __init__(self, title: str, parent=None):
        super().__init__(parent=parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)
        
        self.title_label = StrongBodyLabel(title, self)
        setFont(self.title_label, 18)
        self.layout.addWidget(self.title_label)
        
        # Separator-ish
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: rgba(0, 0, 0, 0.1);")
        self.layout.addWidget(line)

    def add_setting(self, label: str, widget: QWidget, description: str = None):
        row_layout = QHBoxLayout()
        
        text_layout = QVBoxLayout()
        lbl = BodyLabel(label, self)
        setFont(lbl, 14)
        text_layout.addWidget(lbl)
        
        if description:
            desc = BodyLabel(description, self)
            desc.setStyleSheet("color: gray;")
            setFont(desc, 12)
            text_layout.addWidget(desc)
            
        row_layout.addLayout(text_layout)
        row_layout.addStretch(1)
        row_layout.addWidget(widget)
        
        self.layout.addLayout(row_layout)

class SettingsView(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("settings-view")
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.layout = QVBoxLayout(self.scroll_content)
        self.layout.setContentsMargins(40, 40, 40, 40)
        self.layout.setSpacing(25)
        
        self.setWidget(self.scroll_content)
        
        self._setup_ui()
        self.load_settings()

    def _setup_ui(self):
        # Header
        header_layout = QHBoxLayout()
        self.title = SubtitleLabel("Configuration Settings", self.scroll_content)
        setFont(self.title, 28)
        header_layout.addWidget(self.title)
        header_layout.addStretch(1)
        self.layout.addLayout(header_layout)

        # 1. Directories
        self.dir_group = SettingGroup("Paths & Directories", self.scroll_content)
        
        self.input_dir_edit = LineEdit(self.scroll_content)
        self.input_dir_edit.setFixedWidth(400)
        self.input_dir_btn = PushButton("Browse", self.scroll_content)
        self.input_dir_btn.clicked.connect(lambda: self.browse_dir(self.input_dir_edit))
        input_layout = QHBoxLayout()
        input_layout.addWidget(self.input_dir_edit)
        input_layout.addWidget(self.input_dir_btn)
        input_widget = QWidget()
        input_widget.setLayout(input_layout)
        self.dir_group.add_setting("Default Input Directory", input_widget, "Where to look for images by default.")

        self.output_dir_edit = LineEdit(self.scroll_content)
        self.output_dir_edit.setFixedWidth(400)
        self.output_dir_btn = PushButton("Browse", self.scroll_content)
        self.output_dir_btn.clicked.connect(lambda: self.browse_dir(self.output_dir_edit))
        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_dir_edit)
        output_layout.addWidget(self.output_dir_btn)
        output_widget = QWidget()
        output_widget.setLayout(output_layout)
        self.dir_group.add_setting("Default Output Directory", output_widget, "Where to save results.")
        
        self.layout.addWidget(self.dir_group)

        # 2. OCR Engine
        self.ocr_group = SettingGroup("OCR Engine (PaddleOCR)", self.scroll_content)
        
        self.ocr_lang_edit = LineEdit(self.scroll_content)
        self.ocr_lang_edit.setFixedWidth(100)
        self.ocr_group.add_setting("Language", self.ocr_lang_edit, "OCR language code (e.g. 'en', 'ch', 'hi')")
        
        self.use_gpu_switch = SwitchButton(self.scroll_content)
        self.ocr_group.add_setting("Use GPU", self.use_gpu_switch, "Use NVIDIA GPU if available.")
        
        self.use_angle_cls_switch = SwitchButton(self.scroll_content)
        self.ocr_group.add_setting("Angle Classification", self.use_angle_cls_switch, "Enable to detect rotated text.")

        self.ocr_version_combo = ComboBox(self.scroll_content)
        self.ocr_version_combo.addItems(["PP-OCRv4", "PP-OCRv3"])
        self.ocr_version_combo.setFixedWidth(150)
        self.ocr_group.add_setting("OCR Model Version", self.ocr_version_combo)
        
        self.cpu_threads_spin = SpinBox(self.scroll_content)
        self.cpu_threads_spin.setRange(1, 64)
        self.ocr_group.add_setting("CPU Threads", self.cpu_threads_spin, "Number of threads for processing.")

        self.mkldnn_switch = SwitchButton(self.scroll_content)
        self.ocr_group.add_setting("Enable MKLDNN", self.mkldnn_switch, "Use Intel MKLDNN for faster CPU inference.")

        self.layout.addWidget(self.ocr_group)

        # 3. Advanced OCR Parameters
        self.adv_ocr_group = SettingGroup("Advanced OCR Parameters", self.scroll_content)
        
        self.det_thresh_spin = DoubleSpinBox(self.scroll_content)
        self.det_thresh_spin.setRange(0.0, 1.0)
        self.det_thresh_spin.setSingleStep(0.1)
        self.adv_ocr_group.add_setting("Detection Threshold", self.det_thresh_spin, "Threshold for text detection.")
        
        self.box_thresh_spin = DoubleSpinBox(self.scroll_content)
        self.box_thresh_spin.setRange(0.0, 1.0)
        self.box_thresh_spin.setSingleStep(0.1)
        self.adv_ocr_group.add_setting("Box Threshold", self.box_thresh_spin, "Threshold for text box filtering.")

        self.auto_crop_switch = SwitchButton(self.scroll_content)
        self.adv_ocr_group.add_setting("Auto Crop", self.auto_crop_switch, "Automatically crop to detected text regions.")
        
        self.crop_padding_spin = SpinBox(self.scroll_content)
        self.crop_padding_spin.setRange(0, 100)
        self.adv_ocr_group.add_setting("Crop Padding", self.crop_padding_spin, "Padding around cropped text (px).")

        self.layout.addWidget(self.adv_ocr_group)

        # 4. LLM Service
        self.llm_group = SettingGroup("LLM Service (Ollama)", self.scroll_content)
        
        self.llm_path_edit = LineEdit(self.scroll_content)
        self.llm_path_edit.setFixedWidth(400)
        self.llm_path_btn = PushButton("Browse", self.scroll_content)
        self.llm_path_btn.clicked.connect(lambda: self.browse_dir(self.llm_path_edit))
        llm_path_layout = QHBoxLayout()
        llm_path_layout.addWidget(self.llm_path_edit)
        llm_path_layout.addWidget(self.llm_path_btn)
        llm_path_widget = QWidget()
        llm_path_widget.setLayout(llm_path_layout)
        self.llm_group.add_setting("Models Path", llm_path_widget, "Path where Ollama models are stored.")

        self.step1_model_combo = ComboBox(self.scroll_content)
        self.step1_model_combo.addItems(LLM_SETTINGS.get("available_models", []))
        self.step1_model_combo.setFixedWidth(250)
        self.llm_group.add_setting("Step 1 Model (Cleaning)", self.step1_model_combo)
        
        self.json_model_combo = ComboBox(self.scroll_content)
        self.json_model_combo.addItems(LLM_SETTINGS.get("available_models", []))
        self.json_model_combo.setFixedWidth(250)
        self.llm_group.add_setting("JSON Extraction Model", self.json_model_combo)

        self.keep_alive_edit = LineEdit(self.scroll_content)
        self.keep_alive_edit.setFixedWidth(100)
        self.llm_group.add_setting("Keep Alive", self.keep_alive_edit, "Duration models stay in memory (e.g. '5m', '1h')")

        self.layout.addWidget(self.llm_group)

        # Actions
        actions_layout = QHBoxLayout()
        self.save_btn = PrimaryPushButton("Save Settings", self.scroll_content)
        self.save_btn.clicked.connect(self.save_all)
        self.save_btn.setFixedWidth(180)
        self.save_btn.setFixedHeight(40)
        
        self.revert_btn = PushButton("Revert to Defaults", self.scroll_content)
        self.revert_btn.clicked.connect(self.revert_defaults)
        self.revert_btn.setFixedWidth(180)
        self.revert_btn.setFixedHeight(40)
        
        actions_layout.addWidget(self.save_btn)
        actions_layout.addWidget(self.revert_btn)
        actions_layout.addStretch(1)
        self.layout.addLayout(actions_layout)
        
        self.layout.addStretch(1)

    def browse_dir(self, line_edit):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Directory", line_edit.text())
        if dir_path:
            line_edit.setText(dir_path)

    def load_settings(self):
        # OCR
        self.input_dir_edit.setText(OCR_SETTINGS.get("default_input_dir", ""))
        self.output_dir_edit.setText(OCR_SETTINGS.get("default_output_dir", ""))
        self.ocr_lang_edit.setText(OCR_SETTINGS.get("lang", "en"))
        self.use_gpu_switch.setChecked(OCR_SETTINGS.get("use_gpu", False))
        self.use_angle_cls_switch.setChecked(OCR_SETTINGS.get("use_angle_cls", True))
        self.ocr_version_combo.setCurrentText(OCR_SETTINGS.get("ocr_version", "PP-OCRv4"))
        self.cpu_threads_spin.setValue(OCR_SETTINGS.get("cpu_threads", 4))
        self.mkldnn_switch.setChecked(OCR_SETTINGS.get("enable_mkldnn", True))
        
        self.det_thresh_spin.setValue(OCR_SETTINGS.get("det_db_thresh", 0.3))
        self.box_thresh_spin.setValue(OCR_SETTINGS.get("det_db_box_thresh", 0.5))
        self.auto_crop_switch.setChecked(OCR_SETTINGS.get("auto_crop", True))
        self.crop_padding_spin.setValue(OCR_SETTINGS.get("crop_padding", 10))
        
        # LLM
        self.llm_path_edit.setText(LLM_SETTINGS.get("models_path", ""))
        self.step1_model_combo.setCurrentText(LLM_SETTINGS.get("step1_model", ""))
        self.json_model_combo.setCurrentText(LLM_SETTINGS.get("text_to_JSON_model", ""))
        self.keep_alive_edit.setText(LLM_SETTINGS.get("keep_alive", "5m"))

    def save_all(self):
        new_ocr = OCR_SETTINGS.copy()
        new_ocr.update({
            "default_input_dir": self.input_dir_edit.text(),
            "default_output_dir": self.output_dir_edit.text(),
            "lang": self.ocr_lang_edit.text(),
            "use_gpu": self.use_gpu_switch.isChecked(),
            "use_angle_cls": self.use_angle_cls_switch.isChecked(),
            "ocr_version": self.ocr_version_combo.currentText(),
            "cpu_threads": self.cpu_threads_spin.value(),
            "enable_mkldnn": self.mkldnn_switch.isChecked(),
            "det_db_thresh": self.det_thresh_spin.value(),
            "det_db_box_thresh": self.box_thresh_spin.value(),
            "auto_crop": self.auto_crop_switch.isChecked(),
            "crop_padding": self.crop_padding_spin.value()
        })
        
        new_llm = LLM_SETTINGS.copy()
        new_llm.update({
            "models_path": self.llm_path_edit.text(),
            "step1_model": self.step1_model_combo.currentText(),
            "text_to_JSON_model": self.json_model_combo.currentText(),
            "keep_alive": self.keep_alive_edit.text()
        })
        
        save_config(new_ocr, new_llm)
        
        # Update global instances immediately
        OCR_SETTINGS.update(new_ocr)
        LLM_SETTINGS.update(new_llm)
        
        InfoBar.success("Success", "Settings saved successfully", parent=self.window(), duration=2000)

    def revert_defaults(self):
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(self, "Confirm", "Revert all settings to factory defaults?", 
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            OCR_SETTINGS.update(FACTORY_DEFAULTS["OCR_SETTINGS"])
            LLM_SETTINGS.update(FACTORY_DEFAULTS["LLM_SETTINGS"])
            self.load_settings()
            InfoBar.warning("Reverted", "Settings reverted to defaults. Don't forget to save.", 
                            parent=self.window(), duration=3000)

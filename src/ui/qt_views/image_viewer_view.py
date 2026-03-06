import os
import logging
from pathlib import Path
from typing import Optional, Dict

from PySide6.QtCore import Qt, QSize, QPointF, Signal, Slot
from PySide6.QtGui import QPixmap, QPainter, QWheelEvent, QMouseEvent, QImage, QShortcut, QKeySequence
from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QGraphicsView, 
                             QGraphicsScene, QGraphicsPixmapItem, QFileDialog,
                             QScrollArea, QSizePolicy, QSplitter)

from qfluentwidgets import (SubtitleLabel, setFont, CaptionLabel, PushButton, 
                            PrimaryPushButton, ToolButton, TransparentPushButton,
                            FluentIcon as FIF, InfoBar, InfoBarPosition, CardWidget,
                            LineEdit, StrongBodyLabel, BodyLabel, ScrollArea,
                            SmoothScrollArea)

from src.core.result_handler import ResultDataHandler
from src.core.coordinator import PipelineCoordinator
from src.utils.config import OCR_SETTINGS, LLM_SETTINGS, KEY_MAP, save_config
from src.utils.threading import run_in_background
from src.utils.image_processing import ImageProcessingService
from PIL import Image

logger = logging.getLogger(__name__)

class GraphicsImageViewer(QGraphicsView):
    """A custom graphics view for displaying images with zoom and pan."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        self.pixmap_item = QGraphicsPixmapItem()
        self.pixmap_item.setTransformationMode(Qt.SmoothTransformation)
        self.scene.addItem(self.pixmap_item)
        
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setBackgroundBrush(Qt.black)
        self.setFrameShape(QFrame.NoFrame)
        
        self._zoom = 0
        self._empty = True

    def has_image(self):
        return not self._empty

    def set_pixmap(self, pixmap: QPixmap):
        self._empty = False
        self.pixmap_item.setPixmap(pixmap)
        self.scene.setSceneRect(self.pixmap_item.boundingRect())
        self.fit_in_view()

    def fit_in_view(self):
        rect = self.pixmap_item.boundingRect()
        if not rect.isNull():
            self.setSceneRect(rect)
            self.fitInView(rect, Qt.KeepAspectRatio)
            self._zoom = 0

    def wheelEvent(self, event: QWheelEvent):
        if self.has_image():
            if event.angleDelta().y() > 0:
                factor = 1.25
                self._zoom += 1
            else:
                factor = 0.8
                self._zoom -= 1
            
            if self._zoom > 10:
                self._zoom = 10
            elif self._zoom < -10:
                self._zoom = -10
                factor = 1.0
            
            if factor != 1.0:
                self.scale(factor, factor)

class ImageViewerView(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("image-viewer-view")
        
        # Data and Services
        project_root = Path(__file__).parents[3]
        self.output_dir = project_root / OCR_SETTINGS.get("default_output_dir", "output")
        self.handler = ResultDataHandler(str(self.output_dir / "results.csv"), str(self.output_dir))
        
        try:
            self.coordinator = PipelineCoordinator(output_dir=str(self.output_dir))
        except Exception as e:
            logger.error(f"Failed to initialize Pipeline Coordinator: {e}")
            self.coordinator = None
            
        self.model_overrides = {
            "step1_model": LLM_SETTINGS.get("step1_model"),
            "text_to_JSON_model": LLM_SETTINGS.get("text_to_JSON_model"),
            "think": False
        }

        self.entries = {}
        self._setup_ui()
        self._setup_shortcuts()
        
        # Load first item
        self.refresh_view()

    def _setup_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Main Splitter
        self.splitter = QSplitter(Qt.Horizontal)
        
        # --- LEFT SIDE: Viewport ---
        self.viewport_container = QFrame()
        self.viewport_layout = QVBoxLayout(self.viewport_container)
        self.viewport_layout.setContentsMargins(15, 15, 15, 15)
        
        # Graphics View
        self.viewer = GraphicsImageViewer(self.viewport_container)
        self.viewport_layout.addWidget(self.viewer, 1)
        
        # Combined Bottom Toolbar
        self.bottom_bar = QFrame()
        self.bottom_bar_layout = QHBoxLayout(self.bottom_bar)
        self.bottom_bar_layout.setContentsMargins(0, 15, 0, 0)
        self.bottom_bar_layout.setSpacing(10)
        
        # Helper to create squared PushButtons with centered icons
        def create_icon_btn(icon, tooltip, parent, size=36, icon_size=18):
            btn = PushButton(icon, "", parent)
            btn.setToolTip(tooltip)
            btn.setFixedSize(size, size)
            btn.setIconSize(QSize(icon_size, icon_size))
            setFont(btn, 14)
            return btn

        # Navigation Group (Left)
        self.prev_btn = create_icon_btn(FIF.LEFT_ARROW, "Previous Item (Ctrl+Left)", self.bottom_bar)
        self.prev_btn.clicked.connect(self.prev_item)
        
        self.counter_label = StrongBodyLabel("0 / 0", self.bottom_bar)
        self.counter_label.setFixedWidth(70)
        self.counter_label.setAlignment(Qt.AlignCenter)
        setFont(self.counter_label, 14)
        
        self.next_btn = create_icon_btn(FIF.RIGHT_ARROW, "Next Item (Ctrl+Right)", self.bottom_bar)
        self.next_btn.clicked.connect(self.next_item)
        
        # Info Group (Middle)
        self.filename_label = BodyLabel("No File Selected", self.bottom_bar)
        self.filename_label.setContentsMargins(10, 0, 10, 0)
        setFont(self.filename_label, 14)
        
        self.browse_dir_btn = create_icon_btn(FIF.FOLDER, f"Open output directory: {self.output_dir.name}", self.bottom_bar)
        self.browse_dir_btn.clicked.connect(self.browse_output_dir)
        
        # Tools Group (Right)
        self.rotate_btn = create_icon_btn(FIF.SYNC, "Rotate -90° (Ctrl+R)", self.bottom_bar)
        self.rotate_btn.clicked.connect(self.rotate_image)
        
        self.crop_btn = create_icon_btn(FIF.EDIT, "Auto-Crop Text (Ctrl+C)", self.bottom_bar)
        self.crop_btn.clicked.connect(self.auto_crop)
        
        self.reset_zoom_btn = create_icon_btn(FIF.ZOOM, "Reset Zoom (Ctrl+0)", self.bottom_bar)
        self.reset_zoom_btn.clicked.connect(self.viewer.fit_in_view)
        
        self.save_img_btn = create_icon_btn(FIF.SAVE, "Save Image (Ctrl+I)", self.bottom_bar)
        self.save_img_btn.clicked.connect(self.save_current_image)
        
        # Add to Layout
        self.bottom_bar_layout.addWidget(self.prev_btn)
        self.bottom_bar_layout.addWidget(self.counter_label)
        self.bottom_bar_layout.addWidget(self.next_btn)
        
        self.bottom_bar_layout.addSpacing(20)
        self.bottom_bar_layout.addWidget(self.filename_label, 1)
        self.bottom_bar_layout.addWidget(self.browse_dir_btn)
        self.bottom_bar_layout.addSpacing(20)
        
        self.bottom_bar_layout.addWidget(self.rotate_btn)
        self.bottom_bar_layout.addWidget(self.crop_btn)
        self.bottom_bar_layout.addWidget(self.reset_zoom_btn)
        self.bottom_bar_layout.addWidget(self.save_img_btn)
        
        self.viewport_layout.addWidget(self.bottom_bar)
        
        # --- RIGHT SIDE: Data Panel ---
        self.side_panel = QFrame()
        self.side_panel.setFixedWidth(420)
        self.side_panel_layout = QVBoxLayout(self.side_panel)
        self.side_panel_layout.setContentsMargins(15, 15, 15, 15)
        self.side_panel_layout.setSpacing(20)
        
        # Header
        self.side_header_layout = QHBoxLayout()
        self.side_title = SubtitleLabel("Extraction Data")
        setFont(self.side_title, 20)
        self.side_header_layout.addWidget(self.side_title)
        
        # Font size controls
        self.font_ctrl_layout = QHBoxLayout()
        self.font_ctrl_layout.setSpacing(2)
        
        self.font_up_btn = create_icon_btn(FIF.ADD, "Increase Font Size", self.side_panel, size=32, icon_size=16)
        self.font_up_btn.clicked.connect(lambda: self.change_font_size(2))
        
        self.font_down_btn = create_icon_btn(FIF.REMOVE, "Decrease Font Size", self.side_panel, size=32, icon_size=16)
        self.font_down_btn.clicked.connect(lambda: self.change_font_size(-2))
        
        self.font_ctrl_layout.addWidget(self.font_down_btn)
        self.font_ctrl_layout.addWidget(self.font_up_btn)
        self.side_header_layout.addLayout(self.font_ctrl_layout)
        
        self.settings_btn = create_icon_btn(FIF.SETTING, "Session Settings", self.side_panel, size=32, icon_size=16)
        self.settings_btn.clicked.connect(self.open_settings)
        self.side_header_layout.addWidget(self.settings_btn)
        
        self.side_panel_layout.addLayout(self.side_header_layout)
        
        # Fields Scroll Area
        self.scroll_area = SmoothScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.fields_widget = QFrame()
        self.fields_layout = QVBoxLayout(self.fields_widget)
        self.fields_layout.setAlignment(Qt.AlignTop)
        self.scroll_area.setWidget(self.fields_widget)
        
        self.side_panel_layout.addWidget(self.scroll_area, 1)
        
        # Actions
        self.save_data_btn = PrimaryPushButton("Save Changes", self.side_panel)
        self.save_data_btn.setFixedHeight(45)
        self.save_data_btn.clicked.connect(self.save_edits)
        setFont(self.save_data_btn, 16)
        self.side_panel_layout.addWidget(self.save_data_btn)
        
        self.secondary_actions_layout = QHBoxLayout()
        self.secondary_actions_layout.setSpacing(10)
        
        self.reprocess_btn = PushButton(FIF.SYNC, "AI Re-process", self.side_panel)
        self.reprocess_btn.setFixedHeight(35)
        self.reprocess_btn.clicked.connect(self.reprocess_image)
        setFont(self.reprocess_btn, 14)
        
        self.log_btn = PushButton(FIF.DOCUMENT, "Log", self.side_panel)
        self.log_btn.setFixedWidth(80)
        self.log_btn.setFixedHeight(35)
        self.log_btn.clicked.connect(self.view_log)
        setFont(self.log_btn, 14)
        
        self.delete_btn = create_icon_btn(FIF.DELETE, "Delete Item", self.side_panel, size=45, icon_size=18)
        self.delete_btn.setFixedHeight(35)
        # Subtle red for delete
        self.delete_btn.setStyleSheet("""
            PushButton {
                background-color: rgba(255, 68, 68, 0.1);
                border: 1px solid rgba(255, 68, 68, 0.2);
            }
            PushButton:hover {
                background-color: rgba(255, 68, 68, 0.2);
                border: 1px solid rgba(255, 68, 68, 0.4);
            }
        """)
        self.delete_btn.clicked.connect(self.delete_current_item)
        
        self.secondary_actions_layout.addWidget(self.reprocess_btn, 1)
        self.secondary_actions_layout.addWidget(self.log_btn)
        self.secondary_actions_layout.addWidget(self.delete_btn)
        self.side_panel_layout.addLayout(self.secondary_actions_layout)
        
        # Metrics
        self.metrics_label = CaptionLabel("", self.side_panel)
        self.metrics_label.setStyleSheet("color: #888888;")
        setFont(self.metrics_label, 12)
        self.side_panel_layout.addWidget(self.metrics_label)

        # Add to splitter
        self.splitter.addWidget(self.viewport_container)
        self.splitter.addWidget(self.side_panel)
        self.splitter.setStretchFactor(0, 4)
        self.splitter.setStretchFactor(1, 1)
        
        self.main_layout.addWidget(self.splitter)

    def _setup_shortcuts(self):
        """Map keyboard shortcuts based on KEY_MAP configuration."""
        def map_key(key_str):
            # Convert <Control-Right> to Ctrl+Right
            return key_str.replace("<", "").replace(">", "").replace("-", "+")

        shortcuts = [
            (KEY_MAP["viewer_next"], self.next_item),
            (KEY_MAP["viewer_prev"], self.prev_item),
            (KEY_MAP["viewer_save_data"], self.save_edits),
            (KEY_MAP["viewer_rotate"], self.rotate_image),
            (KEY_MAP["viewer_crop"], self.auto_crop),
            (KEY_MAP["viewer_reprocess"], self.reprocess_image),
            (KEY_MAP["viewer_view_log"], self.view_log),
            (KEY_MAP["viewer_reset"], self.viewer.fit_in_view)
        ]

        for key_str, slot in shortcuts:
            seq = QKeySequence(map_key(key_str))
            shortcut = QShortcut(seq, self)
            shortcut.activated.connect(slot)

    def change_font_size(self, delta: int):
        """Adjusts the text size in the entry fields centrally."""
        current_size = OCR_SETTINGS.get("viewer_font_size", 14)
        new_size = max(8, min(40, current_size + delta))
        OCR_SETTINGS["viewer_font_size"] = new_size
        save_config(OCR_SETTINGS, LLM_SETTINGS)
        
        # Apply to current entries
        for entry in self.entries.values():
            setFont(entry, new_size)
            # Adjust height if size is large
            if new_size > 18:
                entry.setFixedHeight(new_size + 15)
            else:
                entry.setFixedHeight(33)

    def refresh_view(self):
        item = self.handler.get_current_item()
        if not item:
            self.counter_label.setText("0 / 0")
            self.filename_label.setText("No results found")
            return
            
        total = len(self.handler.results)
        current = self.handler.current_index + 1
        self.counter_label.setText(f"{current} / {total}")
        self.handler.save_last_index()

        image_name = item.get('processed_image_name', 'Unknown')
        self.filename_label.setText(image_name)
        
        img_path = self.handler.get_image_path(item)
        if img_path and os.path.exists(img_path):
            pixmap = QPixmap(img_path)
            if not pixmap.isNull():
                self.viewer.set_pixmap(pixmap)
            else:
                logger.error(f"Failed to load image pixmap: {img_path}")
        
        self._refresh_data_fields(item)

    def _refresh_data_fields(self, item):
        # Clear existing
        for i in reversed(range(self.fields_layout.count())):
            widget = self.fields_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
            
        self.entries = {}
        font_size = OCR_SETTINGS.get("viewer_font_size", 14)
        
        for key, value in item.items():
            if key == "processed_image_name": continue
            
            field_container = QFrame()
            field_vbox = QVBoxLayout(field_container)
            field_vbox.setContentsMargins(0, 5, 0, 5)
            field_vbox.setSpacing(2)
            
            label = CaptionLabel(key.upper())
            label.setStyleSheet("color: #888888; font-weight: bold;")
            setFont(label, 12)
            field_vbox.addWidget(label)
            
            entry = LineEdit()
            entry.setText(str(value))
            setFont(entry, font_size)
            if font_size > 18:
                entry.setFixedHeight(font_size + 15)
            field_vbox.addWidget(entry)
            
            self.fields_layout.addWidget(field_container)
            self.entries[key] = entry
            
        # Focus the first field if available
        if "category" in self.entries:
            self.entries["category"].setFocus()

    def next_item(self):
        if self.handler.next_item():
            self.refresh_view()

    def prev_item(self):
        if self.handler.prev_item():
            self.refresh_view()

    def browse_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Output Directory", str(self.output_dir))
        if dir_path:
            csv_path = os.path.join(dir_path, "results.csv")
            if os.path.exists(csv_path):
                self.output_dir = Path(dir_path)
                self.handler = ResultDataHandler(csv_path, str(self.output_dir))
                self.coordinator = PipelineCoordinator(output_dir=str(self.output_dir))
                self.refresh_view()
            else:
                InfoBar.error("Error", "No results.csv found in selected directory.", parent=self.window())

    def save_edits(self):
        idx = self.handler.current_index
        if idx < 0: return
        
        new_data = {k: v.text() for k, v in self.entries.items()}
        
        # Rename files if ID/Category changed
        updated_name = self.handler.rename_item_files(
            idx, 
            new_data.get('category', 'UNKNOWN'), 
            new_data.get('id', 'UNKNOWN')
        )
        
        if self.handler.save_edit(idx, new_data):
            InfoBar.success("Success", "Updated successfully ✓", parent=self.window(), duration=2000)
            if updated_name:
                self.filename_label.setText(updated_name)

    def reprocess_image(self):
        if not self.coordinator:
            InfoBar.error("Error", "Pipeline Coordinator not initialized.", parent=self.window())
            return

        item = self.handler.get_current_item()
        if not item: return
        
        img_path = self.handler.get_image_path(item)
        self.reprocess_btn.setEnabled(False)
        self.reprocess_btn.setText("AI Working...")
        
        def on_finished(pipeline_result):
            self.reprocess_btn.setEnabled(True)
            self.reprocess_btn.setText("AI Re-process")
            
            if pipeline_result and pipeline_result.data:
                data = pipeline_result.data
                for k, v in self.entries.items():
                    if k in data:
                        v.setText(str(data[k]))
                
                m = pipeline_result.metrics
                model1 = self.model_overrides.get("step1_model") or LLM_SETTINGS.get("step1_model")
                model2 = self.model_overrides.get("text_to_JSON_model") or LLM_SETTINGS.get("text_to_JSON_model")
                
                metrics_text = (
                    f"LLM Step 1 ({model1}): {m.step1_duration}s | "
                    f"LLM JSON ({model2}): {m.json_duration}s"
                )
                self.metrics_label.setText(metrics_text)
                InfoBar.success("Success", "AI Extraction Successful ✓", parent=self.window())
            else:
                self.metrics_label.setText("AI Reprocessing failed")
                InfoBar.error("Error", "AI reprocessing failed.", parent=self.window())

        run_in_background(
            self.coordinator.extract_data, 
            img_path, 
            model_overrides=self.model_overrides,
            callback=on_finished
        )

    def rotate_image(self):
        if self.viewer.has_image():
            item = self.handler.get_current_item()
            img_path = self.handler.get_image_path(item)
            if not img_path: return
            
            try:
                with Image.open(img_path) as img:
                    img = img.rotate(-90, expand=True)
                    img.save(img_path)
                # Reload
                self.refresh_view()
            except Exception as e:
                logger.error(f"Rotation failed: {e}")

    def auto_crop(self):
        item = self.handler.get_current_item()
        if not item: return
        
        from src.core.ocr_engine import OcrEngine
        ocr = OcrEngine()
        if not ocr.is_ready():
            InfoBar.error("Error", "OCR Engine not ready.", parent=self.window())
            return
            
        img_path = self.handler.get_image_path(item)
        self.crop_btn.setEnabled(False)
        
        def on_ocr_finished(raw):
            self.crop_btn.setEnabled(True)
            if not raw: return
            results = raw[0] if raw else []
            ocr_data = [{"box": line[0], "text": line[1][0]} for line in results]
            bounds = ImageProcessingService.calculate_text_bounds(
                ocr_data, 
                padding=int(OCR_SETTINGS.get("crop_padding", 20))
            )
            if bounds:
                try:
                    with Image.open(img_path) as img:
                        img = ImageProcessingService.crop_to_content(img, bounds)
                        img.save(img_path)
                    self.refresh_view()
                except Exception as e:
                    logger.error(f"Auto-crop failed: {e}")
        
        run_in_background(ocr.run_inference, img_path, callback=on_ocr_finished)

    def save_current_image(self):
        InfoBar.info("Info", "Image transformations are saved automatically.", parent=self.window())

    def delete_current_item(self):
        from qfluentwidgets import MessageBox
        w = MessageBox("Confirm Delete", "Permanently delete this item?", self.window())
        if w.exec():
            item = self.handler.get_current_item()
            if not item: return
            
            try:
                img_path = self.handler.get_image_path(item)
                if img_path and os.path.exists(img_path):
                    os.remove(img_path)
                
                image_name = item.get('processed_image_name', '').strip()
                log_path = self.output_dir / "logs" / f"{Path(image_name).stem}.txt"
                if log_path.exists():
                    os.remove(log_path)
                
                if self.handler.delete_item(self.handler.current_index):
                    InfoBar.success("Deleted", "Item removed successfully", parent=self.window())
                    self.refresh_view()
            except Exception as e:
                InfoBar.error("Error", f"Deletion failed: {e}", parent=self.window())

    def view_log(self):
        item = self.handler.get_current_item()
        if not item: return
        
        image_name = item.get('processed_image_name', '').strip()
        log_path = self.output_dir / "logs" / f"{Path(image_name).stem}.txt"
        
        if log_path.exists():
            os.startfile(str(log_path))
        else:
            InfoBar.warning("Not Found", "No log file exists for this item.", parent=self.window())

    def open_settings(self):
        InfoBar.info("Settings", "Model overrides can be set in the Settings tab.", parent=self.window())

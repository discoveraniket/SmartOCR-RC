from PySide6.QtWidgets import QFrame, QVBoxLayout
from qfluentwidgets import SubtitleLabel, setFont

class ImageViewerView(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("image-viewer-view")
        self.layout = QVBoxLayout(self)
        
        self.label = SubtitleLabel("Image Viewer (Under Reconstruction)", self)
        setFont(self.label, 24)
        self.layout.addWidget(self.label)
        self.layout.addStretch(1)

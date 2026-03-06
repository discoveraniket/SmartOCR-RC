import sys
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QFrame, QVBoxLayout

from qfluentwidgets import (NavigationItemPosition, FluentWindow,
                            SubtitleLabel, setFont, FluentIcon as FIF)

from src.ui.qt_views.search_view import SearchView
from src.ui.qt_views.settings_view import SettingsView

class PlaceholderFrame(QFrame):
    def __init__(self, text: str, parent=None):
        super().__init__(parent=parent)
        self.setObjectName(text.replace(' ', '-'))
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(40, 40, 40, 40)
        label = SubtitleLabel(text, self)
        setFont(label, 24)
        self.layout.addWidget(label)
        self.layout.addStretch(1)

class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SmartOCR-RC")
        self.resize(1100, 800)

        # Initialize Views
        self.searchView = SearchView(self)
        self.dbView = PlaceholderFrame("RC Database Tools", self)
        self.batchView = PlaceholderFrame("Batch Processing", self)
        self.viewerView = PlaceholderFrame("Image Viewer", self)
        self.settingsView = SettingsView(self)

        self._init_navigation()

    def _init_navigation(self):
        # Add items to side navigation
        self.addSubInterface(self.searchView, FIF.SEARCH, 'Search')
        self.addSubInterface(self.dbView, FIF.FOLDER, 'Database')
        self.addSubInterface(self.batchView, FIF.APPLICATION, 'Batch')
        self.addSubInterface(self.viewerView, FIF.PHOTO, 'Viewer')
        
        self.navigationInterface.addSeparator()
        
        self.addSubInterface(self.settingsView, FIF.SETTING, 'Settings', NavigationItemPosition.BOTTOM)

        # Navigation behavior
        self.navigationInterface.setExpandWidth(220)
        
        # Set default
        self.switchTo(self.searchView)

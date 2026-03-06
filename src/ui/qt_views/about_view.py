import os
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QSpacerItem, QSizePolicy

from qfluentwidgets import (TitleLabel, SubtitleLabel, BodyLabel, CaptionLabel, 
                            HyperlinkButton, FluentIcon as FIF, IconWidget, 
                            SmoothScrollArea, CardWidget, setFont, PillPushButton)

class AboutView(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("about-view")
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Scroll Area for the whole view
        self.scroll_area = SmoothScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("background: transparent;")
        
        self.content_widget = QFrame()
        self.content_widget.setObjectName("content-widget")
        self.content_widget.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(60, 40, 60, 40)
        self.content_layout.setSpacing(30)
        self.content_layout.setAlignment(Qt.AlignTop)
        
        self.scroll_area.setWidget(self.content_widget)
        self.main_layout.addWidget(self.scroll_area)
        
        self._setup_ui()

    def _setup_ui(self):
        # --- Header Section ---
        header_layout = QHBoxLayout()
        header_layout.setSpacing(25)
        
        # App Icon (Fluent Icon placeholder)
        self.icon_widget = IconWidget(FIF.APPLICATION, self.content_widget)
        self.icon_widget.setFixedSize(96, 96)
        header_layout.addWidget(self.icon_widget)
        
        title_vbox = QVBoxLayout()
        self.title_label = TitleLabel("SmartOCR-RC")
        setFont(self.title_label, 36)
        
        self.version_label = BodyLabel("Version 2.0.0 (Stable Build)")
        self.version_label.setStyleSheet("color: #888888;")
        
        title_vbox.addWidget(self.title_label)
        title_vbox.addWidget(self.version_label)
        title_vbox.addStretch()
        
        header_layout.addLayout(title_vbox)
        header_layout.addStretch()
        
        self.content_layout.addLayout(header_layout)
        
        # --- Description ---
        self.description = BodyLabel(
            "An intelligent, end-to-end Ration Card processing suite designed for high-accuracy "
            "data extraction using PaddleOCR and local LLM orchestration. SmartOCR-RC streamlines "
            "the transition from raw physical documents to enriched digital databases."
        )
        self.description.setWordWrap(True)
        setFont(self.description, 16)
        self.content_layout.addWidget(self.description)
        
        # --- Features Card ---
        self.features_card = CardWidget(self.content_widget)
        self.features_layout = QVBoxLayout(self.features_card)
        self.features_layout.setContentsMargins(20, 20, 20, 20)
        self.features_layout.setSpacing(15)
        
        feat_title = SubtitleLabel("Core Capabilities")
        setFont(feat_title, 20)
        self.features_layout.addWidget(feat_title)
        
        features = [
            (FIF.SYNC, "One-Click Pipeline: Automatic OCR, LLM extraction, and enrichment."),
            (FIF.SEARCH, "Global Search: Real-time fuzzy searching across localized SQLite databases."),
            (FIF.PHOTO, "Interactive Viewer: Real-time image manipulation and manual data verification."),
            (FIF.APPLICATION, "Batch Processing: High-throughput background processing for large datasets.")
        ]
        
        for icon, text in features:
            row = QHBoxLayout()
            row.setSpacing(15)
            iw = IconWidget(icon)
            iw.setFixedSize(20, 20)
            lbl = BodyLabel(text)
            row.addWidget(iw)
            row.addWidget(lbl)
            row.addStretch()
            self.features_layout.addLayout(row)
            
        self.content_layout.addWidget(self.features_card)
        
        # --- Links & Support ---
        self.links_layout = QHBoxLayout()
        self.links_layout.setSpacing(20)
        
        self.github_btn = HyperlinkButton(
            "https://github.com/AniketSarkar/SmartOCR-RC", 
            "GitHub Repository", 
            self.content_widget
        )
        self.issue_btn = HyperlinkButton(
            "https://github.com/AniketSarkar/SmartOCR-RC/issues", 
            "Report an Issue", 
            self.content_widget
        )
        self.docs_btn = HyperlinkButton(
            "https://github.com/AniketSarkar/SmartOCR-RC/wiki", 
            "Documentation", 
            self.content_widget
        )
        
        self.links_layout.addWidget(self.github_btn)
        self.links_layout.addWidget(self.issue_btn)
        self.links_layout.addWidget(self.docs_btn)
        self.links_layout.addStretch()
        
        self.content_layout.addLayout(self.links_layout)
        
        # --- Technical Acknowledgements ---
        self.tech_layout = QVBoxLayout()
        self.tech_layout.setSpacing(10)
        
        tech_title = SubtitleLabel("Built With")
        setFont(tech_title, 18)
        self.tech_layout.addWidget(tech_title)
        
        self.tech_label = BodyLabel("PaddleOCR, PySide6, Ollama (Local LLM), and Fluent-Widgets.")
        self.tech_label.setStyleSheet("color: #888888;")
        self.tech_layout.addWidget(self.tech_label)
        
        self.content_layout.addLayout(self.tech_layout)
        
        # Spacer
        self.content_layout.addStretch(1)
        
        # --- Footer ---
        footer_vbox = QVBoxLayout()
        footer_vbox.setSpacing(5)
        
        self.copyright_label = CaptionLabel("© 2026 Aniket Sarkar. All rights reserved.")
        self.copyright_label.setAlignment(Qt.AlignCenter)
        self.copyright_label.setStyleSheet("color: #AAAAAA;")
        
        self.license_label = CaptionLabel("Licensed under the MIT License.")
        self.license_label.setAlignment(Qt.AlignCenter)
        self.license_label.setStyleSheet("color: #AAAAAA;")
        
        footer_vbox.addWidget(self.copyright_label)
        footer_vbox.addWidget(self.license_label)
        
        self.content_layout.addLayout(footer_vbox)

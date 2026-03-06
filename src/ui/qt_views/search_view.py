import os
import threading
import winsound
import time
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from qfluentwidgets import (SubtitleLabel, setFont, SearchLineEdit, 
                            CardWidget, StrongBodyLabel, BodyLabel, 
                            LineEdit, PushButton, PrimaryPushButton, InfoBar, InfoBarPosition)

from src.rc_processor.search_manager import SearchManager

class SearchRecordCard(CardWidget):
    """A card to display search results cleanly"""
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(10)
        
        self.fields = {}
        display_fields = [
            ("Category", "Category"),
            ("Ration Card No.", "Ration Card No."),
            ("Name", "Name"),
            ("Father/Husband Name", "Father/Husband Name"),
            ("HOF Name", "HOF Name(As Per NFSA Provision)"),
            ("Dealer Name", "Dealer_Name_Mapped")
        ]
        
        for label_text, db_col in display_fields:
            row = QHBoxLayout()
            lbl = StrongBodyLabel(label_text + ":", self)
            lbl.setFixedWidth(200)
            val = BodyLabel("", self)
            row.addWidget(lbl)
            row.addWidget(val)
            row.addStretch(1)
            self.layout.addLayout(row)
            self.fields[db_col] = val

    def update_data(self, data):
        for col, widget in self.fields.items():
            val = data.get(col, "")
            if col == "Name":
                caste = data.get("Deducted_Caste", "")
                if caste: val = f"{val} ({caste})"
            widget.setText(str(val))

    def clear(self):
        for widget in self.fields.values():
            widget.setText("")

class SearchView(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("search-view")
        
        db_path = os.path.join("data", "rc_db", "final_rc_data.db")
        if not os.path.exists(db_path):
            db_path = os.path.join("data", "rc_db", "rcdb.db")
        
        self.search_manager = SearchManager(db_path)
        self.search_manager.connect()
        
        self._setup_ui()
        self.current_match = {}

    def _setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(40, 40, 40, 40)
        self.layout.setSpacing(25)

        # Header
        self.title = SubtitleLabel("Search Ration Card", self)
        setFont(self.title, 28)
        self.layout.addWidget(self.title)

        # Search Input
        self.search_input = SearchLineEdit(self)
        self.search_input.setPlaceholderText("Enter 10 Digit Ration Card Number...")
        self.search_input.setFixedWidth(550)
        self.search_input.setFixedHeight(45)
        self.search_input.textChanged.connect(self.on_search_changed)
        self.search_input.returnPressed.connect(self.save_data)
        self.layout.addWidget(self.search_input)

        self.match_status = BodyLabel("", self)
        self.match_status.setStyleSheet("color: #0078d4;")
        self.layout.addWidget(self.match_status)

        # Results Card
        self.result_card = SearchRecordCard(self)
        self.layout.addWidget(self.result_card)

        # Editable Info Section
        self.edit_card = CardWidget(self)
        edit_layout = QVBoxLayout(self.edit_card)
        edit_layout.setContentsMargins(20, 20, 20, 20)
        edit_layout.setSpacing(15)
        
        edit_layout.addWidget(StrongBodyLabel("Additional Info (Editable)", self))
        
        caste_layout = QVBoxLayout()
        caste_layout.addWidget(BodyLabel("Caste:", self))
        self.caste_input = LineEdit(self)
        self.caste_input.setPlaceholderText("Enter Caste...")
        self.caste_input.setFixedWidth(400)
        self.caste_input.returnPressed.connect(self.save_data)
        caste_layout.addWidget(self.caste_input)
        edit_layout.addLayout(caste_layout)
        
        mobile_layout = QVBoxLayout()
        mobile_layout.addWidget(BodyLabel("Mobile No:", self))
        self.mobile_input = LineEdit(self)
        self.mobile_input.setPlaceholderText("Enter Mobile Number...")
        self.mobile_input.setFixedWidth(400)
        self.mobile_input.returnPressed.connect(self.save_data)
        mobile_layout.addWidget(self.mobile_input)
        edit_layout.addLayout(mobile_layout)
        
        self.layout.addWidget(self.edit_card)

        # Export Settings Section
        self.export_card = CardWidget(self)
        export_layout = QVBoxLayout(self.export_card)
        export_layout.setContentsMargins(20, 20, 20, 20)
        export_layout.setSpacing(10)
        
        export_layout.addWidget(StrongBodyLabel("Export Settings", self))
        
        path_layout = QHBoxLayout()
        self.output_path_input = LineEdit(self)
        self.output_path_input.setText(os.path.join("data", "rc_db", "Benef_list.csv"))
        self.output_path_input.setPlaceholderText("Select output CSV file...")
        
        self.browse_btn = PushButton("Browse...", self)
        self.browse_btn.clicked.connect(self.browse_output)
        
        path_layout.addWidget(self.output_path_input, 1)
        path_layout.addWidget(self.browse_btn)
        export_layout.addLayout(path_layout)
        
        self.layout.addWidget(self.export_card)

        # Actions
        self.save_btn = PrimaryPushButton("Save Record to File", self)
        self.save_btn.setFixedWidth(200)
        self.save_btn.setFixedHeight(40)
        self.save_btn.clicked.connect(self.save_data)
        self.layout.addWidget(self.save_btn)

        self.layout.addStretch(1)

    def browse_output(self):
        from PySide6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Select Output File", self.output_path_input.text(), "CSV Files (*.csv);;All Files (*)"
        )
        if file_path:
            self.output_path_input.setText(file_path)

    def on_search_changed(self, text):
        text = text.strip()
        if not text:
            self.result_card.clear()
            self.match_status.setText("")
            self.caste_input.clear()
            self.mobile_input.clear()
            return
            
        result, count = self.search_manager.search_ration_card(text)
        if result:
            self.current_match = result
            self.result_card.update_data(result)
            self.caste_input.setText(str(result.get("Deducted_Caste", "")))
            self.mobile_input.setText(str(result.get("Mobile No", "")))
            self.match_status.setText(f"Matches found: {count}")
            if count == 1:
                threading.Thread(target=winsound.Beep, args=(1000, 150), daemon=True).start()
        else:
            self.current_match = {}
            self.result_card.clear()
            self.match_status.setText("No matches found")
            
            def double_low_beep():
                winsound.Beep(400, 150)
                time.sleep(0.1)
                winsound.Beep(400, 150)
            
            threading.Thread(target=double_low_beep, daemon=True).start()

    def save_data(self):
        if not self.current_match:
            return
            
        save_data = self.current_match.copy()
        save_data["Deducted_Caste"] = self.caste_input.text()
        save_data["Mobile No"] = self.mobile_input.text()
        
        output_file = self.output_path_input.text()
        if not output_file:
            InfoBar.error("Error", "Please select an output file path", parent=self.window())
            return
            
        success, msg = self.search_manager.save_record(save_data, target_file=output_file)
        
        if success:
            InfoBar.success("Success", "Record saved to file", parent=self.window(), duration=2000)
            self.search_input.clear()
            self.search_input.setFocus()
            threading.Thread(target=winsound.Beep, args=(1500, 150), daemon=True).start()
        else:
            InfoBar.error("Error", f"Failed to save: {msg}", parent=self.window())

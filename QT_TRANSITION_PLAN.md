# UI Transition Plan: CustomTkinter to PySide6 (Fluent UI)

## 🎯 Goal
Migrate the entire application interface from `customtkinter` to `PySide6` using the `PySide6-Fluent-Widgets` library. This will provide a modern, hardware-accelerated, and native-feeling Windows 10/11 experience with smooth animations and professional layouts.

---

## 🛠️ Mandatory Workflows & Constraints
- **Granular Transition:** Implementation must proceed section-by-section or feature-by-feature (e.g., individual views like Settings or Search).
- **Integrity Checks:** After every section/feature is completed, `python run_tests.py` must be executed.
- **Manual Validation:** I must stop and wait for your manual verification after each section/feature before proceeding.
- **Side-by-Side Coexistence:** The `customtkinter` (`ctk`) code (e.g., `src/ui/dashboard.py`, `src/ui/views/`) must be kept as a reference until the transition is 100% complete and verified.
- **Single Window First:** The new UI must be a single-window application with a collapsible sidebar navigation.

---

## 🏗️ New Architecture
- **Entry Point:** `main_qt.py` (Handles DPI scaling and theme initialization).
- **Main Window:** `src/ui/qt_views/main_window.py` (Uses `FluentWindow` with built-in collapsible sidebar).
- **Views:** Each page is a standalone `QFrame` or `ScrollArea` located in `src/ui/qt_views/`.

---

## ✅ Completed (Phase 1 & 2 Part 1)
- [x] **Environment Setup:** Installed `PySide6` and `PySide6-Fluent-Widgets`.
- [x] **Main Window Scaffolding:** Implemented the navigation hub with a smooth sidebar.
- [x] **Search Ration Card (View):**
    - Real-time search using `SearchManager`.
    - Modern Results Card (`SearchRecordCard`).
    - Editable fields for Caste and Mobile Number.
    - File export functionality with "Browse" path selection.
    - Success/Error notifications using `InfoBar`.
- [x] **Settings View:**
    - Port OCR and LLM parameter management.
    - Implement grouped `CardWidget` or `SettingCardGroup`.
    - Add "Revert to Defaults" and "Save" logic.
- [x] **Integrity Check:** `run_tests.py` passed (Implicitly confirmed by user or latest runs).
- [x] **Manual Validation:** User confirmed Search View.

---

## 📋 Remaining Tasks (Phased)

### Phase 2: Pipeline & Data Hub
- [x] **Auto Process (One-Click Pipeline):**
    - Dedicated sidebar view for the end-to-end processing pipeline.
    - Integrated status and summary dashboard.
- [x] **Database Operations Hub:**
    - Create a unified view using `Pivot` (Tabs) for:
        - Download (Beneficiary Downloader)
        - HTML to CSV (Converter)
        - Enrichment (Caste/Dealer mapping)
        - CSV to Database (SQLite conversion)
- [x] **Integrity Check:** Run `run_tests.py`.
- [x] **Validation:** Wait for User check.

### Phase 3: Processing & Visualization
- [x] **Batch Processing View:**
    - Port the `BatchProcessor` UI (Progress bars, file discovery list).
    - Handle real-time logs in a `TextEdit`.
- [ ] **Image Viewer View (INCOMPLETE - NEEDS REWORK):**
    - Port the interactive viewer (Zoom, pan, OCR bounding box overlays).
- [x] **Integrity Check:** Run `run_tests.py`.
- [ ] **Validation:** Wait for User check.

---

## 🧹 Final Cleanup (Post-Transition)
Once the PySide6 version reaches 100% feature parity and is verified:
1. **Remove CTK UI Files:**
    - Delete `src/ui/views/` directory.
    - Delete `src/ui/dashboard.py`.
    - Delete `src/ui/main_window.py` and other CTK-based windows.
2. **Remove Experimental Files:**
    - Delete `src/ui/flet_ui/` folder.
    - Delete `legacy/` if no longer needed.
3. **Dependency Update:**
    - Remove `customtkinter` from `requirements.txt`.
4. **Main Entry Update:**
    - Merge `main_qt.py` logic into `main.py` and delete `main_qt.py`.

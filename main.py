import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

def main():
    # 1. Enable High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    # 2. Initialize QApplication
    app = QApplication(sys.argv)
    
    # 2.1 Set default application font to avoid QFont::setPointSize warning
    from PySide6.QtGui import QFont
    app.setFont(QFont("Segoe UI", 9))
    
    # 3. Import and show main window
    from qfluentwidgets import setTheme, Theme
    from src.ui.qt_views.main_window import MainWindow
    
    setTheme(Theme.DARK)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

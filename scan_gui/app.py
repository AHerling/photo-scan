"""Application entry point: QApplication setup and main window creation."""

import sys

from PySide6.QtWidgets import QApplication

from scan_gui.ui.main_window import MainWindow

_STYLE_SHEET = """
QLabel#pageHeading { font-size: 18px; font-weight: 600; }
QListWidget#navList { border-right: 1px solid palette(mid); }
"""


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("scan-gui")
    app.setOrganizationName("scan-gui")
    app.setStyle("Fusion")
    app.setStyleSheet(_STYLE_SHEET)

    window = MainWindow()
    window.show()
    return app.exec()

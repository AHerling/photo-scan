"""Page 3: scan controls — milestone 3.

Will provide Start/Cancel, a progress bar fed by ScanJob's stderr progress
stream, and a live log of the scan.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class ScanPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        label = QLabel(
            "Scan controls arrive in milestone 3.\n"
            "Start/Cancel with live progress from scanimage."
        )
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setWordWrap(True)
        layout = QVBoxLayout(self)
        layout.addWidget(label)

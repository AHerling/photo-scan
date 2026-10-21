"""Page 4: scan results — milestone 4.

Will show a preview grid of the photographs detected and cropped from the
raw scan, plus an "open output folder" action.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class ResultsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        label = QLabel(
            "Results arrive in milestone 4.\n"
            "A preview grid of the photographs detected and cropped "
            "from the scan."
        )
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setWordWrap(True)
        layout = QVBoxLayout(self)
        layout.addWidget(label)

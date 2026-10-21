"""Page 2: scanner option form — milestone 2.

Will render an editable form generated from the selected device's SANE
option descriptors (via backend/options.py + ui/widgets/option_widgets.py),
with Apply and Save-as-preset actions.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class OptionsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        label = QLabel(
            "Option editing arrives in milestone 2.\n"
            "This page will show a form generated from the scanner's "
            "SANE options."
        )
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setWordWrap(True)
        layout = QVBoxLayout(self)
        layout.addWidget(label)

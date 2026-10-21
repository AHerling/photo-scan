"""Page 3: scan controls — milestone 3.

Start/Cancel, a progress bar fed by ScanJob's stderr progress stream, and a
live log of the scan.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from scan_gui.models import Device


class ScanPage(QWidget):
    """Start and cancel a scan, show its progress and output."""

    start_requested = Signal()
    cancel_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        heading = QLabel("Scan")
        heading.setObjectName("pageHeading")

        self._device_label = QLabel("No scanner selected.")
        self._output_label = QLabel("No output file yet.")
        self._output_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setPlaceholderText("Scanner output appears here.")

        self._start_button = QPushButton("Start scan")
        self._start_button.clicked.connect(self.start_requested)
        self._cancel_button = QPushButton("Cancel")
        self._cancel_button.clicked.connect(self.cancel_requested)
        self._cancel_button.setEnabled(False)

        buttons = QHBoxLayout()
        buttons.addWidget(self._start_button)
        buttons.addWidget(self._cancel_button)
        buttons.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.addWidget(heading)
        layout.addWidget(self._device_label)
        layout.addWidget(self._output_label)
        layout.addWidget(self._progress)
        layout.addWidget(self._log, 1)
        layout.addLayout(buttons)

    def set_device(self, device: Device | None) -> None:
        if device is None:
            self._device_label.setText("No scanner selected.")
        else:
            self._device_label.setText(f"{device.description}  ({device.name})")

    def set_output_path(self, path) -> None:
        self._output_label.setText(f"Output: {path}")

    def set_busy(self, busy: bool) -> None:
        self._start_button.setEnabled(not busy)
        self._cancel_button.setEnabled(busy)
        if busy:
            self._progress.setValue(0)

    def set_progress(self, percent: int) -> None:
        self._progress.setValue(percent)

    def append_log(self, text: str) -> None:
        self._log.appendPlainText(text)

    def clear_log(self) -> None:
        self._log.clear()

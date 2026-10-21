"""Page 3: scan controls — milestone 3.

Start/Cancel, a progress bar fed by ScanJob's stderr progress stream, and a
live log of the scan. The Preview button takes a fast picture of the whole
scan bed; dragging over that picture picks the area to scan.
"""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from scan_gui.models import Device
from scan_gui.ui.widgets.selection_view import SelectionView


class ScanPage(QWidget):
    """Start and cancel a scan, show its progress and output."""

    start_requested = Signal()
    cancel_requested = Signal()
    output_dir_requested = Signal(str)  # chosen folder
    preview_requested = Signal()
    selection_changed = Signal(object)  # QRect in preview pixels, or None

    def __init__(self, parent=None):
        super().__init__(parent)

        heading = QLabel("Scan")
        heading.setObjectName("pageHeading")

        self._device_label = QLabel("No scanner selected.")
        self._output_path: Path | None = None
        self._output_label = QLabel("No output file yet.")
        self._output_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self._folder_button = QPushButton()
        self._folder_button.setToolTip("Folder for the raw scans — click to change")
        self._folder_button.clicked.connect(self._choose_folder)
        folder_row = QHBoxLayout()
        folder_row.addWidget(QLabel("Output folder"))
        folder_row.addWidget(self._folder_button, 1)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)

        # The preview of the scan bed, with the area the user picks on it.
        self._selection_view = SelectionView()
        self._selection_view.selection_changed.connect(self._on_selection_changed)
        self._selection_view.selection_changed.connect(self.selection_changed)
        self._preview_area = QScrollArea()
        self._preview_area.setWidget(self._selection_view)
        self._preview_area.setWidgetResizable(True)
        self._preview_area.setMinimumHeight(260)
        self._preview_area.setVisible(False)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setPlaceholderText("Scanner output appears here.")
        self._log.setMaximumHeight(140)

        self._preview_button = QPushButton("Preview")
        self._preview_button.setToolTip(
            "Take a fast picture of the whole scan bed to pick an area"
        )
        self._preview_button.clicked.connect(self.preview_requested)

        self._start_button = QPushButton("Start scan")
        self._start_button.clicked.connect(self.start_requested)
        self._cancel_button = QPushButton("Cancel")
        self._cancel_button.clicked.connect(self.cancel_requested)
        self._cancel_button.setEnabled(False)

        buttons = QHBoxLayout()
        buttons.addWidget(self._preview_button)
        buttons.addWidget(self._start_button)
        buttons.addWidget(self._cancel_button)
        buttons.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.addWidget(heading)
        layout.addWidget(self._device_label)
        layout.addLayout(folder_row)
        layout.addWidget(self._output_label)
        layout.addWidget(self._progress)
        layout.addWidget(self._preview_area, 1)
        layout.addWidget(self._log)
        layout.addLayout(buttons)

    def set_device(self, device: Device | None) -> None:
        if device is None:
            self._device_label.setText("No scanner selected.")
        else:
            self._device_label.setText(f"{device.description}  ({device.name})")

    def set_output_dir(self, path: str) -> None:
        self._folder_button.setText(path)

    def set_output_path(self, path) -> None:
        self._output_path = Path(path)
        self._output_label.setText(f"Next file: {path}")

    def output_path(self) -> Path | None:
        """The file the last scan was written to."""
        return self._output_path

    def _choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Output folder", self._folder_button.text()
        )
        if folder:
            self.output_dir_requested.emit(folder)

    def set_busy(self, busy: bool) -> None:
        """While a scan runs: Start is off, Cancel is on."""
        self._start_button.setEnabled(not busy)
        self._cancel_button.setEnabled(busy)
        self._preview_button.setEnabled(not busy)
        if busy:
            self._progress.setValue(0)

    def set_processing(self, processing: bool) -> None:
        """While the photos are being cropped: Start is off, Cancel stays off."""
        self._start_button.setEnabled(not processing)
        self._cancel_button.setEnabled(False)

    def set_progress(self, percent: int) -> None:
        self._progress.setValue(percent)

    # ---- preview and selection ----

    def set_preview(self, image: QImage) -> None:
        """Show the picture of the scan bed."""
        self._selection_view.set_image(image)
        self._preview_area.setVisible(True)

    def clear_preview(self) -> None:
        """Forget the preview and the area picked on it."""
        self._selection_view.clear()
        self._preview_area.setVisible(False)
        self._start_button.setText("Start scan")

    def selection(self):
        """The area the user picked, in preview pixels."""
        return self._selection_view.selection()

    def preview_size(self):
        """The size of the preview image, in pixels."""
        return self._selection_view.image_size()

    def _on_selection_changed(self, selection) -> None:
        """With an area picked, the start button scans just that area."""
        self._start_button.setText("Scan Selection" if selection else "Start scan")

    def append_log(self, text: str) -> None:
        self._log.appendPlainText(text)

    def clear_log(self) -> None:
        self._log.clear()

"""Page 4: scan results — milestone 4.

Shows a preview grid of the photographs detected and cropped from the raw
scan, plus an "open output folder" action.
"""

from pathlib import Path

from PySide6.QtCore import QSize, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QIcon, QImageReader, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

THUMBNAIL_SIZE = QSize(220, 220)


class ResultsPage(QWidget):
    """Preview grid of the cropped photographs."""

    def __init__(self, parent=None):
        super().__init__(parent)

        heading = QLabel("Results")
        heading.setObjectName("pageHeading")

        self._summary = QLabel("No photographs yet.")
        self._summary.setWordWrap(True)

        self._grid = QListWidget()
        self._grid.setViewMode(QListWidget.ViewMode.IconMode)
        self._grid.setResizeMode(QListWidget.ResizeMode.Adjust)
        self._grid.setMovement(QListWidget.Movement.Static)
        self._grid.setIconSize(THUMBNAIL_SIZE)
        self._grid.setWordWrap(True)
        self._grid.setSpacing(8)

        self._open_button = QPushButton("Open output folder")
        self._open_button.clicked.connect(self._open_folder)
        self._open_button.setEnabled(False)
        self._folder = ""

        buttons = QHBoxLayout()
        buttons.addWidget(self._open_button)
        buttons.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.addWidget(heading)
        layout.addWidget(self._summary)
        layout.addWidget(self._grid, 1)
        layout.addLayout(buttons)

    def set_photos(self, paths: list[Path], source: str = "") -> None:
        """Show the cropped photographs in the preview grid."""
        self._grid.clear()
        self._folder = str(Path(paths[0]).parent) if paths else ""
        self._open_button.setEnabled(bool(paths))
        for path in paths:
            item = QListWidgetItem(QIcon(self._thumbnail(path)), Path(path).name)
            item.setToolTip(str(path))
            self._grid.addItem(item)
        if paths:
            origin = f" in {Path(source).name}" if source else ""
            self._summary.setText(f"{len(paths)} photograph(s) detected{origin}.")
        else:
            self._summary.setText("No photographs yet.")

    def set_error(self, message: str) -> None:
        self._grid.clear()
        self._summary.setText(message)

    def _thumbnail(self, path: Path) -> QPixmap:
        """Load a scaled preview without decoding the full image."""
        reader = QImageReader(str(path))
        size = reader.size()
        if size.isValid() and not size.isEmpty():
            scale = min(
                THUMBNAIL_SIZE.width() / size.width(),
                THUMBNAIL_SIZE.height() / size.height(),
            )
            if scale < 1:
                reader.setScaledSize(
                    QSize(int(size.width() * scale), int(size.height() * scale))
                )
        return QPixmap.fromImage(reader.read())

    def _open_folder(self) -> None:
        if self._folder:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self._folder))

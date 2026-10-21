"""QRunnable wrapper for processing/photos.py — milestone 4.

Runs the OpenCV detection/crop in a QThreadPool so the UI never blocks on a
1200 DPI TIFF, and reports results back over Qt signals.
"""

from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from scan_gui.processing import photos


class PhotoWorkerSignals(QObject):
    """Signals emitted by the worker thread."""

    finished = Signal(list)  # list[Path]
    failed = Signal(str)     # human-readable message


class PhotoTask(QRunnable):
    """Detects and crops the photographs of one scan."""

    def __init__(self, scan_path: Path, output_dir: Path, start_number: int = 1):
        super().__init__()
        self.signals = PhotoWorkerSignals()
        self._scan_path = Path(scan_path)
        self._output_dir = Path(output_dir)
        self._start_number = start_number

    @Slot()
    def run(self) -> None:
        try:
            written = photos.process_scan(
                self._scan_path, self._output_dir, self._start_number
            )
        except photos.DetectionError as exc:
            self.signals.failed.emit(str(exc))
        except Exception as exc:  # never let the pool thread die on us
            self.signals.failed.emit(f"Photo detection failed: {exc}")
        else:
            self.signals.finished.emit(written)

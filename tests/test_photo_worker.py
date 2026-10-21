"""Tests for the background photo worker — milestone 4.

The worker runs the OpenCV pipeline in a QThreadPool, so the tests drive it
through a QEventLoop and a real QObject receiver (queued delivery).
"""

import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import QCoreApplication, QEventLoop, QObject, QThreadPool, QTimer, Slot

from scan_gui.processing.worker import PhotoTask


def write_scan(path: Path) -> Path:
    """A scanned page with two photographs on it."""
    page = np.full((800, 1000, 3), 255, dtype=np.uint8)
    page[100:500, 100:400] = 60
    page[100:500, 500:800] = 60
    cv2.imwrite(str(path), page)
    return path


class _Receiver(QObject):
    """Collects the worker's answer."""

    def __init__(self, loop: QEventLoop):
        super().__init__()
        self._loop = loop
        self.paths: list | None = None
        self.error: str | None = None

    @Slot(list)
    def on_finished(self, paths: list) -> None:
        self.paths = paths
        self._loop.quit()

    @Slot(str)
    def on_failed(self, message: str) -> None:
        self.error = message
        self._loop.quit()


class PhotoTaskTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def _run(self, task: PhotoTask) -> _Receiver:
        loop = QEventLoop()
        receiver = _Receiver(loop)
        task.signals.finished.connect(receiver.on_finished)
        task.signals.failed.connect(receiver.on_failed)
        pool = QThreadPool()
        pool.start(task)
        QTimer.singleShot(15000, loop.quit)
        loop.exec()
        pool.waitForDone(5000)
        return receiver

    def test_reports_the_written_photos(self):
        with tempfile.TemporaryDirectory() as tmp:
            scan = write_scan(Path(tmp) / "000001.tiff")
            receiver = self._run(PhotoTask(scan, Path(tmp) / "photos", 1))
            self.assertIsNone(receiver.error)
            self.assertIsNotNone(receiver.paths)
            self.assertEqual(
                [path.name for path in receiver.paths], ["000001.jpg", "000002.jpg"]
            )
            self.assertTrue(all(path.exists() for path in receiver.paths))

    def test_reports_a_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            broken = Path(tmp) / "000001.tiff"
            broken.write_text("not an image")
            receiver = self._run(PhotoTask(broken, Path(tmp) / "photos", 1))
            self.assertIsNone(receiver.paths)
            self.assertIsNotNone(receiver.error)
            self.assertIn("read", receiver.error.lower())


if __name__ == "__main__":
    unittest.main()

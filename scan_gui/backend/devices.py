"""Device discovery via `scanimage -L`.

Layering rule for the backend: QtCore only, never QtWidgets.

`parse_devices()` is a pure function so it can be unit-tested against captured
output in tests/fixtures/ without a scanner attached.
"""

import re

from PySide6.QtCore import QObject, QProcess, Signal

from scan_gui.models import Device

LIST_COMMAND = ["scanimage", "-L"]

# Real output looks like:
#   device `pixma:04A91913_5E2C64' is a CANON Canon PIXMA MP610 Scanner
#   device `escl:https://192.168.1.10:443/eSCL/' is a epsonscan2 network scanner
# with stray backend warnings interleaved that must be ignored.
_DEVICE_RE = re.compile(r"^device [`'](?P<name>.+?)[`'] is a (?P<desc>.+?)\s*$")


def parse_devices(output: str) -> list[Device]:
    """Extract devices from `scanimage -L` output, skipping non-device lines."""
    devices: list[Device] = []
    seen: set[str] = set()
    for line in output.splitlines():
        match = _DEVICE_RE.match(line.strip())
        if not match:
            continue
        name = match.group("name")
        if name in seen:
            continue
        seen.add(name)
        devices.append(Device(name=name, description=match.group("desc")))
    return devices


class DeviceScanner(QObject):
    """Runs `scanimage -L` asynchronously and emits the parsed device list."""

    refresh_started = Signal()
    refresh_finished = Signal(list)  # list[Device]
    refresh_failed = Signal(str)     # human-readable message

    def __init__(self, parent=None):
        super().__init__(parent)
        self._process = QProcess(self)
        self._process.finished.connect(self._on_finished)
        self._process.errorOccurred.connect(self._on_error)

    @property
    def busy(self) -> bool:
        return self._process.state() != QProcess.ProcessState.NotRunning

    def refresh(self) -> None:
        """Start a device scan. Ignored if one is already running."""
        if self.busy:
            return
        self.refresh_started.emit()
        self._process.start(LIST_COMMAND[0], LIST_COMMAND[1:])

    def stop(self) -> None:
        """Kill any in-flight scanimage process (call on window close)."""
        if self.busy:
            self._process.kill()
            self._process.waitForFinished(1000)

    def _on_finished(self, exit_code: int, _status) -> None:
        stdout = self._process.readAllStandardOutput().data().decode("utf-8", "replace")
        if exit_code != 0:
            stderr = self._process.readAllStandardError().data().decode("utf-8", "replace")
            self.refresh_failed.emit(
                stderr.strip() or f"scanimage -L exited with code {exit_code}"
            )
            return
        self.refresh_finished.emit(parse_devices(stdout))

    def _on_error(self, error: QProcess.ProcessError) -> None:
        if error == QProcess.ProcessError.FailedToStart:
            self.refresh_failed.emit(
                "Could not run scanimage. Is sane-backends installed?"
            )

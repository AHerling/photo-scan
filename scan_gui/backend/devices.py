"""Device discovery via `scanimage -L`.

Layering rule for the backend: QtCore only, never QtWidgets.

`parse_devices()` is a pure function so it can be unit-tested against captured
output in tests/fixtures/ without a scanner attached.
"""

import re

from PySide6.QtCore import QObject, QProcess, QTimer, Signal

from scan_gui.models import Device

LIST_COMMAND = ["scanimage", "-L"]

# Real output looks like:
#   device `pixma:04A91913_5E2C64' is a CANON Canon PIXMA MP610 Scanner
#   device `escl:https://192.168.1.10:443/eSCL/' is a epsonscan2 network scanner
#   device `airscan:w0:HP OfficeJet' is a HP OfficeJet eSCL network scanner
# with stray backend warnings interleaved that must be ignored.
_DEVICE_RE = re.compile(r"^device [`'](?P<name>.+?)[`'] is a (?P<desc>.+?)\s*$")

# Give network backends (especially sane-airscan/Avahi) time to discover
# scanners, but don't let the UI hang forever.
DISCOVERY_TIMEOUT_MS = 15000


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
        self._timed_out = False
        self._timeout = QTimer(self)
        self._timeout.setSingleShot(True)
        self._timeout.timeout.connect(self._on_timeout)

    @property
    def busy(self) -> bool:
        return self._process.state() != QProcess.ProcessState.NotRunning

    def refresh(self) -> None:
        """Start a device scan. Ignored if one is already running."""
        if self.busy:
            return
        self._timed_out = False
        self.refresh_started.emit()
        self._process.start(LIST_COMMAND[0], LIST_COMMAND[1:])
        self._timeout.start(DISCOVERY_TIMEOUT_MS)

    def stop(self) -> None:
        """Kill any in-flight scanimage process (call on window close)."""
        self._timeout.stop()
        if self.busy:
            self._process.kill()
            self._process.waitForFinished(1000)

    def _on_timeout(self) -> None:
        if not self.busy or self._timed_out:
            return
        self._timed_out = True
        self._process.kill()
        self._process.waitForFinished(1000)
        self.refresh_failed.emit(
            "Device discovery timed out.\n\n"
            "For network/WiFi scanners (AirScan/eSCL):\n"
            "- Install sane-airscan and avahi: "
            "sudo dnf install sane-airscan avahi\n"
            "- Start Avahi: sudo systemctl enable --now avahi-daemon\n"
            "- Ensure the scanner and computer are on the same network\n"
            "- Check firewall settings\n\n"
            "For USB scanners:\n"
            "- Add your user to scanner/lp groups: "
            "sudo usermod -aG scanner,lp $USER (log out and back in)\n"
            "- Check the USB connection and try Refresh."
        )

    def _on_finished(self, exit_code: int, _status) -> None:
        self._timeout.stop()
        if self._timed_out:
            return
        stdout = self._process.readAllStandardOutput().data().decode("utf-8", "replace")
        if exit_code != 0:
            stderr = self._process.readAllStandardError().data().decode("utf-8", "replace")
            message = stderr.strip() or f"scanimage -L exited with code {exit_code}"
            self.refresh_failed.emit(
                f"{message}\n\n"
                "Tips:\n"
                "- USB: add your user to scanner,lp groups and check permissions\n"
                "- Network/AirScan: install sane-airscan and avahi, "
                "run avahi-daemon, and ensure same network"
            )
            return
        self.refresh_finished.emit(parse_devices(stdout))

    def _on_error(self, error: QProcess.ProcessError) -> None:
        self._timeout.stop()
        if self._timed_out:
            return
        if error == QProcess.ProcessError.FailedToStart:
            self.refresh_failed.emit(
                "Could not run scanimage. Is sane-backends installed?\n\n"
                "Fedora: sudo dnf install sane-backends sane-airscan avahi"
            )

"""Page 1: discover SANE devices and pick one."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from scan_gui.models import Device


class DevicePage(QWidget):
    """Scanner list with refresh. Dumb by design: emits signals, gets data."""

    refresh_requested = Signal()
    device_selected = Signal(object)  # Device | None

    def __init__(self, parent=None):
        super().__init__(parent)
        self._devices: list[Device] = []

        heading = QLabel("Scanner")
        heading.setObjectName("pageHeading")

        self._list = QListWidget()
        self._list.itemSelectionChanged.connect(self._on_selection_changed)

        self._status = QLabel("Scanning for scanners…")
        self._status.setWordWrap(True)

        self._refresh_button = QPushButton("Refresh")
        self._refresh_button.clicked.connect(self.refresh_requested)

        bottom = QHBoxLayout()
        bottom.addWidget(self._status, 1)
        bottom.addWidget(self._refresh_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.addWidget(heading)
        layout.addWidget(self._list, 1)
        layout.addLayout(bottom)

    def set_busy(self, busy: bool) -> None:
        self._refresh_button.setEnabled(not busy)
        if busy:
            self._status.setText("Scanning for scanners…")

    def set_devices(self, devices: list[Device]) -> None:
        self._devices = list(devices)
        self._list.clear()
        for device in self._devices:
            item = QListWidgetItem(device.description, self._list)
            item.setToolTip(device.name)
            item.setData(Qt.ItemDataRole.UserRole, device)
        if self._devices:
            self._status.setText(
                f"Found {len(self._devices)} scanner(s). Select one to continue."
            )
        else:
            self._status.setText(
                "No scanners found.\n\n"
                "USB: connect the scanner, add your user to scanner/lp groups "
                "(log out and back in).\n\n"
                "Network/WiFi (AirScan/eSCL): install sane-airscan and avahi, "
                "start avahi-daemon, ensure same network.\n\n"
                "Press Refresh to try again."
            )

    def set_error(self, message: str) -> None:
        self._list.clear()
        self._status.setText(message)

    def select_device_named(self, name: str | None) -> None:
        if not name:
            return
        for row in range(self._list.count()):
            item = self._list.item(row)
            device: Device = item.data(Qt.ItemDataRole.UserRole)
            if device.name == name:
                self._list.setCurrentRow(row)
                return

    def selected_device(self) -> Device | None:
        item = self._list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _on_selection_changed(self) -> None:
        self.device_selected.emit(self.selected_device())

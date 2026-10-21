"""Main window: navigation sidebar + stacked pages + status bar.

Pages never call each other directly — they emit signals and the window wires
them to the backend and the app state machine.
"""

from PySide6.QtCore import QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QMainWindow,
    QStackedWidget,
    QWidget,
)

from scan_gui.backend.devices import DeviceScanner
from scan_gui.config import load_config, save_config
from scan_gui.models import Device
from scan_gui.state import AppState, AppStateMachine
from scan_gui.ui.pages.device_page import DevicePage
from scan_gui.ui.pages.options_page import OptionsPage
from scan_gui.ui.pages.results_page import ResultsPage
from scan_gui.ui.pages.scan_page import ScanPage

_NAV_ITEMS = ("Scanner", "Options", "Scan", "Results")


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Scan GUI")
        self.resize(960, 640)

        self._config = load_config()
        self._state = AppStateMachine(self)
        self._scanner = DeviceScanner(self)
        self._device: Device | None = None

        # --- layout: nav sidebar + stacked pages ---
        self._nav = QListWidget()
        self._nav.setObjectName("navList")
        self._nav.setFixedWidth(150)
        for label in _NAV_ITEMS:
            self._nav.addItem(label)
        self._nav.setCurrentRow(0)

        self._pages = QStackedWidget()
        self._device_page = DevicePage()
        self._options_page = OptionsPage()
        self._scan_page = ScanPage()
        self._results_page = ResultsPage()
        for page in (
            self._device_page,
            self._options_page,
            self._scan_page,
            self._results_page,
        ):
            self._pages.addWidget(page)
        self._nav.currentRowChanged.connect(self._pages.setCurrentIndex)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._nav)
        layout.addWidget(self._pages, 1)
        self.setCentralWidget(central)

        self.statusBar().showMessage("No scanner selected.")

        # --- wiring ---
        self._device_page.refresh_requested.connect(self._scanner.refresh)
        self._scanner.refresh_started.connect(
            lambda: self._device_page.set_busy(True)
        )
        self._scanner.refresh_finished.connect(self._on_devices_found)
        self._scanner.refresh_failed.connect(self._on_refresh_failed)
        self._device_page.device_selected.connect(self._on_device_selected)
        self._state.changed.connect(self._on_state_changed)

        # Kick off the initial device discovery once the event loop is running.
        QTimer.singleShot(0, self._device_page.refresh_requested)

    # ---- device discovery handlers ----

    def _on_devices_found(self, devices: list) -> None:
        self._device_page.set_busy(False)
        self._device_page.set_devices(devices)
        # Restore previous selection if that device is still present.
        self._device_page.select_device_named(self._config.get("last_device"))
        if not devices:
            self.statusBar().showMessage("No scanners found.")

    def _on_refresh_failed(self, message: str) -> None:
        self._device_page.set_busy(False)
        self._device_page.set_error(f"Device scan failed: {message}")
        self.statusBar().showMessage(f"Device scan failed: {message}")

    def _on_device_selected(self, device: Device | None) -> None:
        self._device = device
        if device is None:
            self._state.transition(AppState.NO_DEVICE)
            self.statusBar().showMessage("No scanner selected.")
        else:
            self._state.transition(AppState.DEVICE_SELECTED)
            self.statusBar().showMessage(f"Selected: {device.name}")
        self._config["last_device"] = device.name if device else None
        save_config(self._config)

    # ---- state machine ----

    def _on_state_changed(self, _old, new_state) -> None:
        # M2+: disable nav entries and controls that require a loaded device.
        # In M1 every page except Scanner is a placeholder, so navigation
        # stays open for exploration.
        return

    def closeEvent(self, event: QCloseEvent) -> None:
        self._scanner.stop()
        super().closeEvent(event)

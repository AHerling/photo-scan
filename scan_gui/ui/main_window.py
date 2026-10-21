"""Main window: navigation sidebar + stacked pages + status bar.

Pages never call each other directly — they emit signals and the window wires
them to the backend and the app state machine.
"""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QMainWindow,
    QStackedWidget,
    QWidget,
)

from scan_gui.backend.devices import DeviceScanner
from scan_gui.backend.options import OptionLoader
from scan_gui.config import load_config, save_config
from scan_gui.models import Device
from scan_gui.state import AppState, AppStateMachine
from scan_gui.ui.pages.device_page import DevicePage
from scan_gui.ui.pages.options_page import OptionsPage
from scan_gui.ui.pages.results_page import ResultsPage
from scan_gui.ui.pages.scan_page import ScanPage

_NAV_ITEMS = ("Scanner", "Options", "Scan", "Results")

# Which pages are reachable in each state.
_NAV_BY_STATE = {
    AppState.NO_DEVICE: {"Scanner"},
    AppState.DEVICE_SELECTED: {"Scanner", "Options"},
    AppState.OPTIONS_LOADED: {"Scanner", "Options", "Scan"},
    AppState.SCANNING: {"Scanner", "Options", "Scan"},
    AppState.PROCESSING: {"Scanner", "Options", "Scan"},
    AppState.DONE: {"Scanner", "Options", "Scan", "Results"},
    AppState.ERROR: {"Scanner", "Options"},
}


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Scan GUI")
        self.resize(960, 640)

        self._config = load_config()
        self._state = AppStateMachine(self)
        self._scanner = DeviceScanner(self)
        self._loader = OptionLoader(self)
        self._device: Device | None = None
        self._option_values: dict[str, str] = {}

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

        self._options_page.load_requested.connect(self._loader.load)
        self._loader.load_started.connect(lambda: self._options_page.set_busy(True))
        self._loader.load_finished.connect(self._on_options_loaded)
        self._loader.load_failed.connect(self._on_options_failed)
        self._options_page.options_applied.connect(self._on_options_applied)
        self._options_page.preset_save_requested.connect(self._on_preset_save)
        self._options_page.preset_delete_requested.connect(self._on_preset_delete)
        self._options_page.set_presets(self._config.get("presets", {}))

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
        self._options_page.set_device(device)
        self._option_values = {}
        if device is None:
            self._state.transition(AppState.NO_DEVICE)
            self.statusBar().showMessage("No scanner selected.")
        else:
            self._state.transition(AppState.DEVICE_SELECTED)
            self.statusBar().showMessage(f"Selected: {device.name}")
            self._options_page.load_requested.emit(device.name)
        self._config["last_device"] = device.name if device else None
        save_config(self._config)

    # ---- option handlers ----

    def _on_options_loaded(self, options: list) -> None:
        self._options_page.set_options(options)
        self._state.transition(AppState.OPTIONS_LOADED)
        self.statusBar().showMessage(
            f"{self._device.name}: {len(options)} option(s) loaded."
            if self._device
            else "Options loaded."
        )

    def _on_options_failed(self, message: str) -> None:
        self._options_page.set_error(f"Could not read options: {message}")
        self.statusBar().showMessage(f"Could not read options: {message}")

    def _on_options_applied(self, values: dict) -> None:
        self._option_values = dict(values)
        self.statusBar().showMessage(f"Applied {len(values)} option(s).")

    def _on_preset_save(self, name: str, values: dict) -> None:
        presets = dict(self._config.get("presets", {}))
        presets[name] = dict(values)
        self._config["presets"] = presets
        save_config(self._config)
        self._options_page.set_presets(presets)
        self.statusBar().showMessage(f"Preset '{name}' saved.")

    def _on_preset_delete(self, name: str) -> None:
        presets = dict(self._config.get("presets", {}))
        presets.pop(name, None)
        self._config["presets"] = presets
        save_config(self._config)
        self._options_page.set_presets(presets)
        self.statusBar().showMessage(f"Preset '{name}' deleted.")

    # ---- state machine ----

    def _on_state_changed(self, _old, new_state) -> None:
        allowed = _NAV_BY_STATE.get(new_state, {"Scanner"})
        for row, label in enumerate(_NAV_ITEMS):
            item = self._nav.item(row)
            flags = item.flags()
            if label in allowed:
                flags |= Qt.ItemFlag.ItemIsEnabled
            else:
                flags &= ~Qt.ItemFlag.ItemIsEnabled
            item.setFlags(flags)
        current = self._nav.currentItem()
        if current is not None and not (current.flags() & Qt.ItemFlag.ItemIsEnabled):
            self._nav.setCurrentRow(0)

    def closeEvent(self, event: QCloseEvent) -> None:
        self._scanner.stop()
        self._loader.stop()
        super().closeEvent(event)

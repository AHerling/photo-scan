"""Main window: navigation sidebar + stacked pages + status bar.

Pages never call each other directly — they emit signals and the window wires
them to the backend and the app state machine.
"""

from pathlib import Path

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
from scan_gui.backend.scan import ScanJob, next_output_path
from scan_gui.config import DEFAULTS, load_config, save_config
from scan_gui.models import Device, OptionDescriptor
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
        self._scan_job = ScanJob(self)
        self._device: Device | None = None
        self._options: list[OptionDescriptor] = []
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

        self._scan_page.set_output_dir(self._raw_dir())
        self._scan_page.set_output_path(next_output_path(Path(self._raw_dir())))

        self._scan_page.start_requested.connect(self._start_scan)
        self._scan_page.cancel_requested.connect(self._scan_job.cancel)
        self._scan_page.output_dir_requested.connect(self._on_output_dir_chosen)
        self._scan_job.started.connect(self._on_scan_started)
        self._scan_job.progress.connect(self._scan_page.set_progress)
        self._scan_job.log.connect(self._scan_page.append_log)
        self._scan_job.finished.connect(self._on_scan_finished)
        self._scan_job.failed.connect(self._on_scan_failed)
        self._scan_job.cancelled.connect(self._on_scan_cancelled)

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
        self._scan_page.set_device(device)
        self._options = []
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
        self._options = list(options)
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

    # ---- scan handlers ----

    def _raw_dir(self) -> str:
        return self._config.get("raw_dir") or DEFAULTS["raw_dir"]

    def _start_scan(self) -> None:
        if self._device is None:
            self.statusBar().showMessage("Select a scanner first.")
            return
        output = next_output_path(Path(self._raw_dir()))
        values = self._options_page.current_values()
        self._scan_page.set_output_path(output)
        self._scan_page.clear_log()
        self._scan_job.start(self._device.name, self._options, values, output)

    def _on_output_dir_chosen(self, path: str) -> None:
        self._config["raw_dir"] = path
        save_config(self._config)
        self._scan_page.set_output_dir(path)
        self._scan_page.set_output_path(next_output_path(Path(path)))
        self.statusBar().showMessage(f"Raw scans will be saved to {path}")

    def _on_scan_started(self, path: str) -> None:
        self._scan_page.set_busy(True)
        self._state.transition(AppState.SCANNING)
        self.statusBar().showMessage(f"Scanning to {path}")

    def _on_scan_finished(self, path: str) -> None:
        self._scan_page.set_busy(False)
        self._scan_page.set_progress(100)
        self._state.transition(AppState.DONE)
        self.statusBar().showMessage(f"Scan complete: {path}")

    def _on_scan_failed(self, message: str) -> None:
        # A failed start (e.g. "a scan is already running") must not disturb a
        # scan that is still going.
        busy = self._scan_job.busy
        self._scan_page.set_busy(busy)
        if not busy:
            self._state.transition(AppState.OPTIONS_LOADED)
        self.statusBar().showMessage(f"Scan failed: {message}")

    def _on_scan_cancelled(self) -> None:
        self._scan_page.set_busy(False)
        self._state.transition(AppState.OPTIONS_LOADED)
        self.statusBar().showMessage("Scan cancelled.")

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
        self._scan_job.stop()
        super().closeEvent(event)

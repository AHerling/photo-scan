"""Main window: navigation sidebar + stacked pages + status bar.

Pages never call each other directly — they emit signals and the window wires
them to the backend and the app state machine.
"""

import tempfile
from pathlib import Path

from PySide6.QtCore import QThreadPool, Qt, QTimer
from PySide6.QtGui import QCloseEvent, QImage
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from scan_gui.backend.area import (
    bed_size,
    find_area_options,
    full_bed_values,
    selection_values,
)
from scan_gui.backend.devices import DeviceScanner
from scan_gui.backend.options import OptionLoader, find_option, option_minimum
from scan_gui.backend.scan import ScanJob, next_number, next_output_path
from scan_gui.config import DEFAULTS, load_config, save_config
from scan_gui.models import Device, OptionDescriptor
from scan_gui.processing.worker import PhotoTask
from scan_gui.state import AppState, AppStateMachine
from scan_gui.ui.pages.device_page import DevicePage
from scan_gui.ui.pages.options_page import OptionsPage
from scan_gui.ui.pages.results_page import ResultsPage
from scan_gui.ui.pages.scan_page import ScanPage
from scan_gui.ui.pages.simple_page import SimplePage

_NAV_ITEMS = ("Scanner", "Options", "Scan", "Results")

# The two ways the app can look: the everyday view and the full one.
_MODE_SIMPLE = 0
_MODE_PRO = 1

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
        self.setWindowTitle("Photo Scan")
        self.resize(960, 640)

        self._config = load_config()
        self._state = AppStateMachine(self)
        self._scanner = DeviceScanner(self)
        self._loader = OptionLoader(self)
        self._scan_job = ScanJob(self)
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(1)
        self._device: Device | None = None
        self._devices: list[Device] = []
        self._options: list[OptionDescriptor] = []
        self._option_values: dict[str, str] = {}
        self._previewing = False
        self._preview_dir = Path(tempfile.mkdtemp(prefix="scan-gui-preview-"))

        # --- layout: header + one of the two modes ---
        self._mode_combo = QComboBox()
        self._mode_combo.addItem("Simple mode", _MODE_SIMPLE)
        self._mode_combo.addItem("Pro Mode", _MODE_PRO)
        self._mode_combo.setToolTip("Simple mode is the everyday view")
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)

        title = QLabel("Scan GUI")
        title.setObjectName("appTitle")

        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 8, 16, 8)
        header_layout.addWidget(title)
        header_layout.addStretch(1)
        header_layout.addWidget(QLabel("Mode"))
        header_layout.addWidget(self._mode_combo)

        # --- nav sidebar + stacked pages (the DEV mode) ---
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

        dev_area = QWidget()
        dev_layout = QHBoxLayout(dev_area)
        dev_layout.setContentsMargins(0, 0, 0, 0)
        dev_layout.setSpacing(0)
        dev_layout.addWidget(self._nav)
        dev_layout.addWidget(self._pages, 1)

        # --- the simple mode ---
        self._simple_page = SimplePage()

        self._modes = QStackedWidget()
        self._modes.addWidget(self._simple_page)
        self._modes.addWidget(dev_area)
        self._modes.setCurrentIndex(_MODE_SIMPLE)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(header)
        layout.addWidget(self._modes, 1)
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
        self._scan_page.preview_requested.connect(self._start_preview)
        self._scan_job.started.connect(self._on_scan_started)
        self._scan_job.progress.connect(self._scan_page.set_progress)
        self._scan_job.progress.connect(self._simple_page.set_progress)
        self._scan_job.log.connect(self._scan_page.append_log)
        self._scan_job.finished.connect(self._on_scan_finished)
        self._scan_job.failed.connect(self._on_scan_failed)
        self._scan_job.cancelled.connect(self._on_scan_cancelled)

        self._simple_page.printer_selected.connect(self._on_simple_printer_selected)
        self._simple_page.scan_requested.connect(self._start_scan)
        self._simple_page.folder_requested.connect(self._on_output_dir_chosen)
        self._simple_page.settings_changed.connect(self._on_simple_settings_changed)
        self._simple_page.set_output_dir(self._raw_dir())

        # Kick off the initial device discovery once the event loop is running.
        QTimer.singleShot(0, self._device_page.refresh_requested)

    # ---- device discovery handlers ----

    def _on_devices_found(self, devices: list) -> None:
        self._devices = list(devices)
        self._device_page.set_busy(False)
        self._device_page.set_devices(devices)
        self._simple_page.set_devices(self._devices)
        # Restore previous selection if that device is still present.
        self._device_page.select_device_named(self._config.get("last_device"))
        if not devices:
            self.statusBar().showMessage("No scanners found.")
            self._simple_page.set_status(
                "No scanners found. Check USB/network, permissions (scanner,lp), "
                "and avahi for AirScan. Press Refresh in the Scanner page."
            )

    def _on_refresh_failed(self, message: str) -> None:
        self._device_page.set_busy(False)
        self._device_page.set_error(f"Device scan failed: {message}")
        self._simple_page.set_status(f"Device scan failed: {message}")
        self.statusBar().showMessage(f"Device scan failed: {message}")

    def _on_device_selected(self, device: Device | None) -> None:
        self._device = device
        self._options_page.set_device(device)
        self._scan_page.set_device(device)
        self._scan_page.clear_preview()
        self._previewing = False
        self._simple_page.set_selected_device(device.name if device else None)
        self._options = []
        self._option_values = {}
        if device is None:
            self._state.transition(AppState.NO_DEVICE)
            self.statusBar().showMessage("No scanner selected.")
            self._simple_page.set_status("Choose a scanner to get started.")
        else:
            self._state.transition(AppState.DEVICE_SELECTED)
            self.statusBar().showMessage(f"Selected: {device.name}")
            self._simple_page.set_status("Reading the scanner's options…")
            self._options_page.load_requested.emit(device.name)
        self._config["last_device"] = device.name if device else None
        save_config(self._config)

    def _on_simple_printer_selected(self, name: str) -> None:
        """The scanner was picked in the simple mode."""
        if not name:
            self._on_device_selected(None)
            return
        device = next((d for d in self._devices if d.name == name), None)
        if device is not None and (self._device is None or self._device.name != name):
            self._on_device_selected(device)

    # ---- option handlers ----

    def _on_options_loaded(self, options: list) -> None:
        self._options = list(options)
        self._options_page.set_options(options)
        self._simple_page.set_options(options)
        self._state.transition(AppState.OPTIONS_LOADED)
        self.statusBar().showMessage(
            f"{self._device.name}: {len(options)} option(s) loaded."
            if self._device
            else "Options loaded."
        )
        self._simple_page.set_status("Ready to scan.")

    def _on_options_failed(self, message: str) -> None:
        self._options_page.set_error(f"Could not read options: {message}")
        self._simple_page.set_options_failed(f"Could not read options: {message}")
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
            self._simple_page.set_status("Choose a scanner first.")
            return
        output = next_output_path(Path(self._raw_dir()))
        values = self._options_page.current_values()
        # The simple mode has the last word on colour and resolution.
        values.update(self._simple_page.current_values())
        selection = self._scan_page.selection()
        if selection is not None:
            values.update(self._selection_values(selection))
        self._scan_page.set_output_path(output)
        self._scan_page.clear_log()
        self._previewing = False
        self._scan_job.start(self._device.name, self._options, values, output)

    def _selection_values(self, selection):
        area = find_area_options(self._options)
        if area is None:
            return {}
        bed = bed_size(self._options)
        size = self._scan_page.preview_size()
        return selection_values(selection, size, bed, area)

    def _start_preview(self) -> None:
        """Take a fast picture of the whole scan bed at the lowest resolution."""
        if self._device is None:
            self.statusBar().showMessage("Select a scanner first.")
            return
        if not self._options:
            self.statusBar().showMessage("Read the scanner options first.")
            return
        values = self._preview_values()
        output = self._preview_dir / "preview.tiff"
        if output.exists():
            output.unlink()
        self._previewing = True
        self._scan_page.clear_log()
        self.statusBar().showMessage("Taking a preview of the scan bed…")
        self._scan_job.start(self._device.name, self._options, values, output)

    def _preview_values(self) -> dict[str, str]:
        """The lowest resolution and the whole bed, for the preview."""
        values = dict(self._options_page.current_values())
        resolution = find_option(self._options, "resolution")
        if resolution is not None:
            lowest = option_minimum(resolution)
            if lowest:
                values["resolution"] = lowest
        values.update(full_bed_values(self._options))
        return values

    def _show_preview(self, path: Path) -> None:
        image = QImage(str(path))
        if image.isNull():
            self._scan_page.set_busy(False)
            self.statusBar().showMessage("Could not read the preview image.")
            return
        self._scan_page.set_busy(False)
        self._scan_page.set_preview(image)
        self._state.transition(AppState.OPTIONS_LOADED)
        self.statusBar().showMessage("Preview ready — drag over it to pick an area.")

    def _on_simple_settings_changed(self, values: dict) -> None:
        """The simple mode changed a setting — keep the full form in step."""
        for name, value in values.items():
            self._options_page.set_value(name, value)

    def _on_output_dir_chosen(self, path: str) -> None:
        # The save location is remembered for both the TIFFs and the photographs.
        self._config["raw_dir"] = path
        self._config["photo_dir"] = path
        save_config(self._config)
        self._scan_page.set_output_dir(path)
        self._scan_page.set_output_path(next_output_path(Path(path)))
        self._simple_page.set_output_dir(path)
        self.statusBar().showMessage(f"Scans will be saved to {path}")

    def _on_scan_started(self, path: str) -> None:
        self._scan_page.set_busy(True)
        self._simple_page.set_busy(True)
        if self._previewing:
            self._simple_page.set_status("Taking a preview…")
            self._state.transition(AppState.SCANNING)
            self.statusBar().showMessage("Taking a preview of the scan bed…")
        else:
            self._simple_page.set_status("Scanning…")
            self._state.transition(AppState.SCANNING)
            self.statusBar().showMessage(f"Scanning to {path}")

    def _on_scan_finished(self, path: str) -> None:
        if self._previewing:
            self._previewing = False
            self._show_preview(Path(path))
            return
        # Pro mode: the TIFF is the result, no photo recognition.
        if self._modes.currentIndex() == _MODE_PRO:
            self._scan_page.set_busy(False)
            self._scan_page.set_processing(False)
            self._scan_page.set_progress(100)
            self._simple_page.set_busy(False)
            self._simple_page.set_progress(100)
            self._state.transition(AppState.DONE)
            self.statusBar().showMessage(f"Scan saved to {path}")
            self._simple_page.set_status(f"Scan saved to {path}")
            return
        self._scan_page.set_processing(True)
        self._scan_page.set_progress(100)
        self._simple_page.set_progress(100)
        self._simple_page.set_status("Looking for photographs…")
        self._state.transition(AppState.PROCESSING)
        self._start_processing(Path(path))

    def _start_processing(self, scan_path: Path) -> None:
        """Look for photographs in the finished scan, off the UI thread."""
        photo_dir = Path(self._raw_dir())
        task = PhotoTask(scan_path, photo_dir, next_number(photo_dir, "jpg"))
        task.signals.finished.connect(self._on_photos_found)
        task.signals.failed.connect(self._on_photos_failed)
        self._pool.start(task)

    def _on_photos_found(self, paths: list) -> None:
        self._scan_page.set_processing(False)
        self._simple_page.set_busy(False)
        source = self._scan_page.output_path()
        self._results_page.set_photos(paths, str(source) if source else "")
        self._state.transition(AppState.DONE)
        self._nav.setCurrentRow(3)
        folder = str(Path(paths[0]).parent) if paths else self._raw_dir()
        self._simple_page.set_status(
            f"{len(paths)} photograph(s) saved in {folder}."
        )
        self.statusBar().showMessage(f"{len(paths)} photograph(s) detected.")

    def _on_photos_failed(self, message: str) -> None:
        self._scan_page.set_processing(False)
        self._simple_page.set_busy(False)
        self._results_page.set_error(message)
        self._state.transition(AppState.DONE)
        self._simple_page.set_status(f"Photo detection: {message}")
        self.statusBar().showMessage(f"Photo detection: {message}")

    def _on_scan_failed(self, message: str) -> None:
        if self._previewing:
            self._previewing = False
        # A failed start (e.g. "a scan is already running") must not disturb a
        # scan that is still going.
        busy = self._scan_job.busy
        self._scan_page.set_busy(busy)
        if not busy:
            self._simple_page.set_busy(False)
            self._state.transition(AppState.OPTIONS_LOADED)
        self._simple_page.set_status(f"Scan failed: {message}")
        self.statusBar().showMessage(f"Scan failed: {message}")

    def _on_scan_cancelled(self) -> None:
        if self._previewing:
            self._previewing = False
        self._scan_page.set_busy(False)
        self._simple_page.set_busy(False)
        self._state.transition(AppState.OPTIONS_LOADED)
        self._simple_page.set_status("Scan cancelled.")
        self.statusBar().showMessage("Scan cancelled.")

    # ---- modes ----

    def _on_mode_changed(self, index: int) -> None:
        """Switch between the everyday view and the full one."""
        self._modes.setCurrentIndex(index)
        if index == _MODE_PRO:
            self._nav.setCurrentRow(0)
            # Pro mode does not run photo recognition; the Results page is not used.
            self._refresh_nav()
        else:
            self._refresh_nav()
        self.statusBar().showMessage(
            "Simple mode" if index == _MODE_SIMPLE else "Pro Mode"
        )

    def _refresh_nav(self) -> None:
        self._on_state_changed(self._state.state, self._state.state)

    # ---- state machine ----

    def _on_state_changed(self, _old, new_state) -> None:
        allowed = set(_NAV_BY_STATE.get(new_state, {"Scanner"}))
        if self._modes.currentIndex() == _MODE_PRO:
            allowed.discard("Results")
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
        import shutil

        if hasattr(self, "_preview_dir"):
            shutil.rmtree(self._preview_dir, ignore_errors=True)
        super().closeEvent(event)

"""The simple mode: the everyday view.

Five rows — scanner, colour, resolution, output folder and the start button.
Everything stays greyed out until the information it needs is there: the
scanner list takes a few seconds to arrive, and the colour and resolution
lists depend on the scanner that was picked.

The page is dumb like the other pages: it emits signals and shows data.
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from scan_gui.models import Device, OptionDescriptor
from scan_gui.simple_options import SimpleChoice, colour_choices, resolution_choices

_PLACEHOLDER = "— choose a scanner —"


class SimplePage(QWidget):
    """Scanner, colour, resolution, folder, start — nothing else."""

    printer_selected = Signal(str)  # device name
    scan_requested = Signal()
    folder_requested = Signal(str)  # chosen folder
    settings_changed = Signal(dict)  # {option name: value}

    def __init__(self, parent=None):
        super().__init__(parent)

        heading = QLabel("Scan")
        heading.setObjectName("pageHeading")

        self._printer = QComboBox()
        self._printer.setToolTip("The scanner to use")
        self._printer.currentIndexChanged.connect(self._on_printer_changed)

        self._colour = QComboBox()
        self._colour.setToolTip("How much colour to capture")
        self._colour.currentIndexChanged.connect(self._on_choice_changed)

        self._resolution = QComboBox()
        self._resolution.setToolTip("Scanning resolution")
        self._resolution.currentIndexChanged.connect(self._on_choice_changed)

        self._folder_button = QPushButton()
        self._folder_button.setToolTip("Where the scans are saved — click to change")
        self._folder_button.clicked.connect(self._choose_folder)

        self._start_button = QPushButton("Start scan")
        self._start_button.clicked.connect(self.scan_requested)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setVisible(False)

        self._status = QLabel("Looking for scanners…")
        self._status.setWordWrap(True)

        form = QFormLayout()
        form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)
        form.addRow("Scanner", self._printer)
        form.addRow("Colour", self._colour)
        self._colour_row = form.rowCount() - 1
        form.addRow("Resolution", self._resolution)
        self._resolution_row = form.rowCount() - 1
        form.addRow("Save to", self._folder_button)
        self._form = form

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self._start_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        layout.addWidget(heading)
        layout.addLayout(form)
        layout.addLayout(buttons)
        layout.addWidget(self._progress)
        layout.addWidget(self._status)
        layout.addStretch(1)

        self._devices: list[Device] = []
        self._colour_option = ""
        self._resolution_option = ""
        self._options_loaded = False
        self._busy = False
        self._update_enabled()

    # ---- data ----

    def set_devices(self, devices: list[Device]) -> None:
        """Fill the scanner drop-down, keeping the current selection."""
        self._devices = list(devices)
        selected = self.selected_device_name()

        self._printer.blockSignals(True)
        self._printer.clear()
        self._printer.addItem(_PLACEHOLDER, None)
        for device in self._devices:
            self._printer.addItem(device.description, device.name)
        self._printer.blockSignals(False)

        if self._devices:
            self.set_status(f"Found {len(self._devices)} scanner(s).")
        else:
            self.set_status("No scanners found. Check the connection and try again.")
        self.set_selected_device(selected)

    def set_selected_device(self, name: str | None) -> None:
        """Show `name` as the selected scanner without emitting anything."""
        index = self._printer.findData(name)
        if index < 0:
            index = 0
        self._printer.blockSignals(True)
        self._printer.setCurrentIndex(index)
        self._printer.blockSignals(False)
        self._update_enabled()

    def set_options(self, options: list[OptionDescriptor]) -> None:
        """Fill the colour and resolution drop-downs from the scanner."""
        self._options_loaded = True
        self._fill(self._colour, colour_choices(options), "colour")
        self._fill(self._resolution, resolution_choices(options), "resolution")
        self._update_enabled()
        # Let the full form know what the simple mode settled on.
        self.settings_changed.emit(self.current_values())

    def set_options_failed(self, message: str) -> None:
        self._options_loaded = False
        self._colour_option = ""
        self._resolution_option = ""
        self._colour.clear()
        self._resolution.clear()
        self._form.setRowVisible(self._colour_row, False)
        self._form.setRowVisible(self._resolution_row, False)
        self.set_status(message)
        self._update_enabled()

    def set_status(self, text: str) -> None:
        self._status.setText(text)

    def set_output_dir(self, path: str) -> None:
        self._folder_button.setText(path)
        self._folder_button.setToolTip(f"Scans are saved to {path} — click to change")

    def set_busy(self, busy: bool) -> None:
        """While a scan runs the controls are locked and the bar shows up."""
        self._busy = busy
        self._progress.setVisible(busy)
        if busy:
            self._progress.setValue(0)
        self._update_enabled()

    def set_progress(self, percent: int) -> None:
        self._progress.setValue(percent)

    def selected_device_name(self) -> str | None:
        """The name of the scanner the user picked, if any."""
        data = self._printer.currentData()
        return str(data) if data else None

    def current_values(self) -> dict[str, str]:
        """The values the simple mode controls, e.g. {"mode": "Color"}."""
        values: dict[str, str] = {}
        for combo, option in (
            (self._colour, self._colour_option),
            (self._resolution, self._resolution_option),
        ):
            if not option or combo.currentIndex() < 0:
                continue
            value = combo.currentData()
            if value:
                values[option] = str(value)
        return values

    # ---- internals ----

    def _fill(self, combo: QComboBox, choices: list[SimpleChoice], kind: str) -> None:
        """Put the choices into a drop-down and remember the option name."""
        combo.blockSignals(True)
        combo.clear()
        for choice in choices:
            combo.addItem(choice.label, choice.value)
        combo.blockSignals(False)

        if kind == "colour":
            self._colour_option = choices[0].option if choices else ""
            row = self._colour_row
        else:
            self._resolution_option = choices[0].option if choices else ""
            row = self._resolution_row

        # A row without choices is not worth showing.
        self._form.setRowVisible(row, bool(choices))
        self._update_enabled()

    def _update_enabled(self) -> None:
        """Grey out whatever is not usable yet."""
        self._printer.setEnabled(not self._busy and bool(self._devices))
        self._colour.setEnabled(not self._busy and bool(self._colour_option))
        self._resolution.setEnabled(not self._busy and bool(self._resolution_option))
        self._folder_button.setEnabled(not self._busy)
        self._start_button.setEnabled(
            not self._busy
            and self._options_loaded
            and self.selected_device_name() is not None
        )

    def _on_printer_changed(self, _index: int) -> None:
        name = self.selected_device_name()
        self.printer_selected.emit(name or "")
        self._update_enabled()

    def _on_choice_changed(self, _index: int) -> None:
        self.settings_changed.emit(self.current_values())

    def _choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Where should the scans be saved?", self._folder_button.text()
        )
        if folder:
            self.folder_requested.emit(folder)

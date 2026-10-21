"""Page 2: scanner option form — milestone 2.

Renders an editable form generated from the selected device's SANE option
descriptors (via backend/options.py + ui/widgets/option_widgets.py), with
Apply and preset actions. The page is dumb: it emits signals and shows data.
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from scan_gui.models import Device, OptionDescriptor
from scan_gui.ui.widgets.option_widgets import OptionWidget, create_option_widget


class OptionsPage(QWidget):
    """Option form for the selected device."""

    load_requested = Signal(str)               # device name
    options_applied = Signal(dict)             # {option name: value}
    preset_save_requested = Signal(str, dict)  # name, values
    preset_delete_requested = Signal(str)       # name

    def __init__(self, parent=None):
        super().__init__(parent)
        self._device: Device | None = None
        self._descriptors: list[OptionDescriptor] = []
        self._widgets: list[OptionWidget] = []
        self._presets: dict[str, dict] = {}

        heading = QLabel("Options")
        heading.setObjectName("pageHeading")

        self._device_label = QLabel("No scanner selected.")
        self._status = QLabel("")
        self._status.setWordWrap(True)

        self._preset_combo = QComboBox()
        self._preset_combo.setMinimumWidth(180)
        self._preset_combo.currentTextChanged.connect(self._on_preset_selected)
        self._save_preset_button = QPushButton("Save as…")
        self._save_preset_button.clicked.connect(self._save_preset)
        self._delete_preset_button = QPushButton("Delete")
        self._delete_preset_button.clicked.connect(self._delete_preset)

        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Preset"))
        preset_row.addWidget(self._preset_combo, 1)
        preset_row.addWidget(self._save_preset_button)
        preset_row.addWidget(self._delete_preset_button)

        self._form = QFormLayout()
        self._form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form_widget = QWidget()
        form_widget.setLayout(self._form)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setWidget(form_widget)

        self._advanced_box = QGroupBox("Advanced options")
        self._advanced_box.setCheckable(True)
        self._advanced_box.setChecked(False)
        self._advanced_form = QFormLayout(self._advanced_box)

        self._apply_button = QPushButton("Apply")
        self._apply_button.clicked.connect(self._apply)
        self._revert_button = QPushButton("Revert")
        self._revert_button.clicked.connect(self._revert)

        buttons = QHBoxLayout()
        buttons.addWidget(self._revert_button)
        buttons.addStretch(1)
        buttons.addWidget(self._apply_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.addWidget(heading)
        layout.addWidget(self._device_label)
        layout.addLayout(preset_row)
        layout.addWidget(self._scroll, 1)
        layout.addWidget(self._advanced_box)
        layout.addWidget(self._status)
        layout.addLayout(buttons)

        self.set_busy(False)

    # ---- page state ----

    def set_device(self, device: Device | None) -> None:
        self._device = device
        if device is None:
            self._device_label.setText("No scanner selected.")
            self._descriptors = []
            self._clear_form()
        else:
            self._device_label.setText(f"{device.description}  ({device.name})")
            self._status.setText("Loading options…")
            self.set_busy(True)

    def set_busy(self, busy: bool) -> None:
        self._apply_button.setEnabled(not busy)
        self._revert_button.setEnabled(not busy)
        self._scroll.setEnabled(not busy)
        self._advanced_box.setEnabled(not busy)

    def set_options(self, options: list[OptionDescriptor]) -> None:
        """Build the form from freshly loaded option descriptors."""
        self._clear_form()
        self._descriptors = list(options)
        for descriptor in options:
            widget = create_option_widget(descriptor)
            if descriptor.current is not None:
                widget.set_value(descriptor.current)
            widget.setEnabled(not descriptor.read_only and not descriptor.inactive)
            label = QLabel(descriptor.name)
            unit = f" ({descriptor.unit})" if descriptor.unit != "NONE" else ""
            label.setText(f"{descriptor.name}{unit}")
            tooltip = descriptor.description or descriptor.name
            label.setToolTip(tooltip)
            widget.setToolTip(tooltip)
            self._widgets.append(widget)
            if descriptor.advanced:
                self._advanced_form.addRow(label, widget)
            else:
                self._form.addRow(label, widget)
        self._status.setText(f"{len(options)} option(s) loaded.")
        self.set_busy(False)

    def set_error(self, message: str) -> None:
        self._descriptors = []
        self._clear_form()
        self._status.setText(message)
        self.set_busy(False)

    def set_presets(self, presets: dict[str, dict]) -> None:
        """Replace the list of saved presets."""
        self._presets = dict(presets)
        current = self._preset_combo.currentText()
        self._preset_combo.blockSignals(True)
        self._preset_combo.clear()
        self._preset_combo.addItems(sorted(self._presets))
        index = self._preset_combo.findText(current)
        if index >= 0:
            self._preset_combo.setCurrentIndex(index)
        self._preset_combo.blockSignals(False)
        self._delete_preset_button.setEnabled(bool(self._presets))

    # ---- values ----

    def current_values(self) -> dict[str, str]:
        """The values currently shown in the form."""
        values: dict[str, str] = {}
        for descriptor, widget in zip(self._descriptors, self._widgets):
            if descriptor.read_only or descriptor.inactive:
                continue
            values[descriptor.name] = widget.value()
        return values

    def set_value(self, name: str, value: str) -> None:
        """Set one option in the form, e.g. from the simple mode."""
        for descriptor, widget in zip(self._descriptors, self._widgets):
            if descriptor.name == name:
                widget.set_value(str(value))
                return

    def _apply(self) -> None:
        values = self.current_values()
        self._status.setText(f"Applied {len(values)} option(s).")
        self.options_applied.emit(values)

    def _revert(self) -> None:
        """Restore the form to the values the scanner reported."""
        for descriptor, widget in zip(self._descriptors, self._widgets):
            if descriptor.current is not None:
                widget.set_value(descriptor.current)
        self._status.setText("Reverted to the scanner's current values.")

    def _on_preset_selected(self, name: str) -> None:
        values = self._presets.get(name)
        if not values:
            return
        for descriptor, widget in zip(self._descriptors, self._widgets):
            if descriptor.name in values:
                widget.set_value(str(values[descriptor.name]))
        self._status.setText(f"Preset '{name}' loaded. Press Apply to use it.")

    def _save_preset(self) -> None:
        name, accepted = QInputDialog.getText(
            self, "Save preset", "Preset name:", text=self._preset_combo.currentText()
        )
        if accepted and name.strip():
            self.preset_save_requested.emit(name.strip(), self.current_values())

    def _delete_preset(self) -> None:
        name = self._preset_combo.currentText()
        if name:
            self.preset_delete_requested.emit(name)

    def _clear_form(self) -> None:
        self._widgets = []
        while self._form.rowCount():
            self._form.removeRow(0)
        while self._advanced_form.rowCount():
            self._advanced_form.removeRow(0)

"""Factory mapping SANE OptionDescriptors to Qt widgets — milestone 2.

  BOOL                 -> QCheckBox (QComboBox when "auto" is allowed)
  enum list constraint -> QComboBox
  RANGE constraint     -> QSlider + QSpinBox
  INTEGER/WORD         -> QSpinBox
  FLOAT                -> QDoubleSpinBox
  STRING               -> QLineEdit
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLineEdit,
    QSlider,
    QSpinBox,
    QWidget,
)

from scan_gui.models import OptionConstraint, OptionDescriptor, OptionType

# A slider is only worth it for small integer ranges.
_SLIDER_MAX_SPAN = 1000


class OptionWidget(QWidget):
    """Base class for the editor of a single option."""

    def __init__(self, descriptor: OptionDescriptor, parent=None):
        super().__init__(parent)
        self.descriptor = descriptor
        self._editor: QWidget | None = None
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

    def _install(self, *widgets: QWidget) -> None:
        for widget in widgets:
            self._layout.addWidget(widget)
        self._layout.addStretch(1)

    def value(self) -> str:
        """The current value as scanimage expects it."""
        raise NotImplementedError

    def set_value(self, value: str) -> None:
        """Apply a value; unknown values are ignored."""
        raise NotImplementedError


class BoolOptionWidget(OptionWidget):
    """A yes/no option, with an extra "auto" choice when allowed."""

    def __init__(self, descriptor: OptionDescriptor, parent=None):
        super().__init__(descriptor, parent)
        choices = descriptor.choices or ["yes", "no"]
        self._combo: QComboBox | None = None
        self._check: QCheckBox | None = None
        if len(choices) > 2:
            self._combo = QComboBox()
            self._combo.addItems(choices)
            self._install(self._combo)
            self._editor = self._combo
        else:
            self._check = QCheckBox()
            self._install(self._check)
            self._editor = self._check

    def value(self) -> str:
        if self._combo is not None:
            return self._combo.currentText()
        return "yes" if self._check.isChecked() else "no"

    def set_value(self, value: str) -> None:
        if self._combo is not None:
            index = self._combo.findText(value)
            if index >= 0:
                self._combo.setCurrentIndex(index)
        else:
            self._check.setChecked(value.strip().lower() in ("yes", "true", "on", "1"))


class ListOptionWidget(OptionWidget):
    """An option restricted to a fixed set of values."""

    def __init__(self, descriptor: OptionDescriptor, parent=None):
        super().__init__(descriptor, parent)
        self._combo = QComboBox()
        self._combo.addItems(descriptor.choices)
        self._install(self._combo)
        self._editor = self._combo

    def value(self) -> str:
        return self._combo.currentText()

    def set_value(self, value: str) -> None:
        index = self._combo.findText(value)
        if index >= 0:
            self._combo.setCurrentIndex(index)


class RangeOptionWidget(OptionWidget):
    """A numeric option bounded by a minimum and a maximum."""

    def __init__(self, descriptor: OptionDescriptor, parent=None):
        super().__init__(descriptor, parent)
        _, low, high, step = descriptor.constraint
        self._is_float = descriptor.type == OptionType.FLOAT
        self._slider: QSlider | None = None

        if self._is_float:
            self._spin = QDoubleSpinBox()
            self._spin.setDecimals(2)
            self._spin.setRange(low, high)
            self._spin.setSingleStep(step or 0.1)
        else:
            self._spin = QSpinBox()
            self._spin.setRange(int(low), int(high))
            self._spin.setSingleStep(int(step) if step else 1)

        if not self._is_float and step == 1 and (high - low) <= _SLIDER_MAX_SPAN:
            self._slider = QSlider(Qt.Orientation.Horizontal)
            self._slider.setRange(int(low), int(high))
            self._slider.valueChanged.connect(self._spin.setValue)
            self._spin.valueChanged.connect(self._slider.setValue)
            self._install(self._slider, self._spin)
        else:
            self._install(self._spin)
        self._editor = self._spin

    def value(self) -> str:
        if self._is_float:
            return f"{self._spin.value():g}"
        return str(self._spin.value())

    def set_value(self, value: str) -> None:
        try:
            number = float(value)
        except ValueError:
            return
        if self._is_float:
            self._spin.setValue(number)
        else:
            self._spin.setValue(int(number))


class TextOptionWidget(OptionWidget):
    """A free-form string option."""

    def __init__(self, descriptor: OptionDescriptor, parent=None):
        super().__init__(descriptor, parent)
        self._edit = QLineEdit()
        self._install(self._edit)
        self._editor = self._edit

    def value(self) -> str:
        return self._edit.text()

    def set_value(self, value: str) -> None:
        self._edit.setText(value)


def create_option_widget(descriptor: OptionDescriptor) -> OptionWidget:
    """Build the editor widget matching one option descriptor."""
    if descriptor.type == OptionType.BOOL:
        return BoolOptionWidget(descriptor)
    constraint = descriptor.constraint
    if constraint and constraint[0] == OptionConstraint.RANGE:
        return RangeOptionWidget(descriptor)
    if constraint and constraint[0] == OptionConstraint.LIST:
        return ListOptionWidget(descriptor)
    return TextOptionWidget(descriptor)

"""Factory mapping SANE OptionDescriptors to Qt widgets — milestone 2.

Planned mapping:
  BOOL               -> QCheckBox
  enum list constraint -> QComboBox
  RANGE constraint   -> QSlider + QSpinBox
  INTEGER/WORD       -> QSpinBox
  STRING             -> QLineEdit
"""

"""Plain data types shared across the app. Imports nothing from scan_gui."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Device:
    """A SANE device as reported by `scanimage -L`."""

    name: str        # e.g. "pixma:04A91913_5E2C64"
    description: str # e.g. "CANON Canon PIXMA MP610 Scanner"


# ---- Added in M2 (option editing) ----

class OptionType:
    BOOL = "BOOL"
    INTEGER = "INTEGER"
    WORD = "WORD"
    STRING = "STRING"
    FIXED = "FIXED"


@dataclass(frozen=True)
class OptionDescriptor:
    """One editable option of a SANE device, from `scanimage --get-options`."""

    name: str
    title: str
    description: str = ""
    type: str = OptionType.STRING
    unit: str = "NONE"
    current: str | None = None
    default: str | None = None
    # Constraint: None (none), ("RANGE", min, max, step), ("LIST", [values...])
    constraint: tuple | None = None


@dataclass(frozen=True)
class ScanProfile:
    """A named set of option values, e.g. 'Photos 1200dpi'."""

    name: str
    values: dict = field(default_factory=dict)

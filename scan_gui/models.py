"""Plain data types shared across the app. Imports nothing from scan_gui."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Device:
    """A SANE device as reported by `scanimage -L`."""

    name: str        # e.g. "pixma:04A91913_5E2C64"
    description: str # e.g. "CANON Canon PIXMA MP610 Scanner"


class OptionType:
    """The kind of value an option accepts."""

    BOOL = "BOOL"
    INTEGER = "INTEGER"
    FLOAT = "FLOAT"
    STRING = "STRING"
    FIXED = "FIXED"


class OptionConstraint:
    """The kind of constraint an option carries."""

    RANGE = "RANGE"
    LIST = "LIST"


@dataclass(frozen=True)
class OptionDescriptor:
    """One option of a SANE device, parsed from `scanimage -A`.

    `constraint` is one of:
        None                              -- free value
        (OptionConstraint.RANGE, min, max, step)
        (OptionConstraint.LIST, [values...])
    """

    name: str                 # SANE option name, e.g. "resolution"
    flag: str = ""            # command line form as printed, e.g. "--resolution"
    description: str = ""
    type: str = OptionType.STRING
    unit: str = "NONE"        # "dpi", "mm", "pel", "bit", "us", "%" or "NONE"
    current: str | None = None
    constraint: tuple | None = None
    read_only: bool = False
    advanced: bool = False
    inactive: bool = False
    hardware: bool = False

    @property
    def choices(self) -> list[str]:
        """Allowed values for a list constraint, empty otherwise."""
        if self.constraint and self.constraint[0] == OptionConstraint.LIST:
            return list(self.constraint[1])
        return []

    @property
    def is_numeric(self) -> bool:
        return self.type in (OptionType.INTEGER, OptionType.FLOAT)


@dataclass(frozen=True)
class ScanProfile:
    """A named set of option values, e.g. 'Photos 1200dpi'."""

    name: str
    values: dict = field(default_factory=dict)

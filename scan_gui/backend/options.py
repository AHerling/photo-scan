"""Option descriptors from `scanimage -A` — milestone 2.

`scanimage -A` (a.k.a. `--all-options`) prints one block per option:

    --resolution 50..600dpi (in steps of 50) [300]
        Sets the resolution of the scanned image in DPI

The layout comes from print_option() in sane-backends' tools/scanimage.c:
the option name (indented four spaces, a single dash for the t/l/x/y window
options), the constraint, the current value in brackets, optional flags such
as [advanced] or [read-only], then the description indented eight spaces.

parse_options() is a pure function so it can be unit-tested against captured
output in tests/fixtures/ without a scanner attached.

Layering rule for the backend: QtCore only, never QtWidgets.
"""

import re
from collections.abc import Iterable, Mapping

from PySide6.QtCore import QObject, QProcess, Signal

from scan_gui.models import OptionConstraint, OptionDescriptor, OptionType

ALL_OPTIONS_ARGS = ["-A"]

# An option header is indented by exactly four spaces and starts with the
# option name. Descriptions are indented eight spaces, so they never match.
_OPTION_RE = re.compile(r"^ {4}(?P<flag>-{1,2}[A-Za-z0-9][\w.-]*)(?P<rest>.*)$")

# Bracketed groups on an option line: the current value first, then flags.
_BRACKET_RE = re.compile(r"\[([^\]]*)\]")

# BOOL options print their constraint glued to the name: "[=(yes|no)]".
_BOOL_RE = re.compile(r"^\[=\((?P<choices>[^)]*)\)\]$")

# Range constraint: "50..600dpi", "0..215.9mm", "75..1200dpi (in steps of 1)".
_RANGE_RE = re.compile(
    r"^(?P<min>-?\d+(?:\.\d+)?)\.\.(?P<max>-?\d+(?:\.\d+)?)"
    r"(?P<unit>dpi|mm|pel|bit|us|%)?"
    r"(?:\s*\(in steps of (?P<step>-?\d+(?:\.\d+)?)\))?$"
)

# Placeholder printed for options that carry no constraint at all.
_FREE_TYPE_RE = re.compile(r"^<(?P<kind>int|float|string)>$")

# A unit glued to the last value of a word list, e.g. "75|150|300dpi".
_LIST_UNIT_RE = re.compile(r"^(?P<value>-?\d+(?:\.\d+)?)(?P<unit>dpi|mm|pel|bit|us|%)$")

# Flags scanimage appends after the current value.
_FLAGS = {
    "inactive": "inactive",
    "hardware": "hardware",
    "read-only": "read_only",
    "advanced": "advanced",
}


def parse_options(output: str) -> list[OptionDescriptor]:
    """Parse `scanimage -A` output into a list of option descriptors."""
    options: list[OptionDescriptor] = []
    header: re.Match | None = None
    description: list[str] = []

    for raw_line in output.splitlines():
        line = raw_line.rstrip()
        match = _OPTION_RE.match(line)
        if match:
            if header is not None:
                options.append(_build_option(header, description))
            header = match
            description = []
        elif header is not None and line.strip():
            description.append(line.strip())

    if header is not None:
        options.append(_build_option(header, description))
    return options


def build_option_arguments(
    options: Iterable[OptionDescriptor], values: Mapping[str, str]
) -> list[str]:
    """Turn `{option name: value}` into scanimage command line arguments."""
    arguments: list[str] = []
    for option in options:
        value = values.get(option.name)
        if value is None or value == "":
            continue
        arguments.append(option.flag or f"--{option.name}")
        arguments.append(str(value))
    return arguments


def _build_option(header: re.Match, description_lines: list[str]) -> OptionDescriptor:
    """Turn one parsed option block into a descriptor."""
    flag = header.group("flag")
    name = flag.lstrip("-")
    rest = header.group("rest")

    # BOOL options carry their constraint glued to the option name.
    attached = ""
    if rest.startswith("["):
        end = rest.find("]")
        if end != -1:
            attached = rest[: end + 1]
            rest = rest[end + 1 :]

    groups = _BRACKET_RE.findall(rest)
    if groups and groups[0] in _FLAGS:
        current: str | None = None
        flag_names = groups
    else:
        current = groups[0] if groups else None
        flag_names = groups[1:]

    option_type = OptionType.STRING
    unit = "NONE"
    constraint: tuple | None = None

    if attached:
        bool_match = _BOOL_RE.match(attached)
        choices = bool_match.group("choices").split("|") if bool_match else []
        option_type = OptionType.BOOL
        constraint = (OptionConstraint.LIST, choices)
    else:
        spec = _BRACKET_RE.sub("", rest).strip().removesuffix(",...").strip()
        range_match = _RANGE_RE.match(spec)
        free_match = _FREE_TYPE_RE.match(spec)
        if range_match:
            low = float(range_match.group("min"))
            high = float(range_match.group("max"))
            step_raw = range_match.group("step")
            integral = low == int(low) and high == int(high)
            step = float(step_raw) if step_raw else (1.0 if integral else 0.0)
            unit = range_match.group("unit") or "NONE"
            option_type = OptionType.INTEGER if integral else OptionType.FLOAT
            constraint = (OptionConstraint.RANGE, low, high, step)
        elif free_match:
            option_type = {
                "int": OptionType.INTEGER,
                "float": OptionType.FIXED,
                "string": OptionType.STRING,
            }[free_match.group("kind")]
        elif spec and not spec.startswith("{"):
            values, unit = _split_list(spec)
            constraint = (OptionConstraint.LIST, values)
            if all(_is_integer(value) for value in values):
                option_type = OptionType.INTEGER

    flags = {name for name in flag_names if name in _FLAGS}
    return OptionDescriptor(
        name=name,
        flag=flag,
        description=" ".join(description_lines),
        type=option_type,
        unit=unit,
        current=current,
        constraint=constraint,
        read_only="read-only" in flags,
        advanced="advanced" in flags,
        inactive="inactive" in flags,
        hardware="hardware" in flags,
    )


def _split_list(spec: str) -> tuple[list[str], str]:
    """Split a "a|b|c" constraint, peeling a unit off the last value."""
    values = spec.split("|")
    unit = "NONE"
    match = _LIST_UNIT_RE.match(values[-1])
    if match:
        values[-1] = match.group("value")
        unit = match.group("unit")
    return values, unit


def _is_integer(value: str) -> bool:
    try:
        int(value)
    except ValueError:
        return False
    return True


class OptionLoader(QObject):
    """Runs `scanimage -d <device> -A` asynchronously."""

    load_started = Signal()
    load_finished = Signal(list)  # list[OptionDescriptor]
    load_failed = Signal(str)    # human-readable message

    def __init__(self, parent=None):
        super().__init__(parent)
        self._process = QProcess(self)
        self._process.finished.connect(self._on_finished)
        self._process.errorOccurred.connect(self._on_error)

    @property
    def busy(self) -> bool:
        return self._process.state() != QProcess.ProcessState.NotRunning

    def load(self, device: str) -> None:
        """Start loading the options of `device`. Ignored if one is running."""
        if self.busy:
            return
        self.load_started.emit()
        self._process.start("scanimage", ["-d", device] + ALL_OPTIONS_ARGS)

    def stop(self) -> None:
        """Kill any in-flight scanimage process (call on window close)."""
        if self.busy:
            self._process.kill()
            self._process.waitForFinished(1000)

    def _on_finished(self, exit_code: int, _status) -> None:
        stdout = self._process.readAllStandardOutput().data().decode("utf-8", "replace")
        if exit_code != 0:
            stderr = self._process.readAllStandardError().data().decode("utf-8", "replace")
            self.load_failed.emit(
                stderr.strip() or f"scanimage -A exited with code {exit_code}"
            )
            return
        self.load_finished.emit(parse_options(stdout))

    def _on_error(self, error: QProcess.ProcessError) -> None:
        if error == QProcess.ProcessError.FailedToStart:
            self.load_failed.emit(
                "Could not run scanimage. Is sane-backends installed?"
            )

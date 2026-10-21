"""The drop-down contents of the simple mode.

The simple mode replaces the full option form with three drop-downs — the
scanner, the colour and the resolution. This module derives the colour and
the resolution lists from a scanner's option descriptors, so it stays pure
Python and can be unit tested without Qt or a scanner.

The colour list runs from full colour down to black and white, the
resolution list from the highest to the lowest, as the simple mode promises.
"""

import re
from dataclasses import dataclass

from scan_gui.models import OptionConstraint, OptionDescriptor

# Friendly names for the scan modes we know, with their rank: full colour
# first, greyscale next, black and white last. Unknown modes keep the order
# the scanner reported them in.
_MODE_LABELS: dict[str, tuple[str, int]] = {
    "color": ("Full colour", 0),
    "colour": ("Full colour", 0),
    "rgb": ("Full colour", 0),
    "24bit": ("Full colour", 0),
    "truecolor": ("Full colour", 0),
    "gray": ("Greyscale", 1),
    "grey": ("Greyscale", 1),
    "grayscale": ("Greyscale", 1),
    "greyscale": ("Greyscale", 1),
    "8bit": ("Greyscale", 1),
    "lineart": ("Black & white", 2),
    "mono": ("Black & white", 2),
    "monochrome": ("Black & white", 2),
    "bw": ("Black & white", 2),
    "blackwhite": ("Black & white", 2),
    "1bit": ("Black & white", 2),
}

# The resolutions the simple mode offers, highest first. Which of them a
# scanner accepts depends on its own range.
_RESOLUTION_PRESETS = (1200, 600, 300, 200, 150, 100, 75, 50)

# The bit depths offered when a scanner has no scan mode of its own.
_BIT_DEPTH_PRESETS = (16, 12, 8, 4, 1)


@dataclass(frozen=True)
class SimpleChoice:
    """One entry of a simple mode drop-down."""

    label: str   # what the user reads
    value: str   # what scanimage is given
    option: str  # the SANE option it belongs to


def colour_choices(options: list[OptionDescriptor]) -> list[SimpleChoice]:
    """The colour choices: full colour first, black and white last.

    Uses the scanner's scan mode (`--mode`); scanners without one fall back
    to their bit depth (`--bit-depth`). An empty list means the scanner does
    not offer the choice at all.
    """
    mode = find_option(options, "mode")
    if mode is not None:
        values = option_values(mode)
        if values:
            ranked = sorted(values, key=_mode_rank)
            return [SimpleChoice(_mode_label(value), value, mode.name) for value in ranked]

    depth = find_option(options, "bit-depth")
    if depth is not None:
        values = option_values(depth)
        if values:
            ordered = sorted(values, key=_as_int, reverse=True)
            return [SimpleChoice(f"{value} bit", value, depth.name) for value in ordered]
    return []


def resolution_choices(options: list[OptionDescriptor]) -> list[SimpleChoice]:
    """The resolution choices: highest first."""
    resolution = find_option(options, "resolution")
    if resolution is None:
        return []
    values = option_values(resolution)
    if not values:
        return []
    ordered = sorted(values, key=_as_int, reverse=True)
    return [SimpleChoice(f"{value} dpi", value, resolution.name) for value in ordered]


def find_option(options: list[OptionDescriptor], name: str) -> OptionDescriptor | None:
    """Find an option by name, ignoring case and dashes."""
    wanted = _normalise(name)
    for option in options:
        if _normalise(option.name) == wanted:
            return option
    return None


def option_values(option: OptionDescriptor) -> list[str]:
    """The values an option allows, as strings.

    A list constraint gives its values directly, a range constraint the
    well-known steps that fit inside it.
    """
    constraint = option.constraint
    if not constraint:
        return []
    if constraint[0] == OptionConstraint.LIST:
        return list(constraint[1])
    if constraint[0] == OptionConstraint.RANGE:
        _, low, high, step = constraint
        presets = (
            _RESOLUTION_PRESETS if option.unit == "dpi" else _BIT_DEPTH_PRESETS
        )
        values = [value for value in presets if _in_range(value, low, high, step)]
        for extra in (high, low):
            if _in_range(extra, low, high, step) and extra not in values:
                values.append(extra)
        return sorted({int(value) for value in values}, reverse=True)
    return []


def _in_range(value: float, low: float, high: float, step: float) -> bool:
    if not low <= value <= high:
        return False
    if not step or step == 1:
        return True
    return (value - low) % step == 0


def _mode_rank(value: str) -> int:
    return _MODE_LABELS.get(_normalise(value), (value, 3))[1]


def _mode_label(value: str) -> str:
    return _MODE_LABELS.get(_normalise(value), (value, 3))[0]


def _normalise(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _as_int(value: str) -> int:
    try:
        return int(value)
    except ValueError:
        return 0

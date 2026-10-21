"""The scan area: from a picked rectangle to scanner values.

The preview shows the whole scan bed at the lowest resolution; what the user
drags on that picture is a rectangle in the picture's own pixels. The
scanner wants millimetres, so the rectangle is scaled by the size of the bed.

Backends name the area options differently — the pixma backend uses
`-l/-t/-x/-y`, the epson2 backend `--tl-x/--tl-y/--br-x/--br-y` — so both
are understood.

Layering rule for the backend: QtCore only, never QtWidgets.
"""

from dataclasses import dataclass

from PySide6.QtCore import QRect, QSize

from scan_gui.models import OptionConstraint, OptionDescriptor


@dataclass(frozen=True)
class AreaOptions:
    """The option names one backend uses for the scan area."""

    left: str
    top: str
    width: str = ""
    height: str = ""
    right: str = ""
    bottom: str = ""


def find_area_options(options: list[OptionDescriptor]) -> AreaOptions | None:
    """Find the options that describe the scan area, whatever they are called."""
    names = {option.name for option in options}
    if {"l", "t", "x", "y"} <= names:
        return AreaOptions(left="l", top="t", width="x", height="y")
    if {"tl-x", "tl-y", "br-x", "br-y"} <= names:
        return AreaOptions(left="tl-x", top="tl-y", right="br-x", bottom="br-y")
    return None


def option_maximum(option: OptionDescriptor) -> float:
    """The largest value an option accepts, 0 when that is unknown."""
    constraint = option.constraint
    if not constraint:
        return 0.0
    if constraint[0] == OptionConstraint.RANGE:
        return float(constraint[2])
    if constraint[0] == OptionConstraint.LIST:
        numbers = [float(value) for value in constraint[1] if _is_number(value)]
        return max(numbers) if numbers else 0.0
    return 0.0


def bed_size(options: list[OptionDescriptor]) -> tuple[float, float]:
    """The full width and height of the scan bed, in millimetres."""
    area = find_area_options(options)
    if area is None:
        return 0.0, 0.0
    by_name = {option.name: option for option in options}
    width_name = area.width or area.right
    height_name = area.height or area.bottom
    if width_name not in by_name or height_name not in by_name:
        return 0.0, 0.0
    return (
        option_maximum(by_name[width_name]),
        option_maximum(by_name[height_name]),
    )


def full_bed_values(options: list[OptionDescriptor]) -> dict[str, str]:
    """The area option values that cover the whole bed."""
    area = find_area_options(options)
    if area is None:
        return {}
    by_name = {option.name: option for option in options}
    values = {area.left: "0", area.top: "0"}
    if area.width:
        values[area.width] = _format(option_maximum(by_name[area.width]))
        values[area.height] = _format(option_maximum(by_name[area.height]))
    else:
        values[area.right] = _format(option_maximum(by_name[area.right]))
        values[area.bottom] = _format(option_maximum(by_name[area.bottom]))
    return values


def selection_values(
    selection: QRect,
    image_size: QSize,
    bed: tuple[float, float],
    area: AreaOptions,
) -> dict[str, str]:
    """The scanner values for the area the user picked on the preview."""
    if image_size.width() <= 0 or image_size.height() <= 0:
        return {}
    bed_width, bed_height = bed
    millimetres_x = bed_width / image_size.width()
    millimetres_y = bed_height / image_size.height()

    left = selection.left() * millimetres_x
    top = selection.top() * millimetres_y
    width = selection.width() * millimetres_x
    height = selection.height() * millimetres_y

    values = {area.left: _format(left), area.top: _format(top)}
    if area.width:
        values[area.width] = _format(width)
        values[area.height] = _format(height)
    else:
        values[area.right] = _format(left + width)
        values[area.bottom] = _format(top + height)
    return values


def _format(value: float) -> str:
    """Millimetres, the way scanimage wants them."""
    return f"{value:.2f}"


def _is_number(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True

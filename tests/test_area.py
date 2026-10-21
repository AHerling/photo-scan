"""Tests for the area/picked-region helpers."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from PySide6.QtCore import QRect, QSize

from scan_gui.backend import area
from scan_gui.models import OptionConstraint, OptionDescriptor, OptionType


def _desc(name, constraint=None, flag=None):
    return OptionDescriptor(
        name=name,
        flag=flag or f"-{name}",
        description="",
        type=OptionType.STRING,
        unit="mm",
        current="0",
        constraint=constraint,
        read_only=False,
        advanced=False,
        inactive=False,
        hardware=False,
    )


class AreaTests(TestCase):
    def test_find_area_options_l_t_x_y(self):
        options = [
            _desc("l", (OptionConstraint.RANGE, 0, 216, 0)),
            _desc("t", (OptionConstraint.RANGE, 0, 297, 0)),
            _desc("x", (OptionConstraint.RANGE, 0, 216, 0)),
            _desc("y", (OptionConstraint.RANGE, 0, 297, 0)),
        ]
        a = area.find_area_options(options)
        self.assertIsNotNone(a)
        self.assertEqual(a.left, "l")
        self.assertEqual(a.width, "x")

    def test_find_area_options_tl_br(self):
        options = [
            _desc("tl-x", (OptionConstraint.RANGE, 0, 210, 0)),
            _desc("tl-y", (OptionConstraint.RANGE, 0, 297, 0)),
            _desc("br-x", (OptionConstraint.RANGE, 0, 210, 0)),
            _desc("br-y", (OptionConstraint.RANGE, 0, 297, 0)),
        ]
        a = area.find_area_options(options)
        self.assertIsNotNone(a)
        self.assertEqual(a.right, "br-x")

    def test_bed_size(self):
        options = [
            _desc("l", (OptionConstraint.RANGE, 0, 216, 0)),
            _desc("t", (OptionConstraint.RANGE, 0, 297, 0)),
            _desc("x", (OptionConstraint.RANGE, 0, 216, 0)),
            _desc("y", (OptionConstraint.RANGE, 0, 297, 0)),
        ]
        self.assertEqual(area.bed_size(options), (216, 297))

    def test_full_bed_values(self):
        options = [
            _desc("l", (OptionConstraint.RANGE, 0, 216, 0)),
            _desc("t", (OptionConstraint.RANGE, 0, 297, 0)),
            _desc("x", (OptionConstraint.RANGE, 0, 216, 0)),
            _desc("y", (OptionConstraint.RANGE, 0, 297, 0)),
        ]
        self.assertEqual(area.full_bed_values(options), {"l": "0", "t": "0", "x": "216.00", "y": "297.00"})

    def test_selection_values_l_t_x_y(self):
        options = [
            _desc("l", (OptionConstraint.RANGE, 0, 216, 0)),
            _desc("t", (OptionConstraint.RANGE, 0, 297, 0)),
            _desc("x", (OptionConstraint.RANGE, 0, 216, 0)),
            _desc("y", (OptionConstraint.RANGE, 0, 297, 0)),
        ]
        a = area.find_area_options(options)
        bed = area.bed_size(options)
        # A 100x100 rectangle in the middle of a 200x200 preview
        values = area.selection_values(QRect(50, 50, 100, 100), QSize(200, 200), bed, a)
        self.assertEqual(values["l"], "54.00")
        self.assertEqual(values["t"], "74.25")
        self.assertEqual(values["x"], "108.00")
        self.assertEqual(values["y"], "148.50")

    def test_selection_values_tl_br(self):
        options = [
            _desc("tl-x", (OptionConstraint.RANGE, 0, 210, 0)),
            _desc("tl-y", (OptionConstraint.RANGE, 0, 297, 0)),
            _desc("br-x", (OptionConstraint.RANGE, 0, 210, 0)),
            _desc("br-y", (OptionConstraint.RANGE, 0, 297, 0)),
        ]
        a = area.find_area_options(options)
        bed = area.bed_size(options)
        values = area.selection_values(QRect(0, 0, 100, 50), QSize(100, 100), bed, a)
        self.assertEqual(values["tl-x"], "0.00")
        self.assertEqual(values["br-x"], "210.00")
        self.assertEqual(values["br-y"], "148.50")

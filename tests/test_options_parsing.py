import unittest
from pathlib import Path

from scan_gui.backend.options import build_option_arguments, parse_options
from scan_gui.models import OptionConstraint, OptionType

FIXTURES = Path(__file__).parent / "fixtures"
VIRTUAL = FIXTURES / "scanimage_A_virtual.txt"    # real capture
PIXMA = FIXTURES / "scanimage_A_pixma.txt"        # hand written, see file header


def by_name(options):
    return {option.name: option for option in options}


class ParseVirtualScannerTest(unittest.TestCase):
    """The fixture was captured from `scanimage -d virtual:virtual_scanner -A`."""

    def setUp(self):
        self.options = parse_options(VIRTUAL.read_text(encoding="utf-8"))
        self.by_name = by_name(self.options)

    def test_parses_every_option_in_order(self):
        self.assertEqual(
            [option.name for option in self.options],
            ["mode", "resolution", "l", "t", "x", "y"],
        )

    def test_string_list_option(self):
        mode = self.by_name["mode"]
        self.assertEqual(mode.flag, "--mode")
        self.assertEqual(mode.type, OptionType.STRING)
        self.assertEqual(mode.constraint, (OptionConstraint.LIST, ["Color"]))
        self.assertEqual(mode.current, "Color")
        self.assertEqual(mode.description, "Selects the scan mode (Color)")

    def test_integer_range_with_unit_and_step(self):
        resolution = self.by_name["resolution"]
        self.assertEqual(resolution.type, OptionType.INTEGER)
        self.assertEqual(resolution.constraint, (OptionConstraint.RANGE, 50.0, 600.0, 50.0))
        self.assertEqual(resolution.unit, "dpi")
        self.assertEqual(resolution.current, "300")

    def test_fractional_range_is_float(self):
        left = self.by_name["l"]
        self.assertEqual(left.type, OptionType.FLOAT)
        self.assertEqual(left.constraint, (OptionConstraint.RANGE, 0.0, 215.9, 0.0))
        self.assertEqual(left.unit, "mm")
        self.assertEqual(left.flag, "-l")

    def test_descriptions_are_joined(self):
        self.assertEqual(self.by_name["y"].description, "Height of scan-area.")


class ParsePixmaFixtureTest(unittest.TestCase):
    """The pixma fixture mimics the layout printed by sane-backends."""

    def setUp(self):
        self.options = parse_options(PIXMA.read_text(encoding="utf-8"))
        self.by_name = by_name(self.options)

    def test_multi_value_list(self):
        mode = self.by_name["mode"]
        self.assertEqual(mode.constraint, (OptionConstraint.LIST, ["Color", "Gray", "Lineart"]))
        self.assertEqual(mode.current, "Color")

    def test_bool_option_with_attached_constraint(self):
        gamma = self.by_name["gamma-correction"]
        self.assertEqual(gamma.type, OptionType.BOOL)
        self.assertEqual(gamma.constraint, (OptionConstraint.LIST, ["yes", "no"]))
        self.assertEqual(gamma.current, "yes")

    def test_flags_are_read(self):
        self.assertTrue(self.by_name["exposure"].read_only)
        self.assertTrue(self.by_name["warmup-lamp"].hardware)
        self.assertTrue(self.by_name["auto-focus"].inactive)
        self.assertTrue(self.by_name["advanced-calibration"].advanced)
        self.assertFalse(self.by_name["mode"].read_only)

    def test_inactive_option_has_no_current_value(self):
        self.assertIsNone(self.by_name["auto-focus"].current)

    def test_free_string_option_has_no_constraint(self):
        lid = self.by_name["sensor-lid-color"]
        self.assertEqual(lid.type, OptionType.STRING)
        self.assertIsNone(lid.constraint)
        self.assertEqual(lid.current, "white")

    def test_free_int_option(self):
        focus = self.by_name["auto-focus"]
        self.assertEqual(focus.type, OptionType.INTEGER)
        self.assertIsNone(focus.constraint)

    def test_percent_unit_range(self):
        brightness = self.by_name["brightness"]
        self.assertEqual(brightness.unit, "%")
        self.assertEqual(brightness.constraint, (OptionConstraint.RANGE, -100.0, 100.0, 1.0))


class ParseRobustnessTest(unittest.TestCase):
    def test_empty_output_yields_no_options(self):
        self.assertEqual(parse_options(""), [])
        self.assertEqual(parse_options("\n\n"), [])

    def test_noise_lines_are_ignored(self):
        output = (
            "scanimage: rounded value of br-x from 215.9 to 215.9\n"
            "All options specific to device `x':\n"
            "    --mode Color [Color]\n"
            "        Selects the scan mode (Color)\n"
        )
        options = parse_options(output)
        self.assertEqual([option.name for option in options], ["mode"])

    def test_group_headers_are_ignored(self):
        output = "  Scan Mode:\n    --mode Color [Color]\n        Pick a mode\n"
        options = parse_options(output)
        self.assertEqual([option.name for option in options], ["mode"])

    def test_description_continuation_lines_are_joined(self):
        output = (
            "    --resolution 75..1200dpi (in steps of 1) [75]\n"
            "        Sets the resolution of the\n"
            "        scanned image in DPI\n"
        )
        options = parse_options(output)
        self.assertEqual(options[0].description, "Sets the resolution of the scanned image in DPI")


class BuildArgumentsTest(unittest.TestCase):
    def test_uses_the_printed_flag_and_skips_empty_values(self):
        options = parse_options(VIRTUAL.read_text(encoding="utf-8"))
        arguments = build_option_arguments(options, {"resolution": "1200", "mode": "Color", "l": ""})
        # Arguments follow the scanner's option order, not the dict order.
        self.assertEqual(arguments, ["--mode", "Color", "--resolution", "1200"])

    def test_single_letter_options_keep_their_short_flag(self):
        options = parse_options(VIRTUAL.read_text(encoding="utf-8"))
        arguments = build_option_arguments(options, {"l": "0"})
        self.assertEqual(arguments, ["-l", "0"])


if __name__ == "__main__":
    unittest.main()

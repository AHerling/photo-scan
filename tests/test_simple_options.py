"""Tests for the simple mode's drop-down contents."""

import unittest
from pathlib import Path

from scan_gui.backend.options import parse_options
from scan_gui.simple_options import colour_choices, resolution_choices

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> list:
    return parse_options((FIXTURES / name).read_text(encoding="utf-8"))


class ColourChoiceTest(unittest.TestCase):
    def test_modes_run_from_full_colour_to_black_and_white(self):
        choices = colour_choices(load("scanimage_A_pixma.txt"))
        self.assertEqual(
            [choice.value for choice in choices], ["Color", "Gray", "Lineart"]
        )
        self.assertEqual(
            [choice.label for choice in choices],
            ["Full colour", "Greyscale", "Black & white"],
        )

    def test_the_option_name_is_kept(self):
        choices = colour_choices(load("scanimage_A_pixma.txt"))
        self.assertTrue(all(choice.option == "mode" for choice in choices))

    def test_a_scanner_with_one_mode(self):
        choices = colour_choices(load("scanimage_A_virtual.txt"))
        self.assertEqual([choice.value for choice in choices], ["Color"])

    def test_no_colour_option_means_no_choices(self):
        options = load("scanimage_A_pixma.txt")
        without_mode = [
            option for option in options if option.name != "mode"
        ]
        self.assertEqual(colour_choices(without_mode), [])

    def test_bit_depth_is_the_fallback(self):
        from scan_gui.models import OptionConstraint, OptionDescriptor

        options = [
            OptionDescriptor(
                name="bit-depth",
                flag="--bit-depth",
                type="INTEGER",
                unit="bit",
                current="8",
                constraint=(OptionConstraint.LIST, ["1", "8", "16"]),
            )
        ]
        choices = colour_choices(options)
        self.assertEqual([choice.value for choice in choices], ["16", "8", "1"])
        self.assertEqual(choices[0].label, "16 bit")
        self.assertEqual(choices[0].option, "bit-depth")


class ResolutionChoiceTest(unittest.TestCase):
    def test_resolutions_run_from_highest_to_lowest(self):
        choices = resolution_choices(load("scanimage_A_pixma.txt"))
        values = [int(choice.value) for choice in choices]
        self.assertEqual(values, sorted(values, reverse=True))
        self.assertEqual(values[0], 1200)
        self.assertIn(300, values)
        self.assertIn(75, values)

    def test_only_steps_the_scanner_accepts(self):
        # The virtual scanner allows 50..600 in steps of 50, so 75 is out.
        choices = resolution_choices(load("scanimage_A_virtual.txt"))
        values = [int(choice.value) for choice in choices]
        self.assertEqual(values, [600, 300, 200, 150, 100, 50])
        self.assertNotIn(75, values)

    def test_the_label_carries_the_unit(self):
        choices = resolution_choices(load("scanimage_A_pixma.txt"))
        self.assertTrue(choices[0].label.endswith(" dpi"))

    def test_no_resolution_option_means_no_choices(self):
        options = [
            option
            for option in load("scanimage_A_pixma.txt")
            if option.name != "resolution"
        ]
        self.assertEqual(resolution_choices(options), [])


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path

from scan_gui.backend.options import parse_options
from scan_gui.backend.scan import (
    build_scan_command,
    next_output_path,
    parse_progress,
    split_chunks,
)

FIXTURE = Path(__file__).parent / "fixtures" / "scanimage_A_virtual.txt"


class ProgressTest(unittest.TestCase):
    def test_parses_a_progress_message(self):
        self.assertEqual(parse_progress("Progress: 42.5%"), 42)
        self.assertEqual(parse_progress("Progress: 100.0%"), 100)
        self.assertEqual(parse_progress("Progress: 0%"), 0)

    def test_ignores_other_messages(self):
        self.assertIsNone(parse_progress("scanimage: rounded value of br-x"))
        self.assertIsNone(parse_progress(""))


class SplitChunksTest(unittest.TestCase):
    def test_progress_messages_are_separated_by_carriage_returns(self):
        chunks, remainder = split_chunks("Progress: 3.9%\rProgress: 7.8%\r")
        self.assertEqual(chunks, ["Progress: 3.9%", "Progress: 7.8%"])
        self.assertEqual(remainder, "")

    def test_lines_are_separated_by_newlines(self):
        chunks, remainder = split_chunks("first\nsecond\n")
        self.assertEqual(chunks, ["first", "second"])
        self.assertEqual(remainder, "")

    def test_the_incomplete_tail_is_kept(self):
        chunks, remainder = split_chunks("done\nhalf")
        self.assertEqual(chunks, ["done"])
        self.assertEqual(remainder, "half")

    def test_final_flushes_the_tail(self):
        chunks, remainder = split_chunks("half", final=True)
        self.assertEqual(chunks, ["half"])
        self.assertEqual(remainder, "")


class NextOutputPathTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.directory = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_empty_directory_starts_at_one(self):
        self.assertEqual(next_output_path(self.directory), self.directory / "000001.tiff")

    def test_counts_up_from_the_highest_number(self):
        (self.directory / "000001.tiff").touch()
        (self.directory / "000007.tiff").touch()
        self.assertEqual(next_output_path(self.directory), self.directory / "000008.tiff")

    def test_ignores_other_files(self):
        (self.directory / "scan.jpg").touch()
        (self.directory / "notes.txt").touch()
        (self.directory / "12.tiff").touch()
        self.assertEqual(next_output_path(self.directory), self.directory / "000001.tiff")

    def test_ignores_other_extensions(self):
        (self.directory / "000005.jpg").touch()
        self.assertEqual(next_output_path(self.directory), self.directory / "000001.tiff")

    def test_creates_the_directory(self):
        target = self.directory / "raw"
        self.assertEqual(next_output_path(target), target / "000001.tiff")
        self.assertTrue(target.is_dir())


class BuildScanCommandTest(unittest.TestCase):
    def setUp(self):
        self.options = parse_options(FIXTURE.read_text(encoding="utf-8"))

    def test_command_contains_device_format_and_output(self):
        command = build_scan_command("virtual:virtual_scanner", self.options, {}, Path("/tmp/000001.tiff"))
        self.assertEqual(command[0], "scanimage")
        self.assertIn("-d", command)
        self.assertIn("virtual:virtual_scanner", command)
        self.assertIn("--format", command)
        self.assertIn("tiff", command)
        self.assertIn("--progress", command)
        self.assertIn("/tmp/000001.tiff", command)

    def test_option_values_are_appended(self):
        command = build_scan_command(
            "virtual:virtual_scanner", self.options, {"resolution": "1200"}, Path("/tmp/000001.tiff")
        )
        self.assertEqual(command[-2:], ["--resolution", "1200"])


if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path

from scan_gui.backend.devices import parse_devices

FIXTURE = Path(__file__).parent / "fixtures" / "scanimage_L.txt"


class ParseDevicesTest(unittest.TestCase):
    def test_parses_devices_and_skips_noise(self):
        devices = parse_devices(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(
            [d.name for d in devices],
            [
                "pixma:04A91913_5E2C64",
                "escl:https://192.168.1.10:443/eSCL/",
                "dnssd://HP%20LaserJet%20M277._ipp._tcp.local/",
            ],
        )
        self.assertEqual(devices[0].description, "CANON Canon PIXMA MP610 Scanner")
        self.assertEqual(
            devices[2].description, "HP LaserJet MFP (driver:hplip)"
        )

    def test_deduplicates_repeated_device_lines(self):
        devices = parse_devices(FIXTURE.read_text(encoding="utf-8"))
        names = [d.name for d in devices]
        self.assertEqual(len(names), len(set(names)))

    def test_empty_output_yields_no_devices(self):
        self.assertEqual(parse_devices(""), [])
        self.assertEqual(parse_devices("No scanners were identified.\n"), [])

    def test_warning_lines_are_ignored(self):
        output = "[W] some backend warning\ndevice `x' is a Test Scanner\n"
        devices = parse_devices(output)
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0].name, "x")

    def test_parses_airscan_eSCL_devices(self):
        output = (Path(__file__).parent / "fixtures" / "scanimage_L_airscan.txt").read_text(
            encoding="utf-8"
        )
        devices = parse_devices(output)
        self.assertEqual(len(devices), 3)
        self.assertEqual(devices[0].name, "escl:https://192.168.1.50:443/eSCL/Scanner")
        self.assertIn("HP", devices[0].description)
        self.assertEqual(devices[1].name, "airscan:w0:Brother MFC")
        self.assertEqual(devices[2].name, "net:192.168.1.60:escl")


if __name__ == "__main__":
    unittest.main()

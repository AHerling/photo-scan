# scan-gui

Qt6 (PySide6) desktop GUI for SANE scanners on Fedora.

Discover scanner devices, edit their SANE options, run scans, and
automatically detect and crop photographs from the scanned image — a GUI
successor to `scan.sh`.

**Status:** milestone 4 — device discovery, option editing, scanning and
photo detection. See [STRUCTURE.md](STRUCTURE.md) for the full plan.

## Dependencies (Fedora)

All via system packages — no venv or pip needed:

```bash
sudo dnf install python3-pyside6 python3-opencv sane-backends
```

## Run

```bash
python3 -m scan_gui
```

The **Scanner** page lists the devices reported by `scanimage -L`; pick one
and the **Options** page is filled with the scanner's own options, read from
`scanimage -A`. Options can be changed, applied, and stored as named presets
(in `~/.config/scan-gui/config.json`).

`scanimage -L` takes a few seconds to probe the backends, so the device list
appears after a short delay.

The **Scan** page starts a scan with the options from the **Options** page:
the raw TIFF goes to the output folder (`/home/cain` by default — click the
folder to change it) as `000001.tiff`, `000002.tiff`, …, the progress bar is
fed by `scanimage --progress`, and Cancel kills the scanner. A lock file keeps
two scans from colliding, the same way the old `scan.sh` did.

When the scan finishes, the **Results** page looks for photographs in the
scanned image and cuts them out — the detection and cropping ported from
`scan.sh`'s embedded Python block. The photos are written to the photo folder
as `000001.jpg`, `000002.jpg`, … and previewed in a thumbnail grid; the app
switches to that page on its own. Detection runs in a background thread, so the
window stays responsive, and a page without photographs simply says so.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

Tests run against captured `scanimage` output fixtures — no scanner required.

The tests/fixtures folder holds one real capture (`scanimage_A_virtual.txt`,
from sane-backends' virtual scanner) and one hand-written fixture
(`scanimage_A_pixma.txt`) that mimics the layout of a Canon PIXMA.

The photo tests build synthetic pages (a white sheet with dark rectangles) and
run them through the real OpenCV pipeline, so detection and cropping are
covered without a scanner as well.

## Roadmap

- **M1** App skeleton, device discovery, device selection — *done*
- **M2** Option form generated from the scanner's SANE options, presets — *done*
- **M3** Async scanning with progress and cancel — *done*
- **M4** Photo detection + cropping with result preview — *done*
- **M5** Desktop integration and RPM packaging — *next*

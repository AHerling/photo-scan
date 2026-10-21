# scan-gui

Qt6 (PySide6) desktop GUI for SANE scanners on Fedora.

Discover scanner devices, edit their SANE options, run scans, and
automatically detect and crop photographs from the scanned image — a GUI
successor to `scan.sh`.

**Status:** milestone 3 — device discovery, option editing and scanning.
See [STRUCTURE.md](STRUCTURE.md) for the full plan.

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
the raw TIFF goes to `raw_dir` (`~/Scan/Raw` by default) as `000001.tiff`,
`000002.tiff`, …, the progress bar is fed by `scanimage --progress`, and
Cancel kills the scanner. A lock file keeps two scans from colliding, the
same way the old `scan.sh` did. The **Results** page is still a placeholder.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

Tests run against captured `scanimage` output fixtures — no scanner required.

The tests/fixtures folder holds one real capture (`scanimage_A_virtual.txt`,
from sane-backends' virtual scanner) and one hand-written fixture
(`scanimage_A_pixma.txt`) that mimics the layout of a Canon PIXMA.

## Roadmap

- **M1** App skeleton, device discovery, device selection — *done*
- **M2** Option form generated from the scanner's SANE options, presets — *done*
- **M3** Async scanning with progress and cancel — *done*
- **M4** Photo detection + cropping with result preview — *next*
- **M5** Desktop integration and RPM packaging

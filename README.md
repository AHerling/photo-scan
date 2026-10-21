# scan-gui

Qt6 (PySide6) desktop GUI for SANE scanners on Fedora.

Discover scanner devices, edit their SANE options, run scans, and
automatically detect and crop photographs from the scanned image — a GUI
successor to `scan.sh`.

**Status:** milestone 1 — device discovery and selection.
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

## Tests

```bash
python3 -m unittest discover -s tests -v
```

Tests run against captured `scanimage` output fixtures — no scanner required.

## Roadmap

- **M1** App skeleton, device discovery, device selection ← *current*
- **M2** Option form generated from the scanner's SANE options, presets
- **M3** Async scanning with progress and cancel
- **M4** Photo detection + cropping with result preview
- **M5** Desktop integration and RPM packaging

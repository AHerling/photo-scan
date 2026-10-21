# scan-gui — Structure & Plan

Qt6 (PySide6) desktop GUI for SANE scanners on Fedora: discover devices, edit
scanner options, run scans, and automatically detect + crop photographs from
the scanned image (the pipeline that started life in `scan.sh`).

## Decisions (locked in)

| Decision | Choice | Why |
|---|---|---|
| GUI toolkit | **Qt6 / PySide6** (system RPM `python3-pyside6`) | Already installed on target machine, mature widgets, good async primitives |
| SANE access | **`scanimage` subprocess** via `QProcess` | No new dependencies, process isolation, trivial cancellation (`kill()`), matches existing `scan.sh` |
| Dependencies | **System Python + RPMs** (`python3-pyside6`, `python3-opencv`, `sane-backends`) | Everything already present on Fedora; no venv needed |
| Scope | All 5 milestones, photo detection/crop included | Full replacement for `scan.sh` |

## Directory layout (target)

```
printer-gui/
├── pyproject.toml                  # metadata; deps are RPMs, not pip
├── README.md
├── STRUCTURE.md                    # this file
├── scan_gui/
│   ├── __main__.py                 # entry: python3 -m scan_gui
│   ├── app.py                      # QApplication, Fusion style, MainWindow
│   ├── config.py                   # JSON settings in ~/.config/scan-gui/ (last device, dirs, presets)
│   ├── models.py                   # dataclasses: Device, OptionDescriptor, OptionType, ScanProfile
│   ├── state.py                    # AppState enum + AppStateMachine (signals on transitions)
│   ├── backend/                    # ALL scanimage access — QtCore only, never QtWidgets
│   │   ├── devices.py              # `scanimage -L` parsing + async DeviceScanner (QProcess)
│   │   ├── options.py              # `--get-options` parsing → OptionDescriptors; builds -o args (M2)
│   │   └── scan.py                 # ScanJob: QProcess wrapper, progress parsing, cancel (M3)
│   ├── processing/
│   │   ├── photos.py               # detect + crop photographs (ported from scan.sh's python block)
│   │   └── worker.py               # QRunnable wrapper so OpenCV never blocks the UI (M4)
│   └── ui/                         # imports backend + models; never builds scanimage commands itself
│       ├── main_window.py          # QMainWindow: nav sidebar + QStackedWidget + status bar
│       ├── pages/
│       │   ├── device_page.py      # scanner list, refresh (M1 — done)
│       │   ├── options_page.py     # generated option form, Apply, presets (M2)
│       │   ├── scan_page.py        # Start/Cancel, progress bar, log (M3)
│       │   └── results_page.py     # preview grid of cropped photos (M4)
│       └── widgets/
│           └── option_widgets.py   # factory: OptionDescriptor → Qt widget (M2)
├── data/                           # .desktop file, icons (M5)
├── packaging/
│   └── scan-gui.spec               # RPM spec (M5)
└── tests/
    ├── fixtures/                   # captured scanimage output (no hardware needed)
    ├── test_devices_parsing.py
    ├── test_options_parsing.py     # M2
    └── test_photos.py              # M4
```

## Layering rules

1. `ui → backend/processing/models`. The UI never constructs `scanimage`
   commands or parses its output.
2. `backend` may import **QtCore only** (QProcess, QObject, Signal) — never
   QtWidgets. Backend and `processing` are importable and testable headless.
3. `models.py` and `config.py` import nothing from the app (plain dataclasses /
   stdlib).
4. Parsers are pure functions tested against captured fixture files in
   `tests/fixtures/`, so the test suite runs without a scanner attached.

## State machine (`state.py`)

```
NO_DEVICE → DEVICE_SELECTED → OPTIONS_LOADED → SCANNING → PROCESSING → DONE
     ↑_______________|   (errors return to a safe state; ERROR is transient)
```

- UI pieces react to `AppStateMachine.changed` signals instead of reaching
  into each other.
- Page navigation and button enable/disable are driven from the state.
- M1 implements the first transition only; later milestones extend it.

## Concurrency model

- **All `scanimage` calls go through `QProcess`** — Qt's event loop makes them
  async for free: `readyReadStandardError` → progress, `finished` → completion,
  `kill()` → cancel.
- **OpenCV detection/crop runs in `QThreadPool`** via a `QRunnable`
  (`processing/worker.py`), reporting back over Qt signals.
- The GUI thread never blocks. Scanning at 1200 DPI takes minutes.

## Milestones

| # | Deliverable | Status |
|---|---|---|
| M1 | App skeleton, nav, real device discovery (`scanimage -L`), device selection, last-device memory | **current** |
| M2 | Option descriptors (`--get-options` parsing), generated option form, Apply, saved presets | |
| M3 | Async scan job: progress bar, cancel, raw TIFF output, sequential numbering | |
| M4 | Photo detection + crop (port of scan.sh python), result preview grid | |
| M5 | `.desktop` file, icons, RPM spec, polish | |

### Spike items (resolve in M2/M3, then freeze as fixtures)

1. Exact `scanimage -d <dev> --get-options` descriptor format in
   sane-backends 1.4.0 (types, constraints, current values).
2. `--progress` output format on stderr → progress bar percentage.

## Where scan.sh went

| scan.sh part | Destination |
|---|---|
| `scanimage -L` existence check | `backend/devices.py` — became real discovery |
| Hardcoded `SCANNER='pixma:...'` | removed → `config.json` `last_device` |
| Fixed `--resolution 1200` | editable option / saved preset (M2) |
| TIFF output + `next_number()` | `backend/scan.py` + `config.py` output dirs (M3) |
| `flock` lock file | single-instance via QApplication + ScanJob guard (M3) |
| Embedded OpenCV detection/crop python | `processing/photos.py` (M4) |

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
│   │   ├── options.py              # `scanimage -A` parsing → OptionDescriptors; builds option args (M2 — done)
│   │   └── scan.py                 # ScanJob: QProcess wrapper, progress parsing, cancel (M3)
│   ├── processing/
│   │   ├── photos.py               # detect + crop photographs (ported from scan.sh's python block) — M4, done
│   │   └── worker.py               # QRunnable wrapper so OpenCV never blocks the UI (M4 — done)
│   └── ui/                         # imports backend + models; never builds scanimage commands itself
│       ├── main_window.py          # QMainWindow: nav sidebar + QStackedWidget + status bar
│       ├── pages/
│       │   ├── device_page.py      # scanner list, refresh (M1 — done)
│       │   ├── options_page.py     # generated option form, Apply, presets (M2 — done)
│       │   ├── scan_page.py        # Start/Cancel, progress bar, log (M3)
│       │   └── results_page.py     # preview grid of cropped photos (M4 — done)
│       └── widgets/
│           └── option_widgets.py   # factory: OptionDescriptor → Qt widget (M2 — done)
├── data/                           # .desktop file, icons (M5)
├── packaging/
│   └── scan-gui.spec               # RPM spec (M5)
└── tests/
    ├── fixtures/                   # captured scanimage output (no hardware needed)
    ├── test_devices_parsing.py
    ├── test_options_parsing.py     # M2 — done
    ├── test_photos.py              # M4 — done
    └── test_photo_worker.py        # M4 — done
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
| M1 | App skeleton, nav, real device discovery (`scanimage -L`), device selection, last-device memory | **done** |
| M2 | Option descriptors (`scanimage -A` parsing), generated option form, Apply, saved presets | **done** |
| M3 | Async scan job: progress bar, cancel, raw TIFF output, sequential numbering | **done** |
| M4 | Photo detection + crop (port of scan.sh python), result preview grid | **done** |
| M5 | `.desktop` file, icons, RPM spec, polish | |

### Spike items (resolved — answers recorded here)

1. **Option descriptors.** `scanimage --get-options` does not exist in
   sane-backends 1.4.0; the flag is **`-A` / `--all-options`**
   (`scanimage --help -d DEV` prints the same list). One block per option:

   ```
       --resolution 50..600dpi (in steps of 50) [300]
           Sets the resolution of the scanned image in DPI
   ```

   The layout comes from `print_option()` in `tools/scanimage.c`: name
   (four-space indent, single dash for the `t`/`l`/`x`/`y` window options),
   constraint, current value in `[...]`, optional flags (`[advanced]`,
   `[read-only]`, `[inactive]`, `[hardware]`), then the description indented
   eight spaces. Constraints are `a..b[unit] (in steps of n)` for ranges,
   `a|b|c` for lists, `<int>`/`<float>`/`<string>` for free values, and
   BOOL options print their constraint glued to the name: `[=(yes|no)]`.
   Types are *not* printed, so `backend/options.py` infers them.

   **Options are set on the command line, not with `-o`:** scanimage's `-o`
   is `--output-file`. `scanimage -d DEV --resolution 1200 --mode Color` is
   the correct form, and the names printed by `-A` are accepted verbatim.

2. **Progress.** `--progress` writes `Progress: 3.9%\rProgress: 7.8%\r…` to
   stderr — carriage-return separated, so the parser must split on `\r` as
   well as `\n`.

3. **Testing without hardware.** sane-backends' virtual scanner
   (`virtual:virtual_scanner`) is present on the test machine and produces
   real TIFFs, so M3/M4 can be developed end to end. Note that `scanimage -L`
   takes ~4 s there while `scanimage -A` is instantaneous.

4. **Photo detection.** The OpenCV block of `scan.sh` is ported as it was:
   greyscale the page, invert everything darker than 215 (the "content"
   threshold), close the mask with a 25×25 kernel and open it with 5×5, then
   keep the external contours that are at least 1.5 % of the page, at least
   45 % filled, not more than 3.5:1 elongated and at least 1 % away from the
   page edge. The four biggest candidates win and are numbered in reading
   order (top to bottom, left to right). The search runs on a copy scaled to
   2400 px wide, but the crops are taken from the full-resolution scan with
   a perspective transform, so the photos keep their original pixels.


## Where scan.sh went

| scan.sh part | Destination |
|---|---|
| `scanimage -L` existence check | `backend/devices.py` — became real discovery |
| Hardcoded `SCANNER='pixma:...'` | removed → `config.json` `last_device` |
| Fixed `--resolution 1200` | editable option / saved preset (M2) |
| TIFF output + `next_number()` | `backend/scan.py` + `config.py` output dirs (M3 — done) |
| `flock` lock file | `QLockFile` in `backend/scan.py` + ScanJob guard (M3 — done) |
| Embedded OpenCV detection/crop python | `processing/photos.py` (M4 — done) |

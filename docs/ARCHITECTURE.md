# Photo Scan — Architecture

Photo Scan is a Qt 6 (PySide6) desktop application for SANE scanners on
Linux: it discovers devices, edits scanner options, runs scans, and
automatically detects and crops photographs from the scanned image.

## Decisions

| Decision | Choice | Why |
|---|---|---|
| GUI toolkit | **Qt 6 / PySide6** (system RPM `python3-pyside6`) | Already installed on the target machine, mature widgets, good async primitives |
| SANE access | **`scanimage` subprocess** via `QProcess` | No new dependencies, process isolation, trivial cancellation (`kill()`) |
| Dependencies | **System Python + RPMs** (`python3-pyside6`, `python3-opencv`, `python3-numpy`, `sane-backends`, `sane-airscan`, `avahi`) | Everything is already present on the distributions we target; no virtual environment needed |
| Scope | Simple mode for everyday use, Pro mode for full control | One application, two depths of control |

## Directory layout

```
photo-scan/
├── pyproject.toml                  # metadata; the dependencies are RPMs, not pip
├── README.md                       # user documentation
├── CHANGELOG.md
├── photo-scan.spec                 # Fedora RPM spec
├── FLATHUB_PACKAGING.md            # how the Flatpak submission works
├── docs/
│   └── ARCHITECTURE.md             # this file
├── packaging/
│   └── FLATPAK_MANIFEST_GUIDE.md   # worksheet for the hand-written manifest
├── data/                           # desktop integration files
│   ├── io.github.AHerling.photo-scan.desktop
│   ├── io.github.AHerling.photo-scan.metainfo.xml
│   ├── icons/hicolor/*/apps/io.github.AHerling.photo-scan.{svg,png}
│   └── screenshots/{simple-mode,pro-mode}.png
├── scan_gui/
│   ├── __main__.py                 # entry: python3 -m scan_gui
│   ├── app.py                      # QApplication, Fusion style, MainWindow
│   ├── config.py                   # JSON settings in ~/.config/scan-gui/
│   ├── models.py                   # dataclasses: Device, OptionDescriptor, OptionType, ScanProfile
│   ├── simple_options.py           # the simple mode's drop-down contents (colour, resolution) — pure
│   ├── state.py                    # AppState enum + AppStateMachine (signals on transitions)
│   ├── backend/                    # ALL scanimage access — QtCore only, never QtWidgets
│   │   ├── devices.py              # `scanimage -L` parsing + async DeviceScanner (QProcess)
│   │   ├── options.py              # `scanimage -A` parsing → OptionDescriptors; builds the option args
│   │   ├── area.py                 # scan area handling
│   │   └── scan.py                 # ScanJob: QProcess wrapper, progress parsing, cancel
│   ├── processing/
│   │   ├── photos.py               # detect + crop photographs
│   │   └── worker.py               # QRunnable wrapper so OpenCV never blocks the UI
│   └── ui/                         # imports backend + models; never builds scanimage commands itself
│       ├── main_window.py          # QMainWindow: header + mode switch, nav sidebar, stacked pages
│       ├── pages/
│       │   ├── simple_page.py      # the everyday view: scanner, colour, resolution, folder, start
│       │   ├── device_page.py      # scanner list, refresh
│       │   ├── options_page.py     # generated option form, Apply, presets
│       │   ├── scan_page.py        # Start/Cancel, progress bar, log
│       │   └── results_page.py     # preview grid of cropped photos
│       └── widgets/
│           ├── option_widgets.py   # factory: OptionDescriptor → Qt widget
│           └── selection_view.py   # the area selection view
└── tests/
    ├── fixtures/                   # captured scanimage output (no hardware needed)
    ├── test_devices_parsing.py
    ├── test_options_parsing.py
    ├── test_photos.py
    ├── test_photo_worker.py
    ├── test_simple_options.py
    ├── test_scan.py
    ├── test_area.py
    └── test_*.py
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

## Concurrency model

- **All `scanimage` calls go through `QProcess`** — Qt's event loop makes them
  async for free: `readyReadStandardError` → progress, `finished` → completion,
  `kill()` → cancel.
- **OpenCV detection/crop runs in `QThreadPool`** via a `QRunnable`
  (`processing/worker.py`), reporting back over Qt signals.
- The GUI thread never blocks. Scanning at 1200 DPI takes minutes.

## The two modes

The window has a **Mode** drop-down in its header:

| Mode | What it shows |
|---|---|
| **Simple mode** (default) | The everyday view: scanner, colour, resolution, output folder, *Start scan*. Everything is greyed out until the information it needs has arrived. |
| **Pro Mode** | The full view: sidebar with the Scanner, Options, Scan and Results pages — every SANE option, presets, the log, the lock file. |

Both modes drive the same state machine and the same backend; the simple
mode only adds a short list of choices on top (`simple_options.py`):

* **Colour** — the scanner's scan mode, ordered full colour → greyscale →
  black & white; scanners without a scan mode fall back to their bit depth.
* **Resolution** — the well-known steps that fit inside the scanner's own
  range, highest first (1200, 600, 300, 200, 150, 100, 75, 50 — only those
  the scanner accepts).

Changing a value in the simple mode updates the full form too, so switching
modes never loses a setting.

## Notes on the SANE interface

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
   (`virtual:virtual_scanner`) produces real TIFFs, so scanning and photo
   detection can be developed end to end. Note that `scanimage -L` takes a
   few seconds there while `scanimage -A` is instantaneous.

4. **Photo detection.** The OpenCV block of the original `scan.sh` is ported
   as it was: greyscale the page, invert everything darker than 215 (the
   "content" threshold), close the mask with a 25×25 kernel and open it with
   5×5, then keep the external contours that are at least 1.5 % of the page,
   at least 45 % filled, not more than 3.5:1 elongated and at least 1 % away
   from the page edge. The four biggest candidates win and are numbered in
   reading order (top to bottom, left to right). The search runs on a copy
   scaled to 2400 px wide, but the crops are taken from the full-resolution
   scan with a perspective transform, so the photos keep their original
   pixels.

## Where scan.sh went

| scan.sh part | Destination |
|---|---|
| `scanimage -L` existence check | `backend/devices.py` — became real discovery |
| Hardcoded `SCANNER='pixma:...'` | removed → `config.json` `last_device` |
| Fixed `--resolution 1200` | editable option / saved preset |
| TIFF output + `next_number()` | `backend/scan.py` + `config.py` output dirs |
| `flock` lock file | `QLockFile` in `backend/scan.py` + ScanJob guard |
| Embedded OpenCV detection/crop python | `processing/photos.py` |

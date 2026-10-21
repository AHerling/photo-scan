# scan-gui

Qt6 (PySide6) desktop GUI for SANE scanners on Fedora.

Discover scanner devices, edit their SANE options, run scans, and
automatically detect and crop photographs from the scanned image — a GUI
successor to `scan.sh`.

**Status:** milestone 4 — device discovery, option editing, scanning and
photo detection, with a new **Simple mode** for everyday use.
See [STRUCTURE.md](STRUCTURE.md) for the full plan.

## The two modes

The **Mode** drop-down in the header switches between them; the app opens in
**Simple mode**.

**Simple mode** is the everyday view — four drop-downs and a button:

```
Scanner      [ Canon PIXMA MP610 Scanner        ▾]
Colour       [ Full colour                     ▾]
Resolution   [ 1200 dpi                        ▾]
Save to      [ /home/cain                      ]  (click to change)
                    [ Start scan ]
```

The colour list runs from full colour down to black and white, the
resolutions from the highest to the lowest, and only what your scanner
actually offers is shown. While the app is still looking for scanners, or
still reading their options, the controls stay greyed out and the line under
the button says what is happening (*Looking for scanners…*, *Reading the
scanner's options…*, *Ready to scan.*, *Scanning…*).

**DEV-Mode** is the full view that came before it: a sidebar with the
Scanner, Options, Scan and Results pages, every SANE option, presets, the
scanner log and the lock file. Pick it in the Mode drop-down.

## Network/WiFi scanners (eSCL/AirScan)

`sane-airscan` is now recommended for network scanners that advertise themselves via mDNS/Avahi or eSCL. After installing it, `scanimage -L` should discover them automatically. If discovery is slow or a scanner is missing, check that `avahi-daemon` is running and enabled (`sudo systemctl enable --now avahi-daemon`), ensure the scanner and computer are on the same network, add your user to the `scanner,lp` groups, and check firewall settings. USB and `net`/`saned` scanners remain supported as before.

## Dependencies (Fedora)

All via system packages — no venv or pip needed:

```bash
sudo dnf install python3-pyside6 python3-opencv sane-backends sane-airscan avahi
```

- `sane-backends` provides `scanimage` and core SANE drivers (USB scanners).
- `sane-airscan` adds support for network/WiFi scanners using eSCL/AirScan (common on modern HP/Epson/Canon/Brother network printers/scanners). If you only use USB scanners, it is optional but recommended for broader compatibility.
- `avahi` enables mDNS/zeroconf discovery for network scanners. Start it with `sudo systemctl enable --now avahi-daemon` if it's not already running.

### Permissions (USB scanners)

On Fedora, many USB scanners require membership in the `scanner` and `lp` groups:

```bash
sudo usermod -aG scanner,lp $USER
```

Log out and back in for the group changes to take effect. Without the correct permissions, `scanimage` may fail to access USB scanners.

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
- **Simple mode** — the everyday view, four drop-downs and a start button — *done*
- **M5** Desktop integration and RPM packaging — *on hold, the UI comes first*

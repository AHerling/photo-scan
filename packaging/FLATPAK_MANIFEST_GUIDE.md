# Flatpak manifest worksheet (for the submitter)

This is a **worksheet**, not a Flatpak manifest. Flathub's policy forbids AI-authored or
AI-assisted manifests. Write the manifest yourself, in your own words, and verify against
the linter. Everything below is verified against currently published Flathub apps and
Flathub's public documentation (see references at the end).

## 1) Required identity and files

| Item | Value / requirement | Notes |
| --- | --- | --- |
| App ID | `io.github.AHerling.photo-scan` | GitHub code-hosting IDs need ≥4 components; use `io.github.`. Dash only allowed in the last component. Linter: `appid-code-hosting-too-few-components`, `appid-uses-code-hosting-domain`, `appid-component-wrong-syntax`. |
| Manifest filename | `io.github.AHerling.photo-scan.yml` (YAML) | Must match the app ID exactly. Linter: `appid-filename-mismatch`. The project uses YAML. |
| Desktop file | `data/io.github.AHerling.photo-scan.desktop` | Install to `share/applications/$FLATPAK_ID.desktop`. Must `Exec=photo-scan`. |
| AppStream metainfo | `data/io.github.AHerling.photo-scan.metainfo.xml` | Install to `share/metainfo/$FLATPAK_ID.metainfo.xml`. The `<id>` must match the app ID. Screenshots are pinned to commit SHAs in git; Flatpak Builder mirrors them to `dl.flathub.org/media` during the Flathub build. No `flathub::manifest` key needed for a Flathub PR submission. |
| Icon | `data/icons/hicolor/*/apps/io.github.AHerling.photo-scan.png` + scalable SVG | Install all sizes and the SVG as the app expects. |
| License | `LICENSE` (MIT) | Land in the package; Flatpak licenses typically go to `$FLATPAK_DEST/share/licenses/$FLATPAK_ID/`. |

## 2) Runtime, base app, command, and env

Use the **PySide BaseApp** (verified present on Flathub). Reference: the `io.qt.PySide.BaseApp` README.

| Field | Recommended value | Rationale / checks |
| --- | --- | --- |
| `runtime` | `org.kde.Platform` | Qt6/KDE runtime used by working SANE apps on Flathub (e.g. `org.kde.skanlite`). |
| `runtime-version` | `'6.11'` | Latest KDE branch at the time of writing. Flathub expects the runtime to be current at submission — verify at submission time. |
| `sdk` | `org.kde.Sdk` | Matches the Platform. |
| `base` | `io.qt.PySide.BaseApp` | Provides PySide6 and Python in a packaging-friendly form for PySide6 apps. Verified in the Flathub OSTree summary (`app/io.qt.PySide.BaseApp/x86_64/6.11`). |
| `base-version` | `'6.11'` | Match the runtime/base branch. |
| `command` | `photo-scan` | The GUI entry point (`pyproject.toml` has `[project.gui-scripts] photo-scan = "scan_gui.app:main"`). No CLI entry points are included. |
| `build-options.env` | `BASEAPP_REMOVE_WEBENGINE=1` | Remove unused WebEngine to save size. **Do NOT** set `BASEAPP_DISABLE_NUMPY=1` — OpenCV depends on NumPy. |
| `cleanup-commands` | `- /app/cleanup-BaseApp.sh` | Required when using the PySide BaseApp. |

**Python / NumPy note (critical):**
- The base runtime branch determines the Python version (org.kde.Sdk 6.11 is based on freedesktop 25.08 → Python 3.13). The app requires `python >= 3.12`, so it is compatible.
- Verify NumPy's version in the chosen runtime/base at build time (e.g. `flatpak run --command=python3 org.kde.Platform//6.11 -c 'import numpy; print(numpy.__version__)'`) because `opencv-python-headless` has numpy version requirements (newer wheels require numpy 2). Pick an `opencv-python-headless` wheel whose numpy ABI matches the runtime (Facetracker uses an abi3 wheel with numpy 2).

## 3) Finish arguments (scanner access)

Use `org.kde.skanlite`'s finish-args as the verified reference for SANE/scanner access on the KDE runtime.

| Finish arg | Why | Linter notes |
| --- | --- | --- |
| `--device=all` | USB scanner access. | Allowed (published apps use it). Consider `--device=usb` if linter guidance changes, but verify against current linter. |
| `--env=SANE_CONFIG_DIR=/var/config/sane.d:` | Point SANE at the bundled config dir. The trailing `:` appends per flatpak environment rules. | Follow skanlite. |
| `--share=ipc` | Required if using `--socket=fallback-x11`. | Linter: `finish-args-x11-without-ipc` is an error. |
| `--share=network` | AirScan/mDNS/network discovery and network scanners. | Allowed with justification in context; network is needed here. |
| `--socket=fallback-x11` | X11 fallback (Wayland-primary). **Do not** combine with `--socket=x11`. | Linter forbids both together. |
| `--socket=wayland` | Wayland support. | Standard. |
| `--system-talk-name=org.freedesktop.Avahi` | SANE AirScan uses Avahi over D-Bus for mDNS discovery. | Specific D-Bus talk names are allowed; `--socket=session-bus`/`--socket=system-bus` are not. |

**Filesystem access:** The app defaults its output folder to the home directory (`Path.home()`) and lets the user pick a folder via `QFileDialog.getExistingDirectory`. In a Flatpak, the folder picker uses the portal and returns a document-portal path that is writable without broad filesystem access in many cases; however, the default folder is the sandbox's `HOME` (writable) but ends up in `~/.var/app/<id>/`. For a better UX (writing to the user's real home), `--filesystem=home` is commonly used, but the linter classifies it as requiring an explanation. Prefer using portals / well-known directories where possible (`xdg-pictures`, `xdg-documents`) and add `--filesystem=home` only with a clear justification in the PR if the default output folder must reach the real home.

**GPU acceleration:** Add `--device=dri` for hardware-accelerated Qt rendering (common for Qt apps; check if needed).

## 4) Modules (build plan)

Build modules in order. Use exact versions from working Flathub references.

| Module | Buildsystem | Source (reference) | Notes |
| --- | --- | --- | --- |
| `sane` | `autotools` | sane-backends 1.4.0 from the SANE project (see `org.kde.skanlite`). Use its `config-opts` (`--with-usb`, `--with-v4l`, `--with-gphoto2`, `--enable-pthread`, `--enable-pnm-backend`, `--enable-avahi`, etc.). | Provides `scanimage` and SANE backends. |
| `sane-airscan` | `meson` | sane-airscan 0.99.38 (see `org.kde.skanlite`). | AirScan/eSCL support for network scanners. |
| `python3-opencv` | `simple` | Vendor `opencv-python-headless` as a pre-fetched manylinux wheel (abi3) via `pip3 install --no-index --find-links="file://${PWD}" --prefix=${FLATPAK_DEST} opencv-python-headless --no-build-isolation` (reference: `flathub/de.z_ray.Facetracker`). Get the wheel URL and `sha256` from PyPI for the arch(es) you support (x86_64 and/or aarch64). Ensure the wheel's numpy requirement matches the runtime's NumPy (do **not** let pip resolve from the network). | OpenCV is required by the photo detection pipeline and is not present in the KDE runtime. |
| `photo-scan` (app) | `simple` (or `meson`/none) | Install from the source tree: copy files to `${FLATPAK_DEST}`, install the desktop file, metainfo, icons, and run `pip3 install --no-index --no-deps --prefix=${FLATPAK_DEST} .` or equivalent with no network. The app has no external pip dependencies. | Ensure `photo-scan` is on `PATH` and the entry point matches. |

**Caveats:**
- All sources must be vendored/fetched by flatpak-builder (no network during the build). Wheel files count as sources.
- Watch Python ABI compatibility between the runtime, NumPy, and the `opencv-python-headless` wheel.
- The PySide BaseApp ships PySide6/NumPy/Python; do not duplicate them unnecessarily.

## 5) Style, linter, and policy constraints

| Rule | Requirement |
| --- | --- |
| YAML style | 2-space indent, LF, UTF-8, trailing newline, blank lines between modules, unquoted strings unless quoting required (Flathub style). |
| Manifest filename = app ID | `io.github.AHerling.photo-scan.yml`. |
| No network during build | All sources (archives, wheels) must be listed explicitly; no `pip install` from PyPI. |
| License placement | Include the app's license in the package. |
| Screenshots | Use `data/screenshots/simple-mode.png` and `data/screenshots/pro-mode.png`. Pin to commit SHAs in metainfo; Flathub mirrors them. |
| D-Bus | Only specific `--talk-name`/`--system-talk-name` are allowed; `--socket=system-bus` and `--socket=session-bus` are forbidden. |
| Sockets | Do not mix `--socket=x11` and `--socket=fallback-x11`. `--socket=fallback-x11` requires `--share=ipc`. |
| Filesystem | Avoid absolute `/home/...`; prefer portals/well-known dirs. `--filesystem=home` is grantable with explanation. |
| AI policy (Flathub) | **Manifests must not contain AI-generated or AI-assisted content.** Disclosure does not exempt. The manifest must be your own work. |
| AI policy (Fedora) | For commits in this repo, use `Assisted-by: OpenCode:Big Pickle` in the commit trailer; the contributor remains responsible. |

## 6) Local test and submission checklist

### Local testing (if `flatpak-builder` is installed)
```bash
# Lint the manifest
flatpak run --command=flatpak-builder-lint org.flatpak.Builder manifest io.github.AHerling.photo-scan.yml

# Build and install locally
flatpak run --command=flathub-build org.flatpak.Builder --install io.github.AHerling.photo-scan.yml
# or
flatpak-builder --user --install --force-clean build-dir io.github.AHerling.photo-scan.yml

# Run
flatpak run io.github.AHerling.photo-scan
```

### Flathub submission
1. Open a PR to the `flathub/flathub` repo as a **new app submission** (fork with `master` branch only unchecked, clone `--branch=new-pr`, branch from `new-pr`, PR against the `new-pr` base branch).
2. PR title: `Add io.github.AHerling.photo-scan`.
3. After the linter is clean and reviewers are satisfied, comment `bot, build` to trigger a test build.
4. Address review feedback; do not close/reopen the PR to reset reviews.
5. When merged, you'll get access to `github.com/flathub/io.github.AHerling.photo-scan` (enable 2FA).

### Verification commands (useful)
```bash
desktop-file-validate data/io.github.AHerling.photo-scan.desktop
appstreamcli validate --no-net data/io.github.AHerling.photo-scan.metainfo.xml
flatpak run --command=flatpak-builder-lint org.flatpak.Builder manifest io.github.AHerling.photo-scan.yml
```

## 7) References (verified)
- `flathub/org.kde.skanlite` (SANE + sane-airscan, finish-args, runtime 6.11)
- `flathub/de.z_ray.Facetracker` (opencv-python-headless wheel installed via pip from vendored manylinux wheel)
- `flathub/com.pot_app.pot` (YAML manifest style)
- `flathub/io.qt.PySide.BaseApp` (base app, branches, env vars, cleanup)
- Flathub docs: Requirements, Submission, Linter, Runtimes, MetaInfo Guidelines
- KDE Runtime 6.11 build (Qt 6.11.1, freedesktop 25.08 base)

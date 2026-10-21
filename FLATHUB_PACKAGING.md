# Photo Scan (Flathub/Bazaar packaging)

Project name: **Photo Scan**  
App ID: `org.photo.scan`  
Entry points: `photo-scan`, `photo-scan-cli` (also `scan-gui`/`scan-gui-cli` for compatibility)

## Files
- `org.photo.scan.desktop` / `photo-scan.desktop`
- `org.photo.scan.metainfo.xml` (AppStream)
- `org.photo.scan.json` (Flatpak manifest for Flathub/Bazaar)
- `photo-scan.png`, `data/icons/.../org.photo.scan.png`/`.svg`
- `LICENSE`

## Flatpak build (local test)
```bash
flatpak-builder --user --install --force-clean build-dir org.photo.scan.json
flatpak run org.photo.scan
```

## Notes
- Uses KDE runtime 6.9, bundles `sane-backends` and `sane-airscan`.
- Grants access to network, Avahi, devices, home, and tmp for scanner discovery/scanning.
- Uses `pip` to install `opencv-python-headless` and `numpy` inside the sandbox (the app expects system/OpenCV deps on native distros; Flatpak packaging uses these).
- On native Fedora, prefer system packages: `python3-pyside6 python3-opencv sane-backends sane-airscan avahi`.

# Photo Scan — Flathub/Bazaar packaging

App ID: `io.github.AHerling.photo-scan`  
Runtime: `org.kde.Platform` / `org.kde.Sdk` 6.11 + `io.qt.PySide.BaseApp` 6.11  
Entry point: `photo-scan` (GUI only)  

## Current state
- The application has been renamed to `io.github.AHerling.photo-scan` with AppStream metadata, desktop integration, and the required screenshots.
- CLI entry points have been removed; only the GUI is shipped.
- The Fedora RPM has been rewritten and built locally; DEB packaging has been removed.
- The Flatpak manifest is **not** included in this repository. Flathub's policy forbids AI-authored or AI-assisted manifests; the human submitter must write `io.github.AHerling.photo-scan.yml` themselves.

## Required files in the Flathub repository
When submitting to Flathub (a PR against `github.com/flathub/io.github.AHerling.photo-scan`), include:
- `io.github.AHerling.photo-scan.yml` (the manifest, written by the submitter)
- `io.github.AHerling.photo-scan.metainfo.xml` (AppStream metadata; can be copied from `data/` or tailored)
- `io.github.AHerling.photo-scan.desktop` (desktop entry)
- Icons (PNG at 16/24/32/48/64/128/256 and scalable SVG)
- `LICENSE`
- Any patches/sources referenced by the manifest

## Submission flow (Flathub)
1. **Create the submission repo**: Fork [flathub/flathub](https://github.com/flathub/flathub) with "Copy the master branch only" unchecked, or follow the documented flow. Alternatively, use `gh repo fork --clone flathub/flathub && cd flathub && git checkout --track origin/new-pr`.
2. **Branch**: `git checkout -b <submission-branch> new-pr`.
3. **Add files**: Add the manifest and all required assets. The manifest filename must match the app ID (`io.github.AHerling.photo-scan.yml`).
4. **Open a PR** against the `new-pr` base branch with the title `Add io.github.AHerling.photo-scan`.
5. **Test**: After the PR is submitted, comment `bot, build` to trigger a test build. Check the build logs and fix any linter errors.
6. **Review**: Respond to reviewer feedback. Do not close/reopen the PR to reset reviews.
7. **Merge**: Once approved and merged, Flathub creates `github.com/flathub/io.github.AHerling.photo-scan` and invites maintainers (enable 2FA on GitHub).

## How to use the worksheet
See [`packaging/FLATPAK_MANIFEST_GUIDE.md`](packaging/FLATPAK_MANIFEST_GUIDE.md) for a verified checklist: runtime/base app, modules (SANE + AirScan + OpenCV wheel), finish-args, linter rules, local testing, and references to working Flathub manifests.

## Notes
- **Bazaar**: Bazaar is a Flathub client; publishing to Flathub makes the app available there.
- **No CLI**: The app is GUI-only. The Fedora package and Flatpak must not ship `photo-scan-cli`.
- **Scanner access**: The app uses `scanimage` and SANE AirScan; the manifest must grant the necessary device/network/Avahi permissions.
- **Qt/PySide**: Use `io.qt.PySide.BaseApp` with `org.kde.Platform` 6.11. Do not disable NumPy in the base app.
- **Screenshots**: `data/screenshots/simple-mode.png` and `data/screenshots/pro-mode.png` are the canonical store screenshots.
- **Policy**: Follow Flathub's linter and policies. The manifest must be written by a human; AI assistance is not acceptable for the manifest file itself.

# Changelog

All notable changes to Photo Scan are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project uses [semantic versioning](https://semver.org/).

## 0.2.0 — 2026-10-21

The first public release.

### Added

- Original application icon, drawn for this project: a flat scanner with a
  photograph rising out of it. The scalable SVG is the master; the PNGs are
  rendered from it at 16, 24, 32, 48, 64, 128 and 256 pixels.
- Application screenshots for the store listings, in both modes.
- AppStream metadata, so the software centres can describe the application:
  name, summary, description, category, keywords, screenshots, releases and
  licence.
- A Fedora RPM spec that actually builds the package, using
  `pyproject-rpm-macros`. The unit tests run in `%check`.
- A rewrite of the README, and a `docs/ARCHITECTURE.md` describing how the
  code is put together.

### Changed

- The application ID is now `io.github.AHerling.photo-scan`, matching the
  repository name. The previous ID, `org.photo.scan`, is not valid for a
  GitHub-hosted application on Flathub, which reserves that namespace for
  applications verified through a domain they control.
- The desktop entry, the AppStream metadata and the icon theme directories
  are all named after the new ID. There is now a single canonical desktop
  file, under `data/`.
- The version was moved to 0.2.0. The 0.1.0 release shipped packages that
  did not install cleanly, and the number is not reused.

### Removed

- The command line entry points `photo-scan-cli` and `scan-gui-cli`. Both
  pointed at the GUI launcher, so the names promised an interface that did
  not exist. Photo Scan is a desktop application with a single entry point.
- The Debian package and the script that built it. The ar members were
  invalid and it was never tested on a Debian based system.
- The built RPM and DEB are no longer tracked in the repository.
- The old `org.photo.scan.json` Flatpak manifest, which contained XML
  rather than JSON and could never have been parsed.

## 0.1.0 — 2026-10-21

Pre-release. The packaging in this release did not work, and the
application ID was not usable on Flathub. Superseded by 0.2.0.

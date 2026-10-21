"""Application entry point: QApplication setup and main window creation."""

import os
import shutil
import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from scan_gui.ui.main_window import MainWindow

_STYLE_SHEET = """
QLabel#pageHeading { font-size: 18px; font-weight: 600; }
QLabel#appTitle { font-size: 16px; font-weight: 600; }
QListWidget#navList { border-right: 1px solid palette(mid); }
"""


def _drop_shell_functions() -> None:
    """Remove the shell's exported bash functions from the environment.

    KDE's file dialog helper (KIO) passes the environment on to systemd and
    complains about the "BASH_FUNC_…%%" entries the shell leaves behind.
    They mean nothing to us, so they are dropped before Qt starts.
    """
    for name in [key for key in os.environ if key.startswith("BASH_FUNC_")]:
        del os.environ[name]


def _check_scanimage() -> bool:
    """Check that scanimage is available. Warn if not."""
    if shutil.which("scanimage") is not None:
        return True

    QMessageBox.critical(
        None,
        "scanimage not found",
        "The 'scanimage' tool was not found.\n\n"
        "Install SANE on your system:\n\n"
        "sudo dnf install sane-backends sane-airscan avahi\n\n"
        "You may also need to add your user to the scanner and lp groups:\n\n"
        "sudo usermod -aG scanner,lp $USER\n\n"
        "Log out and back in for group changes to take effect.",
    )
    return False


def main() -> int:
    _drop_shell_functions()

    app = QApplication(sys.argv)
    app.setApplicationName("Photo Scan")
    app.setApplicationDisplayName("Photo Scan")
    app.setOrganizationName("Photo Scan")
    app.setDesktopFileName("org.photo.scan")
    app.setStyle("Fusion")
    app.setStyleSheet(_STYLE_SHEET)

    if not _check_scanimage():
        return 1

    window = MainWindow()
    window.show()
    return app.exec()

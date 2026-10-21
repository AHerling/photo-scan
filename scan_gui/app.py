"""Application entry point: QApplication setup and main window creation."""

import os
import sys

from PySide6.QtWidgets import QApplication

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


def main() -> int:
    _drop_shell_functions()

    app = QApplication(sys.argv)
    app.setApplicationName("scan-gui")
    app.setOrganizationName("scan-gui")
    app.setStyle("Fusion")
    app.setStyleSheet(_STYLE_SHEET)

    window = MainWindow()
    window.show()
    return app.exec()

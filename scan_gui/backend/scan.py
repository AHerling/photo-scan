"""Scan execution — milestone 3.

ScanJob wraps `scanimage` in a QProcess: the progress percentage is streamed
from stderr, cancel() kills the process, and the raw TIFF is written to the
configured output directory under a sequential number.

Layering rule for the backend: QtCore only, never QtWidgets.
"""

import re
from pathlib import Path

from PySide6.QtCore import QLockFile, QObject, QProcess, Signal

from scan_gui.backend.options import build_option_arguments
from scan_gui.models import OptionDescriptor

# scanimage writes "Progress: 42.5%" to stderr, separated by carriage
# returns, so the buffer has to be split on both kinds of line break.
_PROGRESS_RE = re.compile(r"Progress:\s*(?P<percent>\d+(?:\.\d+)?)%")
_CHUNK_RE = re.compile(r"[\r\n]+")
_NUMBER_RE = re.compile(r"^(?P<number>\d{6})\.")

OUTPUT_FORMAT = "tiff"
LOCK_FILENAME = ".scan.lock"


def parse_progress(text: str) -> int | None:
    """Return the percentage of a scanimage progress message, if any."""
    match = _PROGRESS_RE.search(text)
    return int(float(match.group("percent"))) if match else None


def split_chunks(text: str, final: bool = False) -> tuple[list[str], str]:
    """Split scanimage output into complete lines and the trailing remainder.

    Progress messages are separated by carriage returns, everything else by
    newlines, so both have to be treated as line breaks.
    """
    chunks = _CHUNK_RE.split(text)
    remainder = "" if final else chunks.pop()
    return [chunk.strip() for chunk in chunks if chunk.strip()], remainder


def next_output_path(directory: Path, extension: str = OUTPUT_FORMAT) -> Path:
    """Return the next free numbered output path, e.g. `000007.tiff`.

    Follows the numbering of the original scan.sh: six digits, counting from
    the highest number already present in the directory.
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    highest = 0
    for entry in directory.iterdir():
        match = _NUMBER_RE.match(entry.name)
        if match and entry.suffix.lower() == f".{extension}":
            highest = max(highest, int(match.group("number")))
    return directory / f"{highest + 1:06d}.{extension}"


def build_scan_command(
    device: str,
    options: list[OptionDescriptor],
    values: dict[str, str],
    output_path: Path,
) -> list[str]:
    """Build the full scanimage command line for one scan."""
    arguments = [
        "-d", device,
        "--format", OUTPUT_FORMAT,
        "--progress",
        "-o", str(output_path),
    ]
    arguments += build_option_arguments(options, values)
    return ["scanimage"] + arguments


class ScanJob(QObject):
    """Runs one `scanimage` invocation and reports what it is doing."""

    started = Signal(str)       # output path
    progress = Signal(int)      # percent, 0-100
    log = Signal(str)           # a line of scanner output
    finished = Signal(str)      # output path
    failed = Signal(str)        # human-readable message
    cancelled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._process = QProcess(self)
        self._process.readyReadStandardError.connect(self._on_stderr)
        self._process.finished.connect(self._on_finished)
        self._process.errorOccurred.connect(self._on_error)
        self._buffer = ""
        self._last_message = ""
        self._output_path: Path | None = None
        self._percent = 0
        self._cancelled = False
        self._lock: QLockFile | None = None

    @property
    def busy(self) -> bool:
        return self._process.state() != QProcess.ProcessState.NotRunning

    @property
    def output_path(self) -> Path | None:
        return self._output_path

    def start(
        self,
        device: str,
        options: list[OptionDescriptor],
        values: dict[str, str],
        output_path: Path,
    ) -> bool:
        """Start a scan. Returns False when a scan is already running."""
        if self.busy:
            self.failed.emit("A scan is already running.")
            return False

        self._output_path = Path(output_path)
        self._output_path.parent.mkdir(parents=True, exist_ok=True)

        # scan.sh used flock to keep two scans from colliding; QLockFile does
        # the same and clears the lock when the process dies.
        self._lock = QLockFile(str(self._output_path.parent / LOCK_FILENAME))
        self._lock.setStaleLockTime(0)
        if not self._lock.tryLock(0):
            self.failed.emit("Another scan is already running.")
            return False

        command = build_scan_command(device, options, values, self._output_path)
        self._buffer = ""
        self._last_message = ""
        self._percent = 0
        self._cancelled = False
        self.started.emit(str(self._output_path))
        self._process.start(command[0], command[1:])
        return True

    def cancel(self) -> None:
        """Kill the running scan."""
        if not self.busy:
            return
        self._cancelled = True
        self._process.kill()

    def stop(self) -> None:
        """Kill the running scan and wait for it to die (call on close)."""
        if self.busy:
            self._cancelled = True
            self._process.kill()
            self._process.waitForFinished(1000)

    # ---- process events ----

    def _on_stderr(self) -> None:
        data = self._process.readAllStandardError().data().decode("utf-8", "replace")
        self._buffer += data
        chunks, self._buffer = split_chunks(self._buffer)
        for chunk in chunks:
            self._handle_chunk(chunk)

    def _handle_chunk(self, chunk: str) -> None:
        percent = parse_progress(chunk)
        if percent is None:
            self._last_message = chunk
            self.log.emit(chunk)
            return
        if percent != self._percent:
            self._percent = percent
            self.progress.emit(percent)

    def _on_finished(self, exit_code: int, _status) -> None:
        chunks, _ = split_chunks(self._buffer, final=True)
        self._buffer = ""
        for chunk in chunks:
            self._handle_chunk(chunk)
        if self._lock is not None:
            self._lock.unlock()

        if self._cancelled:
            self._remove_output()
            self.cancelled.emit()
            return

        if exit_code != 0:
            self._remove_output()
            self.failed.emit(
                self._last_message or f"scanimage exited with code {exit_code}"
            )
            return

        if not self._output_path.exists() or self._output_path.stat().st_size == 0:
            self._remove_output()
            self.failed.emit("The scanner produced an empty file.")
            return

        self.finished.emit(str(self._output_path))

    def _on_error(self, error: QProcess.ProcessError) -> None:
        if error == QProcess.ProcessError.FailedToStart:
            if self._lock is not None:
                self._lock.unlock()
            self.failed.emit("Could not run scanimage. Is sane-backends installed?")

    def _remove_output(self) -> None:
        """Delete a partial or empty output file."""
        if self._output_path and self._output_path.exists():
            try:
                self._output_path.unlink()
            except OSError:
                pass

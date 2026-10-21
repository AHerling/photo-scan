"""Central application state machine.

UI pieces react to `AppStateMachine.changed` instead of reaching into each
other. Navigation and button enable/disable are driven from these transitions.
"""

from enum import Enum, auto

from PySide6.QtCore import QObject, Signal


class AppState(Enum):
    NO_DEVICE = auto()
    DEVICE_SELECTED = auto()
    OPTIONS_LOADED = auto()   # M2
    SCANNING = auto()         # M3
    PROCESSING = auto()       # M4
    DONE = auto()
    ERROR = auto()


class AppStateMachine(QObject):
    """Guards and reports app-wide state transitions.

    Flow: NO_DEVICE -> DEVICE_SELECTED -> OPTIONS_LOADED -> SCANNING
          -> PROCESSING -> DONE
    """

    changed = Signal(object, object)  # (old: AppState | None, new: AppState)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = AppState.NO_DEVICE

    @property
    def state(self) -> AppState:
        return self._state

    def transition(self, new_state: AppState) -> None:
        if new_state == self._state:
            return
        old = self._state
        self._state = new_state
        self.changed.emit(old, new_state)

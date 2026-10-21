"""The preview image the user picks an area on.

Shows a low resolution picture of the scan bed and lets the user drag a
rectangle over it. The rectangle is reported in the image's own pixels, so
the caller can turn it into millimetres for the scanner.
"""

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

# A drag shorter than this counts as a click, which clears the selection.
_MIN_DRAG = 5


class SelectionView(QWidget):
    """A preview of the scan bed with a draggable selection."""

    selection_changed = Signal(object)  # QRect in image pixels, or None

    def __init__(self, parent=None):
        super().__init__(parent)
        self._image: QImage | None = None
        self._selection: QRect | None = None
        self._drag_start: QPoint | None = None
        self._drag_end: QPoint | None = None
        self.setMinimumSize(320, 240)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.setCursor(Qt.CursorShape.CrossCursor)

    # ---- data ----

    def set_image(self, image: QImage) -> None:
        """Show a new preview and forget the old selection."""
        self._image = image
        self._selection = None
        self._drag_start = self._drag_end = None
        self.update()
        self.selection_changed.emit(None)

    def clear(self) -> None:
        self.set_image(QImage())

    def image(self) -> QImage | None:
        return self._image if self._image and not self._image.isNull() else None

    def image_size(self) -> QSize:
        image = self.image()
        return image.size() if image else QSize()

    def selection(self) -> QRect | None:
        """The picked area, in the image's own pixels."""
        return self._selection

    # ---- painting ----

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.palette().base())
        image = self.image()
        if image is None:
            return

        target = self._target_rect()
        painter.drawImage(target, image)

        selection = self._selection
        if selection is None and self._drag_start is not None:
            selection = QRect(self._drag_start, self._drag_end or self._drag_start)
            selection = selection.normalized()

        if selection is not None:
            # Darken everything outside the picked area.
            shade = QColor(0, 0, 0, 110)
            area = self._image_rect_to_widget(selection)
            for outside in (
                QRect(target.left(), target.top(), target.width(), area.top() - target.top()),
                QRect(target.left(), area.bottom() + 1, target.width(), target.bottom() - area.bottom()),
                QRect(target.left(), area.top(), area.left() - target.left(), area.height()),
                QRect(area.right() + 1, area.top(), target.right() - area.right(), area.height()),
            ):
                painter.fillRect(outside, shade)
            painter.setPen(QPen(QColor(30, 140, 255), 2, Qt.PenStyle.DashLine))
            painter.drawRect(area)

    # ---- geometry helpers ----

    def _target_rect(self) -> QRect:
        """Where the image is drawn: fitted into the widget, centred."""
        image = self.image()
        if image is None:
            return QRect()
        width = image.width()
        height = image.height()
        if width <= 0 or height <= 0:
            return QRect()
        scale = min(self.width() / width, self.height() / height)
        return QRect(
            (self.width() - int(width * scale)) // 2,
            (self.height() - int(height * scale)) // 2,
            int(width * scale),
            int(height * scale),
        )

    def _to_image(self, point: QPoint) -> QPoint:
        """A widget position in the image's own pixels."""
        image = self.image()
        target = self._target_rect()
        if image is None or target.isEmpty():
            return QPoint()
        x = (point.x() - target.x()) * image.width() / target.width()
        y = (point.y() - target.y()) * image.height() / target.height()
        return QPoint(int(x), int(y))

    def _image_rect_to_widget(self, rect: QRect) -> QRect:
        """A rectangle in image pixels, as drawn on the widget."""
        image = self.image()
        target = self._target_rect()
        if image is None or target.isEmpty():
            return QRect()
        x = target.x() + rect.left() * target.width() / image.width()
        y = target.y() + rect.top() * target.height() / image.height()
        width = rect.width() * target.width() / image.width()
        height = rect.height() * target.height() / image.height()
        return QRect(int(x), int(y), int(width), int(height))

    # ---- mouse ----

    def mousePressEvent(self, event) -> None:
        if self.image() is None:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            point = self._to_image(event.position().toPoint())
            self._drag_start = point
            self._drag_end = point
            self.update()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_start is None:
            return
        self._drag_end = self._to_image(event.position().toPoint())
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        if self._drag_start is None:
            return
        point = self._to_image(event.position().toPoint())
        start = self._drag_start
        self._drag_start = self._drag_end = None

        rect = QRect(start, point).normalized()
        image = self.image()
        if image is not None:
            rect = rect.intersected(image.rect())
        if rect.width() < _MIN_DRAG or rect.height() < _MIN_DRAG:
            # A click without a drag clears the selection.
            self._selection = None
        else:
            self._selection = rect
        self.update()
        self.selection_changed.emit(self._selection)

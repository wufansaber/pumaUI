from __future__ import annotations

import math
import re
from typing import Optional

from .qt_compat import (
    QColor,
    QEvent,
    QFont,
    QFrame,
    QHBoxLayout,
    QLabel,
    QObject,
    QPainter,
    QPainterPath,
    QPen,
    QPointF,
    QPushButton,
    QRectF,
    QSize,
    QSizePolicy,
    Qt,
    QTimer,
    QVBoxLayout,
    QWidget,
)


class ClassicButton(QPushButton):
    def __init__(self, text: str, *, arrow: bool = False, parent: Optional[QWidget] = None):
        super().__init__(text + ("    >" if arrow else ""), parent)
        self.setMinimumHeight(34)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet(
            """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f4f1ea, stop:1 #e3dfd6);
                border: 1px solid #9a968c;
                border-radius: 2px;
                color: #16181c;
                font-size: 11px;
                font-weight: 600;
                padding: 4px 8px;
                text-align: center;
            }
            QPushButton:hover {
                background: #faf8f2;
                border-color: #2f5fb3;
            }
            QPushButton:pressed {
                background: #d6d2c7;
                border-color: #4c4943;
                padding-top: 5px;
                padding-bottom: 3px;
            }
            QPushButton:checked {
                background: #dbe6f9;
                border: 1px solid #2f5fb3;
            }
            QPushButton:disabled {
                color: #8b8b86;
                background: #dedad1;
                border-color: #b0aca2;
            }
            """
        )


class SubmenuArrow(QWidget):
    """Black triangle that sits outside a button which opens a sub-menu."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(11, 11)
        self.setToolTip("Sub-menu indicator")

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#1a1a1a"))
        path = QPainterPath()
        path.moveTo(1, 1)
        path.lineTo(10, 5.5)
        path.lineTo(1, 10)
        path.closeSubpath()
        painter.drawPath(path)
        painter.end()


class SubmenuButtonRow(QWidget):
    """Keeps every navigation button the same size, with the arrow at the lower right."""

    def __init__(self, button: QPushButton, show_arrow: bool = False, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.button = button
        self.arrow = SubmenuArrow(self) if show_arrow else None
        button.setFixedHeight(40)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 12, 0)
        layout.setSpacing(0)
        layout.addWidget(button)
        self.setFixedHeight(42)

    def resizeEvent(self, event):  # noqa: N802 - Qt override
        super().resizeEvent(event)
        if self.arrow is None:
            return
        geo = self.button.geometry()
        self.arrow.move(geo.right() - 1, geo.bottom() - self.arrow.height() + 1)
        self.arrow.raise_()


class StatusDot(QWidget):
    STATUS_COLORS = {
        "valid": "#00a040",
        "nonoptimal": "#e39a21",
        "incomplete": "#ed1c24",
        "invalid": "#ed1c24",
        "unknown": "#8b8b8b",
    }

    def __init__(self, color: str = "#ed1c24", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.color = QColor(color)
        color_name = self.color.name().lower()
        self.status = (
            "valid" if color_name == self.STATUS_COLORS["valid"]
            else "nonoptimal" if color_name == self.STATUS_COLORS["nonoptimal"]
            else "incomplete" if color_name == self.STATUS_COLORS["incomplete"]
            else "unknown"
        )
        self.setFixedSize(16, 16)

    def set_status(self, status: str):
        normalized = str(status or "unknown").strip().lower().replace(" ", "")
        if normalized in {"non-optimal", "non_optimal"}:
            normalized = "nonoptimal"
        if normalized not in self.STATUS_COLORS:
            normalized = "unknown"
        self.status = normalized
        self.color = QColor(self.STATUS_COLORS[normalized])
        label = {
            "valid": "Valid",
            "nonoptimal": "Nonoptimal",
            "incomplete": "Incomplete",
            "invalid": "Invalid",
            "unknown": "Unknown",
        }[normalized]
        self.setToolTip(label)
        self.update()

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(self.color)
        painter.drawEllipse(1, 1, 14, 14)
        if self.status == "valid":
            painter.setPen(QPen(QColor("#ffffff"), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.drawLine(4, 8, 7, 11)
            painter.drawLine(7, 11, 12, 5)
        elif self.status == "nonoptimal":
            painter.setBrush(QColor("#ffffff"))
            painter.drawEllipse(6, 6, 4, 4)
        elif self.status in {"incomplete", "invalid"}:
            painter.setPen(QPen(QColor("#ffffff"), 2, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(4, 8, 12, 8)


class ActionLabel(QLabel):
    def __init__(self, text: str, callback=None, parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self.callback = callback
        if callback:
            self.setCursor(Qt.PointingHandCursor)

    def activate(self):
        if self.callback:
            self.callback()

    def mousePressEvent(self, event):  # noqa: N802 - Qt override
        self.activate()
        if event is not None:
            event.accept()


class WaferMap(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setMinimumSize(120, 120)

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(10, 10, -16, -16)
        side = min(rect.width(), rect.height())
        x = rect.center().x() - side // 2
        y = rect.center().y() - side // 2
        painter.setBrush(QColor("#ffffff"))
        painter.setPen(QPen(QColor("#b8b8b8"), 2))
        painter.drawEllipse(x, y, side, side)
        painter.setPen(QPen(QColor("#bbbbbb"), 2))
        painter.drawEllipse(self.width() - 24, self.height() - 24, 8, 8)
        painter.drawLine(self.width() - 18, self.height() - 18, self.width() - 13, self.height() - 13)


class OverviewWaferMap(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.blank = True
        self.zoom_callback = None
        self.setFixedSize(156, 156)
        self.setMouseTracking(True)
        self.setToolTip("Click the magnifier to view the enlarged wafer map")

    def set_blank(self, blank: bool):
        self.blank = bool(blank)
        self.update()

    def _over_magnifier(self, pos) -> bool:
        return pos.x() >= self.width() - 24 and pos.y() >= self.height() - 24

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(2, 0, -26, -24)
        side = min(rect.width(), rect.height())
        x = rect.center().x() - side // 2
        y = rect.center().y() - side // 2

        painter.setBrush(QColor("#ffffff"))
        painter.setPen(QPen(QColor("#cfcfcf"), 1))
        painter.drawEllipse(x, y, side, side)

        if not self.blank:
            center_x = x + side / 2
            center_y = y + side / 2
            radius = side / 2
            clip_step = 5
            painter.setPen(QPen(QColor("#b6b6b6"), 1))
            for offset in range(clip_step, side, clip_step):
                x_line = x + offset
                dx = x_line - center_x
                y_extent = (radius * radius - dx * dx) ** 0.5 if abs(dx) <= radius else 0
                painter.drawLine(int(x_line), int(center_y - y_extent), int(x_line), int(center_y + y_extent))
                y_line = y + offset
                dy = y_line - center_y
                x_extent = (radius * radius - dy * dy) ** 0.5 if abs(dy) <= radius else 0
                painter.drawLine(int(center_x - x_extent), int(y_line), int(center_x + x_extent), int(y_line))
            painter.setPen(QPen(QColor("#00a040"), 2))
            painter.drawLine(int(center_x), int(center_y - 5), int(center_x), int(center_y + 5))
            painter.drawLine(int(center_x - 5), int(center_y), int(center_x + 5), int(center_y))

        glass_x = self.width() - 20
        glass_y = self.height() - 20
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor("#8d8d8d"), 1.6))
        painter.drawEllipse(glass_x, glass_y, 9, 9)
        painter.drawLine(glass_x + 7, glass_y + 7, glass_x + 13, glass_y + 13)

    def mousePressEvent(self, event):  # noqa: N802 - Qt override
        pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
        if self.zoom_callback and self._over_magnifier(pos):
            self.zoom_callback()

    def mouseMoveEvent(self, event):  # noqa: N802 - Qt override
        pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
        self.setCursor(Qt.PointingHandCursor if self._over_magnifier(pos) else Qt.ArrowCursor)


class DieCornerMap(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(118, 118)
        self.setCursor(Qt.PointingHandCursor)
        self.zoom_callback = None

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(4, 2, -26, -22)
        painter.fillRect(rect, QColor("#5f8790"))
        painter.setPen(QPen(QColor("#527780"), 1))
        for offset in range(0, rect.width(), 6):
            painter.drawLine(rect.left() + offset, rect.top(), rect.left() + offset, rect.bottom())
        corner_x = rect.left() + int(rect.width() * 0.46)
        corner_y = rect.top() + int(rect.height() * 0.48)
        painter.setBrush(QColor("#c8c2e8"))
        painter.setPen(QPen(QColor("#8d85bb"), 1))
        painter.drawRect(corner_x, corner_y, rect.right() - corner_x, rect.bottom() - corner_y)
        painter.setPen(QPen(QColor("#24343c"), 2))
        painter.drawLine(corner_x, corner_y, corner_x, rect.bottom())
        painter.drawLine(corner_x, corner_y, rect.right(), corner_y)
        painter.setPen(QPen(QColor("#b8b8b8"), 1.6))
        painter.drawEllipse(self.width() - 18, self.height() - 18, 8, 8)
        painter.drawLine(self.width() - 12, self.height() - 12, self.width() - 6, self.height() - 6)

    def mousePressEvent(self, event):  # noqa: N802 - Qt override
        if self.zoom_callback:
            self.zoom_callback()


class WaferDisk(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.kind = "empty"
        self.orientation = 180
        self.setFixedSize(88, 88)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)

    def set_state(self, kind: str, orientation: int):
        self.kind = kind
        self.orientation = int(orientation)
        self.update()

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        if self.kind in {"empty", "present"}:
            painter.fillRect(self.rect(), thumbnail_surface_color(self))
        paint_wafer_thumbnail(painter, self.width(), self.kind, self.orientation)


def thumbnail_surface_color(widget: QWidget) -> QColor:
    """Color of the dialog or panel behind the thumbnail, so an empty wafer stays unfilled."""
    node = widget.parentWidget()
    while node is not None:
        match = re.search(r"background:\s*(#[0-9A-Fa-f]{6})", node.styleSheet() or "")
        if match:
            return QColor(match.group(1))
        node = node.parentWidget()
    return QColor("#c9c5bb")


def wafer_thumbnail_kind(slot_state: str) -> str:
    if slot_state == "Aligned":
        return "aligned"
    if slot_state in {"Loaded", "Unloading", "Aligning"}:
        return "loaded"
    if slot_state in {"Present", "Loading"}:
        return "present"
    return "empty"


def wafer_notch_cut(origin_x: float, origin_y: float, size: float, orientation: int) -> QPainterPath:
    """Small V-shaped notch at the rim. 0 is up, 90 right, 180 down, 270 left."""
    cut = QPainterPath()
    direction = {0: (0.0, -1.0), 90: (1.0, 0.0), 180: (0.0, 1.0), 270: (-1.0, 0.0)}.get(int(orientation) % 360)
    if direction is None or size <= 0:
        return cut
    dx, dy = direction
    px, py = -dy, dx
    radius = size / 2
    cx = origin_x + radius
    cy = origin_y + radius
    # Small icons need a wider opening than a large wafer drawing, or the direction disappears.
    icon_scale = min(size, 40.0)
    mouth = max(size * 0.12, icon_scale * 0.30)
    depth = max(size * 0.07, icon_scale * 0.20)
    reach = radius + max(1.2, size * 0.03)
    half = mouth / 2
    cut.moveTo(cx + dx * reach + px * half, cy + dy * reach + py * half)
    cut.lineTo(cx + dx * (radius - depth), cy + dy * (radius - depth))
    cut.lineTo(cx + dx * reach - px * half, cy + dy * reach - py * half)
    cut.closeSubpath()
    return cut


def wafer_disk_with_notch(origin_x: float, origin_y: float, size: float, orientation: int) -> QPainterPath:
    """Filled wafer disk with a small rim notch at the given orientation."""
    wafer = QPainterPath()
    wafer.addEllipse(origin_x, origin_y, size, size)
    cut = wafer_notch_cut(origin_x, origin_y, size, orientation)
    if cut.isEmpty():
        return wafer
    return wafer.subtracted(cut)


_LOADED_WAFER = "#62d836"


def paint_slot_wafer_symbol(
    painter: QPainter,
    origin_x: float,
    origin_y: float,
    size: float,
    state: str,
    orientation: int,
):
    """Slot symbol shared by Wafer Handling, Show Wafer, and the status icon."""
    loaded = state in {"Loaded", "Aligned", "Unloading"}
    has_wafer = state in {"Present", "Loading", "Aligning", "Unloading", "Loaded", "Aligned"}
    painter.setPen(QPen(QColor("#2a7a28") if loaded else QColor("#6d6d6d"), 1))
    if loaded:
        painter.setBrush(QColor(_LOADED_WAFER))
        painter.drawPath(wafer_disk_with_notch(origin_x, origin_y, size, int(orientation)))
    else:
        painter.setBrush(QColor("#f7f7f7") if has_wafer else QColor(0, 0, 0, 0))
        painter.drawEllipse(QPointF(origin_x + size / 2, origin_y + size / 2), size / 2, size / 2)
    center_x = origin_x + size / 2
    center_y = origin_y + size / 2
    if state == "Loaded":
        dot = size * (4 / 12)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#111111"))
        painter.drawEllipse(QPointF(center_x, center_y), dot / 2, dot / 2)
    elif state == "Aligned":
        painter.setPen(QPen(QColor("#111111"), max(1, round(size / 12))))
        inset = size * (2 / 12)
        gap = size * (2 / 12)
        painter.drawLine(
            QPointF(origin_x + inset, center_y - gap),
            QPointF(origin_x + size - inset, center_y - gap),
        )
        painter.drawLine(
            QPointF(origin_x + inset, center_y + gap),
            QPointF(origin_x + size - inset, center_y + gap),
        )


def paint_wafer_notch(painter: QPainter, origin_x: float, origin_y: float, size: float, orientation: int, color: str):
    """Cover the rim with a small V so an already drawn disk shows the notch."""
    painter.save()
    painter.setBrush(QColor(color))
    painter.setPen(Qt.NoPen)
    painter.drawPath(wafer_notch_cut(origin_x, origin_y, size, orientation))
    painter.restore()


_MARK = "#5868d8"


def _draw_dotted_circle(painter: QPainter, center_x: float, center_y: float, radius: float):
    count = 36
    dot = max(1.25, radius * 0.04)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#6a6762"))
    for index in range(count):
        angle = 2 * math.pi * index / count
        painter.drawEllipse(
            QPointF(
                center_x + radius * math.cos(angle),
                center_y + radius * math.sin(angle),
            ),
            dot,
            dot,
        )


def paint_wafer_thumbnail(painter: QPainter, side: int, kind: str, orientation: int):
    painter.setRenderHint(QPainter.Antialiasing)
    inset = max(4, round(side * 0.07))
    disk = side - inset * 2
    if kind in {"empty", "present"}:
        _draw_dotted_circle(painter, inset + disk / 2, inset + disk / 2, disk / 2)
        return
    painter.setBrush(QColor("#505050"))
    painter.setPen(QPen(QColor("#222222"), 2))
    painter.drawPath(wafer_disk_with_notch(inset, inset, disk, orientation))
    center_x = inset + disk / 2
    center_y = inset + disk / 2
    if kind == "loaded":
        dot = max(4, round(disk * 0.14))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(_MARK))
        painter.drawEllipse(QPointF(center_x, center_y), dot / 2, dot / 2)
    elif kind == "aligned":
        painter.setPen(QPen(QColor(_MARK), max(2, round(disk * 0.045))))
        half = disk * 0.22
        gap = disk * 0.11
        painter.drawLine(
            QPointF(center_x - half, center_y - gap),
            QPointF(center_x + half, center_y - gap),
        )
        painter.drawLine(
            QPointF(center_x - half, center_y + gap),
            QPointF(center_x + half, center_y + gap),
        )


class EmptyScrollTrack(QWidget):
    """Classic scrollbar with arrow buttons and an empty stippled track."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedWidth(17)
        self.setMinimumHeight(68)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        width = self.width()
        height = self.height()
        button = 16
        self._paint_button(painter, 0, width, button, up=True)
        lower = max(button, height - button)
        self._paint_button(painter, lower, width, button, up=False)
        top = button
        bottom = lower
        if bottom <= top:
            return
        painter.fillRect(0, top, width, bottom - top, QColor("#e7e4db"))
        for y in range(top, bottom):
            for x in range(width):
                if (x + y) % 2 == 0:
                    painter.setPen(QColor("#d5d1c7"))
                else:
                    painter.setPen(QColor("#f3f1ea"))
                painter.drawPoint(x, y)

    def _paint_button(self, painter: QPainter, top: int, width: int, height: int, *, up: bool):
        painter.fillRect(0, top, width, height, QColor("#e4e1d8"))
        painter.setPen(QColor("#ffffff"))
        painter.drawLine(0, top, width - 2, top)
        painter.drawLine(0, top, 0, top + height - 2)
        painter.setPen(QColor("#6d6a62"))
        painter.drawLine(width - 1, top, width - 1, top + height - 1)
        painter.drawLine(0, top + height - 1, width - 1, top + height - 1)
        painter.setBrush(QColor("#2a2a2a"))
        painter.setPen(Qt.NoPen)
        center_x = width // 2
        center_y = top + height // 2
        triangle = QPainterPath()
        if up:
            triangle.moveTo(center_x, center_y - 3)
            triangle.lineTo(center_x + 4, center_y + 2)
            triangle.lineTo(center_x - 4, center_y + 2)
        else:
            triangle.moveTo(center_x, center_y + 3)
            triangle.lineTo(center_x + 4, center_y - 2)
            triangle.lineTo(center_x - 4, center_y - 2)
        triangle.closeSubpath()
        painter.drawPath(triangle)


class SectionBox(QFrame):
    def __init__(self, title: str, parent: Optional[QWidget] = None, display_title: Optional[str] = None):
        super().__init__(parent)
        self.setObjectName("sectionBox")
        self.title = display_title or title
        self.expanded = True
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(
            """
            QFrame#sectionBox {
                background: #f4f2ec;
                border: 1px solid #b3afa4;
                border-radius: 3px;
            }
            QFrame#sectionBox QLabel {
                color: #2a2c30;
            }
            QLabel[heading="true"] {
                font-weight: 700;
                text-decoration: none;
                color: #1d3f86;
            }
            QLabel[heading="true"]:hover {
                color: #2f5fb3;
            }
            QPushButton#sectionHeader {
                background: transparent;
                border: none;
                color: #1d1f23;
                font-size: 11px;
                font-weight: 700;
                text-align: left;
                padding: 2px 0;
                min-height: 20px;
            }
            QPushButton#sectionHeader:hover {
                color: #1d3f86;
            }
            """
        )
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(12, 10, 12, 12)
        outer_layout.setSpacing(8)
        self.header = QPushButton(f"\u25be  {title}")
        self.header.setObjectName("sectionHeader")
        self.header.setCursor(Qt.PointingHandCursor)
        self.header.clicked.connect(self.toggle_collapsed)
        outer_layout.addWidget(self.header)
        self.content_widget = QWidget()
        self.layout = QVBoxLayout(self.content_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(7)
        outer_layout.addWidget(self.content_widget)

    def toggle_collapsed(self):
        self.set_expanded(not self.expanded)

    def set_expanded(self, expanded: bool):
        self.expanded = expanded
        self.content_widget.setVisible(expanded)
        self.header.setText(("\u25be  " if expanded else "\u25b8  ") + self.title)


class GroupHeader(QWidget):
    """Caption bar with a disclosure triangle for a folding module.

    ``variant="classic"`` paints the beige caption bar from the tuner pages;
    ``variant="pane"`` keeps the blue pane caption while adding the triangle.
    Clicking the bar toggles the group it belongs to, and a folded side pane
    paints its title vertically while it sits in its narrow rail.
    """

    HEIGHT = 24
    RAIL_WIDTH = 26

    def __init__(self, title: str, parent: Optional[QWidget] = None, group=None,
                 variant: str = "classic"):
        super().__init__(parent)
        self.title = str(title)
        self.group = group
        self.variant = "pane" if variant == "pane" else "classic"
        self.rail = False
        self._ui_scale = 1.0
        self.setFixedHeight(self.HEIGHT)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def _scaled_height(self) -> int:
        return max(18, int(round(self.HEIGHT * self._ui_scale)))

    def _scaled_rail(self) -> int:
        return max(18, int(round(self.RAIL_WIDTH * self._ui_scale)))

    @property
    def bar_height(self) -> int:
        return self._scaled_height()

    @property
    def rail_width(self) -> int:
        return self._scaled_rail()

    def set_ui_scale(self, scale: float):
        self._ui_scale = max(0.6, float(scale))
        if self.rail:
            width = self._scaled_rail()
            self.setMinimumHeight(width)
            self.setMaximumHeight(16777215)
            self.setFixedWidth(width)
        else:
            self.setFixedHeight(self._scaled_height())
            self.setMinimumWidth(0)
            self.setMaximumWidth(16777215)
        self.update()

    def setText(self, text: str):  # noqa: N802 - mirrors QLabel
        text = str(text)
        if text == self.title:
            return
        self.title = text
        self.setToolTip(text)
        self.update()

    def text(self) -> str:
        return self.title

    def set_rail(self, rail: bool):
        self.rail = bool(rail)
        if self.rail:
            width = self._scaled_rail()
            self.setFixedHeight(width)
            self.setMinimumHeight(width)
            self.setMaximumHeight(16777215)
            self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
            self.setFixedWidth(width)
        else:
            self.setMinimumHeight(self._scaled_height())
            self.setFixedHeight(self._scaled_height())
            self.setMinimumWidth(0)
            self.setMaximumWidth(16777215)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.update()

    def mousePressEvent(self, event):  # noqa: N802 - Qt override
        if event.button() == Qt.LeftButton and self.group is not None:
            self.group.toggle()
            event.accept()
            return
        super().mousePressEvent(event)

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        rect = self.rect()
        pane = self.variant == "pane"
        if pane:
            top = QColor("#3f6fc0")
            bottom = QColor("#2b5699")
            span = max(1, rect.height() - 1)
            for y in range(span):
                blend = y / max(1, span - 1)
                painter.fillRect(
                    0, y, rect.width(), 1,
                    QColor(
                        int(top.red() + (bottom.red() - top.red()) * blend),
                        int(top.green() + (bottom.green() - top.green()) * blend),
                        int(top.blue() + (bottom.blue() - top.blue()) * blend),
                    ),
                )
            painter.setPen(QColor("#1d3f86"))
            painter.drawLine(0, rect.height() - 1, rect.width() - 1, rect.height() - 1)
            ink = QColor("#ffffff")
            triangle_ink = QColor("#ffffff")
        else:
            painter.fillRect(rect, QColor("#e4e1d8"))
            painter.setPen(QColor("#fbf9f3"))
            painter.drawLine(0, 0, rect.width() - 1, 0)
            painter.setPen(QColor("#a8a49a"))
            painter.drawLine(0, rect.height() - 1, rect.width() - 1, rect.height() - 1)
            painter.drawLine(rect.width() - 1, 0, rect.width() - 1, rect.height() - 1)
            ink = QColor("#1d1f23")
            triangle_ink = QColor("#2a2a2a")
        expanded = self.group is None or self.group.is_expanded()
        painter.setPen(Qt.NoPen)
        painter.setBrush(triangle_ink)
        scale = self._ui_scale
        font = QFont(self.font())
        font.setPixelSize(max(9, int(round(11 * scale))))
        if pane:
            font.setBold(True)
        if self.rail:
            center_x = rect.width() // 2
            triangle = QPainterPath()
            triangle.moveTo(center_x - 3 * scale, 5 * scale)
            triangle.lineTo(center_x + 2 * scale, 9 * scale)
            triangle.lineTo(center_x - 3 * scale, 13 * scale)
            triangle.closeSubpath()
            painter.drawPath(triangle)
            painter.setPen(ink)
            painter.setFont(font)
            painter.save()
            painter.translate(center_x, rect.height() - 8 * scale)
            painter.rotate(-90)
            painter.drawText(0, 0, self.title)
            painter.restore()
            return
        center_y = rect.height() // 2
        triangle = QPainterPath()
        if expanded:
            triangle.moveTo(7 * scale, center_y - 3 * scale)
            triangle.lineTo(16 * scale, center_y - 3 * scale)
            triangle.lineTo(11.5 * scale, center_y + 3 * scale)
        else:
            triangle.moveTo(8 * scale, center_y - 4 * scale)
            triangle.lineTo(8 * scale, center_y + 4 * scale)
            triangle.lineTo(14 * scale, center_y)
        triangle.closeSubpath()
        painter.drawPath(triangle)
        painter.setPen(ink)
        painter.setFont(font)
        painter.drawText(
            QRectF(24 * scale, 0, max(0, rect.width() - 30 * scale), rect.height()),
            Qt.AlignVCenter | Qt.AlignLeft,
            self.title,
        )


class CollapsibleGroup(QFrame):
    """A titled module that folds down to its caption bar.

    The body keeps the widgets added through ``body_layout``, so a module can be
    collapsed without disturbing the widgets it holds.  Expansion changes can be
    observed with ``on_expansion_changed`` (used by splitter panes to move the
    freed space to their sibling).
    """

    def __init__(
        self,
        title: str,
        parent: Optional[QWidget] = None,
        *,
        expanded: bool = True,
        margins=(6, 6, 6, 6),
        spacing: int = 4,
        variant: str = "classic",
    ):
        super().__init__(parent)
        self._expanded = bool(expanded)
        self._rail = False
        self._callbacks = []
        self.variant = "pane" if variant == "pane" else "classic"
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setObjectName("tunerModule")
        self.setStyleSheet(
            "QFrame#tunerModule { background: #f4f2ec; border: 1px solid #b3afa4; }"
        )
        # The caption bar and the folded size are managed here; letting the full
        # screen adapter rewrite this module's metrics would unlock a pane that
        # the user folded.
        self._fullscreen_owned_scaling = True
        self.header = GroupHeader(title, self, self, variant=self.variant)
        self.header.setToolTip("Click to collapse or expand this module")
        self.title_label = self.header
        layout.addWidget(self.header, 0)
        self.body = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(*margins)
        self.body_layout.setSpacing(spacing)
        layout.addWidget(self.body, 1)
        self.body.setVisible(self._expanded)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._fold_axis = None

    def title(self) -> str:
        return self.header.title

    def set_title(self, text: str):
        self.header.setText(text)

    def is_expanded(self) -> bool:
        return self._expanded

    def mark_folded(self, axis):
        """Record that a host splitter capped this module ("v", "h", or None).

        The caption bar grows with the UI scale, so the host cap has to be
        refreshed from the same measurement on every scale change.
        """
        self._fold_axis = axis

    def set_ui_scale(self, scale: float):
        self.header.set_ui_scale(scale)
        if self._fold_axis == "v":
            self.setMaximumHeight(self.header.bar_height + 2)
        elif self._fold_axis == "h":
            self.setMaximumWidth(self.header.rail_width)

    def toggle(self):
        self.set_expanded(not self._expanded)

    def on_expansion_changed(self, callback):
        self._callbacks.append(callback)

    def set_rail(self, rail: bool):
        """Narrow the group to a vertical caption rail (used by side panes)."""
        self._rail = bool(rail)
        self.header.set_rail(self._rail)
        self.setMaximumWidth(self.header.rail_width if self._rail else 16777215)
        self.updateGeometry()

    def set_expanded(self, expanded: bool, *, notify: bool = True):
        expanded = bool(expanded)
        if expanded == self._expanded and self.body.isVisibleTo(self) == expanded:
            return
        self._expanded = expanded
        self.body.setVisible(expanded)
        self._apply_stretch()
        self.updateGeometry()
        if notify:
            for callback in list(self._callbacks):
                callback(expanded)

    def _apply_stretch(self):
        """Collapsed modules must not keep a stretch share of the column."""
        parent = self.parentWidget()
        layout = parent.layout() if parent is not None else None
        if layout is None:
            return
        getter = getattr(layout, "stretch", None)
        index = layout.indexOf(self) if hasattr(layout, "indexOf") else -1
        if not callable(getter) or index < 0:
            return
        base = getattr(self, "_stretch_base", None)
        if base is None:
            self._stretch_base = getter(index)
            base = self._stretch_base
        layout.setStretch(index, base if self._expanded else 0)


class FullscreenWindowAdapter(QObject):
    """Maximize fills the screen and every label, button, and chart scales with it.

    Qt keeps the original metrics on the widgets themselves, so leaving full screen
    restores the designed pixel sizes exactly.
    """

    MAXIMUM_WIDGET_SIZE = 16777215

    def __init__(
        self,
        window: QWidget,
        *,
        base=(1200.0, 760.0),
        minimum: float = 1.0,
        maximum: float = 1.8,
        scale_with_size: bool = False,
    ):
        super().__init__(window)
        self.window = window
        self.base = (max(1.0, float(base[0])), max(1.0, float(base[1])))
        self.minimum = float(minimum)
        self.maximum = float(maximum)
        # Dialogs that open at their host window's size (Review, Sensitivity
        # Tuner) must already scale their content even before the user presses
        # maximize; otherwise a screen-sized window still shows a 980 px layout.
        self.scale_with_size = bool(scale_with_size)
        self.scale = 1.0
        self._design_hint = None
        self._switching = False
        self._applying = False
        self._base_font = QFont(window.font())
        self._fullscreen_timer = QTimer(self)
        self._fullscreen_timer.setSingleShot(True)
        self._fullscreen_timer.setInterval(0)
        self._fullscreen_timer.timeout.connect(self._enter_fullscreen)
        window.installEventFilter(self)

    # ------------------------------------------------------------ Qt events
    def eventFilter(self, obj, event):  # noqa: N802 - Qt override
        if obj is self.window:
            kind = event.type()
            if kind == QEvent.WindowStateChange:
                self._sync_fullscreen()
                self.apply_scale()
            elif kind in (QEvent.Resize, QEvent.Show):
                self.apply_scale()
            elif kind in (QEvent.Hide, QEvent.Close):
                # A closed window must never be pulled back on screen later.
                self._fullscreen_timer.stop()
                self._switching = False
            elif kind == QEvent.KeyPress and self._is_fullscreen_shortcut(event):
                self.toggle_fullscreen()
                return True
        return False

    @staticmethod
    def _is_fullscreen_shortcut(event) -> bool:
        """F11/F12 already step through defects, so Alt+Enter owns full screen."""
        if event.isAutoRepeat():
            return False
        if not event.modifiers() & Qt.AltModifier:
            return False
        return event.key() in (Qt.Key_Return, Qt.Key_Enter)

    def toggle_fullscreen(self):
        """Alt+Enter always gives a way back out of the automatic full screen."""
        if self.window.isFullScreen():
            self.window.showNormal()
        else:
            self.window.showFullScreen()

    def _sync_fullscreen(self):
        window = self.window
        if self._switching or window.isMinimized() or not window.isVisible():
            return
        if window.isMaximized() and not window.isFullScreen():
            self._switching = True
            self._fullscreen_timer.start()

    def _enter_fullscreen(self):
        self._switching = False
        window = self.window
        if not window.isVisible() or window.isMinimized():
            return
        if window.isMaximized() and not window.isFullScreen():
            window.showFullScreen()
            self.apply_scale()

    # ------------------------------------------------------------ scaling
    def target_scale(self) -> float:
        window = self.window
        if window.isMinimized():
            return 1.0
        active = window.isMaximized() or window.isFullScreen() or self.scale_with_size
        if not active:
            return 1.0
        width = max(1, window.width())
        height = max(1, window.height())
        scale = min(width / self.base[0], height / self.base[1])
        hint = self._design_min_hint()
        if hint is not None and hint.width() > 0 and hint.height() > 0:
            # A window can never be smaller than its layout, so never scale past
            # the room the full screen actually has. The hint is measured once at
            # design size so growing fonts cannot feed back into the calculation.
            room = min(width / hint.width(), height / hint.height())
            scale = min(scale, room * 0.97)
        return max(self.minimum, min(self.maximum, scale))

    def _design_min_hint(self):
        """Layout floor captured before the first scale is applied."""
        if self._design_hint is None:
            hint = self.window.minimumSizeHint()
            if hint.width() > 0 and hint.height() > 0:
                self._design_hint = QSize(hint)
        return self._design_hint

    def apply_scale(self, force: bool = False):
        if self._applying:
            return
        scale = self.target_scale()
        if not force and abs(scale - self.scale) < 0.02:
            return
        self._applying = True
        try:
            self._apply(scale)
        finally:
            self._applying = False
        self.scale = scale

    def _apply(self, scale: float):
        # Only scale widgets owned by this window. A child QDialog has its own
        # adapter and must not be scaled twice when it is open on top.
        widgets = [self.window] + [
            widget for widget in self.window.findChildren(QWidget)
            if widget.window() is self.window
        ]
        for widget in widgets:
            # Bases must be recorded before the first font/style change, or a
            # stylesheet px rule scaled in this same pass becomes the "design"
            # value for the next one.
            self._capture_metrics_base(widget)
            self._remember_explicit_font(widget)
        font = QFont(self._base_font)
        if self._base_font.pointSizeF() > 0:
            font.setPointSizeF(max(6.0, self._base_font.pointSizeF() * scale))
        self.window.setFont(font)
        for widget in widgets:
            self._scale_font(widget, scale)
            self._scale_stylesheet(widget, scale)
            self._scale_icon(widget, scale)
            self._scale_layout(widget, scale)
            setter = getattr(widget, "set_ui_scale", None)
            if callable(setter):
                setter(scale)
        self._scale_metrics(widgets, scale)
        self.window.update()

    def _scale_metrics(self, widgets, scale: float):
        for widget in widgets:
            self._scale_widget_metrics(widget, scale)

    @staticmethod
    def _scale_layout(widget: QWidget, scale: float):
        """Margins and spacing grow with the fonts so rows keep their breathing room."""
        layout = widget.layout()
        if layout is None:
            return
        horizontal = getattr(layout, "horizontalSpacing", None)
        vertical = getattr(layout, "verticalSpacing", None)
        base = getattr(widget, "_fullscreen_layout_base", None)
        if base is None:
            margins = layout.contentsMargins()
            base = (
                margins.left(), margins.top(), margins.right(), margins.bottom(),
                layout.spacing(),
                horizontal() if callable(horizontal) else None,
                vertical() if callable(vertical) else None,
            )
            widget._fullscreen_layout_base = base
        left, top, right, bottom = (int(round(value * scale)) for value in base[0:4])
        layout.setContentsMargins(left, top, right, bottom)
        for setter, value in (
            (layout.setSpacing, base[4]),
            (getattr(layout, "setHorizontalSpacing", None), base[5]),
            (getattr(layout, "setVerticalSpacing", None), base[6]),
        ):
            if callable(setter) and value is not None and value >= 0:
                setter(int(round(value * scale)))

    @staticmethod
    def _font_signature(font: QFont):
        return (
            font.family(), font.pixelSize(), round(font.pointSizeF(), 2),
            font.weight(), font.bold(), font.italic(),
        )

    def _remember_explicit_font(self, widget: QWidget):
        """Widgets such as custom painted buttons carry their own font."""
        if hasattr(widget, "_fullscreen_font_base"):
            return
        parent = widget.parentWidget()
        current = widget.font()
        if parent is not None and self._font_signature(current) == self._font_signature(parent.font()):
            return
        widget._fullscreen_font_base = QFont(current)

    @classmethod
    def _scale_font(cls, widget: QWidget, scale: float):
        base = getattr(widget, "_fullscreen_font_base", None)
        if base is None:
            return
        font = QFont(base)
        if base.pixelSize() > 0:
            font.setPixelSize(max(6, int(round(base.pixelSize() * scale))))
        elif base.pointSizeF() > 0:
            font.setPointSizeF(max(6.0, base.pointSizeF() * scale))
        else:
            return
        if cls._font_signature(widget.font()) != cls._font_signature(font):
            widget.setFont(font)

    @staticmethod
    def _scale_stylesheet(widget: QWidget, scale: float):
        if getattr(widget, "_fullscreen_owned_scaling", False):
            return
        current = widget.styleSheet() or ""
        written = getattr(widget, "_fullscreen_style_written", None)
        if written is None or current != written:
            widget._fullscreen_style_base = current
        base = widget._fullscreen_style_base
        if "px" not in base:
            widget._fullscreen_style_written = base
            return

        def replace(match):
            name, value = match.group(1), float(match.group(2)) * scale
            return "%s: %gpx" % (name, max(1.0, value))

        scaled = re.sub(
            r"(font-size|min-height|max-height|min-width|max-width|border-radius)"
            r"\s*:\s*([\d.]+)px",
            replace,
            base,
        )

        def replace_padding(match):
            values = re.sub(
                r"([\d.]+)px",
                lambda item: "%gpx" % max(0.0, float(item.group(1)) * scale),
                match.group(2),
            )
            return match.group(1) + values

        scaled = re.sub(r"(padding\s*:\s*)([^;}]*)", replace_padding, scaled)
        widget._fullscreen_style_written = scaled
        if current != scaled:
            widget.setStyleSheet(scaled)

    def _scale_icon(self, widget: QWidget, scale: float):
        if not hasattr(widget, "icon") or not hasattr(widget, "setIconSize"):
            return
        icon = widget.icon()
        if icon is None or icon.isNull():
            return
        current = QSize(widget.iconSize())
        written = getattr(widget, "_fullscreen_icon_written", None)
        if written is None or current != written:
            widget._fullscreen_icon_base = current
        base = widget._fullscreen_icon_base
        if base.width() <= 0 or base.height() <= 0:
            return
        size = QSize(max(8, int(round(base.width() * scale))), max(8, int(round(base.height() * scale))))
        widget._fullscreen_icon_written = size
        if widget.iconSize() != size:
            widget.setIconSize(size)

    def _capture_metrics_base(self, widget: QWidget):
        if widget is self.window or widget.isWindow():
            return
        if getattr(widget, "_fullscreen_owned_scaling", False):
            return
        if getattr(widget, "_fullscreen_metrics_base", None) is None:
            widget._fullscreen_metrics_base = (
                widget.minimumWidth(), widget.minimumHeight(),
                widget.maximumWidth(), widget.maximumHeight(),
            )

    def _scale_widget_metrics(self, widget: QWidget, scale: float):
        if widget is self.window or widget.isWindow():
            return
        if getattr(widget, "_fullscreen_owned_scaling", False):
            return
        limit = self.MAXIMUM_WIDGET_SIZE
        current = (
            widget.minimumWidth(), widget.minimumHeight(),
            widget.maximumWidth(), widget.maximumHeight(),
        )
        # Capture the designed metrics exactly once. Stylesheets may change the
        # minimum size (for example a min-height rule) after the first pass, and
        # re-reading them here would multiply the same widget on every scale
        # change until it no longer fits its window.
        base = getattr(widget, "_fullscreen_metrics_base", None)
        if base is None:
            widget._fullscreen_metrics_base = current
            base = current
        if widget.layout() is not None:
            # Containers must follow their contents. Pinning a container at its
            # designed size would clip the scaled children it has to hold.
            target = base if abs(scale - 1.0) < 0.001 else (0, 0, limit, limit)
            if target != current:
                widget.setMinimumSize(target[0], target[1])
                widget.setMaximumSize(target[2], target[3])
            widget._fullscreen_metrics_written = target
            return
        if not any(base[0:2]) and max(base[2], base[3]) >= limit:
            return

        def scaled_dimension(minimum, maximum):
            """Grow fixed controls, but never inflate a layout's content floor."""
            if maximum >= limit:
                return minimum, maximum
            if minimum == maximum and minimum > 0:
                value = max(1, int(round(minimum * scale)))
                return value, value
            grown_min = max(0, int(round(minimum * scale))) if minimum else 0
            grown_max = max(1, int(round(maximum * scale)))
            return grown_min, grown_max

        if abs(scale - 1.0) < 0.001:
            target = base
        else:
            width = scaled_dimension(base[0], base[2])
            height = scaled_dimension(base[1], base[3])
            target = (width[0], height[0], width[1], height[1])
        if target == current:
            widget._fullscreen_metrics_written = current
            return
        widget.setMinimumSize(target[0], target[1])
        widget.setMaximumSize(target[2], target[3])
        widget._fullscreen_metrics_written = target

class _CaptionGlyphButton(QPushButton):
    """Flat window button drawn with QPainter (no bitmap assets)."""

    def __init__(self, kind: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._kind = kind
        self._hover = False
        self.setFixedSize(38, 26)
        self.setFlat(True)
        self.setFocusPolicy(Qt.NoFocus)
        self.setCursor(Qt.ArrowCursor)
        # This button scales itself from set_ui_scale(); keeping pixel sizes out
        # of the stylesheet avoids the adapter scaling the same value twice.
        self._fullscreen_owned_scaling = True
        self.setStyleSheet(
            "QPushButton { background: transparent; border: none; padding: 0; }"
        )

    def set_ui_scale(self, scale: float):
        size = (max(24, int(round(38 * scale))), max(18, int(round(26 * scale))))
        if (self.width(), self.height()) != size or self.minimumSize().width() != size[0]:
            self.setFixedSize(size[0], size[1])
            self.update()

    def set_kind(self, kind: str):
        if kind != self._kind:
            self._kind = kind
            self.update()

    def enterEvent(self, event):  # noqa: N802 - Qt override
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):  # noqa: N802 - Qt override
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = self.rect()
        closing = self._kind == "close"
        if self._hover:
            painter.fillRect(rect, QColor("#c8362f" if closing else "#c4c0b6"))
        else:
            painter.fillRect(rect, QColor("#d7d4c9"))
        color = "#ffffff" if (self._hover and closing) else "#33322e"
        scale = max(0.75, rect.height() / 26.0)
        painter.setPen(QPen(QColor(color), 1.6 * scale, Qt.SolidLine, Qt.RoundCap))
        center_x = rect.center().x() + scale
        center_y = rect.center().y() + scale

        def point(dx, dy):
            return QPointF(center_x + dx * scale, center_y + dy * scale)

        if self._kind == "minimize":
            painter.drawLine(point(-6, 5), point(6, 5))
        elif self._kind in {"maximize", "restore"}:
            painter.setBrush(Qt.NoBrush)
            if self._kind == "maximize":
                painter.drawRect(QRectF(center_x - 6 * scale, center_y - 5 * scale, 12 * scale, 11 * scale))
            else:
                painter.drawRect(QRectF(center_x - 7 * scale, center_y - 6 * scale, 10 * scale, 9 * scale))
                painter.drawLine(point(-4, -6), point(-4, -8))
                painter.drawLine(point(-4, -8), point(6, -8))
                painter.drawLine(point(6, -8), point(6, 2))
                painter.drawLine(point(6, 2), point(3, 2))
        else:
            painter.drawLine(point(-6, -6), point(6, 6))
            painter.drawLine(point(6, -6), point(-6, 6))
        painter.end()


class WindowCaptionButtons(QWidget):
    """Minimize / Restore / Close controls for frameless full screen windows."""

    def __init__(self, window: QWidget, parent: Optional[QWidget] = None):
        super().__init__(parent)
        # Never store this as ``self.window``: QWidget.window() is a bound Qt
        # method, and shadowing it makes Qt's own layout pass call into a Python
        # object that then crashes during the first show().
        self.host_window = window
        self.setObjectName("windowCaptionButtons")
        self.setStyleSheet("QWidget#windowCaptionButtons { background: #d7d4c9; }")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.minimize_button = _CaptionGlyphButton("minimize", self)
        self.minimize_button.setToolTip("Minimize")
        self.minimize_button.clicked.connect(self.host_window.showMinimized)
        self.restore_button = _CaptionGlyphButton("restore", self)
        self.restore_button.setToolTip("Restore Down")
        self.restore_button.clicked.connect(self.restore_window)
        self.close_button = _CaptionGlyphButton("close", self)
        self.close_button.setToolTip("Close")
        self.close_button.clicked.connect(self.host_window.close)
        for button in (self.minimize_button, self.restore_button, self.close_button):
            layout.addWidget(button)
        self.hide()

    def restore_window(self):
        window = self.host_window
        if window.isFullScreen() or window.isMaximized():
            window.showNormal()
        else:
            window.showMaximized()

    def sync(self):
        """Show the controls whenever the OS title bar is not on screen."""
        full = self.host_window.isFullScreen() or self.host_window.isMaximized()
        self.restore_button.set_kind("restore" if full else "maximize")
        self.restore_button.setToolTip("Restore Down" if full else "Maximize")
        self.setVisible(full)

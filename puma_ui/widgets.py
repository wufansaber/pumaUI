from __future__ import annotations

import math
import re
from typing import Optional

from .qt_compat import (
    QColor,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPainter,
    QPainterPath,
    QPen,
    QPushButton,
    QSizePolicy,
    Qt,
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
                background: #e4e0d8;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #6a6660;
                border-bottom: 1px solid #6a6660;
                color: #111111;
                font-size: 11px;
                font-weight: 500;
                padding: 3px 8px;
                text-align: center;
            }
            QPushButton:hover {
                background: #eeeae2;
            }
            QPushButton:pressed {
                border-top: 1px solid #6a6660;
                border-left: 1px solid #6a6660;
                border-right: 1px solid #ffffff;
                border-bottom: 1px solid #ffffff;
                background: #d4d0c8;
            }
            QPushButton:checked {
                background: #ddd9d1;
                border-top: 1px solid #f7f7f7;
                border-left: 1px solid #f7f7f7;
                border-right: 2px solid #1a1a1a;
                border-bottom: 2px solid #1a1a1a;
                padding: 2px 7px;
            }
            QPushButton:disabled {
                color: #888888;
                background: #d4d0c8;
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
        painter.drawEllipse(origin_x, origin_y, size, size)
    center_x = origin_x + size / 2
    center_y = origin_y + size / 2
    if state == "Loaded":
        dot = size * (4 / 12)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#111111"))
        painter.drawEllipse(center_x - dot / 2, center_y - dot / 2, dot, dot)
    elif state == "Aligned":
        painter.setPen(QPen(QColor("#111111"), max(1, round(size / 12))))
        inset = size * (2 / 12)
        gap = size * (2 / 12)
        painter.drawLine(origin_x + inset, center_y - gap, origin_x + size - inset, center_y - gap)
        painter.drawLine(origin_x + inset, center_y + gap, origin_x + size - inset, center_y + gap)


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
            center_x + radius * math.cos(angle) - dot,
            center_y + radius * math.sin(angle) - dot,
            dot * 2,
            dot * 2,
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
        painter.drawEllipse(center_x - dot / 2, center_y - dot / 2, dot, dot)
    elif kind == "aligned":
        painter.setPen(QPen(QColor(_MARK), max(2, round(disk * 0.045))))
        half = disk * 0.22
        gap = disk * 0.11
        painter.drawLine(center_x - half, center_y - gap, center_x + half, center_y - gap)
        painter.drawLine(center_x - half, center_y + gap, center_x + half, center_y + gap)


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
                background: #efeee9;
                border: 1px solid #aaa8a0;
                border-radius: 8px;
            }
            QLabel {
                color: #202020;
                font-size: 10px;
            }
            QLabel[heading="true"] {
                text-decoration: underline;
                font-weight: 600;
            }
            QPushButton#sectionHeader {
                background: transparent;
                border: none;
                color: #202020;
                font-size: 10px;
                font-weight: 600;
                text-align: left;
                padding: 0;
            }
            """
        )
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(12, 9, 12, 12)
        outer_layout.setSpacing(7)
        self.header = QPushButton(f"v  {title}")
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
        self.header.setText(("v  " if expanded else ">  ") + self.title)

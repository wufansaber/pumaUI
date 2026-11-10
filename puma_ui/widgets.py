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
        self.setMinimumHeight(36)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet(
            """
            QPushButton {
                background: #d8d5cd;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #65625d;
                border-bottom: 1px solid #65625d;
                color: #111111;
                font-size: 10px;
                font-weight: 600;
                padding: 3px 5px;
                text-align: center;
            }
            QPushButton:hover {
                background: #ebe8df;
            }
            QPushButton:pressed {
                border-top: 1px solid #65625d;
                border-left: 1px solid #65625d;
                border-right: 1px solid #ffffff;
                border-bottom: 1px solid #ffffff;
                background: #c8c4bb;
            }
            QPushButton:disabled {
                color: #888888;
                background: #cfcac1;
            }
            """
        )


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
        self.setFixedSize(13, 13)

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
        painter.setBrush(self.color)
        painter.setPen(QPen(QColor("#ffffff"), 1))
        painter.drawEllipse(1, 1, 10, 10)
        painter.setPen(QPen(QColor("#ffffff"), 2))
        if self.status == "valid":
            painter.drawLine(3, 6, 5, 8)
            painter.drawLine(5, 8, 9, 4)
        elif self.status == "nonoptimal":
            painter.drawEllipse(5, 5, 2, 2)
        elif self.status in {"incomplete", "invalid"}:
            painter.drawLine(4, 6, 8, 6)


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
        self.setFixedSize(118, 118)
        self.setCursor(Qt.PointingHandCursor)
        self.zoom_callback = None

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(8, 8, -14, -14)
        side = min(rect.width(), rect.height())
        x = rect.center().x() - side // 2
        y = rect.center().y() - side // 2

        painter.setBrush(QColor("#f5f5f5"))
        painter.setPen(QPen(QColor("#b7b7b7"), 1))
        painter.drawEllipse(x, y, side, side)

        clip_step = 5
        painter.setPen(QPen(QColor("#b6b6b6"), 1))
        for offset in range(clip_step, side, clip_step):
            painter.drawLine(x + offset, y + 4, x + offset, y + side - 4)
            painter.drawLine(x + 4, y + offset, x + side - 4, y + offset)

        painter.setPen(QPen(QColor("#00a040"), 2))
        center_x = x + side // 2
        center_y = y + side // 2
        painter.drawLine(center_x, center_y - 5, center_x, center_y + 5)
        painter.drawLine(center_x - 5, center_y, center_x + 5, center_y)

        painter.setPen(QPen(QColor("#b8b8b8"), 2))
        painter.drawEllipse(self.width() - 21, self.height() - 21, 7, 7)
        painter.drawLine(self.width() - 16, self.height() - 16, self.width() - 11, self.height() - 11)

    def mousePressEvent(self, event):  # noqa: N802 - Qt override
        if self.zoom_callback:
            self.zoom_callback()


class DieCornerMap(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(118, 118)
        self.setCursor(Qt.PointingHandCursor)
        self.zoom_callback = None

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(7, 7, -12, -12)
        painter.setBrush(QColor("#5f8790"))
        painter.setPen(QPen(QColor("#4d747d"), 1))
        painter.drawRect(rect)

        painter.setPen(QPen(QColor("#ed1c24"), 1))
        painter.drawLine(rect.center().x(), rect.top(), rect.center().x(), rect.bottom())
        painter.drawLine(rect.left(), rect.center().y(), rect.right(), rect.center().y())

        painter.setPen(QPen(QColor("#b8b8b8"), 2))
        painter.drawEllipse(self.width() - 20, self.height() - 20, 7, 7)
        painter.drawLine(self.width() - 15, self.height() - 15, self.width() - 10, self.height() - 10)

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
        if self.kind == "empty":
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


def _wafer_disk_symbol(origin_x: float, origin_y: float, size: float, orientation: int) -> QPainterPath:
    wafer = QPainterPath()
    wafer.addEllipse(origin_x, origin_y, size, size)
    direction = {0: (0.0, -1.0), 90: (1.0, 0.0), 180: (0.0, 1.0), 270: (-1.0, 0.0)}.get(int(orientation) % 360)
    if direction is None:
        return wafer
    dx, dy = direction
    radius = size / 2
    bite = size * 0.42
    center_x = origin_x + radius + dx * radius * 1.15
    center_y = origin_y + radius + dy * radius * 1.15
    cut = QPainterPath()
    cut.addEllipse(center_x - bite / 2, center_y - bite / 2, bite, bite)
    return wafer.subtracted(cut)


_MARK = "#5868d8"


def _draw_dotted_circle(painter: QPainter, center_x: float, center_y: float, radius: float):
    count = 36
    dot = max(1.25, radius * 0.04)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#8a8783"))
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
    if kind == "empty":
        _draw_dotted_circle(painter, inset + disk / 2, inset + disk / 2, disk / 2)
        return
    painter.setBrush(QColor("#505050"))
    painter.setPen(QPen(QColor("#222222"), 2))
    if kind in {"loaded", "aligned"}:
        painter.drawPath(_wafer_disk_symbol(inset, inset, disk, orientation))
    else:
        painter.drawEllipse(inset, inset, disk, disk)
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


class SectionBox(QFrame):
    def __init__(self, title: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("sectionBox")
        self.title = title
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

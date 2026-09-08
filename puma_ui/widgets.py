from __future__ import annotations

from typing import Optional

from .qt_compat import (
    QColor,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPainter,
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
        self.setFixedSize(88, 88)

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#505050"))
        painter.setPen(QPen(QColor("#222222"), 2))
        painter.drawEllipse(6, 6, 76, 76)
        painter.setPen(QPen(QColor("#5868d8"), 3))
        painter.drawLine(30, 35, 58, 35)
        painter.drawLine(30, 51, 58, 51)


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

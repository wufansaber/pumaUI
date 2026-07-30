from __future__ import annotations

from typing import List, Tuple

from .config import MAIN_WINDOW_FRACTION
from .modules.configure_overview import DEFAULT_VISIBLE_RECIPE_PARAMETERS, SelectVisibleRecipeParametersDialog
from .modules.image_display import ImageDisplayWindow
from .modules.select_inspection import OpenInspectionRecipeDialog
from .modules.wafer_alignment import AlignmentMenuDialog
from .modules.wafer_handling import WaferHandlingDialog
from .modules.wafer_map import WaferMapSetupDialog
from .modules.wafer_properties import WaferMenuDialog, WaferPropertiesDialog
from .qt_compat import (
    QAction,
    QApplication,
    QColor,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QIcon,
    QLabel,
    QMainWindow,
    QPainter,
    QPen,
    QPixmap,
    QPushButton,
    QScrollArea,
    QSize,
    QSpinBox,
    QStatusBar,
    QStyle,
    QToolBar,
    Qt,
    QVBoxLayout,
    QWidget,
)
from .widgets import ClassicButton, DieCornerMap, OverviewWaferMap, SectionBox, StatusDot


class DieCornerImage(QWidget):
    def __init__(self, size: int, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#5f8790"))
        painter.setPen(QPen(QColor("#527780"), 1))
        for offset in range(0, self.width(), 7):
            painter.drawLine(offset, 0, offset + self.height(), self.height())
        corner_x = int(self.width() * 0.48)
        corner_y = int(self.height() * 0.49)
        painter.setBrush(QColor("#c8c2e8"))
        painter.setPen(QPen(QColor("#8d85bb"), 2))
        painter.drawRect(corner_x, corner_y, self.width(), self.height())
        painter.setPen(QPen(QColor("#42505f"), 3))
        painter.drawLine(corner_x, corner_y, corner_x, self.height())
        painter.drawLine(corner_x, corner_y, self.width(), corner_y)
        painter.setPen(QPen(QColor("#00a040"), 2))
        painter.drawLine(corner_x - 28, corner_y, corner_x + 28, corner_y)
        painter.drawLine(corner_x, corner_y - 28, corner_x, corner_y + 28)
        painter.setPen(QPen(QColor("#b8b8b8"), 2))
        painter.drawEllipse(self.width() - 18, self.height() - 18, 8, 8)
        painter.drawLine(self.width() - 12, self.height() - 12, self.width() - 6, self.height() - 6)


class DieCornerZoomDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Die Corner Image")
        self.setFixedSize(820, 570)
        self.setStyleSheet(
            """
            QDialog {
                background: #ffffff;
                color: #111111;
                font-family: Arial, Helvetica, sans-serif;
            }
            QLabel {
                font-size: 22px;
                font-weight: 700;
            }
            QPushButton#closeButton {
                background: #c93b31;
                border: 1px solid #ffffff;
                color: #ffffff;
                font-size: 18px;
                font-weight: 700;
                padding: 0;
            }
            """
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 20, 18, 18)
        root.setSpacing(10)

        header = QHBoxLayout()
        low_title = QLabel("Low Mag Image")
        high_title = QLabel("High Mag Image")
        header.addWidget(low_title)
        header.addStretch(1)
        header.addWidget(high_title)
        header.addSpacing(150)
        root.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(54)
        body.addWidget(DieCornerImage(255), alignment=Qt.AlignBottom)

        high_frame = QFrame()
        high_frame.setFixedSize(456, 456)
        high_layout = QVBoxLayout(high_frame)
        high_layout.setContentsMargins(0, 0, 0, 0)
        close_row = QHBoxLayout()
        close_row.addStretch(1)
        close_button = QPushButton("x")
        close_button.setObjectName("closeButton")
        close_button.setFixedSize(28, 28)
        close_button.clicked.connect(self.accept)
        close_row.addWidget(close_button)
        high_layout.addLayout(close_row)
        image_row = QHBoxLayout()
        image_row.setContentsMargins(0, 0, 0, 0)
        image_row.addWidget(DieCornerImage(440))
        high_layout.addLayout(image_row)
        body.addWidget(high_frame, alignment=Qt.AlignTop)
        root.addLayout(body, 1)


class WaferMapImage(QWidget):
    def __init__(self, size: int = 460, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#ffffff"))
        rect = self.rect().adjusted(16, 16, -26, -26)
        side = min(rect.width(), rect.height())
        x = rect.center().x() - side // 2
        y = rect.center().y() - side // 2
        painter.setBrush(QColor("#f7f7f7"))
        painter.setPen(QPen(QColor("#b0b0b0"), 2))
        painter.drawEllipse(x, y, side, side)

        center_x = x + side / 2
        center_y = y + side / 2
        radius = side / 2
        step = max(4, side // 48)
        painter.setPen(QPen(QColor("#c5c5c5"), 1))
        for offset in range(step, side, step):
            x_line = x + offset
            dx = x_line - center_x
            y_extent = int((radius * radius - dx * dx) ** 0.5) if abs(dx) <= radius else 0
            painter.drawLine(x_line, int(center_y - y_extent), x_line, int(center_y + y_extent))
            y_line = y + offset
            dy = y_line - center_y
            x_extent = int((radius * radius - dy * dy) ** 0.5) if abs(dy) <= radius else 0
            painter.drawLine(int(center_x - x_extent), y_line, int(center_x + x_extent), y_line)

        painter.setPen(QPen(QColor("#00a040"), 3))
        painter.drawLine(int(center_x), int(center_y - 10), int(center_x), int(center_y + 10))
        painter.drawLine(int(center_x - 10), int(center_y), int(center_x + 10), int(center_y))
        painter.setPen(QPen(QColor("#b8b8b8"), 3))
        painter.drawEllipse(self.width() - 34, self.height() - 34, 13, 13)
        painter.drawLine(self.width() - 24, self.height() - 24, self.width() - 14, self.height() - 14)


class WaferMapZoomDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Wafer Map Image")
        self.setFixedSize(560, 610)
        self.setStyleSheet(
            """
            QDialog {
                background: #ffffff;
                color: #111111;
                font-family: Arial, Helvetica, sans-serif;
            }
            QLabel {
                font-size: 22px;
                font-weight: 700;
            }
            QPushButton#closeButton {
                background: #c93b31;
                border: 1px solid #ffffff;
                color: #ffffff;
                font-size: 18px;
                font-weight: 700;
                padding: 0;
            }
            """
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 18, 18, 18)
        header = QHBoxLayout()
        header.addWidget(QLabel("Wafer Map Image"))
        header.addStretch(1)
        close_button = QPushButton("x")
        close_button.setObjectName("closeButton")
        close_button.setFixedSize(28, 28)
        close_button.clicked.connect(self.accept)
        header.addWidget(close_button)
        root.addLayout(header)
        root.addWidget(WaferMapImage(500), alignment=Qt.AlignCenter)


class CareAreasPreview(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(78, 170)

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.fillRect(self.rect().adjusted(6, 4, -6, -4), QColor("#ffffff"))
        painter.setPen(QPen(QColor("#b8b8b8"), 1))
        painter.drawRect(self.rect().adjusted(6, 4, -6, -4))
        painter.setBrush(QColor("#7d8700"))
        painter.setPen(Qt.NoPen)
        painter.drawRect(18, 22, 20, 16)
        painter.setBrush(QColor("#bd8700"))
        painter.drawRect(18, 60, 24, 30)
        painter.setBrush(QColor("#00c020"))
        painter.drawRect(24, 126, 6, 34)
        painter.setPen(QPen(QColor("#b8b8b8"), 2))
        painter.drawEllipse(self.width() - 18, self.height() - 18, 8, 8)
        painter.drawLine(self.width() - 12, self.height() - 12, self.width() - 6, self.height() - 6)


class SamplePlanPreview(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(155, 155)

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(8, 8, -16, -16)
        side = min(rect.width(), rect.height())
        x = rect.center().x() - side // 2
        y = rect.center().y() - side // 2
        painter.setBrush(QColor("#ffffff"))
        painter.setPen(QPen(QColor("#c0c0c0"), 1))
        painter.drawEllipse(x, y, side, side)
        center_x = x + side / 2
        center_y = y + side / 2
        radius = side / 2
        step = 5
        painter.setPen(QPen(QColor("#5a6680"), 1))
        for offset in range(step, side, step):
            x_line = x + offset
            dx = x_line - center_x
            y_extent = int((radius * radius - dx * dx) ** 0.5) if abs(dx) <= radius else 0
            painter.drawLine(x_line, int(center_y - y_extent), x_line, int(center_y + y_extent))
            y_line = y + offset
            dy = y_line - center_y
            x_extent = int((radius * radius - dy * dy) ** 0.5) if abs(dy) <= radius else 0
            painter.drawLine(int(center_x - x_extent), y_line, int(center_x + x_extent), y_line)
        painter.setPen(QPen(QColor("#b8b8b8"), 2))
        painter.drawEllipse(self.width() - 22, self.height() - 22, 8, 8)
        painter.drawLine(self.width() - 16, self.height() - 16, self.width() - 10, self.height() - 10)


class PumaMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wafer Inspection System - Puma 9980 UI")
        self._resize_for_screen(default_width=1600, default_height=900, minimum_width=1180, minimum_height=760)
        self.visible_recipe_parameters = dict(DEFAULT_VISIBLE_RECIPE_PARAMETERS)
        self.recipe_overview_sections = {}
        self.recipe_overview_groups = {}
        self.recipe_overview_rows = {}
        self.alignment_context_active = False
        self.image_display_window = None
        self._build_menus()
        self._build_toolbar()
        self._build_central()
        self._build_statusbar()
        self._apply_recipe_overview_visibility()
        self.setStyleSheet(
            """
            QMainWindow, QWidget#root {
                background: #cfcbc2;
                color: #111111;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10px;
            }
            QMenuBar {
                background: #d7d4cc;
                border-bottom: 1px solid #8c8982;
            }
            QMenuBar::item {
                padding: 2px 8px;
            }
            QToolBar {
                background: #c7c3ba;
                border-top: 1px solid #f8f8f8;
                border-bottom: 1px solid #79766e;
                spacing: 2px;
            }
            QComboBox, QSpinBox {
                background: #ffffff;
                border: 1px solid #77736b;
                min-height: 24px;
                font-size: 10px;
            }
            QStatusBar {
                background: #d7d4cc;
                border-top: 1px solid #8f8b82;
                font-size: 10px;
            }
            """
        )

    def _resize_for_screen(
        self,
        default_width: int,
        default_height: int,
        minimum_width: int,
        minimum_height: int,
    ):
        screen = QApplication.primaryScreen()
        if not screen:
            self.resize(default_width, default_height)
            self.setMinimumSize(minimum_width, minimum_height)
            return

        available = screen.availableGeometry()
        width = min(default_width, max(minimum_width, int(available.width() * MAIN_WINDOW_FRACTION)))
        height = min(default_height, max(minimum_height, int(available.height() * MAIN_WINDOW_FRACTION)))
        self.resize(width, height)
        self.setMinimumSize(minimum_width, minimum_height)
        self.move(
            available.x() + (available.width() - width) // 2,
            available.y() + (available.height() - height) // 2,
        )

    def _build_menus(self):
        menu = self.menuBar()
        for name in ["File", "Edit", "Optics"]:
            submenu = menu.addMenu(name)
            submenu.addAction(f"{name} placeholder")

        setup_menu = menu.addMenu("Set Up")
        wafer_menu = setup_menu.addMenu("Wafer")
        wafer_properties = QAction("Wafer Properties", self)
        wafer_properties.triggered.connect(self.open_wafer_properties)
        wafer_menu.addAction(wafer_properties)
        alignment = QAction("Alignment", self)
        alignment.triggered.connect(self.open_alignment_menu)
        wafer_menu.addAction(alignment)
        wafermap = QAction("Wafermap", self)
        wafermap.triggered.connect(self.open_wafer_map)
        wafer_menu.addAction(wafermap)

        view_menu = menu.addMenu("View")
        self.image_display_action = QAction("Image Display", self)
        self.image_display_action.setEnabled(False)
        self.image_display_action.triggered.connect(self.open_image_display)
        view_menu.addAction(self.image_display_action)
        view_menu.addSeparator()
        view_menu.addAction("View placeholder")

        for name in ["Tools", "Help"]:
            submenu = menu.addMenu(name)
            submenu.addAction(f"{name} placeholder")

    def _wafer_handling_icon(self) -> QIcon:
        pixmap = QPixmap(24, 24)
        pixmap.fill(QColor(0, 0, 0, 0))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#1bb7c8"))
        painter.setPen(QPen(QColor("#101010"), 2))
        painter.drawEllipse(4, 3, 16, 17)
        painter.setPen(QPen(QColor("#101010"), 2))
        painter.drawLine(8, 8, 16, 8)
        painter.drawLine(8, 11, 16, 11)
        painter.drawLine(8, 14, 16, 14)
        painter.end()

        return QIcon(pixmap)

    def _toolbar_icon(self, kind: str) -> QIcon:
        pixmap = QPixmap(24, 24)
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor("#202020"), 1))
        painter.setBrush(QColor("#e7e4da"))
        painter.drawRect(3, 3, 18, 18)

        if kind == "wafer_handling":
            painter.end()
            return self._wafer_handling_icon()
        if kind == "job_queue":
            painter.setBrush(QColor("#f7e66b"))
            painter.drawRect(6, 6, 12, 12)
            painter.setPen(QPen(QColor("#159000"), 2))
            painter.drawEllipse(8, 8, 8, 5)
            painter.drawLine(9, 15, 16, 11)
        elif kind == "print":
            painter.setBrush(QColor("#d7d7d7"))
            painter.drawRect(6, 8, 12, 9)
            painter.drawRect(8, 4, 8, 5)
            painter.setPen(QPen(QColor("#f0c400"), 2))
            painter.drawLine(8, 16, 16, 16)
        elif kind == "manual":
            painter.setPen(QPen(QColor("#111111"), 3))
            painter.drawText(8, 18, "?")
        elif kind == "alarm":
            painter.setBrush(QColor("#ffef30"))
            painter.setPen(QPen(QColor("#333333"), 1))
            painter.drawPolygon(
                [
                    self._point(12, 4),
                    self._point(21, 20),
                    self._point(3, 20),
                ]
            )
            painter.setPen(QPen(QColor("#111111"), 2))
            painter.drawLine(12, 9, 12, 15)
            painter.drawPoint(12, 18)
        elif kind == "disengage_optics":
            painter.setBrush(QColor("#a7e0e7"))
            painter.drawRect(7, 8, 8, 7)
            painter.setPen(QPen(QColor("#111111"), 1))
            painter.drawLine(5, 12, 17, 7)
        elif kind == "engage_optics":
            painter.setBrush(QColor("#a7e0e7"))
            painter.drawRect(7, 8, 8, 7)
            painter.setPen(QPen(QColor("#cc0000"), 2))
            painter.drawLine(5, 5, 18, 18)
            painter.drawLine(18, 5, 5, 18)
        elif kind == "apply_optics":
            painter.setBrush(QColor("#99dbe0"))
            painter.drawRect(5, 8, 11, 8)
            painter.setPen(QPen(QColor("#006060"), 3))
            painter.drawLine(17, 6, 8, 12)
            painter.drawLine(8, 12, 17, 18)
        elif kind == "pixel_size":
            painter.setBrush(QColor("#4242d6"))
            painter.drawEllipse(7, 7, 9, 9)
            painter.setPen(QPen(QColor("#111111"), 2))
            painter.drawLine(15, 15, 20, 20)
        elif kind == "imaging_mode":
            for index, color in enumerate(["#00a3ff", "#ff8a00", "#111111"]):
                painter.setBrush(QColor(color))
                painter.drawRect(6 + index * 4, 6, 3, 12)
        elif kind == "aperture":
            painter.setBrush(QColor("#111111"))
            painter.drawEllipse(6, 6, 12, 12)
            painter.setBrush(QColor("#ffffff"))
            painter.drawEllipse(9, 9, 6, 6)
        elif kind == "illumination":
            painter.setBrush(QColor("#ffffff"))
            painter.drawEllipse(8, 5, 8, 10)
            painter.drawRect(10, 15, 4, 4)
        elif kind == "manual_light":
            painter.setPen(QPen(QColor("#555555"), 2))
            painter.drawLine(7, 7, 15, 17)
            painter.drawLine(12, 6, 17, 16)
            painter.drawLine(8, 15, 15, 15)
        elif kind == "auto_light":
            painter.setPen(QPen(QColor("#555555"), 2))
            painter.drawLine(7, 7, 15, 17)
            painter.drawLine(12, 6, 17, 16)
            painter.setPen(QPen(QColor("#cc0000"), 2))
            painter.drawLine(5, 5, 19, 19)
        elif kind == "focus_offset":
            painter.setPen(QPen(QColor("#111111"), 1))
            painter.drawLine(12, 4, 12, 20)
            painter.drawLine(5, 12, 19, 12)
            painter.setBrush(QColor("#0b8f24"))
            painter.drawEllipse(9, 9, 6, 6)
        elif kind == "advanced_optics":
            painter.drawText(8, 16, "...")
        elif kind == "ruler":
            painter.setBrush(QColor("#d9d9d9"))
            painter.drawRect(5, 9, 14, 6)
            for x in range(7, 18, 3):
                painter.drawLine(x, 9, x, 13)
        elif kind == "run_wafer":
            painter.setBrush(QColor("#1aae26"))
            painter.drawEllipse(7, 8, 10, 8)
            painter.setPen(QPen(QColor("#d8ff4a"), 1))
            painter.drawLine(12, 5, 12, 16)
        elif kind == "review_wafer":
            painter.setBrush(QColor("#18c33a"))
            painter.drawEllipse(6, 6, 12, 12)
            painter.setPen(QPen(QColor("#0033cc"), 2))
            painter.drawEllipse(9, 9, 5, 5)
            painter.drawLine(14, 14, 19, 19)
        elif kind == "wafermap_image":
            painter.setBrush(QColor("#22c73a"))
            painter.drawEllipse(6, 6, 12, 12)
            painter.setPen(QPen(QColor("#cc00cc"), 2))
            painter.drawLine(8, 11, 12, 17)
            painter.drawLine(12, 17, 17, 7)
        elif kind == "wafermap_zoom":
            painter.setBrush(QColor("#2bd044"))
            painter.drawEllipse(5, 6, 11, 11)
            painter.setPen(QPen(QColor("#005500"), 2))
            painter.drawLine(13, 14, 19, 19)
        elif kind == "rotate_wafer":
            painter.setBrush(QColor("#2bd044"))
            painter.drawEllipse(6, 6, 12, 12)
            painter.setPen(QPen(QColor("#ff0000"), 2))
            painter.drawArc(7, 5, 11, 11, 30 * 16, 270 * 16)

        painter.end()
        return QIcon(pixmap)

    @staticmethod
    def _point(x: int, y: int):
        try:
            from PySide6.QtCore import QPoint
        except ImportError:
            from PyQt5.QtCore import QPoint
        return QPoint(x, y)

    def _add_tool_button(self, toolbar: QToolBar, kind: str, tooltip: str, callback=None) -> QPushButton:
        button = QPushButton("")
        button.setIcon(self._toolbar_icon(kind))
        button.setIconSize(QSize(24, 24))
        button.setToolTip(tooltip)
        button.setFixedSize(30, 28)
        button.clicked.connect(callback or (lambda checked=False, text=tooltip: self._toolbar_status(text)))
        toolbar.addWidget(button)
        return button

    def _toolbar_status(self, text: str):
        self.statusBar().showMessage(text)

    def _build_toolbar(self):
        toolbar = QToolBar("Toolbar")
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self._add_tool_button(toolbar, "wafer_handling", "Wafer and Cassette Handling", self.open_wafer_handling)
        self._add_tool_button(toolbar, "job_queue", "Inspection Job Queue")
        self._add_tool_button(toolbar, "print", "Print View")
        self._add_tool_button(toolbar, "manual", "User Manual")
        self._add_tool_button(toolbar, "alarm", "Alarm Alert")
        toolbar.addSeparator()

        self._add_tool_button(toolbar, "disengage_optics", "Disengage Optics")
        self._add_tool_button(toolbar, "engage_optics", "Engage Optics")
        self._add_tool_button(toolbar, "apply_optics", "Apply Optics Settings")
        self._add_tool_button(toolbar, "pixel_size", "Pixel Size")
        magnification = QComboBox()
        magnification.addItems(["2.000 (5X)", "1.000 (2.5X)", "4.000 (10X)"])
        magnification.setFixedWidth(104)
        magnification.setToolTip("Pixel Size")
        toolbar.addWidget(magnification)

        self._add_tool_button(toolbar, "imaging_mode", "Imaging Mode")
        field = QComboBox()
        field.addItems(["BrightField", "DarkField", "Laser"])
        field.setFixedWidth(118)
        field.setToolTip("Imaging Mode")
        toolbar.addWidget(field)

        self._add_tool_button(toolbar, "aperture", "Aperture")
        percent = QSpinBox()
        percent.setRange(0, 100)
        percent.setValue(20)
        percent.setSuffix(" %")
        percent.setFixedWidth(72)
        percent.setToolTip("Aperture")
        toolbar.addWidget(percent)

        self._add_tool_button(toolbar, "illumination", "Illumination Level")
        self._add_tool_button(toolbar, "manual_light", "Manual Light Activated")
        self._add_tool_button(toolbar, "auto_light", "Automatic Light Activated")
        self._add_tool_button(toolbar, "focus_offset", "Focus Offset")
        scale = QSpinBox()
        scale.setRange(-1000, 1000)
        scale.setValue(0)
        scale.setSuffix(" um")
        scale.setFixedWidth(72)
        scale.setToolTip("Focus Offset")
        toolbar.addWidget(scale)
        self._add_tool_button(toolbar, "advanced_optics", "Advanced Optics Settings")
        self._add_tool_button(toolbar, "ruler", "Ruler")

        toolbar.addSeparator()
        self._add_tool_button(toolbar, "run_wafer", "Run One Wafer")
        self._add_tool_button(toolbar, "review_wafer", "Review Wafer")
        self._add_tool_button(toolbar, "wafermap_image", "Toggle Wafermap Image")
        self._add_tool_button(toolbar, "wafermap_zoom", "Wafermap Zoom")

        zoom = QComboBox()
        zoom.addItems(["100", "75", "50", "25"])
        zoom.setFixedWidth(66)
        zoom.setToolTip("Wafermap Zoom")
        toolbar.addWidget(zoom)
        self._add_tool_button(toolbar, "rotate_wafer", "Rotate Wafer")

    def _build_central(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)

        main_layout = QVBoxLayout(root)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self._navigation_strip())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._left_navigation())
        overview_scroll = QScrollArea()
        overview_scroll.setWidgetResizable(True)
        overview_scroll.setFrameShape(QFrame.NoFrame)
        overview_scroll.setWidget(self._recipe_overview())
        body.addWidget(overview_scroll, 1)
        main_layout.addLayout(body, 1)

    def _navigation_strip(self) -> QWidget:
        strip = QFrame()
        strip.setFixedHeight(34)
        strip.setStyleSheet(
            """
            QFrame {
                background: #bbb7af;
                border-bottom: 2px solid #77746c;
            }
            QPushButton {
                background: #d8d5cd;
                border: 1px solid #88847c;
                min-height: 24px;
                padding: 1px 10px;
                font-weight: 600;
            }
            QPushButton:disabled {
                color: #888888;
            }
            """
        )
        layout = QHBoxLayout(strip)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(5)
        layout.addWidget(QPushButton("< Back"))
        forward = QPushButton(">")
        forward.setEnabled(False)
        forward.setFixedWidth(30)
        layout.addWidget(forward)
        home = QPushButton("Home")
        home.setFixedWidth(58)
        layout.addWidget(home)
        setup = QPushButton("Setup")
        setup.setFixedWidth(72)
        layout.addWidget(setup)
        layout.addStretch(1)
        navigate = QPushButton("Navigate")
        navigate.setEnabled(False)
        navigate.setFixedWidth(72)
        layout.addWidget(navigate)
        return strip

    def _left_navigation(self) -> QWidget:
        panel = QFrame()
        panel.setFixedWidth(116)
        panel.setStyleSheet(
            """
            QFrame {
                background: #cfcbc2;
                border-right: 2px solid #77746c;
            }
            """
        )
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(9)

        items = [
            ("Select\nInspection", False, True, self.open_inspection_recipe),
            ("Wafer", True, True, self.open_wafer_menu),
            ("Tests", True, False, None),
            ("Lot Plan", False, True, None),
            ("Wafer Post\nProcessing", False, True, None),
            ("Setup Run", True, True, None),
            ("Save\nInspection", False, True, None),
            ("Recipe\nGeneration", False, True, None),
        ]
        for label, arrow, enabled, handler in items:
            button = ClassicButton(label, arrow=arrow)
            button.setEnabled(enabled)
            if handler:
                button.clicked.connect(handler)
            layout.addWidget(button)

        layout.addStretch(1)
        end = ClassicButton("End")
        end.setMinimumHeight(34)
        layout.addWidget(end)
        return panel

    def _recipe_overview(self) -> QWidget:
        area = QWidget()
        layout = QVBoxLayout(area)
        layout.setContentsMargins(18, 12, 16, 16)
        layout.setSpacing(10)

        top_row = QHBoxLayout()
        title = QLabel("Recipe Overview")
        title.setStyleSheet("font-weight: 700; text-decoration: underline;")
        top_row.addWidget(title)
        top_row.addStretch(1)
        configure = QPushButton("Configure")
        configure.setFixedSize(86, 26)
        configure.setStyleSheet(
            "background: #e5e2da; border: 1px solid #88847c; border-radius: 4px;"
        )
        configure.clicked.connect(self.configure_recipe_overview)
        top_row.addWidget(configure)
        layout.addLayout(top_row)

        recipe_properties = self._recipe_properties_box()
        wafer_layout = self._wafer_layout_box()
        test_one = self._test_one_box()
        recipe_properties.set_expanded(False)
        wafer_layout.set_expanded(False)
        layout.addWidget(recipe_properties)
        layout.addWidget(wafer_layout)
        layout.addWidget(test_one)
        layout.addStretch(1)
        return area

    def _recipe_properties_box(self) -> QWidget:
        box = SectionBox("Recipe Properties")
        self.recipe_overview_sections["Recipe Properties"] = box
        self.recipe_property_labels = {}
        self.creation_property_labels = {}
        self.load_save_status_labels = {}
        grid = QGridLayout()
        grid.setHorizontalSpacing(32)
        grid.setVerticalSpacing(3)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)
        box.layout.addLayout(grid)

        self._add_group(
            grid,
            0,
            "Inspection Properties",
            [
                ("Recipe Name", "Vert_Seg0123"),
                ("Device Name", "Device1"),
                ("Layer Name", "Layer1"),
                ("Recipe Type", "Normal"),
                ("Approval", "Engineering"),
            ],
        )
        self._add_group(
            grid,
            1,
            "Creation Properties",
            [
                ("Creation Time", "2011-03-31 23:49:06"),
                ("Last Modification", "2011-09-01 09:27:57"),
                ("Software Version", "9.7.064"),
                ("History Log", ""),
            ],
        )
        self._add_group(
            grid,
            2,
            "Load/Save Status",
            [("Validation Status", "<b>Valid recipe:</b> The recipe successfully passed validation on<br>9/1/2011")],
            with_status=True,
        )
        return box

    def _wafer_layout_box(self) -> QWidget:
        box = SectionBox("Wafer Layout")
        self.recipe_overview_sections["Wafer Layout"] = box
        self.wafer_property_labels = {}
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(4)
        for column in range(7):
            grid.setColumnStretch(column, 0)
        box.layout.addLayout(grid)

        self._add_group(
            grid,
            0,
            "Wafer Properties",
            [
                ("Diameter", "300 mm"),
                ("Wafer Type", "Patterned"),
                ("Orientation", "Down (180 deg.)"),
                ("Align Mark", "Notched"),
                ("Laser Power Sensitive", "Yes"),
                ("Laser Power Factor", "0.03500"),
                ("Layer", "_KT_Low_Power [ 0.03500 ]"),
                ("Dark Wafer", "No"),
                ("Wafer Darkness Level", "Dark"),
            ],
        )
        self._add_alignment_group(grid, 1)
        self._add_registration_sites_group(grid, 2)
        self._add_group(
            grid,
            3,
            "Die Layout",
            [
                ("Die Width", "5.100.1 um"),
                ("Die Height", "16.600.2 um"),
                ("Reticle Size", "Not used"),
                ("Street Size", "99.9 um x 100.2 um"),
                ("Inner Die", "No"),
                ("Valid Dies", "724"),
            ],
            with_status=True,
        )
        self._add_die_corner_group(grid, 4)
        self._add_wafer_map_group(grid, 5)
        self._add_group(grid, 6, "Design Files", [("Selected RDF", "-")])
        return box

    def _test_one_box(self) -> QWidget:
        box = SectionBox("Test 1")
        self.recipe_overview_sections["Test 1"] = box
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(24)
        box.layout.addLayout(grid)

        self._add_test_group(
            grid,
            0,
            0,
            "Test Properties",
            [
                ("Test Name", "Test 1"),
                ("Orientation", "180°"),
                ("Light Trained", "Trained on tool"),
                ("Save Patch Images", "Yes"),
                ("Save Feature Vectors", "Yes"),
                ("iDO Classifier", "-"),
                ("RBB Recipe", "-"),
                ("Dynamic Range", "Extended"),
            ],
            width=245,
        )
        self._add_test_group(
            grid,
            0,
            1,
            "Inspection Optics",
            [
                ("Magnification\n(Pixel Size)", "SL815"),
                ("Focus Offset", "0 um"),
                ("Polarization", "P-POL"),
                ("Incidence Angle", "Oblique"),
                ("Speed", "High Throughput Mode"),
            ],
            width=270,
        )
        self._add_collection_optics_group(grid, 0, 2)
        self._add_test_group(
            grid,
            0,
            3,
            "Illumination Level Optimization",
            [("Noise Boxes", "-")],
            width=245,
            push_to_bottom=True,
        )
        self._add_test_group(
            grid,
            0,
            4,
            "Fourier Filter",
            [
                ("1 (Left)", "On"),
                ("Training Results", "0.0"),
                ("", ""),
                ("2 (Right)", "On"),
                ("Training Results", "0.0"),
                ("", ""),
                ("3 (Center)", "On"),
                ("Training Results", "0.0"),
            ],
            width=220,
        )
        self._add_light_level_group(grid, 1, 0)
        self._add_test_group(
            grid,
            1,
            1,
            "Sensitivity",
            [
                ("Channel 1 (Left)", ""),
                ("Selected Algorithms", "HLAT"),
                ("", ""),
                ("Channel 2 (Right)", ""),
                ("Selected Algorithms", "HLAT"),
                ("", ""),
                ("Channel 3 (Center)", ""),
                ("Selected Algorithms", "HLAT"),
                ("", ""),
                ("Defined Regions", "R1, R2, R3"),
                ("Segmentation", "In Use"),
            ],
            width=255,
        )
        self._add_test_group(
            grid,
            1,
            2,
            "Defect Filters",
            [
                ("Region :", "R1"),
                ("Filters Defined", "No"),
                ("", ""),
                ("Region :", "R2"),
                ("Filters Defined", "No"),
                ("", ""),
                ("Region :", "R3"),
                ("Filters Defined", "No"),
            ],
            width=160,
        )
        self._add_care_areas_group(grid, 1, 3)
        self._add_sample_plan_group(grid, 1, 4)
        return box

    def _add_test_group(
        self,
        grid: QGridLayout,
        row_index: int,
        column: int,
        title: str,
        rows: List[Tuple[str, str]],
        *,
        width: int,
        push_to_bottom: bool = False,
    ):
        group = QFrame()
        self.recipe_overview_groups[title] = group
        group.setMinimumWidth(width)
        group.setStyleSheet("border-right: 1px solid #d1cec5;")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(6, 0, 12, 0)
        layout.setSpacing(4)
        title_label = QLabel(title)
        title_label.setProperty("heading", True)
        layout.addWidget(title_label)
        if push_to_bottom:
            layout.addStretch(1)
        for label, value in rows:
            if not label and not value:
                layout.addSpacing(10)
                continue
            line = QHBoxLayout()
            line.setSpacing(8)
            name = QLabel(label)
            name.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            name.setMinimumWidth(104)
            val = QLabel(value)
            val.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            val.setWordWrap(True)
            line.addWidget(name)
            line.addWidget(val)
            line.addStretch(1)
            layout.addLayout(line)
        if not push_to_bottom:
            layout.addStretch(1)
        grid.addWidget(group, row_index, column)

    def _add_collection_optics_group(self, grid: QGridLayout, row_index: int, column: int):
        group = QFrame()
        self.recipe_overview_groups["Collection Optics"] = group
        group.setMinimumWidth(210)
        group.setStyleSheet("border-right: 1px solid #d1cec5;")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(6, 0, 12, 0)
        layout.setSpacing(4)
        title = QLabel("Collection Optics")
        title.setProperty("heading", True)
        layout.addWidget(title)
        for channel in ["Channel 1 (Left)", "Channel 2 (Right)", "Channel 3 (Center)"]:
            layout.addWidget(QLabel(f"{channel}  On"))
            for label, value in [("Polarization", "None"), ("Iris", "Open")]:
                line = QHBoxLayout()
                name = QLabel(label)
                name.setMinimumWidth(92)
                line.addWidget(name)
                line.addWidget(QLabel(value))
                line.addStretch(1)
                layout.addLayout(line)
            layout.addSpacing(10)
        layout.addStretch(1)
        grid.addWidget(group, row_index, column)

    def _add_light_level_group(self, grid: QGridLayout, row_index: int, column: int):
        group = QFrame()
        self.recipe_overview_groups["Light Level Sensitivity"] = group
        group.setMinimumWidth(245)
        group.setStyleSheet("border-right: 1px solid #d1cec5;")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(6, 0, 12, 0)
        layout.setSpacing(4)
        title = QLabel("Light Level")
        title.setProperty("heading", True)
        layout.addWidget(title)
        for row in [
            ("Channels", "CH1      CH2      CH3"),
            ("Light Levels", "8.6       7.4       2.3"),
            ("Camera Gains", "16.00    16.00    16.00"),
            ("PILO Noise Values", "24.1     23.1     79.4"),
            ("", ""),
            ("Exposures", ""),
        ]:
            if not row[0] and not row[1]:
                layout.addSpacing(12)
                continue
            line = QHBoxLayout()
            name = QLabel(row[0])
            name.setMinimumWidth(126)
            line.addWidget(name)
            line.addWidget(QLabel(row[1]))
            line.addStretch(1)
            layout.addLayout(line)
        layout.addStretch(1)
        grid.addWidget(group, row_index, column)

    def _add_care_areas_group(self, grid: QGridLayout, row_index: int, column: int):
        group = QFrame()
        self.recipe_overview_groups["Care Areas"] = group
        group.setMinimumWidth(170)
        group.setStyleSheet("border-right: 1px solid #d1cec5;")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(6, 0, 12, 0)
        title = QLabel("Care Areas")
        title.setProperty("heading", True)
        layout.addWidget(title)
        layout.addWidget(CareAreasPreview(), alignment=Qt.AlignLeft)
        layout.addWidget(QLabel("CA Border  4.02 um x 2.64 um"))
        layout.addStretch(1)
        grid.addWidget(group, row_index, column)

    def _add_sample_plan_group(self, grid: QGridLayout, row_index: int, column: int):
        group = QFrame()
        self.recipe_overview_groups["Sample Plan"] = group
        group.setMinimumWidth(210)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(6, 0, 12, 0)
        title = QLabel("Sample Plan")
        title.setProperty("heading", True)
        layout.addWidget(title)
        layout.addWidget(SamplePlanPreview(), alignment=Qt.AlignLeft)
        layout.addWidget(QLabel("Inspection Type   Full Die"))
        layout.addStretch(1)
        grid.addWidget(group, row_index, column)

    def _add_group(
        self,
        grid: QGridLayout,
        column: int,
        title: str,
        rows: List[Tuple[str, str]],
        *,
        with_status: bool = False,
    ):
        group = QFrame()
        self.recipe_overview_groups[title] = group
        group.setStyleSheet("border-right: 1px solid #d1cec5;")
        if title in {"Inspection Properties", "Creation Properties", "Load/Save Status"}:
            group.setMinimumWidth(250 if title != "Load/Save Status" else 360)
        elif title == "Wafer Properties":
            group.setMinimumWidth(160)
        elif title == "Die Layout":
            group.setMinimumWidth(160)
        elif title == "Design Files":
            group.setMinimumWidth(130)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(6, 0, 12, 0)
        layout.setSpacing(3)

        header = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setProperty("heading", True)
        header.addWidget(title_label)
        if with_status:
            header.addWidget(StatusDot("#00a040"))
        header.addStretch(1)
        layout.addLayout(header)

        for label, value in rows:
            row = QHBoxLayout()
            row.setSpacing(8)
            row_holder = QWidget()
            row_holder.setLayout(row)
            name = QLabel(label)
            name.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            if title in {"Inspection Properties", "Creation Properties"}:
                name_width = 86
            elif title in {"Wafer Properties", "Die Layout", "Design Files"}:
                name_width = 76
            else:
                name_width = 94
            name.setMinimumWidth(name_width)
            val = QLabel(value)
            val.setMinimumWidth(54 if title in {"Wafer Properties", "Die Layout", "Design Files"} else 70)
            val.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            val.setWordWrap(True)
            val.setTextInteractionFlags(Qt.TextSelectableByMouse)
            if label == "History Log":
                name.setText("")
                name.setMinimumWidth(14)
                val.setText("History Log")
                val.setStyleSheet("text-decoration: underline;")
            if label == "Validation Status":
                name.setText("")
                name.setMinimumWidth(0)
                val.setMinimumWidth(320)
                val.setMaximumWidth(360)
                val.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            self._remember_recipe_overview_label(title, label, val)
            if label:
                self.recipe_overview_rows[label] = row_holder
            row.addWidget(name)
            row.addWidget(val)
            layout.addWidget(row_holder)

        layout.addStretch(1)
        grid.addWidget(group, 0, column)

    def _add_alignment_group(self, grid: QGridLayout, column: int):
        group = QFrame()
        self.recipe_overview_groups["Alignment"] = group
        group.setStyleSheet("border-right: 1px solid #d1cec5;")
        group.setMinimumWidth(190)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(6, 0, 12, 0)
        layout.setSpacing(3)

        header = QHBoxLayout()
        title = QLabel("Alignment")
        title.setProperty("heading", True)
        header.addWidget(title)
        header.addWidget(StatusDot("#00a040"))
        header.addStretch(1)
        layout.addLayout(header)

        layout.addWidget(self._mini_table(
            "",
            ["Type", "DF at 180"],
            [
                ("DF Scores", "Align    X Reg   Y Reg"),
                ("Uniqueness", "83.3     55.0    100.0"),
                ("Sharpness", "10.1      5.9     10.1"),
                ("Features", "98.8     98.8     98.8"),
            ],
        ))
        layout.addWidget(self._mini_table(
            "",
            ["Type", "DF at 90"],
            [
                ("DF Scores", "Align    X Reg   Y Reg"),
                ("Uniqueness", "90.8     99.9     99.9"),
                ("Sharpness", "37.8      8.9     37.8"),
                ("Features", "69.4     10.1     69.4"),
            ],
        ))
        layout.addStretch(1)
        grid.addWidget(group, 0, column)

    def _mini_table(self, title: str, header_row: List[str], rows: List[Tuple[str, str]]) -> QWidget:
        table = QWidget()
        layout = QVBoxLayout(table)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        if title:
            label = QLabel(title)
            label.setStyleSheet("font-weight: 600;")
            layout.addWidget(label)
        header = QLabel("    ".join(header_row))
        header.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(header)
        for name, value in rows:
            row = QHBoxLayout()
            row.setSpacing(5)
            name_label = QLabel(name)
            name_label.setMinimumWidth(70)
            name_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            value_label = QLabel(value)
            value_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            row.addWidget(name_label)
            row.addWidget(value_label)
            layout.addLayout(row)
        return table

    def _add_registration_sites_group(self, grid: QGridLayout, column: int):
        group = QFrame()
        self.recipe_overview_groups["Registration Sites"] = group
        group.setStyleSheet("border-right: 1px solid #d1cec5;")
        group.setMinimumWidth(160)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(6, 0, 12, 0)
        layout.setSpacing(5)
        title = QLabel("Registration Sites")
        title.setProperty("heading", True)
        layout.addWidget(title)
        layout.addStretch(1)
        for label, value in [
            ("Defined Sites", "None at 180"),
            ("Defined Sites", "None at 90"),
        ]:
            row = QHBoxLayout()
            row.setSpacing(5)
            name = QLabel(label)
            name.setMinimumWidth(76)
            name.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            value_label = QLabel(value)
            value_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            row.addWidget(name)
            row.addWidget(value_label)
            layout.addLayout(row)
        grid.addWidget(group, 0, column)

    def _add_die_corner_group(self, grid: QGridLayout, column: int):
        group = QFrame()
        self.recipe_overview_groups["Die Corner"] = group
        group.setStyleSheet("border-right: 1px solid #d1cec5;")
        group.setMinimumWidth(150)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(6, 0, 12, 0)
        title = QLabel("Die Corner")
        title.setProperty("heading", True)
        layout.addWidget(title)
        self.die_corner_map = DieCornerMap()
        self.die_corner_map.zoom_callback = self.open_die_corner_zoom
        self.die_corner_map.setToolTip("Click to view enlarged die corner image")
        layout.addWidget(self.die_corner_map, alignment=Qt.AlignLeft)
        layout.addStretch(1)
        grid.addWidget(group, 0, column)

    def _remember_recipe_overview_label(self, title: str, label: str, value_label: QLabel):
        if not label:
            return
        if title == "Inspection Properties":
            self.recipe_property_labels[label] = value_label
        elif title == "Creation Properties":
            self.creation_property_labels[label] = value_label
        elif title == "Load/Save Status":
            self.load_save_status_labels[label] = value_label
        elif title == "Wafer Properties":
            self.wafer_property_labels[label] = value_label

    def _add_empty_status_group(self, grid: QGridLayout, column: int, title: str):
        group = QFrame()
        self.recipe_overview_groups[title] = group
        group.setStyleSheet("border-right: 1px solid #d1cec5;")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(6, 0, 12, 0)
        header = QHBoxLayout()
        label = QLabel(title)
        label.setProperty("heading", True)
        header.addWidget(label)
        header.addWidget(StatusDot())
        header.addStretch(1)
        layout.addLayout(header)
        layout.addStretch(1)
        grid.addWidget(group, 0, column)

    def _add_wafer_map_group(self, grid: QGridLayout, column: int):
        group = QFrame()
        self.recipe_overview_groups["Wafer Map"] = group
        group.setStyleSheet("border-right: 1px solid #d1cec5;")
        group.setMinimumWidth(160)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(6, 0, 12, 0)
        header = QHBoxLayout()
        title = QLabel("Wafer Map")
        title.setProperty("heading", True)
        header.addWidget(title)
        header.addWidget(StatusDot())
        header.addStretch(1)
        layout.addLayout(header)
        self.overview_wafer_map = OverviewWaferMap()
        self.overview_wafer_map.zoom_callback = self.open_wafer_map_zoom
        self.overview_wafer_map.setToolTip("Click to view enlarged wafer map image")
        layout.addWidget(self.overview_wafer_map, alignment=Qt.AlignLeft)
        layout.addStretch(1)
        grid.addWidget(group, 0, column)

    def _build_statusbar(self):
        status = QStatusBar()
        self.setStatusBar(status)
        status.showMessage("For Help, press F1")

        self.inspection_status_label = QLabel("Inspection: New")
        self.inspection_status_label.setMinimumWidth(180)
        self.inspection_status_label.setStyleSheet("border-left: 1px solid #9c998f; padding-left: 6px;")
        status.addPermanentWidget(self.inspection_status_label, 1)

        for color, text in [("#00b050", ""), ("#ff7f00", ""), ("#ed1c24", ""), ("#d7d4cc", "NUM")]:
            label = QLabel(text)
            label.setFixedWidth(42 if text else 24)
            label.setAlignment(Qt.AlignCenter)
            if text:
                label.setStyleSheet("border-left: 1px solid #9c998f;")
            else:
                label.setStyleSheet(
                    f"background: {color}; border: 1px solid #7c786f; border-radius: 5px;"
                )
            status.addPermanentWidget(label)

    def open_inspection_recipe(self):
        dialog = OpenInspectionRecipeDialog(self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted and dialog.selected_recipe:
            recipe = dialog.selected_recipe
            self._apply_recipe_to_overview(recipe)
            self.inspection_status_label.setText(
                f"Inspection: {recipe['inspection']}    Device: {recipe['device']}    Step: {recipe['step']}"
            )
            self.statusBar().showMessage(f"Loaded recipe {recipe['inspection']}")

    def open_wafer_menu(self):
        menu = WaferMenuDialog(self)
        result = menu.exec() if hasattr(menu, "exec") else menu.exec_()
        if result == QDialog.Accepted and menu.open_wafer_properties:
            self.open_wafer_properties()
        elif result == QDialog.Accepted and menu.open_alignment:
            self.open_alignment_menu()
        elif result == QDialog.Accepted and menu.open_wafer_map:
            self.open_wafer_map()

    def open_alignment_menu(self):
        self.alignment_context_active = True
        self.image_display_action.setEnabled(True)
        alignment = AlignmentMenuDialog(self)
        alignment.exec() if hasattr(alignment, "exec") else alignment.exec_()
        self.statusBar().showMessage("Wafer Alignment selected. Use View > Image Display or Auto Site Selection.")

    def open_wafer_properties(self):
        dialog = WaferPropertiesDialog(self._current_wafer_properties(), self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted and dialog.result_properties:
            self._apply_wafer_properties(dialog.result_properties)
            self.statusBar().showMessage("Updated wafer properties")

    def open_wafer_map(self):
        dialog = WaferMapSetupDialog(self)
        self.statusBar().showMessage("Wafermap View displayed")
        dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        self.statusBar().showMessage("Wafermap View closed")

    def open_die_corner_zoom(self):
        dialog = DieCornerZoomDialog(self)
        dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        self.statusBar().showMessage("Die Corner high mag image closed")

    def open_wafer_map_zoom(self):
        dialog = WaferMapZoomDialog(self)
        dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        self.statusBar().showMessage("Wafer Map image closed")

    def open_wafer_handling(self):
        dialog = WaferHandlingDialog(self)
        dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        self.statusBar().showMessage("Wafer Handling closed")

    def open_image_display(self):
        if not self.alignment_context_active:
            self.statusBar().showMessage("Select Set Up > Wafer > Alignment before opening Image Display.")
            return

        if self.image_display_window and self.image_display_window.isVisible():
            self.image_display_window.raise_()
            self.image_display_window.activateWindow()
            return

        self.image_display_window = ImageDisplayWindow(self)
        self.image_display_window.show()
        self.statusBar().showMessage("Image Display Window opened")

    def configure_recipe_overview(self):
        dialog = SelectVisibleRecipeParametersDialog(self.visible_recipe_parameters, self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted and dialog.result_parameters:
            self.visible_recipe_parameters = dialog.result_parameters
            self._apply_recipe_overview_visibility()
            self.statusBar().showMessage("Updated visible recipe parameters")

    def _apply_recipe_overview_visibility(self):
        for name, widget in self.recipe_overview_sections.items():
            widget.setVisible(self.visible_recipe_parameters.get(name, True))
        for name, widget in self.recipe_overview_groups.items():
            widget.setVisible(self.visible_recipe_parameters.get(name, True))
        for name, widget in self.recipe_overview_rows.items():
            widget.setVisible(self.visible_recipe_parameters.get(name, True))

    def _apply_recipe_to_overview(self, recipe):
        recipe_updates = {
            "Recipe Name": recipe.get("inspection", ""),
            "Device Name": recipe.get("device", ""),
            "Layer Name": recipe.get("step", ""),
            "Recipe Type": recipe.get("recipe_type", ""),
            "Approval": recipe.get("approval", ""),
        }
        creation_updates = {
            "Last Modification": recipe.get("last_modified", ""),
        }
        status_updates = {
            "Validation Status": (
                "<b>Valid recipe:</b> The recipe successfully passed validation on<br>"
                f"{recipe.get('validation_date', '9/1/2011')}"
                if recipe.get("status", "") == "Valid"
                else f"<b>{recipe.get('status', 'Recipe status')}:</b> {recipe.get('state', '')}"
            ),
        }

        self._set_label_group_values(self.recipe_property_labels, recipe_updates)
        self._set_label_group_values(self.creation_property_labels, creation_updates)
        self._set_label_group_values(self.load_save_status_labels, status_updates)

    def _set_label_group_values(self, label_map, values):
        for key, value in values.items():
            label = label_map.get(key)
            if label:
                label.setText(value)
                label.setToolTip(value)

    def _current_wafer_properties(self):
        return {
            "orientation": self.wafer_property_labels["Orientation"].text(),
            "type": self.wafer_property_labels["Wafer Type"].text(),
            "laser_power_sensitive": self.wafer_property_labels["Laser Power Sensitive"].text() == "Yes",
            "laser_power_factor": self.wafer_property_labels["Laser Power Factor"].text(),
            "layer": self.wafer_property_labels["Layer"].text(),
            "dark_wafer_auto_focus": self.wafer_property_labels["Dark Wafer"].text() == "Yes",
            "wafer_darkness_level": self.wafer_property_labels["Wafer Darkness Level"].text(),
        }

    def _apply_wafer_properties(self, properties):
        updates = {
            "Wafer Type": properties["type"],
            "Orientation": properties["orientation"],
            "Laser Power Sensitive": "Yes" if properties["laser_power_sensitive"] else "No",
            "Laser Power Factor": properties["laser_power_factor"],
            "Layer": properties["layer"],
            "Dark Wafer": "Yes" if properties["dark_wafer_auto_focus"] else "No",
            "Wafer Darkness Level": properties["wafer_darkness_level"],
        }
        self._set_label_group_values(self.wafer_property_labels, updates)

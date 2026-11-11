from __future__ import annotations

import re
from typing import Callable, Optional

from ...qt_compat import (
    QBoxLayout,
    QColor,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QSizePolicy,
    QIcon,
    QLabel,
    QPainter,
    QPen,
    QPixmap,
    QPushButton,
    QRadioButton,
    QSize,
    QStackedWidget,
    Qt,
    QTimer,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from ...widgets import (
    paint_slot_wafer_symbol,
    paint_wafer_thumbnail,
    thumbnail_surface_color,
    wafer_disk_with_notch,
    wafer_thumbnail_kind,
)
from ..wafer_handling.operation import TimedWaferOperation

LOAD_PORTS = (1, 2)
_LAMP_ON = "#3cbf4a"
_LAMP_OFF = "#6a6a6a"


def _lamp_style(lit: bool) -> str:
    color = _LAMP_ON if lit else _LAMP_OFF
    return f"background: {color}; border-radius: 5px; border: 1px solid #3a3a3a;"


class MatchingStack(QStackedWidget):
    """Keep every page the size of the largest page so empty and mapped ports match."""

    def sizeHint(self):  # noqa: N802 - Qt override
        return self._largest("sizeHint")

    def minimumSizeHint(self):  # noqa: N802 - Qt override
        return self._largest("minimumSizeHint")

    def _largest(self, method: str) -> QSize:
        result = QSize(0, 0)
        for index in range(self.count()):
            result = result.expandedTo(getattr(self.widget(index), method)())
        return result


def _pixmap_icon(kind: str, size: int = 28) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    if kind in {"cassette", "cassette-disabled"}:
        active = kind == "cassette"
        body = QColor("#ff6f21" if active else "#9b9b9b")
        painter.setPen(QPen(QColor("#333333"), 1))
        painter.setBrush(body)
        painter.drawRoundedRect(4, 4, 18, 18, 2, 2)
        painter.setBrush(QColor("#222222" if active else "#777777"))
        painter.drawEllipse(8, 8, 10, 10)
    elif kind == "load":
        painter.setBrush(QColor("#6d6d6d"))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(3, 3, size - 6, size - 6)
    elif kind == "wafer":
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor("#6d6d6d"), 2))
        painter.drawEllipse(4, 4, size - 8, size - 8)
    elif kind == "load-align":
        painter.setBrush(QColor("#6d6d6d"))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(3, 3, size - 6, size - 6)
        painter.setPen(QPen(QColor("#3f63d8"), 3))
        painter.drawLine(7, size // 2 - 3, size - 7, size // 2 - 3)
        painter.drawLine(7, size // 2 + 3, size - 7, size // 2 + 3)
    elif kind == "align":
        painter.setPen(QPen(QColor("#8d8d8d"), 3))
        painter.drawLine(6, size // 2 - 4, size - 6, size // 2 - 4)
        painter.drawLine(6, size // 2 + 4, size - 6, size // 2 + 4)
    elif kind == "recovery":
        painter.setBrush(QColor("#ed1c24"))
        painter.setPen(QPen(QColor("#ffffff"), 1))
        painter.drawEllipse(3, 3, 22, 22)
        painter.setPen(QPen(QColor("#ffffff"), 3))
        painter.drawLine(14, 8, 14, 20)
        painter.drawLine(8, 14, 20, 14)
    elif kind == "arrow":
        painter.setPen(QPen(QColor("#18a124"), 2))
        painter.setBrush(QColor("#18a124"))
        painter.drawLine(size // 2, 3, 4, size - 3)
        painter.drawLine(size // 2, 3, size - 4, size - 3)
        painter.drawLine(4, size - 3, size - 4, size - 3)
        painter.drawLine(size // 2, 3, size // 2, size - 3)

    painter.end()
    return QIcon(pixmap)


def _orientation_degrees(text, default: int = 180) -> int:
    match = None
    for angle in (270, 180, 90, 0):
        found = re.search(rf"(?<!\d){angle}(?!\d)", str(text))
        if found:
            match = angle
            break
    return default if match is None else match


class EmptyWaferDisk(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.kind = "empty"
        self.orientation = 180
        self.setFixedSize(76, 76)
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


class OrientationDisk(QWidget):
    def __init__(self, notch: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.notch = notch
        self.setFixedSize(34, 30)

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        angle = {"up": 0, "right": 90, "down": 180, "left": 270}.get(self.notch, 180)
        painter.setBrush(QColor("#242424"))
        painter.setPen(QPen(QColor("#111111"), 1))
        painter.drawPath(wafer_disk_with_notch(6, 4, 22, angle))


class ShowSlotRow(QWidget):
    """Cassette slot whose caption animates through Loading, Aligning, and Unloading."""

    def __init__(self, slot: int, on_select, parent=None):
        super().__init__(parent)
        self.slot = slot
        self.on_select = on_select
        self.wafer_state = "Absent"
        self.selected = False
        self.orientation = 180
        self.pulse = 1.0
        self.setFixedHeight(18)
        self.setCursor(Qt.PointingHandCursor)

    def set_state(self, state: str, selected: bool, orientation: int = 180):
        if state != self.wafer_state:
            self.pulse = 0.0 if state in {"Loading", "Aligning", "Unloading"} else 1.0
        self.wafer_state = state
        self.selected = selected
        self.orientation = int(orientation)
        self.setToolTip(f"Slot {self.slot}: {state}")
        self.update()

    def mousePressEvent(self, event):  # noqa: N802 - Qt override
        if event.button() == Qt.LeftButton and self.isEnabled():
            self.on_select(self.slot)
        super().mousePressEvent(event)

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QColor("#222222"))
        painter.drawText(0, 0, 18, self.height(), int(Qt.AlignRight | Qt.AlignVCenter), str(self.slot))

        circle_size = 12
        circle_x = 22
        circle_y = (self.height() - circle_size) // 2
        paint_slot_wafer_symbol(
            painter, circle_x, circle_y, circle_size, self.wafer_state, self.orientation
        )

        bar = self.rect().adjusted(38, 2, -4, -2)
        painter.setPen(QPen(QColor("#1d4f9c") if self.selected else QColor("#8a8a8a"), 1))
        painter.setBrush(QColor("#d7e4f8") if self.selected else QColor("#f4f4f4"))
        painter.drawRoundedRect(bar, 3, 3)
        captions = {
            "Loading": "Loading",
            "Aligning": "Aligning",
            "Unloading": "Unloading",
            "Loaded": "Loaded",
            "Aligned": "Aligned",
        }
        if self.wafer_state in captions:
            painter.setPen(QColor("#111111"))
            font = painter.font()
            font.setPixelSize(9)
            painter.setFont(font)
            if self.wafer_state in {"Loading", "Aligning", "Unloading"}:
                painter.setOpacity(0.25 + 0.75 * self.pulse)
                shift = int((1.0 - self.pulse) * 16)
                painter.drawText(bar.adjusted(shift, 0, 0, 0), int(Qt.AlignCenter), captions[self.wafer_state])
            else:
                painter.drawText(bar, int(Qt.AlignCenter), captions[self.wafer_state])


class ShowWaferPanel(QFrame):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        operation_duration_ms: int = 10000,
        operation_timeout_ms: int = 12000,
        state: Optional[dict] = None,
        recipe: Optional[dict] = None,
    ):
        super().__init__(parent)
        self.setObjectName("showWaferPanel")
        self._expanded = True
        self._port_choice = "All"
        self.runtime_state = state if isinstance(state, dict) else None
        self.port_widgets = {}
        self.port_controls = {}
        self.selected_port = 1
        self.selected_slots = {1: 25, 2: None}
        self.carrier_loaded = {1: True, 2: False}
        self.carrier_mapped = {1: True, 2: False}
        self.slot_states = {
            1: {slot: "Present" for slot in range(1, 26)},
            2: {slot: "Absent" for slot in range(1, 26)},
        }
        self.wafer_ids = {1: {}, 2: {}}
        self.wafer_loaded = False
        self.wafer_aligned = False
        self.wafer_source_port = None
        self.wafer_source_slot = None
        self.orientation = 180
        self.wafer_type = "Patterned"
        self.alignment_sites_defined = True
        self.read_wafer_id = False
        self.last_transfer_outcome = "Idle"
        self.last_transfer_error = ""
        self._sequence = None
        if isinstance(state, dict):
            self._read_state(state)
        self.setStyleSheet(
            """
            QFrame#showWaferPanel {
                background: #c4c0b0;
                border-left: 1px solid #807c73;
            }
            QLabel {
                font-size: 10px;
                color: #111111;
            }
            QGroupBox {
                background: #d0ccbc;
                border: 1px solid #8d897d;
                margin-top: 8px;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 3px;
            }
            QPushButton {
                background: #eceae0;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-height: 24px;
                padding: 2px 5px;
            }
            QPushButton:disabled {
                color: #888888;
                background: #d8d5cc;
            }
            """
        )
        self._build_ui()
        self.operation = TimedWaferOperation(
            self,
            duration_ms=operation_duration_ms,
            timeout_ms=operation_timeout_ms,
            on_progress=self._operation_progress,
            on_active_changed=self._operation_active_changed,
        )
        self._sequence_timer = QTimer(self)
        self._sequence_timer.setInterval(40)
        self._sequence_timer.timeout.connect(self._tick_slot_animation)
        if recipe:
            self.update_recipe(recipe)
        else:
            self._refresh()

    def _read_state(self, state: dict):
        self.selected_port = int(state.get("selected_port", self.selected_port) or 1)
        if self.selected_port not in LOAD_PORTS:
            self.selected_port = 1
        for key, value in (state.get("carrier_loaded") or {}).items():
            port_number = int(key)
            if port_number in self.carrier_loaded:
                self.carrier_loaded[port_number] = bool(value)
        mapped = state.get("carrier_mapped") or {}
        for port in LOAD_PORTS:
            if port in mapped or str(port) in mapped:
                self.carrier_mapped[port] = bool(mapped.get(port, mapped.get(str(port))))
            else:
                self.carrier_mapped[port] = bool(self.carrier_loaded[port])
            if not self.carrier_loaded[port]:
                self.carrier_mapped[port] = False
        for key, value in (state.get("selected_slots") or {}).items():
            port_number = int(key)
            if port_number in self.selected_slots:
                self.selected_slots[port_number] = None if value is None else int(value)
        self.wafer_loaded = bool(state.get("wafer_loaded", False))
        self.wafer_aligned = bool(state.get("wafer_aligned", False)) and self.wafer_loaded
        provided = state.get("slot_states") or {}
        for port in LOAD_PORTS:
            slots = provided.get(port)
            if slots is None:
                slots = provided.get(str(port))
            base = "Present" if self.carrier_loaded[port] else "Absent"
            merged = {slot: base for slot in range(1, 26)}
            if isinstance(slots, dict):
                merged.update({int(slot): value for slot, value in slots.items()})
            self.slot_states[port] = merged
        for port, identifiers in (state.get("wafer_ids") or {}).items():
            port_number = int(port)
            if port_number in self.wafer_ids and isinstance(identifiers, dict):
                self.wafer_ids[port_number] = {int(slot): value for slot, value in identifiers.items()}
        source_port = state.get("wafer_source_port")
        source_slot = state.get("wafer_source_slot")
        if self.wafer_loaded and source_port in LOAD_PORTS and source_slot is not None:
            self.wafer_source_port = int(source_port)
            self.wafer_source_slot = int(source_slot)
            current = self.slot_states[self.wafer_source_port].get(self.wafer_source_slot, "Present")
            if current not in {"Loaded", "Aligned", "Loading", "Aligning", "Unloading"}:
                self.slot_states[self.wafer_source_port][self.wafer_source_slot] = (
                    "Aligned" if self.wafer_aligned else "Loaded"
                )
        else:
            self.wafer_source_port = None
            self.wafer_source_slot = None
            if not self.wafer_loaded:
                self.wafer_aligned = False
        self.orientation = _orientation_degrees(state.get("required_orientation", self.orientation), self.orientation)
        self.read_wafer_id = bool(state.get("read_wafer_id", self.read_wafer_id))
        self.last_transfer_outcome = str(state.get("last_transfer_outcome", self.last_transfer_outcome))
        self.last_transfer_error = str(state.get("last_transfer_error", self.last_transfer_error))

    def export_state(self) -> dict:
        return {
            "selected_port": self.selected_port,
            "carrier_loaded": dict(self.carrier_loaded),
            "carrier_mapped": dict(self.carrier_mapped),
            "selected_slots": dict(self.selected_slots),
            "slot_states": {port: dict(slots) for port, slots in self.slot_states.items()},
            "wafer_ids": {port: dict(values) for port, values in self.wafer_ids.items()},
            "wafer_loaded": self.wafer_loaded,
            "wafer_aligned": self.wafer_aligned,
            "wafer_source_port": self.wafer_source_port,
            "wafer_source_slot": self.wafer_source_slot,
            "read_wafer_id": self.read_wafer_id,
            "required_orientation": str(self.orientation),
            "last_transfer_outcome": self.last_transfer_outcome,
            "last_transfer_error": self.last_transfer_error,
        }

    def apply_state(self, state: Optional[dict]):
        if isinstance(state, dict):
            self.runtime_state = state
            self._read_state(state)
            self._refresh()

    def _publish(self):
        if isinstance(self.runtime_state, dict):
            self.runtime_state.update(self.export_state())

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 6)
        layout.setSpacing(6)
        body = QHBoxLayout()
        body.setSpacing(8)
        self.body_layout = body
        body.addWidget(self._wafer_operations(), 1)
        for port_number in LOAD_PORTS:
            port = self._load_port(port_number)
            self.port_widgets[port_number] = port
            body.addWidget(port, 1)
        layout.addLayout(body, 1)
        layout.addWidget(self._wafer_footer())
        self.set_expanded(self._expanded)

    def _wafer_footer(self) -> QWidget:
        footer = QWidget()
        row = QHBoxLayout(footer)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        self.hide_wafer_button = QPushButton("Show Wafer  >>")
        self.hide_wafer_button.setMinimumWidth(112)
        row.addWidget(self.hide_wafer_button)
        self.load_port_label = QLabel("Show Load Port:")
        row.addWidget(self.load_port_label)
        self.load_port_buttons = []
        for text, checked in [("1", False), ("2", False), ("All", True)]:
            button = QPushButton(text)
            button.setCheckable(True)
            button.setChecked(checked)
            button.setFixedSize(36 if text == "All" else 28, 28)
            button.setStyleSheet("QPushButton:checked { background: #b7b7b7; }")
            self.load_port_buttons.append(button)
            row.addWidget(button)
        row.addStretch(1)
        self.wafer_footer = footer
        return footer

    def set_expanded(self, expanded: bool):
        self._expanded = expanded
        self.operations_box.setVisible(expanded)
        self.orientation_label.setVisible(expanded)
        self.orientation_host.setVisible(expanded)
        self.status_label.setVisible(expanded)
        self.wafer_footer.setVisible(True)
        self.load_port_label.setVisible(expanded)
        for button in self.load_port_buttons:
            button.setVisible(expanded)
        self.summary_layout.setDirection(QBoxLayout.LeftToRight if expanded else QBoxLayout.TopToBottom)
        self.summary_layout.setAlignment(
            self.wafer_disk,
            Qt.AlignLeft | Qt.AlignTop if expanded else Qt.AlignHCenter | Qt.AlignTop,
        )
        if expanded:
            self.operations_column.setMinimumWidth(0)
            self.operations_column.setMaximumWidth(16777215)
            self.operations_column.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
            self.set_visible_ports(self._port_choice)
            self.body_layout.setStretch(0, 1)
            for index in range(1, self.body_layout.count()):
                self.body_layout.setStretch(index, 1)
        else:
            self.operations_column.setMinimumWidth(0)
            self.operations_column.setMaximumWidth(16777215)
            self.operations_column.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            for widget in self.port_widgets.values():
                widget.setVisible(False)

    def _wafer_operations(self) -> QWidget:
        panel = QFrame()
        self.operations_column = panel
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.summary_layout = QBoxLayout(QBoxLayout.TopToBottom)
        self.summary_layout.setSpacing(4)
        self.wafer_disk = EmptyWaferDisk()
        self.wafer_details = QLabel()
        self.wafer_details.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.wafer_details.setWordWrap(True)
        self.wafer_details.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.wafer_details.setStyleSheet("font-size: 10px;")
        self.summary_layout.addWidget(self.wafer_disk, 0, Qt.AlignHCenter | Qt.AlignTop)
        self.summary_layout.addWidget(self.wafer_details, 1)
        layout.addLayout(self.summary_layout)

        operations_box = QGroupBox("Wafer Operations")
        self.operations_box = operations_box
        operations = QVBoxLayout(operations_box)
        operations.setContentsMargins(8, 12, 8, 8)
        operations.setSpacing(6)

        button_row = QHBoxLayout()
        button_row.setSpacing(4)
        self.load_wafer_button = self._operation_button("Load", "load")
        self.load_align_button = self._operation_button("Load &\nAlign", "load-align")
        self.align_button = self._operation_button("Align", "align")
        self.load_wafer_button.clicked.connect(self._load_wafer)
        self.load_align_button.clicked.connect(self._load_and_align)
        self.align_button.clicked.connect(self._align_wafer)
        button_row.addWidget(self.load_wafer_button)
        button_row.addWidget(self.load_align_button)
        button_row.addWidget(self.align_button)
        operations.addLayout(button_row)

        self.unload_wafer_button = QPushButton("Unload Wafer")
        self.unload_wafer_button.setIcon(_pixmap_icon("wafer", 22))
        self.unload_wafer_button.setIconSize(QSize(18, 18))
        self.unload_wafer_button.setFixedHeight(32)
        self.unload_wafer_button.clicked.connect(self._unload_wafer)
        operations.addWidget(self.unload_wafer_button)

        self.recovery_button = QPushButton("Automatic Recovery")
        self.recovery_button.setIcon(_pixmap_icon("recovery", 24))
        self.recovery_button.setIconSize(QSize(20, 20))
        self.recovery_button.setFixedHeight(34)
        self.recovery_button.clicked.connect(self._automatic_recovery)
        operations.addWidget(self.recovery_button)
        layout.addWidget(operations_box)

        orient = QLabel("Change Orientation:")
        orient.setStyleSheet("font-weight: 600;")
        self.orientation_label = orient
        layout.addWidget(orient)
        self.orientation_host = QWidget()
        orientation_layout = QVBoxLayout(self.orientation_host)
        orientation_layout.setContentsMargins(0, 0, 0, 0)
        orientation_layout.addLayout(self._orientation_row())
        layout.addWidget(self.orientation_host)
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #333333; font-size: 9px;")
        layout.addWidget(self.status_label)
        layout.addStretch(1)
        return panel

    def _operation_button(self, label: str, icon_name: str) -> QToolButton:
        button = QToolButton()
        button.setText(label)
        button.setIcon(_pixmap_icon(icon_name, 32))
        button.setIconSize(QSize(28, 28))
        button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        button.setMinimumHeight(74)
        button.setAutoRaise(False)
        button.setStyleSheet(
            """
            QToolButton {
                background: #eceae0;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                padding: 4px 2px;
                color: #111111;
            }
            QToolButton:disabled {
                color: #888888;
                background: #d8d5cc;
            }
            """
        )
        return button

    def _orientation_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(4)
        self.orientation_controls = {}
        for text, notch, angle in [
            ("Up\n0°", "up", 0),
            ("Right\n90°", "right", 90),
            ("Down\n180°", "down", 180),
            ("Left\n270°", "left", 270),
        ]:
            item = QVBoxLayout()
            item.setSpacing(1)
            disk = OrientationDisk(notch)
            item.addWidget(disk, alignment=Qt.AlignHCenter)
            label = QLabel(text)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("font-size: 9px;")
            item.addWidget(label)
            arrow = QLabel()
            arrow.setPixmap(_pixmap_icon("arrow", 16).pixmap(16, 16))
            arrow.setAlignment(Qt.AlignCenter)
            item.addWidget(arrow, alignment=Qt.AlignHCenter)
            selector = QRadioButton()
            selector.setFixedSize(16, 16)
            selector.setToolTip(f"Change orientation to {angle} degrees")
            selector.clicked.connect(lambda checked=False, value=angle: self._set_orientation(value))
            item.addWidget(selector, alignment=Qt.AlignHCenter)
            self.orientation_controls[angle] = selector
            row.addLayout(item)
        return row

    def _load_port(self, port_number: int) -> QWidget:
        panel = QFrame()
        panel.setObjectName("loadPort")
        panel.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        commands = QHBoxLayout()
        commands.setSpacing(4)
        load = QPushButton("Load")
        load.setIcon(_pixmap_icon("cassette", 28))
        load.setIconSize(QSize(22, 22))
        load.setFixedHeight(36)
        load.clicked.connect(lambda checked=False, value=port_number: self.load_selected_wafer(value))
        unload = QPushButton("Unload")
        unload.setIcon(_pixmap_icon("cassette", 28))
        unload.setIconSize(QSize(22, 22))
        unload.setFixedHeight(36)
        unload.clicked.connect(lambda checked=False, value=port_number: self.unload_selected_wafer(value))
        commands.addWidget(load)
        commands.addWidget(unload)
        layout.addLayout(commands)

        tab = QPushButton(f"Port {port_number}")
        tab.setCheckable(True)
        tab.setFixedHeight(22)
        tab.clicked.connect(lambda checked=False, value=port_number: self.select_port(value))
        layout.addWidget(tab, alignment=Qt.AlignHCenter)

        cassette = QFrame()
        cassette.setObjectName("showCassette")
        cassette.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        cassette.setStyleSheet(
            "QFrame#showCassette { background: #d4d4d4; border-left: 5px solid #6e6e6e; "
            "border-right: 5px solid #6e6e6e; border-bottom: 8px solid #6e6e6e; }"
        )
        cassette_layout = QVBoxLayout(cassette)
        cassette_layout.setContentsMargins(6, 4, 6, 4)
        cassette_layout.setSpacing(2)
        stack = MatchingStack()
        stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        slots_page = QWidget()
        slots_page.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        slots_layout = QVBoxLayout(slots_page)
        slots_layout.setContentsMargins(0, 0, 0, 0)
        slots_layout.setSpacing(0)
        slots = {}
        for slot in range(25, 0, -1):
            row = ShowSlotRow(slot, lambda value, port=port_number: self._select_slot(port, value))
            slots_layout.addWidget(row)
            slots[slot] = row
        empty = QFrame()
        empty.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        empty.setStyleSheet("background: #b9b9b9; border: none;")
        stack.addWidget(slots_page)
        stack.addWidget(empty)
        cassette_layout.addWidget(stack, 1)
        lamps = QHBoxLayout()
        lamps.setSpacing(6)
        lamps.addStretch(1)
        lamp_widgets = []
        for _ in range(2):
            lamp = QLabel()
            lamp.setFixedSize(10, 10)
            lamps.addWidget(lamp)
            lamp_widgets.append(lamp)
        lamps.addStretch(1)
        cassette_layout.addLayout(lamps)
        layout.addWidget(cassette, 1)

        state = QLabel()
        state.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        state.setWordWrap(True)
        state.setFixedHeight(64)
        state.setStyleSheet("font-size: 9px;")
        layout.addWidget(state)
        self.port_controls[port_number] = {
            "load": load,
            "unload": unload,
            "tab": tab,
            "stack": stack,
            "slots": slots,
            "lamps": lamp_widgets,
            "state": state,
        }
        return panel

    def set_visible_ports(self, choice: str):
        choice = str(choice)
        self._port_choice = choice
        if not self._expanded:
            for widget in self.port_widgets.values():
                widget.setVisible(False)
            return
        if choice == "1":
            visible = {1}
        elif choice == "2":
            visible = {2}
        else:
            visible = {1, 2}
        for port_number, widget in self.port_widgets.items():
            widget.setVisible(port_number in visible)

    def update_recipe(self, recipe: dict):
        wafer_properties = recipe.get("wafer_properties") or {}
        if wafer_properties.get("type"):
            self.wafer_type = wafer_properties.get("type")
        alignment = recipe.get("alignment")
        if isinstance(alignment, dict):
            self.alignment_sites_defined = bool(alignment.get("sites_defined")) and (
                not alignment.get("derivative_origin_reselection_required")
                or alignment.get("derivative_origin_reselected")
            )
        elif self.wafer_type == "Blank":
            self.alignment_sites_defined = False
        linked_orientation = isinstance(self.runtime_state, dict) and self.runtime_state.get("required_orientation") not in (None, "")
        if not linked_orientation and ("wafer_orientation" in recipe or "orientation" in wafer_properties):
            self.orientation = _orientation_degrees(
                wafer_properties.get("orientation", recipe.get("wafer_orientation", self.orientation)),
                self.orientation,
            )
        self.setToolTip(
            "Inspection: {inspection}\nDevice: {device}\nStep: {step}".format(
                inspection=recipe.get("inspection", ""),
                device=recipe.get("device", ""),
                step=recipe.get("step", ""),
            )
        )
        self._refresh()

    def _set_status(self, message: str):
        self.status_label.setText(message)

    def select_port(self, port_number: int):
        if port_number not in LOAD_PORTS:
            return
        self.selected_port = port_number
        self._refresh()

    def _select_slot(self, port_number: int, slot: int):
        if not self.carrier_loaded[port_number]:
            self._set_status(f"Load a carrier on Port {port_number} first.")
            return
        if self.slot_states[port_number].get(slot) == "Absent":
            self._set_status(f"Port {port_number}, Slot {slot} is empty.")
            return
        self.selected_port = port_number
        self.selected_slots[port_number] = slot
        self._refresh()
        self._set_status(f"Port {port_number}, Slot {slot} selected.")

    def _load_carrier(self, port_number: int):
        if port_number not in LOAD_PORTS:
            self._set_status("Only Port 1 and Port 2 are available.")
            return False
        self.carrier_loaded[port_number] = True
        self.carrier_mapped[port_number] = True
        self.slot_states[port_number] = {slot: "Present" for slot in range(1, 26)}
        self.selected_slots[port_number] = 25
        self.selected_port = port_number
        self._refresh()
        self._set_status(f"Carrier loaded and mapped on Port {port_number}.")
        return True

    def _unload_carrier(self, port_number: int):
        if port_number not in LOAD_PORTS:
            return False
        if self.wafer_loaded and self.wafer_source_port == port_number:
            self._set_status("Unload the wafer before removing its source carrier.")
            return False
        self.carrier_loaded[port_number] = False
        self.carrier_mapped[port_number] = False
        self.slot_states[port_number] = {slot: "Absent" for slot in range(1, 26)}
        self.selected_slots[port_number] = None
        if self.selected_port == port_number:
            self.selected_port = next((port for port, loaded in self.carrier_loaded.items() if loaded), 1)
        self._refresh()
        self._set_status(f"Carrier unloaded from Port {port_number}.")
        return True

    def load_selected_wafer(self, port_number: int):
        self.select_port(port_number)
        return self._load_wafer()

    def unload_selected_wafer(self, port_number: int):
        self.select_port(port_number)
        slot = self.selected_slots.get(port_number)
        if not (
            self.wafer_loaded
            and self.wafer_source_port == port_number
            and self.wafer_source_slot == slot
        ):
            self._set_status("Select the loaded wafer before unloading it.")
            return False
        return self._unload_wafer()

    def _load_wafer(self):
        return self._start_load_operation(align=False)

    def _load_and_align(self):
        if not self.alignment_sites_defined or self.wafer_type == "Blank":
            self._set_status("Load and Align requires a patterned recipe with defined alignment sites.")
            return False
        return self._start_load_operation(align=True)

    def _start_load_operation(self, *, align: bool) -> bool:
        port = self.selected_port
        slot = self.selected_slots.get(port)
        if self._sequence_active:
            self._set_status("A wafer operation is already in progress.")
            return False
        if self.wafer_loaded:
            self._set_status("Unload the wafer on the chuck before loading another wafer.")
            return False
        if not self.carrier_loaded.get(port) or not self.carrier_mapped.get(port) or slot is None:
            self._set_status("Select a mapped wafer before loading.")
            return False
        if self.slot_states[port].get(slot) not in {"Present", "Loaded", "Aligned"}:
            self._set_status("The selected carrier slot does not contain a wafer.")
            return False
        phases = ["Loading", "Aligning"] if align else ["Loading"]

        def finish():
            self.wafer_loaded = True
            self.wafer_aligned = align
            self.wafer_source_port = port
            self.wafer_source_slot = slot
            self.slot_states[port][slot] = "Aligned" if align else "Loaded"
            if self.read_wafer_id:
                self.wafer_ids[port][slot] = f"W{port}-{slot:02d}"
            self.last_transfer_outcome = "Completed"
            self.last_transfer_error = ""
            final = "Aligned" if align else "Loaded"
            self._refresh()
            self._set_status(final)

        self._play_slot_animation(port, slot, phases, finish)
        return True

    def _align_wafer(self):
        if not self.wafer_loaded:
            self._set_status("Load a wafer before alignment.")
            return False
        if not self.alignment_sites_defined or self.wafer_type == "Blank":
            self._set_status("Alignment requires a patterned recipe with defined alignment sites.")
            return False
        if self._sequence_active:
            self._set_status("A wafer operation is already in progress.")
            return False
        port = self.wafer_source_port
        slot = self.wafer_source_slot

        def finish():
            self.wafer_aligned = True
            self.slot_states[port][slot] = "Aligned"
            self._refresh()
            self._set_status("Aligned")

        self._play_slot_animation(port, slot, ["Aligning"], finish)
        return True

    def _unload_wafer(self):
        if not self.wafer_loaded:
            self._set_status("No wafer is loaded.")
            return False
        if self._sequence_active:
            self._set_status("A wafer operation is already in progress.")
            return False
        port = self.wafer_source_port
        slot = self.wafer_source_slot
        if not self.carrier_loaded.get(port, False):
            self._set_status("Source carrier is unavailable; use Automatic Recovery.")
            return False

        def finish():
            if port is not None and slot is not None:
                self.slot_states[port][slot] = "Present"
            self.wafer_loaded = False
            self.wafer_aligned = False
            self.wafer_source_port = None
            self.wafer_source_slot = None
            self.last_transfer_outcome = "Completed"
            self.last_transfer_error = ""
            self._refresh()
            self._set_status("Unloaded")

        self._play_slot_animation(port, slot, ["Unloading"], finish)
        return True

    def _automatic_recovery(self):
        if self._sequence_active:
            self.finish_slot_animation()
        if not self.wafer_loaded:
            self._refresh()
            self._set_status("Automatic recovery found no wafer on the chuck.")
            return True
        port = self.wafer_source_port or self.selected_port
        slot = self.wafer_source_slot or self.selected_slots.get(port) or 25
        if not self.carrier_loaded.get(port):
            self._load_carrier(port)
        self.slot_states[port][slot] = "Present"
        self.wafer_loaded = False
        self.wafer_aligned = False
        self.wafer_source_port = None
        self.wafer_source_slot = None
        self._refresh()
        self._set_status(f"Automatic recovery returned the wafer to Port {port}, Slot {slot}.")
        return True

    def _play_slot_animation(self, port: int, slot: int, phases: list, finish: Callable):
        self._sequence_timer.stop()
        self._sequence = {
            "port": port,
            "slot": slot,
            "phases": list(phases),
            "index": 0,
            "elapsed_ms": 0,
            "finish": finish,
        }
        self.slot_states[port][slot] = phases[0]
        self._set_status(phases[0])
        self._refresh()
        if self.operation.duration_ms == 0:
            self._complete_slot_animation()
            return
        self._sequence_timer.start()

    def _tick_slot_animation(self):
        sequence = self._sequence
        if not sequence:
            self._sequence_timer.stop()
            return
        sequence["elapsed_ms"] += self._sequence_timer.interval()
        phase_index = min(
            len(sequence["phases"]) - 1,
            sequence["elapsed_ms"] // self._slot_phase_ms(),
        )
        port = sequence["port"]
        slot = sequence["slot"]
        if phase_index != sequence["index"]:
            sequence["index"] = phase_index
            self.slot_states[port][slot] = sequence["phases"][phase_index]
            self._set_status(sequence["phases"][phase_index])
            self._refresh()
        phase_elapsed = sequence["elapsed_ms"] - phase_index * self._slot_phase_ms()
        row = self.port_controls[port]["slots"][slot]
        row.pulse = min(1.0, phase_elapsed / 360.0)
        row.update()
        if sequence["elapsed_ms"] >= len(sequence["phases"]) * self._slot_phase_ms():
            self._sequence_timer.stop()
            self._complete_slot_animation()

    def _slot_phase_ms(self) -> int:
        return 800

    def advance_slot_animation(self):
        sequence = self._sequence
        if not sequence:
            return
        self._sequence_timer.stop()
        sequence["index"] += 1
        if sequence["index"] >= len(sequence["phases"]):
            self._complete_slot_animation()
            return
        phase = sequence["phases"][sequence["index"]]
        self.slot_states[sequence["port"]][sequence["slot"]] = phase
        self._set_status(phase)
        sequence["elapsed_ms"] = sequence["index"] * self._slot_phase_ms()
        self._refresh()
        self._sequence_timer.start()

    def finish_slot_animation(self):
        if not self._sequence:
            return
        self._sequence_timer.stop()
        self._complete_slot_animation()

    def _complete_slot_animation(self):
        sequence = self._sequence
        self._sequence = None
        self._sequence_timer.stop()
        if sequence:
            sequence["finish"]()

    @property
    def _sequence_active(self) -> bool:
        return self._sequence is not None

    def hideEvent(self, event):  # noqa: N802 - Qt override
        self.finish_slot_animation()
        super().hideEvent(event)

    def _set_orientation(self, angle: int):
        self.orientation = angle
        self._refresh()
        self._set_status(f"Required orientation changed to {angle} degrees.")

    def _operation_progress(self, state: dict):
        return None

    def _operation_active_changed(self, active: bool):
        if active:
            return
        self._refresh()

    def _refresh(self):
        if not hasattr(self, "port_controls"):
            return
        active = self._sequence_active
        for port_number, controls in self.port_controls.items():
            loaded = self.carrier_loaded[port_number]
            selected = self.selected_port == port_number
            selected_slot = self.selected_slots[port_number]
            mapped = bool(self.carrier_mapped.get(port_number)) and loaded
            controls["tab"].setChecked(selected)
            controls["tab"].setText(("▶ " if selected else "") + f"Port {port_number}")
            selected_is_loaded = (
                loaded
                and self.wafer_loaded
                and self.wafer_source_port == port_number
                and self.wafer_source_slot == selected_slot
            )
            controls["load"].setEnabled(
                mapped and selected_slot is not None and not active and not self.wafer_loaded
            )
            controls["unload"].setEnabled(selected_is_loaded and not active)
            controls["stack"].setCurrentIndex(0 if mapped else 1)
            controls["lamps"][0].setStyleSheet(_lamp_style(loaded))
            controls["lamps"][1].setStyleSheet(_lamp_style(mapped))
            for slot, row in controls["slots"].items():
                row.setEnabled(loaded)
                row.set_state(
                    self.slot_states[port_number].get(slot, "Absent"),
                    selected and loaded and selected_slot == slot,
                    self.orientation,
                )
            if not loaded:
                carrier_state, port_state, transfer = "No Cassette", "Ready to Load", "Ready to Load"
            elif not mapped:
                carrier_state, port_state, transfer = (
                    "Present",
                    "Carrier Present & Unclamped",
                    "Ready to Load",
                )
            elif self.wafer_loaded and self.wafer_source_port == port_number:
                carrier_state, port_state, transfer = (
                    "Mapped",
                    "Carrier Unlocked & Open",
                    "Carrier Allocated to Equipment",
                )
            else:
                carrier_state, port_state, transfer = (
                    "Mapped",
                    "Carrier Present & Unclamped",
                    "Ready to Unload",
                )
            controls["state"].setText(
                f"Carrier State   {carrier_state}\n"
                f"Port State      {port_state}\n"
                f"Transfer        {transfer}\n"
                "Port Size       300 mm"
            )

        port = self.selected_port
        slot = self.selected_slots.get(port)
        slot_state = "Absent" if slot is None else self.slot_states[port].get(slot, "Absent")
        kind = wafer_thumbnail_kind(slot_state)
        self.wafer_disk.set_state(kind, self.orientation)
        if kind == "empty":
            self.wafer_details.setText(
                "Port  -\n"
                "Slot  -\n"
                "State  Not Loaded\n"
                "Alignment  -\n"
                "Align. Angle  -\n"
                "Diameter  -\n"
                "Type  -"
            )
        else:
            alignment = "Aligned" if kind == "aligned" else ("Not Aligned" if kind == "loaded" else "-")
            state_text = "Loaded" if kind in {"loaded", "aligned"} else "Not Loaded"
            angle_text = f"{self.orientation}°" if kind == "aligned" else "-"
            self.wafer_details.setText(
                f"Port  {port}\n"
                f"Slot  {slot}\n"
                f"State  {state_text}\n"
                f"Alignment  {alignment}\n"
                f"Align. Angle  {angle_text}\n"
                "Diameter  300 mm\n"
                f"Type  {self.wafer_type}"
            )
        has_selected_wafer = self.carrier_loaded.get(self.selected_port) and self.selected_slots.get(self.selected_port) is not None
        can_align = self.alignment_sites_defined and self.wafer_type != "Blank"
        self.load_wafer_button.setEnabled(has_selected_wafer and not self.wafer_loaded and not active)
        self.load_align_button.setEnabled(has_selected_wafer and not self.wafer_loaded and can_align and not active)
        self.align_button.setEnabled(self.wafer_loaded and can_align and not active)
        self.unload_wafer_button.setEnabled(self.wafer_loaded and not active)
        self.recovery_button.setEnabled(self.wafer_loaded and not active)
        for button in self.orientation_controls.values():
            button.setEnabled(not active)
        for angle, button in self.orientation_controls.items():
            button.setChecked(angle == self.orientation)
        self._publish()

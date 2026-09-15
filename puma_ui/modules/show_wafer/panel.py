from __future__ import annotations

from typing import Callable, Optional

from ...qt_compat import (
    QColor,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QIcon,
    QLabel,
    QPainter,
    QPen,
    QPixmap,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSize,
    Qt,
    QVBoxLayout,
    QWidget,
)
from ..wafer_handling.operation import TimedWaferOperation


def _pixmap_icon(kind: str, size: int = 28) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    if kind in {"cassette", "cassette-disabled"}:
        active = kind == "cassette"
        body = QColor("#ff6f21" if active else "#9b9b9b")
        dark = QColor("#1d1d1d" if active else "#6d6d6d")
        painter.setPen(QPen(QColor("#333333"), 1))
        painter.setBrush(body)
        painter.drawRect(5, 5, 16, 18)
        painter.setBrush(QColor("#222222" if active else "#777777"))
        painter.drawEllipse(8, 8, 10, 10)
        painter.setPen(QPen(dark, 2))
        painter.drawLine(8, 22, 21, 14)
        painter.drawLine(21, 14, 21, 22)
        painter.setBrush(QColor("#333333" if active else "#777777"))
        painter.drawRect(2, 10, 5, 10)
    elif kind == "wafer":
        painter.setBrush(QColor("#595959"))
        painter.setPen(QPen(QColor("#f4f4f4"), 1))
        painter.drawEllipse(5, 5, 18, 18)
    elif kind == "load-align":
        painter.setBrush(QColor("#575757"))
        painter.setPen(QPen(QColor("#f4f4f4"), 1))
        painter.drawEllipse(5, 5, 18, 18)
        painter.setPen(QPen(QColor("#4d5fd4"), 3))
        painter.drawLine(10, 14, 20, 14)
    elif kind == "align":
        painter.setPen(QPen(QColor("#777777"), 3))
        painter.drawLine(8, 9, 20, 9)
        painter.drawLine(8, 18, 20, 18)
    elif kind == "recovery":
        painter.setBrush(QColor("#ed1c24"))
        painter.setPen(QPen(QColor("#ffffff"), 1))
        painter.drawEllipse(4, 4, 20, 20)
        painter.setPen(QPen(QColor("#ffffff"), 4))
        painter.drawLine(14, 8, 14, 20)
        painter.drawLine(8, 14, 20, 14)

    painter.end()
    return QIcon(pixmap)


class EmptyWaferDisk(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.loaded = False
        self.aligned = False
        self.orientation = 180
        self.setFixedSize(86, 86)

    def set_state(self, loaded: bool, aligned: bool, orientation: int):
        self.loaded = loaded
        self.aligned = aligned
        self.orientation = orientation
        self.update()

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#555555") if self.loaded else QColor("#c4c0b0"))
        pen = QPen(QColor("#5f5b53"), 1)
        if not self.loaded:
            pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        painter.drawEllipse(8, 8, 68, 68)
        if self.loaded:
            painter.setPen(QPen(QColor("#596ee3") if self.aligned else QColor("#aaaaaa"), 2))
            for offset in [-14, 0, 14]:
                painter.drawLine(24, 42 + offset, 62, 42 + offset)
            notch = {
                0: (39, 5, 8, 8),
                90: (73, 39, 8, 8),
                180: (39, 73, 8, 8),
                270: (5, 39, 8, 8),
            }[self.orientation]
            painter.setBrush(QColor("#c4c0b0"))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(*notch)


class OrientationDisk(QWidget):
    def __init__(self, notch: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.notch = notch
        self.setFixedSize(26, 24)

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#242424"))
        painter.setPen(QPen(QColor("#111111"), 1))
        painter.drawEllipse(3, 2, 20, 20)
        painter.setBrush(QColor("#c4c0b0"))
        painter.setPen(Qt.NoPen)
        if self.notch == "up":
            painter.drawEllipse(9, 0, 8, 8)
        elif self.notch == "right":
            painter.drawEllipse(17, 8, 8, 8)
        elif self.notch == "down":
            painter.drawEllipse(9, 16, 8, 8)
        else:
            painter.drawEllipse(1, 8, 8, 8)


class CassetteBody(QFrame):
    def __init__(
        self,
        port_number: int,
        on_slot_selected: Optional[Callable[[int, int], None]] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.port_number = port_number
        self.on_slot_selected = on_slot_selected
        self.selected_slot = 25 if port_number == 1 else None
        self.slot_states = {slot: "Absent" for slot in range(1, 26)}
        self.carrier_loaded = False
        self.setMinimumSize(150, 390)

    def set_state(self, carrier_loaded: bool, selected_slot: Optional[int], slot_states: dict):
        self.carrier_loaded = carrier_loaded
        self.selected_slot = selected_slot
        self.slot_states = dict(slot_states)
        self.update()

    def _slot_geometry(self):
        rect = self.rect().adjusted(9, 8, -9, -10)
        slot_top = rect.top() + 15
        slot_height = max(12, int((rect.height() - 34) / 25))
        return rect, slot_top, slot_height

    def mousePressEvent(self, event):  # noqa: N802 - Qt override
        if not self.carrier_loaded:
            return
        point = event.position().toPoint() if hasattr(event, "position") else event.pos()
        rect, slot_top, slot_height = self._slot_geometry()
        if not rect.contains(point):
            return
        row = (point.y() - slot_top) // slot_height
        slot = 25 - row
        if 1 <= slot <= 25 and self.slot_states.get(slot) != "Absent":
            if self.on_slot_selected:
                self.on_slot_selected(self.port_number, slot)

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect, slot_top, slot_height = self._slot_geometry()
        painter.setBrush(QColor("#a8a8a4"))
        painter.setPen(QPen(QColor("#777777"), 5))
        painter.drawRect(rect.adjusted(0, 10, 0, 0))
        painter.setPen(QPen(QColor("#f7f7f7"), 2))
        painter.drawLine(rect.left() + 5, rect.top() + 10, rect.right() - 5, rect.top() + 10)

        for row, slot in enumerate(range(25, 0, -1)):
            y = slot_top + row * slot_height
            if y + slot_height > rect.bottom() - 11:
                break
            label_rect = rect.adjusted(4, 0, -rect.width() + 27, 0)
            label_rect.setTop(y - 1)
            label_rect.setBottom(y + slot_height)
            slot_state = self.slot_states.get(slot, "Absent")
            selected = slot == self.selected_slot
            painter.setPen(QColor("#f5f5f5") if selected else QColor("#444444"))
            painter.drawText(label_rect, Qt.AlignRight | Qt.AlignVCenter, str(slot))

            marker_color = QColor("#1ed02e") if slot_state in {"Present", "Loaded", "Aligned"} else QColor("#f3f3f3")
            painter.setBrush(marker_color)
            painter.setPen(QPen(QColor("#004d00") if slot_state != "Absent" else QColor("#808080"), 1))
            painter.drawEllipse(rect.left() + 29, y + 2, 10, 10)

            slot_rect = rect.adjusted(43, 0, -5, 0)
            slot_rect.setTop(y + 1)
            slot_rect.setBottom(y + slot_height - 1)
            if selected:
                painter.setBrush(QColor("#c9f3a8"))
                painter.setPen(QPen(QColor("#1420c8"), 2))
                painter.drawRoundedRect(slot_rect, 3, 3)
                painter.setPen(QPen(QColor("#1e6410"), 1))
                painter.drawText(slot_rect, Qt.AlignCenter, slot_state)
            else:
                gradient_color = QColor("#ffffff") if slot_state != "Absent" else QColor("#dedede")
                painter.setBrush(gradient_color)
                painter.setPen(QPen(QColor("#a8a8a8"), 1))
                painter.drawRoundedRect(slot_rect, 4, 4)

        painter.setPen(QPen(QColor("#777777"), 2))
        painter.drawLine(rect.left(), rect.bottom() - 7, rect.right(), rect.bottom() - 7)
        painter.setBrush(QColor("#008a1d"))
        painter.setPen(QPen(QColor("#006812"), 1))
        painter.drawEllipse(rect.center().x() - 12, rect.bottom() - 9, 8, 8)
        painter.drawEllipse(rect.center().x() + 4, rect.bottom() - 9, 8, 8)


class ShowWaferPanel(QFrame):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        operation_duration_ms: int = 10000,
        operation_timeout_ms: int = 12000,
    ):
        super().__init__(parent)
        self.setMinimumWidth(720)
        self.setObjectName("showWaferPanel")
        self.port_widgets = {}
        self.port_controls = {}
        self.selected_port = 1
        self.selected_slots = {1: 25, 2: 25, 3: None}
        self.carrier_loaded = {1: True, 2: True, 3: False}
        self.slot_states = {
            1: {slot: ("Aligned" if slot == 25 else "Present") for slot in range(1, 26)},
            2: {slot: "Present" for slot in range(1, 26)},
            3: {slot: "Absent" for slot in range(1, 26)},
        }
        self.wafer_loaded = True
        self.wafer_aligned = True
        self.wafer_source_port = 1
        self.wafer_source_slot = 25
        self.orientation = 180
        self.wafer_type = "Patterned"
        self.alignment_sites_defined = True
        self.last_transfer_outcome = "Idle"
        self.last_transfer_error = ""
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
            QLabel[section="true"] {
                color: #1b58d4;
                font-weight: 600;
            }
            QPushButton {
                background: #eceae0;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-height: 25px;
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
        self._refresh()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 8)
        layout.setSpacing(10)
        layout.addWidget(self._wafer_operations())
        for port_number in [1, 2, 3]:
            port = self._load_port(port_number)
            self.port_widgets[port_number] = port
            layout.addWidget(port, 1)

    def _wafer_operations(self) -> QWidget:
        panel = QFrame()
        panel.setFixedWidth(226)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        top = QHBoxLayout()
        top.setSpacing(7)
        self.wafer_disk = EmptyWaferDisk()
        top.addWidget(self.wafer_disk, alignment=Qt.AlignLeft | Qt.AlignTop)
        self.wafer_details = QLabel()
        self.wafer_details.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.wafer_details.setStyleSheet("font-size: 9px;")
        top.addWidget(self.wafer_details, 1)
        layout.addLayout(top)

        title = QLabel("Wafer Operations")
        title.setProperty("section", True)
        layout.addWidget(title)

        operations_box = QFrame()
        operations_box.setStyleSheet(
            """
            QFrame {
                background: #d0ccbc;
                border: 1px solid #b0ab9d;
            }
            """
        )
        operations = QVBoxLayout(operations_box)
        operations.setContentsMargins(7, 7, 7, 8)
        operations.setSpacing(7)

        button_row = QHBoxLayout()
        button_row.setSpacing(5)
        self.load_wafer_button = self._operation_button("Load", "wafer")
        self.load_align_button = self._operation_button("Load &&\nAlign", "load-align")
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
        self.unload_wafer_button.setIconSize(QSize(22, 22))
        self.unload_wafer_button.setFixedHeight(31)
        self.unload_wafer_button.clicked.connect(self._unload_wafer)
        operations.addWidget(self.unload_wafer_button)

        self.recovery_button = QPushButton("Automatic Recovery")
        self.recovery_button.setIcon(_pixmap_icon("recovery", 28))
        self.recovery_button.setIconSize(QSize(26, 26))
        self.recovery_button.setFixedHeight(34)
        self.recovery_button.clicked.connect(self._automatic_recovery)
        operations.addWidget(self.recovery_button)

        self.failure_mode = QComboBox()
        self.failure_mode.addItems(TimedWaferOperation.MODES)
        self.failure_mode.setToolTip("Choose the result for the next wafer transfer")
        operations.addWidget(self.failure_mode)

        self.operation_progress = QProgressBar()
        self.operation_progress.setRange(0, 100)
        self.operation_progress.setValue(0)
        self.operation_progress.setTextVisible(True)
        operations.addWidget(self.operation_progress)
        self.operation_timer = QLabel("Timer: 00:10")
        operations.addWidget(self.operation_timer)
        self.abort_operation_button = QPushButton("Abort Operation")
        self.abort_operation_button.setEnabled(False)
        self.abort_operation_button.clicked.connect(self._abort_operation)
        operations.addWidget(self.abort_operation_button)
        layout.addWidget(operations_box)

        orient = QLabel("Change Orientation:")
        orient.setStyleSheet("font-weight: 600;")
        layout.addWidget(orient)
        layout.addLayout(self._orientation_row())
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #333333; font-size: 9px;")
        layout.addWidget(self.status_label)
        layout.addStretch(1)
        return panel

    def _operation_button(self, label: str, icon_name: str) -> QPushButton:
        button = QPushButton(label)
        button.setIcon(_pixmap_icon(icon_name, 26))
        button.setIconSize(QSize(16, 16))
        button.setFixedSize(66, 62)
        return button

    def _orientation_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(6)
        self.orientation_controls = {}
        for text, notch, angle in [
            ("Up\n(0)", "up", 0),
            ("Right\n(90)", "right", 90),
            ("Down\n(180)", "down", 180),
            ("Left\n(270)", "left", 270),
        ]:
            item = QVBoxLayout()
            item.setSpacing(1)
            disk = OrientationDisk(notch)
            disk.setToolTip(f"Change orientation to {angle} degrees")
            item.addWidget(disk, alignment=Qt.AlignHCenter)
            label = QLabel(text)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("font-size: 9px;")
            item.addWidget(label)
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
        panel.setStyleSheet(
            """
            QFrame#loadPort {
                background: transparent;
                border: 0;
            }
            QLabel#portTab {
                background: #f0f0f0;
                border: 1px solid #777777;
                border-radius: 4px;
                font-weight: 600;
                padding: 1px 20px;
            }
            """
        )
        panel.setObjectName("loadPort")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        commands = QHBoxLayout()
        commands.setSpacing(4)
        load = QPushButton("Load")
        load.setIcon(_pixmap_icon("cassette", 28))
        load.setIconSize(QSize(28, 28))
        load.setFixedSize(76, 40)
        load.clicked.connect(lambda checked=False, value=port_number: self._load_carrier(value))
        unload = QPushButton("Unload")
        unload.setIcon(_pixmap_icon("cassette-disabled", 28))
        unload.setIconSize(QSize(28, 28))
        unload.setFixedSize(76, 40)
        unload.clicked.connect(lambda checked=False, value=port_number: self._unload_carrier(value))
        commands.addWidget(load)
        commands.addWidget(unload)
        layout.addLayout(commands)

        tab = QLabel()
        tab.setObjectName("portTab")
        tab.setAlignment(Qt.AlignCenter)
        layout.addWidget(tab, alignment=Qt.AlignHCenter)

        cassette = CassetteBody(port_number, self._select_slot)
        layout.addWidget(cassette, 1)

        state = QLabel()
        state.setAlignment(Qt.AlignHCenter)
        state.setStyleSheet("font-size: 9px;")
        layout.addWidget(state)
        self.port_controls[port_number] = {
            "load": load,
            "unload": unload,
            "tab": tab,
            "cassette": cassette,
            "state": state,
        }
        return panel

    def set_visible_ports(self, choice: str):
        count = max(1, min(int(choice), len(self.port_widgets)))
        for port_number, widget in self.port_widgets.items():
            widget.setVisible(port_number <= count)

    def update_recipe(self, recipe: dict):
        wafer_properties = recipe.get("wafer_properties") or {}
        self.wafer_type = wafer_properties.get("type", self.wafer_type)
        alignment = recipe.get("alignment") or {}
        self.alignment_sites_defined = bool(alignment.get("sites_defined")) and (
            not alignment.get("derivative_origin_reselection_required")
            or alignment.get("derivative_origin_reselected")
        )
        orientation = str(wafer_properties.get("orientation", recipe.get("wafer_orientation", self.orientation)))
        for angle in (0, 90, 180, 270):
            if str(angle) in orientation:
                self.orientation = angle
                break
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

    def _select_slot(self, port_number: int, slot: int):
        if not self.carrier_loaded[port_number]:
            self._set_status(f"Load a carrier on Port {port_number} first.")
            return
        self.selected_port = port_number
        self.selected_slots[port_number] = slot
        self._refresh()
        self._set_status(f"Port {port_number}, Slot {slot} selected.")

    def _load_carrier(self, port_number: int):
        self.carrier_loaded[port_number] = True
        self.slot_states[port_number] = {slot: "Present" for slot in range(1, 26)}
        self.selected_slots[port_number] = 25
        self.selected_port = port_number
        self._refresh()
        self._set_status(f"Carrier loaded and mapped on Port {port_number}.")

    def _unload_carrier(self, port_number: int):
        if self.wafer_loaded and self.wafer_source_port == port_number:
            self._set_status("Unload the wafer before removing its source carrier.")
            return False
        self.carrier_loaded[port_number] = False
        self.slot_states[port_number] = {slot: "Absent" for slot in range(1, 26)}
        self.selected_slots[port_number] = None
        if self.selected_port == port_number:
            self.selected_port = next((port for port, loaded in self.carrier_loaded.items() if loaded), 1)
        self._refresh()
        self._set_status(f"Carrier unloaded from Port {port_number}.")
        return True

    def _load_wafer(self):
        slot = self.selected_slots.get(self.selected_port)
        if self.wafer_loaded:
            self._set_status("Unload the wafer on the stage before loading another wafer.")
            return False
        if not self.carrier_loaded[self.selected_port] or slot is None:
            self._set_status("Select a wafer in a mapped carrier first.")
            return False
        if self.slot_states[self.selected_port].get(slot) != "Present":
            self._set_status("The selected slot does not contain an available wafer.")
            return False
        return self._start_load_operation(align=False)

    def _load_and_align(self):
        if not self.alignment_sites_defined or self.wafer_type == "Blank":
            self._set_status("Load and Align requires a patterned recipe with defined alignment sites.")
            return False
        return self._start_load_operation(align=True)

    def _start_load_operation(self, *, align: bool) -> bool:
        port = self.selected_port
        slot = self.selected_slots.get(port)
        if self.operation.active:
            self._set_status("A wafer operation is already in progress.")
            return False
        if self.wafer_loaded:
            self._set_status("Unload the wafer on the stage before loading another wafer.")
            return False
        if not self.carrier_loaded[port] or slot is None:
            self._set_status("Select a wafer in a mapped carrier first.")
            return False
        if self.slot_states[port].get(slot) != "Present":
            self._set_status("The selected slot does not contain an available wafer.")
            return False

        def complete():
            self.wafer_loaded = True
            self.wafer_aligned = align
            self.wafer_source_port = port
            self.wafer_source_slot = slot
            self.slot_states[port][slot] = "Aligned" if align else "Loaded"
            self.last_transfer_outcome = "Completed"
            self.last_transfer_error = ""
            self._refresh()
            result = "Loaded and aligned wafer" if align else "Loaded wafer"
            self._set_status(f"{result} from Port {port}, Slot {slot}.")

        return self.operation.start(
            "load_align" if align else "load",
            failure_mode=self.failure_mode.currentText(),
            on_success=complete,
            on_failure=self._operation_failed,
        )

    def _operation_progress(self, state: dict):
        if not hasattr(self, "operation_progress"):
            return
        self.operation_progress.setValue(state["progress"])
        if state["active"]:
            self.operation_timer.setText(f"Timer: 00:{state['remaining_seconds']:02d}")
            self._set_status(
                f"{state['phase']} - {state['remaining_seconds']} seconds remaining"
            )
        elif state["outcome"] == "Completed":
            self.operation_timer.setText("Timer: 00:00")

    def _operation_active_changed(self, active: bool):
        if not hasattr(self, "abort_operation_button"):
            return
        self.abort_operation_button.setEnabled(active)
        self._refresh()

    def _operation_failed(self, outcome: str, error_code: str):
        self.last_transfer_outcome = outcome
        self.last_transfer_error = error_code
        self._set_status(f"{outcome}: {error_code}. Wafer state was not changed; retry is available.")

    def _abort_operation(self):
        self.operation.abort()

    def _align_wafer(self):
        if not self.wafer_loaded:
            self._set_status("Load a wafer before alignment.")
            return False
        if not self.alignment_sites_defined or self.wafer_type == "Blank":
            self._set_status("Alignment requires a patterned recipe with defined alignment sites.")
            return False
        self.wafer_aligned = True
        self.slot_states[self.wafer_source_port][self.wafer_source_slot] = "Aligned"
        self._refresh()
        self._set_status("Wafer aligned.")
        return True

    def _unload_wafer(self):
        if not self.wafer_loaded:
            self._set_status("No wafer is loaded on the stage.")
            return False
        source_port = self.wafer_source_port
        source_slot = self.wafer_source_slot
        if not self.carrier_loaded.get(source_port, False):
            self._set_status("Source carrier is unavailable; use Automatic Recovery.")
            return False
        self.slot_states[source_port][source_slot] = "Present"
        self.wafer_loaded = False
        self.wafer_aligned = False
        self.wafer_source_port = None
        self.wafer_source_slot = None
        self._refresh()
        self._set_status(f"Wafer returned to Port {source_port}, Slot {source_slot}.")
        return True

    def _automatic_recovery(self):
        if self.wafer_loaded:
            return self._unload_wafer()
        self._refresh()
        self._set_status("Wafer handling state verified; no recovery action is required.")
        return True

    def _set_orientation(self, angle: int):
        self.orientation = angle
        self._refresh()
        self._set_status(f"Required orientation changed to {angle} degrees.")

    def _refresh(self):
        active = hasattr(self, "operation") and self.operation.active
        for port_number, controls in self.port_controls.items():
            loaded = self.carrier_loaded[port_number]
            selected = self.selected_port == port_number
            controls["tab"].setText(f">  Port {port_number}" if selected else f"Port {port_number}")
            controls["load"].setEnabled(not loaded and not active)
            controls["unload"].setEnabled(loaded and not active and not (
                self.wafer_loaded and self.wafer_source_port == port_number
            ))
            controls["cassette"].setEnabled(not active)
            controls["cassette"].set_state(
                loaded,
                self.selected_slots[port_number],
                self.slot_states[port_number],
            )
            if loaded:
                controls["state"].setText(
                    "Carrier State   Mapped\n"
                    "Port State      Carrier Present\n"
                    "Transfer        Ready\n"
                    "Port Size       300 mm"
                )
            else:
                controls["state"].setText(
                    "Carrier State   No Cassette\n"
                    "Port State      Ready to Load\n"
                    "Transfer        Ready to Load\n"
                    "Port Size       300 mm"
                )

        source_port = self.wafer_source_port if self.wafer_loaded else "-"
        source_slot = self.wafer_source_slot if self.wafer_loaded else "-"
        self.wafer_details.setText(
            f"Port  {source_port}\n"
            f"Slot  {source_slot}\n"
            f"State  {'Loaded' if self.wafer_loaded else 'Not Loaded'}\n"
            f"Alignment  {'Aligned' if self.wafer_aligned else 'Not Aligned'}\n"
            f"Align. Angle  {self.orientation} deg\n"
            "Diameter  300 mm\n"
            f"Type  {self.wafer_type}"
        )
        self.wafer_disk.set_state(self.wafer_loaded, self.wafer_aligned, self.orientation)
        self.load_wafer_button.setEnabled(not self.wafer_loaded and not active)
        can_align = self.alignment_sites_defined and self.wafer_type != "Blank"
        self.load_align_button.setEnabled(not self.wafer_loaded and can_align and not active)
        self.align_button.setEnabled(self.wafer_loaded and not self.wafer_aligned and can_align and not active)
        self.unload_wafer_button.setEnabled(self.wafer_loaded and not active)
        self.recovery_button.setEnabled(self.wafer_loaded and not active)
        self.failure_mode.setEnabled(not active)
        for button in self.orientation_controls.values():
            button.setEnabled(not active)
        for angle, button in self.orientation_controls.items():
            button.setChecked(angle == self.orientation)

from __future__ import annotations

from typing import Dict, Optional

from ...qt_compat import (
    QApplication,
    QCheckBox,
    QColor,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QIcon,
    QLabel,
    QMessageBox,
    QPainter,
    QPen,
    QPixmap,
    QPushButton,
    QRadioButton,
    QSize,
    QSizePolicy,
    QSlider,
    QStackedWidget,
    QTimer,
    Qt,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from ...widgets import StatusDot, WaferDisk, paint_slot_wafer_symbol, wafer_disk_with_notch, wafer_thumbnail_kind
from ..wafer_properties.dialogs import DEFAULT_WAFER_PROPERTIES, EditLayerDatabaseDialog
from .operation import TimedWaferOperation

LOAD_PORTS = (1, 2)
_LAMP_ON = "#3cbf4a"
_LAMP_OFF = "#6a6a6a"


def _loaded_wafer_symbol(origin_x: float, origin_y: float, size: float, orientation: int):
    """Green loaded-wafer disk with a small V notch at the current orientation."""
    return wafer_disk_with_notch(origin_x, origin_y, size, orientation)


def _lamp_style(lit: bool) -> str:
    color = _LAMP_ON if lit else _LAMP_OFF
    return f"background: {color}; border-radius: 5px; border: 1px solid #3a3a3a;"


def _operation_icon(kind: str, size: int = 28) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    if kind == "load":
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#1a1a1a"))
        painter.drawEllipse(4, 4, size - 8, size - 8)
    elif kind == "load-align":
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#1a1a1a"))
        painter.drawEllipse(4, 4, size - 8, size - 8)
        painter.setPen(QPen(QColor("#e8e8e8"), 2))
        painter.drawLine(8, size // 2 - 3, size - 8, size // 2 - 3)
        painter.drawLine(8, size // 2 + 3, size - 8, size // 2 + 3)
    elif kind == "align":
        painter.setPen(QPen(QColor("#8a8a8a"), 3, Qt.SolidLine, Qt.FlatCap))
        painter.drawLine(5, size // 2 - 4, size - 5, size // 2 - 4)
        painter.drawLine(5, size // 2 + 4, size - 5, size // 2 + 4)
    elif kind == "unload":
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor("#8a8a8a"), 2))
        painter.drawEllipse(2, 2, size - 4, size - 4)
    painter.end()
    return QIcon(pixmap)


class _OrientationMark(QWidget):
    """Gray wafer disk whose notch shows Up, Right, Down, or Left."""

    def __init__(self, angle: int, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.angle = angle
        self.chosen = False
        self.radio = None
        self.setFixedSize(42, 30)

    def set_chosen(self, chosen: bool):
        if self.chosen != chosen:
            self.chosen = chosen
            self.update()

    def mousePressEvent(self, event):  # noqa: N802 - Qt override
        if self.radio is not None and self.radio.isEnabled():
            self.radio.click()

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        size = 26.0
        origin_x = (self.width() - size) / 2
        origin_y = 1.0
        path = _loaded_wafer_symbol(origin_x, origin_y, size, self.angle)
        painter.setPen(QPen(QColor("#222222"), 1))
        painter.setBrush(QColor("#242424") if self.chosen else QColor("#8d8d8d"))
        painter.drawPath(path)
        painter.end()


class MatchingStack(QStackedWidget):
    def sizeHint(self):  # noqa: N802 - Qt override
        return self._largest("sizeHint")

    def minimumSizeHint(self):  # noqa: N802 - Qt override
        return self._largest("minimumSizeHint")

    def _largest(self, method: str) -> QSize:
        result = QSize(0, 0)
        for index in range(self.count()):
            result = result.expandedTo(getattr(self.widget(index), method)())
        return result


class WaferHandlingDialog(QDialog):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        selected_port: int = 1,
        state: Optional[dict] = None,
        recipe: Optional[dict] = None,
        operation_duration_ms: int = 10000,
        operation_timeout_ms: int = 12000,
    ):
        super().__init__(parent)
        self.setWindowTitle("Wafer Handling")
        self.resize(900, 640)
        self.setMinimumSize(720, 520)
        self.selected_port = selected_port if selected_port in LOAD_PORTS else 1
        self.carrier_loaded = {1: True, 2: False}
        self.carrier_mapped = {1: True, 2: False}
        self.selected_slots = {1: 25, 2: None}
        self.slot_states = {
            1: {slot: "Present" for slot in range(1, 26)},
            2: {slot: "Absent" for slot in range(1, 26)},
        }
        self.wafer_ids = {1: {}, 2: {}}
        self.wafer_loaded = False
        self.wafer_aligned = False
        self.wafer_source_port = None
        self.wafer_source_slot = None
        self.read_wafer_id = False
        alignment = (recipe or {}).get("alignment") or {}
        self.alignment_sites_defined = True if recipe is None else (
            bool(alignment.get("sites_defined"))
            and (
                not alignment.get("derivative_origin_reselection_required")
                or alignment.get("derivative_origin_reselected")
            )
        )
        self.wafer_type = (recipe or {}).get("wafer_properties", {}).get("type", "Patterned")
        self.recipe_laser_sensitive = bool(
            (recipe or {}).get("wafer_properties", {}).get("laser_power_sensitive", True)
        )
        self.layer_types = [dict(layer) for layer in DEFAULT_WAFER_PROPERTIES["layer_types"]]
        if isinstance(state, dict):
            self.selected_port = int(state.get("selected_port", self.selected_port))
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
                    self.selected_slots[port_number] = value
            self.wafer_loaded = bool(state.get("wafer_loaded", False))
            self.wafer_aligned = bool(state.get("wafer_aligned", False)) and self.wafer_loaded
            for port, slots in (state.get("slot_states") or {}).items():
                port_number = int(port)
                if port_number not in self.slot_states:
                    continue
                self.slot_states[port_number].update({int(slot): value for slot, value in slots.items()})
            for port, identifiers in (state.get("wafer_ids") or {}).items():
                port_number = int(port)
                if port_number not in self.wafer_ids:
                    continue
                self.wafer_ids[port_number].update({int(slot): value for slot, value in identifiers.items()})
            source_port = state.get("wafer_source_port")
            self.wafer_source_port = source_port if source_port in LOAD_PORTS else None
            self.wafer_source_slot = state.get("wafer_source_slot") if self.wafer_source_port else None
        runtime_state = state or {}
        self.read_wafer_id = bool(runtime_state.get("read_wafer_id", False))
        self.required_orientation = str(runtime_state.get("required_orientation", "180"))
        self.last_transfer_outcome = str(runtime_state.get("last_transfer_outcome", "Idle"))
        self.last_transfer_error = str(runtime_state.get("last_transfer_error", ""))
        self._build_ui()
        self.operation = TimedWaferOperation(
            self,
            duration_ms=operation_duration_ms,
            timeout_ms=operation_timeout_ms,
            on_progress=self._operation_progress,
            on_active_changed=self._operation_active_changed,
        )
        self._sequence = None
        self._sequence_timer = QTimer(self)
        self._sequence_timer.setInterval(40)
        self._sequence_timer.timeout.connect(self._tick_slot_animation)
        self._refresh_all()
        self._fit_within_host()

    def result_state(self) -> dict:
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
            "required_orientation": self.orientation_combo.currentText(),
            "last_transfer_outcome": self.last_transfer_outcome,
            "last_transfer_error": self.last_transfer_error,
        }

    def _build_ui(self):
        self.setStyleSheet(
            """
            QDialog {
                background: #c9c5bb;
                color: #111111;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10px;
            }
            QPushButton {
                background: #e7e5dc;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-height: 24px;
                padding: 2px 7px;
            }
            QPushButton:checked {
                background: #ffffff;
                border: 2px solid #2b5fd9;
            }
            QFrame#loadPort {
                background: #aaa9a6;
                border-left: 5px solid #777777;
                border-right: 5px solid #777777;
                border-bottom: 14px solid #777777;
            }
            QLabel#portTab {
                background: #eeeeee;
                border: 1px solid #777777;
                border-radius: 4px;
                font-weight: 600;
                padding: 1px 24px;
            }
            QLabel[section="true"] {
                font-weight: 600;
            }
            QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {
                background: #ffffff;
                border: 1px solid #77736b;
                min-height: 22px;
            }
            """
        )

        main = QVBoxLayout(self)
        main.setContentsMargins(10, 10, 10, 10)
        main.setSpacing(8)

        content = QHBoxLayout()
        content.setSpacing(12)
        self.port_panels: Dict[int, PortPanel] = {}
        for port_number in LOAD_PORTS:
            panel = PortPanel(port_number, self)
            self.port_panels[port_number] = panel
            content.addWidget(panel, 1)
        content.addWidget(self._right_controls(), 0)
        main.addLayout(content, 1)

        footer = QHBoxLayout()
        self.help_button = QPushButton("?")
        self.help_button.setFixedSize(30, 30)
        self.help_button.setStyleSheet(
            "border-radius: 14px; background: #2f5dd2; color: white; font-weight: 700;"
        )
        self.help_button.clicked.connect(self._show_help)
        footer.addWidget(self.help_button)
        footer.addStretch(1)
        close = QPushButton("Close")
        close.setFixedSize(110, 30)
        close.clicked.connect(self._close_dialog)
        footer.addWidget(close)
        footer.addStretch(1)
        self.advanced_button = QPushButton("Advanced")
        self.advanced_button.setCheckable(True)
        self.advanced_button.clicked.connect(self._toggle_advanced)
        footer.addWidget(self.advanced_button)
        main.addLayout(footer)

    def _right_controls(self) -> QWidget:
        panel = QFrame()
        panel.setFixedWidth(278)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self._wafer_operations())
        layout.addWidget(self._wafer_state_panel())
        layout.addWidget(self._orientation_panel())
        self.advanced_laser_panel = self._laser_panel()
        self.advanced_dark_panel = self._dark_wafer_panel()
        layout.addWidget(self.advanced_laser_panel)
        layout.addWidget(self.advanced_dark_panel)
        self.advanced_sim_panel = self._simulation_panel()
        self.advanced_sim_panel.setVisible(False)
        layout.addWidget(self.advanced_sim_panel)
        layout.addStretch(1)
        return panel

    def _wafer_operations(self) -> QWidget:
        group = QGroupBox("Wafer Operations")
        group.setStyleSheet(
            "QGroupBox { border: 1px solid #8f8b82; margin-top: 8px; font-weight: 600; background: transparent; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }"
        )
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(6)

        row = QHBoxLayout()
        row.setSpacing(4)
        self.load_wafer_button = self._operation_button("Load", "load")
        self.load_wafer_button.clicked.connect(self._load_wafer)
        self.load_align_button = self._operation_button("Load &&\nAlign", "load-align")
        self.load_align_button.clicked.connect(self._load_and_align)
        self.align_button = self._operation_button("Align", "align")
        self.align_button.clicked.connect(self._align_wafer)
        row.addWidget(self.load_wafer_button)
        row.addWidget(self.load_align_button)
        row.addWidget(self.align_button)
        layout.addLayout(row)

        self.unload_wafer_button = QPushButton("Unload Wafer")
        self.unload_wafer_button.setIcon(_operation_icon("unload", 22))
        self.unload_wafer_button.setIconSize(QSize(20, 20))
        self.unload_wafer_button.setMinimumHeight(32)
        self.unload_wafer_button.clicked.connect(self._unload_wafer)
        layout.addWidget(self.unload_wafer_button)

        self.recovery_button = QPushButton("Automatic Recovery")
        self.recovery_button.setIcon(self._recovery_icon())
        self.recovery_button.setIconSize(QSize(18, 18))
        self.recovery_button.clicked.connect(self._automatic_recovery)
        layout.addWidget(self.recovery_button)

        self.operation_status = QLabel("", self)
        self.operation_status.hide()
        return group

    def _operation_button(self, label: str, icon_name: str) -> QToolButton:
        button = QToolButton()
        button.setText(label)
        button.setIcon(_operation_icon(icon_name, 30))
        button.setIconSize(QSize(26, 26))
        button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        button.setMinimumHeight(62)
        button.setAutoRaise(False)
        button.setStyleSheet(
            """
            QToolButton {
                background: #eceae0;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                padding: 3px 1px;
                color: #111111;
                font-size: 9px;
            }
            QToolButton:disabled {
                color: #8a8a8a;
                background: #d8d5cc;
            }
            """
        )
        return button

    def _simulation_panel(self) -> QWidget:
        group = QFrame()
        group.setStyleSheet("QFrame { border: 1px solid #8f8b82; }")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)
        title = QLabel("Simulator Transfer")
        title.setProperty("section", True)
        layout.addWidget(title)

        self.read_id_check = QCheckBox("Read Wafer ID during prealignment")
        self.read_id_check.setChecked(self.read_wafer_id)
        self.read_id_check.toggled.connect(lambda checked: setattr(self, "read_wafer_id", checked))
        layout.addWidget(self.read_id_check)

        simulation = QHBoxLayout()
        simulation.addWidget(QLabel("Simulation:"))
        self.failure_mode = QComboBox()
        self.failure_mode.addItems(TimedWaferOperation.MODES)
        self.failure_mode.setToolTip("Choose the result for the next wafer transfer")
        simulation.addWidget(self.failure_mode, 1)
        layout.addLayout(simulation)
        return group

    def _recovery_icon(self) -> QIcon:
        pixmap = QPixmap(18, 18)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#e10600"))
        painter.drawEllipse(0, 0, 18, 18)
        painter.setPen(QPen(QColor("#ffffff"), 2))
        painter.drawLine(9, 4, 9, 14)
        painter.drawLine(4, 9, 14, 9)
        painter.end()
        return QIcon(pixmap)

    def _wafer_state_panel(self) -> QWidget:
        panel = QFrame()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.wafer_disk = WaferDisk()
        layout.addWidget(self.wafer_disk)
        self.wafer_state = QLabel()
        self.wafer_state.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        layout.addWidget(self.wafer_state, 1)
        return panel

    def _orientation_panel(self) -> QWidget:
        panel = QFrame()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(QLabel("Required Orientation:"))
        row = QHBoxLayout()
        row.setSpacing(2)
        self.orientation_buttons = []
        choices = ((0, "Up"), (90, "Right"), (180, "Down"), (270, "Left"))
        for angle, name in choices:
            column = QVBoxLayout()
            column.setSpacing(0)
            mark = _OrientationMark(angle, panel)
            column.addWidget(mark, alignment=Qt.AlignHCenter)
            caption = QLabel(f"{name}\n({angle}°)")
            caption.setAlignment(Qt.AlignHCenter)
            caption.setStyleSheet("font-size: 9px;")
            column.addWidget(caption)
            button = QRadioButton(panel)
            button.setProperty("angle", str(angle))
            button.mark = mark
            mark.radio = button
            button.clicked.connect(lambda checked=False, value=str(angle): self._set_orientation(value))
            column.addWidget(button, alignment=Qt.AlignHCenter)
            row.addLayout(column, 1)
            self.orientation_buttons.append(button)
        layout.addLayout(row)
        self.orientation_combo = QComboBox(panel)
        self.orientation_combo.addItems(["0", "90", "180", "270"])
        self.orientation_combo.setCurrentText(self.required_orientation)
        self.orientation_combo.currentTextChanged.connect(self._orientation_combo_changed)
        self.orientation_combo.hide()
        return panel

    def _laser_panel(self) -> QWidget:
        panel = QFrame()
        layout = QGridLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(6)
        layout.setVerticalSpacing(4)
        layout.setColumnStretch(0, 1)
        self.laser_sensitive = QCheckBox("Laser Power Sensitive")
        self.laser_sensitive.setChecked(self.recipe_laser_sensitive)
        self.laser_sensitive.toggled.connect(self._laser_sensitive_changed)
        layout.addWidget(self.laser_sensitive, 0, 0, 1, 2)
        layout.addWidget(QLabel("Laser Power Factor"), 1, 0)
        unit = QLabel("J/cm²")
        unit.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(unit, 1, 1)
        self.laser_factor = QSlider(Qt.Horizontal)
        self.laser_factor.setObjectName("laserFactor")
        self.laser_factor.setRange(0, 3828)
        self.laser_factor.setValue(350)
        self.laser_factor.setStyleSheet(
            "QSlider#laserFactor::groove:horizontal {"
            " height: 4px; background: #e8e8e8; border: 1px solid #8a8a8a;"
            "}"
            "QSlider#laserFactor::handle:horizontal {"
            " width: 8px; margin: -7px 0; background: #f7f7f7; border: 1px solid #666666;"
            "}"
        )
        slider_column = QVBoxLayout()
        slider_column.setSpacing(1)
        slider_column.setContentsMargins(0, 2, 0, 0)
        slider_column.addWidget(self.laser_factor)
        red_line = QFrame()
        red_line.setFixedHeight(3)
        red_line.setStyleSheet("background: #e10600; border: none;")
        slider_column.addWidget(red_line)
        layout.addLayout(slider_column, 2, 0)
        self.laser_factor_value = QDoubleSpinBox()
        self.laser_factor_value.setDecimals(4)
        self.laser_factor_value.setRange(0.0, 0.3828)
        self.laser_factor_value.setSingleStep(0.0001)
        self.laser_factor_value.setValue(0.0350)
        self.laser_factor_value.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.UpDownArrows)
        self.laser_factor_value.setFixedWidth(78)
        self.laser_factor_value.setAlignment(Qt.AlignRight)
        layout.addWidget(self.laser_factor_value, 2, 1)
        self.laser_factor.valueChanged.connect(self._laser_factor_changed)
        self.laser_factor_value.valueChanged.connect(self._laser_factor_edited)
        layout.addWidget(QLabel("Layer and Power Limit"), 3, 0, 1, 2)
        self.layer_combo = QComboBox()
        self._refresh_layer_combo()
        layout.addWidget(self.layer_combo, 4, 0)
        layer_more = QPushButton("...")
        layer_more.setFixedWidth(30)
        layer_more.setToolTip("Edit layer database")
        layer_more.clicked.connect(self._open_layer_database)
        layout.addWidget(layer_more, 4, 1)
        return panel

    def _dark_wafer_panel(self) -> QWidget:
        panel = QFrame()
        layout = QGridLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(2)
        self.dark_wafer = QCheckBox("Dark Wafer Auto Focus Setting")
        self.dark_wafer.setChecked(False)
        self.dark_wafer.toggled.connect(self._dark_wafer_toggled)
        layout.addWidget(self.dark_wafer, 0, 0, 1, 2)
        self.dark_level_caption = QLabel("Wafer Darkness\nLevel")
        layout.addWidget(self.dark_level_caption, 1, 0, 2, 1, alignment=Qt.AlignRight | Qt.AlignVCenter)
        self.dark_level_slider = QSlider(Qt.Horizontal)
        self.dark_level_slider.setObjectName("darkLevel")
        self.dark_level_slider.setRange(0, 100)
        self.dark_level_slider.setValue(12)
        self.dark_level_slider.setStyleSheet(
            "QSlider#darkLevel::groove:horizontal { height: 4px; background: #d8d8d8; border: 1px solid #8a8a8a; }"
            "QSlider#darkLevel::handle:horizontal {"
            " width: 8px; margin: -7px 0; background: #f7f7f7; border: 1px solid #666666;"
            "}"
            "QSlider#darkLevel:disabled::groove:horizontal { background: #c8c8c8; border: 1px solid #b4b4b4; }"
            "QSlider#darkLevel:disabled::handle:horizontal { background: #d2d2d2; border: 1px solid #b4b4b4; }"
        )
        layout.addWidget(self.dark_level_slider, 1, 1)
        labels = QHBoxLayout()
        self.dark_label_dark = QLabel("Dark")
        self.dark_label_darkest = QLabel("Darkest")
        labels.addWidget(self.dark_label_dark)
        labels.addStretch(1)
        labels.addWidget(self.dark_label_darkest)
        layout.addLayout(labels, 2, 1)
        self._dark_wafer_toggled(False)
        return panel

    def _dark_wafer_toggled(self, checked: bool):
        self.dark_level_slider.setEnabled(checked)
        color = "#111111" if checked else "#9a9a9a"
        for widget in (self.dark_level_caption, self.dark_label_dark, self.dark_label_darkest):
            widget.setEnabled(checked)
            widget.setStyleSheet(f"color: {color};")

    def select_port(self, port_number: int):
        self.selected_port = port_number
        self._refresh_all()
        self._set_status(f"Port {port_number} selected.")

    def load_carrier(self, port_number: int):
        self.carrier_loaded[port_number] = True
        self.carrier_mapped[port_number] = True
        self.slot_states[port_number] = {slot: "Present" for slot in range(1, 26)}
        if self.selected_slots[port_number] is None:
            self.selected_slots[port_number] = 25
        self.select_port(port_number)
        self._set_status(f"Carrier loaded and mapped on Port {port_number}.")

    def unload_carrier(self, port_number: int):
        if self.wafer_loaded and self.wafer_source_port == port_number:
            QMessageBox.warning(
                self, "Unload Carrier",
                "Unload the wafer from the chuck before removing its carrier.",
            )
            self._set_status("Carrier unload blocked while its wafer is on the chuck.")
            return
        self.carrier_loaded[port_number] = False
        self.carrier_mapped[port_number] = False
        self.selected_slots[port_number] = None
        self.slot_states[port_number] = {slot: "Absent" for slot in range(1, 26)}
        self._refresh_all()
        self._set_status(f"Carrier unloaded from Port {port_number}.")

    def select_slot(self, port_number: int, slot: int):
        if not self.carrier_loaded[port_number]:
            self._set_status(f"Load a carrier on Port {port_number} before selecting a wafer.")
            return
        self.selected_slots[port_number] = slot
        self.select_port(port_number)
        self._set_status(f"Port {port_number}, Slot {slot} selected.")

    def _load_wafer(self):
        slot = self.selected_slots[self.selected_port]
        if not self.carrier_loaded[self.selected_port] or not self.carrier_mapped[self.selected_port] or slot is None:
            self._set_status("Select a mapped wafer before loading.")
            return False
        if self.wafer_loaded:
            self._set_status("Unload the wafer on the chuck before loading another wafer.")
            return False
        if self.slot_states[self.selected_port].get(slot) not in {"Present", "Loaded", "Aligned"}:
            self._set_status("The selected carrier slot does not contain a wafer.")
            return False
        return self._start_load_operation(align=False)

    def _load_and_align(self):
        if not self.alignment_sites_defined or self.wafer_type == "Blank":
            self._set_status("Load and Align requires a patterned recipe with defined alignment sites.")
            return
        return self._start_load_operation(align=True)

    def _start_load_operation(self, *, align: bool) -> bool:
        port = self.selected_port
        slot = self.selected_slots[port]
        if self.operation.active or self._sequence_active:
            self._set_status("A wafer operation is already in progress.")
            return False
        if self.wafer_loaded:
            self._set_status("Unload the wafer on the chuck before loading another wafer.")
            return False
        if not self.carrier_loaded[port] or not self.carrier_mapped[port] or slot is None:
            self._set_status("Select a mapped wafer before loading.")
            return False
        if self.slot_states[port].get(slot) not in {"Present", "Loaded", "Aligned"}:
            self._set_status("The selected carrier slot does not contain a wafer.")
            return False

        if self._immediate_failure():
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
            if align:
                self._prepare_simulated_alignment_image()
            final = "Aligned" if align else "Loaded"
            self.operation_status.setText(final)
            self._refresh_all()
            result = "Loaded and aligned wafer" if align else "Loaded wafer"
            self._set_status(f"{result} from Port {port}, Slot {slot}.")

        self._play_slot_animation(port, slot, phases, finish)
        return True

    def _immediate_failure(self) -> bool:
        mode = self.failure_mode.currentText() if hasattr(self, "failure_mode") else "Normal"
        if mode == "Timeout":
            self._operation_failed("Timed Out", "WH-TIMEOUT-001")
            return True
        if mode == "Transfer Exception":
            self._operation_failed("Transfer Exception", "WH-TRANSFER-001")
            return True
        return False

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

    def _operation_progress(self, state: dict):
        if not hasattr(self, "operation_status"):
            return
        if state["active"]:
            self.operation_status.setText("Loading")
        elif state["outcome"] == "Completed":
            self.operation_status.setText("Loaded")

    def _operation_active_changed(self, active: bool):
        if active:
            return
        self._refresh_all()

    def _operation_failed(self, outcome: str, error_code: str):
        self.last_transfer_outcome = outcome
        self.last_transfer_error = error_code
        self.operation_status.setText(f"{outcome}: {error_code}. Wafer state was not changed.")
        self._set_status(f"{outcome} ({error_code}); wafer transfer terminated safely.")

    def _abort_operation(self):
        self.operation.abort()

    def _close_dialog(self):
        if self._terminate_operation_for_close():
            self.accept()

    def _terminate_operation_for_close(self) -> bool:
        if self._sequence_active:
            self.finish_slot_animation()
        if not self.operation.active:
            return True
        answer = QMessageBox.question(
            self,
            "Terminate Wafer Operation",
            "A wafer operation is still running. Abort it and close Wafer Handling?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return False
        self.operation.abort()
        return True

    def closeEvent(self, event):  # noqa: N802 - Qt override
        if self._terminate_operation_for_close():
            event.accept()
        else:
            event.ignore()

    def _align_wafer(self):
        if not self.wafer_loaded:
            self._set_status("Load a wafer before alignment.")
            return
        if not self.alignment_sites_defined or self.wafer_type == "Blank":
            self._set_status("Alignment requires a patterned recipe with defined alignment sites.")
            return
        self.wafer_aligned = True
        self.slot_states[self.wafer_source_port][self.wafer_source_slot] = "Aligned"
        self._prepare_simulated_alignment_image()
        self._refresh_all()
        self._set_status("Wafer aligned. Simulated alignment image ready.")

    def _prepare_simulated_alignment_image(self):
        from ..image_display.simulated_images import ensure_simulated_alignment_images

        ensure_simulated_alignment_images()

    def _unload_wafer(self):
        if not self.wafer_loaded:
            self._set_status("No wafer is loaded.")
            return False
        if self.operation.active or self._sequence_active:
            self._set_status("A wafer operation is already in progress.")
            return False
        port = self.wafer_source_port
        slot = self.wafer_source_slot

        def finish():
            if port is not None and slot is not None:
                self.slot_states[port][slot] = "Present"
            self.wafer_loaded = False
            self.wafer_aligned = False
            self.wafer_source_port = None
            self.wafer_source_slot = None
            self.last_transfer_outcome = "Completed"
            self.last_transfer_error = ""
            self.operation_status.setText("Unloaded")
            self._refresh_all()
            self._set_status("Wafer unloaded.")

        self._play_slot_animation(port, slot, ["Unloading"], finish)
        return True

    def _play_slot_animation(self, port: int, slot: int, phases: list, finish):
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
        self.operation_status.setText(phases[0])
        self._set_status(phases[0])
        self._refresh_all()
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
            self.operation_status.setText(sequence["phases"][phase_index])
            self._set_status(sequence["phases"][phase_index])
            self._refresh_all()
        phase_elapsed = sequence["elapsed_ms"] - phase_index * self._slot_phase_ms()
        row = self.port_panels[port].slot_buttons[slot]
        row.pulse = min(1.0, phase_elapsed / 360.0)
        row.update()
        if sequence["elapsed_ms"] >= len(sequence["phases"]) * self._slot_phase_ms():
            self._sequence_timer.stop()
            self._complete_slot_animation()

    def _slot_phase_ms(self) -> int:
        return 800

    def advance_slot_animation(self):
        """Move the slot caption to the next word. Used by workflow tests."""
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
        self.operation_status.setText(phase)
        self._set_status(phase)
        sequence["elapsed_ms"] = sequence["index"] * self._slot_phase_ms()
        self._refresh_all()
        self._sequence_timer.start()

    def finish_slot_animation(self):
        """Skip the remaining slot captions and apply the finished wafer state."""
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

    def _automatic_recovery(self):
        if not self.wafer_loaded:
            self._set_status("Automatic recovery found no wafer on the chuck.")
            return
        port = self.wafer_source_port or self.selected_port
        slot = self.wafer_source_slot or self.selected_slots.get(port) or 25
        if not self.carrier_loaded.get(port):
            self.load_carrier(port)
        self.slot_states[port][slot] = "Present"
        self.wafer_loaded = False
        self.wafer_aligned = False
        self.wafer_source_port = None
        self.wafer_source_slot = None
        self._refresh_all()
        self._set_status(f"Automatic recovery returned the wafer to Port {port}, Slot {slot}.")

    def _laser_sensitive_changed(self, checked):
        if checked == self.recipe_laser_sensitive:
            return
        action = "selected" if checked else "cleared"
        QMessageBox.warning(
            self, "Laser Power Sensitive",
            f"Laser Power Sensitive was {action} for this session and differs from the active recipe.",
        )

    def _set_orientation(self, label: str):
        degrees = label.split("(")[-1].rstrip(")")
        self.orientation_combo.setCurrentText(degrees)
        self._refresh_orientation_buttons()
        self._set_status(f"Required orientation changed to {degrees} deg.")

    def _orientation_combo_changed(self, value: str):
        self._refresh_orientation_buttons()
        if hasattr(self, "_sequence"):
            for panel in self.port_panels.values():
                panel.refresh()
            self._refresh_wafer_state()
        self._set_status(f"Change Orientation option set to {value} deg.")

    def _toggle_advanced(self):
        visible = self.advanced_button.isChecked()
        self.advanced_sim_panel.setVisible(visible)
        state = "shown" if visible else "hidden"
        self._set_status(f"Advanced options {state}.")

    def _laser_factor_changed(self, value: int):
        factor = value / 10000
        if abs(self.laser_factor_value.value() - factor) > 0.00005:
            self.laser_factor_value.blockSignals(True)
            self.laser_factor_value.setValue(factor)
            self.laser_factor_value.blockSignals(False)

    def _laser_factor_edited(self, factor: float):
        factor = min(0.3828, max(0.0, float(factor)))
        slider_value = int(round(factor * 10000))
        if self.laser_factor.value() != slider_value:
            self.laser_factor.blockSignals(True)
            self.laser_factor.setValue(slider_value)
            self.laser_factor.blockSignals(False)

    def _refresh_layer_combo(self, selected_name: Optional[str] = None):
        if not hasattr(self, "layer_combo"):
            return
        current_name = selected_name or self._layer_name(self.layer_combo.currentText())
        self.layer_combo.clear()
        for layer in self.layer_types:
            self.layer_combo.addItem(
                f"{layer['name']} ({float(layer['laser_power_limit']):.4f})"
            )
        for index, layer in enumerate(self.layer_types):
            if layer["name"] == current_name:
                self.layer_combo.setCurrentIndex(index)
                break

    def _open_layer_database(self):
        selected_name = self._layer_name(self.layer_combo.currentText())
        dialog = EditLayerDatabaseDialog(self.layer_types, selected_name, self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted and dialog.result_layers:
            self.layer_types = [dict(layer) for layer in dialog.result_layers]
            self._refresh_layer_combo(dialog.selected_layer_name)
            self._set_status("Layer database updated.")

    def _show_help(self):
        QMessageBox.information(
            self,
            "Wafer Handling Help",
            "Select a port and wafer slot, then use Load, Load & Align, Align, or Unload Wafer. "
            "A source carrier cannot be removed while its wafer is on the chuck.",
        )

    def _refresh_all(self):
        for panel in self.port_panels.values():
            panel.refresh()
        self._refresh_orientation_buttons()
        self._refresh_wafer_controls()
        self._refresh_wafer_state()

    def _refresh_orientation_buttons(self):
        current = self.orientation_combo.currentText()
        for button in self.orientation_buttons:
            chosen = str(button.property("angle")) == current
            button.setChecked(chosen)
            button.mark.set_chosen(chosen)

    def _refresh_wafer_controls(self):
        active = (hasattr(self, "operation") and self.operation.active) or self._sequence_active
        has_selected_wafer = self.carrier_loaded[self.selected_port] and self.selected_slots[self.selected_port] is not None
        self.load_wafer_button.setEnabled(has_selected_wafer and not self.wafer_loaded and not active)
        can_align = self.alignment_sites_defined and self.wafer_type != "Blank"
        self.load_align_button.setEnabled(has_selected_wafer and not self.wafer_loaded and can_align and not active)
        self.align_button.setEnabled(self.wafer_loaded and can_align and not active)
        self.unload_wafer_button.setEnabled(self.wafer_loaded and not active)
        self.recovery_button.setEnabled(self.wafer_loaded and not active)
        self.failure_mode.setEnabled(not active)
        for button in self.orientation_buttons:
            button.setEnabled(not active)
        self.orientation_combo.setEnabled(not active)

    def _layer_name(self, text: str) -> str:
        for separator in ("(", "["):
            if separator in text:
                return text.split(separator)[0].strip()
        return text.strip()

    def _refresh_wafer_state(self):
        port = self.selected_port
        slot = self.selected_slots.get(port)
        slot_state = "Absent" if slot is None else self.slot_states[port].get(slot, "Absent")
        kind = wafer_thumbnail_kind(slot_state)
        angle = int(self.orientation_combo.currentText() or 0)
        self.wafer_disk.set_state(kind, angle)
        if kind in {"loaded", "aligned"}:
            rows = [
                ("Port", str(port)),
                ("Slot", str(slot)),
                ("State", "Loaded"),
                ("Alignment", "Aligned" if kind == "aligned" else "-"),
                ("Align. Angle", str(angle) if kind == "aligned" else "-"),
                ("Diameter", "300 mm"),
                ("Type", str(self.wafer_type)),
            ]
        else:
            rows = [
                ("Port", "-"),
                ("Slot", "-"),
                ("State", "Not Loaded"),
                ("Alignment", "-"),
                ("Align. Angle", "-"),
                ("Diameter", "-"),
                ("Type", "-"),
            ]
        self.wafer_state.setText(self._wafer_state_table(rows))

    def _wafer_state_table(self, rows) -> str:
        lines = ["<table cellspacing='0' cellpadding='0'>"]
        for name, value in rows:
            emphasis = "font-weight:700;" if value == "Not Loaded" else ""
            lines.append(
                f"<tr><td align='right' style='padding:0 8px 1px 0;'>{name}</td>"
                f"<td style='{emphasis}'>{value}</td></tr>"
            )
        lines.append("</table>")
        return "".join(lines)

    def _set_status(self, message: str):
        self.setWindowTitle(f"Wafer Handling - {message}")

    def _fit_within_host(self):
        screen = QApplication.primaryScreen()
        available = screen.availableGeometry() if screen else None
        parent = self.parentWidget()
        limit_w = parent.width() if parent is not None and parent.width() > 0 else 0
        limit_h = parent.height() if parent is not None and parent.height() > 0 else 0
        if available is not None:
            limit_w = min(limit_w, available.width()) if limit_w else available.width()
            limit_h = min(limit_h, available.height()) if limit_h else available.height()
        if limit_w <= 0 or limit_h <= 0:
            return
        design_w, design_h = 900, 640
        scale = min(1.0, limit_w / design_w, limit_h / design_h)
        self.setMaximumSize(limit_w, limit_h)
        self.resize(max(640, int(design_w * scale)), max(480, int(design_h * scale)))

    def showEvent(self, event):  # noqa: N802 - Qt override
        self._fit_within_host()
        super().showEvent(event)


class SlotRow(QWidget):
    """One cassette slot: number, wafer symbol, and the slot bar."""

    def __init__(self, slot: int, on_select, parent=None):
        super().__init__(parent)
        self.slot = slot
        self.on_select = on_select
        self.wafer_state = "Absent"
        self.selected = False
        self.wafer_id = ""
        self.orientation = 180
        self.pulse = 1.0
        self.setFixedHeight(16)
        self.setCursor(Qt.PointingHandCursor)

    def set_state(self, state: str, selected: bool, wafer_id: str, orientation: int = 180):
        if state != self.wafer_state:
            self.pulse = 0.0 if state in {"Loading", "Aligning", "Unloading"} else 1.0
        self.wafer_state = state
        self.selected = selected
        self.wafer_id = wafer_id
        self.orientation = int(orientation)
        self.setToolTip(
            f"Slot {self.slot}: {state}" + (f"; Wafer ID {wafer_id}" if wafer_id else "")
        )
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


class PortPanel(QFrame):
    def __init__(self, port_number: int, dialog: WaferHandlingDialog):
        super().__init__(dialog)
        self.port_number = port_number
        self.dialog = dialog
        self.slot_buttons = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        commands = QHBoxLayout()
        self.load_button = QPushButton("Load")
        self.load_button.setIcon(self._cassette_icon())
        self.load_button.clicked.connect(lambda: self.dialog.load_selected_wafer(self.port_number))
        self.unload_button = QPushButton("Unload")
        self.unload_button.setIcon(self._cassette_icon())
        self.unload_button.clicked.connect(lambda: self.dialog.unload_selected_wafer(self.port_number))
        commands.addWidget(self.load_button)
        commands.addWidget(self.unload_button)
        layout.addLayout(commands)

        self.port_tab = QPushButton(f"Port {self.port_number}")
        self.port_tab.setCheckable(True)
        self.port_tab.clicked.connect(lambda: self.dialog.select_port(self.port_number))
        layout.addWidget(self.port_tab, alignment=Qt.AlignHCenter)

        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        self.cassette_stack = MatchingStack()
        self.cassette_stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        cassette = QFrame()
        cassette.setObjectName("loadPort")
        cassette.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        cassette.setStyleSheet(
            "QFrame#loadPort { background: #d4d4d4; border-left: 5px solid #6e6e6e; "
            "border-right: 5px solid #6e6e6e; border-bottom: 8px solid #6e6e6e; }"
        )
        cassette_layout = QVBoxLayout(cassette)
        cassette_layout.setContentsMargins(6, 4, 6, 4)
        cassette_layout.setSpacing(2)
        slots_page = QWidget()
        slots_page.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        slots_layout = QVBoxLayout(slots_page)
        slots_layout.setContentsMargins(0, 0, 0, 0)
        slots_layout.setSpacing(0)
        for slot in range(25, 0, -1):
            row = SlotRow(slot, lambda value, port=self.port_number: self.dialog.select_slot(port, value))
            slots_layout.addWidget(row)
            self.slot_buttons[slot] = row
        empty = QFrame()
        empty.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        empty.setStyleSheet("background: #b9b9b9; border: none;")
        self.cassette_stack.addWidget(slots_page)
        self.cassette_stack.addWidget(empty)
        cassette_layout.addWidget(self.cassette_stack, 1)
        lamps = QHBoxLayout()
        lamps.setSpacing(6)
        lamps.addStretch(1)
        self.carrier_lamps = []
        for _ in range(2):
            lamp = QLabel()
            lamp.setFixedSize(10, 10)
            lamps.addWidget(lamp)
            self.carrier_lamps.append(lamp)
        lamps.addStretch(1)
        cassette_layout.addLayout(lamps)
        layout.addWidget(cassette, 1)

        self.carrier_state = QLabel()
        self.carrier_state.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.carrier_state.setWordWrap(True)
        self.carrier_state.setFixedHeight(64)
        layout.addWidget(self.carrier_state)

    def refresh(self):
        selected_port = self.dialog.selected_port == self.port_number
        carrier_loaded = self.dialog.carrier_loaded[self.port_number]
        selected_slot = self.dialog.selected_slots[self.port_number]
        self.port_tab.setChecked(selected_port)
        self.port_tab.setText(("▶ " if selected_port else "") + f"Port {self.port_number}")
        selected_is_loaded = (
            carrier_loaded
            and self.dialog.wafer_loaded
            and self.dialog.wafer_source_port == self.port_number
            and self.dialog.wafer_source_slot == selected_slot
        )
        busy = self.dialog._sequence_active
        mapped = carrier_loaded and bool(self.dialog.carrier_mapped[self.port_number])
        self.load_button.setEnabled(mapped and selected_slot is not None and not busy and not self.dialog.wafer_loaded)
        self.unload_button.setEnabled(selected_is_loaded and not busy)
        self.cassette_stack.setCurrentIndex(0 if mapped else 1)
        self.carrier_lamps[0].setStyleSheet(_lamp_style(carrier_loaded))
        self.carrier_lamps[1].setStyleSheet(_lamp_style(mapped))
        for slot, row in self.slot_buttons.items():
            row.setEnabled(carrier_loaded)
            state = self.dialog.slot_states[self.port_number].get(slot, "Absent")
            wafer_id = self.dialog.wafer_ids[self.port_number].get(slot, "")
            row.set_state(
                state,
                carrier_loaded and selected_slot == slot,
                wafer_id,
                int(self.dialog.orientation_combo.currentText() or 0),
            )
        if carrier_loaded and mapped:
            carrier_state = "Mapped"
            port_state = "Carrier Present & Unclamped"
            transfer = "Carrier Allocated to Equipment"
        elif carrier_loaded:
            carrier_state = "Present"
            port_state = "Carrier Present & Unclamped"
            transfer = "Ready to Load"
        else:
            carrier_state = "No Cassette"
            port_state = "Ready to Load"
            transfer = "Ready to Load"
        self.carrier_state.setText(
            f"Carrier State   {carrier_state}\n"
            f"Port State      {port_state}\n"
            f"Transfer State  {transfer}\n"
            "Port Size       300 mm"
        )

    def _cassette_icon(self) -> QIcon:
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setPen(QPen(QColor("#8a3e00"), 1))
        painter.setBrush(QColor("#e36c12"))
        painter.drawRoundedRect(1, 1, 14, 14, 2, 2)
        painter.end()
        return QIcon(pixmap)

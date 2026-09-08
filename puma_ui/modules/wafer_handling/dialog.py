from __future__ import annotations

from typing import Dict, Optional

from ...qt_compat import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStyle,
    Qt,
    QVBoxLayout,
    QWidget,
)
from ...widgets import StatusDot, WaferDisk
from ..wafer_properties.dialogs import DEFAULT_WAFER_PROPERTIES, EditLayerDatabaseDialog


class WaferHandlingDialog(QDialog):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        selected_port: int = 1,
        state: Optional[dict] = None,
        recipe: Optional[dict] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Wafer Handling")
        self.resize(900, 720)
        self.setMinimumSize(820, 640)
        self.selected_port = selected_port
        self.carrier_loaded = {1: True, 2: False}
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
            self.carrier_loaded.update(
                {int(key): bool(value) for key, value in state.get("carrier_loaded", {}).items()}
            )
            self.selected_slots.update(
                {int(key): value for key, value in state.get("selected_slots", {}).items()}
            )
            self.wafer_loaded = bool(state.get("wafer_loaded", False))
            self.wafer_aligned = bool(state.get("wafer_aligned", False)) and self.wafer_loaded
            for port, slots in (state.get("slot_states") or {}).items():
                self.slot_states[int(port)].update({int(slot): value for slot, value in slots.items()})
            for port, identifiers in (state.get("wafer_ids") or {}).items():
                self.wafer_ids[int(port)].update({int(slot): value for slot, value in identifiers.items()})
            self.wafer_source_port = state.get("wafer_source_port")
            self.wafer_source_slot = state.get("wafer_source_slot")
        runtime_state = state or {}
        self.read_wafer_id = bool(runtime_state.get("read_wafer_id", False))
        self.required_orientation = str(runtime_state.get("required_orientation", "180"))
        self._build_ui()
        self._refresh_all()

    def result_state(self) -> dict:
        return {
            "selected_port": self.selected_port,
            "carrier_loaded": dict(self.carrier_loaded),
            "selected_slots": dict(self.selected_slots),
            "slot_states": {port: dict(slots) for port, slots in self.slot_states.items()},
            "wafer_ids": {port: dict(values) for port, values in self.wafer_ids.items()},
            "wafer_loaded": self.wafer_loaded,
            "wafer_aligned": self.wafer_aligned,
            "wafer_source_port": self.wafer_source_port,
            "wafer_source_slot": self.wafer_source_slot,
            "read_wafer_id": self.read_wafer_id,
            "required_orientation": self.orientation_combo.currentText(),
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
            QComboBox, QLineEdit, QSpinBox {
                background: #ffffff;
                border: 1px solid #77736b;
                min-height: 24px;
            }
            """
        )

        main = QVBoxLayout(self)
        main.setContentsMargins(10, 10, 10, 10)
        main.setSpacing(8)

        content = QHBoxLayout()
        content.setSpacing(12)
        self.port_panels: Dict[int, PortPanel] = {}
        for port_number in [1, 2]:
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
        close.clicked.connect(self.accept)
        footer.addWidget(close)
        footer.addStretch(1)
        self.advanced_button = QPushButton("Advanced")
        self.advanced_button.setCheckable(True)
        self.advanced_button.clicked.connect(self._toggle_advanced)
        footer.addWidget(self.advanced_button)
        main.addLayout(footer)

    def _right_controls(self) -> QWidget:
        panel = QFrame()
        panel.setFixedWidth(260)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self._wafer_operations())
        layout.addWidget(self._wafer_state_panel())
        layout.addWidget(self._orientation_panel())
        self.advanced_laser_panel = self._laser_panel()
        self.advanced_dark_panel = self._dark_wafer_panel()
        self.advanced_laser_panel.setVisible(False)
        self.advanced_dark_panel.setVisible(False)
        layout.addWidget(self.advanced_laser_panel)
        layout.addWidget(self.advanced_dark_panel)
        layout.addStretch(1)
        return panel

    def _wafer_operations(self) -> QWidget:
        group = QFrame()
        group.setStyleSheet("QFrame { border: 1px solid #8f8b82; }")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(7)
        title = QLabel("Wafer Operations")
        title.setProperty("section", True)
        layout.addWidget(title)

        row = QHBoxLayout()
        self.load_wafer_button = QPushButton("Load")
        self.load_wafer_button.setIcon(self.style().standardIcon(QStyle.SP_DialogOpenButton))
        self.load_wafer_button.clicked.connect(self._load_wafer)
        self.load_align_button = QPushButton("Load &&\nAlign")
        self.load_align_button.setIcon(self.style().standardIcon(QStyle.SP_DialogApplyButton))
        self.load_align_button.clicked.connect(self._load_and_align)
        self.align_button = QPushButton("Align")
        self.align_button.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        self.align_button.clicked.connect(self._align_wafer)
        row.addWidget(self.load_wafer_button)
        row.addWidget(self.load_align_button)
        row.addWidget(self.align_button)
        layout.addLayout(row)

        self.unload_wafer_button = QPushButton("Unload Wafer")
        self.unload_wafer_button.setIcon(self.style().standardIcon(QStyle.SP_DialogResetButton))
        self.unload_wafer_button.clicked.connect(self._unload_wafer)
        layout.addWidget(self.unload_wafer_button)

        self.read_id_check = QCheckBox("Read Wafer ID during prealignment")
        self.read_id_check.setChecked(self.read_wafer_id)
        self.read_id_check.toggled.connect(lambda checked: setattr(self, "read_wafer_id", checked))
        layout.addWidget(self.read_id_check)

        self.recovery_button = QPushButton("Automatic Recovery")
        self.recovery_button.setIcon(self.style().standardIcon(QStyle.SP_MessageBoxCritical))
        self.recovery_button.clicked.connect(self._automatic_recovery)
        layout.addWidget(self.recovery_button)
        return group

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
        row.setSpacing(8)
        self.orientation_buttons = []
        for label in ["Up\n(0)", "Right\n(90)", "Down\n(180)", "Left\n(270)"]:
            button = QPushButton(label)
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, value=label: self._set_orientation(value))
            row.addWidget(button)
            self.orientation_buttons.append(button)
        layout.addLayout(row)
        change = QHBoxLayout()
        change.addWidget(QLabel("Change Orientation:"))
        self.orientation_combo = QComboBox()
        self.orientation_combo.addItems(["0", "90", "180", "270"])
        self.orientation_combo.setCurrentText(self.required_orientation)
        self.orientation_combo.currentTextChanged.connect(self._orientation_combo_changed)
        change.addWidget(self.orientation_combo)
        layout.addLayout(change)
        return panel

    def _laser_panel(self) -> QWidget:
        panel = QFrame()
        layout = QGridLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(6)
        layout.setVerticalSpacing(4)
        self.laser_sensitive = QCheckBox("Laser Power Sensitive")
        self.laser_sensitive.setChecked(self.recipe_laser_sensitive)
        self.laser_sensitive.toggled.connect(self._laser_sensitive_changed)
        layout.addWidget(self.laser_sensitive, 0, 0, 1, 3)
        layout.addWidget(QLabel("Laser Power Factor"), 1, 0, 1, 2)
        layout.addWidget(QLabel("J/cm^2"), 1, 2)
        red_bar = QFrame()
        red_bar.setFixedHeight(10)
        red_bar.setStyleSheet("background: #ed1c24; border: 1px solid #777777;")
        layout.addWidget(red_bar, 2, 0, 1, 2)
        self.laser_factor = QSpinBox()
        self.laser_factor.setRange(0, 3828)
        self.laser_factor.setValue(35)
        layout.addWidget(self.laser_factor, 2, 2)
        layout.addWidget(QLabel("Layer and Power Limit"), 3, 0, 1, 3)
        self.layer_combo = QComboBox()
        self._refresh_layer_combo()
        layout.addWidget(self.layer_combo, 4, 0, 1, 2)
        layer_more = QPushButton("...")
        layer_more.setFixedWidth(30)
        layer_more.setToolTip("Edit layer database")
        layer_more.clicked.connect(self._open_layer_database)
        layout.addWidget(layer_more, 4, 2)
        return panel

    def _dark_wafer_panel(self) -> QWidget:
        panel = QFrame()
        layout = QGridLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        self.dark_wafer = QCheckBox("Dark Wafer Auto Focus Setting")
        layout.addWidget(self.dark_wafer, 0, 0, 1, 3)
        layout.addWidget(QLabel("Wafer Darkness\nLevel"), 1, 0)
        self.dark_level = QComboBox()
        self.dark_level.addItems(["Dark", "Darkest"])
        layout.addWidget(self.dark_level, 1, 1, 1, 2)
        return panel

    def select_port(self, port_number: int):
        self.selected_port = port_number
        self._refresh_all()
        self._set_status(f"Port {port_number} selected.")

    def load_carrier(self, port_number: int):
        self.carrier_loaded[port_number] = True
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
        if not self.carrier_loaded[self.selected_port] or slot is None:
            self._set_status("Select a mapped wafer before loading.")
            return False
        if self.wafer_loaded:
            self._set_status("Unload the wafer on the chuck before loading another wafer.")
            return False
        if self.slot_states[self.selected_port].get(slot) not in {"Present", "Loaded", "Aligned"}:
            self._set_status("The selected carrier slot does not contain a wafer.")
            return False
        self.wafer_loaded = True
        self.wafer_aligned = False
        self.wafer_source_port = self.selected_port
        self.wafer_source_slot = slot
        self.slot_states[self.selected_port][slot] = "Loaded"
        if self.read_wafer_id:
            self.wafer_ids[self.selected_port][slot] = f"W{self.selected_port}-{slot:02d}"
        self._refresh_all()
        self._set_status(f"Loaded wafer from Port {self.selected_port}, Slot {slot}.")
        return True

    def _load_and_align(self):
        if not self.alignment_sites_defined or self.wafer_type == "Blank":
            self._set_status("Load and Align requires a patterned recipe with defined alignment sites.")
            return
        if self._load_wafer():
            self.wafer_aligned = True
            self.slot_states[self.wafer_source_port][self.wafer_source_slot] = "Aligned"
            self._refresh_all()
            self._set_status("Loaded and aligned wafer.")

    def _align_wafer(self):
        if not self.wafer_loaded:
            self._set_status("Load a wafer before alignment.")
            return
        if not self.alignment_sites_defined or self.wafer_type == "Blank":
            self._set_status("Alignment requires a patterned recipe with defined alignment sites.")
            return
        self.wafer_aligned = True
        self.slot_states[self.wafer_source_port][self.wafer_source_slot] = "Aligned"
        self._refresh_all()
        self._set_status("Wafer aligned.")

    def _unload_wafer(self):
        if self.wafer_source_port is not None and self.wafer_source_slot is not None:
            self.slot_states[self.wafer_source_port][self.wafer_source_slot] = "Present"
        self.wafer_loaded = False
        self.wafer_aligned = False
        self.wafer_source_port = None
        self.wafer_source_slot = None
        self._refresh_all()
        self._set_status("Wafer unloaded.")

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
        self._set_status(f"Change Orientation option set to {value} deg.")

    def _toggle_advanced(self):
        visible = self.advanced_button.isChecked()
        self.advanced_laser_panel.setVisible(visible)
        self.advanced_dark_panel.setVisible(visible)
        state = "shown" if visible else "hidden"
        self._set_status(f"Advanced options {state}.")

    def _refresh_layer_combo(self, selected_name: Optional[str] = None):
        if not hasattr(self, "layer_combo"):
            return
        current_name = selected_name or self.layer_combo.currentText().split("[")[0].strip()
        self.layer_combo.clear()
        for layer in self.layer_types:
            self.layer_combo.addItem(
                f"{layer['name']} [{float(layer['laser_power_limit']):.4f}]"
            )
        for index, layer in enumerate(self.layer_types):
            if layer["name"] == current_name:
                self.layer_combo.setCurrentIndex(index)
                break

    def _open_layer_database(self):
        selected_name = self.layer_combo.currentText().split("[")[0].strip()
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
            button.setChecked(f"({current})" in button.text())

    def _refresh_wafer_controls(self):
        has_selected_wafer = self.carrier_loaded[self.selected_port] and self.selected_slots[self.selected_port] is not None
        self.load_wafer_button.setEnabled(has_selected_wafer and not self.wafer_loaded)
        can_align = self.alignment_sites_defined and self.wafer_type != "Blank"
        self.load_align_button.setEnabled(has_selected_wafer and not self.wafer_loaded and can_align)
        self.align_button.setEnabled(self.wafer_loaded and can_align)
        self.unload_wafer_button.setEnabled(self.wafer_loaded)
        self.recovery_button.setEnabled(self.wafer_loaded)

    def _refresh_wafer_state(self):
        slot = self.selected_slots[self.selected_port]
        state = "Loaded" if self.wafer_loaded else "Not Loaded"
        alignment = "Aligned" if self.wafer_aligned else "-"
        self.wafer_state.setText(
            f"Port    {self.selected_port}\n"
            f"Slot    {slot if slot is not None else '-'}\n"
            f"State   {state}\n"
            f"Alignment   {alignment}\n"
            f"Align. Angle   {self.orientation_combo.currentText()} deg\n"
            "Diameter   300 mm\n"
            f"Type   {self.wafer_type}"
        )

    def _set_status(self, message: str):
        self.setWindowTitle(f"Wafer Handling - {message}")


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
        self.load_button.setIcon(self.style().standardIcon(QStyle.SP_DialogOpenButton))
        self.load_button.clicked.connect(lambda: self.dialog.load_carrier(self.port_number))
        self.unload_button = QPushButton("Unload")
        self.unload_button.setIcon(self.style().standardIcon(QStyle.SP_TrashIcon))
        self.unload_button.clicked.connect(lambda: self.dialog.unload_carrier(self.port_number))
        commands.addWidget(self.load_button)
        commands.addWidget(self.unload_button)
        layout.addLayout(commands)

        self.port_tab = QPushButton(f"Port {self.port_number}")
        self.port_tab.setCheckable(True)
        self.port_tab.clicked.connect(lambda: self.dialog.select_port(self.port_number))
        layout.addWidget(self.port_tab, alignment=Qt.AlignHCenter)

        cassette = QFrame()
        cassette.setObjectName("loadPort")
        cassette_layout = QGridLayout(cassette)
        cassette_layout.setContentsMargins(6, 6, 6, 6)
        cassette_layout.setHorizontalSpacing(4)
        cassette_layout.setVerticalSpacing(2)
        for visual_row, slot in enumerate(range(25, 0, -1)):
            label = QLabel(str(slot))
            label.setFixedWidth(18)
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            button = QPushButton("")
            button.setCheckable(True)
            button.setFixedHeight(18)
            button.clicked.connect(lambda checked=False, value=slot: self.dialog.select_slot(self.port_number, value))
            cassette_layout.addWidget(label, visual_row, 0)
            cassette_layout.addWidget(button, visual_row, 1)
            self.slot_buttons[slot] = button
        layout.addWidget(cassette, 1)

        self.carrier_state = QLabel()
        self.carrier_state.setAlignment(Qt.AlignHCenter)
        layout.addWidget(self.carrier_state)

    def refresh(self):
        selected_port = self.dialog.selected_port == self.port_number
        carrier_loaded = self.dialog.carrier_loaded[self.port_number]
        selected_slot = self.dialog.selected_slots[self.port_number]
        self.port_tab.setChecked(selected_port)
        self.unload_button.setEnabled(carrier_loaded)
        for slot, button in self.slot_buttons.items():
            button.setEnabled(carrier_loaded)
            button.setChecked(carrier_loaded and selected_slot == slot)
            state = self.dialog.slot_states[self.port_number].get(slot, "Absent")
            marker = {"Absent": "", "Present": "o", "Loaded": "L", "Aligned": "A"}.get(state, "o")
            wafer_id = self.dialog.wafer_ids[self.port_number].get(slot, "")
            button.setText(f"{marker}  {wafer_id}".rstrip())
            button.setToolTip(f"Slot {slot}: {state}" + (f"; Wafer ID {wafer_id}" if wafer_id else ""))
        carrier_state = "Carrier Present" if carrier_loaded else "No Cassette"
        port_state = "Carrier Allocated" if carrier_loaded else "Ready to Load"
        transfer = "Ready to Unload" if carrier_loaded else "Ready to Load"
        self.carrier_state.setText(
            f"Carrier State   {carrier_state}\n"
            f"Port State      {port_state}\n"
            f"Transfer        {transfer}\n"
            "Port Size       300 mm"
        )

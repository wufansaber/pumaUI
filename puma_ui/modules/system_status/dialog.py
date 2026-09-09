from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ...qt_compat import (
    QAbstractItemView,
    QCheckBox,
    QColor,
    QComboBox,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    Qt,
    QVBoxLayout,
    QWidget,
)


class ErrorMessageDialog(QDialog):
    """Manual 2.4.7 error surface with a real Daily Log text export."""

    def __init__(self, message="System error", related_data="", log_directory=None, parent=None):
        super().__init__(parent)
        self.message = str(message)
        self.related_data = str(related_data)
        self.log_directory = Path(log_directory or Path.cwd() / "runtime" / "Daily Logs")
        self.saved_path = None
        self.setWindowTitle("System Error Message")
        self.resize(620, 390)
        root = QVBoxLayout(self)
        heading = QLabel("A system error has occurred")
        heading.setStyleSheet("font-weight: 700; color: #9a1b1b;")
        root.addWidget(heading)
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setPlainText(
            f"Error Message\n{self.message}\n\nRelated Data\n{self.related_data or 'No related data supplied.'}"
        )
        root.addWidget(self.details, 1)
        self.path_label = QLabel(f"Daily Log directory: {self.log_directory}")
        self.path_label.setWordWrap(True)
        root.addWidget(self.path_label)
        buttons = QHBoxLayout()
        self.save_button = QPushButton("Write to Daily Log")
        self.save_button.clicked.connect(self._write_daily_log)
        buttons.addWidget(self.save_button)
        buttons.addStretch(1)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        buttons.addWidget(close)
        root.addLayout(buttons)

    def _write_daily_log(self):
        self.log_directory.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now()
        path = self.log_directory / f"ErrMsgDlg_{timestamp:%H%M%S_%f}.txt"
        payload = (
            f"Timestamp: {timestamp:%Y-%m-%d %H:%M:%S}\n"
            f"Error Message: {self.message}\n"
            f"Related Data:\n{self.related_data or 'No related data supplied.'}\n"
        )
        path.write_text(payload, encoding="utf-8")
        self.saved_path = path
        self.path_label.setText(f"Saved Daily Log: {path}")
        self.save_button.setEnabled(False)


class E84RealTimeSignalDialog(QDialog):
    """Simulator representation of the optional E84 real-time signal monitor."""

    SIGNALS = ("VALID", "CS_0", "CS_1", "TR_REQ", "BUSY", "COMPT", "CONT", "HO_AVBL", "ES")
    HANDOFF_STEPS = (
        ("Idle", set()),
        ("Carrier Valid", {"VALID", "CS_0", "HO_AVBL", "ES"}),
        ("Transfer Requested", {"VALID", "CS_0", "TR_REQ", "HO_AVBL", "ES"}),
        ("Busy", {"VALID", "CS_0", "BUSY", "HO_AVBL", "ES"}),
        ("Complete", {"VALID", "CS_0", "COMPT", "HO_AVBL", "ES"}),
    )

    def __init__(self, enabled=False, parent=None):
        super().__init__(parent)
        self.sequence_index = 0
        self.setWindowTitle("E84 Real Time Signal State Display")
        self.resize(760, 460)
        root = QVBoxLayout(self)
        header = QHBoxLayout()
        self.enabled = QCheckBox("E84 communication enabled")
        self.enabled.setChecked(bool(enabled))
        self.enabled.toggled.connect(self._refresh)
        header.addWidget(self.enabled)
        header.addStretch(1)
        self.phase_label = QLabel()
        self.phase_label.setStyleSheet("font-weight: 700;")
        header.addWidget(self.phase_label)
        root.addLayout(header)

        self.signal_table = QTableWidget(len(self.SIGNALS), 3)
        self.signal_table.setHorizontalHeaderLabels(["E84 Signal", "Load Port 1", "Load Port 2"])
        self.signal_table.verticalHeader().setVisible(False)
        self.signal_table.horizontalHeader().setStretchLastSection(True)
        for row, signal in enumerate(self.SIGNALS):
            self.signal_table.setItem(row, 0, QTableWidgetItem(signal))
            self.signal_table.setItem(row, 1, QTableWidgetItem("OFF"))
            self.signal_table.setItem(row, 2, QTableWidgetItem("OFF"))
        root.addWidget(self.signal_table, 1)

        note = QLabel(
            "Training simulator: signal transitions are deterministic and do not control a physical E84 interface."
        )
        note.setWordWrap(True)
        root.addWidget(note)
        buttons = QHBoxLayout()
        self.next_button = QPushButton("Next Handoff State")
        self.next_button.clicked.connect(self._next_state)
        buttons.addWidget(self.next_button)
        reset = QPushButton("Reset")
        reset.clicked.connect(self._reset)
        buttons.addWidget(reset)
        buttons.addStretch(1)
        minimize = QPushButton("Minimize")
        minimize.clicked.connect(self.showMinimized)
        buttons.addWidget(minimize)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        buttons.addWidget(close)
        root.addLayout(buttons)
        self._refresh()

    def _next_state(self):
        if not self.enabled.isChecked():
            QMessageBox.information(self, "E84", "Enable E84 communication before simulating a handoff.")
            return
        self.sequence_index = (self.sequence_index + 1) % len(self.HANDOFF_STEPS)
        self._refresh()

    def _reset(self):
        self.sequence_index = 0
        self._refresh()

    def _refresh(self):
        active = self.HANDOFF_STEPS[self.sequence_index][1] if self.enabled.isChecked() else set()
        phase = self.HANDOFF_STEPS[self.sequence_index][0] if self.enabled.isChecked() else "E84 Disabled"
        self.phase_label.setText(phase)
        self.next_button.setEnabled(self.enabled.isChecked())
        for row, signal in enumerate(self.SIGNALS):
            for column in (1, 2):
                item = self.signal_table.item(row, column)
                item.setText("ON" if signal in active else "OFF")
                item.setBackground(QColor("#a8e6a3") if signal in active else QColor("#e4e1d8"))


DEFAULT_COMMUNICATION_STATUS = {
    "control_mode": "Local",
    "secs_enabled": True,
    "secs_connected": True,
    "secs_host": "127.0.0.1",
    "secs_port": 5000,
    "ilink_enabled": False,
    "ilink_connected": True,
    "ilink_host": "127.0.0.1",
    "ilink_port": 6000,
}

DEFAULT_EQUIPMENT_CONSTANTS = {
    "initial_e10_state": "Non-Scheduled",
    "e58_startup": False,
    "e58_shutdown": False,
    "device_name": "Puma9980",
    "time_format": "YYYYMMDDHHMMSSCC",
    "signal_tower_control": "Equipment Control",
    "report_step_id": False,
    "host_manages_recipes": False,
    "poll_delay": 25,
    "communication_timeout": 25,
    "wait_for_job": True,
    "auto_start": True,
    "confirm_start": False,
    "check_cassette_map": False,
    "auto_unload": False,
    "operator_load_read_wafer_id": False,
    "production_read_wafer_id": False,
    "continue_on_wafer_id_failure": False,
    "report_type": "Normal",
    "initial_control_state": "Online",
    "initial_online_substate": "Local",
    "spooling": False,
    "remote_job_commands": True,
    "remote_wafer_handling": True,
    "remote_carrier_management": True,
    "remote_clear_alarms": True,
    "remote_recipe_transfer": True,
}

DEFAULT_DATA_TRANSFER = {
    "running": True,
    "protocol": "ILink",
    "analysis_system": "AnalysisSystem1",
    "host": "127.0.0.1",
    "port": 6000,
    "automatic_retry": True,
}


def normalized_equipment_constants(value=None):
    result = {**DEFAULT_EQUIPMENT_CONSTANTS, **(value if isinstance(value, dict) else {})}
    result["poll_delay"] = max(15, min(30, int(result.get("poll_delay", 25))))
    result["communication_timeout"] = max(15, min(30, int(result.get("communication_timeout", 25))))
    for key, default in DEFAULT_EQUIPMENT_CONSTANTS.items():
        if isinstance(default, bool):
            result[key] = bool(result.get(key))
    return result


def normalized_data_transfer(value=None):
    result = {**DEFAULT_DATA_TRANSFER, **(value if isinstance(value, dict) else {})}
    result["running"] = bool(result.get("running", True))
    result["automatic_retry"] = bool(result.get("automatic_retry", True))
    result["port"] = max(1, min(65535, int(result.get("port", 6000))))
    result["protocol"] = str(result.get("protocol", "ILink")) or "ILink"
    result["analysis_system"] = str(result.get("analysis_system", "AnalysisSystem1")) or "AnalysisSystem1"
    result["host"] = str(result.get("host", "127.0.0.1")) or "127.0.0.1"
    return result


def normalized_data_transfer(value=None):
    result = {**DEFAULT_DATA_TRANSFER, **(value if isinstance(value, dict) else {})}
    result["running"] = bool(result.get("running"))
    result["automatic_retry"] = bool(result.get("automatic_retry"))
    result["port"] = max(1, min(65535, int(result.get("port", 6000))))
    return result


def normalized_communication_status(value=None):
    result = {**DEFAULT_COMMUNICATION_STATUS, **(value if isinstance(value, dict) else {})}
    result["control_mode"] = "Remote" if result.get("control_mode") == "Remote" else "Local"
    result["secs_enabled"] = bool(result.get("secs_enabled"))
    result["ilink_enabled"] = bool(result.get("ilink_enabled"))
    result["secs_connected"] = bool(result.get("secs_connected", True))
    result["ilink_connected"] = bool(result.get("ilink_connected", True))
    result["secs_port"] = max(1, min(65535, int(result.get("secs_port", 5000))))
    result["ilink_port"] = max(1, min(65535, int(result.get("ilink_port", 6000))))
    return result


class CommunicationStatusDialog(QDialog):
    def __init__(self, state=None, parent=None):
        super().__init__(parent)
        self.state = normalized_communication_status(state)
        self.result_status = None
        self.setWindowTitle("SECS / ILink Status and Configuration")
        self.resize(620, 390)
        root = QVBoxLayout(self)
        title = QLabel("SECS / ILink Communication")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        root.addWidget(title)
        note = QLabel(
            "Simulation status only. No inspection tool, factory host, or analysis database connection is opened."
        )
        note.setWordWrap(True)
        root.addWidget(note)
        form = QGridLayout()
        self.control_mode = QComboBox()
        self.control_mode.addItems(["Local", "Remote"])
        self.control_mode.setCurrentText(self.state["control_mode"])
        self.secs_enabled = QCheckBox("Enable ISECS host communication")
        self.secs_enabled.setChecked(self.state["secs_enabled"])
        self.secs_connected = QCheckBox("Host connection available")
        self.secs_connected.setChecked(self.state["secs_connected"])
        self.secs_host = QLineEdit(str(self.state["secs_host"]))
        self.secs_port = QSpinBox()
        self.secs_port.setRange(1, 65535)
        self.secs_port.setValue(self.state["secs_port"])
        self.ilink_enabled = QCheckBox("Enable ILink analysis-system transfer")
        self.ilink_enabled.setChecked(self.state["ilink_enabled"])
        self.ilink_connected = QCheckBox("Analysis-system connection available")
        self.ilink_connected.setChecked(self.state["ilink_connected"])
        self.ilink_host = QLineEdit(str(self.state["ilink_host"]))
        self.ilink_port = QSpinBox()
        self.ilink_port.setRange(1, 65535)
        self.ilink_port.setValue(self.state["ilink_port"])
        rows = (
            ("Control Mode", self.control_mode),
            ("SECS", self.secs_enabled),
            ("SECS Connection", self.secs_connected),
            ("SECS Host", self.secs_host),
            ("SECS Port", self.secs_port),
            ("ILink", self.ilink_enabled),
            ("ILink Connection", self.ilink_connected),
            ("ILink Host", self.ilink_host),
            ("ILink Port", self.ilink_port),
        )
        for row, (label, control) in enumerate(rows):
            form.addWidget(QLabel(label), row, 0)
            form.addWidget(control, row, 1)
        form.setColumnStretch(1, 1)
        root.addLayout(form)
        self.status = QLabel()
        self.status.setStyleSheet("font-weight: bold;")
        root.addWidget(self.status)
        self.control_mode.currentTextChanged.connect(self._refresh)
        self.secs_enabled.toggled.connect(self._refresh)
        self.ilink_enabled.toggled.connect(self._refresh)
        self.secs_connected.toggled.connect(self._refresh)
        self.ilink_connected.toggled.connect(self._refresh)
        self._refresh()
        footer = QHBoxLayout()
        defaults = QPushButton("Default")
        defaults.clicked.connect(self._defaults)
        footer.addWidget(defaults)
        footer.addStretch(1)
        apply = QPushButton("Apply")
        apply.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        footer.addWidget(apply)
        footer.addWidget(cancel)
        root.addLayout(footer)

    def _refresh(self, *_args):
        remote_valid = self.control_mode.currentText() == "Local" or self.secs_enabled.isChecked()
        self.secs_connected.setEnabled(self.secs_enabled.isChecked())
        self.ilink_connected.setEnabled(self.ilink_enabled.isChecked())
        secs_state = "Disabled"
        if self.secs_enabled.isChecked():
            secs_state = "Online (simulated)" if self.secs_connected.isChecked() else "Disconnected"
        ilink_state = "Shutdown"
        if self.ilink_enabled.isChecked():
            ilink_state = "Ready (simulated)" if self.ilink_connected.isChecked() else "Transfer Failure"
        self.status.setText(
            f"Control: {self.control_mode.currentText()} | "
            f"SECS: {secs_state} | ILink: {ilink_state}"
        )
        self.status.setStyleSheet(f"font-weight: bold; color: {'#176b2c' if remote_valid else '#a41515'};")

    def _defaults(self):
        defaults = DEFAULT_COMMUNICATION_STATUS
        self.control_mode.setCurrentText(defaults["control_mode"])
        self.secs_enabled.setChecked(defaults["secs_enabled"])
        self.secs_connected.setChecked(defaults["secs_connected"])
        self.secs_host.setText(defaults["secs_host"])
        self.secs_port.setValue(defaults["secs_port"])
        self.ilink_enabled.setChecked(defaults["ilink_enabled"])
        self.ilink_connected.setChecked(defaults["ilink_connected"])
        self.ilink_host.setText(defaults["ilink_host"])
        self.ilink_port.setValue(defaults["ilink_port"])

    def _finish(self):
        if self.control_mode.currentText() == "Remote" and not self.secs_enabled.isChecked():
            QMessageBox.warning(self, "SECS Communication", "Remote control requires SECS communication to be enabled.")
            return
        if self.secs_enabled.isChecked() and not self.secs_host.text().strip():
            QMessageBox.warning(self, "SECS Communication", "SECS Host is required when communication is enabled.")
            return
        if self.ilink_enabled.isChecked() and not self.ilink_host.text().strip():
            QMessageBox.warning(self, "ILink Communication", "ILink Host is required when transfer is enabled.")
            return
        self.result_status = normalized_communication_status({
            "control_mode": self.control_mode.currentText(),
            "secs_enabled": self.secs_enabled.isChecked(),
            "secs_connected": self.secs_connected.isChecked(),
            "secs_host": self.secs_host.text().strip(),
            "secs_port": self.secs_port.value(),
            "ilink_enabled": self.ilink_enabled.isChecked(),
            "ilink_connected": self.ilink_connected.isChecked(),
            "ilink_host": self.ilink_host.text().strip(),
            "ilink_port": self.ilink_port.value(),
        })
        self.accept()


SAFETY_INTERLOCKS = (
    ("Stage Interlock", "The stage safety interlock is active.", "Close all access panels and initialize the Stage subsystem."),
    ("Lamp Power Interlock", "The lamp/laser power interlock is active.", "Install the laser cover, perform the hardware reset, and initialize Optics."),
    ("Robot Interlock", "The robot safety interlock is active.", "Close all robot panels and initialize the Wafer Handler subsystem."),
)

CLEARABLE_SECS_ALARMS = (
    "Transfer Error Alarm",
    "Access Mode Violation",
    "Carrier ID Read/Write Alarm",
    "Carrier ID Verification Alarm",
    "Slot Map Read Alarm",
    "Slot Map Verification Alarm",
    "Out of Service Alarm",
    "Port Operational Alarm",
    "Carrier Open Failure Alarm",
    "Carrier Close Failure Alarm",
    "Light Curtain Violation Alarm",
    "Wafer Handler Mini Environment Low Pressure Alarm",
    "Wafer Handler Mini Environment High Pressure Alarm",
    "Wafer Handler Ionizer Alarm",
    "Clearable Wafer Handler Alarm",
    "Process Job Inspection Alarm",
    "Pressure Sensor Alarm",
    "Temperature Sensor Alarm",
    "CMS Parameter Out of Range Alarm",
    "Substrate Destination Not Accessible Alarm",
    "Tool Error Reporting - Unknown",
    "Clearable Alarm",
    "Stop Tool - Reset",
    "Stop Tool - Service",
    "Data Integrity Issue",
    "Pause Tool",
)

NONCLEARABLE_SECS_ALARMS = (
    "Carrier Presence/Placement Alarm",
    "Crooked Wafers Alarm",
    "Double-Slotted Wafers Alarm",
    "Duplicate Carrier ID Alarm",
    "Wafer Protrusion Interlock Alarm",
    "Service Mode Alarm",
    "Stranded Wafer Alarm",
    "Non-Clearable Wafer Handler Alarm",
    "Wafer Handler Polling Exception Alarm",
    "Mini Environment Hardware Present But Configuration Disabled Alarm",
    "Chiller Alarm",
    "Laser Site Change Error",
    "No Laser Site Left",
    "Light Level Checking Alarm",
    "Secondary Purge Pressure Alarm",
)

ALARM_DETAILS = {
    "Transfer Error Alarm": ("An E84 transfer error occurred at a load port.", "Reset the Wafer Handler or issue Clear Alarms."),
    "Access Mode Violation": ("Manual delivery was attempted while the port was in Auto Access mode.", "Complete or cancel carrier service, unload the carrier, or issue Clear Alarms."),
    "Slot Map Read Alarm": ("The carrier slot map could not be read.", "Read the slot map successfully, remove the carrier, or issue Clear Alarms."),
    "Slot Map Verification Alarm": ("The carrier slot map failed verification.", "Reset the Wafer Handler or issue Clear Alarms."),
    "Pressure Sensor Alarm": ("A pressure sensor is outside its allowed range; inspection may continue with focus drift.", "Contact service support."),
    "Temperature Sensor Alarm": ("A temperature sensor is outside its allowed range; inspection may continue with focus drift.", "Contact service support."),
    "Carrier Presence/Placement Alarm": ("A carrier is present but is not placed correctly.", "Place the carrier correctly or remove it."),
    "Crooked Wafers Alarm": ("A wafer is crossed or otherwise mapped incorrectly in the carrier.", "Correct the wafer placement and read the slot map again."),
    "Double-Slotted Wafers Alarm": ("The slot map detected a double-slotted wafer condition.", "Correct the wafer placement and read the slot map again."),
    "Duplicate Carrier ID Alarm": ("A second carrier uses an ID already present on the tool.", "Remove the duplicate carrier."),
    "Stranded Wafer Alarm": ("A wafer is stranded on the chuck.", "Contact field service to remove the wafer."),
    "Light Level Checking Alarm": ("Measured light level differs from its target by more than 50 percent.", "Contact field service."),
}


class AlarmCenterDialog(QDialog):
    def __init__(
        self,
        alarms=None,
        parent=None,
        *,
        control_mode="Local",
        remote_clear_allowed=True,
    ):
        super().__init__(parent)
        self.alarms = list(alarms or [])
        self.result_alarms = self.alarms
        self.control_mode = "Remote" if control_mode == "Remote" else "Local"
        self.remote_clear_allowed = bool(remote_clear_allowed)
        self.setWindowTitle("Interlock and Alarm Status")
        self.resize(880, 640)
        root = QVBoxLayout(self)
        heading = QLabel("Interlock and Alarm Status")
        heading.setStyleSheet("font-size: 14px; font-weight: bold;")
        root.addWidget(heading)
        self.active_only = QCheckBox("View Only Active Alarms")
        self.active_only.setChecked(True)
        self.active_only.toggled.connect(self._refresh)
        root.addWidget(self.active_only)

        self.tabs = QTabWidget()
        safety_page = QWidget()
        safety_layout = QVBoxLayout(safety_page)
        self.safety_table = self._alarm_table()
        safety_layout.addWidget(self.safety_table)
        self.tabs.addTab(safety_page, "Safety Interlocks")

        secs_page = QWidget()
        secs_layout = QVBoxLayout(secs_page)
        secs_layout.addWidget(QLabel("Clearable Alarms"))
        self.clearable_table = self._alarm_table()
        secs_layout.addWidget(self.clearable_table, 3)
        secs_layout.addWidget(QLabel("Non-Clearable Alarms"))
        self.nonclearable_table = self._alarm_table()
        secs_layout.addWidget(self.nonclearable_table, 2)
        self.tabs.addTab(secs_page, "SECS Alarms")
        root.addWidget(self.tabs, 1)

        detail_grid = QGridLayout()
        detail_grid.addWidget(QLabel("Description"), 0, 0)
        self.description = QLabel("Select an interlock or alarm to view its description.")
        self.description.setWordWrap(True)
        detail_grid.addWidget(self.description, 0, 1)
        detail_grid.addWidget(QLabel("Corrective Action"), 1, 0)
        self.corrective_action = QLabel("-")
        self.corrective_action.setWordWrap(True)
        detail_grid.addWidget(self.corrective_action, 1, 1)
        detail_grid.setColumnStretch(1, 1)
        root.addLayout(detail_grid)

        self.permission_note = QLabel()
        self.permission_note.setWordWrap(True)
        root.addWidget(self.permission_note)
        buttons = QHBoxLayout()
        self.simulate_button = QPushButton("Simulate Alert")
        self.simulate_button.clicked.connect(self._simulate)
        self.clear_button = QPushButton("Clear Alarms")
        self.clear_button.clicked.connect(self._clear)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        buttons.addWidget(self.simulate_button)
        buttons.addWidget(self.clear_button)
        buttons.addStretch(1)
        buttons.addWidget(close)
        root.addLayout(buttons)
        self.table = self.clearable_table
        self._refresh()

    def _alarm_table(self):
        table = QTableWidget(0, 2)
        table.setHorizontalHeaderLabels(["Status", "Name"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.currentCellChanged.connect(
            lambda row, _column, _old_row, _old_column, source=table: self._show_details(source, row)
        )
        return table

    @staticmethod
    def _default_details(name, clearable):
        description, action = ALARM_DETAILS.get(name, (f"{name} is active.", ""))
        if not action:
            action = "Issue Clear Alarms or complete the associated recovery action." if clearable else "Correct the physical condition or contact field service."
        return description, action

    def _definitions(self):
        definitions = []
        for name, description, action in SAFETY_INTERLOCKS:
            definitions.append({"category": "Safety", "name": name, "clearable": False, "description": description, "corrective_action": action})
        for clearable, names in ((True, CLEARABLE_SECS_ALARMS), (False, NONCLEARABLE_SECS_ALARMS)):
            for name in names:
                description, action = self._default_details(name, clearable)
                definitions.append({"category": "SECS", "name": name, "clearable": clearable, "description": description, "corrective_action": action})
        return definitions

    def _display_alarms(self):
        merged = {(item["category"], item["name"]): {**item, "status": "Inactive"} for item in self._definitions()}
        for source in self.alarms:
            name = str(source.get("name") or source.get("message") or "Tool Error Reporting - Unknown")
            category = "Safety" if source.get("category") in {"Safety", "Safety Interlock"} else "SECS"
            key = (category, name)
            base = merged.get(key, {"category": category, "name": name, "clearable": bool(source.get("clearable", True))})
            description, action = self._default_details(name, bool(base.get("clearable", True)))
            merged[key] = {
                **base,
                "description": source.get("description", base.get("description", description)),
                "corrective_action": source.get("corrective_action", base.get("corrective_action", action)),
                "status": source.get("status", "Active"),
            }
        return list(merged.values())

    def _refresh(self):
        for table in (self.safety_table, self.clearable_table, self.nonclearable_table):
            table.setRowCount(0)
        for alarm in self._display_alarms():
            if self.active_only.isChecked() and alarm.get("status") != "Active":
                continue
            if alarm["category"] == "Safety":
                table = self.safety_table
            elif alarm["clearable"]:
                table = self.clearable_table
            else:
                table = self.nonclearable_table
            row = table.rowCount()
            table.insertRow(row)
            status_item = QTableWidgetItem("Active" if alarm.get("status") == "Active" else "Inactive")
            status_item.setBackground(QColor("#d92828") if alarm.get("status") == "Active" else QColor("#ffffff"))
            status_item.setForeground(QColor("#ffffff") if alarm.get("status") == "Active" else QColor("#111111"))
            name_item = QTableWidgetItem(alarm["name"])
            name_item.setData(Qt.UserRole, alarm)
            table.setItem(row, 0, status_item)
            table.setItem(row, 1, name_item)
        remote_blocked = self.control_mode == "Remote" and not self.remote_clear_allowed
        active_clearable = any(
            item.get("status") == "Active" and item.get("clearable")
            for item in self._display_alarms()
        )
        self.clear_button.setEnabled(active_clearable and not remote_blocked)
        self.permission_note.setText(
            "Clear Alarms is unavailable in Online Remote mode because Equipment Constants or Security access does not permit it."
            if remote_blocked
            else ""
        )

    def _show_details(self, table, row):
        item = table.item(row, 1) if row >= 0 else None
        alarm = item.data(Qt.UserRole) if item is not None else None
        if not isinstance(alarm, dict):
            return
        self.description.setText(str(alarm.get("description", "-")))
        self.corrective_action.setText(str(alarm.get("corrective_action", "-")))

    def _simulate(self):
        name = "Process Job Inspection Alarm"
        existing = next((item for item in self.alarms if item.get("name") == name), None)
        event = existing or {"name": name, "category": "SECS", "clearable": True}
        event.update({"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "status": "Active"})
        if existing is None:
            self.alarms.insert(0, event)
        self.result_alarms = self.alarms
        self.tabs.setCurrentIndex(1)
        self._refresh()

    def _clear(self):
        if not self.clear_button.isEnabled():
            return
        answer = QMessageBox.question(
            self,
            "Clear Alarms",
            "Clear all active clearable SECS alarms?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            for item in self.alarms:
                if item.get("status") == "Active" and bool(item.get("clearable", True)):
                    item["status"] = "Inactive"
            self.result_alarms = self.alarms
            self._refresh()


class InitializeSubsystemsDialog(QDialog):
    SUBSYSTEMS = (
        "Wafer Handling",
        "Stage and Alignment",
        "Inspection Optics",
        "Image Computer",
        "Data Transfer",
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.result_subsystems = None
        self.setWindowTitle("Initialize Subsystems")
        self.resize(480, 370)
        root = QVBoxLayout(self)
        note = QLabel(
            "Simulation only. Initialization resets simulator runtime state and does not operate equipment."
        )
        note.setWordWrap(True)
        root.addWidget(note)
        self.all_subsystems = QCheckBox("All SubSystems")
        self.all_subsystems.setChecked(True)
        root.addWidget(self.all_subsystems)
        self.subsystems = {}
        for name in self.SUBSYSTEMS:
            check = QCheckBox(name)
            check.setChecked(True)
            check.setEnabled(False)
            self.subsystems[name] = check
            root.addWidget(check)
        self.all_subsystems.toggled.connect(self._toggle_all)
        root.addStretch(1)
        footer = QHBoxLayout()
        footer.addStretch(1)
        initialize = QPushButton("Initialize")
        initialize.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        footer.addWidget(initialize)
        footer.addWidget(cancel)
        root.addLayout(footer)

    def _toggle_all(self, checked):
        for check in self.subsystems.values():
            check.setEnabled(not checked)
            if checked:
                check.setChecked(True)

    def _finish(self):
        selected = list(self.SUBSYSTEMS) if self.all_subsystems.isChecked() else [
            name for name, check in self.subsystems.items() if check.isChecked()
        ]
        if not selected:
            QMessageBox.warning(self, "Initialize Subsystems", "Select at least one subsystem to initialize.")
            return
        self.result_subsystems = selected
        self.accept()


class PreventiveMaintenanceDialog(QDialog):
    TASKS = {
        "Six Week": ("Inspect stage surface", "Verify prealigner", "Check load ports"),
        "Three Month": ("Clean optical path", "Verify illumination", "Inspect handling modules"),
    }

    def __init__(self, state=None, parent=None):
        super().__init__(parent)
        self.state = dict(state or {})
        self.result_state = None
        self.setWindowTitle("Preventive Maintenance")
        self.resize(620, 410)
        root = QVBoxLayout(self)
        note = QLabel(
            "Training checklist only. Customer Equipment Training and approved service procedures are required on a real tool."
        )
        note.setWordWrap(True)
        root.addWidget(note)
        row = QHBoxLayout()
        row.addWidget(QLabel("Maintenance Interval"))
        self.interval = QComboBox()
        self.interval.addItems(list(self.TASKS))
        self.interval.setCurrentText(self.state.get("interval", "Six Week"))
        row.addWidget(self.interval, 1)
        root.addLayout(row)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Done", "Task", "Last Completed"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table, 1)
        self.interval.currentTextChanged.connect(self._refresh)
        self._refresh()
        footer = QHBoxLayout()
        footer.addStretch(1)
        save = QPushButton("Save")
        save.clicked.connect(self._finish)
        close = QPushButton("Cancel")
        close.clicked.connect(self.reject)
        footer.addWidget(save)
        footer.addWidget(close)
        root.addLayout(footer)

    def _refresh(self, *_args):
        completed = self.state.get("completed", {})
        self.table.setRowCount(0)
        for task in self.TASKS[self.interval.currentText()]:
            row = self.table.rowCount()
            self.table.insertRow(row)
            check = QTableWidgetItem()
            check.setCheckState(Qt.Checked if completed.get(task) else Qt.Unchecked)
            self.table.setItem(row, 0, check)
            self.table.setItem(row, 1, QTableWidgetItem(task))
            self.table.setItem(row, 2, QTableWidgetItem(str(completed.get(task, "-"))))

    def _finish(self):
        completed = dict(self.state.get("completed", {}))
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        for row in range(self.table.rowCount()):
            task = self.table.item(row, 1).text()
            if self.table.item(row, 0).checkState() == Qt.Checked:
                completed[task] = completed.get(task) or timestamp
            else:
                completed.pop(task, None)
        self.result_state = {"interval": self.interval.currentText(), "completed": completed}
        self.accept()


class SystemLogDialog(QDialog):
    def __init__(self, title, entries=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(900, 520)
        root = QVBoxLayout(self)
        heading = QLabel(title)
        heading.setStyleSheet("font-size: 14px; font-weight: bold;")
        root.addWidget(heading)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Time", "Category", "Severity", "Message"])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        root.addWidget(self.table, 1)
        for entry in entries or []:
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = (
                entry.get("timestamp", entry.get("created", "")),
                entry.get("category", entry.get("event", "")),
                entry.get("severity", entry.get("status", "Info")),
                entry.get("message", entry.get("detail", "")),
            )
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(str(value)))
        footer = QHBoxLayout()
        footer.addStretch(1)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        footer.addWidget(close)
        root.addLayout(footer)


class SoftwareOptionsDialog(QDialog):
    OPTIONS = (
        ("Patterned Wafer Inspection", "Installed"),
        ("Reticle Qualification", "Installed"),
        ("Inline Defect Organizer", "Simulated"),
        ("Wafer Post Processing", "Installed"),
        ("Inspection Review", "Installed"),
        ("Design Based Binning", "Simulated"),
        ("Sizing / SST", "Simulated"),
        ("E87 Carrier / E90 Substrate", "Simulated"),
        ("E40 / E94 Control Jobs", "Simulated"),
        ("E116 Equipment Performance Tracking", "Simulated"),
        ("Factory SECS / ILink", "Simulated"),
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Installed Software Options")
        self.resize(650, 430)
        root = QVBoxLayout(self)
        table = QTableWidget(len(self.OPTIONS), 2)
        table.setHorizontalHeaderLabels(["Option", "Status"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        for row, values in enumerate(self.OPTIONS):
            table.setItem(row, 0, QTableWidgetItem(values[0]))
            table.setItem(row, 1, QTableWidgetItem(values[1]))
        root.addWidget(table, 1)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        footer = QHBoxLayout()
        footer.addStretch(1)
        footer.addWidget(close)
        root.addLayout(footer)


class EquipmentConstantsDialog(QDialog):
    def __init__(self, state=None, parent=None):
        super().__init__(parent)
        self.state = normalized_equipment_constants(state)
        self.result_constants = None
        self.setWindowTitle("SECS Equipment Constants")
        self.resize(780, 590)
        root = QVBoxLayout(self)
        note = QLabel("Configuration simulator. Values are persisted locally and no host messages are sent.")
        note.setWordWrap(True)
        root.addWidget(note)
        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)
        self.controls = {}
        self._add_general_tab()
        self._add_communications_tab()
        self._add_material_tab()
        self._add_remote_tab()
        footer = QHBoxLayout()
        defaults = QPushButton("Default")
        defaults.clicked.connect(self._defaults)
        footer.addWidget(defaults)
        footer.addStretch(1)
        apply = QPushButton("OK")
        apply.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        footer.addWidget(apply)
        footer.addWidget(cancel)
        root.addLayout(footer)

    def _combo(self, key, values):
        control = QComboBox()
        control.addItems(values)
        control.setCurrentText(str(self.state[key]))
        self.controls[key] = control
        return control

    def _line(self, key):
        control = QLineEdit(str(self.state[key]))
        self.controls[key] = control
        return control

    def _check(self, key, label):
        control = QCheckBox(label)
        control.setChecked(bool(self.state[key]))
        self.controls[key] = control
        return control

    def _spin(self, key, minimum, maximum):
        control = QSpinBox()
        control.setRange(minimum, maximum)
        control.setValue(int(self.state[key]))
        self.controls[key] = control
        return control

    def _form_tab(self, title, rows):
        page = QWidget()
        form = QGridLayout(page)
        for row, (label, control) in enumerate(rows):
            form.addWidget(QLabel(label), row, 0)
            form.addWidget(control, row, 1)
        form.setColumnStretch(1, 1)
        form.setRowStretch(len(rows), 1)
        self.tabs.addTab(page, title)

    def _add_general_tab(self):
        self._form_tab("General", (
            ("Initial E10 State", self._combo("initial_e10_state", ["Non-Scheduled", "Scheduled Downtime", "Unscheduled Downtime", "Engineering", "Stand-by", "Productive"])),
            ("E58 Startup", self._check("e58_startup", "Enabled")),
            ("E58 Shutdown", self._check("e58_shutdown", "Enabled")),
            ("Device Name", self._line("device_name")),
            ("Time Format", self._combo("time_format", ["YYMMDDHHMMSS", "YYYYMMDDHHMMSSCC"])),
            ("Signal Tower Control", self._combo("signal_tower_control", ["Equipment Control", "Host Control"])),
            ("Report Step ID", self._check("report_step_id", "Include Step ID")),
            ("Host Manages Recipes", self._check("host_manages_recipes", "Enabled")),
        ))

    def _add_communications_tab(self):
        self._form_tab("Communications", (
            ("Polling Delay (seconds)", self._spin("poll_delay", 15, 30)),
            ("Communication Timeout (seconds)", self._spin("communication_timeout", 15, 30)),
            ("Report Type", self._combo("report_type", ["Normal", "Annotated"])),
            ("Initial Control State", self._combo("initial_control_state", ["Online", "Offline"])),
            ("Initial Online Substate", self._combo("initial_online_substate", ["Local", "Remote"])),
            ("Spooling", self._check("spooling", "Enabled")),
        ))

    def _add_material_tab(self):
        self._form_tab("Material Flow", (
            ("Wait For Job", self._check("wait_for_job", "Enabled")),
            ("Auto Start", self._check("auto_start", "Enabled")),
            ("Confirm Start", self._check("confirm_start", "Enabled")),
            ("Check Cassette Map", self._check("check_cassette_map", "Enabled")),
            ("Auto Unload", self._check("auto_unload", "Enabled")),
            ("Operator Load Read Wafer ID", self._check("operator_load_read_wafer_id", "Enabled")),
            ("Production Read Wafer ID", self._check("production_read_wafer_id", "Enabled")),
            ("Continue on Wafer ID Failure", self._check("continue_on_wafer_id_failure", "Enabled")),
        ))

    def _add_remote_tab(self):
        self._form_tab("Remote Mode", (
            ("Inspection Job Commands", self._check("remote_job_commands", "Enabled")),
            ("Wafer Handling Commands", self._check("remote_wafer_handling", "Enabled")),
            ("Carrier Management", self._check("remote_carrier_management", "Enabled")),
            ("Clear Alarms", self._check("remote_clear_alarms", "Enabled")),
            ("Process Program Upload / Download", self._check("remote_recipe_transfer", "Enabled")),
        ))

    def _defaults(self):
        defaults = normalized_equipment_constants()
        for key, control in self.controls.items():
            value = defaults[key]
            if isinstance(control, QCheckBox):
                control.setChecked(value)
            elif isinstance(control, QSpinBox):
                control.setValue(value)
            elif isinstance(control, QComboBox):
                control.setCurrentText(str(value))
            else:
                control.setText(str(value))

    def _finish(self):
        result = {}
        for key, control in self.controls.items():
            if isinstance(control, QCheckBox):
                result[key] = control.isChecked()
            elif isinstance(control, QSpinBox):
                result[key] = control.value()
            elif isinstance(control, QComboBox):
                result[key] = control.currentText()
            else:
                result[key] = control.text().strip()
        if not result["device_name"]:
            QMessageBox.warning(self, "Equipment Constants", "Device Name is required.")
            return
        self.result_constants = normalized_equipment_constants(result)
        self.accept()


class TransferConfigurationDialog(QDialog):
    def __init__(self, state=None, parent=None):
        super().__init__(parent)
        self.state = normalized_data_transfer(state)
        self.setWindowTitle("Transfer Configuration Summary")
        self.resize(600, 360)
        root = QVBoxLayout(self)
        title = QLabel("Data Transfer Configuration")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        root.addWidget(title)
        note = QLabel("Read-only simulator configuration. No Analysis System connection is opened.")
        note.setWordWrap(True)
        root.addWidget(note)
        form = QGridLayout()
        rows = (
            ("Service State", "Running" if self.state["running"] else "Stopped"),
            ("Protocol", self.state["protocol"]),
            ("Analysis System", self.state["analysis_system"]),
            ("Host", self.state["host"]),
            ("Port", self.state["port"]),
            ("Automatic Retry", "Enabled" if self.state["automatic_retry"] else "Disabled"),
        )
        for row, (label, value) in enumerate(rows):
            form.addWidget(QLabel(label), row, 0)
            form.addWidget(QLabel(str(value)), row, 1)
        form.setColumnStretch(1, 1)
        root.addLayout(form)
        root.addStretch(1)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        footer = QHBoxLayout()
        footer.addStretch(1)
        footer.addWidget(close)
        root.addLayout(footer)


class DataTransferQueueDialog(QDialog):
    def __init__(self, items=None, transfer_state=None, parent=None):
        super().__init__(parent)
        self.items = [dict(item) for item in (items or [])]
        self.transfer_state = normalized_data_transfer(transfer_state)
        self.result_items = self.items
        self.setWindowTitle("Data Transfer Queue")
        self.resize(900, 500)
        root = QVBoxLayout(self)
        self.service_status = QLabel()
        root.addWidget(self.service_status)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Select", "Lot Name", "Wafer", "Destination", "Status", "Last Error"])
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        for column, width in enumerate((72, 120, 85, 190, 130)):
            self.table.setColumnWidth(column, width)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table, 1)
        buttons = QHBoxLayout()
        retry = QPushButton("Retry Transfer")
        retry.clicked.connect(self._retry)
        delete = QPushButton("Delete")
        delete.clicked.connect(self._delete)
        buttons.addWidget(retry)
        buttons.addWidget(delete)
        buttons.addStretch(1)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        buttons.addWidget(close)
        root.addLayout(buttons)
        self._refresh()

    def _selected_ids(self):
        return {
            self.table.item(row, 0).data(Qt.UserRole)
            for row in range(self.table.rowCount())
            if self.table.item(row, 0).checkState() == Qt.Checked
        }

    def _refresh(self):
        self.service_status.setText(
            f"Transfer service: {'Running' if self.transfer_state['running'] else 'Stopped'} | "
            f"Analysis System: {self.transfer_state['analysis_system']} (simulated)"
        )
        self.table.setRowCount(0)
        for item in self.items:
            row = self.table.rowCount()
            self.table.insertRow(row)
            check = QTableWidgetItem()
            check.setCheckState(Qt.Unchecked)
            check.setData(Qt.UserRole, item.get("id"))
            self.table.setItem(row, 0, check)
            values = (item.get("lot_id", ""), item.get("wafer_id", ""), item.get("destination", ""), item.get("status", "Pending"), item.get("error", ""))
            for column, value in enumerate(values, 1):
                self.table.setItem(row, column, QTableWidgetItem(str(value)))

    def _retry(self):
        selected = self._selected_ids()
        if not selected:
            return
        if not self.transfer_state["running"]:
            QMessageBox.warning(self, "Data Transfer", "Start the Data Transfer service before retrying queued lots.")
            return
        for item in self.items:
            if item.get("id") in selected:
                item["status"] = "Transferred (simulated)"
                item["error"] = ""
                item["last_attempt"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.result_items = self.items
        self._refresh()

    def _delete(self):
        selected = self._selected_ids()
        if not selected:
            return
        answer = QMessageBox.question(
            self,
            "Delete Transfer Queue Items",
            "Delete the selected lots from the transfer queue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self.items = [item for item in self.items if item.get("id") not in selected]
            self.result_items = self.items
            self._refresh()


class LotSummaryDialog(QDialog):
    def __init__(self, results=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Lot Summary")
        self.resize(980, 540)
        root = QVBoxLayout(self)
        title = QLabel("Inspection Lot Summary")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        root.addWidget(title)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["Lot", "Wafer", "Inspection", "Device", "Step", "Defects", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table, 1)
        for result in results or []:
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = (
                result.get("lot_id", ""),
                result.get("wafer_id", ""),
                result.get("inspection", ""),
                result.get("device", ""),
                result.get("step", ""),
                result.get("defect_count", len(result.get("defects", []))),
                result.get("status", "Complete"),
            )
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(str(value)))
        legend = QLabel("Status: Complete = inspection finished; Aborted = run ended before completion; Failed = inspection error.")
        legend.setWordWrap(True)
        root.addWidget(legend)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        footer = QHBoxLayout()
        footer.addStretch(1)
        footer.addWidget(close)
        root.addLayout(footer)


class DeleteInspectionsDialog(QDialog):
    def __init__(self, recipes=None, current_recipe_id="", parent=None):
        super().__init__(parent)
        self.recipes = [dict(recipe) for recipe in (recipes or [])]
        self.current_recipe_id = current_recipe_id
        self.result_ids = None
        self.setWindowTitle("Select Inspection(s)")
        self.resize(820, 470)
        root = QVBoxLayout(self)
        note = QLabel("Select one or more inspection recipes to permanently delete from simulator storage.")
        note.setWordWrap(True)
        root.addWidget(note)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Select", "Inspection", "Device", "Step", "Status", "Last Modified"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table, 1)
        for recipe in self.recipes:
            row = self.table.rowCount()
            self.table.insertRow(row)
            check = QTableWidgetItem()
            check.setCheckState(Qt.Unchecked)
            check.setData(Qt.UserRole, recipe.get("id"))
            if recipe.get("id") == current_recipe_id:
                check.setFlags(check.flags() & ~Qt.ItemIsEnabled)
                check.setToolTip("The currently open inspection cannot be deleted.")
            self.table.setItem(row, 0, check)
            values = (recipe.get("inspection", ""), recipe.get("device", ""), recipe.get("step", ""), recipe.get("status", ""), recipe.get("last_modified", ""))
            for column, value in enumerate(values, 1):
                self.table.setItem(row, column, QTableWidgetItem(str(value)))
        footer = QHBoxLayout()
        footer.addStretch(1)
        delete = QPushButton("Delete")
        delete.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        footer.addWidget(delete)
        footer.addWidget(cancel)
        root.addLayout(footer)

    def _finish(self):
        selected = [
            self.table.item(row, 0).data(Qt.UserRole)
            for row in range(self.table.rowCount())
            if self.table.item(row, 0).checkState() == Qt.Checked
            and bool(self.table.item(row, 0).flags() & Qt.ItemIsEnabled)
        ]
        if not selected:
            QMessageBox.warning(self, "Delete Inspections", "Select at least one inspection to delete.")
            return
        answer = QMessageBox.question(
            self,
            "Delete Inspections",
            f"Permanently delete {len(selected)} selected inspection(s)?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self.result_ids = selected
            self.accept()


class SendLotsDialog(QDialog):
    def __init__(self, results=None, default_destination="", parent=None):
        super().__init__(parent)
        self.result_selection = None
        self.setWindowTitle("Send Lots")
        self.resize(760, 450)
        root = QVBoxLayout(self)
        destinations = QHBoxLayout()
        destinations.addWidget(QLabel("Analysis or Storage System"))
        self.destination = QLineEdit(default_destination)
        destinations.addWidget(self.destination, 1)
        root.addLayout(destinations)
        lots = {}
        for result in results or []:
            lot_id = str(result.get("lot_id", ""))
            if not lot_id:
                continue
            lots.setdefault(lot_id, {"wafers": set(), "results": []})
            lots[lot_id]["wafers"].add(str(result.get("wafer_id", "")))
            lots[lot_id]["results"].append(result.get("id"))
        self.lots = lots
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Select", "Lot", "Wafers", "Result Files"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table, 1)
        for lot_id, data in lots.items():
            row = self.table.rowCount()
            self.table.insertRow(row)
            check = QTableWidgetItem()
            check.setCheckState(Qt.Unchecked)
            check.setData(Qt.UserRole, lot_id)
            self.table.setItem(row, 0, check)
            self.table.setItem(row, 1, QTableWidgetItem(lot_id))
            self.table.setItem(row, 2, QTableWidgetItem(str(len(data["wafers"]))))
            self.table.setItem(row, 3, QTableWidgetItem(str(len(data["results"]))))
        footer = QHBoxLayout()
        footer.addStretch(1)
        send = QPushButton("Send")
        send.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        footer.addWidget(send)
        footer.addWidget(cancel)
        root.addLayout(footer)

    def _finish(self):
        lot_ids = [
            self.table.item(row, 0).data(Qt.UserRole)
            for row in range(self.table.rowCount())
            if self.table.item(row, 0).checkState() == Qt.Checked
        ]
        if not lot_ids:
            QMessageBox.warning(self, "Send Lots", "Select at least one lot to send.")
            return
        destination = self.destination.text().strip()
        if not destination:
            QMessageBox.warning(self, "Send Lots", "Specify an Analysis or Storage System.")
            return
        self.result_selection = {"lot_ids": lot_ids, "destination": destination}
        self.accept()


class RenameLotDialog(QDialog):
    def __init__(self, lot_names=None, parent=None):
        super().__init__(parent)
        self.result_names = None
        self.setWindowTitle("Rename Lot")
        self.resize(520, 220)
        root = QVBoxLayout(self)
        form = QGridLayout()
        self.old_name = QComboBox()
        self.old_name.addItems(sorted({str(name) for name in (lot_names or []) if str(name)}))
        self.new_name = QLineEdit()
        form.addWidget(QLabel("Old Lot Name"), 0, 0)
        form.addWidget(self.old_name, 0, 1)
        form.addWidget(QLabel("New Lot Name"), 1, 0)
        form.addWidget(self.new_name, 1, 1)
        form.setColumnStretch(1, 1)
        root.addLayout(form)
        root.addStretch(1)
        footer = QHBoxLayout()
        footer.addStretch(1)
        ok = QPushButton("OK")
        ok.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        footer.addWidget(ok)
        footer.addWidget(cancel)
        root.addLayout(footer)

    def _finish(self):
        old_name = self.old_name.currentText().strip()
        new_name = self.new_name.text().strip()
        if not old_name or not new_name:
            QMessageBox.warning(self, "Rename Lot", "Select an existing lot and enter a new lot name.")
            return
        if old_name == new_name:
            QMessageBox.warning(self, "Rename Lot", "The new lot name must be different.")
            return
        self.result_names = (old_name, new_name)
        self.accept()


class ClickAndMarkConfigurationDialog(QDialog):
    DEFAULTS = {
        "enabled": False,
        "auto_acquire": False,
        "auto_visible": False,
        "auto_resize": True,
        "show_toolbar": True,
        "save_location": "",
    }

    def __init__(self, state=None, parent=None):
        super().__init__(parent)
        self.state = {**self.DEFAULTS, **(state if isinstance(state, dict) else {})}
        self.result_settings = None
        self.setWindowTitle("Click and Mark Configuration")
        self.resize(610, 360)
        root = QVBoxLayout(self)
        self.enabled = QCheckBox("Enable Click and Mark Image Display Window")
        self.enabled.setChecked(bool(self.state["enabled"]))
        root.addWidget(self.enabled)
        self.options = {}
        for key, label in (
            ("auto_acquire", "Auto Acquire"),
            ("auto_visible", "Auto Visible"),
            ("auto_resize", "Auto Resize Image"),
            ("show_toolbar", "Show Toolbar"),
        ):
            check = QCheckBox(label)
            check.setChecked(bool(self.state[key]))
            self.options[key] = check
            root.addWidget(check)
        path = QHBoxLayout()
        path.addWidget(QLabel("Image Save Location"))
        self.save_location = QLineEdit(str(self.state["save_location"]))
        path.addWidget(self.save_location, 1)
        root.addLayout(path)
        note = QLabel("Image acquisition, stage movement, and optics changes are simulated in this application.")
        note.setWordWrap(True)
        root.addWidget(note)
        root.addStretch(1)
        footer = QHBoxLayout()
        footer.addStretch(1)
        ok = QPushButton("OK")
        ok.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        footer.addWidget(ok)
        footer.addWidget(cancel)
        root.addLayout(footer)

    def _finish(self):
        self.result_settings = {
            "enabled": self.enabled.isChecked(),
            **{key: check.isChecked() for key, check in self.options.items()},
            "save_location": self.save_location.text().strip(),
        }
        self.accept()

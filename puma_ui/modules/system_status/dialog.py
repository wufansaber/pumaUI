from __future__ import annotations

import random
from datetime import datetime
from pathlib import Path

from ...qt_compat import (
    QAbstractItemView,
    QCheckBox,
    QColor,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPainter,
    QPainterPath,
    QPen,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QPixmap,
    QPushButton,
    QScrollArea,
    QSizePolicy,
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
    (
        "Stage Interlock",
        "A stage safety interlock has been activated.",
        "All access panels must be closed and an initialization of the Stage subsystem must be "
        "performed before normal operation can resume. The Stage subsystem can be initialized "
        "using the Init System option in the Utilities menu.",
    ),
    (
        "Lamp Power Interlock",
        "A lamp power interlock is activated.",
        "The laser cover must be properly installed and a manual switch activated hardware reset "
        "followed by an optics subsystem initialization must be performed before normal operation "
        "can resume.",
    ),
    (
        "Robot Interlock",
        "Triggered when robot safety interlock has been activated.",
        "All Robot panels must be closed and an initialization of the Wafer Handler subsystem must "
        "be performed before normal operation can resume. The Wafer Handler subsystem can be "
        "initialized using the Init System option in the Utilities menu.",
    ),
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
    "Transfer Error Alarm": (
        "An E84 transfer error has occurred on the load port.",
        "Can be cleared by Wafer handler hardware reset or clear alarms remote command or an equivalent UI command.",
    ),
    "Access Mode Violation": (
        "Triggered when manual delivery is attempted in Auto Access mode.",
        "Can be cleared by a Process With Carrier or a CancelCarrier service or Carrier Unload or Clear Alarms remote command or an equivalent UI command.",
    ),
    "Carrier ID Read/Write Alarm": (
        "Triggered when Carrier ID Read/Write failure occurs.",
        "",
    ),
    "Carrier ID Verification Alarm": (
        "Triggered when carrier is present but not properly placed.",
        "Can be cleared by Wafer handler hardware reset or Clear Alarms remote command or an equivalent UI command.",
    ),
    "Slot Map Read Alarm": (
        "Triggered when a slot map read fails.",
        "This alarm may be cleared by any of the following. A second successful slot map read or carrier removal or Clear Alarms remote command or an equivalent UI command.",
    ),
    "Slot Map Verification Alarm": (
        "Cassette map verification has failed.",
        "Can be cleared by Wafer handler reset or Clear Alarms remote command or an equivalent UI command.",
    ),
    "Out of Service Alarm": (
        "Triggered while attempting to use an out of service load port.",
        "Call service engineer.",
    ),
    "Port Operational Alarm": (
        "Triggered when an operational error occurs, including Carrier Clamp/Unclamp, Lock/Unlock, Open/Close and Dock/Undock failure.",
        "Can be cleared by Wafer handler hardware reset or clear alarms remote command or an equivalent UI command.",
    ),
    "Carrier Open Failure Alarm": (
        "Triggered when carrier door failed to open.",
        "Can be cleared by Clear Alarms remote command or an equivalent UI command.",
    ),
    "Carrier Close Failure Alarm": (
        "Triggered when carrier door failed to close.",
        "Can be cleared by Clear Alarms remote command or an equivalent UI command.",
    ),
    "Light Curtain Violation Alarm": (
        "Triggered when detecting light curtain violation during AMHS transfer.",
        "Can be cleared by Clear Alarms remote command or an equivalent UI command.",
    ),
    "Wafer Handler Mini Environment Low Pressure Alarm": (
        "Triggered when the pressure in the wafer handler mini environment drops below an acceptable level.",
        "Pressure should be restored to normal level.",
    ),
    "Wafer Handler Mini Environment High Pressure Alarm": (
        "The wafer handler mini environment differential pressure is too high.",
        "Pressure should be restored to normal level.",
    ),
    "Wafer Handler Ionizer Alarm": (
        "Triggered when the ionizer in the wafer handler has failed.",
        "Maintenance is most likely required as it is unlikely that the ionizer will restart on its own. The alarm is cleared when the ionizer begins working again.",
    ),
    "Clearable Wafer Handler Alarm": (
        "Triggered when a clearable wafer handler error has occurred.",
        "Can be cleared by Clear Alarms remote command or UI command.",
    ),
    "Process Job Inspection Alarm": (
        "Triggered when process job inspection fails.",
        "Can be cleared when the process job is completed/canceled/stopped/aborted, or by Clear Alarms remote command or an equivalent UI command.",
    ),
    "Pressure Sensor Alarm": (
        "Triggered when pressure sensor is out of range. Inspection can continue but image focus may drift.",
        "Contact GSS to schedule service.",
    ),
    "Temperature Sensor Alarm": (
        "Triggered when temperature sensor is out of range. Inspection can continue but image focus may drift.",
        "Contact GSS to schedule service.",
    ),
    "CMS Parameter Out of Range Alarm": (
        "Triggered when a CMS parameter goes out of range.",
        "The CMS parameter should be restored to the normal range.",
    ),
    "Substrate Destination Not Accessible Alarm": (
        "Wafer destination location is not accessible",
        "Contact KT service personnel.",
    ),
    "Tool Error Reporting - Unknown": (
        "Triggered when an error occurred during inspection. The error has not yet been classified.",
        "The alarm will be cleared when lot completes. It can also be cleared by Clear alarms remote command or an equivalent UI command.",
    ),
    "Clearable Alarm": ("User configurable alarm", "Contact KT service personnel."),
    "Stop Tool - Reset": ("User configurable alarm", "Contact KT service personnel."),
    "Stop Tool - Service": ("User configurable alarm", "Contact KT service personnel."),
    "Data Integrity Issue": ("User configurable alarm", "Contact KT service personnel."),
    "Pause Tool": ("User configurable alarm", "Contact KT service personnel."),
    "Carrier Presence/Placement Alarm": (
        "Triggered when carrier is present but not properly placed.",
        "Place the carrier properly or remove.",
    ),
    "Crooked Wafers Alarm": (
        "Triggered when the system detects a cross-slotted or double-wafer abnormal wafer condition in the slot map. The carrier shall be rejected and moved to unload position.",
        "A second successful slot map read may clear the alarm or remove the carrier.",
    ),
    "Double-Slotted Wafers Alarm": (
        "Triggered when the system detects a double-slotted wafer abnormal wafer condition in the slot map. The carrier shall be rejected and moved to unload position.",
        "A second successful slot map read may clear the alarm or carrier removal.",
    ),
    "Duplicate Carrier ID Alarm": (
        "Triggered when a new carrier is added with an ID that is the same as that of another carrier present.",
        "This alarm can be cleared by removing the second carrier.",
    ),
    "Wafer Protrusion Interlock Alarm": (
        "Triggered when load port has one or more protruded wafer(s).",
        "This alarm may be cleared by correcting the physical wafer protrusion (pushing the wafer back into the cassette) followed by a re-initialization of the Wafer Handler subcomponent.",
    ),
    "Service Mode Alarm": (
        "Triggered when the inspection station has been placed in service mode.",
        "Call the field service engineer.",
    ),
    "Stranded Wafer Alarm": (
        "Triggered when a wafer is stranded on chuck. The wafer must be removed by a field service engineer.",
        "Call the field service engineer.",
    ),
    "Non-Clearable Wafer Handler Alarm": (
        "Triggered when a non-clearable wafer handler error has occurred.",
        "Call the field service engineer.",
    ),
    "Wafer Handler Polling Exception Alarm": (
        "Triggered when wafer handler polling exception occurs. Continuing to operate the robot may have possible side effects - not knowing the status of the FFU may impact the PWP, not knowing the status of Ionizer may impact the process, not knowing the status of the interlock may mislead user about the tool's health.",
        "Call the field service engineer.",
    ),
    "Mini Environment Hardware Present But Configuration Disabled Alarm": (
        "Triggered when mini environment hardware is present but configuration is disabled",
        "Enable mini environment configuration.",
    ),
    "Chiller Alarm": (
        "Triggered when chiller temperature, ambient temperature, or pressure is at alarm level.",
        "Call the service engineer.",
    ),
    "Laser Site Change Error": (
        "Triggered when error occurs during laser site change.",
        "Call the service engineer.",
    ),
    "No Laser Site Left": (
        "Triggered if there are no more laser sites left and the current laser site is going to expire in (less than) 6 hours.",
        "Call the service engineer.",
    ),
    "Light Level Checking Alarm": (
        "Triggered when the light level check is over 50% of the desired target.",
        "Call the service engineer.",
    ),
    "Secondary Purge Pressure Alarm": (
        "Triggered when the secondary purge pressure violates the minimum & maximum thresholds. Inspections may fail due to the violation.",
        "Contact GSS to schedule service.",
    ),
}

PORT_SCOPED_ALARMS = {
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
    "Carrier Presence/Placement Alarm",
    "Crooked Wafers Alarm",
    "Double-Slotted Wafers Alarm",
    "Duplicate Carrier ID Alarm",
    "Wafer Protrusion Interlock Alarm",
}


class _SecsAlarmNameDelegate(QStyledItemDelegate):
    """Draw the alarm name with its own color, including while the row is selected."""

    def paint(self, painter, option, index):  # noqa: N802 - Qt override
        if index.column() != 0:
            super().paint(painter, option, index)
            return
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        painter.save()
        rect = opt.rect
        selected = bool(opt.state & QStyle.State_Selected)
        if selected:
            painter.setPen(QPen(QColor("#444444"), 1, Qt.DotLine))
            painter.setBrush(QColor("#f7f4ea"))
            painter.drawRect(rect.adjusted(1, 1, -2, -2))
        else:
            background = index.data(Qt.BackgroundRole)
            color = background.color() if background is not None and hasattr(background, "color") else QColor("#f7f4ea")
            painter.fillRect(rect, color)
        foreground = index.data(Qt.ForegroundRole)
        text_color = foreground.color() if foreground is not None and hasattr(foreground, "color") else QColor("#0000cc")
        painter.setPen(text_color)
        painter.setFont(opt.font)
        painter.drawText(rect.adjusted(6, 0, -4, 0), int(Qt.AlignVCenter | Qt.AlignLeft), opt.text)
        painter.restore()


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
        self.resize(820, 640)
        self.setStyleSheet("QDialog { background: #efe6c8; }")
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        self.active_only = QCheckBox("View Only Active Interlocks")
        self.active_only.toggled.connect(self._refresh)

        self.tabs = QTabWidget()
        safety_page = QWidget()
        self.safety_layout = QVBoxLayout(safety_page)
        self.safety_layout.setContentsMargins(6, 6, 6, 6)
        self.safety_layout.addWidget(self.active_only)
        self.safety_table = self._alarm_table("Interlocks")
        self.safety_layout.addWidget(self.safety_table, 1)
        self.tabs.addTab(safety_page, "Safety Interlocks")

        secs_page = QWidget()
        self.secs_layout = QVBoxLayout(secs_page)
        self.secs_layout.setContentsMargins(6, 6, 6, 6)
        secs_header = QWidget()
        self.secs_header_layout = QHBoxLayout(secs_header)
        self.secs_header_layout.setContentsMargins(0, 0, 0, 0)
        self.secs_header_layout.addStretch(1)
        self.acknowledge_button = QPushButton("Acknowledge")
        self.acknowledge_button.setEnabled(False)
        self.acknowledge_button.clicked.connect(self._acknowledge)
        self.clear_button = QPushButton("Clear Alarms")
        self.clear_button.clicked.connect(self._clear)
        self.secs_header_layout.addWidget(self.acknowledge_button)
        self.secs_header_layout.addWidget(self.clear_button)
        self.secs_layout.addWidget(secs_header)
        self.secs_table = self._secs_alarm_table()
        self.secs_layout.addWidget(self.secs_table, 1)
        self.tabs.addTab(secs_page, "SECS Alarms")
        self.tabs.currentChanged.connect(self._move_active_filter)
        root.addWidget(self.tabs, 1)

        self.detail_prompt = QLabel(
            "Select an interlock to view brief description and corrective measure"
        )
        root.addWidget(self.detail_prompt)

        detail_frame = QFrame()
        detail_frame.setFrameShape(QFrame.StyledPanel)
        detail_frame.setStyleSheet("QFrame { background: #f7f1dc; }")
        detail_layout = QVBoxLayout(detail_frame)
        detail_layout.setContentsMargins(2, 2, 2, 2)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setMinimumHeight(150)
        detail_body = QWidget()
        detail_body.setStyleSheet("background: #f7f1dc;")
        body_layout = QVBoxLayout(detail_body)
        body_layout.setContentsMargins(8, 6, 8, 6)
        self.detail_title = QLabel("")
        self.detail_title.setStyleSheet("font-weight: bold; font-style: italic; font-size: 13px;")
        body_layout.addWidget(self.detail_title)
        self.description = QLabel("")
        self.description.setWordWrap(True)
        body_layout.addWidget(self.description)
        self.corrective_heading = QLabel("Corrective Measures")
        self.corrective_heading.setStyleSheet("font-weight: bold; font-style: italic;")
        body_layout.addWidget(self.corrective_heading)
        self.corrective_action = QLabel("")
        self.corrective_action.setWordWrap(True)
        body_layout.addWidget(self.corrective_action)
        body_layout.addStretch(1)
        scroll.setWidget(detail_body)
        detail_layout.addWidget(scroll)
        root.addWidget(detail_frame)

        self.legend_group = QGroupBox("Legend")
        self.legend_group.setStyleSheet(
            """
            QGroupBox {
                border: 1px solid #9a9a9a;
                border-radius: 2px;
                margin-top: 10px;
                background: #f4f0e4;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 8px;
                padding: 0 4px;
                color: #0000ee;
                background: #efe6c8;
            }
            """
        )
        self.legend_group.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        self.legend_layout = QHBoxLayout(self.legend_group)
        self.legend_layout.setContentsMargins(14, 8, 14, 8)
        legend_row = QHBoxLayout()
        legend_row.addStretch(1)
        legend_row.addWidget(self.legend_group)
        legend_row.addStretch(1)
        root.addLayout(legend_row)
        self._set_legend(False)

        self.permission_note = QLabel()
        self.permission_note.setWordWrap(True)
        root.addWidget(self.permission_note)
        buttons = QHBoxLayout()
        self.simulate_button = QPushButton("Simulate Alert")
        self.simulate_button.clicked.connect(self._simulate)
        self.simulate_button.setVisible(False)
        ok_button = QPushButton("OK")
        ok_button.setFixedWidth(88)
        ok_button.clicked.connect(self.accept)
        buttons.addWidget(self.simulate_button)
        buttons.addStretch(1)
        buttons.addWidget(ok_button)
        buttons.addStretch(1)
        root.addLayout(buttons)
        self.table = self.secs_table
        self._refresh()

    def _alarm_table(self, name_header: str):
        table = QTableWidget(0, 2)
        table.setHorizontalHeaderLabels([name_header, "Status"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        table.setColumnWidth(1, 230)
        table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setShowGrid(True)
        table.setStyleSheet(
            """
            QTableWidget {
                background: #f4ecd4;
                gridline-color: #8d8d8d;
                selection-background-color: #f6f1c2;
                selection-color: #0000cc;
            }
            QHeaderView::section {
                background: #f7f3e4;
                border: 1px solid #8d8d8d;
                font-weight: bold;
                padding: 3px;
            }
            """
        )
        table.currentCellChanged.connect(
            lambda row, _column, _old_row, _old_column, source=table: self._show_details(source, row)
        )
        return table

    def _secs_alarm_table(self):
        table = self._alarm_table("Clearable \\ Non-Clearable Alarms")
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(
            ["Clearable \\ Non-Clearable Alarms", "General", "Port 1", "Port 2"]
        )
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for column in (1, 2, 3):
            table.horizontalHeader().setSectionResizeMode(column, QHeaderView.Fixed)
            table.setColumnWidth(column, 88)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        table.setItemDelegate(_SecsAlarmNameDelegate(table))
        table.setStyleSheet(
            """
            QTableWidget {
                background: #f7f4ea;
                gridline-color: #8d8d8d;
                selection-background-color: #f7f4ea;
            }
            QTableWidget::item:selected {
                background: #f7f4ea;
                border: 1px dotted #444444;
            }
            QHeaderView::section {
                background: #f7f3e4;
                border: 1px solid #8d8d8d;
                font-weight: bold;
                padding: 3px;
            }
            """
        )
        return table

    def _move_active_filter(self, index: int):
        secs = index == 1
        self.active_only.setText(
            "View Only Active Alarms" if secs else "View Only Active Interlocks"
        )
        self.detail_prompt.setText(
            "Select an alarm to view brief description and corrective measure"
            if secs
            else "Select an interlock to view brief description and corrective measure"
        )
        target = self.secs_header_layout if secs else self.safety_layout
        if target.indexOf(self.active_only) < 0:
            self.active_only.setParent(None)
            target.insertWidget(0, self.active_only)
            self.active_only.show()
        self._set_legend(secs)
        if hasattr(self, "simulate_button"):
            self.simulate_button.setVisible(secs)
        if secs and self.secs_table.rowCount() and self.secs_table.currentRow() < 0:
            self.secs_table.selectRow(0)

    def _set_legend(self, secs: bool):
        while self.legend_layout.count():
            item = self.legend_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.legend_layout.addStretch(1)
        self.legend_layout.addWidget(self._legend_mark(True))
        self.legend_layout.addWidget(QLabel("Active"))
        self.legend_layout.addSpacing(16)
        self.legend_layout.addWidget(self._legend_mark(False))
        self.legend_layout.addWidget(QLabel("Inactive"))
        if secs:
            self.legend_layout.addSpacing(16)
            self.legend_layout.addWidget(self._color_swatch("#008080"))
            self.legend_layout.addWidget(QLabel("Clearable"))
            self.legend_layout.addSpacing(16)
            self.legend_layout.addWidget(self._color_swatch("#0000cc"))
            self.legend_layout.addWidget(QLabel("Non-Clearable"))
        self.legend_layout.addStretch(1)

    def _color_swatch(self, color: str) -> QLabel:
        swatch = QLabel()
        swatch.setFixedSize(18, 16)
        swatch.setStyleSheet(f"background: {color}; border: none;")
        return swatch

    @staticmethod
    def _status_pixmap(active: bool) -> QPixmap:
        pixmap = QPixmap(24, 20)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.moveTo(12, 1)
        path.lineTo(23, 19)
        path.lineTo(1, 19)
        path.closeSubpath()
        painter.setPen(QPen(QColor("#202020") if active else QColor("#8d8d8d"), 1.4))
        painter.setBrush(QColor("#e10600") if active else QColor("#ffffff"))
        painter.drawPath(path)
        painter.setPen(QPen(QColor("#111111"), 1.8))
        painter.drawLine(12, 7, 12, 12)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#111111"))
        painter.drawEllipse(11, 14, 3, 3)
        painter.end()
        return pixmap

    def _legend_mark(self, active: bool) -> QLabel:
        mark = QLabel()
        if active:
            mark.setPixmap(self._status_pixmap(True))
            mark.setFixedSize(26, 22)
            return mark
        plate = QPixmap(28, 22)
        plate.fill(QColor("#c0c0c0"))
        painter = QPainter(plate)
        painter.drawPixmap(2, 1, self._status_pixmap(False))
        painter.end()
        mark.setPixmap(plate)
        mark.setFixedSize(28, 22)
        return mark

    def _status_cell(self, active):
        holder = QWidget()
        holder.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        holder.setStyleSheet("background: #c8c8c8;")
        layout = QHBoxLayout(holder)
        layout.setContentsMargins(0, 0, 0, 0)
        if active is not None:
            icon = QLabel()
            icon.setPixmap(self._status_pixmap(bool(active)))
            icon.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            layout.addWidget(icon, alignment=Qt.AlignCenter)
        return holder

    @staticmethod
    def _default_details(name, clearable):
        if name in ALARM_DETAILS:
            return ALARM_DETAILS[name]
        action = (
            "Issue Clear Alarms or complete the associated recovery action."
            if clearable
            else "Correct the physical condition or contact field service."
        )
        return f"{name} is active.", action

    @staticmethod
    def _alarm_scopes(alarm):
        active = alarm.get("status") == "Active"
        if alarm.get("name") not in PORT_SCOPED_ALARMS:
            return {"general": "Active" if active else "Inactive", "1": None, "2": None}
        states = {"general": None, "1": "Inactive", "2": "Inactive"}
        if active:
            port = str(alarm.get("port") or "")
            if port in {"1", "2"}:
                states[port] = "Active"
            else:
                states["1"] = "Active"
                states["2"] = "Active"
        return states

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
                "description": source.get("description") or base.get("description") or description,
                "corrective_action": source.get("corrective_action") or base.get("corrective_action", action),
                "status": source.get("status", "Active"),
                "port": source.get("port", base.get("port")),
                "acknowledged": bool(source.get("acknowledged", False)),
            }
        return list(merged.values())

    def _refresh(self):
        self.safety_table.setRowCount(0)
        self.secs_table.setRowCount(0)
        for alarm in self._display_alarms():
            if self.active_only.isChecked() and alarm.get("status") != "Active":
                continue
            if alarm["category"] == "Safety":
                self._append_safety_row(alarm)
            else:
                self._append_secs_row(alarm)
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
        self.permission_note.setVisible(remote_blocked)
        if self.tabs.currentIndex() == 0 and self.safety_table.rowCount() and self.safety_table.currentRow() < 0:
            self.safety_table.selectRow(0)
        elif self.tabs.currentIndex() == 1 and self.secs_table.rowCount() and self.secs_table.currentRow() < 0:
            self.secs_table.selectRow(0)
        self._update_acknowledge_button()

    def _append_safety_row(self, alarm):
        table = self.safety_table
        row = table.rowCount()
        table.insertRow(row)
        table.setRowHeight(row, 24)
        name_item = QTableWidgetItem(alarm["name"])
        name_item.setData(Qt.UserRole, alarm)
        name_item.setForeground(QColor("#0000cc"))
        font = name_item.font()
        font.setUnderline(True)
        name_item.setFont(font)
        status_item = QTableWidgetItem("")
        status_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        table.setItem(row, 0, name_item)
        table.setItem(row, 1, status_item)
        table.setCellWidget(row, 1, self._status_cell(alarm.get("status") == "Active"))

    def _append_secs_row(self, alarm):
        table = self.secs_table
        row = table.rowCount()
        table.insertRow(row)
        table.setRowHeight(row, 22)
        name_item = QTableWidgetItem(alarm["name"])
        name_item.setData(Qt.UserRole, alarm)
        name_item.setForeground(QColor("#008080" if alarm.get("clearable") else "#0000cc"))
        name_item.setBackground(QColor("#f7f4ea"))
        font = name_item.font()
        font.setUnderline(True)
        name_item.setFont(font)
        table.setItem(row, 0, name_item)
        scopes = self._alarm_scopes(alarm)
        for column, key in ((1, "general"), (2, "1"), (3, "2")):
            status_item = QTableWidgetItem("")
            status_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            table.setItem(row, column, status_item)
            state = scopes[key]
            table.setCellWidget(row, column, self._status_cell(None if state is None else state == "Active"))

    def _show_details(self, table, row):
        item = table.item(row, 0) if row >= 0 else None
        alarm = item.data(Qt.UserRole) if item is not None else None
        if not isinstance(alarm, dict):
            return
        self.detail_title.setText(str(alarm.get("name", "")))
        self.description.setText(str(alarm.get("description", "")))
        self.corrective_action.setText(str(alarm.get("corrective_action", "")))
        self._update_acknowledge_button()

    def _selected_alarm(self):
        table = self.secs_table if self.tabs.currentIndex() == 1 else self.safety_table
        item = table.item(table.currentRow(), 0)
        alarm = item.data(Qt.UserRole) if item is not None else None
        return alarm if isinstance(alarm, dict) else None

    def _update_acknowledge_button(self):
        if not hasattr(self, "acknowledge_button"):
            return
        alarm = self._selected_alarm()
        self.acknowledge_button.setEnabled(
            isinstance(alarm, dict)
            and alarm.get("category") == "SECS"
            and alarm.get("status") == "Active"
            and not alarm.get("acknowledged")
        )

    def _acknowledge(self):
        alarm = self._selected_alarm()
        if not isinstance(alarm, dict) or alarm.get("status") != "Active":
            return
        for item in self.alarms:
            if item.get("name") == alarm.get("name") and item.get("category", "SECS") != "Safety":
                item["acknowledged"] = True
        self.result_alarms = self.alarms
        self._refresh()

    def _simulate(self):
        active_names = {
            item.get("name")
            for item in self.alarms
            if item.get("status") == "Active" and item.get("clearable", True)
        }
        choices = [name for name in CLEARABLE_SECS_ALARMS if name not in active_names]
        name = random.choice(choices or list(CLEARABLE_SECS_ALARMS))
        existing = next((item for item in self.alarms if item.get("name") == name), None)
        event = existing or {"name": name, "category": "SECS", "clearable": True}
        event.update({"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "status": "Active"})
        if existing is None:
            self.alarms.insert(0, event)
        self.result_alarms = self.alarms
        self.tabs.setCurrentIndex(1)
        self._refresh()
        for row in range(self.secs_table.rowCount()):
            item = self.secs_table.item(row, 0)
            if item is not None and item.text() == name:
                self.secs_table.selectRow(row)
                self.secs_table.scrollToItem(item)
                break

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

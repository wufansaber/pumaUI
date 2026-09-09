from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
import hashlib
import re
from uuid import uuid4

from ...qt_compat import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    Qt,
)


ACCESS_LEVELS = ("Operator", "Engineer", "Expert", "System Administrator")
EQUIPMENT_STATES = ("Error", "Maintenance", "Setup", "Idle", "Inspecting", "Lot Complete")
LIGHT_STATES = ("Off", "On", "Flash", "No Change")


def _password_hash(password: str) -> str:
    return hashlib.sha256(str(password).encode("utf-8")).hexdigest() if password else ""


def default_system_admin_state() -> dict:
    return {
        "e87_enabled": True,
        "e40_e94_enabled": True,
        "erc_catalog": [],
        "security": {
            "enabled": True,
            "current_user": "kttool",
            "inactivity_timeout_minutes": 0,
            "users": [{
                "username": "kttool",
                "domain": "Local",
                "access": "System Administrator",
                "password_hash": "",
                "windows_user": False,
            }],
            "privileges": {
                "Recipe Setup": "Engineer",
                "Run Inspection": "Operator",
                "System Utilities": "Expert",
                "Remote Mode Carrier Management": "Expert",
                "Remote Mode Carrier Tag Read Write Data": "Expert",
                "Remote Mode Clear Alarms": "Expert",
                "Data Transfer": "Engineer",
            },
        },
        "signal_tower": {
            "configuration_name": "SignalTowerDefault.xml",
            "default_configuration": "SignalTowerDefault.xml",
            "priority": list(EQUIPMENT_STATES),
            "light_order": ["Red", "Yellow", "Green", "Blue"],
            "states": {
                "Error": {"Red": "Flash", "Yellow": "Off", "Green": "Off", "Blue": "Off", "Buzzer": "On", "Duration": 0},
                "Maintenance": {"Red": "Off", "Yellow": "On", "Green": "Off", "Blue": "Off", "Buzzer": "Off", "Duration": 0},
                "Setup": {"Red": "Off", "Yellow": "On", "Green": "Off", "Blue": "Off", "Buzzer": "Off", "Duration": 0},
                "Idle": {"Red": "Off", "Yellow": "Off", "Green": "On", "Blue": "Off", "Buzzer": "Off", "Duration": 0},
                "Inspecting": {"Red": "Off", "Yellow": "Off", "Green": "On", "Blue": "On", "Buzzer": "Off", "Duration": 0},
                "Lot Complete": {"Red": "Off", "Yellow": "Off", "Green": "On", "Blue": "Off", "Buzzer": "On", "Duration": 5},
            },
            "control": {"Red": "Off", "Yellow": "Off", "Green": "On", "Blue": "Off", "Buzzer": "Off", "Duration": 0},
        },
        "load_port_indicators": {
            "enabled": True,
            "configuration_name": "IndicatorLightsCfgDefault.xml",
            "default_configuration": "IndicatorLightsCfgDefault.xml",
            "priority": ["Alarm", "Transfer", "Reservation", "Inspection", "Access"],
            "states": {
                "Alarm": ["Flash", "Off", "Off"],
                "Transfer": ["Off", "On", "Off"],
                "Reservation": ["Off", "Flash", "Off"],
                "Inspection": ["Off", "Off", "On"],
                "Access": ["Off", "Off", "Flash"],
            },
        },
        "e116_enabled": False,
        "user_preferences": {
            "coordinate_display": "Machine",
            "defect_color_scheme": "Standard",
            "navigation_bar": True,
            "named_settings": {},
        },
        "log_settings": {
            "general_target": "Track Current Flight Recorder",
            "general_file": "",
            "subsystem_logs": {
                name: {"enabled": False, "level": "Error"}
                for name in ("Wafer Handler", "Optics", "Inspection", "Data Transfer", "SECS")
            },
            "private_logs": {
                name: {"enabled": False, "level": "Error"}
                for name in ("EDM", "Diagnostics", "Performance")
            },
        },
        "disk_admin": {
            "schedule": "Never",
            "override_percent": 15,
            "delete_images": False,
            "image_days": 30,
            "delete_lots": False,
            "lot_days": 60,
            "last_run": "Never",
            "next_run": "Not scheduled",
        },
        "remote_tools": [],
        "last_backup": "Never",
        "last_archive": "Never",
        "last_restore": "Never",
        "e10_state": "Standby",
        "host_messages": [],
        "process_program_events": [],
    }


def normalized_system_admin_state(value=None) -> dict:
    result = default_system_admin_state()
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"security", "signal_tower", "load_port_indicators", "user_preferences", "log_settings", "disk_admin"} and isinstance(item, dict):
                result[key].update(deepcopy(item))
            else:
                result[key] = deepcopy(item)
    security = result["security"]
    security["users"] = [item for item in security.get("users", []) if isinstance(item, dict) and item.get("username")]
    if not security["users"]:
        security["users"] = deepcopy(default_system_admin_state()["security"]["users"])
    security["inactivity_timeout_minutes"] = max(0, min(1440, int(security.get("inactivity_timeout_minutes", 0))))
    disk = result["disk_admin"]
    disk["schedule"] = disk.get("schedule") if disk.get("schedule") in {"Daily", "Weekly", "Monthly", "Never"} else "Never"
    disk["override_percent"] = max(10, min(100, int(disk.get("override_percent", 15))))
    disk["image_days"] = max(1, min(365, int(disk.get("image_days", 30))))
    disk["lot_days"] = max(1, min(365, int(disk.get("lot_days", 60))))
    result["e10_state"] = result["e10_state"] if result["e10_state"] in {"Productive", "Standby", "Engineering", "Scheduled Downtime", "Unscheduled Downtime"} else "Standby"
    return result


def authenticate_user(state: dict, username: str, password: str) -> bool:
    security = normalized_system_admin_state(state)["security"]
    if not security["enabled"]:
        return True
    user = next((item for item in security["users"] if item.get("username") == username), None)
    if not user:
        return False
    expected = user.get("password_hash", "")
    return (not expected and not password) or expected == _password_hash(password)


def add_or_update_user(state: dict, username: str, password: str, access: str, *, domain="Local", windows_user=False) -> dict:
    username = str(username).strip()
    if not username:
        raise ValueError("Username is required")
    if len(str(password)) > 16:
        raise ValueError("Passwords are limited to 16 characters")
    if access not in ACCESS_LEVELS:
        raise ValueError("Select a valid access level")
    updated = normalized_system_admin_state(state)
    users = updated["security"]["users"]
    existing = next((item for item in users if item.get("username") == username), None)
    values = {
        "username": username,
        "domain": str(domain).strip() or "Local",
        "access": access,
        "password_hash": _password_hash(password),
        "windows_user": bool(windows_user),
    }
    if existing:
        if not password:
            values["password_hash"] = existing.get("password_hash", "")
        existing.update(values)
    else:
        users.append(values)
    return updated


def control_job_access(admin_state: dict, communication: dict, equipment_constants: dict) -> tuple[bool, str]:
    state = normalized_system_admin_state(admin_state)
    if not state["e87_enabled"] or not state["e40_e94_enabled"]:
        return False, "E87 and E40/E94 options must be installed and enabled"
    if not communication.get("secs_enabled") or communication.get("control_mode") != "Remote":
        return False, "SECS must be enabled in Online/Remote mode"
    if not equipment_constants.get("remote_job_commands", True):
        return False, "Remote Mode UI Control and Process Jobs is disabled"
    return True, "Control and Process Job commands are available"


def disk_admin_next_run(schedule: str, now=None) -> str:
    now = now or datetime.now()
    offsets = {"Daily": timedelta(days=1), "Weekly": timedelta(days=7), "Monthly": timedelta(days=30)}
    return (now + offsets[schedule]).strftime("%Y-%m-%d %H:%M:%S") if schedule in offsets else "Not scheduled"


class ERCManagerDialog(QDialog):
    def __init__(self, recipes, catalog=None, parent=None):
        super().__init__(parent)
        self.recipes = list(recipes)
        self.catalog = list(catalog or self._catalog_from_recipes())
        self.result_catalog = None
        self.deleted_count = 0
        self.setWindowTitle("ERC Deletion Utility")
        self.resize(820, 540)
        root = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(QLabel("Disk Usage"))
        top.addWidget(QLabel(f"{min(99, 42 + len(self.catalog))}%"))
        top.addStretch(1)
        self.mode = QComboBox()
        self.mode.addItems(["Auto Clean-up", "Manual Clean-up"])
        top.addWidget(QLabel("Cleanup Mode"))
        top.addWidget(self.mode)
        root.addLayout(top)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Delete", "Recipe", "ERC", "Valid Recipe Reference", "Size (MB)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        root.addWidget(self.table, 1)
        self._refresh()
        buttons = QHBoxLayout()
        select_all = QCheckBox("Select All")
        select_all.toggled.connect(self._select_all)
        delete = QPushButton("Delete")
        delete.clicked.connect(self._cleanup)
        buttons.addWidget(select_all)
        buttons.addWidget(delete)
        buttons.addStretch(1)
        close = QPushButton("Close")
        close.clicked.connect(self._finish)
        buttons.addWidget(close)
        root.addLayout(buttons)

    def _catalog_from_recipes(self):
        return [{"id": uuid4().hex, "recipe_id": item.get("id", ""), "recipe": item.get("inspection", ""), "name": f"{item.get('inspection', 'Recipe')}.erc", "valid_reference": item.get("status") == "Valid", "size_mb": 8 + index * 3} for index, item in enumerate(self.recipes)]

    def _refresh(self):
        self.table.setRowCount(len(self.catalog))
        for row, item in enumerate(self.catalog):
            check = QTableWidgetItem("")
            check.setFlags(check.flags() | Qt.ItemIsUserCheckable)
            check.setCheckState(Qt.Unchecked)
            self.table.setItem(row, 0, check)
            for column, value in enumerate((item.get("recipe"), item.get("name"), "Yes" if item.get("valid_reference") else "No", item.get("size_mb", 0)), 1):
                cell = QTableWidgetItem(str(value))
                cell.setFlags(cell.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, column, cell)

    def _select_all(self, checked):
        for row in range(self.table.rowCount()):
            self.table.item(row, 0).setCheckState(Qt.Checked if checked else Qt.Unchecked)

    def _cleanup(self):
        if self.mode.currentText() == "Auto Clean-up":
            removed = [item for item in self.catalog if not item.get("valid_reference")]
            self.catalog = [item for item in self.catalog if item.get("valid_reference")]
        else:
            selected = {self.catalog[row]["id"] for row in range(self.table.rowCount()) if self.table.item(row, 0).checkState() == Qt.Checked}
            removed = [item for item in self.catalog if item.get("id") in selected]
            self.catalog = [item for item in self.catalog if item.get("id") not in selected]
        self.deleted_count += len(removed)
        self._refresh()

    def _finish(self):
        self.result_catalog = deepcopy(self.catalog)
        self.accept()


class ControlJobManagementDialog(QDialog):
    def __init__(self, jobs, enabled=True, reason="", parent=None):
        super().__init__(parent)
        self.jobs = deepcopy(list(jobs))
        self.result_jobs = None
        self.enabled = enabled
        self.setWindowTitle("Control Job and Process Job Management")
        self.resize(940, 560)
        root = QVBoxLayout(self)
        status = QLabel(reason)
        status.setStyleSheet(f"color: {'#176b2c' if enabled else '#a41515'}; font-weight: bold;")
        root.addWidget(status)
        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)
        self.control_table = self._table(["Control Job", "Lot", "Carrier", "Status", "Order"])
        self.process_table = self._table(["Process Job", "Inspection", "Wafer", "Status", "Control Job"])
        self.tabs.addTab(self.control_table, "Control Jobs")
        self.tabs.addTab(self.process_table, "Process Jobs")
        actions = QHBoxLayout()
        for name in ("Start", "Stop", "Cancel", "Pause", "Resume", "Move Up", "Move Down"):
            button = QPushButton(name)
            button.setEnabled(enabled)
            button.clicked.connect(lambda checked=False, action=name: self._operate(action))
            actions.addWidget(button)
        actions.addStretch(1)
        close = QPushButton("Close")
        close.clicked.connect(self._finish)
        actions.addWidget(close)
        root.addLayout(actions)
        self._refresh()

    @staticmethod
    def _table(headers):
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        return table

    def _refresh(self):
        self.control_table.setRowCount(len(self.jobs))
        for row, job in enumerate(self.jobs):
            values = (job.get("id", "")[:8], job.get("lot_id", ""), job.get("cassette", ""), job.get("status", ""), row + 1)
            for column, value in enumerate(values):
                self.control_table.setItem(row, column, QTableWidgetItem(str(value)))
        process = [(job, plan) for job in self.jobs for plan in (job.get("slot_plans") or [{"wafer_id": "", "inspection_ids": job.get("inspection_ids", [])}])]
        self.process_table.setRowCount(len(process))
        for row, (job, plan) in enumerate(process):
            values = (f"PJ-{row + 1:03d}", job.get("inspection", ""), plan.get("wafer_id", ""), job.get("status", ""), job.get("id", "")[:8])
            for column, value in enumerate(values):
                self.process_table.setItem(row, column, QTableWidgetItem(str(value)))

    def _operate(self, action):
        rows = self.control_table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        if action == "Move Up" and row > 0:
            self.jobs[row - 1], self.jobs[row] = self.jobs[row], self.jobs[row - 1]
        elif action == "Move Down" and row + 1 < len(self.jobs):
            self.jobs[row + 1], self.jobs[row] = self.jobs[row], self.jobs[row + 1]
        else:
            self.jobs[row]["status"] = {"Start": "Running", "Stop": "Stopped", "Cancel": "Cancelled", "Pause": "Paused", "Resume": "Running"}.get(action, self.jobs[row].get("status"))
        self._refresh()
        self.control_table.selectRow(max(0, min(row, len(self.jobs) - 1)))

    def _finish(self):
        self.result_jobs = deepcopy(self.jobs)
        self.accept()


class SubstrateTrackingDialog(QDialog):
    def __init__(self, runtime_state, enabled=True, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Substrate Tracking Information")
        self.resize(760, 450)
        root = QVBoxLayout(self)
        root.addWidget(QLabel("SEMI E90 substrate state display (simulated)" if enabled else "E87 is not enabled; substrate tracking is unavailable."))
        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(["Substrate", "Location", "State", "Port", "Slot"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        entries = []
        for port, slot in sorted((runtime_state.get("selected_slots") or {}).items()):
            if slot:
                entries.append((f"P{port}-S{slot:02d}", "Stage" if runtime_state.get("wafer_loaded") and port == runtime_state.get("selected_port") else f"Load Port {port}", "At Work" if runtime_state.get("wafer_loaded") else "At Source", port, slot))
        table.setRowCount(len(entries))
        for row, values in enumerate(entries):
            for column, value in enumerate(values):
                table.setItem(row, column, QTableWidgetItem(str(value)))
        root.addWidget(table, 1)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        footer = QHBoxLayout(); footer.addStretch(1); footer.addWidget(close); root.addLayout(footer)


class CarrierManagementDialog(QDialog):
    def __init__(self, runtime_state, enabled=True, parent=None):
        super().__init__(parent)
        self.state = deepcopy(runtime_state)
        self.result_state = None
        self.enabled = enabled
        self.setWindowTitle("Carrier Management - Remote Mode")
        self.resize(860, 560)
        root = QVBoxLayout(self)
        root.addWidget(QLabel("SEMI E87 Carrier Management (simulated)" if enabled else "E87 option is disabled; only state displays and tag data are available."))
        self.tabs = QTabWidget(); root.addWidget(self.tabs, 1)
        self.commands = QWidget(); command_layout = QGridLayout(self.commands)
        self.port = QComboBox(); self.port.addItems(["Port 1", "Port 2", "Port 3"])
        self.carrier_id = QLineEdit("CARRIER-001")
        command_layout.addWidget(QLabel("Load Port"), 0, 0); command_layout.addWidget(self.port, 0, 1)
        command_layout.addWidget(QLabel("Carrier ID"), 1, 0); command_layout.addWidget(self.carrier_id, 1, 1)
        for index, name in enumerate(("Bind Carrier", "Cancel Bind", "Carrier Notification", "Proceed", "Cancel Carrier", "Release Carrier", "ReCreate")):
            button = QPushButton(name); button.setEnabled(enabled); button.clicked.connect(lambda checked=False, action=name: self._command(action)); command_layout.addWidget(button, 2 + index // 3, index % 3)
        self.command_status = QLabel("Ready"); command_layout.addWidget(self.command_status, 5, 0, 1, 3)
        self.tabs.addTab(self.commands, "Carrier Commands")
        states = QTableWidget(3, 5); states.setHorizontalHeaderLabels(["Port", "Transfer State", "Access Mode", "Carrier", "Slot Map"]); states.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for row in range(3):
            loaded = bool((self.state.get("carrier_loaded") or {}).get(row + 1, False))
            for column, value in enumerate((row + 1, "Transfer Blocked" if loaded else "Ready To Load", "Manual", self.carrier_id.text() if loaded else "", "Mapped" if loaded else "Unknown")):
                states.setItem(row, column, QTableWidgetItem(str(value)))
        self.tabs.addTab(states, "Load Port States")
        tag = QWidget(); tag_layout = QGridLayout(tag); self.tag_key = QLineEdit("LotID"); self.tag_value = QLineEdit(); tag_layout.addWidget(QLabel("Tag"), 0, 0); tag_layout.addWidget(self.tag_key, 0, 1); tag_layout.addWidget(QLabel("Data"), 1, 0); tag_layout.addWidget(self.tag_value, 1, 1); self.tabs.addTab(tag, "Carrier Tag Commands")
        close = QPushButton("Close"); close.clicked.connect(self._finish); footer = QHBoxLayout(); footer.addStretch(1); footer.addWidget(close); root.addLayout(footer)

    def _command(self, action):
        port = self.port.currentIndex() + 1
        if action == "Bind Carrier":
            self.state.setdefault("carrier_loaded", {})[port] = True
        elif action in {"Release Carrier", "Cancel Carrier", "Cancel Bind"}:
            self.state.setdefault("carrier_loaded", {})[port] = False
        self.command_status.setText(f"{action} completed for Port {port} (simulated)")

    def _finish(self):
        self.result_state = deepcopy(self.state)
        self.accept()


class UserAdministrationDialog(QDialog):
    def __init__(self, admin_state=None, parent=None):
        super().__init__(parent)
        self.state = normalized_system_admin_state(admin_state)
        self.result_state = None
        self.setWindowTitle("User Administration")
        self.resize(900, 590)
        root = QVBoxLayout(self)
        top = QHBoxLayout()
        self.enabled = QCheckBox("Enable Security"); self.enabled.setChecked(self.state["security"]["enabled"]); top.addWidget(self.enabled)
        top.addStretch(1); top.addWidget(QLabel("Inactivity Timeout (minutes)")); self.timeout = QSpinBox(); self.timeout.setRange(0, 1440); self.timeout.setValue(self.state["security"]["inactivity_timeout_minutes"]); top.addWidget(self.timeout); root.addLayout(top)
        self.tabs = QTabWidget(); root.addWidget(self.tabs, 1)
        users = QWidget(); users_layout = QVBoxLayout(users)
        self.user_table = QTableWidget(0, 4); self.user_table.setHorizontalHeaderLabels(["Username", "Domain", "Access Level", "Type"]); self.user_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); users_layout.addWidget(self.user_table, 1)
        form = QHBoxLayout(); self.username = QLineEdit(); self.username.setPlaceholderText("Username"); self.password = QLineEdit(); self.password.setPlaceholderText("Password (max 16)"); self.password.setEchoMode(QLineEdit.Password); self.domain = QLineEdit("Local"); self.access = QComboBox(); self.access.addItems(ACCESS_LEVELS); form.addWidget(self.username); form.addWidget(self.password); form.addWidget(self.domain); form.addWidget(self.access); users_layout.addLayout(form)
        user_buttons = QHBoxLayout(); add = QPushButton("Create / Update User"); add.clicked.connect(self._add_user); delete = QPushButton("Delete User"); delete.clicked.connect(self._delete_user); user_buttons.addWidget(add); user_buttons.addWidget(delete); user_buttons.addStretch(1); users_layout.addLayout(user_buttons); self.tabs.addTab(users, "User Administration")
        privileges = QWidget(); privilege_layout = QGridLayout(privileges); self.privilege_controls = {}
        for row, (operation, access) in enumerate(self.state["security"]["privileges"].items()):
            combo = QComboBox(); combo.addItems(ACCESS_LEVELS); combo.setCurrentText(access); privilege_layout.addWidget(QLabel(operation), row, 0); privilege_layout.addWidget(combo, row, 1); self.privilege_controls[operation] = combo
        privilege_layout.setRowStretch(len(self.privilege_controls), 1); self.tabs.addTab(privileges, "Group Administration")
        footer = QHBoxLayout(); footer.addStretch(1); ok = QPushButton("OK"); ok.clicked.connect(self._finish); cancel = QPushButton("Cancel"); cancel.clicked.connect(self.reject); footer.addWidget(ok); footer.addWidget(cancel); root.addLayout(footer); self._refresh_users()

    def _refresh_users(self):
        users = self.state["security"]["users"]; self.user_table.setRowCount(len(users))
        for row, user in enumerate(users):
            for column, value in enumerate((user.get("username"), user.get("domain"), user.get("access"), "Windows" if user.get("windows_user") else "Local")):
                self.user_table.setItem(row, column, QTableWidgetItem(str(value)))

    def _add_user(self):
        try:
            self.state = add_or_update_user(self.state, self.username.text(), self.password.text(), self.access.currentText(), domain=self.domain.text())
        except ValueError as exc:
            QMessageBox.warning(self, "User Administration", str(exc)); return
        self.password.clear(); self._refresh_users()

    def _delete_user(self):
        rows = self.user_table.selectionModel().selectedRows()
        if not rows: return
        username = self.state["security"]["users"][rows[0].row()]["username"]
        if username == "kttool":
            QMessageBox.warning(self, "User Administration", "The initial System Administrator cannot be deleted."); return
        self.state["security"]["users"] = [item for item in self.state["security"]["users"] if item.get("username") != username]; self._refresh_users()

    def _finish(self):
        self.state["security"]["enabled"] = self.enabled.isChecked(); self.state["security"]["inactivity_timeout_minutes"] = self.timeout.value(); self.state["security"]["privileges"] = {name: combo.currentText() for name, combo in self.privilege_controls.items()}; self.result_state = normalized_system_admin_state(self.state); self.accept()


class SignalTowerDialog(QDialog):
    def __init__(self, admin_state=None, control_only=False, parent=None):
        super().__init__(parent)
        self.state = normalized_system_admin_state(admin_state)
        self.result_state = None
        self.control_only = control_only
        self.setWindowTitle("Signal Tower Control" if control_only else "Signal Tower Software Configuration")
        self.resize(900, 590)
        root = QVBoxLayout(self)
        self.tabs = QTabWidget(); root.addWidget(self.tabs, 1)
        self.state_controls = {}
        config = QWidget(); grid = QGridLayout(config); headers = ("State", "Red", "Yellow", "Green", "Blue", "Buzzer", "Duration")
        for column, header in enumerate(headers): grid.addWidget(QLabel(header), 0, column)
        source = {"Manual Control": self.state["signal_tower"]["control"]} if control_only else self.state["signal_tower"]["states"]
        for row, (name, values) in enumerate(source.items(), 1):
            grid.addWidget(QLabel(name), row, 0); controls = {}
            for column, light in enumerate(("Red", "Yellow", "Green", "Blue"), 1):
                combo = QComboBox(); combo.addItems(LIGHT_STATES); combo.setCurrentText(values.get(light, "Off")); grid.addWidget(combo, row, column); controls[light] = combo
            buzzer = QComboBox(); buzzer.addItems(["Off", "On", "No Change"]); buzzer.setCurrentText(values.get("Buzzer", "Off")); grid.addWidget(buzzer, row, 5); controls["Buzzer"] = buzzer
            duration = QSpinBox(); duration.setRange(0, 3600); duration.setValue(int(values.get("Duration", 0))); grid.addWidget(duration, row, 6); controls["Duration"] = duration; self.state_controls[name] = controls
        grid.setAlignment(Qt.AlignTop)
        grid.setRowStretch(len(source) + 1, 1)
        self.tabs.addTab(config, "Control" if control_only else "Equipment State Configuration")
        if not control_only:
            priority = QListWidget(); priority.addItems(self.state["signal_tower"]["priority"]); priority.setDragDropMode(QAbstractItemView.InternalMove); self.priority = priority; self.tabs.addTab(priority, "Equipment State Priority")
            order = QListWidget(); order.addItems(self.state["signal_tower"]["light_order"]); order.setDragDropMode(QAbstractItemView.InternalMove); self.light_order = order; self.tabs.addTab(order, "Signal Tower Light Order")
        footer = QHBoxLayout(); footer.addStretch(1); apply = QPushButton("Apply"); apply.clicked.connect(self._finish); cancel = QPushButton("Cancel"); cancel.clicked.connect(self.reject); footer.addWidget(apply); footer.addWidget(cancel); root.addLayout(footer)

    def _finish(self):
        target = self.state["signal_tower"]["control"] if self.control_only else self.state["signal_tower"]["states"]
        for name, controls in self.state_controls.items():
            values = {key: control.value() if key == "Duration" else control.currentText() for key, control in controls.items()}
            if self.control_only: target.update(values)
            else: target[name] = values
        if not self.control_only:
            self.state["signal_tower"]["priority"] = [self.priority.item(index).text() for index in range(self.priority.count())]
            self.state["signal_tower"]["light_order"] = [self.light_order.item(index).text() for index in range(self.light_order.count())]
        self.result_state = normalized_system_admin_state(self.state); self.accept()


class LoadPortIndicatorDialog(QDialog):
    def __init__(self, admin_state=None, parent=None):
        super().__init__(parent)
        self.state = normalized_system_admin_state(admin_state); self.result_state = None; data = self.state["load_port_indicators"]
        self.setWindowTitle("Load Port Indicator Lights Configuration Editor"); self.resize(780, 520); root = QVBoxLayout(self)
        self.enabled = QCheckBox("Load Port Indicator Lights enabled (300 mm Asyst SMIF Series 3)"); self.enabled.setChecked(data["enabled"]); root.addWidget(self.enabled)
        self.tabs = QTabWidget(); root.addWidget(self.tabs, 1); table_page = QWidget(); grid = QGridLayout(table_page)
        for column, header in enumerate(("Equipment State", "Light 1", "Light 2", "Light 3")): grid.addWidget(QLabel(header), 0, column)
        self.controls = {}
        for row, (name, values) in enumerate(data["states"].items(), 1):
            grid.addWidget(QLabel(name), row, 0); combos=[]
            for column in range(3):
                combo=QComboBox(); combo.addItems(LIGHT_STATES); combo.setCurrentText(values[column]); grid.addWidget(combo,row,column+1); combos.append(combo)
            self.controls[name]=combos
        self.tabs.addTab(table_page,"State Configuration"); self.priority=QListWidget(); self.priority.addItems(data["priority"]); self.priority.setDragDropMode(QAbstractItemView.InternalMove); self.tabs.addTab(self.priority,"State Priority")
        footer=QHBoxLayout(); footer.addStretch(1); ok=QPushButton("Save"); ok.clicked.connect(self._finish); cancel=QPushButton("Close"); cancel.clicked.connect(self.reject); footer.addWidget(ok); footer.addWidget(cancel); root.addLayout(footer)

    def _finish(self):
        data=self.state["load_port_indicators"]; data["enabled"]=self.enabled.isChecked(); data["states"]={name:[combo.currentText() for combo in controls] for name,controls in self.controls.items()}; data["priority"]=[self.priority.item(i).text() for i in range(self.priority.count())]; self.result_state=normalized_system_admin_state(self.state); self.accept()


class UserPreferencesDialog(QDialog):
    def __init__(self, admin_state=None, parent=None):
        super().__init__(parent); self.state=normalized_system_admin_state(admin_state); self.result_state=None; prefs=self.state["user_preferences"]
        self.setWindowTitle("User Preferences"); self.resize(620,410); root=QVBoxLayout(self); form=QGridLayout()
        self.coordinate=QComboBox(); self.coordinate.addItems(["Machine","Cartesian","Raster"]); self.coordinate.setCurrentText(prefs["coordinate_display"])
        self.colors=QComboBox(); self.colors.addItems(["Standard","InLine ADC"]); self.colors.setCurrentText(prefs["defect_color_scheme"])
        self.navigation=QCheckBox("Show Navigation Bar"); self.navigation.setChecked(prefs["navigation_bar"])
        form.addWidget(QLabel("Review Coordinate Display"),0,0); form.addWidget(self.coordinate,0,1); form.addWidget(QLabel("Defect Display Color Scheme"),1,0); form.addWidget(self.colors,1,1); form.addWidget(self.navigation,2,0,1,2); root.addLayout(form); root.addStretch(1)
        footer=QHBoxLayout(); footer.addStretch(1); ok=QPushButton("OK"); ok.clicked.connect(self._finish); cancel=QPushButton("Cancel"); cancel.clicked.connect(self.reject); footer.addWidget(ok); footer.addWidget(cancel); root.addLayout(footer)
    def _finish(self):
        prefs=self.state["user_preferences"]; prefs.update({"coordinate_display":self.coordinate.currentText(),"defect_color_scheme":self.colors.currentText(),"navigation_bar":self.navigation.isChecked()}); self.result_state=normalized_system_admin_state(self.state); self.accept()


class LogSettingsDialog(QDialog):
    def __init__(self, admin_state=None, parent=None):
        super().__init__(parent); self.state=normalized_system_admin_state(admin_state); self.result_state=None; logs=self.state["log_settings"]
        self.setWindowTitle("KLA-Tencor Logger Configuration Editor"); self.resize(800,540); root=QVBoxLayout(self); self.tabs=QTabWidget(); root.addWidget(self.tabs,1)
        general=QWidget(); general_layout=QGridLayout(general); self.general_target=QComboBox(); self.general_target.addItems(["Track Current Flight Recorder","Track Any Log File"]); self.general_target.setCurrentText(logs["general_target"]); self.general_file=QLineEdit(logs["general_file"]); general_layout.addWidget(QLabel("Diagnostics Output"),0,0); general_layout.addWidget(self.general_target,0,1); general_layout.addWidget(QLabel("Log File"),1,0); general_layout.addWidget(self.general_file,1,1); self.tabs.addTab(general,"General Logs")
        self.log_controls={}
        for key,label in (("subsystem_logs","Subsystem Logs"),("private_logs","Private Logs")):
            page=QWidget(); grid=QGridLayout(page); grid.addWidget(QLabel("Log"),0,0); grid.addWidget(QLabel("Status"),0,1); grid.addWidget(QLabel("Level"),0,2); controls={}
            for row,(name,settings) in enumerate(logs[key].items(),1):
                enabled=QCheckBox("Enabled"); enabled.setChecked(settings["enabled"]); level=QComboBox(); level.addItems(["Error","Warning","Informational","Debug"]); level.setCurrentText(settings["level"]); grid.addWidget(QLabel(name),row,0); grid.addWidget(enabled,row,1); grid.addWidget(level,row,2); controls[name]=(enabled,level)
            self.log_controls[key]=controls; self.tabs.addTab(page,label)
        footer=QHBoxLayout(); footer.addStretch(1); ok=QPushButton("OK"); ok.clicked.connect(self._finish); cancel=QPushButton("Cancel"); cancel.clicked.connect(self.reject); footer.addWidget(ok); footer.addWidget(cancel); root.addLayout(footer)
    def _finish(self):
        logs=self.state["log_settings"]; logs["general_target"]=self.general_target.currentText(); logs["general_file"]=self.general_file.text().strip()
        for key,controls in self.log_controls.items(): logs[key]={name:{"enabled":enabled.isChecked(),"level":level.currentText()} for name,(enabled,level) in controls.items()}
        self.result_state=normalized_system_admin_state(self.state); self.accept()


class DiskAdminDialog(QDialog):
    def __init__(self, admin_state=None, parent=None):
        super().__init__(parent); self.state=normalized_system_admin_state(admin_state); self.result_state=None; self.run_now=False; disk=self.state["disk_admin"]
        self.setWindowTitle("Disk Admin"); self.resize(620,450); root=QVBoxLayout(self); form=QGridLayout(); self.schedule=QComboBox(); self.schedule.addItems(["Never","Daily","Weekly","Monthly"]); self.schedule.setCurrentText(disk["schedule"]); self.override=QSpinBox(); self.override.setRange(10,100); self.override.setSuffix(" %"); self.override.setValue(disk["override_percent"]); self.delete_images=QCheckBox("Delete Images older than"); self.delete_images.setChecked(disk["delete_images"]); self.image_days=QSpinBox(); self.image_days.setRange(1,365); self.image_days.setSuffix(" days"); self.image_days.setValue(disk["image_days"]); self.delete_lots=QCheckBox("Delete Lots older than"); self.delete_lots.setChecked(disk["delete_lots"]); self.lot_days=QSpinBox(); self.lot_days.setRange(1,365); self.lot_days.setSuffix(" days"); self.lot_days.setValue(disk["lot_days"])
        rows=(("Perform this Task",self.schedule),("Override schedule below free space",self.override),(self.delete_images,self.image_days),(self.delete_lots,self.lot_days));
        for row,(label,control) in enumerate(rows): form.addWidget(label if isinstance(label,QWidget) else QLabel(label),row,0); form.addWidget(control,row,1)
        root.addLayout(form); root.addWidget(QLabel(f"Last Run: {disk['last_run']}\nNext Run: {disk['next_run']}")); root.addStretch(1); footer=QHBoxLayout(); run=QPushButton("Run Now"); run.clicked.connect(self._run); footer.addWidget(run); footer.addStretch(1); ok=QPushButton("OK"); ok.clicked.connect(self._finish); cancel=QPushButton("Cancel"); cancel.clicked.connect(self.reject); footer.addWidget(ok); footer.addWidget(cancel); root.addLayout(footer)
    def _values(self):
        disk=self.state["disk_admin"]; disk.update({"schedule":self.schedule.currentText(),"override_percent":self.override.value(),"delete_images":self.delete_images.isChecked(),"image_days":self.image_days.value(),"delete_lots":self.delete_lots.isChecked(),"lot_days":self.lot_days.value(),"next_run":disk_admin_next_run(self.schedule.currentText())})
    def _run(self): self._values(); self.run_now=True; self.state["disk_admin"]["last_run"]=datetime.now().strftime("%Y-%m-%d %H:%M:%S"); self._finish()
    def _finish(self): self._values(); self.result_state=normalized_system_admin_state(self.state); self.accept()


class ToolsConfigurationDialog(QDialog):
    def __init__(self, admin_state=None, parent=None):
        super().__init__(parent); self.state=normalized_system_admin_state(admin_state); self.result_state=None; self.setWindowTitle("Remote Tool List"); self.resize(760,480); root=QVBoxLayout(self); self.table=QTableWidget(0,4); self.table.setHorizontalHeaderLabels(["Tool Name","Serial No","Station ID","Data Directory"]); self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); root.addWidget(self.table,1); form=QHBoxLayout(); self.name=QLineEdit(); self.name.setPlaceholderText("Tool Name"); self.serial=QLineEdit(); self.serial.setPlaceholderText("Serial No"); self.station=QLineEdit(); self.station.setPlaceholderText("Station ID"); self.directory=QLineEdit(); self.directory.setPlaceholderText("Mapped data directory"); form.addWidget(self.name); form.addWidget(self.serial); form.addWidget(self.station); form.addWidget(self.directory); root.addLayout(form); footer=QHBoxLayout(); add=QPushButton("Add"); add.clicked.connect(self._add); remove=QPushButton("Remove"); remove.clicked.connect(self._remove); footer.addWidget(add); footer.addWidget(remove); footer.addStretch(1); close=QPushButton("Close"); close.clicked.connect(self._finish); footer.addWidget(close); root.addLayout(footer); self._refresh()
    def _refresh(self):
        tools=self.state["remote_tools"]; self.table.setRowCount(len(tools));
        for row,tool in enumerate(tools):
            for column,value in enumerate((tool.get("name"),tool.get("serial"),tool.get("station_id"),tool.get("directory"))): self.table.setItem(row,column,QTableWidgetItem(str(value)))
    def _add(self):
        if not self.name.text().strip() or not self.serial.text().strip(): QMessageBox.warning(self,"Tool Properties","Tool Name and Serial No are required."); return
        self.state["remote_tools"].append({"id":uuid4().hex,"name":self.name.text().strip(),"serial":self.serial.text().strip(),"station_id":self.station.text().strip() or self.serial.text().strip(),"directory":self.directory.text().strip()}); self._refresh()
    def _remove(self):
        rows=self.table.selectionModel().selectedRows();
        if rows: self.state["remote_tools"].pop(rows[0].row()); self._refresh()
    def _finish(self): self.result_state=normalized_system_admin_state(self.state); self.accept()


class BackupArchiveRestoreDialog(QDialog):
    def __init__(self, admin_state=None, parent=None):
        super().__init__(parent); self.state=normalized_system_admin_state(admin_state); self.result_state=None; self.result_action=""; self.setWindowTitle("Backup / Archive / Restore"); self.resize(620,360); root=QVBoxLayout(self); root.addWidget(QLabel("Configuration and recipe data operations are simulated locally. No system drive is modified.")); self.status=QLabel(f"Last Backup: {self.state['last_backup']}\nLast Archive: {self.state['last_archive']}\nLast Restore: {self.state['last_restore']}"); root.addWidget(self.status); root.addStretch(1); buttons=QHBoxLayout()
        for action in ("Backup","Archive","Restore"):
            button=QPushButton(action); button.clicked.connect(lambda checked=False,value=action:self._choose(value)); buttons.addWidget(button)
        buttons.addStretch(1); close=QPushButton("Close"); close.clicked.connect(self.reject); buttons.addWidget(close); root.addLayout(buttons)
    def _choose(self,action):
        key=f"last_{action.lower()}"; self.state[key]=datetime.now().strftime("%Y-%m-%d %H:%M:%S"); self.result_action=action; self.result_state=normalized_system_admin_state(self.state); self.accept()


class SecsOperationsDialog(QDialog):
    def __init__(self, admin_state=None, recipes=None, parent=None):
        super().__init__(parent); self.state=normalized_system_admin_state(admin_state); self.recipes=list(recipes or []); self.result_state=None; self.setWindowTitle("SECS Operations"); self.resize(720,500); root=QVBoxLayout(self); self.tabs=QTabWidget(); root.addWidget(self.tabs,1)
        e10=QWidget(); e10_layout=QGridLayout(e10); self.e10=QComboBox(); self.e10.addItems(["Productive","Standby","Engineering","Scheduled Downtime","Unscheduled Downtime"]); self.e10.setCurrentText(self.state["e10_state"]); e10_layout.addWidget(QLabel("Current E10 State"),0,0); e10_layout.addWidget(self.e10,0,1); self.tabs.addTab(e10,"E10 State")
        host=QWidget(); host_layout=QVBoxLayout(host); self.message=QLineEdit(); self.message.setMaxLength(160); self.message.setPlaceholderText("Alphanumeric host message, maximum 160 characters"); host_layout.addWidget(self.message); self.tabs.addTab(host,"Send Message to Host")
        programs=QWidget(); program_layout=QGridLayout(programs); self.program=QComboBox(); self.program.addItems([item.get("inspection","") for item in self.recipes]); self.direction=QComboBox(); self.direction.addItems(["Upload to Host","Download from Host"]); program_layout.addWidget(QLabel("Process Program"),0,0); program_layout.addWidget(self.program,0,1); program_layout.addWidget(QLabel("Direction"),1,0); program_layout.addWidget(self.direction,1,1); self.tabs.addTab(programs,"Process Program Transfer")
        footer=QHBoxLayout(); sync=QPushButton("Synchronize Clock"); sync.clicked.connect(lambda:self._event("Clock synchronized with simulated host")); send=QPushButton("Apply / Send"); send.clicked.connect(self._finish); footer.addWidget(sync); footer.addStretch(1); footer.addWidget(send); cancel=QPushButton("Cancel"); cancel.clicked.connect(self.reject); footer.addWidget(cancel); root.addLayout(footer)
    def _event(self,text): self.state.setdefault("host_messages",[]).append({"time":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"message":text})
    def _finish(self):
        self.state["e10_state"]=self.e10.currentText(); message=self.message.text().strip()
        if message:
            if not re.fullmatch(r"[A-Za-z0-9 .,;:_/+\-()]*",message): QMessageBox.warning(self,"Send Host Message","Use alphanumeric text and basic punctuation only."); return
            self._event(message)
        if self.program.currentText(): self.state.setdefault("process_program_events",[]).append({"program":self.program.currentText(),"direction":self.direction.currentText(),"time":datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        self.result_state=normalized_system_admin_state(self.state); self.accept()

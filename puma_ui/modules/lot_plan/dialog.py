from __future__ import annotations

from copy import deepcopy

from ...qt_compat import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
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
    Qt,
    QVBoxLayout,
)


def default_lot_plan_state(test_names=None) -> dict:
    names = list(test_names or [])
    return {
        "mode": "Lot Mode",
        "slot_count": 25,
        "test_names": names,
        "assignments": {},
        "repeat_enabled": False,
        "repeat_counts": {},
        "unload_wafer_in_repeat_mode": False,
        "protect": False,
        "backup_lot_result": False,
        "cache_lot_result": False,
        "transfer_host": "",
        "transfer_share": "ImpactDataTemp",
        "tool_type": "9xxx",
    }


def normalized_lot_plan_state(state: dict | None, test_names=None) -> dict:
    names = list(test_names or [])
    result = default_lot_plan_state(names)
    if isinstance(state, dict):
        result.update(deepcopy(state))
    result["test_names"] = names
    result["assignments"] = deepcopy(result.get("assignments") or {})
    result["repeat_counts"] = deepcopy(result.get("repeat_counts") or {})
    valid = set(names)
    result["assignments"] = {
        str(slot): [name for name in assigned if name in valid]
        for slot, assigned in result["assignments"].items()
        if str(slot).isdigit() and 1 <= int(slot) <= int(result["slot_count"])
    }
    repeat_counts = {}
    for key, count in result["repeat_counts"].items():
        try:
            slot, name = str(key).split(":", 1)
            numeric = int(count)
        except (TypeError, ValueError):
            continue
        if name in result["assignments"].get(slot, []):
            repeat_counts[f"{slot}:{name}"] = numeric
    result["repeat_counts"] = repeat_counts
    return result


def validate_lot_plan(state: dict) -> list[str]:
    errors = []
    assigned = sum(len(names) for names in state.get("assignments", {}).values())
    if assigned == 0:
        errors.append("no tests are assigned to wafer slots")
    if state.get("repeat_enabled"):
        for key, count in state.get("repeat_counts", {}).items():
            if int(count) < 1 or int(count) > 999:
                errors.append(f"{key}: repeat count must be between 1 and 999")
    if state.get("cache_lot_result") and not state.get("transfer_host", "").strip():
        errors.append("lot result transfer host is required when caching is enabled")
    if state.get("cache_lot_result") and not state.get("transfer_share", "").strip():
        errors.append("lot result transfer share is required when caching is enabled")
    if state.get("cache_lot_result") and not state.get("tool_type", "").strip():
        errors.append("tool type is required when caching is enabled")
    return errors


def lot_plan_runtime_permissions(state: dict | None, runtime_mode: bool = False) -> dict[str, bool]:
    """Return the Lot Plan controls that may be edited in the current context."""
    if not runtime_mode or not bool((state or {}).get("protect")):
        return {"assignments": True, "settings": True, "repeat_count": True}
    return {
        "assignments": False,
        "settings": False,
        "repeat_count": bool((state or {}).get("repeat_enabled")),
    }


class LotPlanAdvancedOptionsDialog(QDialog):
    def __init__(self, unload_wafer=False, parent=None):
        super().__init__(parent)
        self.result_unload_wafer = None
        self.setWindowTitle("Advanced Options")
        self.setMinimumWidth(430)
        root = QVBoxLayout(self)
        self.unload_wafer = QCheckBox("Unload Wafer in Repeat Mode")
        self.unload_wafer.setChecked(bool(unload_wafer))
        root.addWidget(self.unload_wafer)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        ok = QPushButton("OK")
        ok.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        root.addLayout(buttons)

    def _finish(self):
        self.result_unload_wafer = self.unload_wafer.isChecked()
        self.accept()


class LotPlanDialog(QDialog):
    def __init__(self, test_names, state=None, parent=None, *, runtime_mode=False):
        super().__init__(parent)
        self.state = normalized_lot_plan_state(state, test_names)
        self.runtime_mode = bool(runtime_mode)
        self.result_state = None
        self.changed = False
        self._loading = False
        self.setWindowTitle("Run - Lot Plan" if self.runtime_mode else "Lot Plan")
        self.resize(1220, 760)
        self.setMinimumSize(1080, 660)
        self.setStyleSheet(
            "QDialog { background: #cfcbc2; font-family: Arial; font-size: 10px; }"
            "QPushButton { background: #e8e6dd; border: 1px solid #77736b; min-height: 27px; padding: 2px 8px; }"
            "QTableWidget { background: #efefec; gridline-color: #aaa69d; }"
            "QHeaderView::section { background: #dad7cf; border: 1px solid #918d85; padding: 4px; }"
        )
        root = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(QLabel("Lot Plan Mode"))
        self.mode = QComboBox()
        self.mode.addItems(["Lot Mode", "Repeat Mode"])
        self.mode.setCurrentText(self.state["mode"])
        self.mode.currentTextChanged.connect(self._mode_changed)
        top.addWidget(self.mode)
        top.addStretch(1)
        self.total_runs = QLabel()
        top.addWidget(self.total_runs)
        root.addLayout(top)
        body = QHBoxLayout()
        self.matrix = QTableWidget(self.state["slot_count"], len(self.state["test_names"]))
        self.matrix.setHorizontalHeaderLabels(self.state["test_names"])
        self.matrix.setVerticalHeaderLabels([str(index + 1) for index in range(self.state["slot_count"])])
        self.matrix.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.matrix.horizontalHeader().sectionClicked.connect(self._toggle_column)
        self.matrix.verticalHeader().sectionClicked.connect(self._toggle_row)
        self.matrix.itemChanged.connect(self._item_changed)
        body.addWidget(self.matrix, 1)
        body.addWidget(self._options_panel())
        root.addLayout(body, 1)
        footer = QHBoxLayout()
        self.validation = QLabel()
        footer.addWidget(self.validation, 1)
        ok = QPushButton("OK")
        ok.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        footer.addWidget(ok)
        footer.addWidget(cancel)
        root.addLayout(footer)
        self._populate()

    def _options_panel(self):
        panel = QFrame()
        panel.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        panel.setFixedWidth(390)
        layout = QVBoxLayout(panel)
        self.repeat_enabled = QCheckBox("Repeat Test")
        self.repeat_enabled.setChecked(bool(self.state["repeat_enabled"]))
        self.repeat_enabled.toggled.connect(self._repeat_toggled)
        layout.addWidget(self.repeat_enabled)
        repeat_row = QHBoxLayout()
        repeat_row.addWidget(QLabel("Count"))
        self.repeat_count = QSpinBox()
        self.repeat_count.setRange(1, 999)
        self.repeat_count.setValue(max([1, *self.state["repeat_counts"].values()]))
        self.repeat_count.valueChanged.connect(self._repeat_count_changed)
        repeat_row.addWidget(self.repeat_count)
        layout.addLayout(repeat_row)
        self.apply_count = QPushButton("Apply Count")
        self.apply_count.setToolTip("Apply Count to all assigned tests")
        self.apply_count.clicked.connect(self._apply_repeat_count)
        layout.addWidget(self.apply_count)
        self.advanced_button = QPushButton("Advanced...")
        self.advanced_button.setToolTip("Configure Repeat Mode advanced options")
        self.advanced_button.clicked.connect(self._advanced_options)
        layout.addWidget(self.advanced_button)
        self.advanced_summary = QLabel()
        layout.addWidget(self.advanced_summary)
        self.protect = QCheckBox("Protect")
        self.protect.setToolTip("Prevent Lot Plan changes during Inspection Run")
        self.protect.setChecked(bool(self.state["protect"]))
        self.protect.toggled.connect(lambda value: self._set_state("protect", value))
        layout.addWidget(self.protect)
        self.backup = QCheckBox("Backup Lot Result")
        self.backup.setChecked(bool(self.state["backup_lot_result"]))
        self.backup.toggled.connect(lambda value: self._set_state("backup_lot_result", value))
        layout.addWidget(self.backup)
        layout.addSpacing(10)
        self.cache = QCheckBox("Cache lot result for Classifier Maintenance")
        self.cache.setChecked(bool(self.state["cache_lot_result"]))
        self.cache.toggled.connect(self._cache_changed)
        layout.addWidget(self.cache)
        layout.addWidget(QLabel("Transfer Host / Mapped Drive"))
        self.host = QLineEdit(self.state["transfer_host"])
        self.host.textChanged.connect(lambda value: self._set_state("transfer_host", value))
        layout.addWidget(self.host)
        layout.addWidget(QLabel("Share Name"))
        self.share = QLineEdit(self.state["transfer_share"])
        self.share.textChanged.connect(lambda value: self._set_state("transfer_share", value))
        layout.addWidget(self.share)
        layout.addWidget(QLabel("Tool Type"))
        self.tool_type = QLineEdit(self.state["tool_type"])
        self.tool_type.textChanged.connect(lambda value: self._set_state("tool_type", value))
        layout.addWidget(self.tool_type)
        layout.addStretch(1)
        self._update_option_states()
        return panel

    def _advanced_options(self):
        dialog = LotPlanAdvancedOptionsDialog(
            self.state.get("unload_wafer_in_repeat_mode", False), self
        )
        if (dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()) != QDialog.Accepted:
            return
        self._set_state("unload_wafer_in_repeat_mode", dialog.result_unload_wafer)
        self._update_option_states()

    def _set_state(self, key, value):
        self.state[key] = value
        self.changed = True
        self._refresh_summary()

    def _mode_changed(self, value):
        self.state["mode"] = value
        repeat = value == "Repeat Mode"
        self.repeat_enabled.blockSignals(True)
        self.repeat_enabled.setChecked(repeat)
        self.repeat_enabled.blockSignals(False)
        self.state["repeat_enabled"] = repeat
        self.changed = True
        if repeat:
            self._set_all_repeat_counts(self.repeat_count.value())
        self._update_option_states()
        self._refresh_summary()

    def _repeat_toggled(self, checked):
        self.state["repeat_enabled"] = bool(checked)
        self.mode.blockSignals(True)
        self.mode.setCurrentText("Repeat Mode" if checked else "Lot Mode")
        self.mode.blockSignals(False)
        self.state["mode"] = self.mode.currentText()
        self.changed = True
        if checked:
            self._set_all_repeat_counts(self.repeat_count.value())
        self._update_option_states()
        self._refresh_summary()

    def _cache_changed(self, checked):
        self.state["cache_lot_result"] = bool(checked)
        self.changed = True
        self._update_option_states()
        self._refresh_summary()

    def _update_option_states(self):
        permissions = lot_plan_runtime_permissions(self.state, self.runtime_mode)
        repeat = self.repeat_enabled.isChecked()
        self.matrix.setEnabled(permissions["assignments"])
        self.mode.setEnabled(permissions["settings"])
        self.repeat_enabled.setEnabled(permissions["settings"])
        self.repeat_count.setEnabled(repeat and permissions["repeat_count"])
        self.apply_count.setEnabled(repeat and permissions["repeat_count"])
        self.advanced_button.setEnabled(permissions["settings"])
        self.advanced_summary.setText(
            "Unload Wafer in Repeat Mode: "
            + ("Yes" if self.state.get("unload_wafer_in_repeat_mode") else "No")
        )
        self.advanced_summary.setVisible(repeat)
        self.protect.setEnabled(permissions["settings"])
        self.backup.setEnabled(permissions["settings"])
        self.cache.setEnabled(permissions["settings"])
        transfer = self.cache.isChecked() and permissions["settings"]
        self.host.setEnabled(transfer)
        self.share.setEnabled(transfer)
        self.tool_type.setEnabled(transfer)

    def _populate(self):
        self._loading = True
        for row in range(self.matrix.rowCount()):
            slot = str(row + 1)
            assigned = set(self.state["assignments"].get(slot, []))
            for column, name in enumerate(self.state["test_names"]):
                item = QTableWidgetItem("")
                item.setCheckState(Qt.Checked if name in assigned else Qt.Unchecked)
                self.matrix.setItem(row, column, item)
        self._loading = False
        self._refresh_summary()

    def _item_changed(self, item):
        if self._loading:
            return
        slot = str(item.row() + 1)
        test_name = self.state["test_names"][item.column()]
        assigned = self.state["assignments"].setdefault(slot, [])
        if item.checkState() == Qt.Checked and test_name not in assigned:
            assigned.append(test_name)
            if self.state.get("repeat_enabled"):
                self.state["repeat_counts"][f"{slot}:{test_name}"] = self.repeat_count.value()
        elif item.checkState() != Qt.Checked and test_name in assigned:
            assigned.remove(test_name)
            self.state["repeat_counts"].pop(f"{slot}:{test_name}", None)
        if not assigned:
            self.state["assignments"].pop(slot, None)
        self.changed = True
        self._refresh_summary()

    def _toggle_row(self, row):
        checked = all(
            self.matrix.item(row, column).checkState() == Qt.Checked
            for column in range(self.matrix.columnCount())
        )
        for column in range(self.matrix.columnCount()):
            self.matrix.item(row, column).setCheckState(Qt.Unchecked if checked else Qt.Checked)

    def _toggle_column(self, column):
        checked = all(
            self.matrix.item(row, column).checkState() == Qt.Checked
            for row in range(self.matrix.rowCount())
        )
        for row in range(self.matrix.rowCount()):
            self.matrix.item(row, column).setCheckState(Qt.Unchecked if checked else Qt.Checked)

    def _apply_repeat_count(self):
        count = self.repeat_count.value()
        self._set_all_repeat_counts(count)
        self.changed = True
        self._refresh_summary()

    def _repeat_count_changed(self, count):
        if not self.state.get("repeat_enabled"):
            return
        self._set_all_repeat_counts(count)
        self.changed = True
        self._refresh_summary()

    def _set_all_repeat_counts(self, count):
        for slot, tests in self.state["assignments"].items():
            for test_name in tests:
                self.state["repeat_counts"][f"{slot}:{test_name}"] = count

    def _refresh_summary(self):
        assignments = sum(len(names) for names in self.state["assignments"].values())
        runs = 0
        for slot, names in self.state["assignments"].items():
            for name in names:
                runs += (
                    int(self.state["repeat_counts"].get(f"{slot}:{name}", 1))
                    if self.state["repeat_enabled"]
                    else 1
                )
        self.total_runs.setText(f"Assignments: {assignments}   Planned runs: {runs}")
        errors = validate_lot_plan(self.state)
        self.validation.setText(" | ".join(errors) if errors else "Lot Plan is valid.")
        self.validation.setStyleSheet("color: #a82929;" if errors else "color: #11752a;")

    def _finish(self):
        errors = validate_lot_plan(self.state)
        if errors:
            QMessageBox.warning(self, "Lot Plan", "\n".join(errors))
            return
        self.result_state = deepcopy(self.state)
        self.accept()

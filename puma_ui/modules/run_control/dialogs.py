from __future__ import annotations

from copy import deepcopy
from fnmatch import fnmatchcase
from pathlib import Path

from ...qt_compat import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTimer,
    Qt,
    QVBoxLayout,
    QWidget,
)
from ..wafer_alignment.dialogs import LowMagDieCornerImageDialog, SelectAlignmentSitesDialog
from ..lot_plan import lot_plan_runtime_permissions
from .models import (
    apply_high_defect_abort,
    default_job,
    default_run_setup,
    effective_wafer_defect_limit,
    generate_inspection_result,
    matching_result_ids,
    transfer_prerequisite_errors,
    validate_run_setup,
)


def _exec(dialog):
    return dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()


class RunOneWaferDialog(QDialog):
    def __init__(self, recipe, previous=None, results=None, parent=None):
        super().__init__(parent)
        self.recipe = recipe
        self.state = default_run_setup(recipe)
        if isinstance(previous, dict):
            self.state.update(deepcopy(previous))
        self.results = list(results or [])
        self.result_setup = None
        self.test_checks = {}
        self.setWindowTitle("Run One Wafer Lot Plan")
        self.resize(680, 590)
        self.setStyleSheet(
            "QDialog { background: #cfcbc2; font-family: Arial; font-size: 10px; }"
            "QFrame#panel { background: #ddd9d0; border: 1px solid #8a867e; }"
            "QPushButton { min-height: 26px; background: #ebe9e1; border: 1px solid #77736b; padding: 2px 9px; }"
        )
        root = QVBoxLayout(self)
        title = QLabel("Run One Wafer")
        title.setStyleSheet("font-size: 15px; font-weight: bold;")
        root.addWidget(title)

        identity = QFrame()
        identity.setObjectName("panel")
        identity_grid = QGridLayout(identity)
        self.lot_id = QLineEdit(self.state.get("lot_id", ""))
        self.wafer_id = QLineEdit(self.state.get("wafer_id", ""))
        identity_grid.addWidget(QLabel("Lot ID"), 0, 0)
        identity_grid.addWidget(self.lot_id, 0, 1)
        browse = QPushButton("Browse...")
        browse.clicked.connect(self._browse_result)
        identity_grid.addWidget(browse, 0, 2)
        identity_grid.addWidget(QLabel("Wafer ID (optional)"), 1, 0)
        identity_grid.addWidget(self.wafer_id, 1, 1, 1, 2)
        identity_grid.addWidget(QLabel("Inspection"), 2, 0)
        identity_grid.addWidget(QLabel(recipe.get("inspection", "New")), 2, 1, 1, 2)
        root.addWidget(identity)

        tests = QFrame()
        tests.setObjectName("panel")
        tests_layout = QVBoxLayout(tests)
        tests_layout.addWidget(QLabel("Tests to Run"))
        selected = set(self.state.get("selected_tests", []))
        plan_permissions = lot_plan_runtime_permissions(recipe.get("lot_plan"), runtime_mode=True)
        for index, test in enumerate(recipe.get("tests", [])):
            if test.get("mode") == "No Test":
                continue
            name = test.get("name", f"Test {index + 1}")
            check = QCheckBox(name)
            check.setChecked(name in selected)
            check.setEnabled(plan_permissions["assignments"])
            self.test_checks[name] = check
            check.toggled.connect(self._refresh_transfer_availability)
            tests_layout.addWidget(check)
        root.addWidget(tests)

        options = QFrame()
        options.setObjectName("panel")
        grid = QGridLayout(options)
        self.repeat_test = QCheckBox("Repeat Test")
        self.repeat_test.setChecked(bool(self.state.get("repeat_test")))
        self.repeat_test.setEnabled(plan_permissions["settings"])
        self.repeat_count = QSpinBox()
        self.repeat_count.setRange(1, 999)
        self.repeat_count.setValue(max(1, int(self.state.get("repeat_count", 1))))
        self.repeat_count.setEnabled(
            self.repeat_test.isChecked()
            and (plan_permissions["settings"] or plan_permissions["repeat_count"])
        )
        self.repeat_test.toggled.connect(
            lambda checked: self.repeat_count.setEnabled(
                checked and (plan_permissions["settings"] or plan_permissions["repeat_count"])
            )
        )
        grid.addWidget(self.repeat_test, 0, 0)
        grid.addWidget(QLabel("Count"), 0, 1)
        grid.addWidget(self.repeat_count, 0, 2)
        self.auto_transfer = QCheckBox("Auto Transfer")
        self.auto_transfer.setChecked(bool(self.state.get("auto_transfer")))
        self.transfer_host = QLineEdit(self.state.get("transfer_host", ""))
        self.transfer_host.setPlaceholderText("Analysis system host")
        self.transfer_host.setEnabled(self.auto_transfer.isChecked())
        self.auto_transfer.toggled.connect(self.transfer_host.setEnabled)
        grid.addWidget(self.auto_transfer, 1, 0)
        grid.addWidget(QLabel("Host"), 1, 1)
        grid.addWidget(self.transfer_host, 1, 2)
        self.transfer_patches = QCheckBox("Transfer Patches")
        self.transfer_patches.setChecked(bool(self.state.get("transfer_patches")))
        self.transfer_hi_res = QCheckBox("Transfer Hi-Res Images")
        self.transfer_hi_res.setChecked(bool(self.state.get("transfer_hi_res")))
        self.instant_review = QCheckBox("Instant Review")
        self.instant_review.setChecked(bool(self.state.get("instant_review", True)))
        self.collect_sensitivity = QCheckBox("Collect Sensitivity Data")
        self.collect_sensitivity.setChecked(bool(self.state.get("collect_sensitivity_data")))
        self.osts_data = QCheckBox("OSTS Data")
        self.osts_data.setChecked(bool(self.state.get("osts_data")))
        self.osts_data.setEnabled(self.collect_sensitivity.isChecked())
        self.collect_sensitivity.toggled.connect(self.osts_data.setEnabled)
        self.backup = QCheckBox("Backup Lot Result")
        self.backup.setChecked(bool(self.state.get("backup_lot_result")))
        self.backup.setEnabled(plan_permissions["settings"])
        grid.addWidget(self.transfer_patches, 2, 0, 1, 2)
        grid.addWidget(self.transfer_hi_res, 2, 2)
        grid.addWidget(self.instant_review, 3, 0, 1, 2)
        grid.addWidget(self.backup, 3, 2)
        grid.addWidget(self.collect_sensitivity, 4, 0, 1, 2)
        grid.addWidget(self.osts_data, 4, 2)
        self.transfer_requirements = QLabel()
        self.transfer_requirements.setWordWrap(True)
        self.transfer_requirements.setStyleSheet("color: #555149;")
        grid.addWidget(self.transfer_requirements, 5, 0, 1, 3)
        root.addWidget(options)
        self._refresh_transfer_availability()

        self.validation = QLabel()
        self.validation.setStyleSheet("color: #a41515; font-weight: bold;")
        root.addWidget(self.validation)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        run = QPushButton("Run One Wafer")
        run.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(run)
        buttons.addWidget(cancel)
        root.addLayout(buttons)

    def _refresh_transfer_availability(self, *_args):
        selected = [name for name, check in self.test_checks.items() if check.isChecked()]
        patch_errors = transfer_prerequisite_errors(
            {"transfer_patches": True}, self.recipe, selected
        )
        hi_res_errors = transfer_prerequisite_errors(
            {"transfer_hi_res": True}, self.recipe, selected
        )
        self.transfer_patches.setEnabled(not patch_errors)
        self.transfer_hi_res.setEnabled(not hi_res_errors)
        self.transfer_patches.setToolTip("\n".join(patch_errors))
        self.transfer_hi_res.setToolTip("\n".join(hi_res_errors))
        if patch_errors:
            self.transfer_patches.setChecked(False)
        if hi_res_errors:
            self.transfer_hi_res.setChecked(False)
        messages = []
        if patch_errors:
            messages.append("Patch transfer unavailable: " + "; ".join(patch_errors))
        if hi_res_errors:
            messages.append("Hi-res transfer unavailable: " + "; ".join(hi_res_errors))
        self.transfer_requirements.setText("\n".join(messages))
        self.transfer_requirements.setVisible(bool(messages))

    def _browse_result(self):
        candidates = [item for item in self.results if item.get("lot_id")]
        if not candidates:
            QMessageBox.information(self, "Select Lot Results", "No saved lot results are available.")
            return
        names = [f"{item['lot_id']} / {item.get('wafer_id', '')}" for item in candidates]
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Lot Results")
        layout = QVBoxLayout(dialog)
        combo = QComboBox()
        combo.addItems(names)
        layout.addWidget(combo)
        row = QHBoxLayout()
        ok = QPushButton("OK")
        ok.clicked.connect(dialog.accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(dialog.reject)
        row.addStretch(1)
        row.addWidget(ok)
        row.addWidget(cancel)
        layout.addLayout(row)
        if _exec(dialog) == QDialog.Accepted:
            selected = candidates[combo.currentIndex()]
            self.lot_id.setText(selected.get("lot_id", ""))
            self.wafer_id.setText(selected.get("wafer_id", ""))

    def _collect(self):
        return {
            "lot_id": self.lot_id.text().strip(),
            "wafer_id": self.wafer_id.text().strip(),
            "selected_tests": [name for name, check in self.test_checks.items() if check.isChecked()],
            "repeat_test": self.repeat_test.isChecked(),
            "repeat_count": self.repeat_count.value() if self.repeat_test.isChecked() else 1,
            "auto_transfer": self.auto_transfer.isChecked(),
            "transfer_host": self.transfer_host.text().strip(),
            "transfer_patches": self.transfer_patches.isChecked(),
            "transfer_hi_res": self.transfer_hi_res.isChecked(),
            "instant_review": self.instant_review.isChecked(),
            "collect_sensitivity_data": self.collect_sensitivity.isChecked(),
            "osts_data": self.osts_data.isChecked(),
            "backup_lot_result": self.backup.isChecked(),
        }

    def _finish(self):
        state = self._collect()
        errors = validate_run_setup(state, self.recipe)
        if errors:
            self.validation.setText("; ".join(errors))
            return
        existing_ids = matching_result_ids(self.results, state["lot_id"])
        if existing_ids:
            answer = QMessageBox.question(
                self,
                "Overwrite Lot Results File",
                "A lot results file with this Lot ID already exists. Overwrite the existing results?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
        state["overwrite_result_ids"] = existing_ids
        self.result_setup = state
        self.accept()


class PrintOnRunDialog(QDialog):
    def __init__(self, settings=None, parent=None):
        super().__init__(parent)
        current = settings if isinstance(settings, dict) else {}
        self.result_settings = None
        self.setWindowTitle("Print on Run")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Select the items to print automatically during an inspection run."))
        self.wafer_map = QCheckBox("Print wafer map after each test")
        self.wafer_map.setChecked(bool(current.get("wafer_map_after_each_test", False)))
        self.run_log = QCheckBox("Print run log after the entire run completes")
        self.run_log.setChecked(bool(current.get("run_log_after_run", False)))
        layout.addWidget(self.wafer_map)
        layout.addWidget(self.run_log)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        ok = QPushButton("OK")
        ok.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)

    def _finish(self):
        self.result_settings = {
            "wafer_map_after_each_test": self.wafer_map.isChecked(),
            "run_log_after_run": self.run_log.isChecked(),
        }
        self.accept()


class AbortRunDialog(QDialog):
    OPTIONS = [
        "Abort Entire Run",
        "Abort Current Wafer/Repeat and Continue",
        "Abort Current Inspection and Continue",
        "Abort Hi-Res Image Grab",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selection = ""
        self.setWindowTitle("Abort Run")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Select the part of the run to abort:"))
        self.radios = []
        for index, text in enumerate(self.OPTIONS):
            radio = QRadioButton(text)
            radio.setChecked(index == 0)
            radio.toggled.connect(lambda checked, current=radio: self._exclusive(current, checked))
            self.radios.append(radio)
            layout.addWidget(radio)
        row = QHBoxLayout()
        ok = QPushButton("OK")
        ok.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        row.addStretch(1)
        row.addWidget(ok)
        row.addWidget(cancel)
        layout.addLayout(row)

    def _exclusive(self, current, checked):
        if checked:
            for radio in self.radios:
                if radio is not current:
                    radio.setChecked(False)

    def _finish(self):
        self.selection = next((radio.text() for radio in self.radios if radio.isChecked()), self.OPTIONS[0])
        self.accept()


class RunStatusDialog(QDialog):
    def __init__(self, recipe, setup, *, snapshot_callback=None, print_settings=None, parent=None, auto_start=True):
        super().__init__(parent)
        self.recipe = recipe
        self.setup = deepcopy(setup)
        self.snapshot_callback = snapshot_callback
        self.print_settings = dict(print_settings or {})
        self.results = []
        self.progress_value = 0
        self.paused = False
        self.pending_pause = False
        self.pending_abort = ""
        self.snapshot_open = False
        self.pending_next_repeat = False
        self.auto_start = auto_start
        self.failure_checked = False
        self.finished = False
        self.current_repeat = 1
        self.total_repeats = setup.get("repeat_count", 1) if setup.get("repeat_test") else 1
        self.defect_limit = effective_wafer_defect_limit(recipe)
        self.setWindowTitle("Run Status")
        self.resize(780, 610)
        self.setMinimumSize(700, 560)
        root = QVBoxLayout(self)
        self.heading = QLabel()
        self.heading.setStyleSheet("font-size: 14px; font-weight: bold;")
        root.addWidget(self.heading)
        details = QGridLayout()
        details.addWidget(QLabel("Lot ID"), 0, 0)
        details.addWidget(QLabel(setup.get("lot_id", "")), 0, 1)
        details.addWidget(QLabel("Wafer ID"), 1, 0)
        details.addWidget(QLabel(setup.get("wafer_id", "") or "Auto"), 1, 1)
        details.addWidget(QLabel("Inspection"), 2, 0)
        details.addWidget(QLabel(recipe.get("inspection", "")), 2, 1)
        root.addLayout(details)
        root.addWidget(QLabel("Test Information"))
        self.test_information = QTableWidget(0, 3)
        self.test_information.setHorizontalHeaderLabels(
            ["Test", "Classifier", "Feature Vector"]
        )
        self.test_information.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.test_information.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.test_information.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.test_information.verticalHeader().setVisible(False)
        selected_tests = set(setup.get("selected_tests") or [])
        for test in recipe.get("tests", []):
            name = test.get("name", "Test")
            if selected_tests and name not in selected_tests:
                continue
            chain = (test.get("nef") or {}).get("classifiers") or []
            ido_active = bool(
                test.get("run_ido")
                or (test.get("run_nef") and any(item.get("type") == "iDO" for item in chain))
            )
            row = self.test_information.rowCount()
            self.test_information.insertRow(row)
            self.test_information.setItem(row, 0, QTableWidgetItem(name))
            self.test_information.setItem(
                row, 1, QTableWidgetItem("iDO Active" if ido_active else "None")
            )
            self.test_information.setItem(
                row,
                2,
                QTableWidgetItem(
                    test.get("feature_vector_version", "3.0A")
                    if test.get("save_feature_vectors")
                    else "Not Saved"
                ),
            )
        self.test_information.resizeRowsToContents()
        table_height = self.test_information.horizontalHeader().height() + 8
        table_height += sum(
            self.test_information.rowHeight(row)
            for row in range(self.test_information.rowCount())
        )
        self.test_information.setFixedHeight(min(250, max(96, table_height)))
        root.addWidget(self.test_information)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        root.addWidget(self.progress)
        self.message = QLabel("Preparing wafer and alignment...")
        root.addWidget(self.message)
        self.defects = QLabel("Defects detected: 0")
        root.addWidget(self.defects)
        self.log = QTableWidget(0, 2)
        self.log.setHorizontalHeaderLabels(["Progress", "Run Event"])
        self.log.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.log.verticalHeader().setVisible(False)
        root.addWidget(self.log, 1)
        buttons = QHBoxLayout()
        self.pause_button = QPushButton("Pause")
        self.pause_button.clicked.connect(self._toggle_pause)
        self.snapshot_button = QPushButton("Snapshot Review")
        self.snapshot_button.clicked.connect(self._snapshot)
        self.abort_button = QPushButton("Cancel...")
        self.abort_button.clicked.connect(self._abort)
        self.finish_button = QPushButton("Finish")
        self.finish_button.setEnabled(False)
        self.finish_button.clicked.connect(self.accept)
        buttons.addWidget(self.pause_button)
        buttons.addWidget(self.snapshot_button)
        buttons.addStretch(1)
        buttons.addWidget(self.abort_button)
        buttons.addWidget(self.finish_button)
        root.addLayout(buttons)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._advance)
        self._refresh_heading()
        self._append_log("Run initialized")
        if auto_start:
            self.timer.start(90)

    def _refresh_heading(self):
        self.heading.setText(f"Inspecting wafer - repeat {self.current_repeat} of {self.total_repeats}")

    def _append_log(self, message):
        row = self.log.rowCount()
        self.log.insertRow(row)
        self.log.setItem(row, 0, QTableWidgetItem(f"{self.progress_value}%"))
        self.log.setItem(row, 1, QTableWidgetItem(message))
        self.log.scrollToBottom()

    def _advance(self):
        if self.paused or self.finished:
            return
        self.progress_value = min(100, self.progress_value + 4)
        self.progress.setValue(self.progress_value)
        estimated = int((56 + self.current_repeat * 17) * self.progress_value / 100)
        self.defects.setText(f"Defects detected: {estimated}")
        if self.progress_value >= 16 and not self.failure_checked:
            self.failure_checked = True
            if not self._recover_startup_failure():
                return
        if self.progress_value >= 16 and self.pending_abort:
            selection = self.pending_abort
            self.pending_abort = ""
            self._apply_abort_selection(selection)
            return
        if self.progress_value >= 16 and self.pending_pause:
            self.pending_pause = False
            self.paused = True
            self.pause_button.setText("Continue")
            self.message.setText("Alignment completed; run paused by operator.")
            self._append_log(self.message.text())
            return
        if self.progress_value < 16:
            self.message.setText("Loading and aligning wafer...")
        elif self.progress_value < 88:
            self.message.setText("Swathing wafer and collecting defects...")
        else:
            self.message.setText("Applying wafer post processing...")
        if self.progress_value in (16, 40, 64, 88):
            self._append_log(self.message.text())
        if estimated >= self.defect_limit:
            result = generate_inspection_result(self.recipe, self.setup, repeat_index=self.current_repeat)
            self.results.append(apply_high_defect_abort(result, self.defect_limit))
            self._append_log(f"High defect count limit reached ({self.defect_limit})")
            self._complete()
            return
        if self.progress_value >= 100:
            result = generate_inspection_result(self.recipe, self.setup, repeat_index=self.current_repeat)
            if self.print_settings.get("wafer_map_after_each_test"):
                for test_name in result.get("selected_tests", []):
                    result["run_log"].append({
                        "time": result.get("completed", ""),
                        "level": "Info",
                        "message": f"Print on Run: wafer map printed after {test_name}",
                    })
            self.results.append(result)
            if self.current_repeat < self.total_repeats:
                if self.snapshot_open:
                    self.pending_next_repeat = True
                    self.timer.stop()
                    self.message.setText(
                        "Current repeat complete; close Snapshot Review before starting the next repeat."
                    )
                    self._append_log(self.message.text())
                else:
                    self._start_next_repeat()
            else:
                self._complete()

    def _start_next_repeat(self):
        self.pending_next_repeat = False
        self.current_repeat += 1
        self.progress_value = 0
        self.progress.setValue(0)
        self._refresh_heading()
        self._append_log("Starting next repeat")
        if self.auto_start and not self.timer.isActive():
            self.timer.start(90)

    def _complete(self):
        self.timer.stop()
        self.finished = True
        if self.results and self.results[-1].get("status") == "High Defect Abort":
            self.message.setText("Inspection stopped after reaching the wafer defect limit.")
        else:
            self.message.setText("Inspection run completed successfully.")
        self.defects.setText(f"Defects detected: {sum(item['defect_count'] for item in self.results)}")
        self._append_log("Inspection complete")
        if self.print_settings.get("run_log_after_run") and self.results:
            self.results[-1].setdefault("run_log", []).append({
                "time": self.results[-1].get("completed", ""),
                "level": "Info",
                "message": "Print on Run: run log printed after run completion",
            })
            self._append_log("Print on Run: run log printed")
        self.pause_button.setEnabled(False)
        self.abort_button.setEnabled(False)
        self.snapshot_button.setText("Review Results")
        self.finish_button.setEnabled(True)

    def _toggle_pause(self):
        if self.finished:
            return
        if self.progress_value < 16 and not self.paused:
            self.pending_pause = not self.pending_pause
            self.pause_button.setText("Pause Pending" if self.pending_pause else "Pause")
            self.message.setText(
                "Pause requested; alignment will complete first."
                if self.pending_pause else "Pause request cancelled."
            )
            self._append_log(self.message.text())
            return
        self.paused = not self.paused
        self.pause_button.setText("Continue" if self.paused else "Pause")
        self.message.setText("Run paused by operator." if self.paused else "Run continued.")
        self._append_log(self.message.text())

    def _snapshot(self):
        if not self.snapshot_callback:
            return
        self.snapshot_open = True
        try:
            self.snapshot_callback(
                self._snapshot_result(),
                not self.finished,
                self._snapshot_result,
            )
        finally:
            self.snapshot_open = False
            if self.pending_next_repeat and not self.finished:
                self._start_next_repeat()

    def _snapshot_result(self):
        if self.finished and self.results:
            snapshot = deepcopy(self.results[-1])
            snapshot["snapshot_complete"] = True
            return snapshot
        snapshot = generate_inspection_result(
            self.recipe,
            self.setup,
            repeat_index=self.current_repeat,
            status="Running",
        )
        keep = max(1, int(len(snapshot["defects"]) * max(self.progress_value, 4) / 100))
        snapshot["defects"] = snapshot["defects"][:keep]
        snapshot["defect_count"] = keep
        snapshot["snapshot_complete"] = False
        return snapshot

    def _abort(self):
        dialog = AbortRunDialog(self)
        if _exec(dialog) != QDialog.Accepted:
            return
        selection = dialog.selection
        self._append_log(selection)
        if self.progress_value < 16:
            self.pending_abort = selection
            self.message.setText("Cancel requested; alignment will complete first.")
            self._append_log(self.message.text())
            return
        self._apply_abort_selection(selection)

    def _apply_abort_selection(self, selection):
        if selection == "Abort Entire Run":
            self.timer.stop()
            self.results.append(
                generate_inspection_result(
                    self.recipe,
                    self.setup,
                    repeat_index=self.current_repeat,
                    status="Aborted",
                )
            )
            self.finished = True
            self.message.setText("Inspection run aborted by operator.")
            self.pause_button.setEnabled(False)
            self.snapshot_button.setEnabled(False)
            self.abort_button.setEnabled(False)
            self.finish_button.setEnabled(True)
        elif selection == "Abort Current Wafer/Repeat and Continue":
            if self.current_repeat < self.total_repeats:
                self.current_repeat += 1
                self.progress_value = 0
                self.progress.setValue(0)
                self._refresh_heading()
            else:
                self._complete()
        elif selection == "Abort Hi-Res Image Grab":
            self.setup["transfer_hi_res"] = False
            self.message.setText("Hi-Res image grab disabled; inspection continues.")
        else:
            self.message.setText("Current inspection skipped; continuing run.")

    def _recover_startup_failure(self):
        failure = str(self.setup.get("simulate_failure", "")).strip().lower()
        if failure not in ("alignment", "registration"):
            return True
        label = "wafer alignment" if failure == "alignment" else "wafer registration"
        manual_enabled = bool(
            self.setup.get(
                "manual_alignment_enabled",
                self.recipe.get("manual_alignment_enabled", False),
            )
        )
        if not manual_enabled:
            return self._record_startup_failure(
                label,
                "Manual recovery is disabled (DO_MANUAL_ALIGNMENT = 0)",
            )
        answer = QMessageBox.question(
            self,
            f"{label.title()} Failed",
            f"Automatic {label} failed. Perform manual {label} using the stored recipe data?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        recovered = False
        if answer == QMessageBox.Yes and failure == "alignment":
            alignment = self.recipe.get("alignment", {})
            if alignment.get("sites_defined"):
                dialog = SelectAlignmentSitesDialog(alignment.get("mode", "DF"), self)
                dialog.setWindowTitle("Manual Wafer Alignment")
                recovered = _exec(dialog) == QDialog.Accepted
            else:
                QMessageBox.warning(self, "Manual Wafer Alignment", "The selected recipe has no stored alignment sites.")
        elif answer == QMessageBox.Yes:
            dialog = LowMagDieCornerImageDialog("Select Die Origin", self)
            dialog.setWindowTitle("Manual Wafer Registration - Select Die Origin")
            recovered = _exec(dialog) == QDialog.Accepted
        if recovered:
            self.message.setText(f"Manual {label} completed; inspection continues.")
            self._append_log(self.message.text())
            return True
        return self._record_startup_failure(label)

    def _record_startup_failure(self, label, detail=""):
        result = generate_inspection_result(
            self.recipe,
            self.setup,
            repeat_index=self.current_repeat,
            status="Failed",
        )
        result["failure_reason"] = f"Automatic {label} failed"
        if detail:
            result["failure_reason"] += f"; {detail}"
        result["run_log"].append({
            "time": result.get("created", ""),
            "level": "Error",
            "message": result["failure_reason"],
        })
        self.results.append(result)
        self._complete()
        self.message.setText(f"Inspection failed: {label} was not recovered.")
        return False

    def closeEvent(self, event):
        if self.finished:
            event.accept()
            return
        answer = QMessageBox.question(
            self,
            "Run in Progress",
            "Abort the active inspection run and close this window?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self.timer.stop()
            self.results.append(
                generate_inspection_result(
                    self.recipe,
                    self.setup,
                    repeat_index=self.current_repeat,
                    status="Aborted",
                )
            )
            self.finished = True
            event.accept()
        else:
            event.ignore()


class JobSetupDialog(QDialog):
    def __init__(self, recipes, job=None, parent=None, *, view_only=False):
        super().__init__(parent)
        self.recipes = [recipe for recipe in recipes if recipe.get("status") == "Valid"] or list(recipes)
        self.job = deepcopy(job) if isinstance(job, dict) else None
        self.result_job = None
        self._updating = False
        self.read_only = bool(
            view_only
            or (self.job or {}).get("remote")
            or (self.job or {}).get("material_associated")
            or (self.job or {}).get("status") == "Running"
        )
        self.setWindowTitle("Job Setup Wizard" + (" - Read Only" if self.read_only else ""))
        self.resize(900, 680)
        root = QVBoxLayout(self)
        title = QLabel("Inspection Job Setup Wizard")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        root.addWidget(title)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._inspection_page(), "1. Select Inspection")
        self.tabs.addTab(self._cassette_page(), "2. Cassette Data")
        self.tabs.addTab(self._lot_plan_page(), "3. Lot Plan / Wafer ID")
        self.tabs.addTab(self._lot_id_page(), "4. Lot ID / Settings")
        root.addWidget(self.tabs, 1)
        self.validation = QLabel()
        self.validation.setStyleSheet("color: #a41515; font-weight: bold;")
        root.addWidget(self.validation)
        buttons = QHBoxLayout()
        self.back_button = QPushButton("< Back")
        self.back_button.clicked.connect(lambda: self.tabs.setCurrentIndex(max(0, self.tabs.currentIndex() - 1)))
        self.next_button = QPushButton("Next >")
        self.next_button.clicked.connect(self._next)
        buttons.addWidget(self.back_button)
        buttons.addWidget(self.next_button)
        buttons.addStretch(1)
        finish = QPushButton("Finish")
        finish.clicked.connect(self._finish)
        finish.setEnabled(not self.read_only)
        cancel = QPushButton("Close" if self.read_only else "Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(finish)
        buttons.addWidget(cancel)
        root.addLayout(buttons)
        self.tabs.currentChanged.connect(self._navigation_state)
        self._navigation_state(0)
        self._selected_changed()
        if self.read_only:
            for control in (
                self.available_recipe, self.inspection_list, self.primary, self.material,
                self.cassette, self.slot_order, self.use_map, self.map_table,
                self.repeat_count, self.read_wafer_id, self.plan_table, self.lot_table,
                self.auto_transfer, self.transfer_patches, self.transfer_hi_res, self.instant_review,
            ):
                control.setEnabled(False)

    def _inspection_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        controls = QHBoxLayout()
        self.available_recipe = QComboBox()
        self.available_recipe.addItems([recipe.get("inspection", "New") for recipe in self.recipes])
        add = QPushButton("Add to List")
        add.clicked.connect(self._add_inspection)
        remove = QPushButton("Delete from List")
        remove.clicked.connect(self._delete_inspection)
        reset = QPushButton("Reset List")
        reset.clicked.connect(self._reset_inspections)
        controls.addWidget(QLabel("Inspection"))
        controls.addWidget(self.available_recipe, 1)
        controls.addWidget(add)
        controls.addWidget(remove)
        controls.addWidget(reset)
        layout.addLayout(controls)
        self.inspection_list = QListWidget()
        requested = {
            item for item in (
                (self.job or {}).get("inspection_ids")
                or [(self.job or {}).get("recipe_id")]
            )
            if item
        }
        if not requested and self.recipes:
            requested.add(self.recipes[0].get("id"))
        for recipe in self.recipes:
            self.inspection_list.addItem(recipe.get("inspection", "New"))
            item = self.inspection_list.item(self.inspection_list.count() - 1)
            item.setData(Qt.UserRole, recipe.get("id"))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if recipe.get("id") in requested else Qt.Unchecked)
        self.inspection_list.itemChanged.connect(self._selected_changed)
        layout.addWidget(self.inspection_list, 1)
        primary_row = QHBoxLayout()
        primary_row.addWidget(QLabel("Primary Inspection"))
        self.primary = QComboBox()
        self.inspection = self.primary
        primary_row.addWidget(self.primary, 1)
        layout.addLayout(primary_row)
        return page

    def _cassette_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        top = QGridLayout()
        self.material = QLineEdit((self.job or {}).get("material_id", ""))
        self.material.setPlaceholderText("Cassette or pod ID")
        self.cassette = QComboBox()
        self.cassette.addItems(["Port 1", "Port 2", "Port 3"])
        self.cassette.setCurrentText((self.job or {}).get("cassette", "Port 1"))
        self.slot_order = QComboBox()
        self.slot_order.addItems(["Bottom Up", "Top Down", "Random"])
        self.slot_order.setCurrentText((self.job or {}).get("slot_order", "Bottom Up"))
        self.use_map = QCheckBox("Use This Expected Cassette Map")
        self.use_map.setChecked(bool((self.job or {}).get("use_expected_map", False)))
        top.addWidget(QLabel("Material ID"), 0, 0)
        top.addWidget(self.material, 0, 1)
        top.addWidget(QLabel("Use Cassette"), 1, 0)
        top.addWidget(self.cassette, 1, 1)
        top.addWidget(QLabel("Slot Order"), 2, 0)
        top.addWidget(self.slot_order, 2, 1)
        top.addWidget(self.use_map, 3, 0, 1, 2)
        layout.addLayout(top)
        self.map_table = QTableWidget(25, 2)
        self.map_table.setHorizontalHeaderLabels(["Slot", "Expected Wafer"])
        self.map_table.horizontalHeader().setStretchLastSection(True)
        stored_slots = set((self.job or {}).get("expected_cassette_map") or (self.job or {}).get("slots", [1]))
        self.map_checks = {}
        for row, slot in enumerate(range(25, 0, -1)):
            item = QTableWidgetItem(str(slot))
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.map_table.setItem(row, 0, item)
            check = QCheckBox("Wafer Present")
            check.setChecked(slot in stored_slots)
            check.toggled.connect(lambda checked, s=slot: self._map_changed(s, checked))
            self.map_checks[slot] = check
            self.map_table.setCellWidget(row, 1, check)
        layout.addWidget(self.map_table, 1)
        return page

    def _lot_plan_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        settings = QHBoxLayout()
        settings.addWidget(QLabel("Repeat Count for Selected Slots"))
        self.repeat_count = QSpinBox()
        self.repeat_count.setRange(1, 999)
        self.repeat_count.setValue(int((self.job or {}).get("setup", {}).get("repeat_count", 1)))
        settings.addWidget(self.repeat_count)
        self.read_wafer_id = QCheckBox("Read Wafer ID")
        self.read_wafer_id.setChecked(bool((self.job or {}).get("read_wafer_id", False)))
        settings.addWidget(self.read_wafer_id)
        settings.addStretch(1)
        layout.addLayout(settings)
        self.plan_table = QTableWidget()
        self.plan_table.verticalHeader().setVisible(False)
        layout.addWidget(self.plan_table, 1)
        return page

    def _lot_id_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        self.lot_table = QTableWidget(0, 3)
        self.lot_table.setHorizontalHeaderLabels(["Inspection", "Lot ID", "Result File Action"])
        self.lot_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.lot_table, 1)
        setup = (self.job or {}).get("setup", {})
        self.auto_transfer = QCheckBox("Auto Transfer")
        self.auto_transfer.setChecked(bool(setup.get("auto_transfer", True)))
        self.transfer_patches = QCheckBox("Transfer Patches")
        self.transfer_patches.setChecked(bool(setup.get("transfer_patches", False)))
        self.transfer_hi_res = QCheckBox("Transfer Hi-Res Images")
        self.transfer_hi_res.setChecked(bool(setup.get("transfer_hi_res", False)))
        self.instant_review = QCheckBox("Instant Review")
        self.instant_review.setChecked(bool(setup.get("instant_review", False)))
        options = QHBoxLayout()
        for control in (self.auto_transfer, self.transfer_patches, self.transfer_hi_res, self.instant_review):
            options.addWidget(control)
        options.addStretch(1)
        layout.addLayout(options)
        self.transfer_requirements = QLabel()
        self.transfer_requirements.setWordWrap(True)
        self.transfer_requirements.setStyleSheet("color: #555149;")
        layout.addWidget(self.transfer_requirements)
        return page

    def _selected_recipes(self):
        ids = [
            self.inspection_list.item(row).data(Qt.UserRole)
            for row in range(self.inspection_list.count())
            if self.inspection_list.item(row).checkState() == Qt.Checked
        ]
        return [recipe for recipe in self.recipes if recipe.get("id") in ids]

    def _add_inspection(self):
        row = self.available_recipe.currentIndex()
        if row >= 0:
            self.inspection_list.item(row).setCheckState(Qt.Checked)

    def _delete_inspection(self):
        row = self.inspection_list.currentRow()
        if row >= 0:
            self.inspection_list.item(row).setCheckState(Qt.Unchecked)

    def _reset_inspections(self):
        for row in range(self.inspection_list.count()):
            self.inspection_list.item(row).setCheckState(Qt.Unchecked)

    def _selected_changed(self, *_args):
        if self._updating:
            return
        selected = self._selected_recipes()
        current_id = self.primary.currentData() if hasattr(self, "primary") else None
        self._updating = True
        self.primary.clear()
        for recipe in selected:
            self.primary.addItem(recipe.get("inspection", "New"), recipe.get("id"))
        requested = (self.job or {}).get("primary_inspection_id") or (self.job or {}).get("recipe_id")
        index = self.primary.findData(current_id or requested)
        self.primary.setCurrentIndex(index if index >= 0 else 0)
        self._updating = False
        self._rebuild_lot_plan(selected)
        self._rebuild_lot_ids(selected)
        self._refresh_transfer_availability(selected)

    def _refresh_transfer_availability(self, selected=None):
        if not hasattr(self, "transfer_patches"):
            return
        selected = selected if selected is not None else self._selected_recipes()
        patch_errors = []
        hi_res_errors = []
        for recipe in selected:
            names = [
                test.get("name", "Test")
                for test in recipe.get("tests", [])
                if test.get("mode") != "No Test"
            ]
            prefix = recipe.get("inspection", "Inspection")
            patch_errors.extend(
                f"{prefix}: {message}"
                for message in transfer_prerequisite_errors(
                    {"transfer_patches": True}, recipe, names
                )
            )
            hi_res_errors.extend(
                f"{prefix}: {message}"
                for message in transfer_prerequisite_errors(
                    {"transfer_hi_res": True}, recipe, names
                )
            )
        self.transfer_patches.setEnabled(bool(selected) and not patch_errors and not self.read_only)
        self.transfer_hi_res.setEnabled(bool(selected) and not hi_res_errors and not self.read_only)
        self.transfer_patches.setToolTip("\n".join(patch_errors))
        self.transfer_hi_res.setToolTip("\n".join(hi_res_errors))
        if patch_errors:
            self.transfer_patches.setChecked(False)
        if hi_res_errors:
            self.transfer_hi_res.setChecked(False)
        messages = []
        if patch_errors:
            messages.append("Patch transfer unavailable: " + "; ".join(patch_errors))
        if hi_res_errors:
            messages.append("Hi-res transfer unavailable: " + "; ".join(hi_res_errors))
        self.transfer_requirements.setText("\n".join(messages))
        self.transfer_requirements.setVisible(bool(messages))

    def _map_changed(self, slot, checked):
        if hasattr(self, "plan_checks") and slot in self.plan_checks:
            self.plan_checks[slot].setChecked(checked)

    def _rebuild_lot_plan(self, selected):
        if not hasattr(self, "plan_table"):
            return
        previous = {item.get("slot"): item for item in (self.job or {}).get("slot_plans", [])}
        test_columns = []
        for recipe in selected:
            for test in recipe.get("tests", []):
                if test.get("mode") != "No Test":
                    test_columns.append((recipe, test.get("name", "Test")))
        self.plan_table.setColumnCount(4 + len(test_columns))
        self.plan_table.setRowCount(25)
        self.plan_table.setHorizontalHeaderLabels(
            ["Slot", "Use", "Wafer ID", "Repeat"]
            + [f"{recipe.get('inspection', 'New')} / {test}" for recipe, test in test_columns]
        )
        self.plan_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.plan_checks = {}
        self.plan_wafer_ids = {}
        self.plan_repeats = {}
        self.plan_test_checks = {}
        for row, slot in enumerate(range(25, 0, -1)):
            slot_item = QTableWidgetItem(str(slot))
            slot_item.setFlags(slot_item.flags() & ~Qt.ItemIsEditable)
            self.plan_table.setItem(row, 0, slot_item)
            stored = previous.get(slot, {})
            use = QCheckBox()
            use.setChecked(bool(stored) or self.map_checks.get(slot, QCheckBox()).isChecked())
            self.plan_checks[slot] = use
            self.plan_table.setCellWidget(row, 1, use)
            wafer_id = QLineEdit(str(stored.get("wafer_id", "")))
            self.plan_wafer_ids[slot] = wafer_id
            self.plan_table.setCellWidget(row, 2, wafer_id)
            repeat = QSpinBox()
            repeat.setRange(1, 999)
            repeat.setValue(int(stored.get("repeat_count", self.repeat_count.value())))
            self.plan_repeats[slot] = repeat
            self.plan_table.setCellWidget(row, 3, repeat)
            stored_tests = stored.get("tests") or {}
            stored_inspections = set(stored.get("inspection_ids") or [recipe.get("id") for recipe in selected])
            for offset, (recipe, test_name) in enumerate(test_columns, start=4):
                check = QCheckBox()
                configured = stored_tests.get(recipe.get("id"))
                check.setChecked(recipe.get("id") in stored_inspections and (configured is None or test_name in configured))
                self.plan_test_checks[(slot, recipe.get("id"), test_name)] = check
                self.plan_table.setCellWidget(row, offset, check)

    def _rebuild_lot_ids(self, selected):
        if not hasattr(self, "lot_table"):
            return
        existing = (self.job or {}).get("lot_ids") or {}
        fallback = (self.job or {}).get("setup", {}).get("lot_id", "")
        self.lot_table.setRowCount(0)
        for recipe in selected:
            row = self.lot_table.rowCount()
            self.lot_table.insertRow(row)
            name = QTableWidgetItem(recipe.get("inspection", "New"))
            name.setData(Qt.UserRole, recipe.get("id"))
            name.setFlags(name.flags() & ~Qt.ItemIsEditable)
            self.lot_table.setItem(row, 0, name)
            self.lot_table.setItem(row, 1, QTableWidgetItem(str(existing.get(recipe.get("id"), fallback))))
            action = QComboBox()
            action.addItems(["Create New", "Overwrite", "Append"])
            self.lot_table.setCellWidget(row, 2, action)

    def _navigation_state(self, index):
        self.back_button.setEnabled(index > 0)
        self.next_button.setEnabled(index < self.tabs.count() - 1)

    def _next(self):
        self.validation.clear()
        if self.tabs.currentIndex() == 0 and not self._selected_recipes():
            self.validation.setText("Select at least one inspection; designate the primary inspection")
            return
        self.tabs.setCurrentIndex(min(self.tabs.count() - 1, self.tabs.currentIndex() + 1))

    def _recipe(self):
        recipe_id = self.primary.currentData()
        return next((recipe for recipe in self.recipes if recipe.get("id") == recipe_id), {})

    @staticmethod
    def _parse_slots(text):
        slots = set()
        for token in text.replace(" ", "").split(","):
            if not token:
                continue
            if "-" in token:
                start, end = token.split("-", 1)
                slots.update(range(int(start), int(end) + 1))
            else:
                slots.add(int(token))
        return sorted(item for item in slots if 1 <= item <= 25)

    def _finish(self):
        selected = self._selected_recipes()
        recipe = self._recipe()
        if not selected or not recipe:
            self.validation.setText("Select at least one inspection and a primary inspection")
            self.tabs.setCurrentIndex(0)
            return
        lot_ids = {}
        result_actions = {}
        for row in range(self.lot_table.rowCount()):
            recipe_id = self.lot_table.item(row, 0).data(Qt.UserRole)
            lot_id = self.lot_table.item(row, 1).text().strip()
            if not lot_id:
                self.validation.setText("A Lot ID is required for every inspection")
                self.tabs.setCurrentIndex(3)
                return
            lot_ids[recipe_id] = lot_id
            result_actions[recipe_id] = self.lot_table.cellWidget(row, 2).currentText()
        slot_plans = []
        for slot in range(1, 26):
            if not self.plan_checks[slot].isChecked():
                continue
            tests = {}
            inspection_ids = []
            for selected_recipe in selected:
                recipe_id = selected_recipe.get("id")
                names = [
                    test.get("name", "Test")
                    for test in selected_recipe.get("tests", [])
                    if test.get("mode") != "No Test"
                    and self.plan_test_checks[(slot, recipe_id, test.get("name", "Test"))].isChecked()
                ]
                if names:
                    inspection_ids.append(recipe_id)
                    tests[recipe_id] = names
            if inspection_ids:
                slot_plans.append({
                    "slot": slot,
                    "wafer_id": self.plan_wafer_ids[slot].text().strip(),
                    "repeat_count": self.plan_repeats[slot].value(),
                    "inspection_ids": inspection_ids,
                    "tests": tests,
                })
        if not slot_plans:
            self.validation.setText("Select at least one wafer slot and inspection test")
            self.tabs.setCurrentIndex(2)
            return
        transfer_setup = {
            "transfer_patches": self.transfer_patches.isChecked(),
            "transfer_hi_res": self.transfer_hi_res.isChecked(),
        }
        transfer_errors = []
        for selected_recipe in selected:
            selected_test_names = sorted({
                test_name
                for plan in slot_plans
                for test_name in plan["tests"].get(selected_recipe.get("id"), [])
            })
            transfer_errors.extend(
                f"{selected_recipe.get('inspection', 'Inspection')}: {message}"
                for message in transfer_prerequisite_errors(
                    transfer_setup, selected_recipe, selected_test_names
                )
            )
        if transfer_errors:
            self.validation.setText("; ".join(transfer_errors))
            self.tabs.setCurrentIndex(3)
            return
        result = self.job or default_job(recipe)
        setup = default_run_setup(recipe)
        setup.update(result.get("setup", {}))
        setup.update({
            "lot_id": lot_ids[recipe.get("id")],
            "repeat_test": any(item["repeat_count"] > 1 for item in slot_plans),
            "repeat_count": max(item["repeat_count"] for item in slot_plans),
            "auto_transfer": self.auto_transfer.isChecked(),
            "transfer_patches": self.transfer_patches.isChecked(),
            "transfer_hi_res": self.transfer_hi_res.isChecked(),
            "instant_review": self.instant_review.isChecked(),
        })
        inspection_ids = [item.get("id") for item in selected]
        result.update({
            "inspection": recipe.get("inspection", ""),
            "recipe_id": recipe.get("id", ""),
            "inspection_ids": inspection_ids,
            "primary_inspection_id": recipe.get("id", ""),
            "device": recipe.get("device", ""),
            "step": recipe.get("step", ""),
            "material_id": self.material.text().strip(),
            "material_associated": bool(self.material.text().strip()),
            "cassette": self.cassette.currentText(),
            "slots": [item["slot"] for item in slot_plans],
            "slot_order": self.slot_order.currentText(),
            "slot_plans": slot_plans,
            "use_expected_map": self.use_map.isChecked(),
            "expected_cassette_map": [slot for slot, check in self.map_checks.items() if check.isChecked()],
            "read_wafer_id": self.read_wafer_id.isChecked(),
            "lot_ids": lot_ids,
            "result_file_actions": result_actions,
            "setup": setup,
            "status": "Waiting for Start" if self.material.text().strip() else "Waiting for Material",
        })
        self.result_job = result
        self.accept()


class RunLogDialog(QDialog):
    def __init__(self, title, entries, parent=None):
        super().__init__(parent)
        self.log_title = title
        self.entries = deepcopy(entries)
        self.printed_path = ""
        self.setWindowTitle("Run Log")
        self.resize(720, 430)
        layout = QVBoxLayout(self)
        heading = QLabel(title)
        heading.setStyleSheet("font-size: 13px; font-weight: bold;")
        layout.addWidget(heading)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Time", "Level", "Message"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        for entry in entries:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(entry.get("time", ""))))
            self.table.setItem(row, 1, QTableWidgetItem(str(entry.get("level", "Info"))))
            self.table.setItem(row, 2, QTableWidgetItem(str(entry.get("message", ""))))
        layout.addWidget(self.table, 1)
        print_button = QPushButton("Print...")
        print_button.clicked.connect(self._print)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(print_button)
        row.addWidget(close)
        layout.addLayout(row)

    def _print(self):
        path, _selected = QFileDialog.getSaveFileName(
            self, "Print Run Log", f"{self.log_title or 'Run Log'}.txt", "Text Files (*.txt)"
        )
        if not path:
            return
        lines = [self.log_title, "=" * len(self.log_title)]
        lines.extend(
            f"{entry.get('time', '')}\t{entry.get('level', 'Info')}\t{entry.get('message', '')}"
            for entry in self.entries
        )
        try:
            Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(self, "Print Run Log", f"Unable to create printable log: {exc}")
            return
        self.printed_path = path


class OpenLotResultRunLogDialog(QDialog):
    def __init__(self, results, parent=None):
        super().__init__(parent)
        self.results = list(results or [])
        self.visible_results = []
        self.selected_result = None
        self.setWindowTitle("Open Lot Result")
        self.resize(820, 500)
        root = QVBoxLayout(self)
        heading = QLabel("Open Lot Result - View Run Log")
        heading.setStyleSheet("font-size: 14px; font-weight: bold;")
        root.addWidget(heading)
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Find"))
        self.search = QLineEdit("*")
        self.search.setPlaceholderText("Use wildcards, for example * or S*")
        self.search.textChanged.connect(self._refresh)
        search_row.addWidget(self.search, 1)
        self.match_count = QLabel()
        search_row.addWidget(self.match_count)
        root.addLayout(search_row)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Lot ID", "Wafer ID", "Inspection", "Created"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.doubleClicked.connect(self._finish)
        root.addWidget(self.table, 1)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        open_button = QPushButton("OK")
        open_button.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(open_button)
        buttons.addWidget(cancel)
        root.addLayout(buttons)
        self._refresh()

    def _refresh(self, *_args):
        query = self.search.text().strip() or "*"
        pattern = query if any(character in query for character in "*?[") else f"*{query}*"
        pattern = pattern.casefold()
        self.visible_results = [
            result
            for result in self.results
            if any(
                fnmatchcase(str(result.get(key, "")).casefold(), pattern)
                for key in ("lot_id", "wafer_id", "inspection")
            )
        ]
        self.table.setRowCount(0)
        for result in self.visible_results:
            row = self.table.rowCount()
            self.table.insertRow(row)
            for column, key in enumerate(("lot_id", "wafer_id", "inspection", "created")):
                self.table.setItem(row, column, QTableWidgetItem(str(result.get(key, ""))))
        if self.visible_results:
            self.table.selectRow(0)
        self.match_count.setText(f"{len(self.visible_results)} result(s)")

    def _finish(self, *_args):
        row = self.table.currentRow()
        if not 0 <= row < len(self.visible_results):
            QMessageBox.information(self, "Open Lot Result", "Select a Lot Result to view its run log.")
            return
        self.selected_result = self.visible_results[row]
        self.accept()


class InspectionJobQueueDialog(QDialog):
    def __init__(self, store, recipes, *, run_callback=None, parent=None):
        super().__init__(parent)
        self.store = store
        self.recipes = recipes
        self.run_callback = run_callback
        self.visible_jobs = []
        self.setWindowTitle("Inspection Job Queue")
        self.resize(1050, 650)
        root = QVBoxLayout(self)
        heading = QLabel("Inspection Job Queue")
        heading.setStyleSheet("font-size: 15px; font-weight: bold;")
        root.addWidget(heading)
        current = QFrame()
        current_grid = QGridLayout(current)
        current_grid.addWidget(QLabel("Current Inspection State"), 0, 0)
        self.current_state = QLabel("System ready; no material associated")
        current_grid.addWidget(self.current_state, 0, 1)
        current_grid.addWidget(QLabel("Cassette Platform"), 1, 0)
        self.cassette_state = QLabel("Ports 1-3 available")
        current_grid.addWidget(self.cassette_state, 1, 1)
        root.addWidget(current)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Inspection", "Lot ID", "Material ID", "Cassette", "Slots", "Status", "Created"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        root.addWidget(self.table, 1)
        actions = QHBoxLayout()
        for label, callback in [
            ("Add Job...", self._add),
            ("Remove Job(s)", self._remove),
            ("Edit Job...", self._edit),
            ("View Job", self._view),
            ("Start Job", self._start),
            ("Cancel Job", self._cancel),
            ("View Job Run Log", self._run_log),
            ("Purge Queue", self._purge),
        ]:
            button = QPushButton(label)
            button.clicked.connect(callback)
            actions.addWidget(button)
        root.addLayout(actions)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        close_row = QHBoxLayout()
        close_row.addStretch(1)
        close_row.addWidget(close)
        root.addLayout(close_row)
        self._refresh()

    def _refresh(self):
        self.visible_jobs = self.store.list_jobs()
        self.table.setRowCount(0)
        for job in self.visible_jobs:
            row = self.table.rowCount()
            self.table.insertRow(row)
            setup = job.get("setup", {})
            values = [
                job.get("inspection", ""), setup.get("lot_id", ""), job.get("material_id", ""),
                job.get("cassette", ""), ",".join(str(item) for item in job.get("slots", [])),
                job.get("status", ""), job.get("created", ""),
            ]
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(str(value)))
        if self.visible_jobs:
            self.table.selectRow(0)
        running = next((job for job in self.visible_jobs if job.get("status") == "Running"), None)
        selected = running or (self.visible_jobs[0] if self.visible_jobs else None)
        if selected:
            self.current_state.setText(
                f"{selected.get('inspection', '')} | {selected.get('material_id') or 'No material'} | {selected.get('status', '')}"
            )
            self.cassette_state.setText(
                f"{selected.get('cassette', '')}; slots {', '.join(str(item) for item in selected.get('slots', []))}"
            )
        else:
            self.current_state.setText("System ready; no material associated")
            self.cassette_state.setText("Ports 1-3 available")

    def _selected(self):
        row = self.table.currentRow()
        return self.visible_jobs[row] if 0 <= row < len(self.visible_jobs) else None

    def _selected_jobs(self):
        rows = sorted({index.row() for index in self.table.selectionModel().selectedRows()})
        return [self.visible_jobs[row] for row in rows if 0 <= row < len(self.visible_jobs)]

    def _add(self):
        dialog = JobSetupDialog(self.recipes, parent=self)
        if _exec(dialog) == QDialog.Accepted and dialog.result_job:
            self.store.save_job(dialog.result_job)
            self._refresh()

    def _remove(self):
        jobs = self._selected_jobs()
        if not jobs:
            return
        if any(job.get("status") == "Running" for job in jobs):
            QMessageBox.warning(self, "Inspection Job Queue", "A running job cannot be removed.")
            return
        answer = QMessageBox.question(
            self,
            "Remove Inspection Job",
            f"Remove {len(jobs)} selected inspection job(s) from the queue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        for job in jobs:
            self.store.remove_job(job["id"])
        self._refresh()

    def _edit(self):
        job = self._selected()
        if not job:
            return
        if job.get("remote") or job.get("material_associated") or job.get("status") not in ("Waiting for Material", "Waiting for Start"):
            QMessageBox.information(self, "Inspection Job Queue", "This job is read-only because it is remote, associated with material, or already running.")
            self._view()
            return
        dialog = JobSetupDialog(self.recipes, job, self)
        if _exec(dialog) == QDialog.Accepted and dialog.result_job:
            self.store.save_job(dialog.result_job)
            self._refresh()

    def _view(self):
        job = self._selected()
        if not job:
            return
        _exec(JobSetupDialog(self.recipes, job, self, view_only=True))

    def _context_menu(self, position):
        if not self._selected():
            return
        menu = QMenu(self)
        menu.addAction("Edit Job", self._edit)
        menu.addAction("View Job", self._view)
        menu.addAction("Start Job", self._start)
        menu.addAction("Cancel Job", self._cancel)
        menu.addSeparator()
        menu.addAction("View Job Run Log", self._run_log)
        menu.addAction("Remove Job(s)", self._remove)
        menu.exec(self.table.viewport().mapToGlobal(position))

    def _start(self):
        job = self._selected()
        if not job or job.get("status") in ("Running", "Complete", "Cancelled"):
            return
        if not job.get("material_id"):
            QMessageBox.warning(
                self,
                "Inspection Job Queue",
                "This job is waiting for material. Associate a Material ID before starting the queue.",
            )
            return
        start_index = self.visible_jobs.index(job)
        runnable = [
            item
            for item in self.visible_jobs[start_index:]
            if item.get("material_id")
            and item.get("status") in ("Ready to Run", "Waiting for Start")
        ]
        for queued_job in runnable:
            queued_job["status"] = "Running"
            self.store.save_job(queued_job)
            self._refresh()
            results = self.run_callback(queued_job) if self.run_callback else []
            result_statuses = {result.get("status") for result in results or []}
            if "Failed" in result_statuses or "Aborted" in result_statuses:
                queued_job["status"] = "Failed"
            elif "High Defect Abort" in result_statuses:
                queued_job["status"] = "Complete with Errors"
            else:
                queued_job["status"] = "Complete" if results else "Cancelled"
            queued_job["run_log"] = [
                entry
                for result in (results or [])
                for entry in result.get("run_log", [])
            ]
            self.store.save_job(queued_job)
            self._refresh()

    def _cancel(self):
        job = self._selected()
        if not job or job.get("status") == "Complete":
            return
        job["status"] = "Cancelled"
        self.store.save_job(job)
        self._refresh()

    def _run_log(self):
        job = self._selected()
        if not job:
            return
        _exec(RunLogDialog(job.get("inspection", "Inspection Job"), job.get("run_log", []), self))

    def _purge(self):
        active = [job for job in self.visible_jobs if job.get("status") == "Running"]
        if active:
            QMessageBox.warning(self, "Inspection Job Queue", "Running jobs cannot be purged.")
            return
        answer = QMessageBox.question(
            self,
            "Purge Inspection Queue",
            "Remove all inspection jobs from the queue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.store.purge_jobs()
        self._refresh()

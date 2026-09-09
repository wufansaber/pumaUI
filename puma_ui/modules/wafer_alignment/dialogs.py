from __future__ import annotations

from typing import Optional

from ..image_display.dialog import AdvancedOpticsDialog, ImageDisplayWindow, SIMULATED_ALIGNMENT_IMAGES
from ...qt_compat import (
    QCheckBox,
    QColor,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPainter,
    QPen,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    Qt,
    QVBoxLayout,
    QWidget,
)
from ...widgets import ClassicButton


ALIGNMENT_QUALITY_ROWS = ("correlation", "uniqueness", "sharpness", "feature")
ALIGNMENT_QUALITY_COLUMNS = ("align", "x_reg", "y_reg")
DEFAULT_ALIGNMENT_QUALITY_TARGETS = {
    "correlation": {"align": 71.0, "x_reg": None, "y_reg": None},
    "uniqueness": {"align": 61.0, "x_reg": 10.0, "y_reg": 10.0},
    "sharpness": {"align": 81.0, "x_reg": 30.0, "y_reg": 30.0},
    "feature": {"align": 18386415.0, "x_reg": 16757116.0, "y_reg": 16447263.0},
}


def evaluate_alignment_quality(scores: dict, targets: dict) -> dict:
    """Compare every applicable alignment score with its configured target."""
    checks = {}
    passed = 0
    applicable = 0
    for metric in ALIGNMENT_QUALITY_ROWS:
        checks[metric] = {}
        for axis in ALIGNMENT_QUALITY_COLUMNS:
            target = (targets.get(metric) or {}).get(axis)
            actual = (scores.get(metric) or {}).get(axis)
            if target is None:
                checks[metric][axis] = None
                continue
            applicable += 1
            meets_target = actual is not None and float(actual) >= float(target)
            checks[metric][axis] = meets_target
            passed += int(meets_target)
    return {
        "checks": checks,
        "passed": passed,
        "applicable": applicable,
        "qualified": applicable > 0 and passed == applicable,
    }


def simulated_alignment_candidate_scores(
    candidate_number: int,
    targets: dict,
    *,
    use_pattern_matching: bool = True,
    high_precision_alignment: bool = False,
) -> dict:
    """Create deterministic image-quality measurements for the hardware simulator."""
    candidate_number = max(1, int(candidate_number))
    base_factor = 0.91 + 0.045 * candidate_number
    offsets = {
        "correlation": {"align": 0.020 if use_pattern_matching else -0.035},
        "uniqueness": {
            "align": 0.015 if use_pattern_matching else -0.025,
            "x_reg": 0.015,
            "y_reg": 0.005,
        },
        "sharpness": {"align": 0.010, "x_reg": 0.000, "y_reg": 0.010},
        "feature": {"align": 0.015, "x_reg": 0.005, "y_reg": 0.010},
    }
    if high_precision_alignment:
        for metric in ("uniqueness", "sharpness", "feature"):
            offsets[metric]["x_reg"] = offsets[metric].get("x_reg", 0.0) + 0.020
            offsets[metric]["y_reg"] = offsets[metric].get("y_reg", 0.0) + 0.020

    scores = {}
    for metric in ALIGNMENT_QUALITY_ROWS:
        scores[metric] = {}
        for axis in ALIGNMENT_QUALITY_COLUMNS:
            target = (targets.get(metric) or {}).get(axis)
            if target is None:
                scores[metric][axis] = None
                continue
            factor = base_factor + (offsets.get(metric) or {}).get(axis, 0.0)
            value = float(target) * factor
            scores[metric][axis] = round(value) if metric == "feature" else round(value, 2)
    return scores


class AlignmentMenuDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None, alignment_state: Optional[dict] = None):
        super().__init__(parent)
        self.alignment_state = dict(alignment_state or {})
        self.is_derivative = bool(self.alignment_state.pop("_derivative", False))
        self.test_optics_defined = bool(self.alignment_state.pop("_test_optics_defined", False))
        self.manual_alignment_enabled = bool(self.alignment_state.pop("_manual_alignment_enabled", False))
        self.alignment_failed = bool(self.alignment_state.pop("_alignment_failed", False))
        self.registration_failed = bool(self.alignment_state.pop("_registration_failed", False))
        self.temporary_alignment_enabled = bool(
            self.alignment_state.pop("_temporary_alignment_enabled", False)
        )
        self.orientation = str(self.alignment_state.pop("_orientation", "180"))
        self.alignment_result = None
        self.setWindowTitle("Alignment")
        self.resize(1480, 760)
        self.setStyleSheet(
            """
            QDialog {
                background: #eeece6;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10px;
            }
            QLabel#alignmentTitle {
                color: #111111;
                font-size: 18px;
                font-weight: 700;
            }
            QLabel#alignmentSectionTitle {
                color: #222222;
                font-size: 11px;
                font-weight: 700;
            }
            QLabel#alignmentStatus {
                color: #3f4a4f;
                font-size: 10px;
            }
            QFrame#alignmentSummary {
                background: #e2dfd7;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #88847c;
                border-bottom: 1px solid #88847c;
            }
            QLabel[summaryLabel="true"] {
                color: #55514a;
                font-size: 9px;
            }
            QLabel[summaryValue="true"] {
                color: #111111;
                font-size: 11px;
                font-weight: 700;
            }
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("Alignment")
        title.setObjectName("alignmentTitle")
        header.addWidget(title)
        header.addStretch(1)
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("alignmentStatus")
        header.addWidget(self.status_label)
        layout.addLayout(header)

        self.workspace_splitter = QSplitter(Qt.Horizontal)
        self.workspace_splitter.setChildrenCollapsible(False)
        self.workspace_splitter.setHandleWidth(5)

        controls = QWidget()
        controls.setObjectName("alignmentControls")
        controls.setMinimumWidth(340)
        controls.setMaximumWidth(500)
        controls.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(4, 2, 8, 2)
        controls_layout.setSpacing(10)

        action_title = QLabel("Alignment Operations")
        action_title.setObjectName("alignmentSectionTitle")
        controls_layout.addWidget(action_title)

        actions = QGridLayout()
        actions.setHorizontalSpacing(8)
        actions.setVerticalSpacing(8)
        for column in range(2):
            actions.setColumnStretch(column, 1)

        self.auto_site_button = ClassicButton("Auto Site\nSelection")
        self.auto_site_button.clicked.connect(self._open_auto_site_selection)
        actions.addWidget(self.auto_site_button, 0, 0)

        self.image_display_button = ClassicButton("Image\nDisplay")
        self.image_display_button.clicked.connect(self._open_image_display)
        actions.addWidget(self.image_display_button, 0, 1)

        self.select_sites_button = ClassicButton("Select Sites")
        self.select_sites_button.clicked.connect(self._open_select_sites)
        actions.addWidget(self.select_sites_button, 1, 0)

        self.align_wafer_button = ClassicButton("Align Wafer")
        self.align_wafer_button.clicked.connect(self._align_wafer)
        actions.addWidget(self.align_wafer_button, 1, 1)

        self.set_optics_button = ClassicButton("Set Optics\nand Retrain")
        self.set_optics_button.clicked.connect(self._set_optics_and_retrain)
        actions.addWidget(self.set_optics_button, 2, 0)

        self.qualify_button = ClassicButton("Qualify with\nTest Optics")
        self.qualify_button.clicked.connect(self._open_qualify_with_test_optics)
        actions.addWidget(self.qualify_button, 2, 1)

        self.manual_button = ClassicButton("Manual\nAlignment")
        self.manual_button.clicked.connect(self._open_manual_alignment)
        actions.addWidget(self.manual_button, 3, 0, 1, 2)
        for button in (
            self.auto_site_button,
            self.image_display_button,
            self.select_sites_button,
            self.align_wafer_button,
            self.set_optics_button,
            self.qualify_button,
            self.manual_button,
        ):
            button.setMinimumHeight(58)
        controls_layout.addLayout(actions)

        summary_title = QLabel("Current Alignment")
        summary_title.setObjectName("alignmentSectionTitle")
        controls_layout.addWidget(summary_title)
        summary = QFrame()
        summary.setObjectName("alignmentSummary")
        summary_layout = QGridLayout(summary)
        summary_layout.setContentsMargins(18, 14, 18, 14)
        summary_layout.setHorizontalSpacing(28)
        summary_layout.setVerticalSpacing(4)
        self.summary_values = {}
        for index, (label, key) in enumerate(
            (
                ("Alignment Sites", "sites"),
                ("Imaging Mode", "mode"),
                ("Selection Method", "method"),
                ("Wafer Status", "aligned"),
            )
        ):
            caption = QLabel(label)
            caption.setProperty("summaryLabel", True)
            value = QLabel("-")
            value.setProperty("summaryValue", True)
            row = (index // 2) * 2
            column = index % 2
            summary_layout.addWidget(caption, row, column)
            summary_layout.addWidget(value, row + 1, column)
            summary_layout.setColumnStretch(column, 1)
            self.summary_values[key] = value
        controls_layout.addWidget(summary)
        controls_layout.addStretch(1)

        footer = QHBoxLayout()
        footer.addStretch(1)
        end = ClassicButton("End")
        end.setMinimumWidth(120)
        end.clicked.connect(self.accept)
        footer.addWidget(end)
        controls_layout.addLayout(footer)

        active_state = self.alignment_result or self.alignment_state
        self.image_display = ImageDisplayWindow(
            self,
            embedded=True,
            alignment_mode=str(active_state.get("mode", "DF")),
        )
        self.image_display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.workspace_splitter.addWidget(controls)
        self.workspace_splitter.addWidget(self.image_display)
        self.workspace_splitter.setStretchFactor(0, 0)
        self.workspace_splitter.setStretchFactor(1, 1)
        self.workspace_splitter.setSizes([410, 1030])
        layout.addWidget(self.workspace_splitter, 1)
        self._refresh_action_states()

    def _has_alignment_sites(self) -> bool:
        return bool(
            self.alignment_state.get("sites_defined")
            or (self.alignment_result and self.alignment_result.get("sites_defined"))
        )

    def _refresh_action_states(self):
        has_sites = self._has_alignment_sites()
        self.align_wafer_button.setEnabled(True)
        self.set_optics_button.setEnabled(True)
        self.qualify_button.setEnabled(True)
        self.manual_button.setEnabled(True)
        state = self.alignment_result or self.alignment_state
        if hasattr(self, "image_display"):
            self.image_display.set_alignment_mode(str(state.get("mode", "DF")))
        if hasattr(self, "summary_values"):
            self.summary_values["sites"].setText("Defined" if has_sites else "Not Defined")
            self.summary_values["mode"].setText(str(state.get("mode", "-")))
            self.summary_values["method"].setText(str(state.get("method", "-")))
            self.summary_values["aligned"].setText(
                "Aligned" if state.get("aligned") else "Not Aligned"
            )

    def _set_alignment_status(self, status: str):
        self.setWindowTitle(f"Alignment - {status}")
        if hasattr(self, "status_label"):
            self.status_label.setText(status)

    def _open_auto_site_selection(self):
        if self._has_alignment_sites():
            proceed = QMessageBox.question(
                self,
                "Select Alignment Sites",
                "Valid alignment sites are already defined.\nProceed with Auto Site Selection?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if proceed != QMessageBox.Yes:
                self._set_alignment_status("Auto Site Selection cancelled")
                return

        parameters = AutoSiteAlignmentParametersDialog(
            self,
            test_optics_defined=self.test_optics_defined,
        )
        parameter_result = parameters.exec() if hasattr(parameters, "exec") else parameters.exec_()
        if parameter_result != QDialog.Accepted:
            self._set_alignment_status("Auto Site Selection parameters cancelled")
            return

        dialog = AutoSiteSelectionDialog(self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            qualified = bool(dialog.quality_result.get("qualified"))
            self.alignment_result = dict(self.alignment_state)
            self.alignment_result.update({
                "sites_defined": True,
                "mode": "DF",
                "method": "Automatic",
                "qualified": qualified,
                "status": "Qualified" if qualified else "Nonoptimal",
                "site_coordinates": [[-1800.0, 1200.0], [-800.0, 1200.0]],
                "site_images": ["Sim Cross Mark 1 (DF)", "Sim Cross Mark 2 (DF)"],
                "high_precision": dialog.high_precision_alignment,
                "quality": dialog.quality_result,
                "scores": {self.orientation: dialog.overview_scores("DF")},
            })
            self._refresh_action_states()
            self._set_alignment_status(
                "Auto Site Selection qualified" if qualified else "Auto Site Selection nonoptimal"
            )

    def _open_image_display(self):
        sizes = self.workspace_splitter.sizes()
        if len(sizes) == 2 and sizes[1] < 420:
            total = max(sum(sizes), 900)
            self.workspace_splitter.setSizes([min(410, total // 3), max(600, total - 410)])
        self.image_display.viewport.setFocus()
        self.image_display.viewport.update()
        self._set_alignment_status("Image Display active on the right screen")

    def _open_select_sites(self):
        if self._has_alignment_sites():
            proceed = QMessageBox.question(
                self,
                "Select Alignment Sites",
                "You already have valid Alignment Sites. Reselection of Alignment sites requires\n"
                "that you select your Old Die Origin, or your old High Mag Alignment Site (if available).\n\n"
                "Accurate reselection of this point is very important for ensuring that\n"
                "your wafer map and test data to be reused correctly!\n\n"
                "Do you want to proceed?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if proceed != QMessageBox.Yes:
                self._set_alignment_status("Select Sites cancelled")
                return

        dialog = AlignmentImagingModeDialog(
            self,
            test_optics_defined=self.test_optics_defined,
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            stored_sites = self.alignment_state.get("site_coordinates")
            if self._has_alignment_sites() and not stored_sites:
                stored_sites = [[-1800.0, 1200.0], [-800.0, 1200.0]]
            sites = SelectAlignmentSitesDialog(
                dialog.selected_mode,
                self,
                existing_sites=stored_sites,
                existing_images=self.alignment_state.get("site_images"),
                bf_dual_magnification=dialog.bf_dual_magnification,
            )
            site_result = sites.exec() if hasattr(sites, "exec") else sites.exec_()
            if site_result == QDialog.Accepted:
                self.alignment_result = {
                    "sites_defined": True,
                    "mode": dialog.selected_mode,
                    "method": "Interactive",
                    "site_coordinates": [list(point) for point in sites.marked_sites],
                    "site_images": list(sites.site_images),
                    "high_precision": sites.high_precision_alignment,
                    "bf_dual_magnification": sites.bf_dual_magnification,
                }
                if self.is_derivative:
                    derived = DerivedSiteSelectionDialog(
                        self,
                        has_old_corner=self._has_alignment_sites(),
                    )
                    derived_result = derived.exec() if hasattr(derived, "exec") else derived.exec_()
                    if derived_result != QDialog.Accepted:
                        self.alignment_result = None
                        self._set_alignment_status("Derivative reference selection cancelled")
                        self._refresh_action_states()
                        return
                    corner = LowMagDieCornerImageDialog(derived.selected_choice, self)
                    corner_result = corner.exec() if hasattr(corner, "exec") else corner.exec_()
                    if corner_result != QDialog.Accepted:
                        self.alignment_result = None
                        self._set_alignment_status("Derivative origin reselection cancelled")
                        self._refresh_action_states()
                        return
                    self.alignment_result["derivative_origin_reselected"] = True
                    self.alignment_result["derivative_reference"] = derived.selected_choice
                    self.alignment_result["apply_site_offset"] = derived.apply_site_offset
                    self._set_alignment_status(
                        f"Derivative site selected ({dialog.selected_mode})"
                    )
                else:
                    self._set_alignment_status(f"Sites aligned ({dialog.selected_mode})")
                self._refresh_action_states()
            else:
                self._set_alignment_status(f"Select Sites ready ({dialog.selected_mode})")

    def _open_qualify_with_test_optics(self):
        if not self._has_alignment_sites() or not self.test_optics_defined:
            QMessageBox.warning(
                self,
                "Qualify with Test Optics",
                "Define alignment sites and at least one Test Optics setup before qualification.",
            )
            return
        dialog = QualifyWithTestOpticsDialog(self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            keep_new_data = QMessageBox.question(
                self,
                "Qualify with Test Optics",
                "Alignment qualification is complete.\n\n"
                "Do you want to keep the new alignment data?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            suffix = "with Re-learn" if dialog.relearn_enabled else "without Re-learn"
            data_state = "new data retained" if keep_new_data == QMessageBox.Yes else "new data discarded"
            self._set_alignment_status(f"Qualified {suffix}, {data_state}")

    def _align_wafer(self):
        if not self.alignment_state.get("sites_defined") and not self.alignment_result:
            QMessageBox.warning(
                self,
                "Align Wafer",
                "No stored alignment sites are available. Select alignment sites first.",
            )
            return
        run = AlignmentRunDialog(self)
        result = run.exec() if hasattr(run, "exec") else run.exec_()
        if result != QDialog.Accepted:
            return
        if not run.simulate_registration_failure.isChecked():
            self.alignment_result = dict(self.alignment_result or self.alignment_state)
            self.alignment_result.update({"aligned": True, "last_result": "Alignment successful"})
            QMessageBox.information(self, "Align Wafer", "Wafer alignment completed successfully.")
            self._set_alignment_status("Wafer aligned")
            self._refresh_action_states()
            return

        manual = QMessageBox.question(
            self,
            "Registration Failed",
            "Registration part of the alignment process failed.\n"
            "Do you want to ignore it by manually selecting the die corner?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if manual != QMessageBox.Yes:
            self._set_alignment_status("Registration failed")
            return
        corner = LowMagDieCornerImageDialog("Select Die Origin", self)
        corner.setWindowTitle("Manual Wafer Registration - Select Die Origin")
        corner_result = corner.exec() if hasattr(corner, "exec") else corner.exec_()
        if corner_result == QDialog.Accepted:
            self.alignment_result = dict(self.alignment_result or self.alignment_state)
            self.alignment_result.update(
                {
                    "aligned": True,
                    "manual_registration": True,
                    "last_result": "Registration completed by manual die-origin selection",
                }
            )
            self._set_alignment_status("Manual registration complete")
            self._refresh_action_states()

    def _set_optics_and_retrain(self):
        if not self._has_alignment_sites():
            QMessageBox.warning(
                self,
                "Set Optics and Retrain",
                "Define alignment sites before changing and retraining alignment optics.",
            )
            return
        dialog = AlignmentParametersDialog(self.alignment_state.get("mode", "DF"), self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.alignment_result = dict(self.alignment_result or self.alignment_state)
            self.alignment_result.update({"optics_retrained": True, "sites_defined": True})
            self._refresh_action_states()
            self._set_alignment_status("Optics updated and retrained")

    def _open_manual_alignment(self):
        available = self.alignment_state.get("sites_defined") or (
            self.alignment_result and self.alignment_result.get("sites_defined")
        )
        if not available:
            QMessageBox.warning(
                self,
                "Manual Alignment",
                "Manual alignment requires a saved recipe with stored alignment data.",
            )
            return
        proceed = QMessageBox.question(
            self,
            "Manual Alignment Alert",
            "Perform manual wafer alignment using the stored recipe sites?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if proceed != QMessageBox.Yes:
            return
        stored_sites = self.alignment_state.get("site_coordinates")
        if not stored_sites:
            stored_sites = [[-1800.0, 1200.0], [-800.0, 1200.0]]
        dialog = SelectAlignmentSitesDialog(
            self.alignment_state.get("mode", "DF"),
            self,
            existing_sites=stored_sites,
            existing_images=self.alignment_state.get("site_images"),
        )
        dialog.setWindowTitle("Manual Wafer Alignment")
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result != QDialog.Accepted:
            return
        use_temporary_alignment = False
        if self.registration_failed and self.temporary_alignment_enabled:
            temporary = QMessageBox.question(
                self,
                "Temporary Alignment",
                "Use these manual alignment parameters for the remaining wafers in the lot?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            use_temporary_alignment = temporary == QMessageBox.Yes
        self.alignment_result = dict(self.alignment_result or self.alignment_state)
        self.alignment_result.update(
            {
                "sites_defined": True,
                "aligned": True,
                "method": "Manual",
                "site_coordinates": [list(point) for point in dialog.marked_sites],
                "site_images": list(dialog.site_images),
                "temporary_alignment": use_temporary_alignment,
            }
        )
        self._set_alignment_status("Manual alignment complete")
        self._refresh_action_states()

    def _set_title_status(self, action: str):
        self._set_alignment_status(f"{action} selected")


class AlignmentRunDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Align Wafer")
        self.setFixedSize(410, 220)
        self.setStyleSheet(
            "QDialog { background: #efede2; font-family: Arial; font-size: 10px; }"
            "QPushButton { min-width: 88px; min-height: 25px; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 22, 26, 18)
        title = QLabel("Run alignment using the stored recipe sites")
        title.setStyleSheet("font-weight: 700;")
        layout.addWidget(title)
        layout.addWidget(QLabel("The simulator can exercise the manual registration recovery path."))
        self.simulate_registration_failure = QCheckBox("Simulate registration matching failure")
        layout.addWidget(self.simulate_registration_failure)
        layout.addStretch(1)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        align = QPushButton("Align")
        align.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(align)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)


class AlignmentImagingModeDialog(QDialog):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        test_optics_defined: bool = False,
    ):
        super().__init__(parent)
        self.test_optics_defined = test_optics_defined
        self.setWindowTitle("Alignment Imaging Mode")
        self.setFixedSize(260, 230)
        self.selected_mode = "DF"
        self.bf_dual_magnification = True
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(
            """
            QDialog {
                background: #d0ccc2;
                color: #111111;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10px;
            }
            QPushButton {
                background: #e7e4da;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-height: 28px;
                padding: 3px 12px;
            }
            QLabel {
                color: #111111;
            }
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 16)
        layout.setSpacing(12)
        description = QLabel("Select the optics template used to define alignment.")
        description.setWordWrap(True)
        layout.addWidget(description)

        df = QPushButton("DF")
        df.clicked.connect(lambda: self._open_parameters("DF"))
        layout.addWidget(df)

        bf = QPushButton("BF")
        bf.clicked.connect(lambda: self._open_parameters("BF"))
        layout.addWidget(bf)
        layout.addStretch(1)

        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        layout.addWidget(cancel, alignment=Qt.AlignRight)

    def _open_parameters(self, mode: str):
        dialog = (
            BFAlignmentParametersDialog(self)
            if mode == "BF"
            else AlignmentParametersDialog(
                mode,
                self,
                test_optics_defined=self.test_optics_defined,
            )
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.selected_mode = mode
            if mode == "BF":
                self.bf_dual_magnification = dialog.dual_mag.isChecked()
            self.accept()


class AlignmentParametersDialog(QDialog):
    def __init__(
        self,
        mode: str = "DF",
        parent: Optional[QWidget] = None,
        test_optics_defined: bool = False,
    ):
        super().__init__(parent)
        self.mode = mode
        self.test_optics_defined = test_optics_defined
        self.setWindowTitle("Alignment Parameters")
        self.setFixedSize(520, 400)
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(
            """
            QDialog {
                background: #cfcac1;
                color: #111111;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10px;
            }
            QPushButton {
                background: #e7e4da;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-height: 26px;
                padding: 2px 12px;
            }
            QComboBox {
                background: #ffffff;
                border: 1px solid #77736b;
                min-height: 24px;
            }
            QFrame#parameterGroup {
                border: 1px solid #8f8b82;
                background: #cfcac1;
            }
            QLabel#groupTitle {
                background: #cfcac1;
                padding: 0 4px;
                font-weight: 600;
            }
            """
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(70, 28, 70, 28)
        root.setSpacing(18)

        row = QHBoxLayout()
        row.setSpacing(14)
        row.addWidget(self._optics_group())
        row.addWidget(self._optics_used_group())
        root.addLayout(row)
        root.addStretch(1)

        footer = QHBoxLayout()
        ok = QPushButton("OK")
        ok.setFixedWidth(112)
        ok.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.setFixedWidth(112)
        cancel.clicked.connect(self.reject)
        footer.addStretch(1)
        footer.addWidget(ok)
        footer.addSpacing(54)
        footer.addWidget(cancel)
        footer.addStretch(1)
        root.addLayout(footer)

    def _optics_group(self) -> QFrame:
        group = QFrame()
        group.setObjectName("parameterGroup")
        group.setFixedSize(215, 255)
        title = QLabel("Optics")
        title.setObjectName("groupTitle")
        title.setParent(group)
        title.move(12, -1)

        layout = QVBoxLayout(group)
        layout.setContentsMargins(18, 20, 18, 14)
        layout.setSpacing(10)
        layout.addWidget(QLabel("Pixel Size"))
        pixel = QComboBox()
        pixel.addItems(["SL610", "SL8685", "SL8686"])
        pixel.setFixedWidth(170)
        layout.addWidget(pixel)
        layout.addSpacing(8)

        layout.addWidget(QLabel("Channel Used\nfor Alignment:"))
        channel = QComboBox()
        channel.addItems(["3 (Center)", "1 (Left)", "2 (Right)"])
        channel.setFixedWidth(170)
        layout.addWidget(channel)
        layout.addSpacing(8)

        advanced = QPushButton("Advanced Optics...")
        advanced.setFixedWidth(170)
        advanced.clicked.connect(self._open_advanced_optics)
        layout.addWidget(advanced)
        layout.addStretch(1)
        return group

    def _optics_used_group(self) -> QFrame:
        group = QFrame()
        group.setObjectName("parameterGroup")
        group.setFixedSize(165, 140)
        title = QLabel("Optics to be used")
        title.setObjectName("groupTitle")
        title.setParent(group)
        title.move(12, -1)

        layout = QVBoxLayout(group)
        layout.setContentsMargins(18, 18, 10, 12)
        user_defined = QRadioButton("User defined")
        user_defined.setChecked(True)
        layout.addWidget(user_defined)
        production = QRadioButton("Primary\nProduction\nTest's")
        production.setEnabled(self.test_optics_defined)
        self.production_optics = production
        layout.addWidget(production)
        layout.addStretch(1)
        return group

    def _open_advanced_optics(self):
        dialog = AdvancedOpticsDialog(self)
        dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()


class AutoSiteAlignmentParametersDialog(QDialog):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        test_optics_defined: bool = False,
    ):
        super().__init__(parent)
        self.test_optics_defined = test_optics_defined
        self.setWindowTitle("Alignment Parameters")
        self.setFixedSize(500, 540)
        self.keep_old_wafer_center = True
        self.use_primary_production_test = False
        self._build_ui()
        self._update_production_enabled()

    def _build_ui(self):
        self.setStyleSheet(
            """
            QDialog {
                background: #cfcac1;
                color: #111111;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10px;
            }
            QPushButton {
                background: #e7e4da;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-height: 26px;
                padding: 2px 12px;
            }
            QComboBox {
                background: #ffffff;
                border: 1px solid #77736b;
                min-height: 24px;
            }
            QComboBox:disabled {
                color: #8a867e;
                background: #d8d4ca;
            }
            QFrame#parameterGroup {
                border: 1px solid #8f8b82;
                background: #cfcac1;
            }
            QLabel#groupTitle {
                background: #cfcac1;
                padding: 0 4px;
                font-weight: 600;
            }
            """
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(42, 28, 42, 24)
        root.setSpacing(14)

        top = QHBoxLayout()
        top.setSpacing(12)
        top.addWidget(self._optics_group())
        top.addWidget(self._optics_used_group(), 0, Qt.AlignTop)
        root.addLayout(top)

        production_row = QHBoxLayout()
        production_row.addWidget(QLabel("Primary Production Test:"))
        self.production_test = QComboBox()
        self.production_test.addItems(["1", "2", "3"])
        self.production_test.setFixedWidth(100)
        production_row.addWidget(self.production_test)
        production_row.addStretch(1)
        root.addLayout(production_row)

        self.keep_center = QCheckBox("Keep Old Wafer Center")
        self.keep_center.setChecked(True)
        root.addWidget(self.keep_center)

        warning = QLabel(
            "If you uncheck this box\n"
            "- Use EDIT MAP to verify die map.\n"
            "- Verify all test sample plans.\n"
            "- DSA may not work."
        )
        warning.setContentsMargins(22, 0, 0, 0)
        root.addWidget(warning)
        root.addStretch(1)

        footer = QHBoxLayout()
        footer.addStretch(1)
        ok = QPushButton("OK")
        ok.setFixedWidth(105)
        ok.clicked.connect(self._accept_parameters)
        footer.addWidget(ok)
        footer.addSpacing(50)
        cancel = QPushButton("Cancel")
        cancel.setFixedWidth(105)
        cancel.clicked.connect(self.reject)
        footer.addWidget(cancel)
        footer.addStretch(1)
        root.addLayout(footer)

    def _optics_group(self) -> QFrame:
        group = QFrame()
        group.setObjectName("parameterGroup")
        group.setFixedSize(220, 250)
        title = QLabel("Optics")
        title.setObjectName("groupTitle")
        title.setParent(group)
        title.move(12, -1)

        layout = QVBoxLayout(group)
        layout.setContentsMargins(18, 20, 18, 14)
        layout.setSpacing(10)
        layout.addWidget(QLabel("Pixel Size"))
        self.pixel_size = QComboBox()
        self.pixel_size.addItems(["SL610", "SL8685", "SL8686"])
        self.pixel_size.setFixedWidth(170)
        layout.addWidget(self.pixel_size)
        layout.addSpacing(8)

        layout.addWidget(QLabel("Channel Used\nfor Alignment:"))
        self.channel = QComboBox()
        self.channel.addItems(["3 (Center)", "1 (Left)", "2 (Right)"])
        self.channel.setFixedWidth(170)
        layout.addWidget(self.channel)
        layout.addSpacing(8)

        advanced = QPushButton("Advanced Optics...")
        advanced.setFixedWidth(170)
        advanced.clicked.connect(self._open_advanced_optics)
        layout.addWidget(advanced)
        layout.addStretch(1)
        return group

    def _optics_used_group(self) -> QFrame:
        group = QFrame()
        group.setObjectName("parameterGroup")
        group.setFixedSize(165, 150)
        title = QLabel("Optics to be used")
        title.setObjectName("groupTitle")
        title.setParent(group)
        title.move(12, -1)

        layout = QVBoxLayout(group)
        layout.setContentsMargins(18, 18, 10, 12)
        self.user_defined = QRadioButton("User defined")
        self.user_defined.setChecked(True)
        self.production_optics = QRadioButton("Primary\nProduction\nTest's")
        self.production_optics.setEnabled(self.test_optics_defined)
        self.user_defined.toggled.connect(self._update_production_enabled)
        self.production_optics.toggled.connect(self._update_production_enabled)
        layout.addWidget(self.user_defined)
        layout.addWidget(self.production_optics)
        layout.addStretch(1)
        return group

    def _update_production_enabled(self):
        if hasattr(self, "production_test"):
            self.production_test.setEnabled(
                self.test_optics_defined and self.production_optics.isChecked()
            )

    def _open_advanced_optics(self):
        dialog = AdvancedOpticsDialog(self)
        dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()

    def _accept_parameters(self):
        self.keep_old_wafer_center = self.keep_center.isChecked()
        self.use_primary_production_test = self.production_optics.isChecked()
        self.accept()


class BFAlignmentParametersDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("BF Alignment Parameters")
        self.setFixedSize(430, 500)
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(
            """
            QDialog {
                background: #cfcac1;
                color: #111111;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10px;
            }
            QPushButton {
                background: #e7e4da;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-height: 24px;
                padding: 2px 10px;
            }
            QComboBox, QDoubleSpinBox, QSpinBox {
                background: #ffffff;
                border: 1px solid #77736b;
                min-height: 22px;
            }
            QComboBox:disabled {
                background: #d5d1c8;
                color: #7d7972;
            }
            QFrame#parameterGroup {
                border: 1px solid #8f8b82;
                background: #cfcac1;
            }
            QLabel#groupTitle {
                background: #cfcac1;
                padding: 0 4px;
                font-weight: 600;
            }
            """
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 28, 18, 18)
        root.setSpacing(12)

        root.addWidget(self._alignment_type_group())
        optics_row = QHBoxLayout()
        optics_row.setSpacing(28)
        self.low_mag_group = self._optics_group("Optics - Low Mag", "1.000 (10X)")
        self.high_mag_group = self._optics_group("Optics - High Mag", "0.200 (50X)")
        optics_row.addWidget(self.low_mag_group)
        optics_row.addWidget(self.high_mag_group)
        root.addLayout(optics_row)

        footer = QHBoxLayout()
        footer.addStretch(1)
        ok = QPushButton("OK")
        ok.setFixedWidth(92)
        ok.clicked.connect(self.accept)
        footer.addWidget(ok)
        footer.addSpacing(48)
        cancel = QPushButton("Cancel")
        cancel.setFixedWidth(92)
        cancel.clicked.connect(self.reject)
        footer.addWidget(cancel)
        footer.addStretch(1)
        root.addLayout(footer)

    def _alignment_type_group(self) -> QFrame:
        group = QFrame()
        group.setObjectName("parameterGroup")
        group.setFixedHeight(92)
        title = QLabel("Alignment Type")
        title.setObjectName("groupTitle")
        title.setParent(group)
        title.move(12, -1)

        layout = QVBoxLayout(group)
        layout.setContentsMargins(18, 18, 12, 10)
        self.dual_mag = QRadioButton("Standard Dual Magnification (low/high)")
        self.dual_mag.setChecked(True)
        self.single_mag = QRadioButton("Single Magnification (low=high)")
        self.dual_mag.toggled.connect(self._update_magnification_mode)
        layout.addWidget(self.dual_mag)
        layout.addWidget(self.single_mag)
        return group

    def _optics_group(self, title_text: str, pixel_size: str) -> QFrame:
        group = QFrame()
        group.setObjectName("parameterGroup")
        group.setFixedSize(170, 220)
        title = QLabel(title_text)
        title.setObjectName("groupTitle")
        title.setParent(group)
        title.move(12, -1)

        layout = QVBoxLayout(group)
        layout.setContentsMargins(14, 18, 14, 12)
        layout.setSpacing(5)

        layout.addWidget(QLabel("Imaging Mode"))
        imaging = QComboBox()
        imaging.addItem("BrightField")
        imaging.setEnabled(False)
        layout.addWidget(imaging)

        layout.addWidget(QLabel("Pixel Size"))
        pixel = QComboBox()
        pixel.addItems([pixel_size, "0.500 (20X)", "0.100 (100X)"])
        layout.addWidget(pixel)

        layout.addWidget(QLabel("Focus Offset"))
        focus = QDoubleSpinBox()
        focus.setDecimals(3)
        focus.setRange(-50.0, 50.0)
        focus.setSingleStep(0.001)
        focus.setValue(0.000)
        focus.setSuffix(" um")
        layout.addWidget(focus)

        layout.addWidget(QLabel("Aperture"))
        aperture = QSpinBox()
        aperture.setRange(0, 100)
        aperture.setValue(20)
        aperture.setSuffix(" %")
        layout.addWidget(aperture)

        advanced = QPushButton("Advanced Settings")
        advanced.clicked.connect(self._open_advanced_optics)
        layout.addWidget(advanced)
        return group

    def _update_magnification_mode(self, dual_enabled: bool):
        self.high_mag_group.setEnabled(dual_enabled)

    def _open_advanced_optics(self):
        dialog = AdvancedOpticsDialog(self)
        dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()


class QualifyWithTestOpticsDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Alignment Parameters")
        self.setFixedSize(610, 465)
        self.relearn_enabled = False
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(
            """
            QDialog {
                background: #cfcac1;
                color: #111111;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10px;
            }
            QPushButton {
                background: #e7e4da;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-height: 26px;
                padding: 2px 12px;
            }
            QComboBox {
                background: #ffffff;
                border: 1px solid #77736b;
                min-height: 24px;
            }
            QComboBox:disabled, QPushButton:disabled {
                color: #8a867e;
                background: #d8d4ca;
            }
            QFrame#parameterGroup {
                border: 1px solid #8f8b82;
                background: #cfcac1;
            }
            QLabel#groupTitle {
                background: #cfcac1;
                padding: 0 4px;
                font-weight: 600;
            }
            """
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(70, 34, 70, 28)
        root.setSpacing(18)

        top = QHBoxLayout()
        top.setSpacing(16)
        top.addWidget(self._optics_group())
        right = QVBoxLayout()
        right.addWidget(self._optics_used_group())
        self.relearn = QCheckBox("Re-learn")
        self.relearn.setEnabled(True)
        right.addSpacing(16)
        right.addWidget(self.relearn)
        right.addStretch(1)
        top.addLayout(right)
        root.addLayout(top)

        production_row = QHBoxLayout()
        production_row.addStretch(1)
        production_row.addWidget(QLabel("Primary Production Test:"))
        self.production_test = QComboBox()
        self.production_test.addItems(["1", "2", "3"])
        self.production_test.setFixedWidth(100)
        production_row.addWidget(self.production_test)
        production_row.addStretch(1)
        root.addLayout(production_row)
        root.addStretch(1)

        footer = QHBoxLayout()
        footer.addStretch(1)
        ok = QPushButton("OK")
        ok.setFixedWidth(112)
        ok.clicked.connect(self._accept_parameters)
        footer.addWidget(ok)
        footer.addSpacing(64)
        cancel = QPushButton("Cancel")
        cancel.setFixedWidth(112)
        cancel.clicked.connect(self.reject)
        footer.addWidget(cancel)
        footer.addStretch(1)
        root.addLayout(footer)

    def _optics_group(self) -> QFrame:
        group = QFrame()
        group.setObjectName("parameterGroup")
        group.setFixedSize(230, 260)
        title = QLabel("Optics")
        title.setObjectName("groupTitle")
        title.setParent(group)
        title.move(12, -1)

        layout = QVBoxLayout(group)
        layout.setContentsMargins(20, 20, 20, 14)
        layout.setSpacing(10)
        layout.addWidget(QLabel("Pixel Size"))
        pixel = QComboBox()
        pixel.addItems(["SL610"])
        pixel.setEnabled(False)
        pixel.setFixedWidth(170)
        layout.addWidget(pixel)
        layout.addSpacing(8)

        layout.addWidget(QLabel("Channel Used\nfor Alignment:"))
        channel = QComboBox()
        channel.addItems(["3 (Center)", "1 (Left)", "2 (Right)"])
        channel.setFixedWidth(170)
        layout.addWidget(channel)
        layout.addSpacing(8)

        advanced = QPushButton("Advanced Optics...")
        advanced.setEnabled(False)
        advanced.setFixedWidth(170)
        layout.addWidget(advanced)
        layout.addStretch(1)
        return group

    def _optics_used_group(self) -> QFrame:
        group = QFrame()
        group.setObjectName("parameterGroup")
        group.setFixedSize(195, 145)
        title = QLabel("Optics to be used")
        title.setObjectName("groupTitle")
        title.setParent(group)
        title.move(12, -1)

        layout = QVBoxLayout(group)
        layout.setContentsMargins(18, 18, 10, 12)
        user_defined = QRadioButton("User defined")
        user_defined.setEnabled(False)
        layout.addWidget(user_defined)
        production = QRadioButton("Primary\nProduction\nTest's")
        production.setChecked(True)
        layout.addWidget(production)
        layout.addStretch(1)
        return group

    def _accept_parameters(self):
        self.relearn_enabled = self.relearn.isChecked()
        self.accept()


class AlignmentSettingsDialog(QDialog):
    def __init__(
        self,
        use_pattern_matching: bool = True,
        high_precision_alignment: bool = False,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Alignment Settings")
        self.setFixedSize(390, 190)
        self.use_pattern_matching = use_pattern_matching
        self.high_precision_alignment = high_precision_alignment
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(
            """
            QDialog {
                background: #cfcac1;
                color: #111111;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10px;
            }
            QPushButton {
                background: #e7e4da;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-height: 24px;
                padding: 2px 18px;
            }
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(42, 28, 42, 20)
        layout.setSpacing(10)

        self.pattern_matching = QCheckBox("Use Pattern Matching for die corner selection")
        self.pattern_matching.setChecked(self.use_pattern_matching)
        layout.addWidget(self.pattern_matching)

        self.high_precision = QCheckBox("High Precision Alignment")
        self.high_precision.setChecked(self.high_precision_alignment)
        self.high_precision.setEnabled(True)
        layout.addWidget(self.high_precision)

        footer = QHBoxLayout()
        footer.addStretch(1)
        ok = QPushButton("OK")
        ok.setFixedWidth(100)
        ok.clicked.connect(self._accept_settings)
        footer.addWidget(ok)
        footer.addSpacing(46)
        cancel = QPushButton("Cancel")
        cancel.setFixedWidth(100)
        cancel.clicked.connect(self.reject)
        footer.addWidget(cancel)
        footer.addStretch(1)
        layout.addStretch(1)
        layout.addLayout(footer)

    def _accept_settings(self):
        self.use_pattern_matching = self.pattern_matching.isChecked()
        self.high_precision_alignment = self.high_precision.isChecked()
        self.accept()


class SelectAlignmentSitesDialog(QDialog):
    def __init__(
        self,
        mode: str,
        parent: Optional[QWidget] = None,
        existing_sites: Optional[list] = None,
        existing_images: Optional[list[str]] = None,
        bf_dual_magnification: bool = True,
    ):
        super().__init__(parent)
        self.mode = mode
        self.bf_dual_magnification = bool(bf_dual_magnification) if mode == "BF" else False
        self.marked_sites = [
            (float(point[0]), float(point[1]))
            for point in (existing_sites or [])[:2]
            if isinstance(point, (list, tuple)) and len(point) >= 2
        ]
        images = list(existing_images or [])[:2]
        default_images = (
            ["Sim Cross Mark 3 (BF)", "Sim Cross Mark Offset (BF)"]
            if self.mode == "BF"
            else SIMULATED_ALIGNMENT_IMAGES[:2]
        )
        self.site_images = []
        for index in range(2):
            image_name = images[index] if index < len(images) else ""
            image_matches_mode = (
                "(BF" in image_name
                if self.mode == "BF"
                else bool(image_name) and "(BF" not in image_name
            )
            self.site_images.append(image_name if image_matches_mode else default_images[index])
        self.current_site_index = 0
        self.focus_offset = 0.000
        self.aligned = False
        self.simulated_images = (
            ["Sim Cross Mark 3 (BF)", "Sim Cross Mark Offset (BF)"]
            if self.mode == "BF"
            else [*SIMULATED_ALIGNMENT_IMAGES[:2], SIMULATED_ALIGNMENT_IMAGES[3]]
        )
        self.current_simulated_image = self.simulated_images[0]
        self.generated_image_count = 0
        self.use_pattern_matching = True
        self.high_precision_alignment = False
        self.setWindowTitle("Select Alignment Sites")
        self.resize(1040, 760)
        self.setMinimumSize(940, 680)
        self._build_ui()
        self._load_existing_sites()
        self._refresh_state()

    def _load_existing_sites(self):
        self.wafer_view.marked_sites = list(self.marked_sites)
        for row, (x_value, y_value) in enumerate(self.marked_sites):
            self.site_table.setItem(row, 1, QTableWidgetItem(f"{x_value:.3f}"))
            self.site_table.setItem(row, 2, QTableWidgetItem(f"{y_value:.3f}"))
            self.site_table.setItem(row, 3, QTableWidgetItem(self.site_images[row]))
            self.quality_table.setItem(row, 1, QTableWidgetItem(f"{x_value:.1f}"))
            self.quality_table.setItem(row, 2, QTableWidgetItem(f"{y_value:.1f}"))
        if self.marked_sites:
            self.wafer_view.stage_position = self.marked_sites[0]

    def _build_ui(self):
        self.setStyleSheet(
            """
            QDialog {
                background: #e7e5d5;
                color: #111111;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10px;
            }
            QPushButton {
                background: #e7e4da;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-height: 22px;
                padding: 2px 10px;
            }
            QFrame#rightPanel, QFrame#bottomPanel {
                border: 1px solid #b8b3a5;
                background: #ece9d8;
            }
            QTableWidget {
                background: #fbfaf0;
                gridline-color: #bdb8aa;
            }
            QDoubleSpinBox, QComboBox {
                background: #ffffff;
                border: 1px solid #8f8b82;
                min-height: 20px;
            }
            """
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        content = QHBoxLayout()
        content.setSpacing(8)
        self.wafer_view = AlignmentSiteCanvas(self)
        content.addWidget(self.wafer_view, 1)
        content.addWidget(self._right_panel())
        root.addLayout(content, 1)

        bottom = QFrame()
        bottom.setObjectName("bottomPanel")
        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.setContentsMargins(8, 4, 8, 4)
        bottom_layout.setSpacing(4)
        self.cursor_label = QLabel()
        bottom_layout.addWidget(self.cursor_label)
        self.instruction_label = QLabel()
        self.instruction_label.setWordWrap(True)
        bottom_layout.addWidget(self.instruction_label)
        root.addWidget(bottom)

        footer = QHBoxLayout()
        self.prev_button = QPushButton("<< Prev")
        self.prev_button.clicked.connect(self._prev_site)
        footer.addWidget(self.prev_button)
        self.mark_button = QPushButton("Mark Site >>")
        self.mark_button.clicked.connect(self._mark_site)
        footer.addWidget(self.mark_button)
        self.next_button = QPushButton("Next >>")
        self.next_button.clicked.connect(self._next_site)
        footer.addWidget(self.next_button)
        self.align_button = QPushButton("Align")
        self.align_button.clicked.connect(self._align_sites)
        footer.addWidget(self.align_button)
        self.finish_button = QPushButton("Finish")
        self.finish_button.clicked.connect(self._finish_sites)
        footer.addWidget(self.finish_button)
        footer.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        footer.addWidget(cancel)
        root.addLayout(footer)

    def _right_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("rightPanel")
        panel.setFixedWidth(250)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        layout.addWidget(self._select_sites_orientation_group())

        title = QLabel("Site Coordinates")
        title.setStyleSheet("color: #1641d8;")
        layout.addWidget(title)
        self.site_table = QTableWidget(2, 4)
        self.site_table.setHorizontalHeaderLabels(["Site", "X", "Y", "Image"])
        self.site_table.verticalHeader().setVisible(False)
        self.site_table.setFixedHeight(92)
        for row in range(2):
            self.site_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            for column in range(1, 4):
                self.site_table.setItem(row, column, QTableWidgetItem(""))
        layout.addWidget(self.site_table)

        focus_title = QLabel("Focus Offset")
        focus_title.setStyleSheet("color: #1641d8;")
        layout.addWidget(focus_title)
        focus_row = QHBoxLayout()
        self.focus_spin = QDoubleSpinBox()
        self.focus_spin.setDecimals(3)
        self.focus_spin.setRange(-5.000, 5.000)
        self.focus_spin.setSingleStep(0.001)
        self.focus_spin.setSuffix(" um")
        self.focus_spin.valueChanged.connect(self._set_focus_from_spin)
        focus_row.addWidget(self.focus_spin)
        focus_button = QPushButton("Focus Offset")
        focus_button.clicked.connect(lambda: self.focus_spin.setFocus())
        focus_row.addWidget(focus_button)
        layout.addLayout(focus_row)

        image_display = QPushButton("Image Display...")
        image_display.clicked.connect(self._open_image_display)
        layout.addWidget(image_display)

        self.sim_image_label = QLabel()
        self.sim_image_label.setWordWrap(True)
        layout.addWidget(self.sim_image_label)
        generate_image = QPushButton("Acquire Sim Image")
        generate_image.clicked.connect(self._generate_simulated_image)
        layout.addWidget(generate_image)

        quality = QLabel("Alignment Quality")
        quality.setStyleSheet("color: #1641d8;")
        layout.addWidget(quality)
        self.quality_table = QTableWidget(3, 3)
        self.quality_table.setHorizontalHeaderLabels(["Site", "X", "Y"])
        self.quality_table.verticalHeader().setVisible(False)
        self.quality_table.setFixedHeight(96)
        for row, label in enumerate(["First", "Second", "Result"]):
            self.quality_table.setItem(row, 0, QTableWidgetItem(label))
            self.quality_table.setItem(row, 1, QTableWidgetItem(""))
            self.quality_table.setItem(row, 2, QTableWidgetItem(""))
        layout.addWidget(self.quality_table)

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        layout.addStretch(1)

        legend = QLabel(
            "<span style='color:#ff2d2d'>□</span> Current Position<br>"
            "<span style='color:#20b64a'>□</span> Marked Site<br>"
            "<span style='color:#6266ff'>□</span> Alignment Box"
        )
        layout.addWidget(legend)
        return panel

    def _select_sites_orientation_group(self) -> QFrame:
        group = QFrame()
        group.setObjectName("rightPanel")
        layout = QGridLayout(group)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setHorizontalSpacing(4)
        layout.setVerticalSpacing(4)

        title = QLabel("Orientation")
        title.setStyleSheet("color: #111111; font-weight: 600;")
        layout.addWidget(title, 0, 0, 1, 4)

        layout.addWidget(QLabel("Edit/Define Orientation:"), 1, 0, 1, 2)
        orientation = QComboBox()
        orientation.addItems(["Down (180 deg.)"])
        orientation.setEnabled(False)
        layout.addWidget(orientation, 1, 2, 1, 2)

        same = QRadioButton("Same as First Test")
        same.setChecked(True)
        layout.addWidget(same, 2, 0, 1, 4)
        down = QRadioButton("Down (180 deg.)")
        down.setEnabled(False)
        layout.addWidget(down, 3, 0, 1, 4)

        orientations = [("Up:", "Undefined"), ("Right:", "Undefined"), ("Down:", "Valid"), ("Left:", "Undefined")]
        for index, (label, state) in enumerate(orientations):
            row = 4 + index // 2
            column = (index % 2) * 2
            check = QCheckBox(label)
            layout.addWidget(check, row, column)
            state_button = QPushButton(state)
            state_button.setFixedWidth(72)
            state_button.setEnabled(False)
            layout.addWidget(state_button, row, column + 1)

        delete_alignment = QPushButton("Delete Alignment")
        delete_alignment.setEnabled(False)
        layout.addWidget(delete_alignment, 6, 0, 1, 2)
        settings = QPushButton("Settings...")
        settings.clicked.connect(self._open_alignment_settings)
        layout.addWidget(settings, 6, 2, 1, 2)

        self.high_precision_status = QLabel("High Precision Alignment: Off")
        self.high_precision_status.setStyleSheet("color: #1641d8;")
        layout.addWidget(self.high_precision_status, 7, 0, 1, 4)
        return group

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_F7:
            self._adjust_focus(-0.001)
            return
        if key == Qt.Key_F8:
            self._adjust_focus(0.001)
            return
        if key == Qt.Key_Left:
            self.move_stage(-100, 0)
            return
        if key == Qt.Key_Right:
            self.move_stage(100, 0)
            return
        if key == Qt.Key_Up:
            self.move_stage(0, 100)
            return
        if key == Qt.Key_Down:
            self.move_stage(0, -100)
            return
        super().keyPressEvent(event)

    def move_stage(self, dx: float, dy: float):
        x_value, y_value = self.wafer_view.stage_position
        self.wafer_view.stage_position = (x_value + dx, y_value + dy)
        self.wafer_view.update()
        self._refresh_state()

    def _set_focus_from_spin(self, value: float):
        self.focus_offset = value
        self.wafer_view.focus_offset = value
        self._refresh_state()
        self.wafer_view.update()

    def _adjust_focus(self, delta: float):
        self.focus_spin.setValue(self.focus_spin.value() + delta)

    def _mark_site(self):
        x_value, y_value = self.wafer_view.stage_position
        if not self._inside_alignment_box(x_value, y_value):
            QMessageBox.warning(
                self,
                "Alignment Site Boundary",
                "Select the alignment site inside the blue alignment box.",
            )
            return
        row = self.current_site_index
        if row == 1:
            if not self.marked_sites:
                QMessageBox.warning(self, "Select Alignment Sites", "Mark alignment site #1 before selecting site #2.")
                return
            first_x, first_y = self.marked_sites[0]
            if x_value - first_x < 200:
                QMessageBox.warning(
                    self,
                    "Alignment Site Limit",
                    "The second alignment site must be at least 200 um to the right of the first site.",
                )
                return
            if abs(y_value - first_y) > 2500:
                QMessageBox.warning(
                    self,
                    "Alignment Site Limit",
                    "Select the same high contrast area on an adjacent die.",
                )
                return

        image_name = self.current_simulated_image
        if row < len(self.marked_sites):
            self.marked_sites[row] = (x_value, y_value)
        else:
            self.marked_sites.append((x_value, y_value))
        self.site_images[row] = image_name
        self.aligned = False
        self.wafer_view.marked_sites = list(self.marked_sites)
        self.site_table.setItem(row, 1, QTableWidgetItem(f"{x_value:.3f}"))
        self.site_table.setItem(row, 2, QTableWidgetItem(f"{y_value:.3f}"))
        self.site_table.setItem(row, 3, QTableWidgetItem(image_name))
        self.quality_table.setItem(row, 1, QTableWidgetItem(f"{x_value:.1f}"))
        self.quality_table.setItem(row, 2, QTableWidgetItem(f"{y_value:.1f}"))
        self.quality_table.setItem(2, 1, QTableWidgetItem(""))
        self.quality_table.setItem(2, 2, QTableWidgetItem(""))
        self._advance_simulated_image()
        self._refresh_state()
        self.wafer_view.update()

    def _prev_site(self):
        if self.current_site_index == 0:
            return
        self.current_site_index = 0
        self._move_stage_to_current_site()
        self._refresh_state()

    def _next_site(self):
        if self.current_site_index == 0:
            if len(self.marked_sites) < 1:
                QMessageBox.warning(self, "Select Alignment Sites", "Mark alignment site #1 before continuing.")
                return
            self.current_site_index = 1
            self._move_stage_to_current_site()
            self._refresh_state()
            return
        if len(self.marked_sites) < 2:
            QMessageBox.warning(self, "Select Alignment Sites", "Mark alignment site #2 before continuing.")
            return
        self._align_sites()

    def _move_stage_to_current_site(self):
        if self.current_site_index < len(self.marked_sites):
            self.wafer_view.stage_position = self.marked_sites[self.current_site_index]
            self.wafer_view.update()
        elif self.current_site_index == 1 and self.marked_sites:
            first_x, first_y = self.marked_sites[0]
            self.wafer_view.stage_position = (first_x + 1000.0, first_y)
            self.wafer_view.update()

    def _align_sites(self):
        if len(self.marked_sites) < 2:
            QMessageBox.warning(self, "Select Alignment Sites", "Mark two alignment sites before clicking Align.")
            return
        if not self._has_valid_second_site():
            return
        self.aligned = True
        self.quality_table.setItem(2, 1, QTableWidgetItem("Scanned"))
        result = "High Precision" if self.high_precision_alignment else "Complete"
        self.quality_table.setItem(2, 2, QTableWidgetItem(result))
        suffix = " using High Precision Alignment" if self.high_precision_alignment else ""
        self.status_label.setText(f"Wafer scanned. Alignment completed{suffix} and site coordinates/images recorded.")
        self._refresh_state()
        self.wafer_view.update()

    def _finish_sites(self):
        if len(self.marked_sites) < 2:
            QMessageBox.warning(self, "Select Alignment Sites", "Mark both alignment sites before clicking Finish.")
            return
        if not self._has_valid_second_site():
            return
        if not self.aligned:
            self._align_sites()
        self.accept()

    def _has_valid_second_site(self) -> bool:
        first_x, first_y = self.marked_sites[0]
        second_x, second_y = self.marked_sites[1]
        if second_x - first_x < 200:
            QMessageBox.warning(
                self,
                "Alignment Site Limit",
                "Alignment site #2 must remain at least 200 um to the right of site #1.",
            )
            return False
        if abs(second_y - first_y) > 2500:
            QMessageBox.warning(
                self,
                "Alignment Site Limit",
                "Alignment site #2 must remain in the same high contrast area on an adjacent die.",
            )
            return False
        return True

    @staticmethod
    def _inside_alignment_box(x_value: float, y_value: float) -> bool:
        return -5000.0 <= x_value <= 5000.0 and -5000.0 <= y_value <= 5000.0

    def _open_alignment_settings(self):
        dialog = AlignmentSettingsDialog(
            self.use_pattern_matching,
            self.high_precision_alignment,
            self,
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.use_pattern_matching = dialog.use_pattern_matching
            self.high_precision_alignment = dialog.high_precision_alignment
            state = "On" if self.high_precision_alignment else "Off"
            self.high_precision_status.setText(f"High Precision Alignment: {state}")
            self.status_label.setText(f"High Precision Alignment {state.lower()}.")

    def _open_image_display(self):
        dialog = ImageDisplayWindow(self)
        dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        selected = dialog.current_image.currentText()
        if selected:
            self.current_simulated_image = selected
        self.status_label.setText("Inspection image acquired from Image Display Window.")
        self._refresh_state()

    def _generate_simulated_image(self):
        self.generated_image_count += 1
        x_value, y_value = self.wafer_view.stage_position
        image_name = f"Sim Cross Mark Capture {self.generated_image_count} ({x_value:.0f},{y_value:.0f})"
        self.simulated_images.append(image_name)
        self.current_simulated_image = image_name
        self.status_label.setText("Synthetic wafer cross-mark image generated for the current stage position.")
        self._refresh_state()

    def _advance_simulated_image(self):
        if not self.simulated_images:
            return
        try:
            index = self.simulated_images.index(self.current_simulated_image)
        except ValueError:
            index = -1
        self.current_simulated_image = self.simulated_images[(index + 1) % len(self.simulated_images)]

    def _refresh_state(self):
        x_value, y_value = self.wafer_view.stage_position
        self.cursor_label.setText(
            f"Cursor X: {x_value:.3f} um    Cursor Y: {y_value:.3f} um    Focus Offset: {self.focus_offset:.3f} um"
        )
        self.sim_image_label.setText(f"Current Image: {self.current_simulated_image}")
        self.site_table.selectRow(self.current_site_index)
        if self.aligned:
            instruction = "Alignment completed. Click Finish to return to the Alignment menu."
        elif self.current_site_index == 0 and len(self.marked_sites) == 0:
            instruction = (
                "Select alignment site #1 inside the blue alignment box. Move the stage/crosshair, "
                "then click Mark Site."
            )
            self.status_label.setText("Select alignment site #1.")
        elif self.current_site_index == 0:
            instruction = (
                "Alignment site #1 is selected. Click Next to keep it, or move the stage and click Mark Site "
                "to reselect/adjust this site."
            )
            self.status_label.setText("Review or adjust alignment site #1.")
        elif len(self.marked_sites) < 2:
            instruction = (
                "Select alignment site #2 on the same high contrast area of an adjacent die at least 200 um "
                "to the right of site #1, then click Mark Site."
            )
            self.status_label.setText("Select alignment site #2.")
        else:
            instruction = (
                "Alignment site #2 is selected. Click Finish to proceed beyond site #2, click Align to scan now, "
                "or click Prev to reselect a previous site."
            )
            self.status_label.setText("Ready to align or finish.")
        self.instruction_label.setText(instruction)
        self.prev_button.setEnabled(self.current_site_index > 0)
        self.next_button.setEnabled(
            (self.current_site_index == 0 and len(self.marked_sites) >= 1)
            or (self.current_site_index == 1 and len(self.marked_sites) >= 2 and not self.aligned)
        )
        self.align_button.setEnabled(len(self.marked_sites) == 2 and not self.aligned)
        self.finish_button.setEnabled(len(self.marked_sites) == 2)

    def note_snap(self):
        self.status_label.setText("Ctrl+click snap applied to nearest point/corner.")


class AlignmentSiteCanvas(QWidget):
    def __init__(self, dialog: SelectAlignmentSitesDialog):
        super().__init__(dialog)
        self.dialog = dialog
        self.stage_position = (-1800.0, 1200.0)
        self.marked_sites: list[tuple[float, float]] = []
        self.focus_offset = 0.000
        self.setMinimumSize(620, 540)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        point = self._event_position(event)
        self.stage_position = self._stage_from_screen(point.x(), point.y())
        if event.modifiers() & Qt.ControlModifier:
            x_value, y_value = self.stage_position
            self.stage_position = (round(x_value / 100.0) * 100.0, round(y_value / 100.0) * 100.0)
            self.dialog.note_snap()
        self.dialog._refresh_state()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#858583"))

        margin = 24
        size = min(self.width() - 48, self.height() - 72)
        left = margin
        top = 16
        if self.width() > size + 48:
            left = (self.width() - size) // 2
        wafer_rect = (left, top, size, size)
        painter.setBrush(QColor("#ffffff"))
        painter.setPen(QPen(QColor("#666666"), 1))
        painter.drawEllipse(*wafer_rect)

        box_left = left + int(size * 0.20)
        box_top = top + int(size * 0.30)
        box_width = int(size * 0.60)
        box_height = int(size * 0.34)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor("#6266ff"), 1))
        painter.drawRect(box_left, box_top, box_width, box_height)

        painter.setPen(QPen(QColor("#c9c9c9"), 1, Qt.DotLine))
        for index in range(1, 12):
            x_line = box_left + index * box_width // 12
            y_line = box_top + index * box_height // 12
            painter.drawLine(x_line, box_top, x_line, box_top + box_height)
            painter.drawLine(box_left, y_line, box_left + box_width, y_line)

        for index, (x_value, y_value) in enumerate(self.marked_sites, start=1):
            x_screen, y_screen = self._screen_from_stage(x_value, y_value)
            painter.setPen(QPen(QColor("#20b64a"), 2))
            painter.drawLine(x_screen - 9, y_screen, x_screen + 9, y_screen)
            painter.drawLine(x_screen, y_screen - 9, x_screen, y_screen + 9)
            painter.drawText(x_screen + 7, y_screen - 7, str(index))

        x_screen, y_screen = self._screen_from_stage(*self.stage_position)
        painter.setPen(QPen(QColor("#ff2d2d"), 1))
        painter.drawLine(x_screen - 12, y_screen, x_screen + 12, y_screen)
        painter.drawLine(x_screen, y_screen - 12, x_screen, y_screen + 12)
        painter.setPen(QPen(QColor("#111111"), 1))
        if self.dialog.mode == "BF" and self.dialog.bf_dual_magnification:
            imaging_label = "BF Standard Dual Magnification (Low/High)"
        else:
            imaging_label = f"{self.dialog.mode} Single Magnification"
        painter.drawText(left, top + size + 22, imaging_label)
        painter.drawText(left, top + size + 40, "Blue box marks valid alignment target area. Ctrl+click snaps to nearest point/corner.")

    def _screen_from_stage(self, x_value: float, y_value: float) -> tuple[int, int]:
        margin = 24
        size = min(self.width() - 48, self.height() - 72)
        left = margin if self.width() <= size + 48 else (self.width() - size) // 2
        top = 16
        box_left = left + int(size * 0.20)
        box_top = top + int(size * 0.30)
        box_width = int(size * 0.60)
        box_height = int(size * 0.34)
        x_screen = box_left + int((x_value + 5000.0) / 10000.0 * box_width)
        y_screen = box_top + int((5000.0 - y_value) / 10000.0 * box_height)
        return x_screen, y_screen

    def _stage_from_screen(self, x_screen: float, y_screen: float) -> tuple[float, float]:
        margin = 24
        size = min(self.width() - 48, self.height() - 72)
        left = margin if self.width() <= size + 48 else (self.width() - size) // 2
        top = 16
        box_left = left + int(size * 0.20)
        box_top = top + int(size * 0.30)
        box_width = int(size * 0.60)
        box_height = int(size * 0.34)
        x_clamped = max(box_left, min(box_left + box_width, x_screen))
        y_clamped = max(box_top, min(box_top + box_height, y_screen))
        x_value = ((x_clamped - box_left) / box_width) * 10000.0 - 5000.0
        y_value = 5000.0 - ((y_clamped - box_top) / box_height) * 10000.0
        return x_value, y_value

    @staticmethod
    def _event_position(event):
        return event.position() if hasattr(event, "position") else event.pos()


class DerivedSiteSelectionDialog(QDialog):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        has_old_corner: bool = False,
    ):
        super().__init__(parent)
        self.has_old_corner = bool(has_old_corner)
        self.selected_choice = "Select Die Origin"
        self.apply_site_offset = False
        self.setWindowTitle("Derived Site Selection")
        self.setFixedSize(360, 310)
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(
            """
            QDialog {
                background: #ece9d8;
                color: #111111;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10px;
            }
            QPushButton {
                background: #f1efe3;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-height: 24px;
                padding: 2px 18px;
            }
            QFrame#choiceGroup {
                border: 1px solid #d8d2bc;
                background: #ece9d8;
            }
            """
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 28, 26, 20)
        root.setSpacing(16)

        group = QFrame()
        group.setObjectName("choiceGroup")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(22, 18, 22, 16)
        title = QLabel("Choices")
        title.setStyleSheet("color: #1641d8; font-size: 13px;")
        layout.addWidget(title)

        self.old_corner = QRadioButton("Select Old Die Corner")
        self.old_corner.setEnabled(self.has_old_corner)
        self.old_corner.toggled.connect(self._refresh_site_offset)
        layout.addWidget(self.old_corner)
        self.die_origin = QRadioButton("Select Die Origin")
        self.die_origin.setChecked(True)
        self.die_origin.toggled.connect(self._refresh_site_offset)
        layout.addWidget(self.die_origin)
        self.site_offset = QCheckBox("Apply Site Offset")
        layout.addWidget(self.site_offset)
        self._refresh_site_offset()
        root.addWidget(group)

        ok = QPushButton("OK")
        ok.setFixedWidth(130)
        ok.clicked.connect(self._accept_choice)
        root.addWidget(ok, alignment=Qt.AlignCenter)

    def _accept_choice(self):
        self.selected_choice = "Select Die Origin" if self.die_origin.isChecked() else "Select Old Die Corner"
        self.apply_site_offset = self.site_offset.isChecked()
        self.accept()

    def _refresh_site_offset(self, *_args):
        enabled = self.has_old_corner and self.old_corner.isChecked()
        self.site_offset.setEnabled(enabled)
        if not enabled:
            self.site_offset.setChecked(False)


class LowMagDieCornerImageDialog(QDialog):
    def __init__(self, selection_mode: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.selection_mode = selection_mode
        self.marked_position: Optional[tuple[float, float]] = None
        self.setWindowTitle("Low Mag Die Corner Image")
        self.setFixedSize(430, 420)
        self._build_ui()
        self._refresh_status()

    def _build_ui(self):
        self.setStyleSheet(
            """
            QDialog {
                background: #e7e5d5;
                color: #111111;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10px;
            }
            QPushButton {
                background: #e7e4da;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-height: 22px;
                padding: 2px 10px;
            }
            QComboBox {
                background: #ffffff;
                border: 1px solid #8f8b82;
                min-height: 20px;
            }
            QFrame#statusStrip {
                background: #d5d1c7;
                border: 1px solid #aaa69c;
            }
            """
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Zoom:"))
        zoom = QComboBox()
        zoom.addItems(["100", "150", "200", "Fit"])
        zoom.setFixedWidth(66)
        toolbar.addWidget(zoom)
        toolbar.addStretch(1)
        root.addLayout(toolbar)

        self.image_view = LowMagDieCornerCanvas(self)
        root.addWidget(self.image_view, 1)

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        root.addWidget(self.status_label)

        buttons = QHBoxLayout()
        mark = QPushButton("Mark Site")
        mark.clicked.connect(self._mark_site)
        buttons.addWidget(mark)
        self.finish_button = QPushButton("Finish")
        self.finish_button.clicked.connect(self._finish)
        buttons.addWidget(self.finish_button)
        buttons.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)
        root.addLayout(buttons)

        strip = QFrame()
        strip.setObjectName("statusStrip")
        strip.setFixedHeight(22)
        strip_layout = QHBoxLayout(strip)
        strip_layout.setContentsMargins(6, 0, 6, 0)
        strip_layout.addWidget(QLabel("Use mouse or arrow keys to move the crosshair."))
        root.addWidget(strip)

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Left:
            self.image_view.move_crosshair(-5, 0)
            return
        if key == Qt.Key_Right:
            self.image_view.move_crosshair(5, 0)
            return
        if key == Qt.Key_Up:
            self.image_view.move_crosshair(0, -5)
            return
        if key == Qt.Key_Down:
            self.image_view.move_crosshair(0, 5)
            return
        super().keyPressEvent(event)

    def _mark_site(self):
        self.marked_position = self.image_view.crosshair_position
        self._refresh_status(marked=True)

    def _finish(self):
        if self.marked_position is None:
            QMessageBox.warning(self, "Low Mag Die Corner Image", "Mark the die origin site before clicking Finish.")
            return
        self.accept()

    def _refresh_status(self, marked: bool = False):
        x_value, y_value = self.image_view.crosshair_position
        prefix = "Marked" if marked else "Reselect"
        self.status_label.setText(
            f"{prefix} the die origin from the old inspection. "
            f"Crosshair X: {x_value:.0f}, Y: {y_value:.0f}"
        )


class LowMagDieCornerCanvas(QWidget):
    def __init__(self, dialog: LowMagDieCornerImageDialog):
        super().__init__(dialog)
        self.dialog = dialog
        self.crosshair_position = (105.0, 85.0)
        self.setMinimumSize(340, 245)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

    def move_crosshair(self, dx: float, dy: float):
        x_value, y_value = self.crosshair_position
        self.crosshair_position = (x_value + dx, y_value + dy)
        self._clamp_crosshair()
        self.dialog._refresh_status()
        self.update()

    def mousePressEvent(self, event):
        point = event.position() if hasattr(event, "position") else event.pos()
        self.crosshair_position = (point.x(), point.y())
        self._clamp_crosshair()
        self.dialog._refresh_status()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#e7e5d5"))
        image_rect = self.rect().adjusted(0, 0, -4, -44)
        image_rect.setWidth(min(180, image_rect.width()))
        image_rect.setHeight(min(160, image_rect.height()))
        painter.fillRect(image_rect, QColor("#061cff"))

        painter.setPen(QPen(QColor("#6dff6d"), 1))
        for x_offset in range(18, image_rect.width(), 28):
            painter.drawLine(image_rect.left() + x_offset, image_rect.top(), image_rect.left() + x_offset, image_rect.bottom())
        for y_offset in range(18, image_rect.height(), 28):
            painter.drawLine(image_rect.left(), image_rect.top() + y_offset, image_rect.right(), image_rect.top() + y_offset)

        x_value, y_value = self.crosshair_position
        x_value = max(image_rect.left(), min(image_rect.right(), x_value))
        y_value = max(image_rect.top(), min(image_rect.bottom(), y_value))
        painter.setPen(QPen(QColor("#00e060"), 2))
        painter.drawLine(int(x_value) - 55, int(y_value), int(x_value) + 55, int(y_value))
        painter.drawLine(int(x_value), int(y_value) - 55, int(x_value), int(y_value) + 55)
        painter.setPen(QPen(QColor("#ffffff"), 1))
        painter.drawText(image_rect.left() + 8, image_rect.bottom() + 20, "Old die origin image")
        painter.drawText(image_rect.left() + 8, image_rect.bottom() + 36, "Click Mark Site after reselecting the origin.")

    def _clamp_crosshair(self):
        image_rect = self.rect().adjusted(0, 0, -4, -44)
        image_rect.setWidth(min(180, image_rect.width()))
        image_rect.setHeight(min(160, image_rect.height()))
        x_value, y_value = self.crosshair_position
        self.crosshair_position = (
            max(image_rect.left(), min(image_rect.right(), x_value)),
            max(image_rect.top(), min(image_rect.bottom(), y_value)),
        )


class AutoSiteSelectionDialog(QDialog):
    TARGET_LOCATIONS = [
        ("low", "-71453.063", "66000.750"),
        ("low", "-64475.969", "55930.938"),
        ("high", "-71453.006", "66000.702"),
    ]

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Select Die Corner View")
        self.resize(1360, 760)
        self.setMinimumSize(1240, 680)
        self.corner_count = 0
        self.use_pattern_matching = True
        self.high_precision_alignment = False
        self.quality_targets = {
            metric: dict(values)
            for metric, values in DEFAULT_ALIGNMENT_QUALITY_TARGETS.items()
        }
        self.quality_candidates = []
        self.quality_result = {}
        self._build_ui()
        self.quality_table.itemChanged.connect(self._quality_target_changed)
        self._refresh_step_state()

    def _build_ui(self):
        self.setStyleSheet(
            """
            QDialog {
                background: #e8e4d3;
                color: #111111;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10px;
            }
            QPushButton {
                background: #f1efe3;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-height: 22px;
                padding: 2px 10px;
            }
            QPushButton:disabled, QLineEdit:disabled {
                color: #8f8b82;
                background: #ded9c8;
            }
            QFrame#rightPanel, QFrame#instructionPanel {
                border: 1px solid #c8c1aa;
                background: #e8e4d3;
            }
            QFrame#targetPanel {
                border: 1px solid #d8d1ba;
                background: #e8e4d3;
            }
            QLabel[blueTitle="true"] {
                color: #0a55e5;
                background: #e8e4d3;
            }
            QTableWidget {
                background: #f7f5e9;
                border: 1px solid #c8c1aa;
                gridline-color: #d2ccb8;
            }
            """
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(6)

        body = QHBoxLayout()
        body.setSpacing(8)
        self.wafer_view = DieCornerSelectionView(self)
        body.addWidget(self.wafer_view, 1)
        body.addWidget(self._right_panel(), 0)
        root.addLayout(body, 1)

        root.addWidget(self._instruction_panel())
        root.addLayout(self._footer())

    def _right_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("rightPanel")
        panel.setFixedWidth(600)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)
        layout.addWidget(self._target_location_panel())
        layout.addWidget(self._alignment_order_panel())
        layout.addSpacing(12)
        quality_tables = QHBoxLayout()
        quality_tables.setSpacing(10)
        target_column = QVBoxLayout()
        target_column.setSpacing(3)
        target_title = QLabel("Target Quality Scores")
        target_title.setToolTip("Each applicable measured score must be greater than or equal to its target.")
        target_column.addWidget(target_title)
        self.quality_table = self._quality_table()
        target_column.addWidget(self.quality_table)
        quality_tables.addLayout(target_column)
        candidate_column = QVBoxLayout()
        candidate_column.setSpacing(3)
        candidate_column.addWidget(QLabel("Selected Candidate Scores"))
        self.candidate_quality_table = self._quality_table(editable=False)
        candidate_column.addWidget(self.candidate_quality_table)
        quality_tables.addLayout(candidate_column)
        layout.addLayout(quality_tables)
        self.quality_status = QLabel("Waiting for die-corner selection")
        self.quality_status.setWordWrap(True)
        self.quality_status.setToolTip(
            "PASS requires every applicable Correlation, Uniqueness, Sharpness, and Feature score to meet its target."
        )
        layout.addWidget(self.quality_status)
        layout.addStretch(1)
        legend_title = QLabel("Legend")
        legend_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(legend_title)
        layout.addWidget(self._legend_panel())
        self.event_log = QTableWidget(2, 1)
        self.event_log.horizontalHeader().setVisible(False)
        self.event_log.verticalHeader().setVisible(False)
        self.event_log.setFixedHeight(58)
        self.event_log.setItem(0, 0, QTableWidgetItem(""))
        self.event_log.setItem(1, 0, QTableWidgetItem(""))
        layout.addWidget(self.event_log)
        return panel

    def _alignment_order_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("targetPanel")
        layout = QGridLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setHorizontalSpacing(6)
        layout.setVerticalSpacing(5)
        layout.addWidget(QLabel("Alignment Order"), 0, 0, 1, 2)
        df = QCheckBox("DF")
        df.setChecked(True)
        layout.addWidget(df, 1, 0)
        settings = QPushButton("Settings...")
        settings.setFixedWidth(92)
        settings.clicked.connect(self._open_alignment_settings)
        layout.addWidget(settings, 1, 1)
        layout.addWidget(QLabel("Desired Candidates"), 2, 0)
        self.desired_candidates = QSpinBox()
        self.desired_candidates.setRange(1, 9)
        self.desired_candidates.setValue(3)
        self.desired_candidates.setToolTip(
            "Number of candidate target images acquired by Auto Site Selection."
        )
        self.desired_candidates.valueChanged.connect(self._desired_candidate_count_changed)
        layout.addWidget(self.desired_candidates, 2, 1)
        return panel

    def _target_location_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("targetPanel")
        layout = QGridLayout(panel)
        layout.setContentsMargins(10, 10, 10, 8)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(6)
        title = QLabel("Target Location")
        title.setProperty("blueTitle", True)
        layout.addWidget(title, 0, 0, 1, 4)
        layout.addWidget(QLabel("Low Mag"), 0, 2, alignment=Qt.AlignCenter)
        layout.addWidget(QLabel("X:"), 1, 0)
        self.low_x_location = self._disabled_location("")
        layout.addWidget(self.low_x_location, 1, 1)
        layout.addWidget(QLabel("Y:"), 1, 2)
        self.low_y_location = self._disabled_location("")
        layout.addWidget(self.low_y_location, 1, 3)
        layout.addWidget(QLabel("High Mag"), 2, 2, alignment=Qt.AlignCenter)
        layout.addWidget(QLabel("X:"), 3, 0)
        self.high_x_location = self._disabled_location("")
        layout.addWidget(self.high_x_location, 3, 1)
        layout.addWidget(QLabel("Y:"), 3, 2)
        self.high_y_location = self._disabled_location("")
        layout.addWidget(self.high_y_location, 3, 3)
        return panel

    @staticmethod
    def _disabled_location(value: str) -> QLineEdit:
        field = QLineEdit(value)
        field.setEnabled(False)
        field.setFixedWidth(54)
        return field

    def _quality_table(self, *, editable: bool = True) -> QTableWidget:
        table = QTableWidget(4, 3)
        table.setHorizontalHeaderLabels(["Align", "X Reg", "Y Reg"])
        table.setVerticalHeaderLabels(["Correlation", "Uniqueness", "Sharpness", "Feature"])
        table.setFixedHeight(112)
        table.setFixedWidth(286)
        for row in range(4):
            table.setRowHeight(row, 20)
            for column in range(3):
                item = QTableWidgetItem("")
                if not editable:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                table.setItem(row, column, item)
        table.setItem(0, 1, QTableWidgetItem("N/A"))
        table.setItem(0, 2, QTableWidgetItem("N/A"))
        if not editable:
            for column in (1, 2):
                item = table.item(0, column)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        else:
            for column in (1, 2):
                item = table.item(0, column)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        table.verticalHeader().setFixedWidth(92)
        for column in range(3):
            table.setColumnWidth(column, 58)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        return table

    def _legend_panel(self) -> QWidget:
        panel = QWidget()
        grid = QGridLayout(panel)
        grid.setContentsMargins(2, 2, 2, 2)
        grid.setHorizontalSpacing(2)
        grid.setVerticalSpacing(1)
        items = [
            ("#f05050", "Current Position"),
            ("#00b050", "Single Mag Site"),
            ("#ff944d", "Old First Site"),
            ("#00cc66", "Reselected First Site"),
            ("#808080", "Street Point"),
        ]
        for index, (color, text) in enumerate(items):
            marker = QLabel("")
            marker.setFixedSize(12, 12)
            marker.setStyleSheet(f"background: {color}; border: 1px solid #555555;")
            grid.addWidget(marker, index // 2, (index % 2) * 2)
            grid.addWidget(QLabel(text), index // 2, (index % 2) * 2 + 1)
        return panel

    def _instruction_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("instructionPanel")
        panel.setFixedHeight(62)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(6, 4, 6, 4)
        self.mag_label = QLabel("DF Single Mag")
        self.mag_label.setAlignment(Qt.AlignCenter)
        self.instruction_label = QLabel("")
        self.instruction_label.setAlignment(Qt.AlignCenter)
        self.instruction_label.setWordWrap(True)
        layout.addWidget(self.mag_label)
        layout.addWidget(self.instruction_label)
        return panel

    def _footer(self) -> QHBoxLayout:
        footer = QHBoxLayout()
        footer.setSpacing(8)
        self.prev_button = QPushButton("<< Prev")
        self.prev_button.setEnabled(False)
        self.prev_button.clicked.connect(self._previous_step)
        self.mark_button = QPushButton("Mark Die Corner >>")
        self.mark_button.clicked.connect(self._mark_die_corner)
        advanced = QPushButton("Advanced...")
        advanced.setToolTip("Advanced Inspection Optics Settings")
        advanced.clicked.connect(self._open_advanced_inspection_optics)
        self.next_button = QPushButton("Next >>")
        self.next_button.clicked.connect(self._next_step)
        self.finish_button = QPushButton("Finish")
        self.finish_button.setEnabled(False)
        self.finish_button.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)

        for button in [self.prev_button, self.mark_button, advanced, self.next_button, self.finish_button, cancel]:
            button.setFixedWidth(96)
        footer.addWidget(self.prev_button)
        footer.addWidget(self.mark_button)
        footer.addWidget(advanced)
        footer.addWidget(self.next_button)
        footer.addWidget(self.finish_button)
        footer.addStretch(1)
        footer.addWidget(cancel)
        return footer

    def _mark_die_corner(self):
        self.corner_count = min(3, self.corner_count + 1)
        self.wafer_view.marked_corners = self.corner_count
        self.wafer_view.show_move_stage = self.corner_count >= 1
        self._update_target_location()
        self.wafer_view.update()
        if self.corner_count == 1:
            self.event_log.setItem(0, 0, QTableWidgetItem("First die corner marked."))
        elif self.corner_count == 2:
            self.event_log.setItem(0, 0, QTableWidgetItem("Street marked. Select Second Die Corner view displayed."))
        else:
            self.event_log.setItem(1, 0, QTableWidgetItem("Second die corner marked. Auto Site Selection begins."))
            self._populate_target_quality_scores()
        self._refresh_step_state()

    def _previous_step(self):
        if self.corner_count <= 0:
            return
        self.corner_count -= 1
        self.wafer_view.marked_corners = self.corner_count
        self.wafer_view.show_move_stage = self.corner_count >= 1
        self._clear_target_quality_scores()
        self._update_target_location()
        self.event_log.setItem(0, 0, QTableWidgetItem("Previous die corner step restored."))
        self.event_log.setItem(1, 0, QTableWidgetItem(""))
        self.wafer_view.update()
        self._refresh_step_state()

    def _open_alignment_settings(self):
        dialog = AlignmentSettingsDialog(
            self.use_pattern_matching,
            self.high_precision_alignment,
            self,
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.use_pattern_matching = dialog.use_pattern_matching
            self.high_precision_alignment = dialog.high_precision_alignment
            state = "enabled" if self.high_precision_alignment else "disabled"
            self.event_log.setItem(0, 0, QTableWidgetItem(f"High Precision Alignment {state}."))
            if self.corner_count >= 3:
                self._run_quality_selection()

    def _open_advanced_inspection_optics(self):
        dialog = AdvancedOpticsDialog(self)
        dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        self.event_log.setItem(0, 0, QTableWidgetItem("Advanced Inspection Optics Settings closed."))

    def _next_step(self):
        if self.corner_count < 3:
            self.event_log.setItem(0, 0, QTableWidgetItem("Mark the first corner, street corner, and second die corner before continuing."))
            return
        self.finish_button.setEnabled(True)
        self.next_button.setEnabled(False)
        self.mark_button.setEnabled(False)
        self.instruction_label.setText("Die corners selected. Click Finish to complete automatic alignment site selection.")

    def _refresh_step_state(self):
        self.prev_button.setEnabled(self.corner_count > 0)
        self.next_button.setEnabled(True)
        self.finish_button.setEnabled(False)
        self.mark_button.setEnabled(self.corner_count < 3)
        if self.corner_count == 0:
            self.instruction_label.setText(
                "Select first die corner: Use Stage Movement Control to select the lower left corner of a die. "
                "Click Mark Die Corner. For derivative recipe, you can press Ctrl + Left Mouse click to snap to the nearest point/corner."
            )
        elif self.corner_count == 1:
            self.instruction_label.setText(
                "Select the lower-left corner of the die diagonally adjacent and to the right of the first die. "
                "Click Mark Die Corner to mark the street."
            )
        elif self.corner_count == 2:
            self.instruction_label.setText(
                "Select Second Die Corner view: Use the same method to locate the second die corner, then click Mark Die Corner."
            )
        else:
            self.instruction_label.setText(
                "Auto Site Selection begins. When you are satisfied with the target site quality, click Finish."
            )
            self.finish_button.setEnabled(True)

    def _populate_target_quality_scores(self):
        self.quality_table.blockSignals(True)
        for row, metric in enumerate(ALIGNMENT_QUALITY_ROWS):
            for column, axis in enumerate(ALIGNMENT_QUALITY_COLUMNS):
                value = self.quality_targets[metric][axis]
                text = "N/A" if value is None else self._format_quality_value(metric, value)
                item = QTableWidgetItem(text)
                if value is None:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.quality_table.setItem(row, column, item)
        self.quality_table.blockSignals(False)
        self._run_quality_selection()

    def _clear_target_quality_scores(self):
        self.quality_table.blockSignals(True)
        for row in range(4):
            for column in range(3):
                self.quality_table.setItem(row, column, QTableWidgetItem(""))
        for column in (1, 2):
            item = QTableWidgetItem("N/A")
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.quality_table.setItem(0, column, item)
        self.quality_table.blockSignals(False)
        self._clear_candidate_quality_scores()

    def _quality_target_changed(self):
        if self.corner_count < 3:
            return
        targets = self._read_quality_targets()
        if targets is None:
            self.quality_status.setText("INVALID TARGET - enter a positive numeric value in every applicable cell")
            self.quality_status.setStyleSheet("color: #b42318; font-weight: 700;")
            return
        self.quality_targets = targets
        self._run_quality_selection()

    def _desired_candidate_count_changed(self):
        if self.corner_count >= 3:
            self._run_quality_selection()

    def _read_quality_targets(self) -> Optional[dict]:
        targets = {}
        for row, metric in enumerate(ALIGNMENT_QUALITY_ROWS):
            targets[metric] = {}
            for column, axis in enumerate(ALIGNMENT_QUALITY_COLUMNS):
                if metric == "correlation" and axis != "align":
                    targets[metric][axis] = None
                    continue
                item = self.quality_table.item(row, column)
                try:
                    value = float((item.text() if item else "").replace(",", ""))
                except ValueError:
                    return None
                if value <= 0:
                    return None
                targets[metric][axis] = value
        return targets

    def _run_quality_selection(self):
        targets = self._read_quality_targets()
        if targets is None:
            return
        self.quality_targets = targets
        candidates = []
        for candidate_number in range(1, self.desired_candidates.value() + 1):
            scores = simulated_alignment_candidate_scores(
                candidate_number,
                targets,
                use_pattern_matching=self.use_pattern_matching,
                high_precision_alignment=self.high_precision_alignment,
            )
            evaluation = evaluate_alignment_quality(scores, targets)
            candidates.append(
                {
                    "candidate": candidate_number,
                    "scores": scores,
                    "evaluation": evaluation,
                }
            )
        selected = max(candidates, key=self._candidate_rank)
        self.quality_candidates = candidates
        self.quality_result = {
            "targets": {metric: dict(values) for metric, values in targets.items()},
            "desired_candidates": self.desired_candidates.value(),
            "candidates": candidates,
            "selected_candidate": selected["candidate"],
            "scores": selected["scores"],
            "evaluation": selected["evaluation"],
            "qualified": selected["evaluation"]["qualified"],
        }
        self._display_candidate_quality(selected)

    def _candidate_rank(self, candidate: dict):
        evaluation = candidate["evaluation"]
        ratios = []
        for metric in ALIGNMENT_QUALITY_ROWS:
            for axis in ALIGNMENT_QUALITY_COLUMNS:
                target = self.quality_targets[metric][axis]
                actual = candidate["scores"][metric][axis]
                if target is not None and actual is not None:
                    ratios.append(float(actual) / float(target))
        return evaluation["passed"], sum(ratios)

    def _display_candidate_quality(self, selected: dict):
        scores = selected["scores"]
        checks = selected["evaluation"]["checks"]
        for row, metric in enumerate(ALIGNMENT_QUALITY_ROWS):
            for column, axis in enumerate(ALIGNMENT_QUALITY_COLUMNS):
                value = scores[metric][axis]
                item = QTableWidgetItem(
                    "N/A" if value is None else self._format_quality_value(metric, value)
                )
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                passed = checks[metric][axis]
                if passed is not None:
                    item.setBackground(QColor("#d7ecd3" if passed else "#f1cbc6"))
                    target = self.quality_targets[metric][axis]
                    comparison = ">=" if passed else "<"
                    item.setToolTip(
                        f"Measured {self._format_quality_value(metric, value)} {comparison} "
                        f"target {self._format_quality_value(metric, target)}"
                    )
                self.candidate_quality_table.setItem(row, column, item)
        evaluation = selected["evaluation"]
        result = "PASS" if evaluation["qualified"] else "NOT QUALIFIED"
        self.quality_status.setText(
            f"Candidate {selected['candidate']} of {self.desired_candidates.value()} | "
            f"{result} - {evaluation['passed']}/{evaluation['applicable']} targets met"
        )
        self.quality_status.setStyleSheet(
            "color: #176b2c; font-weight: 700;"
            if evaluation["qualified"]
            else "color: #b42318; font-weight: 700;"
        )
        self.event_log.setItem(
            1,
            0,
            QTableWidgetItem(
                f"Candidate {selected['candidate']} selected; "
                f"{evaluation['passed']}/{evaluation['applicable']} quality targets met."
            ),
        )

    def _clear_candidate_quality_scores(self):
        self.quality_candidates = []
        self.quality_result = {}
        for row, metric in enumerate(ALIGNMENT_QUALITY_ROWS):
            for column, axis in enumerate(ALIGNMENT_QUALITY_COLUMNS):
                text = "N/A" if metric == "correlation" and axis != "align" else ""
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.candidate_quality_table.setItem(row, column, item)
        self.quality_status.setText("Waiting for die-corner selection")
        self.quality_status.setStyleSheet("")

    @staticmethod
    def _format_quality_value(metric: str, value: float) -> str:
        if metric == "feature":
            return f"{int(round(float(value)))}"
        return f"{float(value):.2f}"

    def overview_scores(self, mode: str = "DF") -> dict:
        scores = self.quality_result.get("scores") or {}

        def row_text(metric: str) -> str:
            values = scores.get(metric) or {}
            return " / ".join(
                "N/A" if values.get(axis) is None else self._format_quality_value(metric, values[axis])
                for axis in ALIGNMENT_QUALITY_COLUMNS
            )

        return {
            "type": mode,
            "df_scores": "Align / X Reg / Y Reg",
            "correlation": row_text("correlation"),
            "uniqueness": row_text("uniqueness"),
            "sharpness": row_text("sharpness"),
            "features": row_text("feature"),
        }

    def _update_target_location(self):
        self.low_x_location.setText("")
        self.low_y_location.setText("")
        self.high_x_location.setText("")
        self.high_y_location.setText("")
        if self.corner_count <= 0:
            return
        mag, x_value, y_value = self.TARGET_LOCATIONS[min(self.corner_count, 3) - 1]
        if mag == "low":
            self.low_x_location.setText(x_value)
            self.low_y_location.setText(y_value)
        else:
            self.high_x_location.setText(x_value)
            self.high_y_location.setText(y_value)

    def _snap_to_nearest_corner(self):
        self.event_log.setItem(0, 0, QTableWidgetItem("Ctrl+click snap applied to nearest point/corner."))


class DieCornerSelectionView(QWidget):
    def __init__(self, dialog: Optional[AutoSiteSelectionDialog] = None):
        super().__init__(dialog)
        self.dialog = dialog
        self.setMinimumSize(650, 560)
        self.marked_corners = 0
        self.show_move_stage = False

    def mousePressEvent(self, event):  # noqa: N802 - Qt override
        if event.button() == Qt.LeftButton and event.modifiers() & Qt.ControlModifier:
            if self.dialog:
                self.dialog._snap_to_nearest_corner()
            event.accept()
            return
        super().mousePressEvent(event)

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#858583"))

        rect = self.rect().adjusted(55, 18, -55, -54)
        side = min(rect.width(), rect.height())
        center_x = rect.center().x()
        center_y = rect.center().y() + 8
        wafer_rect = (
            center_x - side // 2,
            center_y - side // 2,
            side,
            side,
        )
        painter.setBrush(QColor("#ffffff"))
        painter.setPen(QPen(QColor("#666666"), 1))
        painter.drawEllipse(*wafer_rect)

        die_rect = self._die_rect(center_x, center_y, side)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor("#6266ff"), 1))
        painter.drawRect(*die_rect)

        painter.setPen(QPen(QColor("#ff3a3a"), 1))
        painter.drawLine(center_x - 9, center_y, center_x + 9, center_y)
        painter.drawLine(center_x, center_y - 9, center_x, center_y + 9)
        painter.setPen(QPen(QColor("#20d04a"), 1))
        painter.drawLine(center_x - 4, center_y + 8, center_x + 10, center_y + 8)
        painter.drawLine(center_x + 3, center_y + 1, center_x + 3, center_y + 15)

        if self.marked_corners >= 1:
            x, y, _, h = die_rect
            self._draw_corner_marker(painter, x, y + h, "#f05050")
        if self.marked_corners >= 2:
            x, y, w, h = die_rect
            self._draw_street_marker(painter, x + int(w * 0.72), y + h, "#ff944d")
        if self.marked_corners >= 3:
            x, y, w, _ = die_rect
            self._draw_corner_marker(painter, x + w, y, "#00b050")

        if self.show_move_stage:
            self._draw_move_stage(painter, 10, self.height() - 150)

    @staticmethod
    def _die_rect(center_x: int, center_y: int, wafer_side: int):
        width = int(wafer_side * 0.72)
        height = int(wafer_side * 0.36)
        return center_x - width // 2, center_y - height // 2, width, height

    @staticmethod
    def _draw_corner_marker(painter: QPainter, x: int, y: int, color: str):
        painter.setPen(QPen(QColor(color), 2))
        painter.drawLine(x - 8, y, x + 8, y)
        painter.drawLine(x, y - 8, x, y + 8)

    @staticmethod
    def _draw_street_marker(painter: QPainter, x: int, y: int, color: str):
        painter.setPen(QPen(QColor(color), 2))
        painter.drawLine(x - 10, y, x + 10, y)
        painter.drawLine(x, y - 10, x, y + 10)
        painter.drawLine(x - 10, y + 10, x + 10, y + 10)

    def _draw_move_stage(self, painter: QPainter, x: int, y: int):
        painter.setPen(QPen(QColor("#ffffff"), 1))
        painter.setBrush(QColor("#3156e8"))
        painter.drawRect(x, y, 58, 92)
        painter.setPen(QPen(QColor("#ffffff"), 1))
        painter.drawText(x + 7, y + 12, "Move Stage")
        positions = [
            (0, 0, "\\"),
            (1, 0, "^"),
            (2, 0, "/"),
            (0, 1, "<"),
            (2, 1, ">"),
            (0, 2, "/"),
            (1, 2, "v"),
            (2, 2, "\\"),
        ]
        for column, row, text in positions:
            bx = x + 6 + column * 16
            by = y + 20 + row * 15
            painter.setBrush(QColor("#f6f6f6"))
            painter.setPen(QPen(QColor("#1641d8"), 1))
            painter.drawRect(bx, by, 13, 13)
            painter.drawText(bx + 3, by + 10, text)
        painter.setPen(QPen(QColor("#111111"), 1))
        painter.setBrush(QColor("#ffffff"))
        painter.drawRect(x + 7, y + 70, 44, 16)
        painter.drawText(x + 11, y + 82, "10 um")

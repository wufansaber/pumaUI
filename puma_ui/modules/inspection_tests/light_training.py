from __future__ import annotations

from copy import deepcopy
from math import exp, hypot

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
    QMessageBox,
    QPainter,
    QPen,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSlider,
    QSizePolicy,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    Qt,
    QVBoxLayout,
    QWidget,
)
from ...simulation_imaging import paint_simulated_die


def default_light_training_state() -> dict:
    return {
        "trained": False,
        "noise_box": [0.28, 0.30, 0.30, 0.10],
        "noise_box_group": "",
        "active_regions": [],
        "active_regions_enabled": False,
        "algorithm": "Puma Illumination Level Optimization",
        "dynamic_range": "Extended",
        "endpoint_mode": "Auto",
        "high_endpoint": 3480,
        "density": 0.001,
        "capture_noise_box_image": True,
        "focus_offset_um": 0.0,
        "focus_trained": False,
        "sample_dies": [[0, 0]],
        "channels": [
            {"name": "1 (Left)", "light_level": 8.64, "exposure": 1.0, "edr": 16.0},
            {"name": "2 (Right)", "light_level": 7.41, "exposure": 1.0, "edr": 16.0},
            {"name": "3 (Center)", "light_level": 2.26, "exposure": 1.0, "edr": 16.0},
        ],
    }


def normalized_light_training_state(state: dict | None) -> dict:
    result = default_light_training_state()
    if isinstance(state, dict):
        result.update(deepcopy(state))
    try:
        density = float(result.get("density", 0.001))
    except (TypeError, ValueError):
        density = 0.001
    result["density"] = density if 0.0 < density <= 1.0 else 0.001
    result["capture_noise_box_image"] = bool(
        result.get("capture_noise_box_image", True)
    )
    try:
        result["focus_offset_um"] = float(result.get("focus_offset_um", 0.0))
    except (TypeError, ValueError):
        result["focus_offset_um"] = 0.0
    result["focus_trained"] = bool(result.get("focus_trained", False))
    return result


def _contains(outer, inner) -> bool:
    ox, oy, ow, oh = [float(value) for value in outer[:4]]
    ix, iy, iw, ih = [float(value) for value in inner[:4]]
    return ix >= ox and iy >= oy and ix + iw <= ox + ow and iy + ih <= oy + oh


def _intersects(first, second) -> bool:
    ax, ay, aw, ah = [float(value) for value in first[:4]]
    bx, by, bw, bh = [float(value) for value in second[:4]]
    return ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by


def eligible_light_training_groups(care_areas) -> list[str]:
    return [
        group.get("name", "")
        for group in (care_areas or {}).get("groups", [])
        if group.get("enabled", True)
        and group.get("areas")
        and "Page Break" not in group.get("kind", "")
    ]


def validate_light_training_state(
    state,
    focus_mode="Median Die",
    care_areas=None,
    die_size_um=(5100.0, 16600.0),
):
    state = normalized_light_training_state(state)
    errors = []
    if not state.get("sample_dies"):
        errors.append("select at least one Light Level training die")
    if state.get("active_regions_enabled") and focus_mode != "Active Die":
        errors.append("Active Regions require Focus Mode Active Die")
    if state.get("active_regions_enabled") and not state.get("active_regions"):
        errors.append("enabled Active Regions require at least one region")
    for index, region in enumerate(state.get("active_regions", []), start=1):
        try:
            x, y, width, height = [float(value) for value in region[:4]]
        except (TypeError, ValueError):
            errors.append(f"Active Region {index} requires numeric geometry")
            continue
        if width <= 0 or height <= 0:
            errors.append(f"Active Region {index} requires positive width and height")
        elif x < 0 or y < 0 or x + width > 1 or y + height > 1:
            errors.append(f"Active Region {index} must remain inside the die")
    if state.get("algorithm", "").startswith("Puma"):
        if not state.get("noise_box"):
            errors.append("PILO requires a Light Training Noise Box")
        else:
            x, y, width, height = [float(value) for value in state["noise_box"]]
            die_width_um, die_height_um = [
                max(1.0, float(value)) for value in die_size_um[:2]
            ]
            if width * die_width_um > 2000.0 or height * die_height_um > 2000.0:
                errors.append("PILO Noise Box exceeds the 2000 x 2000 um limit")
            if x < 0 or y < 0 or x + width > 1 or y + height > 1:
                errors.append("Light Training Noise Box must remain inside the die")
            if care_areas is not None:
                group_name = state.get("noise_box_group", "")
                eligible = eligible_light_training_groups(care_areas)
                if not group_name and len(eligible) == 1:
                    group_name = eligible[0]
                group = next(
                    (
                        item for item in care_areas.get("groups", [])
                        if item.get("name") == group_name
                    ),
                    None,
                )
                if group_name not in eligible or group is None:
                    errors.append(
                        "select an enabled Care Area for the PILO Noise Box"
                    )
                elif not any(_contains(area, state["noise_box"]) for area in group.get("areas", [])):
                    errors.append("PILO Noise Box must remain inside the selected Care Area")
                page_breaks = [
                    area
                    for item in care_areas.get("groups", [])
                    if "Page Break" in item.get("kind", "")
                    for area in item.get("areas", [])
                ]
                if any(_intersects(state["noise_box"], area) for area in page_breaks):
                    errors.append("PILO Noise Box must not include a Page Break")
    return errors


class LightTrainingDialog(QDialog):
    def __init__(
        self,
        state=None,
        test_name="Test 1",
        focus_mode="Median Die",
        care_areas=None,
        die_size_um=(5100.0, 16600.0),
        parent=None,
    ):
        super().__init__(parent)
        self.state = normalized_light_training_state(state)
        self.test_name = str(test_name or "Test 1")
        self.focus_mode = focus_mode
        self.care_areas = deepcopy(care_areas) if care_areas is not None else None
        self.die_size_um = [float(value) for value in die_size_um[:2]]
        eligible = eligible_light_training_groups(self.care_areas)
        if eligible and self.state.get("noise_box_group") not in eligible:
            self.state["noise_box_group"] = eligible[0]
        self.result_state = None
        self.changed = False
        self.workflow_active = False
        self.training_step_finished = False
        self.first_corner = None
        self.stage_position = (
            float(self.state["noise_box"][0]),
            float(self.state["noise_box"][1]),
        )
        self._loading_noise_coordinates = False
        self.setWindowTitle("Light Training")
        self.resize(1320, 780)
        self.setMinimumSize(980, 650)
        self.setStyleSheet(
            "QDialog { background: #cfcbc2; font-family: Arial; font-size: 10px; }"
            "QPushButton { background: #e8e6dd; border: 1px solid #77736b; min-height: 28px; padding: 2px 9px; }"
            "QFrame#summary { background: #efede5; border: 1px solid #8c8982; }"
            "QTableWidget { background: #efefec; border: 1px solid #77736b; gridline-color: #aaa69d; }"
        )
        root = QHBoxLayout(self)
        sidebar = QFrame()
        sidebar.setFixedWidth(180)
        commands = QVBoxLayout(sidebar)
        self.active_region_button = QPushButton("Active Region >")
        self.active_region_button.clicked.connect(self._active_regions)
        self.active_region_button.setToolTip(
            "Active Regions can be reviewed or edited at any time; "
            "enabling them for training requires Focus Mode Active Die."
        )
        self.focus_wizard_button = QPushButton("Focus Wizard")
        self.focus_wizard_button.clicked.connect(self._focus_wizard)
        self.auto_light_button = QPushButton("Auto Light")
        self.auto_light_button.clicked.connect(self._auto_light)
        self.set_light_box_button = QPushButton("Set Light Box")
        self.set_light_box_button.clicked.connect(self._noise_box)
        # Retain the existing public name used by workflow integrations.
        self.light_level_button = self.set_light_box_button
        self.histogram_button = QPushButton("Histogram")
        self.histogram_button.clicked.connect(self._histogram)
        self.sample_plan_button = QPushButton("Light Level\nSample Plan")
        self.sample_plan_button.clicked.connect(self._sample_plan)
        for button in (
            self.active_region_button,
            self.focus_wizard_button,
            self.auto_light_button,
            self.set_light_box_button,
        ):
            button.setFixedSize(154, 52)
            commands.addWidget(button)
        commands.addSpacing(14)
        commands.addWidget(QLabel("Move Stage"))
        stage = QGridLayout()
        for label, row, column, dx, dy in (
            ("Up", 0, 1, 0.0, -0.01),
            ("Left", 1, 0, -0.01, 0.0),
            ("Right", 1, 2, 0.01, 0.0),
            ("Down", 2, 1, 0.0, 0.01),
        ):
            button = QPushButton(label)
            button.setFixedSize(48, 30)
            button.clicked.connect(
                lambda checked=False, move_x=dx, move_y=dy: self._nudge_stage(move_x, move_y)
            )
            stage.addWidget(button, row, column)
        commands.addLayout(stage)
        commands.addStretch(1)
        self.end_button = QPushButton("End")
        self.end_button.clicked.connect(self._end)
        commands.addWidget(self.end_button)
        root.addWidget(sidebar)

        content = QVBoxLayout()
        header = QHBoxLayout()
        title = QLabel("Light Level Training")
        title.setStyleSheet("font-size: 14px; font-weight: 700;")
        self.current_test_label = QLabel(f"Current Test: {self.test_name}")
        self.current_test_label.setStyleSheet("font-size: 12px; font-weight: 700;")
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.current_test_label)
        content.addLayout(header)

        training_body = QHBoxLayout()
        self.preview = LightPreview(
            self.state,
            self.care_areas,
            self._stage_moved,
            self._box_drawn,
        )
        self.preview.stage_position = self.stage_position
        training_body.addWidget(self.preview, 1)

        details_panel = QFrame()
        details_panel.setFixedWidth(365)
        details = QVBoxLayout(details_panel)
        details.addWidget(QLabel("Light Level Values"))
        self.channel_table = QTableWidget(3, 3)
        self.channel_table.setHorizontalHeaderLabels(
            [item["name"] for item in self.state["channels"]]
        )
        self.channel_table.setVerticalHeaderLabels(
            ["Light Level", "Camera Gain", "PILO Noise"]
        )
        self.channel_table.setFixedHeight(145)
        details.addWidget(self.channel_table)

        analysis_buttons = QHBoxLayout()
        analysis_buttons.addWidget(self.histogram_button)
        analysis_buttons.addWidget(self.sample_plan_button)
        details.addLayout(analysis_buttons)

        noise_frame = QFrame()
        noise_frame.setFrameShape(QFrame.StyledPanel)
        noise_layout = QGridLayout(noise_frame)
        noise_layout.addWidget(QLabel("Noise Box"), 0, 0, 1, 4)
        self.noise_controls = []
        for column, label in enumerate(("X1 (um)", "Y1 (um)", "X2 (um)", "Y2 (um)")):
            control = QDoubleSpinBox()
            dimension = self.die_size_um[column % 2]
            control.setRange(0.0, dimension)
            control.setDecimals(1)
            control.setSingleStep(10.0)
            control.valueChanged.connect(self._noise_coordinates_changed)
            self.noise_controls.append(control)
            noise_layout.addWidget(QLabel(label), 1, column)
            noise_layout.addWidget(control, 2, column)
        self.noise_size_label = QLabel()
        noise_layout.addWidget(self.noise_size_label, 3, 0, 1, 4)
        self.noise_group = QComboBox()
        self.noise_group.addItems(eligible)
        self.noise_group.setCurrentText(self.state.get("noise_box_group", ""))
        self.noise_group.currentTextChanged.connect(self._noise_group_changed)
        noise_layout.addWidget(QLabel("Care Area:"), 4, 0)
        noise_layout.addWidget(self.noise_group, 4, 1, 1, 3)
        self.capture_noise_box = QCheckBox("Enable Noise Box Image Capture for Current Recipe")
        self.capture_noise_box.setChecked(self.state["capture_noise_box_image"])
        self.capture_noise_box.toggled.connect(self._capture_noise_box_changed)
        noise_layout.addWidget(self.capture_noise_box, 5, 0, 1, 4)
        details.addWidget(noise_frame)

        self.instructions = QLabel()
        self.instructions.setWordWrap(True)
        self.instructions.setFrameShape(QFrame.StyledPanel)
        self.instructions.setMinimumHeight(125)
        details.addWidget(self.instructions, 1)
        training_body.addWidget(details_panel)
        content.addLayout(training_body, 1)

        self.summary = QLabel()
        self.summary.setObjectName("summary")
        self.summary.setMinimumHeight(54)
        self.summary.setWordWrap(True)
        content.addWidget(self.summary)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        content.addWidget(self.progress)

        buttons = QHBoxLayout()
        self.back_mark_button = QPushButton("<< Back")
        self.back_mark_button.clicked.connect(self._back_mark)
        self.mark_button = QPushButton("Mark >")
        self.mark_button.clicked.connect(self._mark_corner)
        self.next_mark_button = QPushButton("Next >>")
        self.next_mark_button.clicked.connect(self._mark_corner)
        self.advanced_button = QPushButton("Advanced...")
        self.advanced_button.clicked.connect(self._advanced)
        self.train_button = QPushButton("Train Light")
        self.train_button.clicked.connect(self._train)
        self.finish_button = QPushButton("Finish")
        self.finish_button.clicked.connect(self._complete_training_step)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        legend = QPushButton("Legend")
        legend.clicked.connect(self._show_legend)
        for button in (
            self.back_mark_button,
            self.mark_button,
            self.next_mark_button,
            self.advanced_button,
            self.train_button,
        ):
            buttons.addWidget(button)
        buttons.addStretch(1)
        buttons.addWidget(self.finish_button)
        buttons.addWidget(cancel)
        buttons.addWidget(legend)
        content.addLayout(buttons)
        root.addLayout(content, 1)
        self._sync_noise_controls()
        self._refresh()

    def _active_regions(self):
        dialog = ActiveRegionsDialog(
            self.state["active_regions"],
            self.state["active_regions_enabled"],
            self,
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.state["active_regions"] = dialog.result_regions
            self.state["active_regions_enabled"] = dialog.enable.isChecked()
            self.state["trained"] = False
            self.training_step_finished = False
            self.changed = True
            self._refresh()

    def _focus_wizard(self):
        dialog = FocusWizardDialog(
            self.state.get("focus_offset_um", 0.0),
            self.state.get("channels", []),
            self,
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.state["focus_offset_um"] = dialog.result_offset
            self.state["focus_trained"] = True
            self.state["trained"] = False
            self.training_step_finished = False
            self.changed = True
            self.instructions.setText(
                f"Focus Wizard applied {dialog.result_offset:+.3f} um. "
                "Run Auto Light or Train Light to refresh the channel levels."
            )
            self._refresh()

    def _auto_light(self):
        if self.state.get("algorithm", "").startswith("Puma") and self.care_areas is not None:
            eligible = eligible_light_training_groups(self.care_areas)
            if not eligible:
                QMessageBox.warning(
                    self,
                    "Auto Light",
                    "Define an enabled Care Area before running Auto Light.",
                )
                return
            group = next(
                item
                for item in self.care_areas.get("groups", [])
                if item.get("name") == eligible[0]
            )
            x, y, width, height = max(
                group["areas"], key=lambda area: float(area[2]) * float(area[3])
            )[:4]
            box_width = min(float(width) * 0.45, 1800.0 / self.die_size_um[0])
            box_height = min(float(height) * 0.45, 1800.0 / self.die_size_um[1])
            self.state["noise_box_group"] = group["name"]
            self.state["noise_box"] = [
                float(x) + (float(width) - box_width) / 2.0,
                float(y) + (float(height) - box_height) / 2.0,
                box_width,
                box_height,
            ]
            self._sync_noise_controls()
        self._train()
        if self.state.get("trained"):
            self.instructions.setText(
                "Auto Light selected a valid Light Box and optimized all enabled channels."
            )
            self._refresh()

    def _noise_box(self):
        groups = eligible_light_training_groups(self.care_areas)
        if self.care_areas is not None and not groups:
            QMessageBox.warning(
                self,
                "Light Level Training",
                "Define an enabled Care Area before marking the PILO Noise Box.",
            )
            return
        self.workflow_active = True
        self.training_step_finished = False
        self.first_corner = None
        self.preview.first_corner = None
        self.instructions.setText(
            "1. Move the crosshair to the upper-left corner of the Noise Box.\n"
            "2. Click Mark. Move to the lower-right corner and click Mark again.\n"
            "You can also drag directly on the die image."
        )
        self._refresh_workflow_controls()

    def _stage_moved(self, position):
        self.stage_position = position
        if self.workflow_active:
            corner = "upper-left" if self.first_corner is None else "lower-right"
            self.instructions.setText(
                f"Crosshair: X {position[0] * self.die_size_um[0]:.1f} um, "
                f"Y {position[1] * self.die_size_um[1]:.1f} um\n"
                f"Click Mark to store the {corner} corner."
            )

    def _nudge_stage(self, dx, dy):
        self.stage_position = (
            max(0.0, min(1.0, self.stage_position[0] + dx)),
            max(0.0, min(1.0, self.stage_position[1] + dy)),
        )
        self.preview.stage_position = self.stage_position
        self.preview.update()
        self._stage_moved(self.stage_position)

    def _mark_corner(self):
        if not self.workflow_active:
            self._noise_box()
            return
        if self.first_corner is None:
            self.first_corner = self.stage_position
            self.preview.first_corner = self.first_corner
            self.preview.update()
            self.instructions.setText(
                "Upper-left corner marked. Move the crosshair to the lower-right corner, then click Mark."
            )
            self._refresh_workflow_controls()
            return
        x1, y1 = self.first_corner
        x2, y2 = self.stage_position
        if x2 <= x1 or y2 <= y1:
            QMessageBox.warning(
                self,
                "Light Level Training",
                "The second corner must be below and to the right of the first corner.",
            )
            return
        self._set_noise_box([x1, y1, x2 - x1, y2 - y1])
        self.first_corner = None
        self.preview.first_corner = None
        self.instructions.setText(
            "Noise Box marked. Review the coordinates and click Train Light, or mark it again."
        )
        self._refresh_workflow_controls()

    def _back_mark(self):
        if self.first_corner is not None:
            self.first_corner = None
            self.preview.first_corner = None
            self.instructions.setText("First corner cleared. Mark the upper-left corner again.")
        else:
            self.workflow_active = False
            self.instructions.setText("Select Light Level Training to mark the Noise Box.")
        self.preview.update()
        self._refresh_workflow_controls()

    def _box_drawn(self, region):
        self.workflow_active = True
        self.first_corner = None
        self.preview.first_corner = None
        self._set_noise_box(region)
        self.instructions.setText(
            "Noise Box drawn. Review the coordinates and click Train Light, or draw it again."
        )
        self._refresh_workflow_controls()

    def _set_noise_box(self, region):
        self.state["noise_box"] = [float(value) for value in region]
        self.state["trained"] = False
        self.training_step_finished = False
        self.changed = True
        self._sync_noise_controls()
        self._refresh()

    def _sync_noise_controls(self):
        self._loading_noise_coordinates = True
        x, y, width, height = self.state["noise_box"]
        values = (
            x * self.die_size_um[0],
            y * self.die_size_um[1],
            (x + width) * self.die_size_um[0],
            (y + height) * self.die_size_um[1],
        )
        for control, value in zip(self.noise_controls, values):
            control.setValue(value)
        self.noise_size_label.setText(
            f"Width x Height: {width * self.die_size_um[0]:.1f} x "
            f"{height * self.die_size_um[1]:.1f} um"
        )
        self._loading_noise_coordinates = False

    def _noise_coordinates_changed(self, *_args):
        if self._loading_noise_coordinates:
            return
        x1, y1, x2, y2 = [control.value() for control in self.noise_controls]
        if x2 <= x1 or y2 <= y1:
            self.noise_size_label.setText("Width x Height: enter an end point greater than the start point")
            return
        self.state["noise_box"] = [
            x1 / self.die_size_um[0],
            y1 / self.die_size_um[1],
            (x2 - x1) / self.die_size_um[0],
            (y2 - y1) / self.die_size_um[1],
        ]
        self.state["trained"] = False
        self.training_step_finished = False
        self.changed = True
        self.noise_size_label.setText(f"Width x Height: {x2 - x1:.1f} x {y2 - y1:.1f} um")
        self.preview.update()
        self._refresh_workflow_controls()

    def _noise_group_changed(self, value):
        self.state["noise_box_group"] = value
        self.state["trained"] = False
        self.training_step_finished = False
        self.changed = True
        self._refresh_workflow_controls()

    def _capture_noise_box_changed(self, checked):
        self.state["capture_noise_box_image"] = bool(checked)
        self.changed = True

    def _histogram(self):
        if not self.state["trained"]:
            QMessageBox.warning(self, "Light Level Histogram", "Train the light level before opening the histogram.")
            return
        dialog = LightHistogramDialog(
            self.state["channels"],
            dynamic_range=self.state["dynamic_range"],
            algorithm=self.state["algorithm"],
            endpoint_mode=self.state["endpoint_mode"],
            high_endpoint=self.state["high_endpoint"],
            test_name=self.test_name,
            sample_dies=self.state["sample_dies"],
            parent=self,
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.state["channels"] = dialog.result_channels
            self.state["sample_dies"] = dialog.result_sample_dies
            self.changed = True
            self._refresh()

    def _sample_plan(self):
        dialog = LightSamplePlanDialog(
            self.state["sample_dies"],
            test_name=self.test_name,
            parent=self,
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.state["sample_dies"] = dialog.result_dies
            self.state["trained"] = False
            self.training_step_finished = False
            self.changed = True
            self._refresh()

    def _advanced(self):
        dialog = AdvancedLightOptionsDialog(self.state, self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.state.update(dialog.result_options)
            self.state["trained"] = False
            self.training_step_finished = False
            self.changed = True
            self._refresh()

    def _train(self):
        errors = validate_light_training_state(
            self.state,
            self.focus_mode,
            self.care_areas,
            self.die_size_um,
        )
        if errors:
            QMessageBox.warning(self, "Light Training", "\n".join(errors))
            return
        self.progress.setValue(0)
        multiplier = 1.12 if self.state["algorithm"].startswith("Puma") else 1.04
        for index, channel in enumerate(self.state["channels"]):
            channel["light_level"] = round((7.8 - index * 1.85) * multiplier, 2)
            channel["exposure"] = round(0.92 + index * 0.11, 2)
            channel["edr"] = round(15.5 + index * 0.8, 2)
            self.progress.setValue((index + 1) * 33)
        self.progress.setValue(100)
        self.state["trained"] = True
        self.training_step_finished = False
        self.changed = True
        self._refresh()

    def _refresh(self):
        status = "Valid" if self.state["trained"] else "Training required"
        values = ", ".join(f"CH{i + 1} {item['light_level']:.2f}" for i, item in enumerate(self.state["channels"]))
        self.summary.setText(
            f"Algorithm: {self.state['algorithm']} | Dynamic Range: {self.state['dynamic_range']}\n"
            f"Training die: {len(self.state['sample_dies'])} | Focus: "
            f"{self.state['focus_offset_um']:+.3f} um | Light Levels: {values} | Status: {status}"
        )
        for column, channel in enumerate(self.state["channels"]):
            for row, value in enumerate(
                (channel["light_level"], 1.0, max(0.0, 10.0 - channel["light_level"]))
            ):
                item = QTableWidgetItem(f"{float(value):.2f}")
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.channel_table.setItem(row, column, item)
        self.preview.state = self.state
        self.preview.care_areas = self.care_areas
        self.preview.update()
        self._refresh_workflow_controls()

    def _refresh_workflow_controls(self):
        trained = bool(self.state.get("trained"))
        self.histogram_button.setEnabled(trained)
        self.finish_button.setEnabled(trained)
        self.end_button.setEnabled(trained and self.training_step_finished)
        self.back_mark_button.setEnabled(self.workflow_active)
        self.mark_button.setEnabled(self.workflow_active)
        self.next_mark_button.setEnabled(self.workflow_active)

    def _show_legend(self):
        QMessageBox.information(
            self,
            "Light Training Legend",
            "Gray: Care Area\nYellow: Noise Box\nGreen: Active Region\nRed crosshair: stage position",
        )

    def _complete_training_step(self):
        if not self.state.get("trained"):
            QMessageBox.warning(
                self,
                "Light Training",
                "Click Train Light and complete training before Finish.",
            )
            return
        self.training_step_finished = True
        self.workflow_active = False
        self.first_corner = None
        self.preview.first_corner = None
        self.instructions.setText(
            "Light Level Training is finished. Review Histogram or Sample Plan if needed, "
            "then click End to retain the results. Cancel keeps the previous settings."
        )
        self.preview.update()
        self._refresh_workflow_controls()

    def _end(self):
        if not self.state.get("trained") or not self.training_step_finished:
            QMessageBox.warning(
                self,
                "Light Training",
                "Complete Light Level Training and click Finish before End.",
            )
            return
        self.result_state = deepcopy(self.state)
        self.accept()


class FocusWizardDialog(QDialog):
    def __init__(self, current_offset=0.0, channels=None, parent=None):
        super().__init__(parent)
        self.current_offset = float(current_offset)
        self.channels = deepcopy(channels or [])
        self.result_offset = self.current_offset
        self.setWindowTitle("Focus Wizard")
        self.resize(620, 430)

        layout = QVBoxLayout(self)
        title = QLabel("Automatic Focus Sweep")
        title.setStyleSheet("font-size: 14px; font-weight: 700;")
        layout.addWidget(title)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Current Focus Offset:"))
        self.current = QDoubleSpinBox()
        self.current.setRange(-50.0, 50.0)
        self.current.setDecimals(3)
        self.current.setSingleStep(0.01)
        self.current.setSuffix(" um")
        self.current.setValue(self.current_offset)
        controls.addWidget(self.current)
        controls.addWidget(QLabel("Sweep Step:"))
        self.step = QDoubleSpinBox()
        self.step.setRange(0.01, 5.0)
        self.step.setDecimals(3)
        self.step.setSingleStep(0.01)
        self.step.setSuffix(" um")
        self.step.setValue(0.05)
        controls.addWidget(self.step)
        controls.addStretch(1)
        layout.addLayout(controls)

        self.results = QTableWidget(9, 4)
        self.results.setHorizontalHeaderLabels(
            ["Focus Offset (um)", "Contrast", "Sharpness", "Result"]
        )
        for column, width in enumerate((145, 115, 115, 100)):
            self.results.setColumnWidth(column, width)
        layout.addWidget(self.results, 1)

        self.summary = QLabel(
            "Run the sweep to measure nine focus positions around the current offset."
        )
        self.summary.setWordWrap(True)
        self.summary.setFrameShape(QFrame.StyledPanel)
        self.summary.setMinimumHeight(48)
        layout.addWidget(self.summary)

        buttons = QHBoxLayout()
        self.run_button = QPushButton("Run Focus Sweep")
        self.run_button.clicked.connect(self._run)
        self.apply_button = QPushButton("Apply Best Focus")
        self.apply_button.clicked.connect(self._accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(self.run_button)
        buttons.addStretch(1)
        buttons.addWidget(self.apply_button)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)
        self._run()

    def _run(self):
        center = self.current.value()
        step = self.step.value()
        average_light = (
            sum(float(channel.get("light_level", 0.0)) for channel in self.channels)
            / max(1, len(self.channels))
        )
        target = center + max(-0.15, min(0.15, (average_light - 5.5) * 0.08))
        samples = []
        width = max(0.04, step * 1.8)
        for row in range(9):
            offset = center + (row - 4) * step
            sharpness = 100.0 * exp(-((offset - target) / width) ** 2)
            contrast = 42.0 + sharpness * 0.54
            samples.append((sharpness, offset))
            for column, value in enumerate(
                (f"{offset:+.3f}", f"{contrast:.2f}", f"{sharpness:.2f}", "")
            ):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.results.setItem(row, column, item)
        _, self.result_offset = max(samples)
        best_row = min(
            range(9),
            key=lambda row: abs(
                float(self.results.item(row, 0).text()) - self.result_offset
            ),
        )
        self.results.setItem(best_row, 3, QTableWidgetItem("Best"))
        self.results.selectRow(best_row)
        self.summary.setText(
            f"Sweep complete. Best focus: {self.result_offset:+.3f} um at "
            f"sharpness {samples[best_row][0]:.2f}."
        )

    def _accept(self):
        if self.results.item(0, 0) is None:
            self._run()
        self.accept()


class LightPreview(QWidget):
    def __init__(self, state, care_areas=None, on_stage_moved=None, on_box_drawn=None, parent=None):
        super().__init__(parent)
        self.state = state
        self.care_areas = care_areas
        self.on_stage_moved = on_stage_moved or (lambda position: None)
        self.on_box_drawn = on_box_drawn or (lambda region: None)
        self.stage_position = (0.28, 0.30)
        self.first_corner = None
        self.drag_start = None
        self.setMinimumSize(480, 360)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def _point(self, event):
        return event.position() if hasattr(event, "position") else event.pos()

    def _normalized(self, point):
        return (
            max(0.0, min(1.0, float(point.x()) / max(1, self.width()))),
            max(0.0, min(1.0, float(point.y()) / max(1, self.height()))),
        )

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        self.drag_start = self._normalized(self._point(event))
        self.stage_position = self.drag_start
        self.on_stage_moved(self.stage_position)
        self.update()

    def mouseMoveEvent(self, event):
        if self.drag_start is None:
            return
        self.stage_position = self._normalized(self._point(event))
        self.on_stage_moved(self.stage_position)
        self.update()

    def mouseReleaseEvent(self, event):
        if self.drag_start is None:
            return
        end = self._normalized(self._point(event))
        start = self.drag_start
        self.drag_start = None
        self.stage_position = end
        if abs(end[0] - start[0]) >= 0.01 and abs(end[1] - start[1]) >= 0.01:
            self.on_box_drawn(
                [
                    min(start[0], end[0]),
                    min(start[1], end[1]),
                    abs(end[0] - start[0]),
                    abs(end[1] - start[1]),
                ]
            )
        else:
            self.on_stage_moved(self.stage_position)
        self.update()

    def _draw_box(self, painter, area, pen, brush):
        x, y, width, height = area
        painter.setPen(pen)
        painter.setBrush(brush)
        painter.drawRect(
            int(x * self.width()),
            int(y * self.height()),
            max(1, int(width * self.width())),
            max(1, int(height * self.height())),
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        paint_simulated_die(painter, self.rect(), channel=2, brightfield=True)
        painter.setPen(QPen(QColor("#777777"), 1))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        for group in (self.care_areas or {}).get("groups", []):
            page_break = "Page Break" in group.get("kind", "")
            for area in group.get("areas", []):
                self._draw_box(
                    painter,
                    area,
                    QPen(QColor("#c049c9" if page_break else "#9a9a9a"), 2),
                    QColor(192, 73, 201, 60) if page_break else QColor(165, 165, 165, 90),
                )
        self._draw_box(
            painter,
            self.state["noise_box"],
            QPen(QColor("#d8a500"), 2),
            QColor(190, 157, 0, 105),
        )
        for region in self.state.get("active_regions", []):
            self._draw_box(
                painter,
                region,
                QPen(QColor("#22a850"), 2),
                QColor(34, 205, 96, 55),
            )
        if self.drag_start is not None:
            start, end = self.drag_start, self.stage_position
            self._draw_box(
                painter,
                [
                    min(start[0], end[0]),
                    min(start[1], end[1]),
                    abs(end[0] - start[0]),
                    abs(end[1] - start[1]),
                ],
                QPen(QColor("#ffcf20"), 2),
                QColor(255, 207, 32, 45),
            )
        painter.setPen(QPen(QColor("#e53935"), 2))
        cross_x = int(self.stage_position[0] * self.width())
        cross_y = int(self.stage_position[1] * self.height())
        painter.drawLine(cross_x - 10, cross_y, cross_x + 10, cross_y)
        painter.drawLine(cross_x, cross_y - 10, cross_x, cross_y + 10)
        if self.first_corner is not None:
            painter.setPen(QPen(QColor("#d54bce"), 2))
            first_x = int(self.first_corner[0] * self.width())
            first_y = int(self.first_corner[1] * self.height())
            painter.drawLine(first_x - 8, first_y, first_x + 8, first_y)
            painter.drawLine(first_x, first_y - 8, first_x, first_y + 8)


class ActiveRegionCanvas(QWidget):
    def __init__(self, regions, on_drawn, on_selected, parent=None):
        super().__init__(parent)
        self.regions = regions
        self.on_drawn = on_drawn
        self.on_selected = on_selected
        self.selected_index = -1
        self.drag_start = None
        self.drag_current = None
        self.setMinimumSize(460, 420)

    def _die_geometry(self):
        margin = 24.0
        side = max(1.0, min(self.width(), self.height()) - margin * 2.0)
        return (
            (self.width() - side) / 2.0,
            (self.height() - side) / 2.0,
            side,
        )

    def _normalized_point(self, point):
        x0, y0, side = self._die_geometry()
        x = max(0.0, min(1.0, (float(point.x()) - x0) / side))
        y = max(0.0, min(1.0, (float(point.y()) - y0) / side))
        return x, y

    def _point_in_die(self, point):
        x0, y0, side = self._die_geometry()
        return x0 <= point.x() <= x0 + side and y0 <= point.y() <= y0 + side

    def _region_at(self, point):
        x, y = self._normalized_point(point)
        for index in reversed(range(len(self.regions))):
            rx, ry, width, height = self.regions[index]
            if rx <= x <= rx + width and ry <= y <= ry + height:
                return index
        return -1

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        point = event.position() if hasattr(event, "position") else event.pos()
        if not self._point_in_die(point):
            return
        self.drag_start = self._normalized_point(point)
        self.drag_current = self.drag_start
        self.update()

    def mouseMoveEvent(self, event):
        if self.drag_start is None:
            return
        point = event.position() if hasattr(event, "position") else event.pos()
        self.drag_current = self._normalized_point(point)
        self.update()

    def mouseReleaseEvent(self, event):
        if self.drag_start is None:
            return
        point = event.position() if hasattr(event, "position") else event.pos()
        end = self._normalized_point(point)
        start = self.drag_start
        self.drag_start = None
        self.drag_current = None
        x = min(start[0], end[0])
        y = min(start[1], end[1])
        width = abs(end[0] - start[0])
        height = abs(end[1] - start[1])
        if width < 0.01 or height < 0.01:
            index = self._region_at(point)
            if index >= 0:
                self.on_selected(index)
            self.update()
            return
        self.on_drawn([x, y, width, height])
        self.update()

    def _draw_region(self, painter, region, pen, brush):
        x0, y0, side = self._die_geometry()
        x, y, width, height = region
        painter.setPen(pen)
        painter.setBrush(brush)
        painter.drawRect(
            int(x0 + x * side),
            int(y0 + y * side),
            max(1, int(width * side)),
            max(1, int(height * side)),
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#777b7d"))
        x0, y0, side = self._die_geometry()
        die_rect = self.rect()
        die_rect.setRect(int(x0), int(y0), int(side), int(side))
        paint_simulated_die(painter, die_rect, channel=2, brightfield=True)
        painter.setPen(QPen(QColor("#dfe8eb"), 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(int(x0), int(y0), int(side), int(side))
        painter.setPen(QPen(QColor(190, 205, 209, 95), 1))
        for index in range(1, 10):
            offset = int(side * index / 10.0)
            painter.drawLine(int(x0) + offset, int(y0), int(x0) + offset, int(y0 + side))
            painter.drawLine(int(x0), int(y0) + offset, int(x0 + side), int(y0) + offset)
        for index, region in enumerate(self.regions):
            selected = index == self.selected_index
            self._draw_region(
                painter,
                region,
                QPen(QColor("#ffe200" if selected else "#22cd60"), 3 if selected else 2),
                QColor(255, 226, 0, 75) if selected else QColor(34, 205, 96, 55),
            )
        if self.drag_start is not None and self.drag_current is not None:
            start, end = self.drag_start, self.drag_current
            self._draw_region(
                painter,
                [
                    min(start[0], end[0]),
                    min(start[1], end[1]),
                    abs(end[0] - start[0]),
                    abs(end[1] - start[1]),
                ],
                QPen(QColor("#ffcf20"), 2),
                QColor(255, 207, 32, 45),
            )


class ActiveRegionsDialog(QDialog):
    def __init__(self, regions, enabled, parent=None):
        super().__init__(parent)
        self.result_regions = deepcopy(regions or [])
        self.selected_index = 0 if self.result_regions else -1
        self._loading = False
        self.setWindowTitle("Active Region")
        self.resize(1040, 650)
        self.setMinimumSize(880, 560)
        layout = QVBoxLayout(self)
        self.enable = QCheckBox("Enable Active Regions during Inspection Run")
        self.enable.setChecked(bool(enabled))
        layout.addWidget(self.enable)

        body = QHBoxLayout()
        self.canvas = ActiveRegionCanvas(
            self.result_regions,
            self._region_drawn,
            self._select_region,
            self,
        )
        body.addWidget(self.canvas, 1)

        editor = QVBoxLayout()
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Region", "X (%)", "Y (%)", "Width (%)", "Height (%)"]
        )
        self.table.setMinimumWidth(440)
        self.table.setMaximumHeight(270)
        for column, width in enumerate((88, 68, 68, 88, 88)):
            self.table.setColumnWidth(column, width)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.currentCellChanged.connect(self._table_selection_changed)
        editor.addWidget(self.table)

        coordinates = QFrame()
        coordinate_layout = QGridLayout(coordinates)
        title = QLabel("Selected Region Coordinates")
        title.setStyleSheet("font-weight: 700;")
        coordinate_layout.addWidget(title, 0, 0, 1, 2)
        self.coordinate_controls = []
        for row, label in enumerate(("X (%):", "Y (%):", "Width (%):", "Height (%):"), start=1):
            control = QDoubleSpinBox()
            control.setDecimals(2)
            control.setSingleStep(0.5)
            control.setRange(0.1 if row > 2 else 0.0, 100.0 if row > 2 else 99.9)
            control.valueChanged.connect(self._coordinates_changed)
            self.coordinate_controls.append(control)
            coordinate_layout.addWidget(QLabel(label), row, 0)
            coordinate_layout.addWidget(control, row, 1)
        editor.addWidget(coordinates)
        editor.addStretch(1)
        body.addLayout(editor)
        layout.addLayout(body, 1)

        actions = QHBoxLayout()
        new = QPushButton("New")
        new.clicked.connect(self._new)
        delete = QPushButton("Delete")
        delete.clicked.connect(self._delete)
        delete_all = QPushButton("Delete All")
        delete_all.clicked.connect(self._delete_all)
        actions.addWidget(new)
        actions.addWidget(delete)
        actions.addWidget(delete_all)
        actions.addStretch(1)
        finish = QPushButton("Finish")
        finish.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        actions.addWidget(finish)
        actions.addWidget(cancel)
        layout.addLayout(actions)
        self._refresh()

    def _new(self):
        offset = min(0.72, 0.12 + len(self.result_regions) * 0.08)
        self.result_regions.append([offset, offset, 0.22, 0.18])
        self._refresh(len(self.result_regions) - 1)

    def _region_drawn(self, region):
        self.result_regions.append(region)
        self._refresh(len(self.result_regions) - 1)

    def _select_region(self, index):
        if not 0 <= index < len(self.result_regions):
            return
        self.selected_index = index
        self.table.selectRow(index)
        self.canvas.selected_index = index
        self.canvas.update()
        self._sync_coordinates()

    def _table_selection_changed(self, current_row, current_column, previous_row, previous_column):
        if not self._loading and current_row >= 0:
            self._select_region(current_row)

    def _sync_coordinates(self):
        self._loading = True
        has_selection = 0 <= self.selected_index < len(self.result_regions)
        for control in self.coordinate_controls:
            control.setEnabled(has_selection)
        if has_selection:
            for control, value in zip(
                self.coordinate_controls,
                self.result_regions[self.selected_index],
            ):
                control.setValue(float(value) * 100.0)
        self._loading = False

    def _coordinates_changed(self, *_args):
        if self._loading or not 0 <= self.selected_index < len(self.result_regions):
            return
        x, y, width, height = [
            control.value() / 100.0 for control in self.coordinate_controls
        ]
        width = min(width, 1.0 - x)
        height = min(height, 1.0 - y)
        self.result_regions[self.selected_index] = [x, y, width, height]
        self._update_table_row(self.selected_index)
        self._sync_coordinates()
        self.canvas.update()

    def _delete(self):
        row = self.selected_index
        if row >= 0:
            self.result_regions.pop(row)
            self._refresh(min(row, len(self.result_regions) - 1))

    def _delete_all(self):
        self.result_regions = []
        self._refresh(-1)

    def _update_table_row(self, row):
        previous_loading = self._loading
        self._loading = True
        name_item = QTableWidgetItem(f"Active {row + 1}")
        name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, 0, name_item)
        for column, value in enumerate(self.result_regions[row], start=1):
            value_item = QTableWidgetItem(f"{value * 100.0:.2f}")
            value_item.setFlags(value_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, column, value_item)
        self._loading = previous_loading

    def _refresh(self, selected_index=None):
        if selected_index is not None:
            self.selected_index = selected_index
        if self.result_regions:
            self.selected_index = max(0, min(self.selected_index, len(self.result_regions) - 1))
        else:
            self.selected_index = -1
        self._loading = True
        self.table.setRowCount(len(self.result_regions))
        for row in range(len(self.result_regions)):
            self._update_table_row(row)
        if self.selected_index >= 0:
            self.table.selectRow(self.selected_index)
        self._loading = False
        self.canvas.regions = self.result_regions
        self.canvas.selected_index = self.selected_index
        self.canvas.update()
        self._sync_coordinates()

    def _finish(self):
        for x, y, width, height in self.result_regions:
            if width <= 0 or height <= 0 or x < 0 or y < 0 or x + width > 1 or y + height > 1:
                QMessageBox.warning(
                    self,
                    "Active Region",
                    "Every Active Region must have positive size and remain inside the die.",
                )
                return
        if self.enable.isChecked() and not self.result_regions:
            QMessageBox.warning(
                self,
                "Active Region",
                "Create at least one Active Region before enabling this option.",
            )
            return
        self.accept()


class NoiseBoxDialog(QDialog):
    def __init__(
        self,
        noise_box,
        parent=None,
        *,
        group_names=None,
        selected_group="",
        die_size_um=(5100.0, 16600.0),
    ):
        super().__init__(parent)
        self.result_box = list(noise_box or [0.28, 0.30, 0.30, 0.10])
        self.result_group = selected_group
        self.die_size_um = [max(1.0, float(value)) for value in die_size_um[:2]]
        self.setWindowTitle("Light Level Training - Noise Box")
        self.setFixedSize(470, 330)
        layout = QGridLayout(self)
        layout.addWidget(QLabel("Mark the upper-left and lower-right corners of the noise box."), 0, 0, 1, 2)
        self.group = QComboBox()
        self.group.addItems(list(group_names or []))
        self.group.setCurrentText(selected_group)
        self.group.setEnabled(bool(group_names))
        layout.addWidget(QLabel("Care Area:"), 1, 0)
        layout.addWidget(self.group, 1, 1)
        self.controls = []
        dimensions = [
            self.die_size_um[0], self.die_size_um[1],
            self.die_size_um[0], self.die_size_um[1],
        ]
        for row, (label, value, dimension) in enumerate(
            zip(["X (um):", "Y (um):", "Width (um):", "Height (um):"], self.result_box, dimensions),
            start=2,
        ):
            control = QDoubleSpinBox()
            control.setRange(0.0, dimension)
            control.setSingleStep(10.0)
            control.setDecimals(1)
            control.setValue(float(value) * dimension)
            self.controls.append(control)
            layout.addWidget(QLabel(label), row, 0)
            layout.addWidget(control, row, 1)
        warning = QLabel("PILO noise boxes are limited to 2000 x 2000 um and must remain inside the selected Care Area.")
        warning.setWordWrap(True)
        layout.addWidget(warning, 6, 0, 1, 2)
        finish = QPushButton("Finish")
        finish.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        layout.addWidget(finish, 7, 0)
        layout.addWidget(cancel, 7, 1)

    def _finish(self):
        x_um, y_um, width_um, height_um = [control.value() for control in self.controls]
        if width_um > 2000.0 or height_um > 2000.0:
            QMessageBox.warning(self, "Noise Box", "The PILO noise box exceeds the 2000 x 2000 um limit.")
            return
        x = x_um / self.die_size_um[0]
        y = y_um / self.die_size_um[1]
        width = width_um / self.die_size_um[0]
        height = height_um / self.die_size_um[1]
        if x + width > 1.0 or y + height > 1.0:
            QMessageBox.warning(self, "Noise Box", "The noise box must stay inside the die.")
            return
        self.result_box = [x, y, width, height]
        self.result_group = self.group.currentText()
        self.accept()


class AdvancedLightOptionsDialog(QDialog):
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.result_options = None
        self.setWindowTitle("Advanced Light Options")
        self.setFixedSize(560, 390)
        layout = QGridLayout(self)
        self.algorithm = QComboBox()
        self.algorithm.addItems([
            "Puma Illumination Level Optimization",
            "Legacy Light Training",
        ])
        self.algorithm.setCurrentText(state["algorithm"])
        self.dynamic_range = QComboBox()
        self.dynamic_range.addItems(["Extended", "Exposure Control"])
        self.dynamic_range.setCurrentText(state["dynamic_range"])
        self.endpoint_mode = QComboBox()
        self.endpoint_mode.addItems(["Auto", "Manual"])
        self.endpoint_mode.setCurrentText(state["endpoint_mode"])
        self.high_endpoint = QSpinBox()
        self.high_endpoint.setRange(1, 4095)
        self.high_endpoint.setValue(int(state["high_endpoint"]))
        self.density = QDoubleSpinBox()
        self.density.setRange(0.0001, 1.0)
        self.density.setDecimals(4)
        self.density.setSingleStep(0.0001)
        self.density.setValue(float(state["density"]))
        rows = [
            ("Setup Exposure Scheme:", self.algorithm),
            ("Dynamic Range:", self.dynamic_range),
            ("Endpoint Mode:", self.endpoint_mode),
            ("High Endpoint:", self.high_endpoint),
            ("High Density:", self.density),
        ]
        for row, (label, control) in enumerate(rows):
            layout.addWidget(QLabel(label), row, 0)
            layout.addWidget(control, row, 1)
        self.endpoint_mode.currentTextChanged.connect(
            lambda value: self.high_endpoint.setEnabled(value == "Manual")
        )
        self.high_endpoint.setEnabled(self.endpoint_mode.currentText() == "Manual")
        note = QLabel("Extended dynamic range is recommended for new array and logic recipes.")
        note.setWordWrap(True)
        layout.addWidget(note, 5, 0, 1, 2)
        ok = QPushButton("OK")
        ok.clicked.connect(self._accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        layout.addWidget(ok, 6, 0)
        layout.addWidget(cancel, 6, 1)

    def _accept(self):
        self.result_options = {
            "algorithm": self.algorithm.currentText(),
            "dynamic_range": self.dynamic_range.currentText(),
            "endpoint_mode": self.endpoint_mode.currentText(),
            "high_endpoint": self.high_endpoint.value(),
            "density": self.density.value(),
        }
        self.accept()


class LightHistogramDialog(QDialog):
    def __init__(
        self,
        channels,
        dynamic_range="Extended",
        algorithm="Puma Illumination Level Optimization",
        endpoint_mode="Auto",
        high_endpoint=3480,
        test_name="Test 1",
        sample_dies=None,
        parent=None,
    ):
        super().__init__(parent)
        self.result_channels = deepcopy(channels)
        self.result_sample_dies = deepcopy(sample_dies or [[0, 0]])
        self.setWindowTitle("Light Level Histogram")
        self.resize(1120, 700)
        layout = QVBoxLayout(self)
        body = QHBoxLayout()

        self.tabs = QTabWidget()
        self.plots = []
        for channel in self.result_channels:
            plot = HistogramPlot([channel])
            self.plots.append(plot)
            self.tabs.addTab(plot, channel["name"])
        self.plot = self.plots[0]
        body.addWidget(self.tabs, 1)

        details = QFrame()
        details.setFixedWidth(320)
        details_layout = QVBoxLayout(details)
        current_test = QLabel(f"Current Test: {test_name}")
        current_test.setStyleSheet("font-size: 13px; font-weight: 700;")
        details_layout.addWidget(current_test)
        self.value_table = QTableWidget(3, len(self.result_channels))
        self.value_table.setHorizontalHeaderLabels(
            [item["name"] for item in self.result_channels]
        )
        self.value_table.setVerticalHeaderLabels(
            ["Light Level", "Camera Gain", "PILO Noise"]
        )
        self.value_table.setFixedHeight(145)
        details_layout.addWidget(self.value_table)

        controls = QGridLayout()
        self.levels = []
        self.exposures = []
        for column, channel in enumerate(self.result_channels):
            controls.addWidget(QLabel(channel["name"]), 0, column)
            level = QDoubleSpinBox()
            level.setRange(0.1, 200.0)
            level.setValue(float(channel["light_level"]))
            exposure = QDoubleSpinBox()
            exposure.setRange(0.1, 16.0)
            exposure.setValue(float(channel["exposure"]))
            exposure.setVisible(dynamic_range != "Extended")
            self.levels.append(level)
            self.exposures.append(exposure)
            controls.addWidget(level, 1, column)
            controls.addWidget(exposure, 2, column)
        details_layout.addWidget(QLabel("Light Level / Exposure Control"))
        details_layout.addLayout(controls)
        algorithm_summary = QLabel(
            f"Light Level Algorithm\nAlgorithm Type: {algorithm}\n"
            f"Endpoint Mode: {endpoint_mode}\nEndpoints: High {high_endpoint}"
        )
        algorithm_summary.setFrameShape(QFrame.StyledPanel)
        algorithm_summary.setWordWrap(True)
        details_layout.addWidget(algorithm_summary)
        instructions = QLabel(
            "1. Change Light Level or Exposure Control values.\n"
            "2. Click Analyze to redraw every channel histogram.\n"
            "3. Finish saves the analyzed values; Cancel restores the originals."
        )
        instructions.setFrameShape(QFrame.StyledPanel)
        instructions.setWordWrap(True)
        details_layout.addWidget(instructions, 1)
        body.addWidget(details)
        layout.addLayout(body, 1)

        buttons = QHBoxLayout()
        self.analyze_button = QPushButton("Analyze")
        self.analyze_button.clicked.connect(self._analyze)
        finish = QPushButton("Finish")
        finish.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        sample_plan = QPushButton("Sample Plan")
        sample_plan.clicked.connect(self._sample_plan)
        buttons.addWidget(self.analyze_button)
        buttons.addStretch(1)
        buttons.addWidget(finish)
        buttons.addWidget(cancel)
        buttons.addWidget(sample_plan)
        layout.addLayout(buttons)
        self._refresh_values()

    def _analyze(self):
        for index, channel in enumerate(self.result_channels):
            channel["light_level"] = self.levels[index].value()
            channel["exposure"] = self.exposures[index].value()
        for index, plot in enumerate(self.plots):
            plot.channels = [self.result_channels[index]]
            plot.update()
        self._refresh_values()

    def _refresh_values(self):
        for column, channel in enumerate(self.result_channels):
            for row, value in enumerate(
                (channel["light_level"], 1.0, max(0.0, 10.0 - channel["light_level"]))
            ):
                item = QTableWidgetItem(f"{float(value):.2f}")
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.value_table.setItem(row, column, item)

    def _sample_plan(self):
        dialog = LightSamplePlanDialog(self.result_sample_dies, parent=self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.result_sample_dies = dialog.result_dies

    def _finish(self):
        self._analyze()
        self.accept()


class HistogramPlot(QWidget):
    def __init__(self, channels, parent=None):
        super().__init__(parent)
        self.channels = channels
        self.setMinimumHeight(330)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#f5f5f2"))
        painter.setPen(QPen(QColor("#555555"), 1))
        margin = 40
        painter.drawLine(margin, self.height() - margin, self.width() - 20, self.height() - margin)
        painter.drawLine(margin, 20, margin, self.height() - margin)
        colors = ["#215fd5", "#d33131", "#159447"]
        width = max(1, self.width() - margin - 24)
        height = max(1, self.height() - 70)
        for channel_index, channel in enumerate(self.channels):
            scale = min(1.4, float(channel["light_level"]) / 8.0)
            painter.setPen(QPen(QColor(colors[channel_index]), 2))
            previous = None
            for x in range(width):
                normalized = x / max(1, width - 1)
                peak = 0.28 + channel_index * 0.20
                value = exp(-((normalized - peak) ** 2) / 0.012) * scale
                point = (margin + x, self.height() - margin - int(value * height * 0.72))
                if previous:
                    painter.drawLine(previous[0], previous[1], point[0], point[1])
                previous = point


class LightSamplePlanDialog(QDialog):
    def __init__(self, sample_dies, parent=None, test_name="Test 1"):
        super().__init__(parent)
        self.result_dies = deepcopy(sample_dies or [[0, 0]])
        self.setWindowTitle("Light Level Sample Plan")
        self.resize(1120, 740)
        outer = QVBoxLayout(self)
        root = QHBoxLayout()
        self.canvas = LightDieCanvas(self.result_dies)
        root.addWidget(self.canvas, 1)

        controls_frame = QFrame()
        controls_frame.setFixedWidth(330)
        controls = QVBoxLayout(controls_frame)
        current_test = QLabel(f"Current Test: {test_name}")
        current_test.setStyleSheet("font-size: 13px; font-weight: 700;")
        controls.addWidget(current_test)
        controls.addWidget(QLabel("Selection Mode"))
        for mode in ["Toggle", "Add", "Remove", "Set Reference Die"]:
            button = QRadioButton(mode)
            button.setChecked(mode == "Toggle")
            button.toggled.connect(
                lambda checked, value=mode: setattr(self.canvas, "mode", value)
                if checked
                else None
            )
            controls.addWidget(button)
        all_die = QPushButton("Set All Die to Selection Mode")
        all_die.clicked.connect(self.canvas.apply_all)
        controls.addWidget(all_die)
        controls.addSpacing(10)

        self.edge_enabled = QCheckBox("Edge Exclusion")
        self.edge_enabled.toggled.connect(self._edge_controls_changed)
        controls.addWidget(self.edge_enabled)
        self.edge_units = QComboBox()
        self.edge_units.addItems(["In microns", "As % of radius"])
        controls.addWidget(self.edge_units)
        self.edge = QDoubleSpinBox()
        self.edge.setRange(0.0, 150000.0)
        self.edge.setValue(3000.0)
        controls.addWidget(self.edge)
        self.apply_edge_button = QPushButton("Apply")
        self.apply_edge_button.clicked.connect(self._apply_edge_exclusion)
        controls.addWidget(self.apply_edge_button)
        outside = QPushButton("Set Outside Die to Selection Mode")
        outside.clicked.connect(lambda: self.canvas.apply_edge(self._edge_percent(), True))
        inside = QPushButton("Set Inside Die to Selection Mode")
        inside.clicked.connect(lambda: self.canvas.apply_edge(self._edge_percent(), False))
        controls.addWidget(outside)
        controls.addWidget(inside)
        legend = QLabel(
            "Legend\nMagenta: Light Training Die\nCyan: Reference Die\n"
            "Gray: Reticle\nDashed circle: Edge Exclusion Boundary"
        )
        legend.setFrameShape(QFrame.StyledPanel)
        controls.addWidget(legend)
        controls.addStretch(1)
        self.count = QLabel()
        controls.addWidget(self.count)
        root.addWidget(controls_frame)
        outer.addLayout(root, 1)

        self.canvas.on_change = self._refresh_count
        buttons = QHBoxLayout()
        self.undo_button = QPushButton("<< Undo")
        self.undo_button.clicked.connect(self.canvas.undo)
        self.redo_button = QPushButton("Redo >>")
        self.redo_button.clicked.connect(self.canvas.redo)
        finish = QPushButton("Finish")
        finish.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(self.undo_button)
        buttons.addWidget(self.redo_button)
        buttons.addStretch(1)
        buttons.addWidget(finish)
        buttons.addWidget(cancel)
        outer.addLayout(buttons)
        self._edge_controls_changed(False)
        self._refresh_count()

    def _refresh_count(self):
        self.count.setText(
            f"Selected die for Light Training: {len(self.canvas.selected)}"
        )
        self.undo_button.setEnabled(bool(self.canvas.undo_stack))
        self.redo_button.setEnabled(bool(self.canvas.redo_stack))

    def _edge_controls_changed(self, enabled):
        self.edge_units.setEnabled(enabled)
        self.edge.setEnabled(enabled)
        self.apply_edge_button.setEnabled(enabled)

    def _edge_percent(self):
        if self.edge_units.currentText() == "As % of radius":
            return min(50.0, self.edge.value())
        return min(50.0, self.edge.value() / 150000.0 * 100.0)

    def _apply_edge_exclusion(self):
        self.canvas.edge_exclusion_percent = self._edge_percent()
        self.canvas.update()

    def _finish(self):
        if not self.canvas.selected:
            QMessageBox.warning(
                self,
                "Light Level Sample Plan",
                "Select at least one training die.",
            )
            return
        self.result_dies = [list(item) for item in sorted(self.canvas.selected)]
        self.accept()


class LightDieCanvas(QWidget):
    GRID = 21

    def __init__(self, selected, parent=None):
        super().__init__(parent)
        self.selected = {tuple(item) for item in selected}
        self.mode = "Toggle"
        self.reference_die = (0, 0)
        self.edge_exclusion_percent = 0.0
        self.undo_stack = []
        self.redo_stack = []
        self.on_change = lambda: None
        self.setMinimumSize(480, 480)

    def _snapshot(self):
        return (set(self.selected), self.reference_die)

    def _record_change(self):
        self.undo_stack.append(self._snapshot())
        self.redo_stack.clear()

    def _restore(self, snapshot):
        self.selected = set(snapshot[0])
        self.reference_die = snapshot[1]
        self.update()
        self.on_change()

    def _geometry(self):
        side = min(self.width(), self.height()) - 24
        return (self.width() - side) / 2, (self.height() - side) / 2, side, side / self.GRID

    def _valid(self, col, row):
        center = (self.GRID - 1) / 2
        return hypot(col - center, row - center) <= center - 0.3

    def _die(self, col, row):
        center = self.GRID // 2
        return col - center, row - center

    def _apply(self, die):
        if self.mode == "Toggle":
            self.selected.remove(die) if die in self.selected else self.selected.add(die)
        elif self.mode == "Add":
            self.selected.add(die)
        elif self.mode == "Remove":
            self.selected.discard(die)
        else:
            self.reference_die = die
            self.selected.add(die)

    def mousePressEvent(self, event):
        pos = event.position() if hasattr(event, "position") else event.pos()
        x0, y0, side, cell = self._geometry()
        col = int((pos.x() - x0) / cell)
        row = int((pos.y() - y0) / cell)
        if 0 <= col < self.GRID and 0 <= row < self.GRID and self._valid(col, row):
            self._record_change()
            self._apply(self._die(col, row))
            self.update()
            self.on_change()

    def apply_all(self):
        self._record_change()
        for row in range(self.GRID):
            for col in range(self.GRID):
                if self._valid(col, row):
                    self._apply(self._die(col, row))
        self.update()
        self.on_change()

    def apply_edge(self, exclusion_percent, outside):
        self._record_change()
        center = (self.GRID - 1) / 2
        boundary = 1.0 - exclusion_percent / 100.0
        for row in range(self.GRID):
            for col in range(self.GRID):
                if not self._valid(col, row):
                    continue
                is_outside = hypot(col - center, row - center) / center >= boundary
                if is_outside == outside:
                    self._apply(self._die(col, row))
        self.update()
        self.on_change()

    def undo(self):
        if not self.undo_stack:
            return
        self.redo_stack.append(self._snapshot())
        self._restore(self.undo_stack.pop())

    def redo(self):
        if not self.redo_stack:
            return
        self.undo_stack.append(self._snapshot())
        self._restore(self.redo_stack.pop())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#7b7b7b"))
        x0, y0, side, cell = self._geometry()
        painter.setBrush(QColor("#f8f8f6"))
        painter.setPen(QPen(QColor("#4f4f4f"), 1))
        painter.drawEllipse(int(x0), int(y0), int(side), int(side))
        for row in range(self.GRID):
            for col in range(self.GRID):
                if not self._valid(col, row):
                    continue
                die = self._die(col, row)
                if die == self.reference_die:
                    color = QColor("#20d8de")
                elif die in self.selected:
                    color = QColor("#d849e5")
                else:
                    color = QColor("#eeeeee")
                painter.setBrush(color)
                painter.setPen(QPen(QColor("#b0b0b0"), 1))
                painter.drawRect(
                    int(x0 + col * cell),
                    int(y0 + row * cell),
                    max(1, int(cell - 1)),
                    max(1, int(cell - 1)),
                )
        if self.edge_exclusion_percent > 0:
            inset = side * self.edge_exclusion_percent / 100.0
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor("#252525"), 1, Qt.DashLine))
            painter.drawEllipse(
                int(x0 + inset),
                int(y0 + inset),
                max(1, int(side - 2 * inset)),
                max(1, int(side - 2 * inset)),
            )

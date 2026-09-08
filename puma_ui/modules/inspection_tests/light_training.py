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
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    Qt,
    QVBoxLayout,
    QWidget,
)


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
        "high_endpoint": 220,
        "density": 82,
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
        and not group.get("skip_fourier_filter", False)
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
                        "select a Fourier-filtered Care Area for the PILO Noise Box"
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
        focus_mode="Median Die",
        care_areas=None,
        die_size_um=(5100.0, 16600.0),
        parent=None,
    ):
        super().__init__(parent)
        self.state = normalized_light_training_state(state)
        self.focus_mode = focus_mode
        self.care_areas = deepcopy(care_areas) if care_areas is not None else None
        self.die_size_um = [float(value) for value in die_size_um[:2]]
        eligible = eligible_light_training_groups(self.care_areas)
        if eligible and self.state.get("noise_box_group") not in eligible:
            self.state["noise_box_group"] = eligible[0]
        self.result_state = None
        self.changed = False
        self.setWindowTitle("Light Training")
        self.resize(1050, 680)
        self.setMinimumSize(920, 600)
        self.setStyleSheet(
            "QDialog { background: #cfcbc2; font-family: Arial; font-size: 10px; }"
            "QPushButton { background: #e8e6dd; border: 1px solid #77736b; min-height: 28px; padding: 2px 9px; }"
            "QFrame#summary { background: #efede5; border: 1px solid #8c8982; }"
        )
        root = QHBoxLayout(self)
        commands = QVBoxLayout()
        for label, handler in [
            ("Active Region", self._active_regions),
            ("Light Level\nTraining", self._noise_box),
            ("Histogram", self._histogram),
            ("Light Level\nSample Plan", self._sample_plan),
            ("Advanced...", self._advanced),
        ]:
            button = QPushButton(label)
            button.setFixedSize(215, 58)
            button.clicked.connect(handler)
            commands.addWidget(button)
            if label == "Active Region":
                self.active_region_button = button
                button.setEnabled(self.focus_mode == "Active Die")
        commands.addStretch(1)
        train = QPushButton("Train Light")
        train.setFixedSize(215, 42)
        train.clicked.connect(self._train)
        commands.addWidget(train)
        root.addLayout(commands)

        content = QVBoxLayout()
        title = QLabel("Light Level Training")
        title.setStyleSheet("font-size: 14px; font-weight: 700;")
        content.addWidget(title)
        self.preview = LightPreview(self.state)
        content.addWidget(self.preview, 1)
        self.summary = QLabel()
        self.summary.setObjectName("summary")
        self.summary.setMinimumHeight(72)
        self.summary.setWordWrap(True)
        content.addWidget(self.summary)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        content.addWidget(self.progress)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        finish = QPushButton("Finish")
        finish.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(finish)
        buttons.addWidget(cancel)
        content.addLayout(buttons)
        root.addLayout(content, 1)
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
            self.changed = True
            self._refresh()

    def _noise_box(self):
        groups = eligible_light_training_groups(self.care_areas)
        if self.care_areas is not None and not groups:
            QMessageBox.warning(
                self,
                "Light Level Training",
                "Define a Fourier-filtered Care Area before marking the PILO Noise Box.",
            )
            return
        dialog = NoiseBoxDialog(
            self.state["noise_box"],
            self,
            group_names=groups,
            selected_group=self.state.get("noise_box_group", ""),
            die_size_um=self.die_size_um,
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.state["noise_box"] = dialog.result_box
            self.state["noise_box_group"] = dialog.result_group
            self.state["trained"] = False
            self.changed = True
            self._refresh()

    def _histogram(self):
        if not self.state["trained"]:
            QMessageBox.warning(self, "Light Level Histogram", "Train the light level before opening the histogram.")
            return
        dialog = LightHistogramDialog(
            self.state["channels"],
            dynamic_range=self.state["dynamic_range"],
            parent=self,
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.state["channels"] = dialog.result_channels
            self.changed = True
            self._refresh()

    def _sample_plan(self):
        dialog = LightSamplePlanDialog(self.state["sample_dies"], self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.state["sample_dies"] = dialog.result_dies
            self.state["trained"] = False
            self.changed = True
            self._refresh()

    def _advanced(self):
        dialog = AdvancedLightOptionsDialog(self.state, self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.state.update(dialog.result_options)
            self.state["trained"] = False
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
        self.changed = True
        self._refresh()

    def _refresh(self):
        status = "Valid" if self.state["trained"] else "Training required"
        values = ", ".join(f"CH{i + 1} {item['light_level']:.2f}" for i, item in enumerate(self.state["channels"]))
        self.summary.setText(
            f"Algorithm: {self.state['algorithm']} | Dynamic Range: {self.state['dynamic_range']}\n"
            f"Training die: {len(self.state['sample_dies'])} | Light Levels: {values} | Status: {status}"
        )
        self.preview.state = self.state
        self.preview.update()

    def _finish(self):
        if not self.state.get("trained"):
            QMessageBox.warning(
                self,
                "Light Training",
                "Click Train Light and complete training before Finish.",
            )
            return
        self.result_state = deepcopy(self.state)
        self.accept()


class LightPreview(QWidget):
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self.setMinimumSize(480, 360)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#607780"))
        painter.setPen(QPen(QColor("#82969d"), 1))
        for offset in range(0, self.width(), 22):
            painter.drawLine(offset, 0, offset, self.height())
        for offset in range(0, self.height(), 22):
            painter.drawLine(0, offset, self.width(), offset)
        painter.setBrush(QColor(255, 226, 0, 80))
        painter.setPen(QPen(QColor("#ffe200"), 2))
        x, y, width, height = self.state["noise_box"]
        painter.drawRect(
            int(x * self.width()),
            int(y * self.height()),
            int(width * self.width()),
            int(height * self.height()),
        )
        painter.setBrush(QColor(34, 205, 96, 55))
        painter.setPen(QPen(QColor("#22cd60"), 2))
        for region in self.state.get("active_regions", []):
            x, y, width, height = region
            painter.drawRect(
                int(x * self.width()),
                int(y * self.height()),
                int(width * self.width()),
                int(height * self.height()),
            )


class ActiveRegionsDialog(QDialog):
    def __init__(self, regions, enabled, parent=None):
        super().__init__(parent)
        self.result_regions = deepcopy(regions or [])
        self.setWindowTitle("Active Region")
        self.resize(680, 480)
        layout = QVBoxLayout(self)
        self.enable = QCheckBox("Enable Active Regions during Inspection Run")
        self.enable.setChecked(bool(enabled))
        layout.addWidget(self.enable)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Region", "X", "Y", "Width", "Height"])
        layout.addWidget(self.table, 1)
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
        self._refresh()

    def _delete(self):
        row = self.table.currentRow()
        if row >= 0:
            self.result_regions.pop(row)
            self._refresh()

    def _delete_all(self):
        self.result_regions = []
        self._refresh()

    def _refresh(self):
        self.table.setRowCount(len(self.result_regions))
        for row, region in enumerate(self.result_regions):
            self.table.setItem(row, 0, QTableWidgetItem(f"Active {row + 1}"))
            for column, value in enumerate(region, start=1):
                self.table.setItem(row, column, QTableWidgetItem(f"{value:.3f}"))

    def _finish(self):
        for row in range(self.table.rowCount()):
            try:
                self.result_regions[row] = [
                    float(self.table.item(row, column).text()) for column in range(1, 5)
                ]
            except (TypeError, ValueError):
                QMessageBox.warning(self, "Active Region", "Active Region values must be numeric.")
                return
            x, y, width, height = self.result_regions[row]
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
        layout.addWidget(QLabel("Fourier-filtered Care Area:"), 1, 0)
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
        warning = QLabel("PILO noise boxes are limited to 2000 x 2000 um and must remain inside a Fourier-filtered Care Area.")
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
        self.high_endpoint.setRange(1, 255)
        self.high_endpoint.setValue(int(state["high_endpoint"]))
        self.density = QSpinBox()
        self.density.setRange(1, 100)
        self.density.setValue(int(state["density"]))
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
    def __init__(self, channels, dynamic_range="Extended", parent=None):
        super().__init__(parent)
        self.result_channels = deepcopy(channels)
        self.setWindowTitle("Light Level Histogram")
        self.resize(760, 540)
        layout = QVBoxLayout(self)
        self.plot = HistogramPlot(self.result_channels)
        layout.addWidget(self.plot, 1)
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
        layout.addLayout(controls)
        buttons = QHBoxLayout()
        analyze = QPushButton("Analyze")
        analyze.clicked.connect(self._analyze)
        finish = QPushButton("Finish")
        finish.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(analyze)
        buttons.addStretch(1)
        buttons.addWidget(finish)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)

    def _analyze(self):
        for index, channel in enumerate(self.result_channels):
            channel["light_level"] = self.levels[index].value()
            channel["exposure"] = self.exposures[index].value()
        self.plot.channels = self.result_channels
        self.plot.update()

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
    def __init__(self, sample_dies, parent=None):
        super().__init__(parent)
        self.result_dies = deepcopy(sample_dies or [[0, 0]])
        self.setWindowTitle("Light Level Sample Plan")
        self.resize(760, 620)
        root = QHBoxLayout(self)
        self.canvas = LightDieCanvas(self.result_dies)
        root.addWidget(self.canvas, 1)
        controls = QVBoxLayout()
        controls.addWidget(QLabel("Selection Mode"))
        for mode in ["Toggle", "Add", "Remove", "Set Reference Die"]:
            button = QRadioButton(mode)
            button.setChecked(mode == "Toggle")
            button.toggled.connect(
                lambda checked, value=mode: setattr(self.canvas, "mode", value) if checked else None
            )
            controls.addWidget(button)
        all_die = QPushButton("Set All Die to Selection Mode")
        all_die.clicked.connect(self.canvas.apply_all)
        controls.addWidget(all_die)
        controls.addSpacing(10)
        controls.addWidget(QLabel("Edge Exclusion (% radius)"))
        self.edge = QDoubleSpinBox()
        self.edge.setRange(0.0, 50.0)
        self.edge.setValue(12.0)
        controls.addWidget(self.edge)
        outside = QPushButton("Set Outside Die to Selection Mode")
        outside.clicked.connect(lambda: self.canvas.apply_edge(self.edge.value(), True))
        inside = QPushButton("Set Inside Die to Selection Mode")
        inside.clicked.connect(lambda: self.canvas.apply_edge(self.edge.value(), False))
        controls.addWidget(outside)
        controls.addWidget(inside)
        controls.addStretch(1)
        self.count = QLabel()
        controls.addWidget(self.count)
        self.canvas.on_change = self._refresh_count
        finish = QPushButton("Finish")
        finish.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        controls.addWidget(finish)
        controls.addWidget(cancel)
        root.addLayout(controls)
        self._refresh_count()

    def _refresh_count(self):
        self.count.setText(f"Selected die: {len(self.canvas.selected)}")

    def _finish(self):
        if not self.canvas.selected:
            QMessageBox.warning(self, "Light Level Sample Plan", "Select at least one training die.")
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
        self.on_change = lambda: None
        self.setMinimumSize(480, 480)

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
            self._apply(self._die(col, row))
            self.update()
            self.on_change()

    def apply_all(self):
        for row in range(self.GRID):
            for col in range(self.GRID):
                if self._valid(col, row):
                    self._apply(self._die(col, row))
        self.update()
        self.on_change()

    def apply_edge(self, exclusion_percent, outside):
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

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#7b7b7b"))
        x0, y0, side, cell = self._geometry()
        for row in range(self.GRID):
            for col in range(self.GRID):
                if not self._valid(col, row):
                    continue
                die = self._die(col, row)
                if die == self.reference_die:
                    color = QColor("#ef3030")
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

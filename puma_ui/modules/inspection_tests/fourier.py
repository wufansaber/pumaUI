from __future__ import annotations

from copy import deepcopy
from math import exp, sin

from ...qt_compat import (
    QAbstractItemView,
    QCheckBox,
    QColor,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMenuBar,
    QMessageBox,
    QPainter,
    QPen,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTimer,
    QTextEdit,
    Qt,
    QVBoxLayout,
    QWidget,
)
from ...simulation_imaging import paint_simulated_die

MAX_RODS_PER_CHANNEL = 11
MIN_BOX_SIZE = 0.05
MAX_BOX_SIZE = 0.65
MAX_BOX_EDGE = 0.95


def spectral_energy_at(channel, position, box_index=0):
    normalized = max(0.0, min(1.0, float(position)))
    box_shift = max(0, int(box_index)) * 0.07
    dip_a = exp(-((normalized - 0.28 - box_shift) ** 2) / 0.0008)
    dip_b = exp(-((normalized - 0.73 + box_shift / 2) ** 2) / 0.0012)
    ripple = sin(normalized * 78.0 + int(channel)) * 0.015
    green = max(0.02, 0.86 + ripple - dip_a * 0.22 - dip_b * 0.58)
    red = max(0.02, 0.16 + ripple * 0.6 - dip_a * 0.12)
    return green, red


def spectral_energy_samples(channel, box_index=0, sample_count=501):
    count = max(25, int(sample_count))
    return [
        (index / (count - 1), *spectral_energy_at(channel, index / (count - 1), box_index))
        for index in range(count)
    ]


def find_spectral_troughs(samples, max_rods=MAX_RODS_PER_CHANNEL):
    values = [(float(item[0]), float(item[1])) for item in samples if len(item) >= 2]
    if len(values) < 5:
        return []
    smoothed = []
    for index, (position, _energy) in enumerate(values):
        start = max(0, index - 2)
        stop = min(len(values), index + 3)
        smoothed.append((position, sum(value for _x, value in values[start:stop]) / (stop - start)))
    sorted_energy = sorted(value for _position, value in smoothed)
    baseline = sorted_energy[min(len(sorted_energy) - 1, int(len(sorted_energy) * 0.80))]
    maximum_depth = max(baseline - value for _position, value in smoothed)
    if maximum_depth <= 0.04:
        return []
    threshold = max(0.04, maximum_depth * 0.18)
    valleys = []
    index = 0
    while index < len(smoothed):
        if baseline - smoothed[index][1] < threshold:
            index += 1
            continue
        start = index
        while index + 1 < len(smoothed) and baseline - smoothed[index + 1][1] >= threshold:
            index += 1
        segment = smoothed[start:index + 1]
        position, energy = min(segment, key=lambda item: item[1])
        valleys.append((position, baseline - energy))
        index += 1

    merged = []
    for position, depth in sorted(valleys, key=lambda item: item[0]):
        if merged and position - merged[-1][0] < 0.035:
            if depth > merged[-1][1]:
                merged[-1] = (position, depth)
        else:
            merged.append((position, depth))
    strongest = sorted(merged, key=lambda item: item[1], reverse=True)[:max(0, int(max_rods))]
    return [position for position, _depth in sorted(strongest)]


def automatic_rod_positions(channel, boxes=None, numerical_aperture=0.90):
    boxes = list(boxes or [])
    if boxes:
        box_indexes = [
            index for index, box in enumerate(boxes)
            if int(channel) in {int(value) for value in box.get("channels", [])}
        ]
    else:
        box_indexes = [0]
    candidates = []
    for box_index in box_indexes:
        candidates.extend(find_spectral_troughs(spectral_energy_samples(channel, box_index)))
    merged = []
    for position in sorted(candidates):
        if merged and position - merged[-1] < 0.035:
            merged[-1] = (merged[-1] + position) / 2.0
        else:
            merged.append(position)
    scale = 0.90 / max(0.10, float(numerical_aperture))
    mapped = [max(0.0, min(1.0, 0.5 + (position - 0.5) * scale)) for position in merged]
    unique = []
    for position in mapped:
        if not unique or abs(position - unique[-1]) >= 0.015:
            unique.append(position)
    return unique[:MAX_RODS_PER_CHANNEL]


def recalculate_rod_records(rods, boxes=None, numerical_aperture=0.90):
    state = normalize_fourier_state({"rods": rods})
    result = deepcopy(state["rods"])
    for channel in range(1, 4):
        records = [record for record in result if int(record["channel"]) == channel]
        positions = automatic_rod_positions(channel, boxes, numerical_aperture)
        for record in records:
            record["enabled"] = False
            record["score"] = "-"
        used = set()
        for position in positions:
            preferred_decks = (
                (2, 3, 5, 1, 4) if position < 0.46
                else (4, 1, 5, 3, 2) if position > 0.54
                else (5, 3, 1, 2, 4)
            )
            record = next(
                (
                    candidate
                    for deck in preferred_decks
                    for candidate in records
                    if int(candidate.get("deck", 1)) == deck and candidate["rod"] not in used
                ),
                None,
            )
            if record is None:
                break
            record["enabled"] = True
            record["position"] = round(position, 3)
            used.add(record["rod"])
    return result


def _default_rods():
    deck_by_rod = (1, 1, 1, 2, 3, 3, 3, 4, 5, 5, 5)
    return [
        {
            "channel": channel,
            "rod": rod,
            "deck": deck_by_rod[rod - 1],
            "enabled": rod <= 3,
            "position": round(0.08 + (rod - 1) * 0.07, 3),
            "score": "-",
        }
        for channel in range(1, 4)
        for rod in range(1, MAX_RODS_PER_CHANNEL + 1)
    ]


def default_fourier_state():
    return {
        "training_die": [0, 0],
        "boxes": [],
        "options": {
            "user_plan": False,
            "force_training": False,
            "use_test_optics": False,
            "deck": "DECK 0",
            "decks": {"1": "DECK 0", "2": "DECK 0", "3": "DECK 0"},
        },
        "rods": _default_rods(),
        "enforce_specular_block": False,
        "analysis_valid": False,
        "trained": False,
    }


def normalize_fourier_state(state):
    result = default_fourier_state()
    if not isinstance(state, dict):
        return result
    die = state.get("training_die")
    if isinstance(die, (list, tuple)) and len(die) == 2:
        result["training_die"] = [int(die[0]), int(die[1])]
    result["boxes"] = deepcopy(state.get("boxes") or [])
    result["options"].update(deepcopy(state.get("options") or {}))
    legacy_deck = str(result["options"].get("deck") or "DECK 0")
    saved_decks = result["options"].get("decks")
    if not isinstance(saved_decks, dict):
        saved_decks = {}
    result["options"]["decks"] = {
        str(channel): str(saved_decks.get(str(channel), legacy_deck))
        for channel in range(1, 4)
    }
    result["enforce_specular_block"] = bool(state.get("enforce_specular_block", False))
    result["analysis_valid"] = bool(state.get("analysis_valid", False))
    result["trained"] = bool(state.get("trained", False))
    saved = {}
    for record in state.get("rods") or []:
        try:
            channel = int(record.get("channel"))
            rod = int(record.get("rod"))
        except (AttributeError, TypeError, ValueError):
            continue
        if 1 <= channel <= 3 and 1 <= rod <= MAX_RODS_PER_CHANNEL:
            saved[(channel, rod)] = deepcopy(record)
    result["rods"] = []
    for default in _default_rods():
        record = default.copy()
        record.update(saved.get((default["channel"], default["rod"]), {}))
        record["channel"] = default["channel"]
        record["rod"] = default["rod"]
        record["deck"] = int(record.get("deck", default["deck"]))
        result["rods"].append(record)
    return result


def validate_fourier_state(state):
    state = normalize_fourier_state(state)
    errors = []
    if not state["boxes"]:
        errors.append("at least one Fourier Filter training box is required")
    for index, box in enumerate(state["boxes"], start=1):
        try:
            x = float(box["x"])
            y = float(box["y"])
            width = float(box["width"])
            height = float(box["height"])
        except (KeyError, TypeError, ValueError):
            errors.append(f"training box {index} has invalid geometry")
            continue
        if width < MIN_BOX_SIZE or height < MIN_BOX_SIZE:
            errors.append(f"training box {index} is smaller than the minimum size")
        if width > MAX_BOX_SIZE or height > MAX_BOX_SIZE:
            errors.append(f"training box {index} exceeds the maximum size")
        if x < 0 or y < 0 or x + width > MAX_BOX_EDGE or y + height > MAX_BOX_EDGE:
            errors.append(f"training box {index} exceeds the allowed image area")
        channels = sorted({int(value) for value in box.get("channels", []) if str(value).isdigit()})
        if not channels or any(channel not in (1, 2, 3) for channel in channels):
            errors.append(f"training box {index} must use at least one valid channel")
    for record in state["rods"]:
        try:
            position = float(record["position"])
        except (KeyError, TypeError, ValueError):
            errors.append(
                f"channel {record['channel']} rod {record['rod']} has an invalid position"
            )
            continue
        if not 0.0 <= position <= 1.0:
            errors.append(
                f"channel {record['channel']} rod {record['rod']} position is out of range"
            )
    return errors


class FourierFilterTrainingDialog(QDialog):
    BOX_COLORS = ["#ef2f2f", "#00c948", "#2449e8", "#f1db21", "#ee3fd5"]

    def __init__(
        self,
        state=None,
        incidence_angle="Oblique",
        test_name="Test 1",
        parent=None,
    ):
        super().__init__(parent)
        self.state = normalize_fourier_state(state)
        self.incidence_angle = incidence_angle
        self.test_name = str(test_name or "Test 1")
        self.result_state = None
        self.changed = False
        self.workflow_active = False
        self.training_step_finished = False
        self.first_corner = None
        self.stage_position = (0.15, 0.15)
        self.editing_box_index = None
        self.selected_box_index = 0 if self.state["boxes"] else -1
        self._loading_boxes = False
        self.setWindowTitle("Fourier Filter Training")
        self.resize(1260, 760)
        self.setMinimumSize(980, 640)
        self.setStyleSheet(
            "QDialog { background: #d2cec5; font-family: Arial; font-size: 10px; }"
            "QPushButton { min-height: 28px; padding: 2px 10px; }"
            "QFrame#summary { background: #efede2; border: 1px solid #8c8982; }"
        )
        root = QHBoxLayout(self)
        commands_frame = QFrame()
        commands_frame.setFixedWidth(178)
        commands = QVBoxLayout(commands_frame)
        for label, handler in (
            ("Fourier Filter\nSample Plan", self._sample_plan),
            ("Set Fourier\nFilter Box", self._set_box),
        ):
            button = QPushButton(label)
            button.setFixedSize(152, 54)
            button.clicked.connect(handler)
            commands.addWidget(button)
        self.rod_button = QPushButton("Rod Positions")
        self.rod_button.setFixedSize(152, 54)
        self.rod_button.clicked.connect(self._rod_positions)
        commands.addWidget(self.rod_button)
        commands.addSpacing(24)
        retrain = QPushButton("Retrain\nFourier Filter")
        retrain.setFixedSize(152, 54)
        retrain.clicked.connect(self._train)
        commands.addWidget(retrain)
        commands.addStretch(1)
        self.end_button = QPushButton("End")
        self.end_button.clicked.connect(self._end)
        commands.addWidget(self.end_button)
        root.addWidget(commands_frame)

        content = QVBoxLayout()
        body = QHBoxLayout()
        self.preview = FourierPreview(
            self.state,
            on_stage_moved=self._stage_moved,
            on_box_drawn=self._box_drawn,
        )
        self.preview.stage_position = self.stage_position
        body.addWidget(self.preview, 1)

        details_frame = QFrame()
        details_frame.setFixedWidth(390)
        details = QVBoxLayout(details_frame)
        current_test = QLabel(f"Current Test: {self.test_name}")
        current_test.setStyleSheet("font-size: 13px; font-weight: 700;")
        details.addWidget(current_test)
        self.training_status = QLabel()
        self.training_status.setStyleSheet("font-weight: 700; color: #c61e1e;")
        details.addWidget(self.training_status)
        box_commands = QHBoxLayout()
        for label, handler in (
            ("New Box", self._new_box),
            ("Edit Box", self._edit_box),
            ("Delete Box", self._delete_box),
        ):
            button = QPushButton(label)
            button.clicked.connect(handler)
            box_commands.addWidget(button)
        details.addLayout(box_commands)
        self.box_table = QTableWidget(0, 5)
        self.box_table.setHorizontalHeaderLabels(["Box", "Name", "CH1", "CH2", "CH3"])
        self.box_table.verticalHeader().setVisible(False)
        self.box_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.box_table.cellClicked.connect(self._select_box)
        self.box_table.itemChanged.connect(self._box_item_changed)
        self.box_table.setFixedHeight(190)
        details.addWidget(self.box_table)
        self.score_table = QTableWidget(0, 4)
        self.score_table.setHorizontalHeaderLabels(["Box", "CH1", "CH2", "CH3"])
        self.score_table.verticalHeader().setVisible(False)
        self.score_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.score_table.setFixedHeight(155)
        details.addWidget(self.score_table)
        self.instructions = QLabel()
        self.instructions.setFrameShape(QFrame.StyledPanel)
        self.instructions.setWordWrap(True)
        details.addWidget(self.instructions, 1)
        body.addWidget(details_frame)
        content.addLayout(body, 1)

        self.summary = QLabel()
        self.summary.setObjectName("summary")
        self.summary.setMinimumHeight(42)
        content.addWidget(self.summary)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(100 if self.state["trained"] else 0)
        content.addWidget(self.progress)
        footer = QHBoxLayout()
        self.back_button = QPushButton("<< Back")
        self.back_button.clicked.connect(self._back)
        self.mark_button = QPushButton("Mark >")
        self.mark_button.clicked.connect(self._mark_corner)
        self.next_button = QPushButton("Next >>")
        self.next_button.clicked.connect(self._mark_corner)
        self.train_button = QPushButton("Train FF")
        self.train_button.clicked.connect(self._train)
        self.finish_button = QPushButton("Finish")
        self.finish_button.clicked.connect(self._complete_training_step)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        advanced = QPushButton("Advanced...")
        advanced.clicked.connect(self._advanced)
        legend = QPushButton("Legend")
        legend.clicked.connect(self._legend)
        for button in (self.back_button, self.mark_button, self.next_button, self.train_button):
            footer.addWidget(button)
        footer.addStretch(1)
        for button in (self.finish_button, cancel, advanced, legend):
            footer.addWidget(button)
        content.addLayout(footer)
        root.addLayout(content, 1)
        self._refresh()

    def _invalidate_training(self):
        self.state["trained"] = False
        self.state["analysis_valid"] = False
        self.training_step_finished = False
        self.changed = True

    def _sample_plan(self):
        dialog = FourierSamplePlanDialog(self.state["training_die"], self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.state["training_die"] = list(dialog.canvas.selected_die)
            self._invalidate_training()
            self._refresh()

    def _set_box(self):
        self._new_box()

    def _new_box(self):
        self.workflow_active = True
        self.editing_box_index = None
        self.first_corner = None
        self.preview.first_corner = None
        self.instructions.setText(
            "Move the crosshair to the upper-left corner and click Mark. "
            "Then mark the lower-right corner. The shaded and outline boxes show the minimum and maximum size."
        )
        self._refresh_controls()
        self.preview.update()

    def _edit_box(self):
        if not 0 <= self.selected_box_index < len(self.state["boxes"]):
            QMessageBox.warning(self, "Set Fourier Filter Box", "Select a training box to edit.")
            return
        box = self.state["boxes"][self.selected_box_index]
        self.workflow_active = True
        self.editing_box_index = self.selected_box_index
        self.first_corner = None
        self.stage_position = (float(box["x"]), float(box["y"]))
        self.preview.stage_position = self.stage_position
        self.preview.first_corner = None
        self.instructions.setText(
            f"Editing FF BOX {self.selected_box_index + 1}. Mark a new upper-left and lower-right corner."
        )
        self._refresh_controls()
        self.preview.update()

    def _delete_box(self):
        if not 0 <= self.selected_box_index < len(self.state["boxes"]):
            return
        self.state["boxes"].pop(self.selected_box_index)
        self.selected_box_index = min(self.selected_box_index, len(self.state["boxes"]) - 1)
        self._invalidate_training()
        self._refresh()

    def _stage_moved(self, position):
        self.stage_position = position
        if self.workflow_active:
            corner = "upper-left" if self.first_corner is None else "lower-right"
            self.instructions.setText(
                f"Crosshair X {position[0]:.3f}, Y {position[1]:.3f}. Click Mark for the {corner} corner."
            )

    def _mark_corner(self):
        if not self.workflow_active:
            self._new_box()
            return
        if self.first_corner is None:
            self.first_corner = self.stage_position
            self.preview.first_corner = self.first_corner
            self.instructions.setText(
                "Upper-left corner marked. Move to a lower-right point inside the size outlines and click Mark."
            )
            self._refresh_controls()
            self.preview.update()
            return
        x1, y1 = self.first_corner
        x2, y2 = self.stage_position
        self._commit_box([x1, y1, x2 - x1, y2 - y1])

    def _box_drawn(self, region):
        self.workflow_active = True
        self._commit_box(region)

    def _commit_box(self, region):
        x, y, width, height = [float(value) for value in region]
        if (
            width < MIN_BOX_SIZE
            or height < MIN_BOX_SIZE
            or width > MAX_BOX_SIZE
            or height > MAX_BOX_SIZE
            or x < 0
            or y < 0
            or x + width > MAX_BOX_EDGE
            or y + height > MAX_BOX_EDGE
        ):
            QMessageBox.warning(
                self,
                "Set Fourier Filter Box",
                "Invalid point selected. Box width and height must be between "
                f"{MIN_BOX_SIZE:.2f} and {MAX_BOX_SIZE:.2f}, and the box must remain inside 0.95 of the die image.",
            )
            return
        channels = [1, 2, 3]
        if self.editing_box_index is not None:
            channels = list(self.state["boxes"][self.editing_box_index].get("channels", channels))
        record = {
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "channels": channels,
        }
        if self.editing_box_index is None:
            self.state["boxes"].append(record)
            self.selected_box_index = len(self.state["boxes"]) - 1
        else:
            self.state["boxes"][self.editing_box_index] = record
            self.selected_box_index = self.editing_box_index
        self.editing_box_index = None
        self.first_corner = None
        self.preview.first_corner = None
        self.workflow_active = False
        self._invalidate_training()
        self.instructions.setText(
            "Training box stored. Select its channel checkboxes, create another box if needed, then click Train FF."
        )
        self._refresh()

    def _back(self):
        if self.first_corner is not None:
            self.first_corner = None
            self.preview.first_corner = None
            self.instructions.setText("First corner cleared. Mark the upper-left corner again.")
        else:
            self.workflow_active = False
            self.editing_box_index = None
            self.instructions.setText("Box setup closed without changing the current boxes.")
        self._refresh_controls()
        self.preview.update()

    def _select_box(self, row, _column):
        if 0 <= row < len(self.state["boxes"]):
            self.selected_box_index = row
            self.preview.selected_box_index = row
            self.preview.update()

    def _box_item_changed(self, item):
        if self._loading_boxes or item.column() < 2:
            return
        row = item.row()
        if not 0 <= row < len(self.state["boxes"]):
            return
        channels = []
        for column in range(2, 5):
            channel_item = self.box_table.item(row, column)
            if channel_item and channel_item.checkState() == Qt.Checked:
                channels.append(column - 1)
        if not channels:
            self._loading_boxes = True
            item.setCheckState(Qt.Checked)
            self._loading_boxes = False
            QMessageBox.warning(
                self,
                "Fourier Filter Training",
                "Each training box must use at least one collection channel.",
            )
            return
        self.state["boxes"][row]["channels"] = channels
        self._invalidate_training()
        self._refresh_controls()

    def _advanced(self):
        dialog = AdvancedFourierOptionsDialog(self.state["options"], self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.state["options"] = dialog.result_options
            self._invalidate_training()
            self._refresh()

    def _rod_positions(self):
        if not self.state["trained"]:
            QMessageBox.warning(
                self,
                "Rod Positions",
                "Train the Fourier Filter before adjusting Rod Positions.",
            )
            return
        dialog = RodPositionsDialog(
            self.state["rods"],
            boxes=self.state["boxes"],
            incidence_angle=self.incidence_angle,
            enforce_specular_block=self.state["enforce_specular_block"],
            analysis_valid=self.state["analysis_valid"],
            parent=self,
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.state["rods"] = dialog.result_rods
            self.state["enforce_specular_block"] = dialog.result_enforce_specular
            self.state["analysis_valid"] = dialog.analysis_valid
            self.changed = True
            self._refresh()

    def _train(self):
        errors = validate_fourier_state(self.state)
        if errors:
            QMessageBox.warning(self, "Fourier Filter Training", "\n".join(errors))
            return
        progress = FourierTrainingProgressDialog(parent=self)
        result = progress.exec() if hasattr(progress, "exec") else progress.exec_()
        if result != QDialog.Accepted:
            self.instructions.setText("Fourier Filter training was canceled; previous results were retained.")
            return
        self.progress.setValue(100)
        self.state["rods"] = recalculate_rod_records(
            self.state["rods"],
            self.state["boxes"],
            0.90,
        )
        self.state["trained"] = True
        self.state["analysis_valid"] = False
        self.training_step_finished = False
        self.changed = True
        self.instructions.setText(
            "Fourier Filter training completed. Review Rod Positions if needed, then click Finish."
        )
        self._refresh()

    def _complete_training_step(self):
        if not self.state["trained"]:
            QMessageBox.warning(
                self,
                "Fourier Filter Training",
                "Create a valid training box and click Train FF before Finish.",
            )
            return
        self.workflow_active = False
        self.first_corner = None
        self.preview.first_corner = None
        self.training_step_finished = True
        self.instructions.setText("Fourier Filter setup finished. Click End to retain the result.")
        self._refresh_controls()

    def _end(self):
        if not self.state["trained"] or not self.training_step_finished:
            QMessageBox.warning(
                self,
                "Fourier Filter Training",
                "Complete training and click Finish before End.",
            )
            return
        self.result_state = deepcopy(self.state)
        self.accept()

    def _legend(self):
        QMessageBox.information(
            self,
            "Fourier Filter Legend",
            "Red/green/blue/yellow/magenta: training boxes\n"
            "Cyan shaded box: minimum size\nCyan outline: maximum size\n"
            "Blue crosshair: stage position",
        )

    def _refresh(self):
        die = self.state["training_die"]
        status = "Valid" if self.state["trained"] else "Fourier Filter Training Is Required"
        self.training_status.setText(status)
        self.summary.setText(
            f"Training Die: Row {die[1]}, Column {die[0]}    "
            f"Training Boxes: {len(self.state['boxes'])}    Status: {status}"
        )
        self._loading_boxes = True
        self.box_table.setRowCount(len(self.state["boxes"]))
        self.score_table.setRowCount(len(self.state["boxes"]))
        for row, box in enumerate(self.state["boxes"]):
            color = QColor(self.BOX_COLORS[row % len(self.BOX_COLORS)])
            number = QTableWidgetItem(str(row + 1))
            number.setFlags(number.flags() & ~Qt.ItemIsEditable)
            name = QTableWidgetItem(f"FF BOX {row + 1}")
            name.setBackground(color)
            name.setFlags(name.flags() & ~Qt.ItemIsEditable)
            self.box_table.setItem(row, 0, number)
            self.box_table.setItem(row, 1, name)
            channels = set(box.get("channels", []))
            for channel in range(1, 4):
                item = QTableWidgetItem("")
                item.setCheckState(Qt.Checked if channel in channels else Qt.Unchecked)
                self.box_table.setItem(row, channel + 1, item)
            self.score_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            for channel in range(1, 4):
                score = "0.00"
                if self.state["trained"] and channel in channels:
                    score = f"{98.5 - row * 0.8 - channel * 0.35:.2f}"
                self.score_table.setItem(row, channel, QTableWidgetItem(score))
        self._loading_boxes = False
        if 0 <= self.selected_box_index < self.box_table.rowCount():
            self.box_table.selectRow(self.selected_box_index)
        self.preview.state = self.state
        self.preview.selected_box_index = self.selected_box_index
        self.preview.update()
        self._refresh_controls()

    def _refresh_controls(self):
        self.preview.box_drawing_enabled = self.workflow_active
        self.rod_button.setEnabled(bool(self.state["trained"]))
        self.finish_button.setEnabled(bool(self.state["trained"]))
        self.end_button.setEnabled(bool(self.state["trained"] and self.training_step_finished))
        self.back_button.setEnabled(self.workflow_active)
        self.mark_button.setEnabled(self.workflow_active)
        self.next_button.setEnabled(self.workflow_active)


class FourierTrainingProgressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Training Progress")
        self.setFixedSize(430, 150)
        self.paused = False
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Training Fourier Filter for selected boxes and channels..."))
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.progress)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.pause_button = QPushButton("Pause")
        self.pause_button.clicked.connect(self._toggle_pause)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(self.pause_button)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._advance)
        self.timer.start(15)

    def _toggle_pause(self):
        self.paused = not self.paused
        self.pause_button.setText("Resume" if self.paused else "Pause")

    def _advance(self):
        if self.paused:
            return
        value = min(100, self.progress.value() + 20)
        self.progress.setValue(value)
        if value >= 100:
            self.timer.stop()
            self.accept()


class FourierPreview(QWidget):
    def __init__(self, state, on_stage_moved=None, on_box_drawn=None, parent=None):
        super().__init__(parent)
        self.state = state
        self.on_stage_moved = on_stage_moved or (lambda position: None)
        self.on_box_drawn = on_box_drawn or (lambda region: None)
        self.stage_position = (0.15, 0.15)
        self.first_corner = None
        self.drag_start = None
        self.box_drawing_enabled = False
        self.selected_box_index = -1
        self.setMinimumSize(480, 420)

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
        self.on_stage_moved(end)
        x1, x2 = sorted((start[0], end[0]))
        y1, y2 = sorted((start[1], end[1]))
        if self.box_drawing_enabled and x2 - x1 >= 0.01 and y2 - y1 >= 0.01:
            self.on_box_drawn([x1, y1, x2 - x1, y2 - y1])
        self.update()

    def _draw_region(self, painter, region, pen):
        if isinstance(region, dict):
            values = (
                region.get("x", 0.0),
                region.get("y", 0.0),
                region.get("width", 0.0),
                region.get("height", 0.0),
            )
        else:
            values = region[:4]
        x, y, width, height = [float(value) for value in values]
        painter.setBrush(Qt.NoBrush)
        painter.setPen(pen)
        painter.drawRect(
            int(x * self.width()),
            int(y * self.height()),
            max(1, int(width * self.width())),
            max(1, int(height * self.height())),
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#666666"))
        die_left = int(self.width() * 0.23)
        die_width = int(self.width() * 0.54)
        painter.fillRect(die_left, 0, die_width, self.height(), QColor("#f7f7f5"))
        colors = FourierFilterTrainingDialog.BOX_COLORS
        for index, box in enumerate(self.state.get("boxes", [])):
            width = 3 if index == self.selected_box_index else 2
            self._draw_region(painter, box, QPen(QColor(colors[index % len(colors)]), width))
        if self.first_corner is not None:
            x, y = self.first_corner
            minimum = [x, y, MIN_BOX_SIZE, MIN_BOX_SIZE]
            maximum = [x, y, min(MAX_BOX_SIZE, MAX_BOX_EDGE - x), min(MAX_BOX_SIZE, MAX_BOX_EDGE - y)]
            painter.setBrush(QColor(0, 210, 220, 100))
            painter.setPen(QPen(QColor("#00b9c8"), 1, Qt.DashLine))
            painter.drawRect(
                int(x * self.width()),
                int(y * self.height()),
                int(minimum[2] * self.width()),
                int(minimum[3] * self.height()),
            )
            self._draw_region(painter, maximum, QPen(QColor("#00b9c8"), 1, Qt.DashLine))
        sx = int(self.stage_position[0] * self.width())
        sy = int(self.stage_position[1] * self.height())
        painter.setPen(QPen(QColor("#164ae8"), 2))
        painter.drawLine(sx - 10, sy, sx + 10, sy)
        painter.drawLine(sx, sy - 10, sx, sy + 10)


class FourierSamplePlanDialog(QDialog):
    def __init__(self, selected_die, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Fourier Filter Sample Plan")
        self.resize(820, 700)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Click a die to select the Fourier Filter training die."))
        self.canvas = TrainingDieCanvas(selected_die)
        layout.addWidget(self.canvas, 1)
        self.count = QLabel("Total Number of Die Selected for Fourier Filter Training: 1")
        layout.addWidget(self.count, 0, Qt.AlignHCenter)
        buttons = QHBoxLayout()
        self.undo_button = QPushButton("<< Undo")
        self.undo_button.clicked.connect(self.canvas.undo)
        self.redo_button = QPushButton("Redo >>")
        self.redo_button.clicked.connect(self.canvas.redo)
        self.canvas.on_change = self._refresh_controls
        buttons.addWidget(self.undo_button)
        buttons.addWidget(self.redo_button)
        buttons.addStretch(1)
        finish = QPushButton("Finish")
        finish.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(finish)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)
        self._refresh_controls()

    def _refresh_controls(self):
        self.undo_button.setEnabled(bool(self.canvas.undo_stack))
        self.redo_button.setEnabled(bool(self.canvas.redo_stack))


class TrainingDieCanvas(QWidget):
    def __init__(self, selected_die, parent=None):
        super().__init__(parent)
        self.selected_die = tuple(selected_die or (0, 0))
        self.reference_die = (0, 0)
        self.undo_stack = []
        self.redo_stack = []
        self.on_change = lambda: None
        self.setMinimumSize(480, 440)

    def _snapshot(self):
        return self.selected_die

    def undo(self):
        if not self.undo_stack:
            return
        self.redo_stack.append(self.selected_die)
        self.selected_die = self.undo_stack.pop()
        self.update()
        self.on_change()

    def redo(self):
        if not self.redo_stack:
            return
        self.undo_stack.append(self.selected_die)
        self.selected_die = self.redo_stack.pop()
        self.update()
        self.on_change()

    def mousePressEvent(self, event):
        pos = event.position() if hasattr(event, "position") else event.pos()
        side = min(self.width(), self.height()) - 20
        x0 = (self.width() - side) / 2
        y0 = (self.height() - side) / 2
        cell = side / 17.0
        col = int((pos.x() - x0) / cell)
        row = int((pos.y() - y0) / cell)
        if not 0 <= col < 17 or not 0 <= row < 17:
            return
        radius = side / 2
        cx = (col + 0.5) * cell - radius
        cy = (row + 0.5) * cell - radius
        if cx * cx + cy * cy > (radius - cell / 2) ** 2:
            return
        selected = (col - 8, row - 8)
        if selected != self.selected_die:
            self.undo_stack.append(self.selected_die)
            self.redo_stack.clear()
            self.selected_die = selected
            self.update()
            self.on_change()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#7c7c7c"))
        side = min(self.width(), self.height()) - 20
        x0 = (self.width() - side) // 2
        y0 = (self.height() - side) // 2
        cell = side / 17.0
        radius = side / 2
        painter.setBrush(QColor("#f7f7f5"))
        painter.setPen(QPen(QColor("#444444"), 1))
        painter.drawEllipse(x0, y0, int(side), int(side))
        for row in range(17):
            for col in range(17):
                cx = (col + 0.5) * cell - radius
                cy = (row + 0.5) * cell - radius
                if cx * cx + cy * cy > (radius - cell / 2) ** 2:
                    continue
                die = (col - 8, row - 8)
                if die == self.selected_die:
                    color = QColor("#d84ce5")
                elif die == self.reference_die:
                    color = QColor("#20d8de")
                else:
                    color = QColor("#d0d0d0")
                painter.setBrush(color)
                painter.setPen(QPen(QColor("#b0b0b0"), 1))
                painter.drawRect(int(x0 + col * cell), int(y0 + row * cell), int(cell - 1), int(cell - 1))


class FourierBoxDialog(QDialog):
    def __init__(self, boxes, parent=None):
        super().__init__(parent)
        self.boxes = deepcopy(boxes or [])
        self.setWindowTitle("Set Fourier Filter Box")
        self.setFixedSize(520, 430)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Define training boxes and assign one or more collection channels."))
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["X", "Y", "Width", "Height", "Channels"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.cellClicked.connect(self._load_box)
        layout.addWidget(self.table)
        form = QGridLayout()
        self.x = self._fraction_spin(0.20)
        self.y = self._fraction_spin(0.20)
        self.width_spin = self._fraction_spin(0.25)
        self.height_spin = self._fraction_spin(0.25)
        for row, (name, control) in enumerate([("X:", self.x), ("Y:", self.y), ("Width:", self.width_spin), ("Height:", self.height_spin)]):
            form.addWidget(QLabel(name), row, 0)
            form.addWidget(control, row, 1)
        layout.addLayout(form)
        self.channels = [QCheckBox("Channel 1 (Left)"), QCheckBox("Channel 2 (Right)"), QCheckBox("Channel 3 (Center)")]
        for box in self.channels:
            box.setChecked(True)
            layout.addWidget(box)
        layout.addStretch(1)
        buttons = QHBoxLayout()
        new_box = QPushButton("New Box")
        new_box.clicked.connect(self._add_box)
        edit_box = QPushButton("Edit Box")
        edit_box.clicked.connect(self._edit_box)
        delete_box = QPushButton("Delete Box")
        delete_box.clicked.connect(self._delete_box)
        finish = QPushButton("Finish")
        finish.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(new_box)
        buttons.addWidget(edit_box)
        buttons.addWidget(delete_box)
        buttons.addStretch(1)
        buttons.addWidget(finish)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)
        self._refresh_table()

    @staticmethod
    def _fraction_spin(value):
        spin = QDoubleSpinBox()
        spin.setRange(0.05, 0.90)
        spin.setSingleStep(0.05)
        spin.setDecimals(2)
        spin.setValue(value)
        return spin

    def _add_box(self):
        record = self._box_record()
        if record is None:
            return
        self.boxes.append(record)
        self._refresh_table()

    def _edit_box(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Set Fourier Filter Box", "Select a training box to edit.")
            return
        record = self._box_record()
        if record is None:
            return
        self.boxes[row] = record
        self._refresh_table()
        self.table.selectRow(row)

    def _box_record(self):
        if self.x.value() + self.width_spin.value() > 0.95 or self.y.value() + self.height_spin.value() > 0.95:
            QMessageBox.warning(self, "Set Fourier Filter Box", "The training box exceeds the maximum allowed image area.")
            return None
        channels = [index + 1 for index, box in enumerate(self.channels) if box.isChecked()]
        if not channels:
            QMessageBox.warning(self, "Set Fourier Filter Box", "Select at least one collection channel.")
            return None
        return {
            "x": self.x.value(),
            "y": self.y.value(),
            "width": self.width_spin.value(),
            "height": self.height_spin.value(),
            "channels": channels,
        }

    def _delete_box(self):
        row = self.table.currentRow()
        if row >= 0:
            self.boxes.pop(row)
            self._refresh_table()

    def _load_box(self, row, column):
        if not 0 <= row < len(self.boxes):
            return
        record = self.boxes[row]
        for control, key in (
            (self.x, "x"),
            (self.y, "y"),
            (self.width_spin, "width"),
            (self.height_spin, "height"),
        ):
            control.setValue(float(record.get(key, control.value())))
        selected = set(record.get("channels", []))
        for index, check in enumerate(self.channels, start=1):
            check.setChecked(index in selected)

    def _refresh_table(self):
        self.table.setRowCount(len(self.boxes))
        for row, record in enumerate(self.boxes):
            values = [
                f"{float(record.get('x', 0)):.2f}",
                f"{float(record.get('y', 0)):.2f}",
                f"{float(record.get('width', 0)):.2f}",
                f"{float(record.get('height', 0)):.2f}",
                ", ".join(str(value) for value in record.get("channels", [])),
            ]
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))


class AdvancedFourierOptionsDialog(QDialog):
    def __init__(self, options, parent=None):
        super().__init__(parent)
        options = options or {}
        self.result_options = None
        self.setWindowTitle("Advanced Fourier Filter Options")
        self.setFixedSize(560, 330)
        layout = QVBoxLayout(self)
        self.user_plan = QCheckBox("User defined Fourier Filter training sample plan")
        self.force_training = QCheckBox("Force training even if the layer is naturally Fourier filtered")
        self.use_test_optics = QCheckBox("Use Test Optics for Fourier Filter Training")
        self.user_plan.setChecked(bool(options.get("user_plan")))
        self.force_training.setChecked(bool(options.get("force_training")))
        self.use_test_optics.setChecked(bool(options.get("use_test_optics")))
        for check in (self.user_plan, self.force_training, self.use_test_optics):
            layout.addWidget(check)
        deck_grid = QGridLayout()
        deck_grid.addWidget(QLabel("Preferred Deck"), 0, 0)
        saved_decks = options.get("decks") if isinstance(options.get("decks"), dict) else {}
        legacy_deck = options.get("deck", "DECK 0")
        self.decks = []
        for channel in range(1, 4):
            deck_grid.addWidget(QLabel(f"Channel {channel}:"), channel, 0)
            deck = QComboBox()
            deck.addItems(["DECK 0", "DECK 1", "DECK 2"])
            deck.setCurrentText(saved_decks.get(str(channel), legacy_deck))
            deck_grid.addWidget(deck, channel, 1)
            self.decks.append(deck)
        layout.addLayout(deck_grid)
        layout.addStretch(1)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        ok = QPushButton("OK")
        ok.clicked.connect(self._accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)

    def _accept(self):
        self.result_options = {
            "user_plan": self.user_plan.isChecked(),
            "force_training": self.force_training.isChecked(),
            "use_test_optics": self.use_test_optics.isChecked(),
            "deck": self.decks[0].currentText(),
            "decks": {
                str(channel): deck.currentText()
                for channel, deck in enumerate(self.decks, start=1)
            },
        }
        self.accept()


class RodPositionsDialog(QDialog):
    def __init__(
        self,
        rods,
        boxes=None,
        incidence_angle="Oblique",
        enforce_specular_block=False,
        analysis_valid=False,
        parent=None,
    ):
        super().__init__(parent)
        state = normalize_fourier_state({"rods": rods})
        self.result_rods = deepcopy(state["rods"])
        self.result_enforce_specular = bool(enforce_specular_block)
        self.analysis_valid = bool(analysis_valid)
        self.boxes = deepcopy(boxes or [])
        self.setWindowTitle("Fourier Filter Rod Positions")
        self.resize(1120, 700)
        layout = QVBoxLayout(self)
        aperture_controls = QHBoxLayout()
        aperture_controls.addWidget(QLabel("Numerical Aperture:"))
        self.numerical_aperture = QDoubleSpinBox()
        self.numerical_aperture.setRange(0.10, 1.40)
        self.numerical_aperture.setDecimals(2)
        self.numerical_aperture.setSingleStep(0.05)
        self.numerical_aperture.setValue(0.90)
        self.numerical_aperture.valueChanged.connect(self._aperture_changed)
        aperture_controls.addWidget(self.numerical_aperture)
        aperture_controls.addWidget(
            QLabel("Changing NA automatically recalculates enabled rod positions.")
        )
        aperture_controls.addStretch(1)
        layout.addLayout(aperture_controls)
        self.tabs = QTabWidget()
        self.pages = []
        for channel in range(1, 4):
            records = [
                deepcopy(item)
                for item in self.result_rods
                if int(item["channel"]) == channel
            ]
            page = RodChannelPage(
                channel,
                records,
                self.boxes,
                enforce_specular_block and incidence_angle == "Normal",
                self._rods_changed,
            )
            self.pages.append(page)
            self.tabs.addTab(page, ("1 (Left)", "2 (Right)", "3 (Center)")[channel - 1])
        self.table = self.pages[0].table
        layout.addWidget(self.tabs, 1)

        self.auto_summary = QLabel()
        self.auto_summary.setWordWrap(True)
        layout.addWidget(self.auto_summary)

        self.enforce_specular = QCheckBox("Enforce Specular Block in Channel 1 and 2")
        self.enforce_specular.setChecked(self.result_enforce_specular)
        self.enforce_specular.setEnabled(incidence_angle == "Normal")
        self.enforce_specular.toggled.connect(self._specular_changed)
        layout.addWidget(self.enforce_specular)
        if incidence_angle != "Normal":
            layout.addWidget(QLabel("Specular blocking is available only with Normal incidence angle."))

        buttons = QHBoxLayout()
        analyze = QPushButton("Analyze")
        analyze.clicked.connect(self._analyze)
        self.recalc_button = QPushButton("Recalc Rods")
        self.recalc_button.clicked.connect(self._recalc_rods)
        self.box_selector = QComboBox()
        self.box_selector.addItems(
            [f"Training Box {index + 1}" for index in range(len(self.boxes))]
        )
        self.box_selector.currentIndexChanged.connect(self._box_changed)
        self.view_images = QPushButton("View Images")
        self.view_images.setEnabled(self.analysis_valid and bool(self.boxes))
        self.view_images.clicked.connect(self._view_images)
        zoom = QPushButton("Zoom")
        zoom.clicked.connect(self._zoom)
        legend = QPushButton("Legend")
        legend.clicked.connect(self._legend)
        finish = QPushButton("Finish")
        finish.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        for button in (analyze, self.recalc_button):
            buttons.addWidget(button)
        buttons.addWidget(self.box_selector)
        buttons.addWidget(self.view_images)
        buttons.addWidget(zoom)
        buttons.addWidget(legend)
        buttons.addStretch(1)
        buttons.addWidget(finish)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)
        self._update_auto_summary()

    def _invalidate_analysis(self):
        self.analysis_valid = False
        self.view_images.setEnabled(False)

    def _rods_changed(self):
        self._invalidate_analysis()
        self._update_auto_summary()

    def _update_auto_summary(self):
        counts = [
            sum(bool(record.get("enabled")) for record in page.records)
            for page in self.pages
        ]
        self.auto_summary.setText(
            "Curve result: "
            + " | ".join(
                f"CH{channel}: {count} rod{'s' if count != 1 else ''}"
                for channel, count in enumerate(counts, start=1)
            )
        )

    def _specular_changed(self, checked):
        for index, page in enumerate(self.pages):
            page.set_specular(bool(checked and index < 2))
        self._invalidate_analysis()

    def _box_changed(self, index):
        for page in self.pages:
            page.chart.box_index = max(0, index)
            page.chart.update()

    def _analyze(self):
        if not self._collect_rods():
            return
        for page in self.pages:
            page.analyze()
        self._collect_rods()
        self.analysis_valid = True
        self.view_images.setEnabled(bool(self.boxes))

    def _recalc_rods(self):
        for page in self.pages:
            page.recalculate(self.numerical_aperture.value())
        self._rods_changed()

    def _aperture_changed(self, value):
        for page in self.pages:
            page.recalculate(value)
        self._rods_changed()

    def _view_images(self):
        dialog = FourierImagesDialog(self.box_selector.currentIndex(), self)
        dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()

    def _zoom(self):
        for page in self.pages:
            page.chart.zoomed = not page.chart.zoomed
            page.chart.update()

    def _legend(self):
        QMessageBox.information(
            self,
            "Spectral Energy Chart Legend",
            "Green: spectral energy\nRed: background energy\n"
            "Colored vertical lines: enabled rods\nBlue: fixed specular-block rod",
        )

    def _collect_rods(self):
        records = []
        for page in self.pages:
            channel_records = page.collect()
            if channel_records is None:
                return False
            records.extend(channel_records)
        self.result_rods = records
        return True

    def _finish(self):
        if not self._collect_rods():
            return
        self.result_enforce_specular = (
            self.enforce_specular.isEnabled() and self.enforce_specular.isChecked()
        )
        self.accept()


class RodChannelPage(QWidget):
    def __init__(self, channel, records, boxes, specular, on_changed, parent=None):
        super().__init__(parent)
        self.channel = channel
        self.records = deepcopy(records)
        self.on_changed = on_changed
        self._loading = False
        layout = QHBoxLayout(self)
        self.chart = SpectralEnergyChart(
            channel,
            self.records,
            boxes,
            specular,
            self._rod_dragged,
        )
        layout.addWidget(self.chart, 1)
        side = QVBoxLayout()
        side.addWidget(QLabel(f"Rod Positions - Channel {channel}"))
        self.auto_status = QLabel()
        self.auto_status.setWordWrap(True)
        side.addWidget(self.auto_status)
        self.table = QTableWidget(len(self.records), 5)
        self.table.setHorizontalHeaderLabels(
            ["Deck", "Rod", "Enable", "Position", "Training Score"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.itemChanged.connect(self._item_changed)
        side.addWidget(self.table, 1)
        layout.addLayout(side)
        self._refresh_table()

    def _refresh_table(self):
        self._loading = True
        self.table.setRowCount(len(self.records))
        for row, record in enumerate(self.records):
            deck = QTableWidgetItem(f"DECK {int(record.get('deck', 1))}")
            deck.setFlags(deck.flags() & ~Qt.ItemIsEditable)
            rod = QTableWidgetItem(str(record["rod"]))
            rod.setFlags(rod.flags() & ~Qt.ItemIsEditable)
            enabled = QTableWidgetItem("")
            enabled.setCheckState(Qt.Checked if record.get("enabled") else Qt.Unchecked)
            score = QTableWidgetItem(str(record.get("score", "-")))
            score.setFlags(score.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 0, deck)
            self.table.setItem(row, 1, rod)
            self.table.setItem(row, 2, enabled)
            self.table.setItem(row, 3, QTableWidgetItem(f"{float(record['position']):.3f}"))
            self.table.setItem(row, 4, score)
        self._loading = False
        self._update_status()

    def _update_status(self):
        enabled_count = sum(bool(record.get("enabled")) for record in self.records)
        self.auto_status.setText(
            f"Enabled rods: {enabled_count} of {MAX_RODS_PER_CHANNEL}"
        )

    def _item_changed(self, item):
        if self._loading or not 0 <= item.row() < len(self.records):
            return
        row = item.row()
        if item.column() == 2:
            self.records[row]["enabled"] = item.checkState() == Qt.Checked
        elif item.column() == 3:
            try:
                position = float(item.text())
            except ValueError:
                return
            if 0.0 <= position <= 1.0:
                self.records[row]["position"] = position
        self.records[row]["score"] = "-"
        self.chart.rods = self.records
        self.chart.update()
        self._update_status()
        self.on_changed()

    def _rod_dragged(self, row, position):
        self.records[row]["position"] = position
        self.records[row]["score"] = "-"
        self._loading = True
        self.table.item(row, 3).setText(f"{position:.3f}")
        self.table.item(row, 4).setText("-")
        self._loading = False
        self.on_changed()

    def set_specular(self, enabled):
        self.chart.specular = enabled
        self.chart.update()

    def collect(self):
        records = []
        for row, record in enumerate(self.records):
            try:
                position = float(self.table.item(row, 3).text())
            except (AttributeError, TypeError, ValueError):
                QMessageBox.warning(self, "Rod Positions", "Rod positions must be numeric.")
                return None
            if not 0.0 <= position <= 1.0:
                QMessageBox.warning(
                    self,
                    "Rod Positions",
                    "Rod positions must be between 0.000 and 1.000.",
                )
                return None
            records.append(
                {
                    "rod": int(record["rod"]),
                    "deck": int(record.get("deck", 1)),
                    "enabled": self.table.item(row, 2).checkState() == Qt.Checked,
                    "channel": self.channel,
                    "position": position,
                    "score": self.table.item(row, 4).text(),
                }
            )
        self.records = records
        self.chart.rods = self.records
        return deepcopy(records)

    def analyze(self):
        if self.collect() is None:
            return
        samples = spectral_energy_samples(
            self.channel,
            self.chart.box_index,
        )
        baseline = max(value for _position, value, _background in samples)
        maximum_depth = max(
            0.01,
            baseline - min(value for _position, value, _background in samples),
        )
        self._loading = True
        for row, record in enumerate(self.records):
            energy, _background = spectral_energy_at(
                self.channel,
                record["position"],
                self.chart.box_index,
            )
            depth_ratio = max(0.0, min(1.0, (baseline - energy) / maximum_depth))
            score = f"{70.0 + depth_ratio * 29.0:.1f}" if record["enabled"] else "-"
            record["score"] = score
            self.table.item(row, 4).setText(score)
        self._loading = False
        self.chart.update()

    def recalculate(self, numerical_aperture=0.90):
        channel_rods = recalculate_rod_records(
            self.records,
            self.chart.boxes,
            numerical_aperture,
        )
        self.records = [
            record for record in channel_rods
            if int(record["channel"]) == self.channel
        ]
        self.chart.rods = self.records
        self._refresh_table()
        self.chart.update()


class SpectralEnergyChart(QWidget):
    ROD_COLORS = ["#2857e8", "#ed3ad2", "#189940", "#00c9d8", "#e12d2d"]

    def __init__(self, channel, rods, boxes, specular, on_dragged, parent=None):
        super().__init__(parent)
        self.channel = channel
        self.rods = rods
        self.boxes = boxes
        self.box_index = 0
        self.specular = specular
        self.on_dragged = on_dragged
        self.drag_row = None
        self.zoomed = False
        self.setMinimumSize(570, 430)

    def _plot_rect(self):
        return (48, 28, max(1, self.width() - 70), max(1, self.height() - 76))

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        pos = event.position() if hasattr(event, "position") else event.pos()
        left, _top, width, _height = self._plot_rect()
        nearest = None
        distance = 12.0
        for row, record in enumerate(self.rods):
            if not record.get("enabled"):
                continue
            x = left + float(record["position"]) * width
            if abs(pos.x() - x) < distance:
                distance = abs(pos.x() - x)
                nearest = row
        self.drag_row = nearest

    def mouseMoveEvent(self, event):
        if self.drag_row is None:
            return
        pos = event.position() if hasattr(event, "position") else event.pos()
        left, _top, width, _height = self._plot_rect()
        position = max(0.0, min(1.0, (pos.x() - left) / width))
        self.rods[self.drag_row]["position"] = position
        self.on_dragged(self.drag_row, position)
        self.update()

    def mouseReleaseEvent(self, event):
        self.drag_row = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#d3d0c8"))
        left, top, width, height = self._plot_rect()
        painter.setPen(QPen(QColor("#333333"), 1))
        painter.drawLine(left, top + height, left + width, top + height)
        painter.drawLine(left, top, left, top + height)
        painter.drawText(8, 20, "Energy")
        painter.drawText(left + width // 2 - 24, self.height() - 12, "Position")
        scale = 1.45 if self.zoomed else 1.0
        previous_green = None
        previous_red = None
        for pixel in range(width + 1):
            normalized = pixel / max(1, width)
            green, red = spectral_energy_at(self.channel, normalized, self.box_index)
            x = left + pixel
            green_point = (x, top + height - int(green * height * 0.92 * scale))
            red_point = (x, top + height - int(red * height * 0.92 * scale))
            if previous_green:
                painter.setPen(QPen(QColor("#00b928"), 1))
                painter.drawLine(previous_green[0], previous_green[1], green_point[0], green_point[1])
                painter.setPen(QPen(QColor("#e12b2b"), 1))
                painter.drawLine(previous_red[0], previous_red[1], red_point[0], red_point[1])
            previous_green = green_point
            previous_red = red_point
        for row, record in enumerate(self.rods):
            if not record.get("enabled"):
                continue
            color = QColor(self.ROD_COLORS[(int(record.get("deck", 1)) - 1) % len(self.ROD_COLORS)])
            x = left + int(float(record["position"]) * width)
            painter.setPen(QPen(color, 2))
            painter.drawLine(x, top, x, top + height)
        if self.specular and self.channel in (1, 2):
            x = left + width // 2
            painter.setPen(QPen(QColor("#1a4aa5"), 3))
            painter.drawLine(x, top, x, top + height)


class FourierImagesDialog(QDialog):
    def __init__(self, box_index, parent=None):
        super().__init__(parent)
        self.box_index = max(0, int(box_index))
        self.previews = []
        self.setWindowTitle("AIT Char - Fourier Filter Images")
        self.resize(1180, 760)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 6)
        layout.setSpacing(4)
        layout.addWidget(self._menu_bar())
        layout.addWidget(self._display_controls())

        self.heading = QLabel(
            f"Training Box {self.box_index + 1}: Fourier Filter image comparison"
        )
        self.heading.setStyleSheet("font-weight: 600;")
        layout.addWidget(self.heading)
        images = QGridLayout()
        images.setContentsMargins(0, 0, 0, 0)
        images.setSpacing(3)
        images.addWidget(QLabel(""), 0, 0)
        for channel in range(1, 4):
            channel_label = QLabel(f"Channel {channel}")
            channel_label.setAlignment(Qt.AlignCenter)
            images.addWidget(channel_label, 0, channel)
        images.addWidget(QLabel("Without FF"), 1, 0)
        images.addWidget(QLabel("With FF"), 2, 0)
        for row, filtered in enumerate((False, True), start=1):
            for channel in range(1, 4):
                preview = FourierPatternPreview(filtered, channel)
                self.previews.append(preview)
                images.addWidget(preview, row, channel)
        layout.addLayout(images, 1)

        image_row = QHBoxLayout()
        image_row.addWidget(QLabel("Image(s):"))
        self.image_selector = QComboBox()
        for filtered in (False, True):
            state = "after" if filtered else "before"
            for channel in range(1, 4):
                self.image_selector.addItem(
                    f"CH{channel} Box {self.box_index + 1} {state}.mim"
                )
        self.image_selector.currentIndexChanged.connect(self._image_selected)
        image_row.addWidget(self.image_selector)
        self.image_path = QLabel()
        self.image_path.setTextInteractionFlags(Qt.TextSelectableByMouse)
        image_row.addWidget(self.image_path, 1)
        layout.addLayout(image_row)

        self.analysis_result = QLabel("Image analysis has not been run.")
        layout.addWidget(self.analysis_result)
        self.event_log = QTextEdit()
        self.event_log.setReadOnly(True)
        self.event_log.setMaximumHeight(76)
        layout.addWidget(self.event_log)

        self._append_log("AIT Char opened with six simulated Fourier images.")
        self._image_selected(0)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        layout.addWidget(close, 0, Qt.AlignRight)

    def _menu_bar(self):
        menu_bar = QMenuBar()
        file_menu = menu_bar.addMenu("File")
        file_menu.addAction("Close", self.accept)
        view_menu = menu_bar.addMenu("View")
        view_menu.addAction("Fit Images", self._fit_images)
        register_menu = menu_bar.addMenu("Register")
        register_menu.addAction("Register Images", self._register_images)
        analysis_menu = menu_bar.addMenu("Image Analysis")
        analysis_menu.addAction("Analyze FF Suppression", self._analyze_images)
        config_menu = menu_bar.addMenu("Config")
        config_menu.addAction("Reset Display", self._reset_display)
        tools_menu = menu_bar.addMenu("Tools")
        tools_menu.addAction("Refresh Images", self._refresh_images)
        print_menu = menu_bar.addMenu("Print Screen")
        print_menu.addAction("Capture Layout", self._capture_layout)
        window_menu = menu_bar.addMenu("Window")
        window_menu.addAction("Three Channel View").setEnabled(False)
        help_menu = menu_bar.addMenu("Help")
        help_menu.addAction("AIT Char Help", self._show_help)
        return menu_bar

    def _display_controls(self):
        panel = QFrame()
        controls = QHBoxLayout(panel)
        controls.setContentsMargins(4, 2, 4, 2)
        controls.addWidget(QLabel("LUT Low"))
        self.lut_low = QSpinBox()
        self.lut_low.setRange(0, 4094)
        self.lut_low.setValue(0)
        self.lut_low.valueChanged.connect(self._display_changed)
        controls.addWidget(self.lut_low)
        controls.addWidget(QLabel("High"))
        self.lut_high = QSpinBox()
        self.lut_high.setRange(1, 4095)
        self.lut_high.setValue(4095)
        self.lut_high.valueChanged.connect(self._display_changed)
        controls.addWidget(self.lut_high)
        self.auto_scale = QCheckBox("Auto Scale")
        self.auto_scale.setChecked(True)
        self.auto_scale.toggled.connect(self._auto_scale_changed)
        controls.addWidget(self.auto_scale)
        self.grid_overlay = QCheckBox("3 x 3 Grid")
        self.grid_overlay.toggled.connect(self._display_changed)
        controls.addWidget(self.grid_overlay)
        controls.addWidget(QLabel("Palette"))
        self.palette = QComboBox()
        self.palette.addItems(["Spectrum", "Grayscale"])
        self.palette.currentTextChanged.connect(self._display_changed)
        controls.addWidget(self.palette)
        controls.addWidget(QLabel("Zoom"))
        self.zoom = QComboBox()
        self.zoom.addItems(["50%", "100%", "200%"])
        self.zoom.setCurrentText("100%")
        self.zoom.currentTextChanged.connect(self._display_changed)
        controls.addWidget(self.zoom)
        self.analyze_button = QPushButton("Analyze FF")
        self.analyze_button.clicked.connect(self._analyze_images)
        controls.addWidget(self.analyze_button)
        controls.addStretch(1)
        self.lut_low.setEnabled(False)
        self.lut_high.setEnabled(False)
        return panel

    def _display_changed(self, _value=None):
        if not hasattr(self, "previews"):
            return
        low = self.lut_low.value() if hasattr(self, "lut_low") else 0
        high = self.lut_high.value() if hasattr(self, "lut_high") else 4095
        if high <= low:
            if self.sender() is self.lut_low:
                self.lut_high.setValue(min(4095, low + 1))
            else:
                self.lut_low.setValue(max(0, high - 1))
            return
        zoom = int(self.zoom.currentText().rstrip("%")) if hasattr(self, "zoom") else 100
        palette = self.palette.currentText() if hasattr(self, "palette") else "Spectrum"
        show_grid = self.grid_overlay.isChecked() if hasattr(self, "grid_overlay") else False
        for preview in self.previews:
            preview.set_display_options(low, high, palette, zoom, show_grid)

    def _auto_scale_changed(self, checked):
        self.lut_low.setEnabled(not checked)
        self.lut_high.setEnabled(not checked)
        if checked:
            self.lut_low.setValue(0)
            self.lut_high.setValue(4095)
        self._display_changed()

    def _fit_images(self):
        self.zoom.setCurrentText("100%")
        self._append_log("All six images fitted to the AIT Char workspace.")

    def _register_images(self):
        self._append_log("Before/after FF images registered by channel and training box.")

    def _analyze_images(self):
        scores = []
        for channel in range(1, 4):
            samples = spectral_energy_samples(channel, self.box_index)
            energies = [energy for _position, energy, _background in samples]
            baseline = max(energies)
            suppression = 100.0 * (baseline - min(energies)) / max(0.01, baseline)
            scores.append(suppression)
        self.analysis_result.setText(
            "FF suppression: "
            + " | ".join(
                f"CH{channel} {score:.1f}%"
                for channel, score in enumerate(scores, start=1)
            )
        )
        self._append_log("Fourier-filter suppression analysis completed.")

    def _reset_display(self):
        self.auto_scale.setChecked(True)
        self.grid_overlay.setChecked(False)
        self.palette.setCurrentText("Spectrum")
        self.zoom.setCurrentText("100%")
        self._display_changed()
        self._append_log("Display configuration reset.")

    def _refresh_images(self):
        for preview in self.previews:
            preview.update()
        self._append_log("Simulated Fourier images refreshed.")

    def _capture_layout(self):
        self._append_log("Current AIT Char layout captured in the simulated session.")

    def _show_help(self):
        QMessageBox.information(
            self,
            "AIT Char Help",
            "Compare each channel before and after Fourier filtering. "
            "Use LUT, palette, grid, and zoom controls to inspect the simulated images.",
        )

    def _image_selected(self, index):
        name = self.image_selector.itemText(max(0, index))
        self.image_path.setText(
            f"SIM:/AITChar/FF/Box{self.box_index + 1}/{name}    951 x 129    12-bit"
        )

    def _append_log(self, message):
        self.event_log.append(message)


class FourierPatternPreview(QWidget):
    def __init__(self, filtered, channel=1, parent=None):
        super().__init__(parent)
        self.filtered = filtered
        self.channel = channel
        self.lut_low = 0
        self.lut_high = 4095
        self.palette = "Spectrum"
        self.zoom_percent = 100
        self.show_grid = False
        self.setMinimumSize(250, 210)

    def set_display_options(self, low, high, palette, zoom_percent, show_grid):
        self.lut_low = int(low)
        self.lut_high = int(high)
        self.palette = str(palette)
        self.zoom_percent = int(zoom_percent)
        self.show_grid = bool(show_grid)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        grayscale = self.palette == "Grayscale"
        zoom_scale = max(0.5, self.zoom_percent / 100.0)
        painter.fillRect(self.rect(), QColor("#343434" if grayscale else "#111b20"))
        painter.save()
        painter.translate(self.width() / 2, self.height() / 2)
        painter.scale(zoom_scale, zoom_scale)
        painter.translate(-self.width() / 2, -self.height() / 2)
        paint_simulated_die(
            painter,
            self.rect(),
            channel=self.channel,
            filtered=self.filtered,
            grayscale=grayscale,
        )
        painter.restore()
        if self.show_grid:
            painter.setPen(QPen(QColor(245, 245, 245, 150), 1))
            for column in range(1, 3):
                x = self.width() * column // 3
                painter.drawLine(x, 0, x, self.height())
            for row in range(1, 3):
                y = self.height() * row // 3
                painter.drawLine(0, y, self.width(), y)
        painter.fillRect(0, 0, self.width(), 25, QColor(10, 15, 18, 185))
        painter.setPen(QColor("#ffffff"))
        painter.drawText(
            self.rect(),
            Qt.AlignTop | Qt.AlignHCenter,
            f"CH{self.channel} - "
            + ("With Fourier Filtering" if self.filtered else "Without Fourier Filtering"),
        )

from __future__ import annotations

from copy import deepcopy

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
    QMessageBox,
    QPainter,
    QPen,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    Qt,
    QVBoxLayout,
    QWidget,
)

MAX_RODS_PER_CHANNEL = 11
MIN_BOX_SIZE = 0.05
MAX_BOX_EDGE = 0.95


def _default_rods():
    return [
        {
            "channel": channel,
            "rod": rod,
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
    def __init__(self, state=None, incidence_angle="Oblique", parent=None):
        super().__init__(parent)
        self.state = normalize_fourier_state(state)
        self.incidence_angle = incidence_angle
        self.result_state = None
        self.changed = False
        self.setWindowTitle("Fourier Filter Training")
        self.resize(820, 600)
        self.setStyleSheet(
            "QDialog { background: #d2cec5; font-family: Arial; font-size: 10px; }"
            "QPushButton { min-height: 28px; padding: 2px 10px; }"
            "QFrame#summary { background: #efede2; border: 1px solid #8c8982; }"
        )
        root = QHBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        commands = QVBoxLayout()
        for label, handler in [
            ("Fourier Filter\nSample Plan", self._sample_plan),
            ("Set Fourier\nFilter Box", self._set_box),
            ("Advanced...", self._advanced),
        ]:
            button = QPushButton(label)
            button.setFixedSize(150, 54)
            button.clicked.connect(handler)
            commands.addWidget(button)
        self.rod_button = QPushButton("Rod Positions")
        self.rod_button.setFixedSize(150, 54)
        self.rod_button.clicked.connect(self._rod_positions)
        commands.addWidget(self.rod_button)
        commands.addStretch(1)
        train = QPushButton("Train FF")
        train.setFixedSize(150, 42)
        train.clicked.connect(self._train)
        commands.addWidget(train)
        root.addLayout(commands)

        center = QVBoxLayout()
        title = QLabel("Fourier Filter Training Setup")
        title.setStyleSheet("font-size: 14px; font-weight: 700;")
        center.addWidget(title)
        self.preview = FourierPreview(self.state)
        center.addWidget(self.preview, 1)
        self.summary = QLabel()
        self.summary.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.summary.setMinimumHeight(64)
        self.summary.setWordWrap(True)
        center.addWidget(self.summary)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(100 if self.state["trained"] else 0)
        center.addWidget(self.progress)
        footer = QHBoxLayout()
        footer.addStretch(1)
        finish = QPushButton("Finish")
        finish.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        footer.addWidget(finish)
        footer.addWidget(cancel)
        center.addLayout(footer)
        root.addLayout(center, 1)
        self._refresh()

    def _sample_plan(self):
        dialog = FourierSamplePlanDialog(self.state["training_die"], self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.state["training_die"] = list(dialog.canvas.selected_die)
            self.state["trained"] = False
            self.changed = True
            self._refresh()

    def _set_box(self):
        dialog = FourierBoxDialog(self.state["boxes"], self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.state["boxes"] = deepcopy(dialog.boxes)
            self.state["trained"] = False
            self.changed = True
            self._refresh()

    def _advanced(self):
        dialog = AdvancedFourierOptionsDialog(self.state["options"], self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.state["options"] = dialog.result_options
            self.state["trained"] = False
            self.changed = True
            self._refresh()

    def _rod_positions(self):
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
        self.progress.setValue(0)
        for value in (20, 45, 70, 100):
            self.progress.setValue(value)
        self.state["trained"] = True
        self.state["analysis_valid"] = False
        self.changed = True
        self._refresh()
        QMessageBox.information(self, "Training Progress", "Fourier Filter training completed for the selected channels.")

    def _refresh(self):
        die = self.state["training_die"]
        status = "Valid" if self.state["trained"] else "Training required"
        self.summary.setText(
            f"Training Die: Row {die[1]}, Column {die[0]}    "
            f"Training Boxes: {len(self.state['boxes'])}\nStatus: {status}"
        )
        self.preview.state = self.state
        self.preview.update()
        self.rod_button.setEnabled(bool(self.state["trained"]))

    def _finish(self):
        self.result_state = deepcopy(self.state)
        self.accept()


class FourierPreview(QWidget):
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self.setMinimumSize(440, 360)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#66787f"))
        painter.setPen(QPen(QColor("#90a1a8"), 1))
        for offset in range(0, self.width(), 18):
            painter.drawLine(offset, 0, offset, self.height())
        for offset in range(0, self.height(), 18):
            painter.drawLine(0, offset, self.width(), offset)
        colors = [QColor("#ffdf00"), QColor("#00d070"), QColor("#f05050")]
        for index, box in enumerate(self.state.get("boxes", [])):
            painter.setPen(QPen(colors[index % len(colors)], 3))
            x = int(box.get("x", 0.2) * self.width())
            y = int(box.get("y", 0.2) * self.height())
            w = int(box.get("width", 0.25) * self.width())
            h = int(box.get("height", 0.25) * self.height())
            painter.drawRect(x, y, w, h)


class FourierSamplePlanDialog(QDialog):
    def __init__(self, selected_die, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Fourier Filter Sample Plan")
        self.resize(620, 590)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Click a die to select the Fourier Filter training die."))
        self.canvas = TrainingDieCanvas(selected_die)
        layout.addWidget(self.canvas, 1)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        finish = QPushButton("Finish")
        finish.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(finish)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)


class TrainingDieCanvas(QWidget):
    def __init__(self, selected_die, parent=None):
        super().__init__(parent)
        self.selected_die = tuple(selected_die or (0, 0))
        self.setMinimumSize(480, 440)

    def mousePressEvent(self, event):
        pos = event.position() if hasattr(event, "position") else event.pos()
        cell = min(self.width(), self.height()) / 17.0
        self.selected_die = (int(pos.x() / cell) - 8, int(pos.y() / cell) - 8)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#7c7c7c"))
        side = min(self.width(), self.height()) - 20
        x0 = (self.width() - side) // 2
        y0 = (self.height() - side) // 2
        cell = side / 17.0
        radius = side / 2
        for row in range(17):
            for col in range(17):
                cx = (col + 0.5) * cell - radius
                cy = (row + 0.5) * cell - radius
                if cx * cx + cy * cy > (radius - cell / 2) ** 2:
                    continue
                die = (col - 8, row - 8)
                painter.setBrush(QColor("#d84ce5") if die == self.selected_die else QColor("#eeeeee"))
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
        self.width = self._fraction_spin(0.25)
        self.height = self._fraction_spin(0.25)
        for row, (name, control) in enumerate([("X:", self.x), ("Y:", self.y), ("Width:", self.width), ("Height:", self.height)]):
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
        if self.x.value() + self.width.value() > 0.95 or self.y.value() + self.height.value() > 0.95:
            QMessageBox.warning(self, "Set Fourier Filter Box", "The training box exceeds the maximum allowed image area.")
            return None
        channels = [index + 1 for index, box in enumerate(self.channels) if box.isChecked()]
        if not channels:
            QMessageBox.warning(self, "Set Fourier Filter Box", "Select at least one collection channel.")
            return None
        return {
            "x": self.x.value(),
            "y": self.y.value(),
            "width": self.width.value(),
            "height": self.height.value(),
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
            (self.width, "width"),
            (self.height, "height"),
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
        self.resize(760, 520)
        layout = QVBoxLayout(self)
        self.table = QTableWidget(len(self.result_rods), 5)
        self.table.setHorizontalHeaderLabels(["Rod", "Enable", "Channel", "Position", "Training Score"])
        self.table.verticalHeader().setVisible(False)
        for row, record in enumerate(self.result_rods):
            self.table.setItem(row, 0, QTableWidgetItem(str(record["rod"])))
            enabled = QTableWidgetItem("")
            enabled.setCheckState(Qt.Checked if record["enabled"] else Qt.Unchecked)
            self.table.setItem(row, 1, enabled)
            channel = QTableWidgetItem(str(record["channel"]))
            channel.setFlags(channel.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 2, channel)
            self.table.setItem(row, 3, QTableWidgetItem(f"{float(record['position']):.3f}"))
            score = QTableWidgetItem(str(record.get("score", "-")))
            score.setFlags(score.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 4, score)
        layout.addWidget(self.table)
        self.enforce_specular = QCheckBox("Enforce Specular Block in Channel 1 and 2")
        self.enforce_specular.setChecked(self.result_enforce_specular)
        self.enforce_specular.setEnabled(incidence_angle == "Normal")
        layout.addWidget(self.enforce_specular)
        if incidence_angle != "Normal":
            layout.addWidget(QLabel("Specular blocking is available only with Normal incidence angle."))
        buttons = QHBoxLayout()
        analyze = QPushButton("Analyze")
        analyze.clicked.connect(self._analyze)
        self.box_selector = QComboBox()
        self.box_selector.addItems([f"Training Box {index + 1}" for index in range(len(self.boxes))])
        self.view_images = QPushButton("View Images")
        self.view_images.setEnabled(self.analysis_valid and bool(self.boxes))
        self.view_images.clicked.connect(self._view_images)
        finish = QPushButton("Finish")
        finish.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(analyze)
        buttons.addWidget(self.box_selector)
        buttons.addWidget(self.view_images)
        buttons.addStretch(1)
        buttons.addWidget(finish)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)

    def _analyze(self):
        if not self._collect_rods():
            return
        for row in range(self.table.rowCount()):
            if self.table.item(row, 1).checkState() == Qt.Checked:
                rod = int(self.table.item(row, 0).text())
                channel = int(self.table.item(row, 2).text())
                self.table.item(row, 4).setText(f"{96.0 - rod * 1.2 - channel * 0.6:.1f}")
            else:
                self.table.item(row, 4).setText("-")
        self.analysis_valid = True
        self.view_images.setEnabled(bool(self.boxes))

    def _view_images(self):
        dialog = FourierImagesDialog(self.box_selector.currentIndex(), self)
        dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()

    def _collect_rods(self):
        records = []
        for row in range(self.table.rowCount()):
            try:
                position = float(self.table.item(row, 3).text())
            except (AttributeError, TypeError, ValueError):
                QMessageBox.warning(self, "Rod Positions", "Rod positions must be numeric.")
                return False
            if not 0.0 <= position <= 1.0:
                QMessageBox.warning(self, "Rod Positions", "Rod positions must be between 0.000 and 1.000.")
                return False
            records.append(
                {
                    "rod": int(self.table.item(row, 0).text()),
                    "enabled": self.table.item(row, 1).checkState() == Qt.Checked,
                    "channel": int(self.table.item(row, 2).text()),
                    "position": position,
                    "score": self.table.item(row, 4).text(),
                }
            )
        self.result_rods = records
        return True

    def _finish(self):
        if not self._collect_rods():
            return
        self.result_enforce_specular = (
            self.enforce_specular.isEnabled() and self.enforce_specular.isChecked()
        )
        self.accept()


class FourierImagesDialog(QDialog):
    def __init__(self, box_index, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Fourier Filter Images")
        self.resize(720, 360)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Training Box {box_index + 1}: pattern comparison"))
        images = QHBoxLayout()
        images.addWidget(FourierPatternPreview(False))
        images.addWidget(FourierPatternPreview(True))
        layout.addLayout(images, 1)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        layout.addWidget(close, 0, Qt.AlignRight)


class FourierPatternPreview(QWidget):
    def __init__(self, filtered, parent=None):
        super().__init__(parent)
        self.filtered = filtered
        self.setMinimumSize(300, 250)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#244b5e"))
        painter.setPen(QPen(QColor("#79c8e8"), 2))
        spacing = 48 if self.filtered else 16
        for offset in range(0, self.width(), spacing):
            painter.drawLine(offset, 0, offset, self.height())
        for offset in range(0, self.height(), spacing):
            painter.drawLine(0, offset, self.width(), offset)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(
            self.rect(),
            Qt.AlignTop | Qt.AlignHCenter,
            "With Fourier Filtering" if self.filtered else "Without Fourier Filtering",
        )

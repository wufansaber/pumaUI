from __future__ import annotations

from copy import deepcopy
import json
from math import hypot
from pathlib import Path
import re

from ...qt_compat import (
    QCheckBox,
    QColor,
    QComboBox,
    QColorDialog,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
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
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    Qt,
    QVBoxLayout,
    QWidget,
)


SELECTION_MODES = ["Primary Threshold", "Secondary Threshold", "Do Not Inspect", "Do Not Report"]
MODE_COLORS = {
    "Primary Threshold": "#6f7793",
    "Secondary Threshold": "#c99200",
    "Do Not Inspect": "#dadada",
    "Do Not Report": "#18ba42",
}
DISPLAY_COLOR_DEFAULTS = {
    "Setup": {
        **MODE_COLORS,
        "Wafer Border": "#ffffff",
        "Origin Die": "#ff3030",
        "Reticle": "#18a6aa",
        "Edge Exclusion": "#ff3030",
    },
    "Run": {
        "Valid Die": "#6f7793",
        "Current Die": "#20b9ca",
        "Completed Die": "#18ba42",
        "Aborted Die": "#d64040",
    },
    "Review": {
        "Defect": "#2868d8",
        "Selected Defect": "#ffe000",
        "Marked Defect": "#ff3030",
        "Filtered Defect": "#8f8f8f",
    },
    "Alignment": {
        "Crosshair": "#00d060",
        "Site Marker": "#ff3030",
        "Die Grid": "#f0f0f0",
        "Image Background": "#315f72",
    },
}


def default_display_color_scheme():
    return {"name": "Default", "categories": deepcopy(DISPLAY_COLOR_DEFAULTS)}


def normalized_display_color_scheme(state=None):
    result = default_display_color_scheme()
    if isinstance(state, dict):
        result["name"] = str(state.get("name", "Default"))
        supplied = state.get("categories")
        if isinstance(supplied, dict):
            for category, values in supplied.items():
                if isinstance(values, dict):
                    result["categories"].setdefault(str(category), {}).update(
                        {str(name): str(color) for name, color in values.items()}
                    )
    return result


def serialize_display_color_scheme(state):
    return json.dumps(normalized_display_color_scheme(state), indent=2, sort_keys=True)


def parse_display_color_scheme(text):
    try:
        parsed = json.loads(text)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid color preference scheme") from exc
    result = normalized_display_color_scheme(parsed)
    invalid = [
        f"{category}/{name}"
        for category, values in result["categories"].items()
        for name, color in values.items()
        if not QColor(color).isValid()
    ]
    if invalid:
        raise ValueError(f"invalid colors: {', '.join(invalid)}")
    return result


def default_sample_plan() -> dict:
    return {
        "inspection_type": "Full Die",
        "selection_mode": "Primary Threshold",
        "coverage": 100.0,
        "coverage_basis": "Die Based",
        "edge_exclusion_enabled": False,
        "edge_exclusion_method": "In microns",
        "edge_exclusion_value": 3000.0,
        "allow_partial_die": False,
        "row_interval": 2,
        "row_offset": 0,
        "row_count": 1,
        "row_pattern_method": "Number of rows",
        "row_percentage": 50.0,
        "grid_pitch": 1,
        "grid_offset": 0,
        "overrides": {},
        "master_plans": {},
        "inspection_pattern": {"rows": 2, "columns": 2, "cells": [[True, True], [True, True]]},
        "colors": deepcopy(MODE_COLORS),
        "klarf_source": "",
    }


def normalized_sample_plan(state: dict | None) -> dict:
    result = default_sample_plan()
    if state:
        result.update(deepcopy(state))
    result["overrides"] = {
        str(key): value
        for key, value in deepcopy(result.get("overrides") or {}).items()
        if value in SELECTION_MODES and value != "Primary Threshold"
    }
    result["master_plans"] = deepcopy(result.get("master_plans") or {})
    result["inspection_pattern"] = deepcopy(
        result.get("inspection_pattern") or default_sample_plan()["inspection_pattern"]
    )
    result["colors"] = {**MODE_COLORS, **deepcopy(result.get("colors") or {})}
    if float(result.get("coverage", 100)) == 12.5:
        result["coverage"] = 12.0
    result["grid_offset"] = int(result.get("grid_offset", 0)) % max(
        1, int(result.get("grid_pitch", 1))
    )
    result["row_interval"] = max(1, int(result.get("row_interval", 2)))
    result["row_offset"] = max(0, int(result.get("row_offset", 0)))
    result["row_count"] = max(
        1, min(int(result.get("row_count", 1)), result["row_interval"])
    )
    result["row_percentage"] = max(
        1.0, min(100.0, float(result.get("row_percentage", 50.0)))
    )
    return result


def edge_boundary_fraction(state: dict, wafer_radius_um=150000.0) -> float:
    """Return the radius fraction of the configured inner edge boundary."""
    method = state.get("edge_exclusion_method", "In microns")
    value = max(0.0, float(state.get("edge_exclusion_value", 0.0)))
    if method == "As % of radius":
        fraction = 1.0 - value / 100.0
    elif method == "To current stage position":
        fraction = float(state.get("stage_radius_fraction", 0.78))
    else:
        radius = max(1.0, float(wafer_radius_um))
        fraction = 1.0 - value / radius
    return max(0.05, min(0.98, fraction))


def sample_plan_rows(state: dict, grid=31) -> list[int]:
    interval = max(1, int(state.get("row_interval", 2)))
    start = max(0, min(grid - 1, int(state.get("row_offset", 0))))
    if state.get("row_pattern_method") == "Percentage":
        count = round(interval * float(state.get("row_percentage", 50.0)) / 100.0)
    else:
        count = int(state.get("row_count", 1))
    count = max(1, min(interval, count))
    return [
        row
        for row in range(start, grid)
        if (row - start) % interval < count
    ]


def parse_klarf_sample_plan(text):
    match = re.search(r"SampleTestPlan\s+\d+\s+(.*?);", text, re.I | re.S)
    if not match:
        return []
    return [
        [int(x), int(y)]
        for x, y in re.findall(r"(-?\d+)\s+(-?\d+)", match.group(1))
    ]


def pattern_overrides(pattern, grid=31, mode="Primary Threshold"):
    rows = max(1, int(pattern.get("rows", 1)))
    columns = max(1, int(pattern.get("columns", 1)))
    cells = pattern.get("cells") or [[True]]
    center = grid // 2
    overrides = {}
    for row in range(grid):
        for column in range(grid):
            if (
                hypot(column - center, row - center) <= center - 0.35
                and bool(cells[row % rows][column % columns])
            ):
                overrides[f"{column - center},{row - center}"] = mode
    return overrides


def klarf_overrides(sites, grid=31):
    center = grid // 2
    overrides = {}
    for row in range(grid):
        for column in range(grid):
            if hypot(column - center, row - center) <= center - 0.35:
                overrides[f"{column - center},{row - center}"] = "Do Not Inspect"
    for x, y in sites:
        key = f"{int(x)},{int(y)}"
        if key in overrides:
            overrides[key] = "Primary Threshold"
    return overrides


class SamplePlanDialog(QDialog):
    def __init__(self, state=None, inner_die_defined=False, parent=None):
        super().__init__(parent)
        self.state = normalized_sample_plan(state)
        self.inner_die_defined = bool(inner_die_defined)
        self.result_state = None
        self.changed = False
        self.last_action_message = ""
        self.setWindowTitle("Sample Plan")
        self.resize(1360, 760)
        self.setMinimumSize(1280, 680)
        self.setStyleSheet(
            "QDialog { background: #cfcbc2; font-family: Arial; font-size: 10px; }"
            "QPushButton { background: #e7e5dc; border: 1px solid #77736b; min-height: 27px; padding: 2px 8px; }"
            "QFrame#controls { background: #ddd9d0; border-left: 1px solid #99958c; }"
        )
        root = QHBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)
        root.addLayout(self._command_panel())

        center = QVBoxLayout()
        self.canvas = SamplePlanCanvas(self.state, self._canvas_changed)
        center.addWidget(self.canvas, 1)
        self.status = QLabel()
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setWordWrap(True)
        center.addWidget(self.status)
        footer = QHBoxLayout()
        self.undo_button = QPushButton("Undo")
        self.undo_button.clicked.connect(self.canvas.undo)
        self.redo_button = QPushButton("Redo")
        self.redo_button.clicked.connect(self.canvas.redo)
        finish = QPushButton("Finish")
        finish.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        footer.addWidget(self.undo_button)
        footer.addWidget(self.redo_button)
        footer.addStretch(1)
        footer.addWidget(finish)
        footer.addWidget(cancel)
        center.addLayout(footer)
        root.addLayout(center, 1)
        root.addWidget(self._settings_panel())
        self._sync_controls()
        self._refresh_status()

    def _command_panel(self):
        layout = QVBoxLayout()
        layout.setSpacing(8)
        self.command_buttons = {}
        for label, handler in [
            ("Entire Wafer", self._entire_wafer),
            ("Edge Die", self._edge),
            ("Outside Die", self._outside),
            ("Inside Die", self._inside),
            ("Apply Mode to\nDie Rows", self._rows),
            ("Store as\nMaster Plan", self._store_master),
            ("Load\nMaster Plan", self._load_master),
            ("More...", self._more),
        ]:
            button = QPushButton(label)
            button.setFixedSize(178, 50)
            button.clicked.connect(handler)
            layout.addWidget(button)
            self.command_buttons[label.replace("\n", " ")] = button
        self.command_buttons["Select Edge"] = self.command_buttons["Edge Die"]
        self.command_buttons["Select Outside"] = self.command_buttons["Outside Die"]
        self.command_buttons["Select Inside"] = self.command_buttons["Inside Die"]
        self.command_buttons["Row Pattern"] = self.command_buttons["Apply Mode to Die Rows"]
        layout.addStretch(1)
        return layout

    def _settings_panel(self):
        panel = QFrame()
        panel.setObjectName("controls")
        panel.setFixedWidth(380)
        layout = QVBoxLayout(panel)
        layout.addWidget(QLabel("Inspection Type"))
        self.inspection_type = QComboBox()
        self.inspection_type.addItems(["Full Die", "Partial Die", "Inner Die"])
        inner_item = self.inspection_type.model().item(2)
        if inner_item is not None:
            inner_item.setEnabled(self.inner_die_defined)
        self.inspection_type.currentTextChanged.connect(self._set_inspection_type)
        layout.addWidget(self.inspection_type)

        layout.addSpacing(10)
        layout.addWidget(QLabel("Selection Mode"))
        self.mode_buttons = []
        for mode in SELECTION_MODES:
            button = QRadioButton(mode)
            button.toggled.connect(lambda checked, value=mode: self._set_mode(value) if checked else None)
            self.mode_buttons.append(button)
            layout.addWidget(button)

        layout.addSpacing(10)
        self.edge_enabled = QCheckBox("Distance from wafer edge")
        self.edge_enabled.toggled.connect(self._edge_enabled_changed)
        layout.addWidget(self.edge_enabled)
        self.edge_method = QComboBox()
        self.edge_method.addItems(["In microns", "As % of radius", "To current stage position"])
        self.edge_method.currentTextChanged.connect(self._edge_method_changed)
        layout.addWidget(self.edge_method)
        self.edge_value = QDoubleSpinBox()
        self.edge_value.setRange(0.0, 150000.0)
        self.edge_value.setDecimals(1)
        self.edge_value.valueChanged.connect(self._edge_value_changed)
        layout.addWidget(self.edge_value)
        self.apply_edge_button = QPushButton("Apply")
        self.apply_edge_button.clicked.connect(self._apply_edge)
        layout.addWidget(self.apply_edge_button)
        self.allow_partial = QCheckBox("Allow Partial Die")
        self.allow_partial.toggled.connect(self._allow_partial_changed)
        layout.addWidget(self.allow_partial)

        layout.addSpacing(10)
        layout.addWidget(QLabel("Swath Coverage"))
        self.coverage = QComboBox()
        self.coverage.addItems(["100%", "50%", "25%", "12%"])
        self.coverage.currentTextChanged.connect(self._coverage_changed)
        layout.addWidget(self.coverage)
        self.coverage_basis = QComboBox()
        self.coverage_basis.addItems(["Die Based", "Reticle Based"])
        self.coverage_basis.currentTextChanged.connect(self._coverage_basis_changed)
        layout.addWidget(self.coverage_basis)

        layout.addSpacing(10)
        layout.addWidget(QLabel("Grid Pitch"))
        pitch_row = QHBoxLayout()
        self.grid_shift_left = QPushButton("Left")
        self.grid_shift_left.setToolTip("Shift the inspection grid one die to the left")
        self.grid_shift_left.clicked.connect(lambda: self._shift_grid(-1))
        self.grid_pitch = QSpinBox()
        self.grid_pitch.setRange(1, 8)
        self.grid_pitch.valueChanged.connect(self._pitch_changed)
        self.grid_shift_right = QPushButton("Right")
        self.grid_shift_right.setToolTip("Shift the inspection grid one die to the right")
        self.grid_shift_right.clicked.connect(lambda: self._shift_grid(1))
        pitch_row.addWidget(self.grid_shift_left)
        pitch_row.addWidget(self.grid_pitch)
        pitch_row.addWidget(self.grid_shift_right)
        layout.addLayout(pitch_row)
        layout.addStretch(1)
        return panel

    def _sync_controls(self):
        self.inspection_type.setCurrentText(self.state["inspection_type"])
        for button in self.mode_buttons:
            button.setChecked(button.text() == self.state["selection_mode"])
        self.edge_enabled.setChecked(bool(self.state["edge_exclusion_enabled"]))
        self.edge_method.setCurrentText(self.state["edge_exclusion_method"])
        self.edge_value.setValue(float(self.state["edge_exclusion_value"]))
        self.allow_partial.setChecked(bool(self.state["allow_partial_die"]))
        coverage = float(self.state["coverage"])
        self.coverage.setCurrentText(f"{coverage:g}%")
        self.coverage_basis.setCurrentText(self.state.get("coverage_basis", "Die Based"))
        self.grid_pitch.setValue(int(self.state["grid_pitch"]))
        self._update_edge_controls()

    def _set_inspection_type(self, value):
        self.state["inspection_type"] = value
        if value == "Partial Die":
            self.state["edge_exclusion_enabled"] = True
            self.state["edge_exclusion_method"] = "In microns"
            self.state["edge_exclusion_value"] = 2000.0
            self.edge_enabled.setChecked(True)
            self.edge_method.setCurrentText("In microns")
            self.edge_value.setValue(2000.0)
        self._changed()

    def _set_mode(self, value):
        self.state["selection_mode"] = value
        self._changed(repaint=False)

    def _edge_enabled_changed(self, checked):
        self.state["edge_exclusion_enabled"] = bool(checked)
        self._update_edge_controls()
        self._changed()

    def _edge_method_changed(self, value):
        self.state["edge_exclusion_method"] = value
        self._update_edge_controls()
        self._changed()

    def _edge_value_changed(self, value):
        self.state["edge_exclusion_value"] = float(value)
        self._changed()

    def _allow_partial_changed(self, checked):
        self.state["allow_partial_die"] = bool(checked)
        self._changed()

    def _coverage_changed(self, text):
        self.state["coverage"] = float(text.rstrip("%"))
        self._changed()

    def _coverage_basis_changed(self, value):
        self.state["coverage_basis"] = value
        self._changed()

    def _pitch_changed(self, value):
        self.state["grid_pitch"] = int(value)
        self.state["grid_offset"] %= int(value)
        self._changed()

    def _shift_grid(self, amount):
        pitch = max(1, int(self.state["grid_pitch"]))
        previous = int(self.state.get("grid_offset", 0))
        requested = (previous + amount) % pitch
        self.state["grid_offset"] = requested
        if pitch == 1:
            self.last_action_message = "Grid position cannot shift while Grid Pitch is 1."
        else:
            direction = "left" if amount < 0 else "right"
            self.last_action_message = (
                f"Inspection grid shifted {direction}; phase {requested + 1} of {pitch}."
            )
        self._changed()

    def _update_edge_controls(self):
        enabled = self.edge_enabled.isChecked()
        self.edge_method.setEnabled(enabled)
        self.edge_value.setEnabled(enabled and self.edge_method.currentText() != "To current stage position")

    def _apply_edge(self):
        if not self.edge_enabled.isChecked():
            self.edge_enabled.setChecked(True)
        self.canvas.apply_edge_exclusion()

    def _entire_wafer(self):
        self.canvas.apply_region("entire")

    def _edge(self):
        self.canvas.apply_region("edge")

    def _outside(self):
        if not self._require_edge_boundary():
            return
        self.canvas.apply_region("outside")

    def _inside(self):
        if not self._require_edge_boundary():
            return
        self.canvas.apply_region("inside")

    def _require_edge_boundary(self):
        if self.edge_enabled.isChecked():
            return True
        self.edge_enabled.setChecked(True)
        return True

    def _rows(self):
        dialog = RowPatternDialog(self.state, self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.state["row_interval"] = dialog.interval.value()
            self.state["row_offset"] = dialog.start_row.value() - 1
            self.state["row_count"] = min(
                dialog.row_count.value(), dialog.interval.value()
            )
            self.state["row_pattern_method"] = dialog.method.currentText()
            self.state["row_percentage"] = dialog.percentage.value()
            self.canvas.apply_rows()

    def _store_master(self):
        snapshot = deepcopy(self.state)
        snapshot.pop("master_plans", None)
        self.state["master_plans"] = {"Master Sample Plan": snapshot}
        self.changed = True
        self._refresh_status()
        QMessageBox.information(self, "Master Sample Plan", "The current sample plan was stored as the recipe master plan.")

    def _load_master(self):
        saved = self.state.get("master_plans", {}).get("Master Sample Plan")
        if saved is None:
            QMessageBox.information(self, "Master Sample Plan", "No master sample plan has been stored for this recipe.")
            return
        masters = deepcopy(self.state.get("master_plans", {}))
        self.state.clear()
        self.state.update(normalized_sample_plan(saved))
        self.state["master_plans"] = masters
        self.canvas.state = self.state
        self.canvas.clear_history()
        self._sync_controls()
        self._changed()

    def _more(self):
        dialog = MasterSamplePlanDialog(self.state, self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.state.clear()
            self.state.update(dialog.result_state)
            self.canvas.state = self.state
            self.canvas.clear_history()
            self._sync_controls()
            self._changed()

    def _canvas_changed(self):
        self.changed = True
        self.last_action_message = self.canvas.last_action_message
        self._refresh_status()

    def _changed(self, repaint=True):
        self.changed = True
        if repaint:
            self.canvas.update()
        self._refresh_status()

    def _refresh_status(self):
        counts = {mode: 0 for mode in SELECTION_MODES}
        for mode in self.state["overrides"].values():
            counts[mode] = counts.get(mode, 0) + 1
        self.status.setText(
            f"Coverage {float(self.state['coverage']):g}%   |   Modified die {len(self.state['overrides'])}\n"
            f"Excluded {counts['Do Not Inspect']}   |   Do Not Report {counts['Do Not Report']}"
            + (f"\n{self.last_action_message}" if self.last_action_message else "")
        )

    def _finish(self):
        if self.state["inspection_type"] == "Inner Die" and not self.inner_die_defined:
            QMessageBox.warning(
                self,
                "Sample Plan",
                "Define Inner Die during Wafer Map Setup before using Inner Die inspection.",
            )
            return
        self.result_state = deepcopy(self.state)
        self.accept()


class SamplePlanCanvas(QWidget):
    GRID = 31

    def __init__(self, state, on_change, parent=None):
        super().__init__(parent)
        self.state = state
        self.on_change = on_change
        self.history = []
        self.redo_stack = []
        self.last_action_message = ""
        self.setMinimumSize(520, 520)

    def _geometry(self):
        side = min(self.width(), self.height()) - 26
        return (self.width() - side) / 2, (self.height() - side) / 2, side, side / self.GRID

    def _inside_wafer(self, col, row):
        center = (self.GRID - 1) / 2
        return hypot(col - center, row - center) <= center - 0.35

    def _key(self, col, row):
        return f"{col - self.GRID // 2},{row - self.GRID // 2}"

    def _snapshot(self):
        self.history.append(deepcopy(self.state["overrides"]))
        self.history = self.history[-30:]
        self.redo_stack.clear()

    def clear_history(self):
        self.history.clear()
        self.redo_stack.clear()

    def _apply_cells(self, cells, action="Selection"):
        cells = [
            (col, row)
            for col, row in dict.fromkeys(cells)
            if self._inside_wafer(col, row)
        ]
        self._snapshot()
        mode = self.state["selection_mode"]
        changed = 0
        for col, row in cells:
            key = self._key(col, row)
            previous = self.state["overrides"].get(key, "Primary Threshold")
            if previous != mode:
                changed += 1
            if mode == "Primary Threshold":
                self.state["overrides"].pop(key, None)
            else:
                self.state["overrides"][key] = mode
        self.last_action_message = (
            f"{action}: applied {mode} to {len(cells)} die; {changed} changed."
        )
        self.update()
        self.on_change()

    def apply_region(self, region):
        center = (self.GRID - 1) / 2
        boundary = edge_boundary_fraction(self.state)
        half_cell_radius = 2 ** 0.5 * 0.5 / center
        cells = []
        for row in range(self.GRID):
            for col in range(self.GRID):
                if not self._inside_wafer(col, row):
                    continue
                distance = hypot(col - center, row - center) / center
                if (
                    region == "entire"
                    or region == "inside" and distance + half_cell_radius < boundary
                    or region == "outside" and distance + half_cell_radius >= boundary
                    or region == "edge" and distance >= 0.82
                ):
                    cells.append((col, row))
        labels = {
            "entire": "Entire Wafer",
            "inside": "Inside Die",
            "outside": "Outside Die",
            "edge": "Edge Die",
        }
        self._apply_cells(cells, labels.get(region, "Region"))

    def apply_rows(self):
        selected_rows = sample_plan_rows(self.state, self.GRID)
        cells = [
            (col, row)
            for row in selected_rows
            for col in range(self.GRID)
        ]
        self._apply_cells(cells, "Row Pattern")

    def apply_edge_exclusion(self):
        boundary = edge_boundary_fraction(self.state)
        center = (self.GRID - 1) / 2
        half_cell_radius = 2 ** 0.5 * 0.5 / center
        cells = []
        for row in range(self.GRID):
            for col in range(self.GRID):
                distance = hypot(col - center, row - center) / center
                if self._inside_wafer(col, row) and distance + half_cell_radius >= boundary:
                    cells.append((col, row))
        previous = self.state["selection_mode"]
        self.state["selection_mode"] = "Do Not Inspect"
        self._apply_cells(cells, "Edge Exclusion")
        self.state["selection_mode"] = previous

    def undo(self):
        if not self.history:
            self.last_action_message = "Undo: no earlier Sample Plan change."
            self.on_change()
            return
        self.redo_stack.append(deepcopy(self.state["overrides"]))
        self.state["overrides"] = self.history.pop()
        self.last_action_message = "Undo: restored the previous Sample Plan."
        self.update()
        self.on_change()

    def redo(self):
        if not self.redo_stack:
            self.last_action_message = "Redo: no later Sample Plan change."
            self.on_change()
            return
        self.history.append(deepcopy(self.state["overrides"]))
        self.state["overrides"] = self.redo_stack.pop()
        self.last_action_message = "Redo: reapplied the Sample Plan change."
        self.update()
        self.on_change()

    def mousePressEvent(self, event):
        pos = event.position() if hasattr(event, "position") else event.pos()
        x0, y0, side, cell = self._geometry()
        col = int((pos.x() - x0) / cell)
        row = int((pos.y() - y0) / cell)
        if 0 <= col < self.GRID and 0 <= row < self.GRID and self._inside_wafer(col, row):
            self._apply_cells([(col, row)], "Die Selection")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#7d7d7d"))
        x0, y0, side, cell = self._geometry()
        center = (self.GRID - 1) / 2
        for row in range(self.GRID):
            for col in range(self.GRID):
                if not self._inside_wafer(col, row):
                    continue
                key = self._key(col, row)
                mode = self.state["overrides"].get(key, "Primary Threshold")
                painter.setBrush(QColor(self.state.get("colors", MODE_COLORS).get(mode, MODE_COLORS[mode])))
                painter.setPen(QPen(QColor("#f5f5f5"), 1))
                painter.drawRect(int(x0 + col * cell), int(y0 + row * cell), max(1, int(cell - 1)), max(1, int(cell - 1)))
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor("#ffffff"), 2))
        painter.drawEllipse(int(x0), int(y0), int(side), int(side))
        if self.state.get("edge_exclusion_enabled"):
            fraction = edge_boundary_fraction(self.state)
            inset = side * (1.0 - fraction) / 2
            painter.setPen(QPen(QColor("#ff3030"), 2, Qt.DotLine))
            painter.drawEllipse(int(x0 + inset), int(y0 + inset), int(side * fraction), int(side * fraction))
        pitch = max(1, int(self.state.get("grid_pitch", 1)))
        offset = int(self.state.get("grid_offset", 0)) % pitch
        if pitch > 1:
            painter.setPen(QPen(QColor("#202020"), 2, Qt.DashLine))
            for index in range(offset, self.GRID, pitch):
                coordinate = int(x0 + index * cell)
                painter.drawLine(coordinate, int(y0), coordinate, int(y0 + side))


class RowPatternDialog(QDialog):
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sample Plan Row Pattern")
        self.setFixedSize(600, 340)
        layout = QGridLayout(self)
        layout.setColumnMinimumWidth(0, 230)
        layout.setColumnMinimumWidth(1, 300)
        layout.addWidget(QLabel("Starting at Row:"), 0, 0)
        self.start_row = QSpinBox()
        self.start_row.setRange(1, SamplePlanCanvas.GRID)
        self.start_row.setValue(int(state.get("row_offset", 0)) + 1)
        layout.addWidget(self.start_row, 0, 1)
        layout.addWidget(QLabel("Pattern definition:"), 1, 0)
        self.method = QComboBox()
        self.method.addItems(["Number of rows", "Percentage"])
        self.method.setCurrentText(state.get("row_pattern_method", "Number of rows"))
        self.method.currentTextChanged.connect(self._sync_method)
        layout.addWidget(self.method, 1, 1)
        layout.addWidget(QLabel("Inspect rows:"), 2, 0)
        self.row_count = QSpinBox()
        self.row_count.setRange(1, 20)
        self.row_count.setValue(int(state.get("row_count", 1)))
        layout.addWidget(self.row_count, 2, 1)
        layout.addWidget(QLabel("Out of every rows:"), 3, 0)
        self.interval = QSpinBox()
        self.interval.setRange(1, 20)
        self.interval.setValue(int(state.get("row_interval", 2)))
        layout.addWidget(self.interval, 3, 1)
        layout.addWidget(QLabel("Rows to inspect:"), 4, 0)
        self.percentage = QDoubleSpinBox()
        self.percentage.setRange(1.0, 100.0)
        self.percentage.setSuffix(" %")
        self.percentage.setValue(float(state.get("row_percentage", 50.0)))
        layout.addWidget(self.percentage, 4, 1)
        finish = QPushButton("Apply")
        finish.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        layout.addWidget(finish, 6, 0)
        layout.addWidget(cancel, 6, 1)
        self._sync_method()

    def _sync_method(self):
        by_percentage = self.method.currentText() == "Percentage"
        self.row_count.setEnabled(not by_percentage)
        self.percentage.setEnabled(by_percentage)


class MasterSamplePlanDialog(QDialog):
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.result_state = deepcopy(state)
        self.setWindowTitle("Sample Plan - More")
        self.resize(620, 500)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Master Sample Plan"))
        self.name = QComboBox()
        self.name.setEditable(True)
        self.name.addItems(sorted(self.result_state.get("master_plans", {}).keys()))
        layout.addWidget(self.name)
        actions = QHBoxLayout()
        store = QPushButton("Store")
        store.clicked.connect(self._store)
        load = QPushButton("Load")
        load.clicked.connect(self._load)
        actions.addWidget(store)
        actions.addWidget(load)
        layout.addLayout(actions)
        more_actions = QGridLayout()
        for index, (label, handler) in enumerate(
            (
                ("Die Inspection Pattern", self._pattern),
                ("Toggle Legend", self._legend),
                ("Customize Colors", self._colors),
                ("Import KLARF Sample Plan", self._import_klarf),
            )
        ):
            button = QPushButton(label)
            button.clicked.connect(handler)
            more_actions.addWidget(button, index // 2, index % 2)
        layout.addLayout(more_actions)
        legend = QGridLayout()
        legend.addWidget(QLabel("Die Pattern / Legend"), 0, 0, 1, 2)
        for row, mode in enumerate(SELECTION_MODES, start=1):
            swatch = QFrame()
            swatch.setFixedSize(18, 18)
            swatch.setStyleSheet(f"background: {MODE_COLORS[mode]}; border: 1px solid #555;")
            legend.addWidget(swatch, row, 0)
            legend.addWidget(QLabel(mode), row, 1)
        layout.addLayout(legend)
        layout.addStretch(1)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        ok = QPushButton("OK")
        ok.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)

    def _store(self):
        name = self.name.currentText().strip()
        if not name:
            QMessageBox.warning(self, "Master Sample Plan", "Enter a name for the master sample plan.")
            return
        snapshot = deepcopy(self.result_state)
        snapshot.pop("master_plans", None)
        self.result_state.setdefault("master_plans", {})[name] = snapshot
        if self.name.findText(name) < 0:
            self.name.addItem(name)

    def _load(self):
        name = self.name.currentText().strip()
        saved = self.result_state.get("master_plans", {}).get(name)
        if not saved:
            QMessageBox.warning(self, "Master Sample Plan", "Select a stored master sample plan.")
            return
        plans = deepcopy(self.result_state.get("master_plans", {}))
        self.result_state = normalized_sample_plan(saved)
        self.result_state["master_plans"] = plans

    def _pattern(self):
        dialog = DieInspectionPatternDialog(
            self.result_state.get("inspection_pattern"),
            self,
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.result_state["inspection_pattern"] = dialog.result_pattern
            self.result_state["overrides"].update(
                pattern_overrides(
                    dialog.result_pattern,
                    mode=self.result_state.get("selection_mode", "Primary Threshold"),
                )
            )

    def _legend(self):
        dialog = SamplePlanLegendDialog(self.result_state.get("colors"), self)
        dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()

    def _colors(self):
        dialog = SamplePlanColorsDialog(self.result_state.get("colors"), self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.result_state["colors"] = dialog.result_colors

    def _import_klarf(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import KLARF Sample Plan",
            "",
            "KLARF Files (*.001 *.klarf);;All Files (*.*)",
        )
        if not path:
            return
        try:
            sites = parse_klarf_sample_plan(
                Path(path).read_text(encoding="utf-8", errors="ignore")
            )
        except OSError as exc:
            QMessageBox.warning(self, "Import KLARF Sample Plan", str(exc))
            return
        if not sites:
            QMessageBox.warning(
                self,
                "Import KLARF Sample Plan",
                "The selected file does not contain a SampleTestPlan section.",
            )
            return
        self.result_state["overrides"] = klarf_overrides(sites)
        self.result_state["klarf_source"] = path


class DieInspectionPatternDialog(QDialog):
    def __init__(self, pattern=None, parent=None):
        super().__init__(parent)
        pattern = deepcopy(pattern or default_sample_plan()["inspection_pattern"])
        self.result_pattern = pattern
        self.setWindowTitle("Die Inspection Pattern")
        self.resize(520, 460)
        layout = QVBoxLayout(self)
        size = QHBoxLayout()
        self.rows = QSpinBox()
        self.rows.setRange(1, 8)
        self.rows.setValue(int(pattern.get("rows", 2)))
        self.columns = QSpinBox()
        self.columns.setRange(1, 8)
        self.columns.setValue(int(pattern.get("columns", 2)))
        size.addWidget(QLabel("Rows:"))
        size.addWidget(self.rows)
        size.addWidget(QLabel("Columns:"))
        size.addWidget(self.columns)
        layout.addLayout(size)
        self.table = QTableWidget()
        self.table.horizontalHeader().setVisible(False)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table, 1)
        self.rows.valueChanged.connect(self._rebuild)
        self.columns.valueChanged.connect(self._rebuild)
        actions = QHBoxLayout()
        for text, handler in (
            ("Fill", lambda: self._set_all(True)),
            ("Clear", lambda: self._set_all(False)),
            ("Invert", self._invert),
            ("Delete", self._default),
        ):
            button = QPushButton(text)
            button.clicked.connect(handler)
            actions.addWidget(button)
        layout.addLayout(actions)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        apply_button = QPushButton("Apply Pattern")
        apply_button.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(apply_button)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)
        self._rebuild()
        cells = pattern.get("cells") or []
        for row in range(min(self.rows.value(), len(cells))):
            for column in range(min(self.columns.value(), len(cells[row]))):
                self.table.item(row, column).setCheckState(
                    Qt.Checked if cells[row][column] else Qt.Unchecked
                )

    def _rebuild(self):
        previous = self._cells() if self.table.rowCount() else []
        self.table.setRowCount(self.rows.value())
        self.table.setColumnCount(self.columns.value())
        for row in range(self.rows.value()):
            for column in range(self.columns.value()):
                checked = (
                    previous[row][column]
                    if row < len(previous) and column < len(previous[row])
                    else True
                )
                item = QTableWidgetItem("")
                item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
                self.table.setItem(row, column, item)

    def _cells(self):
        return [
            [
                self.table.item(row, column).checkState() == Qt.Checked
                for column in range(self.table.columnCount())
            ]
            for row in range(self.table.rowCount())
        ]

    def _set_all(self, checked):
        for row in range(self.table.rowCount()):
            for column in range(self.table.columnCount()):
                self.table.item(row, column).setCheckState(
                    Qt.Checked if checked else Qt.Unchecked
                )

    def _invert(self):
        for row in range(self.table.rowCount()):
            for column in range(self.table.columnCount()):
                item = self.table.item(row, column)
                item.setCheckState(
                    Qt.Unchecked if item.checkState() == Qt.Checked else Qt.Checked
                )

    def _default(self):
        self.rows.setValue(1)
        self.columns.setValue(1)
        self._set_all(True)

    def _finish(self):
        self.result_pattern = {
            "rows": self.rows.value(),
            "columns": self.columns.value(),
            "cells": self._cells(),
        }
        self.accept()


class SamplePlanLegendDialog(QDialog):
    def __init__(self, colors=None, parent=None):
        super().__init__(parent)
        colors = {**MODE_COLORS, **(colors or {})}
        self.setWindowTitle("Sample Plan Legend")
        self.setFixedSize(440, 320)
        layout = QGridLayout(self)
        for row, mode in enumerate(SELECTION_MODES):
            swatch = QFrame()
            swatch.setFixedSize(24, 24)
            swatch.setStyleSheet(
                f"background: {colors[mode]}; border: 1px solid #555;"
            )
            layout.addWidget(swatch, row, 0)
            layout.addWidget(QLabel(mode), row, 1)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        layout.addWidget(close, len(SELECTION_MODES), 1)


class SamplePlanColorsDialog(QDialog):
    def __init__(self, colors=None, parent=None):
        super().__init__(parent)
        if isinstance(colors, dict) and "categories" in colors:
            self.scheme = normalized_display_color_scheme(colors)
        else:
            self.scheme = default_display_color_scheme()
            self.scheme["categories"]["Setup"].update(colors or {})
        self.result_scheme = None
        self.result_colors = deepcopy(self.scheme["categories"]["Setup"])
        self._loading = False
        self.setWindowTitle("Color Preferences - Display")
        self.resize(720, 520)
        layout = QGridLayout(self)
        layout.addWidget(QLabel("Scheme Name"), 0, 0)
        self.scheme_name = QLineEdit(self.scheme.get("name", "Default"))
        layout.addWidget(self.scheme_name, 0, 1)
        layout.addWidget(QLabel("Category"), 1, 0)
        self.category = QComboBox()
        self.category.setEditable(True)
        self.category.addItems(self.scheme["categories"].keys())
        self.category.currentTextChanged.connect(self._load_category)
        layout.addWidget(self.category, 1, 1)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Item", "Color"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.cellDoubleClicked.connect(self._choose_color)
        layout.addWidget(self.table, 2, 0, 1, 4)
        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(self._capture_category)
        save_all = QPushButton("Save All")
        save_all.clicked.connect(self._save_all)
        load = QPushButton("Load .cps")
        load.clicked.connect(self._load_file)
        restore = QPushButton("Restore All")
        restore.clicked.connect(self._restore_all)
        restore_category = QPushButton("Restore Category")
        restore_category.clicked.connect(self._restore_category)
        ok = QPushButton("OK")
        ok.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        for column, button in enumerate(
            (apply_button, save_all, load, restore, restore_category, ok, cancel)
        ):
            layout.addWidget(button, 3 + column // 4, column % 4)
        self._load_category(self.category.currentText())

    def _capture_category(self):
        if self._loading:
            return True
        category = self.category.currentText().strip()
        if not category:
            QMessageBox.warning(self, "Color Preferences", "Enter a category name.")
            return False
        values = {}
        for row in range(self.table.rowCount()):
            name = self.table.item(row, 0).text().strip()
            color = self.table.item(row, 1).text().strip()
            if not name or not QColor(color).isValid():
                QMessageBox.warning(self, "Color Preferences", "Each item requires a valid color.")
                return False
            values[name] = color
        self.scheme["categories"][category] = values
        self.scheme["name"] = self.scheme_name.text().strip() or "Default"
        if self.category.findText(category) < 0:
            self.category.addItem(category)
        return True

    def _load_category(self, category):
        if not category:
            return
        values = self.scheme["categories"].get(category, {})
        self._loading = True
        self.table.setRowCount(len(values))
        for row, (name, color) in enumerate(values.items()):
            self.table.setItem(row, 0, QTableWidgetItem(name))
            item = QTableWidgetItem(color)
            item.setBackground(QColor(color))
            self.table.setItem(row, 1, item)
        self._loading = False

    def _choose_color(self, row, column):
        if column not in (0, 1):
            return
        color_item = self.table.item(row, 1)
        selected = QColorDialog.getColor(QColor(color_item.text()), self, "Change Color")
        if selected.isValid():
            color_item.setText(selected.name())
            color_item.setBackground(selected)

    def _restore_all(self):
        self.scheme = default_display_color_scheme()
        self.scheme_name.setText("Default")
        self.category.clear()
        self.category.addItems(self.scheme["categories"].keys())
        self._load_category(self.category.currentText())

    def _restore_category(self):
        category = self.category.currentText().strip()
        self.scheme["categories"][category] = deepcopy(DISPLAY_COLOR_DEFAULTS.get(category, {}))
        self._load_category(category)

    def _save_all(self):
        if not self._capture_category():
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Color Preferences - Display", f"{self.scheme['name']}.cps", "Color Preference Scheme (*.cps)"
        )
        if not path:
            return
        target = Path(path)
        if target.suffix.lower() != ".cps":
            target = target.with_suffix(".cps")
        try:
            target.write_text(serialize_display_color_scheme(self.scheme), encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(self, "Color Preferences", str(exc))

    def _load_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Color Preferences - Display", "", "Color Preference Scheme (*.cps)"
        )
        if not path:
            return
        try:
            self.scheme = parse_display_color_scheme(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Color Preferences", str(exc))
            return
        self.scheme_name.setText(self.scheme["name"])
        self.category.clear()
        self.category.addItems(self.scheme["categories"].keys())
        self._load_category(self.category.currentText())

    def _finish(self):
        if not self._capture_category():
            return
        self.result_scheme = normalized_display_color_scheme(self.scheme)
        self.result_colors = deepcopy(self.result_scheme["categories"].get("Setup", MODE_COLORS))
        self.accept()

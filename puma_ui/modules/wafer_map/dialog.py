from __future__ import annotations

from math import ceil
from typing import Optional

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
    QPushButton,
    QRadioButton,
    QRegion,
    QSpinBox,
    Qt,
    QVBoxLayout,
    QWidget,
)


WAFER_DIAMETER_UM = 300000.0


def die_grid_dimensions(pitch_width: float, pitch_height: float) -> tuple[int, int]:
    """Return a centered die grid large enough to cover a 300 mm wafer."""
    if pitch_width <= 0 or pitch_height <= 0:
        return 58, 58
    return (
        max(1, min(250, int(ceil(WAFER_DIAMETER_UM / pitch_width)))),
        max(1, min(250, int(ceil(WAFER_DIAMETER_UM / pitch_height)))),
    )


def centered_die_origin(columns: int, rows: int) -> tuple[int, int]:
    return max(0, columns // 2), max(0, rows // 2)


class WaferMapSetupDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None, state: Optional[dict] = None):
        super().__init__(parent)
        self.setWindowTitle("Wafermap View")
        self.resize(1160, 820)
        self.setMinimumSize(1000, 720)
        self.die_pattern_defined = False
        self.die_pitch_width = 0.0
        self.die_pitch_height = 0.0
        self.die_value_mode = "wafer_map"
        self.die_count = 0
        self.scribe_lines_defined = False
        self.scribe_x = 0.0
        self.scribe_y = 0.0
        self.invalid_die = set()
        self.origin_die = (28, 28)
        self.allow_partial_die = True
        self.die_corner_adjustment_required = False
        self.adjusted_die_corner = (28, 28)
        self.adjust_die_corner_mode = ""
        self.reticle_qualification = False
        self.reticle_width = 1
        self.reticle_height = 1
        self.reference_die = (29, 9)
        self.inner_die_rows = 1
        self.inner_die_columns = 1
        self.inner_die_defined = False
        self.klarf_die_basis = "Recipe Die"
        self.klarf_orientation = "As Inspected"
        self.changed = False
        self._initial_state = dict(state or {})
        self._build_ui()
        self._restore_state(self._initial_state)
        self._refresh_menu_states()
        self.changed = False

    def _build_ui(self):
        self.setStyleSheet(
            """
            QDialog {
                background: #e9e5d3;
                color: #111111;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10px;
            }
            QPushButton {
                background: #f2efe3;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-height: 26px;
                padding: 2px 8px;
            }
            QPushButton:disabled {
                color: #9a958a;
                background: #eeeada;
            }
            QFrame#leftRail, QFrame#rightPanel, QFrame#groupPanel {
                border: 1px solid #c7bea7;
                background: #e9e5d3;
            }
            QLabel[blueTitle="true"] {
                color: #0a55e5;
                background: #e9e5d3;
            }
            """
        )

        root = QHBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(10)
        root.addWidget(self._left_menu(), 0)
        self.wafer_canvas = WaferMapCanvas()
        root.addWidget(self.wafer_canvas, 1)
        root.addWidget(self._right_panel(), 0)

    def _left_menu(self) -> QFrame:
        rail = QFrame()
        rail.setObjectName("leftRail")
        rail.setFixedWidth(112)
        layout = QVBoxLayout(rail)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        menu_actions = [
            ("Die Values", self._open_die_values, True),
            ("Scribe Lines", self._open_scribe_lines, True),
            ("Define Inner\nDie", self._open_inner_die, True),
            ("Edit Map", self._open_edit_map, True),
            ("Reticle Size", self._open_reticle_size, True),
            ("Adjust Die\nCorner", self._open_adjust_die_corner, True),
            ("Registration\nSite", None, False),
        ]
        self.menu_buttons = {}
        for text, handler, enabled in menu_actions:
            button = QPushButton(text)
            button.setEnabled(enabled)
            button.setFixedHeight(38)
            if handler:
                button.clicked.connect(handler)
            layout.addWidget(button)
            self.menu_buttons[text.replace("\n", " ")] = button

        layout.addStretch(1)
        self.end_button = QPushButton("End")
        self.end_button.setFixedHeight(34)
        self.end_button.clicked.connect(self._finish_setup)
        layout.addWidget(self.end_button)
        return rail

    def _refresh_menu_states(self):
        if not hasattr(self, "menu_buttons"):
            return
        for name in ["Scribe Lines", "Define Inner Die", "Edit Map", "Reticle Size", "Adjust Die Corner"]:
            self.menu_buttons[name].setEnabled(self.die_pattern_defined)

    def _finish_setup(self):
        if self.die_corner_adjustment_required:
            adjust = QMessageBox.question(
                self,
                "Adjust Die Corner Required",
                "The inserted recipe components require die-corner reselection.\n"
                "Adjust the die corner now? Selecting No leaves the recipe unable to run.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if adjust == QMessageBox.Yes:
                self._open_adjust_die_corner()
                if self.die_corner_adjustment_required:
                    return
        if self.die_pattern_defined and not self.scribe_lines_defined:
            proceed = QMessageBox.warning(
                self,
                "Scribe Lines",
                "Scribe size is 0. Defining scribe lines is strongly recommended.\n"
                "Continue without defining scribe lines?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if proceed != QMessageBox.Yes:
                return
        self.accept()

    def _open_die_values(self):
        dialog = SpecifyDieValuesDialog(self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result != QDialog.Accepted:
            return

        if self.die_pattern_defined:
            result = QMessageBox.warning(
                self,
                "Puma 9xxx -- Msg 40020041H (1073872961)",
                "A die pattern is already defined for this inspection.\n"
                "Redefining the die pattern may reset reticle data and\n"
                "invalidate all tests in the inspection.  Continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if result != QMessageBox.Yes:
                self.setWindowTitle("Wafermap View - Existing die pattern retained")
                return

        if dialog.use_die_pitch.isChecked() and (dialog.x_pitch.value() < 1200.0 or dialog.y_pitch.value() < 1200.0):
            QMessageBox.warning(
                self,
                "Specify Die Values",
                "Die pitch value is out of range.\nThe minimum X and Y die pitch value is 1200 um.",
            )
            return

        mode = "die_pitch" if dialog.use_die_pitch.isChecked() else "wafer_map"
        pitch_width = dialog.x_pitch.value() if mode == "die_pitch" else 6977.094
        pitch_height = dialog.y_pitch.value() if mode == "die_pitch" else 10069.813
        sites = WaferMapSiteSelectionDialog(mode, pitch_width, pitch_height, self)
        site_result = sites.exec() if hasattr(sites, "exec") else sites.exec_()
        if site_result == QDialog.Accepted:
            self._apply_die_values(mode, pitch_width, pitch_height)
            if mode == "die_pitch":
                self.setWindowTitle("Wafermap View - Die pitch sites specified")
            else:
                self.setWindowTitle("Wafermap View - Wafer Map sites specified")
        else:
            self.setWindowTitle("Wafermap View - New die values discarded")

    def _open_scribe_lines(self):
        dialog = ScribeLinesSetupDialog(self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self._apply_scribe_lines(dialog.scribe_x, dialog.scribe_y)
            self.setWindowTitle("Wafermap View - Scribe Lines setup completed")

    def _open_edit_map(self):
        dialog = EditMapDialog(
            self,
            valid_die_count=self.die_count or 2714,
            invalid_die=self.invalid_die,
            origin_die=self.origin_die,
            allow_partial_die=self.allow_partial_die,
            pitch_width=self.die_pitch_width,
            pitch_height=self.die_pitch_height,
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self._apply_edit_map(
                dialog.valid_die_count,
                dialog.canvas.invalid_die,
                dialog.canvas.origin_die,
                dialog.allow_partial.isChecked(),
            )
            self.setWindowTitle("Wafermap View - Edit Map completed")

    def _open_reticle_size(self):
        max_reticle_width, max_reticle_height = die_grid_dimensions(
            self.die_pitch_width,
            self.die_pitch_height,
        )
        dialog = ReticleSizeDialog(
            self,
            reticle_qualification=self.reticle_qualification,
            reticle_width=self.reticle_width,
            reticle_height=self.reticle_height,
            reference_die=self.reference_die,
            invalid_die=self.invalid_die,
            origin_die=self.origin_die,
            max_width=max_reticle_width,
            max_height=max_reticle_height,
            pitch_width=self.die_pitch_width,
            pitch_height=self.die_pitch_height,
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self._apply_reticle_size(
                dialog.reticle_qualification.isChecked(),
                dialog.reticle_width.value(),
                dialog.reticle_height.value(),
                dialog.canvas.reference_die,
            )
            self.setWindowTitle("Wafermap View - Reticle Size completed")

    def _open_inner_die(self):
        dialog = SpecifyInnerDieValuesDialog(self.inner_die_rows, self.inner_die_columns, self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result != QDialog.Accepted:
            return
        self.inner_die_rows = dialog.rows.value()
        self.inner_die_columns = dialog.columns.value()
        self.inner_die_defined = True
        self.inner_die_label.setText(f"Inner Die: {self.inner_die_columns} columns x {self.inner_die_rows} rows")
        self.changed = True
        self.setWindowTitle("Wafermap View - Inner Die values specified")

    def _open_advanced(self):
        dialog = AdvancedDataOutputParametersDialog(
            self.klarf_die_basis,
            self.klarf_orientation,
            self,
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.klarf_die_basis = dialog.die_basis.currentText()
            self.klarf_orientation = dialog.orientation.currentText()
            self.changed = True
            self.setWindowTitle("Wafermap View - Advanced data output updated")

    def _open_adjust_die_corner(self):
        if self.die_corner_adjustment_required:
            result = QMessageBox.question(
                self,
                "Puma 9xxx -- Msg 80160101H (-2146041599)",
                "You need to adjust the die corner because the recipe components\n"
                "inserted may be incompatible. This can cause care areas to shift.\n"
                "Would you like to adjust die corner now?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
        else:
            result = QMessageBox.warning(
                self,
                "Puma 9xxx -- Msg 40020041H (1073872961)",
                "A die pattern is already defined for this inspection.\n"
                "Redefining the die pattern will invalidate all tests\n"
                "in the inspection.  Continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
        if result != QMessageBox.Yes:
            self.setWindowTitle("Wafermap View - Die corner adjustment skipped")
            return

        options = AdjustDieCornerOptionsDialog(self)
        option_result = options.exec() if hasattr(options, "exec") else options.exec_()
        if option_result != QDialog.Accepted:
            return
        mode = "shift" if options.shift_die_corner.isChecked() else "change"
        if mode == "change" and not self.scribe_lines_defined:
            QMessageBox.warning(
                self,
                "Adjust Die Corner",
                "Change Die Corner requires scribe lines to be defined.",
            )
            return

        dialog = AdjustDieCornerViewDialog(mode, self.adjusted_die_corner, self.invalid_die, self.origin_die, self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self._apply_adjust_die_corner(mode, dialog.canvas.marked_die)
            self.setWindowTitle("Wafermap View - Die Corner adjusted")

    def _right_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("rightPanel")
        panel.setFixedWidth(260)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        layout.addWidget(self._die_pitch_summary_group())
        layout.addWidget(self._reticle_size_group())
        self.number_die_label = QLabel("Number of Die on Wafer:          0")
        layout.addWidget(self.number_die_label)
        self.wafer_diameter_label = QLabel("Wafer Diameter:                 300  mm")
        layout.addWidget(self.wafer_diameter_label)
        advanced = QPushButton("Advanced...")
        advanced.clicked.connect(self._open_advanced)
        advanced.setFixedWidth(88)
        layout.addWidget(advanced, alignment=Qt.AlignRight)
        self.inner_die_label = QLabel("Inner Die: 1 column x 1 row")
        layout.addWidget(self.inner_die_label)
        layout.addStretch(1)
        layout.addWidget(self._legend_panel())
        return panel

    def _die_pitch_summary_group(self) -> QFrame:
        group = QFrame()
        group.setObjectName("groupPanel")
        group.setFixedHeight(68)
        label = QLabel("Die Pitch [um]")
        label.setProperty("blueTitle", True)
        label.setParent(group)
        label.move(8, -1)
        layout = QGridLayout(group)
        layout.setContentsMargins(10, 14, 10, 6)
        layout.setHorizontalSpacing(8)
        layout.addWidget(QLabel("Width:"), 0, 0)
        self.die_pitch_width_label = QLabel("")
        layout.addWidget(self.die_pitch_width_label, 0, 1)
        layout.addWidget(QLabel("Height:"), 1, 0)
        self.die_pitch_height_label = QLabel("")
        layout.addWidget(self.die_pitch_height_label, 1, 1)
        layout.setColumnStretch(1, 1)
        return group

    def _reticle_size_group(self) -> QFrame:
        group = QFrame()
        group.setObjectName("groupPanel")
        group.setFixedHeight(68)
        label = QLabel("Reticle Size")
        label.setProperty("blueTitle", True)
        label.setParent(group)
        label.move(8, -1)
        layout = QGridLayout(group)
        layout.setContentsMargins(10, 14, 10, 6)
        layout.addWidget(QLabel("Scribe X:"), 0, 0)
        self.scribe_x_label = QLabel("")
        layout.addWidget(self.scribe_x_label, 0, 1)
        layout.addWidget(QLabel("Scribe Y:"), 1, 0)
        self.scribe_y_label = QLabel("")
        layout.addWidget(self.scribe_y_label, 1, 1)
        return group

    def _apply_die_values(self, mode: str, pitch_width: float, pitch_height: float):
        self.changed = True
        self.die_pattern_defined = True
        self.die_value_mode = mode
        self.die_pitch_width = pitch_width
        self.die_pitch_height = pitch_height
        columns, rows = die_grid_dimensions(pitch_width, pitch_height)
        self.origin_die = centered_die_origin(columns, rows)
        self.reference_die = self.origin_die
        self.adjusted_die_corner = self.origin_die
        self.die_count = self._estimate_die_count(pitch_width, pitch_height)
        self.die_pitch_width_label.setText(f"{pitch_width:.3f}")
        self.die_pitch_height_label.setText(f"{pitch_height:.3f}")
        self.number_die_label.setText(f"Number of Die on Wafer:          {self.die_count}")
        self.wafer_diameter_label.setText("Wafer Diameter:                 300  mm")
        self.wafer_canvas.set_die_values(pitch_width, pitch_height, self.die_count, mode)
        self._refresh_menu_states()

    def _apply_scribe_lines(self, scribe_x: float, scribe_y: float):
        self.changed = True
        self.scribe_lines_defined = True
        self.scribe_x = scribe_x
        self.scribe_y = scribe_y
        self.scribe_x_label.setText(f"{scribe_x:.3f} um")
        self.scribe_y_label.setText(f"{scribe_y:.3f} um")
        self.wafer_canvas.set_scribe_lines(scribe_x, scribe_y)

    def _apply_edit_map(self, die_count: int, invalid_die, origin_die, allow_partial_die: bool):
        self.changed = True
        self.die_count = die_count
        self.invalid_die = set(invalid_die)
        self.origin_die = origin_die
        self.allow_partial_die = allow_partial_die
        self.number_die_label.setText(f"Number of Die on Wafer:          {self.die_count}")
        self.wafer_diameter_label.setText("Wafer Diameter:                 300  mm")
        self.wafer_canvas.set_edit_map_state(self.die_count, self.invalid_die, self.origin_die, self.allow_partial_die)

    def _apply_reticle_size(self, enabled: bool, width: int, height: int, reference_die):
        self.changed = True
        self.reticle_qualification = enabled
        self.reticle_width = width
        self.reticle_height = height
        self.reference_die = reference_die
        self.wafer_canvas.set_reticle_state(enabled, width, height, reference_die)

    def _apply_adjust_die_corner(self, mode: str, die_corner):
        self.changed = True
        self.adjust_die_corner_mode = mode
        self.adjusted_die_corner = die_corner
        self.die_corner_adjustment_required = False
        if mode == "shift":
            self.origin_die = die_corner
        self.wafer_canvas.set_adjust_die_corner_state(mode, die_corner)

    def _restore_state(self, state: dict):
        if not state:
            return
        self.die_pattern_defined = state.get("die_pattern_defined", self.die_pattern_defined)
        width = float(state.get("die_pitch_width", 0.0))
        height = float(state.get("die_pitch_height", 0.0))
        if width > 0 and height > 0:
            self._apply_die_values(state.get("die_value_mode", "wafer_map"), width, height)
        if state.get("scribe_lines_defined"):
            self._apply_scribe_lines(float(state.get("scribe_x", 0.0)), float(state.get("scribe_y", 0.0)))
        if any(key in state for key in ("die_count", "invalid_die", "origin_die", "allow_partial_die")):
            self._apply_edit_map(
                int(state.get("die_count", self.die_count)),
                {tuple(item) for item in state.get("invalid_die", [])},
                tuple(state.get("origin_die", self.origin_die)),
                bool(state.get("allow_partial_die", self.allow_partial_die)),
            )
        if any(key in state for key in ("reticle_qualification", "reticle_width", "reticle_height")):
            self._apply_reticle_size(
                bool(state.get("reticle_qualification", False)),
                int(state.get("reticle_width", 1)),
                int(state.get("reticle_height", 1)),
                tuple(state.get("reference_die", self.reference_die)),
            )
        self.inner_die_rows = int(state.get("inner_die_rows", 1))
        self.inner_die_columns = int(state.get("inner_die_columns", 1))
        self.inner_die_defined = bool(state.get("inner_die_defined", False))
        self.klarf_die_basis = state.get("klarf_die_basis", "Recipe Die")
        self.klarf_orientation = state.get("klarf_orientation", "As Inspected")
        self.die_corner_adjustment_required = bool(
            state.get("die_corner_adjustment_required", self.die_corner_adjustment_required)
        )
        self.adjust_die_corner_mode = state.get("adjust_die_corner_mode", "")
        self.adjusted_die_corner = tuple(
            state.get("adjusted_die_corner", self.adjusted_die_corner)
        )
        if self.adjust_die_corner_mode:
            self.wafer_canvas.set_adjust_die_corner_state(
                self.adjust_die_corner_mode,
                self.adjusted_die_corner,
            )
        self.inner_die_label.setText(
            f"Inner Die: {self.inner_die_columns} columns x {self.inner_die_rows} rows"
        )

    def result_state(self) -> dict:
        return {
            "die_pattern_defined": self.die_pattern_defined,
            "die_value_mode": self.die_value_mode,
            "die_pitch_width": self.die_pitch_width,
            "die_pitch_height": self.die_pitch_height,
            "die_count": self.die_count,
            "scribe_lines_defined": self.scribe_lines_defined,
            "scribe_x": self.scribe_x,
            "scribe_y": self.scribe_y,
            "invalid_die": [list(item) for item in sorted(self.invalid_die)],
            "origin_die": list(self.origin_die),
            "allow_partial_die": self.allow_partial_die,
            "reticle_qualification": self.reticle_qualification,
            "reticle_width": self.reticle_width,
            "reticle_height": self.reticle_height,
            "reference_die": list(self.reference_die),
            "inner_die_rows": self.inner_die_rows,
            "inner_die_columns": self.inner_die_columns,
            "inner_die_defined": self.inner_die_defined,
            "klarf_die_basis": self.klarf_die_basis,
            "klarf_orientation": self.klarf_orientation,
            "die_corner_adjustment_required": self.die_corner_adjustment_required,
            "adjust_die_corner_mode": self.adjust_die_corner_mode,
            "adjusted_die_corner": list(self.adjusted_die_corner),
        }

    @staticmethod
    def _estimate_die_count(pitch_width: float, pitch_height: float) -> int:
        radius = 150000.0
        count = 0
        columns, rows = die_grid_dimensions(pitch_width, pitch_height)
        for col in range(columns):
            for row in range(rows):
                left = (col - columns / 2) * pitch_width
                top = (row - rows / 2) * pitch_height
                right = left + pitch_width
                bottom = top + pitch_height
                nearest_x = max(left, min(0.0, right))
                nearest_y = max(top, min(0.0, bottom))
                if nearest_x * nearest_x + nearest_y * nearest_y <= radius * radius:
                    count += 1
        return count

    def _empty_group(self, title: str) -> QFrame:
        group = QFrame()
        group.setObjectName("groupPanel")
        group.setFixedHeight(52)
        label = QLabel(title)
        label.setProperty("blueTitle", True)
        label.setParent(group)
        label.move(8, -1)
        return group

    def _legend_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        header = QLabel("Legend")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        grid = QGridLayout()
        grid.setHorizontalSpacing(4)
        grid.setVerticalSpacing(3)
        items = [
            ("#ffffff", "Valid Die"),
            ("#f2d0d0", "Origin Die"),
            ("#3e8d9c", "Reticle"),
            ("#d9b0b0", "Reference die for reticles"),
            ("#c8c8c8", "Invalid Die"),
        ]
        for index, (color, text) in enumerate(items):
            marker = QLabel("")
            marker.setFixedSize(13, 13)
            marker.setStyleSheet(f"background: {color}; border: 1px solid #555555;")
            row = index // 2
            column = (index % 2) * 2
            grid.addWidget(marker, row, column)
            item_label = QLabel(text)
            item_label.setStyleSheet("font-size: 8px;")
            item_label.setWordWrap(True)
            grid.addWidget(item_label, row, column + 1)
        layout.addLayout(grid)
        return panel


class SpecifyInnerDieValuesDialog(QDialog):
    def __init__(self, rows: int = 1, columns: int = 1, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Specify Inner Die Values")
        self.setFixedSize(360, 220)
        self.setStyleSheet(
            "QDialog { background: #efede2; font-family: Arial; font-size: 10px; }"
            "QSpinBox { background: white; min-height: 24px; }"
            "QPushButton { min-width: 78px; min-height: 24px; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 26, 30, 20)
        layout.addWidget(QLabel("Specify the number of equal inner die within each recipe die."))
        form = QGridLayout()
        self.rows = QSpinBox()
        self.rows.setRange(1, 100)
        self.rows.setValue(rows)
        self.columns = QSpinBox()
        self.columns.setRange(1, 100)
        self.columns.setValue(columns)
        form.addWidget(QLabel("Rows:"), 0, 0, alignment=Qt.AlignRight)
        form.addWidget(self.rows, 0, 1)
        form.addWidget(QLabel("Columns:"), 1, 0, alignment=Qt.AlignRight)
        form.addWidget(self.columns, 1, 1)
        layout.addLayout(form)
        layout.addStretch(1)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        ok = QPushButton("OK")
        ok.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        buttons.addStretch(1)
        layout.addLayout(buttons)


class AdvancedDataOutputParametersDialog(QDialog):
    def __init__(self, die_basis: str, orientation: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Advanced Data Output Parameters")
        self.setFixedSize(470, 280)
        self.setStyleSheet(
            "QDialog { background: #efede2; font-family: Arial; font-size: 10px; }"
            "QComboBox { background: white; min-height: 24px; }"
            "QPushButton { min-width: 82px; min-height: 24px; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 20)
        title = QLabel("KLARF Data Output")
        title.setStyleSheet("font-weight: 700;")
        layout.addWidget(title)
        form = QGridLayout()
        self.die_basis = QComboBox()
        self.die_basis.addItems(["Recipe Die", "Inner Die"])
        self.die_basis.setCurrentText(die_basis)
        self.orientation = QComboBox()
        self.orientation.addItems(["As Inspected", "Up (0 deg.)", "Right (90 deg.)", "Down (180 deg.)", "Left (270 deg.)"])
        self.orientation.setCurrentText(orientation)
        form.addWidget(QLabel("Report defects using:"), 0, 0, alignment=Qt.AlignRight)
        form.addWidget(self.die_basis, 0, 1)
        form.addWidget(QLabel("Transfer KLARF data with orientation:"), 1, 0, alignment=Qt.AlignRight)
        form.addWidget(self.orientation, 1, 1)
        layout.addLayout(form)
        note = QLabel("Select Inner Die to report KLARF die coordinates using the defined inner-die grid.")
        note.setWordWrap(True)
        layout.addWidget(note)
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


class SpecifyDieValuesDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Specify Die Values")
        self.setFixedSize(520, 310)
        self._build_ui()
        self._update_die_pitch_enabled()

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
                background: #f2efe3;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-height: 26px;
                padding: 2px 18px;
            }
            QDoubleSpinBox {
                background: #ffffff;
                border: 1px solid #7f9db9;
                min-height: 24px;
            }
            QDoubleSpinBox:disabled {
                color: #a49d90;
                background: #e2dece;
            }
            """
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(70, 34, 24, 24)
        root.setSpacing(14)

        self.use_wafer_map = QRadioButton("Use Wafer Map")
        self.use_wafer_map.setChecked(True)
        self.use_wafer_map.toggled.connect(self._update_die_pitch_enabled)
        root.addWidget(self.use_wafer_map)

        self.use_die_pitch = QRadioButton("Use Die Pitch")
        self.use_die_pitch.toggled.connect(self._update_die_pitch_enabled)
        root.addWidget(self.use_die_pitch)

        pitch_grid = QGridLayout()
        pitch_grid.setHorizontalSpacing(8)
        pitch_grid.setVerticalSpacing(10)
        pitch_grid.addWidget(QLabel("X:"), 0, 0, alignment=Qt.AlignRight)
        self.x_pitch = self._pitch_field()
        pitch_grid.addWidget(self.x_pitch, 0, 1)
        pitch_grid.addWidget(QLabel("Y:"), 1, 0, alignment=Qt.AlignRight)
        self.y_pitch = self._pitch_field()
        pitch_grid.addWidget(self.y_pitch, 1, 1)
        root.addLayout(pitch_grid)
        root.addStretch(1)

        footer = QHBoxLayout()
        footer.addStretch(1)
        ok = QPushButton("OK")
        ok.setFixedWidth(110)
        ok.clicked.connect(self.accept)
        footer.addWidget(ok)
        footer.addSpacing(24)
        cancel = QPushButton("Cancel")
        cancel.setFixedWidth(110)
        cancel.clicked.connect(self.reject)
        footer.addWidget(cancel)
        root.addLayout(footer)

    @staticmethod
    def _pitch_field() -> QDoubleSpinBox:
        field = QDoubleSpinBox()
        field.setRange(0.001, 100000.0)
        field.setDecimals(3)
        field.setValue(1200.000)
        field.setSuffix(" um")
        field.setFixedWidth(126)
        return field

    def _update_die_pitch_enabled(self):
        enabled = hasattr(self, "use_die_pitch") and self.use_die_pitch.isChecked()
        if hasattr(self, "x_pitch"):
            self.x_pitch.setEnabled(enabled)
            self.y_pitch.setEnabled(enabled)


class WaferMapSiteSelectionDialog(QDialog):
    LOW_MAG_POINTS = [
        (-71453.063, 66000.750),
        (-64475.969, 55930.938),
        (64200.125, -65440.000),
    ]
    HIGH_MAG_POINTS = [
        (-71453.006, 66000.702),
        (-64475.910, 55930.880),
        (64200.080, -65439.940),
    ]

    def __init__(
        self,
        mode: str = "wafer_map",
        pitch_width: float = 6977.094,
        pitch_height: float = 10069.813,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Specify Die Values - Select Wafer Map Sites")
        self.resize(1120, 880)
        self.setMinimumSize(1000, 760)
        self.mode = mode
        self.pitch_width = pitch_width
        self.pitch_height = pitch_height
        self.low_mag_required = 1 if mode == "die_pitch" else 3
        self.high_mag_required = 3
        self.mark_count = 0
        self._build_ui()
        self._refresh_state()

    def _build_ui(self):
        self.setStyleSheet(
            """
            QDialog {
                background: #e9e5d3;
                color: #111111;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10px;
            }
            QPushButton {
                background: #f2efe3;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-height: 24px;
                padding: 2px 12px;
            }
            QPushButton:disabled {
                color: #9a958a;
                background: #eeeada;
            }
            QFrame#groupPanel, QFrame#instructionPanel {
                border: 1px solid #c7bea7;
                background: #e9e5d3;
            }
            QLabel[blueTitle="true"] {
                color: #0a55e5;
                background: #e9e5d3;
            }
            """
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(6)

        body = QHBoxLayout()
        body.setSpacing(8)
        self.canvas = WaferMapSiteCanvas()
        self.canvas.low_mag_required = self.low_mag_required
        self.canvas.pitch_width = self.pitch_width
        self.canvas.pitch_height = self.pitch_height
        body.addWidget(self.canvas, 1)
        body.addWidget(self._right_panel(), 0)
        root.addLayout(body, 1)
        root.addWidget(self._instruction_panel())
        root.addLayout(self._footer())

    def _right_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("groupPanel")
        panel.setFixedWidth(255)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        layout.addWidget(self._die_pitch_panel())
        layout.addWidget(self._site_panel("Low Mag Sites [um]", "low"))
        layout.addWidget(self._site_panel("High Mag Sites [um]", "high"))
        layout.addWidget(self._empty_group("Die Corner Offset [um]"))
        layout.addStretch(1)
        layout.addWidget(self._legend_panel())
        layout.addWidget(self._detailed_instructions_panel())
        return panel

    def _die_pitch_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("groupPanel")
        panel.setFixedHeight(54)
        title = QLabel("Die Pitch [um]")
        title.setProperty("blueTitle", True)
        title.setParent(panel)
        title.move(8, -1)
        layout = QGridLayout(panel)
        layout.setContentsMargins(12, 14, 12, 8)
        layout.addWidget(QLabel("Width:"), 0, 0)
        layout.addWidget(QLabel(f"{self.pitch_width:.3f}"), 0, 1)
        layout.addWidget(QLabel("Height:"), 0, 2)
        layout.addWidget(QLabel(f"{self.pitch_height:.3f}"), 0, 3)
        return panel

    def _site_panel(self, title: str, prefix: str) -> QFrame:
        panel = QFrame()
        panel.setObjectName("groupPanel")
        panel.setFixedHeight(92)
        title_label = QLabel(title)
        title_label.setProperty("blueTitle", True)
        title_label.setParent(panel)
        title_label.move(8, -1)
        layout = QGridLayout(panel)
        layout.setContentsMargins(12, 14, 12, 8)
        labels = []
        for index in range(3):
            row = index
            layout.addWidget(QLabel(f"Site {index + 1}:"), row, 0)
            x_label = QLabel("")
            y_label = QLabel("")
            layout.addWidget(QLabel("X:"), row, 1)
            layout.addWidget(x_label, row, 2)
            layout.addWidget(QLabel("Y:"), row, 3)
            layout.addWidget(y_label, row, 4)
            labels.append((x_label, y_label))
        if prefix == "low":
            self.low_site_labels = labels
        else:
            self.high_site_labels = labels
        return panel

    def _empty_group(self, title: str) -> QFrame:
        panel = QFrame()
        panel.setObjectName("groupPanel")
        panel.setFixedHeight(44)
        title_label = QLabel(title)
        title_label.setProperty("blueTitle", True)
        title_label.setParent(panel)
        title_label.move(8, -1)
        return panel

    def _legend_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        header = QLabel("Legend")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        grid = QGridLayout()
        grid.setHorizontalSpacing(3)
        grid.setVerticalSpacing(2)
        items = [
            ("#ff6666", "Stage Mark"),
            ("#4c58ff", "Marked Site"),
            ("#31c96b", "Actual Die Corner"),
            ("#333333", "Die Definition Grid"),
        ]
        for index, (color, text) in enumerate(items):
            marker = QLabel("")
            marker.setFixedSize(11, 11)
            marker.setStyleSheet(f"background: {color}; border: 1px solid #555555;")
            row = index // 2
            column = (index % 2) * 2
            grid.addWidget(marker, row, column)
            grid.addWidget(QLabel(text), row, column + 1)
        layout.addLayout(grid)
        return panel

    def _detailed_instructions_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("instructionPanel")
        panel.setFixedHeight(140)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 4, 8, 8)
        title = QLabel("Detailed Instructions")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        self.detailed_instructions = QLabel("")
        self.detailed_instructions.setWordWrap(True)
        self.detailed_instructions.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        layout.addWidget(self.detailed_instructions, 1)
        return panel

    def _instruction_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("instructionPanel")
        panel.setFixedHeight(28)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 4, 4, 4)
        self.step_instruction = QLabel("")
        self.step_instruction.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.step_instruction)
        return panel

    def _footer(self) -> QHBoxLayout:
        footer = QHBoxLayout()
        footer.setSpacing(10)
        back = QPushButton("<< Back")
        back.setFixedWidth(80)
        back.clicked.connect(self._go_back)
        self.back_button = back
        self.mark_button = QPushButton("Mark Site >>")
        self.mark_button.setFixedWidth(95)
        self.mark_button.clicked.connect(self._mark_site)
        self.next_button = QPushButton("Next >>")
        self.next_button.setFixedWidth(80)
        self.next_button.clicked.connect(self._next_step)
        self.finish_button = QPushButton("Finish")
        self.finish_button.setFixedWidth(80)
        self.finish_button.clicked.connect(self._finish_selection)
        cancel = QPushButton("Cancel")
        cancel.setFixedWidth(80)
        cancel.clicked.connect(self._cancel_selection)
        footer.addWidget(back)
        footer.addWidget(self.mark_button)
        footer.addStretch(1)
        footer.addWidget(self.next_button)
        footer.addStretch(1)
        footer.addWidget(self.finish_button)
        footer.addStretch(1)
        footer.addWidget(cancel)
        return footer

    def _mark_site(self):
        if self.mark_count >= self._total_required_sites():
            return
        self.mark_count += 1
        self.canvas.mark_count = self.mark_count
        if self.mark_count <= self.low_mag_required:
            point = self.LOW_MAG_POINTS[self.mark_count - 1]
            labels = self.low_site_labels[self.mark_count - 1]
        else:
            high_index = self.mark_count - self.low_mag_required - 1
            point = self.HIGH_MAG_POINTS[high_index]
            labels = self.high_site_labels[high_index]
        labels[0].setText(f"{point[0]:.3f}")
        labels[1].setText(f"{point[1]:.3f}")
        self.canvas.update()
        self._refresh_state()

    def _go_back(self):
        if self.mark_count <= 0:
            return
        self.mark_count -= 1
        self.canvas.mark_count = self.mark_count
        self._clear_site_labels_after(self.mark_count)
        self.canvas.update()
        self._refresh_state()

    def _next_step(self):
        if self.mark_count >= self._total_required_sites():
            self._finish_selection()
        elif self.mark_count >= self.low_mag_required:
            self.step_instruction.setText("High magnification reselection is active. Mark the three high mag sites.")

    def _finish_selection(self):
        self.setWindowTitle("Specify Die Values - Sites saved")
        self.accept()

    def _cancel_selection(self):
        result = QMessageBox.warning(
            self,
            "Puma 9xxx -- Msg 4002003BH (1073872955)",
            "Discard new die values?",
            QMessageBox.Ok | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if result == QMessageBox.Ok:
            self.reject()

    def _clear_site_labels_after(self, mark_count: int):
        for index, labels in enumerate(self.low_site_labels, start=1):
            if index > mark_count or index > self.low_mag_required:
                labels[0].setText("")
                labels[1].setText("")
        for high_index, labels in enumerate(self.high_site_labels, start=1):
            absolute_index = self.low_mag_required + high_index
            if absolute_index > mark_count:
                labels[0].setText("")
                labels[1].setText("")

    def _refresh_state(self):
        self.back_button.setEnabled(self.mark_count > 0)
        self.next_button.setEnabled(self.mark_count >= self.low_mag_required)
        self.finish_button.setEnabled(self.mark_count >= self._total_required_sites())
        if self.mark_count < self.low_mag_required:
            target = self.mark_count + 1
            self.step_instruction.setText(f"Select the {self._ordinal(target)} low mag site.")
            if self.mode == "die_pitch":
                self.detailed_instructions.setText(
                    "Use Die Pitch mode: after the first low-mag site is selected, the computer draws a partial die grid. "
                    "Only this first low-mag site and three high-mag sites are required."
                )
            else:
                if self.mark_count == 0:
                    self.detailed_instructions.setText(
                        "Use the joystick or stage movement controls to move to the upper-left portion of the wafer. "
                        "Position the crosshair on the upper-left corner of a die, then click Mark Site."
                    )
                else:
                    self.detailed_instructions.setText(
                        "Move to the die immediately below and to the right of the previously selected die. "
                        "Position the crosshair on the identical upper-left die corner, then click Mark Site."
                    )
        elif self.mark_count == self.low_mag_required:
            self.step_instruction.setText(
                "The first low-mag site is restored and high magnification is active. Select the first high mag site."
            )
            if self.mode == "wafer_map":
                self.detailed_instructions.setText(
                    "After two die corners are defined the system calculates die size and draws a partial die grid. "
                    "After the third low-mag site is selected, the crosshair returns to the first low-mag site and zooms to high magnification."
                )
            else:
                self.detailed_instructions.setText(
                    "After the first low-mag site is selected, a partial die grid is drawn and high magnification is active. "
                    "Repeat the site selection at high magnification."
                )
        elif self.mark_count < self._total_required_sites():
            target = self.mark_count - self.low_mag_required + 1
            self.step_instruction.setText(f"Select the {self._ordinal(target)} high mag site.")
            self.detailed_instructions.setText(
                "Place the crosshair at the exact geometry that defines the upper-left corner of the die and click Mark Site."
            )
        else:
            self.step_instruction.setText("All three high mag sites are selected. Click Finish.")
            self.detailed_instructions.setText("Wafer map site selection is complete.")

    def _total_required_sites(self) -> int:
        return self.low_mag_required + self.high_mag_required

    @staticmethod
    def _ordinal(value: int) -> str:
        return {1: "first", 2: "second", 3: "third"}.get(value, str(value))


class WaferMapSiteCanvas(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.mark_count = 0
        self.low_mag_required = 3
        self.pitch_width = 6977.094
        self.pitch_height = 10069.813
        self.setMinimumSize(740, 720)

    def layout_geometry(self):
        rect = self.rect().adjusted(32, 20, -32, -28)
        side = min(rect.width(), rect.height())
        cx = rect.center().x()
        cy = rect.center().y()
        wafer_x = cx - side // 2
        wafer_y = cy - side // 2
        radius = side / 2.0

        pitch_ratio = self.pitch_height / max(self.pitch_width, 1.0)
        pitch_ratio = max(0.45, min(2.2, pitch_ratio))
        cell_width = max(12.0, side / 28.0)
        cell_height = max(12.0, cell_width * pitch_ratio)

        x_lines = []
        offset = 0
        while cx + offset * cell_width <= wafer_x + side:
            x_lines.append(cx + offset * cell_width)
            if offset:
                x_lines.append(cx - offset * cell_width)
            offset += 1
        y_lines = []
        offset = 0
        while cy + offset * cell_height <= wafer_y + side:
            y_lines.append(cy + offset * cell_height)
            if offset:
                y_lines.append(cy - offset * cell_height)
            offset += 1

        usable_radius = radius - max(cell_width, cell_height) * 0.75
        diagonal_step = 1
        while (
            ((diagonal_step + 1) * cell_width) ** 2
            + ((diagonal_step + 1) * cell_height) ** 2
            <= usable_radius ** 2
        ):
            diagonal_step += 1
        first_step = max(2, diagonal_step // 2)
        selection_points = [
            (cx - first_step * cell_width, cy - first_step * cell_height),
            (cx - (first_step - 1) * cell_width, cy - (first_step - 1) * cell_height),
            (cx + diagonal_step * cell_width, cy + diagonal_step * cell_height),
        ]
        return {
            "wafer": (wafer_x, wafer_y, side, side),
            "center": (cx, cy),
            "radius": radius,
            "cell": (cell_width, cell_height),
            "x_lines": sorted(x_lines),
            "y_lines": sorted(y_lines),
            "selection_points": selection_points,
        }

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#858583"))

        geometry = self.layout_geometry()
        wafer_x, wafer_y, side, _ = geometry["wafer"]
        cx, cy = geometry["center"]
        painter.setBrush(QColor("#ffffff"))
        painter.setPen(QPen(QColor("#555555"), 1))
        painter.drawEllipse(wafer_x, wafer_y, side, side)

        painter.save()
        painter.setClipRegion(QRegion(wafer_x, wafer_y, side, side, QRegion.Ellipse))
        self._draw_grid(painter, geometry)
        painter.restore()

        notch_width = max(10, side // 42)
        painter.setBrush(QColor("#858583"))
        painter.setPen(QPen(QColor("#858583"), 1))
        painter.drawRect(cx - notch_width // 2, wafer_y + side - 4, notch_width, 8)

        self._draw_selection_sites(painter, geometry)
        self._draw_crosshair(painter, geometry)

    def _draw_grid(self, painter: QPainter, geometry):
        wafer_x, wafer_y, side, _ = geometry["wafer"]
        painter.setPen(QPen(QColor("#333333"), 1, Qt.DotLine))
        for px in geometry["x_lines"]:
            painter.drawLine(int(px), wafer_y, int(px), wafer_y + side)
        for py in geometry["y_lines"]:
            painter.drawLine(wafer_x, int(py), wafer_x + side, int(py))

    def _draw_selection_sites(self, painter: QPainter, geometry):
        wafer_x, wafer_y, side, _ = geometry["wafer"]
        points = geometry["selection_points"]
        label_origin = (wafer_x + int(side * 0.17), wafer_y + int(side * 0.43))
        painter.setPen(QPen(QColor("#111111"), 1))
        painter.drawText(label_origin[0] - 8, label_origin[1], "Selection")
        painter.drawText(label_origin[0] + 2, label_origin[1] + 16, "Sites")
        completed = min(self.mark_count, self.low_mag_required)
        for index, (px, py) in enumerate(points, start=1):
            if index > self.low_mag_required:
                continue
            is_visible = index <= completed or index == completed + 1
            if not is_visible:
                continue
            line_color = QColor("#ff0000") if index <= completed else QColor("#d78585")
            painter.setPen(QPen(line_color, 3 if index <= completed else 1, Qt.SolidLine))
            painter.drawLine(label_origin[0] + 46, label_origin[1] - 4, int(px), int(py))
            painter.setPen(QPen(line_color, 2))
            painter.drawLine(int(px - 7), int(py), int(px + 7), int(py))
            painter.drawLine(int(px), int(py - 7), int(px), int(py + 7))
            painter.setPen(QPen(QColor("#0000aa"), 1))
            painter.drawText(int(px - 6), int(py - 9), str(index))

    def _draw_crosshair(self, painter: QPainter, geometry):
        points = geometry["selection_points"]
        if self.mark_count < self.low_mag_required:
            px, py = points[self.mark_count]
        else:
            high_index = (self.mark_count - self.low_mag_required) % 3
            px, py = points[high_index]
        painter.setPen(QPen(QColor("#ff5050"), 1))
        painter.drawLine(int(px - 10), int(py), int(px + 10), int(py))
        painter.drawLine(int(px), int(py - 10), int(px), int(py + 10))
        painter.setPen(QPen(QColor("#30c95b"), 1))
        painter.drawLine(int(px - 4), int(py + 8), int(px + 10), int(py + 8))
        painter.drawLine(int(px + 3), int(py + 1), int(px + 3), int(py + 15))


class ScribeLinesSetupDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Scribe Lines")
        self.resize(780, 650)
        self.setMinimumSize(720, 600)
        self.mark_count = 0
        self.scribe_x = 0.0
        self.scribe_y = 0.0
        self._build_ui()
        self._refresh_state()

    def _build_ui(self):
        self.setStyleSheet(
            """
            QDialog {
                background: #e9e5d3;
                color: #111111;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10px;
            }
            QPushButton {
                background: #f2efe3;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-height: 24px;
                padding: 2px 12px;
            }
            QPushButton:disabled {
                color: #9a958a;
                background: #eeeada;
            }
            QFrame#instructionPanel {
                border: 1px solid #c7bea7;
                background: #e9e5d3;
            }
            """
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(6)
        self.canvas = ScribeLinesCanvas()
        root.addWidget(self.canvas, 1)
        root.addWidget(self._instruction_panel())
        root.addLayout(self._footer())

    def _instruction_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("instructionPanel")
        panel.setFixedHeight(48)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(6, 4, 6, 4)
        self.message = QLabel("")
        self.message.setWordWrap(True)
        self.message.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.message)
        return panel

    def _footer(self) -> QHBoxLayout:
        footer = QHBoxLayout()
        footer.setSpacing(10)
        self.back_button = QPushButton("<< Back")
        self.back_button.setFixedWidth(84)
        self.back_button.clicked.connect(self._back)
        self.mark_button = QPushButton("Mark Site >>")
        self.mark_button.setFixedWidth(100)
        self.mark_button.clicked.connect(self._mark_site)
        self.finish_button = QPushButton("Finish")
        self.finish_button.setFixedWidth(84)
        self.finish_button.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.setFixedWidth(84)
        cancel.clicked.connect(self.reject)
        footer.addWidget(self.back_button)
        footer.addWidget(self.mark_button)
        footer.addStretch(1)
        footer.addWidget(self.finish_button)
        footer.addWidget(cancel)
        return footer

    def _mark_site(self):
        if self.mark_count >= 2:
            return
        self.mark_count += 1
        self.canvas.mark_count = self.mark_count
        if self.mark_count == 2:
            self.scribe_x = 120.000
            self.scribe_y = 120.000
        self.canvas.update()
        self._refresh_state()

    def _back(self):
        if self.mark_count <= 0:
            return
        self.mark_count -= 1
        self.canvas.mark_count = self.mark_count
        self.canvas.update()
        self._refresh_state()

    def _finish(self):
        if self.mark_count < 2:
            QMessageBox.warning(self, "Scribe Lines", "Mark both scribe line sites before clicking Finish.")
            return
        self.accept()

    def _refresh_state(self):
        self.back_button.setEnabled(self.mark_count > 0)
        self.finish_button.setEnabled(self.mark_count >= 2)
        self.mark_button.setEnabled(self.mark_count < 2)
        if self.mark_count == 0:
            self.message.setText(
                "Select the first site. Position the crosshair over the upper-left corner of the bottom right die, then click Mark Site."
            )
        elif self.mark_count == 1:
            self.message.setText(
                "Select the second site. Position the crosshair over the lower-right corner of the upper-left die, then click Mark Site."
            )
        else:
            self.message.setText("Scribe Lines setup Completed. Click Back to redefine a selected site or Finish to return.")


class ScribeLinesCanvas(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.mark_count = 0
        self.setMinimumSize(620, 500)

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#f4f4f0"))
        rect = self.rect().adjusted(36, 28, -36, -28)
        side = min(rect.width(), rect.height())
        x = rect.center().x() - side // 2
        y = rect.center().y() - side // 2
        painter.fillRect(x, y, side, side, QColor("#ffffff"))
        painter.setPen(QPen(QColor("#555555"), 1))
        painter.drawRect(x, y, side, side)

        street = int(side * 0.25)
        center_x = x + side // 2
        center_y = y + side // 2
        self._draw_die(painter, x, y, center_x - x - street // 2, center_y - y - street // 2)
        self._draw_die(painter, center_x + street // 2, y, x + side - center_x - street // 2, center_y - y - street // 2)
        self._draw_die(painter, x, center_y + street // 2, center_x - x - street // 2, y + side - center_y - street // 2)
        self._draw_die(
            painter,
            center_x + street // 2,
            center_y + street // 2,
            x + side - center_x - street // 2,
            y + side - center_y - street // 2,
        )

        first_site = (center_x + street // 2 - 8, center_y + street // 2 + 4)
        second_site = (center_x - street // 2 + 8, center_y - street // 2 - 4)
        self._draw_crosshair(painter, first_site, "1st scribe site", self.mark_count >= 1, label_side=1)
        self._draw_crosshair(painter, second_site, "2nd scribe site", self.mark_count >= 2, label_side=-1)

    @staticmethod
    def _draw_die(painter: QPainter, x: int, y: int, width: int, height: int):
        painter.setBrush(QColor("#bfbfbf"))
        painter.setPen(QPen(QColor("#000000"), 5))
        painter.drawRect(x, y, width, height)
        label_w = 48
        label_h = 30
        painter.setBrush(QColor("#ffffff"))
        painter.setPen(QPen(QColor("#000000"), 2))
        painter.drawRect(x + width // 2 - label_w // 2, y + height // 2 - label_h // 2, label_w, label_h)
        painter.drawText(x + width // 2 - 12, y + height // 2 + 4, "Die")

    def _draw_crosshair(self, painter: QPainter, point, label: str, marked: bool, label_side: int):
        px, py = point
        painter.setPen(QPen(QColor("#ff0000"), 8))
        painter.drawLine(px - 30, py, px + 30, py)
        painter.drawLine(px, py - 30, px, py + 30)
        if marked:
            painter.setPen(QPen(QColor("#0044cc"), 2))
            painter.drawEllipse(px - 14, py - 14, 28, 28)
        label_x = px + (70 if label_side > 0 else -160)
        label_y = py - 25
        painter.setPen(QPen(QColor("#111111"), 1))
        painter.drawText(label_x, label_y, label)
        painter.drawLine(label_x + (5 if label_side < 0 else -8), label_y + 8, px, py)


class EditMapDialog(QDialog):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        valid_die_count: int = 2714,
        invalid_die=None,
        origin_die=(28, 28),
        allow_partial_die: bool = True,
        pitch_width: float = 0.0,
        pitch_height: float = 0.0,
    ):
        super().__init__(parent)
        self.setWindowTitle("Edit Map")
        self.resize(1120, 870)
        self.setMinimumSize(1000, 760)
        self.valid_die_count = valid_die_count
        self.initial_invalid_die = set(invalid_die or set())
        self.initial_origin_die = origin_die
        self.initial_allow_partial_die = allow_partial_die
        self.pitch_width = float(pitch_width)
        self.pitch_height = float(pitch_height)
        self._history = []
        self._redo_history = []
        self._build_ui()
        self._update_edge_controls()

    def _build_ui(self):
        self.setStyleSheet(
            """
            QDialog {
                background: #e9e5d3;
                color: #111111;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10px;
            }
            QPushButton {
                background: #f2efe3;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-height: 24px;
                padding: 2px 10px;
            }
            QPushButton:disabled, QSpinBox:disabled {
                color: #9a958a;
                background: #eeeada;
            }
            QFrame#rightPanel, QFrame#groupPanel, QFrame#instructionPanel {
                border: 1px solid #c7bea7;
                background: #e9e5d3;
            }
            QLabel[blueTitle="true"] {
                color: #0a55e5;
                background: #e9e5d3;
            }
            """
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(6)
        body = QHBoxLayout()
        body.setSpacing(8)
        self.canvas = EditMapCanvas(
            self,
            self.initial_invalid_die,
            self.initial_origin_die,
            allow_partial_die=self.initial_allow_partial_die,
            pitch_width=self.pitch_width,
            pitch_height=self.pitch_height,
        )
        body.addWidget(self.canvas, 1)
        body.addWidget(self._right_panel(), 0)
        root.addLayout(body, 1)
        root.addLayout(self._footer())
        root.addWidget(self._instructions())

    def _right_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("rightPanel")
        panel.setFixedWidth(215)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)
        layout.addWidget(self._selection_mode_panel())
        layout.addWidget(self._distance_panel())
        remove = QPushButton("Remove Outside Die")
        remove.clicked.connect(self._remove_outside_die)
        layout.addWidget(remove)
        add = QPushButton("Add Inside Die")
        add.clicked.connect(self._add_inside_die)
        layout.addWidget(add)
        layout.addSpacing(18)
        self.allow_partial = QCheckBox("Allow Partial Die")
        self.allow_partial.setChecked(self.initial_allow_partial_die)
        self.allow_partial.toggled.connect(self._set_allow_partial_die)
        layout.addWidget(self.allow_partial)
        layout.addStretch(1)
        layout.addWidget(self._legend_panel())
        return panel

    def _selection_mode_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("groupPanel")
        title = QLabel("Selection Mode")
        title.setProperty("blueTitle", True)
        title.setParent(panel)
        title.move(8, -1)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 14, 8, 8)
        self.toggle_mode = QRadioButton("Toggle")
        self.toggle_mode.setChecked(True)
        self.add_mode = QRadioButton("Add (Set to Valid)")
        self.remove_mode = QRadioButton("Remove (Set to Invalid)")
        self.origin_mode = QRadioButton("Set Origin Die")
        for radio in [self.toggle_mode, self.add_mode, self.remove_mode, self.origin_mode]:
            layout.addWidget(radio)
        select_stage = QPushButton("Select Die at Stage Position")
        select_stage.clicked.connect(self._select_die_at_stage_position)
        layout.addWidget(select_stage)
        return panel

    def _distance_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("groupPanel")
        title = QLabel("Distance from wafer edge")
        title.setProperty("blueTitle", True)
        title.setParent(panel)
        title.move(8, -1)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 14, 8, 8)
        self.edge_enabled = QCheckBox("")
        self.edge_enabled.toggled.connect(self._update_edge_controls)
        layout.addWidget(self.edge_enabled)
        self.edge_microns = QRadioButton("In microns")
        self.edge_microns.setChecked(True)
        layout.addWidget(self.edge_microns)
        self.edge_micron_value = QSpinBox()
        self.edge_micron_value.setRange(0, 100000)
        self.edge_micron_value.setValue(3000)
        layout.addWidget(self.edge_micron_value)
        self.edge_percent = QRadioButton("As % of radius")
        layout.addWidget(self.edge_percent)
        self.edge_percent_value = QSpinBox()
        self.edge_percent_value.setRange(0, 100)
        self.edge_percent_value.setValue(2)
        self.edge_percent_value.setSuffix(" %")
        layout.addWidget(self.edge_percent_value)
        self.edge_stage = QRadioButton("To current stage position")
        layout.addWidget(self.edge_stage)
        self.apply_edge = QPushButton("Apply")
        self.apply_edge.clicked.connect(self._apply_edge_boundary)
        layout.addWidget(self.apply_edge, alignment=Qt.AlignCenter)
        return panel

    def _legend_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        grid = QGridLayout()
        items = [
            ("#ff6b6b", "Stage Mark"),
            ("#ffffff", "Valid Die"),
            ("#808080", "Origin Die"),
            ("#3e8d9c", "Reticle"),
            ("#c8c8c8", "Invalid Die"),
        ]
        for index, (color, label) in enumerate(items):
            marker = QLabel("")
            marker.setFixedSize(12, 12)
            marker.setStyleSheet(f"background: {color}; border: 1px solid #555555;")
            grid.addWidget(marker, index, 0)
            grid.addWidget(QLabel(label), index, 1)
        layout.addLayout(grid)
        return panel

    def _footer(self) -> QHBoxLayout:
        footer = QHBoxLayout()
        self.undo_button = QPushButton("<< Undo")
        self.undo_button.setEnabled(False)
        self.undo_button.clicked.connect(self._undo)
        self.redo_button = QPushButton("Redo >>")
        self.redo_button.setEnabled(False)
        self.redo_button.clicked.connect(self._redo)
        footer.addWidget(self.undo_button)
        footer.addWidget(self.redo_button)
        footer.addStretch(1)
        self.valid_die_label = QLabel(f"Total valid die on wafer       {self.valid_die_count}")
        footer.addWidget(self.valid_die_label)
        footer.addStretch(1)
        finish = QPushButton("Finish")
        finish.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        footer.addWidget(finish)
        footer.addWidget(cancel)
        return footer

    def _instructions(self) -> QLabel:
        label = QLabel(
            "Left-click a die to apply the selected mode. Click the same die again in Toggle mode to add it back.\n"
            "Click and drag to draw a rectangle; the selected mode is applied to die inside the rectangle.\n"
            "To zoom, hold down the SHIFT key and click and drag.\n"
            "To drive the stage to a point, hold down the SHIFT key and click the left mouse button on a point on the wafer.\n"
            "Press Ctrl + Left Mouse click to snap to the nearest point/corner."
        )
        label.setAlignment(Qt.AlignCenter)
        return label

    def _update_edge_controls(self, checked=None):
        enabled = hasattr(self, "edge_enabled") and self.edge_enabled.isChecked()
        for widget_name in [
            "edge_microns",
            "edge_micron_value",
            "edge_percent",
            "edge_percent_value",
            "edge_stage",
            "apply_edge",
        ]:
            if hasattr(self, widget_name):
                getattr(self, widget_name).setEnabled(enabled)

    def _apply_edge_boundary(self):
        if not self.edge_enabled.isChecked():
            self.canvas.set_edge_boundary(False)
            return
        if self.edge_percent.isChecked():
            margin_cells = max(
                0,
                round(min(self.canvas.columns, self.canvas.rows) * self.edge_percent_value.value() / 100),
            )
        elif self.edge_stage.isChecked():
            col, row = self.canvas.stage_die
            margin_cells = min(
                col,
                row,
                self.canvas.columns - 1 - col,
                self.canvas.rows - 1 - row,
            )
        else:
            margin_cells = max(0, round(self.edge_micron_value.value() / 3000))
        self.canvas.set_edge_boundary(True, margin_cells)

    def _apply_die_action(self, die=None):
        die = die or self.canvas.stage_die
        self._record_history()
        if self.origin_mode.isChecked():
            self.canvas.set_origin_die(die)
            self._update_history_buttons()
            return
        if self.add_mode.isChecked():
            delta = self.canvas.set_die_valid(die, True)
        elif self.remove_mode.isChecked():
            delta = self.canvas.set_die_valid(die, False)
        else:
            delta = self.canvas.toggle_die(die)
        self.valid_die_count += delta
        self._update_valid_die_count()
        self._update_history_buttons()

    def _apply_die_rect_action(self, dies):
        if not dies:
            return
        self._record_history()
        if self.origin_mode.isChecked():
            self.canvas.set_origin_die(dies[0])
            self._update_history_buttons()
            return
        delta = 0
        for die in dies:
            if self.add_mode.isChecked():
                delta += self.canvas.set_die_valid(die, True, refresh=False)
            elif self.remove_mode.isChecked():
                delta += self.canvas.set_die_valid(die, False, refresh=False)
            else:
                delta += self.canvas.toggle_die(die, refresh=False)
        self.valid_die_count += delta
        self.canvas.update()
        self._update_valid_die_count()
        self._update_history_buttons()

    def _select_die_at_stage_position(self):
        self._apply_die_action()

    def _remove_outside_die(self):
        self._record_history()
        removed = self.canvas.remove_outside_die()
        self.valid_die_count = max(0, self.valid_die_count - removed)
        self._update_valid_die_count()
        self._update_history_buttons()

    def _add_inside_die(self):
        self._record_history()
        added = self.canvas.add_inside_die()
        self.valid_die_count += added
        self._update_valid_die_count()
        self._update_history_buttons()

    def _set_allow_partial_die(self, enabled: bool):
        if not hasattr(self, "canvas") or self.canvas.allow_partial_die == enabled:
            return
        self._record_history()
        self.canvas.set_allow_partial_die(enabled)
        self.valid_die_count = self.canvas.valid_die_count()
        self._update_valid_die_count()
        self._update_history_buttons()

    def _snapshot(self):
        return {
            "invalid_die": set(self.canvas.invalid_die),
            "origin_die": tuple(self.canvas.origin_die),
            "valid_die_count": self.valid_die_count,
            "allow_partial_die": self.canvas.allow_partial_die,
        }

    def _record_history(self):
        self._history.append(self._snapshot())
        self._redo_history.clear()

    def _restore_snapshot(self, state):
        self.canvas.invalid_die = set(state["invalid_die"])
        self.canvas.origin_die = tuple(state["origin_die"])
        self.canvas.allow_partial_die = bool(state["allow_partial_die"])
        self.allow_partial.blockSignals(True)
        self.allow_partial.setChecked(self.canvas.allow_partial_die)
        self.allow_partial.blockSignals(False)
        self.valid_die_count = int(state["valid_die_count"])
        self.canvas.update()
        self._update_valid_die_count()
        self._update_history_buttons()

    def _undo(self):
        if not self._history:
            return
        self._redo_history.append(self._snapshot())
        self._restore_snapshot(self._history.pop())

    def _redo(self):
        if not self._redo_history:
            return
        self._history.append(self._snapshot())
        self._restore_snapshot(self._redo_history.pop())

    def _update_history_buttons(self):
        self.undo_button.setEnabled(bool(self._history))
        self.redo_button.setEnabled(bool(self._redo_history))

    def _update_valid_die_count(self):
        self.valid_die_label.setText(f"Total valid die on wafer       {self.valid_die_count}")

    def _finish(self):
        self._update_valid_die_count()
        self.accept()


class EditMapCanvas(QWidget):
    def __init__(
        self,
        dialog: EditMapDialog,
        invalid_die=None,
        origin_die=(28, 28),
        *,
        pitch_width: float = 0.0,
        pitch_height: float = 0.0,
        allow_partial_die: bool = True,
    ):
        super().__init__(dialog)
        self.dialog = dialog
        self.setMinimumSize(760, 700)
        self.pitch_width = float(pitch_width)
        self.pitch_height = float(pitch_height)
        self.columns, self.rows = die_grid_dimensions(self.pitch_width, self.pitch_height)
        self.stage_die = centered_die_origin(self.columns, self.rows)
        self.origin_die = self._bounded_die(origin_die)
        self.invalid_die = set(invalid_die or set())
        self.allow_partial_die = bool(allow_partial_die)
        self.show_edge_boundary = False
        self.edge_margin_cells = 4
        self.drag_start = None
        self.drag_current = None

    def _bounded_die(self, die):
        col, row = die
        return (
            max(0, min(self.columns - 1, int(col))),
            max(0, min(self.rows - 1, int(row))),
        )

    def _grid_geometry(self, x: int, y: int, side: int):
        if self.pitch_width > 0 and self.pitch_height > 0:
            cell_w = side * self.pitch_width / WAFER_DIAMETER_UM
            cell_h = side * self.pitch_height / WAFER_DIAMETER_UM
        else:
            cell_w = side / self.columns
            cell_h = side / self.rows
        grid_x = x + side / 2 - self.columns * cell_w / 2
        grid_y = y + side / 2 - self.rows * cell_h / 2
        return grid_x, grid_y, cell_w, cell_h

    def _die_center_inside_wafer(self, col: int, row: int, x: int, y: int, side: int) -> bool:
        return self._die_in_wafer(col, row, x, y, side)

    def _die_bounds(self, col: int, row: int, x: int, y: int, side: int):
        grid_x, grid_y, cell_w, cell_h = self._grid_geometry(x, y, side)
        left = grid_x + col * cell_w
        top = grid_y + row * cell_h
        return left, top, left + cell_w, top + cell_h

    @staticmethod
    def _rect_intersects_circle(bounds, center_x: float, center_y: float, radius: float) -> bool:
        left, top, right, bottom = bounds
        nearest_x = max(left, min(center_x, right))
        nearest_y = max(top, min(center_y, bottom))
        return (nearest_x - center_x) ** 2 + (nearest_y - center_y) ** 2 <= radius ** 2

    @staticmethod
    def _rect_inside_circle(bounds, center_x: float, center_y: float, radius: float) -> bool:
        left, top, right, bottom = bounds
        return all(
            (corner_x - center_x) ** 2 + (corner_y - center_y) ** 2 <= radius ** 2
            for corner_x, corner_y in (
                (left, top),
                (right, top),
                (left, bottom),
                (right, bottom),
            )
        )

    def _die_in_wafer(self, col: int, row: int, x: int, y: int, side: int) -> bool:
        bounds = self._die_bounds(col, row, x, y, side)
        center_x = x + side / 2
        center_y = y + side / 2
        radius = side / 2
        if self.allow_partial_die:
            return self._rect_intersects_circle(bounds, center_x, center_y, radius)
        return self._rect_inside_circle(bounds, center_x, center_y, radius)

    def _die_inside_radius(self, col: int, row: int, x: int, y: int, side: int, radius: float) -> bool:
        return self._rect_inside_circle(
            self._die_bounds(col, row, x, y, side),
            x + side / 2,
            y + side / 2,
            radius,
        )

    def valid_die_count(self) -> int:
        x, y, side = self._wafer_geometry()
        return sum(
            1
            for col in range(self.columns)
            for row in range(self.rows)
            if self._die_in_wafer(col, row, x, y, side) and (col, row) not in self.invalid_die
        )

    def set_allow_partial_die(self, enabled: bool):
        self.allow_partial_die = bool(enabled)
        self.update()

    def mousePressEvent(self, event):  # noqa: N802 - Qt override
        if hasattr(event, "button") and event.button() == Qt.LeftButton:
            position = self._event_position(event)
            die = self._die_at_position(position)
            if die:
                self.drag_start = position
                self.drag_current = position
                self.stage_die = die
                self.update()

    def mouseMoveEvent(self, event):  # noqa: N802 - Qt override
        if self.drag_start:
            self.drag_current = self._event_position(event)
            self.update()

    def mouseReleaseEvent(self, event):  # noqa: N802 - Qt override
        if not self.drag_start:
            return
        end = self._event_position(event)
        start = self.drag_start
        self.drag_start = None
        self.drag_current = None
        if abs(end[0] - start[0]) < 5 and abs(end[1] - start[1]) < 5:
            die = self._die_at_position(end)
            if die:
                self.stage_die = die
                self.dialog._apply_die_action(die)
        else:
            dies = self._dies_in_screen_rect(start, end)
            self.dialog._apply_die_rect_action(dies)
        self.update()

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#858583"))
        rect = self.rect().adjusted(38, 24, -38, -36)
        side = min(rect.width(), rect.height())
        x = rect.center().x() - side // 2
        y = rect.center().y() - side // 2
        painter.setBrush(QColor("#ffffff"))
        painter.setPen(QPen(QColor("#555555"), 1))
        painter.drawEllipse(x, y, side, side)
        if self.show_edge_boundary:
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor("#777777"), 1, Qt.DotLine))
            _grid_x, _grid_y, cell_w, cell_h = self._grid_geometry(x, y, side)
            inset = int(self.edge_margin_cells * min(cell_w, cell_h))
            painter.drawEllipse(x + inset, y + inset, side - inset * 2, side - inset * 2)
        self._draw_die_grid(painter, x, y, side)
        self._draw_drag_rect(painter)
        self._draw_move_stage(painter, 18, self.height() - 170)

    def _wafer_geometry(self):
        rect = self.rect().adjusted(38, 24, -38, -36)
        side = min(rect.width(), rect.height())
        x = rect.center().x() - side // 2
        y = rect.center().y() - side // 2
        return x, y, side

    @staticmethod
    def _event_position(event):
        if hasattr(event, "position"):
            point = event.position()
            return int(point.x()), int(point.y())
        point = event.pos()
        return point.x(), point.y()

    def _die_at_position(self, position):
        x, y, side = self._wafer_geometry()
        px, py = position
        if not (x <= px <= x + side and y <= py <= y + side):
            return None
        center_x = x + side / 2
        center_y = y + side / 2
        if (px - center_x) ** 2 + (py - center_y) ** 2 > (side / 2) ** 2:
            return None
        grid_x, grid_y, cell_w, cell_h = self._grid_geometry(x, y, side)
        col = int((px - grid_x) / cell_w)
        row = int((py - grid_y) / cell_h)
        if 0 <= col < self.columns and 0 <= row < self.rows and self._die_in_wafer(col, row, x, y, side):
            return col, row
        return None

    def _dies_in_screen_rect(self, start, end):
        left = min(start[0], end[0])
        right = max(start[0], end[0])
        top = min(start[1], end[1])
        bottom = max(start[1], end[1])
        x, y, side = self._wafer_geometry()
        grid_x, grid_y, cell_w, cell_h = self._grid_geometry(x, y, side)
        dies = []
        for row in range(self.rows):
            for col in range(self.columns):
                cx = grid_x + (col + 0.5) * cell_w
                cy = grid_y + (row + 0.5) * cell_h
                if left <= cx <= right and top <= cy <= bottom:
                    if self._die_at_position((int(cx), int(cy))):
                        dies.append((col, row))
        return dies

    def _draw_die_grid(self, painter: QPainter, x: int, y: int, side: int):
        grid_x, grid_y, cell_w, cell_h = self._grid_geometry(x, y, side)
        wafer_center = (x + side / 2, y + side / 2)
        radius = side / 2
        painter.save()
        painter.setClipRegion(QRegion(x, y, side, side, QRegion.Ellipse))
        painter.setPen(QPen(QColor("#ffffff"), 1))
        for row in range(self.rows):
            for col in range(self.columns):
                if not self._die_in_wafer(col, row, x, y, side):
                    continue
                color = QColor("#a8a8a8") if (col, row) in self.invalid_die else QColor("#d2d2d2")
                painter.fillRect(
                    int(grid_x + col * cell_w),
                    int(grid_y + row * cell_h),
                    max(1, int(cell_w) - 1),
                    max(1, int(cell_h) - 1),
                    color,
                )
        self._draw_die_marker(painter, grid_x, grid_y, cell_w, cell_h, self.origin_die, QColor("#808080"))
        self._draw_crosshair(painter, grid_x, grid_y, cell_w, cell_h, self.stage_die)
        painter.restore()

    def _draw_die_marker(self, painter: QPainter, x: float, y: float, cell_w: float, cell_h: float, die, color: QColor):
        col, row = die
        painter.fillRect(int(x + col * cell_w), int(y + row * cell_h), max(2, int(cell_w)), max(2, int(cell_h)), color)

    def _draw_crosshair(self, painter: QPainter, x: float, y: float, cell_w: float, cell_h: float, die):
        col, row = die
        px = int(x + (col + 0.5) * cell_w)
        py = int(y + (row + 0.5) * cell_h)
        painter.setPen(QPen(QColor("#ff5050"), 1))
        painter.drawLine(px - 10, py, px + 10, py)
        painter.drawLine(px, py - 10, px, py + 10)

    def _draw_drag_rect(self, painter: QPainter):
        if not self.drag_start or not self.drag_current:
            return
        left = min(self.drag_start[0], self.drag_current[0])
        top = min(self.drag_start[1], self.drag_current[1])
        width = abs(self.drag_current[0] - self.drag_start[0])
        height = abs(self.drag_current[1] - self.drag_start[1])
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor("#2b5fd9"), 1, Qt.DashLine))
        painter.drawRect(left, top, width, height)

    def _draw_move_stage(self, painter: QPainter, x: int, y: int):
        painter.setBrush(QColor("#3156e8"))
        painter.setPen(QPen(QColor("#ffffff"), 1))
        painter.drawRect(x, y, 82, 130)
        painter.drawText(x + 12, y + 13, "Move Stage")
        labels = ["\\", "^", "/", "<", "", ">", "/", "v", "\\"]
        for index, text in enumerate(labels):
            col = index % 3
            row = index // 3
            bx = x + 8 + col * 22
            by = y + 22 + row * 22
            painter.setBrush(QColor("#f6f6f6"))
            painter.setPen(QPen(QColor("#1641d8"), 1))
            painter.drawRect(bx, by, 18, 18)
            painter.drawText(bx + 5, by + 13, text)
        painter.setPen(QPen(QColor("#111111"), 1))
        painter.setBrush(QColor("#ffffff"))
        painter.drawRect(x + 9, y + 92, 64, 20)
        painter.drawText(x + 13, y + 106, "Move by Die")
        painter.drawRect(x + 20, y + 114, 42, 14)
        painter.drawText(x + 32, y + 126, ">>")

    def toggle_stage_die(self) -> int:
        return self.toggle_die(self.stage_die)

    def toggle_die(self, die, refresh: bool = True) -> int:
        if die in self.invalid_die:
            self.invalid_die.remove(die)
            if refresh:
                self.update()
            return 1
        self.invalid_die.add(die)
        if refresh:
            self.update()
        return -1

    def set_stage_die_valid(self, valid: bool) -> int:
        return self.set_die_valid(self.stage_die, valid)

    def set_die_valid(self, die, valid: bool, refresh: bool = True) -> int:
        if valid and die in self.invalid_die:
            self.invalid_die.remove(die)
            if refresh:
                self.update()
            return 1
        if not valid and die not in self.invalid_die:
            self.invalid_die.add(die)
            if refresh:
                self.update()
            return -1
        return 0

    def set_origin_at_stage(self):
        self.set_origin_die(self.stage_die)

    def set_origin_die(self, die):
        self.origin_die = self._bounded_die(die)
        self.update()

    def set_edge_boundary(self, enabled: bool, margin_cells: int = 4):
        self.show_edge_boundary = enabled
        self.edge_margin_cells = max(0, min(max(0, min(self.columns, self.rows) // 2), margin_cells))
        self.update()

    def remove_outside_die(self) -> int:
        added = 0
        margin = self.edge_margin_cells if self.show_edge_boundary else 4
        x, y, side = self._wafer_geometry()
        _grid_x, _grid_y, cell_w, cell_h = self._grid_geometry(x, y, side)
        exclusion_radius = max(0.0, side / 2 - margin * min(cell_w, cell_h))
        for col in range(self.columns):
            for row in range(self.rows):
                inside_wafer = self._die_in_wafer(col, row, x, y, side)
                inside_boundary = self._die_inside_radius(col, row, x, y, side, exclusion_radius)
                if inside_wafer and not inside_boundary:
                    if (col, row) not in self.invalid_die:
                        self.invalid_die.add((col, row))
                        added += 1
        self.update()
        return added

    def add_inside_die(self) -> int:
        margin = self.edge_margin_cells if self.show_edge_boundary else 4
        x, y, side = self._wafer_geometry()
        _grid_x, _grid_y, cell_w, cell_h = self._grid_geometry(x, y, side)
        exclusion_radius = max(0.0, side / 2 - margin * min(cell_w, cell_h))
        restored = {
            die
            for die in self.invalid_die
            if self._die_in_wafer(die[0], die[1], x, y, side)
            and self._die_inside_radius(die[0], die[1], x, y, side, exclusion_radius)
        }
        self.invalid_die.difference_update(restored)
        self.update()
        return len(restored)


class AdjustDieCornerOptionsDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Adjust Die Corner")
        self.setFixedSize(260, 170)
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
                background: #f2efe3;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-height: 24px;
                padding: 2px 18px;
            }
            QFrame#groupPanel {
                border: 1px solid #c7bea7;
                background: #ece9d8;
            }
            QLabel[blueTitle="true"] {
                color: #0a55e5;
                background: #ece9d8;
            }
            """
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 14)
        group = QFrame()
        group.setObjectName("groupPanel")
        title = QLabel("Adjust Die Corner Options")
        title.setProperty("blueTitle", True)
        title.setParent(group)
        title.move(8, -1)
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(12, 16, 12, 10)
        self.shift_die_corner = QRadioButton("Shift Die Corner")
        self.change_die_corner = QRadioButton("Change Die Corner")
        self.change_die_corner.setChecked(True)
        group_layout.addWidget(self.shift_die_corner)
        group_layout.addWidget(self.change_die_corner)
        root.addWidget(group)
        footer = QHBoxLayout()
        ok = QPushButton("OK")
        ok.setFixedWidth(92)
        ok.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.setFixedWidth(92)
        cancel.clicked.connect(self.reject)
        footer.addWidget(ok)
        footer.addStretch(1)
        footer.addWidget(cancel)
        root.addLayout(footer)


class AdjustDieCornerNotificationDialog(QDialog):
    def __init__(self, mode: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Puma 9xxx -- Msg 80150390H (-2146106480)")
        self.setFixedSize(520, 360)
        self.mode = mode
        self._build_ui()
        self._set_details_visible(False)

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
                background: #f2efe3;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-height: 24px;
                padding: 2px 14px;
            }
            QFrame#messageBox {
                background: #ffffff;
                border: 1px solid #b8b8b8;
            }
            """
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 12)
        root.setSpacing(10)

        top = QHBoxLayout()
        icon = QLabel("!")
        icon.setAlignment(Qt.AlignCenter)
        icon.setFixedSize(48, 48)
        icon.setStyleSheet("background: #ffd700; border: 2px solid #b49a00; font-size: 28px; font-weight: bold;")
        top.addWidget(icon)
        message_frame = QFrame()
        message_frame.setObjectName("messageBox")
        message_layout = QVBoxLayout(message_frame)
        message_layout.setContentsMargins(8, 8, 8, 8)
        self.message = QLabel(
            "Test Geometry data components (i.e. Care Area, Light\n"
            "Focus, Premap etc...) of this recipe has been\n"
            "changed during Adjust Die Corner, user needs to\n"
            "verify these components along with sample plan and\n"
            "edit map for their correctness following are the\n"
            "warnings: Please click 'More >>' for details."
        )
        self.message.setWordWrap(True)
        self.message.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        message_layout.addWidget(self.message)
        top.addWidget(message_frame, 1)
        root.addLayout(top, 1)

        buttons = QHBoxLayout()
        self.write_button = QPushButton("Write to File")
        self.write_button.clicked.connect(self._write_to_file)
        ok = QPushButton("OK")
        ok.setFixedWidth(96)
        ok.clicked.connect(self.accept)
        self.more_button = QPushButton("More >>")
        self.more_button.setFixedWidth(96)
        self.more_button.clicked.connect(self._toggle_details)
        buttons.addWidget(self.write_button)
        buttons.addStretch(1)
        buttons.addWidget(ok)
        buttons.addStretch(1)
        buttons.addWidget(self.more_button)
        root.addLayout(buttons)

        self.details_frame = QFrame()
        self.details_frame.setObjectName("messageBox")
        details_layout = QVBoxLayout(self.details_frame)
        details_layout.setContentsMargins(8, 8, 8, 8)
        self.details = QLabel(
            "Scribeline is changed according to the changed die corner,\n"
            "please verify the same.\n\n"
            "Care Area geometry was shifted to preserve die-relative coordinates.\n"
            "Light Focus and sample plan locations should be reviewed before running the recipe.\n"
            "Edit Map should be checked for invalid or partial die after the adjustment."
        )
        self.details.setWordWrap(True)
        self.details.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        details_layout.addWidget(self.details)
        root.addWidget(self.details_frame)

    def _toggle_details(self):
        self._set_details_visible(not self.details_frame.isVisible())

    def _set_details_visible(self, visible: bool):
        self.details_frame.setVisible(visible)
        self.more_button.setText("<< Less" if visible else "More >>")

    def _write_to_file(self):
        path = "adjust_die_corner_notification.txt"
        with open(path, "w", encoding="utf-8") as file:
            file.write(self.message.text().replace("<br>", "\n"))
            file.write("\n\n")
            file.write(self.details.text())
        self.setWindowTitle(f"Puma 9xxx -- Notification written to {path}")


class AdjustDieCornerViewDialog(QDialog):
    def __init__(
        self,
        mode: str,
        initial_die_corner=(28, 28),
        invalid_die=None,
        origin_die=(28, 28),
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Adjust Die Corner")
        self.resize(980, 760)
        self.setMinimumSize(900, 680)
        self.mode = mode
        self.marked = False
        self._build_ui(initial_die_corner, invalid_die or set(), origin_die)
        self._refresh_state()

    def _build_ui(self, initial_die_corner, invalid_die, origin_die):
        self.setStyleSheet(
            """
            QDialog {
                background: #e9e5d3;
                color: #111111;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10px;
            }
            QPushButton {
                background: #f2efe3;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-height: 24px;
                padding: 2px 12px;
            }
            QPushButton:disabled {
                color: #9a958a;
                background: #eeeada;
            }
            QFrame#rightPanel, QFrame#instructionPanel {
                border: 1px solid #c7bea7;
                background: #e9e5d3;
            }
            QLabel[blueTitle="true"] {
                color: #0a55e5;
                background: #e9e5d3;
            }
            """
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(6)
        body = QHBoxLayout()
        body.setSpacing(8)
        self.canvas = AdjustDieCornerCanvas(self, initial_die_corner, invalid_die, origin_die)
        body.addWidget(self.canvas, 1)
        body.addWidget(self._right_panel(), 0)
        root.addLayout(body, 1)
        root.addWidget(self._instruction_panel())
        root.addLayout(self._footer())

    def _right_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("rightPanel")
        panel.setFixedWidth(230)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 8, 10, 8)
        mode_label = QLabel("Shift Die Corner" if self.mode == "shift" else "Change Die Corner")
        mode_label.setProperty("blueTitle", True)
        layout.addWidget(mode_label)
        layout.addSpacing(8)
        self.corner_label = QLabel("")
        layout.addWidget(self.corner_label)
        layout.addStretch(1)
        layout.addWidget(self._legend_panel())
        return panel

    def _legend_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        header = QLabel("Legend")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        grid = QGridLayout()
        items = [
            ("#ff6b6b", "Stage Mark"),
            ("#31c96b", "Marked Die Corner"),
            ("#ffffff", "Valid Die"),
            ("#f2d0d0", "Origin Die"),
            ("#c8c8c8", "Invalid Die"),
        ]
        for index, (color, label) in enumerate(items):
            marker = QLabel("")
            marker.setFixedSize(12, 12)
            marker.setStyleSheet(f"background: {color}; border: 1px solid #555555;")
            row = index // 2
            column = (index % 2) * 2
            grid.addWidget(marker, row, column)
            grid.addWidget(QLabel(label), row, column + 1)
        layout.addLayout(grid)
        return panel

    def _instruction_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("instructionPanel")
        panel.setFixedHeight(54)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(6, 4, 6, 4)
        self.message = QLabel("")
        self.message.setAlignment(Qt.AlignCenter)
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        return panel

    def _footer(self) -> QHBoxLayout:
        footer = QHBoxLayout()
        footer.setSpacing(10)
        self.mark_button = QPushButton("Mark")
        self.mark_button.setFixedWidth(84)
        self.mark_button.clicked.connect(self._mark_corner)
        self.finish_button = QPushButton("Finish")
        self.finish_button.setFixedWidth(84)
        self.finish_button.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.setFixedWidth(84)
        cancel.clicked.connect(self.reject)
        footer.addStretch(1)
        footer.addWidget(self.mark_button)
        footer.addWidget(self.finish_button)
        footer.addWidget(cancel)
        return footer

    def set_stage_die(self, die):
        self.canvas.stage_die = die
        self._refresh_state()
        self.canvas.update()

    def _mark_corner(self):
        self.canvas.marked_die = self.canvas.stage_die
        self.marked = True
        self._refresh_state()
        self.canvas.update()

    def _finish(self):
        if not self.marked:
            QMessageBox.warning(self, "Adjust Die Corner", "Mark the die corner before clicking Finish.")
            return
        notice = AdjustDieCornerNotificationDialog(self.mode, self)
        notice_result = notice.exec() if hasattr(notice, "exec") else notice.exec_()
        if notice_result != QDialog.Accepted:
            return
        if self.mode == "change":
            result = QMessageBox.question(
                self,
                "Change die corner confirmation",
                "Do you want to commit the changes?",
                QMessageBox.Ok | QMessageBox.Cancel,
                QMessageBox.Ok,
            )
            if result != QMessageBox.Ok:
                self.message.setText("Change was not committed. Reselect the die corner or click Finish again.")
                return
        self.accept()

    def _refresh_state(self):
        row, column = self.canvas.stage_die[1], self.canvas.stage_die[0]
        self.corner_label.setText(f"Current Die Corner [ Row , Column ]: {row}, {column}")
        self.finish_button.setEnabled(self.marked)
        if self.marked:
            marked_row, marked_column = self.canvas.marked_die[1], self.canvas.marked_die[0]
            self.message.setText(f"Die corner marked at {marked_row}, {marked_column}. Click Finish to save the adjustment.")
        else:
            self.message.setText(
                "Move the crosshair to the true site geometry and click Mark. "
                "Ctrl+click snaps to the nearest die corner in this simulation."
            )


class AdjustDieCornerCanvas(QWidget):
    def __init__(self, dialog: AdjustDieCornerViewDialog, initial_die_corner, invalid_die, origin_die):
        super().__init__(dialog)
        self.dialog = dialog
        self.setMinimumSize(680, 620)
        self.stage_die = initial_die_corner
        self.marked_die = initial_die_corner
        self.invalid_die = set(invalid_die)
        self.origin_die = origin_die

    def mousePressEvent(self, event):  # noqa: N802 - Qt override
        if hasattr(event, "button") and event.button() == Qt.LeftButton:
            die = self._die_at_position(self._event_position(event))
            if die:
                self.dialog.set_stage_die(die)

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#858583"))
        x, y, side = self._wafer_geometry()
        painter.setBrush(QColor("#ffffff"))
        painter.setPen(QPen(QColor("#555555"), 1))
        painter.drawEllipse(x, y, side, side)
        self._draw_die_grid(painter, x, y, side)
        self._draw_die_marker(painter, x, y, side, self.origin_die, QColor("#f2d0d0"))
        if self.dialog.marked:
            self._draw_die_marker(painter, x, y, side, self.marked_die, QColor("#31c96b"))
        self._draw_crosshair(painter, x, y, side, self.stage_die)
        self._draw_move_stage(painter, 18, self.height() - 170)
        notch_width = max(10, side // 42)
        painter.setBrush(QColor("#858583"))
        painter.setPen(QPen(QColor("#858583"), 1))
        painter.drawRect(x + side // 2 - notch_width // 2, y + side - 5, notch_width, 8)

    @staticmethod
    def _event_position(event):
        if hasattr(event, "position"):
            point = event.position()
            return int(point.x()), int(point.y())
        point = event.pos()
        return point.x(), point.y()

    def _wafer_geometry(self):
        rect = self.rect().adjusted(34, 20, -34, -28)
        side = min(rect.width(), rect.height())
        x = rect.center().x() - side // 2
        y = rect.center().y() - side // 2
        return x, y, side

    def _die_at_position(self, position):
        x, y, side = self._wafer_geometry()
        px, py = position
        if not (x <= px <= x + side and y <= py <= y + side):
            return None
        center_x = x + side / 2
        center_y = y + side / 2
        if (px - center_x) ** 2 + (py - center_y) ** 2 > (side / 2) ** 2:
            return None
        cell = side / 58
        col = int((px - x) / cell)
        row = int((py - y) / cell)
        if 0 <= col < 58 and 0 <= row < 58:
            return col, row
        return None

    def _draw_die_grid(self, painter: QPainter, x: int, y: int, side: int):
        cell = side / 58
        center_x = x + side / 2
        center_y = y + side / 2
        radius = side / 2
        painter.setPen(QPen(QColor("#d1d1d1"), 1))
        for row in range(58):
            for col in range(58):
                die_x = x + int(col * cell)
                die_y = y + int(row * cell)
                die_cx = die_x + cell / 2
                die_cy = die_y + cell / 2
                if (die_cx - center_x) ** 2 + (die_cy - center_y) ** 2 <= radius * radius * 0.93:
                    color = QColor("#c8c8c8") if (col, row) in self.invalid_die else QColor("#eeeeee")
                    painter.fillRect(die_x, die_y, max(1, int(cell) - 1), max(1, int(cell) - 1), color)

    def _draw_die_marker(self, painter: QPainter, x: int, y: int, side: int, die, color: QColor):
        cell = side / 58
        col, row = die
        painter.setBrush(color)
        painter.setPen(QPen(QColor("#222222"), 1))
        painter.drawRect(int(x + col * cell), int(y + row * cell), max(2, int(cell)), max(2, int(cell)))

    def _draw_crosshair(self, painter: QPainter, x: int, y: int, side: int, die):
        cell = side / 58
        col, row = die
        px = int(x + (col + 0.5) * cell)
        py = int(y + (row + 0.5) * cell)
        painter.setPen(QPen(QColor("#ff5050"), 1))
        painter.drawLine(px - 10, py, px + 10, py)
        painter.drawLine(px, py - 10, px, py + 10)

    def _draw_move_stage(self, painter: QPainter, x: int, y: int):
        painter.setBrush(QColor("#3156e8"))
        painter.setPen(QPen(QColor("#ffffff"), 1))
        painter.drawRect(x, y, 82, 130)
        painter.drawText(x + 12, y + 13, "Move Stage")
        labels = ["\\", "^", "/", "<", "", ">", "/", "v", "\\"]
        for index, text in enumerate(labels):
            col = index % 3
            row = index // 3
            bx = x + 8 + col * 22
            by = y + 22 + row * 22
            painter.setBrush(QColor("#f6f6f6"))
            painter.setPen(QPen(QColor("#1641d8"), 1))
            painter.drawRect(bx, by, 18, 18)
            painter.drawText(bx + 5, by + 13, text)
        painter.setPen(QPen(QColor("#111111"), 1))
        painter.setBrush(QColor("#ffffff"))
        painter.drawRect(x + 9, y + 92, 64, 20)
        painter.drawText(x + 13, y + 106, "10 um")
        painter.drawRect(x + 20, y + 114, 42, 14)
        painter.drawText(x + 32, y + 126, ">>")


class ReticleSizeDialog(QDialog):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        reticle_qualification: bool = False,
        reticle_width: int = 1,
        reticle_height: int = 1,
        reference_die=(29, 9),
        invalid_die=None,
        origin_die=(28, 28),
        max_width: int = 58,
        max_height: int = 58,
        pitch_width: float = 0.0,
        pitch_height: float = 0.0,
    ):
        super().__init__(parent)
        self.setWindowTitle("Reticle Qualification/Definition")
        self.resize(980, 760)
        self.setMinimumSize(900, 680)
        self.initial_state = (reticle_qualification, reticle_width, reticle_height, reference_die)
        self.max_width = max(1, int(max_width))
        self.max_height = max(1, int(max_height))
        self.pitch_width = float(pitch_width)
        self.pitch_height = float(pitch_height)
        self.reference_selected = bool(reticle_qualification)
        self._build_ui(reticle_qualification, reticle_width, reticle_height, reference_die, invalid_die or set(), origin_die)

    def _build_ui(self, qualification: bool, width: int, height: int, reference_die, invalid_die, origin_die):
        self.setStyleSheet(
            """
            QDialog {
                background: #e9e5d3;
                color: #111111;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10px;
            }
            QPushButton {
                background: #f2efe3;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-height: 24px;
                padding: 2px 12px;
            }
            QFrame#rightPanel, QFrame#groupPanel, QFrame#instructionPanel {
                border: 1px solid #c7bea7;
                background: #e9e5d3;
            }
            QLabel[blueTitle="true"] {
                color: #0a55e5;
                background: #e9e5d3;
            }
            """
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(6)
        body = QHBoxLayout()
        body.setSpacing(8)
        self.canvas = ReticleSizeCanvas(
            self,
            reference_die,
            invalid_die,
            origin_die,
            pitch_width=self.pitch_width,
            pitch_height=self.pitch_height,
        )
        body.addWidget(self.canvas, 1)
        body.addWidget(self._right_panel(qualification, width, height), 0)
        root.addLayout(body, 1)
        footer = QHBoxLayout()
        footer.addStretch(1)
        finish = QPushButton("Finish")
        finish.setFixedWidth(78)
        finish.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.setFixedWidth(78)
        cancel.clicked.connect(self._cancel_with_confirmation)
        footer.addWidget(finish)
        footer.addSpacing(18)
        footer.addWidget(cancel)
        footer.addStretch(1)
        root.addLayout(footer)
        self._refresh_reference_label()
        self._update_reticle_from_controls()

    def _right_panel(self, qualification: bool, width: int, height: int) -> QFrame:
        panel = QFrame()
        panel.setObjectName("rightPanel")
        panel.setFixedWidth(250)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)
        layout.addWidget(self._definition_panel(qualification, width, height))
        layout.addWidget(self._legend_panel())
        layout.addStretch(1)
        layout.addWidget(self._instructions_panel())
        return panel

    def _definition_panel(self, qualification: bool, width: int, height: int) -> QFrame:
        panel = QFrame()
        panel.setObjectName("groupPanel")
        title = QLabel("Reticle Definition")
        title.setProperty("blueTitle", True)
        title.setParent(panel)
        title.move(8, -1)
        layout = QGridLayout(panel)
        layout.setContentsMargins(10, 16, 10, 10)
        self.reticle_qualification = QCheckBox("Reticle Qualification")
        self.reticle_qualification.setChecked(qualification)
        self.reticle_qualification.toggled.connect(self._update_reticle_from_controls)
        layout.addWidget(self.reticle_qualification, 0, 0, 1, 4)
        layout.addWidget(QLabel("Reticle Size [ Width x Height ]:"), 1, 0, 1, 2)
        self.reticle_width = QSpinBox()
        self.reticle_width.setRange(1, self.max_width)
        self.reticle_width.setValue(max(1, width))
        self.reticle_width.setFixedWidth(48)
        self.reticle_width.valueChanged.connect(self._update_reticle_from_controls)
        self.reticle_height = QSpinBox()
        self.reticle_height.setRange(1, self.max_height)
        self.reticle_height.setValue(max(1, height))
        self.reticle_height.setFixedWidth(48)
        self.reticle_height.valueChanged.connect(self._update_reticle_from_controls)
        layout.addWidget(self.reticle_width, 1, 2)
        layout.addWidget(QLabel("x"), 1, 3, alignment=Qt.AlignCenter)
        layout.addWidget(self.reticle_height, 1, 4)
        layout.addWidget(QLabel("Reference Die [ Row , Column ]:"), 2, 0, 1, 3)
        self.reference_die_label = QLabel("")
        layout.addWidget(self.reference_die_label, 2, 3, 1, 2)
        return panel

    def _legend_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        header = QLabel("Legend")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        grid = QGridLayout()
        items = [
            ("#ff6b6b", "Stage Mark"),
            ("#ffffff", "Valid Die"),
            ("#f2d0d0", "Origin Die"),
            ("#d9b0b0", "Reference die for reticles"),
            ("#3e8d9c", "Reticle"),
        ]
        for index, (color, label) in enumerate(items):
            marker = QLabel("")
            marker.setFixedSize(12, 12)
            marker.setStyleSheet(f"background: {color}; border: 1px solid #555555;")
            row = index // 2
            column = (index % 2) * 2
            grid.addWidget(marker, row, column)
            grid.addWidget(QLabel(label), row, column + 1)
        layout.addLayout(grid)
        return panel

    def _instructions_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("instructionPanel")
        panel.setFixedHeight(84)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 4, 8, 8)
        title = QLabel("Detailed Instructions")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        body = QLabel(
            "Enable reticle qualification, enter the reticle width and height, and click a die\n"
            "for the reference die (lower-left corner) for reticles."
        )
        body.setWordWrap(True)
        layout.addWidget(body)
        return panel

    def set_reference_die(self, die):
        self.canvas.reference_die = die
        self.reference_selected = True
        self._refresh_reference_label()
        self.canvas.update()

    def _finish(self):
        if self.reticle_qualification.isChecked() and not self.reference_selected:
            QMessageBox.warning(
                self,
                "Reticle Qualification/Definition",
                "Click a die to mark the reference die before finishing.",
            )
            return
        self.accept()

    def _refresh_reference_label(self):
        row, column = self.canvas.reference_die[1], self.canvas.reference_die[0]
        self.reference_die_label.setText(f"{row}, {column}")

    def _update_reticle_from_controls(self, value=None):
        if hasattr(self, "canvas"):
            self.canvas.reticle_enabled = self.reticle_qualification.isChecked()
            self.canvas.reticle_width = self.reticle_width.value()
            self.canvas.reticle_height = self.reticle_height.value()
            self.canvas.update()

    def _cancel_with_confirmation(self):
        result = QMessageBox.information(
            self,
            "Puma 9xxx -- Msg 4002004AH (1073872970)",
            "Changes during this session will be discarded. Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if result == QMessageBox.Yes:
            self.reject()


class ReticleSizeCanvas(QWidget):
    def __init__(
        self,
        dialog: ReticleSizeDialog,
        reference_die,
        invalid_die,
        origin_die,
        *,
        pitch_width: float = 0.0,
        pitch_height: float = 0.0,
    ):
        super().__init__(dialog)
        self.dialog = dialog
        self.setMinimumSize(680, 620)
        self.pitch_width = float(pitch_width)
        self.pitch_height = float(pitch_height)
        self.columns, self.rows = die_grid_dimensions(self.pitch_width, self.pitch_height)
        self.reference_die = self._bounded_die(reference_die)
        self.stage_die = self.reference_die
        self.invalid_die = set(invalid_die)
        self.origin_die = self._bounded_die(origin_die)
        self.reticle_enabled = False
        self.reticle_width = 1
        self.reticle_height = 1

    def _bounded_die(self, die):
        col, row = die
        return (
            max(0, min(self.columns - 1, int(col))),
            max(0, min(self.rows - 1, int(row))),
        )

    def _grid_geometry(self, x: int, y: int, side: int):
        if self.pitch_width > 0 and self.pitch_height > 0:
            cell_w = side * self.pitch_width / WAFER_DIAMETER_UM
            cell_h = side * self.pitch_height / WAFER_DIAMETER_UM
        else:
            cell_w = side / self.columns
            cell_h = side / self.rows
        grid_x = x + side / 2 - self.columns * cell_w / 2
        grid_y = y + side / 2 - self.rows * cell_h / 2
        return grid_x, grid_y, cell_w, cell_h

    def mousePressEvent(self, event):  # noqa: N802 - Qt override
        if hasattr(event, "button") and event.button() == Qt.LeftButton:
            die = self._die_at_position(self._event_position(event))
            if die:
                self.stage_die = die
                self.dialog.set_reference_die(die)

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#e9e5d3"))
        frame = self.rect().adjusted(10, 10, -10, -10)
        side = min(frame.width(), frame.height())
        x = frame.center().x() - side // 2
        y = frame.center().y() - side // 2
        painter.fillRect(x, y, side, side, QColor("#858583"))
        painter.setPen(QPen(QColor("#4f4f4f"), 1))
        painter.drawRect(x, y, side, side)
        wafer_side = int(side * 0.92)
        wafer_x = x + (side - wafer_side) // 2
        wafer_y = y + (side - wafer_side) // 2
        painter.setBrush(QColor("#ffffff"))
        painter.setPen(QPen(QColor("#5e5e5e"), 1))
        painter.drawEllipse(wafer_x, wafer_y, wafer_side, wafer_side)
        self._draw_die_grid(painter, wafer_x, wafer_y, wafer_side)
        if self.reticle_enabled:
            self._draw_reticle_fields(painter, wafer_x, wafer_y, wafer_side)
        self._draw_die_marker(painter, wafer_x, wafer_y, wafer_side, self.origin_die, QColor("#f2d0d0"))
        self._draw_die_marker(painter, wafer_x, wafer_y, wafer_side, self.reference_die, QColor("#d9b0b0"))
        self._draw_crosshair(painter, wafer_x, wafer_y, wafer_side, self.stage_die)
        notch_width = max(10, wafer_side // 42)
        notch_x = wafer_x + wafer_side // 2 - notch_width // 2
        painter.setBrush(QColor("#858583"))
        painter.setPen(QPen(QColor("#858583"), 1))
        painter.drawRect(notch_x, wafer_y + wafer_side - 5, notch_width, 8)

    @staticmethod
    def _event_position(event):
        if hasattr(event, "position"):
            point = event.position()
            return int(point.x()), int(point.y())
        point = event.pos()
        return point.x(), point.y()

    def _wafer_geometry(self):
        frame = self.rect().adjusted(10, 10, -10, -10)
        side = min(frame.width(), frame.height())
        x = frame.center().x() - side // 2
        y = frame.center().y() - side // 2
        wafer_side = int(side * 0.92)
        wafer_x = x + (side - wafer_side) // 2
        wafer_y = y + (side - wafer_side) // 2
        return wafer_x, wafer_y, wafer_side

    def _die_at_position(self, position):
        x, y, side = self._wafer_geometry()
        px, py = position
        if not (x <= px <= x + side and y <= py <= y + side):
            return None
        center_x = x + side / 2
        center_y = y + side / 2
        if (px - center_x) ** 2 + (py - center_y) ** 2 > (side / 2) ** 2:
            return None
        grid_x, grid_y, cell_w, cell_h = self._grid_geometry(x, y, side)
        col = int((px - grid_x) / cell_w)
        row = int((py - grid_y) / cell_h)
        if 0 <= col < self.columns and 0 <= row < self.rows:
            die_cx = grid_x + (col + 0.5) * cell_w
            die_cy = grid_y + (row + 0.5) * cell_h
            if (die_cx - center_x) ** 2 + (die_cy - center_y) ** 2 > (side / 2) ** 2:
                return None
            return col, row
        return None

    def _draw_die_grid(self, painter: QPainter, x: int, y: int, side: int):
        grid_x, grid_y, cell_w, cell_h = self._grid_geometry(x, y, side)
        center_x = x + side / 2
        center_y = y + side / 2
        radius = side / 2
        painter.save()
        painter.setClipRegion(QRegion(x, y, side, side, QRegion.Ellipse))
        painter.setPen(QPen(QColor("#d1d1d1"), 1))
        for row in range(self.rows):
            for col in range(self.columns):
                die_x = grid_x + col * cell_w
                die_y = grid_y + row * cell_h
                die_cx = die_x + cell_w / 2
                die_cy = die_y + cell_h / 2
                if (die_cx - center_x) ** 2 + (die_cy - center_y) ** 2 <= radius * radius:
                    color = QColor("#c8c8c8") if (col, row) in self.invalid_die else QColor("#eeeeee")
                    painter.fillRect(
                        int(die_x),
                        int(die_y),
                        max(1, int(cell_w) - 1),
                        max(1, int(cell_h) - 1),
                        color,
                    )
        painter.restore()

    def _draw_reticle_fields(self, painter: QPainter, x: int, y: int, side: int):
        grid_x, grid_y, cell_w, cell_h = self._grid_geometry(x, y, side)
        ref_col, ref_row = self.reference_die
        width = max(1, self.reticle_width)
        height = max(1, self.reticle_height)
        painter.save()
        painter.setClipRegion(QRegion(x, y, side, side, QRegion.Ellipse))
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor("#1d6f78"), 1))
        for col in range(self.columns):
            for row in range(self.rows):
                if (col - ref_col) % width == 0 and (row - ref_row) % height == 0:
                    rect_x = int(grid_x + col * cell_w)
                    rect_y = int(grid_y + row * cell_h)
                    rect_w = max(1, int(width * cell_w))
                    rect_h = max(1, int(height * cell_h))
                    painter.drawRect(rect_x, rect_y, rect_w, rect_h)
        painter.restore()

    def _draw_die_marker(self, painter: QPainter, x: int, y: int, side: int, die, color: QColor):
        grid_x, grid_y, cell_w, cell_h = self._grid_geometry(x, y, side)
        col, row = die
        painter.save()
        painter.setClipRegion(QRegion(x, y, side, side, QRegion.Ellipse))
        painter.setBrush(color)
        painter.setPen(QPen(QColor("#222222"), 1))
        painter.drawRect(
            int(grid_x + col * cell_w),
            int(grid_y + row * cell_h),
            max(2, int(cell_w)),
            max(2, int(cell_h)),
        )
        painter.restore()

    def _draw_crosshair(self, painter: QPainter, x: int, y: int, side: int, die):
        grid_x, grid_y, cell_w, cell_h = self._grid_geometry(x, y, side)
        col, row = die
        px = int(grid_x + (col + 0.5) * cell_w)
        py = int(grid_y + (row + 0.5) * cell_h)
        painter.setPen(QPen(QColor("#ff5050"), 1))
        painter.drawLine(px - 10, py, px + 10, py)
        painter.drawLine(px, py - 10, px, py + 10)


class WaferMapCanvas(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setMinimumSize(690, 690)
        self.grid_defined = False
        self.pitch_width = 0.0
        self.pitch_height = 0.0
        self.die_count = 0
        self.definition_mode = ""
        self.scribe_lines_defined = False
        self.scribe_x = 0.0
        self.scribe_y = 0.0
        self.edit_map_applied = False
        self.invalid_die = set()
        self.origin_die = (28, 28)
        self.allow_partial_die = True
        self.reticle_enabled = False
        self.reticle_width = 1
        self.reticle_height = 1
        self.reference_die = (9, 29)
        self.adjust_die_corner_mode = ""
        self.adjusted_die_corner = (28, 28)

    def set_die_values(self, pitch_width: float, pitch_height: float, die_count: int, mode: str):
        self.grid_defined = True
        self.pitch_width = pitch_width
        self.pitch_height = pitch_height
        self.die_count = die_count
        self.definition_mode = mode
        self.edit_map_applied = False
        self.invalid_die.clear()
        self.origin_die = centered_die_origin(*die_grid_dimensions(pitch_width, pitch_height))
        self.reference_die = self.origin_die
        self.update()

    def set_scribe_lines(self, scribe_x: float, scribe_y: float):
        self.scribe_lines_defined = True
        self.scribe_x = scribe_x
        self.scribe_y = scribe_y
        self.update()

    def set_edit_map_state(self, die_count: int, invalid_die, origin_die, allow_partial_die: bool):
        self.grid_defined = True
        self.edit_map_applied = True
        self.die_count = die_count
        self.invalid_die = set(invalid_die)
        self.origin_die = origin_die
        self.allow_partial_die = allow_partial_die
        if not self.definition_mode:
            self.definition_mode = "wafer_map"
        self.update()

    def set_reticle_state(self, enabled: bool, width: int, height: int, reference_die):
        self.grid_defined = True
        self.edit_map_applied = True
        self.reticle_enabled = enabled
        self.reticle_width = max(1, width)
        self.reticle_height = max(1, height)
        self.reference_die = reference_die
        if not self.definition_mode:
            self.definition_mode = "wafer_map"
        self.update()

    def set_adjust_die_corner_state(self, mode: str, die_corner):
        self.grid_defined = True
        self.edit_map_applied = True
        self.adjust_die_corner_mode = mode
        self.adjusted_die_corner = die_corner
        if mode == "shift":
            self.origin_die = die_corner
        if not self.definition_mode:
            self.definition_mode = "wafer_map"
        self.update()

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#e9e5d3"))

        frame = self.rect().adjusted(8, 8, -8, -8)
        side = min(frame.width(), frame.height())
        x = frame.center().x() - side // 2
        y = frame.center().y() - side // 2
        painter.fillRect(x, y, side, side, QColor("#858583"))
        painter.setPen(QPen(QColor("#4f4f4f"), 1))
        painter.drawRect(x, y, side, side)

        wafer_side = int(side * 0.93)
        wafer_x = x + (side - wafer_side) // 2
        wafer_y = y + (side - wafer_side) // 2 + 4
        painter.setBrush(QColor("#ffffff"))
        painter.setPen(QPen(QColor("#5e5e5e"), 1))
        painter.drawEllipse(wafer_x, wafer_y, wafer_side, wafer_side)

        notch_width = max(10, wafer_side // 42)
        notch_x = wafer_x + wafer_side // 2 - notch_width // 2
        painter.setBrush(QColor("#858583"))
        painter.setPen(QPen(QColor("#858583"), 1))
        painter.drawRect(notch_x, wafer_y - 1, notch_width, 7)
        if self.grid_defined:
            self._draw_die_grid(painter, wafer_x, wafer_y, wafer_side)
            if self.scribe_lines_defined:
                self._draw_scribe_lines(painter, wafer_x, wafer_y, wafer_side)
            if self.reticle_enabled:
                self._draw_reticle_fields(painter, wafer_x, wafer_y, wafer_side)
            self._draw_origin_and_reticle(painter, wafer_x, wafer_y, wafer_side)
            if self.adjust_die_corner_mode:
                self._draw_adjusted_die_corner(painter, wafer_x, wafer_y, wafer_side)

    def _draw_die_grid(self, painter: QPainter, wafer_x: int, wafer_y: int, wafer_side: int):
        cols, rows = die_grid_dimensions(self.pitch_width, self.pitch_height)
        cell_w = wafer_side * max(self.pitch_width, 1.0) / WAFER_DIAMETER_UM
        cell_h = wafer_side * max(self.pitch_height, 1.0) / WAFER_DIAMETER_UM
        center_x = wafer_x + wafer_side / 2
        center_y = wafer_y + wafer_side / 2
        grid_x = center_x - cols * cell_w / 2
        grid_y = center_y - rows * cell_h / 2
        radius = wafer_side / 2
        painter.save()
        painter.setClipRegion(QRegion(wafer_x, wafer_y, wafer_side, wafer_side, QRegion.Ellipse))
        painter.setPen(QPen(QColor("#d1d1d1"), 1))
        for col in range(cols):
            for row in range(rows):
                die_x = grid_x + col * cell_w
                die_y = grid_y + row * cell_h
                die_cx = die_x + cell_w / 2
                die_cy = die_y + cell_h / 2
                dx = die_cx - center_x
                dy = die_cy - center_y
                if dx * dx + dy * dy <= radius * radius:
                    if self.edit_map_applied and (col, row) in self.invalid_die:
                        painter.setBrush(QColor("#c8c8c8"))
                    else:
                        painter.setBrush(QColor("#eeeeee"))
                    painter.drawRect(
                        int(die_x),
                        int(die_y),
                        max(1, int(cell_w) - 1),
                        max(1, int(cell_h) - 1),
                    )
        painter.restore()

    def _draw_origin_and_reticle(self, painter: QPainter, wafer_x: int, wafer_y: int, wafer_side: int):
        columns, rows = die_grid_dimensions(self.pitch_width, self.pitch_height)
        cell_w = wafer_side * max(self.pitch_width, 1.0) / WAFER_DIAMETER_UM
        cell_h = wafer_side * max(self.pitch_height, 1.0) / WAFER_DIAMETER_UM
        grid_x = wafer_x + wafer_side / 2 - columns * cell_w / 2
        grid_y = wafer_y + wafer_side / 2 - rows * cell_h / 2
        col, row = self.origin_die
        center_x = int(grid_x + (col + 0.5) * cell_w)
        center_y = int(grid_y + (row + 0.5) * cell_h)
        origin_size = max(8, wafer_side // 48)
        painter.save()
        painter.setClipRegion(QRegion(wafer_x, wafer_y, wafer_side, wafer_side, QRegion.Ellipse))
        painter.setBrush(QColor("#f2d0d0"))
        painter.setPen(QPen(QColor("#222222"), 1))
        painter.drawRect(center_x - origin_size // 2, center_y - origin_size // 2, origin_size, origin_size)
        if self.reticle_enabled:
            col, row = self.reference_die
            ref_x = int(grid_x + col * cell_w)
            ref_y = int(grid_y + row * cell_h)
            painter.setBrush(QColor("#d9b0b0"))
            painter.setPen(QPen(QColor("#222222"), 1))
            painter.drawRect(ref_x, ref_y, max(3, int(cell_w)), max(3, int(cell_h)))
        painter.restore()

    def _draw_scribe_lines(self, painter: QPainter, wafer_x: int, wafer_y: int, wafer_side: int):
        spacing_x = max(3, int(wafer_side * max(self.pitch_width, 1.0) / WAFER_DIAMETER_UM))
        spacing_y = max(3, int(wafer_side * max(self.pitch_height, 1.0) / WAFER_DIAMETER_UM))
        vertical_width = max(1, int(wafer_side * max(self.scribe_x, 1.0) / WAFER_DIAMETER_UM))
        horizontal_width = max(1, int(wafer_side * max(self.scribe_y, 1.0) / WAFER_DIAMETER_UM))
        center_x = wafer_x + wafer_side // 2
        center_y = wafer_y + wafer_side // 2
        radius = wafer_side // 2
        painter.setPen(QPen(QColor("#f7f7f7"), vertical_width))
        for offset in range(-radius, radius + 1, spacing_x):
            x_line = center_x + offset
            y_extent = int((radius * radius - offset * offset) ** 0.5) if abs(offset) <= radius else 0
            painter.drawLine(x_line, center_y - y_extent, x_line, center_y + y_extent)
        painter.setPen(QPen(QColor("#f7f7f7"), horizontal_width))
        for offset in range(-radius, radius + 1, spacing_y):
            y_line = center_y + offset
            x_extent = int((radius * radius - offset * offset) ** 0.5) if abs(offset) <= radius else 0
            painter.drawLine(center_x - x_extent, y_line, center_x + x_extent, y_line)

    def _draw_reticle_fields(self, painter: QPainter, wafer_x: int, wafer_y: int, wafer_side: int):
        columns, rows = die_grid_dimensions(self.pitch_width, self.pitch_height)
        cell_w = wafer_side * max(self.pitch_width, 1.0) / WAFER_DIAMETER_UM
        cell_h = wafer_side * max(self.pitch_height, 1.0) / WAFER_DIAMETER_UM
        grid_x = wafer_x + wafer_side / 2 - columns * cell_w / 2
        grid_y = wafer_y + wafer_side / 2 - rows * cell_h / 2
        ref_col, ref_row = self.reference_die
        width = max(1, self.reticle_width)
        height = max(1, self.reticle_height)
        painter.save()
        painter.setClipRegion(QRegion(wafer_x, wafer_y, wafer_side, wafer_side, QRegion.Ellipse))
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor("#1d6f78"), 1))
        for col in range(columns):
            for row in range(rows):
                if (col - ref_col) % width == 0 and (row - ref_row) % height == 0:
                    rect_x = int(grid_x + col * cell_w)
                    rect_y = int(grid_y + row * cell_h)
                    painter.drawRect(rect_x, rect_y, max(1, int(width * cell_w)), max(1, int(height * cell_h)))
        painter.restore()

    def _draw_adjusted_die_corner(self, painter: QPainter, wafer_x: int, wafer_y: int, wafer_side: int):
        columns, rows = die_grid_dimensions(self.pitch_width, self.pitch_height)
        cell_w = wafer_side * max(self.pitch_width, 1.0) / WAFER_DIAMETER_UM
        cell_h = wafer_side * max(self.pitch_height, 1.0) / WAFER_DIAMETER_UM
        grid_x = wafer_x + wafer_side / 2 - columns * cell_w / 2
        grid_y = wafer_y + wafer_side / 2 - rows * cell_h / 2
        col, row = self.adjusted_die_corner
        px = int(grid_x + (col + 0.5) * cell_w)
        py = int(grid_y + (row + 0.5) * cell_h)
        painter.setPen(QPen(QColor("#31c96b"), 2))
        painter.drawLine(px - 12, py, px + 12, py)
        painter.drawLine(px, py - 12, px, py + 12)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(px - 9, py - 9, 18, 18)

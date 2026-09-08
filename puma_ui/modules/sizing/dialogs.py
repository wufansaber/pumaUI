from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import math

from ...qt_compat import (
    QAction,
    QCheckBox,
    QColor,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMenu,
    QMenuBar,
    QMessageBox,
    QPainter,
    QPen,
    QPushButton,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    Qt,
)
from ..results_review import import_klarf_text
from .models import (
    SCALE_COLORS,
    SCALE_GROUPS,
    active_map,
    auto_map_for_set,
    consolidate_lot_results,
    default_sizing_recipe,
    defect_set_from_klarf_result,
    defect_set_from_result,
    export_sizing_recipe_xml,
    histogram_values,
    import_reference_sizes,
    import_sizing_recipe_xml,
    normalized_sizing_recipe,
    normalized_sizing_state,
    remove_defect_set,
    scatter_points,
    scatter_statistics,
    set_reference_size,
    transfer_reference_sizes,
    validate_sizing_recipe,
)


class ScatterPlotWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.points = []
        self.highlight_group = "All"
        self.legend_position = "Right"
        self.position_changed = None
        self.point_activated = None
        self._screen_points = []
        self._legend_areas = []
        self._hover_group = ""
        self.setMouseTracking(True)
        self.setMinimumSize(560, 430)

    def set_data(self, points, *, highlight_group="All", legend_position="Right"):
        self.points = list(points)
        self.highlight_group = highlight_group
        self.legend_position = legend_position
        self.update()

    def _plot_rect(self):
        left = 72 + (110 if self.legend_position == "Left" else 0)
        right = self.width() - 34 - (120 if self.legend_position == "Right" else 0)
        top = 44 + (48 if self.legend_position == "Top" else 0)
        bottom = self.height() - 64 - (58 if self.legend_position == "Bottom" else 0)
        return left, top, max(100, right - left), max(100, bottom - top)

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#e8e6df"))
        left, top, width, height = self._plot_rect()
        painter.fillRect(left, top, width, height, QColor("#ffffff"))
        painter.setPen(QPen(QColor("#89867f"), 1))
        painter.drawRect(left, top, width, height)
        maximum = max(
            [4.0]
            + [float(point.get("reference_size_um", 0.0)) for point in self.points]
            + [float(point.get("computed_size_um", 0.0)) for point in self.points]
        )
        maximum = math.ceil(maximum * 1.1 * 2.0) / 2.0
        painter.setPen(QPen(QColor("#d5d3cd"), 1))
        for step in range(1, 5):
            x = left + width * step / 5
            y = top + height * step / 5
            painter.drawLine(int(x), top, int(x), top + height)
            painter.drawLine(left, int(y), left + width, int(y))
        for offset, color in ((0.2, "#f7a6ab"), (0.0, "#5bdd60"), (-0.2, "#c6ad61")):
            painter.setPen(QPen(QColor(color), 2))
            x1 = max(0.0, -offset)
            x2 = min(maximum, maximum - offset)
            y1 = x1 + offset
            y2 = x2 + offset
            painter.drawLine(
                int(left + x1 / maximum * width),
                int(top + height - y1 / maximum * height),
                int(left + x2 / maximum * width),
                int(top + height - y2 / maximum * height),
            )
        self._screen_points = []
        for point in self.points:
            x = left + float(point["reference_size_um"]) / maximum * width
            y = top + height - float(point["computed_size_um"]) / maximum * height
            group = point.get("scale_group", "None")
            effective_highlight = self._hover_group or self.highlight_group
            faded = effective_highlight not in {"All", group}
            painter.setPen(QPen(QColor("#777777" if faded else "#202020"), 1))
            color = QColor(SCALE_COLORS.get(group, SCALE_COLORS["None"]))
            if faded:
                color.setAlpha(45)
            painter.setBrush(color)
            radius = 3 if faded else 5
            painter.drawEllipse(int(x - radius), int(y - radius), radius * 2, radius * 2)
            self._screen_points.append((x, y, point))
        painter.setPen(QPen(QColor("#202020"), 1))
        painter.drawText(left + width // 2 - 56, self.height() - 24, "Reference Size (um)")
        painter.save()
        painter.translate(22, top + height // 2 + 62)
        painter.rotate(-90)
        painter.drawText(0, 0, "Computed Size (um)")
        painter.restore()
        for step in range(6):
            value = maximum * step / 5
            painter.drawText(int(left + width * step / 5 - 10), top + height + 20, f"{value:.1f}")
            painter.drawText(left - 42, int(top + height - height * step / 5 + 4), f"{value:.1f}")
        self._paint_legend(painter)
        painter.end()

    def _paint_legend(self, painter):
        groups = list(SCALE_GROUPS)
        self._legend_areas = []
        if self.legend_position in {"Left", "Right"}:
            x = 20 if self.legend_position == "Left" else self.width() - 108
            y = 80
            for index, group in enumerate(groups):
                painter.setBrush(QColor(SCALE_COLORS[group]))
                painter.setPen(QPen(QColor("#303030"), 1))
                painter.drawEllipse(x, y + index * 25, 11, 11)
                painter.drawText(x + 18, y + 10 + index * 25, group)
                self._legend_areas.append((x - 4, y + index * 25 - 5, 95, 22, group))
        else:
            x = 80
            y = 28 if self.legend_position == "Top" else self.height() - 35
            for group in groups:
                painter.setBrush(QColor(SCALE_COLORS[group]))
                painter.drawEllipse(x, y, 10, 10)
                painter.drawText(x + 15, y + 10, group)
                self._legend_areas.append((x - 4, y - 5, 78, 22, group))
                x += 82

    def mouseMoveEvent(self, event):  # noqa: N802
        point = event.position() if hasattr(event, "position") else event.pos()
        hover = next((group for x, y, width, height, group in self._legend_areas if x <= point.x() <= x + width and y <= point.y() <= y + height), "")
        if hover != self._hover_group:
            self._hover_group = hover
            self.update()
        if hover:
            self.setToolTip(f"Highlight {hover} scale factor defects")
            return
        nearest = min(self._screen_points, key=lambda item: (item[0] - point.x()) ** 2 + (item[1] - point.y()) ** 2, default=None)
        if nearest and (nearest[0] - point.x()) ** 2 + (nearest[1] - point.y()) ** 2 <= 100:
            data = nearest[2]
            self.setToolTip(
                f"Defect {data.get('id')}  ({data.get('reference_size_um', 0):.3f}, {data.get('computed_size_um', 0):.3f})  {data.get('scale_group')}"
            )
        else:
            self.setToolTip("")

    def leaveEvent(self, event):  # noqa: N802
        self._hover_group = ""
        self.setToolTip("")
        self.update()

    def mouseDoubleClickEvent(self, event):  # noqa: N802
        point = event.position() if hasattr(event, "position") else event.pos()
        nearest = min(self._screen_points, key=lambda item: (item[0] - point.x()) ** 2 + (item[1] - point.y()) ** 2, default=None)
        if nearest and self.point_activated:
            self.point_activated(nearest[2])

    def contextMenuEvent(self, event):  # noqa: N802
        menu = QMenu(self)
        for position in ("Left", "Top", "Right", "Bottom"):
            action = menu.addAction(position)
            action.setCheckable(True)
            action.setChecked(position == self.legend_position)
            action.triggered.connect(lambda checked=False, value=position: self._set_position(value))
        menu.exec(event.globalPos())

    def _set_position(self, position):
        self.legend_position = position
        if self.position_changed:
            self.position_changed(position)
        self.update()


class HistogramWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.values = []
        self.show_cdf = False
        self.show_out_of_graph = False
        self.displayed_count = 0
        self.out_of_graph_count = 0
        self.setMinimumSize(620, 360)

    def set_data(self, values, show_cdf=False, show_out_of_graph=False):
        self.values = [float(value) for value in values]
        self.show_cdf = bool(show_cdf)
        self.show_out_of_graph = bool(show_out_of_graph)
        self.update()

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#e8e6df"))
        left, top, width, height = 58, 28, max(120, self.width() - 92), max(100, self.height() - 78)
        painter.fillRect(left, top, width, height, QColor("#ffffff"))
        painter.setPen(QPen(QColor("#77736b"), 1))
        painter.drawRect(left, top, width, height)
        if not self.values:
            painter.drawText(left + 18, top + 28, "No defects are available for this histogram.")
            painter.end()
            return
        ordered = sorted(self.values)
        if len(ordered) >= 20 and not self.show_out_of_graph:
            lower = max(0, int(len(ordered) * 0.05) - 1)
            upper = min(len(ordered) - 1, int(len(ordered) * 0.95))
            minimum, maximum = ordered[lower], ordered[upper]
        else:
            minimum, maximum = ordered[0], ordered[-1]
        if maximum <= minimum:
            maximum = minimum + 1.0
        displayed = [value for value in self.values if minimum <= value <= maximum]
        self.displayed_count = len(displayed)
        self.out_of_graph_count = len(self.values) - len(displayed)
        bins = [0] * 20
        for value in displayed:
            index = min(19, int((value - minimum) / (maximum - minimum) * 20))
            bins[index] += 1
        peak = max(bins) or 1
        bar_width = width / len(bins)
        painter.setPen(QPen(QColor("#465b73"), 1))
        painter.setBrush(QColor("#7894af"))
        cumulative = 0
        cdf_points = []
        for index, count in enumerate(bins):
            bar_height = count / peak * (height - 16)
            painter.drawRect(int(left + index * bar_width), int(top + height - bar_height), max(1, int(bar_width - 2)), int(bar_height))
            cumulative += count
            cdf_points.append((left + (index + 0.5) * bar_width, top + height - cumulative / max(1, len(displayed)) * height))
        if self.show_cdf:
            painter.setPen(QPen(QColor("#d33232"), 2))
            for first, second in zip(cdf_points, cdf_points[1:]):
                painter.drawLine(int(first[0]), int(first[1]), int(second[0]), int(second[1]))
        painter.setPen(QPen(QColor("#202020"), 1))
        painter.drawText(left, top + height + 22, f"{minimum:.2f}")
        painter.drawText(left + width - 35, top + height + 22, f"{maximum:.2f}")
        painter.drawText(left + width // 2 - 32, self.height() - 12, "Pixel Property")
        if self.out_of_graph_count:
            painter.drawText(left + width - 145, top + 18, f"Out of graph: {self.out_of_graph_count}")
        painter.end()


class SizingRecipeDialog(QDialog):
    def __init__(self, recipe=None, parent=None):
        super().__init__(parent)
        self.original = normalized_sizing_recipe(recipe)
        self.result_recipe = None
        self.setWindowTitle("Sizing Recipe")
        self.resize(650, 460)
        root = QVBoxLayout(self)
        general = QGridLayout()
        self.sizing_enabled = QCheckBox("Sizing Enabled")
        self.sizing_enabled.setChecked(self.original["sizing_enabled"])
        self.collect_data = QCheckBox("Collect Sizing Data")
        self.collect_data.setChecked(self.original["collect_sizing_data"])
        general.addWidget(self.sizing_enabled, 0, 0)
        general.addWidget(self.collect_data, 0, 1)
        root.addLayout(general)
        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)
        self.factor_controls = {}
        factors = QWidget()
        factor_grid = QGridLayout(factors)
        for index, name in enumerate(SCALE_GROUPS):
            control = QDoubleSpinBox()
            control.setRange(0.001, 1000.0)
            control.setDecimals(3)
            control.setValue(self.original["scale_factors"][name])
            factor_grid.addWidget(QLabel(name), index // 3, (index % 3) * 2)
            factor_grid.addWidget(control, index // 3, (index % 3) * 2 + 1)
            self.factor_controls[name] = control
        note = QLabel("Scale factors are the normal optimization controls. Adjust one defect group at a time.")
        note.setWordWrap(True)
        factor_grid.addWidget(note, 3, 0, 1, 6)
        self.tabs.addTab(factors, "Scale Factors")
        self.cut_controls = {}
        cuts = QWidget()
        cut_grid = QGridLayout(cuts)
        for index, (name, value) in enumerate(self.original["cut_lines"].items()):
            control = QDoubleSpinBox()
            control.setRange(0.0, 1000000.0)
            control.setDecimals(2)
            control.setValue(value)
            cut_grid.addWidget(QLabel(name), index // 3, (index % 3) * 2)
            cut_grid.addWidget(control, index // 3, (index % 3) * 2 + 1)
            self.cut_controls[name] = control
        warning = QLabel("Cut lines are pixel-size dependent advanced parameters and normally do not require editing.")
        warning.setWordWrap(True)
        cut_grid.addWidget(warning, 3, 0, 1, 6)
        self.tabs.addTab(cuts, "Cut Lines")
        buttons = QHBoxLayout()
        reset = QPushButton("Reset")
        reset.clicked.connect(self._reset)
        import_button = QPushButton("Import XML")
        import_button.clicked.connect(self._import_xml)
        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(self._apply)
        ok = QPushButton("OK")
        ok.clicked.connect(self._accept)
        close = QPushButton("Close")
        close.clicked.connect(self.reject)
        buttons.addStretch(1)
        for button in (reset, import_button, apply_button, ok, close):
            buttons.addWidget(button)
        root.addLayout(buttons)
        if not (parent and hasattr(parent, "apply_recipe")):
            apply_button.setEnabled(False)

    def values(self):
        return normalized_sizing_recipe({
            "sizing_enabled": self.sizing_enabled.isChecked(),
            "collect_sizing_data": self.collect_data.isChecked(),
            "scale_factors": {name: control.value() for name, control in self.factor_controls.items()},
            "cut_lines": {name: control.value() for name, control in self.cut_controls.items()},
        })

    def _reset(self):
        defaults = default_sizing_recipe()
        self.sizing_enabled.setChecked(defaults["sizing_enabled"])
        self.collect_data.setChecked(defaults["collect_sizing_data"])
        for name, control in self.factor_controls.items():
            control.setValue(defaults["scale_factors"][name])
        for name, control in self.cut_controls.items():
            control.setValue(defaults["cut_lines"][name])

    def _apply(self):
        values = self.values()
        errors = validate_sizing_recipe(values)
        if errors:
            QMessageBox.warning(self, "Sizing Recipe", "\n".join(errors))
            return
        self.result_recipe = values
        parent = self.parent()
        if parent and hasattr(parent, "apply_recipe"):
            parent.apply_recipe(values)

    def _import_xml(self):
        filename, _selected = QFileDialog.getOpenFileName(self, "Import Sizing Recipe", "", "XML Files (*.xml);;All Files (*)")
        if not filename:
            return
        try:
            recipe = import_sizing_recipe_xml(Path(filename).read_text(encoding="utf-8", errors="replace"))
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Import Sizing Recipe", str(exc))
            return
        self.sizing_enabled.setChecked(recipe["sizing_enabled"])
        self.collect_data.setChecked(recipe["collect_sizing_data"])
        for name, control in self.factor_controls.items():
            control.setValue(recipe["scale_factors"][name])
        for name, control in self.cut_controls.items():
            control.setValue(recipe["cut_lines"][name])

    def _accept(self):
        self._apply()
        if self.result_recipe is not None:
            self.accept()


class LotResultReaderDialog(QDialog):
    def __init__(self, results, parent=None):
        super().__init__(parent)
        self.results = list(results)
        self.selected_set = None
        self.setWindowTitle("Read Lot Result")
        self.resize(720, 460)
        root = QVBoxLayout(self)
        self.table = QTableWidget(len(self.results), 5)
        self.table.setHorizontalHeaderLabels(["Lot", "Wafer", "Inspection", "Status", "Defects"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for row, result in enumerate(self.results):
            for column, value in enumerate((result.get("lot_id", ""), result.get("wafer_id", ""), result.get("inspection", ""), result.get("status", ""), len(result.get("defects", [])))):
                self.table.setItem(row, column, QTableWidgetItem(str(value)))
        if self.results:
            self.table.selectRow(0)
        root.addWidget(self.table, 1)
        form = QGridLayout()
        self.name = QLineEdit()
        self.name.setPlaceholderText("Default defect set name")
        self.test = QComboBox()
        self.test.addItem("All")
        tests = sorted({str(defect.get("test", "Test 1")) for result in self.results for defect in result.get("defects", [])})
        self.test.addItems(tests)
        form.addWidget(QLabel("Defect Set Name"), 0, 0)
        form.addWidget(self.name, 0, 1)
        form.addWidget(QLabel("Choose Test"), 1, 0)
        form.addWidget(self.test, 1, 1)
        root.addLayout(form)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        finished = QPushButton("Finished")
        finished.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(finished)
        buttons.addWidget(cancel)
        root.addLayout(buttons)

    def _finish(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.warning(self, "Read Lot Result", "Select a lot result.")
            return
        source = self.results[rows[0].row()]
        self.selected_set = defect_set_from_result(source, name=self.name.text(), test=self.test.currentText())
        self.accept()


class KlarfOptionsDialog(QDialog):
    def __init__(self, source_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("KLARF Reader")
        root = QVBoxLayout(self)
        form = QGridLayout()
        self.name = QLineEdit(Path(source_path).stem)
        self.field = QComboBox()
        self.field.addItems(["dSize", "Class Code"])
        self.multiplier = QDoubleSpinBox()
        self.multiplier.setRange(0.0001, 1000.0)
        self.multiplier.setDecimals(4)
        self.multiplier.setValue(0.1)
        form.addWidget(QLabel("KLARF"), 0, 0)
        form.addWidget(QLabel(str(source_path)), 0, 1)
        form.addWidget(QLabel("Defect Set Name"), 1, 0)
        form.addWidget(self.name, 1, 1)
        form.addWidget(QLabel("Size Field"), 2, 0)
        form.addWidget(self.field, 2, 1)
        form.addWidget(QLabel("Class Multiplier"), 3, 0)
        form.addWidget(self.multiplier, 3, 1)
        self.field.currentTextChanged.connect(lambda value: self.multiplier.setEnabled(value == "Class Code"))
        self.multiplier.setEnabled(False)
        root.addLayout(form)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        finished = QPushButton("Finished")
        finished.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(finished)
        buttons.addWidget(cancel)
        root.addLayout(buttons)


class DefectSetEditorDialog(QDialog):
    def __init__(self, state, defect_set_id, initial_id=None, parent=None):
        super().__init__(parent)
        self.state = normalized_sizing_state(state)
        self.defect_set_id = defect_set_id
        self.result_state = None
        defect_set = next((item for item in self.state["defect_sets"] if item.get("id") == defect_set_id), {"defects": []})
        self.setWindowTitle("Defect Set")
        self.resize(680, 500)
        root = QVBoxLayout(self)
        self.table = QTableWidget(len(defect_set.get("defects", [])), 5)
        self.table.setHorizontalHeaderLabels(["ID", "Reference Size", "Computed Size", "Scale Factor", "Test"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for row, defect in enumerate(defect_set.get("defects", [])):
            values = (defect.get("id"), defect.get("reference_size_um", 0.0), defect.get("computed_size_um", 0.0), defect.get("scale_group", ""), defect.get("test", ""))
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column != 1:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, column, item)
            if str(defect.get("id")) == str(initial_id):
                self.table.selectRow(row)
        root.addWidget(self.table, 1)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(self._apply)
        ok = QPushButton("OK")
        ok.clicked.connect(self._accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(apply_button)
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        root.addLayout(buttons)

    def _apply(self):
        updated = normalized_sizing_state(self.state)
        for row in range(self.table.rowCount()):
            try:
                identifier = self.table.item(row, 0).text()
                size = float(self.table.item(row, 1).text())
                updated = set_reference_size(updated, self.defect_set_id, identifier, size)
            except (AttributeError, ValueError) as exc:
                QMessageBox.warning(self, "Defect Set", str(exc))
                return False
        self.result_state = updated
        parent = self.parent()
        if parent and hasattr(parent, "replace_state"):
            parent.replace_state(updated, "Reference sizes updated")
        return True

    def _accept(self):
        if self._apply():
            self.accept()


class MappingsDialog(QDialog):
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = normalized_sizing_state(state)
        self.result_state = None
        self.setWindowTitle("Mappings")
        self.resize(760, 500)
        root = QVBoxLayout(self)
        form = QHBoxLayout()
        self.target = QComboBox()
        self.reference = QComboBox()
        for item in self.state["defect_sets"]:
            self.target.addItem(item.get("name", "Defect Set"), item.get("id"))
            self.reference.addItem(item.get("name", "Defect Set"), item.get("id"))
        form.addWidget(QLabel("Defect Set"))
        form.addWidget(self.target, 1)
        form.addWidget(QLabel("Reference Defect Set"))
        form.addWidget(self.reference, 1)
        add = QPushButton("Add")
        add.clicked.connect(self._add)
        form.addWidget(add)
        root.addLayout(form)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Map", "Target", "Reference", "Overlay Radius (um)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        root.addWidget(self.table, 1)
        buttons = QHBoxLayout()
        remove = QPushButton("Remove")
        remove.clicked.connect(self._remove)
        buttons.addWidget(remove)
        buttons.addStretch(1)
        ok = QPushButton("OK")
        ok.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        root.addLayout(buttons)
        self._refresh()

    def _refresh(self):
        names = {item.get("id"): item.get("name") for item in self.state["defect_sets"]}
        self.table.setRowCount(len(self.state["maps"]))
        for row, item in enumerate(self.state["maps"]):
            values = (item.get("name"), names.get(item.get("target_set_id"), ""), names.get(item.get("reference_set_id"), ""), item.get("overlay_radius_um", 10.0))
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(str(value)))

    def _add(self):
        if self.target.currentIndex() < 0 or self.reference.currentIndex() < 0:
            QMessageBox.warning(self, "Mappings", "Select both Defect Sets.")
            return
        target_id = self.target.currentData()
        reference_id = self.reference.currentData()
        target = next(item for item in self.state["defect_sets"] if item.get("id") == target_id)
        reference = next(item for item in self.state["defect_sets"] if item.get("id") == reference_id)
        mapping = auto_map_for_set(target, reference_set=reference)
        self.state["maps"].append(mapping)
        self.state["active_map_id"] = mapping["id"]
        self._refresh()

    def _remove(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        identifier = self.state["maps"][rows[0].row()]["id"]
        self.state["maps"] = [item for item in self.state["maps"] if item.get("id") != identifier]
        if self.state.get("active_map_id") == identifier:
            self.state["active_map_id"] = self.state["maps"][-1]["id"] if self.state["maps"] else ""
        self._refresh()

    def _finish(self):
        self.result_state = normalized_sizing_state(self.state)
        self.accept()


class DefectSetCollectionDialog(QDialog):
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = normalized_sizing_state(state)
        self.result_state = None
        self.setWindowTitle("Defect Set Collection")
        self.resize(560, 390)
        root = QVBoxLayout(self)
        self.list = QListWidget()
        root.addWidget(self.list, 1)
        for item in self.state["defect_sets"]:
            self.list.addItem(f"{item.get('name')}   [{item.get('kind')}]   {len(item.get('defects', []))} defects")
        buttons = QHBoxLayout()
        remove = QPushButton("Remove")
        remove.clicked.connect(self._remove)
        buttons.addWidget(remove)
        buttons.addStretch(1)
        ok = QPushButton("OK")
        ok.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        root.addLayout(buttons)

    def _remove(self):
        row = self.list.currentRow()
        if row < 0:
            return
        identifier = self.state["defect_sets"][row]["id"]
        self.state = remove_defect_set(self.state, identifier)
        self.list.takeItem(row)

    def _finish(self):
        self.result_state = normalized_sizing_state(self.state)
        self.accept()


class HistogramDialog(QDialog):
    CUTS_BY_KIND = {
        "Special Case": ("Tall", "Dim"),
        "Size": ("Small", "Large", "Very Large"),
        "Planar": ("Planar",),
    }

    def __init__(self, state, kind="Size", parent=None):
        super().__init__(parent)
        self.state = normalized_sizing_state(state)
        self.kind = kind if kind in self.CUTS_BY_KIND else "Size"
        self.result_recipe = None
        self.setWindowTitle(f"{self.kind} Histogram")
        self.resize(780, 590)
        root = QVBoxLayout(self)
        controls = QHBoxLayout()
        self.cdf = QCheckBox("Cumulative Density Function")
        self.cdf.setChecked(self.state["histogram"]["show_cdf"])
        self.out_of_graph = QCheckBox("Out of Graph Defects")
        self.out_of_graph.setChecked(self.state["histogram"]["show_out_of_graph"])
        controls.addWidget(self.cdf)
        controls.addWidget(self.out_of_graph)
        controls.addStretch(1)
        root.addLayout(controls)
        self.chart = HistogramWidget()
        root.addWidget(self.chart, 1)
        self.sliders = {}
        slider_grid = QGridLayout()
        for row, name in enumerate(self.CUTS_BY_KIND[self.kind]):
            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, 10000)
            value = float(self.state["recipe"]["cut_lines"][name])
            slider.setValue(min(10000, int(value * (100 if self.kind == "Size" else 1))))
            number = QDoubleSpinBox()
            number.setRange(0.0, 1000000.0)
            number.setDecimals(2)
            number.setValue(value)
            slider.valueChanged.connect(lambda current, box=number: box.setValue(current / (100 if self.kind == "Size" else 1)))
            number.valueChanged.connect(lambda current, bar=slider: bar.setValue(min(10000, int(current * (100 if self.kind == "Size" else 1)))))
            slider_grid.addWidget(QLabel(name), row, 0)
            slider_grid.addWidget(slider, row, 1)
            slider_grid.addWidget(number, row, 2)
            self.sliders[name] = number
        root.addLayout(slider_grid)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(self._apply)
        close = QPushButton("Close")
        close.clicked.connect(self.reject)
        buttons.addWidget(apply_button)
        buttons.addWidget(close)
        root.addLayout(buttons)
        self.cdf.toggled.connect(self._refresh_chart)
        self.out_of_graph.toggled.connect(self._refresh_chart)
        self._refresh_chart()

    def _refresh_chart(self):
        self.chart.set_data(histogram_values(self.state, self.kind), self.cdf.isChecked(), self.out_of_graph.isChecked())

    def _apply(self):
        recipe = normalized_sizing_recipe(self.state["recipe"])
        for name, control in self.sliders.items():
            recipe["cut_lines"][name] = control.value()
        errors = validate_sizing_recipe(recipe)
        if errors:
            QMessageBox.warning(self, self.windowTitle(), "\n".join(errors))
            return
        self.result_recipe = recipe
        parent = self.parent()
        if parent and hasattr(parent, "apply_recipe"):
            parent.apply_recipe(recipe)
        self.state["recipe"] = recipe
        self.state["histogram"] = {"kind": self.kind, "show_cdf": self.cdf.isChecked(), "show_out_of_graph": self.out_of_graph.isChecked()}
        self._refresh_chart()


class SizingSetupTool(QDialog):
    def __init__(self, store, initial_result=None, parent=None):
        super().__init__(parent)
        self.store = store
        saved = store.get_preferences().get("sizing_workspace", {}) if store else {}
        self.state = normalized_sizing_state(saved)
        self.setWindowTitle("Sizing Setup Tool")
        self.resize(1180, 760)
        self.setMinimumSize(900, 640)
        root = QVBoxLayout(self)
        root.setContentsMargins(5, 5, 5, 5)
        root.setSpacing(4)
        self.menu_bar = QMenuBar()
        root.setMenuBar(self.menu_bar)
        self._build_menus()
        toolbar = QHBoxLayout()
        self.open_result_button = QPushButton("Open Lot Result")
        self.open_result_button.clicked.connect(self.open_lot_result)
        toolbar.addWidget(self.open_result_button)
        self.edit_recipe_button = QPushButton("Edit Recipe")
        self.edit_recipe_button.clicked.connect(self.open_recipe)
        toolbar.addWidget(self.edit_recipe_button)
        self.histogram_button = QPushButton("Histogram")
        self.histogram_button.clicked.connect(lambda: self.open_histogram("Size"))
        toolbar.addWidget(self.histogram_button)
        toolbar.addWidget(QLabel("Map"))
        self.map_combo = QComboBox()
        self.map_combo.setMinimumWidth(280)
        self.map_combo.currentIndexChanged.connect(self._map_changed)
        toolbar.addWidget(self.map_combo, 1)
        root.addLayout(toolbar)
        options = QHBoxLayout()
        self.nonzero = QCheckBox("Show defects with non-zero reference size only")
        self.nonzero.setChecked(self.state["show_nonzero_only"])
        self.nonzero.toggled.connect(self._options_changed)
        options.addWidget(self.nonzero)
        self.reference_computed = QCheckBox("Use computed size of reference set")
        self.reference_computed.setChecked(self.state["use_reference_computed"])
        self.reference_computed.toggled.connect(self._options_changed)
        options.addWidget(self.reference_computed)
        options.addStretch(1)
        options.addWidget(QLabel("Highlight"))
        self.highlight = QComboBox()
        self.highlight.addItems(["All", *SCALE_GROUPS])
        self.highlight.setCurrentText(self.state["highlight_group"])
        self.highlight.currentTextChanged.connect(self._options_changed)
        options.addWidget(self.highlight)
        root.addLayout(options)
        body = QHBoxLayout()
        self.scatter = ScatterPlotWidget()
        self.scatter.position_changed = self._legend_position_changed
        self.scatter.point_activated = self._edit_point
        body.addWidget(self.scatter, 1)
        side = QVBoxLayout()
        title = QLabel("Sizing Recipe")
        title.setStyleSheet("font-weight: 700; text-decoration: underline;")
        side.addWidget(title)
        self.recipe_summary = QLabel()
        self.recipe_summary.setMinimumWidth(230)
        self.recipe_summary.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        side.addWidget(self.recipe_summary)
        side.addStretch(1)
        body.addLayout(side)
        root.addLayout(body, 1)
        status = QHBoxLayout()
        self.status_label = QLabel(self.state.get("status", "Ready"))
        self.overlayed_label = QLabel("Overlayed: 0")
        self.shown_label = QLabel("Shown: 0")
        self.spec_label = QLabel("Within spec: 0%")
        for label in (self.overlayed_label, self.shown_label, self.spec_label):
            label.setStyleSheet("border-left: 1px solid #99958d; padding-left: 8px; margin-left: 8px;")
        status.addWidget(self.status_label, 1)
        status.addWidget(self.overlayed_label)
        status.addWidget(self.shown_label)
        status.addWidget(self.spec_label)
        root.addLayout(status)
        if initial_result:
            self.add_defect_set(defect_set_from_result(initial_result))
        self.refresh()

    def _build_menus(self):
        file_menu = self.menu_bar.addMenu("File")
        open_menu = file_menu.addMenu("Open")
        open_menu.addAction("Lot Result", self.open_lot_result)
        open_menu.addAction("KLARF", self.open_klarf)
        file_menu.addAction("Save Defect Set", self.save_active_defect_set)
        file_menu.addAction("Save All", self.save_all_defect_sets)
        file_menu.addAction("Export Recipe", self.export_recipe)
        file_menu.addSeparator()
        file_menu.addAction("Close", self.accept)
        edit_menu = self.menu_bar.addMenu("Edit")
        edit_menu.addAction("Defects", self.open_defects)
        edit_menu.addAction("Maps", self.open_maps)
        edit_menu.addAction("Overlay Radius", self.edit_overlay_radius)
        edit_menu.addAction("Recipe", self.open_recipe)
        edit_menu.addAction("Defect Set Collection", self.open_defect_sets)
        view_menu = self.menu_bar.addMenu("View")
        view_menu.addAction("Scatter Plot", self.refresh)
        view_menu.addAction("Special Case Histogram", lambda: self.open_histogram("Special Case"))
        view_menu.addAction("Size Histogram", lambda: self.open_histogram("Size"))
        view_menu.addAction("Planar Histogram", lambda: self.open_histogram("Planar"))
        tools_menu = self.menu_bar.addMenu("Tools")
        tools_menu.addAction("Import Reference Size", self.import_reference_size_file)
        tools_menu.addAction("Transfer Size from Reference Set", self.transfer_sizes)
        tools_menu.addAction("Consolidate Lotresult", self.consolidate_results)

    def add_defect_set(self, defect_set):
        pending_klarf = next((item for item in reversed(self.state["defect_sets"]) if item.get("kind") == "KLARF"), None)
        self.state["defect_sets"].append(deepcopy(defect_set))
        reference = pending_klarf if defect_set.get("kind") == "Lot Result" and pending_klarf else defect_set
        mapping = auto_map_for_set(defect_set, reference_set=reference)
        self.state["maps"].append(mapping)
        self.state["active_map_id"] = mapping["id"]
        self.replace_state(self.state, f"Loaded {defect_set.get('name')}")

    def replace_state(self, state, status="Ready"):
        self.state = normalized_sizing_state(state)
        self.state["status"] = status
        self._persist()
        self.refresh()

    def _persist(self):
        if self.store:
            self.store.update_preferences({"sizing_workspace": deepcopy(self.state)})

    def refresh(self):
        current = self.state.get("active_map_id", "")
        self.map_combo.blockSignals(True)
        self.map_combo.clear()
        for mapping in self.state["maps"]:
            self.map_combo.addItem(mapping.get("name", "Map"), mapping.get("id"))
        index = self.map_combo.findData(current)
        if index >= 0:
            self.map_combo.setCurrentIndex(index)
        self.map_combo.blockSignals(False)
        mapping = active_map(self.state)
        reference = next((item for item in self.state["defect_sets"] if mapping and item.get("id") == mapping.get("reference_set_id")), None)
        self.reference_computed.setEnabled(bool(reference and reference.get("kind") == "Lot Result"))
        if not self.reference_computed.isEnabled():
            self.reference_computed.setChecked(False)
            self.state["use_reference_computed"] = False
        points = scatter_points(self.state)
        self.scatter.set_data(points, highlight_group=self.state["highlight_group"], legend_position=self.state["legend_position"])
        stats = scatter_statistics(points)
        self.overlayed_label.setText(f"Overlayed: {stats['overlayed']}")
        self.shown_label.setText(f"Shown: {stats['shown']}")
        self.spec_label.setText(f"Within spec: {stats['within_spec_percent']:.1f}%")
        self.status_label.setText(self.state.get("status", "Ready"))
        recipe = self.state["recipe"]
        factor_text = "\n".join(f"{name:<8} {recipe['scale_factors'][name]:.3f}" for name in SCALE_GROUPS)
        cut_text = "\n".join(f"{name:<10} {value:g}" for name, value in recipe["cut_lines"].items())
        self.recipe_summary.setText(f"Scale Factors\n{factor_text}\n\nCut Lines\n{cut_text}")

    def _map_changed(self, index):
        identifier = self.map_combo.itemData(index)
        if identifier:
            self.state["active_map_id"] = identifier
            self.state["status"] = f"Active map: {self.map_combo.currentText()}"
            self._persist()
            self.refresh()

    def _options_changed(self, *args):
        self.state["show_nonzero_only"] = self.nonzero.isChecked()
        self.state["use_reference_computed"] = self.reference_computed.isChecked() and self.reference_computed.isEnabled()
        self.state["highlight_group"] = self.highlight.currentText()
        self._persist()
        self.refresh()

    def _legend_position_changed(self, position):
        self.state["legend_position"] = position
        self._persist()

    def open_lot_result(self):
        results = self.store.list_results() if self.store else []
        if not results:
            QMessageBox.information(self, "Read Lot Result", "No stored lot results are available.")
            return
        dialog = LotResultReaderDialog(results, self)
        if (dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()) == QDialog.Accepted and dialog.selected_set:
            self.add_defect_set(dialog.selected_set)

    def open_klarf(self):
        filename, _selected = QFileDialog.getOpenFileName(self, "Open KLARF", "", "KLARF Files (*.klarf *.001 *.txt);;All Files (*)")
        if not filename:
            return
        options = KlarfOptionsDialog(filename, self)
        if (options.exec() if hasattr(options, "exec") else options.exec_()) != QDialog.Accepted:
            return
        try:
            text = Path(filename).read_text(encoding="utf-8", errors="replace")
            result = import_klarf_text(text, {}, source_path=filename)
            defect_set = defect_set_from_klarf_result(result, name=options.name.text(), size_field=options.field.currentText(), class_multiplier=options.multiplier.value())
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "KLARF Reader", str(exc))
            return
        self.add_defect_set(defect_set)

    def open_recipe(self):
        dialog = SizingRecipeDialog(self.state["recipe"], self)
        dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()

    def apply_recipe(self, recipe):
        self.state["recipe"] = normalized_sizing_recipe(recipe)
        self.replace_state(self.state, "Sizing recipe applied to active map")

    def open_defects(self, initial_id=None):
        mapping = active_map(self.state)
        if not mapping:
            QMessageBox.information(self, "Defect Set", "Load a lot result and select a map first.")
            return
        dialog = DefectSetEditorDialog(self.state, mapping["target_set_id"], initial_id, self)
        dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()

    def _edit_point(self, point):
        self.open_defects(point.get("target_id"))

    def open_maps(self):
        dialog = MappingsDialog(self.state, self)
        if (dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()) == QDialog.Accepted and dialog.result_state:
            self.replace_state(dialog.result_state, "Mappings updated")

    def edit_overlay_radius(self):
        mapping = active_map(self.state)
        if not mapping:
            QMessageBox.information(self, "Overlay Radius", "Select a map first.")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Overlay Radius")
        layout = QVBoxLayout(dialog)
        radius = QDoubleSpinBox()
        radius.setRange(0.0, 1000000.0)
        radius.setDecimals(3)
        radius.setSuffix(" um")
        radius.setValue(float(mapping.get("overlay_radius_um", 10.0)))
        layout.addWidget(QLabel("Radius"))
        layout.addWidget(radius)
        buttons = QHBoxLayout()
        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(dialog.accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(dialog.reject)
        buttons.addStretch(1)
        buttons.addWidget(apply_button)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)
        if (dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()) == QDialog.Accepted:
            mapping["overlay_radius_um"] = radius.value()
            self.replace_state(self.state, f"Overlay radius set to {radius.value():g} um")

    def open_defect_sets(self):
        dialog = DefectSetCollectionDialog(self.state, self)
        if (dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()) == QDialog.Accepted and dialog.result_state:
            self.replace_state(dialog.result_state, "Defect Set Collection updated")

    def open_histogram(self, kind):
        if not active_map(self.state):
            QMessageBox.information(self, f"{kind} Histogram", "Select a map first.")
            return
        dialog = HistogramDialog(self.state, kind, self)
        dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()

    def import_reference_size_file(self):
        mapping = active_map(self.state)
        if not mapping:
            QMessageBox.information(self, "Import Reference Size", "Select a map first.")
            return
        filename, _selected = QFileDialog.getOpenFileName(self, "Import Reference Size", "", "Text Files (*.txt *.tsv *.csv);;All Files (*)")
        if not filename:
            return
        try:
            text = Path(filename).read_text(encoding="utf-8", errors="replace")
            updated, report = import_reference_sizes(self.state, mapping["target_set_id"], text)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Import Reference Size", str(exc))
            return
        self.replace_state(updated, f"Imported {report['applied']} reference size(s); ignored {report['ignored']}")

    def transfer_sizes(self):
        try:
            updated = transfer_reference_sizes(self.state)
        except ValueError as exc:
            QMessageBox.warning(self, "Transfer Size", str(exc))
            return
        self.replace_state(updated, "Reference sizes transferred to target Defect Set")

    def save_active_defect_set(self):
        mapping = active_map(self.state)
        if not mapping:
            QMessageBox.information(self, "Save Defect Set", "Select a map first.")
            return
        defect_set = next(item for item in self.state["defect_sets"] if item.get("id") == mapping["target_set_id"])
        defect_set["saved"] = True
        self._save_defect_set_to_source(defect_set)
        self.replace_state(self.state, f"Saved Defect Set {defect_set.get('name')}")

    def save_all_defect_sets(self):
        for item in self.state["defect_sets"]:
            item["saved"] = True
            self._save_defect_set_to_source(item)
        self.replace_state(self.state, f"Saved {len(self.state['defect_sets'])} Defect Set(s)")

    def _save_defect_set_to_source(self, defect_set):
        source_id = defect_set.get("source_id")
        if not self.store or not source_id:
            return
        source = self.store.get_result(source_id)
        if not source:
            return
        by_id = {str(item.get("id")): item for item in defect_set.get("defects", [])}
        for defect in source.get("defects", []):
            sized = by_id.get(str(defect.get("id")))
            if sized:
                defect["reference_size_um"] = sized.get("reference_size_um", 0.0)
                defect["computed_size_um"] = sized.get("computed_size_um", defect.get("size_um", 0.0))
        self.store.save_result(source)

    def export_recipe(self):
        filename, _selected = QFileDialog.getSaveFileName(self, "Export Sizing Recipe", "SizingRecipe.xml", "XML Files (*.xml)")
        if not filename:
            return
        try:
            Path(filename).write_text(export_sizing_recipe_xml(self.state["recipe"]), encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(self, "Export Sizing Recipe", str(exc))
            return
        self.replace_state(self.state, f"Sizing recipe exported to {filename}")

    def consolidate_results(self):
        results = self.store.list_results() if self.store else []
        lots = sorted({str(item.get("lot_id", "")) for item in results if item.get("lot_id")})
        if not lots:
            QMessageBox.information(self, "Consolidate Lotresult", "No lot results are available.")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Lot Result to Consolidate")
        layout = QVBoxLayout(dialog)
        lot = QComboBox()
        lot.addItems(lots)
        layout.addWidget(QLabel("Lot Result"))
        layout.addWidget(lot)
        buttons = QHBoxLayout()
        ok = QPushButton("Consolidate")
        ok.clicked.connect(dialog.accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(dialog.reject)
        buttons.addStretch(1)
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)
        if (dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()) != QDialog.Accepted:
            return
        selected = [item for item in results if str(item.get("lot_id", "")) == lot.currentText()]
        try:
            consolidated, _transformations = consolidate_lot_results(selected)
        except ValueError as exc:
            QMessageBox.warning(self, "Consolidate Lotresult", str(exc))
            return
        saved = self.store.overwrite_results([item.get("id") for item in selected], [consolidated], backup=True)
        self.add_defect_set(defect_set_from_result(saved[0], name=f"{lot.currentText()} Consolidated"))
        self.state["status"] = f"Consolidated {len(selected)} wafer result(s) into {saved[0].get('wafer_id')}"
        self._persist()
        self.refresh()

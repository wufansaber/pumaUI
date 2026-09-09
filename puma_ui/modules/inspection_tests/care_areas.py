from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from ...qt_compat import (
    QAbstractItemView,
    QCheckBox,
    QColor,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPainter,
    QPen,
    QPushButton,
    QSlider,
    QSplitter,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    Qt,
    QVBoxLayout,
    QWidget,
)


GROUP_COLORS = ["#20b9ca", "#e2b313", "#dc5c74", "#7bcb55", "#8f76d7", "#e88432"]


def care_area_file_metadata(path: str) -> dict:
    file_path = Path(path)
    fallback = {"Current Step": [file_path.stem or "Imported CAG"]}
    try:
        if file_path.suffix.lower() == ".json":
            payload = json.loads(file_path.read_text(encoding="utf-8"))
            steps = payload.get("inspection_steps") or payload.get("steps")
            if isinstance(steps, dict):
                result = {}
                for step, groups in steps.items():
                    values = groups.get("groups", groups) if isinstance(groups, dict) else groups
                    result[str(step)] = [
                        str(item.get("name", "")).strip() if isinstance(item, dict) else str(item).strip()
                        for item in (values or [])
                    ]
                result = {key: [name for name in value if name] for key, value in result.items()}
                if any(result.values()):
                    return result
            groups = payload.get("groups") or payload.get("cags") or []
            names = [
                str(item.get("name", "")).strip() if isinstance(item, dict) else str(item).strip()
                for item in groups
            ]
            names = [name for name in names if name]
            return {str(payload.get("inspection_step") or "Current Step"): names} if names else fallback
        if file_path.suffix.lower() == ".xml":
            root = ET.parse(file_path).getroot()
            result = {}
            for element in root.iter():
                tag = element.tag.rsplit("}", 1)[-1].lower()
                if "cag" not in tag and "careareagroup" not in tag:
                    continue
                name = str(element.get("name") or element.get("id") or "").strip()
                if not name:
                    continue
                step = str(element.get("step") or element.get("inspectionStep") or "Current Step")
                result.setdefault(step, []).append(name)
            return result or fallback
    except (OSError, ValueError, ET.ParseError, TypeError):
        return fallback
    return fallback


def default_care_area_state() -> dict:
    return {
        "selected_die": [0, 0],
        "groups": [],
        "thresholds": [{
            "name": "Default",
            "algorithm": "HLAT",
            "channels": [1, 2, 3],
            "minimum_size": 0.12,
            "threshold": 45.0,
        }],
        "border": {"x": 2.0, "y": 2.0},
        "die_size_um": [5100.0, 16600.0],
        "always_use_default_expansion_order": True,
        "expansion_order": ["Default"],
        "image_opacity": 65,
        "setup_review_defects": [],
    }


def normalized_care_area_state(state: dict | None) -> dict:
    result = default_care_area_state()
    if isinstance(state, dict):
        result.update(deepcopy(state))
    result["groups"] = deepcopy(result.get("groups") or [])
    result["thresholds"] = deepcopy(result.get("thresholds") or default_care_area_state()["thresholds"])
    names = [item["name"] for item in result["thresholds"]]
    order = [name for name in result.get("expansion_order", []) if name in names]
    result["expansion_order"] = order + [name for name in names if name not in order]
    refresh_derived_groups(result["groups"])
    return result


def apply_care_area_offset(
    groups,
    indexes,
    offset_x_um,
    offset_y_um,
    die_size_um=(5100.0, 16600.0),
):
    try:
        die_width_um, die_height_um = [float(value) for value in die_size_um[:2]]
    except (TypeError, ValueError):
        raise ValueError("die size must contain numeric X and Y dimensions") from None
    if die_width_um <= 0 or die_height_um <= 0:
        raise ValueError("die size must be greater than zero")
    offset_x = float(offset_x_um) / die_width_um
    offset_y = float(offset_y_um) / die_height_um
    result = deepcopy(groups)
    for index in indexes:
        if not 0 <= index < len(result):
            continue
        moved = []
        for area in result[index].get("areas", []):
            x, y, width, height = area[:4]
            nx = float(x) + float(offset_x)
            ny = float(y) + float(offset_y)
            if nx < 0 or ny < 0 or nx + width > 1 or ny + height > 1:
                raise ValueError("offset moves a Care Area outside the die")
            moved.append([nx, ny, width, height] + list(area[4:]))
        result[index]["areas"] = moved
        result[index]["offset"] = [
            float(result[index].get("offset", [0, 0])[0]) + float(offset_x),
            float(result[index].get("offset", [0, 0])[1]) + float(offset_y),
        ]
        previous_um = result[index].get("offset_um", [0, 0])
        result[index]["offset_um"] = [
            float(previous_um[0]) + float(offset_x_um),
            float(previous_um[1]) + float(offset_y_um),
        ]
    return result


def grow_shrink_areas(areas, margins):
    left, top, right, bottom = [float(value) for value in margins]
    result = []
    for area in areas:
        x, y, width, height = [float(value) for value in area[:4]]
        nx = max(0.0, x - left)
        ny = max(0.0, y - top)
        end_x = min(1.0, x + width + right)
        end_y = min(1.0, y + height + bottom)
        if end_x > nx and end_y > ny:
            result.append([nx, ny, end_x - nx, end_y - ny] + list(area[4:]))
    return result


def intersect_care_areas(first, second):
    result = []
    for left in first:
        ax, ay, aw, ah = [float(value) for value in left[:4]]
        for right in second:
            bx, by, bw, bh = [float(value) for value in right[:4]]
            x = max(ax, bx)
            y = max(ay, by)
            end_x = min(ax + aw, bx + bw)
            end_y = min(ay + ah, by + bh)
            if end_x > x and end_y > y:
                result.append([x, y, end_x - x, end_y - y])
    return result


def refresh_derived_groups(groups):
    by_name = {group.get("name"): group for group in groups}
    for _ in range(len(groups)):
        changed = False
        for group in groups:
            operation = group.get("derived_operation")
            parents = [by_name.get(name) for name in group.get("parents", [])]
            if operation == "grow_shrink" and parents and parents[0]:
                areas = grow_shrink_areas(
                    parents[0].get("areas", []),
                    group.get("margins", [0, 0, 0, 0]),
                )
            elif operation == "intersection" and len(parents) == 2 and all(parents):
                areas = intersect_care_areas(
                    parents[0].get("areas", []), parents[1].get("areas", [])
                )
            else:
                continue
            if areas != group.get("areas", []):
                group["areas"] = areas
                changed = True
        if not changed:
            break


def delete_groups_with_descendants(groups, indexes):
    remove_names = {
        groups[index].get("name")
        for index in indexes
        if 0 <= index < len(groups)
    }
    changed = True
    while changed:
        changed = False
        for group in groups:
            if group.get("name") in remove_names:
                continue
            parents = list(group.get("parents", []))
            if group.get("parent"):
                parents.append(group.get("parent"))
            if any(parent in remove_names for parent in parents):
                remove_names.add(group.get("name"))
                changed = True
    return [group for group in groups if group.get("name") not in remove_names]


def generate_page_break_groups(search_area, training_area, parent_name="ACA"):
    sx, sy, sw, sh = [float(value) for value in search_area]
    tx, ty, tw, th = [float(value) for value in training_area]
    if sw <= 0 or sh <= 0 or tw <= 0 or th <= 0:
        raise ValueError("search and training areas must have positive dimensions")
    if tx < sx or ty < sy or tx + tw > sx + sw or ty + th > sy + sh:
        raise ValueError("training area must remain inside the ACA search area")
    thickness = min(0.01, tw / 8, th / 8)
    vertical = []
    x = tx + tw
    while x < sx + sw - thickness:
        vertical.append([x, sy, thickness, sh])
        x += tw
    horizontal = []
    y = ty + th
    while y < sy + sh - thickness:
        horizontal.append([sx, y, sw, thickness])
        y += th
    common = {
        "threshold": "Default",
        "status": "OK",
        "enabled": True,
        "show": True,
        "registered": True,
        "verified": True,
        "parent": parent_name,
    }
    return [
        {
            **common,
            "name": f"{parent_name} Horizontal Page Break",
            "kind": "Horizontal Page Break",
            "cag_code": 0,
            "areas": horizontal,
        },
        {
            **common,
            "name": f"{parent_name} Vertical Page Break",
            "kind": "Vertical Page Break",
            "cag_code": 0,
            "areas": vertical,
        },
    ]


def is_page_break_group(group):
    return group.get("kind") in {"Horizontal Page Break", "Vertical Page Break"}


def move_page_break(groups, source_index, area_index, target_index=None):
    result = deepcopy(groups)
    if not 0 <= source_index < len(result) or not is_page_break_group(result[source_index]):
        raise ValueError("select a Horizontal or Vertical Page Break group")
    source = result[source_index]
    areas = source.get("areas", [])
    if not 0 <= area_index < len(areas):
        raise ValueError("select a Page Break to move")
    if target_index is None:
        matching = sum(1 for item in result if item.get("kind") == source.get("kind")) + 1
        target = deepcopy(source)
        target["name"] = f"{source['kind']} {matching}"
        target["areas"] = []
        result.append(target)
        target_index = len(result) - 1
    if not 0 <= target_index < len(result) or target_index == source_index:
        raise ValueError("select a different Page Break group")
    target = result[target_index]
    if target.get("kind") != source.get("kind"):
        raise ValueError("Page Breaks can only move between groups of the same orientation")
    target.setdefault("areas", []).append(areas.pop(area_index))
    return result, target_index


def repeat_page_break(areas, search_area=None):
    result = deepcopy(areas)
    if len(result) < 2:
        raise ValueError("create two Page Breaks before using Repeat Page Break")
    previous, current = result[-2][:4], result[-1][:4]
    candidate = [
        float(current[0]) + float(current[0]) - float(previous[0]),
        float(current[1]) + float(current[1]) - float(previous[1]),
        float(current[2]),
        float(current[3]),
    ]
    bx, by, bw, bh = [float(value) for value in (search_area or [0, 0, 1, 1])]
    if (
        candidate[0] < bx
        or candidate[1] < by
        or candidate[0] + candidate[2] > bx + bw
        or candidate[1] + candidate[3] > by + bh
    ):
        raise ValueError("repeated Page Break falls outside the ACA search area")
    result.append(candidate)
    return result


def sort_page_break_groups(groups, indexes, separation_um, die_size_um=(5100.0, 16600.0)):
    result = deepcopy(groups)
    selected = sorted({int(index) for index in indexes})
    if not selected or any(not 0 <= index < len(result) for index in selected):
        raise ValueError("select at least one Page Break group")
    source_groups = [result[index] for index in selected]
    if any(not is_page_break_group(group) for group in source_groups):
        raise ValueError("only Page Break groups can be sorted")
    kind = source_groups[0].get("kind")
    if any(group.get("kind") != kind for group in source_groups):
        raise ValueError("sort Horizontal and Vertical Page Break groups separately")
    dimension = float(die_size_um[0] if kind == "Vertical Page Break" else die_size_um[1])
    if dimension <= 0 or float(separation_um) < 0:
        raise ValueError("enter a valid Page Break size separation")
    axis = 2 if kind == "Vertical Page Break" else 3
    tolerance = float(separation_um) / dimension
    areas = sorted(
        (deepcopy(area) for group in source_groups for area in group.get("areas", [])),
        key=lambda area: float(area[axis]),
    )
    bins = []
    for area in areas:
        if not bins or abs(float(area[axis]) - float(bins[-1][0][axis])) > tolerance:
            bins.append([area])
        else:
            bins[-1].append(area)
    insert_at = selected[0]
    for index in reversed(selected):
        result.pop(index)
    base = deepcopy(source_groups[0])
    replacements = []
    for number, grouped_areas in enumerate(bins, start=1):
        group = deepcopy(base)
        group["name"] = f"{kind} {number}"
        group["areas"] = grouped_areas
        replacements.append(group)
    result[insert_at:insert_at] = replacements
    return result


def combine_page_break_groups(groups, indexes, group_numbers):
    result = deepcopy(groups)
    selected = sorted({int(index) for index in indexes})
    if not selected or any(not 0 <= index < len(result) for index in selected):
        raise ValueError("select at least one Page Break group")
    source_groups = [result[index] for index in selected]
    if any(not is_page_break_group(group) for group in source_groups):
        raise ValueError("only Page Break groups can be combined")
    kind = source_groups[0].get("kind")
    if any(group.get("kind") != kind for group in source_groups):
        raise ValueError("combine Horizontal and Vertical Page Break groups separately")

    buckets = {}
    for index, group in zip(selected, source_groups):
        number = max(1, int(group_numbers.get(index, 1)))
        buckets.setdefault(number, []).append(group)

    insert_at = selected[0]
    for index in reversed(selected):
        result.pop(index)
    replacements = []
    for number in sorted(buckets):
        combined = deepcopy(buckets[number][0])
        combined["name"] = f"{kind} {number}"
        combined["areas"] = [
            deepcopy(area)
            for group in buckets[number]
            for area in group.get("areas", [])
        ]
        replacements.append(combined)
    result[insert_at:insert_at] = replacements
    return result


def care_area_coverage_report(groups):
    report = []
    for group in groups:
        defined = sum(float(area[2]) * float(area[3]) for area in group.get("areas", []))
        border_loss = min(defined, len(group.get("areas", [])) * 0.0004)
        inspected = max(0.0, defined - border_loss)
        report.append(
            {
                "name": group.get("name", "Care Area"),
                "defined_percent": min(100.0, defined * 100),
                "inspected_percent": min(100.0, inspected * 100),
            }
        )
    return report


class SetupReviewDefectsDialog(QDialog):
    def __init__(self, defects, previous=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Setup-Review - Defect Data")
        self.resize(700, 430)
        previous_marks = {
            int(item.get("id", 0)): bool(item.get("marked"))
            for item in (previous or [])
        }
        self.defects = deepcopy(defects)
        self.result_defects = []
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Marked", "Defect ID", "X", "Y", "Class Code"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for defect in self.defects:
            row = self.table.rowCount()
            self.table.insertRow(row)
            mark = QTableWidgetItem("")
            mark.setCheckState(
                Qt.Checked if previous_marks.get(int(defect.get("id", 0)), False) else Qt.Unchecked
            )
            self.table.setItem(row, 0, mark)
            for column, key in enumerate(("id", "x", "y", "class_code"), start=1):
                self.table.setItem(row, column, QTableWidgetItem(str(defect.get(key, ""))))
        if self.table.rowCount():
            self.table.selectRow(0)
        layout.addWidget(self.table, 1)
        buttons = QHBoxLayout()
        mark_selected = QPushButton("Mark Selected Defects")
        mark_selected.clicked.connect(lambda: self._set_selected_mark(True))
        clear_marks = QPushButton("Clear Marks")
        clear_marks.clicked.connect(self._clear_marks)
        finish = QPushButton("End")
        finish.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(mark_selected)
        buttons.addWidget(clear_marks)
        buttons.addStretch(1)
        buttons.addWidget(finish)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)

    def _set_selected_mark(self, marked: bool):
        for model_index in self.table.selectionModel().selectedRows():
            self.table.item(model_index.row(), 0).setCheckState(
                Qt.Checked if marked else Qt.Unchecked
            )

    def _clear_marks(self):
        for row in range(self.table.rowCount()):
            self.table.item(row, 0).setCheckState(Qt.Unchecked)

    def _finish(self):
        self.result_defects = []
        for row, defect in enumerate(self.defects):
            item = deepcopy(defect)
            item["marked"] = self.table.item(row, 0).checkState() == Qt.Checked
            self.result_defects.append(item)
        self.accept()


class CareAreasDialog(QDialog):
    def __init__(
        self,
        state=None,
        *,
        can_overwrite=False,
        test_mode="Random",
        defect_data=None,
        wafer_aligned=False,
        parent=None,
    ):
        super().__init__(parent)
        self.state = normalized_care_area_state(state)
        self.test_mode = test_mode
        self.defect_data = deepcopy(defect_data or {})
        self.wafer_aligned = bool(wafer_aligned)
        self.result_state = None
        self.overwrite_all = False
        self.changed = False
        self.active_group = -1
        self.group_clipboard = None
        self.area_started = False
        self._loading = False
        self.setWindowTitle("Care Areas")
        self.resize(1320, 790)
        self.setMinimumSize(1050, 650)
        self.setStyleSheet(
            "QDialog { background: #cfcbc2; font-family: Arial; font-size: 10px; }"
            "QPushButton { background: #e8e6dd; border: 1px solid #77736b; min-height: 26px; padding: 2px 7px; }"
            "QTableWidget { background: #f0efeb; gridline-color: #aaa69d; }"
            "QHeaderView::section { background: #dad7cf; border: 1px solid #9a968d; padding: 3px; }"
            "QFrame#pane { border: 1px solid #8c8982; background: #ddd9d0; }"
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        self.panes = QSplitter(Qt.Horizontal)
        self.panes.addWidget(self._die_view())
        self.panes.addWidget(self._groups_pane())
        self.panes.addWidget(self._sensitivity_pane())
        self.panes.setSizes([520, 420, 320])
        root.addWidget(self.panes, 1)
        footer = QHBoxLayout()
        self.info = QLabel("Select a Care Area type, then drag over the Die View.")
        footer.addWidget(self.info, 1)
        overwrite = QPushButton("Finish && Overwrite All Tests")
        overwrite.setEnabled(can_overwrite)
        overwrite.clicked.connect(lambda: self._finish(True))
        finish = QPushButton("Finish")
        finish.clicked.connect(lambda: self._finish(False))
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        footer.addWidget(overwrite)
        footer.addWidget(finish)
        footer.addWidget(cancel)
        root.addLayout(footer)
        self._refresh()

    def _die_view(self):
        pane = QFrame()
        pane.setObjectName("pane")
        layout = QVBoxLayout(pane)
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Die View"))
        zoom_out = QPushButton("-")
        zoom_out.setToolTip("Zoom out")
        toolbar.addWidget(zoom_out)
        self.zoom = QSlider(Qt.Horizontal)
        self.zoom.setRange(25, 300)
        self.zoom.setValue(100)
        toolbar.addWidget(self.zoom, 1)
        zoom_in = QPushButton("+")
        zoom_in.setToolTip("Zoom in")
        toolbar.addWidget(zoom_in)
        fit = QPushButton("Fit")
        toolbar.addWidget(fit)
        acquire = QPushButton("Acquire")
        acquire.setToolTip("Acquire MacroView image")
        toolbar.addWidget(acquire)
        self.measure_button = QPushButton("Measure")
        self.measure_button.setCheckable(True)
        self.measure_button.setToolTip("Measuring Tape Tool")
        self.measure_button.toggled.connect(self._toggle_measurement)
        toolbar.addWidget(self.measure_button)
        self.show_button = QPushButton("Show")
        show_menu = QMenu(self.show_button)
        self.show_rulers_action = show_menu.addAction("Show rulers")
        self.show_rulers_action.setCheckable(True)
        self.show_rulers_action.setChecked(True)
        self.show_tooltips_action = show_menu.addAction("Show position tool tips")
        self.show_tooltips_action.setCheckable(True)
        self.show_tooltips_action.setChecked(True)
        self.show_info_action = show_menu.addAction("Show information bar")
        self.show_info_action.setCheckable(True)
        self.show_info_action.setChecked(True)
        self.show_image_action = show_menu.addAction("Show Die Image")
        self.show_image_action.setCheckable(True)
        self.show_image_action.setChecked(True)
        self.show_care_areas_action = show_menu.addAction("Show Care Areas")
        self.show_care_areas_action.setCheckable(True)
        self.show_care_areas_action.setChecked(True)
        opacity_menu = show_menu.addMenu("Care Area Opacity")
        for opacity in (25, 50, 75, 100):
            opacity_menu.addAction(f"{opacity}%", lambda checked=False, value=opacity: self._set_layer_opacity(value))
        self.show_image_action.toggled.connect(self._set_image_visibility)
        self.show_care_areas_action.toggled.connect(self._set_care_area_visibility)
        self.show_info_action.toggled.connect(lambda visible: self.info.setVisible(visible))
        self.show_button.setMenu(show_menu)
        toolbar.addWidget(self.show_button)
        self.review_button = QPushButton("Review")
        self.review_button.setEnabled(bool(self.defect_data) and self.wafer_aligned)
        if not self.defect_data:
            self.review_button.setToolTip("Attach defect data before opening Setup-Review.")
        elif not self.wafer_aligned:
            self.review_button.setToolTip("Align the wafer before opening Setup-Review.")
        self.review_button.clicked.connect(self._open_setup_review)
        toolbar.addWidget(self.review_button)
        layout.addLayout(toolbar)
        self.canvas = CareAreaCanvas(
            self.state,
            self._area_added,
            self._area_selected,
            self._measurement_completed,
        )
        self.zoom.valueChanged.connect(self.canvas.set_zoom)
        zoom_out.clicked.connect(lambda: self.zoom.setValue(self.zoom.value() - 10))
        zoom_in.clicked.connect(lambda: self.zoom.setValue(self.zoom.value() + 10))
        fit.clicked.connect(lambda: self.zoom.setValue(100))
        acquire.clicked.connect(self._acquire)
        layout.addWidget(self.canvas, 1)
        edit = QHBoxLayout()
        self.start_dca = QCheckBox("Start Area Begins a new Don't Care Area")
        edit.addWidget(self.start_dca)
        self.start_area_button = QPushButton("Start Area")
        self.start_area_button.clicked.connect(self._start_area)
        self.finish_area_button = QPushButton("Finish Area")
        self.finish_area_button.setEnabled(False)
        self.finish_area_button.clicked.connect(self._finish_area)
        edit.addWidget(self.start_area_button)
        edit.addWidget(self.finish_area_button)
        edit.addStretch(1)
        for label, handler in [
            ("Fill", self._fill),
            ("No Fill", self._no_fill),
            ("Undo", self._undo),
            ("Redo", self._redo),
        ]:
            button = QPushButton(label)
            button.clicked.connect(handler)
            edit.addWidget(button)
        layout.addLayout(edit)
        return pane

    def _groups_pane(self):
        pane = QFrame()
        pane.setObjectName("pane")
        layout = QVBoxLayout(pane)
        layout.addWidget(QLabel("Care Area Groups"))
        commands = QGridLayout()
        actions = [
            ("CA", lambda: self._new_group("CA")),
            ("DCA", lambda: self._new_group("DCA")),
            ("ACA", self._new_auto_group),
            ("Derived", self._derived_group),
            ("Hot Spots", self._hot_spots),
            ("Entire Die", self._entire_die),
            ("Delete", self._delete_group),
            ("Cut", self._cut_group),
            ("Copy", self._copy_group),
            ("Paste", self._paste_group),
            ("Register", self._register_group),
            ("Verify", self._verify_group),
            ("Import", self._import_group),
            ("Apply Offset", self._apply_offset),
            ("Page Breaks", self._edit_page_breaks),
            ("Sort PB", self._sort_page_breaks),
            ("CAG Report", self._show_cag_report),
            ("Promote", lambda: self._move_group(-1)),
            ("Demote", lambda: self._move_group(1)),
            ("More...", self._more),
        ]
        for index, (label, handler) in enumerate(actions):
            button = QPushButton(label)
            button.clicked.connect(handler)
            commands.addWidget(button, index // 4, index % 4)
        layout.addLayout(commands)
        self.groups = QTableWidget(0, 7)
        self.groups.setHorizontalHeaderLabels(
            ["Name", "Threshold", "Status", "Enabled", "CAG Code", "Show", "Count"]
        )
        self.groups.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.groups.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.groups.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.groups.setContextMenuPolicy(Qt.CustomContextMenu)
        self.groups.customContextMenuRequested.connect(self._show_group_menu)
        self.groups.itemSelectionChanged.connect(self._group_selected)
        self.groups.itemChanged.connect(self._group_item_changed)
        self.group_tabs = QTabWidget()
        self.group_tabs.addTab(self.groups, "Care Areas")
        self.advanced_groups = QTableWidget(0, 3)
        self.advanced_groups.setHorizontalHeaderLabels(["Name", "Threshold", "PDA Care Area"])
        self.advanced_groups.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.advanced_groups.itemChanged.connect(self._advanced_group_changed)
        self.group_tabs.addTab(self.advanced_groups, "Advanced")
        layout.addWidget(self.group_tabs, 1)
        return pane

    def _start_area(self):
        if self.active_group < 0:
            QMessageBox.information(self, "Start Area", "Create or select a Care Area Group first.")
            return
        self.area_started = True
        self.canvas.drawing_enabled = True
        self.measure_button.setChecked(False)
        self.start_area_button.setEnabled(False)
        self.finish_area_button.setEnabled(True)
        self.info.setText("Start Area marked. Drag from the upper-left to the lower-right corner, then click Finish Area.")

    def _finish_area(self):
        if not self.area_started:
            return
        self.area_started = False
        self.canvas.drawing_enabled = False
        self.start_area_button.setEnabled(True)
        self.finish_area_button.setEnabled(False)
        self.info.setText("Finish Area stored. Click Start Area to define another region or Finish to return to Tests.")

    def _toggle_measurement(self, enabled):
        self.canvas.measurement_enabled = bool(enabled)
        if enabled:
            self.canvas.drawing_enabled = False
            self.info.setText("Measuring Tape active. Drag across the Die View to measure.")
        elif self.area_started:
            self.canvas.drawing_enabled = True
        self.canvas.update()

    def _measurement_completed(self, start, end):
        width = abs(end[0] - start[0]) * self.state["die_size_um"][0]
        height = abs(end[1] - start[1]) * self.state["die_size_um"][1]
        distance = (width ** 2 + height ** 2) ** 0.5
        import math
        angle = math.degrees(math.atan2(height, width)) if distance else 0.0
        self.info.setText(
            f"Height {height:.2f} um | Width {width:.2f} um | Area {width * height:.2f} um2 | "
            f"Distance {distance:.2f} um | Angle {angle:.1f} deg"
        )

    def _set_image_visibility(self, visible):
        self.canvas.show_image = bool(visible)
        self.canvas.update()

    def _set_care_area_visibility(self, visible):
        for group in self.state["groups"]:
            group["show"] = bool(visible)
        self._refresh()

    def _set_layer_opacity(self, value):
        self.state["image_opacity"] = int(value)
        self.canvas.update()

    def _open_setup_review(self):
        defects = self.defect_data.get("defects") or [
            {"id": 1, "x": 0.25, "y": 0.25, "class_code": 0},
            {"id": 2, "x": 0.50, "y": 0.50, "class_code": 0},
            {"id": 3, "x": 0.75, "y": 0.65, "class_code": 0},
        ]
        dialog = SetupReviewDefectsDialog(
            defects,
            self.state.get("setup_review_defects"),
            self,
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.state["setup_review_defects"] = deepcopy(dialog.result_defects)
            marked = sum(1 for defect in dialog.result_defects if defect.get("marked"))
            self.info.setText(
                f"Setup-Review returned {marked} marked DOI(s). Use Derived > Hot Spots to create Care Areas."
            )
            self.changed = True

    def _hot_spots(self):
        defects = [
            defect for defect in self.state.get("setup_review_defects", [])
            if defect.get("marked")
        ]
        if not defects:
            QMessageBox.information(
                self,
                "Derived Hot Spots",
                "Mark one or more defects in Setup-Review before creating Hot Spots.",
            )
            return
        size = 0.04
        areas = []
        for defect in defects:
            x = min(1.0 - size, max(0.0, float(defect.get("x", 0.5)) - size / 2))
            y = min(1.0 - size, max(0.0, float(defect.get("y", 0.5)) - size / 2))
            areas.append([x, y, size, size, int(defect.get("id", 0))])
        self._new_group("Derived")
        group = self.state["groups"][self.active_group]
        group["name"] = f"Hot Spots {self.active_group + 1}"
        group["areas"] = areas
        group["source"] = "Setup-Review marked defects"
        self.canvas.update()
        self._refresh()
        self.info.setText(f"Created {len(areas)} Hot Spot Care Area(s) from marked DOI(s).")
        self.changed = True

    def _sensitivity_pane(self):
        pane = QFrame()
        pane.setObjectName("pane")
        layout = QVBoxLayout(pane)
        layout.addWidget(QLabel("Sensitivity"))
        buttons = QHBoxLayout()
        for label, handler in [
            ("+", self._add_threshold),
            ("Edit", self._edit_threshold),
            ("Delete", self._delete_threshold),
        ]:
            button = QPushButton(label)
            button.clicked.connect(handler)
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.thresholds = QTableWidget(0, 3)
        self.thresholds.setHorizontalHeaderLabels(["Name", "Algorithm", "Threshold"])
        self.thresholds.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.thresholds, 1)
        hint = QLabel("Thresholds are assigned to Care Area Groups. Up to 32 regions are supported.")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        return pane

    def _new_group(self, kind):
        threshold = self.state["thresholds"][0]["name"]
        valid = kind not in {"Derived", "Imported"}
        self.state["groups"].append(
            {
                "name": f"{kind} {len(self.state['groups']) + 1}",
                "kind": kind,
                "threshold": threshold,
                "status": "OK" if valid else "Needs registration and verification",
                "enabled": True,
                "cag_code": len(self.state["groups"]) + 1,
                "show": True,
                "areas": [],
                "registered": valid,
                "verified": valid,
            }
        )
        self.active_group = len(self.state["groups"]) - 1
        self._start_area()
        self._changed(f"{kind} group created. Drag from upper-left to lower-right.")

    def _new_auto_group(self):
        dialog = AutoCareAreaDialog(parent=self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result != QDialog.Accepted:
            return
        self._new_group("ACA")
        group = self.state["groups"][self.active_group]
        group["name"] = dialog.name.text().strip() or group["name"]
        group["areas"] = [dialog.search_area()]
        group["aca"] = {
            "search_area": dialog.search_area(),
            "training_area": dialog.training_area(),
            "use_test_optics": dialog.use_test_optics.isChecked(),
            "skip_fourier_filter": dialog.skip_fourier.isChecked(),
        }
        self.state["groups"].extend(
            generate_page_break_groups(
                dialog.search_area(),
                dialog.training_area(),
                group["name"],
            )
        )
        self.canvas.drawing_enabled = False
        self._changed("Auto Care Area and horizontal/vertical Page Break groups generated.")

    def _derived_group(self):
        indexes = self._selected_group_indexes()
        if len(indexes) == 2:
            parents = [self.state["groups"][index] for index in indexes]
            if any(group.get("derived_operation") == "intersection" for group in parents):
                QMessageBox.warning(
                    self,
                    "Intersect Care Area",
                    "Select two ordinary or Page Break Care Area Groups.",
                )
                return
            self._new_group("Derived")
            group = self.state["groups"][self.active_group]
            group.update({
                "name": f"{parents[0]['name']}_{parents[1]['name']}_Intersect",
                "derived_operation": "intersection",
                "parents": [parents[0]["name"], parents[1]["name"]],
                "registered": True,
                "verified": True,
                "status": "OK",
            })
            self.canvas.drawing_enabled = False
            self._changed("Intersection Care Area Group created from the two selected groups.")
            return
        if len(indexes) != 1:
            QMessageBox.information(
                self,
                "Derived Care Area",
                "Select one group for Grow/Shrink or two groups for Intersection.",
            )
            return
        parent_group = self.state["groups"][indexes[0]]
        dialog = GrowShrinkCareAreaDialog(parent_group["name"], parent=self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result != QDialog.Accepted:
            return
        self._new_group("Derived")
        group = self.state["groups"][self.active_group]
        group.update({
            "name": dialog.name.text().strip(),
            "derived_operation": "grow_shrink",
            "parents": [parent_group["name"]],
            "margins": dialog.margins(),
            "registered": True,
            "verified": True,
            "status": "OK",
        })
        self.canvas.drawing_enabled = False
        self._changed("Grow/Shrink Care Area Group created from the selected parent.")

    def _entire_die(self):
        self._new_group("CA")
        group = self.state["groups"][self.active_group]
        group["name"] = "Entire Die"
        group["areas"] = [[0.02, 0.02, 0.96, 0.96]]
        self.canvas.drawing_enabled = False
        self._changed("Entire die assigned to the current Care Area group.")

    def _area_added(self, rect):
        if self.active_group < 0:
            self._new_group("CA")
        die_width, die_height = self.state.get("die_size_um", [5100.0, 16600.0])
        border = self.state.get("border", {"x": 0.0, "y": 0.0})
        if rect[2] * die_width < 2 * float(border.get("x", 0.0)) or rect[3] * die_height < 2 * float(border.get("y", 0.0)):
            QMessageBox.warning(
                self,
                "Care Area Size",
                "Care Area width and height must each be at least twice the configured Care Area Border.",
            )
            return
        if self.start_dca.isChecked() and self.state["groups"][self.active_group]["kind"] != "DCA":
            rect = list(rect) + ["DCA"]
        self.state["groups"][self.active_group]["areas"].append(rect)
        self._changed("Care Area corners stored.")

    def _advanced_group_changed(self, item):
        if self._loading or item.row() >= len(self.state["groups"]):
            return
        group = self.state["groups"][item.row()]
        if item.column() == 0:
            group["name"] = item.text().strip() or group.get("name", "Care Area")
        elif item.column() == 2:
            group["pda_care_area"] = item.text() == "Include"
        self.changed = True

    def _area_selected(self, group_index):
        if 0 <= group_index < self.groups.rowCount():
            self.groups.selectRow(group_index)

    def _fill(self):
        if self.active_group < 0 or not self.state["groups"][self.active_group]["areas"]:
            QMessageBox.warning(self, "Copy & Fill", "Define the first Care Area rectangle before using Fill.")
            return
        dialog = CopyFillDialog(self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result != QDialog.Accepted:
            return
        source_area = self.state["groups"][self.active_group]["areas"][0]
        x, y, width, height = source_area[:4]
        area_suffix = list(source_area[4:])
        areas = []
        for row in range(dialog.rows.value()):
            for column in range(dialog.columns.value()):
                nx = x + column * (width + dialog.gap_x.value())
                ny = y + row * (height + dialog.gap_y.value())
                if nx + width <= 0.99 and ny + height <= 0.99:
                    areas.append([nx, ny, width, height] + area_suffix)
        self.state["groups"][self.active_group]["areas"] = areas
        self._changed(f"Copy & Fill created {len(areas)} Care Areas.")

    def _no_fill(self):
        if self.active_group < 0:
            return
        areas = self.state["groups"][self.active_group]["areas"]
        if len(areas) > 2:
            self.state["groups"][self.active_group]["areas"] = [areas[0], areas[-1]]
            self._changed("No Fill retained only the first and last areas.")

    def _undo(self):
        if self.canvas.undo():
            self.changed = True
            self.info.setText("Previous Care Area edit restored.")
            self._refresh()

    def _redo(self):
        if self.canvas.redo():
            self.changed = True
            self.info.setText("Most recently undone Care Area edit restored.")
            self._refresh()

    def _show_group_menu(self, position):
        menu = QMenu(self)
        mark_verified = menu.addAction("Mark Group as Verified")
        delete_all = menu.addAction("Delete All Groups")
        menu.addSeparator()
        show_all = menu.addAction("Show All")
        hide_all = menu.addAction("Hide All")
        has_groups = bool(self.state["groups"])
        active = (
            self.state["groups"][self.active_group]
            if 0 <= self.active_group < len(self.state["groups"])
            else {}
        )
        mark_verified.setEnabled(
            self.active_group >= 0 and active.get("kind") != "NP Image Care Area"
        )
        delete_all.setEnabled(has_groups)
        show_all.setEnabled(has_groups)
        hide_all.setEnabled(has_groups)
        action = menu.exec(self.groups.viewport().mapToGlobal(position)) if hasattr(menu, "exec") else menu.exec_(self.groups.viewport().mapToGlobal(position))
        if action == mark_verified and self.active_group >= 0:
            group = self.state["groups"][self.active_group]
            group["verified"] = True
            group["status"] = "OK" if group.get("registered") else "Verified; registration required"
            self._changed("Care Area Group marked as verified.")
        elif action == delete_all:
            answer = QMessageBox.question(
                self,
                "Delete All Groups",
                "Delete all defined Care Area Groups?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer == QMessageBox.Yes:
                self.state["groups"] = []
                self.active_group = -1
                self._changed("All Care Area Groups deleted.")
        elif action in {show_all, hide_all}:
            visible = action == show_all
            for group in self.state["groups"]:
                group["show"] = visible
            self._changed("All Care Area Groups shown." if visible else "All Care Area Groups hidden.")

    def _delete_group(self):
        indexes = self._selected_group_indexes()
        if not indexes:
            return
        answer = QMessageBox.question(
            self,
            "Delete Care Area Group",
            "Delete the selected group(s) and all dependent derived groups?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self.state["groups"] = delete_groups_with_descendants(
                self.state["groups"], indexes
            )
            self.active_group = min(min(indexes), len(self.state["groups"]) - 1)
            self._changed("Selected Care Area Groups and dependent groups deleted.")

    def _copy_group(self):
        indexes = self._selected_group_indexes()
        if not indexes:
            return
        if any(
            self.state["groups"][index].get("derived_operation") == "intersection"
            for index in indexes
        ):
            QMessageBox.information(
                self, "Copy", "Intersection Care Area Groups cannot be copied or cut."
            )
            return
        self.group_clipboard = deepcopy(
            [self.state["groups"][index] for index in indexes]
        )

    def _cut_group(self):
        indexes = self._selected_group_indexes()
        if not indexes:
            return
        self.group_clipboard = None
        self._copy_group()
        if not self.group_clipboard:
            return
        self.state["groups"] = delete_groups_with_descendants(self.state["groups"], indexes)
        self.active_group = min(min(indexes), len(self.state["groups"]) - 1)
        self._changed("Care Area Group selection cut.")

    def _paste_group(self):
        if not self.group_clipboard:
            QMessageBox.information(self, "Paste", "Copy or cut a Care Area Group first.")
            return
        source = self.group_clipboard if isinstance(self.group_clipboard, list) else [self.group_clipboard]
        existing = {group.get("name") for group in self.state["groups"]}
        for source_group in source:
            group = deepcopy(source_group)
            base = f"{group['name']} Copy"
            name = base
            suffix = 2
            while name in existing:
                name = f"{base} {suffix}"
                suffix += 1
            group["name"] = name
            group["parents"] = []
            group.pop("derived_operation", None)
            group["cag_code"] = len(self.state["groups"]) + 1
            self.state["groups"].append(group)
            existing.add(name)
        self.active_group = len(self.state["groups"]) - 1
        self._changed(f"{len(source)} Care Area Group(s) pasted.")

    def _move_group(self, offset):
        target = self.active_group + offset
        if self.active_group < 0 or target < 0 or target >= len(self.state["groups"]):
            return
        groups = self.state["groups"]
        groups[self.active_group], groups[target] = groups[target], groups[self.active_group]
        self.active_group = target
        self._changed("Care Area priority updated.")

    def _register_group(self):
        if self.active_group < 0:
            return
        group = self.state["groups"][self.active_group]
        if group.get("derived_operation") == "intersection":
            QMessageBox.information(
                self, "Register Group", "Intersection groups do not require registration."
            )
            return
        if group.get("kind") == "NP Image Care Area":
            QMessageBox.information(
                self,
                "Register Group",
                "NP Image Care Area Groups are positioned by the image-template search and cannot be registered here.",
            )
            return
        if group.get("kind") == "NP Design Care Area":
            dialog = DesignCareAreaRegistrationDialog(group.get("registration"), self)
            result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
            if result != QDialog.Accepted:
                return
            group["registration"] = dialog.result_registration
        elif group.get("kind") == "Imported" or group.get("source"):
            dialog = RegisterCareAreaGroupDialog(group.get("registration"), self)
            result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
            if result != QDialog.Accepted:
                return
            group["registration"] = dialog.result_registration
        group.update({"registered": True, "verified": False, "status": "Needs verification"})
        self._changed("Care Area Group registered. Verify the group before finishing.")

    def _verify_group(self):
        if self.active_group < 0:
            return
        group = self.state["groups"][self.active_group]
        if group.get("derived_operation") == "intersection":
            QMessageBox.information(
                self, "Verify Group", "Intersection groups do not require verification."
            )
            return
        if group.get("kind") == "NP Image Care Area":
            QMessageBox.information(
                self,
                "Verify Group",
                "NP Image Care Area Groups cannot be verified manually.",
            )
            return
        if not group.get("registered", False):
            QMessageBox.warning(self, "Verify Group", "Register the Care Area Group before verification.")
            return
        dialog = VerifyCareAreaDialog(group.get("areas", []), self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result != QDialog.Accepted:
            return
        group.update({"verified": True, "status": "OK"})
        self._changed(f"{len(group.get('areas', []))} Care Area corners verified.")

    def _selected_group_indexes(self):
        rows = self.groups.selectionModel().selectedRows()
        return sorted({row.row() for row in rows}) or (
            [self.active_group] if self.active_group >= 0 else []
        )

    def _apply_offset(self):
        indexes = self._selected_group_indexes()
        if not indexes:
            return
        if any(
            self.state["groups"][index].get("kind") == "NP Image Care Area"
            or self.state["groups"][index].get("derived_operation") == "intersection"
            for index in indexes
        ):
            QMessageBox.information(
                self,
                "Apply Offset",
                "Offsets cannot be applied to NP Image or Intersection Care Area Groups.",
            )
            return
        dialog = ApplyOffsetDialog(
            self.state["groups"],
            indexes,
            self.state.get("die_size_um", [5100.0, 16600.0]),
            self,
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result != QDialog.Accepted:
            return
        self.state["groups"] = dialog.result_groups
        self._changed(f"Offset applied to {len(indexes)} Care Area Group(s).")

    def _edit_page_breaks(self):
        if self.active_group < 0:
            return
        group = self.state["groups"][self.active_group]
        if is_page_break_group(group):
            parent = next(
                (item for item in self.state["groups"] if item.get("name") == group.get("parent")),
                {},
            )
            dialog = PageBreakEditDialog(
                self.state["groups"],
                self.active_group,
                (parent.get("aca") or {}).get("search_area", [0, 0, 1, 1]),
                self,
            )
            result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
            if result == QDialog.Accepted:
                self.state["groups"] = dialog.result_groups
                self.active_group = min(dialog.active_group, len(self.state["groups"]) - 1)
                self._changed("Page Break edits stored.")
            return
        if group.get("kind") != "ACA":
            QMessageBox.information(self, "Page Breaks", "Select an Auto Care Area group.")
            return
        aca = group.get("aca") or {}
        dialog = AutoCareAreaDialog(
            name=group.get("name", "ACA"),
            search_area=aca.get("search_area", group.get("areas", [[0.1, 0.1, 0.8, 0.8]])[0]),
            training_area=aca.get("training_area", [0.1, 0.1, 0.2, 0.2]),
            use_test_optics=aca.get("use_test_optics", False),
            skip_fourier=aca.get("skip_fourier_filter", False),
            parent=self,
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result != QDialog.Accepted:
            return
        answer = QMessageBox.question(
            self,
            "Regenerate Page Breaks",
            "Existing Page Breaks will be deleted and regenerated. Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        parent_name = group["name"]
        self.state["groups"] = [
            item for item in self.state["groups"]
            if item.get("parent") != parent_name
        ]
        group = next(item for item in self.state["groups"] if item is group)
        group["areas"] = [dialog.search_area()]
        group["aca"] = {
            "search_area": dialog.search_area(),
            "training_area": dialog.training_area(),
            "use_test_optics": dialog.use_test_optics.isChecked(),
            "skip_fourier_filter": dialog.skip_fourier.isChecked(),
        }
        self.state["groups"].extend(
            generate_page_break_groups(dialog.search_area(), dialog.training_area(), parent_name)
        )
        self.active_group = self.state["groups"].index(group)
        self._changed("Page Break groups regenerated.")

    def _sort_page_breaks(self):
        indexes = self._selected_group_indexes()
        if not indexes or any(not is_page_break_group(self.state["groups"][index]) for index in indexes):
            QMessageBox.information(self, "Sort Page Break Groups", "Select Page Break groups of one orientation.")
            return
        dialog = PageBreakSortingDialog(self.state["groups"], indexes, self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result != QDialog.Accepted:
            return
        try:
            if dialog.combine_groups.isChecked():
                self.state["groups"] = combine_page_break_groups(
                    self.state["groups"], indexes, dialog.group_numbers()
                )
            else:
                self.state["groups"] = sort_page_break_groups(
                    self.state["groups"],
                    indexes,
                    dialog.separation.value(),
                    self.state.get("die_size_um", [5100.0, 16600.0]),
                )
        except ValueError as exc:
            QMessageBox.warning(self, "Sort Page Break Groups", str(exc))
            return
        self.active_group = min(indexes)
        self._changed("Page Break groups sorted by size.")

    def _show_cag_report(self):
        dialog = CareAreaCoverageDialog(care_area_coverage_report(self.state["groups"]), self)
        dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()

    def _import_group(self):
        dialog = CareAreaImportDialog(self.test_mode, self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result != QDialog.Accepted:
            return
        kind = dialog.import_type.currentText()
        if kind in {"NP Design Care Area", "NP Image Care Area"}:
            if not any(group.get("name") == "Entire Die" for group in self.state["groups"]):
                QMessageBox.warning(
                    self,
                    "Import Care Area Group",
                    "Define the Entire Die Care Area Group before importing NanoPoint Care Areas.",
                )
                return
        incompatible = {
            "NP Design Care Area": "NP Image Care Area",
            "NP Image Care Area": "NP Design Care Area",
        }.get(kind)
        if incompatible and any(
            group.get("kind") == incompatible for group in self.state["groups"]
        ):
            QMessageBox.warning(
                self,
                "Import Care Area Group",
                "NanoPoint Design and NanoPoint Image Care Areas cannot coexist in one test.",
            )
            return
        for name in dialog.selected_groups():
            self._new_group(kind if kind != "Care Area Component" else "Imported")
            group = self.state["groups"][self.active_group]
            image_cag = kind == "NP Image Care Area"
            group.update(
                {
                    "name": name,
                    "source": dialog.path.text().strip(),
                    "inspection_step": dialog.step.text().strip(),
                    "registration_source": dialog.registration_source.currentText(),
                    "status": "OK" if image_cag else "Needs registration and verification",
                    "registered": image_cag,
                    "verified": image_cag,
                    "requires_rescan": False,
                    "areas": [[0.12, 0.12, 0.30, 0.30]],
                }
            )
        self.canvas.drawing_enabled = False
        self._changed(
            "NP Image Care Area Groups imported from template search."
            if kind == "NP Image Care Area"
            else "Imported Care Area Groups require registration and verification."
        )

    def _more(self):
        dialog = CareAreaOptionsDialog(self.state, self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.state["selected_die"] = [dialog.die_x.value(), dialog.die_y.value()]
            self.state["border"] = {"x": dialog.border_x.value(), "y": dialog.border_y.value()}
            self.state["image_opacity"] = dialog.opacity.value()
            self.state["always_use_default_expansion_order"] = dialog.always_default.isChecked()
            self.state["expansion_order"] = dialog.expansion_order()
            self._changed("Die, border, and display settings updated.")

    def _group_selected(self):
        rows = self.groups.selectionModel().selectedRows()
        if rows:
            self.active_group = rows[0].row()
            self.canvas.active_group = self.active_group
            self.canvas.update()

    def _group_item_changed(self, item):
        if self._loading or item.row() >= len(self.state["groups"]):
            return
        group = self.state["groups"][item.row()]
        if item.column() == 0:
            old_name = group["name"]
            new_name = item.text().strip() or old_name
            if new_name != old_name and new_name in {
                entry.get("name") for entry in self.state["groups"]
            }:
                QMessageBox.warning(self, "Care Area Group", "Each group must have a unique name.")
                self._refresh()
                return
            group["name"] = new_name
            for child in self.state["groups"]:
                child["parents"] = [
                    new_name if parent == old_name else parent
                    for parent in child.get("parents", [])
                ]
                if child.get("parent") == old_name:
                    child["parent"] = new_name
        elif item.column() == 3:
            group["enabled"] = item.checkState() == Qt.Checked
        elif item.column() == 4:
            try:
                group["cag_code"] = int(item.text())
            except ValueError:
                pass
        elif item.column() == 5:
            group["show"] = item.checkState() == Qt.Checked
        self.changed = True
        refresh_derived_groups(self.state["groups"])
        self.canvas.update()

    def _add_threshold(self):
        if len(self.state["thresholds"]) >= 32:
            QMessageBox.warning(self, "Sensitivity", "A maximum of 32 threshold regions is supported.")
            return
        threshold = deepcopy(default_care_area_state()["thresholds"][0])
        threshold["name"] = f"Threshold {len(self.state['thresholds']) + 1}"
        dialog = ThresholdDialog(threshold, self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            if dialog.result_threshold["name"] in {item["name"] for item in self.state["thresholds"]}:
                QMessageBox.warning(self, "Sensitivity", "Each threshold must have a unique name.")
                return
            self.state["thresholds"].append(dialog.result_threshold)
            self.state["expansion_order"].append(dialog.result_threshold["name"])
            self._changed("Threshold created.")

    def _edit_threshold(self):
        row = max(0, self.thresholds.currentRow())
        dialog = ThresholdDialog(self.state["thresholds"][row], self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            old_name = self.state["thresholds"][row]["name"]
            new_name = dialog.result_threshold["name"]
            if new_name != old_name and new_name in {
                item["name"] for item in self.state["thresholds"]
            }:
                QMessageBox.warning(
                    self,
                    "Sensitivity",
                    "Each threshold must have a unique name.",
                )
                return
            for group in self.state["groups"]:
                if group.get("threshold") == old_name:
                    group["threshold"] = new_name
            self.state["thresholds"][row] = dialog.result_threshold
            self._changed("Threshold updated.")

    def _delete_threshold(self):
        row = self.thresholds.currentRow()
        if row <= 0:
            QMessageBox.information(self, "Sensitivity", "The default threshold cannot be deleted.")
            return
        name = self.state["thresholds"][row]["name"]
        if any(group.get("threshold") == name for group in self.state["groups"]):
            QMessageBox.warning(self, "Sensitivity", "This threshold is assigned to a Care Area Group.")
            return
        self.state["thresholds"].pop(row)
        self.state["expansion_order"] = [
            item for item in self.state["expansion_order"] if item != name
        ]
        self._changed("Threshold deleted.")

    def _set_group_threshold(self, index, value):
        if 0 <= index < len(self.state["groups"]):
            self.state["groups"][index]["threshold"] = value
            self.changed = True

    def _acquire(self):
        self.canvas.image_acquired = True
        self.canvas.update()
        self.info.setText("MacroView image acquired.")

    def _refresh(self):
        self._loading = True
        self.groups.setRowCount(len(self.state["groups"]))
        names = [threshold["name"] for threshold in self.state["thresholds"]]
        for row, group in enumerate(self.state["groups"]):
            self.groups.setItem(row, 0, QTableWidgetItem(group["name"]))
            threshold = QComboBox()
            threshold.addItems(names)
            threshold.setCurrentText(group.get("threshold", names[0]))
            threshold.currentTextChanged.connect(
                lambda value, index=row: self._set_group_threshold(index, value)
            )
            self.groups.setCellWidget(row, 1, threshold)
            self.groups.setItem(row, 2, QTableWidgetItem(group.get("status", "OK")))
            enabled = QTableWidgetItem("")
            enabled.setCheckState(Qt.Checked if group.get("enabled", True) else Qt.Unchecked)
            self.groups.setItem(row, 3, enabled)
            self.groups.setItem(row, 4, QTableWidgetItem(str(group.get("cag_code", row + 1))))
            shown = QTableWidgetItem("")
            shown.setCheckState(Qt.Checked if group.get("show", True) else Qt.Unchecked)
            self.groups.setItem(row, 5, shown)
            self.groups.setItem(row, 6, QTableWidgetItem(str(len(group.get("areas", [])))))
        self._loading = False
        self._loading = True
        self.advanced_groups.setRowCount(len(self.state["groups"]))
        for row, group in enumerate(self.state["groups"]):
            self.advanced_groups.setItem(row, 0, QTableWidgetItem(group["name"]))
            self.advanced_groups.setItem(row, 1, QTableWidgetItem(group.get("threshold", "Default")))
            pda = QComboBox()
            pda.addItems(["Include", "Exclude"])
            pda.setCurrentText("Include" if group.get("pda_care_area", False) else "Exclude")
            pda.currentTextChanged.connect(
                lambda value, index=row: self._set_group_pda(index, value)
            )
            self.advanced_groups.setCellWidget(row, 2, pda)
        self._loading = False
        self.thresholds.setRowCount(len(self.state["thresholds"]))
        for row, threshold in enumerate(self.state["thresholds"]):
            self.thresholds.setItem(row, 0, QTableWidgetItem(threshold["name"]))
            self.thresholds.setItem(row, 1, QTableWidgetItem(threshold.get("algorithm", "HLAT")))
            self.thresholds.setItem(
                row, 2, QTableWidgetItem(f"{float(threshold.get('threshold', 0)):g}")
            )
        if 0 <= self.active_group < self.groups.rowCount():
            self.groups.selectRow(self.active_group)
        self.canvas.active_group = self.active_group
        self.canvas.update()

    def _set_group_pda(self, index, value):
        if 0 <= index < len(self.state["groups"]):
            self.state["groups"][index]["pda_care_area"] = value == "Include"
            self.changed = True

    def _changed(self, message):
        self.changed = True
        self.info.setText(message)
        refresh_derived_groups(self.state["groups"])
        self._refresh()

    def _finish(self, overwrite):
        if not self.state["groups"]:
            answer = QMessageBox.question(
                self,
                "Care Areas",
                "No Care Area Groups are defined. Finish anyway?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
        self.overwrite_all = overwrite
        self.result_state = deepcopy(self.state)
        self.accept()


class CareAreaCanvas(QWidget):
    def __init__(self, state, on_added, on_selected, on_measured=None, parent=None):
        super().__init__(parent)
        self.state = state
        self.on_added = on_added
        self.on_selected = on_selected
        self.on_measured = on_measured
        self.active_group = -1
        self.drawing_enabled = False
        self.image_acquired = False
        self.show_image = True
        self.measurement_enabled = False
        self.zoom = 1.0
        self.start = None
        self.current = None
        self.history = []
        self.redo_stack = []
        self.setMinimumSize(460, 460)

    def set_zoom(self, value):
        self.zoom = value / 100.0
        self.update()

    def mousePressEvent(self, event):
        pos = event.position() if hasattr(event, "position") else event.pos()
        if self.measurement_enabled:
            self.start = (pos.x(), pos.y())
            self.current = self.start
            return
        if not self.drawing_enabled:
            for group_index in reversed(range(len(self.state["groups"]))):
                for area in self.state["groups"][group_index].get("areas", []):
                    x, y, width, height = area[:4]
                    inside_x = x * self.width() <= pos.x() <= (x + width) * self.width()
                    inside_y = y * self.height() <= pos.y() <= (y + height) * self.height()
                    if inside_x and inside_y:
                        self.on_selected(group_index)
                        return
            return
        self.start = (pos.x(), pos.y())
        self.current = self.start

    def mouseMoveEvent(self, event):
        if self.start:
            pos = event.position() if hasattr(event, "position") else event.pos()
            self.current = (pos.x(), pos.y())
            self.update()

    def mouseReleaseEvent(self, event):
        if not self.start:
            return
        pos = event.position() if hasattr(event, "position") else event.pos()
        x1, y1 = self.start
        x2, y2 = pos.x(), pos.y()
        self.start = None
        self.current = None
        if abs(x2 - x1) < 6 or abs(y2 - y1) < 6:
            return
        if self.measurement_enabled:
            if self.on_measured:
                self.on_measured(
                    (x1 / max(1, self.width()), y1 / max(1, self.height())),
                    (x2 / max(1, self.width()), y2 / max(1, self.height())),
                )
            self.update()
            return
        self.history.append(deepcopy(self.state["groups"]))
        self.redo_stack.clear()
        self.on_added([
            max(0.0, min(x1, x2) / max(1, self.width())),
            max(0.0, min(y1, y2) / max(1, self.height())),
            min(1.0, abs(x2 - x1) / max(1, self.width())),
            min(1.0, abs(y2 - y1) / max(1, self.height())),
        ])

    def undo(self):
        if self.history:
            self.redo_stack.append(deepcopy(self.state["groups"]))
            self.state["groups"] = self.history.pop()
            self.update()
            return True
        return False

    def redo(self):
        if self.redo_stack:
            self.history.append(deepcopy(self.state["groups"]))
            self.state["groups"] = self.redo_stack.pop()
            self.update()
            return True
        return False

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(
            self.rect(),
            QColor("#627982" if self.show_image and self.image_acquired else "#71848b"),
        )
        painter.setPen(QPen(QColor("#81979e"), 1))
        spacing = max(12, int(28 * self.zoom))
        for x in range(0, self.width(), spacing):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), spacing):
            painter.drawLine(0, y, self.width(), y)
        for index, group in enumerate(self.state["groups"]):
            if not group.get("show", True):
                continue
            color = QColor(GROUP_COLORS[index % len(GROUP_COLORS)])
            opacity = max(0, min(100, int(self.state.get("image_opacity", 65))))
            color.setAlpha(int(255 * opacity / 100) if index == self.active_group else int(160 * opacity / 100))
            painter.setBrush(color)
            painter.setPen(
                QPen(
                    QColor(GROUP_COLORS[index % len(GROUP_COLORS)]),
                    3 if index == self.active_group else 1,
                )
            )
            for area in group.get("areas", []):
                x, y, width, height = area[:4]
                painter.drawRect(
                    int(x * self.width()),
                    int(y * self.height()),
                    int(width * self.width()),
                    int(height * self.height()),
                )
        if self.start and self.current:
            x1, y1 = self.start
            x2, y2 = self.current
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor("#ff3030"), 2, Qt.DashLine))
            painter.drawRect(
                int(min(x1, x2)),
                int(min(y1, y2)),
                int(abs(x2 - x1)),
                int(abs(y2 - y1)),
            )


class ThresholdDialog(QDialog):
    def __init__(self, threshold, parent=None):
        super().__init__(parent)
        self.result_threshold = None
        self.setWindowTitle("Sensitivity Parameters")
        self.setFixedSize(500, 360)
        layout = QGridLayout(self)
        self.name = QLineEdit(threshold.get("name", "Threshold"))
        self.algorithm = QComboBox()
        self.algorithm.addItems(["HLAT", "NanoPoint", "MDS", "BHLAT", "SLAT"])
        self.algorithm.setCurrentText(threshold.get("algorithm", "HLAT"))
        self.threshold = QDoubleSpinBox()
        self.threshold.setRange(0.0, 1000.0)
        self.threshold.setValue(float(threshold.get("threshold", 45.0)))
        self.minimum_size = QDoubleSpinBox()
        self.minimum_size.setRange(0.01, 1000.0)
        self.minimum_size.setDecimals(3)
        self.minimum_size.setValue(float(threshold.get("minimum_size", 0.12)))
        rows = [
            ("Threshold Name:", self.name),
            ("Selected Algorithm:", self.algorithm),
            ("Detection Threshold:", self.threshold),
            ("Minimum Defect Size:", self.minimum_size),
        ]
        for row, (label, control) in enumerate(rows):
            layout.addWidget(QLabel(label), row, 0)
            layout.addWidget(control, row, 1, 1, 3)
        layout.addWidget(QLabel("Channels:"), 4, 0)
        selected = threshold.get("channels", [1, 2, 3])
        self.channels = []
        for index in range(3):
            check = QCheckBox(str(index + 1))
            check.setChecked(index + 1 in selected)
            self.channels.append(check)
            layout.addWidget(check, 4, index + 1)
        ok = QPushButton("OK")
        ok.clicked.connect(self._accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        layout.addWidget(ok, 6, 2)
        layout.addWidget(cancel, 6, 3)

    def _accept(self):
        channels = [
            index + 1 for index, check in enumerate(self.channels) if check.isChecked()
        ]
        if not self.name.text().strip() or not channels:
            QMessageBox.warning(
                self,
                "Sensitivity",
                "Enter a unique name and select at least one channel.",
            )
            return
        self.result_threshold = {
            "name": self.name.text().strip(),
            "algorithm": self.algorithm.currentText(),
            "channels": channels,
            "minimum_size": self.minimum_size.value(),
            "threshold": self.threshold.value(),
        }
        self.accept()


class GrowShrinkCareAreaDialog(QDialog):
    def __init__(self, parent_name, margins=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Edit Grow/Shrink Group - {parent_name}")
        self.resize(520, 250)
        layout = QGridLayout(self)
        self.name = QLineEdit(f"{parent_name} Grow-Shrink")
        layout.addWidget(QLabel("Derived Group Name:"), 0, 0)
        layout.addWidget(self.name, 0, 1, 1, 4)
        layout.addWidget(QLabel("Normalized edge adjustment (+ grow / - shrink)"), 1, 0, 1, 5)
        self.controls = []
        for column, (label, value) in enumerate(
            zip(("Left", "Top", "Right", "Bottom"), margins or [0.01] * 4)
        ):
            layout.addWidget(QLabel(label), 2, column + 1)
            control = QDoubleSpinBox()
            control.setRange(-0.49, 0.49)
            control.setDecimals(4)
            control.setSingleStep(0.005)
            control.setValue(float(value))
            self.controls.append(control)
            layout.addWidget(control, 3, column + 1)
        done = QPushButton("Done")
        done.clicked.connect(self._accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        layout.addWidget(done, 4, 3)
        layout.addWidget(cancel, 4, 4)

    def margins(self):
        return [control.value() for control in self.controls]

    def _accept(self):
        if not self.name.text().strip():
            QMessageBox.warning(self, "Grow/Shrink Care Area", "Enter a derived group name.")
            return
        self.accept()


class CopyFillDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Copy-Fill Settings")
        self.setFixedSize(420, 270)
        layout = QGridLayout(self)
        self.rows = QSpinBox()
        self.rows.setRange(1, 20)
        self.rows.setValue(3)
        self.columns = QSpinBox()
        self.columns.setRange(1, 20)
        self.columns.setValue(3)
        self.gap_x = QDoubleSpinBox()
        self.gap_x.setRange(0.0, 0.5)
        self.gap_x.setSingleStep(0.01)
        self.gap_y = QDoubleSpinBox()
        self.gap_y.setRange(0.0, 0.5)
        self.gap_y.setSingleStep(0.01)
        rows = [
            ("Rows:", self.rows),
            ("Columns:", self.columns),
            ("Gap X:", self.gap_x),
            ("Gap Y:", self.gap_y),
        ]
        for row, (label, control) in enumerate(rows):
            layout.addWidget(QLabel(label), row, 0)
            layout.addWidget(control, row, 1)
        ok = QPushButton("OK")
        ok.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        layout.addWidget(ok, 5, 0)
        layout.addWidget(cancel, 5, 1)


class CareAreaImportDialog(QDialog):
    def __init__(self, test_mode, parent=None):
        super().__init__(parent)
        self.test_mode = test_mode
        self.setWindowTitle("Care Area Group Selection")
        self.resize(620, 470)
        self.setStyleSheet(
            "QDialog { background: #cfcbc2; color: #111111; font-family: 'Segoe UI'; font-size: 9pt; }"
            "QWidget { color: #111111; }"
            "QPushButton { background: #e8e6dd; border: 1px solid #77736b; min-height: 24px; padding: 2px 7px; }"
            "QComboBox, QLineEdit { background: #ffffff; color: #111111; border: 1px solid #8c8982; min-height: 22px; }"
            "QTableWidget { background: #f4f3ef; color: #111111; gridline-color: #aaa69d; }"
            "QHeaderView::section { background: #dad7cf; color: #111111; border: 1px solid #9a968d; padding: 3px; }"
        )
        self.groups_by_step = {}
        layout = QGridLayout(self)
        self.import_type = QComboBox()
        self.import_type.addItems(
            ["Care Area Component", "NP Design Care Area", "NP Image Care Area"]
        )
        self.path = QLineEdit()
        self.browse_button = QPushButton("Open Component...")
        self.browse_button.clicked.connect(self._browse)
        self.step = QLineEdit("Current Step")
        self.step.textChanged.connect(self._populate_groups)
        self.registration_source = QComboBox()
        self.registration_source.addItems(["Recipe", "Manual"])
        layout.addWidget(QLabel("Import Type:"), 0, 0)
        layout.addWidget(self.import_type, 0, 1, 1, 2)
        layout.addWidget(QLabel("Design / Care Area File:"), 1, 0)
        layout.addWidget(self.path, 1, 1)
        layout.addWidget(self.browse_button, 1, 2)
        layout.addWidget(QLabel("Inspection Step:"), 2, 0)
        layout.addWidget(self.step, 2, 1, 1, 2)
        layout.addWidget(QLabel("Registration Source:"), 3, 0)
        layout.addWidget(self.registration_source, 3, 1, 1, 2)
        layout.addWidget(QLabel("Select Care Area Groups"), 4, 0, 1, 3)
        self.groups = QTableWidget(0, 3)
        self.groups.setHorizontalHeaderLabels(["Use", "CAG", "Registered"])
        self.groups.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.groups, 5, 0, 1, 3)
        select_all = QPushButton("Select/Deselect All")
        select_all.clicked.connect(self._toggle_all)
        ok = QPushButton("OK")
        ok.clicked.connect(self._accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        layout.addWidget(select_all, 6, 0)
        layout.addWidget(ok, 6, 1)
        layout.addWidget(cancel, 6, 2)
        self.import_type.currentTextChanged.connect(self._type_changed)
        self._type_changed(self.import_type.currentText())

    def _type_changed(self, kind):
        titles = {
            "NP Design Care Area": "NP Design Care Area Selection",
            "NP Image Care Area": "NP Image Care Area Selection",
        }
        self.setWindowTitle(titles.get(kind, "Open Recipe Component - Care Area"))
        self.browse_button.setText(
            "Open NPCA..." if kind in {"NP Design Care Area", "NP Image Care Area"}
            else "Open Component..."
        )

    def selected_groups(self):
        return [
            self.groups.item(row, 1).text().strip()
            for row in range(self.groups.rowCount())
            if self.groups.item(row, 0).checkState() == Qt.Checked
        ]

    def _toggle_all(self):
        checked = not all(
            self.groups.item(row, 0).checkState() == Qt.Checked
            for row in range(self.groups.rowCount())
        )
        for row in range(self.groups.rowCount()):
            self.groups.item(row, 0).setCheckState(Qt.Checked if checked else Qt.Unchecked)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Design File Browser",
            "",
            "Care Area Files (*.json *.xml *.gds *.cbi *.rlf *.rdf);;All Files (*.*)",
        )
        if path:
            self.path.setText(path)
            self.groups_by_step = care_area_file_metadata(path)
            first_step = next(iter(self.groups_by_step), "Current Step")
            self.step.setText(first_step)
            self._populate_groups(first_step)

    def _populate_groups(self, step):
        names = self.groups_by_step.get(str(step).strip(), [])
        self.groups.setRowCount(len(names))
        for row, name in enumerate(names):
            use = QTableWidgetItem("")
            use.setCheckState(Qt.Checked if row == 0 else Qt.Unchecked)
            self.groups.setItem(row, 0, use)
            self.groups.setItem(row, 1, QTableWidgetItem(name))
            registered = QTableWidgetItem("")
            registered.setFlags((registered.flags() | Qt.ItemIsUserCheckable) & ~Qt.ItemIsEditable)
            registered.setCheckState(Qt.Unchecked)
            self.groups.setItem(row, 2, registered)

    def _accept(self):
        if self.import_type.currentText() == "NP Design Care Area" and self.test_mode not in {
            "Random",
            "Mixed",
        }:
            QMessageBox.warning(
                self,
                "NP Design Care Area",
                "NP Design Care Area is available only for Random and Mixed Mode tests.",
            )
            return
        if not self.path.text().strip() or not self.step.text().strip():
            QMessageBox.warning(
                self,
                "Care Area Group Selection",
                "Select a file and an Inspection Step.",
            )
            return
        if not self.selected_groups():
            QMessageBox.warning(
                self,
                "Care Area Group Selection",
                "Select at least one Care Area Group.",
            )
            return
        self.accept()


class RegisterCareAreaGroupDialog(QDialog):
    def __init__(self, registration=None, parent=None):
        super().__init__(parent)
        registration = registration or {}
        self.result_registration = None
        self.marked = False
        self.setWindowTitle("Register Care Area Group")
        self.resize(460, 220)
        layout = QGridLayout(self)
        site = registration.get("site", [0.5, 0.5])
        self.site_x = QDoubleSpinBox()
        self.site_y = QDoubleSpinBox()
        for control, value in zip((self.site_x, self.site_y), site):
            control.setRange(0.0, 1.0)
            control.setDecimals(4)
            control.setValue(float(value))
        layout.addWidget(QLabel("Care Area corner X / Y:"), 0, 0)
        layout.addWidget(self.site_x, 0, 1)
        layout.addWidget(self.site_y, 0, 2)
        mark = QPushButton("Mark")
        mark.clicked.connect(self._mark)
        layout.addWidget(mark, 0, 3)
        self.status = QLabel("Mark the first Care Area corner to register the group.")
        layout.addWidget(self.status, 1, 0, 1, 4)
        self.done_button = QPushButton("Done")
        self.done_button.setEnabled(False)
        self.done_button.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        layout.addWidget(self.done_button, 2, 2)
        layout.addWidget(cancel, 2, 3)

    def _mark(self):
        self.marked = True
        self.done_button.setEnabled(True)
        self.status.setText("Registration corner marked. Click Done to store the registration.")

    def _finish(self):
        if not self.marked:
            QMessageBox.warning(self, "Register Care Area Group", "Mark the Care Area corner first.")
            return
        self.result_registration = {
            "site": [self.site_x.value(), self.site_y.value()],
            "registered": True,
        }
        self.accept()


class DesignCareAreaRegistrationDialog(QDialog):
    def __init__(self, registration=None, parent=None):
        super().__init__(parent)
        registration = registration or {}
        self.result_registration = None
        self.np_marked = False
        self.design_marked = False
        self.setWindowTitle("Register MCA with Design")
        self.resize(560, 330)
        layout = QGridLayout(self)
        self.np_x, self.np_y = self._point(registration.get("np_site", [0.2, 0.2]))
        self.design_x, self.design_y = self._point(
            registration.get("design_site", [0.2, 0.2])
        )
        layout.addWidget(QLabel("NPDCA Site X / Y:"), 0, 0)
        layout.addWidget(self.np_x, 0, 1)
        layout.addWidget(self.np_y, 0, 2)
        mark_np = QPushButton("Mark NPDCA Site")
        mark_np.clicked.connect(lambda: self._mark("np"))
        layout.addWidget(mark_np, 0, 3)
        layout.addWidget(QLabel("Design Site X / Y:"), 1, 0)
        layout.addWidget(self.design_x, 1, 1)
        layout.addWidget(self.design_y, 1, 2)
        mark_design = QPushButton("Mark Design Site")
        mark_design.clicked.connect(lambda: self._mark("design"))
        layout.addWidget(mark_design, 1, 3)
        self.status = QLabel("Mark corresponding sites in NPDCA and Design.")
        layout.addWidget(self.status, 2, 0, 1, 4)
        done = QPushButton("Done")
        done.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        layout.addWidget(done, 3, 2)
        layout.addWidget(cancel, 3, 3)

    @staticmethod
    def _point(values):
        controls = []
        for value in values:
            spin = QDoubleSpinBox()
            spin.setRange(0, 1)
            spin.setDecimals(4)
            spin.setValue(float(value))
            controls.append(spin)
        return controls

    def _mark(self, which):
        if which == "np":
            self.np_marked = True
        else:
            self.design_marked = True
        self.status.setText(
            f"NPDCA Site: {'Marked' if self.np_marked else 'Pending'}    "
            f"Design Site: {'Marked' if self.design_marked else 'Pending'}"
        )

    def _finish(self):
        if not self.np_marked or not self.design_marked:
            QMessageBox.warning(
                self,
                "Design Registration",
                "Mark both the NPDCA site and corresponding Design site.",
            )
            return
        self.result_registration = {
            "np_site": [self.np_x.value(), self.np_y.value()],
            "design_site": [self.design_x.value(), self.design_y.value()],
        }
        self.accept()


class VerifyCareAreaDialog(QDialog):
    def __init__(self, areas, parent=None):
        super().__init__(parent)
        self.total = len(areas)
        self.marked = 0
        self.setWindowTitle("Verify Care Area Group")
        self.setFixedSize(450, 240)
        layout = QVBoxLayout(self)
        self.status = QLabel()
        layout.addWidget(self.status)
        mark = QPushButton("Mark")
        mark.clicked.connect(self._mark)
        self.done_button = QPushButton("Done")
        self.done_button.setEnabled(self.total == 0)
        self.done_button.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        row = QHBoxLayout()
        row.addWidget(mark)
        row.addStretch(1)
        row.addWidget(self.done_button)
        row.addWidget(cancel)
        layout.addLayout(row)
        self._refresh()

    def _mark(self):
        self.marked = min(self.total, self.marked + 1)
        self.done_button.setEnabled(self.marked == self.total)
        self._refresh()

    def _refresh(self):
        self.status.setText(
            f"Mark lower corner for Care Area {min(self.marked + 1, self.total)} of {self.total}."
            if self.total
            else "No Care Area corners require verification."
        )


class AutoCareAreaDialog(QDialog):
    def __init__(
        self,
        name="ACA",
        search_area=None,
        training_area=None,
        use_test_optics=False,
        skip_fourier=False,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Edit Auto Care Area")
        self.resize(560, 430)
        layout = QGridLayout(self)
        self.name = QLineEdit(name)
        layout.addWidget(QLabel("Care Area Group:"), 0, 0)
        layout.addWidget(self.name, 0, 1, 1, 4)
        layout.addWidget(QLabel("Normalized die coordinates"), 1, 0, 1, 5)
        headers = ["", "X", "Y", "Width", "Height"]
        for column, text in enumerate(headers):
            layout.addWidget(QLabel(text), 2, column)
        self.search_controls = self._area_controls(search_area or [0.08, 0.08, 0.84, 0.84])
        self.training_controls = self._area_controls(training_area or [0.08, 0.08, 0.20, 0.20])
        for row, (label, controls) in enumerate(
            (("Search Area", self.search_controls), ("Training Area", self.training_controls)),
            start=3,
        ):
            layout.addWidget(QLabel(label), row, 0)
            for column, control in enumerate(controls, start=1):
                layout.addWidget(control, row, column)
        self.use_test_optics = QCheckBox("Use Test Optics")
        self.use_test_optics.setChecked(bool(use_test_optics))
        self.skip_fourier = QCheckBox("Skip Fourier Filter")
        self.skip_fourier.setChecked(bool(skip_fourier))
        layout.addWidget(self.use_test_optics, 5, 0, 1, 3)
        layout.addWidget(self.skip_fourier, 5, 3, 1, 2)
        note = QLabel(
            "Generate creates horizontal and vertical Do Not Inspect Page Break subgroups."
        )
        note.setWordWrap(True)
        layout.addWidget(note, 6, 0, 1, 5)
        generate = QPushButton("Generate Page Break")
        generate.clicked.connect(self._accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        layout.addWidget(generate, 7, 3)
        layout.addWidget(cancel, 7, 4)

    @staticmethod
    def _area_controls(values):
        controls = []
        for value in values:
            spin = QDoubleSpinBox()
            spin.setRange(0.0, 1.0)
            spin.setDecimals(3)
            spin.setSingleStep(0.01)
            spin.setValue(float(value))
            controls.append(spin)
        return controls

    def search_area(self):
        return [control.value() for control in self.search_controls]

    def training_area(self):
        return [control.value() for control in self.training_controls]

    def _accept(self):
        try:
            generate_page_break_groups(
                self.search_area(),
                self.training_area(),
                self.name.text().strip() or "ACA",
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Auto Care Area", str(exc))
            return
        self.accept()


class CareAreaOffsetPreview(QWidget):
    def __init__(self, groups, indexes, die_size_um, parent=None):
        super().__init__(parent)
        self.groups = deepcopy(groups)
        self.indexes = list(indexes)
        self.die_size_um = list(die_size_um)
        self.offset_um = [0.0, 0.0]
        self.anchor_corner = "Upper-left"
        self.marked = False
        self.setMinimumSize(360, 280)

    def set_offset(self, x_um, y_um):
        self.offset_um = [float(x_um), float(y_um)]
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#777975"))
        margin = 16
        side = max(20, min(self.width(), self.height()) - margin * 2)
        left = (self.width() - side) // 2
        top = (self.height() - side) // 2
        painter.fillRect(left, top, side, side, QColor("#f5f5f2"))
        painter.setPen(QPen(QColor("#7b7972"), 1))
        painter.drawRect(left, top, side, side)
        dx = self.offset_um[0] / max(1.0, float(self.die_size_um[0]))
        dy = self.offset_um[1] / max(1.0, float(self.die_size_um[1]))
        selected_areas = [
            area
            for index in self.indexes
            if 0 <= index < len(self.groups)
            for area in self.groups[index].get("areas", [])
        ]
        for area in selected_areas:
            x, y, width, height = [float(value) for value in area[:4]]
            painter.setBrush(QColor(40, 156, 178, 90))
            painter.setPen(QPen(QColor("#277e8e"), 1))
            painter.drawRect(
                int(left + x * side), int(top + y * side),
                max(1, int(width * side)), max(1, int(height * side)),
            )
            painter.setBrush(QColor(227, 164, 20, 80))
            painter.setPen(QPen(QColor("#d08a00"), 2 if self.marked else 1, Qt.DashLine))
            painter.drawRect(
                int(left + (x + dx) * side), int(top + (y + dy) * side),
                max(1, int(width * side)), max(1, int(height * side)),
            )
        if selected_areas:
            x, y, width, height = [float(value) for value in selected_areas[0][:4]]
            corner = {
                "Upper-left": (x, y),
                "Upper-right": (x + width, y),
                "Lower-left": (x, y + height),
                "Lower-right": (x + width, y + height),
            }[self.anchor_corner]
            cx = int(left + (corner[0] + dx) * side)
            cy = int(top + (corner[1] + dy) * side)
            painter.setPen(QPen(QColor("#e3262e"), 2))
            painter.drawLine(cx - 9, cy, cx + 9, cy)
            painter.drawLine(cx, cy - 9, cx, cy + 9)


class ApplyOffsetDialog(QDialog):
    def __init__(self, groups, indexes, die_size_um, parent=None):
        super().__init__(parent)
        self.groups = deepcopy(groups)
        self.indexes = list(indexes)
        self.die_size_um = list(die_size_um)
        self.result_groups = None
        self.marked = False
        self.setWindowTitle("Apply Offset")
        self.resize(700, 430)
        layout = QGridLayout(self)
        self.preview = CareAreaOffsetPreview(groups, indexes, die_size_um, self)
        layout.addWidget(self.preview, 0, 0, 8, 1)
        title = QLabel("Move selected Care Area Group(s)")
        title.setStyleSheet("font-weight: 700;")
        layout.addWidget(title, 0, 1, 1, 2)
        self.anchor = QComboBox()
        self.anchor.addItems(["Upper-left", "Upper-right", "Lower-left", "Lower-right"])
        self.anchor.setEnabled(False)
        layout.addWidget(QLabel("Anchor:"), 1, 1)
        layout.addWidget(self.anchor, 1, 2)
        self.offset_x = QDoubleSpinBox()
        self.offset_y = QDoubleSpinBox()
        self.offset_x.setRange(-float(die_size_um[0]), float(die_size_um[0]))
        self.offset_y.setRange(-float(die_size_um[1]), float(die_size_um[1]))
        for control in (self.offset_x, self.offset_y):
            control.setDecimals(1)
            control.setSingleStep(1.0)
            control.setSuffix(" um")
            control.valueChanged.connect(self._offset_changed)
        layout.addWidget(QLabel("X Offset:"), 2, 1)
        layout.addWidget(self.offset_x, 2, 2)
        layout.addWidget(QLabel("Y Offset:"), 3, 1)
        layout.addWidget(self.offset_y, 3, 2)
        self.status = QLabel(
            "The red crosshair is the anchor of the first selected group. "
            "Set the target offset, then click Mark Site."
        )
        self.status.setWordWrap(True)
        layout.addWidget(self.status, 4, 1, 1, 2)
        self.mark_button = QPushButton("Mark Site")
        self.mark_button.clicked.connect(self._mark_site)
        self.undo_button = QPushButton("Undo / Select Anchor")
        self.undo_button.clicked.connect(self._undo)
        self.done_button = QPushButton("Done")
        self.done_button.setEnabled(False)
        self.done_button.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        layout.addWidget(self.mark_button, 5, 1, 1, 2)
        layout.addWidget(self.undo_button, 6, 1, 1, 2)
        layout.addWidget(self.done_button, 7, 1)
        layout.addWidget(cancel, 7, 2)
        self.anchor.currentTextChanged.connect(self._anchor_changed)

    def _offset_changed(self):
        self.marked = False
        self.preview.marked = False
        self.preview.set_offset(self.offset_x.value(), self.offset_y.value())
        self.done_button.setEnabled(False)
        self.status.setText("Offset changed. Click Mark Site to store the target position.")

    def _anchor_changed(self, value):
        self.preview.anchor_corner = value
        self.preview.update()

    def _mark_site(self):
        try:
            self.result_groups = apply_care_area_offset(
                self.groups, self.indexes,
                self.offset_x.value(), self.offset_y.value(), self.die_size_um,
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Apply Offset", str(exc))
            return
        self.marked = True
        self.preview.marked = True
        self.preview.update()
        self.done_button.setEnabled(True)
        self.status.setText("Site marked. Click Done to apply the offset, or Undo to revise it.")

    def _undo(self):
        self.result_groups = None
        self.marked = False
        self.preview.marked = False
        self.anchor.setEnabled(True)
        self.done_button.setEnabled(False)
        self.preview.update()
        self.status.setText("Select another anchor if needed, then click Mark Site again.")

    def _finish(self):
        if self.marked and self.result_groups is not None:
            self.accept()


class PageBreakEditDialog(QDialog):
    def __init__(self, groups, active_group, search_area=None, parent=None):
        super().__init__(parent)
        self.groups = deepcopy(groups)
        self.active_group = int(active_group)
        self.search_area = list(search_area or [0, 0, 1, 1])
        self.result_groups = None
        self.redo_stack = []
        self.setWindowTitle("Edit Page Break")
        self.resize(620, 470)
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["X", "Y", "Width", "Height"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)
        geometry = QGridLayout()
        self.geometry = []
        for column, label in enumerate(("Start X", "Start Y", "End X", "End Y")):
            spin = QDoubleSpinBox()
            spin.setRange(0.0, 1.0)
            spin.setDecimals(4)
            spin.setSingleStep(0.005)
            geometry.addWidget(QLabel(label), 0, column)
            geometry.addWidget(spin, 1, column)
            self.geometry.append(spin)
        layout.addLayout(geometry)
        actions = QHBoxLayout()
        for label, handler in (
            ("Finish PageBreak", self._add),
            ("Undo", self._undo),
            ("Redo", self._redo),
            ("Repeat Page Break", self._repeat),
        ):
            button = QPushButton(label)
            button.clicked.connect(handler)
            actions.addWidget(button)
        layout.addLayout(actions)
        move = QHBoxLayout()
        move.addWidget(QLabel("Move selected Page Break to"))
        self.target = QComboBox()
        self._load_targets()
        move.addWidget(self.target, 1)
        move_button = QPushButton("Move Rect")
        move_button.clicked.connect(self._move)
        move.addWidget(move_button)
        layout.addLayout(move)
        footer = QHBoxLayout()
        footer.addStretch(1)
        done = QPushButton("Done")
        done.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        footer.addWidget(done)
        footer.addWidget(cancel)
        layout.addLayout(footer)
        self._refresh()

    def _group(self):
        return self.groups[self.active_group]

    def _load_targets(self):
        self.target.clear()
        self.target.addItem("Create PageBreak Group", None)
        kind = self._group().get("kind")
        for index, group in enumerate(self.groups):
            if index != self.active_group and group.get("kind") == kind:
                self.target.addItem(group.get("name", f"Group {index + 1}"), index)

    def _refresh(self):
        areas = self._group().get("areas", [])
        self.table.setRowCount(len(areas))
        for row, area in enumerate(areas):
            for column, value in enumerate(area[:4]):
                item = QTableWidgetItem(f"{float(value):.4f}")
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, column, item)
        if areas:
            self.table.selectRow(len(areas) - 1)

    def _add(self):
        x1, y1, x2, y2 = [control.value() for control in self.geometry]
        rect = [min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1)]
        if rect[2] <= 0 or rect[3] <= 0:
            QMessageBox.warning(self, "Edit Page Break", "Start and end points must define an area.")
            return
        bx, by, bw, bh = self.search_area
        if rect[0] < bx or rect[1] < by or rect[0] + rect[2] > bx + bw or rect[1] + rect[3] > by + bh:
            QMessageBox.warning(self, "Edit Page Break", "Page Break must remain inside the ACA search area.")
            return
        self._group().setdefault("areas", []).append(rect)
        self.redo_stack.clear()
        self._refresh()

    def _undo(self):
        areas = self._group().setdefault("areas", [])
        if areas:
            self.redo_stack.append(areas.pop())
            self._refresh()

    def _redo(self):
        if self.redo_stack:
            self._group().setdefault("areas", []).append(self.redo_stack.pop())
            self._refresh()

    def _repeat(self):
        try:
            self._group()["areas"] = repeat_page_break(self._group().get("areas", []), self.search_area)
        except ValueError as exc:
            QMessageBox.warning(self, "Repeat Page Break", str(exc))
            return
        self.redo_stack.clear()
        self._refresh()

    def _move(self):
        row = self.table.currentRow()
        try:
            self.groups, target = move_page_break(
                self.groups,
                self.active_group,
                row,
                self.target.currentData(),
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Move Page Break", str(exc))
            return
        self.active_group = target
        self.redo_stack.clear()
        self._load_targets()
        self._refresh()

    def _finish(self):
        self.result_groups = deepcopy(self.groups)
        self.accept()


class PageBreakSortingDialog(QDialog):
    def __init__(self, groups=None, indexes=None, parent=None):
        super().__init__(parent)
        self.source_groups = groups or []
        self.indexes = list(indexes or [])
        self.setWindowTitle("Page Break Sorting")
        self.resize(560, 390)
        layout = QGridLayout(self)
        layout.addWidget(QLabel("Size Separation Between Page Breaks (um)"), 0, 0)
        self.separation = QDoubleSpinBox()
        self.separation.setRange(0.0, 10000.0)
        self.separation.setDecimals(2)
        self.separation.setValue(2.0)
        layout.addWidget(self.separation, 0, 1)
        self.assignment_table = QTableWidget(len(self.indexes), 2)
        self.assignment_table.setHorizontalHeaderLabels(["Page Break Group", "Group Number"])
        self.assignment_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for row, index in enumerate(self.indexes):
            group = self.source_groups[index]
            name = QTableWidgetItem(str(group.get("name") or f"Page Break {index + 1}"))
            name.setFlags(name.flags() & ~Qt.ItemIsEditable)
            self.assignment_table.setItem(row, 0, name)
            number = QSpinBox()
            number.setRange(1, 999)
            number.setValue(row + 1)
            self.assignment_table.setCellWidget(row, 1, number)
        layout.addWidget(self.assignment_table, 1, 0, 1, 2)
        self.combine_groups = QCheckBox("Combine Groups with the same Group Number")
        layout.addWidget(self.combine_groups, 2, 0, 1, 2)
        update = QPushButton("Update")
        update.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        layout.addWidget(update, 3, 0)
        layout.addWidget(cancel, 3, 1)

    def group_numbers(self):
        return {
            index: self.assignment_table.cellWidget(row, 1).value()
            for row, index in enumerate(self.indexes)
        }


class CareAreaCoverageDialog(QDialog):
    def __init__(self, report, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Area Defined in Each CAG Report")
        self.resize(620, 420)
        layout = QVBoxLayout(self)
        table = QTableWidget(len(report), 3)
        table.setHorizontalHeaderLabels(
            ["Care Area Group", "Defined Area (%)", "Inspected Area (%)"]
        )
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for row, record in enumerate(report):
            table.setItem(row, 0, QTableWidgetItem(record["name"]))
            table.setItem(row, 1, QTableWidgetItem(f"{record['defined_percent']:.3f}"))
            table.setItem(row, 2, QTableWidgetItem(f"{record['inspected_percent']:.3f}"))
        layout.addWidget(table)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        layout.addWidget(close, 0, Qt.AlignRight)


class CareAreaOptionsDialog(QDialog):
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Care Area Options")
        self.resize(560, 540)
        layout = QGridLayout(self)
        self.die_x = QSpinBox()
        self.die_x.setRange(-999, 999)
        self.die_x.setValue(int(state.get("selected_die", [0, 0])[0]))
        self.die_y = QSpinBox()
        self.die_y.setRange(-999, 999)
        self.die_y.setValue(int(state.get("selected_die", [0, 0])[1]))
        self.border_x = QDoubleSpinBox()
        self.border_x.setRange(0.0, 1000.0)
        self.border_x.setValue(float(state.get("border", {}).get("x", 2.0)))
        self.border_y = QDoubleSpinBox()
        self.border_y.setRange(0.0, 1000.0)
        self.border_y.setValue(float(state.get("border", {}).get("y", 2.0)))
        self.opacity = QSlider(Qt.Horizontal)
        self.opacity.setRange(0, 100)
        self.opacity.setValue(int(state.get("image_opacity", 65)))
        rows = [
            ("Selected Die X:", self.die_x),
            ("Selected Die Y:", self.die_y),
            ("Care Area Border X (um):", self.border_x),
            ("Care Area Border Y (um):", self.border_y),
            ("MacroView opacity:", self.opacity),
        ]
        for row, (label, control) in enumerate(rows):
            layout.addWidget(QLabel(label), row, 0)
            layout.addWidget(control, row, 1)
        self.always_default = QCheckBox("Always Use Default Order")
        self.always_default.setChecked(
            bool(state.get("always_use_default_expansion_order", True))
        )
        layout.addWidget(self.always_default, 5, 0, 1, 2)
        self.order_table = QTableWidget(0, 1)
        self.order_table.setHorizontalHeaderLabels(
            ["Expansion Order (least to most sensitive)"]
        )
        self.order_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        order = state.get("expansion_order") or [
            item["name"] for item in state.get("thresholds", [])
        ]
        self.order_table.setRowCount(len(order))
        for row, name in enumerate(order):
            self.order_table.setItem(row, 0, QTableWidgetItem(name))
        layout.addWidget(self.order_table, 6, 0, 1, 2)
        order_buttons = QHBoxLayout()
        self.move_up = QPushButton("Move Up")
        self.move_down = QPushButton("Move Down")
        default = QPushButton("Default Order")
        self.move_up.clicked.connect(lambda: self._move_order(-1))
        self.move_down.clicked.connect(lambda: self._move_order(1))
        default.clicked.connect(
            lambda: self._set_order([item["name"] for item in state.get("thresholds", [])])
        )
        for button in (self.move_up, self.move_down, default):
            order_buttons.addWidget(button)
        layout.addLayout(order_buttons, 7, 0, 1, 2)
        self.always_default.toggled.connect(self._toggle_order)
        self._toggle_order(self.always_default.isChecked())
        ok = QPushButton("OK")
        ok.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        layout.addWidget(ok, 8, 0)
        layout.addWidget(cancel, 8, 1)

    def expansion_order(self):
        return [
            self.order_table.item(row, 0).text()
            for row in range(self.order_table.rowCount())
        ]

    def _toggle_order(self, checked):
        self.order_table.setEnabled(not checked)
        self.move_up.setEnabled(not checked)
        self.move_down.setEnabled(not checked)

    def _set_order(self, names):
        self.order_table.setRowCount(len(names))
        for row, name in enumerate(names):
            self.order_table.setItem(row, 0, QTableWidgetItem(name))

    def _move_order(self, offset):
        row = self.order_table.currentRow()
        target = row + offset
        if row < 0 or target < 0 or target >= self.order_table.rowCount():
            return
        names = self.expansion_order()
        names[row], names[target] = names[target], names[row]
        self._set_order(names)
        self.order_table.selectRow(target)

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from ...qt_compat import (
    QAbstractItemView,
    QApplication,
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
    QIcon,
    QLabel,
    QLineEdit,
    QMenu,
    QMenuBar,
    QMessageBox,
    QPainter,
    QPen,
    QPixmap,
    QPushButton,
    QSlider,
    QSize,
    QSplitter,
    QSpinBox,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    Qt,
    QVBoxLayout,
    QWidget,
)


GROUP_COLORS = ["#20b9ca", "#e2b313", "#dc5c74", "#7bcb55", "#8f76d7", "#e88432"]


def care_area_hand_icon():
    pixmap = QPixmap(18, 18)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setPen(QPen(QColor("#34322e"), 1))
    painter.setBrush(QColor("#f0c44c"))
    painter.drawRect(5, 7, 8, 8)
    painter.drawRect(11, 4, 5, 3)
    painter.drawRect(3, 8, 3, 3)
    painter.drawLine(6, 15, 12, 15)
    painter.end()
    return QIcon(pixmap)


def care_area_group_icon(kind):
    pixmap = QPixmap(28, 28)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setPen(QPen(QColor("#4d4b45"), 1))
    color = QColor("#8b8f08") if kind != "DCA" else QColor("#424846")
    painter.setBrush(color)
    if kind == "ACA":
        for row in range(3):
            for column in range(3):
                painter.drawRect(7 + column * 5, 8 + row * 5, 4, 4)
    else:
        painter.drawRect(7, 8, 15, 15)
    if kind == "Derived":
        painter.setBrush(QColor("#3294d0"))
        painter.drawEllipse(5, 17, 7, 7)
    painter.setPen(QPen(QColor("#f4e500"), 2))
    for x1, y1, x2, y2 in (
        (8, 1, 8, 13),
        (2, 7, 14, 7),
        (4, 3, 12, 11),
        (12, 3, 4, 11),
    ):
        painter.drawLine(x1, y1, x2, y2)
    painter.end()
    return QIcon(pixmap)


def care_area_command_icon(command):
    pixmap = QPixmap(26, 26)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setPen(QPen(QColor("#55534d"), 1))
    if command == "Edit":
        painter.setBrush(QColor("#84920e"))
        painter.drawRect(3, 4, 13, 17)
        painter.setPen(QPen(QColor("#d7db72"), 1))
        for offset in range(4, 17, 4):
            painter.drawLine(offset, 5, min(16, offset + 9), 18)
        painter.setPen(QPen(QColor("#e11d16"), 2))
        painter.drawLine(19, 13, 19, 23)
        painter.drawLine(14, 18, 24, 18)
    elif command == "Delete":
        painter.setBrush(QColor("#84920e"))
        painter.drawRect(3, 4, 13, 17)
        painter.setBrush(QColor("#e5221c"))
        painter.setPen(QPen(QColor("#e5221c"), 1))
        painter.drawEllipse(11, 10, 13, 13)
        painter.setPen(QPen(QColor("#ffffff"), 2))
        painter.drawLine(14, 16, 21, 16)
    elif command == "Cut":
        painter.setPen(QPen(QColor("#6b6a65"), 2))
        painter.drawEllipse(3, 17, 5, 5)
        painter.drawEllipse(11, 17, 5, 5)
        painter.drawLine(6, 18, 14, 4)
        painter.drawLine(13, 18, 7, 4)
    elif command in {"Copy", "Paste"}:
        painter.setBrush(QColor("#f4f3ee"))
        painter.drawRect(5, 4, 12, 16)
        painter.drawRect(9, 7, 12, 16)
        if command == "Paste":
            painter.setBrush(QColor("#a9aaa5"))
            painter.drawRect(4, 2, 12, 5)
    elif command == "Import":
        painter.setBrush(QColor("#c99b59"))
        painter.drawRect(5, 14, 16, 8)
        painter.setPen(QPen(QColor("#37a94d"), 3))
        painter.drawLine(13, 3, 13, 16)
        painter.drawLine(8, 11, 13, 16)
        painter.drawLine(18, 11, 13, 16)
    elif command in {"Promote", "Demote"}:
        painter.setBrush(QColor("#f0f0ec"))
        painter.drawRect(3, 2, 15, 21)
        painter.setPen(QPen(QColor("#617895"), 2))
        for y in (7, 11, 15):
            painter.drawLine(6, y, 15, y)
        arrow_y = 7 if command == "Promote" else 17
        painter.drawLine(17, arrow_y, 24, arrow_y)
        painter.drawLine(20, arrow_y - 3, 24, arrow_y)
        painter.drawLine(20, arrow_y + 3, 24, arrow_y)
    painter.end()
    return QIcon(pixmap)


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
        "die_image_opacity": 65,
        "care_area_opacity": 65,
        "defect_opacity": 100,
        "setup_review_defects": [],
    }


def normalized_care_area_state(state: dict | None) -> dict:
    result = default_care_area_state()
    if isinstance(state, dict):
        result.update(deepcopy(state))
        if "image_opacity" in state and "care_area_opacity" not in state:
            result["care_area_opacity"] = int(state["image_opacity"])
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
    vertical_positions = []
    x = tx
    while x > sx + thickness:
        vertical_positions.append(x)
        x -= tw
    x = tx + tw
    while x < sx + sw - thickness:
        vertical_positions.append(x)
        x += tw
    vertical = [[x, sy, thickness, sh] for x in sorted(vertical_positions)]
    horizontal_positions = []
    y = ty
    while y > sy + thickness:
        horizontal_positions.append(y)
        y -= th
    y = ty + th
    while y < sy + sh - thickness:
        horizontal_positions.append(y)
        y += th
    horizontal = [[sx, y, sw, thickness] for y in sorted(horizontal_positions)]
    common = {
        "threshold": "Do Not Inspect",
        "status": "OK",
        "enabled": True,
        "show": True,
        "registered": True,
        "verified": True,
        "parent": parent_name,
        "do_not_inspect": True,
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


def aca_dram_example():
    """Return a deterministic repeating-cell example for ACA training and QA."""
    return {
        "name": "DRAM Array Example",
        "search_area": [0.08, 0.10, 0.84, 0.80],
        "training_area": [0.08, 0.10, 0.14, 0.16],
        "use_test_optics": True,
        "skip_fourier_filter": False,
        "cib_parameters": {
            "clip": 4.0,
            "offset": 0.0,
            "l0": 1.0,
            "k": 1.0,
        },
    }


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
        test_name="Test 1",
        parent=None,
    ):
        super().__init__(parent)
        self.state = normalized_care_area_state(state)
        self.test_mode = test_mode
        self.defect_data = deepcopy(defect_data or {})
        self.wafer_aligned = bool(wafer_aligned)
        self.test_name = str(test_name or "Test 1")
        self.result_state = None
        self.overwrite_all = False
        self.changed = False
        self.active_group = -1
        self.group_clipboard = None
        self.area_started = False
        self.area_edit_snapshot = None
        self.fill_configuration = None
        self.last_fill = None
        self.grow_shrink_editor = None
        self.grow_shrink_parent_name = ""
        self.grow_shrink_disabled_states = {}
        self.can_overwrite = bool(can_overwrite)
        self._loading = False
        self.setWindowTitle("Care Areas")
        self.resize(1440, 860)
        self.setMinimumSize(1100, 680)
        self.setStyleSheet(
            "QDialog { background: #cfcbc2; font-family: Arial; font-size: 10px; }"
            "QPushButton { background: #e8e6dd; border: 1px solid #77736b; min-height: 26px; padding: 2px 7px; }"
            "QTableWidget { background: #f0efeb; gridline-color: #aaa69d; }"
            "QHeaderView::section { background: #dad7cf; border: 1px solid #9a968d; padding: 3px; }"
            "QFrame#pane { border: 1px solid #8c8982; background: #ddd9d0; }"
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        self.view_menu_bar = QMenuBar()
        view_menu = self.view_menu_bar.addMenu("View")
        wafermap_image_menu = view_menu.addMenu("Wafermap Image")
        self.acquire_macro_action = wafermap_image_menu.addAction("Acquire")
        self.macro_view_action = wafermap_image_menu.addAction(
            "Toggle WaferMap Image"
        )
        self.macro_view_action.setCheckable(True)
        self.macro_view_action.setChecked(False)
        self.macro_view_action.setEnabled(False)
        self.macro_view_action.toggled.connect(self._toggle_macro_image)
        self.acquire_macro_action.triggered.connect(self._acquire)
        root.addWidget(self.view_menu_bar)
        self.panes = QSplitter(Qt.Horizontal)
        self.panes.addWidget(self._die_view())
        self.right_panes = QSplitter(Qt.Vertical)
        self.right_panes.addWidget(self._groups_pane())
        self.right_panes.addWidget(self._sensitivity_pane())
        self.right_panes.setSizes([520, 250])
        self.panes.addWidget(self.right_panes)
        self.panes.setSizes([820, 580])
        root.addWidget(self.panes, 1)
        footer = QHBoxLayout()
        self.info = QLabel("Select a Care Area type, then drag over the Die View.")
        footer.addWidget(self.review_button)
        footer.addWidget(self.info, 1)
        self.overwrite_finish_button = QPushButton("Finish && Overwrite All Tests")
        self.overwrite_finish_button.setEnabled(self.can_overwrite)
        self.overwrite_finish_button.clicked.connect(lambda: self._finish(True))
        self.finish_button = QPushButton("Finish")
        self.finish_button.clicked.connect(lambda: self._finish(False))
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        footer.addWidget(self.overwrite_finish_button)
        footer.addWidget(self.finish_button)
        footer.addWidget(self.cancel_button)
        root.addLayout(footer)
        self._refresh()

    def _die_view(self):
        pane = QFrame()
        pane.setObjectName("pane")
        layout = QVBoxLayout(pane)
        self.die_view_layout = layout
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Die View"))
        self.zoom_out_button = QPushButton("-")
        self.zoom_out_button.setAccessibleName("Zoom out")
        self.zoom_out_button.setToolTip("Zoom Out")
        toolbar.addWidget(self.zoom_out_button)
        self.zoom = QSlider(Qt.Horizontal)
        self.zoom.setRange(25, 300)
        self.zoom.setValue(100)
        toolbar.addWidget(self.zoom, 1)
        self.zoom_value = QComboBox()
        self.zoom_value.addItems(["25%", "50%", "75%", "100%", "150%", "200%", "300%"])
        self.zoom_value.setCurrentText("100%")
        self.zoom_value.setToolTip("Die View zoom")
        self.zoom_value.setFixedWidth(66)
        toolbar.addWidget(self.zoom_value)
        self.zoom_in_button = QPushButton("+")
        self.zoom_in_button.setAccessibleName("Zoom in")
        self.zoom_in_button.setToolTip("Zoom In")
        toolbar.addWidget(self.zoom_in_button)
        self.fit_button = QPushButton("Fit")
        self.fit_button.setToolTip("Zoom to Fit")
        toolbar.addWidget(self.fit_button)
        self.move_stage_buttons = {}
        for direction, icon, dx, dy in (
            ("Left", QStyle.SP_ArrowLeft, -0.01, 0.0),
            ("Up", QStyle.SP_ArrowUp, 0.0, -0.01),
            ("Down", QStyle.SP_ArrowDown, 0.0, 0.01),
            ("Right", QStyle.SP_ArrowRight, 0.01, 0.0),
        ):
            button = QPushButton()
            button.setFixedSize(28, 28)
            button.setIcon(self.style().standardIcon(icon))
            button.setAccessibleName(f"Move stage {direction.lower()}")
            button.setToolTip(f"Move stage {direction.lower()}")
            button.clicked.connect(
                lambda checked=False, move_x=dx, move_y=dy: self._nudge_stage(move_x, move_y)
            )
            self.move_stage_buttons[direction] = button
            toolbar.addWidget(button)
        self.center_stage_button = QPushButton("Center")
        self.center_stage_button.setFixedWidth(52)
        self.center_stage_button.setAccessibleName("Center stage")
        self.center_stage_button.setToolTip("Move stage to die center")
        self.center_stage_button.clicked.connect(self._center_stage)
        toolbar.addWidget(self.center_stage_button)
        self.macro_view_button = QPushButton("MacroView")
        macro_menu = QMenu(self.macro_view_button)
        macro_menu.addAction(self.acquire_macro_action)
        macro_menu.addAction(self.macro_view_action)
        self.macro_view_button.setMenu(macro_menu)
        toolbar.addWidget(self.macro_view_button)
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
        self.show_info_action = show_menu.addAction("Show the information bar")
        self.show_info_action.setCheckable(True)
        self.show_info_action.setChecked(True)
        self.show_image_action = show_menu.addAction("Show Die Image")
        self.show_image_action.setCheckable(True)
        self.show_image_action.setChecked(True)
        self.show_care_areas_action = show_menu.addAction("Show Care Areas")
        self.show_care_areas_action.setCheckable(True)
        self.show_care_areas_action.setChecked(True)
        self.show_defects_action = show_menu.addAction("Show Defects")
        self.show_defects_action.setCheckable(True)
        self.show_defects_action.setChecked(True)
        show_menu.addSeparator()
        self.opacity_controls_action = show_menu.addAction("Layer Opacity Controls")
        self.opacity_controls_action.setCheckable(True)
        for title, layer in (
            ("Die Image Opacity", "die_image"),
            ("Care Area Opacity", "care_area"),
            ("Defect Opacity", "defect"),
        ):
            opacity_menu = show_menu.addMenu(title)
            for opacity in (25, 50, 75, 100):
                opacity_menu.addAction(
                    f"{opacity}%",
                    lambda checked=False, value=opacity, target=layer: self._set_layer_opacity(value, target),
                )
        self.show_image_action.toggled.connect(self._set_image_visibility)
        self.show_care_areas_action.toggled.connect(self._set_care_area_visibility)
        self.show_defects_action.toggled.connect(self._set_defect_visibility)
        self.show_rulers_action.toggled.connect(self._set_ruler_visibility)
        self.show_tooltips_action.toggled.connect(self._set_tooltip_visibility)
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
        layout.addLayout(toolbar)
        self.opacity_panel = self._layer_opacity_panel()
        self.opacity_panel.setVisible(False)
        self.opacity_controls_action.toggled.connect(self.opacity_panel.setVisible)
        layout.addWidget(self.opacity_panel)
        self.canvas = CareAreaCanvas(
            self.state,
            self._area_added,
            self._area_selected,
            self._measurement_completed,
            defects=self.defect_data.get("defects", []),
            on_stage_moved=self._stage_moved,
            on_position_inspected=self._position_inspected,
        )
        self.zoom.valueChanged.connect(self.canvas.set_zoom)
        self.zoom.valueChanged.connect(lambda value: self.zoom_value.setCurrentText(f"{value}%"))
        self.zoom_value.currentTextChanged.connect(
            lambda value: self.zoom.setValue(int(value.rstrip("%"))) if value else None
        )
        self.zoom_out_button.clicked.connect(
            lambda: self.zoom.setValue(self.zoom.value() - 10)
        )
        self.zoom_in_button.clicked.connect(
            lambda: self.zoom.setValue(self.zoom.value() + 10)
        )
        self.fit_button.clicked.connect(self._fit_die_view)
        layout.addWidget(self.canvas, 1)
        self.edit_care_area_panel = QFrame()
        self.edit_care_area_panel.setObjectName("pane")
        edit = QGridLayout(self.edit_care_area_panel)
        edit.setContentsMargins(8, 5, 8, 5)
        edit.setHorizontalSpacing(8)
        edit.setVerticalSpacing(4)
        edit_title = QLabel("Edit Care Area")
        edit_title.setStyleSheet("font-weight: 600;")
        edit.addWidget(edit_title, 0, 0, 1, 5)
        self.edit_instruction = QLabel(
            "Move stage to the beginning of the care area and click Start Care Area, "
            "or click Fill to fill the region with care areas."
        )
        self.edit_instruction.setWordWrap(True)
        edit.addWidget(self.edit_instruction, 1, 0, 1, 5)

        self.undo_area_button = QPushButton("Undo")
        self.undo_area_button.setIcon(
            self.style().standardIcon(QStyle.SP_ArrowBack)
        )
        self.undo_area_button.clicked.connect(self._undo)
        edit.addWidget(self.undo_area_button, 2, 0)
        self.start_area_button = QPushButton("Start Care Area")
        self.start_area_button.setIcon(care_area_hand_icon())
        self.start_area_button.clicked.connect(self._start_area)
        edit.addWidget(self.start_area_button, 2, 1)
        self.start_dca = QCheckBox("Start Area begins a\nnew Don't Care Area")
        edit.addWidget(self.start_dca, 2, 2, 1, 2)
        self.redo_area_button = QPushButton("Redo")
        self.redo_area_button.setIcon(
            self.style().standardIcon(QStyle.SP_ArrowForward)
        )
        self.redo_area_button.clicked.connect(self._redo)
        edit.addWidget(self.redo_area_button, 2, 4)

        self.fill_button = QPushButton("Fill")
        self.fill_button.setIcon(care_area_hand_icon())
        self.fill_button.clicked.connect(self._fill)
        edit.addWidget(self.fill_button, 3, 0)
        self.no_fill_button = QPushButton("No Fill")
        self.no_fill_button.clicked.connect(self._no_fill)
        edit.addWidget(self.no_fill_button, 3, 1)
        self.fill_settings_button = QPushButton("Fill Settings")
        self.fill_settings_button.clicked.connect(self._fill_settings)
        edit.addWidget(self.fill_settings_button, 3, 2)

        self.finish_area_button = QPushButton("Done")
        self.finish_area_button.setIcon(
            self.style().standardIcon(QStyle.SP_DialogApplyButton)
        )
        self.finish_area_button.setEnabled(False)
        self.finish_area_button.clicked.connect(self._finish_area)
        edit.addWidget(self.finish_area_button, 1, 5)
        self.cancel_area_button = QPushButton("Cancel")
        self.cancel_area_button.setIcon(
            self.style().standardIcon(QStyle.SP_DialogCancelButton)
        )
        self.cancel_area_button.clicked.connect(self._cancel_area_edit)
        edit.addWidget(self.cancel_area_button, 2, 5)
        edit.setColumnStretch(3, 1)
        layout.addWidget(self.edit_care_area_panel)
        self._update_edit_controls()
        return pane

    def _layer_opacity_panel(self):
        panel = QFrame()
        panel.setObjectName("pane")
        controls = QHBoxLayout(panel)
        controls.setContentsMargins(6, 3, 6, 3)
        self.opacity_sliders = {}
        for label, layer, state_key in (
            ("Die Image", "die_image", "die_image_opacity"),
            ("Care Areas", "care_area", "care_area_opacity"),
            ("Defects", "defect", "defect_opacity"),
        ):
            controls.addWidget(QLabel(label))
            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(int(self.state.get(state_key, 100)))
            slider.setToolTip(f"{label} opacity")
            slider.valueChanged.connect(
                lambda value, target=layer: self._set_layer_opacity(value, target)
            )
            self.opacity_sliders[layer] = slider
            controls.addWidget(slider, 1)
        return panel

    def _groups_pane(self):
        pane = QFrame()
        pane.setObjectName("pane")
        layout = QVBoxLayout(pane)
        self.group_buttons = {}
        self.more_button = QPushButton("More...")
        more_menu = QMenu(self.more_button)
        more_actions = [
            ("Create Hot Spots from Review", self._hot_spots),
            ("Setup Care Area Border", self._more),
            ("Select Die", self._more),
            ("Re-Register", self._register_group),
            ("Verify Group", self._verify_group),
            ("Mark Group as Verified", self._verify_group),
            ("Apply Offset", self._apply_offset),
            ("Edit Page Breaks", self._edit_page_breaks),
            ("Sort PageBreak Group", self._sort_page_breaks),
            ("Area Defined in Each CAG report", self._show_cag_report),
            ("Image Display Window", self._open_image_display),
            ("Die, Border, and Display Options...", self._more),
        ]
        for label, handler in more_actions:
            more_menu.addAction(label, handler)
        self.more_button.setMenu(more_menu)
        self.group_header = QHBoxLayout()
        self.group_header.addWidget(QLabel(f"{self.test_name} - Care Area Groups"))
        self.group_header.addStretch(1)
        self.group_header.addWidget(self.more_button)
        layout.addLayout(self.group_header)

        self.group_command_grid = QGridLayout()
        self.group_command_grid.setHorizontalSpacing(5)
        self.group_command_grid.setVerticalSpacing(5)
        primary_actions = [
            ("CA", lambda: self._new_group("CA")),
            ("DCA", lambda: self._new_group("DCA")),
            ("ACA", self._new_auto_group),
            ("Derived", self._derived_group),
            ("Entire Die", self._entire_die),
        ]
        for column, (label, handler) in enumerate(primary_actions):
            button = QPushButton(label)
            button.setIcon(care_area_group_icon(label))
            button.setIconSize(QSize(24, 24))
            button.setMinimumHeight(38)
            button.clicked.connect(handler)
            self.group_buttons[label] = button
            self.group_command_grid.addWidget(button, 0, column)

        edit_actions = [
            ("Edit", self._edit_group),
            ("Delete", self._delete_group),
            ("Cut", self._cut_group),
            ("Copy", self._copy_group),
            ("Paste", self._paste_group),
            ("Register", self._register_group),
            ("Import", self._import_group),
        ]
        for column, (label, handler) in enumerate(edit_actions):
            icon_only = label in {"Cut", "Copy", "Paste"}
            button = QPushButton("" if icon_only else label)
            if label != "Register":
                button.setIcon(care_area_command_icon(label))
                button.setIconSize(QSize(22, 22))
            button.setAccessibleName(label)
            button.setToolTip(label)
            button.setMinimumHeight(38)
            if label == "Paste":
                button.setEnabled(False)
            button.clicked.connect(handler)
            self.group_buttons[label] = button
            self.group_command_grid.addWidget(button, 1, column)
        self.promote_button = QPushButton("")
        self.promote_button.setAccessibleName("Promote")
        self.promote_button.setToolTip("Promote selected Care Area Group")
        self.promote_button.setIcon(care_area_command_icon("Promote"))
        self.promote_button.setIconSize(QSize(24, 24))
        self.promote_button.setFixedWidth(38)
        self.promote_button.setMinimumHeight(38)
        self.promote_button.clicked.connect(lambda: self._move_group(-1))
        self.group_command_grid.addWidget(self.promote_button, 0, 7)
        self.demote_button = QPushButton("")
        self.demote_button.setAccessibleName("Demote")
        self.demote_button.setToolTip("Demote selected Care Area Group")
        self.demote_button.setIcon(care_area_command_icon("Demote"))
        self.demote_button.setIconSize(QSize(24, 24))
        self.demote_button.setFixedWidth(38)
        self.demote_button.setMinimumHeight(38)
        self.demote_button.clicked.connect(lambda: self._move_group(1))
        self.group_command_grid.addWidget(self.demote_button, 1, 7)
        layout.addLayout(self.group_command_grid)
        self.groups = QTableWidget(0, 7)
        self.groups.setHorizontalHeaderLabels(
            ["Name", "Threshold", "Status", "Enabled", "CAG Code", "Show", "Count"]
        )
        self.groups.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.groups.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
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
        if self.area_edit_snapshot is None:
            self.area_edit_snapshot = deepcopy(self.state["groups"])
        self.area_started = True
        self.canvas.drawing_enabled = True
        self.measure_button.setChecked(False)
        self.edit_instruction.setText(
            "Drag from the upper-left to the lower-right corner. Click Done to keep "
            "this edit or Cancel to restore the previous care areas."
        )
        self.info.setText(
            "Start Care Area marked. Drag from the upper-left to the lower-right corner, then click Done."
        )
        self._update_edit_controls()

    def _finish_area(self):
        if not self.area_started:
            return
        self.area_started = False
        self.canvas.drawing_enabled = False
        self.canvas.start = None
        self.canvas.current = None
        self.area_edit_snapshot = None
        self.edit_instruction.setText(
            "Move stage to the beginning of the care area and click Start Care Area, "
            "or click Fill to fill the region with care areas."
        )
        self.info.setText(
            "Care Area edit stored. Click Start Care Area to define another region or Finish to return to Tests."
        )
        self._update_edit_controls()

    def _cancel_area_edit(self):
        if self.area_edit_snapshot is not None:
            self.state["groups"] = deepcopy(self.area_edit_snapshot)
            self.active_group = min(self.active_group, len(self.state["groups"]) - 1)
        self.area_edit_snapshot = None
        self.area_started = False
        self.canvas.drawing_enabled = False
        self.canvas.start = None
        self.canvas.current = None
        self.edit_instruction.setText(
            "Move stage to the beginning of the care area and click Start Care Area, "
            "or click Fill to fill the region with care areas."
        )
        self.info.setText("Care Area edit canceled; the previous definition was restored.")
        self._refresh()

    def _update_edit_controls(self):
        if not hasattr(self, "start_area_button"):
            return
        has_group = 0 <= self.active_group < len(self.state["groups"])
        area_count = (
            len(self.state["groups"][self.active_group].get("areas", []))
            if has_group
            else 0
        )
        self.start_area_button.setEnabled(has_group and not self.area_started)
        self.finish_area_button.setEnabled(self.area_started)
        self.cancel_area_button.setEnabled(
            self.area_started or self.area_edit_snapshot is not None
        )
        self.undo_area_button.setEnabled(bool(self.canvas.history))
        self.redo_area_button.setEnabled(bool(self.canvas.redo_stack))
        self.fill_button.setEnabled(has_group and area_count > 0)
        self.fill_settings_button.setEnabled(has_group and area_count > 0)
        fill_matches = (
            has_group
            and self.last_fill is not None
            and self.last_fill.get("group_index") == self.active_group
            and self.state["groups"][self.active_group].get("areas", [])
            == self.last_fill.get("generated_areas", [])
        )
        self.no_fill_button.setEnabled(fill_matches and area_count > 2)
        self.start_dca.setEnabled(has_group and self.area_started)

    def _toggle_measurement(self, enabled):
        self.canvas.measurement_enabled = bool(enabled)
        if enabled:
            self.canvas.drawing_enabled = False
            self.canvas.last_measurement = None
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

    def _toggle_macro_image(self, visible):
        self.canvas.macro_image_visible = bool(visible and self.canvas.image_acquired)
        self.canvas.update()
        self.info.setText(
            "WaferMap image displayed in MacroView."
            if visible
            else "WaferMap image hidden; live Die View remains active."
        )

    def _open_image_display(self):
        if not self.canvas.image_acquired:
            self._acquire()
            return
        self.macro_view_action.setChecked(not self.macro_view_action.isChecked())

    def _stage_moved(self, position):
        x_um = position[0] * self.state["die_size_um"][0]
        y_um = position[1] * self.state["die_size_um"][1]
        self.info.setText(f"Stage position: X {x_um:.2f} um, Y {y_um:.2f} um")

    def _position_inspected(self, position):
        die_x, die_y = self.state.get("selected_die", [0, 0])
        x_um = position[0] * self.state["die_size_um"][0]
        y_um = position[1] * self.state["die_size_um"][1]
        self.info.setText(
            f"Wafer position: Die ({die_x}, {die_y}) | "
            f"Die X {x_um:.2f} um, Y {y_um:.2f} um"
        )

    def _nudge_stage(self, dx, dy):
        x, y = self.canvas.stage_position or (0.5, 0.5)
        self.canvas.set_stage_position(x + float(dx), y + float(dy))

    def _center_stage(self):
        self.canvas.set_stage_position(0.5, 0.5)

    def _fit_die_view(self):
        self.zoom.setValue(100)
        self.info.setText("Die View fitted to the current pane.")

    def _set_care_area_visibility(self, visible):
        for group in self.state["groups"]:
            group["show"] = bool(visible)
        self._refresh()

    def _set_defect_visibility(self, visible):
        self.canvas.show_defects = bool(visible)
        self.canvas.update()

    def _set_ruler_visibility(self, visible):
        self.canvas.show_rulers = bool(visible)
        self.canvas.update()

    def _set_tooltip_visibility(self, visible):
        self.canvas.show_position_tooltips = bool(visible)
        if not visible:
            self.canvas.setToolTip("")

    def _set_layer_opacity(self, value, layer="care_area"):
        key = {
            "die_image": "die_image_opacity",
            "care_area": "care_area_opacity",
            "defect": "defect_opacity",
        }.get(layer, "care_area_opacity")
        self.state[key] = int(value)
        if layer == "care_area":
            self.state["image_opacity"] = int(value)
        slider = getattr(self, "opacity_sliders", {}).get(layer)
        if slider is not None and slider.value() != int(value):
            slider.setValue(int(value))
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

    def _edit_group(self):
        row = self.groups.currentRow()
        if row < 0:
            QMessageBox.information(
                self,
                "Edit Care Area Group",
                "Select a Care Area Group to edit.",
            )
            return
        group = self.state["groups"][row]
        if group.get("kind") == "ACA" or is_page_break_group(group):
            self.active_group = row
            self._edit_page_breaks()
            return
        self.groups.setCurrentCell(row, 0)
        self.groups.editItem(self.groups.item(row, 0))
        self.info.setText("Edit the selected Care Area Group name or its table settings.")

    def _sensitivity_pane(self):
        pane = QFrame()
        pane.setObjectName("pane")
        layout = QVBoxLayout(pane)
        self.sensitivity_content = QWidget()
        sensitivity_layout = QVBoxLayout(self.sensitivity_content)
        sensitivity_layout.setContentsMargins(0, 0, 0, 0)
        sensitivity_layout.addWidget(QLabel("Sensitivity"))
        buttons = QHBoxLayout()
        for label, handler in [
            ("New Threshold", self._add_threshold),
            ("Edit Threshold", self._edit_threshold),
            ("Delete Threshold", self._delete_threshold),
        ]:
            button = QPushButton(label)
            button.clicked.connect(handler)
            buttons.addWidget(button)
        sensitivity_layout.addLayout(buttons)
        self.thresholds = QTableWidget(0, 3)
        self.thresholds.setHorizontalHeaderLabels(["Name", "Algorithm", "Threshold"])
        self.thresholds.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        sensitivity_layout.addWidget(self.thresholds, 1)
        hint = QLabel("Thresholds are assigned to Care Area Groups. Up to 32 regions are supported.")
        hint.setWordWrap(True)
        sensitivity_layout.addWidget(hint)
        layout.addWidget(self.sensitivity_content, 1)
        self.workflow_help = QLabel()
        self.workflow_help.setWordWrap(True)
        self.workflow_help.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.workflow_help.setVisible(False)
        layout.addWidget(self.workflow_help, 1)
        return pane

    def _new_group(self, kind):
        self.area_edit_snapshot = deepcopy(self.state["groups"])
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
        existing_names = {group.get("name") for group in self.state["groups"]}
        name = "ACA"
        suffix = 2
        while name in existing_names:
            name = f"ACA {suffix}"
            suffix += 1
        dialog = AutoCareAreaDialog(name=name, parent=self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result != QDialog.Accepted:
            return
        group_name = dialog.name.text().strip() or name
        if group_name in existing_names:
            QMessageBox.warning(self, "Auto Care Area", "Each group must have a unique name.")
            return
        generated = bool(dialog.result_generated)
        group = {
            "name": group_name,
            "kind": "ACA",
            "threshold": self.state["thresholds"][0]["name"],
            "status": (
                "OK"
                if generated
                else (
                    "Training Area Defined - Page Break generation required"
                    if dialog.training_defined
                    else "Search Area Defined - Training required"
                )
            ),
            "enabled": True,
            "cag_code": len(self.state["groups"]) + 1,
            "show": True,
            "areas": [dialog.search_area()],
            "registered": True,
            "verified": generated,
            "aca": {
            "search_area": dialog.search_area(),
            "training_area": dialog.training_area() if dialog.training_defined else [],
            "use_test_optics": dialog.use_test_optics.isChecked(),
            "skip_fourier_filter": dialog.skip_fourier.isChecked(),
            "cib_parameters": deepcopy(dialog.cib_parameters),
            "page_breaks_generated": generated,
            },
        }
        self.state["groups"].append(group)
        self.state["groups"].extend(deepcopy(dialog.result_generated_groups))
        self.active_group = self.state["groups"].index(group)
        self.canvas.drawing_enabled = False
        if generated:
            self._changed("Auto Care Area and horizontal/vertical Page Break groups generated.")
        else:
            self._changed("ACA Search Area stored. Select Edit to continue training.")

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
        if not parent_group.get("areas"):
            QMessageBox.warning(
                self,
                "Grow/Shrink Care Area",
                "Define at least one Care Area in the selected parent group first.",
            )
            return
        self._open_grow_shrink_editor(parent_group)

    def _open_grow_shrink_editor(self, parent_group):
        self._close_grow_shrink_editor()
        self.grow_shrink_parent_name = str(parent_group.get("name", "Care Area"))
        self.grow_shrink_editor = GrowShrinkCareAreaDialog(
            self.grow_shrink_parent_name,
            die_size_um=self.state.get("die_size_um", [5100.0, 16600.0]),
            embedded=True,
            stage_position_provider=lambda: self.canvas.stage_position or (0.5, 0.5),
            on_measure=self._grow_shrink_measure_started,
            on_preview=self._grow_shrink_preview,
            on_measurement_completed=self._grow_shrink_measurement_completed,
            on_done=self._commit_grow_shrink,
            on_cancel=self._close_grow_shrink_editor,
            parent=self,
        )
        self.edit_care_area_panel.setVisible(False)
        self.die_view_layout.addWidget(self.grow_shrink_editor)
        self.grow_shrink_editor.show()
        self.sensitivity_content.setVisible(False)
        self.workflow_help.setText(
            "Grow & Shrink\n\n"
            "Grow - Enter a positive value to grow an edge.\n\n"
            "Shrink - Enter a negative value to shrink an edge.\n\n"
            "Measure - Press the Measure button for an edge, mark the first site, "
            "move the stage, and mark the second site."
        )
        self.workflow_help.setVisible(True)
        locked_widgets = [
            *self.group_buttons.values(),
            self.promote_button,
            self.demote_button,
            self.more_button,
            self.group_tabs,
            self.overwrite_finish_button,
            self.finish_button,
            self.cancel_button,
        ]
        self.grow_shrink_disabled_states = {
            widget: widget.isEnabled() for widget in locked_widgets
        }
        for widget in locked_widgets:
            widget.setEnabled(False)
        self.canvas.drawing_enabled = False
        self._grow_shrink_preview(self.grow_shrink_editor.margins())
        self.info.setText(
            f"Editing Grow/Shrink Group from parent {self.grow_shrink_parent_name}."
        )

    def _grow_shrink_parent(self):
        return next(
            (
                group
                for group in self.state["groups"]
                if group.get("name") == self.grow_shrink_parent_name
            ),
            None,
        )

    def _grow_shrink_preview(self, margins):
        parent_group = self._grow_shrink_parent()
        self.canvas.derived_preview = (
            grow_shrink_areas(parent_group.get("areas", []), margins)
            if parent_group
            else []
        )
        self.canvas.update()

    def _grow_shrink_measure_started(self, side):
        parent_group = self._grow_shrink_parent()
        areas = parent_group.get("areas", []) if parent_group else []
        if not areas:
            return
        x, y, width, height = [float(value) for value in areas[0][:4]]
        positions = {
            "Left": (x, y + height / 2),
            "Top": (x + width / 2, y),
            "Right": (x + width, y + height / 2),
            "Bottom": (x + width / 2, y + height),
        }
        self.canvas.set_stage_position(*positions[side])
        self.canvas.last_measurement = None
        self.info.setText(
            f"{side} edge measurement: mark the first site, move the stage, then mark the second site."
        )

    def _grow_shrink_measurement_completed(self, side, first, second, value):
        self.canvas.last_measurement = (first, second)
        self.canvas.update()
        self.info.setText(
            f"{side} edge adjustment measured: {value:.2f} um."
        )

    def _commit_grow_shrink(self, name, margins):
        parent_group = self._grow_shrink_parent()
        if parent_group is None:
            QMessageBox.warning(
                self,
                "Grow/Shrink Care Area",
                "The selected parent Care Area Group is no longer available.",
            )
            self._close_grow_shrink_editor()
            return
        if any(group.get("name") == str(name).strip() for group in self.state["groups"]):
            QMessageBox.warning(
                self,
                "Grow/Shrink Care Area",
                "Each Care Area Group must have a unique name.",
            )
            return
        derived_areas = grow_shrink_areas(parent_group.get("areas", []), margins)
        if not derived_areas:
            QMessageBox.warning(
                self,
                "Grow/Shrink Care Area",
                "The edge adjustments remove every Care Area. Reduce the shrink values.",
            )
            return
        self._new_group("Derived")
        group = self.state["groups"][self.active_group]
        group.update({
            "name": str(name).strip(),
            "derived_operation": "grow_shrink",
            "parents": [parent_group["name"]],
            "margins": [float(value) for value in margins],
            "registered": True,
            "verified": True,
            "status": "OK",
        })
        self.area_started = False
        self.area_edit_snapshot = None
        self.canvas.drawing_enabled = False
        self._close_grow_shrink_editor()
        self._changed("Grow/Shrink Care Area Group created from the selected parent.")

    def _close_grow_shrink_editor(self):
        editor = self.grow_shrink_editor
        self.grow_shrink_editor = None
        self.grow_shrink_parent_name = ""
        if editor is not None:
            editor.hide()
            editor.setParent(None)
            editor.deleteLater()
        if hasattr(self, "canvas"):
            self.canvas.derived_preview = []
            self.canvas.last_measurement = None
            self.canvas.update()
        if hasattr(self, "edit_care_area_panel"):
            self.edit_care_area_panel.setVisible(True)
        if hasattr(self, "sensitivity_content"):
            self.sensitivity_content.setVisible(True)
        if hasattr(self, "workflow_help"):
            self.workflow_help.setVisible(False)
        for widget, enabled in self.grow_shrink_disabled_states.items():
            widget.setEnabled(enabled)
        self.grow_shrink_disabled_states = {}

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

    def _fill_settings(self):
        if self.active_group < 0 or not self.state["groups"][self.active_group]["areas"]:
            QMessageBox.warning(self, "Copy & Fill", "Define the first Care Area rectangle before using Fill.")
            return
        dialog = CopyFillDialog(self)
        if self.fill_configuration is not None:
            dialog.set_configuration(self.fill_configuration)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result != QDialog.Accepted:
            return
        self.fill_configuration = dialog.configuration()
        self.info.setText(
            "Fill settings stored: "
            f"{self.fill_configuration['rows']} rows x "
            f"{self.fill_configuration['columns']} columns."
        )
        self._update_edit_controls()

    def _fill(self):
        if self.active_group < 0 or not self.state["groups"][self.active_group]["areas"]:
            QMessageBox.warning(self, "Copy & Fill", "Define the first Care Area rectangle before using Fill.")
            return
        if self.fill_configuration is None:
            dialog = CopyFillDialog(self)
            result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
            if result != QDialog.Accepted:
                return
            self.fill_configuration = dialog.configuration()
        source_area = self.state["groups"][self.active_group]["areas"][0]
        x, y, width, height = source_area[:4]
        area_suffix = list(source_area[4:])
        areas = []
        for row in range(self.fill_configuration["rows"]):
            for column in range(self.fill_configuration["columns"]):
                nx = x + column * (width + self.fill_configuration["gap_x"])
                ny = y + row * (height + self.fill_configuration["gap_y"])
                if nx + width <= 0.99 and ny + height <= 0.99:
                    areas.append([nx, ny, width, height] + area_suffix)
        self.canvas.history.append(deepcopy(self.state["groups"]))
        self.canvas.redo_stack.clear()
        self.state["groups"][self.active_group]["areas"] = areas
        if areas:
            top_left = min(areas, key=lambda area: (float(area[1]), float(area[0])))
            bottom_right = max(areas, key=lambda area: (float(area[1]), float(area[0])))
            self.last_fill = {
                "group_index": self.active_group,
                "generated_areas": deepcopy(areas),
                "endpoint_areas": [deepcopy(top_left), deepcopy(bottom_right)],
            }
        else:
            self.last_fill = None
        self._changed(f"Copy & Fill created {len(areas)} Care Areas.")

    def _no_fill(self):
        if (
            self.active_group < 0
            or self.last_fill is None
            or self.last_fill.get("group_index") != self.active_group
        ):
            return
        areas = self.state["groups"][self.active_group]["areas"]
        generated_areas = self.last_fill.get("generated_areas", [])
        if len(generated_areas) > 2 and areas == generated_areas:
            self.canvas.history.append(deepcopy(self.state["groups"]))
            self.canvas.redo_stack.clear()
            self.state["groups"][self.active_group]["areas"] = deepcopy(
                self.last_fill["endpoint_areas"]
            )
            self._changed(
                "No Fill retained only the upper-left and lower-right Fill endpoint areas."
            )

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
        menu.addSeparator()
        visibility_heading = menu.addAction("Care Area Group Visibility")
        visibility_heading.setEnabled(False)
        show_all = menu.addAction("Show All")
        hide_all = menu.addAction("Hide All")
        menu.addSeparator()
        delete_all = menu.addAction("Delete All Groups")
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
        self.group_buttons["Paste"].setEnabled(True)

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
        parent_name = group["name"]
        existing_children = [
            item for item in self.state["groups"] if item.get("parent") == parent_name
        ]
        dialog = AutoCareAreaDialog(
            name=group.get("name", "ACA"),
            search_area=aca.get("search_area", group.get("areas", [[0.1, 0.1, 0.8, 0.8]])[0]),
            training_area=aca.get("training_area") or None,
            use_test_optics=aca.get("use_test_optics", False),
            skip_fourier=aca.get("skip_fourier_filter", False),
            generated=bool(existing_children) and aca.get("page_breaks_generated", True),
            cib_parameters=aca.get("cib_parameters"),
            parent=self,
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result != QDialog.Accepted:
            return
        new_name = dialog.name.text().strip() or parent_name
        if new_name != parent_name and new_name in {
            item.get("name") for item in self.state["groups"]
        }:
            QMessageBox.warning(self, "Auto Care Area", "Each group must have a unique name.")
            return
        regenerate = bool(
            dialog.result_generated
            and (dialog.generation_requested or not existing_children)
        )
        if regenerate and existing_children:
            answer = QMessageBox.question(
                self,
                "Regenerate Page Breaks",
                "Existing Page Breaks will be deleted and regenerated. Continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
        geometry_changed = (
            list(aca.get("search_area", [])) != dialog.search_area()
            or list(aca.get("training_area", []))
            != (dialog.training_area() if dialog.training_defined else [])
        )
        if regenerate:
            self.state["groups"] = [
                item for item in self.state["groups"]
                if item.get("parent") != parent_name
            ]
        group = next(item for item in self.state["groups"] if item is group)
        group["name"] = new_name
        group["areas"] = [dialog.search_area()]
        group["aca"] = {
            "search_area": dialog.search_area(),
            "training_area": dialog.training_area() if dialog.training_defined else [],
            "use_test_optics": dialog.use_test_optics.isChecked(),
            "skip_fourier_filter": dialog.skip_fourier.isChecked(),
            "cib_parameters": deepcopy(dialog.cib_parameters),
            "page_breaks_generated": bool(dialog.result_generated),
        }
        if regenerate:
            group["status"] = "OK"
            group["verified"] = True
            self.state["groups"].extend(deepcopy(dialog.result_generated_groups))
        elif dialog.result_generated and existing_children:
            group["status"] = "OK"
            group["verified"] = True
            group["aca"]["page_breaks_generated"] = True
        elif geometry_changed and existing_children:
            group["status"] = "Page Break regeneration required"
            group["verified"] = False
            for child in existing_children:
                child["status"] = "Stale - regenerate required"
        else:
            group["status"] = (
                "Training Area Defined - Page Break generation required"
                if dialog.training_defined
                else "Search Area Defined - Training required"
            )
            group["verified"] = False
        if new_name != parent_name:
            for child in self.state["groups"]:
                if child.get("parent") == parent_name:
                    child["parent"] = new_name
                    if child.get("name", "").startswith(parent_name):
                        child["name"] = new_name + child["name"][len(parent_name):]
        self.active_group = self.state["groups"].index(group)
        self._changed(
            "Page Break groups regenerated."
            if regenerate
            else "ACA definition stored. Select Edit to continue training or regenerate Page Breaks."
        )

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
        self.canvas.macro_image_visible = True
        self.macro_view_action.setEnabled(True)
        self.macro_view_action.setChecked(True)
        self.canvas.update()
        self.info.setText("MacroView image acquired.")

    def _refresh(self):
        self._loading = True
        self.groups.setRowCount(len(self.state["groups"]))
        names = [threshold["name"] for threshold in self.state["thresholds"]]
        if any(is_page_break_group(group) for group in self.state["groups"]):
            names.append("Do Not Inspect")
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
        self._update_edit_controls()

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
    def __init__(
        self,
        state,
        on_added,
        on_selected,
        on_measured=None,
        *,
        defects=None,
        on_stage_moved=None,
        on_position_inspected=None,
        parent=None,
    ):
        super().__init__(parent)
        self.state = state
        self.on_added = on_added
        self.on_selected = on_selected
        self.on_measured = on_measured
        self.on_stage_moved = on_stage_moved
        self.on_position_inspected = on_position_inspected
        self.active_group = -1
        self.drawing_enabled = False
        self.image_acquired = False
        self.macro_image_visible = False
        self.show_image = True
        self.show_defects = True
        self.show_rulers = True
        self.show_position_tooltips = True
        self.defects = deepcopy(defects or [])
        self.measurement_enabled = False
        self.zoom = 1.0
        self.start = None
        self.current = None
        self.last_measurement = None
        self.stage_position = None
        self.derived_preview = []
        self.history = []
        self.redo_stack = []
        self.die_image = self._build_simulated_die_image(1200, 1200)
        self.macro_image = self._build_simulated_macro_image(900, 900)
        self.setMinimumSize(460, 460)

    @staticmethod
    def _build_simulated_die_image(width, height):
        image = QPixmap(width, height)
        image.fill(QColor("#111719"))
        painter = QPainter(image)

        # Low-contrast process texture keeps the view photographic without using noise.
        for row in range(0, height, 5):
            shade = 22 + (row * 17 % 19)
            painter.setPen(QPen(QColor(shade, shade + 3, shade + 5), 1))
            painter.drawLine(0, row, width, row)
        for column in range(0, width, 13):
            shade = 36 + (column * 11 % 16)
            painter.setPen(QPen(QColor(shade, shade + 4, shade + 6), 1))
            painter.drawLine(column, 0, column, height)

        # Scribe lanes and alignment marks divide the simulated die into process blocks.
        painter.fillRect(574, 0, 52, height, QColor("#080b0c"))
        painter.fillRect(0, 746, width, 42, QColor("#090c0d"))
        painter.setPen(QPen(QColor("#bac9c7"), 3))
        painter.drawLine(590, 18, 590, 95)
        painter.drawLine(552, 57, 628, 57)
        painter.drawLine(18, 766, 95, 766)
        painter.drawLine(57, 728, 57, 804)

        # Dense memory array: repeated word/bit lines and periodic sense-amplifier blocks.
        painter.fillRect(42, 48, 492, 650, QColor("#1b2528"))
        for y in range(58, 698, 9):
            tone = QColor("#789494") if (y // 9) % 4 else QColor("#b7cbc8")
            painter.setPen(QPen(tone, 1))
            painter.drawLine(48, y, 528, y)
        for x in range(52, 530, 16):
            painter.setPen(QPen(QColor("#405c62"), 2 if x % 64 == 4 else 1))
            painter.drawLine(x, 52, x, 694)
        for bank_y in range(120, 690, 142):
            painter.fillRect(46, bank_y, 484, 13, QColor("#d0d9d2"))
            painter.fillRect(46, bank_y + 4, 484, 3, QColor("#5a7879"))

        # Logic routing: irregular metal tracks, vias, and standard-cell rows.
        painter.fillRect(658, 46, 500, 660, QColor("#172125"))
        route_colors = ("#829fa1", "#c0cfca", "#54777d")
        for index, y in enumerate(range(68, 700, 28)):
            start = 670 + ((index * 67) % 130)
            end = 1138 - ((index * 43) % 110)
            painter.setPen(QPen(QColor(route_colors[index % 3]), 4))
            painter.drawLine(start, y, end, y)
            if index % 2 == 0:
                x = start + (end - start) // 3
                painter.drawLine(x, y, x, min(704, y + 52))
        for index, x in enumerate(range(680, 1140, 37)):
            painter.setBrush(QColor("#d5ddd6") if index % 3 else QColor("#759395"))
            painter.setPen(QPen(QColor("#283b3e"), 1))
            for y in range(82 + index % 4 * 13, 690, 84):
                painter.drawRect(x, y, 7, 7)

        # Lower blocks represent contact arrays and analog/periphery structures.
        painter.fillRect(44, 826, 450, 320, QColor("#202a2c"))
        for y in range(846, 1130, 23):
            for x in range(62, 478, 23):
                tone = 174 + ((x + y) % 38)
                painter.fillRect(x, y, 7, 7, QColor(tone, tone, tone - 5))
                painter.setPen(QPen(QColor("#607579"), 1))
                painter.drawRect(x - 3, y - 3, 13, 13)
        painter.fillRect(660, 826, 496, 320, QColor("#182326"))
        painter.setBrush(Qt.NoBrush)
        for inset in range(0, 130, 18):
            painter.setPen(QPen(QColor(73 + inset, 100 + inset // 2, 104 + inset // 2), 4))
            painter.drawRect(684 + inset, 850 + inset // 2, 440 - inset * 2, 270 - inset)
        painter.setBrush(QColor("#b8cbc6"))
        for x in range(700, 1110, 52):
            painter.drawRect(x, 1100, 22, 15)

        # A few deterministic bright anomalies make defect overlays feel grounded.
        painter.setPen(QPen(QColor("#eef7e9"), 2))
        for x, y in ((214, 243), (447, 582), (786, 337), (1003, 618), (317, 963)):
            painter.drawLine(x - 7, y, x + 7, y)
            painter.drawLine(x, y - 7, x, y + 7)
            painter.drawEllipse(x - 3, y - 3, 6, 6)
        painter.end()
        return image

    @staticmethod
    def _build_simulated_macro_image(width, height):
        image = QPixmap(width, height)
        image.fill(QColor("#1c282c"))
        painter = QPainter(image)
        for row in range(8):
            for column in range(8):
                left = 18 + column * 108
                top = 18 + row * 108
                base = 42 + ((row * 13 + column * 17) % 25)
                painter.fillRect(left, top, 94, 94, QColor(base, base + 17, base + 20))
                painter.setPen(QPen(QColor("#8ea6a5"), 1))
                for offset in range(8, 90, 12):
                    painter.drawLine(left + 5, top + offset, left + 89, top + offset)
                painter.setPen(QPen(QColor("#c4d0ca"), 2))
                painter.drawLine(left + 47, top + 18, left + 47, top + 76)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor("#e4ece6"), 3))
        painter.drawEllipse(6, 6, width - 12, height - 12)
        painter.end()
        return image

    def set_zoom(self, value):
        self.zoom = value / 100.0
        self.update()

    def _view_geometry(self):
        width = max(1.0, self.width() * self.zoom)
        height = max(1.0, self.height() * self.zoom)
        return (
            (self.width() - width) / 2.0,
            (self.height() - height) / 2.0,
            width,
            height,
        )

    def _to_view(self, x, y):
        left, top, width, height = self._view_geometry()
        return left + float(x) * width, top + float(y) * height

    def _from_view(self, x, y):
        left, top, width, height = self._view_geometry()
        return (
            max(0.0, min(1.0, (float(x) - left) / width)),
            max(0.0, min(1.0, (float(y) - top) / height)),
        )

    def _position_text(self, position):
        die_x, die_y = self.state.get("selected_die", [0, 0])
        width_um, height_um = self.state.get("die_size_um", [5100.0, 16600.0])
        return (
            f"Die ({die_x}, {die_y}) | "
            f"X {position[0] * width_um:.2f} um | "
            f"Y {position[1] * height_um:.2f} um"
        )

    def set_stage_position(self, x, y):
        self.stage_position = (
            max(0.0, min(1.0, float(x))),
            max(0.0, min(1.0, float(y))),
        )
        if self.on_stage_moved:
            self.on_stage_moved(self.stage_position)
        self.update()
        return self.stage_position

    def mousePressEvent(self, event):
        pos = event.position() if hasattr(event, "position") else event.pos()
        if (
            event.modifiers() & Qt.ShiftModifier
            and self.image_acquired
            and self.macro_image_visible
        ):
            position = self._from_view(pos.x(), pos.y())
            self.set_stage_position(*position)
            return
        if self.measurement_enabled:
            self.start = (pos.x(), pos.y())
            self.current = self.start
            return
        if not self.drawing_enabled:
            position = self._from_view(pos.x(), pos.y())
            if self.show_position_tooltips:
                self.setToolTip(self._position_text(position))
                if self.on_position_inspected:
                    self.on_position_inspected(position)
            for group_index in reversed(range(len(self.state["groups"]))):
                for area in self.state["groups"][group_index].get("areas", []):
                    x, y, width, height = area[:4]
                    left, top = self._to_view(x, y)
                    right, bottom = self._to_view(x + width, y + height)
                    inside_x = left <= pos.x() <= right
                    inside_y = top <= pos.y() <= bottom
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
            return
        if self.show_position_tooltips:
            pos = event.position() if hasattr(event, "position") else event.pos()
            self.setToolTip(self._position_text(self._from_view(pos.x(), pos.y())))

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
        start_position = self._from_view(x1, y1)
        end_position = self._from_view(x2, y2)
        if self.measurement_enabled:
            self.last_measurement = (start_position, end_position)
            if self.on_measured:
                self.on_measured(start_position, end_position)
            self.update()
            return
        self.history.append(deepcopy(self.state["groups"]))
        self.redo_stack.clear()
        self.on_added([
            min(start_position[0], end_position[0]),
            min(start_position[1], end_position[1]),
            abs(end_position[0] - start_position[0]),
            abs(end_position[1] - start_position[1]),
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
        macro_visible = (
            self.show_image and self.image_acquired and self.macro_image_visible
        )
        painter.fillRect(self.rect(), QColor("#71848b"))
        view_left, view_top, view_width, view_height = self._view_geometry()
        if self.show_image:
            image_opacity = max(
                0,
                min(100, int(self.state.get("die_image_opacity", 65))),
            )
            painter.save()
            painter.setOpacity(image_opacity / 100.0)
            painter.drawPixmap(
                int(view_left),
                int(view_top),
                int(view_width),
                int(view_height),
                self.macro_image if macro_visible else self.die_image,
            )
            painter.restore()
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor("#d8dedc"), 1))
        painter.drawRect(
            int(view_left),
            int(view_top),
            int(view_width),
            int(view_height),
        )
        grid_color = QColor("#9db0b3" if self.show_image else "#81979e")
        grid_color.setAlpha(100 if self.show_image else 255)
        painter.setPen(QPen(grid_color, 1))
        spacing = max(12, int(28 * self.zoom))
        first_x = int(view_left) % spacing
        first_y = int(view_top) % spacing
        for x in range(first_x, self.width(), spacing):
            painter.drawLine(x, 0, x, self.height())
        for y in range(first_y, self.height(), spacing):
            painter.drawLine(0, y, self.width(), y)
        for index, group in enumerate(self.state["groups"]):
            if not group.get("show", True):
                continue
            color = QColor(GROUP_COLORS[index % len(GROUP_COLORS)])
            opacity = max(0, min(100, int(self.state.get("care_area_opacity", 65))))
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
                left, top = self._to_view(x, y)
                right, bottom = self._to_view(x + width, y + height)
                painter.drawRect(
                    int(left),
                    int(top),
                    int(right - left),
                    int(bottom - top),
                )
        for area in self.derived_preview:
            x, y, width, height = [float(value) for value in area[:4]]
            left, top = self._to_view(x, y)
            right, bottom = self._to_view(x + width, y + height)
            rect_left = int(left)
            rect_top = int(top)
            rect_width = max(1, int(right - left))
            rect_height = max(1, int(bottom - top))
            painter.save()
            painter.setClipRect(rect_left, rect_top, rect_width, rect_height)
            preview_fill = QColor("#20b9ca")
            preview_fill.setAlpha(65)
            painter.setBrush(preview_fill)
            painter.setPen(QPen(QColor("#17d9ef"), 3))
            painter.drawRect(rect_left, rect_top, rect_width, rect_height)
            painter.setPen(QPen(QColor("#d8ffff"), 1))
            for offset in range(-rect_height, rect_width, 9):
                painter.drawLine(
                    rect_left + offset,
                    rect_top,
                    rect_left + offset + rect_height,
                    rect_top + rect_height,
                )
            painter.restore()
        if self.show_defects:
            defect_color = QColor("#ef3e36")
            defect_color.setAlpha(
                int(255 * max(0, min(100, int(self.state.get("defect_opacity", 100)))) / 100)
            )
            painter.setBrush(defect_color)
            painter.setPen(QPen(QColor("#8f1714"), 1))
            for defect in self.defects:
                try:
                    x = float(defect.get("x", defect.get("x_rel", -1)))
                    y = float(defect.get("y", defect.get("y_rel", -1)))
                except (TypeError, ValueError):
                    continue
                if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
                    continue
                view_x, view_y = self._to_view(x, y)
                painter.drawEllipse(
                    int(view_x) - 3,
                    int(view_y) - 3,
                    7,
                    7,
                )
        if self.stage_position is not None:
            x, y = self._to_view(*self.stage_position)
            x = int(x)
            y = int(y)
            painter.setPen(QPen(QColor("#20df5b"), 2))
            painter.drawLine(x - 12, y, x + 12, y)
            painter.drawLine(x, y - 12, x, y + 12)
        if self.show_rulers:
            painter.setPen(QPen(QColor("#e9ece8"), 1))
            width_um, height_um = self.state.get("die_size_um", [5100.0, 16600.0])
            for index in range(0, 11):
                x = int(view_left + index * view_width / 10)
                y = int(view_top + index * view_height / 10)
                painter.drawLine(x, max(0, int(view_top)), x, max(0, int(view_top)) + 8)
                painter.drawLine(max(0, int(view_left)), y, max(0, int(view_left)) + 8, y)
                if index in (0, 5, 10):
                    painter.drawText(x + 2, max(12, int(view_top) + 18), f"{width_um * index / 10:.0f}")
                    painter.drawText(max(2, int(view_left) + 10), y - 2, f"{height_um * index / 10:.0f}")
        if self.last_measurement:
            start, end = self.last_measurement
            x1, y1 = self._to_view(*start)
            x2, y2 = self._to_view(*end)
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor("#ffe044"), 2))
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
            painter.drawEllipse(int(x1) - 3, int(y1) - 3, 6, 6)
            painter.drawEllipse(int(x2) - 3, int(y2) - 3, 6, 6)
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
    SIDES = ("Left", "Top", "Right", "Bottom")

    def __init__(
        self,
        parent_name,
        margins=None,
        parent=None,
        *,
        die_size_um=None,
        embedded=False,
        stage_position_provider=None,
        on_measure=None,
        on_preview=None,
        on_measurement_completed=None,
        on_done=None,
        on_cancel=None,
    ):
        super().__init__(parent)
        self.parent_name = str(parent_name)
        self.die_size_um = (
            [float(value) for value in die_size_um[:2]]
            if die_size_um is not None
            else None
        )
        self.stage_position_provider = stage_position_provider
        self.on_measure = on_measure
        self.on_preview = on_preview
        self.on_measurement_completed = on_measurement_completed
        self.on_done = on_done
        self.on_cancel = on_cancel
        self.measurement_side = None
        self.measurement_anchor = None
        self.measurement_original_value = 0.0
        self.measurement_history = []
        self.setWindowTitle(f"Edit Grow/Shrink Group - {self.parent_name}")
        if embedded:
            self.setWindowFlags(Qt.Widget)
        else:
            self.resize(620, 270)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 6, 8, 6)
        self.title_label = QLabel(
            f"Edit Grow/Shrink Group - Parent Group: {self.parent_name}"
        )
        self.title_label.setStyleSheet("font-weight: 600;")
        root.addWidget(self.title_label)

        self.parameter_widget = QWidget()
        parameters = QGridLayout(self.parameter_widget)
        parameters.setContentsMargins(0, 0, 0, 0)
        self.name = QLineEdit(f"{self.parent_name} Grow-Shrink")
        parameters.addWidget(QLabel("Derived Group Name:"), 0, 0)
        parameters.addWidget(self.name, 0, 1, 1, 7)
        unit_text = "microns" if self.die_size_um else "normalized units"
        instructions = QLabel(
            f"Enter a positive value to grow an edge or a negative value to shrink it ({unit_text}). "
            "Use Measure to calculate a value from two stage positions."
        )
        instructions.setWordWrap(True)
        parameters.addWidget(instructions, 1, 0, 1, 8)

        initial_margins = list(margins or [0.01] * 4)
        self.controls = []
        self.control_by_side = {}
        self.measure_buttons = {}
        for index, (side, margin) in enumerate(zip(self.SIDES, initial_margins)):
            row = 2 + index // 2
            column = (index % 2) * 4
            parameters.addWidget(QLabel(side), row, column)
            control = QDoubleSpinBox()
            axis_size = self._axis_size(side)
            if self.die_size_um:
                control.setRange(-axis_size * 0.49, axis_size * 0.49)
                control.setDecimals(2)
                control.setSingleStep(0.5)
                control.setSuffix(" um")
                control.setValue(float(margin) * axis_size)
            else:
                control.setRange(-0.49, 0.49)
                control.setDecimals(4)
                control.setSingleStep(0.005)
                control.setValue(float(margin))
            control.setMinimumWidth(110)
            self.controls.append(control)
            self.control_by_side[side] = control
            parameters.addWidget(control, row, column + 1)
            measure = QPushButton("Measure")
            measure.setIcon(care_area_hand_icon())
            measure.clicked.connect(
                lambda checked=False, edge=side: self._begin_measure(edge)
            )
            self.measure_buttons[side] = measure
            parameters.addWidget(measure, row, column + 2)
            control.valueChanged.connect(self._notify_preview)
        root.addWidget(self.parameter_widget)

        self.measurement_widget = QWidget()
        measurement = QGridLayout(self.measurement_widget)
        measurement.setContentsMargins(0, 0, 0, 0)
        self.measurement_instruction = QLabel()
        self.measurement_instruction.setWordWrap(True)
        measurement.addWidget(self.measurement_instruction, 0, 0, 1, 3)
        self.measure_undo_button = QPushButton("Undo")
        self.measure_undo_button.setIcon(
            self.style().standardIcon(QStyle.SP_ArrowBack)
        )
        self.measure_undo_button.clicked.connect(self._undo_measurement)
        measurement.addWidget(self.measure_undo_button, 1, 0)
        self.mark_site_button = QPushButton("Mark First Site")
        self.mark_site_button.setIcon(care_area_hand_icon())
        self.mark_site_button.clicked.connect(self._mark_measurement_site)
        measurement.addWidget(self.mark_site_button, 1, 1)
        self.cancel_measure_button = QPushButton("Cancel Measure")
        self.cancel_measure_button.setIcon(
            self.style().standardIcon(QStyle.SP_DialogCancelButton)
        )
        self.cancel_measure_button.clicked.connect(self._cancel_measurement)
        measurement.addWidget(self.cancel_measure_button, 1, 2)
        self.measurement_widget.setVisible(False)
        root.addWidget(self.measurement_widget)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self.done_button = QPushButton("Done")
        self.done_button.setIcon(
            self.style().standardIcon(QStyle.SP_DialogApplyButton)
        )
        self.done_button.clicked.connect(self._accept)
        actions.addWidget(self.done_button)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setIcon(
            self.style().standardIcon(QStyle.SP_DialogCancelButton)
        )
        self.cancel_button.clicked.connect(self._cancel)
        actions.addWidget(self.cancel_button)
        root.addLayout(actions)

    def _axis_size(self, side):
        if not self.die_size_um:
            return 1.0
        return self.die_size_um[0 if side in {"Left", "Right"} else 1]

    def margins(self):
        return [
            self.control_by_side[side].value() / self._axis_size(side)
            for side in self.SIDES
        ]

    def _notify_preview(self, _value=None):
        if self.on_preview:
            self.on_preview(self.margins())

    def _begin_measure(self, side):
        self.measurement_side = side
        self.measurement_anchor = None
        self.measurement_original_value = self.control_by_side[side].value()
        self.parameter_widget.setVisible(False)
        self.measurement_widget.setVisible(True)
        self.mark_site_button.setText("Mark First Site")
        self.measure_undo_button.setEnabled(bool(self.measurement_history))
        self.measurement_instruction.setText(
            f"Move the stage to the {side.lower()} edge of a care area and click Mark First Site."
        )
        if self.on_measure:
            self.on_measure(side)

    def _current_stage_position(self):
        if self.stage_position_provider:
            position = self.stage_position_provider()
            if position is not None:
                return tuple(float(value) for value in position[:2])
        return (0.5, 0.5)

    def _mark_measurement_site(self):
        if self.measurement_side is None:
            return
        position = self._current_stage_position()
        if self.measurement_anchor is None:
            self.measurement_anchor = position
            self.mark_site_button.setText("Mark Second Site")
            self.measurement_instruction.setText(
                "Move the stage outward to grow the edge or inward to shrink it, "
                "then click Mark Second Site."
            )
            self.measure_undo_button.setEnabled(True)
            return
        first = self.measurement_anchor
        second = position
        axis = 0 if self.measurement_side in {"Left", "Right"} else 1
        direction = -1.0 if self.measurement_side in {"Left", "Top"} else 1.0
        measured = direction * (second[axis] - first[axis]) * self._axis_size(
            self.measurement_side
        )
        control = self.control_by_side[self.measurement_side]
        previous = control.value()
        self.measurement_history.append((self.measurement_side, previous))
        control.setValue(measured)
        if self.on_measurement_completed:
            self.on_measurement_completed(
                self.measurement_side, first, second, measured
            )
        self._leave_measurement_mode()

    def _undo_measurement(self):
        if self.measurement_anchor is not None:
            self.measurement_anchor = None
            self.mark_site_button.setText("Mark First Site")
            self.measurement_instruction.setText(
                f"First site cleared. Move the stage to the {self.measurement_side.lower()} edge and mark it again."
            )
            self.measure_undo_button.setEnabled(bool(self.measurement_history))
            return
        if self.measurement_history:
            side, previous = self.measurement_history.pop()
            self.control_by_side[side].setValue(previous)
            self._notify_preview()

    def _cancel_measurement(self):
        if self.measurement_side is not None:
            self.control_by_side[self.measurement_side].setValue(
                self.measurement_original_value
            )
        self._leave_measurement_mode()
        self._notify_preview()

    def _leave_measurement_mode(self):
        self.measurement_side = None
        self.measurement_anchor = None
        self.measurement_widget.setVisible(False)
        self.parameter_widget.setVisible(True)

    def _cancel(self):
        if self.on_cancel:
            self.on_cancel()
        else:
            self.reject()

    def _accept(self):
        name = self.name.text().strip()
        if not name:
            QMessageBox.warning(self, "Grow/Shrink Care Area", "Enter a derived group name.")
            return
        if self.measurement_side is not None:
            QMessageBox.warning(
                self,
                "Grow/Shrink Care Area",
                "Mark the second site or cancel the active measurement before finishing.",
            )
            return
        if self.on_done:
            self.on_done(name, self.margins())
        else:
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

    def configuration(self):
        return {
            "rows": self.rows.value(),
            "columns": self.columns.value(),
            "gap_x": self.gap_x.value(),
            "gap_y": self.gap_y.value(),
        }

    def set_configuration(self, configuration):
        self.rows.setValue(int(configuration.get("rows", 3)))
        self.columns.setValue(int(configuration.get("columns", 3)))
        self.gap_x.setValue(float(configuration.get("gap_x", 0.0)))
        self.gap_y.setValue(float(configuration.get("gap_y", 0.0)))


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


class AutoCareAreaPreview(QWidget):
    def __init__(self, on_stage_moved=None, parent=None):
        super().__init__(parent)
        self.on_stage_moved = on_stage_moved
        self.search_area = None
        self.training_area = None
        self.page_break_groups = []
        self.stage_position = [0.08, 0.10]
        self.pending_start = None
        self.setMinimumSize(500, 440)

    def set_regions(
        self,
        search_area,
        training_area,
        page_break_groups,
        *,
        pending_start=None,
    ):
        self.search_area = list(search_area) if search_area else None
        self.training_area = list(training_area) if training_area else None
        self.page_break_groups = deepcopy(page_break_groups)
        self.pending_start = list(pending_start) if pending_start else None
        self.update()

    def set_stage_position(self, x, y):
        self.stage_position = [
            min(1.0, max(0.0, float(x))),
            min(1.0, max(0.0, float(y))),
        ]
        self.update()

    def _geometry(self):
        margin = 22
        width = max(1, self.width() - margin * 2)
        height = max(1, self.height() - margin * 2)
        return margin, margin, width, height

    def _to_view(self, x, y):
        left, top, width, height = self._geometry()
        return left + x * width, top + y * height

    def _from_view(self, x, y):
        left, top, width, height = self._geometry()
        return (
            min(1.0, max(0.0, (x - left) / width)),
            min(1.0, max(0.0, (y - top) / height)),
        )

    def mousePressEvent(self, event):
        pos = event.position() if hasattr(event, "position") else event.pos()
        x, y = self._from_view(pos.x(), pos.y())
        self.set_stage_position(x, y)
        if self.on_stage_moved:
            self.on_stage_moved(x, y)

    def _draw_area(self, painter, area, color, width=2, fill_alpha=45):
        x, y, area_width, area_height = area[:4]
        left, top = self._to_view(x, y)
        right, bottom = self._to_view(x + area_width, y + area_height)
        fill = QColor(color)
        fill.setAlpha(fill_alpha)
        painter.setBrush(fill)
        painter.setPen(QPen(QColor(color), width))
        painter.drawRect(
            int(left),
            int(top),
            max(1, int(right - left)),
            max(1, int(bottom - top)),
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#777975"))
        left, top, width, height = self._geometry()
        painter.fillRect(left, top, width, height, QColor("#b5b6b1"))
        painter.setPen(QPen(QColor("#8f908b"), 1))
        for column in range(1, 25):
            x = int(left + column * width / 25)
            painter.drawLine(x, top, x, top + height)
        for row in range(1, 17):
            y = int(top + row * height / 17)
            painter.drawLine(left, y, left + width, y)
        painter.setPen(QPen(QColor("#6b6c67"), 1))
        for row in range(0, 16, 2):
            for column in range(0, 24, 3):
                x = int(left + (column + 0.25) * width / 25)
                y = int(top + (row + 0.35) * height / 17)
                painter.drawRect(x, y, max(2, int(width / 80)), max(2, int(height / 60)))
        if self.search_area:
            self._draw_area(painter, self.search_area, "#47d1c8", 2, 38)
        if self.training_area:
            self._draw_area(painter, self.training_area, "#ffe21a", 3, 65)
        for group in self.page_break_groups:
            color = "#e31b23" if group.get("kind") == "Horizontal Page Break" else "#111111"
            for area in group.get("areas", []):
                self._draw_area(painter, area, color, 1, 140)
        if self.pending_start:
            x, y = self._to_view(*self.pending_start)
            painter.setPen(QPen(QColor("#2774d8"), 2))
            painter.drawEllipse(int(x) - 7, int(y) - 7, 14, 14)
        x, y = self._to_view(*self.stage_position)
        painter.setPen(QPen(QColor("#e31b23"), 2))
        painter.drawLine(int(x) - 10, int(y), int(x) + 10, int(y))
        painter.drawLine(int(x), int(y) - 10, int(x), int(y) + 10)
        painter.setPen(QPen(QColor("#f3f3ef"), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(left, top, width, height)
        painter.end()


class AcaCibParametersDialog(QDialog):
    def __init__(self, parameters=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit ACA CIB Parameters")
        self.setFixedSize(430, 250)
        values = parameters or {}
        layout = QGridLayout(self)
        self.controls = {}
        for row, (key, label, minimum, maximum, default) in enumerate(
            (
                ("clip", "Clip:", 0.0, 100.0, 4.0),
                ("offset", "Offset:", -100.0, 100.0, 0.0),
                ("l0", "L0:", 0.0, 100.0, 1.0),
                ("k", "K:", 0.01, 100.0, 1.0),
            )
        ):
            control = QDoubleSpinBox()
            control.setRange(minimum, maximum)
            control.setDecimals(3)
            control.setValue(float(values.get(key, default)))
            self.controls[key] = control
            layout.addWidget(QLabel(label), row, 0)
            layout.addWidget(control, row, 1)
        note = QLabel("These parameters control periodic-boundary detection during ACA generation.")
        note.setWordWrap(True)
        layout.addWidget(note, 4, 0, 1, 2)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        ok = QPushButton("OK")
        ok.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        layout.addLayout(buttons, 5, 0, 1, 2)

    def parameters(self):
        return {key: control.value() for key, control in self.controls.items()}


class AutoCareAreaDialog(QDialog):
    def __init__(
        self,
        name="ACA",
        search_area=None,
        training_area=None,
        use_test_optics=False,
        skip_fourier=False,
        generated=False,
        cib_parameters=None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Edit Auto Care Area")
        self.resize(1080, 680)
        self.search_defined = search_area is not None
        self.training_defined = training_area is not None
        self.generated = bool(generated and self.training_defined)
        self.generation_requested = False
        self.result_generated = False
        self.result_generated_groups = []
        self.pending_kind = None
        self.pending_start = None
        self.history = []
        self.redo_stack = []
        self._loading = True
        self.cib_parameters = deepcopy(cib_parameters or aca_dram_example()["cib_parameters"])

        root = QVBoxLayout(self)
        content = QHBoxLayout()
        left = QVBoxLayout()
        left.addWidget(QLabel("Die View - ACA Search and Training Regions"))
        self.preview = AutoCareAreaPreview(self._preview_stage_moved)
        left.addWidget(self.preview, 1)
        legend = QLabel(
            "Cyan: Search Area   Yellow: ACA Training Area   Red/Black: Do Not Inspect Page Breaks"
        )
        legend.setWordWrap(True)
        left.addWidget(legend)
        content.addLayout(left, 3)

        panel = QGridLayout()
        self.name = QLineEdit(name)
        panel.addWidget(QLabel("Care Area Group:"), 0, 0)
        panel.addWidget(self.name, 0, 1, 1, 4)
        panel.addWidget(QLabel("Normalized die coordinates"), 1, 0, 1, 5)
        headers = ["", "X", "Y", "Width", "Height"]
        for column, text in enumerate(headers):
            panel.addWidget(QLabel(text), 2, column)
        self.search_controls = self._area_controls(search_area or [0.08, 0.10, 0.84, 0.80])
        self.training_controls = self._area_controls(training_area or [0.08, 0.10, 0.14, 0.16])
        for row, (label, controls) in enumerate(
            (("Search Area", self.search_controls), ("Training Area", self.training_controls)),
            start=3,
        ):
            panel.addWidget(QLabel(label), row, 0)
            for column, control in enumerate(controls, start=1):
                panel.addWidget(control, row, column)
        for control in self.search_controls:
            control.valueChanged.connect(lambda value: self._coordinates_changed("search"))
        for control in self.training_controls:
            control.valueChanged.connect(lambda value: self._coordinates_changed("training"))

        panel.addWidget(QLabel("Stage Cursor:"), 5, 0)
        self.stage_x = QDoubleSpinBox()
        self.stage_y = QDoubleSpinBox()
        for control, value in ((self.stage_x, 0.08), (self.stage_y, 0.10)):
            control.setRange(0.0, 1.0)
            control.setDecimals(3)
            control.setSingleStep(0.01)
            control.setValue(value)
            control.valueChanged.connect(self._stage_changed)
        panel.addWidget(QLabel("X"), 5, 1)
        panel.addWidget(self.stage_x, 5, 2)
        panel.addWidget(QLabel("Y"), 5, 3)
        panel.addWidget(self.stage_y, 5, 4)

        self.start_search_button = QPushButton("Start Search Area")
        self.start_search_button.clicked.connect(lambda: self._start_region("search"))
        self.finish_search_button = QPushButton("Finish Search Area")
        self.finish_search_button.clicked.connect(lambda: self._finish_region("search"))
        panel.addWidget(self.start_search_button, 6, 0, 1, 2)
        panel.addWidget(self.finish_search_button, 6, 2, 1, 3)
        self.start_training_button = QPushButton("Start ACA Training Area")
        self.start_training_button.clicked.connect(lambda: self._start_region("training"))
        self.finish_training_button = QPushButton("Finish ACA Training Area")
        self.finish_training_button.clicked.connect(lambda: self._finish_region("training"))
        panel.addWidget(self.start_training_button, 7, 0, 1, 2)
        panel.addWidget(self.finish_training_button, 7, 2, 1, 3)

        self.use_test_optics = QCheckBox("Use Test Optics")
        self.use_test_optics.setChecked(bool(use_test_optics))
        self.skip_fourier = QCheckBox("Skip Fourier Filter")
        self.skip_fourier.setChecked(bool(skip_fourier))
        self.use_test_optics.stateChanged.connect(self._option_changed)
        self.skip_fourier.stateChanged.connect(self._option_changed)
        self.name.textChanged.connect(self._name_changed)
        panel.addWidget(self.use_test_optics, 8, 0, 1, 2)
        panel.addWidget(self.skip_fourier, 8, 2, 1, 3)

        self.load_example_button = QPushButton("Load DRAM Example")
        self.load_example_button.setToolTip("Load a complete repeating-cell ACA case for validation")
        self.load_example_button.clicked.connect(self._load_example)
        self.edit_cib_button = QPushButton("Edit CIB Parameters...")
        self.edit_cib_button.clicked.connect(self._edit_cib_parameters)
        panel.addWidget(self.load_example_button, 9, 0, 1, 2)
        panel.addWidget(self.edit_cib_button, 9, 2, 1, 3)

        history_buttons = QHBoxLayout()
        self.undo_button = QPushButton("Undo")
        self.undo_button.clicked.connect(self._undo)
        self.redo_button = QPushButton("Redo")
        self.redo_button.clicked.connect(self._redo)
        history_buttons.addWidget(self.undo_button)
        history_buttons.addWidget(self.redo_button)
        panel.addLayout(history_buttons, 10, 0, 1, 2)
        self.generate_button = QPushButton("Generate Page Break")
        self.generate_button.clicked.connect(self._generate)
        panel.addWidget(self.generate_button, 10, 2, 1, 3)

        self.status = QLabel()
        self.status.setWordWrap(True)
        self.status.setMinimumHeight(70)
        panel.addWidget(self.status, 11, 0, 1, 5)
        panel.setRowStretch(12, 1)
        content.addLayout(panel, 2)
        root.addLayout(content, 1)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self.done_button = QPushButton("Done")
        self.done_button.clicked.connect(self._done)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        actions.addWidget(self.done_button)
        actions.addWidget(self.cancel_button)
        root.addLayout(actions)

        self._loading = False
        if self.generated:
            try:
                self.result_generated_groups = generate_page_break_groups(
                    self.search_area(), self.training_area(), self.name.text().strip() or "ACA"
                )
            except ValueError:
                self.generated = False
                self.result_generated_groups = []
        self._update_workflow()

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

    def _set_area(self, controls, area):
        self._loading = True
        for control, value in zip(controls, area):
            control.setValue(float(value))
        self._loading = False

    def _snapshot(self):
        return {
            "search_area": self.search_area(),
            "training_area": self.training_area(),
            "search_defined": self.search_defined,
            "training_defined": self.training_defined,
            "generated": self.generated,
            "groups": deepcopy(self.result_generated_groups),
            "cib_parameters": deepcopy(self.cib_parameters),
            "generation_requested": self.generation_requested,
            "pending_kind": self.pending_kind,
            "pending_start": deepcopy(self.pending_start),
            "stage": [self.stage_x.value(), self.stage_y.value()],
        }

    def _restore(self, snapshot):
        self._set_area(self.search_controls, snapshot["search_area"])
        self._set_area(self.training_controls, snapshot["training_area"])
        self.search_defined = snapshot["search_defined"]
        self.training_defined = snapshot["training_defined"]
        self.generated = snapshot["generated"]
        self.result_generated_groups = deepcopy(snapshot["groups"])
        self.cib_parameters = deepcopy(snapshot["cib_parameters"])
        self.generation_requested = snapshot["generation_requested"]
        self.pending_kind = snapshot["pending_kind"]
        self.pending_start = deepcopy(snapshot["pending_start"])
        self._loading = True
        self.stage_x.setValue(snapshot["stage"][0])
        self.stage_y.setValue(snapshot["stage"][1])
        self._loading = False
        self._update_workflow()

    def _remember(self):
        self.history.append(self._snapshot())
        self.redo_stack.clear()

    def _undo(self):
        if not self.history:
            return
        self.redo_stack.append(self._snapshot())
        self._restore(self.history.pop())

    def _redo(self):
        if not self.redo_stack:
            return
        self.history.append(self._snapshot())
        self._restore(self.redo_stack.pop())

    def _coordinates_changed(self, kind):
        if self._loading:
            return
        if kind == "search":
            self.search_defined = self.search_area()[2] > 0 and self.search_area()[3] > 0
        else:
            self.training_defined = self.training_area()[2] > 0 and self.training_area()[3] > 0
        self.generated = False
        self.generation_requested = False
        self.result_generated_groups = []
        self._update_workflow()

    def _option_changed(self, value=None):
        if self._loading:
            return
        self.generated = False
        self.generation_requested = False
        self.result_generated_groups = []
        self._update_workflow("Optics selection changed; regenerate Page Breaks to apply it.")

    def _name_changed(self, value):
        if self._loading or not self.generated:
            return
        parent_name = value.strip() or "ACA"
        for group in self.result_generated_groups:
            suffix = " Horizontal Page Break" if group.get("kind") == "Horizontal Page Break" else " Vertical Page Break"
            group["parent"] = parent_name
            group["name"] = parent_name + suffix

    def _stage_changed(self, value=None):
        if self._loading:
            return
        self.preview.set_stage_position(self.stage_x.value(), self.stage_y.value())

    def _preview_stage_moved(self, x, y):
        self._loading = True
        self.stage_x.setValue(x)
        self.stage_y.setValue(y)
        self._loading = False
        self.preview.set_stage_position(x, y)

    def _start_region(self, kind):
        if self.pending_kind:
            return
        self._remember()
        self.pending_kind = kind
        self.pending_start = [self.stage_x.value(), self.stage_y.value()]
        self.generated = False
        self.generation_requested = False
        self.result_generated_groups = []
        self._update_workflow()

    def _finish_region(self, kind):
        if self.pending_kind != kind or self.pending_start is None:
            return
        x1, y1 = self.pending_start
        x2, y2 = self.stage_x.value(), self.stage_y.value()
        area = [min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1)]
        if area[2] < 0.002 or area[3] < 0.002:
            QMessageBox.warning(
                self,
                "Auto Care Area",
                "Move the stage to a different lower corner before finishing the region.",
            )
            return
        self._remember()
        if kind == "search":
            self._set_area(self.search_controls, area)
            self.search_defined = True
            if self.training_defined:
                try:
                    generate_page_break_groups(area, self.training_area(), self.name.text().strip() or "ACA")
                except ValueError:
                    self.training_defined = False
        else:
            self._set_area(self.training_controls, area)
            self.training_defined = True
        self.pending_kind = None
        self.pending_start = None
        self.generated = False
        self.generation_requested = False
        self.result_generated_groups = []
        self._update_workflow()

    def _load_example(self):
        self._remember()
        example = aca_dram_example()
        self.name.setText(example["name"])
        self._set_area(self.search_controls, example["search_area"])
        self._set_area(self.training_controls, example["training_area"])
        self.search_defined = True
        self.training_defined = True
        self.use_test_optics.setChecked(example["use_test_optics"])
        self.skip_fourier.setChecked(example["skip_fourier_filter"])
        self.cib_parameters = deepcopy(example["cib_parameters"])
        self.pending_kind = None
        self.pending_start = None
        self.generated = False
        self.generation_requested = False
        self.result_generated_groups = []
        self._update_workflow("DRAM repeating-cell example loaded. Generate Page Breaks to analyze it.")

    def _edit_cib_parameters(self):
        dialog = AcaCibParametersDialog(self.cib_parameters, self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self._remember()
            self.cib_parameters = dialog.parameters()
            self.generated = False
            self.generation_requested = False
            self.result_generated_groups = []
            self._update_workflow("CIB parameters updated; regenerate Page Breaks to apply them.")

    def _generate(self):
        if not self.search_defined or not self.training_defined:
            QMessageBox.warning(
                self,
                "Auto Care Area",
                "Define the Search Area and ACA Training Area before generating Page Breaks.",
            )
            return
        try:
            generated_groups = generate_page_break_groups(
                self.search_area(),
                self.training_area(),
                self.name.text().strip() or "ACA",
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Auto Care Area", str(exc))
            return
        self._remember()
        self.status.setText("Analyzing periodic boundaries and calculating Page Breaks...")
        QApplication.processEvents()
        self.result_generated_groups = generated_groups
        self.generated = True
        self.generation_requested = True
        self._update_workflow()

    def _done(self):
        if not self.name.text().strip():
            QMessageBox.warning(self, "Auto Care Area", "Enter a Care Area Group name.")
            return
        if self.pending_kind:
            QMessageBox.warning(self, "Auto Care Area", "Finish or undo the active region first.")
            return
        if not self.search_defined:
            QMessageBox.warning(self, "Auto Care Area", "Define the Search Area before saving ACA.")
            return
        self.result_generated = bool(self.generated)
        self.accept()

    def _accept(self):
        self._generate()

    def _update_workflow(self, message=None):
        pending_search = self.pending_kind == "search"
        pending_training = self.pending_kind == "training"
        self.start_search_button.setEnabled(self.pending_kind is None)
        self.finish_search_button.setEnabled(pending_search)
        self.start_training_button.setEnabled(self.search_defined and self.pending_kind is None)
        self.finish_training_button.setEnabled(pending_training)
        self.generate_button.setEnabled(
            self.search_defined and self.training_defined and self.pending_kind is None
        )
        self.done_button.setEnabled(self.search_defined and self.pending_kind is None)
        self.undo_button.setEnabled(bool(self.history))
        self.redo_button.setEnabled(bool(self.redo_stack))
        if message is None:
            if pending_search:
                message = "Move the stage to the opposite Search Area corner, then click Finish Search Area."
            elif pending_training:
                message = "Move the stage to the opposite training-cell corner, then click Finish ACA Training Area."
            elif self.generated:
                horizontal = next(
                    (group for group in self.result_generated_groups if group["kind"] == "Horizontal Page Break"),
                    {"areas": []},
                )
                vertical = next(
                    (group for group in self.result_generated_groups if group["kind"] == "Vertical Page Break"),
                    {"areas": []},
                )
                message = (
                    f"Generation complete: {len(horizontal['areas'])} horizontal and "
                    f"{len(vertical['areas'])} vertical Do Not Inspect Page Breaks. Click Done to keep them."
                )
            elif self.training_defined:
                message = "Training Area defined. Generate Page Breaks, or click Done to save and continue later."
            elif self.search_defined:
                message = "Search Area defined. Mark the ACA Training Area, or click Done to continue later."
            else:
                message = "Mark the upper-left and lower-right corners of the ACA Search Area."
        self.status.setText(message)
        self.preview.set_stage_position(self.stage_x.value(), self.stage_y.value())
        self.preview.set_regions(
            self.search_area() if self.search_defined else None,
            self.training_area() if self.training_defined else None,
            self.result_generated_groups if self.generated else [],
            pending_start=self.pending_start,
        )


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

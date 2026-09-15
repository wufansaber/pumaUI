from __future__ import annotations

from copy import deepcopy
from pathlib import Path

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
    QIcon,
    QLabel,
    QLineEdit,
    QMenu,
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
    QTimer,
    Qt,
    QVBoxLayout,
    QWidget,
)

from .care_areas import SetupReviewDefectsDialog


MAX_NANOPOINT_TARGETS = 30


def nanopoint_tool_icon(name):
    pixmap = QPixmap(26, 26)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setPen(QPen(QColor("#57554f"), 1))
    if name == "Mark":
        painter.setBrush(QColor("#e7efec"))
        painter.drawRect(3, 3, 18, 19)
        painter.setBrush(QColor("#56bcae"))
        painter.drawRect(5, 5, 14, 5)
        painter.setBrush(QColor("#51b84c"))
        painter.drawEllipse(14, 14, 9, 9)
        painter.setPen(QPen(QColor("#ffffff"), 2))
        painter.drawLine(16, 18, 18, 20)
        painter.drawLine(18, 20, 22, 15)
    elif name == "Import":
        painter.setBrush(QColor("#c69a5a"))
        painter.drawRect(4, 14, 18, 8)
        painter.setPen(QPen(QColor("#338fbd"), 3))
        painter.drawLine(13, 2, 13, 16)
        painter.drawLine(8, 11, 13, 16)
        painter.drawLine(18, 11, 13, 16)
    elif name == "Delete":
        painter.setBrush(QColor("#8c9b0d"))
        painter.drawRect(3, 4, 13, 17)
        painter.setBrush(QColor("#e5221c"))
        painter.setPen(QPen(QColor("#e5221c"), 1))
        painter.drawEllipse(11, 10, 13, 13)
        painter.setPen(QPen(QColor("#ffffff"), 2))
        painter.drawLine(14, 16, 21, 16)
    elif name.startswith("Flip"):
        painter.setPen(QPen(QColor("#bd6b73"), 2))
        if name in {"Flip H", "Flip Both"}:
            painter.drawLine(4, 13, 22, 13)
            painter.drawLine(4, 13, 8, 9)
            painter.drawLine(4, 13, 8, 17)
            painter.drawLine(22, 13, 18, 9)
            painter.drawLine(22, 13, 18, 17)
        if name in {"Flip V", "Flip Both"}:
            painter.drawLine(13, 4, 13, 22)
            painter.drawLine(13, 4, 9, 8)
            painter.drawLine(13, 4, 17, 8)
            painter.drawLine(13, 22, 9, 18)
            painter.drawLine(13, 22, 17, 18)
    elif name == "Edit Box":
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor("#ee2721"), 2, Qt.DashLine))
        painter.drawRect(5, 5, 16, 16)
        painter.setPen(QPen(QColor("#333333"), 2))
        painter.drawLine(2, 13, 8, 13)
        painter.drawLine(13, 2, 13, 8)
    elif name == "Reset Boxes":
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor("#e8322d"), 2, Qt.DashLine))
        painter.drawRect(5, 5, 16, 16)
        painter.drawEllipse(2, 2, 22, 22)
    painter.end()
    return QIcon(pixmap)


def nanopoint_thumbnail_icon(has_sem=False):
    pixmap = QPixmap(68, 30)
    pixmap.fill(QColor("#080a0b"))
    painter = QPainter(pixmap)
    painter.setPen(QPen(QColor("#e5e8e6"), 1))
    for left in (2, 36):
        painter.drawLine(left + 3, 15, left + 29, 15)
        painter.drawLine(left + 12, 12, left + 19, 12)
        painter.drawLine(left + 12, 18, left + 19, 18)
        painter.drawRect(left, 1, 30, 27)
    if has_sem:
        painter.setPen(QPen(QColor("#55d88b"), 1))
        painter.drawRect(48, 8, 10, 14)
    painter.end()
    return QIcon(pixmap)


def default_nanopoint_state():
    return {
        "defect_source": "",
        "reference_die": [0, 0],
        "templates": [],
        "images_grabbed": False,
        "valid": True,
        "image_type": "Test",
        "show_ca": True,
        "show_noise": True,
        "show_poi": True,
        "false_colors": False,
        "auto_scale": True,
        "zoom": 100,
        "mca_size": 5,
        "noise_box_size": 64,
        "sem_opacity": 60,
        "show_sem_bounding_box": True,
        "magnifier": False,
        "magnifier_grid": False,
        "poi_search_complete": False,
        "marked_defects": [],
        "color_scale_min": 0,
        "color_scale_max": 4000,
    }


def default_sem_state():
    return {
        "path": "",
        "visible": False,
        "fov_um": 25.0,
        "rotation": 0,
        "care_area": [],
        "matches": [],
        "selected_match": -1,
        "correlated": False,
    }


def normalize_nanopoint_state(state):
    result = default_nanopoint_state()
    if isinstance(state, dict):
        result.update(deepcopy(state))
    result["templates"] = deepcopy(result.get("templates") or [])
    result["marked_defects"] = deepcopy(result.get("marked_defects") or [])
    for template in result["templates"]:
        sem = default_sem_state()
        sem.update(deepcopy(template.get("sem") or {}))
        template["sem"] = sem
        template["has_sem_image"] = bool(template.get("has_sem_image") or sem.get("path"))
        template.setdefault("care_area", [0.30, 0.34, 0.40, 0.24])
        template.setdefault("noise_box", [0.15, 0.15, 0.70, 0.62])
        template.setdefault("poi_box", [0.47, 0.45, 0.06, 0.08])
    die = result.get("reference_die") or [0, 0]
    result["reference_die"] = [int(die[0]), int(die[1])]
    return result


def validate_nanopoint_state(state):
    state = normalize_nanopoint_state(state)
    errors = []
    if not 5 <= int(state.get("mca_size", 5)) <= 21:
        errors.append("NanoPoint MCA size must be between 5 and 21")
    if not 48 <= int(state.get("noise_box_size", 64)) <= 80:
        errors.append("NanoPoint noise box size must be between 48 and 80")
    if len(state["templates"]) > MAX_NANOPOINT_TARGETS:
        errors.append("NanoPoint Image Templates supports at most 30 target types")
    names = []
    for index, template in enumerate(state["templates"], start=1):
        name = str(template.get("name", "")).strip()
        if not name:
            errors.append(f"template {index} requires a name")
        names.append(name.casefold())
        for field in ("confidence", "uniqueness"):
            value = float(template.get(field, 0))
            if not 0 <= value <= 1:
                errors.append(f"template {index} {field} must be between 0 and 1")
        threshold = float(template.get("search_threshold", 0.75))
        if not 0.5 <= threshold <= 1:
            errors.append(f"template {index} search threshold must be between 0.5 and 1")
    if len(names) != len(set(names)):
        errors.append("NanoPoint template names must be unique")
    if state["templates"] and not state.get("defect_source"):
        errors.append("select defect data for NanoPoint Image Templates")
    if state["templates"] and not state.get("images_grabbed"):
        errors.append("grab images for all NanoPoint templates")
    if state["templates"] and not state.get("valid", True):
        errors.append("NanoPoint Image Template data is invalid and must be recreated")
    return errors


def sem_correlation_candidates(care_area):
    x, y, width, height = [float(value) for value in care_area[:4]]
    candidates = []
    for index, (dx, dy, score) in enumerate(((0.0, 0.0, 0.96), (-0.04, 0.02, 0.88), (0.05, -0.03, 0.81))):
        nx = min(max(0.0, x + dx), max(0.0, 1.0 - width))
        ny = min(max(0.0, y + dy), max(0.0, 1.0 - height))
        candidates.append({"name": f"Match {index + 1}", "score": score, "area": [nx, ny, width, height]})
    return candidates


def apply_sem_correlation(template, care_area, selected_match=0):
    result = deepcopy(template)
    sem = default_sem_state()
    sem.update(deepcopy(result.get("sem") or {}))
    matches = sem_correlation_candidates(care_area)
    if not 0 <= int(selected_match) < len(matches):
        raise ValueError("select a valid SEM correlation result")
    sem.update(
        {
            "care_area": deepcopy(matches[int(selected_match)]["area"]),
            "matches": matches,
            "selected_match": int(selected_match),
            "correlated": True,
        }
    )
    result["sem"] = sem
    return result


def accept_sem_correlation_match(template, selected_match):
    result = deepcopy(template)
    sem = default_sem_state()
    sem.update(deepcopy(result.get("sem") or {}))
    matches = deepcopy(sem.get("matches") or [])
    selected_match = int(selected_match)
    if not 0 <= selected_match < len(matches):
        raise ValueError("select a valid SEM correlation result")
    sem.update(
        {
            "care_area": deepcopy(matches[selected_match]["area"]),
            "matches": matches,
            "selected_match": selected_match,
            "correlated": True,
        }
    )
    result["sem"] = sem
    return result


def imported_template(number, care_area_names, defect=None):
    defect = defect if isinstance(defect, dict) else {}
    defect_id = int(defect.get("id", number))
    x = float(defect.get("x", defect.get("x_rel", number - 1)))
    y = float(defect.get("y", defect.get("y_rel", number - 1)))
    sem = default_sem_state()
    sem["path"] = str(defect.get("sem_path") or "")
    return {
        "name": str(defect.get("name") or f"Target {defect_id}"),
        "confidence": 0.0,
        "uniqueness": 0.0,
        "search_threshold": 0.75,
        "search": True,
        "class_code": int(defect.get("class_code", defect_id)),
        "location": [x, y],
        "linked_care_area": care_area_names[0] if care_area_names else "",
        "care_area": [0.30, 0.34, 0.40, 0.24],
        "noise_box": [0.15, 0.15, 0.70, 0.62],
        "poi_box": [0.47, 0.45, 0.06, 0.08],
        "flips": [],
        "source_defect_id": defect_id,
        "has_patch_images": bool(defect.get("has_image", defect.get("image_path"))),
        "has_sem_image": bool(sem["path"] or defect.get("has_sem_image")),
        "sem": sem,
    }


class NanoPointImageTemplatesDialog(QDialog):
    def __init__(
        self,
        state=None,
        care_area_names=None,
        *,
        defect_data=None,
        wafer_loaded=False,
        wafer_aligned=False,
        light_trained=False,
        premap_defined=False,
        test_name="Test 1",
        parent=None,
    ):
        super().__init__(parent)
        self.state = normalize_nanopoint_state(state)
        self.care_area_names = list(care_area_names or [])
        self.defect_data = deepcopy(defect_data or {})
        self.wafer_loaded = bool(wafer_loaded)
        self.wafer_aligned = bool(wafer_aligned)
        self.light_trained = bool(light_trained)
        self.premap_defined = bool(premap_defined)
        self.test_name = str(test_name or "Test 1")
        if self.defect_data and not self.state.get("defect_source"):
            self.state["defect_source"] = str(
                self.defect_data.get("path") or self.defect_data.get("name") or "Attached Lot Result"
            )
        self.result_state = None
        self._loading = False
        self.blink_timer = QTimer(self)
        self.blink_timer.setInterval(600)
        self.blink_timer.timeout.connect(self._blink_step)
        self.setWindowTitle("NP Image Templates")
        self.resize(1500, 860)
        self.setMinimumSize(1120, 680)
        self.setStyleSheet(
            "QDialog { background: #cfcbc2; color: #111111; font-family: 'Segoe UI'; font-size: 9pt; }"
            "QWidget { color: #111111; }"
            "QPushButton { background: #e8e6dd; border: 1px solid #77736b; min-height: 24px; padding: 2px 7px; }"
            "QPushButton:hover { background: #f4f2eb; }"
            "QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit { background: #ffffff; color: #111111; border: 1px solid #8c8982; min-height: 22px; }"
            "QTableWidget { background: #f4f3ef; color: #111111; gridline-color: #aaa69d; }"
            "QHeaderView::section { background: #dad7cf; color: #111111; border: 1px solid #9a968d; padding: 3px; }"
            "QFrame#npPanel { border: 1px solid #8c8982; background: #ddd9d0; }"
        )
        root = QVBoxLayout(self)
        self.panes = QSplitter(Qt.Horizontal)
        templates = QWidget()
        templates.setLayout(self._templates_pane())
        image = QWidget()
        image.setLayout(self._image_pane())
        self.panes.addWidget(templates)
        self.panes.addWidget(image)
        self.panes.setSizes([720, 780])
        root.addWidget(self.panes, 1)
        root.addLayout(self._generic_controls())
        self._refresh()

    def _templates_pane(self):
        layout = QVBoxLayout()
        self.template_toolbar = QHBoxLayout()
        self.template_toolbar.setSpacing(4)
        self.template_toolbar.addWidget(QLabel(f"{self.test_name} - Templates"))
        self.template_buttons = {}
        for text, handler, icon_name in (
            ("Mark HotSpots", self._mark_hotspots, "Mark"),
            ("Import Marked", self._import_marked, "Import"),
            ("Delete", self._delete, "Delete"),
        ):
            button = QPushButton(text)
            button.setIcon(nanopoint_tool_icon(icon_name))
            button.setIconSize(QSize(22, 22))
            button.clicked.connect(handler)
            self.template_buttons[text] = button
            self.template_toolbar.addWidget(button)
        self.template_toolbar.addWidget(QLabel("Flip:"))
        for text, handler in (
            ("Flip H", lambda: self._flip("Horizontal")),
            ("Flip V", lambda: self._flip("Vertical")),
            ("Flip Both", lambda: self._flip("Both")),
        ):
            button = QPushButton("")
            button.setAccessibleName(text)
            button.setToolTip(text)
            button.setIcon(nanopoint_tool_icon(text))
            button.setIconSize(QSize(22, 22))
            button.setFixedWidth(34)
            button.clicked.connect(handler)
            self.template_buttons[text] = button
            self.template_toolbar.addWidget(button)
        self.template_toolbar.addStretch(1)
        layout.addLayout(self.template_toolbar)
        self.table = QTableWidget(0, 9)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        headers = (
            ("Name", "Name"),
            ("Conf.", "Confidence"),
            ("Unique", "Uniqueness"),
            ("Threshold", "Search Threshold"),
            ("Search", "Search"),
            ("Class", "Class Code"),
            ("Location", "Location"),
            ("Image", "Image"),
            ("Care Area", "Linked Care Area"),
        )
        for column, (label, tooltip) in enumerate(headers):
            item = QTableWidgetItem(label)
            item.setToolTip(tooltip)
            self.table.setHorizontalHeaderItem(column, item)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        for column, width in enumerate((108, 58, 60, 72, 54, 50, 92, 74, 92)):
            self.table.setColumnWidth(column, width)
        self.table.setIconSize(QSize(68, 30))
        self.table.itemChanged.connect(self._item_changed)
        self.table.currentCellChanged.connect(
            lambda _row, _column, _previous_row, _previous_column: self._selection_changed()
        )
        layout.addWidget(self.table)
        return layout

    def _image_pane(self):
        layout = QVBoxLayout()
        self.image_toolbar = QHBoxLayout()
        self.image_toolbar.setSpacing(4)
        self.image_toolbar.addWidget(QLabel("Template Image"))
        self.image_type = QComboBox()
        self.image_type.addItems(["Test", "Reference", "Difference", "Golden Image", "SEM"])
        self.image_type.setCurrentText(
            "Golden Image" if self.state["image_type"] == "Golden" else self.state["image_type"]
        )
        self.image_type.currentTextChanged.connect(self._image_changed)
        self.image_type.setVisible(False)
        zoom_out = QPushButton("-")
        zoom_out.setToolTip("Zoom Out")
        zoom_out.setFixedWidth(30)
        zoom_out.clicked.connect(lambda: self.zoom.setValue(self.zoom.value() - 25))
        self.image_toolbar.addWidget(zoom_out)
        self.zoom = QSlider(Qt.Horizontal)
        self.zoom.setRange(25, 300)
        self.zoom.setValue(int(self.state["zoom"]))
        self.zoom.valueChanged.connect(self._zoom_changed)
        self.image_toolbar.addWidget(self.zoom, 1)
        zoom_in = QPushButton("+")
        zoom_in.setToolTip("Zoom In")
        zoom_in.setFixedWidth(30)
        zoom_in.clicked.connect(lambda: self.zoom.setValue(self.zoom.value() + 25))
        self.image_toolbar.addWidget(zoom_in)
        fit = QPushButton("Fit")
        fit.clicked.connect(lambda: self.zoom.setValue(100))
        self.image_toolbar.addWidget(fit)
        self.magnifier_button = QPushButton("")
        self.magnifier_button.setAccessibleName("Magnifier")
        self.magnifier_button.setToolTip("Magnifier")
        self.magnifier_button.setIcon(self.style().standardIcon(QStyle.SP_FileDialogContentsView))
        self.magnifier_button.setCheckable(True)
        self.magnifier_button.setChecked(bool(self.state.get("magnifier")))
        self.magnifier_button.toggled.connect(
            lambda checked: self._set_option("magnifier", checked)
        )
        self.image_toolbar.addWidget(self.magnifier_button)
        self.magnifier_grid_button = QPushButton("")
        self.magnifier_grid_button.setAccessibleName("Magnifier Grid")
        self.magnifier_grid_button.setToolTip("Magnifier Grid")
        self.magnifier_grid_button.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        self.magnifier_grid_button.setCheckable(True)
        self.magnifier_grid_button.setChecked(bool(self.state.get("magnifier_grid")))
        self.magnifier_grid_button.toggled.connect(
            lambda checked: self._set_option("magnifier_grid", checked)
        )
        self.image_toolbar.addWidget(self.magnifier_grid_button)
        self.blink_button = QPushButton("Blink")
        self.blink_button.setCheckable(True)
        self.blink_button.toggled.connect(self._toggle_blink)
        blink_menu = QMenu(self.blink_button)
        blink_menu.addAction("Test / Reference / Difference", lambda: self.blink_button.setChecked(True))
        blink_menu.addAction("Stop Blink", lambda: self.blink_button.setChecked(False))
        self.blink_button.setMenu(blink_menu)
        self.image_toolbar.addWidget(self.blink_button)
        layout.addLayout(self.image_toolbar)

        self.image_headers = QHBoxLayout()
        self.image_headers.addWidget(QLabel("Defect Image"))
        self.image_mode_buttons = {}
        for mode in ("Test", "Reference", "Difference"):
            button = QPushButton(mode)
            button.setCheckable(True)
            button.clicked.connect(
                lambda checked=False, value=mode: self.image_type.setCurrentText(value)
            )
            self.image_mode_buttons[mode] = button
            self.image_headers.addWidget(button)
        self.image_headers.addStretch(1)
        self.image_headers.addWidget(QLabel("Golden Image"))
        layout.addLayout(self.image_headers)

        image_workspace = QHBoxLayout()
        vertical_tools = QVBoxLayout()
        self.box_target = QComboBox()
        self.box_target.addItems(["Care Area", "Noise", "POI"])
        self.box_target.setVisible(False)
        self.edit_box_button = QPushButton("")
        self.edit_box_button.setAccessibleName("Edit Box")
        self.edit_box_button.setToolTip("Edit Box")
        self.edit_box_button.setIcon(nanopoint_tool_icon("Edit Box"))
        edit_menu = QMenu(self.edit_box_button)
        for target in ("Care Area", "Noise", "POI"):
            edit_menu.addAction(
                target,
                lambda checked=False, value=target: self._edit_selected_box(value),
            )
        self.edit_box_button.setMenu(edit_menu)
        vertical_tools.addWidget(self.edit_box_button)
        self.draw_ca_button = QPushButton("")
        self.draw_ca_button.setAccessibleName("Draw CA")
        self.draw_ca_button.setToolTip("Draw Care Area")
        self.draw_ca_button.setIcon(nanopoint_tool_icon("Edit Box"))
        self.draw_ca_button.clicked.connect(self._draw_ca)
        vertical_tools.addWidget(self.draw_ca_button)
        self.reset_boxes_button = QPushButton("")
        self.reset_boxes_button.setAccessibleName("Reset Boxes")
        self.reset_boxes_button.setToolTip("Reset Boxes")
        self.reset_boxes_button.setIcon(nanopoint_tool_icon("Reset Boxes"))
        self.reset_boxes_button.clicked.connect(self._reset_boxes)
        vertical_tools.addWidget(self.reset_boxes_button)
        vertical_tools.addStretch(1)
        image_workspace.addLayout(vertical_tools)
        self.image_splitter = QSplitter(Qt.Horizontal)
        self.preview = NanoPointPreview(self.state, self._box_changed)
        self.golden_preview = NanoPointPreview(self.state, forced_image_type="Golden")
        self.image_splitter.addWidget(self.preview)
        self.image_splitter.addWidget(self.golden_preview)
        self.image_splitter.setSizes([320, 320])
        image_workspace.addWidget(self.image_splitter, 1)
        layout.addLayout(image_workspace, 1)

        bottom_panels = QHBoxLayout()
        bottom_panels.setSpacing(4)
        self.template_parameters_panel = QFrame()
        self.template_parameters_panel.setObjectName("npPanel")
        parameters = QVBoxLayout(self.template_parameters_panel)
        parameters.setContentsMargins(6, 4, 6, 4)
        parameters.addWidget(QLabel("Template Parameters"))
        self.show_ca = QCheckBox("Care Area")
        self.show_noise = QCheckBox("Noise")
        self.show_poi = QCheckBox("POI")
        self.false_colors = QCheckBox("False Colors")
        self.auto_scale = QCheckBox("Auto Scale")
        self.show_sem_box = QCheckBox("SEM Bounding Box")
        for check, key in (
            (self.show_ca, "show_ca"),
            (self.show_noise, "show_noise"),
            (self.show_poi, "show_poi"),
            (self.false_colors, "false_colors"),
            (self.auto_scale, "auto_scale"),
            (self.show_sem_box, "show_sem_bounding_box"),
        ):
            check.setChecked(bool(self.state[key]))
            check.toggled.connect(lambda value, field=key: self._set_option(field, value))
        for check in (self.show_ca, self.show_noise, self.show_poi, self.show_sem_box):
            parameters.addWidget(check)
        sizes = QGridLayout()
        sizes.addWidget(QLabel("MCA"), 0, 0)
        self.mca_size = QSpinBox()
        self.mca_size.setMinimumWidth(68)
        self.mca_size.setRange(5, 21)
        self.mca_size.setValue(int(self.state.get("mca_size", 5)))
        self.mca_size.valueChanged.connect(lambda value: self._set_numeric("mca_size", value))
        sizes.addWidget(self.mca_size, 0, 1)
        sizes.addWidget(QLabel("Noise"), 1, 0)
        self.noise_box_size = QSpinBox()
        self.noise_box_size.setMinimumWidth(68)
        self.noise_box_size.setRange(48, 80)
        self.noise_box_size.setValue(int(self.state.get("noise_box_size", 64)))
        self.noise_box_size.valueChanged.connect(
            lambda value: self._set_numeric("noise_box_size", value)
        )
        sizes.addWidget(self.noise_box_size, 1, 1)
        parameters.addLayout(sizes)
        bottom_panels.addWidget(self.template_parameters_panel, 3)

        self.scores_panel = QFrame()
        self.scores_panel.setObjectName("npPanel")
        scores = QGridLayout(self.scores_panel)
        scores.setContentsMargins(6, 4, 6, 4)
        scores.addWidget(QLabel("Scores"), 0, 0, 1, 2)
        scores.addWidget(QLabel("Confidence"), 1, 0)
        self.confidence_value = QLabel("-")
        scores.addWidget(self.confidence_value, 1, 1)
        scores.addWidget(QLabel("Uniqueness"), 2, 0)
        self.uniqueness_value = QLabel("-")
        scores.addWidget(self.uniqueness_value, 2, 1)
        search_threshold_label = QLabel("Search Thr.")
        search_threshold_label.setToolTip("Search Threshold")
        scores.addWidget(search_threshold_label, 3, 0)
        self.search_threshold = QDoubleSpinBox()
        self.search_threshold.setRange(0.5, 1.0)
        self.search_threshold.setDecimals(2)
        self.search_threshold.setSingleStep(0.01)
        self.search_threshold.setMinimumWidth(72)
        self.search_threshold.valueChanged.connect(self._search_threshold_changed)
        scores.addWidget(self.search_threshold, 3, 1)
        bottom_panels.addWidget(self.scores_panel, 2)

        self.colors_panel = QFrame()
        self.colors_panel.setObjectName("npPanel")
        colors = QGridLayout(self.colors_panel)
        colors.setContentsMargins(6, 4, 6, 4)
        colors.addWidget(QLabel("Colorscale"), 0, 0, 1, 2)
        colors.addWidget(self.false_colors, 1, 0, 1, 2)
        colors.addWidget(self.auto_scale, 2, 0, 1, 2)
        self.color_scale = QSlider(Qt.Horizontal)
        self.color_scale.setRange(0, 4095)
        self.color_scale.setValue(int(self.state.get("color_scale_max", 4000)))
        self.color_scale.valueChanged.connect(
            lambda value: self._set_numeric("color_scale_max", value)
        )
        colors.addWidget(self.color_scale, 3, 0, 1, 2)
        self.color_min = QSpinBox()
        self.color_min.setMinimumWidth(64)
        self.color_min.setRange(0, 4095)
        self.color_min.setValue(int(self.state.get("color_scale_min", 0)))
        self.color_min.valueChanged.connect(
            lambda value: self._set_numeric("color_scale_min", value)
        )
        self.color_max = QSpinBox()
        self.color_max.setMinimumWidth(64)
        self.color_max.setRange(0, 4095)
        self.color_max.setValue(int(self.state.get("color_scale_max", 4000)))
        self.color_max.valueChanged.connect(
            lambda value: self._set_numeric("color_scale_max", value)
        )
        colors.addWidget(self.color_min, 4, 0)
        colors.addWidget(self.color_max, 4, 1)
        bottom_panels.addWidget(self.colors_panel, 2)

        self.sem_panel = QFrame()
        self.sem_panel.setObjectName("npPanel")
        sem_controls = QVBoxLayout(self.sem_panel)
        sem_controls.setContentsMargins(6, 4, 6, 4)
        sem_controls.addWidget(QLabel("SEM Image"))
        self.browse_sem_button = QPushButton("Browse SEM Image...")
        self.browse_sem_button.clicked.connect(self._browse_sem)
        sem_controls.addWidget(self.browse_sem_button)
        self.show_sem_button = QPushButton("Show SEM Image")
        self.show_sem_button.clicked.connect(self._show_sem)
        sem_controls.addWidget(self.show_sem_button)
        sem_more = QPushButton("SEM Tools...")
        sem_menu = QMenu(sem_more)
        sem_menu.addAction("FOV Settings", self._sem_fov)
        sem_menu.addAction("Rotate 90", self._rotate_sem)
        sem_menu.addAction("Draw Care Area on SEM", self._draw_sem_care_area)
        sem_more.setMenu(sem_menu)
        sem_controls.addWidget(sem_more)
        bottom_panels.addWidget(self.sem_panel, 2)
        layout.addLayout(bottom_panels)

        self.sem_detail_widget = QWidget()
        sem_detail = QHBoxLayout(self.sem_detail_widget)
        sem_detail.setContentsMargins(0, 0, 0, 0)
        sem_detail.addWidget(QLabel("Correlation Result"))
        self.sem_match = QComboBox()
        self.sem_match.currentIndexChanged.connect(self._sem_match_changed)
        sem_detail.addWidget(self.sem_match, 1)
        use_match = QPushButton("Use Selected Care Area")
        use_match.clicked.connect(self._use_sem_care_area)
        sem_detail.addWidget(use_match)
        sem_detail.addWidget(QLabel("SEM Opacity"))
        self.sem_opacity = QSlider(Qt.Horizontal)
        self.sem_opacity.setRange(0, 100)
        self.sem_opacity.setValue(int(self.state.get("sem_opacity", 60)))
        self.sem_opacity.valueChanged.connect(
            lambda value: self._set_numeric("sem_opacity", value)
        )
        sem_detail.addWidget(self.sem_opacity)
        self.sem_detail_widget.setVisible(False)
        layout.addWidget(self.sem_detail_widget)
        self.details = QLabel("Select a template to inspect its image parameters.")
        self.details.setWordWrap(True)
        self.details.setMinimumHeight(32)
        layout.addWidget(self.details)
        self._image_changed(self.image_type.currentText())
        return layout

    def _generic_controls(self):
        layout = QVBoxLayout()
        self.generic_toolbar = QHBoxLayout()
        self.generic_toolbar.setSpacing(6)
        self.select_source_button = QPushButton("")
        self.select_source_button.setAccessibleName("Select Defect Data")
        self.select_source_button.setToolTip("Select Defect Data")
        self.select_source_button.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        self.select_source_button.setMenu(QMenu(self.select_source_button))
        self.select_source_button.menu().addAction("Select Defect Data...", self._select_source)
        self.generic_toolbar.addWidget(self.select_source_button)
        self.review_button = QPushButton("Review")
        self.review_button.setIcon(nanopoint_tool_icon("Mark"))
        self.review_button.clicked.connect(self._review)
        self.generic_toolbar.addWidget(self.review_button)
        self.reference_die_button = QPushButton("")
        self.reference_die_button.setAccessibleName("Reference Die")
        self.reference_die_button.setToolTip("Reference Die")
        self.reference_die_button.setIcon(self.style().standardIcon(QStyle.SP_DialogResetButton))
        self.reference_die_button.clicked.connect(self._reference_die)
        self.generic_toolbar.addWidget(self.reference_die_button)
        self.source = QLabel()
        self.grab_button = QPushButton("Grab Images")
        self.grab_button.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        self.grab_button.clicked.connect(self._grab_images)
        grab_menu = QMenu(self.grab_button)
        grab_menu.addAction("Grab Missing Images", lambda: self._grab_images(False))
        grab_menu.addAction("Re-Grab all Images", lambda: self._grab_images(True))
        self.grab_button.setMenu(grab_menu)
        self.generic_toolbar.addWidget(self.grab_button)
        self.search_poi_button = QPushButton("Search POI")
        self.search_poi_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.search_poi_button.clicked.connect(self._search_poi)
        self.generic_toolbar.addWidget(self.search_poi_button)
        self.generic_toolbar.addStretch(1)
        self.finish_button = QPushButton("Finish")
        self.finish_button.setIcon(self.style().standardIcon(QStyle.SP_DialogApplyButton))
        self.finish_button.clicked.connect(self._finish)
        self.generic_toolbar.addWidget(self.finish_button)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setIcon(self.style().standardIcon(QStyle.SP_DialogCancelButton))
        self.cancel_button.clicked.connect(self.reject)
        self.generic_toolbar.addWidget(self.cancel_button)
        self.information_button = QPushButton("")
        self.information_button.setAccessibleName("Information")
        self.information_button.setToolTip("Information")
        self.information_button.setIcon(self.style().standardIcon(QStyle.SP_MessageBoxInformation))
        self.information_button.clicked.connect(self._information)
        self.generic_toolbar.addWidget(self.information_button)
        layout.addLayout(self.generic_toolbar)
        layout.addWidget(self.source)
        return layout

    def _mark_hotspots(self):
        defects = self.defect_data.get("defects") or []
        if not defects:
            QMessageBox.warning(
                self,
                "Mark HotSpots",
                "Select defect data containing defects before marking hotspots.",
            )
            return
        dialog = SetupReviewDefectsDialog(
            defects,
            self.state.get("marked_defects"),
            self,
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.state["marked_defects"] = deepcopy(dialog.result_defects)

    def _import_marked(self):
        marked = [
            defect
            for defect in self.state.get("marked_defects", [])
            if defect.get("marked")
        ]
        if not marked:
            QMessageBox.warning(
                self,
                "Import Marked",
                "Mark one or more defects in Review before importing templates.",
            )
            return
        existing_ids = {
            int(template.get("source_defect_id", -1))
            for template in self.state["templates"]
        }
        additions = [
            defect for defect in marked
            if int(defect.get("id", -1)) not in existing_ids
        ]
        if not additions:
            QMessageBox.information(
                self,
                "Import Marked",
                "All marked defects are already present in the template list.",
            )
            return
        available = MAX_NANOPOINT_TARGETS - len(self.state["templates"])
        if available <= 0:
            QMessageBox.warning(
                self,
                "Import Marked",
                "The maximum of 30 NanoPoint target types has been reached.",
            )
            return
        for defect in additions[:available]:
            self.state["templates"].append(
                imported_template(
                    len(self.state["templates"]) + 1,
                    self.care_area_names,
                    defect,
                )
            )
        if len(additions) > available:
            QMessageBox.information(
                self,
                "Import Marked",
                f"Imported {available} targets; the 30-target limit was reached.",
            )
        self.state["images_grabbed"] = False
        self.state["poi_search_complete"] = False
        self._refresh()
        if self.state["templates"]:
            self.table.selectRow(len(self.state["templates"]) - 1)

    def _delete(self):
        row = self.table.currentRow()
        if 0 <= row < len(self.state["templates"]):
            self.state["templates"].pop(row)
            if not self.state["templates"]:
                self.state["images_grabbed"] = False
            self.state["poi_search_complete"] = False
            self._refresh()

    def _flip(self, direction):
        row = self.table.currentRow()
        if not 0 <= row < len(self.state["templates"]):
            return
        flips = self.state["templates"][row].setdefault("flips", [])
        if direction not in flips:
            flips.append(direction)
            self.state["poi_search_complete"] = False
        self.details.setText(
            f"Template variants: Original, {', '.join(flips)}"
        )

    def _select_source(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Defect Data",
            "",
            "Lot Results (*.json *.klarf *.001);;All Files (*.*)",
        )
        if path:
            self.state["defect_source"] = path
            self.source.setText(f"Defect Source: {Path(path).name}")

    def _review(self):
        self._mark_hotspots()

    def _reference_die(self):
        dialog = ReferenceDieDialog(self.state["reference_die"], self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.state["reference_die"] = [dialog.column.value(), dialog.row.value()]
            self.state["images_grabbed"] = False
            self.state["poi_search_complete"] = False
            self._selection_changed()

    def _grab_images(self, regrab_all=False):
        if not (
            self.wafer_loaded
            and self.wafer_aligned
            and self.light_trained
            and self.premap_defined
        ):
            QMessageBox.warning(
                self,
                "Grab Images",
                "Load and align the wafer, define Premap, and complete Light Level Training before grabbing images.",
            )
            return
        if not self.state["templates"]:
            QMessageBox.warning(self, "Grab Images", "Import at least one marked hotspot first.")
            return
        if not self.state["defect_source"]:
            QMessageBox.warning(self, "Grab Images", "Select defect data first.")
            return
        for index, template in enumerate(self.state["templates"]):
            if not regrab_all and template.get("has_patch_images") and template.get("confidence", 0):
                continue
            template["confidence"] = round(0.94 - index * 0.007, 3)
            template["uniqueness"] = round(0.91 - index * 0.006, 3)
            template["has_patch_images"] = True
            if template.get("has_sem_image"):
                template.setdefault("sem", default_sem_state())
        self.state["images_grabbed"] = True
        self.state["valid"] = True
        self.state["poi_search_complete"] = False
        self._refresh()
        QMessageBox.information(
            self,
            "Grab Images",
            (
                "All Test, Reference, Difference, and available SEM images were re-acquired."
                if regrab_all
                else "Missing Test, Reference, Difference, and available SEM images were stored with the templates."
            ),
        )

    def _selected_box_key(self):
        return {
            "Care Area": "care_area",
            "Noise": "noise_box",
            "POI": "poi_box",
        }[self.box_target.currentText()]

    def _edit_box(self):
        template = self._selected_template()
        if template is None:
            return
        key = self._selected_box_key()
        self.preview.editing_box = key
        self.details.setText(f"Drag in Template Image to redefine {self.box_target.currentText()}.")

    def _edit_selected_box(self, target):
        self.box_target.setCurrentText(target)
        self._edit_box()

    def _draw_ca(self):
        self.box_target.setCurrentText("Care Area")
        self._edit_box()

    def _reset_boxes(self):
        template = self._selected_template()
        if template is None:
            return
        template["care_area"] = [0.30, 0.34, 0.40, 0.24]
        template["noise_box"] = [0.15, 0.15, 0.70, 0.62]
        template["poi_box"] = [0.47, 0.45, 0.06, 0.08]
        self.state["poi_search_complete"] = False
        self.preview.editing_box = None
        self.preview.update()
        self._selection_changed()

    def _box_changed(self, key, region):
        template = self._selected_template()
        if template is None:
            return
        template[key] = list(region)
        self.state["poi_search_complete"] = False
        self.preview.editing_box = None
        self._selection_changed()

    def _toggle_blink(self, enabled):
        if enabled:
            self.blink_timer.start()
            self._blink_step()
        else:
            self.blink_timer.stop()

    def _blink_step(self):
        sequence = ["Test", "Reference", "Difference"]
        current = self.image_type.currentText()
        self.image_type.setCurrentText(sequence[(sequence.index(current) + 1) % 3] if current in sequence else "Test")

    def _selected_template(self, *, require_sem=False):
        row = self.table.currentRow()
        if not 0 <= row < len(self.state["templates"]):
            QMessageBox.information(self, "NanoPoint Image Templates", "Select a template first.")
            return None
        template = self.state["templates"][row]
        if require_sem and not template.get("has_sem_image"):
            QMessageBox.information(self, "SEM Image", "The selected template has no SEM image.")
            return None
        return template

    def _browse_sem(self):
        template = self._selected_template()
        if template is None:
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Browse SEM Image",
            "",
            "SEM Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff);;All Files (*.*)",
        )
        if path:
            sem = default_sem_state()
            sem.update(template.get("sem") or {})
            sem["path"] = path
            template["sem"] = sem
            template["has_sem_image"] = True
            self._selection_changed()

    def _show_sem(self):
        template = self._selected_template(require_sem=True)
        if template is None:
            return
        sem = template.setdefault("sem", default_sem_state())
        visible = not bool(sem.get("visible"))
        sem["visible"] = visible
        self.image_type.setCurrentText("SEM" if visible else "Test")
        self.show_sem_button.setText("Hide SEM Image" if visible else "Show SEM Image")
        self.sem_detail_widget.setVisible(visible)
        self.preview.update()

    def _sem_fov(self):
        template = self._selected_template(require_sem=True)
        if template is None:
            return
        dialog = SemFovDialog(template.setdefault("sem", default_sem_state()).get("fov_um", 25.0), self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            template["sem"]["fov_um"] = dialog.fov.value()
            self._selection_changed()

    def _rotate_sem(self):
        template = self._selected_template(require_sem=True)
        if template is None:
            return
        sem = template.setdefault("sem", default_sem_state())
        sem["rotation"] = (int(sem.get("rotation", 0)) + 90) % 360
        self._selection_changed()

    def _draw_sem_care_area(self):
        template = self._selected_template(require_sem=True)
        if template is None:
            return
        proposed = (template.get("sem") or {}).get("care_area") or [0.35, 0.35, 0.30, 0.30]
        sem = template.setdefault("sem", default_sem_state())
        sem["visible"] = True
        self.image_type.setCurrentText("SEM")
        sem["matches"] = sem_correlation_candidates(proposed)
        sem["selected_match"] = 0
        sem["correlated"] = False
        self._selection_changed()

    def _sem_match_changed(self, index):
        template = self._selected_template()
        if template is not None and index >= 0:
            template.setdefault("sem", default_sem_state())["selected_match"] = int(index)
            self.preview.update()

    def _use_sem_care_area(self):
        template = self._selected_template(require_sem=True)
        if template is None:
            return
        sem = template.setdefault("sem", default_sem_state())
        matches = sem.get("matches") or []
        selected = self.sem_match.currentIndex()
        if not matches or selected < 0:
            QMessageBox.warning(self, "SEM Correlation", "Draw a Care Area and select a correlation result first.")
            return
        template.update(accept_sem_correlation_match(template, selected))
        self._selection_changed()

    def _search_poi(self):
        searchable = [item for item in self.state["templates"] if item.get("search", True)]
        if not searchable or not self.state.get("images_grabbed"):
            QMessageBox.warning(self, "Search POI", "Grab images for at least one searchable template first.")
            return
        for index, template in enumerate(searchable, start=1):
            template["poi_matches"] = [[index, index], [index + 2, index - 1]]
        self.state["poi_search_complete"] = True
        QMessageBox.information(self, "Search POI", "POI locations were attached to the recipe.")

    def _information(self):
        searched = sum(
            len(template.get("poi_matches") or [])
            for template in self.state["templates"]
        )
        QMessageBox.information(
            self,
            "NanoPoint Image Templates",
            f"Templates: {len(self.state['templates'])} / {MAX_NANOPOINT_TARGETS}\n"
            f"Reference Die: {self.state['reference_die']}\n"
            f"MCA Size: {self.state['mca_size']} x {self.state['mca_size']}\n"
            f"Noise Box: {self.state['noise_box_size']} x {self.state['noise_box_size']}\n"
            f"POI Matches: {searched}",
        )

    def _set_option(self, key, value):
        self.state[key] = bool(value)
        self.preview.update()
        self.golden_preview.update()

    def _set_numeric(self, key, value):
        self.state[key] = int(value)
        self.preview.update()
        self.golden_preview.update()
        if key == "color_scale_max":
            for control in (self.color_scale, self.color_max):
                if control.value() != int(value):
                    control.blockSignals(True)
                    control.setValue(int(value))
                    control.blockSignals(False)

    def _search_threshold_changed(self, value):
        row = self.table.currentRow()
        if self._loading or not 0 <= row < len(self.state["templates"]):
            return
        self.state["templates"][row]["search_threshold"] = float(value)
        item = self.table.item(row, 3)
        if item is not None:
            self._loading = True
            item.setText(f"{float(value):.3f}")
            self._loading = False
        self.state["poi_search_complete"] = False

    def _image_changed(self, value):
        row = self.table.currentRow()
        template = (
            self.state["templates"][row]
            if 0 <= row < len(self.state["templates"])
            else None
        )
        if value == "SEM":
            if template is None or not template.get("has_sem_image"):
                self.image_type.blockSignals(True)
                self.image_type.setCurrentText("Test")
                self.image_type.blockSignals(False)
                value = "Test"
        for item in self.state["templates"]:
            item.setdefault("sem", default_sem_state())["visible"] = False
        if value == "SEM" and template is not None:
            template.setdefault("sem", default_sem_state())["visible"] = True
        self.state["image_type"] = "Golden" if value == "Golden Image" else value
        for mode, button in getattr(self, "image_mode_buttons", {}).items():
            button.blockSignals(True)
            button.setChecked(value == mode)
            button.blockSignals(False)
        sem_visible = value == "SEM"
        if hasattr(self, "sem_detail_widget"):
            self.sem_detail_widget.setVisible(sem_visible)
        if hasattr(self, "show_sem_button"):
            self.show_sem_button.setText("Hide SEM Image" if sem_visible else "Show SEM Image")
        self.preview.update()
        self.golden_preview.update()

    def _zoom_changed(self, value):
        self.state["zoom"] = int(value)
        self.preview.update()
        self.golden_preview.update()

    def _selection_changed(self):
        row = self.table.currentRow()
        self.preview.selected = row
        self.golden_preview.selected = row
        self.preview.update()
        self.golden_preview.update()
        if not 0 <= row < len(self.state["templates"]):
            self.confidence_value.setText("-")
            self.uniqueness_value.setText("-")
            return
        template = self.state["templates"][row]
        if self.image_type.currentText() == "SEM" and not template.get("has_sem_image"):
            self.image_type.setCurrentText("Test")
        sem = template.setdefault("sem", default_sem_state())
        self.sem_match.blockSignals(True)
        self.sem_match.clear()
        for match in sem.get("matches", []):
            self.sem_match.addItem(f"{match.get('name')} ({float(match.get('score', 0)):.2f})")
        selected = int(sem.get("selected_match", -1))
        if 0 <= selected < self.sem_match.count():
            self.sem_match.setCurrentIndex(selected)
        self.sem_match.blockSignals(False)
        self.confidence_value.setText(f"{float(template.get('confidence', 0)):.2f}")
        self.uniqueness_value.setText(f"{float(template.get('uniqueness', 0)):.2f}")
        self.search_threshold.blockSignals(True)
        self.search_threshold.setValue(float(template.get("search_threshold", 0.75)))
        self.search_threshold.blockSignals(False)
        mca = int(self.state.get("mca_size", 5))
        noise = int(self.state.get("noise_box_size", 64))
        care_area = template.get("care_area", [0.30, 0.34, 0.40, 0.24])
        noise_box = template.get("noise_box", [0.15, 0.15, 0.70, 0.62])
        poi_box = template.get("poi_box", [0.47, 0.45, 0.06, 0.08])
        self.show_ca.setText(
            f"Care Area  {mca} x {mca} pixels @ {care_area[0]:.2f}, {care_area[1]:.2f}"
        )
        self.show_noise.setText(
            f"Noise  {noise} x {noise} pixels @ {noise_box[0]:.2f}, {noise_box[1]:.2f}"
        )
        self.show_poi.setText(
            f"POI  {max(1, int(poi_box[2] * 100))} x {max(1, int(poi_box[3] * 100))} pixels"
        )
        sem_visible = self.image_type.currentText() == "SEM"
        self.sem_detail_widget.setVisible(sem_visible)
        self.show_sem_button.setText("Hide SEM Image" if sem_visible else "Show SEM Image")
        self.details.setText(
            f"Reference Die: {self.state['reference_die']}    "
            f"Location: {template.get('location')}    "
            f"Variants: {', '.join(template.get('flips', [])) or 'Original'}    "
            f"SEM FOV: {float(sem.get('fov_um', 25.0)):g} um    "
            f"Rotation: {int(sem.get('rotation', 0))} deg    "
            f"Correlation: {'Accepted' if sem.get('correlated') else 'Not accepted'}"
        )

    def _item_changed(self, item):
        if self._loading or item.row() >= len(self.state["templates"]):
            return
        template = self.state["templates"][item.row()]
        try:
            if item.column() == 0:
                template["name"] = item.text().strip()
            elif item.column() == 3:
                template["search_threshold"] = float(item.text())
            elif item.column() == 4:
                template["search"] = item.checkState() == Qt.Checked
            elif item.column() == 5:
                template["class_code"] = int(item.text())
            elif item.column() == 8:
                template["linked_care_area"] = item.text().strip()
        except ValueError:
            QMessageBox.warning(self, "Template Settings", "Enter a valid numeric value.")
            self._refresh()
            return
        self.state["poi_search_complete"] = False

    def _refresh(self):
        self._loading = True
        self.table.setRowCount(len(self.state["templates"]))
        for row, template in enumerate(self.state["templates"]):
            values = [
                template.get("name", ""),
                f"{float(template.get('confidence', 0)):.3f}",
                f"{float(template.get('uniqueness', 0)):.3f}",
                f"{float(template.get('search_threshold', 0.75)):.3f}",
                "",
                str(template.get("class_code", 0)),
                ", ".join(str(value) for value in template.get("location", [])),
                "",
                template.get("linked_care_area", ""),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in (1, 2, 6, 7):
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if column == 7:
                    item.setIcon(nanopoint_thumbnail_icon(template.get("has_sem_image")))
                if column == 4:
                    item.setCheckState(Qt.Checked if template.get("search", True) else Qt.Unchecked)
                self.table.setItem(row, column, item)
            self.table.setRowHeight(row, 42)
        self._loading = False
        source = self.state.get("defect_source")
        self.source.setText(
            f"Defect Source: {Path(source).name}" if source else "Defect Source: Not selected"
        )
        self.preview.state = self.state
        self.golden_preview.state = self.state
        self.preview.update()
        self.golden_preview.update()
        if self.state["templates"] and self.table.currentRow() < 0:
            self.table.selectRow(0)

    def _finish(self):
        errors = validate_nanopoint_state(self.state)
        if errors:
            QMessageBox.warning(self, "NanoPoint Image Templates", "\n".join(errors))
            return
        self.result_state = deepcopy(self.state)
        self.accept()

    def done(self, result):
        self.blink_timer.stop()
        if hasattr(self, "blink_button"):
            self.blink_button.blockSignals(True)
            self.blink_button.setChecked(False)
            self.blink_button.blockSignals(False)
        super().done(result)


class ReferenceDieDialog(QDialog):
    def __init__(self, die, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Reference Die")
        self.setFixedSize(360, 190)
        layout = QGridLayout(self)
        self.column = QSpinBox()
        self.column.setRange(-999, 999)
        self.column.setValue(int(die[0]))
        self.row = QSpinBox()
        self.row.setRange(-999, 999)
        self.row.setValue(int(die[1]))
        layout.addWidget(QLabel("Column:"), 0, 0)
        layout.addWidget(self.column, 0, 1)
        layout.addWidget(QLabel("Row:"), 1, 0)
        layout.addWidget(self.row, 1, 1)
        ok = QPushButton("OK")
        ok.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        layout.addWidget(ok, 2, 0)
        layout.addWidget(cancel, 2, 1)


class SemFovDialog(QDialog):
    def __init__(self, value, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SEM FOV Settings")
        self.setFixedSize(330, 150)
        layout = QGridLayout(self)
        layout.addWidget(QLabel("Field of View (um)"), 0, 0)
        self.fov = QDoubleSpinBox()
        self.fov.setRange(0.1, 10000.0)
        self.fov.setDecimals(2)
        self.fov.setValue(float(value))
        layout.addWidget(self.fov, 0, 1)
        ok = QPushButton("OK")
        ok.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        layout.addWidget(ok, 1, 0)
        layout.addWidget(cancel, 1, 1)


class NanoPointPreview(QWidget):
    def __init__(self, state, on_box_changed=None, parent=None, *, forced_image_type=None):
        super().__init__(parent)
        self.state = state
        self.on_box_changed = on_box_changed
        self.forced_image_type = forced_image_type
        self.selected = -1
        self.editing_box = None
        self.drag_start = None
        self.drag_current = None
        self.setMinimumSize(360, 210)

    def mousePressEvent(self, event):
        if self.editing_box is None:
            return
        pos = event.position() if hasattr(event, "position") else event.pos()
        self.drag_start = (pos.x(), pos.y())
        self.drag_current = self.drag_start

    def mouseMoveEvent(self, event):
        if self.drag_start is None:
            return
        pos = event.position() if hasattr(event, "position") else event.pos()
        self.drag_current = (pos.x(), pos.y())
        self.update()

    def mouseReleaseEvent(self, event):
        if self.drag_start is None:
            return
        pos = event.position() if hasattr(event, "position") else event.pos()
        x1, y1 = self.drag_start
        x2, y2 = pos.x(), pos.y()
        self.drag_start = None
        self.drag_current = None
        if abs(x2 - x1) < 5 or abs(y2 - y1) < 5:
            return
        nx1, ny1 = self._view_to_normalized(x1, y1)
        nx2, ny2 = self._view_to_normalized(x2, y2)
        region = [
            min(nx1, nx2),
            min(ny1, ny2),
            abs(nx2 - nx1),
            abs(ny2 - ny1),
        ]
        if self.on_box_changed:
            self.on_box_changed(self.editing_box, region)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        image_type = self.forced_image_type or self.state.get("image_type", "Test")
        painter.fillRect(self.rect(), QColor("#090b0c"))
        zoom = max(0.25, float(self.state.get("zoom", 100)) / 100)
        left, top, view_width, view_height = self._view_rect()
        if image_type == "SEM":
            painter.fillRect(
                int(left), int(top), int(view_width), int(view_height), QColor("#55585b")
            )
            spacing = max(3, int(30 * zoom))
            painter.setPen(QPen(QColor("#8e9495"), 1))
            x = left
            while x <= left + view_width:
                painter.drawLine(int(x), int(top), int(x), int(top + view_height))
                x += spacing
            y = top
            while y <= top + view_height:
                painter.drawLine(int(left), int(y), int(left + view_width), int(y))
                y += spacing
        else:
            band = max(6, int(view_height / 5))
            tile = max(6, int(10 * zoom))
            for band_top in (top, top + view_height - band):
                y = band_top
                while y < band_top + band:
                    x = left
                    while x < left + view_width:
                        parity = (int((x - left) / tile) + int((y - band_top) / tile)) % 2
                        painter.fillRect(
                            int(x),
                            int(y),
                            tile,
                            tile,
                            QColor("#f2f2f0" if parity else "#c7c7c3"),
                        )
                        x += tile
                    y += tile
            center_x = left + view_width / 2
            center_y = top + view_height / 2
            painter.setPen(QPen(QColor("#f5f5f3"), 2))
            painter.drawLine(
                int(left + view_width / 12),
                int(center_y),
                int(left + view_width * 11 / 12),
                int(center_y),
            )
            painter.drawRect(
                int(left + view_width / 3),
                int(center_y - 8 * zoom),
                int(view_width / 3),
                max(1, int(16 * zoom)),
            )
            painter.drawLine(
                int(center_x),
                int(center_y - 16 * zoom),
                int(center_x),
                int(center_y + 16 * zoom),
            )
            painter.setPen(QPen(QColor("#626665"), 1))
            for offset in (-24, -12, 12, 24):
                painter.drawLine(
                    int(center_x + offset * zoom),
                    int(center_y - 12 * zoom),
                    int(center_x + offset * zoom),
                    int(center_y + 12 * zoom),
                )
        template = (
            self.state.get("templates", [])[self.selected]
            if 0 <= self.selected < len(self.state.get("templates", []))
            else {}
        )
        boxes = {
            "noise_box": template.get("noise_box", [0.15, 0.15, 0.70, 0.62]),
            "care_area": template.get("care_area", [0.30, 0.34, 0.40, 0.24]),
            "poi_box": template.get("poi_box", [0.47, 0.45, 0.06, 0.08]),
        }
        if self.state.get("show_noise"):
            painter.setBrush(QColor(110, 105, 35, 70))
            painter.setPen(QPen(QColor("#b7aa35"), 1))
            self._draw_normalized_box(painter, boxes["noise_box"])
        if self.state.get("show_ca"):
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor("#ffe000"), 3))
            self._draw_normalized_box(painter, boxes["care_area"])
        if self.state.get("show_poi"):
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor("#ff3030"), 2))
            self._draw_normalized_box(painter, boxes["poi_box"])
        if self.state.get("magnifier"):
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor("#ffffff"), 2))
            size = min(self.width(), self.height()) // 3
            painter.drawRect(self.width() // 2 - size // 2, self.height() // 2 - size // 2, size, size)
        if self.state.get("magnifier_grid"):
            painter.setPen(QPen(QColor("#ffffff"), 1))
            size = min(self.width(), self.height()) // 3
            left = self.width() // 2 - size // 2
            top = self.height() // 2 - size // 2
            for index in range(1, 4):
                painter.drawLine(left + index * size // 4, top, left + index * size // 4, top + size)
                painter.drawLine(left, top + index * size // 4, left + size, top + index * size // 4)
        if image_type == "SEM" and 0 <= self.selected < len(self.state.get("templates", [])):
            template = self.state["templates"][self.selected]
            sem = template.get("sem") or {}
            matches = sem.get("matches") or []
            for index, match in enumerate(matches):
                x, y, width, height = match.get("area", [0, 0, 0, 0])
                color = "#00ff66" if index == int(sem.get("selected_match", -1)) else "#ffcc00"
                painter.setPen(QPen(QColor(color), 2))
                painter.drawRect(*self._region_view_rect([x, y, width, height]))
            if self.state.get("show_sem_bounding_box"):
                bounding = QColor("#ff3030")
                bounding.setAlpha(max(20, int(255 * int(self.state.get("sem_opacity", 60)) / 100)))
                painter.setPen(QPen(bounding, 2))
                painter.drawRect(
                    int(left + 55 * zoom),
                    int(top + 55 * zoom),
                    max(1, int(view_width - 110 * zoom)),
                    max(1, int(view_height - 110 * zoom)),
                )
        if self.drag_start and self.drag_current:
            x1, y1 = self.drag_start
            x2, y2 = self.drag_current
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor("#ffffff"), 2, Qt.DashLine))
            painter.drawRect(
                int(min(x1, x2)),
                int(min(y1, y2)),
                int(abs(x2 - x1)),
                int(abs(y2 - y1)),
            )

    def _draw_normalized_box(self, painter, region):
        painter.drawRect(*self._region_view_rect(region))

    def _view_rect(self):
        zoom = max(0.25, float(self.state.get("zoom", 100)) / 100)
        width = max(1.0, float(self.width()) * zoom)
        height = max(1.0, float(self.height()) * zoom)
        return (
            (float(self.width()) - width) / 2,
            (float(self.height()) - height) / 2,
            width,
            height,
        )

    def _region_view_rect(self, region):
        x, y, width, height = [float(value) for value in region[:4]]
        left, top, view_width, view_height = self._view_rect()
        return (
            int(left + x * view_width),
            int(top + y * view_height),
            max(1, int(width * view_width)),
            max(1, int(height * view_height)),
        )

    def _view_to_normalized(self, x, y):
        left, top, view_width, view_height = self._view_rect()
        return (
            max(0.0, min(1.0, (float(x) - left) / view_width)),
            max(0.0, min(1.0, (float(y) - top) / view_height)),
        )

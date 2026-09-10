from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from ...qt_compat import (
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
    QTimer,
    Qt,
    QVBoxLayout,
    QWidget,
)

from .care_areas import SetupReviewDefectsDialog


MAX_NANOPOINT_TARGETS = 30


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
        self.setWindowTitle("NanoPoint Image Templates")
        self.resize(1280, 760)
        self.setMinimumSize(980, 620)
        self.setStyleSheet(
            "QDialog { background: #cfcbc2; color: #111111; font-family: 'Segoe UI'; font-size: 9pt; }"
            "QWidget { color: #111111; }"
            "QPushButton { background: #e8e6dd; border: 1px solid #77736b; min-height: 24px; padding: 2px 7px; }"
            "QPushButton:hover { background: #f4f2eb; }"
            "QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit { background: #ffffff; color: #111111; border: 1px solid #8c8982; min-height: 22px; }"
            "QTableWidget { background: #f4f3ef; color: #111111; gridline-color: #aaa69d; }"
            "QHeaderView::section { background: #dad7cf; color: #111111; border: 1px solid #9a968d; padding: 3px; }"
        )
        root = QVBoxLayout(self)
        self.panes = QSplitter(Qt.Horizontal)
        templates = QWidget()
        templates.setLayout(self._templates_pane())
        image = QWidget()
        image.setLayout(self._image_pane())
        self.panes.addWidget(templates)
        self.panes.addWidget(image)
        self.panes.setSizes([700, 540])
        root.addWidget(self.panes, 1)
        root.addLayout(self._generic_controls())
        self._refresh()

    def _templates_pane(self):
        layout = QVBoxLayout()
        toolbar = QGridLayout()
        toolbar.addWidget(QLabel(f"{self.test_name} - Templates"), 0, 0, 1, 3)
        for index, (text, handler) in enumerate((
            ("Mark HotSpots", self._mark_hotspots),
            ("Import Marked", self._import_marked),
            ("Delete", self._delete),
            ("Flip H", lambda: self._flip("Horizontal")),
            ("Flip V", lambda: self._flip("Vertical")),
            ("Flip Both", lambda: self._flip("Both")),
        )):
            button = QPushButton(text)
            button.clicked.connect(handler)
            toolbar.addWidget(button, 1 + index // 3, index % 3)
        layout.addLayout(toolbar)
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(
            [
                "Name",
                "Confidence",
                "Uniqueness",
                "Search Threshold",
                "Search",
                "Class Code",
                "Location",
                "Image",
                "Linked Care Area",
            ]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        for column, width in enumerate((130, 86, 86, 105, 62, 82, 105, 92, 130)):
            self.table.setColumnWidth(column, width)
        self.table.itemChanged.connect(self._item_changed)
        self.table.itemSelectionChanged.connect(self._selection_changed)
        layout.addWidget(self.table)
        return layout

    def _image_pane(self):
        layout = QVBoxLayout()
        toolbar = QGridLayout()
        toolbar.addWidget(QLabel("Template Image"), 0, 0)
        self.image_type = QComboBox()
        self.image_type.addItems(["Test", "Reference", "Difference", "Golden Image", "SEM"])
        self.image_type.setCurrentText(
            "Golden Image" if self.state["image_type"] == "Golden" else self.state["image_type"]
        )
        self.image_type.currentTextChanged.connect(self._image_changed)
        toolbar.addWidget(self.image_type, 0, 1)
        zoom_out = QPushButton("-")
        zoom_out.setToolTip("Zoom Out")
        zoom_out.clicked.connect(lambda: self.zoom.setValue(self.zoom.value() - 25))
        toolbar.addWidget(zoom_out, 0, 2)
        self.zoom = QSlider(Qt.Horizontal)
        self.zoom.setRange(25, 300)
        self.zoom.setValue(int(self.state["zoom"]))
        self.zoom.valueChanged.connect(self._zoom_changed)
        toolbar.addWidget(self.zoom, 0, 3, 1, 3)
        zoom_in = QPushButton("+")
        zoom_in.setToolTip("Zoom In")
        zoom_in.clicked.connect(lambda: self.zoom.setValue(self.zoom.value() + 25))
        toolbar.addWidget(zoom_in, 0, 6)
        fit = QPushButton("Fit")
        fit.clicked.connect(lambda: self.zoom.setValue(100))
        toolbar.addWidget(fit, 0, 7)
        self.magnifier_button = QPushButton("Magnifier")
        self.magnifier_button.setCheckable(True)
        self.magnifier_button.setChecked(bool(self.state.get("magnifier")))
        self.magnifier_button.toggled.connect(
            lambda checked: self._set_option("magnifier", checked)
        )
        toolbar.addWidget(self.magnifier_button, 1, 0, 1, 2)
        self.magnifier_grid_button = QPushButton("Magnifier Grid")
        self.magnifier_grid_button.setCheckable(True)
        self.magnifier_grid_button.setChecked(bool(self.state.get("magnifier_grid")))
        self.magnifier_grid_button.toggled.connect(
            lambda checked: self._set_option("magnifier_grid", checked)
        )
        toolbar.addWidget(self.magnifier_grid_button, 1, 2, 1, 2)
        self.blink_button = QPushButton("Blink")
        self.blink_button.setCheckable(True)
        self.blink_button.toggled.connect(self._toggle_blink)
        toolbar.addWidget(self.blink_button, 1, 4)
        self.box_target = QComboBox()
        self.box_target.addItems(["Care Area", "Noise", "POI"])
        toolbar.addWidget(self.box_target, 1, 5)
        edit_box = QPushButton("Edit Box")
        edit_box.clicked.connect(self._edit_box)
        toolbar.addWidget(edit_box, 1, 6)
        draw_ca = QPushButton("Draw CA")
        draw_ca.clicked.connect(self._draw_ca)
        toolbar.addWidget(draw_ca, 1, 7)
        reset_boxes = QPushButton("Reset Boxes")
        reset_boxes.clicked.connect(self._reset_boxes)
        toolbar.addWidget(reset_boxes, 2, 6, 1, 2)
        layout.addLayout(toolbar)
        self.preview = NanoPointPreview(self.state, self._box_changed)
        layout.addWidget(self.preview, 1)
        options = QGridLayout()
        self.show_ca = QCheckBox("CA")
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
        for index, check in enumerate(
            (self.show_ca, self.show_noise, self.show_poi, self.false_colors, self.auto_scale, self.show_sem_box)
        ):
            options.addWidget(check, index // 3, index % 3)
        layout.addLayout(options)
        sem_row = QGridLayout()
        for index, (text, handler) in enumerate((
            ("Browse SEM Image", self._browse_sem),
            ("Show SEM Image", self._show_sem),
            ("FOV Settings", self._sem_fov),
            ("Rotate 90", self._rotate_sem),
            ("Draw Care Area on SEM", self._draw_sem_care_area),
        )):
            button = QPushButton(text)
            button.clicked.connect(handler)
            sem_row.addWidget(button, index // 3, index % 3)
        layout.addLayout(sem_row)
        result_row = QHBoxLayout()
        result_row.addWidget(QLabel("Correlation Result"))
        self.sem_match = QComboBox()
        self.sem_match.currentIndexChanged.connect(self._sem_match_changed)
        result_row.addWidget(self.sem_match, 1)
        use_match = QPushButton("Use Selected Care Area")
        use_match.clicked.connect(self._use_sem_care_area)
        result_row.addWidget(use_match)
        layout.addLayout(result_row)
        parameters = QGridLayout()
        parameters.addWidget(QLabel("MCA Size"), 0, 0)
        self.mca_size = QSpinBox()
        self.mca_size.setRange(5, 21)
        self.mca_size.setValue(int(self.state.get("mca_size", 5)))
        self.mca_size.valueChanged.connect(lambda value: self._set_numeric("mca_size", value))
        parameters.addWidget(self.mca_size, 0, 1)
        parameters.addWidget(QLabel("Noise Box Size"), 0, 2)
        self.noise_box_size = QSpinBox()
        self.noise_box_size.setRange(48, 80)
        self.noise_box_size.setValue(int(self.state.get("noise_box_size", 64)))
        self.noise_box_size.valueChanged.connect(
            lambda value: self._set_numeric("noise_box_size", value)
        )
        parameters.addWidget(self.noise_box_size, 0, 3)
        parameters.addWidget(QLabel("SEM Overlay Opacity"), 1, 0)
        self.sem_opacity = QSlider(Qt.Horizontal)
        self.sem_opacity.setRange(0, 100)
        self.sem_opacity.setValue(int(self.state.get("sem_opacity", 60)))
        self.sem_opacity.valueChanged.connect(
            lambda value: self._set_numeric("sem_opacity", value)
        )
        parameters.addWidget(self.sem_opacity, 1, 1, 1, 3)
        layout.addLayout(parameters)
        self.details = QLabel("Select a template to inspect its image parameters.")
        self.details.setWordWrap(True)
        self.details.setMinimumHeight(52)
        layout.addWidget(self.details)
        return layout

    def _generic_controls(self):
        layout = QGridLayout()
        self.source = QLabel()
        layout.addWidget(self.source, 0, 0, 1, 4)
        for index, (text, handler) in enumerate((
            ("Select Defect Data", self._select_source),
            ("Review", self._review),
            ("Reference Die", self._reference_die),
        )):
            button = QPushButton(text)
            button.clicked.connect(handler)
            layout.addWidget(button, 1, index)
        self.grab_button = QPushButton("Grab Images")
        self.grab_button.clicked.connect(self._grab_images)
        grab_menu = QMenu(self.grab_button)
        grab_menu.addAction("Grab Missing Images", lambda: self._grab_images(False))
        grab_menu.addAction("Re-Grab all Images", lambda: self._grab_images(True))
        self.grab_button.setMenu(grab_menu)
        layout.addWidget(self.grab_button, 1, 3)
        for index, (text, handler) in enumerate((
            ("Search POI", self._search_poi),
            ("Information", self._information),
            ("Finish", self._finish),
            ("Cancel", self.reject),
        )):
            button = QPushButton(text)
            button.clicked.connect(handler)
            layout.addWidget(button, 2, index)
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
            self.state["images_grabbed"] = False
            self._refresh()

    def _flip(self, direction):
        row = self.table.currentRow()
        if not 0 <= row < len(self.state["templates"]):
            return
        flips = self.state["templates"][row].setdefault("flips", [])
        if direction not in flips:
            flips.append(direction)
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
        self.preview.editing_box = None
        self.preview.update()
        self._selection_changed()

    def _box_changed(self, key, region):
        template = self._selected_template()
        if template is None:
            return
        template[key] = list(region)
        self.state["images_grabbed"] = False
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
        sem["visible"] = True
        self.image_type.setCurrentText("SEM")
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

    def _set_numeric(self, key, value):
        self.state[key] = int(value)
        self.preview.update()

    def _image_changed(self, value):
        if value == "SEM":
            template = self._selected_template()
            if template is None or not template.get("has_sem_image"):
                self.image_type.blockSignals(True)
                self.image_type.setCurrentText("Test")
                self.image_type.blockSignals(False)
                value = "Test"
        self.state["image_type"] = "Golden" if value == "Golden Image" else value
        self.preview.update()

    def _zoom_changed(self, value):
        self.state["zoom"] = int(value)
        self.preview.update()

    def _selection_changed(self):
        row = self.table.currentRow()
        self.preview.selected = row
        self.preview.update()
        if not 0 <= row < len(self.state["templates"]):
            return
        template = self.state["templates"][row]
        sem = template.setdefault("sem", default_sem_state())
        self.sem_match.blockSignals(True)
        self.sem_match.clear()
        for match in sem.get("matches", []):
            self.sem_match.addItem(f"{match.get('name')} ({float(match.get('score', 0)):.2f})")
        selected = int(sem.get("selected_match", -1))
        if 0 <= selected < self.sem_match.count():
            self.sem_match.setCurrentIndex(selected)
        self.sem_match.blockSignals(False)
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
        self.state["images_grabbed"] = False

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
                "Patch + SEM" if template.get("has_sem_image") else "Patch",
                template.get("linked_care_area", ""),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in (1, 2, 6, 7):
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if column == 4:
                    item.setCheckState(Qt.Checked if template.get("search", True) else Qt.Unchecked)
                self.table.setItem(row, column, item)
        self._loading = False
        source = self.state.get("defect_source")
        self.source.setText(
            f"Defect Source: {Path(source).name}" if source else "Defect Source: Not selected"
        )
        self.preview.state = self.state
        self.preview.update()

    def _finish(self):
        errors = validate_nanopoint_state(self.state)
        if errors:
            QMessageBox.warning(self, "NanoPoint Image Templates", "\n".join(errors))
            return
        self.result_state = deepcopy(self.state)
        self.accept()


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
    def __init__(self, state, on_box_changed=None, parent=None):
        super().__init__(parent)
        self.state = state
        self.on_box_changed = on_box_changed
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
        region = [
            max(0.0, min(x1, x2) / max(1, self.width())),
            max(0.0, min(y1, y2) / max(1, self.height())),
            min(1.0, abs(x2 - x1) / max(1, self.width())),
            min(1.0, abs(y2 - y1) / max(1, self.height())),
        ]
        if self.on_box_changed:
            self.on_box_changed(self.editing_box, region)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        base = {
            "Test": "#315f72",
            "Reference": "#52666f",
            "Difference": "#253d48",
            "Golden": "#596c57",
            "SEM": "#55585b",
        }.get(self.state.get("image_type"), "#315f72")
        painter.fillRect(self.rect(), QColor(base))
        zoom = max(0.25, float(self.state.get("zoom", 100)) / 100)
        spacing = max(10, int(30 * zoom))
        painter.setPen(QPen(QColor("#8eb6c5"), 1))
        for offset in range(0, self.width(), spacing):
            painter.drawLine(offset, 0, offset, self.height())
        for offset in range(0, self.height(), spacing):
            painter.drawLine(0, offset, self.width(), offset)
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
        if self.state.get("image_type") == "SEM" and 0 <= self.selected < len(self.state.get("templates", [])):
            template = self.state["templates"][self.selected]
            sem = template.get("sem") or {}
            matches = sem.get("matches") or []
            for index, match in enumerate(matches):
                x, y, width, height = match.get("area", [0, 0, 0, 0])
                color = "#00ff66" if index == int(sem.get("selected_match", -1)) else "#ffcc00"
                painter.setPen(QPen(QColor(color), 2))
                painter.drawRect(
                    int(x * self.width()),
                    int(y * self.height()),
                    int(width * self.width()),
                    int(height * self.height()),
                )
            if self.state.get("show_sem_bounding_box"):
                bounding = QColor("#ff3030")
                bounding.setAlpha(max(20, int(255 * int(self.state.get("sem_opacity", 60)) / 100)))
                painter.setPen(QPen(bounding, 2))
                painter.drawRect(55, 55, max(20, self.width() - 110), max(20, self.height() - 110))
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
        x, y, width, height = [float(value) for value in region[:4]]
        painter.drawRect(
            int(x * self.width()),
            int(y * self.height()),
            int(width * self.width()),
            int(height * self.height()),
        )

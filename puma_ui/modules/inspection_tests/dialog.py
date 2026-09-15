from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Optional

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
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    Qt,
    QTimer,
    QVBoxLayout,
    QWidget,
)
from ...widgets import ClassicButton
from .care_areas import CareAreasDialog, default_care_area_state, normalized_care_area_state
from .fourier import (
    FourierFilterTrainingDialog,
    default_fourier_state,
    normalize_fourier_state,
    validate_fourier_state,
)
from .light_training import (
    LightTrainingDialog,
    default_light_training_state,
    normalized_light_training_state,
    validate_light_training_state,
)
from .nef import (
    IdoClassifierDialog,
    NuisanceFilterSetupDialog,
    classifier_compatibility_errors,
    classifier_from_path,
    default_nef_state,
    normalize_classifier,
    normalize_nef_state,
    validate_nef_state,
)
from .nanopoint import (
    NanoPointImageTemplatesDialog,
    default_nanopoint_state,
    normalize_nanopoint_state,
    validate_nanopoint_state,
)
from .sample_plan import SamplePlanDialog, default_sample_plan, normalized_sample_plan
from .segmentation import SegmentationDialog, default_segmentation_state
from .sensitivity import (
    SensitivityDialog,
    default_sensitivity_state,
    validate_sensitivity,
)


ORIENTATIONS = ["Up (0 deg.)", "Right (90 deg.)", "Down (180 deg.)", "Left (270 deg.)"]
FOURIER_RETRAIN_FIELDS = {"incidence_angle", "pixel_size", "sample_rate", "iris"}


def optics_change_invalidates_fourier(field: str) -> bool:
    return field in FOURIER_RETRAIN_FIELDS


def iris_options(
    pixel_size: str,
    channel_index: int,
    incidence_angle: str = "Oblique",
) -> list[str]:
    if pixel_size == "SL610":
        return ["OPEN"]
    options = ["OPEN", "FWD", "BKWD", "FWD_BKWD"]
    if channel_index == 2 and incidence_angle == "Oblique":
        options.append("CENTER")
    return options


def default_test(number: int, wafer_type: str = "Patterned", orientation: str = "Down (180 deg.)") -> dict:
    mode = "Test" if wafer_type == "Blank" else "Random"
    return {
        "name": f"Test {number}",
        "mode": mode,
        "orientation": orientation,
        "optics_name": "",
        "run_single_die": False,
        "focus_offset": 0.0,
        "focus_mode": "Median Die",
        "save_image_patches": False,
        "sensitivity_tuner_scan": "OFF",
        "coverage": 100,
        "save_feature_vectors": False,
        "feature_vector_version": "3.0A",
        "run_nef": False,
        "nef": default_nef_state(),
        "nano_point_templates": default_nanopoint_state(),
        "run_ido": False,
        "ido_classifier": None,
        "run_dbb": False,
        "dbb_classifier": None,
        "run_unsupervised_grouping": False,
        "unsupervised_groups": 8,
        "inspection_optics": {
            "pixel_size": "SL815",
            "sample_rate": "2.8 (Default)",
            "speed": "High Throughput Mode",
            "incident_polarization": "P-POL",
            "incidence_angle": "Oblique",
            "laser_power_density": 0.004341,
        },
        "channels": [
            {
                "name": "1 (Left)",
                "enabled": True,
                "polarization": "None",
                "light_level": 8.64,
                "iris": "OPEN",
                "imaging_mode": "DoubleDarkField",
                "use_fourier_filter": False,
            },
            {
                "name": "2 (Right)",
                "enabled": True,
                "polarization": "None",
                "light_level": 7.41,
                "iris": "OPEN",
                "imaging_mode": "DoubleDarkField",
                "use_fourier_filter": False,
            },
            {
                "name": "3 (Center)",
                "enabled": True,
                "polarization": "None",
                "light_level": 2.26,
                "iris": "OPEN",
                "imaging_mode": "DarkField",
                "use_fourier_filter": False,
            },
        ],
        "fourier_trained": False,
        "fourier": default_fourier_state(),
        "light_trained": False,
        "light_training": default_light_training_state(),
        "care_areas": default_care_area_state(),
        "segmentation": default_segmentation_state(),
        "sample_plan": default_sample_plan(),
        "sensitivity": default_sensitivity_state(),
        "status": "Incomplete",
    }


def normalize_test(test: dict, number: int, wafer_type: str, orientation: str) -> dict:
    result = default_test(number, wafer_type, orientation)
    if not isinstance(test, dict):
        return result
    for key, value in test.items():
        if key not in {"inspection_optics", "channels", "nef", "fourier", "nano_point_templates", "ido_classifier", "dbb_classifier"}:
            result[key] = deepcopy(value)
    result["inspection_optics"].update(deepcopy(test.get("inspection_optics") or {}))
    channels = test.get("channels") or []
    for index, channel in enumerate(channels[:3]):
        result["channels"][index].update(deepcopy(channel))
    result["nef"] = normalize_nef_state(test.get("nef"))
    result["ido_classifier"] = normalize_classifier(test.get("ido_classifier"))
    result["dbb_classifier"] = deepcopy(test.get("dbb_classifier"))
    result["fourier"] = normalize_fourier_state(test.get("fourier"))
    result["nano_point_templates"] = normalize_nanopoint_state(test.get("nano_point_templates"))
    if result.get("run_ido"):
        result["save_feature_vectors"] = True
    if result.get("run_unsupervised_grouping"):
        result["save_feature_vectors"] = True
    pixel = result["inspection_optics"].get("pixel_size", "SL815")
    incidence_angle = result["inspection_optics"].get("incidence_angle", "Oblique")
    for index, channel in enumerate(result["channels"]):
        if channel.get("iris") not in iris_options(pixel, index, incidence_angle):
            channel["iris"] = "OPEN"
    return result


def validate_test(test: dict) -> list[str]:
    if test.get("mode") == "No Test":
        return ["test is not defined"]
    errors = []
    if not any(channel.get("enabled") for channel in test.get("channels", [])):
        errors.append("no collection channel is enabled")
    care_state = normalized_care_area_state(test.get("care_areas"))
    if not any(group.get("enabled", True) for group in care_state["groups"]):
        errors.append("no enabled Care Area Group is defined")
    uses_fourier = any(
        channel.get("enabled") and channel.get("use_fourier_filter")
        for channel in test.get("channels", [])
    )
    if uses_fourier:
        if not test.get("fourier_trained"):
            errors.append("Fourier Filter is enabled but training is incomplete")
        else:
            errors.extend(validate_fourier_state(test.get("fourier")))
    if not test.get("light_trained"):
        errors.append("Light Training is incomplete")
    else:
        errors.extend(
            validate_light_training_state(
                test.get("light_training"),
                test.get("focus_mode", "Median Die"),
                care_state,
                care_state.get("die_size_um", [5100.0, 16600.0]),
            )
        )
    errors.extend(validate_sensitivity(test.get("sensitivity") or default_sensitivity_state()))
    if test.get("run_single_die") and not test.get("segmentation", {}).get("sdi", {}).get("measured"):
        errors.append("Single Die Inspection cell size is not measured")
    if test.get("run_nef"):
        nef_state = normalize_nef_state(test.get("nef"))
        if not nef_state["classifiers"]:
            errors.append("NEF is enabled but no classifier is attached")
        errors.extend(
            validate_nef_state(
                nef_state,
                test.get("orientation", ""),
                test.get("feature_vector_version", "3.0A"),
            )
        )
    if test.get("run_ido"):
        classifier = normalize_classifier(test.get("ido_classifier"))
        if classifier is None:
            errors.append("iDO is enabled but no iDO classifier is attached")
        elif classifier.get("type") != "iDO":
            errors.append("Run iDO requires an iDO classifier")
        else:
            errors.extend(
                classifier_compatibility_errors(
                    classifier,
                    test.get("orientation", ""),
                    test.get("feature_vector_version", "3.0A"),
                )
            )
        if not test.get("save_feature_vectors"):
            errors.append("Run iDO requires Save Feature Vectors")
    if test.get("run_dbb") and not test.get("dbb_classifier"):
        errors.append("DBB is enabled but no DBB classifier is attached")
    if test.get("run_unsupervised_grouping"):
        groups = int(test.get("unsupervised_groups", 8))
        if not 2 <= groups <= 32:
            errors.append("Unsupervised Grouping requires between 2 and 32 groups")
        if not test.get("save_feature_vectors"):
            errors.append("Unsupervised Grouping requires Save Feature Vectors")
    errors.extend(validate_nanopoint_state(test.get("nano_point_templates")))
    return errors


class TestsSetupDialog(QDialog):
    PARAMETER_ROWS = [
        ("Mode", "mode", "mode"),
        ("Test Orientation", "orientation", "orientation"),
        ("Test Name", "name", "text"),
        ("Optics Name", "optics_name", "text"),
        ("Run Single Die Inspection", "run_single_die", "check"),
        ("Focus Offset", "focus_offset", "focus"),
        ("Focus Mode", "focus_mode", "focus_mode"),
        ("Save Image Patches", "save_image_patches", "check"),
        ("Sensitivity Tuner Scan", "sensitivity_tuner_scan", "scan"),
        ("Coverage %", "coverage", "coverage"),
        ("Feature Vectors", "feature_vectors", "section"),
        ("    Save Feature Vectors", "save_feature_vectors", "check"),
        ("    Feature Vector Version", "feature_vector_version", "feature_version"),
        ("NEF", "nef", "section"),
        ("    NEF Classifier(s)", "", "nef_classifier"),
        ("    View NEF Classifier(s)", "", "nef_view"),
        ("    Run NEF", "run_nef", "check"),
        ("iDO", "ido", "section"),
        ("    iDO Classifier", "", "ido_classifier"),
        ("    View iDO Classifier", "", "ido_view"),
        ("    Run iDO", "run_ido", "check"),
        ("Design Based Binning", "design_based_binning", "section"),
        ("    DBB Classifier", "", "dbb_classifier"),
        ("    Run DBB", "run_dbb", "check"),
        ("Unsupervised Grouping", "unsupervised_grouping", "section"),
        ("    # Groups", "unsupervised_groups", "group_count"),
        ("    Run Unsupervised Grouping", "run_unsupervised_grouping", "check"),
        ("Test Info", "test_info", "section"),
        ("    # Care Areas", "care_area_count", "test_info"),
        ("    Area (cm2)", "care_area_cm2", "test_info"),
        ("    # Die", "die_count", "test_info"),
        ("    Time (MM:SS)", "estimated_time", "test_info"),
        ("    % of Die As Care Area", "care_area_percent", "test_info"),
        ("Inspection Optics", "inspection_optics", "section"),
        ("    Inspection Pixel Size", "pixel_size", "pixel"),
        ("    Inspection Sample Rate", "sample_rate", "sample_rate"),
        ("    Speed", "speed", "speed"),
        ("    Incident Polarization", "incident_polarization", "incident"),
        ("    Incidence Angle", "incidence_angle", "angle"),
        ("    Laser Power Density", "laser_power_density", "laser"),
    ]

    def __init__(
        self,
        tests: Optional[list[dict]] = None,
        *,
        wafer_type: str = "Patterned",
        wafer_orientation: str = "Down (180 deg.)",
        inner_die_defined: bool = False,
        wafer_loaded: bool = False,
        wafer_aligned: bool = False,
        wafer_geometry_defined: bool = True,
        die_size_um=(5100.0, 16600.0),
        defect_data: Optional[dict] = None,
        wafer_context_provider=None,
        initial_module: Optional[str] = None,
        initial_test_index: int = 0,
        parent=None,
    ):
        super().__init__(parent)
        self.wafer_type = wafer_type
        self.wafer_orientation = wafer_orientation
        self.inner_die_defined = bool(inner_die_defined)
        self.wafer_loaded = bool(wafer_loaded)
        self.wafer_aligned = bool(wafer_aligned)
        self.wafer_geometry_defined = bool(wafer_geometry_defined)
        self.die_size_um = [float(value) for value in die_size_um[:2]]
        self.defect_data = deepcopy(defect_data or {})
        self.wafer_context_provider = wafer_context_provider
        self.tests = [
            normalize_test(item, index + 1, wafer_type, wafer_orientation)
            for index, item in enumerate(tests or [])
        ]
        self.result_tests = None
        self.changed = False
        self.current_test = max(0, min(int(initial_test_index), len(self.tests) - 1)) if self.tests else 0
        self.test_clipboard = None
        self.sample_plan_clipboard = None
        self.stage_orientation = wafer_orientation
        self.stage_rotation_performed = False
        self._loading = False
        self.section_expanded = {
            "feature_vectors": False,
            "nef": False,
            "ido": False,
            "design_based_binning": False,
            "unsupervised_grouping": False,
            "test_info": False,
            "inspection_optics": True,
        }
        self.initial_module = initial_module
        self.setWindowTitle("Tests")
        self.resize(1280, 820)
        self.setMinimumSize(1040, 700)
        self._build_ui()
        self._ensure_display_test()
        self._rebuild_matrix()
        self._refresh_external_wafer_context()
        if self.initial_module:
            QTimer.singleShot(0, self._open_initial_module)

    def _open_initial_module(self):
        self._refresh_external_wafer_context()
        module = self.initial_module
        self.initial_module = None
        handlers = {
            "fourier_filter": self._fourier_training,
            "light_level": self._light_training,
            "sensitivity": self._sensitivity_setup,
            "defect_filters": self._sensitivity_setup,
            "care_areas": self._care_areas,
            "sample_plan": self._sample_plan,
        }
        handler = handlers.get(module)
        if handler:
            handler()

    def update_wafer_context(
        self,
        *,
        wafer_loaded: bool,
        wafer_aligned: bool,
        wafer_geometry_defined: bool,
        die_size_um=None,
    ):
        self.wafer_loaded = bool(wafer_loaded)
        self.wafer_aligned = bool(wafer_aligned)
        self.wafer_geometry_defined = bool(wafer_geometry_defined)
        if die_size_um is not None:
            self.die_size_um = [float(value) for value in die_size_um[:2]]
        retrain_ready = self.wafer_loaded and self.wafer_aligned
        for widget_name in (
            "test_selection",
            "retrain_light",
            "retrain_fourier",
            "do_not_retrain_valid",
            "retrain_button",
        ):
            widget = getattr(self, widget_name, None)
            if widget is not None:
                widget.setEnabled(retrain_ready)
        if hasattr(self, "retrain_button"):
            self.retrain_button.setToolTip(
                "" if retrain_ready else "Load and align a wafer before retraining."
            )
        self._refresh_module_buttons()

    def _refresh_external_wafer_context(self):
        if self.wafer_context_provider is None:
            return
        context = self.wafer_context_provider() or {}
        self.update_wafer_context(
            wafer_loaded=context.get("wafer_loaded", self.wafer_loaded),
            wafer_aligned=context.get("wafer_aligned", self.wafer_aligned),
            wafer_geometry_defined=context.get(
                "wafer_geometry_defined", self.wafer_geometry_defined
            ),
            die_size_um=context.get("die_size_um", self.die_size_um),
        )

    def _build_ui(self):
        self.setStyleSheet(
            """
            QDialog { background: #cfcbc2; color: #111; font-family: Arial; font-size: 10px; }
            QPushButton { background: #e7e5dc; border: 1px solid #77736b; min-height: 25px; padding: 2px 8px; }
            QTableWidget { background: #efefec; border: 1px solid #77736b; gridline-color: #aaa69d; }
            QHeaderView::section { background: #d8d5cd; border: 1px solid #8d8980; padding: 4px; }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox { background: white; border: 1px solid #8a867d; min-height: 22px; }
            QFrame#rightPanel { background: #d7d4cc; border-left: 1px solid #aaa69d; }
            """
        )
        root = QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)
        root.addWidget(self._left_menu())

        center = QVBoxLayout()
        self.matrix = QTableWidget()
        self.matrix.verticalHeader().setVisible(False)
        self.matrix.setSelectionMode(QAbstractItemView.NoSelection)
        self.matrix.setContextMenuPolicy(Qt.CustomContextMenu)
        self.matrix.customContextMenuRequested.connect(self._show_test_menu)
        self.matrix.cellClicked.connect(self._matrix_cell_clicked)
        self.matrix.horizontalHeader().sectionClicked.connect(lambda section: self._select_test(max(0, section - 1)))
        center.addWidget(self.matrix, 3)

        channel_title = QLabel("Collection Channels for Current Test")
        channel_title.setStyleSheet("font-weight: 700;")
        center.addWidget(channel_title)
        self.channel_table = QTableWidget(6, 4)
        self.channel_table.verticalHeader().setVisible(False)
        self.channel_table.setFixedHeight(210)
        self.channel_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        center.addWidget(self.channel_table, 1)
        root.addLayout(center, 1)
        root.addWidget(self._right_panel())

    def _left_menu(self) -> QFrame:
        panel = QFrame()
        panel.setFixedWidth(132)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)
        add_test = ClassicButton("Add Test")
        add_test.clicked.connect(self._add_test)
        layout.addWidget(add_test)
        handlers = {
            "NEF Classifiers": self._nef_setup,
            "iDO Classifier": self._ido_setup,
            "NP Image\nTemplates": self._nanopoint_templates,
            "Fourier Filter\nTraining": self._fourier_training,
            "Care Areas": self._care_areas,
            "Light Training": self._light_training,
            "Segmentation": self._segmentation,
            "Sample Plan": self._sample_plan,
            "Sensitivity\nSetup": self._sensitivity_setup,
        }
        self.module_buttons = {}
        for label, handler in handlers.items():
            button = ClassicButton(label, arrow=True)
            button.clicked.connect(handler)
            layout.addWidget(button)
            self.module_buttons[label] = button
        layout.addStretch(1)
        end = ClassicButton("End")
        end.clicked.connect(self._finish)
        layout.addWidget(end)
        return panel

    def _right_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("rightPanel")
        panel.setFixedWidth(220)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        self.current_label = QLabel("Current Test:  Test 1")
        self.current_label.setStyleSheet("font-weight: 700;")
        layout.addWidget(self.current_label)
        layout.addWidget(QLabel("Test Selection"))
        self.test_selection = QComboBox()
        self.test_selection.addItems(["Current Test", "All Tests"])
        layout.addWidget(self.test_selection)
        layout.addWidget(QLabel("Result Test"))
        self.result_test = QComboBox()
        layout.addWidget(self.result_test)
        self.defined_only = QCheckBox("Defined Tests Only")
        self.defined_only.toggled.connect(self._rebuild_matrix)
        layout.addWidget(self.defined_only)
        layout.addWidget(QLabel("Retrain"))
        self.retrain_light = QCheckBox("Light")
        self.retrain_fourier = QCheckBox("Fourier Filter")
        layout.addWidget(self.retrain_light)
        layout.addWidget(self.retrain_fourier)
        self.do_not_retrain_valid = QCheckBox("Do not retrain valid tests")
        layout.addWidget(self.do_not_retrain_valid)
        self.retrain_button = QPushButton("Retrain")
        self.retrain_button.clicked.connect(self._retrain)
        layout.addWidget(self.retrain_button)
        retrain_ready = self.wafer_loaded and self.wafer_aligned
        for widget in (
            self.test_selection,
            self.retrain_light,
            self.retrain_fourier,
            self.do_not_retrain_valid,
            self.retrain_button,
        ):
            widget.setEnabled(retrain_ready)
        self.retrain_button.setToolTip(
            "" if retrain_ready else "Load and align a wafer before retraining."
        )
        layout.addSpacing(14)
        hint = QLabel("Right-click the test matrix to copy, paste, or delete the selected test.")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addStretch(1)
        return panel

    def _ensure_display_test(self):
        if not self.tests:
            placeholder = default_test(1, self.wafer_type, self.wafer_orientation)
            placeholder["mode"] = "No Test"
            placeholder["status"] = "Undefined"
            self.tests.append(placeholder)

    def _rebuild_matrix(self, checked: bool = False):
        self._loading = True
        visible_indexes = [
            index
            for index, test in enumerate(self.tests)
            if not self.defined_only.isChecked() or test.get("mode") != "No Test"
        ]
        if not visible_indexes:
            visible_indexes = [0]
        self.visible_indexes = visible_indexes
        self.matrix.clear()
        self.matrix.setRowCount(len(self.PARAMETER_ROWS))
        self.matrix.setColumnCount(len(visible_indexes) + 1)
        self.matrix.setHorizontalHeaderLabels([""] + [self.tests[index].get("name", f"Test {index + 1}") for index in visible_indexes])
        self.matrix.setColumnWidth(0, 205)
        active_section = None
        for row, (label, key, kind) in enumerate(self.PARAMETER_ROWS):
            if kind == "section":
                active_section = key
                marker = "-" if self.section_expanded.get(key, False) else "+"
                display_label = f"{marker}  {label}"
            else:
                display_label = label
            parameter = QTableWidgetItem(display_label)
            parameter.setFlags(parameter.flags() & ~Qt.ItemIsEditable)
            parameter.setBackground(QColor("#d5d2ca"))
            self.matrix.setItem(row, 0, parameter)
            self.matrix.setRowHeight(row, 29)
            for visible_column, test_index in enumerate(visible_indexes, start=1):
                self.matrix.setCellWidget(row, visible_column, self._parameter_widget(test_index, key, kind))
            self.matrix.setRowHidden(
                row,
                kind != "section"
                and active_section is not None
                and not self.section_expanded.get(active_section, False),
            )
        self.matrix.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        for column in range(1, self.matrix.columnCount()):
            self.matrix.horizontalHeader().setSectionResizeMode(column, QHeaderView.Stretch)
        self.current_test = min(self.current_test, len(self.tests) - 1)
        self._loading = False
        self._refresh_current_test()

    def _matrix_cell_clicked(self, row: int, column: int):
        if column == 0 and 0 <= row < len(self.PARAMETER_ROWS):
            _label, key, kind = self.PARAMETER_ROWS[row]
            if kind == "section":
                self.section_expanded[key] = not self.section_expanded.get(key, False)
                self._rebuild_matrix()
                return
        self._select_test(max(0, column - 1))

    def _parameter_widget(self, test_index: int, key: str, kind: str) -> QWidget:
        test = self.tests[test_index]
        optics = test["inspection_optics"]
        source = optics if key in optics else test
        value = source.get(key)
        if kind == "section":
            label = QLabel("")
            label.setStyleSheet("background: #d5d2ca;")
            return label
        if kind == "test_info":
            label = QLabel(self._test_info_value(test, key))
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("background: #eceae4; color: #333;")
            return label
        if kind in {"nef_classifier", "ido_classifier", "dbb_classifier"}:
            wrapper = QWidget()
            row = QHBoxLayout(wrapper)
            row.setContentsMargins(2, 1, 2, 1)
            value_label = QLineEdit(self._classifier_label(test, kind))
            value_label.setReadOnly(True)
            browse = QPushButton("...")
            browse.setFixedWidth(30)
            if kind == "nef_classifier":
                browse.clicked.connect(lambda checked=False, index=test_index: self._select_single_nef(index))
            elif kind == "ido_classifier":
                browse.clicked.connect(lambda checked=False, index=test_index: self._select_ido(index))
            else:
                browse.clicked.connect(lambda checked=False, index=test_index: self._select_dbb(index))
            row.addWidget(value_label, 1)
            row.addWidget(browse)
            return wrapper
        if kind in {"nef_view", "ido_view"}:
            button = QPushButton(
                "View" if self._classifier_available(test, kind) else "Not Available"
            )
            button.setEnabled(self._classifier_available(test, kind))
            if kind == "nef_view":
                button.clicked.connect(lambda checked=False, index=test_index: self._view_nef(index))
            else:
                button.clicked.connect(lambda checked=False, index=test_index: self._view_ido(index))
            return button
        if kind in {"mode", "orientation", "scan", "focus_mode", "pixel", "sample_rate", "speed", "incident", "angle", "feature_version"}:
            combo = QComboBox()
            values = {
                "mode": ["No Test", "Random"] + (["Test"] if self.wafer_type == "Blank" else []),
                "orientation": ORIENTATIONS,
                "scan": ["OFF", "ON"],
                "focus_mode": ["Median Die", "Center Die", "Active Die"],
                "pixel": ["SL610", "SL815", "SL890", "SL1020"],
                "sample_rate": ["2.0", "2.6", "2.8 (Default)", "3.0", "4.0"],
                "speed": ["High Throughput Mode", "High Sensitivity Mode", "High Sensitivity 4 Mode"],
                "incident": ["P-POL", "S-POL", "C-POL"],
                "angle": ["Oblique", "Normal"],
                "feature_version": ["3.0A", "2.0", "1.0"],
            }[kind]
            combo.addItems(values)
            combo.setCurrentText(str(value))
            if kind == "orientation":
                combo.currentTextChanged.connect(
                    lambda text, index=test_index, widget=combo: self._change_orientation(index, text, widget)
                )
            elif kind == "mode":
                combo.currentTextChanged.connect(
                    lambda text, index=test_index, widget=combo: self._change_mode(index, text, widget)
                )
            else:
                combo.currentTextChanged.connect(lambda text, index=test_index, field=key: self._set_value(index, field, text))
            return combo
        if kind == "text":
            edit = QLineEdit(str(value or ""))
            edit.editingFinished.connect(lambda index=test_index, field=key, widget=edit: self._set_value(index, field, widget.text()))
            return edit
        if kind == "check":
            wrapper = QWidget()
            row = QHBoxLayout(wrapper)
            row.setContentsMargins(0, 0, 0, 0)
            box = QCheckBox()
            box.setChecked(bool(value))
            box.toggled.connect(lambda checked, index=test_index, field=key: self._set_value(index, field, checked))
            row.addStretch(1)
            row.addWidget(box)
            row.addStretch(1)
            return wrapper
        if kind == "focus":
            spin = QDoubleSpinBox()
            spin.setDecimals(3)
            spin.setRange(-50.0, 50.0)
            spin.setSingleStep(0.125)
            spin.setSuffix(" um")
            spin.setValue(float(value or 0.0))
            spin.valueChanged.connect(lambda number, index=test_index, field=key: self._set_value(index, field, number))
            return spin
        if kind == "coverage":
            spin = QSpinBox()
            spin.setRange(1, 100)
            spin.setSuffix(" %")
            spin.setValue(int(value or 100))
            spin.valueChanged.connect(lambda number, index=test_index, field=key: self._set_value(index, field, number))
            return spin
        if kind == "group_count":
            spin = QSpinBox()
            spin.setRange(2, 32)
            spin.setValue(int(value or 8))
            spin.setEnabled(bool(test.get("run_unsupervised_grouping")))
            spin.valueChanged.connect(lambda number, index=test_index, field=key: self._set_value(index, field, number))
            return spin
        if kind == "laser":
            spin = QDoubleSpinBox()
            spin.setDecimals(6)
            spin.setRange(0.0, 10.0)
            spin.setValue(float(value or 0.0))
            spin.valueChanged.connect(lambda number, index=test_index, field=key: self._set_value(index, field, number))
            return spin
        return QLabel(str(value or ""))

    def _test_info_value(self, test: dict, key: str) -> str:
        groups = [
            group for group in (test.get("care_areas") or {}).get("groups", [])
            if group.get("enabled", True) and group.get("kind") != "DCA"
        ]
        rectangles = [area for group in groups for area in group.get("areas", [])]
        normalized_area = sum(
            max(0.0, float(area[2])) * max(0.0, float(area[3]))
            for area in rectangles if len(area) >= 4
        )
        die_width, die_height = self.die_size_um
        area_cm2 = normalized_area * die_width * die_height / 100_000_000.0
        sample_plan = test.get("sample_plan") or {}
        selected = sample_plan.get("selected_die") or sample_plan.get("selected_dies") or []
        die_count = int(sample_plan.get("selected_count", len(selected)))
        if die_count <= 0 and test.get("mode") != "No Test":
            die_count = int(sample_plan.get("valid_die_count", 0))
        estimated_seconds = max(0, round(area_cm2 * max(1, die_count) * 3.0))
        values = {
            "care_area_count": str(len(rectangles)),
            "care_area_cm2": f"{area_cm2:.4f}",
            "die_count": str(die_count),
            "estimated_time": f"{estimated_seconds // 60:02d}:{estimated_seconds % 60:02d}",
            "care_area_percent": f"{min(100.0, normalized_area * 100.0):.2f}",
        }
        return values.get(key, "-")

    @staticmethod
    def _classifier_label(test: dict, kind: str) -> str:
        if kind == "nef_classifier":
            classifiers = normalize_nef_state(test.get("nef"))["classifiers"]
            if len(classifiers) > 1:
                return "<<multiple>>"
            return classifiers[0]["name"] if classifiers else "none"
        key = "ido_classifier" if kind == "ido_classifier" else "dbb_classifier"
        classifier = test.get(key) or {}
        return str(classifier.get("name") or "none")

    @staticmethod
    def _classifier_available(test: dict, kind: str) -> bool:
        if kind == "nef_view":
            return bool(normalize_nef_state(test.get("nef"))["classifiers"])
        return bool(test.get("ido_classifier"))

    def _select_single_nef(self, index: int):
        path, _selected = QFileDialog.getOpenFileName(
            self,
            "Please select a Classifier for ST-NEF",
            "",
            "ST-NEF Classifier Files (*.nef *.json *.xml);;All Files (*)",
        )
        if not path:
            return
        state = normalize_nef_state(self.tests[index].get("nef"))
        state["classifiers"] = [classifier_from_path(path, "ST-NEF")]
        self.tests[index]["nef"] = state
        self.tests[index]["status"] = "Incomplete"
        self.changed = True
        self._rebuild_matrix()

    def _select_ido(self, index: int):
        self.current_test = index
        self._refresh_current_test()
        self._ido_setup()

    def _select_dbb(self, index: int):
        path, _selected = QFileDialog.getOpenFileName(
            self,
            "Please select a DBB Classifier",
            "",
            "DBB Classifier Files (*.dbb *.json *.xml);;All Files (*)",
        )
        if not path:
            return
        self.tests[index]["dbb_classifier"] = {
            "name": Path(path).stem,
            "path": path,
        }
        self.tests[index]["status"] = "Incomplete"
        self.changed = True
        self._rebuild_matrix()

    def _view_nef(self, index: int):
        self.current_test = index
        self._refresh_current_test()
        self._nef_setup()

    def _view_ido(self, index: int):
        self.current_test = index
        self._refresh_current_test()
        classifier = self.tests[index].get("ido_classifier") or {}
        QMessageBox.information(
            self,
            "iDO Classifier",
            f"Name: {classifier.get('name', '-') }\n"
            f"Orientation: {classifier.get('orientation', '-') }\n"
            f"Feature Vector Version: {classifier.get('feature_vector_version', '-') }\n"
            f"Rough Code: {classifier.get('rough_code', '-') }",
        )

    def _set_value(self, index: int, key: str, value):
        if self._loading:
            return
        target = self.tests[index]["inspection_optics"] if key in self.tests[index]["inspection_optics"] else self.tests[index]
        target[key] = value
        if key in {"run_ido", "run_unsupervised_grouping"} and value:
            self.tests[index]["save_feature_vectors"] = True
        elif (
            key == "save_feature_vectors"
            and not value
            and (
                self.tests[index].get("run_ido")
                or self.tests[index].get("run_unsupervised_grouping")
            )
        ):
            self.tests[index]["save_feature_vectors"] = True
        if key in {"pixel_size", "incidence_angle"}:
            pixel_size = self.tests[index]["inspection_optics"].get("pixel_size", "SL815")
            incidence_angle = self.tests[index]["inspection_optics"].get(
                "incidence_angle",
                "Oblique",
            )
            for channel_index, channel in enumerate(self.tests[index]["channels"]):
                if channel.get("iris") not in iris_options(
                    pixel_size,
                    channel_index,
                    incidence_angle,
                ):
                    channel["iris"] = "OPEN"
            self._invalidate_nanopoint(index, all_data=key == "pixel_size")
            self._invalidate_np_image_care_areas(index)
        elif key in {
            "sample_rate",
            "incident_polarization",
            "speed",
            "laser_power_density",
        }:
            self._invalidate_nanopoint(index, all_data=False)
            self._invalidate_np_image_care_areas(index)
        if optics_change_invalidates_fourier(key):
            self.tests[index]["light_trained"] = False
            self._invalidate_fourier(index)
        if key == "focus_mode":
            self.tests[index]["light_trained"] = False
            state = normalized_light_training_state(
                self.tests[index].get("light_training")
            )
            if value != "Active Die":
                state["active_regions_enabled"] = False
            state["trained"] = False
            self.tests[index]["light_training"] = state
        self.tests[index]["status"] = "Incomplete"
        self.changed = True
        if key in {"pixel_size", "incidence_angle"} and index == self.current_test:
            self._populate_channels()
        if key == "name":
            self._rebuild_matrix()
        elif key in {"run_ido", "run_unsupervised_grouping", "save_feature_vectors"}:
            self._rebuild_matrix()

    def _change_mode(self, index: int, mode: str, combo: QComboBox):
        if self._loading or mode == self.tests[index].get("mode"):
            return
        if mode == "No Test" and self.tests[index].get("mode") != "No Test":
            answer = QMessageBox.question(
                self,
                "Delete Test",
                "Changing Mode to No Test permanently deletes this test setup. Continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                combo.blockSignals(True)
                combo.setCurrentText(self.tests[index]["mode"])
                combo.blockSignals(False)
                return
        replacement = default_test(index + 1, self.wafer_type, self.wafer_orientation)
        replacement["mode"] = mode
        replacement["status"] = "Undefined" if mode == "No Test" else "Incomplete"
        self.tests[index] = replacement
        self.changed = True
        self._rebuild_matrix()

    def _change_orientation(self, index: int, orientation: str, combo: QComboBox):
        previous = self.tests[index].get("orientation", self.wafer_orientation)
        if self._loading or orientation == previous:
            return
        dialog = ChangeTestOrientationDialog(previous, orientation, self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result != QDialog.Accepted:
            combo.blockSignals(True)
            combo.setCurrentText(previous)
            combo.blockSignals(False)
            return
        self.tests[index]["orientation"] = orientation
        self.tests[index]["light_trained"] = False
        self._invalidate_fourier(index)
        self._invalidate_nanopoint(index, all_data=True)
        self._invalidate_np_image_care_areas(index, delete=True)
        self.tests[index]["rotate_wafer"] = dialog.rotate_wafer
        if dialog.rotate_wafer:
            self.stage_orientation = orientation
            self.stage_rotation_performed = True
        self.tests[index]["status"] = "Incomplete"
        self.changed = True

    def _select_test(self, visible_index: int):
        if not getattr(self, "visible_indexes", None):
            return
        visible_index = min(visible_index, len(self.visible_indexes) - 1)
        self.current_test = self.visible_indexes[visible_index]
        self._refresh_current_test()

    def _refresh_current_test(self):
        test = self.tests[self.current_test]
        self.current_label.setText(f"Current Test:  {test.get('name', f'Test {self.current_test + 1}')}")
        self.result_test.blockSignals(True)
        self.result_test.clear()
        self.result_test.addItems([item.get("name", f"Test {index + 1}") for index, item in enumerate(self.tests)])
        self.result_test.setCurrentIndex(self.current_test)
        self.result_test.blockSignals(False)
        self._populate_channels()
        self._refresh_module_buttons()

    def _refresh_module_buttons(self):
        if not hasattr(self, "module_buttons") or not self.tests:
            return
        test = self.tests[self.current_test]
        test_defined = test.get("mode") != "No Test"
        care_ready = (
            test_defined
            and self.wafer_type != "Blank"
            and self.wafer_loaded
            and self.wafer_aligned
            and self.wafer_geometry_defined
        )
        care_button = self.module_buttons["Care Areas"]
        care_button.setEnabled(True)
        care_button.setToolTip(
            "" if care_ready else "Load and align a patterned wafer with defined die geometry first."
        )
        nanopoint_ready = (
            test_defined
            and self.wafer_type != "Blank"
            and self.wafer_loaded
            and self.wafer_aligned
            and self.wafer_geometry_defined
            and bool(test.get("light_trained"))
        )
        nanopoint_button = self.module_buttons["NP Image\nTemplates"]
        nanopoint_button.setEnabled(True)
        nanopoint_button.setToolTip(
            "" if nanopoint_ready else "Define the test, load and align a patterned wafer, define Premap, and complete Light Training first."
        )

    def _populate_channels(self):
        self._loading = True
        labels = ["Enabled", "Polarization", "Light Level", "IRIS", "Imaging Mode", "Use Fourier Filter"]
        self.channel_table.clear()
        self.channel_table.setHorizontalHeaderLabels([""] + [channel["name"] for channel in self.tests[self.current_test]["channels"]])
        for row, label in enumerate(labels):
            item = QTableWidgetItem(label)
            item.setBackground(QColor("#d5d2ca"))
            self.channel_table.setItem(row, 0, item)
        for column, channel in enumerate(self.tests[self.current_test]["channels"], start=1):
            self.channel_table.setCellWidget(0, column, self._channel_check(column - 1, "enabled", channel["enabled"]))
            self.channel_table.setCellWidget(1, column, self._channel_combo(column - 1, "polarization", ["None", "P-POL", "S-POL", "C-POL"], channel["polarization"]))
            light = QDoubleSpinBox()
            light.setRange(8.0, 200.0)
            light.setDecimals(2)
            light.setValue(float(channel["light_level"]))
            light.valueChanged.connect(lambda value, idx=column - 1: self._set_channel(idx, "light_level", value))
            self.channel_table.setCellWidget(2, column, light)
            pixel = self.tests[self.current_test]["inspection_optics"].get("pixel_size", "SL815")
            angle = self.tests[self.current_test]["inspection_optics"].get(
                "incidence_angle",
                "Oblique",
            )
            self.channel_table.setCellWidget(
                3,
                column,
                self._channel_combo(
                    column - 1,
                    "iris",
                    iris_options(pixel, column - 1, angle),
                    channel["iris"],
                ),
            )
            self.channel_table.setCellWidget(4, column, self._channel_combo(column - 1, "imaging_mode", ["DoubleDarkField", "DarkField", "BrightField"], channel["imaging_mode"]))
            fourier = self._channel_check(column - 1, "use_fourier_filter", channel["use_fourier_filter"])
            fourier.setToolTip(
                "When selected on an enabled channel, complete Fourier Filter Training before Light Training."
            )
            self.channel_table.setCellWidget(5, column, fourier)
        self._loading = False

    def _channel_check(self, channel_index: int, key: str, value: bool) -> QCheckBox:
        box = QCheckBox()
        box.setChecked(bool(value))
        box.toggled.connect(lambda checked, idx=channel_index, field=key: self._set_channel(idx, field, checked))
        return box

    def _channel_combo(self, channel_index: int, key: str, values: list[str], value: str) -> QComboBox:
        combo = QComboBox()
        combo.addItems(values)
        combo.setCurrentText(value)
        combo.currentTextChanged.connect(lambda text, idx=channel_index, field=key: self._set_channel(idx, field, text))
        return combo

    def _set_channel(self, channel_index: int, key: str, value):
        if self._loading:
            return
        channel = self.tests[self.current_test]["channels"][channel_index]
        previous = channel.get(key)
        channel[key] = value
        if (
            key == "use_fourier_filter"
            and bool(value)
            and value != previous
            and not self.tests[self.current_test].get("fourier_trained")
        ):
            self.tests[self.current_test]["light_trained"] = False
        if optics_change_invalidates_fourier(key) and value != previous:
            self.tests[self.current_test]["light_trained"] = False
            self._invalidate_fourier(self.current_test)
        if key in {"iris", "imaging_mode", "polarization"} and value != previous:
            self._invalidate_nanopoint(self.current_test, all_data=False)
            self._invalidate_np_image_care_areas(self.current_test)
        self.tests[self.current_test]["status"] = "Incomplete"
        self.changed = True

    def _nef_setup(self):
        test = self.tests[self.current_test]
        dialog = NuisanceFilterSetupDialog(test.get("nef"), self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result != QDialog.Accepted or dialog.result_state is None:
            return
        test["nef"] = dialog.result_state
        test["run_nef"] = bool(dialog.result_state.get("classifiers"))
        test["status"] = "Incomplete"
        self.changed = True
        self._rebuild_matrix()

    def _ido_setup(self):
        test = self.tests[self.current_test]
        dialog = IdoClassifierDialog(
            test.get("ido_classifier"),
            test.get("orientation", ""),
            test.get("feature_vector_version", "3.0A"),
            self,
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result != QDialog.Accepted or dialog.result_classifier is None:
            return
        test["ido_classifier"] = deepcopy(dialog.result_classifier)
        test["run_ido"] = True
        test["save_feature_vectors"] = True
        test["status"] = "Incomplete"
        self.changed = True
        self._rebuild_matrix()

    def _nanopoint_templates(self):
        self._refresh_external_wafer_context()
        test = self.tests[self.current_test]
        if test.get("mode") == "No Test":
            QMessageBox.warning(
                self,
                "NanoPoint Image Templates",
                "Define the current test before creating templates.",
            )
            return
        if not (
            self.wafer_type != "Blank"
            and self.wafer_loaded
            and self.wafer_aligned
            and self.wafer_geometry_defined
            and test.get("light_trained")
        ):
            QMessageBox.warning(
                self,
                "NanoPoint Image Templates",
                "Load and align a patterned wafer, define Premap, and complete Light Level Training before setting up NanoPoint templates.",
            )
            return
        care_names = [
            group.get("name", "")
            for group in normalized_care_area_state(test.get("care_areas"))["groups"]
            if group.get("kind") != "DCA"
        ]
        dialog = NanoPointImageTemplatesDialog(
            test.get("nano_point_templates"),
            care_area_names=care_names,
            defect_data=self.defect_data,
            wafer_loaded=self.wafer_loaded,
            wafer_aligned=self.wafer_aligned,
            light_trained=bool(test.get("light_trained")),
            premap_defined=self.wafer_geometry_defined,
            test_name=test.get("name", f"Test {self.current_test + 1}"),
            parent=self,
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted and dialog.result_state is not None:
            test["nano_point_templates"] = deepcopy(dialog.result_state)
            test["status"] = "Incomplete"
            self.changed = True

    def _add_test(self):
        if len(self.tests) >= 50:
            QMessageBox.warning(self, "Add Test", "The recipe already contains the maximum of 50 tests.")
            return
        if len(self.tests) == 1 and self.tests[0].get("mode") == "No Test":
            self.tests[0] = default_test(1, self.wafer_type, self.wafer_orientation)
            self.current_test = 0
        else:
            self.tests.append(default_test(len(self.tests) + 1, self.wafer_type, self.wafer_orientation))
            self.current_test = len(self.tests) - 1
            self.tests[self.current_test]["sample_plan"]["master_plans"] = (
                self._shared_master_plans()
            )
        self.changed = True
        self._rebuild_matrix()

    def _show_test_menu(self, position):
        menu = QMenu(self)
        copy_action = menu.addAction("Copy Test")
        paste_action = menu.addAction("Paste Test")
        paste_action.setEnabled(self.test_clipboard is not None)
        menu.addSeparator()
        copy_plan_action = menu.addAction("Copy Sample Plan")
        paste_plan_action = menu.addAction("Paste Sample Plan")
        paste_plan_action.setEnabled(self.sample_plan_clipboard is not None)
        delete_action = menu.addAction("Delete Test")
        action = menu.exec(self.matrix.viewport().mapToGlobal(position)) if hasattr(menu, "exec") else menu.exec_(self.matrix.viewport().mapToGlobal(position))
        if action == copy_action:
            self.copy_current_test()
        elif action == paste_action and self.test_clipboard is not None:
            self.paste_current_test()
        elif action == copy_plan_action:
            self.copy_current_sample_plan()
        elif action == paste_plan_action and self.sample_plan_clipboard is not None:
            self.paste_current_sample_plan()
        elif action == delete_action:
            self._delete_test()

    def copy_current_test(self):
        self.test_clipboard = deepcopy(self.tests[self.current_test])
        return True

    def paste_current_test(self):
        if self.test_clipboard is None:
            QMessageBox.information(self, "Paste Test", "Copy a test before pasting.")
            return False
        answer = QMessageBox.question(
            self,
            "Paste Test",
            "Replace the selected test with the copied parameters?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if answer != QMessageBox.Yes:
            return False
        name = self.tests[self.current_test].get("name", f"Test {self.current_test + 1}")
        self.tests[self.current_test] = deepcopy(self.test_clipboard)
        self.tests[self.current_test]["name"] = name
        self.changed = True
        self._rebuild_matrix()
        return True

    def copy_current_sample_plan(self):
        self.sample_plan_clipboard = deepcopy(
            self.tests[self.current_test].get("sample_plan") or default_sample_plan()
        )
        return True

    def paste_current_sample_plan(self):
        if self.sample_plan_clipboard is None:
            QMessageBox.information(
                self, "Paste Sample Plan", "Copy a sample plan before pasting."
            )
            return False
        masters = self._shared_master_plans()
        plan = normalized_sample_plan(self.sample_plan_clipboard)
        plan["master_plans"] = masters
        self.tests[self.current_test]["sample_plan"] = plan
        self.tests[self.current_test]["coverage"] = plan.get("coverage", 100)
        self.tests[self.current_test]["status"] = "Incomplete"
        self.changed = True
        self._rebuild_matrix()
        return True

    def _delete_test(self):
        answer = QMessageBox.question(self, "Delete Test", "Permanently delete the selected test?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        if len(self.tests) == 1:
            self.tests[0] = default_test(1, self.wafer_type, self.wafer_orientation)
            self.tests[0]["mode"] = "No Test"
            self.tests[0]["status"] = "Undefined"
        else:
            self.tests.pop(self.current_test)
            self.current_test = min(self.current_test, len(self.tests) - 1)
        self.changed = True
        self._rebuild_matrix()

    def _retrain(self):
        self._refresh_external_wafer_context()
        if not (self.wafer_loaded and self.wafer_aligned):
            QMessageBox.warning(
                self,
                "Retrain",
                "Load and align a wafer before retraining tests.",
            )
            return
        candidates = (
            range(len(self.tests))
            if self.test_selection.currentText() == "All Tests"
            else [self.current_test]
        )
        indexes = [
            index
            for index in candidates
            if self.tests[index].get("mode") != "No Test"
            and not (
                self.do_not_retrain_valid.isChecked()
                and self.tests[index].get("status") == "Valid"
            )
        ]
        if not indexes:
            QMessageBox.information(self, "Retrain", "No defined tests require retraining.")
            return
        if self.retrain_fourier.isChecked():
            setup_errors = []
            for index in indexes:
                errors = validate_fourier_state(self.tests[index].get("fourier"))
                if errors:
                    name = self.tests[index].get("name", f"Test {index + 1}")
                    setup_errors.append(f"{name}: {errors[0]}")
            if setup_errors:
                QMessageBox.warning(
                    self,
                    "Retrain",
                    "Open Fourier Filter Training and correct the setup first.\n"
                    + "\n".join(setup_errors),
                )
                return
        for index in indexes:
            test = self.tests[index]
            if self.retrain_light.isChecked():
                light = normalized_light_training_state(test.get("light_training"))
                care_state = normalized_care_area_state(test.get("care_areas"))
                errors = validate_light_training_state(
                    light,
                    test.get("focus_mode", "Median Die"),
                    care_state,
                    self.die_size_um,
                )
                if errors:
                    QMessageBox.warning(
                        self,
                        "Retrain",
                        f"{test.get('name', f'Test {index + 1}')}: {errors[0]}",
                    )
                    return
                light["trained"] = True
                test["light_training"] = light
                test["light_trained"] = True
            if self.retrain_fourier.isChecked():
                test["fourier_trained"] = True
                test["fourier"] = normalize_fourier_state(test.get("fourier"))
                test["fourier"]["trained"] = True
            test["status"] = "Incomplete"
        self.changed = True
        self._populate_channels()
        self._refresh_module_buttons()
        QMessageBox.information(
            self,
            "Retrain",
            f"Training data refreshed for {len(indexes)} test(s).",
        )

    def _fourier_training(self):
        test = self.tests[self.current_test]
        if test.get("mode") == "No Test":
            QMessageBox.warning(self, "Fourier Filter Training", "Define the current test before training the Fourier Filter.")
            return
        dialog = FourierFilterTrainingDialog(
            test.get("fourier"),
            incidence_angle=test.get("inspection_optics", {}).get("incidence_angle", "Oblique"),
            test_name=test.get("name", f"Test {self.current_test + 1}"),
            parent=self,
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted and dialog.result_state is not None:
            test["fourier"] = deepcopy(dialog.result_state)
            test["fourier_trained"] = bool(dialog.result_state.get("trained"))
            test["status"] = "Incomplete"
            self.changed = True
            self._populate_channels()

    def _invalidate_fourier(self, index: int):
        test = self.tests[index]
        test["fourier_trained"] = False
        test["fourier"] = normalize_fourier_state(test.get("fourier"))
        test["fourier"]["trained"] = False
        test["fourier"]["analysis_valid"] = False
        for channel in test.get("channels", []):
            channel["use_fourier_filter"] = False

    def _invalidate_nanopoint(self, index: int, *, all_data: bool):
        state = normalize_nanopoint_state(
            self.tests[index].get("nano_point_templates")
        )
        if not state["templates"]:
            return
        state["images_grabbed"] = False
        if all_data:
            state["valid"] = False
        self.tests[index]["nano_point_templates"] = state

    def _invalidate_np_image_care_areas(self, index: int, *, delete: bool = False):
        state = normalized_care_area_state(self.tests[index].get("care_areas"))
        image_groups = [
            group for group in state["groups"]
            if group.get("kind") == "NP Image Care Area"
        ]
        if not image_groups:
            return
        if delete:
            state["groups"] = [
                group for group in state["groups"]
                if group.get("kind") != "NP Image Care Area"
            ]
        else:
            for group in image_groups:
                group["status"] = "Invalid - Test Optics changed; rescan required"
                group["registered"] = False
                group["verified"] = False
                group["requires_rescan"] = True
        self.tests[index]["care_areas"] = state

    def _sample_plan(self):
        test = self.tests[self.current_test]
        if test.get("mode") == "No Test":
            QMessageBox.warning(self, "Sample Plan", "Define the current test before editing its sample plan.")
            return
        plan = normalized_sample_plan(test.get("sample_plan"))
        plan["master_plans"] = self._shared_master_plans()
        dialog = SamplePlanDialog(
            plan,
            inner_die_defined=self.inner_die_defined,
            parent=self,
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted and dialog.result_state is not None:
            test["sample_plan"] = deepcopy(dialog.result_state)
            masters = deepcopy(dialog.result_state.get("master_plans", {}))
            for other in self.tests:
                other_plan = normalized_sample_plan(other.get("sample_plan"))
                other_plan["master_plans"] = deepcopy(masters)
                other["sample_plan"] = other_plan
            test["coverage"] = dialog.result_state.get("coverage", test.get("coverage", 100))
            test["status"] = "Incomplete"
            self.changed = True
            self._rebuild_matrix()

    def _shared_master_plans(self):
        for test in self.tests:
            plans = (test.get("sample_plan") or {}).get("master_plans")
            if plans:
                return deepcopy(plans)
        return {}

    def _care_areas(self):
        self._refresh_external_wafer_context()
        test = self.tests[self.current_test]
        if (
            self.wafer_type == "Blank"
            or not self.wafer_loaded
            or not self.wafer_aligned
            or not self.wafer_geometry_defined
        ):
            QMessageBox.warning(
                self,
                "Care Areas",
                "Load and align a patterned wafer and define die geometry before editing Care Areas.",
            )
            return
        if test.get("mode") == "No Test":
            QMessageBox.warning(self, "Care Areas", "Define the current test before editing Care Areas.")
            return
        same_orientation = [
            item for item in self.tests
            if item.get("mode") != "No Test"
            and item.get("orientation") == test.get("orientation")
        ]
        care_area_state = normalized_care_area_state(test.get("care_areas"))
        care_area_state["die_size_um"] = list(self.die_size_um)
        dialog = CareAreasDialog(
            care_area_state,
            can_overwrite=len(same_orientation) > 1,
            test_mode=test.get("mode", "Random"),
            defect_data=self.defect_data,
            wafer_aligned=self.wafer_aligned,
            test_name=test.get("name", "Test 1"),
            parent=self,
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result != QDialog.Accepted or dialog.result_state is None:
            return
        test["care_areas"] = deepcopy(dialog.result_state)
        if dialog.overwrite_all:
            for other in self.tests:
                if other is test or other.get("orientation") != test.get("orientation"):
                    continue
                target = normalized_care_area_state(other.get("care_areas"))
                source = dialog.result_state
                previous = {item["name"]: item for item in target["thresholds"]}
                target["groups"] = deepcopy(source["groups"])
                target["thresholds"] = [
                    deepcopy(previous.get(item["name"], item))
                    for item in source["thresholds"]
                ]
                other["care_areas"] = target
                other["status"] = "Incomplete"
        test["status"] = "Incomplete"
        self.changed = True

    def _light_training(self):
        test = self.tests[self.current_test]
        care_state = normalized_care_area_state(test.get("care_areas"))
        if not care_state["groups"]:
            QMessageBox.warning(
                self,
                "Light Training",
                "Define at least one Care Area before Light Training.",
            )
            return
        uses_fourier = any(
            channel.get("enabled") and channel.get("use_fourier_filter")
            for channel in test.get("channels", [])
        )
        if uses_fourier and not test.get("fourier_trained"):
            QMessageBox.warning(
                self,
                "Light Training",
                "Fourier Filter is enabled for this test. Complete Fourier Filter Training before Light Training.",
            )
            return
        dialog = LightTrainingDialog(
            test.get("light_training"),
            test_name=test.get("name", f"Test {self.current_test + 1}"),
            focus_mode=test.get("focus_mode", "Median Die"),
            care_areas=care_state,
            die_size_um=self.die_size_um,
            parent=self,
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result != QDialog.Accepted or dialog.result_state is None:
            return
        test["light_training"] = deepcopy(dialog.result_state)
        test["light_trained"] = bool(dialog.result_state.get("trained"))
        for index, trained_channel in enumerate(dialog.result_state.get("channels", [])):
            if index < len(test["channels"]):
                test["channels"][index]["light_level"] = trained_channel["light_level"]
                test["channels"][index]["exposure"] = trained_channel["exposure"]
                test["channels"][index]["edr"] = trained_channel["edr"]
        test["status"] = "Incomplete"
        self.changed = True
        self._populate_channels()
        self._refresh_module_buttons()

    def _segmentation(self):
        self._refresh_external_wafer_context()
        test = self.tests[self.current_test]
        care_state = normalized_care_area_state(test.get("care_areas"))
        if not care_state["groups"]:
            QMessageBox.warning(self, "Segmentation", "Define Care Areas before Segmentation.")
            return
        if not test.get("light_trained"):
            QMessageBox.warning(
                self,
                "Segmentation",
                "Complete Light Training before Segmentation.",
            )
            return
        uses_fourier = any(
            channel.get("enabled") and channel.get("use_fourier_filter")
            for channel in test.get("channels", [])
        )
        if uses_fourier and not test.get("fourier_trained"):
            QMessageBox.warning(
                self,
                "Segmentation",
                "Fourier Filter is enabled for this test. Complete its training before Segmentation.",
            )
            return
        eligible_groups = [
            group for group in care_state["groups"]
            if group.get("enabled", True)
            and group.get("kind") != "DCA"
            and "Page Break" not in group.get("kind", "")
        ]
        dialog = SegmentationDialog(
            test.get("segmentation"),
            care_groups=eligible_groups,
            wafer_ready=self.wafer_loaded and self.wafer_aligned,
            parent=self,
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result != QDialog.Accepted or dialog.result_state is None:
            return
        test["segmentation"] = deepcopy(dialog.result_state)
        test["status"] = "Incomplete"
        self.changed = True
        self._rebuild_matrix()

    def _sensitivity_setup(self):
        test = self.tests[self.current_test]
        care_state = normalized_care_area_state(test.get("care_areas"))
        region_names = [item["name"] for item in care_state["thresholds"]]
        dialog = SensitivityDialog(
            test.get("sensitivity"),
            region_names,
            self,
            feature_vector_version=test.get("feature_vector_version", "3.0A"),
            segmentation_state=test.get("segmentation"),
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result != QDialog.Accepted or dialog.result_state is None:
            return
        test["sensitivity"] = deepcopy(dialog.result_state)
        if dialog.result_segmentation_state is not None:
            test["segmentation"] = deepcopy(dialog.result_segmentation_state)
        test["feature_vector_version"] = dialog.result_feature_vector_version
        test["status"] = "Incomplete"
        self.changed = True
        self._rebuild_matrix()

    def _finish(self):
        for test in self.tests:
            errors = validate_test(test)
            test["validation_errors"] = errors
            test["status"] = "Valid" if not errors else "Incomplete"
        self.result_tests = deepcopy(self.tests)
        self.accept()


class ChangeTestOrientationDialog(QDialog):
    def __init__(self, previous: str, requested: str, parent=None):
        super().__init__(parent)
        self.rotate_wafer = False
        self.setWindowTitle("Change Test Orientation")
        self.setFixedSize(500, 240)
        self.setStyleSheet(
            "QDialog { background: #efede2; font-family: Arial; font-size: 10px; }"
            "QPushButton { min-height: 26px; padding: 2px 10px; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 22, 26, 18)
        message = QLabel(
            f"Change test orientation from {previous} to {requested}?\n"
            "Light and Fourier Filter data for this test must be retrained."
        )
        message.setWordWrap(True)
        layout.addWidget(message)
        layout.addStretch(1)
        buttons = QHBoxLayout()
        rotate = QPushButton("Rotate Wafer & Continue")
        rotate.clicked.connect(lambda: self._accept(True))
        keep = QPushButton("Don't Rotate Wafer & Continue")
        keep.clicked.connect(lambda: self._accept(False))
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(rotate)
        buttons.addWidget(keep)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)

    def _accept(self, rotate: bool):
        self.rotate_wafer = rotate
        self.accept()

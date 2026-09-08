from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from ...qt_compat import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


def default_dbb_state():
    return {
        "server_status": "Active (simulated)",
        "rdf_file": "",
        "rdf_device": "",
        "inspection_layer": "",
        "process_layers": ["Design", "Metal"],
        "strategy": "SemiAutomatic A2D",
        "kernel_size": 64,
        "search_x_um": 25.0,
        "search_y_um": 25.0,
        "use_optics": "Default",
        "design_pitch_width_um": 0.0,
        "design_pitch_height_um": 0.0,
        "offset_x_um": 0.0,
        "offset_y_um": 0.0,
        "scale_x": 1.0,
        "scale_y": 1.0,
        "rdf_sites": [],
        "low_mag_sites": [],
        "high_mag_sites": [],
        "registration_verified": False,
        "registered": False,
        "enabled": False,
        "design_clip_size_nm": 1000,
        "use_defect_size": True,
        "exclude_array_regions": False,
        "dbc_enabled": False,
        "dbc_library": "",
        "dbg_enabled": False,
        "dbg_algorithm": "DBG2 (Recommended)",
        "dbg_similarity": 25,
        "dbg_seed_window_nm": 400,
        "dbg_stop_group_count": 1500,
        "systematic_threshold_mode": "Defect Count",
        "systematic_threshold": 10.0,
        "consider_rotated": False,
        "consider_flipped": False,
        "dbg_filter_enabled": False,
        "dbg_filter_attribute": "Pattern Density",
        "dbg_filter_operator": ">=",
        "dbg_filter_value": 0.0,
        "supergrouping_enabled": False,
        "supergroup_similarity": 30,
        "supergroup_time_limit": "00:30:00",
        "transfer_clip_layer": "Design",
        "transfer_clip_images": False,
        "transfer_clip_limit": 200,
        "throughput_skip_dbb": True,
        "throughput_skip_attributes": False,
        "dci_enabled": False,
        "pci_enabled": False,
        "design_attributes_enabled": False,
        "min_line_space": False,
        "pattern_density_1": False,
        "pattern_density_2": False,
        "overlap_ratio_1": False,
        "overlap_ratio_2": False,
        "sampling": {
            "maximum": 100,
            "dbc_enabled": False,
            "dbc_size": 0,
            "filter_dbc_nuisance": True,
            "dbc_bin_priority": "Count",
            "dbc_scheme": "Random",
            "dbg_systematic_enabled": False,
            "dbg_systematic_bins": 0,
            "dbg_systematic_size": 0,
            "dbg_systematic_priority": "Random",
            "dbg_systematic_scheme": "Prioritized by DCI",
            "dbg_random_enabled": False,
            "dbg_random_scheme": "Prioritized by Pattern Density",
            "limits_enabled": False,
            "max_per_die": 3,
            "max_per_cluster": 5,
            "max_cluster_percent": 10,
            "minimum_defect_size": 0.0,
            "maximum_defect_size": 500000000.0,
            "adders_only": False,
        },
        "dbc_examples": [],
        "dbc_bins": [],
    }


def normalized_dbb_state(value=None):
    result = default_dbb_state()
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "sampling" and isinstance(item, dict):
                result["sampling"].update(deepcopy(item))
            else:
                result[key] = deepcopy(item)
    result["kernel_size"] = max(1, min(4096, int(result.get("kernel_size", 64))))
    result["design_clip_size_nm"] = max(1, min(100000, int(result.get("design_clip_size_nm", 1000))))
    result["dbg_similarity"] = max(1, min(100, int(result.get("dbg_similarity", 25))))
    result["dbg_seed_window_nm"] = max(100, min(1000, int(result.get("dbg_seed_window_nm", 400))))
    result["dbg_stop_group_count"] = max(1, min(25000, int(result.get("dbg_stop_group_count", 1500))))
    result["systematic_threshold"] = max(0.0, float(result.get("systematic_threshold", 10.0)))
    result["dbg_filter_value"] = float(result.get("dbg_filter_value", 0.0))
    result["supergroup_similarity"] = max(1, min(100, int(result.get("supergroup_similarity", 30))))
    result["transfer_clip_limit"] = 200
    sampling = result["sampling"]
    sampling["maximum"] = max(0, min(65000, int(sampling.get("maximum", 100))))
    sampling["dbc_size"] = max(0, min(65000, int(sampling.get("dbc_size", 0))))
    sampling["dbg_systematic_bins"] = max(0, min(65000, int(sampling.get("dbg_systematic_bins", 0))))
    sampling["dbg_systematic_size"] = max(0, min(65000, int(sampling.get("dbg_systematic_size", 0))))
    sampling["max_per_die"] = max(1, min(65000, int(sampling.get("max_per_die", 3))))
    sampling["max_per_cluster"] = max(2, min(65000, int(sampling.get("max_per_cluster", 5))))
    sampling["max_cluster_percent"] = max(0, min(100, int(sampling.get("max_cluster_percent", 10))))
    sampling["minimum_defect_size"] = max(0.0, min(500000000.0, float(sampling.get("minimum_defect_size", 0.0))))
    sampling["maximum_defect_size"] = max(0.0, min(500000000.0, float(sampling.get("maximum_defect_size", 500000000.0))))
    return result


def validate_design_registration(state):
    state = normalized_dbb_state(state)
    errors = []
    if state["server_status"] != "Active (simulated)":
        errors.append("DBB Design Services must be active")
    if not str(state["rdf_file"]).strip():
        errors.append("Select a Reticle Design File (RDF)")
    if not str(state["inspection_layer"]).strip():
        errors.append("Select an inspection layer")
    if state["strategy"] == "Design Offsets and Scales":
        if float(state["scale_x"]) <= 0 or float(state["scale_y"]) <= 0:
            errors.append("Design scales must be greater than zero")
    else:
        minimum = 1 if state["strategy"] == "SemiAutomatic A2D" and state["design_pitch_width_um"] > 0 and state["design_pitch_height_um"] > 0 else 2
        if len(state["rdf_sites"]) < minimum:
            errors.append(f"Mark {minimum} RDF registration site(s)")
        if len(state["low_mag_sites"]) < minimum:
            errors.append(f"Mark {minimum} low-magnification wafer site(s)")
        if len(state["high_mag_sites"]) < minimum:
            errors.append(f"Mark {minimum} high-magnification wafer site(s)")
        if minimum == 2:
            first, second = state["low_mag_sites"][:2] if len(state["low_mag_sites"]) >= 2 else ((0, 0), (0, 0))
            if abs(second[0] - first[0]) + abs(second[1] - first[1]) < 100:
                errors.append("Registration sites must be far apart diagonally")
    if not state["registration_verified"]:
        errors.append("Verify registration with Lock and Overlay before finishing")
    return errors


def validate_dbb_setup(state):
    state = normalized_dbb_state(state)
    if not state["enabled"]:
        return []
    errors = []
    if not state["registered"]:
        errors.append("Complete Design Registration before enabling DBB")
    if state["dbc_enabled"] and not str(state["dbc_library"]).strip():
        errors.append("Select a DBC Library")
    if state["dbg_enabled"] and not state["process_layers"]:
        errors.append("Select at least one process layer for DBG")
    if state["dbg_filter_enabled"] and not state["dbg_enabled"]:
        errors.append("Enable DBG before applying a DBB filter-out rule")
    if state["supergrouping_enabled"] and (not state["dbg_enabled"] or state["dbg_algorithm"] != "DBG1"):
        errors.append("Supergrouping is available only when DBG1 is enabled")
    sampling = state["sampling"]
    allocated = sampling["dbc_size"] + sampling["dbg_systematic_size"]
    if allocated > sampling["maximum"]:
        errors.append("DBB sampling allocations exceed the maximum sample size")
    if sampling["minimum_defect_size"] > sampling["maximum_defect_size"]:
        errors.append("Minimum defect size cannot exceed maximum defect size")
    return errors


class DesignRegistrationDialog(QDialog):
    def __init__(self, state=None, recipe_device="", parent=None):
        super().__init__(parent)
        self.state = normalized_dbb_state(state)
        self.result_state = None
        self.recipe_device = recipe_device
        self.setWindowTitle("Design Registration")
        self.resize(1000, 680)
        root = QVBoxLayout(self)
        status = QHBoxLayout()
        status.addWidget(QLabel("DBB IMC Server"))
        self.server = QComboBox()
        self.server.addItems(["Active (simulated)", "Inactive", "Service not Started"])
        self.server.setCurrentText(self.state["server_status"])
        status.addWidget(self.server)
        status.addStretch(1)
        root.addLayout(status)
        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)
        self._build_file_tab()
        self._build_sites_tab()
        footer = QHBoxLayout()
        footer.addStretch(1)
        finish = QPushButton("Finish")
        finish.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        footer.addWidget(finish)
        footer.addWidget(cancel)
        root.addLayout(footer)
        self.rdf_file.textChanged.connect(self._refresh_file_state)
        self._refresh_file_state()
        self._refresh_site_status()

    def _build_file_tab(self):
        page = QWidget()
        form = QGridLayout(page)
        self.rdf_file = QLineEdit(self.state["rdf_file"])
        self.rdf_file.setPlaceholderText("Selected RDF name or simulator path")
        self.rdf_device = QLineEdit(self.state["rdf_device"] or self.recipe_device)
        self.inspection_layer = QComboBox()
        self.inspection_layer.setEditable(True)
        self.inspection_layer.addItems(["", "Diffusion", "Poly", "Contact", "Metal1", "Via1", "Custom"])
        self.inspection_layer.setCurrentText(self.state["inspection_layer"])
        self.process_layers = QLineEdit(", ".join(self.state["process_layers"]))
        rows = (
            ("Reticle Design File", self.rdf_file),
            ("RDF Device", self.rdf_device),
            ("Inspection Layer", self.inspection_layer),
            ("Process Layers", self.process_layers),
        )
        for row, (label, control) in enumerate(rows):
            form.addWidget(QLabel(label), row, 0)
            form.addWidget(control, row, 1)
        note = QLabel("RDF content is represented as metadata only; no Design Services server is contacted.")
        note.setWordWrap(True)
        form.addWidget(note, len(rows), 0, 1, 2)
        form.setColumnStretch(1, 1)
        form.setRowStretch(len(rows) + 1, 1)
        self.tabs.addTab(page, "Design File")

    def _build_sites_tab(self):
        page = QWidget()
        root = QVBoxLayout(page)
        advanced = QGridLayout()
        self.strategy = QComboBox()
        self.strategy.addItems(["SemiAutomatic A2D", "Manual", "Design Offsets and Scales"])
        self.strategy.setCurrentText(self.state["strategy"])
        self.kernel = QSpinBox()
        self.kernel.setRange(1, 4096)
        self.kernel.setValue(self.state["kernel_size"])
        self.search_x = self._double(0, 10000, self.state["search_x_um"], 3)
        self.search_y = self._double(0, 10000, self.state["search_y_um"], 3)
        self.optics = QComboBox()
        self.optics.addItems(["Default", "Current"])
        self.optics.setCurrentText(self.state["use_optics"])
        self.pitch_width = self._double(0, 1000000, self.state["design_pitch_width_um"], 6)
        self.pitch_height = self._double(0, 1000000, self.state["design_pitch_height_um"], 6)
        self.offset_x = self._double(-1000000, 1000000, self.state["offset_x_um"], 6)
        self.offset_y = self._double(-1000000, 1000000, self.state["offset_y_um"], 6)
        self.scale_x = self._double(0.000001, 1000, self.state["scale_x"], 8)
        self.scale_y = self._double(0.000001, 1000, self.state["scale_y"], 8)
        rows = (
            ("A2D Strategy", self.strategy), ("Kernel Size", self.kernel),
            ("Search Range X (um)", self.search_x), ("Search Range Y (um)", self.search_y),
            ("Use Optics", self.optics), ("Design Reticle Pitch Width (um)", self.pitch_width),
            ("Design Reticle Pitch Height (um)", self.pitch_height), ("Offset X (um)", self.offset_x),
            ("Offset Y (um)", self.offset_y), ("Scale X", self.scale_x), ("Scale Y", self.scale_y),
        )
        for index, (label, control) in enumerate(rows):
            row, column = divmod(index, 2)
            advanced.addWidget(QLabel(label), row, column * 2)
            advanced.addWidget(control, row, column * 2 + 1)
        advanced.setColumnStretch(1, 1)
        advanced.setColumnStretch(3, 1)
        root.addLayout(advanced)
        mark = QHBoxLayout()
        self.mark_rdf = QPushButton("Mark RDF Site")
        self.mark_low = QPushButton("Mark Low Mag Site")
        self.mark_high = QPushButton("Mark High Mag Site")
        self.reset_sites = QPushButton("Reset Sites")
        self.verify = QPushButton("Lock + Overlay Verify")
        self.mark_rdf.clicked.connect(lambda: self._mark("rdf_sites"))
        self.mark_low.clicked.connect(lambda: self._mark("low_mag_sites"))
        self.mark_high.clicked.connect(lambda: self._mark("high_mag_sites"))
        self.reset_sites.clicked.connect(self._reset_sites)
        self.verify.clicked.connect(self._verify)
        for button in (self.mark_rdf, self.mark_low, self.mark_high, self.reset_sites, self.verify):
            mark.addWidget(button)
        root.addLayout(mark)
        self.site_status = QLabel()
        self.site_status.setWordWrap(True)
        root.addWidget(self.site_status)
        self.strategy.currentTextChanged.connect(self._strategy_changed)
        self.pitch_width.valueChanged.connect(self._refresh_site_status)
        self.pitch_height.valueChanged.connect(self._refresh_site_status)
        self._strategy_changed()
        root.addStretch(1)
        self.tabs.addTab(page, "Design Sites")

    @staticmethod
    def _double(minimum, maximum, value, decimals):
        control = QDoubleSpinBox()
        control.setRange(minimum, maximum)
        control.setDecimals(decimals)
        control.setValue(float(value))
        return control

    def _strategy_changed(self, *_args):
        offsets = self.strategy.currentText() == "Design Offsets and Scales"
        for control in (self.mark_rdf, self.mark_low, self.mark_high, self.pitch_width, self.pitch_height):
            control.setEnabled(not offsets)
        for control in (self.offset_x, self.offset_y, self.scale_x, self.scale_y):
            control.setEnabled(offsets)
        self._refresh_site_status()

    def _refresh_file_state(self, *_args):
        self.tabs.setTabEnabled(1, bool(self.rdf_file.text().strip()))

    def _required_site_count(self):
        if self.strategy.currentText() == "Design Offsets and Scales":
            return 0
        if (
            self.strategy.currentText() == "SemiAutomatic A2D"
            and self.pitch_width.value() > 0
            and self.pitch_height.value() > 0
        ):
            return 1
        return 2

    def _collect(self):
        state = normalized_dbb_state(self.state)
        state.update({
            "server_status": self.server.currentText(),
            "rdf_file": self.rdf_file.text().strip(),
            "rdf_device": self.rdf_device.text().strip(),
            "inspection_layer": self.inspection_layer.currentText().strip(),
            "process_layers": [item.strip() for item in self.process_layers.text().split(",") if item.strip()],
            "strategy": self.strategy.currentText(),
            "kernel_size": self.kernel.value(),
            "search_x_um": self.search_x.value(),
            "search_y_um": self.search_y.value(),
            "use_optics": self.optics.currentText(),
            "design_pitch_width_um": self.pitch_width.value(),
            "design_pitch_height_um": self.pitch_height.value(),
            "offset_x_um": self.offset_x.value(),
            "offset_y_um": self.offset_y.value(),
            "scale_x": self.scale_x.value(),
            "scale_y": self.scale_y.value(),
        })
        return state

    def _mark(self, key):
        if len(self.state[key]) >= 2:
            return
        index = len(self.state[key])
        self.state[key].append((100.0 + index * 500.0, 120.0 + index * 520.0))
        self.state["registration_verified"] = False
        self._refresh_site_status()

    def _reset_sites(self):
        for key in ("rdf_sites", "low_mag_sites", "high_mag_sites"):
            self.state[key] = []
        self.state["registration_verified"] = False
        self._refresh_site_status()

    def _verify(self):
        state = self._collect()
        state["registration_verified"] = True
        errors = [item for item in validate_design_registration(state) if "Verify registration" not in item]
        if errors:
            QMessageBox.warning(self, "Design Registration", "\n".join(errors))
            return
        self.state.update(state)
        self.state["registration_verified"] = True
        self._refresh_site_status()

    def _refresh_site_status(self):
        verified = "Verified" if self.state["registration_verified"] else "Not verified"
        required = self._required_site_count()
        self.site_status.setText(
            f"Required site sets: {required} | RDF sites: {len(self.state['rdf_sites'])}/{required} | "
            f"Low Mag: {len(self.state['low_mag_sites'])}/{required} | "
            f"High Mag: {len(self.state['high_mag_sites'])}/{required} | {verified}"
        )

    def _finish(self):
        state = self._collect()
        errors = validate_design_registration(state)
        if errors:
            QMessageBox.warning(self, "Design Registration", "\n".join(errors))
            return
        state["registered"] = True
        self.result_state = normalized_dbb_state(state)
        self.accept()


class DBBSetupDialog(QDialog):
    def __init__(self, state=None, parent=None):
        super().__init__(parent)
        self.state = normalized_dbb_state(state)
        self.result_state = None
        self.setWindowTitle("Design Based Binning Setup")
        self.resize(980, 700)
        root = QVBoxLayout(self)
        summary = QLabel(
            f"RDF: {self.state['rdf_file'] or '-'} | Layer: {self.state['inspection_layer'] or '-'} | "
            f"Registration: {'Verified' if self.state['registered'] else 'Incomplete'}"
        )
        root.addWidget(summary)
        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)
        self._build_general()
        self._build_dbg()
        self._build_attributes()
        self._build_sampling()
        footer = QHBoxLayout()
        footer.addStretch(1)
        ok = QPushButton("OK")
        ok.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        footer.addWidget(ok)
        footer.addWidget(cancel)
        root.addLayout(footer)

    def _build_general(self):
        page = QWidget()
        form = QGridLayout(page)
        self.enabled = QCheckBox("Design Based Binning")
        self.enabled.setChecked(self.state["enabled"])
        self.clip_size = QSpinBox()
        self.clip_size.setRange(1, 100000)
        self.clip_size.setValue(self.state["design_clip_size_nm"])
        self.use_defect_size = QCheckBox("Use Defect Size in EBB Calculation")
        self.use_defect_size.setChecked(self.state["use_defect_size"])
        self.exclude_array = QCheckBox("Exclude Defects from Array Regions")
        self.exclude_array.setChecked(self.state["exclude_array_regions"])
        self.dbc_enabled = QCheckBox("Enable Design Background Classification (DBC)")
        self.dbc_enabled.setChecked(self.state["dbc_enabled"])
        self.dbc_library = QLineEdit(self.state["dbc_library"])
        self.dbc_library.setPlaceholderText("DBC Library name")
        self.throughput = QCheckBox("Skip DBG and DBC on some defects to maintain throughput")
        self.throughput.setChecked(self.state["throughput_skip_dbb"])
        self.throughput_attributes = QCheckBox("Skip DCI, PCI and Design Attributes on some defects")
        self.throughput_attributes.setChecked(self.state["throughput_skip_attributes"])
        self.dbc_enabled.toggled.connect(self.dbc_library.setEnabled)
        self.dbc_library.setEnabled(self.dbc_enabled.isChecked())
        rows = (
            ("Enable", self.enabled), ("Design Clip Size (nm)", self.clip_size),
            ("EBB", self.use_defect_size), ("Array Regions", self.exclude_array),
            ("DBC", self.dbc_enabled), ("DBC Library", self.dbc_library),
            ("DBB Throughput", self.throughput), ("Attribute Throughput", self.throughput_attributes),
        )
        for row, (label, control) in enumerate(rows):
            form.addWidget(QLabel(label), row, 0)
            form.addWidget(control, row, 1)
        form.setColumnStretch(1, 1)
        form.setRowStretch(len(rows), 1)
        self.tabs.addTab(page, "General")

    def _build_dbg(self):
        page = QWidget()
        form = QGridLayout(page)
        self.dbg_enabled = QCheckBox("Enable Design Background Grouping (DBG)")
        self.dbg_enabled.setChecked(self.state["dbg_enabled"])
        self.dbg_algorithm = QComboBox()
        self.dbg_algorithm.addItems(["DBG1", "DBG2 (Recommended)"])
        self.dbg_algorithm.setCurrentText(self.state["dbg_algorithm"])
        self.similarity = QSpinBox()
        self.similarity.setRange(1, 100)
        self.similarity.setValue(self.state["dbg_similarity"])
        self.seed_window = QSpinBox()
        self.seed_window.setRange(100, 1000)
        self.seed_window.setValue(self.state["dbg_seed_window_nm"])
        self.stop_groups = QSpinBox()
        self.stop_groups.setRange(1, 25000)
        self.stop_groups.setValue(self.state["dbg_stop_group_count"])
        self.rotated = QCheckBox("Consider Rotated Patterns the Same")
        self.rotated.setChecked(self.state["consider_rotated"])
        self.flipped = QCheckBox("Consider Flipped Patterns the Same")
        self.flipped.setChecked(self.state["consider_flipped"])
        self.systematic_mode = QComboBox()
        self.systematic_mode.addItems(["Defect Count", "Percent of Total Defects"])
        self.systematic_mode.setCurrentText(self.state["systematic_threshold_mode"])
        self.systematic_threshold = QDoubleSpinBox()
        self.systematic_threshold.setRange(0, 65000)
        self.systematic_threshold.setDecimals(2)
        self.systematic_threshold.setValue(self.state["systematic_threshold"])
        self.filter_enabled = QCheckBox("Apply Defect Filter Out Rule")
        self.filter_enabled.setChecked(self.state["dbg_filter_enabled"])
        self.filter_attribute = QComboBox()
        self.filter_attribute.addItems(["Pattern Density", "Defect Size", "DCI", "PCI"])
        self.filter_attribute.setCurrentText(self.state["dbg_filter_attribute"])
        self.filter_operator = QComboBox()
        self.filter_operator.addItems([">=", ">", "<=", "<", "==", "!="])
        self.filter_operator.setCurrentText(self.state["dbg_filter_operator"])
        self.filter_value = QDoubleSpinBox()
        self.filter_value.setRange(-500000000, 500000000)
        self.filter_value.setDecimals(4)
        self.filter_value.setValue(self.state["dbg_filter_value"])
        self.supergrouping = QCheckBox("Enable Supergrouping (DBG1 only)")
        self.supergrouping.setChecked(self.state["supergrouping_enabled"])
        self.super_similarity = QSpinBox()
        self.super_similarity.setRange(1, 100)
        self.super_similarity.setValue(self.state["supergroup_similarity"])
        self.super_time = QLineEdit(self.state["supergroup_time_limit"])
        self.super_time.setPlaceholderText("hh:mm:ss")
        self.transfer_clips = QCheckBox("Transfer Clip Images for Review Sample (maximum 200)")
        self.transfer_clips.setChecked(self.state["transfer_clip_images"])
        self.transfer_layer = QComboBox()
        self.transfer_layer.addItems(self.state["process_layers"] or ["Design"])
        self.transfer_layer.setCurrentText(self.state["transfer_clip_layer"])
        rows = (
            ("DBG", self.dbg_enabled), ("DBG Algorithm", self.dbg_algorithm),
            ("DBG1 Clip Similarity", self.similarity), ("DBG2 Seed Window (nm)", self.seed_window),
            ("Stop Beyond Group Count", self.stop_groups), ("Systematic Threshold By", self.systematic_mode),
            ("Systematic Threshold", self.systematic_threshold), ("Rotation", self.rotated),
            ("Flip", self.flipped), ("Advanced Filter", self.filter_enabled),
            ("Filter Attribute", self.filter_attribute), ("Relational Operator", self.filter_operator),
            ("Operand Value", self.filter_value), ("Supergrouping", self.supergrouping),
            ("Supergroup Similarity", self.super_similarity), ("Time Limit", self.super_time),
            ("Clip Transfer", self.transfer_clips), ("Transfer Layer", self.transfer_layer),
        )
        for index, (label, control) in enumerate(rows):
            row, pair = divmod(index, 2)
            form.addWidget(QLabel(label), row, pair * 2)
            form.addWidget(control, row, pair * 2 + 1)
        form.setColumnStretch(1, 1)
        form.setColumnStretch(3, 1)
        form.setRowStretch((len(rows) + 1) // 2, 1)
        self.tabs.addTab(page, "DBG")
        self.dbg_enabled.toggled.connect(self._refresh_dbg_controls)
        self.dbg_algorithm.currentTextChanged.connect(self._refresh_dbg_controls)
        self.filter_enabled.toggled.connect(self._refresh_dbg_controls)
        self.supergrouping.toggled.connect(self._refresh_dbg_controls)
        self.transfer_clips.toggled.connect(self._refresh_dbg_controls)
        self._refresh_dbg_controls()

    def _refresh_dbg_controls(self, *_args):
        enabled = self.dbg_enabled.isChecked()
        dbg1 = self.dbg_algorithm.currentText() == "DBG1"
        for control in (
            self.dbg_algorithm, self.systematic_mode, self.systematic_threshold,
            self.rotated, self.flipped, self.filter_enabled, self.transfer_clips,
        ):
            control.setEnabled(enabled)
        self.similarity.setEnabled(enabled and dbg1)
        self.seed_window.setEnabled(enabled and not dbg1)
        self.stop_groups.setEnabled(enabled and not dbg1)
        for control in (self.filter_attribute, self.filter_operator, self.filter_value):
            control.setEnabled(enabled and self.filter_enabled.isChecked())
        self.supergrouping.setEnabled(enabled and dbg1)
        self.super_similarity.setEnabled(enabled and dbg1 and self.supergrouping.isChecked())
        self.super_time.setEnabled(enabled and dbg1 and self.supergrouping.isChecked())
        self.transfer_layer.setEnabled(enabled and self.transfer_clips.isChecked())

    def _build_attributes(self):
        page = QWidget()
        root = QVBoxLayout(page)
        self.attribute_checks = {}
        for key, label in (
            ("dci_enabled", "Defect Criticality Index (DCI)"),
            ("pci_enabled", "Pattern Complexity Index (PCI)"),
            ("design_attributes_enabled", "Design Attributes"),
            ("min_line_space", "Calculate Minimum Line Width and Space"),
            ("pattern_density_1", "EBB Pattern Density 1"),
            ("pattern_density_2", "EBB Pattern Density 2"),
            ("overlap_ratio_1", "EBB Overlap Ratio 1"),
            ("overlap_ratio_2", "EBB Overlap Ratio 2"),
        ):
            check = QCheckBox(label)
            check.setChecked(self.state[key])
            self.attribute_checks[key] = check
            root.addWidget(check)
        root.addWidget(QLabel("Process Layers: " + (", ".join(self.state["process_layers"]) or "None")))
        root.addStretch(1)
        self.tabs.addTab(page, "Design Attributes")

    def _build_sampling(self):
        page = QWidget()
        form = QGridLayout(page)
        sampling = self.state["sampling"]
        self.sample_max = QSpinBox()
        self.sample_max.setRange(0, 65000)
        self.sample_max.setValue(sampling["maximum"])
        self.sample_dbc = QCheckBox("Enable DBC Sampling")
        self.sample_dbc.setChecked(sampling["dbc_enabled"])
        self.sample_dbc_size = QSpinBox()
        self.sample_dbc_size.setRange(0, 65000)
        self.sample_dbc_size.setValue(sampling["dbc_size"])
        self.filter_nuisance = QCheckBox("Filter-Out DBC Nuisance")
        self.filter_nuisance.setChecked(sampling["filter_dbc_nuisance"])
        self.dbc_priority = QComboBox()
        self.dbc_priority.addItems(["Count", "Random"])
        self.dbc_priority.setCurrentText(sampling["dbc_bin_priority"])
        self.dbc_scheme = QComboBox()
        self.dbc_scheme.addItems(["Random", "Prioritized by DCI", "Prioritized by Pattern Density", "Prioritized by Defect Size"])
        self.dbc_scheme.setCurrentText(sampling["dbc_scheme"])
        self.sample_systematic = QCheckBox("Enable DBG Systematic Sampling")
        self.sample_systematic.setChecked(sampling["dbg_systematic_enabled"])
        self.sample_bins = QSpinBox()
        self.sample_bins.setRange(0, 65000)
        self.sample_bins.setValue(sampling["dbg_systematic_bins"])
        self.sample_systematic_size = QSpinBox()
        self.sample_systematic_size.setRange(0, 65000)
        self.sample_systematic_size.setValue(sampling["dbg_systematic_size"])
        self.systematic_priority = QComboBox()
        self.systematic_priority.addItems(["Random", "Count"])
        self.systematic_priority.setCurrentText(sampling["dbg_systematic_priority"])
        self.systematic_scheme = QComboBox()
        self.systematic_scheme.addItems(["Random", "Prioritized by DCI", "Prioritized by Pattern Density", "Prioritized by Defect Size"])
        self.systematic_scheme.setCurrentText(sampling["dbg_systematic_scheme"])
        self.sample_random = QCheckBox("Enable DBG Random Sampling")
        self.sample_random.setChecked(sampling["dbg_random_enabled"])
        self.random_scheme = QComboBox()
        self.random_scheme.addItems(["Random", "Prioritized by DCI", "Prioritized by Pattern Density", "Prioritized by Defect Size"])
        self.random_scheme.setCurrentText(sampling["dbg_random_scheme"])
        self.sample_limits = QCheckBox("Enable Limits")
        self.sample_limits.setChecked(sampling["limits_enabled"])
        self.max_per_die = QSpinBox()
        self.max_per_die.setRange(1, 65000)
        self.max_per_die.setValue(sampling["max_per_die"])
        self.max_per_cluster = QSpinBox()
        self.max_per_cluster.setRange(2, 65000)
        self.max_per_cluster.setValue(sampling["max_per_cluster"])
        self.max_cluster_percent = QSpinBox()
        self.max_cluster_percent.setRange(0, 100)
        self.max_cluster_percent.setValue(sampling["max_cluster_percent"])
        self.minimum_defect_size = QDoubleSpinBox()
        self.minimum_defect_size.setRange(0, 500000000)
        self.minimum_defect_size.setDecimals(2)
        self.minimum_defect_size.setValue(sampling["minimum_defect_size"])
        self.maximum_defect_size = QDoubleSpinBox()
        self.maximum_defect_size.setRange(0, 500000000)
        self.maximum_defect_size.setDecimals(2)
        self.maximum_defect_size.setValue(sampling["maximum_defect_size"])
        self.adders_only = QCheckBox("Adders Only")
        self.adders_only.setChecked(sampling["adders_only"])
        rows = (
            ("Maximum DBB Defects", self.sample_max), ("DBC", self.sample_dbc),
            ("DBC Sample Size", self.sample_dbc_size), ("DBC Nuisance", self.filter_nuisance),
            ("DBC Bin Priorities", self.dbc_priority), ("DBC Within Bin", self.dbc_scheme),
            ("DBG Systematic", self.sample_systematic), ("Systematic Bin Count", self.sample_bins),
            ("Systematic Sample Size", self.sample_systematic_size), ("Systematic Bin Priorities", self.systematic_priority),
            ("Systematic Within Bin", self.systematic_scheme), ("DBG Random", self.sample_random),
            ("DBG Random Within Bin", self.random_scheme),
            ("Limits", self.sample_limits), ("Maximum per Die", self.max_per_die),
            ("Maximum per Cluster", self.max_per_cluster), ("Maximum Cluster Percent", self.max_cluster_percent),
            ("Minimum Defect Size (um^2)", self.minimum_defect_size),
            ("Maximum Defect Size (um^2)", self.maximum_defect_size),
            ("Source Layer", self.adders_only),
        )
        for index, (label, control) in enumerate(rows):
            row, pair = divmod(index, 2)
            form.addWidget(QLabel(label), row, pair * 2)
            form.addWidget(control, row, pair * 2 + 1)
        form.setColumnStretch(1, 1)
        form.setColumnStretch(3, 1)
        form.setRowStretch((len(rows) + 1) // 2, 1)
        self.tabs.addTab(page, "DBB Sampling")
        self.sample_dbc.toggled.connect(self._refresh_sampling_controls)
        self.sample_systematic.toggled.connect(self._refresh_sampling_controls)
        self.sample_random.toggled.connect(self._refresh_sampling_controls)
        self.sample_limits.toggled.connect(self._refresh_sampling_controls)
        self._refresh_sampling_controls()

    def _refresh_sampling_controls(self, *_args):
        for control in (self.sample_dbc_size, self.filter_nuisance, self.dbc_priority, self.dbc_scheme):
            control.setEnabled(self.sample_dbc.isChecked())
        for control in (self.sample_bins, self.sample_systematic_size, self.systematic_priority, self.systematic_scheme):
            control.setEnabled(self.sample_systematic.isChecked())
        self.random_scheme.setEnabled(self.sample_random.isChecked())
        for control in (
            self.max_per_die, self.max_per_cluster, self.max_cluster_percent,
            self.minimum_defect_size, self.maximum_defect_size, self.adders_only,
        ):
            control.setEnabled(self.sample_limits.isChecked())

    def _finish(self):
        state = normalized_dbb_state(self.state)
        state.update({
            "enabled": self.enabled.isChecked(),
            "design_clip_size_nm": self.clip_size.value(),
            "use_defect_size": self.use_defect_size.isChecked(),
            "exclude_array_regions": self.exclude_array.isChecked(),
            "dbc_enabled": self.dbc_enabled.isChecked(),
            "dbc_library": self.dbc_library.text().strip(),
            "dbg_enabled": self.dbg_enabled.isChecked(),
            "dbg_algorithm": self.dbg_algorithm.currentText(),
            "dbg_similarity": self.similarity.value(),
            "dbg_stop_group_count": self.stop_groups.value(),
            "consider_rotated": self.rotated.isChecked(),
            "consider_flipped": self.flipped.isChecked(),
            "dbg_seed_window_nm": self.seed_window.value(),
            "systematic_threshold_mode": self.systematic_mode.currentText(),
            "systematic_threshold": self.systematic_threshold.value(),
            "dbg_filter_enabled": self.filter_enabled.isChecked(),
            "dbg_filter_attribute": self.filter_attribute.currentText(),
            "dbg_filter_operator": self.filter_operator.currentText(),
            "dbg_filter_value": self.filter_value.value(),
            "supergrouping_enabled": self.supergrouping.isChecked(),
            "supergroup_similarity": self.super_similarity.value(),
            "supergroup_time_limit": self.super_time.text().strip(),
            "transfer_clip_images": self.transfer_clips.isChecked(),
            "transfer_clip_layer": self.transfer_layer.currentText(),
            "throughput_skip_dbb": self.throughput.isChecked(),
            "throughput_skip_attributes": self.throughput_attributes.isChecked(),
        })
        if state["dbg_filter_enabled"] and state["dbg_filter_attribute"] == "DCI":
            self.attribute_checks["dci_enabled"].setChecked(True)
        for key, check in self.attribute_checks.items():
            state[key] = check.isChecked()
        state["sampling"].update({
            "maximum": self.sample_max.value(),
            "dbc_enabled": self.sample_dbc.isChecked(),
            "dbc_size": self.sample_dbc_size.value(),
            "filter_dbc_nuisance": self.filter_nuisance.isChecked(),
            "dbc_bin_priority": self.dbc_priority.currentText(),
            "dbc_scheme": self.dbc_scheme.currentText(),
            "dbg_systematic_enabled": self.sample_systematic.isChecked(),
            "dbg_systematic_bins": self.sample_bins.value(),
            "dbg_systematic_size": self.sample_systematic_size.value(),
            "dbg_systematic_priority": self.systematic_priority.currentText(),
            "dbg_systematic_scheme": self.systematic_scheme.currentText(),
            "dbg_random_enabled": self.sample_random.isChecked(),
            "dbg_random_scheme": self.random_scheme.currentText(),
            "limits_enabled": self.sample_limits.isChecked(),
            "max_per_die": self.max_per_die.value(),
            "max_per_cluster": self.max_per_cluster.value(),
            "max_cluster_percent": self.max_cluster_percent.value(),
            "minimum_defect_size": self.minimum_defect_size.value(),
            "maximum_defect_size": self.maximum_defect_size.value(),
            "adders_only": self.adders_only.isChecked(),
        })
        errors = validate_dbb_setup(state)
        if errors:
            QMessageBox.warning(self, "Design Based Binning", "\n".join(errors))
            return
        self.result_state = normalized_dbb_state(state)
        self.accept()


class DBCSetupDialog(QDialog):
    def __init__(self, state=None, parent=None):
        super().__init__(parent)
        self.state = normalized_dbb_state(state)
        self.result_state = None
        self.setWindowTitle("DBC Setup")
        self.resize(980, 620)
        root = QVBoxLayout(self)
        summary = QLabel(f"RDF: {self.state['rdf_file'] or '-'} | Process Layers: {', '.join(self.state['process_layers'])}")
        root.addWidget(summary)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Source", "Name", "Layer", "DBC Bin"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table, 1)
        buttons = QHBoxLayout()
        import_library = QPushButton("Import DBC Examples")
        import_library.clicked.connect(lambda: self._add_example("DBC Library"))
        import_hotspot = QPushButton("Import HotSpot Clip")
        import_hotspot.clicked.connect(self._import_hotspot)
        create_bin = QPushButton("Create Bin")
        create_bin.clicked.connect(self._create_bin)
        buttons.addWidget(import_library)
        buttons.addWidget(import_hotspot)
        buttons.addWidget(create_bin)
        buttons.addStretch(1)
        root.addLayout(buttons)
        self._refresh()
        footer = QHBoxLayout()
        footer.addStretch(1)
        save = QPushButton("Save and Exit")
        save.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        footer.addWidget(save)
        footer.addWidget(cancel)
        root.addLayout(footer)

    def _refresh(self):
        self.table.setRowCount(0)
        for example in self.state["dbc_examples"]:
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = (example.get("source", ""), example.get("name", ""), example.get("layer", ""), example.get("bin", "Unassigned"))
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(str(value)))

    def _add_example(self, source):
        index = len(self.state["dbc_examples"]) + 1
        self.state["dbc_examples"].append({
            "source": source,
            "name": f"Example {index}",
            "layer": self.state["inspection_layer"] or "Design",
            "bin": "Unassigned",
        })
        self._refresh()

    def _import_hotspot(self):
        filename, _selected = QFileDialog.getOpenFileName(
            self,
            "Import HotSpot CSV",
            "",
            "CSV Files (*.csv);;Text Files (*.txt);;All Files (*)",
        )
        if not filename:
            return
        try:
            from .workspace import parse_hotspot_csv

            points = parse_hotspot_csv(
                Path(filename).read_text(encoding="utf-8-sig"),
                self.state["design_clip_size_nm"],
            )
        except (OSError, UnicodeError, ValueError) as exc:
            QMessageBox.warning(self, "Import HotSpot Clip", str(exc))
            return
        for point in points:
            index = len(self.state["dbc_examples"]) + 1
            self.state["dbc_examples"].append({
                "id": point["id"],
                "source": "RDF HotSpot",
                "source_file": filename,
                "name": f"HotSpot {index}",
                "layer": self.state["inspection_layer"] or "Design",
                "bin": "Unassigned",
                "x": point["x"],
                "y": point["y"],
                "clip_size": point["clip_size"],
                "aoi_size": point["aoi_size"],
                "valid": False,
            })
        self._refresh()

    def _create_bin(self):
        selected = [item for item in self.state["dbc_examples"] if item.get("bin") == "Unassigned"]
        if not selected:
            return
        name = f"DBC Bin {len(self.state['dbc_bins']) + 1}"
        self.state["dbc_bins"].append({"name": name, "class_code": 100 + len(self.state["dbc_bins"])})
        for item in selected:
            item["bin"] = name
        self._refresh()

    def _finish(self):
        self.result_state = normalized_dbb_state(self.state)
        self.accept()

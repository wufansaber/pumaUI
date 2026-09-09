from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import csv
from math import hypot
import json
from pathlib import Path

from ...qt_compat import (
    QAction,
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
    QMenuBar,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    Qt,
    QVBoxLayout,
    QWidget,
)


DEFAULT_MATCHING_PARAMETERS = {
    "self_matching_radius": 5.0,
    "self_deskew": False,
    "self_overlay_radius": 2.0,
    "cross_matching_radius": 50.0,
    "cross_deskew": False,
    "cross_overlay_radius": 2.0,
    "clustering_enabled": False,
    "clustering_auto": True,
    "cluster_minimum": 3,
    "cluster_distance": 300.0,
    "cluster_multiplier": 3.0,
    "caprate_enabled": True,
    "caprate_reverse": False,
    "count_enabled": True,
    "count_grand_mean": True,
}

DEFAULT_DSW_PARAMETERS = {
    "select_test": False,
    "test_number": 1,
    "select_channel": False,
    "channel_number": 1,
    "minimum_intensity_enabled": False,
    "minimum_intensity": 0.0,
    "remove_clusters": False,
    "clustering_auto": True,
    "second_pass": 1.0,
    "cluster_radius": 500.0,
    "minimum_cluster_defects": 10,
    "deskew": False,
    "overlay_radius": 500.0,
    "match_radius": 50.0,
    "intensity_ratio": 0.5,
}


def _bounded(value, low=0.0, high=5000.0):
    return max(low, min(high, float(value)))


def normalize_matching_parameters(value=None):
    result = {**DEFAULT_MATCHING_PARAMETERS, **(value if isinstance(value, dict) else {})}
    for key in (
        "self_matching_radius",
        "self_overlay_radius",
        "cross_matching_radius",
        "cross_overlay_radius",
        "cluster_distance",
    ):
        result[key] = _bounded(result[key])
    result["cluster_minimum"] = max(1, int(result["cluster_minimum"]))
    result["cluster_multiplier"] = max(1.0, float(result["cluster_multiplier"]))
    for key, default in DEFAULT_MATCHING_PARAMETERS.items():
        if isinstance(default, bool):
            result[key] = bool(result[key])
    return result


def normalize_dsw_parameters(value=None):
    result = {**DEFAULT_DSW_PARAMETERS, **(value if isinstance(value, dict) else {})}
    for key in ("cluster_radius", "overlay_radius", "match_radius"):
        result[key] = _bounded(result[key])
    result["test_number"] = max(1, int(result["test_number"]))
    result["channel_number"] = max(1, min(3, int(result["channel_number"])))
    result["minimum_cluster_defects"] = max(1, int(result["minimum_cluster_defects"]))
    result["second_pass"] = max(1.0, float(result["second_pass"]))
    result["intensity_ratio"] = max(0.0, min(1.0, float(result["intensity_ratio"])))
    for key, default in DEFAULT_DSW_PARAMETERS.items():
        if isinstance(default, bool):
            result[key] = bool(result[key])
    return result


def calculate_match(master_defects, candidate_defects, radius):
    radius = _bounded(radius)
    available = set(range(len(candidate_defects)))
    pairs = []
    for master in master_defects:
        best = None
        for index in available:
            candidate = candidate_defects[index]
            distance = hypot(
                float(master.get("x", 0.0)) - float(candidate.get("x", 0.0)),
                float(master.get("y", 0.0)) - float(candidate.get("y", 0.0)),
            )
            if distance <= radius and (best is None or distance < best[0]):
                best = (distance, index)
        if best is not None:
            available.remove(best[1])
            pairs.append((master, candidate_defects[best[1]], best[0]))
    master_count = len(master_defects)
    candidate_count = len(candidate_defects)
    matched = len(pairs)
    denominator = max(1, master_count)
    count_match = matched / denominator * 100.0
    count_balance = min(master_count, candidate_count) / max(1, max(master_count, candidate_count))
    distance_quality = 1.0 if not pairs or radius == 0 else max(
        0.0, 1.0 - sum(pair[2] for pair in pairs) / len(pairs) / radius
    )
    return {
        "master_count": master_count,
        "candidate_count": candidate_count,
        "matched_count": matched,
        "count_match_percent": round(count_match, 2),
        "match_factor": round(100.0 * count_balance * distance_quality, 2),
        "average_offset": round(sum(pair[2] for pair in pairs) / max(1, matched), 3),
        "pairs": pairs,
    }


class MatchingParametersDialog(QDialog):
    def __init__(self, parameters=None, defaults=None, parent=None):
        super().__init__(parent)
        self.parameters = normalize_matching_parameters(parameters)
        self.default_parameters = normalize_matching_parameters(defaults)
        self.result_parameters = None
        self.saved_profile = None
        self.setWindowTitle("Inspection Matching Parameters")
        self.resize(760, 590)
        root = QVBoxLayout(self)
        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)
        self.controls = {}
        self.tabs.addTab(self._general_tab(), "General")
        self.tabs.addTab(self._clustering_tab(), "Clustering")
        self.tabs.addTab(self._matching_tab(), "KT Matching / Count")
        buttons = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self._save_profile)
        buttons.addWidget(self.save_button)
        delete = QPushButton("Delete")
        delete.clicked.connect(self._delete_profile)
        buttons.addWidget(delete)
        save_default = QPushButton("Save As Default")
        save_default.clicked.connect(self._save_default)
        buttons.addWidget(save_default)
        load_default = QPushButton("Load Default")
        load_default.clicked.connect(self._load_default)
        buttons.addWidget(load_default)
        buttons.addStretch(1)
        ok = QPushButton("OK")
        ok.clicked.connect(self._accept)
        buttons.addWidget(ok)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)
        root.addLayout(buttons)
        self._load_values(self.parameters)

    def _spin(self, key, maximum=5000.0, decimals=3):
        spin = QDoubleSpinBox()
        spin.setRange(0.0, maximum)
        spin.setDecimals(decimals)
        self.controls[key] = spin
        return spin

    def _check(self, key, label):
        check = QCheckBox(label)
        self.controls[key] = check
        return check

    def _general_tab(self):
        page = QWidget()
        layout = QGridLayout(page)
        for row, (prefix, title) in enumerate((("self", "Self-Tool"), ("cross", "Cross-Tool"))):
            layout.addWidget(QLabel(title), row * 3, 0, 1, 2)
            layout.addWidget(QLabel("Matching Radius"), row * 3 + 1, 0)
            layout.addWidget(self._spin(f"{prefix}_matching_radius"), row * 3 + 1, 1)
            layout.addWidget(self._check(f"{prefix}_deskew", "Deskew"), row * 3 + 2, 0)
            layout.addWidget(self._spin(f"{prefix}_overlay_radius"), row * 3 + 2, 1)
        return page

    def _clustering_tab(self):
        page = QWidget()
        layout = QGridLayout(page)
        layout.addWidget(self._check("clustering_enabled", "Enabled"), 0, 0, 1, 2)
        layout.addWidget(self._check("clustering_auto", "Auto"), 1, 0, 1, 2)
        layout.addWidget(QLabel("Defect Count"), 2, 0)
        minimum = QSpinBox()
        minimum.setRange(1, 999999)
        self.controls["cluster_minimum"] = minimum
        layout.addWidget(minimum, 2, 1)
        layout.addWidget(QLabel("Distance"), 3, 0)
        layout.addWidget(self._spin("cluster_distance"), 3, 1)
        layout.addWidget(QLabel("Second Pass Multiplier"), 4, 0)
        layout.addWidget(self._spin("cluster_multiplier", 100.0), 4, 1)
        return page

    def _matching_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(self._check("caprate_enabled", "Caprate Enabled"))
        layout.addWidget(self._check("caprate_reverse", "Reverse Caprate"))
        layout.addWidget(self._check("count_enabled", "Count Enabled"))
        layout.addWidget(self._check("count_grand_mean", "Use Grand Mean"))
        layout.addStretch(1)
        return page

    def _values(self):
        values = {}
        for key, control in self.controls.items():
            values[key] = control.isChecked() if isinstance(control, QCheckBox) else control.value()
        return normalize_matching_parameters(values)

    def _load_values(self, values):
        for key, control in self.controls.items():
            value = values[key]
            control.setChecked(bool(value)) if isinstance(control, QCheckBox) else control.setValue(value)

    def _save_profile(self):
        self.saved_profile = self._values()

    def _delete_profile(self):
        self.saved_profile = None

    def _save_default(self):
        self.default_parameters = self._values()

    def _load_default(self):
        self._load_values(self.default_parameters)

    def _accept(self):
        self.result_parameters = self._values()
        self.accept()


class DSWMatchParametersDialog(QDialog):
    def __init__(self, parameters=None, parent=None):
        super().__init__(parent)
        self.parameters = normalize_dsw_parameters(parameters)
        self.result_parameters = None
        self.setWindowTitle("DSW Match Parameter")
        self.resize(650, 560)
        root = QVBoxLayout(self)
        form = QGridLayout()
        self.checks = {}
        self.spins = {}
        rows = (
            ("select_test", "Select Test", "test_number", 999, 0),
            ("select_channel", "Select Channel", "channel_number", 3, 0),
            ("minimum_intensity_enabled", "Intensity Minimum", "minimum_intensity", 999999, 2),
            ("remove_clusters", "Remove Cluster", "cluster_radius", 5000, 2),
            ("deskew", "Perform Co-ordinate transformation", "overlay_radius", 5000, 2),
        )
        for row, (check_key, label, spin_key, maximum, decimals) in enumerate(rows):
            check = QCheckBox(label)
            check.setChecked(bool(self.parameters[check_key]))
            self.checks[check_key] = check
            form.addWidget(check, row, 0)
            spin = QDoubleSpinBox() if decimals else QSpinBox()
            spin.setRange(0, maximum)
            if isinstance(spin, QDoubleSpinBox):
                spin.setDecimals(decimals)
            spin.setValue(self.parameters[spin_key])
            self.spins[spin_key] = spin
            form.addWidget(spin, row, 1)
            check.toggled.connect(spin.setEnabled)
            spin.setEnabled(check.isChecked())
        extra = (
            ("second_pass", "Second Pass", 100.0, 2),
            ("minimum_cluster_defects", "Min Defects Per Cluster", 999999, 0),
            ("match_radius", "Match Radius", 5000.0, 2),
            ("intensity_ratio", "Intensity Ratio (diff/sum)", 1.0, 3),
        )
        offset = len(rows)
        for index, (key, label, maximum, decimals) in enumerate(extra):
            form.addWidget(QLabel(label), offset + index, 0)
            spin = QDoubleSpinBox() if decimals else QSpinBox()
            spin.setRange(0, maximum)
            if isinstance(spin, QDoubleSpinBox):
                spin.setDecimals(decimals)
            spin.setValue(self.parameters[key])
            self.spins[key] = spin
            form.addWidget(spin, offset + index, 1)
        self.clustering_auto = QCheckBox("Clustering Auto")
        self.clustering_auto.setChecked(bool(self.parameters["clustering_auto"]))
        form.addWidget(self.clustering_auto, offset + len(extra), 0, 1, 2)
        root.addLayout(form)
        root.addStretch(1)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        ok = QPushButton("OK")
        ok.clicked.connect(self._accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        root.addLayout(buttons)

    def _accept(self):
        values = dict(self.parameters)
        values.update({key: check.isChecked() for key, check in self.checks.items()})
        values.update({key: spin.value() for key, spin in self.spins.items()})
        values["clustering_auto"] = self.clustering_auto.isChecked()
        self.result_parameters = normalize_dsw_parameters(values)
        self.accept()


class MatchDetailDialog(QDialog):
    def __init__(self, title="Inspection Matching Review", result=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(720, 500)
        result = result or {}
        root = QVBoxLayout(self)
        table = QTableWidget(0, 2)
        table.setHorizontalHeaderLabels(["Metric", "Value"])
        table.horizontalHeader().setStretchLastSection(True)
        for key in ("master_count", "candidate_count", "matched_count", "count_match_percent", "match_factor", "average_offset"):
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, QTableWidgetItem(key.replace("_", " ").title()))
            table.setItem(row, 1, QTableWidgetItem(str(result.get(key, "-"))))
        root.addWidget(table, 1)
        note = QLabel("Graph and metric data are deterministic simulator results.")
        root.addWidget(note)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        root.addWidget(close, alignment=Qt.AlignRight)


class InspectionMatchingUtilityDialog(QDialog):
    def __init__(self, results=None, settings=None, parent=None):
        super().__init__(parent)
        self.results = deepcopy(list(results or []))
        self.settings = deepcopy(settings or {})
        self.parameters = normalize_matching_parameters(self.settings.get("product_parameters"))
        self.dsw_parameters = normalize_dsw_parameters(self.settings.get("dsw_parameters"))
        self.user_targets = {"count_match_percent": 80.0, "match_factor": 70.0, **self.settings.get("user_targets", {})}
        self.selections = []
        self.last_result = None
        self.current_session_path = None
        self.setWindowTitle("Inspection Matching Utility")
        self.resize(1180, 760)
        root = QVBoxLayout(self)
        self.menu = self._menu_bar()
        root.addWidget(self.menu)
        self.tabs = QTabWidget()
        self.product_page = self._product_page()
        self.conformance_page = self._conformance_page()
        self.dsw_page = self._dsw_page()
        self.tabs.addTab(self.product_page, "Product Matching")
        self.tabs.addTab(self.conformance_page, "DSW Conformance")
        self.tabs.addTab(self.dsw_page, "DSW Matching")
        root.addWidget(self.tabs, 1)
        footer = QHBoxLayout()
        self.status_label = QLabel("Ready")
        footer.addWidget(self.status_label, 1)
        exit_button = QPushButton("Exit")
        exit_button.clicked.connect(self._exit)
        footer.addWidget(exit_button)
        root.addLayout(footer)

    def _menu_bar(self):
        menu = QMenuBar()
        file_menu = menu.addMenu("File")
        file_menu.addAction("New", self._new_session)
        file_menu.addAction("Open...", self._open_session)
        file_menu.addAction("Save", self._save_session)
        file_menu.addAction("Save As...", lambda: self._save_session(save_as=True))
        file_menu.addAction("Save Result...", self._save_result)
        file_menu.addSeparator()
        file_menu.addAction("Exit", self._exit)
        parameter = menu.addMenu("Parameter")
        parameter.addAction("Product Matching...", self._edit_product_parameters)
        parameter.addAction("DSW Match...", self._edit_dsw_parameters)
        parameter.addAction("DSW Conformance...", self._edit_dsw_parameters)
        view = menu.addMenu("View")
        view.addAction("Setup", lambda: self.tabs.setCurrentIndex(0))
        self.review_action = view.addAction("Review", self._view_result)
        self.review_action.setEnabled(False)
        self.graph_action = view.addAction("DSW Conformance Plot", self._view_result)
        self.graph_action.setEnabled(False)
        review = menu.addMenu("Review")
        color = review.addMenu("Color By")
        self.color_actions = []
        for label in ("Spec", "User Target", "None"):
            action = QAction(label, self)
            action.setCheckable(True)
            action.setChecked(label == "Spec")
            action.triggered.connect(lambda checked=False, value=label: self._set_color_by(value))
            color.addAction(action)
            self.color_actions.append(action)
        review.addAction("Export...", self._export_result)
        help_menu = menu.addMenu("Help")
        help_menu.addAction(
            "About",
            lambda: QMessageBox.information(self, "About", "Puma 9980 Inspection Matching Utility simulator"),
        )
        return menu

    def _product_page(self):
        page = QWidget()
        root = QHBoxLayout(page)
        data_panel = QFrame()
        data_layout = QVBoxLayout(data_panel)
        data_layout.addWidget(QLabel("Data Selection"))
        self.available_table = QTableWidget(len(self.results), 4)
        self.available_table.setHorizontalHeaderLabels(["Data", "Type", "Defect Count", "Tool ID"])
        self.available_table.horizontalHeader().setStretchLastSection(True)
        for row, result in enumerate(self.results):
            values = (
                result.get("lot_id", result.get("inspection", f"Lot {row + 1}")),
                result.get("source_type", "Lot"),
                len(result.get("defects", [])),
                result.get("tool_id", "Puma9980"),
            )
            for column, value in enumerate(values):
                self.available_table.setItem(row, column, QTableWidgetItem(str(value)))
        data_layout.addWidget(self.available_table, 1)
        data_buttons = QHBoxLayout()
        add = QPushButton("Add")
        add.clicked.connect(self._add_selected_data)
        data_buttons.addWidget(add)
        add_all = QPushButton("Add All")
        add_all.clicked.connect(self._add_all_data)
        data_buttons.addWidget(add_all)
        remove = QPushButton("Remove")
        remove.clicked.connect(self._remove_selection)
        data_buttons.addWidget(remove)
        remove_all = QPushButton("Remove All")
        remove_all.clicked.connect(self._remove_all_selections)
        data_buttons.addWidget(remove_all)
        data_layout.addLayout(data_buttons)
        self.selection_table = QTableWidget(0, 5)
        self.selection_table.setHorizontalHeaderLabels(["Selection", "Source", "Enabled", "Defects", "Recipe"])
        self.selection_table.horizontalHeader().setStretchLastSection(True)
        data_layout.addWidget(self.selection_table, 1)
        root.addWidget(data_panel, 3)

        match_panel = QFrame()
        match_layout = QVBoxLayout(match_panel)
        title = QLabel("Matching Configuration")
        title.setStyleSheet("font-weight: 700;")
        match_layout.addWidget(title)
        spec_buttons = QHBoxLayout()
        spec = QPushButton("Spec")
        spec.clicked.connect(self._show_spec)
        target = QPushButton("User Target")
        target.clicked.connect(self._show_user_target)
        parameters = QPushButton("Parameter")
        parameters.clicked.connect(self._edit_product_parameters)
        spec_buttons.addWidget(spec)
        spec_buttons.addWidget(target)
        spec_buttons.addWidget(parameters)
        match_layout.addLayout(spec_buttons)
        match_layout.addWidget(QLabel("Master"))
        self.master_combo = QComboBox()
        match_layout.addWidget(self.master_combo)
        match_layout.addWidget(QLabel("Candidate"))
        self.candidate_combo = QComboBox()
        match_layout.addWidget(self.candidate_combo)
        self.match_progress = QProgressBar()
        self.match_progress.setRange(0, 100)
        match_layout.addWidget(self.match_progress)
        self.match_button = QPushButton("Match")
        self.match_button.clicked.connect(self._run_product_match)
        self.match_button.setEnabled(False)
        match_layout.addWidget(self.match_button)
        self.view_button = QPushButton("View")
        self.view_button.clicked.connect(self._view_result)
        self.view_button.setEnabled(False)
        match_layout.addWidget(self.view_button)
        self.result_table = QTableWidget(0, 3)
        self.result_table.setHorizontalHeaderLabels(["Metric", "Value", "Status"])
        self.result_table.horizontalHeader().setStretchLastSection(True)
        match_layout.addWidget(self.result_table, 1)
        root.addWidget(match_panel, 2)
        return page

    def _conformance_page(self):
        page = QWidget()
        layout = QGridLayout(page)
        layout.addWidget(QLabel("Spec File"), 0, 0)
        self.conformance_spec = QLineEdit()
        layout.addWidget(self.conformance_spec, 0, 1)
        browse = QPushButton("Browse...")
        browse.clicked.connect(self._browse_conformance_spec)
        layout.addWidget(browse, 0, 2)
        layout.addWidget(QLabel("Lot Id(s)"), 1, 0)
        self.conformance_lot = QComboBox()
        self._load_lot_combo(self.conformance_lot)
        layout.addWidget(self.conformance_lot, 1, 1)
        run = QPushButton("Match")
        run.clicked.connect(self._run_conformance)
        layout.addWidget(run, 2, 1)
        self.conformance_result = QLabel("No conformance result")
        self.conformance_result.setWordWrap(True)
        layout.addWidget(self.conformance_result, 3, 0, 1, 3)
        layout.setRowStretch(4, 1)
        return page

    def _dsw_page(self):
        page = QWidget()
        layout = QGridLayout(page)
        layout.addWidget(QLabel("Lot Id(s)"), 0, 0)
        self.dsw_lot = QComboBox()
        self._load_lot_combo(self.dsw_lot)
        layout.addWidget(self.dsw_lot, 0, 1)
        layout.addWidget(QLabel("Batch save location"), 1, 0)
        self.dsw_output = QLineEdit()
        layout.addWidget(self.dsw_output, 1, 1)
        parameters = QPushButton("Parameter")
        parameters.clicked.connect(self._edit_dsw_parameters)
        layout.addWidget(parameters, 2, 0)
        run = QPushButton("Match")
        run.clicked.connect(self._run_dsw_match)
        layout.addWidget(run, 2, 1)
        self.dsw_result = QLabel("No DSW Match result")
        self.dsw_result.setWordWrap(True)
        layout.addWidget(self.dsw_result, 3, 0, 1, 2)
        layout.setRowStretch(4, 1)
        return page

    def _load_lot_combo(self, combo):
        combo.addItem("")
        for result in self.results:
            combo.addItem(str(result.get("lot_id", result.get("inspection", "Lot"))))

    def _selected_result_indexes(self):
        selected = sorted({index.row() for index in self.available_table.selectedIndexes()})
        return selected or ([self.available_table.currentRow()] if self.available_table.currentRow() >= 0 else [])

    def _add_selected_data(self):
        for index in self._selected_result_indexes():
            self._append_selection(index)

    def _add_all_data(self):
        for index in range(len(self.results)):
            self._append_selection(index)

    def _append_selection(self, index):
        if not 0 <= index < len(self.results):
            return
        source = self.results[index]
        source_id = str(source.get("id", index))
        if any(item["source_id"] == source_id for item in self.selections):
            return
        self.selections.append({
            "name": f"Selection {len(self.selections) + 1}",
            "source_id": source_id,
            "source_type": str(source.get("source_type", "Lot")),
            "result": deepcopy(source),
            "enabled": True,
        })
        self._refresh_selections()

    def _remove_selection(self):
        row = self.selection_table.currentRow()
        if 0 <= row < len(self.selections):
            self.selections.pop(row)
            self._refresh_selections()

    def _remove_all_selections(self):
        self.selections = []
        self._refresh_selections()

    def _refresh_selections(self):
        self.selection_table.setRowCount(len(self.selections))
        self.master_combo.clear()
        self.candidate_combo.clear()
        for row, selection in enumerate(self.selections):
            result = selection["result"]
            values = (
                selection["name"],
                selection["source_type"],
                "Yes" if selection["enabled"] else "No",
                len(result.get("defects", [])),
                result.get("inspection", "-"),
            )
            for column, value in enumerate(values):
                self.selection_table.setItem(row, column, QTableWidgetItem(str(value)))
            self.master_combo.addItem(selection["name"], row)
            self.candidate_combo.addItem(selection["name"], row)
        if len(self.selections) > 1:
            self.candidate_combo.setCurrentIndex(1)
        self.match_button.setEnabled(len(self.selections) >= 2)

    def _run_product_match(self):
        master_index = self.master_combo.currentData()
        candidate_index = self.candidate_combo.currentData()
        if master_index is None or candidate_index is None or master_index == candidate_index:
            QMessageBox.warning(self, "Product Matching", "Select different Master and Candidate data selections.")
            return
        master = self.selections[int(master_index)]
        candidate = self.selections[int(candidate_index)]
        if master["source_type"] != candidate["source_type"]:
            QMessageBox.warning(self, "Product Matching", "Master and Candidate cannot mix Lot and KLARF data.")
            return
        self.match_progress.setValue(30)
        radius = self.parameters["cross_matching_radius"]
        self.last_result = calculate_match(
            master["result"].get("defects", []), candidate["result"].get("defects", []), radius
        )
        self.last_result.update({
            "type": "Product Matching",
            "master": master["name"],
            "candidate": candidate["name"],
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        })
        self.match_progress.setValue(100)
        self._refresh_result_table()
        self.view_button.setEnabled(True)
        self.review_action.setEnabled(True)
        self.status_label.setText("Product matching completed")

    def _refresh_result_table(self):
        metrics = (
            ("Count Match %", "count_match_percent", self.user_targets["count_match_percent"]),
            ("Match Factor", "match_factor", self.user_targets["match_factor"]),
            ("Matched Defects", "matched_count", 0),
            ("Average Offset", "average_offset", None),
        )
        self.result_table.setRowCount(len(metrics))
        for row, (label, key, target) in enumerate(metrics):
            value = self.last_result.get(key, 0)
            passed = target is None or float(value) >= float(target)
            for column, text in enumerate((label, value, "PASS" if passed else "FAIL")):
                item = QTableWidgetItem(str(text))
                if column == 2:
                    item.setBackground(QColor("#a8e6a3") if passed else QColor("#f4aaa3"))
                self.result_table.setItem(row, column, item)

    def _run_conformance(self):
        if not self.conformance_spec.text().strip() or not self.conformance_lot.currentText().strip():
            QMessageBox.warning(self, "DSW Conformance", "Select a specification file and candidate lot.")
            return
        self.last_result = {
            "type": "DSW Conformance",
            "lot": self.conformance_lot.currentText(),
            "spec": self.conformance_spec.text().strip(),
            "count_match_percent": 96.0,
            "match_factor": 92.0,
            "matched_count": 24,
            "average_offset": 0.42,
            "master_count": 25,
            "candidate_count": 25,
        }
        self.conformance_result.setText("PASS - candidate lot conforms to the selected DSW specification.")
        self.graph_action.setEnabled(True)
        self.review_action.setEnabled(True)
        self.status_label.setText("DSW Conformance completed")

    def _run_dsw_match(self):
        if not self.dsw_lot.currentText().strip() or not self.dsw_output.text().strip():
            QMessageBox.warning(self, "DSW Matching", "Select a candidate lot and batch save location.")
            return
        self.last_result = {
            "type": "DSW Matching",
            "lot": self.dsw_lot.currentText(),
            "count_match_percent": 94.0,
            "match_factor": 90.0,
            "matched_count": 23,
            "average_offset": 0.51,
            "master_count": 25,
            "candidate_count": 25,
        }
        self.dsw_result.setText("PASS - DSW candidate matched the configured master list.")
        self.review_action.setEnabled(True)
        self.status_label.setText("DSW Matching completed")

    def _show_spec(self):
        QMessageBox.information(
            self,
            "Spec Details",
            "Label: Default\nMaster Repeats: 1\nCandidate Repeats: 1\nCount Match: 80%\nMatch Factor: 70%",
        )

    def _show_user_target(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("User Target Details")
        layout = QGridLayout(dialog)
        count = QDoubleSpinBox()
        count.setRange(0, 100)
        count.setValue(self.user_targets["count_match_percent"])
        factor = QDoubleSpinBox()
        factor.setRange(0, 100)
        factor.setValue(self.user_targets["match_factor"])
        layout.addWidget(QLabel("Count Match %"), 0, 0)
        layout.addWidget(count, 0, 1)
        layout.addWidget(QLabel("Match Factor"), 1, 0)
        layout.addWidget(factor, 1, 1)
        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(dialog.accept)
        layout.addWidget(apply_button, 2, 1)
        if (dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()) == QDialog.Accepted:
            self.user_targets = {"count_match_percent": count.value(), "match_factor": factor.value()}
            if self.last_result:
                self._refresh_result_table()

    def _edit_product_parameters(self):
        dialog = MatchingParametersDialog(self.parameters, self.settings.get("default_product_parameters"), self)
        if (dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()) == QDialog.Accepted:
            self.parameters = dialog.result_parameters
            self.settings["product_parameters"] = deepcopy(self.parameters)
            self.settings["default_product_parameters"] = deepcopy(dialog.default_parameters)

    def _edit_dsw_parameters(self):
        dialog = DSWMatchParametersDialog(self.dsw_parameters, self)
        if (dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()) == QDialog.Accepted:
            self.dsw_parameters = dialog.result_parameters
            self.settings["dsw_parameters"] = deepcopy(self.dsw_parameters)

    def _view_result(self):
        if not self.last_result:
            QMessageBox.information(self, "Inspection Matching", "Run a match before opening Review or Graph.")
            return
        dialog = MatchDetailDialog(str(self.last_result.get("type", "Matching Review")), self.last_result, self)
        dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()

    def _set_color_by(self, label):
        for action in self.color_actions:
            action.setChecked(action.text() == label)
        self.settings["color_by"] = label

    def _session_payload(self):
        return {
            "parameters": self.parameters,
            "dsw_parameters": self.dsw_parameters,
            "user_targets": self.user_targets,
            "selections": self.selections,
            "last_result": self.last_result,
            "active_mode": self.tabs.currentIndex(),
        }

    def _new_session(self):
        self.selections = []
        self.last_result = None
        self.current_session_path = None
        self.match_progress.setValue(0)
        self.result_table.setRowCount(0)
        self._refresh_selections()
        self.review_action.setEnabled(False)
        self.graph_action.setEnabled(False)
        self.status_label.setText("New inspection matching session")

    def _open_session(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Open Inspection Matching Session", "", "Matching Session (*.json)")
        if not filename:
            return
        try:
            payload = json.loads(Path(filename).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Open Inspection Matching Session", str(exc))
            return
        self.parameters = normalize_matching_parameters(payload.get("parameters"))
        self.dsw_parameters = normalize_dsw_parameters(payload.get("dsw_parameters"))
        self.user_targets.update(payload.get("user_targets", {}))
        self.selections = list(payload.get("selections", []))
        self.last_result = payload.get("last_result")
        self.tabs.setCurrentIndex(max(0, min(2, int(payload.get("active_mode", 0)))))
        self.current_session_path = Path(filename)
        self._refresh_selections()
        if self.last_result:
            self._refresh_result_table()
            self.review_action.setEnabled(True)
        self.status_label.setText(f"Opened {filename}")

    def _save_session(self, save_as=False):
        path = self.current_session_path
        if save_as or path is None:
            filename, _ = QFileDialog.getSaveFileName(self, "Save Inspection Matching Session", "matching-session.json", "Matching Session (*.json)")
            if not filename:
                return
            path = Path(filename)
        path.write_text(json.dumps(self._session_payload(), indent=2, default=str), encoding="utf-8")
        self.current_session_path = path
        self.status_label.setText(f"Saved {path}")

    def _save_result(self):
        if not self.last_result:
            QMessageBox.information(self, "Save Result", "Run a match before saving a result.")
            return
        filename, _ = QFileDialog.getSaveFileName(self, "Save Result", "matching-result.json", "JSON Result (*.json)")
        if filename:
            Path(filename).write_text(json.dumps(self.last_result, indent=2, default=str), encoding="utf-8")

    def _export_result(self):
        if not self.last_result:
            QMessageBox.information(self, "Export", "Run a match before exporting results.")
            return
        filename, _ = QFileDialog.getSaveFileName(self, "Export Inspection Matching", "matching-summary.csv", "Excel-compatible CSV (*.csv)")
        if not filename:
            return
        with Path(filename).open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.writer(stream)
            writer.writerow(["Metric", "Value"])
            for key, value in self.last_result.items():
                if key != "pairs":
                    writer.writerow([key, value])
        self.status_label.setText(f"Exported {filename}")

    def _browse_conformance_spec(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Open DSW Conformance Specification", "", "CSV (*.csv)")
        if filename:
            self.conformance_spec.setText(filename)

    def _exit(self):
        if self.last_result and self.current_session_path is None:
            choice = QMessageBox.question(
                self,
                "Save Confirmation",
                "The inspection matching session has not been saved. Exit?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if choice != QMessageBox.Yes:
                return
        self.accept()


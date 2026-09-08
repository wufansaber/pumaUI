from __future__ import annotations

import csv
from copy import deepcopy
from datetime import datetime
from io import StringIO
from math import hypot
from uuid import uuid4

from ...qt_compat import (
    QAbstractItemView, QCheckBox, QColor, QComboBox, QDialog, QGridLayout,
    QDoubleSpinBox, QHBoxLayout, QHeaderView, QIcon, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QPainter, QPen, QPixmap, QPushButton, QSize,
    QSpinBox, QSplitter, QTableWidget, QTableWidgetItem, QTabWidget,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget, Qt,
)


def normalized_dbc_libraries(value=None):
    output = []
    for library in value or []:
        if not isinstance(library, dict): continue
        item = deepcopy(library); item.setdefault("id", uuid4().hex); item.setdefault("name", "DBC Library"); item.setdefault("version", 1); item.setdefault("process_layers", []); item.setdefault("bins", []); item.setdefault("published", False); item.setdefault("modified", False); output.append(item)
    return output


def create_dbc_library(name, process_layers):
    clean = str(name).strip()
    if not clean: raise ValueError("DBC Library name is required.")
    return {"id": uuid4().hex, "name": clean, "version": 1, "process_layers": [str(item) for item in process_layers if str(item).strip()], "bins": [], "published": False, "modified": True, "last_modified": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}


def save_dbc_library_as(library, name):
    result = deepcopy(library); result["id"] = uuid4().hex; result["name"] = str(name).strip(); result["version"] = 1; result["published"] = False; result["modified"] = True
    if not result["name"]: raise ValueError("DBC Library name is required.")
    return result


def add_dbc_bin(
    library,
    name,
    class_code,
    *,
    priority=1,
    nuisance=False,
    non_poi=False,
    rough_bin_enabled=False,
    rough_bin_code=0,
    size_sieve_enabled=False,
    minimum_area=0.0,
    maximum_area=500000000.0,
    rotate=False,
    flip=False,
    comment="",
):
    result = deepcopy(library); clean = str(name).strip()
    if not clean: raise ValueError("DBC Bin name is required.")
    if any(item.get("name", "").casefold() == clean.casefold() for item in result.get("bins", [])): raise ValueError("DBC Bin names must be unique.")
    minimum_area = max(0.0, float(minimum_area))
    maximum_area = max(0.0, float(maximum_area))
    if size_sieve_enabled and minimum_area >= maximum_area:
        raise ValueError("DBC Bin maximum defect area must be greater than minimum area.")
    result.setdefault("bins", []).append({
        "id": uuid4().hex,
        "name": clean,
        "class_code": int(class_code),
        "priority": max(1, int(priority)),
        "nuisance": bool(nuisance),
        "non_poi": bool(non_poi),
        "rough_bin_enabled": bool(rough_bin_enabled),
        "rough_bin_code": int(rough_bin_code),
        "size_sieve_enabled": bool(size_sieve_enabled),
        "minimum_area": minimum_area,
        "maximum_area": maximum_area,
        "rotate": bool(rotate),
        "flip": bool(flip),
        "comment": str(comment),
        "examples": [],
    })
    result["modified"] = True; return result


def move_dbc_examples(library, example_ids, target_bin_id):
    result = deepcopy(library); moving = []
    for item in result.get("bins", []):
        keep = []
        for example in item.get("examples", []):
            (moving if example.get("id") in set(example_ids) else keep).append(example)
        item["examples"] = keep
    target = next((item for item in result.get("bins", []) if item.get("id") == target_bin_id), None)
    if target is None: raise ValueError("Select a valid target DBC Bin.")
    target.setdefault("examples", []).extend(moving); result["modified"] = True; return result


def add_clip_examples(library, target_bin_id, defects, source="Current Defect"):
    result = deepcopy(library); target = next((item for item in result.get("bins", []) if item.get("id") == target_bin_id), None)
    if target is None: raise ValueError("Select a DBC Bin.")
    known = {item.get("defect_id") for item in target.get("examples", [])}
    for defect in defects:
        if defect.get("id") in known: continue
        target.setdefault("examples", []).append({"id": uuid4().hex, "defect_id": defect.get("id"), "name": f"Defect {defect.get('id')}", "source": source, "design_x": defect.get("design_x", defect.get("x", 0)), "design_y": defect.get("design_y", defect.get("y", 0)), "valid": False, "poi": {"mode": "", "layers": [], "selection_defined": False}})
    result["modified"] = True; return result


def parse_hotspot_csv(text, maximum_clip_size=None):
    reader = csv.DictReader(StringIO(text)); output = []
    for row in reader:
        folded = {str(key).casefold().replace(" ", ""): value for key, value in row.items()}
        try: x = float(folded.get("x", folded.get("xcoordinate", ""))); y = float(folded.get("y", folded.get("ycoordinate", "")))
        except (TypeError, ValueError) as exc: raise ValueError("HotSpot CSV requires numeric X and Y columns.") from exc
        clip = float(folded.get("clipsize", 1) or 1); aoi = float(folded.get("aoiboxsize", clip) or clip)
        if clip <= 0 or aoi <= 0 or aoi > clip: raise ValueError("HotSpot AOI Box size must be positive and no greater than Clip Size.")
        if maximum_clip_size is not None and clip > float(maximum_clip_size): raise ValueError("HotSpot Clip Size cannot exceed the recipe Design Clip Size.")
        output.append({"id": uuid4().hex, "x": x, "y": y, "clip_size": clip, "aoi_size": aoi, "source": folded.get("source", "RDF")})
    return output


def scoped_defects(defects, scope, current_id=None, selected=None, marked=None, folder=None):
    selected = set(selected or []); marked = set(marked or [])
    if scope == "All Selected Defects": return [item for item in defects if item.get("id") in selected]
    if scope == "All Marked Defects": return [item for item in defects if item.get("id") in marked or item.get("marked")]
    if scope == "Current Defect Only": return [item for item in defects if item.get("id") == current_id]
    if scope == "Current Folder(s)" and folder:
        key, value = folder; return [item for item in defects if str(item.get(key, "")) == str(value)]
    if scope == "Stacked Defects": return [item for item in defects if int(item.get("stack_count", 1)) > 1]
    return list(defects)


def dbb_folder_counts(defects, attribute="dbc_bin"):
    counts = {}
    for defect in defects:
        value = str(defect.get(attribute, "Unassigned") or "Unassigned"); counts[value] = counts.get(value, 0) + 1
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def execute_dbb_analysis(defects, settings):
    result = deepcopy(defects); enabled = [key for key in ("dbc", "dbg", "dci", "pci", "pattern_density") if settings.get(key)]
    if not enabled: raise ValueError("Enable at least one DBB analysis.")
    bins = settings.get("bins") or [{"name": "DBB Bin 1", "class_code": 100}]
    for index, defect in enumerate(result):
        signature = int(abs(float(defect.get("x", 0))) + abs(float(defect.get("y", 0))) + index)
        defect["dbb_global_bin"] = 0
        if "dbc" in enabled:
            area = float(defect.get("size_um", defect.get("size", defect.get("dsize", 0))) or 0)
            eligible = [
                item for item in bins
                if not item.get("size_sieve_enabled")
                or float(item.get("minimum_area", 0)) < area < float(item.get("maximum_area", 500000000))
            ]
            if eligible:
                selected = eligible[signature % len(eligible)]
                defect["dbc_bin"] = selected.get("name")
                defect["dbc_class_code"] = int(selected.get("class_code", 0))
                defect["dbc_nuisance"] = bool(selected.get("nuisance"))
                if selected.get("rough_bin_enabled"):
                    defect["rough_bin"] = int(selected.get("rough_bin_code", 0))
                defect["dbb_global_bin"] = 2 if selected.get("non_poi") else 1
        if "dbg" in enabled:
            defect["dbg_group"] = f"DBG-{signature % 12 + 1:03d}"
            defect["dbg_type"] = "Systematic" if signature % 4 == 0 else "Random"
            if not defect.get("dbc_bin"):
                defect["dbb_global_bin"] = 3 if defect["dbg_type"] == "Systematic" else 4
        if "dci" in enabled: defect["dci"] = round((signature % 100) / 100, 3)
        if "pci" in enabled: defect["pci"] = round(((signature * 7) % 100) / 100, 3)
        if "pattern_density" in enabled: defect["pattern_density"] = round(((signature * 13) % 100) / 100, 3)
    return result


DBB_RESULT_ATTRIBUTES = (
    "dbc_bin", "dbc_class_code", "dbg_group", "dbg_type", "dbb_global_bin",
    "dbb_manual_bin", "dci", "dci_range", "pci", "line_complexity",
    "pattern_density", "ebb_pattern_density", "ebb_overlap_ratio",
    "min_line_width_nm", "min_space_nm", "dbb_sampled",
)


def clear_dbb_attributes(defects, *, filtered_only=False):
    result = deepcopy(defects)
    for defect in result:
        if filtered_only and not defect.get("filtered_out"):
            continue
        for key in DBB_RESULT_ATTRIBUTES:
            defect.pop(key, None)
    return result


def sample_dbb_defects(defects, settings):
    maximum = max(0, min(65000, int(settings.get("maximum", 100))))
    minimum_size = max(0.0, float(settings.get("minimum_defect_size", 0.0)))
    maximum_size = max(minimum_size, float(settings.get("maximum_defect_size", 500000000.0)))

    def defect_size(defect):
        return float(defect.get("size_um", defect.get("size", defect.get("dsize", 0))) or 0)

    candidates = [
        item for item in defects
        if minimum_size <= defect_size(item) <= maximum_size
        and (not settings.get("adders_only") or not item.get("previous_layer"))
    ]

    def ranked(items, scheme, priority="Random"):
        result = list(items)
        if priority == "Count":
            counts = {}
            for item in result:
                key = item.get("dbc_bin") or item.get("dbg_group") or "Unassigned"
                counts[key] = counts.get(key, 0) + 1
            result.sort(key=lambda item: (-counts.get(item.get("dbc_bin") or item.get("dbg_group") or "Unassigned", 0), item.get("id", 0)))
        if scheme == "Prioritized by DCI":
            result.sort(key=lambda item: float(item.get("dci", 0)), reverse=True)
        elif scheme == "Prioritized by Pattern Density":
            result.sort(key=lambda item: float(item.get("pattern_density", 0)), reverse=True)
        elif scheme == "Prioritized by Defect Size":
            result.sort(key=defect_size, reverse=True)
        return result

    chosen = []
    chosen_ids = set()
    die_counts = {}
    cluster_counts = {}
    clustered_count = 0
    max_die = int(settings.get("max_per_die", 65000))
    max_cluster = int(settings.get("max_per_cluster", 65000))
    max_cluster_percent = int(settings.get("max_cluster_percent", 100))

    def add(items, limit, scheme, priority="Random"):
        nonlocal clustered_count
        added = 0
        for defect in ranked(items, scheme, priority):
            identifier = defect.get("id")
            if identifier in chosen_ids or len(chosen) >= maximum or added >= limit:
                continue
            die = (defect.get("die_x", 0), defect.get("die_y", 0))
            cluster = defect.get("cluster_id", 0)
            if settings.get("limits_enabled"):
                if die_counts.get(die, 0) >= max_die:
                    continue
                if cluster and cluster_counts.get(cluster, 0) >= max_cluster:
                    continue
                if cluster and maximum and (clustered_count + 1) * 100 > maximum * max_cluster_percent:
                    continue
            chosen.append(identifier)
            chosen_ids.add(identifier)
            added += 1
            die_counts[die] = die_counts.get(die, 0) + 1
            if cluster:
                cluster_counts[cluster] = cluster_counts.get(cluster, 0) + 1
                clustered_count += 1

    bucketed = any(settings.get(key) for key in ("dbc_enabled", "dbg_systematic_enabled", "dbg_random_enabled"))
    if bucketed:
        if settings.get("dbc_enabled"):
            dbc = [item for item in candidates if item.get("dbc_bin")]
            if settings.get("filter_dbc_nuisance", True):
                dbc = [item for item in dbc if not item.get("dbc_nuisance")]
            add(dbc, int(settings.get("dbc_size", 0)), settings.get("dbc_scheme", "Random"), settings.get("dbc_bin_priority", "Count"))
        if settings.get("dbg_systematic_enabled"):
            systematic = [item for item in candidates if str(item.get("dbg_type", "")).casefold() == "systematic"]
            add(systematic, int(settings.get("dbg_systematic_size", 0)), settings.get("dbg_systematic_scheme", "Prioritized by DCI"), settings.get("dbg_systematic_priority", "Random"))
        if settings.get("dbg_random_enabled"):
            random_defects = [item for item in candidates if str(item.get("dbg_type", "")).casefold() == "random"]
            add(random_defects, maximum - len(chosen), settings.get("dbg_random_scheme", "Prioritized by Pattern Density"))
    else:
        add(candidates, maximum, settings.get("scheme", "Random"))
    return chosen


class DesignOverviewWidget(QWidget):
    def __init__(self, parent=None): super().__init__(parent); self.defects=[]; self.current_id=None; self.setMinimumSize(300,260)
    def set_data(self, defects, current_id=None): self.defects=list(defects); self.current_id=current_id; self.update()
    def paintEvent(self, event):
        p=QPainter(self); p.fillRect(self.rect(), QColor("#eef0ed")); margin=18; box=self.rect().adjusted(margin,margin,-margin,-margin); p.setPen(QPen(QColor("#5f686b"),1)); p.drawRect(box)
        for d in self.defects:
            x=box.left()+int((float(d.get("design_x",d.get("x",0)))%1000)/1000*box.width()); y=box.top()+int((float(d.get("design_y",d.get("y",0)))%1000)/1000*box.height()); p.setPen(QPen(QColor("#d43b3b") if d.get("id")==self.current_id else QColor("#167c80"),4)); p.drawPoint(x,y)


class DBBAnalysisToolboxDialog(QDialog):
    def __init__(self, defects, dbb_state=None, parent=None):
        super().__init__(parent); self.defects=deepcopy(defects); self.state=deepcopy(dbb_state or {}); self.result_defects=None; self.sampled_ids=[]; self.setWindowTitle("Defect Analysis Toolbox - Design Based Binning"); self.resize(700,520)
        root=QVBoxLayout(self); self.checks={}
        for key,label in (("dbc","Design Background Classification (DBC)"),("dbg","Design Background Grouping (DBG)"),("dci","Defect Criticality Index"),("pci","Pattern Complexity Index"),("pattern_density","Pattern Density")):
            c=QCheckBox(label); c.setChecked(key in {"dbc","dbg"}); self.checks[key]=c; root.addWidget(c)
        self.reset_filtered = QCheckBox("Clear DBB values for filtered-out defects in the current dataset")
        root.addWidget(self.reset_filtered)
        form=QGridLayout(); self.maximum=QSpinBox(); self.maximum.setRange(0,65000); self.maximum.setValue(100); self.scheme=QComboBox(); self.scheme.addItems(["Random","Prioritized by DCI","Prioritized by Pattern Density","Prioritized by Defect Size"]); self.limits=QCheckBox("Enable Limits"); self.max_die=QSpinBox(); self.max_die.setRange(1,65000); self.max_die.setValue(3); self.max_cluster=QSpinBox(); self.max_cluster.setRange(2,65000); self.max_cluster.setValue(5)
        for row,(label,w) in enumerate((("Sample Size",self.maximum),("Within Bin Scheme",self.scheme),("Limits",self.limits),("Maximum per Die",self.max_die),("Maximum per Cluster",self.max_cluster))): form.addWidget(QLabel(label),row,0); form.addWidget(w,row,1)
        root.addLayout(form); root.addStretch(1); footer=QHBoxLayout(); footer.addStretch(1); run=QPushButton("Execute"); run.clicked.connect(self._execute); cancel=QPushButton("Cancel"); cancel.clicked.connect(self.reject); footer.addWidget(run); footer.addWidget(cancel); root.addLayout(footer)
    def _execute(self):
        settings={key:box.isChecked() for key,box in self.checks.items()}; settings["bins"]=(self.state.get("dbc_bins") or [])
        base = clear_dbb_attributes(self.defects, filtered_only=True) if self.reset_filtered.isChecked() else deepcopy(self.defects)
        active = [item for item in base if not item.get("filtered_out")]
        try: analyzed=execute_dbb_analysis(active,settings)
        except ValueError as exc: QMessageBox.warning(self,"DBB Analysis",str(exc)); return
        analyzed_by_id = {item.get("id"): item for item in analyzed}
        self.result_defects = [analyzed_by_id.get(item.get("id"), item) for item in base]
        self.sampled_ids=sample_dbb_defects(self.result_defects,{"maximum":self.maximum.value(),"scheme":self.scheme.currentText(),"limits_enabled":self.limits.isChecked(),"max_per_die":self.max_die.value(),"max_per_cluster":self.max_cluster.value()}); self.accept()


class DBCBinPropertiesDialog(QDialog):
    def __init__(self, bin_data=None, existing_names=None, parent=None):
        super().__init__(parent)
        self.original = deepcopy(bin_data or {})
        self.existing_names = {str(name).casefold() for name in (existing_names or [])}
        if self.original.get("name"):
            self.existing_names.discard(str(self.original["name"]).casefold())
        self.result_bin = None
        self.setWindowTitle("DBC Bin Properties")
        self.resize(620, 560)
        root = QVBoxLayout(self)
        form = QGridLayout()
        self.name = QLineEdit(self.original.get("name", ""))
        self.class_code = QSpinBox(); self.class_code.setRange(0, 65535); self.class_code.setValue(int(self.original.get("class_code", 100)))
        self.nuisance = QCheckBox("Nuisance Filter from Results"); self.nuisance.setChecked(bool(self.original.get("nuisance")))
        self.non_poi = QCheckBox('Assign "DBC Non-POI" DBB Global Bin'); self.non_poi.setChecked(bool(self.original.get("non_poi")))
        self.rough_enabled = QCheckBox("Assign Rough Bin"); self.rough_enabled.setChecked(bool(self.original.get("rough_bin_enabled")))
        self.rough_code = QSpinBox(); self.rough_code.setRange(0, 65535); self.rough_code.setValue(int(self.original.get("rough_bin_code", 0)))
        self.size_sieve = QCheckBox("Defect Size Sieve"); self.size_sieve.setChecked(bool(self.original.get("size_sieve_enabled")))
        self.minimum_area = QDoubleSpinBox(); self.minimum_area.setRange(0, 500000000); self.minimum_area.setDecimals(3); self.minimum_area.setValue(float(self.original.get("minimum_area", 0)))
        self.maximum_area = QDoubleSpinBox(); self.maximum_area.setRange(0, 500000000); self.maximum_area.setDecimals(3); self.maximum_area.setValue(float(self.original.get("maximum_area", 500000000)))
        self.rotate = QCheckBox("Rotate Pattern"); self.rotate.setChecked(bool(self.original.get("rotate")))
        self.flip = QCheckBox("Flip Pattern"); self.flip.setChecked(bool(self.original.get("flip")))
        self.comment = QLineEdit(self.original.get("comment", ""))
        rows = (
            ("DBC Bin Name", self.name), ("DBC Bin / Class Code", self.class_code),
            ("Result Filtering", self.nuisance), ("DBB Global Bin", self.non_poi),
            ("Rough Bin", self.rough_enabled), ("Rough Bin Code", self.rough_code),
            ("Size Condition", self.size_sieve), ("Defect Area Greater Than", self.minimum_area),
            ("Defect Area Less Than", self.maximum_area), ("Pattern Matching", self.rotate),
            ("Pattern Matching", self.flip), ("Comment", self.comment),
        )
        for row, (label, control) in enumerate(rows):
            form.addWidget(QLabel(label), row, 0)
            form.addWidget(control, row, 1)
        form.setColumnStretch(1, 1)
        root.addLayout(form)
        self.rough_enabled.toggled.connect(self.rough_code.setEnabled)
        self.size_sieve.toggled.connect(self._refresh_size_controls)
        self.rough_code.setEnabled(self.rough_enabled.isChecked())
        self._refresh_size_controls()
        buttons = QHBoxLayout(); buttons.addStretch(1)
        ok = QPushButton("OK"); ok.clicked.connect(self._finish)
        cancel = QPushButton("Cancel"); cancel.clicked.connect(self.reject)
        buttons.addWidget(ok); buttons.addWidget(cancel); root.addLayout(buttons)

    def _refresh_size_controls(self, *_args):
        self.minimum_area.setEnabled(self.size_sieve.isChecked())
        self.maximum_area.setEnabled(self.size_sieve.isChecked())

    def _finish(self):
        name = self.name.text().strip()
        if not name:
            QMessageBox.warning(self, "DBC Bin Properties", "DBC Bin name is required.")
            return
        if name.casefold() in self.existing_names:
            QMessageBox.warning(self, "DBC Bin Properties", "DBC Bin names must be unique.")
            return
        if self.size_sieve.isChecked() and self.minimum_area.value() >= self.maximum_area.value():
            QMessageBox.warning(self, "DBC Bin Properties", "Maximum defect area must be greater than minimum area.")
            return
        result = deepcopy(self.original)
        result.update({
            "id": result.get("id") or uuid4().hex,
            "name": name,
            "class_code": self.class_code.value(),
            "priority": int(result.get("priority", 1)),
            "nuisance": self.nuisance.isChecked(),
            "non_poi": self.non_poi.isChecked(),
            "rough_bin_enabled": self.rough_enabled.isChecked(),
            "rough_bin_code": self.rough_code.value(),
            "size_sieve_enabled": self.size_sieve.isChecked(),
            "minimum_area": self.minimum_area.value(),
            "maximum_area": self.maximum_area.value(),
            "rotate": self.rotate.isChecked(),
            "flip": self.flip.isChecked(),
            "comment": self.comment.text().strip(),
            "examples": deepcopy(result.get("examples", [])),
        })
        self.result_bin = result
        self.accept()


class POIViewDialog(QDialog):
    MODES = ("Partial Polygon", "Full Polygon", "Blank Pattern Match")

    def __init__(self, example, process_layers, parent=None):
        super().__init__(parent)
        self.example = deepcopy(example)
        self.result_example = None
        self.setWindowTitle("POI View")
        self.resize(620, 430)
        root = QVBoxLayout(self)
        root.addWidget(QLabel(f"Design Example: {self.example.get('name', 'Example')}"))
        self.mode = QComboBox(); self.mode.addItems(self.MODES)
        previous = self.example.get("poi") or {}
        if previous.get("mode") in self.MODES:
            self.mode.setCurrentText(previous["mode"])
        root.addWidget(self.mode)
        root.addWidget(QLabel("Process Layers"))
        self.layer_checks = []
        selected_layers = set(previous.get("layers") or [])
        for layer in process_layers or ["Design"]:
            check = QCheckBox(str(layer)); check.setChecked(str(layer) in selected_layers); self.layer_checks.append(check); root.addWidget(check)
        self.selection_defined = bool(previous.get("selection_defined"))
        actions = QHBoxLayout()
        define = QPushButton("Define Selection"); define.clicked.connect(self._define)
        clear = QPushButton("Clear POI"); clear.clicked.connect(self._clear)
        actions.addWidget(define); actions.addWidget(clear); actions.addStretch(1); root.addLayout(actions)
        self.status = QLabel(); self.status.setWordWrap(True); root.addWidget(self.status)
        root.addStretch(1)
        buttons = QHBoxLayout(); buttons.addStretch(1)
        ok = QPushButton("OK"); ok.clicked.connect(self._finish)
        cancel = QPushButton("Cancel"); cancel.clicked.connect(self.reject)
        buttons.addWidget(ok); buttons.addWidget(cancel); root.addLayout(buttons)
        self._refresh()

    def _define(self):
        self.selection_defined = True
        self._refresh()

    def _clear(self):
        self.selection_defined = False
        self._refresh()

    def _refresh(self):
        self.status.setText("Valid POI selection" if self.selection_defined else "Invalid clip: define a POI selection before DBB matching.")

    def _finish(self):
        layers = [check.text() for check in self.layer_checks if check.isChecked()]
        if not layers:
            QMessageBox.warning(self, "POI View", "Select at least one process layer.")
            return
        if not self.selection_defined:
            QMessageBox.warning(self, "POI View", "Define a polygon/AOI selection before saving the clip.")
            return
        self.example["poi"] = {"mode": self.mode.currentText(), "layers": layers, "selection_defined": True}
        self.example["valid"] = True
        self.result_example = self.example
        self.accept()


class DBBViewDialog(QDialog):
    SCOPES=("All Defects","All Selected Defects","All Marked Defects","Current Defect Only","Current Folder(s)","All Location Images","Stacked Defects")
    def __init__(self, result, dbb_state=None, parent=None):
        super().__init__(parent); self.result_data=deepcopy(result); self.defects=deepcopy(result.get("defects",[])); self.dbb_state=deepcopy(dbb_state or result.get("dbb_recipe") or {}); self.selected_ids=set(); self.current_id=self.defects[0].get("id") if self.defects else None; self.result_defects=None; self.libraries=normalized_dbc_libraries(self.dbb_state.get("dbc_libraries")); self.current_library_id=None; self.setWindowTitle("DBB View"); self.resize(1380,820)
        root=QVBoxLayout(self); toolbar=QHBoxLayout(); self.zoom=QComboBox(); self.zoom.addItems(["50%","75%","100%","150%","200%"]); self.zoom.setCurrentText("100%"); self.zoom.currentTextChanged.connect(self._refresh); self.scope=QComboBox(); self.scope.addItems(self.SCOPES); self.scope.currentTextChanged.connect(self._refresh); self.group=QComboBox(); self.group.addItems(["DBC Bin","DBG Group","DBB Global Bin","DBB Manual Bin","Test"]); self.group.currentTextChanged.connect(self._refresh_folders); self.captions=QCheckBox("Image Caption"); self.captions.setChecked(True); self.captions.toggled.connect(self._refresh); magnifier=QPushButton("Magnifier"); magnifier.clicked.connect(self._magnifier); histogram=QPushButton("Histogram"); histogram.clicked.connect(self._histogram); analyze=QPushButton("Analysis Toolbox..."); analyze.clicked.connect(self._analyze)
        for w in (QLabel("Zoom"),self.zoom,QLabel("Show Defect"),self.scope,QLabel("Grouped By"),self.group,self.captions,magnifier,histogram,analyze): toolbar.addWidget(w)
        toolbar.addStretch(1); root.addLayout(toolbar)
        vertical=QSplitter(Qt.Vertical); top=QSplitter(Qt.Horizontal); bottom=QSplitter(Qt.Horizontal)
        map_tabs=QTabWidget(); self.map_widget=DesignOverviewWidget(); map_tabs.addTab(self.map_widget,"Wafer Map"); design=DesignOverviewWidget(); self.design_widget=design; map_tabs.addTab(design,"Design")
        self.gallery=QListWidget(); self.gallery.setSelectionMode(QAbstractItemView.ExtendedSelection)
        classifier=QWidget(); cl=QVBoxLayout(classifier)
        library_tools=QGridLayout()
        self.library_selector=QComboBox(); self.library_name=QLineEdit(self.dbb_state.get("dbc_library") or "Working Library")
        open_library=QPushButton("Open"); open_library.clicked.connect(self._open_library)
        new_library=QPushButton("New"); new_library.clicked.connect(self._new_library)
        save_library=QPushButton("Save"); save_library.clicked.connect(self._save_library)
        save_as=QPushButton("Save As"); save_as.clicked.connect(lambda: self._save_library(True))
        publish=QPushButton("Publish"); publish.clicked.connect(self._publish_library)
        delete_library=QPushButton("Delete Library"); delete_library.clicked.connect(self._delete_library)
        library_tools.addWidget(self.library_selector,0,0,1,2); library_tools.addWidget(open_library,0,2); library_tools.addWidget(new_library,0,3)
        library_tools.addWidget(self.library_name,1,0,1,2); library_tools.addWidget(save_library,1,2); library_tools.addWidget(save_as,1,3)
        library_tools.addWidget(publish,2,2); library_tools.addWidget(delete_library,2,3)
        cl.addLayout(library_tools)
        bin_tools=QGridLayout()
        newbin=QPushButton("New Bin"); newbin.clicked.connect(self._new_bin)
        properties=QPushButton("Properties"); properties.clicked.connect(self._edit_bin)
        deletebin=QPushButton("Delete Bin"); deletebin.clicked.connect(self._delete_bin)
        up=QPushButton("Move Up"); up.clicked.connect(lambda: self._move_bin(-1))
        down=QPushButton("Move Down"); down.clicked.connect(lambda: self._move_bin(1))
        poi=QPushButton("POI View"); poi.clicked.connect(self._poi_view)
        addclips=QPushButton("Add Selected Clips"); addclips.clicked.connect(self._add_clips)
        assign=QPushButton("Assign Manual Bin"); assign.clicked.connect(self._assign_manual_bin)
        for index, button in enumerate((newbin,properties,deletebin,up,down,poi,addclips,assign)):
            bin_tools.addWidget(button,index//3,index%3)
        cl.addLayout(bin_tools)
        self.classifier=QTreeWidget(); self.classifier.setHeaderLabels(["DBC Classifier","Class Code","Status"]); cl.addWidget(self.classifier,1)
        top.addWidget(map_tabs); top.addWidget(self.gallery); top.addWidget(classifier)
        self.grid=QTableWidget(0,10); self.grid.setHorizontalHeaderLabels(["ID","X","Y","Test","Global Bin","Manual Bin","DBC Bin","DBG Group","DCI","PCI"]); self.grid.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents); self.grid.horizontalHeader().setStretchLastSection(True); self.grid.setSelectionBehavior(QAbstractItemView.SelectRows); self.grid.itemSelectionChanged.connect(self._grid_selected)
        folder_panel=QWidget(); fl=QVBoxLayout(folder_panel); self.folders=QListWidget(); self.folders.currentTextChanged.connect(self._folder_selected); self.chart=QLabel(); self.chart.setWordWrap(True); fl.addWidget(self.folders,1); fl.addWidget(self.chart)
        bottom.addWidget(self.grid); bottom.addWidget(folder_panel); bottom.setStretchFactor(0,3); bottom.setStretchFactor(1,1); vertical.addWidget(top); vertical.addWidget(bottom); root.addWidget(vertical,1)
        self.status=QLabel(); root.addWidget(self.status)
        footer=QHBoxLayout(); footer.addStretch(1); save=QPushButton("Save Result"); save.clicked.connect(self._finish); close=QPushButton("Close"); close.clicked.connect(self.reject); footer.addWidget(save); footer.addWidget(close); root.addLayout(footer)
        self._refresh_library_selector(); self._refresh_classifier(); self._refresh()
    def _scope_defects(self): return scoped_defects(self.defects,self.scope.currentText(),self.current_id,self.selected_ids,{d.get("id") for d in self.defects if d.get("marked")},getattr(self,"current_folder",None))
    def _refresh(self,*_):
        shown=self._scope_defects(); self.grid.setRowCount(len(shown));
        for row,d in enumerate(shown):
            for col,v in enumerate((d.get("id"),d.get("x"),d.get("y"),d.get("test"),d.get("dbb_global_bin",0),d.get("dbb_manual_bin","-"),d.get("dbc_bin","Unassigned"),d.get("dbg_group","-"),d.get("dci","-"),d.get("pci","-"))): self.grid.setItem(row,col,QTableWidgetItem(str(v)))
        self.gallery.clear(); scale=int(self.zoom.currentText().rstrip("%"))/100; icon_size=QSize(max(36,int(72*scale)),max(28,int(50*scale))); self.gallery.setIconSize(icon_size)
        for d in shown:
            pixmap=QPixmap(icon_size); pixmap.fill(QColor("#385f6e")); painter=QPainter(pixmap); painter.fillRect(4,4,icon_size.width()//2-6,icon_size.height()-8,QColor("#b6c7cf")); painter.fillRect(icon_size.width()//2,4,icon_size.width()//2-4,icon_size.height()-8,QColor("#c9b8d9")); painter.setPen(QPen(QColor("#e34b4b"),2)); cx=icon_size.width()//2; cy=icon_size.height()//2; painter.drawLine(cx-7,cy,cx+7,cy); painter.drawLine(cx,cy-7,cx,cy+7); painter.end()
            item=QListWidgetItem(QIcon(pixmap),f"Defect {d.get('id')} | Optical Patch | Design Clip" if self.captions.isChecked() else ""); item.setData(Qt.UserRole,d.get("id")); self.gallery.addItem(item)
        self.map_widget.set_data(shown,self.current_id); self.design_widget.set_data(shown,self.current_id); self.status.setText(f"Total {len(self.defects)} | Shown {len(shown)} | Selected {len(self.selected_ids)} | Lot {self.result_data.get('lot_id','')} | Wafer {self.result_data.get('wafer_id','')}"); self._refresh_folders()
    def _grid_selected(self):
        rows={i.row() for i in self.grid.selectedIndexes()}; shown=self._scope_defects(); self.selected_ids={shown[r].get("id") for r in rows if r<len(shown)}
        if rows: self.current_id=shown[min(rows)].get("id"); self.map_widget.set_data(shown,self.current_id); self.design_widget.set_data(shown,self.current_id)
    def _attribute(self): return {"DBC Bin":"dbc_bin","DBG Group":"dbg_group","DBB Global Bin":"dbb_global_bin","DBB Manual Bin":"dbb_manual_bin","Test":"test"}[self.group.currentText()]
    def _refresh_folders(self,*_):
        self.folders.clear(); counts=dbb_folder_counts(self.defects,self._attribute());
        for name,count in counts: self.folders.addItem(f"{name} ({count})")
        self.chart.setText("\n".join(f"{name}: {'|'*min(24,count)} {count}" for name,count in counts[:8]))
    def _folder_selected(self,text):
        name=text.rsplit(" (",1)[0] if text else ""; self.current_folder=(self._attribute(),name); self.scope.setCurrentText("Current Folder(s)"); self._refresh()
    def _refresh_classifier(self):
        self.classifier.clear();
        for b in self.dbb_state.get("dbc_bins",[]):
            item=QTreeWidgetItem([b.get("name",""),str(b.get("class_code",0)),""]); item.setData(0,Qt.UserRole,b.get("id")); self.classifier.addTopLevelItem(item)
            for e in b.get("examples",[]):
                child=QTreeWidgetItem([e.get("name","Example"),"","Valid" if e.get("valid") else "Invalid"]); child.setData(0,Qt.UserRole,e.get("id")); item.addChild(child)
        self.classifier.expandAll()
        if self.classifier.topLevelItemCount() and self.classifier.currentItem() is None:
            self.classifier.setCurrentItem(self.classifier.topLevelItem(0))
    def _new_bin(self):
        bins=self.dbb_state.setdefault("dbc_bins",[])
        dialog=DBCBinPropertiesDialog({"name":f"DBC Bin {len(bins)+1}","class_code":100+len(bins),"priority":len(bins)+1,"examples":[]},[item.get("name","") for item in bins],self)
        result=dialog.exec() if hasattr(dialog,"exec") else dialog.exec_()
        if result==QDialog.Accepted and dialog.result_bin is not None:
            bins.append(dialog.result_bin); self._refresh_classifier()

    def _selected_bin_index(self):
        item=self.classifier.currentItem()
        if item is None: return -1
        if item.parent() is not None: item=item.parent()
        return self.classifier.indexOfTopLevelItem(item)

    def _edit_bin(self):
        index=self._selected_bin_index(); bins=self.dbb_state.get("dbc_bins",[])
        if index<0 or index>=len(bins): return
        dialog=DBCBinPropertiesDialog(bins[index],[item.get("name","") for item in bins],self)
        result=dialog.exec() if hasattr(dialog,"exec") else dialog.exec_()
        if result==QDialog.Accepted and dialog.result_bin is not None:
            bins[index]=dialog.result_bin; self._refresh_classifier()

    def _delete_bin(self):
        index=self._selected_bin_index(); bins=self.dbb_state.get("dbc_bins",[])
        if 0<=index<len(bins): bins.pop(index); self._refresh_classifier()

    def _move_bin(self,direction):
        index=self._selected_bin_index(); bins=self.dbb_state.get("dbc_bins",[]); target=index+direction
        if 0<=index<len(bins) and 0<=target<len(bins):
            bins[index],bins[target]=bins[target],bins[index]
            for priority,item in enumerate(bins,1): item["priority"]=priority
            self._refresh_classifier(); self.classifier.setCurrentItem(self.classifier.topLevelItem(target))

    def _poi_view(self):
        item=self.classifier.currentItem()
        if item is None or item.parent() is None: return
        bin_index=self.classifier.indexOfTopLevelItem(item.parent()); child_index=item.parent().indexOfChild(item)
        example=self.dbb_state.get("dbc_bins",[])[bin_index].get("examples",[])[child_index]
        dialog=POIViewDialog(example,self.dbb_state.get("process_layers") or ["Design"],self)
        result=dialog.exec() if hasattr(dialog,"exec") else dialog.exec_()
        if result==QDialog.Accepted and dialog.result_example is not None:
            self.dbb_state["dbc_bins"][bin_index]["examples"][child_index]=dialog.result_example; self._refresh_classifier()
    def _add_clips(self):
        item=self.classifier.currentItem();
        if item is None or item.parent() is not None: return
        bin_data=self.dbb_state.get("dbc_bins",[])[self.classifier.indexOfTopLevelItem(item)]; selected=[d for d in self.defects if d.get("id") in self.selected_ids]
        known={example.get("defect_id") for example in bin_data.get("examples",[])}
        for d in selected:
            if d.get("id") in known: continue
            bin_data.setdefault("examples",[]).append({"id":uuid4().hex,"defect_id":d.get("id"),"name":f"Defect {d.get('id')}","valid":False,"poi":{"mode":"","layers":[],"selection_defined":False}})
        self._refresh_classifier()

    def _assign_manual_bin(self):
        index=self._selected_bin_index(); bins=self.dbb_state.get("dbc_bins",[])
        if index<0 or index>=len(bins): return
        targets=self.selected_ids or ({self.current_id} if self.current_id is not None else set())
        for defect in self.defects:
            if defect.get("id") in targets: defect["dbb_manual_bin"]=bins[index].get("name")
        self._refresh()

    def _refresh_library_selector(self):
        current=self.current_library_id; self.library_selector.clear()
        for library in self.libraries: self.library_selector.addItem(f"{library.get('name')} - v{library.get('version',1)}",library.get("id"))
        if current:
            index=self.library_selector.findData(current)
            if index>=0: self.library_selector.setCurrentIndex(index)

    def _new_library(self):
        self.current_library_id=None; self.dbb_state["dbc_bins"]=[]; self.library_name.setText(f"DBC Library {len(self.libraries)+1}"); self._refresh_classifier()

    def _open_library(self):
        identifier=self.library_selector.currentData(); library=next((item for item in self.libraries if item.get("id")==identifier),None)
        if library is None: return
        self.current_library_id=identifier; self.library_name.setText(library.get("name","")); self.dbb_state["dbc_bins"]=deepcopy(library.get("bins",[])); self._refresh_classifier()

    def _save_library(self,as_new=False):
        name=self.library_name.text().strip()
        if not name: QMessageBox.warning(self,"DBC Library","DBC Library name is required."); return
        if as_new or not self.current_library_id:
            if any(item.get("name","").casefold()==name.casefold() for item in self.libraries):
                QMessageBox.warning(self,"DBC Library","Use a unique name for Save As."); return
            library=create_dbc_library(name,self.dbb_state.get("process_layers",[])); library["bins"]=deepcopy(self.dbb_state.get("dbc_bins",[])); self.libraries.append(library); self.current_library_id=library["id"]
        else:
            library=next(item for item in self.libraries if item.get("id")==self.current_library_id); library.update({"name":name,"bins":deepcopy(self.dbb_state.get("dbc_bins",[])),"modified":False,"last_modified":datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        self.dbb_state["dbc_library"]=name; self._refresh_library_selector()

    def _publish_library(self):
        if not self.current_library_id: self._save_library(False)
        library=next((item for item in self.libraries if item.get("id")==self.current_library_id),None)
        if library is not None: library["published"]=True; library["modified"]=False; self._refresh_library_selector()

    def _delete_library(self):
        identifier=self.library_selector.currentData()
        if not identifier: return
        self.libraries=[item for item in self.libraries if item.get("id")!=identifier]; self.current_library_id=None; self.dbb_state["dbc_bins"]=[]; self.library_name.clear(); self._refresh_library_selector(); self._refresh_classifier()
    def _analyze(self):
        dialog=DBBAnalysisToolboxDialog(self.defects,self.dbb_state,self); result=dialog.exec() if hasattr(dialog,"exec") else dialog.exec_()
        if result==QDialog.Accepted and dialog.result_defects is not None:
            self.defects=dialog.result_defects
            for d in self.defects: d["dbb_sampled"]=d.get("id") in set(dialog.sampled_ids)
            self.result_defects=deepcopy(self.defects); self._refresh()
    def _magnifier(self):
        defect=next((d for d in self.defects if d.get("id")==self.current_id),None)
        if not defect: QMessageBox.information(self,"DBB Magnifier","Select a current defect first."); return
        QMessageBox.information(self,"DBB Magnifier",f"Defect {defect.get('id')}\nTest Clip | Reference Clip | Difference Clip\nDesign position: ({defect.get('design_x',defect.get('x',0))}, {defect.get('design_y',defect.get('y',0))})")
    def _histogram(self):
        shown=self._scope_defects(); values=[float(d.get("intensity",d.get("dci",0))) for d in shown]
        if not values: QMessageBox.information(self,"Clip Histogram","No displayed defects."); return
        buckets=[0]*8
        low=min(values); high=max(values); span=max(1e-9,high-low)
        for value in values: buckets[min(7,int((value-low)/span*8))]+=1
        QMessageBox.information(self,"Clip Histogram","Gray-level / attribute histogram\n"+"\n".join(f"{index+1}: {'|'*count} ({count})" for index,count in enumerate(buckets)))
    def _finish(self):
        self.dbb_state["dbc_libraries"]=deepcopy(self.libraries); self.dbb_state["dbc_library"]=self.library_name.text().strip(); self.result_data["defects"]=deepcopy(self.defects); self.result_data["defect_count"]=len(self.defects); self.result_data["dbb_recipe"]=deepcopy(self.dbb_state); self.result_defects=deepcopy(self.defects); self.accept()

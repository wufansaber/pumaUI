from __future__ import annotations

import csv
from copy import deepcopy
from hashlib import sha256
from io import StringIO
import json
from math import hypot
from pathlib import Path
from uuid import uuid4

from ...qt_compat import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFileDialog,
    QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox,
    QPushButton, QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout, Qt,
)


REGISTRATION_MODES = ("Input Registration Offset", "Re-use Existing GDS2CA", "Re-use DBB", "Select Registration Marks on Tool", "Skip Registration")


def parse_mapping_csv(text: str) -> list[dict]:
    reader = csv.DictReader(StringIO(text))
    if not reader.fieldnames:
        raise ValueError("Mapping file requires a CSV header.")
    aliases = {name.casefold().replace(" ", "").replace("_", ""): name for name in reader.fieldnames}
    def field(row, *names, default=""):
        for name in names:
            key = aliases.get(name.casefold().replace(" ", "").replace("_", ""))
            if key is not None: return row.get(key, default)
        return default
    output = []
    for row in reader:
        name = str(field(row, "CAGName", "GroupName", "Name")).strip()
        if not name: continue
        try:
            code = int(field(row, "CAGCode", "CAGID", default=len(output) + 1) or len(output) + 1)
            region = int(field(row, "RegionID", default=1) or 1)
            layer = int(field(row, "GDSLayer", "Layer", default=0) or 0)
            data_type = int(field(row, "DataType", default=0) or 0)
        except ValueError as exc:
            raise ValueError(f"Invalid numeric mapping value for {name}.") from exc
        if not 1 <= code <= 32000: raise ValueError("CAG Code must be between 1 and 32000.")
        output.append({"name": name, "cag_code": code, "region_id": region, "gds_layer": layer, "data_type": data_type, "kind": field(row, "Type", "CAType", default="CA") or "CA", "priority": int(field(row, "Priority", default=len(output) + 1) or len(output) + 1)})
    if not output: raise ValueError("Mapping file contains no Care Area groups.")
    return output


def parse_config_csv(text: str) -> dict:
    rows = list(csv.reader(StringIO(text)))
    values = {row[0].strip(): row[1].strip() for row in rows if len(row) >= 2 and row[0].strip()}
    clips = [value for key, value in values.items() if key.casefold().startswith("registrationclip")]
    return {"orientation": values.get("Orientation", "0"), "registration_clips": clips, "registration_layer": int(values.get("RegistrationLayer", 0) or 0), "registration_data_type": int(values.get("RegistrationDataType", 0) or 0)}


def generate_care_area_component(cagds_data: bytes, mapping=None, config=None, *, use_default_data=False, source_name="") -> dict:
    if not cagds_data: raise ValueError("Select a non-empty Care Area GDS file.")
    if not use_default_data and (not mapping or config is None): raise ValueError("Mapping and Config files are required unless Use Default Data is selected.")
    definitions = deepcopy(mapping or [{"name": "Default", "cag_code": 1, "region_id": 1, "gds_layer": 0, "data_type": 0, "kind": "CA", "priority": 1}])
    groups = []
    for index, item in enumerate(definitions):
        # The proprietary binary geometry is represented by deterministic normalized rectangles.
        inset = min(0.35, 0.04 + index * 0.025)
        groups.append({"name": item["name"], "kind": item.get("kind", "CA"), "cag_code": int(item.get("cag_code", index + 1)), "region_id": int(item.get("region_id", 1)), "priority": int(item.get("priority", index + 1)), "gds_layer": int(item.get("gds_layer", 0)), "data_type": int(item.get("data_type", 0)), "areas": [[inset, inset, 1 - 2 * inset, 1 - 2 * inset]], "registered": False, "verified": False, "status": "V*R*", "enabled": True, "show": True})
    return {"id": uuid4().hex, "format": "Puma GDS2CA Component", "source_name": source_name, "source_sha256": sha256(cagds_data).hexdigest(), "default_data": bool(use_default_data), "config": deepcopy(config or {}), "groups": groups, "registration": {}, "generation_status": "Care Area component generated successfully (simulated geometry)."}


def register_component(component: dict, design_sites, tool_sites, *, verify=False, max_scale_deviation=0.10) -> tuple[dict, bool]:
    if len(design_sites) != 2 or len(tool_sites) != 2: raise ValueError("Two design sites and two tool registration sites are required.")
    design_distance = hypot(design_sites[1][0] - design_sites[0][0], design_sites[1][1] - design_sites[0][1])
    tool_distance = hypot(tool_sites[1][0] - tool_sites[0][0], tool_sites[1][1] - tool_sites[0][1])
    if design_distance <= 0 or tool_distance <= 0: raise ValueError("Registration sites must be distinct.")
    scale = tool_distance / design_distance
    offset = [float(tool_sites[0][0]) - float(design_sites[0][0]) * scale, float(tool_sites[0][1]) - float(design_sites[0][1]) * scale]
    result = deepcopy(component); result["registration"] = {"design_sites": deepcopy(design_sites), "tool_sites": deepcopy(tool_sites), "scale": scale, "offset": offset}
    for group in result.get("groups", []):
        group["registered"] = True; group["verified"] = bool(verify); group["status"] = "VR" if verify else "V*R"
    return result, abs(scale - 1.0) > float(max_scale_deviation)


def prune_component(component: dict) -> tuple[dict, dict]:
    result = deepcopy(component); removed = {}
    for group in result.get("groups", []):
        before = list(group.get("areas", [])); kept = [area for area in before if area[0] >= 0 and area[1] >= 0 and area[0] + area[2] <= 1 and area[1] + area[3] <= 1]
        group["areas"] = kept; removed[group.get("name", "")] = len(before) - len(kept)
    return result, removed


def assign_cag_codes(groups, names, start_code: int, *, sequential=False) -> list[dict]:
    if not 1 <= int(start_code) <= 32000: raise ValueError("CAG Code must be between 1 and 32000.")
    selected = set(names); result = deepcopy(groups); code = int(start_code)
    for group in result:
        if group.get("name") in selected:
            if code > 32000: raise ValueError("Sequential CAG Code exceeds 32000.")
            group["cag_code"] = code
            if sequential: code += 1
    pairs = [(group.get("name"), group.get("cag_code")) for group in result]
    if len(pairs) != len(set(pairs)): raise ValueError("CAG Name and CAG Code pairs must be unique.")
    return result


def apply_component_to_recipe(recipe: dict, component: dict, test_indexes=None) -> dict:
    result = deepcopy(recipe); indexes = list(test_indexes or range(len(result.get("tests", []))))
    for index in indexes:
        if 0 <= index < len(result.get("tests", [])):
            state = result["tests"][index].setdefault("care_areas", {})
            state["groups"] = deepcopy(component.get("groups", [])); state["gds2ca_component_id"] = component.get("id", "")
    result["dirty"] = True
    return result


class GDS2CAConverterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent); self.result_component = None; self.setWindowTitle("GDS2CA Converter"); self.resize(820, 520)
        root = QVBoxLayout(self); grid = QGridLayout(); self.paths = {}
        for row, label in enumerate(("Care Area GDS File", "Mapping File", "Config File", "Output Location")):
            edit = QLineEdit(); browse = QPushButton("Browse..."); browse.clicked.connect(lambda checked=False, key=label: self._browse(key)); grid.addWidget(QLabel(label), row, 0); grid.addWidget(edit, row, 1); grid.addWidget(browse, row, 2); self.paths[label] = edit
        root.addLayout(grid); self.default = QCheckBox("Use Default Data"); self.default.toggled.connect(self._toggle_default); root.addWidget(self.default)
        self.destination = QComboBox(); self.destination.addItems(["Local Path", "RDS Component Sharing Level"]); root.addWidget(self.destination)
        self.status = QLabel("Select source files and click Generate Care Areas."); self.status.setWordWrap(True); root.addWidget(self.status); root.addStretch(1)
        footer = QHBoxLayout(); footer.addStretch(1); generate = QPushButton("Generate Care Areas"); generate.clicked.connect(self._generate); close = QPushButton("Close"); close.clicked.connect(self.reject); footer.addWidget(generate); footer.addWidget(close); root.addLayout(footer)

    def _browse(self, key):
        if key == "Output Location": value = QFileDialog.getExistingDirectory(self, key)
        else: value, _ = QFileDialog.getOpenFileName(self, key)
        if value: self.paths[key].setText(value)

    def _toggle_default(self, checked):
        for key in ("Mapping File", "Config File"): self.paths[key].setEnabled(not checked)

    def _generate(self):
        try:
            gds_path = Path(self.paths["Care Area GDS File"].text())
            data = gds_path.read_bytes()
            mapping = None if self.default.isChecked() else parse_mapping_csv(Path(self.paths["Mapping File"].text()).read_text(encoding="utf-8-sig"))
            config = {} if self.default.isChecked() else parse_config_csv(Path(self.paths["Config File"].text()).read_text(encoding="utf-8-sig"))
            self.result_component = generate_care_area_component(data, mapping, config, use_default_data=self.default.isChecked(), source_name=gds_path.name)
            output = self.paths["Output Location"].text().strip()
            if output and self.destination.currentText() == "Local Path":
                target = Path(output) / f"{gds_path.stem}.gds2ca.json"
                target.write_text(json.dumps(self.result_component, indent=2), encoding="utf-8")
            self.status.setText(self.result_component["generation_status"]); self.accept()
        except (OSError, ValueError, csv.Error) as exc: QMessageBox.warning(self, "GDS2CA Converter", str(exc))


class CAGEditorDialog(QDialog):
    def __init__(self, groups, parent=None):
        super().__init__(parent); self.groups = deepcopy(groups); self.result_groups = None; self.setWindowTitle("CAG Editor"); self.resize(760, 520)
        root = QVBoxLayout(self); top = QHBoxLayout(); self.filter = QLineEdit(); self.filter.setPlaceholderText("Quick Filter: CAG Name"); self.filter.textChanged.connect(self._refresh); self.code = QSpinBox(); self.code.setRange(1, 32000); self.sequential = QCheckBox("Sequential order"); assign = QPushButton("Assign"); assign.clicked.connect(self._assign); top.addWidget(self.filter, 1); top.addWidget(self.code); top.addWidget(self.sequential); top.addWidget(assign); root.addLayout(top)
        self.table = QTableWidget(0, 4); self.table.setHorizontalHeaderLabels(["CAG Name", "CAG Code", "Region ID", "Type"]); self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); self.table.setSelectionBehavior(QAbstractItemView.SelectRows); root.addWidget(self.table, 1)
        footer = QHBoxLayout(); footer.addStretch(1); ok = QPushButton("OK"); ok.clicked.connect(self._finish); cancel = QPushButton("Cancel"); cancel.clicked.connect(self.reject); footer.addWidget(ok); footer.addWidget(cancel); root.addLayout(footer); self._refresh()

    def _visible(self):
        term = self.filter.text().strip().casefold(); return [(index, item) for index, item in enumerate(self.groups) if not term or term in str(item.get("name", "")).casefold()]
    def _refresh(self):
        self.visible_rows = self._visible(); self.table.setRowCount(len(self.visible_rows))
        for row, (_index, item) in enumerate(self.visible_rows):
            for column, value in enumerate((item.get("name", ""), item.get("cag_code", 0), item.get("region_id", 1), item.get("kind", "CA"))): self.table.setItem(row, column, QTableWidgetItem(str(value)))
    def _assign(self):
        names = [self.visible_rows[row][1].get("name") for row in sorted({index.row() for index in self.table.selectedIndexes()})]
        try: self.groups = assign_cag_codes(self.groups, names, self.code.value(), sequential=self.sequential.isChecked()); self._refresh()
        except ValueError as exc: QMessageBox.warning(self, "CAG Editor", str(exc))
    def _finish(self): self.result_groups = deepcopy(self.groups); self.accept()

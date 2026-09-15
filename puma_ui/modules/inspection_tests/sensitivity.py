from __future__ import annotations

from copy import deepcopy
import csv
import json
from io import StringIO
from math import isfinite
from pathlib import Path

from ...qt_compat import (
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
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    Qt,
    QVBoxLayout,
    QWidget,
)


ALGORITHM_PARAMETERS = {
    "HLAT": ["Threshold", "Noise", "ABSMIN", "Gradient", "Color"],
    "Secondary HLAT": ["Threshold", "Noise", "ABSMIN", "Gradient", "Color"],
    "FAST": ["Threshold"],
    "Secondary FAST": ["Threshold"],
    "AutoSens": [],
    "ArrayMode": ["Threshold", "Noise", "ABSMIN"],
    "Secondary ArrayMode": ["Threshold", "Noise", "ABSMIN"],
    "Secondary Wafer Scale Profile": ["Mean Threshold", "Max Threshold"],
    "Wafer Scale Profile": ["Mean Threshold", "Max Threshold"],
    "CF2": ["Threshold", "Noise"],
    "CF3": ["Threshold", "Noise"],
    "Secondary CF2": ["Threshold", "Noise"],
    "Secondary CF3": ["Threshold", "Noise"],
    "GAP Max Threshold": ["Max Threshold"],
    "GAP Local Noise Filter": ["Local Noise", "Suppression Threshold"],
}
ALGORITHM_GROUPS = {
    "Primary Test Parameters": [
        "HLAT",
        "FAST",
        "AutoSens",
        "ArrayMode",
        "Wafer Scale Profile",
    ],
    "Channel Fusion": ["CF2", "CF3"],
    "Secondary Test Parameters": [
        "Secondary HLAT",
        "Secondary FAST",
        "Secondary ArrayMode",
        "Secondary Wafer Scale Profile",
        "Secondary CF2",
        "Secondary CF3",
    ],
    "GAP": ["GAP Max Threshold", "GAP Local Noise Filter"],
}
PARAMETER_OBJECTS = ("Sensitivity", "Seg0", "Seg1")
EXCLUSIVE_ALGORITHMS = {"HLAT", "FAST", "AutoSens"}
SECONDARY_ALGORITHMS = {
    "Secondary HLAT",
    "Secondary FAST",
    "Secondary ArrayMode",
    "Secondary Wafer Scale Profile",
    "Secondary CF2",
    "Secondary CF3",
}
PRIMARY_DETECTION = {"HLAT", "FAST", "AutoSens", "ArrayMode", "CF2", "CF3"}
POSTFILTERS = {"None", "Off", "Weak", "Medium", "Strong"}
FUSION_FLAVOR_NAMES = [
    "Channel 1 + Channel 2",
    "Channel 1 + Channel 3",
    "Channel 2 + Channel 3",
    "Channel 1 + Channel 2 + Channel 3",
]
SDI_FUSION_NAMES = ["CF12", "CF13", "CF23", "CF123"]


def _fusion_base_algorithm(name: str) -> str:
    return name.removeprefix("Secondary ")


def _default_sdi_mode() -> dict:
    return {
        "run_sdi": False,
        "run_cf_sdi": False,
        "channels": [
            {
                "segments": [
                    {"threshold": 200.0, "run": False},
                    {"threshold": 200.0, "run": False},
                ]
            }
            for _ in range(3)
        ],
        "fusion": {
            name: {
                "segments": [
                    {"threshold": 20.0, "enabled": False, "mask": "Ch1"},
                    {"threshold": 20.0, "enabled": False, "mask": "Ch1"},
                ]
            }
            for name in SDI_FUSION_NAMES
        },
    }


def _algorithm_defaults(name: str) -> dict:
    values = {
        "Threshold": 45.0,
        "Noise": 1.0,
        "ABSMIN": 0.0,
        "Gradient": 0.0,
        "Color": 0.0,
        "Mean Threshold": 800.0,
        "Max Threshold": 1500.0,
        "Local Noise": 0.01,
        "Suppression Threshold": 0.0,
    }
    channels = [
        {parameter: values[parameter] for parameter in ALGORITHM_PARAMETERS[name]}
        for _ in range(3)
    ]
    run_by_default = name == "HLAT"
    return {
        "run": run_by_default,
        "channels": channels,
        "segments": [
            {
                "Seg0": deepcopy(channel),
                "Seg1": deepcopy(channel),
            }
            for channel in channels
        ],
        "segment_run": [
            {"Sensitivity": run_by_default, "Seg0": run_by_default, "Seg1": run_by_default}
            for _ in range(3)
        ],
    }


def default_sensitivity_state(region_names=None) -> dict:
    names = list(region_names or ["Default"])
    return {
        "regions": {
            name: {
                "algorithms": {
                    algorithm: _algorithm_defaults(algorithm)
                    for algorithm in ALGORITHM_PARAMETERS
                },
                "enable_remap": False,
            }
            for name in names
        },
        "histogram_remap": True,
        "preconvolver": "None",
        "enhanced_secondary_die": False,
        "secondary_die_factor": 1.0,
        "variable_noise_control": False,
        "vnc": {
            "enabled": False,
            "mode": "Disabled",
            "regions": [],
            "max_bw": {},
        },
        "decouple_channel_fusion": False,
        "decoupled_cf": {
            name: [
                {
                    "Threshold": 2.0,
                    "Noise": 1.0,
                    "ABSMIN": 0.0,
                    "Color": 0.0,
                    "Gradient": 0.0,
                    "MinDiff": 0.0,
                    "Postfilter": "None",
                }
                for _ in range(3)
            ]
            for name in names
        },
        "fusion_flavors": {
            algorithm: [
                {"name": name, "enabled": False, "threshold": 45.0}
                for name in FUSION_FLAVOR_NAMES
            ]
            for algorithm in ("CF2", "CF3")
        },
        "cib": [
            {"clip": 0.0, "offset": 0.0, "L0": 1450.0, "K": 1.0, "preconvolver": "None"}
            for _ in range(3)
        ],
        "autosens_mode": "Production",
        "post_filter": "None",
        "dark_defect_factor": 1.0,
        "runtime_alignment": {
            "enable_new_rta": True,
            "max_y_init_shift": 0,
        },
        "defect_filters": {
            "run_process_noise_filter": False,
            "intensity": 0.0,
            "side_ratio": 1.0,
            "top_ratio": 1.0,
        },
        "single_die_inspection": {
            "primary": _default_sdi_mode(),
            "secondary": _default_sdi_mode(),
        },
    }


def normalized_sensitivity_state(state: dict | None, region_names=None) -> dict:
    names = list(region_names or ["Default"])
    legacy_vnc = (
        bool(state.get("variable_noise_control", False))
        if isinstance(state, dict) and "vnc" not in state
        else None
    )
    result = default_sensitivity_state(names)
    if isinstance(state, dict):
        for key, value in state.items():
            if key != "regions":
                result[key] = deepcopy(value)
        for name, region in (state.get("regions") or {}).items():
            result["regions"][name] = deepcopy(region)
    for name in names:
        region = result["regions"].setdefault(name, default_sensitivity_state([name])["regions"][name])
        algorithms = region.setdefault("algorithms", {})
        for algorithm in ALGORITHM_PARAMETERS:
            supplied = algorithms.get(algorithm)
            defaults_for_algorithm = _algorithm_defaults(algorithm)
            if not isinstance(supplied, dict):
                algorithms[algorithm] = defaults_for_algorithm
                continue
            channels = list(supplied.get("channels") or [])
            normalized_channels = []
            for channel_index in range(3):
                values = deepcopy(defaults_for_algorithm["channels"][channel_index])
                if channel_index < len(channels) and isinstance(channels[channel_index], dict):
                    values.update(channels[channel_index])
                normalized_channels.append(values)
            supplied_segments = list(supplied.get("segments") or [])
            supplied_segment_run = supplied.get("segment_run")
            if not isinstance(supplied_segment_run, list):
                supplied_segment_run = []
            normalized_segments = []
            for channel_index in range(3):
                stored_channel = (
                    supplied_segments[channel_index]
                    if channel_index < len(supplied_segments)
                    and isinstance(supplied_segments[channel_index], dict)
                    else {}
                )
                channel_segments = {}
                for segment_name in PARAMETER_OBJECTS[1:]:
                    values = deepcopy(normalized_channels[channel_index])
                    stored_values = stored_channel.get(segment_name, {})
                    if isinstance(stored_values, dict):
                        values.update(stored_values)
                    channel_segments[segment_name] = values
                normalized_segments.append(channel_segments)
            algorithms[algorithm] = {
                **defaults_for_algorithm,
                **deepcopy(supplied),
                "channels": normalized_channels,
                "segments": normalized_segments,
                "segment_run": [
                    {
                        **deepcopy(defaults_for_algorithm["segment_run"][channel_index]),
                        **(
                            supplied_segment_run[channel_index]
                            if channel_index < len(supplied_segment_run)
                            and isinstance(supplied_segment_run[channel_index], dict)
                            else {}
                        ),
                    }
                    for channel_index in range(3)
                ],
            }
    vnc = result.setdefault("vnc", {})
    if legacy_vnc is not None:
        vnc["enabled"] = legacy_vnc
        vnc["mode"] = "Apply" if legacy_vnc else "Disabled"
    vnc.setdefault("enabled", bool(result.get("variable_noise_control", False)))
    vnc.setdefault("mode", "Apply" if vnc["enabled"] else "Disabled")
    vnc.setdefault("regions", [])
    vnc.setdefault("max_bw", {})
    vnc.setdefault("analysis", {})
    vnc.setdefault("data_source", "")
    result["variable_noise_control"] = bool(vnc["enabled"])
    defaults = default_sensitivity_state(list(result["regions"]))
    decoupled = result.setdefault("decoupled_cf", {})
    for name in result["regions"]:
        channels = list(decoupled.get(name) or [])
        while len(channels) < 3:
            channels.append({})
        for index in range(3):
            merged = deepcopy(defaults["decoupled_cf"][name][index])
            merged.update(channels[index] if isinstance(channels[index], dict) else {})
            channels[index] = merged
        decoupled[name] = channels[:3]
    flavors = result.setdefault("fusion_flavors", {})
    for algorithm in ("CF2", "CF3"):
        stored = {
            item.get("name"): item
            for item in (flavors.get(algorithm) or [])
            if isinstance(item, dict) and item.get("name")
        }
        flavors[algorithm] = [
            {**deepcopy(item), **deepcopy(stored.get(item["name"], {}))}
            for item in defaults["fusion_flavors"][algorithm]
        ]
    cib = list(result.get("cib") or [])
    while len(cib) < 3:
        cib.append({})
    result["cib"] = [
        {**deepcopy(defaults["cib"][index]), **(cib[index] if isinstance(cib[index], dict) else {})}
        for index in range(3)
    ]
    runtime_alignment = result.setdefault("runtime_alignment", {})
    runtime_alignment.setdefault("enable_new_rta", True)
    runtime_alignment.setdefault("max_y_init_shift", 0)
    result.setdefault("post_filter", "None")
    result.setdefault("dark_defect_factor", 1.0)
    stored_sdi = result.setdefault("single_die_inspection", {})
    normalized_sdi = {}
    for mode_name in ("primary", "secondary"):
        default_mode = _default_sdi_mode()
        supplied_mode = stored_sdi.get(mode_name, {})
        mode = deepcopy(default_mode)
        if isinstance(supplied_mode, dict):
            mode["run_sdi"] = bool(supplied_mode.get("run_sdi", mode["run_sdi"]))
            mode["run_cf_sdi"] = bool(supplied_mode.get("run_cf_sdi", mode["run_cf_sdi"]))
            for channel_index, supplied_channel in enumerate(supplied_mode.get("channels", [])[:3]):
                if not isinstance(supplied_channel, dict):
                    continue
                for segment_index, supplied_segment in enumerate(supplied_channel.get("segments", [])[:2]):
                    if isinstance(supplied_segment, dict):
                        mode["channels"][channel_index]["segments"][segment_index].update(
                            deepcopy(supplied_segment)
                        )
            for flavor_name, supplied_flavor in (supplied_mode.get("fusion") or {}).items():
                if flavor_name not in mode["fusion"] or not isinstance(supplied_flavor, dict):
                    continue
                for segment_index, supplied_segment in enumerate(supplied_flavor.get("segments", [])[:2]):
                    if isinstance(supplied_segment, dict):
                        mode["fusion"][flavor_name]["segments"][segment_index].update(
                            deepcopy(supplied_segment)
                        )
        normalized_sdi[mode_name] = mode
    result["single_die_inspection"] = normalized_sdi
    return result


def serialize_sensitivity_state(state):
    names = list((state or {}).get("regions", {})) or None
    return json.dumps(normalized_sensitivity_state(state, names), indent=2, sort_keys=True)


def parse_sensitivity_state(text, region_names=None):
    try:
        parsed = json.loads(text)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid Sensitivity parameter file") from exc
    if not isinstance(parsed, dict):
        raise ValueError("invalid Sensitivity parameter file")
    result = normalized_sensitivity_state(parsed, region_names or list(parsed.get("regions", {})) or None)
    errors = validate_sensitivity(result)
    if errors:
        raise ValueError("; ".join(errors))
    return result


def analyze_bandwidth_csv(text, region_names):
    rows = list(csv.DictReader(StringIO(text)))
    report = {}
    for region_index, region_name in enumerate(list(region_names)[:2]):
        channels = []
        for channel in range(1, 4):
            key = f"BW{channel}_{region_index}"
            values = []
            for row in rows:
                try:
                    value = float(row.get(key, -1))
                except (TypeError, ValueError):
                    continue
                if isfinite(value) and value >= 0:
                    values.append(value)
            values.sort()
            recommended = values[min(len(values) - 1, round((len(values) - 1) * 0.9))] if values else 100.0
            channels.append(
                {
                    "samples": len(values),
                    "minimum": min(values) if values else None,
                    "maximum": max(values) if values else None,
                    "recommended_max_bw": recommended,
                }
            )
        report[region_name] = channels
    return report


def validate_sensitivity(state: dict) -> list[str]:
    state = normalized_sensitivity_state(state, list((state or {}).get("regions", {})) or None)
    errors = []
    active_exclusive = set()
    for region_name, region in state.get("regions", {}).items():
        active = [
            name for name, config in region.get("algorithms", {}).items()
            if config.get("run")
        ]
        active_exclusive.update(EXCLUSIVE_ALGORITHMS.intersection(active))
        if not active:
            errors.append(f"{region_name}: no sensitivity algorithm is enabled")
    if len(active_exclusive) > 1:
        errors.append("HLAT, FAST, and AutoSens cannot run in the same test")
    all_active = {
        name
        for region in state["regions"].values()
        for name, config in region["algorithms"].items()
        if config.get("run")
    }
    for region_name, region in state["regions"].items():
        for algorithm, config in region["algorithms"].items():
            expected = ALGORITHM_PARAMETERS[algorithm]
            parameter_sets = [
                (channel_index, "Sensitivity", values)
                for channel_index, values in enumerate(config.get("channels", []), start=1)
            ]
            for channel_index, segments in enumerate(config.get("segments", []), start=1):
                for segment_name in PARAMETER_OBJECTS[1:]:
                    parameter_sets.append(
                        (channel_index, segment_name, segments.get(segment_name, {}))
                    )
            for channel_index, object_name, values in parameter_sets:
                for parameter in expected:
                    try:
                        value = float(values.get(parameter, 0))
                    except (TypeError, ValueError):
                        errors.append(
                            f"{region_name}, {algorithm}, channel {channel_index}, "
                            f"{object_name}: {parameter} must be numeric"
                        )
                        continue
                    if not isfinite(value) or value < 0:
                        errors.append(
                            f"{region_name}, {algorithm}, channel {channel_index}, "
                            f"{object_name}: {parameter} must be finite and nonnegative"
                        )
    if state.get("enhanced_secondary_die"):
        if not SECONDARY_ALGORITHMS.intersection(all_active):
            errors.append("Enhanced Secondary Die requires a Secondary algorithm")
    elif SECONDARY_ALGORITHMS.intersection(all_active):
        errors.append("Secondary algorithms require Enhanced Secondary Die")
    if "GAP Max Threshold" in all_active and not {
        "HLAT",
        "FAST",
        "ArrayMode",
    }.intersection(all_active):
        errors.append("GAP Max Threshold requires HLAT, FAST, or ArrayMode")
    if "GAP Local Noise Filter" in all_active and not {"HLAT", "FAST"}.intersection(all_active):
        errors.append("GAP Local Noise Filter requires HLAT or FAST")
    if state.get("decouple_channel_fusion") and not {
        "HLAT",
        "Secondary HLAT",
    }.intersection(all_active):
        errors.append("Decoupled Channel Fusion requires HLAT or Secondary HLAT")
    for algorithm in ("CF2", "CF3", "Secondary CF2", "Secondary CF3"):
        flavor_algorithm = _fusion_base_algorithm(algorithm)
        if algorithm in all_active and not any(
            item.get("enabled") for item in state["fusion_flavors"][flavor_algorithm]
        ):
            errors.append(f"{algorithm} requires at least one Channel Fusion Flavor")
    for channel_index, values in enumerate(state.get("cib", []), start=1):
        try:
            numeric = [
                float(values.get("clip", 0)),
                float(values.get("offset", 0)),
                float(values.get("L0", 0)),
                float(values.get("K", 0)),
            ]
        except (TypeError, ValueError):
            errors.append(f"Channel {channel_index}: CIB values must be numeric")
            continue
        if not all(isfinite(value) for value in numeric) or numeric[2] < 0 or numeric[3] <= 0:
            errors.append(f"Channel {channel_index}: CIB L0 must be nonnegative and K positive")
        if values.get("preconvolver") not in POSTFILTERS - {"Off"}:
            errors.append(f"Channel {channel_index}: invalid Preconvolver")
    vnc = state.get("vnc", {})
    if vnc.get("enabled"):
        regions = list(vnc.get("regions") or [])
        if not 1 <= len(regions) <= 2:
            errors.append("Variable Noise Control requires one or two regions")
        if any(name not in state["regions"] for name in regions):
            errors.append("Variable Noise Control contains an unknown region")
        for name in regions:
            values = vnc.get("max_bw", {}).get(name, [])
            if len(values) != 3 or any(not 0 < float(value) <= 10000 for value in values):
                errors.append(f"{name}: VNC MaxBW requires three values from 0 to 10000")
    for region_name, channels in state.get("decoupled_cf", {}).items():
        for channel_index, values in enumerate(channels, start=1):
            if values.get("Postfilter") not in POSTFILTERS:
                errors.append(
                    f"{region_name}, channel {channel_index}: invalid Channel Fusion Postfilter"
                )
    runtime_alignment = state.get("runtime_alignment", {})
    if runtime_alignment.get("max_y_init_shift") not in (0, 1):
        errors.append("RTA+ MaxYInitShift must be 0 or 1")
    if state.get("post_filter") not in POSTFILTERS:
        errors.append("Invalid global Post Filter")
    valid_masks = {"Ch1", "Ch2", "Ch3", "Ch1+Ch2", "Ch1+Ch3", "Ch2+Ch3"}
    for mode_name, mode in state.get("single_die_inspection", {}).items():
        label = "Primary SDI" if mode_name == "primary" else "Secondary SDI"
        direct_segments = [
            segment
            for channel in mode.get("channels", [])
            for segment in channel.get("segments", [])
        ]
        fusion_segments = [
            segment
            for flavor in mode.get("fusion", {}).values()
            for segment in flavor.get("segments", [])
        ]
        if mode.get("run_sdi") and not any(segment.get("run") for segment in direct_segments):
            errors.append(f"{label} requires at least one enabled Channel Segment")
        if mode.get("run_cf_sdi") and not any(segment.get("enabled") for segment in fusion_segments):
            errors.append(f"{label} Channel Fusion requires at least one enabled Flavor Segment")
        for segment in direct_segments + fusion_segments:
            try:
                threshold = float(segment.get("threshold", 0))
            except (TypeError, ValueError):
                threshold = -1.0
            if not isfinite(threshold) or threshold < 0:
                errors.append(f"{label} Threshold must be finite and nonnegative")
                break
        if any(segment.get("mask") not in valid_masks for segment in fusion_segments):
            errors.append(f"{label} contains an invalid Segment Mask")
    try:
        dark_factor = float(state.get("dark_defect_factor", 1.0))
    except (TypeError, ValueError):
        dark_factor = -1.0
    if not isfinite(dark_factor) or dark_factor <= 0:
        errors.append("Dark Defect Factor must be finite and greater than 0")
    return errors


class VariableNoiseControlDialog(QDialog):
    MODES = ["Disabled", "Collect Bandwidth", "Analyze Bandwidth", "Apply"]

    def __init__(self, state, region_names, parent=None):
        super().__init__(parent)
        self.original_state = deepcopy(state)
        self.result_state = None
        self.setWindowTitle("Variable Noise Control")
        self.resize(700, 420)
        root = QVBoxLayout(self)
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("VNC Stage"))
        self.mode = QComboBox()
        self.mode.addItems(self.MODES)
        self.mode.setCurrentText(state.get("mode", "Disabled"))
        self.mode.currentTextChanged.connect(self._mode_changed)
        mode_row.addWidget(self.mode)
        mode_row.addStretch(1)
        root.addLayout(mode_row)
        root.addWidget(
            QLabel(
                "Select one or two regions. MaxBW is configured independently "
                "for all three channels."
            )
        )
        self.table = QTableWidget(len(region_names), 5)
        self.table.setHorizontalHeaderLabels(
            ["Use", "Region", "Channel 1 MaxBW", "Channel 2 MaxBW", "Channel 3 MaxBW"]
        )
        selected = set(state.get("regions") or [])
        max_bw = state.get("max_bw") or {}
        default_bw = 4000.0 if self.mode.currentText() == "Collect Bandwidth" else 100.0
        for row, name in enumerate(region_names):
            use = QTableWidgetItem("")
            use.setCheckState(Qt.Checked if name in selected else Qt.Unchecked)
            self.table.setItem(row, 0, use)
            self.table.setItem(row, 1, QTableWidgetItem(name))
            values = list(max_bw.get(name) or [default_bw] * 3)
            while len(values) < 3:
                values.append(default_bw)
            for channel in range(3):
                self.table.setItem(row, channel + 2, QTableWidgetItem(f"{float(values[channel]):g}"))
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        root.addWidget(self.table, 1)
        analysis = QHBoxLayout()
        self.data_source = QLineEdit(state.get("data_source", ""))
        self.data_source.setReadOnly(True)
        self.data_source.setPlaceholderText("Image Packer data.csv")
        load_data = QPushButton("Load Image Packer data.csv")
        load_data.clicked.connect(self._load_bandwidth_data)
        analysis.addWidget(self.data_source, 1)
        analysis.addWidget(load_data)
        root.addLayout(analysis)
        controls = QHBoxLayout()
        controls.addStretch(1)
        ok = QPushButton("OK")
        ok.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        controls.addWidget(ok)
        controls.addWidget(cancel)
        root.addLayout(controls)

    def _mode_changed(self, mode):
        if mode != "Collect Bandwidth":
            return
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).checkState() == Qt.Checked:
                for column in range(2, 5):
                    self.table.item(row, column).setText("4000")

    def _load_bandwidth_data(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Image Packer Bandwidth Data", "", "CSV Files (*.csv);;All Files (*.*)"
        )
        if not path:
            return
        try:
            text = Path(path).read_text(encoding="utf-8-sig")
            names = [self.table.item(row, 1).text() for row in range(self.table.rowCount())]
            report = analyze_bandwidth_csv(text, names)
        except OSError as exc:
            QMessageBox.warning(self, "Bandwidth Analysis", str(exc))
            return
        self.original_state["analysis"] = report
        self.original_state["data_source"] = path
        self.data_source.setText(path)
        self.mode.setCurrentText("Analyze Bandwidth")
        for row, name in enumerate(names[:2]):
            channels = report.get(name, [])
            if any(item.get("samples", 0) for item in channels):
                self.table.item(row, 0).setCheckState(Qt.Checked)
                for channel, item in enumerate(channels):
                    self.table.item(row, channel + 2).setText(
                        f"{float(item['recommended_max_bw']):g}"
                    )

    def _finish(self):
        selected = []
        max_bw = {}
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).checkState() != Qt.Checked:
                continue
            name = self.table.item(row, 1).text()
            try:
                values = [
                    float(self.table.item(row, column).text())
                    for column in range(2, 5)
                ]
            except (AttributeError, TypeError, ValueError):
                QMessageBox.warning(self, "Variable Noise Control", f"{name}: enter three MaxBW values.")
                return
            if any(not isfinite(value) or not 0 < value <= 10000 for value in values):
                QMessageBox.warning(
                    self,
                    "Variable Noise Control",
                    f"{name}: MaxBW values must be greater than 0 and no more than 10000.",
                )
                return
            selected.append(name)
            max_bw[name] = values
        enabled = self.mode.currentText() != "Disabled"
        if enabled and not 1 <= len(selected) <= 2:
            QMessageBox.warning(
                self,
                "Variable Noise Control",
                "Select one or two regions for Variable Noise Control.",
            )
            return
        self.result_state = {
            "enabled": enabled,
            "mode": self.mode.currentText(),
            "regions": selected if enabled else [],
            "max_bw": max_bw if enabled else {},
            "analysis": deepcopy(self.original_state.get("analysis", {})),
            "data_source": self.data_source.text().strip(),
        }
        self.accept()


class DecoupledChannelFusionDialog(QDialog):
    PARAMETERS = ["Noise", "Color", "Gradient", "MinDiff"]

    def __init__(self, state, region_names, parent=None):
        super().__init__(parent)
        self.result_state = None
        self.region_names = list(region_names)
        self.setWindowTitle("Decoupled Channel Fusion Parameters")
        self.resize(860, 520)
        root = QVBoxLayout(self)
        root.addWidget(
            QLabel(
                "Set independent Channel Fusion values for each region and channel. "
                "This option is valid only with HLAT or Secondary HLAT."
            )
        )
        headers = ["Region", "Channel"] + self.PARAMETERS + ["Postfilter"]
        self.table = QTableWidget(len(self.region_names) * 3, len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        row = 0
        for region_name in self.region_names:
            channels = state.get(region_name) or []
            for channel_index in range(3):
                values = channels[channel_index] if channel_index < len(channels) else {}
                self.table.setItem(row, 0, QTableWidgetItem(region_name))
                self.table.setItem(row, 1, QTableWidgetItem(f"Channel {channel_index + 1}"))
                for column, parameter in enumerate(self.PARAMETERS, start=2):
                    self.table.setItem(
                        row,
                        column,
                        QTableWidgetItem(f"{float(values.get(parameter, 0)):g}"),
                    )
                postfilter = QComboBox()
                postfilter.addItems(["None", "Off", "Weak", "Medium", "Strong"])
                postfilter.setCurrentText(values.get("Postfilter", "None"))
                self.table.setCellWidget(row, len(headers) - 1, postfilter)
                row += 1
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        root.addWidget(self.table, 1)
        controls = QHBoxLayout()
        controls.addStretch(1)
        ok = QPushButton("OK")
        ok.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        controls.addWidget(ok)
        controls.addWidget(cancel)
        root.addLayout(controls)

    def _finish(self):
        result = {name: [] for name in self.region_names}
        for row in range(self.table.rowCount()):
            region_name = self.table.item(row, 0).text()
            try:
                values = {
                    parameter: float(self.table.item(row, column).text())
                    for column, parameter in enumerate(self.PARAMETERS, start=2)
                }
            except (AttributeError, TypeError, ValueError):
                QMessageBox.warning(
                    self,
                    "Decoupled Channel Fusion",
                    f"{region_name}: all Channel Fusion values must be numeric.",
                )
                return
            if not all(isfinite(value) for value in values.values()):
                QMessageBox.warning(
                    self,
                    "Decoupled Channel Fusion",
                    f"{region_name}: Channel Fusion values must be finite.",
                )
                return
            values["Postfilter"] = self.table.cellWidget(row, 6).currentText()
            result[region_name].append(values)
        self.result_state = result
        self.accept()


class CibParametersDialog(QDialog):
    PARAMETERS = ["clip", "offset", "L0", "K"]

    def __init__(self, channels, parent=None):
        super().__init__(parent)
        self.result_state = None
        self.setWindowTitle("CIB and Preconvolver Parameters")
        self.resize(720, 300)
        root = QVBoxLayout(self)
        self.table = QTableWidget(3, 6)
        self.table.setHorizontalHeaderLabels(
            ["Channel", "Clip", "Offset", "L0", "K", "Preconvolver"]
        )
        for row in range(3):
            values = channels[row]
            self.table.setItem(row, 0, QTableWidgetItem(f"Channel {row + 1}"))
            for column, parameter in enumerate(self.PARAMETERS, start=1):
                self.table.setItem(
                    row,
                    column,
                    QTableWidgetItem(f"{float(values.get(parameter, 0)):g}"),
                )
            preconvolver = QComboBox()
            preconvolver.addItems(["None", "Weak", "Medium", "Strong"])
            preconvolver.setCurrentText(values.get("preconvolver", "None"))
            self.table.setCellWidget(row, 5, preconvolver)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        root.addWidget(self.table)
        controls = QHBoxLayout()
        controls.addStretch(1)
        ok = QPushButton("OK")
        ok.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        controls.addWidget(ok)
        controls.addWidget(cancel)
        root.addLayout(controls)

    def _finish(self):
        result = []
        for row in range(3):
            try:
                values = {
                    parameter: float(self.table.item(row, column).text())
                    for column, parameter in enumerate(self.PARAMETERS, start=1)
                }
            except (AttributeError, TypeError, ValueError):
                QMessageBox.warning(self, "CIB Parameters", "All CIB values must be numeric.")
                return
            if not all(isfinite(value) for value in values.values()):
                QMessageBox.warning(self, "CIB Parameters", "All CIB values must be finite.")
                return
            if values["L0"] < 0 or values["K"] <= 0:
                QMessageBox.warning(
                    self,
                    "CIB Parameters",
                    "L0 must be nonnegative and K must be positive.",
                )
                return
            values["preconvolver"] = self.table.cellWidget(row, 5).currentText()
            result.append(values)
        self.result_state = result
        self.accept()


class ChannelFusionFlavorDialog(QDialog):
    def __init__(self, state, algorithm, parent=None):
        super().__init__(parent)
        self.result_state = None
        self.setWindowTitle(f"{algorithm} Channel Fusion Flavors")
        self.resize(620, 320)
        root = QVBoxLayout(self)
        root.addWidget(QLabel("Enable at least one flavor before running Channel Fusion."))
        self.table = QTableWidget(len(state), 3)
        self.table.setHorizontalHeaderLabels(["Enable", "Flavor", "Threshold"])
        for row, flavor in enumerate(state):
            enabled = QTableWidgetItem("")
            enabled.setCheckState(Qt.Checked if flavor.get("enabled") else Qt.Unchecked)
            self.table.setItem(row, 0, enabled)
            self.table.setItem(row, 1, QTableWidgetItem(flavor.get("name", "")))
            self.table.setItem(row, 2, QTableWidgetItem(f"{float(flavor.get('threshold', 45)):g}"))
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        root.addWidget(self.table)
        controls = QHBoxLayout()
        controls.addStretch(1)
        ok = QPushButton("OK")
        ok.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        controls.addWidget(ok)
        controls.addWidget(cancel)
        root.addLayout(controls)

    def _finish(self):
        result = []
        for row in range(self.table.rowCount()):
            try:
                threshold = float(self.table.item(row, 2).text())
            except (AttributeError, TypeError, ValueError):
                QMessageBox.warning(self, "Channel Fusion", "Flavor thresholds must be numeric.")
                return
            if not isfinite(threshold) or threshold < 0:
                QMessageBox.warning(
                    self,
                    "Channel Fusion",
                    "Flavor thresholds must be finite and nonnegative.",
                )
                return
            result.append(
                {
                    "name": self.table.item(row, 1).text(),
                    "enabled": self.table.item(row, 0).checkState() == Qt.Checked,
                    "threshold": threshold,
                }
            )
        self.result_state = result
        self.accept()


class AdvancedAlgorithmParametersDialog(QDialog):
    """Editable view of the advanced sensitivity parameter hierarchy."""

    FIELD_SPECS = [
        ("EventJobHdr", "EnableNewRTA", ("runtime_alignment", "enable_new_rta"), "bool"),
        ("EventJobHdr", "MaxYInitShift", ("runtime_alignment", "max_y_init_shift"), "int"),
        ("EventJobHdr", "bEnableHistogramRemap", ("histogram_remap",), "bool"),
        ("PreProcessing", "PostFilter", ("post_filter",), "text"),
        ("PreProcessing", "Preconvolver", ("preconvolver",), "text"),
        ("Detection", "EnhancedSecondaryDie", ("enhanced_secondary_die",), "bool"),
        ("Detection", "SecondaryDieFactor", ("secondary_die_factor",), "float"),
        ("Detection", "DarkDefectFactor", ("dark_defect_factor",), "float"),
        ("DefectFilters", "RunProcessNoiseFilter", ("defect_filters", "run_process_noise_filter"), "bool"),
        ("DefectFilters", "Intensity", ("defect_filters", "intensity"), "float"),
        ("DefectFilters", "SideRatio", ("defect_filters", "side_ratio"), "float"),
        ("DefectFilters", "TopRatio", ("defect_filters", "top_ratio"), "float"),
    ]

    def __init__(self, state, parent=None):
        super().__init__(parent)
        region_names = list((state or {}).get("regions", {})) or None
        self.state = normalized_sensitivity_state(state, region_names)
        self.result_state = None
        self.setWindowTitle("Algorithm Parameters")
        self.resize(720, 560)
        root = QVBoxLayout(self)
        path = QLabel(
            "Algorithm > DarkFieldDetectionParameters. Double-click a Value to edit it."
        )
        root.addWidget(path)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Parameter", "Value"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        root.addWidget(self.tree, 1)

        algorithm = QTreeWidgetItem(["Algorithm", ""])
        detection = QTreeWidgetItem(["DarkFieldDetectionParameters", ""])
        algorithm.addChild(detection)
        self.tree.addTopLevelItem(algorithm)
        sections = {}
        self.parameter_items = []
        for section, label, value_path, value_type in self.FIELD_SPECS:
            parent_item = sections.get(section)
            if parent_item is None:
                parent_item = QTreeWidgetItem([section, ""])
                detection.addChild(parent_item)
                sections[section] = parent_item
            value = self._read_path(value_path)
            if value_type == "bool":
                text = "1" if value else "0"
            else:
                text = str(value)
            item = QTreeWidgetItem([label, text])
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            item.setData(1, Qt.UserRole, (value_path, value_type))
            parent_item.addChild(item)
            self.parameter_items.append(item)
        self.tree.expandAll()

        note = QLabel(
            "Boolean values use 0 or 1. PostFilter accepts None, Off, Weak, Medium, or Strong."
        )
        note.setWordWrap(True)
        root.addWidget(note)
        footer = QHBoxLayout()
        footer.addStretch(1)
        apply_button = QPushButton("OK")
        apply_button.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        footer.addWidget(apply_button)
        footer.addWidget(cancel)
        root.addLayout(footer)

    def _read_path(self, value_path):
        value = self.state
        for key in value_path:
            value = value[key]
        return value

    def _write_path(self, value_path, value):
        target = self.state
        for key in value_path[:-1]:
            target = target[key]
        target[value_path[-1]] = value

    def _finish(self):
        try:
            for item in self.parameter_items:
                value_path, value_type = item.data(1, Qt.UserRole)
                text = item.text(1).strip()
                if value_type == "bool":
                    if text.lower() not in {"0", "1", "false", "true", "off", "on"}:
                        raise ValueError(f"{item.text(0)} must be 0 or 1")
                    value = text.lower() in {"1", "true", "on"}
                elif value_type == "int":
                    value = int(text)
                elif value_type == "float":
                    value = float(text)
                else:
                    value = text
                self._write_path(value_path, value)
        except (TypeError, ValueError) as exc:
            QMessageBox.warning(self, "Algorithm Parameters", str(exc))
            return
        errors = validate_sensitivity(self.state)
        if errors:
            QMessageBox.warning(self, "Algorithm Parameters", "\n".join(errors))
            return
        self.result_state = deepcopy(self.state)
        self.accept()


class SensitivityDialog(QDialog):
    LATEST_FEATURE_VECTOR_VERSION = "3.0A"

    def __init__(
        self,
        state=None,
        region_names=None,
        parent=None,
        *,
        feature_vector_version="3.0A",
        segmentation_state=None,
    ):
        super().__init__(parent)
        self.state = normalized_sensitivity_state(state, region_names)
        self.result_state = None
        self.feature_vector_version = str(feature_vector_version or "")
        self.result_feature_vector_version = self.feature_vector_version
        self.segmentation_state = self._normalized_segmentation_state(
            segmentation_state, list(self.state["regions"])
        )
        self.result_segmentation_state = None
        self.segmentation_clipboard = None
        self.changed = False
        self.parameter_clipboard = None
        self.region_clipboard = None
        self._loading = False
        self._all_regions_selected = False
        self.setWindowTitle("Sensitivity Parameters")
        self.resize(1220, 760)
        self.setMinimumSize(1100, 680)
        self.setStyleSheet(
            "QDialog { background: #cfcbc2; font-family: Arial; font-size: 10px; }"
            "QPushButton { background: #e8e6dd; border: 1px solid #77736b; min-height: 27px; padding: 2px 8px; }"
            "QComboBox, QSpinBox, QDoubleSpinBox { min-height: 27px; }"
            "QTableWidget { background: #efefec; gridline-color: #aaa69d; }"
            "QHeaderView::section { background: #dad7cf; border: 1px solid #918d85; padding: 4px; }"
        )
        root = QVBoxLayout(self)
        selectors = QHBoxLayout()
        selectors.addWidget(QLabel("Algo"))
        self.algorithm = QComboBox()
        self.algorithm.addItems(self._available_algorithms())
        self.algorithm.currentTextChanged.connect(self._populate)
        self.algorithm.setMinimumWidth(210)
        selectors.addWidget(self.algorithm)
        selectors.addWidget(QLabel("Channel"))
        self.channel = QComboBox()
        self.channel.addItems(["Channel 1", "Channel 2", "Channel 3"])
        self.channel.currentIndexChanged.connect(self._populate)
        self.channel.setMinimumWidth(150)
        selectors.addWidget(self.channel)
        selectors.addWidget(QLabel("Parameter Object"))
        self.parameter_object = QComboBox()
        self.parameter_object.addItems(list(PARAMETER_OBJECTS))
        self.parameter_object.currentTextChanged.connect(self._populate)
        self.parameter_object.setMinimumWidth(130)
        selectors.addWidget(self.parameter_object)
        copy = QPushButton("Copy")
        copy.clicked.connect(self._copy)
        paste = QPushButton("Paste")
        paste.clicked.connect(self._paste)
        selectors.addWidget(copy)
        selectors.addWidget(paste)
        selectors.addStretch(1)
        self.algorithm_selectors = selectors

        tools = QHBoxLayout()
        defaults = QPushButton("Default Order")
        defaults.clicked.connect(self._defaults)
        apply_all = QPushButton("Apply to All Regions")
        apply_all.clicked.connect(self._apply_all)
        flavors = QPushButton("CF Flavors...")
        flavors.clicked.connect(self._fusion_flavors)
        advanced_algorithm = QPushButton("Advanced Algorithm Parameters...")
        advanced_algorithm.clicked.connect(self._advanced_algorithm_parameters)
        tools.addWidget(defaults)
        tools.addWidget(apply_all)
        tools.addWidget(flavors)
        tools.addWidget(advanced_algorithm)
        tools.addStretch(1)
        self.algorithm_tools = tools

        parameter_tools = QHBoxLayout()
        save_parameters = QPushButton("Save Parameters...")
        save_parameters.clicked.connect(self._save_parameters)
        load_parameters = QPushButton("Load Parameters...")
        load_parameters.clicked.connect(self._load_parameters)
        delete_parameters = QPushButton("Delete Parameters...")
        delete_parameters.clicked.connect(self._delete_parameters)
        self.fx_version_label = QLabel()
        self.upgrade_fx = QPushButton("Upgrade FX Version")
        self.upgrade_fx.clicked.connect(self._upgrade_fx_version)
        parameter_tools.addWidget(save_parameters)
        parameter_tools.addWidget(load_parameters)
        parameter_tools.addWidget(delete_parameters)
        parameter_tools.addStretch(1)
        parameter_tools.addWidget(self.fx_version_label)
        parameter_tools.addWidget(self.upgrade_fx)
        self.parameter_tools = parameter_tools
        region_tools = QHBoxLayout()
        region_tools.addWidget(QLabel("Select Region"))
        self.all_regions_button = QPushButton("All Regions")
        self.all_regions_button.setCheckable(True)
        self.all_regions_button.clicked.connect(self._select_all_regions)
        region_tools.addWidget(self.all_regions_button)
        self.region_buttons = {}
        for name in list(self.state["regions"])[:6]:
            button = QPushButton(name)
            button.setCheckable(True)
            button.clicked.connect(
                lambda checked=False, region=name: self._select_region(region)
            )
            self.region_buttons[name] = button
            region_tools.addWidget(button)
        self.region_selector = QComboBox()
        self.region_selector.addItems(list(self.state["regions"]))
        self.region_selector.setMinimumWidth(180)
        self.region_selector.currentTextChanged.connect(self._region_selected)
        previous_region = QPushButton("< Region")
        previous_region.clicked.connect(lambda: self._step_region(-1))
        next_region = QPushButton("Region >")
        next_region.clicked.connect(lambda: self._step_region(1))
        copy_region = QPushButton("Copy All")
        copy_region.clicked.connect(self._copy_region)
        paste_region = QPushButton("Paste All")
        paste_region.clicked.connect(self._paste_region)
        self.region_selector.setVisible(False)
        region_tools.addWidget(previous_region)
        region_tools.addWidget(next_region)
        region_tools.addWidget(copy_region)
        region_tools.addWidget(paste_region)
        region_tools.addStretch(1)
        root.addLayout(region_tools)
        region_options = QHBoxLayout()
        self.enable_remap = QCheckBox("Enable Remap for selected region")
        self.enable_remap.toggled.connect(self._remap_changed)
        region_options.addWidget(self.enable_remap)
        region_options.addStretch(1)
        self.region_options = region_options
        self.tabs = QTabWidget()
        self.tabs.addTab(self._define_segmentation_tab(), "Define Segmentation")
        algorithm_page = QWidget()
        algorithm_page_layout = QVBoxLayout(algorithm_page)
        algorithm_page_layout.setContentsMargins(0, 0, 0, 0)
        algorithm_scroll = QScrollArea()
        algorithm_scroll.setWidgetResizable(True)
        algorithm_content = QWidget()
        algorithm_layout = QVBoxLayout(algorithm_content)
        algorithm_layout.setContentsMargins(6, 6, 6, 6)
        algorithm_layout.addLayout(self.algorithm_selectors)
        algorithm_layout.addLayout(self.algorithm_tools)
        algorithm_layout.addLayout(self.parameter_tools)
        algorithm_layout.addLayout(self.region_options)
        algorithm_layout.addWidget(self._algorithm_check_panel())
        algorithm_layout.addWidget(self._algorithm_matrix_panel())
        self.parameter_summary = QLabel()
        self.parameter_summary.setWordWrap(True)
        self.parameter_summary.setVisible(False)
        algorithm_layout.addWidget(self.parameter_summary)
        self.table = QTableWidget()
        self.table.setVisible(False)
        self.table.verticalHeader().setVisible(False)
        self.table.itemChanged.connect(self._item_changed)
        self.table.currentCellChanged.connect(self._current_region_changed)
        algorithm_layout.addWidget(self.table, 1)
        self.sdi_panels = {}
        self.sdi_tables = {}
        self.sdi_run_checks = {}
        algorithm_layout.addWidget(self._single_die_panel("primary", "Single Die Inspection"))
        algorithm_layout.addWidget(
            self._single_die_panel("secondary", "Secondary Single Die Inspection")
        )
        lower = QHBoxLayout()
        self.global_parameters_panel = self._advanced_panel()
        lower.addWidget(self.global_parameters_panel)
        self.defect_filter_panel = self._defect_filter_panel()
        lower.addWidget(self.defect_filter_panel)
        algorithm_layout.addLayout(lower)
        algorithm_scroll.setWidget(algorithm_content)
        algorithm_page_layout.addWidget(algorithm_scroll)
        self.tabs.addTab(algorithm_page, "Algorithm Parameters")
        root.addWidget(self.tabs, 1)
        footer = QHBoxLayout()
        self.validation = QLabel()
        footer.addWidget(self.validation, 1)
        finish = QPushButton("OK")
        finish.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        footer.addWidget(finish)
        footer.addWidget(cancel)
        root.addLayout(footer)
        self._populate()
        self._populate_segmentation_table()
        self._refresh_fx_version()
        self._sync_region_buttons()

    def _algorithm_check_panel(self):
        panel = QFrame()
        panel.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        layout = QGridLayout(panel)
        self.algorithm_checks = {}
        row = 0
        for group_name, algorithms in ALGORITHM_GROUPS.items():
            heading = QLabel(group_name)
            heading.setStyleSheet("font-weight: bold;")
            layout.addWidget(heading, row, 0)
            for column, algorithm in enumerate(algorithms, start=1):
                check = QCheckBox(algorithm)
                check.toggled.connect(
                    lambda checked, name=algorithm: self._algorithm_toggled(name, checked)
                )
                self.algorithm_checks[algorithm] = check
                layout.addWidget(check, row, column)
            layout.setColumnStretch(len(algorithms) + 1, 1)
            row += 1
        return panel

    def _algorithm_matrix_panel(self):
        panel = QFrame()
        panel.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        layout = QVBoxLayout(panel)
        heading = QHBoxLayout()
        title = QLabel("Channel / Segment Algorithm Parameters")
        title.setStyleSheet("font-weight: bold;")
        heading.addWidget(title)
        heading.addStretch(1)
        heading.addWidget(QLabel("Selection supports direct cell editing and Copy/Paste."))
        layout.addLayout(heading)
        self.algorithm_matrix = QTableWidget()
        self.algorithm_matrix.verticalHeader().setVisible(False)
        self.algorithm_matrix.setMinimumHeight(205)
        self.algorithm_matrix.itemChanged.connect(self._algorithm_matrix_changed)
        layout.addWidget(self.algorithm_matrix)
        return panel

    def _single_die_panel(self, mode_name, title):
        panel = QFrame()
        panel.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        layout = QVBoxLayout(panel)
        header = QHBoxLayout()
        label = QLabel(title)
        label.setStyleSheet("font-weight: bold;")
        header.addWidget(label)
        run_sdi = QCheckBox("Run SDI")
        run_cf_sdi = QCheckBox("Run CF SDI")
        run_sdi.toggled.connect(
            lambda checked, mode=mode_name: self._set_sdi_run(mode, "run_sdi", checked)
        )
        run_cf_sdi.toggled.connect(
            lambda checked, mode=mode_name: self._set_sdi_run(mode, "run_cf_sdi", checked)
        )
        header.addWidget(run_sdi)
        header.addWidget(run_cf_sdi)
        header.addStretch(1)
        layout.addLayout(header)
        table = QTableWidget(3, 15)
        table.setHorizontalHeaderLabels(
            ["Parameter"]
            + [f"Ch{channel} Seg{segment}" for channel in range(1, 4) for segment in range(2)]
            + [f"{flavor} Seg{segment}" for flavor in SDI_FUSION_NAMES for segment in range(2)]
        )
        table.setVerticalHeaderLabels(["Threshold", "Run / Enable", "Segment Mask"])
        table.setMinimumHeight(142)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        table.itemChanged.connect(
            lambda item, mode=mode_name: self._sdi_table_changed(mode, item)
        )
        layout.addWidget(table)
        self.sdi_panels[mode_name] = panel
        self.sdi_tables[mode_name] = table
        self.sdi_run_checks[mode_name] = (run_sdi, run_cf_sdi)
        return panel

    def _populate_algorithm_matrix(self):
        if not hasattr(self, "algorithm_matrix") or not self.state["regions"]:
            return
        algorithm = self.algorithm.currentText()
        if not algorithm:
            return
        region_name = self._selected_region()
        config = self.state["regions"][region_name]["algorithms"][algorithm]
        parameters = ALGORITHM_PARAMETERS[algorithm]
        headers = (
            ["Algorithm Parameter"]
            + [f"Channel {channel} {object_name}" for channel in range(1, 4) for object_name in PARAMETER_OBJECTS]
            + ["Channel Fusion Sens"]
        )
        self.algorithm_matrix.blockSignals(True)
        self.algorithm_matrix.clear()
        self.algorithm_matrix.setColumnCount(len(headers))
        self.algorithm_matrix.setHorizontalHeaderLabels(headers)
        self.algorithm_matrix.setRowCount(len(parameters) + 1)
        for row, parameter in enumerate(parameters):
            label = "Abs Min" if parameter == "ABSMIN" else parameter
            self.algorithm_matrix.setItem(row, 0, QTableWidgetItem(label))
            for column in range(1, 10):
                channel_index = (column - 1) // 3
                object_name = PARAMETER_OBJECTS[(column - 1) % 3]
                values = (
                    config["channels"][channel_index]
                    if object_name == "Sensitivity"
                    else config["segments"][channel_index][object_name]
                )
                self.algorithm_matrix.setItem(
                    row, column, QTableWidgetItem(f"{float(values.get(parameter, 0)):g}")
                )
            fusion_values = self.state["decoupled_cf"][region_name][0]
            fusion_item = QTableWidgetItem(
                f"{float(fusion_values[parameter]):g}" if parameter in fusion_values else "--"
            )
            if parameter not in fusion_values:
                fusion_item.setFlags(Qt.ItemIsEnabled)
            self.algorithm_matrix.setItem(row, 10, fusion_item)
        run_row = len(parameters)
        self.algorithm_matrix.setItem(run_row, 0, QTableWidgetItem("Run"))
        for column in range(1, 10):
            channel_index = (column - 1) // 3
            object_name = PARAMETER_OBJECTS[(column - 1) % 3]
            run_item = QTableWidgetItem("")
            run_item.setCheckState(
                Qt.Checked
                if config["segment_run"][channel_index].get(object_name, config.get("run"))
                else Qt.Unchecked
            )
            self.algorithm_matrix.setItem(run_row, column, run_item)
        fusion_run = QTableWidgetItem("")
        if algorithm in {"HLAT", "Secondary HLAT"}:
            fusion_run.setCheckState(
                Qt.Checked if self.state.get("decouple_channel_fusion") else Qt.Unchecked
            )
            fusion_run.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
        else:
            fusion_run.setText("--")
            fusion_run.setFlags(Qt.ItemIsEnabled)
        self.algorithm_matrix.setItem(run_row, 10, fusion_run)
        self.algorithm_matrix.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.algorithm_matrix.blockSignals(False)

    def _algorithm_matrix_changed(self, item):
        if self._loading or item.column() == 0 or not self.state["regions"]:
            return
        algorithm = self.algorithm.currentText()
        region_name = self._selected_region()
        config = self.state["regions"][region_name]["algorithms"][algorithm]
        parameters = ALGORITHM_PARAMETERS[algorithm]
        if item.row() == len(parameters):
            checked = item.checkState() == Qt.Checked
            if item.column() == 10:
                if algorithm not in {"HLAT", "Secondary HLAT"}:
                    return
                self.state["decouple_channel_fusion"] = checked
                self.decouple_cf.setChecked(checked)
            else:
                fusion_algorithm = _fusion_base_algorithm(algorithm)
                if checked and fusion_algorithm in {"CF2", "CF3"} and not any(
                    flavor.get("enabled")
                    for flavor in self.state["fusion_flavors"][fusion_algorithm]
                ):
                    QMessageBox.warning(
                        self,
                        "Channel Fusion",
                        f"Enable at least one {algorithm} Channel Fusion Flavor first.",
                    )
                    self._populate_algorithm_matrix()
                    return
                if checked and algorithm in EXCLUSIVE_ALGORITHMS:
                    conflicts = self._exclusive_conflicts(algorithm)
                    if conflicts:
                        QMessageBox.warning(
                            self,
                            "Sensitivity Algorithm",
                            f"{algorithm} cannot run with {', '.join(sorted(conflicts))}.",
                        )
                        self._populate_algorithm_matrix()
                        return
                channel_index = (item.column() - 1) // 3
                object_name = PARAMETER_OBJECTS[(item.column() - 1) % 3]
                config["segment_run"][channel_index][object_name] = checked
                config["run"] = any(
                    enabled
                    for channel in config["segment_run"]
                    for enabled in channel.values()
                )
            self.changed = True
            self._sync_algorithm_checks()
            self._refresh_validation()
            return
        parameter = parameters[item.row()]
        try:
            value = float(item.text())
        except ValueError:
            self._populate_algorithm_matrix()
            return
        if item.column() == 10:
            self.state["decoupled_cf"][region_name][0][parameter] = value
        else:
            channel_index = (item.column() - 1) // 3
            object_name = PARAMETER_OBJECTS[(item.column() - 1) % 3]
            values = (
                config["channels"][channel_index]
                if object_name == "Sensitivity"
                else config["segments"][channel_index][object_name]
            )
            values[parameter] = value
        self.changed = True
        self._populate()

    def _populate_sdi_panels(self):
        if not hasattr(self, "sdi_tables"):
            return
        self._loading = True
        for mode_name, table in self.sdi_tables.items():
            mode = self.state["single_die_inspection"][mode_name]
            run_sdi, run_cf_sdi = self.sdi_run_checks[mode_name]
            for control, checked in ((run_sdi, mode["run_sdi"]), (run_cf_sdi, mode["run_cf_sdi"])):
                control.blockSignals(True)
                control.setChecked(bool(checked))
                control.blockSignals(False)
            table.blockSignals(True)
            table.setItem(0, 0, QTableWidgetItem("Threshold"))
            table.setItem(1, 0, QTableWidgetItem("Run / Enable"))
            table.setItem(2, 0, QTableWidgetItem("Segment Mask"))
            for column in range(1, 7):
                channel_index = (column - 1) // 2
                segment_index = (column - 1) % 2
                segment = mode["channels"][channel_index]["segments"][segment_index]
                table.setItem(0, column, QTableWidgetItem(f"{float(segment['threshold']):g}"))
                run_item = QTableWidgetItem("")
                run_item.setCheckState(Qt.Checked if segment.get("run") else Qt.Unchecked)
                table.setItem(1, column, run_item)
                unavailable = QTableWidgetItem("--")
                unavailable.setFlags(Qt.ItemIsEnabled)
                table.setItem(2, column, unavailable)
            for column in range(7, 15):
                flavor_index = (column - 7) // 2
                segment_index = (column - 7) % 2
                flavor = mode["fusion"][SDI_FUSION_NAMES[flavor_index]]["segments"][segment_index]
                table.setItem(0, column, QTableWidgetItem(f"{float(flavor['threshold']):g}"))
                enabled_item = QTableWidgetItem("")
                enabled_item.setCheckState(Qt.Checked if flavor.get("enabled") else Qt.Unchecked)
                table.setItem(1, column, enabled_item)
                mask = QComboBox()
                mask.addItems(["Ch1", "Ch2", "Ch3", "Ch1+Ch2", "Ch1+Ch3", "Ch2+Ch3"])
                mask.setCurrentText(flavor.get("mask", "Ch1"))
                mask.currentTextChanged.connect(
                    lambda value, mode_key=mode_name, f_index=flavor_index, s_index=segment_index:
                    self._set_sdi_mask(mode_key, f_index, s_index, value)
                )
                table.setCellWidget(2, column, mask)
            table.blockSignals(False)
        self._loading = False

    def _set_sdi_run(self, mode_name, key, checked):
        if self._loading:
            return
        self.state["single_die_inspection"][mode_name][key] = bool(checked)
        self.changed = True
        self._refresh_validation()

    def _set_sdi_mask(self, mode_name, flavor_index, segment_index, value):
        if self._loading:
            return
        flavor_name = SDI_FUSION_NAMES[flavor_index]
        self.state["single_die_inspection"][mode_name]["fusion"][flavor_name]["segments"][segment_index]["mask"] = value
        self.changed = True

    def _sdi_table_changed(self, mode_name, item):
        if self._loading or item.column() == 0 or item.row() > 1:
            return
        mode = self.state["single_die_inspection"][mode_name]
        if item.column() <= 6:
            channel_index = (item.column() - 1) // 2
            segment_index = (item.column() - 1) % 2
            target = mode["channels"][channel_index]["segments"][segment_index]
            key = "threshold" if item.row() == 0 else "run"
        else:
            flavor_index = (item.column() - 7) // 2
            segment_index = (item.column() - 7) % 2
            target = mode["fusion"][SDI_FUSION_NAMES[flavor_index]]["segments"][segment_index]
            key = "threshold" if item.row() == 0 else "enabled"
        if item.row() == 0:
            try:
                target[key] = float(item.text())
            except ValueError:
                self._populate_sdi_panels()
                return
        else:
            target[key] = item.checkState() == Qt.Checked
        self.changed = True
        self._refresh_validation()

    @staticmethod
    def _normalized_segmentation_state(state, region_names):
        result = deepcopy(state) if isinstance(state, dict) else {}
        result.setdefault("sites", [])
        regions = result.setdefault("regions", {})
        result.setdefault("sdi", {"groups": {}, "image_box": [0.20, 0.20, 0.35, 0.35]})
        result.setdefault("valid", False)
        for name in region_names or ["Default"]:
            region = regions.setdefault(name, {})
            channels = list(region.get("channels") or [])
            while len(channels) < 3:
                channels.append(
                    {
                        "type": "Off",
                        "breaks": [],
                        "source": "Own Channel",
                        "dilation": 0,
                        "dilation_x": 0,
                        "dilation_y": 0,
                    }
                )
            region["channels"] = channels[:3]
            for channel in region["channels"]:
                channel.setdefault("type", "Off")
                channel.setdefault("breaks", [])
                channel.setdefault("source", "Own Channel")
                channel.setdefault("dilation", 0)
                channel.setdefault("dilation_x", channel["dilation"])
                channel.setdefault("dilation_y", 0)
        return result

    def _define_segmentation_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        toolbar = QHBoxLayout()
        self.segmentation_type = QComboBox()
        self.segmentation_type.addItems(
            [
                "Off",
                "Median Based Segmentation",
                "Projection Based Segmentation",
                "Median-Edge Based Segmentation",
            ]
        )
        self.segmentation_type.currentTextChanged.connect(self._segmentation_type_changed)
        toolbar.addWidget(QLabel("Segmentation Type"))
        toolbar.addWidget(self.segmentation_type)
        for label, handler in [
            ("Copy", self._copy_segmentation_map),
            ("Paste", self._paste_segmentation_map),
            ("Insert Vertical Break", lambda: self._insert_segmentation_break("X")),
            ("Insert Horizontal Break", lambda: self._insert_segmentation_break("Y")),
            ("Clear All", self._clear_segmentation_map),
        ]:
            button = QPushButton(label)
            button.clicked.connect(handler)
            toolbar.addWidget(button)
        self.group_color_coding = QCheckBox("Group Color Coding")
        self.group_color_coding.setChecked(True)
        toolbar.addWidget(self.group_color_coding)
        toolbar.addStretch(1)
        layout.addLayout(toolbar)

        self.segmentation_table = QTableWidget(3, 7)
        self.segmentation_table.setHorizontalHeaderLabels(
            [
                "Channel Enable",
                "Channel",
                "Breaks / Group IDs",
                "Use Segments From Channel",
                "Projection Dilation X",
                "Projection Dilation Y",
                "Set Break Position",
            ]
        )
        self.segmentation_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.segmentation_table.verticalHeader().setVisible(False)
        self.segmentation_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.segmentation_table.setMinimumHeight(250)
        layout.addWidget(self.segmentation_table, 1)
        hint = QLabel(
            "Select a channel row, then insert, move, copy, paste, or delete Segment breaks. "
            "All enabled channels in one region use the same Segmentation Type."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)
        return page

    def _segmentation_region(self):
        return self.segmentation_state["regions"][self._selected_region()]

    def _selected_segmentation_channel(self):
        row = self.segmentation_table.currentRow()
        return max(0, min(2, row if row >= 0 else 0))

    def _populate_segmentation_table(self):
        if not hasattr(self, "segmentation_table"):
            return
        self._loading = True
        region = self._segmentation_region()
        active_type = next(
            (channel["type"] for channel in region["channels"] if channel["type"] != "Off"),
            "Off",
        )
        self.segmentation_type.setCurrentText(active_type)
        selected_row = max(0, self.segmentation_table.currentRow())
        for row, channel in enumerate(region["channels"]):
            enabled = QCheckBox()
            enabled.setChecked(channel.get("type", "Off") != "Off")
            enabled.toggled.connect(
                lambda checked, index=row: self._segmentation_channel_enabled(index, checked)
            )
            self.segmentation_table.setCellWidget(row, 0, enabled)
            self.segmentation_table.setItem(row, 1, QTableWidgetItem(f"Channel {row + 1}"))
            breaks = channel.get("breaks", [])
            summary = ", ".join(
                f"{item.get('axis', 'X')} {float(item.get('position', 0.5)):.3f} / G{int(item.get('group', 0))}"
                for item in breaks
            ) or "Seg0 only"
            self.segmentation_table.setItem(row, 2, QTableWidgetItem(summary))
            source = QComboBox()
            source.addItems(["Own Channel", "Channel 1", "Channel 2", "Channel 3"])
            source.setCurrentText(channel.get("source", "Own Channel"))
            cross_channel = channel.get("type") in {
                "Projection Based Segmentation", "Median-Edge Based Segmentation"
            }
            source.setEnabled(cross_channel)
            source.currentTextChanged.connect(
                lambda value, index=row: self._segmentation_source_changed(index, value)
            )
            self.segmentation_table.setCellWidget(row, 3, source)
            for column, key in ((4, "dilation_x"), (5, "dilation_y")):
                dilation = QSpinBox()
                dilation.setRange(-64, 64)
                dilation.setValue(int(channel.get(key, 0)))
                dilation.setEnabled(cross_channel)
                dilation.valueChanged.connect(
                    lambda value, index=row, field=key: self._segmentation_dilation_changed(index, field, value)
                )
                self.segmentation_table.setCellWidget(row, column, dilation)
            position = QDoubleSpinBox()
            position.setRange(0.01, 0.99)
            position.setDecimals(3)
            position.setSingleStep(0.01)
            position.setValue(float(breaks[-1].get("position", 0.5)) if breaks else 0.5)
            position.setEnabled(bool(breaks))
            position.valueChanged.connect(
                lambda value, index=row: self._segmentation_position_changed(index, value)
            )
            self.segmentation_table.setCellWidget(row, 6, position)
        self.segmentation_table.selectRow(min(selected_row, 2))
        self._loading = False

    def _segmentation_type_changed(self, value):
        if self._loading:
            return
        for channel in self._segmentation_region()["channels"]:
            if channel.get("type", "Off") != "Off":
                if channel["type"] != value:
                    channel["breaks"] = []
                channel["type"] = value
                if value not in {"Projection Based Segmentation", "Median-Edge Based Segmentation"}:
                    channel["source"] = "Own Channel"
        self.changed = True
        self._populate_segmentation_table()

    def _segmentation_channel_enabled(self, index, checked):
        if self._loading:
            return
        channel = self._segmentation_region()["channels"][index]
        if checked:
            selected_type = self.segmentation_type.currentText()
            channel["type"] = selected_type if selected_type != "Off" else "Median Based Segmentation"
            if selected_type == "Off":
                self.segmentation_type.setCurrentText(channel["type"])
        else:
            channel["type"] = "Off"
            channel["breaks"] = []
            channel["source"] = "Own Channel"
        self.changed = True
        self._populate_segmentation_table()

    def _segmentation_source_changed(self, index, value):
        if not self._loading:
            self._segmentation_region()["channels"][index]["source"] = value
            self.changed = True

    def _segmentation_dilation_changed(self, index, key, value):
        if not self._loading:
            channel = self._segmentation_region()["channels"][index]
            channel[key] = int(value)
            if key == "dilation_x":
                channel["dilation"] = int(value)
            self.changed = True

    def _segmentation_position_changed(self, index, value):
        if self._loading:
            return
        breaks = self._segmentation_region()["channels"][index]["breaks"]
        if breaks:
            breaks[-1]["position"] = float(value)
            self.changed = True
            self._populate_segmentation_table()

    def _insert_segmentation_break(self, axis):
        channel = self._segmentation_region()["channels"][self._selected_segmentation_channel()]
        if channel.get("type", "Off") == "Off":
            QMessageBox.warning(self, "Define Segmentation", "Enable the selected channel first.")
            return
        if channel["type"] == "Median Based Segmentation":
            axis = "Histogram"
        channel["breaks"].append(
            {
                "axis": axis,
                "position": min(0.9, 0.3 + len(channel["breaks"]) * 0.2),
                "group": len(channel["breaks"]) + 1,
            }
        )
        self.changed = True
        self._populate_segmentation_table()

    def _copy_segmentation_map(self):
        self.segmentation_clipboard = deepcopy(
            self._segmentation_region()["channels"][self._selected_segmentation_channel()]
        )

    def _paste_segmentation_map(self):
        if self.segmentation_clipboard is None:
            QMessageBox.information(self, "Define Segmentation", "Copy a channel Segmentation Map first.")
            return
        index = self._selected_segmentation_channel()
        copied = deepcopy(self.segmentation_clipboard)
        selected_type = self.segmentation_type.currentText()
        if selected_type != "Off":
            copied["type"] = selected_type
        self._segmentation_region()["channels"][index] = copied
        self.changed = True
        self._populate_segmentation_table()

    def _clear_segmentation_map(self):
        channel = self._segmentation_region()["channels"][self._selected_segmentation_channel()]
        channel["breaks"] = []
        self.changed = True
        self._populate_segmentation_table()

    def _refresh_fx_version(self):
        self.fx_version_label.setText(
            f"FX Version: {self.feature_vector_version or '-'}"
        )
        self.upgrade_fx.setEnabled(
            self.feature_vector_version != self.LATEST_FEATURE_VECTOR_VERSION
        )

    def _upgrade_fx_version(self):
        self.feature_vector_version = self.LATEST_FEATURE_VECTOR_VERSION
        self.result_feature_vector_version = self.feature_vector_version
        self.changed = True
        self._refresh_fx_version()

    def _advanced_panel(self):
        panel = QFrame()
        panel.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        layout = QGridLayout(panel)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)
        layout.addWidget(QLabel("Advanced Settings"), 0, 0, 1, 4)
        self.histogram_remap = QCheckBox("Histogram Remap")
        self.histogram_remap.setChecked(bool(self.state.get("histogram_remap", True)))
        self.histogram_remap.toggled.connect(lambda value: self._set_value("histogram_remap", value))
        layout.addWidget(self.histogram_remap, 1, 0, 1, 2)
        cib = QPushButton("CIB / Preconvolver...")
        cib.clicked.connect(self._cib_settings)
        layout.addWidget(cib, 1, 2, 1, 2)
        self.autosens_mode = QComboBox()
        self.autosens_mode.addItems(["Production", "Engineering"])
        self.autosens_mode.setCurrentText(self.state.get("autosens_mode", "Production"))
        self.autosens_mode.currentTextChanged.connect(
            lambda value: self._set_value("autosens_mode", value)
        )
        layout.addWidget(QLabel("AutoSens"), 2, 0)
        layout.addWidget(self.autosens_mode, 2, 1)
        self.enhanced_secondary = QCheckBox("Enhanced Secondary Die")
        self.enhanced_secondary.setChecked(bool(self.state.get("enhanced_secondary_die")))
        self.enhanced_secondary.toggled.connect(self._secondary_changed)
        layout.addWidget(self.enhanced_secondary, 2, 2, 1, 2)
        self.secondary_factor = QDoubleSpinBox()
        self.secondary_factor.setRange(0.1, 10.0)
        self.secondary_factor.setValue(float(self.state.get("secondary_die_factor", 1.0)))
        self.secondary_factor.valueChanged.connect(lambda value: self._set_value("secondary_die_factor", value))
        layout.addWidget(QLabel("Secondary Die Factor"), 3, 0)
        layout.addWidget(self.secondary_factor, 3, 1)
        self.secondary_factor.setEnabled(not self.enhanced_secondary.isChecked())
        self.variable_noise = QCheckBox("Variable Noise Control")
        self.variable_noise.setChecked(bool(self.state.get("vnc", {}).get("enabled")))
        self.variable_noise.toggled.connect(self._vnc_enabled)
        layout.addWidget(self.variable_noise, 4, 0, 1, 2)
        self.vnc_settings_button = QPushButton("VNC Settings...")
        self.vnc_settings_button.clicked.connect(self._vnc_settings)
        layout.addWidget(self.vnc_settings_button, 4, 2, 1, 2)
        self.decouple_cf = QCheckBox("Decouple Channel Fusion")
        self.decouple_cf.setChecked(bool(self.state.get("decouple_channel_fusion")))
        self.decouple_cf.toggled.connect(self._decoupled_cf_changed)
        layout.addWidget(self.decouple_cf, 5, 0, 1, 2)
        self.decoupled_button = QPushButton("Decoupled CF Parameters...")
        self.decoupled_button.clicked.connect(self._decoupled_settings)
        layout.addWidget(self.decoupled_button, 5, 2, 1, 2)
        rta = self.state["runtime_alignment"]
        self.enable_rta = QCheckBox("Enable RTA+")
        self.enable_rta.setChecked(bool(rta.get("enable_new_rta", True)))
        self.enable_rta.toggled.connect(self._set_rta_enabled)
        layout.addWidget(self.enable_rta, 6, 0, 1, 2)
        self.max_y_init_shift = QSpinBox()
        self.max_y_init_shift.setRange(0, 1)
        self.max_y_init_shift.setValue(int(rta.get("max_y_init_shift", 0)))
        self.max_y_init_shift.valueChanged.connect(self._set_rta_shift)
        self.max_y_init_shift.setEnabled(self.enable_rta.isChecked())
        layout.addWidget(QLabel("MaxYInitShift"), 6, 2)
        layout.addWidget(self.max_y_init_shift, 6, 3)
        self.post_filter = QComboBox()
        self.post_filter.addItems(["None", "Off", "Weak", "Medium", "Strong"])
        self.post_filter.setCurrentText(self.state.get("post_filter", "None"))
        self.post_filter.currentTextChanged.connect(
            lambda value: self._set_value("post_filter", value)
        )
        layout.addWidget(QLabel("Post Filter"), 7, 0)
        layout.addWidget(self.post_filter, 7, 1)
        self.dark_defect_factor = QDoubleSpinBox()
        self.dark_defect_factor.setRange(0.001, 100.0)
        self.dark_defect_factor.setDecimals(3)
        self.dark_defect_factor.setValue(float(self.state.get("dark_defect_factor", 1.0)))
        self.dark_defect_factor.valueChanged.connect(
            lambda value: self._set_value("dark_defect_factor", value)
        )
        layout.addWidget(QLabel("Dark Defect Factor"), 7, 2)
        layout.addWidget(self.dark_defect_factor, 7, 3)
        return panel

    def _defect_filter_panel(self):
        panel = QFrame()
        panel.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        layout = QGridLayout(panel)
        layout.addWidget(QLabel("Defect Filters"), 0, 0, 1, 2)
        values = self.state["defect_filters"]
        self.process_filter = QCheckBox("Run Process Noise Filter")
        self.process_filter.setChecked(bool(values.get("run_process_noise_filter")))
        self.process_filter.toggled.connect(
            lambda value: self._set_filter("run_process_noise_filter", value)
        )
        layout.addWidget(self.process_filter, 1, 0, 1, 2)
        self.filter_controls = {}
        for row, (key, label, default) in enumerate([
            ("intensity", "Intensity", 0.0),
            ("side_ratio", "Side Ratio", 1.0),
            ("top_ratio", "Top Ratio", 1.0),
        ], start=2):
            control = QDoubleSpinBox()
            control.setRange(0.0, 10000.0)
            control.setDecimals(3)
            control.setValue(float(values.get(key, default)))
            control.setEnabled(self.process_filter.isChecked())
            control.valueChanged.connect(lambda value, name=key: self._set_filter(name, value))
            self.filter_controls[key] = control
            layout.addWidget(QLabel(label), row, 0)
            layout.addWidget(control, row, 1)
        return panel

    def _set_value(self, key, value):
        self.state[key] = value
        self.changed = True

    def _set_filter(self, key, value):
        self.state["defect_filters"][key] = value
        if key == "run_process_noise_filter" and hasattr(self, "filter_controls"):
            for control in self.filter_controls.values():
                control.setEnabled(bool(value))
        self.changed = True

    def _set_rta_enabled(self, enabled):
        self.state["runtime_alignment"]["enable_new_rta"] = bool(enabled)
        self.max_y_init_shift.setEnabled(bool(enabled))
        self.changed = True

    def _set_rta_shift(self, value):
        self.state["runtime_alignment"]["max_y_init_shift"] = int(value)
        self.changed = True

    def _secondary_changed(self, checked):
        self.state["enhanced_secondary_die"] = bool(checked)
        self.secondary_factor.setEnabled(not checked)
        self.changed = True
        self._refresh_algorithm_choices()

    def _decoupled_cf_changed(self, checked):
        self._set_value("decouple_channel_fusion", checked)
        self.decoupled_button.setEnabled(
            self.decouple_cf.isEnabled() and bool(checked)
        )

    def _remap_changed(self, checked):
        if self._loading:
            return
        self.state["regions"][self._selected_region()]["enable_remap"] = bool(checked)
        self.changed = True

    def _sync_remap(self):
        if not hasattr(self, "enable_remap") or not self.state["regions"]:
            return
        self.enable_remap.blockSignals(True)
        self.enable_remap.setChecked(
            bool(self.state["regions"][self._selected_region()].get("enable_remap"))
        )
        self.enable_remap.blockSignals(False)

    def _current_region_changed(self, row, *_args):
        if 0 <= row < len(self.state["regions"]):
            self.region_selector.blockSignals(True)
            self.region_selector.setCurrentIndex(row)
            self.region_selector.blockSignals(False)
        self._sync_remap()

    def _region_selected(self, name):
        names = list(self.state["regions"])
        if name in names and hasattr(self, "table"):
            self._all_regions_selected = False
            self.table.setCurrentCell(names.index(name), 0)
            self._populate_segmentation_table()
            self._sync_algorithm_checks()
            self._populate_algorithm_matrix()
            self._sync_region_buttons()

    def _select_all_regions(self):
        self._all_regions_selected = True
        self._sync_region_buttons()

    def _select_region(self, name):
        self._all_regions_selected = False
        self.region_selector.setCurrentText(name)
        self._sync_region_buttons()

    def _sync_region_buttons(self):
        if not hasattr(self, "region_buttons"):
            return
        selected = self.region_selector.currentText()
        self.all_regions_button.blockSignals(True)
        self.all_regions_button.setChecked(self._all_regions_selected)
        self.all_regions_button.blockSignals(False)
        for name, button in self.region_buttons.items():
            button.blockSignals(True)
            button.setChecked(not self._all_regions_selected and name == selected)
            button.blockSignals(False)
        if hasattr(self, "global_parameters_panel"):
            self.global_parameters_panel.setVisible(self._all_regions_selected)

    def _step_region(self, amount):
        count = self.region_selector.count()
        if count:
            self.region_selector.setCurrentIndex(
                max(0, min(count - 1, self.region_selector.currentIndex() + amount))
            )

    def _copy_region(self):
        name = self._selected_region()
        self.region_clipboard = {
            "sensitivity": deepcopy(self.state["regions"][name]),
            "segmentation": deepcopy(self.segmentation_state["regions"][name]),
        }

    def _paste_region(self):
        if self.region_clipboard is None:
            QMessageBox.information(
                self, "Paste Region Parameters", "Copy Region parameters before pasting."
            )
            return
        name = self._selected_region()
        if "sensitivity" in self.region_clipboard:
            self.state["regions"][name] = deepcopy(self.region_clipboard["sensitivity"])
            self.segmentation_state["regions"][name] = deepcopy(
                self.region_clipboard["segmentation"]
            )
        else:
            self.state["regions"][name] = deepcopy(self.region_clipboard)
        self.changed = True
        self._populate()
        self._populate_segmentation_table()

    def _available_algorithms(self):
        return list(ALGORITHM_PARAMETERS)

    def _algorithm_toggled(self, algorithm, checked):
        if self._loading:
            return
        region_name = self.region_selector.currentText() or next(iter(self.state["regions"]))
        config = self.state["regions"][region_name]["algorithms"][algorithm]
        if checked and algorithm in SECONDARY_ALGORITHMS:
            self.state["enhanced_secondary_die"] = True
            self.enhanced_secondary.blockSignals(True)
            self.enhanced_secondary.setChecked(True)
            self.enhanced_secondary.blockSignals(False)
            self.secondary_factor.setEnabled(False)
        fusion_algorithm = _fusion_base_algorithm(algorithm)
        if checked and fusion_algorithm in {"CF2", "CF3"} and not any(
            flavor.get("enabled") for flavor in self.state["fusion_flavors"][fusion_algorithm]
        ):
            QMessageBox.warning(
                self,
                "Channel Fusion",
                f"Enable at least one {algorithm} Channel Fusion Flavor first.",
            )
            self._sync_algorithm_checks()
            return
        if checked and algorithm in EXCLUSIVE_ALGORITHMS:
            for region in self.state["regions"].values():
                for other in EXCLUSIVE_ALGORITHMS - {algorithm}:
                    other_config = region["algorithms"][other]
                    other_config["run"] = False
                    for channel_runs in other_config["segment_run"]:
                        for object_name in channel_runs:
                            channel_runs[object_name] = False
        config["run"] = bool(checked)
        for channel_runs in config["segment_run"]:
            for object_name in channel_runs:
                channel_runs[object_name] = bool(checked)
        if algorithm in self._available_algorithms():
            self.algorithm.setCurrentText(algorithm)
        self.changed = True
        self._populate()

    def _sync_algorithm_checks(self):
        if not hasattr(self, "algorithm_checks"):
            return
        region_name = self.region_selector.currentText() or next(iter(self.state["regions"]))
        algorithms = self.state["regions"][region_name]["algorithms"]
        for algorithm, check in self.algorithm_checks.items():
            check.blockSignals(True)
            check.setVisible(True)
            check.setChecked(bool(algorithms[algorithm].get("run")))
            check.blockSignals(False)

    def _parameter_values(self, config):
        channel_index = self.channel.currentIndex()
        object_name = self.parameter_object.currentText() or "Sensitivity"
        if object_name == "Sensitivity":
            return config["channels"][channel_index]
        return config["segments"][channel_index][object_name]

    def _refresh_algorithm_choices(self):
        current = self.algorithm.currentText()
        self.algorithm.blockSignals(True)
        self.algorithm.clear()
        self.algorithm.addItems(self._available_algorithms())
        if current in self._available_algorithms():
            self.algorithm.setCurrentText(current)
        self.algorithm.blockSignals(False)
        self._sync_algorithm_checks()
        self._populate()

    def _advanced_algorithm_parameters(self):
        dialog = AdvancedAlgorithmParametersDialog(self.state, self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result != QDialog.Accepted:
            return
        self.state = normalized_sensitivity_state(
            dialog.result_state, list(self.state["regions"])
        )
        self.histogram_remap.setChecked(bool(self.state.get("histogram_remap", True)))
        self.post_filter.setCurrentText(self.state.get("post_filter", "None"))
        self.enhanced_secondary.setChecked(bool(self.state.get("enhanced_secondary_die")))
        self.secondary_factor.setValue(float(self.state.get("secondary_die_factor", 1.0)))
        self.dark_defect_factor.setValue(float(self.state.get("dark_defect_factor", 1.0)))
        self.enable_rta.setChecked(
            bool(self.state["runtime_alignment"].get("enable_new_rta", True))
        )
        self.max_y_init_shift.setValue(
            int(self.state["runtime_alignment"].get("max_y_init_shift", 0))
        )
        self.changed = True
        self._refresh_algorithm_choices()

    def _vnc_enabled(self, checked):
        self.state["variable_noise_control"] = bool(checked)
        vnc = self.state["vnc"]
        vnc["enabled"] = bool(checked)
        vnc["mode"] = "Apply" if checked else "Disabled"
        if checked and not vnc["regions"]:
            name = next(iter(self.state["regions"]))
            vnc["regions"] = [name]
            vnc["max_bw"][name] = [100.0, 100.0, 100.0]
        self.changed = True
        self._refresh_validation()

    def _vnc_settings(self):
        dialog = VariableNoiseControlDialog(self.state["vnc"], list(self.state["regions"]), self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.state["vnc"] = dialog.result_state
            self.state["variable_noise_control"] = dialog.result_state["enabled"]
            self.variable_noise.setChecked(dialog.result_state["enabled"])
            self.changed = True
            self._refresh_validation()

    def _save_parameters(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Sensitivity Parameter Set", "Sensitivity.sens", "Sensitivity Parameters (*.sens)"
        )
        if not path:
            return
        target = Path(path)
        if target.suffix.lower() != ".sens":
            target = target.with_suffix(".sens")
        try:
            target.write_text(serialize_sensitivity_state(self.state), encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(self, "Sensitivity Parameter Set", str(exc))

    def _load_parameters(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Sensitivity Parameter Set", "", "Sensitivity Parameters (*.sens);;All Files (*.*)"
        )
        if not path:
            return
        try:
            loaded = parse_sensitivity_state(
                Path(path).read_text(encoding="utf-8"), list(self.state["regions"])
            )
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Sensitivity Parameter Set", str(exc))
            return
        self.state = loaded
        self.histogram_remap.setChecked(bool(self.state.get("histogram_remap", True)))
        self.enhanced_secondary.setChecked(bool(self.state.get("enhanced_secondary_die")))
        self.secondary_factor.setValue(float(self.state.get("secondary_die_factor", 1.0)))
        self.variable_noise.setChecked(bool(self.state["vnc"].get("enabled")))
        self.decouple_cf.setChecked(bool(self.state.get("decouple_channel_fusion")))
        self.enable_rta.setChecked(bool(self.state["runtime_alignment"].get("enable_new_rta", True)))
        self.max_y_init_shift.setValue(int(self.state["runtime_alignment"].get("max_y_init_shift", 0)))
        self.post_filter.setCurrentText(self.state.get("post_filter", "None"))
        self.dark_defect_factor.setValue(float(self.state.get("dark_defect_factor", 1.0)))
        self.changed = True
        self._refresh_algorithm_choices()

    def _delete_parameters(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Delete Sensitivity Parameter Set", "", "Sensitivity Parameters (*.sens)"
        )
        if not path:
            return
        answer = QMessageBox.question(
            self,
            "Delete Sensitivity Parameter Set",
            f"Delete {Path(path).name}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        try:
            Path(path).unlink()
        except OSError as exc:
            QMessageBox.warning(self, "Sensitivity Parameter Set", str(exc))

    def _decoupled_settings(self):
        dialog = DecoupledChannelFusionDialog(
            self.state["decoupled_cf"],
            list(self.state["regions"]),
            self,
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.state["decoupled_cf"] = dialog.result_state
            self.state["decouple_channel_fusion"] = True
            self.decouple_cf.setChecked(True)
            self.changed = True
            self._refresh_validation()

    def _cib_settings(self):
        dialog = CibParametersDialog(self.state["cib"], self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.state["cib"] = dialog.result_state
            self.changed = True
            self._refresh_validation()

    def _fusion_flavors(self):
        algorithm = self.algorithm.currentText()
        fusion_algorithm = _fusion_base_algorithm(algorithm)
        if fusion_algorithm not in {"CF2", "CF3"}:
            QMessageBox.information(
                self,
                "Channel Fusion",
                "Select CF2 or CF3 to configure Channel Fusion Flavors.",
            )
            return
        dialog = ChannelFusionFlavorDialog(
            self.state["fusion_flavors"][fusion_algorithm],
            fusion_algorithm,
            self,
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.state["fusion_flavors"][fusion_algorithm] = dialog.result_state
            self.changed = True
            self._refresh_validation()

    def _populate(self, *args):
        self._loading = True
        algorithm = self.algorithm.currentText()
        if not algorithm:
            self._loading = False
            return
        parameters = ALGORITHM_PARAMETERS[algorithm]
        object_name = self.parameter_object.currentText() or "Sensitivity"
        parameter_text = ", ".join(parameters) if parameters else "No editable numeric parameters"
        self.parameter_summary.setText(
            f"{algorithm} | {object_name} | Parameters: {parameter_text}"
        )
        headers = ["Region", "Run"] + parameters
        self.table.clear()
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(self.state["regions"]))
        channel_index = self.channel.currentIndex()
        for row, (name, region) in enumerate(self.state["regions"].items()):
            self.table.setItem(row, 0, QTableWidgetItem(name))
            config = region["algorithms"][algorithm]
            run = QTableWidgetItem("")
            run.setCheckState(Qt.Checked if config.get("run") else Qt.Unchecked)
            self.table.setItem(row, 1, run)
            if object_name == "Sensitivity":
                channel = config["channels"][channel_index]
            else:
                channel = config["segments"][channel_index][object_name]
            for column, parameter in enumerate(parameters, start=2):
                self.table.setItem(
                    row,
                    column,
                    QTableWidgetItem(f"{float(channel.get(parameter, 0)):g}"),
                )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._loading = False
        selected_row = max(0, self.region_selector.currentIndex())
        if self.table.rowCount():
            self.table.setCurrentCell(min(selected_row, self.table.rowCount() - 1), 0)
        self._sync_remap()
        self._sync_algorithm_checks()
        self._populate_algorithm_matrix()
        self._populate_sdi_panels()
        supports_decoupled = algorithm in {"HLAT", "Secondary HLAT"}
        self.decouple_cf.setEnabled(supports_decoupled)
        self.decoupled_button.setEnabled(
            supports_decoupled and self.decouple_cf.isChecked()
        )
        self.autosens_mode.setEnabled(algorithm == "AutoSens")
        self._refresh_validation()

    def _item_changed(self, item):
        if self._loading or item.row() >= len(self.state["regions"]):
            return
        region_name = list(self.state["regions"])[item.row()]
        algorithm = self.algorithm.currentText()
        config = self.state["regions"][region_name]["algorithms"][algorithm]
        if item.column() == 1:
            enabled = item.checkState() == Qt.Checked
            fusion_algorithm = _fusion_base_algorithm(algorithm)
            if enabled and fusion_algorithm in {"CF2", "CF3"} and not any(
                flavor.get("enabled")
                for flavor in self.state["fusion_flavors"][fusion_algorithm]
            ):
                QMessageBox.warning(
                    self,
                    "Channel Fusion",
                    f"Enable at least one {algorithm} Channel Fusion Flavor first.",
                )
                self._loading = True
                item.setCheckState(Qt.Unchecked)
                self._loading = False
                return
            if enabled and algorithm in EXCLUSIVE_ALGORITHMS:
                conflicts = self._exclusive_conflicts(algorithm)
                if conflicts:
                    QMessageBox.warning(
                        self,
                        "Sensitivity Algorithm",
                        f"{algorithm} cannot run with {', '.join(sorted(conflicts))}.",
                    )
                    self._loading = True
                    item.setCheckState(Qt.Unchecked)
                    self._loading = False
                    return
            config["run"] = enabled
            for channel_runs in config["segment_run"]:
                for object_name in channel_runs:
                    channel_runs[object_name] = enabled
        else:
            parameter = ALGORITHM_PARAMETERS[algorithm][item.column() - 2]
            try:
                self._parameter_values(config)[parameter] = float(item.text())
            except ValueError:
                self._populate()
                return
        self.changed = True
        self._refresh_validation()

    def _exclusive_conflicts(self, selected):
        conflicts = set()
        for region in self.state["regions"].values():
            for algorithm in EXCLUSIVE_ALGORITHMS - {selected}:
                if region["algorithms"][algorithm].get("run"):
                    conflicts.add(algorithm)
        return conflicts

    def _selected_region(self):
        row = self.table.currentRow()
        if row < 0:
            row = 0
        return list(self.state["regions"])[row]

    def _copy(self):
        region = self._selected_region()
        algorithm = self.algorithm.currentText()
        config = self.state["regions"][region]["algorithms"][algorithm]
        self.parameter_clipboard = deepcopy(self._parameter_values(config))

    def _paste(self):
        if self.parameter_clipboard is None:
            QMessageBox.information(self, "Paste Parameters", "Copy algorithm parameters first.")
            return
        region = self._selected_region()
        algorithm = self.algorithm.currentText()
        expected = set(ALGORITHM_PARAMETERS[algorithm])
        if set(self.parameter_clipboard) != expected:
            QMessageBox.warning(
                self,
                "Paste Parameters",
                "The copied parameters belong to a different algorithm.",
            )
            return
        config = self.state["regions"][region]["algorithms"][algorithm]
        object_name = self.parameter_object.currentText() or "Sensitivity"
        if object_name == "Sensitivity":
            config["channels"][self.channel.currentIndex()] = deepcopy(
                self.parameter_clipboard
            )
        else:
            config["segments"][self.channel.currentIndex()][object_name] = deepcopy(
                self.parameter_clipboard
            )
        self.changed = True
        self._populate()

    def _defaults(self):
        algorithm = self.algorithm.currentText()
        for region in self.state["regions"].values():
            region["algorithms"][algorithm] = _algorithm_defaults(algorithm)
        self.changed = True
        self._populate()

    def _apply_all(self):
        algorithm = self.algorithm.currentText()
        fusion_algorithm = _fusion_base_algorithm(algorithm)
        if fusion_algorithm in {"CF2", "CF3"} and not any(
            flavor.get("enabled")
            for flavor in self.state["fusion_flavors"][fusion_algorithm]
        ):
            QMessageBox.warning(
                self,
                "Channel Fusion",
                f"Enable at least one {algorithm} Channel Fusion Flavor first.",
            )
            return
        if algorithm in EXCLUSIVE_ALGORITHMS:
            for region in self.state["regions"].values():
                for other in EXCLUSIVE_ALGORITHMS - {algorithm}:
                    other_config = region["algorithms"][other]
                    other_config["run"] = False
                    for channel_runs in other_config["segment_run"]:
                        for object_name in channel_runs:
                            channel_runs[object_name] = False
        for region in self.state["regions"].values():
            config = region["algorithms"][algorithm]
            config["run"] = True
            for channel_runs in config["segment_run"]:
                for object_name in channel_runs:
                    channel_runs[object_name] = True
        self.changed = True
        self._populate()

    def _refresh_validation(self):
        errors = validate_sensitivity(self.state)
        if errors:
            self.validation.setText(" | ".join(errors))
            self.validation.setStyleSheet("color: #a82929;")
        else:
            self.validation.setText("Sensitivity parameters are valid.")
            self.validation.setStyleSheet("color: #11752a;")

    def _finish(self):
        errors = validate_sensitivity(self.state)
        if errors:
            QMessageBox.warning(self, "Sensitivity Parameters", "\n".join(errors))
            return
        self.result_state = deepcopy(self.state)
        self.segmentation_state["valid"] = any(
            channel.get("type", "Off") != "Off"
            for region in self.segmentation_state["regions"].values()
            for channel in region.get("channels", [])
        )
        self.result_segmentation_state = deepcopy(self.segmentation_state)
        self.result_feature_vector_version = self.feature_vector_version
        self.accept()

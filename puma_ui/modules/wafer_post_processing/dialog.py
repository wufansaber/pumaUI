from __future__ import annotations

import json
import os
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
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QIcon,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPainter,
    QPen,
    QPixmap,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QTimer,
    QTreeWidget,
    QTreeWidgetItem,
    Qt,
    QVBoxLayout,
    QWidget,
)


OPERATION_SCHEMAS = {
    "Venn": [
        ("default_tolerance_um", "Default Tolerance (um)", "float", 5.0),
        ("enable_multi_test", "Enable Multi-Test", "bool", False),
        ("clear_venn_ids", "Clear Venn IDs", "bool", True),
        ("test_groups", "Test Groups", "groups", [{
            "name": "Group_A",
            "tests": "All Tests",
            "use_default_tolerance": True,
            "tolerance_um": 5.0,
            "inspected_area_mode": "Area of Largest Test",
            "area_tests": "All Tests",
            "duplicate_mode": "Highest Intensity",
            "test_priority": "",
        }]),
        ("inspected_area_mode", "Inspected Area Mode", "choice", ("Area of Largest Test", ["Area of Largest Test", "Sum of Selected Test Areas"])),
        ("duplicate_mode", "Duplicate Mode", "choice", ("Highest Intensity", ["Highest Intensity", "Highest Prioritized Test ID"])),
    ],
    "Clustering": [
        ("auto_clustering", "Auto Clustering Enabled", "bool", True),
        ("minimum_defects", "Minimum Defects per Cluster", "int", 2),
        ("distance_threshold_um", "Distance Threshold (um)", "float", 0.0),
        ("second_pass_multiplier", "Second Pass Multiplier", "int", 3),
        ("cluster_within", "Cluster Within", "choice", ("All Tests", ["Each Test", "All Tests"])),
    ],
    "Defect Source Analysis": [
        ("same_lot_id", "Same Lot ID", "bool", True),
        ("same_wafer_id", "Same Wafer ID", "bool", True),
        ("same_scribe_id", "Same Scribe ID", "bool", False),
        ("search_mode", "Search Option", "choice", ("Point-Based Search", ["Point-Based Search", "Size-Based Search"])),
        ("tolerance_um", "Tolerance (um)", "float", 20.0),
        ("matching_mode", "Matching", "choice", ("All Defects Within Tolerance", ["All Defects Within Tolerance", "Single Defect Within Tolerance"])),
        ("layer_selection", "Layer Selection", "choice", ("All Previous", ["All Previous", "Previous N Layers", "Step IDs"])),
        ("previous_n_layers", "Previous N Layers", "int", 1),
        ("step_ids", "Selected Step IDs", "text", ""),
        ("last_scan_only", "Last Scan Only", "bool", True),
        ("pre_align", "Pre-Align", "choice", ("Using Die Grids", ["Using Die Grids", "Using Defects"])),
        ("remove_common_defects", "Remove Common Defects", "bool", False),
        ("dsa_plus", "Enable DSA+", "bool", False),
        ("upld_class_codes", "UPLD Class Codes", "text", "0"),
        ("reset_upld_class_codes", "Reset UPLD Class Codes to 0", "bool", False),
        ("upld_test_id", "Test ID for Previous Layer Defects", "int", 50),
        ("grab_optical_images", "Grab Optical Images", "bool", False),
        ("grab_reference_images", "Grab Reference Images", "bool", False),
        ("send_images_to_database", "Send Images to Database", "bool", False),
        ("maximum_images", "Maximum Number of Images", "int", 100),
    ],
    "Repeater Analysis": [
        ("algorithm", "Repeater Algorithm", "choice", ("Reticle Wafer", ["Reticle Wafer", "Wafer", "Reticle Row", "Die Row"])),
        ("x_tolerance_um", "X Tolerance (um)", "float", 5.0),
        ("y_tolerance_um", "Y Tolerance (um)", "float", 5.0),
        ("repeater_threshold", "Repeater Threshold", "int", 3),
    ],
    "CAG Code Assignment": [
        ("cag_name_code_map", "CAG Name to Code Mapping", "text", ""),
    ],
    "Spatial Population": [
        ("signature_category", "Signature Category", "choice", ("Scratch", ["Scratch", "Imported SSA Recipe"])),
        ("ssa_recipe", "SSA Recipe", "text", "Scratch"),
        ("class_code_map", "Macro Sig Class / Custom Class Name Map", "text", "1: Scratch"),
    ],
    "Population Arbitration": [
        ("exclude_codes", "Exclude Roughbin Codes", "text", ""),
        ("arbitrate_spatial_population", "Arbitrate Using Spatial Population", "bool", True),
    ],
    "Sampling": [
        ("review_sampling", "Review Sampling", "choice", ("None", ["None", "Precision", "Diversity", "Proportional", "Random/Class Code", "Trigger", "Smart"])),
        ("patch_sampling", "Patch Sampling", "choice", ("None", ["None", "Precision", "Diversity", "Proportional", "Random/Class Code", "Trigger", "Smart"])),
        ("patch_transfer_sampling", "Patch Image Transfer Sampling", "choice", ("None", ["None", "Precision", "Diversity", "Proportional", "Random/Class Code", "Trigger", "Smart"])),
        ("hi_res_sampling", "Hi-Res Image Sampling", "choice", ("None", ["None", "Precision", "Diversity", "Proportional", "Random/Class Code", "Trigger", "Smart"])),
        ("maximum_samples", "Maximum Samples", "int", 50),
        ("sample_within", "Sample Within", "choice", ("All Tests", ["Each Test", "All Tests"])),
        ("smart_diversity", "Smart Diversity Sampling", "bool", False),
        ("edge_die_percentage", "Percentage Sample Size from Edge Dies", "float", 0.0),
        ("precision_rules", "Precision Rule Sequence", "precision_rules", []),
        ("allow_filter_overlap", "Allow Filter Overlapping", "bool", False),
        ("sample_bin_assignment", "Sample Bin Assignment", "choice", ("Sampling Method", ["Sampling Method", "Unique Bin per Rule"])),
        ("overlapping_bin_assignment", "Overlapping Sample Bins", "choice", ("Last Rule", ["Last Rule", "New Unique Bin"])),
        ("method_settings", "Sampling Method Settings", "method_settings", {}),
    ],
    "Defect Limits": [
        ("override_wafer_limit", "Override Default Wafer Maximum", "bool", False),
        ("wafer_maximum_defects", "Wafer Maximum Defect Count", "int", 100000),
        ("override_test_limit", "Override Default Test Maximum", "bool", False),
        ("test_maximum_defects", "Test Maximum Defect Count", "int", 25000),
        ("remap_cag_to_test_id", "Remap CAG Code to Test ID", "bool", False),
    ],
    "Excursion Reduction": [
        ("rules", "Rule Sequence", "excursion_rules", []),
        ("expressions", "Reusable Expressions", "expressions", []),
        ("remove_non_sampled", "Remove Non-Sampled Defects from KLARF", "bool", True),
        ("data_transfer", "Data Transfer Option", "choice", ("Filtered Result", ["Filtered Result", "Full Result", "Both"])),
    ],
}

VENN_PAGE_HELP = (
    "<p style='margin:0 0 4px 0'><b>Edit Groups:</b> This will display a view to construct groups; "
    "Overlapping tests will be combined in a single group.<br>"
    "* Please note that the Venn ID attribute will not report TestIDs greater than 15.</p>"
    "<p style='margin:0 0 4px 0'><b>Tolerance:</b> Venn analysis will be performed to find common defects "
    "across tests that belong to the same group within the specified Tolerance.</p>"
    "<p style='margin:0 0 4px 0'><b>Enable Multi-Test:</b> Duplicates will be marked and automatically "
    "filtered out from Klarf and Review mode.<br>"
    "Clear the duplicate filter in Review to show the duplicates.</p>"
    "<p style='margin:0 0 4px 0'><b>Clear Venn ID's:</b> The Venn ID attribute will be cleared for all "
    "defects before performing Venn Analysis.</p>"
    "<p style='margin:0 0 4px 0'><b>Edit Parameters:</b> Pop up Edit parameter view to update Tolerance, "
    "Duplicate and Inspected Area Mode.<br>"
    "Unless explicitly changed, group default parameters are: Tolerance = Default, "
    "Duplicate = Prioritized test IDs, Inspected Area Mode = Largest Test.</p>"
    "<p style='margin:0'><b>Duplicate Mode:</b> Select the criteria for keeping the defect instance in "
    "each Union group, the rest will be marked as duplicates.</p>"
)

_VENN_DUPLICATE_LABELS = {
    "Highest Intensity": "Highest Intensity",
    "Highest Prioritized Test ID": "Highest Prioritized Test ID",
}
_VENN_AREA_LABELS = {
    "Area of Largest Test": "Area of Largest Test",
    "Sum of Selected Test Areas": "Sum of Selected Test Areas",
}


SAMPLING_METHOD_SCHEMAS = {
    "Diversity": [
        ("scheme", "Sampling Scheme", "choice", ("Discovery", ["Discovery", "Production"])),
        ("discovery_samples", "Defects to Sample", "int", 100),
        ("similar_samples", "Similar Defects to Sample", "int", 10),
        ("save_tiles", "Save Tiles", "bool", False),
        ("production_bins", "Number of Sample Bins", "int", 10),
        ("average_per_bin", "Average Defects per Bin", "int", 10),
        ("proportional_quota", "Allocate Quota Proportionally", "bool", True),
        ("diversification_attributes", "Diversification Attributes", "text", "Defect Size, Intensity"),
        ("directional_bias", "Directional Bias Attributes", "text", ""),
        ("density_groups", "Density Shaping Groups", "text", ""),
        ("dynamic_attributes", "Dynamic Shaping Attributes", "text", ""),
        ("dynamic_direction", "Dynamic Direction", "choice", ("Off", ["Off", "Away from Class Code", "Towards Class Code"])),
        ("dynamic_class_code", "Dynamic Class Code", "int", 0),
        ("limits", "Attribute Limits", "text", ""),
    ],
    "Proportional": [
        ("class_code", "Class Code to Sample", "choice", ("RoughClass", ["CAG Code", "Fine Class", "Fine Code", "Fine Super Group", "Macro Sig Class", "Manual", "Micro Sig Class", "RoughClass", "RoughGroup", "Rough Super Group", "Unsupervised"])),
        ("adders_only", "Adders Only", "bool", False),
        ("exclude_bins", "Exclude Bin Codes", "text", ""),
        ("include_size_range", "Include Size Range", "bool", False),
        ("minimum_size", "Minimum Size", "float", 0.0),
        ("maximum_size", "Maximum Size", "float", 500000000.0),
        ("maximum_per_wafer", "Maximum Defects per Wafer", "int", 100),
        ("maximum_per_die", "Maximum Defects per Die", "int", 5),
        ("percent_from_clusters", "Percentage from Clusters", "int", 10),
        ("maximum_per_cluster", "Maximum Defects per Cluster", "int", 5),
        ("sample_within", "Sample Within", "choice", ("All Tests", ["Each Test", "All Tests"])),
        ("back_fill", "Perform Backfilling", "bool", False),
    ],
    "Random/Class Code": [
        ("random_enabled", "Random Sampling Enabled", "bool", True),
        ("maximum_per_wafer", "Maximum Defects per Wafer", "int", 100),
        ("maximum_per_die", "Maximum Defects per Die", "int", 3),
        ("maximum_per_cluster", "Maximum Defects per Cluster", "int", 5),
        ("percent_from_clusters", "Percent from Clusters", "int", 50),
        ("minimum_size", "Minimum Defect Size", "float", 0.0),
        ("maximum_size", "Maximum Defect Size", "float", 500000000.0),
        ("adders_only", "Adders Only", "bool", False),
        ("back_fill", "Perform Back Filling", "bool", False),
        ("class_code_enabled", "Class Code Sampling Enabled", "bool", False),
        ("maximum_code_defects", "Maximum Code Defects", "int", 100),
        ("class_code_rows", "Class Code Categories / Codes", "text", "RoughClass: all nonzero, 100#"),
        ("class_adders_only", "Adders Only", "bool", False),
        ("class_back_fill", "Perform Back Filling", "bool", False),
        ("enable_limits", "Enable Limits", "bool", False),
        ("apply_limits_per_bin", "Apply Limits per Bin", "bool", False),
        ("code_maximum_per_die", "Code Maximum per Die", "int", 5),
        ("code_maximum_per_cluster", "Code Maximum per Cluster", "int", 5),
        ("code_percent_from_clusters", "Code Maximum Percent from Clusters", "int", 10),
    ],
    "Trigger": [
        ("defects_to_consider", "Defects to Consider", "choice", ("Total", ["Total", "Random"])),
        ("within_bin_code", "Only within Bin Code", "bool", False),
        ("bin_code", "Bin Code", "int", 0),
        ("defect_measure", "Defect Measure", "choice", ("Count", ["Count", "Density", "Percentage of Defective Dies"])),
        ("lower_bound", "Lower Zone Bound", "float", 0.0),
        ("upper_bound", "Upper Zone Bound", "float", 100.0),
        ("below_sampling", "Below Zone Sampling", "choice", ("None", ["None", "Random", "Proportional"])),
        ("within_sampling", "Within Zone Sampling", "choice", ("Random", ["None", "Random", "Proportional"])),
        ("above_sampling", "Above Zone Sampling", "choice", ("Proportional", ["None", "Random", "Proportional"])),
    ],
    "Smart": [
        ("target_samples", "Target Defects to Sample", "int", 100),
        ("sample_within", "Sample Within", "choice", ("All Tests", ["Each Test", "All Tests"])),
        ("smart_diversity", "Smart Diversity Sampling", "bool", False),
        ("edge_die_enabled", "Sample from Edge Dies", "bool", False),
        ("edge_die_percentage", "Percentage from Edge Dies", "float", 0.0),
    ],
}


DEFAULT_QUICK_FILTER = {
    "adder": "All",
    "clusters": "All",
    "bright": True,
    "dark": True,
    "regions": "All",
    "repeaters": "All",
    "tests": "All",
    "threshold_region": "All",
}

DEFECT_ATTRIBUTES = [
    "Defect Size",
    "Intensity",
    "Rough Class",
    "Rough Group",
    "Fine Class",
    "Test ID",
    "Region ID",
    "Channel",
    "Cluster ID",
    "Die X",
    "Die Y",
]


def _normalize_quick_filter(value):
    incoming = value if isinstance(value, dict) else {}
    result = {**DEFAULT_QUICK_FILTER, **deepcopy(incoming)}
    result["bright"] = bool(result["bright"])
    result["dark"] = bool(result["dark"])
    return result


def _string_list(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def _normalize_directional_bias(value):
    if isinstance(value, dict):
        return {
            str(key): str(direction)
            for key, direction in value.items()
            if str(direction) in ("High", "Low")
        }
    result = {}
    for item in _string_list(value):
        name, separator, direction = item.partition(":")
        if separator and direction.strip() in ("High", "Low"):
            result[name.strip()] = direction.strip()
    return result


def _normalize_density_groups(value):
    if isinstance(value, list):
        return [_string_list(group) for group in value if _string_list(group)]
    text = str(value or "").strip()
    return [_string_list(group) for group in text.split(";") if _string_list(group)]


def _normalize_limits(value):
    if isinstance(value, list):
        return [
            {"attribute": str(item.get("attribute") or "Defect Size"), "limit": float(item.get("limit", 0))}
            for item in value
            if isinstance(item, dict)
        ]
    return []


def _normalize_class_code_rows(value):
    if isinstance(value, list):
        rows = []
        for item in value:
            if not isinstance(item, dict):
                continue
            rows.append({
                "category": str(item.get("category") or "RoughClass"),
                "all_nonzero": bool(item.get("all_nonzero", False)),
                "code": str(item.get("code") or ""),
                "defects": int(item.get("defects", 100)),
                "unit": "%" if item.get("unit") == "%" else "#",
                "sample_all": bool(item.get("sample_all", False)),
            })
        return rows
    if str(value or "").strip():
        return [{
            "category": "RoughClass",
            "all_nonzero": True,
            "code": "",
            "defects": 100,
            "unit": "#",
            "sample_all": False,
        }]
    return []


def _default_parameters(schema):
    return {
        key: deepcopy(default[0] if kind == "choice" else default)
        for key, _label, kind, default in schema
    }


def _normalize_sampling_settings(value):
    incoming = value if isinstance(value, dict) else {}
    result = {
        method: {**_default_parameters(schema), **deepcopy(incoming.get(method, {}))}
        for method, schema in SAMPLING_METHOD_SCHEMAS.items()
    }
    diversity = result["Diversity"]
    diversity["diversification_attributes"] = _string_list(diversity["diversification_attributes"])
    diversity["directional_bias"] = _normalize_directional_bias(diversity["directional_bias"])
    diversity["density_groups"] = _normalize_density_groups(diversity["density_groups"])
    diversity["dynamic_attributes"] = _string_list(diversity["dynamic_attributes"])
    diversity["limits"] = _normalize_limits(diversity["limits"])
    result["Random/Class Code"]["class_code_rows"] = _normalize_class_code_rows(
        result["Random/Class Code"]["class_code_rows"]
    )
    return result


def _normalize_groups(value):
    if isinstance(value, list):
        groups = []
        for index, item in enumerate(value, start=1):
            if not isinstance(item, dict):
                continue
            groups.append({
                "name": str(item.get("name") or f"Group_{index}").replace(" ", "_"),
                "tests": str(item.get("tests") or "All Tests"),
                "use_default_tolerance": bool(item.get("use_default_tolerance", True)),
                "tolerance_um": float(item.get("tolerance_um", 5.0)),
                "inspected_area_mode": str(item.get("inspected_area_mode") or "Area of Largest Test"),
                "area_tests": str(item.get("area_tests", "All Tests")),
                "duplicate_mode": str(item.get("duplicate_mode") or "Highest Intensity"),
                "test_priority": str(item.get("test_priority") or ""),
            })
        return groups
    text = str(value or "").strip()
    if not text:
        return []
    name, separator, tests = text.partition(":")
    return [{
        "name": (name.strip() or "Group_1").replace(" ", "_"),
        "tests": tests.strip() if separator and tests.strip() else "All Tests",
        "use_default_tolerance": True,
        "tolerance_um": 5.0,
        "inspected_area_mode": "Area of Largest Test",
        "area_tests": "All Tests",
        "duplicate_mode": "Highest Intensity",
        "test_priority": "",
    }]


def _normalize_precision_rules(value):
    if not isinstance(value, list):
        text = str(value or "").strip()
        if not text:
            return []
        value = [{"name": "Imported_Rule", "filter": text}]
    rules = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            continue
        rules.append({
            "name": str(item.get("name") or f"Rule_{index}").replace(" ", "_"),
            "filter": str(item.get("filter") or "All Defects"),
            "filter_mode": str(item.get("filter_mode") or "Quick Filter"),
            "quick_filter": _normalize_quick_filter(item.get("quick_filter")),
            "sampling_method": str(item.get("sampling_method") or "Random Sampling"),
            "sampling_settings": _normalize_sampling_settings(item.get("sampling_settings")),
            "enabled": bool(item.get("enabled", True)),
            "back_fill": bool(item.get("back_fill", False)),
        })
    return rules


def _normalize_excursion_rules(value):
    if not isinstance(value, list):
        text = str(value or "").strip()
        if not text:
            return []
        value = [{"name": "Imported_Rule", "expression": text}]
    rules = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            continue
        rules.append({
            "name": str(item.get("name") or f"Rule_{index}").replace(" ", "_"),
            "expression": str(item.get("expression") or ""),
            "enabled": bool(item.get("enabled", True)),
        })
    return rules


def _normalize_expressions(value):
    if not isinstance(value, list):
        return []
    expressions = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            continue
        expressions.append({
            "name": str(item.get("name") or f"Expression_{index}").strip().replace(" ", "_"),
            "definition": str(item.get("definition") or item.get("expression") or "").strip(),
            "element": str(item.get("element") or "Defect Size"),
            "operator": str(item.get("operator") or ">"),
            "value": str(item.get("value") or "0"),
        })
    return expressions


def _normalize_special_parameters(operation):
    parameters = operation["parameters"]
    name = operation["name"]
    if name == "Venn":
        parameters["test_groups"] = _normalize_groups(parameters.get("test_groups"))
    elif name == "Sampling":
        parameters["precision_rules"] = _normalize_precision_rules(parameters.get("precision_rules"))
        parameters["method_settings"] = _normalize_sampling_settings(parameters.get("method_settings"))
    elif name == "Excursion Reduction":
        parameters["rules"] = _normalize_excursion_rules(parameters.get("rules"))
        parameters["expressions"] = _normalize_expressions(parameters.get("expressions"))
    return operation


IMPLICIT_ENABLE_OPERATIONS = {"Sampling", "Defect Limits"}


def implicit_operation_enabled(operation: dict) -> bool:
    """Sampling and Defect Limits have no list checkbox; their property page turns them on."""
    parameters = operation.get("parameters") or {}
    name = operation.get("name")
    if name == "Sampling":
        return any(
            parameters.get(key, "None") != "None"
            for key in (
                "review_sampling",
                "patch_sampling",
                "patch_transfer_sampling",
                "hi_res_sampling",
            )
        )
    if name == "Defect Limits":
        return any(
            parameters.get(key)
            for key in (
                "override_wafer_limit",
                "override_test_limit",
                "remap_cag_to_test_id",
            )
        )
    return bool(operation.get("enabled"))


def _default_operation(name):
    parameters = {}
    for key, label, kind, default in OPERATION_SCHEMAS[name]:
        parameters[key] = default[0] if kind == "choice" else default
    return _normalize_special_parameters({"name": name, "enabled": False, "parameters": parameters})


def default_wpp_state() -> dict:
    return {
        "template_name": "Default",
        "operations": [_default_operation(name) for name in OPERATION_SCHEMAS],
        "templates": {},
    }


def normalized_wpp_state(state: dict | None) -> dict:
    result = default_wpp_state()
    if isinstance(state, dict):
        result.update(deepcopy(state))
    existing = {item.get("name"): item for item in result.get("operations", [])}
    requested_order = [
        item.get("name")
        for item in result.get("operations", [])
        if item.get("name") in OPERATION_SCHEMAS
    ]
    requested_order.extend(name for name in OPERATION_SCHEMAS if name not in requested_order)
    result["operations"] = []
    for name in requested_order:
        operation = _default_operation(name)
        if name in existing:
            operation.update(deepcopy(existing[name]))
            operation["parameters"] = {
                **_default_operation(name)["parameters"],
                **deepcopy(existing[name].get("parameters", {})),
            }
        _normalize_special_parameters(operation)
        result["operations"].append(operation)
    result["templates"] = deepcopy(result.get("templates") or {})
    return result


def validate_wpp(state: dict, test_count=0) -> list[str]:
    errors = []
    enabled = {item["name"]: item for item in state.get("operations", []) if item.get("enabled")}
    if "Venn" in enabled:
        parameters = enabled["Venn"]["parameters"]
        if test_count < 2:
            errors.append("Venn requires at least two defined tests")
        if float(parameters.get("default_tolerance_um", 0)) <= 0:
            errors.append("Venn default tolerance must be greater than zero")
        if parameters.get("enable_multi_test"):
            groups = _normalize_groups(parameters.get("test_groups"))
            if not groups:
                errors.append("Multi-Test Venn requires at least one test group")
            names = [group["name"].strip().lower() for group in groups]
            if len(names) != len(set(names)):
                errors.append("Multi-Test Venn group names must be unique")
            if any(not group["tests"].strip() for group in groups):
                errors.append("Each Multi-Test Venn group requires selected tests")
            if any(not group["use_default_tolerance"] and group["tolerance_um"] <= 0 for group in groups):
                errors.append("Each Multi-Test Venn group tolerance must be greater than zero")
            if any(
                group["inspected_area_mode"] == "Sum of Selected Test Areas"
                and not group["area_tests"].strip()
                for group in groups
            ):
                errors.append("Each summed Multi-Test Venn area requires selected tests")
            if any(
                group["duplicate_mode"] == "Highest Prioritized Test ID"
                and not group["test_priority"].strip()
                for group in groups
            ):
                errors.append("Each prioritized Multi-Test Venn group requires a Test ID priority order")
            for group in groups:
                selected = {
                    item.strip() for item in group["tests"].split(",") if item.strip()
                }
                if "All Tests" in selected:
                    continue
                area_tests = {
                    item.strip() for item in group["area_tests"].split(",") if item.strip()
                }
                priorities = {
                    item.strip() for item in group["test_priority"].split(",") if item.strip()
                }
                if group["inspected_area_mode"] == "Sum of Selected Test Areas" and not area_tests <= selected:
                    errors.append(f"{group['name']} area tests must be selected in the group")
                if (
                    group["duplicate_mode"] == "Highest Prioritized Test ID"
                    and priorities
                    and not selected <= priorities
                ):
                    errors.append(f"{group['name']} priority must include every test in the group")
    if "Defect Source Analysis" in enabled:
        parameters = enabled["Defect Source Analysis"]["parameters"]
        if not any(parameters.get(key) for key in ("same_lot_id", "same_wafer_id", "same_scribe_id")):
            errors.append("Defect Source Analysis requires a Lot, Wafer, or Scribe ID match")
        if parameters.get("layer_selection") == "Previous N Layers" and int(parameters.get("previous_n_layers", 0)) < 1:
            errors.append("DSA Previous N Layers must be greater than zero")
        if parameters.get("layer_selection") == "Step IDs" and not str(parameters.get("step_ids", "")).strip():
            errors.append("DSA Step IDs selection requires at least one Step ID")
        if parameters.get("dsa_plus") and int(parameters.get("upld_test_id", 0)) < 1:
            errors.append("DSA+ requires a valid Test ID for previous layer defects")
        if (parameters.get("grab_reference_images") or parameters.get("send_images_to_database")) and not parameters.get("grab_optical_images"):
            errors.append("DSA+ reference/database images require Grab Optical Images")
    if "Clustering" in enabled:
        parameters = enabled["Clustering"]["parameters"]
        if not parameters.get("auto_clustering"):
            if int(parameters.get("minimum_defects", 0)) < 2:
                errors.append("Minimum defects per cluster must be at least two")
            if not 100 <= float(parameters.get("distance_threshold_um", 0)) <= 5000:
                errors.append("Manual clustering distance threshold must be 100 to 5000 um")
        if not 1 <= int(parameters.get("second_pass_multiplier", 0)) <= 5:
            errors.append("Second pass multiplier must be between 1 and 5")
    if "Repeater Analysis" in enabled:
        parameters = enabled["Repeater Analysis"]["parameters"]
        if not 1 <= float(parameters.get("x_tolerance_um", 0)) <= 50:
            errors.append("Repeater X tolerance must be between 1 and 50 um")
        if not 1 <= float(parameters.get("y_tolerance_um", 0)) <= 50:
            errors.append("Repeater Y tolerance must be between 1 and 50 um")
        if not 2 <= int(parameters.get("repeater_threshold", 0)) <= 1000:
            errors.append("Repeater threshold must be between 2 and 1000")
    if "CAG Code Assignment" in enabled:
        mapping = enabled["CAG Code Assignment"]["parameters"].get("cag_name_code_map", "")
        if not str(mapping).strip():
            errors.append("CAG Code Assignment requires a valid CAG name/code mapping")
    if "Sampling" in enabled:
        parameters = enabled["Sampling"]["parameters"]
        schemes = (
            "review_sampling", "patch_sampling", "patch_transfer_sampling", "hi_res_sampling"
        )
        if not any(parameters.get(key, "None") != "None" for key in schemes):
            errors.append("Select a sampling method for at least one sampling scheme")
        if int(parameters.get("maximum_samples", 0)) < 1:
            errors.append("Sampling maximum samples must be greater than zero")
        if not 0 <= float(parameters.get("edge_die_percentage", 0)) <= 100:
            errors.append("Edge die sampling percentage must be between 0 and 100")
        if any(parameters.get(key) == "Precision" for key in schemes):
            rules = _normalize_precision_rules(parameters.get("precision_rules"))
            enabled_rules = [rule for rule in rules if rule["enabled"]]
            if not enabled_rules:
                errors.append("Precision Sampling requires at least one enabled rule")
            if any(not rule["name"].strip() or not rule["filter"].strip() for rule in enabled_rules):
                errors.append("Each enabled Precision Sampling rule requires a name and filter")
            rule_names = [rule["name"].lower() for rule in enabled_rules]
            if len(rule_names) != len(set(rule_names)):
                errors.append("Precision Sampling rule names must be unique")
            if any(rule["sampling_method"] not in PrecisionRulesDialog.METHODS for rule in enabled_rules):
                errors.append("Each Precision Sampling rule requires a supported sampling method")
        selected_methods = {parameters.get(key) for key in schemes}
        settings = _normalize_sampling_settings(parameters.get("method_settings"))
        if "Diversity" in selected_methods:
            diversity = settings["Diversity"]
            for key, label in (("discovery_samples", "Diversity defects to sample"), ("similar_samples", "Diversity similar defects")):
                if not 0 <= int(diversity[key]) <= 1000:
                    errors.append(f"{label} must be between 0 and 1000")
            if diversity["scheme"] == "Production" and (int(diversity["production_bins"]) < 1 or int(diversity["average_per_bin"]) < 1):
                errors.append("Diversity Production sampling requires positive bin count and average")
            if not diversity["diversification_attributes"]:
                errors.append("Diversity Sampling requires at least one diversification attribute")
        if "Random/Class Code" in selected_methods:
            random = settings["Random/Class Code"]
            maximum = int(random["maximum_per_wafer"])
            if not 0 <= maximum <= 65000:
                errors.append("Random maximum defects per wafer must be between 0 and 65000")
            if not 1 <= int(random["maximum_per_die"]) <= max(1, maximum):
                errors.append("Random maximum per die must be between 1 and the wafer maximum")
            if not 2 <= int(random["maximum_per_cluster"]) <= 65000:
                errors.append("Random maximum per cluster must be between 2 and 65000")
            if not 0 <= int(random["percent_from_clusters"]) <= 100:
                errors.append("Random percent from clusters must be between 0 and 100")
            if not 0 <= float(random["minimum_size"]) <= float(random["maximum_size"]) <= 500000000:
                errors.append("Random defect size range must be within 0 to 500000000")
            if random["class_code_enabled"]:
                if not 0 <= int(random["maximum_code_defects"]) <= 100:
                    errors.append("Class Code maximum defects must be between 0 and 100")
                class_rows = _normalize_class_code_rows(random["class_code_rows"])
                if not class_rows:
                    errors.append("Class Code Sampling requires at least one category or code row")
                if any(not row["all_nonzero"] and not row["code"].strip() for row in class_rows):
                    errors.append("Each Class Code row requires a code or All Nonzero")
                if any(row["unit"] == "%" and not 0 <= row["defects"] <= 100 for row in class_rows):
                    errors.append("Class Code percentage rows must be between 0 and 100")
        if "Proportional" in selected_methods:
            proportional = settings["Proportional"]
            maximum = int(proportional["maximum_per_wafer"])
            if maximum < 1 or int(proportional["maximum_per_die"]) < 1 or int(proportional["maximum_per_die"]) > maximum:
                errors.append("Proportional per-die maximum must not exceed its wafer maximum")
            if not 0 <= int(proportional["percent_from_clusters"]) <= 100:
                errors.append("Proportional cluster percentage must be between 0 and 100")
            if proportional["include_size_range"] and not 0 <= float(proportional["minimum_size"]) <= float(proportional["maximum_size"]):
                errors.append("Proportional minimum size must not exceed maximum size")
        if "Trigger" in selected_methods:
            trigger = settings["Trigger"]
            if float(trigger["lower_bound"]) > float(trigger["upper_bound"]):
                errors.append("Trigger lower zone bound must not exceed upper bound")
            if all(trigger[key] == "None" for key in ("below_sampling", "within_sampling", "above_sampling")):
                errors.append("Trigger Sampling requires a sampling action in at least one zone")
        if "Smart" in selected_methods:
            smart = settings["Smart"]
            if not 0 <= int(smart["target_samples"]) <= 1000:
                errors.append("Smart target defects must be between 0 and 1000")
            if smart["edge_die_enabled"] and not 0 <= float(smart["edge_die_percentage"]) <= 100:
                errors.append("Smart edge-die percentage must be between 0 and 100")
    if "Defect Limits" in enabled:
        parameters = enabled["Defect Limits"]["parameters"]
        wafer_limit = int(parameters.get("wafer_maximum_defects", 0))
        test_limit = int(parameters.get("test_maximum_defects", 0))
        if parameters.get("override_wafer_limit") and not 1 <= wafer_limit <= 100000:
            errors.append("Wafer maximum defect count must be between 1 and 100000")
        if parameters.get("override_test_limit") and not 1 <= test_limit <= 25000:
            errors.append("Test maximum defect count must be between 1 and 25000")
        if parameters.get("override_wafer_limit") and parameters.get("override_test_limit") and test_limit >= wafer_limit:
            errors.append("Test maximum defect count must be less than wafer maximum")
        if parameters.get("remap_cag_to_test_id") and "CAG Code Assignment" not in enabled:
            errors.append("CAG Code Assignment must be enabled before remapping CAG codes")
    if "Excursion Reduction" in enabled:
        excursion_parameters = enabled["Excursion Reduction"]["parameters"]
        rules = _normalize_excursion_rules(excursion_parameters.get("rules"))
        enabled_rules = [rule for rule in rules if rule["enabled"]]
        if not enabled_rules:
            errors.append("Excursion Reduction requires at least one enabled rule")
        elif any(not rule["name"].strip() or not rule["expression"].strip() for rule in enabled_rules):
            errors.append("Each enabled Excursion Reduction rule requires a name and expression")
        expressions = _normalize_expressions(excursion_parameters.get("expressions"))
        expression_names = [item["name"].lower() for item in expressions]
        if len(expression_names) != len(set(expression_names)):
            errors.append("Excursion Reduction expression names must be unique")
        if any(not item["name"] or not item["definition"] for item in expressions):
            errors.append("Every reusable expression requires a name and definition")
    return errors


def _format_um(value) -> str:
    number = float(value)
    if number == int(number):
        return str(int(number))
    return f"{number:g}"


def _venn_group_label(name: str) -> str:
    prefix = "Group_"
    if name.startswith(prefix) and name[len(prefix):]:
        return name[len(prefix):]
    return name


def _format_venn_test_ids(tests: str, test_count: int) -> str:
    text = str(tests or "").strip()
    if not text or text == "All Tests":
        count = max(int(test_count or 0), 0)
        if count <= 0:
            return "All" if text == "All Tests" else ""
        return ",".join(str(index) for index in range(1, count + 1))
    parts = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        if part.lower().startswith("test "):
            part = part[5:].strip()
        parts.append(part)
    return ",".join(parts)


def _unassigned_venn_tests(groups, test_count: int) -> str:
    if any(str(group.get("tests", "")).strip() == "All Tests" for group in groups):
        return ""
    assigned = set()
    for group in groups:
        for part in _format_venn_test_ids(group.get("tests", ""), test_count).split(","):
            if part:
                assigned.add(part)
    count = max(int(test_count or 0), 0)
    return ",".join(str(index) for index in range(1, count + 1) if str(index) not in assigned)


def _tolerance_text(group: dict) -> str:
    if group.get("use_default_tolerance", True):
        return "Default"
    return _format_um(group.get("tolerance_um", 0))


def _checkbox_indicator_style() -> str:
    folder = Path(os.environ.get("TEMP", "."))
    unchecked = folder / "puma-venn-checkbox-off.png"
    checked = folder / "puma-venn-checkbox-on.png"
    unchecked_disabled = folder / "puma-venn-checkbox-off-disabled.png"
    checked_disabled = folder / "puma-venn-checkbox-on-disabled.png"
    if not unchecked.exists() or not checked.exists():
        off = QPixmap(14, 14)
        off.fill(QColor("white"))
        painter = QPainter(off)
        painter.setPen(QPen(QColor("#404040")))
        painter.drawRect(0, 0, 13, 13)
        painter.end()
        off.save(str(unchecked))
        on = QPixmap(14, 14)
        on.fill(QColor("white"))
        painter = QPainter(on)
        painter.setPen(QPen(QColor("#404040")))
        painter.drawRect(0, 0, 13, 13)
        pen = QPen(QColor("#111111"))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawLine(3, 7, 6, 11)
        painter.drawLine(6, 11, 11, 3)
        painter.end()
        on.save(str(checked))
    if not unchecked_disabled.exists() or not checked_disabled.exists():
        off = QPixmap(14, 14)
        off.fill(QColor("#c8c4bc"))
        painter = QPainter(off)
        painter.setPen(QPen(QColor("#9a968e")))
        painter.drawRect(0, 0, 13, 13)
        painter.end()
        off.save(str(unchecked_disabled))
        on = QPixmap(14, 14)
        on.fill(QColor("#c8c4bc"))
        painter = QPainter(on)
        painter.setPen(QPen(QColor("#9a968e")))
        painter.drawRect(0, 0, 13, 13)
        pen = QPen(QColor("#8a8680"))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawLine(3, 7, 6, 11)
        painter.drawLine(6, 11, 11, 3)
        painter.end()
        on.save(str(checked_disabled))
    return (
        "QCheckBox::indicator { width: 14px; height: 14px; }"
        f"QCheckBox::indicator:unchecked {{ image: url({unchecked.as_posix()}); }}"
        f"QCheckBox::indicator:checked {{ image: url({checked.as_posix()}); }}"
        f"QCheckBox::indicator:unchecked:disabled {{ image: url({unchecked_disabled.as_posix()}); }}"
        f"QCheckBox::indicator:checked:disabled {{ image: url({checked_disabled.as_posix()}); }}"
        + _radio_indicator_style()
    )


def _radio_indicator_style() -> str:
    folder = Path(os.environ.get("TEMP", "."))
    unchecked = folder / "puma-venn-radio-off.png"
    checked = folder / "puma-venn-radio-on.png"
    if not unchecked.exists() or not checked.exists():
        off = QPixmap(14, 14)
        off.fill(Qt.transparent)
        painter = QPainter(off)
        painter.setPen(QPen(QColor("#404040")))
        painter.setBrush(QColor("white"))
        painter.drawEllipse(1, 1, 11, 11)
        painter.end()
        off.save(str(unchecked))
        on = QPixmap(14, 14)
        on.fill(Qt.transparent)
        painter = QPainter(on)
        painter.setPen(QPen(QColor("#404040")))
        painter.setBrush(QColor("white"))
        painter.drawEllipse(1, 1, 11, 11)
        painter.setBrush(QColor("#111111"))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(4, 4, 5, 5)
        painter.end()
        on.save(str(checked))
    return (
        "QRadioButton::indicator { width: 14px; height: 14px; }"
        f"QRadioButton::indicator:unchecked {{ image: url({unchecked.as_posix()}); }}"
        f"QRadioButton::indicator:checked {{ image: url({checked.as_posix()}); }}"
    )


def _match_catalog_name(token: str, catalog: list[str]) -> str:
    text = token.strip()
    for name in catalog:
        if name == text or name.lower() == f"test {text}".lower():
            return name
    if text.lower().startswith("test "):
        return text
    return f"Test {text}" if text else ""


def _venn_group_test_names(group: dict, catalog) -> list[str]:
    names = [str(name).strip() for name in (catalog or []) if str(name).strip()]
    text = str(group.get("tests") or "").strip()
    if not text or text == "All Tests":
        return names
    selected = []
    for part in text.split(","):
        match = _match_catalog_name(part, names)
        if match and match not in selected:
            selected.append(match)
    return selected or names


def _classic_toolbar_icon(kind: str) -> QIcon:
    pixmap = QPixmap(16, 16)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    if kind == "save":
        painter.fillRect(2, 3, 12, 10, QColor("#2d5f99"))
        painter.fillRect(4, 5, 8, 3, QColor("#f4f7fb"))
        painter.fillRect(5, 10, 6, 2, QColor("#d5deea"))
    elif kind == "delete":
        pen = QPen(QColor("#c41616"))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawLine(4, 4, 12, 12)
        painter.drawLine(12, 4, 4, 12)
    else:
        painter.fillRect(4, 2, 8, 12, QColor("white"))
        painter.setPen(QColor("#666666"))
        painter.drawRect(4, 2, 8, 12)
        painter.drawLine(8, 2, 12, 6)
        painter.drawLine(8, 2, 8, 6)
        painter.drawLine(8, 6, 12, 6)
    painter.end()
    return QIcon(pixmap)


def _exec_dialog(dialog):
    return dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()


def _blank_venn_group(name: str) -> dict:
    return {
        "name": name,
        "tests": [],
        "use_default_tolerance": True,
        "tolerance_um": 5.0,
        "inspected_area_mode": "Area of Largest Test",
        "area_tests": "All Tests",
        "duplicate_mode": "Highest Intensity",
        "test_priority": "",
    }


def _group_test_id_text(tests) -> str:
    labels = []
    for name in tests:
        text = str(name).strip()
        if text.lower().startswith("test "):
            text = text[5:].strip()
        if text:
            labels.append(text)
    return ", ".join(labels)


class MultiTestGroupsDialog(QDialog):
    def __init__(self, groups, tests=None, parent=None):
        super().__init__(parent)
        self.result_groups = None
        self._loading = False
        self.catalog = [str(name).strip() for name in (tests or []) if str(name).strip()]
        self.group_records = self._load_records(groups)
        self.setWindowTitle("Edit Groups")
        self.resize(560, 420)
        self.setMinimumSize(480, 340)
        self.setStyleSheet(
            "QDialog { background: #d4d0c8; font-family: Arial; font-size: 12px; }"
            "QPushButton { background: #ece9d8; border: 1px solid #808080; min-height: 26px; min-width: 72px; padding: 2px 12px; }"
            "QTableWidget { background: white; gridline-color: #b5b5b5; }"
            "QHeaderView::section { background: #d4d0c8; border: 1px solid #808080; padding: 3px; font-weight: normal; }"
            "QListWidget { background: white; border: 1px solid #808080; }"
            + _checkbox_indicator_style()
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        body = QHBoxLayout()
        body.setSpacing(16)
        left = QVBoxLayout()
        left_buttons = QHBoxLayout()
        new_group = QPushButton("New")
        new_group.clicked.connect(self._add)
        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self._delete)
        left_buttons.addWidget(new_group)
        left_buttons.addWidget(self.delete_button)
        left_buttons.addStretch(1)
        left.addLayout(left_buttons)
        self.table = QTableWidget(8, 2)
        self.table.setHorizontalHeaderLabels(["Group", "Test IDs"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.table.setColumnWidth(0, 90)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.currentCellChanged.connect(self._row_changed)
        left.addWidget(self.table, 1)
        body.addLayout(left, 3)

        right = QVBoxLayout()
        right_buttons = QHBoxLayout()
        self.all_button = QPushButton("All")
        self.all_button.clicked.connect(self._assign_all)
        self.none_button = QPushButton("None")
        self.none_button.clicked.connect(self._assign_none)
        right_buttons.addWidget(self.all_button)
        right_buttons.addWidget(self.none_button)
        right_buttons.addStretch(1)
        right.addLayout(right_buttons)
        self.test_checks = []
        self.test_host = QWidget()
        self.test_host.setStyleSheet("background: white;")
        checks = QVBoxLayout(self.test_host)
        checks.setContentsMargins(8, 6, 8, 6)
        checks.setSpacing(4)
        for name in self.catalog:
            box = QCheckBox(name)
            box.toggled.connect(lambda checked, test_name=name: self._test_toggled(test_name, checked))
            checks.addWidget(box)
            self.test_checks.append(box)
        checks.addStretch(1)
        self.test_list = QScrollArea()
        self.test_list.setWidgetResizable(True)
        self.test_list.setWidget(self.test_host)
        self.test_list.setStyleSheet("QScrollArea { background: white; border: 1px solid #808080; }")
        right.addWidget(self.test_list, 1)
        body.addLayout(right, 2)
        root.addLayout(body, 1)
        footer = QHBoxLayout()
        footer.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("OK")
        ok.setDefault(True)
        ok.clicked.connect(self._finish)
        footer.addWidget(cancel)
        footer.addWidget(ok)
        root.addLayout(footer)
        self._reload_table(0)

    def _match_test(self, token: str):
        text = str(token).strip()
        if not text or text == "All Tests":
            return None
        for name in self.catalog:
            if name == text or name.lower() == text.lower() or name.lower() == f"test {text}".lower():
                return name
        if self.catalog:
            return None
        label = f"Test {int(text)}" if text.isdigit() else text
        self.catalog.append(label)
        return label

    def _tests_from_text(self, text: str, claimed: set[str]) -> list[str]:
        names = []
        for part in str(text or "").split(","):
            match = self._match_test(part)
            if match and match not in claimed and match not in names:
                names.append(match)
                claimed.add(match)
        return names

    def _load_records(self, groups) -> list[dict]:
        incoming = _normalize_groups(groups)
        records = []
        claimed: set[str] = set()
        all_test_groups = []
        for group in incoming:
            record = dict(group)
            if str(group.get("tests") or "").strip() == "All Tests":
                record["tests"] = []
                all_test_groups.append(record)
            else:
                record["tests"] = self._tests_from_text(group.get("tests", ""), claimed)
            records.append(record)
        for record in all_test_groups:
            record["tests"] = [name for name in self.catalog if name not in claimed]
            claimed.update(record["tests"])
        if not records:
            records.append(_blank_venn_group("A") | {"tests": list(self.catalog)})
        return records

    def _selected_group_index(self):
        row = self.table.currentRow()
        if 0 <= row < len(self.group_records):
            return row
        return None

    def _set_row(self, row: int, name: str, test_ids: str):
        for column, text in enumerate((name, test_ids)):
            item = QTableWidgetItem(text)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, column, item)

    def _reload_table(self, select_row=0):
        self._loading = True
        self.table.setRowCount(max(8, len(self.group_records) + 1))
        self.table.clearContents()
        for row, group in enumerate(self.group_records):
            self._set_row(row, _venn_group_label(group["name"]), _group_test_id_text(group["tests"]))
        unassigned = [
            name for name in self.catalog
            if not any(name in group["tests"] for group in self.group_records)
        ]
        self._set_row(len(self.group_records), "None", _group_test_id_text(unassigned))
        target = select_row if 0 <= select_row < self.table.rowCount() else 0
        self.table.blockSignals(True)
        self.table.selectRow(target)
        self.table.blockSignals(False)
        self._loading = False
        self._show_checks()

    def _show_checks(self):
        self._loading = True
        index = self._selected_group_index()
        if index is None:
            assigned = {name for group in self.group_records for name in group["tests"]}
            selected = [name for name in self.catalog if name not in assigned]
        else:
            selected = list(self.group_records[index]["tests"])
        selected_names = set(selected)
        for box in self.test_checks:
            box.blockSignals(True)
            box.setChecked(box.text() in selected_names)
            box.setEnabled(index is not None)
            box.blockSignals(False)
        self.all_button.setEnabled(index is not None)
        self.none_button.setEnabled(index is not None)
        self.delete_button.setEnabled(index is not None)
        self._loading = False

    def _row_changed(self, row, _column, _previous_row, _previous_column):
        if self._loading:
            return
        if row > len(self.group_records):
            self.table.selectRow(len(self.group_records))
            return
        self._show_checks()

    def _test_toggled(self, name, checked):
        if self._loading:
            return
        index = self._selected_group_index()
        if index is None:
            self._show_checks()
            return
        for group in self.group_records:
            group["tests"] = [test for test in group["tests"] if test != name]
        if checked:
            order = {test: position for position, test in enumerate(self.catalog)}
            self.group_records[index]["tests"].append(name)
            self.group_records[index]["tests"].sort(key=lambda test: order.get(test, len(order)))
        self._reload_table(index)

    def _assign_all(self):
        index = self._selected_group_index()
        if index is None:
            return
        for group in self.group_records:
            group["tests"] = []
        self.group_records[index]["tests"] = list(self.catalog)
        self._reload_table(index)

    def _assign_none(self):
        index = self._selected_group_index()
        if index is None:
            return
        self.group_records[index]["tests"] = []
        self._reload_table(index)

    def _next_group_name(self) -> str:
        used = {_venn_group_label(group["name"]).upper() for group in self.group_records}
        for code in range(65, 91):
            letter = chr(code)
            if letter not in used:
                return letter
        return f"G{len(self.group_records) + 1}"

    def _add(self):
        self.group_records.append(_blank_venn_group(self._next_group_name()))
        self._reload_table(len(self.group_records) - 1)

    def _delete(self):
        index = self._selected_group_index()
        if index is None:
            return
        del self.group_records[index]
        self._reload_table(min(index, len(self.group_records)))

    def _finish(self):
        saved = []
        for group in self.group_records:
            if not group["tests"]:
                continue
            payload = dict(group)
            payload["tests"] = ", ".join(group["tests"])
            saved.append(payload)
        names = [group["name"].lower() for group in saved]
        if len(names) != len(set(names)):
            QMessageBox.warning(self, "Edit Groups", "Group names must be unique.")
            return
        self.result_groups = _normalize_groups(saved) if saved else []
        self.accept()


class VennGroupParametersDialog(QDialog):
    def __init__(self, group, tests=None, multi_test=False, parent=None):
        super().__init__(parent)
        self.group = _normalize_groups([group])[0]
        self.result_group = None
        self.multi_test = bool(multi_test)
        self.catalog = [str(name).strip() for name in (tests or []) if str(name).strip()]
        self.member_tests = _venn_group_test_names(self.group, self.catalog)
        self.setWindowTitle("Edit Parameters")
        self.resize(660, 500)
        self.setMinimumSize(560, 400)
        self.setStyleSheet(
            "QDialog { background: #d4d0c8; font-family: Arial; font-size: 12px; }"
            "QGroupBox { font-weight: normal; }"
            "QPushButton { background: #ece9d8; border: 1px solid #808080; min-height: 24px; min-width: 72px; padding: 2px 12px; }"
            "QPushButton:disabled { background: #c8c4bc; color: #808080; }"
            "QCheckBox:disabled { color: #808080; }"
            "QLineEdit { background: white; border: 1px solid #808080; min-height: 20px; }"
            "QLineEdit:disabled { background: #c8c4bc; color: #6a6a6a; }"
            "QListWidget { background: white; border: 1px solid #808080; }"
            + _checkbox_indicator_style()
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(8)
        root.addWidget(self._tolerance_box())
        root.addWidget(self._area_box(), 1)
        root.addWidget(self._duplicate_box(), 1)
        footer = QHBoxLayout()
        footer.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("OK")
        ok.setDefault(True)
        ok.clicked.connect(self._finish)
        footer.addWidget(cancel)
        footer.addWidget(ok)
        root.addLayout(footer)
        self._apply_initial_state()

    def _tolerance_box(self):
        box = QGroupBox("Venn Analysis")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(12, 14, 12, 10)
        self.default_tolerance = QRadioButton("Use Default Tolerance")
        tolerance_row = QHBoxLayout()
        self.custom_tolerance = QRadioButton("Tolerance: (μm)")
        self.custom_tolerance.toggled.connect(self._toggle_tolerance)
        self.tolerance = QLineEdit(_format_um(self.group["tolerance_um"]))
        self.tolerance.setFixedWidth(56)
        tolerance_row.addWidget(self.custom_tolerance)
        tolerance_row.addWidget(self.tolerance)
        tolerance_row.addStretch(1)
        layout.addWidget(self.default_tolerance)
        layout.addLayout(tolerance_row)
        return box

    def _area_box(self):
        box = QGroupBox("Inspected Area")
        layout = QHBoxLayout(box)
        layout.setContentsMargins(12, 14, 12, 10)
        choices = QVBoxLayout()
        self.largest_area = QRadioButton("Area of Largest Test")
        self.sum_area = QRadioButton("Sum of the Areas of the Selected Tests")
        self.sum_area.toggled.connect(self._toggle_area_tests)
        choices.addWidget(self.largest_area)
        choices.addWidget(self.sum_area)
        choices.addStretch(1)
        layout.addLayout(choices, 3)

        side = QVBoxLayout()
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.all_area_button = QPushButton("All")
        self.all_area_button.setMinimumWidth(52)
        self.all_area_button.clicked.connect(self._check_all_area_tests)
        self.none_area_button = QPushButton("None")
        self.none_area_button.setMinimumWidth(52)
        self.none_area_button.clicked.connect(self._check_no_area_tests)
        buttons.addWidget(self.all_area_button)
        buttons.addWidget(self.none_area_button)
        side.addLayout(buttons)
        self.area_checks = []
        self.area_host = QWidget()
        self.area_host.setStyleSheet("background: white;")
        checks = QVBoxLayout(self.area_host)
        checks.setContentsMargins(8, 6, 8, 6)
        checks.setSpacing(4)
        for name in self.member_tests:
            item = QCheckBox(name)
            checks.addWidget(item)
            self.area_checks.append(item)
        checks.addStretch(1)
        self.area_list = QScrollArea()
        self.area_list.setWidgetResizable(True)
        self.area_list.setWidget(self.area_host)
        self.area_list.setMinimumHeight(120)
        self.area_list.setStyleSheet("QScrollArea { background: white; border: 1px solid #808080; }")
        side.addWidget(self.area_list, 1)
        layout.addLayout(side, 2)
        return box

    def _duplicate_box(self):
        box = QGroupBox("Duplicate")
        layout = QHBoxLayout(box)
        layout.setContentsMargins(12, 14, 12, 10)
        choices = QVBoxLayout()
        self.highest_intensity = QRadioButton("Keep Defects With Highest Intensity")
        self.prioritized_tests = QRadioButton("Keep Defects From Highest Prioritized Tests")
        choices.addWidget(self.highest_intensity)
        choices.addWidget(self.prioritized_tests)
        choices.addStretch(1)
        layout.addLayout(choices, 3)

        side = QHBoxLayout()
        self.priority_list = QListWidget()
        self.priority_list.setMinimumHeight(120)
        for name in self._priority_names():
            self.priority_list.addItem(name)
        if self.priority_list.count():
            self.priority_list.setCurrentRow(0)
        side.addWidget(self.priority_list, 1)
        arrows = QVBoxLayout()
        arrows.setSpacing(4)
        self.up_button = QPushButton("↑")
        self.up_button.setFixedSize(28, 26)
        self.up_button.setStyleSheet("QPushButton { min-width: 24px; min-height: 22px; padding: 0; }")
        self.up_button.clicked.connect(lambda: self._move_priority(-1))
        self.down_button = QPushButton("↓")
        self.down_button.setFixedSize(28, 26)
        self.down_button.setStyleSheet("QPushButton { min-width: 24px; min-height: 22px; padding: 0; }")
        self.down_button.clicked.connect(lambda: self._move_priority(1))
        arrows.addWidget(self.up_button)
        arrows.addWidget(self.down_button)
        arrows.addStretch(1)
        side.addLayout(arrows)
        layout.addLayout(side, 2)
        return box

    def _apply_initial_state(self):
        if self.group["use_default_tolerance"]:
            self.default_tolerance.setChecked(True)
        else:
            self.custom_tolerance.setChecked(True)
        self.tolerance.setEnabled(not self.group["use_default_tolerance"])
        if self.group["inspected_area_mode"] == "Sum of Selected Test Areas":
            self.sum_area.setChecked(True)
        else:
            self.largest_area.setChecked(True)
        selected = self._checked_area_names()
        for box in self.area_checks:
            box.setChecked(box.text() in selected)
        if self.group["duplicate_mode"] == "Highest Prioritized Test ID":
            self.prioritized_tests.setChecked(True)
        else:
            self.highest_intensity.setChecked(True)
        self.up_button.setEnabled(self.priority_list.count() > 1)
        self.down_button.setEnabled(self.priority_list.count() > 1)
        self._toggle_area_tests(self.sum_area.isChecked())

    def _checked_area_names(self) -> set[str]:
        text = str(self.group.get("area_tests") or "").strip()
        if not text or text == "All Tests":
            return set()
        selected = set()
        for part in text.split(","):
            match = _match_catalog_name(part, self.member_tests)
            if match in self.member_tests:
                selected.add(match)
        return selected

    def _priority_names(self) -> list[str]:
        ordered = []
        text = str(self.group.get("test_priority") or "").strip()
        if text and text != "All Tests":
            for part in text.split(","):
                match = _match_catalog_name(part, self.catalog)
                if match in self.catalog and match not in ordered:
                    ordered.append(match)
        for name in self.catalog:
            if name not in ordered:
                ordered.append(name)
        return ordered

    def _toggle_tolerance(self, checked):
        self.tolerance.setEnabled(checked)

    def _toggle_area_tests(self, enabled):
        self.all_area_button.setEnabled(enabled)
        self.none_area_button.setEnabled(enabled)
        for box in self.area_checks:
            box.setEnabled(enabled)
        color = "white" if enabled else "#c8c4bc"
        self.area_host.setStyleSheet(f"background: {color};")
        self.area_list.setStyleSheet(
            f"QScrollArea {{ background: {color}; border: 1px solid #808080; }}"
        )

    def _check_all_area_tests(self):
        for box in self.area_checks:
            box.setChecked(True)

    def _check_no_area_tests(self):
        for box in self.area_checks:
            box.setChecked(False)

    def _move_priority(self, delta):
        row = self.priority_list.currentRow()
        target = row + delta
        if row < 0 or target < 0 or target >= self.priority_list.count():
            return
        item = self.priority_list.takeItem(row)
        self.priority_list.insertItem(target, item)
        self.priority_list.setCurrentRow(target)

    def _finish(self):
        group = dict(self.group)
        group["use_default_tolerance"] = self.default_tolerance.isChecked()
        tolerance_text = self.tolerance.text().strip()
        if group["use_default_tolerance"]:
            try:
                tolerance = float(tolerance_text)
            except ValueError:
                tolerance = float(self.group["tolerance_um"])
            group["tolerance_um"] = tolerance if tolerance > 0 else float(self.group["tolerance_um"])
        else:
            try:
                tolerance = float(tolerance_text)
            except ValueError:
                QMessageBox.warning(self, "Edit Parameters", "Custom tolerance must be greater than zero.")
                return
            if tolerance <= 0:
                QMessageBox.warning(self, "Edit Parameters", "Custom tolerance must be greater than zero.")
                return
            group["tolerance_um"] = tolerance
        group["inspected_area_mode"] = (
            "Sum of Selected Test Areas" if self.sum_area.isChecked() else "Area of Largest Test"
        )
        checked = [box.text() for box in self.area_checks if box.isChecked()]
        if group["inspected_area_mode"] == "Sum of Selected Test Areas" and not checked:
            QMessageBox.warning(self, "Edit Parameters", "Summed inspected area requires selected tests.")
            return
        if checked:
            group["area_tests"] = ", ".join(checked)
        group["duplicate_mode"] = (
            "Highest Prioritized Test ID" if self.prioritized_tests.isChecked() else "Highest Intensity"
        )
        priority = [self.priority_list.item(index).text() for index in range(self.priority_list.count())]
        if priority:
            group["test_priority"] = ", ".join(priority)
        if group["duplicate_mode"] == "Highest Prioritized Test ID" and not group["test_priority"].strip():
            QMessageBox.warning(self, "Edit Parameters", "Prioritized duplicate mode requires a Test ID priority.")
            return
        self.result_group = group
        self.accept()


class PrecisionFilterDialog(QDialog):
    ELEMENTS = ["Defect Size", "Intensity", "Rough Class", "Test ID", "Region ID", "Cluster ID"]
    OPERATORS = ["=", "!=", ">", ">=", "<", "<=", "In Range"]

    def __init__(self, filter_text="All Defects", quick_filter=None, mode="Quick Filter", parent=None):
        super().__init__(parent)
        self.result_filter = None
        self.result_quick_filter = None
        self.result_mode = None
        self.setWindowTitle("Sampling Scheme Defect Params Filter")
        self.resize(680, 460)
        root = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._quick_page(_normalize_quick_filter(quick_filter)), "Quick Filter")
        self.tabs.addTab(self._rule_page(filter_text), "Rule Editor")
        self.tabs.setCurrentIndex(1 if mode == "Rule Editor" else 0)
        root.addWidget(self.tabs, 1)
        footer = QHBoxLayout()
        footer.addStretch(1)
        ok = QPushButton("OK")
        ok.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        footer.addWidget(ok)
        footer.addWidget(cancel)
        root.addLayout(footer)

    def _choice(self, values, current):
        control = QComboBox()
        control.addItems(values)
        control.setCurrentText(str(current))
        return control

    def _quick_page(self, values):
        page = QWidget()
        form = QGridLayout(page)
        self.adder = self._choice(["All", "Adders", "Non-Adders"], values["adder"])
        self.clusters = self._choice(["All", "Clustered", "Unclustered"], values["clusters"])
        self.bright = QCheckBox("Bright")
        self.bright.setChecked(values["bright"])
        self.dark = QCheckBox("Dark")
        self.dark.setChecked(values["dark"])
        polarity = QWidget()
        polarity_layout = QHBoxLayout(polarity)
        polarity_layout.setContentsMargins(0, 0, 0, 0)
        polarity_layout.addWidget(self.bright)
        polarity_layout.addWidget(self.dark)
        polarity_layout.addStretch(1)
        self.regions = QLineEdit(str(values["regions"]))
        self.repeaters = self._choice(["All", "Repeaters", "Non-Repeaters"], values["repeaters"])
        self.tests = QLineEdit(str(values["tests"]))
        self.threshold_region = QLineEdit(str(values["threshold_region"]))
        rows = (
            ("Adder", self.adder),
            ("Clusters", self.clusters),
            ("Polarity", polarity),
            ("Region ID", self.regions),
            ("Repeaters", self.repeaters),
            ("Test", self.tests),
            ("Threshold Region", self.threshold_region),
        )
        for row, (label, control) in enumerate(rows):
            form.addWidget(QLabel(label), row, 0)
            form.addWidget(control, row, 1)
        form.setColumnStretch(1, 1)
        form.setRowStretch(len(rows), 1)
        return page

    def _rule_page(self, filter_text):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Build or edit an advanced filter expression for this rule."))
        builder = QGridLayout()
        self.rule_element = self._choice(self.ELEMENTS, self.ELEMENTS[0])
        self.rule_operator = self._choice(self.OPERATORS, self.OPERATORS[0])
        self.rule_value = QLineEdit("0")
        build = QPushButton("Build Expression")
        build.clicked.connect(self._build_rule)
        builder.addWidget(QLabel("Selected Element"), 0, 0)
        builder.addWidget(self.rule_element, 0, 1)
        builder.addWidget(self.rule_operator, 0, 2)
        builder.addWidget(self.rule_value, 0, 3)
        builder.addWidget(build, 0, 4)
        layout.addLayout(builder)
        layout.addWidget(QLabel("Expression Definition"))
        self.rule_expression = QLineEdit(str(filter_text or "All Defects"))
        layout.addWidget(self.rule_expression)
        layout.addStretch(1)
        return page

    def _build_rule(self):
        self.rule_expression.setText(
            f"{self.rule_element.currentText()} {self.rule_operator.currentText()} {self.rule_value.text().strip()}"
        )

    def _quick_values(self):
        return {
            "adder": self.adder.currentText(),
            "clusters": self.clusters.currentText(),
            "bright": self.bright.isChecked(),
            "dark": self.dark.isChecked(),
            "regions": self.regions.text().strip() or "All",
            "repeaters": self.repeaters.currentText(),
            "tests": self.tests.text().strip() or "All",
            "threshold_region": self.threshold_region.text().strip() or "All",
        }

    def _quick_summary(self, values):
        polarity = "/".join(name for name, checked in (("Bright", values["bright"]), ("Dark", values["dark"])) if checked)
        return "; ".join((
            f"Adder={values['adder']}",
            f"Clusters={values['clusters']}",
            f"Polarity={polarity or 'None'}",
            f"Region={values['regions']}",
            f"Repeaters={values['repeaters']}",
            f"Test={values['tests']}",
            f"Threshold Region={values['threshold_region']}",
        ))

    def _finish(self):
        quick = self._quick_values()
        if self.tabs.currentIndex() == 0:
            if not quick["bright"] and not quick["dark"]:
                QMessageBox.warning(self, "Quick Filter", "Select Bright, Dark, or both polarities.")
                return
            self.result_filter = self._quick_summary(quick)
            self.result_mode = "Quick Filter"
        else:
            self.result_filter = self.rule_expression.text().strip()
            self.result_mode = "Rule Editor"
            if not self.result_filter:
                QMessageBox.warning(self, "Rule Editor", "Expression Definition is required.")
                return
        self.result_quick_filter = quick
        self.accept()


class PrecisionAdvancedSettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.result_settings = None
        self.setWindowTitle("Advanced Settings - Precision Sampling")
        root = QVBoxLayout(self)
        self.allow_overlap = QCheckBox("Allow Filter Overlapping")
        self.allow_overlap.setChecked(bool(settings.get("allow_filter_overlap", False)))
        root.addWidget(self.allow_overlap)
        form = QGridLayout()
        self.sample_bin = QComboBox()
        self.sample_bin.addItems(["Sampling Method", "Unique Bin per Rule"])
        self.sample_bin.setCurrentText(str(settings.get("sample_bin_assignment", "Sampling Method")))
        self.overlap_bin = QComboBox()
        self.overlap_bin.addItems(["Last Rule", "New Unique Bin"])
        self.overlap_bin.setCurrentText(str(settings.get("overlapping_bin_assignment", "Last Rule")))
        form.addWidget(QLabel("Sample Bin Assignment"), 0, 0)
        form.addWidget(self.sample_bin, 0, 1)
        form.addWidget(QLabel("Overlapping Sample Bins"), 1, 0)
        form.addWidget(self.overlap_bin, 1, 1)
        root.addLayout(form)
        footer = QHBoxLayout()
        footer.addStretch(1)
        ok = QPushButton("OK")
        ok.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        footer.addWidget(ok)
        footer.addWidget(cancel)
        root.addLayout(footer)

    def _finish(self):
        self.result_settings = {
            "allow_filter_overlap": self.allow_overlap.isChecked(),
            "sample_bin_assignment": self.sample_bin.currentText(),
            "overlapping_bin_assignment": self.overlap_bin.currentText(),
        }
        self.accept()


class PrecisionRulesDialog(QDialog):
    METHODS = ["Random Sampling", "Class Code Sampling", "Proportional Sampling"]

    def __init__(self, rules, advanced=None, parent=None):
        super().__init__(parent)
        self.rules = _normalize_precision_rules(rules)
        self.advanced = {
            "allow_filter_overlap": False,
            "sample_bin_assignment": "Sampling Method",
            "overlapping_bin_assignment": "Last Rule",
            **deepcopy(advanced or {}),
        }
        self.result_rules = None
        self.result_advanced = None
        self.setWindowTitle("Precision Sampling Rule Sequence")
        self.resize(850, 480)
        root = QVBoxLayout(self)
        note = QLabel("Each enabled rule filters first, then applies one sampling method. Rules execute from top to bottom.")
        note.setWordWrap(True)
        root.addWidget(note)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Enabled", "Rule Name", "Filter", "Sampling Method", "Back Fill"])
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table, 1)
        actions = QGridLayout()
        for index, (label, callback) in enumerate((
            ("New Rule", self._add),
            ("Edit Filter", self._edit_filter),
            ("Edit Sampling", self._edit_sampling),
            ("Copy", self._copy),
            ("Load Rule", self._load_rule),
            ("Save Rule", self._save_rule),
            ("Remove Rule", self._remove),
            ("Move Up", lambda: self._move(-1)),
            ("Move Down", lambda: self._move(1)),
            ("Advanced Settings", self._advanced_settings),
        )):
            button = QPushButton(label)
            button.clicked.connect(callback)
            actions.addWidget(button, index // 5, index % 5)
        actions.setColumnStretch(4, 1)
        root.addLayout(actions)
        footer = QHBoxLayout()
        footer.addStretch(1)
        ok = QPushButton("OK")
        ok.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        footer.addWidget(ok)
        footer.addWidget(cancel)
        root.addLayout(footer)
        for rule in self.rules:
            self._append(rule)

    def _check_item(self, checked):
        item = QTableWidgetItem()
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
        return item

    def _append(self, rule):
        rule = _normalize_precision_rules([rule])[0]
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, self._check_item(rule["enabled"]))
        name_item = QTableWidgetItem(rule["name"])
        name_item.setData(Qt.UserRole, deepcopy(rule))
        self.table.setItem(row, 1, name_item)
        self.table.setItem(row, 2, QTableWidgetItem(rule["filter"]))
        method = QComboBox()
        method.addItems(self.METHODS)
        method.setCurrentText(rule["sampling_method"])
        self.table.setCellWidget(row, 3, method)
        self.table.setItem(row, 4, self._check_item(rule["back_fill"]))
        self.table.selectRow(row)

    def _row_data(self, row):
        stored = self.table.item(row, 1).data(Qt.UserRole)
        rule = deepcopy(stored) if isinstance(stored, dict) else {}
        rule.update({
            "enabled": self.table.item(row, 0).checkState() == Qt.Checked,
            "name": self.table.item(row, 1).text().strip().replace(" ", "_"),
            "filter": self.table.item(row, 2).text().strip(),
            "sampling_method": self.table.cellWidget(row, 3).currentText(),
            "back_fill": self.table.item(row, 4).checkState() == Qt.Checked,
        })
        return _normalize_precision_rules([rule])[0]

    def _set_row(self, row, rule):
        rule = _normalize_precision_rules([rule])[0]
        self.table.item(row, 0).setCheckState(Qt.Checked if rule["enabled"] else Qt.Unchecked)
        self.table.item(row, 1).setText(rule["name"])
        self.table.item(row, 1).setData(Qt.UserRole, deepcopy(rule))
        self.table.item(row, 2).setText(rule["filter"])
        self.table.cellWidget(row, 3).setCurrentText(rule["sampling_method"])
        self.table.item(row, 4).setCheckState(Qt.Checked if rule["back_fill"] else Qt.Unchecked)

    def _add(self):
        self._append({"enabled": True, "name": f"Rule_{self.table.rowCount() + 1}", "filter": "All Defects", "sampling_method": "Random Sampling", "back_fill": False})

    def _selected_rule(self):
        row = self.table.currentRow()
        return (row, self._row_data(row)) if row >= 0 else (-1, None)

    def _edit_filter(self):
        row, rule = self._selected_rule()
        if rule is None:
            return
        dialog = PrecisionFilterDialog(
            rule["filter"], rule["quick_filter"], rule["filter_mode"], self
        )
        if _exec_dialog(dialog) != QDialog.Accepted:
            return
        rule["filter"] = dialog.result_filter
        rule["filter_mode"] = dialog.result_mode
        rule["quick_filter"] = dialog.result_quick_filter
        self._set_row(row, rule)

    def _sampling_key(self, method):
        return "Proportional" if method == "Proportional Sampling" else "Random/Class Code"

    def _edit_sampling(self):
        row, rule = self._selected_rule()
        if rule is None:
            return
        method = self._sampling_key(rule["sampling_method"])
        dialog = SamplingMethodSettingsDialog(
            rule["sampling_settings"], self, initial_method=method, lock_method=True
        )
        if rule["sampling_method"] == "Class Code Sampling" and hasattr(dialog, "random_class_tabs"):
            dialog.random_class_tabs.setCurrentIndex(1)
        if _exec_dialog(dialog) != QDialog.Accepted:
            return
        rule["sampling_settings"] = dialog.result_settings
        self._set_row(row, rule)

    def _load_rule(self):
        path, _selected = QFileDialog.getOpenFileName(
            self, "Load Precision Sampling Rule", "", "Precision Rule (*.json);;All Files (*)"
        )
        if not path:
            return
        try:
            value = json.loads(Path(path).read_text(encoding="utf-8"))
            rules = _normalize_precision_rules([value])
            if not rules:
                raise ValueError("The file does not contain a Precision rule.")
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            QMessageBox.warning(self, "Load Rule", f"Unable to load rule: {exc}")
            return
        self._append(rules[0])

    def _save_rule(self):
        _row, rule = self._selected_rule()
        if rule is None:
            return
        path, _selected = QFileDialog.getSaveFileName(
            self, "Save Precision Sampling Rule", f"{rule['name']}.json", "Precision Rule (*.json)"
        )
        if not path:
            return
        try:
            Path(path).write_text(json.dumps(rule, indent=2), encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(self, "Save Rule", f"Unable to save rule: {exc}")

    def _advanced_settings(self):
        dialog = PrecisionAdvancedSettingsDialog(self.advanced, self)
        if _exec_dialog(dialog) == QDialog.Accepted:
            self.advanced = deepcopy(dialog.result_settings)

    def _copy(self):
        row = self.table.currentRow()
        if row >= 0:
            rule = self._row_data(row)
            rule["name"] += "_Copy"
            self._append(rule)

    def _remove(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    def _move(self, direction):
        row = self.table.currentRow()
        target = row + direction
        if row < 0 or target < 0 or target >= self.table.rowCount():
            return
        current, other = self._row_data(row), self._row_data(target)
        self._set_row(row, other)
        self._set_row(target, current)
        self.table.selectRow(target)

    def _finish(self):
        rules = [self._row_data(row) for row in range(self.table.rowCount())]
        enabled = [rule for rule in rules if rule["enabled"]]
        if not enabled or any(not rule["name"] or not rule["filter"] for rule in enabled):
            QMessageBox.warning(self, "Precision Sampling", "At least one enabled rule with a name and filter is required.")
            return
        names = [rule["name"].lower() for rule in enabled]
        if len(names) != len(set(names)):
            QMessageBox.warning(self, "Precision Sampling", "Enabled rule names must be unique.")
            return
        self.result_rules = rules
        self.result_advanced = deepcopy(self.advanced)
        self.accept()


class AttributeSelectionDialog(QDialog):
    def __init__(self, selected=None, parent=None, *, directional=False):
        super().__init__(parent)
        self.directional = directional
        self.result_attributes = None
        self.setWindowTitle("Directional Bias" if directional else "Select Attributes")
        self.resize(480, 430)
        root = QVBoxLayout(self)
        if directional:
            values = _normalize_directional_bias(selected)
            self.table = QTableWidget(len(DEFECT_ATTRIBUTES), 2)
            self.table.setHorizontalHeaderLabels(["Attribute", "Direction"])
            self.table.horizontalHeader().setStretchLastSection(True)
            for row, attribute in enumerate(DEFECT_ATTRIBUTES):
                item = QTableWidgetItem(attribute)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, 0, item)
                direction = QComboBox()
                direction.addItems(["Off", "High", "Low"])
                direction.setCurrentText(values.get(attribute, "Off"))
                self.table.setCellWidget(row, 1, direction)
            root.addWidget(self.table, 1)
        else:
            values = set(_string_list(selected))
            self.list = QListWidget()
            for attribute in DEFECT_ATTRIBUTES:
                self.list.addItem(attribute)
                item = self.list.item(self.list.count() - 1)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked if attribute in values else Qt.Unchecked)
            root.addWidget(self.list, 1)
            controls = QHBoxLayout()
            all_button = QPushButton("All")
            all_button.clicked.connect(lambda: self._check_all(True))
            none_button = QPushButton("None")
            none_button.clicked.connect(lambda: self._check_all(False))
            controls.addWidget(all_button)
            controls.addWidget(none_button)
            controls.addStretch(1)
            root.addLayout(controls)
        footer = QHBoxLayout()
        footer.addStretch(1)
        ok = QPushButton("OK")
        ok.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        footer.addWidget(ok)
        footer.addWidget(cancel)
        root.addLayout(footer)

    def _check_all(self, checked):
        for row in range(self.list.count()):
            self.list.item(row).setCheckState(Qt.Checked if checked else Qt.Unchecked)

    def _finish(self):
        if self.directional:
            self.result_attributes = {
                self.table.item(row, 0).text(): self.table.cellWidget(row, 1).currentText()
                for row in range(self.table.rowCount())
                if self.table.cellWidget(row, 1).currentText() != "Off"
            }
        else:
            self.result_attributes = [
                self.list.item(row).text()
                for row in range(self.list.count())
                if self.list.item(row).checkState() == Qt.Checked
            ]
        self.accept()


class DensityGroupsDialog(QDialog):
    def __init__(self, groups, parent=None):
        super().__init__(parent)
        self.groups = _normalize_density_groups(groups)
        self.result_groups = None
        self.setWindowTitle("Density Shaping Groups")
        self.resize(570, 390)
        root = QVBoxLayout(self)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Group", "Selected Attributes"])
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table, 1)
        for group in self.groups:
            self._append(group)
        actions = QHBoxLayout()
        add = QPushButton("Add Group")
        add.clicked.connect(self._add)
        edit = QPushButton("Edit Attributes")
        edit.clicked.connect(self._edit)
        remove = QPushButton("Remove Group")
        remove.clicked.connect(self._remove)
        actions.addWidget(add)
        actions.addWidget(edit)
        actions.addWidget(remove)
        actions.addStretch(1)
        root.addLayout(actions)
        footer = QHBoxLayout()
        footer.addStretch(1)
        ok = QPushButton("OK")
        ok.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        footer.addWidget(ok)
        footer.addWidget(cancel)
        root.addLayout(footer)

    def _append(self, attributes):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(f"Group {row + 1}"))
        self.table.setItem(row, 1, QTableWidgetItem(", ".join(attributes)))
        self.table.selectRow(row)

    def _pick(self, selected):
        dialog = AttributeSelectionDialog(selected, self)
        return dialog.result_attributes if _exec_dialog(dialog) == QDialog.Accepted else None

    def _add(self):
        selected = self._pick([])
        if selected:
            self._append(selected)

    def _edit(self):
        row = self.table.currentRow()
        if row < 0:
            return
        selected = self._pick(_string_list(self.table.item(row, 1).text()))
        if selected:
            self.table.item(row, 1).setText(", ".join(selected))

    def _remove(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    def _finish(self):
        self.result_groups = [
            _string_list(self.table.item(row, 1).text())
            for row in range(self.table.rowCount())
            if _string_list(self.table.item(row, 1).text())
        ]
        self.accept()


class LimitsDialog(QDialog):
    def __init__(self, limits, parent=None):
        super().__init__(parent)
        self.result_limits = None
        self.setWindowTitle("Attribute Limits")
        self.resize(520, 360)
        root = QVBoxLayout(self)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Attribute", "Limit"])
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table, 1)
        for limit in _normalize_limits(limits):
            self._append(limit)
        actions = QHBoxLayout()
        add = QPushButton("Add Row")
        add.clicked.connect(lambda: self._append({"attribute": "Defect Size", "limit": 0}))
        remove = QPushButton("Remove Row")
        remove.clicked.connect(self._remove)
        actions.addWidget(add)
        actions.addWidget(remove)
        actions.addStretch(1)
        root.addLayout(actions)
        footer = QHBoxLayout()
        footer.addStretch(1)
        ok = QPushButton("OK")
        ok.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        footer.addWidget(ok)
        footer.addWidget(cancel)
        root.addLayout(footer)

    def _append(self, limit):
        row = self.table.rowCount()
        self.table.insertRow(row)
        attribute = QComboBox()
        attribute.addItems(DEFECT_ATTRIBUTES)
        attribute.setCurrentText(limit["attribute"])
        self.table.setCellWidget(row, 0, attribute)
        self.table.setItem(row, 1, QTableWidgetItem(str(limit["limit"])))
        self.table.selectRow(row)

    def _remove(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    def _finish(self):
        try:
            self.result_limits = [
                {
                    "attribute": self.table.cellWidget(row, 0).currentText(),
                    "limit": float(self.table.item(row, 1).text()),
                }
                for row in range(self.table.rowCount())
            ]
        except (AttributeError, TypeError, ValueError):
            QMessageBox.warning(self, "Attribute Limits", "Each limit requires a numeric value.")
            return
        self.accept()


class ClassCodeRowsDialog(QDialog):
    CATEGORIES = ["CAG Code", "Fine Class", "Fine Code", "Fine Super Group", "Macro Sig Class", "Manual", "Micro Sig Class", "RoughClass", "RoughGroup", "Rough Super Group", "Unsupervised"]

    def __init__(self, rows, parent=None):
        super().__init__(parent)
        self.result_rows = None
        self.setWindowTitle("Class Code Sampling")
        self.resize(790, 430)
        root = QVBoxLayout(self)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Category", "All Nonzero", "Code", "Defects", "#/ %", "Sample All"])
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table, 1)
        for row in _normalize_class_code_rows(rows):
            self._append(row)
        actions = QHBoxLayout()
        add = QPushButton("New")
        add.clicked.connect(lambda: self._append({}))
        remove = QPushButton("Delete")
        remove.clicked.connect(self._remove)
        actions.addWidget(add)
        actions.addWidget(remove)
        actions.addStretch(1)
        root.addLayout(actions)
        footer = QHBoxLayout()
        footer.addStretch(1)
        ok = QPushButton("OK")
        ok.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        footer.addWidget(ok)
        footer.addWidget(cancel)
        root.addLayout(footer)

    def _check_item(self, checked):
        item = QTableWidgetItem()
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
        return item

    def _append(self, value):
        row_data = _normalize_class_code_rows([value])[0]
        row = self.table.rowCount()
        self.table.insertRow(row)
        category = QComboBox()
        category.addItems(self.CATEGORIES)
        category.setCurrentText(row_data["category"])
        self.table.setCellWidget(row, 0, category)
        self.table.setItem(row, 1, self._check_item(row_data["all_nonzero"]))
        self.table.setItem(row, 2, QTableWidgetItem(row_data["code"]))
        self.table.setItem(row, 3, QTableWidgetItem(str(row_data["defects"])))
        unit = QComboBox()
        unit.addItems(["#", "%"])
        unit.setCurrentText(row_data["unit"])
        self.table.setCellWidget(row, 4, unit)
        self.table.setItem(row, 5, self._check_item(row_data["sample_all"]))
        self.table.selectRow(row)

    def _remove(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    def _finish(self):
        try:
            rows = []
            for row in range(self.table.rowCount()):
                all_nonzero = self.table.item(row, 1).checkState() == Qt.Checked
                code = self.table.item(row, 2).text().strip()
                defects = int(self.table.item(row, 3).text())
                if defects < 0 or defects > 65000 or (not all_nonzero and not code):
                    raise ValueError
                rows.append({
                    "category": self.table.cellWidget(row, 0).currentText(),
                    "all_nonzero": all_nonzero,
                    "code": code,
                    "defects": defects,
                    "unit": self.table.cellWidget(row, 4).currentText(),
                    "sample_all": self.table.item(row, 5).checkState() == Qt.Checked,
                })
        except (AttributeError, TypeError, ValueError):
            QMessageBox.warning(self, "Class Code Sampling", "Each row requires a code or All Nonzero and a valid defect count.")
            return
        self.result_rows = rows
        self.accept()


class SamplingMethodSettingsDialog(QDialog):
    def __init__(self, settings, parent=None, *, initial_method=None, lock_method=False):
        super().__init__(parent)
        self.settings = _normalize_sampling_settings(settings)
        self.result_settings = None
        self.controls = {}
        self.setWindowTitle("Sampling Method Settings")
        self.resize(680, 600)
        root = QVBoxLayout(self)
        method_row = QHBoxLayout()
        method_row.addWidget(QLabel("Sampling Method"))
        self.method = QComboBox()
        self.method.addItems(list(SAMPLING_METHOD_SCHEMAS))
        if initial_method in SAMPLING_METHOD_SCHEMAS:
            self.method.setCurrentText(initial_method)
        self.method.setEnabled(not lock_method)
        self.method.currentTextChanged.connect(self._show_method)
        method_row.addWidget(self.method, 1)
        root.addLayout(method_row)
        self.host = QWidget()
        self.form = QGridLayout(self.host)
        self.form.setColumnStretch(1, 1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.host)
        root.addWidget(scroll, 1)
        footer = QHBoxLayout()
        defaults = QPushButton("Default")
        defaults.clicked.connect(self._defaults)
        footer.addWidget(defaults)
        footer.addStretch(1)
        ok = QPushButton("OK")
        ok.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        footer.addWidget(ok)
        footer.addWidget(cancel)
        root.addLayout(footer)
        self._show_method(self.method.currentText())

    def _clear(self):
        self.controls = {}
        while self.form.count():
            item = self.form.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _show_method(self, method):
        if not method:
            return
        self._clear()
        values = self.settings[method]
        if method == "Random/Class Code":
            self._show_random_class_code(values)
            return
        schema = list(SAMPLING_METHOD_SCHEMAS[method])
        if method == "Diversity":
            if values["scheme"] == "Discovery":
                hidden = {"production_bins", "average_per_bin", "proportional_quota"}
            else:
                hidden = {"discovery_samples", "similar_samples", "save_tiles", "dynamic_attributes", "dynamic_direction", "dynamic_class_code"}
            schema = [entry for entry in schema if entry[0] not in hidden]
        self.form.addWidget(QLabel("Property"), 0, 0)
        self.form.addWidget(QLabel("Value"), 0, 1)
        for row, (key, label, kind, default) in enumerate(schema, start=1):
            self.form.addWidget(QLabel(label), row, 0)
            value = values[key]
            if key in {
                "diversification_attributes", "directional_bias", "density_groups",
                "dynamic_attributes", "limits", "class_code_rows",
            }:
                control = self._structured_method_control(method, key, value)
            elif kind == "bool":
                control = QCheckBox()
                control.setChecked(bool(value))
                control.toggled.connect(lambda checked, m=method, k=key: self._set(m, k, checked))
            elif kind == "choice":
                control = QComboBox()
                control.addItems(default[1])
                control.setCurrentText(str(value))
                if method == "Diversity" and key == "scheme":
                    control.currentTextChanged.connect(lambda text, m=method, k=key: self._set_scheme(m, k, text))
                else:
                    control.currentTextChanged.connect(lambda text, m=method, k=key: self._set(m, k, text))
            elif kind == "int":
                control = QSpinBox()
                control.setRange(0, 500000000)
                control.setValue(int(value))
                control.valueChanged.connect(lambda number, m=method, k=key: self._set(m, k, number))
            elif kind == "float":
                control = QDoubleSpinBox()
                control.setRange(0, 500000000)
                control.setDecimals(3)
                control.setValue(float(value))
                control.valueChanged.connect(lambda number, m=method, k=key: self._set(m, k, number))
            else:
                control = QLineEdit(str(value))
                control.textChanged.connect(lambda text, m=method, k=key: self._set(m, k, text))
            self.controls[key] = control
            self.form.addWidget(control, row, 1)
        self.form.setRowStretch(len(schema) + 1, 1)

    def _show_random_class_code(self, values):
        schema = {entry[0]: entry for entry in SAMPLING_METHOD_SCHEMAS["Random/Class Code"]}
        self.form.addWidget(QLabel("Maximum Number of Defects to be Sampled"), 0, 0)
        maximum = self._basic_method_control("Random/Class Code", *schema["maximum_per_wafer"], values["maximum_per_wafer"])
        self.controls["maximum_per_wafer"] = maximum
        self.form.addWidget(maximum, 0, 1)
        tabs = QTabWidget()
        random_page = QWidget()
        random_form = QGridLayout(random_page)
        class_page = QWidget()
        class_form = QGridLayout(class_page)
        random_keys = [
            "random_enabled", "maximum_per_die", "maximum_per_cluster", "percent_from_clusters",
            "minimum_size", "maximum_size", "adders_only", "back_fill",
        ]
        class_keys = [
            "class_code_enabled", "maximum_code_defects", "class_code_rows", "class_adders_only",
            "class_back_fill", "enable_limits", "apply_limits_per_bin", "code_maximum_per_die",
            "code_maximum_per_cluster", "code_percent_from_clusters",
        ]
        for target, keys in ((random_form, random_keys), (class_form, class_keys)):
            for row, key in enumerate(keys):
                _schema_key, label, kind, default = schema[key]
                target.addWidget(QLabel(label), row, 0)
                if key == "class_code_rows":
                    control = self._structured_method_control("Random/Class Code", key, values[key])
                else:
                    control = self._basic_method_control("Random/Class Code", key, label, kind, default, values[key])
                self.controls[key] = control
                target.addWidget(control, row, 1)
            target.setColumnStretch(1, 1)
            target.setRowStretch(len(keys), 1)
        tabs.addTab(random_page, "Random Sampling")
        tabs.addTab(class_page, "Class Code Sampling")
        self.random_class_tabs = tabs
        self.form.addWidget(tabs, 1, 0, 1, 2)

    def _basic_method_control(self, method, key, _label, kind, default, value):
        if kind == "bool":
            control = QCheckBox()
            control.setChecked(bool(value))
            control.toggled.connect(lambda checked, m=method, k=key: self._set(m, k, checked))
        elif kind == "choice":
            control = QComboBox()
            control.addItems(default[1])
            control.setCurrentText(str(value))
            control.currentTextChanged.connect(lambda text, m=method, k=key: self._set(m, k, text))
        elif kind == "int":
            control = QSpinBox()
            control.setRange(0, 500000000)
            control.setValue(int(value))
            control.valueChanged.connect(lambda number, m=method, k=key: self._set(m, k, number))
        elif kind == "float":
            control = QDoubleSpinBox()
            control.setRange(0, 500000000)
            control.setDecimals(3)
            control.setValue(float(value))
            control.valueChanged.connect(lambda number, m=method, k=key: self._set(m, k, number))
        else:
            control = QLineEdit(str(value))
            control.textChanged.connect(lambda text, m=method, k=key: self._set(m, k, text))
        return control

    def _structured_method_control(self, method, key, value):
        host = QWidget()
        layout = QHBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        if isinstance(value, dict):
            summary_text = ", ".join(f"{name}: {direction}" for name, direction in value.items())
        elif isinstance(value, list):
            if value and isinstance(value[0], list):
                summary_text = f"{len(value)} group(s)"
            elif value and isinstance(value[0], dict):
                summary_text = f"{len(value)} row(s)"
            else:
                summary_text = ", ".join(str(item) for item in value)
        else:
            summary_text = str(value)
        summary = QLabel(summary_text or "None")
        summary.setWordWrap(True)
        button = QPushButton("Edit...")
        button.clicked.connect(lambda: self._edit_method_structured(method, key))
        layout.addWidget(summary, 1)
        layout.addWidget(button)
        return host

    def _edit_method_structured(self, method, key):
        value = self.settings[method][key]
        if key in ("diversification_attributes", "dynamic_attributes"):
            dialog = AttributeSelectionDialog(value, self)
            attribute = "result_attributes"
        elif key == "directional_bias":
            dialog = AttributeSelectionDialog(value, self, directional=True)
            attribute = "result_attributes"
        elif key == "density_groups":
            dialog = DensityGroupsDialog(value, self)
            attribute = "result_groups"
        elif key == "limits":
            dialog = LimitsDialog(value, self)
            attribute = "result_limits"
        else:
            dialog = ClassCodeRowsDialog(value, self)
            attribute = "result_rows"
        if _exec_dialog(dialog) == QDialog.Accepted:
            self.settings[method][key] = deepcopy(getattr(dialog, attribute))
            self._show_method(method)

    def _set_scheme(self, method, key, value):
        self._set(method, key, value)
        self._show_method(method)

    def _set(self, method, key, value):
        self.settings[method][key] = value

    def _defaults(self):
        method = self.method.currentText()
        self.settings[method] = _default_parameters(SAMPLING_METHOD_SCHEMAS[method])
        self._show_method(method)

    def _finish(self):
        state = default_wpp_state()
        sampling = next(item for item in state["operations"] if item["name"] == "Sampling")
        sampling["enabled"] = True
        sampling["parameters"]["review_sampling"] = self.method.currentText()
        sampling["parameters"]["method_settings"] = deepcopy(self.settings)
        errors = validate_wpp(state, test_count=2)
        if errors:
            QMessageBox.warning(self, "Sampling Method Settings", "\n".join(errors))
            return
        self.result_settings = _normalize_sampling_settings(self.settings)
        self.accept()


class ExcursionRuleEditorDialog(QDialog):
    ELEMENTS = ["Defect Size", "Class Code", "Test ID", "Cluster ID", "Die X", "Die Y", "Intensity", "Rough Class"]
    OPERATORS = ["=", "!=", ">", ">=", "<", "<=", "In Range"]

    def __init__(self, rules, expressions=None, parent=None):
        super().__init__(parent)
        self.rules = _normalize_excursion_rules(rules)
        self.expressions = _normalize_expressions(expressions)
        self.result_rules = None
        self.result_expressions = None
        self.setWindowTitle("Excursion Reduction Rule Editor")
        self.resize(900, 610)
        root = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._quick_rule_page(), "Quick Rule Builder")
        self.tabs.addTab(self._define_expressions_page(), "Define Expressions")
        self.tabs.addTab(self._expressions_overview_page(), "Expressions Overview")
        root.addWidget(self.tabs, 1)
        footer = QHBoxLayout()
        footer.addStretch(1)
        ok = QPushButton("OK")
        ok.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        footer.addWidget(ok)
        footer.addWidget(cancel)
        root.addLayout(footer)
        self.table.currentCellChanged.connect(self._select)
        self.expression_table.currentCellChanged.connect(self._expression_selected)
        for rule in self.rules:
            self._append(rule)
        self._populate_expressions()

    def _quick_rule_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Enabled", "Rule Name", "Expression Definition"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)
        builder = QGridLayout()
        self.rule_name = QLineEdit("New_Rule")
        self.element = QComboBox()
        self.element.addItems(self.ELEMENTS)
        self.operator = QComboBox()
        self.operator.addItems(self.OPERATORS)
        self.value = QLineEdit("0")
        self.expression = QLineEdit()
        builder.addWidget(QLabel("Rule Name"), 0, 0)
        builder.addWidget(self.rule_name, 0, 1, 1, 3)
        builder.addWidget(QLabel("Available Element / Expression"), 1, 0)
        builder.addWidget(self.element, 1, 1)
        builder.addWidget(self.operator, 1, 2)
        builder.addWidget(self.value, 1, 3)
        builder.addWidget(QLabel("Expression Definition"), 2, 0)
        builder.addWidget(self.expression, 2, 1, 1, 3)
        layout.addLayout(builder)
        actions = QHBoxLayout()
        for label, callback in (
            ("New", self._new),
            ("Copy", self._copy),
            ("Delete", self._remove),
            ("Move Up", lambda: self._move(-1)),
            ("Move Down", lambda: self._move(1)),
            ("Build Expression", self._build_expression),
            ("Update", self._update),
        ):
            button = QPushButton(label)
            button.clicked.connect(callback)
            actions.addWidget(button)
        layout.addLayout(actions)
        return page

    def _define_expressions_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        self.expression_table = QTableWidget(0, 2)
        self.expression_table.setHorizontalHeaderLabels(["Name", "Expression Definition"])
        self.expression_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.expression_table, 1)
        form = QGridLayout()
        self.expression_name = QLineEdit()
        self.expression_element = QComboBox()
        self.expression_element.addItems(self.ELEMENTS)
        self.expression_operator = QComboBox()
        self.expression_operator.addItems(self.OPERATORS)
        self.expression_value = QLineEdit("0")
        self.expression_definition = QLineEdit()
        form.addWidget(QLabel("Name"), 0, 0)
        form.addWidget(self.expression_name, 0, 1, 1, 3)
        form.addWidget(QLabel("Available Element"), 1, 0)
        form.addWidget(self.expression_element, 1, 1)
        form.addWidget(self.expression_operator, 1, 2)
        form.addWidget(self.expression_value, 1, 3)
        form.addWidget(QLabel("Expression Definition"), 2, 0)
        form.addWidget(self.expression_definition, 2, 1, 1, 3)
        layout.addLayout(form)
        actions = QHBoxLayout()
        for label, callback in (
            ("Build", self._build_reusable_expression),
            ("Store", self._store_expression),
            ("Edit", self._edit_expression),
            ("Delete", self._delete_expression),
            ("Cancel", self._cancel_expression),
        ):
            button = QPushButton(label)
            button.clicked.connect(callback)
            actions.addWidget(button)
        actions.addStretch(1)
        layout.addLayout(actions)
        return page

    def _expressions_overview_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Expand an expression to view its stored definition and operands."))
        self.overview = QTreeWidget()
        self.overview.setHeaderLabels(["Expression", "Value"])
        self.overview.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.overview.header().setSectionResizeMode(1, QHeaderView.Stretch)
        layout.addWidget(self.overview, 1)
        return page

    def _check_item(self, checked):
        item = QTableWidgetItem()
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
        return item

    def _append(self, rule):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, self._check_item(rule["enabled"]))
        self.table.setItem(row, 1, QTableWidgetItem(rule["name"]))
        self.table.setItem(row, 2, QTableWidgetItem(rule["expression"]))
        self.table.selectRow(row)

    def _row_data(self, row):
        return {
            "enabled": self.table.item(row, 0).checkState() == Qt.Checked,
            "name": self.table.item(row, 1).text().strip().replace(" ", "_"),
            "expression": self.table.item(row, 2).text().strip(),
        }

    def _set_row(self, row, rule):
        self.table.item(row, 0).setCheckState(Qt.Checked if rule["enabled"] else Qt.Unchecked)
        self.table.item(row, 1).setText(rule["name"])
        self.table.item(row, 2).setText(rule["expression"])

    def _select(self, current_row, _current_column, _previous_row, _previous_column):
        if current_row >= 0:
            rule = self._row_data(current_row)
            self.rule_name.setText(rule["name"])
            self.expression.setText(rule["expression"])

    def _new(self):
        self._append({"enabled": True, "name": f"Rule_{self.table.rowCount() + 1}", "expression": ""})

    def _copy(self):
        row = self.table.currentRow()
        if row >= 0:
            rule = self._row_data(row)
            rule["name"] += "_Copy"
            self._append(rule)

    def _remove(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    def _move(self, direction):
        row = self.table.currentRow()
        target = row + direction
        if row < 0 or target < 0 or target >= self.table.rowCount():
            return
        current, other = self._row_data(row), self._row_data(target)
        self._set_row(row, other)
        self._set_row(target, current)
        self.table.selectRow(target)

    def _selected_operand(self):
        selected = self.element.currentText()
        stored = next((item for item in self.expressions if item["name"] == selected), None)
        return f"({stored['definition']})" if stored else selected

    def _build_expression(self):
        self.expression.setText(
            f"{self._selected_operand()} {self.operator.currentText()} {self.value.text().strip()}"
        )

    def _update(self):
        row = self.table.currentRow()
        if row < 0:
            self._new()
            row = self.table.currentRow()
        self.table.item(row, 1).setText(self.rule_name.text().strip().replace(" ", "_") or "New_Rule")
        self.table.item(row, 2).setText(self.expression.text().strip())

    def _populate_expressions(self, selected=-1):
        self.expression_table.setRowCount(0)
        for expression in self.expressions:
            row = self.expression_table.rowCount()
            self.expression_table.insertRow(row)
            self.expression_table.setItem(row, 0, QTableWidgetItem(expression["name"]))
            self.expression_table.setItem(row, 1, QTableWidgetItem(expression["definition"]))
        self._refresh_expression_sources()
        self._refresh_overview()
        if self.expressions:
            self.expression_table.selectRow(max(0, min(selected, len(self.expressions) - 1)))

    def _expression_selected(self, current_row, _current_column, _previous_row, _previous_column):
        if 0 <= current_row < len(self.expressions):
            expression = self.expressions[current_row]
            self.expression_name.setText(expression["name"])
            self.expression_element.setCurrentText(expression["element"])
            self.expression_operator.setCurrentText(expression["operator"])
            self.expression_value.setText(expression["value"])
            self.expression_definition.setText(expression["definition"])

    def _build_reusable_expression(self):
        definition = (
            f"{self.expression_element.currentText()} "
            f"{self.expression_operator.currentText()} {self.expression_value.text().strip()}"
        )
        self.expression_definition.setText(definition)
        if not self.expression_name.text().strip():
            self.expression_name.setText(definition.replace(" ", "_"))

    def _expression_form_data(self):
        return {
            "name": self.expression_name.text().strip().replace(" ", "_"),
            "definition": self.expression_definition.text().strip(),
            "element": self.expression_element.currentText(),
            "operator": self.expression_operator.currentText(),
            "value": self.expression_value.text().strip(),
        }

    def _store_expression(self):
        expression = self._expression_form_data()
        if not expression["name"] or not expression["definition"]:
            QMessageBox.warning(self, "Define Expressions", "Name and Expression Definition are required.")
            return
        if any(item["name"].lower() == expression["name"].lower() for item in self.expressions):
            QMessageBox.warning(self, "Define Expressions", "Expression names must be unique.")
            return
        self.expressions.append(expression)
        self._populate_expressions(len(self.expressions) - 1)

    def _edit_expression(self):
        row = self.expression_table.currentRow()
        expression = self._expression_form_data()
        if row < 0 or not expression["name"] or not expression["definition"]:
            QMessageBox.warning(self, "Define Expressions", "Select an expression and enter a name and definition.")
            return
        if any(index != row and item["name"].lower() == expression["name"].lower() for index, item in enumerate(self.expressions)):
            QMessageBox.warning(self, "Define Expressions", "Expression names must be unique.")
            return
        self.expressions[row] = expression
        self._populate_expressions(row)

    def _delete_expression(self):
        row = self.expression_table.currentRow()
        if 0 <= row < len(self.expressions):
            self.expressions.pop(row)
            self._populate_expressions(row)

    def _cancel_expression(self):
        self.expression_table.clearSelection()
        self.expression_name.clear()
        self.expression_definition.clear()
        self.expression_value.setText("0")

    def _refresh_expression_sources(self):
        current = self.element.currentText()
        self.element.clear()
        self.element.addItems(self.ELEMENTS + [item["name"] for item in self.expressions])
        self.element.setCurrentText(current)

    def _refresh_overview(self):
        self.overview.clear()
        for expression in self.expressions:
            root = QTreeWidgetItem([expression["name"], expression["definition"]])
            root.addChild(QTreeWidgetItem(["Element", expression["element"]]))
            root.addChild(QTreeWidgetItem(["Operator", expression["operator"]]))
            root.addChild(QTreeWidgetItem(["Value", expression["value"]]))
            self.overview.addTopLevelItem(root)

    def _finish(self):
        rules = [self._row_data(row) for row in range(self.table.rowCount())]
        enabled = [rule for rule in rules if rule["enabled"]]
        if not enabled or any(not rule["name"] or not rule["expression"] for rule in enabled):
            QMessageBox.warning(self, "Excursion Reduction", "At least one enabled rule with a name and expression is required.")
            return
        names = [item["name"].lower() for item in self.expressions]
        if len(names) != len(set(names)) or any(not item["definition"] for item in self.expressions):
            QMessageBox.warning(self, "Define Expressions", "Reusable expressions require unique names and definitions.")
            return
        self.result_rules = rules
        self.result_expressions = deepcopy(self.expressions)
        self.accept()


class WaferPostProcessingDialog(QDialog):
    def __init__(self, state=None, *, test_count=0, tests=None, parent=None):
        super().__init__(parent)
        self.state = normalized_wpp_state(state)
        self.test_count = int(test_count or 0)
        if tests:
            self.tests = [str(name).strip() for name in tests if str(name).strip()]
        else:
            self.tests = [f"Test {index}" for index in range(1, self.test_count + 1)]
        self.result_state = None
        self.changed = False
        self._loading = False
        self.property_controls = {}
        self.venn_table = None
        self.venn_template = None
        self.clustering_template = None
        self.manual_cluster_box = None
        self.cluster_help = None
        self.setWindowTitle("Wafer Post Processing")
        self.resize(1180, 760)
        self.setMinimumSize(900, 600)
        self.setStyleSheet(
            "QDialog { background: #cfcbc2; font-family: Arial; font-size: 10px; }"
            "QPushButton { background: #e8e6dd; border: 1px solid #77736b; min-height: 27px; padding: 2px 8px; }"
            "QTableWidget { background: #efefec; gridline-color: #aaa69d; }"
            "QHeaderView::section { background: #dad7cf; border: 1px solid #918d85; padding: 4px; }"
        )
        root = QVBoxLayout(self)
        body = QHBoxLayout()
        body.addWidget(self._operations_panel(), 2)
        body.addWidget(self._property_panel(), 3)
        root.addLayout(body, 1)
        footer = QHBoxLayout()
        self.validation = QLabel()
        footer.addWidget(self.validation, 1)
        ok = QPushButton("OK")
        ok.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        footer.addWidget(ok)
        footer.addWidget(cancel)
        root.addLayout(footer)
        self._populate_operations()
        self.operations.selectRow(0)

    def _operations_panel(self):
        panel = QFrame()
        panel.setFrameShape(QFrame.StyledPanel)
        layout = QVBoxLayout(panel)
        heading = QLabel("Post Processing Operations")
        heading.setStyleSheet("font-size: 13px; font-weight: bold;")
        layout.addWidget(heading)
        template_row = QHBoxLayout()
        self.template = QComboBox()
        self.template.setEditable(True)
        self.template.addItem("Default")
        for name in sorted(self.state["templates"]):
            self.template.addItem(name)
        self.template.setCurrentText(self.state.get("template_name", "Default"))
        self.template.activated.connect(self._load_template_index)
        template_row.addWidget(QLabel("Template"))
        template_row.addWidget(self.template, 1)
        layout.addLayout(template_row)
        template_actions = QHBoxLayout()
        self.template_scope = QComboBox()
        self.template_scope.addItems(["Whole Scheme", "Selected Operation"])
        template_actions.addWidget(self.template_scope, 1)
        save = QPushButton("Save")
        save.clicked.connect(self._save_template)
        delete = QPushButton("Delete")
        delete.clicked.connect(self._delete_template)
        defaults = QPushButton("Default")
        defaults.clicked.connect(self._defaults)
        template_actions.addWidget(save)
        template_actions.addWidget(delete)
        template_actions.addWidget(defaults)
        layout.addLayout(template_actions)
        self.operations = QTableWidget(0, 2)
        self.operations.setHorizontalHeaderLabels(["Enabled", "Operation"])
        self.operations.horizontalHeader().setStretchLastSection(True)
        self.operations.verticalHeader().setVisible(False)
        self.operations.setColumnWidth(0, 105)
        self.operations.currentCellChanged.connect(self._operation_selected)
        self.operations.itemChanged.connect(self._operation_item_changed)
        layout.addWidget(self.operations, 1)
        order = QHBoxLayout()
        up = QPushButton("Move Up")
        up.clicked.connect(lambda: self._move_operation(-1))
        down = QPushButton("Move Down")
        down.clicked.connect(lambda: self._move_operation(1))
        order.addStretch(1)
        order.addWidget(up)
        order.addWidget(down)
        layout.addLayout(order)
        return panel

    def _property_panel(self):
        panel = QFrame()
        panel.setFrameShape(QFrame.StyledPanel)
        layout = QVBoxLayout(panel)
        self.property_title = QLabel("Operation Properties")
        self.property_title.setStyleSheet("font-size: 13px; font-weight: bold;")
        layout.addWidget(self.property_title)
        self.property_note = QLabel("Operations execute from top to bottom. Enable an operation, select it, and define its parameters.")
        self.property_note.setWordWrap(True)
        layout.addWidget(self.property_note)
        self.property_host = QWidget()
        self.property_layout = QGridLayout(self.property_host)
        self.property_layout.setColumnStretch(0, 1)
        self.property_layout.setColumnStretch(1, 2)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(self.property_host)
        layout.addWidget(scroll, 1)
        self.venn_help = QTextEdit()
        self.venn_help.setReadOnly(True)
        self.venn_help.setHtml(VENN_PAGE_HELP)
        self.venn_help.setFixedHeight(168)
        self.venn_help.setStyleSheet(
            "QTextEdit { background: #ffffcc; border: 1px solid #8a8a8a; font-size: 12px; }"
        )
        self.venn_help.hide()
        layout.addWidget(self.venn_help, 0)
        return panel

    def _populate_operations(self, selected_name=None):
        self._loading = True
        self.operations.setRowCount(0)
        selected_row = 0
        for row, operation in enumerate(self.state["operations"]):
            self.operations.insertRow(row)
            if operation["name"] in IMPLICIT_ENABLE_OPERATIONS:
                operation["enabled"] = implicit_operation_enabled(operation)
                enabled = QTableWidgetItem("")
                enabled.setFlags(enabled.flags() & ~Qt.ItemIsUserCheckable & ~Qt.ItemIsEditable)
                if operation["name"] == "Sampling":
                    enabled.setToolTip("Sampling is enabled by selecting methods on its Property page.")
                else:
                    enabled.setToolTip(
                        "Defect Limits is enabled by the override settings on its Property page."
                    )
            else:
                enabled = QTableWidgetItem()
                enabled.setFlags(enabled.flags() | Qt.ItemIsUserCheckable)
                enabled.setCheckState(Qt.Checked if operation.get("enabled") else Qt.Unchecked)
            self.operations.setItem(row, 0, enabled)
            name_item = QTableWidgetItem(operation["name"])
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.operations.setItem(row, 1, name_item)
            if operation["name"] == selected_name:
                selected_row = row
        self._loading = False
        if self.state["operations"]:
            self.operations.selectRow(selected_row)
            self._show_operation(selected_row)
        self._refresh_validation()

    def _operation_selected(self, current_row, _current_column, _previous_row, _previous_column):
        if not self._loading and current_row >= 0:
            self._show_operation(current_row)

    def _operation_item_changed(self, item):
        if self._loading or item.column() != 0:
            return
        if not (item.flags() & Qt.ItemIsUserCheckable):
            return
        row = item.row()
        if 0 <= row < len(self.state["operations"]):
            self.state["operations"][row]["enabled"] = item.checkState() == Qt.Checked
            self.changed = True
            self._refresh_validation()

    def _clear_property_layout(self):
        self.property_controls = {}
        self.venn_table = None
        self.venn_template = None
        self.clustering_template = None
        self.manual_cluster_box = None
        self.cluster_help = None
        while self.property_layout.count():
            item = self.property_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        for row in range(8):
            self.property_layout.setRowStretch(row, 0)

    def _show_operation(self, row):
        if row < 0 or row >= len(self.state["operations"]):
            return
        self._clear_property_layout()
        operation = self.state["operations"][row]
        name = operation["name"]
        if name == "Venn":
            self._show_venn_page(operation)
            return
        if name == "Clustering":
            self._show_clustering_page(operation)
            return
        self.property_title.setText(name)
        self.property_title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.property_title.setStyleSheet("font-size: 13px; font-weight: bold;")
        self.property_note.show()
        self.venn_help.hide()
        self.property_layout.addWidget(QLabel("Property"), 0, 0)
        self.property_layout.addWidget(QLabel("Value"), 0, 1)
        for index, (key, label, kind, default) in enumerate(OPERATION_SCHEMAS[name], start=1):
            property_label = QLabel(label)
            property_label.setWordWrap(True)
            property_label.setMaximumWidth(280)
            self.property_layout.addWidget(property_label, index, 0)
            value = operation["parameters"].get(key)
            if kind == "bool":
                control = QCheckBox()
                control.setChecked(bool(value))
                control.toggled.connect(lambda checked, n=name, k=key: self._set_parameter(n, k, checked))
            elif kind == "choice":
                control = QComboBox()
                control.addItems(default[1])
                control.setCurrentText(str(value))
                control.currentTextChanged.connect(lambda text, n=name, k=key: self._set_parameter(n, k, text))
            elif kind == "int":
                control = QSpinBox()
                control.setRange(0, 100000000)
                control.setValue(int(value))
                control.valueChanged.connect(lambda number, n=name, k=key: self._set_parameter(n, k, number))
            elif kind == "float":
                control = QDoubleSpinBox()
                control.setRange(0.0, 100000000.0)
                control.setDecimals(3)
                control.setValue(float(value))
                control.valueChanged.connect(lambda number, n=name, k=key: self._set_parameter(n, k, number))
            elif kind in ("groups", "precision_rules", "excursion_rules", "expressions", "method_settings"):
                control = self._structured_control(name, key, kind, value)
            else:
                control = QLineEdit(str(value))
                control.textChanged.connect(lambda text, n=name, k=key: self._set_parameter(n, k, text))
            self.property_controls[key] = control
            self.property_layout.addWidget(control, index, 1)
        self.property_layout.setRowStretch(len(OPERATION_SCHEMAS[name]) + 1, 1)

    def _show_venn_page(self, operation):
        self.property_title.setText("Venn")
        self.property_title.setAlignment(Qt.AlignCenter)
        self.property_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.property_note.hide()
        self.venn_help.show()
        parameters = operation["parameters"]
        page = QWidget()
        page.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(6, 2, 6, 4)
        layout.setSpacing(6)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(4)
        self.venn_template = QComboBox()
        self.venn_template.setEditable(True)
        self.venn_template.setFixedWidth(190)
        for index in range(self.template.count()):
            self.venn_template.addItem(self.template.itemText(index))
        self.venn_template.setCurrentText(self.template.currentText())
        self.venn_template.activated.connect(self._venn_template_activated)
        toolbar.addWidget(self.venn_template)
        for kind, tip, callback in (
            ("save", "Save template", self._save_venn_template),
            ("delete", "Delete template", self._delete_venn_template),
            ("new", "Restore default scheme", self._defaults),
        ):
            button = QPushButton()
            button.setIcon(_classic_toolbar_icon(kind))
            button.setToolTip(tip)
            button.setFixedSize(24, 22)
            button.setStyleSheet("QPushButton { min-height: 20px; min-width: 22px; padding: 0; }")
            button.clicked.connect(callback)
            toolbar.addWidget(button)
        toolbar.addStretch(1)
        layout.addLayout(toolbar)

        controls = QHBoxLayout()
        controls.setSpacing(8)
        edit_groups = QPushButton("Edit Groups")
        edit_groups.clicked.connect(lambda: self._edit_structured("Venn", "test_groups", "groups"))
        controls.addWidget(edit_groups)
        controls.addWidget(QLabel("Default Tolerance: (μm)"))
        tolerance = QLineEdit(_format_um(parameters.get("default_tolerance_um", 5)))
        tolerance.setFixedWidth(56)
        tolerance.editingFinished.connect(lambda: self._set_venn_tolerance(tolerance.text()))
        controls.addWidget(tolerance)
        controls.addStretch(1)
        multi = QCheckBox("Enable Multi-Test")
        multi.blockSignals(True)
        multi.setChecked(bool(parameters.get("enable_multi_test")))
        multi.blockSignals(False)
        multi.toggled.connect(self._on_venn_multi_test)
        controls.addWidget(multi)
        clear_ids = QCheckBox("Clear Venn ID's")
        clear_ids.blockSignals(True)
        clear_ids.setChecked(bool(parameters.get("clear_venn_ids", True)))
        clear_ids.blockSignals(False)
        clear_ids.toggled.connect(lambda checked: self._set_parameter("Venn", "clear_venn_ids", checked))
        controls.addWidget(clear_ids)
        layout.addLayout(controls)

        self.venn_table = QTableWidget(16, 6)
        self.venn_table.setHorizontalHeaderLabels([
            "Groups", "Test IDs", "Tolerance", "Duplicate Mode", "Inspected Area Mode", "",
        ])
        self.venn_table.verticalHeader().setVisible(False)
        self.venn_table.setShowGrid(True)
        self.venn_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.venn_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.venn_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.venn_table.horizontalHeader().setStretchLastSection(False)
        self.venn_table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.venn_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.venn_table.setStyleSheet(
            "QTableWidget { background: white; gridline-color: #b5b5b5; }"
            "QHeaderView::section { background: #d9d9d9; color: black; border: 1px solid #9a9a9a; "
            "padding: 3px; font-weight: normal; }"
        )
        self._fill_venn_table(operation)
        layout.addWidget(self.venn_table, 1)
        self.property_layout.addWidget(page, 0, 0, 1, 2)
        self.property_layout.setRowStretch(0, 1)
        QTimer.singleShot(0, self._fit_venn_columns)

    def _show_clustering_page(self, operation):
        self.property_title.setText("Clustering")
        self.property_title.setAlignment(Qt.AlignCenter)
        self.property_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.property_note.hide()
        self.venn_help.hide()
        parameters = operation["parameters"]
        page = QWidget()
        page.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        page.setStyleSheet(_checkbox_indicator_style())
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setSpacing(10)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(4)
        self.clustering_template = QComboBox()
        self.clustering_template.setEditable(True)
        self.clustering_template.setFixedWidth(190)
        for index in range(self.template.count()):
            self.clustering_template.addItem(self.template.itemText(index))
        self.clustering_template.setCurrentText(self.template.currentText())
        self.clustering_template.activated.connect(self._clustering_template_activated)
        toolbar.addWidget(self.clustering_template)
        for kind, tip, callback in (
            ("save", "Save template", self._save_venn_template),
            ("delete", "Delete template", self._delete_venn_template),
            ("new", "Restore default scheme", self._defaults),
        ):
            button = QPushButton()
            button.setIcon(_classic_toolbar_icon(kind))
            button.setToolTip(tip)
            button.setFixedSize(24, 22)
            button.setStyleSheet("QPushButton { min-height: 20px; min-width: 22px; padding: 0; }")
            button.clicked.connect(callback)
            toolbar.addWidget(button)
        toolbar.addStretch(1)
        layout.addLayout(toolbar)

        column = QVBoxLayout()
        column.setSpacing(10)
        auto = QCheckBox("Auto Clustering Enabled")
        auto.blockSignals(True)
        auto.setChecked(bool(parameters.get("auto_clustering", True)))
        auto.blockSignals(False)
        auto.toggled.connect(self._on_auto_clustering)
        column.addWidget(auto)

        self.manual_cluster_box = QGroupBox("Manual Clustering Settings")
        manual_form = QGridLayout(self.manual_cluster_box)
        manual_form.setContentsMargins(12, 16, 12, 10)
        manual_form.setHorizontalSpacing(16)
        manual_form.setColumnStretch(2, 1)
        minimum = QLineEdit(str(int(parameters.get("minimum_defects", 2))))
        minimum.setFixedWidth(72)
        minimum.editingFinished.connect(lambda: self._set_cluster_int("minimum_defects", minimum, 2))
        distance = QLineEdit(f"{float(parameters.get('distance_threshold_um', 0)):.2f}")
        distance.setFixedWidth(72)
        distance.editingFinished.connect(lambda: self._set_cluster_distance(distance))
        manual_form.addWidget(QLabel("Minimum Defects per Cluster"), 0, 0)
        manual_form.addWidget(minimum, 0, 1)
        manual_form.addWidget(QLabel("Distance Tolerance"), 1, 0)
        manual_form.addWidget(distance, 1, 1)
        manual_form.addWidget(QLabel("um"), 1, 2)
        self.manual_cluster_box.setEnabled(not auto.isChecked())
        column.addWidget(self.manual_cluster_box)

        multiplier_row = QHBoxLayout()
        multiplier_row.addWidget(QLabel("Second Pass Multiplier"))
        multiplier = QLineEdit(str(int(parameters.get("second_pass_multiplier", 3))))
        multiplier.setFixedWidth(72)
        multiplier.editingFinished.connect(lambda: self._set_cluster_int("second_pass_multiplier", multiplier, 3))
        multiplier_row.addWidget(multiplier)
        multiplier_row.addStretch(1)
        column.addLayout(multiplier_row)

        within = QGroupBox("Cluster Within")
        within_layout = QVBoxLayout(within)
        within_layout.setContentsMargins(12, 16, 12, 10)
        self.cluster_each = QRadioButton("Each Test")
        self.cluster_all = QRadioButton("All Tests")
        self.cluster_each.blockSignals(True)
        self.cluster_all.blockSignals(True)
        if parameters.get("cluster_within") == "Each Test":
            self.cluster_each.setChecked(True)
        else:
            self.cluster_all.setChecked(True)
        self.cluster_each.blockSignals(False)
        self.cluster_all.blockSignals(False)
        self.cluster_all.toggled.connect(self._on_cluster_within)
        within_layout.addWidget(self.cluster_each)
        within_layout.addWidget(self.cluster_all)
        column.addWidget(within)

        self.cluster_help = QLabel(self._cluster_within_help(parameters.get("cluster_within", "All Tests")))
        self.cluster_help.setWordWrap(True)
        self.cluster_help.setFixedWidth(360)
        self.cluster_help.setMinimumHeight(42)
        self.cluster_help.setStyleSheet(
            "QLabel { background: #ffffcc; border: 1px solid #8a8a8a; padding: 4px 6px; }"
        )
        column.addWidget(self.cluster_help, 0, Qt.AlignLeft)
        column.addStretch(1)

        body = QHBoxLayout()
        body.addLayout(column)
        body.addStretch(1)
        layout.addLayout(body, 1)
        self.property_layout.addWidget(page, 0, 0, 1, 2)
        self.property_layout.setRowStretch(0, 1)

    def _cluster_within_help(self, mode) -> str:
        if mode == "Each Test":
            return "Cluster Within Each Test: Perform clustering separately for each test"
        return "Cluster Within All Tests: Perform clustering on the entire wafer"

    def _on_auto_clustering(self, checked):
        self._set_parameter("Clustering", "auto_clustering", checked)
        if self.manual_cluster_box is not None:
            self.manual_cluster_box.setEnabled(not checked)

    def _on_cluster_within(self, all_tests):
        mode = "All Tests" if all_tests else "Each Test"
        self._set_parameter("Clustering", "cluster_within", mode)
        if self.cluster_help is not None:
            self.cluster_help.setText(self._cluster_within_help(mode))

    def _set_cluster_int(self, key, edit, fallback):
        try:
            value = int(float(edit.text().strip()))
        except ValueError:
            edit.setText(str(fallback))
            return
        edit.setText(str(value))
        self._set_parameter("Clustering", key, value)

    def _set_cluster_distance(self, edit):
        try:
            value = float(edit.text().strip())
        except ValueError:
            value = 0.0
        if value < 0:
            value = 0.0
        edit.setText(f"{value:.2f}")
        self._set_parameter("Clustering", "distance_threshold_um", value)

    def _clustering_template_activated(self, index):
        if self.clustering_template is None:
            return
        text = self.clustering_template.itemText(index)
        left_index = self.template.findText(text)
        if left_index < 0:
            return
        self.template.setCurrentIndex(left_index)
        self._load_template_index(left_index)

    def _fit_venn_columns(self):
        table = self.venn_table
        if table is None:
            return
        width = table.viewport().width()
        if width < 80:
            return
        weights = (8, 9, 10, 14, 22, 20)
        total = sum(weights)
        for column, weight in enumerate(weights):
            table.setColumnWidth(column, max(52, width * weight // total))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_venn_columns()

    def _fill_venn_table(self, operation):
        if self.venn_table is None:
            return
        parameters = operation.get("parameters", {})
        groups = _normalize_groups(parameters.get("test_groups"))
        multi = bool(parameters.get("enable_multi_test"))
        rows = []
        for index, group in enumerate(groups):
            if multi:
                duplicate = _VENN_DUPLICATE_LABELS.get(group["duplicate_mode"], group["duplicate_mode"])
                area = _VENN_AREA_LABELS.get(group["inspected_area_mode"], group["inspected_area_mode"])
            else:
                duplicate = area = "NA"
            rows.append((
                _venn_group_label(group["name"]),
                _format_venn_test_ids(group["tests"], self.test_count),
                _tolerance_text(group),
                duplicate,
                area,
                index,
            ))
        rows.append((
            "None",
            _unassigned_venn_tests(groups, self.test_count),
            "",
            "NA",
            "NA",
            -1,
        ))
        for row in range(self.venn_table.rowCount()):
            self.venn_table.removeCellWidget(row, 5)
        self.venn_table.setRowCount(max(16, len(rows)))
        self.venn_table.clearContents()
        for row, values in enumerate(rows):
            *cells, group_index = values
            for column, text in enumerate(cells):
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if column == 0:
                    item.setData(Qt.UserRole, group_index)
                self.venn_table.setItem(row, column, item)
            if group_index >= 0:
                button = QPushButton("Edit Parameters")
                button.setStyleSheet("QPushButton { min-height: 22px; padding: 1px 6px; }")
                button.clicked.connect(
                    lambda _checked=False, index=group_index: self._edit_venn_group_parameters(index)
                )
                self.venn_table.setCellWidget(row, 5, button)
                self.venn_table.setRowHeight(row, 32)

    def _venn_operation(self):
        return next(item for item in self.state["operations"] if item["name"] == "Venn")

    def _set_venn_tolerance(self, text):
        try:
            value = float(text)
        except ValueError:
            return
        if value <= 0:
            return
        current = float(self._venn_operation()["parameters"].get("default_tolerance_um", 0))
        if current == value:
            return
        self._set_parameter("Venn", "default_tolerance_um", value)

    def _on_venn_multi_test(self, checked):
        self._set_parameter("Venn", "enable_multi_test", checked)
        self._fill_venn_table(self._venn_operation())

    def _venn_template_activated(self, index):
        if self.venn_template is None:
            return
        text = self.venn_template.itemText(index)
        left_index = self.template.findText(text)
        if left_index < 0:
            return
        self.template.setCurrentIndex(left_index)
        self._load_template_index(left_index)

    def _copy_venn_template_name(self):
        combo = self.venn_template or self.clustering_template
        if combo is not None:
            self.template.setCurrentText(combo.currentText())

    def _sync_venn_template_combo(self):
        current = self.template.currentText()
        for combo in (self.venn_template, self.clustering_template):
            if combo is None:
                continue
            combo.blockSignals(True)
            combo.clear()
            for index in range(self.template.count()):
                combo.addItem(self.template.itemText(index))
            combo.setCurrentText(current)
            combo.blockSignals(False)

    def _save_venn_template(self):
        self._copy_venn_template_name()
        self._save_template()
        self._sync_venn_template_combo()

    def _delete_venn_template(self):
        self._copy_venn_template_name()
        self._delete_template()
        self._sync_venn_template_combo()

    def _venn_table_clicked(self, row, column):
        if self.venn_table is None or column != 5:
            return
        item = self.venn_table.item(row, column)
        name_item = self.venn_table.item(row, 0)
        if item is None or name_item is None or item.text() != "Edit":
            return
        group_index = name_item.data(Qt.UserRole)
        if group_index is None or int(group_index) < 0:
            return
        self._edit_venn_group_parameters(int(group_index))

    def _edit_venn_group_parameters(self, group_index):
        operation = self._venn_operation()
        groups = _normalize_groups(operation["parameters"].get("test_groups"))
        if group_index < 0 or group_index >= len(groups):
            return
        dialog = VennGroupParametersDialog(
            groups[group_index],
            self.tests,
            multi_test=bool(operation["parameters"].get("enable_multi_test")),
            parent=self,
        )
        if _exec_dialog(dialog) != QDialog.Accepted or dialog.result_group is None:
            return
        groups[group_index] = dialog.result_group
        operation["parameters"]["test_groups"] = groups
        self.changed = True
        self._fill_venn_table(operation)
        self._refresh_validation()

    def _structured_control(self, operation_name, key, kind, value):
        host = QWidget()
        layout = QHBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        count = len(value) if isinstance(value, list) else 0
        noun = (
            "group"
            if kind == "groups"
            else "method"
            if kind == "method_settings"
            else "expression"
            if kind == "expressions"
            else "rule"
        )
        summary = QLabel(f"{count} {noun}(s) configured" if kind == "method_settings" else f"{count} {noun}(s) defined")
        layout.addWidget(summary, 1)
        button = QPushButton("Edit...")
        button.clicked.connect(lambda: self._edit_structured(operation_name, key, kind))
        layout.addWidget(button)
        self.property_controls[key] = button
        return host

    def _edit_structured(self, operation_name, key, kind):
        operation = next(item for item in self.state["operations"] if item["name"] == operation_name)
        current = operation["parameters"].get(key)
        if kind == "groups":
            dialog = MultiTestGroupsDialog(current, self.tests, self)
            result_attribute = "result_groups"
        elif kind == "precision_rules":
            dialog = PrecisionRulesDialog(
                current,
                {
                    "allow_filter_overlap": operation["parameters"].get("allow_filter_overlap"),
                    "sample_bin_assignment": operation["parameters"].get("sample_bin_assignment"),
                    "overlapping_bin_assignment": operation["parameters"].get("overlapping_bin_assignment"),
                },
                self,
            )
            result_attribute = "result_rules"
        elif kind == "method_settings":
            dialog = SamplingMethodSettingsDialog(current, self)
            result_attribute = "result_settings"
        else:
            dialog = ExcursionRuleEditorDialog(
                operation["parameters"].get("rules"),
                operation["parameters"].get("expressions"),
                self,
            )
            result_attribute = "result_rules"
        if _exec_dialog(dialog) != QDialog.Accepted:
            return
        if kind in ("excursion_rules", "expressions"):
            operation["parameters"]["rules"] = deepcopy(dialog.result_rules)
            operation["parameters"]["expressions"] = deepcopy(dialog.result_expressions)
        elif kind == "precision_rules":
            operation["parameters"][key] = deepcopy(dialog.result_rules)
            operation["parameters"].update(deepcopy(dialog.result_advanced))
        else:
            operation["parameters"][key] = deepcopy(getattr(dialog, result_attribute))
        self.changed = True
        row = self.state["operations"].index(operation)
        self._show_operation(row)
        self._refresh_validation()

    def _set_parameter(self, operation_name, key, value):
        for operation in self.state["operations"]:
            if operation["name"] == operation_name:
                operation["parameters"][key] = value
                if operation_name in IMPLICIT_ENABLE_OPERATIONS:
                    operation["enabled"] = implicit_operation_enabled(operation)
                self.changed = True
                self._refresh_validation()
                return

    def _move_operation(self, direction):
        row = self.operations.currentRow()
        target = row + direction
        if row < 0 or target < 0 or target >= len(self.state["operations"]):
            return
        self.state["operations"][row], self.state["operations"][target] = self.state["operations"][target], self.state["operations"][row]
        self.changed = True
        self._populate_operations(self.state["operations"][target]["name"])

    def _load_template_index(self, index):
        name = self.template.itemText(index)
        if name == "Default":
            self._defaults()
            return
        stored = self.state["templates"].get(name)
        if not stored:
            return
        templates = deepcopy(self.state["templates"])
        if stored.get("scope") == "operation":
            replacement = deepcopy(stored.get("operation", {}))
            for position, operation in enumerate(self.state["operations"]):
                if operation["name"] == replacement.get("name"):
                    self.state["operations"][position] = replacement
                    break
        else:
            self.state["operations"] = deepcopy(stored.get("operations", self.state["operations"]))
        self.state = normalized_wpp_state(self.state)
        self.state["templates"] = templates
        self.state["template_name"] = name
        self.changed = True
        self._populate_operations()

    def _save_template(self):
        name = self.template.currentText().strip()
        if not name or name == "Default":
            name = "Custom"
            self.template.setCurrentText(name)
        if self.template_scope.currentText() == "Selected Operation":
            row = self.operations.currentRow()
            if row < 0:
                return
            stored = {"scope": "operation", "operation": deepcopy(self.state["operations"][row])}
        else:
            stored = {"scope": "scheme", "operations": deepcopy(self.state["operations"])}
        self.state["templates"][name] = stored
        self.state["template_name"] = name
        if self.template.findText(name) < 0:
            self.template.addItem(name)
        self.template.setCurrentText(name)
        self.changed = True

    def _delete_template(self):
        name = self.template.currentText().strip()
        if name == "Default" or name not in self.state["templates"]:
            return
        del self.state["templates"][name]
        index = self.template.findText(name)
        if index >= 0:
            self.template.removeItem(index)
        self.template.setCurrentText("Default")
        self.state["template_name"] = "Default"
        self.changed = True

    def _defaults(self):
        selected_name = None
        row = self.operations.currentRow()
        if row >= 0:
            selected_name = self.state["operations"][row]["name"]
        if self.template_scope.currentText() == "Selected Operation" and selected_name:
            self.state["operations"][row] = _default_operation(selected_name)
        else:
            templates = deepcopy(self.state["templates"])
            self.state = default_wpp_state()
            self.state["templates"] = templates
            self.state["template_name"] = "Default"
            self.template.setCurrentText("Default")
        self.changed = True
        self._populate_operations(selected_name)

    def _refresh_validation(self):
        errors = validate_wpp(self.state, self.test_count)
        if errors:
            self.validation.setText("; ".join(errors))
            self.validation.setStyleSheet("color: #a41515; font-weight: bold;")
        else:
            enabled = sum(1 for item in self.state["operations"] if item.get("enabled"))
            self.validation.setText(f"{enabled} operation(s) enabled")
            self.validation.setStyleSheet("color: #176b38;")

    def _finish(self):
        errors = validate_wpp(self.state, self.test_count)
        if errors:
            QMessageBox.warning(self, "Wafer Post Processing", "\n".join(errors))
            return
        self.result_state = normalized_wpp_state(self.state)
        self.accept()

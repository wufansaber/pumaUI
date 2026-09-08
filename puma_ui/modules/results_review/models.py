from __future__ import annotations

from collections import Counter
from copy import deepcopy
import re
from uuid import uuid4

from ..run_control.models import apply_wafer_post_processing


REVIEW_FILTER_ANALYSIS_OPERATIONS = [
    ("General Filter", "Filter"),
    ("Venn ID Filter", "Filter"),
    ("Sensitivity Filter", "Filter"),
    ("Class Code Filter", "Filter"),
    ("Channel Filter", "Filter"),
    ("Advanced Filtering", "Filter"),
    ("Clustering", "Analysis"),
    ("Repeater Analysis", "Analysis"),
    ("Defect Source Analysis", "Analysis"),
    ("Spatial Population", "Analysis"),
    ("Population Arbitration", "Analysis"),
    ("Venn", "Analysis"),
    ("Excursion Reduction", "Analysis"),
    ("Sampling", "Analysis"),
]

SUPER_CLASS_NAMES = ["Killer", "Real", "Nuisance", "Disregard", "Unknown"]


def default_filter_analysis_state() -> dict:
    return {
        "operations": [
            {"name": name, "type": kind, "enabled": False}
            for name, kind in REVIEW_FILTER_ANALYSIS_OPERATIONS
        ],
        "filters": default_filter_state(),
        "analysis": None,
        "templates": {},
    }


def normalized_filter_analysis_state(value=None) -> dict:
    result = default_filter_analysis_state()
    if not isinstance(value, dict):
        return result
    existing = {
        item.get("name"): item
        for item in value.get("operations", [])
        if isinstance(item, dict)
    }
    requested = [
        item.get("name")
        for item in value.get("operations", [])
        if isinstance(item, dict) and item.get("name") in dict(REVIEW_FILTER_ANALYSIS_OPERATIONS)
    ]
    requested.extend(name for name, _kind in REVIEW_FILTER_ANALYSIS_OPERATIONS if name not in requested)
    types = dict(REVIEW_FILTER_ANALYSIS_OPERATIONS)
    result["operations"] = [
        {
            "name": name,
            "type": types[name],
            "enabled": bool(existing.get(name, {}).get("enabled", False)),
        }
        for name in requested
    ]
    result["filters"] = {**default_filter_state(), **deepcopy(value.get("filters") or {})}
    result["analysis"] = deepcopy(value.get("analysis"))
    result["templates"] = deepcopy(value.get("templates") or {})
    return result


def _operation_filter_state(filters: dict, operation_name: str) -> dict:
    state = default_filter_state()
    keys = {
        "General Filter": {
            "minimum_size_um", "maximum_size_um", "adder_mode", "cluster_mode",
            "repeater_mode", "polarities", "marked_only", "unreviewed_only",
            "include_ids", "exclude_ids", "image_filter", "show_binner_filtered", "scale_groups",
        },
        "Venn ID Filter": {"venn_ids", "duplicate_mode"},
        "Sensitivity Filter": {
            "tests", "minimum_signal", "maximum_signal", "region_ids", "threshold_regions",
        },
        "Class Code Filter": {
            "class_codes", "rough_bins", "rough_classes", "rough_groups"
        },
        "Channel Filter": {"channels"},
        "Advanced Filtering": {"advanced_expression"},
    }.get(operation_name, set())
    for key in keys:
        if key in filters:
            state[key] = deepcopy(filters[key])
    return state


def execute_filter_analysis(
    result: dict,
    state: dict,
    *,
    previous_results: list[dict] | None = None,
    source_ids: list | set | None = None,
) -> tuple[dict, dict]:
    configured = normalized_filter_analysis_state(state)
    updated = deepcopy(result)
    all_defects = list(updated.get("defects", []))
    selected_ids = set(source_ids) if source_ids is not None else None
    active = [
        defect for defect in all_defects
        if selected_ids is None or defect.get("id") in selected_ids
    ]
    execution = []
    analysis_state = configured.get("analysis") or {"operations": []}
    analysis_by_name = {
        item.get("name"): item
        for item in analysis_state.get("operations", [])
        if isinstance(item, dict)
    }
    for operation in configured["operations"]:
        if not operation.get("enabled"):
            continue
        name = operation["name"]
        before = len(active)
        if operation.get("type") == "Filter":
            active = filter_defects(
                {"defects": active},
                _operation_filter_state(configured["filters"], name),
            )
            execution.append({"name": name, "type": "Filter", "before": before, "after": len(active)})
            continue
        configured_operation = deepcopy(analysis_by_name.get(name))
        if not configured_operation:
            execution.append({
                "name": name, "type": "Analysis", "before": before, "after": before,
                "status": "Not configured",
            })
            continue
        configured_operation["enabled"] = True
        processed, report = apply_wafer_post_processing(
            active,
            {**updated, "wafer_post_processing": {"operations": [configured_operation]}},
            previous_results=previous_results,
            context={
                "lot_id": updated.get("lot_id", ""),
                "wafer_id": updated.get("wafer_id", ""),
                "scribe_id": updated.get("scribe_id", ""),
            },
        )
        before_ids = {defect.get("id") for defect in active}
        after_ids = {defect.get("id") for defect in processed}
        removed_ids = before_ids - after_ids
        if removed_ids:
            all_defects = [defect for defect in all_defects if defect.get("id") not in removed_ids]
        existing_ids = {defect.get("id") for defect in all_defects}
        all_defects.extend(defect for defect in processed if defect.get("id") not in existing_ids)
        active = processed
        execution.append({
            "name": name, "type": "Analysis", "before": before, "after": len(active),
            "report": report,
        })
    updated["defects"] = all_defects
    updated["defect_count"] = len(all_defects)
    updated["filter_analysis"] = deepcopy(configured)
    updated["review_analysis_execution"] = execution
    updated.setdefault("review_log", []).append(
        "Filter and Analysis executed in order: "
        + (", ".join(item["name"] for item in execution) or "none")
    )
    return updated, {
        "operations": execution,
        "visible_ids": [defect.get("id") for defect in active],
        "total_count": len(all_defects),
    }


def default_filter_state() -> dict:
    return {
        "tests": [],
        "class_codes": [],
        "minimum_signal": 0.0,
        "maximum_signal": 1000000.0,
        "minimum_size_um": 0.0,
        "maximum_size_um": 1000000.0,
        "rough_bins": [],
        "rough_classes": [],
        "rough_groups": [],
        "venn_ids": [],
        "duplicate_mode": "Non-Duplicates",
        "channels": [],
        "polarities": [],
        "region_ids": [],
        "threshold_regions": [],
        "scale_groups": [],
        "adder_mode": "All",
        "cluster_mode": "All",
        "repeater_mode": "All",
        "advanced_expression": "",
        "marked_only": False,
        "unreviewed_only": False,
        "include_ids": [],
        "exclude_ids": [],
        "image_filter": "All Defects",
        "show_binner_filtered": False,
    }


def result_matches_recipe(result: dict, recipe: dict | None) -> bool:
    if not recipe:
        return False
    result_versions = result.get("feature_vector_versions") or {}
    if result_versions:
        recipe_versions = {
            test.get("name", "Test 1"): test.get("feature_vector_version", "3.0A")
            for test in recipe.get("tests", [])
            if test.get("mode") != "No Test"
        }
        if any(
            recipe_versions.get(test_name) != version
            for test_name, version in result_versions.items()
        ):
            return False
    result_classifiers = result.get("classifier_version_ids") or []
    if result_classifiers:
        recipe_classifiers = {}
        for test in recipe.get("tests", []):
            test_name = test.get("name", "Test 1")
            classifiers = list((test.get("nef") or {}).get("classifiers") or [])
            if test.get("ido_classifier"):
                classifiers.append(test["ido_classifier"])
            for classifier in classifiers:
                key = (
                    test_name,
                    classifier.get("name", ""),
                    classifier.get("type", "iDO" if classifier is test.get("ido_classifier") else ""),
                )
                recipe_classifiers[key] = classifier.get("feature_vector_version", "")
        for classifier in result_classifiers:
            key = (
                classifier.get("test", ""),
                classifier.get("name", ""),
                classifier.get("type", ""),
            )
            if key not in recipe_classifiers or (
                classifier.get("feature_vector_version", "")
                and recipe_classifiers[key] != classifier.get("feature_vector_version", "")
            ):
                return False
    if result.get("recipe_id") and recipe.get("id"):
        return result["recipe_id"] == recipe["id"]
    return (
        result.get("inspection") == recipe.get("inspection")
        and result.get("device") == recipe.get("device")
        and result.get("step") == recipe.get("step")
    )


def filter_defects(result: dict, filters: dict | None = None) -> list[dict]:
    state = {**default_filter_state(), **(filters or {})}
    tests = set(state.get("tests") or [])
    class_codes = {int(item) for item in state.get("class_codes") or []}
    minimum_signal = float(state.get("minimum_signal", 0.0))
    maximum_signal = float(state.get("maximum_signal", 1000000.0))
    minimum_size = float(state.get("minimum_size_um", 0.0))
    maximum_size = float(state.get("maximum_size_um", 1000000.0))
    rough_bins = {int(item) for item in state.get("rough_bins") or []}
    rough_classes = {str(item) for item in state.get("rough_classes") or []}
    rough_groups = {str(item) for item in state.get("rough_groups") or []}
    venn_ids = {int(item) for item in state.get("venn_ids") or []}
    duplicate_mode = state.get("duplicate_mode", "Non-Duplicates")
    channels = {int(item) for item in state.get("channels") or []}
    polarities = set(state.get("polarities") or [])
    region_ids = set(state.get("region_ids") or [])
    threshold_regions = set(state.get("threshold_regions") or [])
    scale_groups = set(state.get("scale_groups") or [])
    include_ids = set(state.get("include_ids") or [])
    exclude_ids = set(state.get("exclude_ids") or [])
    image_filter = state.get("image_filter", "All Defects")
    defects = []
    for defect in result.get("defects", []):
        if defect.get("binner_filtered") and not state.get("show_binner_filtered"):
            continue
        if include_ids and defect.get("id") not in include_ids:
            continue
        if defect.get("id") in exclude_ids:
            continue
        has_patch = bool(defect.get("has_patch_image", True))
        has_sem = bool(defect.get("has_sem_image", False))
        has_manual = bool(defect.get("has_manual_image", False))
        has_any = has_patch or has_sem or has_manual
        if image_filter == "With Any Image" and not has_any:
            continue
        if image_filter == "With Patch Images" and not has_patch:
            continue
        if image_filter == "With SEM Images" and not has_sem:
            continue
        if image_filter == "With Manual Images" and not has_manual:
            continue
        if image_filter == "Without Images" and has_any:
            continue
        if tests and defect.get("test") not in tests:
            continue
        if class_codes and int(defect.get("class_code", 0)) not in class_codes:
            continue
        if rough_bins and int(defect.get("roughbin", 0)) not in rough_bins:
            continue
        if rough_classes and str(defect.get("ido_rough_code", "")) not in rough_classes:
            continue
        if rough_groups and str(defect.get("ido_rough_group", "")) not in rough_groups:
            continue
        if venn_ids and int(defect.get("venn_id", 0)) not in venn_ids:
            continue
        is_duplicate = bool(defect.get("multi_test_duplicate") or defect.get("duplicate"))
        if duplicate_mode == "Duplicates" and not is_duplicate:
            continue
        if duplicate_mode == "Non-Duplicates" and is_duplicate:
            continue
        if channels and int(defect.get("channel", 0)) not in channels:
            continue
        if polarities and defect.get("polarity") not in polarities:
            continue
        if region_ids and defect.get("region_id") not in region_ids:
            continue
        if threshold_regions and defect.get("threshold_region") not in threshold_regions:
            continue
        if scale_groups and defect.get("sizing_scale_group") not in scale_groups:
            continue
        adder_mode = state.get("adder_mode", "All")
        if adder_mode != "All" and (adder_mode == "Adders") != bool(defect.get("adder", True)):
            continue
        cluster_mode = state.get("cluster_mode", "All")
        if cluster_mode != "All" and (cluster_mode == "Clustered") != bool(defect.get("cluster_id", 0)):
            continue
        repeater_mode = state.get("repeater_mode", "All")
        if repeater_mode != "All" and (repeater_mode == "Repeaters") != bool(defect.get("repeater", False)):
            continue
        if not minimum_signal <= float(defect.get("signal", 0.0)) <= maximum_signal:
            continue
        if not minimum_size <= float(defect.get("size_um", 0.0)) <= maximum_size:
            continue
        expression = str(state.get("advanced_expression", "")).strip()
        if expression and not _matches_review_expression(defect, expression):
            continue
        if state.get("marked_only") and not defect.get("marked"):
            continue
        if state.get("unreviewed_only") and defect.get("reviewed"):
            continue
        defects.append(defect)
    return defects


def _matches_review_expression(defect: dict, expression: str) -> bool:
    import re

    values = {
        "Defect Size": defect.get("size_um", 0),
        "Intensity": defect.get("signal", 0),
        "Class Code": defect.get("class_code", 0),
        "Roughbin": defect.get("roughbin", 0),
        "Channel": defect.get("channel", 0),
        "Test ID": defect.get("test", ""),
        "Region ID": defect.get("region_id", ""),
    }
    parts = re.split(r"\s+AND\s+", expression, flags=re.IGNORECASE)
    for part in parts:
        match = re.match(r"^\s*(.+?)\s*(>=|<=|!=|=|>|<)\s*(.+?)\s*$", part)
        if not match:
            return False
        name, operator, expected_text = match.groups()
        actual = values.get(name.strip())
        if actual is None:
            return False
        expected_text = expected_text.strip().strip("'\"")
        try:
            left, right = float(actual), float(expected_text)
        except (TypeError, ValueError):
            left, right = str(actual), expected_text
        if not {
            "=": left == right,
            "!=": left != right,
            ">": left > right,
            ">=": left >= right,
            "<": left < right,
            "<=": left <= right,
        }[operator]:
            return False
    return True


def apply_binner(
    result: dict,
    visible_defects: list[dict],
    *,
    nef_state=None,
    ido_classifier=None,
    enable_nef=False,
    enable_ido=False,
    clear_codes_on_wafer=False,
    use_selected_defects=False,
    selected_ids=None,
) -> tuple[dict, dict]:
    if not result.get("feature_vector_file"):
        raise ValueError("Apply Binner requires a result collected with Save Feature Vectors")
    if not enable_nef and not enable_ido:
        raise ValueError("Enable NEF or iDO before executing Apply Binner")
    nef_state = deepcopy(nef_state or {})
    ido_classifier = deepcopy(ido_classifier or {})
    if enable_nef and not nef_state.get("classifiers"):
        raise ValueError("Select an ST-NEF or sequential-NEF configuration")
    if enable_ido and not ido_classifier:
        raise ValueError("Select an iDO classifier")
    selected_ids = {int(value) for value in (selected_ids or [])}
    visible_ids = {int(item.get("id", -1)) for item in visible_defects}
    target_ids = selected_ids & visible_ids if use_selected_defects else visible_ids
    if use_selected_defects and not target_ids:
        raise ValueError("Select at least one displayed defect")
    if not target_ids:
        raise ValueError("No displayed defects are available for Apply Binner")
    updated = deepcopy(result)
    if clear_codes_on_wafer:
        for defect in updated.get("defects", []):
            defect["class_code"] = 0
            defect["roughbin"] = 0
            defect.pop("ido_rough_code", None)
            defect.pop("ido_rough_group", None)
            defect.pop("classification_source", None)
            defect.pop("binner_filtered", None)
            defect.pop("nuisance", None)
    filtered = 0
    classified = 0
    keep_nuisance = bool(nef_state.get("keep_nuisance_defects"))
    rough_code = str(ido_classifier.get("rough_code") or "").strip()
    for defect in updated.get("defects", []):
        if int(defect.get("id", -1)) not in target_ids:
            continue
        defect.pop("binner_filtered", None)
        if enable_nef and int(defect.get("id", 0)) % 7 == 0:
            defect["nuisance"] = True
            defect["classification_source"] = "ST-NEF"
            if not keep_nuisance:
                defect["binner_filtered"] = True
                filtered += 1
        if enable_ido and not defect.get("binner_filtered"):
            defect["ido_rough_code"] = rough_code or f"R{1 + int(defect.get('id', 0)) % 8}"
            defect["ido_rough_group"] = (
                ido_classifier.get("rough_group")
                or f"G{1 + int(defect.get('id', 0)) % 4}"
            )
            defect["classification_source"] = "iDO"
            classified += 1
    stats = {
        "displayed": len(visible_ids),
        "processed": len(target_ids),
        "filtered": filtered,
        "classified": classified,
        "enable_nef": bool(enable_nef),
        "enable_ido": bool(enable_ido),
        "clear_codes_on_wafer": bool(clear_codes_on_wafer),
        "use_selected_defects": bool(use_selected_defects),
    }
    updated.setdefault("binner_history", []).append(deepcopy(stats))
    updated.setdefault("review_log", []).append(
        "Apply Binner processed {processed} displayed defect(s), filtered {filtered}, "
        "and classified {classified}".format(**stats)
    )
    return updated, stats


def review_summary(result: dict, defects: list[dict] | None = None) -> dict:
    selected = defects if defects is not None else list(result.get("defects", []))
    by_test = Counter(str(item.get("test", "")) for item in selected)
    by_class = Counter(int(item.get("class_code", 0)) for item in selected)
    return {
        "total": len(result.get("defects", [])),
        "visible": len(selected),
        "marked": sum(bool(item.get("marked")) for item in selected),
        "reviewed": sum(bool(item.get("reviewed")) for item in selected),
        "by_test": dict(by_test),
        "by_class": dict(by_class),
    }


def select_wafer_transfer_defects(
    result: dict,
    visible_defects: list[dict],
    *,
    scope: str,
    include_duplicates: bool = False,
) -> list[dict]:
    if scope == "Shown Defects":
        return list(visible_defects)
    selected = list(result.get("defects", []))
    if include_duplicates:
        return selected
    return [
        defect for defect in selected
        if not (defect.get("multi_test_duplicate") or defect.get("duplicate"))
    ]


def export_klarf_text(result: dict, defects: list[dict] | None = None) -> str:
    selected = (
        defects
        if defects is not None
        else [item for item in result.get("defects", []) if item.get("klarf_included", True)]
    )
    lines = [
        "FileVersion 1 1;",
        f"InspectionStationID PUMA9980 SIMULATOR {result.get('inspection', '')};",
        f"LotID {result.get('lot_id', '')};",
        f"WaferID {result.get('wafer_id', '')};",
        f"DeviceID {result.get('device', '')};",
        f"StepID {result.get('step', '')};",
        "DefectRecordSpec 8 DEFECTID XREL YREL XINDEX YINDEX TEST CLASSCODE DSIZE;",
        f"DefectList {len(selected)}",
    ]
    for defect in selected:
        lines.append(
            "{id} {x:.5f} {y:.5f} {die_x} {die_y} {test} {class_code} {size_um:.3f}".format(**defect)
        )
    lines.extend([";", "EndOfFile;"])
    return "\n".join(lines) + "\n"


def import_klarf_text(text: str, matching=None, *, source_path="") -> dict:
    if not isinstance(text, str) or "DefectList" not in text:
        raise ValueError("The selected file does not contain a KLARF DefectList")

    def field(name, default=""):
        match = re.search(rf"(?mi)^\s*{re.escape(name)}\s+([^;]+?)\s*;", text)
        return match.group(1).strip().strip('"') if match else default

    result = {
        "id": uuid4().hex,
        "lot_id": field("LotID", "ImportedLot"),
        "wafer_id": field("WaferID", "ImportedWafer"),
        "device": field("DeviceID"),
        "step": field("StepID"),
        "inspection": "Imported KLARF",
        "status": "Complete",
        "source_format": "KLARF",
        "source_path": source_path,
        "path": source_path,
        "selected_tests": [],
        "defects": [],
    }
    station = field("InspectionStationID")
    if station:
        parts = station.split()
        if len(parts) > 2:
            result["inspection"] = " ".join(parts[2:])

    matching = matching or {}
    for result_key, match_key, label in (("device", "device", "Device"), ("step", "step", "Process Step")):
        actual = result.get(result_key)
        expected = matching.get(match_key)
        if actual and expected and actual != expected:
            raise ValueError(f"KLARF {label} '{actual}' does not match '{expected}'")
    if matching:
        result["recipe_id"] = matching.get("recipe_id") or matching.get("id", "")
        result["inspection"] = matching.get("inspection", result["inspection"])
        result["device"] = result["device"] or matching.get("device", "")
        result["step"] = result["step"] or matching.get("step", "")

    section = re.search(r"(?mis)^\s*DefectList\s+\d+\s*(.*?)^\s*;\s*$", text)
    if section is None:
        raise ValueError("The KLARF DefectList is incomplete")
    tests = []
    spec_match = re.search(r"(?mi)^\s*DefectRecordSpec\s+\d+\s+([^;]+);", text)
    specification = spec_match.group(1).split() if spec_match else [
        "DEFECTID", "XREL", "YREL", "XINDEX", "YINDEX", "TEST", "CLASSCODE", "DSIZE"
    ]

    def token_value(tokens, names, default=None):
        for name in names:
            if name in specification:
                index = specification.index(name)
                if index < len(tokens):
                    return tokens[index]
        return default

    for raw_line in section.group(1).splitlines():
        tokens = raw_line.strip().rstrip(";").split()
        if len(tokens) < 5:
            continue
        try:
            identifier = int(float(token_value(tokens, ("DEFECTID", "ID"), tokens[0])))
            x = float(token_value(tokens, ("XREL", "X", "XPOS"), tokens[1]))
            y = float(token_value(tokens, ("YREL", "Y", "YPOS"), tokens[2]))
            die_x = int(float(token_value(tokens, ("XINDEX", "DIECOL", "DIEX"), tokens[3])))
            die_y = int(float(token_value(tokens, ("YINDEX", "DIEROW", "DIEY"), tokens[4])))
        except ValueError:
            continue
        test = token_value(tokens, ("TEST", "TESTID"), "Imported")
        try:
            class_code = int(float(token_value(tokens, ("CLASSCODE", "CLASSNUMBER", "CLASS"), 0)))
            size_um = float(token_value(tokens, ("DSIZE", "XSIZE", "SIZE"), 0.0))
        except ValueError:
            class_code, size_um = 0, 0.0
        if test not in tests:
            tests.append(test)
        result["defects"].append({
            "id": identifier,
            "x": x,
            "y": y,
            "die_x": die_x,
            "die_y": die_y,
            "test": test,
            "class_code": class_code,
            "size_um": size_um,
            "signal": 0.0,
            "roughbin": 0,
            "venn_id": 0,
            "channel": 1,
            "polarity": "Bright",
            "region_id": "R1",
            "threshold_region": "TR1",
            "adder": True,
            "cluster_id": 0,
            "repeater": False,
            "marked": False,
            "reviewed": False,
            "has_patch_image": False,
            "has_sem_image": False,
            "has_manual_image": False,
        })
    if not result["defects"]:
        raise ValueError("No readable defect records were found in the KLARF")
    result["selected_tests"] = tests
    result["defect_count"] = len(result["defects"])
    result["review_log"] = [f"Imported {len(result['defects'])} defect(s) from KLARF"]
    return result


def apply_review_offset(result: dict, x_offset: float, y_offset: float, *, die_origin=False) -> dict:
    updated = deepcopy(result)
    x_offset = float(x_offset)
    y_offset = float(y_offset)
    for defect in updated.get("defects", []):
        defect["x"] = round(float(defect.get("x", 0.0)) + x_offset, 6)
        defect["y"] = round(float(defect.get("y", 0.0)) + y_offset, 6)
    key = "die_origin_offset" if die_origin else "defect_offset"
    previous = updated.get(key) or {"x": 0.0, "y": 0.0}
    updated[key] = {
        "x": round(float(previous.get("x", 0.0)) + x_offset, 6),
        "y": round(float(previous.get("y", 0.0)) + y_offset, 6),
    }
    updated.setdefault("review_log", []).append(
        f"Applied {'die origin' if die_origin else 'defect'} offset X={x_offset:g}, Y={y_offset:g}"
    )
    return updated


def analyze_optics_modes(site_ids, modes) -> list[dict]:
    sites = sorted(int(value) for value in site_ids)
    analyzed = []
    for index, mode in enumerate(modes):
        item = deepcopy(mode)
        seed = sum(sites) + (index + 1) * 37 + sum(ord(char) for char in str(mode))
        signal = round(80.0 + seed % 170, 2)
        noise = round(8.0 + seed % 31, 2)
        ratio = round(signal / noise, 3)
        item.update({
            "signal": signal,
            "noise": noise,
            "signal_noise": ratio,
            "algo_metric": round(ratio * (1.0 + (seed % 9) / 20.0), 3),
            "site_count": len(sites),
        })
        analyzed.append(item)
    return analyzed


def evaluate_sensitivity_tuning(
    result: dict,
    *,
    test: str,
    regions=None,
    polarity="Both",
    dark_filter="Both",
    threshold=45.0,
) -> dict:
    selected_regions = set(regions or [])
    considered = []
    for defect in result.get("defects", []):
        if test and defect.get("test") != test:
            continue
        if selected_regions and defect.get("region_id") not in selected_regions:
            continue
        die_type = defect.get("die_type", "Primary")
        if polarity == "Dark" and defect.get("polarity") != "Dark":
            continue
        if polarity == "Dark" and dark_filter == "Primary Dark Defects Only" and die_type != "Primary":
            continue
        if polarity == "Dark" and dark_filter == "Secondary-Die Defects Only" and die_type != "Secondary":
            continue
        if polarity == "Primary" and (defect.get("polarity") == "Dark" or die_type != "Primary"):
            continue
        if polarity == "Secondary" and (defect.get("polarity") == "Dark" or die_type != "Secondary"):
            continue
        considered.append(defect)
    detected = [item for item in considered if float(item.get("signal", 0.0)) >= float(threshold)]
    return {
        "considered_ids": [item.get("id") for item in considered],
        "detected_ids": [item.get("id") for item in detected],
        "undetected_ids": [item.get("id") for item in considered if item not in detected],
        "considered": len(considered),
        "detected": len(detected),
        "undetected": len(considered) - len(detected),
        "threshold": float(threshold),
    }


def apply_super_class_scheme(result: dict, scheme: dict) -> dict:
    normalized = {
        name: sorted({int(value) for value in scheme.get(name, [])})
        for name in SUPER_CLASS_NAMES
    }
    reverse = {
        code: name
        for name in SUPER_CLASS_NAMES
        for code in normalized[name]
    }
    updated = deepcopy(result)
    for defect in updated.get("defects", []):
        defect["super_class"] = reverse.get(int(defect.get("class_code", 0)), "Unknown")
    updated["super_class_scheme"] = normalized
    updated.setdefault("review_log", []).append("Applied Super Class grouping scheme")
    return updated


def combine_sensitivity_results(target: dict, source: dict, *, target_test="All", source_test="All") -> dict:
    if not target.get("sensitivity_data") or not source.get("sensitivity_data"):
        raise ValueError("Both source and target must contain Sensitivity Tuner data")
    target_orientation = target.get("wafer_orientation")
    source_orientation = source.get("wafer_orientation")
    if target_orientation and source_orientation and target_orientation != source_orientation:
        raise ValueError("Source and target wafer orientations do not match")
    target_height = target.get("die_height_um")
    source_height = source.get("die_height_um")
    if target_height and source_height and float(target_height) != float(source_height):
        raise ValueError("Source and target die heights do not match")

    combined = deepcopy(target)
    target_defects = [
        deepcopy(item) for item in target.get("defects", [])
        if target_test in ("", "All") or item.get("test") == target_test
    ]
    source_defects = [
        deepcopy(item) for item in source.get("defects", [])
        if source_test in ("", "All") or item.get("test") == source_test
    ]
    next_id = max([int(item.get("id", 0)) for item in target_defects] or [0]) + 1
    for index, defect in enumerate(source_defects):
        defect["id"] = next_id + index
        defect["combined_source_id"] = source.get("id", "")
        defect["combined_source_lot"] = source.get("lot_id", "")
    combined["defects"] = target_defects + source_defects
    combined["defect_count"] = len(combined["defects"])
    combined["combined_for_sensitivity_tuner"] = True
    combined.setdefault("combined_sources", []).append({
        "id": source.get("id", ""),
        "lot_id": source.get("lot_id", ""),
        "wafer_id": source.get("wafer_id", ""),
        "test": source_test,
        "defect_count": len(source_defects),
    })
    combined["sensitivity_summary"] = {
        "all": len(combined["defects"]),
        "original": len(target_defects),
        "imported_source": sum(item["defect_count"] for item in combined["combined_sources"]),
    }
    combined.setdefault("review_log", []).append(
        f"Combined {len(source_defects)} Sensitivity Tuner defect(s) from {source.get('lot_id', '')}"
    )
    return combined


def _test_selected(defect, selected):
    return not selected or selected == "All" or defect.get("test") == selected


def _nearest_defect(defect, candidates, tolerance):
    matches = [
        candidate for candidate in candidates
        if (float(candidate.get("x", 0)) - float(defect.get("x", 0))) ** 2
        + (float(candidate.get("y", 0)) - float(defect.get("y", 0))) ** 2
        <= float(tolerance) ** 2
    ]
    if not matches:
        return None
    return min(
        matches,
        key=lambda candidate: (
            (float(candidate.get("x", 0)) - float(defect.get("x", 0))) ** 2
            + (float(candidate.get("y", 0)) - float(defect.get("y", 0))) ** 2
        ),
    )


def auto_label_result(
    target: dict,
    source: dict,
    *,
    tolerance=0.001,
    source_test="All",
    target_test="All",
    preserve_classified=False,
    preserve_codes=None,
    ignore_source_codes=None,
) -> tuple[dict, int]:
    updated = deepcopy(target)
    preserved = {int(code) for code in (preserve_codes or [])}
    ignored = {int(code) for code in (ignore_source_codes or [])}
    sources = [item for item in source.get("defects", []) if _test_selected(item, source_test)]
    changed = 0
    for defect in updated.get("defects", []):
        if not _test_selected(defect, target_test):
            continue
        target_code = int(defect.get("class_code", 0))
        if (preserve_classified and target_code != 0) or target_code in preserved:
            continue
        match = _nearest_defect(defect, sources, tolerance)
        if match is None or int(match.get("class_code", 0)) in ignored:
            continue
        new_code = int(match.get("class_code", 0))
        if new_code != target_code:
            defect["class_code"] = new_code
            changed += 1
    updated.setdefault("review_log", []).append(
        f"Auto Label imported {changed} classification(s) from {source.get('lot_id', '')}"
    )
    return updated, changed


def merge_result(target: dict, source: dict, *, tolerance=0.001, source_test="All", target_test="All") -> tuple[dict, int]:
    merged = deepcopy(target)
    target_defects = merged.setdefault("defects", [])
    comparable = [item for item in target_defects if _test_selected(item, target_test)]
    next_id = max((int(item.get("id", 0)) for item in target_defects), default=0) + 1
    added = 0
    for source_defect in source.get("defects", []):
        if not _test_selected(source_defect, source_test):
            continue
        match = _nearest_defect(source_defect, comparable, tolerance)
        if match is not None:
            match["class_code"] = int(source_defect.get("class_code", 0))
            continue
        new_defect = deepcopy(source_defect)
        new_defect["id"] = next_id
        next_id += 1
        target_defects.append(new_defect)
        comparable.append(new_defect)
        added += 1
    merged["defect_count"] = len(target_defects)
    merged.setdefault("review_log", []).append(
        f"Merged {added} new defect(s) from {source.get('lot_id', '')}"
    )
    return merged, added


def filtered_result_as(result: dict, defects: list[dict], lot_id: str) -> dict:
    name = str(lot_id).strip()
    if not name:
        raise ValueError("Lot Result name is required")
    if name.lower() == str(result.get("lot_id", "")).strip().lower():
        raise ValueError("The new Lot Result name must differ from the original")
    if not defects:
        raise ValueError("No displayed defects are available to save")
    saved = deepcopy(result)
    saved["id"] = uuid4().hex
    saved["lot_id"] = name
    saved["defects"] = deepcopy(defects)
    saved["defect_count"] = len(saved["defects"])
    saved.pop("review_analysis", None)
    saved.pop("optics_selector", None)
    saved["filtered_from"] = result.get("id", "")
    saved["images"] = "Patch images only"
    saved.setdefault("review_log", []).append(f"Saved filtered lot as {name}")
    return saved

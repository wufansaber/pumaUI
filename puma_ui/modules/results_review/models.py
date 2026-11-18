from __future__ import annotations

from collections import Counter
from copy import deepcopy
import math
import re
from uuid import NAMESPACE_OID, uuid4, uuid5

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
        if rough_bins:
            try:
                roughbin = int(defect.get("roughbin"))
            except (TypeError, ValueError):
                continue
            if roughbin not in rough_bins:
                continue
        if rough_classes and str(defect.get("ido_rough_code", "")) not in rough_classes:
            continue
        if rough_groups and str(defect.get("ido_rough_group", "")) not in rough_groups:
            continue
        if venn_ids:
            try:
                venn_id = int(defect.get("venn_id"))
            except (TypeError, ValueError):
                continue
            if venn_id not in venn_ids:
                continue
        is_duplicate = bool(defect.get("multi_test_duplicate") or defect.get("duplicate"))
        if duplicate_mode == "Duplicates" and not is_duplicate:
            continue
        if duplicate_mode == "Non-Duplicates" and is_duplicate:
            continue
        if channels:
            try:
                channel = int(defect.get("channel"))
            except (TypeError, ValueError):
                continue
            if channel not in channels:
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
        signal = defect.get("signal")
        if signal not in (None, ""):
            try:
                if not minimum_signal <= float(signal) <= maximum_signal:
                    continue
            except (TypeError, ValueError):
                continue
        size = defect.get("size_um")
        if size not in (None, ""):
            try:
                if not minimum_size <= float(size) <= maximum_size:
                    continue
            except (TypeError, ValueError):
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
        "Defect Size": defect.get("size_um"),
        "Intensity": defect.get("signal"),
        "Class Code": defect.get("class_code"),
        "Roughbin": defect.get("roughbin"),
        "Channel": defect.get("channel"),
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
        if enable_nef and bool(defect.get("nuisance")):
            defect["nuisance"] = True
            defect["classification_source"] = "ST-NEF"
            if not keep_nuisance:
                defect["binner_filtered"] = True
                filtered += 1
        if enable_ido and not defect.get("binner_filtered"):
            if rough_code:
                defect["ido_rough_code"] = rough_code
            rough_group = str(ido_classifier.get("rough_group") or "").strip()
            if rough_group:
                defect["ido_rough_group"] = rough_group
            if rough_code or rough_group:
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
    specification = list(result.get("defect_record_spec") or _KLARF_DEFECT_SPEC)
    lines = [
        "FileVersion 1 1;",
        f"InspectionStationID PUMA9980 SIMULATOR {result.get('inspection', '')};",
        f"LotID {result.get('lot_id', '')};",
        f"WaferID {result.get('wafer_id', '')};",
        f"DeviceID {result.get('device', '')};",
        f"StepID {result.get('step', '')};",
        f"DefectRecordSpec {len(specification)} {' '.join(specification)};",
        f"DefectList {len(selected)}",
    ]
    for defect in selected:
        values = [_klarf_export_field(defect, name) for name in specification]
        lines.append(" ".join(_klarf_export_token(value) for value in values))
    lines.extend([";", "EndOfFile;"])
    return "\n".join(lines) + "\n"


def _klarf_export_field(defect, name):
    normalized = str(name).upper()
    current = {
        "DEFECTID": defect.get("id"),
        "XREL": defect.get("xrel", defect.get("x")),
        "YREL": defect.get("yrel", defect.get("y")),
        "XINDEX": defect.get("die_x"),
        "YINDEX": defect.get("die_y"),
        "TEST": defect.get("test"),
        "TESTID": defect.get("test"),
        "CLASSNUMBER": defect.get("class_code"),
        "CLASSCODE": defect.get("class_code"),
        "DSIZE": defect.get("size_um"),
        "ROUGHBINNUMBER": defect.get("roughbin"),
        "FINEBINNUMBER": defect.get("fine_code"),
        "CLUSTERNUMBER": defect.get("cluster_id"),
        "DEFECTAREA": defect.get("area"),
        "XSIZE": defect.get("xsize"),
        "YSIZE": defect.get("ysize"),
    }
    if normalized in current and current[normalized] is not None:
        return current[normalized]
    return defect.get(f"klarf:{name}", 0)


def _klarf_export_token(value):
    if isinstance(value, list):
        return " ".join(_klarf_export_token(item) for item in value)
    if value is None:
        return "0"
    text = str(value)
    if any(character.isspace() for character in text):
        return f'"{text}"'
    return text


_KLARF_TOKEN = re.compile(r'"[^"]*"|;|[^\s;]+')
_KLARF_DEFECT_SPEC = ["DEFECTID", "XREL", "YREL", "XINDEX", "YINDEX", "TEST", "CLASSCODE", "DSIZE"]


def _klarf_records(text: str):
    records = []
    name = None
    tokens = []
    for match in _KLARF_TOKEN.finditer(text):
        token = match.group(0)
        if token == ";":
            if name:
                records.append((name, tokens))
            name = None
            tokens = []
            continue
        if token.startswith('"') and token.endswith('"'):
            token = token[1:-1]
        if name is None:
            name = token
        else:
            tokens.append(token)
    return records


def _klarf_number(tokens, index, default=0.0):
    if index >= len(tokens):
        return default
    try:
        return float(tokens[index])
    except (TypeError, ValueError):
        return default


def _klarf_defect_line_groups(text: str):
    """One group of defect rows for each DefectList. A row may end with ';'."""
    groups = []
    lines = text.splitlines()
    index = 0
    stop_words = {"SummarySpec", "SummaryList", "EndOfFile", "LotStatus", "WaferStatus", "DefectRecordSpec"}
    while index < len(lines):
        if not re.match(r"(?i)^\s*DefectList\b", lines[index]):
            index += 1
            continue
        index += 1
        rows = []
        while index < len(lines):
            raw = lines[index].strip()
            index += 1
            if not raw:
                continue
            finished = raw.endswith(";")
            content = raw[:-1].strip() if finished else raw
            if not content:
                break
            tokens = content.split()
            if tokens[0] in stop_words:
                break
            if len(tokens) == 1 and tokens[0].isdigit() and not rows:
                if finished:
                    break
                continue
            if len(tokens) >= 5:
                rows.append(tokens)
            if finished:
                break
        groups.append(rows)
    return groups


def _klarf_defect_rows(tokens, specification):
    width = len(specification) or 8
    rows = list(tokens)
    if rows and rows[0].isdigit() and len(rows) % width == 1:
        rows = rows[1:]
    if width and len(rows) % width == 0:
        return [rows[index:index + width] for index in range(0, len(rows), width)]
    normalized = [str(name).upper() for name in specification]
    image_at = normalized.index("IMAGECOUNT") if "IMAGECOUNT" in normalized else -1
    if image_at < 0:
        return []
    parsed = []
    cursor = 0
    while cursor + width <= len(rows):
        count_text = rows[cursor + image_at]
        try:
            images = int(float(count_text))
        except ValueError:
            break
        # IMAGELIST itself occupies the declared field. Additional image names
        # may be emitted as extra tokens by some KLARF writers.
        extra = max(images - 1, 0)
        end = cursor + width + extra
        if end > len(rows):
            break
        parsed.append(rows[cursor:end])
        cursor = end
    return parsed


def _klarf_token(row, specification, names, default=None):
    lookup = {str(column).upper(): index for index, column in enumerate(specification)}
    for name in names:
        index = lookup.get(str(name).upper())
        if index is not None and index < len(row):
            return row[index]
    return default


def _klarf_cast_value(value):
    """Keep KLARF values losslessly useful while preserving zero and text."""
    if value is None:
        return None
    if isinstance(value, list):
        return [_klarf_cast_value(item) for item in value]
    text = str(value)
    if not text:
        return ""
    try:
        number = float(text)
    except (TypeError, ValueError):
        return text
    if math.isfinite(number) and number.is_integer() and not any(mark in text.lower() for mark in (".", "e")):
        return int(number)
    return number


def _klarf_record_values(row, specification):
    """Map one row to DefectRecordSpec, including a variable trailing list field."""
    values = {}
    for index, name in enumerate(specification):
        if index >= len(row):
            values[name] = None
            continue
        if index == len(specification) - 1 and len(row) > len(specification):
            values[name] = [_klarf_cast_value(value) for value in row[index:]]
        else:
            values[name] = _klarf_cast_value(row[index])
    return values


def test_collects_sensitivity(test) -> bool:
    runtime = ((test or {}).get("sensitivity") or {}).get("runtime_alignment") or {}
    try:
        return int(runtime.get("collect_vo_sensitive_data") or 0) == 1
    except (TypeError, ValueError):
        return False


def sensitivity_setup_gaps(recipe) -> list:
    """Recipe selections the Sensitivity Tuner manual requires before tuning."""
    recipe = recipe or {}
    missing = []
    alignment = recipe.get("alignment") or {}
    if not alignment.get("sites_defined") and not alignment.get("site_coordinates"):
        missing.append("Alignment Sites")
    tests = [
        test for test in (recipe.get("tests") or [])
        if isinstance(test, dict) and test.get("mode") != "No Test"
    ]
    if not tests:
        return missing + ["Polarization Selection", "Care Areas", "Light Training", "Fourier Filter", "Inspection Algorithm"]
    if not any((test.get("inspection_optics") or {}).get("incident_polarization") for test in tests):
        missing.append("Polarization Selection")
    if not any((test.get("care_areas") or {}).get("groups") for test in tests):
        missing.append("Care Areas")
    if not any(test.get("light_trained") for test in tests):
        missing.append("Light Training")
    if not any(
        test.get("fourier_trained")
        or any(channel.get("use_fourier_filter") for channel in (test.get("channels") or []))
        for test in tests
    ):
        missing.append("Fourier Filter")
    if not any(
        (
            ((test.get("sensitivity") or {}).get("regions") or {})
            or test.get("algorithm")
        )
        for test in tests
    ):
        missing.append("Inspection Algorithm")
    return missing


def sensitivity_test_names(recipe) -> list:
    names = []
    for test in (recipe or {}).get("tests") or []:
        if test_collects_sensitivity(test) and test.get("name") and test["name"] not in names:
            names.append(test["name"])
    return names


def apply_collected_sensitivity(result: dict, recipe) -> dict:
    """Mark a result as Sensitivity Tuner data when the recipe collects it."""
    names = sensitivity_test_names(recipe)
    if not names:
        return result
    updated = deepcopy(result)
    updated["sensitivity_data"] = True
    updated["sensitivity_data_mode"] = updated.get("sensitivity_data_mode") or "Sensitivity Tuner Data"
    updated["sensitivity_data_tests"] = names
    return updated


def _klarf_sensitivity_test(name: str, orientation: str) -> dict:
    return {
        "name": str(name),
        "mode": "Array",
        "orientation": orientation,
        "status": "Valid",
        "algorithm": "HLAT",
        "light_trained": True,
        "fourier_trained": True,
        "inspection_optics": {
            "pixel_size": "SL815",
            "incidence_angle": "Oblique",
            "incident_polarization": "P-POL",
            "focus_offset": 0,
        },
        "channels": [
            {
                "name": "1 (Left)",
                "enabled": True,
                "polarization": "S",
                "use_fourier_filter": True,
            },
            {
                "name": "2 (Right)",
                "enabled": True,
                "polarization": "S",
                "use_fourier_filter": True,
            },
        ],
        "care_areas": {
            "groups": [
                {
                    "name": "Full Die",
                    "kind": "DCA",
                    "enabled": True,
                    "areas": [[0.05, 0.05, 0.90, 0.90]],
                }
            ]
        },
        "sensitivity": {
            "runtime_alignment": {
                "enable_new_rta": True,
                "max_y_init_shift": 0,
                "collect_vo_sensitive_data": 1,
            },
            "regions": {
                "Default": {
                    "algorithms": {
                        "HLAT": {"run": True, "threshold": 20},
                    }
                }
            },
        },
    }


def recipe_from_klarf(result: dict) -> dict:
    """Build a review recipe whose device, step, and die layout match a parsed KLARF."""
    device = str(result.get("device") or "ImportedDevice")
    step = str(result.get("step") or "ImportedStep")
    setup = str(result.get("setup_id") or result.get("inspection") or "Imported KLARF")
    pitch_x = float(result.get("die_pitch_x") or 0.0)
    pitch_y = float(result.get("die_pitch_y") or pitch_x or 0.0)
    diameter = float(result.get("wafer_diameter_mm") or 300.0)
    orientation = str(result.get("orientation_mark") or "DOWN").upper()
    degrees = {"UP": 0, "RIGHT": 90, "DOWN": 180, "LEFT": 270}.get(orientation, 180)
    orientation_label = f"{orientation.title()} ({degrees} deg.)"
    tests = [
        _klarf_sensitivity_test(name, orientation_label)
        for name in (result.get("selected_tests") or ["1"])
    ]
    identity = f"klarf:{device}:{step}:{setup}:{pitch_x:g}:{pitch_y:g}:{diameter:g}"
    return {
        "id": uuid5(NAMESPACE_OID, identity).hex,
        "inspection": setup,
        "device": device,
        "step": step,
        "status": "Valid",
        "state": "Sensitivity Tuner recipe generated from the imported KLARF.",
        "recipe_type": "Normal",
        "approval": "Engineering",
        "wafer_orientation": f"{degrees} deg",
        "klarf_setup_id": setup,
        "alignment": {
            "mode": "DF",
            "sites_defined": True,
            "trained": True,
            "aligned": True,
            "status": "Valid",
            "site_coordinates": [[-pitch_x, -pitch_y], [pitch_x, pitch_y]],
        },
        "wafer_properties": {
            "orientation": orientation,
            "diameter": diameter,
            "notch": result.get("orientation_mark_type") or "NOTCH",
        },
        "wafer_map": {
            "die_pattern_defined": True,
            "die_pitch_width": pitch_x,
            "die_pitch_height": pitch_y,
            "die_origin_x": float(result.get("die_origin_x") or 0.0),
            "die_origin_y": float(result.get("die_origin_y") or 0.0),
            "sample_center_x": float(result.get("sample_center_x") or 0.0),
            "sample_center_y": float(result.get("sample_center_y") or 0.0),
            "wafer_diameter": diameter,
            "notch_orientation": degrees,
            "inspected_dies": list(result.get("sample_test_plan") or []),
        },
        "tests": tests,
    }


def upgrade_sensitivity_recipe(existing, generated):
    """Fill a previously saved KLARF recipe with the Sensitivity Tuner setup."""
    if not isinstance(existing, dict):
        return deepcopy(generated)
    if not sensitivity_setup_gaps(existing) and sensitivity_test_names(existing):
        return existing
    updated = deepcopy(existing)
    generated = generated or {}
    updated["alignment"] = deepcopy(generated.get("alignment") or updated.get("alignment") or {})
    updated["tests"] = deepcopy(generated.get("tests") or updated.get("tests") or [])
    updated["status"] = "Valid"
    return updated


def import_klarf_text(text: str, matching=None, *, source_path="") -> dict:
    if not isinstance(text, str) or "DefectList" not in text:
        raise ValueError("The selected file does not contain a KLARF DefectList")
    records = _klarf_records(text)
    header = {
        "lot_id": "ImportedLot",
        "device": "",
        "step": "",
        "setup_id": "",
        "inspection": "Imported KLARF",
        "wafer_diameter_mm": 0.0,
        "orientation_mark": "",
        "orientation_mark_type": "",
        "die_pitch_x": 0.0,
        "die_pitch_y": 0.0,
        "die_origin_x": 0.0,
        "die_origin_y": 0.0,
        "sample_center_x": 0.0,
        "sample_center_y": 0.0,
        "slot": "",
        "sample_test_plan": [],
        "class_lookup": {},
    }
    specification = list(_KLARF_DEFECT_SPEC)
    specifications_seen = []
    defect_groups = _klarf_defect_line_groups(text)
    defect_cursor = 0
    wafers = []
    current = None

    def ensure_wafer():
        nonlocal current
        if current is None:
            current = {"wafer_id": "ImportedWafer", "slot": header.get("slot", ""), "defects": []}
            wafers.append(current)
        return current

    for name, tokens in records:
        if name == "LotID" and tokens:
            header["lot_id"] = tokens[0]
        elif name == "DeviceID" and tokens:
            header["device"] = tokens[0]
        elif name == "StepID" and tokens:
            header["step"] = tokens[0]
        elif name == "SetupID" and tokens:
            header["setup_id"] = tokens[0]
        elif name == "InspectionStationID" and len(tokens) > 2:
            header["inspection"] = " ".join(tokens[2:])
        elif name == "SampleSize" and tokens:
            diameter = tokens[-1]
            try:
                header["wafer_diameter_mm"] = float(diameter)
            except ValueError:
                pass
        elif name == "DiePitch" and tokens:
            header["die_pitch_x"] = _klarf_number(tokens, 0)
            header["die_pitch_y"] = _klarf_number(tokens, 1, header["die_pitch_x"])
        elif name == "DieOrigin" and tokens:
            header["die_origin_x"] = _klarf_number(tokens, 0)
            header["die_origin_y"] = _klarf_number(tokens, 1)
        elif name == "SampleCenterLocation" and tokens:
            header["sample_center_x"] = _klarf_number(tokens, 0)
            header["sample_center_y"] = _klarf_number(tokens, 1)
        elif name == "OrientationMarkLocation" and tokens:
            header["orientation_mark"] = tokens[0]
        elif name == "SampleOrientationMarkType" and tokens:
            header["orientation_mark_type"] = tokens[0]
        elif name == "Slot" and tokens:
            header["slot"] = tokens[0]
            if current is not None:
                current["slot"] = tokens[0]
        elif name == "WaferID" and tokens:
            current = {"wafer_id": tokens[0], "slot": header.get("slot", ""), "defects": []}
            wafers.append(current)
        elif name == "SampleTestPlan" and len(tokens) >= 3:
            pairs = tokens[1:] if tokens[0].lstrip("-").isdigit() and len(tokens) % 2 == 1 else tokens
            dies = []
            for index in range(0, len(pairs) - 1, 2):
                try:
                    dies.append([int(float(pairs[index])), int(float(pairs[index + 1]))])
                except ValueError:
                    continue
            header["sample_test_plan"] = dies
        elif name == "ClassLookup" and len(tokens) >= 3:
            values = tokens[1:] if tokens[0].isdigit() else tokens
            lookup = {}
            for index in range(0, len(values) - 1, 2):
                try:
                    lookup[int(float(values[index]))] = values[index + 1]
                except ValueError:
                    continue
            header["class_lookup"] = lookup
        elif name == "DefectRecordSpec" and len(tokens) > 1:
            declared = tokens[1:] if tokens[0].isdigit() else tokens
            specification = [str(column) for column in declared]
            for column in specification:
                if column not in specifications_seen:
                    specifications_seen.append(column)
        elif name == "DefectList":
            wafer = ensure_wafer()
            rows = _klarf_defect_rows(tokens, specification)
            if not rows and defect_cursor < len(defect_groups):
                rows = defect_groups[defect_cursor]
            defect_cursor += 1
            for row in rows:
                defect = _klarf_defect(row, specification, header)
                if defect is not None:
                    defect["wafer_id"] = wafer["wafer_id"]
                    wafer["defects"].append(defect)
    defects = [defect for wafer in wafers for defect in wafer["defects"]]
    if not defects:
        raise ValueError("No readable defect records were found in the KLARF")
    if not float(header.get("wafer_diameter_mm") or 0.0) and header.get("die_pitch_x") and header.get("die_pitch_y"):
        radius = max(
            [math.hypot(float(defect.get("x_um") or 0.0), float(defect.get("y_um") or 0.0)) for defect in defects]
            or [1.0]
        ) or 1.0
        for defect in defects:
            defect["x"] = float(defect.get("x_um") or 0.0) / radius
            defect["y"] = float(defect.get("y_um") or 0.0) / radius
    tests = []
    for defect in defects:
        if defect["test"] not in tests:
            tests.append(defect["test"])
    wafer_ids = [wafer["wafer_id"] for wafer in wafers] or ["ImportedWafer"]
    result = {
        "id": uuid4().hex,
        "lot_id": header["lot_id"],
        "wafer_id": wafer_ids[0],
        "wafer_ids": wafer_ids,
        "device": header["device"],
        "step": header["step"],
        "setup_id": header["setup_id"],
        "inspection": header["setup_id"] or header["inspection"],
        "status": "Complete",
        "source_format": "KLARF",
        "source_path": source_path,
        "path": source_path,
        "selected_tests": tests,
        "defects": defects,
        "defect_count": len(defects),
        "defect_record_spec": list(specifications_seen or specification),
        "source_defect_columns": [
            {"key": f"klarf:{name}", "label": name, "source": "KLARF"}
            for name in (specifications_seen or specification)
            if str(name).upper() != "DEFECTID"
        ],
        "wafer_diameter_mm": header["wafer_diameter_mm"],
        "orientation_mark": header["orientation_mark"],
        "orientation_mark_type": header["orientation_mark_type"],
        "wafer_orientation": {"UP": 0, "RIGHT": 90, "DOWN": 180, "LEFT": 270}.get(
            str(header["orientation_mark"]).upper()
        ),
        "die_pitch_x": header["die_pitch_x"],
        "die_pitch_y": header["die_pitch_y"],
        "die_origin_x": header["die_origin_x"],
        "die_origin_y": header["die_origin_y"],
        "sample_center_x": header["sample_center_x"],
        "sample_center_y": header["sample_center_y"],
        "slot": header["slot"],
        "sample_test_plan": header["sample_test_plan"],
        "class_lookup": header["class_lookup"],
        "review_log": [f"Imported {len(defects)} defect(s) from KLARF"],
    }
    return apply_klarf_match(result, matching)


def _klarf_defect(row, specification, header):
    source_values = _klarf_record_values(row, specification)

    def value(names, default=None):
        return _klarf_token(row, specification, names, default)

    try:
        identifier = int(float(value(("DEFECTID", "ID"), row[0])))
        xrel = float(value(("XREL", "X", "XPOS"), row[1] if len(row) > 1 else 0))
        yrel = float(value(("YREL", "Y", "YPOS"), row[2] if len(row) > 2 else 0))
        die_x = int(float(value(("XINDEX", "DIECOL", "DIEX"), row[3] if len(row) > 3 else 0)))
        die_y = int(float(value(("YINDEX", "DIEROW", "DIEY"), row[4] if len(row) > 4 else 0)))
    except (TypeError, ValueError, IndexError):
        return None
    test_value = value(("TEST", "TESTID"), None)
    test = str(test_value) if test_value not in (None, "") else ""
    try:
        class_code = int(float(value(("CLASSNUMBER", "CLASSCODE", "CLASS"), 0) or 0))
    except (TypeError, ValueError):
        class_code = 0
    def optional_int(names):
        raw = value(names, None)
        if raw in (None, ""):
            return None
        try:
            return int(float(raw))
        except (TypeError, ValueError):
            return None

    size_um = None
    raw_size = value(("DSIZE", "XSIZE", "SIZE"), None)
    if raw_size not in (None, ""):
        try:
            size_um = float(raw_size)
        except (TypeError, ValueError):
            pass
    roughbin = optional_int(("ROUGHBINNUMBER", "ROUGHBIN"))
    cluster_id = optional_int(("CLUSTERNUMBER", "CLUSTER"))
    fine_code = optional_int(("FINEBINNUMBER", "FINEBIN"))
    try:
        image_count = int(float(value(("IMAGECOUNT",), 0) or 0))
    except (TypeError, ValueError):
        image_count = 0

    def optional_float(names):
        raw = value(names, None)
        if raw in (None, ""):
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    defect_area = optional_float(("DEFECTAREA", "AREA"))
    xsize = optional_float(("XSIZE",))
    ysize = optional_float(("YSIZE",))
    signal = optional_float(("INTENSITY", "SIGNAL", "PRIMARYCHINTENSITY"))
    spec_names = {str(item).upper() for item in (specification or [])}
    channel = None
    if spec_names.intersection({"CHANNEL", "CHANNELID", "PRIMARYCHANNEL"}):
        try:
            channel = int(float(value(("CHANNEL", "CHANNELID", "PRIMARYCHANNEL"), 0)))
        except (TypeError, ValueError):
            channel = None
    polarity = None
    if spec_names.intersection({"POLARITY", "POLAR"}):
        polarity = str(value(("POLARITY", "POLAR"), "") or "") or None
    pitch_x = float(header.get("die_pitch_x") or 0.0)
    pitch_y = float(header.get("die_pitch_y") or 0.0)
    x_um = xrel
    y_um = yrel
    x = xrel
    y = yrel
    if pitch_x and pitch_y:
        x_um = (
            die_x * pitch_x
            + xrel
            + float(header.get("die_origin_x") or 0.0)
            - float(header.get("sample_center_x") or 0.0)
        )
        y_um = (
            die_y * pitch_y
            + yrel
            + float(header.get("die_origin_y") or 0.0)
            - float(header.get("sample_center_y") or 0.0)
        )
        diameter = float(header.get("wafer_diameter_mm") or 0.0)
        if diameter > 0:
            radius = diameter * 500.0
            x = x_um / radius
            y = y_um / radius
        else:
            x = x_um
            y = y_um
    defect = {
        "id": identifier,
        "x": x,
        "y": y,
        "xrel": xrel,
        "yrel": yrel,
        "x_um": x_um,
        "y_um": y_um,
        "die_x": die_x,
        "die_y": die_y,
        "test": test,
        "class_code": class_code,
        "manual_class": class_code,
        "size_um": size_um,
        "area": defect_area,
        "xsize": xsize,
        "ysize": ysize,
        "signal": signal,
        "roughbin": roughbin,
        "fine_code": fine_code,
        "venn_id": None,
        "channel": channel,
        "polarity": polarity,
        "region_id": None,
        "threshold_region": None,
        "adder": None,
        "cluster_id": cluster_id,
        "repeater": None,
        "marked": False,
        "reviewed": False,
        "sampled": bool(value(("REVIEWSAMPLE",), 0) not in (None, "0", 0)),
        "has_patch_image": image_count > 0,
        "has_sem_image": False,
        "has_manual_image": False,
    }
    for name, raw in source_values.items():
        defect[f"klarf:{name}"] = raw
    defect["klarf_fields"] = source_values
    return defect


def apply_klarf_match(result: dict, matching=None) -> dict:
    updated = deepcopy(result)
    matching = matching or {}
    for result_key, match_key, label in (("device", "device", "Device"), ("step", "step", "Process Step")):
        actual = updated.get(result_key)
        expected = matching.get(match_key)
        if actual and expected and str(actual) != str(expected):
            raise ValueError(f"KLARF {label} '{actual}' does not match '{expected}'")
    layout = matching.get("wafer_map") or {}
    klarf_pitch = float(updated.get("die_pitch_x") or 0.0)
    recipe_pitch = float(layout.get("die_pitch_width") or 0.0)
    if klarf_pitch and recipe_pitch and abs(klarf_pitch - recipe_pitch) > max(1.0, abs(klarf_pitch) * 0.001):
        raise ValueError(f"KLARF die pitch '{klarf_pitch:g}' does not match '{recipe_pitch:g}'")
    klarf_diameter = float(updated.get("wafer_diameter_mm") or 0.0)
    recipe_diameter = float(layout.get("wafer_diameter") or (matching.get("wafer_properties") or {}).get("diameter") or 0.0)
    if klarf_diameter and recipe_diameter and abs(klarf_diameter - recipe_diameter) > 1.0:
        raise ValueError(
            f"KLARF wafer diameter '{klarf_diameter:g} mm' does not match '{recipe_diameter:g} mm'"
        )
    if matching:
        updated["recipe_id"] = matching.get("recipe_id") or matching.get("id", "")
        updated["inspection"] = matching.get("inspection", updated.get("inspection"))
        updated["device"] = updated.get("device") or matching.get("device", "")
        updated["step"] = updated.get("step") or matching.get("step", "")
        if sensitivity_test_names(matching):
            collected = apply_collected_sensitivity(updated, matching)
            updated["sensitivity_data"] = collected["sensitivity_data"]
            updated["sensitivity_data_mode"] = collected["sensitivity_data_mode"]
            updated["sensitivity_data_tests"] = collected["sensitivity_data_tests"]
    return updated


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


def analyze_optics_modes(site_ids, modes, defects=None) -> list[dict]:
    sites = sorted(int(value) for value in site_ids)
    selected = [
        defect for defect in (defects or [])
        if int(defect.get("id", -1)) in set(sites)
    ]
    analyzed = []
    for mode in modes:
        item = deepcopy(mode)
        signals = [
            float(defect["signal"]) for defect in selected
            if isinstance(defect.get("signal"), (int, float))
        ]
        noises = [
            float(defect.get("noise", defect.get("hlatcf_noise")))
            for defect in selected
            if isinstance(defect.get("noise", defect.get("hlatcf_noise")), (int, float))
        ]
        metrics = [
            float(defect["algo_metric"]) for defect in selected
            if isinstance(defect.get("algo_metric"), (int, float))
        ]
        signal = round(sum(signals) / len(signals), 3) if signals else None
        noise = round(sum(noises) / len(noises), 3) if noises else None
        ratio = round(signal / noise, 3) if signal is not None and noise not in (None, 0) else None
        item.update({
            "signal": signal,
            "noise": noise,
            "signal_noise": ratio,
            "algo_metric": round(sum(metrics) / len(metrics), 3) if metrics else None,
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
        signal = defect.get("signal")
        if not isinstance(signal, (int, float)) or isinstance(signal, bool):
            continue
        considered.append(defect)
    detected = [item for item in considered if float(item["signal"]) >= float(threshold)]
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
    combined["source_defect_columns"] = _combined_source_columns(target, source)
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
    merged["source_defect_columns"] = _combined_source_columns(target, source)
    merged.setdefault("review_log", []).append(
        f"Merged {added} new defect(s) from {source.get('lot_id', '')}"
    )
    return merged, added


def _combined_source_columns(*results):
    columns = []
    seen = set()
    for result in results:
        for column in (result or {}).get("source_defect_columns") or []:
            key = str(column.get("key") or "")
            if not key or key in seen:
                continue
            columns.append(deepcopy(column))
            seen.add(key)
    return columns


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

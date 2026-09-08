from __future__ import annotations

from copy import deepcopy
import math
import xml.etree.ElementTree as ET
from uuid import uuid4


SCALE_GROUPS = ("Small", "Medium", "Large", "Tall", "Dim", "Planar")
SCALE_COLORS = {
    "Small": "#173bba",
    "Medium": "#ff8a00",
    "Large": "#00bfc4",
    "Tall": "#17752a",
    "Dim": "#9a159d",
    "Planar": "#c9bd55",
    "None": "#d91645",
}


def default_sizing_recipe() -> dict:
    return {
        "sizing_enabled": True,
        "collect_sizing_data": True,
        "scale_factors": {
            "Small": 0.60,
            "Medium": 0.85,
            "Large": 0.50,
            "Tall": 1.90,
            "Dim": 1.40,
            "Planar": 1.00,
        },
        "cut_lines": {
            "Small": 13.0,
            "Large": 17.0,
            "Very Large": 21.0,
            "Tall": 1000.0,
            "Dim": 400.0,
            "Planar": 196.0,
        },
    }


def normalized_sizing_recipe(value=None) -> dict:
    result = default_sizing_recipe()
    if isinstance(value, dict):
        result["sizing_enabled"] = bool(value.get("sizing_enabled", True))
        result["collect_sizing_data"] = bool(value.get("collect_sizing_data", True))
        for section in ("scale_factors", "cut_lines"):
            incoming = value.get(section)
            if isinstance(incoming, dict):
                result[section].update(incoming)
    for name in SCALE_GROUPS:
        try:
            result["scale_factors"][name] = max(0.001, min(1000.0, float(result["scale_factors"][name])))
        except (TypeError, ValueError):
            result["scale_factors"][name] = default_sizing_recipe()["scale_factors"][name]
    for name, default in default_sizing_recipe()["cut_lines"].items():
        try:
            result["cut_lines"][name] = max(0.0, min(1000000.0, float(result["cut_lines"][name])))
        except (TypeError, ValueError):
            result["cut_lines"][name] = default
    return result


def validate_sizing_recipe(value) -> list[str]:
    recipe = normalized_sizing_recipe(value)
    errors = []
    cuts = recipe["cut_lines"]
    if not cuts["Small"] < cuts["Large"] < cuts["Very Large"]:
        errors.append("Size cut lines must increase from Small to Large to Very Large")
    return errors


def default_sizing_state() -> dict:
    return {
        "recipe": default_sizing_recipe(),
        "defect_sets": [],
        "maps": [],
        "active_map_id": "",
        "show_nonzero_only": True,
        "use_reference_computed": False,
        "legend_position": "Right",
        "highlight_group": "All",
        "histogram": {"kind": "Size", "show_cdf": False, "show_out_of_graph": False},
        "status": "Ready",
    }


def normalized_sizing_state(value=None) -> dict:
    result = default_sizing_state()
    if isinstance(value, dict):
        for key in result:
            if key in value:
                result[key] = deepcopy(value[key])
    result["recipe"] = normalized_sizing_recipe(result.get("recipe"))
    result["defect_sets"] = [deepcopy(item) for item in result.get("defect_sets", []) if isinstance(item, dict)]
    result["maps"] = [deepcopy(item) for item in result.get("maps", []) if isinstance(item, dict)]
    valid_sets = {item.get("id") for item in result["defect_sets"]}
    result["maps"] = [
        item for item in result["maps"]
        if item.get("target_set_id") in valid_sets and item.get("reference_set_id") in valid_sets
    ]
    valid_maps = {item.get("id") for item in result["maps"]}
    if result.get("active_map_id") not in valid_maps:
        result["active_map_id"] = result["maps"][-1]["id"] if result["maps"] else ""
    result["legend_position"] = result["legend_position"] if result["legend_position"] in {"Left", "Top", "Right", "Bottom"} else "Right"
    result["highlight_group"] = result["highlight_group"] if result["highlight_group"] in {"All", *SCALE_GROUPS} else "All"
    histogram = result.get("histogram") if isinstance(result.get("histogram"), dict) else {}
    result["histogram"] = {
        "kind": histogram.get("kind") if histogram.get("kind") in {"Special Case", "Size", "Planar"} else "Size",
        "show_cdf": bool(histogram.get("show_cdf", False)),
        "show_out_of_graph": bool(histogram.get("show_out_of_graph", False)),
    }
    return result


def _scale_group(defect: dict, index: int) -> str:
    explicit = str(defect.get("sizing_scale_group", defect.get("scale_group", ""))).title()
    if explicit in SCALE_GROUPS:
        return explicit
    signal = float(defect.get("signal", 0.0))
    size = float(defect.get("size_um", defect.get("computed_size_um", 0.0)))
    if defect.get("polarity") == "Dark" and signal < 80:
        return "Dim"
    if float(defect.get("aspect_ratio", 1.0)) > 2.0:
        return "Tall"
    if float(defect.get("planarity", 0.0)) > 0.7:
        return "Planar"
    if size < 0.8:
        return "Small"
    if size > 4.0:
        return "Large"
    return "Medium" if index % 5 else "Planar"


def defect_set_from_result(result: dict, *, name="", wafer_id="", test="") -> dict:
    defects = []
    selected_wafer = wafer_id or str(result.get("wafer_id", ""))
    for index, source in enumerate(result.get("defects", [])):
        if test and test != "All" and source.get("test") != test:
            continue
        raw = float(source.get("raw_size_um", source.get("size_um", 0.0)))
        defects.append({
            "id": source.get("id", index + 1),
            "source_id": source.get("id", index + 1),
            "source_wafer_id": source.get("source_wafer_id", selected_wafer),
            "x": float(source.get("x", source.get("x_um", 0.0))),
            "y": float(source.get("y", source.get("y_um", 0.0))),
            "raw_size_um": raw,
            "computed_size_um": float(source.get("computed_size_um", source.get("size_um", 0.0))),
            "reference_size_um": max(0.0, float(source.get("reference_size_um", 0.0))),
            "scale_group": _scale_group(source, index),
            "signal": float(source.get("signal", 0.0)),
            "planarity": float(source.get("planarity", (index % 10) / 10.0)),
            "aspect_ratio": float(source.get("aspect_ratio", 1.0 + (index % 4) / 2.0)),
            "test": source.get("test", test or "Test 1"),
        })
    set_name = name.strip() or f"{result.get('lot_id', 'Lot')} : {selected_wafer or 'Wafer'}"
    return {
        "id": uuid4().hex,
        "name": set_name,
        "kind": "Lot Result",
        "source_id": result.get("id", ""),
        "source_path": result.get("path", ""),
        "lot_id": result.get("lot_id", ""),
        "wafer_id": selected_wafer,
        "test": test or "All",
        "saved": False,
        "defects": defects,
    }


def defect_set_from_klarf_result(result: dict, *, name="", size_field="dSize", class_multiplier=0.1) -> dict:
    defect_set = defect_set_from_result(result, name=name or "KLARF Reference")
    defect_set.update({"kind": "KLARF", "source_path": result.get("source_path", result.get("path", ""))})
    use_class = str(size_field).lower() in {"class code", "manual class", "classcode"}
    for source, defect in zip(result.get("defects", []), defect_set["defects"]):
        reference = float(source.get("class_code", 0)) * float(class_multiplier) if use_class else float(source.get("size_um", 0.0))
        defect["reference_size_um"] = max(0.0, reference)
    return defect_set


def auto_map_for_set(defect_set: dict, *, reference_set: dict | None = None, overlay_radius_um=10.0) -> dict:
    reference_set = reference_set or defect_set
    return {
        "id": uuid4().hex,
        "name": f"{defect_set.get('name', 'Target')} : {reference_set.get('name', 'Reference')}",
        "target_set_id": defect_set.get("id", ""),
        "reference_set_id": reference_set.get("id", ""),
        "overlay_radius_um": max(0.0, float(overlay_radius_um)),
    }


def remove_defect_set(state: dict, defect_set_id: str) -> dict:
    updated = normalized_sizing_state(state)
    updated["defect_sets"] = [item for item in updated["defect_sets"] if item.get("id") != defect_set_id]
    updated["maps"] = [
        item for item in updated["maps"]
        if item.get("target_set_id") != defect_set_id and item.get("reference_set_id") != defect_set_id
    ]
    if updated.get("active_map_id") not in {item.get("id") for item in updated["maps"]}:
        updated["active_map_id"] = updated["maps"][-1]["id"] if updated["maps"] else ""
    return updated


def apply_sizing_recipe(defect_set: dict, recipe: dict) -> dict:
    updated = deepcopy(defect_set)
    normalized = normalized_sizing_recipe(recipe)
    for defect in updated.get("defects", []):
        group = defect.get("scale_group") if defect.get("scale_group") in SCALE_GROUPS else "Small"
        factor = normalized["scale_factors"][group]
        defect["computed_size_um"] = round(max(0.0, float(defect.get("raw_size_um", 0.0)) * factor), 4)
    return updated


def _find_set(state: dict, identifier: str) -> dict | None:
    return next((item for item in state.get("defect_sets", []) if item.get("id") == identifier), None)


def active_map(state: dict) -> dict | None:
    return next((item for item in state.get("maps", []) if item.get("id") == state.get("active_map_id")), None)


def scatter_points(state: dict, map_id="") -> list[dict]:
    normalized = normalized_sizing_state(state)
    mapping = next((item for item in normalized["maps"] if item.get("id") == (map_id or normalized["active_map_id"])), None)
    if not mapping:
        return []
    target = _find_set(normalized, mapping.get("target_set_id"))
    reference = _find_set(normalized, mapping.get("reference_set_id"))
    if not target or not reference:
        return []
    target = apply_sizing_recipe(target, normalized["recipe"])
    radius = float(mapping.get("overlay_radius_um", 10.0))
    points = []
    same_set = target.get("id") == reference.get("id")
    for defect in target.get("defects", []):
        candidates = reference.get("defects", [])
        if same_set:
            match = next((item for item in candidates if item.get("id") == defect.get("id")), None)
        else:
            match = min(
                candidates,
                key=lambda item: math.hypot(float(item.get("x", 0.0)) - float(defect.get("x", 0.0)), float(item.get("y", 0.0)) - float(defect.get("y", 0.0))),
                default=None,
            )
            if match is not None:
                distance = math.hypot(float(match.get("x", 0.0)) - float(defect.get("x", 0.0)), float(match.get("y", 0.0)) - float(defect.get("y", 0.0)))
                if distance > radius:
                    match = None
        if match is None:
            continue
        reference_size = float(match.get("computed_size_um", 0.0)) if normalized["use_reference_computed"] else float(match.get("reference_size_um", 0.0))
        if normalized["show_nonzero_only"] and reference_size <= 0:
            continue
        points.append({
            "id": defect.get("id"),
            "target_id": defect.get("id"),
            "reference_id": match.get("id"),
            "reference_size_um": reference_size,
            "computed_size_um": float(defect.get("computed_size_um", 0.0)),
            "scale_group": defect.get("scale_group", "None"),
            "x": defect.get("x", 0.0),
            "y": defect.get("y", 0.0),
        })
    return points


def scatter_statistics(points: list[dict], tolerance_um=0.2) -> dict:
    shown = len(points)
    within = sum(
        1 for item in points
        if abs(float(item.get("computed_size_um", 0.0)) - float(item.get("reference_size_um", 0.0))) <= float(tolerance_um)
    )
    return {"overlayed": shown, "shown": shown, "within_spec": within, "within_spec_percent": round(100.0 * within / shown, 1) if shown else 0.0}


def set_reference_size(state: dict, defect_set_id: str, defect_id, size_um: float) -> dict:
    size = float(size_um)
    if size < 0:
        raise ValueError("Reference size cannot be negative")
    updated = normalized_sizing_state(state)
    defect_set = _find_set(updated, defect_set_id)
    if defect_set is None:
        raise ValueError("Defect Set was not found")
    defect = next((item for item in defect_set.get("defects", []) if str(item.get("id")) == str(defect_id)), None)
    if defect is None:
        raise ValueError("Defect ID was not found")
    defect["reference_size_um"] = size
    defect_set["saved"] = False
    return updated


def import_reference_sizes(state: dict, defect_set_id: str, text: str) -> tuple[dict, dict]:
    updated = normalized_sizing_state(state)
    defect_set = _find_set(updated, defect_set_id)
    if defect_set is None:
        raise ValueError("Defect Set was not found")
    by_id = {str(item.get("id")): item for item in defect_set.get("defects", [])}
    applied = 0
    ignored = 0
    for raw_line in str(text).splitlines():
        values = raw_line.strip().replace(",", "\t").split()
        if len(values) < 2:
            if raw_line.strip():
                ignored += 1
            continue
        try:
            size = float(values[1])
        except ValueError:
            ignored += 1
            continue
        defect = by_id.get(values[0])
        if defect is None or size < 0:
            ignored += 1
            continue
        defect["reference_size_um"] = size
        applied += 1
    if applied:
        defect_set["saved"] = False
    return updated, {"applied": applied, "ignored": ignored}


def transfer_reference_sizes(state: dict, map_id="") -> dict:
    updated = normalized_sizing_state(state)
    mapping = next((item for item in updated["maps"] if item.get("id") == (map_id or updated["active_map_id"])), None)
    if not mapping:
        raise ValueError("Select a map")
    target = _find_set(updated, mapping["target_set_id"])
    reference = _find_set(updated, mapping["reference_set_id"])
    if not target or not reference:
        raise ValueError("Map defect sets are unavailable")
    reference_by_id = {str(item.get("id")): item for item in reference.get("defects", [])}
    paired = scatter_points({**updated, "show_nonzero_only": False}, mapping["id"])
    pairs = {str(item.get("target_id")): str(item.get("reference_id")) for item in paired}
    for defect in target.get("defects", []):
        source = reference_by_id.get(pairs.get(str(defect.get("id")), ""))
        if source:
            defect["reference_size_um"] = float(source.get("reference_size_um", source.get("computed_size_um", 0.0)))
    target["saved"] = False
    return updated


def histogram_values(state: dict, kind="Size", map_id="") -> list[float]:
    normalized = normalized_sizing_state(state)
    points = scatter_points(normalized, map_id)
    mapping = active_map(normalized)
    target = _find_set(normalized, mapping.get("target_set_id")) if mapping else None
    defects = target.get("defects", []) if target else []
    if kind == "Special Case":
        return [float(item.get("signal", 0.0)) for item in defects]
    if kind == "Planar":
        return [float(item.get("planarity", 0.0)) * 1000.0 for item in defects]
    return [float(item.get("computed_size_um", 0.0)) for item in points]


def export_sizing_recipe_xml(recipe: dict, *, name="SizingRecipe") -> str:
    normalized = normalized_sizing_recipe(recipe)
    root = ET.Element("SizingRecipe", {"name": str(name), "version": "9.8.306"})
    general = ET.SubElement(root, "General")
    general.set("enabled", str(normalized["sizing_enabled"]).lower())
    general.set("collectSizingData", str(normalized["collect_sizing_data"]).lower())
    factors = ET.SubElement(root, "ScaleFactors")
    for key in SCALE_GROUPS:
        ET.SubElement(factors, "ScaleFactor", {"name": key, "value": f"{normalized['scale_factors'][key]:g}"})
    cuts = ET.SubElement(root, "CutLines")
    for key, value in normalized["cut_lines"].items():
        ET.SubElement(cuts, "CutLine", {"name": key, "value": f"{value:g}"})
    return ET.tostring(root, encoding="unicode")


def import_sizing_recipe_xml(text: str) -> dict:
    try:
        root = ET.fromstring(str(text))
    except ET.ParseError as exc:
        raise ValueError(f"Invalid sizing recipe XML: {exc}") from exc
    if root.tag != "SizingRecipe":
        raise ValueError("The XML file does not contain a SizingRecipe")
    general = root.find("General")
    values = {
        "sizing_enabled": general is None or general.get("enabled", "true").lower() == "true",
        "collect_sizing_data": general is None or general.get("collectSizingData", "true").lower() == "true",
        "scale_factors": {},
        "cut_lines": {},
    }
    for item in root.findall("./ScaleFactors/ScaleFactor"):
        name = item.get("name", "")
        if name in SCALE_GROUPS:
            try:
                values["scale_factors"][name] = float(item.get("value", ""))
            except ValueError as exc:
                raise ValueError(f"Invalid scale factor for {name}") from exc
    for item in root.findall("./CutLines/CutLine"):
        name = item.get("name", "")
        if name in default_sizing_recipe()["cut_lines"]:
            try:
                values["cut_lines"][name] = float(item.get("value", ""))
            except ValueError as exc:
                raise ValueError(f"Invalid cut line for {name}") from exc
    return normalized_sizing_recipe(values)


def consolidate_lot_results(results: list[dict]) -> tuple[dict, list[dict]]:
    if not results:
        raise ValueError("Select at least one lot result")
    lot_ids = {str(item.get("lot_id", "")) for item in results}
    if len(lot_ids) != 1:
        raise ValueError("All selected results must belong to the same lot")
    consolidated = deepcopy(results[0])
    consolidated["wafer_id"] = str(results[0].get("wafer_id", "W1"))
    consolidated["consolidated_wafers"] = [item.get("wafer_id", "") for item in results]
    consolidated["consolidated_from_ids"] = [item.get("id", "") for item in results]
    merged = []
    transformations = []
    next_id = 1
    for result in results:
        wafer = result.get("wafer_id", "")
        for defect in result.get("defects", []):
            item = deepcopy(defect)
            old_id = item.get("id")
            item["source_wafer_id"] = wafer
            item["source_defect_id"] = old_id
            item["id"] = next_id
            transformations.append({"wafer_id": wafer, "old_id": old_id, "new_id": next_id})
            merged.append(item)
            next_id += 1
    consolidated["defects"] = merged
    consolidated["defect_count"] = len(merged)
    consolidated.setdefault("review_log", []).append(f"SST consolidated {len(results)} wafer result(s)")
    return consolidated, transformations

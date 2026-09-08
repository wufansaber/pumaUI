from __future__ import annotations

import hashlib
import math
import random
import re
from copy import deepcopy
from datetime import datetime
from uuid import uuid4


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _test_names(recipe: dict) -> list[str]:
    return [
        test.get("name", f"Test {index + 1}")
        for index, test in enumerate(recipe.get("tests", []))
        if test.get("mode") != "No Test"
    ]


def _selected_test_states(recipe: dict, selected_names: list[str]) -> list[dict]:
    selected = set(selected_names)
    return [
        test
        for index, test in enumerate(recipe.get("tests", []))
        if test.get("name", f"Test {index + 1}") in selected
        and test.get("mode") != "No Test"
    ]


def default_run_setup(recipe: dict) -> dict:
    tests = _test_names(recipe)
    lot_plan = recipe.get("lot_plan", {})
    repeat_enabled = bool(lot_plan.get("repeat_enabled", lot_plan.get("repeat_test", False)))
    stored_counts = [
        int(value)
        for value in (lot_plan.get("repeat_counts") or {}).values()
        if str(value).isdigit()
    ]
    repeat_count = max(stored_counts or [int(lot_plan.get("repeat_count", 1))])
    return {
        "lot_id": "",
        "wafer_id": "",
        "selected_tests": tests,
        "repeat_test": repeat_enabled,
        "repeat_count": repeat_count if repeat_enabled else 1,
        "unload_wafer_in_repeat_mode": bool(
            lot_plan.get("unload_wafer_in_repeat_mode", False)
        ),
        "lot_plan_protected": bool(lot_plan.get("protect", False)),
        "auto_transfer": bool(lot_plan.get("cache_lot_result", False)),
        "transfer_host": lot_plan.get("transfer_host", ""),
        "transfer_share": lot_plan.get("transfer_share", "ImpactDataTemp"),
        "transfer_tool_type": lot_plan.get("tool_type", "9xxx"),
        "transfer_patches": False,
        "transfer_hi_res": False,
        "instant_review": True,
        "collect_sensitivity_data": False,
        "osts_data": False,
        "backup_lot_result": bool(lot_plan.get("backup_lot_result", False)),
        "overwrite_result_ids": [],
    }


def matching_result_ids(results: list[dict], lot_id: str) -> list[str]:
    target = str(lot_id).strip().lower()
    if not target:
        return []
    return [
        item.get("id", "")
        for item in results
        if str(item.get("lot_id", "")).strip().lower() == target and item.get("id")
    ]


def effective_wafer_defect_limit(recipe: dict, system_default=250000) -> int:
    operations = recipe.get("wafer_post_processing", {}).get("operations", [])
    limits = next((item for item in operations if item.get("name") == "Defect Limits" and item.get("enabled")), None)
    if not limits:
        return int(system_default)
    parameters = limits.get("parameters", {})
    if parameters.get("override_wafer_limit"):
        return max(1, min(100000, int(parameters.get("wafer_maximum_defects", system_default))))
    return int(system_default)


def transfer_prerequisite_errors(
    setup: dict,
    recipe: dict,
    selected_tests: list[str] | None = None,
) -> list[str]:
    """Validate recipe features required by optional image transfers."""
    errors = []
    selected = selected_tests or list(setup.get("selected_tests") or _test_names(recipe))
    tests = _selected_test_states(recipe, selected)
    operations = recipe.get("wafer_post_processing", {}).get("operations", [])
    sampling = next(
        (
            item
            for item in operations
            if item.get("name") == "Sampling" and item.get("enabled")
        ),
        None,
    )
    sampling_parameters = (sampling or {}).get("parameters", {})

    if setup.get("transfer_patches"):
        missing = [
            test.get("name", "Test")
            for test in tests
            if not test.get("save_image_patches")
        ]
        if missing:
            errors.append(
                "Transfer Patches requires Save Image Patches for: "
                + ", ".join(missing)
            )
        if sampling_parameters.get("patch_sampling", "None") == "None":
            errors.append(
                "Transfer Patches requires Wafer Post Processing > Sampling > Patch Sampling"
            )

    if setup.get("transfer_hi_res") and sampling_parameters.get("hi_res_sampling", "None") == "None":
        errors.append(
            "Transfer Hi-Res Images requires Wafer Post Processing > Sampling > Hi-Res Image Sampling"
        )
    return errors


def apply_high_defect_abort(result: dict, limit: int) -> dict:
    if result.get("defect_count", 0) <= limit:
        return result
    result["defects"] = list(result.get("defects", []))[:limit]
    result["defect_count"] = len(result["defects"])
    result["status"] = "High Defect Abort"
    result["completed"] = _now()
    result.setdefault("run_log", []).append({
        "time": _now(),
        "level": "Warning",
        "message": f"Wafer maximum defect count {limit} reached; remaining tests aborted",
    })
    return result


def _defect_value(defect: dict, element: str):
    keys = {
        "Defect Size": "size_um",
        "Class Code": "class_code",
        "Rough Class": "ido_rough_code",
        "Test ID": "test",
        "Cluster ID": "cluster_id",
        "Die X": "die_x",
        "Die Y": "die_y",
        "Intensity": "signal",
        "Region ID": "region_id",
        "Channel": "channel",
    }
    key = keys.get(element.strip(), element.strip().lower().replace(" ", "_"))
    value = defect.get(key)
    if element == "Rough Class" and value in (None, ""):
        value = defect.get("class_code", 0)
    return value


def _comparison_value(text: str):
    value = text.strip().strip("'\"")
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    try:
        return float(value)
    except ValueError:
        return value


def _matches_expression(defect: dict, expression: str) -> bool:
    expression = str(expression or "").strip()
    if not expression or expression.lower() == "all defects":
        return True
    if ";" in expression and all("=" in part for part in expression.split(";") if part.strip()):
        quick = dict(part.strip().split("=", 1) for part in expression.split(";") if part.strip())
        checks = [
            quick.get("Adder", "All") == "All"
            or (quick["Adder"] == "Adders") == bool(defect.get("adder", True)),
            quick.get("Clusters", "All") == "All"
            or (quick["Clusters"] == "Clustered") == bool(defect.get("cluster_id")),
            quick.get("Polarity", "Bright/Dark") in ("Bright/Dark", defect.get("polarity", "Bright")),
            quick.get("Repeaters", "All") == "All"
            or (quick["Repeaters"] == "Repeaters") == bool(defect.get("repeater", False)),
            quick.get("Region", "All") == "All" or defect.get("region_id") in quick.get("Region", "").split(","),
            quick.get("Test", "All") == "All" or defect.get("test") in quick.get("Test", "").split(","),
            quick.get("Threshold Region", "All") == "All"
            or defect.get("threshold_region") in quick.get("Threshold Region", "").split(","),
        ]
        return all(checks)
    or_parts = re.split(r"\s+OR\s+", expression, flags=re.IGNORECASE)
    if len(or_parts) > 1:
        return any(_matches_expression(defect, part.strip(" ()")) for part in or_parts)
    and_parts = re.split(r"\s+AND\s+", expression, flags=re.IGNORECASE)
    if len(and_parts) > 1:
        return all(_matches_expression(defect, part.strip(" ()")) for part in and_parts)
    match = re.match(r"^\(?\s*(.+?)\s+(In Range|!=|>=|<=|=|>|<)\s+(.+?)\s*\)?$", expression, re.IGNORECASE)
    if not match:
        return False
    element, operator, expected_text = match.groups()
    actual = _defect_value(defect, element)
    if operator.lower() == "in range":
        bounds = re.split(r"\s*(?:\.\.|,|to)\s*", expected_text, maxsplit=1, flags=re.IGNORECASE)
        if len(bounds) != 2:
            return False
        try:
            return float(bounds[0]) <= float(actual) <= float(bounds[1])
        except (TypeError, ValueError):
            return False
    expected = _comparison_value(expected_text)
    try:
        left, right = float(actual), float(expected)
    except (TypeError, ValueError):
        left, right = str(actual), str(expected)
    return {
        "=": left == right,
        "!=": left != right,
        ">": left > right,
        ">=": left >= right,
        "<": left < right,
        "<=": left <= right,
    }[operator]


def _spread_sample(candidates: list[dict], count: int, key="size_um") -> list[dict]:
    ordered = sorted(candidates, key=lambda item: (item.get(key, 0), item.get("id", 0)))
    count = max(0, min(int(count), len(ordered)))
    if count >= len(ordered):
        return ordered
    if count <= 1:
        return ordered[:count]
    indexes = {round(index * (len(ordered) - 1) / (count - 1)) for index in range(count)}
    return [ordered[index] for index in sorted(indexes)]


def _round_robin_classes(candidates: list[dict], count: int) -> list[dict]:
    groups = {}
    for defect in candidates:
        groups.setdefault(defect.get("class_code", 0), []).append(defect)
    selected = []
    while len(selected) < count and any(groups.values()):
        for code in sorted(groups, key=str):
            if groups[code] and len(selected) < count:
                selected.append(groups[code].pop(0))
    return selected


def _sample_candidates(candidates: list[dict], method: str, parameters: dict, maximum: int) -> list[dict]:
    maximum = max(0, min(int(maximum), len(candidates)))
    settings = (parameters.get("method_settings") or {}).get(method, {})
    if method == "Diversity":
        count = settings.get("discovery_samples", maximum)
        if settings.get("scheme") == "Production":
            count = int(settings.get("production_bins", 1)) * int(settings.get("average_per_bin", 1))
        return _spread_sample(candidates, min(maximum, int(count)))
    if method == "Proportional":
        return _round_robin_classes(candidates, maximum)
    if method == "Random/Class Code" and settings.get("class_code_enabled"):
        rows = settings.get("class_code_rows") or []
        allowed = {
            str(row.get("code"))
            for row in rows
            if not row.get("all_nonzero") and str(row.get("code", "")).strip()
        }
        all_nonzero = any(row.get("all_nonzero") for row in rows)
        filtered = [
            defect for defect in candidates
            if (all_nonzero and defect.get("class_code", 0) != 0)
            or str(defect.get("class_code", 0)) in allowed
        ]
        return filtered[:min(maximum, int(settings.get("maximum_code_defects", maximum)))]
    if method == "Smart":
        return _spread_sample(candidates, min(maximum, int(settings.get("target_samples", maximum))), "signal")
    if method == "Trigger":
        count = len(candidates)
        lower = float(settings.get("lower_bound", 0))
        upper = float(settings.get("upper_bound", 100))
        zone = "below_sampling" if count < lower else "above_sampling" if count > upper else "within_sampling"
        action = settings.get(zone, "None")
        if action == "None":
            return []
        return _round_robin_classes(candidates, maximum) if action == "Proportional" else candidates[:maximum]
    return candidates[:maximum]


def _precision_sample(candidates: list[dict], parameters: dict, maximum: int) -> list[dict]:
    selected = []
    selected_ids = set()
    overlap = bool(parameters.get("allow_filter_overlap"))
    for rule in parameters.get("precision_rules") or []:
        if not rule.get("enabled", True):
            continue
        population = candidates if overlap or rule.get("back_fill") else [item for item in candidates if item.get("id") not in selected_ids]
        filtered = [item for item in population if _matches_expression(item, rule.get("filter", "All Defects"))]
        method_name = {
            "Random Sampling": "Random/Class Code",
            "Class Code Sampling": "Random/Class Code",
            "Proportional Sampling": "Proportional",
        }.get(rule.get("sampling_method"), "Random/Class Code")
        rule_parameters = {"method_settings": rule.get("sampling_settings") or {}}
        sampled = _sample_candidates(filtered, method_name, rule_parameters, maximum - len(selected))
        for defect in sampled:
            if defect.get("id") not in selected_ids:
                defect.setdefault("precision_rules", []).append(rule.get("name", "Rule"))
                selected.append(defect)
                selected_ids.add(defect.get("id"))
        if len(selected) >= maximum:
            break
    return selected


def _test_list(value) -> list[str]:
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def _venn_position_um(defect: dict) -> tuple[float, float]:
    if defect.get("x_um") is not None and defect.get("y_um") is not None:
        return float(defect["x_um"]), float(defect["y_um"])
    # Simulated results store wafer coordinates normalized to the wafer radius.
    return float(defect.get("x", 0.0)) * 150000.0, float(defect.get("y", 0.0)) * 150000.0


def _venn_groups(parameters: dict) -> list[dict]:
    if parameters.get("enable_multi_test"):
        configured = parameters.get("test_groups") or []
    else:
        configured = [{
            "name": "Group_A",
            "tests": "All Tests",
            "use_default_tolerance": True,
            "inspected_area_mode": parameters.get("inspected_area_mode", "Area of Largest Test"),
            "area_tests": "All Tests",
            "duplicate_mode": parameters.get("duplicate_mode", "Highest Intensity"),
            "test_priority": "",
        }]
    groups = []
    for index, item in enumerate(configured, start=1):
        if not isinstance(item, dict):
            continue
        use_default = bool(item.get("use_default_tolerance", True))
        groups.append({
            "name": str(item.get("name") or f"Group_{index}"),
            "tests": _test_list(item.get("tests") or "All Tests"),
            "tolerance_um": float(
                parameters.get("default_tolerance_um", 5.0)
                if use_default
                else item.get("tolerance_um", 5.0)
            ),
            "inspected_area_mode": item.get(
                "inspected_area_mode",
                parameters.get("inspected_area_mode", "Area of Largest Test"),
            ),
            "area_tests": _test_list(item.get("area_tests", "All Tests")),
            "duplicate_mode": item.get(
                "duplicate_mode",
                parameters.get("duplicate_mode", "Highest Intensity"),
            ),
            "test_priority": _test_list(item.get("test_priority")),
        })
    return groups


def _apply_venn(defects: list[dict], parameters: dict) -> tuple[list[dict], dict, list[dict]]:
    if parameters.get("clear_venn_ids", True):
        for defect in defects:
            defect.pop("venn_id", None)
            defect.pop("union_id", None)
            defect.pop("venn_group", None)
            defect.pop("venn_duplicate_ids", None)
            defect.pop("multi_test_duplicate", None)
            defect.pop("duplicate", None)
            defect.pop("duplicate_of", None)

    removed_indexes = set()
    duplicate_clusters = 0
    group_reports = []
    next_venn_id = 1
    for group in _venn_groups(parameters):
        all_tests = "All Tests" in group["tests"]
        candidate_indexes = [
            index for index, defect in enumerate(defects)
            if index not in removed_indexes
            and (all_tests or str(defect.get("test", "")) in group["tests"])
        ]
        pending = set(candidate_indexes)
        group_removed = 0
        while pending:
            seed = min(pending)
            pending.remove(seed)
            cluster = {seed}
            frontier = [seed]
            while frontier:
                current = frontier.pop()
                current_x, current_y = _venn_position_um(defects[current])
                current_test = str(defects[current].get("test", ""))
                matches = []
                for other in pending:
                    if str(defects[other].get("test", "")) == current_test:
                        continue
                    other_x, other_y = _venn_position_um(defects[other])
                    if math.hypot(other_x - current_x, other_y - current_y) <= group["tolerance_um"]:
                        matches.append(other)
                for other in matches:
                    pending.remove(other)
                    cluster.add(other)
                    frontier.append(other)
            if len(cluster) < 2 or len({defects[index].get("test") for index in cluster}) < 2:
                continue
            if group["duplicate_mode"] == "Highest Prioritized Test ID":
                priority = {test: rank for rank, test in enumerate(group["test_priority"])}
                winner = min(
                    cluster,
                    key=lambda index: (
                        priority.get(str(defects[index].get("test", "")), len(priority)),
                        -float(defects[index].get("signal", 0.0)),
                        str(defects[index].get("id", index)),
                    ),
                )
            else:
                winner = max(
                    cluster,
                    key=lambda index: (
                        float(defects[index].get("signal", 0.0)),
                        -index,
                    ),
                )
            losers = cluster - {winner}
            removed_indexes.update(losers)
            group_removed += len(losers)
            duplicate_clusters += 1
            defects[winner]["venn_id"] = next_venn_id
            defects[winner]["union_id"] = next_venn_id
            defects[winner]["venn_group"] = group["name"]
            defects[winner]["multi_test_duplicate"] = False
            defects[winner]["duplicate"] = False
            defects[winner]["venn_duplicate_ids"] = [
                defects[index].get("id", index) for index in sorted(losers)
            ]
            winner_id = defects[winner].get("id", winner)
            for index in losers:
                defects[index]["venn_id"] = next_venn_id
                defects[index]["union_id"] = next_venn_id
                defects[index]["venn_group"] = group["name"]
                defects[index]["multi_test_duplicate"] = True
                defects[index]["duplicate"] = True
                defects[index]["duplicate_of"] = winner_id
                defects[index]["klarf_included"] = False
            next_venn_id += 1
        group_reports.append({
            "name": group["name"],
            "tolerance_um": group["tolerance_um"],
            "inspected_area_mode": group["inspected_area_mode"],
            "area_tests": group["area_tests"],
            "duplicate_mode": group["duplicate_mode"],
            "test_priority": group["test_priority"],
            "duplicates_removed": group_removed,
        })
    processed = [defect for index, defect in enumerate(defects) if index not in removed_indexes]
    duplicates = [defect for index, defect in enumerate(defects) if index in removed_indexes]
    return processed, {
        "input_count": len(defects),
        "output_count": len(processed),
        "duplicates_removed": len(removed_indexes),
        "duplicate_clusters": duplicate_clusters,
        "groups": group_reports,
        "cleared_existing_ids": bool(parameters.get("clear_venn_ids", True)),
    }, duplicates


def _apply_clustering(defects: list[dict], parameters: dict) -> dict:
    minimum = max(2, int(parameters.get("minimum_defects", 2)))
    auto = bool(parameters.get("auto_clustering", True))
    if auto:
        threshold = max(100.0, min(5000.0, 7500.0 / math.sqrt(max(1, len(defects)))))
    else:
        threshold = float(parameters.get("distance_threshold_um", 0.0))
    multiplier = max(1, min(5, int(parameters.get("second_pass_multiplier", 3))))
    each_test = parameters.get("cluster_within", "All Tests") == "Each Test"
    for defect in defects:
        defect["cluster_id"] = 0

    populations = {}
    for index, defect in enumerate(defects):
        key = str(defect.get("test", "")) if each_test else "All Tests"
        populations.setdefault(key, []).append(index)

    components = []
    for population_name, indexes in populations.items():
        if not indexes or threshold <= 0:
            continue
        parent = {index: index for index in indexes}

        def find(index):
            while parent[index] != index:
                parent[index] = parent[parent[index]]
                index = parent[index]
            return index

        def union(left, right):
            left_root, right_root = find(left), find(right)
            if left_root != right_root:
                parent[right_root] = left_root

        cells = {}
        for index in indexes:
            x, y = _venn_position_um(defects[index])
            cell = (math.floor(x / threshold), math.floor(y / threshold))
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for other in cells.get((cell[0] + dx, cell[1] + dy), []):
                        other_x, other_y = _venn_position_um(defects[other])
                        if math.hypot(x - other_x, y - other_y) <= threshold:
                            union(index, other)
            cells.setdefault(cell, []).append(index)
        grouped = {}
        for index in indexes:
            grouped.setdefault(find(index), []).append(index)
        components.extend(
            {"population": population_name, "indexes": members}
            for members in grouped.values()
            if len(members) >= minimum
        )

    # The manual's second pass merges nearby clusters using a threshold multiplier.
    merged = []
    for component in components:
        points = [_venn_position_um(defects[index]) for index in component["indexes"]]
        component["centroid"] = (
            sum(point[0] for point in points) / len(points),
            sum(point[1] for point in points) / len(points),
        )
        target = None
        for candidate in merged:
            if candidate["population"] != component["population"]:
                continue
            if math.hypot(
                candidate["centroid"][0] - component["centroid"][0],
                candidate["centroid"][1] - component["centroid"][1],
            ) <= threshold * multiplier:
                target = candidate
                break
        if target is None:
            merged.append(component)
            continue
        target["indexes"].extend(component["indexes"])
        points = [_venn_position_um(defects[index]) for index in target["indexes"]]
        target["centroid"] = (
            sum(point[0] for point in points) / len(points),
            sum(point[1] for point in points) / len(points),
        )

    for cluster_id, component in enumerate(merged, start=1):
        for index in component["indexes"]:
            defects[index]["cluster_id"] = cluster_id
    return {
        "auto": auto,
        "distance_threshold_um": round(threshold, 3),
        "second_pass_multiplier": multiplier,
        "cluster_within": "Each Test" if each_test else "All Tests",
        "cluster_count": len(merged),
        "clustered_defect_count": sum(len(item["indexes"]) for item in merged),
    }


def _repeater_position_um(defect: dict, algorithm: str, recipe: dict) -> tuple[float, float]:
    if algorithm == "Reticle Wafer" and defect.get("reticle_local_x_um") is not None:
        return float(defect["reticle_local_x_um"]), float(defect.get("reticle_local_y_um", 0.0))
    if defect.get("die_local_x_um") is not None:
        local_x = float(defect["die_local_x_um"])
        local_y = float(defect.get("die_local_y_um", 0.0))
    else:
        wafer_map = recipe.get("wafer_map") or {}
        width = max(1.0, float(wafer_map.get("die_width_um", 1000.0) or 1000.0))
        height = max(1.0, float(wafer_map.get("die_height_um", 1000.0) or 1000.0))
        x, y = _venn_position_um(defect)
        local_x, local_y = x % width, y % height
    if algorithm == "Reticle Wafer":
        wafer_map = recipe.get("wafer_map") or {}
        reticle = wafer_map.get("reticle_size") or [1, 1]
        reticle_width = int(reticle[0]) if len(reticle) > 0 else 1
        reticle_height = int(reticle[1]) if len(reticle) > 1 else 1
        die_width = max(1.0, float(wafer_map.get("die_width_um", 1000.0) or 1000.0))
        die_height = max(1.0, float(wafer_map.get("die_height_um", 1000.0) or 1000.0))
        local_x += (int(defect.get("die_x", 0)) % max(1, reticle_width)) * die_width
        local_y += (int(defect.get("die_y", 0)) % max(1, reticle_height)) * die_height
    return local_x, local_y


def _apply_repeater_analysis(defects: list[dict], parameters: dict, recipe: dict) -> dict:
    algorithm = parameters.get("algorithm", "Reticle Wafer")
    x_tolerance = float(parameters.get("x_tolerance_um", 5.0))
    y_tolerance = float(parameters.get("y_tolerance_um", 5.0))
    threshold = max(2, int(parameters.get("repeater_threshold", 3)))
    for defect in defects:
        defect["repeater"] = False
        defect.pop("repeater_id", None)

    populations = {}
    for index, defect in enumerate(defects):
        if algorithm == "Die Row":
            population = ("die-row", int(defect.get("die_y", 0)))
        elif algorithm == "Reticle Row":
            reticle = (recipe.get("wafer_map") or {}).get("reticle_size") or [1, 1]
            height = max(1, int(reticle[1]) if len(reticle) > 1 else 1)
            population = ("reticle-row", int(defect.get("die_y", 0)) // height)
        else:
            population = (algorithm, 0)
        populations.setdefault(population, []).append(index)

    repeater_count = 0
    repeater_defects = 0
    for indexes in populations.values():
        pending = set(indexes)
        while pending:
            seed = min(pending)
            pending.remove(seed)
            seed_x, seed_y = _repeater_position_um(defects[seed], algorithm, recipe)
            matches = [seed]
            for other in list(pending):
                other_x, other_y = _repeater_position_um(defects[other], algorithm, recipe)
                if abs(seed_x - other_x) <= x_tolerance and abs(seed_y - other_y) <= y_tolerance:
                    pending.remove(other)
                    matches.append(other)
            if len(matches) < threshold:
                continue
            repeater_count += 1
            repeater_defects += len(matches)
            for index in matches:
                defects[index]["repeater"] = True
                defects[index]["repeater_id"] = repeater_count
    return {
        "algorithm": algorithm,
        "x_tolerance_um": x_tolerance,
        "y_tolerance_um": y_tolerance,
        "threshold": threshold,
        "repeater_count": repeater_count,
        "repeater_defect_count": repeater_defects,
    }


def _parse_name_code_map(value) -> dict[str, int]:
    mapping = {}
    for entry in re.split(r"[\n;,]+", str(value or "")):
        parts = re.split(r"\s*[:=]\s*", entry.strip(), maxsplit=1)
        if len(parts) != 2:
            continue
        left, right = parts
        try:
            mapping[left.strip()] = int(right.strip())
        except ValueError:
            try:
                mapping[right.strip()] = int(left.strip())
            except ValueError:
                continue
    return mapping


def _apply_cag_assignment(defects: list[dict], parameters: dict) -> dict:
    mapping = _parse_name_code_map(parameters.get("cag_name_code_map"))
    assigned = 0
    for defect in defects:
        name = str(
            defect.get("care_area_group")
            or defect.get("cag_name")
            or defect.get("region_id")
            or ""
        )
        if name in mapping:
            defect["cag_code"] = mapping[name]
            assigned += 1
    return {"mapping": mapping, "assigned_count": assigned}


def _apply_spatial_population(defects: list[dict], parameters: dict) -> dict:
    class_map = _parse_name_code_map(parameters.get("class_code_map"))
    scratch_code = class_map.get("Scratch", 1)
    candidates = {}
    for index, defect in enumerate(defects):
        cluster_id = int(defect.get("cluster_id", 0) or 0)
        if cluster_id:
            candidates.setdefault(cluster_id, []).append(index)
        defect.pop("macro_sig_class", None)
        defect.pop("macro_sig_id", None)
        defect.pop("micro_sig_class", None)
    signature_count = 0
    assigned = 0
    for indexes in candidates.values():
        if len(indexes) < 3:
            continue
        points = [_venn_position_um(defects[index]) for index in indexes]
        width = max(point[0] for point in points) - min(point[0] for point in points)
        height = max(point[1] for point in points) - min(point[1] for point in points)
        short_axis = max(1.0, min(width, height))
        if max(width, height) / short_axis < 4.0:
            continue
        signature_count += 1
        for index in indexes:
            defect = defects[index]
            defect["macro_sig_class"] = scratch_code
            defect["macro_sig_id"] = signature_count
            if defect.get("x") is not None and defect.get("y") is not None:
                radius = math.hypot(float(defect["x"]), float(defect["y"]))
                defect["micro_sig_class"] = 2 if radius >= 0.75 else 1
            else:
                defect["micro_sig_class"] = 1
            assigned += 1
    return {
        "signature_category": parameters.get("signature_category", "Scratch"),
        "ssa_recipe": parameters.get("ssa_recipe", "Scratch"),
        "signature_count": signature_count,
        "assigned_count": assigned,
        "macro_sig_class": scratch_code,
    }


def _majority_roughbin(defects: list[dict], indexes: list[int], excluded: set[int]):
    counts = {}
    for index in indexes:
        code = int(defects[index].get("roughbin", 0) or 0)
        if code not in excluded:
            counts[code] = counts.get(code, 0) + 1
    if not counts:
        return None
    return min(counts, key=lambda code: (-counts[code], code))


def _apply_population_arbitration(defects: list[dict], parameters: dict) -> dict:
    excluded = {
        int(value) for value in re.findall(r"-?\d+", str(parameters.get("exclude_codes", "")))
    }
    assigned_indexes = set()
    changed = 0
    if parameters.get("arbitrate_spatial_population", True):
        signatures = {}
        for index, defect in enumerate(defects):
            signature = defect.get("macro_sig_class")
            if signature is not None:
                signatures.setdefault(signature, []).append(index)
        for indexes in signatures.values():
            winner = _majority_roughbin(defects, indexes, excluded)
            if winner is None:
                continue
            for index in indexes:
                if int(defects[index].get("roughbin", 0) or 0) in excluded:
                    continue
                changed += defects[index].get("roughbin") != winner
                defects[index]["roughbin"] = winner
                assigned_indexes.add(index)
    clusters = {}
    for index, defect in enumerate(defects):
        cluster_id = int(defect.get("cluster_id", 0) or 0)
        if cluster_id and index not in assigned_indexes:
            clusters.setdefault(cluster_id, []).append(index)
    for indexes in clusters.values():
        winner = _majority_roughbin(defects, indexes, excluded)
        if winner is None:
            continue
        for index in indexes:
            if int(defects[index].get("roughbin", 0) or 0) in excluded:
                continue
            changed += defects[index].get("roughbin") != winner
            defects[index]["roughbin"] = winner
    return {
        "exclude_codes": sorted(excluded),
        "arbitrate_spatial_population": bool(parameters.get("arbitrate_spatial_population", True)),
        "changed_count": changed,
    }


def _selected_previous_results(previous_results: list[dict], parameters: dict, context: dict) -> list[dict]:
    selected = []
    for result in previous_results:
        if parameters.get("same_lot_id") and str(result.get("lot_id", "")) != str(context.get("lot_id", "")):
            continue
        if parameters.get("same_wafer_id") and str(result.get("wafer_id", "")) != str(context.get("wafer_id", "")):
            continue
        if parameters.get("same_scribe_id") and str(result.get("scribe_id", "")) != str(context.get("scribe_id", "")):
            continue
        selected.append(result)
    selected.sort(key=lambda item: str(item.get("created", "")), reverse=True)
    layer_selection = parameters.get("layer_selection", "All Previous")
    if layer_selection == "Previous N Layers":
        selected = selected[:max(1, int(parameters.get("previous_n_layers", 1)))]
    elif layer_selection == "Step IDs":
        steps = set(_test_list(parameters.get("step_ids")))
        selected = [item for item in selected if str(item.get("step", "")) in steps]
    if parameters.get("last_scan_only", True):
        latest_by_step = {}
        for result in selected:
            latest_by_step.setdefault(str(result.get("step", "")), result)
        selected = list(latest_by_step.values())
    return selected


def _dsa_matches(current: dict, previous: dict, parameters: dict) -> bool:
    current_x, current_y = _venn_position_um(current)
    previous_x, previous_y = _venn_position_um(previous)
    tolerance = float(parameters.get("tolerance_um", 20.0))
    if parameters.get("search_mode", "Point-Based Search") == "Size-Based Search":
        current_radius = float(current.get("size_um", 0.0)) / 2.0
        previous_radius = float(previous.get("size_um", 0.0)) / 2.0
        return (
            abs(current_x - previous_x) <= tolerance + current_radius + previous_radius
            and abs(current_y - previous_y) <= tolerance + current_radius + previous_radius
        )
    return math.hypot(current_x - previous_x, current_y - previous_y) <= tolerance


def _apply_dsa(
    defects: list[dict],
    parameters: dict,
    previous_results: list[dict],
    context: dict,
) -> tuple[list[dict], dict, list[dict]]:
    layers = _selected_previous_results(previous_results, parameters, context)
    previous_defects = []
    for layer_index, result in enumerate(layers):
        for defect in result.get("defects", []):
            item = deepcopy(defect)
            item["_dsa_layer_index"] = layer_index
            item["_dsa_result_id"] = result.get("id", "")
            item["_dsa_step"] = result.get("step", "")
            previous_defects.append(item)

    consumed = set()
    matched_previous = set()
    matched_current = 0
    kept = []
    single = parameters.get("matching_mode") == "Single Defect Within Tolerance"
    for defect in defects:
        matches = []
        for index, previous in enumerate(previous_defects):
            consume_key = (previous.get("_dsa_layer_index"), index)
            if single and consume_key in consumed:
                continue
            if _dsa_matches(defect, previous, parameters):
                matches.append((index, previous, consume_key))
                if single:
                    break
        defect["adder"] = not bool(matches)
        defect["dsa_status"] = "Current Layer Adder" if defect["adder"] else "Previous Layer Match"
        defect["dsa_previous_ids"] = [item.get("id") for _index, item, _key in matches]
        if matches:
            matched_current += 1
            for index, _item, consume_key in matches:
                matched_previous.add(index)
                consumed.add(consume_key)
        if not matches or not parameters.get("remove_common_defects"):
            kept.append(defect)

    upld = []
    if parameters.get("dsa_plus"):
        requested_codes = {
            int(value) for value in re.findall(r"-?\d+", str(parameters.get("upld_class_codes", "")))
        }
        next_id = max(
            [int(item.get("id", 0)) for item in defects if str(item.get("id", "")).isdigit()] or [0]
        ) + 1
        maximum_images = max(0, int(parameters.get("maximum_images", 100)))
        grabbed_images = 0
        for index, previous in enumerate(previous_defects):
            if index in matched_previous:
                continue
            code = int(previous.get("class_code", 0) or 0)
            if requested_codes and code not in requested_codes:
                continue
            previous.pop("_dsa_layer_index", None)
            previous.pop("_dsa_result_id", None)
            previous.pop("_dsa_step", None)
            previous["id"] = next_id
            next_id += 1
            previous["test_id"] = int(parameters.get("upld_test_id", 50))
            previous["test"] = f"Test {previous['test_id']}"
            previous["upld"] = True
            previous["adder"] = False
            previous["dsa_status"] = "Unique Previous Layer Defect"
            if parameters.get("reset_upld_class_codes"):
                previous["class_code"] = 0
            grab = bool(parameters.get("grab_optical_images")) and grabbed_images < maximum_images
            previous["has_patch_image"] = grab
            previous["has_reference_image"] = grab and bool(parameters.get("grab_reference_images"))
            previous["image_sent_to_database"] = grab and bool(parameters.get("send_images_to_database"))
            grabbed_images += int(grab)
            upld.append(previous)
    return kept, {
        "layers_compared": len(layers),
        "previous_defect_count": len(previous_defects),
        "matched_current_count": matched_current,
        "current_adder_count": sum(bool(item.get("adder")) for item in kept),
        "common_removed_count": len(defects) - len(kept),
        "upld_count": len(upld),
        "pre_align": parameters.get("pre_align", "Using Die Grids"),
    }, upld


def apply_wafer_post_processing(
    defects: list[dict],
    recipe: dict,
    *,
    previous_results: list[dict] | None = None,
    context: dict | None = None,
) -> tuple[list[dict], dict]:
    operations = recipe.get("wafer_post_processing", {}).get("operations", [])
    report = {
        "venn": {}, "clustering": {}, "dsa": {}, "repeater": {}, "cag_assignment": {},
        "spatial_population": {}, "population_arbitration": {}, "sampling": {},
        "excursion": {}, "execution_order": [], "klarf_transfer_count": len(defects),
    }
    upld = []
    retained_duplicates = []
    flag_map = {
        "review_sampling": "sampled_review",
        "patch_sampling": "retain_patch",
        "patch_transfer_sampling": "transfer_patch",
        "hi_res_sampling": "grab_hi_res",
    }
    sampling = next(
        (
            item.get("parameters", {}) for item in operations
            if item.get("enabled") and item.get("name") == "Sampling"
        ),
        None,
    )
    for defect in defects:
        defect.update({"sampled_review": False, "retain_patch": sampling is None or sampling.get("patch_sampling", "None") == "None", "transfer_patch": False, "grab_hi_res": False})

    for operation in operations:
        if not operation.get("enabled"):
            continue
        name = operation.get("name")
        parameters = operation.get("parameters", {})
        report["execution_order"].append(name)
        if name == "Venn":
            defects, report["venn"], duplicates = _apply_venn(defects, parameters)
            retained_duplicates.extend(duplicates)
        elif name == "Clustering":
            report["clustering"] = _apply_clustering(defects, parameters)
        elif name == "Defect Source Analysis":
            defects, report["dsa"], pending_upld = _apply_dsa(
                defects,
                parameters,
                list(previous_results or recipe.get("_previous_results") or []),
                dict(context or {}),
            )
            upld.extend(pending_upld)
        elif name == "Repeater Analysis":
            report["repeater"] = _apply_repeater_analysis(defects, parameters, recipe)
        elif name == "CAG Code Assignment":
            report["cag_assignment"] = _apply_cag_assignment(defects, parameters)
        elif name == "Spatial Population":
            report["spatial_population"] = _apply_spatial_population(defects, parameters)
        elif name == "Population Arbitration":
            report["population_arbitration"] = _apply_population_arbitration(defects, parameters)
        elif name == "Sampling":
            maximum = int(parameters.get("maximum_samples", 50))
            for scheme, flag in flag_map.items():
                method = parameters.get(scheme, "None")
                if method == "None":
                    continue
                selected = (
                    _precision_sample(defects, parameters, maximum)
                    if method == "Precision"
                    else _sample_candidates(defects, method, parameters, maximum)
                )
                for defect in selected:
                    defect[flag] = True
                report["sampling"][scheme] = {"method": method, "count": len(selected)}
        elif name == "Excursion Reduction":
            matched = 0
            active_sample_flags = [flag_map[scheme] for scheme in report["sampling"]]
            for defect in defects:
                for rule in parameters.get("rules") or []:
                    if rule.get("enabled", True) and _matches_expression(defect, rule.get("expression", "")):
                        defect["excursion_rule"] = rule.get("name", "Rule")
                        matched += 1
                        break
                sampled = any(defect.get(flag) for flag in active_sample_flags)
                defect["klarf_included"] = (
                    sampled
                    if active_sample_flags and parameters.get("remove_non_sampled", True)
                    else True
                )
            report["excursion"] = {
                "matched": matched,
                "remove_non_sampled": bool(parameters.get("remove_non_sampled", True)),
                "data_transfer": parameters.get("data_transfer", "Filtered Result"),
            }
    if upld:
        for defect in upld:
            defect["klarf_included"] = True
            defect.update({
                "sampled_review": False,
                "retain_patch": bool(defect.get("has_patch_image")),
                "transfer_patch": False,
                "grab_hi_res": False,
            })
        defects.extend(upld)
    if retained_duplicates:
        defects.extend(retained_duplicates)
    for defect in defects:
        if defect.get("multi_test_duplicate") or defect.get("duplicate"):
            defect["klarf_included"] = False
    report["klarf_transfer_count"] = sum(
        1 for defect in defects if defect.get("klarf_included", True)
    )
    return defects, report


def validate_run_setup(setup: dict, recipe: dict) -> list[str]:
    errors = []
    if not str(setup.get("lot_id", "")).strip():
        errors.append("Lot ID is required")
    available = set(_test_names(recipe))
    selected = [name for name in setup.get("selected_tests", []) if name in available]
    if not selected:
        errors.append("Select at least one test to run")
    if setup.get("repeat_test") and not 1 <= int(setup.get("repeat_count", 0)) <= 999:
        errors.append("Repeat count must be between 1 and 999")
    if setup.get("auto_transfer") and not str(setup.get("transfer_host", "")).strip():
        errors.append("Transfer host is required when Auto Transfer is enabled")
    errors.extend(transfer_prerequisite_errors(setup, recipe, selected))
    if setup.get("osts_data"):
        if not setup.get("collect_sensitivity_data"):
            errors.append("OSTS Data requires Collect Sensitivity Data")
        for test in _selected_test_states(recipe, selected):
            enabled = {
                name
                for region in (test.get("sensitivity") or {}).get("regions", {}).values()
                for name, settings in (region.get("algorithms") or {}).items()
                if settings.get("run")
            }
            incompatible = enabled - {"HLAT", "FAST"}
            if incompatible:
                errors.append(
                    f"{test.get('name', 'Test')}: OSTS is incompatible with {', '.join(sorted(incompatible))}"
                )
            if not enabled.intersection({"HLAT", "FAST"}):
                errors.append(f"{test.get('name', 'Test')}: OSTS requires HLAT or FAST")
    return errors


def apply_sample_plans(defects: list[dict], tests: list[dict], wafer_map=None):
    """Apply per-die sample modes and simulated swath coverage before reporting."""
    test_states = {test.get("name", "Test 1"): test for test in tests}
    reticle_height = max(
        1,
        int(
            (wafer_map or {}).get("reticle_size_height")
            or (wafer_map or {}).get("reticle_height")
            or 1
        ),
    )
    report = {}
    kept = []
    for defect in defects:
        test_name = defect.get("test", "Test 1")
        test = test_states.get(test_name, {})
        plan = test.get("sample_plan") or {}
        mode = (plan.get("overrides") or {}).get(
            f"{int(defect.get('die_x', 0))},{int(defect.get('die_y', 0))}",
            "Primary Threshold",
        )
        coverage = float(plan.get("coverage", test.get("coverage", 100.0)))
        denominator = 1 if coverage >= 100 else 2 if coverage >= 50 else 4 if coverage >= 25 else 8
        basis = plan.get("coverage_basis", "Die Based")
        die_x = int(defect.get("die_x", 0))
        die_y = int(defect.get("die_y", 0))
        row_phase = die_y if basis == "Die Based" else die_y // reticle_height
        phase_key = f"{die_x}:{die_y}:{int(defect.get('id', 0))}:{row_phase}"
        swath_phase = (
            int(hashlib.sha256(phase_key.encode("ascii")).hexdigest()[:8], 16)
            % denominator
        )
        covered = swath_phase == 0
        summary = report.setdefault(
            test_name,
            {
                "coverage": coverage,
                "coverage_basis": basis,
                "candidate_defects": 0,
                "reported_defects": 0,
                "do_not_inspect": 0,
                "do_not_report": 0,
                "outside_swath_coverage": 0,
            },
        )
        summary["candidate_defects"] += 1
        defect["sample_plan_mode"] = mode
        defect["swath_coverage"] = coverage
        defect["swath_coverage_basis"] = basis
        if mode == "Do Not Inspect":
            summary["do_not_inspect"] += 1
            continue
        if not covered:
            summary["outside_swath_coverage"] += 1
            continue
        if mode == "Do Not Report":
            summary["do_not_report"] += 1
            continue
        defect["threshold_mode"] = (
            "Secondary" if mode == "Secondary Threshold" else "Primary"
        )
        summary["reported_defects"] += 1
        kept.append(defect)
    return kept, report


def apply_sensitivity_settings(defects: list[dict], tests: list[dict]):
    """Attach configured detection algorithms and apply the process-noise filter."""
    test_states = {test.get("name", "Test 1"): test for test in tests}
    report = {}
    kept = []
    for defect in defects:
        test_name = defect.get("test", "Test 1")
        sensitivity = (test_states.get(test_name, {}).get("sensitivity") or {})
        regions = sensitivity.get("regions") or {}
        region_names = list(regions)
        requested_region = str(defect.get("region_id", ""))
        if requested_region in regions:
            region_name = requested_region
        elif region_names:
            region_name = region_names[(int(defect.get("id", 1)) - 1) % len(region_names)]
        else:
            region_name = requested_region or "Default"
        region = regions.get(region_name) or {}
        active_algorithms = [
            name
            for name, settings in (region.get("algorithms") or {}).items()
            if settings.get("run")
        ]
        if not active_algorithms:
            active_algorithms = ["HLAT"]
        defect["sensitivity_region"] = region_name
        defect["detection_algorithms"] = active_algorithms
        defect["histogram_remap"] = bool(sensitivity.get("histogram_remap", True))
        defect["projection_remap"] = bool(region.get("enable_remap", False))
        channel = max(1, min(3, int(defect.get("channel", 1))))
        if sensitivity.get("decouple_channel_fusion") and any(
            name in active_algorithms for name in ("HLAT", "Secondary HLAT")
        ):
            values = (
                (sensitivity.get("decoupled_cf") or {}).get(region_name) or [{}, {}, {}]
            )
            channel_values = values[channel - 1] if channel - 1 < len(values) else {}
            defect["HLATCFAbsmin"] = float(channel_values.get("MinDiff", 0.0))
            for fusion_channel in range(1, 4):
                settings = values[fusion_channel - 1] if fusion_channel - 1 < len(values) else {}
                prefix = f"HLATCF_CH{fusion_channel}_"
                defect[prefix + "Noise"] = float(settings.get("Noise", 0.0))
                defect[prefix + "Absmin"] = float(settings.get("MinDiff", 0.0))
                defect[prefix + "Gradient"] = float(settings.get("Gradient", 0.0))
                defect[prefix + "Color"] = float(settings.get("Color", 0.0))
        vnc = sensitivity.get("vnc") or {}
        if vnc.get("enabled") and region_name in (vnc.get("regions") or []):
            max_bw = list((vnc.get("max_bw") or {}).get(region_name) or [])
            defect["vnc_mode"] = vnc.get("mode", "Apply")
            defect["vnc_max_bw"] = max_bw[channel - 1] if channel - 1 < len(max_bw) else None

        filters = sensitivity.get("defect_filters") or {}
        filtered = False
        if filters.get("run_process_noise_filter"):
            side_ratio = round(0.5 + (int(defect.get("id", 0)) % 10) / 5.0, 3)
            top_ratio = round(0.5 + (int(defect.get("id", 0)) % 7) / 4.0, 3)
            defect["process_noise_side_ratio"] = side_ratio
            defect["process_noise_top_ratio"] = top_ratio
            filtered = (
                float(defect.get("signal", 0.0)) < float(filters.get("intensity", 0.0))
                or side_ratio < float(filters.get("side_ratio", 0.0))
                or top_ratio < float(filters.get("top_ratio", 0.0))
            )
        summary = report.setdefault(
            test_name,
            {
                "regions": {},
                "process_noise_filter": bool(filters.get("run_process_noise_filter")),
                "filtered_defects": 0,
                "histogram_remap": bool(sensitivity.get("histogram_remap", True)),
                "autosens_mode": sensitivity.get("autosens_mode", "Production"),
                "post_filter": sensitivity.get("post_filter", "None"),
                "dark_defect_factor": float(sensitivity.get("dark_defect_factor", 1.0)),
                "rta": deepcopy(sensitivity.get("runtime_alignment") or {}),
            },
        )
        summary["regions"].setdefault(region_name, active_algorithms)
        if filtered:
            summary["filtered_defects"] += 1
            continue
        kept.append(defect)
    return kept, report


def generate_inspection_result(recipe: dict, setup: dict, *, repeat_index=1, status="Complete") -> dict:
    seed_text = "|".join(
        [
            str(recipe.get("id", "")),
            str(setup.get("lot_id", "")),
            str(setup.get("wafer_id", "")),
            str(repeat_index),
        ]
    )
    seed = int(hashlib.sha256(seed_text.encode("utf-8")).hexdigest()[:16], 16)
    rng = random.Random(seed)
    tests = list(setup.get("selected_tests") or _test_names(recipe) or ["Test 1"])
    selected_test_states = _selected_test_states(recipe, tests)
    collecting_bandwidth = any(
        test.get("name", f"Test {index + 1}") in tests
        and (test.get("sensitivity") or {}).get("vnc", {}).get("mode") == "Collect Bandwidth"
        for index, test in enumerate(recipe.get("tests", []))
    )
    defect_count = 0 if collecting_bandwidth else (10000 if setup.get("osts_data") else 56 + seed % 95)
    defects = []
    class_codes = [0, 1, 2, 10, 20, 30]
    for defect_id in range(1, defect_count + 1):
        radius = math.sqrt(rng.random()) * 0.94
        angle = rng.random() * math.tau
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        size = round(rng.uniform(0.08, 8.5), 3)
        signal = round(rng.uniform(4.0, 260.0), 2)
        defects.append(
            {
                "id": defect_id,
                "x": round(x, 5),
                "y": round(y, 5),
                "die_x": int(round(x * 20)),
                "die_y": int(round(y * 20)),
                "test": tests[(defect_id - 1) % len(tests)],
                "class_code": class_codes[rng.randrange(len(class_codes))],
                "size_um": size,
                "signal": signal,
                "roughbin": rng.randrange(1, 9),
                "cluster_id": defect_id // 4 if defect_id % 4 else 0,
                "region_id": f"R{1 + (defect_id - 1) % 3}",
                "channel": 1 + (defect_id - 1) % 3,
                "polarity": "Bright" if defect_id % 2 else "Dark",
                "die_type": "Secondary" if defect_id % 9 == 0 else "Primary",
                "adder": defect_id % 5 != 0,
                "repeater": defect_id % 11 == 0,
                "threshold_region": f"T{1 + (defect_id - 1) % 2}",
                "venn_id": defect_id % 4,
                "image_kind": rng.randrange(4),
                "has_patch_image": rng.random() > 0.15,
                "has_sem_image": False,
                "has_manual_image": False,
                "marked": False,
                "reviewed": False,
            }
        )
    classifier_execution = []
    nef_filtered_count = 0
    feature_vector_file = ""
    for test in selected_test_states:
        test_name = test.get("name", "Test 1")
        nef = test.get("nef") or {}
        chain = list(nef.get("classifiers") or []) if test.get("run_nef") else []
        direct_ido = test.get("ido_classifier") if test.get("run_ido") else None
        if test.get("run_ido") and test.get("save_feature_vectors"):
            feature_vector_file = "FeatureVectors.bin"
        if chain:
            classifier_execution.append(
                {
                    "test": test_name,
                    "source": "Sequential NEF",
                    "classifiers": [
                        {
                            "name": item.get("name", ""),
                            "type": item.get("type", "ST-NEF"),
                            "st_nef": bool(item.get("st_nef", item.get("type") == "ST-NEF")),
                            "feature_vector_version": item.get("feature_vector_version", ""),
                        }
                        for item in chain
                    ],
                    "keep_nuisance_defects": bool(nef.get("keep_nuisance_defects")),
                }
            )
        if direct_ido:
            classifier_execution.append(
                {
                    "test": test_name,
                    "source": "iDO",
                    "classifiers": [{
                        "name": direct_ido.get("name", ""),
                        "type": "iDO",
                        "st_nef": False,
                        "feature_vector_version": direct_ido.get("feature_vector_version", ""),
                    }],
                    "keep_nuisance_defects": True,
                }
            )
        ido_candidates = [item for item in chain if item.get("type") == "iDO"]
        if direct_ido:
            ido_candidates.append(direct_ido)
        ido_classifier = ido_candidates[-1] if ido_candidates else None
        rough_code = (ido_classifier or {}).get("rough_code") or ""
        kept_defects = []
        for defect in defects:
            if defect.get("test") != test_name:
                kept_defects.append(defect)
                continue
            nuisance = bool(chain) and defect.get("id", 0) % 7 == 0
            if nuisance and not nef.get("keep_nuisance_defects"):
                nef_filtered_count += 1
                continue
            if nuisance:
                defect["nuisance"] = True
                defect["classification_source"] = "ST-NEF"
            if ido_classifier:
                defect["ido_rough_code"] = rough_code or f"R{1 + defect.get('id', 0) % 8}"
                defect["ido_rough_group"] = (
                    (ido_classifier or {}).get("rough_group")
                    or f"G{1 + defect.get('id', 0) % 4}"
                )
                defect["classification_source"] = "iDO"
            kept_defects.append(defect)
        defects = kept_defects
    nanopoint_execution = []
    if not collecting_bandwidth:
        for test in selected_test_states:
            state = test.get("nano_point_templates") or {}
            if not (
                state.get("valid", True)
                and state.get("images_grabbed")
                and state.get("poi_search_complete")
            ):
                continue
            test_name = test.get("name", "Test 1")
            counts = {}
            for template_index, template in enumerate(state.get("templates") or [], start=1):
                if not template.get("search", True):
                    continue
                variants = ["Original"] + list(template.get("flips") or [])
                template_name = str(template.get("name") or f"Target {template_index}")
                for variant_index, variant in enumerate(variants):
                    defect_id = len(defects) + 1
                    radius = math.sqrt(rng.random()) * 0.90
                    angle = rng.random() * math.tau
                    x = radius * math.cos(angle)
                    y = radius * math.sin(angle)
                    display_name = (
                        template_name
                        if variant == "Original"
                        else f"{template_name} ({variant} Flip)"
                    )
                    confidence = round(
                        max(
                            float(template.get("search_threshold", 0.75)),
                            min(0.999, float(template.get("confidence", 0.9))),
                        ),
                        3,
                    )
                    defects.append(
                        {
                            "id": defect_id,
                            "x": round(x, 5),
                            "y": round(y, 5),
                            "die_x": int(round(x * 20)),
                            "die_y": int(round(y * 20)),
                            "test": test_name,
                            "class_code": int(template.get("class_code", 0)),
                            "size_um": round(float(state.get("mca_size", 5)) / 10.0, 3),
                            "signal": round(180.0 + confidence * 70.0, 2),
                            "roughbin": 0,
                            "cluster_id": 0,
                            "region_id": template.get("linked_care_area") or "NPI",
                            "channel": 1,
                            "polarity": "Bright",
                            "die_type": "Primary",
                            "adder": True,
                            "repeater": False,
                            "threshold_region": "NPI",
                            "venn_id": 0,
                            "image_kind": 0,
                            "has_patch_image": bool(template.get("has_patch_images", True)),
                            "has_sem_image": bool(template.get("has_sem_image")),
                            "has_manual_image": False,
                            "marked": False,
                            "reviewed": False,
                            "detection_source": "NanoPoint Image Template",
                            "npi_target_id": f"{template_index}:{variant_index}",
                            "npi_template": display_name,
                            "npi_confidence": confidence,
                        }
                    )
                    counts[display_name] = counts.get(display_name, 0) + 1
            if counts:
                nanopoint_execution.append({"test": test_name, "counts": counts})
    defects, sensitivity_execution = apply_sensitivity_settings(
        defects,
        selected_test_states,
    )
    defects, sample_plan_execution = apply_sample_plans(
        defects,
        selected_test_states,
        recipe.get("wafer_map") or {},
    )
    dbb = recipe.get("dbb") or {}
    dbb_enabled = bool(dbb.get("enabled") and dbb.get("registered"))
    dbb_execution = {"enabled": dbb_enabled, "processed": 0, "sampled": 0, "clips": 0}
    if dbb_enabled:
        bins = list(dbb.get("dbc_bins") or [])
        process_layers = list(dbb.get("process_layers") or [dbb.get("inspection_layer", "Design")])
        processed_count = 0
        skipped_count = 0
        for defect in defects:
            selected_bin = None
            identifier = int(defect.get("id", 0))
            defect["design_x_nm"] = round((float(defect.get("x", 0)) + 1.0) * 500000, 2)
            defect["design_y_nm"] = round((float(defect.get("y", 0)) + 1.0) * 500000, 2)
            defect["design_layer"] = process_layers[identifier % len(process_layers)] if process_layers else "Design"
            defect["floor_plan_id"] = 1 + identifier % 4
            if dbb.get("exclude_array_regions") and str(defect.get("region", "")).casefold() == "array":
                defect["dbb_global_bin"] = 0
                defect["dbb_skipped_reason"] = "Array Region"
                skipped_count += 1
                continue
            skip_attributes = bool(dbb.get("throughput_skip_attributes") and identifier % 10 == 0)
            if dbb.get("dci_enabled") and not skip_attributes:
                defect["dci"] = round((identifier * 17 % 101) / 100.0, 3)
                defect["dci_range"] = round(90 + identifier % 11, 2)
            if dbb.get("pci_enabled") and not skip_attributes:
                defect["pci"] = round((identifier * 29 % 101) / 100.0, 3)
                defect["line_complexity"] = 1 + identifier % 25
            if dbb.get("design_attributes_enabled") and not skip_attributes:
                defect["min_line_width_nm"] = 20 + identifier % 81
                defect["min_space_nm"] = 18 + identifier % 73
                defect["polygon_density"] = round((identifier * 11 % 100) / 100.0, 3)
                defect["pattern_granularity"] = round((identifier * 19 % 100) / 100.0, 3)
            if (dbb.get("pattern_density_1") or dbb.get("pattern_density_2")) and not skip_attributes:
                defect["pattern_density"] = round((identifier * 13 % 100) / 100.0, 3)
                defect["ebb_pattern_density"] = round((identifier * 23 % 100) / 100.0, 3)
            if (dbb.get("overlap_ratio_1") or dbb.get("overlap_ratio_2")) and not skip_attributes:
                defect["ebb_overlap_ratio"] = round((identifier * 31 % 100) / 100.0, 3)
            defect_area = float(defect.get("size_um", defect.get("size", defect.get("dsize", 0))) or 0)
            eligible_bins = [
                item for item in bins
                if not item.get("size_sieve_enabled")
                or float(item.get("minimum_area", 0)) < defect_area < float(item.get("maximum_area", 500000000))
            ]
            if dbb.get("dbc_enabled") and eligible_bins:
                selected_bin = eligible_bins[identifier % len(eligible_bins)]
                defect["dbc_bin"] = selected_bin.get("name", "DBC Bin")
                defect["dbc_class_code"] = selected_bin.get("class_code", 0)
                defect["dbc_nuisance"] = bool(selected_bin.get("nuisance"))
                if selected_bin.get("rough_bin_enabled"):
                    defect["rough_bin"] = selected_bin.get("rough_bin_code", 0)
            filter_out = False
            if dbb.get("dbg_filter_enabled"):
                attribute_name = {
                    "Pattern Density": "pattern_density",
                    "Defect Size": "size_um",
                    "DCI": "dci",
                    "PCI": "pci",
                }.get(dbb.get("dbg_filter_attribute"), "pattern_density")
                left = float(defect.get(attribute_name, defect_area if attribute_name == "size_um" else 0) or 0)
                right = float(dbb.get("dbg_filter_value", 0))
                operator = dbb.get("dbg_filter_operator", ">=")
                filter_out = {
                    ">=": left >= right, ">": left > right, "<=": left <= right,
                    "<": left < right, "==": left == right, "!=": left != right,
                }.get(operator, False)
            skip_scan_dbb = bool(dbb.get("throughput_skip_dbb") and identifier % 20 == 0)
            if dbb.get("dbg_enabled") and not filter_out and not skip_scan_dbb:
                group_count = max(1, min(int(dbb.get("dbg_stop_group_count", 1500)), 50))
                defect["dbg_group"] = 1 + identifier % group_count
                defect["dbg_type"] = "Systematic" if identifier % 4 == 0 else "Random"
                defect["dbg_similarity"] = round(70 + identifier % 31, 2)
                if dbb.get("supergrouping_enabled") and dbb.get("dbg_algorithm") == "DBG1":
                    defect["dbg_supergroup"] = 1 + identifier % max(1, group_count // 4)
            if filter_out:
                defect["dbg_filtered_out"] = True
            if skip_scan_dbb:
                defect["dbb_throughput_skipped"] = True
            if defect.get("dbc_bin") and selected_bin is not None:
                defect["dbb_global_bin"] = 2 if selected_bin.get("non_poi") else 1
            elif defect.get("dbg_group"):
                defect["dbb_global_bin"] = 3 if defect.get("dbg_type") == "Systematic" else 4
            else:
                defect["dbb_global_bin"] = 0
            processed_count += 1
        from ..design_based_binning.workspace import sample_dbb_defects

        sampled_ids = set(sample_dbb_defects(defects, dbb.get("sampling") or {}))
        for defect in defects:
            defect["dbb_sampled"] = defect.get("id") in sampled_ids
        clip_count = min(200, len(sampled_ids)) if dbb.get("transfer_clip_images") else 0
        dbb_execution = {
            "enabled": True,
            "rdf_file": dbb.get("rdf_file", ""),
            "inspection_layer": dbb.get("inspection_layer", ""),
            "processed": processed_count,
            "skipped": skipped_count,
            "sampled": len(sampled_ids),
            "clips": clip_count,
            "server": "Simulated",
        }
    defects, wpp_execution = apply_wafer_post_processing(
        defects,
        recipe,
        previous_results=recipe.get("_previous_results"),
        context={
            **setup,
            "wafer_id": str(setup.get("wafer_id", "")).strip() or f"W{repeat_index:02d}",
        },
    )
    sizing = recipe.get("sizing") if isinstance(recipe.get("sizing"), dict) else {}
    sizing_enabled = bool(sizing.get("sizing_enabled", False))
    sizing_data = sizing_enabled and bool(sizing.get("collect_sizing_data", False))
    sizing_factors = {
        "Small": 0.60, "Medium": 0.85, "Large": 0.50,
        "Tall": 1.90, "Dim": 1.40, "Planar": 1.00,
    }
    if isinstance(sizing.get("scale_factors"), dict):
        sizing_factors.update(sizing["scale_factors"])
    sizing_groups = ("Small", "Medium", "Large", "Tall", "Dim", "Planar")
    if sizing_enabled:
        for index, defect in enumerate(defects):
            raw_size = float(defect.get("size_um", 0.0))
            if defect.get("polarity") == "Dark" and float(defect.get("signal", 0.0)) < 80:
                group = "Dim"
            elif raw_size < 0.8:
                group = "Small"
            elif raw_size > 4.0:
                group = "Large"
            else:
                group = sizing_groups[index % len(sizing_groups)]
            computed = round(raw_size * max(0.001, float(sizing_factors.get(group, 1.0))), 4)
            defect["sizing_scale_group"] = group
            defect["computed_size_um"] = computed
            defect["size_um"] = computed
            defect["reference_size_um"] = float(defect.get("reference_size_um", 0.0))
            if sizing_data:
                defect["raw_size_um"] = raw_size
                defect["planarity"] = round((index % 10) / 10.0, 3)
                defect["aspect_ratio"] = round(1.0 + (index % 4) / 2.0, 3)
    started = _now()
    result = {
        "id": uuid4().hex,
        "created": started,
        "completed": _now() if status == "Complete" else "",
        "lot_id": str(setup.get("lot_id", "")).strip(),
        "wafer_id": str(setup.get("wafer_id", "")).strip() or f"W{repeat_index:02d}",
        "scribe_id": str(setup.get("scribe_id", "")).strip(),
        "repeat_index": repeat_index,
        "inspection": recipe.get("inspection", ""),
        "device": recipe.get("device", ""),
        "step": recipe.get("step", ""),
        "recipe_id": recipe.get("id", ""),
        "recipe_version": f"{recipe.get('software_version', '9.8.306')}:{recipe.get('last_modified', '')}",
        "feature_vector_versions": {
            test.get("name", "Test 1"): test.get("feature_vector_version", "3.0A")
            for test in selected_test_states
        },
        "classifier_version_ids": [
            {
                "test": execution.get("test", ""),
                "name": classifier.get("name", ""),
                "type": classifier.get("type", ""),
                "feature_vector_version": classifier.get("feature_vector_version", ""),
            }
            for execution in classifier_execution
            for classifier in execution.get("classifiers", [])
        ],
        "wafer_orientation": recipe.get("wafer_orientation", "180 deg"),
        "die_height_um": (recipe.get("wafer_map") or {}).get("die_height_um", 0),
        "status": status,
        "selected_tests": tests,
        "defect_count": len(defects),
        "defects": defects,
        "classifier_execution": classifier_execution,
        "feature_vector_file": feature_vector_file,
        "nef_filtered_count": nef_filtered_count,
        "nanopoint_execution": nanopoint_execution,
        "sample_plan_execution": sample_plan_execution,
        "sensitivity_execution": sensitivity_execution,
        "wpp_execution": wpp_execution,
        "dbb_execution": dbb_execution,
        "sizing_enabled": sizing_enabled,
        "sizing_data": sizing_data,
        "sizing_recipe": deepcopy(sizing) if sizing_enabled else {},
        "sensitivity_data": bool(setup.get("collect_sensitivity_data")),
        "sensitivity_data_mode": "OSTS" if setup.get("osts_data") else "Normal Scan",
        "sensitivity_data_tests": tests if setup.get("collect_sensitivity_data") else [],
        "jobdump_files": (
            [f"rec_1_strip_{strip}_Row_{row}.txt" for strip in range(2) for row in range(8)]
            if collecting_bandwidth
            else []
        ),
        "transfer": {
            "auto": bool(setup.get("auto_transfer")),
            "host": setup.get("transfer_host", ""),
            "share": setup.get("transfer_share", "ImpactDataTemp"),
            "tool_type": setup.get("transfer_tool_type", "9xxx"),
            "target_path": "\\".join(
                part.strip("\\/")
                for part in (
                    str(setup.get("transfer_host", "")),
                    str(setup.get("transfer_share", "ImpactDataTemp")),
                    str(setup.get("transfer_tool_type", "9xxx")),
                    str(recipe.get("device", "")),
                    str(recipe.get("step", "")),
                )
                if part.strip("\\/")
            ),
            "patches": bool(setup.get("transfer_patches")),
            "hi_res": bool(setup.get("transfer_hi_res")),
            "state": "Transferred" if setup.get("auto_transfer") and status == "Complete" else "Local",
        },
        "backup_lot_result": bool(setup.get("backup_lot_result")),
        "run_log": [
            {"time": started, "level": "Info", "message": "Inspection run started"},
            {"time": _now(), "level": "Info", "message": f"{len(tests)} inspection test(s) executed"},
            *(
                [{
                    "time": _now(),
                    "level": "Info",
                    "message": (
                        "NanoPoint Image Template search added "
                        f"{sum(sum(item['counts'].values()) for item in nanopoint_execution)} defect(s)"
                    ),
                }]
                if nanopoint_execution
                else []
            ),
            *(
                [{
                    "time": _now(),
                    "level": "Info",
                    "message": "VNC bandwidth collection completed; no defects reported and JobDump files generated",
                }]
                if collecting_bandwidth
                else []
            ),
            *(
                [{
                    "time": _now(),
                    "level": "Info",
                    "message": f"Feature vector data saved to {feature_vector_file}",
                }]
                if feature_vector_file
                else []
            ),
            *(
                [{
                    "time": _now(),
                    "level": "Info",
                    "message": f"NEF/iDO classifier processing completed; {nef_filtered_count} nuisance defects removed",
                }]
                if classifier_execution
                else []
            ),
            *(
                [{
                    "time": _now(),
                    "level": "Info",
                    "message": (
                        "Wafer Post Processing completed; "
                        f"{wpp_execution['klarf_transfer_count']} defects selected for KLARF transfer"
                    ),
                }]
                if (
                    wpp_execution["venn"]
                    or wpp_execution["clustering"]
                    or wpp_execution["dsa"]
                    or wpp_execution["repeater"]
                    or wpp_execution["cag_assignment"]
                    or wpp_execution["spatial_population"]
                    or wpp_execution["population_arbitration"]
                    or wpp_execution["sampling"]
                    or wpp_execution["excursion"]
                )
                else []
            ),
            *(
                [{
                    "time": _now(),
                    "level": "Info",
                    "message": "Wafer unload between repeat runs is enabled",
                }]
                if setup.get("repeat_test")
                and setup.get("unload_wafer_in_repeat_mode")
                else []
            ),
            {"time": _now(), "level": "Info", "message": f"Inspection {status.lower()}; {len(defects)} defects detected"},
        ],
    }
    return result


def default_job(recipe: dict) -> dict:
    setup = default_run_setup(recipe)
    return {
        "id": uuid4().hex,
        "created": _now(),
        "inspection": recipe.get("inspection", ""),
        "recipe_id": recipe.get("id", ""),
        "inspection_ids": [recipe.get("id", "")],
        "primary_inspection_id": recipe.get("id", ""),
        "device": recipe.get("device", ""),
        "step": recipe.get("step", ""),
        "material_id": "",
        "cassette": "Port 1",
        "slots": [1],
        "slot_order": "Bottom Up",
        "slot_plans": [],
        "setup": setup,
        "status": "Waiting for Material",
        "remote": False,
        "material_associated": False,
        "run_log": [],
    }


def job_execution_plan(job: dict, recipes: list[dict]) -> list[dict]:
    by_id = {recipe.get("id"): recipe for recipe in recipes if recipe.get("id")}
    requested = [item for item in job.get("inspection_ids", []) if item in by_id]
    if not requested and job.get("recipe_id") in by_id:
        requested = [job["recipe_id"]]
    primary = job.get("primary_inspection_id")
    order = ([primary] if primary in requested else []) + [item for item in requested if item != primary]
    plans = list(job.get("slot_plans") or [])
    if not plans:
        plans = [
            {
                "slot": slot,
                "wafer_id": "",
                "repeat_count": int(job.get("setup", {}).get("repeat_count", 1)),
                "inspection_ids": order,
                "tests": {},
            }
            for slot in job.get("slots", [])
        ]
    slot_order = job.get("slot_order", "Bottom Up")
    if not job.get("remote") and slot_order in ("Top Down", "Bottom Up"):
        plans.sort(key=lambda item: int(item.get("slot", 0)), reverse=slot_order == "Top Down")
    execution = []
    for plan in plans:
        selected = [item for item in plan.get("inspection_ids", order) if item in order]
        selected = [item for item in order if item in selected]
        for recipe_id in selected:
            recipe = by_id[recipe_id]
            tests = (plan.get("tests") or {}).get(recipe_id)
            execution.append({
                "slot": int(plan.get("slot", 0)),
                "wafer_id": str(plan.get("wafer_id", "")),
                "repeat_count": max(1, int(plan.get("repeat_count", 1))),
                "recipe_id": recipe_id,
                "inspection": recipe.get("inspection", ""),
                "primary": recipe_id == primary,
                "selected_tests": list(tests or _test_names(recipe)),
                "lot_id": str((job.get("lot_ids") or {}).get(recipe_id, job.get("setup", {}).get("lot_id", ""))),
            })
    return execution

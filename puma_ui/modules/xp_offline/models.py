from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from uuid import uuid4


REQUIRED_AUTOLEARN_STEPS = (
    "Wafer Center Find",
    "Auto Alignment Sites Selection",
    "Auto Registration",
)
OPTIONAL_AUTOLEARN_STEPS = ("Auto Retrain Fourier Filter", "Auto Retrain Light")


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def default_xp_state() -> dict:
    return {
        "offline_setup_enabled": True,
        "rds_enabled": True,
        "rds_versions": [],
        "distribution_events": [],
        "manual_assist": {
            "fix_errors": True,
            "verify_results": True,
            "fix_timeout_minutes": 0,
            "verify_timeout_minutes": 0,
            "save_engineering_on_abort": True,
            "signal_tower_enabled": True,
        },
    }


def normalized_xp_state(value=None) -> dict:
    state = default_xp_state()
    if isinstance(value, dict):
        state.update({key: deepcopy(item) for key, item in value.items() if key in state})
        if isinstance(value.get("manual_assist"), dict):
            state["manual_assist"].update(value["manual_assist"])
    state["offline_setup_enabled"] = bool(state["offline_setup_enabled"])
    state["rds_enabled"] = bool(state["rds_enabled"])
    state["rds_versions"] = [item for item in state.get("rds_versions", []) if isinstance(item, dict)]
    state["distribution_events"] = [item for item in state.get("distribution_events", []) if isinstance(item, dict)]
    assist = state["manual_assist"]
    for key in ("fix_errors", "verify_results", "save_engineering_on_abort", "signal_tower_enabled"):
        assist[key] = bool(assist.get(key, state["manual_assist"].get(key, False)))
    for key in ("fix_timeout_minutes", "verify_timeout_minutes"):
        try:
            assist[key] = max(0, min(1440, int(assist.get(key, 0))))
        except (TypeError, ValueError):
            assist[key] = 0
    return state


def active_registration_sites(recipe: dict) -> list[dict]:
    xp = recipe.get("xp_offline") or {}
    sites = xp.get("registration_sites") or recipe.get("registration_sites") or []
    return [deepcopy(site) for site in sites if isinstance(site, dict) and site.get("active", True)]


def validate_base_recipe(recipe: dict) -> list[str]:
    errors = []
    if not (recipe.get("wafer_map") or {}).get("die_pattern_defined"):
        errors.append("Base recipe requires defined wafer-map die values.")
    if not (recipe.get("alignment") or {}).get("sites_defined"):
        errors.append("Base recipe requires alignment sites.")
    if not active_registration_sites(recipe):
        errors.append("Base recipe requires at least one active registration site.")
    return errors


def make_registration_site(name: str, x_um: float, y_um: float, layer: str = "") -> dict:
    clean_name = str(name).strip()
    if not clean_name:
        raise ValueError("Registration site name is required.")
    return {
        "id": uuid4().hex,
        "name": clean_name,
        "layer": str(layer).strip(),
        "x_um": float(x_um),
        "y_um": float(y_um),
        "active": True,
        "low_mag_optics": {"pixel_size": 2.0, "illumination": 100, "focus_offset_um": 0.0},
        "high_mag_optics": {"pixel_size": 0.1, "illumination": 100, "focus_offset_um": 0.0},
    }


def generated_recipe_name(pattern: str, base: dict, layer: str) -> str:
    values = {
        "BaseRecipe": str(base.get("inspection", "Base")),
        "Device": str(base.get("device", "Device")),
        "Layer": str(layer),
    }
    result = str(pattern or "{Device}_{Layer}")
    for token, value in values.items():
        result = result.replace("{" + token + "}", value)
    return result.strip() or f"{values['Device']}_{values['Layer']}"


def autofill_layer(layer: dict, source_recipes: list[dict]) -> dict:
    result = deepcopy(layer)
    source = next((item for item in source_recipes if item.get("step") == result.get("layer")), None)
    if source:
        result["source_recipe_id"] = source.get("id", "")
        result["laser_sensitivity"] = bool((source.get("wafer_properties") or {}).get("laser_power_sensitive"))
        result["sensitivity_source"] = "Auto Fill"
        result["data_analysis_source"] = "Auto Fill"
        result["source_found"] = True
    else:
        result["source_found"] = False
    return result


def generate_autolearn_recipes(
    base_recipe: dict,
    layers: list[dict],
    *,
    naming_pattern: str = "{Device}_{Layer}",
    mode: str = "Production",
    destination: str = "Local",
) -> list[dict]:
    errors = validate_base_recipe(base_recipe)
    if errors:
        raise ValueError("\n".join(errors))
    if mode not in {"Production", "Hot Scan", "OSTS"}:
        raise ValueError("Unknown AutoDerivative mode.")
    output = []
    seen = set()
    for layer in layers:
        layer_name = str(layer.get("layer", "")).strip()
        if not layer_name:
            raise ValueError("Every generated recipe requires a layer name.")
        name = generated_recipe_name(naming_pattern, base_recipe, layer_name)
        if name.casefold() in seen:
            raise ValueError(f"Duplicate generated recipe name: {name}")
        seen.add(name.casefold())
        recipe = deepcopy(base_recipe)
        recipe.update({
            "id": uuid4().hex,
            "inspection": name,
            "step": layer_name,
            "recipe_type": "AutoLearn-Ready",
            "auto_learn": "Ready",
            "status": "Valid",
            "state": "Valid for Run; AutoLearn steps pending.",
            "approval": "Engineering",
            "source": "rds" if destination == "RDS" else "local",
            "date_created": _now(),
            "last_modified": _now(),
            "dirty": True,
        })
        recipe["xp_offline"] = {
            "mode": mode,
            "base_recipe_id": base_recipe.get("id", ""),
            "source_recipe_id": layer.get("source_recipe_id", ""),
            "registration_sites": active_registration_sites(base_recipe),
            "autolearn_steps": list(REQUIRED_AUTOLEARN_STEPS) + [
                step for step in OPTIONAL_AUTOLEARN_STEPS if layer.get(step, False)
            ],
            "laser_sensitivity": bool(layer.get("laser_sensitivity", False)),
            "laser_power_factor": float(layer.get("laser_power_factor", 1.0)),
            "sensitivity_source": layer.get("sensitivity_source", "Use Base Recipe"),
            "data_analysis_source": layer.get("data_analysis_source", "Use Base Recipe"),
            "generation_status": "Valid for Run",
        }
        if mode == "OSTS":
            recipe["xp_offline"]["osts_enabled"] = True
        if mode == "Hot Scan":
            recipe["xp_offline"]["save_locally"] = True
        output.append(recipe)
    return output


def complete_autolearn(recipe: dict, *, successful: bool, manual_assist: dict | None = None) -> dict:
    result = deepcopy(recipe)
    assist = normalized_xp_state({"manual_assist": manual_assist or {}})["manual_assist"]
    xp = result.setdefault("xp_offline", {})
    if successful:
        result["recipe_type"] = "Normal"
        result["auto_learn"] = "Complete"
        result["status"] = "Valid"
        result["state"] = "AutoLearn completed. Inspection result verification is pending." if assist["verify_results"] else "AutoLearn completed."
        xp["manual_assist_state"] = "Verify Results" if assist["verify_results"] else "Complete"
    elif assist["fix_errors"] and assist["signal_tower_enabled"]:
        result["status"] = "Incomplete"
        result["state"] = "AutoLearn paused for Manual Assist."
        xp["manual_assist_state"] = "Fix AutoLearn Errors"
    else:
        result["status"] = "Incomplete"
        result["state"] = "AutoLearn failed."
        xp["manual_assist_state"] = "Aborted"
    result["dirty"] = True
    return result


def rds_check_in(state: dict, recipe: dict, *, user: str, production_approved=False) -> tuple[dict, dict]:
    result = normalized_xp_state(state)
    matching = [item for item in result["rds_versions"] if item.get("inspection") == recipe.get("inspection")]
    version = max([int(item.get("version", 0)) for item in matching] or [0]) + 1
    entry = {
        "id": uuid4().hex,
        "inspection": recipe.get("inspection", ""),
        "device": recipe.get("device", ""),
        "layer": recipe.get("step", ""),
        "version": version,
        "production_approved": bool(production_approved),
        "changed_by": str(user or "Unknown"),
        "timestamp": _now(),
        "recipe": deepcopy(recipe),
    }
    result["rds_versions"].append(entry)
    return result, deepcopy(entry)


def distribute_rds_recipe(state: dict, version_id: str, destinations: list[str]) -> dict:
    result = normalized_xp_state(state)
    version = next((item for item in result["rds_versions"] if item.get("id") == version_id), None)
    if not version:
        raise ValueError("Select a valid RDS recipe version.")
    if not destinations:
        raise ValueError("Select at least one destination tool.")
    result["distribution_events"].append({
        "id": uuid4().hex,
        "version_id": version_id,
        "inspection": version.get("inspection", ""),
        "destinations": [str(item) for item in destinations],
        "timestamp": _now(),
        "status": "Distributed (simulated)",
    })
    return result


def flatten_recipe(recipe: dict) -> dict[str, object]:
    output = {}

    def walk(value, path):
        if isinstance(value, dict):
            for key in sorted(value):
                if key not in {"id", "path", "date_created", "last_modified", "dirty"}:
                    walk(value[key], path + [str(key)])
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, path + [str(index)])
        elif isinstance(value, (str, int, float, bool)) or value is None:
            output[" / ".join(path)] = value

    walk(recipe, [])
    return output


def compare_recipes(recipes: list[dict], reference_id: str = "") -> list[dict]:
    if not recipes:
        return []
    reference = next((item for item in recipes if item.get("id") == reference_id), recipes[0])
    flattened = {item.get("id", str(index)): flatten_recipe(item) for index, item in enumerate(recipes)}
    reference_values = flattened.get(reference.get("id"), flatten_recipe(reference))
    rows = []
    for parameter in sorted(set().union(*(values.keys() for values in flattened.values()))):
        values = [flattened.get(item.get("id", ""), {}).get(parameter) for item in recipes]
        expected = reference_values.get(parameter)
        rows.append({
            "parameter": parameter,
            "category": parameter.split(" / ", 1)[0],
            "values": values,
            "different": [value != expected for value in values],
        })
    return rows


def set_recipe_parameter(recipe: dict, parameter: str, value) -> dict:
    result = deepcopy(recipe)
    parts = [part for part in parameter.split(" / ") if part]
    if not parts:
        raise ValueError("Parameter path is required.")
    cursor = result
    for part in parts[:-1]:
        if isinstance(cursor, list):
            cursor = cursor[int(part)]
        else:
            cursor = cursor[part]
    final = parts[-1]
    if isinstance(cursor, list):
        cursor[int(final)] = value
    else:
        cursor[final] = value
    result["dirty"] = True
    return result

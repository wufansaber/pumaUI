from __future__ import annotations

import sys
from copy import deepcopy
from pathlib import Path

from .modules.design_based_binning import normalized_dbb_state
from .modules.inspection_tests import default_test
from .modules.lot_plan import default_lot_plan_state
from .modules.run_control import default_run_setup, generate_inspection_result
from .modules.wafer_post_processing import default_wpp_state


DEMO_RECIPE_ID = "puma-demo-recipe"
DEMO_RECIPE_NAME = "PUMA_9980_VALIDATION"
DEMO_COMPONENT_FILENAME = "PUMA_9980_FULL_SETUP"
DEMO_CONTENT_VERSION = 2
DEMO_RESULT_IDS = ("puma-demo-result-w01", "puma-demo-result-w02")


def bundled_demo_root() -> Path:
    """Return the source or PyInstaller location for read-only demo assets."""
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        return Path(frozen_root) / "demo_data"
    return Path(__file__).resolve().parent.parent / "demo_data"


def _demo_alignment() -> dict:
    return {
        "mode": "DF",
        "sites_defined": True,
        "trained": True,
        "aligned": True,
        "status": "Valid",
        "site_coordinates": [[-92000.0, -86000.0], [91000.0, 87000.0]],
        "site_images": ["Low Mag Site 1", "High Mag Site 1"],
        "quality_scores": {
            "correlation": 98.4,
            "uniqueness": 99.1,
            "sharpness": 97.8,
            "features": 99.0,
        },
    }


def _demo_wafer_map() -> dict:
    return {
        "die_pattern_defined": True,
        "die_value_mode": "wafer_map",
        "die_pitch_width": 5100.1,
        "die_pitch_height": 16600.2,
        "die_count": 724,
        "scribe_lines_defined": True,
        "scribe_x": 99.9,
        "scribe_y": 100.2,
        "invalid_die": [],
        "origin_die": [29, 9],
        "allow_partial_die": True,
        "reticle_qualification": True,
        "reticle_width": 3,
        "reticle_height": 1,
        "reference_die": [29, 9],
        "inner_die_rows": 1,
        "inner_die_columns": 1,
        "inner_die_defined": False,
        "klarf_die_basis": "Recipe Die",
        "klarf_orientation": "As Inspected",
        "die_corner_adjustment_required": False,
        "adjust_die_corner_mode": "",
        "adjusted_die_corner": [29, 9],
    }


def prepare_loaded_recipe(recipe: dict) -> dict:
    """Hydrate missing legacy recipe sections without replacing stored setup data."""
    prepared = deepcopy(recipe)
    orientation = "Down (180 deg.)"
    wafer_properties = prepared.setdefault("wafer_properties", {})
    wafer_properties.setdefault("orientation", orientation)
    wafer_properties.setdefault("type", "Patterned")
    wafer_properties.setdefault("diameter_mm", 300)
    wafer_properties.setdefault("laser_power_sensitive", False)
    wafer_properties.setdefault("laser_power_factor", 0.035)
    wafer_properties.setdefault("layer", prepared.get("step", "Layer1"))
    wafer_properties.setdefault("dark_wafer_auto_focus", False)
    wafer_properties.setdefault("wafer_darkness_level", 0)

    if not prepared.get("alignment"):
        prepared["alignment"] = _demo_alignment()
    if not prepared.get("wafer_map"):
        prepared["wafer_map"] = _demo_wafer_map()

    if not any(test.get("mode") != "No Test" for test in prepared.get("tests", [])):
        test = default_test(1, wafer_properties["type"], wafer_properties["orientation"])
        valid_recipe = prepared.get("status") == "Valid"
        test["status"] = "Valid" if valid_recipe else "Incomplete"
        test["save_image_patches"] = True
        test["fourier_trained"] = valid_recipe
        test["light_trained"] = valid_recipe
        test["care_areas"]["groups"] = [
            {
                "name": "Full Die",
                "kind": "DCA",
                "threshold": "Default",
                "status": "OK",
                "enabled": True,
                "cag_code": 1,
                "show": True,
                "areas": [[0.05, 0.05, 0.90, 0.90]],
                "registered": True,
                "verified": True,
            }
        ]
        prepared["tests"] = [test]

    test_names = [
        test.get("name", f"Test {index + 1}")
        for index, test in enumerate(prepared["tests"])
        if test.get("mode") != "No Test"
    ]
    if not prepared.get("lot_plan"):
        lot_plan = default_lot_plan_state(test_names)
        lot_plan["assignments"] = {"1": list(test_names)}
        prepared["lot_plan"] = lot_plan
    prepared.setdefault("wafer_post_processing", default_wpp_state())

    active_orientation = str(prepared.get("active_setup_orientation", "180"))
    prepared["active_setup_orientation"] = active_orientation
    profiles = prepared.setdefault("orientation_setups", {})
    profiles.setdefault(
        active_orientation,
        {
            "alignment": deepcopy(prepared["alignment"]),
            "wafer_map": deepcopy(prepared["wafer_map"]),
        },
    )
    if prepared.get("status") == "Valid":
        for test in prepared.get("tests", []):
            if test.get("mode") == "No Test":
                continue
            orientation_text = str(test.get("orientation", active_orientation))
            digits = "".join(character for character in orientation_text if character.isdigit())
            orientation_key = str(int(digits or active_orientation) % 360)
            profiles.setdefault(
                orientation_key,
                {
                    "alignment": deepcopy(prepared["alignment"]),
                    "wafer_map": deepcopy(prepared["wafer_map"]),
                    "loaded_recipe_compatibility": True,
                },
            )
    prepared.setdefault("test_setup_valid", prepared.get("status") == "Valid")
    prepared.setdefault("simulation_defaults_applied", True)
    prepared["dirty"] = False
    return prepared


def demo_recipe() -> dict:
    recipe = prepare_loaded_recipe(
        {
            "id": DEMO_RECIPE_ID,
            "inspection": DEMO_RECIPE_NAME,
            "device": "PUMA-DEMO-300",
            "step": "METAL-1",
            "source": "local",
            "recent": True,
            "status": "Valid",
            "approval": "Engineering",
            "software_version": "9.8.306",
            "wafer_orientation": "180 deg",
            "auto_learn": "Yes",
            "recipe_filter": "All Recipes",
            "recipe_type": "Normal",
            "is_demo": True,
            "bundled_demo": True,
            "demo_content_version": DEMO_CONTENT_VERSION,
            "state": "Complete simulated recipe for setup, run, and Review validation.",
            "comments": "Bundled validation recipe. No production hardware data is used.",
            "path": str(bundled_demo_root() / "recipes" / DEMO_RECIPE_NAME),
        }
    )
    primary_test = recipe["tests"][0]
    primary_test["name"] = "Test 1 - Fourier"
    primary_test["optics_name"] = "DF-SL815 Validation"
    primary_test["channels"][0]["use_fourier_filter"] = True
    primary_test["fourier_trained"] = True
    primary_test["fourier"].update(
        {
            "training_die": [0, 0],
            "boxes": [
                {
                    "name": "Validation Box 1",
                    "x": 0.18,
                    "y": 0.20,
                    "width": 0.24,
                    "height": 0.18,
                    "channels": [1],
                }
            ],
            "analysis_valid": True,
            "trained": True,
        }
    )
    primary_test["light_training"].update(
        {
            "trained": True,
            "noise_box_group": "Full Die",
            "active_regions_enabled": False,
            "sample_dies": [[0, 0], [3, 2], [-3, -2]],
        }
    )

    direct_light_test = default_test(
        2,
        recipe["wafer_properties"]["type"],
        recipe["wafer_properties"]["orientation"],
    )
    direct_light_test.update(
        {
            "name": "Test 2 - Direct Light",
            "optics_name": "DF-SL815 Direct",
            "status": "Valid",
            "light_trained": True,
            "save_image_patches": True,
        }
    )
    direct_light_test["care_areas"]["groups"] = deepcopy(primary_test["care_areas"]["groups"])
    direct_light_test["light_training"].update(
        {
            "trained": True,
            "noise_box_group": "Full Die",
            "sample_dies": [[0, 0], [4, 1], [-4, -1]],
        }
    )
    recipe["tests"] = [primary_test, direct_light_test]

    test_names = [test["name"] for test in recipe["tests"]]
    lot_plan = default_lot_plan_state(test_names)
    lot_plan.update(
        {
            "assignments": {"1": list(test_names), "2": [test_names[0]]},
            "backup_lot_result": True,
            "protect": False,
        }
    )
    recipe["lot_plan"] = lot_plan
    recipe["run_setup"] = default_run_setup(recipe)
    recipe["run_setup"].update(
        {
            "lot_id": "PUMA_VALIDATION_LOT",
            "wafer_id": "W01",
            "selected_tests": list(test_names),
            "instant_review": True,
            "collect_sensitivity_data": True,
        }
    )
    recipe["defect_data"] = {
        "name": "PUMA_DEMO_LOT_W01.klarf",
        "path": str(bundled_demo_root() / "review" / "PUMA_DEMO_LOT_W01.klarf"),
        "source": "Bundled Demo Data",
        "lot_id": "PUMA_DEMO_LOT",
        "wafer_id": "W01",
        "defect_count": 8,
    }
    dbb = normalized_dbb_state(
        {
            "rdf_file": str(bundled_demo_root() / "design" / "PUMA_DEMO.rdf"),
            "rdf_device": "DEMO-300",
            "inspection_layer": "Metal-1",
            "registration_verified": True,
            "registered": True,
            "enabled": True,
            "dbc_enabled": True,
            "dbg_enabled": True,
            "dci_enabled": True,
            "pci_enabled": True,
            "design_attributes_enabled": True,
            "pattern_density_1": True,
            "dbc_bins": [
                {"name": "Pattern Defect", "class_code": 101, "nuisance": False},
                {"name": "Process Nuisance", "class_code": 901, "nuisance": True},
            ],
        }
    )
    recipe["dbb"] = dbb
    recipe["tests"][0]["run_dbb"] = True
    recipe["tests"][0]["dbb_classifier"] = {"name": "PUMA_DEMO_DBB", "type": "DBB"}
    return recipe


def ensure_demo_recipe(store, *, persist: bool = True) -> dict:
    """Install the bundled validation recipe without replacing operator edits."""
    existing = store.get_recipe(DEMO_RECIPE_ID)
    if existing is None:
        existing = next(
            (
                recipe for recipe in store.list_recipes()
                if recipe.get("inspection") == DEMO_RECIPE_NAME
            ),
            None,
        )
    if existing is None:
        existing = store.install_recipe_if_missing(
            demo_recipe(),
            event="Install Demo Recipe",
            detail="Bundled full-workflow validation recipe installed.",
            persist=persist,
        )

    component_source = demo_recipe()
    tests = component_source["tests"]
    components = {
        "Wafer Layout": deepcopy(component_source["wafer_map"]),
        "Alignment": deepcopy(component_source["alignment"]),
        "Data Analysis": deepcopy(component_source["wafer_post_processing"]),
        "Lot Plan": deepcopy(component_source["lot_plan"]),
        "Test 1": deepcopy(tests[0]),
        "1-Care Area": deepcopy(tests[0]["care_areas"]),
        "1-Sensitivity": deepcopy(tests[0]["sensitivity"]),
        "1-Sample Plan": deepcopy(tests[0]["sample_plan"]),
    }
    store.install_component_bundle_if_missing(
        DEMO_COMPONENT_FILENAME,
        component_source,
        components,
        persist=persist,
    )
    return existing


def ensure_demo_review_results(store) -> list[dict]:
    """Seed deterministic Review examples while preserving all operator results."""
    existing = {item.get("id"): item for item in store.list_results()}
    recipe = demo_recipe()
    review_test_name = recipe["tests"][0]["name"]
    review_path = bundled_demo_root() / "review"
    for index, result_id in enumerate(DEMO_RESULT_IDS, start=1):
        if existing.get(result_id, {}).get("demo_content_version") == DEMO_CONTENT_VERSION:
            continue
        setup = default_run_setup(recipe)
        setup.update(
            {
                "lot_id": "PUMA_DEMO_LOT",
                "wafer_id": f"W{index:02d}",
                "selected_tests": [review_test_name],
                "instant_review": True,
                "collect_sensitivity_data": True,
            }
        )
        result = generate_inspection_result(recipe, setup, repeat_index=index)
        result.update(
            {
                "id": result_id,
                "path": str(review_path),
                "source_format": "Puma Simulator Demo",
                "is_demo": True,
                "demo_content_version": DEMO_CONTENT_VERSION,
                "review_recent": index == 1,
                "dbb_recipe": deepcopy(recipe["dbb"]),
            }
        )
        store.save_result(result)
    return [
        item
        for item in store.list_results()
        if item.get("id") in DEMO_RESULT_IDS
    ]

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
VIRTUAL_RECIPE_ID = "vert-seg0123"
VIRTUAL_RECIPE_VERSION = 2
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


def _alignment_score(uniqueness, sharpness, features) -> dict:
    return {
        "type": "DF",
        "mode": "DF",
        "df_scores": "Align    X Reg    Y Reg",
        "uniqueness": uniqueness,
        "sharpness": sharpness,
        "features": features,
    }


def virtual_figure_recipe() -> dict:
    """Recipe whose overview and setup pages match the reference screenshots."""
    from .modules.inspection_tests.sensitivity import default_sensitivity_state

    test = default_test(1, "Patterned", "180°")
    test.update(
        {
            "name": "Test 1",
            "mode": "Random",
            "orientation": "Down (180 deg.)",
            "status": "Valid",
            "light_trained": True,
            "save_image_patches": True,
            "save_feature_vectors": True,
            "ido_classifier": None,
            "rbb_recipe": "",
            "focus_offset": 0,
            "fourier_trained": True,
        }
    )
    test["inspection_optics"].update(
        {
            "pixel_size": "SL815",
            "focus_offset": 0,
            "incident_polarization": "P-POL",
            "incidence_angle": "Oblique",
            "speed": "High Throughput Mode",
        }
    )
    channel_values = (
        ("1 (Left)", 8.6, 24.1),
        ("2 (Right)", 7.4, 23.1),
        ("3 (Center)", 2.3, 79.4),
    )
    for index, (name, light_level, pilo_noise) in enumerate(channel_values):
        test["channels"][index].update(
            {
                "name": name,
                "enabled": True,
                "polarization": "None",
                "iris": "OPEN",
                "light_level": light_level,
                "use_fourier_filter": True,
                "fourier_training_result": 0.0,
            }
        )
    test["light_training"].update(
        {
            "trained": True,
            "dynamic_range": "Extended",
            "noise_box_group": "",
            "channels": [
                {
                    "name": name,
                    "light_level": light_level,
                    "edr": 16.0,
                    "exposure": None,
                    "pilo_noise": pilo_noise,
                }
                for name, light_level, pilo_noise in channel_values
            ],
        }
    )
    test["care_areas"]["border"] = {"x": 10.0, "y": 5.0}
    test["care_areas"]["group_count"] = 5
    test["care_areas"]["die_size_um"] = [5100.1, 16600.2]
    test["care_areas"]["groups"] = [
        {
            "name": "R1",
            "kind": "Care Area",
            "threshold": "Default",
            "status": "OK",
            "enabled": True,
            "cag_code": 1,
            "show": True,
            "areas": [[0.42, 0.08, 0.16, 0.10]],
            "registered": True,
            "verified": True,
        },
        {
            "name": "R2",
            "kind": "Care Area",
            "threshold": "Default",
            "status": "OK",
            "enabled": True,
            "cag_code": 2,
            "show": True,
            "areas": [[0.40, 0.28, 0.18, 0.22]],
            "registered": True,
            "verified": True,
        },
        {
            "name": "R3",
            "kind": "Care Area",
            "threshold": "Default",
            "status": "OK",
            "enabled": True,
            "cag_code": 3,
            "show": True,
            "areas": [[0.55, 0.62, 0.08, 0.28]],
            "registered": True,
            "verified": True,
        },
        {
            "name": "R4",
            "kind": "Care Area",
            "threshold": "Default",
            "status": "OK",
            "enabled": True,
            "cag_code": 4,
            "show": True,
            "areas": [[0.12, 0.18, 0.20, 0.12]],
            "registered": True,
            "verified": True,
        },
        {
            "name": "R5",
            "kind": "Care Area",
            "threshold": "Default",
            "status": "OK",
            "enabled": True,
            "cag_code": 5,
            "show": True,
            "areas": [[0.68, 0.72, 0.14, 0.10]],
            "registered": True,
            "verified": True,
        },
    ]
    sensitivity = default_sensitivity_state(["R1", "R2", "R3"])
    sensitivity["defect_filters"] = {
        "run_process_noise_filter": False,
        "intensity": 0.0,
        "side_ratio": 0.0,
        "top_ratio": 0.0,
    }
    test["sensitivity"] = sensitivity
    test["segmentation"] = {"valid": True}
    test["sample_plan"]["inspection_type"] = "Full Die"
    test["sample_plan"]["total_inspectable_dies"] = 4180

    recipe = {
        "id": VIRTUAL_RECIPE_ID,
        "inspection": "Vert_Seg0123",
        "device": "Device1",
        "step": "Layer1",
        "source": "local",
        "recent": True,
        "date_created": "2011-03-31 23:49:06",
        "last_modified": "2011-09-01 09:27:57",
        "validation_date": "9/1/2011",
        "status": "Valid",
        "dirty": False,
        "approval": "Engineering",
        "software_version": "9.7.064",
        "recipe_type": "Normal",
        "recipe_filter": "All Recipes",
        "wafer_orientation": "180 deg",
        "auto_learn": "No",
        "is_virtual": True,
        "virtual_recipe_version": VIRTUAL_RECIPE_VERSION,
        "state": "The recipe successfully passed validation on 9/1/2011.",
        "path": r"D:\DATA\987KInspr0001\Usr\Recipes\Device1\Layer1\Vert_Seg0123",
        "wafer_properties": {
            "diameter": "300 mm",
            "diameter_mm": 300,
            "type": "Patterned",
            "orientation": "Down (180 deg.)",
            "align_mark": "Notched",
            "laser_power_sensitive": True,
            "laser_power_factor": "0.03500",
            "layer": "-",
            "dark_wafer_auto_focus": False,
            "wafer_darkness_level": "Level 1",
        },
        "alignment": {
            "mode": "DF",
            "sites_defined": True,
            "trained": True,
            "aligned": True,
            "status": "Valid",
            "scores": {
                "180": _alignment_score("83.3    55.0    100.0", "10.1    5.9    10.1", "98.8    98.8    98.8"),
                "90": _alignment_score("90.8    99.9    99.9", "37.8    8.9    37.8", "69.4    10.1    69.4"),
            },
        },
        "registration_sites": [],
        "wafer_map": {
            "die_pattern_defined": True,
            "status": "Valid",
            "die_layout_status": "Valid",
            "die_pitch_width": 5100.1,
            "die_pitch_height": 16600.2,
            "die_count": 724,
            "scribe_lines_defined": True,
            "scribe_x": 99.9,
            "scribe_y": 100.2,
            "reticle_qualification": False,
            "inner_die_defined": False,
            "die_corner_adjustment_required": False,
            "origin_die": [0, 0],
        },
        "tests": [test],
        "dbb": {"rdf_file": "", "registered": False, "enabled": False},
        "active_setup_orientation": "180",
    }
    return recipe


def ensure_virtual_figure_recipe(store, *, persist: bool = False) -> dict:
    """Install Vert_Seg0123 without replacing a newer copy already in the library."""
    recipe = virtual_figure_recipe()
    existing = store.get_recipe(VIRTUAL_RECIPE_ID)
    if existing and existing.get("virtual_recipe_version") == VIRTUAL_RECIPE_VERSION:
        return existing
    if existing is not None:
        store.delete_recipe(VIRTUAL_RECIPE_ID)
    return store.install_recipe_if_missing(
        recipe,
        event="Install Virtual Recipe",
        detail="Reference recipe Vert_Seg0123 installed.",
        persist=persist,
    )


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

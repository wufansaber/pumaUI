from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from puma_ui.modules.xp_offline import (
    ManualAssistDialog,
    RDSManagerDialog,
    RecipeComparatorDialog,
    RegistrationSiteLibraryDialog,
    XPRecipeGeneratorDialog,
    apply_component_to_recipe,
    assign_cag_codes,
    autofill_layer,
    compare_recipes,
    complete_autolearn,
    default_xp_state,
    distribute_rds_recipe,
    generate_autolearn_recipes,
    generated_recipe_name,
    generate_care_area_component,
    make_registration_site,
    normalized_xp_state,
    parse_config_csv,
    parse_mapping_csv,
    prune_component,
    register_component,
    rds_check_in,
    set_recipe_parameter,
    validate_base_recipe,
)
from puma_ui.qt_compat import QApplication, QDialog
from puma_ui.recipe_store import RecipeStore
from puma_ui.main_window import PumaMainWindow


def base_recipe():
    return {
        "id": "base-1",
        "inspection": "BaseRecipe",
        "device": "DeviceA",
        "step": "Base",
        "source": "local",
        "status": "Valid",
        "alignment": {"sites_defined": True},
        "wafer_map": {"die_pattern_defined": True},
        "xp_offline": {"registration_sites": [make_registration_site("CommonMark", 10, 20, "Base")]},
        "tests": [{"name": "Test 1", "light_level": 8.5}],
    }


class XPOfflineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = RecipeStore(Path(self.temp_dir.name) / "recipes.json")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_xp_state_normalizes_timeouts_and_lists(self):
        state = normalized_xp_state({"manual_assist": {"fix_timeout_minutes": -2, "verify_timeout_minutes": 5000}, "rds_versions": "bad"})
        self.assertEqual(state["manual_assist"]["fix_timeout_minutes"], 0)
        self.assertEqual(state["manual_assist"]["verify_timeout_minutes"], 1440)
        self.assertEqual(state["rds_versions"], [])

    def test_registration_site_requires_name_and_has_both_optics(self):
        with self.assertRaises(ValueError): make_registration_site("", 0, 0)
        site = make_registration_site("Site 1", 1.25, -2.5)
        self.assertEqual(site["low_mag_optics"]["pixel_size"], 2.0)
        self.assertEqual(site["high_mag_optics"]["pixel_size"], 0.1)

    def test_base_recipe_validation_covers_all_three_prerequisites(self):
        errors = validate_base_recipe({})
        self.assertEqual(len(errors), 3)
        self.assertEqual(validate_base_recipe(base_recipe()), [])

    def test_generated_name_uses_manual_tokens(self):
        self.assertEqual(generated_recipe_name("{BaseRecipe}-{Device}-{Layer}", base_recipe(), "Metal1"), "BaseRecipe-DeviceA-Metal1")

    def test_autofill_uses_matching_source_layer(self):
        source = {"id": "source", "step": "Metal1", "wafer_properties": {"laser_power_sensitive": True}}
        filled = autofill_layer({"layer": "Metal1"}, [source])
        self.assertTrue(filled["source_found"])
        self.assertTrue(filled["laser_sensitivity"])
        self.assertEqual(filled["data_analysis_source"], "Auto Fill")

    def test_generate_production_recipe_contains_required_steps(self):
        generated = generate_autolearn_recipes(base_recipe(), [{"layer": "Metal1", "Auto Retrain Light": True}])
        recipe = generated[0]
        self.assertEqual(recipe["recipe_type"], "AutoLearn-Ready")
        self.assertEqual(recipe["xp_offline"]["generation_status"], "Valid for Run")
        self.assertIn("Auto Registration", recipe["xp_offline"]["autolearn_steps"])
        self.assertIn("Auto Retrain Light", recipe["xp_offline"]["autolearn_steps"])

    def test_generate_osts_and_hot_scan_modes(self):
        layer = [{"layer": "Metal1"}]
        self.assertTrue(generate_autolearn_recipes(base_recipe(), layer, mode="OSTS")[0]["xp_offline"]["osts_enabled"])
        self.assertTrue(generate_autolearn_recipes(base_recipe(), layer, mode="Hot Scan")[0]["xp_offline"]["save_locally"])

    def test_generate_rejects_invalid_base_and_duplicate_names(self):
        with self.assertRaises(ValueError): generate_autolearn_recipes({}, [{"layer": "A"}])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            generate_autolearn_recipes(base_recipe(), [{"layer": "A"}, {"layer": "A"}])

    def test_autolearn_success_converts_to_normal_and_requests_verify(self):
        generated = generate_autolearn_recipes(base_recipe(), [{"layer": "Metal1"}])[0]
        completed = complete_autolearn(generated, successful=True, manual_assist={"verify_results": True})
        self.assertEqual(completed["recipe_type"], "Normal")
        self.assertEqual(completed["xp_offline"]["manual_assist_state"], "Verify Results")

    def test_autolearn_failure_pauses_only_when_assist_and_signal_are_enabled(self):
        generated = generate_autolearn_recipes(base_recipe(), [{"layer": "Metal1"}])[0]
        paused = complete_autolearn(generated, successful=False, manual_assist={"fix_errors": True, "signal_tower_enabled": True})
        aborted = complete_autolearn(generated, successful=False, manual_assist={"fix_errors": False})
        self.assertEqual(paused["xp_offline"]["manual_assist_state"], "Fix AutoLearn Errors")
        self.assertEqual(aborted["xp_offline"]["manual_assist_state"], "Aborted")

    def test_rds_check_in_increments_versions_and_preserves_snapshot(self):
        state, first = rds_check_in(default_xp_state(), base_recipe(), user="engineer", production_approved=True)
        state, second = rds_check_in(state, base_recipe(), user="expert")
        self.assertEqual((first["version"], second["version"]), (1, 2))
        self.assertTrue(first["production_approved"])
        self.assertEqual(first["recipe"]["inspection"], "BaseRecipe")

    def test_rds_distribution_requires_version_and_destinations(self):
        state, entry = rds_check_in(default_xp_state(), base_recipe(), user="engineer")
        with self.assertRaises(ValueError): distribute_rds_recipe(state, "missing", ["Puma-01"])
        with self.assertRaises(ValueError): distribute_rds_recipe(state, entry["id"], [])
        state = distribute_rds_recipe(state, entry["id"], ["Puma-01", "Puma-02"])
        self.assertEqual(state["distribution_events"][0]["status"], "Distributed (simulated)")

    def test_recipe_comparison_flags_differences(self):
        first = base_recipe(); second = base_recipe(); second["id"] = "base-2"; second["tests"][0]["light_level"] = 9.0
        rows = compare_recipes([first, second], "base-1")
        light = next(row for row in rows if row["parameter"] == "tests / 0 / light_level")
        self.assertEqual(light["different"], [False, True])

    def test_recipe_parameter_edit_marks_recipe_dirty(self):
        edited = set_recipe_parameter(base_recipe(), "tests / 0 / light_level", 9.25)
        self.assertEqual(edited["tests"][0]["light_level"], 9.25)
        self.assertTrue(edited["dirty"])

    def test_registration_site_dialog_round_trip(self):
        dialog = RegistrationSiteLibraryDialog(base_recipe())
        dialog.name.setText("Second"); dialog._add(); dialog._finish()
        self.assertEqual(dialog.result(), QDialog.Accepted)
        self.assertEqual(len(dialog.result_recipe["xp_offline"]["registration_sites"]), 2)

    def test_generator_dialog_saves_generated_recipes(self):
        base = self.store.save_recipe(base_recipe())
        dialog = XPRecipeGeneratorDialog(self.store, base)
        dialog.layer_name.setText("Metal1"); dialog._add_layer(); dialog._generate()
        self.assertEqual(dialog.result(), QDialog.Accepted)
        self.assertEqual(len(dialog.generated_recipes), 1)
        self.assertTrue(any(item["recipe_type"] == "AutoLearn-Ready" for item in self.store.list_recipes()))

    def test_manual_assist_and_rds_dialogs_persist_result_state(self):
        recipe = generate_autolearn_recipes(base_recipe(), [{"layer": "Metal1"}])[0]
        assist = ManualAssistDialog(default_xp_state(), recipe); assist.outcome.setCurrentIndex(1); assist._finish()
        self.assertEqual(assist.result_recipe["recipe_type"], "Normal")
        rds = RDSManagerDialog(self.store, base_recipe(), default_xp_state()); rds._check_in(); rds._finish()
        self.assertEqual(len(rds.result_state["rds_versions"]), 1)

    def test_recipe_comparator_dialog_loads_selected_recipes(self):
        first = base_recipe(); second = base_recipe(); second["id"] = "base-2"; second["inspection"] = "Other"
        dialog = RecipeComparatorDialog([first, second])
        dialog.available.selectAll(); dialog._load()
        self.assertEqual(len(dialog.loaded_recipes), 2)
        self.assertGreater(dialog.comparison.rowCount(), 0)

    def test_gds2ca_mapping_csv_parses_manual_columns(self):
        rows = parse_mapping_csv("GDS Layer,Data Type,CAG Name,Region ID,CAG Code,Type,Priority\n10,2,Gate,3,42,DCA,1\n")
        self.assertEqual(rows[0]["gds_layer"], 10)
        self.assertEqual(rows[0]["cag_code"], 42)
        self.assertEqual(rows[0]["kind"], "DCA")

    def test_gds2ca_mapping_rejects_out_of_range_code(self):
        with self.assertRaisesRegex(ValueError, "32000"):
            parse_mapping_csv("CAG Name,CAG Code\nGate,32001\n")

    def test_gds2ca_config_collects_registration_clips(self):
        config = parse_config_csv("Orientation,90\nRegistrationClip1,site-a.png\nRegistrationClip2,site-b.png\nRegistrationLayer,7\n")
        self.assertEqual(config["orientation"], "90")
        self.assertEqual(config["registration_clips"], ["site-a.png", "site-b.png"])

    def test_component_requires_mapping_unless_default_data_is_used(self):
        with self.assertRaises(ValueError): generate_care_area_component(b"gds", None, None)
        component = generate_care_area_component(b"gds", use_default_data=True, source_name="layout.gds")
        self.assertEqual(component["groups"][0]["name"], "Default")

    def test_component_generation_is_traceable_and_unregistered(self):
        mapping = parse_mapping_csv("CAG Name,CAG Code\nGate,5\n")
        component = generate_care_area_component(b"binary-layout", mapping, {})
        self.assertEqual(len(component["source_sha256"]), 64)
        self.assertEqual(component["groups"][0]["status"], "V*R*")

    def test_two_point_registration_calculates_scale_and_status(self):
        component = generate_care_area_component(b"gds", use_default_data=True)
        registered, warning = register_component(component, [(0, 0), (10, 0)], [(5, 5), (16, 5)])
        self.assertAlmostEqual(registered["registration"]["scale"], 1.1)
        self.assertEqual(registered["groups"][0]["status"], "V*R")
        self.assertTrue(warning)

    def test_registration_rejects_coincident_sites(self):
        component = generate_care_area_component(b"gds", use_default_data=True)
        with self.assertRaisesRegex(ValueError, "distinct"):
            register_component(component, [(0, 0), (0, 0)], [(1, 1), (2, 2)])

    def test_prune_reports_rectangles_outside_inspectable_die(self):
        component = generate_care_area_component(b"gds", use_default_data=True)
        component["groups"][0]["areas"].append([-0.1, 0.2, 0.2, 0.2])
        pruned, removed = prune_component(component)
        self.assertEqual(removed["Default"], 1)
        self.assertEqual(len(pruned["groups"][0]["areas"]), 1)

    def test_cag_code_assignment_supports_sequential_values(self):
        groups = [{"name": "A", "cag_code": 1}, {"name": "B", "cag_code": 2}]
        assigned = assign_cag_codes(groups, ["A", "B"], 100, sequential=True)
        self.assertEqual([item["cag_code"] for item in assigned], [100, 101])
        with self.assertRaises(ValueError): assign_cag_codes(groups, ["A"], 0)

    def test_component_import_updates_selected_tests(self):
        recipe = base_recipe(); recipe["tests"].append({"name": "Test 2"})
        component = generate_care_area_component(b"gds", use_default_data=True)
        updated = apply_component_to_recipe(recipe, component, [1])
        self.assertNotIn("care_areas", updated["tests"][0])
        self.assertEqual(updated["tests"][1]["care_areas"]["groups"][0]["name"], "Default")

    def test_main_window_exposes_xp_and_gds2ca_menu_entries(self):
        window = PumaMainWindow()
        labels = {action.text() for action in window.findChildren(type(window.user_manual_action))}
        self.assertIn("Recipe Generation...", labels)
        self.assertIn("Recipe Comparator...", labels)
        self.assertIn("Recipe Distribution System...", labels)
        self.assertIn("GDS2CA Converter...", labels)
        self.assertIn("CAG Editor...", labels)
        window.close()


if __name__ == "__main__":
    unittest.main()

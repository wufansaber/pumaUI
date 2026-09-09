from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from puma_ui.main_window import PumaMainWindow
from puma_ui.modules.design_based_binning import (
    DBBSetupDialog,
    DBBAnalysisToolboxDialog,
    DBBViewDialog,
    DBCBinPropertiesDialog,
    POIViewDialog,
    clear_dbb_attributes,
    DBCSetupDialog,
    DesignRegistrationDialog,
    add_clip_examples,
    add_dbc_bin,
    create_dbc_library,
    dbb_folder_counts,
    execute_dbb_analysis,
    move_dbc_examples,
    parse_hotspot_csv,
    sample_dbb_defects,
    save_dbc_library_as,
    scoped_defects,
    default_dbb_state,
    normalized_dbb_state,
    validate_dbb_setup,
    validate_design_registration,
)
from puma_ui.modules.results_review import ReviewWorkspace
from puma_ui.modules.run_control import generate_inspection_result
from puma_ui.qt_compat import QApplication, QDialog
from puma_ui.recipe_store import RecipeStore


class DesignBasedBinningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_normalization_enforces_manual_ranges(self):
        state = normalized_dbb_state({
            "dbg_similarity": 500,
            "dbg_seed_window_nm": 5000,
            "dbg_stop_group_count": 50000,
            "transfer_clip_limit": 999,
            "sampling": {"maximum": 90000, "max_per_cluster": 1, "max_cluster_percent": 120},
        })
        self.assertEqual(state["dbg_similarity"], 100)
        self.assertEqual(state["dbg_stop_group_count"], 25000)
        self.assertEqual(state["transfer_clip_limit"], 200)
        self.assertEqual(state["sampling"]["maximum"], 65000)
        self.assertEqual(state["sampling"]["max_per_cluster"], 2)
        self.assertEqual(state["sampling"]["max_cluster_percent"], 100)
        self.assertEqual(state["dbg_seed_window_nm"], 1000)

    def test_setup_validation_rejects_invalid_advanced_dependencies(self):
        state = default_dbb_state()
        state.update({"enabled": True, "registered": True, "dbg_filter_enabled": True})
        self.assertIn("Enable DBG before applying a DBB filter-out rule", validate_dbb_setup(state))
        state.update({"dbg_enabled": True, "supergrouping_enabled": True})
        self.assertIn("Supergrouping is available only when DBG1 is enabled", validate_dbb_setup(state))
        state["sampling"].update({"minimum_defect_size": 5, "maximum_defect_size": 2})
        self.assertIn("Minimum defect size cannot exceed maximum defect size", validate_dbb_setup(state))

    def test_registration_requires_active_server_rdf_and_layer(self):
        state = default_dbb_state()
        state["server_status"] = "Inactive"
        errors = validate_design_registration(state)
        self.assertIn("DBB Design Services must be active", errors)
        self.assertIn("Select a Reticle Design File (RDF)", errors)
        self.assertIn("Select an inspection layer", errors)

    def test_manual_registration_requires_two_distant_site_sets_and_verification(self):
        state = default_dbb_state()
        state.update({
            "rdf_file": "Device1.rdf",
            "inspection_layer": "Metal1",
            "strategy": "Manual",
            "rdf_sites": [(0, 0), (500, 500)],
            "low_mag_sites": [(0, 0), (500, 500)],
            "high_mag_sites": [(0, 0), (500, 500)],
            "registration_verified": True,
        })
        self.assertEqual(validate_design_registration(state), [])
        state["low_mag_sites"][1] = (2, 2)
        self.assertIn("Registration sites must be far apart diagonally", validate_design_registration(state))

    def test_semi_auto_with_design_pitch_accepts_one_site_set(self):
        state = default_dbb_state()
        state.update({
            "rdf_file": "Device1.rdf",
            "inspection_layer": "Metal1",
            "design_pitch_width_um": 5100,
            "design_pitch_height_um": 16500,
            "rdf_sites": [(0, 0)],
            "low_mag_sites": [(0, 0)],
            "high_mag_sites": [(0, 0)],
            "registration_verified": True,
        })
        self.assertEqual(validate_design_registration(state), [])

    def test_offsets_and_scales_path_does_not_require_sites(self):
        state = default_dbb_state()
        state.update({
            "rdf_file": "Device1.rdf",
            "inspection_layer": "Metal1",
            "strategy": "Design Offsets and Scales",
            "scale_x": 1.0001,
            "scale_y": 0.9999,
            "registration_verified": True,
        })
        self.assertEqual(validate_design_registration(state), [])

    def test_dbb_setup_requires_registration_and_dbc_library(self):
        state = default_dbb_state()
        state.update({"enabled": True, "dbc_enabled": True})
        errors = validate_dbb_setup(state)
        self.assertIn("Complete Design Registration before enabling DBB", errors)
        self.assertIn("Select a DBC Library", errors)

    def test_sampling_allocations_cannot_exceed_maximum(self):
        state = default_dbb_state()
        state.update({"enabled": True, "registered": True})
        state["sampling"].update({"maximum": 100, "dbc_size": 70, "dbg_systematic_size": 40})
        self.assertIn("DBB sampling allocations exceed the maximum sample size", validate_dbb_setup(state))

    def test_registration_dialog_marks_verifies_and_finishes(self):
        dialog = DesignRegistrationDialog(recipe_device="Device1")
        self.assertFalse(dialog.tabs.isTabEnabled(1))
        dialog.rdf_file.setText("Device1.rdf")
        self.assertTrue(dialog.tabs.isTabEnabled(1))
        dialog.inspection_layer.setCurrentText("Metal1")
        dialog.strategy.setCurrentText("Manual")
        for key in ("rdf_sites", "rdf_sites", "low_mag_sites", "low_mag_sites", "high_mag_sites", "high_mag_sites"):
            dialog._mark(key)
        dialog._verify()
        dialog._finish()
        self.assertTrue(dialog.result_state["registered"])
        self.assertTrue(dialog.result_state["registration_verified"])

    def test_registration_status_uses_strategy_site_count(self):
        dialog = DesignRegistrationDialog({"rdf_file": "Device1.rdf"})
        dialog.pitch_width.setValue(5100)
        dialog.pitch_height.setValue(16500)
        self.assertIn("Required site sets: 1", dialog.site_status.text())
        dialog.strategy.setCurrentText("Design Offsets and Scales")
        self.assertIn("Required site sets: 0", dialog.site_status.text())

    def test_dbb_setup_and_dbc_examples_are_persistable(self):
        state = default_dbb_state()
        state.update({"registered": True, "rdf_file": "Device1.rdf", "inspection_layer": "Metal1"})
        dbc = DBCSetupDialog(state)
        dbc._add_example("RDF HotSpot")
        dbc._create_bin()
        dbc._finish()
        self.assertEqual(dbc.result_state["dbc_examples"][0]["bin"], "DBC Bin 1")
        setup = DBBSetupDialog(dbc.result_state)
        setup.enabled.setChecked(True)
        setup.dbc_enabled.setChecked(True)
        setup.dbc_library.setText("Metal1.dbc")
        setup.dbg_enabled.setChecked(True)
        setup.filter_enabled.setChecked(True)
        setup.filter_attribute.setCurrentText("DCI")
        setup.sample_random.setChecked(True)
        setup.minimum_defect_size.setValue(0.25)
        setup._finish()
        self.assertTrue(setup.result_state["enabled"])
        self.assertEqual(setup.result_state["dbc_library"], "Metal1.dbc")
        self.assertTrue(setup.result_state["dci_enabled"])
        self.assertTrue(setup.result_state["sampling"]["dbg_random_enabled"])
        self.assertEqual(setup.result_state["sampling"]["minimum_defect_size"], 0.25)
        self.assertEqual(setup.tabs.count(), 4)

    def test_setup_disables_inactive_dbb_sampling_controls(self):
        setup = DBBSetupDialog({"registered": True})
        self.assertFalse(setup.sample_dbc_size.isEnabled())
        self.assertFalse(setup.systematic_scheme.isEnabled())
        self.assertFalse(setup.random_scheme.isEnabled())
        self.assertFalse(setup.maximum_defect_size.isEnabled())
        setup.sample_dbc.setChecked(True)
        setup.sample_systematic.setChecked(True)
        setup.sample_random.setChecked(True)
        setup.sample_limits.setChecked(True)
        self.assertTrue(setup.sample_dbc_size.isEnabled())
        self.assertTrue(setup.systematic_scheme.isEnabled())
        self.assertTrue(setup.random_scheme.isEnabled())
        self.assertTrue(setup.maximum_defect_size.isEnabled())

    def test_main_window_design_actions_follow_manual_prerequisites(self):
        with tempfile.TemporaryDirectory() as directory:
            store = RecipeStore(Path(directory) / "recipes.json")
            with patch("puma_ui.main_window.RecipeStore", return_value=store):
                window = PumaMainWindow()
            self.assertTrue(window.design_registration_action.isEnabled())
            with patch("puma_ui.main_window.QMessageBox.warning") as warning:
                window.design_registration_action.trigger()
            warning.assert_called_once()
            recipe = store.new_recipe()
            recipe["alignment"] = {"sites_defined": True}
            recipe["wafer_map"] = {
                "die_pattern_defined": True,
                "reticle_qualification": True,
            }
            window._set_current_recipe(recipe)
            self.assertTrue(window.design_registration_action.isEnabled())
            self.assertTrue(window.dbb_setup_action.isEnabled())
            recipe["dbb"] = {"registered": True}
            window._set_current_recipe(recipe)
            self.assertTrue(window.dbc_setup_action.isEnabled())
            self.assertTrue(window.dbb_setup_action.isEnabled())
            window.close()

    def test_run_generates_design_attributes_and_enforces_clip_limit(self):
        dbb = default_dbb_state()
        dbb.update({
            "enabled": True,
            "registered": True,
            "rdf_file": "Device1.rdf",
            "inspection_layer": "Metal1",
            "dbc_enabled": True,
            "dbg_enabled": True,
            "dci_enabled": True,
            "pci_enabled": True,
            "design_attributes_enabled": True,
            "pattern_density_1": True,
            "transfer_clip_images": True,
            "dbc_bins": [{"name": "Contact", "class_code": 120}],
        })
        dbb["sampling"]["maximum"] = 65000
        recipe = {
            "id": "dbb-run",
            "inspection": "Deep",
            "device": "Device1",
            "step": "Metal1",
            "tests": [{"name": "Test 1"}],
            "dbb": dbb,
        }
        result = generate_inspection_result(
            recipe,
            {"lot_id": "DBB-LOT", "wafer_id": "W01", "selected_tests": ["Test 1"]},
        )
        defect = result["defects"][0]
        self.assertEqual(defect["dbc_bin"], "Contact")
        self.assertIn("dbg_group", defect)
        self.assertIn("dci", defect)
        self.assertIn("pci", defect)
        self.assertIn("pattern_density", defect)
        self.assertIn("dci_range", defect)
        self.assertIn("line_complexity", defect)
        self.assertIn("floor_plan_id", defect)
        self.assertEqual(defect["dbb_global_bin"], 1)
        self.assertTrue(defect["dbb_sampled"])
        self.assertTrue(result["dbb_execution"]["enabled"])
        self.assertLessEqual(result["dbb_execution"]["clips"], 200)

    def test_review_enables_design_tab_and_tracks_selected_defect(self):
        dbb = default_dbb_state()
        dbb.update({
            "enabled": True,
            "registered": True,
            "rdf_file": "Device1.rdf",
            "inspection_layer": "Metal1",
            "dbg_enabled": True,
        })
        recipe = {
            "id": "dbb-review",
            "inspection": "Deep",
            "device": "Device1",
            "step": "Metal1",
            "tests": [{"name": "Test 1"}],
            "dbb": dbb,
        }
        result = generate_inspection_result(
            recipe,
            {"lot_id": "DBB-LOT", "wafer_id": "W01", "selected_tests": ["Test 1"]},
        )
        review = ReviewWorkspace(result, current_recipe=recipe)
        self.assertTrue(review.map_tabs.isTabEnabled(1))
        review._select_id(result["defects"][0]["id"])
        self.assertIn("Design position", review.design_details.text())
        self.assertIn("DBB Global Bin", review.design_details.text())
        self.assertEqual(len(review.image_widgets), 4)
        self.assertTrue(review.grab_dbb_clips.isEnabled())
        self.assertGreaterEqual(review.chart_dimension.findText("DBB Global Bin"), 0)
        self.assertIn("dbg_similarity", review.grid_columns)
        review.close()

    def test_review_grab_dbb_clips_uses_marked_scope_and_delete_option(self):
        result = {
            "id": "dbb-clips",
            "dbb_execution": {"enabled": True},
            "defects": [
                {"id": 1, "marked": True},
                {"id": 2, "dbb_clip_saved": True, "dbb_clip_image": "old.tif"},
            ],
        }
        review = ReviewWorkspace(result)
        with patch("puma_ui.modules.results_review.dialogs.DBBClipGrabDialog") as dialog_type, patch(
            "puma_ui.modules.results_review.dialogs._exec", return_value=QDialog.Accepted
        ):
            dialog_type.return_value.result_options = {"delete_existing": True}
            review._grab_dbb_clips()
        first, second = review.result["defects"]
        self.assertTrue(first["dbb_clip_saved"])
        self.assertNotIn("dbb_clip_saved", second)
        self.assertEqual(review.result["dbb_saved_clip_count"], 1)
        self.assertEqual(review.result["review_operations"][-1]["operation"], "Grab DBB Clips")

    def test_dbc_library_lifecycle_and_unique_bins(self):
        library = create_dbc_library("Metal Library", ["Metal1"])
        library = add_dbc_bin(
            library, "Contacts", 120, rotate=True, nuisance=True,
            rough_bin_enabled=True, rough_bin_code=7,
            size_sieve_enabled=True, minimum_area=1, maximum_area=25,
            comment="contact patterns",
        )
        self.assertTrue(library["bins"][0]["rotate"])
        self.assertTrue(library["bins"][0]["nuisance"])
        self.assertEqual(library["bins"][0]["rough_bin_code"], 7)
        with self.assertRaisesRegex(ValueError, "unique"):
            add_dbc_bin(library, "contacts", 121)
        copied = save_dbc_library_as(library, "Metal Library Copy")
        self.assertNotEqual(copied["id"], library["id"])
        self.assertEqual(copied["version"], 1)

    def test_dbc_bin_properties_and_poi_validity(self):
        properties = DBCBinPropertiesDialog(existing_names=["Existing"])
        properties.name.setText("Contact POI")
        properties.class_code.setValue(120)
        properties.non_poi.setChecked(True)
        properties.size_sieve.setChecked(True)
        properties.minimum_area.setValue(1)
        properties.maximum_area.setValue(10)
        properties._finish()
        self.assertEqual(properties.result(), QDialog.Accepted)
        self.assertTrue(properties.result_bin["non_poi"])

        poi = POIViewDialog({"id": "e1", "name": "Example", "valid": False}, ["Metal1"])
        poi.layer_checks[0].setChecked(True)
        poi.mode.setCurrentText("Full Polygon")
        poi._define()
        poi._finish()
        self.assertEqual(poi.result(), QDialog.Accepted)
        self.assertTrue(poi.result_example["valid"])
        self.assertEqual(poi.result_example["poi"]["mode"], "Full Polygon")

    def test_dbb_view_library_save_publish_open_and_delete(self):
        state = default_dbb_state()
        state["dbc_bins"] = [{"id": "b1", "name": "A", "class_code": 100, "examples": []}]
        view = DBBViewDialog({"defects": []}, state)
        view.library_name.setText("Working")
        view._save_library()
        self.assertEqual(len(view.libraries), 1)
        view._publish_library()
        self.assertTrue(view.libraries[0]["published"])
        view.library_name.setText("Working Copy")
        view._save_library(True)
        self.assertEqual(len(view.libraries), 2)
        view.library_selector.setCurrentIndex(0)
        view._open_library()
        self.assertEqual(view.library_name.text(), "Working")
        view._delete_library()
        self.assertEqual(len(view.libraries), 1)

    def test_clip_examples_can_be_added_and_moved_between_bins(self):
        library = create_dbc_library("Library", ["Metal1"])
        library = add_dbc_bin(library, "A", 100)
        library = add_dbc_bin(library, "B", 101)
        library = add_clip_examples(library, library["bins"][0]["id"], [{"id": 7, "x": 10, "y": 20}])
        example_id = library["bins"][0]["examples"][0]["id"]
        moved = move_dbc_examples(library, [example_id], library["bins"][1]["id"])
        self.assertEqual(len(moved["bins"][0]["examples"]), 0)
        self.assertEqual(moved["bins"][1]["examples"][0]["defect_id"], 7)

    def test_hotspot_csv_validates_clip_and_aoi_sizes(self):
        points = parse_hotspot_csv("X,Y,Clip Size,AOI Box Size\n10,20,4,2\n")
        self.assertEqual(points[0]["aoi_size"], 2)
        with self.assertRaisesRegex(ValueError, "AOI"):
            parse_hotspot_csv("X,Y,Clip Size,AOI Box Size\n10,20,2,4\n")
        with self.assertRaisesRegex(ValueError, "recipe Design Clip Size"):
            parse_hotspot_csv("X,Y,Clip Size,AOI Box Size\n10,20,12,4\n", maximum_clip_size=10)

    def test_dbc_setup_imports_real_hotspot_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "hotspots.csv"
            path.write_text("X,Y,Clip Size,AOI Box Size\n10,20,4,2\n30,40,5,3\n", encoding="utf-8")
            dialog = DBCSetupDialog({"registered": True, "inspection_layer": "Metal1"})
            with patch(
                "puma_ui.modules.design_based_binning.dialogs.QFileDialog.getOpenFileName",
                return_value=(str(path), "CSV Files (*.csv)"),
            ):
                dialog._import_hotspot()
            self.assertEqual(len(dialog.state["dbc_examples"]), 2)
            self.assertEqual(dialog.state["dbc_examples"][0]["x"], 10)
            self.assertEqual(dialog.state["dbc_examples"][1]["aoi_size"], 3)

    def test_dbb_scope_filters_current_selected_marked_folder_and_stacked(self):
        defects = [{"id": 1, "dbc_bin": "A", "marked": True}, {"id": 2, "dbc_bin": "B", "stack_count": 2}]
        self.assertEqual([d["id"] for d in scoped_defects(defects, "Current Defect Only", 2)], [2])
        self.assertEqual([d["id"] for d in scoped_defects(defects, "All Selected Defects", selected=[1])], [1])
        self.assertEqual([d["id"] for d in scoped_defects(defects, "All Marked Defects")], [1])
        self.assertEqual([d["id"] for d in scoped_defects(defects, "Current Folder(s)", folder=("dbc_bin", "B"))], [2])
        self.assertEqual([d["id"] for d in scoped_defects(defects, "Stacked Defects")], [2])

    def test_folder_counts_are_sorted_by_count(self):
        counts = dbb_folder_counts([{"dbc_bin": "B"}, {"dbc_bin": "A"}, {"dbc_bin": "A"}])
        self.assertEqual(counts, [("A", 2), ("B", 1)])

    def test_analysis_toolbox_populates_design_attributes(self):
        defects = [{"id": 1, "x": 11, "y": 4}, {"id": 2, "x": 20, "y": 7}]
        analyzed = execute_dbb_analysis(defects, {"dbc": True, "dbg": True, "dci": True, "pci": True, "pattern_density": True, "bins": [{"name": "Contact", "class_code": 120}]})
        self.assertEqual(analyzed[0]["dbc_bin"], "Contact")
        self.assertEqual(analyzed[0]["dbb_global_bin"], 1)
        self.assertIn("dbg_group", analyzed[0])
        self.assertIn("dci", analyzed[0])
        self.assertIn("pci", analyzed[0])
        self.assertIn("pattern_density", analyzed[0])
        with self.assertRaisesRegex(ValueError, "Enable"):
            execute_dbb_analysis(defects, {})

    def test_analysis_honors_dbc_non_poi_rough_bin_and_size_sieve(self):
        settings = {
            "dbc": True,
            "bins": [{
                "name": "Non-POI",
                "class_code": 120,
                "non_poi": True,
                "rough_bin_enabled": True,
                "rough_bin_code": 7,
                "size_sieve_enabled": True,
                "minimum_area": 1,
                "maximum_area": 10,
            }],
        }
        analyzed = execute_dbb_analysis([
            {"id": 1, "x": 1, "y": 1, "size_um": 5},
            {"id": 2, "x": 2, "y": 2, "size_um": 20},
        ], settings)
        self.assertEqual(analyzed[0]["dbb_global_bin"], 2)
        self.assertEqual(analyzed[0]["rough_bin"], 7)
        self.assertEqual(analyzed[1]["dbb_global_bin"], 0)
        self.assertNotIn("dbc_bin", analyzed[1])

    def test_run_applies_dbg_filter_out_rule(self):
        dbb = default_dbb_state()
        dbb.update({
            "enabled": True,
            "registered": True,
            "rdf_file": "Device1.rdf",
            "inspection_layer": "Metal1",
            "dbg_enabled": True,
            "dci_enabled": True,
            "dbg_filter_enabled": True,
            "dbg_filter_attribute": "DCI",
            "dbg_filter_operator": ">=",
            "dbg_filter_value": 0,
            "throughput_skip_dbb": False,
        })
        result = generate_inspection_result(
            {"id": "dbb-filter", "inspection": "Deep", "tests": [{"name": "Test 1"}], "dbb": dbb},
            {"lot_id": "LOT", "wafer_id": "W1", "selected_tests": ["Test 1"]},
        )
        self.assertTrue(all(item["dbg_filtered_out"] for item in result["defects"]))
        self.assertTrue(all(item["dbb_global_bin"] == 0 for item in result["defects"]))

    def test_sampling_honors_priority_and_per_die_limit(self):
        defects = [{"id": 1, "dci": .1, "die_x": 0, "die_y": 0}, {"id": 2, "dci": .9, "die_x": 0, "die_y": 0}, {"id": 3, "dci": .5, "die_x": 1, "die_y": 0}]
        sampled = sample_dbb_defects(defects, {"maximum": 2, "scheme": "Prioritized by DCI", "limits_enabled": True, "max_per_die": 1, "max_per_cluster": 5})
        self.assertEqual(sampled, [2, 3])

    def test_sampling_honors_dbb_buckets_size_and_adders(self):
        defects = [
            {"id": 1, "dbc_bin": "POI", "size_um": 2, "previous_layer": False},
            {"id": 2, "dbg_type": "Systematic", "dci": .9, "size_um": 3, "previous_layer": False},
            {"id": 3, "dbg_type": "Random", "pattern_density": .8, "size_um": 4, "previous_layer": False},
            {"id": 4, "dbg_type": "Random", "pattern_density": .9, "size_um": 4, "previous_layer": True},
            {"id": 5, "dbg_type": "Random", "pattern_density": .7, "size_um": 20, "previous_layer": False},
        ]
        sampled = sample_dbb_defects(defects, {
            "maximum": 3,
            "dbc_enabled": True,
            "dbc_size": 1,
            "dbg_systematic_enabled": True,
            "dbg_systematic_size": 1,
            "dbg_random_enabled": True,
            "adders_only": True,
            "minimum_defect_size": 1,
            "maximum_defect_size": 10,
        })
        self.assertEqual(sampled, [1, 2, 3])

    def test_clear_dbb_attributes_can_target_filtered_defects(self):
        defects = [
            {"id": 1, "filtered_out": True, "dci": .8, "dbc_bin": "A"},
            {"id": 2, "dci": .4, "dbc_bin": "B"},
        ]
        cleared = clear_dbb_attributes(defects, filtered_only=True)
        self.assertNotIn("dci", cleared[0])
        self.assertNotIn("dbc_bin", cleared[0])
        self.assertEqual(cleared[1]["dci"], .4)

    def test_analysis_toolbox_dialog_executes_and_samples(self):
        dialog = DBBAnalysisToolboxDialog([{"id": 1, "x": 5, "y": 6}], {"dbc_bins": [{"name": "A", "class_code": 100}]})
        dialog._execute()
        self.assertEqual(dialog.result(), QDialog.Accepted)
        self.assertEqual(dialog.result_defects[0]["dbc_bin"], "A")
        self.assertEqual(dialog.sampled_ids, [1])

    def test_analysis_toolbox_excludes_and_clears_filtered_defects(self):
        dialog = DBBAnalysisToolboxDialog([
            {"id": 1, "x": 5, "y": 6},
            {"id": 2, "x": 7, "y": 8, "filtered_out": True, "dci": .9, "dbc_bin": "Old"},
        ])
        dialog.reset_filtered.setChecked(True)
        dialog._execute()
        filtered = next(item for item in dialog.result_defects if item["id"] == 2)
        self.assertNotIn("dci", filtered)
        self.assertNotIn("dbc_bin", filtered)

    def test_dbb_view_has_five_working_panes_and_saves_analysis(self):
        result = {"id": "lot-1", "lot_id": "LOT", "wafer_id": "W01", "defects": [{"id": 1, "x": 10, "y": 20, "test": "Test 1", "dbc_bin": "A", "dbg_group": "DBG-001", "dci": .5, "pci": .4}]}
        state = default_dbb_state(); state.update({"enabled": True, "dbc_bins": [{"id": "bin-a", "name": "A", "class_code": 100, "examples": []}]})
        view = DBBViewDialog(result, state)
        self.assertEqual(view.grid.rowCount(), 1)
        self.assertEqual(view.gallery.count(), 1)
        self.assertEqual(view.classifier.topLevelItemCount(), 1)
        view.grid.selectRow(0); view._add_clips(); view._finish()
        self.assertEqual(view.result_data["defect_count"], 1)
        self.assertEqual(view.result_data["dbb_recipe"]["dbc_bins"][0]["examples"][0]["defect_id"], 1)
        view.close()

    def test_dbb_view_assigns_manual_bin_and_groups_it(self):
        result = {"defects": [{"id": 1, "x": 0, "y": 0, "test": "Test 1"}]}
        state = default_dbb_state()
        state["dbc_bins"] = [{"id": "bin-a", "name": "Manual A", "class_code": 100, "examples": []}]
        view = DBBViewDialog(result, state)
        view.selected_ids = {1}
        view.classifier.setCurrentItem(view.classifier.topLevelItem(0))
        view._assign_manual_bin()
        self.assertEqual(view.defects[0]["dbb_manual_bin"], "Manual A")
        view.group.setCurrentText("DBB Manual Bin")
        self.assertEqual(view._attribute(), "dbb_manual_bin")

    def test_main_window_exposes_dbb_view_entry(self):
        window = PumaMainWindow()
        labels = {action.text() for action in window.findChildren(type(window.user_manual_action))}
        self.assertIn("DBB View...", labels)
        window.close()


if __name__ == "__main__":
    unittest.main()

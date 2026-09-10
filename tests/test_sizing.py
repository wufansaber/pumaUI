from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from puma_ui.main_window import PumaMainWindow
from puma_ui.modules.sizing import (
    DefectSetEditorDialog,
    HistogramDialog,
    KlarfOptionsDialog,
    LotResultReaderDialog,
    MappingsDialog,
    SizingRecipeDialog,
    SizingSetupTool,
    apply_sizing_recipe,
    auto_map_for_set,
    consolidate_lot_results,
    default_sizing_recipe,
    default_sizing_state,
    defect_set_from_klarf_result,
    defect_set_from_result,
    export_sizing_recipe_xml,
    histogram_values,
    import_reference_sizes,
    import_sizing_recipe_xml,
    normalized_sizing_recipe,
    normalized_sizing_state,
    remove_defect_set,
    scatter_points,
    scatter_statistics,
    set_reference_size,
    transfer_reference_sizes,
    validate_sizing_recipe,
)
from puma_ui.modules.results_review import filter_defects
from puma_ui.modules.run_control import generate_inspection_result
from puma_ui.qt_compat import QApplication
from puma_ui.recipe_store import RecipeStore


def _result(identifier="result-1", wafer="W01", lot="LOT-1"):
    return {
        "id": identifier,
        "lot_id": lot,
        "wafer_id": wafer,
        "inspection": "Deep",
        "status": "Complete",
        "defects": [
            {"id": 1, "x": 0.0, "y": 0.0, "size_um": 1.0, "signal": 120.0, "test": "Test 1"},
            {"id": 2, "x": 5.0, "y": 5.0, "size_um": 2.0, "signal": 90.0, "test": "Test 1"},
            {"id": 3, "x": 10.0, "y": 10.0, "size_um": 5.0, "signal": 50.0, "test": "Test 2", "polarity": "Dark"},
        ],
    }


def _mapped_state():
    target = defect_set_from_result(_result(), name="Target")
    for index, defect in enumerate(target["defects"], 1):
        defect["reference_size_um"] = float(index)
    state = default_sizing_state()
    state["defect_sets"] = [target]
    mapping = auto_map_for_set(target)
    state["maps"] = [mapping]
    state["active_map_id"] = mapping["id"]
    return state


class SizingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = RecipeStore(Path(self.temp_dir.name) / "recipes.json")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_manual_defaults_match_recipe_dialog_in_manual(self):
        recipe = default_sizing_recipe()
        self.assertEqual(recipe["scale_factors"]["Small"], 0.6)
        self.assertEqual(recipe["scale_factors"]["Tall"], 1.9)
        self.assertEqual(recipe["cut_lines"]["Small"], 13.0)
        self.assertEqual(recipe["cut_lines"]["Very Large"], 21.0)
        self.assertEqual(recipe["cut_lines"]["Planar"], 196.0)

    def test_normalization_clamps_invalid_values_and_preserves_six_groups(self):
        recipe = normalized_sizing_recipe({"scale_factors": {"Small": -2, "Large": 9000}, "cut_lines": {"Planar": -1}})
        self.assertEqual(set(recipe["scale_factors"]), {"Small", "Medium", "Large", "Tall", "Dim", "Planar"})
        self.assertEqual(recipe["scale_factors"]["Small"], 0.001)
        self.assertEqual(recipe["scale_factors"]["Large"], 1000.0)
        self.assertEqual(recipe["cut_lines"]["Planar"], 0.0)

    def test_size_cut_lines_must_be_in_increasing_order(self):
        recipe = default_sizing_recipe()
        recipe["cut_lines"].update({"Small": 18, "Large": 17, "Very Large": 16})
        self.assertTrue(validate_sizing_recipe(recipe))

    def test_lot_result_creates_sizing_defect_set(self):
        defect_set = defect_set_from_result(_result(), name="Lot Target", test="Test 1")
        self.assertEqual(defect_set["kind"], "Lot Result")
        self.assertEqual(defect_set["name"], "Lot Target")
        self.assertEqual(len(defect_set["defects"]), 2)
        self.assertIn(defect_set["defects"][0]["scale_group"], {"Small", "Medium", "Large", "Tall", "Dim", "Planar"})

    def test_klarf_dsize_and_class_code_reference_conversion(self):
        source = _result()
        source["defects"][0]["class_code"] = 12
        dsize = defect_set_from_klarf_result(source, size_field="dSize")
        manual = defect_set_from_klarf_result(source, size_field="Class Code", class_multiplier=0.1)
        self.assertEqual(dsize["defects"][0]["reference_size_um"], 1.0)
        self.assertAlmostEqual(manual["defects"][0]["reference_size_um"], 1.2)

    def test_scatter_filters_zero_reference_sizes_by_default(self):
        state = _mapped_state()
        state["defect_sets"][0]["defects"][1]["reference_size_um"] = 0.0
        self.assertEqual(len(scatter_points(state)), 2)
        state["show_nonzero_only"] = False
        self.assertEqual(len(scatter_points(state)), 3)

    def test_position_overlay_honors_radius(self):
        target = defect_set_from_result(_result(), name="Target")
        reference = defect_set_from_result(_result("reference"), name="Reference")
        for defect in reference["defects"]:
            defect["reference_size_um"] = defect["computed_size_um"]
            defect["x"] += 0.5
        state = default_sizing_state()
        state["defect_sets"] = [target, reference]
        mapping = auto_map_for_set(target, reference_set=reference, overlay_radius_um=0.25)
        state["maps"] = [mapping]
        state["active_map_id"] = mapping["id"]
        self.assertEqual(scatter_points(state), [])
        mapping["overlay_radius_um"] = 1.0
        self.assertEqual(len(scatter_points(state)), 3)

    def test_applying_recipe_recalculates_computed_size(self):
        defect_set = defect_set_from_result(_result())
        defect_set["defects"][0]["scale_group"] = "Small"
        recipe = default_sizing_recipe()
        recipe["scale_factors"]["Small"] = 2.5
        updated = apply_sizing_recipe(defect_set, recipe)
        self.assertEqual(updated["defects"][0]["computed_size_um"], 2.5)

    def test_reference_size_validation_and_text_import(self):
        state = _mapped_state()
        defect_set_id = state["defect_sets"][0]["id"]
        with self.assertRaisesRegex(ValueError, "negative"):
            set_reference_size(state, defect_set_id, 1, -0.1)
        with self.assertRaisesRegex(ValueError, "ID"):
            set_reference_size(state, defect_set_id, 99, 1.0)
        updated, report = import_reference_sizes(state, defect_set_id, "1\t1.25\n2,2.50\n99\t3\nbad")
        self.assertEqual(report, {"applied": 2, "ignored": 2})
        self.assertEqual(updated["defect_sets"][0]["defects"][1]["reference_size_um"], 2.5)

    def test_transfer_reference_sizes_updates_target(self):
        target = defect_set_from_result(_result(), name="Target")
        reference = defect_set_from_result(_result("reference"), name="Reference")
        for defect in reference["defects"]:
            defect["reference_size_um"] = 9.0 + defect["id"]
        state = default_sizing_state()
        state["defect_sets"] = [target, reference]
        mapping = auto_map_for_set(target, reference_set=reference)
        state["maps"] = [mapping]
        state["active_map_id"] = mapping["id"]
        updated = transfer_reference_sizes(state)
        self.assertEqual(updated["defect_sets"][0]["defects"][0]["reference_size_um"], 10.0)

    def test_removing_defect_set_removes_associated_maps(self):
        state = _mapped_state()
        updated = remove_defect_set(state, state["defect_sets"][0]["id"])
        self.assertEqual(updated["defect_sets"], [])
        self.assertEqual(updated["maps"], [])
        self.assertEqual(updated["active_map_id"], "")

    def test_histograms_and_scatter_statistics(self):
        state = _mapped_state()
        self.assertEqual(len(histogram_values(state, "Size")), 3)
        self.assertEqual(len(histogram_values(state, "Special Case")), 3)
        self.assertEqual(len(histogram_values(state, "Planar")), 3)
        stats = scatter_statistics(scatter_points(state), tolerance_um=10)
        self.assertEqual(stats["within_spec_percent"], 100.0)

    def test_recipe_exports_importable_xml_shape(self):
        xml = export_sizing_recipe_xml(default_sizing_recipe(), name="Metal1")
        self.assertIn('<SizingRecipe name="Metal1" version="9.8.306">', xml)
        self.assertEqual(xml.count("<ScaleFactor "), 6)
        self.assertEqual(xml.count("<CutLine "), 6)
        imported = import_sizing_recipe_xml(xml)
        self.assertEqual(imported, default_sizing_recipe())
        with self.assertRaisesRegex(ValueError, "SizingRecipe"):
            import_sizing_recipe_xml("<Recipe />")

    def test_consolidation_retains_properties_and_reassigns_ids(self):
        first = _result("one", "W01")
        second = _result("two", "W02")
        consolidated, transformations = consolidate_lot_results([first, second])
        self.assertEqual(consolidated["defect_count"], 6)
        self.assertEqual([item["id"] for item in consolidated["defects"]], list(range(1, 7)))
        self.assertEqual(consolidated["defects"][3]["source_wafer_id"], "W02")
        self.assertEqual(transformations[-1], {"wafer_id": "W02", "old_id": 3, "new_id": 6})
        with self.assertRaisesRegex(ValueError, "same lot"):
            consolidate_lot_results([first, _result("three", "W03", "OTHER")])

    def test_state_normalization_drops_orphan_maps(self):
        state = default_sizing_state()
        state["maps"] = [{"id": "orphan", "target_set_id": "missing", "reference_set_id": "missing"}]
        state["active_map_id"] = "orphan"
        normalized = normalized_sizing_state(state)
        self.assertEqual(normalized["maps"], [])
        self.assertEqual(normalized["active_map_id"], "")

    def test_recipe_store_persists_workspace(self):
        state = _mapped_state()
        self.store.update_preferences({"sizing_workspace": state})
        restored = RecipeStore(self.store.path).get_preferences()["sizing_workspace"]
        self.assertEqual(restored["active_map_id"], state["active_map_id"])
        self.assertEqual(len(restored["defect_sets"]), 1)

    def test_lot_reader_and_recipe_dialog_return_values(self):
        reader = LotResultReaderDialog([_result()])
        self.assertEqual(reader.pages.count(), 3)
        reader._next()
        self.assertEqual(reader.pages.currentIndex(), 1)
        reader._next()
        self.assertEqual(reader.pages.currentIndex(), 2)
        reader.name.setText("Selected Lot")
        reader._finish()
        self.assertEqual(reader.selected_set["name"], "Selected Lot")
        recipe = SizingRecipeDialog()
        recipe.factor_controls["Small"].setValue(1.25)
        recipe._accept()
        self.assertEqual(recipe.result_recipe["scale_factors"]["Small"], 1.25)
        reader.close()
        recipe.close()

    def test_klarf_reader_wizard_can_associate_lot_wafer_and_test(self):
        first = _result("first", "W01")
        second = _result("second", "W02")
        dialog = KlarfOptionsDialog("reference.klarf", [first, second])
        self.assertEqual(dialog.pages.count(), 5)
        dialog._next()
        self.assertEqual(dialog.pages.currentIndex(), 1)
        dialog._next()
        dialog.wafer.setCurrentIndex(1)
        dialog._next()
        dialog.test.setCurrentText("Test 1")
        dialog._next()
        self.assertEqual(dialog.pages.currentIndex(), 4)
        dialog._finish()
        self.assertEqual(dialog.selected_result["wafer_id"], "W02")
        self.assertEqual(dialog.selected_test, "Test 1")
        dialog.close()

    def test_mapping_editor_and_defect_editor_apply_changes(self):
        state = _mapped_state()
        mappings = MappingsDialog(state)
        mappings._add()
        self.assertEqual(len(mappings.state["maps"]), 2)
        editor = DefectSetEditorDialog(state, state["defect_sets"][0]["id"])
        editor.table.item(0, 1).setText("4.75")
        self.assertTrue(editor._apply())
        self.assertEqual(editor.result_state["defect_sets"][0]["defects"][0]["reference_size_um"], 4.75)
        mappings.close()
        editor.close()

    def test_histogram_dialog_updates_cut_line_and_cdf(self):
        state = _mapped_state()
        dialog = HistogramDialog(state, "Size")
        dialog.cdf.setChecked(True)
        dialog.sliders["Small"].setValue(12.5)
        dialog._apply()
        self.assertEqual(dialog.result_recipe["cut_lines"]["Small"], 12.5)
        self.assertTrue(dialog.chart.show_cdf)
        dialog.close()

    def test_histogram_out_of_graph_control_changes_display_range(self):
        from puma_ui.modules.sizing.dialogs import HistogramWidget

        chart = HistogramWidget()
        chart.resize(640, 400)
        chart.set_data(list(range(100)), show_out_of_graph=False)
        chart.show()
        self.app.processEvents()
        clipped = chart.displayed_count
        self.assertGreater(chart.out_of_graph_count, 0)
        chart.set_data(list(range(100)), show_out_of_graph=True)
        self.app.processEvents()
        self.assertGreater(chart.displayed_count, clipped)
        self.assertEqual(chart.out_of_graph_count, 0)
        chart.close()

    def test_workspace_adds_auto_map_and_persists_options(self):
        tool = SizingSetupTool(self.store, initial_result=_result())
        self.assertEqual(len(tool.state["defect_sets"]), 1)
        self.assertEqual(len(tool.state["maps"]), 1)
        tool.nonzero.setChecked(False)
        restored = RecipeStore(self.store.path).get_preferences()["sizing_workspace"]
        self.assertFalse(restored["show_nonzero_only"])
        tool.close()

    def test_run_collects_sizing_data_and_review_filters_scale_group(self):
        recipe = self.store.new_recipe()
        recipe["inspection"] = "Sizing Run"
        recipe["tests"] = [{"name": "Test 1"}]
        recipe["sizing"] = default_sizing_recipe()
        result = generate_inspection_result(
            recipe,
            {"lot_id": "SIZING", "wafer_id": "W01", "selected_tests": ["Test 1"]},
        )
        self.assertTrue(result["sizing_enabled"])
        self.assertTrue(result["sizing_data"])
        self.assertIn("raw_size_um", result["defects"][0])
        self.assertIn("sizing_scale_group", result["defects"][0])
        group = result["defects"][0]["sizing_scale_group"]
        filtered = filter_defects(result, {"scale_groups": [group]})
        self.assertTrue(filtered)
        self.assertTrue(all(item["sizing_scale_group"] == group for item in filtered))

    def test_save_all_writes_reference_sizes_back_to_every_source_result(self):
        first = self.store.save_result(_result("one", "W01"))
        second = self.store.save_result(_result("two", "W02"))
        tool = SizingSetupTool(self.store)
        first_set = defect_set_from_result(first)
        second_set = defect_set_from_result(second)
        first_set["defects"][0]["reference_size_um"] = 1.1
        second_set["defects"][0]["reference_size_um"] = 2.2
        tool.add_defect_set(first_set)
        tool.add_defect_set(second_set)
        tool.save_all_defect_sets()
        self.assertEqual(self.store.get_result("one")["defects"][0]["reference_size_um"], 1.1)
        self.assertEqual(self.store.get_result("two")["defects"][0]["reference_size_um"], 2.2)
        tool.close()

    def test_main_window_exposes_sizing_tool_in_review_and_tools(self):
        with patch("puma_ui.main_window.RecipeStore", return_value=self.store):
            window = PumaMainWindow()
        menu_actions = list(window.menuBar().actions())
        menu_texts = [action.text() for action in menu_actions]
        self.assertIn("Review", menu_texts)
        self.assertIn("Tools", menu_texts)
        review_action = next(action for action in menu_actions if action.text() == "Review")
        tools_action = next(action for action in menu_actions if action.text() == "Tools")
        review = review_action.menu()
        tools = tools_action.menu()
        self.assertIn("Sizing Setup Tool...", [action.text() for action in review.actions()])
        self.assertIn("Sizing Setup Tool...", [action.text() for action in tools.actions()])
        window.close()


if __name__ == "__main__":
    unittest.main()

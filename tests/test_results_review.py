from __future__ import annotations

import unittest

from puma_ui.modules.results_review import (
    analyze_optics_modes,
    apply_binner,
    apply_review_offset,
    apply_super_class_scheme,
    combine_sensitivity_results,
    auto_label_result,
    default_filter_analysis_state,
    evaluate_sensitivity_tuning,
    execute_filter_analysis,
    export_klarf_text,
    import_klarf_text,
    filter_defects,
    filtered_result_as,
    merge_result,
    normalized_filter_analysis_state,
    review_summary,
    select_wafer_transfer_defects,
)
from puma_ui.modules.run_control import generate_inspection_result


class ResultsReviewTests(unittest.TestCase):
    def setUp(self):
        self.recipe = {
            "id": "recipe-1",
            "inspection": "Deep",
            "device": "D1",
            "step": "Metal",
            "tests": [
                {"name": "Test 1", "mode": "Random"},
                {"name": "Test 2", "mode": "Random"},
            ],
        }
        self.setup = {
            "lot_id": "LOT-1",
            "wafer_id": "W01",
            "selected_tests": ["Test 1", "Test 2"],
        }
        self.result = generate_inspection_result(self.recipe, self.setup)

    def test_generated_results_are_repeatable_for_same_run_identity(self):
        other = generate_inspection_result(self.recipe, self.setup)
        self.assertEqual(self.result["defects"], other["defects"])

    def test_filter_by_test_and_signal(self):
        defects = filter_defects(
            self.result,
            {"tests": ["Test 1"], "minimum_signal": 100.0},
        )
        self.assertTrue(defects)
        self.assertTrue(all(item["test"] == "Test 1" for item in defects))
        self.assertTrue(all(item["signal"] >= 100.0 for item in defects))

    def test_filter_by_general_venn_channel_and_sensitivity_dimensions(self):
        reference = self.result["defects"][0]
        defects = filter_defects(self.result, {
            "adder_mode": "Adders" if reference["adder"] else "Non-Adders",
            "cluster_mode": "Clustered" if reference["cluster_id"] else "Unclustered",
            "repeater_mode": "Repeaters" if reference["repeater"] else "Non-Repeaters",
            "polarities": [reference["polarity"]],
            "venn_ids": [reference["venn_id"]],
            "channels": [reference["channel"]],
            "region_ids": [reference["region_id"]],
            "threshold_regions": [reference["threshold_region"]],
        })
        self.assertTrue(defects)
        self.assertTrue(all(item["venn_id"] == reference["venn_id"] for item in defects))
        self.assertTrue(all(item["channel"] == reference["channel"] for item in defects))
        self.assertTrue(all(item["region_id"] == reference["region_id"] for item in defects))

    def test_multi_test_duplicate_filter_defaults_to_non_duplicates(self):
        result = {"defects": [
            {"id": 1, "multi_test_duplicate": False, "signal": 1, "size_um": 1},
            {"id": 2, "multi_test_duplicate": True, "signal": 1, "size_um": 1},
        ]}
        self.assertEqual([item["id"] for item in filter_defects(result)], [1])
        self.assertEqual(
            [item["id"] for item in filter_defects(result, {"duplicate_mode": "Duplicates"})],
            [2],
        )
        self.assertEqual(
            [item["id"] for item in filter_defects(result, {"duplicate_mode": "All"})],
            [1, 2],
        )

    def test_wafer_transfer_scope_and_duplicate_selection(self):
        result = {"defects": [
            {"id": 1},
            {"id": 2, "multi_test_duplicate": True},
            {"id": 3},
        ]}
        visible = [result["defects"][1]]
        self.assertEqual(
            [item["id"] for item in select_wafer_transfer_defects(
                result, visible, scope="All Defects"
            )],
            [1, 3],
        )
        self.assertEqual(
            [item["id"] for item in select_wafer_transfer_defects(
                result, visible, scope="All Defects", include_duplicates=True
            )],
            [1, 2, 3],
        )
        self.assertEqual(
            [item["id"] for item in select_wafer_transfer_defects(
                result, visible, scope="Shown Defects"
            )],
            [2],
        )

    def test_advanced_filter_expression(self):
        defects = filter_defects(
            self.result,
            {"advanced_expression": "Defect Size > 4 AND Intensity >= 100"},
        )
        self.assertTrue(defects)
        self.assertTrue(all(item["size_um"] > 4 and item["signal"] >= 100 for item in defects))

    def test_filter_analysis_state_preserves_order_and_templates(self):
        state = default_filter_analysis_state()
        state["operations"] = [
            {"name": "Sampling", "type": "ignored", "enabled": True},
            {"name": "General Filter", "type": "ignored", "enabled": True},
        ]
        state["templates"] = {"Production": {"operations": []}}
        normalized = normalized_filter_analysis_state(state)
        self.assertEqual(normalized["operations"][0]["name"], "Sampling")
        self.assertEqual(normalized["operations"][0]["type"], "Analysis")
        self.assertEqual(normalized["operations"][1]["name"], "General Filter")
        self.assertEqual(len(normalized["operations"]), 14)
        self.assertIn("Production", normalized["templates"])

    def test_filter_analysis_executes_ordered_filter_then_analysis(self):
        state = default_filter_analysis_state()
        state["filters"]["minimum_signal"] = 200.0
        state["operations"] = [
            {"name": "Sensitivity Filter", "type": "Filter", "enabled": True},
            {"name": "Clustering", "type": "Analysis", "enabled": True},
        ]
        state["analysis"] = {"operations": [{
            "name": "Clustering",
            "enabled": True,
            "parameters": {
                "auto_clustering": False,
                "minimum_defects": 2,
                "distance_threshold_um": 5000.0,
                "second_pass_multiplier": 1,
                "cluster_within": "All Tests",
            },
        }]}
        updated, execution = execute_filter_analysis(self.result, state)
        self.assertEqual(
            [item["name"] for item in execution["operations"]],
            ["Sensitivity Filter", "Clustering"],
        )
        self.assertLess(len(execution["visible_ids"]), updated["defect_count"])
        visible_ids = set(execution["visible_ids"])
        self.assertTrue(all(
            item.get("cluster_id", 0) >= 0
            for item in updated["defects"]
            if item["id"] in visible_ids
        ))

    def test_filter_in_and_filter_out_ids(self):
        first, second, third = [item["id"] for item in self.result["defects"][:3]]
        included = filter_defects(self.result, {"include_ids": [first, second]})
        self.assertEqual([item["id"] for item in included], [first, second])
        excluded = filter_defects(
            self.result,
            {"include_ids": [first, second, third], "exclude_ids": [second]},
        )
        self.assertEqual([item["id"] for item in excluded], [first, third])

    def test_filter_by_image_availability(self):
        self.result["defects"][0].update({
            "has_patch_image": False,
            "has_sem_image": False,
            "has_manual_image": True,
        })
        self.result["defects"][1].update({
            "has_patch_image": False,
            "has_sem_image": False,
            "has_manual_image": False,
        })
        manual = filter_defects(self.result, {"image_filter": "With Manual Images"})
        no_images = filter_defects(self.result, {"image_filter": "Without Images"})
        self.assertIn(self.result["defects"][0], manual)
        self.assertIn(self.result["defects"][1], no_images)

    def test_summary_and_klarf_use_filtered_defects(self):
        defects = self.result["defects"][:3]
        summary = review_summary(self.result, defects)
        klarf = export_klarf_text(self.result, defects)
        self.assertEqual(summary["visible"], 3)
        self.assertIn("DefectList 3", klarf)
        self.assertIn("LotID LOT-1", klarf)

    def test_klarf_export_import_round_trip_and_recipe_matching(self):
        text = export_klarf_text(self.result, self.result["defects"][:4])
        imported = import_klarf_text(text, self.recipe, source_path="sample.klarf")
        self.assertEqual(imported["recipe_id"], self.recipe["id"])
        self.assertEqual(imported["defect_count"], 4)
        self.assertEqual(imported["lot_id"], "LOT-1")
        self.assertEqual(imported["defects"][0]["die_x"], self.result["defects"][0]["die_x"])
        with self.assertRaisesRegex(ValueError, "does not match"):
            import_klarf_text(text, {**self.recipe, "device": "WrongDevice"})

    def test_klarf_import_uses_record_spec_field_order(self):
        text = """FileVersion 1 1;
LotID ALT-LOT;
WaferID W9;
DeviceID D1;
StepID Metal;
DefectRecordSpec 8 YINDEX DEFECTID CLASSNUMBER XINDEX YREL XREL DSIZE TESTID;
DefectList 1
-3 91 7 4 -0.25 0.5 1.75 Test_2
;
EndOfFile;
"""
        imported = import_klarf_text(text, self.recipe)
        defect = imported["defects"][0]
        self.assertEqual(defect["id"], 91)
        self.assertEqual((defect["die_x"], defect["die_y"]), (4, -3))
        self.assertEqual(defect["class_code"], 7)
        self.assertEqual(defect["test"], "Test_2")

    def test_review_offsets_move_every_defect_and_accumulate(self):
        original = self.result["defects"][0]
        moved = apply_review_offset(self.result, 2.5, -1.25)
        moved = apply_review_offset(moved, 0.5, 0.25)
        self.assertAlmostEqual(moved["defects"][0]["x"], original["x"] + 3.0)
        self.assertAlmostEqual(moved["defects"][0]["y"], original["y"] - 1.0)
        self.assertEqual(moved["defect_offset"], {"x": 3.0, "y": -1.0})

    def test_optics_analysis_is_repeatable_and_scores_each_mode(self):
        modes = [
            {"pixel_size": "SL815", "illumination": "Oblique", "analyzer": "None"},
            {"pixel_size": "SL610", "illumination": "Normal", "analyzer": "P-POL"},
        ]
        first = analyze_optics_modes([1, 4, 7], modes)
        second = analyze_optics_modes([1, 4, 7], modes)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 2)
        self.assertTrue(all(item["signal_noise"] > 0 for item in first))

    def test_sensitivity_tuning_threshold_changes_detected_population(self):
        aggressive = evaluate_sensitivity_tuning(
            self.result, test="Test 1", regions=["R1", "R2", "R3"], threshold=20,
        )
        conservative = evaluate_sensitivity_tuning(
            self.result, test="Test 1", regions=["R1", "R2", "R3"], threshold=200,
        )
        self.assertGreater(aggressive["detected"], conservative["detected"])
        self.assertEqual(aggressive["considered"], conservative["considered"])

    def test_sensitivity_tuning_dark_filter_separates_primary_and_secondary_die(self):
        result = {"defects": [
            {"id": 1, "test": "Test 1", "region_id": "R1", "polarity": "Dark", "die_type": "Primary", "signal": 100},
            {"id": 2, "test": "Test 1", "region_id": "R1", "polarity": "Dark", "die_type": "Secondary", "signal": 100},
            {"id": 3, "test": "Test 1", "region_id": "R1", "polarity": "Bright", "die_type": "Primary", "signal": 100},
        ]}
        primary = evaluate_sensitivity_tuning(
            result, test="Test 1", regions=["R1"], polarity="Dark",
            dark_filter="Primary Dark Defects Only", threshold=50,
        )
        secondary = evaluate_sensitivity_tuning(
            result, test="Test 1", regions=["R1"], polarity="Dark",
            dark_filter="Secondary-Die Defects Only", threshold=50,
        )
        self.assertEqual(primary["considered_ids"], [1])
        self.assertEqual(secondary["considered_ids"], [2])

    def test_super_class_scheme_groups_manual_codes(self):
        updated = apply_super_class_scheme(self.result, {
            "Killer": [1, 2], "Real": [10], "Nuisance": [20], "Disregard": [30], "Unknown": [0],
        })
        expected = {1: "Killer", 2: "Killer", 10: "Real", 20: "Nuisance", 30: "Disregard", 0: "Unknown"}
        self.assertTrue(all(item["super_class"] == expected[item["class_code"]] for item in updated["defects"]))

    def test_combine_sensitivity_results_validates_layout_and_tracks_source(self):
        target = {**self.result, "sensitivity_data": True, "wafer_orientation": "180 deg", "die_height_um": 16000}
        source = generate_inspection_result(self.recipe, {**self.setup, "lot_id": "LOT-2"})
        source.update({"sensitivity_data": True, "wafer_orientation": "180 deg", "die_height_um": 16000})
        combined = combine_sensitivity_results(target, source, target_test="Test 1", source_test="Test 2")
        self.assertTrue(combined["combined_for_sensitivity_tuner"])
        self.assertEqual(combined["sensitivity_summary"]["all"], combined["defect_count"])
        self.assertTrue(any(item.get("combined_source_lot") == "LOT-2" for item in combined["defects"]))
        with self.assertRaisesRegex(ValueError, "orientations"):
            combine_sensitivity_results(target, {**source, "wafer_orientation": "90 deg"})

    def test_auto_label_updates_only_location_matches(self):
        source = generate_inspection_result(self.recipe, self.setup)
        source["defects"][0]["class_code"] = 77
        source["defects"][1]["class_code"] = 88
        target = generate_inspection_result(self.recipe, self.setup)
        target["defects"][0]["class_code"] = 0
        target["defects"][1]["class_code"] = 5
        labeled, changed = auto_label_result(
            target,
            source,
            tolerance=0.00001,
            preserve_classified=True,
        )
        self.assertEqual(changed, 1)
        self.assertEqual(labeled["defects"][0]["class_code"], 77)
        self.assertEqual(labeled["defects"][1]["class_code"], 5)

    def test_merge_result_adds_only_unmatched_defects(self):
        source = {"lot_id": "SOURCE", "defects": [
            dict(self.result["defects"][0], class_code=91),
            dict(self.result["defects"][1], id=999, x=0.999, y=0.999),
        ]}
        merged, added = merge_result(self.result, source, tolerance=0.00001)
        self.assertEqual(added, 1)
        self.assertEqual(merged["defect_count"], self.result["defect_count"] + 1)
        self.assertEqual(merged["defects"][0]["class_code"], 91)

    def test_filtered_result_requires_new_name_and_visible_defects(self):
        with self.assertRaises(ValueError):
            filtered_result_as(self.result, self.result["defects"][:2], "LOT-1")
        with self.assertRaises(ValueError):
            filtered_result_as(self.result, [], "LOT-NEW")
        saved = filtered_result_as(self.result, self.result["defects"][:2], "LOT-NEW")
        self.assertEqual(saved["lot_id"], "LOT-NEW")
        self.assertEqual(saved["defect_count"], 2)
        self.assertEqual(saved["images"], "Patch images only")

    def test_apply_binner_requires_feature_vector_data(self):
        with self.assertRaisesRegex(ValueError, "Save Feature Vectors"):
            apply_binner(
                self.result,
                self.result["defects"][:10],
                ido_classifier={"name": "Production iDO", "type": "iDO"},
                enable_ido=True,
            )

    def test_apply_binner_processes_only_displayed_defects(self):
        self.result["feature_vector_file"] = "FeatureVectors.bin"
        visible = self.result["defects"][:14]
        updated, stats = apply_binner(
            self.result,
            visible,
            nef_state={
                "classifiers": [{"name": "Line Filter", "type": "ST-NEF"}],
                "keep_nuisance_defects": False,
            },
            ido_classifier={"name": "Production iDO", "type": "iDO", "rough_code": "R7"},
            enable_nef=True,
            enable_ido=True,
        )
        self.assertEqual(stats["processed"], 14)
        self.assertEqual(stats["filtered"], 2)
        self.assertEqual(stats["classified"], 12)
        self.assertFalse(any(item.get("binner_filtered") for item in updated["defects"][14:]))
        self.assertEqual(len(filter_defects(updated)), len(updated["defects"]) - 2)

    def test_apply_binner_selected_mode_and_clear_codes(self):
        self.result["feature_vector_file"] = "FeatureVectors.bin"
        for defect in self.result["defects"]:
            defect["class_code"] = 9
        selected_id = self.result["defects"][0]["id"]
        updated, stats = apply_binner(
            self.result,
            self.result["defects"][:10],
            ido_classifier={"name": "Production iDO", "type": "iDO"},
            enable_ido=True,
            clear_codes_on_wafer=True,
            use_selected_defects=True,
            selected_ids=[selected_id],
        )
        self.assertEqual(stats["processed"], 1)
        self.assertTrue(all(item["class_code"] == 0 for item in updated["defects"]))
        self.assertIn("ido_rough_code", updated["defects"][0])
        self.assertIn("ido_rough_group", updated["defects"][0])
        self.assertNotIn("ido_rough_code", updated["defects"][1])

    def test_filter_by_ido_rough_class_and_group(self):
        result = {"defects": [
            {"id": 1, "ido_rough_code": "R1", "ido_rough_group": "G1", "signal": 1, "size_um": 1},
            {"id": 2, "ido_rough_code": "R2", "ido_rough_group": "G1", "signal": 1, "size_um": 1},
            {"id": 3, "ido_rough_code": "R1", "ido_rough_group": "G2", "signal": 1, "size_um": 1},
        ]}
        filtered = filter_defects(
            result, {"rough_classes": ["R1"], "rough_groups": ["G1"]}
        )
        self.assertEqual([item["id"] for item in filtered], [1])


if __name__ == "__main__":
    unittest.main()

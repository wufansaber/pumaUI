from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from puma_ui.modules.inspection_tests import (
    aca_dram_example,
    accept_sem_correlation_match,
    apply_care_area_offset,
    automatic_rod_positions,
    care_area_coverage_report,
    delete_groups_with_descendants,
    classifier_compatibility_errors,
    classifier_from_path,
    default_care_area_state,
    default_fourier_state,
    default_light_training_state,
    default_nef_state,
    default_nanopoint_state,
    default_sem_state,
    default_sample_plan,
    edge_boundary_fraction,
    default_display_color_scheme,
    default_segmentation_state,
    default_sensitivity_state,
    default_test,
    iris_options,
    klarf_overrides,
    generate_page_break_groups,
    grow_shrink_areas,
    find_spectral_troughs,
    intersect_care_areas,
    move_page_break,
    normalize_fourier_state,
    normalize_nef_state,
    normalize_nanopoint_state,
    sem_correlation_candidates,
    apply_sem_correlation,
    analyze_bandwidth_csv,
    normalize_test,
    normalized_sample_plan,
    normalized_sensitivity_state,
    parse_sensitivity_state,
    serialize_sensitivity_state,
    normalized_light_training_state,
    normalized_care_area_state,
    repeat_page_break,
    recalculate_rod_records,
    refresh_derived_groups,
    sort_page_break_groups,
    optics_change_invalidates_fourier,
    parse_klarf_sample_plan,
    pattern_overrides,
    parse_display_color_scheme,
    serialize_display_color_scheme,
    sample_plan_rows,
    spectral_energy_samples,
    validate_fourier_state,
    validate_nanopoint_state,
    validate_nef_state,
    validate_sensitivity,
    validate_light_training_state,
    validate_segmentation_regions,
    validate_test,
)


class InspectionTestDefaultsTests(unittest.TestCase):
    def test_grow_shrink_and_intersection_geometry(self):
        grown = grow_shrink_areas([[0.2, 0.2, 0.3, 0.3]], [0.1, 0.05, 0.1, 0.05])
        self.assertEqual(grown, [[0.1, 0.15000000000000002, 0.5, 0.4]])
        intersection = intersect_care_areas(
            [[0.1, 0.1, 0.4, 0.4]], [[0.3, 0.2, 0.4, 0.5]]
        )
        self.assertEqual(intersection, [[0.3, 0.2, 0.2, 0.3]])

    def test_derived_groups_refresh_and_parent_delete_cascades(self):
        groups = [
            {"name": "A", "areas": [[0.1, 0.1, 0.4, 0.4]]},
            {"name": "B", "areas": [[0.3, 0.2, 0.4, 0.5]]},
            {
                "name": "A_B_Intersect",
                "parents": ["A", "B"],
                "derived_operation": "intersection",
                "areas": [],
            },
            {"name": "PB", "parent": "A", "areas": []},
        ]
        refresh_derived_groups(groups)
        self.assertEqual(groups[2]["areas"], [[0.3, 0.2, 0.2, 0.3]])

        remaining = delete_groups_with_descendants(groups, [0])
        self.assertEqual([group["name"] for group in remaining], ["B"])

    def test_patterned_wafer_uses_random_mode(self):
        test = default_test(1, "Patterned", "Down (180 deg.)")
        self.assertEqual(test["mode"], "Random")
        self.assertEqual(test["orientation"], "Down (180 deg.)")
        self.assertEqual(len(test["channels"]), 3)
        self.assertFalse(test["save_image_patches"])
        self.assertFalse(test["save_feature_vectors"])
        self.assertEqual(test["unsupervised_groups"], 8)

    def test_blank_wafer_uses_test_mode(self):
        test = default_test(1, "Blank", "Up (0 deg.)")
        self.assertEqual(test["mode"], "Test")

    def test_default_tests_do_not_share_channel_state(self):
        first = default_test(1)
        second = default_test(2)
        first["channels"][0]["iris"] = "FWD"
        self.assertEqual(second["channels"][0]["iris"], "OPEN")

    def test_default_tests_do_not_share_nef_state(self):
        first = default_test(1)
        second = default_test(2)
        first["nef"]["classifiers"].append({"name": "A", "type": "ST-NEF", "st_nef": True})
        self.assertEqual(second["nef"], default_nef_state())

    def test_default_tests_do_not_share_nanopoint_templates(self):
        first = default_test(1)
        second = default_test(2)
        first["nano_point_templates"]["templates"].append({"name": "Target 1"})
        self.assertEqual(second["nano_point_templates"], default_nanopoint_state())

    def test_nanopoint_templates_require_source_and_images(self):
        state = default_nanopoint_state()
        state["templates"] = [
            {
                "name": "Target 1",
                "confidence": 0.8,
                "uniqueness": 0.9,
                "search_threshold": 0.75,
            }
        ]
        errors = validate_nanopoint_state(state)
        self.assertIn("select defect data for NanoPoint Image Templates", errors)
        self.assertIn("grab images for all NanoPoint templates", errors)
        state["defect_source"] = "lot.json"
        state["images_grabbed"] = True
        self.assertEqual(validate_nanopoint_state(state), [])

    def test_nanopoint_normalization_preserves_reference_die(self):
        state = normalize_nanopoint_state({"reference_die": ["4", "-2"]})
        self.assertEqual(state["reference_die"], [4, -2])

    def test_nanopoint_sem_correlation_is_persisted(self):
        template = {
            "name": "Target 1",
            "has_sem_image": True,
            "sem": default_sem_state(),
        }
        candidates = sem_correlation_candidates([0.3, 0.3, 0.2, 0.2])
        self.assertEqual(len(candidates), 3)
        correlated = apply_sem_correlation(template, [0.3, 0.3, 0.2, 0.2], 1)
        self.assertTrue(correlated["sem"]["correlated"])
        self.assertEqual(correlated["sem"]["selected_match"], 1)
        normalized = normalize_nanopoint_state({"templates": [correlated]})
        self.assertEqual(normalized["templates"][0]["sem"]["rotation"], 0)

    def test_nanopoint_accepts_the_selected_existing_sem_match(self):
        template = {
            "name": "Target 1",
            "has_sem_image": True,
            "sem": default_sem_state(),
        }
        template["sem"]["matches"] = sem_correlation_candidates(
            [0.3, 0.3, 0.2, 0.2]
        )
        accepted = accept_sem_correlation_match(template, 2)
        self.assertEqual(accepted["sem"]["selected_match"], 2)
        self.assertEqual(
            accepted["sem"]["care_area"],
            accepted["sem"]["matches"][2]["area"],
        )
        self.assertTrue(accepted["sem"]["correlated"])

    def test_nanopoint_mca_and_noise_box_ranges_are_validated(self):
        state = default_nanopoint_state()
        state["mca_size"] = 4
        state["noise_box_size"] = 81
        errors = validate_nanopoint_state(state)
        self.assertIn("NanoPoint MCA size must be between 5 and 21", errors)
        self.assertIn("NanoPoint noise box size must be between 48 and 80", errors)

    def test_fourier_defaults_have_eleven_rods_per_channel(self):
        state = default_fourier_state()
        self.assertEqual(len(state["rods"]), 33)
        for channel in (1, 2, 3):
            rods = [record for record in state["rods"] if record["channel"] == channel]
            self.assertEqual([record["rod"] for record in rods], list(range(1, 12)))

    def test_fourier_curve_analysis_finds_valleys_and_sets_rod_count(self):
        positions = find_spectral_troughs(spectral_energy_samples(1))
        self.assertEqual(len(positions), 2)
        self.assertAlmostEqual(positions[0], 0.28, places=2)
        self.assertAlmostEqual(positions[1], 0.73, places=2)

        box = {
            "x": 0.1,
            "y": 0.1,
            "width": 0.2,
            "height": 0.2,
            "channels": [1, 2, 3],
        }
        rods = recalculate_rod_records(default_fourier_state()["rods"], [box], 0.90)
        for channel in (1, 2, 3):
            enabled = [
                record for record in rods
                if record["channel"] == channel and record["enabled"]
            ]
            self.assertEqual(len(enabled), 2)
            self.assertEqual({record["deck"] for record in enabled}, {2, 4})

    def test_fourier_curve_positions_follow_numerical_aperture(self):
        box = {
            "x": 0.1,
            "y": 0.1,
            "width": 0.2,
            "height": 0.2,
            "channels": [1],
        }
        normal = automatic_rod_positions(1, [box], 0.90)
        changed = automatic_rod_positions(1, [box], 0.75)
        self.assertEqual(len(normal), len(changed))
        self.assertNotEqual(normal, changed)
        self.assertEqual(automatic_rod_positions(2, [box], 0.90), [])

    def test_fourier_legacy_rods_are_migrated(self):
        legacy = {
            "rods": [
                {"rod": 1, "channel": 2, "enabled": True, "position": 0.44, "score": "91"}
            ]
        }
        state = normalize_fourier_state(legacy)
        record = next(
            item for item in state["rods"]
            if item["channel"] == 2 and item["rod"] == 1
        )
        self.assertEqual(record["position"], 0.44)
        self.assertEqual(len(state["rods"]), 33)

    def test_fourier_box_requires_valid_geometry_and_channels(self):
        state = default_fourier_state()
        state["boxes"] = [
            {"x": 0.2, "y": 0.2, "width": 0.25, "height": 0.25, "channels": []}
        ]
        self.assertIn(
            "training box 1 must use at least one valid channel",
            validate_fourier_state(state),
        )
        state["boxes"][0]["channels"] = [1, 3]
        self.assertEqual(validate_fourier_state(state), [])

    def test_manual_optics_fields_invalidate_fourier_training(self):
        for field in ("incidence_angle", "pixel_size", "sample_rate", "iris"):
            self.assertTrue(optics_change_invalidates_fourier(field))
        self.assertFalse(optics_change_invalidates_fourier("focus_offset"))

    def test_sl610_only_allows_open_iris(self):
        self.assertEqual(iris_options("SL610", 0), ["OPEN"])
        test = default_test(1)
        test["inspection_optics"]["pixel_size"] = "SL610"
        test["channels"][2]["iris"] = "CENTER"
        normalized = normalize_test(test, 1, "Patterned", "Down (180 deg.)")
        self.assertEqual(normalized["channels"][2]["iris"], "OPEN")

    def test_center_iris_requires_oblique_channel_three(self):
        self.assertIn("CENTER", iris_options("SL815", 2, "Oblique"))
        self.assertNotIn("CENTER", iris_options("SL815", 1, "Oblique"))
        self.assertNotIn("CENTER", iris_options("SL815", 2, "Normal"))
        test = default_test(1)
        test["channels"][2]["iris"] = "CENTER"
        test["inspection_optics"]["incidence_angle"] = "Normal"
        normalized = normalize_test(test, 1, "Patterned", "Down (180 deg.)")
        self.assertEqual(normalized["channels"][2]["iris"], "OPEN")

    def test_nef_enabled_requires_attached_classifier(self):
        test = default_test(1)
        test["run_nef"] = True
        self.assertIn("NEF is enabled but no classifier is attached", validate_test(test))

    def test_nef_classifier_path_and_five_classifier_limit(self):
        classifier = classifier_from_path(r"C:\Classifiers\LineA.nef")
        self.assertEqual(classifier["name"], "LineA")
        self.assertEqual(classifier["type"], "ST-NEF")
        state = default_nef_state()
        state["classifiers"] = [
            {"name": f"Classifier {index}", "type": "ST-NEF", "st_nef": True}
            for index in range(6)
        ]
        self.assertIn(
            "No more than five NEF/iDO classifiers may be attached",
            validate_nef_state(state),
        )

    def test_classifier_metadata_is_parsed_and_persisted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "LineA.ido.json"
            path.write_text(
                '{"Name":"Line A","Orientation":"Down 180",'
                '"Feature Vector Version":"3.0A","Rough Code":"R7",'
                '"Tree":{"Root":{"Rule":"Signal > 40"}}}',
                encoding="utf-8",
            )
            classifier = classifier_from_path(str(path), "iDO")
        self.assertEqual(classifier["name"], "Line A")
        self.assertEqual(classifier["type"], "iDO")
        self.assertEqual(classifier["orientation"], "Down (180 deg.)")
        self.assertEqual(classifier["feature_vector_version"], "3.0A")
        self.assertEqual(classifier["rough_code"], "R7")
        restored = normalize_nef_state({"classifiers": [classifier]})
        self.assertEqual(restored["classifiers"][0]["tree"]["Root"]["Rule"], "Signal > 40")

    def test_classifier_metadata_supports_xml(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Array.nef.xml"
            path.write_text(
                "<Classifier><Name>Array Filter</Name><Orientation>Right 90</Orientation>"
                "<FeatureVectorVersion>2.0</FeatureVectorVersion>"
                "<Node><Rule>Size &gt; 5</Rule></Node></Classifier>",
                encoding="utf-8",
            )
            classifier = classifier_from_path(str(path), "ST-NEF")
        self.assertEqual(classifier["name"], "Array Filter")
        self.assertEqual(classifier["orientation"], "Right (90 deg.)")
        self.assertEqual(classifier["feature_vector_version"], "2.0")
        self.assertEqual(classifier["metadata"]["Node"]["Rule"], "Size > 5")

    def test_ido_orientation_and_feature_vector_version_must_match(self):
        classifier = {
            "name": "Old iDO",
            "type": "iDO",
            "orientation": "Up (0 deg.)",
            "feature_vector_version": "2.0",
        }
        errors = classifier_compatibility_errors(
            classifier,
            "Down (180 deg.)",
            "3.0A",
        )
        self.assertEqual(len(errors), 2)
        self.assertTrue(any("orientation" in error for error in errors))
        self.assertTrue(any("Feature Vector version" in error for error in errors))

    def test_run_ido_requires_classifier_and_forces_feature_vectors(self):
        test = default_test(1)
        test["run_ido"] = True
        test["save_feature_vectors"] = False
        self.assertIn(
            "iDO is enabled but no iDO classifier is attached",
            validate_test(test),
        )
        normalized = normalize_test(test, 1, "Patterned", "Down (180 deg.)")
        self.assertTrue(normalized["save_feature_vectors"])
        normalized["ido_classifier"] = {
            "name": "Production iDO",
            "type": "iDO",
            "orientation": "Down (180 deg.)",
            "feature_vector_version": "3.0A",
        }
        errors = validate_test(normalized)
        self.assertNotIn("iDO is enabled but no iDO classifier is attached", errors)
        self.assertFalse(any("orientation" in error for error in errors))
        self.assertFalse(any("Feature Vector version" in error for error in errors))

    def test_unsupervised_grouping_requires_feature_vectors_and_valid_group_count(self):
        test = default_test(1)
        test["run_unsupervised_grouping"] = True
        test["save_feature_vectors"] = False
        test["unsupervised_groups"] = 33
        errors = validate_test(test)
        self.assertIn("Unsupervised Grouping requires Save Feature Vectors", errors)
        self.assertIn("Unsupervised Grouping requires between 2 and 32 groups", errors)

        normalized = normalize_test(test, 1, "Patterned", "Down (180 deg.)")
        self.assertTrue(normalized["save_feature_vectors"])

    def test_default_tests_do_not_share_sample_plan_state(self):
        first = default_test(1)
        second = default_test(2)
        first["sample_plan"]["overrides"]["0,0"] = "Do Not Inspect"
        self.assertEqual(second["sample_plan"]["overrides"], {})

    def test_default_sample_plan_has_manual_modes(self):
        plan = default_sample_plan()
        self.assertEqual(plan["inspection_type"], "Full Die")
        self.assertEqual(plan["coverage"], 100.0)
        self.assertFalse(plan["edge_exclusion_enabled"])
        self.assertEqual(plan["coverage_basis"], "Die Based")

    def test_display_color_scheme_round_trip_preserves_categories(self):
        scheme = default_display_color_scheme()
        scheme["name"] = "Fab Night"
        scheme["categories"]["Setup"]["Origin Die"] = "#123456"
        restored = parse_display_color_scheme(serialize_display_color_scheme(scheme))
        self.assertEqual(restored["name"], "Fab Night")
        self.assertEqual(restored["categories"]["Setup"]["Origin Die"], "#123456")
        self.assertIn("Run", restored["categories"])
        self.assertIn("Review", restored["categories"])
        self.assertIn("Alignment", restored["categories"])

    def test_display_color_scheme_rejects_invalid_color(self):
        with self.assertRaises(ValueError):
            parse_display_color_scheme(
                '{"categories": {"Setup": {"Origin Die": "not-a-color"}}}'
            )

    def test_legacy_twelve_point_five_coverage_migrates_to_manual_value(self):
        plan = normalized_sample_plan({"coverage": 12.5})
        self.assertEqual(plan["coverage"], 12.0)

    def test_sample_plan_inside_and_outside_use_configured_edge_boundary(self):
        plan = default_sample_plan()
        plan.update({
            "edge_exclusion_method": "In microns",
            "edge_exclusion_value": 30000.0,
        })
        self.assertAlmostEqual(edge_boundary_fraction(plan), 0.8)
        plan.update({
            "edge_exclusion_method": "As % of radius",
            "edge_exclusion_value": 25.0,
        })
        self.assertAlmostEqual(edge_boundary_fraction(plan), 0.75)

    def test_sample_plan_row_pattern_supports_n_of_every_m_and_percentage(self):
        plan = default_sample_plan()
        plan.update({"row_offset": 2, "row_interval": 5, "row_count": 2})
        self.assertEqual(sample_plan_rows(plan, 14), [2, 3, 7, 8, 12, 13])
        plan.update({"row_pattern_method": "Percentage", "row_percentage": 50})
        self.assertEqual(sample_plan_rows(plan, 14), [2, 3, 7, 8, 12, 13])

    def test_klarf_sample_plan_parser_and_overrides(self):
        sites = parse_klarf_sample_plan(
            "FileVersion 1 1; SampleTestPlan 3 0 0 1 -1 -2 2;"
        )
        self.assertEqual(sites, [[0, 0], [1, -1], [-2, 2]])
        overrides = klarf_overrides(sites)
        self.assertEqual(overrides["0,0"], "Primary Threshold")
        self.assertEqual(overrides["3,3"], "Do Not Inspect")

    def test_die_inspection_pattern_repeats_across_wafer(self):
        overrides = pattern_overrides(
            {"rows": 1, "columns": 2, "cells": [[True, False]]}
        )
        self.assertIn("-1,0", overrides)
        self.assertNotIn("0,0", overrides)

    def test_default_care_area_state_is_independent(self):
        first = default_care_area_state()
        second = default_care_area_state()
        first["thresholds"][0]["threshold"] = 88.0
        self.assertEqual(second["thresholds"][0]["threshold"], 45.0)

    def test_care_area_expansion_order_is_migrated(self):
        state = normalized_care_area_state(
            {
                "thresholds": [
                    {"name": "Logic"},
                    {"name": "Array"},
                ],
                "expansion_order": ["Array", "Missing"],
            }
        )
        self.assertEqual(state["expansion_order"], ["Array", "Logic"])

    def test_care_area_offset_moves_selected_group(self):
        groups = [{"name": "CA", "areas": [[0.1, 0.2, 0.3, 0.2]]}]
        moved = apply_care_area_offset(groups, [0], 255.0, -1660.0, [5100.0, 16600.0])
        self.assertAlmostEqual(moved[0]["areas"][0][0], 0.15)
        self.assertAlmostEqual(moved[0]["areas"][0][1], 0.1)
        self.assertEqual(moved[0]["offset_um"], [255.0, -1660.0])
        self.assertEqual(groups[0]["areas"][0][:2], [0.1, 0.2])
        with self.assertRaises(ValueError):
            apply_care_area_offset(groups, [0], -1020.0, 0, [5100.0, 16600.0])
        with self.assertRaises(ValueError):
            apply_care_area_offset(groups, [0], 1.0, 1.0, [0.0, 16600.0])

    def test_auto_care_area_generates_page_break_subgroups(self):
        groups = generate_page_break_groups(
            [0.05, 0.05, 0.9, 0.9],
            [0.05, 0.05, 0.2, 0.2],
            "ACA 1",
        )
        self.assertEqual(
            [group["kind"] for group in groups],
            ["Horizontal Page Break", "Vertical Page Break"],
        )
        self.assertTrue(all(group["parent"] == "ACA 1" for group in groups))
        self.assertTrue(all(group["areas"] for group in groups))
        self.assertTrue(all(group["threshold"] == "Do Not Inspect" for group in groups))
        self.assertTrue(all(group["do_not_inspect"] for group in groups))

    def test_dram_aca_example_covers_periodic_boundaries_inside_search_area(self):
        example = aca_dram_example()
        groups = generate_page_break_groups(
            example["search_area"],
            example["training_area"],
            example["name"],
        )
        horizontal, vertical = groups
        self.assertEqual(len(horizontal["areas"]), 4)
        self.assertEqual(len(vertical["areas"]), 5)
        sx, sy, sw, sh = example["search_area"]
        for group in groups:
            for x, y, width, height in group["areas"]:
                self.assertGreaterEqual(x, sx)
                self.assertGreaterEqual(y, sy)
                self.assertLessEqual(x + width, sx + sw)
                self.assertLessEqual(y + height, sy + sh)

    def test_page_break_can_move_to_existing_or_new_matching_group(self):
        groups = generate_page_break_groups(
            [0.0, 0.0, 1.0, 1.0], [0.0, 0.0, 0.25, 0.25], "ACA"
        )
        vertical = groups[1]
        vertical_copy = dict(vertical, name="Vertical Page Break 2", areas=[])
        groups.append(vertical_copy)
        moved, target = move_page_break(groups, 1, 0, 2)
        self.assertEqual(target, 2)
        self.assertEqual(len(moved[1]["areas"]), len(groups[1]["areas"]) - 1)
        self.assertEqual(len(moved[2]["areas"]), 1)
        moved, target = move_page_break(moved, 2, 0)
        self.assertEqual(moved[target]["kind"], "Vertical Page Break")

    def test_repeat_page_break_requires_two_and_stays_inside_search_area(self):
        with self.assertRaises(ValueError):
            repeat_page_break([[0.1, 0.1, 0.01, 0.2]])
        areas = [[0.1, 0.1, 0.01, 0.2], [0.2, 0.1, 0.01, 0.2]]
        repeated = repeat_page_break(areas)
        self.assertAlmostEqual(repeated[-1][0], 0.3)
        with self.assertRaises(ValueError):
            repeat_page_break(areas, [0.0, 0.0, 0.25, 1.0])

    def test_page_break_sorting_uses_orientation_specific_size(self):
        groups = [
            {
                "name": "Vertical A",
                "kind": "Vertical Page Break",
                "areas": [[0.1, 0.1, 0.0010, 0.5], [0.2, 0.1, 0.0011, 0.4]],
            },
            {
                "name": "Vertical B",
                "kind": "Vertical Page Break",
                "areas": [[0.3, 0.1, 0.0030, 0.2]],
            },
        ]
        sorted_groups = sort_page_break_groups(groups, [0, 1], 1.0, [1000.0, 1000.0])
        self.assertEqual(len(sorted_groups), 2)
        self.assertEqual([len(group["areas"]) for group in sorted_groups], [2, 1])

    def test_cag_coverage_report_keeps_defined_and_inspected_area(self):
        report = care_area_coverage_report(
            [{"name": "Logic", "areas": [[0.1, 0.1, 0.5, 0.5]]}]
        )
        self.assertEqual(report[0]["defined_percent"], 25.0)
        self.assertLess(report[0]["inspected_percent"], 25.0)

    def test_light_training_defaults_cover_three_channels(self):
        state = default_light_training_state()
        self.assertFalse(state["trained"])
        self.assertEqual(len(state["channels"]), 3)
        self.assertEqual(state["dynamic_range"], "Extended")

    def test_pilo_requires_noise_box_but_legacy_does_not(self):
        state = default_light_training_state()
        state["noise_box"] = []
        self.assertIn(
            "PILO requires a Light Training Noise Box",
            validate_light_training_state(state),
        )
        state["algorithm"] = "Legacy Light Training"
        self.assertEqual(validate_light_training_state(state), [])

    def test_pilo_noise_box_limit_uses_actual_die_dimensions(self):
        state = default_light_training_state()
        state["noise_box"] = [0.1, 0.1, 0.2, 0.2]
        self.assertNotIn(
            "PILO Noise Box exceeds the 2000 x 2000 um limit",
            validate_light_training_state(state, die_size_um=[5000.0, 5000.0]),
        )
        self.assertIn(
            "PILO Noise Box exceeds the 2000 x 2000 um limit",
            validate_light_training_state(state, die_size_um=[5000.0, 16600.0]),
        )

    def test_active_regions_require_active_die_focus_mode(self):
        state = normalized_light_training_state(None)
        state["active_regions"] = [[0.1, 0.1, 0.2, 0.2]]
        state["active_regions_enabled"] = True
        self.assertIn(
            "Active Regions require Focus Mode Active Die",
            validate_light_training_state(state, "Median Die"),
        )
        self.assertEqual(validate_light_training_state(state, "Active Die"), [])

    def test_enabled_active_regions_require_valid_geometry(self):
        state = default_light_training_state()
        state["active_regions_enabled"] = True
        state["active_regions"] = []
        self.assertIn(
            "enabled Active Regions require at least one region",
            validate_light_training_state(state, "Active Die"),
        )
        state["active_regions"] = [[0.9, 0.9, 0.2, 0.2]]
        self.assertIn(
            "Active Region 1 must remain inside the die",
            validate_light_training_state(state, "Active Die"),
        )
        state["active_regions"] = [[0.1, 0.1, 0.2, 0.2]]
        self.assertEqual(validate_light_training_state(state, "Active Die"), [])

    def test_pilo_noise_box_requires_care_area_and_excludes_page_breaks(self):
        state = default_light_training_state()
        state["noise_box_group"] = "Array"
        care_areas = {
            "groups": [
                {
                    "name": "Array",
                    "kind": "Care Area",
                    "enabled": True,
                    "skip_fourier_filter": True,
                    "areas": [[0.20, 0.20, 0.65, 0.65]],
                }
            ]
        }
        self.assertEqual(
            validate_light_training_state(state, "Median Die", care_areas),
            [],
        )
        care_areas["groups"].append(
            {
                "name": "Array Vertical Page Break",
                "kind": "Vertical Page Break",
                "areas": [[0.40, 0.20, 0.02, 0.65]],
            }
        )
        self.assertIn(
            "PILO Noise Box must not include a Page Break",
            validate_light_training_state(state, "Median Die", care_areas),
        )
        state["noise_box"] = [0.0, 0.0, 0.10, 0.10]
        self.assertIn(
            "PILO Noise Box must remain inside the selected Care Area",
            validate_light_training_state(state, "Median Die", care_areas),
        )

    def test_segmentation_state_starts_untrained(self):
        state = default_segmentation_state()
        self.assertFalse(state["valid"])
        self.assertEqual(state["sites"], [])
        self.assertEqual(state["sdi"]["image_box"], [0.20, 0.20, 0.35, 0.35])

    def test_segmentation_rejects_wrong_breaks_gaps_and_empty_sources(self):
        channels = [
            {
                "type": "Median Based Segmentation",
                "breaks": [{"axis": "X", "position": 0.4, "group": 0}],
                "source": "Own Channel",
            },
            {
                "type": "Median Based Segmentation",
                "breaks": [{"axis": "Histogram", "position": 0.6, "group": 2}],
                "source": "Own Channel",
            },
            {"type": "Off", "breaks": [], "source": "Own Channel"},
        ]
        errors = validate_segmentation_regions({"Logic": {"channels": channels}})
        self.assertTrue(any("break type" in error for error in errors))
        self.assertTrue(any("consecutive" in error for error in errors))
        channels[0] = {
            "type": "Projection Based Segmentation",
            "breaks": [{"axis": "X", "position": 0.4, "group": 0}],
            "source": "Channel 3",
        }
        channels[1]["type"] = "Projection Based Segmentation"
        channels[1]["breaks"] = [{"axis": "Y", "position": 0.6, "group": 0}]
        errors = validate_segmentation_regions({"Logic": {"channels": channels}})
        self.assertTrue(any("source channel has no segmentation grid" in error for error in errors))

    def test_sensitivity_rejects_mutually_exclusive_algorithms(self):
        state = default_sensitivity_state(["R1"])
        state["regions"]["R1"]["algorithms"]["FAST"]["run"] = True
        self.assertIn(
            "HLAT, FAST, and AutoSens cannot run in the same test",
            validate_sensitivity(state),
        )

    def test_sensitivity_normalizes_three_channels_and_rejects_invalid_values(self):
        state = normalized_sensitivity_state({
            "regions": {
                "R1": {
                    "algorithms": {
                        "HLAT": {
                            "run": True,
                            "channels": [{"Threshold": 22.0}],
                        }
                    }
                }
            }
        }, ["R1"])
        hlat = state["regions"]["R1"]["algorithms"]["HLAT"]
        self.assertEqual(len(hlat["channels"]), 3)
        self.assertEqual(hlat["channels"][0]["Threshold"], 22.0)
        self.assertIn("Noise", hlat["channels"][0])
        hlat["channels"][1]["Noise"] = float("nan")
        self.assertTrue(any("must be finite" in error for error in validate_sensitivity(state)))
        state = default_sensitivity_state(["R1"])
        self.assertEqual(state["post_filter"], "None")
        self.assertEqual(state["dark_defect_factor"], 1.0)
        state["dark_defect_factor"] = 0
        self.assertIn(
            "Dark Defect Factor must be finite and greater than 0",
            validate_sensitivity(state),
        )

    def test_sensitivity_secondary_algorithms_follow_enhanced_mode(self):
        state = default_sensitivity_state(["R1"])
        state["regions"]["R1"]["algorithms"]["Secondary HLAT"]["run"] = True
        self.assertIn(
            "Secondary algorithms require Enhanced Secondary Die",
            validate_sensitivity(state),
        )
        state["enhanced_secondary_die"] = True
        self.assertNotIn(
            "Enhanced Secondary Die requires a Secondary algorithm",
            validate_sensitivity(state),
        )
        self.assertIn(
            "Secondary Wafer Scale Profile",
            state["regions"]["R1"]["algorithms"],
        )

    def test_sensitivity_gap_dependencies(self):
        state = default_sensitivity_state(["R1"])
        state["regions"]["R1"]["algorithms"]["HLAT"]["run"] = False
        state["regions"]["R1"]["algorithms"]["GAP Max Threshold"]["run"] = True
        state["regions"]["R1"]["algorithms"]["GAP Local Noise Filter"]["run"] = True
        errors = validate_sensitivity(state)
        self.assertIn("GAP Max Threshold requires HLAT, FAST, or ArrayMode", errors)
        self.assertIn("GAP Local Noise Filter requires HLAT or FAST", errors)

    def test_channel_fusion_requires_a_flavor(self):
        state = default_sensitivity_state(["R1"])
        state["regions"]["R1"]["algorithms"]["CF2"]["run"] = True
        self.assertIn(
            "CF2 requires at least one Channel Fusion Flavor",
            validate_sensitivity(state),
        )
        state["fusion_flavors"]["CF2"][0]["enabled"] = True
        self.assertNotIn(
            "CF2 requires at least one Channel Fusion Flavor",
            validate_sensitivity(state),
        )

    def test_sensitivity_normalizes_secondary_fusion_and_sdi_parameters(self):
        state = normalized_sensitivity_state({}, ["R1"])
        algorithms = state["regions"]["R1"]["algorithms"]
        self.assertIn("Secondary CF2", algorithms)
        self.assertIn("Secondary CF3", algorithms)
        self.assertEqual(
            algorithms["GAP Local Noise Filter"]["channels"][0]["Suppression Threshold"],
            0.0,
        )
        primary = state["single_die_inspection"]["primary"]
        self.assertEqual(len(primary["channels"]), 3)
        self.assertEqual(len(primary["fusion"]), 4)
        self.assertEqual(primary["channels"][0]["segments"][0]["threshold"], 200.0)

    def test_sdi_run_requires_an_enabled_segment(self):
        state = default_sensitivity_state(["R1"])
        state["single_die_inspection"]["primary"]["run_sdi"] = True
        self.assertIn(
            "Primary SDI requires at least one enabled Channel Segment",
            validate_sensitivity(state),
        )
        state["single_die_inspection"]["primary"]["channels"][0]["segments"][0]["run"] = True
        self.assertNotIn(
            "Primary SDI requires at least one enabled Channel Segment",
            validate_sensitivity(state),
        )

    def test_vnc_migrates_legacy_flag_and_validates_two_region_limit(self):
        legacy = default_sensitivity_state(["R1"])
        legacy.pop("vnc")
        legacy["variable_noise_control"] = True
        migrated = normalized_sensitivity_state(legacy, ["R1"])
        self.assertTrue(migrated["vnc"]["enabled"])
        self.assertEqual(migrated["vnc"]["mode"], "Apply")
        state = default_sensitivity_state(["R1", "R2", "R3"])
        state["vnc"] = {
            "enabled": True,
            "mode": "Apply",
            "regions": ["R1", "R2", "R3"],
            "max_bw": {
                "R1": [100, 100, 100],
                "R2": [100, 100, 100],
                "R3": [100, 100, 100],
            },
        }
        self.assertIn(
            "Variable Noise Control requires one or two regions",
            validate_sensitivity(state),
        )

    def test_image_packer_bandwidth_analysis_ignores_missing_region_values(self):
        report = analyze_bandwidth_csv(
            "BW1_0,BW2_0,BW3_0,BW1_1,BW2_1,BW3_1\n"
            "75,80,90,-1,-1,-1\n"
            "100,110,120,65,70,75\n"
            "125,130,140,85,90,95\n",
            ["Array", "Edge"],
        )
        self.assertEqual(report["Array"][0]["samples"], 3)
        self.assertEqual(report["Array"][0]["recommended_max_bw"], 125.0)
        self.assertEqual(report["Edge"][0]["samples"], 2)
        self.assertEqual(report["Edge"][0]["minimum"], 65.0)

    def test_sensitivity_parameter_set_round_trip(self):
        state = default_sensitivity_state(["Array"])
        state["regions"]["Array"]["algorithms"]["HLAT"]["channels"][0]["Threshold"] = 73.0
        state["regions"]["Array"]["algorithms"]["HLAT"]["segments"][0]["Seg1"]["Noise"] = 2.5
        restored = parse_sensitivity_state(
            serialize_sensitivity_state(state), ["Array"]
        )
        self.assertEqual(
            restored["regions"]["Array"]["algorithms"]["HLAT"]["channels"][0]["Threshold"],
            73.0,
        )
        self.assertEqual(
            restored["regions"]["Array"]["algorithms"]["HLAT"]["segments"][0]["Seg1"]["Noise"],
            2.5,
        )

    def test_sensitivity_migrates_and_validates_segment_algorithm_parameters(self):
        state = normalized_sensitivity_state(
            {
                "regions": {
                    "Array": {
                        "algorithms": {
                            "HLAT": {
                                "run": True,
                                "channels": [{"Threshold": 27.0, "Noise": 1.5}],
                            }
                        }
                    }
                }
            },
            ["Array"],
        )
        hlat = state["regions"]["Array"]["algorithms"]["HLAT"]
        self.assertEqual(len(hlat["segments"]), 3)
        self.assertEqual(hlat["segments"][0]["Seg0"]["Threshold"], 27.0)
        self.assertEqual(hlat["segments"][0]["Seg1"]["Noise"], 1.5)
        hlat["segments"][2]["Seg1"]["Gradient"] = -1
        self.assertTrue(
            any(
                "channel 3, Seg1: Gradient" in error
                for error in validate_sensitivity(state)
            )
        )

    def test_decoupled_channel_fusion_requires_hlat(self):
        state = default_sensitivity_state(["R1"])
        state["regions"]["R1"]["algorithms"]["HLAT"]["run"] = False
        state["regions"]["R1"]["algorithms"]["FAST"]["run"] = True
        state["decouple_channel_fusion"] = True
        self.assertIn(
            "Decoupled Channel Fusion requires HLAT or Secondary HLAT",
            validate_sensitivity(state),
        )

    def test_runtime_alignment_defaults_and_range(self):
        state = default_sensitivity_state(["R1"])
        self.assertTrue(state["runtime_alignment"]["enable_new_rta"])
        self.assertEqual(state["runtime_alignment"]["max_y_init_shift"], 0)
        state["runtime_alignment"]["max_y_init_shift"] = 2
        self.assertIn("RTA+ MaxYInitShift must be 0 or 1", validate_sensitivity(state))

    def test_complete_test_passes_validation(self):
        test = default_test(1)
        test["care_areas"]["groups"].append(
            {
                "name": "CA 1",
                "kind": "Care Area",
                "enabled": True,
                "areas": [[0.0, 0.0, 1.0, 1.0]],
            }
        )
        test["light_training"]["noise_box_group"] = "CA 1"
        test["fourier"]["boxes"].append(
            {"x": 0.2, "y": 0.2, "width": 0.25, "height": 0.25, "channels": [1, 2, 3]}
        )
        test["fourier"]["trained"] = True
        test["fourier_trained"] = True
        test["light_trained"] = True
        self.assertEqual(validate_test(test), [])

    def test_fourier_training_is_required_only_when_a_channel_uses_the_filter(self):
        test = default_test(1)
        test["care_areas"]["groups"].append(
            {
                "name": "CA 1",
                "kind": "Care Area",
                "enabled": True,
                "areas": [[0.0, 0.0, 1.0, 1.0]],
            }
        )
        test["light_training"]["noise_box_group"] = "CA 1"
        test["light_trained"] = True

        self.assertFalse(any("Fourier Filter" in error for error in validate_test(test)))

        test["channels"][0]["use_fourier_filter"] = True
        self.assertIn(
            "Fourier Filter is enabled but training is incomplete",
            validate_test(test),
        )


if __name__ == "__main__":
    unittest.main()

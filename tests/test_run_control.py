from __future__ import annotations

import unittest

from puma_ui.modules.run_control import (
    apply_sample_plans,
    apply_sensitivity_settings,
    apply_high_defect_abort,
    apply_wafer_post_processing,
    default_run_setup,
    effective_wafer_defect_limit,
    generate_inspection_result,
    job_execution_plan,
    matching_result_ids,
    transfer_prerequisite_errors,
    validate_run_setup,
)
from puma_ui.modules.results_review import result_matches_recipe


def _recipe():
    return {
        "id": "recipe-1",
        "inspection": "Deep",
        "tests": [{"name": "Test 1", "mode": "Random"}],
    }


class RunControlTests(unittest.TestCase):
    def test_image_transfer_requires_manual_recipe_prerequisites(self):
        recipe = _recipe()
        setup = default_run_setup(recipe)
        setup.update({
            "lot_id": "LOT-9",
            "transfer_patches": True,
            "transfer_hi_res": True,
        })
        errors = validate_run_setup(setup, recipe)
        self.assertTrue(any("Save Image Patches" in error for error in errors))
        self.assertTrue(any("Patch Sampling" in error for error in errors))
        self.assertTrue(any("Hi-Res Image Sampling" in error for error in errors))

        recipe["tests"][0]["save_image_patches"] = True
        recipe["wafer_post_processing"] = {
            "operations": [{
                "name": "Sampling",
                "enabled": True,
                "parameters": {
                    "patch_sampling": "Smart",
                    "hi_res_sampling": "Precision",
                },
            }]
        }
        self.assertEqual(transfer_prerequisite_errors(setup, recipe), [])

    def test_lot_result_captures_and_checks_feature_vector_versions(self):
        recipe = _recipe()
        recipe["tests"][0]["feature_vector_version"] = "3.0A"
        result = generate_inspection_result(
            recipe,
            {"lot_id": "VERSION-1", "selected_tests": ["Test 1"]},
        )
        self.assertEqual(result["feature_vector_versions"], {"Test 1": "3.0A"})
        self.assertTrue(result_matches_recipe(result, recipe))
        recipe["tests"][0]["feature_vector_version"] = "2.0"
        self.assertFalse(result_matches_recipe(result, recipe))

    def test_sample_plan_modes_and_coverage_affect_reported_defects(self):
        defects = [
            {"id": 1, "test": "Test 1", "die_x": 0, "die_y": 0},
            {"id": 2, "test": "Test 1", "die_x": 1, "die_y": 0},
            {"id": 3, "test": "Test 1", "die_x": 2, "die_y": 0},
        ]
        test = {
            "name": "Test 1",
            "sample_plan": {
                "coverage": 100,
                "coverage_basis": "Die Based",
                "overrides": {
                    "0,0": "Do Not Inspect",
                    "1,0": "Do Not Report",
                    "2,0": "Secondary Threshold",
                },
            },
        }
        kept, report = apply_sample_plans(defects, [test])
        self.assertEqual([item["id"] for item in kept], [3])
        self.assertEqual(kept[0]["threshold_mode"], "Secondary")
        self.assertEqual(report["Test 1"]["do_not_inspect"], 1)
        self.assertEqual(report["Test 1"]["do_not_report"], 1)

    def test_sample_plan_coverage_is_deterministic_and_recorded(self):
        defects = [
            {"id": index, "test": "Test 1", "die_x": index, "die_y": 0}
            for index in range(1, 33)
        ]
        test = {
            "name": "Test 1",
            "sample_plan": {"coverage": 25, "coverage_basis": "Reticle Based"},
        }
        first, report = apply_sample_plans(defects, [test], {"reticle_size_height": 2})
        second, _ = apply_sample_plans(defects, [test], {"reticle_size_height": 2})
        self.assertEqual([item["id"] for item in first], [item["id"] for item in second])
        self.assertEqual(report["Test 1"]["coverage"], 25)
        self.assertEqual(report["Test 1"]["coverage_basis"], "Reticle Based")
        self.assertGreater(report["Test 1"]["outside_swath_coverage"], 0)

    def test_sensitivity_execution_records_algorithms_and_filters_noise(self):
        defects = [
            {"id": 1, "test": "Test 1", "region_id": "R1", "channel": 1, "signal": 25.0},
            {"id": 2, "test": "Test 1", "region_id": "R1", "channel": 2, "signal": 125.0},
        ]
        test = {
            "name": "Test 1",
            "sensitivity": {
                "histogram_remap": True,
                "autosens_mode": "Engineering",
                "regions": {
                    "R1": {
                        "enable_remap": True,
                        "algorithms": {
                            "HLAT": {"run": True},
                            "Wafer Scale Profile": {"run": True},
                        },
                    }
                },
                "defect_filters": {
                    "run_process_noise_filter": True,
                    "intensity": 50.0,
                    "side_ratio": 0.0,
                    "top_ratio": 0.0,
                },
                "runtime_alignment": {"enable_new_rta": True, "max_y_init_shift": 1},
            },
        }
        kept, report = apply_sensitivity_settings(defects, [test])
        self.assertEqual([item["id"] for item in kept], [2])
        self.assertEqual(
            kept[0]["detection_algorithms"], ["HLAT", "Wafer Scale Profile"]
        )
        self.assertTrue(kept[0]["projection_remap"])
        self.assertEqual(report["Test 1"]["filtered_defects"], 1)
        self.assertEqual(report["Test 1"]["autosens_mode"], "Engineering")

    def test_decoupled_channel_fusion_attributes_reach_results(self):
        defect = {"id": 1, "test": "Test 1", "region_id": "R1", "channel": 2, "signal": 100}
        test = {
            "name": "Test 1",
            "sensitivity": {
                "regions": {"R1": {"algorithms": {"HLAT": {"run": True}}}},
                "decouple_channel_fusion": True,
                "decoupled_cf": {
                    "R1": [
                        {},
                        {"Noise": 2, "Color": 3, "Gradient": 4, "MinDiff": 5},
                        {},
                    ]
                },
            },
        }
        kept, _ = apply_sensitivity_settings([defect], [test])
        self.assertEqual(kept[0]["HLATCFAbsmin"], 5.0)
        self.assertEqual(kept[0]["HLATCF_CH2_Noise"], 2.0)
        self.assertEqual(kept[0]["HLATCF_CH2_Color"], 3.0)
    def test_osts_requires_collect_data_and_only_hlat_or_fast(self):
        recipe = _recipe()
        recipe["tests"][0]["sensitivity"] = {
            "regions": {"R1": {"algorithms": {
                "HLAT": {"run": True},
                "CF2": {"run": True},
            }}}
        }
        setup = default_run_setup(recipe)
        setup.update({"lot_id": "OSTS", "selected_tests": ["Test 1"], "osts_data": True})
        errors = validate_run_setup(setup, recipe)
        self.assertTrue(any("requires Collect" in error for error in errors))
        self.assertTrue(any("incompatible with CF2" in error for error in errors))

        setup["collect_sensitivity_data"] = True
        recipe["tests"][0]["sensitivity"]["regions"]["R1"]["algorithms"]["CF2"]["run"] = False
        self.assertEqual(validate_run_setup(setup, recipe), [])

    def test_osts_result_contains_tuner_data(self):
        recipe = _recipe()
        setup = default_run_setup(recipe)
        setup.update({
            "lot_id": "OSTS", "selected_tests": ["Test 1"],
            "collect_sensitivity_data": True, "osts_data": True,
        })
        result = generate_inspection_result(recipe, setup)
        self.assertTrue(result["sensitivity_data"])
        self.assertEqual(result["sensitivity_data_mode"], "OSTS")
        self.assertEqual(result["defect_count"], 10000)

    def test_matching_result_ids_are_case_insensitive(self):
        results = [
            {"id": "one", "lot_id": "LOT-1"},
            {"id": "two", "lot_id": "lot-1"},
            {"id": "three", "lot_id": "LOT-2"},
        ]
        self.assertEqual(matching_result_ids(results, " lot-1 "), ["one", "two"])

    def test_lot_cache_transfer_target_uses_recipe_device_and_layer(self):
        recipe = _recipe()
        recipe.update({"device": "Device1", "step": "Layer1"})
        recipe["lot_plan"] = {
            "cache_lot_result": True,
            "transfer_host": "K:",
            "transfer_share": "ImpactDataTemp",
            "tool_type": "9xxx",
        }
        setup = default_run_setup(recipe)
        setup["lot_id"] = "TRANSFER"
        result = generate_inspection_result(recipe, setup)
        self.assertTrue(result["transfer"]["auto"])
        self.assertEqual(
            result["transfer"]["target_path"],
            r"K:\ImpactDataTemp\9xxx\Device1\Layer1",
        )

    def test_recipe_defect_limit_overrides_system_default(self):
        recipe = _recipe()
        recipe["wafer_post_processing"] = {"operations": [{
            "name": "Defect Limits",
            "enabled": True,
            "parameters": {"override_wafer_limit": True, "wafer_maximum_defects": 42},
        }]}
        self.assertEqual(effective_wafer_defect_limit(recipe), 42)
        recipe["wafer_post_processing"]["operations"][0]["enabled"] = False
        self.assertEqual(effective_wafer_defect_limit(recipe), 250000)

    def test_high_defect_abort_truncates_and_logs_result(self):
        recipe = _recipe()
        setup = default_run_setup(recipe)
        setup.update({"lot_id": "LOT-1", "wafer_id": "W01"})
        result = generate_inspection_result(recipe, setup)
        aborted = apply_high_defect_abort(result, 10)
        self.assertEqual(aborted["status"], "High Defect Abort")
        self.assertEqual(aborted["defect_count"], 10)
        self.assertIn("maximum defect count 10 reached", aborted["run_log"][-1]["message"])

    def test_high_defect_abort_leaves_small_result_unchanged(self):
        result = {"defect_count": 2, "defects": [{}, {}], "status": "Complete"}
        self.assertIs(apply_high_defect_abort(result, 10), result)
        self.assertEqual(result["status"], "Complete")

    def test_vnc_bandwidth_collection_reports_no_defects_and_jobdumps(self):
        recipe = _recipe()
        recipe["tests"][0]["sensitivity"] = {
            "vnc": {"enabled": True, "mode": "Collect Bandwidth"}
        }
        setup = default_run_setup(recipe)
        setup["lot_id"] = "BW-COLLECT"
        result = generate_inspection_result(recipe, setup)
        self.assertEqual(result["defect_count"], 0)
        self.assertEqual(len(result["jobdump_files"]), 16)
        self.assertTrue(
            any(
                "bandwidth collection" in item["message"]
                for item in result["run_log"]
            )
        )

    def test_ido_run_saves_feature_vectors_and_rough_codes(self):
        recipe = _recipe()
        recipe["tests"][0].update(
            {
                "run_ido": True,
                "save_feature_vectors": True,
                "ido_classifier": {
                    "name": "Production iDO",
                    "type": "iDO",
                    "rough_code": "R7",
                },
            }
        )
        setup = default_run_setup(recipe)
        setup["lot_id"] = "IDO-RUN"
        result = generate_inspection_result(recipe, setup)
        self.assertEqual(result["feature_vector_file"], "FeatureVectors.bin")
        self.assertEqual(result["classifier_execution"][0]["source"], "iDO")
        self.assertTrue(result["defects"])
        self.assertTrue(all(item["ido_rough_code"] == "R7" for item in result["defects"]))
        self.assertTrue(all(item["ido_rough_group"].startswith("G") for item in result["defects"]))

    def test_nef_run_filters_or_keeps_deterministic_nuisance_defects(self):
        recipe = _recipe()
        recipe["tests"][0].update(
            {
                "run_nef": True,
                "nef": {
                    "classifiers": [{"name": "Line Filter", "type": "ST-NEF", "st_nef": True}],
                    "keep_nuisance_defects": False,
                },
            }
        )
        setup = default_run_setup(recipe)
        setup["lot_id"] = "NEF-RUN"
        filtered = generate_inspection_result(recipe, setup)
        self.assertGreater(filtered["nef_filtered_count"], 0)
        recipe["tests"][0]["nef"]["keep_nuisance_defects"] = True
        kept = generate_inspection_result(recipe, setup)
        self.assertEqual(kept["nef_filtered_count"], 0)
        self.assertTrue(any(item.get("nuisance") for item in kept["defects"]))

    def test_nanopoint_run_combines_mdat_and_template_defects(self):
        recipe = _recipe()
        recipe["tests"][0]["nano_point_templates"] = {
            "valid": True,
            "images_grabbed": True,
            "poi_search_complete": True,
            "mca_size": 7,
            "templates": [{
                "name": "Weak Bridge",
                "search": True,
                "search_threshold": 0.82,
                "confidence": 0.94,
                "class_code": 27,
                "linked_care_area": "CAG Weak Bridge",
                "has_patch_images": True,
                "flips": ["Horizontal"],
            }],
        }
        setup = default_run_setup(recipe)
        setup["lot_id"] = "NPI-RUN"

        result = generate_inspection_result(recipe, setup)

        npi = [item for item in result["defects"] if item.get("npi_template")]
        mdat = [item for item in result["defects"] if not item.get("npi_template")]
        self.assertTrue(mdat)
        self.assertEqual(len(npi), 2)
        self.assertEqual(npi[0]["npi_template"], "Weak Bridge")
        self.assertEqual(npi[0]["npi_confidence"], 0.94)
        self.assertEqual(npi[0]["class_code"], 27)
        self.assertEqual(result["nanopoint_execution"][0]["counts"]["Weak Bridge"], 1)
        self.assertEqual(result["defect_count"], len(result["defects"]))

    def test_precision_sampling_marks_only_matching_defects(self):
        recipe = _recipe()
        recipe["wafer_post_processing"] = {"operations": [{
            "name": "Sampling",
            "enabled": True,
            "parameters": {
                "review_sampling": "Precision",
                "patch_sampling": "None",
                "patch_transfer_sampling": "None",
                "hi_res_sampling": "None",
                "maximum_samples": 5,
                "allow_filter_overlap": False,
                "precision_rules": [{
                    "name": "Large",
                    "filter": "Defect Size > 4",
                    "sampling_method": "Random Sampling",
                    "enabled": True,
                    "sampling_settings": {},
                }],
            },
        }]}
        setup = default_run_setup(recipe)
        setup["lot_id"] = "PRECISION"
        result = generate_inspection_result(recipe, setup)
        sampled = [item for item in result["defects"] if item["sampled_review"]]
        self.assertLessEqual(len(sampled), 5)
        self.assertTrue(sampled)
        self.assertTrue(all(item["size_um"] > 4 for item in sampled))
        self.assertEqual(result["wpp_execution"]["sampling"]["review_sampling"]["method"], "Precision")

    def test_excursion_reduction_marks_klarf_scope_without_deleting_results(self):
        recipe = _recipe()
        recipe["wafer_post_processing"] = {"operations": [
            {
                "name": "Sampling",
                "enabled": True,
                "parameters": {
                    "review_sampling": "Random/Class Code",
                    "patch_sampling": "None",
                    "patch_transfer_sampling": "None",
                    "hi_res_sampling": "None",
                    "maximum_samples": 7,
                    "method_settings": {"Random/Class Code": {"class_code_enabled": False}},
                },
            },
            {
                "name": "Excursion Reduction",
                "enabled": True,
                "parameters": {
                    "rules": [{"name": "Strong", "expression": "Intensity > 100", "enabled": True}],
                    "remove_non_sampled": True,
                    "data_transfer": "Filtered Result",
                },
            },
        ]}
        setup = default_run_setup(recipe)
        setup["lot_id"] = "EXCURSION"
        result = generate_inspection_result(recipe, setup)
        self.assertGreater(result["defect_count"], 7)
        self.assertEqual(result["wpp_execution"]["klarf_transfer_count"], 7)
        self.assertEqual(sum(item["klarf_included"] for item in result["defects"]), 7)
        self.assertTrue(any(item.get("excursion_rule") == "Strong" for item in result["defects"]))

    def test_wpp_without_sampling_keeps_all_defects_in_klarf(self):
        defects = [{"id": 1, "size_um": 1.0}, {"id": 2, "size_um": 2.0}]
        recipe = {"wafer_post_processing": {"operations": [{
            "name": "Excursion Reduction",
            "enabled": True,
            "parameters": {
                "rules": [{"name": "All", "expression": "Defect Size > 0", "enabled": True}],
                "remove_non_sampled": True,
            },
        }]}}
        processed, report = apply_wafer_post_processing(defects, recipe)
        self.assertEqual(report["klarf_transfer_count"], 2)
        self.assertTrue(all(item["klarf_included"] for item in processed))

    def test_venn_filters_duplicates_by_highest_intensity(self):
        defects = [
            {"id": 1, "test": "Test 1", "x_um": 100.0, "y_um": 200.0, "signal": 30.0},
            {"id": 2, "test": "Test 2", "x_um": 103.0, "y_um": 204.0, "signal": 80.0},
            {"id": 3, "test": "Test 1", "x_um": 500.0, "y_um": 500.0, "signal": 20.0},
        ]
        recipe = {"wafer_post_processing": {"operations": [{
            "name": "Venn",
            "enabled": True,
            "parameters": {
                "default_tolerance_um": 5.0,
                "enable_multi_test": False,
                "clear_venn_ids": True,
                "duplicate_mode": "Highest Intensity",
            },
        }]}}
        processed, report = apply_wafer_post_processing(defects, recipe)
        self.assertEqual([item["id"] for item in processed], [2, 3, 1])
        self.assertEqual(processed[0]["venn_duplicate_ids"], [1])
        self.assertTrue(processed[2]["multi_test_duplicate"])
        self.assertEqual(processed[2]["duplicate_of"], 2)
        self.assertFalse(processed[2]["klarf_included"])
        self.assertEqual(report["venn"]["duplicates_removed"], 1)
        self.assertEqual(report["klarf_transfer_count"], 2)

    def test_venn_honors_group_tolerance_and_test_priority(self):
        defects = [
            {"id": 10, "test": "Test 1", "x_um": 0.0, "y_um": 0.0, "signal": 100.0},
            {"id": 20, "test": "Test 2", "x_um": 8.0, "y_um": 0.0, "signal": 10.0},
        ]
        recipe = {"wafer_post_processing": {"operations": [{
            "name": "Venn",
            "enabled": True,
            "parameters": {
                "default_tolerance_um": 5.0,
                "enable_multi_test": True,
                "clear_venn_ids": True,
                "test_groups": [{
                    "name": "Priority",
                    "tests": "Test 1, Test 2",
                    "use_default_tolerance": False,
                    "tolerance_um": 10.0,
                    "inspected_area_mode": "Area of Largest Test",
                    "duplicate_mode": "Highest Prioritized Test ID",
                    "test_priority": "Test 2, Test 1",
                }],
            },
        }]}}
        processed, report = apply_wafer_post_processing(defects, recipe)
        self.assertEqual([item["id"] for item in processed], [20, 10])
        self.assertTrue(processed[1]["multi_test_duplicate"])
        self.assertEqual(report["venn"]["groups"][0]["tolerance_um"], 10.0)
        self.assertEqual(report["venn"]["groups"][0]["duplicate_mode"], "Highest Prioritized Test ID")

    def test_clustering_groups_close_defects_and_honors_each_test(self):
        defects = [
            {"id": 1, "test": "Test 1", "x_um": 0.0, "y_um": 0.0},
            {"id": 2, "test": "Test 1", "x_um": 50.0, "y_um": 0.0},
            {"id": 3, "test": "Test 2", "x_um": 20.0, "y_um": 0.0},
            {"id": 4, "test": "Test 1", "x_um": 10000.0, "y_um": 10000.0},
        ]
        clustering = {
            "name": "Clustering",
            "enabled": True,
            "parameters": {
                "auto_clustering": False,
                "minimum_defects": 2,
                "distance_threshold_um": 100.0,
                "second_pass_multiplier": 1,
                "cluster_within": "Each Test",
            },
        }
        recipe = {"wafer_post_processing": {"operations": [clustering]}}
        processed, report = apply_wafer_post_processing(defects, recipe)
        self.assertEqual([item["cluster_id"] for item in processed], [1, 1, 0, 0])
        self.assertEqual(report["clustering"]["cluster_count"], 1)
        self.assertEqual(report["clustering"]["clustered_defect_count"], 2)

        clustering["parameters"]["cluster_within"] = "All Tests"
        processed, report = apply_wafer_post_processing(defects, recipe)
        self.assertEqual([item["cluster_id"] for item in processed], [1, 1, 1, 0])
        self.assertEqual(report["clustering"]["clustered_defect_count"], 3)

    def test_auto_clustering_reports_generated_threshold(self):
        defects = [
            {"id": index, "test": "Test 1", "x_um": index * 10.0, "y_um": 0.0}
            for index in range(4)
        ]
        recipe = {"wafer_post_processing": {"operations": [{
            "name": "Clustering",
            "enabled": True,
            "parameters": {
                "auto_clustering": True,
                "minimum_defects": 2,
                "second_pass_multiplier": 3,
                "cluster_within": "All Tests",
            },
        }]}}
        _processed, report = apply_wafer_post_processing(defects, recipe)
        self.assertTrue(report["clustering"]["auto"])
        self.assertGreaterEqual(report["clustering"]["distance_threshold_um"], 100.0)

    def test_repeater_analysis_marks_coincident_die_locations(self):
        defects = [
            {"id": 1, "die_x": 1, "die_y": 0, "die_local_x_um": 25.0, "die_local_y_um": 30.0},
            {"id": 2, "die_x": 2, "die_y": 0, "die_local_x_um": 27.0, "die_local_y_um": 31.0},
            {"id": 3, "die_x": 3, "die_y": 0, "die_local_x_um": 24.0, "die_local_y_um": 29.0},
            {"id": 4, "die_x": 4, "die_y": 1, "die_local_x_um": 100.0, "die_local_y_um": 100.0},
        ]
        recipe = {"wafer_post_processing": {"operations": [{
            "name": "Repeater Analysis",
            "enabled": True,
            "parameters": {
                "algorithm": "Wafer",
                "x_tolerance_um": 5.0,
                "y_tolerance_um": 5.0,
                "repeater_threshold": 3,
            },
        }]}}
        processed, report = apply_wafer_post_processing(defects, recipe)
        self.assertEqual([item["repeater"] for item in processed], [True, True, True, False])
        self.assertEqual(report["repeater"]["repeater_count"], 1)
        self.assertEqual(report["repeater"]["repeater_defect_count"], 3)

    def test_cag_assignment_maps_care_area_group_names(self):
        defects = [
            {"id": 1, "care_area_group": "Critical"},
            {"id": 2, "region_id": "Background"},
            {"id": 3, "region_id": "Unknown"},
        ]
        recipe = {"wafer_post_processing": {"operations": [{
            "name": "CAG Code Assignment",
            "enabled": True,
            "parameters": {"cag_name_code_map": "Critical: 10; Background = 20"},
        }]}}
        processed, report = apply_wafer_post_processing(defects, recipe)
        self.assertEqual([item.get("cag_code") for item in processed], [10, 20, None])
        self.assertEqual(report["cag_assignment"]["assigned_count"], 2)

    def test_spatial_population_and_arbitration_assign_signature_and_majority_bin(self):
        defects = [
            {"id": 1, "cluster_id": 7, "x_um": 0.0, "y_um": 0.0, "roughbin": 4},
            {"id": 2, "cluster_id": 7, "x_um": 100.0, "y_um": 2.0, "roughbin": 4},
            {"id": 3, "cluster_id": 7, "x_um": 200.0, "y_um": 3.0, "roughbin": 6},
            {"id": 4, "cluster_id": 7, "x_um": 300.0, "y_um": 4.0, "roughbin": 9},
        ]
        recipe = {"wafer_post_processing": {"operations": [
            {
                "name": "Spatial Population",
                "enabled": True,
                "parameters": {
                    "signature_category": "Scratch",
                    "ssa_recipe": "Scratch",
                    "class_code_map": "1: Scratch",
                },
            },
            {
                "name": "Population Arbitration",
                "enabled": True,
                "parameters": {
                    "exclude_codes": "9",
                    "arbitrate_spatial_population": True,
                },
            },
        ]}}
        processed, report = apply_wafer_post_processing(defects, recipe)
        self.assertTrue(all(item.get("macro_sig_class") == 1 for item in processed))
        self.assertEqual([item["roughbin"] for item in processed], [4, 4, 4, 9])
        self.assertEqual(report["spatial_population"]["signature_count"], 1)
        self.assertEqual(report["population_arbitration"]["changed_count"], 1)

    def test_dsa_marks_adders_removes_common_and_adds_upld_last(self):
        defects = [
            {"id": 1, "test": "Test 1", "x_um": 100.0, "y_um": 100.0, "class_code": 4},
            {"id": 2, "test": "Test 1", "x_um": 900.0, "y_um": 900.0, "class_code": 5},
        ]
        previous_results = [{
            "id": "previous",
            "created": "2026-09-05 10:00:00",
            "lot_id": "LOT-1",
            "wafer_id": "W01",
            "step": "Layer A",
            "defects": [
                {"id": 10, "x_um": 105.0, "y_um": 100.0, "class_code": 0},
                {"id": 11, "x_um": 500.0, "y_um": 500.0, "class_code": 0},
            ],
        }]
        recipe = {"wafer_post_processing": {"operations": [{
            "name": "Defect Source Analysis",
            "enabled": True,
            "parameters": {
                "same_lot_id": True,
                "same_wafer_id": True,
                "same_scribe_id": False,
                "search_mode": "Point-Based Search",
                "tolerance_um": 10.0,
                "matching_mode": "All Defects Within Tolerance",
                "layer_selection": "All Previous",
                "last_scan_only": True,
                "pre_align": "Using Die Grids",
                "remove_common_defects": True,
                "dsa_plus": True,
                "upld_class_codes": "0",
                "reset_upld_class_codes": True,
                "upld_test_id": 50,
                "grab_optical_images": True,
                "grab_reference_images": True,
                "send_images_to_database": True,
                "maximum_images": 1,
            },
        }]}}
        processed, report = apply_wafer_post_processing(
            defects,
            recipe,
            previous_results=previous_results,
            context={"lot_id": "LOT-1", "wafer_id": "W01"},
        )
        self.assertEqual([item["id"] for item in processed], [2, 3])
        self.assertTrue(processed[0]["adder"])
        self.assertTrue(processed[-1]["upld"])
        self.assertEqual(processed[-1]["test_id"], 50)
        self.assertTrue(processed[-1]["has_reference_image"])
        self.assertEqual(report["dsa"]["matched_current_count"], 1)
        self.assertEqual(report["dsa"]["common_removed_count"], 1)
        self.assertEqual(report["dsa"]["upld_count"], 1)
        self.assertEqual(report["klarf_transfer_count"], 2)

    def test_dsa_identity_filter_leaves_all_current_defects_as_adders(self):
        defects = [{"id": 1, "x_um": 0.0, "y_um": 0.0}]
        recipe = {"wafer_post_processing": {"operations": [{
            "name": "Defect Source Analysis",
            "enabled": True,
            "parameters": {
                "same_lot_id": True,
                "same_wafer_id": True,
                "search_mode": "Point-Based Search",
                "tolerance_um": 20.0,
                "layer_selection": "All Previous",
                "last_scan_only": True,
            },
        }]}}
        processed, report = apply_wafer_post_processing(
            defects,
            recipe,
            previous_results=[{
                "lot_id": "OTHER", "wafer_id": "W01", "step": "A",
                "defects": [{"id": 2, "x_um": 0.0, "y_um": 0.0}],
            }],
            context={"lot_id": "LOT-1", "wafer_id": "W01"},
        )
        self.assertTrue(processed[0]["adder"])
        self.assertEqual(report["dsa"]["layers_compared"], 0)

    def test_wpp_executes_enabled_operations_in_recipe_order(self):
        defects = [
            {"id": 1, "test": "Test 1", "x_um": 0.0, "y_um": 0.0, "size_um": 1.0},
            {"id": 2, "test": "Test 1", "x_um": 10.0, "y_um": 0.0, "size_um": 2.0},
            {"id": 3, "test": "Test 1", "x_um": 20.0, "y_um": 0.0, "size_um": 3.0},
        ]
        sampling = {
            "name": "Sampling", "enabled": True,
            "parameters": {
                "review_sampling": "Random/Class Code", "patch_sampling": "None",
                "patch_transfer_sampling": "None", "hi_res_sampling": "None",
                "maximum_samples": 1, "method_settings": {"Random/Class Code": {}},
            },
        }
        excursion = {
            "name": "Excursion Reduction", "enabled": True,
            "parameters": {"rules": [], "remove_non_sampled": True},
        }
        recipe = {"wafer_post_processing": {"operations": [excursion, sampling]}}
        _processed, report = apply_wafer_post_processing(defects, recipe)
        self.assertEqual(report["execution_order"], ["Excursion Reduction", "Sampling"])
        self.assertEqual(report["klarf_transfer_count"], 3)

        recipe["wafer_post_processing"]["operations"] = [sampling, excursion]
        _processed, report = apply_wafer_post_processing(defects, recipe)
        self.assertEqual(report["execution_order"], ["Sampling", "Excursion Reduction"])
        self.assertEqual(report["klarf_transfer_count"], 1)

    def test_job_execution_plan_runs_primary_first_and_honors_slot_order(self):
        recipes = [
            {"id": "secondary", "inspection": "Secondary", "tests": [{"name": "S1", "mode": "Random"}]},
            {"id": "primary", "inspection": "Primary", "tests": [{"name": "P1", "mode": "Random"}]},
        ]
        job = {
            "inspection_ids": ["secondary", "primary"],
            "primary_inspection_id": "primary",
            "slot_order": "Top Down",
            "setup": {"lot_id": "LOT"},
            "lot_ids": {"primary": "LOT-P", "secondary": "LOT-S"},
            "slot_plans": [
                {"slot": 1, "wafer_id": "W01", "repeat_count": 2, "inspection_ids": ["secondary", "primary"]},
                {"slot": 25, "wafer_id": "W25", "repeat_count": 1, "inspection_ids": ["secondary", "primary"]},
            ],
        }
        plan = job_execution_plan(job, recipes)
        self.assertEqual([(item["slot"], item["recipe_id"]) for item in plan], [
            (25, "primary"), (25, "secondary"), (1, "primary"), (1, "secondary")
        ])
        self.assertEqual(plan[0]["lot_id"], "LOT-P")
        self.assertEqual(plan[2]["repeat_count"], 2)


if __name__ == "__main__":
    unittest.main()

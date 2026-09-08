from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from puma_ui.qt_compat import QApplication, QDialog
from puma_ui.modules.wafer_post_processing import (
    default_wpp_state,
    normalized_wpp_state,
    validate_wpp,
)
from puma_ui.modules.wafer_post_processing.dialog import (
    ClassCodeRowsDialog,
    ExcursionRuleEditorDialog,
    MultiTestGroupsDialog,
    PrecisionFilterDialog,
    PrecisionRulesDialog,
    SamplingMethodSettingsDialog,
)


class WaferPostProcessingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_default_state_contains_manual_operations(self):
        names = [operation["name"] for operation in default_wpp_state()["operations"]]
        self.assertIn("Venn", names)
        self.assertIn("Defect Source Analysis", names)
        self.assertIn("Repeater Analysis", names)
        self.assertIn("Spatial Population", names)
        self.assertIn("Sampling", names)
        self.assertIn("Excursion Reduction", names)
        self.assertNotIn("Multi-Test Merge", names)
        venn = default_wpp_state()["operations"][0]
        self.assertIn("enable_multi_test", venn["parameters"])

    def test_normalization_preserves_operation_order(self):
        state = default_wpp_state()
        state["operations"][0], state["operations"][1] = (
            state["operations"][1],
            state["operations"][0],
        )
        normalized = normalized_wpp_state(state)
        self.assertEqual(normalized["operations"][0]["name"], "Clustering")
        self.assertEqual(normalized["operations"][1]["name"], "Venn")

    def test_venn_requires_two_tests(self):
        state = default_wpp_state()
        state["operations"][0]["enabled"] = True
        self.assertIn(
            "Venn requires at least two defined tests",
            validate_wpp(state, test_count=1),
        )

    def test_defect_source_analysis_requires_match_identity(self):
        state = default_wpp_state()
        operation = next(
            item for item in state["operations"]
            if item["name"] == "Defect Source Analysis"
        )
        operation["enabled"] = True
        operation["parameters"]["same_lot_id"] = False
        operation["parameters"]["same_wafer_id"] = False
        self.assertIn(
            "Defect Source Analysis requires a Lot, Wafer, or Scribe ID match",
            validate_wpp(state, test_count=2),
        )

    def test_valid_sampling_configuration(self):
        state = default_wpp_state()
        operation = next(
            item for item in state["operations"] if item["name"] == "Sampling"
        )
        operation["parameters"]["review_sampling"] = "Smart"
        operation["parameters"]["maximum_samples"] = 25
        operation["enabled"] = True
        self.assertEqual(validate_wpp(state, test_count=1), [])

    def test_repeater_and_defect_limit_ranges(self):
        state = default_wpp_state()
        repeater = next(item for item in state["operations"] if item["name"] == "Repeater Analysis")
        repeater["enabled"] = True
        repeater["parameters"]["x_tolerance_um"] = 51
        limits = next(item for item in state["operations"] if item["name"] == "Defect Limits")
        limits["enabled"] = True
        limits["parameters"]["override_wafer_limit"] = True
        limits["parameters"]["override_test_limit"] = True
        limits["parameters"]["wafer_maximum_defects"] = 1000
        limits["parameters"]["test_maximum_defects"] = 1000
        errors = validate_wpp(state, test_count=2)
        self.assertIn("Repeater X tolerance must be between 1 and 50 um", errors)
        self.assertIn("Test maximum defect count must be less than wafer maximum", errors)

    def test_legacy_text_advanced_values_are_migrated(self):
        state = default_wpp_state()
        venn = next(item for item in state["operations"] if item["name"] == "Venn")
        sampling = next(item for item in state["operations"] if item["name"] == "Sampling")
        excursion = next(item for item in state["operations"] if item["name"] == "Excursion Reduction")
        venn["parameters"]["test_groups"] = "Production: Test 1, Test 2"
        sampling["parameters"]["precision_rules"] = "Defect Size > 5"
        excursion["parameters"]["rules"] = "Class Code = 4"
        normalized = normalized_wpp_state(state)
        venn = next(item for item in normalized["operations"] if item["name"] == "Venn")
        sampling = next(item for item in normalized["operations"] if item["name"] == "Sampling")
        excursion = next(item for item in normalized["operations"] if item["name"] == "Excursion Reduction")
        self.assertEqual(venn["parameters"]["test_groups"][0]["name"], "Production")
        self.assertEqual(sampling["parameters"]["precision_rules"][0]["filter"], "Defect Size > 5")
        self.assertEqual(excursion["parameters"]["rules"][0]["expression"], "Class Code = 4")

    def test_precision_sampling_requires_enabled_rule(self):
        state = default_wpp_state()
        sampling = next(item for item in state["operations"] if item["name"] == "Sampling")
        sampling["enabled"] = True
        sampling["parameters"]["review_sampling"] = "Precision"
        self.assertIn(
            "Precision Sampling requires at least one enabled rule",
            validate_wpp(state, test_count=2),
        )
        sampling["parameters"]["precision_rules"] = [{
            "name": "Large_Defects",
            "filter": "Defect Size > 5",
            "sampling_method": "Random Sampling",
            "enabled": True,
            "back_fill": False,
        }]
        self.assertEqual(validate_wpp(state, test_count=2), [])

    def test_precision_rules_preserve_independent_filter_and_sampling_settings(self):
        state = default_wpp_state()
        sampling = next(item for item in state["operations"] if item["name"] == "Sampling")
        sampling["parameters"]["precision_rules"] = [{
            "name": "Bright_Adders",
            "filter": "Adder=Adders; Polarity=Bright",
            "filter_mode": "Quick Filter",
            "quick_filter": {"adder": "Adders", "bright": True, "dark": False},
            "sampling_method": "Class Code Sampling",
            "sampling_settings": {
                "Random/Class Code": {
                    "class_code_enabled": True,
                    "class_code_rows": [{
                        "category": "RoughClass", "all_nonzero": True, "defects": 25, "unit": "%"
                    }],
                },
            },
            "enabled": True,
        }]
        normalized = normalized_wpp_state(state)
        sampling = next(item for item in normalized["operations"] if item["name"] == "Sampling")
        rule = sampling["parameters"]["precision_rules"][0]
        self.assertEqual(rule["quick_filter"]["adder"], "Adders")
        self.assertFalse(rule["quick_filter"]["dark"])
        code_row = rule["sampling_settings"]["Random/Class Code"]["class_code_rows"][0]
        self.assertEqual((code_row["defects"], code_row["unit"]), (25, "%"))

    def test_precision_filter_and_saved_rule_round_trip(self):
        filter_dialog = PrecisionFilterDialog(quick_filter={"adder": "Adders", "bright": True, "dark": False})
        filter_dialog._finish()
        self.assertEqual(filter_dialog.result(), QDialog.Accepted)
        self.assertIn("Adder=Adders", filter_dialog.result_filter)
        source = PrecisionRulesDialog([{
            "name": "Saved_Rule",
            "filter": filter_dialog.result_filter,
            "quick_filter": filter_dialog.result_quick_filter,
            "sampling_method": "Random Sampling",
            "enabled": True,
        }])
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "precision-rule.json")
            with patch(
                "puma_ui.modules.wafer_post_processing.dialog.QFileDialog.getSaveFileName",
                return_value=(path, "Precision Rule (*.json)"),
            ):
                source._save_rule()
            target = PrecisionRulesDialog([])
            with patch(
                "puma_ui.modules.wafer_post_processing.dialog.QFileDialog.getOpenFileName",
                return_value=(path, "Precision Rule (*.json)"),
            ):
                target._load_rule()
            self.assertEqual(target.table.rowCount(), 1)
            self.assertEqual(target._row_data(0)["name"], "Saved_Rule")

    def test_precision_rule_names_must_be_unique(self):
        state = default_wpp_state()
        sampling = next(item for item in state["operations"] if item["name"] == "Sampling")
        sampling["enabled"] = True
        sampling["parameters"]["review_sampling"] = "Precision"
        sampling["parameters"]["precision_rules"] = [
            {"name": "Rule_A", "filter": "All Defects", "enabled": True},
            {"name": "rule_a", "filter": "Defect Size > 2", "enabled": True},
        ]
        self.assertIn("Precision Sampling rule names must be unique", validate_wpp(state, test_count=2))

    def test_excursion_requires_complete_enabled_rule(self):
        state = default_wpp_state()
        excursion = next(item for item in state["operations"] if item["name"] == "Excursion Reduction")
        excursion["enabled"] = True
        excursion["parameters"]["rules"] = [{"name": "Keep_Large", "expression": "", "enabled": True}]
        self.assertIn(
            "Each enabled Excursion Reduction rule requires a name and expression",
            validate_wpp(state, test_count=1),
        )
        excursion["parameters"]["rules"][0]["expression"] = "Defect Size >= 10"
        self.assertEqual(validate_wpp(state, test_count=1), [])

    def test_excursion_reusable_expressions_are_normalized_and_preserved(self):
        state = default_wpp_state()
        excursion = next(item for item in state["operations"] if item["name"] == "Excursion Reduction")
        excursion["parameters"]["expressions"] = [{
            "name": "Large Defect",
            "expression": "Defect Size > 10",
            "element": "Defect Size",
            "operator": ">",
            "value": 10,
        }]
        normalized = normalized_wpp_state(state)
        excursion = next(item for item in normalized["operations"] if item["name"] == "Excursion Reduction")
        self.assertEqual(excursion["parameters"]["expressions"], [{
            "name": "Large_Defect",
            "definition": "Defect Size > 10",
            "element": "Defect Size",
            "operator": ">",
            "value": "10",
        }])

    def test_excursion_expression_names_must_be_unique(self):
        state = default_wpp_state()
        excursion = next(item for item in state["operations"] if item["name"] == "Excursion Reduction")
        excursion["enabled"] = True
        excursion["parameters"]["rules"] = [{
            "name": "Keep_Large",
            "expression": "Defect Size > 10",
            "enabled": True,
        }]
        excursion["parameters"]["expressions"] = [
            {"name": "Large", "definition": "Defect Size > 10"},
            {"name": "large", "definition": "Intensity > 5"},
        ]
        self.assertIn(
            "Excursion Reduction expression names must be unique",
            validate_wpp(state, test_count=1),
        )

    def test_excursion_editor_stores_and_uses_reusable_expression(self):
        dialog = ExcursionRuleEditorDialog([{
            "name": "Rule_1",
            "expression": "Defect Size > 1",
            "enabled": True,
        }])
        self.assertEqual(dialog.tabs.count(), 3)
        dialog.expression_name.setText("Large_Defect")
        dialog.expression_element.setCurrentText("Defect Size")
        dialog.expression_operator.setCurrentText(">")
        dialog.expression_value.setText("10")
        dialog._build_reusable_expression()
        dialog._store_expression()
        dialog.element.setCurrentText("Large_Defect")
        dialog.operator.setCurrentText("=")
        dialog.value.setText("True")
        dialog._build_expression()
        dialog._update()
        dialog._finish()
        self.assertEqual(dialog.result(), QDialog.Accepted)
        self.assertEqual(dialog.result_expressions[0]["name"], "Large_Defect")
        self.assertIn("Defect Size > 10", dialog.result_rules[0]["expression"])

    def test_multi_test_groups_require_unique_names(self):
        state = default_wpp_state()
        venn = next(item for item in state["operations"] if item["name"] == "Venn")
        venn["enabled"] = True
        venn["parameters"]["enable_multi_test"] = True
        venn["parameters"]["test_groups"] = [
            {"name": "Group_A", "tests": "Test 1", "tolerance_um": 5},
            {"name": "Group_A", "tests": "Test 2", "tolerance_um": 5},
        ]
        self.assertIn(
            "Multi-Test Venn group names must be unique",
            validate_wpp(state, test_count=2),
        )

    def test_multi_test_groups_preserve_manual_group_options(self):
        state = default_wpp_state()
        venn = next(item for item in state["operations"] if item["name"] == "Venn")
        venn["parameters"]["test_groups"] = [{
            "name": "Layer Match",
            "tests": "Test 1, Test 2",
            "use_default_tolerance": False,
            "tolerance_um": 7.5,
            "inspected_area_mode": "Sum of Selected Test Areas",
            "area_tests": "Test 1, Test 2",
            "duplicate_mode": "Highest Prioritized Test ID",
            "test_priority": "Test 2, Test 1",
        }]
        normalized = normalized_wpp_state(state)
        group = normalized["operations"][0]["parameters"]["test_groups"][0]
        self.assertEqual(group["name"], "Layer_Match")
        self.assertFalse(group["use_default_tolerance"])
        self.assertEqual(group["tolerance_um"], 7.5)
        self.assertEqual(group["area_tests"], "Test 1, Test 2")
        self.assertEqual(group["test_priority"], "Test 2, Test 1")

    def test_multi_test_group_requires_area_and_priority_tests(self):
        state = default_wpp_state()
        venn = next(item for item in state["operations"] if item["name"] == "Venn")
        venn["enabled"] = True
        venn["parameters"]["enable_multi_test"] = True
        venn["parameters"]["test_groups"] = [{
            "name": "Group_A",
            "tests": "Test 1, Test 2",
            "inspected_area_mode": "Sum of Selected Test Areas",
            "area_tests": "",
            "duplicate_mode": "Highest Prioritized Test ID",
            "test_priority": "",
        }]
        errors = validate_wpp(state, test_count=2)
        self.assertIn("Each summed Multi-Test Venn area requires selected tests", errors)
        self.assertIn("Each prioritized Multi-Test Venn group requires a Test ID priority order", errors)

    def test_multi_test_group_editor_reorders_test_priority(self):
        dialog = MultiTestGroupsDialog([{
            "name": "Group_A",
            "tests": "Test 1, Test 2, Test 3",
            "duplicate_mode": "Highest Prioritized Test ID",
            "test_priority": "Test 1, Test 2, Test 3",
        }])
        dialog.table.selectRow(0)
        dialog._refresh_priority_selector()
        dialog.priority_test.setCurrentText("Test 2")
        dialog._move_priority(-1)
        self.assertEqual(dialog.table.item(0, 7).text(), "Test 2, Test 1, Test 3")
        dialog._finish()
        self.assertEqual(dialog.result(), QDialog.Accepted)
        self.assertEqual(dialog.result_groups[0]["test_priority"], "Test 2, Test 1, Test 3")

    def test_sampling_method_settings_are_initialized(self):
        state = default_wpp_state()
        sampling = next(item for item in state["operations"] if item["name"] == "Sampling")
        settings = sampling["parameters"]["method_settings"]
        self.assertEqual(settings["Diversity"]["scheme"], "Discovery")
        self.assertEqual(settings["Random/Class Code"]["maximum_per_wafer"], 100)
        self.assertEqual(settings["Smart"]["target_samples"], 100)

    def test_diversity_and_random_class_code_specialized_editors(self):
        dialog = SamplingMethodSettingsDialog(default_wpp_state()["operations"][7]["parameters"]["method_settings"])
        self.assertIn("diversification_attributes", dialog.controls)
        dialog.method.setCurrentText("Random/Class Code")
        self.assertEqual(dialog.random_class_tabs.count(), 2)
        self.assertEqual(dialog.random_class_tabs.tabText(0), "Random Sampling")
        self.assertEqual(dialog.random_class_tabs.tabText(1), "Class Code Sampling")
        rows = ClassCodeRowsDialog([])
        rows._append({"category": "RoughClass", "all_nonzero": True, "defects": 100, "unit": "%"})
        rows._finish()
        self.assertEqual(rows.result(), QDialog.Accepted)
        self.assertTrue(rows.result_rows[0]["all_nonzero"])

    def test_class_code_sampling_requires_rows(self):
        state = default_wpp_state()
        sampling = next(item for item in state["operations"] if item["name"] == "Sampling")
        sampling["enabled"] = True
        sampling["parameters"]["review_sampling"] = "Random/Class Code"
        settings = sampling["parameters"]["method_settings"]["Random/Class Code"]
        settings["class_code_enabled"] = True
        settings["class_code_rows"] = []
        self.assertIn(
            "Class Code Sampling requires at least one category or code row",
            validate_wpp(state, test_count=2),
        )

    def test_random_sampling_manual_ranges(self):
        state = default_wpp_state()
        sampling = next(item for item in state["operations"] if item["name"] == "Sampling")
        sampling["enabled"] = True
        sampling["parameters"]["review_sampling"] = "Random/Class Code"
        random = sampling["parameters"]["method_settings"]["Random/Class Code"]
        random["maximum_per_wafer"] = 10
        random["maximum_per_die"] = 11
        random["maximum_per_cluster"] = 1
        random["percent_from_clusters"] = 101
        errors = validate_wpp(state, test_count=2)
        self.assertIn("Random maximum per die must be between 1 and the wafer maximum", errors)
        self.assertIn("Random maximum per cluster must be between 2 and 65000", errors)
        self.assertIn("Random percent from clusters must be between 0 and 100", errors)

    def test_diversity_trigger_and_smart_ranges(self):
        state = default_wpp_state()
        sampling = next(item for item in state["operations"] if item["name"] == "Sampling")
        sampling["enabled"] = True
        sampling["parameters"]["review_sampling"] = "Diversity"
        sampling["parameters"]["patch_sampling"] = "Trigger"
        sampling["parameters"]["hi_res_sampling"] = "Smart"
        settings = sampling["parameters"]["method_settings"]
        settings["Diversity"]["discovery_samples"] = 1001
        settings["Trigger"]["lower_bound"] = 200
        settings["Trigger"]["upper_bound"] = 100
        settings["Smart"]["target_samples"] = 1001
        errors = validate_wpp(state, test_count=2)
        self.assertIn("Diversity defects to sample must be between 0 and 1000", errors)
        self.assertIn("Trigger lower zone bound must not exceed upper bound", errors)
        self.assertIn("Smart target defects must be between 0 and 1000", errors)


if __name__ == "__main__":
    unittest.main()

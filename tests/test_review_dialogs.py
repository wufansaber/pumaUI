from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from puma_ui.qt_compat import QApplication, QDialog, Qt
from puma_ui.modules.results_review.dialogs import (
    AdvancedSensitivityParametersDialog,
    LotResultColumnsDialog,
    DefectDisplayRulesDialog,
    CombineSensitivityResultsDialog,
    OpticsSelectorDialog,
    ReviewImageGrabDialog,
    ReviewWorkspace,
    SelectLotResultsDialog,
    SensitivityTunerDialog,
    SensitivityMaxLimitsDialog,
    STNEFPartitionsDialog,
    STNEFTunerDialog,
    SuperClassDialog,
    WaferDataTransferDialog,
)
from puma_ui.modules.run_control import generate_inspection_result
from puma_ui.recipe_store import RecipeStore


class ReviewDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = RecipeStore(Path(self.temp_dir.name) / "recipes.json")
        self.recipe = {
            "id": "recipe-1",
            "inspection": "Deep",
            "device": "D1",
            "step": "Metal",
            "tests": [{"name": "Test 1"}],
        }
        self.result = generate_inspection_result(
            self.recipe,
            {"lot_id": "LOT-1", "wafer_id": "W01", "selected_tests": ["Test 1"]},
        )
        self.result = self.store.save_result(self.result)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_review_workspace_scrolls_instead_of_compressing_at_minimum_size(self):
        dialog = ReviewWorkspace(self.result, store=self.store, current_recipe=self.recipe)
        dialog.resize(980, 650)
        dialog.show()
        QApplication.processEvents()
        self.assertGreater(dialog.workspace_scroll.horizontalScrollBar().maximum(), 0)
        self.assertGreater(dialog.workspace_scroll.verticalScrollBar().maximum(), 0)
        self.assertGreaterEqual(dialog.workspace.width(), 1500)
        self.assertGreaterEqual(dialog.workspace.height(), 820)
        dialog.close()

    def test_review_menu_direct_tools_dispatch_to_the_requested_workflow(self):
        dialog = ReviewWorkspace(self.result, store=self.store, current_recipe=self.recipe)
        with patch.object(dialog, "_adjust_offset") as adjust:
            dialog.open_manual_tool("adjust_defect_location")
            adjust.assert_called_once_with(False)
            adjust.reset_mock()
            dialog.open_manual_tool("adjust_die_origin")
            adjust.assert_called_once_with(True)
        with patch.object(dialog, "_optics_selector") as optics:
            dialog.open_manual_tool("optics_selector")
            optics.assert_called_once_with()
        with patch.object(dialog, "_sensitivity_tuner") as sensitivity:
            dialog.open_manual_tool("sensitivity_tuner")
            sensitivity.assert_called_once_with()
        dialog.close()

    def test_review_bulk_mark_sampling_and_status_bar_follow_manual(self):
        dialog = ReviewWorkspace(self.result, store=self.store, current_recipe=self.recipe)
        identifiers = [item["id"] for item in dialog.result["defects"][:2]]
        dialog.selected_ids = set(identifiers)
        dialog._mark_selected(True)
        dialog._sample_marked()
        sampled = [
            item
            for item in dialog.result["defects"]
            if item.get("id") in identifiers
        ]
        self.assertTrue(all(item.get("marked") for item in sampled))
        self.assertTrue(all(item.get("sampled_review") for item in sampled))
        self.assertIn("Lot: LOT-1", dialog.status.text())
        dialog._clear_all_marks()
        self.assertFalse(any(item.get("marked") for item in dialog.result["defects"]))

    def test_select_lot_records_mode_and_recent_item(self):
        dialog = SelectLotResultsDialog(self.store, self.recipe)
        self.assertEqual(dialog.table.rowCount(), 1)
        dialog.review_mode.setCurrentText("Inspected Wafer")
        dialog._open()
        self.assertEqual(dialog.result(), QDialog.Accepted)
        self.assertEqual(dialog.selected_result["review_mode"], "Inspected Wafer")
        self.assertTrue(self.store.get_result(self.result["id"])["review_recent"])

        recent = SelectLotResultsDialog(self.store, self.recipe)
        recent.source.setCurrentText("Recent Items")
        self.assertEqual(recent.table.rowCount(), 1)

    def test_lot_column_selection(self):
        dialog = LotResultColumnsDialog(["lot_id", "wafer_id"])
        dialog.checks["wafer_id"].setChecked(False)
        dialog._finish()
        self.assertEqual(dialog.result_columns, ["lot_id"])

    def test_image_grab_settings_enforce_review_optics_for_full_frame(self):
        dialog = ReviewImageGrabDialog(["Test 1"])
        dialog.full_frame_mode.setChecked(True)
        dialog.optics.setCurrentText("Use Inspection Test")
        self.assertTrue(dialog.image_size_mode.isChecked())
        self.assertFalse(dialog.full_frame_mode.isEnabled())
        dialog._finish()
        self.assertEqual(dialog.result_settings["image_optics"], "Use Inspection Test")
        self.assertEqual(dialog.result_settings["acquisition"], "Image Size")

    def test_transfer_variants_are_stored_separately(self):
        dialog = ReviewWorkspace(self.result, store=self.store, current_recipe=self.recipe)
        dialog._send_images()
        transfer_options = {
            "scope": "All Defects",
            "include_duplicates": False,
            "defect_ids": [item["id"] for item in dialog.result["defects"]],
            "defect_count": len(dialog.result["defects"]),
        }
        with patch(
            "puma_ui.modules.results_review.dialogs.WaferDataTransferDialog"
        ) as transfer_dialog, patch(
            "puma_ui.modules.results_review.dialogs._exec", return_value=QDialog.Accepted
        ):
            transfer_dialog.return_value.result_options = transfer_options
            dialog._send_wafer()
        dialog._send_lot()
        transfer = dialog.result["transfer"]
        self.assertIn("lot image", transfer["images_state"])
        self.assertEqual(transfer["wafer_state"], "Transferred")
        self.assertEqual(transfer["wafer_defect_count"], len(dialog.result["defects"]))
        self.assertEqual(transfer["lot_state"], "Transferred")

    def test_wafer_transfer_dialog_matches_manual_options(self):
        self.result["defects"][0]["multi_test_duplicate"] = True
        dialog = WaferDataTransferDialog(self.result, self.result["defects"][:3])
        self.assertTrue(dialog.send_all.isChecked())
        self.assertFalse(dialog.include_duplicates.isChecked())
        dialog.include_duplicates.setChecked(True)
        dialog._finish()
        self.assertEqual(dialog.result(), QDialog.Accepted)
        self.assertTrue(dialog.result_options["include_duplicates"])
        self.assertEqual(dialog.result_options["defect_count"], len(self.result["defects"]))

    def test_optics_selector_marks_adds_analyzes_and_restores(self):
        self.result["defects"][0]["marked"] = True
        dialog = OpticsSelectorDialog(self.result, self.recipe)
        dialog._add_mode()
        dialog._analyze()
        self.assertEqual(len(dialog.scores), 1)
        dialog._add_to_recipe()
        self.assertEqual(self.recipe["tests"][-1]["source"], "Optics Selector")
        dialog._finish()
        restored = OpticsSelectorDialog(self.result, self.recipe, dialog.result_state)
        self.assertEqual(len(restored.modes), 1)
        self.assertEqual(len(restored.scores), 1)

    def test_advanced_classify_folders_chart_and_grid_columns(self):
        dialog = ReviewWorkspace(self.result, store=self.store, current_recipe=self.recipe)
        dialog.layout_mode.setCurrentText("Advanced Classify")
        original_count = len(dialog.visible_defects)
        self.assertGreater(dialog.class_folders.rowCount(), 0)
        dialog.class_folders.item(0, 0).setCheckState(Qt.Unchecked)
        self.assertLess(len(dialog.visible_defects), original_count)
        dialog.chart_type.setCurrentText("Pareto")
        dialog.summary_mode.setCurrentText("Classification Summary")
        self.assertEqual(dialog.chart.chart_type, "Pareto")
        self.assertTrue(dialog.summary.text().startswith("Classification"))
        original_columns = len(dialog.grid_columns)
        dialog._hide_grid_column(1)
        self.assertEqual(len(dialog.grid_columns), original_columns - 1)
        dialog._show_all_grid_columns()
        self.assertEqual(len(dialog.grid_columns), original_columns)

    def test_sensitivity_tuner_commits_and_returns_review_filter(self):
        self.result["sensitivity_data"] = True
        self.result["sensitivity_data_tests"] = ["Test 1"]
        dialog = SensitivityTunerDialog(self.result, self.recipe)
        dialog.value.setValue(120)
        dialog._commit()
        dialog.show_mode.setCurrentText("Show Detected Defects")
        dialog.filter_scope.setCurrentText("Filter to Current Parameter")
        dialog._finish()
        self.assertTrue(dialog.result_state["committed"])
        self.assertEqual(dialog.result_state["value"], 120)
        self.assertGreater(dialog.result_state["evaluation"]["considered"], 0)
        self.assertLessEqual(
            dialog.result_state["evaluation"]["detected"],
            dialog.result_state["evaluation"]["considered"],
        )

    def test_sensitivity_tuner_catch_lose_save_as_and_export(self):
        self.result["sensitivity_data"] = True
        self.result["sensitivity_data_tests"] = ["Test 1"]
        dialog = SensitivityTunerDialog(self.result, self.recipe)
        signal = float(self.result["defects"][0]["signal"])
        dialog._auto_tune_defect(True)
        self.assertLess(dialog.value.value(), signal)
        dialog._auto_tune_defect(False)
        self.assertGreater(dialog.value.value(), signal)
        dialog.finish_action.setCurrentText("Save Recipe As...")
        dialog.save_name.setText("Tuned Recipe")
        dialog._finish()
        self.assertEqual(dialog.result_state["recipe_identity"]["inspection"], "Tuned Recipe")

        exported = SensitivityTunerDialog(self.result, self.recipe)
        exported.finish_action.setCurrentText("Export Recipe As...")
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "tuned.json")
            with patch(
                "puma_ui.modules.results_review.dialogs.QFileDialog.getSaveFileName",
                return_value=(path, "Recipe JSON (*.json)"),
            ):
                exported._finish()
            payload = Path(path).read_text(encoding="utf-8")
            self.assertIn("sensitivity_tuner_updates", payload)

    def test_sensitivity_tuner_plot_controls_and_nef_crosstalk_persist(self):
        self.result["sensitivity_data"] = True
        self.result["sensitivity_data_tests"] = ["Test 1"]
        state = {
            "nef_states": {"Test 1": {
                "classifiers": [{"name": "ST Filter", "type": "ST-NEF", "st_nef": True}],
                "keep_nuisance_defects": False,
            }},
            "nef_enabled_tests": ["Test 1"],
        }
        dialog = SensitivityTunerDialog(self.result, self.recipe, state)
        self.assertTrue(dialog.enable_nef.isChecked())
        self.assertTrue(dialog.nef_filtered_ids)
        dialog.partition.setCurrentText("Class Code")
        dialog.plot_scale.setCurrentText("Log Y")
        dialog.plot_grid.setChecked(True)
        dialog.plot_legend.setChecked(True)
        dialog.group_size.setValue(5)
        dialog.plot_zoom.setValue(175)
        dialog._finish()
        self.assertEqual(dialog.result_state["partition"], "Class Code")
        self.assertEqual(dialog.result_state["plot_scale"], "Log Y")
        self.assertTrue(dialog.result_state["plot_grid"])
        self.assertEqual(dialog.result_state["plot_zoom"], 175)
        self.assertIn("Test 1", dialog.result_state["nef_enabled_tests"])
        self.assertTrue(dialog.result_state["nef_filtered_ids"])

    def test_sensitivity_tuner_keeps_independent_parameter_values_and_commits(self):
        dialog = SensitivityTunerDialog(self.result, self.recipe)
        dialog.value.setValue(123.0)
        dialog._commit()
        threshold_key = dialog._selection_key()
        dialog.parameter.setCurrentText("Noise")
        self.assertEqual(dialog.value.value(), 1.0)
        dialog.value.setValue(2.0)
        noise_key = dialog._selection_key()
        self.assertNotEqual(threshold_key, noise_key)
        dialog.parameter.setCurrentText("Threshold")
        self.assertEqual(dialog.value.value(), 123.0)
        self.assertIn(threshold_key, dialog.committed_parameters)
        dialog._navigate(1, True)
        self.assertEqual(dialog.parameter.currentText(), "Noise")
        dialog._finish()
        self.assertEqual(dialog.result_state["parameter_values"][threshold_key], 123.0)
        self.assertIn(threshold_key, dialog.result_state["committed_parameters"])

    def test_advanced_sensitivity_parameters_are_editable_and_persisted(self):
        dialog = AdvancedSensitivityParametersDialog({}, SensitivityTunerDialog.PARAMETERS)
        threshold = dialog.tree.topLevelItem(0).child(0)
        threshold.setText(1, "88.5")
        dialog._finish()
        self.assertEqual(dialog.result_parameters["HLAT"]["Threshold"], 88.5)

    def test_sensitivity_tuner_restores_session_and_inspection_parameters(self):
        self.recipe["tests"][0]["sensitivity"] = {
            "regions": {"Default": {"algorithms": {"HLAT": {
                "channels": [{"Threshold": 61.0}],
            }}}},
        }
        probe = SensitivityTunerDialog(self.result, self.recipe)
        key = probe._selection_key()
        state = {
            "parameter_values": {key: 82.0},
            "edited_parameters": [key],
            "committed_parameters": [key],
            "nef_states": {"Test 1": {"classifiers": [{"name": "Session NEF"}]}},
            "nef_enabled_tests": ["Test 1"],
        }

        session = SensitivityTunerDialog(self.result, self.recipe, state)
        session.value.setValue(150.0)
        session.finish_action.setCurrentText("Restore Session - Parameters Only")
        session._finish()
        self.assertEqual(session.result_state["value"], 82.0)
        self.assertEqual(session.result_state["restored_from"], "Session Recipe")
        self.assertIn("Test 1", session.result_state["nef_enabled_tests"])

        inspection = SensitivityTunerDialog(self.result, self.recipe, state)
        inspection.finish_action.setCurrentText("Restore Inspection - Parameters Only")
        inspection._finish()
        self.assertEqual(inspection.result_state["value"], 61.0)
        self.assertEqual(inspection.result_state["parameter_values"][key], 61.0)
        self.assertEqual(inspection.result_state["edited_parameters"], [])
        self.assertIn("Test 1", inspection.result_state["nef_enabled_tests"])

    def test_st_nef_partitions_and_hierarchical_classifier_persist(self):
        partitions = STNEFPartitionsDialog([{"name": "Review", "classes": [1, 2]}])
        partitions._add_row({"name": "Nuisance", "classes": [0, 9]})
        partitions._finish()
        self.assertEqual(partitions.result_partitions[1]["classes"], [0, 9])

        dialog = STNEFTunerDialog(self.result)
        dialog._generate_starter_tree({
            "attributes": ["Primary Ch Intensity", "Area"],
            "partitions": partitions.result_partitions,
        })
        starter = dialog._selected_node()
        self.assertEqual(starter["type"], "Attribute")
        self.assertEqual(len(starter["attributes"]), 2)
        self.assertEqual(dialog.property_chart.chart_type, "Scatter")
        original_points = len(dialog.property_chart.points)
        self.result["defects"][0]["class_code"] = 0
        dialog.hide_unclassified.setChecked(True)
        self.assertLess(len(dialog.property_chart.points), original_points)
        dialog.cut_value.setValue(77.0)
        dialog._insert_cut()
        self.assertIn(77.0, starter["cuts"])
        self.assertIn(77.0, dialog.property_chart.cut_lines)
        dialog._create_nef_node()
        nuisance = dialog._selected_node()
        self.assertTrue(nuisance["nuisance"])
        node_count = len(dialog.nodes)
        dialog._toggle_lock()
        dialog._delete_node()
        self.assertEqual(len(dialog.nodes), node_count)
        dialog._toggle_lock()
        dialog._delete_node()
        self.assertEqual(len(dialog.nodes), node_count - 1)
        dialog._add_nn_node()
        dialog._toggle_nuisance()
        dialog._toggle_lock()
        dialog._finish()
        classifier = dialog.result_state["hierarchical_classifier"]
        self.assertGreaterEqual(len(classifier["nodes"]), 3)
        self.assertEqual(dialog.result_state["nuisance_node_count"], 1)
        self.assertTrue(dialog.result_state["classifiers"][0]["st_nef"])

    def test_sensitivity_tuner_switches_to_hierarchical_st_nef(self):
        result_state = {
            "classifiers": [{"name": "ST Tree", "type": "ST-NEF", "st_nef": True}],
            "hierarchical_classifier": {"nodes": []},
            "nuisance_node_count": 2,
        }
        fake_dialog = type("FakeSTNEFDialog", (), {"result_state": result_state})()
        dialog = SensitivityTunerDialog(self.result, self.recipe)
        with patch(
            "puma_ui.modules.results_review.dialogs.STNEFTunerDialog",
            return_value=fake_dialog,
        ), patch("puma_ui.modules.results_review.dialogs._exec", return_value=QDialog.Accepted):
            dialog._switch_nef()
        self.assertEqual(dialog.nef_states["Test 1"]["nuisance_node_count"], 2)
        self.assertIn("Test 1", dialog.nef_enabled_tests)

    def test_sensitivity_tuner_applies_test_scope_display_and_auto_sort(self):
        defects = self.result["defects"][:3]
        for defect, class_code in zip(defects, (9, 1, 5)):
            defect["class_code"] = class_code
        identifiers = [defect["id"] for defect in defects]
        state = {
            "algorithm": "HLAT",
            "parameter": "Threshold",
            "value": 45.0,
            "finish_action": "Save Session Recipe",
            "filter_scope": "Filter to Current Test",
            "show_mode": "Show Detected Defects",
            "auto_sort": True,
            "test": "Test 1",
            "evaluation": {"detected_ids": identifiers[:1], "considered": 1, "detected": 1},
            "test_evaluation": {
                "detected_ids": identifiers,
                "undetected_ids": [],
                "considered_ids": identifiers,
                "considered": 3,
                "detected": 3,
            },
        }
        fake_dialog = type("FakeSensitivityDialog", (), {"result_state": state})()
        workspace = ReviewWorkspace(self.result, store=self.store, current_recipe=self.recipe)
        with patch(
            "puma_ui.modules.results_review.dialogs.SensitivityTunerDialog",
            return_value=fake_dialog,
        ), patch("puma_ui.modules.results_review.dialogs._exec", return_value=QDialog.Accepted):
            workspace._sensitivity_tuner()
        self.assertEqual(
            [defect["id"] for defect in workspace.visible_defects],
            [identifiers[1], identifiers[2], identifiers[0]],
        )

    def test_sensitivity_max_limits_do_not_drop_below_recipe_floor(self):
        dialog = SensitivityMaxLimitsDialog(
            {"Noise": 2.5, "ABSMIN": 250.0, "Gradient": 2.0},
            minimums={"Noise": 7.0, "ABSMIN": 300.0, "Gradient": 4.0},
        )
        self.assertEqual(dialog.controls["Noise"].minimum(), 7.0)
        self.assertEqual(dialog.controls["Noise"].value(), 7.0)
        dialog._reset()
        self.assertEqual(dialog.controls["ABSMIN"].value(), 300.0)

    def test_super_class_display_rules_and_saved_view_configurations(self):
        super_class = SuperClassDialog(self.result)
        super_class.codes["Killer"].setText("1, 2")
        super_class.codes["Unknown"].setText("0")
        super_class._finish()
        self.assertEqual(super_class.result_result["super_class_scheme"]["Killer"], [1, 2])

        rules = DefectDisplayRulesDialog()
        rules.table.item(1, 0).setCheckState(Qt.Checked)
        rules._finish()
        self.assertTrue(rules.result_rules[1]["enabled"])

        dialog = ReviewWorkspace(super_class.result_result, store=self.store, current_recipe=self.recipe)
        dialog.grid_configuration.setCurrentText("Engineering")
        dialog._hide_grid_column(1)
        dialog._save_grid_configuration()
        dialog.chart_configuration.setCurrentText("Class Pareto")
        dialog.chart_type.setCurrentText("Pareto")
        dialog._save_chart_configuration()
        self.assertIn("Engineering", dialog.result["review_grid_configs"])
        self.assertEqual(dialog.result["review_chart_configs"]["Class Pareto"]["type"], "Pareto")

    def test_gallery_and_histogram_exports(self):
        dialog = ReviewWorkspace(self.result, current_recipe=self.recipe)
        with tempfile.TemporaryDirectory() as directory:
            image_path = str(Path(directory) / "gallery.png")
            with patch(
                "puma_ui.modules.results_review.dialogs.QFileDialog.getSaveFileName",
                return_value=(image_path, "Images (*.png)"),
            ):
                dialog._export_gallery()
            self.assertTrue(Path(image_path).exists())

            histogram_path = str(Path(directory) / "histogram.csv")
            with patch(
                "puma_ui.modules.results_review.dialogs.QFileDialog.getSaveFileName",
                return_value=(histogram_path, "CSV Files (*.csv)"),
            ):
                dialog._export_histogram()
            self.assertIn("Signal", Path(histogram_path).read_text(encoding="utf-8"))

    def test_combine_sensitivity_results_dialog_supports_multiple_sources(self):
        self.result["sensitivity_data"] = True
        self.result["sensitivity_data_tests"] = ["Test 1"]
        source = generate_inspection_result(
            self.recipe,
            {"lot_id": "LOT-2", "wafer_id": "W02", "selected_tests": ["Test 1"]},
        )
        source["sensitivity_data"] = True
        source["sensitivity_data_tests"] = ["Test 1"]
        dialog = CombineSensitivityResultsDialog(self.result, [source])
        dialog._apply()
        self.assertEqual(len(dialog.applied), 1)
        dialog.name.setText("LOT-COMBINED")
        dialog._save()
        self.assertEqual(dialog.result_result["lot_id"], "LOT-COMBINED")
        self.assertGreater(dialog.result_result["defect_count"], self.result["defect_count"])


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from puma_ui.qt_compat import QApplication, QDialog, QMessageBox, QPushButton, QSizePolicy, Qt, QVBoxLayout
from puma_ui.modules.results_review.dialogs import (
    AdvancedSensitivityParametersDialog,
    DefectChart,
    LotResultColumnsDialog,
    DefectDisplayRulesDialog,
    GridColumnsDialog,
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
    WaferDefectMap,
    WaferDataTransferDialog,
)
from puma_ui.modules.run_control import generate_inspection_result
from puma_ui.recipe_store import RecipeStore
from puma_ui.widgets import FullscreenWindowAdapter


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
        self.assertGreaterEqual(dialog.workspace.width(), 1280)
        self.assertGreaterEqual(dialog.workspace.height(), 700)
        dialog.close()

    def test_review_grid_uses_source_columns_and_go_to_only_visible_columns(self):
        self.result["source_format"] = "KLARF"
        self.result["source_defect_columns"] = [
            {"key": "klarf:XREL", "label": "XREL", "source": "KLARF"},
            {"key": "klarf:CUSTOMZERO", "label": "CUSTOMZERO", "source": "KLARF"},
        ]
        for defect in self.result["defects"]:
            defect["klarf:XREL"] = defect.get("x", 0)
            defect["klarf:CUSTOMZERO"] = 0
        dialog = ReviewWorkspace(self.result, store=self.store, current_recipe=self.recipe)
        self.assertEqual(
            dialog.grid_columns,
            ["id", "marked", "sample", "manual_class", "klarf:XREL", "klarf:CUSTOMZERO"],
        )
        self.assertEqual(dialog.grid_go_to.count(), len(dialog.grid_columns))
        self.assertEqual(
            [dialog.grid_go_to.itemData(index) for index in range(dialog.grid_go_to.count())],
            dialog.grid_columns,
        )
        self.assertEqual(
            dialog.grid.item(0, dialog.grid_columns.index("klarf:CUSTOMZERO")).text(),
            "0",
        )
        configure = GridColumnsDialog(
            dialog.grid_columns,
            columns=dialog.available_grid_columns,
        )
        self.assertTrue(configure.checks["klarf:CUSTOMZERO"].isChecked())
        self.assertFalse(configure.checks["signal"].isChecked())
        dialog.close()

    def test_review_toolbar_is_compact_and_wafer_map_fits_its_canvas(self):
        dialog = ReviewWorkspace(self.result, store=self.store, current_recipe=self.recipe)
        dialog.resize(1600, 900)
        dialog.show()
        QApplication.processEvents()
        self.assertLessEqual(dialog.review_toolbar_layout.geometry().height(), 110)
        x0, y0, side = dialog.wafer_map._geometry()
        self.assertGreaterEqual(x0, 0)
        self.assertGreaterEqual(y0, 0)
        self.assertLessEqual(x0 + side, dialog.wafer_map.width())
        self.assertLessEqual(y0 + side, dialog.wafer_map.height())
        dialog.close()

    def test_wafer_map_can_fit_a_short_review_pane_without_clipping(self):
        wafer_map = WaferDefectMap()
        wafer_map.resize(500, 140)
        x0, y0, side = wafer_map._geometry()
        self.assertEqual(wafer_map.minimumHeight(), 140)
        self.assertGreaterEqual(y0, 0)
        self.assertLessEqual(y0 + side, wafer_map.height())

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
        self.assertEqual(len(dialog.grid_columns), len(dialog.available_grid_columns))

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
        for index, defect in enumerate(self.result["defects"]):
            defect["area"] = float(index)
        state = {
            "nef_states": {"Test 1": {
                "classifiers": [{"name": "ST Filter", "type": "ST-NEF", "st_nef": True}],
                "keep_nuisance_defects": False,
                "hierarchical_classifier": {"nodes": [
                    {
                        "id": 1, "parent_id": None, "attributes": ["Area"],
                        "cuts": [10.0], "nuisance": False,
                    },
                    {"id": 2, "parent_id": 1, "attributes": [], "cuts": [], "nuisance": False},
                    {"id": 3, "parent_id": 1, "attributes": [], "cuts": [], "nuisance": True},
                ]},
            }},
            "nef_enabled_tests": ["Test 1"],
        }
        dialog = SensitivityTunerDialog(self.result, self.recipe, state)
        self.assertTrue(dialog.enable_nef.isChecked())
        self.assertTrue(dialog.nef_filtered_ids)
        kept_areas = [defect["area"] for defect in dialog._effective_review_result()["defects"]]
        self.assertTrue(all(area < 10.0 for area in kept_areas))
        for index, defect in enumerate(dialog.review_result["defects"]):
            defect["id"] = f"renumbered-{1000 - index}"
        renumbered_areas = [defect["area"] for defect in dialog._effective_review_result()["defects"]]
        self.assertEqual(kept_areas, renumbered_areas)
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
        child = next(node for node in dialog.nodes if node.get("parent_id") == starter["id"])
        branch_areas = [defect.get("area") for defect in dialog._display_defects(child)]
        for index, defect in enumerate(dialog.review_result["defects"]):
            defect["id"] = f"changed-{5000 - index}"
        self.assertEqual(
            branch_areas,
            [defect.get("area") for defect in dialog._display_defects(child)],
        )
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

    def test_st_nef_root_population_and_attribute_child_partition(self):
        dialog = STNEFTunerDialog(self.result)
        root = dialog._selected_node()
        total = len(self.result["defects"])
        self.assertIsNone(root.get("parent_id"))
        self.assertEqual(dialog._canvas_tree_root()["id"], root["id"])
        self.assertEqual(len(dialog._display_defects(root)), total)

        hidden_dialog = STNEFTunerDialog(
            self.result, hidden_defect_ids=[self.result["defects"][0]["id"]]
        )
        hidden_root = hidden_dialog._selected_node()
        self.assertEqual(len(hidden_dialog._display_defects(hidden_root)), total)

        dialog._apply_attribute("Area")
        attribute_node = dialog._selected_node()
        self.assertEqual(attribute_node.get("parent_id"), root["id"])
        self.assertEqual(attribute_node["attributes"], ["Area"])
        self.assertEqual(len(dialog._display_defects(attribute_node)), total)
        self.assertEqual(len(dialog.property_chart.raw_values), total)

        # The first attribute selection only opens one level and one group; the
        # population is not split until a cut line is placed.
        self.assertEqual(attribute_node["cuts"], [])
        self.assertEqual(
            [item for item in dialog.nodes if item.get("parent_id") == attribute_node["id"]],
            [],
        )
        self.assertEqual(list(dialog._legend_names), ["A"])

        areas = sorted(
            value for value in (
                dialog._attribute_number(defect, "Area")
                for defect in self.result["defects"]
            )
            if value is not None
        )
        dialog.cut_value.setValue(areas[len(areas) // 2])
        dialog._insert_cut()
        buckets = [item for item in dialog.nodes if item.get("parent_id") == attribute_node["id"]]
        self.assertEqual(len(buckets), 2)
        self.assertEqual(len(attribute_node["cuts"]), 1)
        counts = [len(dialog._display_defects(item)) for item in buckets]
        self.assertEqual(sum(counts), total)
        self.assertTrue(all(count > 0 for count in counts))
        self.assertEqual(list(dialog._legend_names), ["A", "B"])

        bucket = max(buckets, key=lambda item: len(dialog._display_defects(item)))
        bucket_count = len(dialog._display_defects(bucket))
        self.assertGreater(bucket_count, 0)
        dialog._rebuild_tree(bucket["id"])
        dialog._apply_attribute("Die Column")
        child_attribute = dialog._selected_node()
        self.assertEqual(child_attribute.get("parent_id"), bucket["id"])
        self.assertEqual(len(dialog._display_defects(child_attribute)), bucket_count)
        self.assertEqual(len(dialog.property_chart.raw_values), bucket_count)
        grand_children = [
            item for item in dialog.nodes if item.get("parent_id") == child_attribute["id"]
        ]
        self.assertEqual(grand_children, [])
        self.assertEqual(len(dialog._display_defects(child_attribute)), bucket_count)

    def test_st_nef_attribute_selection_starts_with_one_group_then_splits_on_cuts(self):
        dialog = STNEFTunerDialog(self.result)
        total = len(self.result["defects"])
        dialog._apply_attribute("Area")
        node = dialog._selected_node()
        layout = dialog._partition_layout(node)
        self.assertEqual(layout["cuts"], [])
        self.assertEqual(layout["labels"], ["A"])
        self.assertFalse(layout["fallback"])
        labels = {
            dialog._partition_label(defect, node) for defect in dialog._display_defects(node)
        }
        self.assertEqual(labels, {"A"})
        entries = dialog._legend_entries(node, dialog._display_defects(node))
        self.assertEqual([entry["label"] for entry in entries], ["A"])

        # Two cut lines produce three groups, each owning one tree bucket.
        areas = sorted(
            value for value in (
                dialog._attribute_number(defect, "Area")
                for defect in self.result["defects"]
            )
            if value is not None
        )
        for fraction in (1 / 3, 2 / 3):
            dialog.cut_value.setValue(areas[int(len(areas) * fraction)])
            dialog._insert_cut()
        self.assertEqual(dialog._partition_layout(node)["labels"], ["A", "B", "C"])
        buckets = [item for item in dialog.nodes if item.get("parent_id") == node["id"]]
        self.assertEqual(len(buckets), 3)
        self.assertEqual(
            sum(len(dialog._display_defects(item)) for item in buckets), total
        )

        # Removing a cut merges those regions back into fewer groups.
        dialog._rebuild_tree(node["id"])
        dialog.property_chart.selected_cut = 0
        dialog._delete_cut()
        self.assertEqual(list(dialog._legend_names), ["A", "B"])
        buckets = [item for item in dialog.nodes if item.get("parent_id") == node["id"]]
        self.assertEqual(len(buckets), 2)

    def test_st_nef_discrete_attribute_starts_with_a_single_group(self):
        dialog = STNEFTunerDialog(self.result)
        dialog._apply_attribute("Venn ID")
        node = dialog._selected_node()
        self.assertEqual(node["cuts"], [])
        self.assertEqual(
            [item for item in dialog.nodes if item.get("parent_id") == node["id"]],
            [],
        )
        self.assertEqual(list(dialog._legend_names), ["A"])
        self.assertEqual(len(dialog._display_defects(node)), len(self.result["defects"]))

    def test_st_nef_cut_lines_split_nested_attribute_levels(self):
        dialog = STNEFTunerDialog(self.result)
        total = len(self.result["defects"])
        dialog._apply_attribute("Area")
        area_node = dialog._selected_node()
        dialog._apply_attribute("Die Column")
        column_node = dialog._selected_node()

        values = sorted(
            value for value in (
                dialog._attribute_number(defect, "Area")
                for defect in dialog._display_defects(area_node)
            )
            if value is not None
        )
        dialog._rebuild_tree(area_node["id"])
        dialog.cut_value.setValue(values[len(values) // 2])
        dialog._insert_cut()

        # Every region below the parent gets its own copy of the nested level,
        # so the child populations still add up to the parent population.
        levels = [
            item for item in dialog.nodes
            if item.get("parent_id") == area_node["id"]
        ]
        self.assertEqual(len(levels), 2)
        self.assertTrue(all(item["attributes"] == ["Die Column"] for item in levels))
        self.assertEqual(levels[0]["attributes"], column_node["attributes"])
        self.assertEqual(
            sum(len(dialog._display_defects(item)) for item in levels), total
        )
        self.assertEqual(list(dialog._legend_names), ["A", "B"])

        dialog.property_chart.selected_cut = 0
        dialog._delete_cut()
        levels = [
            item for item in dialog.nodes
            if item.get("parent_id") == area_node["id"]
        ]
        self.assertEqual(len(levels), 1)
        self.assertEqual(sum(len(dialog._display_defects(item)) for item in levels), total)

    def test_st_nef_attribute_selection_opens_one_level_below_selected_node(self):
        dialog = STNEFTunerDialog(self.result)
        total = len(self.result["defects"])
        dialog._apply_attribute("Area")
        area_node = dialog._selected_node()
        dialog._apply_attribute("Die Column")
        column_node = dialog._selected_node()

        # The second selection adds a level under the attribute node it was
        # issued from; the parent keeps its own attribute untouched.
        self.assertEqual(area_node["attributes"], ["Area"])
        self.assertEqual(area_node["type"], "1-D Attribute")
        self.assertEqual(column_node.get("parent_id"), area_node["id"])
        self.assertEqual(column_node["attributes"], ["Die Column"])
        self.assertEqual(column_node["type"], "1-D Attribute")
        self.assertEqual(len(dialog._display_defects(column_node)), total)
        self.assertEqual(
            [item["id"] for item in dialog.nodes if item.get("parent_id") == area_node["id"]],
            [column_node["id"]],
        )

        # Re-applying on the root still writes only the level below it: the root
        # itself stays attribute-free and keeps one child per region.
        root = next(item for item in dialog.nodes if item.get("parent_id") is None)
        self.assertEqual(root["attributes"], [])
        dialog._rebuild_tree(root["id"])
        dialog._apply_attribute("Signal")
        signal_node = dialog._selected_node()
        self.assertEqual(signal_node.get("parent_id"), root["id"])
        self.assertEqual(signal_node["attributes"], ["Signal"])
        self.assertEqual(root["attributes"], [])
        self.assertEqual(
            [item["id"] for item in dialog.nodes if item.get("parent_id") == root["id"]],
            [signal_node["id"]],
        )
        self.assertEqual(len(dialog._display_defects(signal_node)), total)

    def test_st_nef_shift_combines_second_attribute_on_the_generated_node(self):
        dialog = STNEFTunerDialog(self.result)
        dialog._apply_attribute("Area")
        node = dialog._selected_node()
        dialog._apply_attribute("Die Column", additive=True)
        self.assertIs(dialog._selected_node(), node)
        self.assertEqual(node["attributes"], ["Area", "Die Column"])
        self.assertEqual(node["type"], "2-D Attribute")
        self.assertEqual(
            [item for item in dialog.nodes if item.get("parent_id") == node["id"]],
            [],
        )
        self.assertEqual(len(dialog._display_defects(node)), len(self.result["defects"]))
        self.assertEqual(len(dialog.nodes), 2)
        self.assertEqual(dialog.property_chart.chart_type, "Scatter")

    def test_st_nef_shift_on_the_root_combines_on_the_level_below(self):
        dialog = STNEFTunerDialog(self.result)
        root = dialog._selected_node()
        dialog._apply_attribute("Area", additive=True)
        level = dialog._selected_node()
        self.assertEqual(level.get("parent_id"), root["id"])
        self.assertEqual(level["attributes"], ["Area"])
        self.assertEqual(len(dialog.nodes), 2)

        dialog._rebuild_tree(root["id"])
        dialog._apply_attribute("Die Column", additive=True)
        self.assertEqual(dialog._selected_node(), dialog._node(level["id"]))
        self.assertEqual(level["attributes"], ["Area", "Die Column"])
        self.assertEqual(root["attributes"], [])
        self.assertEqual(len(dialog.nodes), 2)

    def test_st_nef_legend_modes_partitions_and_grouping(self):
        dialog = STNEFTunerDialog(self.result)
        dialog._apply_attribute("Area")
        node = dialog._selected_node()
        self.assertEqual(dialog.legend.currentText(), "Partitions")
        # No cut exists yet, so the single attribute selection is one group.
        self.assertEqual([name for name in dialog._legend_names], ["A"])
        self.assertEqual(node["cuts"], [])
        self.assertEqual(dialog.property_chart.chart_type, "Needle")

        partitions = {
            entry["label"]: entry["color"] for entry in dialog._legend_entries(node, dialog._display_defects(node))
        }
        self.assertEqual(set(partitions), {"A"})

        # Groups are derived from the cut lines the user places.
        areas = sorted(
            value for value in (
                dialog._attribute_number(defect, "Area")
                for defect in self.result["defects"]
            )
            if value is not None
        )
        dialog.cut_value.setValue(areas[len(areas) // 2])
        dialog._insert_cut()
        self.assertEqual(list(dialog._legend_names), ["A", "B"])
        partitions = {
            entry["label"]: entry["color"] for entry in dialog._legend_entries(node, dialog._display_defects(node))
        }
        self.assertEqual(set(partitions), {"A", "B"})
        self.assertNotEqual(partitions["A"], partitions["B"])

        dialog.property_chart.selected_regions = {0, 1}
        dialog._group_cuts()
        self.assertEqual(list(dialog._legend_names), ["A"])
        dialog.property_chart.selected_regions = {0}
        dialog._ungroup_cuts()
        self.assertEqual(list(dialog._legend_names), ["A", "B"])

        dialog.legend.setCurrentText("RoughClass")
        labels = list(dialog._legend_names)
        self.assertTrue(labels)
        self.assertTrue(all(label.startswith("Class ") for label in labels))
        population = dialog._display_defects(node)
        rough = {
            f"Class {int(defect.get('roughbin', defect.get('class_code', 0)))}"
            for defect in population
        }
        self.assertEqual(set(labels), rough)

        dialog.legend.setCurrentText("Manual Classes")
        manual = {
            f"Class {int(defect.get('manual_class', defect.get('class_code', 0)))}"
            for defect in population
        }
        self.assertEqual(set(dialog._legend_names), manual)

        dialog.legend.setCurrentText("Partitions")
        dialog._toggle_legend_row("A", False)
        self.assertIn("A", dialog.legend_hidden)
        self.assertEqual(len(dialog.property_chart.raw_colors or []), len(dialog.property_chart.raw_values))
        colors = set(dialog.property_chart.raw_colors or [])
        self.assertEqual(len(colors), 1)

    def test_st_nef_canvas_marks_the_selected_node(self):
        dialog = STNEFTunerDialog(self.result)
        dialog._apply_attribute("Area")
        node = dialog._selected_node()
        canvas = dialog.classifier_canvas
        canvas.resize(360, 220)

        selected = [item for item in dialog.nodes if canvas._is_selected(item)]
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["id"], node["id"])

        image = canvas.grab().toImage()
        colors = set()
        for y in range(image.height()):
            for x in range(image.width()):
                colors.add(image.pixelColor(x, y).name())
        # The halo fill and its ring mark the selected node on the canvas.
        self.assertIn("#dbe8ff", colors)
        self.assertIn("#2f6fd6", colors)

        dialog._rebuild_tree(dialog.nodes[0]["id"])
        selected = [item for item in dialog.nodes if canvas._is_selected(item)]
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0].get("parent_id"), None)

    def test_st_nef_single_group_uses_one_region_label(self):
        dialog = STNEFTunerDialog(self.result)
        dialog._apply_attribute("Area")
        node = dialog._selected_node()
        # Without a cut the attribute node is the only region, labelled A.
        self.assertEqual(dialog._chart_region_names(node), {"0": "A"})

    def test_st_nef_saved_tree_drops_the_legacy_empty_group_row(self):
        nodes = [
            {"id": 1, "parent_id": None, "name": "Wafer", "type": "Root",
             "attributes": [], "cuts": [], "groups": {}},
            {"id": 2, "parent_id": 1, "name": "Area", "type": "1-D Attribute",
             "attributes": ["Area"], "cuts": [], "groups": {}},
            {"id": 3, "parent_id": 2, "name": "", "type": "Bucket",
             "attributes": [], "cuts": [], "groups": {}},
        ]
        dialog = STNEFTunerDialog(
            self.result, state={"hierarchical_classifier": {"nodes": nodes}}
        )
        self.assertEqual([node["id"] for node in dialog.nodes], [1, 2])
        self.assertEqual(len(dialog._display_defects(dialog.nodes[1])), len(self.result["defects"]))

        # A saved tree that already has region rows keeps them.
        nodes = [
            {"id": 1, "parent_id": None, "name": "Wafer", "type": "Root",
             "attributes": [], "cuts": [], "groups": {}},
            {"id": 2, "parent_id": 1, "name": "Area", "type": "1-D Attribute",
             "attributes": ["Area"], "cuts": [1.0], "groups": {}},
            {"id": 3, "parent_id": 2, "name": "", "type": "Bucket",
             "attributes": [], "cuts": [], "groups": {}},
            {"id": 4, "parent_id": 2, "name": "", "type": "Bucket",
             "attributes": [], "cuts": [], "groups": {}},
        ]
        dialog = STNEFTunerDialog(
            self.result, state={"hierarchical_classifier": {"nodes": nodes}}
        )
        self.assertEqual([node["id"] for node in dialog.nodes], [1, 2, 3, 4])

    def test_sensitivity_tuner_switches_to_hierarchical_st_nef(self):
        dialog = SensitivityTunerDialog(self.result, self.recipe)
        dialog._switch_nef()
        self.assertTrue(dialog.stnef_button.isChecked())
        self.assertFalse(dialog.st_button.isChecked())
        self.assertFalse(dialog.stnef_page.isWindow())
        self.assertFalse(dialog.stnef_page.isHidden())
        self.assertTrue(dialog.st_page.isHidden())
        dialog.stnef_page._add_nn_node()
        dialog.stnef_page._toggle_nuisance()
        dialog._show_st_page()
        self.assertGreaterEqual(dialog.nef_states["Test 1"]["nuisance_node_count"], 1)
        self.assertIn("Test 1", dialog.nef_enabled_tests)
        self.assertFalse(dialog.st_page.isHidden())
        self.assertTrue(dialog.stnef_page.isHidden())

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

    def test_st_nef_legend_modes_without_data_default_to_class_zero(self):
        dialog = STNEFTunerDialog({**self.result, "defects": []})
        node = dialog._selected_node()
        for mode in STNEFTunerDialog.LEGEND_MODES:
            dialog.legend.setCurrentText(mode)
            entries = dialog._legend_entries(node, dialog._display_defects(node))
            self.assertEqual([entry["label"] for entry in entries], ["Class 0"], mode)
            self.assertEqual(entries[0]["color"], dialog._class_color("Class 0"))
            self.assertEqual(list(dialog._legend_names), ["Class 0"], mode)

        bare = {**self.result, "defects": [
            {"id": 1, "x": 1, "y": 2, "area": 0.5, "signal": 3.0, "noise": 0.1},
        ]}
        dialog = STNEFTunerDialog(bare)
        node = dialog._selected_node()
        for mode in STNEFTunerDialog.LEGEND_MODES:
            dialog.legend.setCurrentText(mode)
            entries = dialog._legend_entries(node, dialog._display_defects(node))
            self.assertEqual([entry["label"] for entry in entries], ["Class 0"], mode)
        self.assertEqual(dialog._partition_label(bare["defects"][0], node), "Class 0")

    def test_sensitivity_tuner_close_discards_unsaved_edits(self):
        self.result["sensitivity_data"] = True
        self.result["sensitivity_data_tests"] = ["Test 1"]
        saved = {"value": 82.0, "nef_states": {}}
        dialog = SensitivityTunerDialog(self.result, self.recipe, saved)
        dialog.value.setValue(150.0)
        dialog._modified()
        dialog.reject()
        self.assertIsNone(dialog.result_state)
        self.assertFalse(dialog.state_persisted)

        unsaved = type("UnsavedTuner", (), {"result_state": None, "state_persisted": False})()
        workspace = ReviewWorkspace(self.result, store=self.store, current_recipe=self.recipe)
        workspace.result["sensitivity_tuner"] = {"value": 82.0}
        with patch(
            "puma_ui.modules.results_review.dialogs.SensitivityTunerDialog",
            return_value=unsaved,
        ), patch("puma_ui.modules.results_review.dialogs._exec", return_value=QDialog.Accepted):
            workspace._sensitivity_tuner()
        self.assertEqual(workspace.result["sensitivity_tuner"], {"value": 82.0})
        self.assertIn("without saving", workspace.status.text().lower())

    def test_sensitivity_tuner_saved_finish_persists_for_the_next_open(self):
        self.result["sensitivity_data"] = True
        self.result["sensitivity_data_tests"] = ["Test 1"]
        dialog = SensitivityTunerDialog(self.result, self.recipe)
        dialog.value.setValue(150.0)
        dialog._finish()
        self.assertTrue(dialog.state_persisted)
        self.assertIsNotNone(dialog.result_state)
        reopened = SensitivityTunerDialog(self.result, self.recipe, dialog.result_state)
        self.assertEqual(reopened.value.value(), 150.0)

    def test_fullscreen_adapter_scales_metrics_and_restores_them(self):
        host = QDialog()
        layout = QVBoxLayout(host)
        button = QPushButton("Finish")
        button.setStyleSheet("QPushButton { font-size: 11px; }")
        button.setFixedHeight(22)
        layout.addWidget(button)
        host.show()
        adapter = FullscreenWindowAdapter(host, base=(320, 240))
        host.showMaximized()
        QApplication.processEvents()
        QApplication.processEvents()
        self.assertTrue(host.isFullScreen())
        adapter.apply_scale(force=True)
        self.assertGreater(adapter.scale, 1.0)
        self.assertGreater(button.height(), 22)
        self.assertIn(f"font-size: {11 * adapter.scale:g}", button.styleSheet())
        host.showNormal()
        QApplication.processEvents()
        adapter.apply_scale()
        self.assertFalse(host.isFullScreen())
        self.assertAlmostEqual(adapter.scale, 1.0)
        self.assertEqual(button.height(), 22)
        self.assertIn("font-size: 11px", button.styleSheet())
        host.close()

    def test_review_toolbar_draws_vector_icons_instead_of_screenshots(self):
        from puma_ui.modules.results_review.icons import pixmap as vector_pixmap

        for name in (
            "review_clear", "review_select", "review_mark", "review_analysis",
            "review_super", "review_filter_in", "review_filter_out",
            "review_filter_reset", "review_filter_setup", "review_images",
            "review_send_images", "review_send_wafer", "review_send_lot",
            "review_camera", "optics_engaged", "optics_apply", "grid_save",
            "map_select", "map_help",
        ):
            self.assertFalse(vector_pixmap(name, 24).isNull(), name)
        dialog = ReviewWorkspace(self.result, store=self.store, current_recipe=self.recipe)
        self.assertFalse(dialog._review_icon("clear").isNull())
        self.assertFalse(dialog._optics_icon("engaged").isNull())
        self.assertGreaterEqual(dialog._review_icon("clear").availableSizes()[0].width(), 28)
        dialog.close()

    def test_review_fullscreen_shows_minimize_restore_and_close_buttons(self):
        dialog = ReviewWorkspace(self.result, store=self.store, current_recipe=self.recipe)
        dialog.show()
        QApplication.processEvents()
        self.assertFalse(dialog.window_buttons.isVisible())
        dialog.showMaximized()
        QApplication.processEvents()
        QApplication.processEvents()
        self.assertTrue(dialog.isFullScreen())
        self.assertTrue(dialog.window_buttons.isVisible())
        self.assertTrue(dialog.window_buttons.minimize_button.isVisible())
        self.assertTrue(dialog.window_buttons.close_button.isVisible())
        dialog.window_buttons.restore_window()
        QApplication.processEvents()
        QApplication.processEvents()
        self.assertFalse(dialog.isFullScreen())
        self.assertFalse(dialog.window_buttons.isVisible())
        dialog.close()

    def test_sensitivity_tuner_charts_keep_their_stretch_when_paged(self):
        dialog = SensitivityTunerDialog(self.result, self.recipe)
        layout = dialog.st_page.layout()
        chart_stretches = []
        for index in range(layout.count()):
            widget = layout.itemAt(index).widget()
            if isinstance(widget, DefectChart):
                chart_stretches.append(layout.stretch(index))
                self.assertEqual(
                    widget.sizePolicy().verticalPolicy(), QSizePolicy.Expanding
                )
        self.assertTrue(chart_stretches)
        self.assertTrue(all(stretch == 1 for stretch in chart_stretches))
        dialog.close()

    def test_review_caption_buttons_pin_to_the_top_right_corner(self):
        dialog = ReviewWorkspace(self.result, store=self.store, current_recipe=self.recipe)
        dialog.showMaximized()
        QApplication.processEvents()
        QApplication.processEvents()
        self.assertTrue(dialog.isFullScreen())
        rect = dialog.window_buttons.geometry()
        self.assertEqual(rect.y(), 0)
        self.assertLessEqual(rect.width(), 600)
        self.assertGreaterEqual(rect.right(), dialog.width() - 4)
        dialog.close()

    def test_sensitivity_tuner_refits_its_host_size_every_time_it_opens(self):
        from puma_ui.qt_compat import QWidget

        host = QWidget()
        host.resize(1280, 900)
        host.show()
        dialog = SensitivityTunerDialog(self.result, self.recipe, parent=host)
        dialog.show()
        QApplication.processEvents()
        self.assertEqual((dialog.width(), dialog.height()), (1280, 900))
        host.resize(1720, 1040)
        dialog.hide()
        dialog.resize(900, 640)
        dialog.show()
        QApplication.processEvents()
        self.assertEqual((dialog.width(), dialog.height()), (1720, 1040))
        dialog.close()
        host.close()

    def test_sensitivity_tuner_finish_menu_matches_table_10_43(self):
        dialog = SensitivityTunerDialog(self.result, self.recipe)
        menu = dialog.finish_menu()
        labels = [action.text() for action in menu.actions() if not action.isSeparator()]
        self.assertEqual(
            labels,
            [
                "Restore Session Recipe",
                "Restore Inspection Recipe",
                "Save Session Recipe",
                "Save Recipe As...",
                "Export Recipe As...",
                "Save & Exit",
                "Exit",
            ],
        )
        separators = sum(1 for action in menu.actions() if action.isSeparator())
        self.assertEqual(separators, 2)
        for title in ("Restore Session Recipe", "Restore Inspection Recipe"):
            submenu = next(a for a in menu.actions() if a.text() == title).menu()
            self.assertIsNotNone(submenu)
            self.assertEqual(
                [action.text() for action in submenu.actions()],
                ["Parameters Only", "All"],
            )
        dialog.close()

    def test_sensitivity_tuner_finish_menu_restore_choices_keep_their_scope(self):
        dialog = SensitivityTunerDialog(self.result, self.recipe)
        menu = dialog.finish_menu()
        session = next(a for a in menu.actions() if a.text() == "Restore Session Recipe").menu()
        next(a for a in session.actions() if a.text() == "Parameters Only").trigger()
        self.assertEqual(dialog.finish_action.currentText(), "Restore Session - Parameters Only")
        self.assertEqual(dialog.result_state["restored_from"], "Session Recipe")

        dialog = SensitivityTunerDialog(self.result, self.recipe)
        menu = dialog.finish_menu()
        inspection = next(
            a for a in menu.actions() if a.text() == "Restore Inspection Recipe"
        ).menu()
        next(a for a in inspection.actions() if a.text() == "All").trigger()
        self.assertEqual(dialog.finish_action.currentText(), "Restore Inspection - All")
        self.assertEqual(dialog.result_state["restored_from"], "Inspection Recipe")
        self.assertEqual(dialog.result_state["nef_states"], {})

    def test_sensitivity_tuner_exit_menu_option_prompts_before_leaving(self):
        dialog = SensitivityTunerDialog(self.result, self.recipe)
        exit_action = next(a for a in dialog.finish_menu().actions() if a.text() == "Exit")
        with patch(
            "puma_ui.modules.results_review.dialogs.QMessageBox.question",
            return_value=QMessageBox.Discard,
        ):
            exit_action.trigger()
        self.assertIsNone(dialog.result_state)
        self.assertFalse(dialog.state_persisted)

        dialog = SensitivityTunerDialog(self.result, self.recipe)
        exit_action = next(a for a in dialog.finish_menu().actions() if a.text() == "Exit")
        with patch(
            "puma_ui.modules.results_review.dialogs.QMessageBox.question",
            return_value=QMessageBox.Cancel,
        ):
            exit_action.trigger()
        self.assertEqual(dialog.result(), 0)

    def test_sensitivity_tuner_options_menu_matches_table_10_44(self):
        dialog = SensitivityTunerDialog(self.result, self.recipe)
        menu = dialog.options_menu()
        labels = [action.text() for action in menu.actions() if not action.isSeparator()]
        self.assertEqual(
            labels,
            [
                "Show Detected Defects",
                "Show Undetected Defects",
                "Filter to Current Parameter",
                "Filter to Current Test",
                "Auto Sort on Group (Manual Code)",
                "Dark Defect Filter Option",
                "Region Selection Option ...",
                "Max Limit Configuration ...",
                "Advanced Sensitivity Parameters...",
            ],
        )
        dark = next(a for a in menu.actions() if a.text() == "Dark Defect Filter Option").menu()
        self.assertEqual(
            [action.text() for action in dark.actions()],
            ["Both", "Primary Dark Defects Only", "Secondary-Die Defects Only"],
        )
        dialog.close()

    def test_sensitivity_tuner_options_menu_keeps_its_exclusive_toggles(self):
        dialog = SensitivityTunerDialog(self.result, self.recipe)
        actions = {a.text(): a for a in dialog.options_menu().actions()}
        actions["Show Detected Defects"].trigger()
        self.assertEqual(dialog.show_mode.currentText(), "Show Detected Defects")
        self.assertTrue(actions["Show Detected Defects"].isChecked())
        self.assertFalse(actions["Show Undetected Defects"].isChecked())
        actions["Show Undetected Defects"].trigger()
        self.assertEqual(dialog.show_mode.currentText(), "Show Undetected Defects")
        fresh = {a.text(): a for a in dialog.options_menu().actions()}
        self.assertFalse(fresh["Show Detected Defects"].isChecked())
        self.assertTrue(fresh["Show Undetected Defects"].isChecked())
        fresh["Show Undetected Defects"].trigger()
        self.assertEqual(dialog.show_mode.currentText(), "Show All Defects")

        fresh["Filter to Current Parameter"].trigger()
        self.assertEqual(dialog.filter_scope.currentText(), "Filter to Current Parameter")
        fresh["Filter to Current Test"].trigger()
        self.assertEqual(dialog.filter_scope.currentText(), "Filter to Current Test")
        latest = {a.text(): a for a in dialog.options_menu().actions()}
        self.assertFalse(latest["Filter to Current Parameter"].isChecked())
        self.assertTrue(latest["Filter to Current Test"].isChecked())
        latest["Filter to Current Test"].trigger()
        self.assertEqual(dialog.filter_scope.currentText(), "No Review Filter")

        latest["Auto Sort on Group (Manual Code)"].trigger()
        self.assertTrue(dialog.auto_sort.isChecked())
        dark = next(a for a in latest.values() if a.menu() is not None).menu()
        next(a for a in dark.actions() if a.text() == "Primary Dark Defects Only").trigger()
        self.assertEqual(dialog.dark_filter.currentText(), "Primary Dark Defects Only")
        dialog.close()

    def test_sensitivity_tuner_toolbar_carets_open_their_menus(self):
        dialog = SensitivityTunerDialog(self.result, self.recipe)
        with patch("puma_ui.modules.results_review.dialogs.QMenu.exec") as popup:
            dialog.finish_button.caret_handler(dialog.finish_button)
            dialog.options_button.caret_handler(dialog.options_button)
        self.assertEqual(popup.call_count, 2)
        dialog.close()

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

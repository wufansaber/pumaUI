from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from puma_ui.modules.results_review import (
    DefectFilterDialog,
    OpticsSelectorDialog,
    ResultsUtilityDialog,
    ReviewImageGrabDialog,
    ReviewOffsetDialog,
    ReviewWorkspace,
    SelectLotResultsDialog,
    SensitivityTunerDialog,
    SuperClassDialog,
    WaferDataTransferDialog,
)
from puma_ui.qt_compat import QApplication, QDialog, QMessageBox, Qt
from puma_ui.recipe_store import RecipeStore

from manual_ui_helpers import QTest, click, process_events, replace_text, select_combo, visible_button


def result(identifier="review-1", lot="LOT-1", offset=0.0):
    defects = []
    for index in range(1, 7):
        defects.append({
            "id": index,
            "x": index * 10.0 + offset,
            "y": index * 5.0 + offset,
            "die_x": (index - 1) % 3,
            "die_y": (index - 1) // 3,
            "test": "Test 1" if index < 5 else "Test 2",
            "class_code": index % 3,
            "roughbin": index % 2,
            "channel": (index - 1) % 3 + 1,
            "region_id": "R1" if index % 2 else "R2",
            "threshold_region": "TR1",
            "polarity": "Bright" if index % 2 else "Dark",
            "signal": 40.0 + index * 10,
            "size_um": 0.1 * index,
            "has_patch_image": index % 2 == 0,
            "marked": index == 1,
        })
    return {
        "id": identifier,
        "inspection": "Deep",
        "device": "Device1",
        "step": "Layer1",
        "status": "Complete",
        "lot_id": lot,
        "wafer_id": "W01",
        "selected_tests": ["Test 1", "Test 2"],
        "defects": defects,
        "defect_count": len(defects),
        "feature_vector_file": "FeatureVectors.bin",
        "sensitivity_data": True,
        "sensitivity_data_tests": ["Test 1"],
    }


class ManualChapterTenReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = RecipeStore(Path(self.temp.name) / "recipes.json", default_recipes=[])
        self.primary = self.store.save_result(result())
        self.source = self.store.save_result(result("review-2", "LOT-2", 0.0005))

    def tearDown(self):
        for widget in list(QApplication.topLevelWidgets()):
            widget.close()
        process_events()
        self.temp.cleanup()

    def show_dialog(self, dialog):
        dialog.show()
        process_events(20)
        self.assertTrue(dialog.isVisible())
        return dialog

    def test_10_1_review_layout_map_grid_gallery_chart_summary_and_marks(self):
        dialog = self.show_dialog(ReviewWorkspace(self.primary, store=self.store))
        self.assertEqual(dialog.grid.rowCount(), 6)
        select_combo(dialog.layout_mode, "Wide Grid")
        select_combo(dialog.layout_mode, "Advanced Classify")
        self.assertTrue(dialog.advanced_frame.isVisible())
        select_combo(dialog.map_zoom, "200%")
        self.assertEqual(dialog.wafer_map.zoom_factor, 2.0)
        click(dialog.show_counts)
        self.assertTrue(dialog.wafer_map.show_counts)
        select_combo(dialog.gallery_scope, "All Marked Defects")
        select_combo(dialog.gallery_mode, "Patch Image")
        select_combo(dialog.gallery_zoom, "200%")
        self.assertTrue(dialog.image_widgets[1].isVisible())
        select_combo(dialog.chart_type, "Pareto")
        select_combo(dialog.summary_mode, "Classification Summary")
        self.assertTrue(dialog.summary.text().startswith("Classification"))

        dialog.grid.selectRow(0)
        process_events()
        click(visible_button(dialog, "Select Current"))
        click(visible_button(dialog, "Mark Selected"))
        click(visible_button(dialog, "Sample Marked"))
        selected = next(item for item in dialog.result["defects"] if item["id"] == dialog.selected_id)
        self.assertTrue(selected["marked"])
        self.assertTrue(selected["sampled_review"])
        click(visible_button(dialog, "Clear Selection"))
        self.assertEqual(dialog.selected_ids, set())

    def test_10_2_super_class_export_import_duplicate_validation_and_apply(self):
        dialog = self.show_dialog(SuperClassDialog(self.primary))
        replace_text(dialog.codes["Killer"], "1, 2")
        replace_text(dialog.codes["Real"], "2")
        with patch("puma_ui.modules.results_review.dialogs.QMessageBox.warning") as warning:
            click(visible_button(dialog, "Apply"))
        warning.assert_called_once()
        replace_text(dialog.codes["Real"], "0")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "super-class.json"
            with patch(
                "puma_ui.modules.results_review.dialogs.QFileDialog.getSaveFileName",
                return_value=(str(path), "JSON Files (*.json)"),
            ):
                click(visible_button(dialog, "Export..."))
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["Killer"], [1, 2])
            replace_text(dialog.codes["Killer"], "")
            with patch(
                "puma_ui.modules.results_review.dialogs.QFileDialog.getOpenFileName",
                return_value=(str(path), "JSON Files (*.json)"),
            ):
                click(visible_button(dialog, "Import..."))
            self.assertEqual(dialog.codes["Killer"].text(), "1, 2")
        click(visible_button(dialog, "Apply"))
        self.assertEqual(dialog.result(), QDialog.Accepted)
        self.assertIn("super_class", dialog.result_result["defects"][0])

    def test_10_3_to_10_5_filter_tabs_reset_rule_builder_validation_and_apply(self):
        dialog = self.show_dialog(DefectFilterDialog(self.primary))
        self.assertEqual(dialog.tabs.count(), 6)
        tab_bar = dialog.tabs.tabBar()
        for index in range(dialog.tabs.count()):
            QTest.mouseClick(tab_bar, Qt.LeftButton, Qt.NoModifier, tab_bar.tabRect(index).center())
            process_events()
            self.assertEqual(dialog.tabs.currentIndex(), index)
        dialog.advanced_tabs.setCurrentIndex(1)
        process_events()
        replace_text(dialog.rule_value, "50")
        click(visible_button(dialog, "Build Expression"))
        self.assertIn("50", dialog.advanced_expression.text())
        dialog.minimum_size.setValue(10)
        dialog.maximum_size.setValue(1)
        with patch("puma_ui.modules.results_review.dialogs.QMessageBox.warning") as warning:
            click(visible_button(dialog, "Apply"))
        warning.assert_called_once()
        click(visible_button(dialog, "Reset"))
        self.assertEqual(dialog.minimum_size.value(), 0)
        self.assertEqual(dialog.advanced_expression.text(), "")
        dialog.advanced_tabs.setCurrentIndex(1)
        replace_text(dialog.rule_value, "50")
        click(visible_button(dialog, "Build Expression"))
        click(dialog.dark)
        click(visible_button(dialog, "Apply"))
        self.assertEqual(dialog.result_filters["polarities"], ["Bright"])
        self.assertIn("50", dialog.result_filters["advanced_expression"])

    def test_10_6_results_utility_auto_label_merge_and_save_filtered(self):
        auto = self.show_dialog(ResultsUtilityDialog(self.primary, [self.source], self.primary["defects"]))
        click(auto.preserve_classified)
        replace_text(auto.preserve_codes, "1")
        click(visible_button(auto, "Apply"))
        self.assertIsNotNone(auto.result_result)
        self.assertIn("Auto Label", auto.status_message)

        merge = self.show_dialog(ResultsUtilityDialog(self.primary, [self.source], self.primary["defects"]))
        select_combo(merge.operation, "Merge Result")
        merge.tolerance.setValue(0.0)
        click(visible_button(merge, "Apply"))
        self.assertIsNotNone(merge.result_result)
        self.assertIn("added", merge.status_message)

        filtered = self.show_dialog(ResultsUtilityDialog(self.primary, [self.source], self.primary["defects"][:2]))
        select_combo(filtered.operation, "Save Filtered Lot As")
        replace_text(filtered.new_lot, "LOT-FILTERED")
        click(visible_button(filtered, "Apply"))
        self.assertEqual(filtered.new_result["defect_count"], 2)
        self.assertEqual(filtered.new_result["lot_id"], "LOT-FILTERED")

    def test_10_7_lot_selection_search_recent_modes_delete_cancel_and_confirm(self):
        dialog = self.show_dialog(SelectLotResultsDialog(self.store))
        click(dialog.search_button)
        self.assertTrue(dialog.search_frame.isVisible())
        replace_text(dialog.search, "LOT-2")
        self.assertEqual(dialog.table.rowCount(), 1)
        select_combo(dialog.review_mode, "Inspected Wafer")
        click(visible_button(dialog, "Open"))
        self.assertEqual(dialog.selected_result["review_mode"], "Inspected Wafer")

        recent = self.show_dialog(SelectLotResultsDialog(self.store))
        select_combo(recent.source, "Recent Items")
        self.assertEqual(recent.table.rowCount(), 1)
        click(visible_button(recent, "Cancel"))

        deletion = self.show_dialog(SelectLotResultsDialog(self.store))
        deletion.table.selectRow(0)
        with patch("puma_ui.modules.results_review.dialogs.QMessageBox.question", return_value=QMessageBox.No):
            click(visible_button(deletion, "Delete"))
        self.assertEqual(deletion.table.rowCount(), 2)
        with patch("puma_ui.modules.results_review.dialogs.QMessageBox.question", return_value=QMessageBox.Yes):
            click(visible_button(deletion, "Delete"))
        self.assertEqual(deletion.table.rowCount(), 1)

    def test_10_8_to_10_10_image_settings_transfer_export_and_offsets(self):
        image = self.show_dialog(ReviewImageGrabDialog(["Test 1", "Test 2"]))
        select_combo(image.optics, "Use Inspection Test")
        select_combo(image.test, "Test 2")
        click(image.clear_marks)
        click(visible_button(image, "OK"))
        self.assertEqual(image.result_settings["test"], "Test 2")
        self.assertFalse(image.result_settings["clear_marks"])

        transfer = self.show_dialog(WaferDataTransferDialog(self.primary, self.primary["defects"][:2]))
        click(transfer.send_shown)
        self.assertFalse(transfer.include_duplicates.isEnabled())
        click(visible_button(transfer, "Send"))
        self.assertEqual(transfer.result_options["defect_count"], 2)

        offset = self.show_dialog(ReviewOffsetDialog(self.primary))
        offset.x_offset.setValue(2.5)
        offset.y_offset.setValue(-1.5)
        click(visible_button(offset, "Mark"))
        click(visible_button(offset, "Finish"))
        self.assertEqual(offset.result_result["defects"][0]["x"], self.primary["defects"][0]["x"] + 2.5)

        die = self.show_dialog(ReviewOffsetDialog(self.primary, die_origin=True))
        die.x_offset.setValue(1.0)
        click(visible_button(die, "Mark"))
        click(visible_button(die, "Finish"))
        self.assertEqual(die.result_result["die_origin_offset"]["x"], 1.0)

    def test_10_11_optics_selector_requires_sites_and_modes_then_analyzes(self):
        dialog = self.show_dialog(OpticsSelectorDialog(self.primary, {"tests": [{"name": "Test 1"}]}))
        tab_bar = dialog.tabs.tabBar()
        QTest.mouseClick(tab_bar, Qt.LeftButton, Qt.NoModifier, tab_bar.tabRect(2).center())
        process_events()
        with patch("puma_ui.modules.results_review.dialogs.QMessageBox.warning") as warning:
            click(visible_button(dialog, "Grab and Analyze"))
        warning.assert_called_once()
        QTest.mouseClick(tab_bar, Qt.LeftButton, Qt.NoModifier, tab_bar.tabRect(1).center())
        process_events()
        select_combo(dialog.pixel_size, "SL425")
        select_combo(dialog.illumination, "Normal")
        click(visible_button(dialog, "Add Optics Mode"))
        self.assertEqual(dialog.mode_table.rowCount(), 1)
        QTest.mouseClick(tab_bar, Qt.LeftButton, Qt.NoModifier, tab_bar.tabRect(2).center())
        process_events()
        click(visible_button(dialog, "Grab and Analyze"))
        self.assertEqual(dialog.score_table.rowCount(), 1)
        click(visible_button(dialog, "Add Selected Modes to Recipe"))
        click(visible_button(dialog, "Finish"))
        self.assertEqual(dialog.result_state["inserted_test_count"], 1)

    def test_10_12_to_10_14_sensitivity_tuner_catch_commit_plot_and_finish(self):
        recipe = {"inspection": "Deep", "device": "Device1", "step": "Layer1", "tests": [{"name": "Test 1"}]}
        dialog = self.show_dialog(SensitivityTunerDialog(self.primary, recipe))
        click(visible_button(dialog, "Catch Defect"))
        self.assertIn("catch", dialog.parameter_status.text().lower())
        click(visible_button(dialog, "Commit"))
        self.assertTrue(dialog.committed)
        select_combo(dialog.partition, "Class Code")
        select_combo(dialog.plot_scale, "Log Y")
        click(dialog.plot_grid)
        dialog.plot_zoom.setValue(175)
        select_combo(dialog.show_mode, "Show Detected Defects")
        select_combo(dialog.filter_scope, "Filter to Current Test")
        select_combo(dialog.finish_action, "Save Session Recipe")
        click(visible_button(dialog, "Finish"))
        self.assertTrue(dialog.result_state["committed"])
        self.assertEqual(dialog.result_state["plot_scale"], "Log Y")
        self.assertEqual(dialog.result_state["plot_zoom"], 175)


if __name__ == "__main__":
    unittest.main()

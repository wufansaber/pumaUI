from __future__ import annotations

import unittest
from unittest.mock import patch

from puma_ui.modules.results_review.dialogs import (
    ApplyBinnerDialog,
    ClassifyDefectsDialog,
    DefectAnalysisToolboxDialog,
    GridColumnsDialog,
    KlarfMatchDialog,
    RegionSelectionDialog,
    ResultsUtilityDialog,
    ReviewFilterAnalysisDialog,
    ReviewOffsetDialog,
    StarterTreeGenerationDialog,
)
from puma_ui.modules.sizing.dialogs import DefectSetCollectionDialog, KlarfOptionsDialog
from puma_ui.modules.system_status.dialog import (
    AlarmCenterDialog,
    E84RealTimeSignalDialog,
    ErrorMessageDialog,
    TransferConfigurationDialog,
)
from puma_ui.modules.wafer_post_processing.dialog import (
    AttributeSelectionDialog,
    DensityGroupsDialog,
    PrecisionAdvancedSettingsDialog,
)
from puma_ui.qt_compat import QApplication, QDialog, QLabel, QMessageBox, Qt

from manual_ui_helpers import QTest, click, click_disabled, process_events, replace_text, select_combo, visible_button


def sample_defect(identifier=1):
    return {
        "id": identifier,
        "x": float(identifier),
        "y": float(identifier + 1),
        "die_x": 0,
        "die_y": 0,
        "class_code": 0,
        "test": "Test 1",
        "signal": 100.0,
        "size_um": 0.2,
    }


def sample_result(identifier="r1", lot="LOT-1"):
    defects = [sample_defect(1), sample_defect(2)]
    return {
        "id": identifier,
        "inspection": "Deep",
        "device": "Device1",
        "step": "Layer1",
        "status": "Complete",
        "lot_id": lot,
        "wafer_id": "W01",
        "selected_tests": ["Test 1"],
        "defects": defects,
        "defect_count": len(defects),
    }


class ManualReviewSystemWppDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def show_dialog(self, dialog):
        dialog.show()
        process_events(15)
        self.assertTrue(dialog.isVisible())
        return dialog

    def test_klarf_match_select_and_cancel(self):
        recipe = {"id": "p1", "inspection": "Deep", "device": "Device1", "step": "Layer1", "status": "Valid"}
        result = sample_result()
        dialog = self.show_dialog(KlarfMatchDialog([recipe], [result]))
        self.assertEqual(dialog.table.rowCount(), 2)
        dialog.table.selectRow(1)
        click(visible_button(dialog, "Select"))
        self.assertEqual(dialog.selected_match["id"], "r1")

        cancel = self.show_dialog(KlarfMatchDialog([recipe], []))
        click(visible_button(cancel, "Cancel"))
        self.assertEqual(cancel.result(), QDialog.Rejected)

    def test_error_message_writes_message_and_data_to_daily_log(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as directory:
            dialog = self.show_dialog(
                ErrorMessageDialog("Stage timeout", "Axis=X; Code=42", directory)
            )
            click(dialog.save_button)
            self.assertIsNotNone(dialog.saved_path)
            self.assertTrue(dialog.saved_path.is_file())
            saved = Path(dialog.saved_path).read_text(encoding="utf-8")
            self.assertIn("Stage timeout", saved)
            self.assertIn("Axis=X; Code=42", saved)
            self.assertFalse(dialog.save_button.isEnabled())
            click(visible_button(dialog, "Close"))

    def test_e84_display_runs_enable_handoff_reset_and_minimize_paths(self):
        dialog = self.show_dialog(E84RealTimeSignalDialog(enabled=False))
        self.assertEqual(dialog.phase_label.text(), "E84 Disabled")
        self.assertFalse(dialog.next_button.isEnabled())

        click(dialog.enabled)
        self.assertEqual(dialog.phase_label.text(), "Idle")
        click(dialog.next_button)
        self.assertEqual(dialog.phase_label.text(), "Carrier Valid")
        self.assertEqual(dialog.signal_table.item(0, 1).text(), "ON")
        click(visible_button(dialog, "Reset"))
        self.assertEqual(dialog.phase_label.text(), "Idle")
        click(visible_button(dialog, "Minimize"))
        self.assertTrue(dialog.isMinimized())
        dialog.showNormal()
        process_events()
        click(visible_button(dialog, "Close"))

    def test_results_utility_modes_and_filtered_save(self):
        target = sample_result()
        source = sample_result("r2", "LOT-2")
        dialog = self.show_dialog(ResultsUtilityDialog(target, [source], [target["defects"][0]]))
        select_combo(dialog.operation, "Save Filtered Lot As")
        self.assertTrue(dialog.new_lot.isEnabled())
        replace_text(dialog.new_lot, "LOT-FILTERED")
        click(visible_button(dialog, "Apply"))
        self.assertIsNotNone(dialog.new_result)
        self.assertEqual(dialog.new_result["lot_id"], "LOT-FILTERED")
        self.assertEqual(dialog.new_result["defect_count"], 1)

    def test_classification_and_review_offset_save_values(self):
        classify = self.show_dialog(ClassifyDefectsDialog(2))
        classify.code.setValue(77)
        click(visible_button(classify, "Apply"))
        self.assertEqual(classify.class_code, 77)

        offset = self.show_dialog(ReviewOffsetDialog(sample_result()))
        offset.x_offset.setValue(2.5)
        offset.y_offset.setValue(-1.25)
        click(visible_button(offset, "Mark"))
        self.assertIn("marked", offset.marked.text())
        click(visible_button(offset, "Finish"))
        self.assertIsNotNone(offset.result_result)
        self.assertEqual(offset.result_result["defects"][0]["x"], 3.5)

    def test_region_selection_unlocks_manual_checks_and_rejects_empty(self):
        dialog = self.show_dialog(RegionSelectionDialog(["R1", "R2"]))
        self.assertTrue(dialog.automatic.isChecked())
        self.assertFalse(dialog.checks["R1"].isEnabled())
        click(dialog.automatic)
        self.assertTrue(dialog.checks["R1"].isEnabled())
        click(visible_button(dialog, "Select None"))
        with patch("puma_ui.modules.results_review.dialogs.QMessageBox.warning") as warning:
            click(visible_button(dialog, "OK"))
        warning.assert_called_once()
        click(visible_button(dialog, "Select All"))
        click(visible_button(dialog, "OK"))
        self.assertEqual(dialog.result_regions, ["R1", "R2"])

    def test_starter_tree_manual_attribute_gate_and_generate(self):
        dialog = self.show_dialog(StarterTreeGenerationDialog(["Signal", "Size"]))
        self.assertFalse(dialog.attributes.isEnabled())
        click(dialog.automatic)
        self.assertTrue(dialog.attributes.isEnabled())
        with patch("puma_ui.modules.results_review.dialogs.QMessageBox.warning") as warning:
            click(visible_button(dialog, "Generate"))
        warning.assert_called_once()
        item = dialog.attributes.topLevelItem(0)
        rect = dialog.attributes.visualItemRect(item)
        QTest.mouseClick(
            dialog.attributes.viewport(),
            Qt.LeftButton,
            Qt.NoModifier,
            rect.topLeft() + type(rect.center())(8, rect.height() // 2),
        )
        process_events()
        click(visible_button(dialog, "Generate"))
        self.assertEqual(dialog.result_settings["attributes"], ["Signal"])

    def test_grid_columns_fit_screen_reset_validate_and_save(self):
        dialog = self.show_dialog(GridColumnsDialog(["id"]))
        self.assertLessEqual(dialog.height(), 700)
        self.assertTrue(dialog.checks["id"].isChecked())
        click(visible_button(dialog, "Reset Columns"))
        self.assertTrue(all(check.isChecked() for check in dialog.checks.values()))
        for check in dialog.checks.values():
            click(check)
        with patch("puma_ui.modules.results_review.dialogs.QMessageBox.warning") as warning:
            click(visible_button(dialog, "OK"))
        warning.assert_called_once()
        click(dialog.checks["id"])
        click(dialog.checks["signal"])
        click(visible_button(dialog, "OK"))
        self.assertEqual(dialog.result_columns, ["id", "signal"])

    def test_filter_analysis_enable_reorder_template_and_execute(self):
        dialog = self.show_dialog(ReviewFilterAnalysisDialog(sample_result()))
        self.assertGreater(dialog.table.rowCount(), 1)
        dialog.table.setCurrentCell(0, 0)
        dialog.table.setFocus()
        QTest.keyClick(dialog.table, Qt.Key_Space)
        process_events()
        self.assertEqual(dialog.table.item(0, 0).checkState(), Qt.Checked)
        replace_text(dialog.template_name, "Manual QA")
        click(visible_button(dialog, "Save"))
        self.assertIn("Manual_QA", dialog.state["templates"])
        click(visible_button(dialog, "Move Down"))
        click(visible_button(dialog, "Execute"))
        self.assertIsNotNone(dialog.result_state)

    def test_toolbox_choices_and_apply_binner_feature_vector_gate(self):
        toolbox = self.show_dialog(DefectAnalysisToolboxDialog())
        click(visible_button(toolbox, "Apply Binner"))
        self.assertEqual(toolbox.operation, "Apply Binner")

        result = sample_result()
        disabled = self.show_dialog(ApplyBinnerDialog(result, result["defects"], {1}))
        self.assertFalse(disabled.execute.isEnabled())
        click_disabled(disabled.execute)
        click(visible_button(disabled, "Cancel"))

        result["feature_vector_file"] = "FeatureVectors.bin"
        enabled = self.show_dialog(ApplyBinnerDialog(result, result["defects"], {1}))
        self.assertTrue(enabled.execute.isEnabled())
        self.assertTrue(enabled.use_selected.isEnabled())
        enabled.ido_classifier = {"name": "Manual QA iDO", "rough_code": "R-QA"}
        enabled._refresh_labels()
        click(enabled.enable_ido)
        click(enabled.clear_codes)
        click(enabled.use_selected)
        click(enabled.execute)
        self.assertIsNotNone(enabled.result_result)

    def test_klarf_size_field_unlocks_multiplier(self):
        dialog = self.show_dialog(KlarfOptionsDialog("wafer.klarf"))
        self.assertFalse(dialog.multiplier.isEnabled())
        select_combo(dialog.field, "Class Code")
        self.assertTrue(dialog.multiplier.isEnabled())
        dialog.multiplier.setValue(0.25)
        click(visible_button(dialog, "Finished"))
        self.assertEqual(dialog.multiplier.value(), 0.25)

    def test_defect_set_collection_remove_save_and_cancel(self):
        state = {
            "defect_sets": [
                {"id": "s1", "name": "Set 1", "kind": "Manual", "defects": []},
                {"id": "s2", "name": "Set 2", "kind": "Manual", "defects": []},
            ]
        }
        dialog = self.show_dialog(DefectSetCollectionDialog(state))
        dialog.list.setCurrentRow(0)
        click(visible_button(dialog, "Remove"))
        self.assertEqual(dialog.list.count(), 1)
        click(visible_button(dialog, "OK"))
        self.assertEqual(len(dialog.result_state["defect_sets"]), 1)

        cancel = self.show_dialog(DefectSetCollectionDialog(state))
        click(visible_button(cancel, "Cancel"))
        self.assertEqual(cancel.result(), QDialog.Rejected)

    def test_alarm_tabs_filter_clear_and_transfer_summary(self):
        alarms = self.show_dialog(AlarmCenterDialog())
        click(visible_button(alarms, "Simulate Alert"))
        self.assertEqual(alarms.table.rowCount(), 1)
        alarms.table.selectRow(0)
        process_events()
        self.assertIn("Process Job", alarms.description.text())
        self.assertTrue(alarms.clear_button.isEnabled())
        with patch(
            "puma_ui.modules.system_status.dialog.QMessageBox.question",
            return_value=QMessageBox.Yes,
        ):
            click(visible_button(alarms, "Clear Alarms"))
        self.assertEqual(alarms.table.rowCount(), 0)
        self.assertEqual(alarms.alarms[0]["status"], "Inactive")
        click(alarms.active_only)
        self.assertEqual(alarms.safety_table.rowCount(), 3)
        self.assertEqual(alarms.clearable_table.rowCount(), 26)
        self.assertEqual(alarms.nonclearable_table.rowCount(), 15)
        click(visible_button(alarms, "Close"))

        transfer = self.show_dialog(TransferConfigurationDialog())
        self.assertTrue(any("simulator" in label.text().lower() for label in transfer.findChildren(QLabel)))
        click(visible_button(transfer, "Close"))

    def test_precision_advanced_attribute_and_density_group_paths(self):
        precision = self.show_dialog(PrecisionAdvancedSettingsDialog({}))
        click(precision.allow_overlap)
        select_combo(precision.sample_bin, "Unique Bin per Rule")
        select_combo(precision.overlap_bin, "New Unique Bin")
        click(visible_button(precision, "OK"))
        self.assertEqual(
            precision.result_settings,
            {
                "allow_filter_overlap": True,
                "sample_bin_assignment": "Unique Bin per Rule",
                "overlapping_bin_assignment": "New Unique Bin",
            },
        )

        attributes = self.show_dialog(AttributeSelectionDialog())
        click(visible_button(attributes, "All"))
        click(visible_button(attributes, "OK"))
        self.assertGreater(len(attributes.result_attributes), 5)

        directional = self.show_dialog(AttributeSelectionDialog({}, directional=True))
        first_direction = directional.table.cellWidget(0, 1)
        select_combo(first_direction, "High")
        click(visible_button(directional, "OK"))
        self.assertEqual(len(directional.result_attributes), 1)

        density = self.show_dialog(DensityGroupsDialog([]))
        with patch.object(density, "_pick", return_value=["Signal", "Size"]):
            click(visible_button(density, "Add Group"))
        self.assertEqual(density.table.rowCount(), 1)
        click(visible_button(density, "OK"))
        self.assertEqual(density.result_groups, [["Signal", "Size"]])


if __name__ == "__main__":
    unittest.main()

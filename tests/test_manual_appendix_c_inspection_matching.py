from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from puma_ui.modules.inspection_matching import (
    DSWMatchParametersDialog,
    InspectionMatchingUtilityDialog,
    MatchingParametersDialog,
    calculate_match,
)
from puma_ui.qt_compat import QApplication, QDialog, QMessageBox, Qt

from manual_ui_helpers import QTest, click, process_events, replace_text, visible_button


def sample_result(identifier, source_type="Lot", offset=0.0):
    return {
        "id": identifier,
        "lot_id": f"LOT-{identifier}",
        "inspection": "Deep",
        "tool_id": "Puma9980",
        "source_type": source_type,
        "defects": [
            {"id": 1, "x": 10.0 + offset, "y": 20.0 + offset},
            {"id": 2, "x": 30.0 + offset, "y": 40.0 + offset},
        ],
    }


class ManualAppendixCInspectionMatchingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self):
        for widget in list(QApplication.topLevelWidgets()):
            widget.close()
        process_events()

    def show_dialog(self, dialog):
        dialog.show()
        process_events(20)
        self.assertTrue(dialog.isVisible())
        return dialog

    def test_product_matching_add_select_match_review_and_remove(self):
        dialog = self.show_dialog(
            InspectionMatchingUtilityDialog([sample_result("A"), sample_result("B", offset=1.0)])
        )
        click(visible_button(dialog.product_page, "Add All"))
        self.assertEqual(dialog.selection_table.rowCount(), 2)
        self.assertTrue(dialog.match_button.isEnabled())
        click(dialog.match_button)
        self.assertEqual(dialog.match_progress.value(), 100)
        self.assertEqual(dialog.last_result["matched_count"], 2)
        self.assertTrue(dialog.view_button.isEnabled())
        self.assertTrue(dialog.review_action.isEnabled())
        self.assertEqual(dialog.result_table.rowCount(), 4)

        dialog.selection_table.selectRow(0)
        click(visible_button(dialog.product_page, "Remove"))
        self.assertEqual(dialog.selection_table.rowCount(), 1)
        click(visible_button(dialog.product_page, "Remove All"))
        self.assertEqual(dialog.selection_table.rowCount(), 0)

    def test_product_matching_rejects_same_selection_and_mixed_source_types(self):
        same = self.show_dialog(
            InspectionMatchingUtilityDialog([sample_result("A"), sample_result("B")])
        )
        click(visible_button(same.product_page, "Add All"))
        same.candidate_combo.setCurrentIndex(0)
        with patch("puma_ui.modules.inspection_matching.dialog.QMessageBox.warning") as warning:
            click(same.match_button)
        warning.assert_called_once()
        self.assertIsNone(same.last_result)
        same.close()

        mixed = self.show_dialog(
            InspectionMatchingUtilityDialog(
                [sample_result("LOT", "Lot"), sample_result("KLARF", "KLARF")]
            )
        )
        click(visible_button(mixed.product_page, "Add All"))
        with patch("puma_ui.modules.inspection_matching.dialog.QMessageBox.warning") as warning:
            click(mixed.match_button)
        warning.assert_called_once()
        self.assertIn("cannot mix", warning.call_args.args[2])
        self.assertIsNone(mixed.last_result)

    def test_product_parameter_profiles_defaults_accept_and_cancel(self):
        dialog = self.show_dialog(MatchingParametersDialog())
        dialog.controls["cross_matching_radius"].setValue(125.0)
        click(visible_button(dialog, "Save"))
        self.assertEqual(dialog.saved_profile["cross_matching_radius"], 125.0)
        click(visible_button(dialog, "Save As Default"))
        dialog.controls["cross_matching_radius"].setValue(1.0)
        click(visible_button(dialog, "Load Default"))
        self.assertEqual(dialog.controls["cross_matching_radius"].value(), 125.0)
        click(visible_button(dialog, "Delete"))
        self.assertIsNone(dialog.saved_profile)
        click(visible_button(dialog, "OK"))
        self.assertEqual(dialog.result(), QDialog.Accepted)
        self.assertEqual(dialog.result_parameters["cross_matching_radius"], 125.0)

        cancel = self.show_dialog(MatchingParametersDialog())
        click(visible_button(cancel, "Cancel"))
        self.assertEqual(cancel.result(), QDialog.Rejected)

    def test_dsw_parameter_dependencies_and_bounded_accept(self):
        dialog = self.show_dialog(DSWMatchParametersDialog())
        self.assertFalse(dialog.spins["test_number"].isEnabled())
        click(dialog.checks["select_test"])
        self.assertTrue(dialog.spins["test_number"].isEnabled())
        dialog.spins["test_number"].setValue(12)
        dialog.spins["intensity_ratio"].setValue(0.75)
        click(visible_button(dialog, "OK"))
        self.assertEqual(dialog.result_parameters["test_number"], 12)
        self.assertAlmostEqual(dialog.result_parameters["intensity_ratio"], 0.75)

    def test_session_save_open_result_save_and_csv_export(self):
        dialog = self.show_dialog(
            InspectionMatchingUtilityDialog([sample_result("A"), sample_result("B", offset=1.0)])
        )
        click(visible_button(dialog.product_page, "Add All"))
        click(dialog.match_button)
        with tempfile.TemporaryDirectory() as directory:
            session_path = Path(directory) / "session.json"
            result_path = Path(directory) / "result.json"
            export_path = Path(directory) / "summary.csv"
            with patch(
                "puma_ui.modules.inspection_matching.dialog.QFileDialog.getSaveFileName",
                return_value=(str(session_path), "Matching Session (*.json)"),
            ):
                dialog._save_session(save_as=True)
            self.assertTrue(session_path.is_file())
            self.assertEqual(len(json.loads(session_path.read_text(encoding="utf-8"))["selections"]), 2)

            with patch(
                "puma_ui.modules.inspection_matching.dialog.QFileDialog.getSaveFileName",
                return_value=(str(result_path), "JSON Result (*.json)"),
            ):
                dialog._save_result()
            self.assertTrue(result_path.is_file())

            with patch(
                "puma_ui.modules.inspection_matching.dialog.QFileDialog.getSaveFileName",
                return_value=(str(export_path), "Excel-compatible CSV (*.csv)"),
            ):
                dialog._export_result()
            self.assertIn("matched_count", export_path.read_text(encoding="utf-8-sig"))

            reopened = self.show_dialog(InspectionMatchingUtilityDialog([]))
            with patch(
                "puma_ui.modules.inspection_matching.dialog.QFileDialog.getOpenFileName",
                return_value=(str(session_path), "Matching Session (*.json)"),
            ):
                reopened._open_session()
            self.assertEqual(reopened.selection_table.rowCount(), 2)
            self.assertIsNotNone(reopened.last_result)
            self.assertTrue(reopened.review_action.isEnabled())

    def test_dsw_conformance_and_matching_prerequisite_and_success_paths(self):
        dialog = self.show_dialog(InspectionMatchingUtilityDialog([sample_result("A")]))
        tab_bar = dialog.tabs.tabBar()
        QTest.mouseClick(tab_bar, Qt.LeftButton, Qt.NoModifier, tab_bar.tabRect(1).center())
        process_events()
        with patch("puma_ui.modules.inspection_matching.dialog.QMessageBox.warning") as warning:
            click(visible_button(dialog.conformance_page, "Match"))
        warning.assert_called_once()
        replace_text(dialog.conformance_spec, "dsw-spec.csv")
        dialog.conformance_lot.setCurrentIndex(1)
        click(visible_button(dialog.conformance_page, "Match"))
        self.assertIn("PASS", dialog.conformance_result.text())
        self.assertTrue(dialog.graph_action.isEnabled())

        QTest.mouseClick(tab_bar, Qt.LeftButton, Qt.NoModifier, tab_bar.tabRect(2).center())
        process_events()
        with patch("puma_ui.modules.inspection_matching.dialog.QMessageBox.warning") as warning:
            click(visible_button(dialog.dsw_page, "Match"))
        warning.assert_called_once()
        dialog.dsw_lot.setCurrentIndex(1)
        replace_text(dialog.dsw_output, "C:/Batch")
        click(visible_button(dialog.dsw_page, "Match"))
        self.assertIn("PASS", dialog.dsw_result.text())

    def test_unsaved_exit_no_keeps_open_and_yes_closes(self):
        dialog = self.show_dialog(
            InspectionMatchingUtilityDialog([sample_result("A"), sample_result("B", offset=1.0)])
        )
        click(visible_button(dialog.product_page, "Add All"))
        click(dialog.match_button)
        with patch(
            "puma_ui.modules.inspection_matching.dialog.QMessageBox.question",
            return_value=QMessageBox.No,
        ):
            click(visible_button(dialog, "Exit"))
        self.assertTrue(dialog.isVisible())
        with patch(
            "puma_ui.modules.inspection_matching.dialog.QMessageBox.question",
            return_value=QMessageBox.Yes,
        ):
            click(visible_button(dialog, "Exit"))
        self.assertEqual(dialog.result(), QDialog.Accepted)

    def test_match_calculation_obeys_radius_and_unique_candidate_use(self):
        master = [{"x": 0, "y": 0}, {"x": 0.5, "y": 0.5}]
        candidate = [{"x": 0.1, "y": 0.1}]
        result = calculate_match(master, candidate, 1.0)
        self.assertEqual(result["matched_count"], 1)
        self.assertEqual(result["master_count"], 2)
        self.assertEqual(result["candidate_count"], 1)
        self.assertEqual(result["count_match_percent"], 50.0)


if __name__ == "__main__":
    unittest.main()

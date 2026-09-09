from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from puma_ui.main_window import PumaMainWindow
from puma_ui.modules.results_review import ReviewWorkspace
from puma_ui.qt_compat import QApplication, QDialog, QMessageBox, Qt
from puma_ui.recipe_store import RecipeStore

from manual_ui_helpers import QTest, process_events


def review_result():
    defects = []
    for identifier, (die_x, die_y) in enumerate(((0, 0), (1, 0), (1, 1), (3, 2)), 1):
        defects.append({
            "id": identifier,
            "x": float(identifier),
            "y": float(identifier),
            "die_x": die_x,
            "die_y": die_y,
            "test": "Test 1",
            "class_code": 0,
            "signal": 100.0,
            "size_um": 0.2,
            "marked": identifier in {2, 4},
        })
    return {
        "id": "review-a-b",
        "inspection": "Deep",
        "device": "Device1",
        "step": "Layer1",
        "status": "Complete",
        "lot_id": "LOT-AB",
        "wafer_id": "W01",
        "selected_tests": ["Test 1"],
        "defects": defects,
        "defect_count": len(defects),
    }


class ManualAppendixStartupAndShortcutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = RecipeStore(Path(self.temp.name) / "recipes.json", default_recipes=[])

    def tearDown(self):
        for widget in list(QApplication.topLevelWidgets()):
            widget.close()
        process_events()
        self.temp.cleanup()

    def make_window(self):
        with patch("puma_ui.main_window.RecipeStore", return_value=self.store):
            window = PumaMainWindow()
        window.show()
        process_events(20)
        return window

    @staticmethod
    def action(window, text):
        return next(action for action in window.findChildren(type(window.user_manual_action)) if action.text() == text)

    def test_software_startup_and_shutdown_confirmation_from_ctrl_q(self):
        window = self.make_window()
        self.assertTrue(window.isVisible())
        self.assertIn("Puma", window.windowTitle())
        with patch("puma_ui.main_window.QMessageBox.question", return_value=QMessageBox.No) as question:
            QTest.keyClick(window, Qt.Key_Q, Qt.ControlModifier)
            process_events()
        question.assert_called_once()
        self.assertTrue(window.isVisible())
        with patch("puma_ui.main_window.QMessageBox.question", return_value=QMessageBox.Yes):
            QTest.keyClick(window, Qt.Key_Q, Qt.ControlModifier)
            process_events()
        self.assertFalse(window.isVisible())

    def test_main_shortcuts_match_manual_and_conflicts_are_removed(self):
        window = self.make_window()
        expected = {
            "New Inspection": "Ctrl+N",
            "Save Inspection": "Ctrl+I",
            "Shutdown Application...": "Ctrl+Q",
            "Wafer Handling": "Ctrl+W",
            "Substrate Tracking...": "Ctrl+J",
            "Carrier Management...": "Ctrl+K",
            "E10 / Host / Process Programs...": "Ctrl+Shift+F",
            "User Manual": "F1",
        }
        for label, shortcut in expected.items():
            self.assertEqual(self.action(window, label).shortcut().toString(), shortcut)
        self.assertEqual(self.action(window, "Inspection Queue").shortcut().toString(), "")
        self.assertEqual(self.action(window, "Run One Wafer").shortcut().toString(), "")
        self.assertEqual(self.action(window, "Review Wafer").shortcut().toString(), "")

    def test_ctrl_w_invokes_wafer_handling_entry(self):
        window = self.make_window()
        fake = type("FakeWaferHandling", (), {
            "result_state": lambda self: None,
            "exec": lambda self: QDialog.Rejected,
        })
        with patch("puma_ui.main_window.WaferHandlingDialog", return_value=fake()) as dialog:
            QTest.keyClick(window, Qt.Key_W, Qt.ControlModifier)
            process_events()
        dialog.assert_called_once()

    def test_review_navigation_selection_filter_and_optics_shortcuts(self):
        result = review_result()
        dialog = ReviewWorkspace(
            result,
            current_recipe={"wafer_map": {"reticle_width": 2, "reticle_height": 2}},
        )
        dialog.show()
        process_events(20)
        first = dialog.selected_id

        QTest.keyClick(dialog, Qt.Key_F12)
        process_events()
        self.assertNotEqual(dialog.selected_id, first)
        QTest.keyClick(dialog, Qt.Key_F11)
        process_events()
        self.assertEqual(dialog.selected_id, first)

        QTest.keyClick(dialog, Qt.Key_F10)
        process_events()
        self.assertEqual(dialog.selected_id, 2)
        QTest.keyClick(dialog, Qt.Key_F10, Qt.ShiftModifier)
        process_events()
        self.assertEqual(dialog.selected_id, 3)
        QTest.keyClick(dialog, Qt.Key_F8, Qt.ShiftModifier)
        process_events()
        self.assertEqual(dialog.selected_id, 4)

        QTest.keyClick(dialog, Qt.Key_L, Qt.ControlModifier)
        process_events()
        self.assertIn(dialog.selected_id, {2, 4})
        QTest.keyClick(dialog, Qt.Key_L, Qt.ControlModifier | Qt.ShiftModifier)
        process_events()
        self.assertIn(dialog.selected_id, {2, 4})

        QTest.keyClick(dialog, Qt.Key_S, Qt.ControlModifier)
        process_events()
        self.assertEqual(len(dialog.selected_ids), 1)
        QTest.keyClick(dialog, Qt.Key_A, Qt.ControlModifier)
        process_events()
        self.assertEqual(len(dialog.selected_ids), 4)
        QTest.keyClick(dialog, Qt.Key_Q, Qt.ControlModifier)
        process_events()
        self.assertEqual(len(dialog.visible_defects), 0)
        QTest.keyClick(dialog, Qt.Key_R, Qt.ControlModifier)
        process_events()
        self.assertEqual(len(dialog.visible_defects), 4)

        before = dict(dialog.review_optics_state)
        for key in (Qt.Key_F3, Qt.Key_F5, Qt.Key_F7):
            QTest.keyClick(dialog, key)
        QTest.keyClick(dialog, Qt.Key_P, Qt.ControlModifier)
        process_events()
        self.assertGreater(dialog.review_optics_state["magnification_step"], before["magnification_step"])
        self.assertGreater(dialog.review_optics_state["light_level"], before["light_level"])
        self.assertGreater(dialog.review_optics_state["focus_offset"], before["focus_offset"])
        self.assertGreater(dialog.review_optics_state["aperture"], before["aperture"])

    def test_review_quick_image_shortcuts_update_selected_defect(self):
        dialog = ReviewWorkspace(review_result())
        dialog.show()
        process_events(20)
        QTest.keyClick(dialog, Qt.Key_S, Qt.ControlModifier | Qt.ShiftModifier)
        process_events()
        defect = next(item for item in dialog.result["defects"] if item["id"] == dialog.selected_id)
        self.assertEqual(defect["manual_image_settings"]["image_optics"], "Current Review Optics")
        QTest.keyClick(dialog, Qt.Key_T, Qt.ControlModifier | Qt.ShiftModifier)
        process_events()
        self.assertEqual(defect["manual_image_settings"]["image_optics"], "Inspection Test Optics")


if __name__ == "__main__":
    unittest.main()

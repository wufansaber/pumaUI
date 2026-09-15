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
        self.assertEqual(window._active_route_key, "home")
        self.assertEqual(window._navigation_history, ["home"])
        self.assertIs(window.workspace_stack.currentWidget(), window.home_page)
        self.assertTrue(window.home_button.isChecked())
        self.assertFalse(window.setup_breadcrumb.isChecked())
        self.assertTrue(window.left_navigation.isHidden())
        self.assertFalse(window.back_button.isEnabled())
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
            "Print Window": "Ctrl+P",
            "Shutdown Application...": "Ctrl+Q",
            "Wafer Handling": "Ctrl+W",
            "Substrate Tracking...": "Ctrl+J",
            "Carrier Management...": "Ctrl+K",
            "Set E10 States...": "Ctrl+Shift+F",
            "Diagnostics GUI...": "Ctrl+G",
            "Smart Diagnostics GUI...": "Ctrl+T",
            "Reset Wafermap Zoom": "Ctrl+R",
            "User Manual": "F1",
        }
        for label, shortcut in expected.items():
            self.assertEqual(self.action(window, label).shortcut().toString(), shortcut)
        self.assertEqual(self.action(window, "Inspection Queue").shortcut().toString(), "")
        self.assertEqual(self.action(window, "Run One Wafer").shortcut().toString(), "")
        self.assertEqual(self.action(window, "Review Wafer").shortcut().toString(), "")

    def test_main_function_keys_adjust_manual_optics_controls(self):
        window = self.make_window()
        window._set_automatic_light(False)
        start_magnification = window.pixel_size_combo.currentText()
        start_light = window.illumination_spin.value()
        start_focus = window.focus_offset_spin.value()
        QTest.keyClick(window, Qt.Key_F3)
        QTest.keyClick(window, Qt.Key_F5)
        QTest.keyClick(window, Qt.Key_F7)
        process_events()
        self.assertNotEqual(window.pixel_size_combo.currentText(), start_magnification)
        self.assertEqual(window.illumination_spin.value(), start_light + 1)
        self.assertEqual(window.focus_offset_spin.value(), start_focus + 1)
        QTest.keyClick(window, Qt.Key_F4)
        QTest.keyClick(window, Qt.Key_F6)
        QTest.keyClick(window, Qt.Key_F8)
        process_events()
        self.assertEqual(window.pixel_size_combo.currentText(), start_magnification)
        self.assertEqual(window.illumination_spin.value(), start_light)
        self.assertEqual(window.focus_offset_spin.value(), start_focus)

    def test_navigation_strip_uses_manual_configure_action(self):
        window = self.make_window()
        self.assertEqual(window.configure_button.text(), "Configure")
        self.assertIsNone(window.configure_button.menu())
        with patch("puma_ui.main_window.QMessageBox.question", return_value=QMessageBox.Yes):
            window._navigate_to("home")
        with patch.object(PumaMainWindow, "configure_recipe_overview") as configure:
            window._configure_recipe_overview()
        self.assertEqual(window._active_route_key, "setup")
        configure.assert_called_once_with()

    def test_view_menu_controls_toolbar_status_and_wafermap_image_state(self):
        window = self.make_window()
        window.standard_toolbar_action.setChecked(False)
        window.optics_toolbar_action.setChecked(False)
        window.setup_toolbar_action.setChecked(False)
        window.status_bar_action.setChecked(False)
        process_events()
        self.assertTrue(all(widget.isHidden() for widget in window.standard_toolbar_widgets))
        self.assertTrue(all(widget.isHidden() for widget in window.optics_toolbar_widgets))
        self.assertTrue(all(widget.isHidden() for widget in window.setup_toolbar_widgets))
        self.assertTrue(window.statusBar().isHidden())

        window.standard_toolbar_action.setChecked(True)
        window.optics_toolbar_action.setChecked(True)
        window.setup_toolbar_action.setChecked(True)
        window.status_bar_action.setChecked(True)
        self.assertFalse(window.toggle_wafermap_image_action.isEnabled())
        window.acquire_wafermap_image_action.trigger()
        window.wafermap_zoom_combo.setCurrentText("25")
        window.reset_wafermap_zoom()
        process_events()
        self.assertTrue(window.wafermap_image_acquired)
        self.assertTrue(window.wafermap_image_visible)
        self.assertTrue(window.wafermap_image_button.isEnabled())
        self.assertTrue(window.toggle_wafermap_image_action.isEnabled())
        self.assertTrue(window.toggle_wafermap_image_action.isChecked())
        window.toggle_wafermap_image_action.trigger()
        self.assertFalse(window.wafermap_image_visible)
        window.toggle_wafermap_image_action.trigger()
        self.assertTrue(window.wafermap_image_visible)
        self.assertEqual(window.wafermap_zoom_combo.currentText(), "100")

    def test_manual_top_level_menu_paths_are_present(self):
        window = self.make_window()

        def actions(menu_name):
            menu = next(
                action.menu()
                for action in window.menuBar().actions()
                if action.text() == menu_name
            )
            return {action.text() for action in menu.actions()}

        self.assertTrue({
            "Select Inspection", "Wafer", "Tests", "Lot Plan",
            "Wafer Post Processing", "Setup Run", "Save Inspection",
        }.issubset(actions("Set Up")))
        self.assertTrue({
            "Inspection Queue", "Lot Plan", "Snapshot Review", "View Run Log",
        }.issubset(actions("Run")))
        self.assertTrue({
            "Select Lot Results", "Import KLARF...", "Adjust Defect Location...",
            "Adjust Die Origin...", "Optics Selector...", "Sensitivity Tuner...",
        }.issubset(actions("Review")))
        self.assertTrue({
            "Reset Wafermap Zoom", "Wafermap Image", "Images", "Toolbars",
            "Image Display", "Lot Summary", "Camera Image",
        }.issubset(actions("View")))
        view_action = next(action for action in window.menuBar().actions() if action.text() == "View")
        wafermap_action = next(
            action for action in view_action.menu().actions()
            if action.text() == "Wafermap Image"
        )
        self.assertEqual(
            {action.text() for action in wafermap_action.menu().actions()},
            {"Acquire", "Toggle WaferMap Image"},
        )
        toolbar_action = next(action for action in view_action.menu().actions() if action.text() == "Toolbars")
        self.assertTrue({"Review Toolbar", "Review Image Toolbar"}.issubset(
            {action.text() for action in toolbar_action.menu().actions()}
        ))

    def test_review_toolbar_visibility_controls_are_reversible(self):
        dialog = ReviewWorkspace(review_result())
        dialog.show()
        process_events(20)
        dialog.set_review_toolbar_visible(False)
        dialog.set_review_image_toolbar_visible(False)
        process_events()
        self.assertTrue(all(widget.isHidden() for widget in dialog.review_toolbar_widgets))
        self.assertTrue(all(widget.isHidden() for widget in dialog.review_image_toolbar_widgets))
        dialog.set_review_toolbar_visible(True)
        dialog.set_review_image_toolbar_visible(True)
        process_events()
        self.assertTrue(all(widget.isVisible() for widget in dialog.review_toolbar_widgets))
        self.assertTrue(all(widget.isVisible() for widget in dialog.review_image_toolbar_widgets))

    def test_images_opens_the_last_alignment_swath_not_the_acquisition_window(self):
        window = self.make_window()
        window.current_recipe["alignment"] = {
            "mode": "BF",
            "site_images": ["Low Mag Site", "High Mag Site"],
        }
        swath = window.open_last_alignment_swath_image()
        process_events(20)
        self.assertEqual(swath.windowTitle(), "Last Alignment Swath Image")
        self.assertEqual(swath.current_image.currentText(), "High Mag Site")
        self.assertIsNone(window.image_display_window)

    def test_secs_manual_paths_change_persisted_state(self):
        window = self.make_window()

        def menu_actions(menu):
            return {action.text() for action in menu.actions()}

        tools_action = next(action for action in window.menuBar().actions() if action.text() == "Tools")
        secs_action = next(action for action in tools_action.menu().actions() if action.text() == "SECS")
        self.assertTrue({
            "Disable Communication", "Online / Remote Mode", "Online / Local Mode",
            "Set E10 States...", "Set Equipment Constants...",
            "Send Message To Host...", "Synchronize Clock",
            "Process Program Upload / Download...",
        }.issubset(menu_actions(secs_action.menu())))

        window.toggle_secs_communication()
        communication = self.store.get_preferences()["communication"]
        self.assertFalse(communication["secs_enabled"])
        self.assertEqual(window.secs_communication_action.text(), "Enable Communication")

        window.wafer_runtime_state["wafer_loaded"] = True
        self.assertTrue(window.set_secs_control_mode("Remote"))
        communication = self.store.get_preferences()["communication"]
        self.assertTrue(communication["secs_enabled"])
        self.assertEqual(communication["control_mode"], "Remote")

        window.synchronize_host_clock()
        admin = self.store.get_preferences()["system_admin"]
        self.assertIn("Clock synchronized", admin["host_messages"][-1]["message"])

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

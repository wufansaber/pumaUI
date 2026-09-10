from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from puma_ui.main_window import PumaMainWindow
from puma_ui.modules.inspection_tests import TestsSetupDialog, default_test
from puma_ui.modules.lot_plan import LotPlanDialog
from puma_ui.modules.run_control import RunOneWaferDialog
from puma_ui.modules.wafer_post_processing import WaferPostProcessingDialog
from puma_ui.qt_compat import QApplication
from puma_ui.recipe_store import RecipeStore

from manual_ui_helpers import click, close_workspace_page, process_events, visible_button


class ManualEntryGateTests(unittest.TestCase):
    """Operator-level checks for always-open entries with action-time validation."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = RecipeStore(Path(self.temp.name) / "recipes.json", default_recipes=[])
        with patch("puma_ui.main_window.RecipeStore", return_value=self.store):
            self.window = PumaMainWindow()
        self.window.resize(1440, 820)
        self.window.show()
        process_events(30)
        self.window._navigate_to("setup")
        process_events()
        self.recipe = self.store.new_recipe()
        self.recipe.update({"tests": [], "lot_plan": {}, "wafer_map": {}, "alignment": {}})
        self.window._set_current_recipe(self.recipe)
        process_events()

    def tearDown(self):
        self.window.close()
        process_events()
        self.temp.cleanup()

    def _apply(self, **updates):
        self.recipe.update(updates)
        self.window._set_current_recipe(self.recipe)
        process_events()

    def _wafer_ready(self):
        wafer_properties = self.window._current_wafer_properties()
        wafer_properties.update({"type": "Patterned", "orientation": "Down (180 deg.)"})
        self.recipe["wafer_properties"] = wafer_properties
        self.recipe["alignment"] = {"sites_defined": True, "status": "Valid"}
        self.recipe["wafer_map"] = {
            "die_pattern_defined": True,
            "die_corner_adjustment_required": False,
        }
        self.window._set_current_recipe(self.recipe)
        process_events()

    def test_primary_function_entries_are_enabled_for_a_new_recipe(self):
        entries = {
            "Select Inspection": visible_button(self.window, "Select Inspection"),
            "Wafer": self.window.wafer_button,
            "Tests": self.window.tests_button,
            "Lot Plan": self.window.lot_plan_button,
            "Wafer Post Processing": self.window.wafer_post_processing_button,
            "Setup Run": self.window.setup_run_button,
            "Save Inspection": self.window.save_inspection_button,
            "Recipe Generation": visible_button(self.window, "Recipe Generation"),
            "Alarm": self.window.alarm_button,
            "Run One Wafer": self.window.run_wafer_button,
            "Review Wafer": self.window.review_wafer_button,
            "Wafermap Image": self.window.wafermap_image_button,
            "Wafermap Zoom": self.window.wafermap_zoom_button,
            "Rotate Wafer": self.window.rotate_wafer_button,
        }
        self.assertEqual(
            [name for name, button in entries.items() if not button.isEnabled()],
            [],
        )
        self.assertTrue(self.window.design_registration_action.isEnabled())
        self.assertTrue(self.window.dbc_setup_action.isEnabled())
        self.assertTrue(self.window.dbb_setup_action.isEnabled())
        self.assertTrue(self.window.snapshot_review_action.isEnabled())
        self.assertTrue(self.window.image_display_action.isEnabled())

    def test_tests_entry_stays_open_and_validates_before_navigation(self):
        route = self.window._active_route_key
        self.assertTrue(self.window.tests_button.isEnabled())
        with patch("puma_ui.main_window.QMessageBox.warning") as warning:
            click(self.window.tests_button)
        warning.assert_called_once()
        self.assertEqual(self.window._active_route_key, route)

        self._wafer_ready()
        self.assertTrue(self.window.tests_button.isEnabled())
        click(self.window.tests_button)
        self.assertIsInstance(self.window.workspace_stack.currentWidget(), TestsSetupDialog)
        close_workspace_page(self.window, "End")

        self.recipe["wafer_map"]["die_corner_adjustment_required"] = True
        self.window._set_current_recipe(self.recipe)
        self.assertTrue(self.window.tests_button.isEnabled())
        with patch("puma_ui.main_window.QMessageBox.warning") as warning:
            click(self.window.tests_button)
        warning.assert_called_once()

    def test_loaded_incomplete_recipe_opens_tests_without_redefining_wafer(self):
        loaded = self.store.save_recipe({
            "inspection": "Needs Test Repair",
            "device": "Device-A",
            "step": "Layer-1",
            "status": "Incomplete",
            "state": "Test 1 contains invalid Sample Plan Data.",
            "wafer_properties": {"type": "Patterned", "orientation": "Down (180 deg.)"},
            "alignment": {},
            "wafer_map": {},
            "tests": [default_test(1)],
        })
        selected = type("SelectedRecipe", (), {"selected_recipe": loaded})()
        self.window._apply_selected_inspection(selected)

        with patch("puma_ui.main_window.QMessageBox.warning") as warning:
            opened = self.window.open_tests_setup()
        warning.assert_not_called()
        self.assertIsInstance(opened, TestsSetupDialog)
        self.assertIsInstance(self.window.workspace_stack.currentWidget(), TestsSetupDialog)
        self.assertTrue(self.window._tests_setup_ready)
        close_workspace_page(self.window, "End")

    def test_loaded_recipe_opens_configuration_and_review_surfaces_with_hardware_gates(self):
        loaded = self.store.save_recipe({
            "inspection": "Loaded Metadata Recipe",
            "device": "Device-A",
            "step": "Metal-1",
            "status": "Valid",
        })
        selected = type("SelectedRecipe", (), {"selected_recipe": loaded})()
        self.window._apply_selected_inspection(selected)

        with patch("puma_ui.main_window.QMessageBox.warning") as warning:
            lot_plan = self.window.open_lot_plan()
            warning.assert_not_called()
        self.assertIsInstance(lot_plan, LotPlanDialog)
        close_workspace_page(self.window)

        with patch("puma_ui.main_window.QMessageBox.warning") as warning:
            wpp = self.window.open_wafer_post_processing()
            warning.assert_not_called()
        self.assertIsInstance(wpp, WaferPostProcessingDialog)
        close_workspace_page(self.window)

        with patch("puma_ui.main_window.QMessageBox.warning") as warning:
            run_setup = self.window.open_run_one_wafer()
            warning.assert_not_called()
        self.assertIsInstance(run_setup, RunOneWaferDialog)
        close_workspace_page(self.window)

        with patch("puma_ui.main_window.QMessageBox.warning") as warning:
            alignment = self.window._navigate_to("alignment")
        self.assertFalse(alignment)
        warning.assert_called_once()
        self.assertIn("onto the stage", warning.call_args.args[2])
        self.assertEqual(self.window._active_route_key, "setup")
        self.assertNotIn("alignment", self.window.workspace_pages)

        self.window.wafer_runtime_state["wafer_loaded"] = True
        with patch("puma_ui.main_window.QMessageBox.warning") as warning:
            alignment = self.window._navigate_to("alignment")
        warning.assert_not_called()
        self.assertIsNotNone(alignment)
        close_workspace_page(self.window, "End")

        dialog_names = (
            ("DesignRegistrationDialog", self.window.open_design_registration),
            ("DBCSetupDialog", self.window.open_dbc_setup),
            ("DBBSetupDialog", self.window.open_dbb_setup),
        )
        for class_name, opener in dialog_names:
            with (
                patch(f"puma_ui.main_window.{class_name}") as dialog_class,
                patch("puma_ui.main_window.QMessageBox.warning") as warning,
            ):
                dialog_class.return_value.exec.return_value = 0
                opener()
                warning.assert_not_called()
                dialog_class.assert_called_once()

        self.window.open_image_display()
        self.assertTrue(self.window.image_display_window.isVisible())
        self.window.image_display_window.close()

        with patch("puma_ui.main_window.SelectLotResultsDialog") as selector:
            selector.return_value.exec.return_value = 0
            self.window.open_review_results()
        self.assertEqual(
            len([item for item in self.store.list_results() if item.get("is_demo")]),
            2,
        )

    def test_completed_wafer_setup_is_rechecked_when_tests_is_opened(self):
        self.window._tests_setup_ready = False
        self.window.current_recipe["alignment"] = {
            "sites_defined": True,
            "status": "Valid",
        }
        self.window.current_recipe["wafer_map"] = {
            "die_pattern_defined": True,
            "die_corner_adjustment_required": False,
        }

        with patch("puma_ui.main_window.QMessageBox.warning") as warning:
            opened = self.window.open_tests_setup()
        warning.assert_not_called()
        self.assertIsInstance(opened, TestsSetupDialog)
        self.assertTrue(self.window._tests_setup_ready)
        close_workspace_page(self.window, "End")

    def test_completed_alignment_and_map_unlock_test_development_tools(self):
        self._wafer_ready()
        self.recipe["tests"] = [default_test(1)]
        self.window._set_current_recipe(self.recipe)
        self.assertFalse(self.window.wafer_runtime_state["wafer_loaded"])
        self.assertFalse(self.window.wafer_runtime_state["wafer_aligned"])
        self.assertTrue(self.window._test_development_wafer_ready())

        opened = self.window.open_tests_setup()
        self.assertIsInstance(opened, TestsSetupDialog)
        self.assertTrue(opened.wafer_loaded)
        self.assertTrue(opened.wafer_aligned)
        self.assertTrue(opened.wafer_geometry_defined)
        with (
            patch("puma_ui.modules.inspection_tests.dialog.CareAreasDialog") as care_dialog,
            patch("puma_ui.modules.inspection_tests.dialog.QMessageBox.warning") as warning,
        ):
            care_dialog.return_value.exec.return_value = 0
            opened._care_areas()
        warning.assert_not_called()
        care_dialog.assert_called_once()
        close_workspace_page(self.window, "End")

    def test_loaded_recipe_unlocks_development_after_load_and_alignment(self):
        loaded = self.store.save_recipe({
            "inspection": "Ready Library Recipe",
            "device": "Device-A",
            "step": "Metal-1",
            "status": "Valid",
        })
        selected = type("SelectedRecipe", (), {"selected_recipe": loaded})()
        self.window._apply_selected_inspection(selected)
        self.assertFalse(self.window._test_development_wafer_ready())

        self.window.wafer_runtime_state.update({
            "wafer_loaded": True,
            "wafer_aligned": True,
        })
        self.assertTrue(self.window._test_development_wafer_ready())
        opened = self.window.open_tests_setup()
        self.assertIsInstance(opened, TestsSetupDialog)
        self.assertTrue(opened.wafer_loaded)
        self.assertTrue(opened.wafer_aligned)
        with (
            patch("puma_ui.modules.inspection_tests.dialog.CareAreasDialog") as care_dialog,
            patch("puma_ui.modules.inspection_tests.dialog.QMessageBox.warning") as warning,
        ):
            care_dialog.return_value.exec.return_value = 0
            opened._care_areas()
        warning.assert_not_called()
        care_dialog.assert_called_once()
        close_workspace_page(self.window, "End")

    def test_lot_plan_entry_stays_open_and_validates_before_navigation(self):
        self.assertTrue(self.window.lot_plan_button.isEnabled())
        with patch("puma_ui.main_window.QMessageBox.warning") as warning:
            click(self.window.lot_plan_button)
        warning.assert_called_once()
        self.assertNotIn("lot_plan", self.window.workspace_pages)

        self.recipe["tests"] = [default_test(1)]
        self.window._set_current_recipe(self.recipe)
        self.assertTrue(self.window.lot_plan_button.isEnabled())
        click(self.window.lot_plan_button)
        self.assertIsInstance(self.window.workspace_stack.currentWidget(), LotPlanDialog)
        close_workspace_page(self.window)

        self.recipe["tests"][0]["mode"] = "No Test"
        self.window._set_current_recipe(self.recipe)
        self.assertTrue(self.window.lot_plan_button.isEnabled())

    def test_wpp_entry_stays_open_and_validates_before_navigation(self):
        self.assertTrue(self.window.wafer_post_processing_button.isEnabled())
        with patch("puma_ui.main_window.QMessageBox.warning") as warning:
            click(self.window.wafer_post_processing_button)
        warning.assert_called_once()
        self.assertNotIn("wafer_post_processing", self.window.workspace_pages)

        self.recipe["tests"] = [default_test(1)]
        self.recipe["lot_plan"] = {"assignments": {"1": ["Test 1"]}}
        self.window._set_current_recipe(self.recipe)
        self.assertTrue(self.window.wafer_post_processing_button.isEnabled())
        click(self.window.wafer_post_processing_button)
        self.assertIsInstance(
            self.window.workspace_stack.currentWidget(),
            WaferPostProcessingDialog,
        )
        close_workspace_page(self.window)

        self.recipe["lot_plan"] = {"assignments": {}}
        self.window._set_current_recipe(self.recipe)
        self.assertTrue(self.window.wafer_post_processing_button.isEnabled())

    def test_setup_run_entry_stays_open_and_validates_before_navigation(self):
        self.assertTrue(self.window.setup_run_button.isEnabled())
        with patch("puma_ui.main_window.QMessageBox.warning") as warning:
            click(self.window.setup_run_button)
        warning.assert_called_once()
        self.assertNotIn("setup_run", self.window.workspace_pages)

        self._wafer_ready()
        test = default_test(1)
        test["status"] = "Valid"
        self.recipe["tests"] = [test]
        self.recipe["test_setup_valid"] = True
        self.window._set_current_recipe(self.recipe)
        self.assertTrue(self.window.setup_run_button.isEnabled())
        self.assertTrue(self.window.run_wafer_button.isEnabled())
        click(self.window.setup_run_button)
        self.assertIsInstance(self.window.workspace_stack.currentWidget(), RunOneWaferDialog)
        close_workspace_page(self.window)

        self.recipe["test_setup_valid"] = False
        self.recipe["status"] = "Incomplete"
        self.window._set_current_recipe(self.recipe)
        self.assertTrue(self.window.setup_run_button.isEnabled())
        self.assertTrue(self.window.run_wafer_button.isEnabled())

    def test_design_and_dbb_entries_stay_open_with_action_validation(self):
        self.assertTrue(self.window.design_registration_action.isEnabled())
        self.assertTrue(self.window.dbc_setup_action.isEnabled())
        self.assertTrue(self.window.dbb_setup_action.isEnabled())
        with patch("puma_ui.main_window.QMessageBox.warning") as warning:
            self.window.design_registration_action.trigger()
            self.window.dbc_setup_action.trigger()
            self.window.dbb_setup_action.trigger()
        self.assertEqual(warning.call_count, 3)

        self._wafer_ready()
        self.recipe["wafer_map"]["reticle_qualification"] = True
        self.recipe["pixel_perfect_enabled"] = True
        self.window._set_current_recipe(self.recipe)
        self.assertTrue(self.window.design_registration_action.isEnabled())
        self.assertTrue(self.window.dbc_setup_action.isEnabled())
        self.assertTrue(self.window.dbb_setup_action.isEnabled())

        self.recipe["dbb"] = {"registered": True}
        self.window._set_current_recipe(self.recipe)
        self.assertTrue(self.window.dbc_setup_action.isEnabled())
        self.assertTrue(self.window.dbb_setup_action.isEnabled())

        self.recipe["alignment"] = {"sites_defined": False}
        self.recipe["dbb"] = {"registered": False}
        self.window._set_current_recipe(self.recipe)
        self.assertTrue(self.window.design_registration_action.isEnabled())
        self.assertTrue(self.window.dbc_setup_action.isEnabled())
        self.assertTrue(self.window.dbb_setup_action.isEnabled())

    def test_all_unlock_conditions_can_coexist_without_mutual_exclusion(self):
        self._wafer_ready()
        test = default_test(1)
        test["status"] = "Valid"
        self.recipe.update(
            {
                "status": "Incomplete",
                "tests": [test],
                "test_setup_valid": True,
                "lot_plan": {"assignments": {"1": ["Test 1"]}},
                "pixel_perfect_enabled": True,
                "dbb": {"registered": True},
            }
        )
        self.recipe["wafer_map"]["reticle_qualification"] = True
        self.window._set_current_recipe(self.recipe)

        jointly_available = {
            "Tests": self.window.tests_button.isEnabled(),
            "Lot Plan": self.window.lot_plan_button.isEnabled(),
            "Wafer Post Processing": self.window.wafer_post_processing_button.isEnabled(),
            "Setup Run": self.window.setup_run_button.isEnabled(),
            "Run One Wafer": self.window.run_wafer_button.isEnabled(),
            "Design Registration": self.window.design_registration_action.isEnabled(),
            "DBC Setup": self.window.dbc_setup_action.isEnabled(),
            "DBB Setup": self.window.dbb_setup_action.isEnabled(),
            "Wafermap Image": self.window.wafermap_image_button.isEnabled(),
        }
        self.assertEqual(
            [name for name, enabled in jointly_available.items() if not enabled],
            [],
        )

        # Removing a prerequisite leaves every entry available and moves validation
        # to the attempted action.
        self.recipe["lot_plan"] = {"assignments": {}}
        self.window._set_current_recipe(self.recipe)
        self.assertTrue(self.window.wafer_post_processing_button.isEnabled())
        self.assertTrue(self.window.tests_button.isEnabled())
        self.assertTrue(self.window.lot_plan_button.isEnabled())
        self.assertTrue(self.window.setup_run_button.isEnabled())
        self.assertTrue(self.window.design_registration_action.isEnabled())
        self.assertTrue(self.window.dbb_setup_action.isEnabled())

    def test_wafermap_image_entry_stays_open_and_ignores_unavailable_toggle(self):
        self.assertTrue(self.window.wafermap_image_button.isEnabled())
        click(self.window.wafermap_image_button)
        self.assertFalse(self.window.wafermap_image_visible)
        self.assertFalse(self.window.wafermap_image_button.isChecked())

        self.recipe["wafer_map"] = {"die_pattern_defined": True}
        self.window._set_current_recipe(self.recipe)
        self.assertTrue(self.window.wafermap_image_button.isEnabled())
        click(self.window.wafermap_image_button)
        self.assertTrue(self.window.wafermap_image_visible)
        click(self.window.wafermap_image_button)
        self.assertFalse(self.window.wafermap_image_visible)

        self.recipe["wafer_map"] = {"die_pattern_defined": False}
        self.window._set_current_recipe(self.recipe)
        self.assertTrue(self.window.wafermap_image_button.isEnabled())
        self.assertFalse(self.window.wafermap_image_button.isChecked())


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest
from unittest.mock import patch

from puma_ui.main_window import DieCornerZoomDialog, WaferMapZoomDialog
from puma_ui.modules.configure_overview.dialog import SelectVisibleRecipeParametersDialog
from puma_ui.modules.header_columns.dialog import ConfigureHeaderColumnsDialog
from puma_ui.modules.image_display.dialog import CycleImageSetupDialog
from puma_ui.modules.recipe_lifecycle.dialogs import RecipeGenerationDialog, RecipeImportDialog
from puma_ui.modules.run_control.dialogs import AbortRunDialog, PrintOnRunDialog
from puma_ui.modules.wafer_alignment.dialogs import (
    AlignmentRunDialog,
    AlignmentSettingsDialog,
    BFAlignmentParametersDialog,
    DerivedSiteSelectionDialog,
    LowMagDieCornerImageDialog,
    QualifyWithTestOpticsDialog,
)
from puma_ui.modules.wafer_map.dialog import (
    AdjustDieCornerNotificationDialog,
    AdjustDieCornerOptionsDialog,
    AdjustDieCornerViewDialog,
    AdvancedDataOutputParametersDialog,
    SpecifyInnerDieValuesDialog,
)
from puma_ui.modules.wafer_properties.dialogs import LayerSettingDialog, WaferMenuDialog
from puma_ui.qt_compat import QApplication, QDialog, QMessageBox, QPushButton, Qt

from manual_ui_helpers import QTest, click, click_disabled, process_events, replace_text, select_combo, visible_button


class ManualAuxiliaryDialogTests(unittest.TestCase):
    """Real input checks for auxiliary dialogs omitted by the primary walkthrough."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def show_dialog(self, dialog):
        dialog.show()
        process_events(20)
        self.assertTrue(dialog.isVisible())
        return dialog

    def test_overview_zoom_windows_close_from_visible_close_control(self):
        for dialog_class in (DieCornerZoomDialog, WaferMapZoomDialog):
            dialog = self.show_dialog(dialog_class())
            click(visible_button(dialog, "x"))
            self.assertEqual(dialog.result(), QDialog.Accepted)

    def test_visible_recipe_parameters_tree_changes_and_saves(self):
        dialog = self.show_dialog(
            SelectVisibleRecipeParametersDialog({}, test_count=2)
        )
        self.assertIn("Test 2", dialog.item_by_name)
        item = dialog.item_by_name["Recipe Name"][0]
        rect = dialog.tree.visualItemRect(item)
        QTest.mouseClick(
            dialog.tree.viewport(),
            Qt.LeftButton,
            Qt.NoModifier,
            rect.topLeft() + dialog.tree.viewport().rect().topLeft() + type(rect.center())(8, rect.height() // 2),
        )
        process_events()
        self.assertEqual(item.checkState(0), Qt.Unchecked)
        click(visible_button(dialog, "OK"))
        self.assertEqual(dialog.result(), QDialog.Accepted)
        self.assertFalse(dialog.result_parameters["Recipe Name"])

    def test_header_columns_toggle_reset_and_never_save_an_empty_header(self):
        columns = [("name", "Name"), ("modified", "Last Modified"), ("status", "Status"), ("device", "Device"), ("step", "Process Step")]
        dialog = self.show_dialog(ConfigureHeaderColumnsDialog(columns, {}))
        for checkbox in dialog.checkboxes.values():
            if checkbox.isChecked():
                click(checkbox)
        click(visible_button(dialog, "OK"))
        self.assertTrue(dialog.result_columns["name"])
        self.assertEqual(sum(dialog.result_columns.values()), 1)

        dialog = self.show_dialog(ConfigureHeaderColumnsDialog(columns, {key: False for key, _ in columns}))
        click(visible_button(dialog, "Reset"))
        self.assertEqual(
            [checkbox.isChecked() for checkbox in dialog.checkboxes.values()],
            [True, True, True, True, False],
        )
        click(visible_button(dialog, "Cancel"))
        self.assertEqual(dialog.result(), QDialog.Rejected)

    def test_cycle_image_setup_add_order_remove_delay_play_and_cancel(self):
        dialog = self.show_dialog(CycleImageSetupDialog(["Left", "Right", "Center"], ["Left"], 1.0))
        dialog.images_list.setCurrentRow(0)
        click(visible_button(dialog, "Add >>"))
        self.assertEqual(dialog.cycle_list.count(), 2)
        dialog.cycle_list.setCurrentRow(1)
        click(visible_button(dialog, "|^"))
        self.assertEqual(dialog.cycle_list.item(0).text(), "Right")
        dialog.delay_spin.setFocus()
        QTest.keyClick(dialog.delay_spin, Qt.Key_A, Qt.ControlModifier)
        QTest.keyClicks(dialog.delay_spin, "2.5")
        process_events()
        click(visible_button(dialog, "Play"))
        self.assertTrue(dialog.play_requested)
        self.assertEqual(dialog.result_cycle_images, ["Right", "Left"])
        self.assertAlmostEqual(dialog.result_delay_seconds, 2.5)

        cancelled = self.show_dialog(CycleImageSetupDialog(["Left"], [], 1.0))
        click(visible_button(cancelled, "Cancel"))
        self.assertEqual(cancelled.result(), QDialog.Rejected)

    def test_recipe_generation_disabled_actions_unlock_with_an_active_recipe(self):
        without_recipe = self.show_dialog(RecipeGenerationDialog(False))
        save_copy = visible_button(without_recipe, "Save Copy As...")
        click_disabled(save_copy)
        self.assertEqual(without_recipe.action, "")
        click(visible_button(without_recipe, "New Inspection"))
        self.assertEqual(without_recipe.action, "new")

        with_recipe = self.show_dialog(RecipeGenerationDialog(True))
        click(visible_button(with_recipe, "Create Derivative"))
        self.assertEqual(with_recipe.action, "derivative")
        self.assertEqual(with_recipe.result(), QDialog.Accepted)

    def test_recipe_import_rejects_missing_name_then_returns_selected_components(self):
        dialog = self.show_dialog(RecipeImportDialog())
        replace_text(dialog.recipe_name, "")
        with patch("puma_ui.modules.recipe_lifecycle.dialogs.QMessageBox.warning") as warning:
            click(visible_button(dialog, "Import"))
        warning.assert_called_once()
        self.assertNotEqual(dialog.result(), QDialog.Accepted)

        replace_text(dialog.recipe_name, "Imported_Manual_QA")
        click(dialog.component_checks[-1])
        click(visible_button(dialog, "Import"))
        self.assertEqual(dialog.result_values["inspection"], "Imported_Manual_QA")
        self.assertNotIn(dialog.component_checks[-1].text(), dialog.result_values["components"])

    def test_print_and_abort_run_options_are_operable_and_persisted(self):
        print_dialog = self.show_dialog(PrintOnRunDialog())
        click(print_dialog.wafer_map)
        click(print_dialog.run_log)
        click(visible_button(print_dialog, "OK"))
        self.assertEqual(
            print_dialog.result_settings,
            {"wafer_map_after_each_test": True, "run_log_after_run": True},
        )

        abort_dialog = self.show_dialog(AbortRunDialog())
        click(abort_dialog.radios[2])
        click(visible_button(abort_dialog, "OK"))
        self.assertEqual(abort_dialog.selection, "Abort Current Inspection and Continue")

    def test_wafer_menu_and_layer_setting_invalid_valid_cancel_paths(self):
        menu = self.show_dialog(WaferMenuDialog())
        labels = {" ".join(button.text().split()) for button in menu.findChildren(QPushButton)}
        self.assertTrue({"Wafer Properties", "Alignment >", "Wafer Map >", "Select Defect Data >"}.issubset(labels))
        click(visible_button(menu, "Select Defect\nData    >"))
        self.assertTrue(menu.open_select_defect_data)
        self.assertEqual(menu.result(), QDialog.Accepted)

        layer = self.show_dialog(LayerSettingDialog())
        with patch("puma_ui.modules.wafer_properties.dialogs.QMessageBox.warning") as warning:
            click(visible_button(layer, "OK"))
        warning.assert_called_once()
        replace_text(layer.name, "Metal 2")
        layer.limit.setFocus()
        QTest.keyClick(layer.limit, Qt.Key_A, Qt.ControlModifier)
        QTest.keyClicks(layer.limit, "0.045")
        click(visible_button(layer, "OK"))
        self.assertEqual(layer.result_layer["name"], "Metal 2")
        self.assertAlmostEqual(layer.result_layer["laser_power_limit"], 0.045)

    def test_alignment_run_and_settings_save_real_checkbox_changes(self):
        run = self.show_dialog(AlignmentRunDialog())
        click(run.simulate_registration_failure)
        click(visible_button(run, "Align"))
        self.assertTrue(run.simulate_registration_failure.isChecked())

        settings = self.show_dialog(AlignmentSettingsDialog(True, False))
        click(settings.pattern_matching)
        click(settings.high_precision)
        click(visible_button(settings, "OK"))
        self.assertFalse(settings.use_pattern_matching)
        self.assertTrue(settings.high_precision_alignment)

    def test_bf_alignment_magnification_gate_can_disable_and_reenable(self):
        dialog = self.show_dialog(BFAlignmentParametersDialog())
        self.assertTrue(dialog.high_mag_group.isEnabled())
        click(dialog.single_mag)
        self.assertFalse(dialog.high_mag_group.isEnabled())
        click(dialog.dual_mag)
        self.assertTrue(dialog.high_mag_group.isEnabled())
        click(visible_button(dialog, "OK"))
        self.assertEqual(dialog.result(), QDialog.Accepted)

    def test_qualification_and_derived_selection_have_reachable_valid_paths(self):
        qualify = self.show_dialog(QualifyWithTestOpticsDialog())
        click(qualify.relearn)
        click(visible_button(qualify, "OK"))
        self.assertTrue(qualify.relearn_enabled)

        derived = self.show_dialog(DerivedSiteSelectionDialog())
        disabled = [button for button in derived.findChildren(type(derived.die_origin)) if not button.isEnabled()]
        self.assertTrue(disabled)
        click(visible_button(derived, "OK"))
        self.assertEqual(derived.selected_choice, "Select Die Origin")

    def test_low_mag_corner_requires_mark_then_finishes(self):
        dialog = self.show_dialog(LowMagDieCornerImageDialog("Select Die Origin"))
        with patch("puma_ui.modules.wafer_alignment.dialogs.QMessageBox.warning") as warning:
            click(visible_button(dialog, "Finish"))
        warning.assert_called_once()
        self.assertIsNone(dialog.marked_position)
        before = dialog.image_view.crosshair_position
        dialog.setFocus()
        QTest.keyClick(dialog, Qt.Key_Right)
        process_events()
        click(visible_button(dialog, "Mark Site"))
        self.assertNotEqual(dialog.marked_position, before)
        click(visible_button(dialog, "Finish"))
        self.assertEqual(dialog.result(), QDialog.Accepted)

    def test_inner_die_and_advanced_output_values_save_and_cancel(self):
        inner = self.show_dialog(SpecifyInnerDieValuesDialog())
        inner.rows.setValue(3)
        inner.columns.setValue(4)
        click(visible_button(inner, "OK"))
        self.assertEqual((inner.rows.value(), inner.columns.value()), (3, 4))

        output = self.show_dialog(AdvancedDataOutputParametersDialog("Recipe Die", "As Inspected"))
        select_combo(output.die_basis, "Inner Die")
        select_combo(output.orientation, "Right (90 deg.)")
        click(visible_button(output, "OK"))
        self.assertEqual(output.die_basis.currentText(), "Inner Die")
        self.assertEqual(output.orientation.currentText(), "Right (90 deg.)")

        cancelled = self.show_dialog(AdvancedDataOutputParametersDialog("Recipe Die", "As Inspected"))
        click(visible_button(cancelled, "Cancel"))
        self.assertEqual(cancelled.result(), QDialog.Rejected)

    def test_adjust_die_corner_options_notification_and_commit_flow(self):
        options = self.show_dialog(AdjustDieCornerOptionsDialog())
        click(options.shift_die_corner)
        click(visible_button(options, "OK"))
        self.assertTrue(options.shift_die_corner.isChecked())

        notice = self.show_dialog(AdjustDieCornerNotificationDialog("shift"))
        self.assertTrue(notice.details_frame.isHidden())
        click(visible_button(notice, "More >>"))
        self.assertTrue(notice.details_frame.isVisible())
        click(visible_button(notice, "<< Less"))
        self.assertTrue(notice.details_frame.isHidden())
        click(visible_button(notice, "OK"))

        view = self.show_dialog(AdjustDieCornerViewDialog("change"))
        self.assertFalse(view.finish_button.isEnabled())
        click(view.mark_button)
        self.assertTrue(view.finish_button.isEnabled())
        with patch(
            "puma_ui.modules.wafer_map.dialog.AdjustDieCornerNotificationDialog.exec",
            return_value=QDialog.Accepted,
        ), patch(
            "puma_ui.modules.wafer_map.dialog.QMessageBox.question",
            return_value=QMessageBox.Ok,
        ):
            click(view.finish_button)
        self.assertEqual(view.result(), QDialog.Accepted)


if __name__ == "__main__":
    unittest.main()

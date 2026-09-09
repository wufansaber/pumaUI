from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from puma_ui.main_window import PumaMainWindow
from puma_ui.modules.defect_data.dialogs import SelectDefectDataDialog
from puma_ui.modules.design_based_binning.dialogs import DBBSetupDialog
from puma_ui.modules.image_display.dialog import ImageDisplayWindow
from puma_ui.modules.inspection_tests import default_test
from puma_ui.modules.inspection_tests.care_areas import CareAreaOptionsDialog
from puma_ui.modules.inspection_tests.sample_plan import SamplePlanDialog
from puma_ui.modules.inspection_tests.segmentation import SegmentationSetupDialog
from puma_ui.modules.inspection_tests.sensitivity import SensitivityDialog
from puma_ui.modules.results_review.dialogs import ResultsUtilityDialog, ReviewWorkspace
from puma_ui.modules.run_control.dialogs import RunStatusDialog
from puma_ui.modules.run_control.models import default_run_setup
from puma_ui.modules.select_inspection.dialog import OpenInspectionRecipeDialog
from puma_ui.modules.show_wafer.panel import ShowWaferPanel
from puma_ui.modules.sizing.dialogs import SizingSetupTool
from puma_ui.modules.wafer_alignment.dialogs import (
    AlignmentMenuDialog,
    DerivedSiteSelectionDialog,
    SelectAlignmentSitesDialog,
)
from puma_ui.modules.wafer_handling.dialog import WaferHandlingDialog
from puma_ui.modules.wafer_properties.dialogs import EditLayerDatabaseDialog
from puma_ui.qt_compat import QApplication, QDialog, QMessageBox, Qt
from puma_ui.recipe_store import RecipeStore

from manual_ui_helpers import (
    QTest,
    click,
    click_disabled,
    process_events,
    select_combo,
    visible_button,
)


def sample_result():
    return {
        "id": "manual-gray-result",
        "inspection": "Deep",
        "device": "Device1",
        "step": "Layer1",
        "status": "Complete",
        "lot_id": "LOT-GRAY",
        "wafer_id": "W01",
        "selected_tests": ["Test 1"],
        "defects": [
            {"id": 1, "x": 1.0, "y": 2.0, "size_um": 0.4, "test": "Test 1"},
            {"id": 2, "x": 2.0, "y": 3.0, "size_um": 0.8, "test": "Test 1"},
        ],
        "defect_count": 2,
    }


class ManualGrayControlTests(unittest.TestCase):
    """Exercise every formerly unreferenced gray-control transition with QTest."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def show_widget(self, widget):
        widget.show()
        process_events(20)
        self.assertTrue(widget.isVisible())
        return widget

    def test_main_menu_gates_are_reachable_and_independent(self):
        with tempfile.TemporaryDirectory() as directory:
            store = RecipeStore(Path(directory) / "recipes.json", default_recipes=[])
            with patch("puma_ui.main_window.RecipeStore", return_value=store):
                window = self.show_widget(PumaMainWindow())
            recipe = store.new_recipe()
            recipe["tests"] = []
            window._set_current_recipe(recipe)
            self.assertTrue(window.run_lot_plan_action.isEnabled())
            self.assertTrue(window.review_wafer_button.isEnabled())
            self.assertTrue(window.image_display_action.isEnabled())

            recipe["tests"] = [default_test(1)]
            window._set_current_recipe(recipe)
            self.assertTrue(window.run_lot_plan_action.isEnabled())
            self.assertTrue(window.review_wafer_button.isEnabled())

            store.save_result(sample_result())
            window._set_current_recipe(recipe)
            self.assertTrue(window.review_wafer_button.isEnabled())
            self.assertTrue(window.run_lot_plan_action.isEnabled())

            window.wafer_runtime_state["wafer_loaded"] = True
            with patch.object(QDialog, "exec", side_effect=AssertionError("modal exec called")):
                alignment_page = window.open_alignment_menu()
            self.assertIsInstance(alignment_page, AlignmentMenuDialog)
            self.assertIs(window.workspace_stack.currentWidget(), alignment_page)
            self.assertIs(alignment_page.parent(), window.workspace_stack)
            self.assertFalse(alignment_page.isWindow())
            self.assertTrue(window.image_display_action.isEnabled())
            window.image_display_action.trigger()
            process_events()
            self.assertIsNotNone(window.image_display_window)
            self.assertTrue(window.image_display_window.isVisible())
            window.image_display_window.close()

            self.assertTrue(window.snapshot_review_action.isEnabled())
            window.active_run_dialog = type("ActiveRun", (), {"finished": False})()
            window._refresh_snapshot_review_action()
            self.assertTrue(window.snapshot_review_action.isEnabled())
            store.update_preferences({"communication": {"control_mode": "Remote"}})
            window._refresh_snapshot_review_action()
            self.assertTrue(window.snapshot_review_action.isEnabled())
            store.update_preferences({"communication": {"control_mode": "Local"}})
            window._refresh_snapshot_review_action()
            self.assertTrue(window.snapshot_review_action.isEnabled())
            window.active_run_dialog = None
            window._refresh_snapshot_review_action()
            self.assertTrue(window.snapshot_review_action.isEnabled())
            window.close()

    def test_defect_data_detach_unlocks_and_relocks(self):
        dialog = self.show_widget(SelectDefectDataDialog())
        click_disabled(dialog.detach_button)
        dialog.attached_data = {"name": "LOT-1", "type": "Lot Result"}
        dialog._refresh_status()
        self.assertTrue(dialog.detach_button.isEnabled())
        with patch(
            "puma_ui.modules.defect_data.dialogs.QMessageBox.question",
            return_value=QMessageBox.Yes,
        ):
            click(dialog.detach_button)
        self.assertEqual(dialog.attached_data, {})
        self.assertFalse(dialog.detach_button.isEnabled())

    def test_dbb_algorithm_supergroup_and_transfer_gates_do_not_conflict(self):
        dialog = self.show_widget(DBBSetupDialog({"registered": True}))
        self.assertFalse(dialog.stop_groups.isEnabled())
        click(dialog.enabled)
        click(dialog.dbg_enabled)
        select_combo(dialog.dbg_algorithm, "DBG2 (Recommended)")
        self.assertTrue(dialog.stop_groups.isEnabled())
        self.assertFalse(dialog.super_similarity.isEnabled())

        select_combo(dialog.dbg_algorithm, "DBG1")
        self.assertFalse(dialog.stop_groups.isEnabled())
        self.assertTrue(dialog.supergrouping.isEnabled())
        click(dialog.supergrouping)
        self.assertTrue(dialog.super_similarity.isEnabled())
        self.assertTrue(dialog.super_time.isEnabled())
        click(dialog.transfer_clips)
        self.assertTrue(dialog.transfer_layer.isEnabled())
        self.assertTrue(dialog.super_similarity.isEnabled())

    def test_image_cycle_start_stop_is_a_reversible_gate(self):
        dialog = self.show_widget(ImageDisplayWindow())
        self.assertTrue(dialog.start_cycle_button.isEnabled())
        self.assertFalse(dialog.stop_cycle_button.isEnabled())
        click(dialog.start_cycle_button)
        self.assertFalse(dialog.start_cycle_button.isEnabled())
        self.assertTrue(dialog.stop_cycle_button.isEnabled())
        click(dialog.stop_cycle_button)
        self.assertTrue(dialog.start_cycle_button.isEnabled())
        self.assertFalse(dialog.stop_cycle_button.isEnabled())

    def test_care_area_custom_order_unlocks_all_order_controls(self):
        dialog = self.show_widget(CareAreaOptionsDialog({}))
        self.assertTrue(dialog.always_default.isChecked())
        self.assertFalse(dialog.order_table.isEnabled())
        self.assertFalse(dialog.move_up.isEnabled())
        self.assertFalse(dialog.move_down.isEnabled())
        click(dialog.always_default)
        self.assertTrue(dialog.order_table.isEnabled())
        self.assertTrue(dialog.move_up.isEnabled())
        self.assertTrue(dialog.move_down.isEnabled())

    def test_sample_plan_edge_method_and_value_have_attainable_states(self):
        dialog = self.show_widget(SamplePlanDialog())
        self.assertFalse(dialog.edge_method.isEnabled())
        self.assertFalse(dialog.edge_value.isEnabled())
        click(dialog.edge_enabled)
        self.assertTrue(dialog.edge_method.isEnabled())
        self.assertTrue(dialog.edge_value.isEnabled())
        select_combo(dialog.edge_method, "To current stage position")
        self.assertTrue(dialog.edge_method.isEnabled())
        self.assertFalse(dialog.edge_value.isEnabled())
        select_combo(dialog.edge_method, "In microns")
        self.assertTrue(dialog.edge_value.isEnabled())

    def test_segmentation_break_editor_unlocks_only_for_a_selected_break(self):
        dialog = self.show_widget(SegmentationSetupDialog({}, [{"name": "Logic"}]))
        select_combo(dialog.segmentation_type, "Median Based Segmentation")
        self.assertFalse(dialog.break_position.isEnabled())
        click(dialog.break_buttons["Cut Histogram"])
        self.assertTrue(dialog.break_position.isEnabled())
        dialog.break_table.clearSelection()
        dialog.break_table.setCurrentItem(None)
        dialog._break_selected()
        self.assertFalse(dialog.break_position.isEnabled())

    def test_sensitivity_algorithm_and_secondary_die_gates_are_reversible(self):
        dialog = self.show_widget(SensitivityDialog(region_names=["Array"]))
        select_combo(dialog.algorithm, "HLAT")
        self.assertTrue(dialog.decouple_cf.isEnabled())
        self.assertFalse(dialog.decoupled_button.isEnabled())
        click(dialog.decouple_cf)
        self.assertTrue(dialog.decoupled_button.isEnabled())
        select_combo(dialog.algorithm, "AutoSens")
        self.assertFalse(dialog.decouple_cf.isEnabled())
        self.assertFalse(dialog.decoupled_button.isEnabled())
        select_combo(dialog.algorithm, "HLAT")
        self.assertTrue(dialog.decouple_cf.isEnabled())
        self.assertTrue(dialog.decoupled_button.isEnabled())
        self.assertTrue(dialog.secondary_factor.isEnabled())
        click(dialog.enhanced_secondary)
        self.assertFalse(dialog.secondary_factor.isEnabled())
        self.assertGreaterEqual(dialog.algorithm.findText("Secondary HLAT"), 0)
        click(dialog.enhanced_secondary)
        self.assertTrue(dialog.secondary_factor.isEnabled())

    def test_results_utility_preferences_are_exclusive_only_by_mode(self):
        target = sample_result()
        source = {**sample_result(), "id": "manual-gray-source", "lot_id": "LOT-SOURCE"}
        dialog = self.show_widget(ResultsUtilityDialog(target, [source], target["defects"]))
        select_combo(dialog.operation, "Auto Label")
        self.assertTrue(dialog.preferences_frame.isEnabled())
        select_combo(dialog.operation, "Save Filtered Lot As")
        self.assertFalse(dialog.preferences_frame.isEnabled())
        self.assertTrue(dialog.new_lot.isEnabled())

    def test_run_snapshot_and_abort_controls_follow_run_lifecycle(self):
        recipe = {"inspection": "Deep", "tests": [default_test(1)]}
        setup = default_run_setup(recipe)
        setup.update({"lot_id": "LOT-RUN", "selected_tests": ["Test 1"]})
        snapshots = []
        dialog = self.show_widget(
            RunStatusDialog(
                recipe,
                setup,
                snapshot_callback=lambda result, *_args: snapshots.append(result),
                auto_start=False,
            )
        )
        self.assertTrue(dialog.snapshot_button.isEnabled())
        self.assertTrue(dialog.abort_button.isEnabled())
        click(dialog.snapshot_button)
        self.assertEqual(len(snapshots), 1)
        dialog.progress_value = 50
        class FakeAbort:
            def __init__(self, *_args, **_kwargs):
                self.selection = "Abort Entire Run"

            def exec(self):
                return QDialog.Accepted

        fake_abort = FakeAbort
        with patch("puma_ui.modules.run_control.dialogs.AbortRunDialog", fake_abort):
            click(dialog.abort_button)
        self.assertTrue(dialog.finished)
        self.assertFalse(dialog.snapshot_button.isEnabled())
        self.assertFalse(dialog.abort_button.isEnabled())
        self.assertTrue(dialog.finish_button.isEnabled())

    def test_snapshot_update_unlocks_complete_data_operations_without_reopening(self):
        initial = {**sample_result(), "status": "Running", "snapshot_complete": False}
        complete = {**sample_result(), "snapshot_complete": True}
        dialog = self.show_widget(
            ReviewWorkspace(
                initial,
                snapshot_mode=True,
                snapshot_update_callback=lambda: complete,
            )
        )
        analysis = visible_button(dialog, "Analysis Toolbox...")
        sampling = visible_button(dialog, "Sample Marked")
        send_lot = visible_button(dialog, "Send Lot Results")
        self.assertFalse(analysis.isEnabled())
        self.assertFalse(sampling.isEnabled())
        self.assertFalse(send_lot.isEnabled())
        click(dialog.update_snapshot)
        self.assertFalse(dialog.update_snapshot.isEnabled())
        self.assertTrue(analysis.isEnabled())
        self.assertTrue(sampling.isEnabled())
        self.assertTrue(send_lot.isEnabled())
        self.assertTrue(dialog.grab_image.isEnabled())

    def test_recipe_selection_delete_and_saved_place_gates_relock(self):
        dialog = self.show_widget(OpenInspectionRecipeDialog())
        self.assertTrue(dialog.delete_button.isEnabled())
        dialog.table.clearSelection()
        dialog._clear_details()
        self.assertFalse(dialog.delete_button.isEnabled())
        first = dialog.table.item(0, 0)
        QTest.mouseClick(
            dialog.table.viewport(),
            Qt.LeftButton,
            Qt.NoModifier,
            dialog.table.visualItemRect(first).center(),
        )
        process_events()
        self.assertTrue(dialog.delete_button.isEnabled())

        self.assertFalse(dialog.remove_place_button.isEnabled())
        place_button, _place = dialog.place_buttons[0]
        click(place_button)
        self.assertTrue(dialog.remove_place_button.isEnabled())
        click(dialog.remove_place_button)
        self.assertFalse(dialog.remove_place_button.isEnabled())

    def test_show_wafer_unload_and_recovery_relock_after_return(self):
        panel = self.show_widget(ShowWaferPanel())
        self.assertTrue(panel.unload_wafer_button.isEnabled())
        self.assertTrue(panel.recovery_button.isEnabled())
        click(panel.unload_wafer_button)
        self.assertFalse(panel.unload_wafer_button.isEnabled())
        self.assertFalse(panel.recovery_button.isEnabled())
        click(panel.load_wafer_button)
        self.assertTrue(panel.unload_wafer_button.isEnabled())
        click(panel.recovery_button)
        self.assertFalse(panel.unload_wafer_button.isEnabled())
        self.assertFalse(panel.recovery_button.isEnabled())

    def test_sizing_reference_computed_requires_a_lot_result_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            store = RecipeStore(Path(directory) / "recipes.json", default_recipes=[])
            tool = self.show_widget(SizingSetupTool(store, initial_result=sample_result()))
            self.assertTrue(tool.reference_computed.isEnabled())
            mapping = next(item for item in tool.state["maps"] if item["id"] == tool.state["active_map_id"])
            reference = next(item for item in tool.state["defect_sets"] if item["id"] == mapping["reference_set_id"])
            reference["kind"] = "KLARF"
            tool.refresh()
            self.assertFalse(tool.reference_computed.isEnabled())
            reference["kind"] = "Lot Result"
            tool.refresh()
            self.assertTrue(tool.reference_computed.isEnabled())

    def test_alignment_previous_and_derivative_reference_gates_are_reachable(self):
        sites = self.show_widget(
            SelectAlignmentSitesDialog(
                "DF",
                existing_sites=[[-1800.0, 1200.0], [-800.0, 1200.0]],
                existing_images=["Old 1", "Old 2"],
            )
        )
        self.assertFalse(sites.prev_button.isEnabled())
        click(sites.next_button)
        self.assertTrue(sites.prev_button.isEnabled())
        click(sites.prev_button)
        self.assertFalse(sites.prev_button.isEnabled())

        unavailable = self.show_widget(DerivedSiteSelectionDialog())
        self.assertFalse(unavailable.old_corner.isEnabled())
        self.assertFalse(unavailable.site_offset.isEnabled())
        unavailable.close()

        available = self.show_widget(DerivedSiteSelectionDialog(has_old_corner=True))
        self.assertTrue(available.old_corner.isEnabled())
        self.assertFalse(available.site_offset.isEnabled())
        click(available.old_corner)
        self.assertTrue(available.site_offset.isEnabled())
        click(available.site_offset)
        click(available.die_origin)
        self.assertFalse(available.site_offset.isEnabled())
        self.assertFalse(available.site_offset.isChecked())

    def test_wafer_handling_unload_recovery_and_carrier_gates_are_reachable(self):
        dialog = self.show_widget(WaferHandlingDialog())
        self.assertFalse(dialog.unload_wafer_button.isEnabled())
        self.assertFalse(dialog.recovery_button.isEnabled())
        self.assertTrue(dialog.port_panels[1].unload_button.isEnabled())
        click(dialog.load_wafer_button)
        self.assertTrue(dialog.unload_wafer_button.isEnabled())
        self.assertTrue(dialog.recovery_button.isEnabled())
        self.assertTrue(dialog.port_panels[1].unload_button.isEnabled())
        click(dialog.recovery_button)
        self.assertFalse(dialog.unload_wafer_button.isEnabled())
        self.assertFalse(dialog.recovery_button.isEnabled())
        click(dialog.port_panels[1].unload_button)
        self.assertFalse(dialog.port_panels[1].unload_button.isEnabled())

    def test_layer_database_selection_and_add_current_have_complete_cycles(self):
        dialog = self.show_widget(
            EditLayerDatabaseDialog(
                [{"name": "Existing", "laser_power_limit": 0.2}],
                current_layer={"name": "Recipe Layer", "laser_power_limit": 0.35},
            )
        )
        self.assertFalse(dialog.modify_button.isEnabled())
        self.assertFalse(dialog.delete_button.isEnabled())
        self.assertTrue(dialog.add_current.isEnabled())
        click(dialog.add_current)
        self.assertEqual([item["name"] for item in dialog.layers], ["Existing", "Recipe Layer"])
        self.assertFalse(dialog.add_current.isEnabled())
        self.assertTrue(dialog.modify_button.isEnabled())
        self.assertTrue(dialog.delete_button.isEnabled())
        dialog.table.clearSelection()
        process_events()
        self.assertFalse(dialog.modify_button.isEnabled())
        self.assertFalse(dialog.delete_button.isEnabled())


if __name__ == "__main__":
    unittest.main()

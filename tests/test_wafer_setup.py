from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from puma_ui.qt_compat import (
    QApplication,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QEvent,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    Qt,
    QWidget,
)
from puma_ui.interaction_guard import WheelEditGuard, install_wheel_edit_guard
from puma_ui.main_window import CareAreasPreview, PumaMainWindow, SamplePlanPreview
from puma_ui.modules.image_display.dialog import AdvancedOpticsDialog, ImageDisplayWindow
from puma_ui.modules.defect_data.dialogs import (
    SaveImportedLotResultDialog,
    SelectDefectDataDialog,
    SelectImportedWaferDialog,
)
from puma_ui.modules.inspection_tests import (
    CareAreasDialog,
    NanoPointImageTemplatesDialog,
    TestsSetupDialog,
    default_test,
)
from puma_ui.modules.inspection_tests.light_training import (
    LightTrainingDialog,
    NoiseBoxDialog,
)
from puma_ui.modules.inspection_tests.sample_plan import SamplePlanDialog
from puma_ui.modules.inspection_tests.segmentation import (
    SDISensitivityDialog,
    SegmentationDialog,
    SegmentationSetupDialog,
    SingleDieInspectionDialog,
)
from puma_ui.modules.inspection_tests.sensitivity import SensitivityDialog
from puma_ui.modules.inspection_tests.fourier import (
    AdvancedFourierOptionsDialog,
    FourierBoxDialog,
)
from puma_ui.modules.inspection_tests.care_areas import (
    ApplyOffsetDialog,
    CareAreaImportDialog,
    CopyFillDialog,
    RegisterCareAreaGroupDialog,
    care_area_file_metadata,
)
from puma_ui.modules.recipe_lifecycle import (
    ExtractComponentDialog,
    InspectionPropertiesDialog,
    InsertComponentDialog,
    RecipeHistoryDialog,
    SaveInspectionDialog,
)
from puma_ui.modules.select_inspection import OpenInspectionRecipeDialog
from puma_ui.modules.wafer_alignment.dialogs import (
    DEFAULT_ALIGNMENT_QUALITY_TARGETS,
    AlignmentMenuDialog,
    AlignmentParametersDialog,
    AutoSiteAlignmentParametersDialog,
    AutoSiteSelectionDialog,
    SelectAlignmentSitesDialog,
    evaluate_alignment_quality,
    simulated_alignment_candidate_scores,
)
from puma_ui.modules.wafer_handling.dialog import WaferHandlingDialog
from puma_ui.modules.wafer_map.dialog import (
    EditMapDialog,
    ReticleSizeDialog,
    ScribeLinesSetupDialog,
    WaferMapSetupDialog,
    die_grid_dimensions,
    WaferMapSiteCanvas,
    WaferMapSiteSelectionDialog,
)
from puma_ui.modules.wafer_properties.dialogs import (
    EditLayerDatabaseDialog,
    WaferPropertiesDialog,
)
from puma_ui.modules.show_wafer.panel import ShowWaferPanel
from puma_ui.modules.run_control.dialogs import RunStatusDialog
from puma_ui.recipe_store import RecipeStore


class WaferSetupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_mouse_wheel_edits_values_only_after_clicking_the_control(self):
        guard = WheelEditGuard()
        surface = QWidget()
        controls = [QComboBox(surface), QSpinBox(surface), QDoubleSpinBox(surface), QSlider(surface)]
        controls[0].addItems(["A", "B"])
        for control in controls:
            wheel = QEvent(QEvent.Wheel)
            self.assertTrue(guard.eventFilter(control, wheel))
            self.assertFalse(guard.eventFilter(control, QEvent(QEvent.MouseButtonPress)))
            self.assertFalse(guard.eventFilter(control, QEvent(QEvent.Wheel)))
            self.assertIs(guard.active_editor, control)
        self.assertIs(guard._editor_for(controls[1].lineEdit()), controls[1])
        guard.eventFilter(surface, QEvent(QEvent.MouseButtonPress))
        self.assertIsNone(guard.active_editor)
        self.assertTrue(guard.eventFilter(controls[0], QEvent(QEvent.Wheel)))

    def test_wheel_guard_installs_once_per_application(self):
        existing = getattr(self.app, "_puma_wheel_edit_guard", None)
        if existing is not None:
            self.app.removeEventFilter(existing)
            delattr(self.app, "_puma_wheel_edit_guard")
        first = install_wheel_edit_guard(self.app)
        second = install_wheel_edit_guard(self.app)
        self.assertIs(first, second)

    def test_new_wafer_map_does_not_claim_an_existing_pattern(self):
        dialog = WaferMapSetupDialog()
        self.assertFalse(dialog.die_pattern_defined)
        self.assertEqual(dialog.die_count, 0)

    def test_show_wafer_panel_enforces_carrier_and_chuck_state(self):
        panel = ShowWaferPanel()
        self.assertTrue(panel.wafer_loaded)
        self.assertTrue(panel.wafer_aligned)
        self.assertFalse(panel._unload_carrier(1))
        self.assertTrue(panel.carrier_loaded[1])

        self.assertTrue(panel._unload_wafer())
        self.assertEqual(panel.slot_states[1][25], "Present")
        self.assertTrue(panel._unload_carrier(1))
        self.assertFalse(panel.carrier_loaded[1])

    def test_show_wafer_panel_load_align_recovery_and_orientation(self):
        panel = ShowWaferPanel()
        panel._unload_wafer()
        panel._load_carrier(3)
        panel._select_slot(3, 10)
        panel._load_and_align()
        self.assertEqual((panel.wafer_source_port, panel.wafer_source_slot), (3, 10))
        self.assertEqual(panel.slot_states[3][10], "Aligned")
        panel._set_orientation(90)
        self.assertEqual(panel.orientation, 90)
        self.assertTrue(panel.orientation_controls[90].isChecked())
        panel._automatic_recovery()
        self.assertFalse(panel.wafer_loaded)
        self.assertEqual(panel.slot_states[3][10], "Present")

    def test_show_wafer_panel_port_choice_is_a_visible_count(self):
        panel = ShowWaferPanel()
        panel.set_visible_ports("1")
        self.assertFalse(panel.port_widgets[1].isHidden())
        self.assertTrue(panel.port_widgets[2].isHidden())
        self.assertTrue(panel.port_widgets[3].isHidden())
        panel.set_visible_ports("3")
        self.assertFalse(panel.port_widgets[1].isHidden())
        self.assertFalse(panel.port_widgets[2].isHidden())
        self.assertFalse(panel.port_widgets[3].isHidden())

        recipe_dialog = OpenInspectionRecipeDialog()
        self.assertEqual([button.text() for button in recipe_dialog.load_port_buttons], ["1", "2", "3"])
        self.assertEqual(recipe_dialog.load_port_label.text(), "Show Load Ports:")
        recipe_dialog._set_load_port("2")
        self.assertFalse(recipe_dialog.wafer_panel.port_widgets[2].isHidden())
        self.assertTrue(recipe_dialog.wafer_panel.port_widgets[3].isHidden())

    def test_embedded_wafer_panel_alignment_follows_selected_recipe(self):
        panel = ShowWaferPanel()
        panel._unload_wafer()
        panel.update_recipe(
            {
                "wafer_properties": {"type": "Patterned"},
                "alignment": {"sites_defined": False},
            }
        )
        self.assertFalse(panel.load_align_button.isEnabled())
        self.assertTrue(panel.load_wafer_button.isEnabled())

        panel.update_recipe(
            {
                "wafer_properties": {"type": "Patterned"},
                "alignment": {"sites_defined": True},
            }
        )
        self.assertTrue(panel.load_align_button.isEnabled())
        panel.update_recipe(
            {
                "wafer_properties": {"type": "Blank"},
                "alignment": {"sites_defined": True},
            }
        )
        self.assertFalse(panel.load_align_button.isEnabled())

    def test_select_inspection_search_filter_clear_and_selection_details(self):
        dialog = OpenInspectionRecipeDialog()
        self.assertTrue(dialog.table.isSortingEnabled())
        self.assertFalse(dialog.path_open_button.isHidden())

        dialog._show_search_panel()
        dialog.find_edit.setText("_180_102")
        self.assertEqual(dialog.table.rowCount(), 1)
        self.assertEqual(dialog.table.item(0, 0).text(), "_180_102")

        dialog._hide_search_panel()
        dialog.recipe_filter.setCurrentText("Invalid Recipes")
        self.assertTrue(dialog.clear_recipe_filter_button.isEnabled())
        self.assertGreater(dialog.table.rowCount(), 0)
        for row in range(dialog.table.rowCount()):
            self.assertNotEqual(dialog.table.item(row, 2).text(), "Valid")

        dialog._clear_recipe_filter()
        self.assertEqual(dialog.recipe_filter.currentText(), "All Recipes")
        self.assertFalse(dialog.clear_recipe_filter_button.isEnabled())
        dialog.table.sortItems(0, Qt.DescendingOrder)
        dialog.table.selectRow(0)
        self.assertEqual(
            dialog._current_recipe()["inspection"],
            dialog.table.item(0, 0).text(),
        )

        dialog.find_edit.setText("no-such-recipe")
        self.assertEqual(dialog.table.rowCount(), 0)
        self.assertTrue(dialog.path_open_button.isHidden())
        self.assertTrue(dialog.more_status_button.isHidden())

    def test_select_inspection_more_recent_delete_and_name_column_rules(self):
        dialog = OpenInspectionRecipeDialog()
        self.assertIn("inspection", dialog.DEFAULT_VISIBLE_COLUMN_KEYS)
        dialog._set_column_visible("inspection", False)
        dialog._set_column_visible("approval", False)
        dialog._apply_header_columns()
        self.assertFalse(dialog.table.isColumnHidden(0))
        self.assertTrue(dialog.table.isColumnHidden(3))

        invalid_row = next(
            row for row in range(dialog.table.rowCount())
            if dialog.table.item(row, 2).text() != "Valid"
        )
        dialog.table.selectRow(invalid_row)
        self.assertFalse(dialog.more_status_button.isHidden())
        self.assertTrue(dialog.more_status_button.isEnabled())

        dialog._set_source("recent")
        self.assertGreater(dialog.table.rowCount(), 0)
        dialog._clear_recent_items()
        self.assertEqual(dialog.table.rowCount(), 0)

        dialog = OpenInspectionRecipeDialog()
        before = len(dialog.recipes)
        with patch(
            "puma_ui.modules.select_inspection.dialog.DeleteRecipeConfirmationDialog.exec",
            return_value=QDialog.Accepted,
        ):
            dialog._delete_current_recipe()
        self.assertEqual(len(dialog.recipes), before - 1)

    def test_select_inspection_explorer_status_and_new_place_actions(self):
        dialog = OpenInspectionRecipeDialog()
        with patch(
            "puma_ui.modules.select_inspection.dialog.QDesktopServices.openUrl",
            return_value=True,
        ) as open_url:
            dialog._show_current_recipe_path()
        open_url.assert_called_once()
        self.assertIn("Recipe folder opened", dialog.state_edit.text())

        with patch(
            "puma_ui.modules.select_inspection.dialog.QMessageBox.information"
        ) as information:
            dialog._show_recipe_status_more()
        information.assert_called_once()
        self.assertIn("Recipe Status", information.call_args.args[1])

        before = len(dialog.places)
        with patch(
            "puma_ui.modules.select_inspection.dialog.AddNewPlaceDialog.exec",
            return_value=QDialog.Accepted,
        ):
            dialog._add_new_place()
        self.assertEqual(len(dialog.places), before + 1)
        self.assertIsNotNone(dialog.selected_place)
        dialog._remove_selected_place()
        self.assertEqual(len(dialog.places), before)

    def test_main_toolbar_optics_follow_manual_engage_and_apply_rules(self):
        window = PumaMainWindow()
        window._navigate_to("setup")
        self.assertTrue(window.optics_engaged)
        self.assertFalse(window.apply_optics_button.isEnabled())
        self.assertTrue(window.engage_optics_button.isHidden())
        self.assertFalse(window.illumination_spin.isEnabled())
        self.assertTrue(window.wafermap_image_button.isEnabled())
        self.assertTrue(window.rotate_wafer_button.isEnabled())

        original_aperture = window.optics_applied_settings["aperture"]
        window._set_optics_engaged(False)
        window.aperture_spin.setValue(original_aperture + 10)
        self.assertEqual(window.optics_applied_settings["aperture"], original_aperture)
        self.assertTrue(window.apply_optics_button.isEnabled())
        window._apply_toolbar_optics()
        self.assertEqual(window.optics_applied_settings["aperture"], original_aperture + 10)

        window._set_automatic_light(False)
        self.assertTrue(window.illumination_spin.isEnabled())
        self.assertFalse(window.manual_light_button.isHidden())
        self.assertTrue(window.auto_light_button.isHidden())

    def test_home_and_setup_have_distinct_manual_destinations(self):
        window = PumaMainWindow()
        window.show()
        QApplication.processEvents()
        self.assertEqual(window.user_manual_action.shortcut().toString(), "F1")
        for section in window.recipe_overview_sections.values():
            section.set_expanded(True)

        window.setup_breadcrumb.click()
        QApplication.processEvents()

        with patch(
            "puma_ui.main_window.QMessageBox.question", return_value=QMessageBox.Yes
        ) as question:
            window.home_button.click()
        question.assert_called_once()
        QApplication.processEvents()
        self.assertEqual(window._active_route_key, "home")
        self.assertIs(window.workspace_stack.currentWidget(), window.home_page)
        self.assertTrue(window.left_navigation.isHidden())
        self.assertTrue(window.home_button.isChecked())
        self.assertFalse(window.setup_breadcrumb.isChecked())
        self.assertTrue(all(not action.isVisible() for action in window.setup_toolbar_actions))

        window.setup_breadcrumb.click()
        QApplication.processEvents()
        self.assertEqual(window._active_route_key, "setup")
        self.assertIs(window.workspace_stack.currentWidget(), window.overview_scroll)
        self.assertFalse(window.left_navigation.isHidden())
        self.assertFalse(window.home_button.isChecked())
        self.assertTrue(window.setup_breadcrumb.isChecked())
        self.assertTrue(all(action.isVisible() for action in window.setup_toolbar_actions))
        self.assertFalse(window.recipe_overview_sections["Recipe Properties"].expanded)
        self.assertFalse(window.recipe_overview_sections["Wafer Layout"].expanded)
        self.assertTrue(window.recipe_overview_sections["Test 1"].expanded)

        with patch(
            "puma_ui.main_window.QMessageBox.question", return_value=QMessageBox.Yes
        ):
            window.end_button.click()
        QApplication.processEvents()
        self.assertEqual(window._active_route_key, "home")
        self.assertIs(window.workspace_stack.currentWidget(), window.home_page)
        self.assertTrue(window.isVisible())

    def test_setup_exit_confirmation_can_keep_the_session_open(self):
        window = PumaMainWindow()
        window._navigate_to("setup")
        with patch(
            "puma_ui.main_window.QMessageBox.question", return_value=QMessageBox.No
        ):
            result = window._navigate_to("home")
        self.assertFalse(result)
        self.assertEqual(window._active_route_key, "setup")
        self.assertIs(window.workspace_stack.currentWidget(), window.overview_scroll)

    def test_navigation_bar_visibility_follows_the_view_menu(self):
        window = PumaMainWindow()
        window.show()
        QApplication.processEvents()
        self.assertTrue(window.navigation_bar_action.isChecked())
        self.assertTrue(window.navigation_strip_widget.isVisible())

        window.navigation_bar_action.setChecked(False)
        QApplication.processEvents()
        self.assertTrue(window.navigation_strip_widget.isHidden())

        window.navigation_bar_action.setChecked(True)
        QApplication.processEvents()
        self.assertTrue(window.navigation_strip_widget.isVisible())

    def test_navigation_strip_tracks_hierarchy_and_history(self):
        window = PumaMainWindow()
        self.assertFalse(window.back_button.isEnabled())
        self.assertFalse(window.forward_button.isEnabled())

        with patch.object(window, "open_wafer_properties") as open_properties:
            window._navigate_to("wafer_properties")
            self.assertEqual(window.parent_breadcrumb.text(), "Wafer")
            self.assertEqual(window.current_view_label.text(), "Wafer Properties")
            self.assertTrue(window.back_button.isEnabled())
            open_properties.assert_called_once_with()

            window._navigate_history(-1)
            self.assertFalse(window.back_button.isEnabled())
            self.assertTrue(window.forward_button.isEnabled())
            self.assertTrue(window.current_view_label.isHidden())

            window._navigate_history(1)
            self.assertEqual(open_properties.call_count, 2)
            self.assertEqual(window.current_view_label.text(), "Wafer Properties")

    def test_sidebar_routes_open_inside_the_main_workspace(self):
        window = PumaMainWindow()
        with patch.object(QDialog, "exec", side_effect=AssertionError("modal exec called")):
            window._navigate_to("select_inspection")

        page = window.workspace_pages["select_inspection"]
        self.assertIs(window.workspace_stack.currentWidget(), page)
        self.assertIs(page.parent(), window.workspace_stack)
        self.assertFalse(page.isWindow())
        self.assertEqual(window.current_view_label.text(), "Select Inspection")

        page.reject()
        QApplication.processEvents()
        self.assertNotIn("select_inspection", window.workspace_pages)
        self.assertIs(window.workspace_stack.currentWidget(), window.overview_scroll)

    def test_alignment_menu_opens_inside_the_main_workspace(self):
        window = PumaMainWindow()
        window.wafer_runtime_state["wafer_loaded"] = True
        with patch.object(QDialog, "exec", side_effect=AssertionError("modal exec called")):
            page = window._navigate_to("alignment")

        self.assertIsInstance(page, AlignmentMenuDialog)
        self.assertIs(window.workspace_stack.currentWidget(), page)
        self.assertIs(page.parent(), window.workspace_stack)
        self.assertFalse(page.isWindow())
        self.assertEqual(window._active_route_key, "alignment")
        self.assertEqual(window.current_view_label.text(), "Alignment")

        page.reject()
        QApplication.processEvents()
        self.assertNotIn("alignment", window.workspace_pages)
        self.assertIs(window.workspace_stack.currentWidget(), window.overview_scroll)

    def test_top_navigation_restores_cached_workspace_page(self):
        window = PumaMainWindow()
        window._navigate_to("wafer_map")
        wafer_page = window.workspace_pages["wafer_map"]

        window._navigate_to("setup")
        self.assertIs(window.workspace_stack.currentWidget(), window.overview_scroll)
        window._navigate_history(-1)

        self.assertIs(window.workspace_stack.currentWidget(), wafer_page)
        self.assertEqual(window._active_route_key, "wafer_map")
        self.assertEqual(window.current_view_label.text(), "Wafer Map")

    def test_wafer_selector_expands_inline_then_opens_the_selected_workspace_page(self):
        window = PumaMainWindow()
        window.open_wafer_menu()
        window.wafer_drawer_animation.setCurrentTime(
            window.wafer_drawer_animation.duration()
        )
        QApplication.processEvents()
        self.assertTrue(window._wafer_drawer_open)
        self.assertFalse(window.wafer_drawer.isWindow())
        self.assertIs(window.wafer_drawer.parent(), window.centralWidget())
        self.assertEqual(window.wafer_drawer.maximumWidth(), 246)
        self.assertTrue(window.wafer_button.isChecked())

        window.wafer_drawer_buttons["wafer_map"].click()
        window.wafer_drawer_animation.setCurrentTime(
            window.wafer_drawer_animation.duration()
        )
        QApplication.processEvents()
        self.assertIn("wafer_map", window.workspace_pages)
        self.assertIs(
            window.workspace_stack.currentWidget(),
            window.workspace_pages["wafer_map"],
        )
        self.assertEqual(window._active_route_key, "wafer_map")
        self.assertFalse(window.context_navigation.isHidden())
        self.assertFalse(window._wafer_drawer_open)
        self.assertTrue(window.wafer_drawer.isHidden())

    def test_recipe_overview_test_headings_open_specific_modules(self):
        window = PumaMainWindow()
        with patch.object(window, "open_tests_setup") as open_tests:
            window.overview_action_labels["Fourier Filter"].activate()
            open_tests.assert_called_once_with(
                initial_module="fourier_filter", initial_test_index=0
            )
        with patch.object(window, "open_tests_setup") as open_tests:
            window.overview_action_labels["Care Areas"].activate()
            open_tests.assert_called_once_with(
                initial_module="care_areas", initial_test_index=0
            )

    def test_recipe_overview_tracks_all_defined_tests_and_selected_test(self):
        window = PumaMainWindow()
        recipe = window.recipe_store.new_recipe()
        first = default_test(1)
        second = default_test(2)
        second["name"] = "Edge Scan"
        second["inspection_optics"]["pixel_size"] = "SL1020"
        recipe["tests"] = [first, second]
        window.selected_test_index = 1
        window._set_current_recipe(recipe)

        self.assertEqual(len(window.test_overview_contexts), 2)
        self.assertIn("Test 1", window.recipe_overview_sections)
        self.assertIn("Test 2", window.recipe_overview_sections)
        self.assertFalse(window.recipe_overview_sections["Test 1"].expanded)
        self.assertTrue(window.recipe_overview_sections["Test 2"].expanded)
        self.assertEqual(
            window._test_overview_values("Test Properties", "Test Name", 1)[0].text(),
            "Edge Scan",
        )
        self.assertEqual(
            window._test_overview_values(
                "Inspection Optics", "Magnification\n(Pixel Size)", 1
            )[0].text(),
            "SL1020",
        )
        with patch.object(window, "open_tests_setup") as open_tests:
            window.overview_action_labels[("Care Areas", 1)].activate()
            open_tests.assert_called_once_with(
                initial_module="care_areas", initial_test_index=1
            )

    def test_recipe_overview_displays_wafer_post_processing_summary(self):
        window = PumaMainWindow()
        recipe = window.recipe_store.new_recipe()
        recipe["wpp_valid"] = True
        recipe["wafer_post_processing"] = {
            "template_name": "Production",
            "operations": [
                {"name": "Clustering", "enabled": True},
                {"name": "Sampling", "enabled": False},
                {"name": "Repeater Analysis", "enabled": True},
            ],
        }
        window._set_current_recipe(recipe)

        self.assertIn("Wafer Post Processing", window.recipe_overview_sections)
        self.assertEqual(window.wpp_overview_labels["Processing Status"].text(), "Valid")
        self.assertEqual(window.wpp_overview_labels["Template"].text(), "Production")
        self.assertEqual(window.wpp_overview_labels["Enabled Operations"].text(), "2")
        self.assertEqual(
            window.wpp_overview_labels["Execution Order"].text(),
            "Clustering -> Repeater Analysis",
        )

    def test_tests_overview_module_dispatches_to_requested_editor(self):
        dialog = TestsSetupDialog([default_test(1)])
        dialog.initial_module = "sample_plan"
        with patch.object(dialog, "_sample_plan") as open_sample_plan:
            dialog._open_initial_module()
        open_sample_plan.assert_called_once_with()
        self.assertIsNone(dialog.initial_module)

    def test_sample_plan_copy_paste_and_manual_shortcuts(self):
        first = default_test(1)
        second = default_test(2)
        first["sample_plan"]["coverage"] = 25.0
        first["sample_plan"]["overrides"]["0,0"] = "Secondary Threshold"
        dialog = TestsSetupDialog([first, second])
        dialog.current_test = 0
        self.assertTrue(dialog.copy_current_sample_plan())
        dialog.current_test = 1
        self.assertTrue(dialog.paste_current_sample_plan())
        self.assertEqual(dialog.tests[1]["sample_plan"]["coverage"], 25.0)
        self.assertEqual(
            dialog.tests[1]["sample_plan"]["overrides"]["0,0"],
            "Secondary Threshold",
        )

        window = PumaMainWindow()
        self.assertEqual(window.copy_sample_plan_action.shortcut().toString(), "Ctrl+Shift+C")
        self.assertEqual(window.paste_sample_plan_action.shortcut().toString(), "Ctrl+Shift+V")

    def test_sensitivity_region_navigation_and_copy_paste(self):
        dialog = SensitivityDialog(region_names=["Array", "Logic"])
        self.assertEqual(dialog.tabs.tabText(0), "Define Segmentation")
        self.assertEqual(dialog.tabs.tabText(1), "Algorithm Parameters")
        dialog.region_selector.setCurrentText("Array")
        dialog.state["regions"]["Array"]["enable_remap"] = True
        dialog.segmentation_state["regions"]["Array"]["channels"][0].update(
            {
                "type": "Projection Based Segmentation",
                "breaks": [{"axis": "X", "position": 0.4, "group": 1}],
            }
        )
        dialog._copy_region()
        dialog.region_selector.setCurrentText("Logic")
        dialog._paste_region()
        self.assertTrue(dialog.state["regions"]["Logic"]["enable_remap"])
        self.assertEqual(
            dialog.segmentation_state["regions"]["Logic"]["channels"][0]["type"],
            "Projection Based Segmentation",
        )
        self.assertEqual(dialog.region_selector.currentText(), "Logic")
        dialog._step_region(-1)
        self.assertEqual(dialog.region_selector.currentText(), "Array")

    def test_sensitivity_exposes_manual_algorithm_groups_and_segment_parameters(self):
        dialog = SensitivityDialog(region_names=["Array"])
        expected = {
            "HLAT",
            "FAST",
            "AutoSens",
            "ArrayMode",
            "Wafer Scale Profile",
            "CF2",
            "CF3",
            "GAP Max Threshold",
            "GAP Local Noise Filter",
        }
        self.assertTrue(expected.issubset(dialog.algorithm_checks))
        self.assertTrue(dialog.algorithm_checks["HLAT"].isChecked())
        dialog.tabs.setCurrentIndex(1)
        dialog.algorithm.setCurrentText("HLAT")
        dialog.channel.setCurrentIndex(1)
        dialog.parameter_object.setCurrentText("Seg1")
        self.assertIn("Threshold", dialog.parameter_summary.text())
        dialog.table.item(0, 2).setText("72.5")
        self.assertEqual(
            dialog.state["regions"]["Array"]["algorithms"]["HLAT"]["segments"][1]["Seg1"]["Threshold"],
            72.5,
        )
        dialog.algorithm.setCurrentText("AutoSens")
        self.assertIn("No editable numeric parameters", dialog.parameter_summary.text())

    def test_sensitivity_define_segmentation_controls_round_trip(self):
        dialog = SensitivityDialog(region_names=["Array"])
        dialog.segmentation_table.selectRow(0)
        dialog.segmentation_table.cellWidget(0, 0).setChecked(True)
        self.assertEqual(
            dialog.segmentation_state["regions"]["Array"]["channels"][0]["type"],
            "Median Based Segmentation",
        )
        dialog._insert_segmentation_break("X")
        channel = dialog.segmentation_state["regions"]["Array"]["channels"][0]
        self.assertEqual(channel["breaks"][0]["axis"], "Histogram")
        dialog.segmentation_table.cellWidget(0, 6).setValue(0.61)
        self.assertAlmostEqual(channel["breaks"][0]["position"], 0.61)
        dialog._finish()
        self.assertTrue(dialog.result_segmentation_state["valid"])

    def test_sensitivity_can_upgrade_feature_vector_version(self):
        dialog = SensitivityDialog(feature_vector_version="2.0")
        self.assertTrue(dialog.upgrade_fx.isEnabled())
        dialog._upgrade_fx_version()
        self.assertEqual(dialog.feature_vector_version, "3.0A")
        self.assertFalse(dialog.upgrade_fx.isEnabled())
        dialog._finish()
        self.assertEqual(dialog.result_feature_vector_version, "3.0A")

    def test_run_status_displays_ido_test_information(self):
        recipe = {"inspection": "iDO Run", "tests": [{
            "name": "Test 1",
            "run_ido": True,
            "save_feature_vectors": True,
            "feature_vector_version": "3.0A",
        }]}
        dialog = RunStatusDialog(
            recipe,
            {"lot_id": "LOT-IDO", "wafer_id": "W1", "selected_tests": ["Test 1"]},
            auto_start=False,
        )
        self.assertGreaterEqual(dialog.test_information.height(), 90)
        self.assertEqual(dialog.test_information.item(0, 1).text(), "iDO Active")
        self.assertEqual(dialog.test_information.item(0, 2).text(), "3.0A")

    def test_overview_preview_images_are_clickable(self):
        callbacks = []
        care_area = CareAreasPreview(zoom_callback=lambda: callbacks.append("care"))
        sample_plan = SamplePlanPreview(zoom_callback=lambda: callbacks.append("sample"))
        care_area.mousePressEvent(None)
        sample_plan.mousePressEvent(None)
        self.assertEqual(callbacks, ["care", "sample"])

    def test_recipe_overview_uses_current_wafer_and_test_state(self):
        window = PumaMainWindow()
        recipe = window.recipe_store.new_recipe()
        recipe["wafer_map"] = {
            "die_pattern_defined": True,
            "die_pitch_width": 4321.5,
            "die_pitch_height": 8765.4,
            "scribe_x": 88.2,
            "scribe_y": 91.3,
            "die_count": 612,
            "reticle_qualification": True,
            "reticle_width": 3,
            "reticle_height": 2,
            "inner_die_defined": True,
        }
        test = default_test(1)
        test["name"] = "Production Test"
        test["inspection_optics"]["pixel_size"] = "SL8686"
        test["channels"][0]["use_fourier_filter"] = True
        test["care_areas"]["border"] = {"x": 3.25, "y": 4.5}
        test["sample_plan"]["inspection_type"] = "Partial Die"
        test["sensitivity"]["regions"]["Default"]["algorithms"]["HLAT"]["run"] = False
        test["sensitivity"]["regions"]["Default"]["algorithms"]["FAST"]["run"] = True
        recipe["tests"] = [test]
        window._set_current_recipe(recipe)

        self.assertTrue(window.wafermap_image_acquired)
        self.assertTrue(window.wafermap_image_button.isEnabled())
        self.assertEqual(window.die_layout_labels["Die Width"].text(), "4,321.5 um")
        self.assertEqual(window.die_layout_labels["Reticle Size"].text(), "3 x 2")
        self.assertEqual(
            window._test_overview_values("Test Properties", "Test Name")[0].text(),
            "Production Test",
        )
        self.assertEqual(
            window._test_overview_values("Inspection Optics", "Magnification\n(Pixel Size)")[0].text(),
            "SL8686",
        )
        self.assertEqual(window._test_overview_values("Fourier Filter", "1 (Left)")[0].text(), "On")
        self.assertEqual(
            window._test_overview_values("Sensitivity", "Selected Algorithms")[0].text(),
            "FAST",
        )
        self.assertIn("3.25 um x 4.50 um", window.care_area_border_label.text())
        self.assertIn("Partial Die", window.sample_plan_overview_label.text())

    def test_recipe_overview_status_icons_follow_component_validity(self):
        window = PumaMainWindow()
        recipe = window.recipe_store.new_recipe()
        self.assertEqual(window.overview_status_dots["Load/Save Status"].status, "incomplete")
        self.assertEqual(window.overview_status_dots["Alignment"].status, "incomplete")
        self.assertEqual(window.overview_status_dots["Die Layout"].status, "incomplete")
        self.assertEqual(window.overview_status_dots["Wafer Map"].status, "incomplete")

        recipe.update({
            "status": "Valid",
            "dirty": False,
            "alignment": {"sites_defined": True, "status": "Nonoptimal"},
            "wafer_map": {"die_pattern_defined": True, "die_count": 500},
        })
        window._set_current_recipe(recipe)
        self.assertEqual(window.overview_status_dots["Load/Save Status"].status, "valid")
        self.assertEqual(window.overview_status_dots["Alignment"].status, "nonoptimal")
        self.assertEqual(window.overview_status_dots["Die Layout"].status, "valid")
        self.assertEqual(window.overview_status_dots["Wafer Map"].status, "valid")

        recipe["dirty"] = True
        recipe["alignment_failed"] = True
        recipe["wafer_map"]["die_corner_adjustment_required"] = True
        window._set_current_recipe(recipe)
        self.assertEqual(window.overview_status_dots["Load/Save Status"].status, "nonoptimal")
        self.assertEqual(window.overview_status_dots["Alignment"].status, "invalid")
        self.assertEqual(window.overview_status_dots["Die Layout"].status, "invalid")
        self.assertEqual(window.overview_status_dots["Wafer Map"].status, "invalid")

    def test_recipe_overview_uses_recipe_alignment_registration_and_rdf_data(self):
        window = PumaMainWindow()
        recipe = window.recipe_store.new_recipe()
        recipe["alignment"] = {
            "sites_defined": True,
            "mode": "DF",
            "scores": {
                "180": {
                    "type": "DF",
                    "df_scores": "Align / X Reg / Y Reg",
                    "uniqueness": "81.2 / 90.0 / 92.1",
                    "sharpness": "10.2 / 9.8 / 10.0",
                    "features": "97 / 95 / 96",
                }
            },
        }
        recipe["registration_sites"] = [
            {"orientation": 180},
            {"orientation": "180 deg"},
            {"orientation": 90},
        ]
        recipe["dbb"] = {"rdf_file": "Device1.rdf"}
        window._set_current_recipe(recipe)

        self.assertEqual(window.alignment_overview_labels[(180, "Type")].text(), "DF")
        self.assertIn(
            "81.2", window.alignment_overview_labels[(180, "Uniqueness")].text()
        )
        self.assertEqual(window.alignment_overview_labels[(90, "Uniqueness")].text(), "-")
        self.assertEqual(window.registration_site_overview_labels[0].text(), "2 at 180")
        self.assertEqual(window.registration_site_overview_labels[1].text(), "1 at 90")
        self.assertEqual(window.design_file_labels["Selected RDF"].text(), "Device1.rdf")

    def test_recipe_overview_visibility_is_restored_from_preferences(self):
        with tempfile.TemporaryDirectory() as directory:
            store = RecipeStore(Path(directory) / "recipes.json")
            store.update_preferences(
                {"visible_recipe_parameters": {"Recipe Name": False}}
            )
            with patch("puma_ui.main_window.RecipeStore", return_value=store):
                window = PumaMainWindow()

            self.assertFalse(window.visible_recipe_parameters["Recipe Name"])
            self.assertTrue(window.recipe_overview_rows["Recipe Name"].isHidden())

    def test_recipe_overview_headings_open_the_corresponding_views(self):
        window = PumaMainWindow()
        with patch.object(window, "open_wafer_properties") as open_wafer_properties:
            window.overview_action_labels["Wafer Properties"].activate()
        open_wafer_properties.assert_called_once_with()
        with patch.object(window, "show_recipe_history") as show_history:
            window.overview_action_labels["History Log"].activate()
        show_history.assert_called_once_with()

    def test_inspection_properties_dialog_returns_identity_fields(self):
        dialog = InspectionPropertiesDialog({
            "inspection": "Original",
            "device": "Device1",
            "step": "Layer1",
            "recipe_type": "Normal",
            "approval": "Engineering",
        })
        dialog.name_edit.setText("Updated")
        dialog.device_edit.setText("Device2")
        dialog.step_edit.setText("Metal")
        dialog.approval_combo.setCurrentText("Production")
        dialog._accept()

        self.assertEqual(dialog.result(), QDialog.Accepted)
        self.assertEqual(dialog.result_values["inspection"], "Updated")
        self.assertEqual(dialog.result_values["device"], "Device2")
        self.assertEqual(dialog.result_values["step"], "Metal")
        self.assertEqual(dialog.result_values["approval"], "Production")

    def test_save_dialog_exposes_recipe_state_details_only_when_needed(self):
        valid = SaveInspectionDialog({"inspection": "ValidRecipe", "status": "Valid"})
        self.assertFalse(valid.more_button.isEnabled())

        incomplete = SaveInspectionDialog({
            "inspection": "IncompleteRecipe",
            "status": "Incomplete",
            "state": "Alignment sites are missing.",
        })
        self.assertTrue(incomplete.more_button.isEnabled())
        with patch("puma_ui.modules.recipe_lifecycle.dialogs.QMessageBox.information") as information:
            incomplete._show_status_details()
        self.assertIn("Alignment sites are missing", information.call_args.args[2])

    def test_save_as_overwrite_reuses_the_existing_recipe_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RecipeStore(Path(temp_dir) / "recipes.json")
            existing = store.save_recipe({
                "inspection": "TargetRecipe",
                "device": "Device1",
                "step": "Layer1",
            })
            with patch("puma_ui.main_window.RecipeStore", return_value=store):
                window = PumaMainWindow()

            dialog = type("AcceptedSaveDialog", (), {
                "recipe_values": {
                    "inspection": "TargetRecipe",
                    "device": "Device1",
                    "step": "Layer1",
                    "status": "Valid",
                }
            })()
            window._apply_save_inspection(
                dialog,
                source=store.new_recipe(),
                save_copy=True,
                overwrite_recipe_id=existing["id"],
            )

            matches = [
                recipe for recipe in store.list_recipes()
                if recipe["inspection"] == "TargetRecipe"
            ]
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0]["id"], existing["id"])

    def test_recipe_history_exposes_print_action(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RecipeStore(Path(temp_dir) / "recipes.json")
            store.save_recipe({"inspection": "HistoryRecipe"}, event="Save Inspection")
            dialog = RecipeHistoryDialog(store, "HistoryRecipe")
            print_buttons = [
                button for button in dialog.findChildren(QPushButton)
                if button.text() == "Print"
            ]
            self.assertEqual(len(print_buttons), 1)

    def test_wafer_map_state_round_trip_preserves_manual_setup(self):
        dialog = WaferMapSetupDialog()
        dialog._apply_die_values("die_pitch", 5000.0, 6000.0)
        dialog._apply_scribe_lines(99.5, 102.25)
        dialog._apply_edit_map(100, {(1, 2), (3, 4)}, (6, 7), False)
        dialog._apply_reticle_size(True, 3, 1, (8, 9))
        dialog._apply_adjust_die_corner("change", (10, 11))
        dialog.inner_die_defined = True
        dialog.inner_die_rows = 2
        dialog.inner_die_columns = 3
        state = dialog.result_state()

        restored = WaferMapSetupDialog(state=state)
        self.assertTrue(restored.die_pattern_defined)
        self.assertEqual(restored.die_value_mode, "die_pitch")
        self.assertEqual(restored.invalid_die, {(1, 2), (3, 4)})
        self.assertEqual(restored.reference_die, (8, 9))
        self.assertEqual(restored.adjust_die_corner_mode, "change")
        self.assertEqual(restored.adjusted_die_corner, (10, 11))
        self.assertTrue(restored.inner_die_defined)

    def test_edit_map_toggle_and_origin_behaviors(self):
        dialog = EditMapDialog(valid_die_count=100)
        self.assertEqual(dialog.canvas.set_die_valid((10, 10), False), -1)
        self.assertIn((10, 10), dialog.canvas.invalid_die)
        self.assertEqual(dialog.canvas.set_die_valid((10, 10), True), 1)
        self.assertNotIn((10, 10), dialog.canvas.invalid_die)
        dialog.canvas.set_origin_die((12, 13))
        self.assertEqual(dialog.canvas.origin_die, (12, 13))

    def test_edit_map_undo_and_redo_restore_die_state(self):
        dialog = EditMapDialog(valid_die_count=100)
        dialog._apply_die_action((10, 10))
        self.assertIn((10, 10), dialog.canvas.invalid_die)
        self.assertEqual(dialog.valid_die_count, 99)
        self.assertTrue(dialog.undo_button.isEnabled())
        dialog._undo()
        self.assertNotIn((10, 10), dialog.canvas.invalid_die)
        self.assertEqual(dialog.valid_die_count, 100)
        self.assertTrue(dialog.redo_button.isEnabled())
        dialog._redo()
        self.assertIn((10, 10), dialog.canvas.invalid_die)
        self.assertEqual(dialog.valid_die_count, 99)

    def test_edit_map_partial_die_changes_edge_membership_and_count(self):
        dialog = EditMapDialog(
            valid_die_count=0,
            allow_partial_die=False,
            pitch_width=5000.0,
            pitch_height=5000.0,
        )
        full_die_count = dialog.canvas.valid_die_count()
        dialog.allow_partial.setChecked(True)
        self.assertGreater(dialog.valid_die_count, full_die_count)
        self.assertTrue(dialog.canvas.allow_partial_die)

    def test_add_inside_die_preserves_dies_outside_exclusion_boundary(self):
        dialog = EditMapDialog(
            valid_die_count=0,
            allow_partial_die=True,
            pitch_width=5000.0,
            pitch_height=5000.0,
        )
        canvas = dialog.canvas
        canvas.set_edge_boundary(True, 4)
        x, y, side = canvas._wafer_geometry()
        _grid_x, _grid_y, cell_w, cell_h = canvas._grid_geometry(x, y, side)
        exclusion_radius = side / 2 - 4 * min(cell_w, cell_h)
        edge_die = next(
            (col, row)
            for col in range(canvas.columns)
            for row in range(canvas.rows)
            if canvas._die_in_wafer(col, row, x, y, side)
            and not canvas._die_inside_radius(col, row, x, y, side, exclusion_radius)
        )
        center_die = (canvas.columns // 2, canvas.rows // 2)
        canvas.invalid_die.update({edge_die, center_die})
        restored = canvas.add_inside_die()
        self.assertEqual(restored, 1)
        self.assertIn(edge_die, canvas.invalid_die)
        self.assertNotIn(center_die, canvas.invalid_die)

    def test_wafer_map_exit_warns_when_scribe_lines_are_zero(self):
        dialog = WaferMapSetupDialog()
        dialog._apply_die_values("die_pitch", 5000.0, 6000.0)
        with patch(
            "puma_ui.modules.wafer_map.dialog.QMessageBox.warning",
            return_value=QMessageBox.No,
        ) as warning:
            dialog._finish_setup()
        warning.assert_called_once()
        self.assertNotEqual(dialog.result(), QDialog.Accepted)

        with patch(
            "puma_ui.modules.wafer_map.dialog.QMessageBox.warning",
            return_value=QMessageBox.Yes,
        ):
            dialog._finish_setup()
        self.assertEqual(dialog.result(), QDialog.Accepted)

    def test_wafer_map_actions_require_defined_die_pattern(self):
        dialog = WaferMapSetupDialog()
        self.assertTrue(dialog.menu_buttons["Die Values"].isEnabled())
        self.assertTrue(dialog.menu_buttons["Scribe Lines"].isEnabled())
        self.assertTrue(dialog.menu_buttons["Edit Map"].isEnabled())
        with patch("puma_ui.modules.wafer_map.dialog.QMessageBox.information") as information:
            dialog._open_scribe_lines()
            dialog._open_edit_map()
        self.assertEqual(information.call_count, 2)
        dialog._apply_die_values("wafer_map", 5000.0, 6000.0)
        self.assertTrue(dialog.menu_buttons["Scribe Lines"].isEnabled())
        self.assertTrue(dialog.menu_buttons["Edit Map"].isEnabled())

    def test_die_pitch_geometry_stays_consistent_across_map_edit_and_reticle(self):
        pitch_width = 5100.1
        pitch_height = 16600.2
        expected_grid = die_grid_dimensions(pitch_width, pitch_height)
        self.assertEqual(expected_grid, (59, 19))

        wafer_map = WaferMapSetupDialog()
        wafer_map._apply_die_values("die_pitch", pitch_width, pitch_height)
        self.assertEqual(wafer_map.origin_die, (29, 9))
        self.assertEqual(wafer_map.reference_die, (29, 9))

        edit_map = EditMapDialog(
            valid_die_count=wafer_map.die_count,
            origin_die=wafer_map.origin_die,
            pitch_width=pitch_width,
            pitch_height=pitch_height,
        )
        self.assertEqual((edit_map.canvas.columns, edit_map.canvas.rows), expected_grid)
        _x, _y, cell_width, cell_height = edit_map.canvas._grid_geometry(0, 0, 600)
        self.assertAlmostEqual(cell_width / cell_height, pitch_width / pitch_height)

        reticle = ReticleSizeDialog(
            reference_die=wafer_map.reference_die,
            origin_die=wafer_map.origin_die,
            pitch_width=pitch_width,
            pitch_height=pitch_height,
        )
        self.assertEqual((reticle.canvas.columns, reticle.canvas.rows), expected_grid)
        self.assertEqual(reticle.reference_die_label.text(), "9, 29")

    def test_finishing_wafer_map_returns_to_recipe_overview(self):
        window = PumaMainWindow()
        window._navigate_to("wafer_map")
        page = window.workspace_pages["wafer_map"]
        page.accept()
        QApplication.processEvents()
        self.assertEqual(window._active_route_key, "setup")
        self.assertIs(window.workspace_stack.currentWidget(), window.overview_scroll)

    def test_imported_geometry_requires_die_corner_adjustment(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RecipeStore(Path(temp_dir) / "recipes.json")
            source = {"inspection": "Source", "device": "D", "step": "S"}
            store.save_component_bundle(
                "layout",
                source,
                {"Wafer Layout": {"die_pitch_width": 5000.0}},
            )
            dialog = InsertComponentDialog(
                store,
                {"inspection": "Target", "device": "D", "step": "S"},
            )
            dialog.component_combos[0].setCurrentIndex(1)
            dialog._insert()
        self.assertTrue(
            dialog.result_recipe["wafer_map"]["die_corner_adjustment_required"]
        )
        self.assertEqual(dialog.result_recipe["status"], "Incomplete")

    def test_extract_components_lists_each_test_and_disables_invalid_components(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RecipeStore(Path(temp_dir) / "recipes.json")
            recipe = store.new_recipe()
            recipe.update(
                {
                    "inspection": "Source",
                    "wafer_map": {"die_pattern_defined": True},
                    "alignment": {"sites_defined": False},
                    "tests": [default_test(1), default_test(2)],
                }
            )
            recipe["tests"][0]["status"] = "Valid"
            recipe["tests"][1]["status"] = "Incomplete"
            recipe["tests"][0]["care_areas"]["groups"].append({"name": "CA1"})
            dialog = ExtractComponentDialog(store, recipe)

        names = [box.text() for box in dialog.checks]
        self.assertIn("Test 2", names)
        self.assertIn("2-Sample Plan", names)
        alignment_row = names.index("Alignment")
        test_one_row = names.index("Test 1")
        test_two_row = names.index("Test 2")
        self.assertFalse(dialog.checks[alignment_row].isEnabled())
        self.assertTrue(dialog.checks[test_one_row].isEnabled())
        self.assertFalse(dialog.checks[test_two_row].isEnabled())
        self.assertEqual(dialog.filename_edit.maxLength(), 255)

    def test_extract_components_opens_for_saved_recipe_with_any_valid_component(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RecipeStore(Path(temp_dir) / "recipes.json")
            recipe = store.new_recipe()
            recipe.update(
                {
                    "inspection": "Partial",
                    "status": "Incomplete",
                    "wafer_map": {"die_pattern_defined": True},
                    "dirty": False,
                }
            )
            recipe = store.save_recipe(recipe)
            with patch("puma_ui.main_window.RecipeStore", return_value=store):
                window = PumaMainWindow()
            window._set_current_recipe(recipe)
            with patch(
                "puma_ui.main_window.ExtractComponentDialog.exec",
                return_value=QDialog.Rejected,
            ) as execute:
                window.extract_components()
        execute.assert_called_once()

    def test_insert_components_add_test_creates_rows_and_applies_selected_data(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RecipeStore(Path(temp_dir) / "recipes.json")
            source = {"inspection": "Source", "device": "D", "step": "S"}
            store.save_component_bundle(
                "test-components",
                source,
                {
                    "Test 2": {"name": "Imported Test", "status": "Valid"},
                    "2-Care Area": {"groups": [{"name": "Imported CA"}]},
                },
            )
            dialog = InsertComponentDialog(
                store,
                {"inspection": "Target", "device": "D", "step": "S", "tests": []},
            )
            dialog._add_test()
            names = [dialog.table.item(row, 0).text() for row in range(dialog.table.rowCount())]
            self.assertIn("Test 2", names)
            self.assertIn("2-Care Area", names)
            for component_name in ("Test 2", "2-Care Area"):
                row = names.index(component_name)
                dialog.component_combos[row].setCurrentIndex(1)
            dialog._insert()
            self.assertNotEqual(dialog.result(), QDialog.Accepted)
            dialog._close()

        self.assertEqual(dialog.result(), QDialog.Accepted)
        self.assertEqual(dialog.result_recipe["tests"][1]["name"], "Imported Test")
        self.assertEqual(
            dialog.result_recipe["tests"][1]["care_areas"]["groups"][0]["name"],
            "Imported CA",
        )

    def test_derivative_recipe_cannot_run_before_reference_reselection(self):
        window = PumaMainWindow()
        source = window.recipe_store.new_recipe()
        source.update(
            {
                "status": "Valid",
                "alignment": {"sites_defined": True, "status": "Valid"},
                "wafer_map": {"die_pattern_defined": True},
                "tests": [default_test(1)],
                "test_setup_valid": True,
            }
        )
        source["tests"][0]["status"] = "Valid"
        derivative = window.recipe_store.duplicate_recipe(
            source, "Derivative", derivative=True
        )
        window._set_current_recipe(derivative)

        self.assertTrue(window.setup_run_button.isEnabled())
        self.assertFalse(window._run_setup_ready)
        self.assertEqual(window.overview_status_dots["Alignment"].status, "incomplete")

    def test_reticle_qualification_requires_reference_selection(self):
        dialog = ReticleSizeDialog(reticle_qualification=False)
        dialog.reticle_qualification.setChecked(True)
        self.assertFalse(dialog.reference_selected)
        dialog.set_reference_die((4, 5))
        dialog._finish()
        self.assertEqual(dialog.result(), QDialog.Accepted)
        self.assertEqual(dialog.canvas.reference_die, (4, 5))

    def test_reticle_size_is_limited_by_available_die_axes(self):
        dialog = ReticleSizeDialog(max_width=12, max_height=7)
        self.assertEqual(dialog.reticle_width.maximum(), 12)
        self.assertEqual(dialog.reticle_height.maximum(), 7)
        dialog.reticle_width.setValue(20)
        dialog.reticle_height.setValue(20)
        self.assertEqual(dialog.reticle_width.value(), 12)
        self.assertEqual(dialog.reticle_height.value(), 7)

    def test_wafer_property_sliders_update_values_and_gating(self):
        dialog = WaferPropertiesDialog()
        dialog._set_laser_factor(0.5)
        self.assertEqual(dialog.laser_power_factor.text(), "0.50000")
        dialog.dark_level_slider.setValue(75)
        self.assertEqual(dialog.dark_level_value.text(), "Darkest")
        dialog.laser_power_sensitive.setChecked(False)
        self.assertFalse(dialog.laser_power_slider.isEnabled())
        dialog.dark_wafer_auto_focus.setChecked(False)
        self.assertFalse(dialog.dark_level_slider.isEnabled())

    def test_layer_database_add_modify_delete_and_power_limit(self):
        database = EditLayerDatabaseDialog()
        self.assertTrue(database._insert_layer({
            "name": "Polymer", "laser_power_limit": 0.5,
        }))
        row = next(index for index, layer in enumerate(database.layers) if layer["name"] == "Polymer")
        self.assertTrue(database._insert_layer({
            "name": "Polymer Thin", "laser_power_limit": 0.25,
        }, row))
        with patch("puma_ui.modules.wafer_properties.dialogs.QMessageBox.warning"):
            self.assertFalse(database._insert_layer({
                "name": "Polymer Thin", "laser_power_limit": 0.3,
            }))
        database._finish()
        self.assertIn("Polymer Thin", [layer["name"] for layer in database.result_layers])

        properties = WaferPropertiesDialog({
            "laser_power_factor": "0.50000",
            "layer": "9000 Dose Limit [ 0.24200 ]",
        })
        self.assertEqual(properties.laser_power_factor.text(), "0.24200")
        properties._reload_layers(database.result_layers, "Polymer Thin")
        self.assertEqual(properties.layer_combo.currentData()["name"], "Polymer Thin")

    def test_wafer_property_changes_require_confirmation(self):
        orientation = WaferPropertiesDialog()
        orientation.orientation_combo.setCurrentText("Right (90 deg.)")
        with patch(
            "puma_ui.modules.wafer_properties.dialogs.QMessageBox.question",
            return_value=QMessageBox.No,
        ):
            orientation._accept()
        self.assertIsNone(orientation.result_properties)
        with patch(
            "puma_ui.modules.wafer_properties.dialogs.QMessageBox.question",
            return_value=QMessageBox.Yes,
        ):
            orientation._accept()
        self.assertTrue(orientation.result_properties["orientation_changed"])

        wafer_type = WaferPropertiesDialog()
        wafer_type.type_combo.setCurrentText("Blank")
        with patch(
            "puma_ui.modules.wafer_properties.dialogs.QMessageBox.warning",
            return_value=QMessageBox.Cancel,
        ):
            wafer_type._accept()
        self.assertIsNone(wafer_type.result_properties)

    def test_orientation_rotation_transforms_care_area_geometry(self):
        rotated = PumaMainWindow._rotate_unit_rect([0.1, 0.2, 0.3, 0.4, "CA"], 1)
        self.assertEqual(rotated, [0.4, 0.1, 0.4, 0.3, "CA"])
        recipe = {
            "wafer_properties": {"orientation": "Right (90 deg.)"},
            "wafer_map": {"origin_die": [10, 20], "invalid_die": [[11, 20]]},
            "tests": [{
                "status": "Valid", "fourier_trained": True, "light_trained": True,
                "care_areas": {"groups": [{"areas": [[0.1, 0.2, 0.3, 0.4]]}]},
            }],
        }
        PumaMainWindow._apply_wafer_property_dependencies(
            PumaMainWindow,
            recipe,
            orientation_changed=True,
            type_changed=False,
            old_orientation="Down (180 deg.)",
        )
        self.assertFalse(recipe["tests"][0]["fourier_trained"])
        self.assertFalse(recipe["tests"][0]["light_trained"])
        for actual, expected in zip(
            recipe["tests"][0]["care_areas"]["groups"][0]["areas"][0],
            [0.2, 0.6, 0.4, 0.3],
        ):
            self.assertAlmostEqual(actual, expected)
        self.assertEqual(recipe["wafer_map"]["geometry_rotation_degrees"], 270)

    def test_geometry_changes_detach_attached_defect_data(self):
        recipe = {"defect_data": {"name": "Lot_1"}}
        unchanged = {"die_pitch_width": 5000.0, "origin_die": [10, 10]}
        self.assertFalse(PumaMainWindow._detach_defect_data_for_geometry_change(
            recipe, unchanged, dict(unchanged),
        ))
        self.assertTrue(recipe["defect_data"])

        changed = {"die_pitch_width": 5100.0, "origin_die": [10, 10]}
        self.assertTrue(PumaMainWindow._detach_defect_data_for_geometry_change(
            recipe, unchanged, changed,
        ))
        self.assertEqual(recipe["defect_data"], {})

    def test_advanced_review_optics_named_settings_and_apply(self):
        dialog = AdvancedOpticsDialog()
        dialog.pixel_size.setCurrentText("SL8687")
        dialog.focus_offset.setValue(1.234)
        dialog.named_settings.setCurrentText("Review High Mag")
        dialog._save_named_setting()
        dialog.pixel_size.setCurrentText("SL8685")
        dialog.focus_offset.setValue(0.0)
        dialog._load_named_setting()
        self.assertEqual(dialog.pixel_size.currentText(), "SL8687")
        self.assertAlmostEqual(dialog.focus_offset.value(), 1.234)
        dialog._accept()
        self.assertEqual(dialog.result(), QDialog.Accepted)
        self.assertEqual(dialog.result_settings["named_setting"], "Review High Mag")
        self.assertIn("Review High Mag", dialog.result_settings["profiles"])

    def test_image_display_menus_tools_stage_and_zoom_are_functional(self):
        dialog = ImageDisplayWindow()
        menu_text = [
            action.text()
            for menu_action in dialog.window_menu_bar.actions()
            for action in menu_action.menu().actions()
        ]
        self.assertFalse(any("placeholder" in text.lower() for text in menu_text))
        dialog._move_stage(1, -1)
        self.assertNotEqual(dialog.x_edit.text(), "0.000")
        dialog._reset_stage()
        self.assertEqual(dialog.x_edit.text(), "0.000")
        self.assertEqual(dialog.y_edit.text(), "0.000")
        dialog._set_zoom(200)
        self.assertEqual(dialog.viewport.zoom_percent, 200)
        before = dialog.current_image.count()
        dialog._acquire_image()
        self.assertEqual(dialog.current_image.count(), before + 3)
        dialog.custom_step_radio.setChecked(True)
        dialog.custom_motion_step.setValue(12.5)
        dialog._reset_stage()
        dialog._move_stage(1, 0)
        self.assertEqual(dialog.x_edit.text(), "12.500")
        self.assertTrue(dialog.use_for_alignment_button.isEnabled())
        dialog._use_for_alignment()
        self.assertTrue(dialog.use_current_optics_for_alignment)
        self.assertEqual(
            [dialog.optics_source.itemText(index) for index in range(dialog.optics_source.count())],
            ["Current Machine", "Alignment", "Test 1 Optics", "Test 2 Optics", "Test 3 Optics"],
        )
        dialog.optics_source.setCurrentText("Alignment")
        dialog._load_optics_source()
        self.assertEqual(dialog.loaded_optics_source, "Alignment")
        self.assertEqual(dialog.optics_controls["Pixel Size"].currentText(), "SL8686")
        self.assertEqual(dialog.optics_focus.text(), "0.125 um")
        self.assertEqual(dialog.optics_table.item(2, 3).text(), "2.30")

    def test_alignment_workspace_embeds_image_display_as_right_screen(self):
        dialog = AlignmentMenuDialog(alignment_state={"mode": "DF"})

        self.assertTrue(dialog.image_display.embedded)
        self.assertIs(dialog.image_display.parent(), dialog.workspace_splitter)
        self.assertEqual(dialog.image_display.alignment_mode, "DF")
        self.assertFalse(dialog.image_display.bf_magnification_panel.isVisibleTo(dialog.image_display))

        with patch("puma_ui.modules.wafer_alignment.dialogs.ImageDisplayWindow.exec") as execute:
            dialog._open_image_display()

        execute.assert_not_called()
        self.assertIn("right screen", dialog.status_label.text())

    def test_bf_embedded_image_display_switches_low_and_high_magnification(self):
        dialog = ImageDisplayWindow(embedded=True, alignment_mode="BF")

        self.assertEqual(dialog.current_image.currentText(), "Sim Cross Mark 3 (BF)")
        self.assertTrue(dialog.low_mag_button.isChecked())
        self.assertFalse(dialog.high_mag_button.isChecked())
        self.assertEqual(dialog.viewport.bf_magnification, "Low Mag")

        dialog.high_mag_button.click()

        self.assertFalse(dialog.low_mag_button.isChecked())
        self.assertTrue(dialog.high_mag_button.isChecked())
        self.assertEqual(dialog.viewport.bf_magnification, "High Mag")
        self.assertIn("High Mag", dialog.status_label.text())

        dialog.set_alignment_mode("DF")
        self.assertEqual(dialog.current_image.currentText(), "Sim Cross Mark 1 (DF)")
        self.assertTrue(dialog.bf_magnification_panel.isHidden())

    def test_bf_site_selection_does_not_reuse_df_image_labels(self):
        dialog = SelectAlignmentSitesDialog(
            "BF",
            existing_sites=[[-1800.0, 1200.0], [-800.0, 1200.0]],
            existing_images=["Sim Cross Mark 1 (DF)", "Sim Cross Mark 2 (DF)"],
            bf_dual_magnification=True,
        )

        self.assertTrue(dialog.bf_dual_magnification)
        self.assertTrue(all("(BF" in image for image in dialog.site_images))
        self.assertIn("(BF", dialog.current_simulated_image)

    def test_setup_review_requires_attached_data_and_aligned_wafer(self):
        unavailable = CareAreasDialog(defect_data={}, wafer_aligned=True)
        self.assertFalse(unavailable.review_button.isEnabled())
        not_aligned = CareAreasDialog(
            defect_data={"name": "Lot", "defects": [{"id": 1, "x": 0.5, "y": 0.5}]},
            wafer_aligned=False,
        )
        self.assertFalse(not_aligned.review_button.isEnabled())
        ready = CareAreasDialog(
            defect_data={"name": "Lot", "defects": [{"id": 1, "x": 0.5, "y": 0.5}]},
            wafer_aligned=True,
        )
        self.assertTrue(ready.review_button.isEnabled())

    def test_setup_review_hot_spots_use_only_marked_defects(self):
        dialog = CareAreasDialog(state={
            "setup_review_defects": [
                {"id": 1, "x": 0.25, "y": 0.25, "marked": True},
                {"id": 2, "x": 0.75, "y": 0.75, "marked": False},
            ],
        })
        dialog._hot_spots()
        group = dialog.state["groups"][-1]
        self.assertEqual(group["kind"], "Derived")
        self.assertEqual(len(group["areas"]), 1)
        self.assertEqual(group["areas"][0][-1], 1)

    def test_apply_offset_requires_mark_before_done_and_uses_microns(self):
        groups = [{"name": "CA", "areas": [[0.1, 0.2, 0.3, 0.2]]}]
        dialog = ApplyOffsetDialog(groups, [0], [5000.0, 10000.0])
        self.assertFalse(dialog.done_button.isEnabled())
        self.assertEqual(dialog.offset_x.suffix(), " um")
        dialog.offset_x.setValue(250.0)
        dialog.offset_y.setValue(-1000.0)
        dialog._mark_site()
        self.assertTrue(dialog.done_button.isEnabled())
        self.assertAlmostEqual(dialog.result_groups[0]["areas"][0][0], 0.15)
        self.assertAlmostEqual(dialog.result_groups[0]["areas"][0][1], 0.1)
        dialog._undo()
        self.assertFalse(dialog.done_button.isEnabled())
        self.assertTrue(dialog.anchor.isEnabled())

    def test_noise_box_editor_displays_microns_and_normalizes_on_finish(self):
        dialog = NoiseBoxDialog(
            [0.1, 0.2, 0.2, 0.1],
            group_names=["Array"],
            selected_group="Array",
            die_size_um=[5000.0, 10000.0],
        )
        self.assertEqual(dialog.controls[0].value(), 500.0)
        self.assertEqual(dialog.controls[1].value(), 2000.0)
        dialog.controls[2].setValue(1000.0)
        dialog.controls[3].setValue(1500.0)
        dialog._finish()
        self.assertEqual(dialog.result(), QDialog.Accepted)
        self.assertEqual(dialog.result_box, [0.1, 0.2, 0.2, 0.15])

    def test_light_training_finish_requires_a_completed_training(self):
        dialog = LightTrainingDialog()
        with patch(
            "puma_ui.modules.inspection_tests.light_training.QMessageBox.warning"
        ) as warning:
            dialog._complete_training_step()
        warning.assert_called_once()
        self.assertIsNone(dialog.result_state)
        dialog.state["trained"] = True
        dialog._complete_training_step()
        self.assertTrue(dialog.training_step_finished)
        self.assertIsNone(dialog.result_state)
        dialog._end()
        self.assertEqual(dialog.result(), QDialog.Accepted)

    def test_light_training_does_not_require_optional_fourier_training(self):
        test = default_test(1)
        test["care_areas"]["groups"].append(
            {
                "name": "CA 1",
                "kind": "Care Area",
                "enabled": True,
                "areas": [[0.0, 0.0, 1.0, 1.0]],
            }
        )
        test["fourier_trained"] = False
        setup = TestsSetupDialog([test])

        with (
            patch("puma_ui.modules.inspection_tests.dialog.LightTrainingDialog") as training,
            patch("puma_ui.modules.inspection_tests.dialog.QMessageBox.warning") as warning,
        ):
            training.return_value.exec.return_value = QDialog.Rejected
            setup._light_training()

        warning.assert_not_called()
        training.assert_called_once()

    def test_light_training_requires_fourier_only_for_an_enabled_selected_channel(self):
        test = default_test(1)
        test["care_areas"]["groups"].append(
            {
                "name": "CA 1",
                "kind": "Care Area",
                "enabled": True,
                "areas": [[0.0, 0.0, 1.0, 1.0]],
            }
        )
        test["channels"][0]["use_fourier_filter"] = True
        test["fourier_trained"] = False
        setup = TestsSetupDialog([test])

        with (
            patch("puma_ui.modules.inspection_tests.dialog.LightTrainingDialog") as training,
            patch("puma_ui.modules.inspection_tests.dialog.QMessageBox.warning") as warning,
        ):
            setup._light_training()
        warning.assert_called_once()
        training.assert_not_called()

        setup.tests[0]["channels"][0]["enabled"] = False
        with (
            patch("puma_ui.modules.inspection_tests.dialog.LightTrainingDialog") as training,
            patch("puma_ui.modules.inspection_tests.dialog.QMessageBox.warning") as warning,
        ):
            training.return_value.exec.return_value = QDialog.Rejected
            setup._light_training()
        warning.assert_not_called()
        training.assert_called_once()

    def test_use_fourier_filter_can_be_selected_before_training(self):
        setup = TestsSetupDialog([default_test(1)])
        control = setup.channel_table.cellWidget(5, 1)
        self.assertTrue(control.isEnabled())
        setup.tests[0]["light_trained"] = True
        control.setChecked(True)
        self.assertTrue(setup.tests[0]["channels"][0]["use_fourier_filter"])
        self.assertFalse(setup.tests[0]["light_trained"])

    def test_light_training_active_region_entry_is_never_visually_locked(self):
        dialog = LightTrainingDialog(focus_mode="Median Die")
        self.assertTrue(dialog.active_region_button.isEnabled())
        with patch(
            "puma_ui.modules.inspection_tests.light_training.ActiveRegionsDialog"
        ) as active_regions:
            active_regions.return_value.exec.return_value = QDialog.Rejected
            dialog.active_region_button.click()
        active_regions.assert_called_once()

    def test_sample_plan_screen_buttons_change_state_and_report_actions(self):
        dialog = SamplePlanDialog()
        self.assertTrue(all(button.isEnabled() for button in dialog.command_buttons.values()))

        secondary = next(
            button for button in dialog.mode_buttons
            if button.text() == "Secondary Threshold"
        )
        secondary.click()
        dialog.command_buttons["Entire Wafer"].click()
        selected_count = len(dialog.state["overrides"])
        self.assertGreater(selected_count, 600)
        self.assertIn("Entire Wafer: applied Secondary Threshold", dialog.status.text())

        dialog.undo_button.click()
        self.assertEqual(dialog.state["overrides"], {})
        dialog.redo_button.click()
        self.assertEqual(len(dialog.state["overrides"]), selected_count)

        do_not_inspect = next(
            button for button in dialog.mode_buttons
            if button.text() == "Do Not Inspect"
        )
        do_not_inspect.click()
        self.assertFalse(dialog.edge_enabled.isChecked())
        dialog.command_buttons["Select Outside"].click()
        self.assertTrue(dialog.edge_enabled.isChecked())
        self.assertIn("Outside Die: applied Do Not Inspect", dialog.status.text())
        self.assertTrue(any(value == "Do Not Inspect" for value in dialog.state["overrides"].values()))

        secondary.click()
        dialog.command_buttons["Select Edge"].click()
        self.assertIn("Edge Die: applied Secondary Threshold", dialog.status.text())
        dialog.command_buttons["Select Inside"].click()
        self.assertIn("Inside Die: applied Secondary Threshold", dialog.status.text())

        do_not_report = next(
            button for button in dialog.mode_buttons
            if button.text() == "Do Not Report"
        )
        do_not_report.click()
        dialog.apply_edge_button.click()
        self.assertIn("Edge Exclusion: applied Do Not Inspect", dialog.status.text())
        self.assertEqual(dialog.state["selection_mode"], "Do Not Report")

        dialog.grid_shift_right.click()
        self.assertEqual(dialog.grid_pitch.value(), 1)
        self.assertEqual(dialog.state["grid_offset"], 0)
        self.assertIn("cannot shift while Grid Pitch is 1", dialog.status.text())

        dialog.grid_pitch.setValue(3)
        dialog.grid_shift_right.click()
        self.assertEqual(dialog.state["grid_offset"], 1)
        self.assertIn("shifted right; phase 2 of 3", dialog.status.text())
        dialog.grid_shift_left.click()
        self.assertEqual(dialog.state["grid_offset"], 0)
        self.assertIn("shifted left; phase 1 of 3", dialog.status.text())

        with patch("puma_ui.modules.inspection_tests.sample_plan.QMessageBox.information"):
            dialog.command_buttons["Store as Master Plan"].click()
        dialog.coverage.setCurrentText("50%")
        dialog.command_buttons["Load Master Plan"].click()
        self.assertEqual(dialog.coverage.currentText(), "100%")

        with patch(
            "puma_ui.modules.inspection_tests.sample_plan.RowPatternDialog"
        ) as row_pattern:
            row_pattern.return_value.exec.return_value = QDialog.Rejected
            dialog.command_buttons["Row Pattern"].click()
        row_pattern.assert_called_once()

        with patch(
            "puma_ui.modules.inspection_tests.sample_plan.MasterSamplePlanDialog"
        ) as more_dialog:
            more_dialog.return_value.exec.return_value = QDialog.Rejected
            dialog.command_buttons["More..."].click()
        more_dialog.assert_called_once()

        dialog._finish()
        self.assertEqual(dialog.result(), QDialog.Accepted)
        self.assertIsNotNone(dialog.result_state)

    def test_segmentation_image_grab_and_break_controls_follow_manual_gates(self):
        dialog = SegmentationDialog(wafer_ready=False)
        self.assertFalse(dialog.image_grab_button.isEnabled())
        self.assertFalse(dialog.sdi_button.isEnabled())

        setup = SegmentationSetupDialog({}, [{"name": "Logic"}])
        setup.segmentation_type.setCurrentText("Median Based Segmentation")
        with patch(
            "puma_ui.modules.inspection_tests.segmentation.QMessageBox.warning"
        ) as warning:
            setup._add_break("X")
        warning.assert_called_once()
        self.assertEqual(setup._current()["breaks"], [])
        setup._add_break("Histogram")
        self.assertEqual(len(setup._current()["breaks"]), 1)
        setup.group_id.setValue(2)
        self.assertEqual(setup._current()["breaks"][0]["group"], 2)
        with patch(
            "puma_ui.modules.inspection_tests.segmentation.QMessageBox.warning"
        ) as warning:
            setup._finish()
        warning.assert_called_once()
        self.assertNotEqual(setup.result(), QDialog.Accepted)

    def test_sdi_requires_measurement_and_reports_detected_pattern(self):
        dialog = SingleDieInspectionDialog({}, [{"name": "Array"}])
        dialog.image_channel.setCurrentIndex(2)
        dialog.magnifier.setChecked(True)
        dialog.magnifier_grid.setChecked(True)
        dialog.image_mode.setCurrentText("Processed Image")
        dialog.zoom.setValue(150)
        self.assertEqual(dialog.preview.channel, 3)
        self.assertTrue(dialog.preview.magnifier_grid)
        self.assertEqual(dialog.preview.image_mode, "Processed Image")
        self.assertEqual(dialog.preview.zoom, 1.5)
        dialog.table.cellWidget(0, 1).setChecked(True)
        with patch(
            "puma_ui.modules.inspection_tests.segmentation.QMessageBox.warning"
        ) as warning:
            dialog._finish()
        warning.assert_called_once()
        dialog.table.cellWidget(0, 2).setCurrentText("Force Vertical")
        dialog._measure()
        record = dialog.result_state["groups"]["Array"]
        self.assertTrue(dialog.result_state["measured"])
        self.assertEqual(record["detected_pattern_type"], "Vertical")
        self.assertGreaterEqual(record["feature_score"], 75)
        dialog._finish()
        self.assertEqual(dialog.result(), QDialog.Accepted)

    def test_sdi_sensitivity_and_test_summary_enable_are_independent(self):
        sensitivity = SDISensitivityDialog({}, ["Array"])
        sensitivity.table.cellWidget(0, 1).setChecked(True)
        sensitivity.table.cellWidget(0, 2).setChecked(True)
        sensitivity._finish()
        self.assertTrue(sensitivity.result_state["Array"]["run_sdi"])
        self.assertTrue(sensitivity.result_state["Array"]["run_cf_sdi"])

        test = default_test(1)
        test["care_areas"]["groups"] = [
            {"name": "Array", "kind": "CA", "enabled": True, "areas": [[0.1, 0.1, 0.5, 0.5]]}
        ]
        test["fourier_trained"] = True
        test["light_trained"] = True
        setup = TestsSetupDialog(
            [test], wafer_loaded=True, wafer_aligned=True, wafer_geometry_defined=True
        )
        result_state = {
            "sites": [],
            "regions": {},
            "valid": False,
            "sdi": {
                "groups": {"Array": {"enabled": True, "feature_score": 82.0}},
                "measured": True,
                "image_box": [0.2, 0.2, 0.35, 0.35],
            },
        }
        with patch(
            "puma_ui.modules.inspection_tests.dialog.SegmentationDialog"
        ) as dialog_type:
            dialog_type.return_value.exec.return_value = QDialog.Accepted
            dialog_type.return_value.result_state = result_state
            setup._segmentation()
        self.assertFalse(setup.tests[0]["run_single_die"])

    def test_care_area_panes_are_resizable_and_require_a_ready_wafer(self):
        care = CareAreasDialog()
        self.assertEqual(care.panes.count(), 2)
        self.assertEqual(care.panes.orientation(), Qt.Horizontal)
        self.assertEqual(care.right_panes.count(), 2)
        self.assertEqual(care.right_panes.orientation(), Qt.Vertical)
        self.assertEqual(care.group_tabs.count(), 2)
        self.assertEqual(care.group_buttons["CA"].text(), "CA")
        self.assertEqual(care.more_button.text(), "More...")
        self.assertEqual(care.zoom_value.currentText(), "100%")
        self.assertTrue(care.show_defects_action.isChecked())
        care.group_buttons["CA"].click()
        self.assertEqual(care.state["groups"][0]["kind"], "CA")
        self.assertTrue(care.canvas.drawing_enabled)
        care.zoom_value.setCurrentText("150%")
        self.assertEqual(care.zoom.value(), 150)
        self.assertEqual(care.canvas.zoom, 1.5)
        self.assertFalse(care.macro_view_action.isEnabled())
        care.acquire_macro_action.trigger()
        self.assertTrue(care.macro_view_action.isEnabled())
        self.assertTrue(care.canvas.image_acquired)
        care.show_defects_action.trigger()
        self.assertFalse(care.canvas.show_defects)

        tests = TestsSetupDialog(
            [default_test(1)],
            wafer_loaded=False,
            wafer_aligned=False,
            wafer_geometry_defined=True,
        )
        self.assertTrue(tests.module_buttons["Care Areas"].isEnabled())
        with patch("puma_ui.modules.inspection_tests.dialog.QMessageBox.warning") as warning:
            tests._care_areas()
        warning.assert_called_once()

    def test_nanopoint_import_uses_marked_defects_and_real_image_metadata(self):
        defects = [
            {
                "id": 17,
                "x": 0.21,
                "y": -0.14,
                "class_code": 42,
                "marked": True,
                "image_path": "patch-17.png",
                "sem_path": "sem-17.png",
            },
            {"id": 18, "x": 0.32, "y": 0.41, "class_code": 7, "marked": True},
            {"id": 19, "x": 0.9, "y": 0.9, "marked": False},
        ]
        dialog = NanoPointImageTemplatesDialog(
            {"marked_defects": defects},
            care_area_names=["Entire Die"],
            defect_data={"name": "Attached Lot", "defects": defects},
            wafer_loaded=True,
            wafer_aligned=True,
            light_trained=True,
        )

        self.assertEqual(dialog.panes.count(), 2)
        dialog._import_marked()

        self.assertEqual(len(dialog.state["templates"]), 2)
        first = dialog.state["templates"][0]
        self.assertEqual(first["source_defect_id"], 17)
        self.assertEqual(first["class_code"], 42)
        self.assertEqual(first["location"], [0.21, -0.14])
        self.assertTrue(first["has_patch_images"])
        self.assertEqual(first["sem"]["path"], "sem-17.png")
        self.assertEqual(dialog.panes.count(), 2)
        self.assertEqual(dialog.box_target.currentText(), "Care Area")
        self.assertEqual(
            [action.text() for action in dialog.grab_button.menu().actions()],
            ["Grab Missing Images", "Re-Grab all Images"],
        )
        dialog.magnifier_button.click()
        dialog.magnifier_grid_button.click()
        self.assertTrue(dialog.state["magnifier"])
        self.assertTrue(dialog.state["magnifier_grid"])
        dialog.table.selectRow(0)
        dialog._draw_ca()
        self.assertEqual(dialog.preview.editing_box, "care_area")
        dialog._box_changed("care_area", [0.2, 0.2, 0.3, 0.4])
        self.assertEqual(dialog.state["templates"][0]["care_area"], [0.2, 0.2, 0.3, 0.4])

    def test_segmentation_requires_fourier_only_when_the_test_uses_it(self):
        test = default_test(1)
        test["care_areas"]["groups"].append(
            {
                "name": "CA 1",
                "kind": "CA",
                "enabled": True,
                "areas": [[0.1, 0.1, 0.8, 0.8]],
            }
        )
        test["light_trained"] = True
        test["fourier_trained"] = False
        setup = TestsSetupDialog([test])
        with (
            patch("puma_ui.modules.inspection_tests.dialog.SegmentationDialog") as segmentation,
            patch("puma_ui.modules.inspection_tests.dialog.QMessageBox.warning") as warning,
        ):
            segmentation.return_value.exec.return_value = QDialog.Rejected
            setup._segmentation()
        warning.assert_not_called()
        segmentation.assert_called_once()

        setup.tests[0]["channels"][0]["use_fourier_filter"] = True
        with (
            patch("puma_ui.modules.inspection_tests.dialog.SegmentationDialog") as segmentation,
            patch("puma_ui.modules.inspection_tests.dialog.QMessageBox.warning") as warning,
        ):
            setup._segmentation()
        warning.assert_called_once()
        segmentation.assert_not_called()

    def test_nanopoint_controls_require_light_training_and_ready_wafer(self):
        test = default_test(1)
        dialog = TestsSetupDialog(
            [test], wafer_loaded=True, wafer_aligned=True, wafer_geometry_defined=True
        )
        self.assertTrue(dialog.module_buttons["NP Image\nTemplates"].isEnabled())
        with patch("puma_ui.modules.inspection_tests.dialog.QMessageBox.warning") as warning:
            dialog._nanopoint_templates()
        warning.assert_called_once()

        dialog.tests[0]["light_trained"] = True
        dialog._refresh_module_buttons()
        self.assertTrue(dialog.module_buttons["NP Image\nTemplates"].isEnabled())

    def test_nanopoint_grab_images_blocks_unprepared_stage(self):
        dialog = NanoPointImageTemplatesDialog(
            {
                "defect_source": "lot.json",
                "templates": [{"name": "Target", "search": True}],
            }
        )
        with patch(
            "puma_ui.modules.inspection_tests.nanopoint.QMessageBox.warning"
        ) as warning:
            dialog._grab_images()
        warning.assert_called_once()
        self.assertFalse(dialog.state["images_grabbed"])

    def test_np_image_care_area_disallows_manual_geometry_operations(self):
        dialog = CareAreasDialog(state={
            "groups": [{
                "name": "NPI CAG 1",
                "kind": "NP Image Care Area",
                "areas": [[0.1, 0.1, 0.2, 0.2]],
                "registered": True,
                "verified": True,
                "status": "OK",
            }]
        })
        dialog.active_group = 0
        before = dialog.state["groups"][0].copy()
        with patch(
            "puma_ui.modules.inspection_tests.care_areas.QMessageBox.information"
        ) as information:
            dialog._register_group()
            dialog._verify_group()
            dialog._apply_offset()
        self.assertEqual(information.call_count, 3)
        self.assertEqual(dialog.state["groups"][0], before)

    def test_np_image_care_area_invalidates_for_optics_and_deletes_for_rotation(self):
        test = default_test(1)
        test["care_areas"]["groups"] = [{
            "name": "NPI CAG 1",
            "kind": "NP Image Care Area",
            "areas": [[0.1, 0.1, 0.2, 0.2]],
            "registered": True,
            "verified": True,
            "status": "OK",
        }]
        dialog = TestsSetupDialog([test])

        dialog._set_value(0, "speed", "Low")
        group = dialog.tests[0]["care_areas"]["groups"][0]
        self.assertTrue(group["requires_rescan"])
        self.assertIn("Invalid", group["status"])

        dialog._invalidate_np_image_care_areas(0, delete=True)
        self.assertEqual(dialog.tests[0]["care_areas"]["groups"], [])

    def test_npca_import_reads_real_inspection_steps_and_cag_names(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "device-npca.json"
            path.write_text(
                '{"inspection_steps":{"Metal 1":[{"name":"Logic"},'
                '{"name":"Memory"}],"Via 1":["Array"]}}',
                encoding="utf-8",
            )
            metadata = care_area_file_metadata(str(path))
            self.assertEqual(metadata["Metal 1"], ["Logic", "Memory"])
            self.assertEqual(metadata["Via 1"], ["Array"])

            dialog = CareAreaImportDialog("Random")
            dialog.import_type.setCurrentText("NP Design Care Area")
            dialog.path.setText(str(path))
            dialog.groups_by_step = metadata
            dialog.step.setText("Metal 1")
            dialog._populate_groups("Metal 1")

            self.assertEqual(dialog.windowTitle(), "NP Design Care Area Selection")
            self.assertEqual(dialog.browse_button.text(), "Open NPCA...")
            self.assertEqual(dialog.groups.rowCount(), 2)
            self.assertEqual(dialog.selected_groups(), ["Logic"])

    def test_imported_care_area_registration_requires_a_marked_corner(self):
        dialog = RegisterCareAreaGroupDialog()
        self.assertFalse(dialog.done_button.isEnabled())
        with patch(
            "puma_ui.modules.inspection_tests.care_areas.QMessageBox.warning"
        ) as warning:
            dialog._finish()
        warning.assert_called_once()
        self.assertIsNone(dialog.result_registration)

        dialog.site_x.setValue(0.22)
        dialog.site_y.setValue(0.31)
        dialog._mark()
        dialog._finish()
        self.assertEqual(dialog.result(), QDialog.Accepted)
        self.assertEqual(dialog.result_registration["site"], [0.22, 0.31])

    def test_copy_fill_preserves_embedded_dont_care_area_semantics(self):
        dialog = CareAreasDialog()
        dialog._new_group("CA")
        dialog.start_dca.setChecked(True)
        dialog._area_added([0.1, 0.1, 0.1, 0.1])
        fill = CopyFillDialog()
        fill.rows.setValue(2)
        fill.columns.setValue(2)

        with patch.object(fill, "exec", return_value=QDialog.Accepted), patch(
            "puma_ui.modules.inspection_tests.care_areas.CopyFillDialog", return_value=fill
        ):
            dialog._fill()

        areas = dialog.state["groups"][0]["areas"]
        self.assertEqual(len(areas), 4)
        self.assertTrue(all(area[4] == "DCA" for area in areas))

    def test_care_area_undo_refreshes_group_counts(self):
        dialog = CareAreasDialog()
        dialog._new_group("CA")
        dialog.canvas.history.append([])
        dialog._area_added([0.1, 0.1, 0.2, 0.2])
        self.assertEqual(dialog.groups.item(0, 6).text(), "1")

        dialog._undo()

        self.assertEqual(dialog.groups.rowCount(), 0)

    def test_setup_klarf_import_parses_defects_and_selects_wafer(self):
        klarf = """FileVersion 1 1;
LotID LOT-17;
WaferID W03;
DeviceID Device1;
StepID Layer1;
DefectRecordSpec 8 DEFECTID XREL YREL XINDEX YINDEX TEST CLASSCODE DSIZE;
DefectList 1
7 0.25 0.75 3 4 1 12 0.800
;
EndOfFile;
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "input.klarf"
            path.write_text(klarf, encoding="utf-8")

            dialog = SelectDefectDataDialog()
            with patch(
                "puma_ui.modules.defect_data.dialogs.QFileDialog.getOpenFileName",
                return_value=(str(path), "KLARF Files"),
            ), patch.object(
                SaveImportedLotResultDialog,
                "exec",
                return_value=QDialog.Accepted,
            ), patch.object(
                SelectImportedWaferDialog,
                "exec",
                return_value=QDialog.Accepted,
            ):
                dialog._import_klarf()

        self.assertTrue(dialog.changed)
        self.assertEqual(dialog.attached_data["wafer_id"], "W03")
        self.assertEqual(dialog.attached_data["defects"][0]["id"], 7)
        self.assertEqual(dialog.attached_data["defects"][0]["class_code"], 12)

    def test_auto_alignment_site_sequence_requires_three_corners(self):
        dialog = AutoSiteSelectionDialog()
        self.assertFalse(dialog.finish_button.isEnabled())
        dialog._mark_die_corner()
        dialog._mark_die_corner()
        self.assertFalse(dialog.finish_button.isEnabled())
        dialog._mark_die_corner()
        self.assertTrue(dialog.finish_button.isEnabled())
        self.assertEqual(dialog.corner_count, 3)

    def test_alignment_quality_rule_requires_every_applicable_target(self):
        scores = simulated_alignment_candidate_scores(
            3,
            DEFAULT_ALIGNMENT_QUALITY_TARGETS,
        )
        evaluation = evaluate_alignment_quality(scores, DEFAULT_ALIGNMENT_QUALITY_TARGETS)
        self.assertTrue(evaluation["qualified"])
        self.assertEqual(evaluation["passed"], 10)
        self.assertEqual(evaluation["applicable"], 10)
        self.assertIsNone(evaluation["checks"]["correlation"]["x_reg"])

        scores["sharpness"]["y_reg"] = 29.99
        evaluation = evaluate_alignment_quality(scores, DEFAULT_ALIGNMENT_QUALITY_TARGETS)
        self.assertFalse(evaluation["qualified"])
        self.assertEqual(evaluation["passed"], 9)

    def test_auto_alignment_selects_best_candidate_and_displays_threshold_result(self):
        dialog = AutoSiteSelectionDialog()
        for _ in range(3):
            dialog._mark_die_corner()

        self.assertTrue(dialog.quality_result["qualified"])
        self.assertEqual(dialog.quality_result["selected_candidate"], 3)
        self.assertEqual(dialog.quality_result["evaluation"]["passed"], 10)
        self.assertIn("PASS - 10/10", dialog.quality_status.text())
        self.assertEqual(dialog.quality_table.item(0, 0).text(), "71.00")
        self.assertEqual(dialog.candidate_quality_table.item(0, 1).text(), "N/A")

    def test_auto_alignment_candidate_count_recalculates_nonoptimal_result(self):
        dialog = AutoSiteSelectionDialog()
        dialog.desired_candidates.setValue(1)
        for _ in range(3):
            dialog._mark_die_corner()

        self.assertFalse(dialog.quality_result["qualified"])
        self.assertEqual(dialog.quality_result["selected_candidate"], 1)
        self.assertIn("NOT QUALIFIED", dialog.quality_status.text())
        self.assertTrue(dialog.finish_button.isEnabled())

        dialog.desired_candidates.setValue(3)
        self.assertTrue(dialog.quality_result["qualified"])
        self.assertIn("PASS", dialog.quality_status.text())

    def test_auto_alignment_result_persists_calculated_scores_for_orientation(self):
        selection = AutoSiteSelectionDialog()
        for _ in range(3):
            selection._mark_die_corner()

        menu = AlignmentMenuDialog(alignment_state={"_orientation": "90"})
        with patch(
            "puma_ui.modules.wafer_alignment.dialogs.AutoSiteAlignmentParametersDialog.exec",
            return_value=QDialog.Accepted,
        ), patch(
            "puma_ui.modules.wafer_alignment.dialogs.AutoSiteSelectionDialog",
            return_value=selection,
        ), patch.object(selection, "exec", return_value=QDialog.Accepted):
            menu._open_auto_site_selection()

        self.assertTrue(menu.alignment_result["qualified"])
        self.assertEqual(menu.alignment_result["status"], "Qualified")
        self.assertEqual(menu.alignment_result["quality"]["evaluation"]["applicable"], 10)
        self.assertIn("90", menu.alignment_result["scores"])
        self.assertNotEqual(menu.alignment_result["scores"]["90"]["uniqueness"], "-")

    def test_alignment_primary_test_optics_follow_recipe_availability(self):
        unavailable = AutoSiteAlignmentParametersDialog(test_optics_defined=False)
        self.assertFalse(unavailable.production_optics.isEnabled())
        self.assertFalse(unavailable.production_test.isEnabled())

        available = AutoSiteAlignmentParametersDialog(test_optics_defined=True)
        self.assertTrue(available.production_optics.isEnabled())
        available.production_optics.setChecked(True)
        self.assertTrue(available.production_test.isEnabled())

        interactive = AlignmentParametersDialog(test_optics_defined=True)
        self.assertTrue(interactive.production_optics.isEnabled())

    def test_existing_alignment_sites_can_be_kept_with_next(self):
        dialog = SelectAlignmentSitesDialog(
            "DF",
            existing_sites=[[-1800.0, 1200.0], [-800.0, 1200.0]],
            existing_images=["Stored first", "Stored second"],
        )
        self.assertEqual(len(dialog.marked_sites), 2)
        self.assertEqual(dialog.site_table.item(0, 3).text(), "Stored first")
        self.assertTrue(dialog.next_button.isEnabled())
        dialog._next_site()
        self.assertEqual(dialog.current_site_index, 1)
        self.assertTrue(dialog.next_button.isEnabled())
        dialog._next_site()
        self.assertTrue(dialog.aligned)

    def test_alignment_site_outside_blue_box_is_rejected(self):
        dialog = SelectAlignmentSitesDialog("DF")
        dialog.wafer_view.stage_position = (5100.0, 0.0)
        with patch("puma_ui.modules.wafer_alignment.dialogs.QMessageBox.warning") as warning:
            dialog._mark_site()
        warning.assert_called_once()
        self.assertEqual(dialog.marked_sites, [])

    def test_alignment_actions_follow_recipe_prerequisites(self):
        new_recipe = AlignmentMenuDialog(alignment_state={})
        self.assertTrue(new_recipe.align_wafer_button.isEnabled())
        self.assertTrue(new_recipe.set_optics_button.isEnabled())
        self.assertTrue(new_recipe.qualify_button.isEnabled())
        self.assertTrue(new_recipe.manual_button.isEnabled())
        with patch("puma_ui.modules.wafer_alignment.dialogs.QMessageBox.warning") as warning:
            new_recipe._align_wafer()
            new_recipe._set_optics_and_retrain()
            new_recipe._open_qualify_with_test_optics()
            new_recipe._open_manual_alignment()
        self.assertEqual(warning.call_count, 4)

        existing = AlignmentMenuDialog(alignment_state={
            "sites_defined": True,
            "_test_optics_defined": True,
            "_manual_alignment_enabled": True,
            "_alignment_failed": True,
        })
        self.assertTrue(existing.align_wafer_button.isEnabled())
        self.assertTrue(existing.qualify_button.isEnabled())
        self.assertTrue(existing.manual_button.isEnabled())

    def test_new_alignment_does_not_show_existing_site_warning(self):
        dialog = AlignmentMenuDialog(alignment_state={})
        with patch("puma_ui.modules.wafer_alignment.dialogs.QMessageBox.question") as question, patch(
            "puma_ui.modules.wafer_alignment.dialogs.AutoSiteAlignmentParametersDialog.exec",
            return_value=QDialog.Rejected,
        ):
            dialog._open_auto_site_selection()
        question.assert_not_called()

    def test_existing_alignment_reselection_honors_cancel(self):
        dialog = AlignmentMenuDialog(alignment_state={"sites_defined": True})
        with patch(
            "puma_ui.modules.wafer_alignment.dialogs.QMessageBox.question",
            return_value=QMessageBox.No,
        ) as question:
            dialog._open_select_sites()
        question.assert_called_once()
        self.assertIsNone(dialog.alignment_result)

    def test_die_pitch_uses_one_low_mag_and_three_high_mag_sites(self):
        dialog = WaferMapSiteSelectionDialog("die_pitch", 5000.0, 6000.0)
        self.assertEqual(dialog._total_required_sites(), 4)
        dialog._mark_site()
        self.assertTrue(dialog.next_button.isEnabled())
        for _ in range(3):
            dialog._mark_site()
        self.assertTrue(dialog.finish_button.isEnabled())
        self.assertEqual(dialog.mark_count, 4)

    def test_wafer_map_uses_three_low_mag_and_three_high_mag_sites(self):
        dialog = WaferMapSiteSelectionDialog("wafer_map")
        self.assertEqual(dialog._total_required_sites(), 6)
        for _ in range(5):
            dialog._mark_site()
        self.assertFalse(dialog.finish_button.isEnabled())
        dialog._mark_site()
        self.assertTrue(dialog.finish_button.isEnabled())

    def test_wafer_map_site_grid_is_centered_and_clipped_to_the_wafer(self):
        canvas = WaferMapSiteCanvas()
        canvas.resize(820, 760)
        geometry = canvas.layout_geometry()
        wafer_x, wafer_y, wafer_width, wafer_height = geometry["wafer"]
        center_x, center_y = geometry["center"]
        cell_width, cell_height = geometry["cell"]

        self.assertAlmostEqual(center_x, wafer_x + wafer_width / 2, delta=1)
        self.assertAlmostEqual(center_y, wafer_y + wafer_height / 2, delta=1)
        self.assertLessEqual(min(geometry["x_lines"]), wafer_x + cell_width)
        self.assertGreaterEqual(max(geometry["x_lines"]), wafer_x + wafer_width - cell_width)
        self.assertLessEqual(min(geometry["y_lines"]), wafer_y + cell_height)
        self.assertGreaterEqual(max(geometry["y_lines"]), wafer_y + wafer_height - cell_height)

        first, second, third = geometry["selection_points"]
        self.assertAlmostEqual(second[0] - first[0], cell_width)
        self.assertAlmostEqual(second[1] - first[1], cell_height)
        self.assertGreater(third[0], center_x)
        self.assertGreater(third[1], center_y)
        for point_x, point_y in geometry["selection_points"]:
            distance_squared = (point_x - center_x) ** 2 + (point_y - center_y) ** 2
            self.assertLess(distance_squared, geometry["radius"] ** 2)

    def test_scribe_lines_require_two_diagonal_sites(self):
        dialog = ScribeLinesSetupDialog()
        self.assertFalse(dialog.finish_button.isEnabled())
        dialog._mark_site()
        self.assertFalse(dialog.finish_button.isEnabled())
        dialog._mark_site()
        self.assertTrue(dialog.finish_button.isEnabled())
        self.assertEqual((dialog.scribe_x, dialog.scribe_y), (120.0, 120.0))

    def test_wafer_handling_state_round_trip(self):
        dialog = WaferHandlingDialog()
        dialog._load_and_align()
        state = dialog.result_state()
        self.assertTrue(state["wafer_loaded"])
        self.assertTrue(state["wafer_aligned"])
        restored = WaferHandlingDialog(state=state)
        self.assertTrue(restored.wafer_loaded)
        self.assertTrue(restored.wafer_aligned)
        restored._unload_wafer()
        self.assertFalse(restored.result_state()["wafer_loaded"])

    def test_wafer_handling_exposes_and_persists_three_load_ports(self):
        dialog = WaferHandlingDialog()
        self.assertEqual(set(dialog.port_panels), {1, 2, 3})
        dialog.load_carrier(3)
        dialog.select_slot(3, 17)
        self.assertTrue(dialog._load_wafer())
        state = dialog.result_state()
        self.assertEqual(state["selected_port"], 3)
        self.assertEqual(state["selected_slots"][3], 17)
        self.assertEqual(state["slot_states"][3][17], "Loaded")
        restored = WaferHandlingDialog(state=state)
        self.assertEqual(set(restored.port_panels), {1, 2, 3})
        self.assertEqual(restored.selected_port, 3)
        self.assertEqual(restored.wafer_source_slot, 17)

    def test_wafer_handling_alignment_requires_recipe_sites(self):
        unavailable = WaferHandlingDialog(recipe={
            "alignment": {"sites_defined": False},
            "wafer_properties": {"type": "Patterned"},
        })
        self.assertTrue(unavailable.load_wafer_button.isEnabled())
        self.assertFalse(unavailable.load_align_button.isEnabled())
        unavailable._load_wafer()
        self.assertFalse(unavailable.align_button.isEnabled())

        ready = WaferHandlingDialog(recipe={
            "alignment": {"sites_defined": True},
            "wafer_properties": {"type": "Patterned"},
        })
        self.assertTrue(ready.load_align_button.isEnabled())

    def test_wafer_handling_tracks_slot_state_and_optional_id(self):
        dialog = WaferHandlingDialog()
        dialog.read_id_check.setChecked(True)
        self.assertTrue(dialog._load_wafer())
        self.assertEqual(dialog.slot_states[1][25], "Loaded")
        self.assertEqual(dialog.wafer_ids[1][25], "W1-25")
        dialog._align_wafer()
        self.assertEqual(dialog.slot_states[1][25], "Aligned")
        dialog._unload_wafer()
        self.assertEqual(dialog.slot_states[1][25], "Present")
        self.assertEqual(dialog.wafer_ids[1][25], "W1-25")

    def test_wafer_handling_blocks_source_carrier_unload(self):
        dialog = WaferHandlingDialog()
        dialog._load_wafer()
        with patch("puma_ui.modules.wafer_handling.dialog.QMessageBox.warning") as warning:
            dialog.unload_carrier(1)
        warning.assert_called_once()
        self.assertTrue(dialog.carrier_loaded[1])
        self.assertTrue(dialog.wafer_loaded)

    def test_wafer_handling_automatic_recovery_returns_wafer_to_source(self):
        dialog = WaferHandlingDialog()
        dialog.select_slot(1, 12)
        dialog._load_and_align()
        dialog._automatic_recovery()
        self.assertFalse(dialog.wafer_loaded)
        self.assertFalse(dialog.wafer_aligned)
        self.assertEqual(dialog.slot_states[1][12], "Present")
        self.assertIsNone(dialog.wafer_source_port)
        self.assertIsNone(dialog.wafer_source_slot)

    def test_wafer_handling_advanced_controls_actually_expand(self):
        dialog = WaferHandlingDialog()
        self.assertTrue(dialog.advanced_laser_panel.isHidden())
        self.assertTrue(dialog.advanced_dark_panel.isHidden())
        dialog.advanced_button.setChecked(True)
        dialog._toggle_advanced()
        self.assertFalse(dialog.advanced_laser_panel.isHidden())
        self.assertFalse(dialog.advanced_dark_panel.isHidden())
        dialog.layer_types.append({"name": "Test Layer", "laser_power_limit": 0.5})
        dialog._refresh_layer_combo("Test Layer")
        self.assertIn("Test Layer", dialog.layer_combo.currentText())

    def test_retrain_controls_require_loaded_and_aligned_wafer(self):
        unavailable = TestsSetupDialog(
            [default_test(1)],
            wafer_loaded=True,
            wafer_aligned=False,
        )
        self.assertFalse(unavailable.retrain_button.isEnabled())
        ready = TestsSetupDialog(
            [default_test(1)],
            wafer_loaded=True,
            wafer_aligned=True,
        )
        self.assertTrue(ready.retrain_button.isEnabled())
        self.assertTrue(ready.retrain_light.isEnabled())

    def test_mode_no_test_permanently_clears_the_previous_test_setup(self):
        test = default_test(1)
        test["name"] = "Old tuned test"
        test["fourier_trained"] = True
        test["run_nef"] = True
        dialog = TestsSetupDialog([test])
        mode_combo = dialog.matrix.cellWidget(0, 1)

        with patch(
            "puma_ui.modules.inspection_tests.dialog.QMessageBox.question",
            return_value=QMessageBox.Yes,
        ):
            dialog._change_mode(0, "No Test", mode_combo)

        self.assertEqual(dialog.tests[0]["mode"], "No Test")
        self.assertEqual(dialog.tests[0]["name"], "Test 1")
        self.assertFalse(dialog.tests[0]["fourier_trained"])
        self.assertFalse(dialog.tests[0]["run_nef"])

    def test_unsupervised_grouping_enables_feature_vectors_and_group_count(self):
        dialog = TestsSetupDialog([default_test(1)])
        dialog._set_value(0, "run_unsupervised_grouping", True)

        self.assertTrue(dialog.tests[0]["save_feature_vectors"])
        group_row = next(
            index
            for index, (_label, key, _kind) in enumerate(dialog.PARAMETER_ROWS)
            if key == "unsupervised_groups"
        )
        self.assertTrue(dialog.matrix.cellWidget(group_row, 1).isEnabled())

    def test_fourier_box_page_opens_and_advanced_options_store_each_channel_deck(self):
        box_page = FourierBoxDialog([])
        self.assertEqual(box_page.table.columnCount(), 5)

        advanced = AdvancedFourierOptionsDialog({
            "decks": {"1": "DECK 0", "2": "DECK 1", "3": "DECK 2"}
        })
        advanced._accept()
        self.assertEqual(
            advanced.result_options["decks"],
            {"1": "DECK 0", "2": "DECK 1", "3": "DECK 2"},
        )

    def test_blank_wafer_test_setup_does_not_require_alignment_or_wafermap(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = RecipeStore(Path(temp_dir) / "recipes.json")
            with patch("puma_ui.main_window.RecipeStore", return_value=store):
                window = PumaMainWindow()
            recipe = store.new_recipe()
            wafer_properties = window._current_wafer_properties()
            wafer_properties["type"] = "Blank"
            recipe["wafer_properties"] = wafer_properties
            window._set_current_recipe(recipe)
            test = default_test(1, "Blank")
            test["status"] = "Valid"
            dialog = type("CompletedTestsPage", (), {
                "current_test": 0,
                "result_tests": [test],
                "changed": True,
            })()

            window._apply_tests_setup(dialog)

            self.assertEqual(window.current_recipe["status"], "Valid")
            self.assertTrue(window.setup_run_button.isEnabled())

    def test_edit_menu_exposes_manual_test_copy_and_paste_commands(self):
        window = PumaMainWindow()
        labels = [action.text() for action in window.menuBar().actions()[1].menu().actions()]
        self.assertIn("Copy Test", labels)
        self.assertIn("Paste Test", labels)


if __name__ == "__main__":
    unittest.main()

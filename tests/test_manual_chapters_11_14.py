from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from puma_ui.modules.sizing import (
    DefectSetCollectionDialog,
    DefectSetEditorDialog,
    HistogramDialog,
    MapPropertiesDialog,
    MappingsDialog,
    SizingRecipeDialog,
    SizingSetupTool,
    auto_map_for_set,
    default_sizing_state,
    defect_set_from_result,
)
from puma_ui.modules.system_status import (
    BackupArchiveRestoreDialog,
    CarrierManagementDialog,
    ControlJobManagementDialog,
    DiskAdminDialog,
    LoadPortIndicatorDialog,
    LogSettingsDialog,
    SecsOperationsDialog,
    SignalTowerDialog,
    ToolsConfigurationDialog,
    UserAdministrationDialog,
    UserPreferencesDialog,
)
from puma_ui.modules.xp_offline import (
    CAGEditorDialog,
    GDS2CAConverterDialog,
    ManualAssistDialog,
    RDSManagerDialog,
    RecipeComparatorDialog,
    RegistrationSiteLibraryDialog,
    XPRecipeGeneratorDialog,
    default_xp_state,
    generate_autolearn_recipes,
    generate_care_area_component,
    make_registration_site,
)
from puma_ui.qt_compat import QApplication, QDialog, QMessageBox, Qt
from puma_ui.recipe_store import RecipeStore

from manual_ui_helpers import QTest, click, process_events, replace_text, select_combo, visible_button


def lot_result(identifier="result-1", wafer="W01"):
    return {
        "id": identifier,
        "lot_id": "LOT-SIZING",
        "wafer_id": wafer,
        "inspection": "Deep",
        "status": "Complete",
        "defects": [
            {"id": 1, "x": 0.0, "y": 0.0, "size_um": 1.0, "signal": 120.0, "test": "Test 1"},
            {"id": 2, "x": 5.0, "y": 5.0, "size_um": 2.0, "signal": 90.0, "test": "Test 1"},
            {"id": 3, "x": 10.0, "y": 10.0, "size_um": 5.0, "signal": 50.0, "test": "Test 2"},
        ],
    }


def sizing_state(two_sets=False):
    first = defect_set_from_result(lot_result(), name="Target")
    for index, defect in enumerate(first["defects"], 1):
        defect["reference_size_um"] = float(index)
    state = default_sizing_state()
    state["defect_sets"] = [first]
    if two_sets:
        second = defect_set_from_result(lot_result("result-2", "W02"), name="Reference")
        for defect in second["defects"]:
            defect["reference_size_um"] = defect["computed_size_um"]
        state["defect_sets"].append(second)
    mapping = auto_map_for_set(first, reference_set=state["defect_sets"][-1])
    state["maps"] = [mapping]
    state["active_map_id"] = mapping["id"]
    return state


def base_recipe():
    return {
        "id": "base-1",
        "inspection": "BaseRecipe",
        "device": "DeviceA",
        "step": "Base",
        "source": "local",
        "status": "Valid",
        "approval": "Production",
        "alignment": {"sites_defined": True},
        "wafer_map": {"die_pattern_defined": True},
        "xp_offline": {"registration_sites": [make_registration_site("CommonMark", 10, 20, "Base")]},
        "tests": [{"name": "Test 1", "light_level": 8.5}],
    }


class ManualChaptersElevenToFourteenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = RecipeStore(Path(self.temp.name) / "recipes.json", default_recipes=[])

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

    def test_ch11_sizing_recipe_all_scale_factors_cut_lines_validation_and_save(self):
        dialog = self.show_dialog(SizingRecipeDialog())
        self.assertEqual(len(dialog.factor_controls), 6)
        self.assertEqual(len(dialog.cut_controls), 6)
        dialog.factor_controls["Small"].setValue(1.25)
        dialog.cut_controls["Small"].setValue(30.0)
        dialog.cut_controls["Large"].setValue(20.0)
        with patch("puma_ui.modules.sizing.dialogs.QMessageBox.warning") as warning:
            click(visible_button(dialog, "OK"))
        warning.assert_called_once()
        self.assertTrue(dialog.isVisible())
        dialog.cut_controls["Small"].setValue(10.0)
        dialog.cut_controls["Large"].setValue(20.0)
        dialog.cut_controls["Very Large"].setValue(30.0)
        click(visible_button(dialog, "OK"))
        self.assertEqual(dialog.result(), QDialog.Accepted)
        self.assertEqual(dialog.result_recipe["scale_factors"]["Small"], 1.25)

    def test_ch11_reference_edit_map_histogram_and_collection_workflow(self):
        state = sizing_state(two_sets=True)
        editor = self.show_dialog(DefectSetEditorDialog(state, state["defect_sets"][0]["id"]))
        editor.table.item(0, 1).setText("-1")
        with patch("puma_ui.modules.sizing.dialogs.QMessageBox.warning") as warning:
            click(visible_button(editor, "Apply"))
        warning.assert_called_once()
        editor.table.item(0, 1).setText("4.75")
        click(visible_button(editor, "OK"))
        self.assertEqual(editor.result_state["defect_sets"][0]["defects"][0]["reference_size_um"], 4.75)

        maps = self.show_dialog(MappingsDialog(state))
        maps.target.setCurrentIndex(0)
        maps.reference.setCurrentIndex(1)
        click(visible_button(maps, "Add"))
        self.assertEqual(maps.table.rowCount(), 2)
        maps.table.selectRow(1)
        click(visible_button(maps, "Remove"))
        self.assertEqual(maps.table.rowCount(), 1)
        click(visible_button(maps, "OK"))

        histogram = self.show_dialog(HistogramDialog(state, "Size"))
        click(histogram.cdf)
        click(histogram.out_of_graph)
        histogram.sliders["Small"].setValue(10.0)
        histogram.sliders["Large"].setValue(20.0)
        histogram.sliders["Very Large"].setValue(30.0)
        click(visible_button(histogram, "Apply"))
        self.assertTrue(histogram.chart.show_cdf)
        self.assertTrue(histogram.chart.show_out_of_graph)

        collection = self.show_dialog(DefectSetCollectionDialog(state))
        collection.list.setCurrentRow(1)
        click(visible_button(collection, "Remove"))
        self.assertEqual(collection.list.count(), 1)
        click(visible_button(collection, "OK"))

    def test_ch11_map_properties_matches_target_reference_overlay_workflow(self):
        state = sizing_state(two_sets=True)
        mapping = state["maps"][0]
        dialog = self.show_dialog(MapPropertiesDialog(state, mapping["id"]))
        self.assertEqual(
            [dialog.tabs.tabText(index) for index in range(dialog.tabs.count())],
            ["Target", "Reference", "Overlay"],
        )
        dialog.reference_table.item(0, 3).setText("4.25")
        dialog.overlay_radius.setValue(18.5)
        self.assertTrue(dialog._apply())
        reference_id = mapping["reference_set_id"]
        reference = next(
            item for item in dialog.result_state["defect_sets"] if item["id"] == reference_id
        )
        self.assertEqual(reference["defects"][0]["reference_size_um"], 4.25)
        self.assertEqual(dialog.result_state["maps"][0]["overlay_radius_um"], 18.5)

        workspace = self.show_dialog(SizingSetupTool(self.store))
        self.assertIn("Properties", [action.text() for action in workspace.view_menu.actions()])
        self.assertEqual(workspace.properties_button.text(), "Properties")
        self.assertEqual(
            [
                workspace.open_result_button.text(),
                workspace.open_klarf_button.text(),
                workspace.save_defects_button.text(),
                workspace.transfer_button.text(),
                workspace.edit_map_button.text(),
                workspace.edit_recipe_button.text(),
                workspace.histogram_button.text(),
                workspace.properties_button.text(),
                workspace.export_button.text(),
            ],
            [
                "Open Lot Result",
                "Open KLARF",
                "Save Defects",
                "Transfer Size",
                "Edit Map",
                "Edit Recipe",
                "Histogram",
                "Properties",
                "Export Recipe",
            ],
        )

    def test_ch11_sizing_workspace_load_map_filter_highlight_and_persist(self):
        tool = self.show_dialog(SizingSetupTool(self.store, initial_result=lot_result()))
        self.assertEqual(tool.map_combo.count(), 1)
        click(tool.nonzero)
        select_combo(tool.highlight, "Small")
        self.assertEqual(tool.scatter.highlight_group, "Small")
        saved = self.store.get_preferences()["sizing_workspace"]
        self.assertFalse(saved["show_nonzero_only"])
        self.assertEqual(saved["highlight_group"], "Small")

    def test_ch12_user_security_signal_lights_preferences_and_logs(self):
        users = self.show_dialog(UserAdministrationDialog())
        replace_text(users.username, "operator1")
        replace_text(users.password, "secret")
        select_combo(users.access, "Engineer")
        click(visible_button(users, "Create / Update User"))
        self.assertEqual(users.user_table.rowCount(), 2)
        click(visible_button(users, "OK"))

        tower = self.show_dialog(SignalTowerDialog())
        select_combo(tower.state_controls["Error"]["Red"], "On")
        click(visible_button(tower, "Apply"))
        self.assertEqual(tower.result_state["signal_tower"]["states"]["Error"]["Red"], "On")

        lights = self.show_dialog(LoadPortIndicatorDialog())
        select_combo(lights.controls["Alarm"][0], "On")
        click(visible_button(lights, "Save"))
        self.assertEqual(lights.result_state["load_port_indicators"]["states"]["Alarm"][0], "On")

        prefs = self.show_dialog(UserPreferencesDialog())
        select_combo(prefs.coordinate, "Raster")
        select_combo(prefs.colors, "InLine ADC")
        click(visible_button(prefs, "OK"))
        self.assertEqual(prefs.result_state["user_preferences"]["coordinate_display"], "Raster")

        logs = self.show_dialog(LogSettingsDialog())
        enabled, level = logs.log_controls["subsystem_logs"]["Optics"]
        click(enabled)
        select_combo(level, "Debug")
        click(visible_button(logs, "OK"))
        self.assertEqual(logs.result_state["log_settings"]["subsystem_logs"]["Optics"]["level"], "Debug")

    def test_ch12_control_carrier_disk_tools_backup_and_secs_paths(self):
        jobs = [{"id": "one", "lot_id": "L1", "status": "Waiting", "inspection": "Deep"}]
        controls = self.show_dialog(ControlJobManagementDialog(jobs, enabled=True, reason="Ready"))
        controls.control_table.selectRow(0)
        click(visible_button(controls, "Start"))
        self.assertEqual(controls.jobs[0]["status"], "Running")
        click(visible_button(controls, "Close"))

        carrier = self.show_dialog(CarrierManagementDialog({"carrier_loaded": {1: False}, "selected_port": 1}, enabled=True))
        click(visible_button(carrier, "Bind Carrier"))
        self.assertTrue(carrier.state["carrier_loaded"][1])
        click(visible_button(carrier, "Release Carrier"))
        click(visible_button(carrier, "Close"))

        disk = self.show_dialog(DiskAdminDialog())
        select_combo(disk.schedule, "Weekly")
        click(disk.delete_images)
        disk.image_days.setValue(45)
        click(visible_button(disk, "Run Now"))
        self.assertTrue(disk.run_now)

        tools = self.show_dialog(ToolsConfigurationDialog())
        replace_text(tools.name, "Puma-02")
        replace_text(tools.serial, "9980-002")
        click(visible_button(tools, "Add"))
        self.assertEqual(tools.table.rowCount(), 1)
        click(visible_button(tools, "Close"))

        backup = self.show_dialog(BackupArchiveRestoreDialog())
        click(visible_button(backup, "Backup"))
        self.assertEqual(backup.result_action, "Backup")

        secs = self.show_dialog(SecsOperationsDialog(recipes=[{"inspection": "Deep"}]))
        select_combo(secs.e10, "Productive")
        replace_text(secs.message, "START LOT")
        click(visible_button(secs, "Synchronize Clock"))
        click(visible_button(secs, "Apply / Send"))
        self.assertEqual(secs.result_state["e10_state"], "Productive")
        self.assertGreaterEqual(len(secs.result_state["host_messages"]), 2)

    def test_ch13_registration_generator_autolearn_manual_assist(self):
        recipe = base_recipe()
        sites = self.show_dialog(RegistrationSiteLibraryDialog(recipe))
        replace_text(sites.name, "Second")
        replace_text(sites.layer, "Metal1")
        sites.x.setValue(100)
        sites.y.setValue(200)
        click(visible_button(sites, "Add Site"))
        self.assertEqual(sites.table.rowCount(), 2)
        sites.table.selectRow(1)
        click(visible_button(sites, "Delete"))
        self.assertEqual(sites.table.rowCount(), 1)
        click(visible_button(sites, "Finish"))

        saved = self.store.save_recipe(recipe)
        generator = self.show_dialog(XPRecipeGeneratorDialog(self.store, saved))
        replace_text(generator.layer_name, "Metal1")
        click(visible_button(generator, "Add Layer"))
        self.assertEqual(generator.table.rowCount(), 1)
        select_combo(generator.mode, "OSTS")
        select_combo(generator.destination, "Local")
        click(visible_button(generator, "Generate"))
        self.assertEqual(len(generator.generated_recipes), 1)
        self.assertTrue(generator.generated_recipes[0]["xp_offline"]["osts_enabled"])

        generated = generate_autolearn_recipes(recipe, [{"layer": "Metal2"}])[0]
        assist = self.show_dialog(ManualAssistDialog(default_xp_state(), generated))
        click(assist.fix)
        click(assist.verify)
        click(assist.signal)
        assist.fix_timeout.setValue(15)
        select_combo(assist.outcome, "Simulate AutoLearn Success")
        click(visible_button(assist, "Apply"))
        self.assertEqual(assist.result_recipe["recipe_type"], "Normal")

    def test_ch13_rds_checkin_distribution_comparison_edit_and_save(self):
        recipe = base_recipe()
        rds = self.show_dialog(RDSManagerDialog(self.store, recipe, default_xp_state()))
        replace_text(rds.user, "engineer")
        click(rds.production)
        click(visible_button(rds, "Check In Current Recipe"))
        self.assertEqual(rds.table.rowCount(), 1)
        rds.table.selectRow(0)
        replace_text(rds.destinations, "Puma-01, Puma-02")
        click(visible_button(rds, "Distribute Selected"))
        self.assertEqual(rds.state["distribution_events"][0]["status"], "Distributed (simulated)")
        click(visible_button(rds, "Close"))

        other = dict(recipe, id="base-2", inspection="Other", step="Metal1")
        comparator = self.show_dialog(RecipeComparatorDialog([recipe, other]))
        replace_text(comparator.filter, "DeviceA")
        click(visible_button(comparator, "Check All"))
        click(visible_button(comparator, "Load Recipes"))
        self.assertEqual(len(comparator.loaded_recipes), 2)
        self.assertGreater(comparator.comparison.rowCount(), 0)
        click(visible_button(comparator, "Configure Visible Parameters"))
        tab_bar = comparator.tabs.tabBar()
        QTest.mouseClick(tab_bar, Qt.LeftButton, Qt.NoModifier, tab_bar.tabRect(2).center())
        process_events()
        self.assertGreaterEqual(comparator.tests_table.rowCount(), 1)
        click(visible_button(comparator, "Save All Recipes"))
        self.assertEqual(len(comparator.result_recipes), 2)

    def test_ch14_gds2ca_file_generation_default_path_and_cag_codes(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "layout.cagds"
            source.write_bytes(b"simulated-gds-data")
            converter = self.show_dialog(GDS2CAConverterDialog())
            converter.paths["Care Area GDS File"].setText(str(source))
            converter.paths["Output Location"].setText(directory)
            click(converter.default)
            self.assertFalse(converter.paths["Mapping File"].isEnabled())
            click(visible_button(converter, "Generate Care Areas"))
            self.assertEqual(converter.result(), QDialog.Accepted)
            self.assertTrue((Path(directory) / "layout.gds2ca.json").is_file())
            self.assertEqual(converter.result_component["groups"][0]["status"], "V*R*")

        groups = generate_care_area_component(b"gds", use_default_data=True)["groups"]
        groups.append(dict(groups[0], name="Second", cag_code=2))
        editor = self.show_dialog(CAGEditorDialog(groups))
        editor.table.selectAll()
        editor.code.setValue(100)
        click(editor.sequential)
        click(visible_button(editor, "Assign"))
        self.assertEqual([item["cag_code"] for item in editor.groups], [100, 101])
        click(visible_button(editor, "OK"))


if __name__ == "__main__":
    unittest.main()

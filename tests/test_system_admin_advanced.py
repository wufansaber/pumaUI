from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from puma_ui.main_window import PumaMainWindow
from puma_ui.modules.system_status import (
    BackupArchiveRestoreDialog,
    CarrierManagementDialog,
    ControlJobManagementDialog,
    DiskAdminDialog,
    ERCManagerDialog,
    LoadPortIndicatorDialog,
    LogSettingsDialog,
    SecsOperationsDialog,
    SignalTowerDialog,
    SubstrateTrackingDialog,
    ToolsConfigurationDialog,
    UserAdministrationDialog,
    UserPreferencesDialog,
    add_or_update_user,
    authenticate_user,
    control_job_access,
    default_system_admin_state,
    disk_admin_next_run,
    normalized_system_admin_state,
)
from puma_ui.qt_compat import QApplication, QPushButton, QTableWidget, Qt
from puma_ui.recipe_store import RecipeStore


class AdvancedSystemAdministrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = RecipeStore(Path(self.temp_dir.name) / "recipes.json")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_admin_normalization_enforces_manual_disk_and_timeout_ranges(self):
        state = normalized_system_admin_state({
            "security": {"inactivity_timeout_minutes": 9999},
            "disk_admin": {"override_percent": 2, "image_days": 0, "lot_days": 900},
            "e10_state": "Unknown",
        })
        self.assertEqual(state["security"]["inactivity_timeout_minutes"], 1440)
        self.assertEqual(state["disk_admin"]["override_percent"], 10)
        self.assertEqual(state["disk_admin"]["image_days"], 1)
        self.assertEqual(state["disk_admin"]["lot_days"], 365)
        self.assertEqual(state["e10_state"], "Standby")

    def test_user_passwords_are_hashed_and_limited_to_sixteen_characters(self):
        state = add_or_update_user(default_system_admin_state(), "engineer", "secret", "Engineer")
        user = next(item for item in state["security"]["users"] if item["username"] == "engineer")
        self.assertNotEqual(user["password_hash"], "secret")
        self.assertTrue(authenticate_user(state, "engineer", "secret"))
        self.assertFalse(authenticate_user(state, "engineer", "wrong"))
        with self.assertRaisesRegex(ValueError, "16"):
            add_or_update_user(state, "expert", "x" * 17, "Expert")

    def test_security_disabled_bypasses_authentication(self):
        state = default_system_admin_state()
        state["security"]["enabled"] = False
        self.assertTrue(authenticate_user(state, "missing", "anything"))

    def test_control_jobs_require_options_remote_secs_and_equipment_constant(self):
        state = default_system_admin_state()
        enabled, reason = control_job_access(state, {"secs_enabled": False, "control_mode": "Local"}, {})
        self.assertFalse(enabled)
        self.assertIn("Online/Remote", reason)
        enabled, _reason = control_job_access(state, {"secs_enabled": True, "control_mode": "Remote"}, {"remote_job_commands": True})
        self.assertTrue(enabled)
        state["e87_enabled"] = False
        self.assertFalse(control_job_access(state, {"secs_enabled": True, "control_mode": "Remote"}, {})[0])

    def test_disk_next_run_uses_manual_schedule_intervals(self):
        now = datetime(2026, 9, 6, 10, 0, 0)
        self.assertEqual(disk_admin_next_run("Daily", now), "2026-09-07 10:00:00")
        self.assertEqual(disk_admin_next_run("Weekly", now), "2026-09-13 10:00:00")
        self.assertEqual(disk_admin_next_run("Never", now), "Not scheduled")

    def test_erc_auto_cleanup_removes_only_invalid_references(self):
        recipes = [
            {"id": "valid", "inspection": "Valid", "status": "Valid"},
            {"id": "invalid", "inspection": "Invalid", "status": "Incomplete"},
        ]
        dialog = ERCManagerDialog(recipes)
        dialog.mode.setCurrentText("Auto Clean-up")
        dialog._cleanup()
        self.assertEqual(dialog.deleted_count, 1)
        self.assertEqual(dialog.catalog[0]["recipe_id"], "valid")
        dialog._finish()
        self.assertEqual(len(dialog.result_catalog), 1)
        dialog.close()

    def test_erc_manual_cleanup_uses_checked_rows(self):
        dialog = ERCManagerDialog([{"id": "a", "inspection": "A", "status": "Valid"}, {"id": "b", "inspection": "B", "status": "Valid"}])
        dialog.mode.setCurrentText("Manual Clean-up")
        dialog.table.item(1, 0).setCheckState(Qt.Checked)
        dialog._cleanup()
        self.assertEqual([item["recipe_id"] for item in dialog.catalog], ["a"])
        dialog.close()

    def test_control_job_dialog_changes_state_and_order(self):
        jobs = [
            {"id": "one", "lot_id": "L1", "status": "Waiting", "inspection": "A"},
            {"id": "two", "lot_id": "L2", "status": "Waiting", "inspection": "B"},
        ]
        dialog = ControlJobManagementDialog(jobs, enabled=True, reason="Ready")
        dialog.control_table.selectRow(1)
        dialog._operate("Move Up")
        self.assertEqual(dialog.jobs[0]["id"], "two")
        dialog.control_table.selectRow(0)
        dialog._operate("Start")
        self.assertEqual(dialog.jobs[0]["status"], "Running")
        dialog._finish()
        self.assertEqual(dialog.result_jobs[0]["id"], "two")
        dialog.close()

    def test_control_job_commands_are_disabled_when_prerequisites_fail(self):
        dialog = ControlJobManagementDialog([], enabled=False, reason="Unavailable")
        command_buttons = [
            button for button in dialog.findChildren(QPushButton)
            if button.text() in {"Start", "Stop", "Cancel", "Pause", "Resume", "Move Up", "Move Down"}
        ]
        self.assertFalse(dialog.enabled)
        self.assertEqual(len(command_buttons), 7)
        self.assertTrue(all(not button.isEnabled() for button in command_buttons))
        dialog.close()

    def test_carrier_bind_and_release_updates_runtime_state(self):
        runtime = {"carrier_loaded": {1: False, 2: False, 3: False}, "selected_slots": {1: 25}}
        dialog = CarrierManagementDialog(runtime, enabled=True)
        dialog._command("Bind Carrier")
        self.assertTrue(dialog.state["carrier_loaded"][1])
        dialog._command("Release Carrier")
        self.assertFalse(dialog.state["carrier_loaded"][1])
        dialog._finish()
        self.assertIsNotNone(dialog.result_state)
        dialog.close()

    def test_substrate_tracking_lists_selected_material(self):
        dialog = SubstrateTrackingDialog({"selected_slots": {1: 25}, "wafer_loaded": True, "selected_port": 1})
        table = dialog.findChild(QTableWidget)
        self.assertEqual(dialog.windowTitle(), "Substrate Tracking Information")
        self.assertEqual(table.rowCount(), 1)
        self.assertEqual(table.item(0, 1).text(), "Stage")
        dialog.close()

    def test_user_administration_creates_and_updates_user(self):
        dialog = UserAdministrationDialog()
        dialog.username.setText("alice")
        dialog.password.setText("pass")
        dialog.access.setCurrentText("Expert")
        dialog._add_user()
        self.assertTrue(authenticate_user(dialog.state, "alice", "pass"))
        dialog._finish()
        self.assertEqual(next(item for item in dialog.result_state["security"]["users"] if item["username"] == "alice")["access"], "Expert")
        dialog.close()

    def test_signal_tower_configuration_and_control_are_persistable(self):
        config = SignalTowerDialog()
        config.state_controls["Error"]["Red"].setCurrentText("On")
        config._finish()
        self.assertEqual(config.result_state["signal_tower"]["states"]["Error"]["Red"], "On")
        control = SignalTowerDialog(config.result_state, control_only=True)
        control.state_controls["Manual Control"]["Blue"].setCurrentText("Flash")
        control._finish()
        self.assertEqual(control.result_state["signal_tower"]["control"]["Blue"], "Flash")
        config.close(); control.close()

    def test_load_port_indicator_state_and_priority_are_saved(self):
        dialog = LoadPortIndicatorDialog()
        dialog.controls["Alarm"][0].setCurrentText("On")
        dialog._finish()
        self.assertEqual(dialog.result_state["load_port_indicators"]["states"]["Alarm"][0], "On")
        dialog.close()

    def test_user_preferences_include_all_coordinate_systems(self):
        dialog = UserPreferencesDialog()
        dialog.coordinate.setCurrentText("Raster")
        dialog.colors.setCurrentText("InLine ADC")
        dialog._finish()
        prefs = dialog.result_state["user_preferences"]
        self.assertEqual(prefs["coordinate_display"], "Raster")
        self.assertEqual(prefs["defect_color_scheme"], "InLine ADC")
        dialog.close()

    def test_log_settings_save_subsystem_and_private_levels(self):
        dialog = LogSettingsDialog()
        enabled, level = dialog.log_controls["subsystem_logs"]["Optics"]
        enabled.setChecked(True)
        level.setCurrentText("Debug")
        dialog._finish()
        self.assertEqual(dialog.result_state["log_settings"]["subsystem_logs"]["Optics"], {"enabled": True, "level": "Debug"})
        dialog.close()

    def test_disk_admin_schedule_and_run_now_are_recorded(self):
        dialog = DiskAdminDialog()
        dialog.schedule.setCurrentText("Weekly")
        dialog.delete_images.setChecked(True)
        dialog.image_days.setValue(45)
        dialog._run()
        disk = dialog.result_state["disk_admin"]
        self.assertTrue(dialog.run_now)
        self.assertEqual(disk["schedule"], "Weekly")
        self.assertEqual(disk["image_days"], 45)
        self.assertNotEqual(disk["last_run"], "Never")
        dialog.close()

    def test_remote_tool_defaults_station_id_to_serial(self):
        dialog = ToolsConfigurationDialog()
        dialog.name.setText("Puma-02")
        dialog.serial.setText("9980-002")
        dialog._add()
        self.assertEqual(dialog.state["remote_tools"][0]["station_id"], "9980-002")
        dialog._finish()
        self.assertEqual(len(dialog.result_state["remote_tools"]), 1)
        dialog.close()

    def test_backup_archive_restore_records_selected_action(self):
        dialog = BackupArchiveRestoreDialog()
        dialog._choose("Backup")
        self.assertEqual(dialog.result_action, "Backup")
        self.assertNotEqual(dialog.result_state["last_backup"], "Never")
        dialog.close()

    def test_secs_operations_store_e10_host_and_process_program_events(self):
        dialog = SecsOperationsDialog(recipes=[{"inspection": "Deep"}])
        dialog.e10.setCurrentText("Productive")
        dialog.message.setText("Please send START command")
        dialog._finish()
        self.assertEqual(dialog.result_state["e10_state"], "Productive")
        self.assertEqual(dialog.result_state["host_messages"][-1]["message"], "Please send START command")
        self.assertEqual(dialog.result_state["process_program_events"][-1]["program"], "Deep")
        dialog.close()

    def test_store_persists_system_admin_state(self):
        state = default_system_admin_state()
        state["e116_enabled"] = True
        self.store.update_preferences({"system_admin": state})
        restored = RecipeStore(self.store.path).get_preferences()["system_admin"]
        self.assertTrue(restored["e116_enabled"])
        self.assertEqual(restored["security"]["users"][0]["username"], "kttool")

    def test_main_window_exposes_advanced_utilities(self):
        with patch("puma_ui.main_window.RecipeStore", return_value=self.store):
            window = PumaMainWindow()
        menu_actions = list(window.menuBar().actions())
        utilities_action = next(action for action in menu_actions if action.text() == "Utilities")
        tools_action = next(action for action in menu_actions if action.text() == "Tools")
        utilities = utilities_action.menu()
        tools = tools_action.menu()
        self.assertIn("ERC Manager...", [action.text() for action in utilities.actions()])
        labels = [action.text() for action in tools.actions()]
        self.assertIn("Control Job Management...", labels)
        self.assertIn("Carrier Management...", labels)
        self.assertIn("Disk Admin...", labels)
        self.assertIn("Tools Configure...", labels)
        window.close()


if __name__ == "__main__":
    unittest.main()

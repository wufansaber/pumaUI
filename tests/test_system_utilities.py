from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from puma_ui.main_window import PumaMainWindow
from puma_ui.modules.system_status import (
    ClickAndMarkConfigurationDialog,
    DataTransferQueueDialog,
    DeleteInspectionsDialog,
    EquipmentConstantsDialog,
    InitializeSubsystemsDialog,
    LotSummaryDialog,
    PreventiveMaintenanceDialog,
    RenameLotDialog,
    SendLotsDialog,
    SoftwareOptionsDialog,
    SystemLogDialog,
    normalized_data_transfer,
    normalized_equipment_constants,
)
from puma_ui.qt_compat import QApplication, QMessageBox, Qt
from puma_ui.recipe_store import RecipeStore, SCHEMA_VERSION


class SystemUtilitiesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = RecipeStore(Path(self.temp_dir.name) / "recipes.json")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_equipment_constants_normalize_manual_ranges(self):
        state = normalized_equipment_constants({"poll_delay": 3, "communication_timeout": 80})
        self.assertEqual(state["poll_delay"], 15)
        self.assertEqual(state["communication_timeout"], 30)
        self.assertTrue(state["remote_wafer_handling"])

    def test_data_transfer_normalizes_port_and_service_state(self):
        state = normalized_data_transfer({"port": 99999, "running": 0, "host": "analysis"})
        self.assertEqual(state["port"], 65535)
        self.assertFalse(state["running"])
        self.assertEqual(state["host"], "analysis")

    def test_store_migrates_and_persists_utility_data(self):
        path = Path(self.temp_dir.name) / "legacy.json"
        path.write_text(json.dumps({"schema_version": 3, "recipes": [], "preferences": {}}), encoding="utf-8")
        store = RecipeStore(path)
        event = store.record_utility_event("Initialization", "Initialized: Wafer Handling")
        queued = store.save_transfer_item({"lot_id": "LOT-1", "wafer_id": "W01"})
        restored = RecipeStore(path)
        self.assertEqual(restored._data["schema_version"], SCHEMA_VERSION)
        self.assertEqual(restored.utility_events()[0], event)
        self.assertEqual(restored.list_transfer_items()[0]["id"], queued["id"])
        self.assertTrue(restored.remove_transfer_item(queued["id"]))

    def test_store_renames_lot_across_results_jobs_and_transfer_queue(self):
        self.store.save_result({"id": "r1", "lot_id": "OLD"})
        self.store.save_job({"id": "j1", "lot_id": "OLD"})
        self.store.save_transfer_item({"id": "t1", "lot_id": "OLD"})
        self.assertEqual(self.store.rename_lot("OLD", "NEW"), 3)
        self.assertEqual(self.store.get_result("r1")["lot_id"], "NEW")
        self.assertEqual(self.store.list_jobs()[0]["lot_id"], "NEW")
        self.assertEqual(self.store.list_transfer_items()[0]["lot_id"], "NEW")

    def test_initialize_subsystems_supports_all_and_selected_modes(self):
        dialog = InitializeSubsystemsDialog()
        dialog.all_subsystems.setChecked(False)
        for check in dialog.subsystems.values():
            check.setChecked(False)
        dialog.subsystems["Data Transfer"].setChecked(True)
        dialog._finish()
        self.assertEqual(dialog.result_subsystems, ["Data Transfer"])

    def test_preventive_maintenance_records_completed_tasks(self):
        dialog = PreventiveMaintenanceDialog()
        dialog.table.item(0, 0).setCheckState(Qt.Checked)
        dialog._finish()
        completed = dialog.result_state["completed"]
        self.assertIn("Inspect stage surface", completed)
        self.assertTrue(completed["Inspect stage surface"])

    def test_equipment_constants_dialog_returns_all_tabs(self):
        dialog = EquipmentConstantsDialog()
        self.assertEqual(dialog.tabs.count(), 4)
        dialog.controls["device_name"].setText("SIM-9980")
        dialog.controls["poll_delay"].setValue(20)
        dialog._finish()
        self.assertEqual(dialog.result_constants["device_name"], "SIM-9980")
        self.assertEqual(dialog.result_constants["poll_delay"], 20)

    def test_transfer_queue_retries_and_deletes_selected_lots(self):
        items = [{"id": "q1", "lot_id": "LOT-1", "wafer_id": "W01", "status": "Failed", "error": "Offline"}]
        dialog = DataTransferQueueDialog(items, {"running": True})
        dialog.table.item(0, 0).setCheckState(Qt.Checked)
        dialog._retry()
        self.assertEqual(dialog.result_items[0]["status"], "Transferred (simulated)")
        dialog.table.item(0, 0).setCheckState(Qt.Checked)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
            dialog._delete()
        self.assertEqual(dialog.result_items, [])

    def test_read_only_summary_dialogs_render_expected_rows(self):
        logs = SystemLogDialog("Daily Logs", [{"timestamp": "t", "message": "m"}])
        options = SoftwareOptionsDialog()
        lots = LotSummaryDialog([{"lot_id": "L1", "wafer_id": "W1", "defect_count": 5}])
        self.assertEqual(logs.table.rowCount(), 1)
        self.assertEqual(lots.table.rowCount(), 1)
        self.assertIn("Software Options", options.windowTitle())

    def test_delete_inspections_protects_current_recipe_and_confirms(self):
        recipes = [
            {"id": "current", "inspection": "Open"},
            {"id": "old", "inspection": "Old"},
        ]
        dialog = DeleteInspectionsDialog(recipes, current_recipe_id="current")
        self.assertFalse(bool(dialog.table.item(0, 0).flags() & Qt.ItemIsEnabled))
        dialog.table.item(1, 0).setCheckState(Qt.Checked)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
            dialog._finish()
        self.assertEqual(dialog.result_ids, ["old"])

    def test_send_and_rename_lot_dialogs_validate_results(self):
        send = SendLotsDialog(
            [{"id": "r1", "lot_id": "LOT-1", "wafer_id": "W01"}],
            "AnalysisSystem1",
        )
        send.table.item(0, 0).setCheckState(Qt.Checked)
        send._finish()
        self.assertEqual(send.result_selection["lot_ids"], ["LOT-1"])
        rename = RenameLotDialog(["LOT-1"])
        rename.new_name.setText("LOT-2")
        rename._finish()
        self.assertEqual(rename.result_names, ("LOT-1", "LOT-2"))

    def test_click_and_mark_configuration_persists_manual_options(self):
        dialog = ClickAndMarkConfigurationDialog()
        dialog.enabled.setChecked(True)
        dialog.options["auto_acquire"].setChecked(True)
        dialog.save_location.setText("C:/Images")
        dialog._finish()
        self.assertTrue(dialog.result_settings["enabled"])
        self.assertTrue(dialog.result_settings["auto_acquire"])
        self.assertEqual(dialog.result_settings["save_location"], "C:/Images")

    def test_main_window_exposes_manual_utility_menus(self):
        with patch("puma_ui.main_window.RecipeStore", return_value=self.store):
            window = PumaMainWindow()
        top_level = [action.text() for action in window.menuBar().actions()]
        self.assertIn("Utilities", top_level)
        self.assertIn("Tools", top_level)
        all_actions = []

        def collect(menu):
            for action in menu.actions():
                all_actions.append(action.text())
                if action.menu() is not None:
                    collect(action.menu())

        for action in window.menuBar().actions():
            if action.menu() is not None:
                collect(action.menu())
        self.assertIn("Equipment Constants...", all_actions)
        self.assertIn("Show Queue", all_actions)
        self.assertIn("Lot Summary", all_actions)
        for expected in (
            "Initialize System...",
            "Preventive Maintenance...",
            "Equipment Constants...",
            "Delete Inspections...",
            "Send Lots...",
            "Rename Lot...",
            "Lot Summary",
            "Click and Mark Configuration...",
            "View Configuration",
            "Show Queue",
        ):
            self.assertIn(expected, all_actions)
        window.close()

    def test_unavailable_ilink_queues_auto_transfer_result(self):
        with patch("puma_ui.main_window.RecipeStore", return_value=self.store):
            window = PumaMainWindow()
        result = self.store.save_result({
            "id": "result-1",
            "lot_id": "LOT-1",
            "wafer_id": "W01",
            "status": "Complete",
            "transfer": {"state": "Transferred"},
        })
        window._queue_unavailable_auto_transfers(
            [result],
            {"auto_transfer": True, "transfer_host": "Analysis-1"},
        )
        queue = self.store.list_transfer_items()
        self.assertEqual(len(queue), 1)
        self.assertEqual(queue[0]["status"], "Pending")
        self.assertEqual(queue[0]["destination"], "Analysis-1")
        self.assertEqual(self.store.get_result("result-1")["transfer"]["state"], "Queued")
        window.close()


if __name__ == "__main__":
    unittest.main()

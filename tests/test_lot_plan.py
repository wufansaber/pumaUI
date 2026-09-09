from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from puma_ui.qt_compat import QApplication, QMessageBox, Qt
from puma_ui.modules.lot_plan import (
    LotPlanDialog,
    default_lot_plan_state,
    lot_plan_runtime_permissions,
    normalized_lot_plan_state,
    validate_lot_plan,
)
from puma_ui.modules.run_control import (
    InspectionJobQueueDialog,
    JobSetupDialog,
    OpenLotResultRunLogDialog,
    RunLogDialog,
    RunOneWaferDialog,
    RunStatusDialog,
    default_run_setup,
)
from puma_ui.modules.results_review import ReviewWorkspace
from puma_ui.modules.system_status import CommunicationStatusDialog, normalized_communication_status


class LotPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_plan_requires_an_assignment(self):
        state = default_lot_plan_state(["Test 1"])
        self.assertIn("no tests are assigned to wafer slots", validate_lot_plan(state))

    def test_assigned_test_is_valid(self):
        state = default_lot_plan_state(["Test 1"])
        state["assignments"] = {"1": ["Test 1"]}
        self.assertEqual(validate_lot_plan(state), [])

    def test_cached_results_require_transfer_host(self):
        state = default_lot_plan_state(["Test 1"])
        state["assignments"] = {"1": ["Test 1"]}
        state["cache_lot_result"] = True
        self.assertIn(
            "lot result transfer host is required when caching is enabled",
            validate_lot_plan(state),
        )

    def test_cached_results_require_complete_target(self):
        state = default_lot_plan_state(["Test 1"])
        state["assignments"] = {"1": ["Test 1"]}
        state["cache_lot_result"] = True
        state["transfer_host"] = "K:"
        state["transfer_share"] = ""
        state["tool_type"] = ""
        errors = validate_lot_plan(state)
        self.assertIn("lot result transfer share is required when caching is enabled", errors)
        self.assertIn("tool type is required when caching is enabled", errors)

    def test_normalization_prunes_invalid_slots_and_repeat_keys(self):
        state = default_lot_plan_state(["Test 1"])
        state["assignments"] = {"1": ["Test 1"], "26": ["Test 1"]}
        state["repeat_counts"] = {"1:Test 1": 4, "26:Test 1": 9, "1:Missing": 2}
        normalized = normalized_lot_plan_state(state, ["Test 1"])
        self.assertEqual(normalized["assignments"], {"1": ["Test 1"]})
        self.assertEqual(normalized["repeat_counts"], {"1:Test 1": 4})

    def test_row_column_headers_toggle_assignments(self):
        dialog = LotPlanDialog(["Test 1", "Test 2"])
        dialog._toggle_row(0)
        self.assertEqual(set(dialog.state["assignments"]["1"]), {"Test 1", "Test 2"})
        dialog._toggle_row(0)
        self.assertNotIn("1", dialog.state["assignments"])
        dialog._toggle_column(0)
        self.assertEqual(len(dialog.state["assignments"]), 25)
        dialog._toggle_column(0)
        self.assertEqual(dialog.state["assignments"], {})

    def test_repeat_count_flows_into_run_setup(self):
        plan = default_lot_plan_state(["Test 1"])
        plan["assignments"] = {"1": ["Test 1"]}
        plan["repeat_enabled"] = True
        plan["repeat_counts"] = {"1:Test 1": 7}
        plan["unload_wafer_in_repeat_mode"] = True
        plan["protect"] = True
        recipe = {
            "tests": [{"name": "Test 1", "mode": "Random"}],
            "lot_plan": plan,
        }
        setup = default_run_setup(recipe)
        self.assertTrue(setup["repeat_test"])
        self.assertEqual(setup["repeat_count"], 7)
        self.assertTrue(setup["unload_wafer_in_repeat_mode"])
        self.assertTrue(setup["lot_plan_protected"])

    def test_apply_repeat_count_updates_all_assigned_cells(self):
        dialog = LotPlanDialog(["Test 1", "Test 2"])
        dialog.matrix.item(0, 0).setCheckState(Qt.Checked)
        dialog.matrix.item(1, 1).setCheckState(Qt.Checked)
        dialog.repeat_enabled.setChecked(True)
        dialog.repeat_count.setValue(12)
        dialog._apply_repeat_count()
        self.assertEqual(
            dialog.state["repeat_counts"],
            {"1:Test 1": 12, "2:Test 2": 12},
        )

    def test_repeat_count_change_applies_without_extra_button_click(self):
        dialog = LotPlanDialog(["Test 1", "Test 2"])
        dialog.matrix.item(0, 0).setCheckState(Qt.Checked)
        dialog.repeat_enabled.setChecked(True)
        dialog.repeat_count.setValue(9)
        self.assertEqual(dialog.state["repeat_counts"]["1:Test 1"], 9)
        dialog.matrix.item(1, 1).setCheckState(Qt.Checked)
        self.assertEqual(dialog.state["repeat_counts"]["2:Test 2"], 9)

    def test_runtime_permissions_follow_protect_and_repeat_rules(self):
        state = default_lot_plan_state(["Test 1"])
        self.assertEqual(
            lot_plan_runtime_permissions(state, runtime_mode=True),
            {"assignments": True, "settings": True, "repeat_count": True},
        )
        state["protect"] = True
        self.assertEqual(
            lot_plan_runtime_permissions(state, runtime_mode=True),
            {"assignments": False, "settings": False, "repeat_count": False},
        )
        state["repeat_enabled"] = True
        self.assertTrue(lot_plan_runtime_permissions(state, runtime_mode=True)["repeat_count"])

    def test_protected_runtime_lot_plan_allows_only_repeat_count(self):
        state = default_lot_plan_state(["Test 1"])
        state.update(
            {
                "assignments": {"1": ["Test 1"]},
                "repeat_enabled": True,
                "repeat_counts": {"1:Test 1": 6},
                "protect": True,
            }
        )
        dialog = LotPlanDialog(["Test 1"], state, runtime_mode=True)
        self.assertFalse(dialog.matrix.isEnabled())
        self.assertFalse(dialog.mode.isEnabled())
        self.assertFalse(dialog.repeat_enabled.isEnabled())
        self.assertTrue(dialog.repeat_count.isEnabled())
        self.assertTrue(dialog.apply_count.isEnabled())
        self.assertFalse(dialog.unload_repeat.isEnabled())
        self.assertFalse(dialog.protect.isEnabled())
        self.assertFalse(dialog.backup.isEnabled())
        self.assertEqual(dialog.repeat_count.value(), 6)

    def test_protected_run_one_wafer_locks_plan_but_not_repeat_count(self):
        plan = default_lot_plan_state(["Test 1"])
        plan.update(
            {
                "assignments": {"1": ["Test 1"]},
                "repeat_enabled": True,
                "repeat_counts": {"1:Test 1": 4},
                "protect": True,
            }
        )
        recipe = {
            "inspection": "Protected",
            "tests": [{"name": "Test 1", "mode": "Random"}],
            "lot_plan": plan,
        }
        dialog = RunOneWaferDialog(recipe)
        self.assertFalse(dialog.test_checks["Test 1"].isEnabled())
        self.assertFalse(dialog.repeat_test.isEnabled())
        self.assertTrue(dialog.repeat_count.isEnabled())
        self.assertEqual(dialog.repeat_count.value(), 4)
        self.assertFalse(dialog.backup.isEnabled())

    def test_job_setup_wizard_saves_multiple_inspections_and_per_slot_plan(self):
        recipes = [
            {
                "id": "primary", "inspection": "Primary", "device": "D1", "step": "S1", "status": "Valid",
                "tests": [{"name": "P1", "mode": "Random"}],
            },
            {
                "id": "secondary", "inspection": "Secondary", "device": "D1", "step": "S2", "status": "Valid",
                "tests": [{"name": "S1", "mode": "Random"}],
            },
        ]
        dialog = JobSetupDialog(recipes)
        dialog.inspection_list.item(1).setCheckState(Qt.Checked)
        dialog.primary.setCurrentIndex(dialog.primary.findData("primary"))
        for check in dialog.plan_checks.values():
            check.setChecked(False)
        dialog.plan_checks[2].setChecked(True)
        dialog.plan_wafer_ids[2].setText("W02")
        dialog.plan_repeats[2].setValue(3)
        for row in range(dialog.lot_table.rowCount()):
            recipe_id = dialog.lot_table.item(row, 0).data(Qt.UserRole)
            dialog.lot_table.item(row, 1).setText(f"LOT-{recipe_id}")
        dialog._finish()
        self.assertEqual(dialog.result_job["inspection_ids"], ["primary", "secondary"])
        self.assertEqual(dialog.result_job["primary_inspection_id"], "primary")
        self.assertEqual(dialog.result_job["slots"], [2])
        self.assertEqual(dialog.result_job["slot_plans"][0]["repeat_count"], 3)
        self.assertEqual(dialog.result_job["slot_plans"][0]["wafer_id"], "W02")

    def test_remote_job_setup_is_read_only(self):
        recipe = {
            "id": "remote", "inspection": "Remote", "status": "Valid",
            "tests": [{"name": "T1", "mode": "Random"}],
        }
        job = {
            "recipe_id": "remote",
            "inspection_ids": ["remote"],
            "primary_inspection_id": "remote",
            "remote": True,
            "slots": [1],
            "setup": {"lot_id": "REMOTE-LOT"},
            "status": "Waiting for Material",
        }
        dialog = JobSetupDialog([recipe], job)
        self.assertTrue(dialog.read_only)
        self.assertFalse(dialog.inspection_list.isEnabled())
        self.assertTrue(dialog.tabs.isEnabled())

    def test_run_log_print_creates_a_printable_copy(self):
        dialog = RunLogDialog("LOT-1", [{"time": "10:00", "level": "Info", "message": "Complete"}])
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "run-log.txt")
            with patch(
                "puma_ui.modules.run_control.dialogs.QFileDialog.getSaveFileName",
                return_value=(path, "Text Files (*.txt)"),
            ):
                dialog._print()
            text = Path(path).read_text(encoding="utf-8")
            self.assertIn("LOT-1", text)
            self.assertIn("Complete", text)
            self.assertEqual(dialog.printed_path, path)

    def test_open_lot_result_run_log_supports_manual_wildcards(self):
        dialog = OpenLotResultRunLogDialog([
            {"id": "1", "lot_id": "SAMPLE-01", "wafer_id": "W1", "inspection": "Deep"},
            {"id": "2", "lot_id": "PROD-01", "wafer_id": "W2", "inspection": "Normal"},
        ])
        self.assertEqual(len(dialog.visible_results), 2)
        dialog.search.setText("S*")
        self.assertEqual([item["id"] for item in dialog.visible_results], ["1"])
        dialog.table.selectRow(0)
        dialog._finish()
        self.assertEqual(dialog.selected_result["lot_id"], "SAMPLE-01")

    def test_run_one_wafer_disables_image_transfer_until_recipe_is_ready(self):
        recipe = {
            "inspection": "Transfer Check",
            "tests": [{"name": "Test 1", "mode": "Random"}],
        }
        dialog = RunOneWaferDialog(recipe)
        self.assertFalse(dialog.transfer_patches.isEnabled())
        self.assertFalse(dialog.transfer_hi_res.isEnabled())
        self.assertIn("Patch transfer unavailable", dialog.transfer_requirements.text())

        recipe["tests"][0]["save_image_patches"] = True
        recipe["wafer_post_processing"] = {
            "operations": [{
                "name": "Sampling",
                "enabled": True,
                "parameters": {"patch_sampling": "Smart", "hi_res_sampling": "Smart"},
            }]
        }
        ready = RunOneWaferDialog(recipe)
        self.assertTrue(ready.transfer_patches.isEnabled())
        self.assertTrue(ready.transfer_hi_res.isEnabled())

    def test_queue_start_continues_through_ready_jobs_and_skips_waiting_material(self):
        class QueueStore:
            def __init__(self, jobs):
                self.jobs = jobs

            def list_jobs(self):
                return self.jobs

            def save_job(self, job):
                return job

        jobs = [
            {"id": "1", "inspection": "A", "material_id": "MAT-A", "status": "Waiting for Start", "setup": {}},
            {"id": "2", "inspection": "B", "material_id": "MAT-B", "status": "Ready to Run", "setup": {}},
            {"id": "3", "inspection": "C", "material_id": "", "status": "Waiting for Material", "setup": {}},
        ]
        visited = []

        def run(job):
            visited.append(job["id"])
            return [{"status": "Complete", "run_log": []}]

        dialog = InspectionJobQueueDialog(QueueStore(jobs), [], run_callback=run)
        dialog.table.selectRow(0)
        dialog._start()
        self.assertEqual(visited, ["1", "2"])
        self.assertEqual([job["status"] for job in jobs], ["Complete", "Complete", "Waiting for Material"])

        dialog.table.selectRow(2)
        with patch("puma_ui.modules.run_control.dialogs.QMessageBox.warning") as warning:
            dialog._start()
        warning.assert_called_once()

    def test_snapshot_updates_live_data_and_holds_the_next_repeat(self):
        recipe = {
            "id": "snapshot-recipe",
            "inspection": "Snapshot",
            "device": "D1",
            "step": "S1",
            "tests": [{"name": "Test 1", "mode": "Random"}],
        }
        setup = default_run_setup(recipe)
        setup.update({"lot_id": "SNAP-1", "repeat_test": True, "repeat_count": 2})
        observed = {}

        def review_snapshot(_snapshot, snapshot_mode, updater):
            observed["mode"] = snapshot_mode
            first = updater()["defect_count"]
            dialog.progress_value = 96
            dialog._advance()
            observed["second"] = updater()["defect_count"]
            observed["first"] = first
            observed["held"] = dialog.pending_next_repeat
            observed["repeat_while_open"] = dialog.current_repeat

        dialog = RunStatusDialog(
            recipe,
            setup,
            snapshot_callback=review_snapshot,
            auto_start=False,
        )
        dialog.progress_value = 20
        dialog._snapshot()
        self.assertTrue(observed["mode"])
        self.assertGreater(observed["second"], observed["first"])
        self.assertTrue(observed["held"])
        self.assertEqual(observed["repeat_while_open"], 1)
        self.assertEqual(dialog.current_repeat, 2)
        self.assertFalse(dialog.pending_next_repeat)

    def test_review_update_snapshot_replaces_defects_and_disables_when_complete(self):
        initial = {
            "id": "snapshot",
            "status": "Running",
            "inspection": "Snapshot",
            "defects": [{"id": 1, "die_x": 0, "die_y": 0}],
            "defect_count": 1,
        }
        updated = {
            **initial,
            "status": "Complete",
            "snapshot_complete": True,
            "defects": [
                {"id": 1, "die_x": 0, "die_y": 0},
                {"id": 2, "die_x": 1, "die_y": 0},
            ],
            "defect_count": 2,
        }
        workspace = ReviewWorkspace(
            initial,
            snapshot_mode=True,
            snapshot_update_callback=lambda: updated,
        )
        workspace._update_snapshot()
        self.assertEqual(workspace.result["defect_count"], 2)
        self.assertFalse(workspace.update_snapshot.isEnabled())

    def test_run_failure_skips_manual_prompt_when_manual_recovery_is_disabled(self):
        recipe = {
            "id": "failure-recipe",
            "inspection": "Failure",
            "tests": [{"name": "Test 1", "mode": "Random"}],
            "manual_alignment_enabled": False,
        }
        setup = default_run_setup(recipe)
        setup.update({"lot_id": "FAIL-1", "simulate_failure": "alignment"})
        dialog = RunStatusDialog(recipe, setup, auto_start=False)
        with patch("puma_ui.modules.run_control.dialogs.QMessageBox.question") as question:
            recovered = dialog._recover_startup_failure()
        question.assert_not_called()
        self.assertFalse(recovered)
        self.assertEqual(dialog.results[-1]["status"], "Failed")
        self.assertIn("DO_MANUAL_ALIGNMENT = 0", dialog.results[-1]["failure_reason"])

    def test_communication_status_requires_secs_for_remote_control(self):
        dialog = CommunicationStatusDialog({"secs_enabled": False})
        dialog.control_mode.setCurrentText("Remote")
        with patch("puma_ui.modules.system_status.dialog.QMessageBox.warning") as warning:
            dialog._finish()
        warning.assert_called_once()
        self.assertIsNone(dialog.result_status)
        dialog.secs_enabled.setChecked(True)
        dialog.secs_host.setText("factory-host")
        dialog._finish()
        self.assertEqual(dialog.result_status["control_mode"], "Remote")
        self.assertTrue(dialog.result_status["secs_enabled"])
        self.assertEqual(normalized_communication_status(dialog.result_status)["secs_port"], 5000)


if __name__ == "__main__":
    unittest.main()

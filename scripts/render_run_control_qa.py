from __future__ import annotations

import os
from pathlib import Path
import sys

if os.name != "nt":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from puma_ui.modules.results_review import ReviewWorkspace
from puma_ui.modules.run_control import (
    InspectionJobQueueDialog,
    OpenLotResultRunLogDialog,
    RunOneWaferDialog,
    RunStatusDialog,
    default_run_setup,
)
from puma_ui.qt_compat import QApplication


def capture(widget, path: Path, width: int, height: int, app: QApplication):
    widget.resize(width, height)
    widget.show()
    app.processEvents()
    if not widget.grab().save(str(path)):
        raise RuntimeError(f"Unable to save {path}")
    widget.hide()


def recipe():
    return {
        "id": "run-qa",
        "inspection": "Deep",
        "device": "Device1",
        "step": "Metal1",
        "tests": [
            {"name": "Test 1", "mode": "Random", "save_image_patches": True},
            {"name": "Test 2", "mode": "Random", "save_image_patches": True},
        ],
        "wafer_post_processing": {
            "operations": [{
                "name": "Sampling",
                "enabled": True,
                "parameters": {
                    "patch_sampling": "Smart",
                    "hi_res_sampling": "Precision",
                },
            }]
        },
    }


class QueueStore:
    def __init__(self, jobs):
        self.jobs = jobs

    def list_jobs(self):
        return self.jobs

    def save_job(self, job):
        return job


def main():
    app = QApplication.instance() or QApplication([])
    output = Path(".artifacts/visual-qa")
    output.mkdir(parents=True, exist_ok=True)
    current_recipe = recipe()

    setup = default_run_setup(current_recipe)
    setup.update({"lot_id": "LOT-QA-001", "wafer_id": "W01"})
    run_one = RunOneWaferDialog(current_recipe, setup)
    capture(run_one, output / "run-one-wafer-760x650.png", 760, 650, app)

    status = RunStatusDialog(current_recipe, setup, auto_start=False)
    status.progress_value = 64
    status.progress.setValue(64)
    status.message.setText("Swathing wafer and collecting defects...")
    status.defects.setText("Defects detected: 46")
    status._append_log("Swathing wafer and collecting defects...")
    capture(status, output / "run-status-820x660.png", 820, 660, app)

    results = [
        {
            "id": "r1",
            "lot_id": "SAMPLE-001",
            "wafer_id": "W01",
            "inspection": "Deep",
            "created": "2026-09-08 10:15:00",
            "status": "Complete",
            "defects": [{"id": 1, "die_x": 0, "die_y": 0}],
            "defect_count": 1,
        },
        {
            "id": "r2",
            "lot_id": "PROD-002",
            "wafer_id": "W02",
            "inspection": "Normal",
            "created": "2026-09-08 10:20:00",
            "status": "Complete",
            "defects": [],
            "defect_count": 0,
        },
    ]
    selector = OpenLotResultRunLogDialog(results)
    selector.search.setText("S*")
    capture(selector, output / "open-run-log-820x500.png", 820, 500, app)

    jobs = [
        {
            "id": "j1", "inspection": "Deep", "material_id": "POD-1001",
            "cassette": "Port 1", "slots": [25, 24], "status": "Running",
            "created": "2026-09-08 10:25:00", "setup": {"lot_id": "LOT-QA-001"},
        },
        {
            "id": "j2", "inspection": "Normal", "material_id": "POD-1002",
            "cassette": "Port 2", "slots": [12], "status": "Waiting for Start",
            "created": "2026-09-08 10:27:00", "setup": {"lot_id": "LOT-QA-002"},
        },
        {
            "id": "j3", "inspection": "Deep", "material_id": "",
            "cassette": "Port 3", "slots": [1], "status": "Waiting for Material",
            "created": "2026-09-08 10:29:00", "setup": {"lot_id": "LOT-QA-003"},
        },
    ]
    queue = InspectionJobQueueDialog(QueueStore(jobs), [current_recipe])
    capture(queue, output / "inspection-job-queue-1100x680.png", 1100, 680, app)

    snapshot = status._snapshot_result()
    review = ReviewWorkspace(
        snapshot,
        current_recipe=current_recipe,
        snapshot_mode=True,
        snapshot_update_callback=status._snapshot_result,
    )
    capture(review, output / "snapshot-review-1600x900.png", 1600, 900, app)
    print("Rendered Inspection Run visual QA screenshots to", output.resolve())


if __name__ == "__main__":
    main()

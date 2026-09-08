from __future__ import annotations

import os
from pathlib import Path
import sys

if os.name != "nt":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from puma_ui.modules.system_status import (
    DataTransferQueueDialog,
    EquipmentConstantsDialog,
    LotSummaryDialog,
)
from puma_ui.qt_compat import QApplication


def capture(widget, path: Path, width: int, height: int, app: QApplication):
    widget.resize(width, height)
    widget.show()
    app.processEvents()
    if not widget.grab().save(str(path)):
        raise RuntimeError(f"Unable to save {path}")
    widget.close()


def main():
    app = QApplication.instance() or QApplication([])
    output = Path(".artifacts/visual-qa")
    output.mkdir(parents=True, exist_ok=True)

    constants = EquipmentConstantsDialog()
    capture(constants, output / "equipment-constants-780x590.png", 780, 590, app)

    queue = DataTransferQueueDialog(
        [
            {
                "id": "qa-transfer-1",
                "lot_id": "LOT-QA-001",
                "wafer_id": "W01",
                "destination": "AnalysisSystem1",
                "status": "Pending",
                "error": "ILink unavailable",
            },
            {
                "id": "qa-transfer-2",
                "lot_id": "LOT-QA-002",
                "wafer_id": "W03",
                "destination": "ArchiveHost",
                "status": "Failed",
                "error": "Connection timeout",
            },
        ],
        {"running": True},
    )
    capture(queue, output / "data-transfer-queue-900x500.png", 900, 500, app)

    summary = LotSummaryDialog(
        [
            {
                "lot_id": "LOT-QA-001",
                "wafer_id": "W01",
                "inspection": "Deep",
                "device": "Device1",
                "step": "Metal1",
                "defect_count": 143,
                "status": "Complete",
            },
            {
                "lot_id": "LOT-QA-001",
                "wafer_id": "W02",
                "inspection": "Deep",
                "device": "Device1",
                "step": "Metal1",
                "defect_count": 87,
                "status": "Aborted",
            },
        ]
    )
    capture(summary, output / "lot-summary-980x540.png", 980, 540, app)
    print("Rendered System Utilities visual QA screenshots to", output.resolve())


if __name__ == "__main__":
    main()

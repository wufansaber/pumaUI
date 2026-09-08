from __future__ import annotations

import os
from pathlib import Path
import sys

if os.name != "nt":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from puma_ui.modules.system_status import (
    ControlJobManagementDialog,
    DiskAdminDialog,
    SignalTowerDialog,
    UserAdministrationDialog,
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
    jobs = [
        {"id": "CJ-LOT-001", "lot_id": "LOT-001", "cassette": "Port 1", "status": "Running", "inspection": "Deep"},
        {"id": "CJ-LOT-002", "lot_id": "LOT-002", "cassette": "Port 2", "status": "Waiting for Material", "inspection": "Metal1"},
    ]
    control = ControlJobManagementDialog(jobs, enabled=True, reason="Control and Process Job commands are available")
    capture(control, output / "control-job-management-940x560.png", 940, 560, app)

    security = UserAdministrationDialog()
    security.username.setText("operator1")
    security.password.setText("training")
    security._add_user()
    capture(security, output / "user-administration-900x590.png", 900, 590, app)

    tower = SignalTowerDialog()
    capture(tower, output / "signal-tower-900x590.png", 900, 590, app)

    disk = DiskAdminDialog()
    disk.schedule.setCurrentText("Weekly")
    disk.delete_images.setChecked(True)
    disk.delete_lots.setChecked(True)
    capture(disk, output / "disk-admin-620x450.png", 620, 450, app)
    print("Rendered System Administration visual QA screenshots to", output.resolve())


if __name__ == "__main__":
    main()

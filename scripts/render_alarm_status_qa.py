from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from puma_ui.main_window import PumaMainWindow
from puma_ui.modules.system_status import AlarmCenterDialog
from puma_ui.qt_compat import QApplication
from puma_ui.recipe_store import RecipeStore


def capture(widget, path: Path, app: QApplication):
    widget.show()
    app.processEvents()
    if not widget.grab().save(str(path)):
        raise RuntimeError(f"Unable to save {path}")


def main():
    app = QApplication.instance() or QApplication([])
    output = Path(".artifacts/system-status")
    output.mkdir(parents=True, exist_ok=True)
    alarms = [
        {
            "name": "Stage Interlock",
            "category": "Safety",
            "clearable": False,
            "status": "Active",
        },
        {
            "name": "Transfer Error Alarm",
            "category": "SECS",
            "clearable": True,
            "status": "Active",
        },
    ]
    dialog = AlarmCenterDialog(alarms)
    dialog.active_only.setChecked(False)
    dialog.tabs.setCurrentIndex(0)
    capture(dialog, output / "safety-interlocks.png", app)
    dialog.tabs.setCurrentIndex(1)
    capture(dialog, output / "secs-alarms.png", app)
    dialog.close()

    with tempfile.TemporaryDirectory() as directory:
        store = RecipeStore(Path(directory) / "recipes.json", default_recipes=[])
        store.update_preferences(
            {
                "communication": {
                    "control_mode": "Remote",
                    "secs_enabled": True,
                    "secs_connected": True,
                    "ilink_enabled": True,
                    "ilink_connected": True,
                },
                "data_transfer": {"running": True},
            }
        )
        with patch("puma_ui.main_window.RecipeStore", return_value=store):
            window = PumaMainWindow()
        window.resize(1500, 820)
        window.wafer_runtime_state.update(
            {
                "wafer_loaded": True,
                "wafer_aligned": True,
                "wafer_source_port": 1,
                "wafer_source_slot": 25,
            }
        )
        window.set_alarm_event("Transfer Error Alarm")
        window._refresh_wafer_status()
        window._refresh_communication_status()
        capture(window, output / "main-statusbar.png", app)
        window.close()


if __name__ == "__main__":
    main()

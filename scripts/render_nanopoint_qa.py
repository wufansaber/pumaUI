from __future__ import annotations

import os
from pathlib import Path
import sys


if os.name != "nt":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from puma_ui.qt_compat import QApplication
from puma_ui.modules.inspection_tests.care_areas import CareAreaImportDialog
from puma_ui.modules.inspection_tests.nanopoint import NanoPointImageTemplatesDialog


def save(widget, path: Path):
    widget.show()
    QApplication.processEvents()
    if not widget.grab().save(str(path)):
        raise RuntimeError(f"Unable to save {path}")
    widget.close()


def main():
    app = QApplication.instance() or QApplication([])
    output = ROOT / ".artifacts" / "nanopoint-qa"
    output.mkdir(parents=True, exist_ok=True)
    state = {
        "defect_source": "DemoLot.json",
        "reference_die": [3, 8],
        "images_grabbed": True,
        "poi_search_complete": True,
        "templates": [
            {
                "name": "Weak Bridge",
                "confidence": 0.942,
                "uniqueness": 0.913,
                "search_threshold": 0.82,
                "search": True,
                "class_code": 27,
                "location": [0.21, -0.14],
                "linked_care_area": "CAG Weak Bridge",
                "has_patch_images": True,
                "has_sem_image": True,
                "sem": {"path": "sem-17.png", "fov_um": 25.0},
                "flips": ["Horizontal"],
            },
            {
                "name": "Contact Void",
                "confidence": 0.918,
                "uniqueness": 0.887,
                "search_threshold": 0.78,
                "search": True,
                "class_code": 31,
                "location": [0.32, 0.41],
                "linked_care_area": "Entire Die",
                "has_patch_images": True,
                "has_sem_image": False,
            },
        ],
    }
    templates = NanoPointImageTemplatesDialog(
        state,
        care_area_names=["Entire Die", "CAG Weak Bridge"],
        wafer_loaded=True,
        wafer_aligned=True,
        light_trained=True,
        premap_defined=True,
    )
    templates.resize(1280, 760)
    templates.table.selectRow(0)
    save(templates, output / "nanopoint-templates.png")

    import_dialog = CareAreaImportDialog("Random")
    import_dialog.import_type.setCurrentText("NP Design Care Area")
    import_dialog.path.setText("DeviceA_Metal1.rlf")
    import_dialog.groups_by_step = {"Metal 1": ["Logic", "Memory", "Scribe"]}
    import_dialog.step.setText("Metal 1")
    import_dialog._populate_groups("Metal 1")
    save(import_dialog, output / "npca-selection.png")
    print(f"Rendered NanoPoint QA screenshots to {output.resolve()}")
    app.quit()


if __name__ == "__main__":
    main()

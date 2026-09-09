from __future__ import annotations

import os
from pathlib import Path
import sys


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from puma_ui.modules.inspection_tests.care_areas import CareAreasDialog
from puma_ui.modules.inspection_tests.dialog import TestsSetupDialog, default_test
from puma_ui.modules.inspection_tests.segmentation import SegmentationImageGrabDialog
from puma_ui.modules.recipe_lifecycle import SaveInspectionDialog
from puma_ui.qt_compat import QApplication
from puma_ui.recipe_store import RecipeStore


def save(widget, path):
    widget.show()
    QApplication.processEvents()
    if not widget.grab().save(str(path)):
        raise RuntimeError(f"Unable to render {path}")
    widget.close()


def main():
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    output = ROOT / ".artifacts" / "manual-completion"
    output.mkdir(parents=True, exist_ok=True)
    store = RecipeStore(output / "recipes.json", default_recipes=[])
    recipe = store.save_recipe({
        "inspection": "Production_9980", "device": "Device-A", "step": "Metal-1",
        "status": "Valid", "approval": "Production", "recipe_type": "Normal",
    })
    store.save_recipe({
        "inspection": "Engineering_9980", "device": "Device-A", "step": "Metal-2",
        "status": "Incomplete", "approval": "Engineering", "recipe_type": "FEM",
    })
    save(SaveInspectionDialog(recipe, recipe_store=store), output / "01-save-inspection-browser.png")

    test = default_test(1)
    test["mode"] = "Random"
    test["care_areas"]["groups"] = [{
        "name": "Critical Array", "kind": "CA", "enabled": True,
        "areas": [[0.08, 0.10, 0.32, 0.22], [0.52, 0.48, 0.24, 0.18]],
    }]
    test["sample_plan"]["selected_count"] = 124
    tests = TestsSetupDialog([test], wafer_loaded=True, wafer_aligned=True)
    info_row = next(row for row, item in enumerate(tests.PARAMETER_ROWS) if item[1] == "test_info")
    tests._matrix_cell_clicked(info_row, 0)
    save(tests, output / "02-tests-test-info.png")

    care = CareAreasDialog(test["care_areas"], wafer_aligned=True)
    care.active_group = 0
    care._refresh()
    care.group_tabs.setCurrentIndex(1)
    care._measurement_completed((0.1, 0.1), (0.5, 0.4))
    save(care, output / "03-care-areas-advanced.png")

    segmentation = SegmentationImageGrabDialog([
        {"x": 0.25, "y": 0.30, "grabbed": True, "image_id": "SEG-001"},
        {"x": 0.65, "y": 0.60, "grabbed": True, "image_id": "SEG-002"},
    ])
    segmentation.image_channel.setCurrentText("Channel 3")
    segmentation.image_mode.setCurrentText("Overlay")
    segmentation.image_zoom.setValue(175)
    segmentation.measure.setChecked(True)
    save(segmentation, output / "04-segmentation-image-tools.png")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

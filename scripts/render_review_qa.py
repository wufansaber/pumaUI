from __future__ import annotations

import os
from pathlib import Path
import sys

if os.name != "nt":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from puma_ui.modules.results_review import (
    OpticsSelectorDialog,
    ReviewWorkspace,
    SensitivityTunerDialog,
    STNEFTunerDialog,
)
from puma_ui.modules.run_control import generate_inspection_result
from puma_ui.qt_compat import QApplication, Qt


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
    recipe = {
        "id": "qa-recipe",
        "inspection": "Deep",
        "device": "Device1",
        "step": "Metal1",
        "tests": [{"name": "Test 1", "mode": "Random"}, {"name": "Test 2", "mode": "Random"}],
    }
    result = generate_inspection_result(
        recipe,
        {
            "lot_id": "QA-LOT-001",
            "wafer_id": "W01",
            "selected_tests": ["Test 1", "Test 2"],
            "collect_sensitivity_data": True,
        },
    )
    result["review_mode"] = "Loaded Wafer"
    result["defects"][0]["marked"] = True

    review = ReviewWorkspace(result, current_recipe=recipe)
    capture(review, output / "review-1920x1080.png", 1920, 1080, app)

    advanced = ReviewWorkspace(result, current_recipe=recipe)
    advanced.layout_mode.setCurrentText("Advanced Classify")
    capture(advanced, output / "advanced-classify-980x650.png", 980, 650, app)

    optics = OpticsSelectorDialog(result, recipe)
    optics._add_mode()
    optics._analyze()
    capture(optics, output / "optics-selector-980x680.png", 980, 680, app)

    tuner = SensitivityTunerDialog(result, recipe)
    tuner.value.setValue(120)
    tuner._commit()
    capture(tuner, output / "sensitivity-tuner-1120x720.png", 1120, 720, app)

    st_nef = STNEFTunerDialog(result)
    st_nef._generate_starter_tree({
        "attributes": ["Primary Ch Intensity", "Area"],
        "partitions": [{"name": "Defect", "classes": [1]}, {"name": "Nuisance", "classes": [0]}],
    })
    capture(st_nef, output / "st-nef-tuner-1180x720.png", 1180, 720, app)

    print("Rendered Review visual QA screenshots to", output.resolve())


if __name__ == "__main__":
    main()

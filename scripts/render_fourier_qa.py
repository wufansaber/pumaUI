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

try:
    from PySide6.QtTest import QTest
except ImportError:
    from PyQt5.QtTest import QTest

from puma_ui.modules.inspection_tests.fourier import (
    FourierFilterTrainingDialog,
    FourierImagesDialog,
    FourierSamplePlanDialog,
    RodPositionsDialog,
    default_fourier_state,
)


def capture(widget, path: Path):
    widget.show()
    QApplication.processEvents()
    QTest.qWait(80)
    widget.repaint()
    QApplication.processEvents()
    if not widget.grab().save(str(path)):
        raise RuntimeError(f"Unable to save {path}")
    widget.close()


def main():
    app = QApplication.instance() or QApplication([])
    output = ROOT / ".artifacts" / "fourier-qa"
    output.mkdir(parents=True, exist_ok=True)
    state = default_fourier_state()
    state["boxes"] = [
        {"x": 0.28, "y": 0.20, "width": 0.22, "height": 0.32, "channels": [1, 2, 3]},
        {"x": 0.30, "y": 0.58, "width": 0.18, "height": 0.16, "channels": [1, 2]},
    ]
    training = FourierFilterTrainingDialog(
        state,
        incidence_angle="Normal",
        test_name="Test 1",
    )
    training._new_box()
    training.stage_position = (0.20, 0.16)
    training.first_corner = training.stage_position
    training.preview.stage_position = training.stage_position
    training.preview.first_corner = training.first_corner
    capture(training, output / "fourier-training-mark.png")

    sample = FourierSamplePlanDialog([0, 0])
    capture(sample, output / "fourier-sample-plan.png")

    rods = RodPositionsDialog(
        state["rods"],
        boxes=state["boxes"],
        incidence_angle="Normal",
        enforce_specular_block=True,
    )
    rods._analyze()
    capture(rods, output / "fourier-rod-positions.png")

    images = FourierImagesDialog(0)
    capture(images, output / "fourier-images.png")
    print(f"Rendered Fourier QA screenshots to {output}")
    app.processEvents()


if __name__ == "__main__":
    main()

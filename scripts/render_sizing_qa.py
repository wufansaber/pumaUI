from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile

if os.name != "nt":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from puma_ui.modules.sizing import (
    HistogramDialog,
    KlarfOptionsDialog,
    LotResultReaderDialog,
    MapPropertiesDialog,
    SizingRecipeDialog,
    SizingSetupTool,
)
from puma_ui.qt_compat import QApplication
from puma_ui.recipe_store import RecipeStore


def result_for_qa():
    groups = ("Small", "Medium", "Large", "Tall", "Dim", "Planar")
    defects = []
    for identifier in range(1, 73):
        reference = 0.25 + (identifier % 24) * 0.15
        group = groups[(identifier - 1) % len(groups)]
        factor = 0.82 + (identifier % 7) * 0.05
        defects.append({
            "id": identifier,
            "x": (identifier % 13) * 0.8,
            "y": (identifier % 11) * 0.9,
            "size_um": reference / 0.85,
            "computed_size_um": reference * factor,
            "reference_size_um": reference,
            "sizing_scale_group": group,
            "signal": 30.0 + identifier * 2.5,
            "test": "Test 1",
            "polarity": "Dark" if identifier % 4 == 0 else "Bright",
        })
    return {
        "id": "sst-qa",
        "lot_id": "LOT-SIZING-QA",
        "wafer_id": "W01",
        "inspection": "Deep",
        "status": "Complete",
        "defects": defects,
    }


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
    with tempfile.TemporaryDirectory() as directory:
        store = RecipeStore(Path(directory) / "recipes.json")
        tool = SizingSetupTool(store, initial_result=result_for_qa())
        capture(tool, output / "sizing-workspace-1180x760.png", 1180, 760, app)

        properties = MapPropertiesDialog(tool.state, tool.state["active_map_id"])
        properties.tabs.setCurrentIndex(2)
        capture(properties, output / "sizing-map-properties-780x560.png", 780, 560, app)

        second_result = dict(result_for_qa(), id="sst-qa-2", wafer_id="W02")
        lot_reader = LotResultReaderDialog([result_for_qa(), second_result])
        lot_reader._show_page(2)
        capture(lot_reader, output / "sizing-lot-reader-choose-test-720x460.png", 720, 460, app)

        klarf_reader = KlarfOptionsDialog("reference.klarf", [result_for_qa(), second_result])
        klarf_reader._show_page(4)
        capture(klarf_reader, output / "sizing-klarf-size-field-640x420.png", 640, 420, app)

        recipe = SizingRecipeDialog(tool.state["recipe"])
        capture(recipe, output / "sizing-recipe-650x460.png", 650, 460, app)

        histogram = HistogramDialog(tool.state, "Size")
        histogram.cdf.setChecked(True)
        capture(histogram, output / "sizing-histogram-780x590.png", 780, 590, app)
    print("Rendered Sizing visual QA screenshots to", output.resolve())


if __name__ == "__main__":
    main()

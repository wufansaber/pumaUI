from __future__ import annotations

import os
from pathlib import Path
import sys

if os.name != "nt":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from puma_ui.modules.design_based_binning import (
    DBBSetupDialog,
    DBCSetupDialog,
    DesignRegistrationDialog,
    default_dbb_state,
)
from puma_ui.modules.results_review import ReviewWorkspace
from puma_ui.modules.run_control import generate_inspection_result
from puma_ui.qt_compat import QApplication


def capture(widget, path: Path, width: int, height: int, app: QApplication):
    widget.resize(width, height)
    widget.show()
    app.processEvents()
    if not widget.grab().save(str(path)):
        raise RuntimeError(f"Unable to save {path}")
    widget.close()


def qa_state():
    state = default_dbb_state()
    state.update({
        "rdf_file": "Device1_Metal1.rdf",
        "rdf_device": "Device1",
        "inspection_layer": "Metal1",
        "registered": True,
        "registration_verified": True,
        "rdf_sites": [(100, 100), (600, 620)],
        "low_mag_sites": [(100, 100), (600, 620)],
        "high_mag_sites": [(100, 100), (600, 620)],
        "enabled": True,
        "dbc_enabled": True,
        "dbc_library": "Metal1_Production.dbc",
        "dbg_enabled": True,
        "dci_enabled": True,
        "pci_enabled": True,
        "design_attributes_enabled": True,
        "pattern_density_1": True,
        "transfer_clip_images": True,
        "dbc_bins": [{"name": "Contact", "class_code": 120}],
    })
    return state


def main():
    app = QApplication.instance() or QApplication([])
    output = Path(".artifacts/visual-qa")
    output.mkdir(parents=True, exist_ok=True)
    state = qa_state()

    registration = DesignRegistrationDialog(state, recipe_device="Device1")
    registration.tabs.setCurrentIndex(1)
    capture(registration, output / "dbb-design-registration-1000x680.png", 1000, 680, app)

    for index, name in enumerate(("general", "dbg", "design-attributes", "sampling")):
        setup = DBBSetupDialog(state)
        setup.tabs.setCurrentIndex(index)
        capture(setup, output / f"dbb-setup-{name}-980x700.png", 980, 700, app)

    dbc = DBCSetupDialog(state)
    dbc._add_example("RDF HotSpot")
    dbc._create_bin()
    capture(dbc, output / "dbc-setup-980x620.png", 980, 620, app)

    recipe = {
        "id": "dbb-qa",
        "inspection": "Deep",
        "device": "Device1",
        "step": "Metal1",
        "tests": [{"name": "Test 1"}],
        "dbb": state,
    }
    result = generate_inspection_result(
        recipe,
        {"lot_id": "DBB-QA", "wafer_id": "W01", "selected_tests": ["Test 1"]},
    )
    review = ReviewWorkspace(result, current_recipe=recipe)
    review.map_tabs.setCurrentIndex(1)
    capture(review, output / "dbb-review-design-1600x900.png", 1600, 900, app)
    print("Rendered DBB visual QA screenshots to", output.resolve())


if __name__ == "__main__":
    main()

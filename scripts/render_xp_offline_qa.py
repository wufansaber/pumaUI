from __future__ import annotations

import os
from pathlib import Path
import sys

if os.name != "nt":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from puma_ui.modules.xp_offline import (
    CAGEditorDialog,
    GDS2CAConverterDialog,
    RecipeComparatorDialog,
    RDSManagerDialog,
    XPRecipeGeneratorDialog,
    default_xp_state,
    make_registration_site,
    rds_check_in,
)
from puma_ui.qt_compat import QApplication
from puma_ui.recipe_store import RecipeStore


def capture(widget, path: Path, width: int, height: int, app: QApplication):
    widget.resize(width, height); widget.show(); app.processEvents()
    if not widget.grab().save(str(path)):
        raise RuntimeError(f"Unable to save {path}")
    widget.close()


def sample_recipe(name="BaseRecipe", layer="Base", recipe_id="base-1"):
    return {
        "id": recipe_id, "inspection": name, "device": "DeviceA", "step": layer,
        "source": "local", "status": "Valid", "approval": "Engineering",
        "alignment": {"sites_defined": True}, "wafer_map": {"die_pattern_defined": True},
        "xp_offline": {"registration_sites": [make_registration_site("CommonMark", 1200, -850, layer)]},
        "tests": [{"name": "Test 1", "light_level": 8.5, "pixel_size": "SL815"}],
    }


def main():
    app = QApplication.instance() or QApplication([])
    output = Path(".artifacts/visual-qa"); output.mkdir(parents=True, exist_ok=True)
    store = RecipeStore(output / "xp-offline-qa-store.json")
    base = store.save_recipe(sample_recipe())
    source = store.save_recipe(sample_recipe("MetalSource", "Metal1", "source-1"))

    generator = XPRecipeGeneratorDialog(store, base)
    generator.source.setCurrentIndex(generator.source.findData(source["id"]))
    for layer in ("Metal1", "Via1", "Metal2"):
        generator.layer_name.setText(layer); generator._add_layer()
    capture(generator, output / "xp-recipe-generator-1120x680.png", 1120, 680, app)

    other = sample_recipe("ComparisonRecipe", "Metal1", "compare-1")
    other["tests"][0]["light_level"] = 10.25
    comparator = RecipeComparatorDialog([base, other])
    comparator.available.selectAll(); comparator._load()
    capture(comparator, output / "xp-recipe-comparator-1180x700.png", 1180, 700, app)

    state, _ = rds_check_in(default_xp_state(), base, user="engineer", production_approved=True)
    state, _ = rds_check_in(state, other, user="expert", production_approved=False)
    rds = RDSManagerDialog(store, base, state)
    capture(rds, output / "xp-rds-manager-920x560.png", 920, 560, app)

    converter = GDS2CAConverterDialog()
    converter.paths["Care Area GDS File"].setText("C:/Design/DeviceA_CareAreas.gds")
    converter.paths["Mapping File"].setText("C:/Design/DeviceA_Mapping.csv")
    converter.paths["Config File"].setText("C:/Design/Config.csv")
    converter.paths["Output Location"].setText("C:/RecipeComponents")
    capture(converter, output / "gds2ca-converter-820x520.png", 820, 520, app)

    groups = [
        {"name": "Array", "cag_code": 10, "region_id": 1, "kind": "CA"},
        {"name": "Periphery", "cag_code": 20, "region_id": 2, "kind": "DCA"},
        {"name": "Memory", "cag_code": 30, "region_id": 3, "kind": "CA"},
    ]
    editor = CAGEditorDialog(groups)
    capture(editor, output / "cag-editor-760x520.png", 760, 520, app)
    print("Rendered XP Offline Setup visual QA screenshots to", output.resolve())


if __name__ == "__main__":
    main()

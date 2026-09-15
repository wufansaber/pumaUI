from __future__ import annotations

import os
from pathlib import Path
import sys


if os.name != "nt":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from puma_ui.modules.inspection_tests.care_areas import (
    AutoCareAreaDialog,
    CareAreasDialog,
    aca_dram_example,
    generate_page_break_groups,
)
from puma_ui.qt_compat import QApplication


def save(widget, path: Path):
    widget.show()
    QApplication.processEvents()
    if not widget.grab().save(str(path)):
        raise RuntimeError(f"Unable to save {path}")
    widget.close()


def main():
    app = QApplication.instance() or QApplication([])
    output = ROOT / ".artifacts" / "aca-qa"
    output.mkdir(parents=True, exist_ok=True)
    example = aca_dram_example()

    editor = AutoCareAreaDialog()
    editor._load_example()
    editor._generate()
    editor.resize(1080, 680)
    save(editor, output / "aca-dram-generation.png")

    children = generate_page_break_groups(
        example["search_area"], example["training_area"], example["name"]
    )
    parent = {
        "name": example["name"],
        "kind": "ACA",
        "threshold": "Default",
        "status": "OK",
        "enabled": True,
        "show": True,
        "areas": [example["search_area"]],
        "registered": True,
        "verified": True,
        "aca": {
            "search_area": example["search_area"],
            "training_area": example["training_area"],
            "use_test_optics": example["use_test_optics"],
            "skip_fourier_filter": example["skip_fourier_filter"],
            "cib_parameters": example["cib_parameters"],
            "page_breaks_generated": True,
        },
    }
    groups = CareAreasDialog(
        {"groups": [parent, *children]},
        wafer_aligned=True,
        test_name="DRAM Array Test",
    )
    groups.resize(1400, 860)
    groups.groups.selectRow(0)
    save(groups, output / "aca-groups-result.png")
    print(f"Rendered ACA QA screenshots to {output.resolve()}")
    app.quit()


if __name__ == "__main__":
    main()

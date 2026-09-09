from __future__ import annotations

import os
from pathlib import Path
import sys

if os.name != "nt":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from puma_ui.qt_compat import QApplication
from puma_ui.main_window import (
    CareAreasPreview,
    OverviewPreviewDialog,
    PumaMainWindow,
    SamplePlanPreview,
)
from puma_ui.modules.inspection_tests import CareAreasDialog
from puma_ui.modules.recipe_lifecycle import InspectionPropertiesDialog
from puma_ui.modules.show_wafer import ShowWaferPanel
from puma_ui.modules.wafer_alignment.dialogs import AlignmentMenuDialog, AutoSiteSelectionDialog
from puma_ui.modules.wafer_handling.dialog import WaferHandlingDialog
from puma_ui.modules.wafer_map.dialog import (
    EditMapDialog,
    WaferMapSetupDialog,
    WaferMapSiteSelectionDialog,
)


OUTPUT = Path(".artifacts/visual-qa")


def capture(widget, filename: str, size: tuple[int, int] | None = None) -> None:
    if size:
        widget.resize(*size)
    widget.show()
    QApplication.processEvents()
    pixmap = widget.grab()
    path = OUTPUT / filename
    if not pixmap.save(str(path)):
        raise RuntimeError(f"Unable to save {path}")
    widget.close()


def main() -> None:
    app = QApplication.instance() or QApplication([])
    OUTPUT.mkdir(parents=True, exist_ok=True)

    handling = WaferHandlingDialog(
        recipe={
            "alignment": {"sites_defined": True},
            "wafer_properties": {"type": "Patterned", "laser_power_sensitive": True},
        }
    )
    handling.load_carrier(2)
    handling.select_port(1)
    handling.select_slot(1, 25)
    handling.read_id_check.setChecked(True)
    handling._load_and_align()
    capture(handling, "wafer-handling-900x720.png", (900, 720))

    show_wafer = ShowWaferPanel()
    show_wafer.set_visible_ports("3")
    capture(show_wafer, "show-wafer-920x720.png", (920, 720))

    wafer_map = WaferMapSetupDialog(state={
        "die_pattern_defined": True,
        "die_value_mode": "die_pitch",
        "die_pitch_width": 5100.1,
        "die_pitch_height": 16600.2,
        "die_count": 724,
        "scribe_lines_defined": True,
        "scribe_x": 99.9,
        "scribe_y": 100.2,
        "origin_die": [28, 28],
        "invalid_die": [[4, 4], [52, 52]],
        "reticle_qualification": True,
        "reticle_width": 3,
        "reticle_height": 1,
        "reference_die": [9, 29],
    })
    capture(wafer_map, "wafer-map-1160x820.png", (1160, 820))

    site_selection = WaferMapSiteSelectionDialog("wafer_map")
    for _ in range(3):
        site_selection._mark_site()
    capture(site_selection, "wafer-map-site-selection-1120x880.png", (1120, 880))

    edit_map = EditMapDialog(valid_die_count=2714)
    edit_map.edge_enabled.setChecked(True)
    edit_map._apply_edge_boundary()
    edit_map._apply_die_action((18, 16))
    capture(edit_map, "edit-map-1120x870.png", (1120, 870))

    alignment = AlignmentMenuDialog(alignment_state={
        "sites_defined": True,
        "mode": "BF",
        "method": "Interactive",
        "_test_optics_defined": True,
        "_manual_alignment_enabled": True,
        "_alignment_failed": True,
    })
    alignment.image_display._set_bf_magnification("High Mag")
    capture(alignment, "alignment-dual-screen-bf-high-mag-1600x820.png", (1600, 820))

    auto_alignment = AutoSiteSelectionDialog()
    for _ in range(3):
        auto_alignment._mark_die_corner()
    capture(auto_alignment, "alignment-auto-quality-1360x760.png", (1360, 760))

    care_areas = CareAreasDialog(
        state={
            "setup_review_defects": [
                {"id": 1, "x": 0.25, "y": 0.25, "marked": True},
                {"id": 2, "x": 0.72, "y": 0.68, "marked": True},
            ],
        },
        defect_data={"name": "Engineering_DOI"},
        wafer_aligned=True,
    )
    care_areas._hot_spots()
    capture(care_areas, "care-areas-setup-review-1320x790.png", (1320, 790))

    for filename, size in [
        ("main-window-min-1180x760.png", (1180, 760)),
        ("main-window-1920x1080.png", (1920, 1080)),
    ]:
        main_window = PumaMainWindow()
        recipes = main_window.recipe_store.list_recipes()
        if recipes:
            main_window._set_current_recipe(recipes[0])
        capture(main_window, filename, size)

    overview = PumaMainWindow()
    recipe = overview.recipe_store.new_recipe()
    recipe.update({
        "inspection": "Reference_Overview",
        "status": "Valid",
        "dirty": True,
        "alignment": {"sites_defined": True, "status": "Nonoptimal"},
        "wafer_map": {
            "die_pattern_defined": True,
            "die_count": 724,
            "die_pitch_width": 5100.1,
            "die_pitch_height": 16600.2,
            "scribe_x": 99.9,
            "scribe_y": 100.2,
            "die_corner_adjustment_required": True,
        },
    })
    overview._set_current_recipe(recipe)
    overview.recipe_overview_sections["Recipe Properties"].set_expanded(True)
    overview.recipe_overview_sections["Wafer Layout"].set_expanded(True)
    overview.recipe_overview_sections["Test 1"].set_expanded(False)
    capture(overview, "recipe-overview-status-links-1500x760.png", (1500, 760))

    properties = InspectionPropertiesDialog(recipe)
    capture(properties, "inspection-properties-620x440.png")

    navigation = PumaMainWindow()
    navigation._navigation_history.extend(["tests", "test_fourier_filter"])
    navigation._navigation_index = 2
    navigation._update_navigation_strip("test_fourier_filter")
    capture(navigation, "navigation-tests-fourier-1500x760.png", (1500, 760))

    inspection_workspace = PumaMainWindow()
    inspection_workspace._navigate_to("select_inspection")
    capture(
        inspection_workspace,
        "workspace-select-inspection-1500x820.png",
        (1500, 820),
    )

    wafer_map_workspace = PumaMainWindow()
    wafer_map_workspace._navigate_to("wafer_map")
    capture(
        wafer_map_workspace,
        "workspace-wafer-map-1500x820.png",
        (1500, 820),
    )

    capture(
        OverviewPreviewDialog("Care Area Image", CareAreasPreview(260, 430)),
        "care-area-overview-zoom.png",
    )
    capture(
        OverviewPreviewDialog("Sample Plan Wafermap", SamplePlanPreview(430)),
        "sample-plan-overview-zoom.png",
    )
    app.quit()


if __name__ == "__main__":
    main()

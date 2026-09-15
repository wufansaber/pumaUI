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
from puma_ui.modules.inspection_tests.care_areas import ApplyOffsetDialog, CareAreasDialog
from puma_ui.modules.inspection_tests.light_training import (
    LightHistogramDialog,
    LightSamplePlanDialog,
    LightTrainingDialog,
)
from puma_ui.modules.inspection_tests.sample_plan import RowPatternDialog, SamplePlanDialog
from puma_ui.modules.inspection_tests.sensitivity import SensitivityDialog
from puma_ui.modules.inspection_tests import default_test
from puma_ui.modules.lot_plan import LotPlanAdvancedOptionsDialog, LotPlanDialog
from puma_ui.modules.run_control.dialogs import RunStatusDialog
from puma_ui.modules.wafer_post_processing import WaferPostProcessingDialog
from puma_ui.modules.results_review.dialogs import DefectFilterDialog, WaferDataTransferDialog
from puma_ui.modules.inspection_tests.segmentation import (
    SegmentationDialog,
    SegmentationSetupDialog,
    SingleDieInspectionDialog,
)


def save(widget, path: Path):
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
    output = ROOT / ".artifacts" / "care-light-qa"
    output.mkdir(parents=True, exist_ok=True)

    groups = [
        {"name": "Array", "areas": [[0.10, 0.20, 0.30, 0.20]]},
        {"name": "Logic", "areas": [[0.52, 0.38, 0.24, 0.32]]},
    ]
    offset = ApplyOffsetDialog(groups, [0, 1], [5000.0, 10000.0])
    offset.offset_x.setValue(250.0)
    offset.offset_y.setValue(-1000.0)
    offset._mark_site()
    save(offset, output / "apply-offset-marked.png")

    care_workspace = CareAreasDialog(
        {
            "groups": [
                {
                    "name": "Hot Spot 1",
                    "kind": "CA",
                    "threshold": "R1",
                    "status": "OK",
                    "enabled": True,
                    "cag_code": 0,
                    "show": True,
                    "areas": [[0.10, 0.08, 0.28, 0.18], [0.56, 0.42, 0.22, 0.16]],
                    "registered": True,
                    "verified": True,
                },
                {
                    "name": "Cave Area",
                    "kind": "DCA",
                    "threshold": "Default",
                    "status": "OK",
                    "enabled": True,
                    "cag_code": 1,
                    "show": True,
                    "areas": [[0.32, 0.55, 0.30, 0.24]],
                    "registered": True,
                    "verified": True,
                },
            ],
            "thresholds": [
                {"name": "Default", "algorithm": "HLAT", "threshold": 45.0},
                {"name": "R1", "algorithm": "HLAT", "threshold": 62.0},
            ],
        },
        defect_data={
            "defects": [
                {"id": 1, "x": 0.22, "y": 0.31, "class_code": 10},
                {"id": 2, "x": 0.68, "y": 0.58, "class_code": 20},
            ]
        },
        wafer_aligned=True,
        test_name="Test 1",
    )
    care_workspace.resize(1440, 860)
    care_workspace._refresh()
    save(care_workspace, output / "care-areas-workspace.png")

    care_areas = {
        "groups": [
            {
                "name": "Array",
                "kind": "Care Area",
                "enabled": True,
                "areas": [[0.15, 0.18, 0.65, 0.55]],
            }
        ]
    }
    light = LightTrainingDialog(
        focus_mode="Active Die",
        care_areas=care_areas,
        die_size_um=[5000.0, 10000.0],
    )
    light.state["noise_box_group"] = "Array"
    light.resize(1100, 700)
    light._refresh()
    save(light, output / "light-training.png")

    histogram = LightHistogramDialog(
        light.state["channels"],
        dynamic_range=light.state["dynamic_range"],
        algorithm=light.state["algorithm"],
        endpoint_mode=light.state["endpoint_mode"],
        high_endpoint=light.state["high_endpoint"],
        test_name="Test 1",
        sample_dies=light.state["sample_dies"],
    )
    histogram.resize(1120, 700)
    save(histogram, output / "light-histogram.png")

    light_sample_plan = LightSamplePlanDialog(
        light.state["sample_dies"],
        test_name="Test 1",
    )
    light_sample_plan.edge_enabled.setChecked(True)
    light_sample_plan._apply_edge_exclusion()
    light_sample_plan.resize(1120, 740)
    save(light_sample_plan, output / "light-sample-plan.png")

    segmentation = SegmentationDialog(
        {"sites": [{"x": 0.42, "y": 0.36, "grabbed": True}]},
        care_groups=care_areas["groups"],
        wafer_ready=True,
    )
    segmentation.resize(1050, 680)
    save(segmentation, output / "segmentation-menu.png")

    segmentation_setup = SegmentationSetupDialog({}, care_areas["groups"])
    segmentation_setup.segmentation_type.setCurrentText("Projection Based Segmentation")
    segmentation_setup._add_break("X")
    segmentation_setup._add_break("Y")
    segmentation_setup.resize(1200, 760)
    save(segmentation_setup, output / "segmentation-setup.png")

    sdi = SingleDieInspectionDialog({}, care_areas["groups"])
    sdi.table.cellWidget(0, 1).setChecked(True)
    sdi.table.cellWidget(0, 2).setCurrentText("Force Vertical")
    sdi._measure()
    sdi.resize(1250, 720)
    save(sdi, output / "single-die-inspection.png")

    sample = SamplePlanDialog(inner_die_defined=True)
    sample.inspection_type.setCurrentText("Partial Die")
    sample.mode_buttons[1].setChecked(True)
    sample._outside()
    sample.resize(1150, 740)
    save(sample, output / "sample-plan.png")

    row_pattern = RowPatternDialog(
        {
            "row_offset": 2,
            "row_interval": 5,
            "row_count": 2,
            "row_pattern_method": "Number of rows",
            "row_percentage": 40,
        }
    )
    save(row_pattern, output / "sample-plan-row-pattern.png")

    sensitivity = SensitivityDialog(
        region_names=["Array", "Logic", "Periphery"],
        feature_vector_version="2.0",
    )
    sensitivity.resize(1360, 780)
    save(sensitivity, output / "sensitivity-segmentation.png")

    sensitivity = SensitivityDialog(
        region_names=["Array", "Logic", "Periphery"],
        feature_vector_version="2.0",
    )
    primary_sdi = sensitivity.state["single_die_inspection"]["primary"]
    primary_sdi["run_sdi"] = True
    primary_sdi["run_cf_sdi"] = True
    primary_sdi["channels"][0]["segments"][0]["run"] = True
    primary_sdi["channels"][1]["segments"][0]["run"] = True
    primary_sdi["fusion"]["CF12"]["segments"][0]["enabled"] = True
    primary_sdi["fusion"]["CF12"]["segments"][0]["mask"] = "Ch1+Ch2"
    sensitivity.tabs.setCurrentIndex(1)
    sensitivity._populate()
    sensitivity.resize(1360, 880)
    save(sensitivity, output / "sensitivity-parameters.png")

    lot_plan = LotPlanDialog(
        ["Test 1", "Array Defects", "Edge Review"],
        {
            "assignments": {"1": ["Test 1", "Array Defects"], "2": ["Edge Review"]},
            "repeat_enabled": True,
            "mode": "Repeat Mode",
            "repeat_counts": {"1:Test 1": 5, "1:Array Defects": 5, "2:Edge Review": 5},
        },
    )
    lot_plan.resize(1200, 760)
    save(lot_plan, output / "lot-plan.png")
    lot_advanced = LotPlanAdvancedOptionsDialog(True)
    save(lot_advanced, output / "lot-plan-advanced.png")

    wpp = WaferPostProcessingDialog(test_count=3)
    wpp.state["operations"][0]["enabled"] = True
    wpp._populate_operations("Venn")
    wpp.resize(1280, 760)
    save(wpp, output / "wafer-post-processing.png")

    review_result = {
        "defects": [
            {"id": 1, "venn_id": 1, "multi_test_duplicate": False, "ido_rough_code": "R1", "ido_rough_group": "G1"},
            {"id": 2, "venn_id": 1, "multi_test_duplicate": True, "ido_rough_code": "R2", "ido_rough_group": "G1"},
            {"id": 3, "venn_id": 2, "multi_test_duplicate": False, "ido_rough_code": "R1", "ido_rough_group": "G2"},
        ]
    }
    venn_filter = DefectFilterDialog(review_result)
    venn_filter.tabs.setCurrentIndex(1)
    save(venn_filter, output / "review-multitest-duplicates.png")

    transfer = WaferDataTransferDialog(review_result, review_result["defects"][:2])
    save(transfer, output / "send-current-wafer.png")

    class_filter = DefectFilterDialog(review_result)
    class_filter.tabs.setCurrentIndex(3)
    class_filter.resize(980, 650)
    save(class_filter, output / "review-ido-class-filter.png")

    ido_test = default_test(1)
    ido_test.update({
        "run_ido": True,
        "save_feature_vectors": True,
        "ido_classifier": {"name": "Production iDO", "type": "iDO"},
    })
    run_status = RunStatusDialog(
        {"inspection": "iDO Production", "tests": [ido_test]},
        {"lot_id": "LOT-IDO", "wafer_id": "W01", "selected_tests": ["Test 1"]},
        auto_start=False,
    )
    run_status.finished = True
    save(run_status, output / "run-status-ido.png")
    print(f"Rendered Care Area and Light Training QA screenshots to {output.resolve()}")
    app.quit()


if __name__ == "__main__":
    main()

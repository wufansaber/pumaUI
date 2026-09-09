from __future__ import annotations

import unittest
from unittest.mock import patch

from puma_ui.modules.inspection_tests.care_areas import (
    AutoCareAreaDialog,
    CareAreaCoverageDialog,
    CareAreaOptionsDialog,
    DesignCareAreaRegistrationDialog,
    GrowShrinkCareAreaDialog,
    PageBreakEditDialog,
    PageBreakSortingDialog,
    SetupReviewDefectsDialog,
    ThresholdDialog,
    VerifyCareAreaDialog,
)
from puma_ui.modules.inspection_tests.dialog import ChangeTestOrientationDialog
from puma_ui.modules.inspection_tests.fourier import (
    FourierFilterTrainingDialog,
    FourierImagesDialog,
    FourierSamplePlanDialog,
    RodPositionsDialog,
    default_fourier_state,
)
from puma_ui.modules.inspection_tests.light_training import (
    ActiveRegionsDialog,
    AdvancedLightOptionsDialog,
    LightHistogramDialog,
    LightSamplePlanDialog,
    default_light_training_state,
)
from puma_ui.modules.inspection_tests.nanopoint import ReferenceDieDialog, SemFovDialog
from puma_ui.modules.inspection_tests.nef import IdoClassifierDialog, NuisanceFilterSetupDialog
from puma_ui.modules.inspection_tests.sample_plan import (
    DieInspectionPatternDialog,
    MasterSamplePlanDialog,
    SamplePlanColorsDialog,
    SamplePlanLegendDialog,
    default_sample_plan,
)
from puma_ui.modules.inspection_tests.segmentation import SegmentationImageGrabDialog, SDIImageBoxDialog
from puma_ui.modules.inspection_tests.sensitivity import (
    ChannelFusionFlavorDialog,
    CibParametersDialog,
    DecoupledChannelFusionDialog,
    VariableNoiseControlDialog,
)
from puma_ui.qt_compat import QApplication, QDialog, QMessageBox, Qt

from manual_ui_helpers import QTest, click, process_events, replace_text, select_combo, visible_button


class ManualInspectionSubdialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def show_dialog(self, dialog):
        dialog.show()
        process_events(15)
        self.assertTrue(dialog.isVisible())
        return dialog

    def test_orientation_choices_and_cancel_are_reachable(self):
        rotate = self.show_dialog(ChangeTestOrientationDialog("0 deg.", "90 deg."))
        click(visible_button(rotate, "Rotate Wafer & Continue"))
        self.assertTrue(rotate.rotate_wafer)
        self.assertEqual(rotate.result(), QDialog.Accepted)

        keep = self.show_dialog(ChangeTestOrientationDialog("0 deg.", "90 deg."))
        click(visible_button(keep, "Don't Rotate Wafer & Continue"))
        self.assertFalse(keep.rotate_wafer)
        self.assertEqual(keep.result(), QDialog.Accepted)

        cancel = self.show_dialog(ChangeTestOrientationDialog("0 deg.", "90 deg."))
        click(visible_button(cancel, "Cancel"))
        self.assertEqual(cancel.result(), QDialog.Rejected)

    def test_setup_review_mark_clear_and_save(self):
        defects = [
            {"id": 1, "x": 1.0, "y": 2.0, "class_code": 0},
            {"id": 2, "x": 3.0, "y": 4.0, "class_code": 1},
        ]
        dialog = self.show_dialog(SetupReviewDefectsDialog(defects))
        dialog.table.selectRow(0)
        click(visible_button(dialog, "Mark Selected Defects"))
        self.assertEqual(dialog.table.item(0, 0).checkState(), Qt.Checked)
        click(visible_button(dialog, "Clear Marks"))
        self.assertEqual(dialog.table.item(0, 0).checkState(), Qt.Unchecked)
        dialog.table.selectRow(1)
        click(visible_button(dialog, "Mark Selected Defects"))
        click(visible_button(dialog, "End"))
        self.assertFalse(dialog.result_defects[0]["marked"])
        self.assertTrue(dialog.result_defects[1]["marked"])

    def test_threshold_rejects_empty_selection_then_saves(self):
        dialog = self.show_dialog(ThresholdDialog({"name": "R1", "threshold": 45}))
        for channel in dialog.channels:
            if channel.isChecked():
                click(channel)
        with patch("puma_ui.modules.inspection_tests.care_areas.QMessageBox.warning") as warning:
            click(visible_button(dialog, "OK"))
        warning.assert_called_once()
        click(dialog.channels[1])
        dialog.threshold.setValue(52.0)
        click(visible_button(dialog, "OK"))
        self.assertEqual(dialog.result_threshold["channels"], [2])
        self.assertEqual(dialog.result_threshold["threshold"], 52.0)

    def test_grow_shrink_requires_name_and_returns_signed_margins(self):
        dialog = self.show_dialog(GrowShrinkCareAreaDialog("CA 1"))
        replace_text(dialog.name, "")
        with patch("puma_ui.modules.inspection_tests.care_areas.QMessageBox.warning") as warning:
            click(visible_button(dialog, "Done"))
        warning.assert_called_once()
        replace_text(dialog.name, "CA 1 Border")
        dialog.controls[0].setValue(-0.02)
        dialog.controls[2].setValue(0.03)
        click(visible_button(dialog, "Done"))
        self.assertEqual(dialog.margins()[0], -0.02)
        self.assertEqual(dialog.margins()[2], 0.03)

    def test_design_registration_and_corner_verification_gates(self):
        registration = self.show_dialog(DesignCareAreaRegistrationDialog())
        with patch("puma_ui.modules.inspection_tests.care_areas.QMessageBox.warning") as warning:
            click(visible_button(registration, "Done"))
        warning.assert_called_once()
        click(visible_button(registration, "Mark NPDCA Site"))
        click(visible_button(registration, "Mark Design Site"))
        click(visible_button(registration, "Done"))
        self.assertIsNotNone(registration.result_registration)

        verification = self.show_dialog(VerifyCareAreaDialog([[0, 0, 1, 1], [0.2, 0.2, 0.2, 0.2]]))
        self.assertFalse(verification.done_button.isEnabled())
        click(visible_button(verification, "Mark"))
        self.assertFalse(verification.done_button.isEnabled())
        click(visible_button(verification, "Mark"))
        self.assertTrue(verification.done_button.isEnabled())
        click(verification.done_button)

    def test_auto_care_area_rejects_bad_geometry_then_generates(self):
        dialog = self.show_dialog(AutoCareAreaDialog())
        dialog.training_controls[0].setValue(0.95)
        dialog.training_controls[2].setValue(0.2)
        with patch("puma_ui.modules.inspection_tests.care_areas.QMessageBox.warning") as warning:
            click(visible_button(dialog, "Generate Page Break"))
        warning.assert_called_once()
        dialog.training_controls[0].setValue(0.10)
        dialog.training_controls[2].setValue(0.20)
        click(dialog.use_test_optics)
        click(dialog.skip_fourier)
        click(visible_button(dialog, "Generate Page Break"))
        self.assertEqual(dialog.result(), QDialog.Accepted)

    def test_page_break_add_undo_redo_sort_coverage_and_options(self):
        groups = [{"name": "PB1", "kind": "Page Break", "areas": []}]
        editor = self.show_dialog(PageBreakEditDialog(groups, 0))
        with patch("puma_ui.modules.inspection_tests.care_areas.QMessageBox.warning") as warning:
            click(visible_button(editor, "Finish PageBreak"))
        warning.assert_called_once()
        for control, value in zip(editor.geometry, [0.1, 0.1, 0.3, 0.4]):
            control.setValue(value)
        click(visible_button(editor, "Finish PageBreak"))
        self.assertEqual(editor.table.rowCount(), 1)
        click(visible_button(editor, "Undo"))
        self.assertEqual(editor.table.rowCount(), 0)
        click(visible_button(editor, "Redo"))
        self.assertEqual(editor.table.rowCount(), 1)
        click(visible_button(editor, "Done"))
        self.assertEqual(len(editor.result_groups[0]["areas"]), 1)

        sorting = self.show_dialog(PageBreakSortingDialog())
        sorting.separation.setValue(7.5)
        click(visible_button(sorting, "Update"))
        self.assertEqual(sorting.separation.value(), 7.5)

        coverage = self.show_dialog(CareAreaCoverageDialog([
            {"name": "CA 1", "defined_percent": 22.5, "inspected_percent": 21.9}
        ]))
        click(visible_button(coverage, "Close"))

        options = self.show_dialog(CareAreaOptionsDialog({}))
        options.opacity.setValue(50)
        click(visible_button(options, "OK"))
        self.assertEqual(options.result(), QDialog.Accepted)
        self.assertEqual(options.opacity.value(), 50)

    def test_fourier_training_unlocks_rods_and_saves(self):
        state = default_fourier_state()
        state["boxes"] = [{"x": 0.1, "y": 0.1, "width": 0.2, "height": 0.2, "channels": [1, 2, 3]}]
        dialog = self.show_dialog(FourierFilterTrainingDialog(state))
        self.assertFalse(dialog.rod_button.isEnabled())
        with patch("puma_ui.modules.inspection_tests.fourier.QMessageBox.information"):
            click(visible_button(dialog, "Train FF"))
        self.assertTrue(dialog.rod_button.isEnabled())
        self.assertEqual(dialog.progress.value(), 100)
        click(visible_button(dialog, "Finish"))
        self.assertTrue(dialog.result_state["trained"])

    def test_fourier_sample_plan_and_images_close_paths(self):
        sample = self.show_dialog(FourierSamplePlanDialog([0, 0]))
        QTest.mouseClick(sample.canvas, Qt.LeftButton, Qt.NoModifier, sample.canvas.rect().center())
        process_events()
        click(visible_button(sample, "Finish"))
        self.assertIsNotNone(sample.canvas.selected_die)

        images = self.show_dialog(FourierImagesDialog(0))
        click(visible_button(images, "Close"))
        self.assertEqual(images.result(), QDialog.Accepted)

    def test_rod_analysis_unlocks_images_and_normal_incidence_specular_control(self):
        state = default_fourier_state()
        box = {"x": 0.1, "y": 0.1, "width": 0.2, "height": 0.2, "channels": [1, 2, 3]}
        dialog = self.show_dialog(RodPositionsDialog(state["rods"], boxes=[box], incidence_angle="Normal"))
        self.assertTrue(dialog.enforce_specular.isEnabled())
        self.assertFalse(dialog.view_images.isEnabled())
        click(dialog.enforce_specular)
        click(visible_button(dialog, "Analyze"))
        self.assertTrue(dialog.view_images.isEnabled())
        click(visible_button(dialog, "Finish"))
        self.assertTrue(dialog.analysis_valid)
        self.assertTrue(dialog.result_enforce_specular)

    def test_active_regions_and_advanced_light_manual_endpoint_gate(self):
        active = self.show_dialog(ActiveRegionsDialog([], False))
        click(active.enable)
        click(visible_button(active, "New"))
        self.assertEqual(active.table.rowCount(), 1)
        click(visible_button(active, "Finish"))
        self.assertTrue(active.enable.isChecked())
        self.assertEqual(len(active.result_regions), 1)

        state = default_light_training_state()
        options = self.show_dialog(AdvancedLightOptionsDialog(state))
        self.assertFalse(options.high_endpoint.isEnabled())
        select_combo(options.endpoint_mode, "Manual")
        self.assertTrue(options.high_endpoint.isEnabled())
        options.high_endpoint.setValue(220)
        click(visible_button(options, "OK"))
        self.assertEqual(options.result_options["high_endpoint"], 220)

    def test_light_histogram_sample_plan_reference_and_sem_values(self):
        channels = [
            {"name": "Channel 1", "light_level": 8.0, "exposure": 1.0},
            {"name": "Channel 2", "light_level": 7.0, "exposure": 1.0},
            {"name": "Channel 3", "light_level": 3.0, "exposure": 1.0},
        ]
        histogram = self.show_dialog(LightHistogramDialog(channels, "Exposure Control"))
        histogram.levels[0].setValue(9.5)
        click(visible_button(histogram, "Analyze"))
        click(visible_button(histogram, "Finish"))
        self.assertEqual(histogram.result_channels[0]["light_level"], 9.5)

        plan = self.show_dialog(LightSamplePlanDialog([[0, 0]]))
        click(visible_button(plan, "Set All Die to Selection Mode"))
        click(visible_button(plan, "Finish"))
        self.assertGreaterEqual(len(plan.result_dies), 1)

        reference = self.show_dialog(ReferenceDieDialog([1, 2]))
        reference.column.setValue(4)
        reference.row.setValue(5)
        click(visible_button(reference, "OK"))
        self.assertEqual([reference.column.value(), reference.row.value()], [4, 5])

        sem = self.show_dialog(SemFovDialog(10))
        sem.fov.setValue(18.5)
        click(visible_button(sem, "OK"))
        self.assertEqual(sem.fov.value(), 18.5)

    def test_master_plan_pattern_legend_and_color_paths(self):
        state = default_sample_plan()
        master = self.show_dialog(MasterSamplePlanDialog(state))
        master.name.setEditText("Manual QA")
        click(visible_button(master, "Store"))
        self.assertIn("Manual QA", master.result_state["master_plans"])
        click(visible_button(master, "OK"))

        pattern = self.show_dialog(DieInspectionPatternDialog())
        click(visible_button(pattern, "Clear"))
        self.assertFalse(any(any(row) for row in pattern._cells()))
        click(visible_button(pattern, "Invert"))
        self.assertTrue(all(all(row) for row in pattern._cells()))
        click(visible_button(pattern, "Apply Pattern"))

        legend = self.show_dialog(SamplePlanLegendDialog())
        click(visible_button(legend, "Close"))

        colors = self.show_dialog(SamplePlanColorsDialog())
        replace_text(colors.scheme_name, "Manual QA Colors")
        click(visible_button(colors, "Apply"))
        click(visible_button(colors, "OK"))
        self.assertEqual(colors.result_scheme["name"], "Manual QA Colors")

    def test_nef_add_save_delete_and_ido_missing_classifier_gate(self):
        nef = self.show_dialog(NuisanceFilterSetupDialog())
        click(visible_button(nef, "Add"))
        self.assertEqual(nef.table.rowCount(), 1)
        replace_text(nef.setup_name, "Manual QA")
        click(nef.keep_nuisance)
        click(visible_button(nef, "Save Setup"))
        self.assertIn("Manual QA", nef.state["saved_setups"])
        click(visible_button(nef, "OK"))
        self.assertTrue(nef.result_state["keep_nuisance_defects"])

        ido = self.show_dialog(IdoClassifierDialog())
        with patch("puma_ui.modules.inspection_tests.nef.QMessageBox.warning") as warning:
            click(visible_button(ido, "Open"))
        warning.assert_called_once()
        click(visible_button(ido, "Cancel"))

    def test_segmentation_image_grab_gate_and_completed_path(self):
        dialog = self.show_dialog(SegmentationImageGrabDialog([]))
        with patch("puma_ui.modules.inspection_tests.segmentation.QMessageBox.warning") as warning:
            click(visible_button(dialog, "Finish"))
        warning.assert_called_once()
        click(visible_button(dialog, "Mark New Site"))
        with patch("puma_ui.modules.inspection_tests.segmentation.QMessageBox.warning") as warning:
            click(visible_button(dialog, "Finish"))
        warning.assert_called_once()
        click(visible_button(dialog, "Grab Images"))
        self.assertEqual(dialog.progress.value(), 100)
        click(visible_button(dialog, "Finish"))
        self.assertEqual(dialog.result(), QDialog.Accepted)
        self.assertTrue(dialog.result_sites[0]["grabbed"])

    def test_sdi_image_box_rejects_outside_die_then_saves(self):
        dialog = self.show_dialog(SDIImageBoxDialog([0.2, 0.2, 0.3, 0.3]))
        dialog.controls[0].setValue(0.8)
        dialog.controls[2].setValue(0.4)
        with patch("puma_ui.modules.inspection_tests.segmentation.QMessageBox.warning") as warning:
            click(visible_button(dialog, "Mark and Advance"))
        warning.assert_called_once()
        dialog.controls[0].setValue(0.1)
        dialog.controls[2].setValue(0.4)
        click(visible_button(dialog, "Mark and Advance"))
        self.assertEqual(dialog.result_box[0], 0.1)

    def test_vnc_dcf_cib_and_channel_fusion_numeric_validation(self):
        vnc = self.show_dialog(VariableNoiseControlDialog({}, ["R1"]))
        select_combo(vnc.mode, "Collect Bandwidth")
        vnc.table.setCurrentCell(0, 0)
        vnc.table.setFocus()
        QTest.keyClick(vnc.table, Qt.Key_Space)
        process_events()
        self.assertEqual(vnc.table.item(0, 0).checkState(), Qt.Checked)
        click(visible_button(vnc, "OK"))
        self.assertIsNotNone(vnc.result_state)

        dcf_state = {"R1": [{"Channel": 1, "Alpha": 1, "Beta": 1, "Gamma": 1, "Delta": 1, "Postfilter": "None"}]}
        dcf = self.show_dialog(DecoupledChannelFusionDialog(dcf_state, ["R1"]))
        click(visible_button(dcf, "OK"))
        self.assertIsNotNone(dcf.result_state)

        channels = [
            {"clip": 0, "offset": 0, "L0": 0, "K": 1, "preconvolver": "None"}
            for _ in range(3)
        ]
        cib = self.show_dialog(CibParametersDialog(channels))
        cib.table.item(0, 4).setText("0")
        with patch("puma_ui.modules.inspection_tests.sensitivity.QMessageBox.warning") as warning:
            click(visible_button(cib, "OK"))
        warning.assert_called_once()
        cib.table.item(0, 4).setText("1")
        click(visible_button(cib, "OK"))
        self.assertEqual(len(cib.result_state), 3)

        flavors = self.show_dialog(ChannelFusionFlavorDialog([
            {"name": "CF2", "enabled": False, "threshold": 45}
        ], "HLAT"))
        flavors.table.item(0, 2).setText("-1")
        with patch("puma_ui.modules.inspection_tests.sensitivity.QMessageBox.warning") as warning:
            click(visible_button(flavors, "OK"))
        warning.assert_called_once()
        flavors.table.item(0, 2).setText("55")
        flavors.table.item(0, 0).setCheckState(Qt.Checked)
        click(visible_button(flavors, "OK"))
        self.assertTrue(flavors.result_state[0]["enabled"])


if __name__ == "__main__":
    unittest.main()

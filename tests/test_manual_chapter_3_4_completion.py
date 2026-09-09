from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from puma_ui.modules.inspection_tests.care_areas import (
    CareAreaImportDialog,
    CareAreasDialog,
    PageBreakSortingDialog,
    combine_page_break_groups,
)
from puma_ui.modules.inspection_tests.dialog import TestsSetupDialog, default_test
from puma_ui.modules.inspection_tests.segmentation import SegmentationImageGrabDialog
from puma_ui.modules.recipe_lifecycle import SaveInspectionDialog
from puma_ui.qt_compat import QApplication, QComboBox, QDialog, QMessageBox, Qt
from puma_ui.recipe_store import RecipeStore

from manual_ui_helpers import QTest, click, process_events, select_combo, visible_button


class ManualChapterThreeFourCompletionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = RecipeStore(Path(self.temp.name) / "recipes.json", default_recipes=[])
        self.recipe_a = self.store.save_recipe({
            "inspection": "Recipe-A", "device": "Device-A", "step": "Layer-1",
            "status": "Valid", "approval": "Production", "recipe_type": "Normal",
        })
        self.recipe_b = self.store.save_recipe({
            "inspection": "Recipe-B", "device": "Device-A", "step": "Layer-2",
            "status": "Incomplete", "approval": "Engineering", "recipe_type": "FEM",
        })

    def tearDown(self):
        for widget in list(QApplication.topLevelWidgets()):
            widget.close()
        process_events()
        self.temp.cleanup()

    def show_dialog(self, dialog):
        dialog.show()
        process_events(20)
        self.assertTrue(dialog.isVisible())
        return dialog

    def test_3_10_save_browser_selects_device_step_and_recipe(self):
        dialog = self.show_dialog(SaveInspectionDialog(self.recipe_a, recipe_store=self.store))
        self.assertEqual(dialog.device_list.count(), 1)
        self.assertEqual(dialog.step_list.count(), 2)
        layer_two = dialog.step_list.findItems("Layer-2", Qt.MatchExactly)[0]
        dialog.step_list.setCurrentItem(layer_two)
        process_events()
        self.assertEqual(dialog.step_edit.text(), "Layer-2")
        self.assertEqual(dialog.recipe_table.rowCount(), 1)
        dialog.recipe_table.selectRow(0)
        process_events()
        self.assertEqual(dialog.name_edit.text(), "Recipe-B")
        self.assertEqual(dialog.state_label.text(), "Incomplete")
        self.assertTrue(dialog.more_button.isEnabled())
        click(visible_button(dialog, "Cancel"))
        self.assertEqual(dialog.result(), QDialog.Rejected)

    def test_4_3_parameter_sections_expand_and_test_info_is_computed(self):
        test = default_test(1)
        test["mode"] = "Random"
        test["care_areas"]["groups"] = [{
            "name": "CA 1", "kind": "CA", "enabled": True,
            "areas": [[0.1, 0.1, 0.2, 0.3]],
        }]
        test["sample_plan"]["selected_count"] = 12
        dialog = self.show_dialog(TestsSetupDialog([test], die_size_um=(5000, 10000)))
        section_row = next(
            row for row, (_label, key, kind) in enumerate(dialog.PARAMETER_ROWS)
            if key == "test_info" and kind == "section"
        )
        count_row = next(
            row for row, (_label, key, _kind) in enumerate(dialog.PARAMETER_ROWS)
            if key == "care_area_count"
        )
        self.assertTrue(dialog.matrix.isRowHidden(count_row))
        item = dialog.matrix.item(section_row, 0)
        QTest.mouseClick(
            dialog.matrix.viewport(), Qt.LeftButton, Qt.NoModifier,
            dialog.matrix.visualItemRect(item).center(),
        )
        process_events()
        self.assertFalse(dialog.matrix.isRowHidden(count_row))
        self.assertEqual(dialog.matrix.cellWidget(count_row, 1).text(), "1")
        die_row = next(
            row for row, (_label, key, _kind) in enumerate(dialog.PARAMETER_ROWS)
            if key == "die_count"
        )
        self.assertEqual(dialog.matrix.cellWidget(die_row, 1).text(), "12")
        item = dialog.matrix.item(section_row, 0)
        QTest.mouseClick(
            dialog.matrix.viewport(), Qt.LeftButton, Qt.NoModifier,
            dialog.matrix.visualItemRect(item).center(),
        )
        process_events()
        self.assertTrue(dialog.matrix.isRowHidden(count_row))

    def test_4_5_care_area_start_finish_measure_show_and_pda(self):
        dialog = self.show_dialog(CareAreasDialog())
        click(visible_button(dialog, "CA"))
        self.assertFalse(dialog.start_area_button.isEnabled())
        self.assertTrue(dialog.finish_area_button.isEnabled())
        canvas = dialog.canvas
        start = canvas.rect().center()
        start.setX(canvas.rect().left() + 50)
        start.setY(canvas.rect().top() + 50)
        end = canvas.rect().center()
        QTest.mousePress(canvas, Qt.LeftButton, Qt.NoModifier, start)
        QTest.mouseMove(canvas, end, 20)
        QTest.mouseRelease(canvas, Qt.LeftButton, Qt.NoModifier, end)
        process_events()
        self.assertEqual(len(dialog.state["groups"][0]["areas"]), 1)
        click(dialog.finish_area_button)
        self.assertFalse(canvas.drawing_enabled)
        self.assertTrue(dialog.start_area_button.isEnabled())

        click(dialog.measure_button)
        QTest.mousePress(canvas, Qt.LeftButton, Qt.NoModifier, start)
        QTest.mouseMove(canvas, end, 20)
        QTest.mouseRelease(canvas, Qt.LeftButton, Qt.NoModifier, end)
        process_events()
        self.assertIn("Distance", dialog.info.text())
        dialog.show_image_action.trigger()
        process_events()
        self.assertFalse(canvas.show_image)

        dialog.group_tabs.setCurrentIndex(1)
        pda = dialog.advanced_groups.cellWidget(0, 2)
        self.assertIsInstance(pda, QComboBox)
        select_combo(pda, "Include")
        self.assertTrue(dialog.state["groups"][0]["pda_care_area"])
        click(visible_button(dialog, "Finish"))
        self.assertEqual(dialog.result(), QDialog.Accepted)

    def test_4_5_import_table_has_registered_status_and_page_break_grouping(self):
        importer = self.show_dialog(CareAreaImportDialog("Random"))
        self.assertEqual(importer.groups.columnCount(), 3)
        self.assertEqual(importer.groups.horizontalHeaderItem(2).text(), "Registered")
        click(visible_button(importer, "Cancel"))

        groups = [
            {"name": "PB H1", "kind": "Horizontal Page Break", "areas": [[0.1, 0.1, 0.2, 0.01]]},
            {"name": "PB H2", "kind": "Horizontal Page Break", "areas": [[0.1, 0.2, 0.2, 0.02]]},
        ]
        sorting = self.show_dialog(PageBreakSortingDialog(groups, [0, 1]))
        self.assertEqual(sorting.assignment_table.rowCount(), 2)
        click(sorting.combine_groups)
        sorting.assignment_table.cellWidget(1, 1).setValue(1)
        click(visible_button(sorting, "Update"))
        self.assertEqual(sorting.result(), QDialog.Accepted)
        self.assertEqual(set(sorting.group_numbers().values()), {1})
        combined = combine_page_break_groups(groups, [0, 1], sorting.group_numbers())
        self.assertEqual(len(combined), 1)
        self.assertEqual(combined[0]["name"], "Horizontal Page Break 1")
        self.assertEqual(len(combined[0]["areas"]), 2)
        separated = combine_page_break_groups(groups, [0, 1], {0: 1, 1: 2})
        self.assertEqual(len(separated), 2)

    def test_4_7_segmentation_image_tools_and_finish_sequence(self):
        dialog = self.show_dialog(SegmentationImageGrabDialog([]))
        with patch(
            "puma_ui.modules.inspection_tests.segmentation.QMessageBox.warning"
        ) as warning:
            click(visible_button(dialog, "Finish"))
        warning.assert_called_once()
        click(visible_button(dialog, "Mark New Site"))
        click(visible_button(dialog, "Grab Images"))
        select_combo(dialog.image_channel, "Channel 3")
        select_combo(dialog.image_mode, "Overlay")
        dialog.image_zoom.setValue(175)
        click(dialog.measure)
        self.assertIn("Channel 3", dialog.images.text())
        self.assertIn("Zoom 175%", dialog.images.text())
        self.assertIn("Distance", dialog.images.text())
        click(visible_button(dialog, "Finish"))
        self.assertEqual(dialog.result(), QDialog.Accepted)


if __name__ == "__main__":
    unittest.main()

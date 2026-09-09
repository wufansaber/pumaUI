from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from puma_ui.main_window import PumaMainWindow
from puma_ui.modules.inspection_tests import default_test, validate_test
from puma_ui.modules.inspection_tests.dialog import (
    TestsSetupDialog,
)
from puma_ui.modules.recipe_lifecycle.dialogs import (
    ExtractComponentDialog,
    InsertComponentDialog,
    RecipeHistoryDialog,
)
from puma_ui.modules.run_control import (
    RunOneWaferDialog,
    generate_inspection_result,
)
from puma_ui.qt_compat import QApplication, QDialog, QMessageBox
from puma_ui.recipe_store import RecipeStore

from manual_ui_helpers import click, process_events, replace_text, select_combo, visible_button


ORIENTATIONS = [
    "Up (0 deg.)",
    "Right (90 deg.)",
    "Down (180 deg.)",
    "Left (270 deg.)",
]


def valid_test(number: int, orientation: str) -> dict:
    test = default_test(number, orientation=orientation)
    test["name"] = f"Test {number}"
    test["orientation"] = orientation
    test["care_areas"]["groups"].append(
        {
            "name": f"CA {number}",
            "kind": "Care Area",
            "enabled": True,
            "areas": [[0.0, 0.0, 1.0, 1.0]],
            "skip_fourier_filter": False,
        }
    )
    test["light_training"]["noise_box_group"] = f"CA {number}"
    test["light_training"]["trained"] = True
    test["fourier"]["boxes"].append(
        {"x": 0.2, "y": 0.2, "width": 0.25, "height": 0.25, "channels": [1, 2, 3]}
    )
    test["fourier"]["trained"] = True
    test["fourier"]["analysis_valid"] = True
    test["fourier_trained"] = True
    test["light_trained"] = True
    test["status"] = "Valid"
    assert validate_test(test) == []
    return test


def orientation_profile(marker: str) -> dict:
    return {
        "alignment": {
            "sites_defined": True,
            "aligned": True,
            "status": "Valid",
            "profile_marker": marker,
        },
        "wafer_map": {
            "die_pattern_defined": True,
            "scribe_lines_defined": True,
            "die_pitch_width": 5100.0,
            "die_pitch_height": 16600.0,
            "profile_marker": marker,
        },
    }


class ManualRecipeOrientationWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def show_dialog(self, dialog):
        dialog.show()
        process_events(20)
        self.assertTrue(dialog.isVisible())
        return dialog

    def test_extract_insert_round_trip_uses_visible_controls_and_status(self):
        with tempfile.TemporaryDirectory() as directory:
            store = RecipeStore(Path(directory) / "recipes.json")
            recipe = store.new_recipe()
            recipe.update(
                {
                    "inspection": "LifecycleBase",
                    "alignment": orientation_profile("180")["alignment"],
                    "wafer_map": orientation_profile("180")["wafer_map"],
                    "tests": [valid_test(1, "Down (180 deg.)")],
                    "status": "Valid",
                    "test_setup_valid": True,
                }
            )
            recipe = store.save_recipe(recipe, event="Save Inspection")

            extract = self.show_dialog(ExtractComponentDialog(store, recipe))
            click(visible_button(extract, "Unselect All"))
            test_check = next(box for box in extract.checks if box.text() == "Test 1")
            click(test_check)
            replace_text(extract.filename_edit, "LifecycleBundle")
            click(visible_button(extract, "Extract"))
            self.assertEqual(extract.extracted_filename, "LifecycleBundle")
            self.assertEqual(
                extract.table.item(extract.checks.index(test_check), 2).text(),
                "Extraction succeeded",
            )
            click(visible_button(extract, "Close"))

            insert = self.show_dialog(
                InsertComponentDialog(store, store.new_recipe())
            )
            row_names = [
                insert.table.item(row, 0).text()
                for row in range(insert.table.rowCount())
            ]
            test_row = row_names.index("Test 1")
            select_combo(insert.component_combos[test_row], "LifecycleBundle")
            click(visible_button(insert, "Insert"))
            self.assertEqual(
                insert.table.item(test_row, 2).text(), "Insertion succeeded"
            )
            self.assertIn("Review Load/Save Status", insert.status.text())
            click(visible_button(insert, "Close"))
            self.assertEqual(insert.result(), QDialog.Accepted)
            self.assertEqual(insert.result_recipe["tests"][0]["name"], "Test 1")

    def test_derivative_reselection_and_recipe_history_survive_save_reload(self):
        with tempfile.TemporaryDirectory() as directory:
            store = RecipeStore(Path(directory) / "recipes.json")
            base = store.new_recipe()
            base.update(
                {
                    "inspection": "OriginalMaster",
                    "alignment": orientation_profile("180")["alignment"],
                    "wafer_map": orientation_profile("180")["wafer_map"],
                    "tests": [valid_test(1, "Down (180 deg.)")],
                    "status": "Valid",
                    "test_setup_valid": True,
                }
            )
            base = store.save_recipe(base, event="Save Inspection")
            derivative = store.duplicate_recipe(
                base, "Layer2Derivative", derivative=True
            )
            derivative = store.save_recipe(
                derivative, event="Create Derivative"
            )

            with patch("puma_ui.main_window.RecipeStore", return_value=store):
                window = PumaMainWindow()
            window._set_current_recipe(derivative)
            self.assertTrue(window.setup_run_button.isEnabled())
            self.assertFalse(window._run_setup_ready)
            self.assertTrue(
                derivative["alignment"]["derivative_origin_reselection_required"]
            )

            completed = dict(derivative)
            completed["alignment"] = dict(completed["alignment"])
            completed["alignment"].update(
                {
                    "derivative_origin_reselected": True,
                    "derivative_reference": "Select Die Origin",
                }
            )
            completed["status"] = "Valid"
            completed["test_setup_valid"] = True
            completed = store.save_recipe(
                completed, event="Save Inspection", detail="Reference reselected"
            )
            window._set_current_recipe(completed)
            self.assertTrue(window.setup_run_button.isEnabled())

            history = self.show_dialog(
                RecipeHistoryDialog(store, "Layer2Derivative")
            )
            events = [
                history.table.item(row, 1).text()
                for row in range(history.table.rowCount())
            ]
            self.assertIn("Create Derivative", events)
            self.assertIn("Save Inspection", events)
            click(visible_button(history, "Close"))
            window.close()

    def test_four_orientation_profiles_gate_run_and_are_restored(self):
        with tempfile.TemporaryDirectory() as directory:
            store = RecipeStore(Path(directory) / "recipes.json")
            profiles = {
                str(PumaMainWindow._orientation_degrees(orientation)): orientation_profile(
                    str(PumaMainWindow._orientation_degrees(orientation))
                )
                for orientation in ORIENTATIONS
            }
            recipe = store.new_recipe()
            recipe.update(
                {
                    "inspection": "FourOrientation",
                    "active_setup_orientation": "180",
                    "orientation_setups": profiles,
                    "alignment": profiles["180"]["alignment"],
                    "wafer_map": profiles["180"]["wafer_map"],
                    "tests": [
                        valid_test(index + 1, orientation)
                        for index, orientation in enumerate(ORIENTATIONS)
                    ],
                    "status": "Valid",
                    "test_setup_valid": True,
                }
            )
            recipe = store.save_recipe(recipe, event="Save Inspection")
            with patch("puma_ui.main_window.RecipeStore", return_value=store):
                window = PumaMainWindow()
            window._set_current_recipe(recipe)
            self.assertTrue(window.setup_run_button.isEnabled())

            missing = dict(recipe)
            missing["orientation_setups"] = dict(profiles)
            missing["orientation_setups"].pop("270")
            window._set_current_recipe(missing)
            self.assertTrue(window.setup_run_button.isEnabled())
            self.assertFalse(window._run_setup_ready)

            window._set_current_recipe(recipe)
            for orientation in ("0", "90", "180", "270"):
                window._switch_orientation_setup(window.current_recipe, orientation)
                self.assertEqual(
                    window.current_recipe["alignment"]["profile_marker"], orientation
                )
                self.assertEqual(
                    window.current_recipe["wafer_map"]["profile_marker"], orientation
                )

            saved = store.save_recipe(window.current_recipe, event="Save Inspection")
            reloaded = store.get_recipe(saved["id"])
            self.assertEqual(set(reloaded["orientation_setups"]), {"0", "90", "180", "270"})

            run = self.show_dialog(RunOneWaferDialog(reloaded))
            self.assertEqual(set(run.test_checks), {"Test 1", "Test 2", "Test 3", "Test 4"})
            self.assertTrue(all(check.isChecked() for check in run.test_checks.values()))
            replace_text(run.lot_id, "LOT-4-ORIENTATIONS")
            with patch(
                "puma_ui.modules.run_control.dialogs.QMessageBox.question",
                return_value=QMessageBox.Yes,
            ):
                click(visible_button(run, "Run One Wafer"))
            self.assertEqual(run.result(), QDialog.Accepted)
            self.assertEqual(
                set(run.result_setup["selected_tests"]),
                {"Test 1", "Test 2", "Test 3", "Test 4"},
            )

            result = generate_inspection_result(reloaded, run.result_setup)
            self.assertEqual(
                result["test_orientations"],
                {f"Test {index + 1}": orientation for index, orientation in enumerate(ORIENTATIONS)},
            )
            self.assertEqual(
                {defect["test_orientation"] for defect in result["defects"]},
                set(ORIENTATIONS),
            )
            window.close()

    def test_rotate_wafer_choice_switches_to_an_independent_setup_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            store = RecipeStore(Path(directory) / "recipes.json")
            recipe = store.new_recipe()
            recipe.update(
                {
                    "inspection": "OrientationSwitch",
                    "active_setup_orientation": "180",
                    "alignment": orientation_profile("180")["alignment"],
                    "wafer_map": orientation_profile("180")["wafer_map"],
                    "tests": [valid_test(1, "Down (180 deg.)")],
                    "status": "Valid",
                    "test_setup_valid": True,
                }
            )
            with patch("puma_ui.main_window.RecipeStore", return_value=store):
                window = PumaMainWindow()
            window._set_current_recipe(recipe)

            tests = self.show_dialog(
                TestsSetupDialog(
                    recipe["tests"],
                    wafer_orientation="Down (180 deg.)",
                    wafer_loaded=True,
                    wafer_aligned=True,
                    wafer_geometry_defined=True,
                )
            )

            class AcceptedRotationDialog:
                def __init__(self, *_args, **_kwargs):
                    self.rotate_wafer = True

                def exec(self):
                    return QDialog.Accepted

            orientation_combo = tests.matrix.cellWidget(1, 1)
            with patch(
                "puma_ui.modules.inspection_tests.dialog.ChangeTestOrientationDialog",
                AcceptedRotationDialog,
            ):
                select_combo(orientation_combo, "Right (90 deg.)")
            click(visible_button(tests, "End"))
            window._apply_tests_setup(tests)

            self.assertEqual(window.wafer_runtime_state["required_orientation"], "90")
            self.assertEqual(
                window.current_recipe["orientation_setups"]["180"]["alignment"][
                    "profile_marker"
                ],
                "180",
            )
            self.assertEqual(window.current_recipe["alignment"], {})
            self.assertEqual(window.current_recipe["wafer_map"], {})
            self.assertFalse(window.current_recipe["tests"][0]["light_trained"])
            self.assertFalse(window.current_recipe["tests"][0]["fourier_trained"])
            self.assertTrue(window.tests_button.isEnabled())
            self.assertFalse(window._tests_setup_ready)
            window.close()


if __name__ == "__main__":
    unittest.main()

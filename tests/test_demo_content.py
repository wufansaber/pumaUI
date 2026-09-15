from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from puma_ui.demo_content import (
    DEMO_COMPONENT_FILENAME,
    DEMO_RECIPE_ID,
    DEMO_RECIPE_NAME,
    DEMO_CONTENT_VERSION,
    DEMO_RESULT_IDS,
    bundled_demo_root,
    demo_recipe,
    ensure_demo_recipe,
    ensure_demo_review_results,
    prepare_loaded_recipe,
)
from puma_ui.modules.inspection_tests import validate_test
from puma_ui.modules.lot_plan import validate_lot_plan
from puma_ui.modules.run_control import validate_run_setup
from puma_ui.modules.wafer_post_processing import validate_wpp
from puma_ui.modules.results_review import import_klarf_text
from puma_ui.modules.results_review import SelectLotResultsDialog
from puma_ui.qt_compat import QApplication
from puma_ui.recipe_store import RecipeStore


class DemoContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = RecipeStore(Path(self.temp.name) / "recipes.json")

    def tearDown(self):
        self.temp.cleanup()

    def test_loaded_legacy_recipe_receives_missing_editable_sections(self):
        loaded = prepare_loaded_recipe(
            {
                "id": "legacy-recipe",
                "inspection": "Legacy",
                "device": "D1",
                "step": "M1",
                "status": "Valid",
            }
        )
        self.assertTrue(loaded["alignment"]["sites_defined"])
        self.assertTrue(loaded["wafer_map"]["die_pattern_defined"])
        self.assertTrue(loaded["wafer_map"]["scribe_lines_defined"])
        self.assertEqual(loaded["tests"][0]["name"], "Test 1")
        self.assertEqual(loaded["lot_plan"]["assignments"]["1"], ["Test 1"])
        self.assertIn("operations", loaded["wafer_post_processing"])
        self.assertFalse(loaded["dirty"])

    def test_existing_recipe_sections_are_not_replaced(self):
        original_alignment = {"sites_defined": False, "operator_note": "retain me"}
        original_map = {"die_pattern_defined": True, "die_pitch_width": 7000.0}
        loaded = prepare_loaded_recipe(
            {
                "id": "configured-recipe",
                "status": "Incomplete",
                "alignment": original_alignment,
                "wafer_map": original_map,
                "tests": [{"name": "Existing Test", "mode": "Random"}],
            }
        )
        self.assertEqual(loaded["alignment"], original_alignment)
        self.assertEqual(loaded["wafer_map"], original_map)
        self.assertEqual(loaded["tests"][0]["name"], "Existing Test")

    def test_valid_legacy_recipe_hydrates_each_test_orientation(self):
        prepared = prepare_loaded_recipe({
            "id": "legacy-valid",
            "inspection": "Legacy Valid",
            "status": "Valid",
            "alignment": {"sites_defined": True},
            "wafer_map": {"die_pattern_defined": True},
            "tests": [
                {"name": "Test 1", "mode": "Random", "orientation": "0 deg"},
                {"name": "Test 2", "mode": "Random", "orientation": "90 deg"},
            ],
        })
        self.assertTrue({"0", "90"}.issubset(prepared["orientation_setups"]))
        self.assertTrue(
            prepared["orientation_setups"]["90"]["wafer_map"]["die_pattern_defined"]
        )

    def test_review_demo_results_are_repeatable_and_non_destructive(self):
        operator_result = {"id": "operator-result", "lot_id": "REAL_LOT", "defects": []}
        self.store.save_result(operator_result)
        first = ensure_demo_review_results(self.store)
        second = ensure_demo_review_results(self.store)
        self.assertEqual({item["id"] for item in first}, set(DEMO_RESULT_IDS))
        self.assertEqual(len(second), 2)
        self.assertEqual(len(self.store.list_results()), 3)
        self.assertIsNotNone(self.store.get_result("operator-result"))
        self.assertTrue(all(item["defect_count"] > 0 for item in first))
        self.assertTrue(all(item["dbb_execution"]["enabled"] for item in first))
        self.assertTrue(all(item["demo_content_version"] == DEMO_CONTENT_VERSION for item in first))
        self.assertTrue(all(item["sensitivity_data"] for item in first))
        self.assertTrue(
            all(item["sensitivity_data_tests"] == ["Test 1 - Fourier"] for item in first)
        )
        self.assertTrue(all(Path(item["path"]).is_dir() for item in first))

    def test_validation_demo_recipe_is_complete_and_exercises_fourier_optional_flow(self):
        recipe = demo_recipe()
        self.assertEqual(recipe["id"], DEMO_RECIPE_ID)
        self.assertEqual(recipe["inspection"], DEMO_RECIPE_NAME)
        self.assertEqual(recipe["status"], "Valid")
        self.assertTrue(recipe["alignment"]["aligned"])
        self.assertTrue(recipe["wafer_map"]["die_pattern_defined"])
        self.assertEqual(len(recipe["tests"]), 2)
        self.assertTrue(recipe["tests"][0]["channels"][0]["use_fourier_filter"])
        self.assertTrue(recipe["tests"][0]["fourier_trained"])
        self.assertFalse(any(
            channel["use_fourier_filter"] for channel in recipe["tests"][1]["channels"]
        ))
        self.assertFalse(recipe["tests"][1]["fourier_trained"])
        self.assertEqual([validate_test(test) for test in recipe["tests"]], [[], []])
        self.assertEqual(validate_lot_plan(recipe["lot_plan"]), [])
        self.assertEqual(validate_wpp(recipe["wafer_post_processing"], 2), [])
        self.assertEqual(validate_run_setup(recipe["run_setup"], recipe), [])

    def test_validation_demo_recipe_is_installed_once_without_replacing_edits(self):
        first = ensure_demo_recipe(self.store)
        first["comments"] = "operator edit"
        self.store.save_recipe(first)
        second = ensure_demo_recipe(self.store)
        self.assertEqual(second["comments"], "operator edit")
        self.assertEqual(
            len([item for item in self.store.list_recipes() if item["id"] == DEMO_RECIPE_ID]),
            1,
        )

    def test_validation_demo_can_be_injected_without_startup_disk_write(self):
        store_path = Path(self.temp.name) / "memory-only.json"
        store = RecipeStore(store_path)
        installed = ensure_demo_recipe(store, persist=False)
        self.assertEqual(installed["inspection"], DEMO_RECIPE_NAME)
        self.assertIsNotNone(store.get_recipe(DEMO_RECIPE_ID))
        bundles = store.list_component_bundles()
        self.assertEqual([item["filename"] for item in bundles], [DEMO_COMPONENT_FILENAME])
        self.assertIn("Wafer Layout", bundles[0]["components"])
        self.assertIn("Test 1", bundles[0]["components"])
        self.assertFalse(store_path.exists())

    def test_bundled_klarf_and_supporting_files_are_valid(self):
        root = bundled_demo_root()
        klarf = root / "review" / "PUMA_DEMO_LOT_W01.klarf"
        imported = import_klarf_text(klarf.read_text(encoding="utf-8"))
        self.assertEqual(imported["lot_id"], "PUMA_DEMO_LOT")
        self.assertEqual(imported["wafer_id"], "W01")
        self.assertEqual(len(imported["defects"]), 8)
        self.assertTrue((root / "review" / "defects.csv").is_file())
        self.assertTrue((root / "review" / "review_manifest.json").is_file())
        self.assertTrue((root / "design" / "PUMA_DEMO.rdf").is_file())

    def test_result_selector_exposes_an_explicit_demo_data_source(self):
        ensure_demo_review_results(self.store)
        self.store.save_result({
            "id": "operator-result",
            "lot_id": "REAL_LOT",
            "status": "Complete",
            "defects": [],
        })
        dialog = SelectLotResultsDialog(self.store)
        dialog.source.setCurrentText("Demo Data")
        QApplication.processEvents()
        self.assertEqual(len(dialog.results), 2)
        self.assertTrue(all(item.get("is_demo") for item in dialog.results))
        status_column = dialog.columns.index("status")
        self.assertTrue(dialog.table.item(0, status_column).text().endswith("(Demo)"))
        dialog.close()


if __name__ == "__main__":
    unittest.main()

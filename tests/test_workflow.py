from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from puma_ui.modules.inspection_tests import default_test, validate_test
from puma_ui.modules.lot_plan import default_lot_plan_state, validate_lot_plan
from puma_ui.modules.results_review import filter_defects, result_matches_recipe, review_summary
from puma_ui.modules.run_control import default_run_setup, generate_inspection_result, validate_run_setup
from puma_ui.modules.wafer_post_processing import default_wpp_state, validate_wpp
from puma_ui.recipe_store import RecipeStore


class EndToEndWorkflowTests(unittest.TestCase):
    def _valid_recipe(self):
        test = default_test(1)
        test["care_areas"]["groups"].append(
            {
                "name": "CA 1",
                "kind": "Care Area",
                "enabled": True,
                "areas": [[0.0, 0.0, 1.0, 1.0]],
                "skip_fourier_filter": False,
            }
        )
        test["light_training"]["noise_box_group"] = "CA 1"
        test["fourier"]["boxes"].append(
            {"x": 0.2, "y": 0.2, "width": 0.25, "height": 0.25, "channels": [1, 2, 3]}
        )
        test["fourier"]["trained"] = True
        test["fourier_trained"] = True
        test["light_trained"] = True
        self.assertEqual(validate_test(test), [])
        return {
            "id": "workflow-recipe",
            "inspection": "Deep",
            "device": "Device1",
            "step": "Layer1",
            "status": "Valid",
            "software_version": "9.8.306",
            "tests": [test],
        }

    def test_recipe_through_review_result(self):
        recipe = self._valid_recipe()
        plan = default_lot_plan_state(["Test 1"])
        plan["assignments"] = {"1": ["Test 1"]}
        self.assertEqual(validate_lot_plan(plan), [])
        recipe["lot_plan"] = plan

        wpp = default_wpp_state()
        sampling = next(item for item in wpp["operations"] if item["name"] == "Sampling")
        sampling["enabled"] = True
        sampling["parameters"]["review_sampling"] = "Random/Class Code"
        sampling["parameters"]["maximum_samples"] = 40
        self.assertEqual(validate_wpp(wpp, test_count=1), [])
        recipe["wafer_post_processing"] = wpp

        setup = default_run_setup(recipe)
        setup.update({"lot_id": "LOT-E2E", "wafer_id": "W01"})
        self.assertEqual(validate_run_setup(setup, recipe), [])
        result = generate_inspection_result(recipe, setup)
        self.assertTrue(result_matches_recipe(result, recipe))

        visible = filter_defects(result, {"minimum_signal": 100})
        summary = review_summary(result, visible)
        self.assertGreater(summary["visible"], 0)
        self.assertLess(summary["visible"], summary["total"])

        with tempfile.TemporaryDirectory() as directory:
            store = RecipeStore(Path(directory) / "recipes.json")
            saved = store.save_result(result)
            self.assertEqual(store.get_result(saved["id"])["defect_count"], summary["total"])

    def test_run_rejects_missing_lot_and_tests(self):
        recipe = self._valid_recipe()
        setup = default_run_setup(recipe)
        setup["selected_tests"] = []
        errors = validate_run_setup(setup, recipe)
        self.assertIn("Lot ID is required", errors)
        self.assertIn("Select at least one test to run", errors)


if __name__ == "__main__":
    unittest.main()

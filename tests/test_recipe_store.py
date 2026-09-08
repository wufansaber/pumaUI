from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from puma_ui.recipe_store import RecipeStore, SCHEMA_VERSION


class RecipeStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store_path = Path(self.temp_dir.name) / "recipes.json"
        self.defaults = [
            {
                "inspection": "Base",
                "device": "DeviceA",
                "step": "Layer1",
                "status": "Valid",
                "state": "Recipe is valid for setup review.",
            }
        ]

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_defaults_are_normalized_without_writing(self):
        store = RecipeStore(self.store_path, self.defaults)
        recipes = store.list_recipes()
        self.assertEqual(recipes[0]["inspection"], "Base")
        self.assertTrue(recipes[0]["id"])
        self.assertFalse(self.store_path.exists())

    def test_save_and_reload_recipe(self):
        store = RecipeStore(self.store_path, self.defaults)
        recipe = store.new_recipe()
        recipe.update({"inspection": "Saved", "device": "DeviceB", "step": "Metal"})
        saved = store.save_recipe(recipe)

        reloaded = RecipeStore(self.store_path)
        loaded = reloaded.get_recipe(saved["id"])
        self.assertEqual(loaded["inspection"], "Saved")
        self.assertFalse(loaded["dirty"])
        self.assertEqual(reloaded.history("Saved")[-1]["event"], "Save Recipe")

    def test_derivative_preserves_components_and_tracks_origin(self):
        store = RecipeStore(self.store_path, self.defaults)
        source = store.list_recipes()[0]
        source["components"] = {"Wafer Layout": {"pitch_x": 5100}}
        derivative = store.duplicate_recipe(source, "Layer2", derivative=True)

        self.assertEqual(derivative["derived_from"], "Base")
        self.assertEqual(derivative["recipe_type"], "Derivative")
        self.assertEqual(derivative["components"]["Wafer Layout"]["pitch_x"], 5100)
        self.assertIn("reselection", derivative["state"])
        self.assertTrue(derivative["alignment"]["derivative_origin_reselection_required"])
        self.assertFalse(derivative["alignment"]["derivative_origin_reselected"])

    def test_component_bundle_overwrites_by_filename(self):
        store = RecipeStore(self.store_path, self.defaults)
        source = store.list_recipes()[0]
        store.save_component_bundle("BaseComponents", source, {"Alignment": {"site": 1}})
        store.save_component_bundle("BaseComponents", source, {"Alignment": {"site": 2}})

        bundles = store.list_component_bundles()
        self.assertEqual(len(bundles), 1)
        self.assertEqual(bundles[0]["components"]["Alignment"]["site"], 2)
        with self.store_path.open("r", encoding="utf-8") as stream:
            self.assertEqual(json.load(stream)["schema_version"], SCHEMA_VERSION)

    def test_run_results_and_jobs_persist(self):
        store = RecipeStore(self.store_path)
        result = store.save_result({"lot_id": "LOT-1", "status": "Complete"})
        job = store.save_job({"lot_id": "LOT-2", "status": "Waiting for Material"})

        reopened = RecipeStore(self.store_path)
        self.assertEqual(reopened.get_result(result["id"])["lot_id"], "LOT-1")
        self.assertEqual(reopened.list_jobs()[0]["id"], job["id"])
        self.assertTrue(reopened.remove_job(job["id"]))
        self.assertTrue(reopened.delete_result(result["id"]))

    def test_delete_and_clear_recent_persist(self):
        store = RecipeStore(self.store_path, self.defaults)
        recipe = store.save_recipe(store.list_recipes()[0])
        store.set_recent(recipe["id"], True)
        store.clear_recent()
        self.assertFalse(store.get_recipe(recipe["id"])["recent"])
        self.assertTrue(store.delete_recipe(recipe["id"]))
        self.assertIsNone(store.get_recipe(recipe["id"]))

    def test_corrupt_store_is_backed_up_and_recovers(self):
        self.store_path.write_text("{not valid json", encoding="utf-8")
        store = RecipeStore(self.store_path, self.defaults)
        self.assertEqual(store.list_recipes()[0]["inspection"], "Base")
        backups = list(self.store_path.parent.glob("recipes.corrupt-*.json"))
        self.assertEqual(len(backups), 1)
        self.assertIn("not valid json", backups[0].read_text(encoding="utf-8"))

    def test_old_schema_is_migrated_in_memory(self):
        self.store_path.write_text(
            json.dumps({"schema_version": 1, "recipes": [], "components": [], "history": []}),
            encoding="utf-8",
        )
        store = RecipeStore(self.store_path)
        store.flush()
        data = json.loads(self.store_path.read_text(encoding="utf-8"))
        self.assertEqual(data["schema_version"], SCHEMA_VERSION)
        self.assertEqual(data["results"], [])
        self.assertEqual(data["result_backups"], [])
        self.assertEqual(data["job_queue"], [])
        self.assertEqual(data["transfer_queue"], [])
        self.assertEqual(data["utility_events"], [])

    def test_overwrite_results_can_archive_previous_lot(self):
        store = RecipeStore(self.store_path)
        old = store.save_result({"lot_id": "LOT-1", "wafer_id": "W01", "status": "Complete"})
        replacement = {"lot_id": "LOT-1", "wafer_id": "W01", "status": "Complete", "defect_count": 12}
        saved = store.overwrite_results([old["id"]], [replacement], backup=True)
        self.assertEqual(len(saved), 1)
        self.assertEqual(len(store.list_results()), 1)
        self.assertEqual(store.list_results()[0]["defect_count"], 12)
        self.assertEqual(store.list_result_backups()[0]["backup_of"], old["id"])

    def test_print_on_run_preferences_persist(self):
        store = RecipeStore(self.store_path)
        store.update_preferences({"print_on_run": {"wafer_map_after_each_test": True}})
        reopened = RecipeStore(self.store_path)
        settings = reopened.get_preferences()["print_on_run"]
        self.assertTrue(settings["wafer_map_after_each_test"])
        self.assertFalse(settings["run_log_after_run"])

    def test_communication_preferences_persist(self):
        store = RecipeStore(self.store_path)
        store.update_preferences({"communication": {
            "control_mode": "Remote",
            "secs_enabled": True,
            "secs_host": "factory-host",
            "secs_port": 5100,
            "ilink_enabled": True,
            "ilink_host": "analysis-host",
            "ilink_port": 6100,
        }})
        reopened = RecipeStore(self.store_path)
        communication = reopened.get_preferences()["communication"]
        self.assertEqual(communication["control_mode"], "Remote")
        self.assertEqual(communication["secs_host"], "factory-host")
        self.assertEqual(communication["ilink_port"], 6100)

    def test_invalid_communication_ports_fall_back_to_defaults(self):
        self.store_path.write_text(json.dumps({
            "schema_version": 3,
            "recipes": [],
            "preferences": {"communication": {"secs_port": "bad", "ilink_port": None}},
        }), encoding="utf-8")
        communication = RecipeStore(self.store_path).get_preferences()["communication"]
        self.assertEqual(communication["secs_port"], 5000)
        self.assertEqual(communication["ilink_port"], 6000)


if __name__ == "__main__":
    unittest.main()

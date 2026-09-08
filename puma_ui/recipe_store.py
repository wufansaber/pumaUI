from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional
from uuid import uuid4


SCHEMA_VERSION = 4


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _bounded_port(value, default: int) -> int:
    try:
        return max(1, min(65535, int(value)))
    except (TypeError, ValueError):
        return default


class RecipeStore:
    """Small JSON-backed repository shared by all recipe setup dialogs."""

    def __init__(self, path: Optional[Path] = None, default_recipes: Optional[Iterable[dict]] = None):
        if path is None:
            local_data = Path(os.environ.get("LOCALAPPDATA", Path.home()))
            path = local_data / "Puma9980UI" / "recipes.json"
        self.path = Path(path)
        self._default_recipes = [deepcopy(recipe) for recipe in (default_recipes or [])]
        self._data = self._load()

    def _empty_data(self) -> dict:
        recipes = []
        for recipe in self._default_recipes:
            normalized = self._normalize_recipe(recipe)
            recipes.append(normalized)
        return {
            "schema_version": SCHEMA_VERSION,
            "recipes": recipes,
            "components": [],
            "history": [],
            "results": [],
            "result_backups": [],
            "job_queue": [],
            "transfer_queue": [],
            "utility_events": [],
            "preferences": {
                "print_on_run": {
                    "wafer_map_after_each_test": False,
                    "run_log_after_run": False,
                },
                "communication": {
                    "control_mode": "Local",
                    "secs_enabled": False,
                    "secs_host": "127.0.0.1",
                    "secs_port": 5000,
                    "ilink_enabled": False,
                    "ilink_host": "127.0.0.1",
                    "ilink_port": 6000,
                },
                "data_transfer": {
                    "running": True,
                    "protocol": "ILink",
                    "analysis_system": "AnalysisSystem1",
                    "host": "127.0.0.1",
                    "port": 6000,
                    "automatic_retry": True,
                },
                "equipment_constants": {},
                "preventive_maintenance": {},
                "click_and_mark": {},
                "sizing_workspace": {},
                "system_admin": {},
                "xp_offline": {},
            },
        }

    def _load(self) -> dict:
        if not self.path.exists():
            return self._empty_data()
        try:
            with self.path.open("r", encoding="utf-8") as stream:
                data = json.load(stream)
        except (OSError, ValueError, TypeError):
            self._backup_corrupt_store()
            return self._empty_data()

        if not isinstance(data, dict):
            self._backup_corrupt_store()
            return self._empty_data()

        data["schema_version"] = SCHEMA_VERSION
        for key in (
            "recipes",
            "components",
            "history",
            "results",
            "result_backups",
            "job_queue",
            "transfer_queue",
            "utility_events",
        ):
            if not isinstance(data.get(key), list):
                data[key] = []
        if not isinstance(data.get("preferences"), dict):
            data["preferences"] = {}
        print_on_run = data["preferences"].get("print_on_run")
        if not isinstance(print_on_run, dict):
            print_on_run = {}
        data["preferences"]["print_on_run"] = {
            "wafer_map_after_each_test": bool(print_on_run.get("wafer_map_after_each_test", False)),
            "run_log_after_run": bool(print_on_run.get("run_log_after_run", False)),
        }
        communication = data["preferences"].get("communication")
        if not isinstance(communication, dict):
            communication = {}
        data["preferences"]["communication"] = {
            "control_mode": "Remote" if communication.get("control_mode") == "Remote" else "Local",
            "secs_enabled": bool(communication.get("secs_enabled", False)),
            "secs_host": str(communication.get("secs_host", "127.0.0.1")),
            "secs_port": _bounded_port(communication.get("secs_port", 5000), 5000),
            "ilink_enabled": bool(communication.get("ilink_enabled", False)),
            "ilink_host": str(communication.get("ilink_host", "127.0.0.1")),
            "ilink_port": _bounded_port(communication.get("ilink_port", 6000), 6000),
        }
        transfer = data["preferences"].get("data_transfer")
        if not isinstance(transfer, dict):
            transfer = {}
        data["preferences"]["data_transfer"] = {
            "running": bool(transfer.get("running", True)),
            "protocol": str(transfer.get("protocol", "ILink")),
            "analysis_system": str(transfer.get("analysis_system", "AnalysisSystem1")),
            "host": str(transfer.get("host", "127.0.0.1")),
            "port": _bounded_port(transfer.get("port", 6000), 6000),
            "automatic_retry": bool(transfer.get("automatic_retry", True)),
        }
        if not isinstance(data["preferences"].get("equipment_constants"), dict):
            data["preferences"]["equipment_constants"] = {}
        if not isinstance(data["preferences"].get("preventive_maintenance"), dict):
            data["preferences"]["preventive_maintenance"] = {}
        if not isinstance(data["preferences"].get("click_and_mark"), dict):
            data["preferences"]["click_and_mark"] = {}
        if not isinstance(data["preferences"].get("sizing_workspace"), dict):
            data["preferences"]["sizing_workspace"] = {}
        if not isinstance(data["preferences"].get("system_admin"), dict):
            data["preferences"]["system_admin"] = {}
        if not isinstance(data["preferences"].get("xp_offline"), dict):
            data["preferences"]["xp_offline"] = {}
        data["recipes"] = [self._normalize_recipe(recipe) for recipe in data["recipes"]]
        return data

    def _backup_corrupt_store(self):
        if not self.path.exists():
            return
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = self.path.with_name(f"{self.path.stem}.corrupt-{timestamp}-{uuid4().hex[:6]}{self.path.suffix}")
        try:
            self.path.replace(backup)
        except OSError:
            pass

    def _normalize_recipe(self, recipe: dict) -> dict:
        result = deepcopy(recipe)
        result.setdefault("id", uuid4().hex)
        result.setdefault("inspection", "New")
        result.setdefault("device", "Device1")
        result.setdefault("step", "Layer1")
        result.setdefault("source", "local")
        result.setdefault("recent", False)
        result.setdefault("date_created", _now())
        result.setdefault("last_modified", result["date_created"])
        result.setdefault("status", "Incomplete")
        result.setdefault("approval", "Engineering")
        result.setdefault("software_version", "9.8.306")
        result.setdefault("wafer_orientation", "180 deg")
        result.setdefault("auto_learn", "No")
        result.setdefault("state", "Recipe setup is incomplete.")
        result.setdefault("path", "")
        result.setdefault("recipe_filter", "All Recipes")
        result.setdefault("recipe_type", "Normal")
        result.setdefault("pixel_perfect_enabled", True)
        result.setdefault("sizing", {
            "sizing_enabled": False,
            "collect_sizing_data": False,
            "scale_factors": {
                "Small": 0.60, "Medium": 0.85, "Large": 0.50,
                "Tall": 1.90, "Dim": 1.40, "Planar": 1.00,
            },
            "cut_lines": {
                "Small": 13.0, "Large": 17.0, "Very Large": 21.0,
                "Tall": 1000.0, "Dim": 400.0, "Planar": 196.0,
            },
        })
        result.setdefault("components", {})
        result.setdefault("tests", [])
        result.setdefault("dirty", False)
        return result

    def list_recipes(self) -> list[dict]:
        return deepcopy(self._data["recipes"])

    def get_recipe(self, recipe_id: str) -> Optional[dict]:
        recipe = self._find(recipe_id)
        return deepcopy(recipe) if recipe else None

    def new_recipe(self) -> dict:
        return self._normalize_recipe(
            {
                "inspection": "New",
                "device": "Device1",
                "step": "Layer1",
                "status": "Incomplete",
                "state": "New inspection loaded. Complete wafer and test setup, then save the recipe.",
                "recipe_type": "Normal",
                "dirty": True,
            }
        )

    def duplicate_recipe(self, source: dict, name: str, *, derivative: bool = False) -> dict:
        recipe = self._normalize_recipe(source)
        source_name = source.get("inspection", "")
        recipe["id"] = uuid4().hex
        recipe["inspection"] = name
        recipe["date_created"] = _now()
        recipe["last_modified"] = recipe["date_created"]
        recipe["recent"] = True
        recipe["dirty"] = True
        recipe["derived_from"] = source_name if derivative else ""
        if derivative:
            recipe["recipe_type"] = "Derivative"
            recipe["status"] = "Incomplete"
            recipe["state"] = "Derivative recipe requires reselection of the first alignment site or die origin."
            alignment = deepcopy(recipe.get("alignment") or {})
            alignment["derivative_origin_reselection_required"] = True
            alignment["derivative_origin_reselected"] = False
            recipe["alignment"] = alignment
        self.record_history(
            "Create Derivative" if derivative else "Save As",
            recipe,
            f"Created from {source_name}",
            persist=False,
        )
        return recipe

    def save_recipe(self, recipe: dict, *, event: str = "Save Recipe", detail: str = "") -> dict:
        saved = self._normalize_recipe(recipe)
        saved["last_modified"] = _now()
        saved["dirty"] = False
        existing = self._find(saved["id"])
        if existing is None:
            self._data["recipes"].append(saved)
        else:
            existing.clear()
            existing.update(saved)
        self.record_history(event, saved, detail or saved.get("comments", ""), persist=False)
        self.flush()
        return deepcopy(saved)

    def delete_recipe(self, recipe_id: str) -> bool:
        recipe = self._find(recipe_id)
        if recipe is None:
            return False
        self._data["recipes"].remove(recipe)
        self.record_history("Delete Recipe", recipe, persist=False)
        self.flush()
        return True

    def set_recent(self, recipe_id: str, recent: bool = True):
        recipe = self._find(recipe_id)
        if recipe is not None:
            recipe["recent"] = recent
            self.flush()

    def clear_recent(self):
        for recipe in self._data["recipes"]:
            recipe["recent"] = False
        self.flush()

    def save_component_bundle(self, filename: str, source_recipe: dict, components: dict) -> dict:
        bundle = {
            "id": uuid4().hex,
            "filename": filename,
            "source_recipe": source_recipe.get("inspection", ""),
            "created": _now(),
            "components": deepcopy(components),
        }
        previous = next(
            (item for item in self._data["components"] if item.get("filename") == filename),
            None,
        )
        if previous is None:
            self._data["components"].append(bundle)
        else:
            previous.clear()
            previous.update(bundle)
        self.record_history("Extract Components", source_recipe, filename, persist=False)
        self.flush()
        return deepcopy(bundle)

    def list_component_bundles(self) -> list[dict]:
        return deepcopy(self._data["components"])

    def record_history(self, event: str, recipe: dict, detail: str = "", *, persist: bool = True):
        self._data["history"].append(
            {
                "timestamp": _now(),
                "event": event,
                "inspection": recipe.get("inspection", ""),
                "device": recipe.get("device", ""),
                "step": recipe.get("step", ""),
                "detail": detail,
            }
        )
        if persist:
            self.flush()

    def history(self, inspection: str = "") -> list[dict]:
        entries = self._data["history"]
        if inspection:
            entries = [item for item in entries if item.get("inspection") == inspection]
        return deepcopy(entries)

    def list_results(self) -> list[dict]:
        return deepcopy(self._data["results"])

    def get_result(self, result_id: str) -> Optional[dict]:
        result = next(
            (item for item in self._data["results"] if item.get("id") == result_id),
            None,
        )
        return deepcopy(result) if result else None

    def save_result(self, result: dict) -> dict:
        saved = deepcopy(result)
        saved.setdefault("id", uuid4().hex)
        saved.setdefault("created", _now())
        existing = next(
            (item for item in self._data["results"] if item.get("id") == saved["id"]),
            None,
        )
        if existing is None:
            self._data["results"].append(saved)
        else:
            existing.clear()
            existing.update(saved)
        self.flush()
        return deepcopy(saved)

    def delete_result(self, result_id: str) -> bool:
        result = next(
            (item for item in self._data["results"] if item.get("id") == result_id),
            None,
        )
        if result is None:
            return False
        self._data["results"].remove(result)
        self.flush()
        return True

    def overwrite_results(self, result_ids: Iterable[str], new_results: Iterable[dict], *, backup=False) -> list[dict]:
        identifiers = set(result_ids)
        replaced = [item for item in self._data["results"] if item.get("id") in identifiers]
        if backup:
            timestamp = _now()
            for item in replaced:
                archived = deepcopy(item)
                archived["backup_created"] = timestamp
                archived["backup_of"] = item.get("id", "")
                self._data["result_backups"].append(archived)
        self._data["results"] = [item for item in self._data["results"] if item.get("id") not in identifiers]
        saved = []
        for result in new_results:
            item = deepcopy(result)
            item.setdefault("id", uuid4().hex)
            item.setdefault("created", _now())
            self._data["results"].append(item)
            saved.append(deepcopy(item))
        self.flush()
        return saved

    def list_result_backups(self) -> list[dict]:
        return deepcopy(self._data["result_backups"])

    def rename_lot(self, old_name: str, new_name: str) -> int:
        old_name = str(old_name).strip()
        new_name = str(new_name).strip()
        if not old_name or not new_name:
            return 0
        changed = 0
        for collection in (self._data["results"], self._data["result_backups"], self._data["job_queue"], self._data["transfer_queue"]):
            for item in collection:
                if item.get("lot_id") == old_name:
                    item["lot_id"] = new_name
                    changed += 1
        if changed:
            self.flush()
        return changed

    def get_preferences(self) -> dict:
        return deepcopy(self._data["preferences"])

    def update_preferences(self, changes: dict) -> dict:
        for key, value in changes.items():
            if isinstance(value, dict) and isinstance(self._data["preferences"].get(key), dict):
                self._data["preferences"][key].update(deepcopy(value))
            else:
                self._data["preferences"][key] = deepcopy(value)
        self.flush()
        return self.get_preferences()

    def list_transfer_items(self) -> list[dict]:
        return deepcopy(self._data["transfer_queue"])

    def save_transfer_item(self, item: dict) -> dict:
        saved = deepcopy(item)
        saved.setdefault("id", uuid4().hex)
        saved.setdefault("created", _now())
        saved.setdefault("status", "Pending")
        existing = next(
            (entry for entry in self._data["transfer_queue"] if entry.get("id") == saved["id"]),
            None,
        )
        if existing is None:
            self._data["transfer_queue"].append(saved)
        else:
            existing.clear()
            existing.update(saved)
        self.flush()
        return deepcopy(saved)

    def remove_transfer_item(self, item_id: str) -> bool:
        item = next(
            (entry for entry in self._data["transfer_queue"] if entry.get("id") == item_id),
            None,
        )
        if item is None:
            return False
        self._data["transfer_queue"].remove(item)
        self.flush()
        return True

    def record_utility_event(self, category: str, message: str, *, severity: str = "Info") -> dict:
        event = {
            "timestamp": _now(),
            "category": str(category),
            "severity": str(severity),
            "message": str(message),
        }
        self._data["utility_events"].append(event)
        self.flush()
        return deepcopy(event)

    def utility_events(self, category: str = "") -> list[dict]:
        entries = self._data["utility_events"]
        if category:
            entries = [item for item in entries if item.get("category") == category]
        return deepcopy(entries)

    def list_jobs(self) -> list[dict]:
        return deepcopy(self._data["job_queue"])

    def save_job(self, job: dict) -> dict:
        saved = deepcopy(job)
        saved.setdefault("id", uuid4().hex)
        saved.setdefault("created", _now())
        existing = next(
            (item for item in self._data["job_queue"] if item.get("id") == saved["id"]),
            None,
        )
        if existing is None:
            self._data["job_queue"].append(saved)
        else:
            existing.clear()
            existing.update(saved)
        self.flush()
        return deepcopy(saved)

    def remove_job(self, job_id: str) -> bool:
        job = next(
            (item for item in self._data["job_queue"] if item.get("id") == job_id),
            None,
        )
        if job is None:
            return False
        self._data["job_queue"].remove(job)
        self.flush()
        return True

    def purge_jobs(self):
        self._data["job_queue"] = []
        self.flush()

    def flush(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8") as stream:
            json.dump(self._data, stream, ensure_ascii=False, indent=2)
        temporary.replace(self.path)

    def _find(self, recipe_id: str) -> Optional[dict]:
        return next((recipe for recipe in self._data["recipes"] if recipe.get("id") == recipe_id), None)

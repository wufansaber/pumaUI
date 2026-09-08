from __future__ import annotations

import json
import os
from pathlib import Path

from .modules.results_review import filter_defects, result_matches_recipe, review_summary
from .modules.run_control import default_run_setup, generate_inspection_result, validate_run_setup
from .recipe_store import RecipeStore


def run_packaged_smoke(data_root: Path, output_path: Path | None = None) -> dict:
    data_root = Path(data_root)
    store_path = data_root / "Puma9980UI" / "package-smoke-recipes.json"
    recipe = {
        "id": "package-smoke-recipe",
        "inspection": "Package Smoke Recipe",
        "device": "SMOKE-DEVICE",
        "step": "SMOKE-LAYER",
        "status": "Valid",
        "software_version": "9.8.306",
        "tests": [{"name": "Test 1", "mode": "Random"}],
    }

    checks: dict[str, bool] = {}
    store = RecipeStore(store_path)
    saved_recipe = store.save_recipe(recipe, event="Package Smoke Test")
    reopened = RecipeStore(store_path)
    loaded_recipe = reopened.get_recipe(saved_recipe["id"])
    checks["recipe_save_reload"] = bool(
        loaded_recipe and loaded_recipe.get("inspection") == recipe["inspection"]
    )

    setup = default_run_setup(loaded_recipe or recipe)
    setup.update({"lot_id": "PACKAGE-SMOKE", "wafer_id": "W01"})
    checks["run_setup_valid"] = not validate_run_setup(setup, loaded_recipe or recipe)
    result = generate_inspection_result(loaded_recipe or recipe, setup)
    checks["one_wafer_run"] = bool(
        result.get("status") == "Complete"
        and result.get("defect_count", 0) > 0
        and result_matches_recipe(result, loaded_recipe or recipe)
    )

    saved_result = reopened.save_result(result)
    final_store = RecipeStore(store_path)
    loaded_result = final_store.get_result(saved_result["id"])
    visible = filter_defects(loaded_result or {}, {"minimum_signal": 100.0})
    summary = review_summary(loaded_result or {}, visible)
    checks["result_save_reload"] = bool(
        loaded_result and loaded_result.get("defect_count") == result.get("defect_count")
    )
    checks["result_review"] = bool(
        0 < summary.get("visible", 0) <= summary.get("total", 0)
        and summary.get("total") == result.get("defect_count")
    )

    report = {
        "passed": all(checks.values()),
        "checks": checks,
        "recipe_id": saved_recipe["id"],
        "result_id": saved_result["id"],
        "defect_count": result.get("defect_count", 0),
        "visible_defect_count": summary.get("visible", 0),
        "store_path": str(store_path),
    }
    report_path = Path(output_path) if output_path else data_root / "Puma9980UI" / "package-smoke-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def packaged_smoke_main(arguments: list[str]) -> int:
    output_path = None
    if "--smoke-output" in arguments:
        index = arguments.index("--smoke-output")
        if index + 1 < len(arguments):
            output_path = Path(arguments[index + 1])
    data_root = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    try:
        report = run_packaged_smoke(data_root, output_path)
    except Exception as error:
        report_path = output_path or data_root / "Puma9980UI" / "package-smoke-report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps({"passed": False, "error": str(error)}, indent=2),
            encoding="utf-8",
        )
        return 1
    return 0 if report["passed"] else 1

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from puma_ui.package_smoke import packaged_smoke_main, run_packaged_smoke


class PackageSmokeTests(unittest.TestCase):
    def test_smoke_runs_recipe_wafer_and_review_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = run_packaged_smoke(root)

            self.assertTrue(report["passed"])
            self.assertTrue(all(report["checks"].values()))
            self.assertGreater(report["defect_count"], 0)
            self.assertTrue((root / "Puma9980UI" / "package-smoke-recipes.json").exists())

    def test_cli_writes_requested_report(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "evidence" / "smoke.json"
            old_local_app_data = os.environ.get("LOCALAPPDATA")
            os.environ["LOCALAPPDATA"] = directory
            try:
                exit_code = packaged_smoke_main(["--smoke-test", "--smoke-output", str(output)])
            finally:
                if old_local_app_data is None:
                    os.environ.pop("LOCALAPPDATA", None)
                else:
                    os.environ["LOCALAPPDATA"] = old_local_app_data

            self.assertEqual(exit_code, 0)
            self.assertTrue(json.loads(output.read_text(encoding="utf-8"))["passed"])


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

from copy import deepcopy
import importlib
import inspect
import os
import pkgutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import puma_ui
from puma_ui.modules.inspection_tests import default_test
from puma_ui.modules.inspection_tests.fourier import default_fourier_state
from puma_ui.modules.inspection_tests.light_training import default_light_training_state
from puma_ui.modules.inspection_tests.sample_plan import default_sample_plan
from puma_ui.modules.run_control import default_run_setup
from puma_ui.qt_compat import QApplication, QDialog, QMainWindow, QWidget
from puma_ui.recipe_store import RecipeStore

from manual_ui_helpers import process_events


class ManualSurfaceInventoryTests(unittest.TestCase):
    """Open every operator surface and enforce a desktop-reachable footprint."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = RecipeStore(Path(self.temp.name) / "recipes.json", default_recipes=[])
        self.recipe = self.store.new_recipe()
        test = default_test(1)
        test["status"] = "Valid"
        self.recipe.update(
            {
                "status": "Valid",
                "tests": [test],
                "test_setup_valid": True,
                "alignment": {"sites_defined": True},
                "wafer_map": {"die_pattern_defined": True, "reticle_qualification": True},
                "lot_plan": {"assignments": {"1": ["Test 1"]}},
            }
        )
        self.result = {
            "id": "result-qa",
            "recipe_id": self.recipe["id"],
            "inspection": self.recipe["inspection"],
            "device": self.recipe["device"],
            "step": self.recipe["step"],
            "status": "Complete",
            "lot_id": "LOT-QA",
            "wafer_id": "W01",
            "selected_tests": ["Test 1"],
            "feature_vector_file": "FeatureVectors.bin",
            "defects": [
                {
                    "id": 1,
                    "x": 1.0,
                    "y": 2.0,
                    "die_x": 0,
                    "die_y": 0,
                    "test": "Test 1",
                    "class_code": 0,
                    "signal": 100.0,
                    "size_um": 0.2,
                }
            ],
            "defect_count": 1,
        }

    def tearDown(self):
        for widget in list(QApplication.topLevelWidgets()):
            widget.close()
        process_events()
        self.temp.cleanup()

    @staticmethod
    def _surface_classes():
        classes = {}
        for module_info in pkgutil.walk_packages(puma_ui.__path__, puma_ui.__name__ + "."):
            module = importlib.import_module(module_info.name)
            for name, candidate in vars(module).items():
                if (
                    inspect.isclass(candidate)
                    and candidate.__module__ == module.__name__
                    and issubclass(candidate, (QDialog, QMainWindow))
                ):
                    classes[f"{module.__name__}.{name}"] = candidate
        return classes

    def _special_factory(self, name):
        from puma_ui.main_window import OverviewPreviewDialog, PumaMainWindow
        from puma_ui.modules.inspection_tests.care_areas import CareAreaCoverageDialog, PageBreakEditDialog
        from puma_ui.modules.inspection_tests.light_training import AdvancedLightOptionsDialog, LightHistogramDialog
        from puma_ui.modules.inspection_tests.sensitivity import CibParametersDialog, ChannelFusionFlavorDialog
        from puma_ui.modules.results_review.dialogs import ApplyBinnerDialog
        from puma_ui.modules.sizing.dialogs import DefectSetEditorDialog

        channels = [
            {"clip": 0, "offset": 0, "L0": 0, "K": 1, "preconvolver": "None"}
            for _ in range(3)
        ]
        sizing_state = {
            "defect_sets": [
                {"id": "set-1", "name": "Set 1", "kind": "Manual", "defects": []}
            ]
        }
        factories = {
            "PumaMainWindow": lambda: self._main_window(PumaMainWindow),
            "OverviewPreviewDialog": lambda: OverviewPreviewDialog("Preview", QWidget()),
            "AdvancedLightOptionsDialog": lambda: AdvancedLightOptionsDialog(default_light_training_state()),
            "LightHistogramDialog": lambda: LightHistogramDialog(default_light_training_state()["channels"]),
            "CibParametersDialog": lambda: CibParametersDialog(channels),
            "ChannelFusionFlavorDialog": lambda: ChannelFusionFlavorDialog(
                [{"name": "CF2", "enabled": False, "threshold": 45}], "HLAT"
            ),
            "CareAreaCoverageDialog": lambda: CareAreaCoverageDialog(
                [{"name": "CA 1", "defined_percent": 10.0, "inspected_percent": 9.8}]
            ),
            "PageBreakEditDialog": lambda: PageBreakEditDialog(
                [{"name": "PB1", "kind": "Page Break", "areas": []}], 0
            ),
            "DefectSetEditorDialog": lambda: DefectSetEditorDialog(sizing_state, "set-1"),
            "ApplyBinnerDialog": lambda: ApplyBinnerDialog(
                self.result, self.result["defects"], {1}, self.recipe
            ),
        }
        factory = factories.get(name)
        return factory() if factory else None

    def _main_window(self, window_class):
        with patch("puma_ui.main_window.RecipeStore", return_value=self.store):
            return window_class()

    def _fixture(self, parameter, class_name):
        values = {
            "active_group": 0,
            "algorithms": ["HLAT"],
            "areas": [[0.1, 0.1, 0.2, 0.2]],
            "attributes": ["Signal", "Size"],
            "available_images": ["Left", "Right"],
            "box": [0.1, 0.1, 0.2, 0.2],
            "box_index": 0,
            "boxes": [],
            "channels": [{"name": "Channel 1", "light_level": 8.0, "exposure": 1.0}],
            "columns": [("name", "Name"), ("status", "Status")],
            "count": 1,
            "cycle_images": ["Left"],
            "default_name": "Manual QA",
            "defect_set_id": "set-1",
            "defects": self.result["defects"],
            "delay_seconds": 1.0,
            "die": [0, 0],
            "die_basis": "Recipe Die",
            "die_size_um": [2000, 2000],
            "directional": False,
            "enabled": False,
            "entries": [],
            "example": {"id": 1, "name": "Example"},
            "groups": [],
            "has_recipe": True,
            "indexes": [0],
            "limits": {},
            "marked_count": 1,
            "mode": "DF",
            "noise_box": [0.1, 0.1, 0.2, 0.2],
            "options": {},
            "orientation": "As Inspected",
            "parent_name": "CA 1",
            "path": str(Path(self.temp.name) / "Manual QA"),
            "previous": "0 deg.",
            "process_layers": ["Metal1"],
            "recipe": self.recipe,
            "recipe_store": self.store,
            "recipes": [self.recipe],
            "region_names": ["R1"],
            "regions": ["R1"],
            "report": [{"name": "CA 1", "defined_percent": 10.0, "inspected_percent": 9.8}],
            "requested": "90 deg.",
            "result": self.result,
            "results": [self.result],
            "rods": default_fourier_state()["rods"],
            "rows": [],
            "rules": [],
            "sample_dies": [[0, 0]],
            "selected": [],
            "selected_die": [0, 0],
            "selected_ids": {1},
            "selection_mode": "Select Die Origin",
            "settings": {},
            "sites": [],
            "source_path": "manual-qa.klarf",
            "sources": [dict(self.result, id="result-source", lot_id="LOT-SOURCE")],
            "state": {},
            "store": self.store,
            "target": self.result,
            "test_mode": "Random",
            "test_names": ["Test 1"],
            "tests": ["Test 1"],
            "title": "Manual QA",
            "value": 10.0,
            "values": {},
            "visible_columns": {"name": True, "status": True},
            "visible_defects": self.result["defects"],
            "visible_parameters": {},
            "wafer_ids": ["W01"],
        }
        if parameter == "runtime_state":
            return {}
        if parameter == "threshold":
            return {"name": "R1", "algorithm": "HLAT", "threshold": 45.0}
        if parameter == "regions" and class_name == "ActiveRegionsDialog":
            return [[0.1, 0.1, 0.2, 0.2]]
        if parameter == "regions" and class_name == "SegmentationSetupDialog":
            return {}
        if parameter == "care_groups":
            return [{"name": "R1", "kind": "Care Area", "areas": [[0.1, 0.1, 0.2, 0.2]]}]
        if parameter == "algorithms" and class_name == "AdvancedSensitivityParametersDialog":
            return {"HLAT": ["Threshold", "Noise"]}
        if parameter == "recipe_name":
            return "Manual QA"
        if parameter == "jobs":
            return []
        if parameter == "setup":
            setup = default_run_setup(self.recipe)
            setup.update({"lot_id": "LOT-QA", "wafer_id": "W01"})
            return setup
        if parameter == "state" and class_name == "MasterSamplePlanDialog":
            return default_sample_plan()
        if parameter == "state" and class_name == "FourierFilterTrainingDialog":
            return default_fourier_state()
        if parameter == "state" and class_name == "DefectSetEditorDialog":
            return {"defect_sets": [{"id": "set-1", "name": "Set 1", "kind": "Manual", "defects": []}]}
        if parameter not in values:
            raise KeyError(f"No surface fixture for {class_name}.{parameter}")
        return deepcopy(values[parameter])

    def _construct(self, surface_class):
        special = self._special_factory(surface_class.__name__)
        if special is not None:
            return special
        arguments = []
        keywords = {}
        for parameter in inspect.signature(surface_class).parameters.values():
            if parameter.default is not inspect.Parameter.empty:
                continue
            value = self._fixture(parameter.name, surface_class.__name__)
            if parameter.kind == inspect.Parameter.KEYWORD_ONLY:
                keywords[parameter.name] = value
            else:
                arguments.append(value)
        return surface_class(*arguments, **keywords)

    def test_every_operator_surface_opens_and_fits_a_standard_desktop(self):
        failures = []
        classes = self._surface_classes()
        self.assertEqual(len(classes), 207)
        for qualified_name, surface_class in sorted(classes.items()):
            name = surface_class.__name__
            if os.environ.get("PUMA_SURFACE_TRACE"):
                print(qualified_name, flush=True)
            surface = None
            try:
                surface = self._construct(surface_class)
                surface.show()
                process_events(2)
                self.assertTrue(surface.isVisible())
                self.assertLessEqual(surface.width(), 1920, f"{name} is wider than 1920 px")
                self.assertLessEqual(surface.height(), 1080, f"{name} is taller than 1080 px")
            except Exception as exc:
                failures.append(f"{name}: {type(exc).__name__}: {exc}")
            finally:
                if surface is not None:
                    if name == "RunStatusDialog":
                        surface.timer.stop()
                        surface.finished = True
                    surface.close()
                    process_events(1)
        self.assertEqual(failures, [], "\n" + "\n".join(failures))


if __name__ == "__main__":
    unittest.main()

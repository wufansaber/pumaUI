from __future__ import annotations

import os
from pathlib import Path
import sys
from unittest.mock import patch


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from puma_ui.main_window import PumaMainWindow
from puma_ui.modules.inspection_tests import TestsSetupDialog, default_test
from puma_ui.modules.lot_plan import LotPlanDialog
from puma_ui.modules.run_control import RunOneWaferDialog, RunStatusDialog
from puma_ui.modules.recipe_lifecycle import SaveInspectionDialog
from puma_ui.modules.select_inspection import OpenInspectionRecipeDialog
from puma_ui.modules.wafer_alignment.dialogs import (
    AlignmentImagingModeDialog,
    AlignmentMenuDialog,
    AlignmentParametersDialog,
    SelectAlignmentSitesDialog,
)
from puma_ui.modules.wafer_handling.dialog import WaferHandlingDialog
from puma_ui.modules.wafer_map.dialog import (
    EditMapDialog,
    ReticleSizeDialog,
    ScribeLinesSetupDialog,
    SpecifyDieValuesDialog,
    WaferMapSetupDialog,
    WaferMapSiteSelectionDialog,
)
from puma_ui.modules.wafer_post_processing import WaferPostProcessingDialog
from puma_ui.modules.wafer_properties import WaferPropertiesDialog
from puma_ui.qt_compat import (
    QApplication,
    QCheckBox,
    QDialog,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTimer,
    Qt,
    QT_BINDING,
)
from puma_ui.recipe_store import RecipeStore

if QT_BINDING == "PySide6":
    from PySide6.QtTest import QTest
else:
    from PyQt5.QtTest import QTest


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / ".artifacts" / "operator-workflow"
STORE_PATH = OUTPUT / "runtime" / "recipes.json"


class Walkthrough:
    def __init__(self) -> None:
        self.app = QApplication.instance() or QApplication([])
        self.steps: list[tuple[str, str, str]] = []
        self.modal_errors: list[str] = []
        OUTPUT.mkdir(parents=True, exist_ok=True)
        STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        if STORE_PATH.exists():
            STORE_PATH.unlink()
        self.store = self._seed_store()
        self.window = self._make_window()
        self.window.resize(1500, 850)
        self.window.show()
        self.wait(80)

    def _seed_store(self) -> RecipeStore:
        store = RecipeStore(STORE_PATH, default_recipes=OpenInspectionRecipeDialog.RECIPES)
        recipe = next(item for item in store.list_recipes() if item["inspection"] == "_180")
        test = default_test(1)
        test["care_areas"]["groups"].append(
            {
                "name": "CA 1",
                "kind": "Care Area",
                "enabled": True,
                "areas": [[0.0, 0.0, 1.0, 1.0]],
            }
        )
        test["light_training"]["noise_box_group"] = "CA 1"
        test["fourier"]["boxes"].append(
            {"x": 0.2, "y": 0.2, "width": 0.25, "height": 0.25, "channels": [1, 2, 3]}
        )
        test["fourier"]["trained"] = True
        test["fourier_trained"] = True
        test["light_trained"] = True
        recipe.update(
            {
                "alignment": {"sites_defined": True, "mode": "DF", "status": "Valid"},
                "wafer_map": {},
                "tests": [test],
                "test_setup_valid": True,
                "lot_plan": {},
                "wafer_post_processing": {},
                "status": "Valid",
                "state": "Operator walkthrough reference recipe.",
                "dirty": False,
            }
        )
        store.save_recipe(recipe, event="Prepare operator walkthrough")
        return store

    def _make_window(self) -> PumaMainWindow:
        import puma_ui.main_window as main_window_module

        original_store = main_window_module.RecipeStore
        main_window_module.RecipeStore = lambda *args, **kwargs: self.store
        try:
            return PumaMainWindow()
        finally:
            main_window_module.RecipeStore = original_store

    def wait(self, milliseconds: int = 30) -> None:
        QTest.qWait(milliseconds)
        QApplication.processEvents()

    @staticmethod
    def normalized(text: str) -> str:
        return " ".join(text.replace(">", "").replace("<", "").split())

    def button(self, root, label: str, *, exact: bool = True) -> QPushButton:
        target = self.normalized(label)
        matches = []
        for item in root.findChildren(QPushButton):
            current = self.normalized(item.text())
            matched = current == target if exact else target in current
            if matched and item.isVisible():
                matches.append(item)
        if not matches:
            raise AssertionError(f"Visible button not found: {label!r}")
        enabled = [item for item in matches if item.isEnabled()]
        return enabled[0] if enabled else matches[0]

    def click(self, widget) -> None:
        if not widget.isEnabled():
            raise AssertionError(f"Widget is disabled: {getattr(widget, 'text', lambda: type(widget).__name__)()}")
        QTest.mouseClick(widget, Qt.LeftButton, Qt.NoModifier, widget.rect().center())
        self.wait()

    def replace_text(self, widget, text: str) -> None:
        self.click(widget)
        QTest.keyClick(widget, Qt.Key_A, Qt.ControlModifier)
        QTest.keyClicks(widget, text)
        self.wait()

    def capture(self, widget, filename: str) -> None:
        self.wait(40)
        path = OUTPUT / filename
        if not widget.grab().save(str(path)):
            raise AssertionError(f"Unable to save screenshot {path}")

    def check(self, name: str, condition: bool, detail: str) -> None:
        status = "PASS" if condition else "FAIL"
        self.steps.append((status, name, detail))
        if not condition:
            raise AssertionError(f"{name}: {detail}")

    def schedule_modal(self, expected_type, action, *, attempts: int = 200) -> None:
        def poll(remaining: int) -> None:
            modal = QApplication.activeModalWidget()
            if isinstance(modal, expected_type):
                try:
                    action(modal)
                except Exception as exc:  # keep the nested event loop from hanging
                    self.modal_errors.append(f"{expected_type.__name__}: {exc}")
                    modal.reject()
                return
            if remaining <= 0:
                self.modal_errors.append(
                    f"Timed out waiting for {expected_type.__name__}; active={type(modal).__name__ if modal else 'None'}"
                )
                if isinstance(modal, QDialog):
                    modal.reject()
                return
            QTimer.singleShot(10, lambda: poll(remaining - 1))

        QTimer.singleShot(10, lambda: poll(attempts))

    def select_recipe(self) -> None:
        self.capture(self.window, "01-recipe-overview.png")
        self.click(self.button(self.window, "Select Inspection"))
        page = self.window.workspace_stack.currentWidget()
        self.check("Select Inspection uses the main workspace", isinstance(page, OpenInspectionRecipeDialog), type(page).__name__)
        self.capture(self.window, "02-select-inspection.png")

        row = next(
            index for index in range(page.table.rowCount())
            if page.table.item(index, 0).text() == "_180"
        )
        item = page.table.item(row, 0)
        self.click_table_item(page.table, item)
        self.click(self.button(page, "Open"))
        self.check("Selected recipe loads", self.window.current_recipe.get("inspection") == "_180", self.window.current_recipe.get("inspection", ""))
        self.check("Recipe Overview is restored after Open", self.window._active_route_key == "setup", self.window._active_route_key)

    def wafer_properties(self) -> None:
        old_darkness = self.window._current_wafer_properties()["wafer_darkness_level"]

        def handle_properties(dialog: WaferPropertiesDialog) -> None:
            self.capture(dialog, "03-wafer-properties.png")
            start_laser = dialog.laser_power_slider.value()
            self.click(dialog.laser_power_slider)
            QTest.keyClick(dialog.laser_power_slider, Qt.Key_Right)
            self.check("Laser power slider changes the setting", dialog.laser_power_slider.value() != start_laser, dialog.laser_power_factor.text())
            if not dialog.dark_wafer_auto_focus.isChecked():
                self.click(dialog.dark_wafer_auto_focus)
            self.click(dialog.dark_level_slider)
            QTest.keyClick(dialog.dark_level_slider, Qt.Key_End)
            self.check("Dark wafer slider reaches Darkest", dialog.dark_level_value.text() == "Darkest", dialog.dark_level_value.text())
            self.click(self.button(dialog, "OK"))

        self.click(self.button(self.window, "Wafer"))
        self.wait(220)
        self.check(
            "Wafer menu expands as an inline drawer",
            self.window._wafer_drawer_open
            and self.window.wafer_drawer.isVisible()
            and not self.window.wafer_drawer.isWindow(),
            f"width={self.window.wafer_drawer.width()}",
        )
        self.capture(self.window, "03-wafer-drawer.png")
        self.schedule_modal(WaferPropertiesDialog, handle_properties)
        self.click(self.window.wafer_drawer_buttons["wafer_properties"])
        wafer_properties = self.window.current_recipe.get("wafer_properties", {})
        self.check("Wafer Properties persists slider state", wafer_properties.get("wafer_darkness_level") != old_darkness, wafer_properties.get("wafer_darkness_level", "not saved"))

    def home_and_setup_navigation(self) -> None:
        with patch(
            "puma_ui.main_window.QMessageBox.question", return_value=QMessageBox.Yes
        ):
            self.click(self.window.home_button)
        self.check(
            "Home opens the manual Main Menu",
            self.window._active_route_key == "home"
            and self.window.workspace_stack.currentWidget() is self.window.home_page,
            self.window._active_route_key,
        )
        self.check(
            "Main Menu exposes the four manual workflows",
            all(
                self.button(self.window.home_page, label).isVisible()
                for label in (
                    "Set Up Inspection",
                    "Run Inspection",
                    "Review Results",
                    "Utilities",
                )
            ),
            "Set Up, Run, Review, Utilities",
        )
        self.check(
            "Home hides Setup-only controls",
            self.window.left_navigation.isHidden()
            and all(not action.isVisible() for action in self.window.setup_toolbar_actions),
            "Setup panel and toolbar hidden",
        )
        self.capture(self.window, "02-home-main-menu.png")

        self.click(self.window.setup_breadcrumb)
        self.check(
            "Setup restores Recipe Overview",
            self.window._active_route_key == "setup"
            and self.window.workspace_stack.currentWidget() is self.window.overview_scroll
            and not self.window.left_navigation.isHidden(),
            self.window._active_route_key,
        )
        self.capture(self.window, "02-setup-recipe-overview.png")

    def wafer_handling_and_alignment(self) -> None:
        toolbar_button = next(
            button for button in self.window.findChildren(QPushButton)
            if button.toolTip() == "Wafer and Cassette Handling"
        )

        def handle_wafer(dialog: WaferHandlingDialog) -> None:
            self.check(
                "Mapped carrier starts with a selected slot",
                dialog.selected_port == 1 and dialog.selected_slots[1] == 25,
                f"Port {dialog.selected_port}, Slot {dialog.selected_slots[1]}",
            )
            if not dialog.read_id_check.isChecked():
                dialog.read_id_check.setFocus()
                QTest.keyClick(dialog.read_id_check, Qt.Key_Space)
                self.wait()
            self.click(dialog.load_align_button)
            self.check(
                "Load and Align moves the wafer to the chuck",
                dialog.wafer_loaded and dialog.wafer_aligned,
                dialog.wafer_state.text().replace("\n", "; "),
            )
            self.check(
                "Optional Wafer ID is read",
                bool(dialog.wafer_ids[1].get(25)),
                str(dialog.wafer_ids[1].get(25)),
            )
            self.click(dialog.advanced_button)
            self.check(
                "Wafer Handling Advanced section expands",
                dialog.advanced_laser_panel.isVisible() and dialog.advanced_dark_panel.isVisible(),
                "laser and dark-wafer controls visible",
            )
            self.capture(dialog, "04-wafer-handling.png")
            self.click(self.button(dialog, "Close"))

        self.schedule_modal(WaferHandlingDialog, handle_wafer)
        self.click(toolbar_button)
        self.check(
            "Wafer handling state returns to the main window",
            self.window.wafer_runtime_state["wafer_loaded"]
            and self.window.wafer_runtime_state["wafer_aligned"],
            str(self.window.wafer_runtime_state),
        )

        def handle_alignment(dialog: AlignmentMenuDialog) -> None:
            self.check(
                "Alignment actions recognize stored sites",
                dialog.align_wafer_button.isEnabled() and dialog.set_optics_button.isEnabled(),
                "Align and Set Optics enabled",
            )
            self.check(
                "Qualification recognizes defined test optics",
                dialog.qualify_button.isEnabled(),
                "Qualify enabled",
            )
            self.capture(dialog, "05-alignment-menu.png")

            def handle_imaging_mode(imaging: AlignmentImagingModeDialog) -> None:
                def handle_parameters(parameters: AlignmentParametersDialog) -> None:
                    def handle_sites(sites: SelectAlignmentSitesDialog) -> None:
                        self.check(
                            "Stored alignment sites load for adjustment",
                            len(sites.marked_sites) == 2,
                            f"sites={len(sites.marked_sites)}",
                        )
                        self.click(sites.next_button)
                        self.check(
                            "Next preserves site 1 and advances",
                            sites.current_site_index == 1,
                            f"site={sites.current_site_index + 1}",
                        )
                        self.click(sites.next_button)
                        self.check(
                            "Next on site 2 performs alignment",
                            sites.aligned,
                            sites.status_label.text(),
                        )
                        self.capture(sites, "05-alignment-sites-complete.png")
                        self.click(sites.finish_button)

                    self.schedule_modal(SelectAlignmentSitesDialog, handle_sites)
                    self.click(self.button(parameters, "OK"))

                self.schedule_modal(AlignmentParametersDialog, handle_parameters)
                self.click(self.button(imaging, "DF"))

            self.schedule_modal(AlignmentImagingModeDialog, handle_imaging_mode)
            with patch(
                "puma_ui.modules.wafer_alignment.dialogs.QMessageBox.question",
                return_value=QMessageBox.Yes,
            ):
                self.click(self.button(dialog, "Select Sites"))
            self.check(
                "Adjusted alignment sites return to the recipe state",
                bool(dialog.alignment_result and dialog.alignment_result.get("sites_defined")),
                str(dialog.alignment_result),
            )
            self.click(self.button(dialog, "End"))

        self.click(self.button(self.window, "Wafer"))
        self.wait(220)
        self.schedule_modal(AlignmentMenuDialog, handle_alignment)
        self.click(self.window.wafer_drawer_buttons["alignment"])

    def open_wafer_map(self) -> WaferMapSetupDialog:
        self.click(self.button(self.window, "Wafer"))
        self.wait(220)
        self.click(self.window.wafer_drawer_buttons["wafer_map"])
        page = self.window.workspace_stack.currentWidget()
        self.check("Wafer Map uses the main workspace", isinstance(page, WaferMapSetupDialog), type(page).__name__)
        self.capture(self.window, "04-wafer-map-empty.png")
        return page

    def define_die_values(self, page: WaferMapSetupDialog) -> None:
        def handle_sites(dialog: WaferMapSiteSelectionDialog) -> None:
            self.capture(dialog, "05-die-site-selection-start.png")
            self.check("Use Die Pitch requires four marks", dialog.low_mag_required == 1 and dialog.high_mag_required == 3, f"{dialog.low_mag_required}+{dialog.high_mag_required}")
            for index in range(4):
                self.click(dialog.mark_button)
                self.check(f"Mark die site {index + 1}", dialog.mark_count == index + 1, str(dialog.mark_count))
            self.check("Finish remains gated until all sites", dialog.finish_button.isEnabled(), "enabled after four marks")
            self.capture(dialog, "06-die-site-selection-complete.png")
            self.click(dialog.finish_button)

        def handle_values(dialog: SpecifyDieValuesDialog) -> None:
            self.capture(dialog, "05-specify-die-values.png")
            dialog.use_die_pitch.setFocus()
            QTest.keyClick(dialog.use_die_pitch, Qt.Key_Space)
            self.wait()
            self.check("Use Die Pitch enables X/Y input", dialog.use_die_pitch.isChecked() and dialog.x_pitch.isEnabled(), "pitch fields enabled")
            self.replace_text(dialog.x_pitch, "5100.100")
            self.replace_text(dialog.y_pitch, "16600.200")
            self.schedule_modal(WaferMapSiteSelectionDialog, handle_sites)
            self.click(self.button(dialog, "OK"))

        self.schedule_modal(SpecifyDieValuesDialog, handle_values)
        self.click(page.menu_buttons["Die Values"])
        self.check("Die pattern is defined", page.die_pattern_defined and page.die_count > 0, f"die count={page.die_count}")
        self.check("Dependent Wafer Map actions unlock", all(page.menu_buttons[name].isEnabled() for name in ["Scribe Lines", "Edit Map", "Reticle Size"]), "scribe/edit/reticle enabled")
        self.capture(self.window, "07-wafer-map-die-grid.png")

    def define_scribe_lines(self, page: WaferMapSetupDialog) -> None:
        def handle_scribe(dialog: ScribeLinesSetupDialog) -> None:
            self.capture(dialog, "08-scribe-lines-start.png")
            self.check("Scribe Finish starts disabled", not dialog.finish_button.isEnabled(), "disabled before two marks")
            self.click(dialog.mark_button)
            self.click(dialog.mark_button)
            self.check("Scribe Finish enables after two marks", dialog.finish_button.isEnabled(), f"marks={dialog.mark_count}")
            self.capture(dialog, "09-scribe-lines-complete.png")
            self.click(dialog.finish_button)

        self.schedule_modal(ScribeLinesSetupDialog, handle_scribe)
        self.click(page.menu_buttons["Scribe Lines"])
        self.check("Scribe line state is stored", page.scribe_lines_defined and page.scribe_x > 0 and page.scribe_y > 0, f"{page.scribe_x:.3f} x {page.scribe_y:.3f} um")

    def edit_map(self, page: WaferMapSetupDialog) -> None:
        before = page.die_count

        def handle_edit(dialog: EditMapDialog) -> None:
            self.capture(dialog, "10-edit-map-start.png")
            self.click(dialog.canvas)
            self.check("Clicking a die changes the valid count", dialog.valid_die_count == before - 1, f"{before} -> {dialog.valid_die_count}")
            self.check("Edit Map enables Undo", dialog.undo_button.isEnabled(), "undo enabled")
            self.click(dialog.undo_button)
            self.check("Undo restores the valid count", dialog.valid_die_count == before, str(dialog.valid_die_count))
            self.click(dialog.redo_button)
            self.check("Redo reapplies the edit", dialog.valid_die_count == before - 1, str(dialog.valid_die_count))
            self.click(dialog.allow_partial)
            full_die_count = dialog.valid_die_count
            self.check(
                "Disabling partial die removes edge intersections",
                full_die_count < before - 1,
                f"full={full_die_count}, partial={before - 1}",
            )
            self.click(dialog.allow_partial)
            self.check(
                "Enabling partial die restores intersecting edge die",
                dialog.valid_die_count == before - 1,
                f"restored={dialog.valid_die_count}",
            )
            dialog.edge_enabled.setFocus()
            QTest.keyClick(dialog.edge_enabled, Qt.Key_Space)
            self.wait()
            self.check("Edge exclusion controls enable", dialog.edge_enabled.isChecked() and dialog.apply_edge.isEnabled(), "Apply enabled")
            self.click(dialog.apply_edge)
            self.check("Edge exclusion boundary applies", dialog.canvas.show_edge_boundary, "boundary visible")
            self.capture(dialog, "11-edit-map-complete.png")
            self.click(self.button(dialog, "Finish"))

        self.schedule_modal(EditMapDialog, handle_edit)
        self.click(page.menu_buttons["Edit Map"])
        self.check("Edited die count returns to Wafer Map", page.die_count == before - 1, f"{before} -> {page.die_count}")
        self.check("Invalid die set is persisted", bool(page.invalid_die), f"invalid={len(page.invalid_die)}")

    def define_reticle(self, page: WaferMapSetupDialog) -> None:
        def handle_reticle(dialog: ReticleSizeDialog) -> None:
            self.capture(dialog, "12-reticle-start.png")
            if not dialog.reticle_qualification.isChecked():
                self.click(dialog.reticle_qualification)
            self.replace_text(dialog.reticle_width, "3")
            self.replace_text(dialog.reticle_height, "1")
            self.click(dialog.canvas)
            self.check("Reference die is selected from the map", dialog.reference_selected, dialog.reference_die_label.text())
            self.capture(dialog, "13-reticle-complete.png")
            self.click(self.button(dialog, "Finish"))

        self.schedule_modal(ReticleSizeDialog, handle_reticle)
        self.click(page.menu_buttons["Reticle Size"])
        self.check("Reticle qualification is stored", page.reticle_qualification and page.reticle_width == 3 and page.reticle_height == 1, f"{page.reticle_width} x {page.reticle_height}")
        self.capture(self.window, "14-wafer-map-complete.png")

    def finish_wafer_map(self, page: WaferMapSetupDialog) -> None:
        self.click(page.end_button)
        wafer_map = self.window.current_recipe.get("wafer_map", {})
        self.check("Wafer Map state reaches the recipe", wafer_map.get("die_pattern_defined") and wafer_map.get("scribe_lines_defined"), f"die={wafer_map.get('die_count')}")
        self.check("Wafer Map returns to Recipe Overview", self.window._active_route_key == "setup", self.window._active_route_key)

    def tests_page(self) -> None:
        self.click(self.window.tests_button)
        page = self.window.workspace_stack.currentWidget()
        self.check("Tests uses the main workspace", isinstance(page, TestsSetupDialog), type(page).__name__)
        expected = ["NEF Classifiers", "iDO Classifier", "Fourier Filter Training", "Care Areas", "Light Training", "Segmentation", "Sample Plan", "Sensitivity Setup"]
        visible = {self.normalized(button.text()) for button in page.findChildren(QPushButton) if button.isVisible()}
        missing = [name for name in expected if self.normalized(name) not in visible]
        self.check("Tests exposes the manual modules", not missing, f"missing={missing}")
        parameter_labels = {
            page.matrix.item(row, 0).text()
            for row in range(page.matrix.rowCount())
            if page.matrix.item(row, 0) is not None
        }
        required_parameters = {
            "    NEF Classifier(s)",
            "    iDO Classifier",
            "    DBB Classifier",
            "    # Groups",
        }
        self.check(
            "Tests exposes classifier and grouping parameters",
            required_parameters.issubset(parameter_labels),
            f"missing={sorted(required_parameters - parameter_labels)}",
        )
        grouping_row = next(
            index
            for index, (_label, key, _kind) in enumerate(page.PARAMETER_ROWS)
            if key == "run_unsupervised_grouping"
        )
        grouping_check = page.matrix.cellWidget(grouping_row, 1).findChild(QCheckBox)
        self.click(grouping_check)
        self.check(
            "Unsupervised Grouping enables Feature Vectors",
            page.tests[0]["run_unsupervised_grouping"]
            and page.tests[0]["save_feature_vectors"],
            f"groups={page.tests[0]['unsupervised_groups']}",
        )
        self.window.copy_test_action.trigger()
        self.check(
            "Edit Copy Test enables Paste Test",
            self.window.paste_test_action.isEnabled(),
            "Edit menu copy/paste path active",
        )
        self.capture(self.window, "15-tests.png")
        self.click(self.button(page, "End"))
        self.check("Completed test remains valid", self.window.current_recipe.get("test_setup_valid") is True, self.window.current_recipe.get("state", ""))

    def lot_plan(self) -> None:
        self.click(self.window.lot_plan_button)
        page = self.window.workspace_stack.currentWidget()
        self.check("Lot Plan uses the main workspace", isinstance(page, LotPlanDialog), type(page).__name__)
        item = page.matrix.item(0, 0)
        self.click_table_check_item(page.matrix, item)
        self.click(page.repeat_enabled)
        self.replace_text(page.repeat_count, "2")
        self.click(page.apply_count)
        self.check("Lot assignment and repeat are accepted", bool(page.state["assignments"]) and page.state["repeat_enabled"], page.total_runs.text())
        self.capture(self.window, "16-lot-plan.png")
        self.click(self.button(page, "OK"))
        assignments = self.window.current_recipe.get("lot_plan", {}).get("assignments", {})
        self.check("Lot Plan state reaches the recipe", bool(assignments), str(assignments))
        self.check("Wafer Post Processing unlocks", self.window.wafer_post_processing_button.isEnabled(), "enabled after assignment")

    def wafer_post_processing(self) -> None:
        self.click(self.window.wafer_post_processing_button)
        page = self.window.workspace_stack.currentWidget()
        self.check("Wafer Post Processing uses the main workspace", isinstance(page, WaferPostProcessingDialog), type(page).__name__)
        row = next(index for index, operation in enumerate(page.state["operations"]) if operation["name"] == "Clustering")
        enabled_item = page.operations.item(row, 0)
        self.click_table_check_item(page.operations, enabled_item)
        self.check("A post-processing operation can be enabled", page.state["operations"][row]["enabled"], page.state["operations"][row]["name"])
        self.capture(self.window, "17-wafer-post-processing.png")
        self.click(self.button(page, "OK"))
        enabled = [item["name"] for item in self.window.current_recipe["wafer_post_processing"]["operations"] if item.get("enabled")]
        self.check("Post-processing state reaches the recipe", "Clustering" in enabled, str(enabled))

    def setup_run(self) -> None:
        self.check("Setup Run prerequisite is satisfied", self.window.setup_run_button.isEnabled(), self.window.current_recipe.get("state", ""))
        self.click(self.window.setup_run_button)
        page = self.window.workspace_stack.currentWidget()
        self.check("Setup Run uses the main workspace", isinstance(page, RunOneWaferDialog), type(page).__name__)
        self.replace_text(page.lot_id, "QA-OPERATOR-001")
        self.replace_text(page.wafer_id, "W25")
        if page.instant_review.isChecked():
            self.click(page.instant_review)
        self.capture(self.window, "18-setup-run.png")

        def handle_status(dialog: RunStatusDialog) -> None:
            self.capture(dialog, "19-run-status-start.png")
            self.click(dialog.pause_button)

            def continue_when_paused(remaining: int = 300) -> None:
                if dialog.paused:
                    self.check("Pause waits for alignment completion", dialog.progress_value >= 16, f"progress={dialog.progress_value}")
                    self.click(dialog.pause_button)
                    wait_for_finish()
                    return
                if remaining <= 0:
                    self.modal_errors.append("Run did not enter paused state")
                    dialog.reject()
                    return
                QTimer.singleShot(10, lambda: continue_when_paused(remaining - 1))

            def wait_for_finish(remaining: int = 500) -> None:
                if dialog.finished and dialog.finish_button.isEnabled():
                    self.capture(dialog, "20-run-status-complete.png")
                    self.click(dialog.finish_button)
                    return
                if remaining <= 0:
                    self.modal_errors.append("Run did not complete")
                    dialog.reject()
                    return
                QTimer.singleShot(10, lambda: wait_for_finish(remaining - 1))

            QTimer.singleShot(10, continue_when_paused)

        self.schedule_modal(RunStatusDialog, handle_status, attempts=400)
        self.click(self.button(page, "Run One Wafer"))
        results = self.store.list_results()
        self.check("Repeated inspection results are saved", len(results) == 2, f"results={len(results)}")
        self.check("Run completes successfully", all(item.get("status") == "Complete" for item in results), str([item.get("status") for item in results]))
        self.check("Run returns to Recipe Overview", self.window._active_route_key == "setup", self.window._active_route_key)
        self.capture(self.window, "21-recipe-overview-after-run.png")

    def save_inspection(self) -> None:
        def handle_save(dialog: SaveInspectionDialog) -> None:
            self.replace_text(dialog.comments_edit, "Verified by operator workflow QA")
            self.capture(dialog, "22-save-inspection.png")
            self.click(self.button(dialog, "Save"))

        self.schedule_modal(SaveInspectionDialog, handle_save)
        with patch(
            "puma_ui.main_window.QMessageBox.question",
            return_value=QMessageBox.Yes,
        ):
            self.click(self.window.save_inspection_button)
        self.check("Save clears the recipe dirty state", not self.window.current_recipe.get("dirty"), str(self.window.current_recipe.get("dirty")))
        saved = self.store.get_recipe(self.window.current_recipe.get("id", ""))
        self.check("Saved recipe can be reloaded", saved is not None, self.window.current_recipe.get("inspection", ""))
        self.check(
            "Save preserves completed workflow components",
            bool(saved.get("wafer_map", {}).get("die_pattern_defined"))
            and bool(saved.get("tests"))
            and bool(saved.get("lot_plan", {}).get("assignments"))
            and bool(saved.get("wafer_post_processing", {}).get("operations")),
            "Wafer Map, Tests, Lot Plan, and WPP present",
        )

    def click_table_item(self, table: QTableWidget, item) -> None:
        rect = table.visualItemRect(item)
        QTest.mouseClick(table.viewport(), Qt.LeftButton, Qt.NoModifier, rect.center())
        self.wait()

    def click_table_check_item(self, table: QTableWidget, item) -> None:
        rect = table.visualItemRect(item)
        point = rect.center()
        point.setX(rect.left() + 12)
        QTest.mouseClick(table.viewport(), Qt.LeftButton, Qt.NoModifier, point)
        self.wait()

    def write_report(self) -> None:
        if self.modal_errors:
            for error in self.modal_errors:
                self.steps.append(("FAIL", "Modal interaction", error))
        passed = sum(status == "PASS" for status, _name, _detail in self.steps)
        failed = sum(status == "FAIL" for status, _name, _detail in self.steps)
        lines = [
            "# Operator Workflow QA",
            "",
            "This walkthrough uses real Qt mouse and keyboard events against the source UI and an isolated recipe store.",
            "",
            f"- Passed: {passed}",
            f"- Failed: {failed}",
            f"- Result: {'PASS' if failed == 0 else 'FAIL'}",
            "",
            "## Steps",
            "",
        ]
        lines.extend(f"- [{status}] {name}: {detail}" for status, name, detail in self.steps)
        lines.extend(
            [
                "",
                "## Scope",
                "",
                "Select Inspection -> Home/Main Menu -> Setup/Recipe Overview -> Wafer Properties -> Wafer Handling -> Alignment -> Wafer Map (Die Values, Scribe Lines, Edit Map, Reticle Size) -> Tests -> Lot Plan -> Wafer Post Processing -> Setup Run -> Run Status -> Save Inspection.",
                "",
                "The workflow does not access inspection hardware or production recipe storage.",
            ]
        )
        (OUTPUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def run(self) -> int:
        try:
            self.select_recipe()
            self.home_and_setup_navigation()
            self.wafer_properties()
            self.wafer_handling_and_alignment()
            wafer_map = self.open_wafer_map()
            self.define_die_values(wafer_map)
            self.define_scribe_lines(wafer_map)
            self.edit_map(wafer_map)
            self.define_reticle(wafer_map)
            self.finish_wafer_map(wafer_map)
            self.tests_page()
            self.lot_plan()
            self.wafer_post_processing()
            self.setup_run()
            self.save_inspection()
            if self.modal_errors:
                raise AssertionError("; ".join(self.modal_errors))
            return 0
        except Exception as exc:
            self.steps.append(("FAIL", "Walkthrough stopped", str(exc)))
            return 1
        finally:
            self.write_report()
            self.window.close()
            self.app.quit()


def main() -> int:
    return Walkthrough().run()


if __name__ == "__main__":
    raise SystemExit(main())

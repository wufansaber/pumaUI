from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import tempfile
from typing import Optional

from ...qt_compat import (
    QAbstractItemView,
    QCheckBox,
    QColor,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMenu,
    QMessageBox,
    QPainter,
    QPen,
    QPixmap,
    QPrintDialog,
    QPrinter,
    QPushButton,
    QSpinBox,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    Qt,
    QVBoxLayout,
    QWidget,
)
from ...recipe_store import RecipeStore
from ...widgets import ClassicButton
from ..wafer_post_processing import validate_wpp


BASE_COMPONENT_NAMES = ["Wafer Layout", "Alignment", "Data Analysis", "Lot Plan"]


def component_names_for_recipe(recipe: dict, *, test_count: int | None = None) -> list[str]:
    count = max(1, int(test_count if test_count is not None else len(recipe.get("tests") or [])))
    names = list(BASE_COMPONENT_NAMES)
    for number in range(1, count + 1):
        names.extend(
            [
                f"Test {number}",
                f"{number}-Care Area",
                f"{number}-Sensitivity",
                f"{number}-Sample Plan",
            ]
        )
    return names


COMPONENT_NAMES = component_names_for_recipe({})


def _test_component_parts(name: str):
    if name.startswith("Test "):
        try:
            return int(name.split()[-1]) - 1, "test"
        except ValueError:
            return None
    for suffix, key in (
        ("-Care Area", "care_areas"),
        ("-Sensitivity", "sensitivity"),
        ("-Sample Plan", "sample_plan"),
    ):
        if name.endswith(suffix):
            try:
                return int(name[: -len(suffix)]) - 1, key
            except ValueError:
                return None
    return None


def component_value(recipe: dict, name: str):
    direct_keys = {
        "Wafer Layout": "wafer_map",
        "Alignment": "alignment",
        "Data Analysis": "wafer_post_processing",
        "Lot Plan": "lot_plan",
    }
    if name in direct_keys:
        return deepcopy(recipe.get(direct_keys[name]) or {})
    parts = _test_component_parts(name)
    if parts is None:
        return None
    index, key = parts
    tests = recipe.get("tests") or []
    if index < 0 or index >= len(tests):
        return None
    test = tests[index]
    return deepcopy(test if key == "test" else test.get(key) or {})


def component_status(recipe: dict, name: str) -> tuple[bool, str]:
    value = component_value(recipe, name)
    if not value:
        return False, "Component is not defined"
    if name == "Wafer Layout":
        ready = bool(value.get("die_pattern_defined")) or (
            recipe.get("wafer_properties") or {}
        ).get("type") == "Blank"
    elif name == "Alignment":
        ready = bool(value.get("sites_defined"))
    elif name == "Data Analysis":
        active_tests = [
            test for test in recipe.get("tests", [])
            if test.get("mode") != "No Test"
        ]
        ready = not validate_wpp(value, len(active_tests))
    elif name == "Lot Plan":
        ready = bool(recipe.get("lot_plan_valid")) or bool(value.get("assignments"))
    else:
        parts = _test_component_parts(name)
        index, key = parts
        test = (recipe.get("tests") or [])[index]
        if key == "test":
            ready = test.get("status") == "Valid"
        elif key == "care_areas":
            ready = bool(value.get("groups"))
        elif key == "sensitivity":
            ready = bool(value.get("regions"))
        else:
            ready = bool(value) and not value.get("validation_errors")
    return ready, "" if ready else "Not valid for Run"


def component_file_name(component_name: str, base_name: str) -> str:
    """Wafer components use the recipe file name. Test components append the test number."""
    parts = _test_component_parts(component_name)
    if parts is None:
        return base_name
    index, _key = parts
    return f"{base_name}{index + 1}"


def component_display_name(component_name: str) -> str:
    if component_name.startswith("Test "):
        return component_name
    for suffix, label in (
        ("-Care Area", "Care Area"),
        ("-Sensitivity", "Sensitivity"),
        ("-Sample Plan", "Sample Plan"),
    ):
        if component_name.endswith(suffix):
            return label
    return component_name


def _dialog_style() -> str:
    # The window tone is per dialog (the callers replace the base colour); every
    # control inside is styled by puma_ui.theme so the dialogs match the shell.
    return """
        QDialog { background: #d8ead4; }
    """


class RecipeGenerationDialog(QDialog):
    def __init__(self, has_recipe: bool, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.action = ""
        self.setWindowTitle("Inspection Recipe Setup")
        self.setFixedSize(280, 390)
        self.setStyleSheet(_dialog_style().replace("#d8ead4", "#d7d4c9"))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)
        title = QLabel("Create or modify an inspection recipe")
        title.setStyleSheet("font-weight: 700;")
        layout.addWidget(title)

        actions = [
            ("New Inspection", "new", True),
            ("Save Copy As...", "copy", has_recipe),
            ("Create Derivative", "derivative", has_recipe),
            ("Import Recipe", "import", True),
            ("Extract Components", "extract", has_recipe),
            ("Insert Components", "insert", has_recipe),
            ("Recipe History", "history", True),
        ]
        for label, action, enabled in actions:
            button = ClassicButton(label, arrow=action in {"import", "extract", "insert"})
            button.setEnabled(enabled)
            button.clicked.connect(lambda checked=False, value=action: self._choose(value))
            layout.addWidget(button)
        layout.addStretch(1)
        close = ClassicButton("End")
        close.clicked.connect(self.reject)
        layout.addWidget(close)

    def _choose(self, action: str):
        self.action = action
        self.accept()


class SaveInspectionDialog(QDialog):
    def __init__(self, recipe: dict, *, save_copy: bool = False, derivative: bool = False, recipe_store=None, parent=None):
        super().__init__(parent)
        self.recipe_values = None
        self.save_copy = save_copy
        self.derivative = derivative
        self.original_name = recipe.get("inspection", "New")
        self.recipe_status = str(recipe.get("status", "Incomplete"))
        self.recipe_state = str(recipe.get("state", "Recipe setup is incomplete."))
        self.recipe_store = recipe_store
        self.available_recipes = (
            recipe_store.list_recipes() if recipe_store is not None else [deepcopy(recipe)]
        )
        self.setWindowTitle("Create Derivative Inspection" if derivative else "Save Inspection Recipe")
        self.resize(780, 620)
        self.setMinimumSize(700, 560)
        self.setStyleSheet(_dialog_style().replace("#d8ead4", "#efede2"))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 22, 26, 18)
        layout.setSpacing(14)
        form = QGridLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        suggested = recipe.get("inspection", "New")
        if save_copy:
            suggested = f"{suggested}_Copy"
        if derivative:
            suggested = f"{suggested}_Derivative"
        self.name_edit = QLineEdit(suggested)
        self.device_edit = QLineEdit(recipe.get("device", "Device1"))
        self.step_edit = QLineEdit(recipe.get("step", "Layer1"))
        self.approval_combo = QComboBox()
        self.approval_combo.addItems(["Engineering", "Production", "Development"])
        self.approval_combo.setCurrentText(recipe.get("approval", "Engineering"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Normal", "Derivative", "Imported"])
        self.type_combo.setCurrentText("Derivative" if derivative else recipe.get("recipe_type", "Normal"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All Recipes", "Normal", "FEM", "PWQ"])
        self.filter_combo.setCurrentText(recipe.get("save_filter", "All Recipes"))
        self.comments_edit = QLineEdit(recipe.get("comments", ""))
        self.comments_edit.setPlaceholderText("Version, change reason, or operator note")

        for row, (label, widget) in enumerate(
            [
                ("Inspection Name:", self.name_edit),
                ("Device Name:", self.device_edit),
                ("Layer / Step:", self.step_edit),
                ("Approval:", self.approval_combo),
                ("Recipe Type:", self.type_combo),
                ("Recipe Filter:", self.filter_combo),
                ("Comments:", self.comments_edit),
            ]
        ):
            form.addWidget(QLabel(label), row, 0, alignment=Qt.AlignRight)
            form.addWidget(widget, row, 1)
        layout.addLayout(form)

        browser = QGridLayout()
        browser.addWidget(QLabel("Existing Devices"), 0, 0)
        browser.addWidget(QLabel("Existing Steps"), 0, 1)
        browser.addWidget(QLabel("Recipes at Device / Step"), 0, 2)
        self.device_list = QListWidget()
        self.step_list = QListWidget()
        self.recipe_table = QTableWidget(0, 3)
        self.recipe_table.setHorizontalHeaderLabels(["Inspection", "State", "Approval"])
        self.recipe_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.recipe_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.recipe_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.recipe_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.recipe_table.customContextMenuRequested.connect(self._show_recipe_operations)
        self.recipe_table.itemSelectionChanged.connect(self._recipe_selected)
        browser.addWidget(self.device_list, 1, 0)
        browser.addWidget(self.step_list, 1, 1)
        browser.addWidget(self.recipe_table, 1, 2)
        browser.setColumnStretch(2, 2)
        layout.addLayout(browser, 1)
        self.device_list.currentTextChanged.connect(self._device_selected)
        self.step_list.currentTextChanged.connect(self._step_selected)
        self.filter_combo.currentTextChanged.connect(self._refresh_recipe_browser)
        self._populate_devices(recipe.get("device", "Device1"), recipe.get("step", "Layer1"))

        state_row = QHBoxLayout()
        state_row.addWidget(QLabel("State:"))
        self.state_label = QLabel(self.recipe_status)
        self.state_label.setWordWrap(True)
        state_row.addWidget(self.state_label, 1)
        self.more_button = QPushButton("More")
        self.more_button.setEnabled(self.recipe_status != "Valid")
        self.more_button.clicked.connect(self._show_status_details)
        state_row.addWidget(self.more_button)
        layout.addLayout(state_row)

        note = QLabel(
            "The first alignment site or die origin must be reselected after saving."
            if derivative
            else "The recipe name, device, and process step identify the saved recipe."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch(1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        ok = QPushButton("Save")
        ok.setFixedWidth(94)
        ok.clicked.connect(self._accept)
        cancel = QPushButton("Cancel")
        cancel.setFixedWidth(94)
        cancel.clicked.connect(self.reject)
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)

    def _populate_devices(self, selected_device: str, selected_step: str):
        devices = sorted({str(item.get("device") or "Device1") for item in self.available_recipes})
        if selected_device and selected_device not in devices:
            devices.append(selected_device)
        self.device_list.blockSignals(True)
        self.device_list.clear()
        self.device_list.addItems(devices)
        matches = self.device_list.findItems(selected_device, Qt.MatchExactly)
        if matches:
            self.device_list.setCurrentItem(matches[0])
        elif self.device_list.count():
            self.device_list.setCurrentRow(0)
        self.device_list.blockSignals(False)
        self._populate_steps(self.device_list.currentItem().text() if self.device_list.currentItem() else selected_device, selected_step)

    def _populate_steps(self, device: str, selected_step: str = ""):
        steps = sorted({
            str(item.get("step") or "Layer1")
            for item in self.available_recipes if str(item.get("device") or "Device1") == device
        })
        if selected_step and selected_step not in steps:
            steps.append(selected_step)
        self.step_list.blockSignals(True)
        self.step_list.clear()
        self.step_list.addItems(steps)
        matches = self.step_list.findItems(selected_step, Qt.MatchExactly)
        if matches:
            self.step_list.setCurrentItem(matches[0])
        elif self.step_list.count():
            self.step_list.setCurrentRow(0)
        self.step_list.blockSignals(False)
        self._refresh_recipe_browser()

    def _device_selected(self, device: str):
        if not device:
            return
        self.device_edit.setText(device)
        self._populate_steps(device)

    def _step_selected(self, step: str):
        if step:
            self.step_edit.setText(step)
        self._refresh_recipe_browser()

    def _filtered_recipes(self):
        device = self.device_list.currentItem().text() if self.device_list.currentItem() else self.device_edit.text().strip()
        step = self.step_list.currentItem().text() if self.step_list.currentItem() else self.step_edit.text().strip()
        recipe_filter = self.filter_combo.currentText()
        return [
            item for item in self.available_recipes
            if str(item.get("device") or "Device1") == device
            and str(item.get("step") or "Layer1") == step
            and (
                recipe_filter == "All Recipes"
                or str(item.get("recipe_type") or "Normal") == recipe_filter
            )
        ]

    def _refresh_recipe_browser(self):
        rows = self._filtered_recipes()
        self.recipe_table.setRowCount(len(rows))
        for row, recipe in enumerate(rows):
            name = QTableWidgetItem(str(recipe.get("inspection") or ""))
            name.setData(Qt.UserRole, recipe.get("id"))
            self.recipe_table.setItem(row, 0, name)
            self.recipe_table.setItem(row, 1, QTableWidgetItem(str(recipe.get("status") or "Incomplete")))
            self.recipe_table.setItem(row, 2, QTableWidgetItem(str(recipe.get("approval") or "Engineering")))

    def _recipe_selected(self):
        row = self.recipe_table.currentRow()
        if row < 0:
            return
        name = self.recipe_table.item(row, 0).text()
        recipe = next((item for item in self._filtered_recipes() if item.get("inspection") == name), None)
        if recipe is None:
            return
        self.name_edit.setText(name)
        self.recipe_status = str(recipe.get("status") or "Incomplete")
        self.recipe_state = str(recipe.get("state") or "")
        self.state_label.setText(self.recipe_status)
        self.more_button.setEnabled(self.recipe_status != "Valid")

    def _show_recipe_operations(self, position):
        if self.recipe_table.currentRow() < 0:
            return
        menu = QMenu(self)
        select = menu.addAction("Save Recipe")
        path = menu.addAction("Open in Explorer")
        refresh = menu.addAction("Refresh")
        delete = menu.addAction("Delete")
        action = menu.exec(self.recipe_table.viewport().mapToGlobal(position)) if hasattr(menu, "exec") else menu.exec_(self.recipe_table.viewport().mapToGlobal(position))
        if action == select:
            self._recipe_selected()
            self.name_edit.setFocus()
        elif action == path:
            device = self.device_edit.text().strip()
            step = self.step_edit.text().strip()
            QMessageBox.information(self, "Recipe Path", f"Local Recipes / {device} / {step}")
        elif action == refresh:
            if self.recipe_store is not None:
                self.available_recipes = self.recipe_store.list_recipes()
            self._populate_devices(self.device_edit.text().strip(), self.step_edit.text().strip())
        elif action == delete:
            row = self.recipe_table.currentRow()
            recipe_id = self.recipe_table.item(row, 0).data(Qt.UserRole)
            answer = QMessageBox.question(
                self,
                "Delete Confirmation",
                "Delete the selected inspection recipe?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer == QMessageBox.Yes and recipe_id and self.recipe_store is not None:
                self.recipe_store.delete_recipe(recipe_id)
                self.available_recipes = self.recipe_store.list_recipes()
                self._populate_devices(self.device_edit.text().strip(), self.step_edit.text().strip())

    def _show_status_details(self):
        QMessageBox.information(
            self,
            "Recipe Status Information",
            self.recipe_state or "Recipe setup is incomplete.",
        )

    def _accept(self):
        name = self.name_edit.text().strip()
        device = self.device_edit.text().strip()
        step = self.step_edit.text().strip()
        if not name or not device or not step:
            QMessageBox.warning(self, "Save Inspection Recipe", "Inspection, Device, and Layer are required.")
            return
        if name.startswith("_") and (self.save_copy or self.derivative or name != self.original_name):
            QMessageBox.warning(
                self,
                "Save Inspection Recipe",
                "Inspection names cannot start with an underscore because that prefix is reserved for default files.",
            )
            return
        if len(name) > 80:
            QMessageBox.warning(self, "Save Inspection Recipe", "Inspection names can contain at most 80 characters.")
            return
        self.recipe_values = {
            "inspection": name,
            "device": device,
            "step": step,
            "approval": self.approval_combo.currentText(),
            "recipe_type": self.type_combo.currentText(),
            "save_filter": self.filter_combo.currentText(),
            "comments": self.comments_edit.text().strip(),
        }
        self.accept()


class InspectionPropertiesDialog(QDialog):
    def __init__(self, recipe: dict, history_callback=None, parent=None):
        super().__init__(parent)
        self.result_values = None
        self.original_name = str(recipe.get("inspection", "New"))
        self.setWindowTitle("Inspection Properties")
        self.setFixedSize(620, 440)
        self.setStyleSheet(_dialog_style().replace("#d8ead4", "#efede2"))

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 18)
        root.setSpacing(12)

        title = QLabel("Inspection Properties")
        title.setStyleSheet("font-size: 13px; font-weight: 700; text-decoration: underline;")
        root.addWidget(title)

        identity = QFrame()
        identity.setFrameShape(QFrame.StyledPanel)
        form = QGridLayout(identity)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(9)
        self.name_edit = QLineEdit(self.original_name)
        self.device_edit = QLineEdit(str(recipe.get("device", "Device1")))
        self.step_edit = QLineEdit(str(recipe.get("step", "Layer1")))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Normal", "Derivative", "Imported"])
        self.type_combo.setCurrentText(str(recipe.get("recipe_type", "Normal")))
        self.approval_combo = QComboBox()
        self.approval_combo.addItems(["Engineering", "Production", "Development"])
        self.approval_combo.setCurrentText(str(recipe.get("approval", "Engineering")))
        for row, (label, widget) in enumerate([
            ("Recipe Name:", self.name_edit),
            ("Device Name:", self.device_edit),
            ("Layer Name:", self.step_edit),
            ("Recipe Type:", self.type_combo),
            ("Approval:", self.approval_combo),
        ]):
            form.addWidget(QLabel(label), row, 0, alignment=Qt.AlignRight)
            form.addWidget(widget, row, 1)
        root.addWidget(identity)

        details = QGridLayout()
        for row, (label, value) in enumerate([
            ("Creation Time:", recipe.get("date_created", "-")),
            ("Last Modification:", recipe.get("last_modified", "-")),
            ("Software Version:", recipe.get("software_version", "9.8.306")),
            ("Load/Save Status:", recipe.get("status", "Incomplete")),
        ]):
            details.addWidget(QLabel(label), row, 0, alignment=Qt.AlignRight)
            value_label = QLabel(str(value or "-"))
            value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            details.addWidget(value_label, row, 1)
        root.addLayout(details)

        footer = QHBoxLayout()
        history = QPushButton("History Log")
        history.setEnabled(history_callback is not None)
        if history_callback is not None:
            history.clicked.connect(history_callback)
        footer.addWidget(history)
        footer.addStretch(1)
        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(self._accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        footer.addWidget(apply_button)
        footer.addWidget(cancel)
        root.addLayout(footer)

    def _accept(self):
        name = self.name_edit.text().strip()
        device = self.device_edit.text().strip()
        step = self.step_edit.text().strip()
        if not name or not device or not step:
            QMessageBox.warning(self, "Inspection Properties", "Recipe, Device, and Layer names are required.")
            return
        if name.startswith("_") and name != self.original_name:
            QMessageBox.warning(
                self,
                "Inspection Properties",
                "Recipe names beginning with an underscore are reserved for default files.",
            )
            return
        if len(name) > 80:
            QMessageBox.warning(self, "Inspection Properties", "Recipe names can contain at most 80 characters.")
            return
        self.result_values = {
            "inspection": name,
            "device": device,
            "step": step,
            "recipe_type": self.type_combo.currentText(),
            "approval": self.approval_combo.currentText(),
        }
        self.accept()


IMPORT_RECIPE_SOURCES = (
    {
        "kind": "puma",
        "source_tool": "Puma 9980",
        "origin_tool": "Puma 9980",
        "inspection": "Deep_9980",
        "device": "Device1",
        "step": "Layer1",
    },
    {
        "kind": "brightfield",
        "source_tool": "Brightfield Tool",
        "origin_tool": "Brightfield",
        "inspection": "105_Non_UV",
        "device": "xyz",
        "step": "RLT",
    },
)


def _green_check_image() -> str:
    path = Path(tempfile.gettempdir()) / "puma_ui_green_check.png"
    if not path.exists():
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(QPen(QColor("#1f8a32"), 1))
        painter.setBrush(QColor("#2f9e3f"))
        painter.drawRoundedRect(1, 1, 14, 14, 2, 2)
        painter.setPen(QPen(QColor("#ffffff"), 2))
        painter.drawLine(4, 8, 7, 12)
        painter.drawLine(7, 12, 12, 4)
        painter.end()
        pixmap.save(str(path), "PNG")
    return path.as_posix()


class ImportRecipeSourceDialog(QDialog):
    """Choose a recipe from another Puma 9980 tool or from a Brightfield tool."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected = None
        self.setWindowTitle("Import Recipe")
        self.setFixedSize(520, 280)
        self.setStyleSheet(_dialog_style().replace("#d8ead4", "#efede2"))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        note = QLabel(
            "Select a recipe from another Puma 9980 tool or from a Brightfield tool."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        self.table = QTableWidget(len(IMPORT_RECIPE_SOURCES), 4)
        self.table.setHorizontalHeaderLabels(["Recipe", "Device", "Layer", "Source"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.doubleClicked.connect(self._accept)
        for row, source in enumerate(IMPORT_RECIPE_SOURCES):
            for column, key in enumerate(("inspection", "device", "step", "source_tool")):
                self.table.setItem(row, column, QTableWidgetItem(source[key]))
        self.table.selectRow(0)
        layout.addWidget(self.table, 1)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        open_button = QPushButton("Open")
        open_button.clicked.connect(self._accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(open_button)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)

    def _accept(self):
        row = self.table.currentRow()
        if row < 0:
            return
        self.selected = dict(IMPORT_RECIPE_SOURCES[row])
        self.accept()


class RecipeImportDialog(QDialog):
    """Brightfield recipe component picker."""

    def __init__(self, parent=None, device="xyz", layer="RLT", recipe="105_Non_UV"):
        super().__init__(parent)
        self.result_values = None
        self.source_tool = "Brightfield Tool"
        self.setWindowTitle("Puma Recipe Import")
        self.setFixedSize(440, 500)
        check_image = _green_check_image()
        self.setStyleSheet(
            "QDialog { background: #efe8d4; color: #111111; font-family: Arial; font-size: 11px; }"
            "QLabel#identityName { min-width: 72px; }"
            "QLineEdit#recipeIdentity { background: transparent; border: none; min-height: 18px; }"
            "QGroupBox { color: #1d4f9c; font-weight: 600; border: 1px solid #9a9a9a;"
            " border-radius: 6px; margin-top: 12px; padding: 12px 8px 8px 8px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }"
            "QCheckBox { spacing: 8px; color: #111111; font-weight: 400; }"
            "QCheckBox::indicator { width: 16px; height: 16px; }"
            "QCheckBox::indicator:unchecked { background: white; border: 1px solid #6a6a6a; }"
            f"QCheckBox::indicator:checked {{ image: url({check_image}); }}"
            "QPushButton { background: #f7f7f7; border: 1px solid #7f9db9; border-radius: 3px;"
            " min-height: 32px; padding: 2px 10px; font-weight: 600; }"
            "QPushButton:default { border: 2px solid #3d6ea5; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(8)

        identity = QGridLayout()
        identity.setHorizontalSpacing(12)
        identity.setVerticalSpacing(4)
        self.device_name = QLineEdit(device)
        self.step_name = QLineEdit(layer)
        self.recipe_name = QLineEdit(recipe)
        for row, (label, widget) in enumerate(
            (("Device:", self.device_name), ("Layer:", self.step_name), ("Recipe:", self.recipe_name))
        ):
            name = QLabel(label)
            name.setObjectName("identityName")
            widget.setObjectName("recipeIdentity")
            identity.addWidget(name, row, 0, alignment=Qt.AlignLeft)
            identity.addWidget(widget, row, 1)
        layout.addLayout(identity)

        self.component_checks = []
        components = QGroupBox("Select Recipe Components:")
        component_row = QHBoxLayout(components)
        component_row.setContentsMargins(12, 16, 12, 10)
        left = QVBoxLayout()
        left.setSpacing(8)
        for name in ("Registration", "Wafer layout", "Data Analysis", "Lot Plan"):
            left.addWidget(self._component_check(name))
        left.addStretch(1)
        tests = QGroupBox("Test Components:")
        test_layout = QVBoxLayout(tests)
        test_layout.setContentsMargins(10, 16, 10, 10)
        test_layout.setSpacing(8)
        self.test_data_check = self._component_check("Test Data")
        self.test_data_check.toggled.connect(self._sync_test_components)
        test_layout.addWidget(self.test_data_check)
        self.care_areas_check = self._component_check("Care Areas")
        self.sample_plan_check = self._component_check("Sample Plan")
        for box in (self.care_areas_check, self.sample_plan_check):
            nested = QHBoxLayout()
            nested.setContentsMargins(22, 0, 0, 0)
            nested.addWidget(box)
            test_layout.addLayout(nested)
        test_layout.addStretch(1)
        component_row.addLayout(left, 1)
        component_row.addWidget(tests, 1)
        layout.addWidget(components, 1)

        buttons = QGridLayout()
        buttons.setHorizontalSpacing(16)
        buttons.setVerticalSpacing(10)
        select_all = QPushButton("Select All Components")
        select_all.clicked.connect(lambda: self._set_components(True))
        unselect_all = QPushButton("Unselect All Components")
        unselect_all.clicked.connect(lambda: self._set_components(False))
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        import_button = QPushButton("Import")
        import_button.setDefault(True)
        import_button.clicked.connect(self._accept)
        buttons.addWidget(select_all, 0, 0)
        buttons.addWidget(unselect_all, 0, 1)
        buttons.addWidget(cancel, 1, 0)
        buttons.addWidget(import_button, 1, 1)
        layout.addLayout(buttons)

    def _component_check(self, name: str) -> QCheckBox:
        check = QCheckBox(name)
        check.setChecked(True)
        self.component_checks.append(check)
        return check

    def _set_components(self, checked: bool):
        for box in self.component_checks:
            box.setEnabled(True)
            box.setChecked(checked)
        self._sync_test_components()

    def _sync_test_components(self):
        enabled = self.test_data_check.isChecked()
        for box in (self.care_areas_check, self.sample_plan_check):
            box.setEnabled(enabled)

    def _accept(self):
        if not self.recipe_name.text().strip():
            QMessageBox.warning(self, "Puma Recipe Import", "Recipe Name is required.")
            return
        selected = [
            box.text()
            for box in self.component_checks
            if box.isChecked() and box.isEnabled()
        ]
        if not selected:
            QMessageBox.warning(self, "Puma Recipe Import", "Select at least one recipe component.")
            return
        self.result_values = {
            "inspection": self.recipe_name.text().strip(),
            "device": self.device_name.text().strip() or "xyz",
            "step": self.step_name.text().strip() or "RLT",
            "source_tool": self.source_tool,
            "kind": "brightfield",
            "components": {name: {"imported": True} for name in selected},
        }
        self.accept()


class ExtractComponentDialog(QDialog):
    def __init__(self, store: RecipeStore, recipe: dict, parent=None):
        super().__init__(parent)
        self.store = store
        self.recipe = recipe
        self.extracted_filename = ""
        self.component_names = component_names_for_recipe(recipe)
        self.setWindowTitle("Extract Component")
        self.setFixedSize(690, 560)
        self.setStyleSheet(
            _dialog_style()
            + "QTableWidget { background: #ffffff; gridline-color: #b5b5b5; }"
            + "QTableWidget::item { padding: 2px 6px; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 18, 28, 16)

        details = QGridLayout()
        details.setHorizontalSpacing(12)
        details.setVerticalSpacing(2)
        for row, (name, value) in enumerate(
            [
                ("Device:", recipe.get("device", "")),
                ("Layer:", recipe.get("step", "")),
                ("Recipe:", recipe.get("inspection", "")),
            ]
        ):
            details.addWidget(QLabel(name), row, 0)
            details.addWidget(QLabel(value or "-"), row, 1)
        layout.addLayout(details)

        self.table = QTableWidget(len(self.component_names), 3)
        self.table.setHorizontalHeaderLabels(["", "Component Filename", "Status"])
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setShowGrid(True)
        self.checks = []
        for row, component_name in enumerate(self.component_names):
            check = QCheckBox(component_name)
            ready, status = component_status(recipe, component_name)
            check.setChecked(ready)
            check.setEnabled(ready)
            if _test_component_parts(component_name) and not component_name.startswith("Test "):
                check.setStyleSheet("QCheckBox { margin-left: 18px; }")
            self.table.setCellWidget(row, 0, check)
            filename_item = QTableWidgetItem("")
            filename_item.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(row, 1, filename_item)
            status_item = QTableWidgetItem(status)
            status_item.setFlags(Qt.ItemIsEnabled)
            status_item.setBackground(QColor("#e4e4e4"))
            self.table.setItem(row, 2, status_item)
            self.checks.append(check)
        layout.addWidget(self.table, 1)

        file_row = QHBoxLayout()
        file_row.addWidget(QLabel("Component File:"))
        self.filename_combo = QComboBox()
        self.filename_combo.setEditable(True)
        for bundle in store.list_component_bundles():
            self.filename_combo.addItem(bundle.get("filename", ""))
        self.filename_combo.setEditText(recipe.get("inspection", "Recipe"))
        self.filename_edit = self.filename_combo.lineEdit()
        self.filename_edit.setMaxLength(255)
        self.filename_edit.textChanged.connect(self._refresh_component_filenames)
        file_row.addWidget(self.filename_combo, 1)
        layout.addLayout(file_row)
        self._refresh_component_filenames(self.filename_edit.text())

        self.validity_note = QLabel(
            "Part of the recipe is not valid for Run. "
            "Those components are disabled and noted in the Status column."
        )
        self.validity_note.setWordWrap(True)
        self.validity_note.setVisible(any(not box.isEnabled() for box in self.checks))
        layout.addWidget(self.validity_note)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Components:"))
        select_all = QPushButton("Select All")
        select_all.clicked.connect(lambda: self._set_all_checks(True))
        unselect_all = QPushButton("Unselect All")
        unselect_all.clicked.connect(lambda: self._set_all_checks(False))
        controls.addWidget(select_all)
        controls.addWidget(unselect_all)
        controls.addStretch(1)
        layout.addLayout(controls)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        extract = QPushButton("Extract")
        extract.clicked.connect(self._extract)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        buttons.addWidget(extract)
        buttons.addWidget(close)
        buttons.addStretch(1)
        layout.addLayout(buttons)

    def _set_all_checks(self, checked: bool):
        for box in self.checks:
            if box.isEnabled() or not checked:
                box.setChecked(checked)

    def _refresh_component_filenames(self, text: str):
        base_name = text.strip() or self.recipe.get("inspection", "Recipe")
        for row, name in enumerate(self.component_names):
            item = self.table.item(row, 1)
            if item is not None:
                item.setText(component_file_name(name, base_name))

    def _extract(self):
        filename = self.filename_edit.text().strip()
        if not filename:
            QMessageBox.warning(self, "Extract Component", "Component File is required.")
            return
        if len(filename) > 255:
            QMessageBox.warning(
                self,
                "Extract Component",
                "The component file name can contain at most 255 characters.",
            )
            return
        selected = [box.text() for box in self.checks if box.isChecked() and box.isEnabled()]
        if not selected:
            QMessageBox.warning(self, "Extract Component", "Select at least one component.")
            return
        existing = next(
            (item for item in self.store.list_component_bundles() if item.get("filename") == filename),
            None,
        )
        if existing is not None:
            replaced = "\n".join(
                f'{component_display_name(name)}--"{component_file_name(name, filename)}"'
                for name in selected
            )
            answer = QMessageBox.question(
                self,
                "Puma",
                "The following existing components will be replaced. Do you want to continue?\n\n"
                f"{replaced}",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
        source_components = self.recipe.get("components", {})
        components = {}
        for name in selected:
            value = component_value(self.recipe, name)
            components[name] = deepcopy(
                value if value is not None
                else source_components.get(name, {"source": self.recipe.get("inspection", "")})
            )
        self.store.save_component_bundle(filename, self.recipe, components)
        self.extracted_filename = filename
        if filename not in [
            self.filename_combo.itemText(index) for index in range(self.filename_combo.count())
        ]:
            self.filename_combo.addItem(filename)
        for row, box in enumerate(self.checks):
            if box.isChecked() and box.isEnabled():
                status_item = self.table.item(row, 2)
                status_item.setText("Extraction succeeded")
                status_item.setBackground(QColor("#ffffff"))
        if any(name in ("Alignment", "Wafer Layout") for name in selected):
            QMessageBox.information(
                self,
                "Extract Component",
                "Alignment and/or Wafer Layout components were extracted. "
                "After these components are imported, adjust the die corner. "
                "An incompatibility can shift the die grid and related data such as Care Areas.",
            )


class OpenRecipeComponentDialog(QDialog):
    """Browse a saved component file for one recipe component type."""

    def __init__(self, store: RecipeStore, component_name: str, recipe: dict, parent=None):
        super().__init__(parent)
        self.store = store
        self.component_name = component_name
        self.recipe = recipe
        self.selected_bundle = None
        label = component_display_name(component_name)
        self.setWindowTitle(f"Open Recipe Component - {label}")
        self.resize(760, 560)
        self.setStyleSheet(
            "QDialog { background: #d9d9d9; color: #111111; font-family: Arial; font-size: 11px; }"
            "QTreeWidget, QListWidget, QLineEdit { background: white; border: 1px solid #8a8a8a; }"
            "QPushButton { min-width: 78px; min-height: 26px; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)

        latest_row = QHBoxLayout()
        latest_row.addStretch(1)
        self.latest_production = QCheckBox("Show Latest Production")
        self.latest_production.toggled.connect(self._fill_tree)
        latest_row.addWidget(self.latest_production)
        layout.addLayout(latest_row)

        panes = QHBoxLayout()
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setMinimumWidth(240)
        self.tree.currentItemChanged.connect(self._tree_changed)
        panes.addWidget(self.tree, 1)
        self.files = QListWidget()
        self.files.currentRowChanged.connect(self._file_changed)
        panes.addWidget(self.files, 1)
        layout.addLayout(panes, 1)

        form = QGridLayout()
        form.setHorizontalSpacing(8)
        form.setVerticalSpacing(6)
        self.device_id = QLineEdit(str(recipe.get("device", "")))
        self.step_id = QLineEdit(str(recipe.get("step", "")))
        self.recipe_component = QLineEdit("*")
        self.device_id.textChanged.connect(self._update_path)
        self.step_id.textChanged.connect(self._update_path)
        form.addWidget(QLabel("Device ID:"), 0, 0, alignment=Qt.AlignRight)
        form.addWidget(self.device_id, 0, 1)
        form.addWidget(QLabel("Step ID:"), 0, 2, alignment=Qt.AlignRight)
        form.addWidget(self.step_id, 0, 3)
        form.addWidget(QLabel("Recipe Component:"), 1, 0, alignment=Qt.AlignRight)
        form.addWidget(self.recipe_component, 1, 1, 1, 3)
        layout.addLayout(form)

        diameter = (recipe.get("wafer_properties") or {}).get("diameter") or "300 mm"
        self.meta = QLabel(f"Wafer Diameter: {diameter}      Version: Latest")
        layout.addWidget(self.meta)
        self.path_label = QLabel("")
        self.path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.path_label)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        ok = QPushButton("OK")
        ok.clicked.connect(self._accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        self._bundles = []
        self._fill_tree()
        self._update_path()

    def _matching_bundles(self):
        bundles = [
            bundle for bundle in self.store.list_component_bundles()
            if self.component_name in (bundle.get("components") or {})
        ]
        if self.latest_production.isChecked() and bundles:
            bundles = sorted(bundles, key=lambda item: item.get("created", ""))[-1:]
        return bundles

    def _fill_tree(self):
        self.tree.clear()
        self.files.clear()
        self.recipe_component.setText("*")
        self._bundles = self._matching_bundles()
        computer = self.style().standardIcon(QStyle.SP_ComputerIcon)
        folder_icon = self.style().standardIcon(QStyle.SP_DirIcon)
        local = QTreeWidgetItem(["Local"])
        local.setIcon(0, computer)
        local.setExpanded(True)
        grouped = {}
        for bundle in self._bundles:
            device = bundle.get("device") or self.device_id.text() or "Components"
            grouped.setdefault(device, []).append(bundle)
        for device, bundles in grouped.items():
            folder = QTreeWidgetItem([str(device)])
            folder.setIcon(0, folder_icon)
            folder.setData(0, Qt.UserRole, [item.get("filename", "") for item in bundles])
            local.addChild(folder)
        rds = QTreeWidgetItem(["RDS"])
        rds.setIcon(0, computer)
        self.tree.addTopLevelItem(local)
        self.tree.addTopLevelItem(rds)
        if local.childCount():
            self.tree.setCurrentItem(local.child(0))

    def _tree_changed(self, current, _previous):
        self.files.clear()
        self.recipe_component.setText("*")
        if current is None:
            return
        filenames = current.data(0, Qt.UserRole) or []
        for filename in filenames:
            self.files.addItem(str(filename))
        self._update_path()

    def _file_changed(self, row: int):
        if row < 0:
            return
        filename = self.files.item(row).text()
        self.recipe_component.setText(filename)
        self._update_path()

    def _component_folder(self) -> Path:
        folder = (
            Path(self.store.path).parent
            / "RecipeComponents"
            / safe_component_part(component_display_name(self.component_name))
            / safe_component_part(self.device_id.text() or "Device")
        )
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def _update_path(self):
        if not hasattr(self, "path_label"):
            return
        self.path_label.setText(f"Path: {self._component_folder()}")

    def _accept(self):
        filename = self.recipe_component.text().strip()
        bundle = next((item for item in self._bundles if item.get("filename") == filename), None)
        if bundle is None:
            QMessageBox.warning(self, self.windowTitle(), "Select a component file.")
            return
        target = self._component_folder() / f"{safe_component_part(filename)}.json"
        if not target.exists():
            target.write_text(
                f"{self.component_name}\n{filename}\n",
                encoding="utf-8",
            )
        self.selected_bundle = bundle
        self.accept()


def safe_component_part(value: str) -> str:
    cleaned = "".join("_" if character in '<>:"/\\|?*' else character for character in str(value or "").strip())
    return cleaned.strip(" .") or "Component"


class _ComponentFilenameField(QWidget):
    def __init__(self, combo: QComboBox, browse, select_row):
        super().__init__()
        self.combo = combo
        self.browse = browse
        self.select_row = select_row
        layout = QHBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(2)
        self.display = QLineEdit()
        self.display.setReadOnly(True)
        self.display.setStyleSheet("QLineEdit { background: white; border: none; }")
        self.display.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.arrow = QPushButton()
        self.arrow.setFixedSize(18, 18)
        self.arrow.setIcon(self.style().standardIcon(QStyle.SP_ArrowDown))
        self.arrow.setToolTip("Open Recipe Component")
        self.arrow.setVisible(False)
        self.arrow.clicked.connect(browse)
        layout.addWidget(self.display, 1)
        layout.addWidget(self.arrow, 0, Qt.AlignTop)
        combo.currentIndexChanged.connect(self.sync_display)
        self.sync_display()

    def sync_display(self):
        bundle = self.combo.currentData()
        if not bundle:
            self.display.clear()
            return
        device = bundle.get("device") or ""
        step = bundle.get("step") or ""
        if device or step:
            self.display.setText(f"[L] {device}\\{step}")
        else:
            self.display.setText(f"[L] {bundle.get('filename', '')}")

    def set_arrow_visible(self, visible: bool):
        self.arrow.setVisible(bool(visible))

    def mousePressEvent(self, event):
        self.select_row()
        super().mousePressEvent(event)


class InsertComponentDialog(QDialog):
    def __init__(self, store: RecipeStore, recipe: dict, parent=None):
        super().__init__(parent)
        self.store = store
        self.recipe = recipe
        self.result_recipe = None
        self._listed_tests: list[int] = []
        self.filename_fields = []
        self.setWindowTitle("Insert Component")
        self.setFixedSize(720, 610)
        self.setStyleSheet(
            _dialog_style().replace("#d8ead4", "#efe6d2")
            + "QTableWidget { background: #efe6d2; gridline-color: #b7b7b7; }"
            + "QHeaderView::section { background: #efe6d2; font-weight: 700; border: 1px solid #b7b7b7; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 18, 24, 18)

        details = QGridLayout()
        for row, (name, value) in enumerate(
            [
                ("Device:", recipe.get("device", "")),
                ("Layer:", recipe.get("step", "")),
                ("Recipe:", recipe.get("inspection", "")),
            ]
        ):
            details.addWidget(QLabel(name), row, 0)
            details.addWidget(QLabel(value), row, 1)
        layout.addLayout(details)

        add_frame = QFrame()
        add_frame.setFrameShape(QFrame.Box)
        add_row = QHBoxLayout(add_frame)
        add_row.setContentsMargins(6, 6, 6, 6)
        add_test = QPushButton("Add Test")
        add_test.clicked.connect(self._add_test)
        self.test_count = QSpinBox()
        self.test_count.setRange(1, 99)
        self.test_count.setValue(1)
        add_row.addWidget(add_test)
        add_row.addWidget(self.test_count)
        add_row.addStretch(1)
        add_wrap = QHBoxLayout()
        add_wrap.addWidget(add_frame)
        add_wrap.addStretch(1)
        layout.addLayout(add_wrap)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["", "Component Filename", "Status"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.currentCellChanged.connect(
            lambda row, _column, _previous, _previous_column: self._show_filename_arrow(row)
        )
        self.component_combos = []
        self._populate_component_rows()
        layout.addWidget(self.table, 1)

        layout.addWidget(QLabel("Inspection Status:"))
        self.status = QLabel("")
        self.status.setFrameShape(QFrame.Panel)
        self.status.setWordWrap(True)
        self.status.setMinimumHeight(78)
        self.status.setStyleSheet("QLabel { background: white; border: 1px solid #8a8a8a; }")
        layout.addWidget(self.status)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        insert = QPushButton("Insert")
        insert.clicked.connect(self._insert)
        close = QPushButton("Close")
        close.clicked.connect(self._close)
        buttons.addWidget(insert)
        buttons.addWidget(close)
        buttons.addStretch(1)
        layout.addLayout(buttons)

    def _add_test(self):
        number = self.test_count.value()
        if number not in self._listed_tests:
            self._listed_tests.append(number)
        self.test_count.setValue(min(99, number + 1))
        self._populate_component_rows()

    def _close(self):
        if self.result_recipe is not None:
            self.accept()
        else:
            self.reject()

    def _component_names(self) -> list[str]:
        names = list(BASE_COMPONENT_NAMES)
        for number in self._listed_tests:
            names.extend(
                [
                    f"Test {number}",
                    f"{number}-Care Area",
                    f"{number}-Sensitivity",
                    f"{number}-Sample Plan",
                ]
            )
        return names

    def _populate_component_rows(self):
        selected = {}
        for row, combo in enumerate(getattr(self, "component_combos", [])):
            item = self.table.item(row, 0)
            bundle = combo.currentData()
            if item is not None and bundle:
                selected[item.text()] = bundle.get("filename", "")
        names = self._component_names()
        bundles = self.store.list_component_bundles()
        self.table.setRowCount(len(names))
        self.component_combos = []
        self.filename_fields = []
        for row, name in enumerate(names):
            name_item = QTableWidgetItem(name)
            name_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(row, 0, name_item)
            combo = QComboBox(self)
            combo.hide()
            combo.addItem("", None)
            for bundle in bundles:
                if name in bundle.get("components", {}):
                    combo.addItem(bundle.get("filename", ""), bundle)
            if selected.get(name):
                combo.setCurrentText(selected[name])
            field = _ComponentFilenameField(
                combo,
                lambda _checked=False, active_row=row: self._browse_component(active_row),
                lambda active_row=row: self._select_filename_row(active_row),
            )
            self.table.setCellWidget(row, 1, field)
            status_item = QTableWidgetItem("")
            status_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            status_item.setBackground(QColor("#d0d0d0"))
            self.table.setItem(row, 2, status_item)
            self.component_combos.append(combo)
            self.filename_fields.append(field)
        self.table.clearSelection()
        self._show_filename_arrow(-1)

    def _select_filename_row(self, row: int):
        self._show_filename_arrow(row)

    def _show_filename_arrow(self, row: int):
        for index, field in enumerate(self.filename_fields):
            field.set_arrow_visible(index == row)

    def _browse_component(self, row: int):
        name_item = self.table.item(row, 0)
        if name_item is None:
            return
        dialog = OpenRecipeComponentDialog(self.store, name_item.text(), self.recipe, self)
        if dialog.exec() != QDialog.Accepted or dialog.selected_bundle is None:
            return
        filename = dialog.selected_bundle.get("filename", "")
        combo = self.component_combos[row]
        index = combo.findText(filename)
        if index < 0:
            combo.addItem(filename, dialog.selected_bundle)
            index = combo.findText(filename)
        combo.setCurrentIndex(index)
        self.filename_fields[row].sync_display()

    def _update_instruction_status(self):
        self.status.setText("")

    def _update_component_status(self, row: int):
        if row < len(self.filename_fields):
            self.filename_fields[row].sync_display()

    def _insert(self):
        updated = deepcopy(self.recipe)
        components = deepcopy(updated.get("components", {}))
        tests = list(updated.get("tests", []))
        highest_test = max(self._listed_tests, default=0)
        while len(tests) < highest_test:
            tests.append({"name": f"Test {len(tests) + 1}", "status": "Incomplete"})
        selected_count = 0
        geometry_changed = False
        for row, combo in enumerate(self.component_combos):
            bundle = combo.currentData()
            if not bundle:
                continue
            component_name = self.table.item(row, 0).text()
            value = bundle.get("components", {}).get(component_name)
            if value is None:
                self.table.item(row, 2).setText("Component is not compatible")
                continue
            value = deepcopy(value)
            components[component_name] = value
            direct_keys = {
                "Wafer Layout": "wafer_map",
                "Alignment": "alignment",
                "Data Analysis": "wafer_post_processing",
                "Lot Plan": "lot_plan",
            }
            if component_name in direct_keys:
                updated[direct_keys[component_name]] = value
            else:
                parts = _test_component_parts(component_name)
                if parts is None:
                    self.table.item(row, 2).setText("Component is not compatible")
                    continue
                index, key = parts
                while len(tests) <= index:
                    tests.append({"name": f"Test {len(tests) + 1}", "status": "Incomplete"})
                if key == "test":
                    tests[index] = value
                else:
                    tests[index][key] = value
            status_item = self.table.item(row, 2)
            status_item.setText("Insertion succeeded")
            status_item.setBackground(QColor("#d0d0d0"))
            selected_count += 1
            geometry_changed = geometry_changed or component_name in {"Wafer Layout", "Alignment"}
        if selected_count == 0:
            if any(combo.currentData() for combo in self.component_combos):
                self.status.setText("The selected components are not valid for insertion.")
            else:
                QMessageBox.warning(self, "Insert Component", "Select at least one component file.")
            return
        updated["components"] = components
        updated["tests"] = tests
        if geometry_changed:
            wafer_map = dict(updated.get("wafer_map", {}))
            wafer_map["die_corner_adjustment_required"] = True
            updated["wafer_map"] = wafer_map
        updated["dirty"] = True
        updated["status"] = "Incomplete"
        updated["state"] = (
            "Inserted Alignment/Wafer Layout components. The die grid and Care Areas can shift. "
            "Adjust Die Corner before running. Review Load/Save Status and save the recipe."
            if geometry_changed
            else "Recipe components inserted. Review Load/Save Status and save the recipe."
        )
        self.result_recipe = updated
        self.status.setText(updated["state"])


class RecipeHistoryDialog(QDialog):
    def __init__(self, store: RecipeStore, inspection: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Recipe History Log")
        self.resize(760, 460)
        self.setStyleSheet(_dialog_style().replace("#d8ead4", "#efede2"))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Date / Time", "Event", "Inspection", "Device", "Layer", "Detail"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        for entry in reversed(store.history(inspection)):
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = [
                entry.get("timestamp", ""),
                entry.get("event", ""),
                entry.get("inspection", ""),
                entry.get("device", ""),
                entry.get("step", ""),
                entry.get("detail", ""),
            ]
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))
        layout.addWidget(self.table, 1)
        buttons = QHBoxLayout()
        print_button = QPushButton("Print")
        print_button.setFixedWidth(96)
        print_button.clicked.connect(self._print_history)
        buttons.addWidget(print_button)
        buttons.addStretch(1)
        close = QPushButton("Close")
        close.setFixedWidth(96)
        close.clicked.connect(self.accept)
        buttons.addWidget(close)
        layout.addLayout(buttons)

    def _print_history(self):
        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() != QDialog.Accepted:
            return
        snapshot = self.table.grab()
        painter = QPainter(printer)
        target = painter.viewport()
        scaled = snapshot.scaled(target.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        painter.drawPixmap(target.x(), target.y(), scaled)
        painter.end()

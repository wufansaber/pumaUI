from __future__ import annotations

from copy import deepcopy
from typing import Optional

from ...qt_compat import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMenu,
    QMessageBox,
    QPainter,
    QPrintDialog,
    QPrinter,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    Qt,
    QVBoxLayout,
    QWidget,
)
from ...recipe_store import RecipeStore
from ...widgets import ClassicButton


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
        ready = bool(recipe.get("wpp_valid"))
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
    return ready, "Ready for extraction" if ready else "Not valid for Run"


def _dialog_style() -> str:
    return """
        QDialog { background: #d8ead4; color: #111111; font-family: Arial; font-size: 10px; }
        QLineEdit, QComboBox, QSpinBox, QTableWidget {
            background: #ffffff; border: 1px solid #77736b; min-height: 24px;
        }
        QPushButton {
            background: #e7e5dc; border-top: 1px solid #ffffff; border-left: 1px solid #ffffff;
            border-right: 1px solid #77736b; border-bottom: 1px solid #77736b;
            min-height: 24px; padding: 2px 12px;
        }
        QHeaderView::section { background: #e6e4d9; border: 1px solid #8c8982; padding: 3px; }
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


class RecipeImportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.result_values = None
        self.setWindowTitle("Puma Recipe Import")
        self.setFixedSize(520, 430)
        self.setStyleSheet(_dialog_style().replace("#d8ead4", "#efede2"))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 18)

        form = QGridLayout()
        self.source_tool = QComboBox()
        self.source_tool.addItems(["Puma 9980", "Brightfield Tool"])
        self.recipe_name = QLineEdit("Imported_Recipe")
        self.device_name = QLineEdit("Device1")
        self.step_name = QLineEdit("Layer1")
        for row, (label, widget) in enumerate(
            [
                ("Source Tool:", self.source_tool),
                ("Recipe Name:", self.recipe_name),
                ("Device:", self.device_name),
                ("Layer:", self.step_name),
            ]
        ):
            form.addWidget(QLabel(label), row, 0, alignment=Qt.AlignRight)
            form.addWidget(widget, row, 1)
        layout.addLayout(form)

        layout.addWidget(QLabel("Recipe Components"))
        self.component_checks = []
        grid = QGridLayout()
        for index, name in enumerate(COMPONENT_NAMES):
            check = QCheckBox(name)
            check.setChecked(True)
            grid.addWidget(check, index // 2, index % 2)
            self.component_checks.append(check)
        layout.addLayout(grid)
        layout.addStretch(1)

        buttons = QHBoxLayout()
        select_all = QPushButton("Select All Components")
        select_all.clicked.connect(lambda: [box.setChecked(True) for box in self.component_checks])
        buttons.addWidget(select_all)
        buttons.addStretch(1)
        import_button = QPushButton("Import")
        import_button.clicked.connect(self._accept)
        buttons.addWidget(import_button)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)

    def _accept(self):
        if not self.recipe_name.text().strip():
            QMessageBox.warning(self, "Puma Recipe Import", "Recipe Name is required.")
            return
        selected = [box.text() for box in self.component_checks if box.isChecked()]
        self.result_values = {
            "inspection": self.recipe_name.text().strip(),
            "device": self.device_name.text().strip() or "Device1",
            "step": self.step_name.text().strip() or "Layer1",
            "source_tool": self.source_tool.currentText(),
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
        self.setStyleSheet(_dialog_style())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 20, 28, 20)

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

        self.table = QTableWidget(len(self.component_names), 3)
        self.table.setHorizontalHeaderLabels(["", "Component Filename", "Status"])
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.checks = []
        for row, component_name in enumerate(self.component_names):
            check = QCheckBox(component_name)
            ready, status = component_status(recipe, component_name)
            check.setChecked(ready)
            check.setEnabled(ready)
            self.table.setCellWidget(row, 0, check)
            self.table.setItem(row, 1, QTableWidgetItem(recipe.get("inspection", "Recipe")))
            self.table.setItem(row, 2, QTableWidgetItem(status))
            self.checks.append(check)
        layout.addWidget(self.table, 1)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Component File:"))
        self.filename_edit = QLineEdit(recipe.get("inspection", "Recipe"))
        self.filename_edit.setMaxLength(255)
        controls.addWidget(self.filename_edit, 1)
        select_all = QPushButton("Select All")
        select_all.clicked.connect(lambda: self._set_all_checks(True))
        unselect_all = QPushButton("Unselect All")
        unselect_all.clicked.connect(lambda: self._set_all_checks(False))
        controls.addWidget(select_all)
        controls.addWidget(unselect_all)
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

    def _extract(self):
        filename = self.filename_edit.text().strip()
        if not filename:
            QMessageBox.warning(self, "Extract Component", "Component File is required.")
            return
        selected = [box.text() for box in self.checks if box.isChecked()]
        if not selected:
            QMessageBox.warning(self, "Extract Component", "Select at least one component.")
            return
        existing = {item.get("filename") for item in self.store.list_component_bundles()}
        if filename in existing:
            replaced = "\n".join(f"- {name}: {filename}" for name in selected)
            answer = QMessageBox.question(
                self,
                "Overwrite Warning",
                f'The following components in "{filename}" will be replaced:\n\n'
                f"{replaced}\n\nContinue?",
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
        for row, box in enumerate(self.checks):
            if box.isChecked():
                self.table.item(row, 2).setText("Extraction succeeded")


class InsertComponentDialog(QDialog):
    def __init__(self, store: RecipeStore, recipe: dict, parent=None):
        super().__init__(parent)
        self.store = store
        self.recipe = recipe
        self.result_recipe = None
        self.setWindowTitle("Insert Component")
        self.setFixedSize(720, 610)
        self.setStyleSheet(_dialog_style().replace("#d8ead4", "#efede2"))
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

        add_row = QHBoxLayout()
        add_test = QPushButton("Add Test")
        add_test.clicked.connect(self._add_test)
        self.test_count = QSpinBox()
        self.test_count.setRange(1, 99)
        self.test_count.setValue(max(1, len(recipe.get("tests", []))))
        add_row.addWidget(add_test)
        add_row.addWidget(self.test_count)
        add_row.addStretch(1)
        layout.addLayout(add_row)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Component", "Component Filename", "Status"])
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.component_combos = []
        self._populate_component_rows()
        layout.addWidget(self.table, 1)

        layout.addWidget(QLabel("Inspection Status:"))
        self.status = QLabel("Select one or more compatible components, then click Insert.")
        self.status.setFrameShape(QFrame.Panel)
        self.status.setWordWrap(True)
        self.status.setMinimumHeight(60)
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
        self.test_count.setValue(self.test_count.value() + 1)
        self._populate_component_rows()

    def _close(self):
        if self.result_recipe is not None:
            self.accept()
        else:
            self.reject()

    def _populate_component_rows(self):
        selected = {}
        for row, combo in enumerate(getattr(self, "component_combos", [])):
            item = self.table.item(row, 0)
            bundle = combo.currentData()
            if item is not None and bundle:
                selected[item.text()] = bundle.get("filename", "")
        names = component_names_for_recipe(
            self.recipe,
            test_count=self.test_count.value(),
        )
        bundles = self.store.list_component_bundles()
        self.table.setRowCount(len(names))
        self.component_combos = []
        for row, name in enumerate(names):
            self.table.setItem(row, 0, QTableWidgetItem(name))
            combo = QComboBox()
            combo.addItem("", None)
            for bundle in bundles:
                if name in bundle.get("components", {}):
                    combo.addItem(bundle.get("filename", ""), bundle)
            if selected.get(name):
                combo.setCurrentText(selected[name])
            self.table.setCellWidget(row, 1, combo)
            self.table.setItem(row, 2, QTableWidgetItem("Select a component file"))
            self.component_combos.append(combo)

    def _insert(self):
        updated = deepcopy(self.recipe)
        components = deepcopy(updated.get("components", {}))
        tests = list(updated.get("tests", []))
        while len(tests) < self.test_count.value():
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
            self.table.item(row, 2).setText("Insertion succeeded")
            selected_count += 1
            geometry_changed = geometry_changed or component_name in {"Wafer Layout", "Alignment"}
        if selected_count == 0:
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
            "Inserted Alignment/Wafer Layout components. Adjust Die Corner before running."
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

from __future__ import annotations

from copy import deepcopy

from ...qt_compat import (
    QAbstractItemView,
    QCheckBox,
    QColor,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    Qt,
)
from .models import (
    OPTIONAL_AUTOLEARN_STEPS,
    active_registration_sites,
    compare_recipes,
    complete_autolearn,
    distribute_rds_recipe,
    generate_autolearn_recipes,
    make_registration_site,
    normalized_xp_state,
    rds_check_in,
    set_recipe_parameter,
)


class RegistrationSiteLibraryDialog(QDialog):
    def __init__(self, recipe: dict, parent=None):
        super().__init__(parent)
        self.recipe = deepcopy(recipe)
        self.result_recipe = None
        self.setWindowTitle("Registration Site")
        self.resize(760, 500)
        root = QVBoxLayout(self)
        root.addWidget(QLabel("Registration sites provide common geometry for derivative layers."))
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Active", "Site Name", "Layer", "X (um)", "Y (um)", "Low / High Pixel Size"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        root.addWidget(self.table, 1)
        form = QHBoxLayout()
        self.name = QLineEdit(); self.name.setPlaceholderText("Site name")
        self.layer = QLineEdit(); self.layer.setPlaceholderText("Layer")
        self.x = QDoubleSpinBox(); self.x.setRange(-500000, 500000); self.x.setSuffix(" um")
        self.y = QDoubleSpinBox(); self.y.setRange(-500000, 500000); self.y.setSuffix(" um")
        for widget in (self.name, self.layer, self.x, self.y): form.addWidget(widget)
        root.addLayout(form)
        buttons = QHBoxLayout()
        add = QPushButton("Add Site"); add.clicked.connect(self._add)
        delete = QPushButton("Delete"); delete.clicked.connect(self._delete)
        buttons.addWidget(add); buttons.addWidget(delete); buttons.addStretch(1)
        finish = QPushButton("Finish"); finish.clicked.connect(self._finish)
        cancel = QPushButton("Cancel"); cancel.clicked.connect(self.reject)
        buttons.addWidget(finish); buttons.addWidget(cancel); root.addLayout(buttons)
        self.sites = active_registration_sites(self.recipe)
        self._refresh()

    def _refresh(self):
        self.table.setRowCount(len(self.sites))
        for row, site in enumerate(self.sites):
            values = ["Yes" if site.get("active", True) else "No", site.get("name", ""), site.get("layer", ""), site.get("x_um", 0), site.get("y_um", 0), f"{site.get('low_mag_optics', {}).get('pixel_size', 2.0)} / {site.get('high_mag_optics', {}).get('pixel_size', 0.1)}"]
            for column, value in enumerate(values): self.table.setItem(row, column, QTableWidgetItem(str(value)))

    def _add(self):
        try:
            self.sites.append(make_registration_site(self.name.text(), self.x.value(), self.y.value(), self.layer.text()))
        except ValueError as exc:
            QMessageBox.warning(self, "Registration Site", str(exc)); return
        self.name.clear(); self._refresh()

    def _delete(self):
        rows = sorted({index.row() for index in self.table.selectedIndexes()}, reverse=True)
        for row in rows: self.sites.pop(row)
        self._refresh()

    def _finish(self):
        updated = deepcopy(self.recipe)
        xp = updated.setdefault("xp_offline", {})
        xp["registration_sites"] = deepcopy(self.sites)
        updated["dirty"] = True
        self.result_recipe = updated
        self.accept()


class XPRecipeGeneratorDialog(QDialog):
    def __init__(self, recipe_store, current_recipe=None, parent=None):
        super().__init__(parent)
        self.store = recipe_store
        self.recipes = recipe_store.list_recipes()
        if current_recipe and not any(item.get("id") == current_recipe.get("id") for item in self.recipes):
            self.recipes.append(deepcopy(current_recipe))
        self.generated_recipes = []
        self.layers = []
        self.setWindowTitle("XP Recipe Generation")
        self.resize(1120, 680)
        root = QVBoxLayout(self)
        selection = QGridLayout()
        self.base = QComboBox(); self.source = QComboBox()
        self.base.addItem("Select Base Recipe", "")
        self.source.addItem("No Source Device", "")
        for recipe in self.recipes:
            label = f"{recipe.get('device', '')} / {recipe.get('step', '')} / {recipe.get('inspection', '')}"
            self.base.addItem(label, recipe.get("id")); self.source.addItem(label, recipe.get("id"))
        if current_recipe:
            index = self.base.findData(current_recipe.get("id"))
            if index >= 0: self.base.setCurrentIndex(index)
        self.mode = QComboBox(); self.mode.addItems(["Production", "Hot Scan", "OSTS"])
        self.destination = QComboBox(); self.destination.addItems(["Local", "RDS"])
        self.pattern = QLineEdit("{Device}_{Layer}")
        selection.addWidget(QLabel("Base Recipe"), 0, 0); selection.addWidget(self.base, 0, 1)
        selection.addWidget(QLabel("Source Recipe"), 0, 2); selection.addWidget(self.source, 0, 3)
        selection.addWidget(QLabel("Mode"), 1, 0); selection.addWidget(self.mode, 1, 1)
        selection.addWidget(QLabel("Destination"), 1, 2); selection.addWidget(self.destination, 1, 3)
        selection.addWidget(QLabel("Recipe Name Pattern"), 2, 0); selection.addWidget(self.pattern, 2, 1, 1, 3)
        root.addLayout(selection)
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(["Layer", "Recipe Name", "Laser Sensitive", "Laser Factor", "Sensitivity", "Data Analysis", "Fourier", "Light"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        root.addWidget(self.table, 1)
        add_row = QHBoxLayout(); self.layer_name = QLineEdit(); self.layer_name.setPlaceholderText("Layer name")
        add = QPushButton("Add Layer"); add.clicked.connect(self._add_layer)
        delete = QPushButton("Delete Selected"); delete.clicked.connect(self._delete_layers)
        delete_all = QPushButton("Delete All"); delete_all.clicked.connect(self._delete_all)
        autofill = QPushButton("Auto Fill"); autofill.clicked.connect(self._autofill)
        add_row.addWidget(self.layer_name, 1); add_row.addWidget(add); add_row.addWidget(delete); add_row.addWidget(delete_all); add_row.addWidget(autofill)
        root.addLayout(add_row)
        self.status = QLabel("Add derivative layers, then click Generate."); root.addWidget(self.status)
        footer = QHBoxLayout(); footer.addStretch(1)
        generate = QPushButton("Generate"); generate.clicked.connect(self._generate)
        close = QPushButton("Close"); close.clicked.connect(self.reject)
        footer.addWidget(generate); footer.addWidget(close); root.addLayout(footer)

    def _base_recipe(self):
        recipe_id = self.base.currentData()
        return next((item for item in self.recipes if item.get("id") == recipe_id), None)

    def _source_recipes(self):
        selected = next((item for item in self.recipes if item.get("id") == self.source.currentData()), None)
        if not selected: return []
        return [item for item in self.recipes if item.get("device") == selected.get("device")]

    def _add_layer(self):
        name = self.layer_name.text().strip()
        if not name: return
        self.layers.append({"layer": name, "laser_sensitivity": False, "laser_power_factor": 1.0, "sensitivity_source": "Use Base Recipe", "data_analysis_source": "Use Base Recipe", OPTIONAL_AUTOLEARN_STEPS[0]: False, OPTIONAL_AUTOLEARN_STEPS[1]: False})
        self.layer_name.clear(); self._refresh()

    def _delete_layers(self):
        for row in sorted({index.row() for index in self.table.selectedIndexes()}, reverse=True): self.layers.pop(row)
        self._refresh()

    def _delete_all(self): self.layers.clear(); self._refresh()

    def _autofill(self):
        sources = self._source_recipes()
        if not sources:
            QMessageBox.warning(self, "Recipe Generation", "Select a Source Recipe before Auto Fill."); return
        from .models import autofill_layer
        self.layers = [autofill_layer(layer, sources) for layer in self.layers]
        self._refresh()

    def _refresh(self):
        base = self._base_recipe() or {}
        self.table.setRowCount(len(self.layers))
        for row, layer in enumerate(self.layers):
            values = [layer.get("layer", ""), self.pattern.text().replace("{Device}", str(base.get("device", "Device"))).replace("{Layer}", str(layer.get("layer", ""))).replace("{BaseRecipe}", str(base.get("inspection", "Base"))), "Yes" if layer.get("laser_sensitivity") else "No", layer.get("laser_power_factor", 1.0), layer.get("sensitivity_source", "Use Base Recipe"), layer.get("data_analysis_source", "Use Base Recipe"), "Yes" if layer.get(OPTIONAL_AUTOLEARN_STEPS[0]) else "No", "Yes" if layer.get(OPTIONAL_AUTOLEARN_STEPS[1]) else "No"]
            for column, value in enumerate(values): self.table.setItem(row, column, QTableWidgetItem(str(value)))

    def _generate(self):
        base = self._base_recipe()
        if not base:
            QMessageBox.warning(self, "Recipe Generation", "Select a Base Recipe."); return
        try:
            generated = generate_autolearn_recipes(base, self.layers, naming_pattern=self.pattern.text(), mode=self.mode.currentText(), destination=self.destination.currentText())
        except ValueError as exc:
            QMessageBox.warning(self, "Recipe Generation", str(exc)); return
        self.generated_recipes = [self.store.save_recipe(recipe, event="Generate AutoLearn-Ready Recipe", detail=f"{self.mode.currentText()} mode") for recipe in generated]
        self.status.setText(f"Generated {len(self.generated_recipes)} AutoLearn-Ready recipe(s). Status: Valid for Run")
        self.accept()


class ManualAssistDialog(QDialog):
    def __init__(self, xp_state=None, recipe=None, parent=None):
        super().__init__(parent)
        self.state = normalized_xp_state(xp_state); self.recipe = deepcopy(recipe or {}); self.result_state = None; self.result_recipe = None
        self.setWindowTitle("Manual Assist for AutoDerivative"); self.resize(650, 430)
        root = QVBoxLayout(self); grid = QGridLayout()
        assist = self.state["manual_assist"]
        self.fix = QCheckBox("Enable Fixing AutoLearn Errors"); self.fix.setChecked(assist["fix_errors"])
        self.verify = QCheckBox("Verify Inspection Results"); self.verify.setChecked(assist["verify_results"])
        self.signal = QCheckBox("Signal Tower Required Operation Attention"); self.signal.setChecked(assist["signal_tower_enabled"])
        self.fix_timeout = QSpinBox(); self.fix_timeout.setRange(0, 1440); self.fix_timeout.setValue(assist["fix_timeout_minutes"]); self.fix_timeout.setSuffix(" min")
        self.verify_timeout = QSpinBox(); self.verify_timeout.setRange(0, 1440); self.verify_timeout.setValue(assist["verify_timeout_minutes"]); self.verify_timeout.setSuffix(" min")
        grid.addWidget(self.fix, 0, 0, 1, 2); grid.addWidget(QLabel("Fix timeout (0 = infinite)"), 1, 0); grid.addWidget(self.fix_timeout, 1, 1)
        grid.addWidget(self.verify, 2, 0, 1, 2); grid.addWidget(QLabel("Verify timeout (0 = infinite)"), 3, 0); grid.addWidget(self.verify_timeout, 3, 1)
        grid.addWidget(self.signal, 4, 0, 1, 2); root.addLayout(grid)
        self.outcome = QComboBox(); self.outcome.addItems(["Configure Only", "Simulate AutoLearn Success", "Simulate AutoLearn Failure"])
        root.addWidget(QLabel("AutoLearn Outcome")); root.addWidget(self.outcome); root.addStretch(1)
        footer = QHBoxLayout(); footer.addStretch(1); apply = QPushButton("Apply"); apply.clicked.connect(self._finish); cancel = QPushButton("Cancel"); cancel.clicked.connect(self.reject); footer.addWidget(apply); footer.addWidget(cancel); root.addLayout(footer)

    def _finish(self):
        assist = self.state["manual_assist"]
        assist.update({"fix_errors": self.fix.isChecked(), "verify_results": self.verify.isChecked(), "signal_tower_enabled": self.signal.isChecked(), "fix_timeout_minutes": self.fix_timeout.value(), "verify_timeout_minutes": self.verify_timeout.value()})
        self.result_state = normalized_xp_state(self.state)
        if self.recipe and self.outcome.currentIndex() > 0:
            self.result_recipe = complete_autolearn(self.recipe, successful=self.outcome.currentIndex() == 1, manual_assist=assist)
        self.accept()


class RDSManagerDialog(QDialog):
    def __init__(self, recipe_store, current_recipe=None, xp_state=None, parent=None):
        super().__init__(parent)
        self.store = recipe_store; self.current_recipe = deepcopy(current_recipe or {}); self.state = normalized_xp_state(xp_state); self.result_state = None
        self.setWindowTitle("XP Recipe Distribution System"); self.resize(920, 560)
        root = QVBoxLayout(self)
        root.addWidget(QLabel("Central version, approval, and distribution records are simulated locally."))
        self.table = QTableWidget(0, 7); self.table.setHorizontalHeaderLabels(["Recipe", "Device", "Layer", "Version", "Production", "Changed By", "Timestamp"]); self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); self.table.setSelectionBehavior(QAbstractItemView.SelectRows); root.addWidget(self.table, 1)
        form = QHBoxLayout(); self.user = QLineEdit("kttool"); self.production = QCheckBox("Production Approved"); self.destinations = QLineEdit("Puma-01, Puma-02"); self.destinations.setPlaceholderText("Destination tools, comma separated"); form.addWidget(QLabel("User")); form.addWidget(self.user); form.addWidget(self.production); form.addWidget(self.destinations, 1); root.addLayout(form)
        buttons = QHBoxLayout(); checkin = QPushButton("Check In Current Recipe"); checkin.clicked.connect(self._check_in); distribute = QPushButton("Distribute Selected"); distribute.clicked.connect(self._distribute); buttons.addWidget(checkin); buttons.addWidget(distribute); buttons.addStretch(1); close = QPushButton("Close"); close.clicked.connect(self._finish); buttons.addWidget(close); root.addLayout(buttons); self._refresh()

    def _refresh(self):
        versions = self.state["rds_versions"]; self.table.setRowCount(len(versions))
        for row, item in enumerate(versions):
            values = [item.get("inspection", ""), item.get("device", ""), item.get("layer", ""), item.get("version", 0), "Yes" if item.get("production_approved") else "No", item.get("changed_by", ""), item.get("timestamp", "")]
            for column, value in enumerate(values): self.table.setItem(row, column, QTableWidgetItem(str(value)))

    def _check_in(self):
        if not self.current_recipe:
            QMessageBox.warning(self, "RDS", "No current recipe is loaded."); return
        self.state, _entry = rds_check_in(self.state, self.current_recipe, user=self.user.text(), production_approved=self.production.isChecked()); self._refresh()

    def _distribute(self):
        row = self.table.currentRow()
        if row < 0: return
        destinations = [item.strip() for item in self.destinations.text().split(",") if item.strip()]
        try: self.state = distribute_rds_recipe(self.state, self.state["rds_versions"][row]["id"], destinations)
        except ValueError as exc: QMessageBox.warning(self, "RDS", str(exc))

    def _finish(self): self.result_state = normalized_xp_state(self.state); self.accept()


class RecipeComparatorDialog(QDialog):
    CATEGORIES = ("inspection", "device", "step", "recipe_type", "status", "approval", "wafer_properties", "wafer_map", "alignment", "tests", "wafer_post_processing", "lot_plan", "xp_offline")

    def __init__(self, recipes, rds_versions=None, parent=None):
        super().__init__(parent)
        self.all_recipes = [deepcopy(item) for item in recipes]
        self.all_recipes.extend(deepcopy(item.get("recipe", {})) for item in (rds_versions or []) if item.get("recipe"))
        self.loaded_recipes = []; self.visible_categories = set(self.CATEGORIES); self.result_recipes = []
        self.setWindowTitle("XP Recipe Comparator"); self.resize(1280, 720)
        root = QVBoxLayout(self); top = QHBoxLayout()
        self.scope = QComboBox(); self.scope.addItems(["All", "Local", "RDS"]); self.scope.currentTextChanged.connect(self._refresh_available)
        self.filter = QLineEdit(); self.filter.setPlaceholderText("Quick Filter: Device, Layer, or Recipe"); self.filter.textChanged.connect(self._refresh_available)
        self.production_only = QCheckBox("Show production approved versions"); self.production_only.toggled.connect(self._refresh_available)
        top.addWidget(QLabel("Found Recipes")); top.addWidget(self.scope); top.addWidget(self.filter, 1); top.addWidget(self.production_only); root.addLayout(top)
        self.tabs = QTabWidget(); root.addWidget(self.tabs, 1)
        load_page = QWidget(); load_layout = QVBoxLayout(load_page); self.available = QTableWidget(0, 6); self.available.setHorizontalHeaderLabels(["Load", "Recipe", "Modified", "Device", "Layer", "Status"]); self.available.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); self.available.setSelectionBehavior(QAbstractItemView.SelectRows); load_layout.addWidget(self.available, 1)
        load_buttons = QHBoxLayout(); check = QPushButton("Check All"); check.clicked.connect(lambda: self.available.selectAll()); uncheck = QPushButton("Uncheck All"); uncheck.clicked.connect(self.available.clearSelection); load = QPushButton("Load Recipes"); load.clicked.connect(self._load); load_buttons.addWidget(check); load_buttons.addWidget(uncheck); load_buttons.addStretch(1); load_buttons.addWidget(load); load_layout.addLayout(load_buttons); self.tabs.addTab(load_page, "Load")
        recipe_page = QWidget(); recipe_layout = QVBoxLayout(recipe_page); self.reference = QComboBox(); self.reference.currentIndexChanged.connect(self._refresh_comparison); recipe_layout.addWidget(self.reference); self.comparison = QTableWidget(0, 1); self.comparison.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); self.comparison.itemChanged.connect(self._edit_parameter); recipe_layout.addWidget(self.comparison, 1); self.tabs.addTab(recipe_page, "Recipes")
        tests_page = QWidget(); tests_layout = QVBoxLayout(tests_page); self.tests_table = QTableWidget(0, 1); self.tests_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); tests_layout.addWidget(self.tests_table); self.tabs.addTab(tests_page, "Tests")
        footer = QHBoxLayout(); configure = QPushButton("Configure Visible Parameters"); configure.clicked.connect(self._toggle_compact); save = QPushButton("Save All Recipes"); save.clicked.connect(self._save); footer.addWidget(configure); footer.addStretch(1); footer.addWidget(save); root.addLayout(footer); self._refresh_available()

    def _filtered(self):
        term = self.filter.text().strip().casefold(); scope = self.scope.currentText()
        output = []
        for recipe in self.all_recipes:
            source = str(recipe.get("source", "local")).upper()
            if scope != "All" and source != scope.upper(): continue
            if self.production_only.isChecked() and recipe.get("approval") != "Production": continue
            haystack = " ".join(str(recipe.get(key, "")) for key in ("inspection", "device", "step")).casefold()
            if term and term not in haystack: continue
            output.append(recipe)
        return output

    def _refresh_available(self):
        recipes = self._filtered(); self._available_rows = recipes; self.available.setRowCount(len(recipes))
        for row, recipe in enumerate(recipes):
            values = ["", recipe.get("inspection", ""), recipe.get("last_modified", ""), recipe.get("device", ""), recipe.get("step", ""), recipe.get("status", "")]
            for column, value in enumerate(values): self.available.setItem(row, column, QTableWidgetItem(str(value)))

    def _load(self):
        rows = sorted({index.row() for index in self.available.selectedIndexes()})
        self.loaded_recipes = [deepcopy(self._available_rows[row]) for row in rows]
        self.reference.clear()
        for recipe in self.loaded_recipes: self.reference.addItem(f"Reference: {recipe.get('inspection', '')}", recipe.get("id"))
        self.tabs.setCurrentIndex(1); self._refresh_comparison()

    def _refresh_comparison(self):
        rows = [row for row in compare_recipes(self.loaded_recipes, self.reference.currentData() or "") if row["category"] in self.visible_categories]
        self._comparison_rows = rows
        self._building_comparison = True
        self.comparison.setColumnCount(1 + len(self.loaded_recipes)); self.comparison.setHorizontalHeaderLabels(["Parameter"] + [item.get("inspection", "") for item in self.loaded_recipes]); self.comparison.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            self.comparison.setItem(row_index, 0, QTableWidgetItem(row["parameter"]))
            for column, value in enumerate(row["values"], 1):
                item = QTableWidgetItem(str(value));
                if row["different"][column - 1]: item.setBackground(QColor("#dff4da"))
                self.comparison.setItem(row_index, column, item)
        test_rows = [row for row in rows if row["category"] == "tests"]
        self.tests_table.setColumnCount(self.comparison.columnCount()); self.tests_table.setHorizontalHeaderLabels(["Test Parameter"] + [item.get("inspection", "") for item in self.loaded_recipes]); self.tests_table.setRowCount(len(test_rows))
        for row_index, row in enumerate(test_rows):
            self.tests_table.setItem(row_index, 0, QTableWidgetItem(row["parameter"]))
            for column, value in enumerate(row["values"], 1): self.tests_table.setItem(row_index, column, QTableWidgetItem(str(value)))
        self._building_comparison = False

    def _edit_parameter(self, item):
        if getattr(self, "_building_comparison", False) or item.column() == 0:
            return
        row = item.row(); recipe_index = item.column() - 1
        if row >= len(getattr(self, "_comparison_rows", [])) or recipe_index >= len(self.loaded_recipes):
            return
        old = self._comparison_rows[row]["values"][recipe_index]
        text = item.text()
        if isinstance(old, bool): value = text.strip().casefold() in {"1", "true", "yes", "on"}
        elif isinstance(old, int):
            try: value = int(text)
            except ValueError: value = old
        elif isinstance(old, float):
            try: value = float(text)
            except ValueError: value = old
        elif old is None and text.strip().casefold() == "none": value = None
        else: value = text
        try:
            self.loaded_recipes[recipe_index] = set_recipe_parameter(self.loaded_recipes[recipe_index], self._comparison_rows[row]["parameter"], value)
        except (KeyError, IndexError, ValueError, TypeError):
            return
        self._refresh_comparison()

    def _toggle_compact(self):
        compact = {"inspection", "device", "step", "status", "approval", "wafer_properties", "tests"}
        self.visible_categories = set(self.CATEGORIES) if self.visible_categories == compact else compact
        self._refresh_comparison()

    def _save(self): self.result_recipes = deepcopy(self.loaded_recipes); self.accept()

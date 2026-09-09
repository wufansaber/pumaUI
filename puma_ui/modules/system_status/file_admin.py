from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

from ...qt_compat import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


class FileAdministrationDialog(QDialog):
    """Local counterpart of the standalone File Administration utility."""

    def __init__(self, recipe_store, parent=None):
        super().__init__(parent)
        self.store = recipe_store
        self.last_operation = None
        self.setWindowTitle("File Administration Utility")
        self.resize(900, 560)

        root = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("File Family"))
        self.family = QComboBox()
        self.family.addItems(["Inspection Recipes", "Result Files"])
        self.family.currentTextChanged.connect(self._refresh)
        toolbar.addWidget(self.family)
        toolbar.addStretch(1)
        root.addLayout(toolbar)

        self.table = QTableWidget(0, 5)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        root.addWidget(self.table, 1)

        destination = QHBoxLayout()
        destination.addWidget(QLabel("Destination"))
        self.destination = QLineEdit(str(Path.cwd() / "runtime" / "File Administration"))
        destination.addWidget(self.destination, 1)
        browse = QPushButton("Browse...")
        browse.clicked.connect(self._browse)
        destination.addWidget(browse)
        root.addLayout(destination)

        self.status = QLabel("Select an item, then choose an operation.")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

        operations = QHBoxLayout()
        for label, handler in (
            ("Copy", self._copy),
            ("Move", self._move),
            ("Delete", self._delete),
            ("Convert Recipe Layout", self._convert),
        ):
            button = QPushButton(label)
            button.clicked.connect(handler)
            operations.addWidget(button)
        operations.addStretch(1)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        operations.addWidget(close)
        root.addLayout(operations)
        self._refresh()

    def _items(self):
        if self.family.currentText() == "Inspection Recipes":
            return self.store.list_recipes()
        return self.store.list_results()

    def _refresh(self):
        recipes = self.family.currentText() == "Inspection Recipes"
        headers = (
            ["Inspection", "Device", "Step", "Status", "Path"]
            if recipes
            else ["Lot ID", "Wafer ID", "Inspection", "Status", "Path"]
        )
        self.table.setHorizontalHeaderLabels(headers)
        items = self._items()
        self.table.setRowCount(len(items))
        for row, item in enumerate(items):
            values = (
                [item.get("inspection", ""), item.get("device", ""), item.get("step", ""), item.get("status", ""), item.get("path", "")]
                if recipes
                else [item.get("lot_id", ""), item.get("wafer_id", ""), item.get("inspection", ""), item.get("status", ""), item.get("path", "")]
            )
            for column, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                if column == 0:
                    cell.setData(0x0100, item.get("id", ""))
                self.table.setItem(row, column, cell)
        if items:
            self.table.selectRow(0)

    def _selected(self):
        row = self.table.currentRow()
        if row < 0 or self.table.item(row, 0) is None:
            QMessageBox.warning(self, "File Administration", "Select a recipe or result file first.")
            return None
        item_id = self.table.item(row, 0).data(0x0100)
        return next((item for item in self._items() if item.get("id") == item_id), None)

    def _destination_path(self):
        text = self.destination.text().strip()
        if not text:
            QMessageBox.warning(self, "File Administration", "Select a destination directory first.")
            return None
        path = Path(text)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _browse(self):
        selected = QFileDialog.getExistingDirectory(self, "Select Destination", self.destination.text())
        if selected:
            self.destination.setText(selected)

    @staticmethod
    def _write_managed_file(path, payload):
        Path(path).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _copy(self):
        item = self._selected()
        destination = self._destination_path() if item else None
        if item is None or destination is None:
            return
        if self.family.currentText() == "Inspection Recipes":
            base = f"{item.get('inspection', 'Recipe')}_Copy"
            names = {recipe.get("inspection") for recipe in self.store.list_recipes()}
            name = base
            suffix = 2
            while name in names:
                name = f"{base}_{suffix}"
                suffix += 1
            copied = self.store.duplicate_recipe(item, name)
            copied["path"] = str(destination / f"{name}.json")
            copied = self.store.save_recipe(copied, event="FileAdmin Copy")
            self._write_managed_file(copied["path"], copied)
            detail = name
        else:
            copied = deepcopy(item)
            copied["id"] = uuid4().hex
            copied["path"] = str(destination / f"{copied.get('lot_id', 'Lot')}_{copied.get('wafer_id', 'Wafer')}.json")
            copied = self.store.save_result(copied)
            self._write_managed_file(copied["path"], copied)
            detail = f"{copied.get('lot_id', '')}/{copied.get('wafer_id', '')}"
        self.last_operation = ("copy", detail)
        self.status.setText(f"Copied {detail} to {destination}.")
        self._refresh()

    def _move(self):
        item = self._selected()
        destination = self._destination_path() if item else None
        if item is None or destination is None:
            return
        if self.family.currentText() == "Inspection Recipes":
            item["path"] = str(destination / f"{item.get('inspection', 'Recipe')}.json")
            item = self.store.save_recipe(item, event="FileAdmin Move")
            self._write_managed_file(item["path"], item)
            detail = item.get("inspection", "")
        else:
            item["path"] = str(destination / f"{item.get('lot_id', 'Lot')}_{item.get('wafer_id', 'Wafer')}.json")
            item = self.store.save_result(item)
            self._write_managed_file(item["path"], item)
            detail = f"{item.get('lot_id', '')}/{item.get('wafer_id', '')}"
        self.last_operation = ("move", detail)
        self.status.setText(f"Moved {detail} to {destination}.")
        self._refresh()

    def _delete(self):
        item = self._selected()
        if item is None:
            return
        recipe_family = self.family.currentText() == "Inspection Recipes"
        label = item.get("inspection") if recipe_family else f"{item.get('lot_id', '')}/{item.get('wafer_id', '')}"
        if QMessageBox.question(self, "Delete File", f"Delete {label}?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        if recipe_family:
            self.store.delete_recipe(item.get("id", ""))
        else:
            self.store.delete_result(item.get("id", ""))
        self.last_operation = ("delete", label)
        self.status.setText(f"Deleted {label}.")
        self._refresh()

    def _convert(self):
        if self.family.currentText() != "Inspection Recipes":
            QMessageBox.information(self, "Convert Recipe Layout", "Recipe layout conversion applies only to Inspection Recipes.")
            return
        recipe = self._selected()
        destination = self._destination_path() if recipe else None
        if recipe is None or destination is None:
            return
        safe_name = "".join(character if character.isalnum() or character in "-_" else "_" for character in recipe.get("inspection", "Recipe"))
        output = destination / f"{safe_name}.layout.json"
        payload = {
            "layout_version": "9.8.306",
            "inspection": recipe.get("inspection", ""),
            "device": recipe.get("device", ""),
            "step": recipe.get("step", ""),
            "sections": {
                key: deepcopy(recipe.get(key))
                for key in ("wafer_properties", "alignment", "wafer_map", "tests", "lot_plan", "wafer_post_processing")
                if key in recipe
            },
        }
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self.last_operation = ("convert", str(output))
        self.status.setText(f"Converted recipe layout: {output}")

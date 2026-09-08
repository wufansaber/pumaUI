from __future__ import annotations

from copy import deepcopy
from typing import Dict, List, Optional, Tuple

from ...qt_compat import (
    QDialog,
    QHBoxLayout,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    Qt,
    QVBoxLayout,
    QWidget,
)


ParameterTree = List[Tuple[str, List[Tuple[str, List[str]]]]]


PARAMETER_TREE: ParameterTree = [
    (
        "Recipe Properties",
        [
            ("Inspection Properties", ["Recipe Name", "Device Name", "Layer Name", "Recipe Type", "Approval"]),
            ("Creation Properties", ["Creation Time", "Last Modification", "Software Version", "History Log"]),
            ("Load/Save Status", ["Validation Status", "Status", "State", "Path"]),
        ],
    ),
    (
        "Wafer Layout",
        [
            (
                "Wafer Properties",
                [
                    "Diameter",
                    "Wafer Type",
                    "Orientation",
                    "Align Mark",
                    "Laser Power Sensitive",
                    "Laser Power Factor",
                    "Layer",
                    "Dark Wafer",
                    "Wafer Darkness Level",
                ],
            ),
            ("Alignment", []),
            ("Registration Sites", []),
            ("Die Layout", ["Die Width", "Die Height", "Reticle Size", "Street Size", "Inner Die", "Valid Dies"]),
            ("Die Corner", []),
            ("Wafer Map", []),
            ("Design Files", ["Selected RDF"]),
        ],
    ),
    (
        "Test 1",
        [
            ("Test Properties", ["Test Name", "Test Orientation", "Light Trained", "Save Patch Images", "Save Feature Vectors"]),
            ("Inspection Optics", ["Magnification", "Focus Offset", "Polarization", "Incidence Angle", "Speed"]),
            ("Collection Optics", []),
            ("Illumination Level Optimization", ["Noise Boxes"]),
            ("Fourier Filter", []),
            ("Light Level Sensitivity", []),
            ("Sensitivity", []),
            ("Defect Filters", []),
            ("Care Areas", []),
            ("Sample Plan", []),
        ],
    ),
    (
        "Wafer Post Processing",
        [
            (
                "Processing Summary",
                ["Processing Status", "Template", "Enabled Operations", "Execution Order"],
            ),
        ],
    ),
]


DEFAULT_VISIBLE_RECIPE_PARAMETERS: Dict[str, bool] = {
    "Recipe Properties": True,
    "Inspection Properties": True,
    "Recipe Name": True,
    "Device Name": True,
    "Layer Name": True,
    "Recipe Type": True,
    "Approval": True,
    "Creation Properties": True,
    "Creation Time": True,
    "Last Modification": True,
    "Software Version": True,
    "History Log": False,
    "Load/Save Status": True,
    "Validation Status": True,
    "Status": True,
    "State": True,
    "Path": True,
    "Wafer Layout": True,
    "Wafer Properties": True,
    "Diameter": True,
    "Wafer Type": True,
    "Orientation": True,
    "Align Mark": True,
    "Laser Power Sensitive": True,
    "Laser Power Factor": True,
    "Layer": True,
    "Dark Wafer": True,
    "Wafer Darkness Level": True,
    "Alignment": True,
    "Registration Sites": True,
    "Die Layout": True,
    "Die Width": True,
    "Die Height": True,
    "Reticle Size": True,
    "Street Size": True,
    "Inner Die": True,
    "Valid Dies": True,
    "Die Corner": True,
    "Wafer Map": True,
    "Design Files": True,
    "Selected RDF": True,
    "Test 1": True,
    "Test Properties": True,
    "Test Name": True,
    "Test Orientation": True,
    "Light Trained": True,
    "Save Patch Images": True,
    "Save Feature Vectors": True,
    "Inspection Optics": True,
    "Magnification": True,
    "Focus Offset": True,
    "Polarization": True,
    "Incidence Angle": True,
    "Speed": True,
    "Collection Optics": True,
    "Illumination Level Optimization": True,
    "Noise Boxes": True,
    "Fourier Filter": True,
    "Light Level Sensitivity": True,
    "Sensitivity": True,
    "Defect Filters": True,
    "Care Areas": True,
    "Sample Plan": True,
    "Wafer Post Processing": True,
    "Processing Summary": True,
    "Processing Status": True,
    "Template": True,
    "Enabled Operations": True,
    "Execution Order": True,
}


class SelectVisibleRecipeParametersDialog(QDialog):
    def __init__(
        self,
        visible_parameters: Dict[str, bool],
        parent: Optional[QWidget] = None,
        *,
        test_count: int = 1,
    ):
        super().__init__(parent)
        self.setWindowTitle("Select Visible Recipe Parameters")
        self.resize(430, 600)
        self.setMinimumSize(380, 480)
        self.visible_parameters = dict(DEFAULT_VISIBLE_RECIPE_PARAMETERS)
        self.visible_parameters.update(visible_parameters)
        self.result_parameters = None
        self.item_by_name = {}
        self.parameter_tree = self._parameter_tree(test_count)
        self._build_ui()
        self._populate_tree()

    @staticmethod
    def _parameter_tree(test_count: int) -> ParameterTree:
        tree = deepcopy(PARAMETER_TREE)
        test_template = next(item for item in tree if item[0] == "Test 1")[1]
        wpp = next(item for item in tree if item[0] == "Wafer Post Processing")
        tree = [
            item for item in tree
            if item[0] not in {"Test 1", "Wafer Post Processing"}
        ]
        for index in range(max(1, int(test_count))):
            tree.append((f"Test {index + 1}", deepcopy(test_template)))
        tree.append(wpp)
        return tree

    def _build_ui(self):
        self.setStyleSheet(
            """
            QDialog {
                background: #d7d4c9;
                color: #111111;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10px;
            }
            QTreeWidget {
                background: #ffffff;
                border: 1px solid #8f8b82;
                font-size: 10px;
            }
            QPushButton {
                background: #e7e5dc;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-height: 26px;
                padding: 2px 18px;
            }
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemChanged.connect(self._item_changed)
        layout.addWidget(self.tree, 1)

        buttons = QHBoxLayout()
        reset = QPushButton("Reset")
        reset.clicked.connect(self._reset)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("OK")
        ok.clicked.connect(self._accept)
        buttons.addWidget(reset)
        buttons.addStretch(1)
        buttons.addWidget(cancel)
        buttons.addWidget(ok)
        layout.addLayout(buttons)

    def _populate_tree(self):
        self.tree.blockSignals(True)
        self.tree.clear()
        self.item_by_name = {}
        for section, groups in self.parameter_tree:
            section_item = self._make_item(section)
            self.tree.addTopLevelItem(section_item)
            for group, fields in groups:
                group_item = self._make_item(group)
                section_item.addChild(group_item)
                for field in fields:
                    group_item.addChild(self._make_item(field))
        self.tree.expandAll()
        self.tree.blockSignals(False)

    def _make_item(self, name: str) -> QTreeWidgetItem:
        item = QTreeWidgetItem([name])
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        checked = self.visible_parameters.get(name, True)
        item.setCheckState(0, Qt.Checked if checked else Qt.Unchecked)
        self.item_by_name.setdefault(name, []).append(item)
        return item

    def _item_changed(self, item: QTreeWidgetItem, column: int):
        self.tree.blockSignals(True)
        name = item.text(0)
        for peer in self.item_by_name.get(name, []):
            if peer is not item:
                peer.setCheckState(0, item.checkState(0))
        self._set_children_checked(item, item.checkState(0))
        self._refresh_parent_state(item.parent())
        self.tree.blockSignals(False)

    def _set_children_checked(self, item: QTreeWidgetItem, state):
        for index in range(item.childCount()):
            child = item.child(index)
            child.setCheckState(0, state)
            self._set_children_checked(child, state)

    def _refresh_parent_state(self, item):
        while item is not None:
            checked_count = 0
            partial_count = 0
            for index in range(item.childCount()):
                child_state = item.child(index).checkState(0)
                if child_state == Qt.Checked:
                    checked_count += 1
                elif child_state == Qt.PartiallyChecked:
                    partial_count += 1
            if checked_count == item.childCount():
                item.setCheckState(0, Qt.Checked)
            elif checked_count == 0 and partial_count == 0:
                item.setCheckState(0, Qt.Unchecked)
            else:
                item.setCheckState(0, Qt.PartiallyChecked)
            item = item.parent()

    def _reset(self):
        self.visible_parameters = dict(DEFAULT_VISIBLE_RECIPE_PARAMETERS)
        self._populate_tree()

    def _accept(self):
        self.result_parameters = {}
        for name, items in self.item_by_name.items():
            self.result_parameters[name] = items[0].checkState(0) != Qt.Unchecked
        self.accept()

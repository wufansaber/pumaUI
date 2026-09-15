from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re
from xml.etree import ElementTree

from ...qt_compat import (
    QCheckBox,
    QColor,
    QComboBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPainter,
    QPen,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    Qt,
    QVBoxLayout,
    QWidget,
)


def _canonical_key(value) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def _metadata_lookup(metadata, *names):
    wanted = {_canonical_key(name) for name in names}
    for key, value in (metadata or {}).items():
        if _canonical_key(key) in wanted and not isinstance(value, (dict, list)):
            return value
    return ""


def _normalized_orientation(value) -> str:
    text = str(value or "").strip()
    compact = _canonical_key(text)
    if not compact:
        return ""
    for marker, orientation in (
        ("270", "Left (270 deg.)"),
        ("180", "Down (180 deg.)"),
        ("90", "Right (90 deg.)"),
        ("0", "Up (0 deg.)"),
    ):
        if marker in compact:
            return orientation
    for marker, orientation in (
        ("left", "Left (270 deg.)"),
        ("down", "Down (180 deg.)"),
        ("right", "Right (90 deg.)"),
        ("up", "Up (0 deg.)"),
    ):
        if marker in compact:
            return orientation
    return text


def default_classifier_decision_tree(classifier_type="ST-NEF"):
    if classifier_type == "iDO":
        return [
            {"id": 1, "parent_id": None, "name": "Rough Code", "type": "Attribute", "branch": ""},
            {"id": 2, "parent_id": 1, "name": "Bin 0", "type": "Output", "branch": "0"},
            {"id": 3, "parent_id": 1, "name": "Classified", "type": "Output", "branch": "1-255"},
        ]
    return [
        {"id": 1, "parent_id": None, "name": "Polarity", "type": "Attribute", "branch": ""},
        {
            "id": 2,
            "parent_id": 1,
            "name": "Nuisance",
            "type": "Output",
            "branch": "Dark",
            "nuisance": True,
        },
        {"id": 3, "parent_id": 1, "name": "Defect", "type": "Output", "branch": "Bright"},
    ]


def _normalized_decision_tree(nodes, classifier_type="ST-NEF"):
    if not isinstance(nodes, list) or not nodes:
        return default_classifier_decision_tree(classifier_type)
    result = []
    identifiers = set()
    for index, value in enumerate(nodes, start=1):
        if not isinstance(value, dict):
            continue
        identifier = value.get("id", index)
        if identifier in identifiers:
            identifier = index
        identifiers.add(identifier)
        result.append(
            {
                "id": identifier,
                "parent_id": value.get("parent_id"),
                "name": str(value.get("name") or f"Node {index}"),
                "type": str(value.get("type") or "Attribute"),
                "branch": str(value.get("branch") or ""),
                "nuisance": bool(value.get("nuisance", False)),
            }
        )
    return result or default_classifier_decision_tree(classifier_type)


def _xml_value(element):
    children = list(element)
    if not children:
        return (element.text or "").strip()
    result = dict(element.attrib)
    for child in children:
        value = _xml_value(child)
        if child.tag in result:
            existing = result[child.tag]
            result[child.tag] = existing + [value] if isinstance(existing, list) else [existing, value]
        else:
            result[child.tag] = value
    return result


def _parse_classifier_metadata(path: Path) -> tuple[dict, str]:
    if not path.is_file():
        return {}, "Filename only"
    try:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return {}, "Unreadable"
    if not text:
        return {}, "Empty file"
    try:
        if path.suffix.lower() == ".json" or text.startswith(("{", "[")):
            value = json.loads(text)
            return (value if isinstance(value, dict) else {"Tree": value}), "JSON metadata"
        if path.suffix.lower() == ".xml" or text.startswith("<"):
            root = ElementTree.fromstring(text)
            value = _xml_value(root)
            metadata = value if isinstance(value, dict) else {root.tag: value}
            metadata.setdefault("Root", root.tag)
            return metadata, "XML metadata"
    except (json.JSONDecodeError, ElementTree.ParseError):
        return {}, "Metadata parse error"
    metadata = {}
    for line in text.splitlines():
        match = re.match(r"\s*([^:=]+?)\s*[:=]\s*(.*?)\s*$", line)
        if match:
            metadata[match.group(1)] = match.group(2)
    return metadata, "Text metadata" if metadata else "Binary/opaque classifier"


def _normalized_classifier(item) -> dict:
    item = item if isinstance(item, dict) else {}
    kind = "iDO" if str(item.get("type", "")).lower() == "ido" else "ST-NEF"
    metadata = deepcopy(item.get("metadata") or {})
    orientation = _normalized_orientation(
        item.get("orientation")
        or _metadata_lookup(metadata, "orientation", "test orientation", "wafer orientation")
    )
    feature_version = str(
        item.get("feature_vector_version")
        or _metadata_lookup(metadata, "feature vector version", "feature version", "version id")
        or ""
    ).strip()
    rough_code = str(
        item.get("rough_code") or _metadata_lookup(metadata, "rough code", "roughcode") or ""
    ).strip()
    return {
        "name": str(item.get("name") or "ST-NEF_Default"),
        "type": kind,
        "st_nef": bool(item.get("st_nef", kind == "ST-NEF")),
        "path": str(item.get("path") or ""),
        "orientation": orientation,
        "feature_vector_version": feature_version,
        "rough_code": rough_code,
        "metadata": metadata,
        "tree": deepcopy(item.get("tree") or metadata.get("Tree") or metadata.get("tree") or {}),
        "decision_tree": _normalized_decision_tree(item.get("decision_tree"), kind),
        "apply_nuisance": bool(item.get("apply_nuisance", kind == "ST-NEF")),
        "parse_status": str(item.get("parse_status") or ("Loaded" if metadata else "Filename only")),
    }


def normalize_classifier(classifier):
    return _normalized_classifier(classifier) if classifier else None


def classifier_from_path(path: str, classifier_type: str = "ST-NEF") -> dict:
    clean_path = str(path or "").strip()
    kind = "iDO" if classifier_type == "iDO" else "ST-NEF"
    metadata, parse_status = _parse_classifier_metadata(Path(clean_path)) if clean_path else ({}, "Filename only")
    name = str(
        _metadata_lookup(metadata, "classifier name", "name")
        or (Path(clean_path).stem if clean_path else "")
    ).strip()
    return _normalized_classifier({
        "name": name,
        "type": kind,
        "st_nef": kind == "ST-NEF",
        "path": clean_path,
        "metadata": metadata,
        "parse_status": parse_status,
    })


def default_nef_state():
    return {
        "setup_name": "",
        "classifiers": [],
        "keep_nuisance_defects": False,
        "auto_refresh": True,
        "saved_setups": {},
    }


def normalize_nef_state(state):
    result = default_nef_state()
    if isinstance(state, dict):
        result.update(deepcopy(state))
    classifiers = []
    for item in result.get("classifiers", []):
        if not isinstance(item, dict):
            continue
        classifiers.append(_normalized_classifier(item))
    result["classifiers"] = classifiers
    result["saved_setups"] = deepcopy(result.get("saved_setups") or {})
    return result


def classifier_compatibility_errors(classifier, test_orientation="", feature_vector_version=""):
    classifier = _normalized_classifier(classifier)
    errors = []
    orientation = classifier.get("orientation", "")
    if test_orientation and orientation and orientation != test_orientation:
        errors.append(
            f"{classifier['name']} orientation {orientation} does not match Test orientation {test_orientation}"
        )
    classifier_version = classifier.get("feature_vector_version", "")
    if feature_vector_version and classifier_version and classifier_version != feature_vector_version:
        errors.append(
            f"{classifier['name']} Feature Vector version {classifier_version} does not match recipe version {feature_vector_version}"
        )
    return errors


def validate_nef_state(state, test_orientation="", feature_vector_version=""):
    state = normalize_nef_state(state)
    errors = []
    classifiers = state["classifiers"]
    if len(classifiers) > 5:
        errors.append("No more than five NEF/iDO classifiers may be attached")
    if any(not item["name"].strip() for item in classifiers):
        errors.append("Every NEF classifier requires a name")
    for classifier in classifiers:
        errors.extend(
            classifier_compatibility_errors(
                classifier,
                test_orientation,
                feature_vector_version,
            )
        )
    return errors


def _add_tree_value(parent, label, value):
    item = QTreeWidgetItem([str(label), "" if isinstance(value, (dict, list)) else str(value)])
    parent.addChild(item)
    if isinstance(value, dict):
        for key, child in value.items():
            _add_tree_value(item, key, child)
    elif isinstance(value, list):
        for index, child in enumerate(value, start=1):
            _add_tree_value(item, f"Item {index}", child)
    return item


def populate_classifier_tree(tree, classifier):
    classifier = _normalized_classifier(classifier)
    tree.clear()
    root = QTreeWidgetItem([classifier["name"], classifier["type"]])
    tree.addTopLevelItem(root)
    for label, key in (
        ("Path", "path"),
        ("Orientation", "orientation"),
        ("Feature Vector Version", "feature_vector_version"),
        ("Rough Code", "rough_code"),
        ("Read Status", "parse_status"),
    ):
        _add_tree_value(root, label, classifier.get(key) or "-")
    metadata = classifier.get("tree") or classifier.get("metadata") or {}
    if metadata:
        _add_tree_value(root, "Classifier Tree", metadata)
    tree.expandAll()


class ClassifierTreeCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.nodes = []
        self.selected_node_id = None
        self.node_rects = {}
        self.on_selection_changed = None
        self.setMinimumSize(300, 280)

    def set_classifier(self, classifier):
        classifier = _normalized_classifier(classifier) if classifier else None
        self.set_nodes(classifier.get("decision_tree", []) if classifier else [])

    def set_nodes(self, nodes, selected_id=None):
        self.nodes = deepcopy(nodes or [])
        identifiers = {node.get("id") for node in self.nodes}
        self.selected_node_id = selected_id if selected_id in identifiers else (
            self.nodes[0].get("id") if self.nodes else None
        )
        self.update()
        if self.on_selection_changed:
            self.on_selection_changed(self.selected_node())

    def selected_node(self):
        return next(
            (node for node in self.nodes if node.get("id") == self.selected_node_id),
            None,
        )

    def select_node(self, node_id):
        if any(node.get("id") == node_id for node in self.nodes):
            self.selected_node_id = node_id
            self.update()
            if self.on_selection_changed:
                self.on_selection_changed(self.selected_node())

    def _layout(self):
        if not self.nodes:
            return {}, {}
        by_id = {node.get("id"): node for node in self.nodes}
        depths = {}

        def depth(node_id, trail=None):
            if node_id in depths:
                return depths[node_id]
            trail = set(trail or ())
            if node_id in trail:
                return 0
            trail.add(node_id)
            parent_id = by_id.get(node_id, {}).get("parent_id")
            value = 0 if parent_id not in by_id else depth(parent_id, trail) + 1
            depths[node_id] = value
            return value

        levels = {}
        for node in self.nodes:
            levels.setdefault(depth(node.get("id")), []).append(node)
        positions = {}
        maximum_depth = max(levels, default=0)
        vertical_step = max(72, min(112, (self.height() - 80) // max(1, maximum_depth)))
        for level, nodes in levels.items():
            for index, node in enumerate(nodes, start=1):
                positions[node.get("id")] = (
                    int(index * self.width() / (len(nodes) + 1)),
                    48 + level * vertical_step,
                )
        return positions, by_id

    def mousePressEvent(self, event):
        point = event.position() if hasattr(event, "position") else event.pos()
        for node_id, rect in self.node_rects.items():
            x, y, width, height = rect
            if x <= point.x() <= x + width and y <= point.y() <= y + height:
                self.select_node(node_id)
                return

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#ffffff"))
        positions, by_id = self._layout()
        self.node_rects = {}
        if not positions:
            painter.setPen(QColor("#777777"))
            painter.drawText(self.rect(), Qt.AlignCenter, "Select or add a classifier to view its tree.")
            return

        painter.setPen(QPen(QColor("#c9c6f5"), 3))
        for node in self.nodes:
            parent = by_id.get(node.get("parent_id"))
            if parent is None:
                continue
            x, y = positions[node.get("id")]
            parent_x, parent_y = positions[parent.get("id")]
            painter.drawLine(parent_x, parent_y + 18, x, y - 18)
            branch = node.get("branch", "")
            if branch:
                painter.setPen(QPen(QColor("#5f5d57"), 1))
                painter.drawText((parent_x + x) // 2 - 32, (parent_y + y) // 2 - 10, 64, 20, Qt.AlignCenter, branch)
                painter.setPen(QPen(QColor("#c9c6f5"), 3))

        for node in self.nodes:
            node_id = node.get("id")
            x, y = positions[node_id]
            width, height = 94, 34
            rect = (x - width // 2, y - height // 2, width, height)
            self.node_rects[node_id] = rect
            selected = node_id == self.selected_node_id
            outline = QColor("#2457a6" if selected else "#77736b")
            if node.get("type") == "Output":
                fill = QColor("#1d1d1d" if node.get("nuisance") else "#d9d7cf")
                painter.setBrush(fill)
                painter.setPen(QPen(outline, 2 if selected else 1))
                painter.drawRoundedRect(*rect, 5, 5)
                painter.setPen(QColor("#ffffff" if node.get("nuisance") else "#202020"))
            else:
                painter.setBrush(QColor("#d9e4f3"))
                painter.setPen(QPen(outline, 2 if selected else 1))
                painter.drawRoundedRect(*rect, 12, 12)
                painter.setPen(QColor("#202020"))
            painter.drawText(*rect, Qt.AlignCenter, str(node.get("name", "Node")))
            if node.get("nuisance"):
                painter.setPen(QColor("#d7191c"))
                painter.drawText(rect[0], rect[1] + rect[3] + 3, rect[2], 18, Qt.AlignCenter, "Nuisance")


class NuisanceFilterSetupDialog(QDialog):
    def __init__(self, state=None, parent=None):
        super().__init__(parent)
        self.state = normalize_nef_state(state)
        self.result_state = None
        self.setWindowTitle("Nuisance Filter Setup")
        self.resize(760, 500)
        root = QVBoxLayout(self)
        top = QGridLayout()
        top.addWidget(QLabel("Setup Name"), 0, 0)
        self.setup_name = QLineEdit(self.state.get("setup_name", ""))
        top.addWidget(self.setup_name, 0, 1)
        self.saved = QComboBox()
        self.saved.addItem("Saved Setups")
        self.saved.addItems(sorted(self.state["saved_setups"]))
        self.saved.currentTextChanged.connect(self._load_setup)
        top.addWidget(self.saved, 0, 2)
        root.addLayout(top)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Order", "Classifier Type", "Classifier Name", "ST-NEF"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self._show_selected_classifier)

        tree_panel = QWidget()
        tree_layout = QVBoxLayout(tree_panel)
        tree_layout.setContentsMargins(0, 0, 0, 0)
        tree_toolbar = QHBoxLayout()
        self.starter_tree_button = QPushButton("Starter Tree")
        self.starter_tree_button.clicked.connect(self._create_starter_tree)
        tree_toolbar.addWidget(self.starter_tree_button)
        self.nn_classifier_button = QPushButton("NN Classifier")
        nn_menu = QMenu(self.nn_classifier_button)
        self.add_nn_action = nn_menu.addAction("Add NN Classifier")
        self.add_nn_action.triggered.connect(self._add_nn_classifier)
        self.add_split_action = nn_menu.addAction("Add Polarity Split")
        self.add_split_action.triggered.connect(self._add_polarity_split)
        self.nn_classifier_button.setMenu(nn_menu)
        tree_toolbar.addWidget(self.nn_classifier_button)
        self.delete_tree_node_button = QPushButton("Delete Node")
        self.delete_tree_node_button.clicked.connect(self._delete_tree_node)
        tree_toolbar.addWidget(self.delete_tree_node_button)
        tree_toolbar.addStretch(1)
        tree_layout.addLayout(tree_toolbar)

        self.tree_tabs = QTabWidget()
        self.tree_canvas = ClassifierTreeCanvas()
        self.tree_canvas.on_selection_changed = self._tree_node_selected
        self.tree_tabs.addTab(self.tree_canvas, "Classifier Tree")
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Classifier Details", "Value"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tree_tabs.addTab(self.tree, "Details")
        tree_layout.addWidget(self.tree_tabs, 1)

        tree_options = QHBoxLayout()
        self.auto_refresh = QCheckBox("Auto Refresh")
        self.auto_refresh.setChecked(bool(self.state.get("auto_refresh", True)))
        self.auto_refresh.toggled.connect(self._auto_refresh_changed)
        self.apply_nuisance = QCheckBox("Apply Nuisance")
        self.apply_nuisance.toggled.connect(self._apply_nuisance_changed)
        tree_options.addWidget(self.auto_refresh)
        tree_options.addWidget(self.apply_nuisance)
        tree_options.addStretch(1)
        tree_layout.addLayout(tree_options)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.table)
        splitter.addWidget(tree_panel)
        splitter.setSizes([430, 330])
        root.addWidget(splitter, 1)
        add_row = QHBoxLayout()
        self.classifier_type = QComboBox()
        self.classifier_type.addItems(["ST-NEF", "iDO"])
        self.classifier_name = QLineEdit("ST-NEF_Default")
        add = QPushButton("Add")
        add.clicked.connect(self._add)
        browse = QPushButton("Browse...")
        browse.clicked.connect(self._browse)
        add_row.addWidget(self.classifier_type)
        add_row.addWidget(self.classifier_name, 1)
        add_row.addWidget(browse)
        add_row.addWidget(add)
        root.addLayout(add_row)
        actions = QHBoxLayout()
        for label, callback in (
            ("Delete", self._remove),
            ("Clear", self._clear),
            ("Move Up", lambda: self._move(-1)),
            ("Move Down", lambda: self._move(1)),
            ("Save Setup", self._save_setup),
            ("Delete Setup", self._delete_setup),
        ):
            button = QPushButton(label)
            button.clicked.connect(callback)
            actions.addWidget(button)
        root.addLayout(actions)
        self.keep_nuisance = QCheckBox("Keep Nuisance Defects")
        self.keep_nuisance.setChecked(bool(self.state.get("keep_nuisance_defects")))
        root.addWidget(self.keep_nuisance)
        root.addWidget(QLabel("Classifiers execute from top to bottom. Place ST-NEF before the final iDO binner."))
        footer = QHBoxLayout()
        footer.addStretch(1)
        ok = QPushButton("OK")
        ok.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        footer.addWidget(ok)
        footer.addWidget(cancel)
        root.addLayout(footer)
        self._populate(self.state["classifiers"])

    def _populate(self, classifiers):
        self.table.setRowCount(0)
        for classifier in classifiers:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            self.table.setItem(row, 1, QTableWidgetItem(classifier["type"]))
            name = QTableWidgetItem(classifier["name"])
            name.setData(256, deepcopy(_normalized_classifier(classifier)))
            self.table.setItem(row, 2, name)
            st_nef = QTableWidgetItem("")
            st_nef.setFlags(st_nef.flags() | Qt.ItemIsUserCheckable)
            st_nef.setCheckState(Qt.Checked if classifier.get("st_nef") else Qt.Unchecked)
            self.table.setItem(row, 3, st_nef)
        if self.table.rowCount():
            self.table.selectRow(0)
        else:
            self.tree.clear()
            self.tree_canvas.set_nodes([])
            self._set_tree_controls_enabled(False)

    def _rows(self):
        result = []
        for row in range(self.table.rowCount()):
            stored = self.table.item(row, 2).data(256)
            classifier = deepcopy(stored) if isinstance(stored, dict) else {}
            classifier.update(
                {
                    "type": self.table.item(row, 1).text(),
                    "name": self.table.item(row, 2).text().strip(),
                    "st_nef": self.table.item(row, 3).checkState() == Qt.Checked,
                }
            )
            result.append(_normalized_classifier(classifier))
        return result

    def _show_selected_classifier(self):
        row = self.table.currentRow()
        rows = self._rows()
        if 0 <= row < len(rows):
            classifier = rows[row]
            populate_classifier_tree(self.tree, classifier)
            if self.auto_refresh.isChecked() or not self.tree_canvas.nodes:
                self.tree_canvas.set_classifier(classifier)
            self.apply_nuisance.blockSignals(True)
            self.apply_nuisance.setChecked(bool(classifier.get("apply_nuisance")))
            self.apply_nuisance.blockSignals(False)
            self._set_tree_controls_enabled(True)
        else:
            self.tree.clear()
            self.tree_canvas.set_nodes([])
            self._set_tree_controls_enabled(False)

    def _selected_classifier(self):
        row = self.table.currentRow()
        rows = self._rows()
        return (row, rows[row]) if 0 <= row < len(rows) else (-1, None)

    def _store_selected_classifier(self, classifier, *, refresh=True):
        row = self.table.currentRow()
        if row < 0 or classifier is None:
            return
        normalized = _normalized_classifier(classifier)
        self.table.item(row, 1).setText(normalized["type"])
        self.table.item(row, 2).setText(normalized["name"])
        self.table.item(row, 2).setData(256, deepcopy(normalized))
        self.table.item(row, 3).setCheckState(
            Qt.Checked if normalized.get("st_nef") else Qt.Unchecked
        )
        if refresh:
            populate_classifier_tree(self.tree, normalized)
            self.tree_canvas.set_classifier(normalized)

    def _set_tree_controls_enabled(self, enabled):
        self.starter_tree_button.setEnabled(enabled)
        self.nn_classifier_button.setEnabled(enabled)
        self.apply_nuisance.setEnabled(enabled)
        selected = self.tree_canvas.selected_node()
        self.delete_tree_node_button.setEnabled(
            bool(enabled and selected and selected.get("parent_id") is not None)
        )

    def _tree_node_selected(self, node):
        self.delete_tree_node_button.setEnabled(
            bool(self.table.currentRow() >= 0 and node and node.get("parent_id") is not None)
        )

    def _auto_refresh_changed(self, checked):
        self.state["auto_refresh"] = bool(checked)
        if checked:
            _row, classifier = self._selected_classifier()
            if classifier:
                self.tree_canvas.set_classifier(classifier)

    def _create_starter_tree(self):
        _row, classifier = self._selected_classifier()
        if not classifier:
            return
        classifier["decision_tree"] = default_classifier_decision_tree(classifier["type"])
        self._store_selected_classifier(classifier)

    def _next_tree_id(self, nodes):
        numeric_ids = [node.get("id") for node in nodes if isinstance(node.get("id"), int)]
        return max(numeric_ids, default=0) + 1

    def _append_split(self, split_name, left_branch, right_branch):
        _row, classifier = self._selected_classifier()
        if not classifier:
            return
        nodes = deepcopy(classifier.get("decision_tree") or [])
        selected = self.tree_canvas.selected_node()
        parent_id = selected.get("id") if selected else (nodes[0].get("id") if nodes else None)
        next_id = self._next_tree_id(nodes)
        nodes.extend(
            [
                {
                    "id": next_id,
                    "parent_id": parent_id,
                    "name": split_name,
                    "type": "NN" if split_name == "NN Classifier" else "Attribute",
                    "branch": "",
                },
                {
                    "id": next_id + 1,
                    "parent_id": next_id,
                    "name": "Nuisance",
                    "type": "Output",
                    "branch": left_branch,
                    "nuisance": True,
                },
                {
                    "id": next_id + 2,
                    "parent_id": next_id,
                    "name": "Defect",
                    "type": "Output",
                    "branch": right_branch,
                },
            ]
        )
        classifier["decision_tree"] = nodes
        self._store_selected_classifier(classifier)
        self.tree_canvas.select_node(next_id)

    def _add_nn_classifier(self):
        self._append_split("NN Classifier", "Nuisance", "Defect")

    def _add_polarity_split(self):
        self._append_split("Polarity", "Dark", "Bright")

    def _delete_tree_node(self):
        _row, classifier = self._selected_classifier()
        selected = self.tree_canvas.selected_node()
        if not classifier or not selected or selected.get("parent_id") is None:
            return
        nodes = deepcopy(classifier.get("decision_tree") or [])
        remove_ids = {selected.get("id")}
        changed = True
        while changed:
            changed = False
            for node in nodes:
                if node.get("parent_id") in remove_ids and node.get("id") not in remove_ids:
                    remove_ids.add(node.get("id"))
                    changed = True
        classifier["decision_tree"] = [
            node for node in nodes if node.get("id") not in remove_ids
        ]
        self._store_selected_classifier(classifier)

    def _apply_nuisance_changed(self, checked):
        _row, classifier = self._selected_classifier()
        if not classifier:
            return
        classifier["apply_nuisance"] = bool(checked)
        self._store_selected_classifier(classifier, refresh=False)

    def _add(self):
        if self.table.rowCount() >= 5:
            QMessageBox.warning(self, "Nuisance Filter Setup", "No more than five classifiers may be attached.")
            return
        name = self.classifier_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Nuisance Filter Setup", "Enter a classifier name.")
            return
        rows = self._rows()
        kind = self.classifier_type.currentText()
        rows.append(_normalized_classifier({"name": name, "type": kind, "st_nef": kind == "ST-NEF"}))
        self._populate(rows)
        self.table.selectRow(self.table.rowCount() - 1)

    def _browse(self):
        kind = self.classifier_type.currentText()
        path, _selected = QFileDialog.getOpenFileName(
            self,
            f"Select a Classifier for {kind}",
            "",
            "Classifier Files (*.nef *.ido *.xml *.json);;All Files (*)",
        )
        if not path:
            return
        if self.table.rowCount() >= 5:
            QMessageBox.warning(
                self,
                "Nuisance Filter Setup",
                "No more than five classifiers may be attached.",
            )
            return
        rows = self._rows()
        rows.append(classifier_from_path(path, kind))
        self._populate(rows)
        self.table.selectRow(self.table.rowCount() - 1)

    def _remove(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)
            for index in range(self.table.rowCount()):
                self.table.item(index, 0).setText(str(index + 1))
            if self.table.rowCount():
                self.table.selectRow(min(row, self.table.rowCount() - 1))
            else:
                self._show_selected_classifier()

    def _clear(self):
        self.table.setRowCount(0)
        self._show_selected_classifier()

    def _move(self, direction):
        row = self.table.currentRow()
        target = row + direction
        if row < 0 or target < 0 or target >= self.table.rowCount():
            return
        rows = self._rows()
        rows[row], rows[target] = rows[target], rows[row]
        self._populate(rows)
        self.table.selectRow(target)

    def _save_setup(self):
        name = self.setup_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Nuisance Filter Setup", "Enter a setup name before saving.")
            return
        self.state["saved_setups"][name] = {
            "classifiers": self._rows(),
            "keep_nuisance_defects": self.keep_nuisance.isChecked(),
        }
        if self.saved.findText(name) < 0:
            self.saved.addItem(name)
        self.saved.setCurrentText(name)

    def _load_setup(self, name):
        setup = self.state["saved_setups"].get(name)
        if not setup:
            return
        self.setup_name.setText(name)
        self._populate(setup.get("classifiers", []))
        self.keep_nuisance.setChecked(bool(setup.get("keep_nuisance_defects")))

    def _delete_setup(self):
        name = self.saved.currentText()
        if name not in self.state["saved_setups"]:
            return
        del self.state["saved_setups"][name]
        self.saved.removeItem(self.saved.currentIndex())

    def _finish(self):
        state = {
            "setup_name": self.setup_name.text().strip(),
            "classifiers": self._rows(),
            "keep_nuisance_defects": self.keep_nuisance.isChecked(),
            "auto_refresh": self.auto_refresh.isChecked(),
            "saved_setups": deepcopy(self.state["saved_setups"]),
        }
        errors = validate_nef_state(state)
        if errors:
            QMessageBox.warning(self, "Nuisance Filter Setup", "\n".join(errors))
            return
        self.result_state = normalize_nef_state(state)
        self.accept()


class IdoClassifierDialog(QDialog):
    def __init__(self, classifier=None, test_orientation="", feature_vector_version="3.0A", parent=None):
        super().__init__(parent)
        self.classifier = _normalized_classifier(classifier) if classifier else None
        self.result_classifier = None
        self.test_orientation = test_orientation
        self.feature_vector_version = feature_vector_version
        self.setWindowTitle("Please Select a Classifier for iDO")
        self.resize(650, 470)
        root = QVBoxLayout(self)
        summary = QLabel(
            f"Test Orientation: {test_orientation or '-'}    "
            f"Feature Vector Version: {feature_vector_version or '-'}"
        )
        root.addWidget(summary)
        actions = QHBoxLayout()
        browse = QPushButton("Browse...")
        browse.clicked.connect(self._browse)
        clear = QPushButton("Clear")
        clear.clicked.connect(self._clear)
        actions.addWidget(browse)
        actions.addWidget(clear)
        actions.addStretch(1)
        root.addLayout(actions)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Classifier Tree", "Value"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(1, QHeaderView.Stretch)
        root.addWidget(self.tree, 1)
        self.status = QLabel("")
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        footer = QHBoxLayout()
        footer.addStretch(1)
        ok = QPushButton("Open")
        ok.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        footer.addWidget(ok)
        footer.addWidget(cancel)
        root.addLayout(footer)
        self._refresh()

    def _browse(self):
        path, _selected = QFileDialog.getOpenFileName(
            self,
            "Please Select a Classifier for iDO",
            "",
            "iDO Classifier Files (*.ido *.json *.xml);;All Files (*)",
        )
        if path:
            self.classifier = classifier_from_path(path, "iDO")
            self._refresh()

    def _clear(self):
        self.classifier = None
        self._refresh()

    def _refresh(self):
        self.tree.clear()
        if not self.classifier:
            self.status.setText("No iDO classifier selected.")
            return
        populate_classifier_tree(self.tree, self.classifier)
        errors = classifier_compatibility_errors(
            self.classifier,
            self.test_orientation,
            self.feature_vector_version,
        )
        self.status.setText("\n".join(errors) if errors else "Classifier settings match the current Test.")

    def _finish(self):
        if not self.classifier:
            QMessageBox.warning(self, "iDO Classifier", "Select an iDO classifier first.")
            return
        errors = classifier_compatibility_errors(
            self.classifier,
            self.test_orientation,
            self.feature_vector_version,
        )
        if errors:
            QMessageBox.warning(self, "iDO Classifier", "\n".join(errors))
            return
        self.result_classifier = deepcopy(self.classifier)
        self.accept()

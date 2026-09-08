from __future__ import annotations

from datetime import datetime
from typing import Optional

from ...config import CONTROL_HEIGHT, DIALOG_HEIGHT_FRACTION, DIALOG_WIDTH_FRACTION
from ...recipe_store import RecipeStore
from ...qt_compat import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QColor,
    QComboBox,
    QDesktopServices,
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
    QPushButton,
    QSize,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    Qt,
    QUrl,
    QVBoxLayout,
    QWidget,
)
from ..show_wafer import ShowWaferPanel


class AddNewPlaceDialog(QDialog):
    def __init__(self, default_name: str, path: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Add New Place")
        self.setFixedSize(430, 260)
        self.place_name = default_name
        self.path = path
        self._build_ui(default_name, path)

    def _build_ui(self, default_name: str, path: str):
        self.setStyleSheet(
            """
            QDialog {
                background: #efede2;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10px;
            }
            QLineEdit {
                background: #ffffff;
                border: 1px solid #77736b;
                min-height: 24px;
            }
            QPushButton {
                background: #e7e5dc;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-height: 24px;
                padding: 2px 14px;
            }
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 18)
        layout.setSpacing(14)

        name_row = QHBoxLayout()
        name_label = QLabel("Name")
        name_label.setFixedWidth(58)
        self.name_edit = QLineEdit(default_name)
        self.name_edit.selectAll()
        name_row.addWidget(name_label)
        name_row.addWidget(self.name_edit, 1)
        layout.addLayout(name_row)

        icon_row = QHBoxLayout()
        icon_label = QLabel("Icon")
        icon_label.setFixedWidth(58)
        icon_preview = QLabel()
        icon_preview.setPixmap(self.style().standardIcon(QStyle.SP_DirIcon).pixmap(48, 48))
        icon_row.addWidget(icon_label)
        icon_row.addWidget(icon_preview)
        icon_row.addWidget(QLabel("v"))
        icon_row.addStretch(1)
        layout.addLayout(icon_row)

        path_label = QLabel(path)
        path_label.setWordWrap(True)
        path_label.setStyleSheet("color: #77736b;")
        layout.addWidget(path_label)
        layout.addStretch(1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        ok = QPushButton("OK")
        ok.setFixedWidth(92)
        ok.clicked.connect(self._accept)
        cancel = QPushButton("Cancel")
        cancel.setFixedWidth(92)
        cancel.clicked.connect(self.reject)
        buttons.addWidget(ok)
        buttons.addSpacing(28)
        buttons.addWidget(cancel)
        buttons.addStretch(1)
        layout.addLayout(buttons)

    def _accept(self):
        name = self.name_edit.text().strip()
        if not name:
            name = self.place_name
        self.place_name = name
        self.accept()


class DeleteRecipeConfirmationDialog(QDialog):
    def __init__(self, recipe_name: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Delete Confirmation")
        self.setFixedSize(430, 190)
        self._build_ui(recipe_name)

    def _build_ui(self, recipe_name: str):
        self.setStyleSheet(
            """
            QDialog {
                background: #efede2;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10px;
            }
            QPushButton {
                background: #e7e5dc;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-height: 24px;
                padding: 2px 16px;
            }
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 18, 26, 18)
        layout.setSpacing(14)

        content = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(self.style().standardIcon(QStyle.SP_TrashIcon).pixmap(64, 64))
        content.addWidget(icon)
        message = QLabel(f'Move selected inspection recipe\n"{recipe_name}"\nto the trash can?')
        message.setAlignment(Qt.AlignCenter)
        content.addWidget(message, 1)
        layout.addLayout(content, 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        delete_now = QPushButton("Delete Now")
        delete_now.setFixedWidth(112)
        delete_now.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.setFixedWidth(92)
        cancel.clicked.connect(self.reject)
        buttons.addWidget(delete_now)
        buttons.addWidget(cancel)
        buttons.addStretch(1)
        layout.addLayout(buttons)


class OpenInspectionRecipeDialog(QDialog):
    TABLE_COLUMNS = [
        ("inspection", "Name"),
        ("last_modified", "Last Modified"),
        ("status", "Status"),
        ("approval", "Approval Code"),
        ("device", "Device"),
        ("date_created", "Date Created"),
        ("step", "Process Step"),
        ("software_version", "Software Version"),
        ("wafer_orientation", "Wafer Orientations"),
        ("auto_learn", "Auto Learn"),
        ("recipe_type", "Recipe Type"),
        ("path", "Path"),
    ]
    DEFAULT_VISIBLE_COLUMN_KEYS = {"inspection", "last_modified", "status", "approval", "device", "step"}

    RECIPES = [
        {
            "inspection": "_180_102",
            "device": "_180",
            "step": "Deep",
            "source": "local",
            "recent": True,
            "last_modified": "Today, 11:50:25 AM",
            "date_created": "2/20/2009 1:45:50 PM",
            "status": "Incomplete",
            "approval": "Engineering",
            "software_version": "9.7.064",
            "wafer_orientation": "180°",
            "auto_learn": "No",
            "state": "Test 1 contains invalid Sample Plan Data. It does not have the minimum number of inspectable die on wafer or carrier.",
            "path": r"D:\DATA\987KInspr0001\Usr\Recipes\300_180\Deep\_180_102",
            "recipe_filter": "All Recipes",
            "recipe_type": "Normal",
        },
        {
            "inspection": "_180",
            "device": "_180",
            "step": "Deep",
            "source": "local",
            "recent": True,
            "last_modified": "1/8/2009 3:38:16 PM",
            "date_created": "1/8/2009 3:38:16 PM",
            "status": "Valid",
            "approval": "Engineering",
            "software_version": "9.7.064",
            "wafer_orientation": "180°",
            "auto_learn": "No",
            "state": "Recipe is valid for setup review.",
            "path": r"D:\DATA\987KInspr0001\Usr\Recipes\300_180\Deep\_180",
            "recipe_filter": "All Recipes",
            "recipe_type": "Normal",
        },
        {
            "inspection": "_180_100",
            "device": "_180",
            "step": "Deep",
            "source": "local",
            "recent": False,
            "last_modified": "2/20/2009 1:45:50 PM",
            "date_created": "2/20/2009 1:45:50 PM",
            "status": "Non Optimal",
            "approval": "Engineering",
            "software_version": "9.7.064",
            "wafer_orientation": "180°",
            "auto_learn": "No",
            "state": "Recipe is non optimal. Alignment data exists, but care area and sample plan geometry should be reviewed before running.",
            "path": r"D:\DATA\987KInspr0001\Usr\Recipes\300_180\Deep\_180_100",
            "recipe_filter": "All Recipes",
            "recipe_type": "Normal",
        },
        {
            "inspection": "Deep",
            "device": "9.4.102",
            "step": "Deep",
            "source": "local",
            "recent": False,
            "last_modified": "Today, 12:00:24 PM",
            "date_created": "Today, 12:00:24 PM",
            "status": "Valid",
            "approval": "Engineering",
            "software_version": "9.7.064",
            "wafer_orientation": "180°",
            "auto_learn": "No",
            "state": "Recipe is valid for setup review.",
            "path": r"D:\DATA\987KInspr0001\Usr\Recipes\9.4.102\Deep\Deep",
            "recipe_filter": "All Recipes",
            "recipe_type": "Normal",
        },
    ]

    def __init__(self, parent: Optional[QWidget] = None, recipe_store: Optional[RecipeStore] = None):
        super().__init__(parent)
        self.recipe_store = recipe_store
        self.recipes = (
            self.recipe_store.list_recipes()
            if self.recipe_store is not None
            else [dict(recipe) for recipe in self.RECIPES]
        )
        self.visible_recipes = []
        self.visible_columns = {key: key in self.DEFAULT_VISIBLE_COLUMN_KEYS for key, title in self.TABLE_COLUMNS}
        self.current_source = "local"
        self.places = [
            {
                "name": "Deep",
                "device": "_180",
                "step": "Deep",
                "path": r"D:\DATA\987KInspr0001\Usr\Recipes\300_180\Deep",
            }
        ]
        self.place_buttons = []
        self.selected_place = None
        self.selected_recipe = None
        self.loading_recipe_details = False
        self.search_active = False
        self.search_text = ""
        self._compact_width = 1180
        self._expanded_width = 1600
        self.setWindowTitle("Open Inspection Recipe")
        self._resize_for_screen(default_width=1180, default_height=800, minimum_width=940, minimum_height=700)
        self._build_ui()
        self._set_wafer_visible(False, resize_window=False)
        self._set_source("local")
        self.table.selectRow(0)
        self._update_details()

    def _resize_for_screen(
        self,
        default_width: int,
        default_height: int,
        minimum_width: int,
        minimum_height: int,
    ):
        screen = QApplication.primaryScreen()
        if not screen:
            self.resize(default_width, default_height)
            self.setMinimumSize(minimum_width, minimum_height)
            return

        available = screen.availableGeometry()
        width = min(default_width, max(minimum_width, int(available.width() * DIALOG_WIDTH_FRACTION)))
        height = min(default_height, max(minimum_height, int(available.height() * DIALOG_HEIGHT_FRACTION)))
        self._compact_width = width
        self._expanded_width = max(width, min(max(width + 740, 1700), int(available.width() * 0.95)))
        self.resize(width, height)
        self.setMinimumSize(minimum_width, minimum_height)
        self.move(
            available.x() + (available.width() - width) // 2,
            available.y() + (available.height() - height) // 2,
        )

    def _build_ui(self):
        self.setStyleSheet(
            """
            QDialog {
                background: #efede2;
                color: #111111;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10px;
            }
            QPushButton {
                background: #e7e5dc;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-height: 24px;
                padding: 2px 7px;
            }
            QPushButton:checked {
                background: #ffffff;
                border: 2px solid #ed1c24;
            }
            QListWidget, QTableWidget, QLineEdit, QComboBox {
                background: #ffffff;
                border: 1px solid #b7b4aa;
                selection-background-color: #b9c9ec;
                selection-color: #111111;
                min-height: 24px;
            }
            QTableWidget::item {
                padding: 2px;
            }
            QLabel[section="true"] {
                font-weight: 600;
            }
            """
        )

        main = QVBoxLayout(self)
        main.setContentsMargins(8, 8, 8, 8)
        main.setSpacing(6)
        main.addWidget(self._top_commands())

        center = QHBoxLayout()
        center.setSpacing(8)
        center.addWidget(self._recipe_sources())
        center.addWidget(self._browser_area(), 1)
        self.wafer_panel = ShowWaferPanel()
        center.addWidget(self.wafer_panel)
        main.addLayout(center, 1)
        main.addWidget(self._bottom_area())

    def _top_commands(self) -> QWidget:
        bar = QFrame()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        title = QLabel("Recipes")
        title.setStyleSheet("font-weight: 700;")
        title.setPixmap(self.style().standardIcon(QStyle.SP_FileDialogListView).pixmap(22, 22))
        layout.addWidget(title)

        label = QLabel("Recipes")
        label.setStyleSheet("font-weight: 700;")
        layout.addWidget(label)

        self.search_button = QPushButton("Search")
        self.search_button.setIcon(self.style().standardIcon(QStyle.SP_FileDialogContentsView))
        self.search_button.clicked.connect(self._show_search_panel)
        layout.addWidget(self.search_button)

        self.delete_button = QPushButton("Delete")
        self.delete_button.setIcon(self.style().standardIcon(QStyle.SP_TrashIcon))
        self.delete_button.setEnabled(False)
        self.delete_button.clicked.connect(self._delete_current_recipe)
        layout.addWidget(self.delete_button)
        layout.addStretch(1)
        return bar

    def _recipe_sources(self) -> QWidget:
        panel = QFrame()
        panel.setFixedWidth(112)
        panel.setStyleSheet("QFrame { background: #f6f4e8; border: 1px solid #c4c0b5; }")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 10, 8, 10)
        layout.setSpacing(8)

        self.local_button = QPushButton("Local\nRecipes")
        self.local_button.setIcon(self.style().standardIcon(QStyle.SP_DirIcon))
        self.local_button.setIconSize(QSize(32, 32))
        self.local_button.setMinimumHeight(76)
        self.local_button.setCheckable(True)
        self.local_button.setChecked(True)
        self.local_button.clicked.connect(lambda: self._set_source("local"))
        layout.addWidget(self.local_button)

        self.recent_button = QPushButton("Recent\nItems")
        self.recent_button.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        self.recent_button.setIconSize(QSize(28, 28))
        self.recent_button.setMinimumHeight(76)
        self.recent_button.setCheckable(True)
        self.recent_button.clicked.connect(lambda: self._set_source("recent"))
        layout.addWidget(self.recent_button)

        self.places_layout = QVBoxLayout()
        self.places_layout.setContentsMargins(0, 0, 0, 0)
        self.places_layout.setSpacing(8)
        layout.addLayout(self.places_layout)
        self._rebuild_place_buttons()

        layout.addStretch(1)
        add_remove = QHBoxLayout()
        self.add_button = QPushButton("Add")
        self.add_button.clicked.connect(self._add_new_place)
        add_remove.addWidget(self.add_button)
        self.remove_place_button = QPushButton("Remove")
        self.remove_place_button.setEnabled(False)
        self.remove_place_button.clicked.connect(self._remove_selected_place)
        add_remove.addWidget(self.remove_place_button)
        layout.addLayout(add_remove)

        help_button = QPushButton("?")
        help_button.setFixedSize(28, 28)
        help_button.setStyleSheet(
            "border-radius: 13px; background: #2f5dd2; color: white; font-weight: 700;"
        )
        help_button.clicked.connect(self._show_recipe_help)
        layout.addWidget(help_button, alignment=Qt.AlignLeft)
        return panel

    def _show_recipe_help(self):
        QMessageBox.information(
            self,
            "Open Inspection Recipe Help",
            "Choose Local Recipes or Recent Items, select a Device and Process Step, then select a recipe. "
            "Use Search, Recipe Filter, or the header-column menu to narrow the list.",
        )

    def _browser_area(self) -> QWidget:
        panel = QFrame()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.search_panel = self._search_panel()
        self.search_panel.setVisible(False)
        layout.addWidget(self.search_panel)

        top = QHBoxLayout()
        device_box = QVBoxLayout()
        device_label = QLabel("Device")
        device_label.setProperty("section", True)
        self.device_list = QListWidget()
        self.device_list.setFixedHeight(92)
        self.device_list.currentRowChanged.connect(self._device_changed)
        device_box.addWidget(device_label)
        device_box.addWidget(self.device_list)
        top.addLayout(device_box, 1)

        step_box = QVBoxLayout()
        step_label = QLabel("Step")
        step_label.setProperty("section", True)
        self.step_list = QListWidget()
        self.step_list.setFixedHeight(92)
        self.step_list.currentRowChanged.connect(self._step_changed)
        step_box.addWidget(step_label)
        step_box.addWidget(self.step_list)
        top.addLayout(step_box, 1)
        layout.addLayout(top)

        inspection_header = QHBoxLayout()
        inspection_label = QLabel("Inspections")
        inspection_label.setProperty("section", True)
        inspection_header.addWidget(inspection_label)
        inspection_header.addStretch(1)
        self.configure_columns_button = QPushButton(">")
        self.configure_columns_button.setFixedSize(24, 24)
        self.configure_columns_button.setToolTip("Configure header columns")
        self.configure_columns_button.clicked.connect(self._configure_header_columns)
        inspection_header.addWidget(self.configure_columns_button)
        layout.addLayout(inspection_header)

        self.table = QTableWidget(0, len(self.TABLE_COLUMNS))
        self.table.setHorizontalHeaderLabels([title for key, title in self.TABLE_COLUMNS])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_recipe_operations_menu)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for column in range(1, len(self.TABLE_COLUMNS)):
            self.table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setDefaultSectionSize(24)
        self.table.itemSelectionChanged.connect(self._update_details)
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table, 1)

        self.footer_label = QLabel()
        self.footer_label.setStyleSheet("background: #f1f0e8; border: 1px solid #c4c0b5; padding: 2px;")
        layout.addWidget(self.footer_label)
        self._apply_header_columns()
        return panel

    def _search_panel(self) -> QWidget:
        panel = QFrame()
        panel.setStyleSheet("QFrame { background: #efede2; border-bottom: 1px solid #c4c0b5; }")
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(8)
        icon = QLabel()
        icon.setPixmap(self.style().standardIcon(QStyle.SP_FileDialogContentsView).pixmap(28, 28))
        layout.addWidget(icon)
        layout.addWidget(QLabel("Find"))
        self.find_edit = QLineEdit()
        self.find_edit.setMinimumWidth(360)
        self.find_edit.textChanged.connect(self._find_text_changed)
        layout.addWidget(self.find_edit, 1)
        self.clear_find_button = QPushButton("Clear")
        self.clear_find_button.setIcon(self.style().standardIcon(QStyle.SP_DialogResetButton))
        self.clear_find_button.clicked.connect(self._clear_find_text)
        layout.addWidget(self.clear_find_button)
        close = QPushButton("x")
        close.setFixedSize(24, 24)
        close.setStyleSheet("background: #c93b31; color: #ffffff; font-weight: 700; padding: 0;")
        close.clicked.connect(self._hide_search_panel)
        layout.addWidget(close)
        return panel

    def _bottom_area(self) -> QWidget:
        panel = QFrame()
        layout = QGridLayout(panel)
        layout.setContentsMargins(118, 8, 8, 0)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(4)

        self.inspection_edit = self._editable_line()
        self.device_edit = self._editable_line()
        self.step_edit = self._editable_line()
        self.state_edit = self._editable_line()
        self.path_edit = self._editable_line()
        for line in [self.inspection_edit, self.device_edit, self.step_edit, self.state_edit, self.path_edit]:
            line.textEdited.connect(self._mark_current_recipe_dirty)

        layout.addWidget(QLabel("Inspection"), 0, 0)
        layout.addWidget(self.inspection_edit, 0, 1)
        layout.addWidget(QLabel("Recipe Filter"), 0, 2)
        self.recipe_filter = QComboBox()
        self.recipe_filter.addItems(["All Recipes", "Valid Recipes", "Invalid Recipes"])
        self.recipe_filter.setEditable(True)
        self.recipe_filter.currentTextChanged.connect(self._recipe_filter_changed)
        filter_row = QHBoxLayout()
        filter_row.setSpacing(5)
        filter_row.addWidget(self.recipe_filter, 1)
        self.clear_recipe_filter_button = QPushButton("Clear")
        self.clear_recipe_filter_button.setFixedWidth(58)
        self.clear_recipe_filter_button.setEnabled(False)
        self.clear_recipe_filter_button.clicked.connect(self._clear_recipe_filter)
        filter_row.addWidget(self.clear_recipe_filter_button)
        layout.addLayout(filter_row, 0, 3)

        layout.addWidget(QLabel("Device Id"), 1, 0)
        layout.addWidget(self.device_edit, 1, 1)
        layout.addWidget(QLabel("Recipe Type"), 1, 2)
        self.recipe_type = QComboBox()
        self.recipe_type.addItems(["Normal"])
        self.recipe_type.setEditable(True)
        layout.addWidget(self.recipe_type, 1, 3)

        layout.addWidget(QLabel("Step Id"), 2, 0)
        layout.addWidget(self.step_edit, 2, 1)
        self.production_only = QCheckBox("Show Production Recipes Only")
        self.production_only.toggled.connect(lambda checked: self._populate_recipes())
        layout.addWidget(self.production_only, 2, 2, 1, 2)

        layout.addWidget(QLabel("State"), 3, 0)
        state_row = QHBoxLayout()
        state_row.setSpacing(6)
        state_row.addWidget(self.state_edit, 1)
        self.more_status_button = QPushButton("More")
        self.more_status_button.setFixedWidth(58)
        self.more_status_button.clicked.connect(self._show_recipe_status_more)
        state_row.addWidget(self.more_status_button)
        layout.addLayout(state_row, 3, 1, 1, 3)

        path_label_row = QHBoxLayout()
        path_label_row.setSpacing(3)
        self.path_open_button = QPushButton("")
        self.path_open_button.setIcon(self.style().standardIcon(QStyle.SP_FileDialogContentsView))
        self.path_open_button.setFixedSize(22, 22)
        self.path_open_button.setToolTip("Open selected recipe path")
        self.path_open_button.setEnabled(False)
        self.path_open_button.setVisible(False)
        self.path_open_button.clicked.connect(self._show_current_recipe_path)
        path_label_row.addWidget(self.path_open_button)
        path_label_row.addWidget(QLabel("Path"))
        path_label_row.addStretch(1)
        layout.addLayout(path_label_row, 4, 0)
        layout.addWidget(self.path_edit, 4, 1, 1, 3)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        open_button = QPushButton("Open")
        open_button.setFixedSize(86, 28)
        open_button.clicked.connect(self._open_selected)
        cancel_button = QPushButton("Cancel")
        cancel_button.setFixedSize(86, 28)
        cancel_button.setIcon(self.style().standardIcon(QStyle.SP_DialogCancelButton))
        cancel_button.clicked.connect(self.reject)
        button_row.addWidget(open_button)
        button_row.addWidget(cancel_button)
        button_row.addStretch(1)
        layout.addLayout(button_row, 5, 0, 1, 4)

        wafer_controls = QHBoxLayout()
        wafer_controls.setSpacing(5)
        self.show_wafer_button = QPushButton("Show Wafer  >>")
        self.show_wafer_button.setFixedWidth(112)
        self.show_wafer_button.clicked.connect(self._toggle_wafer_panel)
        wafer_controls.addWidget(self.show_wafer_button)
        self.load_port_label = QLabel("Show Load Ports:")
        wafer_controls.addWidget(self.load_port_label)
        self.load_port_buttons = []
        for text, checked in [("1", False), ("2", False), ("3", True)]:
            button = QPushButton(text)
            button.setCheckable(True)
            button.setChecked(checked)
            button.setFixedSize(28, 28)
            button.setToolTip(f"Display {text} load port{'s' if text != '1' else ''}")
            button.clicked.connect(lambda checked=False, value=text: self._set_load_port(value))
            wafer_controls.addWidget(button)
            self.load_port_buttons.append(button)
        layout.addLayout(wafer_controls, 5, 4, 1, 1)
        return panel

    def _editable_line(self) -> QLineEdit:
        line = QLineEdit()
        line.setMinimumHeight(CONTROL_HEIGHT)
        return line

    def _set_source(self, source: str):
        self.current_source = source
        self.local_button.setChecked(source == "local")
        self.recent_button.setChecked(source == "recent")
        self._set_place_selection(None)
        self._populate_device_list()

    def _source_recipes(self):
        if self.current_source == "recent":
            return [recipe for recipe in self.recipes if recipe.get("recent")]
        return [recipe for recipe in self.recipes if recipe.get("source") == "local"]

    def _populate_device_list(self):
        current = self.device_list.currentItem().text() if self.device_list.currentItem() else ""
        devices = []
        for recipe in self._source_recipes():
            if recipe["device"] not in devices:
                devices.append(recipe["device"])
        self.device_list.blockSignals(True)
        self.device_list.clear()
        self.device_list.addItems(devices)
        row = devices.index(current) if current in devices else 0
        self.device_list.setCurrentRow(row if devices else -1)
        self.device_list.blockSignals(False)
        self._populate_step_list()

    def _populate_step_list(self):
        current = self.step_list.currentItem().text() if self.step_list.currentItem() else ""
        device = self._current_device()
        steps = []
        for recipe in self._source_recipes():
            if recipe["device"] == device and recipe["step"] not in steps:
                steps.append(recipe["step"])
        self.step_list.blockSignals(True)
        self.step_list.clear()
        self.step_list.addItems(steps)
        row = steps.index(current) if current in steps else 0
        self.step_list.setCurrentRow(row if steps else -1)
        self.step_list.blockSignals(False)
        self._populate_recipes()

    def _populate_recipes(self):
        device = self._current_device()
        step = self._current_step()
        if self.search_active and self.search_text:
            needle = self.search_text.lower()
            recipes = [
                recipe
                for recipe in self._source_recipes()
                if needle in recipe.get("inspection", "").lower()
                or needle in recipe.get("device", "").lower()
                or needle in recipe.get("step", "").lower()
                or needle in recipe.get("path", "").lower()
            ]
        else:
            recipes = [
                recipe
                for recipe in self._source_recipes()
                if recipe["device"] == device and recipe["step"] == step
            ]
        recipe_filter = self.recipe_filter.currentText() if hasattr(self, "recipe_filter") else "All Recipes"
        if recipe_filter == "Valid Recipes":
            recipes = [recipe for recipe in recipes if recipe["status"] == "Valid"]
        elif recipe_filter == "Invalid Recipes":
            recipes = [recipe for recipe in recipes if recipe["status"] != "Valid"]
        if self.production_only.isChecked():
            recipes = [recipe for recipe in recipes if recipe.get("production")]
        self.visible_recipes = recipes
        sorting_enabled = self.table.isSortingEnabled()
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for recipe in self.visible_recipes:
            self._append_recipe_row(recipe)
        self.table.setSortingEnabled(sorting_enabled)
        self._update_footer()
        if self.visible_recipes:
            self.table.selectRow(0)
            self._update_details()
        else:
            self._clear_details()

    def _append_recipe_row(self, recipe):
        row = self.table.rowCount()
        self.table.insertRow(row)
        for column, (key, title) in enumerate(self.TABLE_COLUMNS):
            value = recipe.get(key, "")
            item = QTableWidgetItem(value)
            if column == 0:
                item.setData(Qt.UserRole, recipe)
            if key == "status":
                item.setForeground(QColor("#00a020" if value == "Valid" else "#ed1c24"))
            self.table.setItem(row, column, item)
        self._apply_header_columns()

    def _update_footer(self):
        if self.search_active and self.search_text:
            self.footer_label.setText(f"{len(self.visible_recipes)} Items    Search: {self.search_text}")
        else:
            self.footer_label.setText(f"{len(self.visible_recipes)} Items    Wafer Orientation: 180 deg")

    def _show_search_panel(self):
        self.search_active = True
        self.search_panel.setVisible(True)
        self.find_edit.setFocus()
        self.find_edit.selectAll()
        self._populate_recipes()

    def _hide_search_panel(self):
        self.search_active = False
        self.search_text = ""
        self.find_edit.blockSignals(True)
        self.find_edit.clear()
        self.find_edit.blockSignals(False)
        self.search_panel.setVisible(False)
        self._populate_recipes()

    def _find_text_changed(self, text: str):
        self.search_text = text.strip()
        self.search_active = True
        self._populate_recipes()

    def _clear_find_text(self):
        self.find_edit.clear()

    def _current_recipe(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        name_item = self.table.item(row, 0)
        recipe = name_item.data(Qt.UserRole) if name_item is not None else None
        return recipe if isinstance(recipe, dict) else None

    def _update_details(self):
        recipe = self._current_recipe()
        if not recipe:
            return
        self.loading_recipe_details = True
        self.inspection_edit.setText(recipe["inspection"])
        self.device_edit.setText(recipe["device"])
        self.step_edit.setText(recipe["step"])
        self.state_edit.setText(recipe["state"])
        self.state_edit.setToolTip(recipe["state"])
        self.path_edit.setText(recipe["path"])
        self.recipe_type.setCurrentText(recipe["recipe_type"])
        self.loading_recipe_details = False
        invalid = recipe.get("status") != "Valid"
        self.more_status_button.setVisible(invalid)
        self.more_status_button.setEnabled(invalid)
        self.delete_button.setEnabled(True)
        self.path_open_button.setEnabled(True)
        self.path_open_button.setVisible(True)
        self.wafer_panel.update_recipe(recipe)

    def _clear_details(self):
        self.inspection_edit.clear()
        self.device_edit.clear()
        self.step_edit.clear()
        self.state_edit.clear()
        self.path_edit.clear()
        self.more_status_button.setVisible(False)
        self.delete_button.setEnabled(False)
        self.path_open_button.setEnabled(False)
        self.path_open_button.setVisible(False)

    def _recipe_filter_changed(self, text: str):
        self.clear_recipe_filter_button.setEnabled(text != "All Recipes")
        self._populate_recipes()

    def _clear_recipe_filter(self):
        self.recipe_filter.setCurrentText("All Recipes")
        self.production_only.setChecked(False)
        self.clear_recipe_filter_button.setEnabled(False)
        self._populate_recipes()

    def _mark_current_recipe_dirty(self):
        if self.loading_recipe_details:
            return
        recipe = self._current_recipe()
        if recipe:
            recipe["dirty"] = True

    def _show_recipe_status_more(self):
        recipe = self._current_recipe()
        if not recipe:
            return
        detail = (
            f"Inspection: {recipe.get('inspection', '')}\n"
            f"Device ID: {recipe.get('device', '')}\n"
            f"Step ID: {recipe.get('step', '')}\n"
            f"Last Modified: {recipe.get('last_modified', '')}\n"
            f"Status: {recipe.get('status', '')}\n"
            f"Approval Code: {recipe.get('approval', '')}\n"
            f"Recipe Type: {recipe.get('recipe_type', '')}\n\n"
            f"Recipe Status:\n{recipe.get('state', '')}\n\n"
            f"Path:\n{recipe.get('path', '')}"
        )
        QMessageBox.information(self, "Recipe Status", detail)

    def _open_selected(self):
        recipe = self._recipe_from_inputs(base=self._current_recipe())
        recipe["recent"] = True
        if self.recipe_store is not None and recipe.get("id"):
            self.recipe_store.set_recent(recipe["id"], True)
        self.selected_recipe = recipe
        self.accept()

    def _show_recipe_operations_menu(self, position):
        index = self.table.indexAt(position)
        if index.isValid():
            self.table.selectRow(index.row())
        recipe = self._current_recipe()

        menu = QMenu(self)
        open_recipe = menu.addAction("Open Recipe\tEnter")
        save_recipe = None
        if recipe and recipe.get("dirty", False):
            save_recipe = menu.addAction("Save Recipe")
        open_explorer = menu.addAction("Open in Explorer")
        refresh = menu.addAction("Refresh\tF5")
        menu.addSeparator()
        clear_recent = None
        if self.current_source == "recent" and recipe:
            clear_recent = menu.addAction("Clear Recent Items")
        delete_recipe = menu.addAction("Delete\tDel")

        has_recipe = recipe is not None
        open_recipe.setEnabled(has_recipe)
        open_explorer.setEnabled(has_recipe)
        delete_recipe.setEnabled(has_recipe)

        global_position = self.table.viewport().mapToGlobal(position)
        action = menu.exec(global_position) if hasattr(menu, "exec") else menu.exec_(global_position)
        if action == open_recipe:
            self._open_selected()
        elif save_recipe is not None and action == save_recipe:
            self._save_current_recipe()
        elif action == open_explorer:
            self._show_current_recipe_path()
        elif action == refresh:
            self._populate_device_list()
        elif clear_recent is not None and action == clear_recent:
            self._clear_recent_items()
        elif action == delete_recipe:
            self._delete_current_recipe()

    def _configure_header_columns(self):
        menu = QMenu(self)
        reset = menu.addAction("Reset Columns")
        menu.addSeparator()
        action_by_key = {}
        for key, title in self.TABLE_COLUMNS:
            if key == "inspection":
                continue
            action = menu.addAction(title)
            action.setCheckable(True)
            action.setChecked(self.visible_columns.get(key, False))
            action_by_key[action] = key
        button = self.configure_columns_button
        global_position = button.mapToGlobal(button.rect().bottomLeft())
        action = menu.exec(global_position) if hasattr(menu, "exec") else menu.exec_(global_position)
        if not action:
            return
        if action == reset:
            self.visible_columns = {key: key in self.DEFAULT_VISIBLE_COLUMN_KEYS for key, title in self.TABLE_COLUMNS}
        elif action in action_by_key:
            key = action_by_key[action]
            self._set_column_visible(key, action.isChecked())
        self.visible_columns["inspection"] = True
        self._apply_header_columns()

    def _set_column_visible(self, key: str, visible: bool):
        if key == "inspection":
            self.visible_columns[key] = True
            return
        if key in self.visible_columns:
            self.visible_columns[key] = bool(visible)

    def _apply_header_columns(self):
        if not hasattr(self, "table"):
            return
        for column, (key, title) in enumerate(self.TABLE_COLUMNS):
            self.table.setColumnHidden(column, not self.visible_columns.get(key, True))

    def _save_current_recipe(self):
        recipe = self._current_recipe()
        if not recipe:
            return
        saved = self._recipe_from_inputs(base=recipe)
        saved["dirty"] = False
        saved["last_modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self.recipe_store is not None:
            saved = self.recipe_store.save_recipe(saved)
        recipe.clear()
        recipe.update(saved)
        self._populate_recipes()
        self.state_edit.setText("Recipe saved.")

    def _show_current_recipe_path(self):
        recipe = self._current_recipe()
        if recipe:
            path = recipe["path"]
            folder_path = path.rsplit("\\", 1)[0] if "\\" in path else path
            self.path_edit.setText(path)
            opened = QDesktopServices.openUrl(QUrl.fromLocalFile(folder_path))
            if opened:
                self.state_edit.setText(f"Recipe folder opened: {folder_path}")
            else:
                self.state_edit.setText(f"Recipe folder path is displayed: {folder_path}")

    def _clear_recent_items(self):
        for recipe in self.recipes:
            recipe["recent"] = False
        if self.recipe_store is not None:
            self.recipe_store.clear_recent()
        self._populate_device_list()

    def _delete_current_recipe(self):
        recipe = self._current_recipe()
        if not recipe:
            return
        dialog = DeleteRecipeConfirmationDialog(recipe.get("inspection", ""), self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result != QDialog.Accepted:
            return
        if self.recipe_store is not None and recipe.get("id"):
            self.recipe_store.delete_recipe(recipe["id"])
        self.recipes.remove(recipe)
        self._populate_device_list()

    def _add_new_place(self):
        device = self._current_device()
        step = self._current_step()
        if not device and self.device_edit.text().strip():
            device = self.device_edit.text().strip()
        if not step and self.step_edit.text().strip():
            step = self.step_edit.text().strip()
        if not device and not step:
            return
        default_name = step or device
        path = self._place_path_for(device, step)
        dialog = AddNewPlaceDialog(default_name, path, self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            place = {
                "name": dialog.place_name,
                "device": device,
                "step": step,
                "path": path,
            }
            self.places.append(place)
            self._rebuild_place_buttons()
            self._select_place(place)

    def _place_path_for(self, device: str, step: str) -> str:
        for recipe in self.recipes:
            if recipe["device"] == device and recipe["step"] == step:
                path = recipe.get("path", "")
                if "\\" in path:
                    return path.rsplit("\\", 1)[0]
                return path
        return rf"D:\DATA\987KInspr0001\Usr\Recipes\{device}\{step}"

    def _rebuild_place_buttons(self):
        while self.places_layout.count():
            item = self.places_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.place_buttons = []
        for place in self.places:
            button = QPushButton(place["name"])
            button.setIcon(self.style().standardIcon(QStyle.SP_DirIcon))
            button.setIconSize(QSize(32, 32))
            button.setMinimumHeight(72)
            button.setCheckable(True)
            button.setToolTip(place["path"])
            button.clicked.connect(lambda checked=False, selected=place: self._select_place(selected))
            self.places_layout.addWidget(button)
            self.place_buttons.append((button, place))

    def _select_place(self, place):
        self.current_source = "local"
        self.local_button.setChecked(False)
        self.recent_button.setChecked(False)
        self._set_place_selection(place)
        self._populate_device_list()
        self._select_device_step(place["device"], place["step"])

    def _set_place_selection(self, selected_place):
        self.selected_place = selected_place
        for button, place in self.place_buttons:
            button.setChecked(place is selected_place)
        self.remove_place_button.setEnabled(selected_place is not None)

    def _remove_selected_place(self):
        if self.selected_place in self.places:
            self.places.remove(self.selected_place)
        self._set_place_selection(None)
        self._rebuild_place_buttons()

    def _add_input_recipe(self):
        recipe = self._recipe_from_inputs()
        if self.recipe_store is not None:
            recipe = self.recipe_store.save_recipe(recipe, event="Create Recipe")
        self.recipes.append(recipe)
        self._populate_device_list()
        self._select_device_step(recipe["device"], recipe["step"])

    def _recipe_from_inputs(self, base=None):
        recipe = dict(base or {})
        state = self.state_edit.text().strip()
        status = recipe.get("status", "")
        if not status:
            status = "Valid" if "valid" in state.lower() and "invalid" not in state.lower() else "Incomplete"
        recipe.update(
            {
                "inspection": self.inspection_edit.text().strip(),
                "device": self.device_edit.text().strip(),
                "step": self.step_edit.text().strip(),
                "source": recipe.get("source") or "local",
                "recent": recipe.get("recent", True),
                "last_modified": recipe.get("last_modified") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "date_created": recipe.get("date_created") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": status,
                "approval": recipe.get("approval") or "Engineering",
                "software_version": recipe.get("software_version") or "9.7.064",
                "wafer_orientation": recipe.get("wafer_orientation") or "180°",
                "auto_learn": recipe.get("auto_learn") or "No",
                "state": state,
                "path": self.path_edit.text().strip(),
                "recipe_filter": self.recipe_filter.currentText().strip(),
                "recipe_type": self.recipe_type.currentText().strip(),
            }
        )
        return recipe

    def _update_device_step_lists(self, recipe):
        device = recipe["device"]
        step = recipe["step"]
        if device and not self.device_list.findItems(device, Qt.MatchExactly):
            self.device_list.addItem(device)
        if step and not self.step_list.findItems(step, Qt.MatchExactly):
            self.step_list.addItem(step)

    def _current_device(self):
        item = self.device_list.currentItem()
        return item.text() if item else ""

    def _current_step(self):
        item = self.step_list.currentItem()
        return item.text() if item else ""

    def _device_changed(self):
        self._populate_step_list()

    def _step_changed(self):
        self._populate_recipes()

    def _select_step_by_name(self, step_name: str):
        matches = self.step_list.findItems(step_name, Qt.MatchExactly)
        if matches:
            self.step_list.setCurrentItem(matches[0])

    def _select_device_step(self, device: str, step: str):
        device_matches = self.device_list.findItems(device, Qt.MatchExactly)
        if device_matches:
            self.device_list.setCurrentItem(device_matches[0])
        step_matches = self.step_list.findItems(step, Qt.MatchExactly)
        if step_matches:
            self.step_list.setCurrentItem(step_matches[0])

    def _toggle_wafer_panel(self):
        self._set_wafer_visible(not self.wafer_panel.isVisible())

    def _set_wafer_visible(self, visible: bool, *, resize_window: bool = True):
        self.wafer_panel.setVisible(visible)
        self.show_wafer_button.setText("Hide Wafer  <<" if visible else "Show Wafer  >>")
        self.load_port_label.setVisible(visible)
        for button in self.load_port_buttons:
            button.setVisible(visible)
        if visible:
            self.wafer_panel.set_visible_ports(self._current_load_port_choice())
        if resize_window:
            self._resize_for_wafer_panel(visible)

    def _resize_for_wafer_panel(self, visible: bool):
        target_width = self._expanded_width if visible else self._compact_width
        self.resize(target_width, self.height())

        screen = QApplication.primaryScreen()
        if not screen:
            return
        available = screen.availableGeometry()
        right_edge = self.x() + self.width()
        max_right = available.x() + available.width()
        if right_edge > max_right:
            self.move(max(available.x(), max_right - self.width()), self.y())

    def _set_load_port(self, selected_text: str):
        for button in self.load_port_buttons:
            button.setChecked(button.text() == selected_text)
        self.wafer_panel.set_visible_ports(selected_text)

    def _current_load_port_choice(self) -> str:
        for button in self.load_port_buttons:
            if button.isChecked():
                return button.text()
        return "3"

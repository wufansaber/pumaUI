from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

from .config import MAIN_WINDOW_FRACTION
from .demo_content import (
    ensure_demo_recipe,
    ensure_demo_review_results,
    ensure_virtual_figure_recipe,
    prepare_loaded_recipe,
)
from .modules.configure_overview import DEFAULT_VISIBLE_RECIPE_PARAMETERS, SelectVisibleRecipeParametersDialog
from .modules.defect_data import SelectDefectDataDialog
from .modules.design_based_binning import DBBSetupDialog, DBBViewDialog, DBCSetupDialog, DesignRegistrationDialog, normalized_dbb_state
from .modules.image_display import AdvancedOpticsDialog, ImageDisplayWindow
from .modules.inspection_matching import InspectionMatchingUtilityDialog
from .modules.inspection_tests import SamplePlanColorsDialog, TestsSetupDialog
from .modules.lot_plan import LotPlanDialog
from .modules.results_review import (
    KlarfMatchDialog,
    ReviewWorkspace,
    SelectLotResultsDialog,
    import_klarf_text,
)
from .modules.run_control import (
    InspectionJobQueueDialog,
    OpenLotResultRunLogDialog,
    PrintOnRunDialog,
    RunLogDialog,
    RunOneWaferDialog,
    RunStatusDialog,
    job_execution_plan,
)
from .modules.sizing import SizingRecipeDialog, SizingSetupTool
from .modules.system_status import (
    AlarmCenterDialog,
    ClickAndMarkConfigurationDialog,
    CommunicationStatusDialog,
    DataTransferQueueDialog,
    DeleteInspectionsDialog,
    EquipmentConstantsDialog,
    E84RealTimeSignalDialog,
    ErrorMessageDialog,
    FileAdministrationDialog,
    InitializeSubsystemsDialog,
    LotSummaryDialog,
    PreventiveMaintenanceDialog,
    RenameLotDialog,
    SendLotsDialog,
    SoftwareOptionsDialog,
    SystemLogDialog,
    TransferConfigurationDialog,
    BackupArchiveRestoreDialog,
    CarrierManagementDialog,
    ControlJobManagementDialog,
    DiskAdminDialog,
    ERCManagerDialog,
    LoadPortIndicatorDialog,
    LogSettingsDialog,
    SecsOperationsDialog,
    SignalTowerDialog,
    SubstrateTrackingDialog,
    ToolsConfigurationDialog,
    UserAdministrationDialog,
    UserPreferencesDialog,
    control_job_access,
    normalized_system_admin_state,
    normalized_communication_status,
    normalized_data_transfer,
)
from .modules.wafer_post_processing import WaferPostProcessingDialog
from .modules.recipe_lifecycle import (
    ExtractComponentDialog,
    InspectionPropertiesDialog,
    InsertComponentDialog,
    RecipeGenerationDialog,
    RecipeHistoryDialog,
    RecipeImportDialog,
    SaveInspectionDialog,
)
from .modules.select_inspection import OpenInspectionRecipeDialog
from .modules.wafer_alignment import AlignmentMenuDialog
from .modules.wafer_handling import WaferHandlingDialog
from .modules.wafer_map import WaferMapSetupDialog
from .modules.wafer_properties import WaferPropertiesDialog
from .modules.xp_offline import (
    CAGEditorDialog,
    GDS2CAConverterDialog,
    ManualAssistDialog,
    RDSManagerDialog,
    RecipeComparatorDialog,
    RegistrationSiteLibraryDialog,
    XPRecipeGeneratorDialog,
    apply_component_to_recipe,
    normalized_xp_state,
)
from .recipe_store import RecipeStore
from .qt_compat import (
    QAction,
    QApplication,
    QColor,
    QComboBox,
    QDoubleSpinBox,
    QDialog,
    QDesktopServices,
    QEasingCurve,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QIcon,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPrintDialog,
    QPrinter,
    QPropertyAnimation,
    QPushButton,
    QScrollArea,
    QSize,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QStatusBar,
    QStyle,
    QToolBar,
    QTimer,
    Qt,
    QUrl,
    QVBoxLayout,
    QWidget,
)
from .widgets import (
    ActionLabel,
    ClassicButton,
    DieCornerMap,
    EmptyScrollTrack,
    OverviewWaferMap,
    SectionBox,
    StatusDot,
    SubmenuButtonRow,
    wafer_disk_with_notch,
)


class DieCornerImage(QWidget):
    def __init__(self, size: int, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#5f8790"))
        painter.setPen(QPen(QColor("#527780"), 1))
        for offset in range(0, self.width(), 7):
            painter.drawLine(offset, 0, offset + self.height(), self.height())
        corner_x = int(self.width() * 0.48)
        corner_y = int(self.height() * 0.49)
        painter.setBrush(QColor("#c8c2e8"))
        painter.setPen(QPen(QColor("#8d85bb"), 2))
        painter.drawRect(corner_x, corner_y, self.width(), self.height())
        painter.setPen(QPen(QColor("#42505f"), 3))
        painter.drawLine(corner_x, corner_y, corner_x, self.height())
        painter.drawLine(corner_x, corner_y, self.width(), corner_y)
        painter.setPen(QPen(QColor("#00a040"), 2))
        painter.drawLine(corner_x - 28, corner_y, corner_x + 28, corner_y)
        painter.drawLine(corner_x, corner_y - 28, corner_x, corner_y + 28)
        painter.setPen(QPen(QColor("#b8b8b8"), 2))
        painter.drawEllipse(self.width() - 18, self.height() - 18, 8, 8)
        painter.drawLine(self.width() - 12, self.height() - 12, self.width() - 6, self.height() - 6)


class DieCornerZoomDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Die Corner Image")
        self.setFixedSize(820, 570)
        self.setStyleSheet(
            """
            QDialog {
                background: #ffffff;
                color: #111111;
                font-family: Arial, Helvetica, sans-serif;
            }
            QLabel {
                font-size: 22px;
                font-weight: 700;
            }
            QPushButton#closeButton {
                background: #c93b31;
                border: 1px solid #ffffff;
                color: #ffffff;
                font-size: 18px;
                font-weight: 700;
                padding: 0;
            }
            """
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 20, 18, 18)
        root.setSpacing(10)

        header = QHBoxLayout()
        low_title = QLabel("Low Mag Image")
        high_title = QLabel("High Mag Image")
        header.addWidget(low_title)
        header.addStretch(1)
        header.addWidget(high_title)
        header.addSpacing(150)
        root.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(54)
        body.addWidget(DieCornerImage(255), alignment=Qt.AlignBottom)

        high_frame = QFrame()
        high_frame.setFixedSize(456, 456)
        high_layout = QVBoxLayout(high_frame)
        high_layout.setContentsMargins(0, 0, 0, 0)
        close_row = QHBoxLayout()
        close_row.addStretch(1)
        close_button = QPushButton("x")
        close_button.setObjectName("closeButton")
        close_button.setFixedSize(28, 28)
        close_button.clicked.connect(self.accept)
        close_row.addWidget(close_button)
        high_layout.addLayout(close_row)
        image_row = QHBoxLayout()
        image_row.setContentsMargins(0, 0, 0, 0)
        image_row.addWidget(DieCornerImage(440))
        high_layout.addLayout(image_row)
        body.addWidget(high_frame, alignment=Qt.AlignTop)
        root.addLayout(body, 1)


class WaferMapImage(QWidget):
    def __init__(self, size: int = 460, blank: bool = False, parent=None):
        super().__init__(parent)
        self.blank = blank
        self.setFixedSize(size, size)

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#ffffff"))
        rect = self.rect().adjusted(16, 16, -26, -26)
        side = min(rect.width(), rect.height())
        x = rect.center().x() - side // 2
        y = rect.center().y() - side // 2
        painter.setBrush(QColor("#ffffff" if self.blank else "#f7f7f7"))
        painter.setPen(QPen(QColor("#c8c8c8" if self.blank else "#b0b0b0"), 2))
        painter.drawEllipse(x, y, side, side)
        if self.blank:
            return

        center_x = x + side / 2
        center_y = y + side / 2
        radius = side / 2
        step = max(4, side // 48)
        painter.setPen(QPen(QColor("#c5c5c5"), 1))
        for offset in range(step, side, step):
            x_line = x + offset
            dx = x_line - center_x
            y_extent = int((radius * radius - dx * dx) ** 0.5) if abs(dx) <= radius else 0
            painter.drawLine(x_line, int(center_y - y_extent), x_line, int(center_y + y_extent))
            y_line = y + offset
            dy = y_line - center_y
            x_extent = int((radius * radius - dy * dy) ** 0.5) if abs(dy) <= radius else 0
            painter.drawLine(int(center_x - x_extent), y_line, int(center_x + x_extent), y_line)

        painter.setPen(QPen(QColor("#00a040"), 3))
        painter.drawLine(int(center_x), int(center_y - 10), int(center_x), int(center_y + 10))
        painter.drawLine(int(center_x - 10), int(center_y), int(center_x + 10), int(center_y))
        painter.setPen(QPen(QColor("#b8b8b8"), 3))
        painter.drawEllipse(self.width() - 34, self.height() - 34, 13, 13)
        painter.drawLine(self.width() - 24, self.height() - 24, self.width() - 14, self.height() - 14)


class WaferMapZoomDialog(QDialog):
    def __init__(self, parent=None, blank: bool = False):
        super().__init__(parent)
        self.blank = blank
        self.setWindowTitle("Wafer Map Image")
        self.setFixedSize(560, 610)
        self.setStyleSheet(
            """
            QDialog {
                background: #ffffff;
                color: #111111;
                font-family: Arial, Helvetica, sans-serif;
            }
            QLabel {
                font-size: 22px;
                font-weight: 700;
            }
            QPushButton#closeButton {
                background: #c93b31;
                border: 1px solid #ffffff;
                color: #ffffff;
                font-size: 18px;
                font-weight: 700;
                padding: 0;
            }
            """
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 18, 18, 18)
        header = QHBoxLayout()
        header.addWidget(QLabel("Wafer Map Image"))
        header.addStretch(1)
        close_button = QPushButton("x")
        close_button.setObjectName("closeButton")
        close_button.setFixedSize(28, 28)
        close_button.clicked.connect(self.accept)
        header.addWidget(close_button)
        root.addLayout(header)
        root.addWidget(WaferMapImage(500, blank=blank), alignment=Qt.AlignCenter)


class CareAreasPreview(QWidget):
    def __init__(self, width: int = 150, height: int = 148, zoom_callback=None, parent=None, show_magnifier: bool = True):
        super().__init__(parent)
        self.zoom_callback = zoom_callback
        self.show_magnifier = show_magnifier
        self.setFixedSize(width, height)
        if zoom_callback:
            self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        magnifier_gap = 28 if self.show_magnifier else 8
        card_width = max(36, int(self.width() * 0.30))
        card_height = max(48, self.height() - 8)
        card_x = max(4, (self.width() - magnifier_gap - card_width) // 2)
        card = self.rect().__class__(card_x, 2, card_width, card_height)
        painter.fillRect(card, QColor("#ffffff"))
        painter.setPen(QPen(QColor("#d0d0d0"), 1))
        painter.drawRect(card)

        def place(x_ratio, y_ratio, w_ratio, h_ratio):
            return (
                card.left() + int(card.width() * x_ratio),
                card.top() + int(card.height() * y_ratio),
                max(6, int(card.width() * w_ratio)),
                max(6, int(card.height() * h_ratio)),
            )

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#00c000"))
        painter.drawRect(*place(0.22, 0.05, 0.46, 0.13))
        painter.setBrush(QColor("#c48a12"))
        painter.drawRect(*place(0.16, 0.40, 0.42, 0.16))
        hatch_x, hatch_y, hatch_w, hatch_h = place(0.52, 0.66, 0.30, 0.11)
        painter.setBrush(QColor("#8d9a22"))
        painter.drawRect(hatch_x, hatch_y, hatch_w, hatch_h)
        painter.save()
        painter.setClipRect(hatch_x, hatch_y, hatch_w, hatch_h)
        painter.setPen(QPen(QColor("#5c6810"), 1))
        step = max(3, min(hatch_w, hatch_h) // 4)
        for line_x in range(hatch_x, hatch_x + hatch_w, step):
            painter.drawLine(line_x, hatch_y, line_x, hatch_y + hatch_h)
        for line_y in range(hatch_y, hatch_y + hatch_h, step):
            painter.drawLine(hatch_x, line_y, hatch_x + hatch_w, line_y)
        painter.restore()
        if self.show_magnifier:
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor("#8a8a8a"), 1.4))
            glass_x = self.width() - 20
            glass_y = self.height() - 22
            painter.drawEllipse(glass_x, glass_y, 10, 10)
            painter.drawLine(glass_x + 8, glass_y + 8, glass_x + 14, glass_y + 14)

    def mousePressEvent(self, event):  # noqa: N802 - Qt override
        if self.zoom_callback:
            self.zoom_callback()
        if event is not None:
            event.accept()


class SamplePlanPreview(QWidget):
    def __init__(self, size: int = 168, zoom_callback=None, parent=None, show_magnifier: bool = True):
        super().__init__(parent)
        self.zoom_callback = zoom_callback
        self.show_magnifier = show_magnifier
        self.setFixedSize(size, size)
        if zoom_callback:
            self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        right_margin = 28 if self.show_magnifier else 8
        bottom_margin = 22 if self.show_magnifier else 8
        rect = self.rect().adjusted(4, 2, -right_margin, -bottom_margin)
        side = min(rect.width(), rect.height())
        x = rect.left() + max(0, (rect.width() - side) // 2)
        y = rect.top()
        center_x = x + side / 2
        center_y = y + side / 2
        radius = side / 2
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(180, 180, 180, 40))
        painter.drawEllipse(int(x) + 3, int(y) + 3, side, side)
        clip = QPainterPath()
        clip.addEllipse(x, y, side, side)
        painter.setClipPath(clip)
        painter.fillRect(int(x), int(y), side, side, QColor("#e6e9f0"))
        cell = max(4, side // 26)
        for row in range(int(y), int(y + side), cell):
            for col in range(int(x), int(x + side), cell):
                tone = QColor("#b7bfce") if ((row // cell + col // cell) % 2 == 0) else QColor("#d5dbe6")
                painter.fillRect(col, row, cell, cell, tone)
        painter.setPen(QPen(QColor("#9aa3b5"), 1))
        for row in range(int(y), int(y + side) + cell, cell):
            painter.drawLine(int(x), row, int(x + side), row)
        for col in range(int(x), int(x + side) + cell, cell):
            painter.drawLine(col, int(y), col, int(y + side))
        painter.setClipping(False)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor("#d5d5d5"), 3))
        painter.drawEllipse(int(x), int(y), side, side)
        painter.setPen(QPen(QColor("#b7b7b7"), 1))
        painter.drawEllipse(int(x), int(y), side, side)
        if self.show_magnifier:
            painter.setPen(QPen(QColor("#8a8a8a"), 1.4))
            glass_x = self.width() - 20
            glass_y = self.height() - 20
            painter.drawEllipse(glass_x, glass_y, 10, 10)
            painter.drawLine(glass_x + 8, glass_y + 8, glass_x + 14, glass_y + 14)

    def mousePressEvent(self, event):  # noqa: N802 - Qt override
        if self.zoom_callback:
            self.zoom_callback()
        if event is not None:
            event.accept()


class OverviewPreviewDialog(QDialog):
    def __init__(self, title: str, preview: QWidget, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setStyleSheet(
            "QDialog { background: #ffffff; font-family: Arial; } "
            "QLabel { font-size: 18px; font-weight: 700; } "
            "QPushButton { min-width: 80px; min-height: 26px; }"
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)
        root.addWidget(QLabel(title))
        root.addWidget(preview, alignment=Qt.AlignCenter)
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        root.addWidget(close_button, alignment=Qt.AlignRight)
        self.adjustSize()


class _HistoryLogIcon(QWidget):
    """Small document icon that opens the Recipe History Log."""

    def __init__(self, callback, parent=None):
        super().__init__(parent)
        self.callback = callback
        self.setFixedSize(16, 16)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Open Recipe History Log")

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor("#2f5fbf"), 1))
        painter.setBrush(QColor("#f7f8ff"))
        painter.drawRect(2, 1, 10, 13)
        painter.setPen(QPen(QColor("#2f5fbf"), 1))
        painter.drawLine(4, 5, 10, 5)
        painter.drawLine(4, 8, 10, 8)
        painter.drawLine(4, 11, 8, 11)

    def mousePressEvent(self, event):  # noqa: N802 - Qt override
        if self.callback:
            self.callback()
        if event is not None:
            event.accept()


class PumaMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wafer Inspection System - Puma 9980 UI")
        self._resize_for_screen(default_width=1600, default_height=900, minimum_width=1180, minimum_height=760)
        self.visible_recipe_parameters = dict(DEFAULT_VISIBLE_RECIPE_PARAMETERS)
        self.recipe_store = RecipeStore(default_recipes=OpenInspectionRecipeDialog.RECIPES)
        ensure_demo_recipe(self.recipe_store, persist=False)
        ensure_virtual_figure_recipe(self.recipe_store, persist=False)
        stored_overview_parameters = self.recipe_store.get_preferences().get(
            "visible_recipe_parameters", {}
        )
        if isinstance(stored_overview_parameters, dict):
            self.visible_recipe_parameters.update(stored_overview_parameters)
        self.current_recipe = self.recipe_store.new_recipe()
        self._recipe_loaded_from_library = False
        self.wafer_runtime_state = {
            "selected_port": 1,
            "carrier_loaded": {1: True, 2: False},
            "selected_slots": {1: 25, 2: None},
            "wafer_loaded": False,
            "wafer_aligned": False,
            "required_orientation": "180",
        }
        self.recipe_overview_sections = {}
        self.recipe_overview_groups = {}
        self.recipe_overview_rows = {}
        self.overview_action_labels = {}
        self.overview_status_dots = {}
        self._navigation_history = ["home"]
        self._navigation_index = 0
        self._active_route_key = "home"
        self.die_layout_labels = {}
        self.test_overview_labels = {}
        self.test_overview_contexts = []
        self.selected_test_index = 0
        self.alignment_context_active = False
        self.image_display_window = None
        self.optics_engaged = True
        self.optics_applied_settings = {}
        self.ruler_visible = False
        self.wafermap_image_acquired = False
        self.wafermap_image_visible = False
        self.setup_toolbar_user_visible = True
        self.review_toolbar_visible = True
        self.review_image_toolbar_visible = True
        self.alarm_events = []
        self._build_menus()
        self._build_toolbar()
        self._build_central()
        self._build_statusbar()
        self._navigate_to("home", record=False)
        self._apply_recipe_overview_visibility()
        self._set_current_recipe(self.current_recipe, message="New inspection loaded")
        self.setStyleSheet(
            """
            QMainWindow, QWidget#root {
                background: #cfcbc2;
                color: #111111;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10px;
            }
            QMenuBar {
                background: #d7d4cc;
                border-bottom: 1px solid #8c8982;
            }
            QMenuBar::item {
                padding: 2px 8px;
            }
            QToolBar {
                background: #c7c3ba;
                border-top: 1px solid #f8f8f8;
                border-bottom: 1px solid #79766e;
                spacing: 2px;
            }
            QComboBox, QSpinBox, QDoubleSpinBox {
                background: #ffffff;
                color: #111111;
                border: 1px solid #8a8680;
                min-height: 20px;
                max-height: 22px;
                padding: 0 2px;
                font-size: 11px;
            }
            QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {
                background: #ffffff;
                color: #6a6a6a;
            }
            QStatusBar {
                background: #d7d4cc;
                border-top: 1px solid #8f8b82;
                font-size: 10px;
            }
            """
        )

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
        width = min(default_width, max(minimum_width, int(available.width() * MAIN_WINDOW_FRACTION)))
        height = min(default_height, max(minimum_height, int(available.height() * MAIN_WINDOW_FRACTION)))
        self.resize(width, height)
        self.setMinimumSize(minimum_width, minimum_height)
        self.move(
            available.x() + (available.width() - width) // 2,
            available.y() + (available.height() - height) // 2,
        )

    def _build_menus(self):
        menu = self.menuBar()
        file_menu = menu.addMenu("File")
        new_inspection = QAction("New Inspection", self)
        new_inspection.setShortcut("Ctrl+N")
        new_inspection.triggered.connect(self.new_inspection)
        file_menu.addAction(new_inspection)
        save_inspection = QAction("Save Inspection", self)
        save_inspection.setShortcut("Ctrl+I")
        save_inspection.triggered.connect(self.save_inspection)
        file_menu.addAction(save_inspection)
        save_as = QAction("Save Inspection As...", self)
        save_as.triggered.connect(lambda: self.save_inspection(save_copy=True))
        file_menu.addAction(save_as)
        open_inspection = QAction("Open Inspection...", self)
        open_inspection.triggered.connect(lambda: self._navigate_to("select_inspection"))
        file_menu.addAction(open_inspection)
        inspection_properties = QAction("Inspection Properties...", self)
        inspection_properties.triggered.connect(
            lambda: self._navigate_to("inspection_properties")
        )
        file_menu.addAction(inspection_properties)
        print_window = QAction("Print Window", self)
        print_window.setShortcut("Ctrl+P")
        print_window.triggered.connect(self.print_current_view)
        file_menu.addAction(print_window)
        file_admin = QAction("FileAdmin Utility...", self)
        file_admin.triggered.connect(self.open_file_admin_utility)
        file_menu.addAction(file_admin)
        log_off = QAction("Log Off", self)
        log_off.triggered.connect(self.log_off_user)
        file_menu.addAction(log_off)
        file_menu.addSeparator()
        shutdown = QAction("Shutdown Application...", self)
        shutdown.setShortcut("Ctrl+Q")
        shutdown.triggered.connect(self.request_shutdown)
        file_menu.addAction(shutdown)

        edit_menu = menu.addMenu("Edit")
        extract = QAction("Extract Component", self)
        extract.triggered.connect(self.extract_components)
        edit_menu.addAction(extract)
        insert = QAction("Insert Component", self)
        insert.triggered.connect(self.insert_components)
        edit_menu.addAction(insert)
        edit_menu.addSeparator()
        self.copy_test_action = QAction("Copy Test", self)
        self.copy_test_action.setEnabled(False)
        self.copy_test_action.triggered.connect(self._copy_active_test)
        edit_menu.addAction(self.copy_test_action)
        self.paste_test_action = QAction("Paste Test", self)
        self.paste_test_action.setEnabled(False)
        self.paste_test_action.triggered.connect(self._paste_active_test)
        edit_menu.addAction(self.paste_test_action)
        edit_menu.addSeparator()
        self.copy_sample_plan_action = QAction("Copy Sample Plan", self)
        self.copy_sample_plan_action.setShortcut("Ctrl+Shift+C")
        self.copy_sample_plan_action.setEnabled(False)
        self.copy_sample_plan_action.triggered.connect(self._copy_active_sample_plan)
        edit_menu.addAction(self.copy_sample_plan_action)
        self.paste_sample_plan_action = QAction("Paste Sample Plan", self)
        self.paste_sample_plan_action.setShortcut("Ctrl+Shift+V")
        self.paste_sample_plan_action.setEnabled(False)
        self.paste_sample_plan_action.triggered.connect(self._paste_active_sample_plan)
        edit_menu.addAction(self.paste_sample_plan_action)

        optics_menu = menu.addMenu("Optics")
        review_optics = QAction("Advanced Review Optics Settings", self)
        review_optics.triggered.connect(self.open_review_optics)
        optics_menu.addAction(review_optics)

        setup_menu = menu.addMenu("Set Up")
        select_inspection = QAction("Select Inspection", self)
        select_inspection.triggered.connect(lambda: self._navigate_to("select_inspection"))
        setup_menu.addAction(select_inspection)
        wafer_menu = setup_menu.addMenu("Wafer")
        wafer_properties = QAction("Wafer Properties", self)
        wafer_properties.triggered.connect(lambda: self._navigate_to("wafer_properties"))
        wafer_menu.addAction(wafer_properties)
        alignment = QAction("Alignment", self)
        alignment.triggered.connect(lambda: self._navigate_to("alignment"))
        wafer_menu.addAction(alignment)
        wafermap = QAction("Wafermap", self)
        wafermap.triggered.connect(lambda: self._navigate_to("wafer_map"))
        wafer_menu.addAction(wafermap)
        registration_sites = QAction("Registration Site...", self)
        registration_sites.triggered.connect(
            lambda: self._navigate_to("registration_sites")
        )
        wafer_menu.addAction(registration_sites)
        self.design_registration_action = QAction("Design Registration...", self)
        self.design_registration_action.triggered.connect(self.open_design_registration)
        wafer_menu.addAction(self.design_registration_action)
        self.dbc_setup_action = QAction("DBC Setup...", self)
        self.dbc_setup_action.triggered.connect(self.open_dbc_setup)
        wafer_menu.addAction(self.dbc_setup_action)
        select_defect_data = QAction("Select Defect Data", self)
        select_defect_data.triggered.connect(
            lambda: self._navigate_to("select_defect_data")
        )
        wafer_menu.addAction(select_defect_data)
        tests_action = QAction("Tests", self)
        tests_action.triggered.connect(lambda: self._navigate_to("tests"))
        setup_menu.addAction(tests_action)
        lot_plan = QAction("Lot Plan", self)
        lot_plan.triggered.connect(lambda: self._navigate_to("lot_plan"))
        setup_menu.addAction(lot_plan)
        wafer_post_processing = QAction("Wafer Post Processing", self)
        wafer_post_processing.triggered.connect(
            lambda: self._navigate_to("wafer_post_processing")
        )
        setup_menu.addAction(wafer_post_processing)
        self.dbb_setup_action = QAction("Design Based Binning...", self)
        self.dbb_setup_action.triggered.connect(self.open_dbb_setup)
        setup_menu.addAction(self.dbb_setup_action)
        sizing_recipe = QAction("Sizing...", self)
        sizing_recipe.triggered.connect(self.open_sizing_recipe_setup)
        setup_menu.addAction(sizing_recipe)
        xp_generation = QAction("Recipe Generation...", self)
        xp_generation.triggered.connect(self.open_xp_recipe_generation)
        setup_menu.addAction(xp_generation)
        setup_run_menu = setup_menu.addMenu("Setup Run")
        run_one = QAction("Run One Wafer", self)
        run_one.triggered.connect(self.open_run_one_wafer)
        setup_run_menu.addAction(run_one)
        self.snapshot_review_action = QAction("Snapshot Review", self)
        self.snapshot_review_action.setEnabled(True)
        self.snapshot_review_action.triggered.connect(self.open_latest_snapshot)
        setup_run_menu.addAction(self.snapshot_review_action)
        setup_menu.addAction(save_inspection)

        run_menu = menu.addMenu("Run")
        queue = QAction("Inspection Queue", self)
        queue.triggered.connect(self.open_job_queue)
        run_menu.addAction(queue)
        self.run_lot_plan_action = QAction("Lot Plan", self)
        self.run_lot_plan_action.triggered.connect(self.open_run_lot_plan)
        run_menu.addAction(self.run_lot_plan_action)
        run_menu.addAction("Snapshot Review", self.open_latest_snapshot)
        run_menu.addAction("View Run Log", lambda: self.open_system_log("run"))
        review_result = QAction("Review Wafer", self)
        review_result.triggered.connect(self.open_review_results)
        run_menu.addAction(review_result)

        review_menu = menu.addMenu("Review")
        select_lot = QAction("Select Lot Results", self)
        select_lot.triggered.connect(self.open_review_results)
        review_menu.addAction(select_lot)
        import_klarf = QAction("Import KLARF...", self)
        import_klarf.triggered.connect(self.import_review_klarf)
        review_menu.addAction(import_klarf)
        sizing_setup = QAction("Sizing Setup Tool...", self)
        sizing_setup.triggered.connect(self.open_sizing_setup)
        review_menu.addAction(sizing_setup)
        dbb_view = QAction("DBB View...", self)
        dbb_view.triggered.connect(self.open_dbb_view)
        review_menu.addAction(dbb_view)
        review_menu.addSeparator()
        review_menu.addAction(
            "Adjust Defect Location...",
            lambda: self.open_review_results(initial_action="adjust_defect_location"),
        )
        review_menu.addAction(
            "Adjust Die Origin...",
            lambda: self.open_review_results(initial_action="adjust_die_origin"),
        )
        review_menu.addAction(
            "Optics Selector...",
            lambda: self.open_review_results(initial_action="optics_selector"),
        )
        review_menu.addAction(
            "Sensitivity Tuner...",
            lambda: self.open_review_results(initial_action="sensitivity_tuner"),
        )

        view_menu = menu.addMenu("View")
        reset_zoom = QAction("Reset Wafermap Zoom", self)
        reset_zoom.setShortcut("Ctrl+R")
        reset_zoom.triggered.connect(self.reset_wafermap_zoom)
        view_menu.addAction(reset_zoom)
        self.wafermap_image_menu = view_menu.addMenu("Wafermap Image")
        self.acquire_wafermap_image_action = self.wafermap_image_menu.addAction(
            "Acquire",
            self.acquire_wafermap_image,
        )
        self.toggle_wafermap_image_action = self.wafermap_image_menu.addAction(
            "Toggle WaferMap Image"
        )
        self.toggle_wafermap_image_action.setCheckable(True)
        self.toggle_wafermap_image_action.setEnabled(False)
        self.toggle_wafermap_image_action.triggered.connect(
            self.toggle_wafermap_image_from_menu
        )
        view_menu.addAction("Images", self.open_last_alignment_swath_image)
        toolbars_menu = view_menu.addMenu("Toolbars")
        self.standard_toolbar_action = QAction("Standard Toolbar", self)
        self.standard_toolbar_action.setCheckable(True)
        self.standard_toolbar_action.setChecked(True)
        self.standard_toolbar_action.toggled.connect(
            lambda visible: self._set_toolbar_group_visible("standard", visible)
        )
        toolbars_menu.addAction(self.standard_toolbar_action)
        self.optics_toolbar_action = QAction("Optics Toolbar", self)
        self.optics_toolbar_action.setCheckable(True)
        self.optics_toolbar_action.setChecked(True)
        self.optics_toolbar_action.toggled.connect(
            lambda visible: self._set_toolbar_group_visible("optics", visible)
        )
        toolbars_menu.addAction(self.optics_toolbar_action)
        self.setup_toolbar_action = QAction("Setup Toolbar", self)
        self.setup_toolbar_action.setCheckable(True)
        self.setup_toolbar_action.setChecked(True)
        self.setup_toolbar_action.toggled.connect(self._set_setup_toolbar_user_visible)
        toolbars_menu.addAction(self.setup_toolbar_action)
        self.review_toolbar_action = QAction("Review Toolbar", self)
        self.review_toolbar_action.setCheckable(True)
        self.review_toolbar_action.setChecked(True)
        self.review_toolbar_action.toggled.connect(self._set_review_toolbar_visible)
        toolbars_menu.addAction(self.review_toolbar_action)
        self.review_image_toolbar_action = QAction("Review Image Toolbar", self)
        self.review_image_toolbar_action.setCheckable(True)
        self.review_image_toolbar_action.setChecked(True)
        self.review_image_toolbar_action.toggled.connect(self._set_review_image_toolbar_visible)
        toolbars_menu.addAction(self.review_image_toolbar_action)
        self.navigation_bar_action = QAction("Navigation Bar", self)
        self.navigation_bar_action.setCheckable(True)
        self.navigation_bar_action.setChecked(True)
        self.navigation_bar_action.toggled.connect(self._set_navigation_bar_visible)
        toolbars_menu.addAction(self.navigation_bar_action)
        self.status_bar_action = QAction("Status Bar", self)
        self.status_bar_action.setCheckable(True)
        self.status_bar_action.setChecked(True)
        self.status_bar_action.toggled.connect(self._set_status_bar_visible)
        view_menu.addAction(self.status_bar_action)
        self.image_display_action = QAction("Image Display", self)
        self.image_display_action.setEnabled(True)
        self.image_display_action.triggered.connect(self.open_image_display)
        view_menu.addAction(self.image_display_action)
        recipe_history = QAction("Recipe History", self)
        recipe_history.triggered.connect(self.show_recipe_history)
        view_menu.addAction(recipe_history)
        lot_summary = QAction("Lot Summary", self)
        lot_summary.triggered.connect(self.open_lot_summary)
        view_menu.addAction(lot_summary)
        click_and_mark = QAction("Click and Mark Configuration...", self)
        click_and_mark.triggered.connect(self.open_click_and_mark_configuration)
        view_menu.addAction(click_and_mark)
        view_menu.addAction("Camera Image", self.open_image_display)
        view_menu.addAction(
            "Edit Care Areas Toolbar",
            lambda: self._navigate_to("test_care_areas"),
        )
        view_logs = view_menu.addMenu("Logs")
        self._populate_log_menu(view_logs)
        view_menu.addSeparator()

        utilities_menu = menu.addMenu("Utilities")
        initialize = QAction("Initialize System...", self)
        initialize.triggered.connect(self.open_initialize_system)
        utilities_menu.addAction(initialize)
        maintenance = QAction("Preventive Maintenance...", self)
        maintenance.triggered.connect(self.open_preventive_maintenance)
        utilities_menu.addAction(maintenance)
        utility_logs = utilities_menu.addMenu("View Logs")
        self._populate_log_menu(utility_logs)
        show_options = QAction("Show Options", self)
        show_options.triggered.connect(self.open_software_options)
        utilities_menu.addAction(show_options)
        e84_signals = QAction("E84 Real-time Signal Display...", self)
        e84_signals.triggered.connect(self.open_e84_signal_display)
        utilities_menu.addAction(e84_signals)
        inspection_matching = QAction("Inspection Matching Utility...", self)
        inspection_matching.triggered.connect(self.open_inspection_matching)
        utilities_menu.addAction(inspection_matching)
        equipment_constants = QAction("Equipment Constants...", self)
        equipment_constants.triggered.connect(self.open_equipment_constants)
        utilities_menu.addAction(equipment_constants)
        utilities_menu.addSeparator()
        delete_inspections = QAction("Delete Inspections...", self)
        delete_inspections.triggered.connect(self.open_delete_inspections)
        utilities_menu.addAction(delete_inspections)
        erc_manager = QAction("ERC Manager...", self)
        erc_manager.triggered.connect(self.open_erc_manager)
        utilities_menu.addAction(erc_manager)
        send_lots = QAction("Send Lots...", self)
        send_lots.triggered.connect(self.open_send_lots)
        utilities_menu.addAction(send_lots)
        rename_lot = QAction("Rename Lot...", self)
        rename_lot.triggered.connect(self.open_rename_lot)
        utilities_menu.addAction(rename_lot)
        recipe_comparator = QAction("Recipe Comparator...", self)
        recipe_comparator.triggered.connect(self.open_recipe_comparator)
        utilities_menu.addAction(recipe_comparator)
        gds2ca_converter = QAction("GDS2CA Converter...", self)
        gds2ca_converter.triggered.connect(self.open_gds2ca_converter)
        utilities_menu.addAction(gds2ca_converter)

        tools_menu = menu.addMenu("Tools")
        sizing_tool = QAction("Sizing Setup Tool...", self)
        sizing_tool.triggered.connect(self.open_sizing_setup)
        tools_menu.addAction(sizing_tool)
        control_jobs = QAction("Control Job Management...", self)
        control_jobs.triggered.connect(self.open_control_job_management)
        tools_menu.addAction(control_jobs)
        substrate_tracking = QAction("Substrate Tracking...", self)
        substrate_tracking.setShortcut("Ctrl+J")
        substrate_tracking.triggered.connect(self.open_substrate_tracking)
        tools_menu.addAction(substrate_tracking)
        carrier_management = QAction("Carrier Management...", self)
        carrier_management.setShortcut("Ctrl+K")
        carrier_management.triggered.connect(self.open_carrier_management)
        tools_menu.addAction(carrier_management)
        rds_manager = QAction("Recipe Distribution System...", self)
        rds_manager.triggered.connect(self.open_rds_manager)
        tools_menu.addAction(rds_manager)
        manual_assist = QAction("Manual Assist for AutoDerivative...", self)
        manual_assist.triggered.connect(self.open_manual_assist)
        tools_menu.addAction(manual_assist)
        tools_menu.addAction("Laser Maintenance...", self.open_laser_maintenance)
        diagnostics = QAction("Diagnostics GUI...", self)
        diagnostics.setShortcut("Ctrl+G")
        diagnostics.triggered.connect(self.open_diagnostics_gui)
        tools_menu.addAction(diagnostics)
        smart_diagnostics = QAction("Smart Diagnostics GUI...", self)
        smart_diagnostics.setShortcut("Ctrl+T")
        smart_diagnostics.triggered.connect(self.open_smart_diagnostics_gui)
        tools_menu.addAction(smart_diagnostics)
        tools_menu.addAction("GDS2CA Converter...", self.open_gds2ca_converter)
        tools_menu.addAction("CAG Editor...", self.open_cag_editor)
        data_transfer = tools_menu.addMenu("Data Transfer")
        transfer_configuration = QAction("View Configuration", self)
        transfer_configuration.triggered.connect(self.open_transfer_configuration)
        data_transfer.addAction(transfer_configuration)
        transfer_queue = QAction("Show Queue", self)
        transfer_queue.triggered.connect(self.open_transfer_queue)
        data_transfer.addAction(transfer_queue)
        data_transfer.addSeparator()
        self.transfer_service_action = QAction("Shut Down", self)
        self.transfer_service_action.triggered.connect(self.toggle_transfer_service)
        data_transfer.addAction(self.transfer_service_action)
        secs_menu = tools_menu.addMenu("SECS")
        self.secs_communication_action = QAction("Disable Communication", self)
        self.secs_communication_action.triggered.connect(self.toggle_secs_communication)
        secs_menu.addAction(self.secs_communication_action)
        secs_menu.addAction("Online / Remote Mode", lambda: self.set_secs_control_mode("Remote"))
        secs_menu.addAction("Online / Local Mode", lambda: self.set_secs_control_mode("Local"))
        secs_menu.addSeparator()
        communication = QAction("SECS / ILink Status and Configuration...", self)
        communication.triggered.connect(self.open_communication_status)
        secs_menu.addAction(communication)
        set_e10 = QAction("Set E10 States...", self)
        set_e10.setShortcut("Ctrl+Shift+F")
        set_e10.triggered.connect(lambda: self.open_secs_operations(initial_tab=0))
        secs_menu.addAction(set_e10)
        secs_menu.addAction("Set Equipment Constants...", self.open_equipment_constants)
        secs_menu.addAction(
            "Send Message To Host...",
            lambda: self.open_secs_operations(initial_tab=1),
        )
        secs_menu.addAction("Synchronize Clock", self.synchronize_host_clock)
        secs_menu.addAction(
            "Process Program Upload / Download...",
            lambda: self.open_secs_operations(initial_tab=2),
        )
        preferences = tools_menu.addMenu("Preferences")
        user_preferences = QAction("Change User Preferences...", self)
        user_preferences.triggered.connect(self.open_user_preferences)
        preferences.addAction(user_preferences)
        print_on_run = QAction("Print on Run", self)
        print_on_run.triggered.connect(self.open_print_on_run)
        preferences.addAction(print_on_run)
        display_colors = QAction("Change Default Colors", self)
        display_colors.triggered.connect(self.open_display_colors)
        preferences.addAction(display_colors)
        system_security = tools_menu.addMenu("System Security")
        user_admin = QAction("User Administration...", self)
        user_admin.triggered.connect(self.open_user_administration)
        system_security.addAction(user_admin)
        group_admin = QAction("Group Administration...", self)
        group_admin.triggered.connect(lambda: self.open_user_administration(group_tab=True))
        system_security.addAction(group_admin)
        system_security.addAction("Log Off", self.log_off_user)
        signal_tower = tools_menu.addMenu("Signal Tower")
        signal_tower.addAction("Configuration...", self.open_signal_tower_configuration)
        signal_tower.addAction("Control...", self.open_signal_tower_control)
        load_port_lights = QAction("Load Port Indicator Lights...", self)
        load_port_lights.triggered.connect(self.open_load_port_indicators)
        tools_menu.addAction(load_port_lights)
        self.e116_action = QAction("E116 EPT Enabled", self)
        self.e116_action.setCheckable(True)
        self.e116_action.triggered.connect(self.toggle_e116)
        tools_menu.addAction(self.e116_action)
        log_settings = QAction("Log Settings...", self)
        log_settings.triggered.connect(self.open_log_settings)
        tools_menu.addAction(log_settings)
        backup_restore = QAction("Backup / Archive / Restore...", self)
        backup_restore.triggered.connect(self.open_backup_archive_restore)
        tools_menu.addAction(backup_restore)
        disk_admin = QAction("Disk Admin...", self)
        disk_admin.triggered.connect(self.open_disk_admin)
        tools_menu.addAction(disk_admin)
        tools_configure = QAction("Tools Configure...", self)
        tools_configure.triggered.connect(self.open_tools_configuration)
        tools_menu.addAction(tools_configure)
        wafer_handling = QAction("Wafer Handling", self)
        wafer_handling.setShortcut("Ctrl+W")
        wafer_handling.triggered.connect(self.open_wafer_handling)
        tools_menu.addAction(wafer_handling)
        self.alarm_action = QAction("Alarm Alert", self)
        self.alarm_action.setEnabled(True)
        self.alarm_action.triggered.connect(self.open_alarm_center)
        tools_menu.addAction(self.alarm_action)
        help_menu = menu.addMenu("Help")
        self.user_manual_action = QAction("User Manual", self)
        self.user_manual_action.setShortcut("F1")
        self.user_manual_action.triggered.connect(self.open_user_manual)
        help_menu.addAction(self.user_manual_action)
        help_menu.addAction(
            "About Puma 9980 UI Simulator",
            lambda: QMessageBox.information(
                self,
                "About Puma 9980 UI Simulator",
                "Training simulator based on the Puma 9980 v9.8.306 user manual. "
                "Equipment motion, optics, inspection, and factory communication are simulated.",
            ),
        )
        self._top_level_menus = (
            file_menu,
            edit_menu,
            optics_menu,
            setup_menu,
            run_menu,
            review_menu,
            view_menu,
            utilities_menu,
            tools_menu,
            help_menu,
        )
        for top_menu, shortcut in (
            (file_menu, "Alt+F"),
            (edit_menu, "Alt+E"),
            (optics_menu, "Alt+O"),
            (review_menu, "Alt+R"),
            (view_menu, "Alt+V"),
            (tools_menu, "Alt+T"),
            (help_menu, "Alt+H"),
        ):
            top_menu.menuAction().setShortcut(shortcut)
        self._top_level_menu_actions = tuple(menu.actions())
        self._refresh_transfer_service_action()
        self._refresh_secs_communication_action()
        self._refresh_e116_action()

    def request_shutdown(self):
        choice = QMessageBox.question(
            self,
            "Shutdown Application",
            "Exit the Puma 9980 UI simulator? Equipment power-off remains an operator and hardware procedure.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if choice == QMessageBox.Yes:
            self.close()

    def _populate_log_menu(self, menu):
        entries = (
            ("Run Log", "run"),
            ("Daily Logs", "daily"),
            ("Recipe History", "recipe"),
            ("Flight Logs", "flight"),
        )
        for label, kind in entries:
            action = QAction(label, self)
            action.triggered.connect(lambda _checked=False, value=kind: self.open_system_log(value))
            menu.addAction(action)

    def _blank_icon(self) -> tuple[QPixmap, QPainter]:
        pixmap = QPixmap(24, 24)
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        return pixmap, painter

    def _pixel_icon(self) -> tuple[QPixmap, QPainter]:
        pixmap = QPixmap(24, 24)
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        painter.setPen(Qt.NoPen)
        return pixmap, painter

    def _wafer_handling_icon(self) -> QIcon:
        pixmap, painter = self._pixel_icon()
        painter.setBrush(QColor("#c0c0c0"))
        painter.drawRect(1, 1, 22, 22)
        painter.setBrush(QColor("#ffffff"))
        painter.drawRect(1, 1, 21, 1)
        painter.drawRect(1, 2, 1, 20)
        painter.setBrush(QColor("#808080"))
        painter.drawRect(21, 2, 1, 20)
        painter.drawRect(2, 21, 19, 1)
        painter.setBrush(QColor("#202020"))
        painter.drawRect(22, 2, 1, 21)
        painter.drawRect(2, 22, 21, 1)
        painter.setBrush(QColor("#111111"))
        painter.drawRect(6, 4, 12, 15)
        painter.setBrush(QColor("#008000"))
        painter.drawRect(7, 5, 10, 3)
        painter.setBrush(QColor("#111111"))
        painter.drawRect(10, 6, 4, 2)
        bands = (
            (8, "#8a8a8a"),
            (9, "#6a6a6a"),
            (10, "#007000"),
            (11, "#008000"),
            (12, "#7a7a7a"),
            (13, "#5e5e5e"),
            (14, "#006000"),
            (15, "#008000"),
            (16, "#707070"),
            (17, "#909090"),
        )
        for y, color in bands:
            painter.setBrush(QColor(color))
            painter.drawRect(7, y, 10, 1)
        painter.end()
        return self._color_icon(pixmap)

    def _job_queue_icon(self) -> QIcon:
        pixmap, painter = self._pixel_icon()
        painter.setBrush(QColor("#000000"))
        painter.drawRect(1, 1, 22, 22)
        painter.setBrush(QColor("#f3f0e4"))
        painter.drawRect(2, 2, 19, 19)
        painter.setBrush(QColor("#6a675c"))
        painter.drawRect(4, 4, 17, 17)
        painter.setBrush(QColor("#f7f4ea"))
        painter.drawRect(4, 4, 15, 15)
        painter.setBrush(QColor("#ffff00"))
        painter.drawRect(6, 6, 12, 12)
        painter.setBrush(QColor("#1c1a00"))
        painter.drawRect(6, 6, 12, 2)
        painter.setBrush(QColor("#e2c400"))
        painter.drawRect(7, 6, 9, 1)
        painter.setBrush(QColor("#00d400"))
        painter.drawEllipse(7, 9, 10, 4)
        painter.setPen(QPen(QColor("#8a7830"), 1))
        painter.setBrush(QColor("#fff4b0"))
        painter.drawEllipse(7, 13, 10, 3)
        painter.setBrush(QColor("#fff8c8"))
        painter.drawEllipse(8, 16, 8, 3)
        painter.end()
        return self._color_icon(pixmap)

    def _paint_optics_horn(self, painter: QPainter):
        painter.setPen(QPen(QColor("#333333"), 1))
        painter.setBrush(QColor("#d5d5d5"))
        painter.drawRoundedRect(3, 9, 6, 6, 1, 1)
        horn = QPainterPath()
        horn.moveTo(8, 8)
        horn.lineTo(19, 4)
        horn.lineTo(19, 20)
        horn.lineTo(8, 16)
        horn.closeSubpath()
        painter.drawPath(horn)

    def _paint_light_hand(self, painter: QPainter):
        painter.setPen(QPen(QColor("#444444"), 1))
        painter.setBrush(QColor("#ececec"))
        painter.drawRoundedRect(6, 11, 11, 8, 2, 2)
        painter.drawRoundedRect(13, 4, 4, 11, 1, 1)
        painter.drawRoundedRect(8, 8, 3, 6, 1, 1)

    def _toolbar_icon(self, kind: str) -> QIcon:
        if kind == "wafer_handling":
            return self._wafer_handling_icon()
        if kind == "job_queue":
            return self._job_queue_icon()
        if kind == "alarm":
            return self._alarm_alert_icon(False)
        pixmap, painter = self._blank_icon()
        if kind == "print":
            painter.setPen(QPen(QColor("#555555"), 1))
            painter.setBrush(QColor("#f7f7f7"))
            painter.drawRect(8, 2, 8, 5)
            painter.setBrush(QColor("#c4c4c4"))
            painter.drawRoundedRect(4, 6, 16, 10, 1, 1)
            painter.setBrush(QColor("#f7f7f7"))
            painter.drawRect(8, 13, 8, 7)
            painter.drawLine(6, 10, 18, 10)
        elif kind == "manual":
            painter.setPen(QPen(QColor("#6a6a6a"), 1))
            painter.setBrush(QColor("#d4d4d4"))
            painter.drawRect(2, 2, 20, 20)
            painter.setPen(QPen(QColor("#ffffff"), 1))
            painter.drawLine(3, 3, 20, 3)
            painter.drawLine(3, 4, 3, 20)
            painter.setPen(QPen(QColor("#5a5a5a"), 1))
            painter.drawLine(4, 21, 21, 21)
            painter.drawLine(21, 4, 21, 21)
            mark = QPainterPath()
            mark.moveTo(8, 10)
            mark.cubicTo(8, 4, 17, 4, 16.5, 9)
            mark.cubicTo(16, 13, 12.5, 12.5, 12, 16)
            painter.setPen(QPen(QColor("#111111"), 2.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(mark)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#111111"))
            painter.drawEllipse(10, 18, 3, 3)
        elif kind == "disengage_optics":
            self._paint_optics_horn(painter)
        elif kind == "engage_optics":
            self._paint_optics_horn(painter)
            painter.setPen(QPen(QColor("#e10600"), 2))
            painter.drawLine(4, 4, 20, 20)
            painter.drawLine(20, 4, 4, 20)
        elif kind == "apply_optics":
            self._paint_optics_horn(painter)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#2aa4d6"))
            arrow = QPainterPath()
            arrow.moveTo(21, 9)
            arrow.lineTo(21, 15)
            arrow.lineTo(15, 15)
            arrow.lineTo(15, 18)
            arrow.lineTo(8, 12)
            arrow.lineTo(15, 6)
            arrow.lineTo(15, 9)
            arrow.closeSubpath()
            painter.drawPath(arrow)
        elif kind == "pixel_size":
            painter.setPen(QPen(QColor("#222222"), 1.2))
            painter.setBrush(QColor("#3a5ad6"))
            painter.drawEllipse(3, 3, 12, 12)
            painter.setBrush(QColor("#dce6ff"))
            painter.drawEllipse(6, 6, 5, 5)
            painter.setPen(QPen(QColor("#222222"), 2))
            painter.drawLine(13, 13, 20, 20)
        elif kind == "imaging_mode":
            for index, color in enumerate(("#1aa0e8", "#f08a12", "#222222")):
                painter.setPen(QPen(QColor("#222222"), 1))
                painter.setBrush(QColor(color))
                painter.drawRect(5 + index * 5, 4, 4, 16)
        elif kind == "aperture":
            painter.setPen(QPen(QColor("#444444"), 1))
            painter.setBrush(QColor("#b0b0b0"))
            painter.drawEllipse(3, 3, 18, 18)
            painter.setBrush(QColor("#4a4a4a"))
            for turn in range(6):
                blade = QPainterPath()
                blade.moveTo(12, 12)
                blade.arcTo(3, 3, 18, 18, turn * 60, 28)
                blade.closeSubpath()
                painter.drawPath(blade)
            painter.setBrush(QColor("#111111"))
            painter.drawEllipse(9, 9, 6, 6)
        elif kind == "illumination":
            painter.setPen(QPen(QColor("#333333"), 1.1))
            painter.setBrush(QColor("#fff6c8"))
            painter.drawEllipse(7, 2, 10, 13)
            painter.setBrush(QColor("#d0d0d0"))
            painter.drawRect(9, 14, 6, 3)
            painter.drawRect(10, 17, 4, 3)
        elif kind == "manual_light":
            self._paint_light_hand(painter)
        elif kind == "auto_light":
            self._paint_light_hand(painter)
            painter.setPen(QPen(QColor("#e10600"), 2))
            painter.drawLine(4, 4, 20, 20)
            painter.drawLine(20, 4, 4, 20)
        elif kind == "focus_offset":
            painter.setPen(QPen(QColor("#222222"), 1.2))
            painter.drawLine(12, 2, 12, 22)
            painter.drawLine(2, 12, 22, 12)
            painter.setBrush(QColor("#1fa83a"))
            painter.setPen(QPen(QColor("#145214"), 1))
            painter.drawEllipse(7, 7, 10, 10)
        elif kind == "advanced_optics":
            painter.setPen(QPen(QColor("#666666"), 1))
            painter.setBrush(QColor("#d0d0d0"))
            painter.drawRect(5, 6, 14, 12)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#222222"))
            for x in (8, 11, 14):
                painter.drawEllipse(x, 11, 2, 2)
        elif kind == "ruler":
            painter.setPen(QPen(QColor("#333333"), 1))
            painter.setBrush(QColor("#d8d8d8"))
            painter.drawRect(2, 8, 20, 8)
            for x in range(4, 21, 3):
                painter.drawLine(x, 8, x, 12 if x % 6 else 14)
        elif kind == "run_wafer":
            painter.setPen(QPen(QColor("#333333"), 1))
            painter.setBrush(QColor("#f0d040"))
            painter.drawRect(10, 2, 4, 5)
            flask = QPainterPath()
            flask.moveTo(8, 7)
            flask.lineTo(16, 7)
            flask.lineTo(20, 21)
            flask.lineTo(4, 21)
            flask.closeSubpath()
            painter.setBrush(QColor("#2fbe3a"))
            painter.drawPath(flask)
        elif kind == "review_wafer":
            painter.setPen(QPen(QColor("#146622"), 1.2))
            painter.setBrush(QColor("#3ad04a"))
            painter.drawEllipse(2, 2, 14, 14)
            painter.setPen(QPen(QColor("#1a3ea8"), 1))
            painter.setBrush(QColor("#3a62e0"))
            painter.drawEllipse(5, 5, 7, 7)
            painter.setPen(QPen(QColor("#333333"), 2))
            painter.drawLine(14, 14, 21, 21)
        elif kind == "wafermap_image":
            painter.setPen(QPen(QColor("#146622"), 1))
            painter.setBrush(QColor("#2fbe3a"))
            painter.drawEllipse(3, 3, 18, 18)
            painter.setPen(QPen(QColor("#1a4ad0"), 2))
            painter.drawLine(12, 10, 12, 17)
            painter.setBrush(QColor("#1a4ad0"))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(11, 6, 3, 3)
        elif kind == "wafermap_zoom":
            painter.setPen(QPen(QColor("#146622"), 1))
            painter.setBrush(QColor("#2fbe3a"))
            painter.drawEllipse(2, 2, 20, 20)
            painter.setPen(QPen(QColor("#ffffff"), 2))
            painter.drawLine(7, 12, 11, 16)
            painter.drawLine(11, 16, 17, 8)
        elif kind == "rotate_wafer":
            painter.setPen(QPen(QColor("#146622"), 1))
            painter.setBrush(QColor("#2fbe3a"))
            painter.drawEllipse(2, 2, 20, 20)
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor("#ffffff"), 1.8))
            painter.drawArc(6, 6, 12, 12, 45 * 16, 270 * 16)
            painter.setBrush(QColor("#ffffff"))
            painter.setPen(Qt.NoPen)
            painter.drawPolygon([self._point(16, 6), self._point(20, 8), self._point(15, 11)])
        painter.end()
        return self._color_icon(pixmap)

    def _color_icon(self, pixmap: QPixmap) -> QIcon:
        icon = QIcon()
        try:
            normal, disabled, off = QIcon.Mode.Normal, QIcon.Mode.Disabled, QIcon.State.Off
        except AttributeError:
            normal, disabled, off = QIcon.Normal, QIcon.Disabled, QIcon.Off
        icon.addPixmap(pixmap, normal, off)
        icon.addPixmap(pixmap, disabled, off)
        return icon

    def _alarm_alert_icon(self, active: bool) -> QIcon:
        pixmap, painter = self._blank_icon()
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 45))
        painter.drawPolygon([self._point(13, 5), self._point(23, 22), self._point(4, 22)])
        painter.setPen(QPen(QColor("#222222"), 1.2))
        painter.setBrush(QColor("#ffe14a") if active else QColor("#9a9a9a"))
        painter.drawPolygon([self._point(12, 2), self._point(22, 21), self._point(2, 21)])
        painter.setPen(QPen(QColor("#111111"), 2))
        painter.drawLine(12, 8, 12, 14)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#111111"))
        painter.drawEllipse(11, 16, 3, 3)
        painter.end()
        return self._color_icon(pixmap)

    @staticmethod
    def _point(x: int, y: int):
        try:
            from PySide6.QtCore import QPoint
        except ImportError:
            from PyQt5.QtCore import QPoint
        return QPoint(x, y)

    def _add_tool_button(self, toolbar: QToolBar, kind: str, tooltip: str, callback=None) -> QPushButton:
        button = QPushButton("")
        button.setIcon(self._toolbar_icon(kind))
        button.setIconSize(QSize(24, 24))
        button.setToolTip(tooltip)
        button.setFixedSize(32, 30)
        button.setStyleSheet(
            "QPushButton { background: #d7d4cc; border: 1px solid #6e6b64;"
            " border-top-color: #ffffff; border-left-color: #ffffff; padding: 1px; }"
            "QPushButton:pressed { background: #c8c4ba;"
            " border-top-color: #6e6b64; border-left-color: #6e6b64;"
            " border-right-color: #ffffff; border-bottom-color: #ffffff; }"
        )
        if callback is None:
            button.clicked.connect(lambda checked=False, text=tooltip: self._toolbar_status(text))
        else:
            button.clicked.connect(lambda checked=False, cb=callback: cb())
        button.toolbar_action = toolbar.addWidget(button)
        return button

    def _toolbar_status(self, text: str):
        self.statusBar().showMessage(text)

    def _current_toolbar_optics(self):
        return {
            "pixel_size": self.pixel_size_combo.currentText(),
            "imaging_mode": self.imaging_mode_combo.currentText(),
            "aperture": self.aperture_spin.value(),
            "automatic_light": self.automatic_light,
            "illumination_level": self.illumination_spin.value(),
            "focus_offset": self.focus_offset_spin.value(),
        }

    def _show_toolbar_button(self, button, visible: bool):
        button.setVisible(visible)
        action = getattr(button, "toolbar_action", None)
        if action is not None:
            action.setVisible(visible)

    def _sync_optics_button_visibility(self):
        engaged = bool(getattr(self, "optics_engaged", True))
        automatic = bool(getattr(self, "automatic_light", True))
        self._show_toolbar_button(self.disengage_optics_button, engaged)
        self._show_toolbar_button(self.engage_optics_button, not engaged)
        self._show_toolbar_button(self.manual_light_button, not automatic)
        self._show_toolbar_button(self.auto_light_button, automatic)

    def _set_optics_engaged(self, engaged: bool):
        self.optics_engaged = engaged
        self._sync_optics_button_visibility()
        self.apply_optics_button.setEnabled(not engaged)
        self._toolbar_status(
            "Optics engaged; toolbar changes apply immediately"
            if engaged
            else "Optics disengaged; click Apply Optics Settings to commit changes"
        )

    def _optics_control_changed(self, *args):
        if self.optics_engaged:
            self.optics_applied_settings = self._current_toolbar_optics()
            self._toolbar_status("Optics setting applied")
        else:
            self._toolbar_status("Optics setting pending; click Apply Optics Settings")

    def _apply_toolbar_optics(self):
        if self.optics_engaged:
            return
        self.optics_applied_settings = self._current_toolbar_optics()
        self._toolbar_status("Disengaged optics settings applied")

    def _set_automatic_light(self, automatic: bool):
        self.automatic_light = automatic
        self._sync_optics_button_visibility()
        self.illumination_spin.setEnabled(not automatic)
        if hasattr(self, "optics_applied_settings"):
            self._optics_control_changed()

    def _toggle_ruler(self):
        self.ruler_visible = self.ruler_button.isChecked()
        self._toolbar_status(f"Ruler {'ON' if self.ruler_visible else 'OFF'}")

    def _toggle_wafermap_image(self):
        if not self.wafermap_image_acquired:
            self.wafermap_image_button.setChecked(False)
            self._toolbar_status("Acquire a wafermap image before displaying it")
            return
        self.wafermap_image_visible = self.wafermap_image_button.isChecked()
        self._sync_wafermap_image_controls()
        self._toolbar_status(
            f"Wafermap image {'ON' if self.wafermap_image_visible else 'OFF'}"
        )

    def _set_navigation_bar_visible(self, visible: bool):
        if hasattr(self, "navigation_strip_widget"):
            self.navigation_strip_widget.setVisible(bool(visible))

    def _set_setup_toolbar_visible(self, visible: bool):
        visible = bool(visible) and self.setup_toolbar_user_visible
        if hasattr(self, "setup_toolbar_separator"):
            self.setup_toolbar_separator.setVisible(bool(visible))
        for action in getattr(self, "setup_toolbar_actions", []):
            action.setVisible(bool(visible))
        for widget in getattr(self, "setup_toolbar_widgets", []):
            widget.setVisible(bool(visible))

    def _set_setup_toolbar_user_visible(self, visible: bool):
        self.setup_toolbar_user_visible = bool(visible)
        self._set_setup_toolbar_visible(self._active_route_key != "home")

    def _set_toolbar_group_visible(self, group: str, visible: bool):
        for action in getattr(self, f"{group}_toolbar_actions", []):
            action.setVisible(bool(visible))
        for widget in getattr(self, f"{group}_toolbar_widgets", []):
            widget.setVisible(bool(visible))
        if group == "optics" and visible and hasattr(self, "disengage_optics_button"):
            self._sync_optics_button_visibility()

    def _set_status_bar_visible(self, visible: bool):
        if self.statusBar() is not None:
            self.statusBar().setVisible(bool(visible))

    def _set_review_toolbar_visible(self, visible: bool):
        self.review_toolbar_visible = bool(visible)
        for workspace in self.findChildren(ReviewWorkspace):
            workspace.set_review_toolbar_visible(visible)

    def _set_review_image_toolbar_visible(self, visible: bool):
        self.review_image_toolbar_visible = bool(visible)
        for workspace in self.findChildren(ReviewWorkspace):
            workspace.set_review_image_toolbar_visible(visible)

    def reset_wafermap_zoom(self):
        if hasattr(self, "wafermap_zoom_combo"):
            self.wafermap_zoom_combo.setCurrentText("100")
        self.statusBar().showMessage("Wafermap zoom reset to 100%", 4000)

    def acquire_wafermap_image(self):
        self.wafermap_image_acquired = True
        self.wafermap_image_visible = True
        self._sync_wafermap_image_controls()
        self.statusBar().showMessage("Wafermap MacroView image acquired and displayed", 4000)

    def toggle_wafermap_image_from_menu(self, checked=None):
        if not self.wafermap_image_acquired:
            self.wafermap_image_visible = False
            self._sync_wafermap_image_controls()
            self.statusBar().showMessage(
                "Acquire a wafermap image before displaying it",
                4000,
            )
            return
        self.wafermap_image_visible = (
            bool(checked)
            if isinstance(checked, bool)
            else not self.wafermap_image_visible
        )
        self._sync_wafermap_image_controls()
        self.statusBar().showMessage(
            f"Wafermap image {'ON' if self.wafermap_image_visible else 'OFF'}",
            4000,
        )

    def _sync_wafermap_image_controls(self):
        if hasattr(self, "wafermap_image_button"):
            self.wafermap_image_button.blockSignals(True)
            self.wafermap_image_button.setChecked(self.wafermap_image_visible)
            self.wafermap_image_button.blockSignals(False)
        if hasattr(self, "toggle_wafermap_image_action"):
            self.toggle_wafermap_image_action.blockSignals(True)
            self.toggle_wafermap_image_action.setEnabled(self.wafermap_image_acquired)
            self.toggle_wafermap_image_action.setChecked(self.wafermap_image_visible)
            self.toggle_wafermap_image_action.blockSignals(False)

    def _change_toolbar_magnification(self, direction: int):
        choices = []
        for index in range(self.pixel_size_combo.count()):
            text = self.pixel_size_combo.itemText(index)
            try:
                magnification = float(text.split("(", 1)[1].split("X", 1)[0])
            except (IndexError, ValueError):
                magnification = float(index)
            choices.append((magnification, index))
        choices.sort()
        current = self.pixel_size_combo.currentIndex()
        position = next((i for i, (_value, index) in enumerate(choices) if index == current), 0)
        position = max(0, min(len(choices) - 1, position + int(direction)))
        self.pixel_size_combo.setCurrentIndex(choices[position][1])

    def _install_global_optics_shortcuts(self):
        shortcuts = (
            ("F3", lambda: self._change_toolbar_magnification(1)),
            ("F4", lambda: self._change_toolbar_magnification(-1)),
            ("F5", lambda: self.illumination_spin.stepUp()),
            ("F6", lambda: self.illumination_spin.stepDown()),
            ("F7", lambda: self.focus_offset_spin.stepUp()),
            ("F8", lambda: self.focus_offset_spin.stepDown()),
        )
        self.global_optics_shortcuts = []
        for shortcut, callback in shortcuts:
            action = QAction(self)
            action.setShortcut(shortcut)
            action.triggered.connect(callback)
            self.addAction(action)
            self.global_optics_shortcuts.append(action)

    def print_current_view(self):
        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() != QDialog.Accepted:
            return
        snapshot = self.grab()
        painter = QPainter(printer)
        target = painter.viewport()
        scaled = snapshot.scaled(target.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        painter.drawPixmap(target.x(), target.y(), scaled)
        painter.end()
        self._toolbar_status("Current view sent to printer")

    def open_user_manual(self):
        manual_path = Path(__file__).resolve().parents[1] / "docs" / "OPERATOR_GUIDE.md"
        if not manual_path.exists():
            QMessageBox.warning(self, "User Manual", f"Operator guide not found:\n{manual_path}")
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(manual_path))):
            QMessageBox.warning(self, "User Manual", "Unable to open the operator guide.")

    def _show_home_view(self):
        self._activate_workspace_page("home")
        self.statusBar().showMessage("Main menu")

    def _show_setup_view(self):
        self._activate_workspace_page("setup")
        for name, section in self.recipe_overview_sections.items():
            section.set_expanded(name in {"Recipe Properties", "Wafer Layout"})
        self.overview_scroll.verticalScrollBar().setValue(0)
        self.overview_scroll.horizontalScrollBar().setValue(0)
        self.statusBar().showMessage("Main recipe overview")

    def _navigation_routes(self):
        return {
            "home": ("Home", None, self._show_home_view),
            "setup": ("Setup", "home", self._show_setup_view),
            "select_inspection": ("Select Inspection", "setup", self.open_inspection_recipe),
            "inspection_properties": (
                "Inspection Properties", "setup", self.open_inspection_properties,
            ),
            "wafer": ("Wafer", "setup", self._show_wafer_level),
            "wafer_properties": ("Wafer Properties", "wafer", self.open_wafer_properties),
            "alignment": ("Alignment", "wafer", self.open_alignment_menu),
            "registration_sites": (
                "Registration Sites", "wafer", self.open_registration_site_library,
            ),
            "wafer_map": ("Wafer Map", "wafer", self.open_wafer_map),
            "select_defect_data": (
                "Select Defect Data", "wafer", self.open_select_defect_data,
            ),
            "tests": ("Tests", "setup", self.open_tests_setup),
            "test_fourier_filter": (
                "Fourier Filter", "tests",
                lambda: self.open_tests_setup(initial_module="fourier_filter"),
            ),
            "test_light_level": (
                "Light Level", "tests",
                lambda: self.open_tests_setup(initial_module="light_level"),
            ),
            "test_sensitivity": (
                "Sensitivity", "tests",
                lambda: self.open_tests_setup(initial_module="sensitivity"),
            ),
            "test_defect_filters": (
                "Defect Filters", "tests",
                lambda: self.open_tests_setup(initial_module="defect_filters"),
            ),
            "test_care_areas": (
                "Care Areas", "tests",
                lambda: self.open_tests_setup(initial_module="care_areas"),
            ),
            "test_sample_plan": (
                "Sample Plan", "tests",
                lambda: self.open_tests_setup(initial_module="sample_plan"),
            ),
            "lot_plan": ("Lot Plan", "setup", self.open_lot_plan),
            "wafer_post_processing": (
                "Wafer Post Processing", "setup", self.open_wafer_post_processing,
            ),
            "setup_run": ("Setup Run", "setup", self.open_run_one_wafer),
            "recipe_generation": (
                "Recipe Generation", "setup", self.open_recipe_generation,
            ),
        }

    def _navigate_to(self, route_key: str, *, record: bool = True):
        if route_key == "select_inspection":
            return self.open_inspection_recipe()
        if route_key == "home" and self._active_route_key != "home":
            answer = QMessageBox.question(
                self,
                "End Setup",
                "Exit the current Set Up session and return to the Main Menu?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return False
        if getattr(self, "_wafer_drawer_open", False):
            self._set_wafer_drawer_expanded(False)
        routes = self._navigation_routes()
        if route_key not in routes:
            return
        previous_route = self._active_route_key
        history_appended = False
        if record:
            self._navigation_history = self._navigation_history[: self._navigation_index + 1]
            if self._navigation_history[-1] != route_key:
                self._navigation_history.append(route_key)
                self._navigation_index = len(self._navigation_history) - 1
                history_appended = True
        self._update_navigation_strip(route_key)
        if route_key in {"home", "setup"}:
            routes[route_key][2]()
            return self.workspace_pages[route_key]
        if self._activate_workspace_page(route_key):
            return self.workspace_pages[route_key]
        result = routes[route_key][2]()
        if result is False:
            if history_appended:
                self._navigation_history.pop()
                self._navigation_index = len(self._navigation_history) - 1
            self._activate_workspace_page(previous_route)
            self._update_navigation_strip(previous_route)
        return result

    def _activate_workspace_page(self, route_key: str) -> bool:
        if not hasattr(self, "workspace_pages"):
            return False
        page = self.workspace_pages.get(route_key)
        if page is None:
            return False
        if isinstance(page, TestsSetupDialog):
            page._refresh_external_wafer_context()
        self.workspace_stack.setCurrentWidget(page)
        page.show()
        self._active_route_key = route_key
        if hasattr(self, "left_navigation"):
            self.left_navigation.setVisible(route_key != "home")
        self._set_setup_toolbar_visible(route_key != "home")
        self._update_wafer_drawer_selection(route_key)
        return True

    def _show_workspace_dialog(
        self,
        route_key: str,
        dialog: QDialog,
        *,
        on_accept=None,
        on_reject=None,
        return_route: str | None = None,
    ):
        existing = self.workspace_pages.get(route_key)
        if existing is not None and existing is not dialog:
            self.workspace_stack.removeWidget(existing)
            existing.deleteLater()

        dialog.setParent(self.workspace_stack)
        dialog.setWindowFlags(Qt.Widget)
        dialog.setMinimumSize(0, 0)
        dialog.setMaximumSize(16777215, 16777215)
        dialog.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.workspace_pages[route_key] = dialog
        self.workspace_stack.addWidget(dialog)
        self.workspace_stack.setCurrentWidget(dialog)
        self._active_route_key = route_key

        completed = {"value": False}

        def finish_page(result):
            if completed["value"]:
                return
            completed["value"] = True
            accepted = result == QDialog.Accepted
            callback = on_accept if accepted else on_reject
            next_route = callback(dialog) if callback else None
            if self.workspace_pages.get(route_key) is dialog:
                self.workspace_pages.pop(route_key, None)
            self.workspace_stack.removeWidget(dialog)
            dialog.setParent(None)
            dialog.deleteLater()
            target = next_route or return_route
            if target is None:
                target = self._navigation_routes().get(route_key, (None, "setup", None))[1]
            self._navigate_to(target or "setup")

        dialog.finished.connect(finish_page)
        dialog.show()
        dialog.setFocus()
        return dialog

    def _navigate_history(self, offset: int):
        target = self._navigation_index + offset
        if target < 0 or target >= len(self._navigation_history):
            return
        previous = self._navigation_index
        self._navigation_index = target
        result = self._navigate_to(self._navigation_history[target], record=False)
        if result is False:
            self._navigation_index = previous
            self._update_navigation_strip(self._navigation_history[previous])

    def _update_navigation_strip(self, route_key: str | None = None):
        if not hasattr(self, "back_button"):
            return
        route_key = route_key or self._navigation_history[self._navigation_index]
        if hasattr(self, "copy_test_action"):
            tests_active = route_key == "tests"
            self.copy_test_action.setEnabled(tests_active)
            page = self.workspace_pages.get("tests") if hasattr(self, "workspace_pages") else None
            self.paste_test_action.setEnabled(
                tests_active
                and isinstance(page, TestsSetupDialog)
                and page.test_clipboard is not None
            )
            self.copy_sample_plan_action.setEnabled(tests_active)
            self.paste_sample_plan_action.setEnabled(
                tests_active
                and isinstance(page, TestsSetupDialog)
                and page.sample_plan_clipboard is not None
            )
        self.home_button.setChecked(route_key == "home")
        self._rebuild_breadcrumb(route_key)
        self.back_button.setEnabled(self._navigation_index > 0)
        self.forward_button.setEnabled(
            self._navigation_index < len(self._navigation_history) - 1
        )
        self.back_button.setIcon(self._nav_arrow_icon("left", self.back_button.isEnabled()))
        self.forward_button.setIcon(self._nav_arrow_icon("right", self.forward_button.isEnabled()))
        self.back_button.setToolTip(
            "Navigate back in history of the visited views."
            if self.back_button.isEnabled()
            else "No previous view"
        )
        self.forward_button.setToolTip(
            "Previous: navigate forward in history of the visited views."
            if self.forward_button.isEnabled()
            else "No next view in navigation history"
        )
        self._sync_left_nav_selection(route_key)

    def _left_nav_key_for_route(self, route_key: str) -> str | None:
        if route_key in {"wafer", "wafer_properties", "alignment", "registration_sites", "wafer_map", "select_defect_data"}:
            return "wafer"
        if route_key == "tests" or route_key.startswith("test_"):
            return "tests"
        if route_key in {"lot_plan", "wafer_post_processing", "setup_run", "recipe_generation", "select_inspection"}:
            return route_key
        return None

    def _sync_left_nav_selection(self, route_key: str | None = None):
        if not hasattr(self, "left_nav_buttons"):
            return
        route_key = route_key or self._active_route_key
        selected = self._left_nav_key_for_route(route_key)
        if getattr(self, "_wafer_drawer_open", False):
            selected = "wafer"
        for key, button in self.left_nav_buttons.items():
            button.setChecked(key == selected)

    def _breadcrumb_chain(self, route_key: str):
        routes = self._navigation_routes()
        chain = []
        seen = set()
        key = route_key
        while key and key != "home" and key not in seen and key in routes:
            seen.add(key)
            label, parent, _handler = routes[key]
            chain.append((key, label))
            key = parent
        chain.reverse()
        return chain

    def _rebuild_breadcrumb(self, route_key: str):
        if not hasattr(self, "context_navigation_layout"):
            return
        kept = {self.setup_breadcrumb, self.parent_breadcrumb, self.current_view_label}
        while self.context_navigation_layout.count():
            item = self.context_navigation_layout.takeAt(0)
            widget = item.widget()
            if widget is not None and widget not in kept:
                widget.deleteLater()
        chain = self._breadcrumb_chain(route_key)
        used = []
        for index, (key, label) in enumerate(chain):
            leaf = index == len(chain) - 1
            if key == "setup":
                button = self.setup_breadcrumb
            elif leaf:
                button = self.current_view_label
            else:
                button = self.parent_breadcrumb
            button.setText(label)
            button.setProperty("routeKey", key)
            button.setChecked(leaf)
            button.setToolTip("Current menu" if leaf else f"Go to {label}")
            used.append(button)
        for button in kept:
            if button not in used:
                button.hide()
                button.setChecked(False)
        self.context_navigation.setVisible(bool(used))
        for index, button in enumerate(used):
            if index:
                self.context_navigation_layout.addWidget(self._breadcrumb_chevron())
            self.context_navigation_layout.addWidget(button)
            button.show()

    def _breadcrumb_chevron(self) -> QLabel:
        chevron = QLabel()
        chevron.setPixmap(self._nav_arrow_icon("right").pixmap(QSize(8, 8)))
        chevron.setFixedSize(12, 20)
        chevron.setAlignment(Qt.AlignCenter)
        return chevron

    def _open_parent_breadcrumb(self):
        route_key = self.parent_breadcrumb.property("routeKey")
        if route_key:
            self._navigate_to(str(route_key))

    def _open_breadcrumb_target(self):
        button = self.sender()
        route_key = button.property("routeKey") if button is not None else None
        if route_key:
            self._navigate_to(str(route_key))

    def _open_navigate_menu(self):
        self.statusBar().showMessage("Navigate is not available yet.", 3000)

    def _nav_arrow_icon(self, direction: str, enabled: bool = True) -> QIcon:
        pixmap = QPixmap(12, 12)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#222222" if enabled else "#8a8a8a"))
        if direction == "left":
            points = [(2, 6), (10, 1), (10, 11)]
        elif direction == "down":
            points = [(6, 10), (1, 3), (11, 3)]
        else:
            points = [(10, 6), (2, 1), (2, 11)]
        path = QPainterPath()
        path.moveTo(*points[0])
        path.lineTo(*points[1])
        path.lineTo(*points[2])
        path.closeSubpath()
        painter.drawPath(path)
        painter.end()
        return QIcon(pixmap)

    def _nav_home_icon(self) -> QIcon:
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor("#222222"), 1.1))
        painter.setBrush(QColor("#f7f4ee"))
        roof = QPainterPath()
        roof.moveTo(8, 1.5)
        roof.lineTo(14.5, 7.5)
        roof.lineTo(1.5, 7.5)
        roof.closeSubpath()
        painter.drawPath(roof)
        painter.setBrush(QColor("#f7f4ee"))
        painter.drawRect(4, 7, 8, 7)
        painter.setBrush(QColor("#222222"))
        painter.setPen(Qt.NoPen)
        painter.drawRect(7, 10, 2, 4)
        painter.end()
        return QIcon(pixmap)

    def _build_toolbar(self):
        toolbar = QToolBar("Toolbar")
        self.main_toolbar = toolbar
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        standard_buttons = [
            self._add_tool_button(
                toolbar,
                "wafer_handling",
                "Wafer and Cassette Handling: load and unload cassettes and wafers.",
                self.open_wafer_handling,
            ),
            self._add_tool_button(
                toolbar,
                "job_queue",
                "Inspection Job Queue: add, remove, edit, start, or stop jobs, and view the job run log.",
                self.open_job_queue,
            ),
            self._add_tool_button(
                toolbar,
                "print",
                "Print View: print the current view. The Print dialog sets up printer output.",
                self.print_current_view,
            ),
            self._add_tool_button(
                toolbar,
                "manual",
                "User Manual: open the software user manual.",
                self.open_user_manual,
            ),
        ]
        self.alarm_button = self._add_tool_button(
            toolbar,
            "alarm",
            "Alarm Alert: open interlock and alarm status. No active alarms.",
            self.open_alarm_center,
        )
        standard_buttons.append(self.alarm_button)
        self.alarm_button.setEnabled(True)
        self.standard_toolbar_separator = toolbar.addSeparator()
        self.standard_toolbar_actions = [
            *(button.toolbar_action for button in standard_buttons),
            self.standard_toolbar_separator,
        ]
        self.standard_toolbar_widgets = list(standard_buttons)

        self.disengage_optics_button = self._add_tool_button(
            toolbar,
            "disengage_optics",
            "Disengage Optics: toolbar changes apply immediately. Click to disengage optics.",
            lambda: self._set_optics_engaged(False),
        )
        self.engage_optics_button = self._add_tool_button(
            toolbar,
            "engage_optics",
            "Engage Optics: changes wait until Apply Optics Settings is pressed.",
            lambda: self._set_optics_engaged(True),
        )
        self.apply_optics_button = self._add_tool_button(
            toolbar,
            "apply_optics",
            "Apply Optics Settings: apply the pending optics changes together.",
            self._apply_toolbar_optics,
        )
        self.pixel_size_button = self._add_tool_button(
            toolbar, "pixel_size", "Pixel Size: select a pixel size for the inspection.", lambda: self.pixel_size_combo.setFocus()
        )
        self.pixel_size_combo = QComboBox()
        self.pixel_size_combo.addItems(["2.000 (5X)", "1.000 (2.5X)", "4.000 (10X)"])
        self.pixel_size_combo.setFixedWidth(104)
        self.pixel_size_combo.setToolTip("Pixel Size")
        self.pixel_size_combo_action = toolbar.addWidget(self.pixel_size_combo)

        self.imaging_mode_button = self._add_tool_button(
            toolbar,
            "imaging_mode",
            "Imaging Mode: select Darkfield or Brightfield.",
            lambda: self.imaging_mode_combo.setFocus(),
        )
        self.imaging_mode_combo = QComboBox()
        self.imaging_mode_combo.addItems(["BrightField", "DarkField"])
        self.imaging_mode_combo.setFixedWidth(118)
        self.imaging_mode_combo.setToolTip("Imaging Mode")
        self.imaging_mode_combo_action = toolbar.addWidget(self.imaging_mode_combo)

        self.aperture_button = self._add_tool_button(
            toolbar, "aperture", "Aperture: adjust the amount of light.", lambda: self.aperture_spin.setFocus()
        )
        self.aperture_spin = QSpinBox()
        self.aperture_spin.setRange(0, 100)
        self.aperture_spin.setValue(20)
        self.aperture_spin.setSuffix(" %")
        self.aperture_spin.setFixedWidth(72)
        self.aperture_spin.setToolTip("Aperture")
        self.aperture_spin_action = toolbar.addWidget(self.aperture_spin)

        self.illumination_button = self._add_tool_button(
            toolbar,
            "illumination",
            "Illumination Level: manual or automatic light-level selection.",
            lambda: self.illumination_spin.setFocus(),
        )
        self.manual_light_button = self._add_tool_button(
            toolbar,
            "manual_light",
            "Manual Light Activated: click to switch the light to automatic.",
            lambda: self._set_automatic_light(True),
        )
        self.auto_light_button = self._add_tool_button(
            toolbar,
            "auto_light",
            "Automatic Light Activated: the light-level menu is disabled. Click to allow manual light setting.",
            lambda: self._set_automatic_light(False),
        )
        self.illumination_spin = QSpinBox()
        self.illumination_spin.setRange(0, 255)
        self.illumination_spin.setValue(100)
        self.illumination_spin.setFixedWidth(52)
        self.illumination_spin.setToolTip("Illumination Level")
        self.illumination_spin_action = toolbar.addWidget(self.illumination_spin)
        self.focus_offset_button = self._add_tool_button(
            toolbar,
            "focus_offset",
            "Focus Offset: set the focus offset. The default is 0.000 μm.",
            lambda: self.focus_offset_spin.setFocus(),
        )
        self.focus_offset_spin = QDoubleSpinBox()
        self.focus_offset_spin.setDecimals(3)
        self.focus_offset_spin.setRange(-1000, 1000)
        self.focus_offset_spin.setSingleStep(1)
        self.focus_offset_spin.setValue(0)
        self.focus_offset_spin.setSuffix(" μm")
        self.focus_offset_spin.setFixedWidth(84)
        self.focus_offset_spin.setToolTip("Focus Offset")
        self.focus_offset_spin_action = toolbar.addWidget(self.focus_offset_spin)
        self.advanced_optics_button = self._add_tool_button(
            toolbar, "advanced_optics", "Advanced Optics Settings: open the advanced optics dialog.", self.open_review_optics
        )
        self.ruler_button = self._add_tool_button(
            toolbar, "ruler", "Ruler: turn the ruler on or off in the boundary box display.", self._toggle_ruler
        )
        self.ruler_button.setCheckable(True)

        optics_buttons = [
            self.disengage_optics_button,
            self.engage_optics_button,
            self.apply_optics_button,
            self.pixel_size_button,
            self.imaging_mode_button,
            self.aperture_button,
            self.illumination_button,
            self.manual_light_button,
            self.auto_light_button,
            self.focus_offset_button,
            self.advanced_optics_button,
            self.ruler_button,
        ]
        self.optics_toolbar_actions = [
            *(button.toolbar_action for button in optics_buttons),
            self.pixel_size_combo_action,
            self.imaging_mode_combo_action,
            self.aperture_spin_action,
            self.illumination_spin_action,
            self.focus_offset_spin_action,
        ]
        self.optics_toolbar_widgets = [
            *optics_buttons,
            self.pixel_size_combo,
            self.imaging_mode_combo,
            self.aperture_spin,
            self.illumination_spin,
            self.focus_offset_spin,
        ]

        self.setup_toolbar_separator = toolbar.addSeparator()
        self.run_wafer_button = self._add_tool_button(
            toolbar,
            "run_wafer",
            "Run One Wafer: open the lot plan, select tests, and run one wafer.",
            self.open_run_one_wafer,
        )
        self.review_wafer_button = self._add_tool_button(
            toolbar,
            "review_wafer",
            "Review Wafer: review, sort, and classify defects for a wafer that just finished.",
            self.open_review_results,
        )
        self.wafermap_image_button = self._add_tool_button(
            toolbar,
            "wafermap_image",
            "Toggle Wafermap Image: turn the MacroView background on or off.",
            self._toggle_wafermap_image,
        )
        self.wafermap_image_button.setCheckable(True)
        self.wafermap_image_button.setEnabled(True)
        self.wafermap_zoom_button = self._add_tool_button(
            toolbar,
            "wafermap_zoom",
            "Wafermap Zoom: reset the wafermap zoom to 100%.",
            self.reset_wafermap_zoom,
        )

        self.wafermap_zoom_combo = QComboBox()
        self.wafermap_zoom_combo.addItems(["100", "75", "50", "25"])
        self.wafermap_zoom_combo.setFixedWidth(66)
        self.wafermap_zoom_combo.setToolTip("Wafermap Zoom")
        self.wafermap_zoom_combo_action = toolbar.addWidget(self.wafermap_zoom_combo)
        self.rotate_wafer_button = self._add_tool_button(
            toolbar,
            "rotate_wafer",
            "Rotate Wafer: rotate the wafer to the specified test orientation.",
            self.open_wafer_handling,
        )
        self.setup_toolbar_actions = [
            self.run_wafer_button.toolbar_action,
            self.review_wafer_button.toolbar_action,
            self.wafermap_image_button.toolbar_action,
            self.wafermap_zoom_button.toolbar_action,
            self.wafermap_zoom_combo_action,
            self.rotate_wafer_button.toolbar_action,
        ]
        self.setup_toolbar_widgets = [
            self.run_wafer_button,
            self.review_wafer_button,
            self.wafermap_image_button,
            self.wafermap_zoom_button,
            self.wafermap_zoom_combo,
            self.rotate_wafer_button,
        ]

        for control in (
            self.pixel_size_combo,
            self.imaging_mode_combo,
            self.aperture_spin,
            self.illumination_spin,
            self.focus_offset_spin,
        ):
            if isinstance(control, QComboBox):
                control.currentTextChanged.connect(self._optics_control_changed)
            else:
                control.valueChanged.connect(self._optics_control_changed)
        self._set_automatic_light(True)
        self._set_optics_engaged(True)
        self.optics_applied_settings = self._current_toolbar_optics()
        self._install_global_optics_shortcuts()

    def _build_central(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)

        main_layout = QVBoxLayout(root)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.navigation_strip_widget = self._navigation_strip()
        main_layout.addWidget(self.navigation_strip_widget)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        self.left_navigation = self._left_navigation()
        body.addWidget(self.left_navigation)
        body.addWidget(self._wafer_navigation_drawer())
        self.overview_scroll = QScrollArea()
        self.overview_scroll.setWidgetResizable(True)
        self.overview_scroll.setFrameShape(QFrame.NoFrame)
        self.overview_scroll.setWidget(self._recipe_overview())
        self.home_page = self._main_menu_home()
        self.workspace_stack = QStackedWidget()
        self.workspace_stack.setObjectName("workspaceStack")
        self.workspace_stack.addWidget(self.home_page)
        self.workspace_stack.addWidget(self.overview_scroll)
        self.workspace_pages = {
            "home": self.home_page,
            "setup": self.overview_scroll,
        }
        self.workspace_stack.setCurrentWidget(self.home_page)
        body.addWidget(self.workspace_stack, 1)
        main_layout.addLayout(body, 1)

    def _navigation_strip(self) -> QWidget:
        strip = QFrame()
        strip.setObjectName("navigationBar")
        strip.setFixedHeight(32)
        strip.setStyleSheet(
            """
            QFrame#navigationBar {
                background: #8d8d8d;
                border: 1px solid #111111;
            }
            QFrame#navigationBar QPushButton {
                background: #e6e1d6;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #6d6a62;
                border-bottom: 1px solid #6d6a62;
                color: #1a1a1a;
                padding: 0px 8px;
                min-height: 20px;
            }
            QFrame#navigationBar QPushButton:checked {
                background: #f6f3ec;
                border-bottom: 1px solid #2f2f2f;
            }
            QFrame#navigationBar QPushButton:disabled {
                color: #7d7d7d;
            }
            QFrame#navigationBar QLabel {
                background: transparent;
                border: none;
            }
            QFrame#navSeparator {
                background: #5c5c5c;
                border: 1px solid #3c3c3c;
            }
            """
        )
        layout = QHBoxLayout(strip)
        layout.setContentsMargins(4, 3, 6, 3)
        layout.setSpacing(3)

        self.back_button = QPushButton("Back")
        self.back_button.setIcon(self._nav_arrow_icon("left", False))
        self.back_button.setIconSize(QSize(10, 10))
        self.back_button.clicked.connect(lambda: self._navigate_history(-1))
        layout.addWidget(self.back_button)

        self.forward_button = QPushButton()
        self.forward_button.setAccessibleName("Previous")
        self.forward_button.setIcon(self._nav_arrow_icon("right", False))
        self.forward_button.setIconSize(QSize(10, 10))
        self.forward_button.setFixedSize(26, 22)
        self.forward_button.clicked.connect(lambda: self._navigate_history(1))
        layout.addWidget(self.forward_button)

        separator = QFrame()
        separator.setObjectName("navSeparator")
        separator.setFixedSize(8, 22)
        layout.addWidget(separator)

        self.home_button = QPushButton()
        self.home_button.setIcon(self._nav_home_icon())
        self.home_button.setIconSize(QSize(16, 16))
        self.home_button.setFixedSize(26, 22)
        self.home_button.setCheckable(True)
        self.home_button.setToolTip("Return to the Main menu")
        self.home_button.clicked.connect(lambda: self._navigate_to("home"))
        layout.addWidget(self.home_button)

        self.setup_breadcrumb = QPushButton("Setup")
        self.setup_breadcrumb.setCheckable(True)
        self.setup_breadcrumb.setProperty("routeKey", "setup")
        self.setup_breadcrumb.clicked.connect(self._open_breadcrumb_target)
        self.parent_breadcrumb = QPushButton()
        self.parent_breadcrumb.setCheckable(True)
        self.parent_breadcrumb.clicked.connect(self._open_breadcrumb_target)
        self.parent_breadcrumb.hide()
        self.current_view_label = QPushButton()
        self.current_view_label.setCheckable(True)
        self.current_view_label.setToolTip("Current menu")
        self.current_view_label.clicked.connect(self._open_breadcrumb_target)
        self.current_view_label.hide()

        self.context_navigation = QWidget()
        self.context_navigation_layout = QHBoxLayout(self.context_navigation)
        self.context_navigation_layout.setContentsMargins(2, 0, 2, 0)
        self.context_navigation_layout.setSpacing(2)
        self.context_navigation.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        self.context_navigation.hide()
        layout.addWidget(self.context_navigation)
        layout.addStretch(1)

        self.navigate_button = QPushButton("Navigate")
        self.navigate_button.setIcon(self._nav_arrow_icon("down"))
        self.navigate_button.setIconSize(QSize(10, 10))
        self.navigate_button.setToolTip("Navigate")
        self.navigate_button.clicked.connect(self._open_navigate_menu)
        layout.addWidget(self.navigate_button)

        self.configure_button = QPushButton("Configure", strip)
        self.configure_button.setToolTip("Select visible Recipe Overview parameters")
        self.configure_button.clicked.connect(self._configure_recipe_overview)
        self.configure_button.hide()

        self._update_navigation_strip("home")
        return strip

    def _configure_recipe_overview(self):
        if self._active_route_key != "setup":
            self._navigate_to("setup")
        self.configure_recipe_overview()

    def _left_navigation(self) -> QWidget:
        panel = QFrame()
        panel.setFixedWidth(148)
        panel.setStyleSheet(
            """
            QFrame {
                background: #cfcbc2;
                border-right: 2px solid #77746c;
            }
            """
        )
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 14, 6, 12)
        layout.setSpacing(8)

        items = [
            ("Select\nInspection", False, True, "select_inspection"),
            ("Wafer", True, True, "wafer"),
            ("Tests", True, True, "tests"),
            ("Lot Plan", False, True, "lot_plan"),
            ("Wafer Post\nProcessing", False, True, "wafer_post_processing"),
            ("Setup Run", True, True, "setup_run"),
            ("Save\nInspection", False, True, None),
            ("Recipe Generation", False, True, "recipe_generation"),
        ]
        self.left_nav_buttons = {}
        for label, arrow, enabled, route_key in items:
            button = ClassicButton(label)
            button.setEnabled(enabled)
            button.setFocusPolicy(Qt.NoFocus)
            button.setCheckable(route_key is not None)
            if route_key == "wafer":
                button.clicked.connect(self.open_wafer_menu)
                self.wafer_button = button
            elif route_key == "recipe_generation":
                button.clicked.connect(self.open_recipe_generation)
            elif route_key:
                button.clicked.connect(
                    lambda checked=False, key=route_key: self._navigate_to(key)
                )
            elif label == "Save\nInspection":
                button.clicked.connect(self.save_inspection)
            if route_key:
                self.left_nav_buttons[route_key] = button
            if label == "Tests":
                self.tests_button = button
            if label == "Lot Plan":
                self.lot_plan_button = button
            if label == "Wafer Post\nProcessing":
                self.wafer_post_processing_button = button
            if label == "Setup Run":
                self.setup_run_button = button
            if label == "Save\nInspection":
                self.save_inspection_button = button
            layout.addWidget(SubmenuButtonRow(button, arrow))

        layout.addStretch(1)
        end = ClassicButton("End")
        end.setFixedHeight(40)
        end.setToolTip("Close current menu")
        end.clicked.connect(lambda: self._navigate_to("home"))
        self.end_button = end
        layout.addWidget(SubmenuButtonRow(end))
        return panel

    def _wafer_navigation_drawer(self) -> QWidget:
        drawer = QFrame()
        drawer.setObjectName("waferNavigationDrawer")
        drawer.setMinimumWidth(0)
        drawer.setMaximumWidth(0)
        drawer.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        drawer.setStyleSheet(
            """
            QFrame#waferNavigationDrawer {
                background: #e2dfd7;
                border-right: 1px solid #8a867e;
            }
            QLabel#waferDrawerTitle {
                color: #222222;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton#waferDrawerClose {
                background: transparent;
                border: 0;
                padding: 2px;
            }
            QPushButton#waferDrawerClose:hover {
                background: #cbc7bd;
            }
            QPushButton[drawerRoute="true"] {
                background: #d7d4cc;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                color: #111111;
                min-height: 42px;
                padding: 4px 14px;
                text-align: left;
                font-size: 10px;
                font-weight: 600;
            }
            QPushButton[drawerRoute="true"]:hover {
                background: #f0eee7;
            }
            QPushButton[drawerRoute="true"]:checked {
                background: #f7f5ee;
                border-left: 3px solid #c58e00;
            }
            """
        )

        layout = QVBoxLayout(drawer)
        layout.setContentsMargins(14, 14, 14, 12)
        layout.setSpacing(9)
        header = QHBoxLayout()
        title = QLabel("Wafer Setup")
        title.setObjectName("waferDrawerTitle")
        header.addWidget(title)
        header.addStretch(1)
        close_button = QPushButton()
        close_button.setObjectName("waferDrawerClose")
        close_button.setIcon(self.style().standardIcon(QStyle.SP_TitleBarCloseButton))
        close_button.setToolTip("Close Wafer menu")
        close_button.setFixedSize(24, 24)
        close_button.clicked.connect(lambda: self._set_wafer_drawer_expanded(False))
        header.addWidget(close_button)
        layout.addLayout(header)

        self.wafer_drawer_buttons = {}
        for label, route_key in (
            ("Wafer Properties", "wafer_properties"),
            ("Alignment", "alignment"),
            ("Wafer Map", "wafer_map"),
            ("Select Defect Data", "select_defect_data"),
        ):
            button = QPushButton(f"{label}    >")
            button.setProperty("drawerRoute", True)
            button.setCheckable(True)
            button.setToolTip(f"Open {label} in the main workspace")
            button.clicked.connect(
                lambda checked=False, key=route_key: self._open_wafer_drawer_route(key)
            )
            self.wafer_drawer_buttons[route_key] = button
            layout.addWidget(button)
        layout.addStretch(1)

        self._wafer_drawer_open = False
        self.wafer_drawer = drawer
        self.wafer_drawer_animation = QPropertyAnimation(drawer, b"maximumWidth", self)
        self.wafer_drawer_animation.setDuration(180)
        self.wafer_drawer_animation.setEasingCurve(QEasingCurve.OutCubic)
        self.wafer_drawer_animation.finished.connect(self._finish_wafer_drawer_animation)
        drawer.hide()
        return drawer

    def _open_wafer_drawer_route(self, route_key: str):
        self._set_wafer_drawer_expanded(False)
        self._navigate_to(route_key)

    def _update_wafer_drawer_selection(self, route_key: str):
        for key, button in getattr(self, "wafer_drawer_buttons", {}).items():
            button.setChecked(key == route_key)

    def _set_wafer_drawer_expanded(self, expanded: bool):
        if not hasattr(self, "wafer_drawer"):
            return
        self._wafer_drawer_open = bool(expanded)
        self._sync_left_nav_selection()
        self._update_wafer_drawer_selection(self._active_route_key)
        self.wafer_drawer_animation.stop()
        if expanded:
            self.wafer_drawer.show()
        self.wafer_drawer_animation.setStartValue(self.wafer_drawer.maximumWidth())
        self.wafer_drawer_animation.setEndValue(246 if expanded else 0)
        self.wafer_drawer_animation.start()

    def _finish_wafer_drawer_animation(self):
        if not self._wafer_drawer_open:
            self.wafer_drawer.hide()

    def _main_menu_home(self) -> QWidget:
        page = QWidget()
        page.setObjectName("mainMenuHome")
        page.setStyleSheet(
            """
            QWidget#mainMenuHome {
                background: #eeece6;
            }
            QLabel#mainMenuTitle {
                color: #111111;
                font-size: 18px;
                font-weight: 700;
            }
            QLabel#mainMenuSectionTitle {
                color: #222222;
                font-size: 11px;
                font-weight: 700;
                text-decoration: underline;
            }
            QFrame#homeCommandBand {
                background: #d4d1c8;
                border-top: 1px solid #ffffff;
                border-bottom: 1px solid #8a867e;
            }
            QPushButton[homeCommand="true"] {
                background: #e1ded6;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-width: 180px;
                min-height: 54px;
                padding: 4px 16px;
                text-align: left;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton[homeCommand="true"]:hover {
                background: #f7f5ee;
                border-left: 3px solid #c58e00;
            }
            QFrame#homeStatusBand {
                background: #f4f2ed;
                border-top: 1px solid #aaa69d;
                border-bottom: 1px solid #aaa69d;
            }
            QLabel[homeValue="true"] {
                font-weight: 600;
            }
            """
        )
        root = QVBoxLayout(page)
        root.setContentsMargins(28, 22, 28, 24)
        root.setSpacing(16)

        title = QLabel("Main Menu")
        title.setObjectName("mainMenuTitle")
        root.addWidget(title)

        commands = QFrame()
        commands.setObjectName("homeCommandBand")
        command_layout = QHBoxLayout(commands)
        command_layout.setContentsMargins(18, 16, 18, 16)
        command_layout.setSpacing(12)

        setup = QPushButton("Set Up")
        setup.setProperty("homeCommand", True)
        setup.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        setup.setToolTip("Select, set up, or modify an inspection recipe")
        setup.clicked.connect(lambda: self._navigate_to("setup"))
        command_layout.addWidget(setup)

        run = QPushButton("Run")
        run.setProperty("homeCommand", True)
        run.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        run.setToolTip("Open the inspection job queue")
        run.clicked.connect(self.open_job_queue)
        command_layout.addWidget(run)

        review = QPushButton("Review")
        review.setProperty("homeCommand", True)
        review.setIcon(self.style().standardIcon(QStyle.SP_FileDialogContentsView))
        review.setToolTip("Select and review inspection results")
        review.clicked.connect(self.open_review_results)
        command_layout.addWidget(review)

        utilities = QPushButton("Utilities")
        utilities.setProperty("homeCommand", True)
        utilities.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        utilities.setToolTip("Open system utility functions")
        utilities_menu = QMenu(utilities)
        utilities_menu.addAction("Initialize System...", self.open_initialize_system)
        utilities_menu.addAction("Communication Status...", self.open_communication_status)
        utilities_menu.addAction("Equipment Constants...", self.open_equipment_constants)
        utilities_menu.addAction("System Log", lambda: self.open_system_log("System"))
        utilities_menu.addAction("User Preferences...", self.open_user_preferences)
        utilities.setMenu(utilities_menu)
        command_layout.addWidget(utilities)
        command_layout.addStretch(1)
        root.addWidget(commands)

        status_title = QLabel("Current Inspection")
        status_title.setObjectName("mainMenuSectionTitle")
        root.addWidget(status_title)
        status_band = QFrame()
        status_band.setObjectName("homeStatusBand")
        status_layout = QGridLayout(status_band)
        status_layout.setContentsMargins(18, 14, 18, 14)
        status_layout.setHorizontalSpacing(12)
        status_layout.setVerticalSpacing(8)
        self.home_status_labels = {}
        for row, (label, key) in enumerate(
            (
                ("Inspection", "inspection"),
                ("Device", "device"),
                ("Process Step", "step"),
                ("Recipe Status", "recipe_status"),
                ("Wafer State", "wafer_state"),
                ("Stored Results", "results"),
            )
        ):
            status_layout.addWidget(QLabel(f"{label}:"), row, 0)
            value = QLabel("-")
            value.setProperty("homeValue", True)
            self.home_status_labels[key] = value
            status_layout.addWidget(value, row, 1)
        status_layout.setColumnStretch(1, 1)
        root.addWidget(status_band)
        root.addStretch(1)
        return page

    def _recipe_overview(self) -> QWidget:
        area = QWidget()
        layout = QVBoxLayout(area)
        layout.setContentsMargins(18, 12, 16, 16)
        layout.setSpacing(10)

        top_row = QHBoxLayout()
        title = QLabel("Recipe Overview")
        title.setStyleSheet("font-weight: 700; text-decoration: underline;")
        top_row.addWidget(title)
        top_row.addStretch(1)
        self.configure_button.setParent(area)
        self.configure_button.setCursor(Qt.PointingHandCursor)
        self.configure_button.setStyleSheet(
            "QPushButton { background: #e4e1d8; color: #111111;"
            " border-top: 1px solid #ffffff; border-left: 1px solid #ffffff;"
            " border-right: 1px solid #6d6a62; border-bottom: 1px solid #6d6a62;"
            " padding: 2px 16px; min-width: 78px; min-height: 22px; }"
            "QPushButton:pressed { border-top-color: #6d6a62; border-left-color: #6d6a62;"
            " border-right-color: #ffffff; border-bottom-color: #ffffff; }"
        )
        self.configure_button.show()
        top_row.addWidget(self.configure_button, 0, Qt.AlignRight)
        layout.addLayout(top_row)

        recipe_properties = self._recipe_properties_box()
        wafer_layout = self._wafer_layout_box()
        recipe_properties.set_expanded(False)
        wafer_layout.set_expanded(False)
        layout.addWidget(recipe_properties)
        layout.addWidget(wafer_layout)

        self.test_overview_container = QWidget()
        self.test_overview_layout = QVBoxLayout(self.test_overview_container)
        self.test_overview_layout.setContentsMargins(0, 0, 0, 0)
        self.test_overview_layout.setSpacing(10)
        layout.addWidget(self.test_overview_container)

        self.wafer_post_processing_overview = self._wafer_post_processing_box()
        self.wafer_post_processing_overview.set_expanded(False)
        layout.addWidget(self.wafer_post_processing_overview)
        self._sync_recipe_test_sections(self.current_recipe.get("tests", []))
        layout.addStretch(1)
        return area

    def _recipe_properties_box(self) -> QWidget:
        box = SectionBox("Recipe Properties")
        self.recipe_overview_sections["Recipe Properties"] = box
        self.recipe_property_labels = {}
        self.creation_property_labels = {}
        self.load_save_status_labels = {}
        grid = QGridLayout()
        grid.setHorizontalSpacing(0)
        grid.setVerticalSpacing(3)
        grid.setColumnStretch(0, 18)
        grid.setColumnStretch(1, 25)
        grid.setColumnStretch(2, 57)
        box.layout.addLayout(grid)

        self._add_group(
            grid,
            0,
            "Inspection Properties",
            [
                ("Recipe Name", "Vert_Seg0123"),
                ("Device Name", "Device1"),
                ("Layer Name", "Layer1"),
                ("Recipe Type", "Normal"),
                ("Approval", "Engineering"),
            ],
        )
        self._add_group(
            grid,
            1,
            "Creation Properties",
            [
                ("Creation Time", "2011-03-31 23:49:06"),
                ("Last Modification", "2011-09-01 09:27:57"),
                ("Software Version", "9.7.064"),
                ("History Log", ""),
            ],
        )
        self._add_group(
            grid,
            2,
            "Load/Save Status",
            [("Validation Status", "<b>Valid recipe:</b> The recipe successfully passed validation on<br>9/1/2011")],
            with_status=True,
        )
        validation_row = self.recipe_overview_rows.get("Validation Status")
        if validation_row is not None:
            validation_row.show()
        self._equalize_overview_modules(
            [
                self.recipe_overview_groups.get("Inspection Properties"),
                self.recipe_overview_groups.get("Creation Properties"),
                self.recipe_overview_groups.get("Load/Save Status"),
            ]
        )
        if validation_row is not None:
            validation_row.hide()
        return box

    def _lock_overview_module(self, group: QFrame):
        """Keep a module at the height of its full content for every recipe state."""
        hint = group.sizeHint()
        group.setMinimumHeight(max(group.minimumHeight(), hint.height()))

    def _equalize_overview_modules(self, groups):
        present = [group for group in groups if group is not None]
        for group in present:
            self._lock_overview_module(group)
        if not present:
            return
        height = max(group.minimumHeight() for group in present)
        for group in present:
            group.setMinimumHeight(height)

    def _set_overview_divider(self, group: QFrame, divided: bool):
        group.setObjectName("overviewColumn")
        group.setFrameShape(QFrame.NoFrame)
        border = "border-right: 1px solid #9c998f;" if divided else "border: none;"
        group.setStyleSheet(
            "QFrame#overviewColumn { background: transparent; border: none; " + border + " }"
        )

    def _overview_heading(self, title: str, display_text: str | None = None) -> QLabel:
        actions = {
            "Inspection Properties": lambda: self._navigate_to("inspection_properties"),
            "Wafer Properties": lambda: self._navigate_to("wafer_properties"),
            "Alignment": lambda: self._navigate_to("alignment"),
            "Registration Sites": lambda: self._navigate_to("registration_sites"),
            "Die Layout": lambda: self._navigate_to("wafer_map"),
            "Die Corner": lambda: self.open_die_corner_zoom(),
            "Wafer Map": lambda: self._navigate_to("wafer_map"),
            "Design Files": lambda: self.open_design_registration(),
            "Test Properties": lambda: self._navigate_to("tests"),
            "Inspection Optics": lambda: self._navigate_to("tests"),
            "Collection Optics": lambda: self._navigate_to("tests"),
            "Illumination Level Optimization": lambda: self._navigate_to("test_light_level"),
            "Fourier Filter": lambda: self._navigate_to("test_fourier_filter"),
            "Light Level Sensitivity": lambda: self._navigate_to("test_light_level"),
            "Sensitivity": lambda: self._navigate_to("test_sensitivity"),
            "Defect Filters": lambda: self._navigate_to("test_defect_filters"),
            "Care Areas": lambda: self._navigate_to("test_care_areas"),
            "Sample Plan": lambda: self._navigate_to("test_sample_plan"),
            "Wafer Post Processing": lambda: self._navigate_to("wafer_post_processing"),
        }
        context = getattr(self, "_building_test_context", None)
        if context is not None and title in {
            "Test Properties", "Inspection Optics", "Collection Optics",
            "Illumination Level Optimization", "Fourier Filter",
            "Light Level Sensitivity", "Sensitivity", "Defect Filters",
            "Care Areas", "Sample Plan",
        }:
            modules = {
                "Fourier Filter": "fourier_filter",
                "Light Level Sensitivity": "light_level",
                "Sensitivity": "sensitivity",
                "Defect Filters": "defect_filters",
                "Care Areas": "care_areas",
                "Sample Plan": "sample_plan",
            }
            callback = lambda checked=False, index=context["index"], module=modules.get(title): self.open_tests_setup(
                initial_module=module,
                initial_test_index=index,
            )
        else:
            callback = actions.get(title)
        label = ActionLabel(display_text or title, callback)
        label.setProperty("heading", True)
        if callback:
            label.setToolTip(f"Open {display_text or title}")
            if context is not None:
                self.overview_action_labels[(title, context["index"])] = label
                if context["index"] == 0:
                    self.overview_action_labels[title] = label
            else:
                self.overview_action_labels[title] = label
        return label

    def _wafer_layout_box(self) -> QWidget:
        box = SectionBox("Wafer Layout")
        self.recipe_overview_sections["Wafer Layout"] = box
        self.wafer_property_labels = {}
        self.design_file_labels = {}
        grid = QGridLayout()
        grid.setHorizontalSpacing(0)
        grid.setVerticalSpacing(4)
        for column, stretch in enumerate((22, 12, 13, 17, 18, 19, 14)):
            grid.setColumnStretch(column, stretch)
        self.wafer_layout_grid = grid
        box.layout.addLayout(grid)

        self._add_group(
            grid,
            0,
            "Wafer Properties",
            [
                ("Diameter", "300 mm"),
                ("Wafer Type", "Patterned"),
                ("Orientation", "Down"),
                ("Align Mark", "Notched"),
                ("Laser Power Sensitive", "Yes"),
                ("Dark Wafer", "No"),
                ("Wafer Darkness Level", "Level 1"),
                ("Laser Power Factor", "0.03500"),
                ("Layer", "-"),
            ],
            with_status=True,
        )
        self._add_alignment_group(grid, 1)
        self._add_registration_sites_group(grid, 2)
        self._add_group(
            grid,
            3,
            "Die Layout",
            [
                ("Die Width", "0 um"),
                ("Die Height", "0 um"),
                ("Reticle Size", "Not used"),
                ("Street Size", "Not Defined"),
                ("Inner Die", "No"),
                ("Valid Dies", "0"),
            ],
            with_status=True,
        )
        self._add_die_corner_group(grid, 4)
        self._add_wafer_map_group(grid, 5)
        self._add_group(grid, 6, "Design Files", [("Selected RDF", "-")])
        self._equalize_overview_modules(
            [
                self.recipe_overview_groups.get(name)
                for name in (
                    "Wafer Properties",
                    "Alignment",
                    "Registration Sites",
                    "Die Layout",
                    "Die Corner",
                    "Wafer Map",
                    "Design Files",
                )
            ]
        )
        return box

    def _test_one_box(self, index: int = 0) -> QWidget:
        section_name = f"Test {index + 1}"
        box = SectionBox(section_name)
        self.recipe_overview_sections[section_name] = box
        context = {
            "index": index,
            "section": box,
            "labels": {},
            "groups": {},
            "collection": {"channels": [], "polarization": [], "iris": []},
            "light_level": {},
            "care_area_border": None,
            "care_area_group_count": None,
            "sample_plan_label": None,
            "sample_plan_dies": None,
        }
        self._building_test_context = context
        grid = QGridLayout()
        grid.setHorizontalSpacing(0)
        grid.setVerticalSpacing(18)
        grid.setRowStretch(0, 1)
        grid.setRowStretch(1, 1)
        box.layout.addLayout(grid)

        self._add_test_group(
            grid,
            0,
            0,
            "Test Properties",
            [
                ("Test Name", "Test 1"),
                ("Orientation", "180°"),
                ("Light Trained", "Trained on tool"),
                ("Save Patch Images", "Yes"),
                ("Save Feature Vectors", "Yes"),
                ("iDO Classifier", "-"),
                ("RBB Recipe", "-"),
                ("Dynamic Range", "Extended"),
            ],
            width=245,
        )
        self._add_test_group(
            grid,
            0,
            1,
            "Inspection Optics",
            [
                ("Magnification\n(Pixel Size)", "SL815"),
                ("Focus Offset", "0 um"),
                ("Polarization", "P-POL"),
                ("Incidence Angle", "Oblique"),
                ("Speed", "High Throughput Mode"),
            ],
            width=270,
        )
        self._add_collection_optics_group(grid, 0, 2)
        self._add_test_group(
            grid,
            0,
            3,
            "Illumination Level Optimization",
            [("Noise Boxes", "-")],
            width=245,
            push_to_bottom=True,
        )
        self._add_test_group(
            grid,
            0,
            4,
            "Fourier Filter",
            [
                ("1 (Left)", "On"),
                ("Training Results", "0.0"),
                ("", ""),
                ("2 (Right)", "On"),
                ("Training Results", "0.0"),
                ("", ""),
                ("3 (Center)", "On"),
                ("Training Results", "0.0"),
            ],
            width=220,
        )
        self._add_light_level_group(grid, 1, 0)
        self._add_test_group(
            grid,
            1,
            1,
            "Sensitivity",
            [
                ("Channel 1 (Left)", ""),
                ("Selected Algorithms", "HLAT"),
                ("", ""),
                ("Channel 2 (Right)", ""),
                ("Selected Algorithms", "HLAT"),
                ("", ""),
                ("Channel 3 (Center)", ""),
                ("Selected Algorithms", "HLAT"),
                ("", ""),
                ("Defined Regions", "R1, R2, R3"),
                ("Segmentation", "In Use"),
            ],
            width=255,
        )
        self._add_test_group(
            grid,
            1,
            2,
            "Defect Filters",
            [
                ("Region :", "R1"),
                ("Filters Defined", "No"),
                ("", ""),
                ("Region :", "R2"),
                ("Filters Defined", "No"),
                ("", ""),
                ("Region :", "R3"),
                ("Filters Defined", "No"),
            ],
            width=160,
        )
        self._add_care_areas_group(grid, 1, 3)
        self._add_sample_plan_group(grid, 1, 4)
        self._building_test_context = None
        self.test_overview_contexts.append(context)
        self._equalize_overview_modules(
            [context["groups"].get(name) for name in (
                "Test Properties",
                "Inspection Optics",
                "Collection Optics",
                "Illumination Level Optimization",
                "Fourier Filter",
            )]
        )
        self._equalize_overview_modules(
            [context["groups"].get(name) for name in (
                "Light Level Sensitivity",
                "Sensitivity",
                "Defect Filters",
                "Care Areas",
                "Sample Plan",
            )]
        )
        if index == 0:
            self.test_overview_labels = context["labels"]
            self.collection_overview_labels = context["collection"]
            self.light_level_overview_labels = context["light_level"]
            self.care_area_border_label = context["care_area_border"]
            self.care_area_group_count_label = context["care_area_group_count"]
            self.sample_plan_overview_label = context["sample_plan_label"]
            self.sample_plan_dies_label = context["sample_plan_dies"]
        return box

    def _sync_recipe_test_sections(self, tests):
        while self.test_overview_layout.count():
            item = self.test_overview_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for name in [key for key in self.recipe_overview_sections if key.startswith("Test ")]:
            del self.recipe_overview_sections[name]
        self.test_overview_contexts = []
        self.overview_care_previews = []
        displayed_tests = list(tests or [{}])
        for index, _test in enumerate(displayed_tests):
            section = self._test_one_box(index)
            section.set_expanded(index == min(self.selected_test_index, len(displayed_tests) - 1))
            self.test_overview_layout.addWidget(section)

    def _wafer_post_processing_box(self) -> QWidget:
        box = SectionBox("Wafer Post Processing")
        self.recipe_overview_sections["Wafer Post Processing"] = box
        group = QFrame()
        self.recipe_overview_groups["Processing Summary"] = group
        grid = QGridLayout(group)
        grid.setContentsMargins(6, 0, 12, 6)
        grid.setHorizontalSpacing(12)
        heading = self._overview_heading("Wafer Post Processing", "Processing Summary")
        grid.addWidget(heading, 0, 0, 1, 2)
        self.wpp_overview_labels = {}
        for row, label in enumerate(
            ("Processing Status", "Template", "Enabled Operations", "Execution Order"),
            start=1,
        ):
            holder = QWidget()
            holder_layout = QHBoxLayout(holder)
            holder_layout.setContentsMargins(0, 0, 0, 0)
            name = QLabel(label)
            name.setMinimumWidth(118)
            value = QLabel("-")
            value.setWordWrap(True)
            value.setTextInteractionFlags(Qt.TextSelectableByMouse)
            holder_layout.addWidget(name)
            holder_layout.addWidget(value, 1)
            grid.addWidget(holder, row, 0, 1, 2)
            self.wpp_overview_labels[label] = value
            self.recipe_overview_rows[label] = holder
        box.layout.addWidget(group)
        return box

    def _add_test_group(
        self,
        grid: QGridLayout,
        row_index: int,
        column: int,
        title: str,
        rows: List[Tuple[str, str]],
        *,
        width: int,
        push_to_bottom: bool = False,
    ):
        group = QFrame()
        context = self._building_test_context
        context["groups"][title] = group
        if context["index"] == 0:
            self.recipe_overview_groups[title] = group
        group.setMinimumWidth(width)
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._set_overview_divider(group, column < 4)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(6, 0, 12, 0)
        layout.setSpacing(4)
        title_label = self._overview_heading(title)
        layout.addWidget(title_label)
        if push_to_bottom:
            layout.addStretch(1)
        for label, value in rows:
            if not label and not value:
                layout.addSpacing(10)
                continue
            line = QHBoxLayout()
            line.setSpacing(8)
            name = QLabel(label)
            name.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            name.setMinimumWidth(104)
            val = QLabel(value)
            val.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            val.setWordWrap(True)
            if label:
                context["labels"].setdefault(title, {}).setdefault(label, []).append(val)
            line.addWidget(name)
            line.addWidget(val)
            line.addStretch(1)
            layout.addLayout(line)
        if not push_to_bottom:
            layout.addStretch(1)
        grid.addWidget(group, row_index, column)

    def _add_collection_optics_group(self, grid: QGridLayout, row_index: int, column: int):
        group = QFrame()
        context = self._building_test_context
        context["groups"]["Collection Optics"] = group
        if context["index"] == 0:
            self.recipe_overview_groups["Collection Optics"] = group
        group.setMinimumWidth(210)
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._set_overview_divider(group, True)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(6, 0, 12, 0)
        layout.setSpacing(4)
        title = self._overview_heading("Collection Optics")
        layout.addWidget(title)
        collection_labels = context["collection"]
        for channel in ["Channel 1 (Left)", "Channel 2 (Right)", "Channel 3 (Center)"]:
            channel_label = QLabel(f"{channel}  On")
            collection_labels["channels"].append(channel_label)
            layout.addWidget(channel_label)
            for label, value in [("Polarization", "None"), ("Iris", "Open")]:
                line = QHBoxLayout()
                name = QLabel(label)
                name.setMinimumWidth(92)
                line.addWidget(name)
                value_label = QLabel(value)
                collection_labels[label.lower()].append(value_label)
                line.addWidget(value_label)
                line.addStretch(1)
                layout.addLayout(line)
            layout.addSpacing(10)
        layout.addStretch(1)
        grid.addWidget(group, row_index, column)

    def _add_light_level_group(self, grid: QGridLayout, row_index: int, column: int):
        group = QFrame()
        context = self._building_test_context
        context["groups"]["Light Level Sensitivity"] = group
        if context["index"] == 0:
            self.recipe_overview_groups["Light Level Sensitivity"] = group
        group.setMinimumWidth(245)
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._set_overview_divider(group, True)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(6, 0, 12, 0)
        layout.setSpacing(4)
        title = self._overview_heading("Light Level Sensitivity", "Light Level")
        layout.addWidget(title)
        light_labels = context["light_level"]
        for row in [
            ("Channels", "CH1      CH2      CH3"),
            ("Light Levels", "8.6       7.4       2.3"),
            ("Camera Gains", "16.00    16.00    16.00"),
            ("PILO Noise Values", "24.1     23.1     79.4"),
            ("", ""),
            ("Exposures", ""),
        ]:
            if not row[0] and not row[1]:
                layout.addSpacing(12)
                continue
            line = QHBoxLayout()
            name = QLabel(row[0])
            name.setMinimumWidth(126)
            line.addWidget(name)
            value_label = QLabel(row[1])
            light_labels[row[0]] = value_label
            line.addWidget(value_label)
            line.addStretch(1)
            layout.addLayout(line)
        layout.addStretch(1)
        grid.addWidget(group, row_index, column)

    def _add_overview_metric_form(self, layout, rows):
        form = QGridLayout()
        form.setContentsMargins(0, 6, 0, 0)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(3)
        form.setColumnStretch(1, 1)
        value_labels = []
        for row_index, (name, value) in enumerate(rows):
            name_label = QLabel(name)
            name_label.setStyleSheet("color: #4a4a4a; background: transparent;")
            value_label = QLabel(value)
            value_label.setStyleSheet("color: #111111; background: transparent;")
            value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            form.addWidget(name_label, row_index, 0, Qt.AlignLeft | Qt.AlignVCenter)
            form.addWidget(value_label, row_index, 1, Qt.AlignLeft | Qt.AlignVCenter)
            value_labels.append(value_label)
        layout.addLayout(form)
        return value_labels

    def _add_care_areas_group(self, grid: QGridLayout, row_index: int, column: int):
        group = QFrame()
        context = self._building_test_context
        context["groups"]["Care Areas"] = group
        if context["index"] == 0:
            self.recipe_overview_groups["Care Areas"] = group
        group.setMinimumWidth(196)
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._set_overview_divider(group, True)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(6, 0, 8, 0)
        layout.setSpacing(2)
        title = self._overview_heading("Care Areas")
        layout.addWidget(title)
        preview = CareAreasPreview(
            zoom_callback=self.open_care_area_zoom
        )
        preview.setToolTip("Click to view the enlarged Care Area image")
        self.overview_care_previews.append(preview)
        layout.addWidget(preview, alignment=Qt.AlignLeft | Qt.AlignTop)
        border_label, group_count_label = self._add_overview_metric_form(
            layout,
            [("CA Border", "10.00 μm × 5.00 μm"), ("Group Count", "5")],
        )
        context["care_area_border"] = border_label
        context["care_area_group_count"] = group_count_label
        layout.addStretch(1)
        grid.addWidget(group, row_index, column)

    def _add_sample_plan_group(self, grid: QGridLayout, row_index: int, column: int):
        group = QFrame()
        context = self._building_test_context
        context["groups"]["Sample Plan"] = group
        if context["index"] == 0:
            self.recipe_overview_groups["Sample Plan"] = group
        group.setMinimumWidth(230)
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._set_overview_divider(group, False)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(6, 0, 8, 0)
        layout.setSpacing(2)
        title = self._overview_heading("Sample Plan")
        layout.addWidget(title)
        preview = SamplePlanPreview(
            zoom_callback=self.open_sample_plan_zoom
        )
        preview.setToolTip("Click to view the enlarged Sample Plan wafermap")
        layout.addWidget(preview, alignment=Qt.AlignLeft | Qt.AlignTop)
        sample_label, dies_label = self._add_overview_metric_form(
            layout,
            [("Inspection Type", "Full Die"), ("Total Inspectable Dies", "4180")],
        )
        context["sample_plan_label"] = sample_label
        context["sample_plan_dies"] = dies_label
        layout.addStretch(1)
        grid.addWidget(group, row_index, column)

    def _add_group(
        self,
        grid: QGridLayout,
        column: int,
        title: str,
        rows: List[Tuple[str, str]],
        *,
        with_status: bool = False,
    ):
        group = QFrame()
        self.recipe_overview_groups[title] = group
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._set_overview_divider(group, title not in {"Load/Save Status", "Design Files"})
        if title == "Wafer Properties":
            group.setMinimumWidth(168)
        elif title == "Die Layout":
            group.setMinimumWidth(132)
        elif title == "Inspection Properties":
            group.setMinimumWidth(148)
        elif title == "Creation Properties":
            group.setMinimumWidth(196)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 0, 10, 0)
        layout.setSpacing(3)

        header = QHBoxLayout()
        display = "Custom Files" if title == "Design Files" else None
        title_label = self._overview_heading(title, display)
        header.addWidget(title_label)
        if with_status:
            status_dot = StatusDot()
            self.overview_status_dots[title] = status_dot
            header.addWidget(status_dot)
        header.addStretch(1)
        layout.addLayout(header)
        content_layout = layout
        if title == "Load/Save Status":
            content_row = QHBoxLayout()
            content_row.setContentsMargins(0, 4, 0, 0)
            content_row.setSpacing(8)
            content_host = QWidget()
            content_layout = QVBoxLayout(content_host)
            content_layout.setContentsMargins(0, 0, 0, 0)
            content_layout.setSpacing(3)
            content_row.addWidget(content_host, 1)
            self.load_save_status_scroll = EmptyScrollTrack()
            content_row.addWidget(self.load_save_status_scroll)
            layout.addLayout(content_row, 1)
            self.load_save_status_combo = QComboBox()
            self.load_save_status_combo.addItems(["Incomplete", "Valid", "Nonoptimal", "Invalid"])
            self.load_save_status_combo.setFixedWidth(148)
            self.load_save_status_combo.setToolTip("Load/Save Status")
            content_layout.addWidget(self.load_save_status_combo)

        for label, value in rows:
            row = QHBoxLayout()
            row.setSpacing(8)
            row_holder = QWidget()
            row_holder.setLayout(row)
            name = QLabel(label)
            name.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            if title == "Inspection Properties":
                name_width = 78
            elif title == "Creation Properties":
                name_width = 112
            elif title == "Wafer Properties":
                name_width = 118
                name.setWordWrap(True)
                name.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            elif title in {"Die Layout", "Design Files"}:
                name_width = 72
            else:
                name_width = 94
            name.setFixedWidth(name_width)
            val = (
                ActionLabel(value, lambda: self.show_recipe_history())
                if label == "History Log"
                else QLabel(value)
            )
            val.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
            val.setMinimumWidth(0)
            val.setAlignment(Qt.AlignLeft | (Qt.AlignTop if title == "Wafer Properties" else Qt.AlignVCenter))
            val.setWordWrap(True)
            val.setTextInteractionFlags(Qt.TextSelectableByMouse)
            if label == "History Log":
                name.setText("")
                name.setFixedWidth(0)
                name.setMinimumWidth(0)
                icon = _HistoryLogIcon(lambda: self.show_recipe_history())
                row.insertWidget(0, icon)
                val.setText("History Log")
                val.setStyleSheet("text-decoration: underline;")
                val.setToolTip(
                    "Open Recipe History Log: version, date, tool ID, software version, "
                    "optics type/subtype, user, event, and comment."
                )
                self.overview_action_labels["History Log"] = val
            if label == "Validation Status":
                name.setText("")
                name.setFixedWidth(0)
                name.setMinimumWidth(0)
                row.setSpacing(0)
                row.setContentsMargins(0, 0, 0, 0)
                val.setMinimumWidth(0)
                val.setWordWrap(True)
                val.setAlignment(Qt.AlignLeft | Qt.AlignTop)
                row_holder.hide()
            self._remember_recipe_overview_label(title, label, val)
            if label:
                self.recipe_overview_rows[label] = row_holder
            row.addWidget(name)
            row.addWidget(val)
            content_layout.addWidget(row_holder)

        content_layout.addStretch(1)
        grid.addWidget(group, 0, column)

    def _add_alignment_group(self, grid: QGridLayout, column: int):
        group = QFrame()
        self.recipe_overview_groups["Alignment"] = group
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._set_overview_divider(group, True)
        group.setMinimumWidth(92)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(6, 0, 12, 0)
        layout.setSpacing(3)

        header = QHBoxLayout()
        title = self._overview_heading("Alignment")
        header.addWidget(title)
        status_dot = StatusDot()
        self.overview_status_dots["Alignment"] = status_dot
        header.addWidget(status_dot)
        header.addStretch(1)
        layout.addLayout(header)

        self.alignment_overview_labels = {}
        self.alignment_detail_widgets = []
        for angle in (180, 90):
            angle_label = QLabel(f"At {angle} deg")
            angle_label.setStyleSheet("font-weight: 600;")
            layout.addWidget(angle_label)
            self.alignment_detail_widgets.append(angle_label)
            for field in ("Type", "DF Scores", "Uniqueness", "Sharpness", "Features"):
                row = QHBoxLayout()
                row.setSpacing(5)
                holder = QWidget()
                holder.setLayout(row)
                name = QLabel(field)
                name.setMinimumWidth(72)
                value = QLabel("-")
                value.setTextInteractionFlags(Qt.TextSelectableByMouse)
                row.addWidget(name)
                row.addWidget(value, 1)
                layout.addWidget(holder)
                self.alignment_detail_widgets.append(holder)
                self.alignment_overview_labels[(angle, field)] = value
            if angle == 180:
                layout.addSpacing(8)
        layout.addStretch(1)
        grid.addWidget(group, 0, column)

    def _mini_table(self, title: str, header_row: List[str], rows: List[Tuple[str, str]]) -> QWidget:
        table = QWidget()
        layout = QVBoxLayout(table)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        if title:
            label = QLabel(title)
            label.setStyleSheet("font-weight: 600;")
            layout.addWidget(label)
        header = QLabel("    ".join(header_row))
        header.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(header)
        for name, value in rows:
            row = QHBoxLayout()
            row.setSpacing(5)
            name_label = QLabel(name)
            name_label.setMinimumWidth(70)
            name_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            value_label = QLabel(value)
            value_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            row.addWidget(name_label)
            row.addWidget(value_label)
            layout.addLayout(row)
        return table

    def _add_registration_sites_group(self, grid: QGridLayout, column: int):
        group = QFrame()
        self.recipe_overview_groups["Registration Sites"] = group
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._set_overview_divider(group, True)
        group.setMinimumWidth(108)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(6, 0, 12, 0)
        layout.setSpacing(5)
        title = self._overview_heading("Registration Sites")
        layout.addWidget(title)
        layout.addStretch(1)
        self.registration_site_overview_labels = []
        self.registration_site_rows = []
        for label, value in [
            ("Defined Sites", "None at 180"),
            ("Defined Sites", "None at 90"),
        ]:
            row = QHBoxLayout()
            row.setSpacing(5)
            holder = QWidget()
            holder.setLayout(row)
            name = QLabel(label)
            name.setMinimumWidth(76)
            name.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            value_label = QLabel(value)
            self.registration_site_overview_labels.append(value_label)
            value_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            row.addWidget(name)
            row.addWidget(value_label)
            layout.addWidget(holder)
            self.registration_site_rows.append(holder)
        grid.addWidget(group, 0, column)

    def _add_die_corner_group(self, grid: QGridLayout, column: int):
        group = QFrame()
        self.recipe_overview_groups["Die Corner"] = group
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._set_overview_divider(group, True)
        group.setMinimumWidth(90)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(6, 0, 12, 0)
        title = self._overview_heading("Die Corner")
        layout.addWidget(title)
        self.die_corner_map = DieCornerMap()
        self.die_corner_map.zoom_callback = self.open_die_corner_zoom
        self.die_corner_map.setToolTip("Click to view enlarged die corner image")
        layout.addWidget(self.die_corner_map, alignment=Qt.AlignLeft)
        layout.addStretch(1)
        grid.addWidget(group, 0, column)

    def _remember_recipe_overview_label(self, title: str, label: str, value_label: QLabel):
        if not label:
            return
        if title == "Inspection Properties":
            self.recipe_property_labels[label] = value_label
        elif title == "Creation Properties":
            self.creation_property_labels[label] = value_label
        elif title == "Load/Save Status":
            self.load_save_status_labels[label] = value_label
        elif title == "Wafer Properties":
            self.wafer_property_labels[label] = value_label
        elif title == "Die Layout":
            self.die_layout_labels[label] = value_label
        elif title == "Design Files":
            self.design_file_labels[label] = value_label

    def _add_empty_status_group(self, grid: QGridLayout, column: int, title: str):
        group = QFrame()
        self.recipe_overview_groups[title] = group
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._set_overview_divider(group, True)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(6, 0, 12, 0)
        header = QHBoxLayout()
        label = QLabel(title)
        label.setProperty("heading", True)
        header.addWidget(label)
        header.addWidget(StatusDot())
        header.addStretch(1)
        layout.addLayout(header)
        layout.addStretch(1)
        grid.addWidget(group, 0, column)

    def _add_wafer_map_group(self, grid: QGridLayout, column: int):
        group = QFrame()
        self.recipe_overview_groups["Wafer Map"] = group
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._set_overview_divider(group, False)
        group.setMinimumWidth(150)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 0, 4, 0)
        header = QHBoxLayout()
        title = self._overview_heading("Wafer Map")
        header.addWidget(title)
        status_dot = StatusDot()
        self.overview_status_dots["Wafer Map"] = status_dot
        header.addWidget(status_dot)
        header.addStretch(1)
        layout.addLayout(header)
        self.overview_wafer_map = OverviewWaferMap()
        self.overview_wafer_map.zoom_callback = self.open_wafer_map_zoom
        self.overview_wafer_map.setToolTip("Click to view enlarged wafer map image")
        layout.addWidget(self.overview_wafer_map, alignment=Qt.AlignHCenter)
        layout.addStretch(1)
        grid.addWidget(group, 0, column)

    def _build_statusbar(self):
        status = QStatusBar()
        self.setStatusBar(status)
        status.setSizeGripEnabled(False)
        status.setStyleSheet("QStatusBar { background: #d8d5cc; } QStatusBar::item { border: none; }")

        holder = QWidget()
        row = QHBoxLayout(holder)
        row.setContentsMargins(8, 1, 10, 1)
        row.setSpacing(8)

        help_label = QLabel("For Help, press F1")
        help_label.setStyleSheet("background: transparent; border: none; color: #111111;")
        row.addWidget(help_label)

        rule = QFrame()
        rule.setFixedWidth(1)
        rule.setStyleSheet("background: #8a867e; border: none;")
        row.addWidget(rule)

        self.inspection_status_label = QLabel("Inspection: New    Device: -    Step: -")
        self.inspection_status_label.setAlignment(Qt.AlignCenter)
        self.inspection_status_label.setMinimumWidth(320)
        self.inspection_status_label.setToolTip("Inspection name / Device ID / Step ID")
        self.inspection_status_label.setStyleSheet(
            "background: #eceae3; color: #111111;"
            "border-top: 1px solid #7d796f; border-left: 1px solid #7d796f;"
            "border-right: 1px solid #ffffff; border-bottom: 1px solid #ffffff;"
            "padding: 1px 12px;"
        )
        row.addWidget(self.inspection_status_label, 1)

        self.wafer_status_symbol = QLabel()
        self.wafer_status_symbol.setFixedSize(24, 24)
        self.secs_status_symbol = QLabel()
        self.secs_status_symbol.setFixedSize(24, 24)
        self.ilink_status_symbol = QLabel()
        self.ilink_status_symbol.setFixedSize(24, 24)
        for symbol in (self.wafer_status_symbol, self.secs_status_symbol, self.ilink_status_symbol):
            symbol.setAlignment(Qt.AlignCenter)
            row.addWidget(symbol)

        num_lock = QLabel("NUM")
        num_lock.setAlignment(Qt.AlignCenter)
        num_lock.setStyleSheet(
            "background: transparent; border: none; border-left: 1px solid #8a867e;"
            "padding-left: 8px; color: #111111;"
        )
        row.addWidget(num_lock)
        status.addPermanentWidget(holder, 1)

        self.wafer_status_label = QLabel(status)
        self.wafer_status_label.hide()
        self.secs_status_label = QLabel(status)
        self.secs_status_label.hide()
        self.ilink_status_label = QLabel(status)
        self.ilink_status_label.hide()
        self.dbb_status_label = QLabel("DBB ACTIVE", status)
        self.dbb_status_label.hide()
        self._refresh_wafer_status()
        self._refresh_communication_status()
        self._refresh_alarm_alert_state()

    def _status_symbol_pixmap(self, kind: str, state: str) -> QPixmap:
        if kind == "wafer":
            return self._wafer_status_pixmap(state)
        if kind == "secs":
            return self._secs_status_pixmap(state)
        return self._ilink_status_pixmap(state)

    def _wafer_orientation(self) -> tuple[int, str]:
        try:
            degrees = int(str(self.wafer_runtime_state.get("required_orientation") or "180").split()[0])
        except ValueError:
            degrees = 180
        names = {0: "up", 90: "right", 180: "down", 270: "left"}
        return degrees % 360, names.get(degrees % 360, f"{degrees} deg")

    def _wafer_status_pixmap(self, state: str) -> QPixmap:
        pixmap = QPixmap(22, 22)
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        if state == "empty":
            painter.setPen(QPen(QColor("#8a8a8a"), 1.4))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(3, 3, 16, 16)
            painter.end()
            return pixmap
        orientation, _name = self._wafer_orientation()
        painter.setPen(QPen(QColor("#1d7a28"), 1))
        painter.setBrush(QColor("#3ad63a"))
        painter.drawPath(wafer_disk_with_notch(2, 2, 18, orientation))
        if state == "aligned":
            painter.setPen(QPen(QColor("#f4fff4"), 1.6))
            painter.drawLine(6, 9, 16, 9)
            painter.drawLine(6, 13, 16, 13)
        else:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#143018"))
            painter.drawEllipse(9, 9, 4, 4)
        painter.end()
        return pixmap

    def _secs_hook_path(self) -> QPainterPath:
        path = QPainterPath()
        path.moveTo(4, 2)
        path.lineTo(16, 2)
        path.lineTo(16, 10)
        path.lineTo(10, 10)
        path.lineTo(10, 6)
        path.lineTo(7, 6)
        path.lineTo(7, 15)
        path.lineTo(4, 15)
        path.closeSubpath()
        head = QPainterPath()
        head.moveTo(2, 14)
        head.lineTo(9, 14)
        head.lineTo(5.5, 19)
        head.closeSubpath()
        path.addPath(head)
        return path

    def _secs_status_pixmap(self, state: str) -> QPixmap:
        pixmap = QPixmap(22, 22)
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        green = QColor("#1f9a32")
        if state == "remote":
            painter.setPen(QPen(QColor("#146622"), 1))
            painter.setBrush(green)
            painter.drawPath(self._secs_hook_path())
        elif state == "local":
            painter.setPen(QPen(green, 1.6))
            painter.setBrush(QColor("#ffffff"))
            painter.drawPath(self._secs_hook_path())
        elif state == "disabled":
            painter.setPen(QPen(QColor("#1d3f86"), 1))
            painter.setBrush(QColor("#2f5fbf"))
            painter.drawPath(self._secs_hook_path())
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor("#e10600"), 2))
            painter.drawEllipse(2, 2, 18, 18)
            painter.drawLine(4, 18, 18, 4)
        else:
            painter.setPen(QPen(QColor("#e10600"), 2))
            painter.drawLine(2, 3, 2, 18)
            painter.drawLine(19, 3, 19, 18)
            painter.setPen(QPen(QColor("#146622"), 1))
            painter.setBrush(green)
            painter.drawRect(5, 4, 4, 13)
            painter.drawRect(12, 4, 4, 8)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#e10600"))
            painter.drawRect(10, 8, 2, 5)
        painter.end()
        return pixmap

    def _ilink_frame(self, painter: QPainter, fill: QColor, border: QColor):
        painter.setPen(QPen(border, 1.6))
        painter.setBrush(fill)
        painter.drawRect(3, 3, 16, 16)

    def _ilink_arrow_path(self) -> QPainterPath:
        path = QPainterPath()
        path.moveTo(5.7, 14.1)
        path.lineTo(10.5, 9.3)
        path.lineTo(9.3, 8.1)
        path.lineTo(16.4, 5.6)
        path.lineTo(13.9, 12.7)
        path.lineTo(12.7, 11.5)
        path.lineTo(7.9, 16.3)
        path.closeSubpath()
        return path

    def _ilink_arrow(self, painter: QPainter, color: QColor, filled: bool):
        painter.setPen(QPen(color, 1.5, Qt.SolidLine, Qt.FlatCap, Qt.MiterJoin))
        painter.setBrush(color if filled else Qt.NoBrush)
        painter.drawPath(self._ilink_arrow_path())

    def _ilink_status_pixmap(self, state: str) -> QPixmap:
        pixmap = QPixmap(22, 22)
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        green = QColor("#1f9a32")
        gray = QColor("#d5d5d5")
        if state == "ready":
            self._ilink_frame(painter, gray, green)
            self._ilink_arrow(painter, green, False)
        elif state == "progress":
            self._ilink_frame(painter, gray, green)
            self._ilink_arrow(painter, green, True)
        elif state == "warning":
            self._ilink_frame(painter, gray, green)
            arrow = self._ilink_arrow_path()
            painter.save()
            painter.setClipPath(arrow)
            painter.setPen(Qt.NoPen)
            painter.setBrush(green)
            painter.drawRect(0, 0, 22, 22)
            painter.setBrush(QColor("#e0b000"))
            painter.drawRect(8, 0, 14, 12)
            painter.setBrush(QColor("#e10600"))
            painter.drawRect(12, 0, 10, 8)
            painter.restore()
        elif state == "shutdown":
            self._ilink_frame(painter, QColor("#e8e8e8"), QColor("#6a6a6a"))
            self._ilink_arrow(painter, QColor("#2f5fbf"), True)
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor("#e10600"), 2))
            painter.drawEllipse(2, 2, 18, 18)
            painter.drawLine(4, 18, 18, 4)
        else:
            self._ilink_frame(painter, gray, QColor("#6a6a6a"))
            painter.setPen(Qt.NoPen)
            painter.setBrush(green)
            lower = QPainterPath()
            lower.moveTo(4, 12)
            lower.lineTo(4, 18)
            lower.lineTo(10, 18)
            lower.closeSubpath()
            painter.drawPath(lower)
            painter.setBrush(QColor("#d24a4a"))
            upper = QPainterPath()
            upper.moveTo(12, 4)
            upper.lineTo(18, 4)
            upper.lineTo(18, 10)
            upper.closeSubpath()
            painter.drawPath(upper)
            painter.setPen(QPen(QColor("#e10600"), 1.6))
            painter.drawLine(9, 13, 13, 9)
        painter.end()
        return pixmap

    def open_inspection_recipe(self):
        dialog = OpenInspectionRecipeDialog(
            self,
            recipe_store=self.recipe_store,
            wafer_state=self.wafer_runtime_state,
            recipe=self.current_recipe,
        )
        dialog.setWindowModality(Qt.ApplicationModal)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self._apply_selected_inspection(dialog)
        self._sync_left_nav_selection()
        return dialog

    def _apply_selected_inspection(self, dialog):
        if dialog.selected_recipe:
            recipe = prepare_loaded_recipe(dialog.selected_recipe)
            recipe["dirty"] = False
            self._recipe_loaded_from_library = True
            active_orientation = recipe.get(
                "active_setup_orientation",
                self._orientation_degrees(
                    (recipe.get("wafer_properties") or {}).get(
                        "orientation", "Down (180 deg.)"
                    )
                ),
            )
            self.wafer_runtime_state["required_orientation"] = str(
                self._orientation_degrees(active_orientation)
            )
            self.wafer_runtime_state["wafer_aligned"] = False
            source_port = self.wafer_runtime_state.get("wafer_source_port")
            source_slot = self.wafer_runtime_state.get("wafer_source_slot")
            slot_states = self.wafer_runtime_state.get("slot_states") or {}
            port_slots = slot_states.get(source_port)
            if port_slots is None:
                port_slots = slot_states.get(str(source_port), {})
            if source_slot is not None and port_slots.get(source_slot) == "Aligned":
                port_slots[source_slot] = "Loaded"
            elif source_slot is not None and port_slots.get(str(source_slot)) == "Aligned":
                port_slots[str(source_slot)] = "Loaded"
            self._set_current_recipe(recipe, message=f"Loaded recipe {recipe['inspection']}")

    def _has_loaded_recipe(self, recipe=None):
        recipe = recipe or self.current_recipe
        recipe_id = recipe.get("id", "")
        return bool(recipe_id and self.recipe_store.get_recipe(recipe_id) is not None)

    def _should_confirm_discard_inspection(self) -> bool:
        recipe = self.current_recipe or {}
        if self._has_loaded_recipe(recipe):
            return bool(recipe.get("dirty"))
        if recipe.get("inspection") not in {None, "", "New"}:
            return True
        return bool(recipe.get("tests") or recipe.get("components"))

    def new_inspection(self, checked: bool = False):
        if self._should_confirm_discard_inspection():
            answer = QMessageBox.question(
                self,
                "New Inspection",
                "The current inspection contains unsaved changes. Create a new inspection?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return False
        prompt = QMessageBox(self)
        prompt.setIcon(QMessageBox.Question)
        prompt.setWindowTitle("New Inspection")
        prompt.setText("Create a new inspection?")
        prompt.setInformativeText("The default inspection parameter file will be loaded.")
        prompt.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        prompt.setDefaultButton(QMessageBox.Ok)
        prompt_result = prompt.exec() if hasattr(prompt, "exec") else prompt.exec_()
        if prompt_result != QMessageBox.Ok:
            return False
        self._recipe_loaded_from_library = False
        self._set_current_recipe(self.recipe_store.new_recipe(), message="Inspection: New")
        if self._active_route_key != "setup":
            self._navigate_to("setup")
        self.inspection_status_label.setText(
            f"Inspection: {self.current_recipe.get('inspection') or 'New'}"
            f"    Device: {self.current_recipe.get('device') or '-'}"
            f"    Step: {self.current_recipe.get('step') or '-'}"
        )
        self.statusBar().showMessage("Inspection: New")
        return True

    def save_inspection(self, checked: bool = False, *, save_copy: bool = False):
        source = dict(self.current_recipe)
        dialog = SaveInspectionDialog(
            source,
            save_copy=save_copy,
            recipe_store=self.recipe_store,
            parent=self,
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result != QDialog.Accepted or not dialog.recipe_values:
            return False
        target = dialog.recipe_values
        existing = next(
            (
                recipe
                for recipe in self.recipe_store.list_recipes()
                if recipe.get("inspection") == target["inspection"]
                and recipe.get("device") == target["device"]
                and recipe.get("step") == target["step"]
            ),
            None,
        )
        overwrite_recipe_id = None
        if existing is not None:
            overwrite = QMessageBox.question(
                self,
                "Overwrite Confirmation",
                f"The inspection recipe '{target['inspection']}' already exists.\nOverwrite it?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if overwrite != QMessageBox.Yes:
                return False
            overwrite_recipe_id = existing["id"]
        self._apply_save_inspection(
            dialog,
            source=source,
            save_copy=save_copy,
            overwrite_recipe_id=overwrite_recipe_id,
        )
        return True

    def _apply_save_inspection(
        self,
        dialog,
        *,
        source,
        save_copy,
        overwrite_recipe_id=None,
    ):
        if not dialog.recipe_values:
            return
        if save_copy:
            recipe = self.recipe_store.duplicate_recipe(
                source,
                dialog.recipe_values["inspection"],
                derivative=False,
            )
        else:
            recipe = source
        if overwrite_recipe_id is not None:
            recipe["id"] = overwrite_recipe_id
        recipe.update(dialog.recipe_values)
        recipe["path"] = str(
            self.recipe_store.path.parent
            / "Recipes"
            / recipe["device"]
            / recipe["step"]
            / recipe["inspection"]
        )
        if recipe.get("status") == "Incomplete" and recipe.get("inspection") != "New":
            recipe["state"] = recipe.get("state") or "Recipe setup is incomplete."
        saved = self.recipe_store.save_recipe(
            recipe,
            event="Save Inspection As" if save_copy else "Save Inspection",
            detail=recipe.get("comments", ""),
        )
        self._set_current_recipe(saved, message=f"Saved inspection {saved['inspection']}")

    def open_recipe_generation(self):
        dialog = RecipeGenerationDialog(bool(self.current_recipe), self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result != QDialog.Accepted:
            self._sync_left_nav_selection()
            return False
        self._apply_recipe_generation_action(dialog)
        self._sync_left_nav_selection()
        return False

    def _apply_recipe_generation_action(self, dialog):
        action = dialog.action
        if action == "new":
            self.new_inspection()
        elif action == "copy":
            self.save_inspection(save_copy=True)
        elif action == "derivative":
            self.create_derivative_inspection()
        elif action == "import":
            self.import_recipe()
        elif action == "extract":
            self.extract_components()
        elif action == "insert":
            self.insert_components()
        elif action == "history":
            self.show_recipe_history()

    def _xp_offline_state(self):
        return normalized_xp_state(self.recipe_store.get_preferences().get("xp_offline"))

    def _save_xp_offline_state(self, state, detail="XP Offline Setup updated"):
        normalized = normalized_xp_state(state)
        self.recipe_store.update_preferences({"xp_offline": normalized})
        self.recipe_store.record_utility_event("XP Offline Setup", detail)
        return normalized

    def open_registration_site_library(self):
        dialog = RegistrationSiteLibraryDialog(self.current_recipe, self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted and dialog.result_recipe:
            self._set_current_recipe(dialog.result_recipe, message="Registration site library updated; save required")
        return False

    def open_xp_recipe_generation(self):
        state = self._xp_offline_state()
        if not state["offline_setup_enabled"]:
            QMessageBox.information(self, "XP Offline Setup", "Enable XP Offline Setup before using Recipe Generation.")
            return
        dialog = XPRecipeGeneratorDialog(self.recipe_store, self.current_recipe, self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted and dialog.generated_recipes:
            self._save_xp_offline_state(state, f"Generated {len(dialog.generated_recipes)} AutoLearn-Ready recipe(s)")
            self.statusBar().showMessage(f"Generated {len(dialog.generated_recipes)} AutoLearn-Ready recipe(s)", 7000)

    def open_manual_assist(self):
        dialog = ManualAssistDialog(self._xp_offline_state(), self.current_recipe, self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result != QDialog.Accepted or dialog.result_state is None:
            return
        self._save_xp_offline_state(dialog.result_state, "Manual Assist configuration updated")
        if dialog.result_recipe:
            self._set_current_recipe(dialog.result_recipe, message=dialog.result_recipe.get("state", "AutoLearn state updated"))

    def open_rds_manager(self):
        dialog = RDSManagerDialog(self.recipe_store, self.current_recipe, self._xp_offline_state(), self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted and dialog.result_state is not None:
            events = len(dialog.result_state.get("distribution_events", []))
            self._save_xp_offline_state(dialog.result_state, f"RDS updated; {events} distribution event(s)")
            self.statusBar().showMessage("RDS version and distribution records saved (simulated)", 6000)

    def open_recipe_comparator(self):
        state = self._xp_offline_state()
        dialog = RecipeComparatorDialog(self.recipe_store.list_recipes(), state.get("rds_versions", []), self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            for recipe in dialog.result_recipes:
                self.recipe_store.save_recipe(recipe, event="Recipe Comparator Save")
            self.statusBar().showMessage(f"Recipe Comparator saved {len(dialog.result_recipes)} recipe(s)", 6000)

    def open_gds2ca_converter(self):
        dialog = GDS2CAConverterDialog(self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result != QDialog.Accepted or not dialog.result_component:
            return
        updated = deepcopy(self.current_recipe)
        updated.setdefault("gds2ca_components", []).append(deepcopy(dialog.result_component))
        if updated.get("tests"):
            updated = apply_component_to_recipe(updated, dialog.result_component)
        updated["dirty"] = True
        self._set_current_recipe(updated, message="GDS2CA Care Area component generated and imported; save required")

    def open_cag_editor(self):
        groups = []
        seen = set()
        for test in self.current_recipe.get("tests", []):
            for group in (test.get("care_areas") or {}).get("groups", []):
                key = (group.get("name"), group.get("cag_code"))
                if key not in seen:
                    seen.add(key); groups.append(deepcopy(group))
        if not groups:
            QMessageBox.information(self, "CAG Editor", "No Care Area groups are available in the current recipe.")
            return
        dialog = CAGEditorDialog(groups, self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result != QDialog.Accepted or dialog.result_groups is None:
            return
        mapping = {group.get("name"): group.get("cag_code") for group in dialog.result_groups}
        updated = deepcopy(self.current_recipe)
        for test in updated.get("tests", []):
            for group in (test.get("care_areas") or {}).get("groups", []):
                if group.get("name") in mapping: group["cag_code"] = mapping[group.get("name")]
        updated["dirty"] = True
        self._set_current_recipe(updated, message="CAG Codes updated; save required")

    def create_derivative_inspection(self):
        source = dict(self.current_recipe)
        dialog = SaveInspectionDialog(
            source,
            derivative=True,
            recipe_store=self.recipe_store,
            parent=self,
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result != QDialog.Accepted or not dialog.recipe_values:
            return
        recipe = self.recipe_store.duplicate_recipe(
            source,
            dialog.recipe_values["inspection"],
            derivative=True,
        )
        recipe.update(dialog.recipe_values)
        recipe["path"] = str(
            self.recipe_store.path.parent
            / "Recipes"
            / recipe["device"]
            / recipe["step"]
            / recipe["inspection"]
        )
        saved = self.recipe_store.save_recipe(recipe, event="Create Derivative")
        self._set_current_recipe(saved, message=f"Created derivative inspection {saved['inspection']}")
        QMessageBox.information(
            self,
            "Derivative Inspection",
            "Reselect the first alignment site or die origin before running this derivative inspection.",
        )

    def import_recipe(self):
        dialog = RecipeImportDialog(self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result != QDialog.Accepted or not dialog.result_values:
            return
        values = dialog.result_values
        recipe = self.recipe_store.new_recipe()
        recipe.update(values)
        recipe["recipe_type"] = "Imported"
        recipe["status"] = "Incomplete"
        recipe["state"] = "Imported recipe translated for this tool. Review all components before running."
        recipe["path"] = str(
            self.recipe_store.path.parent
            / "Recipes"
            / recipe["device"]
            / recipe["step"]
            / recipe["inspection"]
        )
        saved = self.recipe_store.save_recipe(recipe, event="Import Recipe")
        self._set_current_recipe(saved, message=f"Imported recipe {saved['inspection']}")
        QMessageBox.information(
            self,
            "Recipe Translation",
            f"The recipe from {values['source_tool']} was translated to work on this machine.",
        )

    def extract_components(self):
        stored = self.recipe_store.get_recipe(self.current_recipe.get("id", ""))
        if stored is None or self.current_recipe.get("dirty"):
            answer = QMessageBox.question(
                self,
                "Extract Component",
                "The current inspection must be saved before components can be extracted.\n\n"
                "Save it now?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if answer != QMessageBox.Yes or not self.save_inspection():
                return
            stored = self.recipe_store.get_recipe(self.current_recipe.get("id", ""))
            if stored is None or self.current_recipe.get("dirty"):
                return
        dialog = ExtractComponentDialog(self.recipe_store, self.current_recipe, self)
        if not any(box.isEnabled() for box in dialog.checks):
            QMessageBox.warning(
                self,
                "Extract Component",
                "This saved recipe has no components that are valid for Run.",
            )
            return
        dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if dialog.extracted_filename:
            self.statusBar().showMessage(f"Extracted component file {dialog.extracted_filename}")

    def insert_components(self):
        dialog = InsertComponentDialog(self.recipe_store, self.current_recipe, self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted and dialog.result_recipe:
            self._set_current_recipe(dialog.result_recipe, message="Recipe components inserted; save required")

    def show_recipe_history(self):
        inspection = self.current_recipe.get("inspection", "")
        dialog = RecipeHistoryDialog(self.recipe_store, inspection, self)
        dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()

    def open_inspection_properties(self):
        dialog = InspectionPropertiesDialog(
            self.current_recipe,
            history_callback=self.show_recipe_history,
            parent=self,
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result != QDialog.Accepted or not dialog.result_values:
            return False
        updated = dict(self.current_recipe)
        changed = any(updated.get(key) != value for key, value in dialog.result_values.items())
        updated.update(dialog.result_values)
        if changed:
            updated["dirty"] = True
            self._set_current_recipe(updated, message="Inspection properties updated; save required")
        return False

    def _set_current_recipe(self, recipe: dict, *, message: str = ""):
        self.current_recipe = dict(recipe)
        self._apply_recipe_to_overview(self.current_recipe)
        self._refresh_home_status()
        inspection_name = self.current_recipe.get("inspection") or "New"
        device_name = self.current_recipe.get("device") or "-"
        step_name = self.current_recipe.get("step") or "-"
        self.inspection_status_label.setText(
            f"Inspection: {inspection_name}    Device: {device_name}    Step: {step_name}"
        )
        dirty = bool(self.current_recipe.get("dirty"))
        wafer = self.current_recipe.get("wafer_properties", {})
        wafer_type = wafer.get("type", "Patterned")
        alignment_state = self.current_recipe.get("alignment", {})
        derivative_reference_ready = (
            not alignment_state.get("derivative_origin_reselection_required")
            or alignment_state.get("derivative_origin_reselected")
        )
        alignment_ready = bool(alignment_state.get("sites_defined")) and derivative_reference_ready
        wafer_map = self.current_recipe.get("wafer_map", {})
        die_corner_ready = not wafer_map.get("die_corner_adjustment_required", False)
        map_ready = bool(wafer_map.get("die_pattern_defined")) and die_corner_ready
        dbb_state = normalized_dbb_state(self.current_recipe.get("dbb"))
        design_ready = (
            alignment_ready
            and bool(wafer_map.get("reticle_qualification"))
            and bool(self.current_recipe.get("pixel_perfect_enabled", True))
        )
        self.design_registration_action.setEnabled(True)
        self.dbc_setup_action.setEnabled(True)
        self.dbb_setup_action.setEnabled(True)
        server_status = dbb_state.get("server_status", "Active (simulated)")
        self.dbb_status_label.setText(
            "DBB ACTIVE" if server_status == "Active (simulated)"
            else ("DBB INACTIVE" if server_status == "Inactive" else "DBB STOPPED")
        )
        self.dbb_status_label.setStyleSheet(
            f"background: {'#63c96b' if server_status == 'Active (simulated)' else '#e0b55a' if server_status == 'Inactive' else '#d56a62'}; "
            "border: 1px solid #7c786f;"
        )
        self.wafermap_image_acquired = bool(wafer_map.get("die_pattern_defined"))
        self.wafermap_image_button.setEnabled(True)
        if not self.wafermap_image_acquired:
            self.wafermap_image_visible = False
        self._sync_wafermap_image_controls()
        self._tests_setup_ready = self._tests_setup_access_ready(self.current_recipe)
        self.tests_button.setEnabled(True)
        defined_tests = [
            test for test in self.current_recipe.get("tests", [])
            if test.get("mode") != "No Test"
        ]
        self.lot_plan_button.setEnabled(True)
        self.run_lot_plan_action.setEnabled(True)
        lot_plan = self.current_recipe.get("lot_plan", {})
        has_assignments = any(lot_plan.get("assignments", {}).values())
        self.wafer_post_processing_button.setEnabled(True)
        wafer_setup_ready = wafer_type == "Blank" or (alignment_ready and map_ready)
        orientation_setups_ready = self._all_test_orientation_setups_ready(
            self.current_recipe
        )
        run_ready = bool(defined_tests) and orientation_setups_ready and (
            self.current_recipe.get("status") == "Valid"
            or (
                bool(self.current_recipe.get("test_setup_valid"))
                and wafer_setup_ready
            )
        )
        self._run_setup_ready = run_ready
        self.setup_run_button.setEnabled(True)
        self.run_wafer_button.setEnabled(True)
        self.review_wafer_button.setEnabled(True)
        self._refresh_snapshot_review_action()
        self.save_inspection_button.setStyleSheet(
            "border: 2px solid #d39a00;" if dirty else ""
        )
        if message:
            self.statusBar().showMessage(message)

    def _tests_setup_access_ready(self, recipe=None):
        recipe = recipe or self.current_recipe
        wafer = recipe.get("wafer_properties") or {}
        if wafer.get("type", "Patterned") == "Blank":
            return True
        wafer_map = self._effective_wafer_map_state(recipe)
        if wafer_map.get("die_corner_adjustment_required"):
            return False
        alignment = self._effective_alignment_state(recipe)
        derivative_reference_ready = (
            not alignment.get("derivative_origin_reselection_required")
            or alignment.get("derivative_origin_reselected")
        )
        setup_complete = (
            bool(alignment.get("sites_defined"))
            and derivative_reference_ready
            and bool(wafer_map.get("die_pattern_defined"))
        )
        if setup_complete or recipe.get("status") == "Valid":
            return True
        recipe_id = recipe.get("id", "")
        return bool(recipe_id and self.recipe_store.get_recipe(recipe_id) is not None)

    def _effective_alignment_state(self, recipe=None):
        recipe = recipe or self.current_recipe
        alignment = dict(recipe.get("alignment") or {})
        if recipe is not self.current_recipe:
            return alignment
        page = self.workspace_pages.get("alignment")
        live_result = getattr(page, "alignment_result", None)
        if live_result:
            alignment.update(dict(live_result))
        return alignment

    def _effective_wafer_map_state(self, recipe=None):
        recipe = recipe or self.current_recipe
        wafer_map = dict(recipe.get("wafer_map") or {})
        if recipe is not self.current_recipe:
            return wafer_map
        page = self.workspace_pages.get("wafer_map")
        if page is not None and getattr(page, "changed", False):
            live_state = page.result_state()
            if live_state:
                wafer_map.update(dict(live_state))
        return wafer_map

    def _test_development_context(self, recipe=None):
        recipe = recipe or self.current_recipe
        wafer = recipe.get("wafer_properties") or {}
        alignment = self._effective_alignment_state(recipe)
        wafer_map = self._effective_wafer_map_state(recipe)
        derivative_ready = (
            not alignment.get("derivative_origin_reselection_required")
            or alignment.get("derivative_origin_reselected")
        )
        geometry_ready = bool(wafer_map.get("die_pattern_defined")) and not wafer_map.get(
            "die_corner_adjustment_required", False
        )
        configured_in_session = (
            bool(alignment.get("sites_defined"))
            and derivative_ready
            and geometry_ready
        )
        live_alignment_page = self.workspace_pages.get("alignment") if recipe is self.current_recipe else None
        live_alignment_result = getattr(live_alignment_page, "alignment_result", None) or {}
        runtime_ready = bool(
            self.wafer_runtime_state.get("wafer_loaded")
            and (
                self.wafer_runtime_state.get("wafer_aligned")
                or live_alignment_result.get("aligned")
            )
        )
        if wafer.get("type", "Patterned") == "Blank":
            ready = False
        elif self._recipe_loaded_from_library:
            ready = configured_in_session and runtime_ready
        else:
            ready = configured_in_session or runtime_ready
        return {
            "wafer_loaded": ready,
            "wafer_aligned": ready,
            "wafer_geometry_defined": geometry_ready,
            "die_size_um": (
                float(wafer_map.get("die_pitch_width") or 5100.0),
                float(wafer_map.get("die_pitch_height") or 16600.0),
            ),
        }

    def _test_development_wafer_ready(self, recipe=None):
        return bool(self._test_development_context(recipe)["wafer_aligned"])

    def _refresh_home_status(self):
        if not hasattr(self, "home_status_labels"):
            return
        recipe = self.current_recipe
        runtime = self.wafer_runtime_state
        if runtime.get("wafer_loaded"):
            wafer_state = "Loaded and aligned" if runtime.get("wafer_aligned") else "Loaded"
        else:
            wafer_state = "Not loaded"
        values = {
            "inspection": recipe.get("inspection") or "New",
            "device": recipe.get("device") or "-",
            "step": recipe.get("step") or "-",
            "recipe_status": recipe.get("status") or "Incomplete",
            "wafer_state": wafer_state,
            "results": str(len(self.recipe_store.list_results())),
        }
        for key, value in values.items():
            self.home_status_labels[key].setText(str(value))

    def open_wafer_menu(self):
        self._set_wafer_drawer_expanded(not self._wafer_drawer_open)
        self.statusBar().showMessage(
            "Wafer setup drawer expanded"
            if self._wafer_drawer_open
            else "Wafer setup drawer collapsed",
            3000,
        )
        return self.wafer_drawer

    def _show_wafer_level(self):
        self._activate_workspace_page("setup")
        self._active_route_key = "wafer"
        if not self._wafer_drawer_open:
            self._set_wafer_drawer_expanded(True)
        else:
            self._sync_left_nav_selection("wafer")
        self.statusBar().showMessage("Wafer", 3000)
        return self.wafer_drawer

    def open_select_defect_data(self):
        dialog = SelectDefectDataDialog(self.current_recipe.get("defect_data"), self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted and dialog.changed:
            self.current_recipe["defect_data"] = dict(dialog.attached_data)
            self.current_recipe["dirty"] = True
            attached = dialog.attached_data.get("name", "None") if dialog.attached_data else "None"
            self._set_current_recipe(
                self.current_recipe,
                message=f"Attached defect data: {attached}; save required",
            )
        return False

    def open_tests_setup(
        self,
        checked: bool = False,
        *,
        initial_module: str | None = None,
        initial_test_index: int | None = None,
    ):
        wafer_map = self._effective_wafer_map_state(self.current_recipe)
        if wafer_map.get("die_corner_adjustment_required"):
            QMessageBox.warning(
                self,
                "Adjust Die Corner Required",
                "Adjust the die corner before opening the Test summary grid.",
            )
            return False
        self._tests_setup_ready = self._tests_setup_access_ready(self.current_recipe)
        if not self._tests_setup_ready:
            QMessageBox.warning(
                self,
                "Tests",
                "Align the wafer and define the wafer map before setting up patterned-wafer tests.",
            )
            return False
        wafer = self.current_recipe.get("wafer_properties", self._current_wafer_properties())
        development_context = self._test_development_context(self.current_recipe)
        development_wafer_ready = development_context["wafer_aligned"]
        dialog = TestsSetupDialog(
            self.current_recipe.get("tests", []),
            wafer_type=wafer.get("type", "Patterned"),
            wafer_orientation=self._orientation_label(
                self._active_orientation_key(self.current_recipe)
            ),
            inner_die_defined=bool(wafer_map.get("inner_die_defined", False)),
            wafer_loaded=development_wafer_ready,
            wafer_aligned=development_wafer_ready,
            wafer_geometry_defined=development_context["wafer_geometry_defined"],
            die_size_um=development_context["die_size_um"],
            defect_data=self.current_recipe.get("defect_data"),
            wafer_context_provider=self._test_development_context,
            initial_module=initial_module,
            initial_test_index=(
                self.selected_test_index
                if initial_test_index is None
                else initial_test_index
            ),
            parent=self,
        )
        route_key = {
            "fourier_filter": "test_fourier_filter",
            "light_level": "test_light_level",
            "sensitivity": "test_sensitivity",
            "defect_filters": "test_defect_filters",
            "care_areas": "test_care_areas",
            "sample_plan": "test_sample_plan",
        }.get(initial_module, "tests")
        return self._show_workspace_dialog(
            route_key,
            dialog,
            on_accept=self._apply_tests_setup,
            return_route="tests" if initial_module else "setup",
        )

    def _copy_active_test(self):
        page = self.workspace_pages.get("tests")
        if isinstance(page, TestsSetupDialog) and page.copy_current_test():
            self.paste_test_action.setEnabled(True)
            self.statusBar().showMessage("Current test copied", 3000)

    def _paste_active_test(self):
        page = self.workspace_pages.get("tests")
        if isinstance(page, TestsSetupDialog) and page.paste_current_test():
            self.statusBar().showMessage("Copied test parameters pasted", 3000)

    def _copy_active_sample_plan(self):
        page = self.workspace_pages.get("tests")
        if isinstance(page, TestsSetupDialog) and page.copy_current_sample_plan():
            self.paste_sample_plan_action.setEnabled(True)
            self.statusBar().showMessage("Current sample plan copied", 3000)

    def _paste_active_sample_plan(self):
        page = self.workspace_pages.get("tests")
        if isinstance(page, TestsSetupDialog) and page.paste_current_sample_plan():
            self.statusBar().showMessage("Copied sample plan pasted", 3000)

    def _apply_tests_setup(self, dialog):
        self.selected_test_index = dialog.current_test
        if getattr(dialog, "stage_rotation_performed", False):
            target_orientation = str(self._orientation_degrees(dialog.stage_orientation))
            self._switch_orientation_setup(self.current_recipe, target_orientation)
            self.wafer_runtime_state["required_orientation"] = target_orientation
            self.wafer_runtime_state["wafer_aligned"] = False
        if dialog.result_tests is not None:
            previous_tests = self.current_recipe.get("tests", [])
            self.current_recipe["tests"] = dialog.result_tests
            if dialog.changed or dialog.result_tests != previous_tests:
                self.current_recipe["dirty"] = True
                defined = [test for test in dialog.result_tests if test.get("mode") != "No Test"]
                invalid = [test for test in defined if test.get("status") != "Valid"]
                tests_valid = bool(defined) and not invalid
                alignment_ready = bool(self.current_recipe.get("alignment", {}).get("sites_defined"))
                map_ready = bool(self.current_recipe.get("wafer_map", {}).get("die_pattern_defined"))
                wafer_type = self.current_recipe.get("wafer_properties", {}).get(
                    "type", "Patterned"
                )
                wafer_setup_ready = wafer_type == "Blank" or (
                    alignment_ready and map_ready
                )
                self.current_recipe["test_setup_valid"] = tests_valid
                self.current_recipe["status"] = (
                    "Valid" if tests_valid and wafer_setup_ready else "Incomplete"
                )
                if not defined:
                    state = "No inspection tests are defined."
                elif invalid:
                    state = (
                        f"{len(defined)} test(s) defined; {len(invalid)} require additional setup. "
                        "Open the Tests view to review validation details."
                    )
                else:
                    state = f"{len(defined)} inspection test(s) passed validation."
                self.current_recipe["state"] = state
                self._set_current_recipe(
                    self.current_recipe,
                    message="Inspection test parameters updated; save required",
                )

    def open_lot_plan(self):
        return self._edit_lot_plan(runtime_mode=False, embedded=True)

    def open_run_lot_plan(self):
        self._edit_lot_plan(runtime_mode=True)

    def _edit_lot_plan(self, *, runtime_mode, embedded=False):
        defined = [
            test for test in self.current_recipe.get("tests", [])
            if test.get("mode") != "No Test"
        ]
        if not defined and not self._has_loaded_recipe():
            QMessageBox.warning(self, "Lot Plan", "Define at least one inspection test before creating a Lot Plan.")
            return False
        names = [test.get("name", f"Test {index + 1}") for index, test in enumerate(defined)]
        dialog = LotPlanDialog(
            names,
            self.current_recipe.get("lot_plan"),
            self,
            runtime_mode=runtime_mode,
        )
        if embedded:
            return self._show_workspace_dialog(
                "lot_plan",
                dialog,
                on_accept=lambda page: self._apply_lot_plan(page, runtime_mode=False),
                return_route="setup",
            )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result != QDialog.Accepted or dialog.result_state is None:
            return
        self._apply_lot_plan(dialog, runtime_mode=runtime_mode)

    def _apply_lot_plan(self, dialog, *, runtime_mode):
        if dialog.result_state is None:
            return
        self.current_recipe["lot_plan"] = dialog.result_state
        self.current_recipe["lot_plan_valid"] = True
        self.current_recipe["dirty"] = True
        assignments = sum(
            len(items) for items in dialog.result_state.get("assignments", {}).values()
        )
        source = "Run" if runtime_mode else "Set Up"
        self.current_recipe["state"] = (
            f"Lot Plan contains {assignments} wafer/test assignment(s); last edited from {source}."
        )
        self._set_current_recipe(
            self.current_recipe,
            message="Lot Plan updated; save required",
        )

    def open_wafer_post_processing(self):
        lot_plan = self.current_recipe.get("lot_plan", {})
        if (
            not any(lot_plan.get("assignments", {}).values())
            and not self._has_loaded_recipe()
        ):
            QMessageBox.warning(
                self,
                "Wafer Post Processing",
                "Assign at least one wafer/test combination in the Lot Plan first.",
            )
            return False
        defined_tests = [
            test for test in self.current_recipe.get("tests", [])
            if test.get("mode") != "No Test"
        ]
        test_names = [
            str(test.get("name") or f"Test {index}")
            for index, test in enumerate(defined_tests, start=1)
        ]
        dialog = WaferPostProcessingDialog(
            self.current_recipe.get("wafer_post_processing"),
            test_count=len(test_names),
            tests=test_names,
            parent=self,
        )
        return self._show_workspace_dialog(
            "wafer_post_processing",
            dialog,
            on_accept=self._apply_wafer_post_processing,
            return_route="setup",
        )

    def _apply_wafer_post_processing(self, dialog):
        if dialog.result_state is None:
            return
        self.current_recipe["wafer_post_processing"] = dialog.result_state
        self.current_recipe["wpp_valid"] = True
        self.current_recipe["dirty"] = True
        enabled = sum(
            1 for operation in dialog.result_state.get("operations", [])
            if operation.get("enabled")
        )
        self.current_recipe["state"] = f"Wafer Post Processing has {enabled} enabled operation(s)."
        self._set_current_recipe(
            self.current_recipe,
            message="Wafer Post Processing updated; save required",
        )

    def open_run_one_wafer(self):
        communication = normalized_communication_status(
            self.recipe_store.get_preferences().get("communication")
        )
        if communication["control_mode"] == "Remote":
            QMessageBox.warning(
                self,
                "Run One Wafer",
                "Setup Run is available only in Local control mode. Switch to Online/Local in Tools > SECS.",
            )
            return False
        if not getattr(self, "_run_setup_ready", False):
            QMessageBox.warning(
                self,
                "Run One Wafer",
                "Complete wafer alignment, wafer map, and inspection test validation before running.",
            )
            return False
        dialog = RunOneWaferDialog(
            self.current_recipe,
            self.current_recipe.get("run_setup"),
            self.recipe_store.list_results(),
            self,
        )
        return self._show_workspace_dialog(
            "setup_run",
            dialog,
            on_accept=self._apply_run_setup,
            return_route="setup",
        )

    def _apply_run_setup(self, dialog):
        if dialog.result_setup is None:
            return
        self.current_recipe["run_setup"] = dialog.result_setup
        self.current_recipe["dirty"] = True
        self._set_current_recipe(self.current_recipe, message="Run plan accepted; inspection starting")
        run_recipe = deepcopy(self.current_recipe)
        run_recipe["_previous_results"] = self.recipe_store.list_results()
        status = RunStatusDialog(
            run_recipe,
            dialog.result_setup,
            snapshot_callback=self._open_snapshot_review,
            print_settings=self.recipe_store.get_preferences().get("print_on_run", {}),
            parent=self,
        )
        self.active_run_dialog = status
        self._refresh_snapshot_review_action()
        status_result = status.exec() if hasattr(status, "exec") else status.exec_()
        self.active_run_dialog = None
        self._refresh_snapshot_review_action()
        if status_result != QDialog.Accepted and not status.results:
            return
        overwrite_ids = dialog.result_setup.get("overwrite_result_ids", [])
        if overwrite_ids:
            saved_results = self.recipe_store.overwrite_results(
                overwrite_ids,
                status.results,
                backup=dialog.result_setup.get("backup_lot_result", False),
            )
        else:
            saved_results = [self.recipe_store.save_result(item) for item in status.results]
        self._queue_unavailable_auto_transfers(saved_results, dialog.result_setup)
        if saved_results:
            self.current_recipe["last_result_id"] = saved_results[-1]["id"]
            self.current_recipe["state"] = (
                f"Last run {saved_results[-1]['status'].lower()}; "
                f"{sum(item['defect_count'] for item in saved_results)} defects detected."
            )
            self._set_current_recipe(self.current_recipe, message="Inspection results saved")
            if dialog.result_setup.get("instant_review") and saved_results[-1].get("status") == "Complete":
                self.open_review_results(result=saved_results[-1])

    def _queue_unavailable_auto_transfers(self, results, setup):
        if not setup.get("auto_transfer"):
            return
        transfer_state = normalized_data_transfer(
            self.recipe_store.get_preferences().get("data_transfer")
        )
        communication = normalized_communication_status(
            self.recipe_store.get_preferences().get("communication")
        )
        available = transfer_state["running"] and communication["ilink_enabled"]
        existing_result_ids = {
            item.get("result_id") for item in self.recipe_store.list_transfer_items()
        }
        for result in results:
            if available or result.get("status") != "Complete" or result.get("id") in existing_result_ids:
                continue
            transfer = dict(result.get("transfer", {}))
            transfer["state"] = "Queued"
            result["transfer"] = transfer
            self.recipe_store.save_result(result)
            self.recipe_store.save_transfer_item({
                "result_id": result.get("id"),
                "lot_id": result.get("lot_id", ""),
                "wafer_id": result.get("wafer_id", ""),
                "destination": setup.get("transfer_host") or transfer_state["analysis_system"],
                "status": "Pending",
                "error": "ILink unavailable" if not communication["ilink_enabled"] else "Transfer service stopped",
            })
            self.recipe_store.record_utility_event(
                "Data Transfer",
                f"Lot {result.get('lot_id', '')}, wafer {result.get('wafer_id', '')} queued for transfer",
                severity="Warning",
            )

    def _open_snapshot_review(self, result, snapshot_mode=True, update_callback=None):
        self.open_review_results(
            result=result,
            snapshot_mode=snapshot_mode,
            snapshot_update_callback=update_callback,
        )

    def open_latest_snapshot(self):
        communication = normalized_communication_status(
            self.recipe_store.get_preferences().get("communication")
        )
        if communication["control_mode"] == "Remote":
            QMessageBox.information(
                self,
                "Snapshot Review",
                "Snapshot Review is unavailable while SECS control mode is Remote.",
            )
            return
        active = getattr(self, "active_run_dialog", None)
        if active and not active.finished:
            active._snapshot()
            return
        QMessageBox.information(
            self,
            "Snapshot Review",
            "Snapshot Review is available while an inspection run is in progress.",
        )

    def _refresh_snapshot_review_action(self):
        if not hasattr(self, "snapshot_review_action"):
            return
        self.snapshot_review_action.setEnabled(True)

    def open_review_results(
        self,
        checked=False,
        *,
        result=None,
        snapshot_mode=False,
        snapshot_update_callback=None,
        initial_action=None,
    ):
        if result is None:
            ensure_demo_review_results(self.recipe_store)
            selection = SelectLotResultsDialog(self.recipe_store, self.current_recipe, self)
            selected = selection.exec() if hasattr(selection, "exec") else selection.exec_()
            if selected != QDialog.Accepted or selection.selected_result is None:
                return
            result = selection.selected_result
        workspace = ReviewWorkspace(
            result,
            store=self.recipe_store,
            current_recipe=self.current_recipe,
            snapshot_mode=snapshot_mode,
            snapshot_update_callback=snapshot_update_callback,
            parent=self,
        )
        workspace.set_review_toolbar_visible(self.review_toolbar_visible)
        workspace.set_review_image_toolbar_visible(self.review_image_toolbar_visible)
        if initial_action:
            QTimer.singleShot(0, lambda: workspace.open_manual_tool(initial_action))
        workspace.exec() if hasattr(workspace, "exec") else workspace.exec_()

    def open_dbb_view(self, checked=False, *, result=None):
        if result is None:
            ensure_demo_review_results(self.recipe_store)
            selection = SelectLotResultsDialog(self.recipe_store, self.current_recipe, self)
            selected = selection.exec() if hasattr(selection, "exec") else selection.exec_()
            if selected != QDialog.Accepted or selection.selected_result is None:
                return
            result = selection.selected_result
        dbb_state = result.get("dbb_recipe") or self.current_recipe.get("dbb") or {}
        if not normalized_dbb_state(dbb_state).get("enabled"):
            QMessageBox.information(self, "DBB View", "The selected result was not created with Design Based Binning enabled.")
            return
        dialog = DBBViewDialog(result, dbb_state, self)
        accepted = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if accepted == QDialog.Accepted:
            self.recipe_store.save_result(dialog.result_data)
            self.statusBar().showMessage("DBB analysis and sampling changes saved", 6000)

    def open_sizing_setup(self):
        workspace = SizingSetupTool(self.recipe_store, parent=self)
        workspace.exec() if hasattr(workspace, "exec") else workspace.exec_()
        self.statusBar().showMessage("Sizing Setup Tool closed; workspace saved", 5000)

    def open_sizing_recipe_setup(self):
        dialog = SizingRecipeDialog(self.current_recipe.get("sizing"), self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted and dialog.result_recipe:
            recipe = deepcopy(self.current_recipe)
            recipe["sizing"] = dialog.result_recipe
            recipe["dirty"] = True
            self._set_current_recipe(recipe, message="Sizing recipe updated; save required")

    def import_review_klarf(self):
        filename, _selected = QFileDialog.getOpenFileName(
            self,
            "Import KLARF",
            str(self.recipe_store.path.parent),
            "KLARF Files (*.klarf *.001 *.txt);;All Files (*)",
        )
        if not filename:
            return
        recipes = self.recipe_store.list_recipes()
        if not any(item.get("id") == self.current_recipe.get("id") for item in recipes):
            recipes.append(self.current_recipe)
        match_dialog = KlarfMatchDialog(recipes, self.recipe_store.list_results(), self)
        if (match_dialog.exec() if hasattr(match_dialog, "exec") else match_dialog.exec_()) != QDialog.Accepted:
            return
        try:
            text = Path(filename).read_text(encoding="utf-8", errors="replace")
            imported = import_klarf_text(text, match_dialog.selected_match, source_path=filename)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Import KLARF", str(exc))
            return
        imported["review_mode"] = "Review Only"
        imported = self.recipe_store.save_result(imported)
        self.open_review_results(result=imported)

    def _run_queued_job(self, job):
        recipes = self.recipe_store.list_recipes()
        if not any(item.get("id") == self.current_recipe.get("id") for item in recipes):
            recipes.append(self.current_recipe)
        by_id = {recipe.get("id"): recipe for recipe in recipes}
        results = []
        for item in job_execution_plan(job, recipes):
            recipe = deepcopy(by_id.get(item["recipe_id"], self.current_recipe))
            recipe["_previous_results"] = self.recipe_store.list_results()
            setup = deepcopy(job.get("setup", {}))
            setup.update({
                "lot_id": item["lot_id"],
                "wafer_id": item["wafer_id"] or f"Slot-{item['slot']:02d}",
                "selected_tests": item["selected_tests"],
                "repeat_test": item["repeat_count"] > 1,
                "repeat_count": item["repeat_count"],
            })
            status = RunStatusDialog(
                recipe,
                setup,
                snapshot_callback=self._open_snapshot_review,
                print_settings=self.recipe_store.get_preferences().get("print_on_run", {}),
                parent=self,
            )
            self.active_run_dialog = status
            self._refresh_snapshot_review_action()
            status.exec() if hasattr(status, "exec") else status.exec_()
            results.extend(self.recipe_store.save_result(result) for result in status.results)
            self.active_run_dialog = None
            self._refresh_snapshot_review_action()
        return results

    def open_job_queue(self):
        recipes = self.recipe_store.list_recipes()
        if not any(item.get("id") == self.current_recipe.get("id") for item in recipes):
            recipes.append(self.current_recipe)
        dialog = InspectionJobQueueDialog(
            self.recipe_store,
            recipes,
            run_callback=self._run_queued_job,
            parent=self,
        )
        dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        self._set_current_recipe(self.current_recipe)

    def open_initialize_system(self):
        if self.wafer_runtime_state.get("wafer_loaded"):
            QMessageBox.warning(
                self,
                "Initialize System",
                "Unload the wafer from the stage before initializing any subsystem.",
            )
            return
        dialog = InitializeSubsystemsDialog(self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result != QDialog.Accepted or not dialog.result_subsystems:
            return
        if "Wafer Handling" in dialog.result_subsystems:
            self.wafer_runtime_state["wafer_loaded"] = False
            self.wafer_runtime_state["wafer_aligned"] = False
        if "Stage and Alignment" in dialog.result_subsystems:
            self.wafer_runtime_state["wafer_aligned"] = False
        detail = ", ".join(dialog.result_subsystems)
        self.recipe_store.record_utility_event("Initialization", f"Initialized: {detail}")
        self._set_current_recipe(self.current_recipe)
        self.statusBar().showMessage(f"Initialization completed (simulated): {detail}", 7000)

    def open_preventive_maintenance(self):
        state = self.recipe_store.get_preferences().get("preventive_maintenance", {})
        dialog = PreventiveMaintenanceDialog(state, self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted and dialog.result_state is not None:
            self.recipe_store.update_preferences({"preventive_maintenance": dialog.result_state})
            done = len(dialog.result_state.get("completed", {}))
            self.recipe_store.record_utility_event(
                "Preventive Maintenance",
                f"{dialog.result_state['interval']} checklist saved with {done} completed task(s)",
            )
            self.statusBar().showMessage("Preventive maintenance checklist saved", 5000)

    def open_file_admin_utility(self):
        dialog = FileAdministrationDialog(self.recipe_store, self)
        dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()

    def _open_diagnostics_surface(self, title: str, smart: bool = False):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(620, 360)
        layout = QVBoxLayout(dialog)
        heading = QLabel(title)
        heading.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(heading)
        description = QLabel(
            "Simulator diagnostics expose software state only. Password-protected hardware "
            "service commands, sensors, and actuator tests remain outside the simulator."
        )
        description.setWordWrap(True)
        layout.addWidget(description)
        state = QLabel(
            f"Mode: {'guided fault isolation' if smart else 'configuration and subsystem diagnostics'}\n"
            f"Wafer loaded: {'Yes' if self.wafer_runtime_state.get('wafer_loaded') else 'No'}\n"
            f"Wafer aligned: {'Yes' if self.wafer_runtime_state.get('wafer_aligned') else 'No'}\n"
            f"Active alarms: {sum(1 for item in self.alarm_events if item.get('status') == 'Active')}"
        )
        layout.addWidget(state)
        buttons = QHBoxLayout()
        alarms = QPushButton("Interlock and Alarm Status...")
        alarms.clicked.connect(lambda: (dialog.accept(), self.open_alarm_center()))
        initialize = QPushButton("Initialize System...")
        initialize.clicked.connect(lambda: (dialog.accept(), self.open_initialize_system()))
        close = QPushButton("Close")
        close.clicked.connect(dialog.accept)
        buttons.addWidget(alarms)
        buttons.addWidget(initialize)
        buttons.addStretch(1)
        buttons.addWidget(close)
        layout.addStretch(1)
        layout.addLayout(buttons)
        dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()

    def open_diagnostics_gui(self):
        self._open_diagnostics_surface("Diagnostics GUI")

    def open_smart_diagnostics_gui(self):
        self._open_diagnostics_surface("Smart Diagnostics GUI", smart=True)

    def open_laser_maintenance(self):
        state = self.recipe_store.get_preferences().get("laser_maintenance", {})
        dialog = QDialog(self)
        dialog.setWindowTitle("Laser Site Change Maintenance Schedule")
        dialog.resize(560, 280)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Laser Site Change Maintenance Schedule"))
        status = QLabel(
            f"Site changes recorded: {int(state.get('site_changes', 0))}\n"
            f"Last action: {state.get('last_action', 'Never')}\n"
            "Physical laser site selection and laser power verification are equipment operations."
        )
        status.setWordWrap(True)
        layout.addWidget(status)
        buttons = QHBoxLayout()
        record = QPushButton("Record Site Change")
        record.clicked.connect(dialog.accept)
        close = QPushButton("Close")
        close.clicked.connect(dialog.reject)
        buttons.addWidget(record)
        buttons.addStretch(1)
        buttons.addWidget(close)
        layout.addStretch(1)
        layout.addLayout(buttons)
        accepted = (dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()) == QDialog.Accepted
        if accepted:
            state = {
                **state,
                "site_changes": int(state.get("site_changes", 0)) + 1,
                "last_action": "Recorded in current simulator session",
            }
            self.recipe_store.update_preferences({"laser_maintenance": state})
            self.statusBar().showMessage("Laser maintenance record updated", 5000)

    def open_system_log(self, kind):
        titles = {
            "run": "Run Log",
            "daily": "Daily Logs",
            "recipe": "Recipe History Log",
            "flight": "Flight Recorder Logs",
        }
        if kind == "run":
            selector = OpenLotResultRunLogDialog(self.recipe_store.list_results(), self)
            result = selector.exec() if hasattr(selector, "exec") else selector.exec_()
            if result != QDialog.Accepted or not selector.selected_result:
                return
            selected = selector.selected_result
            title = f"Current Log - {selected.get('lot_id', 'Inspection Run')}"
            entries = selected.get("run_log", [])
            if not entries:
                entries = [{
                    "time": selected.get("created", ""),
                    "level": selected.get("status", "Complete"),
                    "message": (
                        f"Wafer {selected.get('wafer_id', '')}; "
                        f"inspection {selected.get('inspection', '')}; "
                        f"defects {selected.get('defect_count', len(selected.get('defects', [])))}"
                    ),
                }]
            log = RunLogDialog(title, entries, self)
            log.exec() if hasattr(log, "exec") else log.exec_()
            return
        elif kind == "recipe":
            entries = self.recipe_store.history()
        elif kind == "daily":
            entries = [
                item for item in self.recipe_store.utility_events()
                if item.get("severity") in {"Warning", "Error"}
            ]
        else:
            entries = self.recipe_store.utility_events()
            entries.extend(
                {
                    "timestamp": job.get("created", ""),
                    "category": "Inspection Job",
                    "severity": job.get("status", "Queued"),
                    "message": job.get("name", job.get("lot_id", "")),
                }
                for job in self.recipe_store.list_jobs()
            )
        dialog = SystemLogDialog(titles.get(kind, "System Logs"), entries, self)
        dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()

    def open_software_options(self):
        dialog = SoftwareOptionsDialog(self)
        dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()

    def open_e84_signal_display(self):
        existing = getattr(self, "e84_signal_window", None)
        if existing is not None and existing.isVisible():
            existing.showNormal()
            existing.raise_()
            existing.activateWindow()
            return
        enabled = bool(self.recipe_store.get_preferences().get("e84_enabled", False))
        self.e84_signal_window = E84RealTimeSignalDialog(enabled, self)
        self.e84_signal_window.enabled.toggled.connect(
            lambda value: self.recipe_store.update_preferences({"e84_enabled": bool(value)})
        )
        self.e84_signal_window.showMaximized()

    def show_system_error(self, message: str, related_data: str = ""):
        log_directory = self.recipe_store.path.parent / "Daily Logs"
        dialog = ErrorMessageDialog(message, related_data, log_directory, self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if dialog.saved_path:
            self.recipe_store.record_utility_event(
                "System Error",
                f"{message}; saved to {dialog.saved_path}",
                severity="Error",
            )
        return result

    def open_inspection_matching(self):
        preferences = self.recipe_store.get_preferences()
        dialog = InspectionMatchingUtilityDialog(
            self.recipe_store.list_results(),
            preferences.get("inspection_matching", {}),
            self,
        )
        dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        self.recipe_store.update_preferences({"inspection_matching": deepcopy(dialog.settings)})

    def open_equipment_constants(self):
        state = self.recipe_store.get_preferences().get("equipment_constants", {})
        dialog = EquipmentConstantsDialog(state, self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted and dialog.result_constants is not None:
            self.recipe_store.update_preferences({"equipment_constants": dialog.result_constants})
            self.recipe_store.record_utility_event("Equipment Constants", "SECS equipment constants updated")
            self.statusBar().showMessage("Equipment Constants updated", 5000)

    def open_lot_summary(self):
        dialog = LotSummaryDialog(self.recipe_store.list_results(), self)
        dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()

    def open_click_and_mark_configuration(self):
        state = self.recipe_store.get_preferences().get("click_and_mark", {})
        dialog = ClickAndMarkConfigurationDialog(state, self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted and dialog.result_settings is not None:
            self.recipe_store.update_preferences({"click_and_mark": dialog.result_settings})
            self.statusBar().showMessage("Click and Mark configuration updated", 5000)

    def open_delete_inspections(self):
        dialog = DeleteInspectionsDialog(
            self.recipe_store.list_recipes(),
            current_recipe_id=self.current_recipe.get("id", ""),
            parent=self,
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result != QDialog.Accepted or not dialog.result_ids:
            return
        deleted = sum(1 for recipe_id in dialog.result_ids if self.recipe_store.delete_recipe(recipe_id))
        self.recipe_store.record_utility_event("Delete Inspections", f"Deleted {deleted} inspection recipe(s)")
        self.statusBar().showMessage(f"Deleted {deleted} inspection recipe(s)", 5000)

    def open_send_lots(self):
        transfer_state = normalized_data_transfer(
            self.recipe_store.get_preferences().get("data_transfer")
        )
        dialog = SendLotsDialog(
            self.recipe_store.list_results(),
            default_destination=transfer_state["analysis_system"],
            parent=self,
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result != QDialog.Accepted or dialog.result_selection is None:
            return
        communication = normalized_communication_status(
            self.recipe_store.get_preferences().get("communication")
        )
        available = transfer_state["running"] and communication["ilink_enabled"]
        selected_lots = set(dialog.result_selection["lot_ids"])
        destination = dialog.result_selection["destination"]
        queued = 0
        transferred = 0
        queued_result_ids = {item.get("result_id") for item in self.recipe_store.list_transfer_items()}
        for result_item in self.recipe_store.list_results():
            if result_item.get("lot_id") not in selected_lots:
                continue
            transfer = dict(result_item.get("transfer", {}))
            transfer.update({"host": destination, "state": "Transferred" if available else "Queued"})
            result_item["transfer"] = transfer
            self.recipe_store.save_result(result_item)
            if available:
                transferred += 1
            elif result_item.get("id") not in queued_result_ids:
                self.recipe_store.save_transfer_item({
                    "result_id": result_item.get("id"),
                    "lot_id": result_item.get("lot_id", ""),
                    "wafer_id": result_item.get("wafer_id", ""),
                    "destination": destination,
                    "status": "Pending",
                    "error": "ILink unavailable" if not communication["ilink_enabled"] else "Transfer service stopped",
                })
                queued += 1
        message = (
            f"Transferred {transferred} result file(s) (simulated)"
            if available
            else f"Queued {queued} result file(s); Data Transfer is unavailable"
        )
        self.recipe_store.record_utility_event(
            "Data Transfer",
            message,
            severity="Info" if available else "Warning",
        )
        self.statusBar().showMessage(message, 7000)

    def open_rename_lot(self):
        lot_names = [item.get("lot_id", "") for item in self.recipe_store.list_results()]
        dialog = RenameLotDialog(lot_names, self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result != QDialog.Accepted or dialog.result_names is None:
            return
        old_name, new_name = dialog.result_names
        changed = self.recipe_store.rename_lot(old_name, new_name)
        self.recipe_store.record_utility_event(
            "Rename Lot",
            f"Renamed {old_name} to {new_name}; updated {changed} stored item(s)",
        )
        self.statusBar().showMessage(f"Lot {old_name} renamed to {new_name}", 5000)

    def _system_admin_state(self):
        return normalized_system_admin_state(
            self.recipe_store.get_preferences().get("system_admin")
        )

    def _save_system_admin_state(self, state, message="System administration settings updated"):
        normalized = normalized_system_admin_state(state)
        self.recipe_store.update_preferences({"system_admin": normalized})
        self.recipe_store.record_utility_event("System Administration", message)
        self._refresh_e116_action()
        self.statusBar().showMessage(message, 6000)

    def open_erc_manager(self):
        state = self._system_admin_state()
        dialog = ERCManagerDialog(
            self.recipe_store.list_recipes(),
            state.get("erc_catalog"),
            self,
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted and dialog.result_catalog is not None:
            state["erc_catalog"] = dialog.result_catalog
            self._save_system_admin_state(
                state,
                f"ERC cleanup completed; deleted {dialog.deleted_count} ERC(s)",
            )

    def open_control_job_management(self):
        preferences = self.recipe_store.get_preferences()
        state = normalized_system_admin_state(preferences.get("system_admin"))
        enabled, reason = control_job_access(
            state,
            normalized_communication_status(preferences.get("communication")),
            preferences.get("equipment_constants", {}),
        )
        dialog = ControlJobManagementDialog(
            self.recipe_store.list_jobs(), enabled=enabled, reason=reason, parent=self
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted and dialog.result_jobs is not None and enabled:
            self.recipe_store.purge_jobs()
            for job in dialog.result_jobs:
                self.recipe_store.save_job(job)
            self.recipe_store.record_utility_event(
                "Control Job Management", "Control and Process Job states updated"
            )

    def open_substrate_tracking(self):
        state = self._system_admin_state()
        dialog = SubstrateTrackingDialog(
            self.wafer_runtime_state,
            enabled=state["e87_enabled"],
            parent=self,
        )
        dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()

    def open_carrier_management(self):
        state = self._system_admin_state()
        dialog = CarrierManagementDialog(
            self.wafer_runtime_state,
            enabled=state["e87_enabled"],
            parent=self,
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted and dialog.result_state is not None:
            self.wafer_runtime_state.update(dialog.result_state)
            self._set_current_recipe(self.current_recipe)

    def open_user_administration(self, group_tab=False):
        state = self._system_admin_state()
        dialog = UserAdministrationDialog(state, self)
        if group_tab:
            dialog.tabs.setCurrentIndex(1)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted and dialog.result_state is not None:
            self._save_system_admin_state(dialog.result_state, "System Security settings updated")

    def log_off_user(self):
        state = self._system_admin_state()
        previous = state["security"].get("current_user", "")
        state["security"]["current_user"] = ""
        self._save_system_admin_state(state, f"User {previous or 'current user'} logged off")

    def open_signal_tower_configuration(self):
        dialog = SignalTowerDialog(self._system_admin_state(), parent=self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted and dialog.result_state is not None:
            self._save_system_admin_state(dialog.result_state, "Signal Tower configuration saved")

    def open_signal_tower_control(self):
        dialog = SignalTowerDialog(self._system_admin_state(), control_only=True, parent=self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted and dialog.result_state is not None:
            self._save_system_admin_state(dialog.result_state, "Signal Tower control state applied (simulated)")

    def open_load_port_indicators(self):
        dialog = LoadPortIndicatorDialog(self._system_admin_state(), self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted and dialog.result_state is not None:
            self._save_system_admin_state(dialog.result_state, "Load Port Indicator configuration saved")

    def _refresh_e116_action(self):
        if hasattr(self, "e116_action"):
            self.e116_action.blockSignals(True)
            self.e116_action.setChecked(self._system_admin_state()["e116_enabled"])
            self.e116_action.blockSignals(False)

    def toggle_e116(self, enabled):
        state = self._system_admin_state()
        state["e116_enabled"] = bool(enabled)
        self._save_system_admin_state(
            state,
            f"E116 Equipment Performance Tracking {'enabled' if enabled else 'disabled'}",
        )

    def open_user_preferences(self):
        dialog = UserPreferencesDialog(self._system_admin_state(), self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted and dialog.result_state is not None:
            self._save_system_admin_state(dialog.result_state, "User Preferences updated")

    def open_log_settings(self):
        dialog = LogSettingsDialog(self._system_admin_state(), self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted and dialog.result_state is not None:
            self._save_system_admin_state(dialog.result_state, "Diagnostic Log Settings updated")

    def open_backup_archive_restore(self):
        dialog = BackupArchiveRestoreDialog(self._system_admin_state(), self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted and dialog.result_state is not None:
            self._save_system_admin_state(
                dialog.result_state,
                f"{dialog.result_action} completed for simulator data",
            )

    def open_disk_admin(self):
        dialog = DiskAdminDialog(self._system_admin_state(), self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted and dialog.result_state is not None:
            action = "run completed" if dialog.run_now else "schedule updated"
            self._save_system_admin_state(dialog.result_state, f"Disk Admin {action}")

    def open_tools_configuration(self):
        dialog = ToolsConfigurationDialog(self._system_admin_state(), self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted and dialog.result_state is not None:
            self._save_system_admin_state(dialog.result_state, "Remote Tool List updated")

    def _refresh_secs_communication_action(self):
        if not hasattr(self, "secs_communication_action"):
            return
        communication = normalized_communication_status(
            self.recipe_store.get_preferences().get("communication")
        )
        self.secs_communication_action.setText(
            "Disable Communication" if communication["secs_enabled"] else "Enable Communication"
        )

    def toggle_secs_communication(self):
        communication = normalized_communication_status(
            self.recipe_store.get_preferences().get("communication")
        )
        communication["secs_enabled"] = not communication["secs_enabled"]
        if not communication["secs_enabled"]:
            communication["control_mode"] = "Local"
        self.recipe_store.update_preferences({"communication": communication})
        state = "enabled" if communication["secs_enabled"] else "disabled"
        self.recipe_store.record_utility_event("SECS", f"Communication {state}")
        self._refresh_secs_communication_action()
        self._refresh_communication_status()
        self.statusBar().showMessage(f"SECS communication {state} (simulated)", 5000)

    def set_secs_control_mode(self, mode):
        requested_mode = "Remote" if mode == "Remote" else "Local"
        communication = normalized_communication_status(
            self.recipe_store.get_preferences().get("communication")
        )
        communication["secs_enabled"] = True
        communication["control_mode"] = requested_mode
        self.recipe_store.update_preferences({"communication": communication})
        self.recipe_store.record_utility_event(
            "SECS", f"Control mode changed to Online / {requested_mode}"
        )
        self._refresh_secs_communication_action()
        self._refresh_communication_status()
        self.statusBar().showMessage(f"SECS Online / {requested_mode} (simulated)", 5000)
        return True

    def synchronize_host_clock(self):
        state = self._system_admin_state()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        state.setdefault("host_messages", []).append(
            {"time": timestamp, "message": "Clock synchronized with simulated host"}
        )
        self._save_system_admin_state(state, f"SECS host clock synchronized at {timestamp}")

    def open_secs_operations(self, initial_tab=None):
        communication = normalized_communication_status(
            self.recipe_store.get_preferences().get("communication")
        )
        if not communication["secs_enabled"]:
            QMessageBox.information(
                self,
                "SECS Operations",
                "Enable SECS communication before sending E10 states, host messages, or process programs.",
            )
            return
        dialog = SecsOperationsDialog(
            self._system_admin_state(),
            recipes=self.recipe_store.list_recipes(),
            parent=self,
        )
        if initial_tab is not None:
            dialog.tabs.setCurrentIndex(max(0, min(dialog.tabs.count() - 1, int(initial_tab))))
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted and dialog.result_state is not None:
            self._save_system_admin_state(dialog.result_state, "SECS operation queued to simulated host")

    def _refresh_transfer_service_action(self):
        if not hasattr(self, "transfer_service_action"):
            return
        state = normalized_data_transfer(self.recipe_store.get_preferences().get("data_transfer"))
        self.transfer_service_action.setText("Shut Down" if state["running"] else "Start Up")

    def open_transfer_configuration(self):
        state = self.recipe_store.get_preferences().get("data_transfer", {})
        dialog = TransferConfigurationDialog(state, self)
        dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()

    def open_transfer_queue(self):
        before = {item.get("id") for item in self.recipe_store.list_transfer_items()}
        state = self.recipe_store.get_preferences().get("data_transfer", {})
        dialog = DataTransferQueueDialog(self.recipe_store.list_transfer_items(), state, self)
        dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        after = {item.get("id") for item in dialog.result_items}
        for item_id in before - after:
            self.recipe_store.remove_transfer_item(item_id)
        for item in dialog.result_items:
            self.recipe_store.save_transfer_item(item)
        self._refresh_communication_status()

    def toggle_transfer_service(self):
        state = normalized_data_transfer(self.recipe_store.get_preferences().get("data_transfer"))
        state["running"] = not state["running"]
        self.recipe_store.update_preferences({"data_transfer": state})
        label = "started" if state["running"] else "stopped"
        self.recipe_store.record_utility_event("Data Transfer", f"Data Transfer service {label}")
        self._refresh_transfer_service_action()
        self._refresh_communication_status()
        self.statusBar().showMessage(f"Data Transfer service {label} (simulated)", 5000)

    def open_alarm_center(self):
        communication = normalized_communication_status(
            self.recipe_store.get_preferences().get("communication")
        )
        dialog = AlarmCenterDialog(
            self.alarm_events,
            self,
            control_mode=communication["control_mode"],
            remote_clear_allowed=self._remote_clear_alarms_allowed(),
        )
        dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        self.alarm_events = list(dialog.result_alarms)
        active = sum(1 for item in self.alarm_events if item.get("status") == "Active")
        self._refresh_alarm_alert_state()
        self.statusBar().showMessage(f"Alarm Center closed; {active} active alert(s)")

    def _remote_clear_alarms_allowed(self):
        preferences = self.recipe_store.get_preferences()
        equipment = preferences.get("equipment_constants", {})
        if not bool(equipment.get("remote_clear_alarms", True)):
            return False
        security = self._system_admin_state()["security"]
        if not security.get("enabled", True):
            return True
        current_user = security.get("current_user", "")
        user = next(
            (item for item in security.get("users", []) if item.get("username") == current_user),
            None,
        )
        levels = {"Operator": 0, "Engineer": 1, "Expert": 2, "System Administrator": 3}
        required = security.get("privileges", {}).get("Remote Mode Clear Alarms", "Expert")
        return bool(user) and levels.get(user.get("access", "Operator"), 0) >= levels.get(required, 2)

    def _refresh_alarm_alert_state(self):
        active = sum(1 for item in self.alarm_events if item.get("status") == "Active")
        enabled = active > 0
        if hasattr(self, "alarm_action"):
            self.alarm_action.setEnabled(True)
        if hasattr(self, "alarm_button"):
            self.alarm_button.setEnabled(True)
            self.alarm_button.setToolTip(
                f"Alarm Alert: open interlock and alarm status. {active} active alarm(s)."
                if enabled
                else "Alarm Alert: open interlock and alarm status. No active alarms."
            )
            self.alarm_button.setIcon(self._alarm_alert_icon(enabled))

    def set_alarm_event(
        self,
        name: str,
        *,
        category="SECS",
        clearable=True,
        active=True,
        description="",
        corrective_action="",
    ):
        event = next((item for item in self.alarm_events if item.get("name") == name), None)
        if event is None:
            event = {"name": name}
            self.alarm_events.append(event)
        event.update(
            {
                "category": category,
                "clearable": bool(clearable),
                "status": "Active" if active else "Inactive",
                "description": description,
                "corrective_action": corrective_action,
            }
        )
        self._refresh_alarm_alert_state()

    def _refresh_wafer_status(self):
        if not hasattr(self, "wafer_status_symbol"):
            return
        loaded = bool(self.wafer_runtime_state.get("wafer_loaded"))
        aligned = bool(self.wafer_runtime_state.get("wafer_aligned"))
        state = "aligned" if loaded and aligned else "loaded" if loaded else "empty"
        port = self.wafer_runtime_state.get("wafer_source_port") or self.wafer_runtime_state.get("selected_port", "-")
        selected_slots = self.wafer_runtime_state.get("selected_slots", {})
        slot = self.wafer_runtime_state.get("wafer_source_slot") or selected_slots.get(port, "-")
        tooltip = "No wafer is loaded on the stage."
        if aligned:
            tooltip = f"Wafer Aligned\nPort {port}, Slot {slot}"
        elif loaded:
            tooltip = f"Wafer Loaded\nPort {port}, Slot {slot}"
        self.wafer_status_symbol.setPixmap(self._status_symbol_pixmap("wafer", state))
        self.wafer_status_symbol.setProperty("statusState", state)
        self.wafer_status_symbol.setToolTip(tooltip)
        self.wafer_status_label.setText("Wafer ALIGNED" if aligned else "Wafer LOADED" if loaded else "Wafer EMPTY")
        self.wafer_status_label.setToolTip(tooltip)

    def _refresh_communication_status(self):
        if not hasattr(self, "secs_status_label"):
            return
        state = normalized_communication_status(
            self.recipe_store.get_preferences().get("communication")
        )
        if not state["secs_enabled"]:
            secs_state, secs_text = "disabled", "SECS DISABLED"
            secs_tip = "ISECS: SECS host communication is disabled."
        elif not state.get("secs_connected", True):
            secs_state, secs_text = "disconnected", "SECS DISCONNECTED"
            secs_tip = "ISECS: SECS disconnected."
        elif state["control_mode"] == "Remote":
            secs_state, secs_text = "remote", "SECS REMOTE"
            secs_tip = "ISECS: SECS Online Remote."
        else:
            secs_state, secs_text = "local", "SECS LOCAL"
            secs_tip = "ISECS: SECS Online Local."
        self.secs_status_symbol.setPixmap(self._status_symbol_pixmap("secs", secs_state))
        self.secs_status_symbol.setProperty("statusState", secs_state)
        self.secs_status_symbol.setToolTip(secs_tip)
        self.secs_status_label.setText(secs_text)
        self.secs_status_label.setToolTip(secs_tip)

        transfer = normalized_data_transfer(
            self.recipe_store.get_preferences().get("data_transfer")
        )
        queue = self.recipe_store.list_transfer_items()
        has_progress = any(item.get("status") in {"In Progress", "Transferring"} for item in queue)
        has_failure = any(item.get("status") == "Failed" for item in queue)
        if not transfer["running"] or not state["ilink_enabled"]:
            ilink_state, ilink_text = "shutdown", "ILink SHUTDOWN"
            ilink_tip = "ILink Data Transfer Shutdown. Data transfer was shut down from Tools > Data Transfer."
        elif not state.get("ilink_connected", True):
            ilink_state, ilink_text = "failure", "ILink FAILURE"
            ilink_tip = "ILink Data Transfer Failure. Check connectivity, configuration, translator, or data."
        elif has_progress:
            ilink_state, ilink_text = "progress", "ILink TRANSFER"
            ilink_tip = "ILink Data Transfer in Progress. The Inspector/ILink is currently transferring data."
        elif has_failure:
            ilink_state, ilink_text = "warning", "ILink WARNING"
            ilink_tip = "ILink ready for Data Transfer. Check the transfer dialog for past failures."
        else:
            ilink_state, ilink_text = "ready", "ILink READY"
            ilink_tip = "ILink ready for Data Transfer. The Inspector/ILink is ready to receive a request for data transfer."
        self.ilink_status_symbol.setPixmap(self._status_symbol_pixmap("ilink", ilink_state))
        self.ilink_status_symbol.setProperty("statusState", ilink_state)
        self.ilink_status_symbol.setToolTip(ilink_tip)
        self.ilink_status_label.setText(ilink_text)
        self.ilink_status_label.setToolTip(ilink_tip)
        self._refresh_snapshot_review_action()

    def open_communication_status(self):
        state = self.recipe_store.get_preferences().get("communication")
        dialog = CommunicationStatusDialog(state, self)
        if (dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()) == QDialog.Accepted:
            self.recipe_store.update_preferences({"communication": dialog.result_status})
            self._refresh_secs_communication_action()
            self._refresh_communication_status()
            self.statusBar().showMessage("SECS / ILink simulation status updated", 5000)

    def open_print_on_run(self):
        settings = self.recipe_store.get_preferences().get("print_on_run", {})
        dialog = PrintOnRunDialog(settings, self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted and dialog.result_settings is not None:
            self.recipe_store.update_preferences({"print_on_run": dialog.result_settings})
            self.statusBar().showMessage("Print on Run preferences updated", 5000)

    def open_display_colors(self):
        settings = self.recipe_store.get_preferences().get("display_colors")
        dialog = SamplePlanColorsDialog(settings, self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted and dialog.result_scheme is not None:
            self.recipe_store.update_preferences({"display_colors": dialog.result_scheme})
            self.statusBar().showMessage("Display color preferences updated", 5000)

    def open_alignment_menu(self):
        wafer_type = self._current_wafer_properties().get("type", "Patterned")
        if wafer_type == "Blank":
            QMessageBox.information(
                self,
                "Wafer Alignment",
                "Blank wafers do not require alignment.",
            )
            return False
        if not self.wafer_runtime_state.get("wafer_loaded"):
            QMessageBox.warning(
                self,
                "Wafer Alignment",
                "Load a wafer onto the stage before opening Alignment.",
            )
            return False
        self.alignment_context_active = True
        self.image_display_action.setEnabled(True)
        alignment_state = dict(self.current_recipe.get("alignment", {}))
        if self.current_recipe.get("status") == "Valid":
            alignment_state.setdefault("sites_defined", True)
            alignment_state.setdefault("mode", "DF")
        alignment_state["_derivative"] = bool(
            self.current_recipe.get("recipe_type") == "Derivative"
            or self.current_recipe.get("derived_from")
        )
        alignment_state["_test_optics_defined"] = any(
            test.get("mode") != "No Test" for test in self.current_recipe.get("tests", [])
        )
        alignment_state["_manual_alignment_enabled"] = bool(
            self.current_recipe.get("manual_alignment_enabled", False)
        )
        alignment_state["_alignment_failed"] = bool(
            self.current_recipe.get("alignment_failed", False)
        )
        alignment_state["_registration_failed"] = (
            self.current_recipe.get("alignment_failure_kind") == "registration"
        )
        alignment_state["_temporary_alignment_enabled"] = bool(
            self.current_recipe.get("temporary_alignment_enabled", False)
        )
        alignment_state["_orientation"] = self._active_orientation_key(self.current_recipe)
        alignment = AlignmentMenuDialog(alignment_state=alignment_state)

        def apply_alignment(page):
            if page.alignment_result:
                self.current_recipe["alignment"] = dict(page.alignment_result)
                self._store_active_orientation_setup(self.current_recipe)
                self.wafer_runtime_state["wafer_aligned"] = bool(
                    page.alignment_result.get("aligned")
                )
                if self.current_recipe.get("dbb", {}).get("registered"):
                    self.current_recipe["dbb"]["registered"] = False
                    self.current_recipe["dbb"]["registration_verified"] = False
                self.current_recipe["dirty"] = True
                self._set_current_recipe(
                    self.current_recipe,
                    message="Wafer alignment updated; save required",
                )
            else:
                self.statusBar().showMessage("Wafer Alignment closed without changes", 5000)
            return "setup"

        self.statusBar().showMessage(
            "Wafer Alignment opened in the main workspace."
        )
        return self._show_workspace_dialog(
            "alignment",
            alignment,
            on_accept=apply_alignment,
            return_route="setup",
        )

    def open_wafer_properties(self):
        dialog = WaferPropertiesDialog(self._current_wafer_properties(), self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted and dialog.result_properties:
            old_orientation = self._current_wafer_properties().get("orientation", "Down (180 deg.)")
            properties = deepcopy(dialog.result_properties)
            orientation_changed = properties.pop("orientation_changed", False)
            type_changed = properties.pop("type_changed", False)
            updated = deepcopy(self.current_recipe)
            updated["wafer_properties"] = properties
            self._apply_wafer_property_dependencies(
                updated, orientation_changed=orientation_changed, type_changed=type_changed,
                old_orientation=old_orientation,
            )
            updated["dirty"] = True
            if orientation_changed:
                degrees = self._orientation_degrees(properties["orientation"])
                suggested = deepcopy(updated)
                suggested["inspection"] = f"{self.current_recipe.get('inspection', 'Recipe')}_{degrees}"
                save_dialog = SaveInspectionDialog(
                    suggested,
                    recipe_store=self.recipe_store,
                    parent=self,
                )
                save_result = save_dialog.exec() if hasattr(save_dialog, "exec") else save_dialog.exec_()
                if save_result != QDialog.Accepted or not save_dialog.recipe_values:
                    self.statusBar().showMessage("Wafer orientation change cancelled; original recipe retained")
                    return False
                saved = self.recipe_store.duplicate_recipe(
                    updated, save_dialog.recipe_values["inspection"], derivative=False,
                )
                saved.update(save_dialog.recipe_values)
                saved["path"] = str(
                    self.recipe_store.path.parent / "Recipes" / saved["device"]
                    / saved["step"] / saved["inspection"]
                )
                saved = self.recipe_store.save_recipe(
                    saved, event="Save Rotated Inspection",
                    detail=f"Wafer orientation changed to {degrees} degrees",
                )
                self._set_current_recipe(saved, message=f"Saved rotated inspection {saved['inspection']}")
                return False
            self._set_current_recipe(updated, message="Updated wafer properties; save required")
        return False

    def open_wafer_map(self):
        previous_map = deepcopy(self.current_recipe.get("wafer_map") or {})
        dialog = WaferMapSetupDialog(self, state=previous_map)
        self.statusBar().showMessage("Wafermap View displayed")
        return self._show_workspace_dialog(
            "wafer_map",
            dialog,
            on_accept=lambda page: self._apply_wafer_map(page, previous_map),
            on_reject=self._close_wafer_map,
            return_route="setup",
        )

    def _apply_wafer_map(self, dialog, previous_map):
        if dialog.changed:
            updated_map = dialog.result_state()
            self.current_recipe["wafer_map"] = updated_map
            self._store_active_orientation_setup(self.current_recipe)
            if previous_map != updated_map and self.current_recipe.get("dbb", {}).get("registered"):
                self.current_recipe["dbb"]["registered"] = False
                self.current_recipe["dbb"]["registration_verified"] = False
            defect_data_detached = self._detach_defect_data_for_geometry_change(
                self.current_recipe,
                previous_map,
                updated_map,
            )
            self.current_recipe["dirty"] = True
            message = "Wafermap updated; save required"
            if defect_data_detached:
                message += ". Attached defect data was detached after the geometry change"
            self._set_current_recipe(self.current_recipe, message=message)

    def _close_wafer_map(self, dialog):
        self.statusBar().showMessage("Wafermap View closed")

    def open_design_registration(self):
        wafer_map = self.current_recipe.get("wafer_map", {})
        prerequisites = []
        if not self.current_recipe.get("alignment", {}).get("sites_defined"):
            prerequisites.append("wafer alignment")
        if not wafer_map.get("reticle_qualification"):
            prerequisites.append("reticle boundary")
        if not self.current_recipe.get("pixel_perfect_enabled", True):
            prerequisites.append("Pixel Perfect")
        if prerequisites and not self._has_loaded_recipe():
            QMessageBox.warning(
                self,
                "Design Registration",
                "Complete or enable the following before Design Registration: " + ", ".join(prerequisites),
            )
            return
        dialog = DesignRegistrationDialog(
            self.current_recipe.get("dbb"),
            recipe_device=self.current_recipe.get("device", ""),
            parent=self,
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted and dialog.result_state is not None:
            self.current_recipe["dbb"] = dialog.result_state
            self.current_recipe["dirty"] = True
            self._set_current_recipe(self.current_recipe, message="Design Registration verified; save required")

    def open_dbc_setup(self):
        state = normalized_dbb_state(self.current_recipe.get("dbb"))
        if not state["registered"] and not self._has_loaded_recipe():
            QMessageBox.warning(self, "DBC Setup", "Complete Design Registration before editing DBC examples.")
            return
        dialog = DBCSetupDialog(state, self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted and dialog.result_state is not None:
            self.current_recipe["dbb"] = dialog.result_state
            self.current_recipe["dirty"] = True
            self._set_current_recipe(self.current_recipe, message="DBC examples and bins updated; save required")

    def open_dbb_setup(self):
        state = normalized_dbb_state(self.current_recipe.get("dbb"))
        if not state["registered"] and not self._has_loaded_recipe():
            QMessageBox.warning(self, "Design Based Binning", "Complete Design Registration before DBB setup.")
            return
        dialog = DBBSetupDialog(state, self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted and dialog.result_state is not None:
            self.current_recipe["dbb"] = dialog.result_state
            self.current_recipe["dirty"] = True
            enabled = "enabled" if dialog.result_state["enabled"] else "disabled"
            self._set_current_recipe(self.current_recipe, message=f"Design Based Binning {enabled}; save required")

    def open_die_corner_zoom(self):
        dialog = DieCornerZoomDialog(self)
        dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        self.statusBar().showMessage("Die Corner high mag image closed")

    def open_wafer_map_zoom(self):
        blank = bool(getattr(getattr(self, "overview_wafer_map", None), "blank", False))
        dialog = WaferMapZoomDialog(self, blank=blank)
        dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        self.statusBar().showMessage("Wafer Map image closed")

    def open_care_area_zoom(self):
        dialog = OverviewPreviewDialog(
            "Care Area Image",
            CareAreasPreview(260, 430, show_magnifier=False),
            self,
        )
        dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        self.statusBar().showMessage("Care Area image closed")

    def open_sample_plan_zoom(self):
        dialog = OverviewPreviewDialog(
            "Sample Plan Wafermap",
            SamplePlanPreview(430, show_magnifier=False),
            self,
        )
        dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        self.statusBar().showMessage("Sample Plan wafermap closed")

    def open_wafer_handling(self):
        dialog = WaferHandlingDialog(
            self,
            state=self.wafer_runtime_state,
            recipe=self.current_recipe,
        )
        dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        result_state = dialog.result_state()
        if result_state is not None:
            self.wafer_runtime_state = result_state
        self._refresh_home_status()
        self._refresh_wafer_status()
        self.statusBar().showMessage("Wafer Handling closed")

    def open_image_display(self):
        if not self.alignment_context_active:
            if self._has_loaded_recipe():
                self.alignment_context_active = True
            else:
                self.statusBar().showMessage("Select Set Up > Wafer > Alignment before opening Image Display.")
                return

        if self.image_display_window and self.image_display_window.isVisible():
            self.image_display_window.raise_()
            self.image_display_window.activateWindow()
            return

        self.image_display_window = ImageDisplayWindow(self)
        self.image_display_window.show()
        self.statusBar().showMessage("Image Display Window opened")

    def open_last_alignment_swath_image(self):
        alignment = self.current_recipe.get("alignment") or {}
        images = list(alignment.get("site_images") or [])
        label = images[-1] if images else "Last Alignment Swath (simulated)"
        window = ImageDisplayWindow(self, alignment_mode=alignment.get("mode", "DF"))
        window.setWindowTitle("Last Alignment Swath Image")
        if window.current_image.findText(label) < 0:
            window.current_image.addItem(label)
        window.current_image.setCurrentText(label)
        window._display_current_image(label)
        window.show()
        self.alignment_swath_window = window
        self.statusBar().showMessage("Last Alignment Swath Image opened")
        return window

    def open_review_optics(self):
        dialog = AdvancedOpticsDialog(
            self,
            state=self.current_recipe.get("review_optics"),
        )
        dialog.setWindowTitle("Advanced Review Optics Settings")
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted and dialog.result_settings:
            self.current_recipe["review_optics"] = deepcopy(dialog.result_settings)
            self.current_recipe["dirty"] = True
            self._set_current_recipe(self.current_recipe, message="Review optics updated; save required")

    def configure_recipe_overview(self):
        test_count = max(1, len(self.current_recipe.get("tests") or []))
        dialog = SelectVisibleRecipeParametersDialog(
            self.visible_recipe_parameters,
            self,
            test_count=test_count,
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted and dialog.result_parameters:
            self.visible_recipe_parameters = dialog.result_parameters
            self.recipe_store.update_preferences(
                {"visible_recipe_parameters": self.visible_recipe_parameters}
            )
            self._apply_recipe_overview_visibility()
            self.statusBar().showMessage("Updated visible recipe parameters")

    def _apply_recipe_overview_visibility(self):
        for name, widget in self.recipe_overview_sections.items():
            widget.setVisible(self.visible_recipe_parameters.get(name, True))
        for name, widget in self.recipe_overview_groups.items():
            widget.setVisible(self.visible_recipe_parameters.get(name, True))
        for context in self.test_overview_contexts:
            for name, widget in context["groups"].items():
                widget.setVisible(self.visible_recipe_parameters.get(name, True))
        for name, widget in self.recipe_overview_rows.items():
            widget.setVisible(self.visible_recipe_parameters.get(name, True))

    def _apply_recipe_to_overview(self, recipe):
        recipe_status = recipe.get("status", "Incomplete")
        load_save_status = "Nonoptimal" if recipe.get("dirty") and recipe_status == "Valid" else recipe_status
        recipe_updates = {
            "Recipe Name": recipe.get("inspection", ""),
            "Device Name": recipe.get("device", ""),
            "Layer Name": recipe.get("step", ""),
            "Recipe Type": recipe.get("recipe_type", ""),
            "Approval": recipe.get("approval", ""),
        }
        creation_updates = {
            "Creation Time": recipe.get("date_created", ""),
            "Last Modification": recipe.get("last_modified", ""),
            "Software Version": recipe.get("software_version", ""),
        }
        status_updates = {
            "Validation Status": self._load_save_status_definition(recipe, load_save_status),
        }

        self._set_label_group_values(self.recipe_property_labels, recipe_updates)
        self._set_label_group_values(self.creation_property_labels, creation_updates)
        self._set_label_group_values(self.load_save_status_labels, status_updates)
        wafer_properties = recipe.get("wafer_properties")
        self._apply_wafer_properties(wafer_properties or {})
        wafer_map = recipe.get("wafer_map") or {}
        self._apply_wafer_map_to_overview(wafer_map)
        tests = list(recipe.get("tests") or [{}])
        self.selected_test_index = min(self.selected_test_index, len(tests) - 1)
        self._sync_recipe_test_sections(tests)
        for index, test in enumerate(tests):
            self._apply_test_to_overview(test, index)
        self._apply_wafer_post_processing_to_overview(recipe)
        self._apply_recipe_overview_visibility()
        self._sync_blank_recipe_overview(recipe)

        alignment = recipe.get("alignment") or {}
        self._apply_alignment_to_overview(alignment)
        self._apply_registration_sites_to_overview(recipe)
        self._set_label_group_values(
            self.design_file_labels,
            {"Selected RDF": (recipe.get("dbb") or {}).get("rdf_file") or "-"},
        )
        derivative_reference_pending = (
            alignment.get("derivative_origin_reselection_required")
            and not alignment.get("derivative_origin_reselected")
        )
        alignment_status = self._overview_component_status(
            None if derivative_reference_pending else alignment.get("status"),
            ready=(
                bool(alignment.get("sites_defined"))
                and not derivative_reference_pending
            ),
            invalid=bool(recipe.get("alignment_failed")),
        )
        blank_wafer = (wafer_properties or {}).get("type") == "Blank"
        die_ready = blank_wafer or bool(wafer_map.get("die_pattern_defined"))
        geometry_invalid = bool(wafer_map.get("die_corner_adjustment_required"))
        die_status = self._overview_component_status(
            wafer_map.get("die_layout_status"),
            ready=die_ready,
            invalid=geometry_invalid,
        )
        map_status = self._overview_component_status(
            wafer_map.get("status"),
            ready=die_ready,
            invalid=geometry_invalid,
        )
        wafer_status = "valid" if recipe.get("status") == "Valid" and wafer_properties else "incomplete"
        if hasattr(self, "load_save_status_combo"):
            combo_index = self.load_save_status_combo.findText(str(load_save_status or "Incomplete"))
            self.load_save_status_combo.setCurrentIndex(combo_index if combo_index >= 0 else 0)
        for name, status in {
            "Load/Save Status": load_save_status,
            "Wafer Properties": wafer_status,
            "Alignment": alignment_status,
            "Die Layout": die_status,
            "Wafer Map": map_status,
        }.items():
            dot = self.overview_status_dots.get(name)
            if dot:
                dot.set_status(status)

    @staticmethod
    def _overview_component_status(explicit_status, *, ready: bool, invalid: bool = False) -> str:
        text = str(explicit_status or "").strip().lower().replace(" ", "")
        if invalid or any(word in text for word in ("invalid", "failed", "error")):
            return "Invalid"
        if "nonoptimal" in text or "non-optimal" in text:
            return "Nonoptimal"
        if ready or any(word in text for word in ("valid", "complete", "qualified", "passed")):
            return "Valid"
        return "Incomplete"

    def _apply_alignment_to_overview(self, alignment):
        scores = alignment.get("scores") or {}
        for angle in (180, 90):
            angle_data = scores.get(str(angle)) or scores.get(angle) or {}
            mode = angle_data.get("type") or angle_data.get("mode")
            if angle == 180 and not mode and alignment.get("sites_defined"):
                mode = alignment.get("mode")
            values = {
                "Type": mode or "-",
                "DF Scores": angle_data.get("df_scores") or "-",
                "Uniqueness": angle_data.get("uniqueness") or "-",
                "Sharpness": angle_data.get("sharpness") or "-",
                "Features": angle_data.get("features") or "-",
            }
            for field, value in values.items():
                label = self.alignment_overview_labels.get((angle, field))
                if label is not None:
                    label.setText(str(value))
                    label.setToolTip(str(value))

    def _apply_registration_sites_to_overview(self, recipe):
        sites = list(recipe.get("registration_sites") or [])
        if not sites:
            sites = list((recipe.get("xp_offline") or {}).get("registration_sites") or [])
        counts = {180: 0, 90: 0}
        for site in sites:
            orientation = str(site.get("orientation", site.get("angle", 180)))
            angle = 90 if "90" in orientation else 180
            counts[angle] += 1
        for index, angle in enumerate((180, 90)):
            if index < len(self.registration_site_overview_labels):
                count = counts[angle]
                self.registration_site_overview_labels[index].setText(
                    f"{count} at {angle}°" if count else f"None at {angle}°"
                )

    @staticmethod
    def _overview_orientation(value) -> str:
        text = str(value or "-")
        if "270" in text:
            return "270°"
        if "180" in text or text.lower() == "down":
            return "180°"
        if "90" in text:
            return "90°"
        if text in {"0", "0°"} or text.lower().startswith("up"):
            return "0°"
        return text

    @staticmethod
    def _overview_number(value, decimals=1):
        try:
            return f"{float(value):,.{decimals}f}"
        except (TypeError, ValueError):
            return "-"

    def _apply_wafer_map_to_overview(self, wafer_map):
        wafer_map = wafer_map or {}
        has_die = any(
            wafer_map.get(key) not in (None, "")
            for key in ("die_pitch_width", "die_pitch_height", "scribe_x", "scribe_y", "die_count")
        ) or bool(wafer_map.get("die_pattern_defined"))
        if not has_die:
            updates = {
                "Die Width": "0 um",
                "Die Height": "0 um",
                "Reticle Size": "Not used",
                "Street Size": "Not Defined",
                "Inner Die": "No",
                "Valid Dies": "0",
            }
        else:
            pitch_width = self._overview_number(wafer_map.get("die_pitch_width"))
            pitch_height = self._overview_number(wafer_map.get("die_pitch_height"))
            scribe_x = wafer_map.get("scribe_x")
            scribe_y = wafer_map.get("scribe_y")
            if scribe_x in (None, "") and scribe_y in (None, ""):
                street = "Not Defined"
            else:
                street = f"{self._overview_number(scribe_x)} um x {self._overview_number(scribe_y)} um"
            reticle = (
                f"{wafer_map.get('reticle_width', 1)} x {wafer_map.get('reticle_height', 1)}"
                if wafer_map.get("reticle_qualification")
                else "Not used"
            )
            updates = {
                "Die Width": f"{pitch_width} um",
                "Die Height": f"{pitch_height} um",
                "Reticle Size": reticle,
                "Street Size": street,
                "Inner Die": "Yes" if wafer_map.get("inner_die_defined") else "No",
                "Valid Dies": str(wafer_map.get("die_count", 0)),
            }
        self._set_label_group_values(self.die_layout_labels, updates)

    def _test_overview_values(self, group, label, test_index=0):
        if test_index >= len(self.test_overview_contexts):
            return []
        labels = self.test_overview_contexts[test_index]["labels"]
        return labels.get(group, {}).get(label, [])

    def _set_test_overview_value(self, group, label, value, index=0, *, test_index=0):
        labels = self._test_overview_values(group, label, test_index)
        if index < len(labels):
            labels[index].setText(str(value))
            labels[index].setToolTip(str(value))

    def _apply_test_to_overview(self, test, test_index=0):
        context = self.test_overview_contexts[test_index]
        present = bool(test)
        optics = test.get("inspection_optics") or {}
        channels = list(test.get("channels") or [])
        light_training = test.get("light_training") or {}
        care_areas = test.get("care_areas") or {}
        sample_plan = test.get("sample_plan") or {}
        sensitivity = test.get("sensitivity") or {}

        ido = test.get("ido_classifier") or {}
        ido_name = ido.get("name", "-") if isinstance(ido, dict) else str(ido or "-")
        properties = {
            "Test Name": test.get("name", "No Test"),
            "Orientation": self._overview_orientation(test.get("orientation")) if present else "-",
            "Light Trained": "Trained on tool" if test.get("light_trained") else "Not trained",
            "Save Patch Images": "Yes" if test.get("save_image_patches") else "No",
            "Save Feature Vectors": "Yes" if test.get("save_feature_vectors") else "No",
            "iDO Classifier": ido_name,
            "RBB Recipe": test.get("rbb_recipe") or "-",
            "Dynamic Range": light_training.get("dynamic_range", "-") if present else "-",
        }
        for label, value in properties.items():
            self._set_test_overview_value(
                "Test Properties", label, value, test_index=test_index
            )

        inspection_optics = {
            "Magnification\n(Pixel Size)": optics.get("pixel_size", "-"),
            "Focus Offset": f"{optics.get('focus_offset', test.get('focus_offset', 0))} um" if present else "-",
            "Polarization": optics.get("incident_polarization", "-"),
            "Incidence Angle": optics.get("incidence_angle", "-"),
            "Speed": optics.get("speed", "-"),
        }
        for label, value in inspection_optics.items():
            self._set_test_overview_value(
                "Inspection Optics", label, value, test_index=test_index
            )

        noise_group = light_training.get("noise_box_group") or "-"
        self._set_test_overview_value(
            "Illumination Level Optimization",
            "Noise Boxes",
            noise_group,
            test_index=test_index,
        )

        for index in range(3):
            channel = channels[index] if index < len(channels) else {}
            channel_name = channel.get("name", f"{index + 1}")
            enabled = "On" if channel.get("enabled") else "Off"
            collection = context["collection"]
            if index < len(collection.get("channels", [])):
                collection["channels"][index].setText(f"Channel {channel_name} {enabled}")
                collection["polarization"][index].setText(channel.get("polarization", "-"))
                collection["iris"][index].setText(str(channel.get("iris", "-")).title())
            fourier_label = f"{index + 1} ({['Left', 'Right', 'Center'][index]})"
            self._set_test_overview_value(
                "Fourier Filter", fourier_label,
                "On" if channel.get("use_fourier_filter") else "Off",
                test_index=test_index,
            )
            training_result = channel.get("fourier_training_result")
            if training_result is None:
                training_text = "Valid" if test.get("fourier_trained") else "Not trained"
            else:
                training_text = f"{float(training_result):.1f}"
            self._set_test_overview_value(
                "Fourier Filter", "Training Results",
                training_text, index,
                test_index=test_index,
            )

        light_channels = light_training.get("channels") or channels

        def channel_numbers(key, decimals, default=0.0):
            shown = []
            for item in light_channels[:3]:
                value = item.get(key, default)
                if value in (None, ""):
                    shown.append("")
                else:
                    shown.append(f"{float(value):.{decimals}f}")
            if not any(shown):
                return ""
            return "    ".join(shown)

        context["light_level"]["Light Levels"].setText(channel_numbers("light_level", 1) or "-")
        context["light_level"]["Camera Gains"].setText(channel_numbers("edr", 2) or "-")
        if any(item.get("pilo_noise") not in (None, "") for item in light_channels[:3]):
            context["light_level"]["PILO Noise Values"].setText(channel_numbers("pilo_noise", 1, None))
        context["light_level"]["Exposures"].setText(channel_numbers("exposure", 2, None))

        regions = sensitivity.get("regions") or {}
        region_names = list(regions) or ["-"]
        active_algorithms = []
        for region in regions.values():
            for name, settings in (region.get("algorithms") or {}).items():
                if settings.get("run") and name not in active_algorithms:
                    active_algorithms.append(name)
        algorithm_text = ", ".join(active_algorithms) or "-"
        for index in range(3):
            self._set_test_overview_value(
                "Sensitivity", "Selected Algorithms", algorithm_text, index,
                test_index=test_index,
            )
        self._set_test_overview_value(
            "Sensitivity", "Defined Regions", ", ".join(region_names),
            test_index=test_index,
        )
        segmentation = test.get("segmentation") or {}
        self._set_test_overview_value(
            "Sensitivity", "Segmentation", "In Use" if segmentation.get("valid") else "Not in use",
            test_index=test_index,
        )

        defect_filter = sensitivity.get("defect_filters") or {}
        filters_defined = any(
            bool(value) for key, value in defect_filter.items()
            if key != "run_process_noise_filter" and isinstance(value, (int, float))
        ) or bool(defect_filter.get("run_process_noise_filter"))
        for index in range(3):
            region_name = region_names[index] if index < len(region_names) else "-"
            self._set_test_overview_value(
                "Defect Filters", "Region :", region_name, index,
                test_index=test_index,
            )
            self._set_test_overview_value(
                "Defect Filters", "Filters Defined", "Yes" if filters_defined else "No", index,
                test_index=test_index,
            )

        border = care_areas.get("border") or {}
        if present and border:
            border_text = "{x} μm × {y} μm".format(
                x=self._overview_number(border.get("x"), 2),
                y=self._overview_number(border.get("y"), 2),
            )
        else:
            border_text = "-"
        context["care_area_border"].setText(border_text)
        groups = list(care_areas.get("groups") or [])
        group_count = care_areas.get("group_count")
        if group_count is None:
            group_count = len(groups) if present else "-"
        context["care_area_group_count"].setText(str(group_count))
        context["sample_plan_label"].setText(
            str(sample_plan.get("inspection_type", "-") if present else "-")
        )
        inspectable = sample_plan.get("total_inspectable_dies")
        if not present or inspectable in (None, ""):
            dies_text = "-"
        else:
            try:
                dies_text = str(int(inspectable))
            except (TypeError, ValueError):
                dies_text = str(inspectable)
        context["sample_plan_dies"].setText(dies_text)

    def _apply_wafer_post_processing_to_overview(self, recipe):
        state = recipe.get("wafer_post_processing") or {}
        enabled = [
            str(item.get("name", "")).strip()
            for item in state.get("operations", [])
            if item.get("enabled") and str(item.get("name", "")).strip()
        ]
        configured = bool(state)
        status = (
            "Valid" if recipe.get("wpp_valid")
            else "Incomplete" if configured
            else "Not configured"
        )
        updates = {
            "Processing Status": status,
            "Template": state.get("template_name") or "Default",
            "Enabled Operations": str(len(enabled)),
            "Execution Order": " -> ".join(enabled) if enabled else "None",
        }
        self._set_label_group_values(self.wpp_overview_labels, updates)

    def _set_label_group_values(self, label_map, values):
        for key, value in values.items():
            label = label_map.get(key)
            if label:
                display_value = str(value)
                label.setText(display_value)
                label.setToolTip(display_value)

    def _current_wafer_properties(self):
        properties = {
            "orientation": self.wafer_property_labels["Orientation"].text(),
            "type": self.wafer_property_labels["Wafer Type"].text(),
            "laser_power_sensitive": self.wafer_property_labels["Laser Power Sensitive"].text() == "Yes",
            "laser_power_factor": self.wafer_property_labels["Laser Power Factor"].text(),
            "layer": self.wafer_property_labels["Layer"].text(),
            "dark_wafer_auto_focus": self.wafer_property_labels["Dark Wafer"].text() == "Yes",
            "wafer_darkness_level": self.wafer_property_labels["Wafer Darkness Level"].text(),
        }
        stored = self.current_recipe.get("wafer_properties") or {}
        if stored.get("layer_types"):
            properties["layer_types"] = deepcopy(stored["layer_types"])
        return properties

    @staticmethod
    def _orientation_degrees(orientation):
        text = str(orientation).lower()
        for value in (270, 180, 90, 0):
            if str(value) in text:
                return value
        if "left" in text:
            return 270
        if "right" in text:
            return 90
        if "down" in text:
            return 180
        if "up" in text:
            return 0
        return 180

    @classmethod
    def _orientation_label(cls, orientation):
        return {
            0: "Up (0 deg.)",
            90: "Right (90 deg.)",
            180: "Down (180 deg.)",
            270: "Left (270 deg.)",
        }[cls._orientation_degrees(orientation)]

    def _active_orientation_key(self, recipe=None):
        recipe = recipe or self.current_recipe
        value = recipe.get("active_setup_orientation")
        if value is None:
            value = self.wafer_runtime_state.get(
                "required_orientation",
                (recipe.get("wafer_properties") or {}).get(
                    "orientation", "Down (180 deg.)"
                ),
            )
        return str(self._orientation_degrees(value))

    def _store_active_orientation_setup(self, recipe, orientation=None):
        key = str(
            self._orientation_degrees(
                orientation if orientation is not None else self._active_orientation_key(recipe)
            )
        )
        profiles = deepcopy(recipe.get("orientation_setups") or {})
        profiles[key] = {
            "alignment": deepcopy(recipe.get("alignment") or {}),
            "wafer_map": deepcopy(recipe.get("wafer_map") or {}),
        }
        recipe["orientation_setups"] = profiles
        recipe["active_setup_orientation"] = key
        return key

    def _switch_orientation_setup(self, recipe, target_orientation):
        source_key = self._active_orientation_key(recipe)
        self._store_active_orientation_setup(recipe, source_key)
        target_key = str(self._orientation_degrees(target_orientation))
        profile = (recipe.get("orientation_setups") or {}).get(target_key)
        if profile:
            recipe["alignment"] = deepcopy(profile.get("alignment") or {})
            recipe["wafer_map"] = deepcopy(profile.get("wafer_map") or {})
        else:
            recipe["alignment"] = {}
            recipe["wafer_map"] = {}
        recipe["active_setup_orientation"] = target_key
        recipe["dirty"] = True

    def _all_test_orientation_setups_ready(self, recipe):
        wafer_type = (recipe.get("wafer_properties") or {}).get("type", "Patterned")
        if wafer_type == "Blank":
            return True
        active_key = self._active_orientation_key(recipe)
        profiles = recipe.get("orientation_setups") or {}
        required = {
            str(self._orientation_degrees(test.get("orientation", active_key)))
            for test in recipe.get("tests", [])
            if test.get("mode") != "No Test"
        }
        for key in required:
            if key == active_key:
                alignment = recipe.get("alignment") or {}
                wafer_map = recipe.get("wafer_map") or {}
            else:
                profile = profiles.get(key) or {}
                alignment = profile.get("alignment") or {}
                wafer_map = profile.get("wafer_map") or {}
            if not alignment.get("sites_defined"):
                return False
            if not wafer_map.get("die_pattern_defined"):
                return False
            if wafer_map.get("die_corner_adjustment_required"):
                return False
        return True

    @staticmethod
    def _rotate_point(point, side, turns):
        x, y = point
        for _ in range(turns % 4):
            x, y = side - 1 - y, x
        return [x, y]

    @staticmethod
    def _rotate_unit_rect(area, turns):
        x, y, width, height = [float(value) for value in area[:4]]
        for _ in range(turns % 4):
            x, y, width, height = 1.0 - y - height, x, height, width
        return [x, y, width, height] + list(area[4:])

    @staticmethod
    def _detach_defect_data_for_geometry_change(recipe, previous_map=None, updated_map=None):
        if not recipe.get("defect_data"):
            return False
        if previous_map is not None and updated_map is not None:
            geometry_keys = {
                "die_value_mode", "die_pitch_width", "die_pitch_height", "origin_die",
                "adjust_die_corner_mode", "adjusted_die_corner", "inner_die_rows",
                "inner_die_columns",
            }
            if all(previous_map.get(key) == updated_map.get(key) for key in geometry_keys):
                return False
        recipe["defect_data"] = {}
        return True

    def _apply_wafer_property_dependencies(
        self, recipe, *, orientation_changed, type_changed, old_orientation=None,
    ):
        properties = recipe.get("wafer_properties") or {}
        old_orientation = old_orientation or self._current_wafer_properties().get(
            "orientation", "Down (180 deg.)"
        )
        old_degrees = self._orientation_degrees(old_orientation)
        new_degrees = self._orientation_degrees(properties.get("orientation"))
        turns = ((new_degrees - old_degrees) // 90) % 4
        tests = recipe.get("tests") or []
        if orientation_changed:
            self._detach_defect_data_for_geometry_change(recipe)
            alignment = recipe.setdefault("alignment", {})
            alignment.update({"sites_defined": False, "trained": False, "status": "Incomplete"})
            wafer_map = recipe.setdefault("wafer_map", {})
            coordinates = list(wafer_map.get("invalid_die") or [])
            for name in ("origin_die", "reference_die", "adjusted_die_corner"):
                if wafer_map.get(name):
                    coordinates.append(wafer_map[name])
            side = max([55] + [int(max(point)) for point in coordinates if len(point) >= 2]) + 1
            for name in ("origin_die", "reference_die", "adjusted_die_corner"):
                point = wafer_map.get(name)
                if point and len(point) >= 2:
                    wafer_map[name] = self._rotate_point(point[:2], side, turns)
            wafer_map["invalid_die"] = [
                self._rotate_point(point[:2], side, turns)
                for point in wafer_map.get("invalid_die") or [] if len(point) >= 2
            ]
            if turns % 2:
                wafer_map["reticle_width"], wafer_map["reticle_height"] = (
                    wafer_map.get("reticle_height", 1), wafer_map.get("reticle_width", 1),
                )
            wafer_map["geometry_rotation_degrees"] = (
                int(wafer_map.get("geometry_rotation_degrees", 0)) + turns * 90
            ) % 360
            for test in tests:
                test["fourier_trained"] = False
                test["light_trained"] = False
                test["status"] = "Incomplete"
                care_areas = test.setdefault("care_areas", {})
                for group in care_areas.get("groups") or []:
                    group["areas"] = [
                        self._rotate_unit_rect(area, turns)
                        for area in group.get("areas") or [] if len(area) >= 4
                    ]
                    aca = group.get("aca") or {}
                    for name in ("search_area", "training_area"):
                        area = aca.get(name)
                        if area and len(area) >= 4:
                            aca[name] = self._rotate_unit_rect(area, turns)
                care_areas["geometry_rotation_degrees"] = (
                    int(care_areas.get("geometry_rotation_degrees", 0)) + turns * 90
                ) % 360
        if type_changed:
            for test in tests:
                test["status"] = "Incomplete"
                test["validation_errors"] = ["Wafer type changed; test setup must be reviewed."]
        if orientation_changed or type_changed:
            recipe["status"] = "Incomplete"
            recipe["state"] = "Wafer properties changed; affected setup components require review."

    def _load_save_status_definition(self, recipe, status: str) -> str:
        normalized = str(status or "Incomplete")
        if normalized == "Valid":
            validated_on = recipe.get("validation_date") or recipe.get("last_modified") or ""
            when = f" on {validated_on}" if validated_on else ""
            return f"<b>Valid recipe:</b> The recipe successfully passed validation{when}."
        if normalized == "Nonoptimal":
            return (
                "<b>Nonoptimal:</b> The recipe can be used, but one or more parameters are not optimal."
            )
        if normalized == "Invalid":
            detail = recipe.get("state") or "The recipe failed validation."
            return f"<b>Invalid:</b> {detail}"
        detail = recipe.get("state") or "Recipe setup is not complete."
        return f"<b>Incomplete:</b> {detail}"

    def _new_recipe_has_completed_content(self, recipe) -> bool:
        recipe = recipe or {}
        name = str(recipe.get("inspection") or "").strip()
        if name and name != "New":
            return True
        if str(recipe.get("status") or "") in {"Valid", "Nonoptimal", "Invalid"}:
            return True
        if (recipe.get("alignment") or {}).get("sites_defined"):
            return True
        wafer_map = recipe.get("wafer_map") or {}
        if wafer_map.get("die_pattern_defined"):
            return True
        for test in recipe.get("tests") or []:
            if test.get("name") or str(test.get("status") or "") == "Valid":
                return True
        return False

    def _recipe_shows_identity(self, recipe=None) -> bool:
        recipe = recipe if recipe is not None else self.current_recipe
        if not self._overview_is_blank_recipe(recipe):
            return True
        return self._new_recipe_has_completed_content(recipe or {})

    def _overview_is_blank_recipe(self, recipe=None) -> bool:
        recipe = recipe if recipe is not None else self.current_recipe
        if self._recipe_loaded_from_library:
            return False
        return not self._has_loaded_recipe(recipe or {})

    def _sync_blank_recipe_overview(self, recipe):
        blank = self._overview_is_blank_recipe(recipe)
        show_identity = self._recipe_shows_identity(recipe)
        if not show_identity:
            for key in ("Recipe Name", "Device Name", "Layer Name"):
                label = self.recipe_property_labels.get(key)
                if label is not None:
                    label.setText("")
                    label.setToolTip("")
        if hasattr(self, "load_save_status_combo"):
            self.load_save_status_combo.hide()
        validation_row = self.recipe_overview_rows.get("Validation Status")
        if validation_row is not None:
            validation_row.setVisible(
                show_identity and self.visible_recipe_parameters.get("Validation Status", True)
            )
        if hasattr(self, "load_save_status_scroll"):
            self.load_save_status_scroll.setVisible(True)
        load_save_dot = self.overview_status_dots.get("Load/Save Status")
        if load_save_dot is not None:
            load_save_dot.setVisible(show_identity)
        for widget in getattr(self, "alignment_detail_widgets", []):
            widget.setVisible(not blank)
        for widget in getattr(self, "registration_site_rows", []):
            widget.setVisible(not blank)
        for name in ("Laser Power Factor", "Layer"):
            row = self.recipe_overview_rows.get(name)
            if row is not None:
                row.setVisible(
                    (not blank) and self.visible_recipe_parameters.get(name, True)
                )
        wafer_map = getattr(self, "overview_wafer_map", None)
        if wafer_map is not None:
            wafer_map.setVisible(True)
            wafer_map.set_blank(blank)
        design = self.recipe_overview_groups.get("Design Files")
        wafer_grid = getattr(self, "wafer_layout_grid", None)
        if design is not None and wafer_grid is not None:
            show_design = self.visible_recipe_parameters.get("Design Files", True)
            design.setVisible(show_design)
            design.setMaximumWidth(16777215 if show_design else 0)
            wafer_grid.setColumnStretch(6, 14 if show_design else 0)
        wafer_map_group = self.recipe_overview_groups.get("Wafer Map")
        if wafer_map_group is not None:
            self._set_overview_divider(
                wafer_map_group,
                design is not None and not design.isHidden(),
            )
        for widget in (
            getattr(self, "die_corner_map", None),
            *getattr(self, "overview_care_previews", []),
        ):
            if widget is not None:
                widget.setVisible(not blank)

    def _apply_wafer_properties(self, properties):
        normalized = {
            "diameter": "300 mm",
            "type": "Patterned",
            "orientation": "Down",
            "align_mark": "Notched",
            "laser_power_sensitive": True,
            "laser_power_factor": "0.03500",
            "layer": "-",
            "dark_wafer_auto_focus": False,
            "wafer_darkness_level": "Level 1",
        }
        normalized.update(properties or {})
        orientation = str(normalized["orientation"])
        if "180" in orientation or orientation.lower() == "down":
            orientation = "Down"
        updates = {
            "Diameter": str(normalized.get("diameter") or "300 mm"),
            "Wafer Type": normalized["type"],
            "Orientation": orientation,
            "Align Mark": str(normalized.get("align_mark") or "Notched"),
            "Laser Power Sensitive": "Yes" if normalized["laser_power_sensitive"] else "No",
            "Laser Power Factor": normalized["laser_power_factor"],
            "Layer": normalized["layer"],
            "Dark Wafer": "Yes" if normalized["dark_wafer_auto_focus"] else "No",
            "Wafer Darkness Level": normalized["wafer_darkness_level"],
        }
        self._set_label_group_values(self.wafer_property_labels, updates)

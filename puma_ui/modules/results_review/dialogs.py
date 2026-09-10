from __future__ import annotations

from copy import deepcopy
from collections import Counter
import json
import math
from pathlib import Path

from ...qt_compat import (
    QAbstractItemView,
    QApplication,
    QColor,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QDesktopServices,
    QFileDialog,
    QFrame,
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
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QStyle,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    Qt,
    QUrl,
    QVBoxLayout,
    QWidget,
)
from ..wafer_post_processing import WaferPostProcessingDialog
from ..inspection_tests import IdoClassifierDialog, NuisanceFilterSetupDialog
from .models import (
    analyze_optics_modes,
    apply_binner,
    apply_review_offset,
    apply_super_class_scheme,
    combine_sensitivity_results,
    auto_label_result,
    default_filter_state,
    default_filter_analysis_state,
    export_klarf_text,
    evaluate_sensitivity_tuning,
    execute_filter_analysis,
    filter_defects,
    filtered_result_as,
    merge_result,
    normalized_filter_analysis_state,
    result_matches_recipe,
    review_summary,
    select_wafer_transfer_defects,
)


GRID_COLUMNS = [
    ("id", "ID"),
    ("die_x", "Die X"),
    ("die_y", "Die Y"),
    ("test", "Test"),
    ("class_code", "Class"),
    ("size_um", "Size (um)"),
    ("signal", "Signal"),
    ("roughbin", "Roughbin"),
    ("ido_rough_code", "Rough Class"),
    ("ido_rough_group", "Rough Group"),
    ("cluster_id", "Cluster ID"),
    ("repeater_id", "Repeater ID"),
    ("cag_code", "CAG Code"),
    ("macro_sig_class", "Macro Sig Class"),
    ("macro_sig_id", "Macro Sig ID"),
    ("micro_sig_class", "Micro Sig Class"),
    ("super_class", "Super Class"),
    ("dbb_global_bin", "DBB Global Bin"),
    ("dbb_manual_bin", "DBB Manual Bin"),
    ("dbc_bin", "DBC Bin"),
    ("dbg_group", "DBG Group"),
    ("dbg_similarity", "DBG Similarity"),
    ("dci", "DCI"),
    ("dci_range", "DCI Range (%)"),
    ("pci", "PCI"),
    ("line_complexity", "Line Complexity"),
    ("pattern_density", "Pattern Density"),
    ("ebb_pattern_density", "EBB Pattern Density"),
    ("ebb_overlap_ratio", "EBB Overlap Ratio"),
    ("polygon_density", "Polygon Density"),
    ("pattern_granularity", "Pattern Granularity"),
    ("min_line_width_nm", "Min Line Width (nm)"),
    ("min_space_nm", "Min Space (nm)"),
    ("floor_plan_id", "Floor Plan ID"),
    ("design_layer", "Design Layer"),
    ("design_x_nm", "Design X (nm)"),
    ("design_y_nm", "Design Y (nm)"),
    ("npi_template", "NPI Template"),
    ("npi_confidence", "NPI Confidence"),
    ("sensitivity_region", "Sensitivity Region"),
    ("detection_algorithms", "Detection Algorithms"),
    ("threshold_mode", "Threshold Mode"),
    ("HLATCFAbsmin", "HLAT CF Absmin"),
    ("HLATCF_CH1_Noise", "HLAT CF CH1 Noise"),
    ("HLATCF_CH1_Absmin", "HLAT CF CH1 Absmin"),
    ("HLATCF_CH1_Gradient", "HLAT CF CH1 Gradient"),
    ("HLATCF_CH1_Color", "HLAT CF CH1 Color"),
    ("HLATCF_CH2_Noise", "HLAT CF CH2 Noise"),
    ("HLATCF_CH2_Absmin", "HLAT CF CH2 Absmin"),
    ("HLATCF_CH2_Gradient", "HLAT CF CH2 Gradient"),
    ("HLATCF_CH2_Color", "HLAT CF CH2 Color"),
    ("marked", "Marked"),
    ("reviewed", "Reviewed"),
]

LOT_RESULT_COLUMNS = [
    ("lot_id", "Lot ID"),
    ("wafer_id", "Wafer ID"),
    ("inspection", "Inspection"),
    ("completed", "Last Modified"),
    ("status", "Status"),
    ("recipe_match", "Recipe"),
    ("defect_count", "Defects"),
    ("device", "Device"),
    ("step", "Process Step"),
]


def _exec(dialog):
    return dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()


class WaferDefectMap(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.defects = []
        self.selected_id = None
        self.selected_ids = set()
        self.on_selected = None
        self.on_select_toggle = None
        self.on_area_selected = None
        self.drag_start = None
        self.drag_end = None
        self.zoom_factor = 1.0
        self.show_die = True
        self.show_defects = True
        self.show_counts = False
        self.display_rules = []
        self.setMinimumSize(180, 140)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored)

    def set_defects(self, defects):
        self.defects = list(defects)
        self.update()

    def select_defect(self, defect_id):
        self.selected_id = defect_id
        self.update()

    def set_selected_ids(self, defect_ids):
        self.selected_ids = set(defect_ids)
        self.update()

    def set_zoom(self, factor):
        self.zoom_factor = max(0.5, min(3.0, float(factor)))
        self.update()

    def set_display_rules(self, rules):
        self.display_rules = deepcopy(rules or [])
        self.update()

    def _geometry(self):
        side = max(40, (min(self.width(), self.height()) - 28) * self.zoom_factor)
        return (self.width() - side) / 2, (self.height() - side) / 2, side

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#7d7f80"))
        x0, y0, side = self._geometry()
        painter.setPen(QPen(QColor("#202020"), 1))
        painter.setBrush(QColor("#f4f4f1"))
        painter.drawEllipse(int(x0), int(y0), int(side), int(side))
        if self.show_die:
            painter.setPen(QPen(QColor("#c9c9c5"), 1))
            step = max(12, int(side / 22))
            for offset in range(step, int(side), step):
                painter.drawLine(int(x0 + offset), int(y0 + 8), int(x0 + offset), int(y0 + side - 8))
                painter.drawLine(int(x0 + 8), int(y0 + offset), int(x0 + side - 8), int(y0 + offset))
        if not self.show_defects:
            painter.end()
            return
        for defect in self.defects:
            px = x0 + side / 2 + float(defect.get("x", 0.0)) * side / 2
            py = y0 + side / 2 - float(defect.get("y", 0.0)) * side / 2
            selected = defect.get("id") == self.selected_id
            marked = defect.get("marked")
            color, shape = self._defect_style(defect)
            painter.setPen(QPen(QColor("#202020"), 1))
            painter.setBrush(QColor("#ffe13d") if selected else QColor("#15a85d") if marked else QColor(color))
            radius = 5 if selected else 3
            if shape == "Square":
                painter.drawRect(int(px - radius), int(py - radius), radius * 2, radius * 2)
            elif shape == "Diamond":
                painter.drawRect(int(px - radius), int(py - radius), radius * 2, radius * 2)
                painter.drawLine(int(px - radius), int(py), int(px), int(py - radius))
                painter.drawLine(int(px), int(py - radius), int(px + radius), int(py))
            else:
                painter.drawEllipse(int(px - radius), int(py - radius), radius * 2, radius * 2)
            if self.show_counts:
                painter.drawText(int(px + 4), int(py - 4), str(defect.get("id", "")))
            if defect.get("id") in self.selected_ids:
                painter.setPen(QPen(QColor("#111111"), 1))
                painter.drawLine(int(px - 6), int(py), int(px + 6), int(py))
                painter.drawLine(int(px), int(py - 6), int(px), int(py + 6))
        if self.drag_start and self.drag_end:
            x1, y1 = self.drag_start
            x2, y2 = self.drag_end
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor("#202020"), 1))
            painter.drawRect(int(min(x1, x2)), int(min(y1, y2)), int(abs(x2 - x1)), int(abs(y2 - y1)))
        painter.end()

    def _defect_style(self, defect):
        values = {
            "Marked": bool(defect.get("marked")),
            "Reviewed": bool(defect.get("reviewed")),
            "Repeater": bool(defect.get("repeater")),
            "Clustered": bool(defect.get("cluster_id")),
            "Dark": defect.get("polarity") == "Dark",
        }
        for rule in self.display_rules:
            if rule.get("enabled") and values.get(rule.get("rule")) == bool(rule.get("state", True)):
                return rule.get("color", "#d62d2d"), rule.get("shape", "Circle")
        return "#d62d2d", "Circle"

    def mousePressEvent(self, event):
        if not self.defects:
            return
        point = event.position() if hasattr(event, "position") else event.pos()
        self.drag_start = (point.x(), point.y())
        self.drag_end = self.drag_start
        x0, y0, side = self._geometry()
        nearest = min(
            self.defects,
            key=lambda defect: (
                (x0 + side / 2 + defect.get("x", 0.0) * side / 2 - point.x()) ** 2
                + (y0 + side / 2 - defect.get("y", 0.0) * side / 2 - point.y()) ** 2
            ),
        )
        self.select_defect(nearest.get("id"))
        if self.on_selected:
            self.on_selected(nearest.get("id"))

    def mouseMoveEvent(self, event):
        if self.drag_start is None:
            return
        point = event.position() if hasattr(event, "position") else event.pos()
        self.drag_end = (point.x(), point.y())
        self.update()

    def mouseReleaseEvent(self, event):
        if self.drag_start is None:
            return
        point = event.position() if hasattr(event, "position") else event.pos()
        self.drag_end = (point.x(), point.y())
        x1, y1 = self.drag_start
        x2, y2 = self.drag_end
        if abs(x2 - x1) > 5 or abs(y2 - y1) > 5:
            x0, y0, side = self._geometry()
            left, right = sorted((x1, x2))
            top, bottom = sorted((y1, y2))
            identifiers = []
            for defect in self.defects:
                px = x0 + side / 2 + float(defect.get("x", 0.0)) * side / 2
                py = y0 + side / 2 - float(defect.get("y", 0.0)) * side / 2
                if left <= px <= right and top <= py <= bottom:
                    identifiers.append(defect.get("id"))
            if self.on_area_selected:
                self.on_area_selected(identifiers)
        self.drag_start = None
        self.drag_end = None
        self.update()

    def mouseDoubleClickEvent(self, event):
        self.mousePressEvent(event)
        if self.on_select_toggle and self.selected_id is not None:
            self.on_select_toggle(self.selected_id)


class DefectImageWidget(QWidget):
    PALETTES = [
        ("#273f49", "#8bd0cf", "#f6ca4b"),
        ("#342c49", "#be9be5", "#ff7d5f"),
        ("#384239", "#b6d782", "#ffffff"),
        ("#3f3430", "#d8a66d", "#5fd5ff"),
    ]

    def __init__(self, title="Image", parent=None):
        super().__init__(parent)
        self.title = title
        self.defect = None
        self.zoom = 1.0
        self.setMinimumSize(150, 130)

    def set_defect(self, defect):
        self.defect = defect
        self.update()

    def set_zoom(self, zoom):
        self.zoom = max(1.0, float(zoom))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#101719"))
        if not self.defect:
            painter.setPen(QColor("#b8b8b8"))
            painter.drawText(self.rect(), Qt.AlignCenter, "No defect selected")
            painter.end()
            return
        palette = self.PALETTES[int(self.defect.get("image_kind", 0)) % len(self.PALETTES)]
        painter.fillRect(6, 23, self.width() - 12, self.height() - 29, QColor(palette[0]))
        painter.fillRect(self.width() // 2, 23, self.width() // 2 - 6, self.height() - 29, QColor(palette[1]))
        painter.setPen(QPen(QColor(palette[2]), 2))
        cx = self.width() // 2 + int(float(self.defect.get("x", 0.0)) * 25 * self.zoom)
        cy = self.height() // 2 - int(float(self.defect.get("y", 0.0)) * 20 * self.zoom)
        painter.drawLine(cx - 11, cy, cx + 11, cy)
        painter.drawLine(cx, cy - 11, cx, cy + 11)
        painter.setPen(QColor("#ffffff"))
        display_title = {
            "Reference Image": "Reference",
            "Patch Image": "Patch",
            "Difference Image": "Difference",
        }.get(self.title, self.title)
        painter.drawText(8, 16, f"{display_title} - D{self.defect.get('id')}")
        painter.end()


class DefectChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.counts = {}
        self.points = []
        self.cut_lines = []
        self.title = "Defects by Class Code"
        self.chart_type = "Bar"
        self.scale_mode = "Linear"
        self.show_grid = False
        self.show_legend = False
        self.group_size = 1
        self.zoom = 1.0
        self.setMinimumSize(260, 120)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)

    def set_counts(self, counts, title=None, chart_type="Bar"):
        self.counts = dict(counts)
        self.points = []
        self.chart_type = chart_type
        if title:
            self.title = title
        self.update()

    def set_points(self, points, title=None):
        self.points = list(points)
        self.counts = {}
        self.chart_type = "Scatter"
        if title:
            self.title = title
        self.update()

    def set_cut_lines(self, values):
        self.cut_lines = [float(value) for value in values]
        self.update()

    def set_plot_options(self, *, scale=None, grid=None, legend=None, group_size=None, zoom=None):
        if scale is not None:
            self.scale_mode = str(scale)
        if grid is not None:
            self.show_grid = bool(grid)
        if legend is not None:
            self.show_legend = bool(legend)
        if group_size is not None:
            self.group_size = max(1, min(5, int(group_size)))
        if zoom is not None:
            self.zoom = max(1.0, min(4.0, float(zoom)))
        self.update()

    def _context_menu(self, position):
        menu = QMenu(self)
        menu.addAction("Zoom In", lambda: self.set_plot_options(zoom=self.zoom * 1.25))
        menu.addAction("Zoom Out", lambda: self.set_plot_options(zoom=self.zoom / 1.25))
        menu.addAction("Reset Zoom", lambda: self.set_plot_options(zoom=1.0))
        menu.addSeparator()
        legend = menu.addAction("Show Legend")
        legend.setCheckable(True)
        legend.setChecked(self.show_legend)
        legend.triggered.connect(lambda checked: self.set_plot_options(legend=checked))
        grid = menu.addAction("Show Grid")
        grid.setCheckable(True)
        grid.setChecked(self.show_grid)
        grid.triggered.connect(lambda checked: self.set_plot_options(grid=checked))
        scale = menu.addMenu("Scale")
        for name in ("Linear", "Log", "Log X", "Log Y"):
            action = scale.addAction(name)
            action.setCheckable(True)
            action.setChecked(name == self.scale_mode)
            action.triggered.connect(lambda _checked=False, value=name: self.set_plot_options(scale=value))
        menu.exec(self.mapToGlobal(position))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#efefeb"))
        painter.setPen(QColor("#202020"))
        painter.drawText(10, 18, self.title)
        if not self.counts and not self.points:
            painter.drawText(self.rect(), Qt.AlignCenter, "No visible defects")
            painter.end()
            return
        if self.points:
            left, top, right, bottom = 32, 30, self.width() - 18, self.height() - 28
            width = max(1, right - left)
            height = max(1, bottom - top)
            xs = [float(point[0]) for point in self.points]
            ys = [float(point[1]) for point in self.points]
            if self.scale_mode in ("Log", "Log X"):
                xs = [math.log1p(max(0.0, value)) for value in xs]
            if self.scale_mode in ("Log", "Log Y"):
                ys = [math.log1p(max(0.0, value)) for value in ys]
            minimum_x, maximum_x = min(xs), max(xs)
            minimum_y, maximum_y = min(ys), max(ys)
            range_x = maximum_x - minimum_x or 1.0
            range_y = maximum_y - minimum_y or 1.0
            painter.setPen(QColor("#b8b8b2"))
            painter.drawLine(left, bottom, right, bottom)
            painter.drawLine(left, top, left, bottom)
            if self.show_grid:
                painter.setPen(QColor("#d0d0cb"))
                for step in range(1, 5):
                    x = left + int(width * step / 5)
                    y = bottom - int(height * step / 5)
                    painter.drawLine(x, top, x, bottom)
                    painter.drawLine(left, y, right, y)
            painter.setPen(QColor("#2d7487"))
            painter.setBrush(QColor("#2d7487"))
            for x_value, y_value in zip(xs, ys):
                x = left + int((x_value - minimum_x) * width / range_x)
                y = bottom - int((y_value - minimum_y) * height / range_y)
                painter.drawEllipse(x - 2, y - 2, 5, 5)
            painter.setPen(QPen(QColor("#c63f36"), 2))
            for value in self.cut_lines:
                transformed = math.log1p(max(0.0, value)) if self.scale_mode in ("Log", "Log X") else value
                x = left + int((transformed - minimum_x) * width / range_x)
                if left <= x <= right:
                    painter.drawLine(x, top, x, bottom)
            painter.setPen(QColor("#202020"))
            painter.drawText(left, self.height() - 8, f"{minimum_x:g}")
            painter.drawText(right - 45, self.height() - 8, f"{maximum_x:g}")
            painter.drawText(4, top + 5, f"{maximum_y:g}")
            painter.end()
            return
        items = sorted(
            self.counts.items(),
            key=(lambda item: (-item[1], str(item[0]))) if self.chart_type == "Pareto" else (lambda item: str(item[0])),
        )
        transformed = {
            code: math.log1p(count) if self.scale_mode in ("Log", "Log Y") else count
            for code, count in items
        }
        maximum = max(transformed.values()) or 1
        legend_width = 110 if self.show_legend else 0
        available_width = max(80, self.width() - 45 - legend_width)
        bar_width = max(18, int(available_width * self.zoom) // max(1, len(items)))
        baseline = self.height() - 52
        chart_height = max(28, self.height() - 86)
        if self.show_grid:
            painter.setPen(QColor("#c7c7c2"))
            for step in range(1, 5):
                y = baseline - int(chart_height * step / 4)
                painter.drawLine(22, y, 22 + available_width, y)
        for index, (code, count) in enumerate(items):
            height = int(chart_height * transformed[code] / maximum)
            x = 25 + index * bar_width
            y = baseline - height
            colors = ["#2d7487", "#a55b45", "#648447", "#8a6d9b"]
            color = colors[index % len(colors)] if self.chart_type in ("Stacked", "Side by Side") else "#2d7487"
            fill_width = max(4, min(bar_width - 3, (bar_width - 5) * self.group_size // 3))
            painter.fillRect(x, y, fill_width, height, QColor(color))
            painter.setPen(QColor("#202020"))
            painter.drawText(x, self.height() - 31, str(code))
            painter.drawText(x, max(32, y - 3), str(count))
        if self.show_legend:
            legend_x = self.width() - legend_width + 8
            painter.drawText(legend_x, 18, "Legend")
            for index, (code, _count) in enumerate(items[:6]):
                y = 36 + index * 16
                color = ["#2d7487", "#a55b45", "#648447", "#8a6d9b"][index % 4]
                painter.fillRect(legend_x, y - 9, 10, 10, QColor(color))
                painter.drawText(legend_x + 15, y, str(code)[:14])
        painter.end()


class DefectFilterDialog(QDialog):
    def __init__(self, result, state=None, parent=None):
        super().__init__(parent)
        self.review_result = result
        self.state = {**default_filter_state(), **(state or {})}
        self.result_filters = None
        self.setWindowTitle("Filter and Analysis - Filter Properties")
        self.resize(980, 560)
        self.setMinimumWidth(900)
        defects = result.get("defects", [])
        self.values = {
            "tests": sorted({item.get("test", "") for item in defects}),
            "class_codes": sorted({int(item.get("class_code", 0)) for item in defects}),
            "rough_bins": sorted({int(item.get("roughbin", 0)) for item in defects}),
            "rough_classes": sorted({
                str(item.get("ido_rough_code")) for item in defects if item.get("ido_rough_code")
            }),
            "rough_groups": sorted({
                str(item.get("ido_rough_group")) for item in defects if item.get("ido_rough_group")
            }),
            "venn_ids": sorted({int(item.get("venn_id", 0)) for item in defects}),
            "channels": sorted({int(item.get("channel", 0)) for item in defects}),
            "region_ids": sorted({str(item.get("region_id", "")) for item in defects if item.get("region_id")}),
            "threshold_regions": sorted({str(item.get("threshold_region", "")) for item in defects if item.get("threshold_region")}),
            "scale_groups": sorted({str(item.get("sizing_scale_group", "")) for item in defects if item.get("sizing_scale_group")}),
        }
        root = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._general_page(), "General")
        self.tabs.addTab(self._venn_page(), "Venn ID")
        self.tabs.addTab(self._sensitivity_page(), "Sensitivity")
        self.tabs.addTab(self._class_page(), "Class Code")
        self.tabs.addTab(self._channel_page(), "Channel")
        self.tabs.addTab(self._advanced_page(), "Advanced Filtering")
        root.addWidget(self.tabs, 1)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(self._finish)
        reset = QPushButton("Reset")
        reset.clicked.connect(self._reset)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(apply_button)
        buttons.addWidget(reset)
        buttons.addWidget(cancel)
        root.addLayout(buttons)

    def _choice(self, values, current):
        control = QComboBox()
        control.addItems(values)
        control.setCurrentText(str(current))
        return control

    def _check_grid(self, values, selected):
        host = QWidget()
        grid = QGridLayout(host)
        checks = {}
        active = set(selected or values)
        for index, value in enumerate(values):
            check = QCheckBox(str(value))
            check.setChecked(value in active)
            checks[value] = check
            grid.addWidget(check, index // 4, index % 4)
        grid.setRowStretch((len(values) + 3) // 4, 1)
        return host, checks

    def _general_page(self):
        page = QWidget()
        layout = QGridLayout(page)
        self.adder_mode = self._choice(["All", "Adders", "Non-Adders"], self.state["adder_mode"])
        self.cluster_mode = self._choice(["All", "Clustered", "Unclustered"], self.state["cluster_mode"])
        self.repeater_mode = self._choice(["All", "Repeaters", "Non-Repeaters"], self.state["repeater_mode"])
        self.bright = QCheckBox("Bright")
        self.dark = QCheckBox("Dark")
        selected_polarities = set(self.state.get("polarities") or ["Bright", "Dark"])
        self.bright.setChecked("Bright" in selected_polarities)
        self.dark.setChecked("Dark" in selected_polarities)
        polarity = QWidget()
        polarity_layout = QHBoxLayout(polarity)
        polarity_layout.setContentsMargins(0, 0, 0, 0)
        polarity_layout.addWidget(self.bright)
        polarity_layout.addWidget(self.dark)
        polarity_layout.addStretch(1)
        self.minimum_size = QDoubleSpinBox()
        self.minimum_size.setRange(0, 1000000)
        self.minimum_size.setDecimals(3)
        self.minimum_size.setValue(float(self.state["minimum_size_um"]))
        self.maximum_size = QDoubleSpinBox()
        self.maximum_size.setRange(0, 1000000)
        self.maximum_size.setDecimals(3)
        self.maximum_size.setValue(float(self.state["maximum_size_um"]))
        self.marked_only = QCheckBox("Marked defects only")
        self.marked_only.setChecked(bool(self.state["marked_only"]))
        self.unreviewed_only = QCheckBox("Unreviewed defects only")
        self.unreviewed_only.setChecked(bool(self.state["unreviewed_only"]))
        scale_host, self.scale_group_checks = self._check_grid(self.values["scale_groups"], self.state["scale_groups"])
        rows = (
            ("Adder", self.adder_mode), ("Clusters", self.cluster_mode),
            ("Repeaters", self.repeater_mode), ("Polarity", polarity),
            ("Minimum Size (um)", self.minimum_size), ("Maximum Size (um)", self.maximum_size),
            ("Sizing Scale Factor", scale_host),
        )
        for row, (label, control) in enumerate(rows):
            layout.addWidget(QLabel(label), row, 0)
            layout.addWidget(control, row, 1)
        layout.addWidget(self.marked_only, len(rows), 0, 1, 2)
        layout.addWidget(self.unreviewed_only, len(rows) + 1, 0, 1, 2)
        layout.setColumnStretch(1, 1)
        layout.setRowStretch(len(rows) + 2, 1)
        return page

    def _venn_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        duplicate_row = QHBoxLayout()
        duplicate_row.addWidget(QLabel("MultiTest Duplicates"))
        self.duplicate_mode = self._choice(
            ["All", "Duplicates", "Non-Duplicates"],
            self.state.get("duplicate_mode", "Non-Duplicates"),
        )
        duplicate_row.addWidget(self.duplicate_mode)
        duplicate_row.addStretch(1)
        layout.addLayout(duplicate_row)
        layout.addWidget(QLabel("Venn IDs"))
        venn_grid, self.venn_checks = self._check_grid(
            self.values["venn_ids"], self.state["venn_ids"]
        )
        layout.addWidget(venn_grid, 1)
        return page

    def _sensitivity_page(self):
        page = QWidget()
        layout = QGridLayout(page)
        test_host, self.test_checks = self._check_grid(self.values["tests"], self.state["tests"])
        region_host, self.region_checks = self._check_grid(self.values["region_ids"], self.state["region_ids"])
        threshold_host, self.threshold_checks = self._check_grid(self.values["threshold_regions"], self.state["threshold_regions"])
        self.minimum_signal = QDoubleSpinBox()
        self.minimum_signal.setRange(0, 1000000)
        self.minimum_signal.setValue(float(self.state["minimum_signal"]))
        self.maximum_signal = QDoubleSpinBox()
        self.maximum_signal.setRange(0, 1000000)
        self.maximum_signal.setValue(float(self.state["maximum_signal"]))
        layout.addWidget(QLabel("Tests"), 0, 0)
        layout.addWidget(test_host, 0, 1)
        layout.addWidget(QLabel("Regions"), 1, 0)
        layout.addWidget(region_host, 1, 1)
        layout.addWidget(QLabel("Threshold Regions"), 2, 0)
        layout.addWidget(threshold_host, 2, 1)
        layout.addWidget(QLabel("Signal Range"), 3, 0)
        range_host = QWidget()
        range_layout = QHBoxLayout(range_host)
        range_layout.setContentsMargins(0, 0, 0, 0)
        range_layout.addWidget(self.minimum_signal)
        range_layout.addWidget(QLabel("to"))
        range_layout.addWidget(self.maximum_signal)
        layout.addWidget(range_host, 3, 1)
        layout.setColumnStretch(1, 1)
        return page

    def _class_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Class Codes"))
        class_host, self.class_checks = self._check_grid(self.values["class_codes"], self.state["class_codes"])
        layout.addWidget(class_host, 1)
        layout.addWidget(QLabel("Rough Bins"))
        rough_host, self.rough_checks = self._check_grid(self.values["rough_bins"], self.state["rough_bins"])
        layout.addWidget(rough_host, 1)
        layout.addWidget(QLabel("iDO Rough Class"))
        rough_class_host, self.rough_class_checks = self._check_grid(
            self.values["rough_classes"], self.state["rough_classes"]
        )
        layout.addWidget(rough_class_host, 1)
        layout.addWidget(QLabel("iDO Rough Group"))
        rough_group_host, self.rough_group_checks = self._check_grid(
            self.values["rough_groups"], self.state["rough_groups"]
        )
        layout.addWidget(rough_group_host, 1)
        return page

    def _channel_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Select channels used to display matching and unique defects."))
        host, self.channel_checks = self._check_grid(self.values["channels"], self.state["channels"])
        layout.addWidget(host, 1)
        return page

    def _advanced_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        self.advanced_tabs = QTabWidget()
        quick = QWidget()
        quick_layout = QVBoxLayout(quick)
        quick_layout.addWidget(QLabel("Quick Filter uses the General, Sensitivity, Class Code, and Channel tabs."))
        quick_layout.addStretch(1)
        rules = QWidget()
        rule_layout = QGridLayout(rules)
        self.rule_element = self._choice(["Defect Size", "Intensity", "Class Code", "Roughbin", "Channel", "Test ID", "Region ID"], "Defect Size")
        self.rule_operator = self._choice(["=", "!=", ">", ">=", "<", "<="], ">")
        self.rule_value = QLineEdit("0")
        self.advanced_expression = QLineEdit(str(self.state.get("advanced_expression", "")))
        build = QPushButton("Build Expression")
        build.clicked.connect(lambda: self.advanced_expression.setText(f"{self.rule_element.currentText()} {self.rule_operator.currentText()} {self.rule_value.text().strip()}"))
        rule_layout.addWidget(QLabel("Selected Element"), 0, 0)
        rule_layout.addWidget(self.rule_element, 0, 1)
        rule_layout.addWidget(self.rule_operator, 0, 2)
        rule_layout.addWidget(self.rule_value, 0, 3)
        rule_layout.addWidget(build, 0, 4)
        rule_layout.addWidget(QLabel("Expression Definition"), 1, 0)
        rule_layout.addWidget(self.advanced_expression, 1, 1, 1, 4)
        rule_layout.setRowStretch(2, 1)
        self.advanced_tabs.addTab(quick, "Quick Filter")
        self.advanced_tabs.addTab(rules, "Rule Editor")
        layout.addWidget(self.advanced_tabs)
        return page

    @staticmethod
    def _selected_values(checks):
        selected = [value for value, check in checks.items() if check.isChecked()]
        return [] if len(selected) == len(checks) else selected

    def _finish(self):
        if self.minimum_signal.value() > self.maximum_signal.value() or self.minimum_size.value() > self.maximum_size.value():
            QMessageBox.warning(self, "Filter and Analysis", "Minimum values must not exceed maximum values.")
            return
        polarities = [name for name, check in (("Bright", self.bright), ("Dark", self.dark)) if check.isChecked()]
        if not polarities:
            QMessageBox.warning(self, "Filter and Analysis", "Select Bright, Dark, or both polarities.")
            return
        self.result_filters = {
            **self.state,
            "tests": self._selected_values(self.test_checks),
            "class_codes": self._selected_values(self.class_checks),
            "rough_bins": self._selected_values(self.rough_checks),
            "rough_classes": self._selected_values(self.rough_class_checks),
            "rough_groups": self._selected_values(self.rough_group_checks),
            "venn_ids": self._selected_values(self.venn_checks),
            "duplicate_mode": self.duplicate_mode.currentText(),
            "channels": self._selected_values(self.channel_checks),
            "region_ids": self._selected_values(self.region_checks),
            "threshold_regions": self._selected_values(self.threshold_checks),
            "scale_groups": self._selected_values(self.scale_group_checks),
            "polarities": [] if len(polarities) == 2 else polarities,
            "adder_mode": self.adder_mode.currentText(),
            "cluster_mode": self.cluster_mode.currentText(),
            "repeater_mode": self.repeater_mode.currentText(),
            "minimum_signal": self.minimum_signal.value(),
            "maximum_signal": self.maximum_signal.value(),
            "minimum_size_um": self.minimum_size.value(),
            "maximum_size_um": self.maximum_size.value(),
            "advanced_expression": self.advanced_expression.text().strip(),
            "marked_only": self.marked_only.isChecked(),
            "unreviewed_only": self.unreviewed_only.isChecked(),
        }
        self.accept()

    def _reset(self):
        for checks in (
            self.test_checks, self.class_checks, self.rough_checks,
            self.rough_class_checks, self.rough_group_checks, self.venn_checks,
            self.channel_checks, self.region_checks, self.threshold_checks,
            self.scale_group_checks,
        ):
            for check in checks.values():
                check.setChecked(True)
        self.adder_mode.setCurrentText("All")
        self.cluster_mode.setCurrentText("All")
        self.repeater_mode.setCurrentText("All")
        self.duplicate_mode.setCurrentText("Non-Duplicates")
        self.bright.setChecked(True)
        self.dark.setChecked(True)
        self.minimum_signal.setValue(0)
        self.maximum_signal.setValue(1000000)
        self.minimum_size.setValue(0)
        self.maximum_size.setValue(1000000)
        self.advanced_expression.clear()
        self.marked_only.setChecked(False)
        self.unreviewed_only.setChecked(False)


class LotResultColumnsDialog(QDialog):
    def __init__(self, selected, parent=None):
        super().__init__(parent)
        self.result_columns = None
        self.checks = {}
        self.setWindowTitle("Configure Lot Parameters")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Select the lot parameters to display."))
        selected = set(selected)
        for key, label in LOT_RESULT_COLUMNS:
            check = QCheckBox(label)
            check.setChecked(key in selected)
            self.checks[key] = check
            layout.addWidget(check)
        buttons = QHBoxLayout()
        reset = QPushButton("Reset Columns")
        reset.clicked.connect(lambda: [check.setChecked(True) for check in self.checks.values()])
        buttons.addWidget(reset)
        buttons.addStretch(1)
        ok = QPushButton("OK")
        ok.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)

    def _finish(self):
        selected = [key for key, _label in LOT_RESULT_COLUMNS if self.checks[key].isChecked()]
        if not selected:
            QMessageBox.warning(self, "Configure Lot Parameters", "Select at least one parameter.")
            return
        self.result_columns = selected
        self.accept()


class KlarfMatchDialog(QDialog):
    def __init__(self, recipes, results, parent=None):
        super().__init__(parent)
        self.matches = []
        self.selected_match = None
        self.setWindowTitle("Select Matching Recipe or Lot Results")
        self.resize(620, 390)
        root = QVBoxLayout(self)
        root.addWidget(QLabel("Select a recipe or lot result whose wafer layout matches the imported KLARF."))
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Type", "Name", "Device", "Process Step", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        for kind, items in (("Recipe", recipes), ("Lot Result", results)):
            for item in items:
                self.matches.append(item)
                row = self.table.rowCount()
                self.table.insertRow(row)
                name = item.get("inspection") if kind == "Recipe" else f"{item.get('lot_id', '')} / {item.get('wafer_id', '')}"
                values = [kind, name, item.get("device", ""), item.get("step", ""), item.get("status", "")]
                for column, value in enumerate(values):
                    self.table.setItem(row, column, QTableWidgetItem(str(value)))
        if self.matches:
            self.table.selectRow(0)
        root.addWidget(self.table, 1)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        select = QPushButton("Select")
        select.clicked.connect(self._select)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(select)
        buttons.addWidget(cancel)
        root.addLayout(buttons)

    def _select(self):
        row = self.table.currentRow()
        if 0 <= row < len(self.matches):
            self.selected_match = self.matches[row]
            self.accept()


class SelectLotResultsDialog(QDialog):
    def __init__(self, store, current_recipe=None, parent=None):
        super().__init__(parent)
        self.store = store
        self.current_recipe = current_recipe
        self.results = []
        self.selected_result = None
        self.columns = [key for key, _label in LOT_RESULT_COLUMNS[:7]]
        self.setWindowTitle("Select Lot Results")
        self.resize(1020, 620)
        root = QVBoxLayout(self)
        tools = QHBoxLayout()
        tools.addWidget(QLabel("Source"))
        self.source = QComboBox()
        self.source.addItems(["Lot Results", "Recent Items", "Demo Data"])
        self.source.currentTextChanged.connect(self._refresh)
        tools.addWidget(self.source)
        self.search_button = QPushButton("Search")
        self.search_button.setCheckable(True)
        self.search_button.toggled.connect(self._search_toggled)
        tools.addWidget(self.search_button)
        folder = QPushButton("Folder...")
        folder.clicked.connect(self._choose_folder)
        tools.addWidget(folder)
        info = QPushButton("Info")
        info.clicked.connect(self._show_info)
        tools.addWidget(info)
        configure = QPushButton("Configure Columns...")
        configure.clicked.connect(self._configure_columns)
        tools.addWidget(configure)
        tools.addStretch(1)
        root.addLayout(tools)
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Find"))
        self.search = QLineEdit()
        self.search.setPlaceholderText("Lot, wafer, inspection, device, or process step")
        self.search.textChanged.connect(self._refresh)
        search_row.addWidget(self.search, 1)
        self.clear_search = QPushButton("Clear")
        self.clear_search.clicked.connect(self.search.clear)
        search_row.addWidget(self.clear_search)
        self.search_frame = QWidget()
        self.search_frame.setLayout(search_row)
        self.search_frame.setVisible(False)
        root.addWidget(self.search_frame)
        self.table = QTableWidget(0, len(self.columns))
        self._apply_headers()
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        self.table.cellDoubleClicked.connect(lambda _row, _column: self._open())
        root.addWidget(self.table, 1)
        self.details = QLabel()
        self.details.setWordWrap(True)
        self.details.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.details.setMinimumHeight(58)
        root.addWidget(self.details)
        buttons = QHBoxLayout()
        path_button = QPushButton("Open Path")
        path_button.clicked.connect(self._open_path)
        open_button = QPushButton("Open")
        open_button.clicked.connect(self._open)
        delete = QPushButton("Delete")
        delete.clicked.connect(self._delete)
        self.review_mode = QComboBox()
        self.review_mode.addItems(["Review Only", "Loaded Wafer", "Inspected Wafer"])
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(delete)
        buttons.addWidget(path_button)
        buttons.addStretch(1)
        buttons.addWidget(QLabel("Wafer Selection"))
        buttons.addWidget(self.review_mode)
        buttons.addWidget(open_button)
        buttons.addWidget(cancel)
        root.addLayout(buttons)
        self.table.currentCellChanged.connect(self._selection_changed)
        self._refresh()

    def _apply_headers(self):
        labels = dict(LOT_RESULT_COLUMNS)
        self.table.setColumnCount(len(self.columns))
        self.table.setHorizontalHeaderLabels([labels[key] for key in self.columns])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        if "inspection" in self.columns:
            self.table.horizontalHeader().setSectionResizeMode(self.columns.index("inspection"), QHeaderView.Stretch)

    def _column_value(self, result, key):
        if key == "recipe_match":
            return "Matched" if result_matches_recipe(result, self.current_recipe) else "Mismatch"
        if key == "completed":
            return result.get("completed") or result.get("created", "")
        if key == "status" and result.get("is_demo"):
            return f"{result.get('status', '')} (Demo)"
        return result.get(key, "")

    def _refresh(self, *_args):
        query = self.search.text().strip().lower()
        self.results = []
        for result in reversed(self.store.list_results()):
            if self.source.currentText() == "Recent Items" and not result.get("review_recent"):
                continue
            if self.source.currentText() == "Demo Data" and not result.get("is_demo"):
                continue
            haystack = " ".join(str(result.get(key, "")) for key in ("lot_id", "wafer_id", "inspection", "device", "step")).lower()
            if not query or query in haystack:
                self.results.append(result)
        self.table.setRowCount(0)
        for result in self.results:
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = [self._column_value(result, key) for key in self.columns]
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(str(value)))
        if self.results:
            self.table.selectRow(0)

    def _selection_changed(self, row, _column, _previous_row, _previous_column):
        if 0 <= row < len(self.results):
            result = self.results[row]
            self.details.setText(
                f"Device: {result.get('device', '')}    Step: {result.get('step', '')}    "
                f"Tests: {', '.join(result.get('selected_tests', []))}\n"
                f"Source: {result.get('source_format', 'Puma Lot Result')}    "
                f"Path: {result.get('path') or self.store.path.parent}"
            )

    def _search_toggled(self, checked):
        self.search_frame.setVisible(checked)
        if checked:
            self.search.setFocus()
        else:
            self.search.clear()

    def _configure_columns(self):
        dialog = LotResultColumnsDialog(self.columns, self)
        if _exec(dialog) == QDialog.Accepted and dialog.result_columns:
            self.columns = dialog.result_columns
            self._apply_headers()
            self._refresh()

    def _choose_folder(self):
        initial = str(self.store.get_preferences().get("review_quick_reference", self.store.path.parent))
        folder = QFileDialog.getExistingDirectory(self, "Browse for Folder", initial)
        if folder:
            self.store.update_preferences({"review_quick_reference": folder})
            self.details.setText(f"Quick reference folder: {folder}")

    def _selected(self):
        row = self.table.currentRow()
        return self.results[row] if 0 <= row < len(self.results) else None

    def _show_info(self):
        result = self._selected()
        if result is None:
            return
        QMessageBox.information(
            self,
            "Lot Information",
            f"Lot: {result.get('lot_id', '')}\nWafer: {result.get('wafer_id', '')}\n"
            f"Inspection: {result.get('inspection', '')}\nDevice: {result.get('device', '')}\n"
            f"Process Step: {result.get('step', '')}\nTests: {', '.join(result.get('selected_tests', []))}\n"
            f"Defect Count: {result.get('defect_count', 0)}\nStatus: {result.get('status', '')}",
        )

    def _open_path(self):
        result = self._selected()
        if result is None:
            return
        path = str(result.get("path") or self.store.path.parent)
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _context_menu(self, position):
        if self._selected() is None:
            return
        menu = QMenu(self)
        for label, mode in (
            ("Review Only", "Review Only"),
            ("Review Loaded Wafer", "Loaded Wafer"),
            ("Review Inspected Wafer", "Inspected Wafer"),
        ):
            action = menu.addAction(label)
            action.triggered.connect(lambda _checked=False, value=mode: self._open(value))
        menu.addSeparator()
        menu.addAction("Info", self._show_info)
        menu.addAction("Open Path", self._open_path)
        menu.addAction("Delete", self._delete)
        menu.addAction("Refresh", self._refresh)
        menu.exec(self.table.viewport().mapToGlobal(position)) if hasattr(menu, "exec") else menu.exec_(self.table.viewport().mapToGlobal(position))

    def _open(self, mode=None):
        result = self._selected()
        if result is None:
            return
        selected = deepcopy(result)
        selected["review_mode"] = mode or self.review_mode.currentText()
        selected["review_recent"] = True
        selected.setdefault("path", str(self.store.path.parent))
        self.selected_result = self.store.save_result(selected)
        self.accept()

    def _delete(self):
        result = self._selected()
        if result is not None:
            answer = QMessageBox.question(
                self,
                "Delete Lot Result",
                f"Delete lot result {result.get('lot_id', '')} / {result.get('wafer_id', '')}?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
            self.store.delete_result(result["id"])
            self._refresh()


class ResultsUtilityDialog(QDialog):
    def __init__(self, target, sources, visible_defects, parent=None):
        super().__init__(parent)
        self.target = deepcopy(target)
        self.sources = [item for item in sources if item.get("id") != target.get("id")]
        self.visible_defects = deepcopy(visible_defects)
        self.result_result = None
        self.new_result = None
        self.status_message = ""
        self.setWindowTitle("Results Utility")
        self.resize(620, 470)
        root = QVBoxLayout(self)
        form = QGridLayout()
        self.operation = QComboBox()
        self.operation.addItems(["Auto Label", "Merge Result", "Save Filtered Lot As"])
        self.operation.currentTextChanged.connect(self._mode_changed)
        self.source = QComboBox()
        for result in self.sources:
            self.source.addItem(
                f"{result.get('lot_id', '')} / {result.get('wafer_id', '')} / {result.get('inspection', '')}",
                result.get("id", ""),
            )
        self.source.currentIndexChanged.connect(self._source_changed)
        self.source_test = QComboBox()
        self.target_test = QComboBox()
        self.target_test.addItems(["All"] + list(target.get("selected_tests", [])))
        self.tolerance = QDoubleSpinBox()
        self.tolerance.setRange(0, 1)
        self.tolerance.setDecimals(6)
        self.tolerance.setSingleStep(0.0001)
        self.tolerance.setValue(0.001)
        self.new_lot = QLineEdit(f"{target.get('lot_id', 'Lot')}_Filtered")
        form.addWidget(QLabel("Operation"), 0, 0)
        form.addWidget(self.operation, 0, 1)
        form.addWidget(QLabel("Source Result"), 1, 0)
        form.addWidget(self.source, 1, 1)
        form.addWidget(QLabel("Source Test"), 2, 0)
        form.addWidget(self.source_test, 2, 1)
        form.addWidget(QLabel("Target Test"), 3, 0)
        form.addWidget(self.target_test, 3, 1)
        form.addWidget(QLabel("Location Tolerance"), 4, 0)
        form.addWidget(self.tolerance, 4, 1)
        form.addWidget(QLabel("New Lot Result"), 5, 0)
        form.addWidget(self.new_lot, 5, 1)
        root.addLayout(form)
        preferences = QFrame()
        pref = QVBoxLayout(preferences)
        pref.addWidget(QLabel("Auto Label Update Preferences"))
        self.preserve_classified = QCheckBox("Do not update target classified defects")
        self.preserve_codes = QLineEdit()
        self.preserve_codes.setPlaceholderText("Target class codes to preserve, comma separated")
        self.ignore_source_codes = QLineEdit()
        self.ignore_source_codes.setPlaceholderText("Source class codes to ignore, comma separated")
        pref.addWidget(self.preserve_classified)
        pref.addWidget(self.preserve_codes)
        pref.addWidget(self.ignore_source_codes)
        root.addWidget(preferences)
        self.preferences_frame = preferences
        self.validation = QLabel()
        self.validation.setStyleSheet("color: #a41515; font-weight: bold;")
        root.addWidget(self.validation)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(self._apply)
        close = QPushButton("Close")
        close.clicked.connect(self.reject)
        buttons.addWidget(apply_button)
        buttons.addWidget(close)
        root.addLayout(buttons)
        self._source_changed()
        self._mode_changed(self.operation.currentText())

    @staticmethod
    def _codes(text):
        return [int(token.strip()) for token in text.split(",") if token.strip()]

    def _selected_source(self):
        identifier = self.source.currentData()
        return next((item for item in self.sources if item.get("id") == identifier), None)

    def _source_changed(self, *_args):
        source = self._selected_source()
        self.source_test.clear()
        self.source_test.addItems(["All"] + list((source or {}).get("selected_tests", [])))

    def _mode_changed(self, mode):
        needs_source = mode != "Save Filtered Lot As"
        for widget in (self.source, self.source_test, self.target_test, self.tolerance):
            widget.setEnabled(needs_source)
        self.preferences_frame.setEnabled(mode == "Auto Label")
        self.new_lot.setEnabled(mode == "Save Filtered Lot As")
        self.validation.clear()

    def _apply(self):
        mode = self.operation.currentText()
        try:
            if mode == "Save Filtered Lot As":
                self.new_result = filtered_result_as(self.target, self.visible_defects, self.new_lot.text())
                self.status_message = f"Filtered lot saved as {self.new_result['lot_id']}"
                self.accept()
                return
            source = self._selected_source()
            if source is None:
                raise ValueError("Select a source result")
            if mode == "Auto Label":
                self.result_result, changed = auto_label_result(
                    self.target,
                    source,
                    tolerance=self.tolerance.value(),
                    source_test=self.source_test.currentText(),
                    target_test=self.target_test.currentText(),
                    preserve_classified=self.preserve_classified.isChecked(),
                    preserve_codes=self._codes(self.preserve_codes.text()),
                    ignore_source_codes=self._codes(self.ignore_source_codes.text()),
                )
                self.status_message = f"Auto Label updated {changed} matching defect classification(s)"
            else:
                self.result_result, added = merge_result(
                    self.target,
                    source,
                    tolerance=self.tolerance.value(),
                    source_test=self.source_test.currentText(),
                    target_test=self.target_test.currentText(),
                )
                self.status_message = f"Merge Result added {added} new defect(s)"
        except ValueError as exc:
            self.validation.setText(str(exc))
            return
        self.accept()


class CombineSensitivityResultsDialog(QDialog):
    def __init__(self, target, sources, parent=None):
        super().__init__(parent)
        self.base_target = deepcopy(target)
        self.sources = [
            item for item in sources
            if item.get("id") != target.get("id") and item.get("sensitivity_data")
        ]
        self.applied = []
        self.combined = deepcopy(target)
        self.result_result = None
        self.setWindowTitle("Combine Results for Sensitivity Tuner")
        self.resize(760, 520)
        root = QVBoxLayout(self)
        form = QGridLayout()
        self.source = QComboBox()
        for item in self.sources:
            self.source.addItem(f"{item.get('lot_id', '')} / {item.get('wafer_id', '')}", item.get("id"))
        self.source.currentIndexChanged.connect(self._source_changed)
        self.source_test = QComboBox()
        self.target_test = QComboBox()
        self.target_test.addItems(["All"] + list(target.get("sensitivity_data_tests") or target.get("selected_tests", [])))
        form.addWidget(QLabel("Source Lot / Wafer"), 0, 0)
        form.addWidget(self.source, 0, 1)
        form.addWidget(QLabel("Source Test"), 1, 0)
        form.addWidget(self.source_test, 1, 1)
        form.addWidget(QLabel("Target Lot / Wafer"), 2, 0)
        form.addWidget(QLabel(f"{target.get('lot_id', '')} / {target.get('wafer_id', '')}"), 2, 1)
        form.addWidget(QLabel("Target Test"), 3, 0)
        form.addWidget(self.target_test, 3, 1)
        root.addLayout(form)
        actions = QHBoxLayout()
        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(self._apply)
        remove = QPushButton("Remove Last Source")
        remove.clicked.connect(self._remove)
        actions.addWidget(apply_button)
        actions.addWidget(remove)
        actions.addStretch(1)
        root.addLayout(actions)
        self.summary = QTableWidget(0, 2)
        self.summary.setHorizontalHeaderLabels(["Defect Summary", "Count"])
        self.summary.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.summary.verticalHeader().setVisible(False)
        root.addWidget(self.summary, 1)
        save_row = QHBoxLayout()
        save_row.addWidget(QLabel("Combined Lot Result"))
        self.name = QLineEdit(f"{target.get('lot_id', 'Lot')}_Combined_ST")
        save_row.addWidget(self.name, 1)
        save = QPushButton("Save As")
        save.clicked.connect(self._save)
        close = QPushButton("Close")
        close.clicked.connect(self.reject)
        save_row.addWidget(save)
        save_row.addWidget(close)
        root.addLayout(save_row)
        self.message = QLabel()
        root.addWidget(self.message)
        self._source_changed()
        self._refresh_summary()

    def _selected_source(self):
        identifier = self.source.currentData()
        return next((item for item in self.sources if item.get("id") == identifier), None)

    def _source_changed(self, *_args):
        source = self._selected_source()
        self.source_test.clear()
        self.source_test.addItems(["All"] + list((source or {}).get("sensitivity_data_tests") or (source or {}).get("selected_tests", [])))

    def _rebuild(self):
        self.combined = deepcopy(self.base_target)
        for source, source_test, target_test in self.applied:
            self.combined = combine_sensitivity_results(
                self.combined, source, source_test=source_test, target_test=target_test,
            )
        self._refresh_summary()

    def _apply(self):
        source = self._selected_source()
        if source is None:
            self.message.setText("Select a source result with Sensitivity Tuner data.")
            return
        try:
            candidate = self.applied + [(deepcopy(source), self.source_test.currentText(), self.target_test.currentText())]
            previous = self.applied
            self.applied = candidate
            self._rebuild()
        except ValueError as exc:
            self.applied = previous
            self.message.setText(str(exc))
            return
        self.message.setText(f"Imported source {source.get('lot_id', '')}; add another source or Save As.")

    def _remove(self):
        if self.applied:
            self.applied.pop()
            self._rebuild()

    def _refresh_summary(self):
        summary = self.combined.get("sensitivity_summary") or {
            "all": len(self.combined.get("defects", [])),
            "original": len(self.combined.get("defects", [])),
            "imported_source": 0,
        }
        self.summary.setRowCount(0)
        for label, key in (("All", "all"), ("Original", "original"), ("Imported Source", "imported_source")):
            row = self.summary.rowCount()
            self.summary.insertRow(row)
            self.summary.setItem(row, 0, QTableWidgetItem(label))
            self.summary.setItem(row, 1, QTableWidgetItem(str(summary.get(key, 0))))

    def _save(self):
        name = self.name.text().strip()
        if not self.applied:
            self.message.setText("Apply at least one source result before saving.")
            return
        if not name or name == self.base_target.get("lot_id"):
            self.message.setText("Enter a new combined Lot Result name.")
            return
        self.result_result = deepcopy(self.combined)
        self.result_result.pop("id", None)
        self.result_result["lot_id"] = name
        self.result_result["status"] = "Complete"
        self.accept()


class ClassifyDefectsDialog(QDialog):
    def __init__(self, count, parent=None):
        super().__init__(parent)
        self.class_code = None
        self.setWindowTitle("Classify Defects")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Assign a manual class code to {count} selected defect(s)."))
        row = QHBoxLayout()
        row.addWidget(QLabel("Class Code"))
        self.code = QSpinBox()
        self.code.setRange(0, 9999)
        row.addWidget(self.code)
        layout.addLayout(row)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        ok = QPushButton("Apply")
        ok.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)

    def _finish(self):
        self.class_code = self.code.value()
        self.accept()


class ReviewImageGrabDialog(QDialog):
    def __init__(self, tests, state=None, parent=None):
        super().__init__(parent)
        state = deepcopy(state or {})
        self.result_settings = None
        self.setWindowTitle("Image Grab")
        self.resize(540, 500)
        root = QVBoxLayout(self)
        root.addWidget(QLabel("Image Optics"))
        self.optics = QComboBox()
        self.optics.addItems(["Use Review Optics", "Use Inspection Test", "Simulated Test Run"])
        self.optics.setCurrentText(state.get("image_optics", "Use Review Optics"))
        self.optics.currentTextChanged.connect(self._mode_changed)
        root.addWidget(self.optics)
        test_row = QHBoxLayout()
        test_row.addWidget(QLabel("Inspection Test"))
        self.test = QComboBox()
        self.test.addItems(list(tests) or ["Test 1"])
        self.test.setCurrentText(state.get("test", self.test.currentText()))
        test_row.addWidget(self.test, 1)
        root.addLayout(test_row)

        root.addWidget(QLabel("Image Acquisition"))
        acquisition = QGridLayout()
        self.image_size_mode = QRadioButton("Image Size")
        self.full_frame_mode = QRadioButton("Full Frame Images")
        self.image_size_mode.setChecked(state.get("acquisition", "Image Size") == "Image Size")
        self.full_frame_mode.setChecked(not self.image_size_mode.isChecked())
        self.image_size = QComboBox()
        self.image_size.addItems(["128 x 128", "256 x 256", "512 x 512", "1024 x 1024"])
        self.image_size.setCurrentText(state.get("image_size", "256 x 256"))
        acquisition.addWidget(self.image_size_mode, 0, 0)
        acquisition.addWidget(self.image_size, 0, 1)
        acquisition.addWidget(self.full_frame_mode, 1, 0)
        self.full_frame_elements = {}
        element_row = QHBoxLayout()
        for name in ("Raw Image", "Reference Image", "Difference Image"):
            check = QCheckBox(name)
            check.setChecked(name in state.get("full_frame_elements", ["Raw Image", "Reference Image"]))
            self.full_frame_elements[name] = check
            element_row.addWidget(check)
        acquisition.addLayout(element_row, 1, 1)
        root.addLayout(acquisition)

        root.addWidget(QLabel("Image Handling"))
        self.clear_marks = QCheckBox("Clear Marks After Grab")
        self.allow_transfer = QCheckBox("Allow Images To Be Transferred To Database")
        self.ministrip = QCheckBox("Perform MiniStrip")
        self.clear_marks.setChecked(state.get("clear_marks", True))
        self.allow_transfer.setChecked(state.get("allow_transfer", True))
        self.ministrip.setChecked(state.get("ministrip", True))
        root.addWidget(self.clear_marks)
        root.addWidget(self.allow_transfer)
        root.addWidget(self.ministrip)
        references = QHBoxLayout()
        references.addWidget(QLabel("Number of Reference Die"))
        references.addWidget(QLabel("Left"))
        self.reference_left = QSpinBox()
        self.reference_left.setRange(0, 10)
        self.reference_left.setValue(int(state.get("reference_left", 1)))
        references.addWidget(self.reference_left)
        references.addWidget(QLabel("Right"))
        self.reference_right = QSpinBox()
        self.reference_right.setRange(0, 10)
        self.reference_right.setValue(int(state.get("reference_right", 1)))
        references.addWidget(self.reference_right)
        references.addStretch(1)
        root.addLayout(references)
        root.addStretch(1)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        ok = QPushButton("OK")
        ok.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        root.addLayout(buttons)
        self._mode_changed(self.optics.currentText())

    def _mode_changed(self, mode):
        self.test.setEnabled(mode != "Use Review Optics")
        self.full_frame_mode.setEnabled(mode == "Use Review Optics")
        if mode != "Use Review Optics" and self.full_frame_mode.isChecked():
            self.image_size_mode.setChecked(True)

    def _finish(self):
        self.result_settings = {
            "image_optics": self.optics.currentText(),
            "test": self.test.currentText(),
            "acquisition": "Full Frame Images" if self.full_frame_mode.isChecked() else "Image Size",
            "image_size": self.image_size.currentText(),
            "full_frame_elements": [name for name, check in self.full_frame_elements.items() if check.isChecked()],
            "clear_marks": self.clear_marks.isChecked(),
            "allow_transfer": self.allow_transfer.isChecked(),
            "ministrip": self.ministrip.isChecked(),
            "reference_left": self.reference_left.value(),
            "reference_right": self.reference_right.value(),
        }
        self.accept()


class ReviewOffsetDialog(QDialog):
    def __init__(self, result, *, die_origin=False, parent=None):
        super().__init__(parent)
        self.review_result = result
        self.die_origin = die_origin
        self.result_result = None
        self.setWindowTitle("Adjust Die Origin Offset" if die_origin else "Adjust Defect Location")
        root = QVBoxLayout(self)
        root.addWidget(QLabel(
            "Position the simulated crosshair on the actual die origin and mark the location."
            if die_origin else
            "Position the simulated crosshair on the defect center and mark the location."
        ))
        offsets = QGridLayout()
        self.x_offset = QDoubleSpinBox()
        self.y_offset = QDoubleSpinBox()
        for control in (self.x_offset, self.y_offset):
            control.setRange(-1000000.0, 1000000.0)
            control.setDecimals(3)
            control.setSuffix(" um")
        offsets.addWidget(QLabel("X Offset"), 0, 0)
        offsets.addWidget(self.x_offset, 0, 1)
        offsets.addWidget(QLabel("Y Offset"), 1, 0)
        offsets.addWidget(self.y_offset, 1, 1)
        root.addLayout(offsets)
        self.marked = QLabel("Location not marked")
        root.addWidget(self.marked)
        buttons = QHBoxLayout()
        mark = QPushButton("Mark")
        mark.clicked.connect(lambda: self.marked.setText("Location marked; offset vector is ready."))
        finish = QPushButton("Finish")
        finish.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(mark)
        buttons.addStretch(1)
        buttons.addWidget(finish)
        buttons.addWidget(cancel)
        root.addLayout(buttons)

    def _finish(self):
        self.result_result = apply_review_offset(
            self.review_result,
            self.x_offset.value(),
            self.y_offset.value(),
            die_origin=self.die_origin,
        )
        self.accept()


class OpticsSelectorDialog(QDialog):
    def __init__(self, result, recipe=None, state=None, parent=None):
        super().__init__(parent)
        self.review_result = result
        self.recipe = recipe
        self.state = deepcopy(state or {})
        self.result_state = None
        self.setWindowTitle("Optics Selector")
        self.resize(980, 680)
        root = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._sites_page(), "Mark Sites")
        self.tabs.addTab(self._optics_page(), "Select Optics")
        self.tabs.addTab(self._analysis_page(), "Grab and Analyze")
        root.addWidget(self.tabs, 1)
        footer = QHBoxLayout()
        footer.addStretch(1)
        finish = QPushButton("Finish")
        finish.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        footer.addWidget(finish)
        footer.addWidget(cancel)
        root.addLayout(footer)
        self._restore()

    def _sites_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Mark defects and special-interest locations for optics comparison."))
        self.site_table = QTableWidget(0, 5)
        self.site_table.setHorizontalHeaderLabels(["Marked", "Defect ID", "Test", "Die X", "Die Y"])
        self.site_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.site_table.verticalHeader().setVisible(False)
        for defect in self.review_result.get("defects", []):
            row = self.site_table.rowCount()
            self.site_table.insertRow(row)
            marked = QTableWidgetItem()
            marked.setFlags(marked.flags() | Qt.ItemIsUserCheckable)
            marked.setCheckState(Qt.Checked if defect.get("marked") else Qt.Unchecked)
            self.site_table.setItem(row, 0, marked)
            for column, key in enumerate(("id", "test", "die_x", "die_y"), 1):
                self.site_table.setItem(row, column, QTableWidgetItem(str(defect.get(key, ""))))
        layout.addWidget(self.site_table, 1)
        location_row = QHBoxLayout()
        self.location_x = QDoubleSpinBox()
        self.location_y = QDoubleSpinBox()
        for control in (self.location_x, self.location_y):
            control.setRange(-1000000, 1000000)
            control.setSuffix(" um")
        location_row.addWidget(QLabel("Location X"))
        location_row.addWidget(self.location_x)
        location_row.addWidget(QLabel("Y"))
        location_row.addWidget(self.location_y)
        add_location = QPushButton("Mark Location")
        add_location.clicked.connect(self._mark_location)
        location_row.addWidget(add_location)
        self.location_count = QLabel("0 locations")
        location_row.addWidget(self.location_count)
        location_row.addStretch(1)
        layout.addLayout(location_row)
        return page

    def _optics_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        form = QGridLayout()
        self.base_test = QComboBox()
        self.base_test.addItems(self.review_result.get("selected_tests", []) or ["Test 1"])
        self.pixel_size = QComboBox()
        self.pixel_size.addItems(["SL815", "SL610", "SL425", "SL280"])
        self.illumination = QComboBox()
        self.illumination.addItems(["Oblique", "Normal"])
        self.use_filters = QComboBox()
        self.use_filters.addItems(["Yes", "No"])
        self.iris = QComboBox()
        self.iris.addItems(["Open", "Large", "Medium", "Small"])
        self.incident = QComboBox()
        self.incident.addItems(["P-POL", "S-POL", "Unpolarized"])
        self.analyzer = QComboBox()
        self.analyzer.addItems(["None", "S-POL", "P-POL", "Variable Analyzer"])
        controls = [
            ("Base Test", self.base_test), ("Pixel Size", self.pixel_size),
            ("Illumination", self.illumination), ("Use Fourier Filters", self.use_filters),
            ("Iris", self.iris), ("Incident", self.incident), ("Analyzer", self.analyzer),
        ]
        for row, (label, control) in enumerate(controls):
            form.addWidget(QLabel(label), row, 0)
            form.addWidget(control, row, 1)
        self.analyzer_steps = QSpinBox()
        self.analyzer_steps.setRange(1, 32)
        self.analyzer_steps.setValue(4)
        form.addWidget(QLabel("Variable Analyzer Steps"), 7, 0)
        form.addWidget(self.analyzer_steps, 7, 1)
        self.focus_offset = QDoubleSpinBox()
        self.focus_offset.setRange(-500, 500)
        self.focus_offset.setDecimals(3)
        self.focus_offset.setSuffix(" um")
        form.addWidget(QLabel("Focus Offset"), 8, 0)
        form.addWidget(self.focus_offset, 8, 1)
        self.patch_size = QComboBox()
        self.patch_size.addItems(["128 x 128", "256 x 256", "512 x 512"])
        form.addWidget(QLabel("Patch Image Size"), 9, 0)
        form.addWidget(self.patch_size, 9, 1)
        self.light_training = QComboBox()
        self.light_training.addItems(["Use Existing Light", "Train Each Optics Mode"])
        form.addWidget(QLabel("Light Training"), 10, 0)
        form.addWidget(self.light_training, 10, 1)
        self.generate_algo = QCheckBox("Generate algorithm data")
        self.generate_algo.setChecked(True)
        self.regrab = QCheckBox("Regrab Images")
        form.addWidget(self.generate_algo, 11, 0, 1, 2)
        form.addWidget(self.regrab, 12, 0, 1, 2)
        layout.addLayout(form)
        add = QPushButton("Add Optics Mode")
        add.clicked.connect(self._add_mode)
        layout.addWidget(add, 0, Qt.AlignLeft)
        self.mode_table = QTableWidget(0, 8)
        self.mode_table.setHorizontalHeaderLabels(
            ["Base Test", "Pixel Size", "Illumination", "Filters", "Iris", "Incident", "Analyzer", "Focus"]
        )
        self.mode_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.mode_table.verticalHeader().setVisible(False)
        layout.addWidget(self.mode_table, 1)
        return page

    def _analysis_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        controls = QHBoxLayout()
        grab = QPushButton("Grab and Analyze")
        grab.clicked.connect(self._analyze)
        analyze = QPushButton("Analyze Existing Images")
        analyze.clicked.connect(self._analyze)
        export = QPushButton("Export Scores...")
        export.clicked.connect(self._export_scores)
        insert = QPushButton("Add Selected Modes to Recipe")
        insert.clicked.connect(self._add_to_recipe)
        controls.addWidget(grab)
        controls.addWidget(analyze)
        controls.addWidget(export)
        controls.addWidget(insert)
        controls.addStretch(1)
        layout.addLayout(controls)
        view = QHBoxLayout()
        self.image_mode = QComboBox()
        self.image_mode.addItems(["Test", "Reference", "Difference", "Blink Test/Ref", "Blink Test/Diff"])
        self.reference_type = QComboBox()
        self.reference_type.addItems(["First", "Second", "Highest", "Lowest"])
        self.channel = QComboBox()
        self.channel.addItems(["Channel 1", "Channel 2", "Channel 3", "Best Channel"])
        self.mapping = QComboBox()
        self.mapping.addItems(["Color", "Grayscale"])
        for label, control in (("Image", self.image_mode), ("Reference", self.reference_type), ("Channel", self.channel), ("Mapping", self.mapping)):
            view.addWidget(QLabel(label))
            view.addWidget(control)
        view.addStretch(1)
        layout.addLayout(view)
        self.score_table = QTableWidget(0, 7)
        self.score_table.setHorizontalHeaderLabels(
            ["Select", "Optics Mode", "Sites", "Signal", "Noise", "Signal/Noise", "Algo Metric"]
        )
        self.score_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.score_table.verticalHeader().setVisible(False)
        layout.addWidget(self.score_table, 1)
        self.analysis_status = QLabel("Select sites and optics modes, then click Grab and Analyze.")
        layout.addWidget(self.analysis_status)
        return page

    def _restore(self):
        self.locations = deepcopy(self.state.get("locations") or [])
        self.location_count.setText(f"{len(self.locations)} locations")
        self.modes = deepcopy(self.state.get("modes") or [])
        self.scores = deepcopy(self.state.get("scores") or [])
        self._populate_modes()
        self._populate_scores()

    def _marked_site_ids(self):
        return [
            int(self.site_table.item(row, 1).text())
            for row in range(self.site_table.rowCount())
            if self.site_table.item(row, 0).checkState() == Qt.Checked
        ]

    def _mark_location(self):
        self.locations.append({"x": self.location_x.value(), "y": self.location_y.value()})
        self.location_count.setText(f"{len(self.locations)} locations")

    def _add_mode(self):
        mode = {
            "base_test": self.base_test.currentText(),
            "pixel_size": self.pixel_size.currentText(),
            "illumination": self.illumination.currentText(),
            "use_filters": self.use_filters.currentText(),
            "iris": self.iris.currentText(),
            "incident": self.incident.currentText(),
            "analyzer": self.analyzer.currentText(),
            "analyzer_steps": self.analyzer_steps.value(),
            "focus_offset": self.focus_offset.value(),
            "patch_size": self.patch_size.currentText(),
            "light_training": self.light_training.currentText(),
            "generate_algo_data": self.generate_algo.isChecked(),
        }
        self.modes.append(mode)
        self._populate_modes()

    def _populate_modes(self):
        self.mode_table.setRowCount(0)
        for mode in self.modes:
            row = self.mode_table.rowCount()
            self.mode_table.insertRow(row)
            values = [
                mode.get("base_test"), mode.get("pixel_size"), mode.get("illumination"),
                mode.get("use_filters"), mode.get("iris"), mode.get("incident"),
                mode.get("analyzer"), mode.get("focus_offset"),
            ]
            for column, value in enumerate(values):
                self.mode_table.setItem(row, column, QTableWidgetItem(str(value)))

    def _analyze(self):
        if not self.modes:
            QMessageBox.warning(self, "Optics Selector", "Add at least one optics mode.")
            return
        site_ids = self._marked_site_ids()
        site_ids.extend(100000 + index for index in range(len(self.locations)))
        if not site_ids:
            QMessageBox.warning(self, "Optics Selector", "Mark at least one defect or location.")
            return
        self.scores = analyze_optics_modes(site_ids, self.modes)
        self._populate_scores()
        self.tabs.setCurrentIndex(2)
        self.analysis_status.setText(f"Analyzed {len(self.modes)} optics mode(s) at {len(site_ids)} site(s).")

    def _populate_scores(self):
        self.score_table.setRowCount(0)
        for score in self.scores:
            row = self.score_table.rowCount()
            self.score_table.insertRow(row)
            selected = QTableWidgetItem()
            selected.setFlags(selected.flags() | Qt.ItemIsUserCheckable)
            selected.setCheckState(Qt.Checked)
            self.score_table.setItem(row, 0, selected)
            name = f"{score.get('pixel_size')} / {score.get('illumination')} / {score.get('analyzer')}"
            values = [name, score.get("site_count"), score.get("signal"), score.get("noise"), score.get("signal_noise"), score.get("algo_metric")]
            for column, value in enumerate(values, 1):
                self.score_table.setItem(row, column, QTableWidgetItem(str(value)))

    def _selected_scores(self):
        return [
            self.scores[row]
            for row in range(min(self.score_table.rowCount(), len(self.scores)))
            if self.score_table.item(row, 0).checkState() == Qt.Checked
        ]

    def _export_scores(self):
        if not self.scores:
            return
        filename, _selected = QFileDialog.getSaveFileName(self, "Export Optics Selector Scores", "Optics Selector.csv", "CSV Files (*.csv)")
        if not filename:
            return
        lines = ["Base Test,Pixel Size,Illumination,Iris,Analyzer,Focus Offset,Signal,Noise,Signal Noise,Algo Metric"]
        for item in self.scores:
            lines.append(",".join(str(item.get(key, "")) for key in (
                "base_test", "pixel_size", "illumination", "iris", "analyzer", "focus_offset",
                "signal", "noise", "signal_noise", "algo_metric",
            )))
        Path(filename).write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.analysis_status.setText(f"Scores exported: {filename}")

    def _add_to_recipe(self):
        selected = self._selected_scores()
        if not selected or self.recipe is None:
            return
        tests = self.recipe.setdefault("tests", [])
        for index, mode in enumerate(selected, 1):
            tests.append({
                "name": f"Optics Selector {len(tests) + 1}",
                "mode": "Random",
                "inspection_optics": deepcopy(mode),
                "source": "Optics Selector",
            })
        self.state["inserted_test_count"] = self.state.get("inserted_test_count", 0) + len(selected)
        self.analysis_status.setText(f"Added {len(selected)} selected optics mode(s) as new recipe test(s).")

    def _finish(self):
        self.result_state = {
            "site_ids": self._marked_site_ids(),
            "locations": deepcopy(self.locations),
            "modes": deepcopy(self.modes),
            "scores": deepcopy(self.scores),
            "inserted_test_count": self.state.get("inserted_test_count", 0),
        }
        self.accept()


class RegionSelectionDialog(QDialog):
    def __init__(self, regions, selected=None, parent=None):
        super().__init__(parent)
        self.result_regions = None
        self.checks = {}
        self.setWindowTitle("Region Selection Option")
        layout = QVBoxLayout(self)
        self.automatic = QCheckBox("Automatically select current region only")
        self.automatic.setChecked(selected is None)
        layout.addWidget(self.automatic)
        selected = set(selected or regions)
        for region in regions:
            check = QCheckBox(region)
            check.setChecked(region in selected)
            check.setEnabled(not self.automatic.isChecked())
            self.checks[region] = check
            layout.addWidget(check)
        self.automatic.toggled.connect(
            lambda checked: [check.setEnabled(not checked) for check in self.checks.values()]
        )
        buttons = QHBoxLayout()
        select_all = QPushButton("Select All")
        select_all.clicked.connect(lambda: [check.setChecked(True) for check in self.checks.values()])
        select_none = QPushButton("Select None")
        select_none.clicked.connect(lambda: [check.setChecked(False) for check in self.checks.values()])
        ok = QPushButton("OK")
        ok.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(select_all)
        buttons.addWidget(select_none)
        buttons.addStretch(1)
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)

    def _finish(self):
        self.result_regions = None if self.automatic.isChecked() else [
            name for name, check in self.checks.items() if check.isChecked()
        ]
        if self.result_regions == []:
            QMessageBox.warning(self, "Region Selection", "Select at least one region.")
            return
        self.accept()


class STNEFPartitionsDialog(QDialog):
    def __init__(self, partitions=None, parent=None):
        super().__init__(parent)
        self.result_partitions = None
        self.setWindowTitle("Partitions")
        self.resize(480, 330)
        root = QVBoxLayout(self)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Name", "Classes"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        for partition in partitions or [
            {"name": "Defect", "classes": [1]},
            {"name": "Nuisance", "classes": [0]},
        ]:
            self._add_row(partition)
        root.addWidget(self.table)
        actions = QHBoxLayout()
        new_button = QPushButton("New")
        new_button.setIcon(self.style().standardIcon(QStyle.SP_FileIcon))
        new_button.clicked.connect(lambda: self._add_row({"name": "New Partition", "classes": []}))
        delete_button = QPushButton("Delete")
        delete_button.setIcon(self.style().standardIcon(QStyle.SP_TrashIcon))
        delete_button.clicked.connect(self._delete)
        actions.addWidget(new_button)
        actions.addWidget(delete_button)
        actions.addStretch(1)
        ok = QPushButton("OK")
        ok.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        actions.addWidget(ok)
        actions.addWidget(cancel)
        root.addLayout(actions)

    def _add_row(self, partition):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(str(partition.get("name", ""))))
        self.table.setItem(
            row, 1, QTableWidgetItem(", ".join(str(value) for value in partition.get("classes", [])))
        )

    def _delete(self):
        rows = sorted({index.row() for index in self.table.selectedIndexes()}, reverse=True)
        for row in rows:
            self.table.removeRow(row)

    def _finish(self):
        result = []
        names = set()
        try:
            for row in range(self.table.rowCount()):
                name = self.table.item(row, 0).text().strip()
                if not name or name in names:
                    raise ValueError("Partition names must be nonempty and unique.")
                classes_text = self.table.item(row, 1).text().strip()
                classes = [] if not classes_text else [
                    int(value.strip()) for value in classes_text.split(",") if value.strip()
                ]
                names.add(name)
                result.append({"name": name, "classes": sorted(set(classes))})
        except (AttributeError, ValueError) as exc:
            QMessageBox.warning(self, "Partitions", str(exc) or "Classes must be integer values.")
            return
        self.result_partitions = result
        self.accept()


class StarterTreeGenerationDialog(QDialog):
    def __init__(self, attributes, partitions=None, parent=None):
        super().__init__(parent)
        self.result_settings = None
        self.partitions = deepcopy(partitions or [])
        self.setWindowTitle("Starter Tree Generation")
        self.resize(520, 480)
        root = QVBoxLayout(self)
        self.automatic = QCheckBox("Select Attributes Automatically")
        self.automatic.setChecked(True)
        root.addWidget(self.automatic)
        self.attributes = QTreeWidget()
        self.attributes.setHeaderLabels(["Attribute", "Use"])
        self.attributes.header().setSectionResizeMode(0, QHeaderView.Stretch)
        for name in attributes:
            item = QTreeWidgetItem([name, ""])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(0, Qt.Unchecked)
            self.attributes.addTopLevelItem(item)
        self.attributes.setEnabled(False)
        self.automatic.toggled.connect(lambda checked: self.attributes.setEnabled(not checked))
        root.addWidget(self.attributes, 1)
        actions = QHBoxLayout()
        partition_button = QPushButton("Partitioning Goal")
        partition_button.clicked.connect(self._partitions)
        actions.addWidget(partition_button)
        actions.addStretch(1)
        generate = QPushButton("Generate")
        generate.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        actions.addWidget(generate)
        actions.addWidget(cancel)
        root.addLayout(actions)

    def _partitions(self):
        dialog = STNEFPartitionsDialog(self.partitions, self)
        if _exec(dialog) == QDialog.Accepted and dialog.result_partitions is not None:
            self.partitions = dialog.result_partitions

    def _finish(self):
        selected = [
            self.attributes.topLevelItem(index).text(0)
            for index in range(self.attributes.topLevelItemCount())
            if self.attributes.topLevelItem(index).checkState(0) == Qt.Checked
        ]
        if not self.automatic.isChecked() and not selected:
            QMessageBox.warning(self, "Starter Tree", "Select at least one attribute.")
            return
        self.result_settings = {
            "automatic": self.automatic.isChecked(),
            "attributes": selected,
            "partitions": deepcopy(self.partitions),
        }
        self.accept()


class STNEFTunerDialog(QDialog):
    CONTINUOUS_ATTRIBUTES = [
        "Region Id", "Channel Detected", "Area", "Polarity", "Primary Channel",
        "Primary Ch Intensity", "Ch1 Intensity", "Ch2 Intensity", "Ch3 Intensity",
        "HLAT CF Intensity", "CF Strip Correlation", "CF Ch1 Intensity", "CF Ch2 Intensity",
        "CF Ch3 Intensity", "CF Ch12 Fusion", "CF Ch13 Fusion", "CF Ch23 Fusion",
        "CF Ch123 Fusion", "Ch1 HLAT AbsMin", "Ch2 HLAT AbsMin", "Ch3 HLAT AbsMin",
        "Ch1 HLAT Noise", "Ch2 HLAT Noise", "Ch3 HLAT Noise", "Ch1 HLAT Gradient",
        "Ch2 HLAT Gradient", "Ch3 HLAT Gradient", "Ch1 HLAT Color", "Ch2 HLAT Color",
        "Ch3 HLAT Color", "Ch1 Fast Threshold", "Ch2 Fast Threshold", "Ch3 Fast Threshold",
        "Die Column", "Die Row", "Wafer X Position", "Wafer Y Position", "USG Code",
        "Scaled Size", "Scaled Factor", "Radius", "Angle", "Rough Bin Code",
        "Max Dim", "Min Dim", "BBox Width", "BBox Height",
    ]
    DISCRETE_ATTRIBUTES = [
        "Test ID", "Partial Die", "Added Die", "X Position", "Venn ID", "Die Y Position",
        "Cluster", "Repeater",
    ]
    ATTRIBUTE_KEYS = {
        "Region Id": "region_id", "Channel Detected": "channel", "Area": "size_um",
        "Polarity": "polarity", "Primary Ch Intensity": "signal", "Ch1 Intensity": "signal",
        "Ch2 Intensity": "signal", "Ch3 Intensity": "signal", "Die Column": "die_x",
        "Die Row": "die_y", "Wafer X Position": "x_um", "Wafer Y Position": "y_um",
        "Rough Bin Code": "roughbin", "Scaled Size": "size_um", "Max Dim": "size_um",
        "Min Dim": "size_um", "BBox Width": "size_um", "BBox Height": "size_um",
        "Test ID": "test", "Venn ID": "venn_id", "Cluster": "cluster_id",
        "Repeater": "repeater_id", "Die Y Position": "die_y", "X Position": "die_x",
    }

    def __init__(self, result, state=None, parent=None):
        super().__init__(parent)
        self.review_result = result
        self.state = deepcopy(state or {})
        classifier = deepcopy(self.state.get("hierarchical_classifier") or {})
        self.nodes = classifier.get("nodes") or [{
            "id": 1, "parent_id": None, "name": "Wafer", "type": "Root",
            "attributes": [], "cuts": [], "groups": {}, "partitions": [],
            "locked": False, "nuisance": False,
        }]
        self.next_node_id = max(int(node.get("id", 0)) for node in self.nodes) + 1
        self.auto_fit_value = bool(classifier.get("auto_fit", True))
        self.zoom_value = int(classifier.get("zoom", 100))
        self.toolbox_state = deepcopy(self.state.get("toolbox") or {})
        self.result_state = None
        self.setWindowTitle("ST-NEF Tuner")
        self.resize(1180, 720)
        root = QVBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._classifier_pane())
        splitter.addWidget(self._toolbox_pane())
        splitter.addWidget(self._properties_pane())
        splitter.setSizes([450, 280, 450])
        root.addWidget(splitter, 1)
        self.status = QLabel("")
        root.addWidget(self.status)
        footer = QHBoxLayout()
        classifier_setup = QPushButton("Classifier Setup...")
        classifier_setup.clicked.connect(self._classifier_setup)
        footer.addWidget(classifier_setup)
        footer.addStretch(1)
        save = QPushButton("Save and Exit")
        save.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        footer.addWidget(save)
        footer.addWidget(cancel)
        root.addLayout(footer)
        self._rebuild_tree(1)

    def _pane(self, title):
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        layout = QVBoxLayout(frame)
        label = QLabel(title)
        label.setStyleSheet("font-weight: 700;")
        layout.addWidget(label)
        return frame, layout

    def _classifier_pane(self):
        frame, layout = self._pane("Hierarchical Classifier")
        actions = QHBoxLayout()
        for label, callback in (
            ("Starter Tree", self._starter_tree), ("Add NN", self._add_nn_node),
            ("Create NEF", self._create_nef_node), ("Lock", self._toggle_lock),
            ("Delete", self._delete_node), ("Nuisance", self._toggle_nuisance),
        ):
            button = QPushButton(label)
            button.clicked.connect(callback)
            button.setMaximumWidth(82)
            actions.addWidget(button)
        layout.addLayout(actions)
        self.classifier_tree = QTreeWidget()
        self.classifier_tree.setHeaderLabels(["Node", "Type", "State"])
        self.classifier_tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.classifier_tree.currentItemChanged.connect(self._node_changed)
        layout.addWidget(self.classifier_tree, 1)
        view = QHBoxLayout()
        self.auto_fit = QCheckBox("Auto Fit")
        self.auto_fit.setChecked(self.auto_fit_value)
        self.zoom = QSlider(Qt.Horizontal)
        self.zoom.setRange(50, 250)
        self.zoom.setValue(self.zoom_value)
        self.zoom.setEnabled(not self.auto_fit.isChecked())
        self.auto_fit.toggled.connect(lambda checked: self.zoom.setEnabled(not checked))
        view.addWidget(self.auto_fit)
        view.addWidget(QLabel("Zoom"))
        view.addWidget(self.zoom, 1)
        layout.addLayout(view)
        return frame

    def _toolbox_pane(self):
        frame, layout = self._pane("Toolbox")
        self.toolbox = QTreeWidget()
        self.toolbox.setHeaderLabels(["Attributes"])
        for category, attributes in (
            ("Continuous Attributes", self.CONTINUOUS_ATTRIBUTES),
            ("Discrete Attributes", self.DISCRETE_ATTRIBUTES),
        ):
            parent_item = QTreeWidgetItem([category])
            for attribute in attributes:
                child = QTreeWidgetItem([attribute])
                child.setData(0, Qt.UserRole, attribute)
                parent_item.addChild(child)
            self.toolbox.addTopLevelItem(parent_item)
        self.toolbox.expandAll()
        self.toolbox.itemDoubleClicked.connect(self._toolbox_double_clicked)
        layout.addWidget(self.toolbox, 1)
        self.view_all = QCheckBox("View All")
        self.view_all.setChecked(bool(self.toolbox_state.get("view_all", True)))
        self.log_histogram = QCheckBox("Log Histogram")
        self.log_histogram.setChecked(bool(self.toolbox_state.get("log_histogram", False)))
        self.hide_unclassified = QCheckBox("Hide Unclassified")
        self.hide_unclassified.setChecked(bool(self.toolbox_state.get("hide_unclassified", False)))
        for check in (self.view_all, self.log_histogram, self.hide_unclassified):
            check.toggled.connect(self._refresh_property_chart)
            layout.addWidget(check)
        return frame

    def _properties_pane(self):
        frame, layout = self._pane("Properties")
        self.attribute_label = QLabel("Select a node and double-click an attribute.")
        self.attribute_label.setWordWrap(True)
        layout.addWidget(self.attribute_label)
        self.property_chart = DefectChart()
        self.property_chart.setMinimumHeight(180)
        layout.addWidget(self.property_chart, 1)
        controls = QHBoxLayout()
        self.cut_value = QDoubleSpinBox()
        self.cut_value.setRange(-1000000.0, 1000000.0)
        self.cut_value.setDecimals(3)
        controls.addWidget(QLabel("Cut Line"))
        controls.addWidget(self.cut_value)
        for label, callback in (
            ("Insert", self._insert_cut), ("Apply", self._apply_cut), ("Delete", self._delete_cut),
            ("Group", self._group_cuts), ("Ungroup", self._ungroup_cuts),
        ):
            button = QPushButton(label)
            button.clicked.connect(callback)
            controls.addWidget(button)
        layout.addLayout(controls)
        self.cuts = QTableWidget(0, 2)
        self.cuts.setHorizontalHeaderLabels(["Position", "Group"])
        self.cuts.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.cuts.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.cuts.setSelectionMode(QAbstractItemView.ExtendedSelection)
        layout.addWidget(self.cuts)
        options = QHBoxLayout()
        self.show_labels = QCheckBox("Show Group Labels")
        self.legend = QComboBox()
        self.legend.addItems(["Manual Classes", "Super Classes", "Rough Classes", "Groups", "Partitions"])
        partitions = QPushButton("Partitions...")
        partitions.clicked.connect(self._edit_partitions)
        options.addWidget(self.show_labels)
        options.addWidget(QLabel("Legend"))
        options.addWidget(self.legend)
        options.addWidget(partitions)
        layout.addLayout(options)
        return frame

    def _node(self, node_id):
        return next((node for node in self.nodes if int(node.get("id", 0)) == int(node_id)), None)

    def _selected_node(self):
        item = self.classifier_tree.currentItem()
        return self._node(item.data(0, Qt.UserRole)) if item is not None else None

    def _rebuild_tree(self, selected_id=None):
        self.classifier_tree.blockSignals(True)
        self.classifier_tree.clear()
        items = {}
        for node in self.nodes:
            state = "Nuisance" if node.get("nuisance") else ("Locked" if node.get("locked") else "")
            item = QTreeWidgetItem([node.get("name", "Node"), node.get("type", ""), state])
            item.setData(0, Qt.UserRole, node["id"])
            items[node["id"]] = item
        for node in self.nodes:
            item = items[node["id"]]
            parent_item = items.get(node.get("parent_id"))
            if parent_item is None:
                self.classifier_tree.addTopLevelItem(item)
            else:
                parent_item.addChild(item)
        self.classifier_tree.expandAll()
        selected = items.get(selected_id) or next(iter(items.values()), None)
        if selected is not None:
            self.classifier_tree.setCurrentItem(selected)
        self.classifier_tree.blockSignals(False)
        self._node_changed(selected)

    def _node_changed(self, *_args):
        node = self._selected_node()
        if node is None:
            return
        attributes = node.get("attributes") or []
        self.attribute_label.setText(
            f"{node.get('name')} - " + (" vs ".join(attributes) if attributes else "No attribute applied")
        )
        self.cuts.setRowCount(0)
        groups = node.get("groups") or {}
        for index, value in enumerate(node.get("cuts") or []):
            self.cuts.insertRow(index)
            self.cuts.setItem(index, 0, QTableWidgetItem(str(value)))
            self.cuts.setItem(index, 1, QTableWidgetItem(str(groups.get(str(index), ""))))
        self._refresh_property_chart()
        if hasattr(self, "status"):
            nuisance_nodes = sum(bool(item.get("nuisance")) for item in self.nodes)
            divisor = max(2, 7 - min(4, nuisance_nodes))
            eliminated = sum(
                self._numeric_defect_id(defect) % divisor == 0
                for defect in self.review_result.get("defects", [])
            )
            self.status.setText(
                f"{eliminated} defect(s) eliminated by ST; "
                f"{len(self.review_result.get('defects', [])) - eliminated}/"
                f"{len(self.review_result.get('defects', []))} caught."
            )

    @staticmethod
    def _numeric_defect_id(defect):
        identifier = defect.get("id", 0)
        try:
            return int(identifier)
        except (TypeError, ValueError):
            return sum(ord(character) for character in str(identifier))

    def _display_defects(self, node):
        defects = list(self.review_result.get("defects", []))
        if self.hide_unclassified.isChecked():
            defects = [defect for defect in defects if int(defect.get("class_code", 0)) != 0]
        if self.view_all.isChecked() or node is None or node.get("parent_id") is None:
            return defects
        path = []
        cursor = node
        while cursor is not None and cursor.get("parent_id") is not None:
            path.append(cursor)
            cursor = self._node(cursor.get("parent_id"))
        for path_node in reversed(path):
            siblings = sorted(
                [item for item in self.nodes if item.get("parent_id") == path_node.get("parent_id")],
                key=lambda item: int(item.get("id", 0)),
            )
            if len(siblings) > 1:
                branch = siblings.index(path_node)
                defects = [
                    defect for defect in defects
                    if self._numeric_defect_id(defect) % len(siblings) == branch
                ]
        return defects

    def _refresh_property_chart(self):
        node = self._selected_node()
        attributes = (node or {}).get("attributes") or []
        if not attributes:
            self.property_chart.set_counts({}, "Attribute Properties")
            self.property_chart.set_cut_lines([])
            return
        defects = self._display_defects(node)
        if len(attributes) == 2:
            x_key = self.ATTRIBUTE_KEYS.get(attributes[0], "signal")
            y_key = self.ATTRIBUTE_KEYS.get(attributes[1], "size_um")
            points = [
                (float(defect.get(x_key, 0.0)), float(defect.get(y_key, 0.0)))
                for defect in defects
                if isinstance(defect.get(x_key, 0.0), (int, float))
                and isinstance(defect.get(y_key, 0.0), (int, float))
            ]
            self.property_chart.set_points(points, f"{attributes[0]} vs {attributes[1]}")
            self.property_chart.set_cut_lines((node or {}).get("cuts") or [])
            self.property_chart.set_plot_options(
                scale="Log" if self.log_histogram.isChecked() else "Linear",
                grid=True, legend=False, group_size=3, zoom=1.0,
            )
            return
        key = self.ATTRIBUTE_KEYS.get(attributes[0], "signal")
        counts = Counter()
        for defect in defects:
            value = defect.get(key, "-")
            if isinstance(value, float):
                value = round(value, 1)
            counts[str(value)] += 1
        self.property_chart.set_counts(counts, attributes[0], "Bar")
        self.property_chart.set_cut_lines((node or {}).get("cuts") or [])
        self.property_chart.set_plot_options(
            scale="Log Y" if self.log_histogram.isChecked() else "Linear",
            grid=True, legend=True, group_size=3, zoom=1.0,
        )

    def _add_node(self, parent_id, name, node_type, **values):
        node = {
            "id": self.next_node_id, "parent_id": parent_id, "name": name, "type": node_type,
            "attributes": [], "cuts": [], "groups": {}, "partitions": [],
            "locked": False, "nuisance": False,
        }
        node.update(values)
        self.next_node_id += 1
        self.nodes.append(node)
        self._rebuild_tree(node["id"])
        return node

    def _starter_tree(self):
        node = self._selected_node()
        if node is None or node.get("locked"):
            return
        dialog = StarterTreeGenerationDialog(
            self.CONTINUOUS_ATTRIBUTES + self.DISCRETE_ATTRIBUTES,
            node.get("partitions"), self,
        )
        if _exec(dialog) == QDialog.Accepted and dialog.result_settings:
            self._generate_starter_tree(dialog.result_settings)

    def _generate_starter_tree(self, settings):
        node = self._selected_node()
        if node is None or node.get("locked"):
            return
        attributes = settings.get("attributes") or ["Primary Ch Intensity", "Area"]
        node["partitions"] = deepcopy(settings.get("partitions") or [])
        generated = self._add_node(
            node["id"], "Starter Tree", "Attribute", attributes=attributes[:2],
            cuts=[45.0], partitions=deepcopy(node["partitions"]),
        )
        self.status.setText(f"Starter Tree generated with {len(generated['attributes'])} attribute(s).")

    def _add_nn_node(self):
        node = self._selected_node()
        if node is not None and not node.get("locked"):
            self._add_node(node["id"], "NN Node", "NN")

    def _create_nef_node(self):
        node = self._selected_node()
        if node is None or node.get("locked"):
            return
        parent_id = node["id"]
        self._add_node(parent_id, "Defect", "NEF Partition")
        self.classifier_tree.blockSignals(True)
        self.classifier_tree.setCurrentItem(self.classifier_tree.topLevelItem(0))
        self.classifier_tree.blockSignals(False)
        self._add_node(parent_id, "Nuisance", "NEF Partition", nuisance=True)

    def _toggle_lock(self):
        node = self._selected_node()
        if node is not None:
            node["locked"] = not node.get("locked", False)
            self._rebuild_tree(node["id"])

    def _descendant_ids(self, node_id):
        result = {node_id}
        for child in [node for node in self.nodes if node.get("parent_id") == node_id]:
            result.update(self._descendant_ids(child["id"]))
        return result

    def _delete_node(self):
        node = self._selected_node()
        if node is None or node.get("parent_id") is None or node.get("locked"):
            return
        parent_id = node["parent_id"]
        remove_ids = self._descendant_ids(node["id"])
        self.nodes = [item for item in self.nodes if item["id"] not in remove_ids]
        self._rebuild_tree(parent_id)

    def _toggle_nuisance(self):
        node = self._selected_node()
        if node is not None and not node.get("locked"):
            node["nuisance"] = not node.get("nuisance", False)
            self._rebuild_tree(node["id"])

    def _toolbox_double_clicked(self, item, _column):
        attribute = item.data(0, Qt.UserRole)
        if attribute:
            self._apply_attribute(attribute)

    def _apply_attribute(self, attribute):
        node = self._selected_node()
        if node is None or node.get("locked"):
            return
        attributes = node.setdefault("attributes", [])
        if attribute not in attributes:
            if len(attributes) >= 2:
                attributes.pop(0)
            attributes.append(attribute)
        node["type"] = "2-D Attribute" if len(attributes) == 2 else "1-D Attribute"
        self._rebuild_tree(node["id"])

    def _selected_cut_rows(self):
        return sorted({index.row() for index in self.cuts.selectedIndexes()})

    def _insert_cut(self):
        node = self._selected_node()
        if node is None or node.get("locked") or not node.get("attributes"):
            return
        node.setdefault("cuts", []).append(self.cut_value.value())
        node["cuts"] = sorted(set(node["cuts"]))
        self._node_changed()

    def _apply_cut(self):
        node = self._selected_node()
        rows = self._selected_cut_rows()
        if node is None or node.get("locked") or len(rows) != 1:
            return
        node["cuts"][rows[0]] = self.cut_value.value()
        node["cuts"] = sorted(set(node["cuts"]))
        self._node_changed()

    def _delete_cut(self):
        node = self._selected_node()
        if node is None or node.get("locked"):
            return
        for row in reversed(self._selected_cut_rows()):
            node["cuts"].pop(row)
        node["groups"] = {}
        self._node_changed()

    def _group_cuts(self):
        node = self._selected_node()
        rows = self._selected_cut_rows()
        if node is None or len(rows) < 2:
            return
        groups = node.setdefault("groups", {})
        group_id = max([int(value) for value in groups.values()] or [0]) + 1
        for row in rows:
            groups[str(row)] = group_id
        self._node_changed()

    def _ungroup_cuts(self):
        node = self._selected_node()
        if node is None:
            return
        groups = node.setdefault("groups", {})
        for row in self._selected_cut_rows():
            groups.pop(str(row), None)
        self._node_changed()

    def _edit_partitions(self):
        node = self._selected_node()
        if node is None:
            return
        dialog = STNEFPartitionsDialog(node.get("partitions"), self)
        if _exec(dialog) == QDialog.Accepted and dialog.result_partitions is not None:
            node["partitions"] = dialog.result_partitions
            self.legend.setCurrentText("Partitions")

    def _classifier_setup(self):
        dialog = NuisanceFilterSetupDialog(self.state, self)
        if _exec(dialog) == QDialog.Accepted and dialog.result_state is not None:
            hierarchical = self.state.get("hierarchical_classifier")
            toolbox = self.state.get("toolbox")
            self.state = deepcopy(dialog.result_state)
            self.state["hierarchical_classifier"] = hierarchical
            self.state["toolbox"] = toolbox

    def _finish(self):
        nuisance_nodes = sum(bool(node.get("nuisance")) for node in self.nodes)
        classifiers = deepcopy(self.state.get("classifiers") or [])
        if not classifiers:
            classifiers = [{"name": "ST-NEF Hierarchical", "type": "ST-NEF", "st_nef": True}]
        self.result_state = {
            **deepcopy(self.state),
            "classifiers": classifiers,
            "hierarchical_classifier": {
                "nodes": deepcopy(self.nodes),
                "auto_fit": self.auto_fit.isChecked(),
                "zoom": self.zoom.value(),
                "legend": self.legend.currentText(),
                "show_group_labels": self.show_labels.isChecked(),
            },
            "toolbox": {
                "view_all": self.view_all.isChecked(),
                "log_histogram": self.log_histogram.isChecked(),
                "hide_unclassified": self.hide_unclassified.isChecked(),
            },
            "nuisance_node_count": nuisance_nodes,
        }
        self.accept()


class SensitivityMaxLimitsDialog(QDialog):
    DEFAULTS = {"Noise": 2.5, "ABSMIN": 250.0, "Gradient": 2.0}

    def __init__(self, limits=None, parent=None, minimums=None):
        super().__init__(parent)
        self.result_limits = None
        self.controls = {}
        self.setWindowTitle("Max Limit Configuration")
        layout = QGridLayout(self)
        current = {**self.DEFAULTS, **(limits or {})}
        minimums = {name: float((minimums or {}).get(name, 0.0)) for name in self.DEFAULTS}
        absolute = {"Noise": 100.0, "ABSMIN": 4095.0, "Gradient": 100.0}
        for row, name in enumerate(("Noise", "ABSMIN", "Gradient")):
            control = QDoubleSpinBox()
            control.setRange(minimums[name], absolute[name])
            control.setValue(max(minimums[name], float(current[name])))
            self.controls[name] = control
            layout.addWidget(QLabel(name), row, 0)
            layout.addWidget(control, row, 1)
            layout.addWidget(QLabel(f"Allowed range {minimums[name]:g} to {absolute[name]:g}"), row, 2)
        reset = QPushButton("Reset")
        reset.clicked.connect(self._reset)
        ok = QPushButton("OK")
        ok.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        layout.addWidget(reset, 3, 0)
        layout.addWidget(ok, 3, 1)
        layout.addWidget(cancel, 3, 2)

    def _reset(self):
        for name, value in self.DEFAULTS.items():
            self.controls[name].setValue(max(self.controls[name].minimum(), value))

    def _finish(self):
        self.result_limits = {name: control.value() for name, control in self.controls.items()}
        self.accept()


class AdvancedSensitivityParametersDialog(QDialog):
    def __init__(self, values, algorithms, parent=None):
        super().__init__(parent)
        self.result_parameters = None
        self.values = deepcopy(values or {})
        self.algorithms = deepcopy(algorithms)
        self.setWindowTitle("Advanced Sensitivity Parameters")
        self.resize(560, 480)
        root = QVBoxLayout(self)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Algorithm Parameter", "Value"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        for algorithm, parameters in self.algorithms.items():
            parent_item = QTreeWidgetItem([algorithm, ""])
            parent_item.setFlags(parent_item.flags() & ~Qt.ItemIsEditable)
            self.tree.addTopLevelItem(parent_item)
            for parameter in parameters:
                default = {
                    "Threshold": 45.0, "Noise": 1.0, "ABSMIN": 100.0,
                    "Gradient": 1.0, "Color": 1.0, "Max Threshold": 250.0,
                    "Local Noise": 1.0,
                }.get(parameter, 0.0)
                value = self.values.get(algorithm, {}).get(parameter, default)
                child = QTreeWidgetItem([parameter, str(value)])
                child.setFlags(child.flags() | Qt.ItemIsEditable)
                child.setData(0, Qt.UserRole, (algorithm, parameter))
                parent_item.addChild(child)
        self.tree.expandAll()
        root.addWidget(self.tree, 1)
        footer = QHBoxLayout()
        footer.addStretch(1)
        ok = QPushButton("OK")
        ok.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        footer.addWidget(ok)
        footer.addWidget(cancel)
        root.addLayout(footer)

    def _finish(self):
        result = {}
        try:
            for index in range(self.tree.topLevelItemCount()):
                parent_item = self.tree.topLevelItem(index)
                for child_index in range(parent_item.childCount()):
                    child = parent_item.child(child_index)
                    algorithm, parameter = child.data(0, Qt.UserRole)
                    value = float(child.text(1))
                    if value < 0 or value > 4095:
                        raise ValueError
                    result.setdefault(algorithm, {})[parameter] = value
        except (TypeError, ValueError):
            QMessageBox.warning(self, "Advanced Sensitivity Parameters", "All parameter values must be between 0 and 4095.")
            return
        self.result_parameters = result
        self.accept()


class SensitivityTunerDialog(QDialog):
    PARAMETERS = {
        "HLAT": ["Threshold", "Noise", "ABSMIN", "Gradient", "Color"],
        "HLAT CF": ["Threshold", "Noise"],
        "FAST": ["Threshold"],
        "CF2": ["Threshold", "Noise"],
        "CF3": ["Threshold", "Noise"],
        "LAT": ["Threshold"],
        "Max Threshold": ["Max Threshold"],
        "Local Noise Filter": ["Local Noise"],
    }

    def __init__(self, result, recipe=None, state=None, parent=None):
        super().__init__(parent)
        self.review_result = result
        self.recipe = recipe
        self.state = deepcopy(state or {})
        self.result_state = None
        self.selected_regions = deepcopy(self.state.get("regions"))
        self.max_limits = deepcopy(self.state.get("max_limits") or SensitivityMaxLimitsDialog.DEFAULTS)
        self.committed = bool(self.state.get("committed", False))
        self.parameter_values = deepcopy(self.state.get("parameter_values") or {})
        self.edited_parameters = set(
            self.state.get("edited_parameters") or self.parameter_values.keys()
        )
        self.committed_parameters = set(self.state.get("committed_parameters") or [])
        self.advanced_parameter_values = deepcopy(self.state.get("advanced_parameter_values") or {})
        self.session_baseline = deepcopy(self.state)
        self._loading_parameter = False
        self.current_evaluation = {}
        self.test_evaluation = {}
        self.nef_states = deepcopy(self.state.get("nef_states") or {})
        self.nef_enabled_tests = set(self.state.get("nef_enabled_tests") or [])
        for test_state in (recipe or {}).get("tests", []):
            name = test_state.get("name")
            if name and test_state.get("nef"):
                self.nef_states.setdefault(name, deepcopy(test_state["nef"]))
                if test_state.get("run_nef"):
                    self.nef_enabled_tests.add(name)
        self.nef_filtered_ids = []
        self.setWindowTitle("Sensitivity Tuner")
        self.resize(1120, 720)
        root = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        for label, tooltip, callback in (
            ("Prev *", "Previous uncommitted parameter", lambda: self._navigate(-1, True)),
            ("Prev", "Previous parameter", lambda: self._navigate(-1)),
            ("Next", "Next parameter", lambda: self._navigate(1)),
            ("Next *", "Next uncommitted parameter", lambda: self._navigate(1, True)),
            ("Commit", "Commit the current parameter", self._commit),
            ("ST-NEF", "Switch to ST-NEF Tuner", self._switch_nef),
            ("Regions", "Region Selection", self._select_regions),
            ("Limits", "Maximum Limit Configuration", self._max_limits),
            ("Advanced", "Advanced Sensitivity Parameters", self._advanced_parameters),
        ):
            button = QPushButton(label)
            button.setToolTip(tooltip)
            button.setMaximumWidth(110)
            button.clicked.connect(callback)
            toolbar.addWidget(button)
        toolbar.addStretch(1)
        root.addLayout(toolbar)
        auto_tune = QHBoxLayout()
        auto_tune.addWidget(QLabel("Scatter Defect"))
        self.scatter_defect = QComboBox()
        for defect in result.get("defects", []):
            self.scatter_defect.addItem(
                f"ID {defect.get('id')} / Signal {defect.get('signal', 0)}",
                defect.get("id"),
            )
        auto_tune.addWidget(self.scatter_defect, 1)
        catch = QPushButton("Catch Defect")
        catch.clicked.connect(lambda: self._auto_tune_defect(True))
        lose = QPushButton("Lose Defect")
        lose.clicked.connect(lambda: self._auto_tune_defect(False))
        auto_tune.addWidget(catch)
        auto_tune.addWidget(lose)
        root.addLayout(auto_tune)

        selectors = QGridLayout()
        self.test = QComboBox()
        self.test.addItems(result.get("sensitivity_data_tests") or result.get("selected_tests") or ["Test 1"])
        self.test.setCurrentText(self.state.get("test", self.test.currentText()))
        self.region = QComboBox()
        self.polarity = QComboBox()
        self.polarity.addItems(["Primary", "Secondary", "Dark", "Both"])
        self.polarity.setCurrentText(self.state.get("polarity", "Both"))
        self.algorithm = QComboBox()
        self.algorithm.addItems(list(self.PARAMETERS))
        self.algorithm.setCurrentText(self.state.get("algorithm", "HLAT"))
        self.path = QComboBox()
        self.path.addItems(["Regular Path", "Segmentation Path"])
        self.channel = QComboBox()
        self.channel.addItems(["Channel 1", "Channel 2", "Channel 3", "Channel Fusion"])
        self.parameter = QComboBox()
        selectors_data = [
            ("Test", self.test), ("Region", self.region), ("Defect Type", self.polarity),
            ("Algorithm", self.algorithm), ("Detection Path", self.path),
            ("Channel", self.channel), ("Parameter", self.parameter),
        ]
        for index, (label, control) in enumerate(selectors_data):
            control.setMaximumWidth(250)
            selectors.addWidget(QLabel(label), index // 4 * 2, index % 4)
            selectors.addWidget(control, index // 4 * 2 + 1, index % 4)
        root.addLayout(selectors)

        tuning = QHBoxLayout()
        tuning.addWidget(QLabel("New Value"))
        self.value = QDoubleSpinBox()
        self.value.setRange(0.0, 4095.0)
        self.value.setDecimals(3)
        self.value.setValue(float(self.state.get("value", 45.0)))
        tuning.addWidget(self.value)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 4095)
        self.slider.setValue(int(self.value.value()))
        self.slider.valueChanged.connect(lambda value: self.value.setValue(float(value)))
        self.value.valueChanged.connect(lambda value: self.slider.setValue(int(value)))
        tuning.addWidget(self.slider, 1)
        self.parameter_status = QLabel("Original")
        tuning.addWidget(self.parameter_status)
        root.addLayout(tuning)

        plots = QHBoxLayout()
        self.tuner_chart = DefectChart()
        self.scatter_chart = DefectChart()
        plots.addWidget(self.tuner_chart, 1)
        plots.addWidget(self.scatter_chart, 1)
        root.addLayout(plots, 1)
        self.summary_table = QTableWidget(0, 3)
        self.summary_table.setHorizontalHeaderLabels(["Defect Group", "Count", "Percent"])
        self.summary_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.summary_table.verticalHeader().setVisible(False)
        root.addWidget(self.summary_table)

        plot_options = QHBoxLayout()
        plot_options.addWidget(QLabel("Partition"))
        self.partition = QComboBox()
        self.partition.addItems(["None", "Class Code", "Test", "Region", "Source"])
        self.partition.setCurrentText(self.state.get("partition", "None"))
        plot_options.addWidget(self.partition)
        plot_options.addWidget(QLabel("Group Size"))
        self.group_size = QSpinBox()
        self.group_size.setRange(1, 5)
        self.group_size.setValue(int(self.state.get("group_size", 3)))
        plot_options.addWidget(self.group_size)
        plot_options.addWidget(QLabel("Scale"))
        self.plot_scale = QComboBox()
        self.plot_scale.addItems(["Linear", "Log", "Log X", "Log Y"])
        self.plot_scale.setCurrentText(self.state.get("plot_scale", "Linear"))
        plot_options.addWidget(self.plot_scale)
        self.plot_grid = QCheckBox("Grid")
        self.plot_grid.setChecked(bool(self.state.get("plot_grid", False)))
        self.plot_legend = QCheckBox("Legend")
        self.plot_legend.setChecked(bool(self.state.get("plot_legend", True)))
        plot_options.addWidget(self.plot_grid)
        plot_options.addWidget(self.plot_legend)
        plot_options.addWidget(QLabel("Zoom"))
        self.plot_zoom = QSlider(Qt.Horizontal)
        self.plot_zoom.setRange(100, 400)
        self.plot_zoom.setValue(int(self.state.get("plot_zoom", 100)))
        plot_options.addWidget(self.plot_zoom, 1)
        reset_zoom = QPushButton("Reset Zoom")
        reset_zoom.clicked.connect(lambda: self.plot_zoom.setValue(100))
        plot_options.addWidget(reset_zoom)
        root.addLayout(plot_options)

        options = QGridLayout()
        self.show_mode = QComboBox()
        self.show_mode.addItems(["Show All Defects", "Show Detected Defects", "Show Undetected Defects"])
        self.show_mode.setCurrentText(self.state.get("show_mode", "Show All Defects"))
        self.show_mode.setMaximumWidth(190)
        self.filter_scope = QComboBox()
        self.filter_scope.addItems(["No Review Filter", "Filter to Current Parameter", "Filter to Current Test"])
        self.filter_scope.setCurrentText(self.state.get("filter_scope", "No Review Filter"))
        self.filter_scope.setMaximumWidth(190)
        self.auto_sort = QCheckBox("Auto Sort on Classification Code")
        self.auto_sort.setChecked(bool(self.state.get("auto_sort")))
        self.auto_sort.setMaximumWidth(240)
        self.dark_filter = QComboBox()
        self.dark_filter.addItems([
            "Both", "Primary Dark Defects Only", "Secondary-Die Defects Only",
        ])
        self.dark_filter.setCurrentText(self.state.get("dark_filter", "Both"))
        self.dark_filter.setMaximumWidth(220)
        self.enable_nef = QCheckBox("Enable ST-NEF")
        options.addWidget(QLabel("Defect Display"), 0, 0)
        options.addWidget(self.show_mode, 0, 1)
        options.addWidget(QLabel("Review Filter"), 0, 2)
        options.addWidget(self.filter_scope, 0, 3)
        options.addWidget(QLabel("Dark Defects"), 0, 4)
        options.addWidget(self.dark_filter, 0, 5)
        options.addWidget(self.auto_sort, 1, 1, 1, 2)
        options.addWidget(self.enable_nef, 1, 3, 1, 2)
        options.setColumnStretch(6, 1)
        root.addLayout(options)

        identity = QHBoxLayout()
        identity.addWidget(QLabel("Recipe Name"))
        self.save_name = QLineEdit(f"{(recipe or {}).get('inspection', 'Recipe')}_Tuned")
        identity.addWidget(self.save_name)
        identity.addWidget(QLabel("Device"))
        self.save_device = QLineEdit((recipe or {}).get("device", "Device1"))
        identity.addWidget(self.save_device)
        identity.addWidget(QLabel("Layer"))
        self.save_step = QLineEdit((recipe or {}).get("step", "Layer1"))
        identity.addWidget(self.save_step)
        root.addLayout(identity)

        finish_row = QHBoxLayout()
        self.finish_action = QComboBox()
        self.finish_action.addItems([
            "Save & Exit", "Save Session Recipe", "Save Recipe As...", "Export Recipe As...",
            "Restore Session - Parameters Only", "Restore Session - All",
            "Restore Inspection - Parameters Only", "Restore Inspection - All",
            "Exit Without Saving",
        ])
        finish_row.addWidget(QLabel("Finish"))
        finish_row.addWidget(self.finish_action)
        finish_row.addStretch(1)
        finish = QPushButton("Finish")
        finish.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        finish_row.addWidget(finish)
        finish_row.addWidget(cancel)
        root.addLayout(finish_row)

        self.test.currentTextChanged.connect(self._refresh_regions)
        self.region.currentTextChanged.connect(self._selection_changed)
        self.polarity.currentTextChanged.connect(self._selection_changed)
        self.algorithm.currentTextChanged.connect(self._algorithm_changed)
        self.path.currentTextChanged.connect(self._selection_changed)
        self.channel.currentTextChanged.connect(self._selection_changed)
        self.parameter.currentTextChanged.connect(self._selection_changed)
        self.value.valueChanged.connect(self._modified)
        self.dark_filter.currentTextChanged.connect(self._update)
        self.enable_nef.toggled.connect(self._toggle_nef)
        for control in (
            self.partition, self.group_size, self.plot_scale,
            self.plot_grid, self.plot_legend, self.plot_zoom,
        ):
            if hasattr(control, "currentTextChanged"):
                control.currentTextChanged.connect(self._plot_options_changed)
            elif hasattr(control, "valueChanged"):
                control.valueChanged.connect(self._plot_options_changed)
            else:
                control.toggled.connect(self._plot_options_changed)
        self.partition.currentTextChanged.connect(self._update)
        self._refresh_regions()
        self._algorithm_changed()

    def _refresh_regions(self, *_args):
        current = self.region.currentText()
        regions = sorted({
            str(item.get("region_id", "R1"))
            for item in self.review_result.get("defects", [])
            if item.get("test") == self.test.currentText()
        }) or ["R1"]
        self.available_regions = regions
        self.region.blockSignals(True)
        self.region.clear()
        self.region.addItems(regions)
        self.region.setCurrentText(current if current in regions else regions[0])
        self.region.blockSignals(False)
        self.enable_nef.blockSignals(True)
        self.enable_nef.setChecked(self.test.currentText() in self.nef_enabled_tests)
        self.enable_nef.blockSignals(False)
        self._load_parameter_value()
        self._update()

    def _algorithm_changed(self, *_args):
        current = self.parameter.currentText()
        parameters = self.PARAMETERS[self.algorithm.currentText()]
        self.parameter.blockSignals(True)
        self.parameter.clear()
        self.parameter.addItems(parameters)
        self.parameter.setCurrentText(current if current in parameters else parameters[0])
        self.parameter.blockSignals(False)
        self._load_parameter_value()
        self._update()

    def _selection_key(self):
        return "|".join((
            self.test.currentText(), self.region.currentText(), self.polarity.currentText(),
            self.algorithm.currentText(), self.path.currentText(), self.channel.currentText(),
            self.parameter.currentText(),
        ))

    def _parameter_default(self):
        advanced = self.advanced_parameter_values.get(self.algorithm.currentText(), {})
        if self.parameter.currentText() in advanced:
            return float(advanced[self.parameter.currentText()])
        channel_index = {
            "Channel 1": 0, "Channel 2": 1, "Channel 3": 2, "Channel Fusion": 0,
        }.get(self.channel.currentText(), 0)
        for test_state in (self.recipe or {}).get("tests", []):
            if test_state.get("name") != self.test.currentText():
                continue
            regions = (test_state.get("sensitivity") or {}).get("regions") or {}
            region_state = regions.get(self.region.currentText())
            if region_state is None and regions:
                region_state = next(iter(regions.values()))
            algorithm_state = ((region_state or {}).get("algorithms") or {}).get(
                self.algorithm.currentText(), {}
            )
            channels = algorithm_state.get("channels") or []
            if channels:
                channel_state = channels[min(channel_index, len(channels) - 1)]
                value = channel_state.get(self.parameter.currentText())
                if isinstance(value, (int, float)):
                    return float(value)
        return {
            "Threshold": 45.0, "Noise": 1.0, "ABSMIN": 100.0, "Gradient": 1.0,
            "Color": 1.0, "Max Threshold": 250.0, "Local Noise": 1.0,
        }.get(self.parameter.currentText(), 45.0)

    def _parameter_floor(self, parameter):
        target = parameter.lower().replace(" ", "")
        values = []

        def visit(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    normalized = str(key).lower().replace("_", "").replace(" ", "")
                    if normalized == target and isinstance(child, (int, float)):
                        values.append(float(child))
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)

        for test_state in (self.recipe or {}).get("tests", []):
            if test_state.get("name") == self.test.currentText():
                visit(test_state.get("sensitivity") or {})
        return max(values or [0.0])

    def _update_parameter_range(self):
        maximum = 4095.0
        if self.algorithm.currentText() == "HLAT":
            name = self.parameter.currentText()
            if name in self.max_limits:
                maximum = max(self._parameter_floor(name), float(self.max_limits[name]))
        self.value.setRange(0.0, maximum)
        self.slider.setRange(0, max(1, int(maximum)))

    def _load_parameter_value(self):
        if not hasattr(self, "value") or not self.parameter.currentText() or not self.region.currentText():
            return
        key = self._selection_key()
        if key not in self.parameter_values:
            fallback = self.state.get("value") if not self.parameter_values else None
            self.parameter_values[key] = float(fallback if fallback is not None else self._parameter_default())
        self._loading_parameter = True
        self._update_parameter_range()
        self.value.setValue(float(self.parameter_values[key]))
        self.slider.setValue(int(self.value.value()))
        self._loading_parameter = False
        if key in self.committed_parameters:
            self.parameter_status.setText("Modified - committed")
            self.parameter_status.setStyleSheet("background: #5fc56d; padding: 3px;")
        elif key in self.edited_parameters:
            self.parameter_status.setText("Modified - uncommitted")
            self.parameter_status.setStyleSheet("background: #f1d85a; padding: 3px;")
        else:
            self.parameter_status.setText("Original")
            self.parameter_status.setStyleSheet("")

    def _selection_changed(self, *_args):
        self._load_parameter_value()
        self._update()

    def _regions(self):
        return self.selected_regions if self.selected_regions is not None else [self.region.currentText()]

    def _update(self, *_args):
        if not self.test.currentText() or not self.region.currentText():
            return
        tuning_result = self._effective_review_result()
        self.current_evaluation = evaluate_sensitivity_tuning(
            tuning_result,
            test=self.test.currentText(),
            regions=self._regions(),
            polarity=self.polarity.currentText(),
            dark_filter=self.dark_filter.currentText(),
            threshold=self.value.value(),
        )
        data = self.current_evaluation
        thresholds = {
            "Current": data["detected"],
            "Original": max(data["detected"], int(data["considered"] * 0.72)),
        }
        if self.review_result.get("combined_for_sensitivity_tuner"):
            detected_ids = set(data["detected_ids"])
            thresholds["Original Source"] = sum(
                item.get("id") in detected_ids and not item.get("combined_source_id")
                for item in tuning_result.get("defects", [])
            )
            for source in self.review_result.get("combined_sources", []):
                source_id = source.get("id")
                thresholds[source.get("lot_id") or "Imported Source"] = sum(
                    item.get("id") in detected_ids and item.get("combined_source_id") == source_id
                    for item in tuning_result.get("defects", [])
                )
        self.tuner_chart.set_counts(thresholds, "Tuner Chart - Threshold vs Defects")
        considered_ids = set(data["considered_ids"])
        detected_ids = set(data["detected_ids"])
        partition_key = {
            "Class Code": "class_code", "Test": "test", "Region": "region_id",
            "Source": "combined_source_lot",
        }.get(self.partition.currentText())
        scatter_counts = Counter()
        for item in tuning_result.get("defects", []):
            if item.get("id") not in considered_ids:
                continue
            status = "Caught" if item.get("id") in detected_ids else "Lost"
            if partition_key:
                partition = item.get(partition_key) or ("Original" if partition_key == "combined_source_lot" else "-")
                status = f"{partition}: {status}"
            scatter_counts[status] += 1
        self.scatter_chart.set_counts(
            scatter_counts,
            "Scatter Chart - Caught and Lost Defects",
            "Side by Side" if partition_key else "Bar",
        )
        self._plot_options_changed()
        self.summary_table.setRowCount(0)
        self.test_evaluation = evaluate_sensitivity_tuning(
            tuning_result,
            test=self.test.currentText(),
            regions=[],
            polarity="Both",
            threshold=self.value.value(),
        )
        rows = [
            ("Current", data["detected"], data["considered"]),
            ("Test", self.test_evaluation["detected"], self.test_evaluation["considered"]),
        ]
        if self.review_result.get("combined_for_sensitivity_tuner"):
            original = [item for item in tuning_result.get("defects", []) if not item.get("combined_source_id")]
            imported = [item for item in tuning_result.get("defects", []) if item.get("combined_source_id")]
            rows.extend((("Original", len(original), len(tuning_result.get("defects", []))), ("Imported Source", len(imported), len(tuning_result.get("defects", [])))))
        for name, count, total in rows:
            row = self.summary_table.rowCount()
            self.summary_table.insertRow(row)
            percent = 0 if not total else round(count * 100 / total, 1)
            for column, value in enumerate((name, f"{count}/{total}", f"{percent}%")):
                self.summary_table.setItem(row, column, QTableWidgetItem(str(value)))

    def _effective_review_result(self):
        state = self.nef_states.get(self.test.currentText()) or {}
        classifiers = state.get("classifiers") or []
        enabled = self.test.currentText() in self.nef_enabled_tests and bool(classifiers)
        self.nef_filtered_ids = []
        if not enabled:
            return self.review_result
        tuning_result = deepcopy(self.review_result)
        kept = []
        keep_nuisance = bool(state.get("keep_nuisance_defects"))
        nuisance_nodes = int(state.get("nuisance_node_count", 0))
        divisor = max(2, 7 - min(4, nuisance_nodes))
        for defect in tuning_result.get("defects", []):
            identifier = defect.get("id", 0)
            try:
                numeric_id = int(identifier)
            except (TypeError, ValueError):
                numeric_id = sum(ord(character) for character in str(identifier))
            filtered = numeric_id % divisor == 0
            if filtered and not keep_nuisance:
                self.nef_filtered_ids.append(defect.get("id"))
            else:
                kept.append(defect)
        tuning_result["defects"] = kept
        return tuning_result

    def _plot_options_changed(self, *_args):
        if not hasattr(self, "tuner_chart") or not hasattr(self, "plot_scale"):
            return
        options = {
            "scale": self.plot_scale.currentText(),
            "grid": self.plot_grid.isChecked(),
            "legend": self.plot_legend.isChecked(),
            "group_size": self.group_size.value(),
            "zoom": self.plot_zoom.value() / 100.0,
        }
        self.tuner_chart.set_plot_options(**options)
        self.scatter_chart.set_plot_options(**options)

    def _modified(self, *_args):
        if self._loading_parameter:
            return
        key = self._selection_key()
        self.parameter_values[key] = self.value.value()
        self.edited_parameters.add(key)
        self.committed_parameters.discard(key)
        self.committed = False
        self.parameter_status.setText("Modified - uncommitted")
        self.parameter_status.setStyleSheet("background: #f1d85a; padding: 3px;")
        self._update()

    def _commit(self):
        key = self._selection_key()
        self.parameter_values[key] = self.value.value()
        self.edited_parameters.add(key)
        self.committed_parameters.add(key)
        self.committed = True
        self.parameter_status.setText("Modified - committed")
        self.parameter_status.setStyleSheet("background: #5fc56d; padding: 3px;")

    def _navigate(self, direction, uncommitted=False):
        count = self.parameter.count()
        if not count:
            return
        start = self.parameter.currentIndex()
        if not uncommitted:
            self.parameter.setCurrentIndex((start + direction) % count)
            return
        original = self.parameter.currentIndex()
        for step in range(1, count + 1):
            target = (start + direction * step) % count
            self.parameter.blockSignals(True)
            self.parameter.setCurrentIndex(target)
            key = self._selection_key()
            self.parameter.setCurrentIndex(original)
            self.parameter.blockSignals(False)
            if key in self.edited_parameters and key not in self.committed_parameters:
                self.parameter.setCurrentIndex(target)
                return

    def _switch_nef(self):
        test = self.test.currentText()
        dialog = STNEFTunerDialog(self.review_result, self.nef_states.get(test), self)
        if _exec(dialog) != QDialog.Accepted or dialog.result_state is None:
            return
        self.nef_states[test] = deepcopy(dialog.result_state)
        self.nef_enabled_tests.add(test)
        self.enable_nef.setChecked(True)
        self.parameter_status.setText(
            f"ST-NEF updated; {len(dialog.result_state.get('classifiers', []))} classifier(s) active."
        )
        self._update()

    def _toggle_nef(self, enabled):
        test = self.test.currentText()
        if enabled:
            self.nef_enabled_tests.add(test)
        else:
            self.nef_enabled_tests.discard(test)
        self._update()

    def _auto_tune_defect(self, catch):
        identifier = self.scatter_defect.currentData()
        defect = next(
            (item for item in self.review_result.get("defects", []) if item.get("id") == identifier),
            None,
        )
        if defect is None:
            return
        signal = float(defect.get("signal", 0.0))
        self.value.setValue(
            max(self.value.minimum(), signal - 0.001)
            if catch
            else min(self.value.maximum(), signal + 0.001)
        )
        self.parameter_status.setText(
            f"Auto-tuned to {'catch' if catch else 'lose'} defect {identifier}; review and Commit."
        )
        self.parameter_status.setStyleSheet("background: #f1d85a; padding: 3px;")

    def _select_regions(self):
        dialog = RegionSelectionDialog(self.available_regions, self.selected_regions, self)
        if _exec(dialog) == QDialog.Accepted:
            self.selected_regions = dialog.result_regions
            self._update()

    def _max_limits(self):
        minimums = {
            name: self._parameter_floor(name) for name in SensitivityMaxLimitsDialog.DEFAULTS
        }
        dialog = SensitivityMaxLimitsDialog(self.max_limits, self, minimums=minimums)
        if _exec(dialog) == QDialog.Accepted and dialog.result_limits:
            self.max_limits = dialog.result_limits
            self._load_parameter_value()
            self._update()

    def _advanced_parameters(self):
        dialog = AdvancedSensitivityParametersDialog(
            self.advanced_parameter_values,
            self.PARAMETERS,
            self,
        )
        if _exec(dialog) != QDialog.Accepted or dialog.result_parameters is None:
            return
        self.advanced_parameter_values = deepcopy(dialog.result_parameters)
        key = self._selection_key()
        self.parameter_values[key] = self._parameter_default()
        self._load_parameter_value()
        self._modified()

    def _finish(self):
        action = self.finish_action.currentText()
        if action == "Exit Without Saving":
            self.result_state = None
            self.accept()
            return
        restored = ""
        if action.startswith("Restore Session"):
            self.parameter_values = deepcopy(self.session_baseline.get("parameter_values") or {})
            self.edited_parameters = set(
                self.session_baseline.get("edited_parameters") or self.parameter_values.keys()
            )
            self.committed_parameters = set(self.session_baseline.get("committed_parameters") or [])
            self.max_limits = deepcopy(self.session_baseline.get("max_limits") or SensitivityMaxLimitsDialog.DEFAULTS)
            self.advanced_parameter_values = deepcopy(self.session_baseline.get("advanced_parameter_values") or {})
            if action.endswith("All"):
                self.nef_states = deepcopy(self.session_baseline.get("nef_states") or {})
                self.nef_enabled_tests = set(self.session_baseline.get("nef_enabled_tests") or [])
            restored = "Session Recipe"
        elif action.startswith("Restore Inspection"):
            self.parameter_values = {}
            self.edited_parameters = set()
            self.committed_parameters = set()
            self.state.pop("value", None)
            self.max_limits = deepcopy(SensitivityMaxLimitsDialog.DEFAULTS)
            self.advanced_parameter_values = {}
            if action.endswith("All"):
                self.nef_states = {}
                self.nef_enabled_tests = set()
                for test_state in (self.recipe or {}).get("tests", []):
                    name = test_state.get("name")
                    if name and test_state.get("nef"):
                        self.nef_states[name] = deepcopy(test_state["nef"])
                        if test_state.get("run_nef"):
                            self.nef_enabled_tests.add(name)
            restored = "Inspection Recipe"
        if restored:
            self.committed = False
            self._load_parameter_value()
            self._update()
        if action == "Save Recipe As..." and not all(
            edit.text().strip() for edit in (self.save_name, self.save_device, self.save_step)
        ):
            QMessageBox.warning(self, "Sensitivity Tuner", "Recipe Name, Device, and Layer are required.")
            return
        export_path = ""
        if action == "Export Recipe As...":
            export_path, _selected = QFileDialog.getSaveFileName(
                self, "Export Tuned Recipe", "_kt_visopt.json", "Recipe JSON (*.json)"
            )
            if not export_path:
                return
        self.result_state = {
            "test": self.test.currentText(),
            "regions": deepcopy(self.selected_regions),
            "polarity": self.polarity.currentText(),
            "algorithm": self.algorithm.currentText(),
            "path": self.path.currentText(),
            "channel": self.channel.currentText(),
            "parameter": self.parameter.currentText(),
            "value": self.value.value(),
            "committed": self.committed,
            "parameter_values": deepcopy(self.parameter_values),
            "edited_parameters": sorted(self.edited_parameters),
            "committed_parameters": sorted(self.committed_parameters),
            "advanced_parameter_values": deepcopy(self.advanced_parameter_values),
            "show_mode": self.show_mode.currentText(),
            "filter_scope": self.filter_scope.currentText(),
            "auto_sort": self.auto_sort.isChecked(),
            "dark_filter": self.dark_filter.currentText(),
            "partition": self.partition.currentText(),
            "group_size": self.group_size.value(),
            "plot_scale": self.plot_scale.currentText(),
            "plot_grid": self.plot_grid.isChecked(),
            "plot_legend": self.plot_legend.isChecked(),
            "plot_zoom": self.plot_zoom.value(),
            "nef_states": deepcopy(self.nef_states),
            "nef_enabled_tests": sorted(self.nef_enabled_tests),
            "nef_filtered_ids": list(self.nef_filtered_ids),
            "max_limits": deepcopy(self.max_limits),
            "finish_action": action,
            "recipe_identity": {
                "inspection": self.save_name.text().strip(),
                "device": self.save_device.text().strip(),
                "step": self.save_step.text().strip(),
            },
            "export_path": export_path,
            "evaluation": deepcopy(self.current_evaluation),
            "test_evaluation": deepcopy(self.test_evaluation),
            "restored_from": restored,
        }
        if export_path:
            payload = deepcopy(self.recipe or {})
            payload["sensitivity_tuner_updates"] = [deepcopy(self.result_state)]
            Path(export_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self.accept()


class SuperClassDialog(QDialog):
    NAMES = ["Killer", "Real", "Nuisance", "Disregard", "Unknown"]

    def __init__(self, result, parent=None):
        super().__init__(parent)
        self.review_result = result
        self.result_result = None
        self.setWindowTitle("Super Class")
        self.resize(560, 360)
        root = QVBoxLayout(self)
        root.addWidget(QLabel("Group manual class codes into the five general Super Classes."))
        form = QGridLayout()
        self.codes = {}
        scheme = result.get("super_class_scheme") or {}
        for row, name in enumerate(self.NAMES):
            edit = QLineEdit(", ".join(str(value) for value in scheme.get(name, [])))
            edit.setPlaceholderText("Manual class codes, comma separated")
            self.codes[name] = edit
            form.addWidget(QLabel(name), row, 0)
            form.addWidget(edit, row, 1)
        root.addLayout(form)
        buttons = QHBoxLayout()
        import_button = QPushButton("Import...")
        import_button.clicked.connect(self._import)
        export_button = QPushButton("Export...")
        export_button.clicked.connect(self._export)
        buttons.addWidget(import_button)
        buttons.addWidget(export_button)
        buttons.addStretch(1)
        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(apply_button)
        buttons.addWidget(cancel)
        root.addLayout(buttons)

    def _scheme(self):
        scheme = {}
        assigned = set()
        for name, edit in self.codes.items():
            values = []
            for token in edit.text().replace(";", ",").split(","):
                if not token.strip():
                    continue
                value = int(token.strip())
                if value in assigned:
                    raise ValueError(f"Manual class code {value} is assigned more than once")
                assigned.add(value)
                values.append(value)
            scheme[name] = values
        return scheme

    def _import(self):
        filename, _selected = QFileDialog.getOpenFileName(self, "Import Super Class Scheme", "", "JSON Files (*.json)")
        if not filename:
            return
        try:
            scheme = json.loads(Path(filename).read_text(encoding="utf-8"))
            if not isinstance(scheme, dict):
                raise ValueError("Scheme must be a JSON object")
            for name, edit in self.codes.items():
                edit.setText(", ".join(str(value) for value in scheme.get(name, [])))
        except (OSError, ValueError, TypeError) as exc:
            QMessageBox.warning(self, "Import Super Class Scheme", str(exc))

    def _export(self):
        try:
            scheme = self._scheme()
        except ValueError as exc:
            QMessageBox.warning(self, "Super Class", str(exc))
            return
        filename, _selected = QFileDialog.getSaveFileName(self, "Export Super Class Scheme", "SuperClass.json", "JSON Files (*.json)")
        if filename:
            Path(filename).write_text(json.dumps(scheme, indent=2), encoding="utf-8")

    def _finish(self):
        try:
            self.result_result = apply_super_class_scheme(self.review_result, self._scheme())
        except ValueError as exc:
            QMessageBox.warning(self, "Super Class", str(exc))
            return
        self.accept()


class DefectDisplayRulesDialog(QDialog):
    DEFAULTS = [
        {"rule": "Marked", "enabled": True, "state": True, "color": "#15a85d", "shape": "Circle"},
        {"rule": "Reviewed", "enabled": False, "state": True, "color": "#2d7487", "shape": "Square"},
        {"rule": "Repeater", "enabled": False, "state": True, "color": "#a55b45", "shape": "Diamond"},
        {"rule": "Clustered", "enabled": False, "state": True, "color": "#8a6d9b", "shape": "Square"},
        {"rule": "Dark", "enabled": False, "state": True, "color": "#303030", "shape": "Circle"},
    ]

    def __init__(self, rules=None, parent=None):
        super().__init__(parent)
        self.result_rules = None
        self.setWindowTitle("Defect Display Rules")
        self.resize(620, 360)
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Enabled", "Rule", "State", "Color", "Shape"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        for rule in deepcopy(rules or self.DEFAULTS):
            row = self.table.rowCount()
            self.table.insertRow(row)
            enabled = QTableWidgetItem()
            enabled.setFlags(enabled.flags() | Qt.ItemIsUserCheckable)
            enabled.setCheckState(Qt.Checked if rule.get("enabled") else Qt.Unchecked)
            self.table.setItem(row, 0, enabled)
            self.table.setItem(row, 1, QTableWidgetItem(rule.get("rule", "")))
            state = QComboBox()
            state.addItems(["True", "False"])
            state.setCurrentText("True" if rule.get("state", True) else "False")
            self.table.setCellWidget(row, 2, state)
            self.table.setItem(row, 3, QTableWidgetItem(rule.get("color", "#d62d2d")))
            shape = QComboBox()
            shape.addItems(["Circle", "Square", "Diamond"])
            shape.setCurrentText(rule.get("shape", "Circle"))
            self.table.setCellWidget(row, 4, shape)
        layout.addWidget(self.table)
        buttons = QHBoxLayout()
        reset = QPushButton("Restore Defaults")
        reset.clicked.connect(lambda: self._restore_defaults())
        buttons.addWidget(reset)
        buttons.addStretch(1)
        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(apply_button)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)

    def _restore_defaults(self):
        for row in range(self.table.rowCount()):
            default = self.DEFAULTS[row]
            self.table.item(row, 0).setCheckState(Qt.Checked if default["enabled"] else Qt.Unchecked)
            self.table.cellWidget(row, 2).setCurrentText("True")
            self.table.item(row, 3).setText(default["color"])
            self.table.cellWidget(row, 4).setCurrentText(default["shape"])

    def _finish(self):
        rules = []
        for row in range(self.table.rowCount()):
            color = self.table.item(row, 3).text().strip()
            if not color.startswith("#") or len(color) not in (4, 7):
                QMessageBox.warning(self, "Defect Display Rules", f"Invalid color: {color}")
                return
            rules.append({
                "enabled": self.table.item(row, 0).checkState() == Qt.Checked,
                "rule": self.table.item(row, 1).text(),
                "state": self.table.cellWidget(row, 2).currentText() == "True",
                "color": color,
                "shape": self.table.cellWidget(row, 4).currentText(),
            })
        self.result_rules = rules
        self.accept()


class GridColumnsDialog(QDialog):
    def __init__(self, selected, parent=None):
        super().__init__(parent)
        self.result_columns = None
        self.checks = {}
        self.setWindowTitle("Configure Defect Grid Columns")
        self.resize(560, 620)
        self.setMinimumSize(480, 480)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Select the attributes to display in the Defect Properties Grid."))
        selected = set(selected)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.StyledPanel)
        choices = QWidget()
        choices_layout = QGridLayout(choices)
        choices_layout.setContentsMargins(12, 10, 12, 10)
        choices_layout.setHorizontalSpacing(24)
        choices_layout.setVerticalSpacing(4)
        midpoint = (len(GRID_COLUMNS) + 1) // 2
        for index, (key, label) in enumerate(GRID_COLUMNS):
            check = QCheckBox(label)
            check.setChecked(key in selected)
            self.checks[key] = check
            column = 0 if index < midpoint else 1
            row = index if column == 0 else index - midpoint
            choices_layout.addWidget(check, row, column)
        choices_layout.setRowStretch(midpoint, 1)
        scroll.setWidget(choices)
        layout.addWidget(scroll, 1)
        buttons = QHBoxLayout()
        reset = QPushButton("Reset Columns")
        reset.clicked.connect(lambda: [check.setChecked(True) for check in self.checks.values()])
        buttons.addWidget(reset)
        buttons.addStretch(1)
        ok = QPushButton("OK")
        ok.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)

    def _finish(self):
        selected = [key for key, _label in GRID_COLUMNS if self.checks[key].isChecked()]
        if not selected:
            QMessageBox.warning(self, "Configure Defect Grid Columns", "Select at least one column.")
            return
        self.result_columns = selected
        self.accept()


class ReviewFilterAnalysisDialog(QDialog):
    FILTER_TABS = {
        "General Filter": 0,
        "Venn ID Filter": 1,
        "Sensitivity Filter": 2,
        "Class Code Filter": 3,
        "Channel Filter": 4,
        "Advanced Filtering": 5,
    }

    def __init__(self, result, state=None, parent=None):
        super().__init__(parent)
        self.review_result = result
        self.state = normalized_filter_analysis_state(state)
        self.result_state = None
        self.setWindowTitle("Filter and Analysis")
        self.resize(760, 610)
        root = QVBoxLayout(self)
        template_row = QHBoxLayout()
        template_row.addWidget(QLabel("Configuration"))
        self.template = QComboBox()
        self.template.addItems(["Default"] + sorted(self.state["templates"]))
        self.template.currentTextChanged.connect(self._load_template)
        self.template_name = QLineEdit()
        self.template_name.setPlaceholderText("Template name")
        save = QPushButton("Save")
        save.clicked.connect(self._save_template)
        delete = QPushButton("Delete")
        delete.clicked.connect(self._delete_template)
        template_row.addWidget(self.template, 1)
        template_row.addWidget(self.template_name, 1)
        template_row.addWidget(save)
        template_row.addWidget(delete)
        root.addLayout(template_row)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Enabled", "Operation", "Type"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table, 1)
        actions = QHBoxLayout()
        configure = QPushButton("Edit Properties...")
        configure.clicked.connect(self._configure)
        up = QPushButton("Move Up")
        up.clicked.connect(lambda: self._move(-1))
        down = QPushButton("Move Down")
        down.clicked.connect(lambda: self._move(1))
        actions.addWidget(configure)
        actions.addWidget(up)
        actions.addWidget(down)
        actions.addStretch(1)
        root.addLayout(actions)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        root.addWidget(self.summary)
        footer = QHBoxLayout()
        footer.addStretch(1)
        execute = QPushButton("Execute")
        execute.clicked.connect(self._finish)
        close = QPushButton("Cancel")
        close.clicked.connect(self.reject)
        footer.addWidget(execute)
        footer.addWidget(close)
        root.addLayout(footer)
        self._populate()
        self.table.itemChanged.connect(self._operation_changed)

    def _check_item(self, checked):
        item = QTableWidgetItem()
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
        return item

    def _populate(self, selected=0):
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        for operation in self.state["operations"]:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, self._check_item(operation["enabled"]))
            name = QTableWidgetItem(operation["name"])
            name.setFlags(name.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 1, name)
            kind = QTableWidgetItem(operation["type"])
            kind.setFlags(kind.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 2, kind)
        if self.table.rowCount():
            self.table.selectRow(max(0, min(selected, self.table.rowCount() - 1)))
        self.table.blockSignals(False)
        self._summary()

    def _sync_operations(self):
        self.state["operations"] = [
            {
                "enabled": self.table.item(row, 0).checkState() == Qt.Checked,
                "name": self.table.item(row, 1).text(),
                "type": self.table.item(row, 2).text(),
            }
            for row in range(self.table.rowCount())
        ]

    def _summary(self):
        enabled = [item["name"] for item in self.state["operations"] if item["enabled"]]
        self.summary.setText("Execution order: " + (" -> ".join(enabled) if enabled else "No operations enabled"))

    def _operation_changed(self, _item):
        self._sync_operations()
        self._summary()

    def _move(self, direction):
        self._sync_operations()
        row = self.table.currentRow()
        target = row + direction
        if row < 0 or target < 0 or target >= len(self.state["operations"]):
            return
        self.state["operations"][row], self.state["operations"][target] = self.state["operations"][target], self.state["operations"][row]
        self._populate(target)

    def _configure(self):
        row = self.table.currentRow()
        if row < 0:
            return
        name = self.table.item(row, 1).text()
        if name in self.FILTER_TABS:
            dialog = DefectFilterDialog(self.review_result, self.state["filters"], self)
            dialog.tabs.setCurrentIndex(self.FILTER_TABS[name])
            if _exec(dialog) == QDialog.Accepted and dialog.result_filters is not None:
                self.state["filters"] = deepcopy(dialog.result_filters)
        else:
            dialog = WaferPostProcessingDialog(
                self.state.get("analysis"),
                test_count=len(self.review_result.get("selected_tests", [])),
                parent=self,
            )
            if _exec(dialog) == QDialog.Accepted and dialog.result_state is not None:
                self.state["analysis"] = deepcopy(dialog.result_state)

    def _template_payload(self):
        self._sync_operations()
        return {
            "operations": deepcopy(self.state["operations"]),
            "filters": deepcopy(self.state["filters"]),
            "analysis": deepcopy(self.state.get("analysis")),
        }

    def _save_template(self):
        name = self.template_name.text().strip().replace(" ", "_")
        if not name:
            QMessageBox.warning(self, "Filter and Analysis", "Enter a template name.")
            return
        self.state["templates"][name] = self._template_payload()
        if self.template.findText(name) < 0:
            self.template.addItem(name)
        self.template.setCurrentText(name)

    def _load_template(self, name):
        if not name:
            return
        if name == "Default":
            templates = self.state["templates"]
            self.state = default_filter_analysis_state()
            self.state["templates"] = templates
        elif name in self.state["templates"]:
            templates = self.state["templates"]
            self.state = normalized_filter_analysis_state(self.state["templates"][name])
            self.state["templates"] = templates
        self._populate()

    def _delete_template(self):
        name = self.template.currentText()
        if name == "Default":
            return
        self.state["templates"].pop(name, None)
        self.template.removeItem(self.template.currentIndex())
        self.template.setCurrentText("Default")

    def _finish(self):
        self._sync_operations()
        self.result_state = normalized_filter_analysis_state(self.state)
        self.accept()


class DefectAnalysisToolboxDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.operation = None
        self.setWindowTitle("Defect Analysis Toolbox")
        self.setFixedSize(360, 220)
        layout = QVBoxLayout(self)
        title = QLabel("Defect Analysis Toolbox")
        title.setStyleSheet("font-weight: 700; font-size: 13px;")
        layout.addWidget(title)
        for label, operation in (
            ("Apply Binner", "Apply Binner"),
            ("Wafer Post Processing", "Wafer Post Processing"),
        ):
            button = QPushButton(label)
            button.setMinimumHeight(42)
            button.clicked.connect(lambda _checked=False, value=operation: self._select(value))
            layout.addWidget(button)
        layout.addStretch(1)
        close = QPushButton("Close")
        close.clicked.connect(self.reject)
        layout.addWidget(close)

    def _select(self, operation):
        self.operation = operation
        self.accept()


class ApplyBinnerDialog(QDialog):
    def __init__(self, result, visible_defects, selected_ids, current_recipe=None, parent=None):
        super().__init__(parent)
        self.result = deepcopy(result)
        self.visible_defects = deepcopy(visible_defects)
        self.selected_ids = set(selected_ids or [])
        self.current_recipe = current_recipe or {}
        self.result_result = None
        self.stats = None
        self.nef_state = {}
        self.ido_classifier = None
        self.setWindowTitle("Apply Binner")
        self.resize(620, 460)
        root = QVBoxLayout(self)
        notice = QLabel(
            "Apply Binner operates only on defects currently displayed on the Wafer Map. "
            "Use Filter / Sort to display all defects when full-wafer processing is required."
        )
        notice.setWordWrap(True)
        root.addWidget(notice)
        form = QGridLayout()
        form.addWidget(QLabel("Test"), 0, 0)
        self.test = QComboBox()
        names = list(result.get("selected_tests") or [])
        if not names:
            names = [item.get("name", f"Test {index + 1}") for index, item in enumerate(self.current_recipe.get("tests", []))]
        self.test.addItems(names or ["Test 1"])
        self.test.currentTextChanged.connect(self._load_test_settings)
        form.addWidget(self.test, 0, 1, 1, 2)
        self.enable_nef = QCheckBox("Enable NEF")
        form.addWidget(self.enable_nef, 1, 0)
        self.nef_label = QLabel("No classifier selected")
        form.addWidget(self.nef_label, 1, 1)
        nef_setup = QPushButton("Nuisance Setup Filter...")
        nef_setup.clicked.connect(self._configure_nef)
        form.addWidget(nef_setup, 1, 2)
        self.enable_ido = QCheckBox("Enable iDO")
        form.addWidget(self.enable_ido, 2, 0)
        self.ido_label = QLabel("No classifier selected")
        form.addWidget(self.ido_label, 2, 1)
        ido_setup = QPushButton("Select iDO Classifier...")
        ido_setup.clicked.connect(self._configure_ido)
        form.addWidget(ido_setup, 2, 2)
        root.addLayout(form)
        self.clear_codes = QCheckBox("Clear Codes on Wafer")
        self.use_selected = QCheckBox("Use Selected Defects")
        self.use_selected.setEnabled(bool(self.selected_ids))
        self.use_selected.setToolTip(
            "" if self.selected_ids else "Select defects on the Wafer Map before enabling this option."
        )
        root.addWidget(self.clear_codes)
        root.addWidget(self.use_selected)
        self.summary = QLabel("")
        self.summary.setWordWrap(True)
        root.addWidget(self.summary)
        root.addStretch(1)
        footer = QHBoxLayout()
        footer.addStretch(1)
        self.execute = QPushButton("Execute")
        self.execute.clicked.connect(self._execute)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        footer.addWidget(self.execute)
        footer.addWidget(cancel)
        root.addLayout(footer)
        has_vectors = bool(self.result.get("feature_vector_file"))
        self.execute.setEnabled(has_vectors)
        if not has_vectors:
            self.summary.setText("This result does not contain Feature Vector data. Apply Binner is unavailable.")
        self._load_test_settings(self.test.currentText())

    def _test_state(self):
        name = self.test.currentText()
        return next(
            (item for item in self.current_recipe.get("tests", []) if item.get("name") == name),
            {},
        )

    def _load_test_settings(self, _name):
        state = self._test_state()
        self.nef_state = deepcopy(state.get("nef") or {})
        self.ido_classifier = deepcopy(state.get("ido_classifier"))
        self.enable_nef.setChecked(bool(state.get("run_nef") and self.nef_state.get("classifiers")))
        self.enable_ido.setChecked(bool(state.get("run_ido") and self.ido_classifier))
        self._refresh_labels()

    def _refresh_labels(self):
        classifiers = self.nef_state.get("classifiers") or []
        self.nef_label.setText(
            " <<multiple>>" if len(classifiers) > 1 else (classifiers[0].get("name", "") if classifiers else "No classifier selected")
        )
        self.ido_label.setText(
            self.ido_classifier.get("name", "") if self.ido_classifier else "No classifier selected"
        )

    def _configure_nef(self):
        dialog = NuisanceFilterSetupDialog(self.nef_state, self)
        if _exec(dialog) == QDialog.Accepted and dialog.result_state is not None:
            self.nef_state = deepcopy(dialog.result_state)
            self.enable_nef.setChecked(bool(self.nef_state.get("classifiers")))
            self._refresh_labels()

    def _configure_ido(self):
        state = self._test_state()
        dialog = IdoClassifierDialog(
            self.ido_classifier,
            state.get("orientation", ""),
            state.get("feature_vector_version", "3.0A"),
            self,
        )
        if _exec(dialog) == QDialog.Accepted and dialog.result_classifier is not None:
            self.ido_classifier = deepcopy(dialog.result_classifier)
            self.enable_ido.setChecked(True)
            self._refresh_labels()

    def _execute(self):
        test_name = self.test.currentText()
        visible = [item for item in self.visible_defects if item.get("test") == test_name]
        try:
            self.result_result, self.stats = apply_binner(
                self.result,
                visible,
                nef_state=self.nef_state,
                ido_classifier=self.ido_classifier,
                enable_nef=self.enable_nef.isChecked(),
                enable_ido=self.enable_ido.isChecked(),
                clear_codes_on_wafer=self.clear_codes.isChecked(),
                use_selected_defects=self.use_selected.isChecked(),
                selected_ids=self.selected_ids,
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Apply Binner", str(exc))
            return
        self.accept()


class WaferDataTransferDialog(QDialog):
    def __init__(self, result, visible_defects, parent=None):
        super().__init__(parent)
        self.review_result = result
        self.visible_defects = list(visible_defects)
        self.result_options = None
        self.setWindowTitle("Select Data Transfer Options")
        self.resize(760, 280)
        self.setMinimumWidth(720)
        root = QVBoxLayout(self)
        heading = QLabel("Send Current Wafer")
        heading.setStyleSheet("font-size: 13px; font-weight: bold;")
        root.addWidget(heading)
        self.send_all = QRadioButton("Send All Defects on the Wafer")
        self.send_shown = QRadioButton("Send Only Shown Defects on the Wafer")
        self.send_all.setChecked(True)
        root.addWidget(self.send_all)
        self.include_duplicates = QCheckBox("Include Duplicates")
        self.include_duplicates.setToolTip(
            "Include defects marked as duplicates by Multi-Test Merge."
        )
        duplicate_row = QHBoxLayout()
        duplicate_row.addSpacing(24)
        duplicate_row.addWidget(self.include_duplicates)
        duplicate_row.addStretch(1)
        root.addLayout(duplicate_row)
        root.addWidget(self.send_shown)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setStyleSheet("background: #efefec; border: 1px solid #aaa69d; padding: 6px;")
        root.addWidget(self.summary)
        self.send_all.toggled.connect(self._refresh)
        self.send_shown.toggled.connect(self._refresh)
        self.include_duplicates.toggled.connect(self._refresh)
        footer = QHBoxLayout()
        footer.addStretch(1)
        send = QPushButton("Send")
        send.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        footer.addWidget(send)
        footer.addWidget(cancel)
        root.addLayout(footer)
        self._refresh()

    def _selection(self):
        scope = "All Defects" if self.send_all.isChecked() else "Shown Defects"
        return scope, select_wafer_transfer_defects(
            self.review_result,
            self.visible_defects,
            scope=scope,
            include_duplicates=self.include_duplicates.isChecked(),
        )

    def _refresh(self):
        self.include_duplicates.setEnabled(self.send_all.isChecked())
        scope, selected = self._selection()
        self.summary.setText(f"{len(selected)} defect(s) will be transferred from {scope.lower()}.")

    def _finish(self):
        scope, selected = self._selection()
        self.result_options = {
            "scope": scope,
            "include_duplicates": bool(
                self.send_all.isChecked() and self.include_duplicates.isChecked()
            ),
            "defect_ids": [item.get("id") for item in selected],
            "defect_count": len(selected),
        }
        self.accept()


class DBBClipGrabDialog(QDialog):
    def __init__(self, marked_count, existing_count=0, parent=None):
        super().__init__(parent)
        self.result_options = None
        self.setWindowTitle("Grab DBB Clips")
        self.resize(620, 280)
        root = QVBoxLayout(self)
        description = QLabel(
            f"Marked defects: {marked_count}    Existing DBB clips: {existing_count}\n"
            f"Up to {min(200, marked_count)} marked defect clip(s) will be saved to the lot result."
        )
        description.setWordWrap(True)
        root.addWidget(description)
        self.delete_existing = QCheckBox("Delete All Existing DBB Clips before saving new images")
        root.addWidget(self.delete_existing)
        root.addStretch(1)
        buttons = QHBoxLayout(); buttons.addStretch(1)
        save = QPushButton("Save"); save.clicked.connect(self._finish)
        cancel = QPushButton("Cancel"); cancel.clicked.connect(self.reject)
        buttons.addWidget(save); buttons.addWidget(cancel); root.addLayout(buttons)

    def _finish(self):
        self.result_options = {"delete_existing": self.delete_existing.isChecked()}
        self.accept()


class ReviewWorkspace(QDialog):
    def __init__(
        self,
        result,
        *,
        store=None,
        current_recipe=None,
        snapshot_mode=False,
        snapshot_update_callback=None,
        parent=None,
    ):
        super().__init__(parent)
        self.result = deepcopy(result)
        self.store = store
        self.current_recipe = current_recipe
        self.snapshot_mode = snapshot_mode
        self.snapshot_update_callback = snapshot_update_callback
        self.complete_data_controls = []
        self.machine_free_controls = []
        self.review_toolbar_widgets = []
        self.review_image_toolbar_widgets = []
        self.filters = default_filter_state()
        self.grid_columns = [key for key, _label in GRID_COLUMNS]
        self.visible_defects = []
        self.selected_id = None
        self.selected_ids = set()
        self.advanced_class_codes = None
        self.advanced_attribute_values = None
        self.review_optics_state = {
            "magnification_step": 0,
            "light_level": 50,
            "focus_offset": 0,
            "aperture": 50,
        }
        self._loading = False
        self.setWindowTitle("Snapshot Review" if snapshot_mode else "Inspection Review")
        self.resize(1320, 820)
        self.setMinimumSize(980, 650)
        self.setStyleSheet(
            "QDialog { background: #c9c6be; font-family: Arial; font-size: 10px; }"
            "QFrame#pane { background: #efefeb; border: 1px solid #706d66; }"
            "QPushButton { min-height: 25px; background: #e9e7df; border: 1px solid #706d66; padding: 2px 7px; }"
            "QHeaderView::section { background: #d7d4cc; border: 1px solid #8c8981; padding: 3px; }"
        )
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.workspace_scroll = QScrollArea()
        self.workspace_scroll.setWidgetResizable(True)
        self.workspace_scroll.setFrameShape(QFrame.NoFrame)
        self.workspace = QWidget()
        self.workspace.setMinimumSize(1280, 700)
        root = QVBoxLayout(self.workspace)
        root.setContentsMargins(5, 5, 5, 5)
        root.addLayout(self._toolbar())
        self.vertical_splitter = QSplitter(Qt.Vertical)
        self.top_splitter = QSplitter(Qt.Horizontal)
        self.map_pane = self._map_pane()
        self.gallery_pane = self._gallery_pane()
        self.top_splitter.addWidget(self.map_pane)
        self.top_splitter.addWidget(self.gallery_pane)
        self.top_splitter.setSizes([520, 760])
        self.bottom_splitter = QSplitter(Qt.Horizontal)
        self.grid_pane = self._grid_pane()
        self.chart_pane = self._chart_pane()
        self.bottom_splitter.addWidget(self.grid_pane)
        self.bottom_splitter.addWidget(self.chart_pane)
        self.bottom_splitter.setSizes([900, 380])
        self.vertical_splitter.addWidget(self.top_splitter)
        self.vertical_splitter.addWidget(self.bottom_splitter)
        self.vertical_splitter.setSizes([390, 350])
        root.addWidget(self.vertical_splitter, 1)
        self.status = QLabel()
        self.status.setStyleSheet("background: #dedbd3; border-top: 1px solid #777; padding: 4px;")
        root.addWidget(self.status)
        self.workspace_scroll.setWidget(self.workspace)
        outer.addWidget(self.workspace_scroll)
        self._refresh_snapshot_controls()
        self._refresh_defects()

    def open_manual_tool(self, tool_name: str):
        """Open a Review menu tool directly after the result selection step."""
        actions = {
            "adjust_defect_location": lambda: self._adjust_offset(False),
            "adjust_die_origin": lambda: self._adjust_offset(True),
            "optics_selector": self._optics_selector,
            "sensitivity_tuner": self._sensitivity_tuner,
        }
        action = actions.get(str(tool_name))
        if action is not None:
            action()

    def _toolbar(self):
        toolbar = QVBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(3)
        self.review_toolbar_layout = toolbar
        primary_widget = QWidget()
        primary = QHBoxLayout(primary_widget)
        primary.setContentsMargins(0, 0, 0, 0)
        primary.setSpacing(4)
        primary.addWidget(QLabel("Layout"))
        self.layout_mode = QComboBox()
        self.layout_mode.addItems(["Review", "Wide Grid", "Advanced Classify"])
        self.layout_mode.currentTextChanged.connect(self._set_layout)
        primary.addWidget(self.layout_mode)
        primary.addWidget(QLabel("Images"))
        self.image_filter = QComboBox()
        self.image_filter.addItems([
            "All Defects", "With Any Image", "With Patch Images", "With SEM Images",
            "With Manual Images", "Without Images",
        ])
        self.image_filter.currentTextChanged.connect(self._set_image_filter)
        primary.addWidget(self.image_filter)
        self.selection_mode = QComboBox()
        self.selection_mode.addItems([
            "Select Defect(s)", "Select Die(s)", "Select Reticle(s)",
            "Deselect Defect(s)", "Deselect Die(s)", "Deselect Reticle(s)",
        ])
        primary.addWidget(self.selection_mode)
        for label, callback in [
            ("Previous", lambda: self._navigate(-1)),
            ("Next", lambda: self._navigate(1)),
            ("Mark Defect", self._toggle_mark),
            ("Select Current", self._select_current),
            ("Classify...", self._classify),
        ]:
            button = QPushButton(label)
            button.clicked.connect(callback)
            primary.addWidget(button)
        primary.addStretch(1)
        toolbar.addWidget(primary_widget)
        self.review_toolbar_widgets.append(primary_widget)
        secondary_widget = QWidget()
        secondary = QHBoxLayout(secondary_widget)
        secondary.setContentsMargins(0, 0, 0, 0)
        secondary.setSpacing(4)
        for label, callback in [
            ("Filter In", self._filter_in),
            ("Filter Out", self._filter_out),
            ("Reset Filter", self._reset_filter),
            ("Filter and Analysis...", self._filter_analysis),
            ("Analysis Toolbox...", self._analysis),
            ("Super Class...", self._super_class),
            ("Results Utility...", self._results_utility),
        ]:
            button = QPushButton(label)
            button.clicked.connect(callback)
            if label in ("Analysis Toolbox...", "Results Utility..."):
                self.complete_data_controls.append(button)
                button.setToolTip("Unavailable until complete wafer data and post-processing are available.")
            secondary.addWidget(button)
        self.review_toolbar_widgets.append(secondary_widget)
        selection_widget = QWidget()
        selection_tools = QHBoxLayout(selection_widget)
        selection_tools.setContentsMargins(0, 0, 0, 0)
        selection_tools.setSpacing(4)
        for label, callback in (
            ("Clear Selection", self._clear_selection),
            ("Mark Selected", lambda: self._mark_selected(True)),
            ("Clear Selected Marks", lambda: self._mark_selected(False)),
            ("Sample Marked", self._sample_marked),
            ("Clear All Marks", self._clear_all_marks),
        ):
            button = QPushButton(label)
            button.clicked.connect(callback)
            if label == "Sample Marked":
                self.complete_data_controls.append(button)
                button.setToolTip("Sampling is unavailable until wafer processing is complete.")
            selection_tools.addWidget(button)
        self.review_toolbar_widgets.append(selection_widget)
        analysis_row_widget = QWidget()
        analysis_row = QHBoxLayout(analysis_row_widget)
        analysis_row.setContentsMargins(0, 0, 0, 0)
        analysis_row.setSpacing(8)
        analysis_row.addWidget(secondary_widget)
        analysis_row.addWidget(selection_widget)
        analysis_row.addStretch(1)
        toolbar.addWidget(analysis_row_widget)
        transfer_widget = QWidget()
        transfer_tools = QHBoxLayout(transfer_widget)
        transfer_tools.setContentsMargins(0, 0, 0, 0)
        transfer_tools.setSpacing(4)
        for label, callback in [
            ("Send Lot Images", self._send_images),
            ("Send Current Wafer", self._send_wafer),
            ("Send Lot Results", self._send_lot),
            ("Export KLARF...", self._export),
        ]:
            button = QPushButton(label)
            button.clicked.connect(callback)
            if label in ("Send Lot Images", "Send Current Wafer", "Send Lot Results"):
                self.complete_data_controls.append(button)
                button.setToolTip("Unavailable until complete wafer data and post-processing are available.")
            transfer_tools.addWidget(button)
        self.update_snapshot = QPushButton("Update Snapshot")
        self.update_snapshot.clicked.connect(self._update_snapshot)
        transfer_tools.addWidget(self.update_snapshot)
        close = QPushButton("Close Review")
        close.clicked.connect(self.accept)
        transfer_tools.addWidget(close)
        self.review_image_toolbar_widgets.append(transfer_widget)
        review_widget = QWidget()
        review_tools = QHBoxLayout(review_widget)
        review_tools.setContentsMargins(0, 0, 0, 0)
        review_tools.setSpacing(4)
        for label, callback in (
            ("Adjust Defect Location...", lambda: self._adjust_offset(False)),
            ("Adjust Die Origin...", lambda: self._adjust_offset(True)),
            ("Optics Selector...", self._optics_selector),
        ):
            button = QPushButton(label)
            button.clicked.connect(callback)
            self.machine_free_controls.append(button)
            button.setToolTip("Requires a loaded or inspected wafer selection.")
            review_tools.addWidget(button)
        sensitivity = QPushButton("Sensitivity Tuner...")
        sensitivity.clicked.connect(self._sensitivity_tuner)
        sensitivity.setEnabled(bool(self.result.get("sensitivity_data")))
        sensitivity.setToolTip("Available for tests with collected Sensitivity Tuner data.")
        review_tools.addWidget(sensitivity)
        combine_st = QPushButton("Combine Results for ST...")
        combine_st.clicked.connect(self._combine_sensitivity_results)
        combine_st.setEnabled(bool(self.result.get("sensitivity_data")) and self.store is not None)
        combine_st.setToolTip("Combine compatible results that contain Sensitivity Tuner data.")
        review_tools.addWidget(combine_st)
        self.review_toolbar_widgets.append(review_widget)
        operations_row_widget = QWidget()
        operations_row = QHBoxLayout(operations_row_widget)
        operations_row.setContentsMargins(0, 0, 0, 0)
        operations_row.setSpacing(8)
        operations_row.addWidget(transfer_widget)
        operations_row.addWidget(review_widget)
        operations_row.addStretch(1)
        toolbar.addWidget(operations_row_widget)
        return toolbar

    def set_review_toolbar_visible(self, visible):
        for widget in self.review_toolbar_widgets:
            widget.setVisible(bool(visible))

    def set_review_image_toolbar_visible(self, visible):
        for widget in self.review_image_toolbar_widgets:
            widget.setVisible(bool(visible))

    def _set_layout(self, mode):
        if not hasattr(self, "vertical_splitter"):
            return
        layouts = {
            "Review": ([390, 350], [520, 760], [900, 380]),
            "Wide Grid": ([230, 560], [500, 780], [1120, 200]),
            "Advanced Classify": ([500, 290], [360, 920], [820, 460]),
        }
        vertical, top, bottom = layouts.get(mode, layouts["Review"])
        self.vertical_splitter.setSizes(vertical)
        self.top_splitter.setSizes(top)
        self.bottom_splitter.setSizes(bottom)
        if hasattr(self, "advanced_frame"):
            self.advanced_frame.setVisible(mode == "Advanced Classify")
            self._refresh_advanced_classify()
        if hasattr(self, "grid"):
            self._refresh_defects(self.selected_id)

    @staticmethod
    def _pane(title):
        frame = QFrame()
        frame.setObjectName("pane")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(6, 5, 6, 6)
        heading = QLabel(title)
        heading.setStyleSheet("font-weight: bold; text-decoration: underline;")
        layout.addWidget(heading)
        return frame, layout

    def _map_pane(self):
        frame, layout = self._pane("Wafer Map")
        self.map_tabs = QTabWidget()
        layout.addWidget(self.map_tabs, 1)
        wafer_page = QWidget()
        wafer_layout = QVBoxLayout(wafer_page)
        wafer_layout.setContentsMargins(0, 0, 0, 0)
        controls = QHBoxLayout()
        controls.addWidget(QLabel("Zoom"))
        self.map_zoom = QComboBox()
        self.map_zoom.addItems(["50%", "75%", "100%", "150%", "200%", "300%"])
        self.map_zoom.setCurrentText("100%")
        self.map_zoom.currentTextChanged.connect(
            lambda text: self.wafer_map.set_zoom(float(text.rstrip("%")) / 100.0)
        )
        controls.addWidget(self.map_zoom)
        fit = QPushButton("Fit")
        fit.setToolTip("Fit the full wafer map in the current pane")
        fit.clicked.connect(lambda: self.map_zoom.setCurrentText("100%"))
        controls.addWidget(fit)
        rules = QPushButton("Rules...")
        rules.setToolTip("Configure defect display rules")
        rules.clicked.connect(self._display_rules)
        controls.addWidget(rules)
        self.show_die = QCheckBox("Die")
        self.show_die.setChecked(True)
        self.show_defects = QCheckBox("Defects")
        self.show_defects.setChecked(True)
        self.show_counts = QCheckBox("Counts")
        self.show_counts.setToolTip("Show the defect count for each die")
        for check in (self.show_die, self.show_defects, self.show_counts):
            check.toggled.connect(self._map_options_changed)
            controls.addWidget(check)
        controls.addStretch(1)
        wafer_layout.addLayout(controls)
        self.wafer_map = WaferDefectMap()
        self.wafer_map.set_display_rules(self.result.get("defect_display_rules"))
        self.wafer_map.on_selected = self._select_id
        self.wafer_map.on_select_toggle = self._toggle_selected_id
        self.wafer_map.on_area_selected = self._select_area
        self.wafer_map.setContextMenuPolicy(Qt.CustomContextMenu)
        self.wafer_map.customContextMenuRequested.connect(self._map_context_menu)
        wafer_layout.addWidget(self.wafer_map, 1)
        self.map_info = QLabel()
        wafer_layout.addWidget(self.map_info)
        self.map_tabs.addTab(wafer_page, "Wafer Map")

        design_page = QWidget()
        design_layout = QVBoxLayout(design_page)
        design_layout.setContentsMargins(6, 6, 6, 6)
        execution = self.result.get("dbb_execution") or {}
        self.design_summary = QLabel(
            f"RDF: {execution.get('rdf_file', '-')}    Layer: {execution.get('inspection_layer', '-')}    "
            f"Processed: {execution.get('processed', 0)}    Sampled: {execution.get('sampled', 0)}    "
            f"Clips: {execution.get('clips', 0)}"
        )
        self.design_summary.setWordWrap(True)
        design_layout.addWidget(self.design_summary)
        self.design_details = QLabel("Select a defect to view its design coordinates and DBB attributes.")
        self.design_details.setWordWrap(True)
        self.design_details.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.design_details.setStyleSheet("background: #f4f4f1; border: 1px solid #aaa79f; padding: 8px;")
        design_scroll = QScrollArea()
        design_scroll.setWidgetResizable(True)
        design_scroll.setWidget(self.design_details)
        design_layout.addWidget(design_scroll, 1)
        design_index = self.map_tabs.addTab(design_page, "Design")
        self.map_tabs.setTabEnabled(design_index, bool(execution.get("enabled")))
        return frame

    def _map_options_changed(self, *_args):
        self.wafer_map.show_die = self.show_die.isChecked()
        self.wafer_map.show_defects = self.show_defects.isChecked()
        self.wafer_map.show_counts = self.show_counts.isChecked()
        self.wafer_map.update()

    def _display_rules(self):
        dialog = DefectDisplayRulesDialog(self.result.get("defect_display_rules"), self)
        if _exec(dialog) == QDialog.Accepted and dialog.result_rules is not None:
            self.result["defect_display_rules"] = deepcopy(dialog.result_rules)
            self.wafer_map.set_display_rules(dialog.result_rules)
            self._save_result()

    def _save_wafer_map(self):
        filename, _selected = QFileDialog.getSaveFileName(
            self, "Save Wafer Map", "wafer-map.png", "Images (*.png *.jpg *.bmp)"
        )
        if filename and not self.wafer_map.grab().save(filename):
            QMessageBox.warning(self, "Save Wafer Map", "The wafer map image could not be saved.")

    def _copy_wafer_map(self):
        QApplication.clipboard().setPixmap(self.wafer_map.grab())

    def _gallery_pane(self):
        frame, layout = self._pane("Image Gallery")
        self.advanced_frame = QFrame()
        advanced = QHBoxLayout(self.advanced_frame)
        advanced.setContentsMargins(0, 0, 0, 4)
        class_side = QVBoxLayout()
        class_row = QHBoxLayout()
        class_row.addWidget(QLabel("Manual Folder List"))
        new_class = QPushButton("New Class...")
        new_class.clicked.connect(self._classify)
        class_row.addWidget(new_class)
        class_side.addLayout(class_row)
        self.class_folders = QTableWidget(0, 3)
        self.class_folders.setHorizontalHeaderLabels(["Show", "Class Code", "Count"])
        self.class_folders.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.class_folders.verticalHeader().setVisible(False)
        self.class_folders.setContextMenuPolicy(Qt.CustomContextMenu)
        self.class_folders.customContextMenuRequested.connect(self._advanced_context_menu)
        self.class_folders.itemChanged.connect(self._advanced_filter_changed)
        class_side.addWidget(self.class_folders)
        advanced.addLayout(class_side, 1)
        attribute_side = QVBoxLayout()
        attribute_row = QHBoxLayout()
        attribute_row.addWidget(QLabel("Attribute Folder List"))
        self.advanced_attribute = QComboBox()
        self.advanced_attribute.addItems([
            "Polarity", "Channel", "Test", "Roughbin", "Region", "CAG Code",
            "Macro Sig Class", "Macro Sig ID", "Micro Sig Class", "Super Class",
            "DBB Global Bin", "DBC Bin", "DBG Group", "DBB Manual Bin",
        ])
        self.advanced_attribute.currentTextChanged.connect(self._advanced_attribute_changed)
        attribute_row.addWidget(self.advanced_attribute)
        attribute_side.addLayout(attribute_row)
        self.attribute_folders = QTableWidget(0, 3)
        self.attribute_folders.setHorizontalHeaderLabels(["Show", "Attribute", "Count"])
        self.attribute_folders.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.attribute_folders.verticalHeader().setVisible(False)
        self.attribute_folders.itemChanged.connect(self._advanced_filter_changed)
        attribute_side.addWidget(self.attribute_folders)
        self.attribute_tabs = QTabWidget()
        self.attribute_tabs.setMaximumHeight(42)
        polarity_page = QWidget()
        polarity_page.setObjectName("attribute_Polarity")
        self.attribute_tabs.addTab(polarity_page, "Polarity")
        attribute_side.addWidget(self.attribute_tabs)
        advanced.addLayout(attribute_side, 1)
        layout.addWidget(self.advanced_frame)
        self.advanced_frame.setVisible(False)
        controls = QHBoxLayout()
        controls.addWidget(QLabel("Show Defect"))
        self.gallery_scope = QComboBox()
        self.gallery_scope.addItems([
            "All Defects", "All Selected Defects", "All Marked Defects",
            "Current Defect Only", "All Location Images", "Stacked Defects",
        ])
        self.gallery_scope.setCurrentText("Current Defect Only")
        self.gallery_scope.currentTextChanged.connect(self._gallery_scope_changed)
        controls.addWidget(self.gallery_scope)
        controls.addWidget(QLabel("Image Type"))
        self.gallery_mode = QComboBox()
        gallery_modes = ["All Images", "Reference Image", "Patch Image", "Difference Image"]
        if (self.result.get("dbb_execution") or {}).get("enabled"):
            gallery_modes.append("DBB RDF Clip")
        self.gallery_mode.addItems(gallery_modes)
        self.gallery_mode.currentTextChanged.connect(self._gallery_mode_changed)
        controls.addWidget(self.gallery_mode)
        controls.addWidget(QLabel("Zoom"))
        self.gallery_zoom = QComboBox()
        self.gallery_zoom.addItems(["100%", "150%", "200%"])
        self.gallery_zoom.currentTextChanged.connect(self._gallery_zoom_changed)
        controls.addWidget(self.gallery_zoom)
        controls.addStretch(1)
        layout.addLayout(controls)
        acquisition = QHBoxLayout()
        self.grab_image = QPushButton("Grab Image")
        self.grab_image.clicked.connect(self._grab_image)
        self.machine_free_controls.append(self.grab_image)
        acquisition.addWidget(self.grab_image)
        self.grab_dbb_clips = QPushButton("Grab DBB Clips...")
        self.grab_dbb_clips.clicked.connect(self._grab_dbb_clips)
        acquisition.addWidget(self.grab_dbb_clips)
        self.freeze_gallery = QCheckBox("Freeze")
        self.freeze_gallery.setToolTip("Freeze image movement to enable ROI and histogram export.")
        acquisition.addWidget(self.freeze_gallery)
        acquisition.addStretch(1)
        layout.addLayout(acquisition)
        images = QHBoxLayout()
        self.image_widgets = [
            DefectImageWidget("Reference Image"),
            DefectImageWidget("Patch Image"),
            DefectImageWidget("Difference Image"),
        ]
        if (self.result.get("dbb_execution") or {}).get("enabled"):
            self.image_widgets.append(DefectImageWidget("DBB RDF Clip"))
        for widget in self.image_widgets:
            widget.setContextMenuPolicy(Qt.CustomContextMenu)
            widget.customContextMenuRequested.connect(
                lambda position, current=widget: self._image_context_menu(current, position)
            )
            images.addWidget(widget, 1)
        layout.addLayout(images, 1)
        self.defect_details = QLabel("Select a defect to display images.")
        self.defect_details.setWordWrap(True)
        layout.addWidget(self.defect_details)
        return frame

    def _gallery_mode_changed(self, mode):
        if not hasattr(self, "image_widgets"):
            return
        for widget in self.image_widgets:
            widget.setVisible(mode == "All Images" or widget.title == mode)

    def _gallery_scope_changed(self, mode):
        if mode == "All Selected Defects":
            candidates = [item for item in self.visible_defects if item.get("id") in self.selected_ids]
        elif mode == "All Marked Defects":
            candidates = [item for item in self.visible_defects if item.get("marked")]
        else:
            candidates = self.visible_defects
        if candidates and mode != "Current Defect Only":
            self._select_id(candidates[0].get("id"))
        if hasattr(self, "status"):
            self.status.setText(f"Image Gallery scope: {mode}; {len(candidates)} matching defect(s)")

    def _image_context_menu(self, widget, position):
        menu = QMenu(self)
        image_mode = menu.addMenu("Image Mode")
        for name in [item.title for item in self.image_widgets]:
            image_mode.addAction(name, lambda _checked=False, value=name: self.gallery_mode.setCurrentText(value))
        menu.addAction("View", lambda: self.gallery_zoom.setCurrentText("200%"))
        menu.addAction("Export Images...", self._export_gallery)
        roi = menu.addAction("Export ROI...", lambda: self._export_gallery("roi"))
        histogram = menu.addAction("Export Histogram...", self._export_histogram)
        roi.setEnabled(self.freeze_gallery.isChecked())
        histogram.setEnabled(self.freeze_gallery.isChecked())
        menu.exec(widget.mapToGlobal(position)) if hasattr(menu, "exec") else menu.exec_(widget.mapToGlobal(position))

    def _export_gallery(self, suffix="images"):
        filename, _selected = QFileDialog.getSaveFileName(
            self, "Export Images", f"review-{suffix}.png", "Images (*.png *.jpg *.tif)"
        )
        if filename and not self.gallery_pane.grab().save(filename):
            QMessageBox.warning(self, "Export Images", "The gallery image could not be saved.")

    def _export_histogram(self):
        defect = next((item for item in self.visible_defects if item.get("id") == self.selected_id), None)
        if defect is None:
            return
        filename, _selected = QFileDialog.getSaveFileName(
            self, "Export Histogram", "review-histogram.csv", "CSV Files (*.csv)"
        )
        if filename:
            Path(filename).write_text(
                "Attribute,Value\nSignal,{signal}\nSize,{size_um}\nClass Code,{class_code}\n".format(**defect),
                encoding="utf-8",
            )

    def _gallery_zoom_changed(self, text):
        if not hasattr(self, "image_widgets"):
            return
        zoom = float(text.rstrip("%")) / 100.0
        for widget in self.image_widgets:
            widget.set_zoom(zoom)

    @staticmethod
    def _checkable_item(checked):
        item = QTableWidgetItem()
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
        return item

    def _advanced_key(self):
        return {
            "Polarity": "polarity",
            "Channel": "channel",
            "Test": "test",
            "Roughbin": "roughbin",
            "Region": "region_id",
            "CAG Code": "cag_code",
            "Macro Sig Class": "macro_sig_class",
            "Macro Sig ID": "macro_sig_id",
            "Micro Sig Class": "micro_sig_class",
            "Super Class": "super_class",
            "DBB Global Bin": "dbb_global_bin",
            "DBC Bin": "dbc_bin",
            "DBG Group": "dbg_group",
            "DBB Manual Bin": "dbb_manual_bin",
        }[self.advanced_attribute.currentText()]

    def _refresh_advanced_classify(self):
        if not hasattr(self, "class_folders"):
            return
        source = filter_defects(self.result, self.filters)
        class_counts = Counter(int(item.get("class_code", 0)) for item in source)
        self.class_folders.blockSignals(True)
        self.class_folders.setRowCount(0)
        for code, count in sorted(class_counts.items()):
            row = self.class_folders.rowCount()
            self.class_folders.insertRow(row)
            checked = self.advanced_class_codes is None or code in self.advanced_class_codes
            self.class_folders.setItem(row, 0, self._checkable_item(checked))
            self.class_folders.setItem(row, 1, QTableWidgetItem(str(code)))
            self.class_folders.setItem(row, 2, QTableWidgetItem(str(count)))
        self.class_folders.blockSignals(False)
        class_source = source
        if self.advanced_class_codes is not None:
            class_source = [item for item in source if int(item.get("class_code", 0)) in self.advanced_class_codes]
        key = self._advanced_key()
        attribute_counts = Counter(str(item.get(key, "")) for item in class_source)
        self.attribute_folders.blockSignals(True)
        self.attribute_folders.setRowCount(0)
        for value, count in sorted(attribute_counts.items()):
            row = self.attribute_folders.rowCount()
            self.attribute_folders.insertRow(row)
            checked = self.advanced_attribute_values is None or value in self.advanced_attribute_values
            self.attribute_folders.setItem(row, 0, self._checkable_item(checked))
            self.attribute_folders.setItem(row, 1, QTableWidgetItem(value))
            self.attribute_folders.setItem(row, 2, QTableWidgetItem(str(count)))
        self.attribute_folders.blockSignals(False)

    def _advanced_attribute_changed(self, name):
        self.advanced_attribute_values = None
        if self.attribute_tabs.findChild(QWidget, f"attribute_{name}") is None:
            page = QWidget()
            page.setObjectName(f"attribute_{name}")
            self.attribute_tabs.addTab(page, name)
        self._refresh_advanced_classify()
        self._refresh_defects(self.selected_id)

    def _advanced_filter_changed(self, _item):
        codes = {
            int(self.class_folders.item(row, 1).text())
            for row in range(self.class_folders.rowCount())
            if self.class_folders.item(row, 0).checkState() == Qt.Checked
        }
        self.advanced_class_codes = None if len(codes) == self.class_folders.rowCount() else codes
        values = {
            self.attribute_folders.item(row, 1).text()
            for row in range(self.attribute_folders.rowCount())
            if self.attribute_folders.item(row, 0).checkState() == Qt.Checked
        }
        self.advanced_attribute_values = None if len(values) == self.attribute_folders.rowCount() else values
        self._refresh_defects(self.selected_id)

    def _set_folder_checks(self, table, checked):
        table.blockSignals(True)
        for row in range(table.rowCount()):
            table.item(row, 0).setCheckState(Qt.Checked if checked else Qt.Unchecked)
        table.blockSignals(False)
        self._advanced_filter_changed(None)

    def _advanced_context_menu(self, position):
        menu = QMenu(self)
        menu.addAction("Select All", lambda: self.class_folders.selectAll())
        menu.addAction("Deselect All", lambda: self.class_folders.clearSelection())
        menu.addSeparator()
        menu.addAction("Check All", lambda: self._set_folder_checks(self.class_folders, True))
        menu.addAction("Uncheck All", lambda: self._set_folder_checks(self.class_folders, False))
        image_types = menu.addMenu("Image Types")
        for name in ("Reference Image", "Patch Image", "Difference Image"):
            image_types.addAction(name, lambda _checked=False, value=name: self.gallery_mode.setCurrentText(value))
        menu.exec(self.class_folders.viewport().mapToGlobal(position)) if hasattr(menu, "exec") else menu.exec_(self.class_folders.viewport().mapToGlobal(position))

    def _select_all_visible(self):
        self.selected_ids = {item.get("id") for item in self.visible_defects}
        self.wafer_map.set_selected_ids(self.selected_ids)
        self.grid.selectAll()

    def _clear_selection(self):
        self.selected_ids.clear()
        self.wafer_map.set_selected_ids(self.selected_ids)
        self.grid.clearSelection()

    def _mark_selected(self, marked):
        targets = self.selected_ids or ({self.selected_id} if self.selected_id is not None else set())
        for defect in self.result.get("defects", []):
            if defect.get("id") in targets:
                defect["marked"] = marked
        self._save_result()
        self._refresh_defects(self.selected_id)

    def _clear_all_marks(self):
        for defect in self.result.get("defects", []):
            defect["marked"] = False
        self._save_result()
        self._refresh_defects(self.selected_id)

    def _sample_marked(self):
        marked = [
            defect
            for defect in self.result.get("defects", [])
            if defect.get("marked")
        ]
        if not marked:
            QMessageBox.information(
                self,
                "Sample Marked",
                "Mark at least one defect before applying review sampling.",
            )
            return
        for defect in marked:
            defect["sampled_review"] = True
        self.result.setdefault("review_log", []).append(
            f"Sample Marked applied to {len(marked)} defect(s)"
        )
        self._save_result()
        self._refresh_defects(self.selected_id)

    def _grid_context_menu(self, position):
        menu = QMenu(self)
        menu.addAction("Select All Defects", self._select_all_visible)
        menu.addAction("Remove Selection", self._clear_selection)
        menu.addAction("Mark Selected Defects", lambda: self._mark_selected(True))
        menu.addAction("Clear Marks For Selected Defects", lambda: self._mark_selected(False))
        menu.addAction("Classify Selected...", self._classify)
        menu.addSeparator()
        menu.addAction("Filter In", self._filter_in)
        menu.addAction("Filter Out", self._filter_out)
        menu.addAction("Reset Filter", self._reset_filter)
        menu.addSeparator()
        menu.addAction("Show All Columns", self._show_all_grid_columns)
        column = self.grid.columnAt(position.x())
        if 0 <= column < len(self.grid_columns):
            menu.addAction("Hide Column", lambda: self._hide_grid_column(column))
        menu.exec(self.grid.viewport().mapToGlobal(position)) if hasattr(menu, "exec") else menu.exec_(self.grid.viewport().mapToGlobal(position))

    def _map_context_menu(self, position):
        menu = QMenu(self)
        menu.addAction("Select Current Defect", self._select_current)
        menu.addAction("Mark Selected Defects", lambda: self._mark_selected(True))
        menu.addAction("Clear Marks For Selected Defects", lambda: self._mark_selected(False))
        menu.addSeparator()
        menu.addAction("Filter In", self._filter_in)
        menu.addAction("Filter Out", self._filter_out)
        menu.addAction("Reset Filter", self._reset_filter)
        menu.addAction("Open Analysis Toolbox", self._analysis)
        menu.addSeparator()
        menu.addAction("Save Wafer Map...", self._save_wafer_map)
        menu.addAction("Copy Wafer Map", self._copy_wafer_map)
        display = menu.addMenu("Display Options")
        for label, check in (("Show Die", self.show_die), ("Show Defect", self.show_defects), ("Show Defect Count", self.show_counts)):
            action = display.addAction(label)
            action.setCheckable(True)
            action.setChecked(check.isChecked())
            action.toggled.connect(check.setChecked)
        menu.exec(self.wafer_map.mapToGlobal(position)) if hasattr(menu, "exec") else menu.exec_(self.wafer_map.mapToGlobal(position))

    def _show_all_grid_columns(self):
        self.grid_columns = [key for key, _label in GRID_COLUMNS]
        self._apply_grid_headers()
        self._refresh_defects(self.selected_id)

    def _hide_grid_column(self, column):
        if len(self.grid_columns) <= 1:
            return
        self.grid_columns.pop(column)
        self._apply_grid_headers()
        self._refresh_defects(self.selected_id)

    def _grab_image(self):
        dialog = ReviewImageGrabDialog(
            self.result.get("selected_tests", []),
            self.result.get("image_grab_settings"),
            self,
        )
        if _exec(dialog) != QDialog.Accepted or dialog.result_settings is None:
            return
        settings = dialog.result_settings
        self.result["image_grab_settings"] = deepcopy(settings)
        marked = [item for item in self.result.get("defects", []) if item.get("marked")]
        targets = marked or [item for item in self.result.get("defects", []) if item.get("id") in self.selected_ids]
        if not targets:
            targets = [item for item in self.result.get("defects", []) if item.get("id") == self.selected_id]
        simulated = settings["image_optics"] == "Simulated Test Run"
        if simulated:
            self.result.setdefault("simulated_test_images", []).append({
                "test": settings["test"],
                "channels": [1, 2, 3],
                "images_per_channel": 3,
            })
        else:
            for defect in targets:
                defect["has_manual_image"] = True
                defect["manual_image_settings"] = deepcopy(settings)
        if settings["clear_marks"] and not simulated:
            for defect in self.result.get("defects", []):
                defect["marked"] = False
        self.result.setdefault("review_log", []).append(
            f"Image Grab using {settings['image_optics']} for {len(targets)} marked/selected location(s)"
        )
        self._save_result()
        self._refresh_defects(self.selected_id)
        self.status.setText(
            "Simulated test and reference images acquired"
            if simulated else f"Grabbed manual image(s) for {len(targets)} defect(s)"
        )

    def _set_image_filter(self, mode):
        self.filters["image_filter"] = mode
        self._refresh_defects(self.selected_id)

    def _grid_pane(self):
        frame, layout = self._pane("Defect Properties Grid")
        configuration = QHBoxLayout()
        configuration.addWidget(QLabel("Configuration"))
        self.grid_configuration = QComboBox()
        self.grid_configuration.setEditable(True)
        self.grid_configuration.addItems(["Default"] + sorted((self.result.get("review_grid_configs") or {}).keys()))
        self.grid_configuration.currentTextChanged.connect(self._load_grid_configuration)
        configuration.addWidget(self.grid_configuration, 1)
        layout.addLayout(configuration)
        tools = QHBoxLayout()
        save = QPushButton("Save")
        save.clicked.connect(self._save_grid_configuration)
        delete = QPushButton("Delete")
        delete.clicked.connect(self._delete_grid_configuration)
        make_default = QPushButton("Set Default")
        make_default.clicked.connect(self._set_default_grid_configuration)
        tools.addWidget(save)
        tools.addWidget(delete)
        tools.addWidget(make_default)
        configure = QPushButton("Configure Columns...")
        configure.clicked.connect(self._configure_grid_columns)
        tools.addWidget(configure)
        tools.addStretch(1)
        layout.addLayout(tools)
        self.grid = QTableWidget(0, len(self.grid_columns))
        self.grid.setSelectionMode(QAbstractItemView.MultiSelection)
        self.grid.setContextMenuPolicy(Qt.CustomContextMenu)
        self.grid.customContextMenuRequested.connect(self._grid_context_menu)
        self._apply_grid_headers()
        self.grid.verticalHeader().setVisible(False)
        self.grid.currentCellChanged.connect(self._grid_selection_changed)
        self.grid.cellDoubleClicked.connect(lambda _row, _column: self._select_current())
        layout.addWidget(self.grid, 1)
        return frame

    def _chart_pane(self):
        frame, layout = self._pane("Chart and Summary")
        config_row = QHBoxLayout()
        config_row.addWidget(QLabel("Quick Chart"))
        self.chart_configuration = QComboBox()
        self.chart_configuration.setEditable(True)
        self.chart_configuration.addItems(["Default"] + sorted((self.result.get("review_chart_configs") or {}).keys()))
        self.chart_configuration.currentTextChanged.connect(self._load_chart_configuration)
        config_row.addWidget(self.chart_configuration, 1)
        for label, callback in (
            ("Save", self._save_chart_configuration),
            ("Set Default", self._set_default_chart_configuration),
            ("Delete", self._delete_chart_configuration),
        ):
            button = QPushButton(label)
            button.clicked.connect(callback)
            config_row.addWidget(button)
        layout.addLayout(config_row)
        chart_row = QHBoxLayout()
        chart_row.addWidget(QLabel("Type"))
        self.chart_type = QComboBox()
        self.chart_type.addItems(["Bar", "Pareto", "Stacked", "Side by Side"])
        self.chart_type.currentTextChanged.connect(lambda _text: self._refresh_chart())
        chart_row.addWidget(self.chart_type)
        chart_row.addWidget(QLabel("Chart"))
        self.chart_dimension = QComboBox()
        self.chart_dimension.addItems([
            "Class Code", "Test", "Roughbin", "Channel", "Polarity",
            "Threshold Region", "Venn ID",
            "Cluster ID", "Repeater ID", "CAG Code", "Macro Sig Class", "Macro Sig ID", "Micro Sig Class",
            "Super Class",
            "DBB Global Bin", "DBC Bin", "DBG Group", "DBB Manual Bin",
        ])
        self.chart_dimension.currentTextChanged.connect(lambda _text: self._refresh_chart())
        chart_row.addWidget(self.chart_dimension)
        chart_row.addWidget(QLabel("Summary"))
        self.summary_mode = QComboBox()
        self.summary_mode.addItems(["Lot Summary", "Test Summary", "Classification Summary"])
        self.summary_mode.currentTextChanged.connect(lambda _text: self._refresh_summary())
        chart_row.addWidget(self.summary_mode)
        chart_row.addStretch(1)
        layout.addLayout(chart_row)
        self.chart = DefectChart()
        layout.addWidget(self.chart, 1)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        return frame

    def _apply_grid_headers(self):
        labels = dict(GRID_COLUMNS)
        self.grid.setColumnCount(len(self.grid_columns))
        self.grid.setHorizontalHeaderLabels([labels[key] for key in self.grid_columns])
        if "test" in self.grid_columns:
            self.grid.horizontalHeader().setSectionResizeMode(self.grid_columns.index("test"), QHeaderView.Stretch)

    def _configure_grid_columns(self):
        dialog = GridColumnsDialog(self.grid_columns, self)
        if _exec(dialog) == QDialog.Accepted and dialog.result_columns:
            self.grid_columns = dialog.result_columns
            self._apply_grid_headers()
            self._refresh_defects(self.selected_id)

    def _grab_dbb_clips(self):
        if not (self.result.get("dbb_execution") or {}).get("enabled"):
            QMessageBox.information(self, "Grab DBB Clips", "The selected lot was not created with Design Based Binning enabled.")
            return
        marked = [item for item in self.result.get("defects", []) if item.get("marked")]
        if not marked:
            QMessageBox.information(self, "Grab DBB Clips", "Mark at least one defect before grabbing DBB clips.")
            return
        existing = sum(1 for item in self.result.get("defects", []) if item.get("dbb_clip_saved"))
        dialog = DBBClipGrabDialog(len(marked), existing, self)
        if _exec(dialog) != QDialog.Accepted or dialog.result_options is None:
            return
        if dialog.result_options["delete_existing"]:
            for defect in self.result.get("defects", []):
                defect.pop("dbb_clip_saved", None)
                defect.pop("dbb_clip_image", None)
        for defect in marked[:200]:
            defect["dbb_clip_saved"] = True
            defect["dbb_clip_image"] = f"DBB_RDF_Clip_{defect.get('id')}.tif"
        self.result["dbb_saved_clip_count"] = sum(
            1 for item in self.result.get("defects", []) if item.get("dbb_clip_saved")
        )
        self.result.setdefault("review_operations", []).append({
            "operation": "Grab DBB Clips",
            "saved": min(200, len(marked)),
            "delete_existing": dialog.result_options["delete_existing"],
        })
        self._save_result()
        self._refresh_defects(self.selected_id)

    def _load_grid_configuration(self, name):
        if not hasattr(self, "grid"):
            return
        configs = self.result.get("review_grid_configs") or {}
        if name == "Default":
            default_name = self.result.get("default_review_grid_config")
            columns = configs.get(default_name, [key for key, _label in GRID_COLUMNS])
        else:
            columns = configs.get(name)
        if columns:
            valid = [key for key in columns if key in dict(GRID_COLUMNS)]
            if valid:
                self.grid_columns = valid
                self._apply_grid_headers()
                self._refresh_defects(self.selected_id)

    def _save_grid_configuration(self):
        name = self.grid_configuration.currentText().strip()
        if not name or name == "Default":
            return
        self.result.setdefault("review_grid_configs", {})[name] = list(self.grid_columns)
        if self.grid_configuration.findText(name) < 0:
            self.grid_configuration.addItem(name)
        self._save_result()

    def _delete_grid_configuration(self):
        name = self.grid_configuration.currentText()
        if name == "Default":
            return
        self.result.setdefault("review_grid_configs", {}).pop(name, None)
        if self.result.get("default_review_grid_config") == name:
            self.result.pop("default_review_grid_config", None)
        self.grid_configuration.removeItem(self.grid_configuration.findText(name))
        self.grid_configuration.setCurrentText("Default")
        self._save_result()

    def _set_default_grid_configuration(self):
        name = self.grid_configuration.currentText().strip()
        if name and name != "Default":
            self._save_grid_configuration()
            self.result["default_review_grid_config"] = name
            self._save_result()

    def _load_chart_configuration(self, name):
        if not hasattr(self, "chart"):
            return
        configs = self.result.get("review_chart_configs") or {}
        if name == "Default":
            config = configs.get(self.result.get("default_review_chart_config"), {})
        else:
            config = configs.get(name, {})
        if config:
            self.chart_type.setCurrentText(config.get("type", "Bar"))
            self.chart_dimension.setCurrentText(config.get("dimension", "Class Code"))
            self.summary_mode.setCurrentText(config.get("summary", "Lot Summary"))

    def _save_chart_configuration(self):
        name = self.chart_configuration.currentText().strip()
        if not name or name == "Default":
            return
        self.result.setdefault("review_chart_configs", {})[name] = {
            "type": self.chart_type.currentText(),
            "dimension": self.chart_dimension.currentText(),
            "summary": self.summary_mode.currentText(),
        }
        if self.chart_configuration.findText(name) < 0:
            self.chart_configuration.addItem(name)
        self._save_result()

    def _delete_chart_configuration(self):
        name = self.chart_configuration.currentText()
        if name == "Default":
            return
        self.result.setdefault("review_chart_configs", {}).pop(name, None)
        if self.result.get("default_review_chart_config") == name:
            self.result.pop("default_review_chart_config", None)
        self.chart_configuration.removeItem(self.chart_configuration.findText(name))
        self.chart_configuration.setCurrentText("Default")
        self._save_result()

    def _set_default_chart_configuration(self):
        name = self.chart_configuration.currentText().strip()
        if name and name != "Default":
            self._save_chart_configuration()
            self.result["default_review_chart_config"] = name
            self._save_result()

    def _refresh_chart(self):
        if not hasattr(self, "chart"):
            return
        mode = self.chart_dimension.currentText()
        key = {
            "Class Code": "class_code", "Test": "test", "Roughbin": "roughbin",
            "Channel": "channel", "Polarity": "polarity", "Threshold Region": "threshold_region",
            "Venn ID": "venn_id",
            "Cluster ID": "cluster_id", "Repeater ID": "repeater_id", "CAG Code": "cag_code",
            "Macro Sig Class": "macro_sig_class", "Macro Sig ID": "macro_sig_id",
            "Micro Sig Class": "micro_sig_class",
            "Super Class": "super_class",
            "DBB Global Bin": "dbb_global_bin",
            "DBC Bin": "dbc_bin",
            "DBG Group": "dbg_group",
            "DBB Manual Bin": "dbb_manual_bin",
        }[mode]
        counts = Counter(str(item.get(key, "")) for item in self.visible_defects)
        self.chart.set_counts(counts, f"{self.chart_type.currentText()} - Defects by {mode}", self.chart_type.currentText())

    def _refresh_summary(self):
        if not hasattr(self, "summary"):
            return
        summary = review_summary(self.result, self.visible_defects)
        mode = self.summary_mode.currentText()
        if mode == "Test Summary":
            lines = [f"{name}: {count}" for name, count in sorted(summary["by_test"].items())]
            text = "Tests\n" + ("\n".join(lines) if lines else "No visible defects")
        elif mode == "Classification Summary":
            lines = [f"Class {code}: {count}" for code, count in sorted(summary["by_class"].items())]
            text = "Classification\n" + ("\n".join(lines) if lines else "No visible defects")
        else:
            text = (
                f"Lot: {self.result.get('lot_id', '')}\nWafer: {self.result.get('wafer_id', '')}\n"
                f"Visible: {summary['visible']} of {summary['total']}\n"
                f"Marked: {summary['marked']}    Reviewed: {summary['reviewed']}"
            )
        self.summary.setText(text)

    def _refresh_defects(self, preferred_id=None):
        self.visible_defects = filter_defects(self.result, self.filters)
        if (self.result.get("sensitivity_tuner") or {}).get("auto_sort"):
            self.visible_defects.sort(
                key=lambda item: (int(item.get("class_code", 0)), int(item.get("id", 0)))
            )
        if self.layout_mode.currentText() == "Advanced Classify":
            if self.advanced_class_codes is not None:
                self.visible_defects = [
                    item for item in self.visible_defects
                    if int(item.get("class_code", 0)) in self.advanced_class_codes
                ]
            if self.advanced_attribute_values is not None:
                key = self._advanced_key()
                self.visible_defects = [
                    item for item in self.visible_defects
                    if str(item.get(key, "")) in self.advanced_attribute_values
                ]
        self._loading = True
        self.grid.setRowCount(0)
        for defect in self.visible_defects:
            row = self.grid.rowCount()
            self.grid.insertRow(row)
            values = []
            for key in self.grid_columns:
                value = defect.get(key)
                if key in ("marked", "reviewed"):
                    value = "Yes" if value else "No"
                values.append(value)
            for column, value in enumerate(values):
                self.grid.setItem(row, column, QTableWidgetItem(str(value)))
        self._loading = False
        self.wafer_map.set_defects(self.visible_defects)
        self.wafer_map.set_selected_ids(self.selected_ids)
        summary = review_summary(self.result, self.visible_defects)
        self._refresh_chart()
        self._refresh_summary()
        self._refresh_advanced_classify()
        match = result_matches_recipe(self.result, self.current_recipe)
        mode = "Snapshot data" if self.snapshot_mode else "Complete lot result"
        recipe_name = (self.current_recipe or {}).get(
            "inspection", self.result.get("inspection", "")
        )
        self.status.setText(
            f"{mode}    Recipe: {recipe_name} ({'Matched' if match else 'Mismatch'})    "
            f"Lot: {self.result.get('lot_id', '')}    "
            f"Defects: {summary['visible']} / {summary['total']}"
        )
        self.map_info.setText(f"Red: defect    Green: marked    Yellow: selected    Visible defects: {summary['visible']}")
        if self.visible_defects:
            ids = {item.get("id") for item in self.visible_defects}
            self._select_id(preferred_id if preferred_id in ids else self.visible_defects[0].get("id"))
        else:
            self.selected_id = None
            for widget in self.image_widgets:
                widget.set_defect(None)

    def _grid_selection_changed(self, row, _column, _previous_row, _previous_column):
        if not self._loading and 0 <= row < len(self.visible_defects):
            self._select_id(self.visible_defects[row].get("id"), select_row=False)

    def _select_id(self, defect_id, select_row=True):
        self.selected_id = defect_id
        defect = next((item for item in self.visible_defects if item.get("id") == defect_id), None)
        if not defect:
            return
        self.wafer_map.select_defect(defect_id)
        for widget in self.image_widgets:
            widget.set_defect(defect)
        defect["reviewed"] = True
        self.defect_details.setText(
            f"Defect {defect.get('id')}    Die ({defect.get('die_x')}, {defect.get('die_y')})    "
            f"Test: {defect.get('test')}    Class: {defect.get('class_code')}    "
            f"Size: {defect.get('size_um')} um    Signal: {defect.get('signal')}"
        )
        if hasattr(self, "design_details") and (self.result.get("dbb_execution") or {}).get("enabled"):
            self.design_details.setText(
                f"Defect {defect.get('id')}\n"
                f"Design position: ({defect.get('design_x_nm', '-')}, {defect.get('design_y_nm', '-')}) nm\n"
                f"Layer: {defect.get('design_layer', '-')}\n"
                f"DBB Global Bin: {defect.get('dbb_global_bin', '-')}\n"
                f"DBC Bin: {defect.get('dbc_bin', '-')}    DBG Group: {defect.get('dbg_group', '-')}\n"
                f"DCI: {defect.get('dci', '-')}    PCI: {defect.get('pci', '-')}    "
                f"Pattern Density: {defect.get('pattern_density', '-')}"
            )
        if select_row:
            row = next((index for index, item in enumerate(self.visible_defects) if item.get("id") == defect_id), -1)
            if row >= 0:
                self._loading = True
                self.grid.selectRow(row)
                self._loading = False

    def _navigate(self, direction):
        if not self.visible_defects:
            return
        index = next((i for i, item in enumerate(self.visible_defects) if item.get("id") == self.selected_id), 0)
        self._select_id(self.visible_defects[(index + direction) % len(self.visible_defects)].get("id"))

    def _navigate_group(self, key, direction):
        if not self.visible_defects:
            return
        current = next(
            (item for item in self.visible_defects if item.get("id") == self.selected_id),
            self.visible_defects[0],
        )
        if key == "die":
            value = (current.get("die_x"), current.get("die_y"))
            group = lambda item: (item.get("die_x"), item.get("die_y"))
        elif key == "row":
            value = current.get("die_y")
            group = lambda item: item.get("die_y")
        else:
            layout = self.current_recipe.get("wafer_map", {}) if self.current_recipe else {}
            width = max(1, int(layout.get("reticle_width", 1)))
            height = max(1, int(layout.get("reticle_height", 1)))
            value = (int(current.get("die_x", 0)) // width, int(current.get("die_y", 0)) // height)
            group = lambda item: (
                int(item.get("die_x", 0)) // width,
                int(item.get("die_y", 0)) // height,
            )
        groups = []
        for item in self.visible_defects:
            candidate = group(item)
            if candidate not in groups:
                groups.append(candidate)
        index = groups.index(value) if value in groups else 0
        target = groups[(index + direction) % len(groups)]
        defect = next(item for item in self.visible_defects if group(item) == target)
        self._select_id(defect.get("id"))

    def _navigate_marked(self, direction):
        marked = [item for item in self.visible_defects if item.get("marked")]
        if not marked:
            self.status.setText("No marked locations are available for navigation.")
            return
        index = next((i for i, item in enumerate(marked) if item.get("id") == self.selected_id), -1)
        self._select_id(marked[(index + direction) % len(marked)].get("id"))

    def _adjust_review_optics(self, key, delta, label):
        low, high = (-20, 20) if key in {"magnification_step", "focus_offset"} else (0, 100)
        self.review_optics_state[key] = max(low, min(high, self.review_optics_state[key] + delta))
        self.status.setText(f"{label}: {self.review_optics_state[key]}")

    def _quick_grab(self, source):
        defect = next((item for item in self.result.get("defects", []) if item.get("id") == self.selected_id), None)
        if defect is None:
            self.status.setText("Select a defect before grabbing an image.")
            return
        defect["has_manual_image"] = True
        defect["manual_image_settings"] = {"image_optics": source}
        self._save_result()
        self._refresh_defects(self.selected_id)
        self.status.setText(f"Grabbed current defect image using {source}.")

    def _toggle_mark(self):
        defect = next((item for item in self.result.get("defects", []) if item.get("id") == self.selected_id), None)
        if not defect:
            return
        defect["marked"] = not defect.get("marked")
        self._save_result()
        self._refresh_defects(defect.get("id"))

    def _select_current(self):
        if self.selected_id is None:
            return
        self._toggle_selected_id(self.selected_id)

    def _toggle_selected_id(self, defect_id):
        if defect_id in self.selected_ids:
            self.selected_ids.remove(defect_id)
        else:
            self.selected_ids.add(defect_id)
        self.wafer_map.set_selected_ids(self.selected_ids)
        self.status.setText(f"{len(self.selected_ids)} defect(s) selected for filtering or classification")

    def _select_area(self, identifiers):
        inside = [item for item in self.visible_defects if item.get("id") in set(identifiers)]
        mode = self.selection_mode.currentText()
        if "Die" in mode:
            dies = {(item.get("die_x"), item.get("die_y")) for item in inside}
            identifiers = [
                item.get("id") for item in self.visible_defects
                if (item.get("die_x"), item.get("die_y")) in dies
            ]
        elif "Reticle" in mode:
            layout = self.current_recipe.get("wafer_map", {}) if self.current_recipe else {}
            width = max(1, int(layout.get("reticle_width", 1)))
            height = max(1, int(layout.get("reticle_height", 1)))
            fields = {
                (int(item.get("die_x", 0)) // width, int(item.get("die_y", 0)) // height)
                for item in inside
            }
            identifiers = [
                item.get("id") for item in self.visible_defects
                if (int(item.get("die_x", 0)) // width, int(item.get("die_y", 0)) // height) in fields
            ]
        if mode.startswith("Deselect"):
            self.selected_ids.difference_update(identifiers)
        else:
            self.selected_ids.update(identifiers)
        self.wafer_map.set_selected_ids(self.selected_ids)
        self.grid.clearSelection()
        for row, defect in enumerate(self.visible_defects):
            if defect.get("id") in self.selected_ids:
                self.grid.selectRow(row)
        self.status.setText(f"{len(self.selected_ids)} defect(s) selected using {mode}")

    def _filter_in(self):
        if not self.selected_ids:
            return
        self.filters["include_ids"] = sorted(self.selected_ids)
        self.filters["exclude_ids"] = []
        self._refresh_defects(self.selected_id)

    def _filter_out(self):
        if not self.selected_ids:
            return
        excluded = set(self.filters.get("exclude_ids") or [])
        excluded.update(self.selected_ids)
        self.filters["exclude_ids"] = sorted(excluded)
        self.selected_ids.clear()
        self._refresh_defects()

    def _reset_filter(self):
        self.filters = default_filter_state()
        self.selected_ids.clear()
        self._refresh_defects(self.selected_id)

    def _classify(self):
        selected = [item for item in self.result.get("defects", []) if item.get("id") in self.selected_ids]
        marked = [item for item in self.result.get("defects", []) if item.get("marked")]
        targets = selected or marked or [
            item for item in self.result.get("defects", []) if item.get("id") == self.selected_id
        ]
        if not targets:
            return
        dialog = ClassifyDefectsDialog(len(targets), self)
        if _exec(dialog) != QDialog.Accepted or dialog.class_code is None:
            return
        for defect in targets:
            defect["class_code"] = dialog.class_code
            defect["reviewed"] = True
        self.result.setdefault("review_log", []).append(
            f"Assigned manual class code {dialog.class_code} to {len(targets)} defect(s)"
        )
        self._save_result()
        self._refresh_defects(self.selected_id)

    def _filter(self):
        dialog = DefectFilterDialog(self.result, self.filters, self)
        if _exec(dialog) == QDialog.Accepted and dialog.result_filters is not None:
            self.filters = dialog.result_filters
            self._refresh_defects()

    def _filter_analysis(self):
        dialog = ReviewFilterAnalysisDialog(
            self.result,
            self.result.get("filter_analysis"),
            self,
        )
        if _exec(dialog) != QDialog.Accepted or dialog.result_state is None:
            return
        state = dialog.result_state
        enabled = [item for item in state["operations"] if item.get("enabled")]
        previous_results = self.store.list_results() if self.store else []
        self.result, execution = execute_filter_analysis(
            self.result,
            state,
            previous_results=previous_results,
        )
        if any(item["type"] == "Filter" for item in enabled):
            self.filters = default_filter_state()
            self.filters["include_ids"] = list(execution["visible_ids"])
        else:
            self.filters = default_filter_state()
        if state.get("analysis") is not None:
            self.result["review_analysis"] = deepcopy(state["analysis"])
        names = [item["name"] for item in enabled]
        self._save_result()
        self._refresh_defects(self.selected_id)
        self.status.setText(
            f"Filter and Analysis executed in order: {', '.join(names) or 'none'}; "
            f"{len(execution['visible_ids'])} defects visible."
        )

    def _analysis(self):
        toolbox = DefectAnalysisToolboxDialog(self)
        if _exec(toolbox) != QDialog.Accepted:
            return
        if toolbox.operation == "Apply Binner":
            self._apply_binner()
        elif toolbox.operation == "Wafer Post Processing":
            self._wafer_analysis()

    def _apply_binner(self):
        dialog = ApplyBinnerDialog(
            self.result,
            self.visible_defects,
            self.selected_ids,
            self.current_recipe,
            self,
        )
        if _exec(dialog) != QDialog.Accepted or dialog.result_result is None:
            return
        self.result = dialog.result_result
        self._save_result()
        self._refresh_defects(self.selected_id)
        stats = dialog.stats or {}
        self.status.setText(
            "Apply Binner processed {processed} defect(s): {classified} classified, "
            "{filtered} filtered.".format(**stats)
        )

    def _wafer_analysis(self):
        dialog = WaferPostProcessingDialog(
            self.result.get("review_analysis"),
            test_count=len(self.result.get("selected_tests", [])),
            parent=self,
        )
        if _exec(dialog) == QDialog.Accepted and dialog.result_state is not None:
            self.result["review_analysis"] = dialog.result_state
            enabled = [item["name"] for item in dialog.result_state["operations"] if item.get("enabled")]
            review_state = default_filter_analysis_state()
            review_state["analysis"] = deepcopy(dialog.result_state)
            for operation in review_state["operations"]:
                operation["enabled"] = operation["type"] == "Analysis" and operation["name"] in enabled
            self.result, execution = execute_filter_analysis(
                self.result,
                review_state,
                previous_results=self.store.list_results() if self.store else [],
                source_ids=[item.get("id") for item in self.visible_defects],
            )
            self._save_result()
            self._refresh_defects(self.selected_id)
            self.status.setText(
                f"Analysis applied to visible data: {', '.join(enabled) or 'no operations enabled'}; "
                f"{len(execution['visible_ids'])} defects remain in scope."
            )

    def _super_class(self):
        dialog = SuperClassDialog(self.result, self)
        if _exec(dialog) != QDialog.Accepted or dialog.result_result is None:
            return
        self.result = dialog.result_result
        self._save_result()
        self._refresh_defects(self.selected_id)
        self.status.setText("Super Class grouping applied to the Review grid and charts.")

    def _results_utility(self):
        sources = self.store.list_results() if self.store else []
        dialog = ResultsUtilityDialog(self.result, sources, self.visible_defects, self)
        if _exec(dialog) != QDialog.Accepted:
            return
        if dialog.new_result is not None:
            if self.store:
                self.store.save_result(dialog.new_result)
            self.status.setText(dialog.status_message)
            return
        if dialog.result_result is not None:
            self.result = dialog.result_result
            self._save_result()
            self._refresh_defects(self.selected_id)
            self.status.setText(dialog.status_message)

    def _adjust_offset(self, die_origin):
        dialog = ReviewOffsetDialog(self.result, die_origin=die_origin, parent=self)
        if _exec(dialog) != QDialog.Accepted or dialog.result_result is None:
            return
        self.result = dialog.result_result
        self._save_result()
        self._refresh_defects(self.selected_id)
        label = "Die origin" if die_origin else "Defect"
        self.status.setText(f"{label} offset applied to all defects.")

    def _optics_selector(self):
        dialog = OpticsSelectorDialog(
            self.result,
            self.current_recipe,
            self.result.get("optics_selector"),
            self,
        )
        if _exec(dialog) != QDialog.Accepted or dialog.result_state is None:
            return
        self.result["optics_selector"] = deepcopy(dialog.result_state)
        self.result.setdefault("review_log", []).append(
            f"Optics Selector stored {len(dialog.result_state.get('modes', []))} mode(s)"
        )
        self._save_result()
        if self.store and self.current_recipe and dialog.result_state.get("inserted_test_count"):
            self.current_recipe = self.store.save_recipe(self.current_recipe)
        self.status.setText("Optics Selector data saved for later analysis.")

    def _sensitivity_tuner(self):
        dialog = SensitivityTunerDialog(
            self.result,
            self.current_recipe,
            self.result.get("sensitivity_tuner"),
            self,
        )
        if _exec(dialog) != QDialog.Accepted or dialog.result_state is None:
            return
        state = dialog.result_state
        self.result["sensitivity_tuner"] = deepcopy(state)
        scope = state.get("filter_scope")
        evaluation = (
            state.get("test_evaluation") or {}
            if scope == "Filter to Current Test"
            else state.get("evaluation") or {}
        )
        if scope == "Filter to Current Test":
            self.filters["tests"] = [state.get("test")]
        mode = state.get("show_mode")
        if scope != "No Review Filter" or mode != "Show All Defects":
            identifiers = {
                "Show Undetected Defects": evaluation.get("undetected_ids", []),
                "Show Detected Defects": evaluation.get("detected_ids", []),
            }.get(mode, evaluation.get("considered_ids", []))
            self.filters["include_ids"] = list(identifiers)
        if self.current_recipe and state.get("finish_action") == "Save & Exit":
            self.current_recipe.setdefault("sensitivity_tuner_updates", []).append(deepcopy(state))
            if self.store:
                self.current_recipe = self.store.save_recipe(self.current_recipe)
        elif self.current_recipe and state.get("finish_action") == "Save Recipe As..." and self.store:
            identity = state.get("recipe_identity") or {}
            saved_as = self.store.duplicate_recipe(self.current_recipe, identity.get("inspection", "Tuned Recipe"))
            saved_as["device"] = identity.get("device", self.current_recipe.get("device", ""))
            saved_as["step"] = identity.get("step", self.current_recipe.get("step", ""))
            saved_as.setdefault("sensitivity_tuner_updates", []).append(deepcopy(state))
            self.store.save_recipe(saved_as, event="Sensitivity Tuner Save As")
        self.result.setdefault("review_log", []).append(
            f"Sensitivity Tuner {state.get('algorithm')} {state.get('parameter')}={state.get('value')}"
        )
        self._save_result()
        self._refresh_defects(self.selected_id)
        self.status.setText(
            f"Sensitivity Tuner detected {evaluation.get('detected', 0)} of {evaluation.get('considered', 0)} defect(s)."
        )

    def _combine_sensitivity_results(self):
        sources = self.store.list_results() if self.store else []
        dialog = CombineSensitivityResultsDialog(self.result, sources, self)
        if _exec(dialog) != QDialog.Accepted or dialog.result_result is None:
            return
        saved = self.store.save_result(dialog.result_result) if self.store else dialog.result_result
        self.status.setText(
            f"Combined Sensitivity Tuner result saved as {saved.get('lot_id', '')} "
            f"with {saved.get('defect_count', 0)} defects."
        )

    def _send_images(self):
        transferable = [
            item for item in self.result.get("defects", [])
            if item.get("has_patch_image") or item.get("has_sem_image") or item.get("has_manual_image")
        ]
        self.result.setdefault("transfer", {})["images_state"] = f"Transferred {len(transferable)} lot image set(s)"
        self._save_result()
        self.status.setText(self.result["transfer"]["images_state"])

    def _send_wafer(self):
        dialog = WaferDataTransferDialog(self.result, self.visible_defects, self)
        if _exec(dialog) != QDialog.Accepted or dialog.result_options is None:
            return
        options = dialog.result_options
        transfer = self.result.setdefault("transfer", {})
        transfer["wafer_state"] = "Transferred"
        transfer["wafer_scope"] = options["scope"]
        transfer["wafer_include_duplicates"] = options["include_duplicates"]
        transfer["wafer_defect_ids"] = list(options["defect_ids"])
        transfer["wafer_defect_count"] = options["defect_count"]
        self._save_result()
        self.status.setText(
            f"Transferred {options['defect_count']} current-wafer defect(s) "
            f"from {options['scope'].lower()}."
        )

    def _send_lot(self):
        self.result.setdefault("transfer", {})["lot_state"] = "Transferred"
        self._save_result()
        self.status.setText("Current lot results transferred to the configured analysis system.")

    def _export(self):
        filename, _selected = QFileDialog.getSaveFileName(
            self,
            "Export KLARF",
            f"{self.result.get('lot_id', 'lot')}_{self.result.get('wafer_id', 'wafer')}.klarf",
            "KLARF Files (*.klarf);;Text Files (*.txt)",
        )
        if not filename:
            return
        try:
            Path(filename).write_text(export_klarf_text(self.result, self.visible_defects), encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(self, "Export KLARF", str(exc))
            return
        self.result.setdefault("exports", []).append(filename)
        self._save_result()
        self.status.setText(f"Filtered lot exported: {filename}")

    def _update_snapshot(self):
        if not self.snapshot_update_callback:
            self.status.setText("No active inspection is available to update this snapshot.")
            self.update_snapshot.setEnabled(False)
            return
        updated = self.snapshot_update_callback()
        if not updated:
            self.status.setText("No newer snapshot data is available.")
            return
        current_id = self.selected_id
        self.result = deepcopy(updated)
        self.selected_ids.intersection_update(
            defect.get("id") for defect in self.result.get("defects", [])
        )
        self._refresh_defects(preferred_id=current_id)
        complete = bool(self.result.get("snapshot_complete"))
        self.update_snapshot.setEnabled(not complete)
        if complete:
            self.status.setText("Inspection data is complete; complete-data review functions are now available.")
        self._refresh_snapshot_controls()

    def _refresh_snapshot_controls(self):
        complete = not self.snapshot_mode or bool(self.result.get("snapshot_complete"))
        for control in self.complete_data_controls:
            control.setEnabled(complete)
        machine_free = complete and self.result.get("review_mode") != "Review Only"
        for control in self.machine_free_controls:
            control.setEnabled(machine_free)
        if hasattr(self, "grab_dbb_clips"):
            self.grab_dbb_clips.setEnabled(
                machine_free
                and bool((self.result.get("dbb_execution") or {}).get("enabled"))
            )
        if hasattr(self, "update_snapshot"):
            self.update_snapshot.setEnabled(
                self.snapshot_mode
                and not complete
                and self.snapshot_update_callback is not None
            )

    def _save_result(self):
        if self.store and self.result.get("status") != "Running":
            self.result = self.store.save_result(self.result)

    def keyPressEvent(self, event):
        modifiers = event.modifiers()
        if event.key() == Qt.Key_F11:
            self._navigate(-1)
        elif event.key() == Qt.Key_F12:
            self._navigate(1)
        elif event.key() == Qt.Key_F9 and modifiers & Qt.ShiftModifier:
            self._navigate_group("row", -1)
        elif event.key() == Qt.Key_F10 and modifiers & Qt.ShiftModifier:
            self._navigate_group("row", 1)
        elif event.key() == Qt.Key_F9:
            self._navigate_group("die", -1)
        elif event.key() == Qt.Key_F10:
            self._navigate_group("die", 1)
        elif event.key() == Qt.Key_F7 and modifiers & Qt.ShiftModifier:
            self._navigate_group("reticle", -1)
        elif event.key() == Qt.Key_F8 and modifiers & Qt.ShiftModifier:
            self._navigate_group("reticle", 1)
        elif event.key() == Qt.Key_L and modifiers & Qt.ControlModifier and modifiers & Qt.ShiftModifier:
            self._navigate_marked(-1)
        elif event.key() == Qt.Key_L and modifiers & Qt.ControlModifier:
            self._navigate_marked(1)
        elif event.key() == Qt.Key_F3:
            self._adjust_review_optics("magnification_step", 1, "Magnification")
        elif event.key() == Qt.Key_F4:
            self._adjust_review_optics("magnification_step", -1, "Magnification")
        elif event.key() == Qt.Key_F5:
            self._adjust_review_optics("light_level", 1, "Light level")
        elif event.key() == Qt.Key_F6:
            self._adjust_review_optics("light_level", -1, "Light level")
        elif event.key() == Qt.Key_F7:
            self._adjust_review_optics("focus_offset", 1, "Focus offset")
        elif event.key() == Qt.Key_F8:
            self._adjust_review_optics("focus_offset", -1, "Focus offset")
        elif event.key() == Qt.Key_P and modifiers & Qt.ControlModifier:
            self._adjust_review_optics("aperture", 1, "Aperture")
        elif event.key() == Qt.Key_E and modifiers & Qt.ControlModifier:
            self._adjust_review_optics("aperture", -1, "Aperture")
        elif event.key() == Qt.Key_S and modifiers & Qt.ControlModifier and modifiers & Qt.ShiftModifier:
            self._quick_grab("Current Review Optics")
        elif event.key() == Qt.Key_T and modifiers & Qt.ControlModifier and modifiers & Qt.ShiftModifier:
            self._quick_grab("Inspection Test Optics")
        elif event.key() == Qt.Key_S and modifiers & Qt.ControlModifier:
            self._select_current()
        elif event.key() == Qt.Key_A and modifiers & Qt.ControlModifier:
            self._select_all_visible()
        elif event.key() == Qt.Key_Q and modifiers & Qt.ControlModifier:
            self._filter_out()
        elif event.key() == Qt.Key_W and modifiers & Qt.ControlModifier:
            self._filter_in()
        elif event.key() == Qt.Key_R and modifiers & Qt.ControlModifier:
            self._reset_filter()
        elif event.key() == Qt.Key_Left:
            self._navigate(-1)
        elif event.key() == Qt.Key_Right:
            self._navigate(1)
        elif event.key() == Qt.Key_M:
            self._toggle_mark()
        elif event.key() == Qt.Key_F and modifiers & Qt.ControlModifier:
            self._filter()
        else:
            super().keyPressEvent(event)

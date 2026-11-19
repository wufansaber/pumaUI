from __future__ import annotations

from copy import deepcopy
from collections import Counter
from datetime import datetime
import json
import math
from pathlib import Path

from ...qt_compat import (
    QAbstractButton,
    QAbstractItemView,
    QApplication,
    QColor,
    QColorDialog,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QDesktopServices,
    QEvent,
    QFileDialog,
    QFrame,
    QFont,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QIcon,
    QItemSelectionModel,
    QLabel,
    QLineEdit,
    QMenu,
    QMenuBar,
    QMessageBox,
    QObject,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPrintDialog,
    QPrinter,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSize,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QStyle,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QToolButton,
    QTimer,
    QToolTip,
    QTreeWidget,
    QTreeWidgetItem,
    Qt,
    QUrl,
    QVBoxLayout,
    QWidget,
)
from ...widgets import (
    ClassicButton,
    CollapsibleGroup,
    FullscreenWindowAdapter,
    GroupHeader,
    SubmenuButtonRow,
    WindowCaptionButtons,
    wafer_disk_with_notch,
)
from .icons import icon as vector_icon
from .icons import pixmap as vector_pixmap
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
    apply_collected_sensitivity,
    filter_defects,
    filtered_result_as,
    merge_result,
    sensitivity_test_names,
    normalized_filter_analysis_state,
    result_matches_recipe,
    review_summary,
    select_wafer_transfer_defects,
)


def _defect_grid_columns():
    """Regular attributes from Table 10-7, then per-channel attributes, then SDI (Table 10-8)."""
    regular = [
        ("id", "ID"),
        ("marked", "Marked"),
        ("sample", "Sample"),
        ("manual_class", "Manual Class"),
        ("ch1_intensity", "Ch1_Intensity"),
        ("ch2_intensity", "Ch2_Intensity"),
        ("ch3_intensity", "Ch3_Intensity"),
        ("added", "Added"),
        ("fine_code", "Fine Code"),
        ("ido_rough_code", "Rough Class"),
        ("angle", "Angle"),
        ("hlatcf_intensity", "HLATCFIntensity"),
        ("roughbin", "Rough Code"),
        ("area", "Area"),
        ("hlatcf_noise", "HLATCFNoise"),
        ("cag_code", "CAG Code"),
        ("hlat_intensity", "HLATIntensity"),
        ("scale_flag", "Scale Flag"),
        ("cf_ch123_fusion", "CF_Ch123Fusion"),
        ("scaled_size", "Scaled Size"),
        ("cf_ch12_fusion", "CF_Ch12Fusion"),
        ("intensity", "Intensity"),
        ("scale_factor", "ScaleFactor"),
        ("cf_ch13_fusion", "CF_Ch13Fusion"),
        ("macro_sig_class", "Macro Sig Class"),
        ("segment_id", "SegmentID"),
        ("cf_ch1_intensity", "CF_Ch1Intensity"),
        ("macro_sig_id", "Macro Sig Id"),
        ("segment_mode", "SegmentMode"),
        ("cf_ch23_fusion", "CF_Ch23Fusion"),
        ("single_channel_biased", "SingleChannelBiased"),
        ("cf_ch2_intensity", "CF_Ch2Intensity"),
        ("max_dim", "Max Dim"),
        ("cf_ch3_intensity", "CF_Ch3Intensity"),
        ("single_pixel_event", "SinglePixelEvent"),
        ("cf_strip_correlation", "CF_StripCorrelation"),
        ("max_channel_brightness", "MaxChannelBrightness"),
        ("super_class", "Super Class"),
        ("cf_top_side_fusion", "CF_TopSideFusion"),
        ("max_x_gradient", "MaxXGradient"),
        ("test", "Test ID"),
        ("ch_fusion_post_nonlinear", "ChFusion_PostNonLinearFilterStrength"),
        ("micro_sig_class", "Micro Sig Class"),
        ("threshold_region", "Threshold Region"),
        ("clip_transfer_sample", "Clip transfer sample"),
        ("min_dim", "Min Dim"),
        ("union_id", "Union ID"),
        ("cluster_id", "ClusterId"),
        ("partial_die", "Partial Die"),
        ("unsupervised", "Unsupervised"),
        ("combine_result_source_id", "CombineResult Source ID"),
        ("polarity", "Polarity"),
        ("venn_id", "Venn ID"),
        ("die_x", "Die Col"),
        ("prediction", "Prediction"),
        ("x_die", "X (Die)"),
        ("die_y", "Die Row"),
        ("primary_channel", "Primary Channel"),
        ("x_wafer", "X (Wafer)"),
        ("duplicate", "Duplicate"),
        ("radius", "Radius"),
        ("y_die", "Y (Die)"),
        ("edge_die_defect", "EdgeDieDefect"),
        ("reference_size", "ReferenceSize"),
        ("y_wafer", "Y (Wafer)"),
        ("fine_class", "Fine Class"),
        ("repeater_id", "RepeaterId"),
        ("class_code", "Class"),
        ("size_um", "Size (um)"),
        ("signal", "Signal"),
        ("ido_rough_group", "Rough Group"),
        ("reviewed", "Reviewed"),
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
    ]
    channel_fields = [
        ("hlat_absmin", "HLAT Absmin"),
        ("hlat_color", "HLAT Color"),
        ("hlat_gradient", "HLAT Gradient"),
        ("hlat_intensity", "HLAT Intensity"),
        ("hlat_noise", "HLAT Noise"),
        ("local_noise_threshold", "LocalNoiseThreshold"),
        ("median_intensity", "MedianInstensity"),
        ("post_nonlinear_filter_strength", "PostNonLinearFilterStrength"),
        ("primary_segment_id", "PrimarySegmentID"),
        ("secondary_seg_hlat_absmin", "SecondarySeg_00_HLATAbsmin"),
        ("secondary_seg_hlat_color", "SecondarySeg_00_HLAT Color"),
        ("secondary_seg_hlat_gradient", "SecondarySeg_00_HLAT Gradient"),
        ("secondary_seg_hlat_intensity", "SecondarySeg_00_HLAT Intensity"),
        ("secondary_seg_hlat_noise", "SecondarySeg_00_HLAT Noise"),
        ("secondary_seg_segment_id", "SecondarySeg_00_SegmentID"),
        ("segment_mask", "Segment Mask"),
        ("x_projection_percentage", "XProjectionPercentage"),
        ("y_projection_percentage", "YProjectionPercentage"),
        ("biased", "Biased"),
        ("non_uniqueness", "NonUniqueness"),
    ]
    for number in (1, 2, 3):
        for key, label in channel_fields:
            regular.append((f"ch{number}_{key}", f"Ch{number}_{label}"))
    regular.extend([
        ("sdi_group_id", "SDIGroupID"),
        ("primary_sdi_threshold", "Primary_SDIThreshold"),
        ("channel1_sdi_threshold", "Channel1_SDIThreshold"),
        ("channel2_sdi_threshold", "Channel2_SDIThreshold"),
        ("channel3_sdi_threshold", "Channel3_SDIThreshold"),
        ("sdicf_ch12_threshold", "SDICF_CH12_Threshold"),
        ("sdicf_ch13_threshold", "SDICF_CH13_Threshold"),
        ("sdicf_ch23_threshold", "SDICF_CH23_Threshold"),
        ("sdicf_ch123_threshold", "SDICF_CH123_Threshold"),
        ("sdi_defect_type", "SDI_DefectType"),
    ])
    return regular


GRID_COLUMNS = _defect_grid_columns()
FIXED_GRID_COLUMNS = ("id", "marked", "sample", "manual_class")
GRID_CHECK_COLUMNS = {"marked", "sample"}
GRID_CHOICE_COLUMNS = {"manual_class"}


def _review_grid_columns(result):
    columns = list(GRID_COLUMNS)
    known = {key for key, _label in columns}
    for column in (result or {}).get("source_defect_columns") or []:
        key = str(column.get("key") or "")
        label = str(column.get("label") or key)
        if key and key not in known:
            columns.append((key, label))
            known.add(key)
    return columns


def _initial_review_grid_columns(result, available):
    available_keys = {key for key, _label in available}
    fixed = [key for key in FIXED_GRID_COLUMNS if key in available_keys]
    configured = (result or {}).get("default_review_grid_columns") or []
    configured = [key for key in configured if key in available_keys]
    if configured:
        return configured
    source = [
        str(column.get("key") or "")
        for column in (result or {}).get("source_defect_columns") or []
    ]
    source = [key for key in source if key in available_keys and key not in fixed]
    if source:
        return fixed + source
    defects = list((result or {}).get("defects") or [])
    present = []
    for key, _label in available:
        if key in fixed:
            continue
        if any(key in defect for defect in defects):
            present.append(key)
    return fixed + present

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
        self.on_clicked = None
        self.on_zoom_changed = None
        self.drag_start = None
        self.drag_end = None
        self._pan_cursor = None
        self.zoom_factor = 1.0
        self.view_center = (0.0, 0.0)
        self._zoom_drag = False
        self.show_die = True
        self.show_defects = True
        self.show_counts = False
        self.display_rules = []
        self.interaction = "select"
        self.display_mode = "Wafer Map"
        self.stack_defects = False
        self.show_legend = False
        self.show_care_areas = False
        self.show_partial_die = False
        self.show_selected_crosshair = True
        self.show_overview = False
        self.show_tooltips = False
        self.show_reticle = False
        self.show_marker = True
        self.show_reticle_modulation = False
        self.defect_resolution = "Small"
        self.stack_tolerance_x = 0.0
        self.stack_tolerance_y = 0.0
        self.die_pitch_x = 5100.0
        self.die_pitch_y = 16600.0
        self.care_rects = []
        self.dont_care_rects = []
        self.setMouseTracking(True)
        self.location_marks = []
        self.secondary_dies = set()
        self._pan_last = None
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
        self.zoom_factor = max(0.5, min(12.0, float(factor)))
        self._clamp_view_center()
        self.update()

    def _clamp_view_center(self):
        # Keep the wafer reachable: the view can travel about one radius past
        # the rim before the map would be panning empty space.
        limit = max(0.5, 1.6 - 0.6 / max(self.zoom_factor, 0.5))
        self.view_center = (
            max(-limit, min(limit, float(self.view_center[0]))),
            max(-limit, min(limit, float(self.view_center[1]))),
        )

    def pan_by(self, dx, dy):
        """Move the view by a pixel delta (positive x moves the map right)."""
        _x0, _y0, side = self._geometry()
        self.view_center = (
            self.view_center[0] - dx / max(side, 1) * 2,
            self.view_center[1] + dy / max(side, 1) * 2,
        )
        self._clamp_view_center()
        self.update()

    def zoom_at(self, px, py, factor):
        """Zoom in/out while keeping the wafer point under (px, py) fixed."""
        new_factor = max(0.5, min(12.0, float(self.zoom_factor) * float(factor)))
        if abs(new_factor - self.zoom_factor) < 1e-6:
            return
        width, height = self.width(), self.height()
        fit = max(40.0, min(width, height) - 28.0)
        x0, y0, side = self._geometry()
        if side <= 1:
            self.zoom_factor = new_factor
            self.update()
            return
        wafer_x = (px - x0) / side * 2 - 1
        wafer_y = 1 - (py - y0) / side * 2
        side_new = fit * new_factor
        left = px - (wafer_x + 1) / 2 * side_new
        top = py - (1 - wafer_y) / 2 * side_new
        self.zoom_factor = new_factor
        self.view_center = (
            (width / 2 - side_new / 2 - left) * 2 / side_new,
            (top - height / 2 + side_new / 2) * 2 / side_new,
        )
        self._clamp_view_center()
        if callable(self.on_zoom_changed):
            self.on_zoom_changed(self.zoom_factor)
        self.update()

    def reset_view(self):
        self.zoom_factor = 1.0
        self.view_center = (0.0, 0.0)
        if callable(self.on_zoom_changed):
            self.on_zoom_changed(self.zoom_factor)
        self.update()

    def wheelEvent(self, event):  # noqa: N802 - Qt override
        # The wheel always zooms and drags pan, in every interaction mode.
        delta = event.angleDelta().y() if hasattr(event, "angleDelta") else 0
        if not delta:
            return
        steps = delta / 120.0
        point = event.position() if hasattr(event, "position") else event.pos()
        self.zoom_at(point.x(), point.y(), 1.2 ** steps)
        event.accept()

    def _geometry(self):
        """Fit the wafer to the pane, then apply zoom around the view center.

        Pane size changes the drawn size of the wafer and every mark on it.
        Zoom keeps that scale relationship and shows only the portion that
        fits in the pane.
        """
        fit = max(40.0, min(self.width(), self.height()) - 28.0)
        side = fit * self.zoom_factor
        center_x, center_y = self.view_center
        x0 = self.width() / 2 - side / 2 - center_x * side / 2
        y0 = self.height() / 2 - side / 2 + center_y * side / 2
        return x0, y0, side

    def set_display_rules(self, rules):
        self.display_rules = deepcopy(rules or [])
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#7d7f80"))
        x0, y0, side = self._geometry()
        mark = max(2.0, side * 0.014) * (1.8 if self.defect_resolution == "Large" else 1.0)
        painter.setPen(QPen(QColor("#202020"), 1))
        painter.setBrush(QColor("#f4f4f1"))
        painter.drawEllipse(int(x0), int(y0), int(side), int(side))
        if self.show_die:
            painter.setPen(QPen(QColor("#c9c9c5"), 1))
            step = max(4, int(side / 22))
            for offset in range(step, int(side), step):
                painter.drawLine(int(x0 + offset), int(y0 + 8), int(x0 + offset), int(y0 + side - 8))
                painter.drawLine(int(x0 + 8), int(y0 + offset), int(x0 + side - 8), int(y0 + offset))
        if self.show_reticle or self.show_reticle_modulation:
            step = max(4, int(side / 22))
            cell_x = step * max(1, int(getattr(self, "reticle_width", 1)))
            cell_y = step * max(1, int(getattr(self, "reticle_height", 1)))
            if self.show_reticle_modulation:
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(70, 130, 200, 45))
                column = 0
                left = int(x0)
                while left < x0 + side:
                    row = 0
                    top = int(y0)
                    while top < y0 + side:
                        if (column + row) % 2 == 0:
                            painter.drawRect(left, top, int(cell_x), int(cell_y))
                        top += int(cell_y)
                        row += 1
                    left += int(cell_x)
                    column += 1
            if self.show_reticle:
                painter.setPen(QPen(QColor("#3d6ea8"), 2))
                painter.setBrush(Qt.NoBrush)
                offset = int(cell_x)
                while offset < side:
                    painter.drawLine(int(x0 + offset), int(y0), int(x0 + offset), int(y0 + side))
                    offset += int(cell_x)
                offset = int(cell_y)
                while offset < side:
                    painter.drawLine(int(x0), int(y0 + offset), int(x0 + side), int(y0 + offset))
                    offset += int(cell_y)
        for defect in ([] if not self.show_defects else self._marks()):
            px = x0 + side / 2 + float(defect.get("x", 0.0)) * side / 2
            py = y0 + side / 2 - float(defect.get("y", 0.0)) * side / 2
            selected = defect.get("id") == self.selected_id
            marked = defect.get("marked")
            secondary = (int(defect.get("die_x", 0)), int(defect.get("die_y", 0))) in self.secondary_dies
            color, shape = self._defect_style(defect)
            painter.setPen(QPen(QColor("#202020"), max(1, int(mark * 0.25))))
            painter.setBrush(
                QColor("#ffe13d") if selected else QColor("#15a85d") if marked else QColor("#4c7fd4") if secondary else QColor(color)
            )
            radius = mark * (1.7 if selected else 1.0)
            if shape in ("Square", "Rectangle"):
                painter.drawRect(int(px - radius), int(py - radius), int(radius * 2), int(radius * 2))
            elif shape == "Diamond":
                painter.drawRect(int(px - radius), int(py - radius), int(radius * 2), int(radius * 2))
                painter.drawLine(int(px - radius), int(py), int(px), int(py - radius))
                painter.drawLine(int(px), int(py - radius), int(px + radius), int(py))
            else:
                painter.drawEllipse(int(px - radius), int(py - radius), int(radius * 2), int(radius * 2))
            if selected:
                painter.setPen(QPen(QColor("#111111"), max(1, int(mark * 0.35))))
                painter.drawLine(int(px - radius * 1.8), int(py), int(px + radius * 1.8), int(py))
                painter.drawLine(int(px), int(py - radius * 1.8), int(px), int(py + radius * 1.8))
            if self.show_counts:
                painter.setPen(QColor("#111111"))
                painter.drawText(
                    int(px + radius),
                    int(py - radius),
                    str(defect.get("stack_count", defect.get("id", ""))),
                )
            if self.show_selected_crosshair and defect.get("id") in self.selected_ids:
                painter.setPen(QPen(QColor("#111111"), max(1, int(mark * 0.35))))
                painter.drawLine(int(px - mark * 1.6), int(py), int(px + mark * 1.6), int(py))
                painter.drawLine(int(px), int(py - mark * 1.6), int(px), int(py + mark * 1.6))
        if self.show_marker:
            stage_x = x0 + side / 2
            stage_y = y0 + side * 0.18
            painter.setPen(QPen(QColor("#1a1a1a"), max(1, int(mark * 0.4))))
            painter.setBrush(Qt.NoBrush)
            painter.drawLine(int(stage_x - mark * 1.5), int(stage_y), int(stage_x + mark * 1.5), int(stage_y))
            painter.drawLine(int(stage_x), int(stage_y - mark * 1.5), int(stage_x), int(stage_y + mark * 1.5))
        if self.show_partial_die:
            painter.setPen(QPen(QColor("#2f9e4f"), 2))
            painter.setBrush(Qt.NoBrush)
            inset = side * 0.08
            painter.drawEllipse(int(x0 + inset), int(y0 + inset), int(side - inset * 2), int(side - inset * 2))
        if self.show_care_areas:
            painter.setPen(QPen(QColor("#c45a12"), 1))
            painter.setBrush(QColor(255, 196, 64, 70))
            for rect in self.care_rects:
                left, top, width, height = [float(value) for value in rect[:4]]
                painter.drawRect(
                    int(x0 + left * side),
                    int(y0 + top * side),
                    max(2, int(width * side)),
                    max(2, int(height * side)),
                )
            painter.setPen(QPen(QColor("#2a6fbf"), 1))
            painter.setBrush(QColor(80, 150, 230, 70))
            for rect in self.dont_care_rects:
                left, top, width, height = [float(value) for value in rect[:4]]
                painter.drawRect(
                    int(x0 + left * side),
                    int(y0 + top * side),
                    max(2, int(width * side)),
                    max(2, int(height * side)),
                )
        for mx, my in self.location_marks:
            mark_x = x0 + side / 2 + float(mx) * side / 2
            mark_y = y0 + side / 2 - float(my) * side / 2
            painter.setPen(QPen(QColor("#7a2ea8"), max(2, int(mark * 0.45))))
            painter.drawLine(int(mark_x - mark * 2), int(mark_y), int(mark_x + mark * 2), int(mark_y))
            painter.drawLine(int(mark_x), int(mark_y - mark * 2), int(mark_x), int(mark_y + mark * 2))
        if self.show_legend:
            painter.setPen(QPen(QColor("#6e6a62"), 1))
            painter.setBrush(QColor("#f7f4ea"))
            painter.drawRect(8, 8, 118, 62)
            painter.setPen(QColor("#202020"))
            painter.drawText(16, 24, "Legend")
            for index, (color, label) in enumerate((
                ("#d62d2d", "Defect"),
                ("#15a85d", "Marked"),
                ("#ffe13d", "Selected"),
            )):
                painter.setBrush(QColor(color))
                painter.drawRect(16, 32 + index * 12, 10, 8)
                painter.drawText(32, 40 + index * 12, label)
        if self.show_overview:
            box = 92
            ox, oy = self.width() - box - 10, self.height() - box - 10
            painter.setPen(QPen(QColor("#6e6a62"), 1))
            painter.setBrush(QColor("#f7f4ea"))
            painter.drawRect(ox, oy, box, box)
            painter.setBrush(QColor("#d7d4cc"))
            painter.drawEllipse(ox + 8, oy + 8, box - 16, box - 16)
            current = next((item for item in self.defects if item.get("id") == self.selected_id), None)
            if current is not None:
                painter.setBrush(QColor("#d62d2d"))
                painter.drawEllipse(
                    int(ox + box / 2 + float(current.get("x", 0.0)) * (box - 16) / 2 - 2),
                    int(oy + box / 2 - float(current.get("y", 0.0)) * (box - 16) / 2 - 2),
                    4,
                    4,
                )
            view = max(4.0, (box - 16) / max(self.zoom_factor, 0.5))
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor("#1d4f9c"), 1))
            painter.drawRect(
                int(ox + box / 2 - view / 2 + self.view_center[0] * (box - 16) / 2),
                int(oy + box / 2 - view / 2 - self.view_center[1] * (box - 16) / 2),
                int(view),
                int(view),
            )
        if self.drag_start and self.drag_end and self.interaction != "pan":
            x1, y1 = self.drag_start
            x2, y2 = self.drag_end
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor("#202020"), 1))
            painter.drawRect(int(min(x1, x2)), int(min(y1, y2)), int(abs(x2 - x1)), int(abs(y2 - y1)))
        painter.end()

    def _defect_style(self, defect):
        values = {
            "Added": bool(defect.get("added") or defect.get("manually_added")),
            "Sample": bool(defect.get("sampled") or defect.get("sampled_review")),
            "Repeater": bool(defect.get("repeater") or defect.get("repeater_id")),
            "Cluster": bool(defect.get("cluster_id")),
            "Clustered": bool(defect.get("cluster_id")),
            "Flag_PatchImage": bool(defect.get("has_patch_image")),
            "Flag_HRDC": bool(defect.get("hrdc") or defect.get("flag_hrdc")),
            "iADCCamera": bool(defect.get("iadc_camera") or defect.get("has_iadc_image")),
            "Marked": bool(defect.get("marked")),
            "Reviewed": bool(defect.get("reviewed")),
            "Dark": defect.get("polarity") == "Dark",
        }
        for rule in self.display_rules:
            if rule.get("enabled") and values.get(rule.get("rule")) == bool(rule.get("state", True)):
                return rule.get("color", "#1a3f86"), rule.get("shape", "Rectangle")
        return "#d62d2d", "Ellipse"

    def _marks(self):
        defects = list(self.defects)
        if self.display_mode in ("Die Stack", "Reticle Stack") and defects:
            current = next((item for item in defects if item.get("id") == self.selected_id), defects[0])
            if self.display_mode == "Die Stack":
                die = (int(current.get("die_x", 0)), int(current.get("die_y", 0)))
                defects = [
                    item for item in defects
                    if (int(item.get("die_x", 0)), int(item.get("die_y", 0))) == die
                ]
            else:
                width = max(1, int(getattr(self, "reticle_width", 1)))
                height = max(1, int(getattr(self, "reticle_height", 1)))
                field = (int(current.get("die_x", 0)) // width, int(current.get("die_y", 0)) // height)
                defects = [
                    item for item in defects
                    if (int(item.get("die_x", 0)) // width, int(item.get("die_y", 0)) // height) == field
                ]
        if not self.stack_defects:
            return defects
        groups = {}
        tolerance_x = float(getattr(self, "stack_tolerance_x", 0.0) or 0.0)
        tolerance_y = float(getattr(self, "stack_tolerance_y", 0.0) or 0.0)
        for defect in defects:
            die = (int(defect.get("die_x", 0)), int(defect.get("die_y", 0)))
            if tolerance_x > 0 or tolerance_y > 0:
                bucket = (
                    die,
                    round(float(defect.get("x", 0.0)) / tolerance_x) if tolerance_x else 0,
                    round(float(defect.get("y", 0.0)) / tolerance_y) if tolerance_y else 0,
                )
            else:
                bucket = die
            groups.setdefault(bucket, []).append(defect)
        stacked = []
        for items in groups.values():
            mark = dict(items[0])
            mark["x"] = sum(float(item.get("x", 0.0)) for item in items) / len(items)
            mark["y"] = sum(float(item.get("y", 0.0)) for item in items) / len(items)
            mark["stack_count"] = len(items)
            stacked.append(mark)
        return stacked

    def _zoom_to_rect(self, x1, y1, x2, y2):
        x0, y0, side = self._geometry()
        if side <= 1:
            return

        def wafer_point(px, py):
            return ((px - x0) / side * 2 - 1, 1 - (py - y0) / side * 2)

        left, right = sorted((x1, x2))
        top, bottom = sorted((y1, y2))
        wx1, wy1 = wafer_point(left, bottom)
        wx2, wy2 = wafer_point(right, top)
        span = max(abs(wx2 - wx1), abs(wy2 - wy1), 0.08)
        self.zoom_factor = max(0.5, min(12.0, 2.0 / span))
        self.view_center = ((wx1 + wx2) / 2, (wy1 + wy2) / 2)
        self._clamp_view_center()
        if self.on_zoom_changed:
            self.on_zoom_changed(self.zoom_factor)
        self.update()

    def _event_point(self, event):
        point = event.position() if hasattr(event, "position") else event.pos()
        return point.x(), point.y()

    def _nearest_defect(self, px, py):
        if not self.defects:
            return None
        x0, y0, side = self._geometry()

        def distance(defect):
            dx = x0 + side / 2 + float(defect.get("x", 0.0)) * side / 2 - px
            dy = y0 + side / 2 - float(defect.get("y", 0.0)) * side / 2 - py
            return dx * dx + dy * dy

        return min(self.defects, key=distance)

    def _show_die_tooltip(self, event, px, py):
        x0, y0, side = self._geometry()
        if side <= 1 or px < x0 or py < y0 or px > x0 + side or py > y0 + side:
            QToolTip.hideText()
            return
        wafer_x = (px - x0) / side * 2 - 1
        wafer_y = 1 - (py - y0) / side * 2
        position_x = wafer_x * 150000.0
        position_y = wafer_y * 150000.0
        pitch_x = float(self.die_pitch_x or 5100.0)
        pitch_y = float(self.die_pitch_y or 16600.0)
        column = int(position_x // pitch_x)
        row = int(position_y // pitch_y)
        die_x = position_x - column * pitch_x
        die_y = position_y - row * pitch_y
        if hasattr(event, "globalPosition"):
            global_pos = event.globalPosition().toPoint()
        else:
            global_pos = event.globalPos()
        QToolTip.showText(
            global_pos,
            f"Wafer Position (X,Y): ({position_x:.1f}, {position_y:.1f})\n"
            f"Die Index (Row, Column): ({row}, {column})\n"
            f"Die Position (X,Y): ({die_x:.1f}, {die_y:.1f})",
            self,
        )

    def mousePressEvent(self, event):
        px, py = self._event_point(event)
        button = event.button() if hasattr(event, "button") else Qt.LeftButton
        modifiers = event.modifiers() if hasattr(event, "modifiers") else Qt.NoModifier
        if button == Qt.MiddleButton:
            # Middle drag pans in every mode, so the map can be moved without
            # leaving the tool the user is working with.
            self._pan_last = (px, py)
            self._pan_cursor = self.cursor()
            self.drag_start = None
            self.setCursor(Qt.ClosedHandCursor)
            return
        if button == Qt.RightButton and self.interaction != "zoom":
            return
        if self.interaction == "pan" and button == Qt.LeftButton:
            self._pan_last = (px, py)
            self._pan_cursor = Qt.OpenHandCursor
            self.drag_start = None
            self.setCursor(Qt.ClosedHandCursor)
            return
        if not self.defects and self.interaction != "zoom":
            return
        self._zoom_drag = self.interaction == "zoom" or bool(modifiers & Qt.ControlModifier)
        self.drag_start = (px, py)
        self.drag_end = self.drag_start
        if self._zoom_drag:
            self.update()

    def mouseMoveEvent(self, event):
        point = event.position() if hasattr(event, "position") else event.pos()
        if self.show_tooltips and self._pan_last is None and self.drag_start is None:
            self._show_die_tooltip(event, point.x(), point.y())
        if self._pan_last is not None:
            dx = point.x() - self._pan_last[0]
            dy = point.y() - self._pan_last[1]
            self._pan_last = (point.x(), point.y())
            self.pan_by(dx, dy)
            return
        if self.drag_start is None:
            return
        self.drag_end = (point.x(), point.y())
        self.update()

    def mouseReleaseEvent(self, event):
        button = event.button() if hasattr(event, "button") else Qt.LeftButton
        if self._pan_last is not None:
            self._pan_last = None
            restore = getattr(self, "_pan_cursor", None)
            if restore is None or restore == Qt.ClosedHandCursor:
                self.unsetCursor()
            else:
                self.setCursor(restore)
            self._pan_cursor = None
            self.update()
            return
        if self.drag_start is None:
            return
        px, py = self._event_point(event)
        self.drag_end = (px, py)
        x1, y1 = self.drag_start
        x2, y2 = self.drag_end
        zoom_drag = self._zoom_drag
        self._zoom_drag = False
        self.drag_start = None
        self.drag_end = None
        if zoom_drag:
            if abs(x2 - x1) > 8 or abs(y2 - y1) > 8:
                self._zoom_to_rect(x1, y1, x2, y2)
            self.update()
            return
        if abs(x2 - x1) > 5 or abs(y2 - y1) > 5:
            x0, y0, side = self._geometry()
            left, right = sorted((x1, x2))
            top, bottom = sorted((y1, y2))
            identifiers = []
            for defect in self.defects:
                defect_x = x0 + side / 2 + float(defect.get("x", 0.0)) * side / 2
                defect_y = y0 + side / 2 - float(defect.get("y", 0.0)) * side / 2
                if left <= defect_x <= right and top <= defect_y <= bottom:
                    identifiers.append(defect.get("id"))
            if self.on_area_selected:
                self.on_area_selected(identifiers)
        elif self.on_clicked:
            self.on_clicked(x2, y2)
        self.update()

    def mouseDoubleClickEvent(self, event):
        if self.interaction != "select":
            return
        px, py = self._event_point(event)
        nearest = self._nearest_defect(px, py)
        if nearest is not None and self.on_select_toggle:
            self.on_select_toggle(nearest.get("id"))


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
        self.show_ruler = False
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
        if self.show_ruler:
            painter.setPen(QPen(QColor("#f2f2f2"), 1))
            box = max(18, int(28 * self.zoom))
            painter.drawRect(cx - box, cy - box // 2, box * 2, box)
            painter.drawText(cx - box, cy + box // 2 + 14, f"{box * 2} px")
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
        self.y_cut_lines = []
        self.title = "Defects by Class Code"
        self.chart_type = "Bar"
        self.scale_mode = "Linear"
        self.show_grid = False
        self.show_legend = False
        self.group_size = 1
        self.zoom = 1.0
        self.point_marker = "circle"
        self.point_colors = None
        self.legend_items = []
        self.partition_series = None
        self.partition_bins = []
        self.ordered_labels = None
        self.axis_x = ""
        self.axis_y = ""
        self.y_labels = None
        self.bar_color = None
        self.raw_values = []
        self.view_min = None
        self.view_max = None
        self.full_min = 0.0
        self.full_max = 1.0
        self.tool = "select"
        self.density = True
        self.interaction = False
        self.region_labels_on = True
        self.region_names = {}
        self.region_groups = {}
        self.selected_regions = set()
        self._region_label_rects = []
        self.selected_cut = None
        self.selected_y_cut = None
        self.history = []
        self.future = []
        self._plot_box = None
        self._scatter_box = None
        self._press = None
        self._rubber = None
        self._cut_preview = None
        self._dragging_cut = None
        self._dragging_y_cut = None
        self.raw_colors = None
        self.suppress_legend = False
        self.on_place_cut = None
        self.on_move_cut = None
        self.on_select_cut = None
        self.on_place_y_cut = None
        self.on_move_y_cut = None
        self.on_select_y_cut = None
        self.on_select_region = None
        self.on_view_changed = None
        self.setMinimumSize(260, 120)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)

    def set_counts(self, counts, title=None, chart_type="Bar", ordered_labels=None, axis_x="", axis_y="", bar_color=None):
        self.counts = dict(counts)
        self.points = []
        self.partition_series = None
        self.point_colors = None
        self.legend_items = []
        self.y_labels = None
        self.ordered_labels = list(ordered_labels) if ordered_labels else None
        self.axis_x = axis_x or ""
        self.axis_y = axis_y or ""
        self.bar_color = bar_color
        self.chart_type = chart_type
        if title is not None:
            self.title = title
        self.update()

    def set_points(self, points, title=None, marker="circle", colors=None, legend_items=None, y_labels=None, axis_x="", axis_y=""):
        self.points = list(points)
        self.counts = {}
        self.partition_series = None
        self.ordered_labels = None
        self.bar_color = None
        self.chart_type = "Scatter"
        self.point_marker = marker
        self.point_colors = list(colors) if colors else None
        self.legend_items = list(legend_items or [])
        self.y_labels = list(y_labels) if y_labels else None
        self.axis_x = axis_x or ""
        self.axis_y = axis_y or ""
        if title is not None:
            self.title = title
        self.update()

    def set_partition_bars(self, bins, series, title=None):
        self.partition_bins = list(bins)
        self.partition_series = list(series)
        self.counts = {}
        self.points = []
        self.chart_type = "Partition"
        self.legend_items = [(item.get("name", ""), item.get("color", "#888888")) for item in series]
        if title:
            self.title = title
        self.update()

    def set_curve(self, points, cut=None, title=None):
        self.points = list(points)
        self.counts = {}
        self.partition_series = None
        self.point_colors = None
        self.legend_items = []
        self.chart_type = "Line"
        self.point_marker = "circle"
        self.cut_lines = [] if cut is None else [float(cut)]
        if title is not None:
            self.title = title
        self.update()

    def set_cut_lines(self, values):
        self.cut_lines = [float(value) for value in values]
        self.update()

    def set_y_cut_lines(self, values):
        self.y_cut_lines = [float(value) for value in values]
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

    def set_needle(self, values, axis_x="", axis_y="Defect Count", reset_view=False, colors=None):
        self.raw_values = [float(value) for value in values]
        self.raw_colors = list(colors) if colors and len(colors) == len(self.raw_values) else None
        self.counts = {}
        self.points = []
        self.partition_series = None
        self.ordered_labels = None
        self.y_labels = None
        self.chart_type = "Needle"
        self.axis_x = axis_x or ""
        self.axis_y = axis_y or "Defect Count"
        self.title = ""
        if self.raw_values:
            low, high = min(self.raw_values), max(self.raw_values)
            pad = (high - low) * 0.04 or 1.0
            self.full_min = low - pad
            self.full_max = high + pad
        else:
            self.full_min, self.full_max = 0.0, 1.0
        if reset_view or self.view_min is None or self.view_max is None:
            self.view_min, self.view_max = self.full_min, self.full_max
            self.history = []
            self.future = []
            self.selected_regions = set()
            self.selected_cut = None
        self.update()
        self._notify_view()

    def _tx(self, value):
        if self.scale_mode in ("Log", "Log X"):
            return math.log1p(max(0.0, float(value)))
        return float(value)

    def _value_to_px(self, value, left, right, view_min, view_max):
        start, end = self._tx(view_min), self._tx(view_max)
        span = end - start or 1.0
        return left + (self._tx(value) - start) / span * (right - left)

    def _px_to_value(self, px, left, right, view_min, view_max):
        start, end = self._tx(view_min), self._tx(view_max)
        span = end - start or 1.0
        mapped = start + (px - left) / max(1.0, right - left) * span
        if self.scale_mode in ("Log", "Log X"):
            return max(0.0, math.expm1(mapped))
        return mapped

    def _push_view(self):
        self.history.append((self.view_min, self.view_max))
        if len(self.history) > 30:
            self.history.pop(0)
        self.future = []

    def _clamp_view(self):
        full = (self.full_max - self.full_min) or 1.0
        minimum = full / 200.0 or 1e-6
        span = min(max(self.view_max - self.view_min, minimum), full * 4.0)
        mid = (self.view_min + self.view_max) / 2.0
        limit_min = self.full_min - span
        limit_max = self.full_max + span
        mid = min(max(mid, limit_min + span / 2.0), limit_max - span / 2.0)
        self.view_min = mid - span / 2.0
        self.view_max = mid + span / 2.0

    def _notify_view(self):
        if self.on_view_changed:
            self.on_view_changed()

    def zoom_in(self):
        if self.view_min is None:
            return
        self._push_view()
        mid = (self.view_min + self.view_max) / 2.0
        half = (self.view_max - self.view_min) / 2.0 * 0.7
        self.view_min, self.view_max = mid - half, mid + half
        self._clamp_view()
        self.update()
        self._notify_view()

    def zoom_out(self):
        if self.view_min is None:
            return
        self._push_view()
        mid = (self.view_min + self.view_max) / 2.0
        half = (self.view_max - self.view_min) / 2.0 / 0.7
        self.view_min, self.view_max = mid - half, mid + half
        self._clamp_view()
        self.update()
        self._notify_view()

    def zoom_fit(self):
        if self.view_min is None:
            return
        self._push_view()
        self.view_min, self.view_max = self.full_min, self.full_max
        self.update()
        self._notify_view()

    def view_back(self):
        if not self.history:
            return
        self.future.append((self.view_min, self.view_max))
        self.view_min, self.view_max = self.history.pop()
        self.update()
        self._notify_view()

    def view_forward(self):
        if not self.future:
            return
        self.history.append((self.view_min, self.view_max))
        self.view_min, self.view_max = self.future.pop()
        self.update()
        self._notify_view()

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

    def _paint_legend_box(self, painter, top):
        if self.suppress_legend or not self.legend_items:
            return
        legend_x = self.width() - 88
        painter.setPen(QColor("#202020"))
        painter.setBrush(QColor("#ffffff"))
        painter.drawRoundedRect(legend_x - 6, top - 4, 84, 18 + 16 * len(self.legend_items), 4, 4)
        painter.drawText(legend_x, top + 10, "Partitions")
        for index, (name, color) in enumerate(self.legend_items):
            y = top + 28 + index * 16
            painter.setBrush(QColor(color))
            painter.setPen(QColor("#333333"))
            painter.drawEllipse(legend_x, y - 9, 9, 9)
            painter.drawText(legend_x + 14, y, str(name)[:10])

    def _paint_partition_histogram(self, painter):
        bins = self.partition_bins
        series = self.partition_series
        if not bins or not series:
            painter.drawText(self.rect(), Qt.AlignCenter, "No visible defects")
            return
        left, top, right, bottom = 36, 36, self.width() - 100, self.height() - 36
        width = max(1, right - left)
        height = max(1, bottom - top)
        totals = []
        for label in bins:
            totals.append(sum(int(item.get("counts", {}).get(label, 0)) for item in series))
        maximum = max(totals) or 1
        bar_width = max(2, width // max(1, len(bins)))
        painter.setPen(QColor("#9a9a94"))
        painter.drawLine(left, bottom, right, bottom)
        painter.drawLine(left, top, left, bottom)
        for index, label in enumerate(bins):
            x = left + index * bar_width
            y = bottom
            for item in series:
                count = int(item.get("counts", {}).get(label, 0))
                if count <= 0:
                    continue
                bar_height = int(height * count / maximum)
                y -= bar_height
                painter.fillRect(x, y, max(1, bar_width - 1), bar_height, QColor(item.get("color", "#888888")))
        painter.save()
        painter.translate(14, (top + bottom) / 2)
        painter.rotate(-90)
        painter.setPen(QColor("#202020"))
        painter.drawText(-40, 0, "Defect Count")
        painter.restore()
        painter.setPen(QColor("#202020"))
        painter.drawText(left, self.height() - 8, str(bins[0]))
        painter.drawText(right - 48, self.height() - 8, str(bins[-1]))
        painter.drawText(left + width // 2 - 40, self.height() - 8, self.title)
        self.legend_items = [(item.get("name", ""), item.get("color", "#888888")) for item in series]
        self._paint_legend_box(painter, top)

    def paintEvent(self, event):
        painter = QPainter(self)
        if self.chart_type == "Needle":
            self._paint_needle(painter)
            painter.end()
            return
        painter.fillRect(self.rect(), QColor("#efefeb"))
        painter.setPen(QColor("#202020"))
        painter.drawText(10, 18, self.title)
        if self.chart_type == "Partition" and self.partition_series:
            self._paint_partition_histogram(painter)
            painter.end()
            return
        if not self.counts and not self.points:
            painter.drawText(self.rect(), Qt.AlignCenter, "No visible defects")
            painter.end()
            return
        if self.points:
            legend_width = 92 if self.legend_items else 0
            left_margin = 78 if self.y_labels or self.axis_y else 32
            left, top, right, bottom = left_margin, 30, self.width() - 18 - legend_width, self.height() - 36
            width = max(1, right - left)
            height = max(1, bottom - top)
            xs = [float(point[0]) for point in self.points]
            ys = [float(point[1]) for point in self.points]
            if self.scale_mode in ("Log", "Log X"):
                xs = [math.log1p(max(0.0, value)) for value in xs]
            if self.y_labels:
                minimum_y, maximum_y = -0.5, max(0.5, len(self.y_labels) - 0.5)
            else:
                if self.scale_mode in ("Log", "Log Y"):
                    ys = [math.log1p(max(0.0, value)) for value in ys]
                minimum_y, maximum_y = min(ys), max(ys)
            minimum_x, maximum_x = min(xs), max(xs)
            range_x = maximum_x - minimum_x or 1.0
            range_y = maximum_y - minimum_y or 1.0
            self._scatter_box = (
                left, top, right, bottom,
                minimum_x, maximum_x, minimum_y, maximum_y,
            )
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
            if self.chart_type == "Line":
                painter.setPen(QPen(QColor("#3c9a45"), 2))
                previous = None
                for x_value, y_value in zip(xs, ys):
                    x = left + int((x_value - minimum_x) * width / range_x)
                    y = bottom - int((y_value - minimum_y) * height / range_y)
                    if previous is not None:
                        painter.drawLine(previous[0], previous[1], x, y)
                    previous = (x, y)
            else:
                for index, (x_value, y_value) in enumerate(zip(xs, ys)):
                    color = QColor("#1d4d24")
                    if self.point_colors and index < len(self.point_colors):
                        color = QColor(self.point_colors[index])
                    painter.setPen(color)
                    painter.setBrush(color)
                    x = left + int((x_value - minimum_x) * width / range_x)
                    y = bottom - int((y_value - minimum_y) * height / range_y)
                    if self.point_marker == "triangle":
                        painter.drawLine(x, y - 4, x - 4, y + 3)
                        painter.drawLine(x - 4, y + 3, x + 4, y + 3)
                        painter.drawLine(x + 4, y + 3, x, y - 4)
                    else:
                        painter.drawEllipse(x - 2, y - 2, 5, 5)
            painter.setPen(QPen(QColor("#c63f36"), 2))
            x_cuts = sorted(self.cut_lines)
            y_cuts = sorted(self.y_cut_lines)
            for index, value in enumerate(x_cuts):
                transformed = math.log1p(max(0.0, value)) if self.scale_mode in ("Log", "Log X") else value
                x = left + int((transformed - minimum_x) * width / range_x)
                if left <= x <= right:
                    painter.setPen(QPen(
                        QColor("#202020") if index == self.selected_cut else QColor("#c63f36"),
                        2 if index == self.selected_cut else 1,
                        Qt.SolidLine if index == self.selected_cut else Qt.DashLine,
                    ))
                    painter.drawLine(x, top, x, bottom)
            if not self.y_labels:
                for index, value in enumerate(y_cuts):
                    transformed = math.log1p(max(0.0, value)) if self.scale_mode in ("Log", "Log Y") else value
                    y = bottom - int((transformed - minimum_y) * height / range_y)
                    if top <= y <= bottom:
                        painter.setPen(QPen(
                            QColor("#202020") if index == self.selected_y_cut else QColor("#c63f36"),
                            2 if index == self.selected_y_cut else 1,
                            Qt.SolidLine if index == self.selected_y_cut else Qt.DashLine,
                        ))
                        painter.drawLine(left, y, right, y)
            if self._cut_preview is not None:
                painter.setPen(QPen(QColor("#9a1c1c"), 1))
                if self._dragging_y_cut is not None:
                    transformed = (
                        math.log1p(max(0.0, self._cut_preview))
                        if self.scale_mode in ("Log", "Log Y") else self._cut_preview
                    )
                    y = bottom - int((transformed - minimum_y) * height / range_y)
                    painter.drawLine(left, y, right, y)
                elif self._dragging_cut is not None:
                    transformed = (
                        math.log1p(max(0.0, self._cut_preview))
                        if self.scale_mode in ("Log", "Log X") else self._cut_preview
                    )
                    x = left + int((transformed - minimum_x) * width / range_x)
                    painter.drawLine(x, top, x, bottom)
            if self.region_labels_on and (x_cuts or y_cuts) and not self.y_labels:
                x_bounds = [minimum_x] + [
                    math.log1p(max(0.0, value)) if self.scale_mode in ("Log", "Log X") else value
                    for value in x_cuts
                ] + [maximum_x]
                y_bounds = [minimum_y] + [
                    math.log1p(max(0.0, value)) if self.scale_mode in ("Log", "Log Y") else value
                    for value in y_cuts
                ] + [maximum_y]
                keys = []
                for y_index in range(len(y_bounds) - 1):
                    for x_index in range(len(x_bounds) - 1):
                        region = y_index * (len(x_bounds) - 1) + x_index
                        explicit = (self.region_groups or {}).get(str(region))
                        key = ("group", explicit) if explicit is not None else ("region", region)
                        if key not in keys:
                            keys.append(key)
                        group_number = keys.index(key) + 1
                        x0 = left + int((x_bounds[x_index] - minimum_x) * width / range_x)
                        x1 = left + int((x_bounds[x_index + 1] - minimum_x) * width / range_x)
                        y0 = bottom - int((y_bounds[y_index + 1] - minimum_y) * height / range_y)
                        y1 = bottom - int((y_bounds[y_index] - minimum_y) * height / range_y)
                        painter.setPen(QColor("#202020"))
                        display_label = str(
                            (self.region_names or {}).get(str(region))
                            or f"Group {group_number}"
                        )
                        painter.drawText(
                            min(x0, x1), min(y0, y1), max(18, abs(x1 - x0)), max(16, abs(y1 - y0)),
                            Qt.AlignCenter, display_label,
                        )
            painter.setPen(QColor("#202020"))
            if self.y_labels:
                for index, label in enumerate(self.y_labels):
                    y = bottom - int((index - minimum_y) * height / range_y)
                    painter.drawText(4, y - 8, left - 8, 16, Qt.AlignRight | Qt.AlignVCenter, str(label))
                    painter.setPen(QColor("#d0d0cb"))
                    painter.drawLine(left, y, right, y)
                    painter.setPen(QColor("#202020"))
            else:
                painter.drawText(4, top + 5, f"{maximum_y:g}")
            painter.drawText(left, self.height() - 8, f"{minimum_x:g}")
            painter.drawText(right - 45, self.height() - 8, f"{maximum_x:g}")
            if self.axis_x:
                painter.drawText(left, self.height() - 20, right - left, 14, Qt.AlignCenter, self.axis_x)
            if self.axis_y:
                painter.save()
                painter.translate(12, (top + bottom) / 2)
                painter.rotate(-90)
                painter.drawText(-40, 0, self.axis_y)
                painter.restore()
            self._paint_legend_box(painter, top)
            painter.end()
            return
        if self.ordered_labels:
            items = [(label, self.counts.get(label, 0)) for label in self.ordered_labels]
        else:
            items = sorted(
                self.counts.items(),
                key=(lambda item: (-item[1], str(item[0]))) if self.chart_type == "Pareto" else (lambda item: str(item[0])),
            )
        transformed = {
            code: math.log1p(count) if self.scale_mode in ("Log", "Log Y") else count
            for code, count in items
        }
        if not items:
            painter.end()
            return
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
            color = self.bar_color or (colors[index % len(colors)] if self.chart_type in ("Stacked", "Side by Side") else "#2d7487")
            fill_width = max(4, bar_width - 4) if self.bar_color else max(4, min(bar_width - 3, (bar_width - 5) * self.group_size // 3))
            painter.fillRect(x, y, fill_width, height, QColor(color))
            painter.setPen(QColor("#202020"))
            if len(items) <= 8:
                painter.drawText(x, self.height() - 31, max(12, bar_width), 16, Qt.AlignLeft, str(code)[:12])
            elif index in (0, len(items) - 1):
                painter.drawText(x, self.height() - 31, str(code))
            if not self.axis_y:
                painter.drawText(x, max(32, y - 3), str(count))
        if self.show_legend:
            legend_x = self.width() - legend_width + 8
            painter.drawText(legend_x, 18, "Legend")
            for index, (code, _count) in enumerate(items[:6]):
                y = 36 + index * 16
                color = ["#2d7487", "#a55b45", "#648447", "#8a6d9b"][index % 4]
                painter.fillRect(legend_x, y - 9, 10, 10, QColor(color))
                painter.drawText(legend_x + 15, y, str(code)[:14])
        if self.axis_y:
            painter.setPen(QColor("#202020"))
            painter.drawText(2, baseline, "0")
            painter.drawText(2, baseline - chart_height, str(max(count for _code, count in items) if items else 0))
            painter.save()
            painter.translate(12, baseline - chart_height / 2)
            painter.rotate(-90)
            painter.drawText(-36, 0, self.axis_y)
            painter.restore()
        if self.axis_x:
            painter.setPen(QColor("#202020"))
            painter.drawText(25, self.height() - 14, available_width, 14, Qt.AlignCenter, self.axis_x)
        painter.end()

    def _paint_needle(self, painter):
        painter.fillRect(self.rect(), QColor("#f3f1ea"))
        label_band = 44 if self.cut_lines else 28
        left, top = 54, 8
        right = max(left + 20, self.width() - 8)
        bottom = max(top + 20, self.height() - label_band)
        if self.view_min is None:
            painter.setPen(QColor("#202020"))
            painter.drawText(self.rect(), Qt.AlignCenter, "No visible defects" if not self.raw_values else "")
            return
        self._plot_box = (left, top, right, bottom)
        plot_w = right - left
        plot_h = bottom - top
        view_min, view_max = self.view_min, self.view_max
        painter.fillRect(left, top, plot_w, plot_h, QColor("#ffffff"))
        cuts = sorted(self.cut_lines)
        bounds = [view_min] + cuts + [view_max]
        # A selected range is the user's working selection for Group/Ungroup.
        # Paint it behind the histogram so the defect distribution stays legible.
        for index in sorted(self.selected_regions):
            if index < 0 or index + 1 >= len(bounds):
                continue
            vis_a = max(bounds[index], view_min)
            vis_b = min(bounds[index + 1], view_max)
            if vis_b <= vis_a:
                continue
            x0 = self._value_to_px(vis_a, left, right, view_min, view_max)
            x1 = self._value_to_px(vis_b, left, right, view_min, view_max)
            painter.fillRect(
                int(min(x0, x1)), top, max(1, int(abs(x1 - x0))), plot_h,
                QColor(92, 125, 224, 105),
            )
        start, end = self._tx(view_min), self._tx(view_max)
        span = end - start or 1.0
        bin_count = max(12, int(plot_w / max(1, self.group_size)))
        if not self.density:
            bin_count = max(12, min(80, plot_w // 6))
        bin_count = min(500, bin_count)
        palette = self.raw_colors or ["#161616"] * len(self.raw_values)
        bin_colors = [Counter() for _ in range(bin_count)]
        for value, color in zip(self.raw_values, palette):
            mapped = self._tx(value)
            if mapped < start or mapped > end:
                continue
            index = min(bin_count - 1, int((mapped - start) / span * bin_count))
            bin_colors[index][color] += 1
        counts = [sum(item.values()) for item in bin_colors]
        transformed = [math.log1p(count) if self.scale_mode in ("Log", "Log Y") else count for count in counts]
        maximum = max(transformed) or 1
        if self.show_grid:
            painter.setPen(QColor("#d5d5d0"))
            for step in range(1, 5):
                y = bottom - int(plot_h * step / 4)
                x = left + int(plot_w * step / 4)
                painter.drawLine(left, y, right, y)
                painter.drawLine(x, top, x, bottom)
        slot = plot_w / bin_count
        bar_w = max(1, min(slot, float(max(1, self.group_size))))
        for index, height_value in enumerate(transformed):
            bar_height = int(plot_h * height_value / maximum)
            if bar_height <= 0:
                continue
            x = left + int(index * slot)
            y = bottom
            total = counts[index] or 1
            for color, count in bin_colors[index].items():
                segment = max(1, int(bar_height * count / total))
                y -= segment
                painter.fillRect(x, y, int(bar_w), segment, QColor(color))
        for index, value in enumerate(cuts):
            x = self._value_to_px(value, left, right, view_min, view_max)
            if x < left - 1 or x > right + 1:
                continue
            pen = QPen(QColor("#202020") if index == self.selected_cut else QColor("#5f5f5f"), 1)
            pen.setStyle(Qt.SolidLine if index == self.selected_cut else Qt.DashLine)
            painter.setPen(pen)
            painter.drawLine(int(x), top, int(x), bottom)
        if self._cut_preview is not None:
            x = self._value_to_px(self._cut_preview, left, right, view_min, view_max)
            painter.setPen(QPen(QColor("#9a1c1c"), 1))
            painter.drawLine(int(x), top, int(x), bottom)
        painter.setPen(QColor("#202020"))
        painter.drawLine(left, bottom, right, bottom)
        painter.drawLine(left, top, left, bottom)
        painter.drawText(4, bottom - 2, "0")
        painter.drawText(4, top + 12, str(max(counts) if counts else 0))
        mid = max(counts) // 2 if counts else 0
        if mid:
            painter.drawText(4, top + plot_h // 2, str(mid))
        painter.save()
        painter.translate(16, (top + bottom) / 2)
        painter.rotate(-90)
        painter.drawText(-70, -6, 140, 16, Qt.AlignCenter, self.axis_y or "Defect Count")
        painter.restore()
        for step in range(5):
            value = view_min + (view_max - view_min) * step / 4.0
            if self.scale_mode in ("Log", "Log X"):
                value = self._px_to_value(left + plot_w * step / 4.0, left, right, view_min, view_max)
            x = left + int(plot_w * step / 4.0)
            painter.drawText(x - 24, bottom + 2, 48, 14, Qt.AlignCenter, f"{value:.4g}")
        self._region_label_rects = []
        if cuts:
            bold = QFont(painter.font())
            bold.setBold(True)
            group_numbers = {}
            for region in range(len(bounds) - 1):
                explicit = (self.region_groups or {}).get(str(region))
                key = ("group", explicit) if explicit is not None else ("region", region)
                if key not in group_numbers:
                    group_numbers[key] = len(group_numbers) + 1
            for index in range(len(bounds) - 1):
                vis_a = max(bounds[index], view_min)
                vis_b = min(bounds[index + 1], view_max)
                if vis_b <= vis_a:
                    continue
                x0 = self._value_to_px(vis_a, left, right, view_min, view_max)
                x1 = self._value_to_px(vis_b, left, right, view_min, view_max)
                rect = (
                    int(min(x0, x1)), bottom + 14,
                    max(12, int(abs(x1 - x0))), 16,
                )
                self._region_label_rects.append((index, rect))
                if index == 0:
                    label = f"< {cuts[0]:.2f}"
                elif index == len(cuts):
                    label = f"≥ {cuts[-1]:.2f}"
                else:
                    label = f"≥ {cuts[index - 1]:.2f}  < {cuts[index]:.2f}"
                painter.setFont(bold)
                painter.setPen(QColor("#1a1a1a"))
                painter.drawText(*rect, Qt.AlignCenter, label)
                if self.region_labels_on:
                    explicit = (self.region_groups or {}).get(str(index))
                    key = ("group", explicit) if explicit is not None else ("region", index)
                    group_label = str(
                        (self.region_names or {}).get(str(index))
                        or f"Group {group_numbers[key]}"
                    )
                    painter.drawText(
                        rect[0], top + max(4, plot_h // 3), rect[2], 18,
                        Qt.AlignCenter, group_label,
                    )
            painter.setFont(QFont())
        painter.drawText(left, self.height() - 16, plot_w, 14, Qt.AlignCenter, self.axis_x)
        if self._rubber:
            (x0, y0), (x1, y1) = self._rubber
            painter.setPen(QPen(QColor("#2f5f9f"), 1, Qt.DashLine))
            painter.setBrush(QColor(47, 95, 159, 40))
            painter.drawRect(int(min(x0, x1)), int(min(y0, y1)), int(abs(x1 - x0)), int(abs(y1 - y0)))

    def _event_xy(self, event):
        if hasattr(event, "position"):
            point = event.position()
            return float(point.x()), float(point.y())
        point = event.pos()
        return float(point.x()), float(point.y())

    def _cut_at(self, px, py=None):
        box = self._plot_box
        if not box or self.view_min is None:
            return None
        left, top, right, bottom = box
        if py is not None and not (top <= py <= bottom):
            return None
        best = None
        best_dist = 6.0
        for index, value in enumerate(sorted(self.cut_lines)):
            dist = abs(px - self._value_to_px(value, left, right, self.view_min, self.view_max))
            if dist <= best_dist:
                best = index
                best_dist = dist
        return best

    def _region_at(self, px):
        box = self._plot_box
        if not box or self.view_min is None:
            return None
        left, _top, right, _bottom = box
        value = self._px_to_value(px, left, right, self.view_min, self.view_max)
        cuts = sorted(self.cut_lines)
        for index, cut in enumerate(cuts):
            if value < cut:
                return index
        return len(cuts)

    def _region_label_at(self, px, py):
        for region, (x, y, width, height) in self._region_label_rects:
            if x <= px <= x + width and y <= py <= y + height:
                return region
        return None

    def _scatter_x_value(self, px):
        if not self._scatter_box:
            return None
        left, _top, right, _bottom, minimum, maximum, _min_y, _max_y = self._scatter_box
        transformed = minimum + (px - left) / max(1.0, right - left) * (maximum - minimum)
        return max(0.0, math.expm1(transformed)) if self.scale_mode in ("Log", "Log X") else transformed

    def _scatter_y_value(self, py):
        if not self._scatter_box:
            return None
        _left, top, _right, bottom, _min_x, _max_x, minimum, maximum = self._scatter_box
        transformed = minimum + (bottom - py) / max(1.0, bottom - top) * (maximum - minimum)
        return max(0.0, math.expm1(transformed)) if self.scale_mode in ("Log", "Log Y") else transformed

    def _scatter_cut_at(self, px, py):
        if not self._scatter_box:
            return None, None
        left, top, right, bottom, minimum_x, maximum_x, minimum_y, maximum_y = self._scatter_box
        width, height = max(1.0, right - left), max(1.0, bottom - top)
        for index, value in enumerate(sorted(self.cut_lines)):
            transformed = math.log1p(max(0.0, value)) if self.scale_mode in ("Log", "Log X") else value
            x = left + (transformed - minimum_x) / max(1e-9, maximum_x - minimum_x) * width
            if top <= py <= bottom and abs(px - x) <= 6:
                return "x", index
        if not self.y_labels:
            for index, value in enumerate(sorted(self.y_cut_lines)):
                transformed = math.log1p(max(0.0, value)) if self.scale_mode in ("Log", "Log Y") else value
                y = bottom - (transformed - minimum_y) / max(1e-9, maximum_y - minimum_y) * height
                if left <= px <= right and abs(py - y) <= 6:
                    return "y", index
        return None, None

    def _scatter_press(self, event, px, py):
        if not self._scatter_box:
            return
        left, top, right, bottom, *_limits = self._scatter_box
        if not (left <= px <= right and top <= py <= bottom):
            return
        if self.tool == "cut" and self.on_place_cut:
            self.on_place_cut(self._scatter_x_value(px))
            return
        if self.tool == "hcut" and not self.y_labels and self.on_place_y_cut:
            self.on_place_y_cut(self._scatter_y_value(py))
            return
        if self.tool == "select":
            axis, index = self._scatter_cut_at(px, py)
            if axis == "x":
                self.selected_cut = index
                self.selected_y_cut = None
                self._dragging_cut = index
                if self.on_select_cut:
                    self.on_select_cut(index)
            elif axis == "y":
                self.selected_y_cut = index
                self.selected_cut = None
                self._dragging_y_cut = index
                if self.on_select_y_cut:
                    self.on_select_y_cut(index)
            self.update()

    def mousePressEvent(self, event):
        if not self.interaction:
            return
        px, py = self._event_xy(event)
        self._press = (px, py)
        self._rubber = None
        self._cut_preview = None
        self._dragging_cut = None
        self._dragging_y_cut = None
        if self.chart_type == "Scatter":
            self._scatter_press(event, px, py)
            return
        if self.chart_type != "Needle":
            self._press = None
            return
        if self.tool == "select":
            cut = self._cut_at(px, py)
            if cut is not None:
                self.selected_cut = cut
                self._dragging_cut = cut
                if self.on_select_cut:
                    self.on_select_cut(cut)
            else:
                # Regions are selected through the bold numeric range below
                # the plot. Shift adds/removes a second region for grouping.
                region = self._region_label_at(px, py)
                if region is not None:
                    modifiers = event.modifiers() if hasattr(event, "modifiers") else Qt.NoModifier
                    if modifiers & Qt.ShiftModifier:
                        if region in self.selected_regions:
                            self.selected_regions.discard(region)
                        elif len(self.selected_regions) < 2:
                            self.selected_regions.add(region)
                    else:
                        self.selected_regions = {region}
                    if self.on_select_region:
                        self.on_select_region(region)
            self.update()
        elif self.tool == "cut":
            box = self._plot_box
            if box and self.on_place_cut:
                left, top, right, bottom = box
                if left <= px <= right and top <= py <= bottom:
                    self.on_place_cut(self._px_to_value(px, left, right, self.view_min, self.view_max))

    def mouseMoveEvent(self, event):
        if not self.interaction:
            return
        px, py = self._event_xy(event)
        if self.chart_type == "Scatter":
            if self._press is None:
                if self.tool == "select":
                    axis, _index = self._scatter_cut_at(px, py)
                    self.setCursor(
                        Qt.SizeHorCursor if axis == "x"
                        else Qt.SizeVerCursor if axis == "y"
                        else Qt.ArrowCursor
                    )
                return
            if self.tool == "select" and self._dragging_cut is not None:
                self._cut_preview = self._scatter_x_value(px)
                self.setCursor(Qt.SizeHorCursor)
            elif self.tool == "select" and self._dragging_y_cut is not None:
                self._cut_preview = self._scatter_y_value(py)
                self.setCursor(Qt.SizeVerCursor)
            return
        if self.chart_type != "Needle":
            return
        if self._press is None:
            if self.tool == "select":
                self.setCursor(Qt.SizeHorCursor if self._cut_at(px, py) is not None else Qt.ArrowCursor)
            return
        if self.tool == "zoom":
            self._rubber = (self._press, (px, py))
            self.update()
        elif self.tool == "scroll":
            box = self._plot_box
            if not box:
                return
            left, _top, right, _bottom = box
            shift = -(px - self._press[0]) / max(1.0, right - left) * (self.view_max - self.view_min)
            self.view_min += shift
            self.view_max += shift
            self._clamp_view()
            self._press = (px, py)
            self.update()
        elif self.tool == "select" and self._dragging_cut is not None:
            box = self._plot_box
            if not box:
                return
            left, _top, right, _bottom = box
            self._cut_preview = self._px_to_value(px, left, right, self.view_min, self.view_max)
            self.setCursor(Qt.SizeHorCursor)
            self.update()

    def mouseReleaseEvent(self, event):
        if not self.interaction or self._press is None:
            self._press = None
            return
        px, py = self._event_xy(event)
        if self.chart_type == "Scatter":
            if self.tool == "select" and self._dragging_cut is not None and self._cut_preview is not None:
                if self.on_move_cut:
                    self.on_move_cut(self._dragging_cut, self._cut_preview)
            elif self.tool == "select" and self._dragging_y_cut is not None and self._cut_preview is not None:
                if self.on_move_y_cut:
                    self.on_move_y_cut(self._dragging_y_cut, self._cut_preview)
            self._press = None
            self._cut_preview = None
            self._dragging_cut = None
            self._dragging_y_cut = None
            self.setCursor(Qt.ArrowCursor)
            self.update()
            return
        if self.chart_type != "Needle":
            self._press = None
            return
        if self.tool == "zoom" and self._rubber and abs(px - self._press[0]) > 6:
            box = self._plot_box
            if box:
                left, _top, right, _bottom = box
                start = self._px_to_value(min(self._press[0], px), left, right, self.view_min, self.view_max)
                end = self._px_to_value(max(self._press[0], px), left, right, self.view_min, self.view_max)
                if end > start:
                    self._push_view()
                    self.view_min, self.view_max = start, end
                    self._clamp_view()
                    self._notify_view()
        elif self.tool == "select" and self._dragging_cut is not None and self._cut_preview is not None:
            index = self._dragging_cut
            value = self._cut_preview
            self._cut_preview = None
            self._dragging_cut = None
            if self.on_move_cut:
                self.on_move_cut(index, value)
        elif self.tool == "scroll":
            self._notify_view()
        self._rubber = None
        self._press = None
        self._cut_preview = None
        if self.tool == "select":
            self.setCursor(Qt.ArrowCursor)
        self.update()


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

        def integer_values(key):
            values = set()
            for item in defects:
                try:
                    values.add(int(item.get(key)))
                except (TypeError, ValueError):
                    continue
            return sorted(values)

        self.values = {
            "tests": sorted({item.get("test", "") for item in defects}),
            "class_codes": integer_values("class_code"),
            "rough_bins": integer_values("roughbin"),
            "rough_classes": sorted({
                str(item.get("ido_rough_code")) for item in defects if item.get("ido_rough_code")
            }),
            "rough_groups": sorted({
                str(item.get("ido_rough_group")) for item in defects if item.get("ido_rough_group")
            }),
            "venn_ids": integer_values("venn_id"),
            "channels": integer_values("channel"),
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
    def __init__(self, recipes, results, parent=None, preferred_id=None):
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
        selected = 0
        if preferred_id:
            for index, item in enumerate(self.matches):
                if item.get("id") == preferred_id:
                    selected = index
                    break
        if self.matches:
            self.table.selectRow(selected)
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


class _DefectOffsetMap(QWidget):
    """Wafer view for Adjust Defect Location. The red crosshair is the simulated stage."""

    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self._dragging = False
        self.setMinimumSize(480, 420)
        self.setMouseTracking(True)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#e7e2d4"))
        side = max(80.0, min(self.width(), self.height()) - 36.0)
        x0 = (self.width() - side) / 2
        y0 = (self.height() - side) / 2
        painter.setPen(QPen(QColor("#9a9a96"), 1))
        painter.setBrush(QColor("#f3f3f0"))
        painter.drawEllipse(int(x0), int(y0), int(side), int(side))
        painter.setPen(QPen(QColor("#d0d0cc"), 1))
        step = max(8, int(side / 22))
        for offset in range(step, int(side), step):
            painter.drawLine(int(x0 + offset), int(y0 + 6), int(x0 + offset), int(y0 + side - 6))
            painter.drawLine(int(x0 + 6), int(y0 + offset), int(x0 + side - 6), int(y0 + offset))
        for defect in self.owner.review_result.get("defects", []):
            nx, ny = self.owner._normalized_point(defect)
            px = x0 + side / 2 + nx * side / 2
            py = y0 + side / 2 - ny * side / 2
            current = defect.get("id") == self.owner.defect.get("id")
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#1d4f9c"))
            radius = 4.5 if current else 3.0
            painter.drawEllipse(int(px - radius), int(py - radius), int(radius * 2), int(radius * 2))
        cross_x, cross_y = self.owner._crosshair_norm()
        px = x0 + side / 2 + cross_x * side / 2
        py = y0 + side / 2 - cross_y * side / 2
        painter.setPen(QPen(QColor("#d01212"), 2))
        painter.drawLine(int(px - 14), int(py), int(px + 14), int(py))
        painter.drawLine(int(px), int(py - 14), int(px), int(py + 14))
        painter.end()

    def _norm_at(self, point):
        side = max(80.0, min(self.width(), self.height()) - 36.0)
        x0 = (self.width() - side) / 2
        y0 = (self.height() - side) / 2
        nx = ((point.x() - x0) / side - 0.5) * 2
        ny = (0.5 - (point.y() - y0) / side) * 2
        return nx, ny

    def mousePressEvent(self, event):
        point = event.position() if hasattr(event, "position") else event.pos()
        self._dragging = True
        self.owner._move_crosshair_norm(*self._norm_at(point))

    def mouseMoveEvent(self, event):
        if not self._dragging:
            return
        point = event.position() if hasattr(event, "position") else event.pos()
        self.owner._move_crosshair_norm(*self._norm_at(point))

    def mouseReleaseEvent(self, event):
        self._dragging = False


class ReviewOffsetDialog(QDialog):
    def __init__(self, result, *, die_origin=False, defect_id=None, embedded=False, parent=None):
        super().__init__(parent)
        self.review_result = result
        self.die_origin = die_origin
        self.embedded = embedded
        self._host = parent if embedded else None
        self.result_result = None
        self._syncing = False
        self._last_step = (1, 0)
        defects = list(result.get("defects") or [])
        self.defect = next((item for item in defects if item.get("id") == defect_id), None) or (defects[0] if defects else {})
        self._radius = max(float(result.get("wafer_diameter_mm") or 300.0), 1.0) * 500.0
        raw_x = float(self.defect.get("x", 0.0) or 0.0)
        raw_y = float(self.defect.get("y", 0.0) or 0.0)
        self._normalized = abs(raw_x) <= 2 and abs(raw_y) <= 2
        if die_origin:
            stored = result.get("die_origin_um") or {}
            self._origin_um = (float(stored.get("x", 0.0) or 0.0), float(stored.get("y", 0.0) or 0.0))
        elif self.defect.get("x_um") is not None:
            self._origin_um = (float(self.defect.get("x_um") or 0.0), float(self.defect.get("y_um") or 0.0))
        elif self._normalized:
            self._origin_um = (raw_x * self._radius, raw_y * self._radius)
        else:
            self._origin_um = (raw_x, raw_y)
        self.setStyleSheet(
            "QDialog { background: #e4dfd2; font-family: Arial; font-size: 10px; }"
            "QPushButton { min-height: 24px; background: #f4f1e8; border: 1px solid #6e6a62; padding: 2px 8px; }"
            "QLineEdit, QComboBox, QListWidget { background: white; }"
        )
        if embedded:
            self.setWindowFlags(Qt.Widget)
        else:
            self.setWindowTitle("Wafer Inspection Review")
            self.resize(1180, 760)
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        if not embedded:
            root.addWidget(self._rail())
        body = QVBoxLayout()
        body.setContentsMargins(8, 8, 8, 8)
        content = QHBoxLayout()
        self.map = _DefectOffsetMap(self)
        content.addWidget(self.map, 1)
        content.addWidget(self._readout())
        body.addLayout(content, 1)
        body.addLayout(self._footer())
        root.addLayout(body, 1)
        self.x_offset.valueChanged.connect(self._readouts_from_offsets)
        self.y_offset.valueChanged.connect(self._readouts_from_offsets)
        self._readouts_from_offsets()

    def _rail(self):
        rail = QFrame()
        rail.setFixedWidth(148)
        rail.setStyleSheet("QFrame { background: #cfcbc2; border-right: 2px solid #77746c; }")
        layout = QVBoxLayout(rail)
        layout.setContentsMargins(8, 14, 6, 12)
        layout.setSpacing(8)
        active = "Adjust Die\nOrigin" if self.die_origin else "Adjust Defect\nLocation"
        actions = {
            "Select Lot": ("_choose_lot", ()),
            "Import KLARF": ("_menu_import_klarf", ()),
            "Adjust Defect\nLocation": ("_adjust_offset", (False,)),
            "Adjust Die\nOrigin": ("_adjust_offset", (True,)),
            "Optics Selector": ("_optics_selector", ()),
            "Sensitivity Tuner": ("_sensitivity_tuner", ()),
        }
        for text, action in actions.items():
            button = QPushButton(text)
            button.setFocusPolicy(Qt.NoFocus)
            if text == active:
                button.setStyleSheet(
                    "QPushButton { background: #d7e4f8; border: 2px solid #1d4f9c; font-weight: 700; }"
                )
            else:
                button.clicked.connect(
                    lambda _checked=False, name=action[0], args=action[1]: self._follow_review(name, args)
                )
            layout.addWidget(button)
        layout.addStretch(1)
        end = QPushButton("End")
        end.setFocusPolicy(Qt.NoFocus)
        end.clicked.connect(self.reject)
        layout.addWidget(end)
        return rail

    def _follow_review(self, name, args):
        parent = self.parent()
        self.reject()
        if parent is None or not hasattr(parent, name):
            return
        QTimer.singleShot(0, lambda: getattr(parent, name)(*args))

    def _readout(self):
        panel = QWidget()
        panel.setFixedWidth(230)
        form = QVBoxLayout(panel)
        form.setContentsMargins(8, 12, 4, 8)
        kind = "Die Origin" if self.die_origin else "Defect Location"
        form.addWidget(QLabel(f"Original {kind} (µm)"))
        self.original_location = QLabel()
        self.original_location.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.addWidget(self.original_location)
        form.addWidget(QLabel(f"New {kind} (µm)"))
        self.new_location = QLabel()
        self.new_location.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.addWidget(self.new_location)
        form.addWidget(QLabel("Defect Offset (µm)" if not self.die_origin else "Die Origin Offset (µm)"))
        self.offset_location = QLabel()
        self.offset_location.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.addWidget(self.offset_location)
        reset = QPushButton("Reset Offset")
        reset.clicked.connect(self._reset_offset)
        form.addWidget(reset, 0, Qt.AlignLeft)
        form.addSpacing(16)
        self.unique_id = QLabel(f"Unique ID  :  {self.defect.get('id', '')}")
        self.defect_die = QLabel(
            f"Defect Die  :  ({self.defect.get('die_x', 0)},{self.defect.get('die_y', 0)})"
        )
        form.addWidget(self.unique_id)
        form.addWidget(self.defect_die)
        form.addSpacing(12)
        self.permanent = QCheckBox("Apply Offset Permanently")
        self.permanent.toggled.connect(self._permanent_text)
        form.addWidget(self.permanent)
        self.permanent_note = QLabel()
        self.permanent_note.setWordWrap(True)
        form.addWidget(self.permanent_note)
        self._permanent_text(False)
        if self.die_origin:
            for widget in (reset, self.unique_id, self.defect_die, self.permanent, self.permanent_note):
                widget.hide()
            self.permanent.setChecked(True)
        form.addStretch(1)
        self.x_offset = QDoubleSpinBox(panel)
        self.y_offset = QDoubleSpinBox(panel)
        for control in (self.x_offset, self.y_offset):
            control.setRange(-1000000.0, 1000000.0)
            control.setDecimals(6)
            control.hide()
        return panel

    def _footer(self):
        footer = QHBoxLayout()
        stage = QGroupBox("Move Stage")
        grid = QGridLayout(stage)
        moves = (
            ("↖", -1, 1, 0, 0), ("↑", 0, 1, 0, 1), ("↗", 1, 1, 0, 2),
            ("←", -1, 0, 1, 0), ("•", 0, 0, 1, 1), ("→", 1, 0, 1, 2),
            ("↙", -1, -1, 2, 0), ("↓", 0, -1, 2, 1), ("↘", 1, -1, 2, 2),
        )
        for label, sx, sy, row, column in moves:
            button = QPushButton(label)
            button.setFixedSize(28, 28)
            button.setStyleSheet("QPushButton { min-height: 0; padding: 0; font-weight: 700; }")
            if label == "•":
                button.clicked.connect(self._reset_offset)
            else:
                button.clicked.connect(lambda _checked=False, sx=sx, sy=sy: self._step(sx, sy))
            grid.addWidget(button, row, column)
        self.stage_step = QComboBox()
        self.stage_step.addItems(["1 µm", "2 µm", "5 µm", "10 µm", "20 µm", "50 µm"])
        self.stage_step.setCurrentText("2 µm")
        grid.addWidget(self.stage_step, 3, 0, 1, 2)
        repeat = QPushButton(">>")
        repeat.setToolTip("Move again by ten steps in the last direction.")
        repeat.clicked.connect(self._repeat_step)
        grid.addWidget(repeat, 3, 2)
        self.stage_box = stage
        stage.setParent(self)
        if not self.embedded:
            footer.addWidget(stage, 0, Qt.AlignLeft)
        footer.addStretch(1)
        mark = QPushButton("Mark")
        mark.clicked.connect(self._mark)
        finish = QPushButton("Finish")
        finish.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self._cancel)
        footer.addWidget(mark)
        footer.addWidget(finish)
        footer.addWidget(cancel)
        footer.addStretch(1)
        self.marked = QLabel("Mark the actual die origin" if self.die_origin else "Mark the actual defect")
        footer.addWidget(self.marked)
        return footer

    def _permanent_text(self, checked):
        if checked:
            self.permanent_note.setText("The offset will be saved to the result file.")
        else:
            self.permanent_note.setText(
                "The offset will apply only for this review session and will not be saved to the result file."
            )

    def _offset_um(self):
        scale = self._radius if self._normalized else 1.0
        return self.x_offset.value() * scale, self.y_offset.value() * scale

    def _normalized_point(self, defect):
        if defect.get("x_um") is not None:
            return float(defect.get("x_um") or 0.0) / self._radius, float(defect.get("y_um") or 0.0) / self._radius
        x = float(defect.get("x", 0.0) or 0.0)
        y = float(defect.get("y", 0.0) or 0.0)
        if abs(x) <= 2 and abs(y) <= 2:
            return x, y
        return x / self._radius, y / self._radius

    def _crosshair_norm(self):
        dx, dy = self._offset_um()
        return (self._origin_um[0] + dx) / self._radius, (self._origin_um[1] + dy) / self._radius

    def _readouts_from_offsets(self):
        if self._syncing:
            return
        dx, dy = self._offset_um()
        ox, oy = self._origin_um
        self.original_location.setText(f"{ox:.2f}    {oy:.2f}")
        self.new_location.setText(f"{ox + dx:.2f}    {oy + dy:.2f}")
        self.offset_location.setText(f"{dx:.2f}    {dy:.2f}")
        self.map.update()

    def _set_offset_um(self, dx, dy):
        scale = self._radius if self._normalized else 1.0
        self._syncing = True
        self.x_offset.setValue(dx / scale)
        self.y_offset.setValue(dy / scale)
        self._syncing = False
        self._readouts_from_offsets()

    def _step_um(self):
        text = self.stage_step.currentText().split()[0]
        try:
            return float(text)
        except ValueError:
            return 2.0

    def _step(self, sx, sy):
        if sx or sy:
            self._last_step = (sx, sy)
        dx, dy = self._offset_um()
        step = self._step_um()
        self._set_offset_um(dx + sx * step, dy + sy * step)

    def _repeat_step(self):
        sx, sy = self._last_step
        dx, dy = self._offset_um()
        step = self._step_um() * 10
        self._set_offset_um(dx + sx * step, dy + sy * step)

    def _move_crosshair_norm(self, nx, ny):
        dx = nx * self._radius - self._origin_um[0]
        dy = ny * self._radius - self._origin_um[1]
        self._set_offset_um(dx, dy)

    def _reset_offset(self):
        self._set_offset_um(0.0, 0.0)

    def _mark(self):
        dx, dy = self._offset_um()
        self.marked.setText(f"Location marked; offset vector is ready.  {dx:.2f}, {dy:.2f} µm")

    def _cancel(self):
        host = getattr(self, "_host", None)
        if self.embedded and host is not None and hasattr(host, "_close_offset_page"):
            host._close_offset_page(False)
            return
        self.reject()

    def _finish(self):
        updated = apply_review_offset(
            self.review_result,
            self.x_offset.value(),
            self.y_offset.value(),
            die_origin=self.die_origin,
        )
        dx, dy = self._offset_um()
        for defect in updated.get("defects", []):
            if "x_um" in defect:
                defect["x_um"] = round(float(defect.get("x_um") or 0.0) + dx, 3)
                defect["y_um"] = round(float(defect.get("y_um") or 0.0) + dy, 3)
        if self.die_origin:
            updated["die_origin_um"] = {
                "x": round(self._origin_um[0] + dx, 3),
                "y": round(self._origin_um[1] + dy, 3),
            }
        self.result_result = updated
        host = getattr(self, "_host", None)
        if self.embedded and host is not None and hasattr(host, "_close_offset_page"):
            host._close_offset_page(True)
            return
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
        self.scores = analyze_optics_modes(
            site_ids,
            self.modes,
            self.review_result.get("defects", []),
        )
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
    """Assign class codes to named partitions. Unassigned codes stay on the <None> row."""

    def __init__(self, partitions=None, parent=None, class_codes=None):
        super().__init__(parent)
        self.result_partitions = None
        if partitions is None:
            partitions = [
                {"name": "Partition A", "classes": [2]},
                {"name": "Partition B", "classes": [4]},
            ]
            if class_codes is None:
                class_codes = [1, 2, 3, 4, 5]
        self.class_codes = []
        for code in class_codes or []:
            try:
                self.class_codes.append(int(code))
            except (TypeError, ValueError):
                continue
        self._seen_codes = set(self.class_codes)
        self.setWindowTitle("Partitions")
        self.resize(440, 360)
        self.setStyleSheet("QDialog { background: #ece9d8; } QTableWidget { background: white; }")
        root = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Partitions"))
        clear_classes = QToolButton()
        clear_classes.setIcon(_nuisance_bin_icon())
        clear_classes.setToolTip("Clear classes from the selected partition")
        clear_classes.clicked.connect(self._clear_selected_classes)
        toolbar.addWidget(clear_classes)
        self.classes_button = QToolButton()
        self.classes_button.setText("Classes")
        self.classes_button.setPopupMode(QToolButton.InstantPopup)
        self.classes_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.classes_menu = QMenu(self.classes_button)
        self.classes_menu.aboutToShow.connect(self._rebuild_class_menu)
        self.classes_button.setMenu(self.classes_menu)
        toolbar.addWidget(self.classes_button)
        name_button = QPushButton("Name")
        name_button.clicked.connect(self._rename_selected)
        new_button = QPushButton("New")
        new_button.setIcon(self.style().standardIcon(QStyle.SP_FileIcon))
        new_button.clicked.connect(self._new_partition)
        delete_button = QPushButton("Delete")
        delete_button.setIcon(_delete_node_icon())
        delete_button.clicked.connect(self._delete)
        toolbar.addWidget(name_button)
        toolbar.addWidget(new_button)
        toolbar.addWidget(delete_button)
        toolbar.addStretch(1)
        root.addLayout(toolbar)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Name", "Classes"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        for partition in partitions:
            self._add_row(partition)
        self._ensure_none_row()
        self._refresh_none()
        if self.table.rowCount():
            self.table.selectRow(0)
        root.addWidget(self.table, 1)
        actions = QHBoxLayout()
        actions.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("OK")
        ok.clicked.connect(self._finish)
        actions.addWidget(cancel)
        actions.addWidget(ok)
        root.addLayout(actions)

    def _add_row(self, partition):
        row = self.table.rowCount()
        self.table.insertRow(row)
        name = QTableWidgetItem(str(partition.get("name", "")))
        classes = QTableWidgetItem(", ".join(str(value) for value in partition.get("classes", [])))
        name.setFlags(name.flags() & ~Qt.ItemIsEditable)
        classes.setFlags(classes.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, 0, name)
        self.table.setItem(row, 1, classes)
        for code in self._classes_at(row):
            self._seen_codes.add(code)
        return row

    def _is_none_row(self, row):
        item = self.table.item(row, 0) if row >= 0 else None
        return item is not None and item.text().strip() == "<None>"

    def _none_row(self):
        for row in range(self.table.rowCount()):
            if self._is_none_row(row):
                return row
        return -1

    def _classes_at(self, row):
        item = self.table.item(row, 1) if row >= 0 else None
        if item is None or not item.text().strip():
            return []
        codes = []
        for value in item.text().split(","):
            value = value.strip()
            if not value:
                continue
            codes.append(int(value))
        return codes

    def _set_classes(self, row, codes):
        self.table.item(row, 1).setText(", ".join(str(code) for code in codes))
        for code in codes:
            self._seen_codes.add(int(code))

    def _ensure_none_row(self):
        if self._none_row() < 0:
            self._add_row({"name": "<None>", "classes": []})

    def _refresh_none(self):
        row = self._none_row()
        if row < 0:
            return
        assigned = set()
        for index in range(self.table.rowCount()):
            if index != row:
                assigned.update(self._classes_at(index))
        leftover = [code for code in sorted(self._seen_codes) if code not in assigned]
        self.table.item(row, 1).setText(", ".join(str(code) for code in leftover))

    def _selected_real_row(self):
        row = self.table.currentRow()
        if row >= 0 and not self._is_none_row(row):
            return row
        for index in range(self.table.rowCount()):
            if not self._is_none_row(index):
                self.table.selectRow(index)
                return index
        return -1

    def _rebuild_class_menu(self):
        self.classes_menu.clear()
        row = self._selected_real_row()
        current = set(self._classes_at(row)) if row >= 0 else set()
        codes = sorted(self._seen_codes) or [1, 2, 3, 4, 5]
        for code in codes:
            action = self.classes_menu.addAction(str(code))
            action.setCheckable(True)
            action.setChecked(code in current)
            action.triggered.connect(lambda checked=False, value=code: self._toggle_class(value, checked))

    def _toggle_class(self, code, checked):
        code = int(code)
        self._seen_codes.add(code)
        row = self._selected_real_row()
        if row < 0:
            return
        current = set(self._classes_at(row))
        if checked:
            current.add(code)
            for other in range(self.table.rowCount()):
                if other == row or self._is_none_row(other):
                    continue
                self._set_classes(other, [value for value in self._classes_at(other) if value != code])
        else:
            current.discard(code)
        self._set_classes(row, sorted(current))
        self._refresh_none()

    def _clear_selected_classes(self):
        row = self.table.currentRow()
        if row < 0 or self._is_none_row(row):
            return
        self._set_classes(row, [])
        self._refresh_none()

    def _rename_selected(self):
        row = self.table.currentRow()
        if row < 0 or self._is_none_row(row):
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Name")
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Partition name"))
        edit = QLineEdit(self.table.item(row, 0).text())
        layout.addWidget(edit)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(dialog.reject)
        ok = QPushButton("OK")
        ok.clicked.connect(dialog.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(ok)
        layout.addLayout(buttons)
        if _exec(dialog) == QDialog.Accepted and edit.text().strip():
            self.table.item(row, 0).setText(edit.text().strip())

    def _new_partition(self):
        existing = {
            self.table.item(row, 0).text()
            for row in range(self.table.rowCount())
            if self.table.item(row, 0) is not None
        }
        letter = "A"
        while f"Partition {letter}" in existing and letter < "Z":
            letter = chr(ord(letter) + 1)
        name = f"Partition {letter}"
        none_row = self._none_row()
        if none_row < 0:
            row = self._add_row({"name": name, "classes": []})
        else:
            self.table.insertRow(none_row)
            name_item = QTableWidgetItem(name)
            classes_item = QTableWidgetItem("")
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            classes_item.setFlags(classes_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(none_row, 0, name_item)
            self.table.setItem(none_row, 1, classes_item)
            row = none_row
        self.table.selectRow(row)

    def _delete(self):
        rows = sorted({index.row() for index in self.table.selectedIndexes()}, reverse=True)
        for row in rows:
            if not self._is_none_row(row):
                self.table.removeRow(row)
        self._ensure_none_row()
        self._refresh_none()

    def _finish(self):
        result = []
        names = set()
        try:
            for row in range(self.table.rowCount()):
                if self._is_none_row(row):
                    continue
                name = self.table.item(row, 0).text().strip()
                if not name or name in names:
                    raise ValueError("Partition names must be nonempty and unique.")
                classes = self._classes_at(row)
                names.add(name)
                result.append({"name": name, "classes": sorted(set(classes))})
        except (AttributeError, ValueError) as exc:
            QMessageBox.warning(self, "Partitions", str(exc) or "Classes must be integer values.")
            return
        self.result_partitions = result
        self.accept()


def _starter_tree_pixmap(size=16):
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#2f8f32"))
    radius = max(3, size // 5)
    painter.drawEllipse(size // 2 - radius, 1, radius * 2, radius * 2)
    painter.drawEllipse(2, size // 3, radius * 2, radius * 2)
    painter.drawEllipse(size - radius * 2 - 2, size // 3, radius * 2, radius * 2)
    painter.setBrush(QColor("#8a5a2b"))
    painter.drawRect(size // 2 - 1, size // 2, 3, size // 2 - 1)
    painter.end()
    return pixmap


def _starter_tree_icon():
    return QIcon(_starter_tree_pixmap(16))


def _delete_node_icon():
    pixmap = QPixmap(16, 16)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setPen(QPen(QColor("#c43737"), 2))
    painter.drawLine(4, 4, 12, 12)
    painter.drawLine(12, 4, 4, 12)
    painter.end()
    return QIcon(pixmap)


def _folder_pixmap():
    pixmap = QPixmap(16, 14)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#e6b422"))
    painter.drawRect(1, 3, 14, 10)
    painter.setBrush(QColor("#f0c84a"))
    painter.drawRect(1, 1, 7, 3)
    painter.end()
    return pixmap


def _view_all_icon():
    pixmap = QPixmap(16, 16)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setPen(QPen(QColor("#6a6a6a"), 1))
    painter.setBrush(QColor("#f7f7f7"))
    painter.drawRect(1, 3, 10, 8)
    painter.setBrush(QColor("#3d78d8"))
    path = QPainterPath()
    path.moveTo(8, 5)
    path.lineTo(14, 8)
    path.lineTo(8, 11)
    path.closeSubpath()
    painter.setPen(Qt.NoPen)
    painter.drawPath(path)
    painter.end()
    return QIcon(pixmap)


def _log_histogram_icon():
    pixmap = QPixmap(16, 16)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#3d78d8"))
    path = QPainterPath()
    path.moveTo(2, 13)
    path.lineTo(8, 3)
    path.lineTo(14, 13)
    path.closeSubpath()
    painter.drawPath(path)
    painter.end()
    return QIcon(pixmap)


def _hide_unclassified_icon():
    pixmap = QPixmap(16, 16)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setPen(QPen(QColor("#5c4630"), 1))
    painter.setBrush(QColor("#f0c14a"))
    body = QPainterPath()
    body.moveTo(11, 2)
    body.lineTo(14, 5)
    body.lineTo(6, 13)
    body.lineTo(3, 10)
    body.closeSubpath()
    painter.drawPath(body)
    painter.setBrush(QColor("#333333"))
    tip = QPainterPath()
    tip.moveTo(3, 10)
    tip.lineTo(6, 13)
    tip.lineTo(2, 14)
    tip.closeSubpath()
    painter.drawPath(tip)
    painter.end()
    return QIcon(pixmap)


def _chart_icon(kind):
    pixmap = QPixmap(18, 18)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)

    def magnifier(glyph):
        painter.setPen(QPen(QColor("#202020"), 1.3))
        painter.setBrush(QColor("#fbfbf6"))
        painter.drawEllipse(1, 1, 11, 11)
        painter.drawLine(10, 10, 16, 16)
        painter.setPen(QPen(QColor("#202020"), 1.4))
        glyph()

    if kind == "zoom":
        magnifier(lambda: None)
        painter.setBrush(QColor("#202020"))
        painter.setPen(Qt.NoPen)
        path = QPainterPath()
        path.moveTo(12, 8)
        path.lineTo(17, 11)
        path.lineTo(12, 14)
        path.closeSubpath()
        painter.drawPath(path)
    elif kind == "select":
        painter.setPen(QPen(QColor("#202020"), 1))
        painter.setBrush(QColor("#f7f7f7"))
        path = QPainterPath()
        path.moveTo(4, 2)
        path.lineTo(4, 15)
        path.lineTo(8, 12)
        path.lineTo(11, 16)
        path.lineTo(13, 15)
        path.lineTo(10, 11)
        path.lineTo(14, 11)
        path.closeSubpath()
        painter.drawPath(path)
    elif kind == "hand":
        painter.setPen(QPen(QColor("#202020"), 1))
        painter.setBrush(QColor("#f4f4f4"))
        painter.drawRoundedRect(6, 8, 8, 7, 2, 2)
        for index, top in enumerate((3, 5, 6, 8)):
            painter.drawRoundedRect(6 + index * 2, top, 2, 8, 1, 1)
    elif kind == "zoom-out":
        magnifier(lambda: painter.drawLine(3, 6, 9, 6))
    elif kind == "zoom-in":
        magnifier(lambda: (painter.drawLine(6, 3, 6, 9), painter.drawLine(3, 6, 9, 6)))
    elif kind == "zoom-fit":
        magnifier(lambda: painter.drawRect(4, 4, 5, 5))
    elif kind == "density":
        magnifier(lambda: (painter.setBrush(QColor("#202020")), painter.drawEllipse(5, 3, 3, 3), painter.drawLine(6, 6, 6, 9)))
    elif kind == "back":
        painter.setPen(QPen(QColor("#111111"), 1))
        painter.setBrush(QColor("#11c4d6"))
        path = QPainterPath()
        path.moveTo(2, 9)
        path.lineTo(9, 3)
        path.lineTo(9, 6)
        path.lineTo(16, 6)
        path.lineTo(16, 12)
        path.lineTo(9, 12)
        path.lineTo(9, 15)
        path.closeSubpath()
        painter.drawPath(path)
    elif kind == "forward":
        painter.setPen(QPen(QColor("#111111"), 1))
        painter.setBrush(QColor("#11c4d6"))
        path = QPainterPath()
        path.moveTo(16, 9)
        path.lineTo(9, 3)
        path.lineTo(9, 6)
        path.lineTo(2, 6)
        path.lineTo(2, 12)
        path.lineTo(9, 12)
        path.lineTo(9, 15)
        path.closeSubpath()
        painter.drawPath(path)
    elif kind == "cut":
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#243a86"))
        for index in range(6):
            painter.drawRect(2 + index * 2, 3, 1, 12)
    elif kind == "horizontal-cut":
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#243a86"))
        for index in range(6):
            painter.drawRect(3, 2 + index * 2, 12, 1)
    elif kind == "delete-cut":
        painter.setPen(QPen(QColor("#d00000"), 2))
        painter.drawLine(4, 4, 14, 14)
        painter.drawLine(14, 4, 4, 14)
    elif kind == "apply":
        painter.setPen(QPen(QColor("#4c4c4c"), 1.6))
        painter.setBrush(Qt.NoBrush)
        painter.drawArc(2, 3, 12, 12, 40 * 16, 280 * 16)
        painter.setBrush(QColor("#4c4c4c"))
        path = QPainterPath()
        path.moveTo(12, 3)
        path.lineTo(17, 6)
        path.lineTo(12, 9)
        path.closeSubpath()
        painter.drawPath(path)
    elif kind == "group":
        painter.setPen(QPen(QColor("#5c5c5c"), 1.4))
        for x, y, dx, dy in ((2, 2, 4, 0), (2, 2, 0, 4), (12, 2, 4, 0), (16, 2, 0, 4), (2, 12, 0, 4), (2, 16, 4, 0), (16, 12, 0, 4), (12, 16, 4, 0)):
            painter.drawLine(x, y, x + dx, y + dy)
    elif kind == "ungroup":
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#333333"))
        for index in range(8):
            angle = index / 8.0 * math.tau
            painter.drawEllipse(int(9 + math.cos(angle) * 5) - 1, int(9 + math.sin(angle) * 5) - 1, 3, 3)
    elif kind == "rename":
        painter.setPen(QColor("#202020"))
        painter.drawText(0, 0, 18, 18, Qt.AlignCenter, "ab")
    elif kind == "partitions":
        painter.setPen(QPen(QColor("#1d4e89"), 1))
        painter.setBrush(QColor("#dce9f8"))
        painter.drawRoundedRect(1, 2, 16, 14, 2, 2)
        painter.drawLine(1, 6, 17, 6)
        painter.drawLine(7, 2, 7, 16)
        painter.drawLine(12, 2, 12, 16)
    elif kind == "group-size":
        painter.setPen(QPen(QColor("#666666"), 1))
        painter.setBrush(QColor("#d9d9d9"))
        painter.drawRect(2, 6, 8, 8)
        painter.drawRect(6, 3, 8, 8)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#202020"))
        path = QPainterPath()
        path.moveTo(15, 14)
        path.lineTo(17, 14)
        path.lineTo(16, 16)
        path.closeSubpath()
        painter.drawPath(path)
    elif kind == "scale":
        painter.setPen(QPen(QColor("#d00000"), 1.6))
        for index in range(6):
            angle = index / 6.0 * math.pi
            painter.drawLine(int(6 + math.cos(angle) * 2), int(8 + math.sin(angle) * 2), int(6 + math.cos(angle) * 6), int(8 + math.sin(angle) * 6))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#202020"))
        path = QPainterPath()
        path.moveTo(13, 14)
        path.lineTo(17, 14)
        path.lineTo(15, 17)
        path.closeSubpath()
        painter.drawPath(path)
    elif kind == "grid":
        painter.setPen(QPen(QColor("#8a8a8a"), 1))
        for step in range(5):
            painter.drawLine(2 + step * 3, 2, 2 + step * 3, 16)
            painter.drawLine(2, 2 + step * 3, 16, 2 + step * 3)
    elif kind == "legend":
        for index, color in enumerate(("#e53935", "#1e88e5", "#43a047")):
            painter.fillRect(2, 2 + index * 5, 5, 4, QColor(color))
            painter.setPen(QPen(QColor("#666666"), 1))
            painter.drawLine(9, 4 + index * 5, 16, 4 + index * 5)
    elif kind == "labels":
        painter.setPen(QPen(QColor("#d89200"), 2))
        painter.drawLine(3, 2, 3, 15)
        painter.drawLine(3, 15, 15, 15)
        painter.setPen(QColor("#202020"))
        painter.drawText(5, 1, 12, 13, Qt.AlignCenter, "L")
    painter.end()
    return QIcon(pixmap)


def _triangle_icon(pointing_down):
    pixmap = QPixmap(12, 12)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#202020"))
    path = QPainterPath()
    if pointing_down:
        path.moveTo(2, 3)
        path.lineTo(10, 3)
        path.lineTo(6, 9)
    else:
        path.moveTo(3, 2)
        path.lineTo(9, 6)
        path.lineTo(3, 10)
    path.closeSubpath()
    painter.drawPath(path)
    painter.end()
    return QIcon(pixmap)


def _nuisance_mark_icon():
    pixmap = QPixmap(16, 16)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setPen(QPen(QColor("#666666"), 1))
    painter.setBrush(QColor("#d0d0d0"))
    painter.drawRect(3, 2, 10, 2)
    painter.drawRect(4, 5, 8, 9)
    painter.setPen(QColor("#d32f2f"))
    painter.drawText(0, 0, 16, 16, Qt.AlignCenter, "N")
    painter.end()
    return QIcon(pixmap)


def _nuisance_bin_icon():
    pixmap = QPixmap(16, 16)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setPen(QPen(QColor("#666666"), 1))
    painter.setBrush(QColor("#d0d0d0"))
    painter.drawRect(3, 2, 10, 2)
    painter.drawRect(4, 5, 8, 9)
    painter.end()
    return QIcon(pixmap)


def _nn_classifier_icon():
    pixmap = QPixmap(16, 16)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#3d62c3"))
    painter.drawEllipse(1, 1, 6, 6)
    painter.drawEllipse(8, 2, 6, 6)
    painter.drawRoundedRect(0, 8, 8, 7, 2, 2)
    painter.drawRoundedRect(7, 9, 8, 6, 2, 2)
    painter.end()
    return QIcon(pixmap)


class StarterTreeGenerationDialog(QDialog):
    def __init__(self, attributes, partitions=None, parent=None, classified_count=0, population=0, class_codes=None):
        super().__init__(parent)
        self.result_settings = None
        self.partitions = deepcopy(partitions or [])
        self.class_codes = list(class_codes or [])
        self.setWindowTitle("Starter Tree Generation")
        self.resize(460, 520)
        self.setStyleSheet("QDialog { background: #ece9d8; } QTreeWidget { background: white; }")
        root = QVBoxLayout(self)
        heading = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(_starter_tree_pixmap(28))
        title = QLabel("Auto Classifier")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        heading.addWidget(icon)
        heading.addWidget(title)
        heading.addStretch(1)
        root.addLayout(heading)
        description = QLabel("Classifier tree will be generated automatically using available attributes.")
        description.setWordWrap(True)
        root.addWidget(description)
        choice = QHBoxLayout()
        self.automatic = QCheckBox("Select attributes automatically")
        self.automatic.setChecked(True)
        self.all_button = QPushButton("All")
        self.none_button = QPushButton("None")
        self.all_button.clicked.connect(lambda: self._set_checks(Qt.Checked))
        self.none_button.clicked.connect(lambda: self._set_checks(Qt.Unchecked))
        choice.addWidget(self.automatic)
        choice.addStretch(1)
        choice.addWidget(self.all_button)
        choice.addWidget(self.none_button)
        root.addLayout(choice)
        self.attributes = QTreeWidget()
        self.attributes.setHeaderLabels(["Use", "Elements"])
        self.attributes.setIndentation(0)
        self.attributes.setColumnWidth(0, 46)
        self.attributes.header().setSectionResizeMode(1, QHeaderView.Stretch)
        for name in attributes:
            item = QTreeWidgetItem(["", name])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(0, Qt.Unchecked)
            item.setData(0, Qt.UserRole, name)
            self.attributes.addTopLevelItem(item)
        self.automatic.toggled.connect(self._sync_manual_selection)
        self._sync_manual_selection(True)
        root.addWidget(self.attributes, 1)
        percent = (100.0 * classified_count / population) if population else 0.0
        note = QLabel(
            f"Note: Selected node contains {classified_count} ({percent:.1f}% of node population) defects\n"
            "with manual classification.\n"
            "Only those defects will be used to construct a tree."
        )
        note.setWordWrap(True)
        root.addWidget(note)
        actions = QHBoxLayout()
        partition_button = QPushButton("Partitioning Goal...")
        partition_button.clicked.connect(self._partitions)
        actions.addWidget(partition_button)
        actions.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        generate = QPushButton("Generate")
        generate.clicked.connect(self._finish)
        actions.addWidget(cancel)
        actions.addWidget(generate)
        root.addLayout(actions)

    def _sync_manual_selection(self, automatic):
        manual = not automatic
        self.attributes.setEnabled(manual)
        self.all_button.setEnabled(manual)
        self.none_button.setEnabled(manual)

    def _set_checks(self, state):
        for index in range(self.attributes.topLevelItemCount()):
            self.attributes.topLevelItem(index).setCheckState(0, state)

    def _partitions(self):
        dialog = STNEFPartitionsDialog(self.partitions, self, class_codes=self.class_codes)
        if _exec(dialog) == QDialog.Accepted and dialog.result_partitions is not None:
            self.partitions = dialog.result_partitions

    def _attribute_name(self, item):
        return item.data(0, Qt.UserRole) or item.text(1) or item.text(0)

    def _finish(self):
        if self.automatic.isChecked():
            selected = [
                self._attribute_name(self.attributes.topLevelItem(index))
                for index in range(self.attributes.topLevelItemCount())
            ]
        else:
            selected = [
                self._attribute_name(self.attributes.topLevelItem(index))
                for index in range(self.attributes.topLevelItemCount())
                if self.attributes.topLevelItem(index).checkState(0) == Qt.Checked
            ]
            if not selected:
                QMessageBox.warning(self, "Starter Tree", "Select at least one attribute.")
                return
        self.result_settings = {
            "automatic": self.automatic.isChecked(),
            "attributes": selected,
            "partitions": deepcopy(self.partitions),
        }
        self.accept()


def _stnef_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _stnef_children(nodes, node):
    parent_id = node.get("id")
    return sorted(
        [item for item in nodes if item.get("parent_id") == parent_id],
        key=lambda item: int(item.get("id", 0)),
    )


def _stnef_attribute_text(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, float):
        return f"{value:g}"
    text = str(value).strip()
    return text or None


def _stnef_partition(node, defects, children, attribute_value, attribute_label, partition_name):
    """Split a node population across its children without losing defects."""
    assignments = {child.get("id"): [] for child in children}
    if not children:
        return assignments
    attributes = [name for name in (node.get("attributes") or []) if name]
    cuts = []
    for value in node.get("cuts") or []:
        try:
            cuts.append(float(value))
        except (TypeError, ValueError):
            continue
    cuts.sort()
    y_cuts = []
    for value in node.get("y_cuts") or []:
        try:
            y_cuts.append(float(value))
        except (TypeError, ValueError):
            continue
    y_cuts.sort()

    def fallback_target():
        unnamed = next(
            (child.get("id") for child in children if not str(child.get("name") or "").strip()),
            None,
        )
        return unnamed if unnamed is not None else children[0].get("id")

    nef_children = [
        (child, bool(child.get("nuisance")))
        for child in children
        if child.get("type") == "NEF Partition"
    ]
    if nef_children and len({flag for _child, flag in nef_children}) > 1:
        for defect in defects:
            wanted = bool(defect.get("nuisance") or defect.get("binner_filtered"))
            target = next(
                (child.get("id") for child, flag in nef_children if flag == wanted),
                children[0].get("id"),
            )
            assignments[target].append(defect)
        return assignments

    if attributes and (cuts or y_cuts):
        attribute = attributes[0]
        y_attribute = attributes[1] if len(attributes) >= 2 and y_cuts else None
        measured = []
        for defect in defects:
            value = attribute_value(defect, attribute)
            y_value = attribute_value(defect, y_attribute) if y_attribute else 0.0
            if value is not None and y_value is not None:
                measured.append((defect, value, y_value))
        if measured:
            measured_ids = {id(defect) for defect, _value, _y_value in measured}
            x_count = len(cuts) + 1
            for defect, value, y_value in measured:
                x_index = sum(value >= cut for cut in cuts)
                y_index = sum(y_value >= cut for cut in y_cuts) if y_attribute else 0
                index = y_index * x_count + x_index
                index = min(index, len(children) - 1)
                assignments[children[index].get("id")].append(defect)
            for defect in defects:
                if id(defect) not in measured_ids:
                    assignments[children[-1].get("id")].append(defect)
            return assignments

    if attributes:
        attribute = attributes[0]
        named = {}
        for child in children:
            label = str(child.get("name") or "").strip()
            if label:
                named.setdefault(label, child.get("id"))
        if named:
            unmatched = []
            for defect in defects:
                label = attribute_label(defect, attribute)
                target = named.get(label) if label is not None else None
                if target is None:
                    unmatched.append(defect)
                else:
                    assignments[target].append(defect)
            if unmatched:
                assignments[fallback_target()].extend(unmatched)
            return assignments

    nuisance_flags = [bool(child.get("nuisance")) for child in children]
    if any(nuisance_flags) and not all(nuisance_flags):
        for defect in defects:
            wanted = bool(defect.get("nuisance") or defect.get("binner_filtered"))
            target = next(
                (child.get("id") for child, flag in zip(children, nuisance_flags) if flag == wanted),
                children[0].get("id"),
            )
            assignments[target].append(defect)
        return assignments

    partitions = node.get("partitions") or []
    if partitions:
        named = {
            str(child.get("name") or "").strip(): child.get("id")
            for child in children
            if str(child.get("name") or "").strip()
        }
        for defect in defects:
            name = partition_name(defect, partitions)
            target = named.get(str(name)) if name else None
            assignments[target or children[0].get("id")].append(defect)
        return assignments

    if str(node.get("type")) == "NN":
        named = {
            str(child.get("name") or "").strip().lower(): child.get("id")
            for child in children
            if str(child.get("name") or "").strip()
        }
        for defect in defects:
            label = defect.get("nn_class", defect.get("nn_bucket", defect.get("nn_label")))
            target = named.get(str(label).strip().lower()) if label is not None else None
            assignments[target or children[0].get("id")].append(defect)
        return assignments

    assignments[children[0].get("id")].extend(defects)
    return assignments


def _stnef_populations(nodes, defects, attribute_value, attribute_label, partition_name):
    """Return the real defect population of every node, partitioned top-down."""
    node_ids = {node.get("id") for node in nodes}
    children_by_parent = {}
    for node in nodes:
        children_by_parent.setdefault(node.get("parent_id"), []).append(node)
    for key in children_by_parent:
        children_by_parent[key].sort(key=lambda item: int(item.get("id", 0)))
    roots = sorted(
        [node for node in nodes if node.get("parent_id") not in node_ids],
        key=lambda node: int(node.get("id", 0)),
    )
    populations = {}

    def walk(node, pool):
        populations[node.get("id")] = list(pool)
        siblings = children_by_parent.get(node.get("id")) or []
        if not siblings:
            return
        parts = _stnef_partition(node, pool, siblings, attribute_value, attribute_label, partition_name)
        for child in siblings:
            walk(child, parts.get(child.get("id"), []))

    for root in roots:
        walk(root, defects)
    return populations


def _stnef_nuisance_ids(nodes, defects, attribute_value, attribute_label, partition_name):
    populations = _stnef_populations(nodes, defects, attribute_value, attribute_label, partition_name)
    hidden = []
    for node in nodes:
        if node.get("nuisance"):
            hidden.extend(defect.get("id") for defect in populations.get(node.get("id"), []))
    return hidden


class _LegendComboBox(QComboBox):
    """Flat legend selector drawn as underlined text with a small drop-down triangle."""

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(QColor("#1f1f1f"))
        available = max(10, self.width() - 20)
        metrics = self.fontMetrics()
        caption = metrics.elidedText(self.currentText(), Qt.ElideRight, available)
        painter.drawText(
            3, 0, available, max(1, self.height() - 2),
            Qt.AlignLeft | Qt.AlignVCenter,
            caption,
        )
        underline = min(self.width() - 4, 4 + metrics.width(caption) + 13)
        painter.setPen(QPen(QColor("#6b6b6b"), 1))
        painter.drawLine(3, self.height() - 2, underline, self.height() - 2)
        painter.setPen(QPen(QColor("#2b2b2b"), 1))
        x = underline - 5
        y = max(3, self.height() // 2 - 1)
        painter.drawLine(x - 3, y, x + 3, y)
        painter.drawLine(x - 2, y + 1, x + 2, y + 1)
        painter.drawLine(x - 1, y + 2, x + 1, y + 2)
        painter.end()


def _summary_code_label(value) -> str:
    """Render one class code (or manual code) as the summary column label."""
    try:
        return str(int(float(value)))
    except (TypeError, ValueError):
        text = "" if value is None else str(value).strip()
        return text or "0"


def _summary_code_sort(labels) -> list:
    """Sort class code labels numerically, keeping unknown labels last."""
    def key(label):
        try:
            return (0, float(label), label)
        except ValueError:
            return (1, 0.0, label)

    return sorted({str(label) for label in labels}, key=key)


def _summary_cells(defects, caught_ids, code_of) -> dict:
    """``{code: "caught/total"}`` for one summary row of ``defects``."""
    totals = Counter()
    caught = Counter()
    for defect in defects:
        code = code_of(defect)
        totals[code] += 1
        if defect.get("id") in caught_ids:
            caught[code] += 1
    return {code: f"{caught[code]}/{totals[code]}" for code in totals}


def _summary_split(cell) -> tuple:
    """Split one ``caught/total`` cell back into two integers."""
    caught, _, total = str(cell or "").partition("/")
    try:
        return int(caught), int(total)
    except ValueError:
        return 0, 0


class TunerSummaryPanel(QFrame):
    """Class Code Summary List strip shared by the ST and ST-NEF tuner views.

    Both pages dock one of these along the whole bottom edge of their window,
    so the two views reserve exactly the same space and read the same way: one
    heading, one grid of ``caught / total`` values per class code with a Total
    column, and a single caption line.  Selecting ``Current`` or ``Test`` tells
    the review which defect population the numbers describe.
    """

    MIN_HEIGHT = 142
    TABLE_HEIGHT = 88
    MAX_CODE_COLUMNS = 10
    ROW_TITLES = ("Current", "Test")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("tunerSummaryPanel")
        self._expanded = True
        self._ui_scale = 1.0
        self._summary_hint = ""
        self.setMinimumHeight(self.MIN_HEIGHT)
        self.setStyleSheet(
            "QFrame#tunerSummaryPanel { background: #efece2;"
            " border-top: 1px solid #a8a49a; }"
        )
        # The strip folds to its caption like the tuner modules above it, so
        # the plots get the whole window when the numbers are not needed.
        self._fullscreen_owned_scaling = True
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.header = GroupHeader("Summary", self, self)
        self.header.setToolTip("Click to collapse or expand the Class Code Summary List")
        self.heading = self.header
        outer.addWidget(self.header, 0)
        self.body = QWidget()
        layout = QVBoxLayout(self.body)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(4)
        outer.addWidget(self.body, 1)

        self.table = QTableWidget(len(self.ROW_TITLES), 2)
        self.table.setHorizontalHeaderLabels(["", "Total"])
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(False)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table.setFixedHeight(self.TABLE_HEIGHT)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.table.setToolTip(
            "Defects caught / total defects. Current counts the selected threshold "
            "and region (including defects shared with other channels); Test counts "
            "the entire test. Selecting a row sets the Review visible defect filter."
        )
        layout.addWidget(self.table, 0)

        self.note = QLabel("")
        self.note.setStyleSheet("color: #5f605c; font-size: 10px;")
        layout.addWidget(self.note)

        # Set by the owning dialog when a row selection should drive the review
        # filter; the ST-NEF page leaves it unset and only highlights the row.
        self.row_selected = None
        self.selected_row = ""
        self._updating = False
        self.table.itemSelectionChanged.connect(self._selection_changed)

    def is_expanded(self) -> bool:
        return self._expanded

    def toggle(self):
        self.set_expanded(not self._expanded)

    def set_expanded(self, expanded: bool):
        self._expanded = bool(expanded)
        self.body.setVisible(self._expanded)
        self._sync_header_text()
        self._apply_metrics()

    def _sync_header_text(self):
        if hasattr(self, "header"):
            hint = getattr(self, "_summary_hint", "")
            self.header.setText("Summary" if self._expanded or not hint else f"Summary   {hint}")
            self.header.setToolTip(
                "Click to collapse the Class Code Summary List" if self._expanded
                else "Click to expand the Class Code Summary List"
            )
            self.header.update()

    def set_ui_scale(self, scale: float):
        self._ui_scale = max(0.6, float(scale))
        self.header.set_ui_scale(self._ui_scale)
        self._apply_metrics()

    def _apply_metrics(self):
        scale = self._ui_scale
        table_height = max(48, int(round(self.TABLE_HEIGHT * scale)))
        self.table.setFixedHeight(table_height)
        if self._expanded:
            self.setMinimumHeight(max(72, int(round(self.MIN_HEIGHT * scale))))
            self.setMaximumHeight(16777215)
        else:
            height = self.header.bar_height
            self.setMinimumHeight(height)
            self.setMaximumHeight(height)

    def set_summary(self, columns, rows, note: str = "") -> None:
        """Fill the grid. ``rows`` is ``[(title, {code: "caught/total"}, total)]``."""
        self.note.setText(note)
        self._summary_hint = "  ·  ".join(
            f"{title} {total}" for title, _cells, total in rows if str(total).strip()
        )
        self._sync_header_text()
        columns = list(columns)
        if len(columns) > self.MAX_CODE_COLUMNS:
            columns, rows = self._aggregate_columns(columns, rows)
        wanted = self.selected_row or (rows[0][0] if rows else "")
        self._updating = True
        self.table.blockSignals(True)
        self.table.setColumnCount(len(columns) + 2)
        self.table.setRowCount(len(rows))
        self.table.setHorizontalHeaderLabels([""] + list(columns) + ["Total"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        for row, (title, cells, total) in enumerate(rows):
            label = self.table.item(row, 0)
            if label is None:
                label = QTableWidgetItem(title)
                label.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.table.setItem(row, 0, label)
            label.setText(str(title))
            for column, code in enumerate(columns, start=1):
                item = QTableWidgetItem(str(cells.get(code, "")))
                item.setTextAlignment(Qt.AlignCenter)
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.table.setItem(row, column, item)
            total_item = QTableWidgetItem(str(total))
            total_item.setTextAlignment(Qt.AlignCenter)
            total_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table.setItem(row, len(columns) + 1, total_item)
        self.table.blockSignals(False)
        self._updating = False
        self._fit_columns()
        self.select_row(wanted)

    def _aggregate_columns(self, columns, rows):
        """Fold the smallest class codes into one ``Other`` column.

        A real KLARF can carry dozens of class codes; keeping the grid readable
        matters more than naming every one of them, and the folded ``Other``
        column still sums the caught and total defects exactly.
        """
        sizes = {}
        for _title, cells, _total in rows:
            for code in columns:
                caught, total = _summary_split(cells.get(code, ""))
                entry = sizes.setdefault(code, [0, 0])
                entry[0] += caught
                entry[1] += total
        ranked = sorted(columns, key=lambda code: (-sizes[code][1], code))
        keep = set(ranked[: self.MAX_CODE_COLUMNS - 1])
        kept = [code for code in columns if code in keep]
        folded = [code for code in columns if code not in keep]
        merged_rows = []
        for title, cells, total in rows:
            merged = {code: cells.get(code, "0/0") for code in kept}
            caught = sum(_summary_split(cells.get(code, ""))[0] for code in folded)
            count = sum(_summary_split(cells.get(code, ""))[1] for code in folded)
            merged["Other"] = f"{caught}/{count}"
            merged_rows.append((title, merged, total))
        return kept + ["Other"], merged_rows

    def _fit_columns(self) -> None:
        """Keep the grid compact: label fits its text, code columns share the rest."""
        total = self.table.columnCount()
        if total < 2:
            return
        label = max(64, self.table.columnWidth(0))
        self.table.setColumnWidth(0, label)
        # Use the strip's own width: the table's viewport still holds the previous
        # geometry while the layout is settling.
        width = max(self.width() - 20, 240)
        available = max(1, width - label)
        share = available // (total - 1)
        size = max(58, min(150, share))
        for column in range(1, total):
            self.table.setColumnWidth(column, size)

    def resizeEvent(self, event):  # noqa: N802 - Qt override
        super().resizeEvent(event)
        self._fit_columns()

    def select_row(self, label: str, notify: bool = False) -> None:
        """Highlight ``label`` (``Current``/``Test``); empty clears the selection."""
        self._updating = True
        self.table.blockSignals(True)
        target = -1
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is not None and item.text() == label:
                target = row
        if target < 0:
            self.table.clearSelection()
            self.selected_row = ""
        else:
            self.table.selectRow(target)
            self.selected_row = label
        self.table.blockSignals(False)
        self._updating = False
        if notify and target >= 0 and self.row_selected is not None:
            self.row_selected(label)

    def _selection_changed(self) -> None:
        if self._updating:
            return
        model = self.table.selectionModel()
        rows = model.selectedRows() if model is not None else []
        if not rows:
            self.selected_row = ""
            return
        item = self.table.item(rows[0].row(), 0)
        self.selected_row = item.text() if item is not None else ""
        if self.row_selected is not None:
            self.row_selected(self.selected_row)


class STNEFTunerDialog(QDialog):
    LEGEND_MODES = ("RoughClass", "Manual Classes", "Super Classes", "Partitions")
    FALLBACK_LEGEND_LABEL = "Class 0"
    LEGEND_CLASS_FIELDS = {
        "RoughClass": "roughbin",
        "Manual Classes": "manual_class",
        "Super Classes": "super_class",
    }
    LEGEND_COLORS = (
        "#e53935", "#1e88e5", "#f9a825", "#43a047",
        "#8e24aa", "#00897b", "#f4511e", "#3949ab",
    )
    CLASS_COLORS = (
        "#202020", "#2e7d32", "#1560bd", "#e53935",
        "#1a237e", "#c62828", "#6a1b9a", "#00897b",
    )
    CONTINUOUS_ATTRIBUTES = [
        "Region Id", "Channel Detected", "Area", "Polarity",
        "Primary Channel", "Primary Ch Intensity", "Primary Ch HLAT Intensity", "Ch1 Intensity",
        "Ch2 Intensity", "Ch3 Intensity", "Ch1 HLAT Intensity", "Ch2 HLAT Intensity",
        "Ch3 HLAT Intensity", "HLAT CF Intensity", "CF_StripCorrelation", "CF_Ch1Intensity",
        "CF_Ch2Intensity", "CF_Ch3Intensity", "CF_Ch12Fusion", "CF_Ch13Fusion",
        "CF_Ch23Fusion", "CF_Ch123Fusion", "CF_TopSideFusion", "Ch2 HLAT AbsMin",
        "Ch3 HLAT AbsMin", "Ch1 HLAT Noise", "Ch2 HLAT Noise", "Ch3 HLAT Noise",
        "Ch1 HLAT Gradient", "Ch2 HLAT Gradient", "Ch3 HLAT Gradient", "Ch1 HLAT Color",
        "Ch2 HLAT Color", "Ch3 HLAT Color", "Ch1 Array Mode Threshold", "Ch2 Array Mode Threshold",
        "Ch3 Array Mode Threshold", "Ch1 Array Mode AbsMin", "Ch2 Array Mode AbsMin", "Ch3 Array Mode AbsMin",
        "Ch1 Array Mode Noise", "Ch2 Array Mode Noise", "Ch3 Array Mode Noise", "Ch1 Local Noise Threshold",
        "Ch2 Local Noise Threshold", "Ch3 Local Noise Threshold", "Ch1 Fast Threshold", "Ch2 Fast Threshold",
        "Ch3 Fast Threshold", "Die Column", "Die Row", "Wafer X Position",
        "Wafer Y Position", "USG Code", "Scaled Size", "Scaled Factor",
        "Radius", "Angle", "Channel1NonUniqueness", "Channel2NonUniqueness",
        "Channel3NonUniqueness", "SingleChannel NonUniqueness", "Channel1Biased", "Channel2Biased",
        "Channel3Biased", "Scale Flag", "MaxChannelBrightness", "Rough Bin Code",
        "Max Dim", "Min Dim", "BBox Width", "BBox Height",
        "HLAT CF Noise", "Ch1 HLAT AbsMin", "SingleChannelBiased",
    ]
    DISCRETE_ATTRIBUTES = [
        "Test ID", "Partial Die",
        "Added", "Die X Position",
        "Venn ID", "Die Y Position",
        "Cluster", "Repeater",
    ]
    HISTOGRAM_CATEGORIES = {
        "Polarity": ("Dark", "Bright"),
        "Primary Channel": ("None", "1", "2", "3"),
        "Partial Die": ("FullDie", "PartialDie"),
    }
    ATTRIBUTE_KEYS = {
        "Region Id": "region_id", "Channel Detected": "channel", "Area": "size_um",
        "Polarity": "polarity", "Primary Channel": "channel", "Primary Ch Intensity": "signal",
        "Primary Ch HLAT Intensity": "signal", "Ch1 Intensity": "signal", "Ch2 Intensity": "signal",
        "Ch3 Intensity": "signal", "Ch1 HLAT Intensity": "signal", "Ch2 HLAT Intensity": "signal",
        "Ch3 HLAT Intensity": "signal", "HLAT CF Intensity": "signal", "Die Column": "die_x",
        "Die Row": "die_y", "Wafer X Position": "x_um", "Wafer Y Position": "y_um",
        "Rough Bin Code": "roughbin", "Scaled Size": "size_um", "Max Dim": "size_um",
        "Min Dim": "size_um", "BBox Width": "size_um", "BBox Height": "size_um",
        "Radius": "size_um", "Test ID": "test", "Venn ID": "venn_id", "Cluster": "cluster_id",
        "Repeater": "repeater_id", "Die Y Position": "die_y", "Die X Position": "die_x",
        "X Position": "die_x", "Added Die": "added",
    }

    def __init__(self, result, state=None, parent=None, hidden_defect_ids=None,
                 embedded=False, summary_panel=None):
        super().__init__(parent)
        self.embedded = embedded
        if embedded:
            self.setWindowFlags(Qt.Widget)
        self.review_result = result
        self.hidden_defect_ids = set(hidden_defect_ids or [])
        self.state = deepcopy(state or {})
        classifier = deepcopy(self.state.get("hierarchical_classifier") or {})
        self.nodes = classifier.get("nodes") or [{
            "id": 1, "parent_id": None, "name": "Wafer", "type": "Root",
            "attributes": [], "cuts": [], "y_cuts": [], "groups": {}, "partitions": [],
            "locked": False, "nuisance": False,
        }]
        self.nodes = self._without_empty_group_rows(self.nodes)
        node_ids = {node.get("id") for node in self.nodes}
        for node in self.nodes:
            if node.get("parent_id") is not None and node.get("parent_id") not in node_ids:
                node["parent_id"] = None
        roots = [node for node in self.nodes if node.get("parent_id") is None]
        root = roots[0] if roots else None
        if root is not None:
            for extra in roots[1:]:
                extra["parent_id"] = root.get("id")
            if self.nodes[0] is not root:
                self.nodes = [root] + [node for node in self.nodes if node is not root]
        self.next_node_id = max(int(node.get("id", 0)) for node in self.nodes) + 1
        self.auto_fit_value = bool(classifier.get("auto_fit", True))
        self.zoom_value = int(classifier.get("zoom", 100))
        self.show_group_labels_value = bool(classifier.get("show_group_labels", False))
        self.toolbox_state = deepcopy(self.state.get("toolbox") or {})
        self.result_state = None
        self._population_cache = None
        self._partition_cache = None
        self._pending_cut_changes = False
        self._legend_names = []
        self._grouped_legend_names = set()
        if not embedded:
            self.setWindowTitle("Sensitivity Tuner")
            self.resize(1180, 760)
        self._maximized_pane = None
        self._saved_pane_sizes = []
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        if not embedded:
            bar = QFrame()
            bar.setObjectName("tunerBar")
            bar.setStyleSheet(
                "QFrame#tunerBar { background: #c9c5bc; border: none;"
                " border-bottom: 1px solid #79766e; }"
            )
            toolbar = QHBoxLayout(bar)
            toolbar.setContentsMargins(8, 5, 8, 5)
            toolbar.setSpacing(6)
            finish = QPushButton("Finish")
            finish.clicked.connect(self._finish)
            cancel = QPushButton("Cancel")
            cancel.clicked.connect(self.reject)
            toolbar.addWidget(finish)
            toolbar.addWidget(cancel)
            toolbar.addStretch(1)
            st_button = QPushButton("ST")
            st_button.setToolTip("Return to Sensitivity Tuner")
            st_button.clicked.connect(self.reject)
            toolbar.addWidget(st_button)
            st_nef_button = QPushButton("STNEF")
            st_nef_button.setToolTip("ST-NEF Tuner")
            st_nef_button.setCheckable(True)
            st_nef_button.setChecked(True)
            toolbar.addWidget(st_nef_button)
            root.addWidget(bar)
            heading = QLabel("ST-NEF Classifier")
            heading.setStyleSheet(
                "font-weight: 700; font-size: 12px; color: #16181c;"
                " padding: 5px 10px 2px 10px;"
            )
            root.addWidget(heading)
        left = QSplitter(Qt.Vertical)
        self.classifier_frame = self._classifier_pane()
        self.properties_frame = self._properties_pane()
        left.addWidget(self.classifier_frame)
        left.addWidget(self.properties_frame)
        left.setStretchFactor(0, 3)
        left.setStretchFactor(1, 4)
        left.setSizes([300, 420])
        self.left_splitter = left
        # The summary is a full width strip along the bottom of the window, so
        # the toolbox pane above it ends level with the properties pane.  The
        # host ST dialog owns the strip when this page is embedded, and both
        # views then reserve the same space.
        self._owns_summary = summary_panel is None
        self.summary_panel = summary_panel if summary_panel is not None else TunerSummaryPanel()
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left)
        self.toolbox_frame = self._toolbox_pane()
        splitter.addWidget(self.toolbox_frame)
        splitter.setSizes([760, 300])
        self.splitter = splitter
        self._arm_pane(self.classifier_frame, left)
        self._arm_pane(self.properties_frame, left)
        self._arm_pane(self.toolbox_frame, splitter)
        workspace = QWidget()
        workspace_layout = QVBoxLayout(workspace)
        workspace_layout.setContentsMargins(8, 6, 8, 6)
        workspace_layout.setSpacing(4)
        workspace_layout.addWidget(splitter, 1)
        root.addWidget(workspace, 1)
        self.status = QLabel("")
        self.status.setStyleSheet("color: #5f605c; font-size: 10px; padding: 0 10px;")
        root.addWidget(self.status)
        if self._owns_summary:
            root.addWidget(self.summary_panel, 0)
        if not embedded:
            footer = QHBoxLayout()
            footer.setContentsMargins(8, 2, 8, 8)
            footer.setSpacing(6)
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
        saved_legend = str(classifier.get("legend") or "")
        if saved_legend in self.LEGEND_MODES:
            self.legend.setCurrentText(saved_legend)
        self._rebuild_tree(1)
        self.fullscreen_adapter = None
        if not embedded:
            self.fullscreen_adapter = FullscreenWindowAdapter(self, base=(1180, 760))

    @staticmethod
    def _without_empty_group_rows(nodes):
        """Drop the old empty group row that used to hang under attribute nodes.

        Attribute nodes are their own group until a cut line adds region rows,
        so a saved tree from the earlier layout is cleaned up on load.
        """
        drop = set()
        for node in nodes:
            if not [name for name in (node.get("attributes") or []) if name]:
                continue
            if node.get("cuts"):
                continue
            for child in nodes:
                if child.get("parent_id") != node.get("id"):
                    continue
                if child.get("type") != "Bucket":
                    continue
                if str(child.get("name") or "").strip():
                    continue
                if any(item.get("parent_id") == child.get("id") for item in nodes):
                    continue
                drop.add(child.get("id"))
        if not drop:
            return list(nodes)
        return [node for node in nodes if node.get("id") not in drop]

    def _pane(self, title):
        frame = CollapsibleGroup(title, margins=(8, 8, 8, 8), spacing=6, variant="pane")
        layout = frame.body_layout
        label = frame.header
        frame.title_label = label
        label.setToolTip("Click the caption to collapse or expand; double-click to maximize")
        return frame, layout

    def _arm_pane(self, frame, splitter):
        filt = _PaneMaximizeFilter(self, splitter, frame)
        frame.installEventFilter(filt)
        frame.header.installEventFilter(filt)
        frame._maximize_filter = filt
        frame.on_expansion_changed(
            lambda expanded, pane=frame, host=splitter:
            self._pane_expansion_changed(pane, host, expanded)
        )

    def _pane_expansion_changed(self, frame, splitter, expanded):
        """Fold a pane down to its caption and give the space to its siblings."""
        index = splitter.indexOf(frame)
        if index < 0:
            return
        vertical = splitter.orientation() == Qt.Vertical
        sizes = list(splitter.sizes())
        panes = [splitter.widget(item) for item in range(splitter.count())]
        if not expanded:
            extent = splitter.height() if vertical else splitter.width()
            folded_siblings = [
                pane for item, pane in enumerate(panes)
                if item != index and hasattr(pane, "is_expanded") and not pane.is_expanded()
            ]
            if not folded_siblings:
                # Remember how much room the splitter has while every pane is
                # open; capped panes later shrink the splitter's own extent.
                splitter._expanded_extent = extent
            if getattr(self, "_maximized_pane", None) == (id(splitter), index):
                # Folding wins over a maximized sibling, so restore the normal
                # split before taking this pane down to its caption.
                self._maximized_pane = None
                saved = list(getattr(self, "_saved_pane_sizes", []) or [])
                if len(saved) == splitter.count() and sum(saved) > 0:
                    splitter.setSizes(saved)
                    sizes = list(splitter.sizes())
            frame._expanded_share = sizes[index] if index < len(sizes) else 0
            frame._expanded_total = sum(sizes)
            if vertical:
                # Capping the height keeps the splitter from handing the folded
                # pane its share back when the window is resized.
                frame.setMaximumHeight(frame.header.bar_height + 2)
                frame.mark_folded("v")
                folded = frame.header.bar_height + 2
            else:
                frame._restore_minimum_width = frame.minimumWidth()
                frame._restore_maximum_width = frame.maximumWidth()
                frame.setMinimumWidth(frame.header.rail_width)
                frame.setMaximumWidth(frame.header.rail_width)
                frame.set_rail(True)
                frame.mark_folded("h")
                folded = frame.header.rail_width
            others = [item for item in range(splitter.count()) if item != index]
            open_others = [
                item for item in others
                if not (hasattr(panes[item], "is_expanded") and not panes[item].is_expanded())
            ]
            closed_others = {
                item: (panes[item].header.bar_height + 2 if vertical
                       else panes[item].header.rail_width)
                for item in others if item not in open_others
            }
            room = max(0, sum(sizes) - folded - sum(closed_others.values()))
            base = sum(sizes[item] for item in open_others)
            new_sizes = list(sizes)
            new_sizes[index] = folded
            for item, value in closed_others.items():
                new_sizes[item] = value
            if base > 0:
                for item in open_others:
                    new_sizes[item] = max(1, int(round(room * sizes[item] / base)))
            splitter.setSizes(new_sizes)
            return

        if vertical:
            frame.setMaximumHeight(16777215)
        else:
            frame.set_rail(False)
            frame.setMinimumWidth(getattr(frame, "_restore_minimum_width", 0))
            frame.setMaximumWidth(getattr(frame, "_restore_maximum_width", 16777215))
        frame.mark_folded(None)
        total = sum(sizes)
        # A splitter whose panes are all folded reports only the folded sizes
        # and shrinks its own extent, so fall back to the room it had while the
        # panes were open.
        extent = splitter.height() if vertical else splitter.width()
        handles = splitter.handleWidth() * max(0, splitter.count() - 1)
        total = max(total, extent - handles, getattr(splitter, "_expanded_extent", 0) - handles)
        if total <= 0:
            return
        # Panes folded next to this one keep their caption-sized share; the
        # rest is split by the ratio this pane had before it was folded.
        folded_others = {}
        for item in range(splitter.count()):
            pane = panes[item]
            if item == index or not hasattr(pane, "is_expanded"):
                continue
            if not pane.is_expanded():
                folded_others[item] = (
                    pane.header.bar_height + 2 if vertical else pane.header.rail_width
                )
        room = max(1, total - sum(folded_others.values()))
        share = float(getattr(frame, "_expanded_share", 0) or 0)
        share_total = float(getattr(frame, "_expanded_total", 0) or 0)
        if share > 0 and share_total > 0:
            target = int(round(room * share / share_total))
        else:
            target = int(round(room * 0.5))
        target = max(1, min(target, max(1, room - 1)))
        growables = [
            item for item in range(splitter.count())
            if item != index and item not in folded_others
        ]
        base = sum(sizes[item] for item in growables) or 1
        rest = max(0, room - target)
        new_sizes = list(sizes)
        new_sizes[index] = target
        for item in growables:
            new_sizes[item] = max(1, int(round(rest * sizes[item] / base)))
        splitter.setSizes(new_sizes)
        # The splitter only regains its full extent after the cap is gone, so
        # apply the restored split once more after that relayout.
        QTimer.singleShot(
            0, lambda host=splitter, values=list(new_sizes): host.setSizes(values)
        )

    def _toggle_pane(self, splitter, frame):
        index = splitter.indexOf(frame)
        if index < 0:
            return
        if not frame.is_expanded():
            frame.set_expanded(True)
            return
        key = (id(splitter), index)
        if self._maximized_pane == key:
            splitter.setSizes(self._saved_pane_sizes or [1, 1])
            self._maximized_pane = None
            return
        self._saved_pane_sizes = splitter.sizes()
        total = max(sum(self._saved_pane_sizes), 1)
        sizes = [0] * splitter.count()
        for item in range(splitter.count()):
            pane = splitter.widget(item)
            if item != index and hasattr(pane, "is_expanded") and not pane.is_expanded():
                # A folded pane keeps its caption while a sibling is maximized.
                sizes[item] = pane.header.bar_height + 2
                total -= sizes[item]
        sizes[index] = max(total, 1)
        splitter.setSizes(sizes)
        self._maximized_pane = key

    def _classifier_pane(self):
        frame, layout = self._pane("Hierarchical Classifier")
        actions = QHBoxLayout()
        self.starter_tree_button = QPushButton("Starter Tree")
        self.starter_tree_button.setIcon(_starter_tree_icon())
        self.nn_classifier_button = QPushButton("NN Classifier")
        self.nn_classifier_button.setIcon(_nn_classifier_icon())
        self.delete_node_button = QPushButton("Delete")
        self.delete_node_button.setIcon(_delete_node_icon())
        self.nuisance_button = QPushButton("Nuisance")
        self.nuisance_button.setIcon(_nuisance_mark_icon())
        for button, callback in (
            (self.starter_tree_button, self._starter_tree),
            (self.nn_classifier_button, self._show_nn_menu),
            (self.delete_node_button, self._delete_node),
            (self.nuisance_button, self._toggle_nuisance),
        ):
            button.clicked.connect(callback)
            actions.addWidget(button)
        actions.addStretch(1)
        layout.addLayout(actions)
        self.classifier_tree = QTreeWidget()
        self.classifier_tree.setHeaderLabels(["Node", "Type", "State"])
        self.classifier_tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.classifier_tree.currentItemChanged.connect(self._node_changed)
        self.classifier_tree.hide()
        layout.addWidget(self.classifier_tree)
        self.classifier_canvas = _STNEFCanvas(self)
        layout.addWidget(self.classifier_canvas, 1)
        view = QHBoxLayout()
        self.auto_refresh = QCheckBox("Auto Refresh")
        self.auto_refresh.setChecked(True)
        self.apply_nuisance = QCheckBox("Apply Nuisance")
        self.apply_nuisance.setChecked(True)
        self.auto_fit = QCheckBox("Auto Fit")
        self.auto_fit.setChecked(self.auto_fit_value)
        self.zoom = QSlider(Qt.Horizontal)
        self.zoom.setRange(50, 250)
        self.zoom.setValue(self.zoom_value)
        self.zoom.setFixedWidth(120)
        self.zoom_label = QLabel("Zoom")
        for check in (self.auto_refresh, self.apply_nuisance):
            check.toggled.connect(lambda *_args: self._node_changed())
        self.auto_fit.toggled.connect(self._sync_classifier_zoom)
        view.addWidget(self.auto_refresh)
        view.addStretch(1)
        view.addWidget(self.apply_nuisance)
        view.addStretch(1)
        view.addWidget(self.zoom_label)
        view.addWidget(self.zoom)
        view.addWidget(self.auto_fit)
        self.canvas_fit_button = QPushButton("Fit View")
        self.canvas_fit_button.setToolTip(
            "Reset the tree view: fit the whole classifier and clear any pan or wheel zoom."
        )
        self.canvas_fit_button.setStyleSheet(
            "QPushButton { background: transparent; border: 1px solid #a8a49a;"
            " border-radius: 2px; padding: 1px 8px; font-size: 11px; }"
            "QPushButton:hover { background: #f7f4ee; border-color: #2f5fb3; }"
        )
        self.canvas_fit_button.clicked.connect(self._reset_classifier_view)
        view.addWidget(self.canvas_fit_button)
        self.zoom.valueChanged.connect(lambda *_args: self.classifier_canvas.update())
        layout.addLayout(view)
        self._sync_classifier_zoom()
        return frame

    def _reset_classifier_view(self):
        if hasattr(self, "classifier_canvas"):
            self.classifier_canvas.reset_view()

    def _sync_classifier_zoom(self, *_args):
        show_zoom = not self.auto_fit.isChecked()
        self.zoom.setVisible(show_zoom)
        self.zoom_label.setVisible(show_zoom)
        self.zoom.setEnabled(show_zoom)
        if hasattr(self, "classifier_canvas"):
            self.classifier_canvas.update()

    def _toolbox_option(self, text, icon, checked):
        button = QPushButton(text)
        button.setIcon(icon)
        button.setCheckable(True)
        button.setChecked(bool(checked))
        button.setStyleSheet(
            "QPushButton { background: transparent; border: 1px solid transparent;"
            " border-radius: 2px; padding: 3px 8px; text-align: left; min-width: 0; }"
            "QPushButton:checked { background: #dbe6f9; border: 1px solid #2f5fb3; }"
            "QPushButton:hover { background: #f2efe7; border: 1px solid #a8a49a; }"
        )
        return button

    def _toolbox_pane(self):
        frame, layout = self._pane("ToolBox")
        tools = QHBoxLayout()
        tools.setSpacing(2)
        self.view_all = self._toolbox_option("View All", _view_all_icon(), self.toolbox_state.get("view_all", True))
        self.log_histogram = self._toolbox_option("Log Histogram", _log_histogram_icon(), self.toolbox_state.get("log_histogram", False))
        self.hide_unclassified = self._toolbox_option("Hide Unclassified", _hide_unclassified_icon(), self.toolbox_state.get("hide_unclassified", False))
        tools.addWidget(self.view_all)
        tools.addWidget(self.log_histogram)
        tools.addWidget(self.hide_unclassified)
        tools.addStretch(1)
        layout.addLayout(tools)
        attributes_row = QHBoxLayout()
        attributes_row.setSpacing(2)
        self.attribute_arrow = QToolButton()
        self.attribute_arrow.setAutoRaise(True)
        self.attribute_arrow.setFixedSize(18, 18)
        self.attribute_arrow.clicked.connect(self._toggle_attributes)
        folder = QLabel()
        folder.setPixmap(_folder_pixmap())
        attributes_title = QLabel("Attributes")
        attributes_title.setStyleSheet("font-weight: 700;")
        attributes_row.addWidget(self.attribute_arrow)
        attributes_row.addWidget(folder)
        attributes_row.addWidget(attributes_title)
        attributes_row.addStretch(1)
        layout.addLayout(attributes_row)
        self.attributes_expanded = True
        self.histogram_host = QWidget()
        self.histogram_layout = QVBoxLayout(self.histogram_host)
        self.histogram_layout.setContentsMargins(4, 0, 4, 0)
        self.attribute_scroll = QScrollArea()
        self.attribute_scroll.setWidgetResizable(True)
        self.attribute_scroll.setMinimumWidth(0)
        self.attribute_scroll.setWidget(self.histogram_host)
        layout.addWidget(self.attribute_scroll, 1)
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
        self.toolbox.hide()
        self.toolbox.itemDoubleClicked.connect(self._toolbox_double_clicked)
        layout.addWidget(self.toolbox)
        for check in (self.view_all, self.log_histogram, self.hide_unclassified):
            check.toggled.connect(self._toolbox_options_changed)
        header_width = (
            self.view_all.sizeHint().width()
            + self.log_histogram.sizeHint().width()
            + self.hide_unclassified.sizeHint().width()
            + 28
        )
        frame.setMinimumWidth(header_width)
        self._set_attributes_expanded(True)
        return frame

    def _toggle_attributes(self):
        self._set_attributes_expanded(not self.attributes_expanded)

    def _set_attributes_expanded(self, expanded):
        splitter = getattr(self, "splitter", None)
        sizes = splitter.sizes() if splitter is not None else None
        self.attributes_expanded = bool(expanded)
        self.attribute_scroll.setVisible(self.attributes_expanded)
        self.attribute_arrow.setIcon(_triangle_icon(not self.attributes_expanded))
        self.attribute_arrow.setToolTip(
            "Collapse the attribute list" if self.attributes_expanded else "Expand the attribute list"
        )
        if self.attributes_expanded and self.histogram_layout.count() == 0:
            self._refresh_histograms()
        if splitter is not None and sizes and sum(sizes) > 0:
            splitter.setSizes(sizes)
            QTimer.singleShot(0, lambda kept=list(sizes): splitter.setSizes(kept))

    def _toolbox_options_changed(self, *_args):
        self._refresh_histograms()
        self._refresh_property_chart()

    def _chart_tool_button(self, kind, tip, callback=None, checkable=False):
        button = QToolButton()
        button.setIcon(_chart_icon(kind))
        button.setToolTip(tip)
        button.setAutoRaise(True)
        button.setFixedSize(20, 20)
        button.setIconSize(QSize(18, 18))
        button.setCheckable(checkable)
        button.setCursor(Qt.ArrowCursor)
        button.setStyleSheet(
            "QToolButton { background: transparent; border: 1px solid transparent;"
            " border-radius: 2px; padding: 0; }"
            "QToolButton:hover { background: #f7f4ee; border: 1px solid #a8a49a; }"
            "QToolButton:checked { background: #d6e6f8; border: 1px solid #2f5fb3; }"
            "QToolButton:disabled { background: transparent; border-color: transparent; }"
        )
        if callback is not None:
            button.clicked.connect(callback)
        return button

    def _chart_text_button(self, kind, text, tip, callback):
        button = QPushButton(text)
        button.setIcon(_chart_icon(kind))
        button.setIconSize(QSize(16, 16))
        button.setToolTip(tip)
        button.setFixedHeight(20)
        button.setCursor(Qt.ArrowCursor)
        button.setStyleSheet(
            "QPushButton { background: transparent; border: 1px solid transparent;"
            " border-radius: 2px; padding: 0 5px; font-size: 11px; color: #1d1f23; }"
            "QPushButton:hover { background: #f7f4ee; border: 1px solid #a8a49a; }"
            "QPushButton:checked { background: #dbe6f9; border: 1px solid #2f5fb3; }"
            "QPushButton:disabled { color: #70706c; background: transparent; border-color: transparent; }"
        )
        button.clicked.connect(callback)
        return button

    @staticmethod
    def _chart_rule():
        """Thin divider between toolbar groups."""
        rule = QFrame()
        rule.setFrameShape(QFrame.VLine)
        rule.setFixedSize(9, 16)
        rule.setStyleSheet("color: #b3afa4; background: transparent;")
        return rule

    def _chart_toolbar_group(self, bar, widgets):
        for widget in widgets:
            bar.addWidget(widget, 0, Qt.AlignVCenter)
        bar.addWidget(self._chart_rule(), 0, Qt.AlignVCenter)

    def _chart_toolbar_row(self, rows):
        """One compact toolbar row: 28px tall, items vertically centred."""
        host = QWidget()
        host.setFixedHeight(28)
        bar = QHBoxLayout(host)
        bar.setContentsMargins(8, 0, 8, 0)
        bar.setSpacing(2)
        rows.addWidget(host, 0)
        return bar

    def _chart_toolbar_last(self, bar):
        """Drop the divider a group leaves at the end of a row."""
        if not bar.count():
            return
        item = bar.takeAt(bar.count() - 1)
        widget = item.widget() if item is not None else None
        if widget is not None:
            widget.deleteLater()

    def _properties_pane(self):
        frame, layout = self._pane("Properties")
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.attribute_label = QLabel("Select a node and double-click an attribute.")
        self.attribute_label.hide()
        self.property_scale = "Linear"
        self.property_grid = False
        self.property_legend_on = True
        bar_host = QWidget()
        bar_host.setObjectName("propertiesToolBar")
        bar_host.setFixedHeight(30)
        bar_host.setStyleSheet(
            "QWidget#propertiesToolBar { background: #e7e4dc;"
            " border-bottom: 1px solid #b3afa4; }"
        )
        bar = QHBoxLayout(bar_host)
        bar.setContentsMargins(6, 0, 6, 0)
        bar.setSpacing(1)
        self.zoom_tool = self._chart_tool_button("zoom", "Zoom Tool: drag a box to zoom in.", lambda: self._set_chart_tool("zoom"), True)
        self.select_tool = self._chart_tool_button("select", "Selection Tool: select a cut line or a region.", lambda: self._set_chart_tool("select"), True)
        self.scroll_tool = self._chart_tool_button("hand", "Scroll Tool: drag to pan the chart.", lambda: self._set_chart_tool("scroll"), True)
        self.zoom_out_button = self._chart_tool_button("zoom-out", "Zoom Out", self._chart_zoom_out)
        self.zoom_in_button = self._chart_tool_button("zoom-in", "Zoom In", self._chart_zoom_in)
        self.zoom_fit_button = self._chart_tool_button("zoom-fit", "Zoom to Fit", self._chart_zoom_fit)
        self.density_button = self._chart_tool_button("density", "Toggle Zoom Density", self._toggle_density, True)
        self.density_button.setChecked(True)
        self.chart_back = self._chart_tool_button("back", "Back: scroll back through the chart.", self._chart_back)
        self.chart_forward = self._chart_tool_button("forward", "Forward: scroll forward through the chart.", self._chart_forward)
        self.create_cut_button = self._chart_tool_button("cut", "Create Cutline: click the chart to place a cut line.", lambda: self._set_chart_tool("cut"), True)
        self.create_horizontal_cut_button = self._chart_tool_button(
            "horizontal-cut",
            "Horizontal Cutline: split a two-attribute plot along the Y axis.",
            lambda: self._set_chart_tool("hcut"),
            True,
        )
        self.delete_cut_button = self._chart_tool_button("delete-cut", "Delete Cutline: delete the selected cut line.", self._delete_cut)
        self.cut_value = QDoubleSpinBox()
        self.cut_value.setRange(-1000000.0, 1000000.0)
        self.cut_value.setDecimals(2)
        self.cut_value.setFixedSize(52, 20)
        self.cut_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.cut_value.setToolTip("Cutline value: the threshold the cut line is placed at.")
        self.cut_value.setStyleSheet(
            "QDoubleSpinBox { background: #ffffff; border: 1px solid #a8a49a;"
            " border-radius: 2px; padding: 0 2px; font-size: 11px; }"
        )
        self.apply_cut_button = self._chart_tool_button(
            "apply",
            "Apply Cutline: insert at the entered value, or move the selected cutline.",
            self._apply_or_insert_cut,
        )
        self.group_button = self._chart_text_button("group", "Group", "Group Regions: group the selected regions.", self._group_cuts)
        self.group_button.setFixedWidth(62)
        self.ungroup_button = self._chart_text_button("ungroup", "Ungroup", "Ungroup Regions.", self._ungroup_cuts)
        self.ungroup_button.setFixedWidth(74)
        self.rename_button = QToolButton()
        self.rename_button.setText("Rename")
        self.rename_button.setIcon(_chart_icon("rename"))
        self.rename_button.setIconSize(QSize(16, 16))
        self.rename_button.setFixedSize(80, 20)
        self.rename_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.rename_button.setPopupMode(QToolButton.MenuButtonPopup)
        self.rename_button.setCursor(Qt.ArrowCursor)
        self.rename_button.setStyleSheet(
            "QToolButton { background: transparent; border: 1px solid transparent;"
            " border-radius: 2px; padding: 0 5px; font-size: 11px; color: #1d1f23; }"
            "QToolButton:hover { background: #f7f4ee; border: 1px solid #a8a49a; }"
            "QToolButton:disabled { color: #70706c; background: transparent; border-color: transparent; }"
            "QToolButton::menu-indicator { subcontrol-position: right center; right: 2px; }"
        )
        self.rename_button.setToolTip("Rename Region")
        rename_menu = QMenu(self.rename_button)
        rename_menu.addAction("Rename Region", self._rename_region)
        self.rename_button.setMenu(rename_menu)
        self.rename_button.clicked.connect(self._rename_region)
        self.partitions_button = self._chart_tool_button(
            "partitions", "Partitions: configure attribute-based color partitions.", self._edit_partitions
        )
        self.labels_button = self._chart_tool_button(
            "labels", "Show or hide group labels in the chart.", self._toggle_group_labels, True
        )
        self.labels_button.setChecked(self.show_group_labels_value)
        self.group_size_button = self._chart_tool_button("group-size", "Change Group Size: bar thickness.")
        self.group_size_button.setPopupMode(QToolButton.InstantPopup)
        size_menu = QMenu(self.group_size_button)
        for size in range(1, 6):
            size_menu.addAction(str(size), lambda _checked=False, value=size: self._set_chart_group_size(value))
        self.group_size_button.setMenu(size_menu)
        self.scale_button = self._chart_tool_button("scale", "Toggle Scale: Linear, Log, Log X, or Log Y.")
        self.scale_button.setText("Scale")
        self.scale_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.scale_button.setFixedSize(68, 20)
        self.scale_button.setPopupMode(QToolButton.InstantPopup)
        scale_menu = QMenu(self.scale_button)
        for name in ("Linear", "Log", "Log X", "Log Y"):
            scale_menu.addAction(name, lambda _checked=False, value=name: self._set_chart_scale(value))
        self.scale_button.setMenu(scale_menu)
        self.grid_button = self._chart_tool_button("grid", "Toggle Grid", self._toggle_chart_grid, True)
        self.legend_button = self._chart_tool_button("legend", "Toggle Legend", self._toggle_chart_legend, True)
        self.legend_button.setChecked(True)
        # Match the operator manual: one left-to-right strip with tools grouped
        # by task, not a wrapped two-row toolbar.
        self._chart_toolbar_group(bar, (self.zoom_tool, self.select_tool, self.scroll_tool))
        self._chart_toolbar_group(
            bar,
            (self.zoom_out_button, self.zoom_in_button, self.zoom_fit_button, self.density_button),
        )
        self._chart_toolbar_group(bar, (self.chart_back, self.chart_forward))
        self._chart_toolbar_group(
            bar,
            (
                self.create_cut_button, self.create_horizontal_cut_button,
                self.delete_cut_button, self.cut_value, self.apply_cut_button,
            ),
        )
        self._chart_toolbar_group(
            bar,
            (self.group_button, self.ungroup_button, self.rename_button),
        )
        self._chart_toolbar_group(
            bar,
            (
                self.partitions_button, self.labels_button, self.group_size_button,
                self.scale_button, self.grid_button, self.legend_button,
            ),
        )
        self._chart_toolbar_last(bar)
        bar.addStretch(1)
        layout.addWidget(bar_host)
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        self.property_chart = DefectChart()
        self.property_chart.setMinimumHeight(160)
        self.property_chart.interaction = True
        self.property_chart.density = True
        self.property_chart.on_place_cut = self._place_cut_at
        self.property_chart.on_move_cut = self._move_chart_cut
        self.property_chart.on_select_cut = self._remember_cut
        self.property_chart.on_place_y_cut = self._place_horizontal_cut_at
        self.property_chart.on_move_y_cut = self._move_horizontal_chart_cut
        self.property_chart.on_select_y_cut = self._remember_horizontal_cut
        self.property_chart.on_select_region = self._region_selection_changed
        self.property_chart.on_view_changed = self._sync_chart_history
        self.property_chart.suppress_legend = True
        self.legend_hidden = set()
        self._legend_names = []
        body.addWidget(self.property_chart, 1)
        self.legend_frame = QFrame()
        self.legend_frame.setObjectName("legendHost")
        self.legend_frame.setFixedWidth(152)
        self.legend_frame.setStyleSheet("QFrame#legendHost { background: transparent; border: none; }")
        legend_layout = QVBoxLayout(self.legend_frame)
        legend_layout.setContentsMargins(2, 0, 4, 4)
        legend_layout.setSpacing(2)
        legend_header = QHBoxLayout()
        legend_header.setContentsMargins(2, 0, 0, 0)
        legend_title = QLabel("Legend")
        legend_title.setStyleSheet(
            "font-size: 11px; font-weight: 700; color: #1f1f1f;"
            " border: none; background: transparent; padding: 1px 2px;"
        )
        legend_close = QToolButton()
        legend_close.setText("\u00d7")
        legend_close.setAutoRaise(True)
        legend_close.setFixedSize(14, 14)
        legend_close.setStyleSheet(
            "QToolButton { border: none; background: transparent; font-weight: 700; color: #1f1f1f; }"
            "QToolButton:hover { color: #b00000; }"
        )
        legend_close.clicked.connect(self._hide_chart_legend)
        legend_header.addWidget(legend_title)
        legend_header.addStretch(1)
        legend_header.addWidget(legend_close)
        legend_layout.addLayout(legend_header)
        self.legend_box = QFrame()
        self.legend_box.setObjectName("legendBox")
        self.legend_box.setStyleSheet(
            "QFrame#legendBox { background: #ffffff; border: 1px solid #8fb3dd; border-radius: 6px; }"
        )
        box_layout = QVBoxLayout(self.legend_box)
        box_layout.setContentsMargins(5, 3, 5, 5)
        box_layout.setSpacing(2)
        self.legend = _LegendComboBox()
        self.legend.setFixedHeight(19)
        self.legend.setCursor(Qt.PointingHandCursor)
        self.legend.setToolTip(
            "Legend source: RoughClass, Manual Classes, Super Classes, or attribute Partitions"
        )
        self.legend.setStyleSheet(
            "QComboBox { background: transparent; border: none; padding: 0; font-size: 11px; }"
            "QComboBox::drop-down { border: none; width: 0; }"
            "QComboBox::down-arrow { image: none; width: 0; height: 0; }"
            "QComboBox QAbstractItemView {"
            " background: #ffffff; border: 1px solid #7f9db9; outline: none; font-size: 11px;"
            " selection-background-color: #2f6fd6; selection-color: #ffffff;"
            "}"
        )
        self.legend.addItems(list(self.LEGEND_MODES))
        self.legend.setCurrentText("Partitions")
        self.legend.currentTextChanged.connect(self._legend_mode_changed)
        box_layout.addWidget(self.legend)
        self.legend_list = QFrame()
        self.legend_list.setObjectName("legendList")
        self.legend_list.setStyleSheet(
            "QFrame#legendList { background: #ffffff; border: 1px solid #b9cde2; border-radius: 5px; }"
        )
        list_layout = QVBoxLayout(self.legend_list)
        list_layout.setContentsMargins(3, 3, 3, 3)
        list_layout.setSpacing(2)
        self.legend_rows = QVBoxLayout()
        self.legend_rows.setContentsMargins(0, 0, 0, 0)
        self.legend_rows.setSpacing(3)
        list_layout.addLayout(self.legend_rows)
        box_layout.addWidget(self.legend_list)
        self.legend_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        legend_layout.addWidget(self.legend_box, 0, Qt.AlignTop)
        self.legend_controls = QWidget()
        controls = QGridLayout(self.legend_controls)
        controls.setContentsMargins(0, 2, 0, 0)
        controls.setHorizontalSpacing(2)
        controls.setVerticalSpacing(2)
        for index, (text, callback) in enumerate((
            ("Select All", self._select_all_legend),
            ("Deselect All", self._deselect_all_legend),
            ("Group", self._group_legend_classes),
            ("Ungroup", self._ungroup_legend_classes),
        )):
            button = QPushButton(text)
            button.setFixedHeight(20)
            button.setStyleSheet(
                "QPushButton { background: transparent; border: 1px solid transparent;"
                " padding: 0 2px; font-size: 10px; text-align: left; }"
                "QPushButton:hover { background: #f7f4ee; border-color: #a8a49a; }"
            )
            button.clicked.connect(callback)
            controls.addWidget(button, index // 2, index % 2)
        legend_layout.addWidget(self.legend_controls, 0, Qt.AlignTop)
        legend_layout.addStretch(1)
        body.addWidget(self.legend_frame, 0, Qt.AlignTop)
        layout.addLayout(body, 1)
        self.cuts = QTableWidget(0, 2)
        self.cuts.setHorizontalHeaderLabels(["Position", "Group"])
        self.cuts.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.cuts.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.cuts.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.cuts.hide()
        layout.addWidget(self.cuts)
        self.show_labels = QCheckBox("Show Group Labels")
        self.show_labels.setChecked(self.show_group_labels_value)
        self.show_labels.hide()
        layout.addWidget(self.show_labels)
        self._set_chart_tool("select")
        self._sync_chart_history()
        self._region_selection_changed()
        return frame

    def _set_chart_tool(self, tool):
        self.property_chart.tool = tool
        for name, button in (
            ("zoom", self.zoom_tool),
            ("select", self.select_tool),
            ("scroll", self.scroll_tool),
            ("cut", self.create_cut_button),
            ("hcut", self.create_horizontal_cut_button),
        ):
            button.setChecked(name == tool)
        cursor = Qt.ArrowCursor
        if tool in ("zoom", "cut", "hcut"):
            cursor = Qt.CrossCursor
        elif tool == "scroll":
            cursor = Qt.OpenHandCursor
        self.property_chart.setCursor(cursor)

    def _chart_zoom_in(self):
        if self.property_chart.chart_type == "Needle":
            self.property_chart.zoom_in()
        else:
            self.property_chart.set_plot_options(zoom=self.property_chart.zoom * 1.25)

    def _chart_zoom_out(self):
        if self.property_chart.chart_type == "Needle":
            self.property_chart.zoom_out()
        else:
            self.property_chart.set_plot_options(zoom=max(1.0, self.property_chart.zoom / 1.25))

    def _chart_zoom_fit(self):
        if self.property_chart.chart_type == "Needle":
            self.property_chart.zoom_fit()
        else:
            self.property_chart.set_plot_options(zoom=1.0)

    def _chart_back(self):
        self.property_chart.view_back()

    def _chart_forward(self):
        self.property_chart.view_forward()

    def _toggle_density(self):
        self.property_chart.density = self.density_button.isChecked()
        self.property_chart.update()

    def _toggle_chart_grid(self):
        self.property_grid = self.grid_button.isChecked()
        self.property_chart.set_plot_options(grid=self.property_grid)

    def _toggle_chart_legend(self):
        self.property_legend_on = self.legend_button.isChecked()
        self.legend_frame.setVisible(self.property_legend_on)

    def _hide_chart_legend(self):
        self.legend_button.setChecked(False)
        self._toggle_chart_legend()

    def _set_chart_group_size(self, size):
        self.property_chart.set_plot_options(group_size=size)

    def _set_chart_scale(self, scale):
        self.property_scale = scale
        self.property_chart.set_plot_options(scale=scale)

    def _sync_chart_history(self):
        self.chart_back.setEnabled(bool(self.property_chart.history))
        self.chart_forward.setEnabled(bool(self.property_chart.future))

    def _remember_cut(self, index):
        cuts = self.property_chart.cut_lines
        if 0 <= index < len(cuts):
            self.property_chart.selected_y_cut = None
            self._active_cut_value = cuts[index]
            self._active_cut_axis = "x"
            self.cut_value.setValue(cuts[index])
        self.delete_cut_button.setEnabled(0 <= index < len(cuts))

    def _remember_horizontal_cut(self, index):
        cuts = self.property_chart.y_cut_lines
        if 0 <= index < len(cuts):
            self.property_chart.selected_cut = None
            self._active_cut_value = cuts[index]
            self._active_cut_axis = "y"
            self.cut_value.setValue(cuts[index])
        self.delete_cut_button.setEnabled(0 <= index < len(cuts))

    def _region_selection_changed(self, _region=None):
        regions = sorted(self.property_chart.selected_regions)
        node = self._selected_node()
        groups = (node or {}).get("region_groups") or {}
        pending = bool(getattr(self, "_pending_cut_changes", False))
        self.group_button.setEnabled(not pending and len(regions) == 2)
        self.ungroup_button.setEnabled(
            not pending and any(str(region) in groups for region in regions)
        )
        self.rename_button.setEnabled(not pending and len(regions) == 1)

    def _toggle_group_labels(self, checked=False):
        checked = bool(checked)
        self.show_labels.setChecked(checked)
        self.property_chart.region_labels_on = checked
        self.property_chart.update()
        self.classifier_canvas.update()

    def _apply_or_insert_cut(self):
        node = self._selected_node()
        if node is None or node.get("locked"):
            return
        cuts = sorted(float(item) for item in self.property_chart.cut_lines)
        y_cuts = sorted(float(item) for item in self.property_chart.y_cut_lines)
        selected_y = self.property_chart.selected_y_cut
        if selected_y is not None and 0 <= selected_y < len(y_cuts):
            y_cuts[selected_y] = self.cut_value.value()
            self.property_chart.set_y_cut_lines(sorted(set(y_cuts)))
            self._active_cut_axis = "y"
        else:
            selected = self.property_chart.selected_cut
            if selected is not None and 0 <= selected < len(cuts):
                cuts[selected] = self.cut_value.value()
                self.property_chart.set_cut_lines(sorted(set(cuts)))
                self._active_cut_axis = "x"
            elif self.property_chart.tool == "hcut" and self.create_horizontal_cut_button.isEnabled():
                y_cuts.append(self.cut_value.value())
                self.property_chart.set_y_cut_lines(sorted(set(y_cuts)))
                self._active_cut_axis = "y"
            else:
                cuts.append(self.cut_value.value())
                self.property_chart.set_cut_lines(sorted(set(cuts)))
                self._active_cut_axis = "x"
        self._active_cut_value = float(self.cut_value.value())
        self._commit_chart_cuts(node)

    def _commit_chart_cuts(self, node):
        cuts = sorted(set(float(value) for value in self.property_chart.cut_lines))
        y_cuts = sorted(set(float(value) for value in self.property_chart.y_cut_lines))
        count_changed = (
            len(cuts) != len(node.get("cuts") or [])
            or len(y_cuts) != len(node.get("y_cuts") or [])
        )
        node["cuts"] = cuts
        node["y_cuts"] = y_cuts
        if count_changed:
            node["region_groups"] = {}
            self.property_chart.selected_regions = set()
        self._pending_cut_changes = False
        self._sync_region_children(node)
        self._node_changed()

    def _place_horizontal_cut_at(self, value):
        self.cut_value.setValue(float(value))
        self._active_cut_value = float(value)
        self._active_cut_axis = "y"
        cuts = sorted(set(self.property_chart.y_cut_lines + [float(value)]))
        self.property_chart.set_y_cut_lines(cuts)
        self.property_chart.selected_y_cut = min(
            range(len(cuts)), key=lambda index: abs(cuts[index] - float(value))
        )
        self.property_chart.selected_cut = None
        self._pending_cut_changes = True
        self._region_selection_changed()
        self.property_chart.update()

    def _move_horizontal_chart_cut(self, index, value):
        cuts = sorted(float(item) for item in self.property_chart.y_cut_lines)
        if index >= len(cuts):
            return
        cuts[index] = float(value)
        cuts = sorted(set(cuts))
        self.property_chart.set_y_cut_lines(cuts)
        self.property_chart.selected_y_cut = min(
            range(len(cuts)), key=lambda item: abs(cuts[item] - float(value))
        )
        self._active_cut_value = float(value)
        self._active_cut_axis = "y"
        self.cut_value.setValue(float(value))
        self._pending_cut_changes = True
        self._region_selection_changed()
        self.property_chart.update()

    def _place_cut_at(self, value):
        self.cut_value.setValue(float(value))
        self._active_cut_value = float(value)
        self._active_cut_axis = "x"
        cuts = sorted(set(self.property_chart.cut_lines + [float(value)]))
        self.property_chart.set_cut_lines(cuts)
        self.property_chart.selected_cut = min(
            range(len(cuts)), key=lambda index: abs(cuts[index] - float(value))
        )
        self.property_chart.selected_y_cut = None
        self._pending_cut_changes = True
        self._region_selection_changed()
        self.property_chart.update()

    def _move_chart_cut(self, index, value):
        cuts = sorted(float(item) for item in self.property_chart.cut_lines)
        if index >= len(cuts):
            return
        cuts[index] = float(value)
        cuts = sorted(set(cuts))
        self.property_chart.set_cut_lines(cuts)
        self.property_chart.selected_cut = min(
            range(len(cuts)), key=lambda item: abs(cuts[item] - float(value))
        )
        self._active_cut_value = float(value)
        self._active_cut_axis = "x"
        self.cut_value.setValue(float(value))
        self._pending_cut_changes = True
        self._region_selection_changed()
        self.property_chart.update()

    def _legend_swatch(self, color):
        pixmap = QPixmap(22, 12)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setPen(QColor("#202020"))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(1, 2, 7, 7)
        painter.setBrush(QColor(color))
        painter.drawRect(12, 1, 8, 8)
        painter.end()
        label = QLabel()
        label.setPixmap(pixmap)
        return label

    def _fill_property_legend(self, entries):
        while self.legend_rows.count():
            item = self.legend_rows.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        labels = [entry["label"] for entry in entries]
        self._legend_names = list(labels)
        for entry in entries:
            label = entry["label"]
            row = QWidget()
            row.setStyleSheet("background: transparent;")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(4)
            eye = QToolButton()
            eye.setIcon(self._eye_icon(label not in self.legend_hidden))
            eye.setAutoRaise(True)
            eye.setFixedSize(15, 15)
            eye.setCheckable(True)
            eye.setChecked(label not in self.legend_hidden)
            eye.setStyleSheet("QToolButton { border: none; background: transparent; }")
            eye.clicked.connect(lambda shown, name=label: self._toggle_legend_row(name, bool(shown)))
            row_layout.addWidget(eye)
            row_layout.addWidget(self._color_square(entry["color"]))
            text = QLabel(str(label))
            text.setStyleSheet("font-size: 11px; color: #1f1f1f; border: none; background: transparent;")
            row_layout.addWidget(text)
            row_layout.addStretch(1)
            self.legend_rows.addWidget(row)

    def _eye_icon(self, open_eye):
        pixmap = QPixmap(16, 12)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(QPen(QColor("#202020"), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(1, 3, 14, 7)
        if open_eye:
            painter.setBrush(QColor("#202020"))
            painter.drawEllipse(6, 4, 4, 4)
        else:
            painter.drawLine(2, 10, 14, 2)
        painter.end()
        return QIcon(pixmap)

    def _color_square(self, color):
        pixmap = QPixmap(12, 12)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setPen(QColor("#202020"))
        painter.setBrush(QColor(color))
        painter.drawRect(1, 1, 9, 9)
        painter.end()
        label = QLabel()
        label.setPixmap(pixmap)
        return label

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
        self._pending_cut_changes = False
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
            defects = list(self.review_result.get("defects", []))
            total = len(defects)
            hidden = {str(value) for value in self.hidden_defect_ids}
            eliminated = sum(str(defect.get("id")) in hidden for defect in defects)
            population = self._display_defects(node)
            current = len(population)
            self._refresh_summary(defects, population)
            label = node.get("name") or node.get("type") or "Node"
            message = f"{label}: {current}/{total} defects"
            if eliminated:
                message += f" - {eliminated} tuned-out by ST (included in root)"
            self.status.setText(message)
        if hasattr(self, "classifier_canvas"):
            self.classifier_canvas.update()
        if hasattr(self, "delete_node_button"):
            locked = bool(node.get("locked"))
            is_root = node.get("parent_id") is None
            self.starter_tree_button.setEnabled(not locked)
            self.delete_node_button.setEnabled(not is_root and not locked)
            self.nuisance_button.setEnabled(not is_root and not locked)
        self._refresh_histograms()

    def _refresh_summary(self, defects, population):
        """Write the shared Class Code Summary List for the selected node."""
        if not hasattr(self, "summary_panel"):
            return

        def code_of(defect):
            return _summary_code_label(defect.get("class_code", 0))

        test_counts = Counter(code_of(item) for item in defects)
        node_counts = Counter(code_of(item) for item in population)
        columns = _summary_code_sort(test_counts)
        current_cells = {
            code: f"{node_counts.get(code, 0)}/{test_counts[code]}" for code in columns
        }
        test_cells = {code: f"{test_counts[code]}/{test_counts[code]}" for code in columns}
        current = len(population)
        total = len(defects)
        classified = sum(1 for item in population if _stnef_int(item.get("class_code")) != 0)
        note = (
            f"{classified}/{current} defects in this node classified by ST-NEF; "
            f"{total} in the test."
        )
        self.summary_panel.set_summary(
            columns,
            [
                ("Current", current_cells, f"{current}/{total}"),
                ("Test", test_cells, f"{total}/{total}"),
            ],
            note,
        )
        self.summary_panel.select_row("Current")

    def _refresh_histograms(self):
        if not hasattr(self, "histogram_layout"):
            return
        while self.histogram_layout.count():
            item = self.histogram_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not getattr(self, "attributes_expanded", True):
            return
        defects = self._display_defects(self._selected_node())
        log_scale = self.log_histogram.isChecked()
        for title in self.CONTINUOUS_ATTRIBUTES + self.DISCRETE_ATTRIBUTES:
            labels, ordered = self._attribute_histogram(title, defects)
            selected = title in ((self._selected_node() or {}).get("attributes") or [])
            card = _AttributeHistogram(
                title, ordered,
                lambda shift=False, name=title: self._apply_attribute(name, additive=bool(shift)),
                labels=labels, log_scale=log_scale, selected=selected,
            )
            self.histogram_layout.addWidget(card)
        self.histogram_layout.addStretch(1)

    def _apply_histogram_attribute(self, name):
        matches = self.toolbox.findItems(name, Qt.MatchExactly | Qt.MatchRecursive)
        if matches:
            self._toolbox_double_clicked(matches[0], 0)

    @staticmethod
    def _numeric_defect_id(defect):
        identifier = defect.get("id", 0)
        try:
            return int(identifier)
        except (TypeError, ValueError):
            return sum(ord(character) for character in str(identifier))

    def _base_defects(self):
        defects = list(self.review_result.get("defects", []))
        if not self.view_all.isChecked():
            defects = [
                defect for defect in defects
                if not defect.get("binner_filtered")
            ]
        if self.hide_unclassified.isChecked():
            defects = [
                defect for defect in defects
                if _stnef_int(defect.get("class_code")) != 0
            ]
        return defects

    def _population_signature(self):
        return (
            self.hide_unclassified.isChecked(),
            self.view_all.isChecked(),
            tuple(
                (
                    node.get("id"),
                    node.get("parent_id"),
                    tuple(name for name in (node.get("attributes") or []) if name),
                    tuple(node.get("cuts") or []),
                    tuple(node.get("y_cuts") or []),
                    bool(node.get("nuisance")),
                    node.get("type"),
                    tuple(
                        (
                            str(partition.get("name") or ""),
                            tuple(str(value) for value in partition.get("classes") or []),
                        )
                        for partition in node.get("partitions") or []
                    ),
                )
                for node in self.nodes
            ),
        )

    def _tree_populations(self, defects=None):
        if defects is not None:
            return _stnef_populations(
                self.nodes,
                list(defects),
                self._attribute_number,
                self._attribute_text,
                self._partition_name,
            )
        signature = self._population_signature()
        cached = self._population_cache
        if cached is not None and cached[0] == signature:
            return cached[1]
        populations = _stnef_populations(
            self.nodes,
            self._base_defects(),
            self._attribute_number,
            self._attribute_text,
            self._partition_name,
        )
        self._population_cache = (signature, populations)
        return populations

    def _display_defects(self, node):
        if node is None:
            return self._base_defects()
        return self._tree_populations().get(node.get("id"), [])

    def _defect_branch_index(self, node, defect, child_count, children=None):
        siblings = list(children or _stnef_children(self.nodes, node))
        if child_count < 2 or len(siblings) != child_count:
            return None
        parts = _stnef_partition(
            node,
            [defect],
            siblings,
            self._attribute_number,
            self._attribute_text,
            self._partition_name,
        )
        for index, child in enumerate(siblings):
            if any(item is defect for item in parts.get(child.get("id"), [])):
                return index
        return None

    def _nuisance_defect_ids(self):
        return _stnef_nuisance_ids(
            self.nodes,
            self._base_defects(),
            self._attribute_number,
            self._attribute_text,
            self._partition_name,
        )

    def _partition_cuts(self, node):
        cuts = []
        for value in (node or {}).get("cuts") or []:
            try:
                cuts.append(float(value))
            except (TypeError, ValueError):
                continue
        return sorted(cuts)

    def _partition_layout(self, node):
        node = node or {}
        cuts = self._partition_cuts(node)
        y_cuts = []
        for value in node.get("y_cuts") or []:
            try:
                y_cuts.append(float(value))
            except (TypeError, ValueError):
                continue
        y_cuts.sort()
        names = {
            str(key): str(value).strip()
            for key, value in (node.get("region_names") or {}).items()
        }
        groups = {}
        for key, value in (node.get("region_groups") or {}).items():
            number = self._class_number(value)
            if number is not None:
                groups[str(key)] = number
        children = [
            str(child.get("name") or "")
            for child in _stnef_children(self.nodes, node)
            if child.get("type") == "Bucket" and str(child.get("name") or "").strip()
        ]
        signature = (
            node.get("id"),
            tuple(cuts),
            tuple(y_cuts),
            tuple(sorted(groups.items())),
            tuple(sorted(names.items())),
            tuple(children),
        )
        cached = getattr(self, "_partition_cache", None)
        if cached and cached[0] == signature:
            return cached[1]
        attribute = next((name for name in (node.get("attributes") or []) if name), None)
        region_keys = {}
        key_order = []
        key_labels = {}
        region_count = (len(cuts) + 1) * (len(y_cuts) + 1)
        for region in range(region_count):
            group = groups.get(str(region))
            key = f"group:{group}" if group is not None else f"region:{region}"
            region_keys[region] = key
            if key not in key_labels:
                key_order.append(key)
                key_labels[key] = ""
            label = names.get(str(region), "")
            if label and not key_labels[key]:
                key_labels[key] = label
        for index, key in enumerate(key_order):
            if not key_labels[key]:
                key_labels[key] = self._partition_letter(index)
        buckets = {}
        labels = []
        if cuts or y_cuts:
            labels = [key_labels[key] for key in key_order]
        elif attribute and children:
            for name in children:
                buckets[name] = name
                labels.append(name)
        elif attribute:
            # A node with an attribute but no cut yet is a single group; the
            # legend must show that one group instead of falling back to a class.
            key = region_keys.get(0)
            labels = [key_labels.get(key) or self._partition_letter(0)]
        fallback = not labels
        layout = {
            "cuts": cuts,
            "y_cuts": y_cuts,
            "attribute": attribute,
            "region_keys": region_keys,
            "key_labels": key_labels,
            "labels": labels or [self.FALLBACK_LEGEND_LABEL],
            "buckets": buckets,
            "fallback": fallback,
        }
        self._partition_cache = (signature, layout)
        return layout

    @staticmethod
    def _partition_letter(index):
        return f"Group {index + 1}"

    def _partition_label(self, defect, node):
        layout = self._partition_layout(node)
        cuts = layout["cuts"]
        y_cuts = layout.get("y_cuts") or []
        if cuts or y_cuts:
            region = self._defect_region_index(defect, node)
            key = layout["region_keys"].get(region)
            return layout["key_labels"].get(key) or layout["labels"][0]
        buckets = layout["buckets"]
        if buckets:
            attribute = layout["attribute"]
            text = self._attribute_text(defect, attribute) if attribute else None
            if text is not None and str(text) in buckets:
                return buckets[str(text)]
        return layout["labels"][0]

    def _defect_region_index(self, defect, node):
        layout = self._partition_layout(node)
        cuts = layout["cuts"]
        y_cuts = layout.get("y_cuts") or []
        attributes = [name for name in (node or {}).get("attributes") or [] if name]
        x_attribute = attributes[0] if attributes else None
        y_attribute = attributes[1] if len(attributes) >= 2 else None
        x_value = self._attribute_number(defect, x_attribute) if x_attribute else None
        y_value = self._attribute_number(defect, y_attribute) if y_attribute else None
        x_region = len(cuts) if x_value is None else min(
            sum(x_value >= cut for cut in cuts), len(cuts)
        )
        y_region = (
            len(y_cuts)
            if y_cuts and y_value is None
            else sum((y_value or 0) >= cut for cut in y_cuts)
        )
        return y_region * (len(cuts) + 1) + x_region

    def _legend_mode(self):
        return self.legend.currentText() or "Manual Classes"

    def _legend_mode_changed(self, *_args):
        self.legend_hidden.clear()
        self._grouped_legend_names.clear()
        self._refresh_property_chart()
        if hasattr(self, "classifier_canvas"):
            self.classifier_canvas.update()

    def _select_partitions_mode(self):
        if hasattr(self, "legend") and self.legend.currentText() != "Partitions":
            self.legend.setCurrentText("Partitions")

    @staticmethod
    def _class_number(value):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    def _legend_key(self, defect, node):
        mode = self._legend_mode()
        if mode == "Partitions":
            return self._partition_label(defect, node)
        field = self.LEGEND_CLASS_FIELDS.get(mode, "manual_class")
        if field == "super_class":
            name = defect.get("super_class")
            if isinstance(name, str) and name.strip():
                return name.strip()
            code = self._class_number(defect.get("class_code"))
            return f"Class {code if code is not None else 0}"
        code = self._class_number(defect.get(field))
        if code is None:
            code = self._class_number(defect.get("class_code"))
        return f"Class {code if code is not None else 0}"

    def _class_color(self, label):
        text = str(label)
        code = self._class_number(text.split()[-1]) if text.startswith("Class ") else None
        if code is None:
            code = sum(ord(character) for character in text)
        return self.CLASS_COLORS[code % len(self.CLASS_COLORS)]

    @staticmethod
    def _ordered_labels(values):
        labels = []
        for value in values:
            if value is None:
                continue
            label = str(value)
            if label not in labels:
                labels.append(label)
        return labels

    def _sort_class_labels(self, labels):
        def key(label):
            if str(label).startswith("Class "):
                code = self._class_number(str(label).split()[-1])
                if code is not None:
                    return (0, code, "")
            return (1, 0, str(label))
        return sorted(labels, key=key)

    def _legend_entries(self, node, defects):
        mode = self._legend_mode()
        if mode == "Partitions":
            layout = self._partition_layout(node)
            labels = list(layout["labels"]) or [self.FALLBACK_LEGEND_LABEL]
            if layout.get("fallback"):
                return [{"label": labels[0], "color": self._class_color(labels[0])}]
            grouped = set(getattr(self, "_grouped_legend_names", set()))
            return [
                {
                    "label": label,
                    "color": self.LEGEND_COLORS[0] if label in grouped
                    else self.LEGEND_COLORS[index % len(self.LEGEND_COLORS)],
                }
                for index, label in enumerate(labels)
            ]
        labels = self._sort_class_labels(
            self._ordered_labels(self._legend_key(defect, node) for defect in defects)
        )
        if not labels:
            labels = [self.FALLBACK_LEGEND_LABEL]
        grouped = set(getattr(self, "_grouped_legend_names", set()))
        grouped_color = self.CLASS_COLORS[0]
        return [
            {
                "label": label,
                "color": grouped_color if label in grouped else self._class_color(label),
            }
            for label in labels
        ]

    def _refresh_property_chart(self):
        node = self._selected_node()
        attributes = (node or {}).get("attributes") or []
        title = "Properties"
        if len(attributes) == 1:
            title = f"{attributes[0]} Attribute Properties"
        elif len(attributes) >= 2:
            title = f"{attributes[0]} Vs {attributes[1]} Properties"
        if hasattr(self, "properties_frame") and hasattr(self.properties_frame, "title_label"):
            self.properties_frame.title_label.setText(title)
        self.attribute_label.setText("" if attributes else "Select the wafer node and double-click an attribute.")
        if not attributes:
            self.legend_controls.hide()
            self.property_chart.set_counts({}, title)
            self.property_chart.set_cut_lines([])
            self.property_chart.set_y_cut_lines([])
            self.create_horizontal_cut_button.setEnabled(False)
            fallback = self.FALLBACK_LEGEND_LABEL
            self._fill_property_legend([
                {"label": fallback, "color": self._class_color(fallback)}
            ])
            return
        defects = self._display_defects(node)
        self._sync_legend_choices()
        entries = self._legend_entries(node, defects)
        colors = {entry["label"]: entry["color"] for entry in entries}
        plot = len(attributes) >= 2 or self._attribute_is_plot(attributes[0], defects)
        self.legend_controls.setVisible(len(attributes) == 1 and not plot)
        if len(attributes) >= 2:
            self._needle_key = None
            points, y_labels, point_colors = self._attribute_points(
                defects, attributes[0], attributes[1], node, colors
            )
            self.property_chart.set_points(
                points,
                "",
                colors=point_colors,
                legend_items=[(entry["label"], entry["color"]) for entry in entries],
                y_labels=y_labels,
                axis_x=self._axis_name(attributes[0]),
                axis_y=self._axis_name(attributes[1]),
            )
            self.property_chart.set_cut_lines((node or {}).get("cuts") or [])
            self.property_chart.set_y_cut_lines((node or {}).get("y_cuts") or [])
            self.create_horizontal_cut_button.setEnabled(y_labels is None)
            self._apply_chart_chrome(node)
            self._fill_property_legend(entries)
            return
        if plot:
            raw = []
            point_colors = []
            for defect in defects:
                value = self._attribute_raw(defect, attributes[0])
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    continue
                name = self._legend_key(defect, node)
                if name is None or name in self.legend_hidden:
                    continue
                raw.append(float(value))
                point_colors.append(colors.get(name, "#9e9e9e"))
            reset = getattr(self, "_needle_key", None) != attributes[0]
            self._needle_key = attributes[0]
            self.property_chart.set_needle(
                raw, axis_x=self._axis_name(attributes[0]), reset_view=reset, colors=point_colors,
            )
        else:
            self._needle_key = None
            self._set_class_bars(defects, attributes[0], entries)
        self.property_chart.set_cut_lines((node or {}).get("cuts") or [])
        self.property_chart.set_y_cut_lines([])
        self.create_horizontal_cut_button.setEnabled(False)
        if self.property_chart.tool == "hcut":
            self._set_chart_tool("select")
        self._apply_chart_chrome(node)
        self._fill_property_legend(entries)

    def _attribute_is_plot(self, name, defects):
        if name in self.DISCRETE_ATTRIBUTES:
            return False
        present = [self._attribute_raw(defect, name) for defect in defects]
        present = [value for value in present if value is not None]
        return bool(present) and all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in present)

    def _sync_legend_choices(self):
        items = list(self.LEGEND_MODES)
        current = [self.legend.itemText(index) for index in range(self.legend.count())]
        if current == items:
            return
        selected = self.legend.currentText()
        self.legend.blockSignals(True)
        self.legend.clear()
        self.legend.addItems(items)
        self.legend.setCurrentText(selected if selected in items else "Partitions")
        self.legend.blockSignals(False)

    def _set_class_bars(self, defects, attribute, entries):
        node = self._selected_node()
        label_order = []
        buckets = {}
        for defect in defects:
            value = self._attribute_raw(defect, attribute)
            if value is None:
                continue
            name = self._legend_key(defect, node)
            if name is None or name in self.legend_hidden:
                continue
            label = str(value)
            if label not in label_order:
                label_order.append(label)
            buckets.setdefault(name, Counter())[label] += 1
        if attribute == "Channel Detected":
            preferred = (
                "Ch Other", "Ch 1 Unique", "Ch 2 Unique", "Ch 1 2 Unique",
                "Ch 3 Unique", "Ch 1 3 Unique", "Ch 2 3 Unique", "Ch 1 2 3 Unique",
            )
            label_order = [item for item in preferred if item in label_order] + [
                item for item in label_order if item not in preferred
            ]
        series = []
        for entry in entries:
            counts = buckets.get(entry["label"])
            if counts:
                series.append({
                    "name": entry["label"],
                    "color": entry["color"],
                    "counts": dict(counts),
                })
        if series and label_order:
            self.property_chart.set_partition_bars(label_order, series, "")
        else:
            self.property_chart.set_counts({}, "", "Bar", axis_x=self._axis_name(attribute), axis_y="Defect Count")

    def _select_all_legend(self):
        self.legend_hidden.clear()
        self._refresh_property_chart()

    def _deselect_all_legend(self):
        self.legend_hidden = set(getattr(self, "_legend_names", []))
        self._refresh_property_chart()

    def _group_legend_classes(self):
        self._grouped_legend_names = {name for name in getattr(self, "_legend_names", []) if name not in self.legend_hidden}
        self._refresh_property_chart()

    def _ungroup_legend_classes(self):
        self._grouped_legend_names = set()
        self._refresh_property_chart()

    def _toggle_legend_row(self, name, shown):
        if shown:
            self.legend_hidden.discard(name)
        else:
            self.legend_hidden.add(name)
        self._refresh_property_chart()

    def _chart_region_names(self, node):
        names = {
            str(key): str(value)
            for key, value in ((node or {}).get("region_names") or {}).items()
        }
        layout = self._partition_layout(node)
        if self._legend_mode() == "Partitions":
            for region, key in layout["region_keys"].items():
                label = layout["key_labels"].get(key)
                if label:
                    names[str(region)] = label
            return names
        by_region = {}
        for defect in self._display_defects(node):
            region = self._defect_region_index(defect, node)
            label = self._legend_key(defect, node)
            if label is not None:
                by_region.setdefault(region, Counter())[label] += 1
        for region, counts in by_region.items():
            if counts:
                names[str(region)] = counts.most_common(1)[0][0]
        return names

    def _tree_branch_label(self, parent, child, index):
        if self._legend_mode() == "Partitions":
            layout = self._partition_layout(parent)
            key = layout.get("region_keys", {}).get(index)
            return str(layout.get("key_labels", {}).get(key) or "")
        counts = Counter(
            self._legend_key(defect, parent)
            for defect in self._display_defects(child)
        )
        counts.pop(None, None)
        return str(counts.most_common(1)[0][0]) if counts else ""

    def _apply_chart_chrome(self, node):
        self.property_chart.set_plot_options(scale=self.property_scale, grid=self.property_grid)
        self.property_chart.region_labels_on = self.show_labels.isChecked()
        self.property_chart.region_names = self._chart_region_names(node)
        self.property_chart.region_groups = dict((node or {}).get("region_groups") or {})
        region_count = (
            (len((node or {}).get("cuts") or []) + 1)
            * (len((node or {}).get("y_cuts") or []) + 1)
        )
        self.property_chart.selected_regions = {
            region for region in self.property_chart.selected_regions
            if 0 <= region < region_count
        }
        active = getattr(self, "_active_cut_value", None)
        cuts = self.property_chart.cut_lines
        y_cuts = self.property_chart.y_cut_lines
        axis = getattr(self, "_active_cut_axis", "x")
        if active is not None and axis == "y" and y_cuts:
            self.property_chart.selected_y_cut = min(
                range(len(y_cuts)), key=lambda index: abs(y_cuts[index] - active)
            )
            self.property_chart.selected_cut = None
        elif active is not None and cuts:
            self.property_chart.selected_cut = min(range(len(cuts)), key=lambda index: abs(cuts[index] - active))
            self.property_chart.selected_y_cut = None
        self._region_selection_changed()

    def _axis_name(self, attribute):
        if attribute == "Area":
            return "Area(µm²)"
        return attribute

    def _channel_detected_label(self, defect):
        bits = []
        has_channel_data = False
        for index, key in enumerate(("ch1_intensity", "ch2_intensity", "ch3_intensity"), start=1):
            value = defect.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool) and float(value) > 0:
                bits.append(index)
            if key in defect and value is not None:
                has_channel_data = True
        if not bits:
            raw_channels = defect.get("channels")
            if isinstance(raw_channels, (list, tuple)):
                has_channel_data = True
                bits = [int(value) for value in raw_channels if str(value).isdigit() and int(value) in (1, 2, 3)]
        if not bits:
            channel = defect.get("channel")
            if channel not in (None, ""):
                has_channel_data = True
            try:
                channel = int(channel)
            except (TypeError, ValueError):
                channel = 0
            if channel in (1, 2, 3):
                bits = [channel]
        if not bits:
            return "Ch Other" if has_channel_data else None
        if len(bits) == 1:
            return f"Ch {bits[0]} Unique"
        return "Ch " + " ".join(str(bit) for bit in bits) + " Unique"

    def _attribute_raw(self, defect, name):
        if name == "Channel Detected":
            return self._channel_detected_label(defect)
        if name == "Radius":
            x_value = defect.get("x_um", defect.get("xrel"))
            y_value = defect.get("y_um", defect.get("yrel"))
            if isinstance(x_value, (int, float)) and isinstance(y_value, (int, float)):
                return math.hypot(float(x_value), float(y_value))
            return None
        if name == "Area":
            for key in ("area", "size_um"):
                if isinstance(defect.get(key), (int, float)) and not isinstance(defect.get(key), bool):
                    return float(defect[key])
            return None
        if name in ("Max Dim", "BBox Width"):
            for key in ("xsize", "max_dim", "size_um"):
                if isinstance(defect.get(key), (int, float)) and not isinstance(defect.get(key), bool):
                    return float(defect[key])
            return None
        if name in ("Min Dim", "BBox Height"):
            for key in ("ysize", "min_dim", "size_um"):
                if isinstance(defect.get(key), (int, float)) and not isinstance(defect.get(key), bool):
                    return float(defect[key])
            return None
        if name == "Primary Ch Intensity":
            for key in ("signal", "intensity", "hlat_intensity"):
                if isinstance(defect.get(key), (int, float)) and not isinstance(defect.get(key), bool):
                    return float(defect[key])
            return None
        key = self.ATTRIBUTE_KEYS.get(name)
        if not key:
            return None
        value = defect.get(key)
        if value is None or value == "":
            return None
        return value

    def _attribute_histogram(self, name, defects):
        if name == "Channel Detected":
            order = (
                "Ch Other", "Ch 1 Unique", "Ch 2 Unique", "Ch 1 2 Unique",
                "Ch 3 Unique", "Ch 1 3 Unique", "Ch 2 3 Unique", "Ch 1 2 3 Unique",
            )
            counts = Counter(
                label for label in (self._channel_detected_label(defect) for defect in defects)
                if label is not None
            )
            labels = [label for label in order if counts.get(label)]
            labels.extend(label for label in counts if label not in labels)
            return labels, [counts[label] for label in labels]
        values = [self._attribute_raw(defect, name) for defect in defects]
        values = [value for value in values if value is not None]
        if not values:
            return [], []
        numeric = [value for value in values if isinstance(value, (int, float)) and not isinstance(value, bool)]
        if len(numeric) == len(values):
            low, high = min(numeric), max(numeric)
            if low == high:
                return [f"{low:g}"], [len(numeric)]
            bin_count = min(24, max(4, len({round(value, 3) for value in numeric})))
            span = high - low or 1.0
            ordered = [0] * bin_count
            labels = []
            for index in range(bin_count):
                edge = low + span * index / bin_count
                labels.append(f"{edge:.4g}")
            for value in numeric:
                index = min(bin_count - 1, int((float(value) - low) / span * bin_count))
                ordered[index] += 1
            return labels, ordered
        counts = Counter(str(value) for value in values)
        labels = list(counts)
        return labels, [counts[label] for label in labels]

    def _attribute_points(self, defects, x_name, y_name, node, colors):
        pairs = []
        for defect in defects:
            x_value = self._attribute_raw(defect, x_name)
            y_value = self._attribute_raw(defect, y_name)
            if x_value is None or y_value is None:
                continue
            pairs.append((defect, x_value, y_value))
        y_numeric = all(isinstance(value, (int, float)) and not isinstance(value, bool) for _defect, _x, value in pairs)
        x_numeric = all(isinstance(value, (int, float)) and not isinstance(value, bool) for _defect, value, _y in pairs)

        def color_of(defect):
            return (colors or {}).get(self._legend_key(defect, node), "#9e9e9e")

        if y_numeric and x_numeric:
            points = [(float(x_value), float(y_value)) for _defect, x_value, y_value in pairs]
            return points, None, [color_of(defect) for defect, _x, _y in pairs]
        categories = []
        for _defect, _x, y_value in pairs:
            label = str(y_value)
            if label not in categories:
                categories.append(label)
        if "Dark" in categories and "Bright" in categories:
            categories = [label for label in categories if label not in ("Dark", "Bright")] + ["Bright", "Dark"]
        index = {label: position for position, label in enumerate(categories)}
        points = []
        point_colors = []
        for defect, x_value, y_value in pairs:
            if not isinstance(x_value, (int, float)) or isinstance(x_value, bool):
                continue
            points.append((float(x_value), float(index[str(y_value)])))
            point_colors.append(color_of(defect))
        return points, categories, point_colors

    def _add_node(self, parent_id, name, node_type, **values):
        node = {
            "id": self.next_node_id, "parent_id": parent_id, "name": name, "type": node_type,
            "attributes": [], "cuts": [], "y_cuts": [], "groups": {}, "partitions": [],
            "locked": False, "nuisance": False,
        }
        node.update(values)
        self.next_node_id += 1
        self.nodes.append(node)
        self._rebuild_tree(node["id"])
        return node

    def _classified_defects(self, node):
        defects = self._display_defects(node)
        classified = [
            defect for defect in defects
            if defect.get("class_code") not in (None, "", 0, "0")
        ]
        return classified or defects

    def _attribute_number(self, defect, attribute):
        value = self._attribute_raw(defect, attribute)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        return None

    def _attribute_text(self, defect, attribute):
        return _stnef_attribute_text(self._attribute_raw(defect, attribute))

    def _class_codes(self):
        codes = set()
        for defect in self.review_result.get("defects", []):
            try:
                codes.add(int(defect.get("class_code")))
            except (TypeError, ValueError):
                continue
        return sorted(codes)

    def _partition_name(self, defect, partitions):
        try:
            code = int(defect.get("class_code"))
        except (TypeError, ValueError):
            return None
        for partition in partitions or []:
            if code in [int(value) for value in partition.get("classes", []) if str(value).lstrip("-").isdigit()]:
                return partition.get("name")
        return None

    def _split_threshold(self, defects, attribute, partitions=None):
        pairs = [
            (defect, self._attribute_number(defect, attribute))
            for defect in defects
        ]
        pairs = [(defect, value) for defect, value in pairs if value is not None]
        if not pairs:
            return 0.0
        values = [value for _defect, value in pairs]
        ordered = sorted(values)
        median = round(ordered[len(ordered) // 2], 2)
        labeled = [
            (value, self._partition_name(defect, partitions))
            for defect, value in pairs
        ]
        names = {name for _value, name in labeled if name}
        if len(names) < 2:
            return median
        best_cut = median
        best_score = -1.0
        for cut in sorted({round(value, 2) for value in values}):
            left = [name for value, name in labeled if value < cut]
            right = [name for value, name in labeled if value >= cut]
            if not left or not right:
                continue
            score = (max(Counter(left).values()) / len(left)) + (max(Counter(right).values()) / len(right))
            if score > best_score:
                best_score = score
                best_cut = cut
        return best_cut

    def _canvas_tree_root(self):
        node = self._selected_node()
        if node is None:
            node = next((item for item in self.nodes if item.get("parent_id") is None), None)
        if node is None:
            return None
        root = node
        visited = set()
        while root.get("parent_id") is not None and root.get("id") not in visited:
            visited.add(root.get("id"))
            parent = self._node(root.get("parent_id"))
            if parent is None:
                break
            root = parent
        return root

    def _starter_tree(self):
        node = self._selected_node()
        if node is None or node.get("locked"):
            return
        defects = self._display_defects(node)
        classified = [
            defect for defect in defects
            if defect.get("class_code") not in (None, "", 0, "0")
        ]
        dialog = StarterTreeGenerationDialog(
            self.CONTINUOUS_ATTRIBUTES + self.DISCRETE_ATTRIBUTES,
            node.get("partitions"),
            self,
            classified_count=len(classified),
            population=len(defects),
            class_codes=self._class_codes(),
        )
        if _exec(dialog) == QDialog.Accepted and dialog.result_settings:
            self._generate_starter_tree(dialog.result_settings)

    def _append_raw_node(self, parent_id, name, node_type, **values):
        node = {
            "id": self.next_node_id, "parent_id": parent_id, "name": name, "type": node_type,
            "attributes": [], "cuts": [], "y_cuts": [], "groups": {}, "partitions": [],
            "locked": False, "nuisance": False,
        }
        node.update(values)
        self.next_node_id += 1
        self.nodes.append(node)
        return node

    def _append_starter_branches(self, parent, attributes, defects, depth, partitions=None):
        attribute = attributes[depth] if depth < len(attributes) else parent.get("name")
        threshold = (parent.get("cuts") or [self._split_threshold(defects, attribute, partitions)])[0]
        next_attribute = attributes[depth + 1] if depth + 1 < len(attributes) else None
        measured = [
            (defect, self._attribute_number(defect, attribute))
            for defect in defects
        ]
        measured = [(defect, value) for defect, value in measured if value is not None]
        if not measured:
            self._append_raw_node(parent["id"], "", "Bucket")
            return
        left = [defect for defect, value in measured if value < threshold]
        right = [defect for defect, value in measured if value >= threshold]
        for branch in (left, right):
            if not branch:
                continue
            if next_attribute is None or depth >= 2:
                self._append_raw_node(parent["id"], "", "Bucket")
                continue
            cut = self._split_threshold(branch, next_attribute, partitions)
            child = self._append_raw_node(
                parent["id"], next_attribute, "Attribute",
                attributes=[next_attribute], cuts=[cut],
            )
            self._append_starter_branches(child, attributes, branch, depth + 1, partitions)

    def _generate_starter_tree(self, settings):
        node = self._selected_node()
        if node is None or node.get("locked"):
            return
        attributes = [name for name in (settings.get("attributes") or []) if name]
        if not attributes:
            attributes = ["Primary Ch Intensity", "Area"]
        chart_attributes = (attributes + ["Primary Ch Intensity", "Area"])[:2]
        partitions = deepcopy(settings.get("partitions") or [])
        node["partitions"] = partitions
        defects = self._classified_defects(node)
        threshold = self._split_threshold(defects, chart_attributes[0], partitions)
        generated = self._append_raw_node(
            node["id"], chart_attributes[0], "Attribute",
            attributes=list(chart_attributes), cuts=[threshold],
            partitions=deepcopy(node["partitions"]),
        )
        self._append_starter_branches(generated, attributes[:6], defects, 0, partitions)
        self._select_partitions_mode()
        self._rebuild_tree(generated["id"])
        self.status.setText(f"Starter Tree generated with {len(chart_attributes)} attribute(s).")

    def _show_nn_menu(self):
        menu = QMenu(self)
        menu.addAction("Add New NN Node", self._add_nn_node)
        menu.addAction("Create NEF Node", self._create_nef_node)
        menu.addSeparator()
        lock = menu.addAction("Lock NN", self._toggle_lock)
        lock.setCheckable(True)
        node = self._selected_node()
        lock.setChecked(bool(node and node.get("locked")))
        menu.exec(self.nn_classifier_button.mapToGlobal(self.nn_classifier_button.rect().bottomLeft()))

    def _show_node_menu(self, global_pos):
        menu = QMenu(self)
        menu.addAction("Add New NN Node", self._add_nn_node)
        menu.addAction("Create NEF Node", self._create_nef_node)
        menu.addAction("Delete Node", self._delete_node)
        menu.addAction("Mark As Nuisance", self._toggle_nuisance)
        menu.exec(global_pos)

    def _select_canvas_node(self, node_id):
        self._rebuild_tree(node_id)

    def _add_nn_node(self):
        node = self._selected_node()
        if node is None or node.get("locked"):
            return
        created = self._append_raw_node(node["id"], "NN Node", "NN")
        self._rebuild_tree(created["id"])

    def _create_nef_node(self):
        node = self._selected_node()
        if node is None or node.get("locked"):
            return
        parent_id = node["id"]
        self._append_raw_node(parent_id, "B", "NEF Partition")
        nuisance = self._append_raw_node(parent_id, "A", "NEF Partition", nuisance=True)
        self._rebuild_tree(nuisance["id"])

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
            additive = bool(QApplication.keyboardModifiers() & Qt.ShiftModifier)
            self._apply_attribute(attribute, additive=additive)

    def _apply_attribute(self, attribute, additive=False):
        node = self._selected_node()
        if node is None or node.get("locked"):
            return
        current = [name for name in (node.get("attributes") or []) if name]
        if additive:
            # Shift combines the second attribute on the attribute level the
            # tree already has below the selected node (or on the node itself).
            target = node if current else self._only_attribute_level(node)
            if target is not None:
                previous = [name for name in (target.get("attributes") or []) if name]
                merged = [name for name in (target.get("attributes") or []) if name][:1]
                if attribute not in merged:
                    merged.append(attribute)
                target["attributes"] = merged[:2]
                if previous[1:2] != target["attributes"][1:2]:
                    target["y_cuts"] = []
                    target["region_groups"] = {}
                    self._sync_region_children(target)
                target["type"] = "2-D Attribute" if len(merged) >= 2 else "1-D Attribute"
                self._select_partitions_mode()
                self._rebuild_tree(target["id"])
                return
        # A double-click never writes the attribute onto the selected node: it
        # always opens exactly one new level below it, even when that node is
        # the root (or an attribute node that already carries attributes).
        created = self._open_attribute_level(node, attribute)
        self._select_partitions_mode()
        self._rebuild_tree(created["id"])

    def _only_attribute_level(self, node):
        children = _stnef_children(self.nodes, node)
        if len(children) == 1 and self._is_attribute_level(children[0]):
            return children[0]
        return None

    def _open_attribute_level(self, node, attribute):
        """Place the attribute on the level directly below ``node``.

        The selected node itself is never rewritten, so the tree grows exactly
        one level at a time no matter whether the node is the root or already an
        attribute node.
        """
        children = _stnef_children(self.nodes, node)
        if children and all(self._is_region_child(child) for child in children):
            # The rows under the selected node are its next level, so the new
            # attribute belongs on those rows instead of on a new level.
            adopted = [self._adopt_attribute(child, attribute) for child in children]
            return adopted[-1]
        child = self._append_raw_node(
            node["id"], attribute, "1-D Attribute", attributes=[attribute]
        )
        return child

    def _adopt_attribute(self, row, attribute):
        """Give an existing row (a region row or an attribute level) the attribute."""
        row["name"] = attribute
        row["attributes"] = [attribute]
        row["type"] = "1-D Attribute"
        row["cuts"] = []
        row["y_cuts"] = []
        row["groups"] = {}
        row["region_names"] = {}
        row["region_groups"] = {}
        row["nuisance"] = bool(row.get("nuisance"))
        # A row that already had its own regions keeps only one of them; the old
        # thresholds belong to the previous attribute and no longer apply.
        extra_rows = _stnef_children(self.nodes, row)[1:]
        if extra_rows:
            remove_ids = set()
            for extra in extra_rows:
                remove_ids.update(self._descendant_ids(extra["id"]))
            self.nodes = [item for item in self.nodes if item.get("id") not in remove_ids]
        return row

    @staticmethod
    def _is_region_child(child):
        """A region row is either an empty group bucket or a nested attribute level."""
        if not child:
            return False
        if child.get("type") == "Bucket":
            return not str(child.get("name") or "").strip()
        return bool([name for name in (child.get("attributes") or []) if name])

    @staticmethod
    def _is_attribute_level(child):
        return bool(child) and bool([name for name in (child.get("attributes") or []) if name])

    def _sync_region_children(self, node):
        """Keep one row per region so a cut really splits the tree.

        An attribute node without a cut is the group itself and owns no row; a
        cut line adds one row per region underneath it.
        """
        if node is None:
            return False
        children = _stnef_children(self.nodes, node)
        if children and not all(self._is_region_child(child) for child in children):
            return False
        cuts = self._partition_cuts(node)
        y_cuts = []
        for value in node.get("y_cuts") or []:
            try:
                y_cuts.append(float(value))
            except (TypeError, ValueError):
                continue
        if cuts or y_cuts:
            wanted = (len(cuts) + 1) * (len(y_cuts) + 1)
        elif any(self._is_attribute_level(child) for child in children):
            # Collapsing every cut keeps the nested level the user added.
            wanted = 1
        else:
            wanted = 0
        if len(children) == wanted:
            return False
        while len(children) < wanted:
            if children:
                children.append(self._clone_region_child(node, children[-1]))
            else:
                children.append(self._append_raw_node(node["id"], "", "Bucket"))
        for extra in children[wanted:]:
            remove_ids = self._descendant_ids(extra["id"])
            self.nodes = [item for item in self.nodes if item.get("id") not in remove_ids]
        self._population_cache = None
        self._partition_cache = None
        return True

    def _clone_region_child(self, node, source):
        attributes = [name for name in (source.get("attributes") or []) if name]
        if not attributes:
            return self._append_raw_node(node["id"], "", "Bucket")
        return self._clone_subtree(source, node["id"])

    def _clone_subtree(self, source, parent_id):
        clone = deepcopy(source)
        clone["id"] = self.next_node_id
        clone["parent_id"] = parent_id
        clone["locked"] = False
        self.next_node_id += 1
        self.nodes.append(clone)
        for child in _stnef_children(self.nodes, source):
            self._clone_subtree(child, clone["id"])
        return clone

    def _selected_cut_rows(self):
        return sorted({index.row() for index in self.cuts.selectedIndexes()})

    def _insert_cut(self):
        node = self._selected_node()
        if node is None or node.get("locked") or not node.get("attributes"):
            return
        node.setdefault("cuts", []).append(self.cut_value.value())
        node["cuts"] = sorted(set(node["cuts"]))
        # Region indices change when a new boundary is inserted. Old grouping
        # selections cannot be carried across without assigning them to the
        # wrong numeric ranges.
        node["region_groups"] = {}
        self.property_chart.selected_regions = set()
        self._active_cut_value = float(self.cut_value.value())
        self._active_cut_axis = "x"
        self._sync_region_children(node)
        self._node_changed()

    def _insert_horizontal_cut(self):
        node = self._selected_node()
        attributes = [name for name in (node or {}).get("attributes") or [] if name]
        if (
            node is None or node.get("locked") or len(attributes) < 2
            or self.property_chart.chart_type != "Scatter"
            or self.property_chart.y_labels
        ):
            return
        node.setdefault("y_cuts", []).append(self.cut_value.value())
        node["y_cuts"] = sorted(set(node["y_cuts"]))
        node["region_groups"] = {}
        self.property_chart.selected_regions = set()
        self._active_cut_value = float(self.cut_value.value())
        self._active_cut_axis = "y"
        self._sync_region_children(node)
        self._node_changed()

    def _apply_cut(self):
        node = self._selected_node()
        rows = self._selected_cut_rows()
        if node is None or node.get("locked") or len(rows) != 1:
            return
        node["cuts"][rows[0]] = self.cut_value.value()
        node["cuts"] = sorted(set(node["cuts"]))
        self._sync_region_children(node)
        self._node_changed()

    def _delete_cut(self):
        node = self._selected_node()
        if node is None or node.get("locked"):
            return
        y_cuts = sorted(float(value) for value in self.property_chart.y_cut_lines)
        y_index = self.property_chart.selected_y_cut
        if y_index is not None and 0 <= y_index < len(sorted(y_cuts)):
            y_cuts.pop(y_index)
            self.property_chart.set_y_cut_lines(y_cuts)
            self._active_cut_value = None
            self._active_cut_axis = None
            self.property_chart.selected_y_cut = None
            self._commit_chart_cuts(node)
            return
        cuts = sorted(float(value) for value in self.property_chart.cut_lines)
        index = self.property_chart.selected_cut
        if index is not None and 0 <= index < len(sorted(cuts)):
            cuts.pop(index)
            self.property_chart.set_cut_lines(cuts)
            self._active_cut_value = None
            self._active_cut_axis = None
            self.property_chart.selected_cut = None
            self._commit_chart_cuts(node)
            return
        else:
            rows = self._selected_cut_rows()
            if not rows:
                return
            for row in reversed(rows):
                node["cuts"].pop(row)
        node["groups"] = {}
        node["region_groups"] = {}
        self.property_chart.selected_regions = set()
        self._active_cut_value = None
        self._active_cut_axis = None
        self.property_chart.selected_cut = None
        self._sync_region_children(node)
        self._node_changed()

    def _group_cuts(self):
        node = self._selected_node()
        if node is None:
            return
        regions = sorted(self.property_chart.selected_regions)
        if len(regions) >= 2:
            groups = node.setdefault("region_groups", {})
            group_id = max([int(value) for value in groups.values()] or [0]) + 1
            for region in regions:
                groups[str(region)] = group_id
            self._node_changed()
            return
        rows = self._selected_cut_rows()
        if len(rows) < 2:
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
        regions = sorted(self.property_chart.selected_regions)
        if regions:
            groups = node.setdefault("region_groups", {})
            for region in regions:
                groups.pop(str(region), None)
            self._node_changed()
            return
        groups = node.setdefault("groups", {})
        for row in self._selected_cut_rows():
            groups.pop(str(row), None)
        self._node_changed()

    def _rename_region(self, _checked=False):
        node = self._selected_node()
        regions = sorted(self.property_chart.selected_regions)
        if node is None or not regions:
            return
        index = regions[0]
        current = str((node.get("region_names") or {}).get(str(index), ""))
        dialog = QDialog(self)
        dialog.setWindowTitle("Rename Region")
        form = QVBoxLayout(dialog)
        edit = QLineEdit(current)
        form.addWidget(edit)
        buttons = QHBoxLayout()
        ok = QPushButton("OK")
        cancel = QPushButton("Cancel")
        ok.clicked.connect(dialog.accept)
        cancel.clicked.connect(dialog.reject)
        buttons.addStretch(1)
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        form.addLayout(buttons)
        if _exec(dialog) == QDialog.Accepted:
            node.setdefault("region_names", {})[str(index)] = edit.text().strip()
            self._node_changed()

    def _edit_partitions(self):
        node = self._selected_node()
        if node is None:
            return
        dialog = STNEFPartitionsDialog(node.get("partitions"), self, class_codes=self._class_codes())
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

    def capture_state(self):
        nuisance_nodes = sum(bool(node.get("nuisance")) for node in self.nodes)
        classifiers = deepcopy(self.state.get("classifiers") or [])
        if not classifiers:
            classifiers = [{"name": "ST-NEF Hierarchical", "type": "ST-NEF", "st_nef": True}]
        hidden_defect_ids = self._nuisance_defect_ids()
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
            "hidden_defect_ids": list(hidden_defect_ids),
        }
        return self.result_state

    def _finish(self):
        self.capture_state()
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


class _PaneMaximizeFilter(QObject):
    """Double-click a pane to fill the splitter, and double-click again to restore it."""

    def __init__(self, dialog, splitter, frame):
        super().__init__(dialog)
        self.dialog = dialog
        self.splitter = splitter
        self.frame = frame

    def eventFilter(self, watched, event):  # noqa: N802 - Qt override
        if event.type() == QEvent.MouseButtonDblClick:
            self.dialog._toggle_pane(self.splitter, self.frame)
            return True
        return False


class _STNEFCanvas(QWidget):
    """Hierarchical classifier tree. Auto Fit scales it to the pane; otherwise Zoom applies.

    The wheel zooms around the pointer and dragging the empty ground pans the
    tree, so a deep classifier can be explored without changing any tool state.
    """

    def __init__(self, host):
        super().__init__(host)
        self.host = host
        self._hit_nodes = []
        self._populations = None
        self.view_scale = 1.0
        self.view_offset = [0.0, 0.0]
        self._base_frame = None
        self._pan_last = None
        self.setMinimumHeight(160)
        self.setContextMenuPolicy(Qt.DefaultContextMenu)
        self.setStyleSheet("background: #ffffff; border: 1px solid #b7b7b7;")
        self.setToolTip("Wheel: zoom the tree. Drag the background: pan. Double-click the background: reset the view.")
        self.setMouseTracking(True)

    def reset_view(self):
        self.view_scale = 1.0
        self.view_offset = [0.0, 0.0]
        self.update()

    def zoom_at(self, px, py, factor):
        if self._base_frame is None:
            self._base_frame = (0.0, 0.0, 1.0)
        base_origin_x, base_origin_y, base_scale = self._base_frame
        current = max(0.05, self.view_scale)
        target = max(0.15, min(6.0, current * float(factor)))
        if abs(target - current) < 1e-6:
            return
        center_x, center_y = self.width() / 2.0, self.height() / 2.0
        scale = base_scale * current
        origin_x = center_x * (1 - current) + current * base_origin_x + self.view_offset[0]
        origin_y = center_y * (1 - current) + current * base_origin_y + self.view_offset[1]
        tree_x = (px - origin_x) / max(scale, 1e-6)
        tree_y = (py - origin_y) / max(scale, 1e-6)
        new_scale = base_scale * target
        self.view_scale = target
        self.view_offset = [
            px - tree_x * new_scale - center_x * (1 - target) - target * base_origin_x,
            py - tree_y * new_scale - center_y * (1 - target) - target * base_origin_y,
        ]
        self.update()

    def wheelEvent(self, event):  # noqa: N802 - Qt override
        delta = event.angleDelta().y() if hasattr(event, "angleDelta") else 0
        if not delta:
            return
        point = event.position() if hasattr(event, "position") else event.pos()
        self.zoom_at(point.x(), point.y(), 1.2 ** (delta / 120.0))
        event.accept()

    def _children(self, node):
        return sorted(
            [item for item in self.host.nodes if item.get("parent_id") == node.get("id")],
            key=lambda item: int(item.get("id", 0)),
        )

    def _layout(self, node, depth, cursor):
        children = self._children(node)
        if not children:
            placed = {"node": node, "x": cursor[0] * 150, "y": depth * 88, "children": []}
            cursor[0] += 1
            return placed
        placed_children = [self._layout(child, depth + 1, cursor) for child in children]
        placed = {
            "node": node,
            "x": sum(child["x"] for child in placed_children) / len(placed_children),
            "y": depth * 88,
            "children": placed_children,
        }
        return placed

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), QColor("#ffffff"))
        root = self.host._canvas_tree_root() if hasattr(self.host, "_canvas_tree_root") else None
        if root is None:
            painter.end()
            return
        placed = self._layout(root, 0, [0])
        self._populations = self.host._tree_populations()
        flat = []

        def walk(item):
            flat.append(item)
            for child in item["children"]:
                walk(child)

        walk(placed)
        min_x = min(item["x"] for item in flat) - 90
        max_x = max(item["x"] for item in flat) + 110
        min_y = min(item["y"] for item in flat) - 24
        max_y = max(item["y"] for item in flat) + 28
        span_x = max(1.0, max_x - min_x)
        span_y = max(1.0, max_y - min_y)
        auto_fit = getattr(self.host, "auto_fit", None)
        fitted = auto_fit is None or auto_fit.isChecked()
        if len(flat) == 1:
            base_scale = 1.0 if fitted else max(0.4, self.host.zoom.value() / 100.0)
            base_x = self.width() / 2 - placed["x"] * base_scale
            base_y = self.height() / 2 - placed["y"] * base_scale
        else:
            if fitted:
                base_scale = min((self.width() - 24) / span_x, (self.height() - 24) / span_y)
            else:
                base_scale = max(0.4, self.host.zoom.value() / 100.0)
            base_x = self.width() / 2 - ((min_x + max_x) / 2) * base_scale
            base_y = 12 - min_y * base_scale
        self._base_frame = (base_x, base_y, base_scale)
        # Extra view transform: zoom about the pane center plus a pan offset.
        view = max(0.05, self.view_scale)
        center_x, center_y = self.width() / 2.0, self.height() / 2.0
        origin_x = center_x * (1 - view) + view * base_x + self.view_offset[0]
        origin_y = center_y * (1 - view) + view * base_y + self.view_offset[1]
        scale = base_scale * view
        self._hit_nodes = [
            (item["node"].get("id"), origin_x + item["x"] * scale, origin_y + item["y"] * scale)
            for item in flat
        ]
        painter.translate(origin_x, origin_y)
        painter.scale(scale, scale)
        self._draw_tree(painter, placed)
        painter.end()

    def _node_at(self, x, y):
        best = None
        best_distance = 26
        for node_id, sx, sy in self._hit_nodes:
            distance = ((sx - x) ** 2 + (sy - y) ** 2) ** 0.5
            if distance < best_distance:
                best = node_id
                best_distance = distance
        return best

    def mousePressEvent(self, event):
        point = event.position().toPoint() if hasattr(event, "position") else event.pos()
        button = event.button() if hasattr(event, "button") else Qt.LeftButton
        node_id = self._node_at(point.x(), point.y())
        if button == Qt.RightButton:
            if node_id is not None and hasattr(self.host, "_select_canvas_node"):
                self.host._select_canvas_node(node_id)
            if hasattr(self.host, "_show_node_menu"):
                self.host._show_node_menu(self.mapToGlobal(point))
            return
        if node_id is None:
            # Empty ground: start a pan instead of selecting a node.
            self._pan_last = (point.x(), point.y())
            self.setCursor(Qt.ClosedHandCursor)
            return
        if hasattr(self.host, "_select_canvas_node"):
            self.host._select_canvas_node(node_id)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._pan_last is None:
            super().mouseMoveEvent(event)
            return
        point = event.position().toPoint() if hasattr(event, "position") else event.pos()
        dx = point.x() - self._pan_last[0]
        dy = point.y() - self._pan_last[1]
        self._pan_last = (point.x(), point.y())
        self.view_offset = [self.view_offset[0] + dx, self.view_offset[1] + dy]
        self.update()

    def mouseReleaseEvent(self, event):
        if self._pan_last is not None:
            self._pan_last = None
            self.unsetCursor()
            self.update()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        point = event.position().toPoint() if hasattr(event, "position") else event.pos()
        if self._node_at(point.x(), point.y()) is None:
            self.reset_view()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def _edge_label(self, parent, child, index):
        kind = child.get("type")
        if kind in ("Bucket", "NEF Partition") and child.get("name"):
            return str(child.get("name"))
        if hasattr(self.host, "_tree_branch_label"):
            linked = self.host._tree_branch_label(parent, child, index)
            if linked:
                return linked
        if (
            hasattr(self.host, "_partition_layout")
            and getattr(self.host, "show_labels", None) is not None
            and self.host.show_labels.isChecked()
        ):
            layout = self.host._partition_layout(parent)
            key = layout.get("region_keys", {}).get(index)
            if key is not None:
                ordered = []
                for region in sorted(layout["region_keys"]):
                    region_key = layout["region_keys"][region]
                    if region_key not in ordered:
                        ordered.append(region_key)
                if key in ordered:
                    return f"Group {ordered.index(key) + 1}"
        cuts = parent.get("cuts") or []
        if cuts:
            threshold = float(cuts[0])
            return f"< {threshold:.2f}" if index == 0 else f"≥ {threshold:.2f}"
        return ""

    def _draw_tree(self, painter, placed):
        node = placed["node"]
        children = placed["children"]
        for index, child in enumerate(children):
            painter.setPen(QPen(QColor("#9eb4ea"), 2))
            painter.drawLine(int(placed["x"]), int(placed["y"]), int(child["x"]), int(child["y"]) - 8)
            label = self._edge_label(node, child["node"], index)
            if label:
                mid_x = (placed["x"] + child["x"]) / 2
                mid_y = (placed["y"] + child["y"]) / 2
                painter.setBrush(QColor("#f7f7f7"))
                painter.setPen(QColor("#8d8d8d"))
                width = max(22, len(label) * 7 + 8)
                painter.drawRect(int(mid_x - width / 2), int(mid_y) - 12, width, 16)
                painter.setPen(QColor("#202020"))
                painter.drawText(int(mid_x - width / 2), int(mid_y) - 12, width, 16, Qt.AlignCenter, label)
            self._draw_tree(painter, child)
        self._draw_node(painter, placed)

    def _draw_node(self, painter, placed):
        node = placed["node"]
        x = int(placed["x"])
        y = int(placed["y"])
        selected = self._is_selected(node)
        if selected:
            self._draw_selection(painter, x, y)
        self._draw_count(painter, node, x, y, selected=selected)
        has_nef_children = any(child["node"].get("type") == "NEF Partition" for child in placed["children"])
        is_nn = node.get("type") == "NN"
        nuisance = bool(node.get("nuisance"))
        if has_nef_children:
            self._draw_bucket(painter, x, y, blue=True)
        elif is_nn or (y == 0 and node.get("type") not in ("Bucket", "NEF Partition")):
            painter.setPen(QPen(QColor("#2f3f86"), 3 if selected else 1))
            painter.setBrush(QColor("#7f93ee"))
            painter.drawEllipse(x - 11, y - 11, 22, 22)
        else:
            self._draw_bucket(painter, x, y, blue=nuisance or node.get("type") == "NEF Partition")
        if node.get("locked"):
            self._draw_lock(painter, x, y)
        if nuisance:
            painter.setPen(QColor("#d32f2f"))
            painter.drawText(x - 36, y + 27, 72, 16, Qt.AlignCenter, "Nuisance")
        if has_nef_children:
            self._draw_pill(painter, x, y, "NEF Node", selected=selected)
            return
        attributes = [name for name in (node.get("attributes") or []) if name]
        if attributes and not is_nn and node.get("type") not in ("Bucket", "NEF Partition"):
            self._draw_attribute_pill(painter, x, y, attributes[:2], selected=selected)
            return
        label = node.get("name") or ""
        if not label or node.get("type") in ("Bucket", "NEF Partition"):
            return
        if node.get("parent_id") is None and not node.get("attributes") and not is_nn:
            return
        self._draw_pill(painter, x, y, label, selected=selected)

    def _draw_selection(self, painter, x, y):
        """Highlight the node the user has selected."""
        painter.setPen(QPen(QColor("#2f6fd6"), 2))
        painter.setBrush(QColor("#dbe8ff"))
        painter.drawRoundedRect(x - 17, y - 17, 34, 34, 9, 9)

    def _draw_count(self, painter, node, x, y, selected=False):
        if self._populations is None:
            return
        count = len(self._populations.get(node.get("id"), []))
        font = painter.font()
        font.setBold(bool(selected))
        painter.save()
        painter.setFont(font)
        painter.setPen(QColor("#1d3fa0") if selected else QColor("#4a4a4a"))
        painter.drawText(x - 44, y + 13, 88, 14, Qt.AlignCenter, str(count))
        painter.restore()

    def _is_selected(self, node):
        selected = self.host._selected_node() if hasattr(self.host, "_selected_node") else None
        return selected is not None and selected.get("id") == node.get("id")

    def _draw_attribute_pill(self, painter, x, y, labels, selected=False):
        lines = labels[:2]
        line_height = 16
        height = 8 + line_height * len(lines)
        width = max(64, max(len(line) for line in lines) * 7 + 20)
        top = y - height // 2
        painter.setPen(QPen(QColor("#0d2a85"), 2) if selected else Qt.NoPen)
        painter.setBrush(QColor("#3157c2"))
        painter.drawRoundedRect(x + 16, top, width, height, 8, 8)
        painter.setPen(QColor("#ffffff"))
        for index, line in enumerate(lines):
            painter.drawText(x + 16, top + 4 + index * line_height, width, line_height, Qt.AlignCenter, line)

    def _draw_pill(self, painter, x, y, label, selected=False):
        text = label if len(label) <= 16 else label[:14] + "..."
        width = max(54, len(text) * 7 + 16)
        painter.setPen(QPen(QColor("#0d2a85"), 2) if selected else Qt.NoPen)
        painter.setBrush(QColor("#3157c2"))
        painter.drawRoundedRect(x + 16, y - 11, width, 22, 9, 9)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(x + 16, y - 11, width, 22, Qt.AlignCenter, text)

    def _draw_lock(self, painter, x, y):
        painter.setPen(QPen(QColor("#24346e"), 1))
        painter.setBrush(QColor("#e8eeff"))
        painter.drawArc(x - 18, y - 14, 10, 10, 0, 180 * 16)
        painter.drawRoundedRect(x - 20, y - 8, 12, 9, 1, 1)

    def _draw_bucket(self, painter, x, y, blue=False):
        painter.setPen(QPen(QColor("#2f3f86") if blue else QColor("#5c6578"), 1))
        painter.setBrush(QColor("#6d86e6") if blue else QColor("#e4e7ef"))
        path = QPainterPath()
        path.moveTo(x - 9, y - 4)
        path.lineTo(x + 9, y - 4)
        path.lineTo(x + 7, y + 10)
        path.lineTo(x - 7, y + 10)
        path.closeSubpath()
        painter.drawPath(path)
        painter.drawEllipse(x - 9, y - 8, 18, 6)


class _AttributeHistogram(QFrame):
    def __init__(self, title, counts, on_double=None, labels=None, log_scale=False, selected=False):
        super().__init__()
        self.title = title
        self.counts = list(counts)
        self.labels = list(labels or [])
        self.log_scale = bool(log_scale)
        self.on_double = on_double
        self.setFixedHeight(118)
        self._set_selected(selected)

    def _set_selected(self, selected):
        border = "#2f6fd6" if selected else "#9a9a9a"
        self.setStyleSheet(f"QFrame {{ background: #ffffff; border: 1px solid {border}; }}")

    def mouseDoubleClickEvent(self, event):
        if not self.on_double:
            return
        modifiers = event.modifiers() if hasattr(event, "modifiers") else Qt.NoModifier
        shift = bool(modifiers & Qt.ShiftModifier)
        callback = self.on_double
        QTimer.singleShot(0, lambda: callback(shift))

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#ffffff"))
        painter.setPen(QColor("#202020"))
        painter.drawText(0, 2, self.width(), 16, Qt.AlignCenter, self.title)
        if not self.counts:
            painter.end()
            return
        heights = [math.log1p(max(0, value)) if self.log_scale else value for value in self.counts]
        maximum = max(heights) or 1
        left, top, bottom = 28, 22, self.height() - 22
        width = max(1, (self.width() - left - 8) // max(1, len(self.counts)))
        painter.setPen(QColor("#666666"))
        painter.drawText(2, top + 8, "0" if not self.log_scale else "1")
        peak = max(self.counts) or 0
        painter.drawText(0, top - 2, str(peak if not self.log_scale else max(1, peak)))
        for index, value in enumerate(heights):
            bar = int((bottom - top) * value / maximum)
            painter.fillRect(left + index * width, bottom - bar, max(1, width - 1), bar, QColor("#111111"))
        if self.labels:
            painter.setPen(QColor("#333333"))
            if len(self.labels) <= 6 and len(self.labels) == len(self.counts):
                for index, label in enumerate(self.labels):
                    painter.drawText(left + index * width, bottom + 2, max(12, width), 16, Qt.AlignCenter, str(label)[:8])
            else:
                painter.drawText(left, bottom + 2, str(self.labels[0]))
                painter.drawText(self.width() - 48, bottom + 2, str(self.labels[-1]))
        painter.end()


class SensitivityTestSelectionDialog(QDialog):
    """Choose the test whose Sensitivity Tuner data will be edited."""

    COLUMNS = (
        "Test", "Orientation", "Defect #", "Pixel Size", "Beam Incidence",
        "Filter", "Focus Offset", "Incident", "Collection",
    )

    def __init__(self, result, recipe=None, parent=None):
        super().__init__(parent)
        self.review_result = result or {}
        self.recipe = recipe or {}
        self.selected_test = None
        self.clear_existing_filters = False
        self.setWindowTitle("Test Selection")
        self.resize(760, 420)
        self.setStyleSheet(
            "QDialog { background: #e8e4d4; font-family: Arial, Helvetica, sans-serif; font-size: 11px; }"
            "QLineEdit { background: #ffffff; border: 1px solid #9a9a9a; }"
            "QTableWidget { background: #ffffff; }"
            "QPushButton { min-width: 72px; min-height: 24px; }"
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        form = QGridLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)
        defects = list(self.review_result.get("defects") or [])
        fields = (
            ("Slot No", str(self.review_result.get("slot_no") or self.review_result.get("slot") or "")),
            ("Total Defects", str(self.review_result.get("defect_count") or len(defects))),
            ("Wafer ID", str(self.review_result.get("wafer_id") or "")),
        )
        for row, (label, value) in enumerate(fields):
            form.addWidget(QLabel(label), row, 0)
            edit = QLineEdit(value)
            edit.setReadOnly(True)
            edit.setFixedWidth(140)
            form.addWidget(edit, row, 1)
        root.addLayout(form)

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(list(self.COLUMNS))
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.doubleClicked.connect(self._accept_selection)
        root.addWidget(self.table, 1)
        self._populate()

        self.clear_filters = QCheckBox("Clear Existing Filters")
        root.addWidget(self.clear_filters)
        note = QLabel(
            "Tests that lack Sensitivity data or have defect counts greater than 175000 are excluded."
        )
        note.setWordWrap(True)
        root.addWidget(note)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        ok_button = QPushButton("Ok")
        ok_button.clicked.connect(self._accept_selection)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(ok_button)
        buttons.addWidget(cancel_button)
        root.addLayout(buttons)

    def _populate(self):
        defects = list(self.review_result.get("defects") or [])
        counts = Counter(str(item.get("test") or "") for item in defects)
        if "sensitivity_data_tests" in self.review_result:
            allowed = [str(name) for name in (self.review_result.get("sensitivity_data_tests") or []) if name]
        elif self.review_result.get("sensitivity_data") is False:
            return
        else:
            allowed = [name for name in counts if name]
        tests = list((self.recipe or {}).get("tests") or [])
        if not tests:
            tests = [{"name": name} for name in allowed]
        for test in tests:
            name = str(test.get("name") or "")
            if not name or not self._name_allowed(name, allowed):
                continue
            defect_count = self._defect_count(name, counts)
            if defect_count > 175000:
                continue
            optics = test.get("inspection_optics") or {}
            channels = list(test.get("channels") or [])
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = (
                self._test_number(name),
                self._orientation_label(test.get("orientation")),
                str(defect_count),
                str(optics.get("pixel_size") or "-"),
                str(optics.get("incidence_angle") or "-"),
                "Yes" if any(channel.get("use_fourier_filter") for channel in channels) else "No",
                self._format_offset(optics.get("focus_offset", test.get("focus_offset", 0))),
                str(optics.get("incident_polarization") or "-"),
                self._collection_label(channels),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.UserRole, name)
                self.table.setItem(row, column, item)
        if self.table.rowCount():
            self.table.selectRow(0)
            self.selected_test = self.table.item(0, 0).data(Qt.UserRole)

    @staticmethod
    def _name_aliases(name: str) -> set:
        number = SensitivityTestSelectionDialog._test_number(name)
        aliases = {str(name), number}
        if number:
            aliases.add(f"Test {number}")
        return {alias for alias in aliases if alias}

    @classmethod
    def _name_allowed(cls, name: str, allowed) -> bool:
        return bool(cls._name_aliases(name) & set(allowed or []))

    @classmethod
    def _defect_count(cls, name: str, counts) -> int:
        return sum(counts.get(alias, 0) for alias in cls._name_aliases(name))

    @staticmethod
    def _test_number(name: str) -> str:
        digits = "".join(character for character in name if character.isdigit())
        return digits or name

    @staticmethod
    def _orientation_label(value) -> str:
        text = str(value or "")
        if "270" in text:
            return "Left"
        if "180" in text or text.lower() == "down":
            return "Down"
        if "90" in text:
            return "Right"
        if text.lower().startswith("up") or text in {"0", "0°"}:
            return "Up"
        return text or "Down"

    @staticmethod
    def _format_offset(value) -> str:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return str(value or "0")
        text = f"{number:.3f}".rstrip("0").rstrip(".")
        return text or "0"

    @staticmethod
    def _collection_label(channels) -> str:
        names = [
            str(channel.get("polarization") or "None")
            for channel in channels
            if channel.get("enabled", True)
        ]
        unique = []
        for name in names:
            if name not in unique:
                unique.append(name)
        if not unique or unique == ["None"]:
            return "None"
        return ", ".join(unique)

    def _accept_selection(self):
        row = self.table.currentRow()
        if row < 0 and self.table.rowCount():
            row = 0
        if row < 0:
            QMessageBox.warning(
                self,
                "Test Selection",
                "No test with Sensitivity Tuner data is available. Collect Sensitivity Data on Run One Wafer, "
                "set CollectVOSensitiveData to 1, or run an OSTS scan.",
            )
            return
        self.selected_test = self.table.item(row, 0).data(Qt.UserRole)
        self.clear_existing_filters = self.clear_filters.isChecked()
        self.accept()


class TunerToolButton(QPushButton):
    """Icon above a caption, with a gap so the two never share the same pixels."""

    ICON_TOP = 5
    ICON_SIZE = 22
    TEXT_GAP = 6
    TEXT_HEIGHT = 16

    def __init__(self, label, kind, parent=None, caret=False):
        super().__init__(label, parent)
        self.kind = kind
        self.caret = caret
        self.caret_handler = None
        font = self.font()
        font.setFamily("Arial")
        font.setPixelSize(11)
        self.setFont(font)
        text_width = max(self.fontMetrics().horizontalAdvance(label) + 16, 46)
        if caret:
            text_width += 8
        self.setFixedSize(text_width, self.ICON_TOP + self.ICON_SIZE + self.TEXT_GAP + self.TEXT_HEIGHT + 5)
        self.setFlat(True)
        self.setFocusPolicy(Qt.NoFocus)
        self.setStyleSheet("QPushButton { background: transparent; border: none; }")

    def _caret_rect(self):
        zoom = self.zoom()
        bottom = int((self.TEXT_HEIGHT + self.TEXT_GAP) * zoom)
        return self.rect().adjusted(self.width() - int(14 * zoom), 0, 0, -bottom)

    def mouseReleaseEvent(self, event):
        point = event.position().toPoint() if hasattr(event, "position") else event.pos()
        if self.caret and self.caret_handler and self._caret_rect().contains(point):
            # A direct call has no sender(); hand the button over so the menu
            # can anchor under the caret.
            self.caret_handler(self)
            return
        super().mouseReleaseEvent(event)

    def zoom(self) -> float:
        return max(1.0, float(getattr(self, "_tuner_zoom", 1.0)))

    def set_ui_scale(self, scale):
        self._tuner_zoom = max(1.0, float(scale))
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        if self.isChecked():
            painter.fillRect(self.rect(), QColor("#dbe6f9"))
            painter.fillRect(0, self.height() - 2, self.width(), 2, QColor("#2f5fb3"))
        elif self.underMouse():
            painter.fillRect(self.rect(), QColor("#f2efe7"))
        zoom = self.zoom()
        icon_size = max(8, int(round(self.ICON_SIZE * zoom)))
        icon_left = (self.width() - icon_size) // 2
        if self.caret:
            icon_left -= int(round(4 * zoom))
        icon_top = int(round(self.ICON_TOP * zoom))
        # The icon glyphs keep their designed 22px geometry; the painter
        # transform scales them, so every inner coordinate stays integral.
        painter.save()
        painter.translate(icon_left, icon_top)
        painter.scale(zoom, zoom)
        self._draw_icon(painter, 0, 0, self.ICON_SIZE)
        painter.restore()
        if self.caret:
            self._draw_caret(
                painter,
                icon_left + icon_size + 2,
                icon_top + int(round(8 * zoom)),
            )
        painter.setPen(QColor("#1a1a1a"))
        painter.setFont(self.font())
        text_top = icon_top + icon_size + int(round(self.TEXT_GAP * zoom))
        text_height = int(round(self.TEXT_HEIGHT * zoom))
        painter.drawText(0, text_top, self.width(), text_height, Qt.AlignCenter, self.text())
        painter.end()

    def _draw_caret(self, painter, x, y):
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#243140"))
        path = QPainterPath()
        path.moveTo(x, y)
        path.lineTo(x + 7, y)
        path.lineTo(x + 3.5, y + 5)
        path.closeSubpath()
        painter.drawPath(path)

    def _draw_icon(self, painter, x, y, size):
        kind = self.kind
        blue = QColor("#2d7cc4")
        green = QColor("#2f9d3a")
        if kind in {"prev", "next", "prevu", "nextu"}:
            painter.setPen(Qt.NoPen)
            painter.setBrush(blue)
            pairs = (0, 11) if kind in {"prevu", "nextu"} else (5,)
            for offset in pairs:
                path = QPainterPath()
                left = x + offset
                if kind.startswith("prev"):
                    path.moveTo(left + 9, y + 3)
                    path.lineTo(left + 2, y + 11)
                    path.lineTo(left + 9, y + 19)
                    path.lineTo(left + 12, y + 16)
                    path.lineTo(left + 7, y + 11)
                    path.lineTo(left + 12, y + 6)
                else:
                    path.moveTo(left + 3, y + 3)
                    path.lineTo(left + 10, y + 11)
                    path.lineTo(left + 3, y + 19)
                    path.lineTo(left, y + 16)
                    path.lineTo(left + 5, y + 11)
                    path.lineTo(left, y + 6)
                path.closeSubpath()
                painter.drawPath(path)
            return
        if kind == "cancel":
            painter.setPen(QPen(QColor("#3a86c5"), 2))
            painter.setBrush(QColor("#e7f3fc"))
            painter.drawEllipse(x + 1, y + 1, size - 2, size - 2)
            painter.setPen(QPen(QColor("#d02323"), 2.2))
            painter.setBrush(Qt.NoBrush)
            path = QPainterPath()
            path.arcMoveTo(x + 5, y + 5, size - 10, size - 10, 40)
            path.arcTo(x + 5, y + 5, size - 10, size - 10, 40, 250)
            painter.drawPath(path)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#d02323"))
            tip = QPainterPath()
            tip.moveTo(x + 5, y + 8)
            tip.lineTo(x + 5, y + 15)
            tip.lineTo(x + 12, y + 12)
            tip.closeSubpath()
            painter.drawPath(tip)
            return
        if kind == "options":
            painter.setPen(QPen(QColor("#5d6c7a"), 1.6))
            painter.setBrush(QColor("#eef3f7"))
            painter.drawEllipse(x + 3, y + 3, size - 6, size - 6)
            painter.setBrush(QColor("#d5e4ef"))
            painter.drawEllipse(x + 8, y + 8, size - 16, size - 16)
            painter.setPen(QPen(QColor("#5d6c7a"), 2))
            center = x + size / 2
            middle = y + size / 2
            for angle in range(0, 360, 45):
                radians = math.radians(angle)
                painter.drawLine(
                    int(center + math.cos(radians) * 6),
                    int(middle + math.sin(radians) * 6),
                    int(center + math.cos(radians) * 10),
                    int(middle + math.sin(radians) * 10),
                )
            return
        if kind == "st":
            painter.setPen(QColor("#b08920"))
            painter.setBrush(QColor("#f3c14b"))
            painter.drawRoundedRect(x + 1, y + 2, size - 2, size - 4, 2, 2)
            painter.setPen(QPen(green, 1.8))
            painter.drawLine(x + 4, y + 15, x + 8, y + 10)
            painter.drawLine(x + 8, y + 10, x + 13, y + 13)
            painter.drawLine(x + 13, y + 13, x + 18, y + 6)
            painter.setPen(QPen(QColor("#d02323"), 1.8))
            painter.drawLine(x + 15, y + 4, x + 15, y + size - 4)
            return
        if kind == "stnef":
            painter.setPen(QPen(QColor("#2a6eab"), 1.6))
            painter.setBrush(QColor("#d7ebfa"))
            painter.drawRoundedRect(x + 7, y + 1, 8, 7, 1, 1)
            painter.drawRoundedRect(x + 1, y + 14, 8, 7, 1, 1)
            painter.drawRoundedRect(x + 13, y + 14, 8, 7, 1, 1)
            painter.drawLine(x + 11, y + 8, x + 5, y + 14)
            painter.drawLine(x + 11, y + 8, x + 17, y + 14)
            return
        painter.setPen(QColor("#7a7a7a"))
        painter.setBrush(QColor("#f7f7f7"))
        painter.drawRoundedRect(x + 3, y + 2, 14, 17, 1, 1)
        painter.drawLine(x + 6, y + 6, x + 14, y + 6)
        painter.drawLine(x + 6, y + 9, x + 14, y + 9)
        painter.setPen(QPen(green, 2))
        painter.drawLine(x + 6, y + 14, x + 9, y + 17)
        painter.drawLine(x + 9, y + 17, x + 16, y + 8)


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
    # Only these Finish choices write the tuner page back to the session.
    SAVING_ACTIONS = (
        "Save & Exit",
        "Save Session Recipe",
        "Save Recipe As...",
        "Export Recipe As...",
    )

    def __init__(self, result, recipe=None, state=None, parent=None, initial_test=None):
        super().__init__(parent)
        self.review_result = result
        self.recipe = recipe
        self.state = deepcopy(state or {})
        if initial_test and not self.state.get("test"):
            self.state["test"] = initial_test
        self.result_state = None
        self.state_persisted = False
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
        self.setWindowFlags(
            Qt.Window
            | Qt.WindowTitleHint
            | Qt.WindowSystemMenuHint
            | Qt.WindowMinimizeButtonHint
            | Qt.WindowMaximizeButtonHint
            | Qt.WindowCloseButtonHint
        )
        self.resize(980, 720)
        self._default_size = (980, 720)
        self._fitted_once = False
        self._in_size_adjust = False
        self.setStyleSheet(
            "QDialog { background: #d9d4c8; }"
            "QTableWidget { background: #ffffff; }"
        )
        root = QVBoxLayout(self)
        # The summary strip spans the whole window width, so the window itself
        # carries no margin; the page contents keep their own inset.
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        bar = QFrame()
        bar.setObjectName("tunerBar")
        bar.setStyleSheet(
            "QFrame#tunerBar { background: #c9c5bc; border: none;"
            " border-bottom: 1px solid #79766e; }"
            "QFrame#tunerBar QComboBox { background: white; min-height: 22px; }"
        )
        toolbar = QHBoxLayout(bar)
        toolbar.setContentsMargins(8, 5, 8, 5)
        toolbar.setSpacing(4)
        tool_buttons = (
            ("Finish", "finish", True, "Save and exit Sensitivity Tuner.", self._finish),
            ("Cancel", "cancel", False, "Exit Sensitivity Tuner without saving any changes.", self.reject),
            ("PrevU", "prevu", False, "Go to the previous uncommitted parameter.", lambda: self._navigate(-1, True)),
            ("Prev", "prev", False, "Go to the previous parameter.", lambda: self._navigate(-1)),
            ("Next", "next", False, "Go to the next parameter.", lambda: self._navigate(1)),
            ("NextU", "nextu", False, "Go to the next uncommitted parameter.", lambda: self._navigate(1, True)),
            ("Commit", "commit", False, "Commit the current parameter. Committed channel parameters turn green.", self._commit),
        )
        for label, kind, caret, tooltip, callback in tool_buttons:
            button = TunerToolButton(label, kind, caret=caret)
            button.setToolTip(tooltip)
            button.clicked.connect(callback)
            toolbar.addWidget(button)
            if label == "Finish":
                # The caret drops the Finish menu (Table 10-43); the body of the
                # button runs the current Finish choice.
                self.finish_button = button
                button.caret_handler = self._show_finish_menu
                button.setToolTip(
                    "Finish and exit. Use the caret for Restore, Save, Export, and Exit options."
                )
            if label in {"Cancel", "NextU", "Commit"}:
                toolbar.addWidget(self._toolbar_rule())
        self.manual_code = QComboBox()
        self.manual_code.addItems(["Manual Code", "USG Code", "CAG Code"])
        self.manual_code.setToolTip(
            "Group similar classification codes in the Tuner Chart, Scatter Chart, and summary."
        )
        self.manual_code.setFixedSize(132, 26)
        toolbar.addWidget(self.manual_code)
        toolbar.addWidget(self._toolbar_rule())
        self.st_button = TunerToolButton("ST", "st")
        self.st_button.setToolTip("Change to the Sensitivity Tuner view.")
        self.st_button.setCheckable(True)
        self.st_button.setChecked(True)
        self.st_button.clicked.connect(self._show_st_page)
        toolbar.addWidget(self.st_button)
        self.stnef_button = TunerToolButton("STNEF", "stnef", caret=True)
        self.stnef_button.setCheckable(True)
        self.stnef_button.setToolTip("Change to the ST-NEF Tuner view.")
        self.stnef_button.clicked.connect(self._switch_nef)
        self.stnef_button.caret_handler = self._show_stnef_menu
        toolbar.addWidget(self.stnef_button)
        toolbar.addWidget(self._toolbar_rule())
        options_button = TunerToolButton("Options", "options", caret=True)
        options_button.setToolTip(
            "Click for the parameter panel. Use the caret for the Options menu "
            "(display, review filter, sort, and configuration)."
        )
        # Figure 10-218: the caret drops the Options menu. The button body still
        # opens the parameter panel so the tuner controls stay reachable.
        options_button.clicked.connect(self._toggle_options)
        options_button.caret_handler = self._show_options_menu
        self.options_button = options_button
        toolbar.addWidget(options_button)
        toolbar.addStretch(1)
        self.window_buttons = WindowCaptionButtons(self, bar)
        toolbar.addWidget(self.window_buttons, 0, Qt.AlignVCenter)
        root.addWidget(bar)
        self.section_label = QLabel("Sensitivity Tuner")
        self.section_label.setStyleSheet(
            "font-weight: 700; font-size: 12px; color: #16181c;"
            " padding: 5px 10px 2px 10px;"
        )
        root.addWidget(self.section_label)

        self._options_panel = QWidget()
        self._options_panel.setVisible(False)
        options_root = QVBoxLayout(self._options_panel)

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
        options_root.addLayout(auto_tune)

        self.test = QComboBox()
        test_names = list(result.get("sensitivity_data_tests") or result.get("selected_tests") or ["Test 1"])
        chosen = self.state.get("test")
        if chosen and chosen not in test_names:
            test_names.insert(0, chosen)
        self.test.addItems(test_names)
        if chosen:
            self.test.setCurrentText(chosen)
        self.region = QComboBox()
        self.region.setStyleSheet("QComboBox { background: #ffffff; font-weight: 700; min-width: 64px; }")
        self.region.setToolTip("Region color tracks parameter status only. It does not change how the recipe is saved.")
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
        selector_row = QHBoxLayout()
        selector_row.addWidget(QLabel("Test:"))
        selector_row.addWidget(self.test)
        selector_row.addSpacing(28)
        selector_row.addWidget(QLabel("Region:"))
        selector_row.addWidget(self.region)
        selector_row.addStretch(1)
        root.addLayout(selector_row)

        selectors = QGridLayout()
        selectors_data = [
            ("Channel", self.channel), ("Parameter", self.parameter),
        ]
        for index, (label, control) in enumerate(selectors_data):
            control.setMaximumWidth(250)
            selectors.addWidget(QLabel(label), index // 3, (index % 3) * 2)
            selectors.addWidget(control, index // 3, (index % 3) * 2 + 1)
        options_root.addLayout(selectors)
        utility_row = QHBoxLayout()
        for label, callback in (
            ("Regions", self._select_regions),
            ("Limits", self._max_limits),
            ("Advanced", self._advanced_parameters),
        ):
            button = QPushButton(label)
            button.clicked.connect(callback)
            utility_row.addWidget(button)
        utility_row.addStretch(1)
        options_root.addLayout(utility_row)

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
        options_root.addLayout(tuning)

        self.threshold_table = QTableWidget(7, 7)
        self.threshold_table.setHorizontalHeaderLabels(
            ["", "Threshold", "Noise", "Absmin", "Gradient", "Color", "Threshold"]
        )
        self.threshold_table.verticalHeader().setVisible(False)
        self.threshold_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.threshold_table.setMaximumHeight(248)
        self.threshold_table.setMinimumHeight(96)
        self._build_threshold_table()
        self.threshold_table.itemChanged.connect(self._threshold_cell_edited)
        color_key = QLabel("Yellow: modified, not committed.    Green: modified and committed.")
        color_key.setStyleSheet("color: #333333;")
        # Each module folds down to its caption bar, so the window can show just
        # the plot a given step needs.
        self.threshold_section = CollapsibleGroup("Threshold Parameters", spacing=4, margins=(0, 4, 0, 0))
        self.threshold_section.body_layout.addWidget(self.threshold_table)
        self.threshold_section.body_layout.addWidget(color_key)
        root.addWidget(self.threshold_section)

        self.tuner_chart = DefectChart()
        self.scatter_chart = DefectChart()
        self.tuner_section = CollapsibleGroup("Tuner Chart", spacing=4, margins=(0, 4, 0, 0))
        self.tuner_section.body_layout.addWidget(self.tuner_chart, 1)
        root.addWidget(self.tuner_section, 1)
        scatter_axis = QHBoxLayout()
        self.scatter_attribute = QComboBox()
        self.scatter_attribute.addItems(["Noise", "Signal", "Area"])
        self.scatter_attribute.setFixedWidth(120)
        self.scatter_attribute.currentTextChanged.connect(self._update)
        scatter_axis.addWidget(self.scatter_attribute)
        scatter_axis.addStretch(1)
        self.scatter_section = CollapsibleGroup("Scatter Chart", spacing=4, margins=(0, 4, 0, 0))
        self.scatter_section.body_layout.addLayout(scatter_axis)
        self.scatter_section.body_layout.addWidget(self.scatter_chart, 1)
        root.addWidget(self.scatter_section, 1)

        # Summary: one full width strip along the bottom edge of the window,
        # shared with the embedded ST-NEF page (see _install_tuner_pages) so
        # both views reserve exactly the same space and read the same way.
        self.summary_panel = TunerSummaryPanel()
        self.summary_panel.row_selected = self._summary_row_selected
        root.addWidget(self._options_panel)

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
        options_root.addLayout(plot_options)

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
        options_root.addLayout(options)

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
        options_root.addLayout(identity)

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
        options_root.addLayout(finish_row)

        self.manual_code.currentTextChanged.connect(self._update)
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
        self._install_tuner_pages()
        self._update()
        self._fit_inside_parent()
        self.fullscreen_adapter = FullscreenWindowAdapter(self, base=(1180, 760), scale_with_size=True)
        self.window_buttons.sync()

    def reject(self):
        """Closing the tuner clears anything that was not explicitly saved."""
        self.result_state = None
        self.state_persisted = False
        super().reject()

    def showEvent(self, event):
        # The host window may have been resized or made full screen since the
        # tuner was constructed, so re-fit on every show instead of only once.
        self._fit_inside_parent()
        if hasattr(self, "window_buttons"):
            self.window_buttons.sync()
        super().showEvent(event)

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange and not self.isMinimized():
            if self.isMaximized() or self.isFullScreen():
                self.setMaximumSize(16777215, 16777215)
            else:
                previous = event.oldState() if hasattr(event, "oldState") else Qt.WindowNoState
                if previous & (Qt.WindowMaximized | Qt.WindowFullScreen):
                    self._apply_restored_size()
        if hasattr(self, "window_buttons"):
            self.window_buttons.sync()
        super().changeEvent(event)

    def _fit_inside_parent(self):
        """Open at the main window size. Maximize can still fill the screen."""
        if self.isMaximized() or self.isFullScreen():
            return
        self.setMaximumSize(16777215, 16777215)
        host = self.parentWidget().window() if self.parentWidget() is not None else None
        if host is None or host.width() < 320 or host.height() < 240:
            return
        width, height = host.width(), host.height()
        self._default_size = (width, height)
        self._fitted_once = True
        self.setMinimumSize(min(640, width), min(480, height))
        if self.width() != width or self.height() != height:
            self._in_size_adjust = True
            self.resize(width, height)
            self._in_size_adjust = False

    def _apply_restored_size(self):
        width, height = self._default_size
        self._in_size_adjust = True
        self.resize(width, height)
        self._in_size_adjust = False

    def _install_tuner_pages(self):
        layout = self.layout()
        self.st_page = QWidget()
        st_layout = QVBoxLayout(self.st_page)
        st_layout.setContentsMargins(14, 8, 14, 8)
        st_layout.setSpacing(4)
        while layout.count() > 2:
            item = layout.takeAt(2)
            widget = item.widget()
            if widget is not None:
                # Charts must keep the stretch they were added with, otherwise the
                # extra full screen height is handed to the labels around them and
                # the plots stay pinned at their designed 120 px.
                stretch = 0
                if isinstance(widget, DefectChart):
                    stretch = 1
                    policy = widget.sizePolicy()
                    policy.setVerticalPolicy(QSizePolicy.Expanding)
                    widget.setSizePolicy(policy)
                elif isinstance(widget, QTableWidget):
                    policy = widget.sizePolicy()
                    policy.setVerticalPolicy(QSizePolicy.Expanding)
                    widget.setSizePolicy(policy)
                elif isinstance(widget, CollapsibleGroup):
                    # The chart now lives inside a folding module, so the module
                    # takes the chart's stretch and passes the growth on to it.
                    charts = widget.body.findChildren(DefectChart)
                    if charts:
                        stretch = 1
                        for chart in charts:
                            policy = chart.sizePolicy()
                            policy.setVerticalPolicy(QSizePolicy.Expanding)
                            chart.setSizePolicy(policy)
                        policy = widget.sizePolicy()
                        policy.setVerticalPolicy(QSizePolicy.Expanding)
                        widget.setSizePolicy(policy)
                    for table in widget.body.findChildren(QTableWidget):
                        policy = table.sizePolicy()
                        policy.setVerticalPolicy(QSizePolicy.Expanding)
                        table.setSizePolicy(policy)
                st_layout.addWidget(widget, stretch)
            elif item.layout() is not None:
                st_layout.addLayout(item.layout())
        self.stnef_page = STNEFTunerDialog(
            self.review_result,
            None,
            self,
            embedded=True,
            summary_panel=self.summary_panel,
        )
        self.stnef_page.hide()
        layout.addWidget(self.st_page, 1)
        layout.addWidget(self.stnef_page, 1)
        # Both pages sit above the strip, so it spans the whole window width.
        layout.addWidget(self.summary_panel, 0)

    def _show_st_page(self, *_args):
        self._capture_stnef()
        self.st_button.setChecked(True)
        self.stnef_button.setChecked(False)
        self.section_label.setText("▼  Sensitivity Tuner")
        self.stnef_page.hide()
        self.st_page.show()
        self._update()

    def _capture_stnef(self):
        page = getattr(self, "stnef_page", None)
        if page is None or page.isHidden():
            return
        state = page.capture_state()
        test = self.test.currentText()
        self.nef_states[test] = deepcopy(state)
        self.nef_enabled_tests.add(test)
        if hasattr(self, "enable_nef"):
            self.enable_nef.setChecked(True)

    def _refresh_regions(self, *_args):
        current = self.region.currentText()
        regions = sorted({
            str(item.get("region_id"))
            for item in self.review_result.get("defects", [])
            if item.get("test") == self.test.currentText() and item.get("region_id") not in (None, "")
        }) or ["All"]
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
        if self.selected_regions is not None:
            return self.selected_regions
        return [] if self.region.currentText() == "All" else [self.region.currentText()]

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
        original_threshold = float(self.session_baseline.get("value", self.value.value()))
        original = evaluate_sensitivity_tuning(
            tuning_result,
            test=self.test.currentText(),
            regions=self._regions(),
            polarity=self.polarity.currentText(),
            dark_filter=self.dark_filter.currentText(),
            threshold=original_threshold,
        )
        thresholds = {
            "Current": data["detected"],
            "Original": original["detected"],
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
        considered_ids = set(data["considered_ids"])
        detected_ids = set(data["detected_ids"])
        considered = [
            item for item in tuning_result.get("defects", [])
            if item.get("id") in considered_ids
        ]
        signals = [
            float(item["signal"])
            for item in considered
            if isinstance(item.get("signal"), (int, float)) and not isinstance(item.get("signal"), bool)
        ]
        low = min(signals + [float(self.value.value())])
        high = max(signals + [float(self.value.value())])
        span = high - low or 1.0
        curve = []
        for step in range(25):
            threshold = low + span * step / 24.0
            curve.append((threshold, sum(value >= threshold for value in signals)))
        self.tuner_chart.set_curve(curve, cut=self.value.value(), title="")
        attribute = self.scatter_attribute.currentText() if hasattr(self, "scatter_attribute") else "Noise"
        code_key = {"Manual Code": "manual_class", "USG Code": "usg_code", "CAG Code": "cag_code"}.get(
            self.manual_code.currentText()
        )
        points = []
        for item in considered:
            if code_key and str(item.get(code_key) or "") not in {"", "0", "None"}:
                continue
            signal = item.get("signal")
            scatter = self._scatter_value(item, attribute)
            if isinstance(signal, (int, float)) and scatter is not None:
                points.append((float(signal), scatter))
        if not points:
            points = [
                (float(item["signal"]), self._scatter_value(item, attribute))
                for item in considered
                if isinstance(item.get("signal"), (int, float))
                and self._scatter_value(item, attribute) is not None
            ]
        self.scatter_chart.set_points(points, "", marker="triangle")
        self.scatter_chart.set_cut_lines([self.value.value()])
        self._plot_options_changed()
        self.test_evaluation = evaluate_sensitivity_tuning(
            tuning_result,
            test=self.test.currentText(),
            regions=[],
            polarity="Both",
            threshold=self.value.value(),
        )
        self._refresh_summary(tuning_result, considered, code_key, data)
        self._sync_threshold_table()

    def _refresh_summary(self, result, considered, code_key, data):
        """Write the Class Code Summary List for the current threshold."""
        if not hasattr(self, "summary_panel"):
            return

        def code_of(defect):
            raw = defect.get(code_key)
            if raw in (None, ""):
                raw = defect.get("class_code", 0)
            return _summary_code_label(raw)

        defects_by_id = {item.get("id"): item for item in result.get("defects", [])}
        test_population = [
            defects_by_id[identifier]
            for identifier in self.test_evaluation.get("considered_ids", [])
            if identifier in defects_by_id
        ]
        columns = _summary_code_sort(
            [code_of(item) for item in considered]
            + [code_of(item) for item in test_population]
        )
        current_cells = _summary_cells(
            considered, set(data.get("detected_ids") or []), code_of
        )
        test_cells = _summary_cells(
            test_population, set(self.test_evaluation.get("detected_ids") or []), code_of
        )
        eliminated = max(0, int(data["considered"]) - int(data["detected"]))
        note = (
            f"{eliminated}/{data['considered']} Events has been tuned-out by ST. "
            "They are now hidden."
        )
        self.summary_panel.set_summary(
            columns,
            [
                ("Current", current_cells, f"{data['detected']}/{data['considered']}"),
                (
                    "Test",
                    test_cells,
                    f"{self.test_evaluation['detected']}/{self.test_evaluation['considered']}",
                ),
            ],
            note,
        )
        self._sync_summary_selection()

    def _summary_row_selected(self, label):
        """Row selection in the summary drives the review visible defect filter."""
        if not hasattr(self, "filter_scope") or not label:
            return
        if hasattr(self, "st_page") and not self.st_page.isVisible():
            return
        self.filter_scope.setCurrentText(
            "Filter to Current Test" if label == "Test" else "Filter to Current Parameter"
        )

    def _sync_summary_selection(self):
        if not hasattr(self, "summary_panel") or not hasattr(self, "filter_scope"):
            return
        scope = self.filter_scope.currentText()
        if scope == "Filter to Current Test":
            self.summary_panel.select_row("Test")
        elif scope == "Filter to Current Parameter":
            self.summary_panel.select_row("Current")
        else:
            self.summary_panel.select_row("")

    def _toolbar_rule(self):
        rule = QFrame()
        rule.setFrameShape(QFrame.VLine)
        rule.setFixedSize(10, 46)
        rule.setStyleSheet("color: #8eacbf; background: transparent;")
        return rule

    def _toggle_options(self, *_args):
        self._options_panel.setVisible(not self._options_panel.isVisible())

    def _popup_menu(self, menu, button=None):
        """Anchor a toolbar dropdown under its caret."""
        if button is not None:
            origin = button.mapToGlobal(button.rect().bottomLeft())
        else:
            origin = self.mapToGlobal(self.rect().topLeft())
        menu.exec(origin)

    # ---------------------------------------------------- Finish menu (10-43)
    def _show_finish_menu(self, button=None):
        self._popup_menu(self.finish_menu(), button)

    def finish_menu(self):
        """Table 10-43: everything the Finish button can do before exiting."""
        menu = QMenu(self)
        for title, choices in (
            (
                "Restore Session Recipe",
                (
                    ("Parameters Only", "Restore Session - Parameters Only"),
                    ("All", "Restore Session - All"),
                ),
            ),
            (
                "Restore Inspection Recipe",
                (
                    ("Parameters Only", "Restore Inspection - Parameters Only"),
                    ("All", "Restore Inspection - All"),
                ),
            ),
        ):
            submenu = menu.addMenu(title)
            for label, action in choices:
                submenu.addAction(
                    label, lambda _checked=False, name=action: self._finish_as(name)
                )
        menu.addSeparator()
        menu.addAction(
            "Save Session Recipe", lambda _checked=False: self._finish_as("Save Session Recipe")
        )
        menu.addAction(
            "Save Recipe As...", lambda _checked=False: self._finish_as("Save Recipe As...")
        )
        menu.addAction(
            "Export Recipe As...", lambda _checked=False: self._finish_as("Export Recipe As...")
        )
        menu.addSeparator()
        menu.addAction("Save & Exit", lambda _checked=False: self._finish_as("Save & Exit"))
        # Table 10-43: Exit asks whether to save, and still allows leaving
        # without saving.
        menu.addAction("Exit", lambda _checked=False: self._exit_with_prompt())
        return menu

    def _exit_with_prompt(self):
        answer = QMessageBox.question(
            self,
            "Sensitivity Tuner",
            "Save the Sensitivity Tuner session before exiting?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save,
        )
        if answer == QMessageBox.Save:
            self._finish_as("Save & Exit")
        elif answer == QMessageBox.Discard:
            # Unsaved tuner work never survives the dialog.
            self.result_state = None
            self.state_persisted = False
            self.accept()

    def _finish_as(self, name):
        self.finish_action.setCurrentText(name)
        self._finish()

    # --------------------------------------------------- Options menu (10-44)
    def _show_options_menu(self, button=None):
        self._popup_menu(self.options_menu(), button)

    def options_menu(self):
        """Figure 10-218 / Table 10-44."""
        menu = QMenu(self)
        # Show Detected and Show Undetected are mutually exclusive; clearing a
        # check returns to "Show All Defects".
        for label, selected in (
            ("Show Detected Defects", "Show Detected Defects"),
            ("Show Undetected Defects", "Show Undetected Defects"),
        ):
            action = menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(self.show_mode.currentText() == selected)
            action.triggered.connect(
                lambda checked, name=selected: self._menu_show_mode(name, bool(checked))
            )
        menu.addSeparator()
        # Filter to Current Parameter and Filter to Current Test are mutually
        # exclusive; clearing a check returns to "No Review Filter".
        for label in ("Filter to Current Parameter", "Filter to Current Test"):
            action = menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(self.filter_scope.currentText() == label)
            action.triggered.connect(
                lambda checked, name=label: self._menu_filter_scope(name, bool(checked))
            )
        menu.addSeparator()
        auto_sort = menu.addAction("Auto Sort on Group (Manual Code)")
        auto_sort.setCheckable(True)
        auto_sort.setChecked(self.auto_sort.isChecked())
        auto_sort.triggered.connect(lambda checked: self.auto_sort.setChecked(bool(checked)))
        dark_menu = menu.addMenu("Dark Defect Filter Option")
        for label in (
            "Both",
            "Primary Dark Defects Only",
            "Secondary-Die Defects Only",
        ):
            action = dark_menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(self.dark_filter.currentText() == label)
            action.triggered.connect(
                lambda _checked=False, name=label: self._set_dark_filter(name)
            )
        menu.addSeparator()
        menu.addAction(
            "Region Selection Option ...", lambda _checked=False: self._select_regions()
        )
        menu.addAction(
            "Max Limit Configuration ...", lambda _checked=False: self._max_limits()
        )
        menu.addAction(
            "Advanced Sensitivity Parameters...",
            lambda _checked=False: self._advanced_parameters(),
        )
        return menu

    def _menu_show_mode(self, label, checked):
        self.show_mode.setCurrentText(label if checked else "Show All Defects")
        self._update()

    def _menu_filter_scope(self, label, checked):
        self.filter_scope.setCurrentText(label if checked else "No Review Filter")
        self._update()

    def _set_dark_filter(self, label):
        self.dark_filter.setCurrentText(label)
        self._update()

    def _show_stnef_menu(self, button=None):
        menu = QMenu(self)
        action = menu.addAction("Enable ST-NEF")
        action.setCheckable(True)
        action.setChecked(self.test.currentText() in self.nef_enabled_tests)
        action.triggered.connect(lambda checked: self.enable_nef.setChecked(bool(checked)))
        self._popup_menu(menu, button)

    def _scatter_value(self, defect, attribute):
        names = {
            "Noise": ("noise", "hlatcf_noise"),
            "Signal": ("signal",),
            "Area": ("area", "defect_area"),
        }.get(attribute, ("noise",))
        for name in names:
            value = defect.get(name)
            if isinstance(value, (int, float)):
                return float(value)
        return None

    def _grid_channels(self):
        return ("Channel 1", "Channel 2", "Channel 3", "Channel Fusion")

    def _grid_parameters(self):
        return ("Threshold", "Noise", "ABSMIN", "Gradient", "Color", "Max Threshold")

    def _field_key(self, channel, parameter):
        return "|".join((
            self.test.currentText(),
            self.region.currentText(),
            self.polarity.currentText(),
            self.algorithm.currentText(),
            self.path.currentText(),
            channel,
            parameter,
        ))

    def _parameter_fields(self):
        parameters = list(self.PARAMETERS.get(self.algorithm.currentText()) or ["Threshold"])
        return [
            (channel, parameter)
            for channel in self._grid_channels()
            for parameter in parameters
        ]

    def _build_threshold_table(self):
        header = QColor("#d7f3f6")
        self.threshold_table.setCellWidget(0, 0, self.polarity)
        self.threshold_table.setCellWidget(1, 0, self.algorithm)
        self.threshold_table.setCellWidget(2, 0, self.path)
        self.threshold_table.setSpan(0, 1, 1, 6)
        seq = QTableWidgetItem("Seq0")
        seq.setFlags(Qt.ItemIsEnabled)
        seq.setTextAlignment(Qt.AlignCenter)
        seq.setBackground(header)
        self.threshold_table.setItem(0, 1, seq)
        for column, label in enumerate(("Threshold", "Noise", "Absmin", "Gradient", "Color", "Threshold"), start=1):
            item = QTableWidgetItem(label)
            item.setFlags(Qt.ItemIsEnabled)
            item.setBackground(header)
            item.setTextAlignment(Qt.AlignCenter)
            self.threshold_table.setItem(1, column, item)
        for row, label in enumerate(("1 (Left)", "2 (Right)", "3 (Center)", "CFusion"), start=3):
            name = QTableWidgetItem(label)
            name.setFlags(Qt.ItemIsEnabled)
            self.threshold_table.setItem(row, 0, name)
        self.threshold_table.horizontalHeader().setVisible(False)
        self.threshold_table.setColumnWidth(0, 108)

    def _threshold_key(self, channel, path):
        return "|".join((
            self.test.currentText(),
            self.region.currentText(),
            self.polarity.currentText(),
            self.algorithm.currentText(),
            path,
            channel,
            "Threshold",
        ))

    def _sync_threshold_table(self):
        if not hasattr(self, "threshold_table"):
            return
        self.threshold_table.blockSignals(True)
        channels = self._grid_channels()
        parameters = self._grid_parameters()
        active_channel = self.channel.currentText()
        active_parameter = self.parameter.currentText()
        for index, channel in enumerate(channels):
            for column, parameter in enumerate(parameters, start=1):
                key = self._field_key(channel, parameter)
                value = self.parameter_values.get(key)
                if value is None and channel == active_channel and parameter == active_parameter:
                    value = self.value.value()
                if value is None:
                    value = {
                        "Threshold": 3.0, "Noise": 1.0, "ABSMIN": 40.0,
                        "Gradient": 0.2, "Color": 0.2, "Max Threshold": 6.0,
                    }.get(parameter, 0.0)
                item = QTableWidgetItem(f"{float(value):.2f}")
                item.setTextAlignment(Qt.AlignCenter)
                if key in self.committed_parameters:
                    item.setBackground(QColor("#8ee08e"))
                elif key in self.edited_parameters:
                    item.setBackground(QColor("#fff59d"))
                else:
                    item.setBackground(QColor("#ffffff"))
                self.threshold_table.setItem(index + 3, column, item)
        self.threshold_table.blockSignals(False)
        self._refresh_region_indicator()

    def _refresh_region_indicator(self):
        """Color the region chip for status only. Saving the recipe ignores this color."""
        if not hasattr(self, "region"):
            return
        prefix = f"{self.test.currentText()}|{self.region.currentText()}|"
        pending = any(
            key.startswith(prefix) and key not in self.committed_parameters
            for key in self.edited_parameters
        )
        committed = any(key.startswith(prefix) for key in self.committed_parameters)
        if pending:
            color = "#fff59d"
        elif committed:
            color = "#8ee08e"
        else:
            color = "#ffffff"
        self.region.setStyleSheet(
            f"QComboBox {{ background: {color}; font-weight: 700; min-width: 64px; }}"
        )

    def _threshold_cell_edited(self, item):
        if self._loading_parameter or item.row() < 3 or item.column() < 1:
            return
        channels = self._grid_channels()
        parameters = self._grid_parameters()
        try:
            number = float(item.text())
        except ValueError:
            return
        channel = channels[item.row() - 3]
        parameter = parameters[item.column() - 1]
        if self.parameter.findText(parameter) < 0:
            return
        self.channel.setCurrentText(channel)
        self.parameter.setCurrentText(parameter)
        self.value.setValue(number)

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
        hidden_ids = {str(value) for value in (state.get("hidden_defect_ids") or [])}
        hierarchy = state.get("hierarchical_classifier") or {}
        nodes = list(hierarchy.get("nodes") or [])
        page = getattr(self, "stnef_page", None)

        if nodes:
            if page is not None:
                attribute_number = page._attribute_number
                attribute_text = page._attribute_text
                partition_name = page._partition_name
            else:
                attribute_number = lambda defect, attribute: None
                attribute_text = lambda defect, attribute: _stnef_attribute_text(
                    defect.get({
                        "Area": "area",
                        "Signal": "signal",
                        "Primary Ch Intensity": "signal",
                    }.get(attribute, attribute.lower().replace(" ", "_")))
                )
                partition_name = lambda defect, partitions: None
            tree_hidden = _stnef_nuisance_ids(
                nodes,
                tuning_result.get("defects", []),
                attribute_number,
                attribute_text,
                partition_name,
            )
            hidden_ids.update(str(value) for value in tree_hidden)

        def classified_as_nuisance(defect):
            if str(defect.get("id", "")) in hidden_ids:
                return True
            return bool(defect.get("nuisance") or defect.get("binner_filtered"))

        for defect in tuning_result.get("defects", []):
            filtered = classified_as_nuisance(defect)
            if filtered and not keep_nuisance:
                self.nef_filtered_ids.append(defect.get("id"))
            else:
                copy = deepcopy(defect)
                copy["nuisance"] = bool(copy.get("nuisance") or filtered)
                kept.append(copy)
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
        self._sync_threshold_table()

    def _navigate(self, direction, uncommitted=False):
        fields = self._parameter_fields()
        if not fields:
            return
        current = (self.channel.currentText(), self.parameter.currentText())
        start = fields.index(current) if current in fields else 0
        if not uncommitted:
            channel, parameter = fields[(start + direction) % len(fields)]
            self.channel.setCurrentText(channel)
            self.parameter.setCurrentText(parameter)
            return
        original = current if current in fields else fields[0]
        for step in range(1, len(fields) + 1):
            channel, parameter = fields[(start + direction * step) % len(fields)]
            self.channel.blockSignals(True)
            self.parameter.blockSignals(True)
            self.channel.setCurrentText(channel)
            self.parameter.setCurrentText(parameter)
            key = self._selection_key()
            self.channel.setCurrentText(original[0])
            self.parameter.setCurrentText(original[1])
            self.channel.blockSignals(False)
            self.parameter.blockSignals(False)
            if key in self.edited_parameters and key not in self.committed_parameters:
                self.channel.setCurrentText(channel)
                self.parameter.setCurrentText(parameter)
                return

    def _switch_nef(self):
        test = self.test.currentText()
        page = self.stnef_page
        stored = self.nef_states.get(test)
        if stored and not page.nodes:
            pass
        if stored and stored.get("hierarchical_classifier"):
            page.nodes = deepcopy(stored["hierarchical_classifier"].get("nodes") or page.nodes)
            page._rebuild_tree(1)
        page._node_changed()
        self.st_button.setChecked(False)
        self.stnef_button.setChecked(True)
        self.section_label.setText("▼  STNEF")
        self.st_page.hide()
        page.show()

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
        signal_value = defect.get("signal")
        if not isinstance(signal_value, (int, float)) or isinstance(signal_value, bool):
            self.parameter_status.setText(
                f"Defect {identifier} has no measured signal; auto-tune is unavailable."
            )
            return
        signal = float(signal_value)
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
        if not action.startswith("Restore"):
            self._capture_stnef()
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
        self.state_persisted = action in self.SAVING_ACTIONS
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
    BLUE = "#1a3f86"
    DEFAULTS = [
        {"rule": "Added", "enabled": False, "state": True, "color": BLUE, "shape": "Rectangle"},
        {"rule": "Sample", "enabled": True, "state": True, "color": "#ff00ff", "shape": "Ellipse"},
        {"rule": "Repeater", "enabled": False, "state": True, "color": BLUE, "shape": "Rectangle"},
        {"rule": "Cluster", "enabled": True, "state": True, "color": "#1f8a32", "shape": "Rectangle"},
        {"rule": "Flag_PatchImage", "enabled": False, "state": True, "color": BLUE, "shape": "Rectangle"},
        {"rule": "Flag_HRDC", "enabled": False, "state": True, "color": BLUE, "shape": "Rectangle"},
        {"rule": "iADCCamera", "enabled": False, "state": True, "color": BLUE, "shape": "Rectangle"},
    ]
    SHAPES = ["Rectangle", "Ellipse"]

    def __init__(self, rules=None, parent=None, files=None, on_apply=None):
        super().__init__(parent)
        self.result_rules = None
        self.on_apply = on_apply
        self.files = deepcopy(files or {})
        self.setWindowTitle("Defect Display Rules")
        self.resize(560, 340)
        self.setStyleSheet("QDialog { background: #e6e1d4; } QTableWidget { background: #ffffff; }")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        bar = QHBoxLayout()
        bar.setSpacing(4)
        self.profile = QComboBox()
        self.profile.setEditable(False)
        self.profile.setFixedWidth(180)
        self.profile.setToolTip("Saved defect display rule set")
        names = ["(DEFAULT)"] + [name for name in self.files if name != "(DEFAULT)"]
        self.profile.addItems(names)
        bar.addWidget(self.profile)
        save = QPushButton()
        save.setIcon(self._bar_icon("save"))
        save.setToolTip("Save the current rules under the selected name")
        save.setFixedSize(26, 24)
        save.clicked.connect(self._save_profile)
        load = QPushButton()
        load.setIcon(self._bar_icon("check"))
        load.setToolTip("Load the selected rule set")
        load.setFixedSize(26, 24)
        load.clicked.connect(self._load_profile)
        delete = QPushButton()
        delete.setIcon(self._bar_icon("delete"))
        delete.setToolTip("Delete the selected rule set")
        delete.setFixedSize(26, 24)
        delete.clicked.connect(self._delete_profile)
        bar.addWidget(save)
        bar.addWidget(load)
        bar.addWidget(delete)
        bar.addStretch(1)
        layout.addLayout(bar)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Enabled", "Rules", "State", "Color", "Shape"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setColumnWidth(0, 70)
        self.table.setColumnWidth(2, 72)
        self.table.setColumnWidth(3, 110)
        self.table.setColumnWidth(4, 110)
        self.table.verticalHeader().setVisible(True)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.cellDoubleClicked.connect(self._edit_color)
        self._fill(deepcopy(rules or self.DEFAULTS))
        layout.addWidget(self.table, 1)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(apply_button)
        buttons.addWidget(cancel)
        buttons.addStretch(1)
        layout.addLayout(buttons)

    @staticmethod
    def _bar_icon(kind):
        pixmap = QPixmap(18, 18)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        if kind == "save":
            painter.setPen(QPen(QColor("#3a3a3a"), 1))
            painter.setBrush(QColor("#d8d2c4"))
            painter.drawRect(3, 2, 12, 14)
            painter.setBrush(QColor("#6f8fbf"))
            painter.drawRect(5, 2, 8, 5)
            painter.setBrush(QColor("#f7f4ea"))
            painter.drawRect(6, 10, 6, 4)
        elif kind == "check":
            painter.setPen(QPen(QColor("#1d4f9c"), 2))
            painter.drawLine(4, 9, 8, 13)
            painter.drawLine(8, 13, 14, 4)
        else:
            painter.setPen(QPen(QColor("#c42323"), 2))
            painter.drawLine(4, 4, 14, 14)
            painter.drawLine(14, 4, 4, 14)
        painter.end()
        return QIcon(pixmap)

    def _fill(self, rules):
        self.table.setRowCount(0)
        for rule in rules:
            row = self.table.rowCount()
            self.table.insertRow(row)
            enabled = QTableWidgetItem()
            enabled.setFlags((enabled.flags() | Qt.ItemIsUserCheckable) & ~Qt.ItemIsEditable)
            enabled.setCheckState(Qt.Checked if rule.get("enabled") else Qt.Unchecked)
            self.table.setItem(row, 0, enabled)
            name = QTableWidgetItem(str(rule.get("rule", "")))
            name.setFlags(name.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 1, name)
            state = QComboBox()
            state.addItems(["True", "False"])
            state.setCurrentText("True" if rule.get("state", True) else "False")
            self.table.setCellWidget(row, 2, state)
            self._set_color_item(row, rule.get("color", self.BLUE))
            shape = QComboBox()
            current = {"Circle": "Ellipse", "Square": "Rectangle", "Diamond": "Rectangle"}.get(
                rule.get("shape", "Rectangle"), rule.get("shape", "Rectangle")
            )
            choices = list(self.SHAPES)
            if current not in choices:
                choices.append(current)
            shape.addItems(choices)
            shape.setCurrentText(current)
            self.table.setCellWidget(row, 4, shape)

    def _set_color_item(self, row, color):
        item = QTableWidgetItem("")
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        item.setData(Qt.UserRole, color)
        item.setBackground(QColor(color))
        self.table.setItem(row, 3, item)

    def _edit_color(self, row, column):
        if column != 3:
            return
        current = QColor(self.table.item(row, 3).data(Qt.UserRole) or self.BLUE)
        chosen = QColorDialog.getColor(current, self, "Color")
        if chosen.isValid():
            self._set_color_item(row, chosen.name())

    def _collected_rules(self):
        rules = []
        for row in range(self.table.rowCount()):
            color = str(self.table.item(row, 3).data(Qt.UserRole) or "").strip()
            if not color.startswith("#") or len(color) not in (4, 7):
                QMessageBox.warning(self, "Defect Display Rules", f"Invalid color: {color}")
                return None
            rules.append({
                "enabled": self.table.item(row, 0).checkState() == Qt.Checked,
                "rule": self.table.item(row, 1).text(),
                "state": self.table.cellWidget(row, 2).currentText() == "True",
                "color": color,
                "shape": self.table.cellWidget(row, 4).currentText(),
            })
        return rules

    def _save_profile(self, *_args):
        rules = self._collected_rules()
        if rules is None:
            return
        name = self.profile.currentText() or "(DEFAULT)"
        self.files[name] = deepcopy(rules)
        if self.profile.findText(name) < 0:
            self.profile.addItem(name)
        self.profile.setCurrentText(name)

    def _load_profile(self, *_args):
        name = self.profile.currentText() or "(DEFAULT)"
        rules = self.files.get(name)
        if name == "(DEFAULT)" and not rules:
            rules = deepcopy(self.DEFAULTS)
        if rules:
            self._fill(deepcopy(rules))

    def _delete_profile(self, *_args):
        name = self.profile.currentText() or "(DEFAULT)"
        if name == "(DEFAULT)":
            self.files.pop("(DEFAULT)", None)
            self._fill(deepcopy(self.DEFAULTS))
            return
        self.files.pop(name, None)
        index = self.profile.findText(name)
        if index >= 0:
            self.profile.removeItem(index)

    def _finish(self, *_args):
        rules = self._collected_rules()
        if rules is None:
            return
        self.result_rules = rules
        self.files["(DEFAULT)"] = deepcopy(rules)
        if self.on_apply is not None:
            self.on_apply(rules, self.files)


class WaferMapDisplayOptionsDialog(QDialog):
    def __init__(self, wafer_map, show_die, show_defects, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Display Options")
        self.resize(280, 210)
        layout = QVBoxLayout(self)
        self.show_die = QCheckBox("Show die")
        self.show_die.setChecked(show_die.isChecked())
        self.show_reticle = QCheckBox("Show reticle")
        self.show_reticle.setChecked(wafer_map.show_reticle)
        self.show_defects = QCheckBox("Show defect")
        self.show_defects.setChecked(show_defects.isChecked())
        self.show_marker = QCheckBox("Show marker")
        self.show_marker.setChecked(wafer_map.show_marker)
        self.show_modulation = QCheckBox("Show reticle modulation")
        self.show_modulation.setChecked(wafer_map.show_reticle_modulation)
        for box in (self.show_die, self.show_reticle, self.show_defects, self.show_marker, self.show_modulation):
            layout.addWidget(box)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        ok = QPushButton("OK")
        ok.clicked.connect(lambda _checked=False: self.accept())
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(lambda _checked=False: self.reject())
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)


class DefectStackingSettingsDialog(QDialog):
    def __init__(self, tolerance_x, tolerance_y, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Defect Stacking settings")
        self.resize(320, 160)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Edit the stacking tolerance in wafer coordinates."))
        row_x = QHBoxLayout()
        row_x.addWidget(QLabel("X"))
        self.tolerance_x = QDoubleSpinBox()
        self.tolerance_x.setRange(0.0, 1.0)
        self.tolerance_x.setDecimals(3)
        self.tolerance_x.setSingleStep(0.01)
        self.tolerance_x.setValue(float(tolerance_x))
        row_x.addWidget(self.tolerance_x)
        layout.addLayout(row_x)
        row_y = QHBoxLayout()
        row_y.addWidget(QLabel("Y"))
        self.tolerance_y = QDoubleSpinBox()
        self.tolerance_y.setRange(0.0, 1.0)
        self.tolerance_y.setDecimals(3)
        self.tolerance_y.setSingleStep(0.01)
        self.tolerance_y.setValue(float(tolerance_y))
        row_y.addWidget(self.tolerance_y)
        layout.addLayout(row_y)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        ok = QPushButton("OK")
        ok.clicked.connect(lambda _checked=False: self.accept())
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(lambda _checked=False: self.reject())
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)


class GridColumnsDialog(QDialog):
    def __init__(self, selected, parent=None, columns=None):
        super().__init__(parent)
        self.result_columns = None
        self.checks = {}
        self.columns = list(columns or GRID_COLUMNS)
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
        midpoint = (len(self.columns) + 1) // 2
        for index, (key, label) in enumerate(self.columns):
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
        selected = [key for key, _label in self.columns if self.checks[key].isChecked()]
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
            names = list(self.review_result.get("selected_tests") or [])
            dialog = WaferPostProcessingDialog(
                self.state.get("analysis"),
                test_count=len(names),
                tests=names,
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


class _FolderTile(QFrame):
    def __init__(self, on_press, parent=None):
        super().__init__(parent)
        self.on_press = on_press

    def mousePressEvent(self, event):
        self.on_press(event)
        super().mousePressEvent(event)


class ClassifyThumbnailStrip(QWidget):
    """Horizontal filmstrip of the defects currently shown in Advanced Classify."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.defects = []
        self.selected_id = None
        self.on_chosen = None
        self.setMinimumHeight(86)

    def set_defects(self, defects, selected_id=None):
        self.defects = list(defects)
        self.selected_id = selected_id
        self.setMinimumWidth(max(80, len(self.defects) * 76 + 8))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#f7f7f4"))
        for index, defect in enumerate(self.defects[:80]):
            left = 6 + index * 76
            chosen = defect.get("id") == self.selected_id
            painter.setPen(QPen(QColor("#1d4f9c") if chosen else QColor("#b0ada6"), 2 if chosen else 1))
            painter.setBrush(QColor("#6a7f92"))
            painter.drawRect(left, 8, 68, 46)
            painter.setPen(QColor("#f4f4f1"))
            painter.drawText(left + 4, 28, f"{defect.get('class_code', 0)}")
            painter.setPen(QColor("#333333"))
            painter.drawText(left, 72, str(defect.get("id", "")))
        painter.end()

    def mousePressEvent(self, event):
        point = event.position() if hasattr(event, "position") else event.pos()
        index = int((point.x() - 6) // 76)
        if 0 <= index < len(self.defects) and self.on_chosen:
            self.on_chosen(self.defects[index].get("id"))


class ReviewPaneSplitter(QWidget):
    """Review panes. Review is a four-way cross; Wide Grid and Advanced Classify rearrange them."""

    HANDLE = 8

    def __init__(self, parent=None):
        super().__init__(parent)
        self.panes = []
        self.split_x = 0.42
        self.split_y = 0.52
        self.arrangement = "review"
        self._drag = None
        self._press = None
        self.tab_host = QTabWidget(self)
        self.tab_host.hide()
        self.setMouseTracking(True)
        self.setMinimumSize(480, 320)
        self.setToolTip("Drag a splitter bar to resize the panes.")

    def set_panes(self, top_left, top_right, bottom_left, bottom_right):
        self.panes = [top_left, top_right, bottom_left, bottom_right]
        for pane in self.panes:
            pane.setParent(self)
            pane.show()
        self._place()

    def apply_layout(self, vertical, top, bottom):
        top_span = max(1, sum(top))
        bottom_span = max(1, sum(bottom))
        vertical_span = max(1, sum(vertical))
        split_x = ((top[0] / top_span) + (bottom[0] / bottom_span)) / 2
        split_y = vertical[0] / vertical_span
        self.set_ratios(split_x, split_y)

    def set_ratios(self, split_x, split_y):
        self.split_x = float(split_x)
        self.split_y = float(split_y)
        self._place()

    def set_arrangement(self, arrangement):
        self.arrangement = arrangement or "review"
        self._place()

    def resizeEvent(self, event):
        self._place()
        super().resizeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#8d8980"))
        x, y, right, bottom = self._handle_rect()
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#6f6b64"))
        if self.arrangement == "wide":
            painter.drawRect(x, 0, self.HANDLE, y)
            painter.drawRect(0, y, self.width(), self.HANDLE)
        elif self.arrangement == "classify":
            painter.drawRect(0, y, self.width(), self.HANDLE)
            painter.drawRect(x, y + self.HANDLE, self.HANDLE, bottom)
        else:
            painter.drawRect(x, 0, self.HANDLE, self.height())
            painter.drawRect(0, y, self.width(), self.HANDLE)
            painter.fillRect(x - 3, y - 3, self.HANDLE + 6, self.HANDLE + 6, QColor("#5e5a54"))
        painter.end()

    def _handle_rect(self):
        width = max(self.width(), 1)
        height = max(self.height(), 1)
        span_x = max(1, width - self.HANDLE)
        span_y = max(1, height - self.HANDLE)
        x = int(self.split_x * span_x)
        y = int(self.split_y * span_y)
        return x, y, width - x - self.HANDLE, height - y - self.HANDLE

    def _release_tabs(self):
        while self.tab_host.count():
            widget = self.tab_host.widget(0)
            self.tab_host.removeTab(0)
            widget.setParent(self)
            widget.show()
        self.tab_host.hide()

    def _show_tabs(self, pages):
        current = [self.tab_host.widget(index) for index in range(self.tab_host.count())]
        wanted = [widget for widget, _title in pages]
        if current != wanted:
            self._release_tabs()
            for widget, title in pages:
                widget.setParent(self.tab_host)
                self.tab_host.addTab(widget, title)
                widget.show()
        self.tab_host.show()

    def _place(self):
        if len(self.panes) != 4 or self.width() < 2 or self.height() < 2:
            return
        self._clamp()
        x, y, right, bottom = self._handle_rect()
        wafer_map, gallery, grid, chart = self.panes
        if self.arrangement == "wide":
            wafer_map.setParent(self)
            grid.setParent(self)
            wafer_map.setGeometry(0, 0, x, y)
            wafer_map.show()
            self.tab_host.setParent(self)
            self._show_tabs([(gallery, "Image Gallery"), (chart, "Defect Chart")])
            self.tab_host.setGeometry(x + self.HANDLE, 0, right, y)
            grid.setGeometry(0, y + self.HANDLE, self.width(), bottom)
            grid.show()
            return
        self._release_tabs()
        for pane in self.panes:
            pane.setParent(self)
        if self.arrangement == "classify":
            gallery.setGeometry(0, 0, self.width(), y)
            gallery.show()
            grid.setGeometry(0, y + self.HANDLE, x, bottom)
            grid.show()
            wafer_map.setGeometry(x + self.HANDLE, y + self.HANDLE, right, bottom)
            wafer_map.show()
            chart.hide()
            return
        chart.show()
        wafer_map.setGeometry(0, 0, x, y)
        gallery.setGeometry(x + self.HANDLE, 0, right, y)
        grid.setGeometry(0, y + self.HANDLE, x, bottom)
        chart.setGeometry(x + self.HANDLE, y + self.HANDLE, right, bottom)
        for pane in self.panes:
            pane.show()

    def _clamp(self):
        min_x = 140 / max(self.width(), 1)
        min_y = 90 / max(self.height(), 1)
        self.split_x = min(max(self.split_x, min_x), 1 - min_x)
        self.split_y = min(max(self.split_y, min_y), 1 - min_y)

    def _hit(self, position):
        x, y, _right, bottom = self._handle_rect()
        px, py = position.x(), position.y()
        on_vertical = abs(px - (x + self.HANDLE / 2)) <= 6
        on_horizontal = abs(py - (y + self.HANDLE / 2)) <= 6
        if self.arrangement == "wide":
            if on_vertical and py <= y:
                return "x"
            if on_horizontal:
                return "y"
            return None
        if self.arrangement == "classify":
            if on_horizontal:
                return "y"
            if on_vertical and py >= y + self.HANDLE:
                return "x"
            return None
        near_center = abs(px - (x + self.HANDLE / 2)) <= 14 and abs(py - (y + self.HANDLE / 2)) <= 14
        if near_center or (on_vertical and on_horizontal):
            return "both"
        if on_vertical and y <= py <= y + self.HANDLE:
            return None
        if on_vertical:
            return "x"
        if on_horizontal:
            return "y"
        return None

    def mousePressEvent(self, event):
        point = event.position() if hasattr(event, "position") else event.pos()
        self._drag = self._hit(point)
        self._press = (point.x(), point.y(), self.split_x, self.split_y)
        if self._drag:
            event.accept()

    def mouseMoveEvent(self, event):
        point = event.position() if hasattr(event, "position") else event.pos()
        if not self._drag or self._press is None:
            kind = self._hit(point)
            if kind == "both":
                self.setCursor(Qt.SizeAllCursor)
            elif kind == "x":
                self.setCursor(Qt.SplitHCursor)
            elif kind == "y":
                self.setCursor(Qt.SplitVCursor)
            else:
                self.unsetCursor()
            return
        origin_x, origin_y, split_x, split_y = self._press
        if self._drag in ("x", "both"):
            self.split_x = split_x + (point.x() - origin_x) / max(1, self.width() - self.HANDLE)
        if self._drag in ("y", "both"):
            self.split_y = split_y + (point.y() - origin_y) / max(1, self.height() - self.HANDLE)
        self._place()

    def mouseReleaseEvent(self, event):
        self._drag = None
        self._press = None


class ReviewStatusLabel(QLabel):
    """Keeps the recipe, lot, and defect summary while operation notes are added."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._summary = ""
        self._message = ""

    def set_summary(self, text: str):
        self._summary = text
        self._message = ""
        self._publish()

    def setText(self, text: str):
        self._message = text or ""
        self._publish()

    def _publish(self):
        if self._summary and self._message and self._message != self._summary:
            shown = f"{self._summary}    {self._message}"
        else:
            shown = self._summary or self._message
        QLabel.setText(self, shown)


class _ReviewStatusIcon(QWidget):
    def __init__(self, kind: str, parent=None, on_click=None):
        super().__init__(parent)
        self.kind = kind
        self.orientation = 180
        self.online = True
        self.on_click = on_click
        self.setFixedSize(22, 18)

    def mousePressEvent(self, event):
        if self.on_click is not None:
            self.on_click()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if self.kind == "orientation":
            painter.setPen(QPen(QColor("#4a4a4a"), 1))
            painter.setBrush(QColor("#d8d8d8"))
            painter.drawPath(wafer_disk_with_notch(2, 1, 16, int(self.orientation)))
        elif self.kind == "ilink":
            painter.setPen(QPen(QColor("#1d6b28"), 1))
            painter.setBrush(QColor("#3cba4a") if self.online else QColor("#8a8a8a"))
            painter.drawEllipse(3, 2, 14, 14)
        else:
            painter.setPen(QPen(QColor("#1f8f32"), 2))
            painter.drawLine(11, 1, 11, 17)
            painter.drawLine(3, 9, 19, 9)
        painter.end()


_REVIEW_OPTICS_WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_REVIEW_OPTICS_PIXEL_SIZES = (
    "2.000 (5X)",
    "1.000 (10X)",
    "0.500 (20X)",
    "0.250 (40X)",
    "0.1000 (100X)",
)
_DEFAULT_REVIEW_OPTICS_ORDER = (
    "DefaultAttemptAlignmentHighMag",
    "DefaultAttemptAlignmentLowMag",
    "DefaultCameraRegistrationHighMag",
    "DefaultCameraRegistrationLowMag",
    "DefaultReview",
    "DefaultSetupHighMag",
    "DefaultSetupLowMag",
    "PumaDefaultReview",
    "PumaDefaultSetupHighMag",
    "PumaDefaultSetupLowMag",
)


def _review_optics_timestamp(moment: datetime | None = None) -> str:
    moment = moment or datetime.now()
    weekday = _REVIEW_OPTICS_WEEKDAYS[moment.weekday()]
    return f"{moment:%Y/%m/%d} ({weekday}) {moment:%H:%M:%S}"


def _review_optics_pixmap(filename: str, height: int = 20) -> QPixmap:
    return vector_pixmap(filename, height)


def default_review_optics_files() -> dict:
    stamp = "2007/03/07 (Wed) 21:19:22"
    presets = {
        "DefaultAttemptAlignmentHighMag": ("0.250 (40X)", "BrightField", 20, 100, True, 0.0, 1.0),
        "DefaultAttemptAlignmentLowMag": ("2.000 (5X)", "BrightField", 20, 100, True, 0.0, 1.0),
        "DefaultCameraRegistrationHighMag": ("0.500 (20X)", "BrightField", 20, 100, True, 0.0, 1.0),
        "DefaultCameraRegistrationLowMag": ("2.000 (5X)", "DarkField", 100, 100, True, 0.0, 1.0),
        "DefaultReview": ("0.1000 (100X)", "BrightField", 5, 100, True, 0.0, 1.0),
        "DefaultSetupHighMag": ("0.250 (40X)", "BrightField", 20, 100, True, 0.0, 1.0),
        "DefaultSetupLowMag": ("2.000 (5X)", "BrightField", 20, 100, True, 0.0, 1.0),
        "PumaDefaultReview": ("1.000 (10X)", "BrightField", 20, 100, True, 0.0, 1.0),
        "PumaDefaultSetupHighMag": ("0.250 (40X)", "BrightField", 10, 100, True, 0.0, 1.0),
        "PumaDefaultSetupLowMag": ("2.000 (5X)", "BrightField", 20, 100, True, 0.0, 1.0),
    }
    files = {}
    for name, values in presets.items():
        pixel, mode, aperture, light, automatic, focus, step = values
        files[name] = {
            "pixel_size": pixel,
            "imaging_mode": mode,
            "aperture": aperture,
            "light_level": light,
            "light_automatic": automatic,
            "focus_offset": focus,
            "focus_step": step,
            "updated": stamp,
        }
    return files


class SelectReviewOpticsFileDialog(QDialog):
    """Figure 10-5. Pick a saved Review Optics file."""

    def __init__(self, files: dict, parent=None):
        super().__init__(parent)
        self.files = files
        self.selected_name = ""
        self.setWindowTitle("Select Review Optics File")
        self.resize(520, 420)
        self.setStyleSheet(
            "QDialog { background: #d8d3c8; font-family: Arial; font-size: 11px; }"
            "QTableWidget { background: #ffffff; gridline-color: #c8c4ba; }"
            "QHeaderView::section { background: #e6e2d6; border: 1px solid #b7b2a6; padding: 3px; }"
            "QLineEdit { background: #ffffff; border: 1px solid #7a756c; }"
            "QPushButton { min-width: 78px; min-height: 26px; background: #ece8de;"
            " border-top: 1px solid #ffffff; border-left: 1px solid #ffffff;"
            " border-right: 1px solid #6e6b64; border-bottom: 1px solid #6e6b64; }"
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 12)
        found = QLabel(f"File(s) Found: {len(files)}")
        found.setAlignment(Qt.AlignRight)
        root.addWidget(found)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Selected File", "Last Update"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        ordered = [name for name in _DEFAULT_REVIEW_OPTICS_ORDER if name in files]
        ordered.extend(sorted(name for name in files if name not in ordered))
        for name in ordered:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(name))
            self.table.setItem(row, 1, QTableWidgetItem(str(files[name].get("updated", ""))))
        self.table.itemSelectionChanged.connect(self._selection_changed)
        self.table.itemDoubleClicked.connect(lambda _item: self._accept())
        root.addWidget(self.table, 1)
        selected = QHBoxLayout()
        selected.addWidget(QLabel("Selected File:"))
        self.selected_file = QLineEdit("*")
        self.selected_file.setReadOnly(True)
        selected.addWidget(self.selected_file, 1)
        root.addLayout(selected)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        ok = QPushButton("OK")
        ok.clicked.connect(self._accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(ok)
        buttons.addSpacing(18)
        buttons.addWidget(cancel)
        buttons.addStretch(1)
        root.addLayout(buttons)

    def _selection_changed(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            self.selected_file.setText("*")
            self.selected_name = ""
            return
        name = self.table.item(rows[0].row(), 0).text()
        self.selected_name = name
        self.selected_file.setText(name)

    def _accept(self):
        if not self.selected_name or self.selected_name not in self.files:
            return
        self.accept()


class AdvancedReviewOpticsSettingsDialog(QDialog):
    """Figure 10-6. Pixel size, light, imaging mode, focus, aperture, and named files."""

    def __init__(self, values: dict, files: dict, parent=None, on_apply=None):
        super().__init__(parent)
        self.files = files
        self.on_apply = on_apply
        self.applied_values = None
        self._brightfield_aperture = int(values.get("aperture", 20))
        self.setWindowTitle("Advanced Review Optics Settings")
        self.resize(640, 390)
        self.setStyleSheet(
            "QDialog { background: #d5d0c4; color: #111111; font-family: Arial; font-size: 11px; }"
            "QGroupBox { border: 1px solid #8d897f; margin-top: 12px; background: #d5d0c4; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; color: #1d4f9c; }"
            "QComboBox, QSpinBox, QDoubleSpinBox { background: #ffffff; border: 1px solid #7a756c; min-height: 22px; }"
            "QPushButton { background: #ece8de; min-height: 26px; padding: 2px 12px;"
            " border-top: 1px solid #ffffff; border-left: 1px solid #ffffff;"
            " border-right: 1px solid #6e6b64; border-bottom: 1px solid #6e6b64; }"
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 12)
        root.setSpacing(12)
        root.addLayout(self._settings_form(values))
        root.addWidget(self._named_settings())
        root.addLayout(self._footer())
        self._apply_values(values)

    def _icon_label(self, filename: str) -> QLabel:
        label = QLabel()
        pixmap = _review_optics_pixmap(filename)
        if not pixmap.isNull():
            label.setPixmap(pixmap)
            label.setFixedSize(pixmap.size())
        return label

    def _settings_form(self, values: dict) -> QGridLayout:
        form = QGridLayout()
        form.setHorizontalSpacing(8)
        form.setVerticalSpacing(10)
        form.setColumnMinimumWidth(0, 150)
        form.setColumnMinimumWidth(3, 168)

        self.pixel_size = QComboBox()
        self.pixel_size.addItems(list(_REVIEW_OPTICS_PIXEL_SIZES))
        self.pixel_size.setFixedWidth(150)
        self.imaging_mode = QComboBox()
        self.imaging_mode.addItems(["BrightField", "DarkField"])
        self.imaging_mode.setFixedWidth(150)
        self.imaging_mode.currentTextChanged.connect(self._imaging_mode_changed)
        self.aperture = QSpinBox()
        self.aperture.setRange(0, 100)
        self.aperture.setSuffix(" %")
        self.aperture.setFixedWidth(110)
        self.illumination = QSpinBox()
        self.illumination.setRange(0, 255)
        self.illumination.setFixedWidth(90)
        self.light_automatic = True
        self.light_button = QPushButton()
        self.light_button.setFixedSize(36, 26)
        self.light_button.setToolTip("Illumination Level")
        self.light_button.clicked.connect(self._toggle_light)
        self.focus_offset = QDoubleSpinBox()
        self.focus_offset.setRange(-50.0, 50.0)
        self.focus_offset.setDecimals(3)
        self.focus_offset.setSuffix(" μm")
        self.focus_offset.setFixedWidth(110)
        self.focus_step = QDoubleSpinBox()
        self.focus_step.setRange(0.001, 10.0)
        self.focus_step.setDecimals(3)
        self.focus_step.setSingleStep(0.001)
        self.focus_step.setSuffix(" μm")
        self.focus_step.setValue(float(values.get("focus_step", 1.0)))
        self.focus_step.setFixedWidth(110)
        self.focus_step.setToolTip("Focus Offset Step Size. Adjustable in increments of 0.001 μm.")
        self.focus_step.valueChanged.connect(self._step_changed)

        form.addWidget(QLabel("Pixel Size:"), 0, 0, alignment=Qt.AlignRight)
        form.addWidget(self._icon_label("optics_pixel.png"), 0, 1)
        form.addWidget(self.pixel_size, 0, 2)
        form.addWidget(QLabel("Illumination Level:"), 0, 3, alignment=Qt.AlignRight)
        form.addWidget(self.light_button, 0, 4)
        form.addWidget(self.illumination, 0, 5)
        form.addWidget(QLabel("Imaging Mode:"), 1, 0, alignment=Qt.AlignRight)
        form.addWidget(self._icon_label("optics_imaging.png"), 1, 1)
        form.addWidget(self.imaging_mode, 1, 2)
        form.addWidget(QLabel("Focus Offset:"), 1, 3, alignment=Qt.AlignRight)
        form.addWidget(self._icon_label("optics_focus.png"), 1, 4)
        form.addWidget(self.focus_offset, 1, 5)
        form.addWidget(QLabel("Aperture:"), 2, 0, alignment=Qt.AlignRight)
        form.addWidget(self._icon_label("optics_aperture.png"), 2, 1)
        form.addWidget(self.aperture, 2, 2)
        form.addWidget(QLabel("Focus Offset Step Size:"), 2, 3, alignment=Qt.AlignRight)
        form.addWidget(self.focus_step, 2, 5)
        form.setColumnStretch(6, 1)
        return form

    def _named_settings(self) -> QGroupBox:
        box = QGroupBox("Review Optics Named Settings")
        row = QHBoxLayout(box)
        row.setContentsMargins(12, 16, 12, 12)
        row.setSpacing(8)
        self.named_settings = QComboBox()
        self.named_settings.setEditable(True)
        self.named_settings.setFixedWidth(230)
        self.named_settings.addItem("")
        for name in _DEFAULT_REVIEW_OPTICS_ORDER:
            if name in self.files:
                self.named_settings.addItem(name)
        for name in sorted(self.files):
            if self.named_settings.findText(name) < 0:
                self.named_settings.addItem(name)
        browse = QPushButton("...")
        browse.setFixedSize(28, 26)
        browse.setToolTip("Browse")
        browse.clicked.connect(self._browse)
        load = QPushButton("Load")
        save = QPushButton("Save")
        delete = QPushButton("Delete")
        load.clicked.connect(self._load_file)
        save.clicked.connect(self._save_file)
        delete.clicked.connect(self._delete_file)
        for button in (load, save, delete):
            button.setFixedWidth(72)
        row.addWidget(self.named_settings)
        row.addWidget(browse)
        row.addSpacing(8)
        row.addWidget(load)
        row.addWidget(save)
        row.addWidget(delete)
        row.addStretch(1)
        return box

    def _footer(self) -> QHBoxLayout:
        footer = QHBoxLayout()
        footer.addStretch(1)
        ok = QPushButton("OK")
        apply_button = QPushButton("Apply")
        cancel = QPushButton("Cancel")
        for button in (ok, apply_button, cancel):
            button.setFixedWidth(96)
        ok.clicked.connect(self._accept)
        apply_button.clicked.connect(self._apply)
        cancel.clicked.connect(self.reject)
        footer.addWidget(ok)
        footer.addSpacing(28)
        footer.addWidget(apply_button)
        footer.addSpacing(28)
        footer.addWidget(cancel)
        footer.addStretch(1)
        return footer

    def _current_values(self) -> dict:
        return {
            "pixel_size": self.pixel_size.currentText(),
            "imaging_mode": self.imaging_mode.currentText(),
            "aperture": self.aperture.value(),
            "light_level": self.illumination.value(),
            "light_automatic": self.light_automatic,
            "focus_offset": self.focus_offset.value(),
            "focus_step": self.focus_step.value(),
        }

    def _apply_values(self, values: dict):
        pixel = str(values.get("pixel_size") or "1.000 (10X)")
        if self.pixel_size.findText(pixel) < 0:
            self.pixel_size.addItem(pixel)
        self.pixel_size.setCurrentText(pixel)
        self.light_automatic = bool(values.get("light_automatic", True))
        self._refresh_light_button()
        self.illumination.setValue(int(values.get("light_level", 100)))
        step = float(values.get("focus_step", 1.0) or 1.0)
        self.focus_step.blockSignals(True)
        self.focus_step.setValue(step)
        self.focus_step.blockSignals(False)
        self.focus_offset.setSingleStep(max(0.001, step))
        self.focus_offset.setValue(float(values.get("focus_offset", 0.0)))
        mode = str(values.get("imaging_mode") or "BrightField")
        aperture = int(values.get("aperture", 20))
        if mode != "DarkField":
            self._brightfield_aperture = aperture
        self.imaging_mode.blockSignals(True)
        self.imaging_mode.setCurrentText(mode if mode in ("BrightField", "DarkField") else "BrightField")
        self.imaging_mode.blockSignals(False)
        self._imaging_mode_changed(self.imaging_mode.currentText())
        if self.imaging_mode.currentText() != "DarkField":
            self.aperture.setValue(aperture)

    def _refresh_light_button(self):
        pixmap = _review_optics_pixmap(
            "optics_light_auto.png" if self.light_automatic else "optics_light.png"
        )
        if not pixmap.isNull():
            self.light_button.setIcon(QIcon(pixmap))
            self.light_button.setIconSize(pixmap.size())
        self.illumination.setEnabled(not self.light_automatic)
        self.light_button.setToolTip(
            "Illumination Level Automatic" if self.light_automatic else "Illumination Level Manual"
        )

    def _toggle_light(self):
        self.light_automatic = not self.light_automatic
        self._refresh_light_button()

    def _imaging_mode_changed(self, mode: str):
        if mode == "DarkField":
            if self.aperture.isEnabled():
                self._brightfield_aperture = self.aperture.value()
            self.aperture.setEnabled(False)
            self.aperture.setValue(100)
        else:
            self.aperture.setEnabled(True)
            if self.aperture.value() == 100:
                self.aperture.setValue(self._brightfield_aperture)

    def _step_changed(self, value: float):
        self.focus_offset.setSingleStep(max(0.001, float(value)))

    def _set_named_text(self, name: str):
        if self.named_settings.findText(name) < 0:
            self.named_settings.addItem(name)
        self.named_settings.setCurrentText(name)

    def _browse(self):
        dialog = SelectReviewOpticsFileDialog(self.files, self)
        if _exec(dialog) != QDialog.Accepted or not dialog.selected_name:
            return
        self._set_named_text(dialog.selected_name)

    def _load_file(self):
        name = self.named_settings.currentText().strip()
        settings = self.files.get(name)
        if not settings:
            QMessageBox.information(self, "Review Optics Named Settings", "Select a Review Optics file to load.")
            return
        self._apply_values(settings)

    def _save_file(self):
        name = self.named_settings.currentText().strip()
        if not name:
            QMessageBox.warning(self, "Review Optics Named Settings", "Enter a name before saving.")
            return
        self.files[name] = {**self._current_values(), "updated": _review_optics_timestamp()}
        self._set_named_text(name)

    def _delete_file(self):
        name = self.named_settings.currentText().strip()
        if not name or name not in self.files:
            QMessageBox.information(self, "Review Optics Named Settings", "Select a Review Optics file to delete.")
            return
        answer = QMessageBox.question(
            self,
            "Puma 9xxx",
            f"Do you want to delete the Review Optics File '{name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.files.pop(name, None)
        index = self.named_settings.findText(name)
        if index >= 0:
            self.named_settings.removeItem(index)
        self.named_settings.setCurrentText("")

    def _apply(self):
        self.applied_values = self._current_values()
        if self.on_apply is not None:
            self.on_apply(self.applied_values)

    def _accept(self):
        self._apply()
        self.accept()


class _IconCommandButton(QPushButton):
    """Icon-only face. text() stays available for the manual tests."""

    def paintEvent(self, event):
        icon = self.icon()
        if icon.isNull():
            return
        painter = QPainter(self)
        icon.paint(painter, self.rect(), Qt.AlignLeft | Qt.AlignVCenter)
        painter.end()


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
        if result is None:
            recipe = current_recipe or {}
            result = {
                "placeholder": True,
                "inspection": recipe.get("inspection", ""),
                "device": recipe.get("device", ""),
                "step": recipe.get("step", ""),
                "lot_id": "",
                "wafer_id": "",
                "defects": [],
                "status": "No Lot",
                "sensitivity_data": False,
                "selected_tests": [],
            }
        self.result = deepcopy(result)
        self._review_lot_ready = self.result.get("source_format") == "KLARF"
        self.store = store
        self.current_recipe = current_recipe
        if (
            self.current_recipe
            and "sensitivity_data" not in result
            and sensitivity_test_names(self.current_recipe)
        ):
            self.result = apply_collected_sensitivity(self.result, self.current_recipe)
        self.snapshot_mode = snapshot_mode
        if self.snapshot_mode and not self.result.get("placeholder"):
            self._review_lot_ready = True
        self.snapshot_update_callback = snapshot_update_callback
        self.complete_data_controls = []
        self.machine_free_controls = []
        self.machine_free_actions = []
        self.review_toolbar_widgets = []
        self.review_image_toolbar_widgets = []
        self.filters = default_filter_state()
        self.available_grid_columns = _review_grid_columns(self.result)
        self.grid_columns = _initial_review_grid_columns(self.result, self.available_grid_columns)
        self.visible_defects = []
        self.selected_id = None
        self.selected_ids = set()
        self.advanced_class_codes = None
        self.gallery_class_codes = set()
        self.gallery_attribute_value = None
        self.folder_view = "icons"
        self.advanced_attribute_values = None
        self.review_optics_state = {
            "magnification_step": 0,
            "light_level": 50,
            "focus_offset": 0,
            "aperture": 50,
        }
        self.coordinate_mode = "wafer"
        self._loading = False
        self.setWindowTitle("Snapshot Review" if snapshot_mode else "Wafer Inspection Review")
        self.setWindowFlags(
            Qt.Window
            | Qt.WindowTitleHint
            | Qt.WindowSystemMenuHint
            | Qt.WindowMinimizeButtonHint
            | Qt.WindowMaximizeButtonHint
            | Qt.WindowCloseButtonHint
        )
        self.resize(1320, 820)
        self.setMinimumSize(980, 650)
        self._parent_size_limit = None
        self._restored_size = None
        self._in_size_adjust = False
        self.setStyleSheet(
            "QFrame#pane { background: #f2f0ea; border: 1px solid #a8a49a; }"
        )
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self._outer_layout = outer
        self.access_menu_bar = self._build_access_menu()
        outer.addWidget(self.access_menu_bar)
        self.workspace_scroll = QScrollArea()
        self.workspace_scroll.setWidgetResizable(True)
        self.workspace_scroll.setFrameShape(QFrame.NoFrame)
        self.workspace = QWidget()
        self.workspace.setMinimumSize(1280, 700)
        root = QVBoxLayout(self.workspace)
        root.setContentsMargins(5, 5, 5, 5)
        root.addWidget(self._optics_toolbar())
        root.addLayout(self._toolbar())
        self.pane_splitter = ReviewPaneSplitter()
        self.map_pane = self._map_pane()
        self.gallery_pane = self._gallery_pane()
        self.grid_pane = self._grid_pane()
        self.chart_pane = self._chart_pane()
        self.pane_splitter.set_panes(self.map_pane, self.gallery_pane, self.grid_pane, self.chart_pane)
        self.pane_splitter.apply_layout([390, 350], [520, 760], [900, 380])
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(4)
        body.addWidget(self._command_rail())
        panes = QVBoxLayout()
        panes.setContentsMargins(0, 0, 0, 0)
        panes.setSpacing(2)
        panes.addWidget(self.pane_splitter, 1)
        self.defect_details_bar = self._defect_details_bar()
        panes.addWidget(self.defect_details_bar)
        self.review_panes_layout = panes
        body.addLayout(panes, 1)
        root.addLayout(body, 1)
        root.addWidget(self._status_bar())
        self.workspace_scroll.setWidget(self.workspace)
        outer.addWidget(self.workspace_scroll)
        self._fit_inside_parent()
        self._refresh_snapshot_controls()
        self._refresh_defects()
        self.fullscreen_adapter = FullscreenWindowAdapter(self, base=(1320, 820), scale_with_size=True)
        # Full screen drops the native title bar, so the workspace carries its
        # own minimize / restore / close controls. They are installed last, once
        # the layouts above are settled: creating layout children into the
        # workspace while it is still being assembled made Qt re-enter the grid
        # layout during the first show.
        self.window_buttons = self._install_window_controls()
        self.window_buttons.sync()

    def _install_window_controls(self):
        controls = WindowCaptionButtons(self, self)
        # The controls share the menu bar row so they sit in the real top-right
        # corner once full screen hides the native title bar.
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(0)
        top_row.addWidget(self.access_menu_bar, 1)
        top_row.addWidget(controls, 0, Qt.AlignTop)
        outer = getattr(self, "_outer_layout", None)
        if outer is not None:
            outer.removeWidget(self.access_menu_bar)
            outer.insertLayout(0, top_row)
        return controls

    def showEvent(self, event):
        self._fit_inside_parent()
        if hasattr(self, "window_buttons"):
            self.window_buttons.sync()
        super().showEvent(event)

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange and not self.isMinimized():
            if self.isMaximized() or self.isFullScreen():
                self.setMaximumSize(16777215, 16777215)
            else:
                previous = event.oldState() if hasattr(event, "oldState") else Qt.WindowNoState
                if previous & (Qt.WindowMaximized | Qt.WindowFullScreen):
                    self._apply_restored_size()
        if hasattr(self, "window_buttons"):
            self.window_buttons.sync()
        super().changeEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._in_size_adjust or self.isMaximized() or self.isFullScreen() or self.isMinimized():
            return
        if self._size_is_screen():
            return
        self._remember_normal_size()

    def _size_is_screen(self):
        screen = self.screen() if hasattr(self, "screen") else None
        if screen is None:
            screen = QApplication.primaryScreen()
        if screen is None:
            return False
        available = screen.availableGeometry()
        return self.width() >= available.width() - 4 and self.height() >= available.height() - 4

    def _remember_normal_size(self):
        parent = self.parentWidget()
        width, height = self.width(), self.height()
        if parent is not None and parent.width() >= 320 and parent.height() >= 240:
            width = min(width, parent.width())
            height = min(height, parent.height())
        self._restored_size = (width, height)
        if width != self.width() or height != self.height():
            self._in_size_adjust = True
            self.resize(width, height)
            self._in_size_adjust = False

    def _apply_restored_size(self):
        if not self._restored_size:
            self._fit_inside_parent()
            return
        width, height = self._restored_size
        self._in_size_adjust = True
        self.resize(width, height)
        self._in_size_adjust = False

    def _fit_inside_parent(self):
        """Keep the restored review window inside the main window. Maximize can still fill the screen."""
        if self.isMaximized() or self.isFullScreen():
            return
        self.setMaximumSize(16777215, 16777215)
        parent = self.parentWidget()
        if parent is None:
            return
        limit_w = parent.width()
        limit_h = parent.height()
        if limit_w < 320 or limit_h < 240:
            return
        self._parent_size_limit = (limit_w, limit_h)
        self.setMinimumSize(min(self.minimumWidth(), limit_w), min(self.minimumHeight(), limit_h))
        width = min(self._restored_size[0] if self._restored_size else self.width(), limit_w)
        height = min(self._restored_size[1] if self._restored_size else self.height(), limit_h)
        self._restored_size = (width, height)
        if self.width() != width or self.height() != height:
            self._in_size_adjust = True
            self.resize(width, height)
            self._in_size_adjust = False

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

    def _build_access_menu(self):
        """Review toolbar menus for viewing and navigating defects, dice, and reticles."""
        bar = QMenuBar(self)
        bar.setStyleSheet(
            "QMenuBar { background: #d7d4c9; }"
            "QMenuBar::item { padding: 4px 12px; background: transparent; }"
            "QMenuBar::item:selected { background: #dbe6f9; }"
        )
        file_menu = bar.addMenu("File")
        file_menu.addAction("Print View", self._print_view)
        file_menu.addAction("FileAdmin Utility", lambda: self._call_parent("open_file_admin_utility"))

        edit_menu = bar.addMenu("Edit")
        edit_menu.addAction("Mark Current Defects", self._toggle_mark)
        edit_menu.addAction("Mark Selected Defects", lambda: self._mark_selected(True))
        edit_menu.addAction("Select All", self._select_all_visible)

        optics_menu = bar.addMenu("Optics")
        for label, callback in (
            ("Increase Mag", lambda: self._step_pixel_size(1)),
            ("Decrease Mag", lambda: self._step_pixel_size(-1)),
            ("Increase Light", lambda: self._step_spin(self.review_light, 1)),
            ("Decrease Light", lambda: self._step_spin(self.review_light, -1)),
            ("Increase Focus", lambda: self._step_spin(self.review_focus, 1)),
            ("Decrease Focus", lambda: self._step_spin(self.review_focus, -1)),
            ("Increase Aperture", lambda: self._step_spin(self.review_aperture, 1)),
            ("Decrease Aperture", lambda: self._step_spin(self.review_aperture, -1)),
        ):
            optics_menu.addAction(label, callback)

        if self.snapshot_mode:
            menu = bar.addMenu("Snapshot Review")
            update = menu.addAction("Update Snapshot")
            update.triggered.connect(self._update_snapshot)
            self.snapshot_update_action = update
            menu.addAction("Adjust Defect...", lambda _checked=False: self._adjust_offset(False))
            menu.addAction("Optics Selector...", self._optics_selector)
        else:
            menu = bar.addMenu("Review")
            menu.addAction("Import KLARF", self._menu_import_klarf)
            menu.addAction("Adjust Defect Location...", lambda _checked=False: self._adjust_offset(False))
            menu.addAction("Adjust Die Origin...", lambda _checked=False: self._adjust_offset(True))
            menu.addAction("Optics Selector...", self._optics_selector)
        self.sensitivity_menu_action = menu.addAction("Sensitivity Tuner...", self._sensitivity_tuner)
        navigate = menu.addMenu("Navigate")
        for label, callback in (
            ("Previous Defect", lambda: self._navigate(-1)),
            ("Next Defect", lambda: self._navigate(1)),
            ("Previous Die", lambda: self._navigate_group("die", -1)),
            ("Next Die", lambda: self._navigate_group("die", 1)),
            ("Previous Reticle", lambda: self._navigate_group("reticle", -1)),
            ("Next Reticle", lambda: self._navigate_group("reticle", 1)),
            ("Previous Marked Location", lambda: self._navigate_marked(-1)),
            ("Next Marked Location", lambda: self._navigate_marked(1)),
        ):
            navigate.addAction(label, callback)
        grab = menu.addMenu("Grab Image")
        grab.addAction("Marked", lambda: self._quick_grab("Marked"))
        grab.addAction("Current Defects Current Optics", lambda: self._quick_grab("Current Review Optics"))
        grab.addAction("Current Defects Test Optics", lambda: self._quick_grab("Inspection Test Optics"))
        menu.addAction("Results Utility", self._results_utility)
        self.access_menu = menu

        view_menu = bar.addMenu("View")
        view_menu.addAction("Camera Image", lambda: self._call_parent("open_image_display"))
        logs = view_menu.addMenu("Logs")
        logs.addAction("Run Logs", lambda: self._call_parent("open_system_log", "run"))
        logs.addAction("Daily Logs", lambda: self._call_parent("open_system_log", "daily"))
        logs.addAction("Recipe History", lambda: self._call_parent("open_system_log", "recipe"))

        tools_menu = bar.addMenu("Tools")
        tools_menu.addAction("Wafer Handling", lambda: self._call_parent("open_wafer_handling"))
        tools_menu.addAction("System Security", lambda: self._call_parent("open_user_administration"))
        tools_menu.addAction("Log Settings", lambda: self._call_parent("open_log_settings"))
        tools_menu.addAction("Current User", self._show_current_user)
        tools_menu.addAction("Disk Admin", lambda: self._call_parent("open_disk_admin"))
        transfer = tools_menu.addMenu("Data Transfer")
        transfer.addAction("Transfer Settings", lambda: self._call_parent("open_transfer_configuration"))
        transfer.addAction("Transfer Queue", lambda: self._call_parent("open_transfer_queue"))
        transfer.addAction("Export KLARF", self._export)
        tools_menu.addAction("Analysis Toolbox", self._analysis)
        tools_menu.addAction("SECS", lambda: self._call_parent("open_secs_operations"))
        tools_menu.addAction("User Preferences", lambda: self._call_parent("open_user_preferences"))

        help_menu = bar.addMenu("Help")
        help_menu.addAction("User Manual", lambda: self._call_parent("open_user_manual"))
        help_menu.addAction("About", self._show_about)
        return bar

    def _call_parent(self, name, *args):
        parent = self.parent()
        method = getattr(parent, name, None) if parent is not None else None
        if method is None:
            self.status.setText(f"{name.replace('_', ' ')} is available from the main window.")
            return
        method(*args)

    def _show_about(self):
        QMessageBox.information(
            self,
            "About",
            "Puma 9980\nWafer Inspection Review",
        )

    def _show_current_user(self):
        parent = self.parent()
        security = {}
        if parent is not None and hasattr(parent, "_system_admin_state"):
            security = parent._system_admin_state().get("security") or {}
        if not security.get("enabled"):
            self.status.setText("Current User is displayed only when security is enabled.")
            return
        QMessageBox.information(
            self,
            "Current User",
            f"Current User: {security.get('current_user') or '(none)'}",
        )

    def _print_view(self):
        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() != QDialog.Accepted:
            return
        painter = QPainter(printer)
        snapshot = self.grab()
        target = painter.viewport()
        scaled = snapshot.scaled(target.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        painter.drawPixmap(target.x(), target.y(), scaled)
        painter.end()
        self.status.setText("Print View sent the review screen to the printer.")

    def _choose_lot(self, _checked=False):
        if self.store is None:
            self.status.setText("Select Lot requires a result store.")
            return
        dialog = SelectLotResultsDialog(self.store, self.current_recipe, self)
        if _exec(dialog) != QDialog.Accepted or dialog.selected_result is None:
            return
        self._load_result(dialog.selected_result)

    def _load_result(self, result):
        self.result = deepcopy(result)
        self.available_grid_columns = _review_grid_columns(self.result)
        self.grid_columns = _initial_review_grid_columns(self.result, self.available_grid_columns)
        self.filters = default_filter_state()
        self.selected_id = None
        self.selected_ids.clear()
        for combo, key in (
            (getattr(self, "grid_configuration", None), "review_grid_configs"),
            (getattr(self, "chart_configuration", None), "review_chart_configs"),
        ):
            if combo is None:
                continue
            combo.blockSignals(True)
            combo.clear()
            combo.addItems(["Default"] + sorted((self.result.get(key) or {}).keys()))
            combo.blockSignals(False)
        self._review_lot_ready = True
        self._sync_released_columns()
        self._apply_grid_headers()
        self._refresh_snapshot_controls()
        self._refresh_defects()

    def _menu_import_klarf(self, _checked=False):
        parent = self.parent()
        if parent is not None and hasattr(parent, "import_review_klarf"):
            self.accept()
            parent.import_review_klarf()

    def _optics_icon(self, kind: str) -> QIcon:
        key = "optics_" + str(kind).replace("-", "_")
        return vector_icon(key, 28)

    def _set_optics_button_face(self, button: QPushButton, kind: str):
        icon = self._optics_icon(kind)
        button.setIcon(icon)
        sizes = icon.availableSizes()
        if sizes:
            button.setIconSize(sizes[0])
            button.setFixedSize(sizes[0].width(), sizes[0].height())

    def _optics_toolbar(self):
        """Review Optics Toolbar across the top of the review screen."""
        bar = QWidget()
        layout = QVBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        optics = QHBoxLayout()
        optics.setSpacing(4)
        self.optics_engaged = True
        self.light_automatic = True
        self._brightfield_aperture = 20
        self._focus_step = 1.0
        self.optics_engage_button = QPushButton()
        self.optics_engage_button.setCheckable(True)
        self.optics_engage_button.setChecked(True)
        self._set_optics_button_face(self.optics_engage_button, "engaged")
        self.optics_engage_button.setToolTip(
            "Optics Engaged. Changes apply to the machine state immediately."
        )
        self.optics_engage_button.toggled.connect(self._set_optics_engaged)
        self.apply_optics_button = QPushButton()
        self._set_optics_button_face(self.apply_optics_button, "apply")
        self.apply_optics_button.setToolTip("Apply Optics Settings")
        self.apply_optics_button.setEnabled(False)
        self.apply_optics_button.clicked.connect(self._apply_optics_settings)
        self.review_pixel_size = QComboBox()
        self.review_pixel_size.addItems(["2.000 (5X)", "1.000 (10X)", "0.500 (20X)", "0.250 (40X)"])
        self.review_pixel_size.setCurrentText("1.000 (10X)")
        self.review_pixel_size.setToolTip("Pixel Size")
        self.review_pixel_size.currentTextChanged.connect(lambda _text: self._stage_optics("Pixel Size"))
        self.review_imaging_mode = QComboBox()
        self.review_imaging_mode.addItems(["BrightField", "DarkField"])
        self.review_imaging_mode.setToolTip(
            "Imaging Mode. DarkField sets Aperture to 100 and disables it."
        )
        self.review_imaging_mode.currentTextChanged.connect(self._imaging_mode_changed)
        self.review_aperture = QSpinBox()
        self.review_aperture.setRange(0, 100)
        self.review_aperture.setSuffix(" %")
        self.review_aperture.setValue(20)
        self.review_aperture.setToolTip("Aperture")
        self.review_aperture.valueChanged.connect(lambda _value: self._stage_optics("Aperture"))
        self.light_mode_button = QPushButton()
        self._set_optics_button_face(self.light_mode_button, "light-auto")
        self.light_mode_button.setToolTip("Light Level Automatic")
        self.light_mode_button.clicked.connect(self._toggle_light_mode)
        self.review_light = QSpinBox()
        self.review_light.setRange(0, 255)
        self.review_light.setValue(100)
        self.review_light.setEnabled(False)
        self.review_light.setToolTip("Light Level")
        self.review_light.valueChanged.connect(lambda _value: self._stage_optics("Light Level"))
        self.review_focus = QDoubleSpinBox()
        self.review_focus.setRange(-50.0, 50.0)
        self.review_focus.setDecimals(3)
        self.review_focus.setSingleStep(0.001)
        self.review_focus.setSuffix(" μm")
        self.review_focus.setValue(0.0)
        self.review_focus.setToolTip("Focus Offset")
        self.review_focus.valueChanged.connect(lambda _value: self._stage_optics("Focus Offset"))
        self.advanced_optics_button = QPushButton()
        self._set_optics_button_face(self.advanced_optics_button, "advanced")
        self.advanced_optics_button.setToolTip("Advanced Review Optics Settings")
        self.advanced_optics_button.clicked.connect(self._open_advanced_review_optics)
        self.sizing_ruler_button = QPushButton()
        self.sizing_ruler_button.setCheckable(True)
        self._set_optics_button_face(self.sizing_ruler_button, "ruler")
        self.sizing_ruler_button.setToolTip("Sizing Ruler")
        self.sizing_ruler_button.toggled.connect(self._toggle_sizing_ruler)
        icon_style = (
            "QPushButton { background: transparent; border: none; padding: 0; }"
            "QPushButton:disabled { background: transparent; }"
        )
        for button in (
            self.optics_engage_button,
            self.apply_optics_button,
            self.light_mode_button,
            self.advanced_optics_button,
            self.sizing_ruler_button,
        ):
            button.setStyleSheet(icon_style)
        optics.addWidget(self.optics_engage_button)
        optics.addWidget(self.apply_optics_button)
        optics.addWidget(self._optics_badge("pixel"))
        optics.addWidget(self.review_pixel_size)
        optics.addWidget(self._optics_badge("imaging"))
        optics.addWidget(self.review_imaging_mode)
        optics.addWidget(self._optics_badge("aperture"))
        optics.addWidget(self.review_aperture)
        optics.addWidget(self.light_mode_button)
        optics.addWidget(self.review_light)
        optics.addWidget(self._optics_badge("focus"))
        optics.addWidget(self.review_focus)
        optics.addWidget(self.advanced_optics_button)
        optics.addWidget(self.sizing_ruler_button)
        optics.addStretch(1)
        layout.addLayout(optics)
        return bar

    def _optics_badge(self, kind: str) -> QLabel:
        icon = self._optics_icon(kind)
        badge = QLabel()
        sizes = icon.availableSizes()
        if sizes:
            badge.setPixmap(icon.pixmap(sizes[0]))
            badge.setFixedSize(sizes[0])
        return badge

    def _command_rail(self):
        """Left command column, using the same buttons as the Setup navigation."""
        rail = QFrame()
        rail.setObjectName("reviewRail")
        rail.setFixedWidth(148)
        rail.setStyleSheet(
            """
            QFrame#reviewRail {
                background: #cfcbc2;
                border-right: 2px solid #77746c;
            }
            """
        )
        layout = QVBoxLayout(rail)
        self.review_rail_layout = layout
        layout.setContentsMargins(8, 14, 6, 12)
        layout.setSpacing(8)
        if self.snapshot_mode:
            commands = (
                ("Update\nSnapshot", self._update_snapshot, False, False, "Update Snapshot"),
                ("Sensitivity Tuner", self._sensitivity_tuner, False, False, "Sensitivity Tuner"),
                (
                    "Adjust Defect",
                    lambda _checked=False: self._adjust_offset(False),
                    True,
                    False,
                    "Adjust Defect",
                ),
                ("Optics Selector", self._optics_selector, True, True, "Optics Selector"),
            )
            gated = {"Sensitivity Tuner", "Adjust Defect", "Optics Selector"}
        else:
            commands = (
                ("Select Lot", self._choose_lot, False, False, "Select Lot"),
                ("Import KLARF", self._menu_import_klarf, False, False, "Import KLARF"),
                (
                    "Adjust Defect\nLocation",
                    lambda _checked=False: self._adjust_offset(False),
                    True,
                    False,
                    "Adjust Defect Location",
                ),
                (
                    "Adjust Die\nOrigin",
                    lambda _checked=False: self._adjust_offset(True),
                    True,
                    False,
                    "Adjust Die Origin",
                ),
                ("Optics Selector", self._optics_selector, True, True, "Optics Selector"),
                ("Sensitivity Tuner", self._sensitivity_tuner, False, False, "Sensitivity Tuner"),
            )
            gated = {
                "Adjust Defect\nLocation",
                "Adjust Die\nOrigin",
                "Optics Selector",
                "Sensitivity Tuner",
            }
        self.review_rail_buttons = []
        self.lot_gated_rail_buttons = []
        for text, callback, _machine_free, arrow, tooltip in commands:
            button = ClassicButton(text)
            button.setFocusPolicy(Qt.NoFocus)
            button.setToolTip(tooltip)
            button.clicked.connect(callback)
            self.review_rail_buttons.append(button)
            if text in gated:
                self.lot_gated_rail_buttons.append(button)
                button.setEnabled(False)
            if text == "Sensitivity Tuner":
                self.command_sensitivity_button = button
                self.sensitivity_tuner_button = button
            if text == "Update\nSnapshot":
                self.snapshot_rail_update = button
            layout.addWidget(SubmenuButtonRow(button, arrow))
        layout.addStretch(1)
        end = ClassicButton("End")
        end.setFixedHeight(40)
        end.setFocusPolicy(Qt.NoFocus)
        end.setToolTip("End")
        end.clicked.connect(self.accept)
        layout.addWidget(SubmenuButtonRow(end))
        return rail

    def _set_optics_engaged(self, engaged):
        self.optics_engaged = bool(engaged)
        self.apply_optics_button.setEnabled(not self.optics_engaged)
        self._set_optics_button_face(
            self.optics_engage_button,
            "engaged" if self.optics_engaged else "disengaged",
        )
        self.optics_engage_button.setToolTip(
            "Optics Engaged. Changes apply to the machine state immediately."
            if self.optics_engaged
            else "Optics Disengaged. Click Apply Optics Settings to change the machine state."
        )

    def _toggle_light_mode(self):
        self.light_automatic = not self.light_automatic
        self.review_light.setEnabled(not self.light_automatic)
        self._set_optics_button_face(
            self.light_mode_button,
            "light-auto" if self.light_automatic else "light",
        )
        self.light_mode_button.setToolTip(
            "Light Level Automatic" if self.light_automatic else "Light Level Manual"
        )
        self._stage_optics("Light Level")

    def _imaging_mode_changed(self, mode):
        if mode == "DarkField":
            if self.review_aperture.isEnabled():
                self._brightfield_aperture = self.review_aperture.value()
            self.review_aperture.setEnabled(False)
            if self.review_aperture.value() != 100:
                self.review_aperture.setValue(100)
        else:
            self.review_aperture.setEnabled(True)
            if self.review_aperture.value() != self._brightfield_aperture:
                self.review_aperture.setValue(self._brightfield_aperture)
        self._stage_optics("Imaging Mode")

    def _stage_optics(self, label):
        if not hasattr(self, "review_pixel_size"):
            return
        values = {
            "pixel_size": self.review_pixel_size.currentText(),
            "imaging_mode": self.review_imaging_mode.currentText(),
            "aperture": self.review_aperture.value(),
            "light_level": self.review_light.value(),
            "light_automatic": self.light_automatic,
            "focus_offset": self.review_focus.value(),
            "focus_step": getattr(self, "_focus_step", 1.0),
            "optics_engaged": self.optics_engaged,
        }
        if self.optics_engaged:
            self.review_optics_state.update(values)
            message = f"{label} applied."
        else:
            self._pending_optics = values
            message = f"{label} is pending. Click Apply Optics Settings."
        if hasattr(self, "status"):
            self.status.setText(message)

    def _apply_optics_settings(self):
        self.review_optics_state.update(self._optics_form_values())
        self._pending_optics = None
        self.status.setText("Optics settings applied.")

    def _optics_form_values(self):
        return {
            "pixel_size": self.review_pixel_size.currentText(),
            "imaging_mode": self.review_imaging_mode.currentText(),
            "aperture": self.review_aperture.value(),
            "light_level": self.review_light.value(),
            "light_automatic": self.light_automatic,
            "focus_offset": self.review_focus.value(),
            "focus_step": getattr(self, "_focus_step", 1.0),
            "optics_engaged": self.optics_engaged,
        }

    def _step_pixel_size(self, direction):
        index = self.review_pixel_size.currentIndex() + direction
        index = max(0, min(self.review_pixel_size.count() - 1, index))
        self.review_pixel_size.setCurrentIndex(index)

    def _step_spin(self, spin, direction):
        if not spin.isEnabled():
            self.status.setText("That optics control is disabled in the current mode.")
            return
        if direction > 0:
            spin.stepUp()
        else:
            spin.stepDown()

    def _toggle_sizing_ruler(self, checked):
        for widget in getattr(self, "image_widgets", []):
            widget.show_ruler = bool(checked)
            widget.update()

    def _open_advanced_review_optics(self):
        if not hasattr(self, "review_optics_files"):
            self.review_optics_files = default_review_optics_files()
        dialog = AdvancedReviewOpticsSettingsDialog(
            self._optics_form_values(),
            self.review_optics_files,
            self,
            on_apply=self._install_optics_values,
        )
        _exec(dialog)

    def _install_optics_values(self, values: dict):
        pixel = str(values.get("pixel_size") or "")
        if pixel and self.review_pixel_size.findText(pixel) < 0:
            self.review_pixel_size.addItem(pixel)
        if pixel:
            self.review_pixel_size.setCurrentText(pixel)
        self.light_automatic = bool(values.get("light_automatic", True))
        self.review_light.setEnabled(not self.light_automatic)
        self._set_optics_button_face(
            self.light_mode_button,
            "light-auto" if self.light_automatic else "light",
        )
        self.light_mode_button.setToolTip(
            "Light Level Automatic" if self.light_automatic else "Light Level Manual"
        )
        self.review_light.setValue(int(values.get("light_level", self.review_light.value())))
        step = max(0.001, float(values.get("focus_step", getattr(self, "_focus_step", 1.0)) or 1.0))
        self._focus_step = step
        self.review_focus.setSingleStep(step)
        self.review_focus.setValue(float(values.get("focus_offset", self.review_focus.value())))
        mode = str(values.get("imaging_mode") or "BrightField")
        aperture = int(values.get("aperture", self.review_aperture.value()))
        if mode != "DarkField":
            self._brightfield_aperture = aperture
        if mode in ("BrightField", "DarkField"):
            self.review_imaging_mode.setCurrentText(mode)
        if self.review_imaging_mode.currentText() != "DarkField":
            self.review_aperture.setValue(aperture)
        self.review_optics_state["focus_step"] = step

    def _update_active_filter_label(self):
        if not hasattr(self, "active_filter_label"):
            return
        filters = self.filters or {}
        include = [item for item in (filters.get("include_ids") or []) if item != -1]
        exclude = list(filters.get("exclude_ids") or [])
        name = "None"
        if include:
            name = "In"
        elif exclude or filters.get("include_ids") == [-1]:
            name = "Out"
        elif (
            filters.get("marked_only")
            or filters.get("tests")
            or filters.get("class_codes")
            or filters.get("advanced_expression")
        ):
            name = "Custom"
        elif filters.get("image_filter") not in (None, "", "All Defects"):
            name = str(filters.get("image_filter"))
        self.active_filter_label.setText(name)

    def _review_icon(self, kind: str) -> QIcon:
        return vector_icon("review_" + str(kind).replace("-", "_"), 28)

    def _icon_button(self, text: str, tooltip: str, kind: str, callback, width: int = 30) -> QPushButton:
        button = _IconCommandButton(text)
        icon = self._review_icon(kind)
        button.setIcon(icon)
        button.setToolTip(tooltip)
        sizes = icon.availableSizes()
        if sizes:
            button.setIconSize(sizes[0])
            button.setFixedSize(sizes[0].width(), sizes[0].height())
        else:
            button.setFixedSize(width, 28)
        button.setStyleSheet(
            "QPushButton { background: transparent; color: transparent; border: none;"
            " padding: 0; min-width: 0; min-height: 0; }"
            "QPushButton::menu-indicator { image: none; width: 0px; }"
            "QPushButton:disabled { background: transparent; }"
        )
        button.clicked.connect(callback)
        return button

    def _toolbar(self):
        toolbar = QVBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(0)
        self.review_toolbar_layout = toolbar
        row_widget = QWidget()
        row = QHBoxLayout(row_widget)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)

        self.image_filter = QComboBox(row_widget)
        self.image_filter.addItems([
            "All Defects", "With Any Image", "With Patch Images", "With SEM Images",
            "With Manual Images", "Without Images",
        ])
        self.image_filter.currentTextChanged.connect(self._set_image_filter)
        self.image_filter.hide()
        self.selection_mode = QComboBox(row_widget)
        self.selection_mode.addItems([
            "Select Defect(s)", "Select Die(s)", "Select Reticle(s)",
            "Deselect Defect(s)", "Deselect Die(s)", "Deselect Reticle(s)",
        ])
        self.selection_mode.setToolTip(
            "Select: choose Select Defect(s), Select Die(s), Select Reticle(s), "
            "or a Deselect mode. The wafer-map cursor changes with the mode."
        )

        commands = QWidget()
        command_row = QHBoxLayout(commands)
        command_row.setContentsMargins(0, 0, 0, 0)
        command_row.setSpacing(4)
        command_row.addWidget(self._icon_button(
            "Clear Selection",
            "Clear All Selected Defects: deselects all selected defects.",
            "clear",
            self._clear_selection,
        ))
        command_row.addWidget(self._icon_button(
            "Select Current",
            "Select Current Defect: toggles selection of the defect currently being viewed.",
            "select",
            self._select_current,
        ))
        mark = self._icon_button(
            "Mark Selected",
            "Mark Selected Defects: marks all selected defects.",
            "mark",
            lambda _checked=False: self._mark_selected(True),
            width=24,
        )
        mark_group = QWidget()
        mark_layout = QHBoxLayout(mark_group)
        mark_layout.setContentsMargins(0, 0, 0, 0)
        mark_layout.setSpacing(0)
        mark_layout.addWidget(mark)
        menu = QMenu(mark)
        menu.addAction("Mark Selected Defects", lambda: self._mark_selected(True))
        menu.addAction("Clear Marks For Selected Defects", lambda: self._mark_selected(False))
        menu.addAction("Sample Marked Defects", self._sample_marked)
        menu.addAction("Clear Marked Defects", self._clear_all_marks)
        # The dropdown lives on its own caret so clicking the face always marks
        # the selection instead of tearing a popup open.
        caret = QToolButton(mark_group)
        caret.setPopupMode(QToolButton.InstantPopup)
        caret.setMenu(menu)
        caret.setArrowType(Qt.DownArrow)
        caret.setAutoRaise(True)
        caret.setFixedSize(14, 24)
        caret.setFocusPolicy(Qt.NoFocus)
        caret.setToolTip("Mark Options: open the mark and sampling menu.")
        mark_layout.addWidget(caret)
        sample = QPushButton("Sample Marked")
        sample.setFixedSize(1, 28)
        sample.setStyleSheet(
            "QPushButton { background: transparent; color: transparent; border: none; padding: 0; }"
        )
        sample.setToolTip("Sample Marked Defects: applies the cluster/sampling flag to all selected defects.")
        sample.clicked.connect(self._sample_marked)
        self.complete_data_controls.append(sample)
        mark_layout.addWidget(sample)
        command_row.addWidget(mark_group)
        analysis = self._icon_button(
            "Analysis Toolbox...",
            "Open Analysis Toolbox: opens the Defect Analysis Toolbox.",
            "analysis",
            self._analysis,
        )
        self.complete_data_controls.append(analysis)
        command_row.addWidget(analysis)
        command_row.addWidget(self._icon_button(
            "",
            "Setup Super Class: bins defects into general groups from their manual class codes.",
            "super",
            self._super_class,
        ))
        for text, tooltip, kind, callback in (
            ("", "Filter In: displays only the selected defects in the Defect Grid.", "filter-in", self._filter_in),
            ("", "Filter Out: removes the selected defects from the Defect Grid.", "filter-out", self._filter_out),
            ("", "Setup Filter and Analysis: sets up filter and analysis schemes.", "filter-setup", self._filter_analysis),
        ):
            command_row.addWidget(self._icon_button(text, tooltip, kind, callback))
        images = QToolButton()
        image_icon = self._review_icon("images")
        images.setIcon(image_icon)
        image_sizes = image_icon.availableSizes()
        if image_sizes:
            images.setIconSize(image_sizes[0])
            images.setFixedSize(image_sizes[0].width(), image_sizes[0].height())
        else:
            images.setFixedSize(32, 26)
        images.setPopupMode(QToolButton.InstantPopup)
        images.setToolTip(
            "Show Defects With or Without Images: displays defects based on image availability."
        )
        images.setStyleSheet(
            "QToolButton { background: transparent; border: none; padding: 0; }"
            "QToolButton::menu-indicator { image: none; width: 0px; }"
        )
        image_menu = QMenu(images)
        for label, value in (
            ("All Defects", "All Defects"),
            ("Defects With Images", "With Any Image"),
            ("Defects With Patch Images", "With Patch Images"),
            ("Defects With Sem Images", "With SEM Images"),
            ("Defects With Manual Images", "With Manual Images"),
            ("Defects Without Images", "Without Images"),
        ):
            image_menu.addAction(
                label,
                lambda _checked=False, mode=value: self._apply_image_filter(mode),
            )
        images.setMenu(image_menu)
        command_row.addWidget(images)
        command_row.addWidget(self._icon_button(
            "",
            "Reset Filter: restores all defects to the Defect Grid.",
            "filter-reset",
            self._reset_filter,
        ))
        command_row.addSpacing(8)
        command_row.addWidget(QLabel("Active Filter:"))
        self.active_filter_label = QLabel("None")
        self.active_filter_label.setAlignment(Qt.AlignCenter)
        self.active_filter_label.setFixedSize(54, 28)
        self.active_filter_label.setStyleSheet(
            "background: #6f6f6f; color: #ffffff; border: 1px solid #4a4a4a; padding: 0 8px;"
        )
        self.active_filter_label.setToolTip("Active Filter")
        command_row.addWidget(self.active_filter_label)
        self.review_toolbar_widgets.append(commands)

        transfer = QWidget()
        transfer_row = QHBoxLayout(transfer)
        transfer_row.setContentsMargins(0, 0, 0, 0)
        transfer_row.setSpacing(4)
        send_images = self._icon_button(
            "",
            "Send Current Lot Images: sends the selected defect images to an analysis station or storage.",
            "send-images",
            self._send_images,
        )
        send_wafer = self._icon_button(
            "",
            "Send Current Wafer: sends the current wafer results to an analysis system and storage.",
            "send-wafer",
            self._send_wafer,
        )
        send_lot = self._icon_button(
            "Send Lot Results",
            "Send Current Lot: sends the current lot results file to an analysis system and storage.",
            "send-lot",
            self._send_lot,
        )
        for button in (send_images, send_wafer, send_lot):
            self.complete_data_controls.append(button)
            transfer_row.addWidget(button)
        grab = self._icon_button(
            "",
            "Grab Camera Image: opens the Image Grab dialog. Available when a wafer is loaded.",
            "camera",
            self._grab_image,
        )
        self.machine_free_controls.append(grab)
        transfer_row.addWidget(grab)
        self.update_snapshot = QPushButton("Update Snapshot")
        self.update_snapshot.setToolTip("Update Snapshot")
        self.update_snapshot.clicked.connect(self._update_snapshot)
        self.update_snapshot.setVisible(self.snapshot_mode)
        transfer_row.addWidget(self.update_snapshot)
        self.review_image_toolbar_widgets.append(transfer)

        status = QWidget()
        status_row = QHBoxLayout(status)
        status_row.setContentsMargins(0, 0, 0, 0)
        status_row.setSpacing(6)
        status_row.addWidget(QLabel("RICO Status:"))
        offline = QLabel("Offline")
        offline.setStyleSheet("font-weight: 700; background: transparent; border: none; padding: 0 2px;")
        status_row.addWidget(offline)
        self.rico_status = QComboBox()
        self.rico_status.setIconSize(self._rico_swatch_icon().availableSizes()[0])
        self.rico_status.addItem(self._rico_swatch_icon(), "")
        self.rico_status.setFixedSize(42, 28)
        self.rico_status.setToolTip("RICO Status")
        status_row.addWidget(self.rico_status)
        status_row.addWidget(self._toolbar_separator())
        layout_box = QFrame()
        layout_box.setFixedHeight(28)
        layout_box.setStyleSheet(
            "QFrame { background: #e6e1d6; border: 1px solid #b7b2a6; }"
            "QLabel { background: #e6e1d6; border: none; padding: 0 8px; color: #222222; }"
            "QComboBox { background: #ffffff; border: none; min-width: 88px; padding: 0 6px; }"
        )
        layout_row = QHBoxLayout(layout_box)
        layout_row.setContentsMargins(0, 0, 2, 0)
        layout_row.setSpacing(0)
        layout_label = QLabel("Layout")
        layout_label.setToolTip("Layout")
        layout_row.addWidget(layout_label)
        self.layout_mode = QComboBox()
        self.layout_mode.addItems(["Review", "Wide Grid", "Advanced Classify"])
        self.layout_mode.setToolTip("Layout: Review, Wide Grid, or Advanced Classify.")
        self.layout_mode.setFixedHeight(26)
        self.layout_mode.currentTextChanged.connect(self._set_layout)
        layout_row.addWidget(self.layout_mode)
        status_row.addWidget(layout_box)

        row.addWidget(commands)
        row.addWidget(transfer)
        row.addWidget(status)
        row.addStretch(1)
        toolbar.addWidget(row_widget)
        return toolbar

    def _rico_swatch_icon(self) -> QIcon:
        pixmap = QPixmap(22, 16)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        for index, color in enumerate(("#e23b3b", "#2a6adf", "#2f9e3f", "#f08a12")):
            painter.fillRect(1 + index * 5, 2, 4, 12, QColor(color))
        painter.end()
        return QIcon(pixmap)

    def _toolbar_separator(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setFixedWidth(8)
        line.setStyleSheet("color: #8a8680;")
        return line

    def set_review_toolbar_visible(self, visible):
        for widget in self.review_toolbar_widgets:
            widget.setVisible(bool(visible))

    def set_review_image_toolbar_visible(self, visible):
        for widget in self.review_image_toolbar_widgets:
            widget.setVisible(bool(visible))

    def _set_layout(self, mode):
        if not hasattr(self, "pane_splitter"):
            return
        layouts = {
            "Review": ("review", 0.55, 0.53),
            "Wide Grid": ("wide", 0.46, 0.56),
            "Advanced Classify": ("classify", 0.58, 0.56),
        }
        arrangement, split_x, split_y = layouts.get(mode, layouts["Review"])
        self.pane_splitter.arrangement = arrangement
        self.pane_splitter.set_ratios(split_x, split_y)
        if hasattr(self, "advanced_frame"):
            self._apply_gallery_presentation(mode)
            self._refresh_advanced_classify()
        if hasattr(self, "grid"):
            self._refresh_defects(self.selected_id)

    def _status_bar(self):
        bar = QFrame()
        bar.setObjectName("reviewStatus")
        bar.setStyleSheet(
            "QFrame#reviewStatus { background: #e6e2d4; border-top: 1px solid #6e6a62; }"
            "QFrame#reviewStatus QLabel { background: #f4f1e6; border: 1px solid #8d897f; padding: 2px 8px; }"
        )
        row = QHBoxLayout(bar)
        row.setContentsMargins(4, 3, 6, 3)
        row.setSpacing(6)
        self.status = ReviewStatusLabel()
        self.status.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        row.addWidget(self.status, 1)
        self.orientation_icon = _ReviewStatusIcon("orientation")
        self.orientation_icon.setToolTip("Wafer Orientation")
        self.ilink_icon = _ReviewStatusIcon("ilink")
        self.ilink_icon.setToolTip("iLink Status")
        self.coordinate_icon = _ReviewStatusIcon("coordinate", on_click=self._toggle_coordinate_mode)
        self.coordinate_icon.setToolTip("Coordinate System: Wafer")
        row.addWidget(self.orientation_icon)
        row.addWidget(self.ilink_icon)
        row.addWidget(self.coordinate_icon)
        return bar

    def _toggle_coordinate_mode(self, _event=None):
        self.coordinate_mode = "die" if self.coordinate_mode == "wafer" else "wafer"
        label = "Wafer" if self.coordinate_mode == "wafer" else "In-Die"
        self.coordinate_icon.setToolTip(f"Coordinate System: {label}")
        self._sync_review_status()

    def _wafer_orientation_degrees(self) -> int:
        raw = self.result.get("wafer_orientation")
        if raw is None and self.current_recipe:
            wafer_map = self.current_recipe.get("wafer_map") or {}
            properties = self.current_recipe.get("wafer_properties") or {}
            raw = wafer_map.get("notch_orientation", properties.get("orientation"))
        names = {"up": 0, "right": 90, "down": 180, "left": 270}
        if isinstance(raw, str):
            return names.get(raw.strip().lower(), 180)
        try:
            return int(raw) % 360
        except (TypeError, ValueError):
            return 180

    def _defect_coordinates(self, defect):
        if not defect:
            return 0.0, 0.0
        if self.coordinate_mode == "wafer" and defect.get("x_um") is not None:
            return float(defect.get("x_um") or 0.0), float(defect.get("y_um") or 0.0)
        if self.coordinate_mode != "wafer" and defect.get("xrel") is not None:
            return float(defect.get("xrel") or 0.0), float(defect.get("yrel") or 0.0)
        x = float(defect.get("x", 0.0) or 0.0)
        y = float(defect.get("y", 0.0) or 0.0)
        normalized = abs(x) <= 2 and abs(y) <= 2
        diameter = float(self.result.get("wafer_diameter_mm") or 300.0)
        radius = diameter * 500.0
        if self.coordinate_mode == "wafer":
            if normalized:
                return x * radius, y * radius
            return x, y
        pitch = 5000.0
        if self.current_recipe:
            wafer_map = self.current_recipe.get("wafer_map") or {}
            pitch = float(wafer_map.get("die_pitch_width") or pitch)
        if normalized:
            return (x * radius) % pitch, (y * radius) % pitch
        return x % pitch, y % pitch

    def _sync_review_status(self):
        if not hasattr(self, "status"):
            return
        summary = review_summary(self.result, self.visible_defects)
        marked = sum(bool(item.get("marked")) for item in self.result.get("defects", []))
        recipe_name = (self.current_recipe or {}).get("inspection", self.result.get("inspection", ""))
        defect = next(
            (item for item in self.visible_defects if item.get("id") == self.selected_id),
            None,
        )
        x_value, y_value = self._defect_coordinates(defect)
        self.status.set_summary(
            f"Tot:{summary['total']} Vis:{summary['visible']} "
            f"Sel:{len(self.selected_ids)} Mark:{marked}    "
            f"Inspection:{recipe_name}    "
            f"Lot: {self.result.get('lot_id', '')}    "
            f"X: {x_value:.2f} Y: {y_value:.2f}"
        )
        if hasattr(self, "orientation_icon"):
            self.orientation_icon.orientation = self._wafer_orientation_degrees()
            self.orientation_icon.update()
            online = self.result.get("ilink_online", True)
            self.ilink_icon.online = bool(online)
            self.ilink_icon.setToolTip("iLink Status: Online" if online else "iLink Status: Offline")
            self.ilink_icon.update()

    @staticmethod
    def _pane(title):
        frame = QFrame()
        frame.setObjectName("pane")
        frame.setProperty("paneTitle", title)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(4, 2, 4, 4)
        layout.setSpacing(2)
        return frame, layout

    def _map_pane(self):
        frame, layout = self._pane("Wafer Map")
        row1 = QHBoxLayout()
        row1.setSpacing(3)
        row2 = QHBoxLayout()
        row2.setSpacing(4)
        self.selection_mode.setFixedHeight(22)
        self.selection_mode.currentTextChanged.connect(self._selection_mode_changed)
        self.selection_mode.hide()
        select = self._map_tool_button(
            "map_select.png",
            "Select: choose Defect, Die, or Reticle, then click the feature to select or deselect.",
            lambda: self._set_map_interaction("select"),
            checkable=True,
        )
        select_menu = QMenu(select)
        for mode in (
            "Select Defect(s)", "Select Die(s)", "Select Reticle(s)",
            "Deselect Defect(s)", "Deselect Die(s)", "Deselect Reticle(s)",
        ):
            select_menu.addAction(mode, lambda _checked=False, value=mode: self._choose_map_selection(value))
        select.setMenu(select_menu)
        row1.addWidget(select)
        self.map_select_button = select
        self.map_pan_button = self._map_tool_button(
            "map_pan.png",
            "Pan: drag to reposition the Wafer Map (a middle-button drag pans in any tool).",
            lambda: self._set_map_interaction("pan"),
            checkable=True,
        )
        self.map_zoom_region_button = self._map_tool_button(
            "map_zoom_region.png",
            "Zoom to Region: drag a rectangle to zoom in on that region.",
            lambda: self._set_map_interaction("zoom"),
            checkable=True,
        )
        row1.addWidget(self.map_pan_button)
        row1.addWidget(self.map_zoom_region_button)
        self.map_zoom = QComboBox()
        self.map_zoom.addItems(["50%", "75%", "100%", "150%", "200%", "300%"])
        self.map_zoom.setCurrentText("100%")
        self.map_zoom.setFixedHeight(22)
        self.map_zoom.setToolTip(
            "Select Zoom Factor. 100% is the default map size. "
            "The mouse wheel also zooms around the pointer, and a middle-button drag pans."
        )
        self.map_zoom.currentTextChanged.connect(self._set_map_zoom_percent)
        row1.addWidget(self.map_zoom)
        row1.addWidget(self._map_tool_button(
            "map_fit.png",
            "Zoom to Fit: size the Wafer Map to fit the pane and reset zoom to 100%.",
            self._zoom_map_to_fit,
        ))
        self.map_stack_button = self._map_tool_button(
            "map_stack.png",
            "Stack: stack defects on the selected die so repeaters are easier to see.",
            self._toggle_map_stack,
            checkable=True,
        )
        self.map_legend_button = self._map_tool_button(
            "map_legend.png",
            "Legend: show or hide the color legend.",
            self._toggle_map_legend,
            checkable=True,
        )
        self.show_counts = self._map_tool_button(
            "map_count.png",
            "Defect Count: show or hide the defect count on the wafer.",
            None,
            checkable=True,
        )
        self.show_counts.toggled.connect(self._map_options_changed)
        row1.addWidget(self.map_stack_button)
        row1.addWidget(self.map_legend_button)
        row1.addWidget(self.show_counts)
        row1.addWidget(self._map_tool_button(
            "map_rules.png",
            "Defect Display Rules: define how each defect type is drawn.",
            self._display_rules,
        ))
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFixedWidth(2)
        row1.addWidget(separator)
        row1.addWidget(QLabel("Display"))
        self.map_display = QComboBox()
        self.map_display.addItems(["Wafer Map", "Die Stack", "Reticle Stack"])
        self.map_display.setFixedHeight(22)
        self.map_display.setToolTip("View Wafer Map, Die Stack, or Reticle Stack.")
        self.map_display.currentTextChanged.connect(self._map_display_changed)
        row1.addWidget(self.map_display)
        row1.addWidget(QLabel("Show"))
        self.map_care_button = self._map_tool_button(
            "map_care.png",
            "Show Care Areas: show or hide Care Areas in a contrasting color.",
            self._toggle_care_areas,
            checkable=True,
        )
        self.map_partial_button = self._map_tool_button(
            "map_partial.png",
            "Show Partial Die: draw a circle for the partial die diameter.",
            self._toggle_partial_die,
            checkable=True,
        )
        row1.addWidget(self.map_care_button)
        row1.addWidget(self.map_partial_button)
        row1.addStretch(1)
        row2.addWidget(QLabel("For"))
        self.map_test = QComboBox()
        tests = []
        for defect in self.result.get("defects") or []:
            name = str(defect.get("test") or "")
            if name and name not in tests:
                tests.append(name)
        if not tests:
            tests = ["Test 1"]
        self.map_test.addItems(tests)
        self.map_test.setFixedHeight(22)
        self.map_test.setToolTip("Valid Tests: review data for a test that has defects.")
        self.map_test.currentTextChanged.connect(self._map_test_changed)
        row2.addWidget(self.map_test)
        self.map_primary_to_secondary = self._map_tool_button(
            "map_pd_sd.png",
            "Convert the current die from Primary to Secondary. Enabled only when ST is enabled.",
            self._convert_die_to_secondary,
        )
        self.map_secondary_to_primary = self._map_tool_button(
            "map_sd_pd.png",
            "Convert a Secondary die back to Primary. Enabled only when ST is enabled.",
            self._convert_die_to_primary,
        )
        row2.addWidget(self.map_primary_to_secondary)
        row2.addWidget(self.map_secondary_to_primary)
        row2.addWidget(self._map_tool_button(
            "map_help.png",
            "Keyboard shortcuts for Review.",
            self._show_map_shortcuts,
        ))
        row2.addStretch(1)
        layout.addLayout(row1)
        layout.addLayout(row2)
        self.show_die = QCheckBox("Die", self)
        self.show_die.setChecked(True)
        self.show_die.hide()
        self.show_defects = QCheckBox("Defects", self)
        self.show_defects.setChecked(True)
        self.show_defects.hide()
        self.show_die.toggled.connect(self._map_options_changed)
        self.show_defects.toggled.connect(self._map_options_changed)
        self.wafer_map = WaferDefectMap()
        self.wafer_map.setToolTip(
            "Select a mode from the Select list. Drag a rectangle to select defects, "
            "dies, or reticles. Double-click a defect to select it. "
            "Ctrl+drag or right-drag zooms to a region."
        )
        self.wafer_map.set_display_rules(self.result.get("defect_display_rules"))
        self.wafer_map.on_selected = self._select_id
        self.wafer_map.on_clicked = self._map_clicked
        self.wafer_map.on_select_toggle = self._map_double_clicked
        self.wafer_map.on_area_selected = self._select_area
        self.wafer_map.on_zoom_changed = self._map_zoom_changed
        layout_map = (self.current_recipe or {}).get("wafer_map") or {}
        self.wafer_map.reticle_width = max(1, int(layout_map.get("reticle_width", 1) or 1))
        self.wafer_map.reticle_height = max(1, int(layout_map.get("reticle_height", 1) or 1))
        self.wafer_map.die_pitch_x = float(layout_map.get("die_pitch_width") or 5100.0)
        self.wafer_map.die_pitch_y = float(layout_map.get("die_pitch_height") or 16600.0)
        self._set_map_interaction("select")
        self._selection_mode_changed(self.selection_mode.currentText())
        self.wafer_map.setContextMenuPolicy(Qt.CustomContextMenu)
        self.wafer_map.customContextMenuRequested.connect(self._map_context_menu)
        self.wafer_map.setToolTip(
            "Mouse wheel: zoom around the pointer. Middle-button drag: pan the map."
        )
        layout.addWidget(self.wafer_map, 1)
        self.map_info = QLabel(self)
        self.map_info.hide()
        self.design_details = QLabel(self)
        self.design_details.hide()
        frame.setContextMenuPolicy(Qt.CustomContextMenu)
        frame.customContextMenuRequested.connect(self._map_context_menu)
        return frame

    def _map_tool_button(self, filename, tooltip, callback=None, checkable=False):
        button = QPushButton()
        button.setToolTip(tooltip)
        button.setCheckable(checkable)
        pixmap = vector_pixmap(filename, 22)
        button.setIcon(QIcon(pixmap))
        button.setIconSize(pixmap.size())
        button.setFixedSize(pixmap.width() + 4, pixmap.height() + 4)
        button.setStyleSheet(
            "QPushButton { background: transparent; border: 1px solid transparent; padding: 0; min-height: 0; }"
            "QPushButton:checked { background: #d7e4f8; border: 1px solid #1d4f9c; }"
            "QPushButton::menu-indicator { image: none; width: 0px; }"
        )
        if callback is not None:
            button.clicked.connect(lambda _checked=False, callback=callback: callback())
        return button

    def _choose_map_selection(self, mode):
        self.selection_mode.setCurrentText(mode)
        self._set_map_interaction("select")

    def _set_map_interaction(self, mode):
        self.wafer_map.interaction = mode
        if hasattr(self, "map_select_button"):
            self.map_select_button.setChecked(mode == "select")
            self.map_pan_button.setChecked(mode == "pan")
            self.map_zoom_region_button.setChecked(mode == "zoom")
        if mode == "pan":
            self.wafer_map.setCursor(Qt.OpenHandCursor)
        elif mode == "zoom":
            self.wafer_map.setCursor(Qt.CrossCursor)
        else:
            self._selection_mode_changed(self.selection_mode.currentText())

    def _set_map_zoom_percent(self, text):
        if not text or not hasattr(self, "wafer_map"):
            return
        try:
            factor = float(str(text).rstrip("%")) / 100.0
        except ValueError:
            return
        self.wafer_map.set_zoom(factor)

    def _zoom_map_to_fit(self):
        self.wafer_map.view_center = (0.0, 0.0)
        self.wafer_map.zoom_factor = 1.0
        self.map_zoom.blockSignals(True)
        self.map_zoom.setCurrentText("100%")
        self.map_zoom.blockSignals(False)
        self.wafer_map.update()

    def _map_zoom_changed(self, factor):
        percent = f"{int(round(float(factor) * 100))}%"
        self.map_zoom.setToolTip(
            f"Current zoom {percent}. The mouse wheel zooms around the pointer,"
            " and a middle-button drag pans."
        )
        if self.map_zoom.findText(percent) >= 0:
            self.map_zoom.blockSignals(True)
            self.map_zoom.setCurrentText(percent)
            self.map_zoom.blockSignals(False)

    def _toggle_map_stack(self):
        self.wafer_map.stack_defects = self.map_stack_button.isChecked()
        self.wafer_map.update()

    def _toggle_map_legend(self):
        self.wafer_map.show_legend = self.map_legend_button.isChecked()
        self.wafer_map.update()

    def _mark_map_location(self):
        defect = next((item for item in self.visible_defects if item.get("id") == self.selected_id), None)
        if defect is None:
            self.status.setText("Load a wafer and select a defect before marking a location.")
            return
        self.wafer_map.location_marks.append((float(defect.get("x", 0.0)), float(defect.get("y", 0.0))))
        self.wafer_map.update()
        self.status.setText(f"Marked the current location for defect {defect.get('id')}.")

    def _map_display_changed(self, mode):
        self.wafer_map.display_mode = mode
        self.wafer_map.update()

    def _toggle_care_areas(self):
        self._set_care_areas_visible(self.map_care_button.isChecked())

    def _set_care_areas_visible(self, visible):
        self.wafer_map.show_care_areas = visible
        care, dont_care = self._care_area_rects() if visible else ([], [])
        self.wafer_map.care_rects = care
        self.wafer_map.dont_care_rects = dont_care
        if hasattr(self, "map_care_button"):
            self.map_care_button.blockSignals(True)
            self.map_care_button.setChecked(visible)
            self.map_care_button.blockSignals(False)
        self.wafer_map.update()

    def _care_area_rects(self):
        care, dont_care = [], []
        for test in (self.current_recipe or {}).get("tests") or []:
            for group in (test.get("care_areas") or {}).get("groups") or []:
                name = str(group.get("name") or "")
                kind = str(group.get("type") or group.get("care") or "")
                target = dont_care if "do not" in name.lower() or kind in ("False", "Do Not Care", "DNCA") else care
                for area in group.get("areas") or []:
                    if len(area) >= 4:
                        target.append(area[:4])
        if not care and not dont_care:
            care = [[0.35, 0.35, 0.12, 0.08], [0.52, 0.48, 0.1, 0.1]]
            dont_care = [[0.62, 0.32, 0.10, 0.08]]
        return care, dont_care

    def _toggle_partial_die(self):
        self.wafer_map.show_partial_die = self.map_partial_button.isChecked()
        self.wafer_map.update()

    def _map_test_changed(self, name):
        if not name:
            self.filters.pop("tests", None)
        else:
            self.filters["tests"] = [name]
        self._refresh_defects(self.selected_id)

    def _show_map_shortcuts(self):
        QMessageBox.information(
            self,
            "Wafer Map Shortcuts",
            "F11 / Left: previous defect\n"
            "F12 / Right: next defect\n"
            "F9 / F10: previous / next die\n"
            "Shift+F9 / Shift+F10: previous / next row\n"
            "Shift+F7 / Shift+F8: previous / next reticle\n"
            "Ctrl+L: next marked defect\n"
            "Ctrl+S: select the current defect\n"
            "Ctrl+A: select all visible defects\n"
            "Ctrl+W: Filter In\n"
            "Ctrl+Q: Filter Out\n"
            "Ctrl+R: Reset Filter",
        )

    def _current_die_key(self):
        defect = next((item for item in self.visible_defects if item.get("id") == self.selected_id), None)
        if defect is None:
            return None
        return (int(defect.get("die_x", 0)), int(defect.get("die_y", 0)))

    def _convert_die_to_secondary(self):
        die = self._current_die_key()
        if die is None:
            return
        self.wafer_map.secondary_dies.add(die)
        self.result.setdefault("secondary_dies", [])
        if list(die) not in self.result["secondary_dies"]:
            self.result["secondary_dies"].append(list(die))
        self.wafer_map.update()
        self.status.setText(f"Die {die} converted from Primary to Secondary.")

    def _convert_die_to_primary(self):
        die = self._current_die_key()
        if die is None or die not in self.wafer_map.secondary_dies:
            self.status.setText("Only a die converted to Secondary can be converted back to Primary.")
            return
        self.wafer_map.secondary_dies.discard(die)
        self.result["secondary_dies"] = [
            item for item in self.result.get("secondary_dies", [])
            if tuple(item) != die
        ]
        self.wafer_map.update()
        self.status.setText(f"Die {die} converted from Secondary to Primary.")

    def _map_options_changed(self, *_args):
        self.wafer_map.show_die = self.show_die.isChecked()
        self.wafer_map.show_defects = self.show_defects.isChecked()
        self.wafer_map.show_counts = self.show_counts.isChecked()
        self.wafer_map.update()

    def _display_rules(self):
        def apply_rules(rules, files):
            self.result["defect_display_rules"] = deepcopy(rules)
            self.result["defect_display_rule_files"] = deepcopy(files)
            self.wafer_map.set_display_rules(rules)
            self.wafer_map.update()
            self._save_result()
            self.status.setText("Defect display rules applied.")

        dialog = DefectDisplayRulesDialog(
            self.result.get("defect_display_rules"),
            self,
            files=self.result.get("defect_display_rule_files"),
            on_apply=apply_rules,
        )
        _exec(dialog)

    def _save_wafer_map(self):
        filename, _selected = QFileDialog.getSaveFileName(
            self, "Save Wafer Map", "wafer-map.bmp", "Images (*.bmp *.gif *.jpg)"
        )
        if filename and not self.wafer_map.grab().save(filename):
            QMessageBox.warning(self, "Save Wafer Map", "The wafer map image could not be saved.")

    def _copy_wafer_map(self):
        QApplication.clipboard().setPixmap(self.wafer_map.grab())

    def _print_wafer_map(self):
        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self)
        if _exec(dialog) != QDialog.Accepted:
            return
        painter = QPainter(printer)
        snapshot = self.wafer_map.grab()
        target = painter.viewport()
        scaled = snapshot.scaled(target.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        painter.drawPixmap(target.x(), target.y(), scaled)
        painter.end()
        self.status.setText("Print sent the Wafer Map to the printer.")

    def _gallery_pane(self):
        frame, layout = self._pane("Image Gallery")
        self.attribute_tabs = QTabWidget()
        self.attribute_tabs.setMaximumHeight(28)
        self.attribute_tabs.setDocumentMode(True)
        self.attribute_tabs.currentChanged.connect(self._attribute_tab_changed)
        self.attribute_tabs.hide()
        layout.addWidget(self.attribute_tabs)
        self.classify_group_label = QLabel("UnGrouped")
        self.classify_group_label.hide()
        layout.addWidget(self.classify_group_label)
        self.classify_strip = ClassifyThumbnailStrip()
        self.classify_strip.on_chosen = self._select_id
        strip_scroll = QScrollArea()
        strip_scroll.setWidgetResizable(True)
        strip_scroll.setFrameShape(QFrame.NoFrame)
        strip_scroll.setFixedHeight(96)
        strip_scroll.setWidget(self.classify_strip)
        self.classify_strip_host = strip_scroll
        self.classify_strip_host.hide()
        layout.addWidget(self.classify_strip_host)
        self.advanced_frame = QFrame()
        advanced = QVBoxLayout(self.advanced_frame)
        advanced.setContentsMargins(0, 0, 0, 4)
        advanced.setSpacing(4)
        folders = QHBoxLayout()
        class_side = QVBoxLayout()
        class_row = QHBoxLayout()
        class_row.addWidget(QLabel("Manual Folder List"))
        new_class = QPushButton("New Class")
        new_class.setToolTip("New Class")
        new_class.clicked.connect(self._classify)
        class_row.addWidget(new_class)
        class_row.addStretch(1)
        class_side.addLayout(class_row)
        self.class_folders = QTableWidget(0, 3)
        self.class_folders.setHorizontalHeaderLabels(["Show", "Class Code", "Count"])
        self.class_folders.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.class_folders.verticalHeader().setVisible(False)
        self.class_folders.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.class_folders.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.class_folders.setContextMenuPolicy(Qt.CustomContextMenu)
        self.class_folders.customContextMenuRequested.connect(self._manual_folder_menu)
        self.class_folders.itemChanged.connect(self._advanced_filter_changed)
        self.class_folders.itemSelectionChanged.connect(self._class_folders_selected)
        class_side.addWidget(self.class_folders)
        self.class_icon_host = QWidget()
        self.class_icon_layout = QHBoxLayout(self.class_icon_host)
        self.class_icon_layout.setContentsMargins(0, 0, 0, 0)
        self.class_icon_layout.addStretch(1)
        self.class_icon_scroll = QScrollArea()
        self.class_icon_scroll.setWidgetResizable(True)
        self.class_icon_scroll.setFrameShape(QFrame.NoFrame)
        self.class_icon_scroll.setFixedHeight(108)
        self.class_icon_scroll.setWidget(self.class_icon_host)
        self.class_icon_scroll.setContextMenuPolicy(Qt.CustomContextMenu)
        self.class_icon_scroll.customContextMenuRequested.connect(self._manual_folder_menu)
        class_side.addWidget(self.class_icon_scroll)
        folders.addLayout(class_side, 1)
        attribute_side = QVBoxLayout()
        attribute_row = QHBoxLayout()
        attribute_row.addWidget(QLabel("Attribute Folder List"))
        self.advanced_attribute = QComboBox()
        self.advanced_attribute.setToolTip("Attribute Dropdown List")
        self.advanced_attribute.addItems([
            "Rough Code", "Polarity", "Venn ID", "Super Class", "PWQ Ranking", "PWQ Child Select",
            "Channel", "Test", "Region", "CAG Code",
            "Macro Sig Class", "Macro Sig ID", "Micro Sig Class",
            "DBB Global Bin", "DBC Bin", "DBG Group", "DBB Manual Bin",
        ])
        self.advanced_attribute.currentTextChanged.connect(self._advanced_attribute_changed)
        attribute_row.addWidget(self.advanced_attribute)
        attribute_row.addStretch(1)
        attribute_side.addLayout(attribute_row)
        self.attribute_folders = QTableWidget(0, 3)
        self.attribute_folders.setHorizontalHeaderLabels(["Show", "Attribute", "Count"])
        self.attribute_folders.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.attribute_folders.verticalHeader().setVisible(False)
        self.attribute_folders.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.attribute_folders.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.attribute_folders.setContextMenuPolicy(Qt.CustomContextMenu)
        self.attribute_folders.customContextMenuRequested.connect(self._attribute_folder_menu)
        self.attribute_folders.itemChanged.connect(self._advanced_filter_changed)
        self.attribute_folders.itemSelectionChanged.connect(self._attribute_folders_selected)
        attribute_side.addWidget(self.attribute_folders)
        self.attribute_icon_host = QWidget()
        self.attribute_icon_layout = QHBoxLayout(self.attribute_icon_host)
        self.attribute_icon_layout.setContentsMargins(0, 0, 0, 0)
        self.attribute_icon_layout.addStretch(1)
        self.attribute_icon_scroll = QScrollArea()
        self.attribute_icon_scroll.setWidgetResizable(True)
        self.attribute_icon_scroll.setFrameShape(QFrame.NoFrame)
        self.attribute_icon_scroll.setFixedHeight(108)
        self.attribute_icon_scroll.setWidget(self.attribute_icon_host)
        self.attribute_icon_scroll.setContextMenuPolicy(Qt.CustomContextMenu)
        self.attribute_icon_scroll.customContextMenuRequested.connect(self._attribute_folder_menu)
        attribute_side.addWidget(self.attribute_icon_scroll)
        folders.addLayout(attribute_side, 1)
        advanced.addLayout(folders)
        layout.addWidget(self.advanced_frame)
        self.advanced_frame.setVisible(False)
        self._remember_attribute_tab(self.advanced_attribute.currentText())
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
            "Rough Code": "roughbin",
            "Polarity": "polarity",
            "Venn ID": "venn_id",
            "Super Class": "super_class",
            "PWQ Ranking": "pwq_ranking",
            "PWQ Child Select": "pwq_child_select",
            "Channel": "channel",
            "Test": "test",
            "Region": "region_id",
            "CAG Code": "cag_code",
            "Macro Sig Class": "macro_sig_class",
            "Macro Sig ID": "macro_sig_id",
            "Micro Sig Class": "micro_sig_class",
            "DBB Global Bin": "dbb_global_bin",
            "DBC Bin": "dbc_bin",
            "DBG Group": "dbg_group",
            "DBB Manual Bin": "dbb_manual_bin",
        }[self.advanced_attribute.currentText()]

    def _apply_gallery_presentation(self, mode):
        advanced = mode == "Advanced Classify"
        if hasattr(self, "advanced_frame"):
            self.advanced_frame.setVisible(advanced)
        if hasattr(self, "attribute_tabs"):
            self.attribute_tabs.setVisible(advanced)
        if hasattr(self, "classify_strip_host"):
            self.classify_strip_host.setVisible(advanced)
            self.classify_group_label.setVisible(advanced)
        self._apply_folder_view()

    def _folder_pixmap(self, size: int) -> QPixmap:
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor("#c4a15a"), 1))
        painter.setBrush(QColor("#f0c24b"))
        painter.drawRoundedRect(2, size // 3, size - 4, size - size // 3 - 2, 2, 2)
        painter.drawRoundedRect(2, size // 5, size // 2, size // 5, 2, 2)
        painter.end()
        return pixmap

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def _rebuild_folder_icons(self, layout, table, on_toggle, on_activate):
        self._clear_layout(layout)
        large = self.folder_view == "tiles"
        for row in range(table.rowCount()):
            title = table.item(row, 1).text()
            count = table.item(row, 2).text()
            checked = table.item(row, 0).checkState() == Qt.Checked
            tile = _FolderTile(lambda event, index=row, callback=on_activate: callback(index, event))
            tile.setFixedSize(110 if large else 84, 96 if large else 84)
            column = QVBoxLayout(tile)
            column.setContentsMargins(2, 2, 2, 2)
            column.setSpacing(0)
            box = QCheckBox()
            box.setChecked(checked)
            box.toggled.connect(lambda state, index=row, callback=on_toggle: callback(index, state))
            column.addWidget(box, alignment=Qt.AlignLeft)
            icon = QLabel()
            icon.setPixmap(self._folder_pixmap(52 if large else 40))
            icon.setAlignment(Qt.AlignCenter)
            column.addWidget(icon)
            caption = QLabel(title)
            caption.setAlignment(Qt.AlignCenter)
            column.addWidget(caption)
            total = QLabel(count)
            total.setAlignment(Qt.AlignCenter)
            column.addWidget(total)
            layout.addWidget(tile)
        layout.addStretch(1)

    def _apply_folder_view(self):
        if not hasattr(self, "class_folders"):
            return
        icons = self.folder_view in ("icons", "tiles")
        self.class_folders.setVisible(not icons)
        self.class_icon_scroll.setVisible(icons)
        self.attribute_folders.setVisible(not icons)
        self.attribute_icon_scroll.setVisible(icons)

    def _set_folder_view(self, mode):
        self.folder_view = mode
        self._refresh_advanced_classify()
        self._apply_folder_view()

    def _toggle_table_check(self, table, row, checked):
        item = table.item(row, 0)
        if item is None:
            return
        desired = Qt.Checked if checked else Qt.Unchecked
        if item.checkState() != desired:
            item.setCheckState(desired)

    def _activate_table_row(self, table, row, event):
        modifiers = event.modifiers() if hasattr(event, "modifiers") else Qt.NoModifier
        index = table.model().index(row, 0)
        command = QItemSelectionModel.Rows
        if modifiers & Qt.ControlModifier:
            command |= QItemSelectionModel.Toggle
        else:
            command |= QItemSelectionModel.ClearAndSelect
        table.selectionModel().select(index, command)
        table.setCurrentCell(row, 1)

    def _refresh_advanced_classify(self):
        if not hasattr(self, "class_folders"):
            return
        self._refreshing_folders = True
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
        self._refreshing_folders = True
        self._rebuild_folder_icons(
            self.class_icon_layout,
            self.class_folders,
            lambda row, checked: self._toggle_table_check(self.class_folders, row, checked),
            lambda row, event: self._activate_table_row(self.class_folders, row, event),
        )
        self._rebuild_folder_icons(
            self.attribute_icon_layout,
            self.attribute_folders,
            lambda row, checked: self._toggle_table_check(self.attribute_folders, row, checked),
            lambda row, event: self._activate_table_row(self.attribute_folders, row, event),
        )
        self._refreshing_folders = False
        self._apply_folder_view()

    def _advanced_attribute_changed(self, name):
        self.advanced_attribute_values = None
        self.gallery_attribute_value = None
        self._remember_attribute_tab(name)
        self._refresh_advanced_classify()
        self._refresh_defects(self.selected_id)

    def _remember_attribute_tab(self, name):
        if not name or not hasattr(self, "attribute_tabs"):
            return
        self._loading_tabs = True
        page = self.attribute_tabs.findChild(QWidget, f"attribute_{name}")
        if page is None:
            page = QWidget()
            page.setObjectName(f"attribute_{name}")
            self.attribute_tabs.addTab(page, name)
        index = self.attribute_tabs.indexOf(page)
        if index >= 0:
            self.attribute_tabs.setCurrentIndex(index)
        self._loading_tabs = False

    def _attribute_tab_changed(self, index):
        if index < 0 or getattr(self, "_loading_tabs", False) or not hasattr(self, "advanced_attribute"):
            return
        name = self.attribute_tabs.tabText(index)
        if name and self.advanced_attribute.currentText() != name:
            self.advanced_attribute.setCurrentText(name)

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

    def _set_selected_checks(self, table, checked):
        rows = {index.row() for index in table.selectionModel().selectedRows()}
        if not rows:
            return
        table.blockSignals(True)
        for row in rows:
            table.item(row, 0).setCheckState(Qt.Checked if checked else Qt.Unchecked)
        table.blockSignals(False)
        self._advanced_filter_changed(None)

    def _popup_menu(self, menu, position):
        host = self.sender()
        point = host.mapToGlobal(position) if host is not None and hasattr(host, "mapToGlobal") else position
        menu.exec(point) if hasattr(menu, "exec") else menu.exec_(point)

    def _add_view_menu(self, menu):
        view = menu.addMenu("View")
        view.addAction("Icons", lambda: self._set_folder_view("icons"))
        view.addAction("List", lambda: self._set_folder_view("list"))
        view.addAction("Tiles", lambda: self._set_folder_view("tiles"))
        numerical = menu.addAction("Numerical Text")
        numerical.setEnabled(False)

    def _add_image_type_menu(self, menu):
        image_types = menu.addMenu("Image Types")
        for name in ("Reference Image", "Patch Image", "Difference Image"):
            image_types.addAction(name, lambda _checked=False, value=name: self.gallery_mode.setCurrentText(value))

    def _manual_folder_menu(self, position):
        menu = QMenu(self)
        menu.addAction("New Class", self._classify)
        menu.addAction("Rename", self._rename_class_folder)
        menu.addAction("Delete", self._delete_class_folder)
        menu.addSeparator()
        self._add_view_menu(menu)
        menu.addSeparator()
        menu.addAction("Select All", self.class_folders.selectAll)
        menu.addAction("Deselect All", self.class_folders.clearSelection)
        menu.addSeparator()
        menu.addAction("Check All", lambda: self._set_folder_checks(self.class_folders, True))
        menu.addAction("Uncheck All", lambda: self._set_folder_checks(self.class_folders, False))
        menu.addAction("Check Selected", lambda: self._set_selected_checks(self.class_folders, True))
        menu.addAction("Uncheck Selected", lambda: self._set_selected_checks(self.class_folders, False))
        menu.addSeparator()
        self._add_image_type_menu(menu)
        self._popup_menu(menu, position)

    def _attribute_folder_menu(self, position):
        menu = QMenu(self)
        self._add_view_menu(menu)
        menu.addSeparator()
        menu.addAction("Select All", self.attribute_folders.selectAll)
        menu.addAction("Deselect All", self.attribute_folders.clearSelection)
        menu.addSeparator()
        self._add_image_type_menu(menu)
        self._popup_menu(menu, position)

    def _prompt_text(self, title, label, text=""):
        box = QDialog(self)
        box.setWindowTitle(title)
        form = QVBoxLayout(box)
        form.addWidget(QLabel(label))
        edit = QLineEdit(text)
        form.addWidget(edit)
        buttons = QHBoxLayout()
        ok = QPushButton("OK")
        cancel = QPushButton("Cancel")
        ok.clicked.connect(box.accept)
        cancel.clicked.connect(box.reject)
        buttons.addStretch(1)
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        form.addLayout(buttons)
        if _exec(box) != QDialog.Accepted:
            return None
        return edit.text().strip()

    def _selected_class_code(self):
        rows = self.class_folders.selectionModel().selectedRows()
        if not rows:
            return None
        item = self.class_folders.item(rows[0].row(), 1)
        return int(item.text()) if item else None

    def _rename_class_folder(self):
        code = self._selected_class_code()
        if code is None:
            return
        new_text = self._prompt_text("Rename", "Class code:", str(code))
        if new_text is None or not new_text.lstrip("-").isdigit():
            return
        new_code = int(new_text)
        for defect in self.result.get("defects", []):
            if int(defect.get("class_code", 0)) == code:
                defect["class_code"] = new_code
        self._save_result()
        self._refresh_advanced_classify()
        self._refresh_defects(self.selected_id)

    def _delete_class_folder(self):
        code = self._selected_class_code()
        if code is None:
            return
        answer = QMessageBox.question(
            self,
            "Delete",
            f"Delete class code {code}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        for defect in self.result.get("defects", []):
            if int(defect.get("class_code", 0)) == code:
                defect["class_code"] = 0
        self._save_result()
        self._refresh_advanced_classify()
        self._refresh_defects(self.selected_id)

    def _class_folders_selected(self):
        if getattr(self, "_refreshing_folders", False):
            return
        codes = set()
        for index in self.class_folders.selectionModel().selectedRows():
            item = self.class_folders.item(index.row(), 1)
            if item is not None:
                codes.add(int(item.text()))
        self.gallery_class_codes = codes
        self._show_classify_matches()

    def _attribute_folders_selected(self):
        if getattr(self, "_refreshing_folders", False):
            return
        rows = self.attribute_folders.selectionModel().selectedRows()
        if not rows:
            self.gallery_attribute_value = None
        else:
            item = self.attribute_folders.item(rows[0].row(), 1)
            self.gallery_attribute_value = item.text() if item is not None else None
        self._show_classify_matches()

    def _classify_matches(self):
        defects = list(self.visible_defects)
        if self.gallery_class_codes:
            defects = [
                item for item in defects
                if int(item.get("class_code", 0)) in self.gallery_class_codes
            ]
        if self.gallery_attribute_value not in (None, ""):
            key = self._advanced_key()
            defects = [
                item for item in defects
                if str(item.get(key, "")) == self.gallery_attribute_value
            ]
        return defects

    def _show_classify_matches(self):
        matches = self._classify_matches()
        if (
            matches
            and hasattr(self, "layout_mode")
            and self.layout_mode.currentText() == "Advanced Classify"
            and self.selected_id not in {item.get("id") for item in matches}
        ):
            self._select_id(matches[0].get("id"))
        self._refresh_classify_strip()

    def _refresh_classify_strip(self):
        if not hasattr(self, "classify_strip"):
            return
        advanced = hasattr(self, "layout_mode") and self.layout_mode.currentText() == "Advanced Classify"
        matches = self._classify_matches() if advanced else []
        self.classify_group_label.setText(f"UnGrouped  ({len(matches)} items)")
        self.classify_strip.set_defects(matches, self.selected_id)

    def _select_all_visible(self):
        self.selected_ids = {item.get("id") for item in self.visible_defects}
        if self.visible_defects:
            current = self.selected_id if self.selected_id in self.selected_ids else self.visible_defects[0].get("id")
            self._select_id(current, select_row=False)
        self._publish_selection()

    def _clear_selection(self):
        self.selected_ids.clear()
        self.grid.clearSelection()
        self._publish_selection()

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
        menu = self._grid_menu(False, None)
        menu.exec(self.grid.viewport().mapToGlobal(position)) if hasattr(menu, "exec") else menu.exec_(self.grid.viewport().mapToGlobal(position))

    def _grid_header_context_menu(self, position):
        column = self.grid.horizontalHeader().logicalIndexAt(position)
        menu = self._grid_menu(True, column)
        menu.exec(self.grid.horizontalHeader().mapToGlobal(position)) if hasattr(menu, "exec") else menu.exec_(self.grid.horizontalHeader().mapToGlobal(position))

    def _grid_menu(self, on_header, column):
        menu = QMenu(self)
        menu.addAction("Toolbar", self._show_grid_toolbar)
        menu.addAction("Select All Defects", self._select_all_visible)
        menu.addAction("Remove Selection", self._clear_selection)
        menu.addAction("Show All Columns", self._show_all_grid_columns)
        if on_header and column is not None and 0 <= column < len(self.grid_columns):
            menu.addAction("Hide Column", lambda _checked=False, index=column: self._hide_grid_column(index))
            key = self.grid_columns[column]
            if key in GRID_CHECK_COLUMNS and self._column_has_checks(key):
                menu.addAction("Clear", lambda _checked=False, name=key: self._clear_column_checks(name))
        return menu

    def _show_grid_toolbar(self):
        self.grid_toolbar.setVisible(True)
        self.status.setText("Defect Grid toolbar displayed.")

    def _column_has_checks(self, key):
        return any(bool(self._grid_attribute(defect, key)) for defect in self.visible_defects)

    def _clear_column_checks(self, key):
        for defect in self.visible_defects:
            if key == "sample":
                defect["sampled"] = False
                defect["sampled_review"] = False
            elif key == "marked":
                defect["marked"] = False
        self._refresh_defects(self.selected_id)
        self.status.setText(f"Cleared the {dict(self.available_grid_columns).get(key, key)} check boxes.")

    def _grid_icon_button(self, filename, tooltip, callback):
        button = QPushButton()
        button.setToolTip(tooltip)
        pixmap = vector_pixmap(filename, 22)
        button.setIcon(QIcon(pixmap))
        button.setIconSize(pixmap.size())
        button.setFixedSize(pixmap.width() + 4, pixmap.height() + 4)
        button.setStyleSheet("QPushButton { background: transparent; border: 1px solid transparent; padding: 0; min-height: 0; }")
        button.clicked.connect(lambda _checked=False: callback())
        return button

    def _default_grid_name(self, name):
        return str(name or "").strip() in {"", "Default", "(DEFAULT)"}

    def _go_to_grid_column(self, selection):
        if not hasattr(self, "grid"):
            return
        if isinstance(selection, int):
            key = self.grid_go_to.itemData(selection)
        else:
            key = next(
                (column for column, text in self.available_grid_columns if text == selection),
                None,
            )
        if key not in self.grid_columns:
            return
        index = self.grid_columns.index(key)
        item = self.grid.item(max(self.grid.currentRow(), 0), index)
        if item is not None:
            self.grid.scrollToItem(item, QAbstractItemView.PositionAtCenter)

    def _show_named_column(self, selection):
        if isinstance(selection, int):
            key = self.grid_show_column.itemData(selection)
        else:
            key = next(
                (column for column, text in self.available_grid_columns if text == selection),
                None,
            )
        if key is None or key in self.grid_columns:
            return
        frozen = self._frozen_grid_keys()
        self.grid_columns.insert(len(frozen), key)
        self._apply_grid_headers()
        self._refresh_defects(self.selected_id)

    def _set_grid_column_width(self, text):
        if not text or not hasattr(self, "grid"):
            return
        try:
            width = int(str(text).strip())
        except ValueError:
            return
        column = self.grid.currentColumn()
        if column < 0:
            column = 0
        self.grid.setColumnWidth(column, max(24, width))

    def _frozen_grid_keys(self):
        released = getattr(self, "_released_grid_columns", set())
        return [
            key for key in ("id", "marked", "sample", "manual_class")
            if key in self.grid_columns and key not in released
        ]

    def _grid_section_moved(self, logical, old_visual, new_visual):
        if getattr(self, "_moving_sections", False):
            return
        key = self.grid_columns[logical] if 0 <= logical < len(self.grid_columns) else ""
        frozen = self._frozen_grid_keys()
        header = self.grid.horizontalHeader()
        if key in ("id", "marked"):
            self._snap_grid_section(header, new_visual, old_visual)
            return
        if key in frozen and new_visual >= len(frozen):
            self._released_grid_columns.add(key)
            return
        if key not in frozen and new_visual < len(self._frozen_grid_keys()):
            self._snap_grid_section(header, new_visual, max(old_visual, len(frozen)))

    def _snap_grid_section(self, header, visual_from, visual_to):
        self._moving_sections = True
        header.moveSection(visual_from, visual_to)
        self._moving_sections = False

    def _grid_header_double_clicked(self, logical):
        if not (0 <= logical < len(self.grid_columns)):
            return
        key = self.grid_columns[logical]
        if self._grid_sort_column == key:
            self._grid_sort_ascending = not self._grid_sort_ascending
        else:
            self._grid_sort_column = key
            self._grid_sort_ascending = True
        self._refresh_defects(self.selected_id)

    def _map_menu_icon(self, kind):
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        if kind == "selected":
            painter.setBrush(QColor("#39c15a"))
            painter.setPen(Qt.NoPen)
            for x, y in ((4, 4), (8, 3), (12, 5), (6, 8), (11, 9), (5, 12), (10, 12)):
                painter.drawEllipse(x, y, 3, 3)
        elif kind == "care":
            painter.setBrush(QColor("#7d9a3a"))
            painter.setPen(QPen(QColor("#4d4d4d"), 1))
            painter.drawRect(3, 2, 4, 12)
            painter.drawRect(9, 2, 4, 12)
        elif kind == "overview":
            painter.setBrush(QColor("#f4f4f1"))
            painter.setPen(QPen(QColor("#666666"), 1))
            painter.drawEllipse(1, 1, 14, 14)
        elif kind == "tip":
            painter.setBrush(QColor("#f0c040"))
            painter.setPen(QPen(QColor("#8a6a10"), 1))
            painter.drawEllipse(4, 2, 8, 8)
            painter.drawRect(6, 10, 4, 3)
        elif kind == "resolution":
            painter.setPen(QPen(QColor("#1d4f9c"), 2))
            painter.drawEllipse(2, 2, 8, 8)
            painter.drawLine(9, 9, 14, 14)
        elif kind == "view":
            painter.setBrush(QColor("#4c7fd4"))
            painter.setPen(Qt.NoPen)
            painter.drawRect(2, 3, 12, 8)
        elif kind == "save":
            painter.setPen(QPen(QColor("#333333"), 1))
            painter.setBrush(QColor("#d8d2c4"))
            painter.drawRect(3, 2, 10, 12)
        elif kind == "copy":
            painter.setPen(QPen(QColor("#333333"), 1))
            painter.setBrush(QColor("#f7f4ea"))
            painter.drawRect(4, 3, 8, 10)
            painter.drawRect(2, 1, 8, 10)
        elif kind == "print":
            painter.setBrush(QColor("#6f8fbf"))
            painter.setPen(QPen(QColor("#333333"), 1))
            painter.drawRect(3, 5, 10, 7)
            painter.drawRect(5, 2, 6, 4)
        else:
            painter.setPen(QPen(QColor("#333333"), 1))
            painter.setBrush(QColor("#f7f4ea"))
            painter.drawRect(2, 2, 12, 12)
        painter.end()
        return QIcon(pixmap)

    def _map_context_menu(self, position):
        menu = self._build_map_menu()
        widget = self.sender() if isinstance(self.sender(), QWidget) else self.wafer_map
        menu.exec(widget.mapToGlobal(position)) if hasattr(menu, "exec") else menu.exec_(widget.mapToGlobal(position))

    def _build_map_menu(self):
        menu = QMenu(self)
        selected = menu.addAction(self._map_menu_icon("selected"), "Display selected defects")
        selected.setCheckable(True)
        selected.setChecked(self.wafer_map.show_selected_crosshair)
        selected.toggled.connect(lambda checked: self._set_map_flag("show_selected_crosshair", checked))
        care = menu.addAction(self._map_menu_icon("care"), "Display care areas")
        care.setCheckable(True)
        care.setChecked(self.wafer_map.show_care_areas)
        care.toggled.connect(self._set_care_areas_visible)
        overview = menu.addAction(self._map_menu_icon("overview"), "Display overview")
        overview.setCheckable(True)
        overview.setChecked(self.wafer_map.show_overview)
        overview.toggled.connect(lambda checked: self._set_map_flag("show_overview", checked))
        tips = menu.addAction(self._map_menu_icon("tip"), "Display tooltips")
        tips.setCheckable(True)
        tips.setChecked(self.wafer_map.show_tooltips)
        tips.toggled.connect(lambda checked: self._set_map_flag("show_tooltips", checked))
        menu.addSeparator()
        resolution = menu.addMenu(self._map_menu_icon("resolution"), "Defect Resolution")
        for name in ("Large", "Small"):
            action = resolution.addAction(name)
            action.setCheckable(True)
            action.setChecked(self.wafer_map.defect_resolution == name)
            action.triggered.connect(lambda _checked=False, value=name: self._set_defect_resolution(value))
        view = menu.addMenu(self._map_menu_icon("view"), "View Mode")
        for label, mode in (("Wafer", "Wafer Map"), ("Die", "Die Stack"), ("Reticle", "Reticle Stack")):
            action = view.addAction(label)
            action.setCheckable(True)
            action.setChecked(self.map_display.currentText() == mode)
            action.triggered.connect(lambda _checked=False, value=mode: self.map_display.setCurrentText(value))
        menu.addSeparator()
        menu.addAction(self._map_menu_icon("save"), "Save", self._save_wafer_map)
        menu.addAction(self._map_menu_icon("copy"), "Copy", self._copy_wafer_map)
        menu.addAction(self._map_menu_icon("print"), "Print", self._print_wafer_map)
        menu.addSeparator()
        menu.addAction(self._map_menu_icon("options"), "Display Options ...", self._map_display_options)
        stacking = menu.addAction("Defect Stacking settings...")
        stacking.triggered.connect(self._stacking_settings)
        return menu

    def _set_map_flag(self, name, checked):
        setattr(self.wafer_map, name, bool(checked))
        self.wafer_map.update()

    def _set_defect_resolution(self, value):
        self.wafer_map.defect_resolution = value
        self.wafer_map.update()
        self.status.setText(f"Defect Resolution: {value}.")

    def _map_display_options(self):
        dialog = WaferMapDisplayOptionsDialog(self.wafer_map, self.show_die, self.show_defects, self)
        if _exec(dialog) != QDialog.Accepted:
            return
        self.show_die.setChecked(dialog.show_die.isChecked())
        self.show_defects.setChecked(dialog.show_defects.isChecked())
        self.wafer_map.show_reticle = dialog.show_reticle.isChecked()
        self.wafer_map.show_marker = dialog.show_marker.isChecked()
        self.wafer_map.show_reticle_modulation = dialog.show_modulation.isChecked()
        self._map_options_changed()

    def _stacking_settings(self):
        dialog = DefectStackingSettingsDialog(
            self.wafer_map.stack_tolerance_x,
            self.wafer_map.stack_tolerance_y,
            self,
        )
        if _exec(dialog) != QDialog.Accepted:
            return
        self.wafer_map.stack_tolerance_x = dialog.tolerance_x.value()
        self.wafer_map.stack_tolerance_y = dialog.tolerance_y.value()
        self.wafer_map.update()
        self.status.setText(
            "Defect stacking tolerance "
            f"X {self.wafer_map.stack_tolerance_x:.3f}, Y {self.wafer_map.stack_tolerance_y:.3f}."
        )

    def _show_all_grid_columns(self):
        self.grid_columns = [key for key, _label in self.available_grid_columns]
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

    def _apply_image_filter(self, mode):
        if self.image_filter.currentText() != mode:
            self.image_filter.setCurrentText(mode)
            return
        self._set_image_filter(mode)

    def _set_image_filter(self, mode):
        self.filters["image_filter"] = mode
        self._refresh_defects(self.selected_id)

    def _grid_pane(self):
        frame, layout = self._pane("Defect Grid")
        self._released_grid_columns = set()
        self._moving_sections = False
        self._grid_anchor = None
        self._grid_sort_column = None
        self._grid_sort_ascending = True
        self.grid_toolbar = QWidget()
        toolbar = QVBoxLayout(self.grid_toolbar)
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(2)
        top = QHBoxLayout()
        top.setSpacing(4)
        self.grid_configuration = QComboBox()
        self.grid_configuration.setEditable(True)
        self.grid_configuration.setFixedWidth(88)
        self.grid_configuration.setToolTip("Configurations: select a previously defined grid configuration.")
        self.grid_configuration.addItems(["(DEFAULT)"] + sorted((self.result.get("review_grid_configs") or {}).keys()))
        self.grid_configuration.currentTextChanged.connect(self._load_grid_configuration)
        top.addWidget(self.grid_configuration)
        top.addWidget(self._grid_icon_button("grid_save.png", "Save the current grid configuration.", self._save_grid_configuration))
        top.addWidget(self._grid_icon_button("grid_default.png", "Set the current grid configuration as the default.", self._set_default_grid_configuration))
        top.addWidget(self._grid_icon_button("grid_delete.png", "Delete the current grid configuration.", self._delete_grid_configuration))
        top.addWidget(QLabel("Go To :"))
        self.grid_go_to = QComboBox()
        self.grid_go_to.setToolTip("Go To: jump to a column in the grid.")
        self.grid_go_to.currentIndexChanged.connect(self._go_to_grid_column)
        top.addWidget(self.grid_go_to, 1)
        top.addWidget(QLabel("Show Column:"))
        self.grid_show_column = QComboBox()
        self.grid_show_column.setToolTip("Show Column: display a previously hidden column.")
        self.grid_show_column.currentIndexChanged.connect(self._show_named_column)
        top.addWidget(self.grid_show_column, 1)
        toolbar.addLayout(top)
        bottom = QHBoxLayout()
        bottom.setSpacing(4)
        bottom.addWidget(QLabel("Column Width"))
        self.grid_column_width = QComboBox()
        self.grid_column_width.setEditable(True)
        self.grid_column_width.setFixedWidth(52)
        self.grid_column_width.addItems(["60", "80", "100", "120", "160"])
        self.grid_column_width.setCurrentText("80")
        self.grid_column_width.setToolTip("Column Width: set the width of the current column.")
        self.grid_column_width.currentTextChanged.connect(self._set_grid_column_width)
        bottom.addWidget(self.grid_column_width)
        configure = QPushButton("Configure...")
        configure.setToolTip("Choose which attributes are displayed.")
        configure.clicked.connect(self._configure_grid_columns)
        bottom.addWidget(configure)
        bottom.addStretch(1)
        toolbar.addLayout(bottom)
        layout.addWidget(self.grid_toolbar)
        self.grid = QTableWidget(0, len(self.grid_columns))
        self.grid.setSelectionMode(QAbstractItemView.MultiSelection)
        self.grid.setContextMenuPolicy(Qt.CustomContextMenu)
        self.grid.customContextMenuRequested.connect(self._grid_context_menu)
        header = self.grid.horizontalHeader()
        header.setSectionsMovable(True)
        header.setContextMenuPolicy(Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self._grid_header_context_menu)
        header.sectionMoved.connect(self._grid_section_moved)
        header.sectionDoubleClicked.connect(self._grid_header_double_clicked)
        self._apply_grid_headers()
        self.grid.verticalHeader().setVisible(True)
        self.grid.verticalHeader().setDefaultAlignment(Qt.AlignCenter)
        self.grid.currentCellChanged.connect(self._grid_selection_changed)
        self.grid.cellClicked.connect(self._grid_id_clicked)
        self.grid.cellDoubleClicked.connect(self._grid_double_clicked)
        header.installEventFilter(self)
        layout.addWidget(self.grid, 1)
        return frame

    def _chart_pane(self):
        frame, layout = self._pane("Chart Pane")
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
        labels = dict(self.available_grid_columns)
        self._moving_sections = True
        self.grid.setColumnCount(len(self.grid_columns))
        self.grid.setHorizontalHeaderLabels([labels[key] for key in self.grid_columns])
        self.grid.horizontalHeader().setSectionsMovable(True)
        self._moving_sections = False
        header = self.grid.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignCenter)
        sort_key = getattr(self, "_grid_sort_column", None)
        if sort_key in self.grid_columns:
            header.setSortIndicatorShown(True)
            header.setSortIndicator(
                self.grid_columns.index(sort_key),
                Qt.AscendingOrder if getattr(self, "_grid_sort_ascending", True) else Qt.DescendingOrder,
            )
        else:
            header.setSortIndicatorShown(False)
        corner = next((child for child in self.grid.children() if isinstance(child, QAbstractButton)), None)
        if corner is not None:
            corner.setText("Defect")
        self._refresh_grid_toolbar_lists()

    def _configure_grid_columns(self):
        dialog = GridColumnsDialog(self.grid_columns, self, columns=self.available_grid_columns)
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
        if self._default_grid_name(name):
            columns = self.result.get("default_review_grid_columns") or _initial_review_grid_columns(
                self.result, self.available_grid_columns
            )
        else:
            columns = configs.get(name)
        if columns:
            valid = [key for key in columns if key in dict(self.available_grid_columns)]
            if valid:
                self.grid_columns = valid
                self._sync_released_columns()
                self._apply_grid_headers()
                self._refresh_defects(self.selected_id)

    def _save_grid_configuration(self):
        name = self.grid_configuration.currentText().strip()
        if self._default_grid_name(name):
            self.result["default_review_grid_columns"] = list(self.grid_columns)
            self._save_result()
            self.status.setText("Current column order saved as the default configuration.")
            return
        self.result.setdefault("review_grid_configs", {})[name] = list(self.grid_columns)
        if self.grid_configuration.findText(name) < 0:
            self.grid_configuration.addItem(name)
        self._save_result()
        self.status.setText(f"Saved grid configuration {name}.")

    def _sync_released_columns(self):
        prefix = []
        for key in self.grid_columns:
            if key in ("id", "marked", "sample", "manual_class"):
                prefix.append(key)
            else:
                break
        self._released_grid_columns = {
            key for key in ("sample", "manual_class")
            if key in self.grid_columns and key not in prefix
        }

    def _delete_grid_configuration(self):
        name = self.grid_configuration.currentText()
        if self._default_grid_name(name):
            return
        self.result.setdefault("review_grid_configs", {}).pop(name, None)
        if self.result.get("default_review_grid_config") == name:
            self.result.pop("default_review_grid_config", None)
        self.grid_configuration.removeItem(self.grid_configuration.findText(name))
        self.grid_configuration.setCurrentText("(DEFAULT)")
        self._save_result()

    def _set_default_grid_configuration(self):
        name = self.grid_configuration.currentText().strip()
        if name and not self._default_grid_name(name):
            self._save_grid_configuration()
            self.result["default_review_grid_config"] = name
        self.result["default_review_grid_columns"] = list(self.grid_columns)
        self._save_result()
        self.status.setText("Current column order saved as the default configuration.")

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

    def _grid_attribute(self, defect, key):
        if key == "sample":
            return bool(defect.get("sampled") or defect.get("sampled_review"))
        if key == "manual_class":
            return defect.get("manual_class", defect.get("class_code", 0))
        if key == "intensity":
            return defect.get("intensity", defect.get("signal", ""))
        if key == "x_wafer":
            return defect.get("x_wafer", defect.get("x_um", defect.get("x", "")))
        if key == "y_wafer":
            return defect.get("y_wafer", defect.get("y_um", defect.get("y", "")))
        if key in defect and defect.get(key) not in (None, ""):
            return defect.get(key)
        single_path = not any(str(name).startswith(("ch2_", "ch3_")) for name in defect)
        if key == "ch1_intensity" and single_path:
            return defect.get("intensity", defect.get("signal", ""))
        return defect.get(key, "")

    def _grid_text(self, key, value):
        if isinstance(value, bool):
            return "Yes" if value else "No"
        if isinstance(value, float):
            try:
                return f"{float(value):.3f}"
            except (TypeError, ValueError):
                return ""
        if value is None:
            return ""
        return str(value)

    def _set_grid_check(self, row, column, key, checked):
        box = QCheckBox()
        box.setChecked(checked)
        box.toggled.connect(lambda state, row=row, key=key: self._grid_check_changed(row, key, state))
        self.grid.setCellWidget(row, column, box)

    def _set_grid_choice(self, row, column, value):
        choice = QComboBox()
        choice.setEditable(True)
        self._fill_class_combo(choice, value)
        choice.activated.connect(
            lambda _index, row=row, widget=choice: self._commit_manual_class(row, widget.currentText(), False)
        )
        editor = choice.lineEdit()
        editor.setProperty("manual_class_row", row)
        editor.setProperty("manual_class_advance", True)
        editor.installEventFilter(self)
        self.grid.setCellWidget(row, column, choice)

    def _grid_check_changed(self, row, key, checked):
        if self._loading or not (0 <= row < len(self.visible_defects)):
            return
        defect = self.visible_defects[row]
        if key == "sample":
            defect["sampled"] = bool(checked)
            defect["sampled_review"] = bool(checked)
        else:
            defect["marked"] = bool(checked)
        self.wafer_map.update()
        self._sync_review_status()

    def _known_class_codes(self):
        codes = set(getattr(self, "_extra_class_codes", set()))
        for defect in self.result.get("defects") or []:
            for key in ("class_code", "manual_class"):
                try:
                    codes.add(int(defect.get(key) or 0))
                except (TypeError, ValueError):
                    continue
        return sorted(codes) or [0]

    def _fill_class_combo(self, combo, value):
        text = str(0 if value is None else value)
        combo.blockSignals(True)
        combo.clear()
        combo.addItems([str(code) for code in self._known_class_codes()])
        if combo.findText(text) < 0:
            combo.addItem(text)
        combo.setCurrentText(text)
        combo.blockSignals(False)

    def _commit_manual_class(self, row, text, advance):
        if getattr(self, "_loading", False):
            return
        if row < 0:
            row = next((index for index, item in enumerate(self.visible_defects) if item.get("id") == self.selected_id), -1)
        if not (0 <= row < len(self.visible_defects)):
            return
        try:
            code = int(str(text).strip())
        except ValueError:
            return
        source = self.visible_defects[row]
        if source.get("id") in self.selected_ids and len(self.selected_ids) > 1:
            targets = set(self.selected_ids)
        else:
            targets = {source.get("id")}
        self._assign_manual_class(code, targets, source.get("id") if advance else None)

    def _assign_manual_class(self, code, targets, advance_from=None):
        code = int(code)
        self._extra_class_codes = getattr(self, "_extra_class_codes", set())
        self._extra_class_codes.add(code)
        count = 0
        for defect in self.result.get("defects") or []:
            if defect.get("id") in targets:
                defect["manual_class"] = code
                defect["class_code"] = code
                defect["reviewed"] = True
                count += 1
        next_id = self.selected_id
        if advance_from is not None:
            identifiers = [item.get("id") for item in self.visible_defects]
            if advance_from in identifiers:
                index = identifiers.index(advance_from)
                next_id = identifiers[min(index + 1, len(identifiers) - 1)]
        self._save_result()
        self._refresh_defects(next_id)
        if advance_from is not None and "manual_class" in self.grid_columns:
            row = next((index for index, item in enumerate(self.visible_defects) if item.get("id") == next_id), -1)
            column = self.grid_columns.index("manual_class")
            if row >= 0:
                self.grid.setCurrentCell(row, column)
                widget = self.grid.cellWidget(row, column)
                if widget is not None and widget.lineEdit() is not None:
                    widget.setFocus()
                    widget.lineEdit().selectAll()
        self.status.setText(f"Assigned class code {code} to {count} defect(s).")

    def _classify_from_toolbar(self, code):
        if self.selected_ids:
            targets = set(self.selected_ids)
        elif self.selected_id is not None:
            targets = {self.selected_id}
        else:
            return
        self._assign_manual_class(code, targets)

    def _grid_id_clicked(self, row, column):
        if self._loading or "id" not in self.grid_columns or column != self.grid_columns.index("id"):
            return
        if not (0 <= row < len(self.visible_defects)):
            return
        modifiers = QApplication.keyboardModifiers()
        if modifiers & Qt.ShiftModifier and self._grid_anchor is not None:
            self._select_grid_range(self._grid_anchor, row)
        else:
            self._grid_anchor = row
        defect = self.visible_defects[row]
        self.review_optics_state["stage_connected"] = True
        self.review_optics_state["stage_x"] = float(defect.get("x", 0.0))
        self.review_optics_state["stage_y"] = float(defect.get("y", 0.0))
        self.review_optics_state["stage_defect_id"] = defect.get("id")
        self.status.setText(f"Stage connected. Moved to defect {defect.get('id')}.")

    def _apply_grid_sort(self):
        key = getattr(self, "_grid_sort_column", None)
        if not key:
            return

        def sort_value(defect):
            value = self._grid_attribute(defect, key)
            if isinstance(value, bool):
                return (0, int(value))
            if isinstance(value, (int, float)):
                return (0, float(value))
            text = str(value)
            try:
                return (0, float(text))
            except ValueError:
                return (1, text.lower())

        self.visible_defects.sort(key=sort_value, reverse=not getattr(self, "_grid_sort_ascending", True))

    def _refresh_grid_toolbar_lists(self):
        if not hasattr(self, "grid_go_to"):
            return
        labels = dict(self.available_grid_columns)
        self.grid_go_to.blockSignals(True)
        current = self.grid_go_to.currentData()
        self.grid_go_to.clear()
        for key in self.grid_columns:
            self.grid_go_to.addItem(labels[key], key)
        if current in self.grid_columns:
            self.grid_go_to.setCurrentIndex(self.grid_columns.index(current))
        self.grid_go_to.blockSignals(False)
        self.grid_show_column.blockSignals(True)
        self.grid_show_column.clear()
        self.grid_show_column.addItem("", None)
        for key, text in self.available_grid_columns:
            if key not in self.grid_columns:
                self.grid_show_column.addItem(text, key)
        self.grid_show_column.blockSignals(False)

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
        self._apply_grid_sort()
        self._loading = True
        self.grid.setRowCount(0)
        for defect in self.visible_defects:
            row = self.grid.rowCount()
            self.grid.insertRow(row)
            self.grid.setVerticalHeaderItem(row, QTableWidgetItem(str(defect.get("id", ""))))
            for column, key in enumerate(self.grid_columns):
                value = self._grid_attribute(defect, key)
                item = QTableWidgetItem("" if key in GRID_CHECK_COLUMNS or key in GRID_CHOICE_COLUMNS else self._grid_text(key, value))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.grid.setItem(row, column, item)
                if key in GRID_CHECK_COLUMNS:
                    self._set_grid_check(row, column, key, bool(value))
                elif key in GRID_CHOICE_COLUMNS:
                    self._set_grid_choice(row, column, value)
        self._loading = False
        self.wafer_map.set_defects(self.visible_defects)
        self.wafer_map.set_selected_ids(self.selected_ids)
        summary = review_summary(self.result, self.visible_defects)
        self._refresh_chart()
        self._refresh_summary()
        self._refresh_advanced_classify()
        self.map_info.setText(f"Red: defect    Green: marked    +: selected    Visible defects: {summary['visible']}")
        if self.visible_defects:
            ids = {item.get("id") for item in self.visible_defects}
            self._select_id(preferred_id if preferred_id in ids else self.visible_defects[0].get("id"))
        else:
            self.selected_id = None
            for widget in self.image_widgets:
                widget.set_defect(None)
            self._sync_defect_details()
            self._sync_review_status()
        self._sync_grid_highlight()
        self._refresh_classify_strip()
        self._update_active_filter_label()

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
        self._sync_defect_details()
        self._sync_review_status()

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
        self._publish_selection()

    def _selection_mode_changed(self, mode):
        if not hasattr(self, "wafer_map"):
            return
        if str(mode).startswith("Deselect"):
            self.wafer_map.setCursor(Qt.ForbiddenCursor)
        else:
            self.wafer_map.setCursor(Qt.CrossCursor)

    def _reticle_size(self):
        layout = self.current_recipe.get("wafer_map", {}) if self.current_recipe else {}
        return max(1, int(layout.get("reticle_width", 1))), max(1, int(layout.get("reticle_height", 1)))

    def _die_key(self, defect):
        return (int(defect.get("die_x", 0)), int(defect.get("die_y", 0)))

    def _reticle_key(self, defect):
        width, height = self._reticle_size()
        die_x, die_y = self._die_key(defect)
        return die_x // width, die_y // height

    def _die_at_point(self, px, py):
        if not self.visible_defects:
            return None
        x0, y0, side = self.wafer_map._geometry()
        if side <= 1:
            return None
        wafer_x = (px - x0) / side * 2 - 1
        wafer_y = 1 - (py - y0) / side * 2
        centers = {}
        for defect in self.visible_defects:
            key = self._die_key(defect)
            bucket = centers.setdefault(key, [0.0, 0.0, 0])
            bucket[0] += float(defect.get("x", 0.0))
            bucket[1] += float(defect.get("y", 0.0))
            bucket[2] += 1
        return min(
            centers,
            key=lambda key: (centers[key][0] / centers[key][2] - wafer_x) ** 2
            + (centers[key][1] / centers[key][2] - wafer_y) ** 2,
        )

    def _ids_on_feature(self, defect, mode):
        if "Reticle" in mode:
            field = self._reticle_key(defect)
            return [
                item.get("id") for item in self.visible_defects
                if self._reticle_key(item) == field
            ]
        die = self._die_key(defect)
        return [
            item.get("id") for item in self.visible_defects
            if self._die_key(item) == die
        ]

    def _map_clicked(self, px, py):
        nearest = self.wafer_map._nearest_defect(px, py)
        if nearest is not None:
            self._select_id(nearest.get("id"))

    def _map_double_clicked(self, defect_id):
        mode = self.selection_mode.currentText()
        defect = next((item for item in self.visible_defects if item.get("id") == defect_id), None)
        if defect is None:
            return
        if "Die" in mode or "Reticle" in mode:
            self._apply_feature_selection(self._ids_on_feature(defect, mode))
            return
        self._select_id(defect_id, select_row=True)
        if mode.startswith("Deselect"):
            self.selected_ids.discard(defect_id)
            self._publish_selection()
        else:
            self._toggle_selected_id(defect_id)

    def _select_grid_range(self, start, end):
        first, last = sorted((start, end))
        self.selected_ids = {
            self.visible_defects[index].get("id")
            for index in range(first, last + 1)
            if 0 <= index < len(self.visible_defects)
        }
        self._select_id(self.visible_defects[end].get("id"), select_row=False)
        self._publish_selection()

    def _grid_double_clicked(self, row, column):
        if not (0 <= row < len(self.visible_defects)):
            return
        defect = self.visible_defects[row]
        if "id" in self.grid_columns and column == self.grid_columns.index("id"):
            self._grid_anchor = row
            self.selected_ids.add(defect.get("id"))
            self._select_id(defect.get("id"), select_row=False)
            self._publish_selection()
            return
        mode = self.selection_mode.currentText()
        self._select_id(defect.get("id"), select_row=False)
        if "Die" in mode or "Reticle" in mode:
            self._apply_feature_selection(self._ids_on_feature(defect, mode))
            return
        if mode.startswith("Deselect"):
            self.selected_ids.discard(defect.get("id"))
            self._publish_selection()
            return
        self._toggle_selected_id(defect.get("id"))

    def _apply_feature_selection(self, identifiers):
        deselect = self.selection_mode.currentText().startswith("Deselect")
        if deselect:
            self.selected_ids.difference_update(identifiers)
        else:
            self.selected_ids.update(identifiers)
        focus = next((item for item in identifiers if item in self.selected_ids), None)
        if focus is None and identifiers:
            focus = identifiers[0]
        if focus is not None:
            self._select_id(focus, select_row=False)
        self._publish_selection()

    def _publish_selection(self):
        self.wafer_map.set_selected_ids(self.selected_ids)
        self._sync_grid_highlight()
        self._sync_review_status()

    def _sync_grid_highlight(self):
        if not hasattr(self, "grid"):
            return
        chosen = QColor("#d7e4f8")
        plain = QColor("#ffffff")
        for row, defect in enumerate(self.visible_defects):
            color = chosen if defect.get("id") in self.selected_ids else plain
            for column in range(self.grid.columnCount()):
                item = self.grid.item(row, column)
                if item is not None:
                    item.setBackground(color)
                widget = self.grid.cellWidget(row, column)
                if widget is not None:
                    widget.setStyleSheet(f"background: {color.name()};")

    def _select_area(self, identifiers):
        inside = [item for item in self.visible_defects if item.get("id") in set(identifiers)]
        mode = self.selection_mode.currentText()
        if "Die" in mode or "Reticle" in mode:
            identifiers = []
            seen = set()
            for item in inside:
                for defect_id in self._ids_on_feature(item, mode):
                    if defect_id not in seen:
                        seen.add(defect_id)
                        identifiers.append(defect_id)
        self._apply_feature_selection(identifiers)

    def _filter_in(self):
        if not self.selected_ids:
            self.status.setText("Select defects before using Filter In.")
            return
        self.filters["include_ids"] = sorted(self.selected_ids)
        self.filters["exclude_ids"] = []
        kept = self.selected_id if self.selected_id in self.selected_ids else None
        self._refresh_defects(kept)
        self.status.setText(f"Filter In: {len(self.visible_defects)} defect(s) displayed.")

    def _filter_out(self):
        if not self.selected_ids:
            self.status.setText("Select defects before using Filter Out.")
            return
        removed = len(self.selected_ids)
        include = list(self.filters.get("include_ids") or [])
        if include:
            remaining = [item for item in include if item not in self.selected_ids]
            self.filters["include_ids"] = remaining if remaining else [-1]
        excluded = set(self.filters.get("exclude_ids") or [])
        excluded.update(self.selected_ids)
        self.filters["exclude_ids"] = sorted(item for item in excluded if item != -1)
        self.selected_ids.clear()
        self._refresh_defects()
        self.status.setText(f"Filter Out: {removed} defect(s) removed from the Defect Grid.")

    def _reset_filter(self):
        self.filters = default_filter_state()
        self.selected_ids.clear()
        if hasattr(self, "image_filter"):
            self.image_filter.blockSignals(True)
            self.image_filter.setCurrentText("All Defects")
            self.image_filter.blockSignals(False)
        self._refresh_defects(self.selected_id)
        self.status.setText("Reset Filter: all defects restored to the Defect Grid.")

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
        names = list(self.result.get("selected_tests") or [])
        dialog = WaferPostProcessingDialog(
            self.result.get("review_analysis"),
            test_count=len(names),
            tests=names,
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
        if not getattr(self, "_review_lot_ready", False):
            self.status.setText("Select a lot or import a KLARF before adjusting the offset.")
            return
        self._close_offset_page(False)
        page = ReviewOffsetDialog(
            self.result,
            die_origin=die_origin,
            defect_id=self.selected_id,
            embedded=True,
            parent=self,
        )
        self._offset_page = page
        self.pane_splitter.hide()
        self.defect_details_bar.hide()
        self.review_panes_layout.insertWidget(0, page, 1)
        self.review_rail_layout.insertWidget(self.review_rail_layout.count() - 1, page.stage_box)
        self._mark_offset_button(die_origin)
        label = "die origin" if die_origin else "current defect"
        self.status.setText(f"Stage connected. Crosshair is at the {label}.")

    def _mark_offset_button(self, die_origin):
        active = None
        if die_origin is True:
            active = "Adjust Die\nOrigin"
        elif die_origin is False:
            active = "Adjust Defect\nLocation"
        for button in getattr(self, "review_rail_buttons", []):
            if active is not None and button.text() == active:
                button.setStyleSheet("QPushButton { background: #d7e4f8; border: 2px solid #1d4f9c; }")
            else:
                button.setStyleSheet("")

    def _close_offset_page(self, apply_result):
        page = getattr(self, "_offset_page", None)
        if page is None:
            return
        self._offset_page = None
        if apply_result and page.result_result is not None:
            self.result = page.result_result
            label = "Die origin" if page.die_origin else "Defect"
            if page.permanent.isChecked():
                self._save_result()
                scope = "saved to the result file"
            else:
                scope = "applied for this review session"
            self._refresh_defects(self.selected_id)
            self.status.setText(f"{label} offset applied to all defects and {scope}.")
        if page.stage_box is not None:
            self.review_rail_layout.removeWidget(page.stage_box)
            page.stage_box.setParent(page)
            page.stage_box.hide()
        self.review_panes_layout.removeWidget(page)
        page.hide()
        page.deleteLater()
        self.pane_splitter.show()
        self.defect_details_bar.show()
        self._mark_offset_button(None)

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
        selection = SensitivityTestSelectionDialog(self.result, self.current_recipe, self)
        if _exec(selection) != QDialog.Accepted:
            return
        previous_filters = deepcopy(self.filters)
        if selection.clear_existing_filters:
            self.filters = default_filter_state()
            self._refresh_defects(self.selected_id)

        def discard_unsaved():
            """Unsaved tuner work never touches the review result or its filters."""
            if selection.clear_existing_filters:
                self.filters = previous_filters
                self._refresh_defects(self.selected_id)
            self.status.setText(
                "Sensitivity Tuner closed without saving. Unsaved changes were discarded."
            )

        dialog = SensitivityTunerDialog(
            self.result,
            self.current_recipe,
            self.result.get("sensitivity_tuner"),
            self,
            initial_test=selection.selected_test,
        )
        if _exec(dialog) != QDialog.Accepted or dialog.result_state is None:
            discard_unsaved()
            return
        if not getattr(dialog, "state_persisted", True):
            discard_unsaved()
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
            snapshot_update_enabled = (
                self.snapshot_mode
                and not complete
                and self.snapshot_update_callback is not None
            )
            self.update_snapshot.setEnabled(snapshot_update_enabled)
            if hasattr(self, "snapshot_rail_update"):
                self.snapshot_rail_update.setEnabled(snapshot_update_enabled)
            if hasattr(self, "snapshot_update_action"):
                self.snapshot_update_action.setEnabled(snapshot_update_enabled)
        for action in self.machine_free_actions:
            action.setEnabled(machine_free)
        sensitivity_ready = bool(self.result.get("sensitivity_data"))
        if hasattr(self, "sensitivity_tuner_button"):
            self.sensitivity_tuner_button.setEnabled(sensitivity_ready)
        if hasattr(self, "map_primary_to_secondary"):
            self.map_primary_to_secondary.setEnabled(sensitivity_ready)
            self.map_secondary_to_primary.setEnabled(sensitivity_ready)
        if hasattr(self, "command_sensitivity_button"):
            self.command_sensitivity_button.setEnabled(sensitivity_ready)
        lot_ready = bool(getattr(self, "_review_lot_ready", False))
        for button in getattr(self, "lot_gated_rail_buttons", []):
            button.setEnabled(lot_ready)
        if hasattr(self, "sensitivity_menu_action"):
            self.sensitivity_menu_action.setEnabled(lot_ready)

    def _save_result(self):
        if self.result.get("placeholder"):
            return
        if self.store and self.result.get("status") != "Running":
            self.result = self.store.save_result(self.result)

    def eventFilter(self, watched, event):
        try:
            header = self.grid.horizontalHeader() if hasattr(self, "grid") else None
        except RuntimeError:
            return False
        if watched is header:
            if event.type() == QEvent.MouseMove and event.buttons() & Qt.LeftButton:
                header.setCursor(Qt.IBeamCursor)
            elif event.type() in (QEvent.MouseButtonRelease, QEvent.Leave):
                header.unsetCursor()
            return False
        try:
            if event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Return, Qt.Key_Enter):
                row = watched.property("manual_class_row")
                if row is not None:
                    self._commit_manual_class(
                        int(row),
                        watched.text(),
                        bool(watched.property("manual_class_advance")),
                    )
                    return True
        except RuntimeError:
            return False
        return super().eventFilter(watched, event)

    def _lock_text_width(self, widget, sample, extra):
        metrics = widget.fontMetrics()
        advance = metrics.horizontalAdvance(sample) if hasattr(metrics, "horizontalAdvance") else metrics.width(sample)
        widget.setFixedWidth(advance + extra)

    def _defect_details_bar(self):
        bar = QWidget()
        bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        bar.setStyleSheet("background: #e4dfd2;")
        row = QHBoxLayout(bar)
        row.setContentsMargins(6, 2, 6, 2)
        row.setSpacing(8)
        row.addWidget(QLabel("DefectID"))
        self.detail_defect_id = QLineEdit()
        self.detail_defect_id.setAlignment(Qt.AlignLeft)
        self.detail_defect_id.returnPressed.connect(self._jump_defect_id)
        self._lock_text_width(self.detail_defect_id, "999999", 16)
        row.addWidget(self.detail_defect_id)
        arrows = QWidget()
        arrow_row = QHBoxLayout(arrows)
        arrow_row.setContentsMargins(0, 0, 0, 0)
        arrow_row.setSpacing(0)
        previous = QPushButton("◀")
        previous.setFixedSize(22, 22)
        previous.setToolTip("Previous defect")
        previous.clicked.connect(lambda _checked=False: self._navigate(-1))
        following = QPushButton("▶")
        following.setFixedSize(22, 22)
        following.setToolTip("Next defect")
        following.clicked.connect(lambda _checked=False: self._navigate(1))
        for button in (previous, following):
            button.setStyleSheet("QPushButton { color: #1d4f9c; font-weight: 700; padding: 0; min-height: 0; }")
            arrow_row.addWidget(button)
        row.addWidget(arrows)
        self.detail_die = QLabel("Die")
        self.detail_rough = QLabel("Roughcode")
        self.detail_cluster = QLabel("ClusterId")
        for label in (self.detail_die, self.detail_rough, self.detail_cluster):
            label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._lock_text_width(self.detail_die, "Die  (-999,999)", 4)
        self._lock_text_width(self.detail_rough, "Roughcode  9999", 4)
        self._lock_text_width(self.detail_cluster, "ClusterId  99999", 4)
        row.addWidget(self.detail_die)
        row.addWidget(self.detail_rough)
        row.addWidget(self.detail_cluster)
        row.addWidget(QLabel("Manual Class"))
        self.detail_manual_class = QComboBox()
        self.detail_manual_class.setEditable(True)
        self._lock_text_width(self.detail_manual_class, "9999", 28)
        self.detail_manual_class.activated.connect(
            lambda _index: self._commit_manual_class(-1, self.detail_manual_class.currentText(), False)
        )
        editor = self.detail_manual_class.lineEdit()
        editor.setProperty("manual_class_row", -1)
        editor.setProperty("manual_class_advance", False)
        editor.installEventFilter(self)
        row.addWidget(self.detail_manual_class)
        self.detail_classify = QPushButton("Classify Defect(s)")
        self.detail_classify.setToolTip("Assign a class code to the current defect or the selected defects.")
        self._lock_text_width(self.detail_classify, "Classify Defect(s)", 28)
        row.addWidget(self.detail_classify)
        row.addStretch(1)
        return bar

    def _jump_defect_id(self):
        try:
            defect_id = int(self.detail_defect_id.text().strip())
        except ValueError:
            return
        if any(item.get("id") == defect_id for item in self.visible_defects):
            self._select_id(defect_id)

    def _sync_defect_details(self):
        if not hasattr(self, "detail_defect_id"):
            return
        defect = next((item for item in self.visible_defects if item.get("id") == self.selected_id), None)
        self.detail_defect_id.blockSignals(True)
        self.detail_defect_id.setText("" if defect is None else str(defect.get("id", "")))
        self.detail_defect_id.blockSignals(False)
        self._lock_text_width(self.detail_defect_id, "999999", 16)
        self._lock_text_width(self.detail_die, "Die  (-999,999)", 4)
        self._lock_text_width(self.detail_rough, "Roughcode  9999", 4)
        self._lock_text_width(self.detail_cluster, "ClusterId  99999", 4)
        self._lock_text_width(self.detail_manual_class, "9999", 28)
        self._lock_text_width(self.detail_classify, "Classify Defect(s)", 28)
        if defect is None:
            self.detail_die.setText("Die")
            self.detail_rough.setText("Roughcode")
            self.detail_cluster.setText("ClusterId")
            self._fill_class_combo(self.detail_manual_class, 0)
            return
        self.detail_die.setText(f"Die  ({defect.get('die_x')},{defect.get('die_y')})")
        self.detail_rough.setText(f"Roughcode  {defect.get('roughbin', 0)}")
        self.detail_cluster.setText(f"ClusterId  {defect.get('cluster_id', 0) or 0}")
        self._fill_class_combo(self.detail_manual_class, defect.get("manual_class", defect.get("class_code", 0)))
        menu = QMenu(self.detail_classify)
        for code in self._known_class_codes():
            menu.addAction(str(code), lambda _checked=False, value=code: self._classify_from_toolbar(value))
        self.detail_classify.setMenu(menu)

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

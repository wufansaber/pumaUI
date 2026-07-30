from __future__ import annotations

from typing import Optional

from ..image_display.dialog import AdvancedOpticsDialog, ImageDisplayWindow, SIMULATED_ALIGNMENT_IMAGES
from ...qt_compat import (
    QCheckBox,
    QColor,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPainter,
    QPen,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    Qt,
    QVBoxLayout,
    QWidget,
)
from ...widgets import ClassicButton


class AlignmentMenuDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Alignment")
        self.setFixedSize(155, 520)
        self.setStyleSheet(
            """
            QDialog {
                background: #d7d4c9;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10px;
            }
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        auto = ClassicButton("Auto Site\nSelection")
        auto.clicked.connect(self._open_auto_site_selection)
        layout.addWidget(auto)

        image_display = ClassicButton("Image\nDisplay")
        image_display.clicked.connect(self._open_image_display)
        layout.addWidget(image_display)
        layout.addSpacing(12)

        select_sites = ClassicButton("Select Sites")
        select_sites.clicked.connect(self._open_select_sites)
        layout.addWidget(select_sites)

        align_wafer = ClassicButton("Align Wafer")
        align_wafer.clicked.connect(lambda: self._set_title_status("Align Wafer"))
        layout.addWidget(align_wafer)

        set_optics = ClassicButton("Set Optics\nand Retrain")
        set_optics.clicked.connect(lambda: self._set_title_status("Set Optics and Retrain"))
        layout.addWidget(set_optics)

        qualify = ClassicButton("Qualify with\nTest Optics")
        qualify.clicked.connect(self._open_qualify_with_test_optics)
        layout.addWidget(qualify)

        manual = ClassicButton("Manual\nAlignment")
        manual.clicked.connect(lambda: self._set_title_status("Manual Alignment"))
        layout.addWidget(manual)
        layout.addStretch(1)

        end = ClassicButton("End")
        end.clicked.connect(self.accept)
        layout.addWidget(end)

    def _open_auto_site_selection(self):
        proceed = QMessageBox.question(
            self,
            "Select Alignment Sites",
            "Valid alignment sites are already defined.\nProceed with Auto Site Selection?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if proceed != QMessageBox.Yes:
            self.setWindowTitle("Alignment - Auto Site Selection cancelled")
            return

        parameters = AutoSiteAlignmentParametersDialog(self)
        parameter_result = parameters.exec() if hasattr(parameters, "exec") else parameters.exec_()
        if parameter_result != QDialog.Accepted:
            self.setWindowTitle("Alignment - Auto Site Selection parameters cancelled")
            return

        dialog = AutoSiteSelectionDialog(self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.setWindowTitle("Alignment - Auto Site Selection complete")

    def _open_image_display(self):
        dialog = ImageDisplayWindow(self)
        dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        self.setWindowTitle("Alignment - Image Display closed")

    def _open_select_sites(self):
        proceed = QMessageBox.question(
            self,
            "Select Alignment Sites",
            "You already have valid Alignment Sites. Reselection of Alignment sites requires\n"
            "that you select your Old Die Origin, or your old High Mag Alignment Site (if available).\n\n"
            "Accurate reselection of this point is very important for ensuring that\n"
            "your wafer map and test data to be reused correctly!\n\n"
            "Do you want to proceed?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if proceed != QMessageBox.Yes:
            self.setWindowTitle("Alignment - Select Sites cancelled")
            return

        dialog = AlignmentImagingModeDialog(self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            sites = SelectAlignmentSitesDialog(dialog.selected_mode, self)
            site_result = sites.exec() if hasattr(sites, "exec") else sites.exec_()
            if site_result == QDialog.Accepted:
                derived = DerivedSiteSelectionDialog(self)
                derived_result = derived.exec() if hasattr(derived, "exec") else derived.exec_()
                if derived_result == QDialog.Accepted:
                    corner = LowMagDieCornerImageDialog(derived.selected_choice, self)
                    corner_result = corner.exec() if hasattr(corner, "exec") else corner.exec_()
                    if corner_result == QDialog.Accepted:
                        self.setWindowTitle(f"Alignment - Derivative site selected ({dialog.selected_mode})")
                    else:
                        self.setWindowTitle(f"Alignment - Sites aligned ({dialog.selected_mode})")
                else:
                    self.setWindowTitle(f"Alignment - Sites aligned ({dialog.selected_mode})")
            else:
                self.setWindowTitle(f"Alignment - Select Sites ready ({dialog.selected_mode})")

    def _open_qualify_with_test_optics(self):
        dialog = QualifyWithTestOpticsDialog(self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            keep_new_data = QMessageBox.question(
                self,
                "Qualify with Test Optics",
                "Alignment qualification is complete.\n\n"
                "Do you want to keep the new alignment data?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            suffix = "with Re-learn" if dialog.relearn_enabled else "without Re-learn"
            data_state = "new data retained" if keep_new_data == QMessageBox.Yes else "new data discarded"
            self.setWindowTitle(f"Alignment - Qualified {suffix}, {data_state}")

    def _set_title_status(self, action: str):
        self.setWindowTitle(f"Alignment - {action} selected")


class AlignmentImagingModeDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Alignment Imaging Mode")
        self.setFixedSize(260, 230)
        self.selected_mode = "DF"
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(
            """
            QDialog {
                background: #d0ccc2;
                color: #111111;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10px;
            }
            QPushButton {
                background: #e7e4da;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-height: 28px;
                padding: 3px 12px;
            }
            QLabel {
                color: #111111;
            }
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 16)
        layout.setSpacing(12)
        description = QLabel("Select the optics template used to define alignment.")
        description.setWordWrap(True)
        layout.addWidget(description)

        df = QPushButton("DF")
        df.clicked.connect(lambda: self._open_parameters("DF"))
        layout.addWidget(df)

        bf = QPushButton("BF")
        bf.clicked.connect(lambda: self._open_parameters("BF"))
        layout.addWidget(bf)
        layout.addStretch(1)

        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        layout.addWidget(cancel, alignment=Qt.AlignRight)

    def _open_parameters(self, mode: str):
        dialog = BFAlignmentParametersDialog(self) if mode == "BF" else AlignmentParametersDialog(mode, self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.selected_mode = mode
            self.accept()


class AlignmentParametersDialog(QDialog):
    def __init__(self, mode: str = "DF", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.mode = mode
        self.setWindowTitle("Alignment Parameters")
        self.setFixedSize(520, 400)
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(
            """
            QDialog {
                background: #cfcac1;
                color: #111111;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10px;
            }
            QPushButton {
                background: #e7e4da;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-height: 26px;
                padding: 2px 12px;
            }
            QComboBox {
                background: #ffffff;
                border: 1px solid #77736b;
                min-height: 24px;
            }
            QFrame#parameterGroup {
                border: 1px solid #8f8b82;
                background: #cfcac1;
            }
            QLabel#groupTitle {
                background: #cfcac1;
                padding: 0 4px;
                font-weight: 600;
            }
            """
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(70, 28, 70, 28)
        root.setSpacing(18)

        row = QHBoxLayout()
        row.setSpacing(14)
        row.addWidget(self._optics_group())
        row.addWidget(self._optics_used_group())
        root.addLayout(row)
        root.addStretch(1)

        footer = QHBoxLayout()
        ok = QPushButton("OK")
        ok.setFixedWidth(112)
        ok.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.setFixedWidth(112)
        cancel.clicked.connect(self.reject)
        footer.addStretch(1)
        footer.addWidget(ok)
        footer.addSpacing(54)
        footer.addWidget(cancel)
        footer.addStretch(1)
        root.addLayout(footer)

    def _optics_group(self) -> QFrame:
        group = QFrame()
        group.setObjectName("parameterGroup")
        group.setFixedSize(215, 255)
        title = QLabel("Optics")
        title.setObjectName("groupTitle")
        title.setParent(group)
        title.move(12, -1)

        layout = QVBoxLayout(group)
        layout.setContentsMargins(18, 20, 18, 14)
        layout.setSpacing(10)
        layout.addWidget(QLabel("Pixel Size"))
        pixel = QComboBox()
        pixel.addItems(["SL610", "SL8685", "SL8686"])
        pixel.setFixedWidth(170)
        layout.addWidget(pixel)
        layout.addSpacing(8)

        layout.addWidget(QLabel("Channel Used\nfor Alignment:"))
        channel = QComboBox()
        channel.addItems(["3 (Center)", "1 (Left)", "2 (Right)"])
        channel.setFixedWidth(170)
        layout.addWidget(channel)
        layout.addSpacing(8)

        advanced = QPushButton("Advanced Optics...")
        advanced.setFixedWidth(170)
        advanced.clicked.connect(self._open_advanced_optics)
        layout.addWidget(advanced)
        layout.addStretch(1)
        return group

    def _optics_used_group(self) -> QFrame:
        group = QFrame()
        group.setObjectName("parameterGroup")
        group.setFixedSize(165, 140)
        title = QLabel("Optics to be used")
        title.setObjectName("groupTitle")
        title.setParent(group)
        title.move(12, -1)

        layout = QVBoxLayout(group)
        layout.setContentsMargins(18, 18, 10, 12)
        user_defined = QRadioButton("User defined")
        user_defined.setChecked(True)
        layout.addWidget(user_defined)
        production = QRadioButton("Primary\nProduction\nTest's")
        production.setEnabled(False)
        layout.addWidget(production)
        layout.addStretch(1)
        return group

    def _open_advanced_optics(self):
        dialog = AdvancedOpticsDialog(self)
        dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()


class AutoSiteAlignmentParametersDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Alignment Parameters")
        self.setFixedSize(500, 540)
        self.keep_old_wafer_center = True
        self.use_primary_production_test = False
        self._build_ui()
        self._update_production_enabled()

    def _build_ui(self):
        self.setStyleSheet(
            """
            QDialog {
                background: #cfcac1;
                color: #111111;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10px;
            }
            QPushButton {
                background: #e7e4da;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-height: 26px;
                padding: 2px 12px;
            }
            QComboBox {
                background: #ffffff;
                border: 1px solid #77736b;
                min-height: 24px;
            }
            QComboBox:disabled {
                color: #8a867e;
                background: #d8d4ca;
            }
            QFrame#parameterGroup {
                border: 1px solid #8f8b82;
                background: #cfcac1;
            }
            QLabel#groupTitle {
                background: #cfcac1;
                padding: 0 4px;
                font-weight: 600;
            }
            """
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(42, 28, 42, 24)
        root.setSpacing(14)

        top = QHBoxLayout()
        top.setSpacing(12)
        top.addWidget(self._optics_group())
        top.addWidget(self._optics_used_group(), 0, Qt.AlignTop)
        root.addLayout(top)

        production_row = QHBoxLayout()
        production_row.addWidget(QLabel("Primary Production Test:"))
        self.production_test = QComboBox()
        self.production_test.addItems(["1", "2", "3"])
        self.production_test.setFixedWidth(100)
        production_row.addWidget(self.production_test)
        production_row.addStretch(1)
        root.addLayout(production_row)

        self.keep_center = QCheckBox("Keep Old Wafer Center")
        self.keep_center.setChecked(True)
        root.addWidget(self.keep_center)

        warning = QLabel(
            "If you uncheck this box\n"
            "- Use EDIT MAP to verify die map.\n"
            "- Verify all test sample plans.\n"
            "- DSA may not work."
        )
        warning.setContentsMargins(22, 0, 0, 0)
        root.addWidget(warning)
        root.addStretch(1)

        footer = QHBoxLayout()
        footer.addStretch(1)
        ok = QPushButton("OK")
        ok.setFixedWidth(105)
        ok.clicked.connect(self._accept_parameters)
        footer.addWidget(ok)
        footer.addSpacing(50)
        cancel = QPushButton("Cancel")
        cancel.setFixedWidth(105)
        cancel.clicked.connect(self.reject)
        footer.addWidget(cancel)
        footer.addStretch(1)
        root.addLayout(footer)

    def _optics_group(self) -> QFrame:
        group = QFrame()
        group.setObjectName("parameterGroup")
        group.setFixedSize(220, 250)
        title = QLabel("Optics")
        title.setObjectName("groupTitle")
        title.setParent(group)
        title.move(12, -1)

        layout = QVBoxLayout(group)
        layout.setContentsMargins(18, 20, 18, 14)
        layout.setSpacing(10)
        layout.addWidget(QLabel("Pixel Size"))
        self.pixel_size = QComboBox()
        self.pixel_size.addItems(["SL610", "SL8685", "SL8686"])
        self.pixel_size.setFixedWidth(170)
        layout.addWidget(self.pixel_size)
        layout.addSpacing(8)

        layout.addWidget(QLabel("Channel Used\nfor Alignment:"))
        self.channel = QComboBox()
        self.channel.addItems(["3 (Center)", "1 (Left)", "2 (Right)"])
        self.channel.setFixedWidth(170)
        layout.addWidget(self.channel)
        layout.addSpacing(8)

        advanced = QPushButton("Advanced Optics...")
        advanced.setFixedWidth(170)
        advanced.clicked.connect(self._open_advanced_optics)
        layout.addWidget(advanced)
        layout.addStretch(1)
        return group

    def _optics_used_group(self) -> QFrame:
        group = QFrame()
        group.setObjectName("parameterGroup")
        group.setFixedSize(165, 150)
        title = QLabel("Optics to be used")
        title.setObjectName("groupTitle")
        title.setParent(group)
        title.move(12, -1)

        layout = QVBoxLayout(group)
        layout.setContentsMargins(18, 18, 10, 12)
        self.user_defined = QRadioButton("User defined")
        self.user_defined.setChecked(True)
        self.production_optics = QRadioButton("Primary\nProduction\nTest's")
        self.user_defined.toggled.connect(self._update_production_enabled)
        self.production_optics.toggled.connect(self._update_production_enabled)
        layout.addWidget(self.user_defined)
        layout.addWidget(self.production_optics)
        layout.addStretch(1)
        return group

    def _update_production_enabled(self):
        if hasattr(self, "production_test"):
            self.production_test.setEnabled(self.production_optics.isChecked())

    def _open_advanced_optics(self):
        dialog = AdvancedOpticsDialog(self)
        dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()

    def _accept_parameters(self):
        self.keep_old_wafer_center = self.keep_center.isChecked()
        self.use_primary_production_test = self.production_optics.isChecked()
        self.accept()


class BFAlignmentParametersDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("BF Alignment Parameters")
        self.setFixedSize(430, 500)
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(
            """
            QDialog {
                background: #cfcac1;
                color: #111111;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10px;
            }
            QPushButton {
                background: #e7e4da;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-height: 24px;
                padding: 2px 10px;
            }
            QComboBox, QDoubleSpinBox, QSpinBox {
                background: #ffffff;
                border: 1px solid #77736b;
                min-height: 22px;
            }
            QComboBox:disabled {
                background: #d5d1c8;
                color: #7d7972;
            }
            QFrame#parameterGroup {
                border: 1px solid #8f8b82;
                background: #cfcac1;
            }
            QLabel#groupTitle {
                background: #cfcac1;
                padding: 0 4px;
                font-weight: 600;
            }
            """
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 28, 18, 18)
        root.setSpacing(12)

        root.addWidget(self._alignment_type_group())
        optics_row = QHBoxLayout()
        optics_row.setSpacing(28)
        self.low_mag_group = self._optics_group("Optics - Low Mag", "1.000 (10X)")
        self.high_mag_group = self._optics_group("Optics - High Mag", "0.200 (50X)")
        optics_row.addWidget(self.low_mag_group)
        optics_row.addWidget(self.high_mag_group)
        root.addLayout(optics_row)

        footer = QHBoxLayout()
        footer.addStretch(1)
        ok = QPushButton("OK")
        ok.setFixedWidth(92)
        ok.clicked.connect(self.accept)
        footer.addWidget(ok)
        footer.addSpacing(48)
        cancel = QPushButton("Cancel")
        cancel.setFixedWidth(92)
        cancel.clicked.connect(self.reject)
        footer.addWidget(cancel)
        footer.addStretch(1)
        root.addLayout(footer)

    def _alignment_type_group(self) -> QFrame:
        group = QFrame()
        group.setObjectName("parameterGroup")
        group.setFixedHeight(92)
        title = QLabel("Alignment Type")
        title.setObjectName("groupTitle")
        title.setParent(group)
        title.move(12, -1)

        layout = QVBoxLayout(group)
        layout.setContentsMargins(18, 18, 12, 10)
        self.dual_mag = QRadioButton("Standard Dual Magnification (low/high)")
        self.dual_mag.setChecked(True)
        self.single_mag = QRadioButton("Single Magnification (low=high)")
        self.dual_mag.toggled.connect(self._update_magnification_mode)
        layout.addWidget(self.dual_mag)
        layout.addWidget(self.single_mag)
        return group

    def _optics_group(self, title_text: str, pixel_size: str) -> QFrame:
        group = QFrame()
        group.setObjectName("parameterGroup")
        group.setFixedSize(170, 220)
        title = QLabel(title_text)
        title.setObjectName("groupTitle")
        title.setParent(group)
        title.move(12, -1)

        layout = QVBoxLayout(group)
        layout.setContentsMargins(14, 18, 14, 12)
        layout.setSpacing(5)

        layout.addWidget(QLabel("Imaging Mode"))
        imaging = QComboBox()
        imaging.addItem("BrightField")
        imaging.setEnabled(False)
        layout.addWidget(imaging)

        layout.addWidget(QLabel("Pixel Size"))
        pixel = QComboBox()
        pixel.addItems([pixel_size, "0.500 (20X)", "0.100 (100X)"])
        layout.addWidget(pixel)

        layout.addWidget(QLabel("Focus Offset"))
        focus = QDoubleSpinBox()
        focus.setDecimals(3)
        focus.setRange(-50.0, 50.0)
        focus.setSingleStep(0.001)
        focus.setValue(0.000)
        focus.setSuffix(" um")
        layout.addWidget(focus)

        layout.addWidget(QLabel("Aperture"))
        aperture = QSpinBox()
        aperture.setRange(0, 100)
        aperture.setValue(20)
        aperture.setSuffix(" %")
        layout.addWidget(aperture)

        advanced = QPushButton("Advanced Settings")
        advanced.clicked.connect(self._open_advanced_optics)
        layout.addWidget(advanced)
        return group

    def _update_magnification_mode(self, dual_enabled: bool):
        self.high_mag_group.setEnabled(dual_enabled)

    def _open_advanced_optics(self):
        dialog = AdvancedOpticsDialog(self)
        dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()


class QualifyWithTestOpticsDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Alignment Parameters")
        self.setFixedSize(610, 465)
        self.relearn_enabled = False
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(
            """
            QDialog {
                background: #cfcac1;
                color: #111111;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10px;
            }
            QPushButton {
                background: #e7e4da;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-height: 26px;
                padding: 2px 12px;
            }
            QComboBox {
                background: #ffffff;
                border: 1px solid #77736b;
                min-height: 24px;
            }
            QComboBox:disabled, QPushButton:disabled {
                color: #8a867e;
                background: #d8d4ca;
            }
            QFrame#parameterGroup {
                border: 1px solid #8f8b82;
                background: #cfcac1;
            }
            QLabel#groupTitle {
                background: #cfcac1;
                padding: 0 4px;
                font-weight: 600;
            }
            """
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(70, 34, 70, 28)
        root.setSpacing(18)

        top = QHBoxLayout()
        top.setSpacing(16)
        top.addWidget(self._optics_group())
        right = QVBoxLayout()
        right.addWidget(self._optics_used_group())
        self.relearn = QCheckBox("Re-learn")
        self.relearn.setEnabled(True)
        right.addSpacing(16)
        right.addWidget(self.relearn)
        right.addStretch(1)
        top.addLayout(right)
        root.addLayout(top)

        production_row = QHBoxLayout()
        production_row.addStretch(1)
        production_row.addWidget(QLabel("Primary Production Test:"))
        self.production_test = QComboBox()
        self.production_test.addItems(["1", "2", "3"])
        self.production_test.setFixedWidth(100)
        production_row.addWidget(self.production_test)
        production_row.addStretch(1)
        root.addLayout(production_row)
        root.addStretch(1)

        footer = QHBoxLayout()
        footer.addStretch(1)
        ok = QPushButton("OK")
        ok.setFixedWidth(112)
        ok.clicked.connect(self._accept_parameters)
        footer.addWidget(ok)
        footer.addSpacing(64)
        cancel = QPushButton("Cancel")
        cancel.setFixedWidth(112)
        cancel.clicked.connect(self.reject)
        footer.addWidget(cancel)
        footer.addStretch(1)
        root.addLayout(footer)

    def _optics_group(self) -> QFrame:
        group = QFrame()
        group.setObjectName("parameterGroup")
        group.setFixedSize(230, 260)
        title = QLabel("Optics")
        title.setObjectName("groupTitle")
        title.setParent(group)
        title.move(12, -1)

        layout = QVBoxLayout(group)
        layout.setContentsMargins(20, 20, 20, 14)
        layout.setSpacing(10)
        layout.addWidget(QLabel("Pixel Size"))
        pixel = QComboBox()
        pixel.addItems(["SL610"])
        pixel.setEnabled(False)
        pixel.setFixedWidth(170)
        layout.addWidget(pixel)
        layout.addSpacing(8)

        layout.addWidget(QLabel("Channel Used\nfor Alignment:"))
        channel = QComboBox()
        channel.addItems(["3 (Center)", "1 (Left)", "2 (Right)"])
        channel.setFixedWidth(170)
        layout.addWidget(channel)
        layout.addSpacing(8)

        advanced = QPushButton("Advanced Optics...")
        advanced.setEnabled(False)
        advanced.setFixedWidth(170)
        layout.addWidget(advanced)
        layout.addStretch(1)
        return group

    def _optics_used_group(self) -> QFrame:
        group = QFrame()
        group.setObjectName("parameterGroup")
        group.setFixedSize(195, 145)
        title = QLabel("Optics to be used")
        title.setObjectName("groupTitle")
        title.setParent(group)
        title.move(12, -1)

        layout = QVBoxLayout(group)
        layout.setContentsMargins(18, 18, 10, 12)
        user_defined = QRadioButton("User defined")
        user_defined.setEnabled(False)
        layout.addWidget(user_defined)
        production = QRadioButton("Primary\nProduction\nTest's")
        production.setChecked(True)
        layout.addWidget(production)
        layout.addStretch(1)
        return group

    def _accept_parameters(self):
        self.relearn_enabled = self.relearn.isChecked()
        self.accept()


class AlignmentSettingsDialog(QDialog):
    def __init__(
        self,
        use_pattern_matching: bool = True,
        high_precision_alignment: bool = False,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Alignment Settings")
        self.setFixedSize(390, 190)
        self.use_pattern_matching = use_pattern_matching
        self.high_precision_alignment = high_precision_alignment
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(
            """
            QDialog {
                background: #cfcac1;
                color: #111111;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10px;
            }
            QPushButton {
                background: #e7e4da;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-height: 24px;
                padding: 2px 18px;
            }
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(42, 28, 42, 20)
        layout.setSpacing(10)

        self.pattern_matching = QCheckBox("Use Pattern Matching for die corner selection")
        self.pattern_matching.setChecked(self.use_pattern_matching)
        layout.addWidget(self.pattern_matching)

        self.high_precision = QCheckBox("High Precision Alignment")
        self.high_precision.setChecked(self.high_precision_alignment)
        self.high_precision.setEnabled(True)
        layout.addWidget(self.high_precision)

        footer = QHBoxLayout()
        footer.addStretch(1)
        ok = QPushButton("OK")
        ok.setFixedWidth(100)
        ok.clicked.connect(self._accept_settings)
        footer.addWidget(ok)
        footer.addSpacing(46)
        cancel = QPushButton("Cancel")
        cancel.setFixedWidth(100)
        cancel.clicked.connect(self.reject)
        footer.addWidget(cancel)
        footer.addStretch(1)
        layout.addStretch(1)
        layout.addLayout(footer)

    def _accept_settings(self):
        self.use_pattern_matching = self.pattern_matching.isChecked()
        self.high_precision_alignment = self.high_precision.isChecked()
        self.accept()


class SelectAlignmentSitesDialog(QDialog):
    def __init__(self, mode: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.mode = mode
        self.marked_sites: list[tuple[float, float]] = []
        self.site_images = ["", ""]
        self.current_site_index = 0
        self.focus_offset = 0.000
        self.aligned = False
        self.simulated_images = list(SIMULATED_ALIGNMENT_IMAGES)
        self.current_simulated_image = self.simulated_images[0]
        self.generated_image_count = 0
        self.use_pattern_matching = True
        self.high_precision_alignment = False
        self.setWindowTitle("Select Alignment Sites")
        self.resize(1040, 760)
        self.setMinimumSize(940, 680)
        self._build_ui()
        self._refresh_state()

    def _build_ui(self):
        self.setStyleSheet(
            """
            QDialog {
                background: #e7e5d5;
                color: #111111;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10px;
            }
            QPushButton {
                background: #e7e4da;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-height: 22px;
                padding: 2px 10px;
            }
            QFrame#rightPanel, QFrame#bottomPanel {
                border: 1px solid #b8b3a5;
                background: #ece9d8;
            }
            QTableWidget {
                background: #fbfaf0;
                gridline-color: #bdb8aa;
            }
            QDoubleSpinBox, QComboBox {
                background: #ffffff;
                border: 1px solid #8f8b82;
                min-height: 20px;
            }
            """
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        content = QHBoxLayout()
        content.setSpacing(8)
        self.wafer_view = AlignmentSiteCanvas(self)
        content.addWidget(self.wafer_view, 1)
        content.addWidget(self._right_panel())
        root.addLayout(content, 1)

        bottom = QFrame()
        bottom.setObjectName("bottomPanel")
        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.setContentsMargins(8, 4, 8, 4)
        bottom_layout.setSpacing(4)
        self.cursor_label = QLabel()
        bottom_layout.addWidget(self.cursor_label)
        self.instruction_label = QLabel()
        self.instruction_label.setWordWrap(True)
        bottom_layout.addWidget(self.instruction_label)
        root.addWidget(bottom)

        footer = QHBoxLayout()
        self.prev_button = QPushButton("<< Prev")
        self.prev_button.clicked.connect(self._prev_site)
        footer.addWidget(self.prev_button)
        self.mark_button = QPushButton("Mark Site >>")
        self.mark_button.clicked.connect(self._mark_site)
        footer.addWidget(self.mark_button)
        self.next_button = QPushButton("Next >>")
        self.next_button.clicked.connect(self._next_site)
        footer.addWidget(self.next_button)
        self.align_button = QPushButton("Align")
        self.align_button.clicked.connect(self._align_sites)
        footer.addWidget(self.align_button)
        self.finish_button = QPushButton("Finish")
        self.finish_button.clicked.connect(self._finish_sites)
        footer.addWidget(self.finish_button)
        footer.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        footer.addWidget(cancel)
        root.addLayout(footer)

    def _right_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("rightPanel")
        panel.setFixedWidth(250)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        layout.addWidget(self._select_sites_orientation_group())

        title = QLabel("Site Coordinates")
        title.setStyleSheet("color: #1641d8;")
        layout.addWidget(title)
        self.site_table = QTableWidget(2, 4)
        self.site_table.setHorizontalHeaderLabels(["Site", "X", "Y", "Image"])
        self.site_table.verticalHeader().setVisible(False)
        self.site_table.setFixedHeight(92)
        for row in range(2):
            self.site_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            for column in range(1, 4):
                self.site_table.setItem(row, column, QTableWidgetItem(""))
        layout.addWidget(self.site_table)

        focus_title = QLabel("Focus Offset")
        focus_title.setStyleSheet("color: #1641d8;")
        layout.addWidget(focus_title)
        focus_row = QHBoxLayout()
        self.focus_spin = QDoubleSpinBox()
        self.focus_spin.setDecimals(3)
        self.focus_spin.setRange(-5.000, 5.000)
        self.focus_spin.setSingleStep(0.001)
        self.focus_spin.setSuffix(" um")
        self.focus_spin.valueChanged.connect(self._set_focus_from_spin)
        focus_row.addWidget(self.focus_spin)
        focus_button = QPushButton("Focus Offset")
        focus_button.clicked.connect(lambda: self.focus_spin.setFocus())
        focus_row.addWidget(focus_button)
        layout.addLayout(focus_row)

        image_display = QPushButton("Image Display...")
        image_display.clicked.connect(self._open_image_display)
        layout.addWidget(image_display)

        self.sim_image_label = QLabel()
        self.sim_image_label.setWordWrap(True)
        layout.addWidget(self.sim_image_label)
        generate_image = QPushButton("Acquire Sim Image")
        generate_image.clicked.connect(self._generate_simulated_image)
        layout.addWidget(generate_image)

        quality = QLabel("Alignment Quality")
        quality.setStyleSheet("color: #1641d8;")
        layout.addWidget(quality)
        self.quality_table = QTableWidget(3, 3)
        self.quality_table.setHorizontalHeaderLabels(["Site", "X", "Y"])
        self.quality_table.verticalHeader().setVisible(False)
        self.quality_table.setFixedHeight(96)
        for row, label in enumerate(["First", "Second", "Result"]):
            self.quality_table.setItem(row, 0, QTableWidgetItem(label))
            self.quality_table.setItem(row, 1, QTableWidgetItem(""))
            self.quality_table.setItem(row, 2, QTableWidgetItem(""))
        layout.addWidget(self.quality_table)

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        layout.addStretch(1)

        legend = QLabel(
            "<span style='color:#ff2d2d'>□</span> Current Position<br>"
            "<span style='color:#20b64a'>□</span> Marked Site<br>"
            "<span style='color:#6266ff'>□</span> Alignment Box"
        )
        layout.addWidget(legend)
        return panel

    def _select_sites_orientation_group(self) -> QFrame:
        group = QFrame()
        group.setObjectName("rightPanel")
        layout = QGridLayout(group)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setHorizontalSpacing(4)
        layout.setVerticalSpacing(4)

        title = QLabel("Orientation")
        title.setStyleSheet("color: #111111; font-weight: 600;")
        layout.addWidget(title, 0, 0, 1, 4)

        layout.addWidget(QLabel("Edit/Define Orientation:"), 1, 0, 1, 2)
        orientation = QComboBox()
        orientation.addItems(["Down (180 deg.)"])
        orientation.setEnabled(False)
        layout.addWidget(orientation, 1, 2, 1, 2)

        same = QRadioButton("Same as First Test")
        same.setChecked(True)
        layout.addWidget(same, 2, 0, 1, 4)
        down = QRadioButton("Down (180 deg.)")
        down.setEnabled(False)
        layout.addWidget(down, 3, 0, 1, 4)

        orientations = [("Up:", "Undefined"), ("Right:", "Undefined"), ("Down:", "Valid"), ("Left:", "Undefined")]
        for index, (label, state) in enumerate(orientations):
            row = 4 + index // 2
            column = (index % 2) * 2
            check = QCheckBox(label)
            layout.addWidget(check, row, column)
            state_button = QPushButton(state)
            state_button.setFixedWidth(72)
            state_button.setEnabled(False)
            layout.addWidget(state_button, row, column + 1)

        delete_alignment = QPushButton("Delete Alignment")
        delete_alignment.setEnabled(False)
        layout.addWidget(delete_alignment, 6, 0, 1, 2)
        settings = QPushButton("Settings...")
        settings.clicked.connect(self._open_alignment_settings)
        layout.addWidget(settings, 6, 2, 1, 2)

        self.high_precision_status = QLabel("High Precision Alignment: Off")
        self.high_precision_status.setStyleSheet("color: #1641d8;")
        layout.addWidget(self.high_precision_status, 7, 0, 1, 4)
        return group

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_F7:
            self._adjust_focus(-0.001)
            return
        if key == Qt.Key_F8:
            self._adjust_focus(0.001)
            return
        if key == Qt.Key_Left:
            self.move_stage(-100, 0)
            return
        if key == Qt.Key_Right:
            self.move_stage(100, 0)
            return
        if key == Qt.Key_Up:
            self.move_stage(0, 100)
            return
        if key == Qt.Key_Down:
            self.move_stage(0, -100)
            return
        super().keyPressEvent(event)

    def move_stage(self, dx: float, dy: float):
        x_value, y_value = self.wafer_view.stage_position
        self.wafer_view.stage_position = (x_value + dx, y_value + dy)
        self.wafer_view.update()
        self._refresh_state()

    def _set_focus_from_spin(self, value: float):
        self.focus_offset = value
        self.wafer_view.focus_offset = value
        self._refresh_state()
        self.wafer_view.update()

    def _adjust_focus(self, delta: float):
        self.focus_spin.setValue(self.focus_spin.value() + delta)

    def _mark_site(self):
        x_value, y_value = self.wafer_view.stage_position
        row = self.current_site_index
        if row == 1:
            if not self.marked_sites:
                QMessageBox.warning(self, "Select Alignment Sites", "Mark alignment site #1 before selecting site #2.")
                return
            first_x, first_y = self.marked_sites[0]
            if x_value - first_x < 200:
                QMessageBox.warning(
                    self,
                    "Alignment Site Limit",
                    "The second alignment site must be at least 200 um to the right of the first site.",
                )
                return
            if abs(y_value - first_y) > 2500:
                QMessageBox.warning(
                    self,
                    "Alignment Site Limit",
                    "Select the same high contrast area on an adjacent die.",
                )
                return

        image_name = self.current_simulated_image
        if row < len(self.marked_sites):
            self.marked_sites[row] = (x_value, y_value)
        else:
            self.marked_sites.append((x_value, y_value))
        self.site_images[row] = image_name
        self.aligned = False
        self.wafer_view.marked_sites = list(self.marked_sites)
        self.site_table.setItem(row, 1, QTableWidgetItem(f"{x_value:.3f}"))
        self.site_table.setItem(row, 2, QTableWidgetItem(f"{y_value:.3f}"))
        self.site_table.setItem(row, 3, QTableWidgetItem(image_name))
        self.quality_table.setItem(row, 1, QTableWidgetItem(f"{x_value:.1f}"))
        self.quality_table.setItem(row, 2, QTableWidgetItem(f"{y_value:.1f}"))
        self.quality_table.setItem(2, 1, QTableWidgetItem(""))
        self.quality_table.setItem(2, 2, QTableWidgetItem(""))
        self._advance_simulated_image()
        self._refresh_state()
        self.wafer_view.update()

    def _prev_site(self):
        if self.current_site_index == 0:
            return
        self.current_site_index = 0
        self._move_stage_to_current_site()
        self._refresh_state()

    def _next_site(self):
        if self.current_site_index == 0:
            if len(self.marked_sites) < 1:
                QMessageBox.warning(self, "Select Alignment Sites", "Mark alignment site #1 before continuing.")
                return
            self.current_site_index = 1
            self._move_stage_to_current_site()
            self._refresh_state()
            return
        self.status_label.setText("Click Finish to proceed beyond alignment site #2.")

    def _move_stage_to_current_site(self):
        if self.current_site_index < len(self.marked_sites):
            self.wafer_view.stage_position = self.marked_sites[self.current_site_index]
            self.wafer_view.update()
        elif self.current_site_index == 1 and self.marked_sites:
            first_x, first_y = self.marked_sites[0]
            self.wafer_view.stage_position = (first_x + 1000.0, first_y)
            self.wafer_view.update()

    def _align_sites(self):
        if len(self.marked_sites) < 2:
            QMessageBox.warning(self, "Select Alignment Sites", "Mark two alignment sites before clicking Align.")
            return
        if not self._has_valid_second_site():
            return
        self.aligned = True
        self.quality_table.setItem(2, 1, QTableWidgetItem("Scanned"))
        result = "High Precision" if self.high_precision_alignment else "Complete"
        self.quality_table.setItem(2, 2, QTableWidgetItem(result))
        suffix = " using High Precision Alignment" if self.high_precision_alignment else ""
        self.status_label.setText(f"Wafer scanned. Alignment completed{suffix} and site coordinates/images recorded.")
        self._refresh_state()
        self.wafer_view.update()

    def _finish_sites(self):
        if len(self.marked_sites) < 2:
            QMessageBox.warning(self, "Select Alignment Sites", "Mark both alignment sites before clicking Finish.")
            return
        if not self._has_valid_second_site():
            return
        if not self.aligned:
            self._align_sites()
        self.accept()

    def _has_valid_second_site(self) -> bool:
        first_x, first_y = self.marked_sites[0]
        second_x, second_y = self.marked_sites[1]
        if second_x - first_x < 200:
            QMessageBox.warning(
                self,
                "Alignment Site Limit",
                "Alignment site #2 must remain at least 200 um to the right of site #1.",
            )
            return False
        if abs(second_y - first_y) > 2500:
            QMessageBox.warning(
                self,
                "Alignment Site Limit",
                "Alignment site #2 must remain in the same high contrast area on an adjacent die.",
            )
            return False
        return True

    def _open_alignment_settings(self):
        dialog = AlignmentSettingsDialog(
            self.use_pattern_matching,
            self.high_precision_alignment,
            self,
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.use_pattern_matching = dialog.use_pattern_matching
            self.high_precision_alignment = dialog.high_precision_alignment
            state = "On" if self.high_precision_alignment else "Off"
            self.high_precision_status.setText(f"High Precision Alignment: {state}")
            self.status_label.setText(f"High Precision Alignment {state.lower()}.")

    def _open_image_display(self):
        dialog = ImageDisplayWindow(self)
        dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        selected = dialog.current_image.currentText()
        if selected:
            self.current_simulated_image = selected
        self.status_label.setText("Inspection image acquired from Image Display Window.")
        self._refresh_state()

    def _generate_simulated_image(self):
        self.generated_image_count += 1
        x_value, y_value = self.wafer_view.stage_position
        image_name = f"Sim Cross Mark Capture {self.generated_image_count} ({x_value:.0f},{y_value:.0f})"
        self.simulated_images.append(image_name)
        self.current_simulated_image = image_name
        self.status_label.setText("Synthetic wafer cross-mark image generated for the current stage position.")
        self._refresh_state()

    def _advance_simulated_image(self):
        if not self.simulated_images:
            return
        try:
            index = self.simulated_images.index(self.current_simulated_image)
        except ValueError:
            index = -1
        self.current_simulated_image = self.simulated_images[(index + 1) % len(self.simulated_images)]

    def _refresh_state(self):
        x_value, y_value = self.wafer_view.stage_position
        self.cursor_label.setText(
            f"Cursor X: {x_value:.3f} um    Cursor Y: {y_value:.3f} um    Focus Offset: {self.focus_offset:.3f} um"
        )
        self.sim_image_label.setText(f"Current Image: {self.current_simulated_image}")
        self.site_table.selectRow(self.current_site_index)
        if self.aligned:
            instruction = "Alignment completed. Click Finish to return to the Alignment menu."
        elif self.current_site_index == 0 and len(self.marked_sites) == 0:
            instruction = (
                "Select alignment site #1 inside the blue alignment box. Move the stage/crosshair, "
                "then click Mark Site."
            )
            self.status_label.setText("Select alignment site #1.")
        elif self.current_site_index == 0:
            instruction = (
                "Alignment site #1 is selected. Click Next to keep it, or move the stage and click Mark Site "
                "to reselect/adjust this site."
            )
            self.status_label.setText("Review or adjust alignment site #1.")
        elif len(self.marked_sites) < 2:
            instruction = (
                "Select alignment site #2 on the same high contrast area of an adjacent die at least 200 um "
                "to the right of site #1, then click Mark Site."
            )
            self.status_label.setText("Select alignment site #2.")
        else:
            instruction = (
                "Alignment site #2 is selected. Click Finish to proceed beyond site #2, click Align to scan now, "
                "or click Prev to reselect a previous site."
            )
            self.status_label.setText("Ready to align or finish.")
        self.instruction_label.setText(instruction)
        self.prev_button.setEnabled(self.current_site_index > 0)
        self.next_button.setEnabled(self.current_site_index == 0 and len(self.marked_sites) >= 1)
        self.align_button.setEnabled(len(self.marked_sites) == 2 and not self.aligned)
        self.finish_button.setEnabled(len(self.marked_sites) == 2)

    def note_snap(self):
        self.status_label.setText("Ctrl+click snap applied to nearest point/corner.")


class AlignmentSiteCanvas(QWidget):
    def __init__(self, dialog: SelectAlignmentSitesDialog):
        super().__init__(dialog)
        self.dialog = dialog
        self.stage_position = (-1800.0, 1200.0)
        self.marked_sites: list[tuple[float, float]] = []
        self.focus_offset = 0.000
        self.setMinimumSize(620, 540)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        point = self._event_position(event)
        self.stage_position = self._stage_from_screen(point.x(), point.y())
        if event.modifiers() & Qt.ControlModifier:
            x_value, y_value = self.stage_position
            self.stage_position = (round(x_value / 100.0) * 100.0, round(y_value / 100.0) * 100.0)
            self.dialog.note_snap()
        self.dialog._refresh_state()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#858583"))

        margin = 24
        size = min(self.width() - 48, self.height() - 72)
        left = margin
        top = 16
        if self.width() > size + 48:
            left = (self.width() - size) // 2
        wafer_rect = (left, top, size, size)
        painter.setBrush(QColor("#ffffff"))
        painter.setPen(QPen(QColor("#666666"), 1))
        painter.drawEllipse(*wafer_rect)

        box_left = left + int(size * 0.20)
        box_top = top + int(size * 0.30)
        box_width = int(size * 0.60)
        box_height = int(size * 0.34)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor("#6266ff"), 1))
        painter.drawRect(box_left, box_top, box_width, box_height)

        painter.setPen(QPen(QColor("#c9c9c9"), 1, Qt.DotLine))
        for index in range(1, 12):
            x_line = box_left + index * box_width // 12
            y_line = box_top + index * box_height // 12
            painter.drawLine(x_line, box_top, x_line, box_top + box_height)
            painter.drawLine(box_left, y_line, box_left + box_width, y_line)

        for index, (x_value, y_value) in enumerate(self.marked_sites, start=1):
            x_screen, y_screen = self._screen_from_stage(x_value, y_value)
            painter.setPen(QPen(QColor("#20b64a"), 2))
            painter.drawLine(x_screen - 9, y_screen, x_screen + 9, y_screen)
            painter.drawLine(x_screen, y_screen - 9, x_screen, y_screen + 9)
            painter.drawText(x_screen + 7, y_screen - 7, str(index))

        x_screen, y_screen = self._screen_from_stage(*self.stage_position)
        painter.setPen(QPen(QColor("#ff2d2d"), 1))
        painter.drawLine(x_screen - 12, y_screen, x_screen + 12, y_screen)
        painter.drawLine(x_screen, y_screen - 12, x_screen, y_screen + 12)
        painter.setPen(QPen(QColor("#111111"), 1))
        painter.drawText(left, top + size + 22, f"{self.dialog.mode} Single Mag")
        painter.drawText(left, top + size + 40, "Blue box marks valid alignment target area. Ctrl+click snaps to nearest point/corner.")

    def _screen_from_stage(self, x_value: float, y_value: float) -> tuple[int, int]:
        margin = 24
        size = min(self.width() - 48, self.height() - 72)
        left = margin if self.width() <= size + 48 else (self.width() - size) // 2
        top = 16
        box_left = left + int(size * 0.20)
        box_top = top + int(size * 0.30)
        box_width = int(size * 0.60)
        box_height = int(size * 0.34)
        x_screen = box_left + int((x_value + 5000.0) / 10000.0 * box_width)
        y_screen = box_top + int((5000.0 - y_value) / 10000.0 * box_height)
        return x_screen, y_screen

    def _stage_from_screen(self, x_screen: float, y_screen: float) -> tuple[float, float]:
        margin = 24
        size = min(self.width() - 48, self.height() - 72)
        left = margin if self.width() <= size + 48 else (self.width() - size) // 2
        top = 16
        box_left = left + int(size * 0.20)
        box_top = top + int(size * 0.30)
        box_width = int(size * 0.60)
        box_height = int(size * 0.34)
        x_clamped = max(box_left, min(box_left + box_width, x_screen))
        y_clamped = max(box_top, min(box_top + box_height, y_screen))
        x_value = ((x_clamped - box_left) / box_width) * 10000.0 - 5000.0
        y_value = 5000.0 - ((y_clamped - box_top) / box_height) * 10000.0
        return x_value, y_value

    @staticmethod
    def _event_position(event):
        return event.position() if hasattr(event, "position") else event.pos()


class DerivedSiteSelectionDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.selected_choice = "Select Die Origin"
        self.apply_site_offset = False
        self.setWindowTitle("Derived Site Selection")
        self.setFixedSize(360, 310)
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(
            """
            QDialog {
                background: #ece9d8;
                color: #111111;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10px;
            }
            QPushButton {
                background: #f1efe3;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-height: 24px;
                padding: 2px 18px;
            }
            QFrame#choiceGroup {
                border: 1px solid #d8d2bc;
                background: #ece9d8;
            }
            """
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 28, 26, 20)
        root.setSpacing(16)

        group = QFrame()
        group.setObjectName("choiceGroup")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(22, 18, 22, 16)
        title = QLabel("Choices")
        title.setStyleSheet("color: #1641d8; font-size: 13px;")
        layout.addWidget(title)

        old_corner = QRadioButton("Select Old Die Corner")
        old_corner.setEnabled(False)
        layout.addWidget(old_corner)
        self.die_origin = QRadioButton("Select Die Origin")
        self.die_origin.setChecked(True)
        layout.addWidget(self.die_origin)
        self.site_offset = QCheckBox("Apply Site Offset")
        self.site_offset.setEnabled(False)
        layout.addWidget(self.site_offset)
        root.addWidget(group)

        ok = QPushButton("OK")
        ok.setFixedWidth(130)
        ok.clicked.connect(self._accept_choice)
        root.addWidget(ok, alignment=Qt.AlignCenter)

    def _accept_choice(self):
        self.selected_choice = "Select Die Origin" if self.die_origin.isChecked() else "Select Old Die Corner"
        self.apply_site_offset = self.site_offset.isChecked()
        self.accept()


class LowMagDieCornerImageDialog(QDialog):
    def __init__(self, selection_mode: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.selection_mode = selection_mode
        self.marked_position: Optional[tuple[float, float]] = None
        self.setWindowTitle("Low Mag Die Corner Image")
        self.setFixedSize(430, 420)
        self._build_ui()
        self._refresh_status()

    def _build_ui(self):
        self.setStyleSheet(
            """
            QDialog {
                background: #e7e5d5;
                color: #111111;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10px;
            }
            QPushButton {
                background: #e7e4da;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-height: 22px;
                padding: 2px 10px;
            }
            QComboBox {
                background: #ffffff;
                border: 1px solid #8f8b82;
                min-height: 20px;
            }
            QFrame#statusStrip {
                background: #d5d1c7;
                border: 1px solid #aaa69c;
            }
            """
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Zoom:"))
        zoom = QComboBox()
        zoom.addItems(["100", "150", "200", "Fit"])
        zoom.setFixedWidth(66)
        toolbar.addWidget(zoom)
        toolbar.addStretch(1)
        root.addLayout(toolbar)

        self.image_view = LowMagDieCornerCanvas(self)
        root.addWidget(self.image_view, 1)

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        root.addWidget(self.status_label)

        buttons = QHBoxLayout()
        mark = QPushButton("Mark Site")
        mark.clicked.connect(self._mark_site)
        buttons.addWidget(mark)
        self.finish_button = QPushButton("Finish")
        self.finish_button.clicked.connect(self._finish)
        buttons.addWidget(self.finish_button)
        buttons.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)
        root.addLayout(buttons)

        strip = QFrame()
        strip.setObjectName("statusStrip")
        strip.setFixedHeight(22)
        strip_layout = QHBoxLayout(strip)
        strip_layout.setContentsMargins(6, 0, 6, 0)
        strip_layout.addWidget(QLabel("Use mouse or arrow keys to move the crosshair."))
        root.addWidget(strip)

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Left:
            self.image_view.move_crosshair(-5, 0)
            return
        if key == Qt.Key_Right:
            self.image_view.move_crosshair(5, 0)
            return
        if key == Qt.Key_Up:
            self.image_view.move_crosshair(0, -5)
            return
        if key == Qt.Key_Down:
            self.image_view.move_crosshair(0, 5)
            return
        super().keyPressEvent(event)

    def _mark_site(self):
        self.marked_position = self.image_view.crosshair_position
        self._refresh_status(marked=True)

    def _finish(self):
        if self.marked_position is None:
            QMessageBox.warning(self, "Low Mag Die Corner Image", "Mark the die origin site before clicking Finish.")
            return
        self.accept()

    def _refresh_status(self, marked: bool = False):
        x_value, y_value = self.image_view.crosshair_position
        prefix = "Marked" if marked else "Reselect"
        self.status_label.setText(
            f"{prefix} the die origin from the old inspection. "
            f"Crosshair X: {x_value:.0f}, Y: {y_value:.0f}"
        )


class LowMagDieCornerCanvas(QWidget):
    def __init__(self, dialog: LowMagDieCornerImageDialog):
        super().__init__(dialog)
        self.dialog = dialog
        self.crosshair_position = (105.0, 85.0)
        self.setMinimumSize(340, 245)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

    def move_crosshair(self, dx: float, dy: float):
        x_value, y_value = self.crosshair_position
        self.crosshair_position = (x_value + dx, y_value + dy)
        self._clamp_crosshair()
        self.dialog._refresh_status()
        self.update()

    def mousePressEvent(self, event):
        point = event.position() if hasattr(event, "position") else event.pos()
        self.crosshair_position = (point.x(), point.y())
        self._clamp_crosshair()
        self.dialog._refresh_status()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#e7e5d5"))
        image_rect = self.rect().adjusted(0, 0, -4, -44)
        image_rect.setWidth(min(180, image_rect.width()))
        image_rect.setHeight(min(160, image_rect.height()))
        painter.fillRect(image_rect, QColor("#061cff"))

        painter.setPen(QPen(QColor("#6dff6d"), 1))
        for x_offset in range(18, image_rect.width(), 28):
            painter.drawLine(image_rect.left() + x_offset, image_rect.top(), image_rect.left() + x_offset, image_rect.bottom())
        for y_offset in range(18, image_rect.height(), 28):
            painter.drawLine(image_rect.left(), image_rect.top() + y_offset, image_rect.right(), image_rect.top() + y_offset)

        x_value, y_value = self.crosshair_position
        x_value = max(image_rect.left(), min(image_rect.right(), x_value))
        y_value = max(image_rect.top(), min(image_rect.bottom(), y_value))
        painter.setPen(QPen(QColor("#00e060"), 2))
        painter.drawLine(int(x_value) - 55, int(y_value), int(x_value) + 55, int(y_value))
        painter.drawLine(int(x_value), int(y_value) - 55, int(x_value), int(y_value) + 55)
        painter.setPen(QPen(QColor("#ffffff"), 1))
        painter.drawText(image_rect.left() + 8, image_rect.bottom() + 20, "Old die origin image")
        painter.drawText(image_rect.left() + 8, image_rect.bottom() + 36, "Click Mark Site after reselecting the origin.")

    def _clamp_crosshair(self):
        image_rect = self.rect().adjusted(0, 0, -4, -44)
        image_rect.setWidth(min(180, image_rect.width()))
        image_rect.setHeight(min(160, image_rect.height()))
        x_value, y_value = self.crosshair_position
        self.crosshair_position = (
            max(image_rect.left(), min(image_rect.right(), x_value)),
            max(image_rect.top(), min(image_rect.bottom(), y_value)),
        )


class AutoSiteSelectionDialog(QDialog):
    TARGET_LOCATIONS = [
        ("low", "-71453.063", "66000.750"),
        ("low", "-64475.969", "55930.938"),
        ("high", "-71453.006", "66000.702"),
    ]

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Select Die Corner View")
        self.resize(980, 760)
        self.setMinimumSize(900, 680)
        self.corner_count = 0
        self.use_pattern_matching = True
        self.high_precision_alignment = False
        self._build_ui()
        self._refresh_step_state()

    def _build_ui(self):
        self.setStyleSheet(
            """
            QDialog {
                background: #e8e4d3;
                color: #111111;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10px;
            }
            QPushButton {
                background: #f1efe3;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-height: 22px;
                padding: 2px 10px;
            }
            QPushButton:disabled, QLineEdit:disabled {
                color: #8f8b82;
                background: #ded9c8;
            }
            QFrame#rightPanel, QFrame#instructionPanel {
                border: 1px solid #c8c1aa;
                background: #e8e4d3;
            }
            QFrame#targetPanel {
                border: 1px solid #d8d1ba;
                background: #e8e4d3;
            }
            QLabel[blueTitle="true"] {
                color: #0a55e5;
                background: #e8e4d3;
            }
            QTableWidget {
                background: #f7f5e9;
                border: 1px solid #c8c1aa;
                gridline-color: #d2ccb8;
            }
            """
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(6)

        body = QHBoxLayout()
        body.setSpacing(8)
        self.wafer_view = DieCornerSelectionView(self)
        body.addWidget(self.wafer_view, 1)
        body.addWidget(self._right_panel(), 0)
        root.addLayout(body, 1)

        root.addWidget(self._instruction_panel())
        root.addLayout(self._footer())

    def _right_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("rightPanel")
        panel.setFixedWidth(220)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)
        layout.addWidget(self._target_location_panel())
        layout.addWidget(self._alignment_order_panel())
        layout.addSpacing(12)
        layout.addWidget(QLabel("Target Quality Scores:"))
        self.quality_table = self._quality_table()
        layout.addWidget(self.quality_table)
        layout.addStretch(1)
        legend_title = QLabel("Legend")
        legend_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(legend_title)
        layout.addWidget(self._legend_panel())
        self.event_log = QTableWidget(2, 1)
        self.event_log.horizontalHeader().setVisible(False)
        self.event_log.verticalHeader().setVisible(False)
        self.event_log.setFixedHeight(58)
        self.event_log.setItem(0, 0, QTableWidgetItem(""))
        self.event_log.setItem(1, 0, QTableWidgetItem(""))
        layout.addWidget(self.event_log)
        return panel

    def _alignment_order_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("targetPanel")
        layout = QGridLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setHorizontalSpacing(6)
        layout.setVerticalSpacing(5)
        layout.addWidget(QLabel("Alignment Order"), 0, 0, 1, 2)
        df = QCheckBox("DF")
        df.setChecked(True)
        layout.addWidget(df, 1, 0)
        settings = QPushButton("Settings...")
        settings.setFixedWidth(92)
        settings.clicked.connect(self._open_alignment_settings)
        layout.addWidget(settings, 1, 1)
        return panel

    def _target_location_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("targetPanel")
        layout = QGridLayout(panel)
        layout.setContentsMargins(10, 10, 10, 8)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(6)
        title = QLabel("Target Location")
        title.setProperty("blueTitle", True)
        layout.addWidget(title, 0, 0, 1, 4)
        layout.addWidget(QLabel("Low Mag"), 0, 2, alignment=Qt.AlignCenter)
        layout.addWidget(QLabel("X:"), 1, 0)
        self.low_x_location = self._disabled_location("")
        layout.addWidget(self.low_x_location, 1, 1)
        layout.addWidget(QLabel("Y:"), 1, 2)
        self.low_y_location = self._disabled_location("")
        layout.addWidget(self.low_y_location, 1, 3)
        layout.addWidget(QLabel("High Mag"), 2, 2, alignment=Qt.AlignCenter)
        layout.addWidget(QLabel("X:"), 3, 0)
        self.high_x_location = self._disabled_location("")
        layout.addWidget(self.high_x_location, 3, 1)
        layout.addWidget(QLabel("Y:"), 3, 2)
        self.high_y_location = self._disabled_location("")
        layout.addWidget(self.high_y_location, 3, 3)
        return panel

    @staticmethod
    def _disabled_location(value: str) -> QLineEdit:
        field = QLineEdit(value)
        field.setEnabled(False)
        field.setFixedWidth(54)
        return field

    def _quality_table(self) -> QTableWidget:
        table = QTableWidget(4, 3)
        table.setHorizontalHeaderLabels(["Align", "X Reg", "Y Reg"])
        table.setVerticalHeaderLabels(["Correlation", "Uniqueness", "Sharpness", "Feature"])
        table.setFixedHeight(112)
        table.setFixedWidth(204)
        for row in range(4):
            for column in range(3):
                table.setItem(row, column, QTableWidgetItem(""))
        table.setItem(0, 1, QTableWidgetItem("N/A"))
        table.setItem(0, 2, QTableWidgetItem("N/A"))
        table.resizeColumnsToContents()
        return table

    def _legend_panel(self) -> QWidget:
        panel = QWidget()
        grid = QGridLayout(panel)
        grid.setContentsMargins(2, 2, 2, 2)
        grid.setHorizontalSpacing(2)
        grid.setVerticalSpacing(1)
        items = [
            ("#f05050", "Current Position"),
            ("#00b050", "Single Mag Site"),
            ("#ff944d", "Old First Site"),
            ("#00cc66", "Reselected First Site"),
            ("#808080", "Street Point"),
        ]
        for index, (color, text) in enumerate(items):
            marker = QLabel("")
            marker.setFixedSize(12, 12)
            marker.setStyleSheet(f"background: {color}; border: 1px solid #555555;")
            grid.addWidget(marker, index // 2, (index % 2) * 2)
            grid.addWidget(QLabel(text), index // 2, (index % 2) * 2 + 1)
        return panel

    def _instruction_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("instructionPanel")
        panel.setFixedHeight(62)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(6, 4, 6, 4)
        self.mag_label = QLabel("DF Single Mag")
        self.mag_label.setAlignment(Qt.AlignCenter)
        self.instruction_label = QLabel("")
        self.instruction_label.setAlignment(Qt.AlignCenter)
        self.instruction_label.setWordWrap(True)
        layout.addWidget(self.mag_label)
        layout.addWidget(self.instruction_label)
        return panel

    def _footer(self) -> QHBoxLayout:
        footer = QHBoxLayout()
        footer.setSpacing(8)
        self.prev_button = QPushButton("<< Prev")
        self.prev_button.setEnabled(False)
        self.prev_button.clicked.connect(self._previous_step)
        self.mark_button = QPushButton("Mark Die Corner >>")
        self.mark_button.clicked.connect(self._mark_die_corner)
        advanced = QPushButton("Advanced...")
        advanced.setToolTip("Advanced Inspection Optics Settings")
        advanced.clicked.connect(self._open_advanced_inspection_optics)
        self.next_button = QPushButton("Next >>")
        self.next_button.clicked.connect(self._next_step)
        self.finish_button = QPushButton("Finish")
        self.finish_button.setEnabled(False)
        self.finish_button.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)

        for button in [self.prev_button, self.mark_button, advanced, self.next_button, self.finish_button, cancel]:
            button.setFixedWidth(96)
        footer.addWidget(self.prev_button)
        footer.addWidget(self.mark_button)
        footer.addWidget(advanced)
        footer.addWidget(self.next_button)
        footer.addWidget(self.finish_button)
        footer.addStretch(1)
        footer.addWidget(cancel)
        return footer

    def _mark_die_corner(self):
        self.corner_count = min(3, self.corner_count + 1)
        self.wafer_view.marked_corners = self.corner_count
        self.wafer_view.show_move_stage = self.corner_count >= 1
        self._update_target_location()
        self.wafer_view.update()
        if self.corner_count == 1:
            self.event_log.setItem(0, 0, QTableWidgetItem("First die corner marked."))
        elif self.corner_count == 2:
            self.event_log.setItem(0, 0, QTableWidgetItem("Street marked. Select Second Die Corner view displayed."))
        else:
            self.event_log.setItem(1, 0, QTableWidgetItem("Second die corner marked. Auto Site Selection begins."))
            self._populate_target_quality_scores()
        self._refresh_step_state()

    def _previous_step(self):
        if self.corner_count <= 0:
            return
        self.corner_count -= 1
        self.wafer_view.marked_corners = self.corner_count
        self.wafer_view.show_move_stage = self.corner_count >= 1
        self._clear_target_quality_scores()
        self._update_target_location()
        self.event_log.setItem(0, 0, QTableWidgetItem("Previous die corner step restored."))
        self.event_log.setItem(1, 0, QTableWidgetItem(""))
        self.wafer_view.update()
        self._refresh_step_state()

    def _open_alignment_settings(self):
        dialog = AlignmentSettingsDialog(
            self.use_pattern_matching,
            self.high_precision_alignment,
            self,
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.use_pattern_matching = dialog.use_pattern_matching
            self.high_precision_alignment = dialog.high_precision_alignment
            state = "enabled" if self.high_precision_alignment else "disabled"
            self.event_log.setItem(0, 0, QTableWidgetItem(f"High Precision Alignment {state}."))

    def _open_advanced_inspection_optics(self):
        dialog = AdvancedOpticsDialog(self)
        dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        self.event_log.setItem(0, 0, QTableWidgetItem("Advanced Inspection Optics Settings closed."))

    def _next_step(self):
        if self.corner_count < 3:
            self.event_log.setItem(0, 0, QTableWidgetItem("Mark the first corner, street corner, and second die corner before continuing."))
            return
        self.finish_button.setEnabled(True)
        self.next_button.setEnabled(False)
        self.mark_button.setEnabled(False)
        self.instruction_label.setText("Die corners selected. Click Finish to complete automatic alignment site selection.")

    def _refresh_step_state(self):
        self.prev_button.setEnabled(self.corner_count > 0)
        self.next_button.setEnabled(True)
        self.finish_button.setEnabled(False)
        self.mark_button.setEnabled(self.corner_count < 3)
        if self.corner_count == 0:
            self.instruction_label.setText(
                "Select first die corner: Use Stage Movement Control to select the lower left corner of a die. "
                "Click Mark Die Corner. For derivative recipe, you can press Ctrl + Left Mouse click to snap to the nearest point/corner."
            )
        elif self.corner_count == 1:
            self.instruction_label.setText(
                "Select the lower-left corner of the die diagonally adjacent and to the right of the first die. "
                "Click Mark Die Corner to mark the street."
            )
        elif self.corner_count == 2:
            self.instruction_label.setText(
                "Select Second Die Corner view: Use the same method to locate the second die corner, then click Mark Die Corner."
            )
        else:
            self.instruction_label.setText(
                "Auto Site Selection begins. When you are satisfied with the target site quality, click Finish."
            )
            self.finish_button.setEnabled(True)

    def _populate_target_quality_scores(self):
        values = [
            ["71.00", "N/A", "N/A"],
            ["61.00", "10.00", "10.00"],
            ["81.00", "30.00", "30.00"],
            ["18386415", "16757116", "16447263"],
        ]
        for row, columns in enumerate(values):
            for column, value in enumerate(columns):
                self.quality_table.setItem(row, column, QTableWidgetItem(value))
        self.quality_table.resizeColumnsToContents()

    def _clear_target_quality_scores(self):
        for row in range(4):
            for column in range(3):
                self.quality_table.setItem(row, column, QTableWidgetItem(""))
        self.quality_table.setItem(0, 1, QTableWidgetItem("N/A"))
        self.quality_table.setItem(0, 2, QTableWidgetItem("N/A"))
        self.quality_table.resizeColumnsToContents()

    def _update_target_location(self):
        self.low_x_location.setText("")
        self.low_y_location.setText("")
        self.high_x_location.setText("")
        self.high_y_location.setText("")
        if self.corner_count <= 0:
            return
        mag, x_value, y_value = self.TARGET_LOCATIONS[min(self.corner_count, 3) - 1]
        if mag == "low":
            self.low_x_location.setText(x_value)
            self.low_y_location.setText(y_value)
        else:
            self.high_x_location.setText(x_value)
            self.high_y_location.setText(y_value)

    def _snap_to_nearest_corner(self):
        self.event_log.setItem(0, 0, QTableWidgetItem("Ctrl+click snap applied to nearest point/corner."))


class DieCornerSelectionView(QWidget):
    def __init__(self, dialog: Optional[AutoSiteSelectionDialog] = None):
        super().__init__(dialog)
        self.dialog = dialog
        self.setMinimumSize(650, 560)
        self.marked_corners = 0
        self.show_move_stage = False

    def mousePressEvent(self, event):  # noqa: N802 - Qt override
        if event.button() == Qt.LeftButton and event.modifiers() & Qt.ControlModifier:
            if self.dialog:
                self.dialog._snap_to_nearest_corner()
            event.accept()
            return
        super().mousePressEvent(event)

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#858583"))

        rect = self.rect().adjusted(55, 18, -55, -54)
        side = min(rect.width(), rect.height())
        center_x = rect.center().x()
        center_y = rect.center().y() + 8
        wafer_rect = (
            center_x - side // 2,
            center_y - side // 2,
            side,
            side,
        )
        painter.setBrush(QColor("#ffffff"))
        painter.setPen(QPen(QColor("#666666"), 1))
        painter.drawEllipse(*wafer_rect)

        die_rect = self._die_rect(center_x, center_y, side)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor("#6266ff"), 1))
        painter.drawRect(*die_rect)

        painter.setPen(QPen(QColor("#ff3a3a"), 1))
        painter.drawLine(center_x - 9, center_y, center_x + 9, center_y)
        painter.drawLine(center_x, center_y - 9, center_x, center_y + 9)
        painter.setPen(QPen(QColor("#20d04a"), 1))
        painter.drawLine(center_x - 4, center_y + 8, center_x + 10, center_y + 8)
        painter.drawLine(center_x + 3, center_y + 1, center_x + 3, center_y + 15)

        if self.marked_corners >= 1:
            x, y, _, h = die_rect
            self._draw_corner_marker(painter, x, y + h, "#f05050")
        if self.marked_corners >= 2:
            x, y, w, h = die_rect
            self._draw_street_marker(painter, x + int(w * 0.72), y + h, "#ff944d")
        if self.marked_corners >= 3:
            x, y, w, _ = die_rect
            self._draw_corner_marker(painter, x + w, y, "#00b050")

        if self.show_move_stage:
            self._draw_move_stage(painter, 10, self.height() - 150)

    @staticmethod
    def _die_rect(center_x: int, center_y: int, wafer_side: int):
        width = int(wafer_side * 0.72)
        height = int(wafer_side * 0.36)
        return center_x - width // 2, center_y - height // 2, width, height

    @staticmethod
    def _draw_corner_marker(painter: QPainter, x: int, y: int, color: str):
        painter.setPen(QPen(QColor(color), 2))
        painter.drawLine(x - 8, y, x + 8, y)
        painter.drawLine(x, y - 8, x, y + 8)

    @staticmethod
    def _draw_street_marker(painter: QPainter, x: int, y: int, color: str):
        painter.setPen(QPen(QColor(color), 2))
        painter.drawLine(x - 10, y, x + 10, y)
        painter.drawLine(x, y - 10, x, y + 10)
        painter.drawLine(x - 10, y + 10, x + 10, y + 10)

    def _draw_move_stage(self, painter: QPainter, x: int, y: int):
        painter.setPen(QPen(QColor("#ffffff"), 1))
        painter.setBrush(QColor("#3156e8"))
        painter.drawRect(x, y, 58, 92)
        painter.setPen(QPen(QColor("#ffffff"), 1))
        painter.drawText(x + 7, y + 12, "Move Stage")
        positions = [
            (0, 0, "\\"),
            (1, 0, "^"),
            (2, 0, "/"),
            (0, 1, "<"),
            (2, 1, ">"),
            (0, 2, "/"),
            (1, 2, "v"),
            (2, 2, "\\"),
        ]
        for column, row, text in positions:
            bx = x + 6 + column * 16
            by = y + 20 + row * 15
            painter.setBrush(QColor("#f6f6f6"))
            painter.setPen(QPen(QColor("#1641d8"), 1))
            painter.drawRect(bx, by, 13, 13)
            painter.drawText(bx + 3, by + 10, text)
        painter.setPen(QPen(QColor("#111111"), 1))
        painter.setBrush(QColor("#ffffff"))
        painter.drawRect(x + 7, y + 70, 44, 16)
        painter.drawText(x + 11, y + 82, "10 um")

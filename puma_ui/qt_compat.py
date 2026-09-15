from __future__ import annotations

try:
    from PySide6.QtCore import QEvent, QObject, QEasingCurve, QPropertyAnimation, QUrl, Qt, QSize, QTimer
    from PySide6.QtGui import QAction, QColor, QDesktopServices, QIcon, QPainter, QPen, QPixmap, QRegion
    from PySide6.QtPrintSupport import QPrintDialog, QPrinter
    from PySide6.QtWidgets import (
        QAbstractItemView,
        QApplication,
        QCheckBox,
        QComboBox,
        QColorDialog,
        QDialog,
        QDoubleSpinBox,
        QFileDialog,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLineEdit,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMenu,
        QMenuBar,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QRadioButton,
        QScrollArea,
        QSizePolicy,
        QSlider,
        QSplitter,
        QSpinBox,
        QStackedWidget,
        QStatusBar,
        QStyle,
        QTableWidget,
        QTableWidgetItem,
        QTabWidget,
        QTextEdit,
        QToolBar,
        QToolButton,
        QTreeWidget,
        QTreeWidgetItem,
        QVBoxLayout,
        QWidget,
    )

    QT_BINDING = "PySide6"
except ImportError as pyside_error:
    try:
        from PyQt5.QtCore import QEvent, QObject, QEasingCurve, QPropertyAnimation, QUrl, Qt, QSize, QTimer
        from PyQt5.QtGui import QColor, QDesktopServices, QIcon, QPainter, QPen, QPixmap, QRegion
        from PyQt5.QtPrintSupport import QPrintDialog, QPrinter
        from PyQt5.QtWidgets import (
            QAbstractItemView,
            QAction,
            QApplication,
            QCheckBox,
            QComboBox,
            QColorDialog,
            QDialog,
            QDoubleSpinBox,
            QFileDialog,
            QFrame,
            QGridLayout,
            QHBoxLayout,
            QHeaderView,
            QLabel,
            QLineEdit,
            QListWidget,
            QListWidgetItem,
            QMainWindow,
            QMenu,
            QMenuBar,
            QMessageBox,
            QProgressBar,
            QPushButton,
            QRadioButton,
            QScrollArea,
            QSizePolicy,
            QSlider,
            QSplitter,
            QSpinBox,
            QStackedWidget,
            QStatusBar,
            QStyle,
            QTableWidget,
            QTableWidgetItem,
            QTabWidget,
            QTextEdit,
            QToolBar,
            QToolButton,
            QTreeWidget,
            QTreeWidgetItem,
            QVBoxLayout,
            QWidget,
        )

        QT_BINDING = "PyQt5"
    except ImportError as pyqt_error:
        raise SystemExit(
            "Qt binding not found. Install one in conda env 'pumaui':\n"
            "  conda activate pumaui\n"
            "  pip install PySide6\n"
            "or\n"
            "  pip install PyQt5\n\n"
            f"PySide6 import error: {pyside_error}\n"
            f"PyQt5 import error: {pyqt_error}"
        ) from pyqt_error

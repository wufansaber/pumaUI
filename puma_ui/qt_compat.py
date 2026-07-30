from __future__ import annotations

try:
    from PySide6.QtCore import QUrl, Qt, QSize, QTimer
    from PySide6.QtGui import QAction, QColor, QDesktopServices, QIcon, QPainter, QPen, QPixmap
    from PySide6.QtWidgets import (
        QAbstractItemView,
        QApplication,
        QCheckBox,
        QComboBox,
        QDialog,
        QDoubleSpinBox,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLineEdit,
        QListWidget,
        QMainWindow,
        QMenu,
        QMenuBar,
        QMessageBox,
        QPushButton,
        QRadioButton,
        QScrollArea,
        QSizePolicy,
        QSlider,
        QSpinBox,
        QStatusBar,
        QStyle,
        QTableWidget,
        QTableWidgetItem,
        QToolBar,
        QTreeWidget,
        QTreeWidgetItem,
        QVBoxLayout,
        QWidget,
    )

    QT_BINDING = "PySide6"
except ImportError:
    try:
        from PyQt5.QtCore import QUrl, Qt, QSize, QTimer
        from PyQt5.QtGui import QColor, QDesktopServices, QIcon, QPainter, QPen, QPixmap
        from PyQt5.QtWidgets import (
            QAbstractItemView,
            QAction,
            QApplication,
            QCheckBox,
            QComboBox,
            QDialog,
            QDoubleSpinBox,
            QFrame,
            QGridLayout,
            QHBoxLayout,
            QHeaderView,
            QLabel,
            QLineEdit,
            QListWidget,
            QMainWindow,
            QMenu,
            QMenuBar,
            QMessageBox,
            QPushButton,
            QRadioButton,
            QScrollArea,
            QSizePolicy,
            QSlider,
            QSpinBox,
            QStatusBar,
            QStyle,
            QTableWidget,
            QTableWidgetItem,
            QToolBar,
            QTreeWidget,
            QTreeWidgetItem,
            QVBoxLayout,
            QWidget,
        )

        QT_BINDING = "PyQt5"
    except ImportError as exc:
        raise SystemExit(
            "Qt binding not found. Install one in conda env 'pumaui':\n"
            "  conda activate pumaui\n"
            "  pip install PySide6\n"
            "or\n"
            "  pip install PyQt5"
        ) from exc

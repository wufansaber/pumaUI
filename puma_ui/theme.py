"""Application-wide visual system for the Puma UI prototype.

The dialogs in this project were written one at a time, so they each carried
their own font sizes, paddings and button metrics.  This module owns the single
source of truth for those decisions:

* a type ramp (``TYPE``) and spacing ramp (``SPACE``),
* a palette tied to the existing industrial grey/beige shell,
* one Qt style sheet for every stock control, so tables, tabs, menus, inputs
  and buttons agree in every window,
* helpers for the few decisions a style sheet cannot make (button roles,
  dialog chrome, spacing normalisation).

Nothing here touches business state, signals or the order of controls.  Calling
:func:`install` only changes how the widgets paint and how much air they get.
"""

from __future__ import annotations

import re

from .qt_compat import (
    QApplication,
    QDialog,
    QEvent,
    QFont,
    QFrame,
    QLabel,
    QLayout,
    QMainWindow,
    QObject,
    QPushButton,
    QWidget,
)

# --------------------------------------------------------------------------- #
# Tokens
# --------------------------------------------------------------------------- #

PALETTE = {
    "window": "#cfcbc2",       # shell background
    "panel": "#e7e4dc",        # grouped content
    "surface": "#f2f0ea",      # cards, bands
    "surface_alt": "#e1ded6",
    "field": "#ffffff",
    "ink": "#16181c",
    "ink_soft": "#454743",
    "muted": "#5f605c",
    "line": "#a8a49a",
    "line_soft": "#c6c2b7",
    "line_dark": "#6e6b64",
    "line_light": "#ffffff",
    "accent": "#2f5fb3",
    "accent_dark": "#1d3f86",
    "accent_soft": "#dbe6f9",
    "selected": "#cfe0f7",
    "success": "#2f7d3f",
    "warning": "#a97417",
    "danger": "#a8332a",
}

# Type ramp in px.  Qt style sheets take px, so the ramp stays explicit.
TYPE = {
    "display": 18,     # one per page: Main Menu, dialog hero title
    "title": 14,       # dialog title
    "subtitle": 12,    # pane title, section heading
    "body": 11,        # default text, inputs, tables
    "small": 10,       # field labels, status bar, meta
}

SPACE = {
    "xxs": 2,
    "xs": 4,
    "sm": 6,
    "md": 8,
    "lg": 12,
    "xl": 16,
    "xxl": 24,
}

# Geometry shared by every command surface.
CONTROL_HEIGHT = 26
CONTROL_HEIGHT_COMPACT = 22
BUTTON_MIN_WIDTH = 84
DIALOG_MARGIN_H = 14
DIALOG_MARGIN_V = 12

FONT_STACK = '"Segoe UI", Tahoma, Arial, Helvetica, sans-serif'


def _palette_block() -> str:
    return "\n".join(f"/* {name}: {value} */" for name, value in PALETTE.items())




STYLE_SHEET = f"""
/* ---------- base typography ---------- */
QWidget {{
    font-family: {FONT_STACK};
    font-size: {TYPE["body"]}px;
    color: {PALETTE["ink"]};
}}
QMainWindow, QDialog, QWidget#root {{
    background: {PALETTE["window"]};
}}
QDialog QLabel, QMainWindow QLabel {{
    background: transparent;
}}
QLabel[role="muted"] {{
    color: {PALETTE["muted"]};
}}
QLabel[role="field"] {{
    color: {PALETTE["ink_soft"]};
}}
QLabel[role="title"] {{
    font-size: {TYPE["title"]}px;
    font-weight: 700;
    color: {PALETTE["ink"]};
}}
QLabel[role="display"] {{
    font-size: {TYPE["display"]}px;
    font-weight: 700;
    color: {PALETTE["ink"]};
}}
QLabel[role="section"] {{
    font-size: {TYPE["subtitle"]}px;
    font-weight: 700;
    color: {PALETTE["ink"]};
}}
QLabel[role="caption"] {{
    font-size: {TYPE["small"]}px;
    color: {PALETTE["muted"]};
}}
QLabel[role="value"] {{
    font-weight: 600;
}}
QLabel:disabled {{
    color: {PALETTE["line_dark"]};
}}

/* ---------- buttons ---------- */
QPushButton {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #f2efe7, stop:1 #e2ded5);
    border: 1px solid {PALETTE["line_dark"]};
    border-radius: 2px;
    padding: 4px 12px;
    min-height: {CONTROL_HEIGHT}px;
    color: {PALETTE["ink"]};
}}
QPushButton[iconOnly="true"] {{
    padding: 1px;
    min-width: 0;
}}
QPushButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #fbf9f3, stop:1 #ebe7de);
    border-color: #56534d;
}}
QPushButton:pressed {{
    background: #d6d2c7;
    border-color: #4c4943;
    padding-top: 5px;
    padding-bottom: 3px;
}}
QPushButton:checked {{
    background: #d9e4f5;
    border-color: {PALETTE["accent"]};
}}
QPushButton:focus {{
    border-color: {PALETTE["accent"]};
}}
QPushButton:disabled {{
    background: #dedad1;
    border-color: #b0aca2;
    color: #8b8b86;
}}
QPushButton[role="primary"] {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #3f6fc0, stop:1 #2b5699);
    border: 1px solid {PALETTE["accent_dark"]};
    color: #ffffff;
    font-weight: 600;
}}
QPushButton[role="primary"]:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #4c7ccc, stop:1 #3461a6);
}}
QPushButton[role="primary"]:pressed {{
    background: #274c88;
}}
QPushButton[role="primary"]:disabled {{
    background: #b9c5d8;
    border-color: #9aa8bd;
    color: #f0f2f6;
}}
QPushButton[role="quiet"] {{
    background: transparent;
    border: 1px solid transparent;
    min-width: 0;
    padding: 2px 6px;
    color: {PALETTE["accent_dark"]};
    text-decoration: underline;
}}
QPushButton[role="quiet"]:hover {{
    background: {PALETTE["accent_soft"]};
    border-color: {PALETTE["accent_soft"]};
}}
QPushButton[role="danger"] {{
    color: {PALETTE["danger"]};
    border-color: #9d5148;
}}
QPushButton[compact="true"] {{
    min-height: {CONTROL_HEIGHT_COMPACT}px;
    min-width: 0;
    padding: 1px 8px;
}}

QToolButton {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 2px;
    padding: 2px;
    color: {PALETTE["ink"]};
}}
QToolButton:hover {{
    background: #f4f1e9;
    border-color: #a8a49a;
}}
QToolButton:pressed, QToolButton:checked {{
    background: #d9e4f5;
    border-color: {PALETTE["accent"]};
}}
QToolButton:disabled {{
    color: #8b8b86;
}}

/* ---------- inputs ---------- */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit, QPlainTextEdit {{
    background: {PALETTE["field"]};
    border: 1px solid #8a8680;
    border-radius: 2px;
    padding: 2px 5px;
    min-height: 20px;
    selection-background-color: {PALETTE["accent"]};
    selection-color: #ffffff;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus,
QDoubleSpinBox:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {PALETTE["accent"]};
}}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled,
QDoubleSpinBox:disabled, QTextEdit:disabled {{
    background: #f0eee8;
    color: #74746f;
}}
QComboBox QAbstractItemView {{
    background: {PALETTE["field"]};
    border: 1px solid #8a8680;
    selection-background-color: {PALETTE["accent"]};
    selection-color: #ffffff;
    outline: none;
}}

/* ---------- item views ---------- */
QTableView, QTableWidget, QTreeWidget, QListWidget, QListView, QTreeView {{
    background: {PALETTE["field"]};
    alternate-background-color: #f6f4ef;
    border: 1px solid {PALETTE["line_dark"]};
    gridline-color: #d6d2c7;
    selection-background-color: {PALETTE["selected"]};
    selection-color: {PALETTE["ink"]};
    outline: none;
}}
QTableView::item, QTableWidget::item, QTreeWidget::item, QListWidget::item {{
    padding: 3px 6px;
    border: none;
}}
QTableView::item:selected, QTableWidget::item:selected,
QTreeWidget::item:selected, QListWidget::item:selected {{
    background: {PALETTE["selected"]};
    color: {PALETTE["ink"]};
}}
QHeaderView {{
    background: #dedad0;
    border: none;
}}
QHeaderView::section {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #eae6dd, stop:1 #dad6cb);
    border: none;
    border-right: 1px solid #bdb8ac;
    border-bottom: 1px solid #a8a49a;
    padding: 4px 6px;
    font-size: {TYPE["small"]}px;
    font-weight: 700;
    color: {PALETTE["ink_soft"]};
}}
QHeaderView::section:hover {{
    background: #eeeae1;
}}
QTableCornerButton::section {{
    background: #dedad0;
    border: none;
    border-right: 1px solid #bdb8ac;
    border-bottom: 1px solid #a8a49a;
}}
QListWidget::item, QTreeWidget::item {{
    min-height: 20px;
}}

/* ---------- tabs ---------- */
QTabWidget::pane {{
    border: 1px solid {PALETTE["line_dark"]};
    top: -1px;
    background: {PALETTE["surface"]};
}}
QTabBar::tab {{
    background: #dcd8ce;
    border: 1px solid {PALETTE["line"]};
    border-bottom: none;
    padding: 6px 14px;
    margin-right: 2px;
    color: {PALETTE["ink_soft"]};
    min-width: 70px;
}}
QTabBar::tab:hover {{
    background: #eae6dd;
}}
QTabBar::tab:selected {{
    background: {PALETTE["surface"]};
    color: {PALETTE["ink"]};
    font-weight: 600;
    border-top: 2px solid {PALETTE["accent"]};
}}
QTabBar::tab:disabled {{
    color: #8b8b86;
}}

/* ---------- grouping ---------- */
QGroupBox {{
    border: 1px solid #b3afa4;
    border-radius: 3px;
    margin-top: 16px;
    padding: 10px 10px 8px 10px;
    background: transparent;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 8px;
    padding: 0 4px;
    color: {PALETTE["ink"]};
}}
QFrame[role="panel"] {{
    background: {PALETTE["panel"]};
    border: 1px solid {PALETTE["line"]};
    border-radius: 3px;
}}
QFrame[role="band"] {{
    background: {PALETTE["surface"]};
    border-top: 1px solid {PALETTE["line_light"]};
    border-bottom: 1px solid {PALETTE["line"]};
}}
QFrame[role="rule"] {{
    background: {PALETTE["line_soft"]};
    border: none;
    max-height: 1px;
}}

/* ---------- checks and radios ---------- */
QCheckBox, QRadioButton {{
    spacing: 7px;
    background: transparent;
}}
QCheckBox:disabled, QRadioButton:disabled {{
    color: #8b8b86;
}}

/* ---------- menus ---------- */
QMenuBar {{
    background: {PALETTE["surface_alt"]};
    border-bottom: 1px solid #8c8982;
    padding: 1px 4px;
}}
QMenuBar::item {{
    padding: 4px 10px;
    background: transparent;
}}
QMenuBar::item:selected {{
    background: {PALETTE["accent_soft"]};
    border: 1px solid {PALETTE["accent"]};
    padding: 3px 9px;
}}
QMenu {{
    background: #fbfaf6;
    border: 1px solid #7d7a72;
    padding: 4px 0;
}}
QMenu::item {{
    padding: 5px 26px 5px 22px;
    margin: 0 2px;
}}
QMenu::item:selected {{
    background: {PALETTE["accent"]};
    color: #ffffff;
}}
QMenu::item:disabled {{
    color: #8b8b86;
}}
QMenu::separator {{
    height: 1px;
    background: {PALETTE["line_soft"]};
    margin: 4px 8px;
}}

/* ---------- scroll bars ---------- */
QScrollBar:vertical {{
    background: #ddd9cf;
    width: 13px;
    margin: 0;
    border-left: 1px solid #b8b3a8;
}}
QScrollBar::handle:vertical {{
    background: #bab5a9;
    min-height: 26px;
    border: 1px solid #9f9a8e;
    border-radius: 2px;
    margin: 1px;
}}
QScrollBar::handle:vertical:hover {{
    background: #a9a497;
}}
QScrollBar:horizontal {{
    background: #ddd9cf;
    height: 13px;
    margin: 0;
    border-top: 1px solid #b8b3a8;
}}
QScrollBar::handle:horizontal {{
    background: #bab5a9;
    min-width: 26px;
    border: 1px solid #9f9a8e;
    border-radius: 2px;
    margin: 1px;
}}
QScrollBar::handle:horizontal:hover {{
    background: #a9a497;
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    width: 0;
    height: 0;
}}
QScrollBar::add-page, QScrollBar::sub-page {{
    background: transparent;
}}

/* ---------- misc ---------- */
QToolBar {{
    background: #c9c5bc;
    border-top: 1px solid {PALETTE["line_light"]};
    border-bottom: 1px solid {PALETTE["line_dark"]};
    spacing: 4px;
    padding: 3px 6px;
}}
QToolBar::separator {{
    background: #a5a198;
    width: 1px;
    margin: 4px 6px;
}}
QStatusBar {{
    background: #d8d5cc;
    border-top: 1px solid #8f8b82;
    font-size: {TYPE["small"]}px;
}}
QStatusBar::item {{
    border: none;
}}
QSplitter::handle {{
    background: #c2beb4;
}}
QSplitter::handle:hover {{
    background: {PALETTE["accent"]};
}}
QProgressBar {{
    background: {PALETTE["field"]};
    border: 1px solid {PALETTE["line_dark"]};
    border-radius: 2px;
    text-align: center;
    min-height: 16px;
    font-size: {TYPE["small"]}px;
}}
QProgressBar::chunk {{
    background: {PALETTE["accent"]};
}}
QSlider::groove:horizontal {{
    height: 4px;
    background: #bdb8ac;
    border: 1px solid #9f9a8e;
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    width: 12px;
    margin: -5px 0;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #f6f4ee, stop:1 #dcd8ce);
    border: 1px solid #6e6b64;
    border-radius: 2px;
}}
QToolTip {{
    background: #ffffe1;
    color: #1a1a1a;
    border: 1px solid #7d7a72;
    padding: 3px 6px;
}}
QScrollArea {{
    border: none;
    background: transparent;
}}
QDialogButtonBox QPushButton {{
    min-width: {BUTTON_MIN_WIDTH}px;
    min-height: {CONTROL_HEIGHT}px;
}}
"""


# --------------------------------------------------------------------------- #
# Public helpers
# --------------------------------------------------------------------------- #

_ROLES = ("primary", "quiet", "danger")


def apply_role(button: QPushButton, role: str) -> QPushButton:
    """Give ``button`` the style sheet role ``primary``/``quiet``/``danger``.

    The role lives in a dynamic property so the global sheet keeps owning the
    actual colours; no per-widget style sheet string is duplicated.
    """
    if role not in _ROLES:
        raise ValueError(f"unknown button role: {role!r}")
    button.setProperty("role", role)
    _refresh(button)
    return button


def compact(button: QPushButton) -> QPushButton:
    """Mark a button as a compact inline control (toolbar height)."""
    button.setProperty("compact", "true")
    _refresh(button)
    return button


def role_label(label: QLabel, role: str) -> QLabel:
    """Tag a label with one of the type-ramp roles from the style sheet."""
    label.setProperty("role", role)
    _refresh(label)
    return label


def section_heading(text: str, role: str = "section") -> QLabel:
    label = QLabel(text)
    role_label(label, role)
    return label


def rule() -> QWidget:
    """A one pixel horizontal rule that matches the panel borders."""
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setFixedHeight(1)
    line.setProperty("role", "rule")
    line.setStyleSheet(
        f"background: {PALETTE['line_soft']}; border: none;"
    )
    return line


def _refresh(widget: QWidget) -> None:
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


_WINDOW_SELECTOR = (
    r"(?:QDialog|QMainWindow|QWidget(?:#[\w-]+)?)"
    r"(?:\s*,\s*(?:QDialog|QMainWindow|QWidget(?:#[\w-]+)?))*"
)
_BASE_RULE = re.compile(r"(?P<sel>" + _WINDOW_SELECTOR + r")\s*\{(?P<body>[^}]*)\}")
# Rules whose whole selector list is plain ``QPushButton`` (optionally with a
# state).  Window sheets written before the design system used them to rebuild
# a bevel button, which also suppressed the shared hover/pressed feedback; the
# system sheet owns those buttons now.
_BUTTON_ONLY_RULE = re.compile(
    r"(?P<lead>^|[}\n])[ \t]*"
    r"(?:QPushButton(?::[a-z]+)?[ \t]*,[ \t]*)*QPushButton(?::[a-z]+)?"
    r"[ \t]*\{[^}]*\}[ \t]*\r?\n?",
    re.MULTILINE,
)


def _normalize_window_sheet(sheet: str) -> str:
    """Drop per-window base fonts so the app type ramp owns body text.

    Dialogs written at different times declare ``font-size: 10px`` (or Arial)
    on ``QDialog``/``QWidget``.  Those rules would defeat the single type ramp,
    so they are removed from the *base* selectors only; component rules such as
    ``QLabel[section="true"]`` keep their deliberate sizes, and bevel button
    rules are dropped so the shared button style (with its hover and pressed
    states) applies everywhere.
    """
    if not sheet:
        return sheet

    def clean(match) -> str:
        body = match.group("body")
        body = re.sub(r"font-family\s*:[^;}]*;?", "", body)
        body = re.sub(r"font-size\s*:\s*[\d.]+px\s*;?", "", body)
        return f"{match.group('sel')} {{{body}}}"

    def drop_buttons(match) -> str:
        lead = match.group("lead")
        return lead + " " if lead.strip() else lead

    return _BUTTON_ONLY_RULE.sub(drop_buttons, _BASE_RULE.sub(clean, sheet))


class _ThemeWatcher(QObject):
    """Attach the visual system to every window the app opens.

    The sheet is applied to the top level window, not to ``QApplication``, so
    :class:`FullscreenWindowAdapter` can keep scaling fonts, paddings and control
    heights when a window is maximised (it rewrites px values on the window's own
    style sheet; an application wide sheet would be frozen at design size).
    A window that already carries its own sheet keeps it: the system rules are
    prepended, so local rules still win.
    """

    def __init__(self, app: QApplication):
        super().__init__(app)
        self.app = app

    def eventFilter(self, watched, event):  # noqa: N802 - Qt override
        if event.type() == QEvent.Show:
            self.attach(watched)
        return False

    def attach(self, widget) -> None:
        if not isinstance(widget, (QDialog, QMainWindow)):
            return
        if widget.property("pumaThemed"):
            return
        widget.setProperty("pumaThemed", True)
        existing = _normalize_window_sheet(widget.styleSheet() or "")
        widget.setStyleSheet(STYLE_SHEET + "\n" + existing)
        self._tag_icon_buttons(widget)
        if isinstance(widget, QDialog):
            self._normalize_spacing(widget)

    @staticmethod
    def _tag_icon_buttons(widget) -> None:
        """Icon-only buttons keep a tight content box, so their glyphs fit."""
        for button in widget.findChildren(QPushButton):
            if button.property("iconOnly"):
                continue
            if button.icon().isNull() or button.text().strip():
                continue
            button.setProperty("iconOnly", "true")
            _refresh(button)

    @staticmethod
    def _normalize_spacing(dialog: QDialog) -> None:
        if dialog.property("spacingNormalized"):
            return
        dialog.setProperty("spacingNormalized", True)
        layout = dialog.layout()
        if layout is None:
            return
        margins = layout.contentsMargins()
        if margins.isNull():
            return
        left = max(margins.left(), DIALOG_MARGIN_H)
        right = max(margins.right(), DIALOG_MARGIN_H)
        top = max(margins.top(), DIALOG_MARGIN_V)
        bottom = max(margins.bottom(), DIALOG_MARGIN_V)
        if (left, top, right, bottom) != (
            margins.left(), margins.top(), margins.right(), margins.bottom()
        ):
            layout.setContentsMargins(left, top, right, bottom)


def install(app: QApplication) -> QApplication:
    """Install the palette, type ramp and control metrics on ``app``.

    Idempotent: the entry point and tests can both call it.
    """
    if app is None:
        return app
    if getattr(app, "_puma_theme_installed", False):
        return app
    app.setStyle("Fusion")
    font = QFont()
    font.setFamily("Segoe UI")
    font.setPixelSize(TYPE["body"])
    app.setFont(font)
    watcher = _ThemeWatcher(app)
    app.installEventFilter(watcher)
    for widget in app.topLevelWidgets():
        watcher.attach(widget)
    app._puma_theme_watcher = watcher
    app._puma_theme_installed = True
    return app


def apply_layout(layout: QLayout, horizontal: int = SPACE["lg"], vertical: int = SPACE["md"],
                 spacing: int = SPACE["sm"]) -> QLayout:
    """Apply the standard content margins and spacing to a layout."""
    layout.setContentsMargins(horizontal, vertical, horizontal, vertical)
    layout.setSpacing(spacing)
    return layout

"""
Config Viewer — Industrial Drive Configuration Comparison Tool  (v3.0)

Desktop application for loading, comparing, and analysing multi-format drive
configuration files across multiple project sites.  Supports binary .dco files
(DCO Mode) and text-based .ini parameter files (INI Mode) in a single tabbed
session with independent per-tab state.

Architecture
------------
- GUI:     PyQt5 (QMainWindow, QTabWidget, per-tab sessions, toolbar)
- Data:    struct-based binary parser + INI text parser (private lib/)
- I/O:     QFileDialog for file selection, openpyxl for Excel export
- Icon:    Embedded base64 JPEG — no external icon file required at runtime
- State:   JSON-backed recent-selection history with exact file tracking

Author: Umang Panchal (github.com/ichumang)
"""

import sys
import os
import json
import base64

from PyQt5.QtCore import Qt, QSize, QPoint
from PyQt5.QtGui import (
    QFont, QColor, QIcon, QPainter, QFontMetrics, QPixmap,
)
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QPushButton,
    QLabel,
    QCheckBox,
    QTableWidget,
    QTableWidgetItem,
    QFileDialog,
    QStatusBar,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QHeaderView,
    QMessageBox,
    QGroupBox,
    QFrame,
    QAbstractScrollArea,
    QDialog,
    QDialogButtonBox,
    QTabWidget,
    QTabBar,
    QMenu,
    QAction,
    QTextBrowser,
)

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font as XlFont, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


APP_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
#  Embedded application icon (base64-encoded JPEG, 256×256)
# ---------------------------------------------------------------------------
#  The icon is baked into the script so the standalone .exe never needs
#  an external image file.  Qt decodes it at runtime into a QIcon.
#  (Base64 data omitted from public repo — see NOTICE.md)

_ICON_B64 = ""   # populated in private build


def _app_icon():
    """Return a QIcon from the embedded JPEG, or a null icon if not set."""
    if not _ICON_B64:
        return QIcon()
    raw = base64.b64decode(_ICON_B64)
    pm = QPixmap()
    pm.loadFromData(raw, "JPEG")
    return QIcon(pm)


# ---------------------------------------------------------------------------
#  Recent-selections persistence
# ---------------------------------------------------------------------------
#  Stores the last 10 file selections as [{folder, files}, ...] in a
#  JSON file next to the executable.  Each entry records the exact files
#  selected (not just the folder) so reopening is one click.

_RECENT_FILE = "configview_recent.json"
MAX_RECENT = 10


def _recent_path():
    base = (os.path.dirname(sys.executable) if getattr(sys, "frozen", False)
            else os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, _RECENT_FILE)


def load_recent():
    try:
        with open(_recent_path(), "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_recent(entries):
    with open(_recent_path(), "w", encoding="utf-8") as f:
        json.dump(entries[:MAX_RECENT], f, indent=2)


def add_recent_entry(folder, basenames):
    entries = load_recent()
    new = {"folder": folder, "files": basenames}
    entries = [e for e in entries
               if not (e["folder"] == folder and e["files"] == basenames)]
    entries.insert(0, new)
    save_recent(entries[:MAX_RECENT])


# ---------------------------------------------------------------------------
#  Parser interfaces (stubs — private lib/ provides real implementations)
# ---------------------------------------------------------------------------
#
#  lib/dco_parser.py  (private – not included in this repository)
#    - KONFDAT_FORMAT: struct format string for .dco files (400 bytes)
#    - COLUMN_DEFS: list of (column_header, category, struct_field, ...) tuples
#    - BIT_FLAG_COLUMNS: set of column names rendered as boolean x/blank
#    - decode_record(filename, data) → dict[str, str]
#    - DCO_CATEGORIES: dict mapping category name → colour hex
#
#  lib/ini_parser.py  (private – not included in this repository)
#    - ANT_COLS: column definitions for [Antriebsparameter] section
#    - PRT_COLS: column definitions for [Prototypen] section
#    - decode_ini(filepath) → (ant_rows, prt_rows)
#    - INI_CATEGORIES: dict mapping category name → colour hex

DCO_FILTER_CATEGORIES = {
    "Position":        "Encoder position, limits, encoder resolution",
    "Regelung":        "Closed-loop control: P / I / FF gains",
    "Last":            "Load-cell and load-monitoring parameters",
    "Sicherheiten":    "Safety monitoring: standstill, tracking, overspeed",
    "Geschwindigkeit": "Speed setpoints and ramp parameters",
    "Locking":         "Locking / docking position values",
    "Optional":        "Vendor-specific optional fields",
    "Sonstige":        "Miscellaneous parameters",
}

INI_FILTER_CATEGORIES = {
    "Position/Geschw./Beschl.": "Position, speed, acceleration",
    "Sicherheit":               "Safety-related flags and limits",
    "Antriebstyp":              "Drive type identifiers and mode bits",
    "Sonstige":                 "Miscellaneous flags and settings",
}


# ---------------------------------------------------------------------------
#  Custom header view — paints certain columns with vertical rotated text.
#  Bit-flag columns (x / blank) only need ~30 px width; rotating their
#  labels saves a lot of horizontal space in wide comparison grids.
# ---------------------------------------------------------------------------

class VerticalHeaderView(QHeaderView):
    """A QHeaderView that renders certain column headers as vertical text."""

    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self._vertical_columns = set()
        self._col_names = []

    def set_vertical_columns(self, names, col_names):
        self._vertical_columns = set(names)
        self._col_names = list(col_names)

    def sectionSizeFromContents(self, logicalIndex):
        base = super().sectionSizeFromContents(logicalIndex)
        if logicalIndex < len(self._col_names):
            if self._col_names[logicalIndex] in self._vertical_columns:
                fm = QFontMetrics(self.font())
                text_w = fm.horizontalAdvance(self._col_names[logicalIndex])
                return QSize(30, min(text_w + 12, 160))
        return base

    def paintSection(self, painter, rect, logicalIndex):
        if logicalIndex < len(self._col_names):
            name = self._col_names[logicalIndex]
            if name in self._vertical_columns:
                painter.save()
                painter.fillRect(rect, self.palette().button())
                painter.setPen(self.palette().mid().color())
                painter.drawRect(rect.adjusted(0, 0, -1, -1))
                painter.setPen(self.palette().buttonText().color())
                painter.translate(rect.x() + rect.width() / 2 + 4,
                                  rect.y() + rect.height() - 4)
                painter.rotate(-90)
                painter.drawText(0, 0, name)
                painter.restore()
                return
        super().paintSection(painter, rect, logicalIndex)


# ---------------------------------------------------------------------------
#  TablePane — reusable table widget with filter, sort, drag-reorder,
#  vertical headers, and category-coloured Excel export.
# ---------------------------------------------------------------------------

class TablePane(QWidget):
    """Encapsulates a QTableWidget with sort (context menu), drag-reorder,
    vertical bit-flag headers, and styled Excel export.

    This is the core rendering component shared by both DCO and INI modes.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget()
        self._header = VerticalHeaderView(Qt.Horizontal, self.table)
        self.table.setHorizontalHeader(self._header)
        self._setup_table(self.table)

        # drag-reorder
        self._header.setSectionsMovable(True)
        self._header.setDragEnabled(True)
        self._header.setDragDropMode(self._header.InternalMove)

        # context-menu sort
        self._header.setContextMenuPolicy(Qt.CustomContextMenu)
        self._header.customContextMenuRequested.connect(self._header_ctx)

        layout.addWidget(self.table)

        self.columns = []
        self.rows = []
        self._sort_col = -1
        self._sort_asc = True

    @staticmethod
    def _setup_table(table):
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setShowGrid(True)
        table.setAlternatingRowColors(True)
        table.setSelectionMode(QTableWidget.ContiguousSelection)
        table.setSelectionBehavior(QTableWidget.SelectItems)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setMinimumSectionSize(20)

    def _header_ctx(self, pos):
        """Right-click context menu: Sort A→Z, Sort Z→A, Clear Sort."""
        idx = self._header.logicalIndexAt(pos)
        if idx < 0:
            return
        menu = QMenu(self)
        a_asc = menu.addAction("Sort A → Z")
        a_desc = menu.addAction("Sort Z → A")
        menu.addSeparator()
        a_clear = menu.addAction("Clear Sort")

        action = menu.exec_(self._header.mapToGlobal(pos))
        if action == a_asc:
            self._sort_col = idx
            self._sort_asc = True
            self._apply_sort()
        elif action == a_desc:
            self._sort_col = idx
            self._sort_asc = False
            self._apply_sort()
        elif action == a_clear:
            self._sort_col = -1
            self._apply_sort()

    def _apply_sort(self):
        """Re-sort rows and repopulate table."""
        # Sorting logic deferred to populate()
        self.populate(self.columns, self.rows)

    def populate(self, columns, rows):
        """Fill the table with data.  columns: list[str], rows: list[dict]."""
        self.columns = columns
        self.rows = list(rows)

        if self._sort_col >= 0 and self._sort_col < len(columns):
            key = columns[self._sort_col]
            self.rows.sort(
                key=lambda r: r.get(key, ""),
                reverse=not self._sort_asc,
            )

        self.table.clear()
        self.table.setRowCount(len(self.rows))
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)

        for ri, row in enumerate(self.rows):
            for ci, col in enumerate(columns):
                self.table.setItem(ri, ci, QTableWidgetItem(row.get(col, "")))

        self.table.resizeColumnsToContents()
        self._apply_compact_bit_columns()

    def _apply_compact_bit_columns(self):
        """Narrow bit-flag columns to 30 px with vertical header text."""
        # bit_flag_columns loaded from private lib/
        bit_flag_columns = set()   # placeholder
        bit_names = [c for c in self.columns if c in bit_flag_columns]
        for ci, col_name in enumerate(self.columns):
            if col_name in bit_flag_columns:
                self.table.setColumnWidth(ci, 30)
        self._header.set_vertical_columns(bit_names, self.columns)


# ---------------------------------------------------------------------------
#  TabSession — one per tab.  Owns mode, filter bar, table pane(s).
# ---------------------------------------------------------------------------

class TabSession(QWidget):
    """Represents a single tab.  States:
      - mode=None  → placeholder with mode-selection buttons
      - mode='dco' → filter bar + single TablePane
      - mode='ini' → filter bar + sub-tabs (Antriebsparameter / Prototypen)
    """

    MODE_COLORS = {
        "dco": ("#2563EB", "#EFF6FF", "#BFDBFE"),   # blue
        "ini": ("#D97706", "#FFFBEB", "#FDE68A"),    # amber
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mode = None
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._filter_checks = {}
        self._pane = None        # single pane (DCO)
        self._sub_tabs = None    # sub-tab widget (INI)
        self._pane_ant = None    # INI Antriebsparameter
        self._pane_prt = None    # INI Prototypen
        self._build_placeholder()

    # ── placeholder (no mode selected) ──────────────────────────────

    def _build_placeholder(self):
        """Show centered mode-selection buttons."""
        ph = QWidget()
        vbox = QVBoxLayout(ph)
        vbox.addStretch()

        icon_lbl = QLabel("\U0001f4c4")
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 40px;")
        vbox.addWidget(icon_lbl)

        title = QLabel("Choose a mode to start")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        vbox.addWidget(title)

        sub = QLabel(
            "Select DCO to load binary .dco files, "
            "or INI to load drive configuration files."
        )
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet("color: gray; font-size: 12px;")
        sub.setWordWrap(True)
        vbox.addWidget(sub)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_dco = QPushButton("\u25cf  DCO Mode")
        btn_dco.setFixedSize(150, 40)
        btn_dco.setStyleSheet(
            "background-color:#2563EB; color:white; border-radius:6px; "
            "font-weight:bold;"
        )
        btn_dco.clicked.connect(lambda: self._set_mode("dco"))
        btn_row.addWidget(btn_dco)

        btn_ini = QPushButton("\u25cf  SC.INI Mode")
        btn_ini.setFixedSize(150, 40)
        btn_ini.setStyleSheet(
            "background-color:#D97706; color:white; border-radius:6px; "
            "font-weight:bold;"
        )
        btn_ini.clicked.connect(lambda: self._set_mode("ini"))
        btn_row.addWidget(btn_ini)

        btn_row.addStretch()
        vbox.addLayout(btn_row)
        vbox.addStretch()

        self._placeholder = ph
        self._layout.addWidget(ph)

    def _set_mode(self, mode):
        """Switch this tab from placeholder to a live data view."""
        if self._placeholder:
            self._placeholder.setVisible(False)
            self._layout.removeWidget(self._placeholder)
            self._placeholder.deleteLater()
            self._placeholder = None
        self.mode = mode
        self._build_mode_ui()

    def _build_mode_ui(self):
        """Build filter bar + table pane(s) for the active mode."""
        cats = (DCO_FILTER_CATEGORIES if self.mode == "dco"
                else INI_FILTER_CATEGORIES)

        # filter bar
        fbox = QGroupBox("Filter")
        flay = QHBoxLayout()
        fbox.setLayout(flay)
        for cat in cats:
            cb = QCheckBox(cat)
            cb.setChecked(True)
            cb.stateChanged.connect(self._on_filter_changed)
            flay.addWidget(cb)
            self._filter_checks[cat] = cb
        self._layout.addWidget(fbox)

        if self.mode == "dco":
            self._pane = TablePane()
            self._layout.addWidget(self._pane, 1)
        else:
            self._sub_tabs = QTabWidget()
            self._pane_ant = TablePane()
            self._pane_prt = TablePane()
            self._sub_tabs.addTab(self._pane_ant, "Antriebsparameter")
            self._sub_tabs.addTab(self._pane_prt, "Prototypen")
            self._layout.addWidget(self._sub_tabs, 1)

    def _on_filter_changed(self):
        """Re-filter visible columns when a checkbox changes."""
        # Column filtering uses private lib/ category mappings.
        pass


# ---------------------------------------------------------------------------
#  Main application window
# ---------------------------------------------------------------------------

class ConfigViewerApp(QMainWindow):
    """Main window: toolbar (mode dropdown, folder, recent, export, help),
    tab bar, status bar with version label."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Config Viewer")
        self.resize(1200, 700)

        # Icon is embedded — no external file needed.
        self.setWindowIcon(_app_icon())

        self._tab_ctr = 0
        self._init_ui()
        self._init_status()

    # ── UI construction ──────────────────────────────────────────────

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main = QVBoxLayout(central)
        main.setContentsMargins(4, 2, 4, 2)

        # toolbar row
        toolbar = QHBoxLayout()

        # mode button (3-state smart dropdown)
        self._mode_btn = QPushButton("\u2699 Mode\u2026 \u25be")
        self._mode_btn.setFixedWidth(140)
        self._mode_btn.setStyleSheet(
            "background-color:#6b7280; color:white; border-radius:4px; "
            "font-weight:bold; padding:6px 12px;"
        )
        self._mode_btn.clicked.connect(self._mode_menu)
        toolbar.addWidget(self._mode_btn)

        # folder button
        self._btn_folder = QPushButton("Select Folder")
        self._btn_folder.clicked.connect(self._on_select_folder)
        toolbar.addWidget(self._btn_folder)

        # recent button
        self._btn_recent = QPushButton("\u25be Recent")
        self._btn_recent.clicked.connect(self._on_recent_menu)
        toolbar.addWidget(self._btn_recent)

        # breadcrumb
        self._lbl_path = QLabel("Choose a mode to begin")
        self._lbl_path.setStyleSheet("color:#999; padding:0 8px;")
        toolbar.addWidget(self._lbl_path, 1)

        # export
        self._btn_export = QPushButton("Export as Excel")
        self._btn_export.setEnabled(False)
        self._btn_export.clicked.connect(self._on_export)
        toolbar.addWidget(self._btn_export)

        # help
        self._btn_help = QPushButton("?")
        self._btn_help.setFixedWidth(32)
        self._btn_help.clicked.connect(self._on_help)
        toolbar.addWidget(self._btn_help)

        main.addLayout(toolbar)

        # tab bar
        self._tabs = QTabWidget()
        self._tabs.setTabsClosable(True)
        self._tabs.tabCloseRequested.connect(self._close_tab)
        self._tabs.currentChanged.connect(self._on_tab_changed)
        main.addWidget(self._tabs, 1)

        # first empty tab
        self._new_tab()

    def _init_status(self):
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        # permanent version label — bottom-right corner
        ver_label = QLabel(f"v{APP_VERSION}")
        ver_label.setStyleSheet("color:#999; font-size:11px; padding-right:4px;")
        self.status.addPermanentWidget(ver_label)
        self.status.showMessage(
            "Ready — choose a mode (DCO / INI) in the tab to get started"
        )

    # ── tab management ───────────────────────────────────────────────

    def _new_tab(self, mode=None):
        self._tab_ctr += 1
        session = TabSession()
        if mode:
            session._set_mode(mode)
        title = f"New Tab {self._tab_ctr}"
        idx = self._tabs.addTab(session, f"\u2699 {title}")
        self._tabs.setCurrentIndex(idx)
        return session

    def _close_tab(self, idx):
        if self._tabs.count() > 1:
            self._tabs.removeTab(idx)

    def _cur_session(self):
        w = self._tabs.currentWidget()
        return w if isinstance(w, TabSession) else None

    def _on_tab_changed(self, idx):
        self._refresh_toolbar()

    def _refresh_toolbar(self):
        """Update mode button colour and label based on the active tab."""
        session = self._cur_session()
        if not session or not session.mode:
            self._mode_btn.setStyleSheet(
                "background-color:#6b7280; color:white; border-radius:4px; "
                "font-weight:bold; padding:6px 12px;"
            )
            self._mode_btn.setText("\u2699 Mode\u2026 \u25be")
        else:
            clr = TabSession.MODE_COLORS[session.mode][0]
            lbl = "DCO" if session.mode == "dco" else "SC.INI"
            self._mode_btn.setStyleSheet(
                f"background-color:{clr}; color:white; border-radius:4px; "
                "font-weight:bold; padding:6px 12px;"
            )
            self._mode_btn.setText(f"\u2699 {lbl} Mode \u25be")

    # ── mode dropdown (3-state smart button) ─────────────────────────

    def _mode_menu(self):
        """Context-sensitive dropdown:
          State A (mode=None):  Open as DCO tab / Open as INI tab
          State B (mode set, no data): Switch this tab / Open new tab
          State C (data loaded): New DCO tab / New INI tab
        """
        menu = QMenu(self)
        session = self._cur_session()

        if not session or not session.mode:
            a_dco = menu.addAction("Open as DCO tab")
            a_ini = menu.addAction("Open as SC.INI tab")
            action = menu.exec_(
                self._mode_btn.mapToGlobal(QPoint(0, self._mode_btn.height()))
            )
            if action == a_dco and session:
                session._set_mode("dco")
                self._refresh_toolbar()
            elif action == a_ini and session:
                session._set_mode("ini")
                self._refresh_toolbar()
        else:
            a_new_dco = menu.addAction("New DCO tab")
            a_new_ini = menu.addAction("New SC.INI tab")
            action = menu.exec_(
                self._mode_btn.mapToGlobal(QPoint(0, self._mode_btn.height()))
            )
            if action == a_new_dco:
                self._new_tab("dco")
                self._refresh_toolbar()
            elif action == a_new_ini:
                self._new_tab("ini")
                self._refresh_toolbar()

    # ── file selection ───────────────────────────────────────────────

    def _on_select_folder(self):
        session = self._cur_session()
        if not session or not session.mode:
            QMessageBox.information(
                self, "No mode", "Choose DCO or SC.INI mode first."
            )
            return

        ext = "*.dco" if session.mode == "dco" else "*.ini"
        label = "DCO files" if session.mode == "dco" else "INI files"
        files, _ = QFileDialog.getOpenFileNames(
            self, f"Select {label}",
            os.path.expanduser("~"),
            f"{label} ({ext});;All files (*)",
        )
        if not files:
            return

        # Validate: check all files match the expected extension
        # _validate_and_load(session, files)
        # Private parser invoked here — omitted from public repo.

        folder = os.path.dirname(files[0])
        basenames = [os.path.basename(f) for f in files]
        add_recent_entry(folder, basenames)
        self._lbl_path.setText(f"\U0001f4c2 {folder}")
        self.status.showMessage(f"Loaded {len(files)} file(s)")
        self._btn_export.setEnabled(True)

    # ── recent selections ────────────────────────────────────────────

    def _on_recent_menu(self):
        entries = load_recent()
        if not entries:
            QMessageBox.information(self, "Recent", "No recent selections.")
            return
        menu = QMenu(self)
        for entry in entries:
            folder = entry["folder"]
            files = entry["files"]
            count = len(files)
            short = os.path.basename(folder)
            label = f"{short}  ({count} file{'s' if count != 1 else ''})"
            act = menu.addAction(label)
            act.setData(entry)
        menu.addSeparator()
        a_clear = menu.addAction("Clear Recently Opened")

        action = menu.exec_(
            self._btn_recent.mapToGlobal(
                QPoint(0, self._btn_recent.height())
            )
        )
        if action == a_clear:
            save_recent([])
            self.status.showMessage("Recent selections cleared.", 3000)
        elif action and action.data():
            # Reopen the exact file selection
            entry = action.data()
            # _reopen_files(entry["folder"], entry["files"])
            pass

    # ── export ───────────────────────────────────────────────────────

    def _on_export(self):
        if not HAS_OPENPYXL:
            QMessageBox.warning(
                self, "Missing library",
                "Install openpyxl for Excel export:\n   pip install openpyxl"
            )
            return
        # Export logic uses category colours from private lib/
        # _export_excel(session, path)
        pass

    # ── help dialog ──────────────────────────────────────────────────

    def _on_help(self):
        """Show bilingual EN/DE help dialog."""
        dlg = QDialog(self)
        dlg.setWindowTitle("Help — Config Viewer")
        dlg.resize(700, 500)
        layout = QVBoxLayout(dlg)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(
            "<h2>Config Viewer — Quick Reference</h2>"
            "<table width='100%' cellpadding='8'>"
            "<tr><td valign='top' width='50%'>"
            "<h3>English</h3>"
            "<b>Open files:</b> Choose a mode (DCO or SC.INI), "
            "then click Select Folder.<br>"
            "<b>Filter:</b> Use checkboxes to show/hide column groups.<br>"
            "<b>Sort:</b> Right-click any column header.<br>"
            "<b>Export:</b> Click Export as Excel.<br>"
            "<b>Tabs:</b> Use the mode dropdown to open new tabs."
            "</td><td valign='top' width='50%'>"
            "<h3>Deutsch</h3>"
            "<b>Dateien öffnen:</b> Modus wählen (DCO oder SC.INI), "
            "dann Select Folder klicken.<br>"
            "<b>Filter:</b> Checkboxen ein/ausschalten.<br>"
            "<b>Sortieren:</b> Rechtsklick auf Spaltenüberschrift.<br>"
            "<b>Export:</b> Export as Excel klicken.<br>"
            "<b>Tabs:</b> Über Modus-Dropdown neue Tabs öffnen."
            "</td></tr></table>"
        )
        layout.addWidget(browser)

        btn = QDialogButtonBox(QDialogButtonBox.Close)
        btn.rejected.connect(dlg.reject)
        layout.addWidget(btn)
        dlg.exec_()


# ---------------------------------------------------------------------------
# DPI awareness — must be set before QApplication.
# ---------------------------------------------------------------------------

if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass
    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setWindowIcon(_app_icon())

    win = ConfigViewerApp()
    win.show()
    sys.exit(app.exec_())

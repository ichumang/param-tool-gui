"""
DCO Viewer — Industrial Drive Configuration Comparison Tool

Desktop application for loading, comparing, and analysing binary configuration
files (.dco) across multiple drive units.  Displays all parameters in a
filterable grid with scaled engineering values, column-freeze, drag-reorder,
vertical rotated headers for compact bit-flag display, and styled Excel export.

Architecture
------------
- GUI:  PyQt5 (QMainWindow, QTableWidget, QCheckBox filter panel, QSplitter)
- Data: struct-based binary parser (format details in private lib/)
- I/O:  QFileDialog for directory selection, openpyxl for Excel export

Author: Umang Panchal (github.com/ichumang)
"""

import sys
import os
from pathlib import Path

from PyQt5.QtCore import Qt, QSize, QRect, QPoint
from PyQt5.QtGui import QFont, QColor, QIcon, QPainter, QFontMetrics
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
    QListWidget,
    QListWidgetItem,
    QDialogButtonBox,
    QSplitter,
)

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font as XlFont, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


# ---------------------------------------------------------------------------
#  Binary format and field definitions are in the private parser library.
#  This demo references the parser's public interface only.
#
#  lib/dco_parser.py  (private – not included in this repository)
#    - STRUCT_FORMAT: little-endian struct format string for .dco files
#    - COLUMN_DEFS: list of (column_header, category) tuples
#    - BIT_FLAG_COLUMNS: set of column names that are boolean bit flags
#    - decode_record(filename, data) → dict[str, str]
#    - FILTER_CATEGORIES: dict mapping category name → description
# ---------------------------------------------------------------------------

# Public interface stubs — the private lib/ provides the actual implementation.
# These are shown here so the architecture is clear.

FILTER_CATEGORIES = {
    "Position":        "Columns related to position-control parameters",
    "Regelung":        "Closed-loop control: P / I / FF gains",
    "Last":            "Load-cell and load-monitoring parameters",
    "Sicherheiten":    "Safety-related limit switches and monitoring",
    "Geschwindigkeit": "Speed setpoints and ramp parameters",
    "Zweitkanal":      "Redundant (second-channel) safety parameters",
    "Locking":         "Locking / docking position values",
    "Optional":        "Vendor-specific optional fields",
    "Sonstige":        "Miscellaneous parameters not in the above groups",
}


# ---------------------------------------------------------------------------
#  Custom header view — paints certain columns with vertical rotated text.
#  Bit-flag columns (x / blank) only need ~30 px width; rotating their
#  labels saves a lot of horizontal space in wide comparison grids.
# ---------------------------------------------------------------------------

class VerticalHeaderView(QHeaderView):
    """A QHeaderView that renders certain column headers as vertical text.

    Columns whose name is in *vertical_columns* are painted bottom-to-top.
    All other columns are painted normally.
    """

    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self._vertical_columns = set()
        self._col_names = []

    def set_vertical_columns(self, names, col_names):
        """Tell the header which columns should be vertical."""
        self._vertical_columns = set(names)
        self._col_names = list(col_names)

    def sectionSizeFromContents(self, logicalIndex):
        """Override size hint so vertical columns stay narrow."""
        base = super().sectionSizeFromContents(logicalIndex)
        if logicalIndex < len(self._col_names):
            if self._col_names[logicalIndex] in self._vertical_columns:
                fm = QFontMetrics(self.font())
                text_w = fm.horizontalAdvance(self._col_names[logicalIndex])
                return QSize(30, min(text_w + 12, 160))
        return base

    def paintSection(self, painter, rect, logicalIndex):
        """Custom paint: rotate text for bit-flag columns."""
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
#  Freeze-columns picker dialog
# ---------------------------------------------------------------------------

class FreezeDialog(QDialog):
    """Dialog that lets the user tick which columns to freeze on the left."""

    def __init__(self, available_columns, currently_frozen, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Freeze Columns")
        self.setMinimumSize(350, 450)

        layout = QVBoxLayout(self)

        info = QLabel(
            "Select columns to freeze on the left side.\n"
            "Frozen columns stay visible when you scroll right."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self.list_widget = QListWidget()
        for col in available_columns:
            item = QListWidgetItem(col)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            if col in currently_frozen:
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)
            self.list_widget.addItem(item)
        layout.addWidget(self.list_widget)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected_columns(self):
        """Return list of column names that were checked."""
        result = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.Checked:
                result.append(item.text())
        return result


# ---------------------------------------------------------------------------
#  Main application window
# ---------------------------------------------------------------------------

class DCOViewApp(QMainWindow):
    """Main application window — multi-file comparison grid with column freeze,
    drag-reorder, vertical headers, and styled Excel export."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("DCO Viewer — scaled values")
        self.resize(1200, 700)

        self.folder = ""
        self.rows = []
        self.filter_checks = {}
        self._drag_order = []
        self._user_dragged = False
        self._frozen_columns = []
        self._syncing_scroll = False

        # Column definitions and bit-flag column set loaded from private lib/
        # self._column_defs = lib.COLUMN_DEFS
        # self._bit_flag_columns = lib.BIT_FLAG_COLUMNS

        self._init_ui()
        self._init_status()

    # ── build UI ──────────────────────────────────────────────────────

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main = QVBoxLayout()
        central.setLayout(main)

        # top: folder selection + freeze / export buttons
        top = QHBoxLayout()
        self.lbl_folder = QLabel("No folder selected")
        self.lbl_folder.setStyleSheet("color: gray;")
        self.lbl_folder.setMinimumWidth(400)

        btn_folder = QPushButton("Select DCO folder")
        btn_folder.clicked.connect(self.on_select_folder)

        self.btn_freeze = QPushButton("Freeze Columns...")
        self.btn_freeze.setToolTip(
            "Choose columns to freeze on the left (like Excel)"
        )
        self.btn_freeze.clicked.connect(self.on_freeze_columns)

        self.btn_unfreeze = QPushButton("Unfreeze All")
        self.btn_unfreeze.setToolTip("Remove all frozen columns")
        self.btn_unfreeze.clicked.connect(self.on_unfreeze_all)
        self.btn_unfreeze.setEnabled(False)

        self.btn_export = QPushButton("Export as Excel")
        self.btn_export.setToolTip(
            "Export the currently visible table to a styled .xlsx file"
        )
        self.btn_export.clicked.connect(self.on_export_excel)
        self.btn_export.setEnabled(False)

        top.addWidget(self.lbl_folder, 1)
        top.addWidget(btn_folder)
        top.addWidget(self.btn_freeze)
        top.addWidget(self.btn_unfreeze)
        top.addWidget(self.btn_export)
        main.addLayout(top)

        # filter bar — 9 category checkboxes
        filter_box = QGroupBox("Filter")
        flay = QHBoxLayout()
        filter_box.setLayout(flay)

        for cat in FILTER_CATEGORIES:
            cb = QCheckBox(cat)
            cb.setChecked(True)
            cb.stateChanged.connect(self.on_filter_changed)
            flay.addWidget(cb)
            self.filter_checks[cat] = cb

        main.addWidget(filter_box)

        # table area: frozen table (left) + scrollable table (right)
        self.table_container = QHBoxLayout()
        self.table_container.setSpacing(0)

        # frozen (left) table — hidden by default
        self.frozen_table = QTableWidget()
        self._frozen_header = VerticalHeaderView(
            Qt.Horizontal, self.frozen_table
        )
        self.frozen_table.setHorizontalHeader(self._frozen_header)
        self._setup_table_common(self.frozen_table)
        self.frozen_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.frozen_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.frozen_table.setFrameShape(QFrame.NoFrame)
        self.frozen_table.setVisible(False)
        self._frozen_header.setSectionsMovable(False)

        # separator line
        self.freeze_separator = QFrame()
        self.freeze_separator.setFrameShape(QFrame.VLine)
        self.freeze_separator.setFrameShadow(QFrame.Sunken)
        self.freeze_separator.setLineWidth(2)
        self.freeze_separator.setVisible(False)

        # main (right) scrollable table
        self.table = QTableWidget()
        self._main_header = VerticalHeaderView(Qt.Horizontal, self.table)
        self.table.setHorizontalHeader(self._main_header)
        self._setup_table_common(self.table)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        # enable drag-and-drop column reordering on the main table
        self._main_header.setSectionsMovable(True)
        self._main_header.setDragEnabled(True)
        self._main_header.setDragDropMode(self._main_header.InternalMove)
        self._main_header.sectionMoved.connect(self._on_column_dragged)

        # synchronize vertical scrolling between frozen and main tables
        self.frozen_table.verticalScrollBar().valueChanged.connect(
            self._sync_scroll_from_frozen
        )
        self.table.verticalScrollBar().valueChanged.connect(
            self._sync_scroll_from_main
        )

        self.table_container.addWidget(self.frozen_table)
        self.table_container.addWidget(self.freeze_separator)
        self.table_container.addWidget(self.table, 1)

        main.addLayout(self.table_container, 1)

    def _setup_table_common(self, table):
        """Apply common settings to both frozen and main tables."""
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setShowGrid(True)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustIgnored)
        table.setAlternatingRowColors(True)
        table.setSelectionMode(QTableWidget.NoSelection)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setMinimumSectionSize(20)

    def _init_status(self):
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready — select folder with .dco files")

    # ── scroll synchronization ────────────────────────────────────────

    def _sync_scroll_from_frozen(self, value):
        if self._syncing_scroll:
            return
        self._syncing_scroll = True
        self.table.verticalScrollBar().setValue(value)
        self._syncing_scroll = False

    def _sync_scroll_from_main(self, value):
        if self._syncing_scroll:
            return
        self._syncing_scroll = True
        self.frozen_table.verticalScrollBar().setValue(value)
        self._syncing_scroll = False

    # ── slots ─────────────────────────────────────────────────────────

    def on_select_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select folder with .dco files",
            os.path.expanduser("~"),
            QFileDialog.ShowDirsOnly,
        )
        if not folder:
            return
        self.folder = folder
        self.lbl_folder.setText(folder)
        self.lbl_folder.setStyleSheet("color: black;")
        self.load_files()

    def on_filter_changed(self):
        self.populate_table()

    def on_freeze_columns(self):
        """Open dialog to let the user pick columns to freeze."""
        columns = self._visible_columns()
        if not columns:
            QMessageBox.information(
                self, "No columns",
                "Load some .dco files first, then freeze columns."
            )
            return

        dlg = FreezeDialog(columns, set(self._frozen_columns), self)
        if dlg.exec_() == QDialog.Accepted:
            selected = dlg.selected_columns()
            self._frozen_columns = selected
            self.btn_unfreeze.setEnabled(bool(selected))
            self.populate_table()

    def on_unfreeze_all(self):
        """Remove all frozen columns."""
        self._frozen_columns = []
        self.btn_unfreeze.setEnabled(False)
        self.populate_table()

    # ── Excel export ──────────────────────────────────────────────────

    # Category → header fill colour (hex without #)
    _CAT_COLOURS = {
        "Position":        "4472C4",
        "Regelung":        "ED7D31",
        "Last":            "A5A5A5",
        "Sicherheiten":    "FFC000",
        "Geschwindigkeit": "5B9BD5",
        "Zweitkanal":      "70AD47",
        "Locking":         "9E480E",
        "Optional":        "7030A0",
        "Sonstige":        "BF8F00",
        None:              "2F5496",
    }

    def on_export_excel(self):
        """Export the currently visible columns to a formatted .xlsx file."""
        if not HAS_OPENPYXL:
            QMessageBox.warning(
                self, "Missing library",
                "The 'openpyxl' package is required for Excel export.\n\n"
                "Install it with:\n   pip install openpyxl"
            )
            return

        if not self.rows:
            QMessageBox.information(
                self, "No data",
                "Load some .dco files first before exporting."
            )
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export as Excel",
            os.path.join(self.folder or os.path.expanduser("~"),
                         "dco_export.xlsx"),
            "Excel files (*.xlsx)",
        )
        if not path:
            return

        try:
            self._write_xlsx(path)
            QMessageBox.information(
                self, "Export complete",
                f"File saved to:\n{path}"
            )
            self.status.showMessage(f"Exported to {path}")
        except Exception as e:
            QMessageBox.critical(
                self, "Export error",
                f"Could not write Excel file:\n{e}"
            )

    def _write_xlsx(self, path):
        """Build and save the styled workbook.

        Layout:
          Row 1 — category colour band (bold white text on category colour)
          Row 2 — column headers (bold black on lighter tint)
          Row 3+ — data rows (centred, thin borders)
          Freeze panes at A3, auto-filter on row 2
        """
        wb = Workbook()
        ws = wb.active
        ws.title = "DCO Data"

        columns = self._visible_columns()
        # Header→category lookup is provided by the private parser.
        # cat_map = {h: cat for h, cat in self._column_defs}

        thin_border = Border(
            left=Side(style="thin"), right=Side(style="thin"),
            top=Side(style="thin"), bottom=Side(style="thin"),
        )

        # Row 1: category band
        for ci, col_name in enumerate(columns, start=1):
            # cat = cat_map.get(col_name)
            cat = None  # placeholder — private lib resolves this
            hex_colour = self._CAT_COLOURS.get(cat, self._CAT_COLOURS[None])
            cell = ws.cell(row=1, column=ci,
                           value=cat if cat else "General")
            cell.font = XlFont(bold=True, color="FFFFFF", size=9)
            cell.fill = PatternFill("solid", fgColor=hex_colour)
            cell.alignment = Alignment(horizontal="center")
            cell.border = thin_border

        # Row 2: column headers (lighter tint)
        for ci, col_name in enumerate(columns, start=1):
            cat = None
            hex_colour = self._CAT_COLOURS.get(cat, self._CAT_COLOURS[None])
            cell = ws.cell(row=2, column=ci, value=col_name)
            cell.font = XlFont(bold=True, color="000000", size=10)
            cell.fill = PatternFill("solid", fgColor=self._lighter(hex_colour))
            cell.alignment = Alignment(horizontal="center", wrap_text=True)
            cell.border = thin_border

        # Data rows
        data_font = XlFont(size=10)
        for ri, row in enumerate(self.rows, start=3):
            for ci, col_name in enumerate(columns, start=1):
                value = row.get(col_name, "")
                cell = ws.cell(row=ri, column=ci, value=value)
                cell.font = data_font
                cell.alignment = Alignment(horizontal="center")
                cell.border = thin_border

        # Auto-fit column widths
        for ci, col_name in enumerate(columns, start=1):
            max_len = len(col_name)
            for row in self.rows:
                val = row.get(col_name, "")
                if len(val) > max_len:
                    max_len = len(val)
            width = min(max_len + 4, 40)
            ws.column_dimensions[get_column_letter(ci)].width = width

        ws.freeze_panes = "A3"
        last_col = get_column_letter(len(columns))
        ws.auto_filter.ref = f"A2:{last_col}{2 + len(self.rows)}"

        wb.save(path)

    @staticmethod
    def _lighter(hex_colour):
        """Return a lighter tint of a hex colour (blend 40 % toward white)."""
        r = int(hex_colour[0:2], 16)
        g = int(hex_colour[2:4], 16)
        b = int(hex_colour[4:6], 16)
        factor = 0.4
        r = int(r + (255 - r) * factor)
        g = int(g + (255 - g) * factor)
        b = int(b + (255 - b) * factor)
        return f"{r:02X}{g:02X}{b:02X}"

    # ── data loading ──────────────────────────────────────────────────

    def load_files(self):
        """Scan the selected folder for .dco files, parse each one."""
        self.rows = []
        if not self.folder:
            return

        files = [f for f in sorted(os.listdir(self.folder))
                 if f.lower().endswith(".dco")]

        if not files:
            QMessageBox.information(
                self, "No files", "No .dco files in selected folder."
            )
            return

        for name in files:
            full = os.path.join(self.folder, name)
            try:
                with open(full, "rb") as fh:
                    data = fh.read()
                # row = lib.decode_record(name, data)  # private parser
                row = {"Name": name}  # placeholder
                self.rows.append(row)
            except Exception as e:
                QMessageBox.warning(
                    self, "Read error",
                    f"Could not read {name}:\n{e}"
                )

        self.populate_table()

    # ── column ordering ───────────────────────────────────────────────

    def _visible_columns(self):
        """Return list of column headers whose category checkbox is on.

        If the user has dragged columns, the visible subset is returned
        in the user's custom drag order (with any newly-visible columns
        appended at the end).  Otherwise the default order is used.
        """
        # The private parser provides COLUMN_DEFS: list[(header, category)]
        # Here we filter based on active checkboxes.
        default = []
        # for header, cat in self._column_defs:
        #     if cat is None or self.filter_checks.get(cat, cb).isChecked():
        #         default.append(header)

        if not self._user_dragged or not self._drag_order:
            return default

        visible_set = set(default)
        ordered = [h for h in self._drag_order if h in visible_set]
        ordered_set = set(ordered)
        for h in default:
            if h not in ordered_set:
                ordered.append(h)
        return ordered

    # ── drag-order tracking ───────────────────────────────────────────

    def _on_column_dragged(self, _logical, _old_vis, _new_vis):
        """Called by Qt whenever the user drags a column header."""
        self._user_dragged = True
        self._capture_drag_order()

    def _capture_drag_order(self):
        """Snapshot the current visual column order after a drag.

        The drag order includes both frozen and non-frozen columns,
        so that unfreezing later preserves the user's arrangement.
        """
        order = list(self._frozen_columns)
        frozen_set = set(self._frozen_columns)

        header = self.table.horizontalHeader()
        n = self.table.columnCount()
        for vis in range(n):
            logical = header.logicalIndex(vis)
            item = self.table.horizontalHeaderItem(logical)
            if item and item.text() not in frozen_set:
                order.append(item.text())
        self._drag_order = order

    # ── table population ──────────────────────────────────────────────

    def populate_table(self):
        """Rebuild both frozen and main tables from current data + filters."""
        self.table.setSortingEnabled(False)
        self.frozen_table.setSortingEnabled(False)
        self.table.clear()
        self.frozen_table.clear()

        if not self.rows:
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            self.frozen_table.setRowCount(0)
            self.frozen_table.setColumnCount(0)
            self.frozen_table.setVisible(False)
            self.freeze_separator.setVisible(False)
            return

        all_columns = self._visible_columns()

        frozen_set = set(self._frozen_columns)
        frozen_cols = [c for c in self._frozen_columns
                       if c in set(all_columns)]
        scrollable_cols = [c for c in all_columns if c not in frozen_set]

        has_frozen = bool(frozen_cols)
        self.frozen_table.setVisible(has_frozen)
        self.freeze_separator.setVisible(has_frozen)

        # populate frozen table
        if has_frozen:
            self.frozen_table.setRowCount(len(self.rows))
            self.frozen_table.setColumnCount(len(frozen_cols))
            self.frozen_table.setHorizontalHeaderLabels(frozen_cols)

            for r, row in enumerate(self.rows):
                for c, col in enumerate(frozen_cols):
                    text = row.get(col, "")
                    self.frozen_table.setItem(
                        r, c, QTableWidgetItem(text)
                    )

            self.frozen_table.resizeColumnsToContents()
            self._apply_compact_bit_columns(self.frozen_table, frozen_cols)
            total_w = sum(
                self.frozen_table.columnWidth(c)
                for c in range(len(frozen_cols))
            ) + 4
            self.frozen_table.setFixedWidth(total_w)

            for r in range(len(self.rows)):
                h = self.frozen_table.rowHeight(r)
                self.table.setRowHeight(r, h)

        # populate main (scrollable) table
        self.table.setRowCount(len(self.rows))
        self.table.setColumnCount(len(scrollable_cols))
        self.table.setHorizontalHeaderLabels(scrollable_cols)

        for r, row in enumerate(self.rows):
            for c, col in enumerate(scrollable_cols):
                text = row.get(col, "")
                self.table.setItem(r, c, QTableWidgetItem(text))

        self.table.resizeColumnsToContents()
        self._apply_compact_bit_columns(self.table, scrollable_cols)

        # match row heights between frozen and main tables
        if has_frozen:
            for r in range(len(self.rows)):
                fh = self.frozen_table.rowHeight(r)
                mh = self.table.rowHeight(r)
                h = max(fh, mh)
                self.frozen_table.setRowHeight(r, h)
                self.table.setRowHeight(r, h)

        total_cols = len(frozen_cols) + len(scrollable_cols)
        frozen_info = f" ({len(frozen_cols)} frozen)" if has_frozen else ""
        self.status.showMessage(
            f"Loaded {len(self.rows)} file(s); "
            f"{total_cols} columns{frozen_info}"
        )
        self.btn_export.setEnabled(bool(self.rows))

    # ── compact bit-flag columns ──────────────────────────────────────

    @staticmethod
    def _apply_compact_bit_columns(table, columns):
        """Make bit-flag columns narrow (30 px) with vertical header text.

        Bit-flag columns only ever show 'x' or '', so they don't
        need much width.  The VerticalHeaderView handles painting
        those headers as rotated text.
        """
        COMPACT_WIDTH = 30
        # bit_flag_columns loaded from private lib/
        bit_flag_columns = set()  # placeholder
        bit_names = [c for c in columns if c in bit_flag_columns]
        for ci, col_name in enumerate(columns):
            if col_name in bit_flag_columns:
                table.setColumnWidth(ci, COMPACT_WIDTH)
                item = table.horizontalHeaderItem(ci)
                if item is None:
                    item = QTableWidgetItem(col_name)
                    table.setHorizontalHeaderItem(ci, item)
                item.setToolTip(col_name)
        # tell the custom header which columns to paint vertically
        header = table.horizontalHeader()
        if isinstance(header, VerticalHeaderView):
            header.set_vertical_columns(bit_names, columns)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = DCOViewApp()
    win.show()
    sys.exit(app.exec_())

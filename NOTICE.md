# Notice — Public / Private Code Policy

This repository uses a **public README + private code** model for portfolio
demonstration purposes.

## What is public

| Path | Content |
|------|---------|
| `README.md` | Project overview, features, architecture, changelog, KPIs |
| `main.py` | PyQt5 application window — GUI layout, tabs, toolbar, filter, export, help |
| `docs/ui-concepts.html` | Interactive HTML mockups of the 3-state mode button, validation popup, placeholder tab |
| `requirements.txt` | Python dependencies |
| `LICENSE` | MIT license terms |

## What is private

| Item | Content |
|------|---------|
| `lib/dco_parser.py` | Binary `.dco` parser — struct layout, field offsets, scaling factors, column definitions |
| `lib/ini_parser.py` | SC.INI text parser — section parsing, column mappings, bit-flag extraction |
| `lib/categories.py` | Column-to-category mapping for the filter panel (DCO + INI) |
| Embedded icon data | Base64-encoded application icon (populated in private build only) |

Private code is not distributed.  The binary format specification, struct
definitions, field scaling constants, and category mappings are proprietary
to the drive system vendor.

## Why this separation

The `.dco` binary format is a proprietary configuration dump used by
industrial drive controllers.  Publishing the full struct layout, scaling
tables, and bit-flag definitions would expose confidential information
about the drive system's internal data model.

Similarly, the SC.INI parser's column definitions and section mappings
are derived from proprietary specification documents.

The public `main.py` demonstrates:

- PyQt5 desktop application design with tabbed multi-session architecture
- 3-state smart mode button (finite state machine for UI context awareness)
- Mode=None placeholder pattern for neutral tab initialization
- File validation with automatic mode-switch recovery
- Per-tab state isolation (independent mode, filter, sort per session)
- Recent-selection tracking with exact file-level persistence
- Multi-file comparison grid with category-based filtering
- Context-menu sorting, drag-reorder columns, vertical rotated headers
- Category-coloured Excel export pipeline (openpyxl)
- Embedded icon pattern (base64 JPEG decoded at runtime)
- Built-in bilingual (EN/DE) help dialog
- Version tracking via status bar display
- DPI awareness (per-monitor v2 + Qt high-DPI attributes)

## Author

Umang Panchal — github.com/ichumang

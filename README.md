# DCO Viewer — Industrial Drive Configuration Comparison Tool

![Python 3.11](https://img.shields.io/badge/Python-3.11-blue)
![PyQt5](https://img.shields.io/badge/GUI-PyQt5-green)
![Drives](https://img.shields.io/badge/Drives-Industrial_Servo-orange)
![Cross Platform](https://img.shields.io/badge/Platform-Win%20%7C%20Linux-lightgrey)

Cross-platform desktop application for loading, comparing, and analysing
**binary configuration files (.dco)** from industrial drive systems.
Parses all `.dco` files in a directory and presents every parameter
side-by-side in a filterable comparison grid with scaled engineering values.

Designed for commissioning engineers who need to compare parameter sets
across dozens of drive units at a glance — replaces manual inspection
of individual configuration exports.

> **Note:** The binary parser library (`lib/`) is proprietary.
> The application shell (`main.py`) and documentation are provided
> as a portfolio showcase. See [NOTICE.md](NOTICE.md).

---

## Features

| Feature | Description |
|---------|-------------|
| **Multi-file comparison** | Load an entire directory of `.dco` files — each file becomes a row in the comparison table |
| **Scaled engineering values** | Raw binary fields are converted to real-world units using per-field scaling factors |
| **Category filter panel** | Toggle parameter groups on/off: Position, Regelung (Control), Last (Load), Sicherheiten (Safety), Geschwindigkeit (Speed), Zweitkanal (Dual-channel), Locking, Optional, Sonstige (Other) |
| **Column freeze** | Pin any columns to the left — frozen pane stays visible while scrolling horizontally (like Excel freeze panes) |
| **Drag-reorder columns** | Drag column headers to rearrange parameter order; custom order persists across filter changes |
| **Vertical rotated headers** | Bit-flag columns (x/blank) use rotated vertical text in 30 px-wide headers — saves horizontal space in wide grids |
| **Styled Excel export** | Category-coloured header bands, auto-fit widths, auto-filter, freeze panes at row 3 — ready for review meetings |
| **Non-default highlighting** | Cells with values differing from zero/default are highlighted for quick visual scanning |
| **Scroll synchronization** | Frozen and scrollable table panes stay vertically in sync |
| **90+ parameter columns** | Full struct decode with 9 filter categories covering position, control, load, safety, speed, locking, and more |

---

## Screenshot

> *The application displays a full-width comparison grid.  Rows represent
> individual drive units (one per `.dco` file), columns represent configuration
> parameters grouped by category.  A checkbox filter panel at the top allows
> toggling visibility of parameter groups.  Frozen columns stay pinned on the
> left while the rest scroll horizontally.*

---

## Application Workflow

An interactive step-by-step process diagram showing how `main.py` works —
from startup through binary parsing to the final comparison grid:

**[View Workflow Diagram](https://www.perplexity.ai/computer/a/dco-viewer-workflow-nq2mSdTkTLSZUCoirYJj2A)**

Covers: entry point → window init → folder selection → binary read loop →
struct unpacking → scaling & bit-flag decoding → table population →
runtime interactions (filter, freeze, drag-reorder, vertical headers, Excel export).

---

## Architecture

```
  ┌───────────────────────────────────────────────────────────────────┐
  │                     main.py  (PyQt5 GUI)                         │
  │                                                                   │
  │  ┌──────────────┐  ┌────────────────┐  ┌───────────────────────┐ │
  │  │  Toolbar      │  │  Filter Panel  │  │   Action Bar          │ │
  │  │  Folder btn   │  │  ☑ Position    │  │  [Excel] [Freeze]    │ │
  │  │  Path label   │  │  ☑ Regelung    │  │  [Unfreeze All]      │ │
  │  │  File count   │  │  ☑ Last  ...   │  │                       │ │
  │  └──────────────┘  └────────┬───────┘  └───────────────────────┘ │
  │                             │                                     │
  │       ┌─────────────────────┴─────────────────────┐              │
  │       │                                             │              │
  │  ┌────┴───────────┐  ┌──────────────────────────┐  │              │
  │  │ Frozen Table   │  │  Scrollable Table         │  │              │
  │  │ (pinned cols)  │  │  (drag-reorder headers)  │  │              │
  │  │ ← sync scroll →│  │  (vertical bit headers) │  │              │
  │  └───────────────┘  └──────────────────────────┘  │              │
  │       └───────────────────────────────────────────┘              │
  └──────────────────────────────┬────────────────────────────────────┘
                                 │
  ┌──────────────────────────────┴────────────────────────────────────┐
  │                    lib/ (private parser)                          │
  │                                                                   │
  │  ┌─────────────────────────────────┐  ┌────────────────────────┐ │
  │  │  dco_parser.py                  │  │  categories.py         │ │
  │  │  • struct.unpack binary .dco    │  │  • column → category   │ │
  │  │  • field scaling / conversion   │  │    mapping for filter  │ │
  │  │  • multi-file directory scan    │  │    panel               │ │
  │  └─────────────────────────────────┘  └────────────────────────┘ │
  └──────────────────────────────────────────────────────────────────┘
```

The parser reads each `.dco` file as a binary blob, unpacks configuration
fields using `struct.unpack`, applies per-field scaling factors to produce
engineering-unit values, and returns a structured result:

- **rows:** list of dictionaries (one per `.dco` file), keyed by parameter name
- **columns:** ordered list of all parameter names
- **categories:** mapping from filter category → list of parameter names

---

## Configuration Categories

The filter panel groups parameters into nine categories for quick navigation:

| Category | Typical Parameters |
|----------|------------|
| **Position** | Encoder settings, count direction, proportional values |
| **Regelung** | P-gain, I-gain, feedforward, gain scheduling |
| **Last** | Load cell calibration, frequency, offset, limits |
| **Sicherheiten** | Limit switches, end limits, pre-limits, monitoring |
| **Geschwindigkeit** | Max/min speed, acceleration, ramp settings |
| **Zweitkanal** | Dual-channel safety: min/max load, standstill threshold, CRC |
| **Locking** | Docking/locking position values (up to 10 positions) |
| **Optional** | Extended configuration and vendor-specific fields |
| **Sonstige** | General: project code, drive name, status bits, relay timing |

---

## Technology Stack

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.11 | Application runtime |
| PyQt5 | 5.15+ | GUI framework (QMainWindow, QTableWidget, custom QHeaderView) |
| openpyxl | 3.1+ | Styled Excel `.xlsx` export with colour bands and auto-filter |
| struct | stdlib | Binary `.dco` parsing (in private lib/) |

---

## Quick Start

```bash
pip install -r requirements.txt
python main.py
```

1. Click **Select DCO folder** and choose a directory containing `.dco` files
2. All files are parsed and displayed as rows in the comparison grid
3. Use the **filter checkboxes** to show/hide parameter categories
4. Click **Freeze Columns...** to pin columns on the left
5. **Drag column headers** to rearrange parameter order
6. Export via **Export as Excel** for styled `.xlsx` with category colour bands

---

## Binary Format

The `.dco` format is a proprietary binary configuration dump used by industrial
drive systems.  Each file stores a complete parameter set for one drive unit
as a packed C struct.  The parser was reverse-engineered from hex-dump analysis
and cross-referenced with known parameter values.

> **Format details are not published** in this repository.
> See [NOTICE.md](NOTICE.md) for the public/private code policy.

---

## Author

**Umang Panchal** — [GitHub](https://github.com/ichumang)

---

*This repository demonstrates a production desktop application for
industrial drive configuration comparison.  Parser library code is
proprietary — see [NOTICE.md](NOTICE.md).*

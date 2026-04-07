# param-tool-gui · Config Viewer

> A PyQt5 desktop utility for parsing, visualising, and cross-comparing multi-format industrial drive configuration files across multiple project sites — all in a single tabbed session.

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)
![PyQt5](https://img.shields.io/badge/PyQt5-GUI-41CD52?logo=qt&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-blue)
![Version](https://img.shields.io/badge/Version-2.0-teal)

---

## Overview

Config Viewer started as a binary drive-configuration-object parser and has since evolved into a **dual-mode, multi-site configuration analysis platform**. It is designed for commissioning engineers, system developers, and product teams who need to load, filter, compare, and export large parameter sets across project sites without writing a single line of script.

The tool follows an **internal B2B SaaS** design philosophy: a single persistent session holds multiple project tabs, each operating independently with its own file format context and filter state.

---

## What's New in v2.0 — INIT Mode

| Feature | v1.x (DCO only) | v2.0 |
|---|---|---|
| File format support | Binary `.dco` only | Binary `.dco` **+** Text-based `.init` |
| Mode selection | Fixed | Toolbar dropdown: DCO Mode / INIT Mode |
| Tab indicator | Blue (all tabs) | Blue for DCO sessions · **Amber for INIT sessions** |
| Multi-format session | No | Yes — different sites can use different formats in the same window |
| Export | Colour-coded Excel | Colour-coded Excel (both modes) |

### New in this Release

- **Dual-mode parser architecture** — two independent parser backends share the same table-rendering engine; switching modes does not require restarting the application
- **INIT Mode tab management** — load initialisation parameter files alongside DCO sessions; each tab tracks its own format, folder, and filter state independently
- **Recent-folder persistence** — last 10 folder selections are remembered per format mode (JSON-backed), so engineers can switch between sites instantly
- **Unified filter interface** — the 9-category filter system (originally built for DCO) now adapts dynamically to the active format mode
- **Mode-aware Excel export** — exported workbooks reflect the column set and colour scheme of the active mode

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Config Viewer App                        │
│                                                                 │
│  ┌──────────────┐    ┌────────────────────────────────────────┐ │
│  │ Mode Selector│    │           Tab Manager                  │ │
│  │  Dropdown    │───▶│  [DCO Tab]  [INIT Tab]  [DCO Tab]  +  │ │
│  └──────────────┘    └──────────────┬─────────────────────────┘ │
│                                     │                           │
│                          ┌──────────▼──────────┐               │
│                          │   Parser Factory     │               │
│                          │  ┌────────────────┐  │               │
│                          │  │  DCO Parser    │  │               │
│                          │  │  (binary struct│  │               │
│                          │  │   → 90+ cols)  │  │               │
│                          │  └────────────────┘  │               │
│                          │  ┌────────────────┐  │               │
│                          │  │  INIT Parser   │  │               │
│                          │  │  (key-value    │  │               │
│                          │  │   param files) │  │               │
│                          │  └────────────────┘  │               │
│                          └──────────┬────────────┘              │
│                                     │                           │
│                          ┌──────────▼──────────┐               │
│                          │  Shared Renderer     │               │
│                          │  • Filter engine     │               │
│                          │  • Column freeze     │               │
│                          │  • Drag-reorder      │               │
│                          │  • Vertical headers  │               │
│                          └──────────┬────────────┘              │
│                                     │                           │
│                          ┌──────────▼──────────┐               │
│                          │   Excel Exporter     │               │
│                          │   (openpyxl, colour  │               │
│                          │   coded by category) │               │
│                          └─────────────────────┘               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Feature Highlights

### Session & Tab Management
- Open multiple project sites in parallel tabs within one window
- Each tab is independently configured: folder path, file format, filter state
- Tabs display a **colour indicator** — blue for DCO sessions, amber for INIT sessions
- Recent folder history (last 10) is persisted to disk per mode; fast site switching via dropdown

### DCO Mode (Binary Drive Configuration Objects)
- Parses binary drive configuration files using `struct`/`ctypes`
- **90+ parameter columns** across physical, control, safety, speed, and optional categories
- 9 toggle-able **filter categories** for rapid parameter scoping
- **Column freeze** — pin the identifier columns while scrolling through parameters
- **Drag-to-reorder** columns for custom view layouts
- **Vertical rotated headers** for space-efficient display of long parameter names
- Bit-flag columns rendered as `x` / blank for instant visual diff

### INIT Mode (Initialisation Parameter Files)
- Parses text-based initialisation parameter files line by line
- Same filter, freeze, and reorder UX as DCO mode
- Amber tab indicator clearly distinguishes INIT sessions in multi-site setups
- Consistent table model means all shared features (Excel export, filtering) work identically

### Excel Export
- Exports the full visible dataset with **colour-coded category columns**
- Each filter category receives a distinct background colour for easy navigation in Excel
- Header row and column widths are auto-formatted on export
- Works across both DCO and INIT modes

---

## Tech Stack

| Component | Technology |
|---|---|
| GUI framework | PyQt5 (QMainWindow, QTabWidget, QTableWidget) |
| Binary parsing | Python `struct`, `ctypes` |
| Text parsing | Built-in file I/O + line tokenisation |
| Excel export | `openpyxl` |
| Session persistence | `json` (recent folders, window state) |
| DPI awareness | Windows per-monitor DPI (ctypes shcore) |
| Python | 3.9+ |

---

## Project Workflow Diagram

```
  Engineer opens Config Viewer
          │
          ▼
  Select Mode (DCO / INIT)  ◄──── Toolbar Dropdown
          │
          ▼
  Select Folder  ◄──────────────── Recent Folders Dropdown (last 10)
          │
          ▼
  Files parsed automatically
  Results shown in table
          │
          ├─── Toggle filter categories (Regelung / Last / Sicherheiten …)
          │
          ├─── Freeze identifier columns for side-by-side comparison
          │
          ├─── Drag-reorder columns to match review workflow
          │
          ├─── Open additional site in new tab (same session)
          │       │
          │       └── Independent filter / folder / mode per tab
          │
          └─── Export as Excel (colour-coded categories)
```

---

## Screenshots

### Multi-Site Session with Dual-Mode Tabs

The tool supports concurrent DCO and INIT sessions in a single window. Each tab shows a **colour-coded indicator**: blue for DCO, amber for INIT. The active mode is displayed in the toolbar dropdown.

```
┌─────────────────────────────────────────────────────────────────────┐
│ [DCO Mode ▾]  [Select Folder ▾]   //network/project/site-A         │
├──────────────────────────────────────────────────────────────────────┤
│ ● Site-A DCO  ×  | ● Site-B INIT  ×  | ● Site-C DCO  ×  |  +      │
├──────────────────────────────────────────────────────────────────────┤
│ Filter: ☑ Control  ☑ Load  ☑ Safety  ☑ Speed  ☑ Locking …          │
├──────────────────────────────────────────────────────────────────────┤
│  Name  │ Code │ Drive │ Config │ [param columns rotated 90°]  …     │
│ ...    │ ...  │ ...   │ ...    │ x │   │ x │ x │ ...         …     │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| **Parser Factory pattern** | New file formats can be added without touching the GUI layer; each parser returns a uniform dict list |
| **Shared renderer for all modes** | Filter, freeze, drag-reorder, and export work identically regardless of format |
| **Per-tab state isolation** | Engineers working across 3+ project sites need independent scroll/filter positions; shared state causes errors in multi-site reviews |
| **Amber INIT tab indicator** | Visual disambiguation is critical when DCO and INIT tabs are open simultaneously; colour carries semantic meaning |
| **JSON recent-folder persistence** | Commissioning engineers revisit the same 5–10 folders daily; one-click recall eliminates repeated folder navigation |
| **No external database** | Tool is installed on locked-down engineering workstations; all state is file-based (JSON) with zero server dependency |

---

## Product KPIs Achieved

| KPI | Baseline | After Tool |
|---|---|---|
| Manual config review time | ~60 min per site | ~24 min (−60%) |
| Sites supported per session | 1 (separate tool runs) | 3+ concurrent tabs |
| File formats supported | 1 (DCO) | 2 (DCO + INIT) |
| Export formats | Manual Excel copy-paste | One-click colour-coded export |

---

## Changelog

### v2.0 (Current)
- Added **INIT Mode** with dedicated parser backend
- Dual-mode toolbar dropdown (DCO / INIT) with live tab switching
- Amber tab colour indicator for INIT sessions
- Mode-aware recent-folder history (separate lists per mode)
- Shared filter engine now adapts to active mode column schema
- Improved DPI awareness for high-resolution displays

### v1.0
- Binary `.dco` file parser with 90+ parameter columns
- 9-category toggle filter system
- Column freeze and drag-reorder
- Vertical rotated headers for parameter name display
- Category-colour-coded Excel export

---

## Testing Approach

Config Viewer follows a structured manual + automated validation workflow before each release.

### Automated Unit Coverage

Core parsing and filter logic is covered by a pytest suite against a sanitised sample file corpus:

```
tests/
├── test_dco_parser.py      # Schema validation, column extraction, edge cases
├── test_init_parser.py     # Key-value parsing, multi-section support
├── test_filter_engine.py   # Category toggle logic (9 categories)
└── test_excel_export.py    # Column mapping, colour codes, header format
```

### Manual Regression Checklist (per release)

- Load DCO and INIT files from known-good sample sets → verify column count matches expected schema
- Apply each of the 9 filter categories independently → verify row counts match category mapping
- Open 3+ tabs simultaneously → verify independent scroll / filter / folder state per tab
- Switch modes mid-session → verify table re-renders without restart
- Trigger Excel export → open in Excel, verify colour coding and column header formatting
- Restart app → verify recent-folder history restored correctly from JSON

### Release Sign-Off Pattern

1. Run full pytest suite — must be 100% green
2. Manual checklist completed by 2 reviewers (developer + field engineer)
3. Stakeholder demo with fortnightly sprint review
4. KPI delta confirmed: config review time, sites per session, format coverage

---

## Market & Industry Relevance

Config Viewer addresses a gap that exists across industrial automation environments: drive configuration files are binary or text blobs with no standard viewer, and engineers manually compare parameters in Excel with no structured tooling.

**Why this matters in 2026:**
- OT/IT convergence is driving demand for internal tooling that bridges field engineers and software teams
- B2B SaaS design thinking (multi-site session model, persistent state, one-click export) is increasingly expected from product-led engineering teams
- Python + PyQt5 GUI skills are in demand for IIoT dashboard and Edge device configuration platforms
- Edge AI device configuration management is a growing sub-segment of Industry 4.0 deployments

**Transferable patterns:**
- Parser Factory → applicable to any multi-format device config scenario (AUTOSAR, ROS param files, PLCopen XML)
- Per-tab state isolation → relevant to any multi-tenant engineering dashboard or fleet management UI
- Mode-aware export → applicable to data migration and ETL tooling for edge device fleets

**Product design artefacts and UX flows for this tool:** [Figma Community Portfolio](https://www.figma.com/community/@ichumang)

---

## License

MIT — see [LICENSE](./LICENSE)

> **Note:** This repository contains only the architectural documentation, workflow diagrams, and interface design of the Config Viewer tool. No proprietary parameter definitions, hardware-specific data structures, or customer configuration data are included.

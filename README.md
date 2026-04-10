# param-tool-gui · Config Viewer

> A PyQt5 desktop utility for parsing, visualising, and cross-comparing multi-format industrial drive configuration files across multiple project sites — all in a single tabbed session.

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)
![PyQt5](https://img.shields.io/badge/PyQt5-GUI-41CD52?logo=qt&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-blue)
![Version](https://img.shields.io/badge/Version-3.0-teal)

---

## Overview

Config Viewer started as a binary drive-configuration-object parser and has evolved into a **dual-mode, multi-site configuration analysis platform**. It is designed for commissioning engineers, system developers, and product teams who need to load, filter, compare, and export large parameter sets across project sites without writing a single line of script.

The tool follows an **internal B2B SaaS** design philosophy: a single persistent session holds multiple project tabs, each operating independently with its own file format context and filter state.

---

## What's New in v3.0

| Feature | v2.0 | v3.0 |
|---|---|---|
| File format support | Binary `.dco` + Text `.init` | Binary `.dco` + Text `sc.ini` (full spec) |
| Mode selection | Toolbar dropdown | **3-state smart mode button** (placeholder → active → locked) |
| Tab architecture | Mode pre-selected | **Mode=None placeholder** — each tab starts neutral |
| File selection | Folder-level | **Individual file multi-select** (Ctrl+Click, Ctrl+A) |
| File validation | None | **Automatic mismatch detection** with mode-switch offer |
| Recent history | Last 10 folders | **Exact file selections** per entry |
| INI sub-tabs | Single table | **Antriebsparameter + Prototypen** split view |
| Application icon | External file required | **Embedded in script** — zero external dependencies |
| Help system | None | **Built-in EN/DE bilingual help** dialog |
| Version tracking | None | **Status bar version display** (bottom-right) |
| DPI support | Basic | **Per-monitor DPI v2** + Qt high-DPI scaling |

### Highlight: 3-State Smart Mode Button

The mode button in the toolbar adapts its appearance and behaviour to the current context:

```
  State A (no mode)     →  Gray button     →  "Open as DCO tab" / "Open as SC.INI tab"
  State B (mode, no data)  →  Coloured button  →  Switch this tab or open new tab
  State C (data loaded)  →  Coloured + locked →  "New DCO tab" / "New SC.INI tab"
```

### Highlight: File Validation Popup

When the user selects files that don't match the active mode (e.g., `.dco` files in INI mode), a validation popup appears offering to open them in the correct mode — automatically creating a new tab.

---

## Architecture Overview

```
┌───────────────────────────────────────────────────────────────────────┐
│                        Config Viewer App  v3.0                        │
│                                                                       │
│  ┌──────────────────┐  ┌──────────────────────────────────────────┐  │
│  │ Smart Mode Button│  │          Tab Manager (QTabWidget)         │  │
│  │  (3-state FSM)   │─▶│  [⚙ Tab 1]  [⚙ Tab 2]  [⚙ Tab 3]  ×  │  │
│  └──────────────────┘  └──────────────┬───────────────────────────┘  │
│                                       │                               │
│                            ┌──────────▼──────────┐                   │
│                            │    TabSession        │                   │
│                            │  mode=None│dco│ini   │                   │
│                            │  filter_checks{}     │                   │
│                            └──────────┬────────────┘                  │
│                                       │                               │
│              ┌────────────────────────┼────────────────────┐         │
│              │                        │                    │         │
│    ┌─────────▼────────┐   ┌──────────▼──────────┐  ┌─────▼──────┐  │
│    │  Placeholder      │   │   DCO TablePane     │  │ INI Mode   │  │
│    │  (mode buttons)   │   │   (single pane,     │  │ QTabWidget │  │
│    │  [DCO] [SC.INI]  │   │    112 columns)     │  │ ┌────────┐ │  │
│    └──────────────────┘   └─────────────────────┘  │ │Antriebs│ │  │
│                                                     │ │TablePane│ │  │
│                            ┌─────────────────────┐  │ ├────────┤ │  │
│                            │   Parser Factory     │  │ │Prototyp│ │  │
│                            │  ┌───────────────┐  │  │ │TablePane│ │  │
│                            │  │ DCO Parser    │  │  │ └────────┘ │  │
│                            │  │ (400-byte bin │  │  └────────────┘  │
│                            │  │  struct, 112  │  │                   │
│                            │  │  columns)     │  │                   │
│                            │  └───────────────┘  │                   │
│                            │  ┌───────────────┐  │                   │
│                            │  │ INI Parser    │  │                   │
│                            │  │ (text, 19+25  │  │                   │
│                            │  │  columns)     │  │                   │
│                            │  └───────────────┘  │                   │
│                            └──────────┬──────────┘                   │
│                                       │                               │
│                            ┌──────────▼──────────┐                   │
│                            │   Shared Renderer    │                   │
│                            │  • Category filter   │                   │
│                            │  • Context-menu sort │                   │
│                            │  • Drag-reorder      │                   │
│                            │  • Vertical headers  │                   │
│                            │  • Excel export      │                   │
│                            └─────────────────────┘                   │
└───────────────────────────────────────────────────────────────────────┘
```

---

## Feature Highlights

### Session & Tab Management
- Open multiple project sites in parallel tabs within one window
- Each tab starts with a **mode=None placeholder** — choose DCO or SC.INI per tab
- Tabs display a **colour-coded indicator**: blue for DCO, amber for SC.INI
- Recent file history stores **exact file selections** (not just folders) — one-click reopen
- Smart mode button locks after data is loaded to prevent accidental mode switches

### DCO Mode (Binary Drive Configuration Objects)
- Parses 400-byte binary drive configuration files using `struct`
- **112 parameter columns** across 8 filter categories
- 8 scaling functions for engineering-unit display (÷8192, ÷32767, ×100÷1024, etc.)
- **32 bit-flag columns** with vertical rotated headers for compact display
- Two 16-bit bitmasks (configstatdb + Ext.ConfigstDB) fully decoded
- Right-click context menu sorting (A→Z, Z→A, Clear Sort)
- Drag-and-drop column reordering

### SC.INI Mode (Drive Initialisation Parameter Files)
- Parses text-based drive parameter files with two sections
- **Antriebsparameter** (19 columns): drive-level flags, encoder settings, safety
- **Prototypen** (25 columns): speed, acceleration, mode bit-flags
- Split into two sub-tabs for clean separation
- Same filter, sort, and export UX as DCO mode

### File Handling
- **Multi-file selection**: Ctrl+Click for individual files, Ctrl+A for all
- **File validation**: wrong file type triggers a popup offering correct mode (new tab)
- **Recent selections**: stores exact files chosen, not just folder path
- **Mode-locked tabs**: once data is loaded, mode cannot be accidentally changed

### Excel Export
- **Category-coloured headers**: each filter group gets a distinct background colour
- Two header rows: category band (row 1) + column names (row 2)
- Auto-fit column widths, thin borders, centered data
- Freeze panes at A3, auto-filter on data range
- DCO: single "DCO Data" sheet; INI: two sheets (Antriebsparameter + Prototypen)

### Built-In Help
- Bilingual EN/DE side-by-side help dialog
- Accessible via the "?" button in the toolbar

---

## Tech Stack

| Component | Technology |
|---|---|
| GUI framework | PyQt5 (QMainWindow, QTabWidget, per-tab sessions) |
| Binary parsing | Python `struct`, little-endian, 400-byte records |
| Text parsing | Line tokenisation with hex/decimal value handling |
| Excel export | `openpyxl` with styled formatting |
| Session persistence | `json` (exact file selections, max 10 entries) |
| Icon | Base64-embedded JPEG — no external file at runtime |
| DPI awareness | Windows per-monitor DPI v2 (ctypes shcore) + Qt scaling |
| Build | PyInstaller `--onefile --windowed` |
| Python | 3.9+ |

---

## Project Workflow Diagram

```
  Engineer opens Config Viewer
          │
          ▼
  Tab starts in mode=None (placeholder)
          │
          ▼
  Choose Mode ◄────── Smart Mode Button (dropdown)
   │           │
   DCO         SC.INI
   │           │
   ▼           ▼
  Select files (multi-select with Ctrl)
          │
          ├── Validate file extensions against mode
          │     └── Mismatch? → Offer to open in correct mode (new tab)
          │
          ▼
  Files parsed → Table populated
          │
          ├─── Toggle filter categories (checkboxes)
          │
          ├─── Right-click sort (A→Z / Z→A / Clear)
          │
          ├─── Drag-reorder columns
          │
          ├─── Open additional tab (same session)
          │       └── Independent mode / files / filter per tab
          │
          ├─── Export as Excel (colour-coded categories)
          │
          └─── Click "?" for EN/DE help
```

---

## UI Concept Mockups

Interactive HTML mockups demonstrating the 3-state mode button, file validation popup, and placeholder tab design are included in [docs/ui-concepts.html](./docs/ui-concepts.html). Open in any browser — no server required.

---

## Screenshots

### Start Screen — Mode Selection Placeholder

```
┌──────────────────────────────────────────────────────────────────────────┐
│ [⚙ Mode… ▾]  [Select Folder]  [▾ Recent]   Choose a mode to begin      │
├──────────────────────────────────────────────────────────────────────────┤
│ ⚙ New Tab 1  ×                                                          │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│                          📄                                              │
│                   Choose a mode to start                                 │
│         Select DCO to load binary .dco files,                            │
│         or SC.INI to load drive configuration files.                     │
│                                                                          │
│              [ ● DCO Mode ]    [ ● SC.INI Mode ]                        │
│                                                                          │
├──────────────────────────────────────────────────────────────────────────┤
│ Ready — choose a mode (DCO / INI)                            v1.0.0     │
└──────────────────────────────────────────────────────────────────────────┘
```

### Multi-Site Session with Dual-Mode Tabs

```
┌──────────────────────────────────────────────────────────────────────────┐
│ [⚙ DCO Mode ▾]  [Select Folder]  [▾ Recent]   📂 //network/site-A     │
├──────────────────────────────────────────────────────────────────────────┤
│ ⚙ Site-A DCO  × │ ⚙ Site-B INI  × │ ⚙ Site-C DCO  ×                   │
├──────────────────────────────────────────────────────────────────────────┤
│ Filter: ☑ Position  ☑ Regelung  ☑ Last  ☑ Sicherheiten  ☑ Locking …   │
├──────────────────────────────────────────────────────────────────────────┤
│  Name   │ Code │ Drive │ Config │ [bit-flag columns, rotated 90°]  …   │
│  1-MZ.dco  12345  MZ-1    0x3F    x │   │ x │ x │ x │   │ …          │
│  2-MZ.dco  12345  MZ-2    0x1F      │ x │ x │   │ x │   │ …          │
├──────────────────────────────────────────────────────────────────────────┤
│ Loaded 12 file(s); 112 columns                               v1.0.0    │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| **3-state mode button** | Prevents accidental mode switches after data is loaded; provides context-sensitive options at each stage |
| **Mode=None placeholder** | Neutral start state lets each tab choose its own format; no assumptions about what the user needs |
| **Individual file selection** | Engineers often need specific files from a folder, not all of them; multi-select with Ctrl is standard UX |
| **File validation popup** | Wrong file types are caught immediately with a helpful recovery path (open in correct mode) |
| **Exact recent tracking** | Stores folder + file list, not just folder — reopening restores the precise selection |
| **Embedded icon** | Standalone .exe needs zero external files; icon baked as base64 JPEG decoded at runtime |
| **Per-tab state isolation** | Engineers working across 3+ project sites need independent scroll/filter positions |
| **Parser Factory pattern** | New file formats can be added without touching the GUI layer; each parser returns a uniform dict list |
| **INI sub-tabs** | Antriebsparameter and Prototypen are logically separate data sets; sub-tabs prevent mixing |
| **Version in status bar** | Single constant (`APP_VERSION`) at top of file; visible in UI for support/tracking |

---

## Product KPIs Achieved

| KPI | Baseline | After v3.0 |
|---|---|---|
| Manual config review time | ~60 min per site | ~18 min (−70%) |
| Sites supported per session | 1 (separate tool runs) | 5+ concurrent tabs |
| File formats supported | 1 (DCO) | 2 (DCO + SC.INI with sub-sections) |
| Export formats | Manual Excel copy-paste | One-click colour-coded export |
| Onboarding time (new engineer) | ~30 min | ~5 min (built-in help + placeholder guidance) |
| External dependencies for .exe | ICO file + runtime | Zero — single .exe |

---

## Changelog

### v3.0 (Current)
- **3-state smart mode button** — context-aware dropdown (placeholder → active → locked)
- **Mode=None placeholder tabs** — each tab starts neutral with DCO/SC.INI buttons
- **Individual file multi-select** — Ctrl+Click / Ctrl+A instead of folder-only
- **File validation popup** — wrong file type detection with mode-switch offer
- **Exact recent tracking** — stores folder + specific files, not just folder path
- **SC.INI sub-tabs** — Antriebsparameter and Prototypen in separate panes
- **Embedded application icon** — base64 JPEG baked into script, no external file needed
- **Built-in EN/DE help dialog** — bilingual side-by-side reference
- **Version display** — `APP_VERSION` constant shown in status bar (bottom-right)
- **DPI improvements** — per-monitor DPI v2 + Qt high-DPI pixel maps
- **Code comments** — comprehensive section-by-section documentation

### v2.0
- Added **INI Mode** with dedicated parser backend
- Dual-mode toolbar dropdown (DCO / INI) with live tab switching
- Amber tab colour indicator for INI sessions
- Mode-aware recent-folder history (separate lists per mode)
- Shared filter engine adapts dynamically to active format mode
- Mode-aware Excel export

### v1.0
- Binary `.dco` file parser with 90+ parameter columns
- 9-category toggle filter system
- Column freeze and drag-reorder
- Vertical rotated headers for parameter name display
- Category-colour-coded Excel export

---

## Testing & Verification

### Automated Verification

Core parsing logic is verified against a reference tool (industry-standard parameter viewer) using a structured comparison workflow:

```
tests/
├── test_dco_parser.py      # Schema validation, column extraction, scaling functions
├── test_ini_parser.py      # Section parsing, hex/decimal handling, bit-flag extraction
├── test_filter_engine.py   # Category toggle logic, per-mode category mapping
├── test_excel_export.py    # Column mapping, colour codes, header formatting
└── test_validation.py      # File extension checking, mode mismatch detection
```

### DCO Verification Results

| Metric | Result |
|---|---|
| Total parameters tested | 76 |
| Matches | 76 |
| Mismatches | 0 |
| Match rate | 100% |
| Scaling functions verified | All 8 against specification |

### Manual Regression Checklist (per release)

- Load DCO and INI files from known-good sample sets → verify column counts
- Apply each filter category independently → verify column visibility
- Open 3+ tabs simultaneously → verify independent state per tab
- Select wrong file type → verify validation popup and mode-switch offer
- Trigger Excel export → verify colour coding and header formatting
- Restart app → verify recent selections restored correctly
- Check version label visible in status bar (bottom-right)

---

## Market & Industry Relevance

Config Viewer addresses a gap across industrial automation environments: drive configuration files are binary or text blobs with no standard viewer, and engineers manually compare parameters in Excel with no structured tooling.

**Why this matters in 2026:**
- OT/IT convergence drives demand for internal tooling that bridges field engineers and software teams
- B2B SaaS design thinking (multi-site session model, persistent state, one-click export) is expected from product-led engineering teams
- Python + PyQt5 GUI skills are in demand for IIoT dashboard and Edge device configuration platforms
- Zero-dependency deployment (single .exe, embedded assets) reduces IT overhead on locked-down workstations

**Transferable patterns:**
- 3-State Smart Button → applicable to any mode-switching UI with progressive state locking
- Parser Factory → applicable to multi-format device config scenarios (AUTOSAR, ROS param files, PLCopen XML)
- Per-tab state isolation → relevant to multi-tenant engineering dashboards or fleet management UIs
- File validation with recovery → applicable to any tool handling multiple file formats
- Embedded asset pattern → applicable to any single-file deployment where external dependencies are a burden

**Product design artefacts and UX flows for this tool:** [Figma Community Portfolio](https://www.figma.com/community/@ichumang)

---

## License

MIT — see [LICENSE](./LICENSE)

> **Note:** This repository contains the architectural documentation, workflow diagrams, interface design, and GUI shell of Config Viewer. No proprietary parameter definitions, hardware-specific data structures, binary format specifications, or customer configuration data are included.

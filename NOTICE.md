# Notice — Public / Private Code Policy

This repository uses a **public README + private code** model for portfolio
demonstration purposes.

## What is public

| Path | Content |
|------|---------|
| `README.md` | Project overview, features, architecture, category descriptions |
| `docs/user-guide.md` | Usage instructions and keyboard shortcuts |
| `docs/architecture.md` | High-level design and data-flow documentation |
| `main.py` | PyQt5 application window — GUI layout, filter panel, export, printing |
| `requirements.txt` | Python dependencies |
| `LICENSE` | Proprietary license terms |

## What is private

| Path | Content |
|------|---------|
| `lib/dco_parser.py` | Binary `.dco` parser — struct layout, field offsets, scaling factors |
| `lib/categories.py` | Column-to-category mapping for the filter panel |

Private code is not distributed.  The binary format specification, struct
definitions, field scaling constants, and category mappings are proprietary
to the drive system vendor.

## Why this separation

The `.dco` binary format is a proprietary configuration dump.  Publishing
the full struct layout and scaling tables would expose confidential
information about the drive system's internal data model.

The public `main.py` demonstrates:

- PyQt5 desktop application design
- Multi-file comparison grid with category-based filtering
- Export pipeline (PDF, Excel, CSV, Print)
- Clean separation between GUI and parser logic

## Author

Umang Panchal — github.com/ichumang

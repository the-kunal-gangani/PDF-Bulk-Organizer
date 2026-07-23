# PDF Bulk Organizer

A desktop tool that reads, classifies, and automatically organizes a folder full of unsorted PDFs — invoices, resumes, certificates, offer letters, and more — with OCR support, duplicate detection, undo, and a fully customizable classification system.

Built from a simple CLI script into a full desktop app with a modern GUI, live progress, and safety features like stop/undo.

---

## Problem

Folders full of PDFs — invoices, resumes, certificates, scanned documents — pile up with generic names like `scan001.pdf` or `document(3).pdf`, making them impossible to search or manage. This tool reads the actual content of each file to figure out what it is, then organizes it automatically — including scanned PDFs with no selectable text, and PDFs that are duplicates of each other.

---

## Features

### Core organizing
- Extracts text from PDFs using `pdfplumber`
- Classifies documents into categories (Invoice, Resume, Certificate, Contract, Report, Offer Letter, or Unsorted) using a weighted keyword system
- Extracts dates and sender/company names directly from document content
- Auto-renames files with meaningful names, e.g. `Invoice_2026-06-15_AmazonPay.pdf`
- Moves files into category subfolders automatically
- `--dry-run` mode to preview every rename and move before anything actually happens
- Logs every real move to a timestamped log file for traceability

### OCR support
- Automatically detects scanned/image-only PDFs with no extractable text
- Falls back to Tesseract OCR (`pytesseract`) to read them anyway
- OCR'd files are tagged `[OCR]` in the log so you know which ones needed it

### Duplicate detection
- Hashes normalized document content (not just raw file bytes) to catch duplicates
- Catches both exact copies *and* re-saved files with identical text but different file bytes/metadata
- Duplicates are routed to their own `Duplicates/` folder, named after the original they match

### Undo & Stop safety
- **Undo Last Run** — reverses the most recent real Organize run, restoring every file to its original name and location
- **Stop button** — appears only while a run is active; stops cleanly between files (never mid-file)
- After stopping, you're asked whether to undo the files already sorted, or leave them sorted and pick up the rest later

### Fully customizable categories
- All categories and keywords live in an editable `config.yaml` — no code changes needed
- Each category has **strong** keywords (near-certain identifiers), **weak** keywords (supporting signals), and **exclude** keywords (veto signals that stop false positives, e.g. academic syllabi false-matching "Resume")
- **In-app Category Editor** — add, rename, or delete categories and their keywords entirely through the GUI
- Falls back gracefully to built-in defaults if the config file is missing or has invalid syntax — never crashes

### Modern desktop GUI
- Dark-themed interface built with `customtkinter`
- **Drag-and-drop** a folder straight onto the window
- **Recent folders** dropdown remembers your last few used folders
- **Animated liquid-fill progress bar** with a live percentage and real per-file progress tracking ("Processing file 6 of 42")
- **Color-coded activity log** — each category gets its own color
- **Category filter chips** — checkboxes above the log let you show/hide specific categories on the fly
- **Summary chips** after each run showing counts per category (e.g. `Invoice: 5` `Resume: 3` `Unsorted: 2`)

---

## Project Structure

```
pdf_organizer/
├── organizer.py         # Core logic — CLI entry point, file moving/renaming, undo, stop handling
├── classifier.py        # Keyword-based classification engine + config.yaml loading/saving
├── extractor.py         # PDF text extraction, OCR fallback, date/sender parsing, content hashing
├── gui.py                # Desktop GUI (customtkinter) — all interactive features live here
├── config.yaml           # Editable categories, keywords, and scoring weights
└── requirements.txt
```

**How the pieces connect:**
- `organizer.py` is the core engine — it can be run standalone via CLI, or imported by `gui.py`
- `extractor.py` is self-contained — pure text/data extraction with no dependency on the other modules, which is what made adding OCR and duplicate hashing possible without touching classification logic
- `classifier.py` owns all category/keyword logic and the `config.yaml` read/write path — both the CLI and the in-app Category Editor go through the same functions, so there's one source of truth
- `gui.py` wraps everything in a threaded, non-blocking interface — long-running operations happen on a background thread so the UI stays responsive, with progress reported back via callbacks

---

## Installation

```bash
pip install -r requirements.txt
```

Two additional system-level installs are required for optional features:

- **OCR:** install the [Tesseract OCR engine](https://github.com/UB-Mannheim/tesseract/wiki) (Windows installer). `pytesseract` is just a Python wrapper around it.
- **Drag-and-drop:** included via `tkinterdnd2` in requirements — if it's not installed, the app still runs fine, just without drag-and-drop.

---

## Usage

### GUI (recommended)
```bash
python gui.py
```
Drag a folder onto the window (or use Browse/Recent), hit **Preview (Dry Run)** to check the plan, then **Organize Now** to actually sort the files.

### CLI
```bash
# Preview what will happen, without touching any files
python organizer.py /path/to/folder --dry-run

# Actually organize the files
python organizer.py /path/to/folder

# Undo the most recent real organize run
python organizer.py /path/to/folder --undo
```

---

## Customizing Categories

Open `config.yaml` directly, or use the **⚙ Edit Categories** button in the GUI for a visual editor. Example of adding a new category:

```yaml
  Bank Statement:
    strong:
      - "account statement"
      - "closing balance"
    weak:
      - "transaction"
      - "debit"
      - "credit"
    exclude: []
```

- **strong** keywords are worth more scoring weight — near-certain identifiers
- **weak** keywords are supporting signals — worth less on their own
- **exclude** keywords veto the category entirely if present, preventing false positives (e.g. academic documents matching "Certificate" just because they mention certification requirements)

---

## Example

```
[DRY RUN] scan001.pdf [OCR]           ->  Invoice/Invoice_15062026_Amazon_Pay.pdf
[DRY RUN] doc2.pdf                    ->  Resume/Resume_Kunal_Gangani.pdf
[DRY RUN] doc2_copy.pdf [DUPLICATE]   ->  Duplicates/Duplicate_of_Resume_Kunal_Gangani.pdf
[DRY RUN] notes.pdf                   ->  Unsorted/Unsorted_Random_unrelated_notes_file_wi.pdf

Summary — Invoice: 1, Resume: 1, Duplicates: 1, Unsorted: 1
```

---

## Roadmap

- Package as a standalone `.exe` (no Python install required to run)
- Multi-level undo history (currently reverses only the most recent run)
- Dark/light theme toggle
- Batch mode for organizing multiple subfolders in one pass

---

## Tech Stack

Python · pdfplumber · pytesseract (Tesseract OCR) · PyYAML · customtkinter · tkinterdnd2 · argparse
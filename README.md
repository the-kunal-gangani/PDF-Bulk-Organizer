# PDF Bulk Organizer

A command-line tool that scans a folder full of unsorted PDFs, reads their content,
and automatically renames and sorts them into categorized folders — no manual sorting needed.

## Problem

Folders full of PDFs (invoices, resumes, certificates, contracts) pile up with generic
names like `scan001.pdf` or `document(3).pdf`, making them impossible to search or manage.
This tool reads the actual content of each file to figure out what it is, then organizes
it automatically.

## Features

- Extracts text from PDFs using `pdfplumber`
- Classifies documents into categories (Invoice, Resume, Certificate, Contract, Report,
  or Unsorted) using keyword-based detection
- Extracts dates and sender/company names directly from document content
- Auto-renames files with meaningful names, e.g. `Invoice_2026-06-15_AmazonPay.pdf`
- Moves files into category subfolders automatically
- `--dry-run` mode to preview every rename and move before anything actually happens
- Logs every real move to a log file for traceability

## Project Structure

pdf_organizer/
├── organizer.py       # CLI entry point — argument parsing, renaming, and file moving
├── classifier.py      # Keyword-based document category detection
├── extractor.py       # PDF text extraction + date/sender parsing
└── requirements.txt

## Usage

```bash
pip install -r requirements.txt

# Preview what will happen, without touching any files
python3 organizer.py /path/to/folder --dry-run

# Actually organize the files
python3 organizer.py /path/to/folder
```

## Example
[DRY RUN] scan001.pdf -> Invoice/Invoice_15062026_Amazon_Pay.pdf
[DRY RUN] doc2.pdf -> Resume/Resume_Kunal_Gangani.pdf
[DRY RUN] notes.pdf -> Unsorted/Unsorted_Random_unrelated_notes_file_wi.pdf

## Roadmap

- OCR support for scanned/image-based PDFs (`pytesseract`)
- Simple GUI (`tkinter`) for drag-and-drop use
- Config file for custom categories and keywords

## Tech Stack

Python, pdfplumber, regex, argparse
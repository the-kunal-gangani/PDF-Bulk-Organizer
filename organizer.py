import argparse
import shutil
from pathlib import Path

from extractor import extract_text, extract_date, extract_sender, clean_for_filename
from classifier import classify


def build_new_name(category, date, sender, original_stem):
    parts = [category]
    if date:
        parts.append(clean_for_filename(date))
    if sender:
        parts.append(clean_for_filename(sender))
    if not date and not sender:
        parts.append(clean_for_filename(original_stem))
    return "_".join(parts) + ".pdf"


def unique_path(target_path):
    if not target_path.exists():
        return target_path
    counter = 1
    stem, suffix, parent = target_path.stem, target_path.suffix, target_path.parent
    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def process_folder(source_dir, dry_run=True, log_path=None, on_action=None):
    source = Path(source_dir)
    pdf_files = sorted(source.glob("*.pdf"))

    if not pdf_files:
        message = f"No PDF files found in {source}"
        if on_action:
            on_action(message)
        else:
            print(message)
        return []

    log_lines = []

    for pdf_path in pdf_files:
        text, used_ocr = extract_text(pdf_path)
        category = classify(text)
        date = extract_date(text)
        sender = extract_sender(text)

        new_name = build_new_name(category, date, sender, pdf_path.stem)
        dest_dir = source / category
        dest_path = unique_path(dest_dir / new_name)

        ocr_tag = " [OCR]" if used_ocr else ""
        action = f"{pdf_path.name}{ocr_tag}  ->  {category}/{dest_path.name}"
        line = ("[DRY RUN] " if dry_run else "[MOVED]   ") + action
        if on_action:
            on_action(line)
        else:
            print(line)
        log_lines.append(action)

        if not dry_run:
            dest_dir.mkdir(exist_ok=True)
            shutil.move(str(pdf_path), str(dest_path))

    if not dry_run and log_path:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write("\n".join(log_lines) + "\n")

    return log_lines


def main():
    parser = argparse.ArgumentParser(description="Bulk-organize PDFs by content.")
    parser.add_argument("folder", help="Path to the folder containing PDFs")
    parser.add_argument("--dry-run", action="store_true", help="Preview actions without moving files")
    parser.add_argument("--log", default="organizer_log.txt", help="Log file name for recorded moves")
    args = parser.parse_args()

    process_folder(args.folder, dry_run=args.dry_run, log_path=args.log)


if __name__ == "__main__":
    main()
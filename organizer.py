import argparse
import shutil
import datetime
from pathlib import Path

from extractor import extract_text, extract_date, extract_sender, clean_for_filename, compute_content_hash
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


def process_folder(source_dir, dry_run=True, log_path=None, on_action=None, on_progress=None):
    source = Path(source_dir)
    pdf_files = sorted(source.glob("*.pdf"))

    if not pdf_files:
        message = f"No PDF files found in {source}"
        if on_action:
            on_action(message)
        else:
            print(message)
        return [], {}

    log_lines = []
    move_records = []
    seen_hashes = {}
    category_counts = {}
    total_files = len(pdf_files)

    for index, pdf_path in enumerate(pdf_files, start=1):
        text, used_ocr = extract_text(pdf_path)
        content_hash = compute_content_hash(text, pdf_path)

        is_duplicate = content_hash is not None and content_hash in seen_hashes

        if is_duplicate:
            original_ref = seen_hashes[content_hash]
            category = "Duplicates"
            original_stem = Path(original_ref).stem
            new_name = unique_path(
                source / category / f"Duplicate_of_{clean_for_filename(original_stem)}{pdf_path.suffix}"
            ).name
            dup_tag = " [DUPLICATE]"
        else:
            category = classify(text)
            date = extract_date(text)
            sender = extract_sender(text)
            new_name = build_new_name(category, date, sender, pdf_path.stem)
            dup_tag = ""

        dest_dir = source / category
        dest_path = unique_path(dest_dir / new_name)

        if not is_duplicate and content_hash is not None:
            seen_hashes[content_hash] = dest_path.name

        category_counts[category] = category_counts.get(category, 0) + 1

        ocr_tag = " [OCR]" if used_ocr else ""
        action = f"{pdf_path.name}{ocr_tag}{dup_tag}  ->  {category}/{dest_path.name}"
        line = ("[DRY RUN] " if dry_run else "[MOVED]   ") + action
        if on_action:
            on_action(line)
        else:
            print(line)
        log_lines.append(action)

        if not dry_run:
            dest_dir.mkdir(exist_ok=True)
            original_name = pdf_path.name
            shutil.move(str(pdf_path), str(dest_path))
            move_records.append(f"{original_name}::{category}/{dest_path.name}")

        if on_progress:
            on_progress(index, total_files)

    if not dry_run and log_path and move_records:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"### RUN {timestamp} ###\n")
            f.write("\n".join(move_records) + "\n")

    return log_lines, category_counts


def undo_last_run(source_dir, log_path):
    source = Path(source_dir)
    log_file = Path(log_path)

    if not log_file.exists():
        return [], [], "No log file found — nothing to undo."

    lines = log_file.read_text(encoding="utf-8").splitlines()
    run_indices = [i for i, line in enumerate(lines) if line.startswith("### RUN")]

    if not run_indices:
        return [], [], "No recorded runs found in the log."

    last_start = run_indices[-1]
    batch = [line for line in lines[last_start + 1:] if line.strip()]

    if not batch:
        return [], [], "The last run had no file moves to undo."

    restored = []
    skipped = []

    for record in batch:
        if "::" not in record:
            continue
        original_name, rel_dest = record.split("::", 1)
        dest_path = source / rel_dest
        original_path = source / original_name

        if not dest_path.exists():
            skipped.append(f"Missing (already moved/deleted): {rel_dest}")
            continue
        if original_path.exists():
            skipped.append(f"Skipped, name already taken: {original_name}")
            continue

        shutil.move(str(dest_path), str(original_path))
        restored.append(f"{rel_dest}  ->  {original_name}")

    for record in batch:
        if "::" not in record:
            continue
        _, rel_dest = record.split("::", 1)
        dest_dir = source / Path(rel_dest).parent
        try:
            if dest_dir.exists() and not any(dest_dir.iterdir()):
                dest_dir.rmdir()
        except OSError:
            pass

    remaining_lines = lines[:last_start]
    log_file.write_text(
        "\n".join(remaining_lines) + ("\n" if remaining_lines else ""), encoding="utf-8"
    )

    return restored, skipped, None


def main():
    parser = argparse.ArgumentParser(description="Bulk-organize PDFs by content.")
    parser.add_argument("folder", help="Path to the folder containing PDFs")
    parser.add_argument("--dry-run", action="store_true", help="Preview actions without moving files")
    parser.add_argument("--log", default="organizer_log.txt", help="Log file name for recorded moves")
    parser.add_argument("--undo", action="store_true", help="Undo the last real organize run")
    args = parser.parse_args()

    if args.undo:
        log_path = str(Path(args.folder) / args.log)
        restored, skipped, error = undo_last_run(args.folder, log_path)
        if error:
            print(error)
            return
        for line in restored:
            print(f"[RESTORED] {line}")
        for line in skipped:
            print(f"[SKIPPED]  {line}")
        print(f"Undo complete — {len(restored)} file(s) restored, {len(skipped)} skipped.")
        return

    log_lines, category_counts = process_folder(
        args.folder, dry_run=args.dry_run, log_path=str(Path(args.folder) / args.log)
    )
    if category_counts:
        summary = ", ".join(f"{cat}: {count}" for cat, count in category_counts.items())
        print(f"\nSummary — {summary}")


if __name__ == "__main__":
    main()
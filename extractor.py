import re
import pdfplumber

DATE_PATTERNS = [
    r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",
    r"\b(\d{4}-\d{1,2}-\d{1,2})\b",
    r"\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})\b",
]


def extract_text(pdf_path):
    text_chunks = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_chunks.append(page_text)
    except Exception:
        return ""
    return "\n".join(text_chunks)


def extract_date(text):
    for pattern in DATE_PATTERNS:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


def extract_sender(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines[:15]:
        match = re.search(r"(?:From|Sender|Company|Vendor)\s*[:\-]\s*(.+)", line, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    if lines:
        return lines[0][:40]
    return None


def clean_for_filename(text):
    if not text:
        return "Unknown"
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"\s+", "_", text.strip())
    return text[:30] if text else "Unknown"
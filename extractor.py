import re
import hashlib
import pdfplumber

import os

try:
    import pytesseract
    _default_tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(_default_tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = _default_tesseract_path
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

DATE_PATTERNS = [
    r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",
    r"\b(\d{4}-\d{1,2}-\d{1,2})\b",
    r"\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})\b",
]

OCR_MIN_CHARS = 20
OCR_RESOLUTION = 200


def extract_text(pdf_path, ocr_fallback=True):
    text_chunks = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_chunks.append(page_text)
    except Exception:
        return "", False

    text = "\n".join(text_chunks)

    if len(text.strip()) >= OCR_MIN_CHARS or not ocr_fallback or not OCR_AVAILABLE:
        return text, False

    ocr_text = _extract_text_via_ocr(pdf_path)
    if len(ocr_text.strip()) > len(text.strip()):
        return ocr_text, True
    return text, False


def _extract_text_via_ocr(pdf_path):
    ocr_chunks = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                try:
                    image = page.to_image(resolution=OCR_RESOLUTION).original
                    page_text = pytesseract.image_to_string(image)
                    if page_text:
                        ocr_chunks.append(page_text)
                except Exception:
                    continue
    except Exception:
        return ""
    return "\n".join(ocr_chunks)


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


def compute_content_hash(text, pdf_path):
    if text and len(text.strip()) >= 20:
        normalized = re.sub(r"\s+", " ", text.strip().lower())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    try:
        with open(pdf_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception:
        return None
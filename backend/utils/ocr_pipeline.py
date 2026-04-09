"""
backend/utils/ocr_pipeline.py
Extracts plain text from PDF or TXT past-paper files.

PDF strategy (in priority order):
  1. pdfplumber  — fast, exact, works for digital PDFs (recommended)
  2. pytesseract — fallback for scanned / image-only PDFs
     (requires Tesseract installed: sudo apt-get install tesseract-ocr)

TXT files are read directly.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


# ── PDF text extraction ───────────────────────────────────────────────────────

def _extract_with_pdfplumber(pdf_path: Path) -> str:
    """Extract text using pdfplumber (best for digital PDFs)."""
    import pdfplumber

    pages = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text:
                pages.append(text)
            else:
                logger.debug("pdfplumber: no text on page %d of %s", i + 1, pdf_path.name)

    return "\n\n".join(pages)


def _extract_with_tesseract(pdf_path: Path) -> str:
    """
    Fallback: convert each PDF page to image and run Tesseract OCR.
    Requires: pdf2image (pip) + poppler-utils (apt) + tesseract-ocr (apt).
    """
    try:
        from pdf2image import convert_from_path
        import pytesseract
        from PIL import Image, ImageEnhance, ImageFilter
    except ImportError as e:
        raise RuntimeError(
            f"Tesseract fallback requires pdf2image and pytesseract: {e}"
        )

    images = convert_from_path(str(pdf_path), dpi=200)
    pages  = []

    for img in images:
        # Preprocess for better OCR
        img = img.convert("L")
        img = img.filter(ImageFilter.SHARPEN)
        img = ImageEnhance.Contrast(img).enhance(2.0)

        text = pytesseract.image_to_string(img, config="--oem 3 --psm 6")
        if text.strip():
            pages.append(text)

    return "\n\n".join(pages)


def extract_text_from_pdf(pdf_path: Path) -> str:
    """
    Extract text from a PDF file.
    Tries pdfplumber first; falls back to Tesseract OCR if result is empty.
    """
    # Step 1: try pdfplumber (fast, accurate for digital PDFs)
    try:
        text = _extract_with_pdfplumber(pdf_path)
        if text.strip():
            logger.info("pdfplumber: extracted %d chars from %s", len(text), pdf_path.name)
            return text
        logger.info("pdfplumber returned empty — falling back to Tesseract.")
    except Exception as exc:
        logger.warning("pdfplumber failed for %s: %s — trying Tesseract.", pdf_path.name, exc)

    # Step 2: Tesseract OCR (slower, for scanned PDFs)
    try:
        text = _extract_with_tesseract(pdf_path)
        logger.info("Tesseract: extracted %d chars from %s", len(text), pdf_path.name)
        return text
    except Exception as exc:
        raise ValueError(
            f"Could not extract text from {pdf_path.name}. "
            f"Ensure Tesseract and poppler-utils are installed. Error: {exc}"
        )


def extract_text_from_txt(txt_path: Path) -> str:
    """Read a plain-text past-paper file."""
    with open(str(txt_path), "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def extract_text_from_file(file_path: Path) -> str:
    """Dispatch to the correct extractor based on file extension."""
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return extract_text_from_pdf(file_path)
    elif suffix == ".txt":
        return extract_text_from_txt(file_path)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")

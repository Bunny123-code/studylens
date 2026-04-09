"""
backend/utils/text_cleaner.py
Cleans raw OCR or PDF-extracted text before analysis.

Operations:
  - Remove excessive whitespace and blank lines
  - Strip common header/footer noise (page numbers, board stamps)
  - Normalise unicode characters
  - Remove non-printable control characters
"""

import re
import unicodedata
import logging

logger = logging.getLogger(__name__)

# Common header/footer patterns found in Pakistani board papers
_NOISE_PATTERNS = [
    r"page\s+\d+\s+of\s+\d+",           # "Page 1 of 8"
    r"^\s*\d+\s*$",                       # lone page numbers
    r"federal board of intermediate.*",   # board headers
    r"sindh board of intermediate.*",
    r"karachi board of intermediate.*",
    r"board of intermediate.*education.*",
    r"bise\s+\w+",                        # BISE abbreviation
    r"roll\s+no[:\.]?\s*_+",             # Roll No: ______
    r"do not write.*margin",
    r"time allowed.*hours?",              # Time allowed: 3 hours
    r"maximum marks.*\d+",
    r"objective\s+type",
    r"subjective\s+type",
    r"section\s+[a-z]\s*$",
    r"section-[a-z]\s*$",
    r"answer any\s+\w+\s+(?:of the following|questions)",
    r"all questions carry equal marks",
    r"use of calculator.*not.*allowed",
]

_NOISE_RE = re.compile(
    "|".join(_NOISE_PATTERNS),
    flags=re.IGNORECASE | re.MULTILINE,
)


def remove_noise(text: str) -> str:
    """Remove board-paper headers, footers, and instructions."""
    return _NOISE_RE.sub("", text)


def normalise_unicode(text: str) -> str:
    """Normalise unicode to NFC form and remove non-printable characters."""
    text = unicodedata.normalize("NFC", text)
    # Keep printable ASCII + whitespace; drop control chars
    text = "".join(ch for ch in text if unicodedata.category(ch)[0] != "C" or ch in "\n\t ")
    return text


def collapse_whitespace(text: str) -> str:
    """Collapse multiple blank lines to a single blank line."""
    # Replace 3+ consecutive newlines with 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Collapse spaces / tabs on a single line
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def clean_text(raw: str) -> str:
    """
    Full cleaning pipeline.

    Args:
        raw: Raw text from OCR or PDF extractor.

    Returns:
        Cleaned, normalised text ready for analysis.
    """
    text = normalise_unicode(raw)
    text = remove_noise(text)
    text = collapse_whitespace(text)
    logger.debug("Text cleaned: %d → %d chars", len(raw), len(text))
    return text


def clean_papers(papers: list[dict]) -> list[dict]:
    """
    Apply clean_text() to each paper dict's 'text' field.

    Args:
        papers: List of dicts with keys 'filename', 'year', 'text'.

    Returns:
        Same list with 'text' replaced by cleaned text.
        Papers whose cleaned text is empty are dropped.
    """
    cleaned = []
    for p in papers:
        c = clean_text(p["text"])
        if c:
            cleaned.append({**p, "text": c})
        else:
            logger.warning("Paper %s produced empty text after cleaning — skipped.", p["filename"])
    return cleaned

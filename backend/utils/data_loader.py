"""
backend/utils/data_loader.py
Loads past paper files (PDF or TXT) from the structured folder tree.

Folder layout:
  data/past_papers/
    Grade9/
      Federal Board/
        Physics/
          2022.pdf
          2023.txt
          ...
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Root of all past papers, relative to the project root
BASE_DATA_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "past_papers"
)


def _normalise(name: str) -> str:
    """Lower-case + strip for case-insensitive matching."""
    return name.strip().lower()


def list_grades() -> list[str]:
    """Return all available grade folders."""
    base = Path(BASE_DATA_DIR)
    if not base.exists():
        return []
    return sorted([d.name for d in base.iterdir() if d.is_dir()])


def list_boards(grade: str) -> list[str]:
    """Return all board folders under a given grade."""
    grade_path = Path(BASE_DATA_DIR) / grade
    if not grade_path.exists():
        return []
    return sorted([d.name for d in grade_path.iterdir() if d.is_dir()])


def list_subjects(grade: str, board: str) -> list[str]:
    """Return all subject folders under grade/board."""
    subject_path = Path(BASE_DATA_DIR) / grade / board
    if not subject_path.exists():
        return []
    return sorted([d.name for d in subject_path.iterdir() if d.is_dir()])


def get_paper_files(grade: str, board: str, subject: str) -> list[Path]:
    """
    Return all PDF and TXT files under grade/board/subject.
    Performs case-insensitive matching on folder names.
    """
    base = Path(BASE_DATA_DIR)

    # Case-insensitive folder matching
    def find_folder(parent: Path, target: str) -> Path | None:
        if not parent.exists():
            return None
        for child in parent.iterdir():
            if child.is_dir() and _normalise(child.name) == _normalise(target):
                return child
        return None

    grade_dir   = find_folder(base,       grade)
    board_dir   = find_folder(grade_dir,  board)   if grade_dir   else None
    subject_dir = find_folder(board_dir,  subject) if board_dir   else None

    if not subject_dir:
        logger.warning(
            "No folder found for Grade=%s Board=%s Subject=%s",
            grade, board, subject,
        )
        return []

    files = sorted(
        [f for f in subject_dir.iterdir() if f.suffix.lower() in {".pdf", ".txt"}]
    )
    logger.info(
        "Found %d file(s) for Grade=%s Board=%s Subject=%s",
        len(files), grade, board, subject,
    )
    return files


def load_all_texts(grade: str, board: str, subject: str) -> list[dict]:
    """
    Load text from every paper file for the given selection.

    Returns a list of dicts:
      { "filename": str, "year": str | None, "text": str }
    """
    from utils.ocr_pipeline import extract_text_from_file

    files  = get_paper_files(grade, board, subject)
    result = []

    for f in files:
        try:
            text = extract_text_from_file(f)
            if text.strip():
                year = _guess_year(f.stem)
                result.append({
                    "filename": f.name,
                    "year":     year,
                    "text":     text,
                })
        except Exception as exc:
            logger.warning("Failed to read %s: %s", f.name, exc)

    return result


def _guess_year(stem: str) -> str | None:
    """Try to extract a 4-digit year from the filename stem."""
    import re
    m = re.search(r"(20\d{2}|19\d{2})", stem)
    return m.group(1) if m else None

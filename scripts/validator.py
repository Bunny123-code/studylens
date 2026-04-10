#!/usr/bin/env python3
"""
StudyLens Dataset Validator

Validates, corrects, and cleans the past papers dataset.
- Detects and fixes incorrect grade/board/subject placements
- Removes duplicates (hash-based)
- Deletes corrupted or non-paper files
- Generates a detailed JSON report
"""

import os
import sys
import json
import hashlib
import shutil
import logging
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import pdfplumber

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("Validator")

# -------------------------------------------------------------------
# Constants & Patterns
# -------------------------------------------------------------------

VALID_EXTENSIONS = {".pdf", ".txt"}

# Subject keywords (standardized names)
SUBJECTS = {
    "Physics": ["physics", "physic", "فیسکس"],
    "Chemistry": ["chemistry", "chem", "کیمسٹری"],
    "Mathematics": ["mathematics", "math", "maths", "ریاضی"],
    "Biology": ["biology", "bio", "حیاتیات"],
    "English": ["english", "eng", "انگلش"],
    "Urdu": ["urdu", "اردو"],
    "Islamiat": ["islamiat", "islamiyat", "islamic studies", "اسلامیات"],
    "Pakistan Studies": ["pakistan studies", "pak study", "mutalia pakistan", "مطالعہ پاکستان"],
}

# Grade detection patterns (regex)
GRADE_PATTERNS = {
    "Grade9": [
        r"class\s*9", r"9th", r"ssc\s*part\s*I", r"part\s*I", r"IX",
        r"matric\s*part\s*1", r"secondary school certificate \(part I\)"
    ],
    "Grade10": [
        r"class\s*10", r"10th", r"ssc\s*part\s*II", r"part\s*II", r"X",
        r"matric\s*part\s*2", r"secondary school certificate \(part II\)"
    ],
    "Grade11": [
        r"class\s*11", r"11th", r"hssc\s*part\s*I", r"intermediate\s*part\s*I",
        r"1st\s*year", r"XI", r"higher secondary school certificate \(part I\)"
    ],
    "Grade12": [
        r"class\s*12", r"12th", r"hssc\s*part\s*II", r"intermediate\s*part\s*II",
        r"2nd\s*year", r"XII", r"higher secondary school certificate \(part II\)"
    ],
}

# Board patterns (expand as needed)
BOARD_PATTERNS = {
    "Federal Board": [
        r"federal\s*board", r"fbise", r"federal\s*board\s*of\s*intermediate",
        r"federal\s*board\s*islamabad"
    ],
    "Multan Board": [
        r"multan\s*board", r"bise\s*multan", r"board\s*of\s*intermediate.*multan"
    ],
    "Karachi Board": [
        r"karachi\s*board", r"biek", r"board\s*of\s*secondary\s*education\s*karachi"
    ],
    "Lahore Board": [
        r"lahore\s*board", r"bise\s*lahore"
    ],
    "Rawalpindi Board": [
        r"rawalpindi\s*board", r"bise\s*rawalpindi"
    ],
}

# Minimum thresholds
MIN_PDF_SIZE_KB = 10          # 10 KB
MIN_TXT_SIZE_BYTES = 200      # ~200 bytes of text
MIN_TEXT_LENGTH = 100         # characters

# -------------------------------------------------------------------
# Utility Functions
# -------------------------------------------------------------------

def compute_file_hash(filepath: Path) -> str:
    """Compute SHA256 hash of file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def extract_text_from_file(filepath: Path) -> str:
    """
    Extract text from a file.
    - If .pdf: use pdfplumber.
    - If .txt: read directly.
    Returns empty string on failure.
    """
    if filepath.suffix.lower() == ".pdf":
        try:
            with pdfplumber.open(filepath) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
                return text.strip()
        except Exception as e:
            logger.warning(f"PDF read error {filepath}: {e}")
            return ""
    elif filepath.suffix.lower() == ".txt":
        try:
            return filepath.read_text(encoding="utf-8").strip()
        except Exception:
            return ""
    return ""

def detect_from_text(text: str, patterns_dict: Dict[str, List[str]]) -> Optional[str]:
    """Return the key whose pattern matches first in text, or None."""
    text_lower = text.lower()
    for key, patterns in patterns_dict.items():
        for pat in patterns:
            if re.search(pat, text_lower):
                return key
    return None

def detect_grade(text: str) -> Optional[str]:
    return detect_from_text(text, GRADE_PATTERNS)

def detect_board(text: str) -> Optional[str]:
    return detect_from_text(text, BOARD_PATTERNS)

def detect_subject(text: str) -> Optional[str]:
    text_lower = text.lower()
    for subj, keywords in SUBJECTS.items():
        for kw in keywords:
            if kw in text_lower:
                return subj
    return None

def extract_year(text: str) -> Optional[str]:
    """Extract 4-digit year from text (2000-2029)."""
    match = re.search(r"\b(20[0-2][0-9])\b", text)
    return match.group(1) if match else None

# -------------------------------------------------------------------
# Core Validation Functions
# -------------------------------------------------------------------

def validate_file(filepath: Path) -> Tuple[bool, str]:
    """
    Check if file is valid (exists, readable, not corrupt, sufficient size/text).
    Returns (is_valid, reason).
    """
    if not filepath.exists():
        return False, "file missing"
    if not os.access(filepath, os.R_OK):
        return False, "not readable"

    suffix = filepath.suffix.lower()
    if suffix not in VALID_EXTENSIONS:
        return False, f"invalid extension {suffix}"

    # Size checks
    size = filepath.stat().st_size
    if suffix == ".pdf" and size < MIN_PDF_SIZE_KB * 1024:
        return False, f"PDF too small ({size} bytes)"
    if suffix == ".txt" and size < MIN_TXT_SIZE_BYTES:
        return False, f"TXT too small ({size} bytes)"

    # PDF corruption check: attempt to open with pdfplumber
    if suffix == ".pdf":
        try:
            with pdfplumber.open(filepath) as pdf:
                if len(pdf.pages) == 0:
                    return False, "PDF has no pages"
        except Exception as e:
            return False, f"corrupted PDF: {e}"

    return True, "ok"

def validate_content(filepath: Path) -> Tuple[bool, Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    Extract text from file and determine classification.
    Returns (has_sufficient_text, grade, board, subject, year).
    If text insufficient, grade/board/subject may be None.
    """
    text = extract_text_from_file(filepath)
    if len(text) < MIN_TEXT_LENGTH:
        return False, None, None, None, None

    grade = detect_grade(text)
    board = detect_board(text)
    subject = detect_subject(text)
    year = extract_year(text)

    # If any of the essential fields missing, consider content insufficient
    if not all([grade, board, subject]):
        return False, grade, board, subject, year

    return True, grade, board, subject, year

# -------------------------------------------------------------------
# Duplicate Detection
# -------------------------------------------------------------------

def find_duplicates(file_list: List[Path]) -> Dict[str, List[Path]]:
    """Group files by SHA256 hash."""
    hash_map = defaultdict(list)
    for fp in file_list:
        try:
            h = compute_file_hash(fp)
            hash_map[h].append(fp)
        except Exception as e:
            logger.error(f"Hash error {fp}: {e}")
    return {h: paths for h, paths in hash_map.items() if len(paths) > 1}

# -------------------------------------------------------------------
# Main Validator Class
# -------------------------------------------------------------------

class DatasetValidator:
    def __init__(self, base_dir: str = "data/past_papers"):
        self.base_dir = Path(base_dir)
        self.report = {
            "total_files_processed": 0,
            "files_validated": 0,
            "files_corrected": 0,
            "files_deleted": 0,
            "duplicates_removed": 0,
            "errors": [],
            "actions": []  # list of action dicts for detailed log
        }
        self.seen_hashes = set()  # for cross-directory dedup

    def log_action(self, action: str, details: str, filepath: Path):
        logger.info(f"[{action}] {details} - {filepath}")
        self.report["actions"].append({
            "action": action,
            "details": details,
            "file": str(filepath)
        })

    def safe_move(self, src: Path, dst: Path) -> bool:
        """Move file, creating parent dirs. If destination exists with different content, handle conflict."""
        if dst.exists():
            # Check if same content
            try:
                if compute_file_hash(src) == compute_file_hash(dst):
                    # Same file already there, can delete src
                    src.unlink()
                    return True
                else:
                    # Conflict: different file with same name; rename src with hash suffix
                    short_hash = compute_file_hash(src)[:6]
                    new_stem = f"{dst.stem}_{short_hash}"
                    dst = dst.with_name(f"{new_stem}{dst.suffix}")
                    self.log_action("RENAME", f"conflict resolved: {new_stem}", src)
            except Exception as e:
                self.report["errors"].append(f"Hash conflict error: {e}")
                return False

        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(src), str(dst))
            return True
        except Exception as e:
            self.report["errors"].append(f"Move failed {src} -> {dst}: {e}")
            return False

    def process_file(self, filepath: Path) -> bool:
        """
        Validate and potentially relocate a single file.
        Returns True if file remains (or was moved) successfully, False if deleted.
        """
        self.report["total_files_processed"] += 1

        # 1. Basic file validation
        is_valid, reason = validate_file(filepath)
        if not is_valid:
            self.log_action("DELETE", f"invalid file: {reason}", filepath)
            filepath.unlink(missing_ok=True)
            self.report["files_deleted"] += 1
            return False

        # 2. Content validation & classification
        has_content, detected_grade, detected_board, detected_subject, detected_year = validate_content(filepath)
        if not has_content:
            self.log_action("DELETE", "insufficient text / cannot classify", filepath)
            filepath.unlink(missing_ok=True)
            self.report["files_deleted"] += 1
            return False

        # 3. Duplicate detection (across whole dataset)
        try:
            fhash = compute_file_hash(filepath)
        except Exception:
            self.log_action("DELETE", "hash computation failed", filepath)
            filepath.unlink(missing_ok=True)
            self.report["files_deleted"] += 1
            return False

        if fhash in self.seen_hashes:
            self.log_action("DELETE", "duplicate file (hash match)", filepath)
            filepath.unlink(missing_ok=True)
            self.report["duplicates_removed"] += 1
            return False
        self.seen_hashes.add(fhash)

        # 4. Determine expected path based on detected metadata
        year = detected_year or "unknown_year"
        # Keep original extension
        suffix = filepath.suffix.lower()
        expected_dir = self.base_dir / detected_grade / detected_board / detected_subject
        expected_path = expected_dir / f"{year}{suffix}"

        # 5. If file is not already in expected location, move it
        current_parent = filepath.parent
        expected_parent = expected_path.parent
        if current_parent != expected_parent or filepath.name != expected_path.name:
            if self.safe_move(filepath, expected_path):
                self.log_action("FIXED", f"moved to {detected_grade}/{detected_board}/{detected_subject}", filepath)
                self.report["files_corrected"] += 1
            else:
                return False
        else:
            self.log_action("OK", "already correct", filepath)
            self.report["files_validated"] += 1

        return True

    def remove_duplicates_global(self, all_files: List[Path]):
        """Pre-scan to remove exact duplicates before processing."""
        # This is covered in process_file using seen_hashes, but we can also do a pre-pass
        # for efficiency.
        pass

    def scan_and_validate(self):
        """Main entry: traverse directory and validate all files."""
        # Collect all files in base_dir recursively
        all_files = []
        for ext in VALID_EXTENSIONS:
            all_files.extend(self.base_dir.glob(f"**/*{ext}"))

        logger.info(f"Found {len(all_files)} files to validate.")

        # Process each file
        for fp in all_files:
            self.process_file(fp)

        # Remove empty directories (optional)
        for root, dirs, files in os.walk(self.base_dir, topdown=False):
            root_path = Path(root)
            if root_path != self.base_dir and not any(root_path.iterdir()):
                try:
                    root_path.rmdir()
                    logger.info(f"Removed empty directory: {root_path}")
                except OSError:
                    pass

    def generate_report(self, output_path: str = "validation_report.json"):
        """Save report to JSON."""
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.report, f, indent=2)
        logger.info(f"Report saved to {output_path}")

# -------------------------------------------------------------------
# Main Execution
# -------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Validate and clean StudyLens dataset.")
    parser.add_argument("--base-dir", default="data/past_papers",
                        help="Path to the past_papers directory")
    parser.add_argument("--report", default="validation_report.json",
                        help="Output JSON report file")
    args = parser.parse_args()

    validator = DatasetValidator(base_dir=args.base_dir)
    validator.scan_and_validate()
    validator.generate_report(args.report)

    # Print summary
    print("\n=== Validation Summary ===")
    print(f"Total processed: {validator.report['total_files_processed']}")
    print(f"Validated (already correct): {validator.report['files_validated']}")
    print(f"Corrected (moved): {validator.report['files_corrected']}")
    print(f"Deleted (bad/duplicate): {validator.report['files_deleted']}")
    print(f"Duplicates removed: {validator.report['duplicates_removed']}")
    if validator.report["errors"]:
        print(f"Errors: {len(validator.report['errors'])}")
    print("==========================\n")

if __name__ == "__main__":
    main()

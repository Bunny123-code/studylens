#!/usr/bin/env python3
"""
scripts/ingest_papers.py
Professional PDF → TXT converter using ocrmypdf.
Stores .txt files in the same folder as the original PDF.
Resumable, memory‑optimized, continuous mode.

Fixes applied:
- Removed --remove-background (unsupported in current ocrmypdf)
- Added failure tracking (max 3 attempts per file)
- Uses pdftotext for digital PDFs to save time
"""

import sys
import os
import argparse
import json
import subprocess
import time
import shutil
from pathlib import Path
from typing import List, Set, Optional, Dict

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    def tqdm(iterable, **kwargs):
        return iterable

DATA_ROOTS = [Path("data/past_papers"), Path("data/model_papers")]
PROGRESS_FILE = Path("backend/data/ingest_progress.json")
FAILED_LOG = Path("backend/data/failed_files.log")
FAILURE_COUNT_FILE = Path("backend/data/failure_counts.json")

# Optimized ocrmypdf flags WITHOUT --remove-background
OCR_FLAGS = [
    "--tesseract-pagesegmode", "1",
    "--tesseract-oem", "1",
    "--oversample", "200",
    "--skip-text",                # skip if text already present
    "--output-type", "pdf",
    "--jobs", "1",
    "--max-image-mpixels", "500",
]

MAX_FAILURES = 3  # skip file after this many consecutive failures

def check_dependencies() -> None:
    if shutil.which("ocrmypdf") is None:
        print("ERROR: ocrmypdf not found. Install with:")
        print("  pip install ocrmypdf")
        print("  sudo apt-get install -y tesseract-ocr tesseract-ocr-eng poppler-utils")
        sys.exit(1)
    if shutil.which("pdftotext") is None:
        print("WARNING: pdftotext not found. Digital PDFs will be OCR'd instead.")
        print("  Install with: sudo apt-get install -y poppler-utils")

def load_json(path: Path, default=None):
    if not path.exists():
        return default if default is not None else {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default if default is not None else {}

def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    tmp.replace(path)

def load_progress() -> Set[str]:
    data = load_json(PROGRESS_FILE, {"completed": []})
    return set(data.get("completed", []))

def save_progress(completed: Set[str]) -> None:
    save_json(PROGRESS_FILE, {"completed": list(completed)})

def load_failure_counts() -> Dict[str, int]:
    return load_json(FAILURE_COUNT_FILE, {})

def save_failure_counts(counts: Dict[str, int]) -> None:
    save_json(FAILURE_COUNT_FILE, counts)

def log_failed_file(pdf_path: Path) -> None:
    with open(FAILED_LOG, "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {pdf_path}\n")

def find_all_pdfs(board_filter: Optional[str] = None) -> List[Path]:
    pdfs = []
    for root in DATA_ROOTS:
        if not root.exists():
            continue
        for pdf in root.rglob("*.pdf"):
            if board_filter and board_filter not in pdf.parts:
                continue
            pdfs.append(pdf.resolve())
    return sorted(pdfs)

def extract_text_from_digital_pdf(pdf_path: Path) -> bool:
    """Use pdftotext to extract text from a PDF that already has a text layer."""
    txt_path = pdf_path.with_suffix(".txt")
    try:
        subprocess.run(
            ["pdftotext", "-layout", str(pdf_path), str(txt_path)],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
        )
        return txt_path.exists()
    except Exception:
        return False

def process_pdf(pdf_path: Path) -> bool:
    """
    Attempt to extract text.
    First try pdftotext for digital PDFs (fast).
    If that fails or produces empty file, fall back to ocrmypdf.
    """
    txt_path = pdf_path.with_suffix(".txt")

    # 1. Try pdftotext first (if available)
    if shutil.which("pdftotext"):
        if extract_text_from_digital_pdf(pdf_path):
            # Check if file is not empty
            if txt_path.stat().st_size > 100:  # at least some text
                return True
            else:
                txt_path.unlink(missing_ok=True)  # delete empty, fall back to OCR

    # 2. Fall back to ocrmypdf
    try:
        cmd = [
            "ocrmypdf",
            "--sidecar", str(txt_path),
            *OCR_FLAGS,
            str(pdf_path),
            "/dev/null"
        ]
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            tqdm.write(f"  FAILED (ocrmypdf): {pdf_path.name} - {result.stderr.strip()}")
            return False
        return txt_path.exists()
    except Exception as e:
        tqdm.write(f"  ERROR: {pdf_path.name} - {e}")
        return False

def get_pending_pdfs(force: bool = False, board_filter: Optional[str] = None) -> List[Path]:
    all_pdfs = find_all_pdfs(board_filter)
    completed = load_progress()
    failure_counts = load_failure_counts()
    pending = []

    for pdf in all_pdfs:
        pdf_str = str(pdf)
        if force:
            pending.append(pdf)
        else:
            # Skip if already marked complete OR .txt exists
            if pdf_str in completed or pdf.with_suffix(".txt").exists():
                if pdf_str not in completed and pdf.with_suffix(".txt").exists():
                    completed.add(pdf_str)
                    save_progress(completed)
                continue

            # Skip if failed too many times
            fails = failure_counts.get(pdf_str, 0)
            if fails >= MAX_FAILURES:
                continue

            pending.append(pdf)
    return pending

def ingest_continuous(force: bool = False, board: Optional[str] = None, sleep_between: int = 10):
    print("Continuous mode. Press Ctrl+C to stop.\n")
    all_pdfs = find_all_pdfs(board)
    total = len(all_pdfs)
    print(f"Total PDFs matching filter: {total}")

    completed = load_progress()
    failure_counts = load_failure_counts()
    print(f"Already completed: {len(completed)}")
    print(f"Files with failures: {len(failure_counts)}")

    while True:
        pending = get_pending_pdfs(force=force, board_filter=board)
        if not pending:
            print("All PDFs processed or max failures reached. Exiting.")
            break

        pdf = pending[0]
        pdf_str = str(pdf)
        rel_path = pdf.relative_to(Path.cwd())
        print(f"[{time.strftime('%H:%M:%S')}] Processing: {rel_path}")

        success = process_pdf(pdf)
        if success:
            completed.add(pdf_str)
            save_progress(completed)
            # Clear failure count for this file
            if pdf_str in failure_counts:
                del failure_counts[pdf_str]
                save_failure_counts(failure_counts)
            print(f"  Success. ({len(completed)}/{total} completed)")
        else:
            # Increment failure count
            failure_counts[pdf_str] = failure_counts.get(pdf_str, 0) + 1
            save_failure_counts(failure_counts)
            fails = failure_counts[pdf_str]
            print(f"  Failed ({fails}/{MAX_FAILURES}).")
            if fails >= MAX_FAILURES:
                log_failed_file(pdf)
                print(f"  Maximum failures reached. Skipping this file permanently.")

        time.sleep(sleep_between)

def main():
    parser = argparse.ArgumentParser(description="StudyLens PDF Ingestion")
    parser.add_argument("--max-files", type=int, help="Process N files then stop")
    parser.add_argument("--continuous", action="store_true", help="Run until all done")
    parser.add_argument("--force", action="store_true", help="Re‑extract all (ignore progress)")
    parser.add_argument("--board", type=str, help="Only process PDFs under this board folder (e.g., FBISE)")
    parser.add_argument("--sleep", type=int, default=5, help="Seconds between files in continuous mode")
    args = parser.parse_args()

    check_dependencies()

    if args.continuous:
        ingest_continuous(force=args.force, board=args.board, sleep_between=args.sleep)
    else:
        # For batch mode, you may want to add similar failure handling.
        # For now, keep simple.
        from tqdm import tqdm as tqdm_module
        pending = get_pending_pdfs(force=args.force, board_filter=args.board)
        if args.max_files:
            pending = pending[:args.max_files]
        print(f"Processing {len(pending)} PDFs.")
        completed = load_progress()
        for pdf in tqdm_module(pending):
            if process_pdf(pdf):
                completed.add(str(pdf))
                save_progress(completed)
            time.sleep(1)

if __name__ == "__main__":
    main()

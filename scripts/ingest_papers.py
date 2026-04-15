#!/usr/bin/env python3

import os
import sys
import json
import re
import io
import argparse
import time
from pathlib import Path
from typing import Set, List, Optional, Tuple

# -----------------------------
# DEPENDENCIES
# -----------------------------
try:
    import fitz  # PyMuPDF
except ImportError:
    print("Install PyMuPDF: pip install pymupdf")
    sys.exit(1)

try:
    import pytesseract
    from PIL import Image
except ImportError:
    print("Install pytesseract + pillow: pip install pytesseract pillow")
    sys.exit(1)

# -----------------------------
# CONFIG
# -----------------------------
DATA_ROOTS = [
    Path("data/past_papers"),
    Path("data/model_papers"),
]

PROGRESS_FILE = Path("backend/data/ingest_progress.json")
FAILURE_FILE = Path("backend/data/failure_counts.json")

FAST_DPI = 200
ACCURATE_DPI = 300
MIN_VALID_SIZE = 1000  # bytes

TESS_FAST = "--psm 4 --oem 1"
TESS_ACCURATE = "--psm 6 --oem 1"

# -----------------------------
# JSON HELPERS
# -----------------------------
def load_json(path, default):
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    tmp.replace(path)

def load_progress():
    return set(load_json(PROGRESS_FILE, {"completed": []})["completed"])

def save_progress(s):
    save_json(PROGRESS_FILE, {"completed": list(s)})

def load_failures():
    return load_json(FAILURE_FILE, {})

def save_failures(f):
    save_json(FAILURE_FILE, f)

# -----------------------------
# FILE DISCOVERY
# -----------------------------
def find_pdfs():
    pdfs = []
    for root in DATA_ROOTS:
        if root.exists():
            pdfs.extend(root.rglob("*.pdf"))
    return sorted(pdfs)

# -----------------------------
# OCR CORE
# -----------------------------
def preprocess(pix):
    img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("L")
    img = img.point(lambda x: 0 if x < 140 else 255, "1")
    return img

def ocr_page(page, dpi, config):
    pix = page.get_pixmap(dpi=dpi)
    img = preprocess(pix)
    text = pytesseract.image_to_string(img, config=config)
    return text

def extract_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    pages = []

    for i in range(len(doc)):
        page = doc.load_page(i)
        text = ocr_page(page, FAST_DPI, TESS_FAST)
        pages.append(text)

    doc.close()
    return "\n\n".join(pages)

def extract_pdf_high_quality(pdf_path):
    doc = fitz.open(pdf_path)
    pages = []

    for i in range(len(doc)):
        page = doc.load_page(i)
        text = ocr_page(page, ACCURATE_DPI, TESS_ACCURATE)
        pages.append(text)

    doc.close()
    return "\n\n".join(pages)

# -----------------------------
# VALIDATION
# -----------------------------
def is_valid(txt_path):
    return txt_path.exists() and txt_path.stat().st_size > MIN_VALID_SIZE

# -----------------------------
# PROCESS ONE FILE
# -----------------------------
def process_pdf(pdf):
    txt_path = pdf.with_suffix(".txt")

    # Skip if already valid
    if is_valid(txt_path):
        return True, "already_done"

    try:
        text = extract_pdf(pdf)

        # Retry if weak
        if len(text.strip()) < 300:
            text = extract_pdf_high_quality(pdf)

        # Ensure directory exists
        txt_path.parent.mkdir(parents=True, exist_ok=True)

        # Write safely
        tmp = txt_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)

        tmp.replace(txt_path)

        # Verify
        if not is_valid(txt_path):
            return False, "invalid_output"

        return True, "success"

    except Exception as e:
        return False, str(e)

# -----------------------------
# MAIN LOOP
# -----------------------------
def run(force=False, sleep=1):
    pdfs = find_pdfs()
    progress = load_progress()
    failures = load_failures()

    total = len(pdfs)
    done = 0

    print(f"Total PDFs: {total}")

    for pdf in pdfs:
        pdf_str = str(pdf)
        txt_path = pdf.with_suffix(".txt")

        # Fix corrupted progress
        if pdf_str in progress and not is_valid(txt_path):
            print(f"[FIX] Missing txt → reprocessing: {pdf}")
            progress.remove(pdf_str)
            save_progress(progress)

        # Skip valid
        if not force and is_valid(txt_path):
            if pdf_str not in progress:
                progress.add(pdf_str)
                save_progress(progress)
            done += 1
            continue

        print(f"[{done+1}/{total}] Processing: {pdf}")

        success, msg = process_pdf(pdf)

        if success:
            progress.add(pdf_str)
            save_progress(progress)
            print("   ✓ Done")
        else:
            failures[pdf_str] = failures.get(pdf_str, 0) + 1
            save_failures(failures)
            print(f"   ✗ Failed: {msg}")

        done += 1
        time.sleep(sleep)

    print("Completed.")

# -----------------------------
# ENTRY
# -----------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    run(force=args.force)

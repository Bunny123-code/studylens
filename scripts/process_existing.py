#!/usr/bin/env python3
"""
Process already downloaded raw files without scraping.
Extracts text, classifies, and organizes into final folder structure.
"""

import sys
from pathlib import Path

# Add project root to Python path
sys.path.append(str(Path(__file__).parent.parent))

from scripts.processor import FileProcessor
from scripts.classifier import Classifier
from scripts.organizer import Organizer
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("ProcessOnly")

def main():
    raw_dir = Path("data/raw")
    past_papers_dir = Path("data/past_papers")

    if not raw_dir.exists():
        logger.error(f"Raw directory does not exist: {raw_dir}")
        return

    processor = FileProcessor()
    classifier = Classifier()
    organizer = Organizer(base_dir=str(past_papers_dir))

    all_files = list(raw_dir.glob("**/*"))
    pdf_files = [f for f in all_files if f.is_file() and f.suffix.lower() in ['.pdf', '.jpg', '.jpeg', '.png']]
    logger.info(f"Found {len(pdf_files)} raw files to process.")

    processed = 0
    for file_path in pdf_files:
        logger.info(f"Processing {file_path}")
        text, file_type = processor.process_file(file_path)

        if not text:
            logger.warning(f"No text extracted from {file_path}, skipping.")
            continue

        classification = classifier.classify(text)
        if not classification:
            logger.warning(f"Classification failed for {file_path}, skipping.")
            continue

        logger.info(f"Classified as: Grade={classification['grade']}, Board={classification['board']}, "
                    f"Subject={classification['subject']}, Year={classification['year']}")

        if organizer.organize(file_path, text, classification):
            processed += 1

    logger.info(f"Processing completed. Successfully organized {processed} files.")

if __name__ == "__main__":
    main()

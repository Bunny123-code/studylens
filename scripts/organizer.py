import os
import shutil
import hashlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class Organizer:
    """Move processed files into final structure and create .txt files."""

    def __init__(self, base_dir="data/past_papers"):
        self.base_dir = Path(base_dir)
        self.processed_hashes = set()  # global deduplication across all files

    def _compute_file_hash(self, file_path):
        """SHA256 hash of file content."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def organize(self, raw_file_path, extracted_text, classification):
        """
        Move raw file to final location, rename with year, and save .txt.
        classification dict must contain grade, board, subject, year.
        Returns True if successful.
        """
        if not classification:
            logger.warning(f"No classification for {raw_file_path}, skipping.")
            return False

        grade = classification["grade"]
        board = classification["board"]
        subject = classification["subject"]
        year = classification["year"]

        # Build destination path
        dest_dir = self.base_dir / grade / board / subject
        dest_dir.mkdir(parents=True, exist_ok=True)

        # File hash for deduplication
        file_hash = self._compute_file_hash(raw_file_path)
        if file_hash in self.processed_hashes:
            logger.info(f"Duplicate file skipped (hash already processed): {raw_file_path}")
            return False
        self.processed_hashes.add(file_hash)

        # Determine extension (keep original)
        suffix = Path(raw_file_path).suffix.lower()
        new_filename = f"{year}{suffix}"
        dest_pdf_path = dest_dir / new_filename

        # If a file with same name exists but different hash, append a suffix
        if dest_pdf_path.exists():
            existing_hash = self._compute_file_hash(dest_pdf_path)
            if existing_hash != file_hash:
                # Conflict: same year but different content. Append a short hash.
                short_hash = file_hash[:6]
                new_filename = f"{year}_{short_hash}{suffix}"
                dest_pdf_path = dest_dir / new_filename
                logger.warning(f"Year conflict resolved by appending hash: {dest_pdf_path}")

        # Copy file (or move)
        shutil.copy2(raw_file_path, dest_pdf_path)
        logger.info(f"Copied to {dest_pdf_path}")

        # Save extracted text as .txt
        txt_path = dest_dir / f"{year}.txt"
        # If txt already exists, we might want to keep the latest or merge?
        # For simplicity, overwrite only if same year (assuming one paper per year per subject)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(extracted_text)
        logger.info(f"Saved text to {txt_path}")

        return True

import io
import logging
from pathlib import Path

import pdfplumber
from PIL import Image
import pytesseract
from pdf2image import convert_from_path

logger = logging.getLogger(__name__)

class FileProcessor:
    """Extract text from PDF or image files. PDFs get OCR fallback if needed."""

    def __init__(self, min_text_length=50):
        self.min_text_length = min_text_length

    def _ocr_image(self, image):
        """Run Tesseract on a PIL Image."""
        try:
            return pytesseract.image_to_string(image, lang="eng+urd")  # support Urdu
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return ""

    def _extract_pdf_text(self, pdf_path):
        """Extract text from PDF using pdfplumber; if text too short, OCR all pages."""
        text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            logger.warning(f"pdfplumber error on {pdf_path}: {e}")

        if len(text.strip()) >= self.min_text_length:
            return text.strip()

        # Fallback: OCR the PDF as images
        logger.info(f"pdfplumber gave short text ({len(text)} chars). Falling back to OCR for {pdf_path}")
        try:
            images = convert_from_path(pdf_path, dpi=200)
            ocr_text = ""
            for img in images:
                ocr_text += self._ocr_image(img) + "\n"
            return ocr_text.strip()
        except Exception as e:
            logger.error(f"PDF OCR fallback failed for {pdf_path}: {e}")
            return text.strip()  # return whatever we had

    def _extract_image_text(self, img_path):
        """Run OCR directly on an image file."""
        try:
            img = Image.open(img_path)
            return self._ocr_image(img).strip()
        except Exception as e:
            logger.error(f"Image OCR failed for {img_path}: {e}")
            return ""

    def process_file(self, file_path):
        """
        Determine file type and extract text.
        Returns (text, file_type) where file_type is 'pdf' or 'image'.
        """
        file_path = Path(file_path)
        suffix = file_path.suffix.lower()

        if suffix == ".pdf":
            text = self._extract_pdf_text(file_path)
            return text, "pdf"
        elif suffix in [".jpg", ".jpeg", ".png"]:
            text = self._extract_image_text(file_path)
            return text, "image"
        else:
            logger.warning(f"Unsupported file type: {file_path}")
            return "", "unknown"

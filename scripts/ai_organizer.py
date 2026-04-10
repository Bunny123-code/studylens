import os
import pdfplumber
import shutil

RAW_DIR = "data/raw"
FINAL_DIR = "data/past_papers"

def extract_text(pdf_path):
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
    except:
        pass
    return text.lower()


def detect_grade(text):
    if "class 9" in text or "ix" in text:
        return "Grade9"
    if "class 10" in text or "x" in text:
        return "Grade10"
    if "class 11" in text or "xi" in text:
        return "Grade11"
    if "class 12" in text or "xii" in text:
        return "Grade12"
    return None


def detect_subject(text):
    subjects = ["physics", "chemistry", "mathematics", "biology"]
    for s in subjects:
        if s in text:
            return s.capitalize()
    return None


def detect_board(text):
    if "federal board" in text or "fbise" in text:
        return "Federal Board"
    if "multan" in text:
        return "Multan Board"
    if "karachi" in text:
        return "Karachi Board"
    return "Other Board"


def run():
    for root, _, files in os.walk(RAW_DIR):
        for file in files:
            if not file.endswith(".pdf"):
                continue

            path = os.path.join(root, file)

            text = extract_text(path)

            grade = detect_grade(text)
            subject = detect_subject(text)
            board = detect_board(text)

            if not grade or not subject:
                continue

            dest = os.path.join(FINAL_DIR, grade, board, subject)
            os.makedirs(dest, exist_ok=True)

            shutil.move(path, os.path.join(dest, file))


if __name__ == "__main__":
    run()

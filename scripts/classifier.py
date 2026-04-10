import re
import logging
from collections import Counter

logger = logging.getLogger(__name__)

class Classifier:
    """
    Rule‑based classifier that determines Grade, Board, and Subject from extracted text.
    Does NOT use filenames or URLs.
    """

    # Standardised subjects (must match final folder names)
    SUBJECTS = [
        "Physics", "Chemistry", "Mathematics", "Biology",
        "English", "Urdu", "Islamiat", "Pakistan Studies"
    ]

    # Subject keyword variations (lowercase)
    SUBJECT_KEYWORDS = {
        "Physics": ["physics", "physic", "فیسکس"],
        "Chemistry": ["chemistry", "chem", "کیمسٹری"],
        "Mathematics": ["mathematics", "math", "maths", "ریاضی"],
        "Biology": ["biology", "bio", "حیاتیات"],
        "English": ["english", "eng", "انگلش"],
        "Urdu": ["urdu", "اردو"],
        "Islamiat": ["islamiat", "islamiyat", "islamic studies", "اسلامیات"],
        "Pakistan Studies": ["pakistan studies", "pak study", "mutalia pakistan", "مطالعہ پاکستان"],
    }

    # Grade patterns
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

    # Board patterns (including variations)
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
        # Add more boards as needed (e.g., Lahore, Rawalpindi)
    }

    def __init__(self):
        # Compile regex patterns for performance
        self.grade_regex = {
            grade: [re.compile(p, re.IGNORECASE) for p in patterns]
            for grade, patterns in self.GRADE_PATTERNS.items()
        }
        self.board_regex = {
            board: [re.compile(p, re.IGNORECASE) for p in patterns]
            for board, patterns in self.BOARD_PATTERNS.items()
        }
        self.subject_keywords = self.SUBJECT_KEYWORDS

    def _find_grade(self, text):
        """Return best matching grade string (e.g., 'Grade9') or None."""
        scores = Counter()
        for grade, patterns in self.grade_regex.items():
            for pattern in patterns:
                if pattern.search(text):
                    scores[grade] += 1
        if scores:
            return scores.most_common(1)[0][0]
        return None

    def _find_board(self, text):
        """Return best matching board name or None."""
        scores = Counter()
        for board, patterns in self.board_regex.items():
            for pattern in patterns:
                if pattern.search(text):
                    scores[board] += 1
        if scores:
            return scores.most_common(1)[0][0]
        # If no board found, we could fallback to "Federal Board" as default?
        # Requirement says MUST NOT rely on URLs, but we can still try to detect.
        # We'll log a warning and return "UnknownBoard" – but that violates the "no Unknown" rule.
        # Better: raise an exception so the file gets skipped/logged for manual check.
        logger.warning("No board detected in text.")
        return None

    def _find_subject(self, text):
        """Return standardised subject name or None."""
        text_lower = text.lower()
        for subject, keywords in self.subject_keywords.items():
            for kw in keywords:
                if kw in text_lower:
                    return subject
        return None

    def _extract_year(self, text):
        """Try to extract a 4‑digit year from text (e.g., 2022)."""
        match = re.search(r"\b(20[0-2][0-9])\b", text)  # years 2000–2029
        if match:
            return match.group(1)
        return None

    def classify(self, text):
        """
        Analyse text and return a dict with:
        { 'grade': 'Grade12', 'board': 'Federal Board', 'subject': 'Physics', 'year': '2022' }
        If any field cannot be determined, returns None for that field.
        """
        if not text or len(text.strip()) < 20:
            logger.warning("Text too short for classification.")
            return None

        grade = self._find_grade(text)
        board = self._find_board(text)
        subject = self._find_subject(text)
        year = self._extract_year(text)

        if not all([grade, board, subject]):
            missing = [k for k, v in {"grade": grade, "board": board, "subject": subject}.items() if not v]
            logger.warning(f"Classification incomplete. Missing: {missing}. Text snippet: {text[:200]}")
            return None

        return {
            "grade": grade,
            "board": board,
            "subject": subject,
            "year": year or "unknown_year"
        }

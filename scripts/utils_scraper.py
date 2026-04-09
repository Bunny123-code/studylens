import os, re, requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

HEADERS = {"User-Agent": "Mozilla/5.0"}

BOARD_MAP = {
    "fbise": "Federal Board",
    "federal": "Federal Board",
    "karachi": "Karachi Board",
    "biek": "Karachi Board",
    "bsek": "Karachi Board",
    "multan": "Multan Board",
    "lahore": "Lahore Board",
    "gujranwala": "Gujranwala Board",
    "sahiwal": "Sahiwal Board",
    "punjab": "Punjab Board",
    "kpk": "KPK Board",
    "peshawar": "Peshawar Board",
    "balochistan": "Balochistan Board",
    "quetta": "Quetta Board",
    "sindh": "Sindh Board"
}

VALID_SUBJECTS = ["physics", "chemistry", "mathematics", "math"]

def get_soup(url):
    return BeautifulSoup(requests.get(url, headers=HEADERS, timeout=15).text, "html.parser")

def extract_year(text):
    m = re.search(r"(20\d{2})", text)
    return m.group(1) if m else None

def detect_subject(text):
    text = text.lower()
    for s in VALID_SUBJECTS:
        if s in text:
            return "Mathematics" if s == "math" else s.capitalize()
    return None

def detect_board(text):
    text = text.lower()
    for k, v in BOARD_MAP.items():
        if k in text:
            return v
    return None

def save_file(url, path):
    r = requests.get(url, headers=HEADERS, stream=True, timeout=20)
    if r.status_code == 200:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            for chunk in r.iter_content(1024):
                f.write(chunk)

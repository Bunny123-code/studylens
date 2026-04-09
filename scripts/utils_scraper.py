import os, re, requests, time
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# =========================
# SESSION WITH RETRY
# =========================

def create_session():
    session = requests.Session()

    retries = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504]
    )

    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session

SESSION = create_session()

HEADERS = {"User-Agent": "Mozilla/5.0"}

# =========================

def get_soup(url):
    try:
        res = SESSION.get(url, headers=HEADERS, timeout=30)
        return BeautifulSoup(res.text, "html.parser")
    except Exception as e:
        print(f"[ERROR] Failed: {url}")
        return None

def extract_year(text):
    m = re.search(r"(20\d{2})", text)
    return m.group(1) if m else None

def save_file(url, path):
    try:
        r = SESSION.get(url, headers=HEADERS, stream=True, timeout=30)

        if r.status_code == 200:
            os.makedirs(os.path.dirname(path), exist_ok=True)

            with open(path, "wb") as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)

            print(f"[SAVED] {path}")

    except Exception as e:
        print(f"[DOWNLOAD ERROR] {url}")

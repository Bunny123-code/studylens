import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from tqdm import tqdm

# ==============================
# CONFIGURATION
# ==============================

BASE_DIR = "data/past_papers"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# Example sources (you will expand these)
SOURCES = {
    "Federal Board": {
        "Physics": [
            "https://example.com/fbise/physics-past-papers"
        ],
        "Chemistry": [],
        "Mathematics": []
    },
    "Sindh Board": {
        "Physics": [],
        "Chemistry": [],
        "Mathematics": []
    },
    "Karachi Board": {
        "Physics": [],
        "Chemistry": [],
        "Mathematics": []
    }
}

GRADE = "Grade12"


# ==============================
# CORE FUNCTIONS
# ==============================

def create_folder(path):
    os.makedirs(path, exist_ok=True)


def get_pdf_links(url):
    """Extract all PDF links from a webpage"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if ".pdf" in href.lower():
                full_url = urljoin(url, href)
                links.append(full_url)

        return links

    except Exception as e:
        print(f"[ERROR] Failed to scrape {url}: {e}")
        return []


def download_file(url, save_path):
    """Download a single PDF"""
    try:
        response = requests.get(url, headers=HEADERS, stream=True, timeout=20)
        if response.status_code == 200:
            with open(save_path, "wb") as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
        else:
            print(f"[FAILED] {url}")
    except Exception as e:
        print(f"[ERROR] {url}: {e}")


def extract_year_from_url(url):
    """Try to extract year from filename"""
    import re
    match = re.search(r"(20\d{2})", url)
    return match.group(1) if match else None


# ==============================
# MAIN SCRAPER
# ==============================

def run_scraper():
    for board, subjects in SOURCES.items():
        for subject, urls in subjects.items():
            for page_url in urls:

                print(f"\nScraping: {board} | {subject}")
                pdf_links = get_pdf_links(page_url)

                save_dir = os.path.join(BASE_DIR, GRADE, board, subject)
                create_folder(save_dir)

                for link in tqdm(pdf_links):
                    year = extract_year_from_url(link)

                    if not year:
                        continue  # skip unknown files

                    filename = f"{year}.pdf"
                    save_path = os.path.join(save_dir, filename)

                    if os.path.exists(save_path):
                        continue  # skip existing

                    download_file(link, save_path)


if __name__ == "__main__":
    run_scraper()

import os
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

BASE_DIR = "data/raw"

SOURCES = {
    "fbise": [
        "https://fbisepastpapers.com/class-9-fbise-past-papers/",
        "https://fbisepastpapers.com/class-10-fbise-past-papers/",
        "https://fbisepastpapers.com/class-11-fbise-past-papers/",
        "https://fbisepastpapers.com/class-12-fbise-past-papers/"
    ],
    "multan": [
        "https://web.bisemultan.edu.pk/past-papers-9th/",
        "https://web.bisemultan.edu.pk/past-papers-10th/",
        "https://web.bisemultan.edu.pk/past-papers-part-i/",
        "https://web.bisemultan.edu.pk/past-papers-part-ii/"
    ],
    "ilmkidunya": [
        "https://www.ilmkidunya.com/past_papers/9th-past-papers.aspx",
        "https://www.ilmkidunya.com/past_papers/10th-past-papers.aspx",
        "https://www.ilmkidunya.com/past_papers/11th-past-papers.aspx",
        "https://www.ilmkidunya.com/past_papers/12th-past-papers.aspx"
    ]
}

HEADERS = {"User-Agent": "Mozilla/5.0"}

def download(url, path):
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code == 200:
            with open(path, "wb") as f:
                f.write(r.content)
    except:
        pass

def run():
    for source, urls in SOURCES.items():
        for url in urls:
            print(f"[SCRAPING] {url}")

            try:
                soup = BeautifulSoup(requests.get(url, headers=HEADERS).text, "html.parser")

                for a in soup.find_all("a", href=True):
                    link = urljoin(url, a["href"])

                    if ".pdf" not in link:
                        continue

                    filename = link.split("/")[-1]

                    save_path = os.path.join(BASE_DIR, source, filename)
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)

                    if not os.path.exists(save_path):
                        download(link, save_path)

            except:
                continue

if __name__ == "__main__":
    run()

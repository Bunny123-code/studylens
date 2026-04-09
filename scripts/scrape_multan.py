import os
from urllib.parse import urljoin
from utils_scraper import get_soup, extract_year, detect_subject, save_file

BASE_DIR = "data/past_papers"

GRADES = {
    "Grade9": "https://web.bisemultan.edu.pk/past-papers-9th/",
    "Grade10": "https://web.bisemultan.edu.pk/past-papers-10th/",
    "Grade11": "https://web.bisemultan.edu.pk/past-papers-part-i/",
    "Grade12": "https://web.bisemultan.edu.pk/past-papers-part-ii/"
}

def run():
    for grade, url in GRADES.items():
        soup = get_soup(url)

        for a in soup.find_all("a", href=True):
            href = urljoin(url, a["href"])

            if ".pdf" not in href:
                continue

            subject = detect_subject(href)
            year = extract_year(href)

            if not subject or not year:
                continue

            path = os.path.join(
                BASE_DIR, grade, "Multan Board", subject, f"{year}.pdf"
            )

            if not os.path.exists(path):
                save_file(href, path)

if __name__ == "__main__":
    run()

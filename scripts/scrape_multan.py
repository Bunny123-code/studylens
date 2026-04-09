import os
from urllib.parse import urljoin
from utils_scraper import get_soup, extract_year, save_file

BASE_DIR = "data/past_papers"

GRADES = {
    "Grade9": "https://web.bisemultan.edu.pk/past-papers-9th/",
    "Grade10": "https://web.bisemultan.edu.pk/past-papers-10th/",
    "Grade11": "https://web.bisemultan.edu.pk/past-papers-part-i/",
    "Grade12": "https://web.bisemultan.edu.pk/past-papers-part-ii/"
}

def run():
    for grade, url in GRADES.items():
        print(f"\n[MULTAN] {grade}")

        soup = get_soup(url)
        if not soup:
            continue  # ← prevents crash

        for a in soup.find_all("a", href=True):
            link = urljoin(url, a["href"])

            if ".pdf" not in link:
                continue

            year = extract_year(link)
            subject = a.text.strip() or "Unknown"

            if not year:
                continue

            path = os.path.join(
                BASE_DIR, grade, "Multan Board", subject, f"{year}.pdf"
            )

            if not os.path.exists(path):
                save_file(link, path)

if __name__ == "__main__":
    run()

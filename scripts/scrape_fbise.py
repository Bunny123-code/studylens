import os
from urllib.parse import urljoin
from utils_scraper import get_soup, extract_year, detect_subject, save_file

BASE_DIR = "data/past_papers"

GRADES = {
    "Grade9": "https://fbisepastpapers.com/class-9-fbise-past-papers/",
    "Grade10": "https://fbisepastpapers.com/class-10-fbise-past-papers/",
    "Grade11": "https://fbisepastpapers.com/class-11-fbise-past-papers/",
    "Grade12": "https://fbisepastpapers.com/class-12-fbise-past-papers/"
}

def run():
    for grade, url in GRADES.items():
        soup = get_soup(url)

        for a in soup.find_all("a", href=True):
            href = urljoin(url, a["href"])

            if ".pdf" not in href:
                continue

            subject = detect_subject(href + a.text)
            year = extract_year(href)

            if not subject or not year:
                continue

            path = os.path.join(
                BASE_DIR, grade, "Federal Board", subject, f"{year}.pdf"
            )

            if not os.path.exists(path):
                save_file(href, path)

if __name__ == "__main__":
    run()

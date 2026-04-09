import os
from urllib.parse import urljoin
from utils_scraper import get_soup, extract_year, save_file

BASE_DIR = "data/past_papers"

GRADES = {
    "Grade9": "https://fbisepastpapers.com/class-9-fbise-past-papers/",
    "Grade10": "https://fbisepastpapers.com/class-10-fbise-past-papers/",
    "Grade11": "https://fbisepastpapers.com/class-11-fbise-past-papers/",
    "Grade12": "https://fbisepastpapers.com/class-12-fbise-past-papers/"
}

def run():
    for grade, url in GRADES.items():
        print(f"\n[FBISE] {grade}")

        soup = get_soup(url)
        if not soup:
            continue

        for a in soup.find_all("a", href=True):
            link = urljoin(url, a["href"])

            # STEP 1: If direct PDF
            if ".pdf" in link:
                year = extract_year(link)
                if not year:
                    continue

                subject = a.text.strip() or "Unknown"

                path = os.path.join(
                    BASE_DIR, grade, "Federal Board", subject, f"{year}.pdf"
                )

                if not os.path.exists(path):
                    save_file(link, path)

            # STEP 2: If intermediate page
            else:
                sub_soup = get_soup(link)
                if not sub_soup:
                    continue

                for sub_a in sub_soup.find_all("a", href=True):
                    sub_link = urljoin(link, sub_a["href"])

                    if ".pdf" not in sub_link:
                        continue

                    year = extract_year(sub_link)
                    if not year:
                        continue

                    subject = a.text.strip() or "Unknown"

                    path = os.path.join(
                        BASE_DIR, grade, "Federal Board", subject, f"{year}.pdf"
                    )

                    if not os.path.exists(path):
                        save_file(sub_link, path)

if __name__ == "__main__":
    run()

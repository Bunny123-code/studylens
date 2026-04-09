import os, time
from urllib.parse import urljoin
from utils_scraper import get_soup, extract_year, save_file

BASE_DIR = "data/past_papers"

def run(base_url, grade):
    print(f"\n[ILMKIDUNYA] {grade}")

    soup = get_soup(base_url)
    if not soup:
        return

    for link in soup.find_all("a", href=True):
        sub_url = urljoin(base_url, link["href"])

        sub_soup = get_soup(sub_url)
        if not sub_soup:
            continue

        time.sleep(1)  # prevent blocking

        for a in sub_soup.find_all("a", href=True):
            pdf = urljoin(sub_url, a["href"])

            if ".pdf" not in pdf:
                continue

            year = extract_year(pdf)
            subject = a.text.strip() or "Unknown"
            board = "Other Board"

            if not year:
                continue

            path = os.path.join(
                BASE_DIR, grade, board, subject, f"{year}.pdf"
            )

            if not os.path.exists(path):
                save_file(pdf, path)

if __name__ == "__main__":
    run("https://www.ilmkidunya.com/past_papers/12th-past-papers.aspx", "Grade12")

import os
from urllib.parse import urljoin
from utils_scraper import get_soup, extract_year, detect_subject, detect_board, save_file

BASE_DIR = "data/past_papers"

def run(base_url, grade):
    soup = get_soup(base_url)

    for link in soup.find_all("a", href=True):
        sub_url = urljoin(base_url, link["href"])

        try:
            sub_page = get_soup(sub_url)

            for a in sub_page.find_all("a", href=True):
                href = urljoin(sub_url, a["href"])

                if ".pdf" not in href:
                    continue

                board = detect_board(href)
                subject = detect_subject(href)
                year = extract_year(href)

                if not board or not subject or not year:
                    continue

                path = os.path.join(
                    BASE_DIR, grade, board, subject, f"{year}.pdf"
                )

                if not os.path.exists(path):
                    save_file(href, path)

        except:
            continue


if __name__ == "__main__":
    run("https://www.ilmkidunya.com/past_papers/12th-past-papers.aspx", "Grade12")

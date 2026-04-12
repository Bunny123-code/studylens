# run_fbise_scraper.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from scraper import Scraper


FBISE_SOURCES = {
    "fbise_class9": "https://fbisepastpapers.com/class-9-fbise-past-papers/",
    "fbise_class10": "https://fbisepastpapers.com/class-10-fbise-past-papers/",
    "fbise_class11": "https://fbisepastpapers.com/class-11-fbise-past-papers/",
    "fbise_class12": "https://fbisepastpapers.com/class-12-fbise-past-papers/",
}

if __name__ == "__main__":
    scraper = Scraper(raw_dir="data/raw", delay=2.0)
    for name, url in FBISE_SOURCES.items():
        scraper.scrape_source(name, url)

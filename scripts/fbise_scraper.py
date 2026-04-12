# scripts/fbise_scraper.py
import logging
import sys
from pathlib import Path

# Adjust sys.path to include parent directory (so data/raw works correctly)
sys.path.insert(0, str(Path(__file__).parent.parent))

from scraper import Scraper

# Configure logging to see output
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("FBISE_Scraper")

FBISE_SOURCES = {
    "fbise_class9": "https://fbisepastpapers.com/class-9-fbise-past-papers/",
    "fbise_class10": "https://fbisepastpapers.com/class-10-fbise-past-papers/",
    "fbise_class11": "https://fbisepastpapers.com/class-11-fbise-past-papers/",
    "fbise_class12": "https://fbisepastpapers.com/class-12-fbise-past-papers/",
}

if __name__ == "__main__":
    logger.info("Starting FBISE scraper...")
    scraper = Scraper(raw_dir="data/raw", delay=2.0)
    for name, url in FBISE_SOURCES.items():
        logger.info(f"Scraping {name}: {url}")
        scraper.scrape_source(name, url)
    logger.info("FBISE scraper finished.")

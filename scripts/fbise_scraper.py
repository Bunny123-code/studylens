#!/usr/bin/env python3
"""
FBISE Past Papers Scraper
Can be run from inside scripts/ or from root.
"""
import logging
import sys
from pathlib import Path

# Add parent directory to path so imports work from anywhere
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.scraper import Scraper

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
    # Ensure raw_dir is relative to project root
    raw_dir = Path(__file__).parent.parent / "data" / "raw"
    logger.info("Starting FBISE scraper...")
    scraper = Scraper(raw_dir=str(raw_dir), delay=2.0)
    for name, url in FBISE_SOURCES.items():
        logger.info(f"Scraping {name}: {url}")
        scraper.scrape_source(name, url)
    logger.info("FBISE scraper finished.")

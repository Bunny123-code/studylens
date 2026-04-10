import logging
import sys
from pathlib import Path

from scraper import Scraper
from processor import FileProcessor
from classifier import Classifier
from organizer import Organizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("StudyLens")

# Define all source URLs as per requirement
SOURCES = {
    "fbise_class9": "https://fbisepastpapers.com/class-9-fbise-past-papers/",
    "fbise_class10": "https://fbisepastpapers.com/class-10-fbise-past-papers/",
    "fbise_class11": "https://fbisepastpapers.com/class-11-fbise-past-papers/",
    "fbise_class12": "https://fbisepastpapers.com/class-12-fbise-past-papers/",
    "multan_class9": "https://web.bisemultan.edu.pk/past-papers-9th/",
    "multan_class10": "https://web.bisemultan.edu.pk/past-papers-10th/",
    "multan_class11": "https://web.bisemultan.edu.pk/past-papers-part-i/",
    "multan_class12": "https://web.bisemultan.edu.pk/past-papers-part-ii/",
    "ilmkidunya_9": "https://www.ilmkidunya.com/past_papers/9th-past-papers.aspx",
    "ilmkidunya_10": "https://www.ilmkidunya.com/past_papers/10th-past-papers.aspx",
    "ilmkidunya_11": "https://www.ilmkidunya.com/past_papers/11th-past-papers.aspx",
    "ilmkidunya_12": "https://www.ilmkidunya.com/past_papers/12th-past-papers.aspx",
}

def main():
    # Step 1: Scrape raw files
    scraper = Scraper(raw_dir="data/raw", delay=2.0)
    scraper.run_all(SOURCES)

    # Step 2: Process, classify, and organize each file
    processor = FileProcessor()
    classifier = Classifier()
    organizer = Organizer(base_dir="data/past_papers")

    raw_dir = Path("data/raw")
    all_files = list(raw_dir.glob("**/*"))
    logger.info(f"Found {len(all_files)} raw files to process.")

    for file_path in all_files:
        if not file_path.is_file():
            continue
        logger.info(f"Processing {file_path}")
        text, file_type = processor.process_file(file_path)

        if not text:
            logger.warning(f"No text extracted from {file_path}, skipping.")
            continue

        classification = classifier.classify(text)
        if not classification:
            logger.warning(f"Classification failed for {file_path}, skipping.")
            continue

        # Log classification result
        logger.info(f"Classified as: Grade={classification['grade']}, Board={classification['board']}, "
                    f"Subject={classification['subject']}, Year={classification['year']}")

        # Organize into final structure
        organizer.organize(file_path, text, classification)

    logger.info("Pipeline completed successfully.")

if __name__ == "__main__":
    main()

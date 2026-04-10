import os
import time
import hashlib
import logging
from urllib.parse import urljoin, urlparse
from pathlib import Path

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class Scraper:
    """Crawl listed websites and download all past paper PDFs/images."""

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ...",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 ...",
    ]

    def __init__(self, raw_dir="data/raw", delay=1.5, max_retries=3):
        self.raw_dir = Path(raw_dir)
        self.delay = delay
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.USER_AGENTS[0]})
        self.downloaded_hashes = set()

    def _get_soup(self, url):
        for attempt in range(self.max_retries):
            try:
                resp = self.session.get(url, timeout=30)
                resp.raise_for_status()
                return BeautifulSoup(resp.text, "lxml")
            except Exception as e:
                logger.warning(f"Attempt {attempt+1} failed for {url}: {e}")
                time.sleep(2 ** attempt)
        logger.error(f"Failed to fetch {url} after {self.max_retries} attempts.")
        return None

    def _extract_links(self, start_url, source_name):
        """Recursively find all PDF/image links from a page."""
        soup = self._get_soup(start_url)
        if not soup:
            return []

        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            full_url = urljoin(start_url, href)

            # Direct file links
            if any(full_url.lower().endswith(ext) for ext in [".pdf", ".jpg", ".jpeg", ".png"]):
                links.append(full_url)
            # Intermediate pages – we must follow them (common on ilmkidunya)
            elif "past_papers" in href or "paper" in href.lower():
                # Avoid infinite loops by checking domain
                if urlparse(full_url).netloc == urlparse(start_url).netloc:
                    logger.debug(f"Following intermediate link: {full_url}")
                    links.extend(self._extract_links(full_url, source_name))

        return list(set(links))  # deduplicate within the same source crawl

    def _download_file(self, url, dest_path):
        """Download file with retries and hash verification."""
        for attempt in range(self.max_retries):
            try:
                resp = self.session.get(url, stream=True, timeout=45)
                resp.raise_for_status()

                # Check content type to avoid downloading HTML error pages
                content_type = resp.headers.get("content-type", "").lower()
                if "html" in content_type and not url.lower().endswith(".pdf"):
                    logger.warning(f"Skipping non-binary response from {url}")
                    return None

                # Compute hash while writing to avoid duplicate downloads
                hasher = hashlib.sha256()
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                with open(dest_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            hasher.update(chunk)

                file_hash = hasher.hexdigest()
                if file_hash in self.downloaded_hashes:
                    logger.info(f"Duplicate file skipped: {url}")
                    os.remove(dest_path)
                    return None
                self.downloaded_hashes.add(file_hash)
                return dest_path

            except Exception as e:
                logger.warning(f"Download attempt {attempt+1} failed for {url}: {e}")
                time.sleep(2 ** attempt)

        logger.error(f"Failed to download {url}")
        return None

    def scrape_source(self, source_name, start_url):
        """Crawl one source website and save all discovered files."""
        logger.info(f"Starting scrape of {source_name} from {start_url}")
        file_urls = self._extract_links(start_url, source_name)
        logger.info(f"Found {len(file_urls)} potential files.")

        source_raw_dir = self.raw_dir / source_name
        source_raw_dir.mkdir(parents=True, exist_ok=True)

        downloaded = 0
        for url in file_urls:
            # Generate a safe filename from the URL
            parsed = urlparse(url)
            filename = os.path.basename(parsed.path)
            if not filename or "." not in filename:
                filename = f"{hashlib.md5(url.encode()).hexdigest()}.pdf"
            dest = source_raw_dir / filename

            if dest.exists():
                logger.debug(f"File already exists: {dest}")
                continue

            result = self._download_file(url, dest)
            if result:
                downloaded += 1
                logger.info(f"Downloaded: {result.name}")
            time.sleep(self.delay)  # be polite

        logger.info(f"Completed {source_name}: {downloaded} new files downloaded.")
        return downloaded

    def run_all(self, sources_dict):
        """Run scraping for all given sources."""
        total = 0
        for name, url in sources_dict.items():
            total += self.scrape_source(name, url)
        logger.info(f"Scraping finished. Total new files: {total}")

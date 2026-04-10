import os
import time
import hashlib
import logging
from urllib.parse import urljoin, urlparse
from pathlib import Path
from collections import deque

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class Scraper:
    """Crawl listed websites and download all past paper PDFs/images."""

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    ]

    # Keywords that indicate a link should be followed
    FOLLOW_KEYWORDS = ["past-paper", "past_paper", "paper", "202", "201", "2020", "2021", "2022", "2023", "2024", "2025"]
    # Keywords to avoid following
    AVOID_KEYWORDS = ["guess", "note", "book", "syllabus", "date-sheet", "result", "roll-no"]

    def __init__(self, raw_dir="data/raw", delay=1.5, max_retries=3, max_depth=1):
        self.raw_dir = Path(raw_dir)
        self.delay = delay
        self.max_retries = max_retries
        self.max_depth = max_depth
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

    def _should_follow_link(self, url: str, base_domain: str) -> bool:
        """Decide whether to follow a link for further crawling."""
        parsed = urlparse(url)
        # Only follow links on same domain
        if parsed.netloc and parsed.netloc != base_domain:
            return False
        # Avoid non-http schemes
        if parsed.scheme not in ("http", "https"):
            return False
        # Avoid known non-paper sections
        url_lower = url.lower()
        for avoid in self.AVOID_KEYWORDS:
            if avoid in url_lower:
                return False
        # Must contain at least one follow keyword or a year pattern
        for kw in self.FOLLOW_KEYWORDS:
            if kw in url_lower:
                return True
        return False

    def _extract_links(self, start_url: str) -> list:
        """
        Crawl using BFS up to max_depth to find all PDF/image links.
        Returns list of direct file URLs.
        """
        start_domain = urlparse(start_url).netloc
        visited = set()
        queue = deque()
        queue.append((start_url, 0))
        file_urls = []

        while queue:
            url, depth = queue.popleft()
            if url in visited:
                continue
            visited.add(url)

            logger.debug(f"Crawling depth {depth}: {url}")
            soup = self._get_soup(url)
            if not soup:
                continue

            # Find direct file links
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                full_url = urljoin(url, href)
                full_lower = full_url.lower()

                # Direct file links
                if any(full_lower.endswith(ext) for ext in [".pdf", ".jpg", ".jpeg", ".png"]):
                    if full_url not in file_urls:
                        file_urls.append(full_url)
                # Intermediate pages: follow if within depth limit and criteria met
                elif depth < self.max_depth and self._should_follow_link(full_url, start_domain):
                    if full_url not in visited:
                        queue.append((full_url, depth + 1))

            time.sleep(0.5)  # small delay between page fetches

        return file_urls

    def _download_file(self, url, dest_path):
        """Download file with retries and hash verification."""
        for attempt in range(self.max_retries):
            try:
                resp = self.session.get(url, stream=True, timeout=45)
                resp.raise_for_status()

                content_type = resp.headers.get("content-type", "").lower()
                if "html" in content_type and not url.lower().endswith(".pdf"):
                    logger.warning(f"Skipping non-binary response from {url}")
                    return None

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
        file_urls = self._extract_links(start_url)
        logger.info(f"Found {len(file_urls)} potential files.")

        source_raw_dir = self.raw_dir / source_name
        source_raw_dir.mkdir(parents=True, exist_ok=True)

        downloaded = 0
        for url in file_urls:
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
            time.sleep(self.delay)

        logger.info(f"Completed {source_name}: {downloaded} new files downloaded.")
        return downloaded

    def run_all(self, sources_dict):
        """Run scraping for all given sources."""
        total = 0
        for name, url in sources_dict.items():
            total += self.scrape_source(name, url)
        logger.info(f"Scraping finished. Total new files: {total}")

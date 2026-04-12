import os
import time
import hashlib
import logging
import re
import random
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
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    ]

    # Keywords to avoid following (prevents recursion into notes, books, etc.)
    AVOID_KEYWORDS = [
        "guess", "note", "book", "syllabus", "date-sheet", "result",
        "roll-no", "practical", "fbise-books", "fbise-notes"
    ]

    def __init__(self, raw_dir="data/raw", delay=1.5, max_retries=3, max_depth=1):
        self.raw_dir = Path(raw_dir)
        self.delay = delay
        self.max_retries = max_retries
        self.max_depth = max_depth
        self.session = requests.Session()
        # Rotate User-Agent
        self.session.headers.update({
            "User-Agent": random.choice(self.USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        })

    def _get_soup(self, url):
        """Fetch URL and return BeautifulSoup object with retries."""
        for attempt in range(self.max_retries):
            try:
                # Random delay before request
                time.sleep(random.uniform(1.0, 2.0))
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
        # Must contain "past" or "paper" or a year pattern
        if "past" in url_lower or "paper" in url_lower or re.search(r'20[12]\d', url_lower):
            return True
        return False

    def _extract_links_fbise(self, start_url: str) -> list:
        """
        Crawl FBISE site: class page -> subject pages -> PDF links.
        Improved to use more robust selectors and handle New/Old syllabus.
        """
        soup = self._get_soup(start_url)
        if not soup:
            logger.error(f"Could not fetch FBISE class page: {start_url}")
            return []

        file_urls = []
        subject_links = []

        # Find all subject links on the class page.
        # They are typically inside <div class="entry-content"> and have "fbise-past-papers" in href.
        content_div = soup.find("div", class_="entry-content")
        if content_div:
            for a in content_div.find_all("a", href=True):
                href = a["href"]
                if "fbise-past-papers" in href and "/class-" in href:
                    full_url = urljoin(start_url, href)
                    subject_links.append(full_url)
        else:
            # Fallback: search whole page
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "fbise-past-papers" in href and "/class-" in href:
                    full_url = urljoin(start_url, href)
                    subject_links.append(full_url)

        # Remove duplicates while preserving order
        subject_links = list(dict.fromkeys(subject_links))
        logger.info(f"Found {len(subject_links)} subject links on {start_url}")

        # Visit each subject page and extract PDF links
        for subj_url in subject_links:
            logger.debug(f"Visiting subject page: {subj_url}")
            sub_soup = self._get_soup(subj_url)
            if not sub_soup:
                continue

            # Find all PDF links on the subject page.
            # Sometimes PDFs are inside <a> tags, sometimes in <div class="wp-block-file">.
            pdf_links = []
            # Direct <a> tags with .pdf
            for a in sub_soup.find_all("a", href=True):
                href = a["href"]
                if href.lower().endswith(".pdf"):
                    pdf_links.append(href)
            # Also check for links inside .wp-block-file (common in newer WordPress)
            for file_block in sub_soup.select(".wp-block-file a"):
                href = file_block.get("href")
                if href and href.lower().endswith(".pdf"):
                    pdf_links.append(href)

            # Convert to absolute URLs and add to master list
            for pdf_link in pdf_links:
                full_pdf_url = urljoin(subj_url, pdf_link)
                file_urls.append(full_pdf_url)

            # Polite delay between subject pages
            time.sleep(random.uniform(1.0, 2.0))

        logger.info(f"Total PDF links found from FBISE: {len(file_urls)}")
        return list(set(file_urls))

    def _extract_links_multan(self, start_url: str) -> list:
        """
        Parse Multan Board pages with download tables.
        Improved to also find ZIP files and direct PDFs.
        """
        soup = self._get_soup(start_url)
        if not soup:
            return []
        file_urls = []

        # Find all tables with past papers (class may vary)
        tables = soup.select("table.table-striped, table.past-papers")
        for table in tables:
            for a in table.find_all("a", href=True):
                href = a["href"]
                if href.lower().endswith(('.pdf', '.zip')):
                    pdf_url = urljoin(start_url, href)
                    file_urls.append(pdf_url)

        # If no tables found, fallback to all PDF/ZIP links on page
        if not file_urls:
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if href.lower().endswith(('.pdf', '.zip')):
                    pdf_url = urljoin(start_url, href)
                    file_urls.append(pdf_url)

        return list(set(file_urls))

    def _extract_links_ilmkidunya(self, start_url: str) -> list:
        """
        Handle ilmkidunya with extra care (cookies, headers).
        Note: This site may block requests; use headless browser if needed.
        """
        soup = self._get_soup(start_url)
        if not soup:
            logger.error(f"Could not fetch ilmkidunya page: {start_url}")
            return []
        file_urls = []

        # Find all links to detail pages (e.g., /past_papers/9th-class/...)
        detail_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            full_url = urljoin(start_url, href)
            if "past_papers" in full_url and any(x in full_url for x in ["9th", "10th", "11th", "12th"]):
                detail_links.append(full_url)

        # Visit each detail page and find download link
        for detail_url in detail_links:
            logger.debug(f"Visiting detail page: {detail_url}")
            detail_soup = self._get_soup(detail_url)
            if not detail_soup:
                continue
            # Look for download button/link
            for a in detail_soup.find_all("a", href=True):
                href = a["href"]
                if href.lower().endswith(".pdf"):
                    pdf_url = urljoin(detail_url, href)
                    file_urls.append(pdf_url)
                # Sometimes the link text indicates download
                if "download" in a.get_text().lower() or "click here" in a.get_text().lower():
                    pdf_url = urljoin(detail_url, href)
                    if pdf_url.lower().endswith(".pdf"):
                        file_urls.append(pdf_url)
            time.sleep(random.uniform(0.5, 1.5))

        return list(set(file_urls))

    def _extract_links(self, start_url: str, source_name: str) -> list:
        """Dispatch to appropriate parser based on domain."""
        domain = urlparse(start_url).netloc

        if "fbisepastpapers.com" in domain:
            return self._extract_links_fbise(start_url)
        elif "bisemultan.edu.pk" in domain:
            return self._extract_links_multan(start_url)
        elif "ilmkidunya.com" in domain:
            return self._extract_links_ilmkidunya(start_url)
        else:
            # Generic fallback: BFS crawl up to max_depth
            visited = set()
            queue = deque()
            queue.append((start_url, 0))
            file_urls = []

            while queue:
                url, depth = queue.popleft()
                if url in visited:
                    continue
                visited.add(url)

                soup = self._get_soup(url)
                if not soup:
                    continue

                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    full_url = urljoin(url, href)

                    if any(full_url.lower().endswith(ext) for ext in [".pdf", ".jpg", ".jpeg", ".png", ".zip"]):
                        file_urls.append(full_url)
                    elif depth < self.max_depth and self._should_follow_link(full_url, domain):
                        queue.append((full_url, depth + 1))

                time.sleep(random.uniform(0.5, 1.0))

            return list(set(file_urls))

    def _download_file(self, url, dest_path, source_hashes):
        """Download file with retries and source-specific hash verification."""
        for attempt in range(self.max_retries):
            try:
                resp = self.session.get(url, stream=True, timeout=45)
                resp.raise_for_status()

                content_type = resp.headers.get("content-type", "").lower()
                # If content is HTML, it might be an error page; skip
                if "html" in content_type and not url.lower().endswith(('.pdf', '.zip')):
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
                if file_hash in source_hashes:
                    logger.info(f"Duplicate within source skipped: {url}")
                    os.remove(dest_path)
                    return None

                source_hashes.add(file_hash)
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
        source_hashes = set()  # Hash set per source to avoid false duplicates

        for url in file_urls:
            parsed = urlparse(url)
            filename = os.path.basename(parsed.path)
            if not filename or "." not in filename:
                filename = f"{hashlib.md5(url.encode()).hexdigest()}.pdf"
            dest = source_raw_dir / filename

            if dest.exists():
                logger.debug(f"File already exists: {dest}")
                continue

            result = self._download_file(url, dest, source_hashes)
            if result:
                downloaded += 1
                logger.info(f"Downloaded: {result.name}")

            time.sleep(self.delay + random.uniform(-0.5, 0.5))

        logger.info(f"Completed {source_name}: {downloaded} new files downloaded.")
        return downloaded

    def run_all(self, sources_dict):
        """Run scraping for all given sources."""
        total = 0
        for name, url in sources_dict.items():
            total += self.scrape_source(name, url)
        logger.info(f"Scraping finished. Total new files: {total}")

"""
High-Speed Asynchronous Asset Crawler and Deep Path Localizer.
Mirrors all static assets (HTML, CSS, JS, Images, Fonts) and rewrites all links
to relative local directory paths for complete offline functionality.
"""

import asyncio
import os
import re
from urllib.parse import urljoin, urlparse, urldefrag
from pathlib import Path
from typing import Dict, Set, List, Callable, Optional, Tuple
import aiohttp
from bs4 import BeautifulSoup

class CrawlerConfig:
    def __init__(
        self,
        start_url: str,
        output_dir: str,
        max_depth: int = 2,
        max_threads: int = 12,
        timeout_seconds: int = 15,
        user_agent: str = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
    ):
        self.start_url = start_url
        self.output_dir = output_dir
        self.max_depth = max_depth
        self.max_threads = max_threads
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent


class CrawlResult:
    def __init__(self):
        self.success: bool = False
        self.error_message: str = ""
        self.total_downloaded: int = 0
        self.total_bytes: int = 0
        self.downloaded_assets: List[Dict[str, str]] = []
        self.discovered_endpoints: List[str] = []
        self.html_files: List[str] = []


class AsyncCrawler:
    def __init__(self, config: CrawlerConfig):
        self.config = config
        self.parsed_start = urlparse(config.start_url)
        self.base_domain = self.parsed_start.netloc
        self.output_path = Path(config.output_dir)
        
        # State tracking
        self.visited_urls: Set[str] = set()
        self.url_to_local_rel: Dict[str, str] = {}
        self.url_to_local_abs: Dict[str, Path] = {}
        self.discovered_endpoints: Set[str] = set()
        self.html_pages_content: Dict[str, str] = {}  # local_rel -> html content
        
        # Callbacks
        self.log_callback: Optional[Callable[[str, str], None]] = None
        self.progress_callback: Optional[Callable[[int, int, str], None]] = None
        
        self.is_stopped = False
        self.total_tasks_queued = 0
        self.tasks_completed = 0

    def log(self, level: str, message: str):
        if self.log_callback:
            self.log_callback(level, message)
        else:
            print(f"[{level}] {message}")

    def progress(self, current: int, total: int, item: str):
        if self.progress_callback:
            self.progress_callback(current, total, item)

    def stop(self):
        self.is_stopped = True

    def _sanitize_path(self, url: str) -> str:
        """Determines a safe relative filesystem path for an asset URL."""
        parsed = urlparse(url)
        clean_path = parsed.path.lstrip("/")
        
        # If root or directory
        if not clean_path or clean_path.endswith("/"):
            clean_path = clean_path + "index.html"
            
        # Extension handling
        _, ext = os.path.splitext(clean_path)
        if not ext:
            clean_path = clean_path + ".html"
            
        # Clean illegal characters for Windows/POSIX
        clean_path = re.sub(r'[<>:"|?*]', '_', clean_path)
        
        # If from external CDN, organize into cdn_assets/
        if parsed.netloc and parsed.netloc != self.base_domain:
            safe_domain = re.sub(r'[<>:"|?*]', '_', parsed.netloc)
            clean_path = os.path.join("external_assets", safe_domain, clean_path)
            
        return clean_path

    async def run(self) -> CrawlResult:
        result = CrawlResult()
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        headers = {
            "User-Agent": self.config.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        
        timeout = aiohttp.ClientTimeout(total=self.config.timeout_seconds)
        conn = aiohttp.TCPConnector(limit=self.config.max_threads, ssl=False)
        
        self.log("INFO", f"Initializing high-speed crawl of: {self.config.start_url}")
        self.log("INFO", f"Target destination: {self.config.output_dir}")

        queue = asyncio.Queue()
        await queue.put((self.config.start_url, 0))
        self.visited_urls.add(self.config.start_url)
        self.total_tasks_queued = 1

        async with aiohttp.ClientSession(headers=headers, timeout=timeout, connector=conn) as session:
            # Worker pool
            workers = []
            for i in range(self.config.max_threads):
                w = asyncio.create_task(self._worker(i, queue, session))
                workers.append(w)

            # Wait until queue is completely processed
            await queue.join()

            # Stop workers
            for w in workers:
                w.cancel()
            await asyncio.gather(*workers, return_exceptions=True)

        if self.is_stopped:
            self.log("WARN", "Crawl stopped by user.")
            result.error_message = "Stopped by user"
            return result

        # Pass 2: Deep Path Localization on all saved HTML & CSS files
        self.log("INFO", "Running Deep Path Localizer to make web assets 100% offline...")
        await self._localize_all_saved_files()

        result.success = True
        result.total_downloaded = len(self.url_to_local_rel)
        result.discovered_endpoints = sorted(list(self.discovered_endpoints))
        result.html_files = list(self.html_pages_content.keys())
        for orig, rel in self.url_to_local_rel.items():
            result.downloaded_assets.append({
                "original_url": orig,
                "local_path": rel
            })
            
        self.log("SUCCESS", f"Finished! Downloaded {result.total_downloaded} assets, discovered {len(result.discovered_endpoints)} potential API endpoints.")
        return result

    async def _worker(self, worker_id: int, queue: asyncio.Queue, session: aiohttp.ClientSession):
        while not self.is_stopped:
            try:
                url, depth = await queue.get()
            except asyncio.CancelledError:
                break

            try:
                await self._fetch_and_process(url, depth, queue, session)
            except Exception as e:
                self.log("ERROR", f"Error fetching {url}: {e}")
            finally:
                self.tasks_completed += 1
                self.progress(self.tasks_completed, self.total_tasks_queued, url)
                queue.task_done()

    async def _fetch_and_process(
        self,
        url: str,
        depth: int,
        queue: asyncio.Queue,
        session: aiohttp.ClientSession
    ):
        rel_path = self._sanitize_path(url)
        local_file_path = self.output_path / rel_path

        # Cache mapping
        self.url_to_local_rel[url] = rel_path
        self.url_to_local_abs[url] = local_file_path

        try:
            async with session.get(url, allow_redirects=True) as resp:
                if resp.status >= 400:
                    self.log("WARN", f"HTTP {resp.status} for {url}")
                    return

                content_type = resp.headers.get("Content-Type", "").lower()
                content = await resp.read()

                # Ensure parent directory exists
                local_file_path.parent.mkdir(parents=True, exist_ok=True)

                is_html = "text/html" in content_type or rel_path.endswith(".html")
                is_css = "text/css" in content_type or rel_path.endswith(".css")
                is_js = "javascript" in content_type or rel_path.endswith(".js")

                # Save raw content first
                local_file_path.write_bytes(content)

                if is_html:
                    try:
                        text_content = content.decode("utf-8", errors="replace")
                        self.html_pages_content[rel_path] = text_content
                        # Extract child links & endpoints
                        await self._extract_links_from_html(url, text_content, depth, queue)
                    except Exception as err:
                        self.log("WARN", f"Error parsing HTML from {url}: {err}")

                elif is_css:
                    try:
                        css_text = content.decode("utf-8", errors="replace")
                        await self._extract_assets_from_css(url, css_text, queue)
                    except Exception as err:
                        self.log("WARN", f"Error parsing CSS from {url}: {err}")

                elif is_js:
                    try:
                        js_text = content.decode("utf-8", errors="replace")
                        self._detect_endpoints_in_js(js_text)
                    except Exception as err:
                        self.log("WARN", f"Error parsing JS from {url}: {err}")

        except Exception as e:
            self.log("ERROR", f"Failed downloading {url}: {e}")

    async def _extract_links_from_html(
        self,
        base_url: str,
        html_text: str,
        depth: int,
        queue: asyncio.Queue
    ):
        soup = BeautifulSoup(html_text, "html.parser")

        # 1. Inspect forms
        for form in soup.find_all("form"):
            action = form.get("action", "")
            if action:
                full_endpoint = urljoin(base_url, action)
                self.discovered_endpoints.add(full_endpoint)

        # 2. Extract asset tags: link, script, img, source, video, audio
        asset_urls = []
        for tag in soup.find_all(["link", "script", "img", "source", "video", "audio"]):
            for attr in ["src", "href", "data-src", "poster"]:
                val = tag.get(attr)
                if val and not val.startswith("data:") and not val.startswith("javascript:"):
                    asset_urls.append(urljoin(base_url, val))

        # 3. Extract CSS style backgrounds
        for tag in soup.find_all(style=True):
            style = tag.get("style", "")
            matches = re.findall(r'url\(\s*[\'"]?([^\'")]+)[\'"]?\s*\)', style, re.I)
            for m in matches:
                if not m.startswith("data:"):
                    asset_urls.append(urljoin(base_url, m))

        # 4. Extract child pages if depth < max_depth (same domain only)
        if depth < self.config.max_depth:
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if href and not href.startswith("#") and not href.startswith("mailto:") and not href.startswith("tel:") and not href.startswith("javascript:"):
                    resolved = urljoin(base_url, href)
                    resolved, _ = urldefrag(resolved)
                    parsed_link = urlparse(resolved)
                    if parsed_link.netloc == self.base_domain:
                        if resolved not in self.visited_urls:
                            self.visited_urls.add(resolved)
                            self.total_tasks_queued += 1
                            await queue.put((resolved, depth + 1))

        # Queue discovered assets
        for a_url in asset_urls:
            clean_url, _ = urldefrag(a_url)
            if clean_url not in self.visited_urls:
                self.visited_urls.add(clean_url)
                self.total_tasks_queued += 1
                await queue.put((clean_url, depth + 1))

        # Extract JS fetch/AJAX calls from inline scripts
        for script in soup.find_all("script"):
            if script.string:
                self._detect_endpoints_in_js(script.string)

    async def _extract_assets_from_css(self, base_url: str, css_text: str, queue: asyncio.Queue):
        matches = re.findall(r'url\(\s*[\'"]?([^\'")]+)[\'"]?\s*\)', css_text, re.I)
        for m in matches:
            m = m.strip()
            if m and not m.startswith("data:"):
                full_asset = urljoin(base_url, m)
                clean_url, _ = urldefrag(full_asset)
                if clean_url not in self.visited_urls:
                    self.visited_urls.add(clean_url)
                    self.total_tasks_queued += 1
                    await queue.put((clean_url, 99))  # Asset leaf node

    def _detect_endpoints_in_js(self, js_code: str):
        # Scan for fetch, axios, $.ajax endpoints
        patterns = [
            r'(?:fetch|axios\.(?:get|post|put|delete|patch)|\$\.(?:ajax|get|post))\s*\(\s*[\'"`]([^\'"`]+)[\'"`]',
            r'url\s*:\s*[\'"`]([^\'"`]+)[\'"`]',
            r'[\'"`](/api/[^\'"`]+)[\'"`]',
            r'[\'"`](/v1/[^\'"`]+)[\'"`]',
            r'[\'"`](/auth/[^\'"`]+)[\'"`]'
        ]
        for pat in patterns:
            for match in re.findall(pat, js_code):
                if match and not match.endswith(".js") and not match.endswith(".css"):
                    self.discovered_endpoints.add(match)

    async def _localize_all_saved_files(self):
        """Pass 2: Replace absolute / external links with relative local paths."""
        for root, _, files in os.walk(self.output_path):
            for file in files:
                file_path = Path(root) / file
                rel_from_root = file_path.relative_to(self.output_path).as_posix()
                ext = file_path.suffix.lower()

                if ext in [".html", ".htm"]:
                    self._localize_html_file(file_path, rel_from_root)
                elif ext == ".css":
                    self._localize_css_file(file_path, rel_from_root)

    def _calculate_relative_link(self, current_file_rel: str, target_asset_rel: str) -> str:
        """Calculates the correct relative path (e.g., ../assets/app.js) between two files."""
        current_dir = os.path.dirname(current_file_rel)
        rel = os.path.relpath(target_asset_rel, current_dir).replace("\\", "/")
        return rel

    def _localize_html_file(self, file_path: Path, current_rel: str):
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            soup = BeautifulSoup(content, "html.parser")

            # Localize tag attributes
            for tag in soup.find_all(True):
                for attr in ["src", "href", "data-src", "poster"]:
                    val = tag.get(attr)
                    if not val or val.startswith("data:") or val.startswith("javascript:") or val.startswith("#"):
                        continue
                    
                    # Check if mapped
                    for orig_url, local_rel in self.url_to_local_rel.items():
                        if val == orig_url or val.rstrip("/") == orig_url.rstrip("/") or (val.startswith("/") and orig_url.endswith(val)):
                            relative_link = self._calculate_relative_link(current_rel, local_rel)
                            tag[attr] = relative_link
                            break

            # Localize inline styles
            for tag in soup.find_all(style=True):
                style = tag["style"]
                for orig_url, local_rel in self.url_to_local_rel.items():
                    if orig_url in style:
                        relative_link = self._calculate_relative_link(current_rel, local_rel)
                        style = style.replace(orig_url, relative_link)
                tag["style"] = style

            file_path.write_text(str(soup), encoding="utf-8")
        except Exception as e:
            self.log("WARN", f"Failed localizing HTML {file_path}: {e}")

    def _localize_css_file(self, file_path: Path, current_rel: str):
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            for orig_url, local_rel in self.url_to_local_rel.items():
                if orig_url in content:
                    relative_link = self._calculate_relative_link(current_rel, local_rel)
                    content = content.replace(orig_url, relative_link)
            file_path.write_text(content, encoding="utf-8")
        except Exception as e:
            self.log("WARN", f"Failed localizing CSS {file_path}: {e}")


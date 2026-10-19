"""
Crawler Bridge: Transparently switches between the C++ Hardware Performance Layer
(via pybind11) and the high-speed Python AsyncCrawler fallback.
"""

import asyncio
from typing import Callable, Optional
from pathlib import Path
from .python_crawler import CrawlerConfig, CrawlResult, AsyncCrawler

# Attempt to import compiled C++ pybind11 module
CPP_AVAILABLE = False
cpp_crawler = None

try:
    import cpp_crawler
    CPP_AVAILABLE = True
except ImportError:
    # Check parent and local directory for compiled .pyd / .so
    import sys
    sys.path.append(str(Path(__file__).parent.parent))
    try:
        import cpp_crawler
        CPP_AVAILABLE = True
    except ImportError:
        CPP_AVAILABLE = False


class UnifiedCrawler:
    def __init__(self, config: CrawlerConfig):
        self.config = config
        self.log_callback: Optional[Callable[[str, str], None]] = None
        self.progress_callback: Optional[Callable[[int, int, str], None]] = None
        self.cpp_crawler_instance = None
        self.async_crawler_instance = None

    def set_callbacks(
        self,
        log_cb: Optional[Callable[[str, str], None]] = None,
        prog_cb: Optional[Callable[[int, int, str], None]] = None
    ):
        self.log_callback = log_cb
        self.progress_callback = prog_cb

    def is_cpp_accelerated(self) -> bool:
        return CPP_AVAILABLE

    def run(self) -> CrawlResult:
        """Synchronous runner compatible with GUI thread or CLI."""
        if CPP_AVAILABLE and cpp_crawler is not None:
            if self.log_callback:
                self.log_callback("INFO", "🚀 Activating C++ Native Accelerated Scraping Core (pybind11)!")
            try:
                cpp_cfg = cpp_crawler.CrawlerConfig()
                cpp_cfg.start_url = self.config.start_url
                cpp_cfg.output_dir = self.config.output_dir
                cpp_cfg.max_depth = self.config.max_depth
                cpp_cfg.max_threads = self.config.max_threads
                cpp_cfg.timeout_seconds = self.config.timeout_seconds
                cpp_cfg.user_agent = self.config.user_agent

                self.cpp_crawler_instance = cpp_crawler.Crawler(cpp_cfg)
                if self.log_callback:
                    self.cpp_crawler_instance.set_log_callback(self.log_callback)
                if self.progress_callback:
                    self.cpp_crawler_instance.set_progress_callback(self.progress_callback)

                res = self.cpp_crawler_instance.start()
                
                # Wrap C++ result into python CrawlResult
                py_res = CrawlResult()
                py_res.success = res.success
                py_res.error_message = res.error_message
                py_res.total_downloaded = res.total_downloaded
                py_res.total_bytes = res.total_bytes
                py_res.discovered_endpoints = res.discovered_endpoints
                return py_res
            except Exception as e:
                if self.log_callback:
                    self.log_callback("WARN", f"C++ Core encountered an exception: {e}. Falling back to Python Async engine.")
        
        # Fallback to Python AsyncCrawler
        if self.log_callback:
            self.log_callback("INFO", "⚡ Executing High-Speed Python AsyncIO/AIOHTTP Engine...")
        
        self.async_crawler_instance = AsyncCrawler(self.config)
        self.async_crawler_instance.log_callback = self.log_callback
        self.async_crawler_instance.progress_callback = self.progress_callback
        
        return asyncio.run(self.async_crawler_instance.run())

    def stop(self):
        if self.cpp_crawler_instance:
            self.cpp_crawler_instance.stop()
        if self.async_crawler_instance:
            self.async_crawler_instance.stop()


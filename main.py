"""
AI-Powered Full-Stack Website Cloner & Code Generator
Entry point supporting both Desktop GUI mode and Headless CLI mode.
"""

import argparse
import sys
from pathlib import Path

# Fix Windows console UTF-8 encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def run_cli(args):
    from python_engine.crawler_bridge import UnifiedCrawler, CrawlerConfig
    from python_engine.ast_analyzer import ASTAnalyzer
    from python_engine.ai_generator import AIGenerator
    from python_engine.bundler import FullStackBundler

    print("=================================================================")
    print("🚀 AI-Powered Full-Stack Website Cloner (Python + C++)")
    print(f"Target URL: {args.url}")
    print(f"Destination: {args.output}")
    print(f"Backend Target: {args.framework}")
    print(f"AI Provider: {args.provider}")
    print("=================================================================\n")

    bundler = FullStackBundler(args.output)
    bundler.prepare_directories()

    # 1. Scrape Assets
    cfg = CrawlerConfig(
        start_url=args.url,
        output_dir=str(bundler.frontend_dir),
        max_depth=args.depth,
        max_threads=args.threads
    )
    crawler = UnifiedCrawler(cfg)
    crawler.set_callbacks(
        log_cb=lambda lvl, msg: print(f"[{lvl}] {msg}"),
        prog_cb=lambda cur, tot, item: print(f"[{cur}/{tot}] {item}")
    )

    print(f"Engine Mode: {'C++ Native Core (pybind11)' if crawler.is_cpp_accelerated() else 'AsyncIO High-Speed Python Engine'}")
    crawl_result = crawler.run()

    if not crawl_result.success:
        print(f"❌ Crawl failed: {crawl_result.error_message}")
        sys.exit(1)

    print(f"\n✅ Crawl Completed. Downloaded {crawl_result.total_downloaded} assets.")

    # 2. Reverse Engineer AST
    print("🔍 Analyzing forms and network requests in frontend assets...")
    analyzer = ASTAnalyzer(str(bundler.frontend_dir))
    analysis = analyzer.analyze()
    print(f"✅ Identified {analysis['total_endpoints']} endpoints and {len(analysis['models'])} data models.")

    # 3. Generate Backend
    print(f"🤖 Generating {args.framework.upper()} backend code...")
    ai = AIGenerator(provider=args.provider, api_key=args.api_key)
    ai.log_callback = lambda lvl, msg: print(f"[{lvl}] {msg}")
    backend_files = ai.generate_backend(analysis, framework=args.framework)

    bundler.write_backend_files(backend_files)
    bundler.create_orchestration_scripts(framework=args.framework)

    # 4. Optional ZIP Export
    if args.export_zip:
        zip_path = bundler.export_zip()
        print(f"📦 Exported Full-Stack ZIP to: {zip_path}")

    print("\n🎉 Full-Stack Project generated successfully!")
    print(f"👉 Location: {Path(args.output).resolve()}")
    print("👉 To run: double click start_fullstack.bat or execute: cd backend && python run_server.py\n")


def main():
    parser = argparse.ArgumentParser(description="AI Full-Stack Website Cloner & Code Generator")
    parser.add_argument("--cli", action="store_true", help="Run in command line mode instead of GUI")
    parser.add_argument("--url", type=str, help="Target website URL to clone")
    parser.add_argument("--output", "-o", type=str, default="./cloned_project", help="Destination folder")
    parser.add_argument("--framework", choices=["fastapi", "drogon"], default="fastapi", help="Target backend API framework")
    parser.add_argument("--provider", choices=["offline", "gemini", "openai"], default="offline", help="AI code generation provider")
    parser.add_argument("--api-key", type=str, default=None, help="API key for Gemini or OpenAI (optional)")
    parser.add_argument("--depth", type=int, default=2, help="Crawl depth")
    parser.add_argument("--threads", type=int, default=12, help="Scraper concurrency threads")
    parser.add_argument("--export-zip", action="store_true", help="Automatically create a full-stack .zip archive")

    args = parser.parse_args()

    if args.cli or args.url:
        if not args.url:
            print("Error: --url is required when running in CLI mode.")
            sys.exit(1)
        run_cli(args)
    else:
        from ui.app_gui import launch_gui
        launch_gui()


if __name__ == "__main__":
    main()

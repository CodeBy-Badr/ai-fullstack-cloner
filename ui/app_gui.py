"""
Modern Desktop GUI for AI-Powered Full-Stack Website Cloner & Code Generator
Built with CustomTkinter.
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

import customtkinter as ctk

from python_engine.crawler_bridge import UnifiedCrawler, CrawlerConfig
from python_engine.ast_analyzer import ASTAnalyzer
from python_engine.ai_generator import AIGenerator
from python_engine.bundler import FullStackBundler


class AppGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Appearance configuration
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("AI-Powered Full-Stack Website Cloner & Generator (Python + C++)")
        self.geometry("980x780")
        self.minsize(850, 680)

        # State variables
        self.crawler_thread = None
        self.active_bundler = None
        self.last_export_zip = None

        self._build_ui()

    def _build_ui(self):
        # Master layout: 2 rows (Header, Content)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # 1. Header Frame
        header = ctk.CTkFrame(self, corner_radius=10, fg_color="#1a1c23")
        header.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            header,
            text="AI-Powered Full-Stack Website Cloner",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title.grid(row=0, column=0, padx=15, pady=(10, 2), sticky="w")

        subtitle = ctk.CTkLabel(
            header,
            text="High-Speed C++ & Python Hybrid Asset Scraper • Path Localizer • AI Backend API Reverse-Engineer",
            font=ctk.CTkFont(size=12),
            text_color="#9da5b4"
        )
        subtitle.grid(row=1, column=0, padx=15, pady=(0, 10), sticky="w")

        # 2. Main Content Frame
        main_content = ctk.CTkFrame(self, corner_radius=10)
        main_content.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        main_content.grid_columnconfigure(0, weight=1)
        main_content.grid_rowconfigure(3, weight=1)

        # Input Form
        form_frame = ctk.CTkFrame(main_content, fg_color="transparent")
        form_frame.grid(row=0, column=0, padx=15, pady=15, sticky="ew")
        form_frame.grid_columnconfigure(1, weight=1)

        # Target URL
        ctk.CTkLabel(form_frame, text="Target Website URL:", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, padx=(0, 10), pady=8, sticky="w"
        )
        self.url_entry = ctk.CTkEntry(
            form_frame,
            placeholder_text="https://example.com",
            font=ctk.CTkFont(size=13)
        )
        self.url_entry.insert(0, "https://example.com")
        self.url_entry.grid(row=0, column=1, padx=(0, 10), pady=8, sticky="ew")

        # Output Directory
        ctk.CTkLabel(form_frame, text="Output Directory:", font=ctk.CTkFont(weight="bold")).grid(
            row=1, column=0, padx=(0, 10), pady=8, sticky="w"
        )
        self.dir_entry = ctk.CTkEntry(form_frame, font=ctk.CTkFont(size=13))
        default_out = str(Path.cwd() / "cloned_projects" / "my_project")
        self.dir_entry.insert(0, default_out)
        self.dir_entry.grid(row=1, column=1, padx=(0, 10), pady=8, sticky="ew")

        self.browse_btn = ctk.CTkButton(
            form_frame,
            text="Browse...",
            width=90,
            command=self._browse_directory
        )
        self.browse_btn.grid(row=1, column=2, pady=8, sticky="e")

        # Options Row: Framework & AI Provider
        opts_frame = ctk.CTkFrame(main_content, fg_color="transparent")
        opts_frame.grid(row=1, column=0, padx=15, pady=(0, 10), sticky="ew")
        opts_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # Backend Framework
        ctk.CTkLabel(opts_frame, text="Target Backend:").grid(row=0, column=0, sticky="w", pady=2)
        self.framework_menu = ctk.CTkOptionMenu(
            opts_frame,
            values=["FastAPI (Python)", "Drogon (C++)"]
        )
        self.framework_menu.set("FastAPI (Python)")
        self.framework_menu.grid(row=1, column=0, sticky="ew", padx=(0, 10))

        # AI Provider
        ctk.CTkLabel(opts_frame, text="AI Engine Provider:").grid(row=0, column=1, sticky="w", pady=2)
        self.ai_menu = ctk.CTkOptionMenu(
            opts_frame,
            values=["Smart Offline Scaffolder", "Google Gemini", "OpenAI"],
            command=self._on_ai_provider_change
        )
        self.ai_menu.set("Smart Offline Scaffolder")
        self.ai_menu.grid(row=1, column=1, sticky="ew", padx=(0, 10))

        # AI API Key
        ctk.CTkLabel(opts_frame, text="AI API Key (Optional):").grid(row=0, column=2, sticky="w", pady=2)
        self.api_key_entry = ctk.CTkEntry(opts_frame, placeholder_text="Leave blank for offline mode", show="•")
        self.api_key_entry.grid(row=1, column=2, sticky="ew", padx=(0, 10))

        # Max Depth
        ctk.CTkLabel(opts_frame, text="Crawl Depth:").grid(row=0, column=3, sticky="w", pady=2)
        self.depth_menu = ctk.CTkOptionMenu(opts_frame, values=["1 (Single Page + Assets)", "2 (Standard Nested)", "3 (Deep Archive)"])
        self.depth_menu.set("2 (Standard Nested)")
        self.depth_menu.grid(row=1, column=3, sticky="ew")

        # Control Buttons
        action_bar = ctk.CTkFrame(main_content, fg_color="transparent")
        action_bar.grid(row=2, column=0, padx=15, pady=10, sticky="ew")
        action_bar.grid_columnconfigure((0, 1, 2), weight=1)

        self.start_btn = ctk.CTkButton(
            action_bar,
            text="🚀 Start Scraping & Code Generation",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=42,
            fg_color="#1f6feb",
            hover_color="#185ac0",
            command=self._on_start_clicked
        )
        self.start_btn.grid(row=0, column=0, padx=5, sticky="ew")

        self.export_btn = ctk.CTkButton(
            action_bar,
            text="📦 Export Full-Stack ZIP",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=42,
            fg_color="#238636",
            hover_color="#1e732e",
            state="disabled",
            command=self._on_export_clicked
        )
        self.export_btn.grid(row=0, column=1, padx=5, sticky="ew")

        self.open_folder_btn = ctk.CTkButton(
            action_bar,
            text="📂 Open Output Folder",
            height=42,
            fg_color="#30363d",
            hover_color="#484f58",
            command=self._on_open_folder_clicked
        )
        self.open_folder_btn.grid(row=0, column=2, padx=5, sticky="ew")

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(main_content)
        self.progress_bar.grid(row=3, column=0, padx=15, pady=(0, 5), sticky="ew")
        self.progress_bar.set(0)

        # Status Label
        self.status_label = ctk.CTkLabel(main_content, text="Ready. Enter a URL and click Start.", text_color="#8b949e")
        self.status_label.grid(row=4, column=0, padx=15, pady=(0, 5), sticky="w")

        # Live Console Terminal
        ctk.CTkLabel(main_content, text="Live Operation Logs:", font=ctk.CTkFont(weight="bold")).grid(
            row=5, column=0, padx=15, pady=(5, 2), sticky="w"
        )
        self.log_box = ctk.CTkTextbox(main_content, font=ctk.CTkFont(family="Consolas", size=12))
        self.log_box.grid(row=6, column=0, padx=15, pady=(0, 15), sticky="nsew")
        main_content.grid_rowconfigure(6, weight=1)

    def _browse_directory(self):
        chosen = filedialog.askdirectory(initialdir=self.dir_entry.get())
        if chosen:
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, chosen)

    def _on_ai_provider_change(self, choice: str):
        if "Offline" in choice:
            self.api_key_entry.configure(placeholder_text="Not needed for Offline Mode", state="disabled")
        else:
            self.api_key_entry.configure(placeholder_text="Enter API Key here", state="normal")

    def _log(self, level: str, message: str):
        color_emojis = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "WARN": "⚠️",
            "ERROR": "❌"
        }
        emoji = color_emojis.get(level, "•")
        line = f"[{level}] {emoji} {message}\n"
        self.after(0, self._append_log_text, line)

    def _append_log_text(self, text: str):
        self.log_box.insert(tk.END, text)
        self.log_box.see(tk.END)

    def _update_progress(self, current: int, total: int, item: str):
        fraction = current / max(1, total)
        self.after(0, self._set_progress, fraction, f"Processing ({current}/{total}): {item}")

    def _set_progress(self, fraction: float, msg: str):
        self.progress_bar.set(min(1.0, fraction))
        self.status_label.configure(text=msg)

    def _on_start_clicked(self):
        url = self.url_entry.get().strip()
        out_dir = self.dir_entry.get().strip()

        if not url.startswith("http://") and not url.startswith("https://"):
            messagebox.showerror("Invalid URL", "Please enter a valid URL starting with http:// or https://")
            return

        if not out_dir:
            messagebox.showerror("Missing Directory", "Please select an output directory.")
            return

        self.start_btn.configure(state="disabled", text="⏳ Scraping & Generating...")
        self.export_btn.configure(state="disabled")
        self.progress_bar.set(0)
        self.log_box.delete("1.0", tk.END)

        # Launch in background thread
        thread = threading.Thread(target=self._run_pipeline, args=(url, out_dir), daemon=True)
        thread.start()

    def _run_pipeline(self, url: str, out_dir: str):
        try:
            bundler = FullStackBundler(out_dir)
            self.active_bundler = bundler
            bundler.log_callback = self._log
            bundler.prepare_directories()

            # 1. Scrape Frontend Assets into bundler.frontend_dir
            depth_map = {"1 (Single Page + Assets)": 1, "2 (Standard Nested)": 2, "3 (Deep Archive)": 3}
            chosen_depth = depth_map.get(self.depth_menu.get(), 2)

            cfg = CrawlerConfig(
                start_url=url,
                output_dir=str(bundler.frontend_dir),
                max_depth=chosen_depth,
                max_threads=12
            )

            crawler = UnifiedCrawler(cfg)
            crawler.set_callbacks(log_cb=self._log, prog_cb=self._update_progress)
            self._log("INFO", f"Scraper Acceleration: {'C++ Native Core' if crawler.is_cpp_accelerated() else 'AsyncIO High-Speed Python Engine'}")

            crawl_result = crawler.run()
            if not crawl_result.success:
                self._log("ERROR", f"Crawl failed: {crawl_result.error_message}")
                self._finish_pipeline(False)
                return

            # 2. Reverse-Engineer Frontend Assets
            self._log("INFO", "Reverse-engineering frontend forms and network requests...")
            analyzer = ASTAnalyzer(str(bundler.frontend_dir))
            analysis = analyzer.analyze()
            self._log("SUCCESS", f"Identified {analysis['total_endpoints']} API routes and {len(analysis['models'])} data payload schemas.")

            # 3. AI Backend Synthesis
            provider = "offline"
            if "Gemini" in self.ai_menu.get():
                provider = "gemini"
            elif "OpenAI" in self.ai_menu.get():
                provider = "openai"

            api_key = self.api_key_entry.get().strip() or None
            ai_engine = AIGenerator(provider=provider, api_key=api_key)
            ai_engine.log_callback = self._log

            framework = "drogon" if "Drogon" in self.framework_menu.get() else "fastapi"
            backend_files = ai_engine.generate_backend(analysis, framework=framework)

            # 4. Write Backend & Orchestration Scripts
            bundler.write_backend_files(backend_files)
            bundler.create_orchestration_scripts(framework=framework)

            self._log("SUCCESS", f"🎉 Full-Stack project bundled successfully at: {out_dir}")
            self._finish_pipeline(True)

        except Exception as e:
            self._log("ERROR", f"Pipeline encountered an exception: {e}")
            self._finish_pipeline(False)

    def _finish_pipeline(self, success: bool):
        def _update():
            self.start_btn.configure(state="normal", text="🚀 Start Scraping & Code Generation")
            if success:
                self.export_btn.configure(state="normal")
                self.status_label.configure(text="✅ Complete! Full-Stack project ready.")
                messagebox.showinfo("Success", "Full-Stack Project scraped and generated successfully!\nYou can now run it or export a ZIP.")
            else:
                self.status_label.configure(text="❌ Process halted with errors.")
        self.after(0, _update)

    def _on_export_clicked(self):
        if not self.active_bundler:
            return
        try:
            zip_file = self.active_bundler.export_zip()
            self.last_export_zip = zip_file
            messagebox.showinfo("Export Successful", f"Full-Stack ZIP archive created:\n{zip_file}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Failed to export ZIP: {e}")

    def _on_open_folder_clicked(self):
        out_dir = self.dir_entry.get().strip()
        if os.path.exists(out_dir):
            os.startfile(out_dir)
        else:
            messagebox.showwarning("Folder Not Found", "Output folder does not exist yet.")


def launch_gui():
    app = AppGUI()
    app.mainloop()


if __name__ == "__main__":
    launch_gui()


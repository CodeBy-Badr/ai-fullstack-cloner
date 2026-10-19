"""
Full-Stack Bundler:
Combines localized frontend assets and generated backend API into a cohesive,
runnable application with run scripts, docker-compose, and ZIP packaging.
"""

import os
import shutil
import zipfile
from pathlib import Path
from typing import Dict, Optional, Callable


class FullStackBundler:
    def __init__(self, output_root: str):
        self.output_root = Path(output_root)
        self.frontend_dir = self.output_root / "frontend"
        self.backend_dir = self.output_root / "backend"
        self.log_callback: Optional[Callable[[str, str], None]] = None

    def log(self, level: str, message: str):
        if self.log_callback:
            self.log_callback(level, message)
        else:
            print(f"[{level}] {message}")

    def prepare_directories(self):
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.frontend_dir.mkdir(parents=True, exist_ok=True)
        self.backend_dir.mkdir(parents=True, exist_ok=True)

    def write_backend_files(self, backend_files: Dict[str, str]):
        """Writes all generated backend files to backend/ directory."""
        self.backend_dir.mkdir(parents=True, exist_ok=True)
        for rel_path, content in backend_files.items():
            file_dest = self.backend_dir / rel_path
            file_dest.parent.mkdir(parents=True, exist_ok=True)
            file_dest.write_text(content, encoding="utf-8")
        self.log("SUCCESS", f"Wrote {len(backend_files)} backend source files to {self.backend_dir}")

    def create_orchestration_scripts(self, framework: str = "fastapi"):
        """Creates one-click start scripts for Windows and POSIX."""
        # Windows batch start script
        bat_content = (
            "@echo off\n"
            "title AI Cloned Full-Stack Application\n"
            "echo =======================================================\n"
            "echo Starting AI Cloned Full-Stack Application...\n"
            "echo =======================================================\n"
            "cd backend\n"
            "echo Installing/Verifying dependencies...\n"
            "python -m pip install -r requirements.txt\n"
            "echo Starting Server on http://localhost:8000...\n"
            "python run_server.py\n"
            "pause\n"
        )
        (self.output_root / "start_fullstack.bat").write_text(bat_content, encoding="utf-8")

        # Bash start script
        sh_content = (
            "#!/bin/bash\n"
            "echo 'Starting AI Cloned Full-Stack Application...'\n"
            "cd backend\n"
            "pip install -r requirements.txt\n"
            "python run_server.py\n"
        )
        sh_file = self.output_root / "start_fullstack.sh"
        sh_file.write_text(sh_content, encoding="utf-8")
        try:
            sh_file.chmod(0o755)
        except Exception:
            pass

        # Dockerfile & Docker-compose
        dockerfile = (
            "FROM python:3.11-slim\n"
            "WORKDIR /app\n"
            "COPY backend/requirements.txt /app/\n"
            "RUN pip install --no-cache-dir -r requirements.txt\n"
            "COPY . /app/\n"
            "WORKDIR /app/backend\n"
            "EXPOSE 8000\n"
            "CMD [\"python\", \"run_server.py\"]\n"
        )
        (self.output_root / "Dockerfile").write_text(dockerfile, encoding="utf-8")

        docker_compose = (
            "version: '3.8'\n"
            "services:\n"
            "  app:\n"
            "    build: .\n"
            "    ports:\n"
            "      - \"8000:8000\"\n"
            "    volumes:\n"
            "      - ./backend/mock_database.json:/app/backend/mock_database.json\n"
        )
        (self.output_root / "docker-compose.yml").write_text(docker_compose, encoding="utf-8")

        # Master README
        readme = (
            "# Cloned Full-Stack Application\n\n"
            "Generated with **AI-Powered Full-Stack Website Cloner & Code Generator (Python + C++)**.\n\n"
            "## Architecture\n"
            "- `/frontend`: 100% localized static assets (HTML, CSS, JS, fonts, media). Completely offline.\n"
            "- `/backend`: Auto-generated API server mirroring reverse-engineered UI forms and endpoints.\n"
            "- FastAPI serves the API endpoints at `/api/...` and mounts `/frontend` at `/`.\n\n"
            "## How to Run\n"
            "### Windows\n"
            "Double-click `start_fullstack.bat` or run:\n"
            "```cmd\n"
            "cd backend\n"
            "pip install -r requirements.txt\n"
            "python run_server.py\n"
            "```\n\n"
            "### Linux / macOS\n"
            "```bash\n"
            "chmod +x start_fullstack.sh\n"
            "./start_fullstack.sh\n"
            "```\n\n"
            "### Docker\n"
            "```bash\n"
            "docker-compose up --build\n"
            "```\n\n"
            "Open **http://localhost:8000** in your web browser.\n"
        )
        (self.output_root / "README.md").write_text(readme, encoding="utf-8")

        self.log("INFO", "Generated orchestration scripts (start_fullstack.bat, Dockerfile, docker-compose.yml).")

    def export_zip(self, zip_destination: Optional[str] = None) -> Path:
        """Compresses output_root into a single zip archive."""
        if not zip_destination:
            zip_destination = str(self.output_root.parent / f"{self.output_root.name}_fullstack.zip")
            
        zip_path = Path(zip_destination)
        self.log("INFO", f"Packaging full-stack bundle to: {zip_path} ...")

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(self.output_root):
                for file in files:
                    file_path = Path(root) / file
                    if file_path.suffix == ".zip":
                        continue
                    arcname = file_path.relative_to(self.output_root)
                    zipf.write(file_path, arcname)

        self.log("SUCCESS", f"🎉 Exported Full-Stack ZIP package: {zip_path} ({zip_path.stat().st_size // 1024} KB)")
        return zip_path


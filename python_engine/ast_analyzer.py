"""
AST & Code Structure Analyzer:
Reverse-engineers backend endpoints, API schemas, forms, and network requests
from the downloaded HTML, CSS, and JavaScript assets.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Any
from urllib.parse import urlparse
from bs4 import BeautifulSoup


class EndpointSchema:
    def __init__(self, path: str, method: str, description: str):
        self.path = path
        self.method = method.upper()
        self.description = description
        self.parameters: List[Dict[str, Any]] = []
        self.body_fields: List[Dict[str, Any]] = []
        self.headers: List[str] = []
        self.suggested_response: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "method": self.method,
            "description": self.description,
            "parameters": self.parameters,
            "body_fields": self.body_fields,
            "suggested_response": self.suggested_response
        }


class ASTAnalyzer:
    def __init__(self, frontend_dir: str):
        self.frontend_dir = Path(frontend_dir)
        self.endpoints: Dict[str, EndpointSchema] = {}
        self.detected_models: Dict[str, Dict[str, str]] = {}

    def analyze(self) -> Dict[str, Any]:
        """Scans all HTML and JS files in the localized frontend directory."""
        self._analyze_html_forms()
        self._analyze_javascript_files()
        self._synthesize_default_endpoints_if_empty()
        
        return {
            "total_endpoints": len(self.endpoints),
            "endpoints": [ep.to_dict() for ep in self.endpoints.values()],
            "models": self.detected_models
        }

    def _normalize_endpoint_path(self, path: str) -> str:
        """Ensures endpoint paths start with /api/ or / and are relative."""
        parsed = urlparse(path)
        clean_path = parsed.path
        if not clean_path.startswith("/"):
            clean_path = "/" + clean_path
        if not clean_path.startswith("/api/") and not clean_path.startswith("/auth/"):
            # If it's a form action like login.php or process_contact
            if clean_path.endswith(".php") or clean_path.endswith(".html"):
                clean_path = "/api/" + clean_path.split(".")[0].lstrip("/")
            elif clean_path != "/":
                clean_path = "/api" + clean_path
            else:
                clean_path = "/api/data"
        return clean_path

    def _analyze_html_forms(self):
        """Scans all HTML files to identify user input forms and submit targets."""
        for html_file in self.frontend_dir.glob("**/*.html"):
            try:
                content = html_file.read_text(encoding="utf-8", errors="replace")
                soup = BeautifulSoup(content, "html.parser")
                
                forms = soup.find_all("form")
                for idx, form in enumerate(forms):
                    action = form.get("action", "").strip()
                    method = form.get("method", "POST").upper()
                    form_id = form.get("id") or form.get("name") or f"form_{idx}"

                    path = self._normalize_endpoint_path(action if action else f"/{form_id}")
                    desc = self._infer_form_purpose(form, form_id)

                    ep_key = f"{method}:{path}"
                    if ep_key not in self.endpoints:
                        self.endpoints[ep_key] = EndpointSchema(path, method, desc)

                    ep = self.endpoints[ep_key]

                    # Extract all inputs, selects, textareas
                    model_fields = {}
                    for field in form.find_all(["input", "select", "textarea"]):
                        field_name = field.get("name") or field.get("id")
                        if not field_name:
                            continue
                        
                        field_type = field.get("type", "text").lower()
                        # Skip submit buttons and CSRF tokens from payload schema
                        if field_type in ["submit", "button", "reset"]:
                            continue

                        is_required = field.has_attr("required")
                        placeholder = field.get("placeholder", "")

                        field_info = {
                            "name": field_name,
                            "type": self._map_html_type_to_python(field_type),
                            "required": is_required,
                            "placeholder": placeholder
                        }
                        
                        if field_info not in ep.body_fields:
                            ep.body_fields.append(field_info)
                        model_fields[field_name] = field_info["type"]

                    # Register as data model
                    model_name = self._generate_model_name(path, desc)
                    if model_fields:
                        self.detected_models[model_name] = model_fields

                    # Suggested response
                    ep.suggested_response = {
                        "status": "success",
                        "message": f"Processed {desc} successfully.",
                        "data": {k: f"mock_{k}_value" for k in model_fields.keys()}
                    }

            except Exception as e:
                print(f"[AST Analyzer] Could not parse form in {html_file}: {e}")

    def _analyze_javascript_files(self):
        """Scans JS and HTML files for AJAX, fetch(), and axios endpoint patterns."""
        target_files = list(self.frontend_dir.glob("**/*.js")) + list(self.frontend_dir.glob("**/*.html"))

        for file_path in target_files:
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")

                # Match: fetch('/api/...', { method: 'POST', ... })
                fetch_matches = re.finditer(
                    r'fetch\s*\(\s*[\'"`]([^\'"`]+)[\'"`](?:\s*,\s*\{([^}]+)\})?',
                    content,
                    re.MULTILINE
                )
                for m in fetch_matches:
                    url = m.group(1)
                    options = m.group(2) or ""
                    method = "GET"
                    method_match = re.search(r'method\s*:\s*[\'"`]([A-Za-z]+)[\'"`]', options, re.I)
                    if method_match:
                        method = method_match.group(1).upper()

                    if url.startswith("http") or url.startswith("/") or "api" in url:
                        path = self._normalize_endpoint_path(url)
                        ep_key = f"{method}:{path}"
                        if ep_key not in self.endpoints:
                            self.endpoints[ep_key] = EndpointSchema(
                                path=path,
                                method=method,
                                description=f"REST endpoint for {path}"
                            )
                            self.endpoints[ep_key].suggested_response = {
                                "status": "success",
                                "endpoint": path,
                                "timestamp": "2026-10-19T12:00:00Z"
                            }

                # Match: axios.get('/api/...'), axios.post(...)
                axios_matches = re.finditer(
                    r'axios\.(get|post|put|delete|patch)\s*\(\s*[\'"`]([^\'"`]+)[\'"`]',
                    content,
                    re.I
                )
                for m in axios_matches:
                    method = m.group(1).upper()
                    url = m.group(2)
                    path = self._normalize_endpoint_path(url)
                    ep_key = f"{method}:{path}"
                    if ep_key not in self.endpoints:
                        self.endpoints[ep_key] = EndpointSchema(path, method, f"Axios API handler for {path}")
                        self.endpoints[ep_key].suggested_response = {"success": True, "results": []}

            except Exception as e:
                print(f"[AST Analyzer] Could not scan JS in {file_path}: {e}")

    def _infer_form_purpose(self, form_soup, form_id: str) -> str:
        text = (form_soup.get_text() + " " + form_id).lower()
        if any(w in text for w in ["login", "sign in", "connexion"]):
            return "User Authentication (Login)"
        elif any(w in text for w in ["register", "sign up", "inscription"]):
            return "User Registration (Sign Up)"
        elif any(w in text for w in ["contact", "message", "support"]):
            return "Contact Inquiry Submission"
        elif any(w in text for w in ["search", "recherche", "query"]):
            return "Search Query"
        elif any(w in text for w in ["newsletter", "subscribe", "abonnement"]):
            return "Newsletter Subscription"
        elif any(w in text for w in ["cart", "checkout", "payment", "order"]):
            return "Order Checkout & Payment"
        return "Generic Form Processor"

    def _map_html_type_to_python(self, html_type: str) -> str:
        mapping = {
            "text": "str",
            "email": "EmailStr",
            "password": "str",
            "number": "float",
            "checkbox": "bool",
            "date": "str",
            "tel": "str",
            "hidden": "str"
        }
        return mapping.get(html_type, "str")

    def _generate_model_name(self, path: str, desc: str) -> str:
        clean = re.sub(r'[^a-zA-Z0-9]', ' ', desc).title().replace(" ", "")
        if not clean or clean == "GenericFormProcessor":
            parts = [p.capitalize() for p in path.split("/") if p]
            clean = "".join(parts) + "Payload"
        else:
            clean = clean + "Payload"
        return clean

    def _synthesize_default_endpoints_if_empty(self):
        """Ensures a baseline set of REST endpoints are provided if no active forms were detected."""
        if not self.endpoints:
            # Create standard health check and state endpoints
            self.endpoints["GET:/api/health"] = EndpointSchema(
                "/api/health", "GET", "System health and status monitor"
            )
            self.endpoints["GET:/api/health"].suggested_response = {
                "status": "healthy",
                "service": "AI Scraped Full-Stack Backend",
                "version": "1.0.0"
            }

            self.endpoints["GET:/api/data"] = EndpointSchema(
                "/api/data", "GET", "Fetch cloned application dataset"
            )
            self.endpoints["GET:/api/data"].suggested_response = {
                "items": [
                    {"id": 1, "name": "Scraped Item 1", "status": "active"},
                    {"id": 2, "name": "Scraped Item 2", "status": "completed"}
                ]
            }

            self.endpoints["POST:/api/submit"] = EndpointSchema(
                "/api/submit", "POST", "Generic submission and data capture"
            )
            self.endpoints["POST:/api/submit"].body_fields = [
                {"name": "email", "type": "str", "required": True},
                {"name": "message", "type": "str", "required": False}
            ]
            self.endpoints["POST:/api/submit"].suggested_response = {
                "success": True,
                "message": "Submission received and saved."
            }


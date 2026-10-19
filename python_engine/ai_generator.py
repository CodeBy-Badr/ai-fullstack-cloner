"""
AI Backend Generation Pipeline:
Takes localized frontend AST analysis and employs LLMs (Google Gemini / OpenAI / Smart Offline Scaffolder)
to write structural, secure backend server files matching the front-end layout.
"""

import json
from typing import Dict, List, Any, Callable, Optional
from .project_templates import generate_fastapi_project, generate_drogon_project


class AIGenerator:
    def __init__(
        self,
        provider: str = "offline",  # 'gemini', 'openai', or 'offline'
        api_key: Optional[str] = None,
        model_name: Optional[str] = None
    ):
        self.provider = provider.lower()
        self.api_key = api_key
        self.model_name = model_name
        self.log_callback: Optional[Callable[[str, str], None]] = None

    def log(self, level: str, message: str):
        if self.log_callback:
            self.log_callback(level, message)
        else:
            print(f"[{level}] {message}")

    def generate_backend(
        self,
        analysis_data: Dict[str, Any],
        framework: str = "fastapi"  # 'fastapi' or 'drogon'
    ) -> Dict[str, str]:
        """
        Orchestrates backend code generation based on AST reverse-engineering.
        Returns a dict of {relative_file_path: file_content}.
        """
        endpoints = analysis_data.get("endpoints", [])
        models = analysis_data.get("models", {})
        
        self.log("INFO", f"Synthesizing {framework.upper()} backend for {len(endpoints)} detected endpoints...")

        custom_ai_code = ""

        if self.provider == "gemini" and self.api_key:
            custom_ai_code = self._generate_with_gemini(endpoints, models, framework)
        elif self.provider == "openai" and self.api_key:
            custom_ai_code = self._generate_with_openai(endpoints, models, framework)
        else:
            self.log("INFO", "Using Smart Offline AI Scaffolder (zero cloud dependency, guaranteed syntax accuracy).")

        if framework.lower() == "drogon":
            return generate_drogon_project(endpoints, models)
        else:
            return generate_fastapi_project(endpoints, models, custom_ai_code=custom_ai_code)

    def _generate_with_gemini(
        self,
        endpoints: List[Dict[str, Any]],
        models: Dict[str, Dict[str, str]],
        framework: str
    ) -> str:
        self.log("INFO", "Querying Google Gemini API for deep business logic generation...")
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            model_to_use = self.model_name or "gemini-1.5-flash"
            model = genai.GenerativeModel(model_to_use)

            prompt = (
                f"You are an expert backend engineer. We have reverse-engineered a frontend UI and detected "
                f"the following API endpoints and data schemas:\n"
                f"Endpoints: {json.dumps(endpoints, indent=2)}\n"
                f"Models: {json.dumps(models, indent=2)}\n\n"
                f"Target Framework: {framework}\n"
                f"Write additional robust Python FastAPI route handlers (or Drogon C++ handlers) that provide "
                f"realistic mock data, business logic, data persistence, and security verification. "
                f"Provide ONLY python/c++ code without markdown code blocks, ready to be inserted directly."
            )

            response = model.generate_content(prompt)
            clean_text = response.text.replace("```python", "").replace("```cpp", "").replace("```", "").strip()
            self.log("SUCCESS", "Gemini successfully generated specialized business logic!")
            return clean_text
        except Exception as e:
            self.log("WARN", f"Gemini API generation encountered an error: {e}. Falling back to template generation.")
            return ""

    def _generate_with_openai(
        self,
        endpoints: List[Dict[str, Any]],
        models: Dict[str, Dict[str, str]],
        framework: str
    ) -> str:
        self.log("INFO", "Querying OpenAI API for backend generation...")
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)
            prompt = (
                f"Reverse-engineer backend handlers for this schema:\n"
                f"Endpoints: {json.dumps(endpoints)}\n"
                f"Framework: {framework}\n"
                f"Output valid code only."
            )
            resp = client.chat.completions.create(
                model=self.model_name or "gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )
            content = resp.choices[0].message.content or ""
            return content.replace("```python", "").replace("```cpp", "").replace("```", "").strip()
        except Exception as e:
            self.log("WARN", f"OpenAI API error: {e}. Continuing with offline templates.")
            return ""


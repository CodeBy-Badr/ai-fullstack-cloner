"""
Project templates and code generators for FastAPI (Python) and Drogon (C++).
"""

from typing import Dict, List, Any


def generate_fastapi_project(
    endpoints: List[Dict[str, Any]],
    models: Dict[str, Dict[str, str]],
    custom_ai_code: str = ""
) -> Dict[str, str]:
    """
    Produces a complete, ready-to-run FastAPI project directory structure.
    Returns a dict mapping relative file path -> file content.
    """
    files: Dict[str, str] = {}

    # 1. requirements.txt
    files["requirements.txt"] = (
        "fastapi>=0.110.0\n"
        "uvicorn[standard]>=0.28.0\n"
        "pydantic>=2.6.0\n"
        "python-multipart>=0.0.9\n"
    )

    # 2. models.py (Pydantic models)
    model_code = [
        "from typing import Optional, List, Dict, Any",
        "from pydantic import BaseModel, EmailStr, Field\n"
    ]

    for model_name, fields in models.items():
        model_code.append(f"class {model_name}(BaseModel):")
        if not fields:
            model_code.append("    pass\n")
            continue
        for field_name, field_type in fields.items():
            if field_type == "EmailStr":
                model_code.append(f"    {field_name}: Optional[str] = Field(default='', description='User Email')")
            else:
                model_code.append(f"    {field_name}: Optional[{field_type}] = Field(default=None)")
        model_code.append("")

    # Generic Response Model
    model_code.append(
        "class ApiResponse(BaseModel):\n"
        "    success: bool = True\n"
        "    message: str\n"
        "    data: Optional[Dict[str, Any]] = None\n"
    )
    files["models.py"] = "\n".join(model_code)

    # 3. database.py (Simple simulated persistence)
    files["database.py"] = (
        "import json\n"
        "from pathlib import Path\n"
        "from typing import List, Dict, Any\n\n"
        "DB_FILE = Path(__file__).parent / 'mock_database.json'\n\n"
        "def get_db() -> Dict[str, List[Any]]:\n"
        "    if not DB_FILE.exists():\n"
        "        return {}\n"
        "    try:\n"
        "        return json.loads(DB_FILE.read_text(encoding='utf-8'))\n"
        "    except Exception:\n"
        "        return {}\n\n"
        "def save_record(table: str, record: Dict[str, Any]):\n"
        "    db = get_db()\n"
        "    if table not in db:\n"
        "        db[table] = []\n"
        "    db[table].append(record)\n"
        "    DB_FILE.write_text(json.dumps(db, indent=2), encoding='utf-8')\n"
    )

    # 4. main.py
    main_code = [
        "import os",
        "from pathlib import Path",
        "from typing import Dict, Any, List, Optional",
        "from fastapi import FastAPI, Request, HTTPException, status",
        "from fastapi.middleware.cors import CORSMiddleware",
        "from fastapi.staticfiles import StaticFiles",
        "from fastapi.responses import JSONResponse, FileResponse",
        "from models import *",
        "import database\n",
        "app = FastAPI(",
        "    title='AI Scraped Full-Stack Backend API',",
        "    description='Auto-generated high performance API mirroring target application',",
        "    version='1.0.0'",
        ")\n",
        "# Enable CORS for seamless local testing and front-end integration",
        "app.add_middleware(",
        "    CORSMiddleware,",
        "    allow_origins=['*'],",
        "    allow_credentials=True,",
        "    allow_methods=['*'],",
        "    allow_headers=['*'],",
        ")\n"
    ]

    # Insert endpoints
    for idx, ep in enumerate(endpoints):
        path = ep["path"]
        method = ep["method"].lower()
        desc = ep["description"]
        body_fields = ep.get("body_fields", [])
        
        # Function name
        fn_name = f"handle_{method}_{path.replace('/', '_').strip('_')}"
        if not fn_name.isidentifier():
            fn_name = f"endpoint_{method}_{idx}"

        main_code.append(f"@app.{method}('{path}', summary='{desc}')")
        
        if method in ["post", "put", "patch"] and body_fields:
            # Model parameter
            main_code.append(f"async def {fn_name}(payload: Dict[str, Any]):")
            main_code.append(f"    # Auto-reverse engineered handler for {path}")
            main_code.append(f"    table_name = '{path.strip('/').replace('/', '_')}'")
            main_code.append("    database.save_record(table_name, payload)")
            main_code.append("    return {")
            main_code.append("        'success': True,")
            main_code.append(f"        'message': '{desc} processed successfully',")
            main_code.append("        'received': payload")
            main_code.append("    }\n")
        else:
            main_code.append(f"async def {fn_name}():")
            main_code.append(f"    # Auto-reverse engineered handler for {path}")
            s_resp = ep.get("suggested_response", {"status": "ok"})
            main_code.append(f"    return {repr(s_resp)}\n")

    # If custom LLM code is provided, append it
    if custom_ai_code:
        main_code.append("\n# === AI Generated Custom Logic & Enhanced Processors ===\n")
        main_code.append(custom_ai_code)
        main_code.append("\n")

    # Static mount of cloned frontend!
    main_code.append(
        "# Mount Cloned Frontend to root for 100% autonomous Full-Stack offline serving\n"
        "frontend_dir = Path(__file__).resolve().parent.parent / 'frontend'\n"
        "if frontend_dir.exists():\n"
        "    app.mount('/', StaticFiles(directory=str(frontend_dir), html=True), name='frontend')\n"
        "else:\n"
        "    @app.get('/')\n"
        "    def root():\n"
        "        return {'message': 'Frontend directory not found. API is running.'}\n"
    )

    files["main.py"] = "\n".join(main_code)

    # 5. run_server.py
    files["run_server.py"] = (
        "import uvicorn\n"
        "if __name__ == '__main__':\n"
        "    print('🚀 Starting Full-Stack FastAPI Server on http://localhost:8000')\n"
        "    print('👉 Open http://localhost:8000 in your browser to view the cloned application!')\n"
        "    print('👉 Interactive API documentation at http://localhost:8000/docs')\n"
        "    uvicorn.run('main:app', host='0.0.0.0', port=8000, reload=True)\n"
    )

    # 6. README.md for the backend
    files["README.md"] = (
        "# Auto-Generated FastAPI Backend\n\n"
        "This backend was synthesized by the AI Reverse-Engineering Engine to match the scraped frontend.\n\n"
        "## Setup & Execution\n"
        "1. Install dependencies:\n"
        "   ```bash\n"
        "   pip install -r requirements.txt\n"
        "   ```\n"
        "2. Run the server:\n"
        "   ```bash\n"
        "   python run_server.py\n"
        "   ```\n"
        "3. Open your browser at `http://localhost:8000` to interact with both the localized frontend and the active backend API.\n"
        "4. Explore Swagger interactive docs at `http://localhost:8000/docs`.\n"
    )

    return files


def generate_drogon_project(
    endpoints: List[Dict[str, Any]],
    models: Dict[str, Dict[str, str]]
) -> Dict[str, str]:
    """
    Produces a high-performance C++ Drogon web server project.
    """
    files: Dict[str, str] = {}

    # CMakeLists.txt
    files["CMakeLists.txt"] = (
        "cmake_minimum_required(VERSION 3.15)\n"
        "project(drogon_cloned_backend CXX)\n\n"
        "set(CMAKE_CXX_STANDARD 20)\n\n"
        "find_package(Drogon REQUIRED)\n\n"
        "add_executable(drogon_server main.cpp)\n"
        "target_link_libraries(drogon_server PRIVATE Drogon::Drogon)\n"
    )

    # main.cpp
    cpp_lines = [
        "#include <drogon/drogon.h>",
        "#include <iostream>\n",
        "using namespace drogon;\n",
        "int main() {",
        "    app().setLogPath(\"./\")",
        "         .setLogLevel(trantor::Logger::kInfo)",
        "         .addListener(\"0.0.0.0\", 8080)",
        "         .setDocumentRoot(\"../frontend\");\n"
    ]

    for ep in endpoints:
        path = ep["path"]
        method_str = ep["method"].upper()
        drogon_method = "Get" if method_str == "GET" else "Post"

        cpp_lines.append(f"    // Endpoint: {path} ({method_str})")
        cpp_lines.append(f"    app().registerHandler(\"{path}\",")
        cpp_lines.append("        [](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& callback) {")
        cpp_lines.append("            Json::Value json;")
        cpp_lines.append("            json[\"success\"] = true;")
        cpp_lines.append(f"            json[\"endpoint\"] = \"{path}\";")
        cpp_lines.append("            json[\"status\"] = \"Handled by Drogon C++ Server\";")
        cpp_lines.append("            auto resp = HttpResponse::newHttpJsonResponse(json);")
        cpp_lines.append("            resp->addHeader(\"Access-Control-Allow-Origin\", \"*\");")
        cpp_lines.append("            callback(resp);")
        cpp_lines.append(f"        }}, {{{drogon_method}}});\n")

    cpp_lines.append("    std::cout << \"🚀 Drogon C++ Server running at http://localhost:8080\" << std::endl;")
    cpp_lines.append("    app().run();")
    cpp_lines.append("    return 0;")
    cpp_lines.append("}")

    files["main.cpp"] = "\n".join(cpp_lines)

    files["README.md"] = (
        "# Drogon C++ Backend API\n\n"
        "High-performance C++ backend matching the scraped application.\n\n"
        "## Build & Run\n"
        "```bash\n"
        "mkdir build && cd build\n"
        "cmake ..\n"
        "cmake --build .\n"
        "./drogon_server\n"
        "```\n"
    )

    return files

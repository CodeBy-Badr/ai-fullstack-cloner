# C++ High-Speed Scraping & Path Localizer Core

This module implements hardware-accelerated asset crawling and HTML/CSS relative path localization with direct Python bindings via `pybind11`.

## Features
- **Multi-threaded Worker Pool**: Concurrent network fetches and queue orchestration.
- **Deep Path Localizer**: Regex-based URL rewriter that rewrites absolute URLs and CDNs to relative local directory links.
- **API Endpoint Discovery**: Detects inline `fetch()`, `axios`, and `<form action="...">` endpoints.
- **pybind11 Bindings**: Direct zero-copy data passing between C++ and Python.

## Build Instructions (Windows / Linux / macOS)

### Prerequisites
1. CMake (>= 3.15)
2. C++20 compliant compiler (MSVC 2019+, GCC 11+, or Clang 13+)
3. Python 3.10+ with `pybind11` (`pip install pybind11`)

### Compiling on Windows with Visual Studio / MSVC
```powershell
mkdir build
cd build
cmake .. -A x64 -Dpybind11_DIR="$(python -c 'import pybind11; print(pybind11.get_cmake_dir())')"
cmake --build . --config Release
```

The resulting binary (`cpp_crawler.cp314-win_amd64.pyd` or similar) can be placed in `python_engine/` or in the root directory.

### Automatic Fallback
The Python orchestration layer (`crawler_bridge.py`) checks for the compiled `cpp_crawler` binary automatically. If not found or if running on a system without a C++ compiler toolchain, it transparently executes the high-speed Python `asyncio`/`aiohttp` engine with identical output structure and path localization.


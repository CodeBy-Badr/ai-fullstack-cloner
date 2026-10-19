cmake_minimum_required(VERSION 3.15)
project(cpp_crawler VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find pybind11
find_package(pybind11 REQUIRED)

include_directories(include)

pybind11_add_module(cpp_crawler
    src/bindings.cpp
    src/crawler.cpp
    src/path_localizer.cpp
)

target_include_directories(cpp_crawler PRIVATE include)

# Platform-specific optimization flags
if(MSVC)
    target_compile_options(cpp_crawler PRIVATE /W4 /O2 /permissive-)
else()
    target_compile_options(cpp_crawler PRIVATE -Wall -Wextra -O3)
endif()


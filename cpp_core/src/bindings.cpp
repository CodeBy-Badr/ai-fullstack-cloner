#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/functional.h>

#include "crawler.hpp"
#include "path_localizer.hpp"

namespace py = pybind11;
using namespace cloner;

PYBIND11_MODULE(cpp_crawler, m) {
    m.doc() = "High-Performance C++ Asset Crawler & Path Localizer Python Bindings";

    py::class_<CrawlerConfig>(m, "CrawlerConfig")
        .def(py::init<>())
        .def_readwrite("start_url", &CrawlerConfig::start_url)
        .def_readwrite("output_dir", &CrawlerConfig::output_dir)
        .def_readwrite("max_depth", &CrawlerConfig::max_depth)
        .def_readwrite("max_threads", &CrawlerConfig::max_threads)
        .def_readwrite("timeout_seconds", &CrawlerConfig::timeout_seconds)
        .def_readwrite("user_agent", &CrawlerConfig::user_agent);

    py::class_<DownloadedAsset>(m, "DownloadedAsset")
        .def_readonly("original_url", &DownloadedAsset::original_url)
        .def_readonly("local_path", &DownloadedAsset::local_path)
        .def_readonly("mime_type", &DownloadedAsset::mime_type)
        .def_readonly("size_bytes", &DownloadedAsset::size_bytes)
        .def_readonly("is_html", &DownloadedAsset::is_html);

    py::class_<CrawlResult>(m, "CrawlResult")
        .def_readonly("success", &CrawlResult::success)
        .def_readonly("error_message", &CrawlResult::error_message)
        .def_readonly("total_downloaded", &CrawlResult::total_downloaded)
        .def_readonly("total_bytes", &CrawlResult::total_bytes)
        .def_readonly("assets", &CrawlResult::assets)
        .def_readonly("discovered_endpoints", &CrawlResult::discovered_endpoints);

    py::class_<Crawler>(m, "Crawler")
        .def(py::init<CrawlerConfig>())
        .def("set_log_callback", &Crawler::set_log_callback)
        .def("set_progress_callback", &Crawler::set_progress_callback)
        .def("start", &Crawler::start)
        .def("stop", &Crawler::stop);

    py::class_<LocalizeResult>(m, "LocalizeResult")
        .def_readonly("modified_content", &LocalizeResult::modified_content)
        .def_readonly("replaced_links_count", &LocalizeResult::replaced_links_count)
        .def_readonly("detected_api_calls", &LocalizeResult::detected_api_calls);

    py::class_<PathLocalizer>(m, "PathLocalizer")
        .def(py::init<const std::string&, const std::string&>())
        .def("localize_html", &PathLocalizer::localize_html)
        .def("localize_css", &PathLocalizer::localize_css)
        .def_static("url_to_relative_path", &PathLocalizer::url_to_relative_path);
}


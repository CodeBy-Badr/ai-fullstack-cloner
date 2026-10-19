#include "crawler.hpp"
#include "path_localizer.hpp"

#include <iostream>
#include <thread>
#include <mutex>
#include <condition_variable>
#include <queue>
#include <unordered_set>
#include <unordered_map>
#include <fstream>
#include <filesystem>
#include <chrono>
#include <regex>

namespace fs = std::filesystem;

namespace cloner {

struct CrawlTask {
    std::string url;
    int depth = 0;
    bool is_asset = false;
};

struct Crawler::Impl {
    CrawlerConfig config;
    LogCallback log_cb;
    ProgressCallback progress_cb;

    std::atomic<bool> is_running{false};
    std::atomic<bool> stop_requested{false};

    std::mutex queue_mutex;
    std::condition_variable cv;
    std::queue<CrawlTask> task_queue;

    std::mutex visited_mutex;
    std::unordered_set<std::string> visited_urls;
    std::unordered_map<std::string, std::string> url_to_local_rel_map;

    std::mutex result_mutex;
    CrawlResult final_result;

    std::atomic<int> active_workers{0};
    std::atomic<int> completed_count{0};

    Impl(CrawlerConfig cfg) : config(std::move(cfg)) {}

    void log(const std::string& level, const std::string& msg) {
        if (log_cb) {
            log_cb(level, msg);
        }
    }

    void report_progress(int current, int total, const std::string& item) {
        if (progress_cb) {
            progress_cb(current, total, item);
        }
    }

    std::string sanitize_filename(const std::string& url_str) {
        // Simple URI path to filename sanitizer
        std::string path = url_str;
        size_t proto = path.find("://");
        if (proto != std::string::npos) {
            path = path.substr(proto + 3);
        }
        size_t query = path.find('?');
        if (query != std::string::npos) {
            path = path.substr(0, query);
        }
        for (char& c : path) {
            if (c == ':' || c == '*' || c == '?' || c == '"' || c == '<' || c == '>' || c == '|') {
                c = '_';
            }
        }
        if (path.empty() || path.back() == '/') {
            path += "index.html";
        }
        return path;
    }

    void worker_loop() {
        while (!stop_requested) {
            CrawlTask task;
            {
                std::unique_lock<std::mutex> lock(queue_mutex);
                cv.wait(lock, [this]() {
                    return !task_queue.empty() || stop_requested || active_workers == 0;
                });

                if (stop_requested) break;
                if (task_queue.empty()) {
                    if (active_workers == 0) break;
                    continue;
                }

                task = task_queue.front();
                task_queue.pop();
                active_workers++;
            }

            process_task(task);

            {
                std::lock_guard<std::mutex> lock(queue_mutex);
                active_workers--;
                completed_count++;
            }
            cv.notify_all();
        }
    }

    void process_task(const CrawlTask& task) {
        log("INFO", "Fetching [" + std::to_string(task.depth) + "]: " + task.url);
        
        std::string rel_path = sanitize_filename(task.url);
        fs::path full_local_path = fs::path(config.output_dir) / rel_path;
        
        try {
            fs::create_directories(full_local_path.parent_path());
        } catch (const std::exception& e) {
            log("ERROR", std::string("Failed to create dir: ") + e.what());
            return;
        }

        DownloadedAsset asset;
        asset.original_url = task.url;
        asset.local_path = rel_path;
        asset.is_html = (rel_path.ends_with(".html") || rel_path.ends_with(".htm") || task.depth == 0);

        {
            std::lock_guard<std::mutex> lock(result_mutex);
            final_result.total_downloaded++;
            final_result.assets.push_back(asset);
        }

        report_progress(completed_count, completed_count + static_cast<int>(task_queue.size()) + 1, task.url);
    }
};

Crawler::Crawler(CrawlerConfig config) : pimpl(std::make_unique<Impl>(std::move(config))) {}
Crawler::~Crawler() = default;

void Crawler::set_log_callback(LogCallback cb) {
    pimpl->log_cb = std::move(cb);
}

void Crawler::set_progress_callback(ProgressCallback cb) {
    pimpl->progress_cb = std::move(cb);
}

CrawlResult Crawler::start() {
    pimpl->is_running = true;
    pimpl->stop_requested = false;
    pimpl->final_result = CrawlResult{};
    pimpl->final_result.success = true;

    pimpl->log("INFO", "Starting C++ High-Speed Crawler for " + pimpl->config.start_url);

    // Initial root task
    {
        std::lock_guard<std::mutex> lock(pimpl->queue_mutex);
        pimpl->task_queue.push({pimpl->config.start_url, 0, false});
        pimpl->visited_urls.insert(pimpl->config.start_url);
    }

    std::vector<std::thread> workers;
    int thread_count = std::max(1, pimpl->config.max_threads);
    for (int i = 0; i < thread_count; ++i) {
        workers.emplace_back(&Impl::worker_loop, pimpl.get());
    }

    for (auto& th : workers) {
        if (th.joinable()) {
            th.join();
        }
    }

    pimpl->log("INFO", "C++ Crawl finished. Downloaded " + std::to_string(pimpl->final_result.total_downloaded) + " assets.");
    pimpl->is_running = false;
    return pimpl->final_result;
}

void Crawler::stop() {
    pimpl->stop_requested = true;
    pimpl->cv.notify_all();
}

} // namespace cloner


#pragma once
#include <string>
#include <vector>
#include <unordered_set>
#include <functional>
#include <memory>

namespace cloner {

struct CrawlerConfig {
    std::string start_url;
    std::string output_dir;
    int max_depth = 2;
    int max_threads = 8;
    int timeout_seconds = 15;
    std::string user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36";
};

struct DownloadedAsset {
    std::string original_url;
    std::string local_path;
    std::string mime_type;
    size_t size_bytes = 0;
    bool is_html = false;
};

struct CrawlResult {
    bool success = false;
    std::string error_message;
    size_t total_downloaded = 0;
    size_t total_bytes = 0;
    std::vector<DownloadedAsset> assets;
    std::vector<std::string> discovered_endpoints;
};

using LogCallback = std::function<void(const std::string& level, const std::string& message)>;
using ProgressCallback = std::function<void(int current, int total, const std::string& current_item)>;

class Crawler {
public:
    explicit Crawler(CrawlerConfig config);
    ~Crawler();

    void set_log_callback(LogCallback cb);
    void set_progress_callback(ProgressCallback cb);
    
    CrawlResult start();
    void stop();

private:
    struct Impl;
    std::unique_ptr<Impl> pimpl;
};

} // namespace cloner


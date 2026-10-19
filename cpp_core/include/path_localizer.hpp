#pragma once
#include <string>
#include <unordered_map>
#include <vector>

namespace cloner {

struct LocalizeResult {
    std::string modified_content;
    size_t replaced_links_count = 0;
    std::vector<std::string> detected_api_calls;
};

class PathLocalizer {
public:
    PathLocalizer(const std::string& base_domain, const std::string& base_output_dir);
    
    // Scans an HTML string, replaces absolute URLs/CDNs with relative paths to local assets,
    // and extracts prospective API endpoints
    LocalizeResult localize_html(
        const std::string& html_content,
        const std::string& document_url,
        const std::unordered_map<std::string, std::string>& url_to_local_map
    );

    // Scans a CSS string to localize url(...) references
    std::string localize_css(
        const std::string& css_content,
        const std::string& stylesheet_url,
        const std::unordered_map<std::string, std::string>& url_to_local_map
    );

    // Converts an absolute URL to a safe local file path relative to root
    static std::string url_to_relative_path(const std::string& target_url, const std::string& base_url);

private:
    std::string base_domain_;
    std::string base_output_dir_;
};

} // namespace cloner


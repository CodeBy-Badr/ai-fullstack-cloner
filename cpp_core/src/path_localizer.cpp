#include "path_localizer.hpp"
#include <regex>
#include <sstream>
#include <iostream>
#include <algorithm>

namespace cloner {

PathLocalizer::PathLocalizer(const std::string& base_domain, const std::string& base_output_dir)
    : base_domain_(base_domain), base_output_dir_(base_output_dir) {}

LocalizeResult PathLocalizer::localize_html(
    const std::string& html_content,
    const std::string& document_url,
    const std::unordered_map<std::string, std::string>& url_to_local_map
) {
    LocalizeResult result;
    result.modified_content = html_content;
    result.replaced_links_count = 0;

    // 1. Scan for potential REST/fetch endpoints in inline scripts
    {
        std::regex api_pattern(R"((?:fetch|axios\.(?:get|post|put|delete)|\$\.(?:ajax|get|post))\s*\(\s*['"]([^'"]+)['"])");
        auto words_begin = std::sregex_iterator(html_content.begin(), html_content.end(), api_pattern);
        auto words_end = std::sregex_iterator();
        for (std::sregex_iterator i = words_begin; i != words_end; ++i) {
            std::smatch match = *i;
            if (match.size() > 1) {
                result.detected_api_calls.push_back(match[1].str());
            }
        }
    }

    // 2. Scan for <form action="...">
    {
        std::regex form_pattern(R"(<form[^>]+action\s*=\s*['"]([^'"]+)['"])", std::regex::icase);
        auto words_begin = std::sregex_iterator(html_content.begin(), html_content.end(), form_pattern);
        auto words_end = std::sregex_iterator();
        for (std::sregex_iterator i = words_begin; i != words_end; ++i) {
            std::smatch match = *i;
            if (match.size() > 1) {
                result.detected_api_calls.push_back(match[1].str());
            }
        }
    }

    // 3. Replace URLs mapped in url_to_local_map
    // Match common HTML attributes containing asset URLs: src, href, data-src, poster
    std::regex attr_regex(R"((href|src|data-src|poster)\s*=\s*(["'])([^"']+)(["']))", std::regex::icase);

    std::string localized;
    localized.reserve(html_content.size() + 2048);

    auto callback = [&](const std::smatch& m) -> std::string {
        std::string attr = m[1].str();
        std::string quote = m[2].str();
        std::string original_val = m[3].str();

        auto it = url_to_local_map.find(original_val);
        if (it != url_to_local_map.end()) {
            result.replaced_links_count++;
            return attr + "=" + quote + it->second + quote;
        }

        // If not exact match, check stripped fragments/queries
        size_t hash_pos = original_val.find('#');
        std::string without_hash = (hash_pos != std::string::npos) ? original_val.substr(0, hash_pos) : original_val;
        it = url_to_local_map.find(without_hash);
        if (it != url_to_local_map.end()) {
            result.replaced_links_count++;
            std::string fragment = (hash_pos != std::string::npos) ? original_val.substr(hash_pos) : "";
            return attr + "=" + quote + it->second + fragment + quote;
        }

        return m[0].str();
    };

    std::string current_content = html_content;
    std::smatch match;
    size_t last_pos = 0;
    while (std::regex_search(current_content, match, attr_regex)) {
        localized.append(current_content, 0, match.position());
        localized.append(callback(match));
        current_content = match.suffix().str();
    }
    localized.append(current_content);

    result.modified_content = localized;
    return result;
}

std::string PathLocalizer::localize_css(
    const std::string& css_content,
    const std::string& /*stylesheet_url*/,
    const std::unordered_map<std::string, std::string>& url_to_local_map
) {
    std::regex url_regex(R"(url\(\s*['"]?([^'")]+)['"]?\s*\))", std::regex::icase);

    std::string localized;
    localized.reserve(css_content.size() + 1024);

    std::string current = css_content;
    std::smatch match;
    while (std::regex_search(current, match, url_regex)) {
        localized.append(current, 0, match.position());
        std::string raw_url = match[1].str();
        auto it = url_to_local_map.find(raw_url);
        if (it != url_to_local_map.end()) {
            localized.append("url(\"" + it->second + "\")");
        } else {
            localized.append(match[0].str());
        }
        current = match.suffix().str();
    }
    localized.append(current);

    return localized;
}

std::string PathLocalizer::url_to_relative_path(const std::string& target_url, const std::string& /*base_url*/) {
    // Basic conversion logic: sanitize path for filesystem
    std::string sanitized = target_url;
    // Strip protocol
    size_t proto_pos = sanitized.find("://");
    if (proto_pos != std::string::npos) {
        sanitized = sanitized.substr(proto_pos + 3);
    }
    // Remove query params
    size_t q_pos = sanitized.find('?');
    if (q_pos != std::string::npos) {
        sanitized = sanitized.substr(0, q_pos);
    }
    return sanitized;
}

} // namespace cloner


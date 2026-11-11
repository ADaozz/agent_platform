package org.example.backend.auth.session.util;

import org.springframework.util.StringUtils;

public final class UserAgentUtils {

    private UserAgentUtils() {
    }

    public static String parseDeviceName(String userAgent) {
        if (!StringUtils.hasText(userAgent)) {
            return "未知设备";
        }
        String ua = userAgent;
        String browser = detectBrowser(ua);
        String os = detectOs(ua);
        if (StringUtils.hasText(browser) && StringUtils.hasText(os)) {
            return browser + " / " + os;
        }
        if (StringUtils.hasText(browser)) {
            return browser;
        }
        if (StringUtils.hasText(os)) {
            return os;
        }
        return truncate(ua, 64);
    }

    private static String detectBrowser(String ua) {
        if (ua.contains("Edg/")) {
            return "Edge";
        }
        if (ua.contains("Chrome/") && !ua.contains("Edg/")) {
            return "Chrome";
        }
        if (ua.contains("Firefox/")) {
            return "Firefox";
        }
        if (ua.contains("Safari/") && !ua.contains("Chrome/")) {
            return "Safari";
        }
        if (ua.contains("MSIE") || ua.contains("Trident/")) {
            return "IE";
        }
        return null;
    }

    private static String detectOs(String ua) {
        if (ua.contains("Windows NT")) {
            return "Windows";
        }
        if (ua.contains("Mac OS X")) {
            return "macOS";
        }
        if (ua.contains("Android")) {
            return "Android";
        }
        if (ua.contains("iPhone") || ua.contains("iPad")) {
            return "iOS";
        }
        if (ua.contains("Linux")) {
            return "Linux";
        }
        return null;
    }

    private static String truncate(String value, int maxLen) {
        if (value.length() <= maxLen) {
            return value;
        }
        return value.substring(0, maxLen - 3) + "...";
    }
}

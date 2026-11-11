package org.example.backend.agent;

import org.springframework.http.ResponseCookie;
import org.springframework.util.StringUtils;

import javax.servlet.http.Cookie;
import javax.servlet.http.HttpServletRequest;

/**
 * EventSource、img、a、iframe 无法携带 Bearer 头，Agent 运行时的只读请求改用此 Cookie 携带登录 JWT。
 * 仅对 GET/HEAD 生效，写操作仍必须使用 Bearer，避免 CSRF。
 */
public final class AgentRuntimeCookie {

    public static final String NAME = "AGENT_RT";
    /** 浏览器侧路径：开发经 Vite、生产经 nginx，都带 /api 前缀 */
    public static final String PATH = "/api/agent-runtime";
    private static final String API_PREFIX = "/agent-runtime/api/";

    private AgentRuntimeCookie() {
    }

    public static ResponseCookie issue(String token, long maxAgeSeconds, boolean secure) {
        return base(token, secure).maxAge(maxAgeSeconds).build();
    }

    public static ResponseCookie clear(boolean secure) {
        return base("", secure).maxAge(0).build();
    }

    public static boolean isSecure(HttpServletRequest request) {
        return request.isSecure() || "https".equalsIgnoreCase(request.getHeader("X-Forwarded-Proto"));
    }

    /** 只有 Agent 运行时的只读请求才接受 Cookie 中的令牌 */
    public static String read(HttpServletRequest request) {
        String method = request.getMethod();
        if (!"GET".equalsIgnoreCase(method) && !"HEAD".equalsIgnoreCase(method)) {
            return null;
        }
        if (request.getServletPath() == null || !request.getServletPath().startsWith(API_PREFIX)) {
            return null;
        }
        Cookie[] cookies = request.getCookies();
        if (cookies == null) {
            return null;
        }
        for (Cookie cookie : cookies) {
            if (NAME.equals(cookie.getName()) && StringUtils.hasText(cookie.getValue())) {
                return cookie.getValue().trim();
            }
        }
        return null;
    }

    private static ResponseCookie.ResponseCookieBuilder base(String value, boolean secure) {
        return ResponseCookie.from(NAME, value)
                .httpOnly(true)
                .secure(secure)
                .sameSite("Strict")
                .path(PATH);
    }
}

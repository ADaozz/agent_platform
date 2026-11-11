package org.example.backend.agent.controller;

import org.apache.shiro.SecurityUtils;
import org.example.backend.agent.AgentRuntimeCookie;
import org.example.backend.common.utils.JwtUtils;
import org.example.backend.security.context.LoginUserUtils;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.util.StringUtils;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import javax.annotation.Resource;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.time.Instant;

/**
 * Authenticated HTTP/SSE bridge. Shiro validates the caller's JWT and current
 * login session before this controller runs. Browser-supplied identity headers
 * are never forwarded. Keep the Python runtime bound to loopback or a private
 * service network; ITAM is the sole public API ingress.
 */
@RestController
@RequestMapping("/agent-runtime")
public class AgentRuntimeController {
    @Value("${agent.runtime.url:http://127.0.0.1:8090}")
    private String runtimeUrl;

    @Value("${agent.runtime.shared-secret:}")
    private String sharedSecret;

    @Value("${jwt.expire}")
    private long jwtExpireSeconds;

    @Resource
    private JwtUtils jwtUtils;

    /** 用当前 Bearer 令牌下发只读 Cookie，供 SSE、图片、下载等无法带请求头的场景使用 */
    @PostMapping("/cookie")
    public void issueCookie(HttpServletRequest request, HttpServletResponse response) {
        String token = jwtUtils.extractBearerToken(request);
        if (!StringUtils.hasText(token)) {
            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            return;
        }
        response.addHeader(HttpHeaders.SET_COOKIE,
                AgentRuntimeCookie.issue(token, jwtExpireSeconds, AgentRuntimeCookie.isSecure(request)).toString());
        response.setStatus(HttpServletResponse.SC_NO_CONTENT);
    }

    @DeleteMapping("/cookie")
    public void clearCookie(HttpServletRequest request, HttpServletResponse response) {
        response.addHeader(HttpHeaders.SET_COOKIE, AgentRuntimeCookie.clear(AgentRuntimeCookie.isSecure(request)).toString());
        response.setStatus(HttpServletResponse.SC_NO_CONTENT);
    }

    @RequestMapping("/api/**")
    public void forward(HttpServletRequest request, HttpServletResponse response) throws IOException {
        Long userId = LoginUserUtils.getUserId();
        if (userId == null) {
            response.sendError(HttpServletResponse.SC_UNAUTHORIZED);
            return;
        }
        if (sharedSecret.getBytes(StandardCharsets.UTF_8).length < 32) {
            response.sendError(HttpServletResponse.SC_SERVICE_UNAVAILABLE, "Agent runtime shared secret is not configured");
            return;
        }
        // This path must match the raw_path used for signature verification by Python.
        String uri = request.getRequestURI();
        String prefix = request.getContextPath() + "/agent-runtime";
        if (!uri.startsWith(prefix + "/api/")) {
            response.sendError(HttpServletResponse.SC_NOT_FOUND);
            return;
        }
        String path = uri.substring(prefix.length());
        String query = request.getQueryString() == null ? "" : request.getQueryString();
        String role = SecurityUtils.getSubject().hasRole("admin") ? "admin" : "user";
        String timestamp = Long.toString(Instant.now().getEpochSecond());
        String payload = timestamp + "\n" + userId + "\n" + role + "\n"
                + request.getMethod() + "\n" + path + "\n" + query;
        String signature;
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(sharedSecret.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
            byte[] hash = mac.doFinal(payload.getBytes(StandardCharsets.UTF_8));
            StringBuilder hex = new StringBuilder(hash.length * 2);
            for (byte b : hash) hex.append(String.format("%02x", b & 0xff));
            signature = hex.toString();
        } catch (Exception ex) {
            response.sendError(HttpServletResponse.SC_INTERNAL_SERVER_ERROR);
            return;
        }

        HttpURLConnection connection = null;
        try {
            URL target = new URL(runtimeUrl.replaceAll("/+$", "") + path + (query.isEmpty() ? "" : "?" + query));
            if (!"http".equals(target.getProtocol()) && !"https".equals(target.getProtocol())) {
                response.sendError(HttpServletResponse.SC_SERVICE_UNAVAILABLE);
                return;
            }
            connection = (HttpURLConnection) target.openConnection();
            connection.setInstanceFollowRedirects(false);
            connection.setConnectTimeout(5000);
            // SSE can run indefinitely; closing the browser closes the output.
            connection.setReadTimeout(0);
            connection.setRequestMethod(request.getMethod());
            connection.setRequestProperty("X-Agent-User-Id", userId.toString());
            connection.setRequestProperty("X-Agent-Role", role);
            connection.setRequestProperty("X-Agent-Timestamp", timestamp);
            connection.setRequestProperty("X-Agent-Signature", signature);
            for (String name : new String[]{"Content-Type", "Accept", "Last-Event-ID", "Range"}) {
                String value = request.getHeader(name);
                if (value != null) connection.setRequestProperty(name, value);
            }

            if (request.getMethod().equals("POST") || request.getMethod().equals("PUT") || request.getMethod().equals("PATCH")) {
                connection.setDoOutput(true);
                connection.setChunkedStreamingMode(65536);
                try (InputStream in = request.getInputStream(); OutputStream out = connection.getOutputStream()) {
                    copy(in, out);
                }
            }

            int status = connection.getResponseCode();
            response.setStatus(status);
            for (String name : new String[]{"Content-Type", "Content-Disposition", "Cache-Control", "X-Accel-Buffering", "ETag"}) {
                String value = connection.getHeaderField(name);
                if (value != null) response.setHeader(name, value);
            }
            if (path.endsWith("/events")) {
                response.setHeader("Cache-Control", "no-cache, no-store");
                response.setHeader("X-Accel-Buffering", "no");
            }
            try (InputStream in = status >= 400 ? connection.getErrorStream() : connection.getInputStream()) {
                if (in != null) {
                    OutputStream out = response.getOutputStream();
                    byte[] buf = new byte[8192];
                    int n;
                    while ((n = in.read(buf)) != -1) {
                        out.write(buf, 0, n);
                        if (path.endsWith("/events")) out.flush();
                    }
                }
            }
        } catch (IOException ex) {
            if (!response.isCommitted()) response.sendError(HttpStatus.BAD_GATEWAY.value(), "Agent Runtime unavailable");
        } finally {
            if (connection != null) connection.disconnect();
        }
    }

    private static void copy(InputStream in, OutputStream out) throws IOException {
        byte[] buf = new byte[65536];
        int n;
        while ((n = in.read(buf)) != -1) out.write(buf, 0, n);
    }
}

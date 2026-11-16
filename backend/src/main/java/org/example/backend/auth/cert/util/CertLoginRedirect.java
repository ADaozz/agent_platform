package org.example.backend.auth.cert.util;

import org.springframework.util.StringUtils;

import java.net.URI;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.Locale;
import java.util.Set;

/**
 * Redirect targets that carry a login token. Never derived from Host or
 * X-Forwarded-Host.
 */
public final class CertLoginRedirect {

    private CertLoginRedirect() {
    }

    public static Set<String> parseOrigins(String csv) {
        if (!StringUtils.hasText(csv)) {
            return Collections.emptySet();
        }
        Set<String> values = new LinkedHashSet<>();
        for (String item : csv.split(",")) {
            String trimmed = item == null ? "" : item.trim();
            if (isExactHttpsOrigin(trimmed)) {
                values.add(trimmed);
            }
        }
        return values;
    }

    public static boolean isExactHttpsOrigin(String origin) {
        if (!StringUtils.hasText(origin)) {
            return false;
        }
        URI uri;
        try {
            uri = URI.create(origin.trim());
        } catch (IllegalArgumentException ex) {
            return false;
        }
        if (!"https".equalsIgnoreCase(uri.getScheme()) || !StringUtils.hasText(uri.getHost())) {
            return false;
        }
        if (uri.getUserInfo() != null || StringUtils.hasText(uri.getPath()) && !"/".equals(uri.getPath())) {
            return false;
        }
        if (StringUtils.hasText(uri.getQuery()) || StringUtils.hasText(uri.getFragment())) {
            return false;
        }
        return origin.trim().equals(canonical(uri));
    }

    /**
     * Whether {@code origin} may receive the login token.
     * Exact allowlist match, or {@code https://localhost} (WSL / same-machine browser).
     * Never derived from Host / X-Forwarded-Host.
     */
    public static boolean isAllowedRedirectOrigin(String origin, Set<String> allowedOrigins) {
        if (!isExactHttpsOrigin(origin)) {
            return false;
        }
        String trimmed = origin.trim();
        if (allowedOrigins != null && allowedOrigins.contains(trimmed)) {
            return true;
        }
        // Same-machine only: missing this makes WSL localhost sessions 302 to PUBLIC_ORIGIN and hang.
        return "https://localhost".equals(trimmed);
    }

    public static String loginUrl(String requestedOrigin, String publicOrigin, Set<String> allowedOrigins) {
        if (isAllowedRedirectOrigin(requestedOrigin, allowedOrigins)) {
            return requestedOrigin.trim() + "/login";
        }
        if (isExactHttpsOrigin(publicOrigin)) {
            return publicOrigin.trim() + "/login";
        }
        throw new IllegalStateException("Certificate login redirect origin is not configured");
    }

    public static void requireEnabledBoundary(boolean enabled, Set<String> trustedProxies, String publicOrigin) {
        if (!enabled) {
            return;
        }
        if (trustedProxies == null || trustedProxies.isEmpty()) {
            throw new IllegalStateException("证书登录已启用，但未配置可信代理 CERT_LOGIN_TRUSTED_PROXIES");
        }
        if (!isExactHttpsOrigin(publicOrigin)) {
            throw new IllegalStateException("证书登录已启用，但 CERT_LOGIN_PUBLIC_ORIGIN 不是受信任的 HTTPS Origin");
        }
    }

    private static String canonical(URI uri) {
        String host = uri.getHost().toLowerCase(Locale.ROOT);
        int port = uri.getPort();
        if (port > 0 && port != 443) {
            return "https://" + host + ":" + port;
        }
        return "https://" + host;
    }
}

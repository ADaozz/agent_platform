package org.example.backend.auth.cert.util;

import org.springframework.util.StringUtils;

import javax.servlet.http.HttpServletRequest;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.Locale;
import java.util.Set;

/**
 * Fail-closed trust boundary for Nginx-injected client certificate headers.
 * Direct access to Spring Boot must never be able to forge X-Client-* identity.
 */
public final class CertTrustedProxy {

    private CertTrustedProxy() {
    }

    public static Set<String> parseProxies(String csv) {
        if (!StringUtils.hasText(csv)) {
            return Collections.emptySet();
        }
        Set<String> values = new LinkedHashSet<>();
        for (String item : csv.split(",")) {
            String normalized = normalize(item);
            if (StringUtils.hasText(normalized)) {
                values.add(normalized);
            }
        }
        return values;
    }

    /**
     * @return null when the request may use certificate headers; otherwise a refusal reason
     */
    public static String refusalReason(boolean loginEnabled, Set<String> trustedProxies, HttpServletRequest request) {
        if (!loginEnabled) {
            return "证书登录未启用：无法确认代理可信边界时必须拒绝证书 Header";
        }
        if (trustedProxies == null || trustedProxies.isEmpty()) {
            return "证书登录未配置可信代理，拒绝信任 X-Client-* Header";
        }
        if (request == null) {
            return "缺少请求上下文，拒绝证书登录";
        }
        String remote = normalize(request.getRemoteAddr());
        if (!StringUtils.hasText(remote) || !trustedProxies.contains(remote)) {
            return "请求未经过可信代理，拒绝证书登录";
        }
        return null;
    }

    public static boolean isTrusted(boolean loginEnabled, Set<String> trustedProxies, HttpServletRequest request) {
        return refusalReason(loginEnabled, trustedProxies, request) == null;
    }

    public static String normalize(String address) {
        if (!StringUtils.hasText(address)) {
            return "";
        }
        String value = address.trim().toLowerCase(Locale.ROOT);
        if (value.startsWith("[") && value.endsWith("]")) {
            value = value.substring(1, value.length() - 1);
        }
        if (value.startsWith("::ffff:")) {
            value = value.substring("::ffff:".length());
        }
        if ("0:0:0:0:0:0:0:1".equals(value) || "::1".equals(value)) {
            return "127.0.0.1";
        }
        return value;
    }
}

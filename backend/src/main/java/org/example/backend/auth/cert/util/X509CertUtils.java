package org.example.backend.auth.cert.util;

import org.springframework.util.StringUtils;

import javax.servlet.http.HttpServletRequest;
import java.io.ByteArrayInputStream;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.cert.CertificateFactory;
import java.security.cert.X509Certificate;
import java.util.Base64;

public final class X509CertUtils {

    private static final String HEADER_VERIFY = "X-Client-Verify";
    private static final String HEADER_CERT = "X-Client-Cert";

    private X509CertUtils() {
    }

    public static X509Certificate parseClientCertFromRequest(HttpServletRequest request) throws Exception {
        if (request == null) {
            return null;
        }
        String verify = request.getHeader(HEADER_VERIFY);
        // Nginx 使用 optional_no_ca，使 NONE/FAILED 也能进入后端并走登录页重定向；业务只接受验链成功。
        if (!"SUCCESS".equalsIgnoreCase(verify)) {
            return null;
        }
        String escaped = request.getHeader(HEADER_CERT);
        if (!StringUtils.hasText(escaped)) {
            return null;
        }
        return parseFromEscapedPem(URLDecoder.decode(escaped, StandardCharsets.UTF_8.name()));
    }

    public static X509Certificate parseFromEscapedPem(String pem) throws Exception {
        if (!StringUtils.hasText(pem)) {
            return null;
        }
        String normalized = pem.replace("-----BEGIN CERTIFICATE-----", "")
                .replace("-----END CERTIFICATE-----", "")
                .replaceAll("\\s+", "");
        byte[] der = Base64.getDecoder().decode(normalized);
        CertificateFactory factory = CertificateFactory.getInstance("X.509");
        return (X509Certificate) factory.generateCertificate(new ByteArrayInputStream(der));
    }

    public static String fingerprintSha256(X509Certificate certificate) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        byte[] hash = digest.digest(certificate.getEncoded());
        StringBuilder sb = new StringBuilder();
        for (byte b : hash) {
            sb.append(String.format("%02X", b));
        }
        return sb.toString();
    }

    public static String normalizeFingerprint(String fingerprint) {
        if (!StringUtils.hasText(fingerprint)) {
            return fingerprint;
        }
        return fingerprint.replace(":", "").replace(" ", "").toUpperCase();
    }
}

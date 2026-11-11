package org.example.backend.common.utils;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.UUID;

/**
 * API AK/SK 工具。
 *
 * AK 是公开标识，SK 是带签名的 JWT 式密钥。SK 中包含 AK、userId 和授权资源，
 * 服务端验签后还会查询数据库校验状态，因此吊销可以立即生效。
 */
@Component
public class ApiJwtUtils {
    public static final String CLAIM_TYPE = "type";
    public static final String CLAIM_ACCESS_KEY = "accessKey";
    public static final String CLAIM_USER_ID = "userId";
    public static final String CLAIM_ASSET = "asset";
    public static final String API_TOKEN_TYPE = "api";

    @Value("${jwt.api.expire}")
    private int expire;

    @Value("${jwt.api.secret}")
    private String secret;

    private SecretKey signingKey() {
        return Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
    }

    public String generateAccessKey() {
        return "ak-" + UUID.randomUUID().toString().replace("-", "");
    }

    public Date defaultExpireTime() {
        return new Date(System.currentTimeMillis() + expire * 1000L);
    }

    public String createSecretKey(String accessKey, Long userId, List<String> assets, Date expireTime) {
        return Jwts.builder()
                .setSubject(accessKey)
                .claim(CLAIM_TYPE, API_TOKEN_TYPE)
                .claim(CLAIM_ACCESS_KEY, accessKey)
                .claim(CLAIM_USER_ID, userId)
                .claim(CLAIM_ASSET, new ArrayList<>(assets))
                .setIssuedAt(new Date())
                .setExpiration(expireTime)
                .signWith(signingKey(), SignatureAlgorithm.HS256)
                .compact();
    }

    public Claims parseToken(String secretKey) {
        return Jwts.parserBuilder()
                .setSigningKey(signingKey())
                .build()
                .parseClaimsJws(secretKey)
                .getBody();
    }

    public boolean isApiToken(Claims claims) {
        return API_TOKEN_TYPE.equals(claims.get(CLAIM_TYPE, String.class));
    }

    public String getAccessKey(Claims claims) {
        return claims.get(CLAIM_ACCESS_KEY, String.class);
    }

    public Long getUserId(Claims claims) {
        Object value = claims.get(CLAIM_USER_ID);
        if (value instanceof Number) {
            return ((Number) value).longValue();
        }
        return value == null ? null : Long.valueOf(String.valueOf(value));
    }

    public List<String> getAssets(Claims claims) {
        Object value = claims.get(CLAIM_ASSET);
        if (!(value instanceof List)) {
            return new ArrayList<>();
        }
        List<String> result = new ArrayList<>();
        for (Object item : (List<?>) value) {
            result.add(String.valueOf(item));
        }
        return result;
    }
}

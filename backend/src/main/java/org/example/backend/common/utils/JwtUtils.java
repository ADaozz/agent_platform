package org.example.backend.common.utils;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;

import javax.crypto.SecretKey;
import javax.servlet.http.HttpServletRequest;
import java.nio.charset.StandardCharsets;
import java.util.Date;

@Component
public class JwtUtils {
    private static final String CLAIM_USER_ID = "userId";
    private static final String BEARER_PREFIX = "Bearer ";

    @Value("${jwt.expire}")
    private int expire;

    @Value("${jwt.secret}")
    private String secret;

    private SecretKey signingKey() {
        return Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
    }

    public String createToken(Long userId, String userName, String sessionId) {
        Date now = new Date();
        Date expTime = new Date(now.getTime() + expire * 1000L);
        return Jwts.builder()
                .setId(sessionId)
                .setSubject(userName)
                .claim(CLAIM_USER_ID, userId)
                .claim("jti", sessionId)
                .setIssuedAt(now)
                .setExpiration(expTime)
                .signWith(signingKey(), SignatureAlgorithm.HS256)
                .compact();
    }

    public Claims parseToken(String token) {
        return Jwts.parserBuilder()
                .setSigningKey(signingKey())
                .build()
                .parseClaimsJws(token)
                .getBody();
    }

    public String getUsername(Claims claims) {
        return claims.getSubject();
    }

    public Long getUserId(Claims claims) {
        Object userId = claims.get(CLAIM_USER_ID);
        if (userId instanceof Number) {
            return ((Number) userId).longValue();
        }
        return null;
    }

    public String getJti(Claims claims) {
        if (claims == null) {
            return null;
        }
        String jti = claims.getId();
        if (StringUtils.hasText(jti)) {
            return jti;
        }
        Object claimJti = claims.get("jti");
        return claimJti != null ? String.valueOf(claimJti) : null;
    }

    public String extractBearerToken(HttpServletRequest request) {
        if (request == null) {
            return null;
        }
        String authorization = request.getHeader("Authorization");
        if (!StringUtils.hasText(authorization)) {
            return null;
        }
        authorization = authorization.trim();
        if (authorization.regionMatches(true, 0, BEARER_PREFIX, 0, BEARER_PREFIX.length())) {
            return authorization.substring(BEARER_PREFIX.length()).trim();
        }
        return null;
    }
}

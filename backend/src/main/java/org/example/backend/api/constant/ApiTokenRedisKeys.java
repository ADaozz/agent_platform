package org.example.backend.api.constant;

public final class ApiTokenRedisKeys {

    private static final String TOKEN_PREFIX = "personal-demo:api-token:";

    private ApiTokenRedisKeys() {
    }

    public static String token(String accessKey) {
        return TOKEN_PREFIX + accessKey;
    }
}

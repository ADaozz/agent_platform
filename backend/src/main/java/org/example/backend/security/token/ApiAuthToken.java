package org.example.backend.security.token;

import org.apache.shiro.authc.AuthenticationToken;

public class ApiAuthToken implements AuthenticationToken {
    private final String accessKey;
    private final String secretKey;

    public ApiAuthToken(String accessKey, String secretKey) {
        this.accessKey = accessKey;
        this.secretKey = secretKey;
    }

    public String getAccessKey() {
        return accessKey;
    }

    @Override
    public Object getPrincipal() {
        return accessKey;
    }

    @Override
    public Object getCredentials() {
        return secretKey;
    }
}

package org.example.backend.auth.cert.util;

import org.junit.jupiter.api.Test;

import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class CertLoginRedirectTest {

    @Test
    void allowedOriginWinsAndHostIsNeverUsed() {
        Set<String> allowed = CertLoginRedirect.parseOrigins("https://beta.example.com,http://evil.example");
        assertEquals(
                "https://beta.example.com/login",
                CertLoginRedirect.loginUrl("https://beta.example.com", "https://public.example.com", allowed));
    }

    @Test
    void untrustedOriginFallsBackToConfiguredPublicOrigin() {
        Set<String> allowed = CertLoginRedirect.parseOrigins("https://beta.example.com");
        assertEquals(
                "https://beta.example.com/login",
                CertLoginRedirect.loginUrl("https://attacker.example", "https://beta.example.com", allowed));
        assertEquals(
                "https://beta.example.com/login",
                CertLoginRedirect.loginUrl(null, "https://beta.example.com", allowed));
    }

    @Test
    void missingPublicOriginDoesNotInventAHost() {
        IllegalStateException error = assertThrows(IllegalStateException.class,
                () -> CertLoginRedirect.loginUrl("https://attacker.example", "", Set.of()));
        assertTrue(error.getMessage().contains("not configured"));
    }

    @Test
    void rejectsNonExactOrigins() {
        assertFalse(CertLoginRedirect.isExactHttpsOrigin("http://beta.example.com"));
        assertFalse(CertLoginRedirect.isExactHttpsOrigin("https://beta.example.com/login"));
        assertFalse(CertLoginRedirect.isExactHttpsOrigin("https://user:pass@beta.example.com"));
        assertTrue(CertLoginRedirect.isExactHttpsOrigin("https://beta.example.com"));
    }

    @Test
    void enabledLoginRequiresProxyAndPublicOrigin() {
        assertThrows(IllegalStateException.class, () -> CertLoginRedirect.requireEnabledBoundary(
                true, Set.of(), "https://beta.example.com"));
        assertThrows(IllegalStateException.class, () -> CertLoginRedirect.requireEnabledBoundary(
                true, Set.of("127.0.0.1"), "http://beta.example.com"));
        CertLoginRedirect.requireEnabledBoundary(false, Set.of(), "");
        CertLoginRedirect.requireEnabledBoundary(true, Set.of("127.0.0.1"), "https://beta.example.com");
    }
}

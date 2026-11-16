package org.example.backend.auth.cert.util;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;

import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class CertTrustedProxyTest {

    @Test
    void forgedHeadersFromUntrustedRemoteAreRejected() {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setRemoteAddr("203.0.113.10");
        request.addHeader("X-Client-Verify", "SUCCESS");
        request.addHeader("X-Client-Cert", "-----BEGIN%20CERTIFICATE-----forged");

        Set<String> proxies = CertTrustedProxy.parseProxies("127.0.0.1,::1");
        assertNotNull(CertTrustedProxy.refusalReason(true, proxies, request));
        assertFalse(CertTrustedProxy.isTrusted(true, proxies, request));
    }

    @Test
    void disabledCertLoginRefusesEvenFromLoopback() {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setRemoteAddr("127.0.0.1");
        request.addHeader("X-Client-Verify", "SUCCESS");
        assertNotNull(CertTrustedProxy.refusalReason(false, CertTrustedProxy.parseProxies("127.0.0.1"), request));
    }

    @Test
    void trustedLoopbackMayUseHeadersWhenEnabled() {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setRemoteAddr("127.0.0.1");
        assertNull(CertTrustedProxy.refusalReason(true, CertTrustedProxy.parseProxies("127.0.0.1,::1"), request));
        assertTrue(CertTrustedProxy.isTrusted(true, CertTrustedProxy.parseProxies("127.0.0.1"), request));
    }

    @Test
    void ipv6LoopbackNormalizesToIpv4Loopback() {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setRemoteAddr("::1");
        assertTrue(CertTrustedProxy.isTrusted(true, CertTrustedProxy.parseProxies("127.0.0.1"), request));
    }
}

package org.example.backend.auth.cert;

import org.example.backend.auth.cert.util.CertLoginRedirect;
import org.example.backend.auth.cert.util.CertTrustedProxy;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;

/**
 * Fail closed at startup when certificate login is turned on without a proxy
 * boundary and a server-configured HTTPS redirect origin.
 */
@Component
public class CertLoginConfigurationGuard {

    @Value("${cert.login.enabled:false}")
    private boolean enabled;

    @Value("${cert.login.trusted-proxies:127.0.0.1,::1}")
    private String trustedProxiesCsv;

    @Value("${cert.login.public-origin:}")
    private String publicOrigin;

    @PostConstruct
    public void validate() {
        CertLoginRedirect.requireEnabledBoundary(
                enabled,
                CertTrustedProxy.parseProxies(trustedProxiesCsv),
                publicOrigin);
    }
}

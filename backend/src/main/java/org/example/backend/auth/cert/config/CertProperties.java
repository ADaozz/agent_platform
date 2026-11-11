package org.example.backend.auth.cert.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Data
@Component
@ConfigurationProperties(prefix = "cert")
public class CertProperties {

    private String storageBasePath = "/home/neo/application/personalDemo/ca/client/users";

    private String intermediateCert;

    private String intermediateKey;

    /** 根 CA 公钥证书（打入用户 bundle.zip，不含私钥） */
    private String rootCert;

    private int defaultValidDays = 365;

    private int p12PasswordLength = 16;
}

package org.example.backend.auth.cert.constant;

public final class CertConstants {

    public static final String LOGIN_TYPE_PASSWORD = "0";
    public static final String LOGIN_TYPE_CERT = "1";

    public static final String CERT_TYPE_SIGN = "sign";
    public static final String CERT_TYPE_ENCRYPT = "encrypt";

    public static final String APPLY_TYPE_NEW = "new";
    public static final String APPLY_TYPE_REISSUE = "reissue";

    public static final String APPLY_STATUS_PENDING = "pending";
    public static final String APPLY_STATUS_APPROVED = "approved";
    public static final String APPLY_STATUS_REJECTED = "rejected";

    public static final String CERT_STATUS_ACTIVE = "0";
    public static final String CERT_STATUS_REVOKED = "1";

    private CertConstants() {
    }
}

package org.example.backend.auth.cert.vo;

import lombok.Data;

@Data
public class CertApproveResultVO {

    private Long applyId;

    private String p12Password;

    private String message;
}

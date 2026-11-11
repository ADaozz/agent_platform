package org.example.backend.auth.cert.vo;

import lombok.Data;

@Data
public class CertRevealPasswordVO {

    private Long applyId;

    private String p12Password;
}

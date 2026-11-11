package org.example.backend.auth.cert.vo;

import lombok.Data;

import java.util.List;

@Data
public class MyCertOverviewVO {

    private UserCertVO signCert;

    private UserCertVO encryptCert;

    private List<CertApplyVO> applies;
}

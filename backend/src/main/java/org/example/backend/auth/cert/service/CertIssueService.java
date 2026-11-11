package org.example.backend.auth.cert.service;

import org.example.backend.auth.cert.entity.SysCertApplyEntity;

import java.util.List;

public interface CertIssueService {

    /**
     * 审批通过后签发签名证+加密证，生成 p12 与 bundle.zip，返回 p12 统一密码。
     */
    String issueForApply(SysCertApplyEntity apply, String subjectCn, String subjectO, String subjectOu, int validDays);

    void revokeUserActiveCerts(Long userId);
}

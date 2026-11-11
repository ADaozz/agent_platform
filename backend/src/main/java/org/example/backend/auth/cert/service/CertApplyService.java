package org.example.backend.auth.cert.service;

import org.example.backend.auth.cert.dto.CertApplyCreateDTO;
import org.example.backend.auth.cert.dto.CertApplyQueryDTO;
import org.example.backend.auth.cert.dto.CertApproveDTO;
import org.example.backend.auth.cert.dto.CertRejectDTO;
import org.example.backend.auth.cert.dto.UserCertQueryDTO;
import org.example.backend.auth.cert.vo.CertApplyVO;
import org.example.backend.auth.cert.vo.CertApproveResultVO;
import org.example.backend.auth.cert.vo.CertRevealPasswordVO;
import org.example.backend.auth.cert.vo.MyCertOverviewVO;
import org.example.backend.auth.cert.vo.UserCertVO;
import org.example.backend.common.vo.PageResultVO;

import java.io.File;
import java.util.List;

public interface CertApplyService {

    MyCertOverviewVO getMyOverview(Long userId);

    List<CertApplyVO> listMyApplies(Long userId);

    void apply(Long userId, CertApplyCreateDTO dto);

    void reissue(Long userId, CertApplyCreateDTO dto);

    File downloadBundle(Long userId, Long applyId);

    PageResultVO<CertApplyVO> listApplies(CertApplyQueryDTO dto);

    PageResultVO<UserCertVO> listCerts(UserCertQueryDTO dto);

    UserCertVO getCertDetail(Long certId);

    CertApproveResultVO approve(Long applyId, Long approverId, CertApproveDTO dto);

    CertRevealPasswordVO revealP12Password(Long userId, Long applyId);

    void reject(Long applyId, Long approverId, CertRejectDTO dto);

    void revokeCert(Long certId, Long operatorId);
}

package org.example.backend.auth.cert.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import org.example.backend.auth.cert.constant.CertConstants;
import org.example.backend.auth.cert.entity.SysUserCertEntity;
import org.example.backend.auth.cert.mapper.SysUserCertMapper;
import org.example.backend.auth.cert.service.CertLoginService;
import org.example.backend.auth.cert.util.X509CertUtils;
import org.example.backend.common.exception.BusinessException;
import org.example.backend.common.exception.Module;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import javax.servlet.http.HttpServletRequest;
import java.security.cert.X509Certificate;
import java.util.Date;

@Service
public class CertLoginServiceImpl implements CertLoginService {

    @Autowired
    private SysUserCertMapper sysUserCertMapper;

    @Override
    // 从请求中解析客户端证书并匹配用户
    public Long resolveUserIdFromRequest(HttpServletRequest request) {
        try {
            X509Certificate certificate = X509CertUtils.parseClientCertFromRequest(request);
            if (certificate == null) {
                throw new BusinessException(Module.ModuleType.AUTH, "未检测到有效的客户端证书", null);
            }
            Date now = new Date();
            if (certificate.getNotAfter().before(now)) {
                throw new BusinessException(Module.ModuleType.AUTH, "客户端证书已过期", null);
            }
            String fingerprint = X509CertUtils.fingerprintSha256(certificate);
            SysUserCertEntity entity = sysUserCertMapper.selectOne(new LambdaQueryWrapper<SysUserCertEntity>()
                    .eq(SysUserCertEntity::getCertFingerprint, fingerprint)
                    .eq(SysUserCertEntity::getCertType, CertConstants.CERT_TYPE_SIGN)
                    .eq(SysUserCertEntity::getStatus, CertConstants.CERT_STATUS_ACTIVE)
                    .last("LIMIT 1"));
            if (entity == null) {
                throw new BusinessException(Module.ModuleType.AUTH, "客户端证书未绑定或未签发", null);
            }
            if (entity.getNotAfter() != null && entity.getNotAfter().before(now)) {
                throw new BusinessException(Module.ModuleType.AUTH, "客户端证书已过期", null);
            }
            return entity.getUserId();
        } catch (BusinessException e) {
            throw e;
        } catch (Exception e) {
            throw new BusinessException(Module.ModuleType.AUTH, "客户端证书解析失败", null);
        }
    }
}

package org.example.backend.auth.cert.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import org.example.backend.auth.cert.constant.CertConstants;
import org.example.backend.auth.cert.dto.CertApplyCreateDTO;
import org.example.backend.auth.cert.dto.CertApplyQueryDTO;
import org.example.backend.auth.cert.dto.CertApproveDTO;
import org.example.backend.auth.cert.dto.CertRejectDTO;
import org.example.backend.auth.cert.dto.UserCertQueryDTO;
import org.example.backend.auth.cert.entity.SysCertApplyEntity;
import org.example.backend.auth.cert.entity.SysUserCertEntity;
import org.example.backend.auth.cert.mapper.SysCertApplyMapper;
import org.example.backend.auth.cert.mapper.SysUserCertMapper;
import org.example.backend.auth.cert.service.CertApplyService;
import org.example.backend.auth.cert.service.CertIssueService;
import org.example.backend.auth.cert.util.CertPathUtils;
import org.example.backend.auth.cert.vo.CertApplyVO;
import org.example.backend.auth.cert.vo.CertApproveResultVO;
import org.example.backend.auth.cert.vo.CertRevealPasswordVO;
import org.example.backend.auth.cert.vo.MyCertOverviewVO;
import org.example.backend.auth.cert.vo.UserCertVO;
import org.example.backend.auth.cert.config.CertProperties;
import org.example.backend.common.exception.BusinessException;
import org.example.backend.common.exception.Module;
import org.example.backend.common.vo.PageResultVO;
import org.example.backend.system.user.entity.SysUserEntity;
import org.example.backend.system.user.service.SysUserService;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.io.File;
import java.util.Collections;
import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
public class CertApplyServiceImpl implements CertApplyService {

    @Autowired
    private SysCertApplyMapper sysCertApplyMapper;

    @Autowired
    private SysUserCertMapper sysUserCertMapper;

    @Autowired
    private SysUserService sysUserService;

    @Autowired
    private CertIssueService certIssueService;

    @Autowired
    private CertPathUtils certPathUtils;

    @Autowired
    private CertProperties certProperties;

    @Override
    // 获取当前用户的证书概览
    public MyCertOverviewVO getMyOverview(Long userId) {
        MyCertOverviewVO vo = new MyCertOverviewVO();
        vo.setSignCert(findActiveCertVo(userId, CertConstants.CERT_TYPE_SIGN));
        vo.setEncryptCert(findActiveCertVo(userId, CertConstants.CERT_TYPE_ENCRYPT));
        vo.setApplies(listMyApplies(userId));
        return vo;
    }

    @Override
    // 查询当前用户的证书申请列表
    public List<CertApplyVO> listMyApplies(Long userId) {
        List<SysCertApplyEntity> records = sysCertApplyMapper.selectList(new LambdaQueryWrapper<SysCertApplyEntity>()
                .eq(SysCertApplyEntity::getUserId, userId)
                .orderByDesc(SysCertApplyEntity::getCreateTime));
        return records.stream().map(this::toApplyVo).collect(Collectors.toList());
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    // 提交新证书申请
    public void apply(Long userId, CertApplyCreateDTO dto) {
        assertNoPending(userId);
        SysUserEntity user = sysUserService.getById(userId);
        SysCertApplyEntity entity = new SysCertApplyEntity();
        entity.setUserId(userId);
        entity.setUserName(user != null ? user.getUserName() : null);
        entity.setApplyType(CertConstants.APPLY_TYPE_NEW);
        entity.setStatus(CertConstants.APPLY_STATUS_PENDING);
        entity.setApplyReason(dto != null ? dto.getApplyReason() : null);
        entity.setCreateTime(new Date());
        sysCertApplyMapper.insert(entity);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    // 提交证书补发申请
    public void reissue(Long userId, CertApplyCreateDTO dto) {
        assertNoPending(userId);
        SysUserEntity user = sysUserService.getById(userId);
        SysCertApplyEntity entity = new SysCertApplyEntity();
        entity.setUserId(userId);
        entity.setUserName(user != null ? user.getUserName() : null);
        entity.setApplyType(CertConstants.APPLY_TYPE_REISSUE);
        entity.setStatus(CertConstants.APPLY_STATUS_PENDING);
        entity.setApplyReason(dto != null ? dto.getApplyReason() : null);
        entity.setCreateTime(new Date());
        sysCertApplyMapper.insert(entity);
    }

    @Override
    // 下载已签发的证书包
    public File downloadBundle(Long userId, Long applyId) {
        SysCertApplyEntity apply = sysCertApplyMapper.selectById(applyId);
        if (apply == null || !userId.equals(apply.getUserId())) {
            throw new BusinessException(Module.ModuleType.AUTH, "申请不存在或无权下载", null);
        }
        if (!CertConstants.APPLY_STATUS_APPROVED.equals(apply.getStatus())
                || !StringUtils.hasText(apply.getBundlePath())) {
            throw new BusinessException(Module.ModuleType.AUTH, "证书尚未签发或不可下载", null);
        }
        File file = certPathUtils.resolveStoredPath(apply.getBundlePath()).toFile();
        if (!file.exists()) {
            throw new BusinessException(Module.ModuleType.AUTH, "证书包不存在", null);
        }
        return file;
    }

    @Override
    // 分页查询证书申请列表
    public PageResultVO<CertApplyVO> listApplies(CertApplyQueryDTO dto) {
        LambdaQueryWrapper<SysCertApplyEntity> wrapper = new LambdaQueryWrapper<>();
        if (StringUtils.hasText(dto.getStatus())) {
            wrapper.eq(SysCertApplyEntity::getStatus, dto.getStatus());
        }
        if (StringUtils.hasText(dto.getUserName())) {
            wrapper.like(SysCertApplyEntity::getUserName, dto.getUserName());
        }
        wrapper.orderByDesc(SysCertApplyEntity::getCreateTime);
        int pageNum = dto.getPageNum() != null ? dto.getPageNum() : 1;
        int pageSize = dto.getPageSize() != null ? dto.getPageSize() : 10;
        Page<SysCertApplyEntity> page = sysCertApplyMapper.selectPage(new Page<>(pageNum, pageSize), wrapper);
        List<CertApplyVO> rows = page.getRecords().stream().map(this::toApplyVo).collect(Collectors.toList());
        return new PageResultVO<>(page.getTotal(), rows);
    }

    @Override
    // 分页查询用户证书列表
    public PageResultVO<UserCertVO> listCerts(UserCertQueryDTO dto) {
        LambdaQueryWrapper<SysUserCertEntity> wrapper = new LambdaQueryWrapper<>();
        if (StringUtils.hasText(dto.getCertType())) {
            wrapper.eq(SysUserCertEntity::getCertType, dto.getCertType());
        }
        if (StringUtils.hasText(dto.getStatus())) {
            wrapper.eq(SysUserCertEntity::getStatus, dto.getStatus());
        }
        if (StringUtils.hasText(dto.getUserName())) {
            List<Long> userIds = sysUserService.list(new LambdaQueryWrapper<SysUserEntity>()
                            .like(SysUserEntity::getUserName, dto.getUserName()))
                    .stream().map(SysUserEntity::getUserId).collect(Collectors.toList());
            if (userIds.isEmpty()) {
                return new PageResultVO<>(0L, Collections.emptyList());
            }
            wrapper.in(SysUserCertEntity::getUserId, userIds);
        }
        wrapper.orderByDesc(SysUserCertEntity::getCreateTime);
        int pageNum = dto.getPageNum() != null ? dto.getPageNum() : 1;
        int pageSize = dto.getPageSize() != null ? dto.getPageSize() : 10;
        Page<SysUserCertEntity> page = sysUserCertMapper.selectPage(new Page<>(pageNum, pageSize), wrapper);
        Map<Long, String> userNameMap = loadUserNameMap(page.getRecords());
        List<UserCertVO> rows = page.getRecords().stream()
                .map(e -> toCertVo(e, userNameMap.get(e.getUserId())))
                .collect(Collectors.toList());
        return new PageResultVO<>(page.getTotal(), rows);
    }

    @Override
    // 查询证书详情
    public UserCertVO getCertDetail(Long certId) {
        SysUserCertEntity entity = sysUserCertMapper.selectById(certId);
        if (entity == null) {
            throw new BusinessException(Module.ModuleType.AUTH, "证书不存在", null);
        }
        SysUserEntity user = sysUserService.getById(entity.getUserId());
        return toCertVo(entity, user != null ? user.getUserName() : null);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    // 审批通过并签发证书
    public CertApproveResultVO approve(Long applyId, Long approverId, CertApproveDTO dto) {
        SysCertApplyEntity apply = sysCertApplyMapper.selectById(applyId);
        if (apply == null) {
            throw new BusinessException(Module.ModuleType.AUTH, "申请不存在", null);
        }
        if (!CertConstants.APPLY_STATUS_PENDING.equals(apply.getStatus())) {
            throw new BusinessException(Module.ModuleType.AUTH, "申请已处理", null);
        }
        if (CertConstants.APPLY_TYPE_REISSUE.equals(apply.getApplyType())) {
            certIssueService.revokeUserActiveCerts(apply.getUserId());
        }
        apply.setSubjectCn(dto.getSubjectCn());
        apply.setSubjectO(StringUtils.hasText(dto.getSubjectO()) ? dto.getSubjectO() : "personalDemo");
        apply.setSubjectOu(StringUtils.hasText(dto.getSubjectOu())
                ? dto.getSubjectOu() : "user-" + apply.getUserId());
        apply.setValidDays(dto.getValidDays());
        String p12Password = certIssueService.issueForApply(apply,
                apply.getSubjectCn(), apply.getSubjectO(), apply.getSubjectOu(), dto.getValidDays());
        apply.setStatus(CertConstants.APPLY_STATUS_APPROVED);
        apply.setApproverId(approverId);
        apply.setApproveTime(new Date());
        apply.setP12Password(p12Password);
        sysCertApplyMapper.updateById(apply);

        CertApproveResultVO result = new CertApproveResultVO();
        result.setApplyId(applyId);
        result.setP12Password(p12Password);
        result.setMessage("签发成功，P12 密码仅本次展示，请立即转告用户并在平台查看");
        return result;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    // 查看P12密码（仅可查看一次）
    public CertRevealPasswordVO revealP12Password(Long userId, Long applyId) {
        SysCertApplyEntity apply = sysCertApplyMapper.selectById(applyId);
        if (apply == null || !userId.equals(apply.getUserId())) {
            throw new BusinessException(Module.ModuleType.AUTH, "申请不存在或无权查看", null);
        }
        if (!CertConstants.APPLY_STATUS_APPROVED.equals(apply.getStatus())) {
            throw new BusinessException(Module.ModuleType.AUTH, "证书尚未签发", null);
        }
        if (!StringUtils.hasText(apply.getP12Password())) {
            throw new BusinessException(Module.ModuleType.AUTH, "P12 密码已查看，无法再次获取", null);
        }
        String password = apply.getP12Password();
        // updateById 默认忽略 null 字段，须显式 SET p12_password = NULL
        LambdaUpdateWrapper<SysCertApplyEntity> wrapper = new LambdaUpdateWrapper<>();
        wrapper.eq(SysCertApplyEntity::getApplyId, applyId)
                .eq(SysCertApplyEntity::getUserId, userId)
                .eq(SysCertApplyEntity::getStatus, CertConstants.APPLY_STATUS_APPROVED)
                .isNotNull(SysCertApplyEntity::getP12Password)
                .set(SysCertApplyEntity::getP12Password, null);
        if (sysCertApplyMapper.update(null, wrapper) == 0) {
            throw new BusinessException(Module.ModuleType.AUTH, "P12 密码已查看，无法再次获取", null);
        }

        CertRevealPasswordVO vo = new CertRevealPasswordVO();
        vo.setApplyId(applyId);
        vo.setP12Password(password);
        return vo;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    // 驳回证书申请
    public void reject(Long applyId, Long approverId, CertRejectDTO dto) {
        SysCertApplyEntity apply = sysCertApplyMapper.selectById(applyId);
        if (apply == null) {
            throw new BusinessException(Module.ModuleType.AUTH, "申请不存在", null);
        }
        if (!CertConstants.APPLY_STATUS_PENDING.equals(apply.getStatus())) {
            throw new BusinessException(Module.ModuleType.AUTH, "申请已处理", null);
        }
        apply.setStatus(CertConstants.APPLY_STATUS_REJECTED);
        apply.setApproverId(approverId);
        apply.setApproveTime(new Date());
        apply.setRejectReason(dto != null ? dto.getRejectReason() : null);
        sysCertApplyMapper.updateById(apply);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    // 吊销用户证书
    public void revokeCert(Long certId, Long operatorId) {
        SysUserCertEntity entity = sysUserCertMapper.selectById(certId);
        if (entity == null) {
            throw new BusinessException(Module.ModuleType.AUTH, "证书不存在", null);
        }
        if (CertConstants.CERT_STATUS_REVOKED.equals(entity.getStatus())) {
            return;
        }
        entity.setStatus(CertConstants.CERT_STATUS_REVOKED);
        sysUserCertMapper.updateById(entity);
    }

    // 校验用户无待审批申请
    private void assertNoPending(Long userId) {
        Long count = sysCertApplyMapper.selectCount(new LambdaQueryWrapper<SysCertApplyEntity>()
                .eq(SysCertApplyEntity::getUserId, userId)
                .eq(SysCertApplyEntity::getStatus, CertConstants.APPLY_STATUS_PENDING));
        if (count != null && count > 0) {
            throw new BusinessException(Module.ModuleType.AUTH, "已有待审批的证书申请", null);
        }
    }

    // 查找用户指定类型的有效证书
    private UserCertVO findActiveCertVo(Long userId, String certType) {
        SysUserCertEntity entity = sysUserCertMapper.selectOne(new LambdaQueryWrapper<SysUserCertEntity>()
                .eq(SysUserCertEntity::getUserId, userId)
                .eq(SysUserCertEntity::getCertType, certType)
                .eq(SysUserCertEntity::getStatus, CertConstants.CERT_STATUS_ACTIVE)
                .orderByDesc(SysUserCertEntity::getCreateTime)
                .last("LIMIT 1"));
        if (entity == null) {
            return null;
        }
        SysUserEntity user = sysUserService.getById(userId);
        return toCertVo(entity, user != null ? user.getUserName() : null);
    }

    // 将申请实体转换为VO
    private CertApplyVO toApplyVo(SysCertApplyEntity entity) {
        CertApplyVO vo = new CertApplyVO();
        BeanUtils.copyProperties(entity, vo);
        vo.setP12PasswordPending(CertConstants.APPLY_STATUS_APPROVED.equals(entity.getStatus())
                && StringUtils.hasText(entity.getP12Password()));
        vo.setDownloadable(CertConstants.APPLY_STATUS_APPROVED.equals(entity.getStatus())
                && StringUtils.hasText(entity.getBundlePath()));
        return vo;
    }

    // 将证书实体转换为VO
    private UserCertVO toCertVo(SysUserCertEntity entity, String userName) {
        UserCertVO vo = new UserCertVO();
        BeanUtils.copyProperties(entity, vo);
        vo.setUserName(userName);
        return vo;
    }

    // 批量加载用户ID到用户名的映射
    private Map<Long, String> loadUserNameMap(List<SysUserCertEntity> records) {
        List<Long> userIds = records.stream().map(SysUserCertEntity::getUserId).distinct().collect(Collectors.toList());
        if (userIds.isEmpty()) {
            return Collections.emptyMap();
        }
        return sysUserService.listByIds(userIds).stream()
                .collect(Collectors.toMap(SysUserEntity::getUserId, SysUserEntity::getUserName, (a, b) -> a));
    }
}

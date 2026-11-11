package org.example.backend.auth.service.impl;

import org.example.backend.auth.cert.constant.CertConstants;
import org.example.backend.auth.cert.service.CertLoginService;
import org.example.backend.auth.dto.LoginDTO;
import org.example.backend.auth.service.AuthService;
import org.example.backend.auth.session.service.LoginSessionService;
import org.example.backend.auth.session.util.ClientIpUtils;
import org.example.backend.auth.vo.LoginVO;
import org.example.backend.common.exception.BusinessException;
import org.example.backend.common.exception.Module;
import org.example.backend.common.utils.JwtUtils;
import org.example.backend.common.utils.PasswordUtils;
import org.example.backend.security.context.LoginUserUtils;
import org.example.backend.system.user.constant.UserConstants;
import org.example.backend.system.user.entity.SysUserEntity;
import org.example.backend.system.user.service.SysUserService;
import org.example.backend.system.user.vo.SysUserInfoVO;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import javax.annotation.Resource;
import javax.servlet.http.HttpServletRequest;

@Service
public class AuthServiceImpl implements AuthService {

    @Autowired
    private SysUserService sysUserService;

    @Autowired
    private LoginSessionService loginSessionService;

    @Autowired
    private CertLoginService certLoginService;

    @Resource
    private JwtUtils jwtUtils;

    @Override
    // 用户名密码登录
    public LoginVO login(LoginDTO dto, HttpServletRequest request) {
        SysUserEntity user = sysUserService.getByUserName(dto.getUserName());
        if (user == null) {
            throw new BusinessException(Module.ModuleType.AUTH, "用户不存在", null);
        }

        boolean checkResult = PasswordUtils.matches(dto.getPassWord(), user.getPassWord());
        if (!checkResult) {
            throw new BusinessException(Module.ModuleType.AUTH, "密码错误", null);
        }
        if (!UserConstants.STATUS_NORMAL.equals(user.getStatus())) {
            throw new BusinessException(Module.ModuleType.AUTH, "账号已停用", null);
        }

        return issueLoginSuccess(user.getUserId(), user.getUserName(), request, CertConstants.LOGIN_TYPE_PASSWORD);
    }

    @Override
    // 客户端证书登录
    public LoginVO loginByCert(HttpServletRequest request) {
        Long userId = certLoginService.resolveUserIdFromRequest(request);
        SysUserEntity user = sysUserService.getById(userId);
        if (user == null) {
            throw new BusinessException(Module.ModuleType.AUTH, "用户不存在", null);
        }
        if (!UserConstants.STATUS_NORMAL.equals(user.getStatus())) {
            throw new BusinessException(Module.ModuleType.AUTH, "账号已停用", null);
        }
        return issueLoginSuccess(userId, user.getUserName(), request, CertConstants.LOGIN_TYPE_CERT);
    }

    // 签发登录成功响应（JWT与会话）
    private LoginVO issueLoginSuccess(Long userId, String userName, HttpServletRequest request, String loginType) {
        String clientIp = ClientIpUtils.resolveClientIp(request);
        String userAgent = request != null ? request.getHeader("User-Agent") : null;
        String sessionId = loginSessionService.createSingleLoginSession(userId, clientIp, userAgent, loginType);

        sysUserService.updateLastLoginTime(userId);
        LoginVO vo = new LoginVO();
        vo.setToken(jwtUtils.createToken(userId, userName, sessionId));
        vo.setSessionId(sessionId);
        vo.setUser(buildUserInfo(userId));
        return vo;
    }

    @Override
    // 登出并吊销会话
    public void logout(HttpServletRequest request) {
        String token = jwtUtils.extractBearerToken(request);
        if (!StringUtils.hasText(token)) {
            return;
        }
        try {
            String sessionId = jwtUtils.getJti(jwtUtils.parseToken(token));
            loginSessionService.revokeSession(sessionId);
        } catch (Exception ignored) {
            // 已过期或无效 token 无需吊销
        }
    }

    @Override
    // 获取当前登录用户信息
    public SysUserInfoVO getCurrentUser() {
        Long userId = LoginUserUtils.getUserId();
        if (userId == null) {
            throw new BusinessException(Module.ModuleType.AUTH, "未登录", null);
        }
        return buildUserInfo(userId);
    }

    // 构建用户角色与权限信息
    public SysUserInfoVO buildUserInfo(Long userId) {
        return sysUserService.getCurrentUserInfo(userId);
    }
}

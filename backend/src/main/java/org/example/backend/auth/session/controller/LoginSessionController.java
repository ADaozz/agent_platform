package org.example.backend.auth.session.controller;

import org.apache.shiro.SecurityUtils;
import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.example.backend.auth.session.dto.LoginSessionQueryDTO;
import org.example.backend.auth.session.service.LoginSessionService;
import org.example.backend.common.annotation.Log;
import org.example.backend.common.enums.BusinessType;
import org.example.backend.common.exception.BusinessException;
import org.example.backend.common.exception.Module;
import org.example.backend.common.result.AjaxResult;
import org.example.backend.common.utils.JwtUtils;
import org.example.backend.security.context.LoginUserUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.util.StringUtils;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import javax.annotation.Resource;
import javax.servlet.http.HttpServletRequest;

@RestController
@Validated
@RequestMapping("/system/session")
public class LoginSessionController {

    @Autowired
    private LoginSessionService loginSessionService;

    @Resource
    private JwtUtils jwtUtils;

    @Log(title = "登录设备", businessType = BusinessType.QUERY)
    @GetMapping
    @RequiresPermissions("system:session:list")
    public AjaxResult list(LoginSessionQueryDTO query, HttpServletRequest request) {
        boolean canManageAll = SecurityUtils.getSubject().isPermitted("system:session:manage");
        if (!canManageAll) {
            query.setUserId(LoginUserUtils.getUserId());
            query.setUserName(null);
        }
        return AjaxResult.success("成功",
                loginSessionService.listSessions(query, resolveCurrentSessionId(request)));
    }

    @Log(title = "登录设备", businessType = BusinessType.QUERY)
    @GetMapping("/history")
    @RequiresPermissions("system:session:list")
    public AjaxResult history(@RequestParam Long userId, HttpServletRequest request) {
        boolean canManageAll = SecurityUtils.getSubject().isPermitted("system:session:manage");
        Long currentUserId = LoginUserUtils.getUserId();
        if (!canManageAll && !userId.equals(currentUserId)) {
            throw new BusinessException(Module.ModuleType.AUTH, "无权查看该用户登录轨迹", null);
        }
        return AjaxResult.success("成功",
                loginSessionService.listSessionHistory(userId, resolveCurrentSessionId(request)));
    }

    @Log(title = "登录设备", businessType = BusinessType.DELETE)
    @DeleteMapping("/{sessionId}")
    @RequiresPermissions("system:session:kick")
    public AjaxResult kick(@PathVariable String sessionId) {
        boolean canManageAll = SecurityUtils.getSubject().isPermitted("system:session:manage");
        loginSessionService.kickSession(sessionId, LoginUserUtils.getUserId(), canManageAll);
        return AjaxResult.success("踢出成功", null);
    }

    private String resolveCurrentSessionId(HttpServletRequest request) {
        String token = extractBearerToken(request);
        if (!StringUtils.hasText(token)) {
            return null;
        }
        try {
            return jwtUtils.getJti(jwtUtils.parseToken(token));
        } catch (Exception e) {
            return null;
        }
    }

    private String extractBearerToken(HttpServletRequest request) {
        String authorization = request.getHeader("Authorization");
        if (!StringUtils.hasText(authorization)) {
            return null;
        }
        authorization = authorization.trim();
        final String prefix = "Bearer ";
        if (authorization.regionMatches(true, 0, prefix, 0, prefix.length())) {
            return authorization.substring(prefix.length()).trim();
        }
        return null;
    }
}

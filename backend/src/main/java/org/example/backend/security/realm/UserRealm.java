package org.example.backend.security.realm;

import io.jsonwebtoken.Claims;
import org.apache.shiro.authc.AuthenticationException;
import org.apache.shiro.authc.AuthenticationInfo;
import org.apache.shiro.authc.AuthenticationToken;
import org.apache.shiro.authc.SimpleAuthenticationInfo;
import org.apache.shiro.authz.AuthorizationInfo;
import org.apache.shiro.authz.SimpleAuthorizationInfo;
import org.apache.shiro.realm.AuthorizingRealm;
import org.apache.shiro.subject.PrincipalCollection;
import org.example.backend.common.utils.JwtUtils;
import org.example.backend.common.utils.ApiJwtUtils;
import org.example.backend.api.service.ApiTokenService;
import org.example.backend.security.token.ApiAuthToken;
import org.example.backend.security.token.JwtToken;
import org.example.backend.system.permission.service.SysPermissionService;
import org.example.backend.system.role.service.SysRoleService;
import org.example.backend.system.user.service.SysUserService;
import org.springframework.stereotype.Component;

import javax.annotation.Resource;
import java.util.HashSet;
import java.util.Set;

@Component
public class UserRealm extends AuthorizingRealm {

    @Resource
    SysRoleService sysRoleService;
    @Resource
    SysPermissionService sysPermissionService;
    @Resource
    private JwtUtils jwtUtils;
    @Resource
    private ApiJwtUtils apiJwtUtils;
    @Resource
    private ApiTokenService apiTokenService;
    @Resource
    private org.example.backend.auth.session.service.LoginSessionService loginSessionService;
    @Resource
    private SysUserService sysUserService;

    @Override
    public boolean supports(AuthenticationToken token) {
        return token instanceof JwtToken || token instanceof ApiAuthToken;
    }

    @Override
    protected AuthorizationInfo doGetAuthorizationInfo(PrincipalCollection principals) {
        SimpleAuthorizationInfo info = new SimpleAuthorizationInfo();
        Long userId = (Long) principals.getPrimaryPrincipal();
        Set<String> sysRoleSet = new HashSet<>(sysRoleService.selectSysRoleByUserId(userId));
        Set<String> sysPermissionSet = new HashSet<>(sysPermissionService.selectSysPermissionByUserId(userId));
        info.setRoles(sysRoleSet);
        info.setStringPermissions(sysPermissionSet);
        return info;
    }

    @Override
    protected AuthenticationInfo doGetAuthenticationInfo(AuthenticationToken token) throws AuthenticationException {
        if (token instanceof ApiAuthToken) {
            return doGetApiAuthenticationInfo((ApiAuthToken) token);
        }
        JwtToken jwtToken = (JwtToken) token;
        String tokenStr = (String) jwtToken.getCredentials();
        try {
            Claims payload = jwtUtils.parseToken(tokenStr);
            Long userId = jwtUtils.getUserId(payload);
            if (userId == null) {
                throw new AuthenticationException("token 中缺少 userId");
            }
            String jti = jwtUtils.getJti(payload);
            loginSessionService.assertSessionActive(jti);
            sysUserService.assertUserActive(userId);
            return new SimpleAuthenticationInfo(userId, tokenStr, getName());
        } catch (AuthenticationException e) {
            throw e;
        } catch (Exception e) {
            throw new AuthenticationException("token 无效或已过期", e);
        }
    }

    private AuthenticationInfo doGetApiAuthenticationInfo(ApiAuthToken token) throws AuthenticationException {
        try {
            Claims claims = apiJwtUtils.parseToken((String) token.getCredentials());
            if (!apiJwtUtils.isApiToken(claims)
                    || !token.getAccessKey().equals(apiJwtUtils.getAccessKey(claims))) {
                throw new AuthenticationException("AK/SK 不匹配");
            }
            Long userId = apiJwtUtils.getUserId(claims);
            if (userId == null) {
                throw new AuthenticationException("API Token 中缺少 userId");
            }
            apiTokenService.assertTokenActive(
                    token.getAccessKey(),
                    (String) token.getCredentials(),
                    userId
            );
            sysUserService.assertUserActive(userId);
            return new SimpleAuthenticationInfo(userId, token.getCredentials(), getName());
        } catch (AuthenticationException e) {
            throw e;
        } catch (Exception e) {
            throw new AuthenticationException("API Token 无效或已过期", e);
        }
    }
}

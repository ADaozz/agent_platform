package org.example.backend.security.aspect;

import org.apache.shiro.SecurityUtils;
import org.apache.shiro.authz.AuthorizationException;
import org.apache.shiro.authz.annotation.Logical;
import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.apache.shiro.subject.Subject;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.annotation.Before;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import java.util.Arrays;

/**
 * 显式校验 {@link RequiresPermissions}。
 * Shiro 自带 Advisor 与 Spring Boot AOP 并存时可能不生效，故用 Spring Aspect 兜底。
 */
@Aspect
@Component
@Order(0)
public class PermissionAspect {

    @Before("@annotation(requiresPermissions)")
    public void checkPermission(RequiresPermissions requiresPermissions) {
        Subject subject = SecurityUtils.getSubject();
        String[] perms = requiresPermissions.value();
        if (perms.length == 0) {
            return;
        }
        if (requiresPermissions.logical() == Logical.OR) {
            boolean allowed = Arrays.stream(perms).anyMatch(subject::isPermitted);
            if (!allowed) {
                throw new AuthorizationException("无权限访问");
            }
            return;
        }
        subject.checkPermissions(perms);
    }
}

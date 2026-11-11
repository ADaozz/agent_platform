package org.example.backend.security.cache;

import lombok.extern.slf4j.Slf4j;
import org.apache.shiro.authz.AuthorizationInfo;
import org.apache.shiro.cache.Cache;
import org.example.backend.security.realm.UserRealm;
import org.example.backend.system.user.service.SysUserRoleService;
import org.springframework.context.annotation.Lazy;
import org.springframework.stereotype.Component;

import javax.annotation.Resource;
import java.util.Collection;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.Set;

/**
 * RBAC 变更后失效 Shiro 授权缓存，避免用户仍持有旧权限。
 */
@Component
@Slf4j
public class AuthorizationCacheEvictor {

    @Lazy
    @Resource
    private UserRealm userRealm;

    @Resource
    private SysUserRoleService sysUserRoleService;

    public void evictByUserId(Long userId) {
        if (userId == null) {
            return;
        }
        evictByUserIds(Collections.singleton(userId));
    }

    public void evictByRoleId(Long roleId) {
        if (roleId == null) {
            return;
        }
        evictByUserIds(sysUserRoleService.listUserIdsByRoleId(roleId));
    }

    public void evictByUserIds(Collection<Long> userIds) {
        if (userIds == null || userIds.isEmpty()) {
            return;
        }
        Cache<Object, AuthorizationInfo> cache = userRealm.getAuthorizationCache();
        if (cache == null) {
            return;
        }
        Set<Long> distinct = new LinkedHashSet<>();
        for (Long userId : userIds) {
            if (userId != null) {
                distinct.add(userId);
            }
        }
        for (Long userId : distinct) {
            cache.remove(userId);
        }
        log.debug("已清除 Shiro 授权缓存 userIds={}", distinct);
    }

    public void evictAll() {
        Cache<Object, AuthorizationInfo> cache = userRealm.getAuthorizationCache();
        if (cache != null) {
            cache.clear();
            log.debug("已清空 Shiro 授权缓存");
        }
    }
}

package org.example.backend.asset.infrastructure.acl;

import org.example.backend.asset.port.UserQueryPort;
import org.example.backend.system.user.entity.SysUserEntity;
import org.example.backend.system.user.service.SysUserService;
import org.springframework.stereotype.Component;
import org.springframework.util.CollectionUtils;

import javax.annotation.Resource;
import java.util.Collection;
import java.util.Collections;
import java.util.Map;
import java.util.stream.Collectors;

@Component
public class UserQueryAdapter implements UserQueryPort {

    @Resource
    private SysUserService sysUserService;

    @Override
    public String getUserName(Long userId) {
        if (userId == null) {
            return null;
        }
        SysUserEntity user = sysUserService.getById(userId);
        return user != null ? user.getUserName() : String.valueOf(userId);
    }

    @Override
    public Map<Long, String> getUserNames(Collection<Long> userIds) {
        if (CollectionUtils.isEmpty(userIds)) {
            return Collections.emptyMap();
        }
        return sysUserService.listByIds(userIds).stream()
                .collect(Collectors.toMap(SysUserEntity::getUserId, SysUserEntity::getUserName, (a, b) -> a));
    }
}

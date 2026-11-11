package org.example.backend.security.listener;

import lombok.extern.slf4j.Slf4j;
import org.example.backend.security.cache.AuthorizationCacheEvictor;
import org.example.backend.system.user.event.UserStatusChangedEvent;
import org.springframework.stereotype.Component;
import org.springframework.transaction.event.TransactionPhase;
import org.springframework.transaction.event.TransactionalEventListener;

import javax.annotation.Resource;

@Component
@Slf4j
public class UserStatusChangedAuthCacheListener {

    @Resource
    private AuthorizationCacheEvictor authorizationCacheEvictor;

    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void onUserStatusChanged(UserStatusChangedEvent event) {
        try {
            authorizationCacheEvictor.evictByUserId(event.getUserId());
        } catch (Exception e) {
            log.error("用户状态变更后授权缓存清理失败 userId={} type={}",
                    event.getUserId(), event.getChangeType(), e);
        }
    }
}

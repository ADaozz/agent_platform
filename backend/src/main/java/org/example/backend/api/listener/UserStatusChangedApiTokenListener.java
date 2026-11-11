package org.example.backend.api.listener;

import lombok.extern.slf4j.Slf4j;
import org.example.backend.api.service.ApiTokenService;
import org.example.backend.system.user.event.UserStatusChangedEvent;
import org.springframework.stereotype.Component;
import org.springframework.transaction.event.TransactionPhase;
import org.springframework.transaction.event.TransactionalEventListener;

import javax.annotation.Resource;

@Component
@Slf4j
public class UserStatusChangedApiTokenListener {

    @Resource
    private ApiTokenService apiTokenService;

    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void onUserStatusChanged(UserStatusChangedEvent event) {
        try {
            apiTokenService.revokeAllByUserId(event.getUserId());
        } catch (Exception e) {
            log.error("用户状态变更后 API Token 吊销失败 userId={} type={}",
                    event.getUserId(), event.getChangeType(), e);
        }
    }
}

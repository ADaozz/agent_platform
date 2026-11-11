package org.example.backend.auth.session.listener;

import lombok.extern.slf4j.Slf4j;
import org.example.backend.auth.session.service.LoginSessionService;
import org.example.backend.system.user.event.UserStatusChangedEvent;
import org.springframework.stereotype.Component;
import org.springframework.transaction.event.TransactionPhase;
import org.springframework.transaction.event.TransactionalEventListener;

import javax.annotation.Resource;

@Component
@Slf4j
public class UserStatusChangedSessionListener {

    @Resource
    private LoginSessionService loginSessionService;

    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void onUserStatusChanged(UserStatusChangedEvent event) {
        try {
            loginSessionService.revokeAllActiveSessions(event.getUserId());
        } catch (Exception e) {
            log.error("用户状态变更后会话吊销失败 userId={} type={}",
                    event.getUserId(), event.getChangeType(), e);
        }
    }
}

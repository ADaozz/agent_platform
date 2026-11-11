package org.example.backend.auth.cert.listener;

import lombok.extern.slf4j.Slf4j;
import org.example.backend.auth.cert.service.CertIssueService;
import org.example.backend.system.user.event.UserStatusChangedEvent;
import org.springframework.stereotype.Component;
import org.springframework.transaction.event.TransactionPhase;
import org.springframework.transaction.event.TransactionalEventListener;

import javax.annotation.Resource;

@Component
@Slf4j
public class UserStatusChangedCertListener {

    @Resource
    private CertIssueService certIssueService;

    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void onUserStatusChanged(UserStatusChangedEvent event) {
        try {
            certIssueService.revokeUserActiveCerts(event.getUserId());
        } catch (Exception e) {
            log.error("用户状态变更后证书吊销失败 userId={} type={}",
                    event.getUserId(), event.getChangeType(), e);
        }
    }
}

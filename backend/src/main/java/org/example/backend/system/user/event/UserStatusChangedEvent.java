package org.example.backend.system.user.event;

import lombok.Getter;

/**
 * 用户状态变更领域事件，由 IAM 上下文发布。
 * DISABLED：正常 → 停用；DELETED：用户被物理删除。
 */
@Getter
public class UserStatusChangedEvent {

    public enum ChangeType {
        DISABLED,
        DELETED
    }

    private final Long userId;
    private final ChangeType changeType;

    public UserStatusChangedEvent(Long userId, ChangeType changeType) {
        this.userId = userId;
        this.changeType = changeType;
    }
}

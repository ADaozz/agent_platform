package org.example.backend.asset.constant;

import org.example.backend.asset.host.domain.model.VmLifecycle;

/**
 * 虚机生命周期：只能按顺序单向流转，不可跳过、不可回退。
 * creating → running → stopped → pending_delete → destroyed
 *
 * @deprecated 使用 {@link VmLifecycle} 值对象
 */
@Deprecated
public final class VmLifecycleStatus {

    public static final String CREATING = VmLifecycle.CREATING;
    public static final String RUNNING = VmLifecycle.RUNNING;
    public static final String STOPPED = VmLifecycle.STOPPED;
    public static final String PENDING_DELETE = VmLifecycle.PENDING_DELETE;
    public static final String DESTROYED = VmLifecycle.DESTROYED;

    private VmLifecycleStatus() {
    }

    public static void validateTransition(String current, String target) {
        VmLifecycle.of(current).transitionTo(target);
    }

    public static boolean isTerminal(String status) {
        return VmLifecycle.isTerminal(status);
    }
}

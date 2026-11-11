package org.example.backend.asset.host.domain.model;

import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import java.util.Objects;

/**
 * 虚机生命周期值对象：creating → running → stopped → pending_delete → destroyed
 */
public final class VmLifecycle {

    public static final String CREATING = "creating";
    public static final String RUNNING = "running";
    public static final String STOPPED = "stopped";
    public static final String PENDING_DELETE = "pending_delete";
    public static final String DESTROYED = "destroyed";

    private static final Map<String, String> NEXT;

    static {
        Map<String, String> map = new HashMap<>();
        map.put(CREATING, RUNNING);
        map.put(RUNNING, STOPPED);
        map.put(STOPPED, PENDING_DELETE);
        map.put(PENDING_DELETE, DESTROYED);
        NEXT = Collections.unmodifiableMap(map);
    }

    private final String value;

    private VmLifecycle(String value) {
        this.value = value;
    }

    public static VmLifecycle of(String value) {
        return new VmLifecycle(value);
    }

    public String getValue() {
        return value;
    }

    public VmLifecycle transitionTo(String target) {
        if (target == null) {
            throw new IllegalArgumentException("lifecycle status cannot be null");
        }
        if (Objects.equals(value, target)) {
            return this;
        }
        String expectedNext = NEXT.get(value);
        if (expectedNext == null || !expectedNext.equals(target)) {
            throw new IllegalArgumentException(value + " -> " + target);
        }
        return new VmLifecycle(target);
    }

    public boolean isTerminal() {
        return isTerminal(value);
    }

    public static boolean isTerminal(String status) {
        return DESTROYED.equals(status);
    }
}

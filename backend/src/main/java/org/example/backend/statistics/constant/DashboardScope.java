package org.example.backend.statistics.constant;

public final class DashboardScope {

    public static final String MINE = "mine";

    public static final String ALL = "all";

    private DashboardScope() {
    }

    public static boolean isMine(String scope) {
        return MINE.equals(scope);
    }

    public static boolean isAll(String scope) {
        return ALL.equals(scope);
    }
}

package org.example.backend.quartz.constant;

/**
 * 定时任务默认值与状态常量。
 */
public final class SysJobConstants {

    private SysJobConstants() {
    }

    /** 默认任务分组 */
    public static final String DEFAULT_JOB_GROUP = "DEFAULT";

    /**
     * 未配置 Cron 的占位值（空字符串）。
     * 停用状态下允许；启用前须改为合法表达式（含 {@code 0 0 0 * * ?} 每天 0 点）。
     */
    public static final String UNCONFIGURED_CRON_EXPRESSION = "";

    /** 停用，新建任务默认不可执行 */
    public static final String ENABLED_NO = "0";

    /** 启用，允许按 Cron 调度或手动触发 */
    public static final String ENABLED_YES = "1";

    /** 最近一次执行状态：0-未执行 */
    public static final String RUN_IDLE = "0";

    /** 最近一次执行状态：1-正在执行 */
    public static final String RUN_RUNNING = "1";

    /** 最近一次执行状态：2-执行成功 */
    public static final String RUN_SUCCESS = "2";

    /** 最近一次执行状态：3-执行失败 */
    public static final String RUN_FAILURE = "3";
}
